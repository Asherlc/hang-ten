"""Oracle-isolated evaluation for finalized Stage 3 vector candidates."""

from __future__ import annotations

from dataclasses import asdict
from hashlib import sha256
import json
from pathlib import Path
from typing import Mapping
import xml.etree.ElementTree as ET

import cv2
import numpy as np
from PIL import Image, ImageDraw, ImageFont

from .display_paths import DisplayPath, parse_display_path
from .stage2_evaluation import _oracle_masks, _oracle_overlay, _region_metrics, _summary
from .vector_smoothing import (
    OpenPath,
    Stage2MaskRegion,
    VectorizationProfile,
    _piece_masks,
    _mask_boundary_edges,
    _mask_edge_polygon,
    _ordered_seam,
    _orient_seam_for_mask,
    _persistent_corners,
    _remove_collinear,
    display_path_contains_open_path,
    parse_open_path_data,
    rasterize_display_path,
    rasterize_paths_half_open,
    rasterize_paths_independent,
    validate_display_path,
)


_CANDIDATE_NAMES = frozenset(
    {"stage-3-vector-regions.json", "stage-3-vector.svg", "stage-3-vector-overlay.png"}
)
_RAW_THRESHOLDS = {
    "microIou": (">=", 0.95),
    "medianRegionIou": (">=", 0.95),
    "minimumRegionIou": (">=", 0.90),
    "medianCentroidDisplacementPx": ("<=", 0.75),
    "maximumCentroidDisplacementPx": ("<=", 1.5),
    "maximumHd95Px": ("<=", 3.0),
    "newOverlapPixels": ("<=", 0.0),
    "outsideSilhouettePixels": ("<=", 0.0),
}


