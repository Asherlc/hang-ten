"""Catalog-generic, image-only hold geometry candidate derivation.

Candidates are deliberately unlabeled. Package semantics enter only at the
separate, complete, hash-bound materialization boundary.
"""

from __future__ import annotations

import hashlib
import importlib.util
import json
import math
import sys
from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from pathlib import Path

import cv2
import numpy as np
from PIL import Image

from .board_catalog import load_board_package
from .board_path_simplification import (
    NativeContourError,
    measure_native_contour_error,
    simplify_native_contour,
)
from .board_presentation import visible_foreground_mask

_WORKBENCH_GEOMETRY_PATH = (
    Path(__file__).resolve().parents[3] / "HangboardWorkbench" / "board_geometry.py"
)
_WORKBENCH_SPEC = importlib.util.spec_from_file_location(
    "hangboard_derivation_workbench_geometry", _WORKBENCH_GEOMETRY_PATH
)
if _WORKBENCH_SPEC is None or _WORKBENCH_SPEC.loader is None:
    raise ImportError("Hangboard Workbench geometry codec is unavailable")
_WORKBENCH_GEOMETRY = importlib.util.module_from_spec(_WORKBENCH_SPEC)
sys.modules[_WORKBENCH_SPEC.name] = _WORKBENCH_GEOMETRY
_WORKBENCH_SPEC.loader.exec_module(_WORKBENCH_GEOMETRY)

GeometryError = _WORKBENCH_GEOMETRY.GeometryError
display_path_for_shape = _WORKBENCH_GEOMETRY.display_path_for_shape
parse_closed_path = _WORKBENCH_GEOMETRY.parse_closed_path
shape_for_path = _WORKBENCH_GEOMETRY.shape_for_path


_SCHEMA_VERSION = 1
_ALGORITHM_VERSION = "catalog-generic-v1"
_SCALE_FRACTIONS = (0.05, 0.10, 0.20, 0.30)
_THRESHOLD_OFFSETS = (-1, 0, 1)
_MINIMUM_COMPONENT_AREA_FRACTION = 0.0005
_MINIMUM_COMPONENT_AREA_PIXELS = 9
_MORPHOLOGY_GAP_FRACTION = 0.01
_ROUNDED_RECT_RADIUS_STEPS = 20

Point = tuple[float, float]
Bounds = tuple[int, int, int, int]


@dataclass(frozen=True)
class GeometryCandidate:
    candidate_id: str
    source: str
    polarity: str | None
    bounds: Bounds
    display_path: str
    representation: str
    point_count: int
    maximum_boundary_deviation_pixels: float
    symmetric_difference_ratio: float
    topology_stable: bool
    mask_hash: str
    path_hash: str
    _frame: Mapping[str, float] = field(repr=False, compare=False)
    _shape: Mapping[str, object] = field(repr=False, compare=False)
    _contour: tuple[Point, ...] = field(repr=False, compare=False)

    def manifest(self) -> dict[str, object]:
        return {
            "bounds": list(self.bounds),
            "candidateID": self.candidate_id,
            "displayPath": self.display_path,
            "maskHash": self.mask_hash,
            "maximumBoundaryDeviationPixels": round(
                self.maximum_boundary_deviation_pixels, 12
            ),
            "pathHash": self.path_hash,
            "pointCount": self.point_count,
            "polarity": self.polarity,
            "representation": self.representation,
            "source": self.source,
            "symmetricDifferenceRatio": round(self.symmetric_difference_ratio, 12),
            "topologyStable": self.topology_stable,
        }


@dataclass(frozen=True)
class CandidateRejection:
    source: str
    polarity: str | None
    bounds: Bounds | None
    reason: str

    def manifest(self) -> dict[str, object]:
        return {
            "bounds": list(self.bounds) if self.bounds is not None else None,
            "polarity": self.polarity,
            "reason": self.reason,
            "source": self.source,
        }


