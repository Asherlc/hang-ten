from __future__ import annotations

from hashlib import sha256
import json
from pathlib import Path

import numpy as np
from PIL import Image
import pytest

from hangboard_vectorizer.generic_stage2 import run_generic_stage2
from hangboard_vectorizer.generic_stage3 import run_generic_stage3
from hangboard_vectorizer.onboarding_run import RunContext
from hangboard_vectorizer.review_edits import (
    materialize_stage2_edit,
    materialize_stage3_edit,
    validate_stage_edit,
)
from hangboard_vectorizer.models import ConversionError


_DATA = Path(__file__).parent / "data"


@pytest.fixture
def accepted_stage1_run(tmp_path: Path) -> Path:
    run = tmp_path / "accepted-stage-1"
    inputs = run / "inputs"
    inputs.mkdir(parents=True)
    rgba = np.full((160, 1000, 4), 255, dtype=np.uint8)
    raster_path = inputs / "stage-1-rgba.png"
    Image.fromarray(rgba, "RGBA").save(
        raster_path, format="PNG", optimize=False, compress_level=9
    )
    raster_hash = _hash_file(raster_path)
    acceptance = {
        "registered": {
            "fileSha256": raster_hash,
            "path": "inputs/stage-1-rgba.png",
            "pixelSha256": sha256(rgba.tobytes()).hexdigest(),
        },
        "runIdentitySha256": "review-edit-test-run",
        "stage": 1,
    }
    acceptance_path = inputs / "stage-1-acceptance.json"
    _write_json(acceptance_path, acceptance)
    acceptance_hash = _hash_file(acceptance_path)
    proposal = {
        "canvas": {"height": 160, "width": 1000},
        "inputAcceptanceSha256": acceptance_hash,
        "inputRasterSha256": raster_hash,
        "productKey": "fixture-board",
        "provider": "file",
        "regions": [
            {
                "anchor": [175, 50],
                "geometry": {
                    "mode": "surface",
                    "polygon": [[100, 30], [250, 30], [250, 70], [100, 70]],
                },
                "id": 1,
                "key": "grip-001",
                "metadata": {},
                "type": "pocket",
            },
            {
                "anchor": [775, 110],
                "geometry": {
                    "mode": "surface",
                    "polygon": [[700, 90], [850, 90], [850, 130], [700, 130]],
                },
                "id": 2,
                "key": "grip-002",
                "metadata": {},
                "type": "pocket",
            },
        ],
        "schemaVersion": 1,
    }
    _write_json(inputs / "stage-2-semantic-proposal.json", proposal)
    manifest = {
        "pipeline": {"currentStage": 1, "status": "ready_for_next_stage"},
        "product": {"key": "fixture-board"},
        "runIdentitySha256": "review-edit-test-run",
        "stages": [
            {"stage": 0, "status": "approved"},
            {
                "acceptancePath": "inputs/stage-1-acceptance.json",
                "acceptanceSha256": acceptance_hash,
                "stage": 1,
                "status": "approved",
            },
        ],
    }
    artifact_root = run / "stages/02/attempt-0001"
    run_generic_stage2(RunContext(run, manifest), artifact_root)
    manifest["stages"].append(_pending_record(run, artifact_root, stage=2))
    manifest["pipeline"] = {"currentStage": 2, "status": "awaiting_approval"}
    _write_json(run / "run.json", manifest)
    return run


@pytest.fixture
def accepted_stage2_run(accepted_stage1_run: Path) -> Path:
    run = accepted_stage1_run
    manifest = json.loads((run / "run.json").read_text())
    stage2 = manifest["stages"][2]
    stage2_root = run / stage2["artifactRoot"]
    candidate = json.loads((stage2_root / "stage-2-candidate.json").read_text())
    acceptance = {
        "profile": candidate["profile"],
        "regionCount": candidate["regionCount"],
        "regions": {
            **candidate["regions"],
            "path": f'{stage2["artifactRoot"]}/stage-2-regions.json',
        },
        "registered": {
            **candidate["registered"],
            "path": f'{stage2["artifactRoot"]}/stage-2-labels.png',
        },
        "runIdentitySha256": manifest["runIdentitySha256"],
        "stage": 2,
    }
    acceptance_path = run / "approvals/stage-2-acceptance.json"
    acceptance_path.parent.mkdir()
    _write_json(acceptance_path, acceptance)
    stage2.update(
        {
            "acceptancePath": "approvals/stage-2-acceptance.json",
            "acceptanceSha256": _hash_file(acceptance_path),
            "status": "approved",
        }
    )
    manifest["pipeline"] = {"currentStage": 2, "status": "ready_for_next_stage"}
    artifact_root = run / "stages/03/attempt-0001"
    run_generic_stage3(RunContext(run, manifest), artifact_root)
    manifest["stages"].append(_pending_record(run, artifact_root, stage=3))
    manifest["pipeline"] = {"currentStage": 3, "status": "awaiting_approval"}
    _write_json(run / "run.json", manifest)
    return run