def evaluate_stage3_candidate(
    candidate_root: Path,
    *,
    source_rgba: np.ndarray,
    raw_regions: tuple[Stage2MaskRegion, ...],
    stage2_acceptance: Mapping[str, object],
    stage2_acceptance_raw_sha256: str,
    oracle_paths: Mapping[str, str] | None = None,
) -> dict[str, object]:
    """Verify frozen vector bytes before the first V14/oracle access."""
    hashes = _verify_candidate_hashes(candidate_root)
    document = _load_candidate_document(candidate_root / "stage-3-vector-regions.json")
    height, width = source_rgba.shape[:2]
    if document["stage2AcceptanceRawSha256"] != stage2_acceptance_raw_sha256:
        raise ValueError(
            "serialized Stage 3 provenance does not match Stage 2 acceptance"
        )
    profile = _candidate_profile(document["profile"])
    piece_values = document.get("pieces")
    if not isinstance(piece_values, list):
        raise ValueError("serialized Stage 3 pieces are invalid")
    piece_masks = _piece_masks(source_rgba[..., 3], len(piece_values))
    piece_paths = _candidate_piece_paths(document, source_rgba, piece_masks, profile)
    expected_seams = _expected_canonical_seams(raw_regions, piece_masks)
    seams = _candidate_seams(document, width, height, expected_seams)
    paths = _candidate_paths(document, width, height, raw_regions, profile, seams)
    _validate_seam_membership(document, paths, piece_paths, seams)
    _validate_svg(candidate_root / "stage-3-vector.svg", paths, piece_paths)
    ordered_masks = rasterize_paths_half_open(tuple(paths.values()), width, height)
    candidate_masks = dict(zip(paths, ordered_masks, strict=True))
    for item in document["regions"]:
        actual = sha256(candidate_masks[item["id"]].tobytes()).hexdigest()
        if actual != item["outputMaskSha256"]:
            raise ValueError("serialized Stage 3 output mask hash mismatch")
    raw_metrics, raw_region_metrics = _raw_preservation(
        source_rgba,
        raw_regions,
        paths,
        {
            frozenset((value["firstId"], value["secondId"])): seams[value["id"]]
            for value in document["canonicalSeams"]
            if value["kind"] == "region"
        },
        piece_masks=piece_masks,
    )
    raw_accepted = _passes(raw_metrics, _RAW_THRESHOLDS)

    # This is intentionally the first V14 access. Candidate paths and their
    # exact byte hashes are already fixed above.
    if oracle_paths is None:
        from .beastmaker_v14_paths import ACCEPTED_V14_PATHS

        oracle_paths = ACCEPTED_V14_PATHS
    oracle = _oracle_masks(oracle_paths, width, height)
    pairing = _validated_pairing(
        stage2_acceptance, candidate_masks, raw_regions, oracle
    )
    typed_candidates = {
        region.id: (region.grip_type, candidate_masks[region.id])
        for region in raw_regions
    }
    oracle_regions = [
        _region_metrics(
            candidate_id,
            oracle_id,
            typed_candidates[candidate_id][1],
            oracle[oracle_id][1],
        )
        for candidate_id, oracle_id in pairing
    ]
    oracle_metrics = _summary(oracle_regions)
    regression = _oracle_regression(stage2_acceptance, oracle_metrics, oracle_regions)
    oracle_accepted = (
        regression["microIouLoss"] <= 0.01
        and regression["medianRegionIouLoss"] <= 0.01
        and regression["maximumRegionIouLoss"] <= 0.03
    )
    accepted = raw_accepted and oracle_accepted and len(paths) == len(raw_regions)

    overlay = _oracle_overlay(source_rgba, pairing, typed_candidates, oracle)
    candidate_image = np.asarray(
        Image.open(candidate_root / "stage-3-vector-overlay.png").convert("RGB")
    )
    review = _review_image(candidate_image, overlay)
    Image.fromarray(review).save(
        candidate_root / "stage-3-review.png",
        format="PNG",
        optimize=False,
        compress_level=9,
    )
    acceptance = {
        "accepted": accepted,
        "artifacts": {
            "candidateHashes": "stage-3-candidate-hashes.json",
            "review": "stage-3-review.png",
            "vectorOverlay": "stage-3-vector-overlay.png",
            "vectorRegions": "stage-3-vector-regions.json",
            "vectorSvg": "stage-3-vector.svg",
        },
        "candidateHashes": hashes,
        "oracleMetrics": oracle_metrics,
        "oracleRegression": regression,
        "oracleRegions": oracle_regions,
        "pairing": [
            {"candidateId": first, "oracleId": second} for first, second in pairing
        ],
        "rawMetrics": raw_metrics,
        "rawRegions": raw_region_metrics,
        "rawThresholds": {
            name: {"operator": operator, "value": value}
            for name, (operator, value) in _RAW_THRESHOLDS.items()
        },
        "schemaVersion": 1,
        "stage": 3,
    }
    _write_json(candidate_root / "stage-3-acceptance.json", acceptance)
    if not accepted:
        raise ValueError(
            f"Stage 3 candidate does not meet acceptance thresholds: raw={raw_metrics}, oracle={regression}"
        )
    return acceptance


def _verify_candidate_hashes(root: Path) -> dict[str, str]:
    path = root / "stage-3-candidate-hashes.json"
    if not path.is_file():
        raise FileNotFoundError("serialized Stage 3 candidate hash manifest is missing")
    try:
        document = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        raise ValueError("invalid Stage 3 candidate hash manifest") from error
    if (
        not isinstance(document, dict)
        or set(document) != {"files", "schemaVersion"}
        or document.get("schemaVersion") != 1
    ):
        raise ValueError("invalid Stage 3 candidate hash manifest")
    files = document.get("files")
    if not isinstance(files, dict) or set(files) != _CANDIDATE_NAMES:
        raise ValueError("invalid Stage 3 candidate hash manifest")
    for name, expected in files.items():
        candidate = root / name
        if (
            not isinstance(expected, str)
            or len(expected) != 64
            or not candidate.is_file()
        ):
            raise ValueError("invalid Stage 3 candidate hash manifest")
        if sha256(candidate.read_bytes()).hexdigest() != expected:
            raise ValueError(f"serialized Stage 3 candidate was changed: {name}")
    return {name: files[name] for name in sorted(files)}


