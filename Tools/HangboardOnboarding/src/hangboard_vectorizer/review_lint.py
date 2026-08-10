"""Lint edited hold-region reviews against the generated baseline."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
import json
import math
import os
from pathlib import Path
import tempfile
from typing import Literal

from .review_artifacts import ReviewRun, load_json, sha256_file

_ALLOWED_TYPES = frozenset({"pocket", "edge", "sloper", "jug"})
_ALLOWED_MODES = frozenset({"aperture", "surface"})


@dataclass(frozen=True)
class LintIssue:
    severity: Literal["error", "warning"]
    code: str
    path: str
    message: str


@dataclass(frozen=True)
class LintReport:
    passed: bool
    issues: tuple[LintIssue, ...]
    baseline_sha256: str
    edited_sha256: str


def lint_review(
    run: ReviewRun, profile: Mapping[str, object] | None = None
) -> LintReport:
    """Validate one edited Stage 2 review run."""
    del profile
    if run.edited_regions is None:
        raise ValueError("edited regions artifact is missing")
    if run.corrections is None:
        raise ValueError("review corrections artifact is missing")

    baseline = load_json(run.stage2_regions, "stage-2 baseline")
    edited = load_json(run.edited_regions, "stage-2 edited regions")
    corrections = load_json(run.corrections, "stage-2 review corrections")

    issues: list[LintIssue] = []
    canvas = _validate_canvas(edited, issues)
    edited_regions = _validate_regions(edited, canvas, issues)
    baseline_regions = _regions_by_id(baseline.get("regions"))
    _validate_corrections(corrections, baseline_regions, edited_regions, issues)

    ordered = tuple(
        sorted(issues, key=lambda issue: (issue.severity, issue.code, issue.path))
    )
    return LintReport(
        passed=not ordered,
        issues=ordered,
        baseline_sha256=sha256_file(run.stage2_regions),
        edited_sha256=sha256_file(run.edited_regions),
    )


def write_lint_report(run: ReviewRun, report: LintReport) -> Path:
    """Persist one lint report beside the edited Stage 2 artifact."""
    if run.edited_regions is None:
        raise ValueError("edited regions artifact is missing")
    path = _confined_stage2_dir(run) / "lint-report.json"
    payload = lint_report_payload(report)
    _atomic_write_json(path, payload)
    return path


def lint_report_payload(report: LintReport) -> dict[str, object]:
    return {
        "baselineSha256": report.baseline_sha256,
        "editedSha256": report.edited_sha256,
        "issues": [
            {
                "severity": issue.severity,
                "code": issue.code,
                "path": issue.path,
                "message": issue.message,
            }
            for issue in report.issues
        ],
        "passed": report.passed,
    }


def _validate_canvas(
    document: Mapping[str, object], issues: list[LintIssue]
) -> tuple[float, float] | None:
    canvas = document.get("canvas")
    if not isinstance(canvas, Mapping):
        issues.append(
            LintIssue("error", "canvas.missing", "canvas", "canvas must be a JSON object")
        )
        return None
    width = canvas.get("width")
    height = canvas.get("height")
    width_value = _positive_number(width)
    height_value = _positive_number(height)
    if width_value is None:
        issues.append(
            LintIssue(
                "error",
                "canvas.width-positive",
                "canvas.width",
                "canvas width must be a positive finite number",
            )
        )
    if height_value is None:
        issues.append(
            LintIssue(
                "error",
                "canvas.height-positive",
                "canvas.height",
                "canvas height must be a positive finite number",
            )
        )
    if width_value is None or height_value is None:
        return None
    return (width_value, height_value)


def _validate_regions(
    document: Mapping[str, object],
    canvas: tuple[float, float] | None,
    issues: list[LintIssue],
) -> dict[int, Mapping[str, object]]:
    raw_regions = document.get("regions")
    if not isinstance(raw_regions, list):
        issues.append(
            LintIssue("error", "regions.missing", "regions", "regions must be a JSON array")
        )
        return {}

    seen_ids: set[int] = set()
    indexed: dict[int, Mapping[str, object]] = {}
    for index, region in enumerate(raw_regions):
        region_path = f"regions[{index}]"
        if not isinstance(region, Mapping):
            issues.append(
                LintIssue("error", "region.object", region_path, "region must be a JSON object")
            )
            continue
        region_id = region.get("id")
        if not _is_int(region_id):
            issues.append(
                LintIssue(
                    "error",
                    "region.id-integer",
                    f"{region_path}.id",
                    "region id must be an integer",
                )
            )
        else:
            if region_id in seen_ids:
                issues.append(
                    LintIssue(
                        "error",
                        "region.id-unique",
                        f"{region_path}.id",
                        "region ids must be unique within the document",
                    )
                )
            else:
                seen_ids.add(region_id)
                indexed[region_id] = region

        if not isinstance(region.get("key"), str) or not region["key"].strip():
            issues.append(
                LintIssue(
                    "error",
                    "region.key-non-empty",
                    f"{region_path}.key",
                    "region key must be a non-empty string",
                )
            )
        if region.get("type") not in _ALLOWED_TYPES:
            issues.append(
                LintIssue(
                    "error",
                    "region.type-recognized",
                    f"{region_path}.type",
                    "region type must be one of pocket, edge, sloper, or jug",
                )
            )
        if region.get("mode") not in _ALLOWED_MODES:
            issues.append(
                LintIssue(
                    "error",
                    "region.mode-recognized",
                    f"{region_path}.mode",
                    "region mode must be aperture or surface",
                )
            )

        points = _points(region.get("contour"))
        if points is None:
            issues.append(
                LintIssue(
                    "error",
                    "contour.min-points",
                    f"{region_path}.contour",
                    "contour must contain at least three finite points",
                )
            )
            continue
        if _shoelace_area(points) <= 0:
            issues.append(
                LintIssue(
                    "error",
                    "contour.area-positive",
                    f"{region_path}.contour",
                    "contour shoelace area must be positive",
                )
            )
        if canvas is not None:
            width, height = canvas
            for point_index, (x, y) in enumerate(points):
                if x < 0 or y < 0 or x > width or y > height:
                    issues.append(
                        LintIssue(
                            "error",
                            "contour.out-of-bounds",
                            f"{region_path}.contour[{point_index}]",
                            "contour points must stay inside the canvas",
                        )
                    )
    return indexed


def _validate_corrections(
    corrections: Mapping[str, object],
    baseline_regions: Mapping[int, Mapping[str, object]],
    edited_regions: Mapping[int, Mapping[str, object]],
    issues: list[LintIssue],
) -> None:
    _validate_correction_entries(
        corrections.get("modified"),
        "modified",
        baseline_regions,
        edited_regions,
        issues,
    )
    _validate_correction_entries(
        corrections.get("added"),
        "added",
        {},
        edited_regions,
        issues,
    )
    _validate_correction_entries(
        corrections.get("deleted"),
        "deleted",
        baseline_regions,
        {},
        issues,
    )


def _validate_correction_entries(
    raw_entries: object,
    kind: Literal["modified", "added", "deleted"],
    baseline_regions: Mapping[int, Mapping[str, object]],
    edited_regions: Mapping[int, Mapping[str, object]],
    issues: list[LintIssue],
) -> None:
    path = f"corrections.{kind}"
    if raw_entries is None:
        return
    if not isinstance(raw_entries, list):
        issues.append(
            LintIssue(
                "error",
                f"corrections.{kind}-list",
                path,
                f"{kind} corrections must be a JSON array",
            )
        )
        return

    for index, entry in enumerate(raw_entries):
        entry_path = f"{path}[{index}]"
        if not isinstance(entry, Mapping) or not _is_int(entry.get("id")):
            issues.append(
                LintIssue(
                    "error",
                    f"corrections.{kind}-entry",
                    entry_path,
                    f"{kind} correction entries must include an integer id",
                )
            )
            continue
        expected = _expected_correction_entry(
            kind, int(entry["id"]), baseline_regions, edited_regions
        )
        if expected is None or _canonical_json_bytes(entry) != _canonical_json_bytes(expected):
            issues.append(
                LintIssue(
                    "error",
                    f"corrections.{kind}-mismatch",
                    entry_path,
                    f"{kind} correction entry does not match the baseline and edited documents",
                )
            )


def _expected_correction_entry(
    kind: Literal["modified", "added", "deleted"],
    region_id: int,
    baseline_regions: Mapping[int, Mapping[str, object]],
    edited_regions: Mapping[int, Mapping[str, object]],
) -> dict[str, object] | None:
    if kind == "modified":
        baseline = baseline_regions.get(region_id)
        edited = edited_regions.get(region_id)
        if baseline is None or edited is None:
            return None
        baseline_identity = _region_identity(baseline)
        edited_identity = _region_identity(edited)
        return edited_identity if baseline_identity == edited_identity else None
    if kind == "added":
        if region_id in baseline_regions:
            return None
        edited = edited_regions.get(region_id)
        return _region_identity(edited) if edited is not None else None
    if region_id in edited_regions:
        return None
    baseline = baseline_regions.get(region_id)
    return _region_identity(baseline) if baseline is not None else None


def _region_identity(region: Mapping[str, object] | None) -> dict[str, object] | None:
    if region is None or not _is_int(region.get("id")) or not isinstance(region.get("key"), str):
        return None
    return {"id": int(region["id"]), "key": region["key"]}


def _regions_by_id(raw_regions: object) -> dict[int, Mapping[str, object]]:
    if not isinstance(raw_regions, list):
        return {}
    indexed: dict[int, Mapping[str, object]] = {}
    for region in raw_regions:
        if isinstance(region, Mapping) and _is_int(region.get("id")):
            indexed[int(region["id"])] = region
    return indexed


def _points(raw_contour: object) -> list[tuple[float, float]] | None:
    if not isinstance(raw_contour, list) or len(raw_contour) < 3:
        return None
    points: list[tuple[float, float]] = []
    for raw_point in raw_contour:
        if not isinstance(raw_point, list | tuple) or len(raw_point) != 2:
            return None
        x = _finite_number(raw_point[0])
        y = _finite_number(raw_point[1])
        if x is None or y is None:
            return None
        points.append((x, y))
    return points


def _positive_number(value: object) -> float | None:
    number = _finite_number(value)
    if number is None or number <= 0:
        return None
    return number


def _finite_number(value: object) -> float | None:
    if isinstance(value, bool) or not isinstance(value, int | float):
        return None
    number = float(value)
    return number if math.isfinite(number) else None


def _is_int(value: object) -> bool:
    return isinstance(value, int) and not isinstance(value, bool)


def _shoelace_area(points: list[tuple[float, float]]) -> float:
    total = 0.0
    for index, (x1, y1) in enumerate(points):
        x2, y2 = points[(index + 1) % len(points)]
        total += (x1 * y2) - (x2 * y1)
    return total / 2.0


def _canonical_json_bytes(value: Mapping[str, object]) -> bytes:
    return json.dumps(
        value, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False
    ).encode("utf-8")


def _confined_stage2_dir(run: ReviewRun) -> Path:
    if run.edited_regions is None:
        raise ValueError("edited regions artifact is missing")
    stage2_dir = run.edited_regions.parent.resolve(strict=False)
    stage2_dir.relative_to(run.root)
    return stage2_dir


def _atomic_write_json(path: Path, payload: Mapping[str, object]) -> None:
    directory = path.parent
    directory.mkdir(parents=True, exist_ok=True)
    descriptor, temporary_name = tempfile.mkstemp(
        prefix=f".{path.name}.tmp-", suffix=".json", dir=directory
    )
    temporary_path = Path(temporary_name)
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
            handle.write(json.dumps(payload, sort_keys=True, separators=(",", ":")))
            handle.write("\n")
        temporary_path.replace(path)
    finally:
        temporary_path.unlink(missing_ok=True)
