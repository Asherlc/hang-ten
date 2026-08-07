from __future__ import annotations

from collections.abc import Mapping
from concurrent.futures import ThreadPoolExecutor
from hashlib import sha256
from io import BytesIO
import json
from pathlib import Path
from threading import Event
import tempfile

from PIL import Image
import pytest

from hangboard_vectorizer import source_cache
from hangboard_vectorizer.generic_stage0 import StageCheckpoint
from hangboard_vectorizer.models import ConversionError
from hangboard_vectorizer.onboard_cli import main as onboard_main
from hangboard_vectorizer.onboarding_run import (
    RunContext,
    approve_stage,
    cached_source_path,
    read_status,
    replace_pending_checkpoint,
    resume_run,
    start_run,
)
from hangboard_vectorizer.workbench import (
    WorkbenchService,
    WorkbenchServiceError,
    WorkbenchView,
)
from hangboard_vectorizer.workbench_store import WorkbenchStore, WorkbenchStoreError


@pytest.fixture
def service(tmp_path: Path) -> WorkbenchService:
    return WorkbenchService(WorkbenchStore(tmp_path), runners=_stub_runners())


@pytest.fixture
def board_with_stage0(service: WorkbenchService) -> WorkbenchView:
    return service.create_from_upload("Example Board", _fixture_image_bytes())


@pytest.fixture
def complete_board(
    service: WorkbenchService, board_with_stage0: WorkbenchView
) -> WorkbenchView:
    current = board_with_stage0
    for stage in range(5):
        current = service.approve_and_advance(
            current.board_id,
            expected_revision_id=current.revision_id,
            expected_stage=stage,
        )
    return service.save(
        current.board_id, expected_revision_id=current.revision_id
    )


def test_approve_and_advance_stops_at_next_review(
    service: WorkbenchService, board_with_stage0: WorkbenchView
) -> None:
    result = service.approve_and_advance(
        board_with_stage0.board_id, expected_stage=0
    )

    assert result.stage == 1
    assert result.state == "awaiting_review"
    assert result.review_path is not None
    assert result.review_path.name == "stage-1-review.png"
    revision = service.store.read_revision(result.board_id, result.revision_id)
    assert revision.current_stage == 1
    assert revision.state == "active"


def test_editable_stages_expose_a_clean_canvas_aligned_image_separate_from_review(
    service: WorkbenchService, board_with_stage0: WorkbenchView
) -> None:
    current = service.approve_and_advance(
        board_with_stage0.board_id, expected_stage=0
    )
    current = service.approve_and_advance(current.board_id, expected_stage=1)

    assert current.stage == 2
    assert current.editor_image_path is not None
    assert current.editor_image_path.name == "stage-1-auto-rgba.png"
    assert current.editor_image_path != current.review_path
    with Image.open(current.editor_image_path) as editor_image:
        assert editor_image.size == (4, 4)


def test_get_board_rejects_editable_artifact_canvas_mismatched_to_clean_image(
    service: WorkbenchService, board_with_stage0: WorkbenchView
) -> None:
    current = service.approve_and_advance(
        board_with_stage0.board_id, expected_stage=0
    )
    current = service.approve_and_advance(current.board_id, expected_stage=1)
    assert service.get_board(current.board_id).stage == 2

    manifest = json.loads(
        (current.run_root / "run.json").read_text(encoding="utf-8")
    )
    record = manifest["stages"][2]
    artifact_root = current.run_root / record["artifactRoot"]
    regions_path = artifact_root / "stage-2-regions.json"
    _write_json(
        regions_path,
        {"canvas": {"width": 5, "height": 4}, "regions": []},
    )
    candidate_path = artifact_root / "stage-2-candidate.json"
    candidate = json.loads(candidate_path.read_text(encoding="utf-8"))
    candidate["regions"]["fileSha256"] = _hash_file(regions_path)
    _write_json(candidate_path, candidate)
    _rehash_pending_checkpoint(current.run_root, manifest, record)

    with pytest.raises(
        WorkbenchServiceError, match="inconsistent editable evidence"
    ):
        service.get_board(current.board_id)


def test_get_board_rejects_editable_artifact_review_with_same_hash_as_clean_image(
    service: WorkbenchService, board_with_stage0: WorkbenchView
) -> None:
    current = service.approve_and_advance(
        board_with_stage0.board_id, expected_stage=0
    )
    current = service.approve_and_advance(current.board_id, expected_stage=1)
    assert current.editor_image_path is not None
    assert current.review_path is not None

    manifest = json.loads((current.run_root / "run.json").read_text(encoding="utf-8"))
    record = manifest["stages"][2]
    current.review_path.write_bytes(current.editor_image_path.read_bytes())
    record["reviewSha256"] = _hash_file(current.review_path)
    _rehash_pending_checkpoint(current.run_root, manifest, record)

    with pytest.raises(
        WorkbenchServiceError, match="inconsistent editable evidence"
    ):
        service.get_board(current.board_id)


