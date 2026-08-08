"""Generic Stage 3 vector geometry from an approved semantic raster."""

from __future__ import annotations

import base64
from collections.abc import Mapping
from dataclasses import asdict, dataclass
from hashlib import sha256
from io import BytesIO
import json
from pathlib import Path
import shutil
import tempfile
from types import MappingProxyType
from typing import Protocol

import cv2
import numpy as np
from PIL import Image, ImageDraw, ImageFont

from .display_paths import DisplayPath, flatten_display_path, parse_display_path
from .generic_stage0 import StageCheckpoint
from .models import ConversionError


_TYPE_COLORS: Mapping[str, tuple[int, int, int]] = MappingProxyType(
    {
        "jug": (238, 105, 54),
        "sloper": (25, 159, 174),
        "edge": (117, 79, 194),
        "pocket": (218, 60, 132),
    }
)
_CANDIDATE_FILES = (
    "stage-3-candidate.json",
    "stage-3-vector-regions.json",
    "stage-3-vector.svg",
    "stage-3-review.png",
)


@dataclass(frozen=True, slots=True)
class GenericStage3Profile:
    profile_id: str = "generic-contour-vector-v1"
    canvas_width: int = 1000
    silhouette_epsilon_fraction: float = 0.0015
    feature_epsilon_fraction: float = 0.0035
    silhouette_corner_radius: float = 3.0
    pocket_corner_radius_fraction: float = 0.42


class Stage3RunContext(Protocol):
    root: Path
    manifest: Mapping[str, object]


@dataclass(frozen=True, slots=True)
class GenericStage3Runner:
    profile: GenericStage3Profile = GenericStage3Profile()
    stage: int = 3

    def run(self, context: Stage3RunContext, artifact_root: Path) -> StageCheckpoint:
        return run_generic_stage3(context, artifact_root, profile=self.profile)


def run_generic_stage3(
    context: Stage3RunContext,
    artifact_root: Path,
    *,
    profile: GenericStage3Profile = GenericStage3Profile(),
) -> StageCheckpoint:
    """Vectorize the approved Stage 2 labels without inferring product topology."""
    if artifact_root.exists():
        raise FileExistsError(f"Stage 3 artifact root already exists: {artifact_root}")
    rgba, labels, source_regions, evidence = _approved_inputs(context)
    if rgba.shape[1] != profile.canvas_width:
        raise ConversionError(
            "generic Stage 3 requires the canonical 1000-pixel canvas"
        )

    first = _vector_document(rgba, labels, source_regions, evidence, profile)
    second = _vector_document(rgba, labels, source_regions, evidence, profile)
    first_bytes = _json_bytes(first)
    if first_bytes != _json_bytes(second):
        raise ConversionError("generic Stage 3 vectorization is not deterministic")

    svg = _svg(first, rgba)
    if svg != _svg(second, rgba):
        raise ConversionError("generic Stage 3 SVG generation is not deterministic")
    candidate = {
        "inputAcceptance": evidence["stage2Acceptance"],
        "inputLabels": evidence["stage2Labels"],
        "inputRegions": evidence["stage2Regions"],
        "inputRgba": evidence["stage1Rgba"],
        "profile": asdict(profile),
        "stage": 3,
    }
    temporary_root: Path | None = None
    try:
        artifact_root.parent.mkdir(parents=True, exist_ok=True)
        temporary_root = Path(
            tempfile.mkdtemp(
                prefix=f".{artifact_root.name}.tmp-", dir=artifact_root.parent
            )
        )
        hashes = build_stage3_artifacts(
            temporary_root,
            rgba=rgba,
            labels=labels,
            vector_document=first,
            candidate=candidate,
            preserved_files={},
            candidate_files=_CANDIDATE_FILES,
        )
        temporary_root.replace(artifact_root)
        return StageCheckpoint(
            stage=3,
            artifact_root=artifact_root,
            candidate_hashes=MappingProxyType(hashes),
            review_path=artifact_root / "stage-3-review.png",
            machine_passed=True,
        )
    except Exception:
        if temporary_root is not None:
            shutil.rmtree(temporary_root, ignore_errors=True)
        raise


