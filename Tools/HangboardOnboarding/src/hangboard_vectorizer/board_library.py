"""Repository-confined immutable hangboard package storage."""

from __future__ import annotations

from collections.abc import Mapping
from contextlib import contextmanager
from dataclasses import dataclass
from datetime import datetime, timezone
import fcntl
from hashlib import sha256
import json
import os
from pathlib import Path
import re
import shutil
import tempfile
from threading import RLock
import unicodedata

from .onboarding_run import OnboardingStateError, read_status


_SCHEMA_VERSION = 1
_BOARD_ID = re.compile(r"[a-z0-9](?:[a-z0-9.-]*[a-z0-9])?\Z")
_VERSION_ID = re.compile(r"revision-(\d+)\Z")
_OUTPUTS = (
    ("definition", "manifest"),
    ("image", "normal"),
    ("selectableSvg", "productSvg"),
    ("highlights", "highlights"),
)


@dataclass(frozen=True, slots=True)
class LibraryBoard:
    board_id: str
    display_name: str
    package_path: Path
    current_version_id: str
    current_run_path: Path


@dataclass(frozen=True, slots=True)
class PublishedBoard:
    board: LibraryBoard
    version_id: str


class BoardLibraryError(ValueError):
    """Raised when a repository board package is malformed or unsafe."""