def test_stage2_edit_rebuilds_labels_review_and_candidate_hashes(
    accepted_stage1_run: Path, tmp_path: Path
) -> None:
    edited = _load_fixture("stage-2-regions-edited.json")
    baseline = _pending_artifact_root(accepted_stage1_run, 2)
    before = _artifact_hashes(baseline)
    checkpoint = materialize_stage2_edit(
        _context(accepted_stage1_run), edited, tmp_path / "attempt"
    )
    assert checkpoint.stage == 2
    assert (checkpoint.artifact_root / "stage-2-labels.png").is_file()
    assert (checkpoint.artifact_root / "stage-2-review.png").is_file()
    assert _candidate_hashes_match(checkpoint.artifact_root)
    assert _candidate_hash_names(checkpoint.artifact_root) == _pending_candidate_hash_names(
        accepted_stage1_run, 2
    )
    assert _artifact_hashes(baseline) == before


def test_stage3_edit_preserves_exact_display_paths(
    accepted_stage2_run: Path, tmp_path: Path
) -> None:
    edited = _load_fixture("stage-3-vector-regions-edited.json")
    baseline = _pending_artifact_root(accepted_stage2_run, 3)
    before = _artifact_hashes(baseline)
    checkpoint = materialize_stage3_edit(
        _context(accepted_stage2_run), edited, tmp_path / "attempt"
    )
    actual = json.loads(
        (checkpoint.artifact_root / "stage-3-vector-regions.json").read_text()
    )
    assert [r["displayPath"] for r in actual["regions"]] == [
        r["displayPath"] for r in edited["regions"]
    ]
    assert [p["displayPath"] for p in actual["silhouettePaths"]] == [
        p["displayPath"] for p in edited["silhouettePaths"]
    ]
    assert actual["silhouettePaths"][0]["outputMaskSha256"] != "silhouette"
    assert actual["silhouettePaths"][0]["sourceMaskSha256"] != "silhouette"
    assert _candidate_hashes_match(checkpoint.artifact_root)
    assert _candidate_hash_names(checkpoint.artifact_root) == _pending_candidate_hash_names(
        accepted_stage2_run, 3
    )
    assert _artifact_hashes(baseline) == before


def test_validation_rejects_a_missing_stable_id_with_the_affected_region() -> None:
    edited = _load_fixture("stage-2-regions-edited.json")
    del edited["regions"][0]["id"]

    with pytest.raises(ConversionError, match=r"Stage 2 region 1"):
        validate_stage_edit(2, edited)


def test_validation_rejects_duplicate_stable_ids_with_the_affected_region() -> None:
    edited = _load_fixture("stage-2-regions-edited.json")
    edited["regions"][1]["id"] = 1

    with pytest.raises(ConversionError, match=r"Stage 2 region 1"):
        validate_stage_edit(2, edited)


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("anchor", [float("nan"), 51]),
        ("anchor", [1000, 51]),
        ("contour", [[104, 29], [float("inf"), 31], [101, 70]]),
        ("contour", [[104, 29], [-1, 31], [101, 70]]),
    ],
)
def test_validation_rejects_nonfinite_or_out_of_bounds_stage2_coordinates(
    field: str, value: object
) -> None:
    edited = _load_fixture("stage-2-regions-edited.json")
    edited["regions"][0][field] = value

    with pytest.raises(ConversionError, match=r"Stage 2 region 1"):
        validate_stage_edit(2, edited)


def test_validation_rejects_contours_with_fewer_than_three_vertices() -> None:
    edited = _load_fixture("stage-2-regions-edited.json")
    edited["regions"][0]["contour"] = [[104, 29], [250, 31]]

    with pytest.raises(ConversionError, match=r"Stage 2 region 1"):
        validate_stage_edit(2, edited)


def test_validation_rejects_nonfinite_or_out_of_bounds_stage2_bounds() -> None:
    edited = _load_fixture("stage-2-regions-edited.json")
    edited["regions"][0]["bounds"] = [0, 0, float("nan"), 161]

    with pytest.raises(ConversionError, match=r"Stage 2 region 1"):
        validate_stage_edit(2, edited)


def test_validation_rejects_a_self_intersecting_stage2_contour() -> None:
    edited = _load_fixture("stage-2-regions-edited.json")
    edited["regions"][0]["contour"] = [
        [100, 20],
        [200, 80],
        [100, 80],
        [200, 20],
    ]

    with pytest.raises(ConversionError, match=r"Stage 2 region 1"):
        validate_stage_edit(2, edited)


def test_validation_rejects_a_malformed_display_path() -> None:
    edited = _load_fixture("stage-3-vector-regions-edited.json")
    edited["regions"][0]["displayPath"] = "M 100 20 L nope Z"

    with pytest.raises(ConversionError, match=r"Stage 3 region 1"):
        validate_stage_edit(3, edited)


def test_validation_rejects_a_self_intersecting_display_path() -> None:
    edited = _load_fixture("stage-3-vector-regions-edited.json")
    edited["regions"][0]["displayPath"] = (
        "M 100 20 L 200 80 L 100 80 L 200 20 Z"
    )

    with pytest.raises(ConversionError, match=r"Stage 3 region 1"):
        validate_stage_edit(3, edited)