def build_stage3_artifacts(
    artifact_root: Path,
    *,
    rgba: np.ndarray,
    labels: np.ndarray,
    vector_document: Mapping[str, object],
    candidate: Mapping[str, object],
    preserved_files: Mapping[str, bytes],
    candidate_files: tuple[str, ...],
) -> dict[str, str]:
    """Write one complete deterministic Stage 3 candidate into an empty directory."""
    if any(artifact_root.iterdir()):
        raise FileExistsError(f"Stage 3 artifact root is not empty: {artifact_root}")
    regions = vector_document["regions"]
    if not isinstance(regions, list):
        raise ConversionError("Stage 3 vector-region document is invalid")
    for name, content in preserved_files.items():
        _validate_artifact_name(name)
        if name == "candidate-hashes.json":
            raise ConversionError("candidate hashes must be written last")
        (artifact_root / name).write_bytes(content)

    regions_path = artifact_root / "stage-3-vector-regions.json"
    svg_path = artifact_root / "stage-3-vector.svg"
    regions_path.write_bytes(_json_bytes(vector_document))
    svg_path.write_text(_svg(vector_document, rgba), encoding="utf-8")
    _write_png(artifact_root / "stage-3-review.png", _review_image(rgba, labels, vector_document))

    candidate_document = dict(candidate)
    candidate_document.update(
        {
            "regionCount": len(regions),
            "stage": 3,
            "vectorRegions": {
                "fileSha256": _hash_file(regions_path),
                "path": "stage-3-vector-regions.json",
            },
            "vectorSvg": {
                "fileSha256": _hash_file(svg_path),
                "path": "stage-3-vector.svg",
            },
        }
    )
    _write_json(artifact_root / "stage-3-candidate.json", candidate_document)
    hashes = _candidate_hashes(artifact_root, candidate_files)
    _write_json(artifact_root / "candidate-hashes.json", hashes)
    _verify_candidate_hashes(artifact_root, hashes)
    return hashes


def _vector_document(
    rgba: np.ndarray,
    labels: np.ndarray,
    source_regions: list[dict[str, object]],
    evidence: Mapping[str, object],
    profile: GenericStage3Profile,
) -> dict[str, object]:
    height, width = labels.shape
    alpha = rgba[..., 3] > 0
    piece_labels, piece_masks = _piece_masks(alpha)
    silhouettes = []
    for index, mask in enumerate(piece_masks):
        path = _silhouette_path(mask, profile)
        silhouettes.append(
            {
                "displayPath": path.data,
                "id": f"piece-{index + 1:02d}-silhouette",
                "outputMaskSha256": _hash_bytes(
                    _rasterize(path, width, height).tobytes()
                ),
                "pieceIndex": index,
                "primitive": "minimally-smoothed-alpha-contour",
                "sourceMaskSha256": _hash_bytes(mask.astype(np.uint8).tobytes()),
            }
        )

    source_masks = {
        int(region["id"]): labels == int(region["id"]) for region in source_regions
    }
    vector_masks: dict[int, np.ndarray] = {}
    paths: dict[int, DisplayPath] = {}
    symmetry: dict[int, dict[str, object]] = {}

    symmetry_pairs = _edge_symmetry_pairs(source_regions, width)
    locked_pair = (
        max(
            symmetry_pairs,
            key=lambda pair: sum(
                float(_region_by_id(source_regions, region_id)["anchor"][1])
                for region_id in pair
            ),
        )
        if symmetry_pairs
        else None
    )
    for left_id, right_id in symmetry_pairs:
        if left_id not in source_masks or right_id not in source_masks:
            continue
        canonical = source_masks[left_id] & np.fliplr(source_masks[right_id])
        if int(canonical.sum()) < 100:
            raise ConversionError(
                f"Stage 3 symmetry pair {left_id}/{right_id} has no stable overlap"
            )
        # The lower edge pair contains three intentional, persistent straights:
        # its top, bottom, and inner wall.  A consensus/intersection raster can
        # move those by a pixel before contour fitting, visibly changing their
        # angles.  Lock them to the accepted canonical contour and curve only
        # the routed transitions and alpha-clipped exterior.
        left_path = (
            _locked_lower_edge_path(source_masks[left_id], profile)
            if (left_id, right_id) == locked_pair
            else _feature_path(canonical, profile)
        )
        right_path = _mirror_path(left_path, width, height)
        paths[left_id], paths[right_id] = left_path, right_path
        vector_masks[left_id] = _rasterize(left_path, width, height)
        vector_masks[right_id] = _rasterize(right_path, width, height)
        pair = f"mirror-x-{width / 2:g}-{left_id}-{right_id}"
        symmetry[left_id] = {
            "axisX": width / 2,
            "canonicalRegionId": left_id,
            "pair": pair,
            "role": "canonical",
        }
        symmetry[right_id] = {
            "axisX": width / 2,
            "canonicalRegionId": left_id,
            "pair": pair,
            "role": "mirrored",
        }

    pocket_rows = _pocket_row_bounds(source_regions)
    for region in source_regions:
        region_id = int(region["id"])
        if region_id in paths:
            continue
        kind = str(region["type"])
        if kind == "pocket":
            bounds = list(region["bounds"])
            row = _row_for_region(region_id, pocket_rows)
            bounds[1], bounds[3] = pocket_rows[row][0], pocket_rows[row][1]
            path = _rounded_box_path(bounds, profile.pocket_corner_radius_fraction)
        else:
            path = _feature_path(source_masks[region_id], profile)
        paths[region_id] = path
        vector_masks[region_id] = _rasterize(path, width, height)

    regions: list[dict[str, object]] = []
    for region in source_regions:
        region_id = int(region["id"])
        source_mask = source_masks[region_id]
        piece_index = _piece_owner(source_mask, piece_labels)
        kind = str(region["type"])
        region_metadata = dict(region.get("metadata", {}))
        corner_metadata: dict[str, object] = {
            "policy": "rounded-mouth" if kind == "pocket" else "feature-preserving",
            "roundedOnlyWhereRouted": kind != "pocket",
        }
        if locked_pair is not None and region_id in locked_pair:
            corner_metadata = {
                "lockedSegments": ["top", "bottom", "inner-edge"],
                "policy": "persistent-straights-with-routed-transitions",
                "roundedTransitions": [
                    "inner-top",
                    "inner-bottom",
                    "alpha-clipped-exterior",
                ],
            }
        regions.append(
            {
                "anchor": list(region["anchor"]),
                "cornerMetadata": corner_metadata,
                "displayPath": paths[region_id].data,
                "id": region_id,
                "key": region["key"],
                "metadata": region_metadata,
                "outputMaskSha256": _hash_bytes(vector_masks[region_id].tobytes()),
                "pieceIndex": piece_index,
                "primitive": "rounded-mouth" if kind == "pocket" else "feature-contour",
                "sourceMaskSha256": _hash_bytes(source_mask.astype(np.uint8).tobytes()),
                "symmetry": symmetry.get(region_id),
                "type": kind,
            }
        )

    return {
        "canvas": {"height": height, "width": width},
        "inputAcceptance": evidence["stage2Acceptance"],
        "pieceCount": len(silhouettes),
        "profile": asdict(profile),
        "regions": regions,
        "schemaVersion": 1,
        "silhouettePaths": silhouettes,
        "stage": 3,
    }