@dataclass(frozen=True)
class GeometryCandidateReport:
    package_root: Path
    image_hash: str
    width: int
    height: int
    foreground_ambiguous: bool
    scales: tuple[int, ...]
    thresholds: tuple[Mapping[str, object], ...]
    candidates: tuple[GeometryCandidate, ...]
    rejections: tuple[CandidateRejection, ...]
    reflection_axis_x: float | None
    symmetry_pairs: tuple[tuple[str, str], ...]

    def _payload_without_hash(self) -> dict[str, object]:
        return {
            "algorithmVersion": _ALGORITHM_VERSION,
            "candidates": [candidate.manifest() for candidate in self.candidates],
            "canvas": {"height": self.height, "width": self.width},
            "foregroundAmbiguous": self.foreground_ambiguous,
            "imageHash": self.image_hash,
            "parameters": {
                "morphologyGapFraction": _MORPHOLOGY_GAP_FRACTION,
                "scaleFractions": list(_SCALE_FRACTIONS),
                "scales": list(self.scales),
                "thresholdOffsets": list(_THRESHOLD_OFFSETS),
                "thresholds": [dict(threshold) for threshold in self.thresholds],
            },
            "reflectionAxisX": self.reflection_axis_x,
            "rejections": [rejection.manifest() for rejection in self.rejections],
            "schemaVersion": _SCHEMA_VERSION,
            "symmetryPairs": [list(pair) for pair in self.symmetry_pairs],
        }

    @property
    def manifest_hash(self) -> str:
        return hashlib.sha256(_canonical_json(self._payload_without_hash())).hexdigest()

    def manifest(self) -> dict[str, object]:
        payload = self._payload_without_hash()
        payload["manifestHash"] = self.manifest_hash
        return payload

    def manifest_bytes(self) -> bytes:
        return (
            json.dumps(
                self.manifest(), indent=2, sort_keys=True, separators=(",", ": ")
            ).encode("utf-8")
            + b"\n"
        )


@dataclass(frozen=True)
class _RawCandidate:
    source: str
    polarity: str | None
    mask: np.ndarray
    topology_stable: bool


def derive_geometry_candidates(package_root: Path) -> GeometryCandidateReport:
    """Derive deterministic unlabeled candidates from only ``primary.png``.

    Loading the package first enforces the direct-package contract. The
    detector receives only decoded pixels and canvas dimensions; board IDs,
    hold IDs, existing geometry, and product metadata never enter its inputs or
    output manifest.
    """
    package = load_board_package(package_root)
    primary_path = package.root / "assets" / "primary.png"
    image_bytes = primary_path.read_bytes()
    try:
        with Image.open(primary_path) as opened:
            opened.load()
            image = opened.convert("RGBA")
    except (OSError, ValueError) as error:
        raise ValueError(
            f"assets/primary.png must be a decodable PNG image: {error}"
        ) from error

    width, height = image.size
    foreground, foreground_ambiguous = visible_foreground_mask(image)
    scales = _canvas_scales(width, height)
    minimum_area = max(
        _MINIMUM_COMPONENT_AREA_PIXELS,
        math.ceil(width * height * _MINIMUM_COMPONENT_AREA_FRACTION),
    )

    raw_candidates: list[_RawCandidate] = []
    rejections: list[CandidateRejection] = []
    silhouettes, silhouette_rejections = _silhouette_candidates(
        foreground, minimum_area=minimum_area
    )
    raw_candidates.extend(silhouettes)
    rejections.extend(silhouette_rejections)

    rgba = np.asarray(image)
    rgb = np.ascontiguousarray(rgba[:, :, :3])
    luminance = cv2.cvtColor(rgb, cv2.COLOR_RGB2LAB)[:, :, 0]
    residuals, thresholds, residual_rejections = _residual_candidates(
        luminance,
        foreground,
        scales=scales,
        minimum_area=minimum_area,
        width=width,
        height=height,
    )
    raw_candidates.extend(residuals)
    rejections.extend(residual_rejections)

    raw_candidates = _deduplicate_raw(raw_candidates, width=width, height=height)
    candidates: list[GeometryCandidate] = []
    for raw in raw_candidates:
        try:
            candidates.append(_materialize_candidate(raw, width=width, height=height))
        except (GeometryError, ValueError):
            rejections.append(
                CandidateRejection(
                    raw.source,
                    raw.polarity,
                    _mask_bounds(raw.mask),
                    "invalidSimpleContour",
                )
            )

    candidates.sort(
        key=lambda candidate: (
            candidate.bounds[1],
            candidate.bounds[0],
            candidate.bounds[3],
            candidate.bounds[2],
            candidate.source,
            candidate.polarity or "",
            candidate.candidate_id,
        )
    )
    reflection_axis = _reflection_axis(foreground)
    symmetry_pairs = _symmetry_pairs(
        candidates, reflection_axis, width=width, height=height
    )
    rejections.sort(
        key=lambda rejection: (
            rejection.bounds is None,
            rejection.bounds or (0, 0, 0, 0),
            rejection.source,
            rejection.polarity or "",
            rejection.reason,
        )
    )
    return GeometryCandidateReport(
        package_root=package.root,
        image_hash=hashlib.sha256(image_bytes).hexdigest(),
        width=width,
        height=height,
        foreground_ambiguous=foreground_ambiguous,
        scales=scales,
        thresholds=tuple(thresholds),
        candidates=tuple(candidates),
        rejections=tuple(rejections),
        reflection_axis_x=reflection_axis,
        symmetry_pairs=tuple(symmetry_pairs),
    )