def _load_candidate_document(path: Path) -> dict[str, object]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        raise ValueError("invalid serialized Stage 3 regions") from error
    expected = {
        "canonicalSeams",
        "height",
        "pieces",
        "profile",
        "regions",
        "schemaVersion",
        "stage",
        "stage2AcceptanceRawSha256",
        "width",
    }
    if (
        not isinstance(value, dict)
        or set(value) != expected
        or value.get("schemaVersion") != 1
        or value.get("stage") != 3
        or not isinstance(value.get("regions"), list)
        or not isinstance(value.get("pieces"), list)
    ):
        raise ValueError("invalid serialized Stage 3 regions")
    return value


def _candidate_profile(value: object) -> VectorizationProfile:
    if not isinstance(value, dict) or set(value) != set(asdict(VectorizationProfile())):
        raise ValueError("serialized Stage 3 profile is invalid")
    try:
        profile = VectorizationProfile(**value)
    except (TypeError, ValueError) as error:
        raise ValueError("serialized Stage 3 profile is invalid") from error
    if asdict(profile) != value:
        raise ValueError("serialized Stage 3 profile is not canonical")
    return profile


def _candidate_piece_paths(
    document: Mapping[str, object],
    source_rgba: np.ndarray,
    piece_masks: tuple[np.ndarray, ...],
    profile: VectorizationProfile,
) -> dict[str, DisplayPath]:
    height, width = source_rgba.shape[:2]
    values = document["pieces"]
    assert isinstance(values, list)
    expected_fields = {
        "displayPath",
        "id",
        "outputMaskSha256",
        "pieceIndex",
        "rawMaskSha256",
        "sharedSeamIds",
    }
    result: dict[str, DisplayPath] = {}
    for index, (value, raw) in enumerate(zip(values, piece_masks, strict=True)):
        identifier = f"piece-{index + 1:02d}-silhouette"
        if (
            not isinstance(value, dict)
            or set(value) != expected_fields
            or value.get("id") != identifier
            or value.get("pieceIndex") != index
            or value.get("rawMaskSha256") != sha256(raw.tobytes()).hexdigest()
            or not _string_list(value.get("sharedSeamIds"))
        ):
            raise ValueError("serialized Stage 3 piece provenance is invalid")
        path = parse_display_path(
            value.get("displayPath"),
            identifier,
            width,
            height,
            allow_linear_segments=True,
        )
        if path is None:
            raise ValueError("serialized Stage 3 piece path is missing")
        validate_display_path(
            path, scale_basis=float(min(_bbox_size(raw))), profile=profile
        )
        output = rasterize_display_path(path, width, height)
        if (
            value.get("outputMaskSha256") != sha256(output.tobytes()).hexdigest()
            or _iou(raw, output) < 0.98
        ):
            raise ValueError(
                "serialized Stage 3 piece path does not match alpha silhouette"
            )
        result[identifier] = path
    return result