def test_validation_rejects_a_self_intersecting_silhouette_path() -> None:
    edited = _load_fixture("stage-3-vector-regions-edited.json")
    edited["silhouettePaths"][0]["displayPath"] = (
        "M 100 20 L 200 80 L 100 80 L 200 20 Z"
    )

    with pytest.raises(ConversionError, match=r"piece-01-silhouette"):
        validate_stage_edit(3, edited)


def test_stage3_materialization_rejects_region_order_changes(
    accepted_stage2_run: Path, tmp_path: Path
) -> None:
    edited = _load_fixture("stage-3-vector-regions-edited.json")
    edited["regions"].reverse()
    output = tmp_path / "attempt"

    with pytest.raises(ConversionError, match=r"Stage 3 region 2"):
        materialize_stage3_edit(_context(accepted_stage2_run), edited, output)

    assert not output.exists()


def test_stage3_materialization_reports_the_first_missing_region_id(
    accepted_stage2_run: Path, tmp_path: Path
) -> None:
    edited = _load_fixture("stage-3-vector-regions-edited.json")
    edited["regions"].pop()

    with pytest.raises(ConversionError, match=r"Stage 3 region 2"):
        materialize_stage3_edit(
            _context(accepted_stage2_run), edited, tmp_path / "attempt"
        )


def test_stage2_materialization_reports_the_first_missing_stable_id(
    accepted_stage1_run: Path, tmp_path: Path
) -> None:
    edited = _load_fixture("stage-2-regions-edited.json")
    edited["regions"].pop()

    with pytest.raises(ConversionError, match=r"Stage 2 region 2"):
        materialize_stage2_edit(
            _context(accepted_stage1_run), edited, tmp_path / "attempt"
        )


def test_stage2_materialization_cleans_a_failed_transaction(
    accepted_stage1_run: Path,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    edited = _load_fixture("stage-2-regions-edited.json")
    output = tmp_path / "attempt"

    def fail_after_partial_write(root: Path, **_kwargs):
        (root / "partial").write_text("partial")
        raise RuntimeError("injected write failure")

    monkeypatch.setattr(
        "hangboard_vectorizer.review_edits.generic_stage2.build_stage2_artifacts",
        fail_after_partial_write,
    )

    with pytest.raises(RuntimeError, match="injected write failure"):
        materialize_stage2_edit(_context(accepted_stage1_run), edited, output)

    assert not output.exists()
    assert not list(tmp_path.glob(".attempt.tmp-*"))


def test_materialization_rejects_a_changed_pending_candidate_hash_contract(
    accepted_stage1_run: Path, tmp_path: Path
) -> None:
    baseline = _pending_artifact_root(accepted_stage1_run, 2)
    hashes_path = baseline / "candidate-hashes.json"
    hashes_path.write_text(hashes_path.read_text() + "\n")

    with pytest.raises(ConversionError, match="pending candidate hashes changed"):
        materialize_stage2_edit(
            _context(accepted_stage1_run),
            _load_fixture("stage-2-regions-edited.json"),
            tmp_path / "attempt",
        )


def _context(run: Path) -> RunContext:
    return RunContext(run, json.loads((run / "run.json").read_text()))


def _load_fixture(name: str) -> dict[str, object]:
    return json.loads((_DATA / name).read_text())


def _candidate_hashes_match(root: Path) -> bool:
    hashes = json.loads((root / "candidate-hashes.json").read_text())
    return all(_hash_file(root / name) == expected for name, expected in hashes.items())


def _candidate_hash_names(root: Path) -> set[str]:
    return set(json.loads((root / "candidate-hashes.json").read_text()))


def _pending_candidate_hash_names(run: Path, stage: int) -> set[str]:
    return _candidate_hash_names(_pending_artifact_root(run, stage))


def _pending_artifact_root(run: Path, stage: int) -> Path:
    manifest = json.loads((run / "run.json").read_text())
    record = next(item for item in reversed(manifest["stages"]) if item["stage"] == stage)
    return run / record["artifactRoot"]


def _artifact_hashes(root: Path) -> dict[str, str]:
    return {path.name: _hash_file(path) for path in root.iterdir() if path.is_file()}


def _pending_record(root: Path, artifact_root: Path, *, stage: int) -> dict[str, object]:
    relative = artifact_root.relative_to(root).as_posix()
    return {
        "artifactRoot": relative,
        "attempt": 1,
        "candidateHashesPath": f"{relative}/candidate-hashes.json",
        "candidateHashesSha256": _hash_file(artifact_root / "candidate-hashes.json"),
        "reviewPath": f"{relative}/stage-{stage}-review.png",
        "reviewSha256": _hash_file(artifact_root / f"stage-{stage}-review.png"),
        "stage": stage,
        "status": "review_pending",
    }


def _write_json(path: Path, value: object) -> None:
    path.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n")


def _hash_file(path: Path) -> str:
    return sha256(path.read_bytes()).hexdigest()