def materialize_editor_document(
    package_root: Path, accepted_mapping: Mapping[str, object]
) -> dict[str, object]:
    """Return a complete Workbench document after fail-closed mapping checks."""
    package = load_board_package(package_root)
    source = json.loads((package.root / "board.json").read_text(encoding="utf-8"))
    report = derive_geometry_candidates(package.root)
    _exact_keys(
        accepted_mapping,
        {"schemaVersion", "manifestHash", "holds", "rejectedCandidateIDs", "symmetry"},
        "accepted mapping",
    )
    if accepted_mapping["schemaVersion"] != _SCHEMA_VERSION:
        raise ValueError("accepted mapping schemaVersion is unsupported")
    if accepted_mapping["manifestHash"] != report.manifest_hash:
        raise ValueError(
            "accepted mapping manifest hash does not match the candidate report"
        )

    mappings = accepted_mapping["holds"]
    if not isinstance(mappings, list):
        raise ValueError("accepted mapping holds must be an array")
    expected_holds = source["holds"]
    if len(mappings) != len(expected_holds):
        raise ValueError("accepted mapping must cover every audited hold")

    candidate_by_id = {
        candidate.candidate_id: candidate for candidate in report.candidates
    }
    assigned: set[str] = set()
    selected: list[tuple[dict[str, object], list[GeometryCandidate]]] = []
    for index, (mapping, hold) in enumerate(zip(mappings, expected_holds, strict=True)):
        if not isinstance(mapping, Mapping):
            raise ValueError(f"accepted mapping holds[{index}] must be an object")
        _exact_keys(
            mapping, {"holdID", "candidateIDs"}, f"accepted mapping holds[{index}]"
        )
        if mapping["holdID"] != hold["id"]:
            raise ValueError(
                "accepted mapping must cover every audited hold in source order"
            )
        candidate_ids = mapping["candidateIDs"]
        if not isinstance(candidate_ids, list) or not all(
            isinstance(candidate_id, str) for candidate_id in candidate_ids
        ):
            raise ValueError("accepted mapping candidateIDs must be an array of IDs")
        if len(candidate_ids) != len(hold["geometry"]):
            raise ValueError("accepted mapping must map every audited hold piece")
        pieces: list[GeometryCandidate] = []
        for candidate_id in candidate_ids:
            if candidate_id in assigned:
                raise ValueError("candidate ID is assigned more than once")
            candidate = candidate_by_id.get(candidate_id)
            if candidate is None:
                raise ValueError("accepted mapping references an unknown candidate ID")
            assigned.add(candidate_id)
            pieces.append(candidate)
        selected.append((hold, pieces))

    rejected = accepted_mapping["rejectedCandidateIDs"]
    if not isinstance(rejected, list) or not all(
        isinstance(candidate_id, str) for candidate_id in rejected
    ):
        raise ValueError("rejectedCandidateIDs must be an array of IDs")
    for candidate_id in rejected:
        if candidate_id in assigned:
            raise ValueError("candidate ID is assigned more than once")
        if candidate_id not in candidate_by_id:
            raise ValueError("accepted mapping rejects an unknown candidate ID")
        assigned.add(candidate_id)
    if assigned != set(candidate_by_id):
        raise ValueError("accepted mapping must map or reject every candidate ID")

    _validate_symmetry_mapping(accepted_mapping["symmetry"], report)

    regions: list[dict[str, object]] = []
    region_id = 1
    for hold, pieces in selected:
        for piece_index, candidate in enumerate(pieces):
            parsed = parse_closed_path(
                candidate.display_path,
                report.width,
                report.height,
                label=f"candidate {candidate.candidate_id}",
            )
            frame, shape = shape_for_path(parsed, report.width, report.height)
            round_trip = display_path_for_shape(
                frame.to_json(),
                shape,
                report.width,
                report.height,
                label=f"candidate {candidate.candidate_id}",
            )
            if round_trip.data != parsed.data:
                raise ValueError("candidate failed Workbench geometry round trip")
            regions.append(
                {
                    "id": region_id,
                    "key": f"{hold['id']}-piece-{piece_index}",
                    "type": hold["kind"],
                    "displayPath": parsed.data,
                    "metadata": {
                        "holdID": hold["id"],
                        "pieceIndex": piece_index,
                    },
                }
            )
            region_id += 1
    return {
        "schemaVersion": 1,
        "canvas": {"width": report.width, "height": report.height},
        "regions": regions,
    }