def _approved_inputs(
    context: Stage3RunContext,
) -> tuple[np.ndarray, np.ndarray, list[dict[str, object]], dict[str, object]]:
    stages = context.manifest.get("stages")
    if not isinstance(stages, list) or len(stages) < 3:
        raise ConversionError("Stage 2 checkpoint is missing")
    stage1 = stages[1]
    stage2 = stages[2]
    if not isinstance(stage1, Mapping) or not isinstance(stage2, Mapping):
        raise ConversionError("Stage 3 input records are invalid")
    if stage1.get("status") != "approved" or stage2.get("status") != "approved":
        raise ConversionError("Stage 1 and Stage 2 must be approved")

    stage1_acceptance_path = _inside_root(context.root, stage1.get("acceptancePath"))
    stage2_acceptance_path = _inside_root(context.root, stage2.get("acceptancePath"))
    if _hash_file(stage1_acceptance_path) != stage1.get("acceptanceSha256"):
        raise ConversionError("Stage 1 acceptance hash changed")
    if _hash_file(stage2_acceptance_path) != stage2.get("acceptanceSha256"):
        raise ConversionError("Stage 2 acceptance hash changed")
    stage1_acceptance = _read_json(stage1_acceptance_path)
    stage2_acceptance = _read_json(stage2_acceptance_path)
    if stage2_acceptance.get("runIdentitySha256") != context.manifest.get(
        "runIdentitySha256"
    ):
        raise ConversionError("Stage 2 acceptance belongs to another run")
    expected_region_count = stage2_acceptance.get("regionCount")
    if type(expected_region_count) is not int or expected_region_count < 1:
        raise ConversionError("approved Stage 2 region count is invalid")

    rgba_path = _inside_root(context.root, stage1_acceptance["registered"]["path"])
    labels_path = _inside_root(context.root, stage2_acceptance["registered"]["path"])
    regions_path = _inside_root(context.root, stage2_acceptance["regions"]["path"])
    for path, record in (
        (rgba_path, stage1_acceptance["registered"]),
        (labels_path, stage2_acceptance["registered"]),
        (regions_path, stage2_acceptance["regions"]),
    ):
        if _hash_file(path) != record["fileSha256"]:
            raise ConversionError(f"accepted Stage 3 input changed: {path.name}")

    with Image.open(rgba_path) as image:
        if image.mode != "RGBA":
            raise ConversionError("Stage 1 input must be RGBA")
        rgba = np.asarray(image, dtype=np.uint8).copy()
    with Image.open(labels_path) as image:
        labels = np.asarray(image).astype(np.uint16)
    if labels.shape != rgba.shape[:2]:
        raise ConversionError("Stage 2 labels do not match Stage 1 RGBA")
    document = _read_json(regions_path)
    regions = document.get("regions")
    if not isinstance(regions, list) or len(regions) != expected_region_count:
        raise ConversionError("Stage 2 regions are invalid")
    reconstructed = np.zeros(labels.shape, np.uint16)
    seen_keys: set[str] = set()
    seen_ids: set[int] = set()
    previous_id = 0
    for region in regions:
        if not isinstance(region, dict):
            raise ConversionError("Stage 2 regions are invalid")
        region_id = region.get("id")
        if (
            type(region_id) is not int
            or region_id <= 0
            or region_id in seen_ids
            or region_id <= previous_id
        ):
            raise ConversionError("Stage 2 region IDs must be positive and increasing")
        key = region.get("key")
        if not isinstance(key, str) or not key or key in seen_keys:
            raise ConversionError("Stage 2 region keys must be stable and unique")
        if region.get("type") not in _TYPE_COLORS:
            raise ConversionError("Stage 2 region type is invalid")
        seen_ids.add(region_id)
        seen_keys.add(key)
        previous_id = region_id
        reconstructed[labels == region_id] = region_id
    if not np.array_equal(reconstructed, labels):
        raise ConversionError("Stage 2 label raster contains unknown IDs")
    evidence = {
        "stage1Rgba": {
            "path": stage1_acceptance["registered"]["path"],
            "sha256": _hash_file(rgba_path),
        },
        "stage2Acceptance": {
            "path": stage2["acceptancePath"],
            "sha256": stage2["acceptanceSha256"],
        },
        "stage2Labels": {
            "path": stage2_acceptance["registered"]["path"],
            "sha256": _hash_file(labels_path),
        },
        "stage2Regions": {
            "path": stage2_acceptance["regions"]["path"],
            "sha256": _hash_file(regions_path),
        },
    }
    return rgba, labels, regions, evidence


