"""Repository-confined discovery of complete hangboard onboarding runs."""

from __future__ import annotations

from collections.abc import Mapping
from contextlib import contextmanager
from dataclasses import dataclass
import fcntl
from hashlib import sha256
import json
import os
from pathlib import Path
import re
import shutil
import stat
import tempfile
from threading import RLock
from typing import Iterator
from uuid import uuid4

from .onboarding_run import OnboardingStateError, read_status


_BOARD_ID = re.compile(r"[a-z0-9](?:[a-z0-9.-]*[a-z0-9])?\Z")
_OUTPUTS = (
    ("definition", "manifest"),
    ("image", "normal"),
    ("selectableSvg", "productSvg"),
    ("highlights", "highlights"),
)
_DIAGNOSTIC_CODES = {
    "invalid_path",
    "invalid_board_id",
    "missing_manifest",
    "identity_mismatch",
    "invalid_run",
    "invalid_outputs",
    "invalid_transaction",
}
_TRANSACTION_SCHEMA_VERSION = 1
_TRANSACTION_PHASES = {"staged", "prior_moved", "candidate_installed"}


@dataclass(frozen=True, slots=True)
class LibraryBoard:
    board_id: str
    display_name: str
    run_path: Path
    revision_token: str


@dataclass(frozen=True, slots=True)
class PublishedBoard:
    board: LibraryBoard
    revision_token: str


@dataclass(frozen=True, slots=True)
class LibraryDiagnostic:
    path: str
    code: str
    message: str


@dataclass(frozen=True, slots=True)
class LibrarySnapshot:
    boards: tuple[LibraryBoard, ...]
    diagnostics: tuple[LibraryDiagnostic, ...]


@dataclass(frozen=True, slots=True)
class _TransactionJournal:
    board_id: str
    expected_revision_token: str | None
    candidate_revision_token: str
    phase: str

    def document(self, *, phase: str | None = None) -> dict[str, object]:
        return {
            "schemaVersion": _TRANSACTION_SCHEMA_VERSION,
            "boardId": self.board_id,
            "expectedRevisionToken": self.expected_revision_token,
            "candidateRevisionToken": self.candidate_revision_token,
            "phase": self.phase if phase is None else phase,
        }


class BoardLibraryError(ValueError):
    """Raised when a requested board or file operation is unsafe."""


class _BoardDiagnosticError(Exception):
    def __init__(self, code: str, message: str) -> None:
        if code not in _DIAGNOSTIC_CODES:
            raise ValueError(f"unknown board diagnostic code: {code}")
        self.code = code
        self.message = message