def _canvas_scales(width: int, height: int) -> tuple[int, ...]:
    shortest = min(width, height)
    scales = []
    for fraction in _SCALE_FRACTIONS:
        value = max(3, round(shortest * fraction))
        value += 1 - value % 2
        scales.append(value)
    return tuple(dict.fromkeys(scales))


def _silhouette_candidates(
    foreground: np.ndarray, *, minimum_area: int
) -> tuple[list[_RawCandidate], list[CandidateRejection]]:
    candidates: list[_RawCandidate] = []
    rejections: list[CandidateRejection] = []
    for component in _component_masks(foreground):
        bounds = _mask_bounds(component)
        assert bounds is not None
        area = int(np.count_nonzero(component))
        if area < minimum_area:
            rejections.append(
                CandidateRejection("foregroundSilhouette", None, bounds, "tinyNoise")
            )
            continue
        if _touches_image_border(component):
            rejections.append(
                CandidateRejection(
                    "foregroundSilhouette", None, bounds, "imageBorderClipped"
                )
            )
            continue
        if _has_hole(component):
            rejections.append(
                CandidateRejection("foregroundSilhouette", None, bounds, "nestedHole")
            )
            continue
        candidates.append(_RawCandidate("foregroundSilhouette", None, component, True))
    return candidates, rejections


