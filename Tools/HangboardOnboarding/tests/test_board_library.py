from __future__ import annotations

from hashlib import sha256
import json
from pathlib import Path

from PIL import Image
import pytest

from hangboard_vectorizer.board_library import BoardLibraryError, RepositoryBoardLibrary
from hangboard_vectorizer.generic_stage0 import StageCheckpoint
from hangboard_vectorizer.onboarding_run import (
    RunContext,
    approve_stage,
    read_status,
    resume_run,
    start_run,
)


def test_snapshot_discovers_self_describing_runs_and_sorts_them(tmp_path: Path) -> None:
    _complete_board(tmp_path, "charlie", "charlie")
    _complete_board(tmp_path, "alpha-2", "Alpha 2")
    _complete_board(tmp_path, "alpha-1", "alpha 1")

    snapshot = RepositoryBoardLibrary(tmp_path).snapshot()

    assert [board.board_id for board in snapshot.boards] == [
        "alpha-1",
        "alpha-2",
        "charlie",
    ]
    assert snapshot.diagnostics == ()
    assert all(len(board.revision_token) == 64 for board in snapshot.boards)


def test_invalid_board_is_diagnostic_without_hiding_valid_boards(tmp_path: Path) -> None:
    _complete_board(tmp_path, "valid-board", "Valid Board")
    invalid = _complete_board(tmp_path, "wrong-directory", "Wrong Directory")
    manifest = _read_json(invalid / "run.json")
    product = manifest["product"]
    assert isinstance(product, dict)
    product["key"] = "different-key"
    _write_json(invalid / "run.json", manifest)

    snapshot = RepositoryBoardLibrary(tmp_path).snapshot()

    assert [board.board_id for board in snapshot.boards] == ["valid-board"]
    assert [(item.path, item.code) for item in snapshot.diagnostics] == [
        ("wrong-directory", "identity_mismatch")
    ]
    assert "Tools/HangboardOnboarding/boards/wrong-directory/run.json" in snapshot.diagnostics[0].message


def test_snapshot_ignores_hidden_transaction_directories(tmp_path: Path) -> None:
    _complete_board(tmp_path, "visible-board", "Visible Board")
    transaction = _boards_root(tmp_path) / ".publication.tmp-123"
    transaction.mkdir()
    (transaction / "run.json").write_text("not inspected", encoding="utf-8")

    snapshot = RepositoryBoardLibrary(tmp_path).snapshot()

    assert [board.board_id for board in snapshot.boards] == ["visible-board"]
    assert snapshot.diagnostics == ()


def test_snapshot_reports_symlinked_board_directories(tmp_path: Path) -> None:
    target = _complete_board(tmp_path, "valid-board", "Valid Board")
    (_boards_root(tmp_path) / "linked-board").symlink_to(target, target_is_directory=True)

    snapshot = RepositoryBoardLibrary(tmp_path).snapshot()

    assert [board.board_id for board in snapshot.boards] == ["valid-board"]
    assert [(item.path, item.code) for item in snapshot.diagnostics] == [
        ("linked-board", "invalid_path")
    ]


def test_snapshot_reports_invalid_board_ids(tmp_path: Path) -> None:
    _complete_board(tmp_path, "valid-board", "Valid Board")
    invalid = _boards_root(tmp_path) / "Invalid_Board"
    invalid.mkdir()

    snapshot = RepositoryBoardLibrary(tmp_path).snapshot()

    assert [board.board_id for board in snapshot.boards] == ["valid-board"]
    assert [(item.path, item.code) for item in snapshot.diagnostics] == [
        ("Invalid_Board", "invalid_board_id")
    ]


def test_snapshot_reports_missing_run_manifest(tmp_path: Path) -> None:
    missing = _boards_root(tmp_path) / "missing-manifest"
    missing.mkdir(parents=True)

    snapshot = RepositoryBoardLibrary(tmp_path).snapshot()

    assert snapshot.boards == ()
    assert [(item.path, item.code) for item in snapshot.diagnostics] == [
        ("missing-manifest", "missing_manifest")
    ]
    assert "Tools/HangboardOnboarding/boards/missing-manifest/run.json" in snapshot.diagnostics[0].message


