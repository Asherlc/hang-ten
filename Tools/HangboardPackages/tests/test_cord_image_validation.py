from __future__ import annotations

from dataclasses import replace
from datetime import date
import json
from pathlib import Path
import shutil

from PIL import Image
import pytest

from hangboard_packages.tensioned_cord_audit import (
    TensionedCordEvidence,
    TensionedCordRecord,
    load_tensioned_cord_ledger,
)
from hangboard_packages.board_catalog import discover_board_packages
from hangboard_packages.cli import main as cli_main

try:
    from hangboard_packages.cord_image_validation import (
        CordCandidateRun,
        load_cord_candidate_runs,
        validate_cord_candidate,
        validate_cord_method_cohort,
    )
except (ImportError, ModuleNotFoundError):
    CordCandidateRun = None
    load_cord_candidate_runs = None
    validate_cord_candidate = None
    validate_cord_method_cohort = None


_PRESERVATION = {
    "backgroundFramingPreserved": True,
    "boardTransformPreserved": True,
    "boardAppearancePreserved": True,
    "unrelatedPixelsPreserved": True,
    "overlayAlignmentPreserved": True,
}

_REPOSITORY_ROOT = Path(__file__).resolve().parents[3]


def _record(package_id: str = "fixture.board", presentation_id: str = "primary") -> TensionedCordRecord:
    return TensionedCordRecord(
        package_id=package_id,
        presentation_id=presentation_id,
        asset_path="assets/primary.png",
        asset_sha256="0" * 64,
        source_presentation_id=None,
        evidence=TensionedCordEvidence(
            url="https://manufacturer.example/fixture",
            label="Fixture",
            reviewed_at=date(2026, 9, 1),
            audit_path="docs/source-audits/fixture.md",
            facts=("presentation", "orientation", "visibleTopology", "tensionDirection"),
        ),
        orientation="upright",
        gravity="canvasDown",
        tension_direction="towardCanvasBottom",
        visible_topology="visibleSegmentsOnly",
        routing="visibleOnly",
        terminals="unknown",
        knots="unknown",
        hardware="unknown",
        status="accepted",
        output="accepted",
        blocker=None,
    )


def _write_png(path: Path, *, size: tuple[int, int] = (4, 4), mode: str = "RGBA") -> Path:
    color = (240, 235, 220, 0) if mode == "RGBA" else (240, 235, 220)
    Image.new(mode, size, color).save(path)
    return path


def _run(record: TensionedCordRecord, **overrides: object) -> dict[str, object]:
    run: dict[str, object] = {
        "schemaVersion": 1,
        "captureID": f"{record.package_id}::{record.presentation_id}",
        "orientation": record.orientation,
        "gravity": record.gravity,
        "sourcePresentationID": record.source_presentation_id,
        "method": {
            "id": "fixture-noop",
            "intent": "negativeControl",
            "configuration": {"mode": "exact-canvas"},
        },
        "claimedTopology": record.visible_topology,
        "changedPixels": [],
        "preservation": dict(_PRESERVATION),
        "physics": {
            "proofCaptureID": f"{record.package_id}::{record.presentation_id}",
            "orientation": record.orientation,
            "gravity": record.gravity,
            "loadDirection": record.tension_direction,
            "cordPaths": [[[1.0, 0.0], [1.0, 3.0]]],
        },
    }
    run.update(overrides)
    return run


def _candidate_run(tmp_path: Path, capture_id: str) -> object:
    assert CordCandidateRun is not None
    package_id, presentation_id = capture_id.split("::", 1)
    baseline = _write_png(tmp_path / f"{presentation_id}-baseline.png")
    candidate = _write_png(tmp_path / f"{presentation_id}-candidate.png")
    record = _record(package_id, presentation_id)
    return CordCandidateRun(baseline, candidate, record, _run(record))


def _require_api() -> None:
    assert validate_cord_candidate is not None, "cord candidate validator is missing"
    assert validate_cord_method_cohort is not None, "cord cohort validator is missing"


