"""Shared guided orchestration over CLI-compatible onboarding runs."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
import json
import os
from pathlib import Path
import shutil
import tempfile
from types import MappingProxyType
from urllib.parse import urlparse

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
from .review_edits import (
    materialize_stage2_edit,
    materialize_stage3_edit,
    validate_stage_edit,
)
from .workbench_store import BoardRecord, RevisionRecord, WorkbenchStore


_FINAL_STAGE = 4
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
        self.__start(board, revision, source_url)
        return self.__view(board.id, revision.id)

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
        cached = False
        try:
            with os.fdopen(descriptor, "wb") as stream:
                descriptor = -1
                stream.write(bytes(content))
                stream.flush()
                os.fsync(stream.fileno())
            self.__start(board, revision, str(upload))
            cached_source_path(revision.run_root)
            cached = True
        finally:
            if descriptor >= 0:
                os.close(descriptor)
            if cached:
                upload.unlink(missing_ok=True)
        return self.__view(board.id, revision.id)

    def import_run(self, run_root: Path) -> WorkbenchView:
        """Register a validated CLI run in place beneath the store workspace."""
        run_root = Path(run_root).resolve(strict=True)
        status = read_status(run_root)
        manifest = self.__manifest(run_root)
        product = manifest.get("product")
        if not isinstance(product, Mapping):
            raise WorkbenchServiceError("onboarding product identity is missing")
        product_name = product.get("assertedName")
        if not isinstance(product_name, str) or not product_name.strip():
            raise WorkbenchServiceError("onboarding product name is invalid")
        board, revision = self.store.register_run(product_name, run_root)
        if status["status"] == "complete":
            self.store.mark_revision_complete(board.id, revision.id)
        return self.__view(board.id, revision.id)

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
        validated = validate_stage_edit(expected_stage, document)
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

        resume_run(revision.run_root, runners=self.__runners)
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
        self.store.mark_descendants_stale(
            board.id, parent.id, from_stage=stage
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
        if status["status"] == "ready_for_next_stage":
            resume_run(revision.run_root, runners=self.__runners)
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
        review_value = status.get("review")
        review_path = (
            revision.run_root / review_value
            if isinstance(review_value, str)
            else None
        )
        editor_mode = "contour" if stage == 2 else "vector" if stage == 3 else None
        return WorkbenchView(
            board_id=board.id,
            revision_id=revision.id,
            parent_revision_id=revision.parent_revision_id,
            run_root=revision.run_root,
            product_name=board.product_name,
            stage=stage,
            state=_STATE_NAMES[raw_state],
            review_path=review_path,
            editor_mode=editor_mode,
            saved=board.saved_revision_id == revision.id,
            stale_from_stage=revision.stale_from_stage,
        )

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
        drafts = sorted(drafts_root.glob("draft-*.json"))
        if not drafts:
            return None
        latest = drafts[-1].resolve(strict=True)
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
        if stage == 2:
            if not isinstance(document, Mapping):
                raise WorkbenchServiceError("Stage 2 draft must be an object")
            return materialize_stage2_edit(context, document, artifact_root)
        if stage == 3:
            if not isinstance(document, Mapping):
                raise WorkbenchServiceError("Stage 3 draft must be an object")
            return materialize_stage3_edit(context, document, artifact_root)
        raise WorkbenchServiceError(
            "review drafts are supported only for Stage 2 and Stage 3"
        )

    __runners: Mapping[int, StageRunner]