def test_snapshot_reports_incomplete_runs(tmp_path: Path) -> None:
    _incomplete_board(tmp_path, "incomplete-board", "Incomplete Board")

    snapshot = RepositoryBoardLibrary(tmp_path).snapshot()

    assert snapshot.boards == ()
    assert [(item.path, item.code) for item in snapshot.diagnostics] == [
        ("incomplete-board", "invalid_run")
    ]


def test_snapshot_reports_bad_approval_hashes(tmp_path: Path) -> None:
    run = _complete_board(tmp_path, "approval-board", "Approval Board")
    approval = run / "approvals" / "stage-3.json"
    document = _read_json(approval)
    document["decision"] = "rejected"
    _write_json(approval, document)

    snapshot = RepositoryBoardLibrary(tmp_path).snapshot()

    assert snapshot.boards == ()
    assert [(item.path, item.code) for item in snapshot.diagnostics] == [
        ("approval-board", "invalid_run")
    ]


def test_snapshot_reports_bad_stage_four_output_hashes(tmp_path: Path) -> None:
    run = _complete_board(tmp_path, "output-board", "Output Board")
    normal = _stage_four_acceptance(run)["normal"]
    assert isinstance(normal, dict)
    output = run / str(normal["path"])
    output.write_bytes(b"changed output")

    snapshot = RepositoryBoardLibrary(tmp_path).snapshot()

    assert snapshot.boards == ()
    assert [(item.path, item.code) for item in snapshot.diagnostics] == [
        ("output-board", "invalid_outputs")
    ]


def test_snapshot_revision_tokens_are_deterministic(tmp_path: Path) -> None:
    run = _complete_board(tmp_path, "token-board", "Token Board")
    library = RepositoryBoardLibrary(tmp_path)

    first = library.snapshot().boards[0]
    second = library.snapshot().boards[0]

    assert first.revision_token == second.revision_token
    assert first.revision_token == sha256((run / "run.json").read_bytes()).hexdigest()


def test_copy_current_run_copies_only_a_validated_confined_run(tmp_path: Path) -> None:
    run = _complete_board(tmp_path, "copy-board", "Copy Board")
    destination = tmp_path / "runtime" / "run"

    board = RepositoryBoardLibrary(tmp_path).copy_current_run("copy-board", destination)

    assert board.run_path == run
    assert destination != run
    assert read_status(destination)["status"] == "complete"
    assert not list(destination.parent.glob(f".{destination.name}.tmp-*"))


def test_copy_current_run_rejects_a_symlinked_destination_parent(tmp_path: Path) -> None:
    _complete_board(tmp_path, "copy-board", "Copy Board")
    outside = tmp_path / "outside"
    outside.mkdir()
    runtime = tmp_path / "runtime"
    runtime.symlink_to(outside, target_is_directory=True)

    with pytest.raises(BoardLibraryError, match="symlink"):
        RepositoryBoardLibrary(tmp_path).copy_current_run("copy-board", runtime / "run")

    assert not (outside / "run").exists()


def test_get_board_rejects_invalid_and_missing_boards(tmp_path: Path) -> None:
    invalid = _boards_root(tmp_path) / "Invalid_Board"
    invalid.mkdir(parents=True)
    library = RepositoryBoardLibrary(tmp_path)

    with pytest.raises(BoardLibraryError, match="identifier is invalid"):
        library.get_board("Invalid_Board")
    with pytest.raises(BoardLibraryError, match="does not exist"):
        library.get_board("missing-board")


def _complete_board(repository: Path, board_id: str, product_name: str) -> Path:
    assert _product_key(product_name) == board_id
    run = _boards_root(repository) / board_id
    run.parent.mkdir(parents=True, exist_ok=True)
    source = _source_image(repository, board_id)
    runners = {stage: _StubStageRunner(stage) for stage in range(5)}
    start_run(product_name, str(source), run, runners=runners, workspace_root=repository)
    for stage in range(5):
        approve_stage(run, stage)
        if stage < 4:
            resume_run(run, runners=runners)
    assert read_status(run)["status"] == "complete"
    return run


def _incomplete_board(repository: Path, board_id: str, product_name: str) -> Path:
    assert _product_key(product_name) == board_id
    run = _boards_root(repository) / board_id
    run.parent.mkdir(parents=True, exist_ok=True)
    source = _source_image(repository, board_id)
    start_run(
        product_name,
        str(source),
        run,
        runners={stage: _StubStageRunner(stage) for stage in range(5)},
        workspace_root=repository,
    )
    assert read_status(run)["status"] == "awaiting_approval"
    return run