def test_get_board_rejects_editable_artifact_replaced_between_status_and_evidence(
    service: WorkbenchService,
    board_with_stage0: WorkbenchView,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    current = service.approve_and_advance(
        board_with_stage0.board_id, expected_stage=0
    )
    current = service.approve_and_advance(current.board_id, expected_stage=1)
    manifest = json.loads((current.run_root / "run.json").read_text(encoding="utf-8"))
    replacement = _StubStageRunner(2).run(
        RunContext(current.run_root, manifest),
        tmp_path / "replacement-stage-2",
    )
    original_manifest = getattr(
        WorkbenchService, "_WorkbenchService__manifest"
    )
    replaced = False

    def replace_before_manifest_read(run_root: Path) -> dict[str, object]:
        nonlocal replaced
        if not replaced:
            replace_pending_checkpoint(run_root, replacement)
            replaced = True
        return original_manifest(run_root)

    monkeypatch.setattr(
        WorkbenchService,
        "_WorkbenchService__manifest",
        staticmethod(replace_before_manifest_read),
    )

    with pytest.raises(
        WorkbenchServiceError, match="inconsistent editable evidence"
    ):
        service.get_board(current.board_id)

    assert "attempt-0002" in str(read_status(current.run_root)["review"])


def test_get_board_converts_editor_image_decompression_bomb_to_safe_error(
    service: WorkbenchService,
    board_with_stage0: WorkbenchView,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    current = service.approve_and_advance(
        board_with_stage0.board_id, expected_stage=0
    )
    current = service.approve_and_advance(current.board_id, expected_stage=1)

    class BombingImageDecoder:
        DecompressionBombError = Image.DecompressionBombError

        @staticmethod
        def open(_path: Path) -> None:
            raise Image.DecompressionBombError(
                "decoded image exceeds safety limit"
            )

    monkeypatch.setattr(
        "hangboard_vectorizer.workbench.Image", BombingImageDecoder
    )

    with pytest.raises(
        WorkbenchServiceError, match="inconsistent editable evidence"
    ):
        service.get_board(current.board_id)


def test_revising_approved_stage_forks_revision_and_marks_old_descendants_stale(
    service: WorkbenchService, complete_board: WorkbenchView
) -> None:
    revised = service.revise_stage(complete_board.board_id, stage=2)

    assert revised.revision_id != complete_board.revision_id
    assert revised.parent_revision_id == complete_board.revision_id
    old = service.store.read_revision(
        complete_board.board_id, complete_board.revision_id
    )
    assert old.stale_from_stage == 2
    assert read_status(revised.run_root)["stage"] == 2


def test_revision_fork_replays_accepted_stage2_and_stage3_reviewed_edits(
    service: WorkbenchService,
    board_with_stage0: WorkbenchView,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        "hangboard_vectorizer.workbench.materialize_stage2_edit",
        lambda context, document, artifact_root: _materialize_reviewed_stub(
            2, context, document, artifact_root
        ),
    )
    monkeypatch.setattr(
        "hangboard_vectorizer.workbench.materialize_stage3_edit",
        lambda context, document, artifact_root: _materialize_reviewed_stub(
            3, context, document, artifact_root
        ),
    )
    current = service.approve_and_advance(
        board_with_stage0.board_id, expected_stage=0
    )
    current = service.approve_and_advance(current.board_id, expected_stage=1)
    stage2_document = _stage2_edit_document()
    assert isinstance(stage2_document, dict)
    stage2_document["replayMarker"] = "accepted-stage-2-edit"
    service.save_draft(
        current.board_id, stage2_document, expected_stage=2
    )
    current = service.approve_and_advance(current.board_id, expected_stage=2)
    stage3_document = _stage3_edit_document()
    assert isinstance(stage3_document, dict)
    stage3_document["replayMarker"] = "accepted-stage-3-edit"
    service.save_draft(
        current.board_id, stage3_document, expected_stage=3
    )
    current = service.approve_and_advance(current.board_id, expected_stage=3)
    complete = service.approve_and_advance(current.board_id, expected_stage=4)

    revised = service.revise_stage(complete.board_id, stage=4)
    manifest = json.loads(
        (revised.run_root / "run.json").read_text(encoding="utf-8")
    )
    stage2 = manifest["stages"][2]
    stage3 = manifest["stages"][3]
    replayed_stage2 = json.loads(
        (
            revised.run_root
            / stage2["artifactRoot"]
            / "stage-2-regions.json"
        ).read_text(encoding="utf-8")
    )
    replayed_stage3 = json.loads(
        (
            revised.run_root
            / stage3["artifactRoot"]
            / "stage-3-vector-regions.json"
        ).read_text(encoding="utf-8")
    )

    assert stage2["attempt"] == 2
    assert stage3["attempt"] == 2
    assert replayed_stage2["replayMarker"] == "accepted-stage-2-edit"
    assert replayed_stage3["replayMarker"] == "accepted-stage-3-edit"


def test_revision_replay_failure_does_not_mark_parent_lineage_stale(
    service: WorkbenchService,
    complete_board: WorkbenchView,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def fail_replay(
        _context: RunContext,
        _document: Mapping[str, object],
        _artifact_root: Path,
    ) -> StageCheckpoint:
        raise RuntimeError("replay interrupted")

    monkeypatch.setattr(
        "hangboard_vectorizer.workbench.materialize_stage2_edit", fail_replay
    )

    with pytest.raises(RuntimeError, match="replay interrupted"):
        service.revise_stage(complete_board.board_id, stage=3)

    parent = service.store.read_revision(
        complete_board.board_id, complete_board.revision_id
    )
    board = service.store.read_board(complete_board.board_id)
    child = board.revisions[-1]
    assert parent.stale_from_stage is None
    assert board.active_revision_id == parent.id
    assert child.parent_revision_id == parent.id
    assert child.state == "failed"
    assert child.run_root.is_dir()


def test_concurrent_initial_creation_exposes_no_pending_revision(
    tmp_path: Path,
) -> None:
    runner = _BlockingStageRunner(0)
    store = WorkbenchStore(tmp_path)
    service = WorkbenchService(store, runners={0: runner})

    with ThreadPoolExecutor(max_workers=1) as executor:
        future = executor.submit(
            service.create_from_upload,
            "Concurrent Board",
            _fixture_image_bytes(),
        )
        assert runner.entered.wait(timeout=5)
        board = store.list_boards()[0]
        try:
            assert board.active_revision_id == ""
            assert board.revisions[0].state == "pending"
            assert service.list_boards() == ()
            with pytest.raises(WorkbenchServiceError, match="no active revision"):
                service.get_board(board.id)
            with pytest.raises(WorkbenchServiceError, match="pending"):
                service.get_board(
                    board.id,
                    revision_id=board.revisions[0].id,
                )
            assert store.read_revision(
                board.id, board.revisions[0].id
            ).state == "pending"
        finally:
            runner.release.set()
        created = future.result(timeout=5)

    persisted = store.read_board(created.board_id)
    assert persisted.active_revision_id == created.revision_id
    assert [
        revision.id
        for revision in persisted.revisions
        if revision.state == "active"
    ] == [created.revision_id]


def test_concurrent_fork_replay_keeps_parent_active_until_child_is_usable(
    service: WorkbenchService,
    complete_board: WorkbenchView,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    entered = Event()
    release = Event()

    def block_replay(
        context: RunContext,
        document: Mapping[str, object],
        artifact_root: Path,
    ) -> StageCheckpoint:
        entered.set()
        if not release.wait(timeout=5):
            raise TimeoutError("replay was not released")
        return _materialize_reviewed_stub(2, context, document, artifact_root)

    monkeypatch.setattr(
        "hangboard_vectorizer.workbench.materialize_stage2_edit", block_replay
    )

    with ThreadPoolExecutor(max_workers=1) as executor:
        future = executor.submit(
            service.revise_stage,
            complete_board.board_id,
            stage=3,
        )
        assert entered.wait(timeout=5)
        try:
            board = service.store.read_board(complete_board.board_id)
            assert board.active_revision_id == complete_board.revision_id
            assert board.revisions[-1].state == "pending"
            assert service.get_board(complete_board.board_id) == complete_board
            assert service.list_boards() == (complete_board,)
            with pytest.raises(WorkbenchServiceError, match="pending"):
                service.get_board(
                    complete_board.board_id,
                    revision_id=board.revisions[-1].id,
                )
            assert service.store.read_revision(
                complete_board.board_id, board.revisions[-1].id
            ).state == "pending"
        finally:
            release.set()
        child = future.result(timeout=5)

    persisted = service.store.read_board(complete_board.board_id)
    records = {revision.id: revision for revision in persisted.revisions}
    assert persisted.active_revision_id == child.revision_id
    assert records[child.revision_id].state == "active"
    assert records[complete_board.revision_id].stale_from_stage == 3


def test_competing_fork_activation_failure_retains_failed_child_and_winner(
    service: WorkbenchService,
    complete_board: WorkbenchView,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    first_entered = Event()
    release_first = Event()
    replay_count = 0

    def block_first_replay(
        context: RunContext,
        document: Mapping[str, object],
        artifact_root: Path,
    ) -> StageCheckpoint:
        nonlocal replay_count
        replay_count += 1
        if replay_count == 1:
            first_entered.set()
            if not release_first.wait(timeout=5):
                raise TimeoutError("first replay was not released")
        return _materialize_reviewed_stub(2, context, document, artifact_root)

    monkeypatch.setattr(
        "hangboard_vectorizer.workbench.materialize_stage2_edit",
        block_first_replay,
    )

    with ThreadPoolExecutor(max_workers=1) as executor:
        losing_future = executor.submit(
            service.revise_stage,
            complete_board.board_id,
            stage=3,
        )
        assert first_entered.wait(timeout=5)
        winner = service.revise_stage(complete_board.board_id, stage=3)
        try:
            blocked = service.store.read_board(complete_board.board_id)
            assert blocked.active_revision_id == winner.revision_id
            assert blocked.revisions[1].state == "pending"
        finally:
            release_first.set()
        with pytest.raises(WorkbenchStoreError, match="active revision changed"):
            losing_future.result(timeout=5)

    persisted = service.store.read_board(complete_board.board_id)
    records = {revision.id: revision for revision in persisted.revisions}
    assert persisted.active_revision_id == winner.revision_id
    assert records[winner.revision_id].state == "active"
    assert records["revision-0002"].state == "failed"


def test_ui_created_run_is_inspectable_by_cli_status(
    service: WorkbenchService,
    capsys: pytest.CaptureFixture[str],
) -> None:
    created = service.create_from_upload("CLI-Compatible Board", _fixture_image_bytes())

    result = onboard_main(
        [
            "--output",
            str(created.run_root),
            "--workspace-root",
            str(created.run_root.parent),
            "--status",
        ]
    )

    payload = json.loads(capsys.readouterr().out)
    assert result == 0
    assert payload["stage"] == 0
    assert payload["status"] == "awaiting_approval"


def test_create_from_upload_caches_source_before_removing_temporary_file(
    service: WorkbenchService,
) -> None:
    content = _fixture_image_bytes()

    created = service.create_from_upload("Upload Board", content)

    assert cached_source_path(created.run_root).read_bytes() == content
    assert list(created.run_root.parent.glob(".upload-*")) == []


def test_failed_stage0_creation_remains_active_and_retries_from_cached_upload(
    tmp_path: Path,
) -> None:
    runner = _FailAfterCacheRunner()
    store = WorkbenchStore(tmp_path)
    service = WorkbenchService(store, runners={0: runner})
    content = _fixture_image_bytes()

    with pytest.raises(RuntimeError, match="stage failure"):
        service.create_from_upload("Failed Upload", content)

    assert runner.saw_cached_source is True
    assert runner.saw_upload is True
    assert list(tmp_path.rglob(".upload-*")) == []
    failed = service.list_boards()[0]
    board = store.read_board(failed.board_id)
    failure_log = (
        failed.run_root
        / "stages/00/attempt-0001/stage-0-failure.log"
    )
    evidence_before = failure_log.read_bytes()
    assert failed.stage == 0
    assert failed.state == "failed"
    assert board.active_revision_id == failed.revision_id
    assert cached_source_path(failed.run_root).read_bytes() == content

    retrying_service = WorkbenchService(
        store, runners={0: _StubStageRunner(0)}
    )
    retried = retrying_service.retry(
        failed.board_id,
        expected_revision_id=failed.revision_id,
        expected_stage=0,
    )

    assert retried.stage == 0
    assert retried.state == "awaiting_review"
    assert retried.review_path is not None
    assert "attempt-0002" in retried.review_path.as_posix()
    assert failure_log.read_bytes() == evidence_before


def test_failed_creation_before_source_cache_rolls_back_and_removes_upload(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    store = WorkbenchStore(tmp_path)
    service = WorkbenchService(store, runners={0: _StubStageRunner(0)})
    saw_upload = False

    def fail_before_cache(_source: str, destination: Path) -> None:
        nonlocal saw_upload
        saw_upload = any(destination.parent.parent.glob(".upload-*"))
        raise RuntimeError("cache interrupted")

    monkeypatch.setattr(
        "hangboard_vectorizer.onboarding_run.cache_source", fail_before_cache
    )

    with pytest.raises(RuntimeError, match="cache interrupted"):
        service.create_from_upload("Failed Upload", _fixture_image_bytes())

    assert saw_upload is True
    assert list(tmp_path.rglob(".upload-*")) == []
    assert store.list_boards() == ()


def test_initial_revision_reservation_failure_removes_the_empty_board(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    store = WorkbenchStore(tmp_path)
    service = WorkbenchService(store, runners={0: _StubStageRunner(0)})

    def fail_revision_reservation(
        _board_id: str,
        *,
        parent_revision_id: str | None = None,
        fork_stage: int | None = None,
    ) -> None:
        del parent_revision_id, fork_stage
        raise RuntimeError("revision reservation interrupted")

    monkeypatch.setattr(store, "create_revision", fail_revision_reservation)

    with pytest.raises(RuntimeError, match="revision reservation interrupted"):
        service.create_from_upload("Interrupted Board", _fixture_image_bytes())

    assert WorkbenchStore(tmp_path).list_boards() == ()
    assert list(tmp_path.rglob(".upload-*")) == []


def test_upload_staging_failure_removes_the_pending_board(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    store = WorkbenchStore(tmp_path)
    service = WorkbenchService(store, runners={0: _StubStageRunner(0)})
    original_mkstemp = tempfile.mkstemp

    def fail_upload_staging(*args: object, **kwargs: object) -> tuple[int, str]:
        if kwargs.get("prefix") == ".upload-":
            raise OSError("upload staging interrupted")
        return original_mkstemp(*args, **kwargs)

    monkeypatch.setattr(
        "hangboard_vectorizer.workbench.tempfile.mkstemp",
        fail_upload_staging,
    )

    with pytest.raises(OSError, match="upload staging interrupted"):
        service.create_from_upload("Interrupted Board", _fixture_image_bytes())

    assert WorkbenchStore(tmp_path).list_boards() == ()


@pytest.mark.parametrize("failed_publication", [1, 2], ids=["board", "revision"])
def test_initial_reservation_reconciles_post_replace_fsync_ambiguity(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    failed_publication: int,
) -> None:
    store = WorkbenchStore(tmp_path)
    service = WorkbenchService(store, runners={0: _StubStageRunner(0)})
    original_fsync = store._fsync_directory
    publications = 0

    def fail_selected_publication(directory: Path) -> None:
        nonlocal publications
        if directory.name.startswith("board-"):
            publications += 1
            if publications == failed_publication:
                raise OSError("manifest publication ambiguous")
        original_fsync(directory)

    monkeypatch.setattr(store, "_fsync_directory", fail_selected_publication)

    with pytest.raises(OSError, match="manifest publication ambiguous"):
        service.create_from_upload("Interrupted Board", _fixture_image_bytes())

    assert WorkbenchStore(tmp_path).list_boards() == ()
    assert list(tmp_path.rglob(".upload-*")) == []


def test_post_publication_creation_failure_preserves_failed_run_evidence(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    store = WorkbenchStore(tmp_path)
    service = WorkbenchService(store, runners=_stub_runners())

    monkeypatch.setattr(
        WorkbenchService,
        "_WorkbenchService__view",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(
            RuntimeError("view publication interrupted")
        ),
    )

    with pytest.raises(RuntimeError, match="view publication interrupted"):
        service.create_from_upload("Interrupted Board", _fixture_image_bytes())

    board = store.list_boards()[0]
    revision = board.revisions[0]
    assert board.active_revision_id == ""
    assert revision.state == "failed"
    assert revision.run_root.is_dir()


def test_import_rejects_an_outside_run_before_reading_its_manifest(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    workspace = tmp_path / "workspace"
    outside = tmp_path / "outside-run"
    outside.mkdir()
    service = WorkbenchService(WorkbenchStore(workspace), runners=_stub_runners())
    reads = []

    def record_read(run_root: Path):
        reads.append(run_root)
        raise AssertionError("outside run was read")

    monkeypatch.setattr("hangboard_vectorizer.workbench.read_status", record_read)

    with pytest.raises(WorkbenchStoreError, match="workspace"):
        service.import_run(outside)

    assert reads == []


def test_create_from_url_uses_shared_source_cache_without_network_in_tests(
    service: WorkbenchService, monkeypatch: pytest.MonkeyPatch
) -> None:
    content = _fixture_image_bytes()
    source = "https://example.test/board.png"
    monkeypatch.setattr(
        source_cache,
        "_read_network",
        lambda locator, _limits: (content, locator),
    )

    created = service.create_from_url("URL Board", source)

    evidence = json.loads(
        (created.run_root / "inputs/source.json").read_text(encoding="utf-8")
    )
    assert evidence["kind"] == "https"
    assert evidence["sanitizedLocator"] == source


def test_list_and_get_boards_return_the_active_revision_view(
    service: WorkbenchService, board_with_stage0: WorkbenchView
) -> None:
    listed = service.list_boards()

    assert [view.board_id for view in listed] == [board_with_stage0.board_id]
    assert service.get_board(board_with_stage0.board_id) == board_with_stage0


def test_optimistic_revision_mismatch_does_not_advance(
    service: WorkbenchService, board_with_stage0: WorkbenchView
) -> None:
    before = read_status(board_with_stage0.run_root)

    with pytest.raises(WorkbenchServiceError, match="expected revision"):
        service.approve_and_advance(
            board_with_stage0.board_id,
            expected_revision_id="revision-9999",
            expected_stage=0,
        )

    assert read_status(board_with_stage0.run_root) == before


def test_boolean_expected_stage_is_rejected_without_advancing(
    service: WorkbenchService, board_with_stage0: WorkbenchView
) -> None:
    before = read_status(board_with_stage0.run_root)

    with pytest.raises(WorkbenchServiceError, match="between 0 and 4"):
        service.approve_and_advance(
            board_with_stage0.board_id,
            expected_stage=False,
        )

    assert read_status(board_with_stage0.run_root) == before


def test_save_draft_is_immutable_and_published_before_approval(
    service: WorkbenchService,
    board_with_stage0: WorkbenchView,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    current = service.approve_and_advance(
        board_with_stage0.board_id, expected_stage=0
    )
    current = service.approve_and_advance(
        current.board_id,
        expected_revision_id=current.revision_id,
        expected_stage=1,
    )
    document = json.loads(
        (
            Path(__file__).parent
            / "data"
            / "stage-2-regions-edited.json"
        ).read_text(encoding="utf-8")
    )

    saved = service.save_draft(
        current.board_id,
        document,
        expected_revision_id=current.revision_id,
        expected_stage=2,
    )
    drafts = sorted(
        (current.run_root.parent / "drafts/stage-2").glob("draft-*.json")
    )
    monkeypatch.setattr(
        "hangboard_vectorizer.workbench.materialize_stage2_edit",
        lambda context, _document, artifact_root: _StubStageRunner(2).run(
            context, artifact_root
        ),
    )
    advanced = service.approve_and_advance(
        current.board_id,
        expected_revision_id=current.revision_id,
        expected_stage=2,
    )
    manifest = json.loads(
        (current.run_root / "run.json").read_text(encoding="utf-8")
    )

    assert saved.stage == 2
    assert [path.name for path in drafts] == ["draft-0001.json"]
    assert json.loads(drafts[0].read_text(encoding="utf-8")) == document
    assert manifest["stages"][2]["attempt"] == 2
    assert advanced.stage == 3


def test_geometry_conversion_errors_are_public_and_retain_the_region_id(
    service: WorkbenchService,
    board_with_stage0: WorkbenchView,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    current = service.approve_and_advance(board_with_stage0.board_id, expected_stage=0)
    current = service.approve_and_advance(current.board_id, expected_stage=1)
    service.save_draft(current.board_id, _stage2_edit_document(), expected_stage=2)
    monkeypatch.setattr(
        "hangboard_vectorizer.workbench.materialize_stage2_edit",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(
            ConversionError("Stage 2 region 7: contour is invalid")
        ),
    )

    with pytest.raises(
        WorkbenchServiceError, match=r"Stage 2 region 7: contour is invalid"
    ):
        service.approve_and_advance(current.board_id, expected_stage=2)


def test_approval_selects_latest_draft_by_numeric_identifier(
    service: WorkbenchService,
    board_with_stage0: WorkbenchView,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    current = service.approve_and_advance(
        board_with_stage0.board_id, expected_stage=0
    )
    current = service.approve_and_advance(
        current.board_id, expected_stage=1
    )
    older = _stage2_edit_document()
    newer = _stage2_edit_document()
    assert isinstance(older, dict)
    assert isinstance(newer, dict)
    older["draftSelection"] = "older"
    newer["draftSelection"] = "newer"
    drafts_root = current.run_root.parent / "drafts/stage-2"
    drafts_root.mkdir(parents=True)
    _write_json(drafts_root / "draft-9999.json", older)
    _write_json(drafts_root / "draft-10000.json", newer)

    def materialize_latest(
        context: RunContext, document: Mapping[str, object], artifact_root: Path
    ) -> StageCheckpoint:
        assert document["draftSelection"] == "newer"
        return _StubStageRunner(2).run(context, artifact_root)

    monkeypatch.setattr(
        "hangboard_vectorizer.workbench.materialize_stage2_edit",
        materialize_latest,
    )

    advanced = service.approve_and_advance(
        current.board_id,
        expected_revision_id=current.revision_id,
        expected_stage=2,
    )

    assert advanced.stage == 3


def test_retry_publishes_a_new_attempt_without_advancing(
    service: WorkbenchService, board_with_stage0: WorkbenchView
) -> None:
    retried = service.retry(
        board_with_stage0.board_id,
        expected_revision_id=board_with_stage0.revision_id,
        expected_stage=0,
    )

    assert retried.stage == 0
    assert retried.state == "awaiting_review"
    assert retried.review_path is not None
    assert "attempt-0002" in retried.review_path.as_posix()
    assert (
        board_with_stage0.run_root
        / "stages/00/attempt-0001/stage-0-review.png"
    ).is_file()


def test_retry_resumes_an_imported_failed_run_without_changing_prior_evidence(
    tmp_path: Path,
) -> None:
    source = tmp_path / "failed-source.png"
    source.write_bytes(_fixture_image_bytes())
    cli_run = tmp_path / "failed-cli-run"
    start_run(
        "Failed CLI Board",
        str(source),
        cli_run,
        runners=_stub_runners(),
        workspace_root=tmp_path,
    )
    approve_stage(cli_run, 0)
    with pytest.raises(RuntimeError, match="stage failure"):
        resume_run(cli_run, runners={1: _FailingStage1Runner()})
    prior_evidence = {
        path.relative_to(cli_run).as_posix(): path.read_bytes()
        for path in sorted((cli_run / "stages/00").rglob("*"))
        if path.is_file()
    }
    service = WorkbenchService(
        WorkbenchStore(tmp_path), runners=_stub_runners()
    )
    imported = service.import_run(cli_run)
    imported_record = service.store.read_revision(
        imported.board_id, imported.revision_id
    )

    assert imported_record.current_stage == 0
    assert imported_record.state == "failed"

    retried = service.retry(
        imported.board_id,
        expected_revision_id=imported.revision_id,
        expected_stage=0,
    )

    assert retried.run_root == cli_run
    assert retried.stage == 1
    assert retried.state == "awaiting_review"
    assert retried.review_path is not None
    assert "stages/01/attempt-0002" in retried.review_path.as_posix()
    assert {
        path.relative_to(cli_run).as_posix(): path.read_bytes()
        for path in sorted((cli_run / "stages/00").rglob("*"))
        if path.is_file()
    } == prior_evidence


@pytest.mark.parametrize("failed_stage", [3, 4], ids=["stage-3", "stage-4"])
def test_failed_late_stage_reopens_after_restart_and_retries(
    tmp_path: Path, failed_stage: int
) -> None:
    store = WorkbenchStore(tmp_path)
    failing_runners = _stub_runners()
    failing_runners[failed_stage] = _FailingStageRunner(failed_stage)
    service = WorkbenchService(store, runners=failing_runners)
    current = service.create_from_upload("Retry Board", _fixture_image_bytes())
    for stage in range(failed_stage - 1):
        current = service.approve_and_advance(
            current.board_id,
            expected_revision_id=current.revision_id,
            expected_stage=stage,
        )

    with pytest.raises(RuntimeError, match="stage failure"):
        service.approve_and_advance(
            current.board_id,
            expected_revision_id=current.revision_id,
            expected_stage=failed_stage - 1,
        )

    restarted = WorkbenchService(store, runners=_stub_runners())
    failed = restarted.get_board(current.board_id)
    assert failed.stage == failed_stage - 1
    assert failed.state == "failed"
    assert failed.review_path is None
    assert failed.editor_image_path is None
    assert failed.editor_mode is None

    retried = restarted.retry(
        failed.board_id,
        expected_revision_id=failed.revision_id,
        expected_stage=failed.stage,
    )
    assert retried.stage == failed_stage
    assert retried.state == "awaiting_review"
    assert retried.review_path is not None
    assert f"stages/{failed_stage:02d}/attempt-0002" in retried.review_path.as_posix()


def test_import_run_preserves_a_cli_root_and_lists_it(
    service: WorkbenchService, tmp_path: Path
) -> None:
    source = tmp_path / "cli-source.png"
    source.write_bytes(_fixture_image_bytes())
    cli_run = tmp_path / "cli-run"
    start_run(
        "CLI Board",
        str(source),
        cli_run,
        runners=_stub_runners(),
        workspace_root=tmp_path,
    )

    imported = service.import_run(cli_run)

    assert imported.run_root == cli_run
    assert service.get_board(imported.board_id).run_root == cli_run
    assert imported.board_id in {view.board_id for view in service.list_boards()}
    with pytest.raises(WorkbenchStoreError, match="already registered"):
        service.import_run(cli_run)


def test_imported_run_recovers_store_drafts_after_service_restart(
    service: WorkbenchService,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    source = tmp_path / "imported-source.png"
    source.write_bytes(_fixture_image_bytes())
    cli_run = tmp_path / "imported-run"
    start_run(
        "Imported Board",
        str(source),
        cli_run,
        runners=_stub_runners(),
        workspace_root=tmp_path,
    )
    current = service.import_run(cli_run)
    current = service.approve_and_advance(current.board_id, expected_stage=0)
    current = service.approve_and_advance(current.board_id, expected_stage=1)
    service.save_draft(
        current.board_id,
        _stage2_edit_document(),
        expected_revision_id=current.revision_id,
        expected_stage=2,
    )
    restarted = WorkbenchService(service.store, runners=_stub_runners())
    monkeypatch.setattr(
        "hangboard_vectorizer.workbench.materialize_stage2_edit",
        lambda context, _document, artifact_root: _StubStageRunner(2).run(
            context, artifact_root
        ),
    )

    restarted.approve_and_advance(
        current.board_id,
        expected_revision_id=current.revision_id,
        expected_stage=2,
    )
    manifest = json.loads((cli_run / "run.json").read_text(encoding="utf-8"))

    assert manifest["stages"][2]["attempt"] == 2


def test_save_rejects_an_incomplete_run_without_updating_local_selection(
    service: WorkbenchService, board_with_stage0: WorkbenchView
) -> None:
    with pytest.raises(WorkbenchServiceError, match="complete lineage"):
        service.save(
            board_with_stage0.board_id,
            expected_revision_id=board_with_stage0.revision_id,
        )

    assert service.store.read_board(board_with_stage0.board_id).saved_revision_id is None


def _fixture_image_bytes() -> bytes:
    stream = BytesIO()
    Image.new("RGB", (512, 256), (45, 65, 85)).save(stream, format="PNG")
    return stream.getvalue()


def _stub_runners() -> dict[int, _StubStageRunner]:
    return {stage: _StubStageRunner(stage) for stage in range(5)}


def _stage2_edit_document() -> object:
    return json.loads(
        (
            Path(__file__).parent
            / "data"
            / "stage-2-regions-edited.json"
        ).read_text(encoding="utf-8")
    )


def _stage3_edit_document() -> object:
    return json.loads(
        (
            Path(__file__).parent
            / "data"
            / "stage-3-vector-regions-edited.json"
        ).read_text(encoding="utf-8")
    )


def _materialize_reviewed_stub(
    stage: int,
    context: RunContext,
    document: Mapping[str, object],
    artifact_root: Path,
) -> StageCheckpoint:
    checkpoint = _StubStageRunner(stage).run(context, artifact_root)
    document_name = (
        "stage-2-regions.json"
        if stage == 2
        else "stage-3-vector-regions.json"
    )
    document_path = artifact_root / document_name
    _write_json(document_path, document)
    candidate_path = artifact_root / f"stage-{stage}-candidate.json"
    candidate = json.loads(candidate_path.read_text(encoding="utf-8"))
    field = "regions" if stage == 2 else "vectorRegions"
    candidate[field]["fileSha256"] = _hash_file(document_path)
    _write_json(candidate_path, candidate)
    hashes = {
        path.name: _hash_file(path)
        for path in sorted(artifact_root.iterdir())
        if path.is_file() and path.name != "candidate-hashes.json"
    }
    _write_json(artifact_root / "candidate-hashes.json", hashes)
    return StageCheckpoint(
        stage=stage,
        artifact_root=artifact_root,
        candidate_hashes=hashes,
        review_path=checkpoint.review_path,
        machine_passed=True,
    )


class _StubStageRunner:
    def __init__(self, stage: int) -> None:
        self.stage = stage

    def run(self, context: RunContext, artifact_root: Path) -> StageCheckpoint:
        artifact_root.mkdir(parents=True)
        review = artifact_root / f"stage-{self.stage}-review.png"
        Image.new("RGB", (4, 4), (120, 80, 40)).save(review)
        candidate = self._candidate(context, artifact_root)
        candidate_path = artifact_root / f"stage-{self.stage}-candidate.json"
        _write_json(candidate_path, candidate)
        hashes = {
            path.name: sha256(path.read_bytes()).hexdigest()
            for path in sorted(artifact_root.iterdir())
            if path.is_file()
        }
        _write_json(artifact_root / "candidate-hashes.json", hashes)
        return StageCheckpoint(
            stage=self.stage,
            artifact_root=artifact_root,
            candidate_hashes=hashes,
            review_path=review,
            machine_passed=True,
        )

    def _candidate(
        self, context: RunContext, artifact_root: Path
    ) -> dict[str, object]:
        candidate: dict[str, object] = {"profile": {}, "stage": self.stage}
        if self.stage == 0:
            candidate["registered"] = {}
            return candidate

        stages = context.manifest["stages"]
        assert isinstance(stages, list)
        upstream = stages[self.stage - 1]
        assert isinstance(upstream, dict)
        candidate["inputAcceptance"] = {
            "path": upstream["acceptancePath"],
            "sha256": upstream["acceptanceSha256"],
        }
        if self.stage == 1:
            registered = artifact_root / "stage-1-auto-rgba.png"
            Image.new("RGBA", (4, 4), (10, 20, 30, 255)).save(registered)
            candidate["registered"] = {"fileSha256": _hash_file(registered)}
        elif self.stage == 2:
            regions = artifact_root / "stage-2-regions.json"
            labels = artifact_root / "stage-2-labels.png"
            _write_json(
                regions,
                {"canvas": {"width": 4, "height": 4}, "regions": []},
            )
            Image.new("I;16", (4, 4), 0).save(labels)
            candidate.update(
                {
                    "regionCount": 0,
                    "regions": {"fileSha256": _hash_file(regions)},
                    "registered": {"fileSha256": _hash_file(labels)},
                }
            )
        elif self.stage == 3:
            regions = artifact_root / "stage-3-vector-regions.json"
            svg = artifact_root / "stage-3-vector.svg"
            _write_json(
                regions,
                {"canvas": {"width": 4, "height": 4}, "regions": []},
            )
            svg.write_text('<svg xmlns="http://www.w3.org/2000/svg"/>\n')
            candidate.update(
                {
                    "regionCount": 0,
                    "vectorRegions": {"fileSha256": _hash_file(regions)},
                    "vectorSvg": {"fileSha256": _hash_file(svg)},
                }
            )
        else:
            candidate["regionCount"] = 0
            for field, filename in (
                ("normal", "stage-4-normal.png"),
                ("productSvg", "stage-4-product.svg"),
                ("manifest", "stage-4-manifest.json"),
                ("highlights", "stage-4-highlights.json"),
            ):
                path = artifact_root / filename
                if path.suffix == ".png":
                    Image.new("RGB", (4, 4), (1, 2, 3)).save(path)
                elif path.suffix == ".svg":
                    path.write_text('<svg xmlns="http://www.w3.org/2000/svg"/>\n')
                else:
                    _write_json(path, {})
                candidate[field] = {"fileSha256": _hash_file(path)}
        return candidate


class _BlockingStageRunner(_StubStageRunner):
    def __init__(self, stage: int) -> None:
        super().__init__(stage)
        self.entered = Event()
        self.release = Event()

    def run(self, context: RunContext, artifact_root: Path) -> StageCheckpoint:
        self.entered.set()
        if not self.release.wait(timeout=5):
            raise TimeoutError("stage runner was not released")
        return super().run(context, artifact_root)


class _FailAfterCacheRunner:
    stage = 0

    def __init__(self) -> None:
        self.saw_cached_source = False
        self.saw_upload = False

    def run(self, context: RunContext, _artifact_root: Path) -> StageCheckpoint:
        source = context.manifest["source"]
        assert isinstance(source, Mapping)
        cached_path = source["cachedPath"]
        assert isinstance(cached_path, str)
        self.saw_cached_source = (context.root / cached_path).is_file()
        self.saw_upload = any(context.root.parent.glob(".upload-*"))
        raise RuntimeError("stage failure")


class _FailingStage1Runner:
    stage = 1

    def run(self, _context: RunContext, _artifact_root: Path) -> StageCheckpoint:
        raise RuntimeError("stage failure")


class _FailingStageRunner:
    def __init__(self, stage: int) -> None:
        self.stage = stage

    def run(self, _context: RunContext, _artifact_root: Path) -> StageCheckpoint:
        raise RuntimeError("stage failure")


def _write_json(path: Path, value: object) -> None:
    path.write_text(json.dumps(value, sort_keys=True) + "\n", encoding="utf-8")


def _hash_file(path: Path) -> str:
    return sha256(path.read_bytes()).hexdigest()


def _rehash_pending_checkpoint(
    run_root: Path,
    manifest: dict[str, object],
    record: dict[str, object],
) -> None:
    artifact_root = run_root / str(record["artifactRoot"])
    hashes = {
        path.name: _hash_file(path)
        for path in sorted(artifact_root.iterdir())
        if path.is_file() and path.name != "candidate-hashes.json"
    }
    hashes_path = artifact_root / "candidate-hashes.json"
    _write_json(hashes_path, hashes)
    record["candidateHashesSha256"] = _hash_file(hashes_path)
    _write_json(run_root / "run.json", manifest)