class RepositoryBoardLibrary:
    """Discover immutable, complete onboarding runs directly from the repository."""

    _locks_guard = RLock()
    _locks: dict[Path, RLock] = {}

    def __init__(self, repository_root: Path) -> None:
        try:
            self._repository_root = Path(repository_root).resolve(strict=True)
        except OSError as error:
            raise BoardLibraryError("repository root is not accessible") from error
        if not self._repository_root.is_dir():
            raise BoardLibraryError("repository root is not a directory")
        self._boards_root = (
            self._repository_root / "Tools" / "HangboardOnboarding" / "boards"
        )
        self._transactions_root = self._boards_root / ".transactions"
        with self._locks_guard:
            self._in_process_lock = self._locks.setdefault(self._boards_root, RLock())

    def snapshot(self) -> LibrarySnapshot:
        """Return all independently valid board runs and diagnostics for the rest."""
        root_problem = self._boards_root_problem()
        if root_problem is not None:
            return LibrarySnapshot(
                boards=(),
                diagnostics=(
                    LibraryDiagnostic(
                        self._repository_relative(self._boards_root),
                        "invalid_path",
                        root_problem,
                    ),
                ),
            )
        with self._publication_lock():
            transaction_diagnostics = self._recover_transactions_locked()
            return self._snapshot_locked(transaction_diagnostics)

    def _snapshot_locked(
        self, transaction_diagnostics: tuple[LibraryDiagnostic, ...]
    ) -> LibrarySnapshot:
        boards: list[LibraryBoard] = []
        diagnostics = list(transaction_diagnostics)
        try:
            entries = sorted(self._boards_root.iterdir(), key=lambda entry: entry.name)
        except OSError as error:
            raise BoardLibraryError("boards root is not readable") from error
        for entry in entries:
            if entry.name.startswith("."):
                continue
            try:
                boards.append(self._read_board(entry))
            except _BoardDiagnosticError as error:
                diagnostics.append(
                    LibraryDiagnostic(entry.name, error.code, error.message)
                )
        boards.sort(key=lambda board: (board.display_name.casefold(), board.board_id))
        return LibrarySnapshot(tuple(boards), tuple(diagnostics))

    def get_board(self, board_id: str) -> LibraryBoard:
        requested = self._board_id(board_id, "board")
        for board in self.snapshot().boards:
            if board.board_id == requested:
                return board
        raise BoardLibraryError(f"board does not exist: {requested}")

    def copy_current_run(self, board_id: str, destination: Path) -> LibraryBoard:
        requested = self._board_id(board_id, "board")
        with self._publication_lock():
            self._recover_transactions_locked()
            board = self._optional_board_locked(requested)
            if board is None:
                raise BoardLibraryError(f"board does not exist: {requested}")
            destination = Path(destination).absolute()
            if destination.exists() or destination.is_symlink():
                raise BoardLibraryError(f"destination already exists: {destination}")
            self._prepare_write_parent(destination.parent)
            stage = Path(
                tempfile.mkdtemp(
                    prefix=f".{destination.name}.tmp-", dir=destination.parent
                )
            )
            try:
                staged_run = stage / "run"
                self._copy_tree(board.run_path, staged_run)
                self._validate_complete_run(staged_run)
                shutil.move(str(staged_run), str(stage / "payload"))
                (stage / "payload").replace(destination)
                self._fsync_directory(destination.parent)
            except Exception:
                shutil.rmtree(stage, ignore_errors=True)
                raise
            else:
                shutil.rmtree(stage, ignore_errors=True)
        return board

    def publish(
        self,
        *,
        run_root: Path,
        board_id: str | None,
        expected_revision_token: str | None,
    ) -> PublishedBoard:
        candidate = self._validated_package(run_root)
        identifier = (
            candidate.board_id
            if board_id is None
            else self._board_id(board_id, "board")
        )
        if identifier != candidate.board_id:
            raise BoardLibraryError("board ID does not match run product key")
        with self._publication_lock():
            diagnostics = self._recover_transactions_locked()
            if diagnostics:
                raise BoardLibraryError(
                    "publication recovery requires manual intervention: "
                    + diagnostics[0].message
                )
            current = self._optional_board_locked(identifier)
            if (
                current is not None
                and current.revision_token == candidate.revision_token
            ):
                return PublishedBoard(current, current.revision_token)
            self._require_expected_revision(current, expected_revision_token)
            self._replace_board_locked(candidate, current)
            published = self._optional_board_locked(identifier)
            if published is None:
                raise BoardLibraryError("published board package is missing")
            return PublishedBoard(published, published.revision_token)

    @contextmanager
    def _publication_lock(self) -> Iterator[None]:
        with self._in_process_lock:
            self._prepare_write_parent(self._boards_root.parent)
            try:
                self._boards_root.mkdir(exist_ok=True)
                self._fsync_directory(self._boards_root.parent)
                self._transactions_root.mkdir(exist_ok=True)
                self._fsync_directory(self._boards_root)
            except OSError as error:
                raise BoardLibraryError(
                    "publication lock directory is not accessible"
                ) from error
            self._safe_existing_directory(
                self._transactions_root, self._boards_root, "transaction root"
            )
            lock_path = self._transactions_root / "lock"
            flags = os.O_RDWR | os.O_CREAT
            if hasattr(os, "O_NOFOLLOW"):
                flags |= os.O_NOFOLLOW
            try:
                descriptor = os.open(lock_path, flags, 0o600)
            except OSError as error:
                raise BoardLibraryError("publication lock is not accessible") from error
            try:
                if not stat.S_ISREG(os.fstat(descriptor).st_mode):
                    raise BoardLibraryError("publication lock is not a file")
                fcntl.flock(descriptor, fcntl.LOCK_EX)
                yield
            finally:
                try:
                    fcntl.flock(descriptor, fcntl.LOCK_UN)
                finally:
                    os.close(descriptor)

    def _validated_package(self, run_root: Path) -> LibraryBoard:
        run = Path(run_root).absolute()
        self._safe_existing_directory(run, run.parent, "run")
        self._reject_tree_symlinks(run)
        manifest_path = run / "run.json"
        manifest = self._read_json(manifest_path, run, "run manifest")
        product = self._mapping(manifest.get("product"), "run product")
        board_id = self._board_id(product.get("key"), "run product key")
        try:
            self._validate_complete_run(run, manifest)
        except _BoardDiagnosticError as error:
            raise BoardLibraryError(error.message) from error
        display_name = self._display_name(
            product.get("normalizedName"), "run product normalizedName"
        )
        return LibraryBoard(
            board_id=board_id,
            display_name=display_name,
            run_path=run,
            revision_token=sha256(manifest_path.read_bytes()).hexdigest(),
        )

    def _optional_board_locked(self, board_id: str) -> LibraryBoard | None:
        path = self._boards_root / board_id
        if not path.exists() and not path.is_symlink():
            return None
        try:
            return self._read_board(path)
        except _BoardDiagnosticError as error:
            raise BoardLibraryError(
                f"current board package is invalid: {error.message}"
            ) from error

    @staticmethod
    def _require_expected_revision(
        current: LibraryBoard | None, expected_revision_token: str | None
    ) -> None:
        current_token = current.revision_token if current is not None else None
        if current_token == expected_revision_token:
            return
        expected = expected_revision_token or "absent"
        actual = current_token or "absent"
        raise BoardLibraryError(
            "publication conflict: "
            f"expected revision {expected}, current revision {actual}"
        )

    def _replace_board_locked(
        self, candidate: LibraryBoard, current: LibraryBoard | None
    ) -> None:
        transaction = Path(
            tempfile.mkdtemp(
                prefix=f"{candidate.board_id}-", dir=self._transactions_root
            )
        )
        self._fsync_directory(self._transactions_root)
        staged = transaction / "candidate"
        journal = _TransactionJournal(
            board_id=candidate.board_id,
            expected_revision_token=(
                current.revision_token if current is not None else None
            ),
            candidate_revision_token=candidate.revision_token,
            phase="staged",
        )
        journaled = False
        try:
            self._copy_tree(candidate.run_path, staged)
            staged_package = self._validated_package(staged)
            if (
                staged_package.board_id != candidate.board_id
                or staged_package.revision_token != candidate.revision_token
            ):
                raise BoardLibraryError("copied publication candidate changed")
            self._fsync_tree(staged)
            self._write_journal(transaction, journal.document())
            journaled = True
            self._finish_transaction_locked(transaction, journal)
        except Exception:
            if not journaled:
                shutil.rmtree(transaction, ignore_errors=True)
                self._fsync_directory(self._transactions_root)
            raise

    def _finish_transaction_locked(
        self, transaction: Path, journal: _TransactionJournal
    ) -> None:
        current_path = self._boards_root / journal.board_id
        rollback_path = transaction / "rollback"
        candidate_path = transaction / "candidate"
        if current_path.exists() or current_path.is_symlink():
            if rollback_path.exists() or rollback_path.is_symlink():
                raise BoardLibraryError("transaction rollback path already exists")
            self._move_path(current_path, rollback_path)
            self._fsync_directory(transaction)
            self._fsync_directory(self._boards_root)
        self._write_journal(transaction, journal.document(phase="prior_moved"))
        self._move_path(candidate_path, current_path)
        self._fsync_directory(self._boards_root)
        self._fsync_directory(transaction)
        self._write_journal(
            transaction, journal.document(phase="candidate_installed")
        )
        self._remove_transaction(transaction)

    def _recover_transactions_locked(self) -> tuple[LibraryDiagnostic, ...]:
        diagnostics: list[LibraryDiagnostic] = []
        try:
            entries = sorted(
                self._transactions_root.iterdir(), key=lambda path: path.name
            )
        except OSError as error:
            raise BoardLibraryError("transaction root is not readable") from error
        for transaction in entries:
            if transaction.name == "lock":
                continue
            path = self._transaction_relative(transaction)
            if transaction.is_symlink() or not transaction.is_dir():
                diagnostics.append(
                    LibraryDiagnostic(
                        path,
                        "invalid_transaction",
                        self._message(
                            transaction,
                            "transaction evidence must be a non-symlink directory",
                        ),
                    )
                )
                continue
            try:
                self._recover_transaction_locked(transaction)
            except (BoardLibraryError, OSError) as error:
                diagnostics.append(
                    LibraryDiagnostic(
                        path,
                        "invalid_transaction",
                        self._message(
                            transaction, f"transaction is ambiguous: {error}"
                        ),
                    )
                )
        return tuple(diagnostics)

    def _recover_transaction_locked(self, transaction: Path) -> None:
        journal = self._read_transaction_journal(transaction)
        current_path = self._boards_root / journal.board_id
        candidate_path = transaction / "candidate"
        rollback_path = transaction / "rollback"
        invalid_canonical_path = transaction / "invalid-canonical"
        invalid_canonical_retained = (
            invalid_canonical_path.exists() or invalid_canonical_path.is_symlink()
        )
        current, current_problem = self._probe_package(current_path, canonical=True)
        candidate, candidate_problem = self._probe_package(candidate_path)
        rollback, rollback_problem = self._probe_package(rollback_path)
        candidate_valid = (
            candidate is not None
            and candidate.board_id == journal.board_id
            and candidate.revision_token == journal.candidate_revision_token
        )
        rollback_valid = (
            rollback is not None
            and rollback.board_id == journal.board_id
            and journal.expected_revision_token is not None
            and rollback.revision_token == journal.expected_revision_token
        )
        candidate_state_problem = candidate_problem
        if candidate is not None and not candidate_valid:
            candidate_state_problem = "candidate package does not match its journal"
        rollback_state_problem = rollback_problem
        if rollback is not None and not rollback_valid:
            rollback_state_problem = "rollback package does not match its journal"

        if invalid_canonical_retained and current is not None:
            raise BoardLibraryError(
                "recovered package has retained invalid canonical evidence"
            )
        if (
            current is not None
            and current.revision_token == journal.candidate_revision_token
        ):
            if (
                candidate_state_problem is not None
                or rollback_state_problem is not None
            ):
                problem = candidate_state_problem or rollback_state_problem
                raise BoardLibraryError(f"installed candidate has {problem}")
            self._remove_transaction(transaction)
            return
        if current_problem is not None:
            if invalid_canonical_retained:
                raise BoardLibraryError(
                    "canonical package is invalid and prior invalid evidence exists"
                )
            if not candidate_valid and not rollback_valid:
                raise BoardLibraryError(f"canonical package {current_problem}")
            self._move_path(current_path, invalid_canonical_path)
            self._fsync_directory(transaction)
            self._fsync_directory(self._boards_root)
            invalid_canonical_retained = True

        if current is not None:
            if (
                current.revision_token == journal.expected_revision_token
                and candidate_valid
                and rollback is None
                and rollback_problem is None
            ):
                self._finish_transaction_locked(transaction, journal)
                return
            raise BoardLibraryError(
                "canonical package does not prove the expected transaction state"
            )

        if candidate_valid:
            self._write_journal(
                transaction, journal.document(phase="prior_moved")
            )
            self._move_path(candidate_path, current_path)
            self._fsync_directory(self._boards_root)
            self._fsync_directory(transaction)
            self._write_journal(
                transaction, journal.document(phase="candidate_installed")
            )
            if rollback_state_problem is not None:
                raise BoardLibraryError(
                    f"installed the candidate but retained {rollback_state_problem}"
                )
            if invalid_canonical_retained:
                raise BoardLibraryError(
                    "installed the candidate and retained invalid canonical evidence"
                )
            self._remove_transaction(transaction)
            return

        if rollback_valid:
            self._move_path(rollback_path, current_path)
            self._fsync_directory(self._boards_root)
            self._fsync_directory(transaction)
            reason = candidate_state_problem or "candidate package is missing"
            raise BoardLibraryError(
                f"restored the prior package because the {reason}"
            )

        problems = [
            problem
            for problem in (candidate_state_problem, rollback_state_problem)
            if problem
        ]
        detail = "; ".join(problems) if problems else "required packages are missing"
        raise BoardLibraryError(detail)

    def _read_transaction_journal(
        self, transaction: Path
    ) -> _TransactionJournal:
        document = self._read_json(
            transaction / "journal.json", transaction, "transaction journal"
        )
        if document.get("schemaVersion") != _TRANSACTION_SCHEMA_VERSION:
            raise BoardLibraryError("transaction journal schema version is invalid")
        board_id = self._board_id(document.get("boardId"), "transaction board")
        expected_value = document.get("expectedRevisionToken")
        expected = (
            None
            if expected_value is None
            else self._sha(expected_value, "transaction expected revision token")
        )
        candidate = self._sha(
            document.get("candidateRevisionToken"),
            "transaction candidate revision token",
        )
        phase = self._string(document.get("phase"), "transaction phase")
        if phase not in _TRANSACTION_PHASES:
            raise BoardLibraryError("transaction phase is invalid")
        return _TransactionJournal(board_id, expected, candidate, phase)

    def _probe_package(
        self, path: Path, *, canonical: bool = False
    ) -> tuple[LibraryBoard | None, str | None]:
        if not path.exists() and not path.is_symlink():
            return None, None
        try:
            package = (
                self._read_board(path)
                if canonical
                else self._validated_package(path)
            )
        except (BoardLibraryError, _BoardDiagnosticError) as error:
            message = (
                error.message
                if isinstance(error, _BoardDiagnosticError)
                else str(error)
            )
            return None, f"at {self._repository_relative(path)} is invalid: {message}"
        return package, None

    def _write_journal(
        self, transaction: Path, document: Mapping[str, object]
    ) -> None:
        journal = transaction / "journal.json"
        temporary = transaction / f".journal-{uuid4().hex}.tmp"
        payload = (
            json.dumps(document, indent=2, sort_keys=True).encode("utf-8") + b"\n"
        )
        flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL
        if hasattr(os, "O_NOFOLLOW"):
            flags |= os.O_NOFOLLOW
        descriptor: int | None = None
        try:
            descriptor = os.open(temporary, flags, 0o600)
            with os.fdopen(descriptor, "wb") as stream:
                descriptor = None
                stream.write(payload)
                stream.flush()
                os.fsync(stream.fileno())
            os.replace(temporary, journal)
            self._fsync_directory(transaction)
        finally:
            if descriptor is not None:
                os.close(descriptor)
            temporary.unlink(missing_ok=True)

    def _move_path(self, source: Path, destination: Path) -> None:
        source.replace(destination)

    def _remove_transaction(self, transaction: Path) -> None:
        shutil.rmtree(transaction)
        self._fsync_directory(self._transactions_root)

    def _transaction_relative(self, transaction: Path) -> str:
        try:
            return transaction.relative_to(self._boards_root).as_posix()
        except ValueError:
            return transaction.as_posix()

    def _boards_root_problem(self) -> str | None:
        try:
            self._reject_symlinks(self._repository_root, self._boards_root)
        except BoardLibraryError as error:
            return self._message(self._boards_root, str(error))
        if self._boards_root.exists() and not self._boards_root.is_dir():
            return self._message(self._boards_root, "must be a directory")
        return None

    def _read_board(self, run: Path) -> LibraryBoard:
        if run.is_symlink() or not run.is_dir():
            raise self._diagnostic("invalid_path", run, "must be a non-symlink directory")
        try:
            board_id = self._board_id(run.name, "board directory")
        except BoardLibraryError as error:
            raise self._diagnostic("invalid_board_id", run, str(error)) from error
        try:
            self._reject_tree_symlinks(run)
        except BoardLibraryError as error:
            raise self._diagnostic("invalid_path", run, str(error)) from error

        manifest_path = run / "run.json"
        if not manifest_path.is_file():
            raise self._diagnostic("missing_manifest", manifest_path, "is missing")
        try:
            manifest = self._read_json(manifest_path, run, "run manifest")
            product = self._mapping(manifest.get("product"), "run product")
            product_key = self._string(product.get("key"), "run product key")
        except BoardLibraryError as error:
            raise self._diagnostic("invalid_run", manifest_path, str(error)) from error
        if product_key != board_id:
            raise self._diagnostic(
                "identity_mismatch",
                manifest_path,
                "product.key does not match its board directory",
            )

        try:
            self._validate_complete_run(run, manifest)
            display_name = self._display_name(
                product.get("normalizedName"), "run product normalizedName"
            )
        except _BoardDiagnosticError:
            raise
        except BoardLibraryError as error:
            raise self._diagnostic("invalid_run", manifest_path, str(error)) from error
        return LibraryBoard(
            board_id=board_id,
            display_name=display_name,
            run_path=run,
            revision_token=sha256(manifest_path.read_bytes()).hexdigest(),
        )

    def _validate_complete_run(
        self, run: Path, manifest: dict[str, object] | None = None
    ) -> None:
        self._safe_existing_directory(run, run.parent, "run")
        self._reject_tree_symlinks(run)
        if manifest is None:
            manifest = self._read_json(run / "run.json", run, "run manifest")
        output_problem = self._stage_four_output_problem(run, manifest)
        try:
            status = read_status(run)
        except (OSError, OnboardingStateError, ValueError) as error:
            if output_problem is not None:
                raise _BoardDiagnosticError("invalid_outputs", output_problem) from error
            raise BoardLibraryError(f"run is invalid: {error}") from error
        if status.get("status") != "complete" or status.get("stage") != 4:
            raise BoardLibraryError("run is not Stage 4 complete")
        if output_problem is not None:
            raise _BoardDiagnosticError("invalid_outputs", output_problem)

    def _stage_four_output_problem(
        self, run: Path, manifest: Mapping[str, object]
    ) -> str | None:
        try:
            stages = self._list(manifest.get("stages"), "run stages")
            if len(stages) != 5:
                return None
            stage = self._mapping(stages[4], "stage 4")
            if stage.get("stage") != 4:
                return None
            acceptance_path = self._member_path(
                run,
                stage.get("acceptancePath"),
                "stage 4 acceptance path",
                require_file=True,
            )
            acceptance = self._read_json(acceptance_path, run, "stage 4 acceptance")
            for _, acceptance_key in _OUTPUTS:
                output = self._mapping(
                    acceptance.get(acceptance_key), f"stage 4 {acceptance_key}"
                )
                path = self._member_path(
                    run,
                    output.get("path"),
                    f"stage 4 {acceptance_key} path",
                    require_file=True,
                )
                expected = self._sha(
                    output.get("fileSha256"), f"stage 4 {acceptance_key} hash"
                )
                if self._hash_file(path) != expected:
                    return self._message(
                        path, f"Stage 4 {acceptance_key} hash does not match"
                    )
        except BoardLibraryError as error:
            return self._message(run, f"Stage 4 outputs are invalid: {error}")
        return None

    def _diagnostic(
        self, code: str, path: Path, reason: str
    ) -> _BoardDiagnosticError:
        return _BoardDiagnosticError(code, self._message(path, reason))

    def _message(self, path: Path, reason: str) -> str:
        return f"{self._repository_relative(path)}: {reason}"

    def _repository_relative(self, path: Path) -> str:
        try:
            return path.absolute().relative_to(self._repository_root).as_posix()
        except ValueError:
            return path.as_posix()

    def _read_json(self, path: Path, root: Path, label: str) -> dict[str, object]:
        path = self._safe_existing_file(path, root, label)
        try:
            value = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, UnicodeDecodeError, json.JSONDecodeError) as error:
            raise BoardLibraryError(f"{label} is not valid JSON") from error
        return self._mapping(value, label)

    def _member_path(
        self,
        root: Path,
        value: object,
        label: str,
        *,
        require_file: bool = False,
    ) -> Path:
        relative = self._string(value, label)
        candidate = Path(relative)
        if candidate.is_absolute() or ".." in candidate.parts:
            raise BoardLibraryError(f"{label} must stay beneath its root")
        path = self._confined(root, Path(root) / candidate, label)
        self._reject_symlinks(root, path)
        if require_file:
            return self._safe_existing_file(path, root, label)
        return path

    def _safe_existing_file(self, path: Path, root: Path, label: str) -> Path:
        self._reject_symlinks(root, path)
        path = self._confined(root, path, label)
        if not path.is_file():
            raise BoardLibraryError(f"{label} is missing or not a file")
        return path

    def _safe_existing_directory(self, path: Path, root: Path, label: str) -> Path:
        self._reject_symlinks(root, path)
        path = self._confined(root, path, label)
        if not path.is_dir():
            raise BoardLibraryError(f"{label} is missing or not a directory")
        return path

    def _confined(self, root: Path, path: Path, label: str) -> Path:
        root = Path(root).resolve(strict=False)
        candidate = Path(path).resolve(strict=False)
        try:
            candidate.relative_to(root)
        except ValueError as error:
            raise BoardLibraryError(f"{label} escapes its root") from error
        return candidate

    def _reject_symlinks(self, root: Path, path: Path) -> None:
        root = Path(root).absolute()
        path = Path(path).absolute()
        self._reject_symlink_components(root, path)
        try:
            path.relative_to(self._repository_root)
        except ValueError:
            return
        self._reject_symlink_components(self._repository_root, path)

    @staticmethod
    def _reject_symlink_components(root: Path, path: Path) -> None:
        try:
            relative = path.relative_to(root)
        except ValueError as error:
            raise BoardLibraryError("path escapes its root") from error
        current = root
        if current.is_symlink():
            raise BoardLibraryError("root is a symlink")
        for part in relative.parts:
            current /= part
            if current.is_symlink():
                raise BoardLibraryError("symlinked path is not allowed")
        physical_root = root.resolve(strict=False)
        physical_path = path.resolve(strict=False)
        try:
            physical_path.relative_to(physical_root)
        except ValueError as error:
            raise BoardLibraryError("path escapes its root") from error

    def _reject_tree_symlinks(self, root: Path) -> None:
        if root.is_symlink():
            raise BoardLibraryError("symlinked run is not allowed")
        for path in root.rglob("*"):
            if path.is_symlink():
                raise BoardLibraryError("symlinked run member is not allowed")

    def _prepare_write_parent(self, parent: Path) -> None:
        absolute = parent.absolute()
        try:
            relative = absolute.relative_to(self._repository_root)
        except ValueError:
            root = Path(absolute.anchor)
            relative = absolute.relative_to(root)
        else:
            root = self._repository_root
        current = root
        for part in relative.parts:
            current /= part
            needs_parent_sync = False
            try:
                mode = current.lstat().st_mode
            except FileNotFoundError:
                needs_parent_sync = True
                try:
                    current.mkdir()
                except FileExistsError:
                    pass
                except OSError as error:
                    raise BoardLibraryError("write parent is not accessible") from error
                try:
                    mode = current.lstat().st_mode
                except OSError as error:
                    raise BoardLibraryError("write parent is not accessible") from error
            except OSError as error:
                raise BoardLibraryError("write parent is not accessible") from error
            if stat.S_ISLNK(mode):
                raise BoardLibraryError("write target contains a symlink")
            if not stat.S_ISDIR(mode):
                raise BoardLibraryError("write parent is not a directory")
            if needs_parent_sync:
                self._fsync_directory(current.parent)

    def _reject_write_target(self, path: Path) -> None:
        self._prepare_write_parent(path.parent)
        if path.exists() or path.is_symlink():
            raise BoardLibraryError(f"write target already exists: {path}")

    def _copy_tree(self, source: Path, destination: Path) -> None:
        self._safe_existing_directory(source, source.parent, "copy source")
        self._reject_tree_symlinks(source)
        self._reject_write_target(destination)
        shutil.copytree(source, destination, symlinks=False)
        self._reject_tree_symlinks(destination)

    def _fsync_tree(self, root: Path) -> None:
        self._reject_tree_symlinks(root)
        directories = [root]
        for path in root.rglob("*"):
            if path.is_dir():
                directories.append(path)
                continue
            descriptor = os.open(path, os.O_RDONLY)
            try:
                os.fsync(descriptor)
            finally:
                os.close(descriptor)
        for directory in sorted(
            directories, key=lambda path: len(path.parts), reverse=True
        ):
            self._fsync_directory(directory)

    @staticmethod
    def _fsync_directory(path: Path) -> None:
        descriptor = os.open(path, os.O_RDONLY)
        try:
            os.fsync(descriptor)
        finally:
            os.close(descriptor)

    @staticmethod
    def _hash_file(path: Path) -> str:
        return sha256(path.read_bytes()).hexdigest()

    @staticmethod
    def _mapping(value: object, label: str) -> dict[str, object]:
        if not isinstance(value, dict):
            raise BoardLibraryError(f"{label} must be an object")
        return dict(value)

    @staticmethod
    def _list(value: object, label: str) -> list[object]:
        if not isinstance(value, list):
            raise BoardLibraryError(f"{label} must be an array")
        return value

    @staticmethod
    def _string(value: object, label: str) -> str:
        if not isinstance(value, str):
            raise BoardLibraryError(f"{label} must be a string")
        return value

    @classmethod
    def _display_name(cls, value: object, label: str) -> str:
        result = cls._string(value, label).strip()
        if not result:
            raise BoardLibraryError(f"{label} must not be empty")
        return result

    @classmethod
    def _board_id(cls, value: object, label: str) -> str:
        result = cls._string(value, label)
        if not _BOARD_ID.fullmatch(result):
            raise BoardLibraryError(f"{label} identifier is invalid")
        return result

    @classmethod
    def _sha(cls, value: object, label: str) -> str:
        result = cls._string(value, label)
        if not re.fullmatch(r"[0-9a-f]{64}", result):
            raise BoardLibraryError(f"{label} is invalid")
        return result