def _source_image(repository: Path, name: str) -> Path:
    source = repository / ".fixtures" / f"{name}.png"
    source.parent.mkdir(exist_ok=True)
    Image.new("RGB", (512, 512), (45, 65, 85)).save(source)
    return source


def _stage_four_acceptance(run: Path) -> dict[str, object]:
    manifest = _read_json(run / "run.json")
    stages = manifest["stages"]
    assert isinstance(stages, list)
    stage = stages[4]
    assert isinstance(stage, dict)
    return _read_json(run / str(stage["acceptancePath"]))


def _boards_root(repository: Path) -> Path:
    return repository / "Tools" / "HangboardOnboarding" / "boards"


def _product_key(value: str) -> str:
    return "-".join(value.lower().split())


def _read_json(path: Path) -> dict[str, object]:
    value = json.loads(path.read_text(encoding="utf-8"))
    assert isinstance(value, dict)
    return value


def _write_json(path: Path, value: object) -> None:
    path.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8")


class _StubStageRunner:
    def __init__(self, stage: int) -> None:
        self.stage = stage

    def run(self, context: RunContext, artifact_root: Path) -> StageCheckpoint:
        artifact_root.mkdir(parents=True)
        review = artifact_root / f"stage-{self.stage}-review.png"
        Image.new("RGB", (4, 4), (120, 80, 40)).save(review)
        candidate = self._candidate(context, artifact_root)
        _write_json(artifact_root / f"stage-{self.stage}-candidate.json", candidate)
        hashes = {
            path.name: sha256(path.read_bytes()).hexdigest()
            for path in sorted(artifact_root.iterdir())
            if path.is_file()
        }
        _write_json(artifact_root / "candidate-hashes.json", hashes)
        return StageCheckpoint(self.stage, artifact_root, hashes, review, True)

    def _candidate(self, context: RunContext, root: Path) -> dict[str, object]:
        candidate: dict[str, object] = {"profile": {}, "stage": self.stage}
        if self.stage == 0:
            candidate["registered"] = {}
            return candidate
        stages = context.manifest["stages"]
        assert isinstance(stages, list) and isinstance(stages[-1], dict)
        candidate["inputAcceptance"] = {
            "path": stages[-1]["acceptancePath"],
            "sha256": stages[-1]["acceptanceSha256"],
        }
        if self.stage == 1:
            path = root / "stage-1-auto-rgba.png"
            Image.new("RGBA", (4, 4), (10, 20, 30, 255)).save(path)
            candidate["registered"] = {"fileSha256": _hash(path)}
        elif self.stage == 2:
            regions, labels = root / "stage-2-regions.json", root / "stage-2-labels.png"
            _write_json(regions, {"canvas": {"width": 4, "height": 4}, "regions": []})
            Image.new("I;16", (4, 4), 0).save(labels)
            candidate.update({"regionCount": 0, "regions": {"fileSha256": _hash(regions)}, "registered": {"fileSha256": _hash(labels)}})
        elif self.stage == 3:
            regions, svg = root / "stage-3-vector-regions.json", root / "stage-3-vector.svg"
            _write_json(regions, {"canvas": {"width": 4, "height": 4}, "regions": []})
            svg.write_text('<svg xmlns="http://www.w3.org/2000/svg"/>\n', encoding="utf-8")
            candidate.update({"regionCount": 0, "vectorRegions": {"fileSha256": _hash(regions)}, "vectorSvg": {"fileSha256": _hash(svg)}})
        else:
            candidate["regionCount"] = 0
            for field, name in (("normal", "stage-4-normal.png"), ("productSvg", "stage-4-product.svg"), ("manifest", "stage-4-manifest.json"), ("highlights", "stage-4-highlights.json")):
                path = root / name
                if path.suffix == ".png":
                    Image.new("RGB", (4, 4), (1, 2, 3)).save(path)
                elif path.suffix == ".svg":
                    path.write_text('<svg xmlns="http://www.w3.org/2000/svg"/>\n', encoding="utf-8")
                else:
                    _write_json(path, {})
                candidate[field] = {"fileSha256": _hash(path)}
        return candidate


def _hash(path: Path) -> str:
    return sha256(path.read_bytes()).hexdigest()
