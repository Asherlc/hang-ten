from __future__ import annotations

from hashlib import sha256
from io import BytesIO
import json
from pathlib import Path

from PIL import Image
import pytest

from hangboard_vectorizer import source_cache
from hangboard_vectorizer.generic_stage0 import StageCheckpoint
from hangboard_vectorizer.onboard_cli import main as onboard_main
from hangboard_vectorizer.onboarding_run import (
    RunContext,
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


def _write_json(path: Path, value: object) -> None:
    path.write_text(json.dumps(value, sort_keys=True) + "\n", encoding="utf-8")


def _hash_file(path: Path) -> str:
    return sha256(path.read_bytes()).hexdigest()
