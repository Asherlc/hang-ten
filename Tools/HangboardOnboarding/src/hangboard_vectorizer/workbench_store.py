"""Filesystem-backed board and immutable revision metadata for the workbench."""

from __future__ import annotations

from collections.abc import Callable, Mapping
from dataclasses import dataclass, replace
from functools import wraps
import json
import os
from pathlib import Path
import re
import shutil
import tempfile
from threading import RLock
from typing import TypeVar


_SCHEMA_VERSION = 1
_FINAL_STAGE = 4
_IDENTIFIER = re.compile(r"[A-Za-z0-9][A-Za-z0-9._-]*\Z")
_BOARD_ID = re.compile(r"board-(\d+)\Z")
_REVISION_ID = re.compile(r"revision-(\d+)\Z")
_DRAFT_ID = re.compile(r"draft-(\d+)\.json\Z")
_REPOSITORY_BOARD_ID = re.compile(r"[a-z0-9](?:[a-z0-9.-]*[a-z0-9])?\Z")
_REPOSITORY_VERSION_ID = re.compile(r"revision-(\d+)\Z")


@dataclass(frozen=True, slots=True)
class RevisionRecord:
    id: str
    run_root: Path
    parent_revision_id: str | None
    fork_stage: int | None
    current_stage: int
    state: str
    stale_from_stage: int | None


@dataclass(frozen=True, slots=True)
class BoardRecord:
    id: str
    product_name: str
    active_revision_id: str
    saved_revision_id: str | None
    revisions: tuple[RevisionRecord, ...]
    repository_board_id: str | None = None
    repository_version_id: str | None = None


class WorkbenchStoreError(ValueError):
    """Raised when a board store operation or persisted record is invalid."""


@dataclass(slots=True)
class _PublicationState:
    published: bool = False


@dataclass(slots=True)
class _InitialReservationState:
    board_id: str | None = None


_ResultT = TypeVar("_ResultT")


def _synchronized(
    method: Callable[..., _ResultT],
) -> Callable[..., _ResultT]:
    @wraps(method)
    def locked(
        self: WorkbenchStore, *args: object, **kwargs: object
    ) -> _ResultT:
        with self._metadata_lock:
            return method(self, *args, **kwargs)

    return locked


