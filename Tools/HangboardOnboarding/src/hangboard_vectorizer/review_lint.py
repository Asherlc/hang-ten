"""Lint edited hold-region reviews against the generated baseline."""

from __future__ import annotations

from collections.abc import Mapping
from copy import deepcopy
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
    baseline_regions = _normalized_baseline_regions(baseline.get("regions"))
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
        if _region_mode(region) not in _ALLOWED_MODES:
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
    if corrections.get("schemaVersion") != 1:
        issues.append(
            LintIssue(
                "error",
                "corrections.schema-version",
                "corrections.schemaVersion",
                "corrections schemaVersion must be 1",
            )
        )

    baseline_ids = set(baseline_regions)
    edited_ids = set(edited_regions)
    expected_ids = {
        "added": edited_ids - baseline_ids,
        "deleted": baseline_ids - edited_ids,
        "modified": {
            region_id
            for region_id in baseline_ids & edited_ids
            if _comparison_signature(baseline_regions[region_id])
            != _comparison_signature(edited_regions[region_id])
        },
    }
    for kind in ("modified", "added", "deleted"):
        _validate_correction_entries(
            corrections.get(kind),
            kind,
            expected_ids[kind],
            baseline_regions,
            edited_regions,
            issues,
        )


def _validate_correction_entries(
    raw_entries: object,
    kind: Literal["modified", "added", "deleted"],
    expected_ids: set[int],
    baseline_regions: Mapping[int, Mapping[str, object]],
    edited_regions: Mapping[int, Mapping[str, object]],
    issues: list[LintIssue],
) -> None:
    path = f"corrections.{kind}"
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

    found_ids: set[int] = set()
    for index, entry in enumerate(raw_entries):
        entry_path = f"{path}[{index}]"
        region_id = _correction_entry_id(entry, kind)
        if region_id is None:
            issues.append(
                LintIssue(
                    "error",
                    f"corrections.{kind}-entry",
                    entry_path,
                    _correction_entry_message(kind),
                )
            )
            continue
        if region_id in found_ids:
            issues.append(
                LintIssue(
                    "error",
                    f"corrections.{kind}-duplicate",
                    entry_path,
                    f"{kind} correction contains duplicate region id {region_id}",
                )
            )
        found_ids.add(region_id)
        expected = _expected_correction_entry(
            kind, region_id, baseline_regions, edited_regions
        )
        if region_id not in expected_ids or expected is None or entry != expected:
            issues.append(
                LintIssue(
                    "error",
                    f"corrections.{kind}-mismatch",
                    entry_path,
                    f"{kind} correction entry does not match the baseline and edited documents",
                )
            )

    for region_id in sorted(expected_ids - found_ids):
        issues.append(
            LintIssue(
                "error",
                f"corrections.{kind}-missing",
                path,
                f"{kind} correction is missing region id {region_id}",
            )
        )


def _expected_correction_entry(
    kind: Literal["modified", "added", "deleted"],
    region_id: int,
    baseline_regions: Mapping[int, Mapping[str, object]],
    edited_regions: Mapping[int, Mapping[str, object]],
) -> Mapping[str, object] | None:
    if kind == "modified":
        baseline = baseline_regions.get(region_id)
        edited = edited_regions.get(region_id)
        if baseline is None or edited is None:
            return None
        return {
            "before": _editor_export_region(baseline),
            "after": edited,
        }
    if kind == "added":
        if region_id in baseline_regions:
            return None
        return edited_regions.get(region_id)
    if region_id in edited_regions:
        return None
    baseline = baseline_regions.get(region_id)
    return _region_identity(baseline) if baseline is not None else None


def _correction_entry_id(
    entry: object, kind: Literal["modified", "added", "deleted"]
) -> int | None:
    if not isinstance(entry, Mapping):
        return None
    if kind != "modified":
        value = entry.get("id")
        return int(value) if _is_int(value) else None
    before = entry.get("before")
    after = entry.get("after")
    if not isinstance(before, Mapping) or not isinstance(after, Mapping):
        return None
    before_id = before.get("id")
    after_id = after.get("id")
    if not _is_int(before_id) or not _is_int(after_id) or before_id != after_id:
        return None
    return int(after_id)


def _correction_entry_message(kind: str) -> str:
    if kind == "modified":
        return "modified correction entries must contain before and after regions with the same integer id"
    if kind == "added":
        return "added correction entries must contain the full added region with an integer id"
    return "deleted correction entries must include an integer id"


def _region_identity(region: Mapping[str, object] | None) -> dict[str, object] | None:
    if region is None or not _is_int(region.get("id")) or not isinstance(region.get("key"), str):
        return None
    return {"id": int(region["id"]), "key": region["key"]}


