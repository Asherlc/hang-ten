from __future__ import annotations

from collections.abc import Mapping
from hashlib import sha256
from io import BytesIO
import json
from pathlib import Path

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
    assert parent.stale_from_stage is None


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


@pytest.mark.parametrize("source_kind", ("upload", "url"))
def test_failed_creation_rolls_back_metadata_without_removing_upload_before_cache(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    source_kind: str,
) -> None:
    runner = _FailAfterCacheRunner()
    service = WorkbenchService(WorkbenchStore(tmp_path), runners={0: runner})
    content = _fixture_image_bytes()
    if source_kind == "url":
        monkeypatch.setattr(
            source_cache,
            "_read_network",
            lambda locator, _limits: (content, locator),
        )

    with pytest.raises(RuntimeError, match="stage failure"):
        if source_kind == "upload":
            service.create_from_upload("Failed Upload", content)
        else:
            service.create_from_url(
                "Failed URL", "https://example.test/failed.png"
            )

    assert runner.saw_cached_source is True
    assert runner.saw_upload is (source_kind == "upload")
    assert list(tmp_path.rglob(".upload-*")) == []
    assert service.list_boards() == ()


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
    manifest = json.loads((cli_run / "run.json").read_text(encoding="utf-8"))
    manifest["pipeline"] = {
        "currentStage": 0,
        "nextAction": "retry-stage-1",
        "nextStage": 1,
        "status": "failed",
    }
    _write_json(cli_run / "run.json", manifest)
    prior_evidence = {
        path.relative_to(cli_run).as_posix(): path.read_bytes()
        for path in sorted((cli_run / "stages/00").rglob("*"))
        if path.is_file()
    }
    service = WorkbenchService(
        WorkbenchStore(tmp_path), runners=_stub_runners()
    )
    imported = service.import_run(cli_run)

    retried = service.retry(
        imported.board_id,
        expected_revision_id=imported.revision_id,
        expected_stage=0,
    )

    assert retried.run_root == cli_run
    assert retried.stage == 1
    assert retried.state == "awaiting_review"
    assert retried.review_path is not None
    assert "stages/01/attempt-0001" in retried.review_path.as_posix()
    assert {
        path.relative_to(cli_run).as_posix(): path.read_bytes()
        for path in sorted((cli_run / "stages/00").rglob("*"))
        if path.is_file()
    } == prior_evidence


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
            _write_json(regions, {"regions": []})
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
            _write_json(regions, {"regions": []})
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


def _write_json(path: Path, value: object) -> None:
    path.write_text(json.dumps(value, sort_keys=True) + "\n", encoding="utf-8")


def _hash_file(path: Path) -> str:
    return sha256(path.read_bytes()).hexdigest()