class RepositoryBoardLibrary:
    """Read and atomically publish complete onboarding runs in one repository."""

    __repository_locks_guard = RLock()
    __repository_locks: dict[Path, RLock] = {}

    def __init__(self, repository_root: Path) -> None:
        self._repository_root = Path(repository_root).absolute()
        self._library_root = self._repository_root / "Tools" / "HangboardOnboarding" / "board-library"

    def list_boards(self) -> tuple[LibraryBoard, ...]:
        catalog = self._read_catalog()
        entries = self._list(catalog["boards"], "catalog.boards")
        board_ids: set[str] = set()
        package_paths: set[Path] = set()
        boards: list[LibraryBoard] = []
        for index, entry_value in enumerate(entries):
            board_id: str | None = None
            try:
                entry = self._mapping(entry_value, "catalog board")
                self._exact_keys(entry, {"boardId", "displayName", "packagePath"}, "catalog board")
                board_id = self._board_id(entry["boardId"], "catalog boardId")
                display_name = self._display_name(entry["displayName"], "catalog displayName")
                package_path = self._member_path(
                    self._library_root, entry["packagePath"], "catalog packagePath", require_directory=True
                )
                if board_id in board_ids:
                    raise BoardLibraryError("duplicate boardId in catalog")
                if package_path in package_paths:
                    raise BoardLibraryError("duplicate packagePath in catalog")
                board_ids.add(board_id)
                package_paths.add(package_path)
                boards.append(self._read_board_package(board_id, display_name, package_path))
            except BoardLibraryError as error:
                context = f"catalog.boards[{index}]"
                if board_id is not None:
                    context += f" boardId {board_id}"
                raise BoardLibraryError(f"{context}: {error}") from error
        return tuple(sorted(boards, key=lambda board: (board.display_name.casefold(), board.board_id)))

    def get_board(self, board_id: str) -> LibraryBoard:
        requested = self._board_id(board_id, "board")
        for board in self.list_boards():
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
            self._copy_tree(board.current_run_path, staged_run)
            self._validate_complete_run(staged_run)
            version_root = board.current_run_path.parent
            published = self._read_published(version_root / "published.json", version_root)
            self._validate_published_run(published, staged_run)
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
        display_name: str,
        run_root: Path,
        board_id: str | None,
        expected_current_version_id: str | None,
        publication_token: str | None = None,
    ) -> PublishedBoard:
        display_name = self._display_name(display_name, "displayName")
        run_root = Path(run_root)
        published = self._published_document_for_run(run_root)
        if publication_token is not None:
            publication_token = self._sha(publication_token, "publication token")
        if board_id is None:
            if expected_current_version_id is not None:
                raise BoardLibraryError("new board must not have an expected current version")
            return self._publish_new(
                display_name, run_root, published, publication_token
            )
        identifier = self._board_id(board_id, "board")
        current = self._catalog_index().get(identifier)
        if current is None:
            raise BoardLibraryError(f"board does not exist: {identifier}")
        if expected_current_version_id != current.current_version_id:
            reconciled = self._reconciled_publication(
                (current,),
                display_name,
                published["runIdentitySha256"],
                publication_token,
            )
            if reconciled is not None:
                return reconciled
            raise BoardLibraryError(
                f"expected {expected_current_version_id}, current {current.current_version_id}"
            )
        return self._publish_existing(
            current,
            run_root,
            published,
            expected_current_version_id=expected_current_version_id,
            publication_token=publication_token,
        )

    def _publish_existing(
        self,
        board: LibraryBoard,
        run_root: Path,
        published: dict[str, object],
        *,
        expected_current_version_id: str,
        publication_token: str | None,
    ) -> PublishedBoard:
        package = board.package_path
        versions_root = self._safe_existing_directory(package / "versions", package, "versions")
        stage = Path(tempfile.mkdtemp(prefix=".publication.tmp-", dir=versions_root))
        try:
            stage_run = stage / "run"
            self._copy_tree(run_root, stage_run)
            self._validate_complete_run(stage_run)
            self._validate_published_run(published, stage_run)
            self._write_new_json(stage / "published.json", published)
            self._write_publication_token(
                stage,
                publication_token,
                published["runIdentitySha256"],
            )
            self._fsync_tree(stage)
            with self._publication_lock():
                current = self._catalog_index().get(board.board_id)
                if current is None:
                    raise BoardLibraryError(f"board does not exist: {board.board_id}")
                if current.current_version_id != expected_current_version_id:
                    reconciled = self._reconciled_publication(
                        (current,),
                        board.display_name,
                        published["runIdentitySha256"],
                        publication_token,
                    )
                    if reconciled is not None:
                        return reconciled
                    raise BoardLibraryError(
                        f"expected {expected_current_version_id}, current {current.current_version_id}"
                    )
                board_document = self._read_board_document(package / "board.json", package)
                versions = self._list(board_document["versions"], "board.versions")
                version_id = self._next_version_id(versions_root)
                final_version = versions_root / version_id
                self._reject_write_target(final_version)
                os.replace(stage, final_version)
                self._fsync_directory(versions_root)
                updated = dict(board_document)
                updated["currentVersionId"] = version_id
                updated["versions"] = [
                    *versions,
                    self._version_record(version_id, current.current_version_id),
                ]
                self._replace_json(package / "board.json", updated, package)
        finally:
            shutil.rmtree(stage, ignore_errors=True)
        return PublishedBoard(self.get_board(board.board_id), version_id)

    def _publish_new(
        self,
        display_name: str,
        run_root: Path,
        published: dict[str, object],
        publication_token: str | None,
    ) -> PublishedBoard:
        self._prepare_write_parent(self._library_root / "boards")
        boards_root = self._library_root / "boards"
        stage = Path(tempfile.mkdtemp(prefix=".publication.tmp-", dir=boards_root))
        version_id = "revision-0001"
        try:
            version = stage / "versions" / version_id
            self._copy_tree(run_root, version / "run")
            self._validate_complete_run(version / "run")
            self._validate_published_run(published, version / "run")
            self._write_new_json(version / "published.json", published)
            self._write_publication_token(
                version,
                publication_token,
                published["runIdentitySha256"],
            )
            self._fsync_tree(stage)
            with self._publication_lock():
                existing = self._catalog_index()
                reconciled = self._reconciled_publication(
                    existing.values(),
                    display_name,
                    published["runIdentitySha256"],
                    publication_token,
                )
                if reconciled is not None:
                    return reconciled
                reserved_ids = set(existing) | self._package_ids(boards_root)
                board_id = self._allocate_board_id(display_name, reserved_ids)
                package = boards_root / board_id
                self._reject_write_target(package)
                self._write_new_json(
                    stage / "board.json",
                    {
                        "schemaVersion": _SCHEMA_VERSION,
                        "boardId": board_id,
                        "displayName": display_name,
                        "currentVersionId": version_id,
                        "versions": [self._version_record(version_id, None)],
                    },
                )
                self._fsync_tree(stage)
                os.replace(stage, package)
                self._fsync_directory(boards_root)
                catalog = self._read_catalog()
                entries = self._list(catalog["boards"], "catalog.boards")
                merged = [
                    *entries,
                    {
                        "boardId": board_id,
                        "displayName": display_name,
                        "packagePath": f"boards/{board_id}",
                    },
                ]
                merged.sort(
                    key=lambda entry: (
                        self._display_name(
                            self._mapping(entry, "catalog board")["displayName"],
                            "catalog displayName",
                        ).casefold(),
                        self._board_id(
                            self._mapping(entry, "catalog board")["boardId"],
                            "catalog boardId",
                        ),
                    )
                )
                self._replace_json(
                    self._library_root / "catalog.json",
                    {"schemaVersion": _SCHEMA_VERSION, "boards": merged},
                    self._library_root,
                )
        finally:
            shutil.rmtree(stage, ignore_errors=True)
        board = self.get_board(board_id)
        return PublishedBoard(board, version_id)

    def _read_catalog(self) -> dict[str, object]:
        document = self._read_json(self._library_root / "catalog.json", self._library_root, "catalog")
        self._exact_keys(document, {"schemaVersion", "boards"}, "catalog")
        if document["schemaVersion"] != _SCHEMA_VERSION:
            raise BoardLibraryError("unsupported catalog schema version")
        self._list(document["boards"], "catalog.boards")
        return document

    def _read_board_package(self, board_id: str, display_name: str, package: Path) -> LibraryBoard:
        document = self._read_board_document(package / "board.json", package)
        if document["boardId"] != board_id:
            raise BoardLibraryError("boardId does not match catalog")
        if document["displayName"] != display_name:
            raise BoardLibraryError("displayName does not match catalog")
        current_id = self._version_id(document["currentVersionId"])
        versions = self._list(document["versions"], "board.versions")
        found_run: Path | None = None
        seen: set[str] = set()
        for index, value in enumerate(versions):
            version_id: str | None = None
            try:
                version = self._mapping(value, "board version")
                self._exact_keys(version, {"versionId", "parentVersionId", "publishedAt", "publishedPath"}, "board version")
                version_id = self._version_id(version["versionId"])
                if version_id in seen:
                    raise BoardLibraryError("duplicate versionId")
                parent = version["parentVersionId"]
                if parent is not None:
                    parent = self._version_id(parent)
                    if parent not in seen:
                        raise BoardLibraryError(
                            "parentVersionId must reference an earlier existing version"
                        )
                self._published_at(version["publishedAt"])
                version_path = self._member_path(package, version["publishedPath"], "publishedPath", require_directory=True)
                expected = package / "versions" / version_id
                if version_path != expected:
                    raise BoardLibraryError("publishedPath does not match versionId")
                run = self._safe_existing_directory(version_path / "run", version_path, "run")
                published = self._read_published(version_path / "published.json", version_path)
                self._read_publication_token(
                    version_path, published["runIdentitySha256"]
                )
                self._validate_complete_run(run)
                self._validate_published_run(published, run)
                seen.add(version_id)
                if version_id == current_id:
                    found_run = run
            except BoardLibraryError as error:
                context = f"board {board_id} versions[{index}]"
                if version_id is not None:
                    context += f" versionId {version_id}"
                raise BoardLibraryError(f"{context}: {error}") from error
        if found_run is None:
            raise BoardLibraryError("currentVersionId is missing from versions")
        return LibraryBoard(board_id, display_name, package, current_id, found_run)

    def _read_board_document(self, path: Path, package: Path) -> dict[str, object]:
        document = self._read_json(path, package, "board")
        self._exact_keys(document, {"schemaVersion", "boardId", "displayName", "currentVersionId", "versions"}, "board")
        if document["schemaVersion"] != _SCHEMA_VERSION:
            raise BoardLibraryError("unsupported board schema version")
        self._board_id(document["boardId"], "boardId")
        self._display_name(document["displayName"], "displayName")
        self._version_id(document["currentVersionId"])
        self._list(document["versions"], "board.versions")
        return document

    def _read_published(self, path: Path, version: Path) -> dict[str, object]:
        document = self._read_json(path, version, "published")
        self._exact_keys(document, {"schemaVersion", "runIdentitySha256", "definition", "image", "selectableSvg", "highlights"}, "published")
        if document["schemaVersion"] != _SCHEMA_VERSION:
            raise BoardLibraryError("unsupported published schema version")
        self._sha(document["runIdentitySha256"], "published runIdentitySha256")
        for key, _ in _OUTPUTS:
            output = self._mapping(document[key], f"published {key}")
            self._exact_keys(output, {"path", "sha256"}, f"published {key}")
            self._member_path(version, output["path"], f"published {key} path", require_file=True)
            self._sha(output["sha256"], f"published {key} sha256")
        return document

    def _published_document_for_run(self, run: Path) -> dict[str, object]:
        run = Path(run).resolve(strict=False)
        self._validate_complete_run(run)
        manifest = self._read_json(run / "run.json", run, "run manifest")
        identity = self._sha(manifest.get("runIdentitySha256"), "runIdentitySha256")
        stages = self._list(manifest.get("stages"), "run stages")
        if len(stages) != 5:
            raise BoardLibraryError("complete run does not have five stages")
        stage = self._mapping(stages[4], "stage 4")
        acceptance_path = self._member_path(run, stage.get("acceptancePath"), "stage 4 acceptancePath", require_file=True)
        acceptance = self._read_json(acceptance_path, run, "stage 4 acceptance")
        if acceptance.get("runIdentitySha256") != identity or acceptance.get("stage") != 4:
            raise BoardLibraryError("stage 4 acceptance does not match run")
        document: dict[str, object] = {"schemaVersion": _SCHEMA_VERSION, "runIdentitySha256": identity}
        for published_key, acceptance_key in _OUTPUTS:
            output = self._mapping(acceptance.get(acceptance_key), f"stage 4 {acceptance_key}")
            path = self._string(output.get("path"), f"stage 4 {acceptance_key} path")
            hash_value = self._sha(output.get("fileSha256"), f"stage 4 {acceptance_key} hash")
            artifact = self._member_path(run, path, f"stage 4 {acceptance_key} path", require_file=True)
            if self._hash_file(artifact) != hash_value:
                raise BoardLibraryError(f"stage 4 {acceptance_key} hash does not match")
            document[published_key] = {"path": f"run/{path}", "sha256": hash_value}
        return document

    def _validate_published_run(self, published: Mapping[str, object], run: Path) -> None:
        generated = self._published_document_for_run(run)
        if dict(published) != generated:
            raise BoardLibraryError("published outputs do not match approved Stage 4 evidence")

    def _validate_complete_run(self, run: Path) -> None:
        self._safe_existing_directory(run, run.parent, "run")
        self._reject_tree_symlinks(run)
        try:
            status = read_status(run)
        except (OSError, OnboardingStateError, ValueError) as error:
            raise BoardLibraryError(f"run is invalid: {error}") from error
        if status.get("status") != "complete" or status.get("stage") != 4:
            raise BoardLibraryError("run is not Stage 4 complete")

    def _catalog_index(self) -> dict[str, LibraryBoard]:
        return {board.board_id: board for board in self.list_boards()}

    def _allocate_board_id(self, display_name: str, existing: set[str]) -> str:
        text = unicodedata.normalize("NFKD", display_name).encode("ascii", "ignore").decode("ascii").lower()
        base = re.sub(r"[^a-z0-9]+", "-", text).strip("-")
        if not base or not _BOARD_ID.fullmatch(base):
            raise BoardLibraryError("displayName cannot produce a valid board identifier")
        candidate = base
        suffix = 2
        while candidate in existing:
            candidate = f"{base}-{suffix}"
            suffix += 1
        return candidate

    def _next_version_id(self, versions_root: Path) -> str:
        values = []
        for entry in versions_root.iterdir():
            if entry.is_symlink():
                raise BoardLibraryError("versions contains a symlink")
            match = _VERSION_ID.fullmatch(entry.name)
            if match:
                values.append(int(match.group(1)))
        return f"revision-{max(values, default=0) + 1:04d}"

    def _version_record(self, version_id: str, parent: str | None) -> dict[str, object]:
        return {
            "versionId": version_id,
            "parentVersionId": parent,
            "publishedAt": datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z"),
            "publishedPath": f"versions/{version_id}",
        }

    def _reconciled_publication(
        self,
        boards: object,
        display_name: str,
        run_identity: object,
        publication_token: str | None,
    ) -> PublishedBoard | None:
        if publication_token is None:
            return None
        identity = self._sha(run_identity, "runIdentitySha256")
        matches = [
            board
            for board in boards
            if isinstance(board, LibraryBoard)
            and board.display_name == display_name
            and self._current_run_identity(board) == identity
            and self._current_publication_token(board) == publication_token
        ]
        if len(matches) > 1:
            raise BoardLibraryError(
                "published run identity matches more than one repository board"
            )
        if not matches:
            return None
        board = matches[0]
        return PublishedBoard(board, board.current_version_id)

    def _current_publication_token(self, board: LibraryBoard) -> str | None:
        version_root = board.current_run_path.parent
        return self._read_publication_token(
            version_root,
            self._current_run_identity(board),
        )

    def _read_publication_token(
        self, version_root: Path, run_identity: object
    ) -> str | None:
        path = version_root / "publication.json"
        self._reject_symlinks(version_root, path)
        if not path.exists():
            return None
        document = self._read_json(path, version_root, "publication token")
        self._exact_keys(
            document,
            {"schemaVersion", "token", "runIdentitySha256"},
            "publication token",
        )
        if document["schemaVersion"] != _SCHEMA_VERSION:
            raise BoardLibraryError("unsupported publication token schema version")
        identity = self._sha(
            document["runIdentitySha256"], "publication token runIdentitySha256"
        )
        if identity != self._sha(run_identity, "published runIdentitySha256"):
            raise BoardLibraryError("publication token does not match published run")
        return self._sha(document["token"], "publication token")

    def _write_publication_token(
        self,
        version_root: Path,
        publication_token: str | None,
        run_identity: object,
    ) -> None:
        if publication_token is None:
            return
        self._write_new_json(
            version_root / "publication.json",
            {
                "schemaVersion": _SCHEMA_VERSION,
                "token": publication_token,
                "runIdentitySha256": self._sha(
                    run_identity, "published runIdentitySha256"
                ),
            },
        )

    def _current_run_identity(self, board: LibraryBoard) -> str:
        version_root = board.current_run_path.parent
        published = self._read_published(version_root / "published.json", version_root)
        return self._sha(
            published["runIdentitySha256"], "published runIdentitySha256"
        )

    def _package_ids(self, boards_root: Path) -> set[str]:
        identifiers: set[str] = set()
        for entry in boards_root.iterdir():
            if entry.is_symlink():
                raise BoardLibraryError("boards contains a symlink")
            if entry.is_dir() and _BOARD_ID.fullmatch(entry.name):
                identifiers.add(entry.name)
        return identifiers

    @contextmanager
    def _publication_lock(self):
        self._reject_symlinks(self._repository_root, self._library_root)
        key = self._library_root.resolve(strict=False)
        with self.__repository_locks_guard:
            thread_lock = self.__repository_locks.setdefault(key, RLock())
        with thread_lock:
            flags = os.O_RDONLY
            flags |= getattr(os, "O_DIRECTORY", 0)
            flags |= getattr(os, "O_NOFOLLOW", 0)
            try:
                descriptor = os.open(self._library_root, flags)
            except OSError as error:
                raise BoardLibraryError("library root is not safely accessible") from error
            try:
                fcntl.flock(descriptor, fcntl.LOCK_EX)
                yield
            finally:
                fcntl.flock(descriptor, fcntl.LOCK_UN)
                os.close(descriptor)

    def _read_json(self, path: Path, root: Path, label: str) -> dict[str, object]:
        path = self._safe_existing_file(path, root, label)
        try:
            value = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as error:
            raise BoardLibraryError(f"{label} is not valid JSON") from error
        return self._mapping(value, label)

    def _member_path(self, root: Path, value: object, label: str, *, require_directory: bool = False, require_file: bool = False) -> Path:
        relative = self._string(value, label)
        candidate = Path(relative)
        if candidate.is_absolute() or ".." in candidate.parts:
            raise BoardLibraryError(f"{label} must stay beneath its root")
        raw_path = Path(root) / candidate
        self._reject_symlinks(root, raw_path)
        path = self._confined(root, raw_path, label)
        if require_directory:
            return self._safe_existing_directory(path, root, label)
        if require_file:
            return self._safe_existing_file(path, root, label)
        self._reject_symlinks(root, path)
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
            path.relative_to(self._library_root)
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
        parent = Path(parent)
        parent.mkdir(parents=True, exist_ok=True)
        if not parent.is_dir():
            raise BoardLibraryError("write parent is not a directory")
        absolute = parent.absolute()
        current = Path(absolute.anchor)
        for part in absolute.parts[1:]:
            current /= part
            if current.is_symlink():
                raise BoardLibraryError("write target contains a symlink")

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

    def _write_new_json(self, path: Path, value: object) -> None:
        self._reject_write_target(path)
        self._write_json_file(path, value, replace=False)

    def _replace_json(self, path: Path, value: object, root: Path) -> None:
        self._safe_existing_file(path, root, "write target")
        self._write_json_file(path, value, replace=True)

    def _write_json_file(self, path: Path, value: object, *, replace: bool) -> None:
        descriptor, temporary_name = tempfile.mkstemp(prefix=f".{path.name}.tmp-", dir=path.parent)
        temporary = Path(temporary_name)
        try:
            with os.fdopen(descriptor, "w", encoding="utf-8") as stream:
                descriptor = -1
                json.dump(value, stream, indent=2, sort_keys=True)
                stream.write("\n")
                stream.flush()
                os.fsync(stream.fileno())
            if replace:
                os.replace(temporary, path)
            else:
                os.link(temporary, path)
            self._fsync_directory(path.parent)
        finally:
            if descriptor >= 0:
                os.close(descriptor)
            temporary.unlink(missing_ok=True)

    @staticmethod
    def _fsync_directory(path: Path) -> None:
        descriptor = os.open(path, os.O_RDONLY)
        try:
            os.fsync(descriptor)
        finally:
            os.close(descriptor)

    def _fsync_tree(self, root: Path) -> None:
        for path in sorted(root.rglob("*")):
            if path.is_file():
                with path.open("rb") as stream:
                    os.fsync(stream.fileno())
        for path in sorted((item for item in root.rglob("*") if item.is_dir()), reverse=True):
            self._fsync_directory(path)
        self._fsync_directory(root)

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
    def _version_id(cls, value: object) -> str:
        result = cls._board_id(value, "versionId")
        if not _VERSION_ID.fullmatch(result):
            raise BoardLibraryError("versionId is invalid")
        return result

    @classmethod
    def _sha(cls, value: object, label: str) -> str:
        result = cls._string(value, label)
        if not re.fullmatch(r"[0-9a-f]{64}", result):
            raise BoardLibraryError(f"{label} is invalid")
        return result

    @classmethod
    def _published_at(cls, value: object) -> str:
        result = cls._string(value, "publishedAt")
        if not re.fullmatch(r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z", result):
            raise BoardLibraryError("publishedAt must be a UTC timestamp")
        try:
            datetime.strptime(result, "%Y-%m-%dT%H:%M:%SZ")
        except ValueError as error:
            raise BoardLibraryError("publishedAt must be a UTC timestamp") from error
        return result

    @staticmethod
    def _exact_keys(value: Mapping[str, object], expected: set[str], label: str) -> None:
        if set(value) != expected:
            raise BoardLibraryError(f"{label} members are invalid")
