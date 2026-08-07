"""Shared guided orchestration over CLI-compatible onboarding runs."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from hashlib import sha256
import json
import os
from pathlib import Path
import re
import shutil
import tempfile
from types import MappingProxyType
from urllib.parse import urlparse

from PIL import Image

from .onboarding_run import (
    DEFAULT_STAGE_RUNNERS,
    RunContext,
    StageRunner,
    approve_stage,
    cached_source_path,
    read_status,
    replace_pending_checkpoint,
    resume_run,
    start_run,
)
from .models import ConversionError
from .review_edits import (
    materialize_stage2_edit,
    materialize_stage3_edit,
    validate_stage_edit,
)
from .workbench_store import BoardRecord, RevisionRecord, WorkbenchStore


_FINAL_STAGE = 4
_DRAFT_FILE = re.compile(r"draft-(\d+)\.json\Z")
_STATE_NAMES = {
    "awaiting_approval": "awaiting_review",
    "complete": "complete",
    "failed": "failed",
    "ready_for_next_stage": "ready",
    "running": "running",
}


@dataclass(frozen=True, slots=True)
class WorkbenchView:
    board_id: str
    revision_id: str
    parent_revision_id: str | None
    run_root: Path
    product_name: str
    stage: int
    state: str
    review_path: Path | None
    editor_image_path: Path | None
    editor_mode: str | None
    saved: bool
    stale_from_stage: int | None


class WorkbenchServiceError(ValueError):
    """Raised when a guided workflow operation is inconsistent or unsupported."""


class WorkbenchService:
    """Coordinate persistent board metadata and the shared onboarding state machine."""

    def __init__(
        self,
        store: WorkbenchStore,
        *,
        runners: Mapping[int, StageRunner] | None = None,
    ) -> None:
        self.store = store
        self.__runners = MappingProxyType(
            dict(DEFAULT_STAGE_RUNNERS if runners is None else runners)
        )

    def create_from_url(self, product_name: str, source_url: str) -> WorkbenchView:
        """Create a board from one public HTTP(S) source URL."""
        if not isinstance(source_url, str) or urlparse(source_url).scheme.lower() not in {
            "http",
            "https",
        }:
            raise WorkbenchServiceError("source URL must use HTTP(S)")
        board = self.store.create_board(product_name)
        revision = self.store.create_revision(board.id)
        try:
            self.__start(board, revision, source_url)
            self.store.activate_revision(board.id, revision.id)
            return self.__view(board.id, revision.id)
        except Exception:
            self.__record_failed_creation(board, revision)
            raise

    def create_from_upload(
        self, product_name: str, content: bytes | bytearray | memoryview
    ) -> WorkbenchView:
        """Create a board from uploaded image bytes without retaining the upload."""
        if not isinstance(content, (bytes, bytearray, memoryview)) or not content:
            raise WorkbenchServiceError("upload content must not be empty")
        board = self.store.create_board(product_name)
        revision = self.store.create_revision(board.id)
        descriptor, temporary_name = tempfile.mkstemp(
            prefix=".upload-", suffix=".image", dir=revision.run_root.parent
        )
        upload = Path(temporary_name)
        remove_upload = False
        try:
            with os.fdopen(descriptor, "wb") as stream:
                descriptor = -1
                stream.write(bytes(content))
                stream.flush()
                os.fsync(stream.fileno())
            self.__start(board, revision, str(upload))
            cached_source_path(revision.run_root)
            self.store.activate_revision(board.id, revision.id)
            remove_upload = True
            return self.__view(board.id, revision.id)
        except Exception:
            self.__record_failed_creation(board, revision)
            remove_upload = True
            raise
        finally:
            if descriptor >= 0:
                os.close(descriptor)
            if remove_upload:
                upload.unlink(missing_ok=True)

    def import_run(self, run_root: Path) -> WorkbenchView:
        """Register a validated CLI run in place beneath the store workspace."""
        run_root = self.store.resolve_import_run(run_root)
        status = read_status(run_root)
        manifest = self.__manifest(run_root)
        product = manifest.get("product")
        if not isinstance(product, Mapping):
            raise WorkbenchServiceError("onboarding product identity is missing")
        product_name = product.get("assertedName")
        if not isinstance(product_name, str) or not product_name.strip():
            raise WorkbenchServiceError("onboarding product name is invalid")
        board, revision = self.store.register_run(product_name, run_root)
        try:
            if status["status"] == "complete":
                self.store.mark_revision_complete(board.id, revision.id)
            return self.__view(board.id, revision.id)
        except Exception:
            self.store.mark_revision_failed(
                board.id,
                revision.id,
                restore_active_revision_id="",
            )
            raise

    def list_boards(self) -> tuple[WorkbenchView, ...]:
        """Return active revision views for all persisted boards."""
        return tuple(
            self.__view(board.id, board.active_revision_id)
            for board in self.store.list_boards()
            if board.active_revision_id
        )

    def get_board(
        self, board_id: str, *, revision_id: str | None = None
    ) -> WorkbenchView:
        """Return one active or explicitly selected revision view."""
        board = self.store.read_board(board_id)
        selected = board.active_revision_id if revision_id is None else revision_id
        if not selected:
            raise WorkbenchServiceError(f"board {board.id} has no active revision")
        return self.__view(board.id, selected)

    def save_draft(
        self,
        board_id: str,
        document: object,
        *,
        expected_stage: int,
        expected_revision_id: str | None = None,
    ) -> WorkbenchView:
        """Validate and append an immutable draft for the pending editor stage."""
        board, revision, status = self.__expected_checkpoint(
            board_id,
            expected_revision_id=expected_revision_id,
            expected_stage=expected_stage,
        )
        if status["status"] != "awaiting_approval":
            raise WorkbenchServiceError(
                f"stage {expected_stage} is not awaiting review"
            )
        if expected_stage not in (2, 3):
            raise WorkbenchServiceError(
                "review drafts are supported only for Stage 2 and Stage 3"
            )
        try:
            validated = validate_stage_edit(expected_stage, document)
        except ConversionError as error:
            raise self.__public_geometry_error(error) from error
        self.store.write_draft(
            board.id, revision.id, expected_stage, validated
        )
        return self.__view(board.id, revision.id)

    def approve_and_advance(
        self,
        board_id: str,
        *,
        expected_stage: int,
        expected_revision_id: str | None = None,
    ) -> WorkbenchView:
        """Approve one selected checkpoint and stop at the next review."""
        board, revision, status = self.__expected_checkpoint(
            board_id,
            expected_revision_id=expected_revision_id,
            expected_stage=expected_stage,
        )
        if status["status"] != "awaiting_approval":
            raise WorkbenchServiceError(
                f"stage {expected_stage} is not awaiting review"
            )

        self.__publish_latest_draft(board.id, revision, expected_stage)
        approved = approve_stage(revision.run_root, expected_stage)
        if approved["status"] == "complete":
            self.store.mark_revision_complete(board.id, revision.id)
            return self.__view(board.id, revision.id)

        try:
            resume_run(revision.run_root, runners=self.__runners)
        except Exception:
            self.__synchronize_revision(board.id, revision.id)
            raise
        return self.__view(board.id, revision.id)

    def revise_stage(
        self,
        board_id: str,
        *,
        stage: int,
        expected_revision_id: str | None = None,
    ) -> WorkbenchView:
        """Fork an approved lineage and stop at a fresh upstream checkpoint."""
        self.__validate_stage(stage)
        board, parent = self.__active_revision(
            board_id, expected_revision_id=expected_revision_id
        )
        manifest = self.__manifest(parent.run_root)
        stages = manifest.get("stages")
        if not isinstance(stages, list) or stage >= len(stages):
            raise WorkbenchServiceError(f"stage {stage} has not been generated")
        selected = stages[stage]
        if not isinstance(selected, dict) or selected.get("status") != "approved":
            raise WorkbenchServiceError(f"stage {stage} has not been approved")

        source = cached_source_path(parent.run_root)
        revision = self.store.create_revision(
            board.id, parent_revision_id=parent.id, fork_stage=stage
        )
        try:
            self.__start(board, revision, str(source))
            for accepted_stage in range(stage):
                if accepted_stage in (2, 3):
                    self.__replay_reviewed_edit(
                        source_revision=parent,
                        target_revision=revision,
                        stage=accepted_stage,
                    )
                approve_stage(revision.run_root, accepted_stage)
                resume_run(revision.run_root, runners=self.__runners)
        except Exception:
            self.store.mark_revision_failed(
                board.id,
                revision.id,
                restore_active_revision_id=parent.id,
            )
            raise
        self.store.activate_revision(
            board.id,
            revision.id,
            stale_parent_revision_id=parent.id,
            stale_from_stage=stage,
        )
        return self.__view(board.id, revision.id)

    def retry(
        self,
        board_id: str,
        *,
        expected_stage: int,
        expected_revision_id: str | None = None,
    ) -> WorkbenchView:
        """Regenerate the selected checkpoint as a new immutable attempt."""
        _board, revision, status = self.__expected_checkpoint(
            board_id,
            expected_revision_id=expected_revision_id,
            expected_stage=expected_stage,
        )
        if status["status"] in {"ready_for_next_stage", "failed"}:
            try:
                resume_run(revision.run_root, runners=self.__runners)
            except Exception:
                self.__synchronize_revision(board_id, revision.id)
                raise
            return self.__view(board_id, revision.id)
        if status["status"] != "awaiting_approval":
            raise WorkbenchServiceError(
                f"stage {expected_stage} cannot be retried from {status['status']}"
            )
        runner = self.__runners.get(expected_stage)
        if runner is None or runner.stage != expected_stage:
            raise WorkbenchServiceError(
                f"Stage {expected_stage} runner is not installed"
            )
        temporary_root = Path(
            tempfile.mkdtemp(
                prefix=f".stage-{expected_stage}-retry-",
                dir=revision.run_root.parent,
            )
        )
        try:
            checkpoint = runner.run(
                RunContext(
                    revision.run_root,
                    MappingProxyType(self.__manifest(revision.run_root)),
                ),
                temporary_root / "artifacts",
            )
            replace_pending_checkpoint(revision.run_root, checkpoint)
        finally:
            shutil.rmtree(temporary_root, ignore_errors=True)
        return self.__view(board_id, revision.id)

    def save(
        self, board_id: str, *, expected_revision_id: str | None = None
    ) -> WorkbenchView:
        """Select a complete, non-stale revision in the local store."""
        board, revision = self.__active_revision(
            board_id, expected_revision_id=expected_revision_id
        )
        status = read_status(revision.run_root)
        if status["status"] != "complete" or status["stage"] != _FINAL_STAGE:
            raise WorkbenchServiceError(
                f"revision {revision.id} does not have a complete lineage"
            )
        self.store.mark_revision_complete(board.id, revision.id)
        self.store.save_revision(board.id, revision.id)
        return self.__view(board.id, revision.id)

    def __start(
        self, board: BoardRecord, revision: RevisionRecord, source: str
    ) -> None:
        start_run(
            board.product_name,
            source,
            revision.run_root,
            runners=self.__runners,
            workspace_root=revision.run_root.parent,
        )

    def __record_failed_creation(
        self, board: BoardRecord, revision: RevisionRecord
    ) -> None:
        if revision.run_root.exists():
            if read_status(revision.run_root)["status"] == "failed":
                self.store.mark_revision_failed(
                    board.id,
                    revision.id,
                    restore_active_revision_id=revision.id,
                )
                return
            self.store.mark_revision_failed(
                board.id,
                revision.id,
                restore_active_revision_id="",
            )
            return
        self.store._discard_unstarted_board(board.id, revision.id)

    def __expected_checkpoint(
        self,
        board_id: str,
        *,
        expected_revision_id: str | None,
        expected_stage: int,
    ) -> tuple[BoardRecord, RevisionRecord, Mapping[str, object]]:
        self.__validate_stage(expected_stage)
        board, revision = self.__active_revision(
            board_id, expected_revision_id=expected_revision_id
        )
        status = read_status(revision.run_root)
        if status["stage"] != expected_stage:
            raise WorkbenchServiceError(
                f"expected stage {expected_stage}, found stage {status['stage']}"
            )
        return board, revision, status

    @staticmethod
    def __validate_stage(stage: object) -> None:
        if (
            isinstance(stage, bool)
            or not isinstance(stage, int)
            or not 0 <= stage <= _FINAL_STAGE
        ):
            raise WorkbenchServiceError(
                f"stage must be between 0 and {_FINAL_STAGE}"
            )

    def __active_revision(
        self, board_id: str, *, expected_revision_id: str | None
    ) -> tuple[BoardRecord, RevisionRecord]:
        board = self.store.read_board(board_id)
        if not board.active_revision_id:
            raise WorkbenchServiceError(f"board {board.id} has no active revision")
        if (
            expected_revision_id is not None
            and expected_revision_id != board.active_revision_id
        ):
            raise WorkbenchServiceError(
                f"expected revision {expected_revision_id}, found revision "
                f"{board.active_revision_id}"
            )
        revision = self.store.read_revision(board.id, board.active_revision_id)
        return board, revision

    def __view(self, board_id: str, revision_id: str) -> WorkbenchView:
        board = self.store.read_board(board_id)
        revision = self.store.read_revision(board.id, revision_id)
        status = read_status(revision.run_root)
        stage = status["stage"]
        if isinstance(stage, bool) or not isinstance(stage, int):
            raise WorkbenchServiceError("onboarding status stage is invalid")
        raw_state = status["status"]
        if not isinstance(raw_state, str) or raw_state not in _STATE_NAMES:
            raise WorkbenchServiceError("onboarding status state is invalid")
        revision = self.store.synchronize_revision(
            board.id,
            revision.id,
            current_stage=stage,
            state=self.__stored_state(raw_state),
        )
        board = self.store.read_board(board.id)
        review_value = status.get("review")
        editor_mode = "contour" if stage == 2 else "vector" if stage == 3 else None
        if stage in (2, 3):
            review_path, editor_image_path = self.__editable_artifacts(
                revision, stage, review_value
            )
        else:
            review_path = (
                revision.run_root / review_value
                if isinstance(review_value, str)
                else None
            )
            editor_image_path = None
        return WorkbenchView(
            board_id=board.id,
            revision_id=revision.id,
            parent_revision_id=revision.parent_revision_id,
            run_root=revision.run_root,
            product_name=board.product_name,
            stage=stage,
            state=_STATE_NAMES[raw_state],
            review_path=review_path,
            editor_image_path=editor_image_path,
            editor_mode=editor_mode,
            saved=board.saved_revision_id == revision.id,
            stale_from_stage=revision.stale_from_stage,
        )

    def __synchronize_revision(
        self, board_id: str, revision_id: str
    ) -> RevisionRecord:
        status = read_status(self.store.read_revision(board_id, revision_id).run_root)
        stage = status.get("stage")
        raw_state = status.get("status")
        if isinstance(stage, bool) or not isinstance(stage, int):
            raise WorkbenchServiceError("onboarding status stage is invalid")
        if not isinstance(raw_state, str) or raw_state not in _STATE_NAMES:
            raise WorkbenchServiceError("onboarding status state is invalid")
        return self.store.synchronize_revision(
            board_id,
            revision_id,
            current_stage=stage,
            state=self.__stored_state(raw_state),
        )

    @staticmethod
    def __stored_state(raw_state: str) -> str:
        if raw_state == "complete":
            return "complete"
        if raw_state == "failed":
            return "failed"
        return "active"

    def __editor_image_path(
        self,
        revision: RevisionRecord,
        stage: int,
        manifest: Mapping[str, object],
    ) -> Path | None:
        if stage not in (2, 3):
            return None
        stages = manifest.get("stages")
        if not isinstance(stages, list) or len(stages) <= 1:
            raise WorkbenchServiceError("clean editor image evidence is missing")
        stage1 = stages[1]
        if not isinstance(stage1, Mapping) or stage1.get("status") != "approved":
            raise WorkbenchServiceError("clean editor image evidence is missing")
        acceptance_path = self.__confined_run_path(
            revision.run_root, stage1.get("acceptancePath")
        )
        acceptance = self.__read_object(
            acceptance_path, "Stage 1 acceptance evidence"
        )
        registered = acceptance.get("registered")
        if not isinstance(registered, Mapping):
            raise WorkbenchServiceError("clean editor image evidence is missing")
        image_path = self.__confined_run_path(
            revision.run_root, registered.get("path")
        )
        expected_hash = registered.get("fileSha256")
        if (
            not isinstance(expected_hash, str)
            or sha256(image_path.read_bytes()).hexdigest() != expected_hash
        ):
            raise WorkbenchServiceError("clean editor image evidence changed")
        return image_path

    def __editable_artifacts(
        self,
        revision: RevisionRecord,
        stage: int,
        review_value: object,
    ) -> tuple[Path, Path]:
        try:
            manifest = self.__manifest(revision.run_root)
            stages = manifest.get("stages")
            if not isinstance(stages, list) or len(stages) <= stage:
                raise ValueError("editable stage evidence is missing")
            record = stages[stage]
            # Validated status paths contain the immutable attempt root. A changed
            # review path means replacement selected another checkpoint snapshot.
            if (
                not isinstance(record, Mapping)
                or record.get("stage") != stage
                or record.get("status") != "review_pending"
                or record.get("reviewPath") != review_value
            ):
                raise ValueError("editable checkpoint identity changed")
            editor_path = self.__editor_image_path(
                revision, stage, manifest
            )
            if editor_path is None:
                raise ValueError("editor image is missing")
            review_path = self.__confined_run_path(
                revision.run_root, record.get("reviewPath")
            )
            document = self.__editable_document(revision, stage, record)
            canvas = document.get("canvas")
            if not isinstance(canvas, Mapping):
                raise ValueError("geometry canvas is missing")
            width = canvas.get("width")
            height = canvas.get("height")
            if (
                isinstance(width, bool)
                or not isinstance(width, int)
                or width <= 0
                or isinstance(height, bool)
                or not isinstance(height, int)
                or height <= 0
            ):
                raise ValueError("geometry canvas is invalid")
            with Image.open(editor_path) as editor_image:
                editor_image.load()
                image_size = editor_image.size
            editor_hash = sha256(editor_path.read_bytes()).hexdigest()
            review_hash = sha256(review_path.read_bytes()).hexdigest()
            if (
                image_size != (width, height)
                or editor_path == review_path
                or editor_hash == review_hash
            ):
                raise ValueError("editable artifacts do not align")
            return review_path, editor_path
        except (
            Image.DecompressionBombError,
            OSError,
            RuntimeError,
            SyntaxError,
            TypeError,
            ValueError,
        ) as error:
            raise WorkbenchServiceError(
                "inconsistent editable evidence"
            ) from error

    def __editable_document(
        self,
        revision: RevisionRecord,
        stage: int,
        record: Mapping[str, object],
    ) -> dict[str, object]:
        filename = (
            "stage-2-regions.json"
            if stage == 2
            else "stage-3-vector-regions.json"
        )
        artifact_root = record.get("artifactRoot")
        if not isinstance(artifact_root, str):
            raise ValueError("editable artifact root is invalid")
        document_path = self.__confined_run_path(
            revision.run_root, f"{artifact_root}/{filename}"
        )
        hashes_path = self.__confined_run_path(
            revision.run_root, record.get("candidateHashesPath")
        )
        hashes = self.__read_object(hashes_path, "editable candidate hashes")
        expected_hash = hashes.get(filename)
        if (
            not isinstance(expected_hash, str)
            or sha256(document_path.read_bytes()).hexdigest() != expected_hash
        ):
            raise ValueError("editable geometry is not hash-bound")
        return self.__read_object(document_path, "editable geometry")

    @staticmethod
    def __confined_run_path(run_root: Path, relative: object) -> Path:
        if not isinstance(relative, str) or not relative or Path(relative).is_absolute():
            raise WorkbenchServiceError("onboarding artifact path is invalid")
        try:
            root = run_root.resolve(strict=True)
            path = (root / relative).resolve(strict=True)
            path.relative_to(root)
        except (OSError, RuntimeError, ValueError) as error:
            raise WorkbenchServiceError("onboarding artifact path is invalid") from error
        if not path.is_file():
            raise WorkbenchServiceError("onboarding artifact is missing")
        return path

    @staticmethod
    def __read_object(path: Path, label: str) -> dict[str, object]:
        try:
            value = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as error:
            raise WorkbenchServiceError(f"{label} is invalid") from error
        if not isinstance(value, dict):
            raise WorkbenchServiceError(f"{label} is invalid")
        return value

    def __publish_latest_draft(
        self, board_id: str, revision: RevisionRecord, stage: int
    ) -> None:
        draft = self.__latest_draft(board_id, revision, stage)
        if draft is None:
            return
        document = json.loads(draft.read_text(encoding="utf-8"))
        temporary_root = Path(
            tempfile.mkdtemp(
                prefix=f".stage-{stage}-edit-", dir=revision.run_root.parent
            )
        )
        try:
            checkpoint = self.__materialize_edit(
                revision, stage, document, temporary_root / "artifacts"
            )
            replace_pending_checkpoint(revision.run_root, checkpoint)
        finally:
            shutil.rmtree(temporary_root, ignore_errors=True)

    def __latest_draft(
        self, board_id: str, revision: RevisionRecord, stage: int
    ) -> Path | None:
        revision_root = self.store._revision_root(
            board_id, revision.id
        ).resolve(strict=True)
        drafts_root = (
            revision_root / "drafts" / f"stage-{stage}"
        ).resolve(strict=False)
        try:
            drafts_root.relative_to(revision_root)
        except ValueError as error:
            raise WorkbenchServiceError("draft path escapes its revision") from error
        if not drafts_root.is_dir():
            return None
        drafts = [
            (int(match.group(1)), path)
            for path in drafts_root.iterdir()
            if path.is_file()
            and (match := _DRAFT_FILE.fullmatch(path.name)) is not None
        ]
        if not drafts:
            return None
        latest = max(drafts, key=lambda item: item[0])[1].resolve(strict=True)
        try:
            latest.relative_to(revision_root)
        except ValueError as error:
            raise WorkbenchServiceError("draft path escapes its revision") from error
        return latest

    def __replay_reviewed_edit(
        self,
        *,
        source_revision: RevisionRecord,
        target_revision: RevisionRecord,
        stage: int,
    ) -> None:
        source_manifest = self.__manifest(source_revision.run_root)
        stages = source_manifest["stages"]
        assert isinstance(stages, list)
        record = stages[stage]
        assert isinstance(record, dict)
        artifact_value = record.get("artifactRoot")
        if not isinstance(artifact_value, str):
            raise WorkbenchServiceError(
                f"stage {stage} artifact root is invalid"
            )
        filename = (
            "stage-2-regions.json"
            if stage == 2
            else "stage-3-vector-regions.json"
        )
        document_path = (source_revision.run_root / artifact_value / filename).resolve(
            strict=True
        )
        try:
            document_path.relative_to(source_revision.run_root.resolve(strict=True))
        except ValueError as error:
            raise WorkbenchServiceError(
                f"stage {stage} replay document escapes its run"
            ) from error
        document = json.loads(document_path.read_text(encoding="utf-8"))
        temporary_root = Path(
            tempfile.mkdtemp(
                prefix=f".stage-{stage}-replay-", dir=target_revision.run_root.parent
            )
        )
        try:
            checkpoint = self.__materialize_edit(
                target_revision, stage, document, temporary_root / "artifacts"
            )
            replace_pending_checkpoint(target_revision.run_root, checkpoint)
        finally:
            shutil.rmtree(temporary_root, ignore_errors=True)

    @staticmethod
    def __manifest(run_root: Path) -> dict[str, object]:
        value = json.loads((run_root / "run.json").read_text(encoding="utf-8"))
        if not isinstance(value, dict):
            raise WorkbenchServiceError("onboarding manifest must be an object")
        return value

    @staticmethod
    def __materialize_edit(
        revision: RevisionRecord,
        stage: int,
        document: object,
        artifact_root: Path,
    ):
        manifest = WorkbenchService.__manifest(revision.run_root)
        context = RunContext(revision.run_root, MappingProxyType(manifest))
        try:
            if stage == 2:
                if not isinstance(document, Mapping):
                    raise WorkbenchServiceError("Stage 2 draft must be an object")
                return materialize_stage2_edit(context, document, artifact_root)
            if stage == 3:
                if not isinstance(document, Mapping):
                    raise WorkbenchServiceError("Stage 3 draft must be an object")
                return materialize_stage3_edit(context, document, artifact_root)
        except ConversionError as error:
            raise WorkbenchService.__public_geometry_error(error) from error
        raise WorkbenchServiceError(
            "review drafts are supported only for Stage 2 and Stage 3"
        )

    @staticmethod
    def __public_geometry_error(error: ConversionError) -> WorkbenchServiceError:
        message = str(error).strip()
        if (
            re.match(r"^Stage [23] region \d+: ", message)
            and len(message) <= 500
            and "/" not in message
            and "\\" not in message
        ):
            return WorkbenchServiceError(message)
        return WorkbenchServiceError("review geometry is invalid")

    __runners: Mapping[int, StageRunner]