def _candidate_seams(
    document: Mapping[str, object],
    width: int,
    height: int,
    expected: tuple[tuple[str, str, str, tuple[tuple[float, float], ...]], ...],
) -> dict[str, OpenPath]:
    values = document["canonicalSeams"]
    if not isinstance(values, list) or len(values) != len(expected):
        raise ValueError("canonical seam evidence does not match raw geometry")
    if not values and expected:
        raise ValueError("serialized Stage 3 canonical seams are invalid")
    expected_fields = {
        "firstId",
        "id",
        "kind",
        "path",
        "rawCoordinates",
        "reversePath",
        "secondId",
    }
    result: dict[str, OpenPath] = {}
    for index, (value, required) in enumerate(
        zip(values, expected, strict=True), start=1
    ):
        required_kind, required_first, required_second, required_raw = required
        if (
            not isinstance(value, dict)
            or set(value) != expected_fields
            or value.get("id") != f"seam-{index:03d}"
            or value.get("kind") != required_kind
            or value.get("firstId") != required_first
            or value.get("secondId") != required_second
        ):
            raise ValueError("canonical seam evidence does not match raw geometry")
        path = parse_open_path_data(value.get("path"), width, height)
        if value.get("reversePath") != path.reversed().data:
            raise ValueError(
                "serialized Stage 3 canonical seam reverse path is invalid"
            )
        raw = value.get("rawCoordinates")
        if (
            not isinstance(raw, list)
            or len(raw) < 2
            or any(not isinstance(point, list) or len(point) != 2 for point in raw)
            or tuple(float(item) for item in raw[0]) != path.start
            or tuple(float(item) for item in raw[-1]) != path.end
        ):
            raise ValueError(
                "serialized Stage 3 canonical seam coordinates are invalid"
            )
        raw_points = tuple((float(point[0]), float(point[1])) for point in raw)
        if raw_points != required_raw:
            raise ValueError("canonical seam evidence does not match raw geometry")
        raw_edges = {
            tuple(sorted((first, second)))
            for first, second in zip(raw_points, raw_points[1:])
        }
        if _ordered_seam(raw_edges) not in {raw_points, tuple(reversed(raw_points))}:
            raise ValueError("serialized Stage 3 canonical seam graph is invalid")
        result[value["id"]] = path
    return result


def _expected_canonical_seams(
    regions: tuple[Stage2MaskRegion, ...], piece_masks: tuple[np.ndarray, ...]
) -> tuple[tuple[str, str, str, tuple[tuple[float, float], ...]], ...]:
    expected: list[tuple[str, str, str, tuple[tuple[float, float], ...]]] = []
    surfaces = [region for region in regions if region.visual_mode == "surface"]
    for index, first in enumerate(surfaces):
        for second in surfaces[index + 1 :]:
            if first.piece_index != second.piece_index:
                continue
            shared = _mask_boundary_edges(first.mask) & _mask_boundary_edges(
                second.mask
            )
            if not shared:
                continue
            raw = _orient_seam_for_mask(_ordered_seam(shared), first.mask)
            expected.append(("region", first.id, second.id, raw))
    for region in surfaces:
        shared = _mask_boundary_edges(region.mask) & _mask_boundary_edges(
            piece_masks[region.piece_index]
        )
        if not shared:
            continue
        raw = _orient_seam_for_mask(_ordered_seam(shared), region.mask)
        expected.append(
            (
                "piece",
                region.id,
                f"piece-{region.piece_index + 1:02d}-silhouette",
                raw,
            )
        )
    return tuple(expected)