def _normalized_baseline_regions(
    raw_regions: object,
) -> dict[int, Mapping[str, object]]:
    if not isinstance(raw_regions, list):
        return {}
    indexed: dict[int, Mapping[str, object]] = {}
    for index, region in enumerate(raw_regions):
        if not isinstance(region, Mapping):
            continue
        normalized = _normalize_editor_region(region, index + 1)
        indexed[int(normalized["id"])] = normalized
    return indexed


def _normalize_editor_region(
    region: Mapping[str, object], fallback_id: int
) -> dict[str, object]:
    normalized = deepcopy(dict(region))
    source_id = region.get("id", fallback_id)
    numeric_id = _numeric_id(source_id)
    region_id = numeric_id if numeric_id is not None and numeric_id > 0 else fallback_id
    key = region.get("key")
    if not key:
        key = (
            source_id
            if isinstance(source_id, str)
            else f"grip-{region_id:03d}"
        )
    grip_type = region.get("type") or "edge"
    raw_contour = region.get("contour") or region.get("points") or []
    contour = [
        [_js_number(point[0]), _js_number(point[1])]
        for point in raw_contour
        if isinstance(point, list | tuple) and len(point) == 2
    ]
    raw_metadata = region.get("metadata")
    metadata_source = dict(raw_metadata) if isinstance(raw_metadata, Mapping) else {}
    metadata = {
        "mode": metadata_source.get("mode")
        or region.get("mode")
        or region.get("visualMode")
        or ("aperture" if grip_type == "pocket" else "surface"),
        "shapeKind": metadata_source.get("shapeKind") or "freeform",
        "pathStyle": metadata_source.get("pathStyle") or "straight",
        "curveTension": _js_number(metadata_source.get("curveTension", 0.8)),
        "humanNotes": metadata_source.get("humanNotes") or "",
        **metadata_source,
    }
    if isinstance(source_id, str) and not source_id.isdigit():
        metadata["sourceRegionId"] = source_id
    normalized.update(
        id=region_id,
        key=key,
        type=grip_type,
        contour=contour,
        metadata=metadata,
    )
    return normalized


def _editor_export_region(region: Mapping[str, object]) -> dict[str, object]:
    exported = deepcopy(dict(region))
    contour = [
        [_js_round(_js_number(point[0])), _js_round(_js_number(point[1]))]
        for point in region.get("contour", [])
        if isinstance(point, list | tuple) and len(point) == 2
    ]
    xs = [point[0] for point in contour]
    ys = [point[1] for point in contour]
    metadata = region.get("metadata")
    exported.update(
        anchor=[
            _js_round(sum(xs) / len(xs)),
            _js_round(sum(ys) / len(ys)),
        ],
        areaPixels=int(math.floor(abs(_shoelace_area([(x, y) for x, y in contour])) + 0.5)),
        bounds=[
            _js_round(min(xs)),
            _js_round(min(ys)),
            _js_round(max(xs)),
            _js_round(max(ys)),
        ],
        contour=contour,
        metadata={
            **(dict(metadata) if isinstance(metadata, Mapping) else {}),
            "editedBy": "hold-highlight-editor",
        },
    )
    return exported


def _comparison_signature(region: Mapping[str, object]) -> dict[str, object]:
    metadata = region.get("metadata")
    metadata_mapping = metadata if isinstance(metadata, Mapping) else {}
    return {
        "key": region.get("key"),
        "type": region.get("type"),
        "contour": [
            [_js_round(_js_number(point[0])), _js_round(_js_number(point[1]))]
            for point in region.get("contour", [])
            if isinstance(point, list | tuple) and len(point) == 2
        ],
        "mode": _region_mode(region),
        "shapeKind": metadata_mapping.get("shapeKind") or "freeform",
        "pathStyle": metadata_mapping.get("pathStyle") or "straight",
        "curveTension": _js_round(
            _js_number(metadata_mapping.get("curveTension", 0.8))
        ),
        "rotation": _js_round(_js_number(metadata_mapping.get("rotation", 0))),
        "bend": _js_round(_js_number(metadata_mapping.get("bend", 0))),
        "notes": metadata_mapping.get("humanNotes") or "",
    }


def _region_mode(region: Mapping[str, object]) -> object:
    metadata = region.get("metadata")
    if isinstance(metadata, Mapping) and metadata.get("mode") is not None:
        return metadata.get("mode")
    return region.get("mode", region.get("visualMode"))


def _numeric_id(value: object) -> int | None:
    if _is_int(value):
        return int(value)
    if isinstance(value, str):
        try:
            numeric = float(value)
        except ValueError:
            return None
        if numeric.is_integer():
            return int(numeric)
    return None


def _js_number(value: object) -> float | int:
    if isinstance(value, bool):
        return int(value)
    if isinstance(value, int | float):
        return value
    try:
        return float(str(value))
    except ValueError:
        return math.nan


def _js_round(value: float | int, digits: int = 2) -> float | int:
    factor = 10**digits
    rounded = math.floor(float(value) * factor + 0.5) / factor
    return int(rounded) if rounded.is_integer() else rounded


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
