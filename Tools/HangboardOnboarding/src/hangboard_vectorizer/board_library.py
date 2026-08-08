"""Repository-confined discovery of complete hangboard onboarding runs."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from hashlib import sha256
import json
import os
from pathlib import Path
import re
import shutil
import stat
import tempfile

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
}


@dataclass(frozen=True, slots=True)
class LibraryBoard:
    board_id: str
    display_name: str
    run_path: Path
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
        if not self._boards_root.exists():
            return LibrarySnapshot(boards=(), diagnostics=())

        boards: list[LibraryBoard] = []
        diagnostics: list[LibraryDiagnostic] = []
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
        board = self.get_board(board_id)
        destination = Path(destination).absolute()
        if destination.exists() or destination.is_symlink():
            raise BoardLibraryError(f"destination already exists: {destination}")
        self._prepare_write_parent(destination.parent)
        stage = Path(tempfile.mkdtemp(prefix=f".{destination.name}.tmp-", dir=destination.parent))
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
        except (OSError, json.JSONDecodeError) as error:
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
            try:
                mode = current.lstat().st_mode
            except FileNotFoundError:
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