def _residual_candidates(
    luminance: np.ndarray,
    foreground: np.ndarray,
    *,
    scales: Sequence[int],
    minimum_area: int,
    width: int,
    height: int,
) -> tuple[list[_RawCandidate], list[Mapping[str, object]], list[CandidateRejection]]:
    candidates: list[_RawCandidate] = []
    thresholds: list[Mapping[str, object]] = []
    rejections: list[CandidateRejection] = []
    gap = max(1, round(min(width, height) * _MORPHOLOGY_GAP_FRACTION))
    gap = gap + 1 - gap % 2
    gap_kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (gap, gap))
    interior = cv2.erode(foreground.astype(np.uint8), np.ones((3, 3), np.uint8)) > 0

    for scale in scales:
        kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (scale, scale))
        closed = cv2.morphologyEx(luminance, cv2.MORPH_CLOSE, kernel)
        opened = cv2.morphologyEx(luminance, cv2.MORPH_OPEN, kernel)
        for polarity, residual in (
            ("dark", cv2.subtract(closed, luminance)),
            ("light", cv2.subtract(luminance, opened)),
        ):
            selected = _statistical_threshold(residual[interior])
            if selected is None:
                continue
            levels = tuple(max(1, selected + offset) for offset in _THRESHOLD_OFFSETS)
            thresholds.append(
                {
                    "lower": levels[0],
                    "polarity": polarity,
                    "scale": scale,
                    "selected": levels[1],
                    "upper": levels[2],
                }
            )
            masks = []
            for level in levels:
                mask = ((residual >= level) & interior).astype(np.uint8)
                mask = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, gap_kernel) > 0
                masks.append(mask)
            lower, central, upper = masks
            for component in _component_masks(central):
                bounds = _mask_bounds(component)
                assert bounds is not None
                if int(np.count_nonzero(component)) < minimum_area:
                    continue
                if _touches_image_border(component):
                    rejections.append(
                        CandidateRejection(
                            "multiscaleResidual", polarity, bounds, "imageBorderClipped"
                        )
                    )
                    continue
                if _has_hole(component):
                    rejections.append(
                        CandidateRejection(
                            "multiscaleResidual", polarity, bounds, "nestedHole"
                        )
                    )
                    continue
                if not _stable_across_thresholds(
                    component, lower, upper, width=width, height=height
                ):
                    rejections.append(
                        CandidateRejection(
                            "multiscaleResidual", polarity, bounds, "thresholdUnstable"
                        )
                    )
                    continue
                candidates.append(
                    _RawCandidate("multiscaleResidual", polarity, component, True)
                )
    return candidates, thresholds, rejections


def _statistical_threshold(values: np.ndarray) -> int | None:
    positive = np.asarray(values, dtype=np.uint8)
    positive = positive[positive > 0]
    if positive.size < _MINIMUM_COMPONENT_AREA_PIXELS:
        return None
    otsu, _binary = cv2.threshold(
        positive.reshape((-1, 1)), 0, 255, cv2.THRESH_BINARY | cv2.THRESH_OTSU
    )
    quantile = float(np.quantile(positive, 0.90))
    return max(2, round(max(float(otsu), quantile)))


def _stable_across_thresholds(
    central: np.ndarray,
    lower: np.ndarray,
    upper: np.ndarray,
    *,
    width: int,
    height: int,
) -> bool:
    del width, height
    for alternate in (lower, upper):
        _count, labels = cv2.connectedComponents(
            alternate.astype(np.uint8), connectivity=8
        )
        overlapping_labels = np.unique(labels[central])
        overlapping_labels = overlapping_labels[overlapping_labels != 0]
        if len(overlapping_labels) != 1:
            return False
        match = labels == int(overlapping_labels[0])
        if _has_hole(match):
            return False
        intersection = int(np.count_nonzero(central & match))
        union = int(np.count_nonzero(central | match))
        if not union or intersection / union < 0.50:
            return False
    return True