def _edge_symmetry_pairs(
    regions: list[dict[str, object]], width: int
) -> tuple[tuple[int, int], ...]:
    """Pair mirrored edge semantics using metadata and geometry, not product IDs."""
    left = [
        region
        for region in regions
        if region.get("type") == "edge"
        and isinstance(region.get("metadata"), dict)
        and region["metadata"].get("side") == "left"
    ]
    right = [
        region
        for region in regions
        if region.get("type") == "edge"
        and isinstance(region.get("metadata"), dict)
        and region["metadata"].get("side") == "right"
    ]
    available = {int(region["id"]): region for region in right}
    pairs: list[tuple[int, int]] = []
    for left_region in sorted(left, key=lambda value: int(value["id"])):
        left_metadata = {
            key: value
            for key, value in left_region["metadata"].items()
            if key != "side"
        }
        left_anchor = left_region.get("anchor")
        if not isinstance(left_anchor, list) or len(left_anchor) != 2:
            continue
        candidates = []
        for identifier, right_region in available.items():
            right_metadata = {
                key: value
                for key, value in right_region["metadata"].items()
                if key != "side"
            }
            right_anchor = right_region.get("anchor")
            if (
                right_metadata == left_metadata
                and isinstance(right_anchor, list)
                and len(right_anchor) == 2
            ):
                error = abs(float(left_anchor[0]) + float(right_anchor[0]) - width)
                error += abs(float(left_anchor[1]) - float(right_anchor[1]))
                candidates.append((error, identifier))
        if not candidates:
            continue
        error, right_id = min(candidates)
        if error <= max(6.0, width * 0.03):
            pairs.append((int(left_region["id"]), right_id))
            del available[right_id]
    return tuple(pairs)


def _region_by_id(
    regions: list[dict[str, object]], region_id: int
) -> dict[str, object]:
    return next(region for region in regions if int(region["id"]) == region_id)


def _piece_masks(alpha: np.ndarray) -> tuple[np.ndarray, list[np.ndarray]]:
    count, labels, stats, _ = cv2.connectedComponentsWithStats(
        alpha.astype(np.uint8), 8
    )
    components = [
        index for index in range(1, count) if int(stats[index, cv2.CC_STAT_AREA]) >= 50
    ]
    components.sort(key=lambda index: int(stats[index, cv2.CC_STAT_LEFT]))
    relabeled = np.zeros(labels.shape, np.int16)
    masks: list[np.ndarray] = []
    for piece_index, component in enumerate(components):
        mask = labels == component
        relabeled[mask] = piece_index + 1
        masks.append(mask)
    if not masks:
        raise ConversionError("Stage 1 alpha has no product silhouette")
    return relabeled, masks