def test_method_run_loader_resolves_exact_declared_files_and_ledger_identity(tmp_path: Path) -> None:
    """Catches a loader mutation that silently selects another presentation or path."""
    _require_api()
    assert load_cord_candidate_runs is not None
    record = _record()
    _write_png(tmp_path / "baseline.png")
    _write_png(tmp_path / "candidate.png")
    contract = tmp_path / "cohort.json"
    contract.write_text(
        json.dumps(
            {
                "schemaVersion": 1,
                "runs": [
                    {
                        "captureID": "fixture.board::primary",
                        "baselinePath": "baseline.png",
                        "candidatePath": "candidate.png",
                        "evidence": _run(record),
                    }
                ],
            }
        ),
        encoding="utf-8",
    )

    assert load_cord_candidate_runs(
        contract,
        records_by_capture_id={"fixture.board::primary": record},
    ) == (
        CordCandidateRun(tmp_path / "baseline.png", tmp_path / "candidate.png", record, _run(record)),
    )


def test_method_run_loader_rejects_unknown_pair_and_paths_outside_contract_directory(
    tmp_path: Path,
) -> None:
    """Catches open cohort identity and path traversal acceptance."""
    _require_api()
    assert load_cord_candidate_runs is not None
    record = _record()
    contract = tmp_path / "cohort.json"
    payload = {
        "schemaVersion": 1,
        "runs": [
            {
                "captureID": "fixture.unknown::primary",
                "baselinePath": "../baseline.png",
                "candidatePath": "candidate.png",
                "evidence": _run(record),
            }
        ],
    }
    contract.write_text(json.dumps(payload), encoding="utf-8")

    with pytest.raises(ValueError, match="unknown capture identity|must stay beneath"):
        load_cord_candidate_runs(
            contract,
            records_by_capture_id={"fixture.board::primary": record},
        )


def test_method_run_loader_rejects_symlinked_png_inputs(tmp_path: Path) -> None:
    """Catches resolving a symlink before enforcing the closed regular-file boundary."""
    _require_api()
    assert load_cord_candidate_runs is not None
    record = _record()
    baseline = _write_png(tmp_path / "real-baseline.png")
    (tmp_path / "baseline.png").symlink_to(baseline.name)
    _write_png(tmp_path / "candidate.png")
    contract = tmp_path / "cohort.json"
    contract.write_text(
        json.dumps(
            {
                "schemaVersion": 1,
                "runs": [
                    {
                        "captureID": "fixture.board::primary",
                        "baselinePath": "baseline.png",
                        "candidatePath": "candidate.png",
                        "evidence": _run(record),
                    }
                ],
            }
        ),
        encoding="utf-8",
    )

    with pytest.raises(ValueError, match="regular file"):
        load_cord_candidate_runs(
            contract,
            records_by_capture_id={"fixture.board::primary": record},
        )


def test_unchanged_exact_canvas_candidate_passes_all_generic_invariants(tmp_path: Path) -> None:
    """Catches a validator mutation that blocks byte-preserving feasibility replay."""
    _require_api()
    record = _record()
    baseline = _write_png(tmp_path / "baseline.png")
    candidate = _write_png(tmp_path / "candidate.png")

    report = validate_cord_candidate(baseline, candidate, record, _run(record))

    assert report.passed is True
    assert report.to_json() == {
        "captureID": "fixture.board::primary",
        "passed": True,
        "violations": [],
    }


def test_negative_control_rejects_even_an_exactly_accounted_pixel_change(tmp_path: Path) -> None:
    """Catches relabeling an edited candidate as the unchanged fail-closed control."""
    _require_api()
    record = _record()
    baseline = _write_png(tmp_path / "baseline.png")
    candidate = _write_png(tmp_path / "candidate.png")
    with Image.open(candidate) as image:
        image.putpixel((2, 2), (10, 20, 30, 0))
        image.save(candidate)
    run = _run(
        record,
        changedPixels=[
            {
                "x": 2,
                "y": 2,
                "beforeRGBA": [240, 235, 220, 0],
                "afterRGBA": [10, 20, 30, 0],
                "classification": "cord",
            }
        ],
    )
    run["method"] = {
        "id": "fixture-noop",
        "intent": "negativeControl",
        "configuration": {"mode": "exact-canvas"},
    }

    report = validate_cord_candidate(baseline, candidate, record, run)

    assert "negativeControlMutation" in {item.invariant for item in report.violations}