def _deduplicate_raw(
    candidates: Sequence[_RawCandidate], *, width: int, height: int
) -> list[_RawCandidate]:
    ordered = sorted(
        candidates,
        key=lambda candidate: (
            _mask_bounds(candidate.mask) or (0, 0, 0, 0),
            candidate.source,
            candidate.polarity or "",
            _mask_hash(candidate.mask),
        ),
    )
    kept: list[_RawCandidate] = []
    for candidate in ordered:
        duplicate = False
        for previous in kept:
            intersection = np.count_nonzero(candidate.mask & previous.mask)
            if not intersection:
                continue
            union = np.count_nonzero(candidate.mask | previous.mask)
            if union and intersection / union >= 0.75:
                duplicate = True
                break
            try:
                error = measure_native_contour_error(
                    _contour(candidate.mask),
                    _contour(previous.mask),
                    width=width,
                    height=height,
                )
            except ValueError:
                continue
            if error.passes:
                duplicate = True
                break
        if not duplicate:
            kept.append(candidate)
    return kept


def _materialize_candidate(
    raw: _RawCandidate, *, width: int, height: int
) -> GeometryCandidate:
    baseline = _contour(raw.mask)
    simplified = list(simplify_native_contour(baseline, width=width, height=height))
    simplified = _canonicalize_points(simplified)
    path = parse_closed_path(_path_data(simplified), width, height, label="candidate")
    frame, path_shape = shape_for_path(path, width, height)
    round_trip = display_path_for_shape(
        frame.to_json(), path_shape, width, height, label="candidate"
    )
    if round_trip.data != path.data:
        raise ValueError("candidate failed Workbench geometry round trip")

    representation = "path"
    selected_frame: Mapping[str, float] = frame.to_json()
    selected_shape: Mapping[str, object] = path_shape
    selected_path = path
    selected_error = measure_native_contour_error(
        baseline, simplified, width=width, height=height
    )
    rounded = _fit_rounded_rectangle(baseline, width=width, height=height)
    if rounded is not None:
        selected_frame, selected_shape, selected_path, selected_error = rounded
        representation = "roundedRect"

    mask_hash = _mask_hash(raw.mask)
    path_hash = hashlib.sha256(selected_path.data.encode("utf-8")).hexdigest()
    identity = hashlib.sha256(
        f"{raw.source}\0{raw.polarity or ''}\0{mask_hash}\0{path_hash}".encode()
    ).hexdigest()[:20]
    bounds = _mask_bounds(raw.mask)
    assert bounds is not None
    return GeometryCandidate(
        candidate_id=f"candidate-{identity}",
        source=raw.source,
        polarity=raw.polarity,
        bounds=bounds,
        display_path=selected_path.data,
        representation=representation,
        point_count=len(simplified),
        maximum_boundary_deviation_pixels=selected_error.maximum_boundary_deviation_pixels,
        symmetric_difference_ratio=selected_error.symmetric_difference_ratio,
        topology_stable=raw.topology_stable,
        mask_hash=mask_hash,
        path_hash=path_hash,
        _frame=selected_frame,
        _shape=selected_shape,
        _contour=tuple(baseline),
    )


def _fit_rounded_rectangle(
    baseline: Sequence[Point], *, width: int, height: int
) -> (
    tuple[Mapping[str, float], Mapping[str, object], object, NativeContourError] | None
):
    minimum_x = min(point[0] for point in baseline)
    maximum_x = max(point[0] for point in baseline)
    minimum_y = min(point[1] for point in baseline)
    maximum_y = max(point[1] for point in baseline)
    frame = {
        "x": minimum_x / width,
        "y": minimum_y / height,
        "width": (maximum_x - minimum_x) / width,
        "height": (maximum_y - minimum_y) / height,
    }
    best = None
    for step in range(_ROUNDED_RECT_RADIUS_STEPS + 1):
        radius = step / (2 * _ROUNDED_RECT_RADIUS_STEPS)
        shape = {"type": "roundedRect", "cornerRadiusFraction": radius}
        try:
            path = display_path_for_shape(
                frame, shape, width, height, label="candidate"
            )
            approximated = _approximate_contour(path.contour, epsilon=0.75)
            error = measure_native_contour_error(
                baseline, approximated, width=width, height=height
            )
        except (GeometryError, ValueError):
            continue
        if not error.passes:
            continue
        score = (
            error.symmetric_difference_ratio,
            error.maximum_boundary_deviation_pixels,
            radius,
        )
        if best is None or score < best[0]:
            best = (score, frame, shape, path, error)
    if best is None:
        return None
    return best[1], best[2], best[3], best[4]