def _piece_owner(mask: np.ndarray, piece_labels: np.ndarray) -> int:
    values, counts = np.unique(piece_labels[mask], return_counts=True)
    candidates = [
        (int(count), int(value) - 1)
        for value, count in zip(values, counts, strict=True)
        if value > 0
    ]
    if not candidates:
        raise ConversionError("Stage 2 region has no Stage 1 piece owner")
    return max(candidates)[1]


def _pocket_row_bounds(
    regions: list[dict[str, object]],
) -> dict[int, tuple[int, int, tuple[int, ...]]]:
    pockets = [region for region in regions if region["type"] == "pocket"]
    centers = sorted(
        (int(region["bounds"][1]) + int(region["bounds"][3])) / 2 for region in pockets
    )
    split = (centers[len(centers) // 2 - 1] + centers[len(centers) // 2]) / 2
    groups: dict[int, list[dict[str, object]]] = {0: [], 1: []}
    for region in pockets:
        center = (int(region["bounds"][1]) + int(region["bounds"][3])) / 2
        groups[0 if center < split else 1].append(region)
    result = {}
    for row, values in groups.items():
        top = int(round(float(np.median([region["bounds"][1] for region in values]))))
        bottom = int(
            round(float(np.median([region["bounds"][3] for region in values])))
        )
        result[row] = (top, bottom, tuple(int(region["id"]) for region in values))
    return result


def _row_for_region(
    region_id: int, rows: Mapping[int, tuple[int, int, tuple[int, ...]]]
) -> int:
    for row, (_top, _bottom, ids) in rows.items():
        if region_id in ids:
            return row
    raise ConversionError("pocket row assignment failed")


def _silhouette_path(mask: np.ndarray, profile: GenericStage3Profile) -> DisplayPath:
    points = _simplified_contour(mask, profile.silhouette_epsilon_fraction)
    data = _rounded_polygon_data(points, profile.silhouette_corner_radius)
    path = parse_display_path(
        data, "silhouette", mask.shape[1], mask.shape[0], allow_linear_segments=True
    )
    if path is None:
        raise ConversionError("silhouette vectorization failed")
    return path


def _feature_path(mask: np.ndarray, profile: GenericStage3Profile) -> DisplayPath:
    points = _simplified_contour(mask, profile.feature_epsilon_fraction)
    data = "M " + " L ".join(f"{_number(x)} {_number(y)}" for x, y in points) + " Z"
    path = parse_display_path(
        data, "feature", mask.shape[1], mask.shape[0], allow_linear_segments=True
    )
    if path is None:
        raise ConversionError("feature vectorization failed")
    return path


def _locked_lower_edge_path(
    mask: np.ndarray, profile: GenericStage3Profile
) -> DisplayPath:
    """Retain accepted lower-edge line angles and route only its transitions."""
    points = _simplified_contour(mask, profile.feature_epsilon_fraction)
    segments = [
        (points[index], points[(index + 1) % len(points)])
        for index in range(len(points))
    ]
    horizontal = sorted(
        segments,
        key=lambda pair: abs(float(pair[1][0] - pair[0][0])),
        reverse=True,
    )[:2]
    if len(horizontal) != 2:
        raise ConversionError("lower edge has no persistent top/bottom segments")
    horizontal.sort(key=lambda pair: float((pair[0][1] + pair[1][1]) / 2))
    top_pair, bottom_pair = horizontal
    top_outer, top_inner = sorted(
        (top_pair[0], top_pair[1]), key=lambda point: point[0]
    )
    bottom_outer, bottom_inner = sorted(
        (bottom_pair[0], bottom_pair[1]), key=lambda point: point[0]
    )
    inner_candidates = [
        pair for pair in segments if min(pair[0][0], pair[1][0]) > top_inner[0] - 4
    ]
    if not inner_candidates:
        raise ConversionError("lower edge has no persistent inner wall segment")
    vertical = max(
        inner_candidates,
        key=lambda pair: abs(float(pair[1][1] - pair[0][1])),
    )
    inner_top, inner_bottom = sorted(
        (vertical[0], vertical[1]), key=lambda point: point[1]
    )

    outer_points = points[points[:, 0] < top_outer[0] + 7]
    if len(outer_points):
        outer_x = float(np.min(outer_points[:, 0]))
        outer_mid_y = float(np.median(outer_points[:, 1]))
    else:
        outer_x = float(top_outer[0])
        outer_mid_y = float((top_outer[1] + bottom_outer[1]) / 2)
    upper_outer = np.asarray(
        (
            outer_x + 1.0,
            float(top_outer[1]) + min(4.0, (inner_top[1] - top_outer[1]) / 2),
        ),
        dtype=np.float64,
    )
    lower_outer = np.asarray(
        (outer_x + 4.0, float(bottom_outer[1]) - 2.0), dtype=np.float64
    )
    outer_mid = np.asarray((outer_x, outer_mid_y), dtype=np.float64)

    data = " ".join(
        (
            f"M {_point(top_outer)}",
            f"L {_point(top_inner)}",
            f"C {_point(top_inner + (inner_top - top_inner) * 0.42)} {_point(inner_top - (inner_top - top_inner) * 0.24)} {_point(inner_top)}",
            f"L {_point(inner_bottom)}",
            f"C {_point(inner_bottom + (bottom_inner - inner_bottom) * 0.34)} {_point(bottom_inner - (bottom_inner - inner_bottom) * 0.18)} {_point(bottom_inner)}",
            f"L {_point(bottom_outer)}",
            f"C {_point(bottom_outer + (lower_outer - bottom_outer) * 0.45)} {_point(lower_outer)} {_point(lower_outer)}",
            f"C {_point(lower_outer + (outer_mid - lower_outer) * 0.55)} {_point(outer_mid)} {_point(outer_mid)}",
            f"C {_point(outer_mid + (upper_outer - outer_mid) * 0.55)} {_point(upper_outer)} {_point(upper_outer)}",
            f"C {_point(upper_outer + (top_outer - upper_outer) * 0.48)} {_point(top_outer)} {_point(top_outer)} Z",
        )
    )
    path = parse_display_path(
        data,
        "locked lower edge",
        mask.shape[1],
        mask.shape[0],
        allow_linear_segments=True,
    )
    if path is None:
        raise ConversionError("lower edge vectorization failed")
    return path


def _simplified_contour(mask: np.ndarray, epsilon_fraction: float) -> np.ndarray:
    contours, _ = cv2.findContours(
        mask.astype(np.uint8), cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_NONE
    )
    if not contours:
        raise ConversionError("cannot vectorize an empty mask")
    contour = max(contours, key=cv2.contourArea)
    epsilon = max(0.5, cv2.arcLength(contour, True) * epsilon_fraction)
    points = cv2.approxPolyDP(contour, epsilon, True).reshape(-1, 2).astype(np.float64)
    if len(points) < 3:
        raise ConversionError("mask contour is degenerate")
    return points


def _rounded_polygon_data(points: np.ndarray, radius: float) -> str:
    entries: list[np.ndarray] = []
    exits: list[np.ndarray] = []
    for index, point in enumerate(points):
        previous = points[index - 1]
        following = points[(index + 1) % len(points)]
        before = point - previous
        after = following - point
        before_length = float(np.linalg.norm(before))
        after_length = float(np.linalg.norm(after))
        cut = min(radius, before_length * 0.22, after_length * 0.22)
        entries.append(point - before / max(before_length, 1e-9) * cut)
        exits.append(point + after / max(after_length, 1e-9) * cut)
    chunks = [f"M {_point(entries[0])}"]
    for index, point in enumerate(points):
        if index:
            chunks.append(f"L {_point(entries[index])}")
        chunks.append(f"Q {_point(point)} {_point(exits[index])}")
    chunks.append(f"L {_point(entries[0])} Z")
    return " ".join(chunks)


def _rounded_box_path(bounds: list[object], radius_fraction: float) -> DisplayPath:
    x0, y0, x1, y1 = (float(value) for value in bounds)
    radius = min((y1 - y0) * radius_fraction, (x1 - x0) / 2)
    kappa = 0.552284749831
    data = (
        f"M {_number(x0 + radius)} {_number(y0)} "
        f"L {_number(x1 - radius)} {_number(y0)} "
        f"C {_number(x1 - radius + kappa * radius)} {_number(y0)} {_number(x1)} {_number(y0 + radius - kappa * radius)} {_number(x1)} {_number(y0 + radius)} "
        f"L {_number(x1)} {_number(y1 - radius)} "
        f"C {_number(x1)} {_number(y1 - radius + kappa * radius)} {_number(x1 - radius + kappa * radius)} {_number(y1)} {_number(x1 - radius)} {_number(y1)} "
        f"L {_number(x0 + radius)} {_number(y1)} "
        f"C {_number(x0 + radius - kappa * radius)} {_number(y1)} {_number(x0)} {_number(y1 - radius + kappa * radius)} {_number(x0)} {_number(y1 - radius)} "
        f"L {_number(x0)} {_number(y0 + radius)} "
        f"C {_number(x0)} {_number(y0 + radius - kappa * radius)} {_number(x0 + radius - kappa * radius)} {_number(y0)} {_number(x0 + radius)} {_number(y0)} Z"
    )
    path = parse_display_path(
        data, "pocket", int(x1 + 1), int(y1 + 1), allow_linear_segments=True
    )
    if path is None:
        raise ConversionError("pocket vectorization failed")
    return path


def _mirror_path(path: DisplayPath, width: int, height: int) -> DisplayPath:
    tokens = path.data.split()
    output: list[str] = []
    index = 0
    arity = {"M": 2, "L": 2, "Q": 4, "C": 6, "Z": 0}
    while index < len(tokens):
        command = tokens[index]
        output.append(command)
        index += 1
        for coordinate_index in range(arity[command]):
            value = float(tokens[index])
            output.append(
                _number(width - value if coordinate_index % 2 == 0 else value)
            )
            index += 1
    mirrored = parse_display_path(
        " ".join(output), "mirrored", width, height, allow_linear_segments=True
    )
    if mirrored is None:
        raise ConversionError("symmetric vectorization failed")
    return mirrored


def _rasterize(path: DisplayPath, width: int, height: int) -> np.ndarray:
    contour = flatten_display_path(path, curve_steps=48)
    mask = np.zeros((height, width), np.uint8)
    cv2.fillPoly(mask, [np.rint(contour).astype(np.int32)], 1)
    return mask


def _svg(document: Mapping[str, object], rgba: np.ndarray) -> str:
    height, width = rgba.shape[:2]
    source = BytesIO()
    Image.fromarray(rgba, "RGBA").save(
        source, format="PNG", optimize=False, compress_level=9
    )
    encoded = base64.b64encode(source.getvalue()).decode("ascii")
    pieces = "\n".join(
        f'  <path id="{piece["id"]}" data-piece-index="{piece["pieceIndex"]}" data-type="piece-silhouette" d="{piece["displayPath"]}" fill="none" stroke="#735b42" stroke-width="1" />'
        for piece in document["silhouettePaths"]
    )
    regions = "\n".join(
        f'  <path id="region-{int(region["id"]):02d}" data-region-id="{region["id"]}" data-key="{region["key"]}" data-type="{region["type"]}" data-piece-index="{region["pieceIndex"]}" d="{region["displayPath"]}" fill="#ffffff" fill-opacity="0" stroke="#171919" stroke-width="1" pointer-events="all" />'
        for region in document["regions"]
    )
    return (
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}">\n'
        f'  <image width="{width}" height="{height}" href="data:image/png;base64,{encoded}" />\n'
        f"{pieces}\n{regions}\n</svg>\n"
    )


def _review_image(
    rgba: np.ndarray, labels: np.ndarray, document: Mapping[str, object]
) -> np.ndarray:
    height, width = labels.shape
    panel1 = rgba[..., :3].copy()
    panel1[rgba[..., 3] == 0] = 250
    blended = panel1.astype(np.float32)
    panel2 = np.full((height, width, 3), 244, np.uint8)
    all_source = labels > 0
    all_vector = np.zeros_like(all_source)
    vector_masks: dict[int, np.ndarray] = {}
    for region in document["regions"]:
        region_id = int(region["id"])
        path = parse_display_path(
            region["displayPath"], "review", width, height, allow_linear_segments=True
        )
        if path is None:
            raise ConversionError("review vector path is invalid")
        mask = _rasterize(path, width, height).astype(bool)
        vector_masks[region_id] = mask
        all_vector |= mask
        color = np.asarray(_TYPE_COLORS[str(region["type"])], np.float32)
        blended[mask] = blended[mask] * 0.58 + color * 0.42
    panel1 = np.clip(blended, 0, 255).astype(np.uint8)

    overlap = all_source & all_vector
    panel2[overlap] = (62, 166, 91)
    panel2[all_vector & ~all_source] = (222, 52, 165)
    panel2[all_source & ~all_vector] = (246, 202, 48)
    alpha_boundary = _boundary(rgba[..., 3] > 0)
    panel1[alpha_boundary] = (80, 66, 50)
    panel2[alpha_boundary] = (48, 48, 48)

    for region in document["regions"]:
        region_id = int(region["id"])
        source = labels == region_id
        vector = vector_masks[region_id]
        panel1[_boundary(source)] = (255, 255, 255)
        panel1[_boundary(vector)] = (0, 235, 255)
        panel2[_boundary(source)] = (255, 255, 255)
        panel2[_boundary(vector)] = (0, 210, 235)

    header = 48
    legend = 43
    canvas = Image.new("RGB", (width * 2, header + height + legend), (247, 246, 243))
    canvas.paste(Image.fromarray(panel1), (0, header))
    canvas.paste(Image.fromarray(panel2), (width, header))
    draw = ImageDraw.Draw(canvas)
    title = _font(18, bold=True)
    small = _font(13)
    badge = _font(12, bold=True)
    draw.text(
        (18, 13), "Vector geometry over approved photo", font=title, fill=(32, 32, 32)
    )
    draw.text(
        (width + 18, 13),
        "Fidelity: green overlap · magenta vector-only · yellow Stage 2-only",
        font=title,
        fill=(32, 32, 32),
    )
    draw.line((width, 0, width, header + height), fill=(190, 188, 181), width=2)
    for region in document["regions"]:
        x, y = (int(value) for value in region["anchor"])
        radius = 9
        draw.ellipse(
            (x - radius, header + y - radius, x + radius, header + y + radius),
            fill=(25, 25, 25),
            outline=(255, 255, 255),
            width=1,
        )
        text = str(region["id"])
        bbox = draw.textbbox((0, 0), text, font=badge)
        draw.text(
            (x - (bbox[2] - bbox[0]) / 2, header + y - (bbox[3] - bbox[1]) / 2 - 1),
            text,
            font=badge,
            fill=(255, 255, 255),
        )
    legend_y = header + height
    draw.line((0, legend_y, width * 2, legend_y), fill=(205, 202, 195), width=1)
    x = 18
    for kind in ("jug", "sloper", "edge", "pocket"):
        draw.rounded_rectangle(
            (x, legend_y + 14, x + 15, legend_y + 29), radius=4, fill=_TYPE_COLORS[kind]
        )
        draw.text((x + 22, legend_y + 13), kind, font=small, fill=(55, 55, 55))
        x += 116
    draw.text(
        (width + 18, legend_y + 13),
        "cyan = vector boundary · white = approved Stage 2 boundary · dark = Stage 1 silhouette",
        font=small,
        fill=(55, 55, 55),
    )
    return np.asarray(canvas)


def _boundary(mask: np.ndarray) -> np.ndarray:
    eroded = cv2.erode(mask.astype(np.uint8), np.ones((3, 3), np.uint8)) > 0
    return mask & ~eroded


def _font(
    size: int, *, bold: bool = False
) -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
    names = (
        ["DejaVuSans-Bold.ttf", "Arial Bold.ttf"]
        if bold
        else ["DejaVuSans.ttf", "Arial.ttf"]
    )
    for name in names:
        try:
            return ImageFont.truetype(name, size)
        except OSError:
            continue
    return ImageFont.load_default()


def _inside_root(root: Path, relative: object) -> Path:
    if not isinstance(relative, str) or not relative or Path(relative).is_absolute():
        raise ConversionError("Stage 3 evidence path is invalid")
    root_resolved = root.resolve()
    path = (root / relative).resolve()
    try:
        path.relative_to(root_resolved)
    except ValueError as error:
        raise ConversionError("Stage 3 evidence leaves the run root") from error
    return path


def _read_json(path: Path) -> dict[str, object]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        raise ConversionError(f"invalid Stage 3 evidence: {path.name}") from error
    if not isinstance(value, dict):
        raise ConversionError(f"Stage 3 evidence must be an object: {path.name}")
    return value


def _json_bytes(value: object) -> bytes:
    return (json.dumps(value, indent=2, sort_keys=True) + "\n").encode()


def _write_json(path: Path, value: object) -> None:
    path.write_bytes(_json_bytes(value))


def _write_png(path: Path, image: np.ndarray) -> None:
    Image.fromarray(image).save(path, format="PNG", optimize=False, compress_level=9)


def _hash_file(path: Path) -> str:
    return _hash_bytes(path.read_bytes())


def _hash_bytes(value: bytes) -> str:
    return sha256(value).hexdigest()


def _candidate_hashes(root: Path, names: tuple[str, ...]) -> dict[str, str]:
    hashes: dict[str, str] = {}
    for name in names:
        _validate_artifact_name(name)
        if name == "candidate-hashes.json" or name in hashes:
            raise ConversionError(f"invalid Stage 3 candidate artifact: {name}")
        path = root / name
        if not path.is_file():
            raise ConversionError(f"missing Stage 3 candidate artifact: {name}")
        hashes[name] = _hash_file(path)
    return hashes


def _verify_candidate_hashes(root: Path, hashes: Mapping[str, str]) -> None:
    recorded = _read_json(root / "candidate-hashes.json")
    if recorded != hashes or any(
        _hash_file(root / name) != expected for name, expected in hashes.items()
    ):
        raise ConversionError("Stage 3 candidate hash verification failed")


def _validate_artifact_name(name: str) -> None:
    if not isinstance(name, str) or not name or Path(name).name != name:
        raise ConversionError("Stage 3 candidate artifact name is invalid")


def _number(value: float) -> str:
    rounded = round(float(value), 3)
    return f"{rounded:.3f}".rstrip("0").rstrip(".")


def _point(value: np.ndarray) -> str:
    return f"{_number(float(value[0]))} {_number(float(value[1]))}"