def test_candidate_rejects_invalid_method_identity_without_a_cohort(tmp_path: Path) -> None:
    """Catches direct candidate validation silently ignoring malformed method evidence."""
    _require_api()
    record = _record()
    baseline = _write_png(tmp_path / "baseline.png")
    candidate = _write_png(tmp_path / "candidate.png")
    run = _run(record)
    run["method"] = {"id": "", "configuration": {"mode": "exact-canvas"}}

    report = validate_cord_candidate(baseline, candidate, record, run)

    assert "methodRunContract" in {item.invariant for item in report.violations}


@pytest.mark.parametrize(
    ("mutation", "invariant"),
    (
        ("dimensions", "canvasDimensions"),
        ("alpha-mode", "alphaCompatibility"),
        ("alpha-values", "alphaCompatibility"),
        ("background", "backgroundFraming"),
        ("transform", "boardTransform"),
        ("appearance", "boardAppearance"),
        ("unrelated", "unrelatedPixels"),
        ("overlay", "overlayAlignment"),
    ),
)
def test_preservation_mutations_fail_the_named_invariant(
    tmp_path: Path, mutation: str, invariant: str
) -> None:
    """Catches acceptance of the alpha, framing, transform, appearance, and overlay regressions."""
    _require_api()
    record = _record()
    baseline = _write_png(tmp_path / "baseline.png")
    candidate = _write_png(tmp_path / "candidate.png")
    run = _run(record)
    preservation = dict(_PRESERVATION)
    run["preservation"] = preservation
    if mutation == "dimensions":
        _write_png(candidate, size=(5, 4))
    elif mutation == "alpha-mode":
        _write_png(candidate, mode="RGB")
    elif mutation == "alpha-values":
        image = Image.open(candidate)
        image.putpixel((0, 0), (240, 235, 220, 255))
        image.save(candidate)
    elif mutation == "background":
        preservation["backgroundFramingPreserved"] = False
    elif mutation == "transform":
        preservation["boardTransformPreserved"] = False
    elif mutation == "appearance":
        preservation["boardAppearancePreserved"] = False
    elif mutation == "unrelated":
        preservation["unrelatedPixelsPreserved"] = False
    else:
        preservation["overlayAlignmentPreserved"] = False

    report = validate_cord_candidate(baseline, candidate, record, run)

    assert report.passed is False
    assert invariant in {violation.invariant for violation in report.violations}


def test_changed_pixels_must_be_exactly_accounted_and_classified_as_cord(tmp_path: Path) -> None:
    """Catches a validator mutation that permits silent or unrelated-pixel edits."""
    _require_api()
    record = _record()
    baseline = _write_png(tmp_path / "baseline.png")
    candidate = _write_png(tmp_path / "candidate.png")
    image = Image.open(candidate)
    image.putpixel((2, 2), (10, 20, 30, 0))
    image.save(candidate)

    missing = validate_cord_candidate(baseline, candidate, record, _run(record))
    unrelated = validate_cord_candidate(
        baseline,
        candidate,
        record,
        _run(
            record,
            changedPixels=[
                {
                    "x": 2,
                    "y": 2,
                    "beforeRGBA": [240, 235, 220, 0],
                    "afterRGBA": [10, 20, 30, 0],
                    "classification": "unrelated",
                }
            ],
        ),
    )

    assert "changedPixelAccounting" in {item.invariant for item in missing.violations}
    assert "unrelatedPixels" in {item.invariant for item in unrelated.violations}


def test_claimed_topology_must_match_source_record(tmp_path: Path) -> None:
    """Catches a method run that invents unsupported doubled or routed strands."""
    _require_api()
    record = _record()
    baseline = _write_png(tmp_path / "baseline.png")
    candidate = _write_png(tmp_path / "candidate.png")

    report = validate_cord_candidate(
        baseline,
        candidate,
        record,
        _run(record, claimedTopology="pairedSideStrands"),
    )

    assert "cordTopology" in {item.invariant for item in report.violations}