def _symmetry_pairs(
    candidates: Sequence[GeometryCandidate],
    axis: float | None,
    *,
    width: int,
    height: int,
) -> list[tuple[str, str]]:
    if axis is None:
        return []
    unused = set(range(len(candidates)))
    pairs: list[tuple[str, str]] = []
    for first_index, first in enumerate(candidates):
        if first_index not in unused:
            continue
        reflected = _canonicalize_points([(2 * axis - x, y) for x, y in first._contour])
        best: tuple[tuple[float, float, str], int] | None = None
        for second_index in sorted(unused):
            if second_index == first_index:
                continue
            second = candidates[second_index]
            if first.source != second.source or first.polarity != second.polarity:
                continue
            try:
                error = measure_native_contour_error(
                    reflected, second._contour, width=width, height=height
                )
            except ValueError:
                continue
            if not error.passes:
                continue
            score = (
                error.symmetric_difference_ratio,
                error.maximum_boundary_deviation_pixels,
                second.candidate_id,
            )
            if best is None or score < best[0]:
                best = (score, second_index)
        if best is None:
            continue
        second_index = best[1]
        first_id, second_id = first.candidate_id, candidates[second_index].candidate_id
        first_center = (first.bounds[0] + first.bounds[2]) / 2
        second = candidates[second_index]
        second_center = (second.bounds[0] + second.bounds[2]) / 2
        pair = (
            (first_id, second_id)
            if first_center <= second_center
            else (second_id, first_id)
        )
        pairs.append(pair)
        unused.remove(first_index)
        unused.remove(second_index)
    pairs.sort()
    return pairs


def _reflection_axis(foreground: np.ndarray) -> float | None:
    bounds = _mask_bounds(foreground)
    if bounds is None:
        return None
    return (bounds[0] + bounds[2]) / 2


def _validate_symmetry_mapping(value: object, report: GeometryCandidateReport) -> None:
    if not isinstance(value, list):
        raise ValueError("accepted mapping symmetry must be an array")
    detected = {frozenset(pair) for pair in report.symmetry_pairs}
    seen: set[frozenset[str]] = set()
    for index, relationship in enumerate(value):
        if not isinstance(relationship, Mapping):
            raise ValueError(f"accepted mapping symmetry[{index}] must be an object")
        _exact_keys(
            relationship,
            {"candidateIDs"},
            f"accepted mapping symmetry[{index}]",
        )
        candidate_ids = relationship["candidateIDs"]
        if (
            not isinstance(candidate_ids, list)
            or len(candidate_ids) != 2
            or not all(isinstance(candidate_id, str) for candidate_id in candidate_ids)
            or candidate_ids[0] == candidate_ids[1]
        ):
            raise ValueError(
                "accepted symmetry must contain two distinct candidate IDs"
            )
        pair = frozenset(candidate_ids)
        if pair not in detected:
            raise ValueError(
                "accepted symmetry does not pass the derived native-pixel gates"
            )
        if pair in seen:
            raise ValueError("accepted symmetry relationship is duplicated")
        seen.add(pair)


def _component_masks(mask: np.ndarray) -> list[np.ndarray]:
    count, labels = cv2.connectedComponents(mask.astype(np.uint8), connectivity=8)
    return [labels == label for label in range(1, count)]