class WorkbenchStore:
    """Own board manifests above CLI-compatible onboarding run directories."""

    def __init__(self, workspace: Path) -> None:
        self._metadata_lock = RLock()
        self._workspace = Path(workspace).resolve(strict=False)
        self._workspace.mkdir(parents=True, exist_ok=True)
        if not self._workspace.is_dir():
            raise WorkbenchStoreError(
                f"workbench workspace is not a directory: {self._workspace}"
            )
        self._boards_root = self._confined(self._workspace / "boards")
        self._boards_root.mkdir(exist_ok=True)

    @_synchronized
    def create_board(self, product_name: str) -> BoardRecord:
        """Create a board manifest without manufacturing a product-specific ID."""
        return self._create_board(product_name, reservation=None)

    @_synchronized
    def reserve_initial_revision(
        self, product_name: str
    ) -> tuple[BoardRecord, RevisionRecord]:
        """Reserve one initial board and revision as a single cleanup transaction."""
        reservation = _InitialReservationState()
        try:
            board = self._create_board(product_name, reservation=reservation)
            revision = self.create_revision(board.id)
        except Exception:
            if reservation.board_id is not None:
                self._discard_failed_initial_reservation(reservation.board_id)
            raise
        return board, revision

    def _create_board(
        self,
        product_name: str,
        *,
        reservation: _InitialReservationState | None,
    ) -> BoardRecord:
        if not isinstance(product_name, str) or not product_name.strip():
            raise WorkbenchStoreError("product name must not be empty")
        board_id = self._next_numbered_id(self._boards_root, _BOARD_ID, "board")
        board_root = self._board_root(board_id)
        board_root.mkdir()
        if reservation is not None:
            reservation.board_id = board_id
        board = BoardRecord(
            id=board_id,
            product_name=product_name.strip(),
            active_revision_id="",
            saved_revision_id=None,
            revisions=(),
        )
        publication = _PublicationState()
        try:
            self._write_board(board, publication=publication)
        except Exception:
            if not publication.published:
                board_root.rmdir()
            raise
        return board

    def _discard_failed_initial_reservation(self, board_id: str) -> None:
        """Remove this transaction's board only when no run can have started."""
        board_root = self._board_root(board_id)
        if not board_root.exists():
            return
        board = self.read_board(board_id)
        if (
            board.active_revision_id
            or board.saved_revision_id is not None
            or len(board.revisions) > 1
        ):
            raise WorkbenchStoreError(
                f"board {board.id} is not an unstarted initial reservation"
            )
        if board.revisions:
            revision = board.revisions[0]
            expected_root = self._revision_root(board.id, revision.id) / "run"
            if (
                revision.parent_revision_id is not None
                or revision.state != "pending"
                or revision.run_root != self._confined(expected_root)
                or revision.run_root.exists()
            ):
                raise WorkbenchStoreError(
                    f"board {board.id} is not an unstarted initial reservation"
                )
        shutil.rmtree(board_root)
        self._fsync_directory(self._boards_root)

    @_synchronized
    def create_revision(
        self,
        board_id: str,
        *,
        parent_revision_id: str | None = None,
        fork_stage: int | None = None,
    ) -> RevisionRecord:
        """Reserve a revision whose run root can be created by ``start_run``."""
        board = self.read_board(board_id)
        if (parent_revision_id is None) != (fork_stage is None):
            raise WorkbenchStoreError(
                "parent revision and fork stage must be provided together"
            )
        if parent_revision_id is not None:
            self._validate_identifier(parent_revision_id, "revision")
            self._revision(board, parent_revision_id)
            self._validate_stage(fork_stage)

        revisions_root = self._confined(self._board_root(board.id) / "revisions")
        revisions_root.mkdir(exist_ok=True)
        revision_id = self._next_numbered_id(
            revisions_root, _REVISION_ID, "revision"
        )
        revision_root = self._confined(revisions_root / revision_id)
        revision_root.mkdir()
        revision = RevisionRecord(
            id=revision_id,
            run_root=self._confined(revision_root / "run"),
            parent_revision_id=parent_revision_id,
            fork_stage=fork_stage,
            current_stage=0,
            state="pending",
            stale_from_stage=None,
        )
        updated = replace(
            board,
            revisions=(*board.revisions, revision),
        )
        publication = _PublicationState()
        try:
            self._write_board(updated, publication=publication)
        except Exception:
            if not publication.published:
                revision_root.rmdir()
            raise
        return revision

    @_synchronized
    def activate_revision(
        self,
        board_id: str,
        revision_id: str,
        *,
        stale_parent_revision_id: str | None = None,
        stale_from_stage: int | None = None,
    ) -> RevisionRecord:
        """Publish one usable reserved revision and optional stale parent atomically."""
        if (stale_parent_revision_id is None) != (stale_from_stage is None):
            raise WorkbenchStoreError(
                "stale parent revision and stale stage must be provided together"
            )
        board = self.read_board(board_id)
        revision = self._revision(board, revision_id)
        if revision.state != "pending":
            raise WorkbenchStoreError(
                f"revision {revision.id} is not pending activation"
            )
        if (
            revision.parent_revision_id is not None
            and stale_parent_revision_id is None
        ):
            raise WorkbenchStoreError(
                "fork activation requires a stale parent revision and stale stage"
            )
        updated_board = board
        if stale_parent_revision_id is not None:
            self._validate_identifier(stale_parent_revision_id, "revision")
            self._validate_stage(stale_from_stage)
            if revision.parent_revision_id != stale_parent_revision_id:
                raise WorkbenchStoreError(
                    f"revision {stale_parent_revision_id} is not the reserved parent"
                )
            if board.active_revision_id != stale_parent_revision_id:
                raise WorkbenchStoreError(
                    f"active revision changed from {stale_parent_revision_id}"
                )
            parent = self._revision(board, stale_parent_revision_id)
            stale_stage = (
                stale_from_stage
                if parent.stale_from_stage is None
                else min(stale_from_stage, parent.stale_from_stage)
            )
            updated_board = self._replace_revision(
                updated_board,
                replace(parent, stale_from_stage=stale_stage),
            )
        activated = replace(revision, state="active")
        updated_board = replace(
            self._replace_revision(updated_board, activated),
            active_revision_id=activated.id,
        )
        self._write_board(updated_board)
        return activated

    @_synchronized
    def register_run(
        self, product_name: str, run_root: Path
    ) -> tuple[BoardRecord, RevisionRecord]:
        """Register one existing CLI run without copying or relocating it."""
        resolved_run = self.resolve_import_run(run_root)
        if any(
            revision.run_root == resolved_run
            for board in self.list_boards()
            for revision in board.revisions
        ):
            raise WorkbenchStoreError(
                f"run root is already registered: {resolved_run}"
            )

        board = self.create_board(product_name)
        revisions_root = self._confined(self._board_root(board.id) / "revisions")
        revisions_root.mkdir(exist_ok=True)
        revision_id = self._next_numbered_id(
            revisions_root, _REVISION_ID, "revision"
        )
        revision_root = self._confined(revisions_root / revision_id)
        revision_root.mkdir()
        revision = RevisionRecord(
            id=revision_id,
            run_root=resolved_run,
            parent_revision_id=None,
            fork_stage=None,
            current_stage=0,
            state="active",
            stale_from_stage=None,
        )
        updated = replace(
            board,
            active_revision_id=revision.id,
            revisions=(revision,),
        )
        publication = _PublicationState()
        try:
            self._write_board(updated, publication=publication)
        except Exception:
            if not publication.published:
                revision_root.rmdir()
            raise
        return updated, revision

    @_synchronized
    def _discard_unstarted_board(
        self, board_id: str, revision_id: str
    ) -> None:
        """Remove one reserved board only when no onboarding run was published."""
        board = self.read_board(board_id)
        revision = self._revision(board, revision_id)
        expected_root = self._revision_root(board.id, revision.id) / "run"
        if (
            board.active_revision_id
            or board.saved_revision_id is not None
            or board.revisions != (revision,)
            or revision.parent_revision_id is not None
            or revision.state != "pending"
            or revision.run_root != self._confined(expected_root)
            or revision.run_root.exists()
        ):
            raise WorkbenchStoreError(
                f"board {board.id} is not an unstarted reservation"
            )
        shutil.rmtree(self._board_root(board.id))
        self._fsync_directory(self._boards_root)

    @_synchronized
    def read_board(self, board_id: str) -> BoardRecord:
        """Read and validate one board manifest from the confined workspace."""
        manifest_path = self._manifest_path(board_id)
        try:
            value = json.loads(manifest_path.read_text(encoding="utf-8"))
        except FileNotFoundError as error:
            raise WorkbenchStoreError(f"board does not exist: {board_id}") from error
        except (OSError, json.JSONDecodeError) as error:
            raise WorkbenchStoreError(
                f"board manifest is unreadable: {board_id}"
            ) from error
        return self._board_from_json(value, board_id)

    @_synchronized
    def read_revision(self, board_id: str, revision_id: str) -> RevisionRecord:
        """Return a validated immutable revision record."""
        self._validate_identifier(revision_id, "revision")
        return self._revision(self.read_board(board_id), revision_id)

    @_synchronized
    def list_boards(self) -> tuple[BoardRecord, ...]:
        """Return every persisted board in stable identifier order."""
        board_ids = sorted(
            entry.name
            for entry in self._boards_root.iterdir()
            if entry.is_dir() and _BOARD_ID.fullmatch(entry.name)
        )
        return tuple(self.read_board(board_id) for board_id in board_ids)

    @_synchronized
    def write_draft(
        self,
        board_id: str,
        revision_id: str,
        stage: int,
        document: object,
    ) -> Path:
        """Atomically publish a new draft document without replacing older drafts."""
        self._validate_stage(stage)
        revision = self.read_revision(board_id, revision_id)
        revision_root = self._revision_root(board_id, revision.id)
        drafts_root = self._confined(revision_root / "drafts" / f"stage-{stage}")
        drafts_root.mkdir(parents=True, exist_ok=True)
        draft_name = self._next_numbered_id(
            drafts_root, _DRAFT_ID, "draft", suffix=".json"
        )
        draft_path = self._confined(drafts_root / draft_name)
        self._write_new_json(draft_path, document)
        return draft_path

    @_synchronized
    def mark_descendants_stale(
        self, board_id: str, revision_id: str, *, from_stage: int
    ) -> RevisionRecord:
        """Mark downstream work in one revision stale from ``from_stage`` onward."""
        self._validate_stage(from_stage)
        board = self.read_board(board_id)
        revision = self._revision(board, revision_id)
        stale_stage = (
            from_stage
            if revision.stale_from_stage is None
            else min(from_stage, revision.stale_from_stage)
        )
        updated_revision = replace(revision, stale_from_stage=stale_stage)
        self._write_board(self._replace_revision(board, updated_revision))
        return updated_revision

    @_synchronized
    def mark_revision_complete(
        self, board_id: str, revision_id: str
    ) -> RevisionRecord:
        """Record that the revision has reached the final approved stage."""
        board = self.read_board(board_id)
        revision = self._revision(board, revision_id)
        updated_revision = replace(
            revision, current_stage=_FINAL_STAGE, state="complete"
        )
        self._write_board(self._replace_revision(board, updated_revision))
        return updated_revision

    @_synchronized
    def save_revision(self, board_id: str, revision_id: str) -> BoardRecord:
        """Atomically select a complete, current revision as the local saved version."""
        board = self.read_board(board_id)
        revision = self._savable_revision(board, revision_id)
        updated = replace(
            board,
            active_revision_id=revision.id,
            saved_revision_id=revision.id,
        )
        self._write_board(updated)
        return updated

    @_synchronized
    def publish_repository_revision(
        self,
        board_id: str,
        revision_id: str,
        *,
        repository_board_id: str,
        repository_version_id: str,
    ) -> BoardRecord:
        """Atomically save a revision and record the repository version it published."""
        board = self.read_board(board_id)
        revision = self._savable_revision(board, revision_id)
        self._validate_repository_link(
            repository_board_id, repository_version_id
        )
        updated = replace(
            board,
            active_revision_id=revision.id,
            saved_revision_id=revision.id,
            repository_board_id=repository_board_id,
            repository_version_id=repository_version_id,
        )
        self._write_board(updated)
        return updated

    @_synchronized
    def link_repository_version(
        self,
        board_id: str,
        *,
        repository_board_id: str,
        repository_version_id: str,
    ) -> BoardRecord:
        """Atomically record the repository version represented by this board."""
        board = self.read_board(board_id)
        self._validate_repository_link(
            repository_board_id, repository_version_id
        )
        updated = replace(
            board,
            repository_board_id=repository_board_id,
            repository_version_id=repository_version_id,
        )
        self._write_board(updated)
        return updated

    @_synchronized
    def resolve_import_run(self, run_root: Path) -> Path:
        """Resolve and confine an import root before callers read any run data."""
        resolved_run = self._confined(Path(run_root))
        if not resolved_run.is_dir():
            raise WorkbenchStoreError(
                f"imported run root is not a directory: {resolved_run}"
            )
        return resolved_run

    @_synchronized
    def synchronize_revision(
        self,
        board_id: str,
        revision_id: str,
        *,
        current_stage: int,
        state: str,
    ) -> RevisionRecord:
        """Persist the current onboarding state represented by a run manifest."""
        self._validate_stage(current_stage)
        if state not in {"active", "complete", "failed"}:
            raise WorkbenchStoreError(f"revision state is invalid: {state}")
        if state == "complete" and current_stage != _FINAL_STAGE:
            raise WorkbenchStoreError("complete revision must be at the final stage")
        board = self.read_board(board_id)
        revision = self._revision(board, revision_id)
        if revision.state == "pending":
            raise WorkbenchStoreError(
                f"revision {revision.id} is pending activation"
            )
        if revision.current_stage == current_stage and revision.state == state:
            return revision
        updated_revision = replace(
            revision, current_stage=current_stage, state=state
        )
        self._write_board(self._replace_revision(board, updated_revision))
        return updated_revision

    @_synchronized
    def mark_revision_failed(
        self,
        board_id: str,
        revision_id: str,
        *,
        restore_active_revision_id: str | None,
    ) -> RevisionRecord:
        """Retain failed evidence and restore or atomically preserve active lineage."""
        board = self.read_board(board_id)
        revision = self._revision(board, revision_id)
        if restore_active_revision_id is None:
            restore_active_revision_id = board.active_revision_id
        if restore_active_revision_id:
            self._validate_identifier(
                restore_active_revision_id, "active revision"
            )
            self._revision(board, restore_active_revision_id)
        updated_revision = replace(revision, state="failed")
        updated_board = replace(
            self._replace_revision(board, updated_revision),
            active_revision_id=restore_active_revision_id,
        )
        self._write_board(updated_board)
        return updated_revision

    def _board_from_json(self, value: object, expected_id: str) -> BoardRecord:
        manifest = self._mapping(value, "board manifest")
        if manifest.get("schemaVersion") != _SCHEMA_VERSION:
            raise WorkbenchStoreError("board manifest schema version is unsupported")
        board_id = self._string(manifest.get("id"), "board id")
        self._validate_identifier(board_id, "board")
        if board_id != expected_id:
            raise WorkbenchStoreError("board manifest identifier does not match its path")
        product_name = self._string(manifest.get("productName"), "product name")
        if not product_name.strip():
            raise WorkbenchStoreError("product name must not be empty")
        active_revision_id = self._string(
            manifest.get("activeRevisionId"), "active revision id", allow_empty=True
        )
        saved_revision_id = manifest.get("savedRevisionId")
        if saved_revision_id is not None:
            saved_revision_id = self._string(
                saved_revision_id, "saved revision id"
            )
        repository_board_id = manifest.get("repositoryBoardId")
        repository_version_id = manifest.get("repositoryVersionId")
        self._validate_repository_link(
            repository_board_id, repository_version_id
        )

        raw_revisions = manifest.get("revisions")
        if not isinstance(raw_revisions, list):
            raise WorkbenchStoreError("board revisions must be a list")
        revisions = tuple(
            self._revision_from_json(board_id, item) for item in raw_revisions
        )
        revision_ids = [revision.id for revision in revisions]
        if len(revision_ids) != len(set(revision_ids)):
            raise WorkbenchStoreError("board revision identifiers must be unique")
        known_ids = set(revision_ids)
        if active_revision_id and active_revision_id not in known_ids:
            raise WorkbenchStoreError("active revision does not exist")
        if saved_revision_id is not None and saved_revision_id not in known_ids:
            raise WorkbenchStoreError("saved revision does not exist")
        for revision in revisions:
            if (
                revision.parent_revision_id is not None
                and revision.parent_revision_id not in known_ids
            ):
                raise WorkbenchStoreError(
                    f"parent revision does not exist: {revision.parent_revision_id}"
                )
            if revision.parent_revision_id == revision.id:
                raise WorkbenchStoreError("revision cannot be its own parent")
        return BoardRecord(
            id=board_id,
            product_name=product_name,
            active_revision_id=active_revision_id,
            saved_revision_id=saved_revision_id,
            revisions=revisions,
            repository_board_id=repository_board_id,
            repository_version_id=repository_version_id,
        )

    def _revision_from_json(
        self, board_id: str, value: object
    ) -> RevisionRecord:
        record = self._mapping(value, "revision record")
        revision_id = self._string(record.get("id"), "revision id")
        self._validate_identifier(revision_id, "revision")
        expected_run_root = self._revision_root(board_id, revision_id) / "run"
        run_root_value = self._string(record.get("runRoot"), "revision run root")
        run_root = self._confined(self._board_root(board_id) / run_root_value)
        imported = record.get("imported", False)
        if type(imported) is not bool:
            raise WorkbenchStoreError("revision imported marker must be a boolean")
        if not imported and run_root != self._confined(expected_run_root):
            raise WorkbenchStoreError("revision run root is inconsistent")
        if imported and not run_root.is_dir():
            raise WorkbenchStoreError("imported revision run root is missing")

        parent_revision_id = record.get("parentRevisionId")
        if parent_revision_id is not None:
            parent_revision_id = self._string(
                parent_revision_id, "parent revision id"
            )
            self._validate_identifier(parent_revision_id, "revision")
        fork_stage = self._optional_stage(record.get("forkStage"), "fork stage")
        if (parent_revision_id is None) != (fork_stage is None):
            raise WorkbenchStoreError(
                "parent revision and fork stage must be provided together"
            )
        current_stage = self._stage(record.get("currentStage"), "current stage")
        state = self._string(record.get("state"), "revision state")
        if state not in {"pending", "active", "complete", "failed"}:
            raise WorkbenchStoreError(f"revision state is invalid: {state}")
        stale_from_stage = self._optional_stage(
            record.get("staleFromStage"), "stale stage"
        )
        return RevisionRecord(
            id=revision_id,
            run_root=run_root,
            parent_revision_id=parent_revision_id,
            fork_stage=fork_stage,
            current_stage=current_stage,
            state=state,
            stale_from_stage=stale_from_stage,
        )

    def _write_board(
        self,
        board: BoardRecord,
        *,
        publication: _PublicationState | None = None,
    ) -> None:
        manifest_path = self._manifest_path(board.id)
        board_root = manifest_path.parent
        value = {
            "activeRevisionId": board.active_revision_id,
            "id": board.id,
            "productName": board.product_name,
            "repositoryBoardId": board.repository_board_id,
            "repositoryVersionId": board.repository_version_id,
            "revisions": [
                {
                    "currentStage": revision.current_stage,
                    "forkStage": revision.fork_stage,
                    "id": revision.id,
                    "imported": revision.run_root
                    != self._confined(
                        board_root / "revisions" / revision.id / "run"
                    ),
                    "parentRevisionId": revision.parent_revision_id,
                    "runRoot": Path(
                        os.path.relpath(revision.run_root, board_root)
                    ).as_posix(),
                    "staleFromStage": revision.stale_from_stage,
                    "state": revision.state,
                }
                for revision in board.revisions
            ],
            "savedRevisionId": board.saved_revision_id,
            "schemaVersion": _SCHEMA_VERSION,
        }
        self._write_replaced_json(manifest_path, value, publication=publication)

    @staticmethod
    def _validate_repository_link(
        repository_board_id: object, repository_version_id: object
    ) -> None:
        if (repository_board_id is None) != (repository_version_id is None):
            raise WorkbenchStoreError(
                "repository board and version identifiers must be provided together"
            )
        if repository_board_id is None:
            return
        if (
            not isinstance(repository_board_id, str)
            or not _REPOSITORY_BOARD_ID.fullmatch(repository_board_id)
        ):
            raise WorkbenchStoreError("repository board identifier is invalid")
        if (
            not isinstance(repository_version_id, str)
            or not _REPOSITORY_VERSION_ID.fullmatch(repository_version_id)
        ):
            raise WorkbenchStoreError("repository version identifier is invalid")

    def _write_replaced_json(
        self,
        path: Path,
        value: object,
        *,
        publication: _PublicationState | None = None,
    ) -> None:
        path = self._confined(path)
        path.parent.mkdir(parents=True, exist_ok=True)
        descriptor, temporary_name = tempfile.mkstemp(
            prefix=f".{path.name}.tmp-", dir=path.parent
        )
        temporary_path = Path(temporary_name)
        try:
            with os.fdopen(descriptor, "w", encoding="utf-8") as stream:
                descriptor = -1
                json.dump(value, stream, indent=2, sort_keys=True)
                stream.write("\n")
                stream.flush()
                os.fsync(stream.fileno())
            os.replace(temporary_path, path)
            if publication is not None:
                publication.published = True
            self._fsync_directory(path.parent)
        finally:
            if descriptor >= 0:
                os.close(descriptor)
            temporary_path.unlink(missing_ok=True)

    def _write_new_json(self, path: Path, value: object) -> None:
        path = self._confined(path)
        descriptor, temporary_name = tempfile.mkstemp(
            prefix=f".{path.name}.tmp-", dir=path.parent
        )
        temporary_path = Path(temporary_name)
        try:
            with os.fdopen(descriptor, "w", encoding="utf-8") as stream:
                descriptor = -1
                json.dump(value, stream, indent=2, sort_keys=True)
                stream.write("\n")
                stream.flush()
                os.fsync(stream.fileno())
            try:
                os.link(temporary_path, path)
            except FileExistsError as error:
                raise WorkbenchStoreError(
                    f"draft already exists and will not be overwritten: {path.name}"
                ) from error
            self._fsync_directory(path.parent)
        finally:
            if descriptor >= 0:
                os.close(descriptor)
            temporary_path.unlink(missing_ok=True)

    def _manifest_path(self, board_id: str) -> Path:
        return self._confined(self._board_root(board_id) / "board.json")

    def _board_root(self, board_id: str) -> Path:
        self._validate_identifier(board_id, "board")
        return self._confined(self._boards_root / board_id)

    def _revision_root(self, board_id: str, revision_id: str) -> Path:
        self._validate_identifier(revision_id, "revision")
        return self._confined(
            self._board_root(board_id) / "revisions" / revision_id
        )

    def _confined(self, path: Path) -> Path:
        resolved = Path(path).resolve(strict=False)
        try:
            resolved.relative_to(self._workspace)
        except ValueError as error:
            raise WorkbenchStoreError(
                f"workbench path must stay inside workspace: {self._workspace}"
            ) from error
        return resolved

    @staticmethod
    def _validate_identifier(value: str, label: str) -> None:
        if not isinstance(value, str) or not _IDENTIFIER.fullmatch(value):
            raise WorkbenchStoreError(f"{label} identifier is invalid")

    @staticmethod
    def _next_numbered_id(
        root: Path,
        pattern: re.Pattern[str],
        prefix: str,
        *,
        suffix: str = "",
    ) -> str:
        numbers = [
            int(match.group(1))
            for entry in root.iterdir()
            if (match := pattern.fullmatch(entry.name)) is not None
        ]
        return f"{prefix}-{max(numbers, default=0) + 1:04d}{suffix}"

    @staticmethod
    def _revision(board: BoardRecord, revision_id: str) -> RevisionRecord:
        for revision in board.revisions:
            if revision.id == revision_id:
                return revision
        raise WorkbenchStoreError(f"revision does not exist: {revision_id}")

    @classmethod
    def _savable_revision(
        cls, board: BoardRecord, revision_id: str
    ) -> RevisionRecord:
        revision = cls._revision(board, revision_id)
        if revision.stale_from_stage is not None:
            raise WorkbenchStoreError(
                f"revision {revision.id} has a stale lineage from stage "
                f"{revision.stale_from_stage}"
            )
        if revision.state != "complete" or revision.current_stage != _FINAL_STAGE:
            raise WorkbenchStoreError(
                f"revision {revision.id} does not have a complete lineage"
            )
        return revision

    @staticmethod
    def _replace_revision(
        board: BoardRecord, updated: RevisionRecord
    ) -> BoardRecord:
        revisions = tuple(
            updated if revision.id == updated.id else revision
            for revision in board.revisions
        )
        return replace(board, revisions=revisions)

    @staticmethod
    def _mapping(value: object, label: str) -> Mapping[str, object]:
        if not isinstance(value, dict):
            raise WorkbenchStoreError(f"{label} must be an object")
        return value

    @staticmethod
    def _string(value: object, label: str, *, allow_empty: bool = False) -> str:
        if not isinstance(value, str) or (not allow_empty and not value):
            raise WorkbenchStoreError(f"{label} must be a string")
        return value

    @classmethod
    def _stage(cls, value: object, label: str) -> int:
        if isinstance(value, bool) or not isinstance(value, int):
            raise WorkbenchStoreError(f"{label} must be an integer")
        cls._validate_stage(value)
        return value

    @classmethod
    def _optional_stage(cls, value: object, label: str) -> int | None:
        return None if value is None else cls._stage(value, label)

    @staticmethod
    def _validate_stage(stage: object) -> None:
        if (
            isinstance(stage, bool)
            or not isinstance(stage, int)
            or stage < 0
            or stage > _FINAL_STAGE
        ):
            raise WorkbenchStoreError(
                f"stage must be between 0 and {_FINAL_STAGE}"
            )

    @staticmethod
    def _fsync_directory(directory: Path) -> None:
        descriptor = os.open(directory, os.O_RDONLY)
        try:
            os.fsync(descriptor)
        finally:
            os.close(descriptor)