@pytest.mark.parametrize(
    ("physics", "invariant"),
    (
        (
            {"loadDirection": "towardCanvasBottom", "cordPaths": [[[0, 0], [1, 1], [0, 3]]]},
            "cordTautness",
        ),
        (
            {"loadDirection": "towardCanvasTop", "cordPaths": [[[0, 3], [0, 0]]]},
            "tensionDirection",
        ),
    ),
)
def test_cord_physics_rejects_slack_paths_and_non_gravity_load(
    tmp_path: Path, physics: dict[str, object], invariant: str
) -> None:
    """Catches acceptance of slack geometry or a canvas-up load vector."""
    _require_api()
    record = _record()
    baseline = _write_png(tmp_path / "baseline.png")
    candidate = _write_png(tmp_path / "candidate.png")

    run = _run(record)
    run_physics = dict(run["physics"])
    run_physics.update(physics)
    run["physics"] = run_physics
    report = validate_cord_candidate(baseline, candidate, record, run)

    assert invariant in {item.invariant for item in report.violations}


@pytest.mark.parametrize(
    "cord_path",
    (
        [[0, 2], [3, 2]],
        [[1, 3], [1, 0]],
        [[1, 0], [1, 5]],
    ),
)
def test_cord_physics_requires_on_canvas_paths_that_end_toward_gravity(
    tmp_path: Path, cord_path: list[list[int]]
) -> None:
    """Catches accepting horizontal, canvas-up, or off-canvas load-path evidence."""
    _require_api()
    record = _record()
    baseline = _write_png(tmp_path / "baseline.png")
    candidate = _write_png(tmp_path / "candidate.png")

    run = _run(record)
    physics = dict(run["physics"])
    physics["cordPaths"] = [cord_path]
    run["physics"] = physics
    report = validate_cord_candidate(baseline, candidate, record, run)

    assert "cordLoadPath" in {item.invariant for item in report.violations}


def test_rotated_or_inverted_alias_cannot_reuse_source_orientation_proof(tmp_path: Path) -> None:
    """Catches mechanically reusing an upright run as proof for an inverted presentation."""
    _require_api()
    record = replace(
        _record(presentation_id="inverted"),
        orientation="inverted",
        source_presentation_id="primary",
    )
    baseline = _write_png(tmp_path / "baseline.png")
    candidate = _write_png(tmp_path / "candidate.png")
    stale_run = _run(record, orientation="upright", sourcePresentationID=None)

    report = validate_cord_candidate(baseline, candidate, record, stale_run)

    assert {item.invariant for item in report.violations} >= {
        "presentationOrientation",
        "sourcePresentationIdentity",
    }


def test_physics_proof_is_bound_to_the_current_alias_and_canvas_gravity(tmp_path: Path) -> None:
    """Catches mechanically rotating a source path while rewriting only top-level alias fields."""
    _require_api()
    record = replace(
        _record(presentation_id="inverted"),
        orientation="inverted",
        source_presentation_id="primary",
    )
    baseline = _write_png(tmp_path / "baseline.png")
    candidate = _write_png(tmp_path / "candidate.png")
    run = _run(record)
    run["physics"] = {
        "proofCaptureID": "fixture.board::primary",
        "orientation": "upright",
        "gravity": "canvasDown",
        "loadDirection": "towardCanvasBottom",
        "cordPaths": [[[1, 0], [1, 3]]],
    }

    report = validate_cord_candidate(baseline, candidate, record, run)

    assert "physicsPresentation" in {item.invariant for item in report.violations}


def test_blocked_source_record_is_never_accepted_by_image_validation(tmp_path: Path) -> None:
    """Catches a gate mutation that promotes an evidence-blocked presentation."""
    _require_api()
    record = replace(_record(), status="blocked", output="blocked", blocker="Routing is unknown.")
    baseline = _write_png(tmp_path / "baseline.png")
    candidate = _write_png(tmp_path / "candidate.png")

    report = validate_cord_candidate(baseline, candidate, record, _run(record))

    assert "sourceBlocker" in {item.invariant for item in report.violations}


def test_cohort_requires_every_named_asset_and_one_method_configuration(tmp_path: Path) -> None:
    """Catches missing feasibility members and product-specific configuration drift."""
    _require_api()
    required = ("fixture.a::primary", "fixture.b::primary", "fixture.c::primary")
    runs = [_candidate_run(tmp_path, capture_id) for capture_id in required]

    passing = validate_cord_method_cohort(runs, required_capture_ids=required)
    missing = validate_cord_method_cohort(runs[:-1], required_capture_ids=required)
    different_evidence = dict(runs[-1].evidence)
    different_evidence["method"] = {
        "id": "fixture-noop",
        "intent": "negativeControl",
        "configuration": {"mode": "per-product"},
    }
    different = validate_cord_method_cohort(
        [*runs[:-1], replace(runs[-1], evidence=different_evidence)],
        required_capture_ids=required,
    )

    assert passing.passed is True
    assert passing.method_id == "fixture-noop"
    assert len(passing.configuration_sha256) == 64
    assert "cohortCompleteness" in {item.invariant for item in missing.violations}
    assert "methodConfiguration" in {item.invariant for item in different.violations}