def _has_hole(mask: np.ndarray) -> bool:
    _contours, hierarchy = cv2.findContours(
        mask.astype(np.uint8), cv2.RETR_CCOMP, cv2.CHAIN_APPROX_SIMPLE
    )
    return hierarchy is not None and any(item[3] >= 0 for item in hierarchy[0])


def _touches_image_border(mask: np.ndarray) -> bool:
    return bool(
        np.any(mask[0]) or np.any(mask[-1]) or np.any(mask[:, 0]) or np.any(mask[:, -1])
    )


def _contour(mask: np.ndarray) -> list[Point]:
    contours, hierarchy = cv2.findContours(
        mask.astype(np.uint8), cv2.RETR_CCOMP, cv2.CHAIN_APPROX_SIMPLE
    )
    if hierarchy is None:
        raise ValueError("candidate has no contour")
    outer = [
        contour
        for contour, relation in zip(contours, hierarchy[0], strict=True)
        if relation[3] < 0
    ]
    if len(outer) != 1 or any(relation[3] >= 0 for relation in hierarchy[0]):
        raise ValueError("candidate must contain one contour without holes")
    # A subpixel approximation removes raster stair-step collinearity while
    # remaining inside the shared one-native-pixel boundary budget.
    return _approximate_contour(outer[0].reshape((-1, 2)), epsilon=0.75)


def _approximate_contour(
    points: Sequence[Sequence[float]], *, epsilon: float
) -> list[Point]:
    values = np.asarray(points, dtype=np.float32).reshape((-1, 1, 2))
    approximated = cv2.approxPolyDP(values, epsilon, True).reshape((-1, 2))
    return _canonicalize_points(
        [(float(point[0]), float(point[1])) for point in approximated]
    )


def _canonicalize_points(points: Sequence[Point]) -> list[Point]:
    cleaned: list[Point] = []
    for point in points:
        value = (float(point[0]), float(point[1]))
        if not cleaned or value != cleaned[-1]:
            cleaned.append(value)
    if len(cleaned) > 1 and cleaned[0] == cleaned[-1]:
        cleaned.pop()
    if len(cleaned) < 3:
        raise ValueError("candidate contour has fewer than three points")
    area = sum(
        start[0] * end[1] - end[0] * start[1]
        for start, end in zip(cleaned, cleaned[1:] + cleaned[:1])
    )
    if abs(area) <= 1e-9:
        raise ValueError("candidate contour has zero area")
    if area < 0:
        cleaned.reverse()
    start_index = min(
        range(len(cleaned)), key=lambda index: (cleaned[index][1], cleaned[index][0])
    )
    return cleaned[start_index:] + cleaned[:start_index]


def _path_data(points: Sequence[Point]) -> str:
    return " ".join(
        [f"M {_number(points[0][0])} {_number(points[0][1])}"]
        + [f"L {_number(x)} {_number(y)}" for x, y in points[1:]]
        + ["Z"]
    )


def _number(value: float) -> str:
    if value == round(value):
        return str(round(value))
    return f"{value:.12f}".rstrip("0").rstrip(".")


def _mask_bounds(mask: np.ndarray) -> Bounds | None:
    rows, columns = np.nonzero(mask)
    if not len(rows):
        return None
    return (
        int(columns.min()),
        int(rows.min()),
        int(columns.max()),
        int(rows.max()),
    )


def _mask_hash(mask: np.ndarray) -> str:
    dimensions = np.asarray(mask.shape, dtype=">u4").tobytes()
    return hashlib.sha256(
        dimensions + np.packbits(mask, bitorder="big").tobytes()
    ).hexdigest()


def _exact_keys(value: Mapping[str, object], expected: set[str], label: str) -> None:
    unknown = set(value) - expected
    missing = expected - set(value)
    if unknown:
        raise ValueError(f"{label} has unknown keys: {sorted(unknown)}")
    if missing:
        raise ValueError(f"{label} is missing keys: {sorted(missing)}")


def _canonical_json(value: object) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":")).encode("utf-8")