def _candidate_paths(
    document: Mapping[str, object],
    width: int,
    height: int,
    raw_regions: tuple[Stage2MaskRegion, ...],
    profile: VectorizationProfile,
    seams: Mapping[str, OpenPath],
) -> dict[str, DisplayPath]:
    if document.get("width") != width or document.get("height") != height:
        raise ValueError("serialized Stage 3 dimensions mismatch")
    values = document["regions"]
    assert isinstance(values, list)
    if len(values) != len(raw_regions):
        raise ValueError("serialized Stage 3 topology mismatch")
    expected_fields = {
        "displayPath",
        "id",
        "lockedCorners",
        "outputMaskSha256",
        "pieceIndex",
        "primitive",
        "rawMaskSha256",
        "sharedSeamIds",
        "type",
    }
    paths: dict[str, DisplayPath] = {}
    for value, raw in zip(values, raw_regions, strict=True):
        if (
            not isinstance(value, dict)
            or set(value) != expected_fields
            or (value.get("id"), value.get("pieceIndex"), value.get("type"))
            != (raw.id, raw.piece_index, raw.grip_type)
            or value.get("primitive") not in {"rounded-mouth", "feature-spline"}
            or value.get("rawMaskSha256") != raw.raw_mask_sha256
            or not isinstance(value.get("outputMaskSha256"), str)
            or not _points(value.get("lockedCorners"), width, height)
            or not _string_list(value.get("sharedSeamIds"))
            or any(identifier not in seams for identifier in value["sharedSeamIds"])
        ):
            raise ValueError("serialized Stage 3 region identity mismatch")
        parsed = parse_display_path(
            value.get("displayPath"), raw.id, width, height, allow_linear_segments=True
        )
        if parsed is None:
            raise ValueError("serialized Stage 3 display path is missing")
        expected_locked = (
            ()
            if value["primitive"] == "rounded-mouth"
            else _persistent_corners(
                _remove_collinear(_mask_edge_polygon(raw.mask)),
                float(min(_bbox_size(raw.mask))),
                profile,
            )
        )
        serialized_locked = tuple(
            (float(point[0]), float(point[1])) for point in value["lockedCorners"]
        )
        if serialized_locked != expected_locked:
            raise ValueError(
                "serialized Stage 3 locked corners do not match raw geometry"
            )
        validate_display_path(
            parsed, scale_basis=float(min(_bbox_size(raw.mask))), profile=profile
        )
        paths[raw.id] = parsed
    if len(paths) != len(values):
        raise ValueError("duplicate serialized Stage 3 region ID")
    return paths


def _validate_seam_membership(
    document: Mapping[str, object],
    regions: Mapping[str, DisplayPath],
    pieces: Mapping[str, DisplayPath],
    seams: Mapping[str, OpenPath],
) -> None:
    entities = {**pieces, **regions}
    expected: dict[str, set[str]] = {identifier: set() for identifier in entities}
    values = document["canonicalSeams"]
    assert isinstance(values, list)
    for value in values:
        assert isinstance(value, dict)
        seam = seams[value["id"]]
        first, second = value["firstId"], value["secondId"]
        if first not in entities or second not in entities:
            raise ValueError("canonical seam references an unavailable entity")
        if not display_path_contains_open_path(entities[first], seam):
            raise ValueError("canonical seam is not embedded in its first path")
        second_seam = seam.reversed() if value["kind"] == "region" else seam
        if not display_path_contains_open_path(entities[second], second_seam):
            raise ValueError("canonical seam orientation is invalid in its second path")
        expected[first].add(value["id"])
        expected[second].add(value["id"])
    for collection in (document["pieces"], document["regions"]):
        assert isinstance(collection, list)
        for value in collection:
            assert isinstance(value, dict)
            if set(value["sharedSeamIds"]) != expected[value["id"]]:
                raise ValueError(
                    "serialized shared seam IDs do not match path geometry"
                )


def _validate_svg(
    path: Path,
    regions: Mapping[str, DisplayPath],
    pieces: Mapping[str, DisplayPath],
) -> None:
    try:
        root = ET.fromstring(path.read_bytes())
    except (OSError, ET.ParseError) as error:
        raise ValueError("serialized Stage 3 SVG is invalid") from error
    namespace = "{http://www.w3.org/2000/svg}"
    elements = {value.get("id"): value for value in root.findall(f"{namespace}path")}
    expected = {**pieces, **regions}
    if set(elements) != set(expected) or any(
        elements[key].get("d") != value.data for key, value in expected.items()
    ):
        raise ValueError("serialized Stage 3 SVG paths do not match candidate JSON")
    if len(root.findall(f"{namespace}image")) != 1:
        raise ValueError("serialized Stage 3 SVG source raster is invalid")