def test_cohort_report_is_json_serializable(tmp_path: Path) -> None:
    """Catches returning path or dataclass objects that the CLI cannot emit."""
    _require_api()
    required = ("fixture.a::primary", "fixture.b::primary", "fixture.c::primary")
    report = validate_cord_method_cohort(
        [_candidate_run(tmp_path, capture_id) for capture_id in required],
        required_capture_ids=required,
    )

    json.dumps(report.to_json())


def test_negative_control_cohort_can_validate_without_being_promoted(tmp_path: Path) -> None:
    """Catches presenting the unchanged infrastructure control as an editing-method promotion."""
    _require_api()
    required = ("fixture.a::primary", "fixture.b::primary", "fixture.c::primary")
    runs = [_candidate_run(tmp_path, capture_id) for capture_id in required]
    for index, run in enumerate(runs):
        evidence = dict(run.evidence)
        evidence["method"] = {
            "id": "fixture-noop",
            "intent": "negativeControl",
            "configuration": {"mode": "exact-canvas"},
        }
        runs[index] = replace(run, evidence=evidence)

    report = validate_cord_method_cohort(runs, required_capture_ids=required)

    assert report.passed is True
    assert report.promoted is False
    assert report.to_json()["methodIntent"] == "negativeControl"
    assert report.to_json()["promoted"] is False


def test_gate_cli_fail_closed_replays_the_three_required_live_assets_with_one_configuration(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """Catches a CLI replay that invents physics evidence or promotes the unchanged control."""
    required = (
        "aelith.cyclops-011::primary",
        "captain-fingerfood.dual::primary",
        "lattice.mxedge-lift-large::primary",
    )
    hangboards = _REPOSITORY_ROOT / "Hangboards"
    ledger_path = (
        _REPOSITORY_ROOT
        / "docs"
        / "source-audits"
        / "2026-09-01-tensioned-cord-presentations.json"
    )
    ledger = load_tensioned_cord_ledger(ledger_path)
    records = {f"{record.package_id}::{record.presentation_id}": record for record in ledger.records}
    packages = {
        package.board.id: package
        for package in discover_board_packages(hangboards, require_complete_inventory=True).packages
    }
    run_values: list[dict[str, object]] = []
    for capture_id in required:
        record = records[capture_id]
        source = packages[record.package_id].root / record.asset_path
        stem = capture_id.replace("::", "--")
        baseline = tmp_path / f"{stem}-baseline.png"
        candidate = tmp_path / f"{stem}-candidate.png"
        shutil.copyfile(source, baseline)
        shutil.copyfile(source, candidate)
        evidence = _run(record)
        physics = dict(evidence["physics"])
        physics["cordPaths"] = []
        evidence["physics"] = physics
        run_values.append(
            {
                "captureID": capture_id,
                "baselinePath": baseline.name,
                "candidatePath": candidate.name,
                "evidence": evidence,
            }
        )
    cohort = tmp_path / "cohort.json"
    cohort.write_text(json.dumps({"schemaVersion": 1, "runs": run_values}), encoding="utf-8")

    result = cli_main(
        [
            "gate-tensioned-cord-method",
            "--root",
            str(hangboards),
            "--ledger",
            str(ledger_path),
            "--cohort",
            str(cohort),
            *[
                argument
                for capture_id in required
                for argument in ("--required-capture-id", capture_id)
            ],
        ]
    )

    assert result == 1
    output = json.loads(capsys.readouterr().out)
    assert output["passed"] is False
    assert output["promoted"] is False
    assert output["methodIntent"] == "negativeControl"
    assert output["requiredCaptureIDs"] == list(required)
    assert {
        candidate["captureID"]: [violation["invariant"] for violation in candidate["violations"]]
        for candidate in output["candidates"]
    } == {capture_id: ["cordTautness"] for capture_id in required}
