from __future__ import annotations

from hashlib import sha256
import json
from pathlib import Path
import shutil
import subprocess
import sys
import xml.etree.ElementTree as ET
from zipfile import ZipFile

import cv2
import numpy as np
from PIL import Image
import pytest

import hangboard_vectorizer.beastmaker_replay as beastmaker_replay
from hangboard_vectorizer.beastmaker_v14_paths import (
    ACCEPTED_V14_PATHS,
    ACCEPTED_V14_PATHS_SHA256,
    accepted_v14_paths_sha256,
)
from hangboard_vectorizer.display_paths import flatten_display_path

from hangboard_vectorizer.beastmaker_replay import (
    _FINAL_V5_PATH_OVERRIDES,
    _V4_PATH_OVERRIDES,
    _V5_PATH_OVERRIDES,
    _V5_STAGE3_SVG_SHA256,
    FullSuiteVerification,
    _comparison_metrics,
    _current_revision,
    _validate_full_suite_verification,
    _load_registered_source,
    _repository_state,
    _run_full_suite,
    _stage_three_parity,
    _validate_and_record_topology,
    _template_with_path_overrides,
    _v3_candidate_template,
    discover_beastmaker_golden_root,
    final_v5_candidate_document,
    final_v5_template,
    run_replay_final,
    run_replay_first_gate,
)
from hangboard_vectorizer.templates import get_product_template


_GOLDEN_ROOT = discover_beastmaker_golden_root()
_SOURCE = _GOLDEN_ROOT / "source.jpg" if _GOLDEN_ROOT is not None else Path("missing-source.jpg")


def _fake_full_suite_runner(repository_root: Path, result_path: Path) -> FullSuiteVerification:
    ET.ElementTree(
        ET.Element("testsuite", {"tests": "1", "failures": "0", "errors": "0", "skipped": "0"})
    ).write(result_path, encoding="utf-8", xml_declaration=True)
    return FullSuiteVerification(
        command="rtk python -m pytest -q --junitxml stage-5-full-suite.xml",
        exit_status=0,
        passed_count=1,
        revision=_current_revision(repository_root),
    )