def _points(value: object, width: int, height: int) -> bool:
    return isinstance(value, list) and all(
        isinstance(point, list)
        and len(point) == 2
        and all(type(item) in {int, float} and np.isfinite(item) for item in point)
        and 0 <= point[0] <= width
        and 0 <= point[1] <= height
        for point in value
    )


def _string_list(value: object) -> bool:
    return (
        isinstance(value, list)
        and all(isinstance(item, str) for item in value)
        and len(value) == len(set(value))
    )


def _bbox_size(mask: np.ndarray) -> tuple[int, int]:
    ys, xs = np.nonzero(mask)
    return int(xs.max() - xs.min() + 1), int(ys.max() - ys.min() + 1)


def _iou(first: np.ndarray, second: np.ndarray) -> float:
    intersection = int(np.count_nonzero(first.astype(bool) & second.astype(bool)))
    union = int(np.count_nonzero(first.astype(bool) | second.astype(bool)))
    return intersection / union if union else 1.0


def _raw_preservation(
    rgba: np.ndarray,
    raw_regions: tuple[Stage2MaskRegion, ...],
    paths: Mapping[str, DisplayPath],
    shared_region_seams: Mapping[frozenset[str], OpenPath],
    *,
    piece_masks: tuple[np.ndarray, ...] | None = None,
) -> tuple[dict[str, float], list[dict[str, object]]]:
    height, width = rgba.shape[:2]
    scale = 4
    if piece_masks is None:
        piece_masks = _piece_masks(
            rgba[..., 3], max(region.piece_index for region in raw_regions) + 1
        )
    ordered_candidates = rasterize_paths_half_open(
        tuple(paths[region.id] for region in raw_regions), width, height, scale=scale
    )
    independent_candidates = rasterize_paths_independent(
        tuple(paths[region.id] for region in raw_regions), width, height, scale=scale
    )
    independent_boundaries = tuple(_boundary(mask) for mask in independent_candidates)
    shared_seam_masks = {
        owners: _rasterize_open_path_boundary(path, width, height, scale=scale)
        for owners, path in shared_region_seams.items()
    }
    region_metrics: list[dict[str, object]] = []
    total_intersection = 0
    total_union = 0
    outside = 0
    overlap = 0
    for position, (region, candidate, independent) in enumerate(
        zip(raw_regions, ordered_candidates, independent_candidates, strict=True)
    ):
        raw = cv2.resize(
            region.mask,
            (width * scale, height * scale),
            interpolation=cv2.INTER_NEAREST,
        )
        piece = cv2.resize(
            piece_masks[region.piece_index],
            (width * scale, height * scale),
            interpolation=cv2.INTER_NEAREST,
        )
        intersection = int(np.count_nonzero(candidate.astype(bool) & raw.astype(bool)))
        union = int(np.count_nonzero(candidate.astype(bool) | raw.astype(bool)))
        iou = intersection / union if union else 1.0
        centroid = _centroid_shift(raw, candidate) / scale
        hd95 = _hd95(raw, candidate) / scale
        independent_selected = independent.astype(bool)
        true_overlap = np.zeros_like(independent_selected)
        for previous_position, previous_region in enumerate(raw_regions[:position]):
            pair_overlap = (
                independent_candidates[previous_position].astype(bool)
                & independent_selected
            )
            seam_mask = shared_seam_masks.get(
                frozenset((previous_region.id, region.id))
            )
            if seam_mask is not None:
                seam_ownership = (
                    pair_overlap
                    & independent_boundaries[previous_position]
                    & independent_boundaries[position]
                    & seam_mask.astype(bool)
                )
                pair_overlap &= ~seam_ownership
            true_overlap |= pair_overlap
        new_overlap = int(np.count_nonzero(true_overlap))
        outside_pixels = int(
            np.count_nonzero(independent_selected & ~piece.astype(bool))
        )
        overlap += new_overlap
        outside += outside_pixels
        total_intersection += intersection
        total_union += union
        region_metrics.append(
            {
                "centroidDisplacementPx": centroid,
                "hd95Px": hd95,
                "id": region.id,
                "intersectionPixels4x": intersection,
                "iou": iou,
                "outsideSilhouettePixels4x": outside_pixels,
                "overlapPixels4x": new_overlap,
                "unionPixels4x": union,
            }
        )
    ious = np.asarray([value["iou"] for value in region_metrics], dtype=float)
    centroids = np.asarray(
        [value["centroidDisplacementPx"] for value in region_metrics], dtype=float
    )
    hd95s = np.asarray([value["hd95Px"] for value in region_metrics], dtype=float)
    metrics = {
        "maximumCentroidDisplacementPx": float(centroids.max()),
        "maximumHd95Px": float(hd95s.max()),
        "medianCentroidDisplacementPx": float(np.median(centroids)),
        "medianRegionIou": float(np.median(ious)),
        "microIou": total_intersection / total_union if total_union else 1.0,
        "minimumRegionIou": float(ious.min()),
        "newOverlapPixels": float(overlap),
        "outsideSilhouettePixels": float(outside),
    }
    return metrics, region_metrics


def _rasterize_open_path_boundary(
    path: OpenPath, width: int, height: int, *, scale: int
) -> np.ndarray:
    sampling = 2
    render_scale = scale * sampling
    points = [np.asarray(path.start, dtype=np.float64)]
    start = points[0]
    for segment in path.segments:
        end = np.asarray(segment.end, dtype=np.float64)
        if segment.command == "L":
            points.append(end)
        else:
            if segment.control_1 is None or segment.control_2 is None:
                raise ValueError("cubic open-path segment requires two controls")
            control_1 = np.asarray(segment.control_1, dtype=np.float64)
            control_2 = np.asarray(segment.control_2, dtype=np.float64)
            for step in range(1, 65):
                t = step / 64
                points.append(
                    (1 - t) ** 3 * start
                    + 3 * (1 - t) ** 2 * t * control_1
                    + 3 * (1 - t) * t**2 * control_2
                    + t**3 * end
                )
        start = end
    high = np.zeros((height * render_scale, width * render_scale), dtype=np.uint8)
    cv2.polylines(
        high,
        [np.rint(np.asarray(points) * render_scale).astype(np.int32)],
        False,
        1,
        thickness=1,
        lineType=cv2.LINE_8,
    )
    offset = sampling // 2
    return high[offset::sampling, offset::sampling].copy()


def _validated_pairing(
    stage2_acceptance: Mapping[str, object],
    candidates: Mapping[str, np.ndarray],
    raw_regions: tuple[Stage2MaskRegion, ...],
    oracle: Mapping[str, tuple[str, np.ndarray]],
) -> tuple[tuple[str, str], ...]:
    values = stage2_acceptance.get("pairing")
    if not isinstance(values, list) or len(values) != len(raw_regions):
        raise ValueError("Stage 2 oracle pairing is invalid")
    pairs: list[tuple[str, str]] = []
    for value in values:
        if not isinstance(value, dict) or set(value) != {"candidateId", "oracleId"}:
            raise ValueError("Stage 2 oracle pairing is invalid")
        candidate_id, oracle_id = value["candidateId"], value["oracleId"]
        if candidate_id not in candidates or oracle_id not in oracle:
            raise ValueError("Stage 2 oracle pairing references missing geometry")
        pairs.append((candidate_id, oracle_id))
    if {first for first, _ in pairs} != {region.id for region in raw_regions}:
        raise ValueError("Stage 2 oracle pairing changed candidate topology")
    return tuple(pairs)