def test_full_suite_reports_missing_rtk(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(beastmaker_replay.shutil, "which", lambda _name: None)

    with pytest.raises(RuntimeError, match="requires the 'rtk' executable"):
        _run_full_suite(tmp_path, tmp_path / "suite.xml")


def _golden_snapshot_paths() -> tuple[Path, ...]:
    assert _GOLDEN_ROOT is not None
    package_root = Path(__file__).resolve().parents[1] / "src" / "hangboard_vectorizer" / "products"
    return (
        _SOURCE,
        _GOLDEN_ROOT / "photo-proof-fix1-v3.png",
        _GOLDEN_ROOT / "photo-proof-fix1-v3-review.png",
        _GOLDEN_ROOT / "product-render-proof-task4.svg",
        _GOLDEN_ROOT / "product-render-proof-task4.json",
        *sorted(_GOLDEN_ROOT.glob("product-render-proof-task4-*.png")),
        package_root / "beastmaker-1000-render.png",
    )


def test_registered_source_rejects_an_unregistered_raster(tmp_path: Path) -> None:
    wrong_dimensions = tmp_path / "wrong-dimensions.png"
    Image.new("RGB", (64, 64)).save(wrong_dimensions)
    wrong_content = tmp_path / "wrong-content.png"
    Image.new("RGB", (1080, 318), color=(1, 2, 3)).save(wrong_content)

    with pytest.raises(ValueError, match="1080 x 318 RGB"):
        _load_registered_source(wrong_dimensions)
    with pytest.raises(ValueError, match="fingerprint"):
        _load_registered_source(wrong_content)


def test_explicit_missing_golden_root_fails_instead_of_skipping(monkeypatch, tmp_path: Path) -> None:
    monkeypatch.setenv("HANGBOARD_REPLAY_GOLDEN_ROOT", str(tmp_path / "missing"))

    with pytest.raises(FileNotFoundError, match="configured Beastmaker golden root"):
        discover_beastmaker_golden_root()


def test_metrics_report_exact_and_real_differences() -> None:
    exact = np.zeros((2, 3, 4), dtype=np.uint8)
    exact[..., 3] = 255
    changed = exact.copy()
    changed[0, 1, 0] = 11

    identical = _comparison_metrics(exact, exact, exact)
    different = _comparison_metrics(exact, changed, exact)

    assert identical["automatedEqualsManual"] is True
    assert identical["rgbMae"] == 0.0
    assert identical["routedEdgeDisplacementPx"] == 0.0
    assert different["automatedEqualsManual"] is False
    assert different["rgbMaxAbsError"] == 11
    assert different["rgbMae"] == pytest.approx(11 / 18)


def test_v3_candidate_lifts_only_the_outer_top_pair_without_mutating_template() -> None:
    original = get_product_template("beastmaker-1000")
    candidate = _v3_candidate_template(original)
    original_paths = {region.id: region.display_path.data for region in original.regions}
    candidate_paths = {region.id: region.display_path.data for region in candidate.regions}

    assert tuple(region.id for region in candidate.regions) == tuple(
        region.id for region in original.regions
    )
    assert candidate_paths["pocket-top-outer-left"] != original_paths["pocket-top-outer-left"]
    assert candidate_paths["pocket-top-outer-right"] != original_paths["pocket-top-outer-right"]
    assert all(
        candidate_paths[region_id] == original_paths[region_id]
        for region_id in original_paths
        if region_id not in {"pocket-top-outer-left", "pocket-top-outer-right"}
    )
    left = next(region for region in candidate.regions if region.id == "pocket-top-outer-left")
    right = next(region for region in candidate.regions if region.id == "pocket-top-outer-right")
    assert left.display_path.coordinates[0][1] == right.display_path.coordinates[0][1] == 72.0


def test_v4_candidate_changes_exactly_four_reviewed_paths_with_symmetric_gaps() -> None:
    v2 = get_product_template("beastmaker-1000")
    v3 = _v3_candidate_template(v2)
    v4 = _template_with_path_overrides(v3, _V4_PATH_OVERRIDES, "testV4")
    v2_paths = {region.id: region.display_path.data for region in v2.regions}
    v4_paths = {region.id: region.display_path.data for region in v4.regions}

    assert {
        region_id for region_id in v2_paths if v2_paths[region_id] != v4_paths[region_id]
    } == set(_V4_PATH_OVERRIDES)
    left_top = next(region for region in v4.regions if region.id == "pocket-top-outer-left")
    right_top = next(region for region in v4.regions if region.id == "pocket-top-outer-right")
    assert min(y for _, y in left_top.display_path.coordinates) == 60.0
    assert min(y for _, y in right_top.display_path.coordinates) == 60.0
    assert v4_paths["pocket-middle-inner-left"] == _V4_PATH_OVERRIDES["pocket-middle-inner-left"]
    assert v4_paths["pocket-middle-inner-right"] == _V4_PATH_OVERRIDES["pocket-middle-inner-right"]


def test_v5_candidate_changes_only_inner_pair_and_keeps_v4_outer_pair_locked() -> None:
    v2 = get_product_template("beastmaker-1000")
    v3 = _v3_candidate_template(v2)
    v4 = _template_with_path_overrides(v3, _V4_PATH_OVERRIDES, "testV4")
    v5 = _template_with_path_overrides(v4, _V5_PATH_OVERRIDES, "testV5")
    v4_paths = {region.id: region.display_path.data for region in v4.regions}
    v5_paths = {region.id: region.display_path.data for region in v5.regions}

    assert {
        region_id for region_id in v4_paths if v4_paths[region_id] != v5_paths[region_id]
    } == set(_V5_PATH_OVERRIDES)
    assert v5_paths["pocket-top-outer-left"] == v4_paths["pocket-top-outer-left"]
    assert v5_paths["pocket-top-outer-right"] == v4_paths["pocket-top-outer-right"]
    assert v5_paths["pocket-middle-inner-left"] == _V5_PATH_OVERRIDES["pocket-middle-inner-left"]
    assert v5_paths["pocket-middle-inner-right"] == _V5_PATH_OVERRIDES["pocket-middle-inner-right"]


def test_final_v14_constructor_and_serialization_lock_the_accepted_paths() -> None:
    packaged = get_product_template("beastmaker-1000")
    candidate = final_v5_template()
    document = final_v5_candidate_document()
    changed = {
        before.id
        for before, after in zip(packaged.regions, candidate.regions, strict=True)
        if before.display_path != after.display_path
    }

    assert changed == set()
    assert document["acceptedPackagePathIds"] == list(ACCEPTED_V14_PATHS)
    assert document["acceptedPathsSha256"] == ACCEPTED_V14_PATHS_SHA256
    assert document["packagedPathParity"] is True
    assert len(document["paths"]) == 22
    assert {
        region.id: region.display_path.data if region.display_path else None
        for region in packaged.regions
    } == dict(ACCEPTED_V14_PATHS)
    assert packaged.regions == candidate.regions


def test_packaged_template_uses_the_exact_accepted_v14_path_contract() -> None:
    template = get_product_template("beastmaker-1000")
    paths = {region.id: region.display_path.data for region in template.regions}

    assert paths == dict(ACCEPTED_V14_PATHS)
    assert accepted_v14_paths_sha256(paths) == ACCEPTED_V14_PATHS_SHA256


def test_final_v14_constructor_is_available_for_the_promoted_path_contract() -> None:
    assert callable(getattr(beastmaker_replay, "final_v14_template", None))


def test_independent_v14_evidence_fixture_rejects_current_mask_drift() -> None:
    evidence = beastmaker_replay.load_v14_accepted_evidence()
    template = beastmaker_replay.final_v14_template()
    masks = {
        region.id: beastmaker_replay._capture_path_mask(
            region.display_path, beastmaker_replay._CAPTURE_SIZE[::-1]
        )
        for region in template.regions
        if region.display_path is not None
    }
    tampered = dict(masks)
    tampered["pocket-top-left"] = np.roll(tampered["pocket-top-left"], 1, axis=1)

    with pytest.raises(ValueError, match="independent accepted evidence"):
        beastmaker_replay.validate_v14_accepted_masks(tampered, evidence)


def test_independent_v14_evidence_is_shipped_in_a_built_wheel(tmp_path: Path) -> None:
    project_root = Path(__file__).resolve().parents[1]
    project_copy = tmp_path / "project"
    shutil.copytree(
        project_root,
        project_copy,
        ignore=shutil.ignore_patterns(".git", ".worktrees", "build", "*.egg-info", "__pycache__"),
    )
    dist = tmp_path / "dist"
    result = subprocess.run(
        [
            "uv",
            "build",
            "--wheel",
            "--out-dir",
            str(dist),
        ],
        cwd=project_copy,
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode == 0, result.stderr
    (wheel_path,) = dist.glob("hangboard_vectorizer-*.whl")
    with ZipFile(wheel_path) as wheel:
        assert (
            "hangboard_vectorizer/evidence/beastmaker-v14-accepted-evidence.json"
            in wheel.namelist()
        )
    runtime = subprocess.run(
        [
            sys.executable,
            "-I",
            "-c",
            (
                "import json, sys; "
                "sys.path.insert(0, sys.argv[1]); "
                "from hangboard_vectorizer.beastmaker_replay import load_v14_accepted_evidence; "
                "evidence = load_v14_accepted_evidence(); "
                "print(json.dumps({'schema': evidence['schemaVersion'], "
                "'regions': len(evidence['regions'])}))"
            ),
            str(wheel_path),
        ],
        cwd=tmp_path,
        capture_output=True,
        text=True,
        check=False,
    )

    assert runtime.returncode == 0, runtime.stderr
    assert json.loads(runtime.stdout) == {"schema": 1, "regions": 22}


def test_v14_candidate_traceability_is_against_the_pinned_dense_evidence() -> None:
    evidence = beastmaker_replay.load_v14_accepted_evidence()
    template = beastmaker_replay.final_v14_template()

    traceability = beastmaker_replay.v14_candidate_traceability(template, evidence)

    assert traceability["passed"] is True
    assert set(traceability["regions"]) == set(ACCEPTED_V14_PATHS)
    assert traceability["regions"]["jug-left"]["candidateMaskSha256"] != traceability[
        "regions"
    ]["jug-left"]["currentMaskSha256"]


def test_v14_preserves_reviewed_symmetry_rows_and_outward_mid_pockets() -> None:
    template = beastmaker_replay.final_v14_template()
    paths = {region.id: region.display_path for region in template.regions}

    def bounds(region_id: str) -> tuple[float, float, float, float]:
        assert paths[region_id] is not None
        contour = flatten_display_path(paths[region_id])
        return (
            float(contour[:, 0].min()),
            float(contour[:, 1].min()),
            float(contour[:, 0].max()),
            float(contour[:, 1].max()),
        )

    def center_y(region_id: str) -> float:
        _, y0, _, y1 = bounds(region_id)
        return (y0 + y1) / 2

    for left, right in (
        ("jug-left", "jug-right"),
        ("sloper-35-left", "sloper-35-right"),
        ("pocket-top-outer-left", "pocket-top-outer-right"),
        ("pocket-top-left", "pocket-top-right"),
        ("pocket-middle-outer-left", "pocket-middle-outer-right"),
        ("pocket-middle-mid-left", "pocket-middle-mid-right"),
        ("pocket-middle-inner-left", "pocket-middle-inner-right"),
        ("pocket-bottom-outer-left", "pocket-bottom-outer-right"),
        ("pocket-bottom-mid-left", "pocket-bottom-mid-right"),
        ("pocket-bottom-inner-left", "pocket-bottom-inner-right"),
    ):
        left_box, right_box = bounds(left), bounds(right)
        assert np.allclose((left_box[0], left_box[2]), (1000 - right_box[2], 1000 - right_box[0]))
        assert np.isclose(center_y(left), center_y(right))

    assert {round(center_y(region_id), 6) for region_id in (
        "pocket-middle-outer-left", "pocket-middle-mid-left", "pocket-middle-inner-left",
        "pocket-middle-center", "pocket-middle-inner-right", "pocket-middle-mid-right",
        "pocket-middle-outer-right",
    )} == {141.0}
    assert {round(center_y(region_id), 6) for region_id in (
        "pocket-bottom-outer-left", "pocket-bottom-mid-left", "pocket-bottom-inner-left",
        "pocket-bottom-inner-right", "pocket-bottom-mid-right", "pocket-bottom-outer-right",
    )} == {212.892857}
    assert bounds("pocket-middle-mid-left")[2] < bounds("pocket-middle-inner-left")[0]
    assert bounds("pocket-middle-mid-right")[0] > bounds("pocket-middle-inner-right")[2]


def test_v14_keeps_pockets_smooth_and_scopes_linear_paths_to_mixed_corner_regions() -> None:
    template = beastmaker_replay.final_v14_template()
    linear_ids = {"jug-left", "jug-right", "sloper-35-left", "sloper-35-right"}

    for region in template.regions:
        assert region.display_path is not None
        commands = set(region.display_path.commands)
        if region.type == "pocket":
            assert "C" in commands
            assert len(region.display_path.commands) <= 10
        elif region.id in linear_ids:
            assert {"C", "L", "Z"} <= commands
            assert len(region.display_path.commands) > 10
        elif region.id == "sloper-center":
            assert {"L", "Q"} <= commands


def test_v14_outer_jugs_and_slopers_stay_within_the_board_outline() -> None:
    template = beastmaker_replay.final_v14_template()
    assert template.display_outline_path is not None
    board = flatten_display_path(template.display_outline_path).astype(np.float32)
    for region in template.regions[:4]:
        assert region.display_path is not None
        contour = flatten_display_path(region.display_path)
        assert all(
            cv2.pointPolygonTest(board, (float(x), float(y)), False) >= 0
            for x, y in contour[:-1]
        )


def test_topology_matches_the_accepted_template_and_output() -> None:
    if _GOLDEN_ROOT is None:
        pytest.skip("untracked Beastmaker goldens absent")
    topology = _validate_and_record_topology(
        get_product_template("beastmaker-1000"), _GOLDEN_ROOT
    )

    assert len(topology["orderedIds"]) == 22
    assert topology["typeCounts"] == {"jug": 2, "pocket": 17, "sloper": 3}
    assert topology["sloperIds"] == [
        "sloper-35-left",
        "sloper-35-right",
        "sloper-center",
    ]
    assert topology["exactPathParity"] is True


@pytest.mark.skipif(_GOLDEN_ROOT is None, reason="untracked Beastmaker goldens absent")
def test_first_gate_is_deterministic_and_never_writes_goldens(tmp_path: Path) -> None:
    golden_before = {
        path.name: sha256(path.read_bytes()).hexdigest()
        for path in _golden_snapshot_paths()
    }
    first = run_replay_first_gate(_SOURCE, tmp_path / "v1")
    second = run_replay_first_gate(_SOURCE, tmp_path / "v2")

    assert first.metrics["automatedEqualsManual"] is True
    assert first.metrics["automatedReviewEqualsManual"] is True
    assert first.metrics["pngFileEquality"] == {
        "automatedRgbaEqualsManual": True,
        "automatedRgbaEqualsPackaged": True,
        "automatedReviewEqualsManual": True,
    }
    assert first.metrics["copiedAcceptedPngBytes"] == {
        "automatedReview": True,
        "automatedRgba": True,
    }
    assert first.metrics == second.metrics
    for name in (
        "stage-0-crop.png",
        "stage-0-alignment.png",
        "stage-1-auto-rgba.png",
        "stage-1-auto-review.png",
        "stage-1-auto-vs-manual.png",
        "stage-1-diff-heatmap.png",
        "stage-2-auto-regions-labeled.png",
    ):
        assert (first.artifact_root / name).read_bytes() == (second.artifact_root / name).read_bytes()
    assert golden_before == {
        path.name: sha256(path.read_bytes()).hexdigest()
        for path in _golden_snapshot_paths()
    }


@pytest.mark.skipif(_GOLDEN_ROOT is None, reason="untracked Beastmaker goldens absent")
def test_first_gate_refuses_to_overwrite_an_existing_replay_directory(tmp_path: Path) -> None:
    artifact_root = tmp_path / "v1"
    run_replay_first_gate(_SOURCE, artifact_root)

    with pytest.raises(FileExistsError, match="already exists"):
        run_replay_first_gate(_SOURCE, artifact_root)


@pytest.mark.skipif(_GOLDEN_ROOT is None, reason="untracked Beastmaker goldens absent")
def test_final_replay_is_deterministic_and_preserves_goldens(tmp_path: Path) -> None:
    golden_before = {
        path.name: sha256(path.read_bytes()).hexdigest()
        for path in _golden_snapshot_paths()
    }
    first = run_replay_final(_SOURCE, tmp_path / "v1", full_suite_runner=_fake_full_suite_runner)
    second = run_replay_final(_SOURCE, tmp_path / "v2", full_suite_runner=_fake_full_suite_runner)

    with pytest.raises(FileExistsError, match="already exists"):
        run_replay_final(_SOURCE, first.artifact_root, full_suite_runner=_fake_full_suite_runner)

    assert first.metrics == second.metrics
    assert first.metrics["svg"]["sha256"] == _V5_STAGE3_SVG_SHA256
    assert first.metrics["svg"]["sha256"] != first.metrics["svg"]["acceptedSupersededSha256"]
    assert first.metrics["packagedRaster"] == {
        "sha256": "4bd615d34bf60d083d4bb7da945cdbe23a59858a430d268d25c2c67308f23627",
        "expectedSha256": "4bd615d34bf60d083d4bb7da945cdbe23a59858a430d268d25c2c67308f23627",
        "unchanged": True,
    }
    assert first.metrics["gates"] == {
        "stage3Parity": True,
        "stage4Highlights": True,
        "packagedRasterUnchanged": True,
        "normalExercisesGeneratedSvg": True,
    }
    assert first.metrics["normal"]["generatedFromSvg"] is True
    assert first.metrics["normal"]["layoutBoundsExact"] is True
    assert first.metrics["normal"]["productMaskIouWithAccepted"] >= 0.995
    repository_state = _repository_state(Path(__file__).resolve().parents[1])
    assert first.metrics["verification"]["fullSuite"] == {
        "command": "rtk python -m pytest -q --junitxml stage-5-full-suite.xml",
        "exitStatus": 0,
        "passedCount": 1,
        "revision": _current_revision(Path(__file__).resolve().parents[1]),
        "tree": repository_state.tree,
        "worktreeStatus": repository_state.status,
        "invocation": {"mode": "injected"},
    }
    assert first.metrics["highlights"]["passed"] is True
    assert all(
        scenario["selectedMaskIouWithAccepted"] >= 0.995
        for scenario in first.metrics["highlights"]["scenarios"].values()
    )
    assert first.metrics["highlights"]["scenarios"]["all-22"]["activeIds"] == list(
        ACCEPTED_V14_PATHS
    )
    assert first.metrics["candidateTraceability"]["passed"] is True
    assert set(first.metrics["candidateTraceability"]["regions"]) == set(ACCEPTED_V14_PATHS)
    assert all(
        scenario["approvedMaskSha256Matched"]
        and scenario["approvedHighlightSha256Matched"]
        for scenario in first.metrics["highlights"]["scenarios"].values()
    )
    for name in (
        "stage-3-product.svg",
        "stage-3-manifest.json",
        "stage-3-parity.json",
        "stage-3-normal.png",
        "stage-3-numbered-hold-map.png",
        "stage-4-highlight-jugs.png",
        "stage-4-highlight-slopers.png",
        "stage-4-highlight-symmetric-pockets.png",
        "stage-4-highlight-mixed-grips.png",
        "stage-4-highlight-all-22.png",
        "stage-4-highlights.json",
        "stage-5-summary.json",
        "stage-5-full-suite.xml",
    ):
        assert (first.artifact_root / name).read_bytes() == (second.artifact_root / name).read_bytes()
    assert golden_before == {
        path.name: sha256(path.read_bytes()).hexdigest()
        for path in _golden_snapshot_paths()
    }


@pytest.mark.skipif(_GOLDEN_ROOT is None, reason="untracked Beastmaker goldens absent")
def test_stage_three_parity_rejects_perturbed_image_geometry(tmp_path: Path) -> None:
    replay = run_replay_final(_SOURCE, tmp_path / "v1", full_suite_runner=_fake_full_suite_runner)
    svg_path = replay.artifact_root / "stage-3-product.svg"
    package_png = (
        Path(__file__).resolve().parents[1]
        / "src"
        / "hangboard_vectorizer"
        / "products"
        / "beastmaker-1000-render.png"
    )
    for index, (original, replacement) in enumerate(
        (
            ('viewBox="0 0 1000 259"', 'viewBox="0 0 999 259"'),
            ('width="1000"', 'width="999"'),
        )
    ):
        mutated_svg = tmp_path / f"perturbed-{index}.svg"
        mutated_svg.write_text(
            svg_path.read_text(encoding="utf-8").replace(original, replacement, 1),
            encoding="utf-8",
        )
        with pytest.raises(ValueError, match="Stage 3 SVG"):
            _stage_three_parity(
                get_product_template("beastmaker-1000"),
                mutated_svg,
                replay.artifact_root / "stage-3-manifest.json",
                np.asarray(Image.open(replay.artifact_root / "stage-3-normal.png").convert("RGB")),
                np.asarray(
                    Image.open(_GOLDEN_ROOT / "product-render-proof-task4-normal.png").convert("RGB")
                ),
                package_png,
            )


def test_final_replay_rejects_static_or_stale_full_suite_provenance(tmp_path: Path) -> None:
    verification = _fake_full_suite_runner(Path(__file__).resolve().parents[1], tmp_path / "suite.xml")
    stale = FullSuiteVerification(
        command=verification.command,
        exit_status=verification.exit_status,
        passed_count=verification.passed_count,
        revision="stale-revision",
    )

    with pytest.raises(ValueError, match="stale"):
        _validate_full_suite_verification(
            stale, tmp_path / "suite.xml", verification.revision
        )


@pytest.mark.skipif(_GOLDEN_ROOT is None, reason="untracked Beastmaker goldens absent")
def test_final_replay_cannot_reuse_same_revision_preexisting_evidence(tmp_path: Path) -> None:
    junit_path = tmp_path / "old-suite.xml"
    verification = _fake_full_suite_runner(Path(__file__).resolve().parents[1], junit_path)
    evidence_path = tmp_path / "old-evidence.json"
    evidence_path.write_text(
        json.dumps(
            {
                "command": verification.command,
                "exitStatus": verification.exit_status,
                "passedCount": verification.passed_count,
                "revision": verification.revision,
                "junitResult": str(junit_path),
            }
        ),
        encoding="utf-8",
    )

    with pytest.raises(TypeError, match="full_suite_evidence_path"):
        run_replay_final(
            _SOURCE,
            tmp_path / "v1",
            full_suite_evidence_path=evidence_path,
        )