def _oracle_regression(
    stage2_acceptance: Mapping[str, object],
    vector_summary: Mapping[str, float],
    vector_regions: list[dict[str, object]],
) -> dict[str, float]:
    baseline_summary = stage2_acceptance.get("metrics")
    baseline_regions = stage2_acceptance.get("regions")
    if not isinstance(baseline_summary, dict) or not isinstance(baseline_regions, list):
        raise ValueError("Stage 2 baseline metrics are invalid")
    baseline_by_id = {
        value["candidateId"]: float(value["iou"])
        for value in baseline_regions
        if isinstance(value, dict) and "candidateId" in value and "iou" in value
    }
    missing = [
        value["candidateId"]
        for value in vector_regions
        if value["candidateId"] not in baseline_by_id
    ]
    if missing:
        raise ValueError("Stage 2 per-region baseline metrics are incomplete")
    losses = [
        baseline_by_id[value["candidateId"]] - float(value["iou"])
        for value in vector_regions
    ]
    return {
        "maximumRegionIouLoss": max(losses),
        "medianRegionIouLoss": float(baseline_summary["medianRegionIou"])
        - float(vector_summary["medianRegionIou"]),
        "microIouLoss": float(baseline_summary["microIou"])
        - float(vector_summary["microIou"]),
    }


def _passes(
    metrics: Mapping[str, float], thresholds: Mapping[str, tuple[str, float]]
) -> bool:
    return all(
        metrics[name] >= value if operator == ">=" else metrics[name] <= value
        for name, (operator, value) in thresholds.items()
    )


def _centroid_shift(first: np.ndarray, second: np.ndarray) -> float:
    def center(mask: np.ndarray) -> tuple[float, float]:
        moments = cv2.moments(mask.astype(np.uint8), binaryImage=True)
        return moments["m10"] / moments["m00"], moments["m01"] / moments["m00"]

    first_center, second_center = center(first), center(second)
    return float(
        np.hypot(first_center[0] - second_center[0], first_center[1] - second_center[1])
    )


def _hd95(first: np.ndarray, second: np.ndarray) -> float:
    first_boundary = _boundary(first)
    second_boundary = _boundary(second)
    distance_second = cv2.distanceTransform(
        (~second_boundary).astype(np.uint8), cv2.DIST_L2, 5
    )
    distance_first = cv2.distanceTransform(
        (~first_boundary).astype(np.uint8), cv2.DIST_L2, 5
    )
    distances = np.concatenate(
        (distance_second[first_boundary], distance_first[second_boundary])
    )
    return float(np.percentile(distances, 95)) if distances.size else 0.0


def _boundary(mask: np.ndarray) -> np.ndarray:
    selected = mask.astype(bool)
    eroded = cv2.erode(
        selected.astype(np.uint8),
        np.ones((3, 3), np.uint8),
        borderType=cv2.BORDER_CONSTANT,
        borderValue=0,
    )
    return selected & ~(eroded > 0)


def _review_image(candidate: np.ndarray, overlay: np.ndarray) -> np.ndarray:
    gap, top, bottom = 24, 38, 18
    height, width = candidate.shape[:2]
    canvas = Image.new(
        "RGB", (width * 2 + gap * 3, height + top + bottom), (248, 247, 244)
    )
    canvas.paste(Image.fromarray(candidate), (gap, top))
    canvas.paste(Image.fromarray(overlay), (width + gap * 2, top))
    draw = ImageDraw.Draw(canvas)
    font = ImageFont.load_default()
    draw.text(
        (gap, 14),
        "AUTOMATIC MIXED-CORNER VECTORS - 22 REGIONS",
        fill=(25, 25, 25),
        font=font,
    )
    draw.text(
        (width + gap * 2, 8),
        "V14 COMPARISON - green overlap / magenta over / yellow missed",
        fill=(25, 25, 25),
        font=font,
    )
    draw.text(
        (width + gap * 2, 22),
        "cyan automatic boundary / white oracle boundary",
        fill=(25, 25, 25),
        font=font,
    )
    return np.asarray(canvas)


def _write_json(path: Path, document: Mapping[str, object]) -> None:
    path.write_text(
        json.dumps(document, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
