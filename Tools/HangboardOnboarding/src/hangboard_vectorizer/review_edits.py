"""Transactional materialization of reviewed Stage 2 and Stage 3 geometry."""

from __future__ import annotations

from collections.abc import Mapping
from copy import deepcopy
from hashlib import sha256
import json
import math
from pathlib import Path
import shutil
import tempfile
from types import MappingProxyType

import cv2
import numpy as np

from .display_paths import flatten_display_path, parse_display_path
from .generic_stage0 import StageCheckpoint
from . import generic_stage2, generic_stage3
from .models import ConversionError
from .onboarding_run import RunContext


_REGION_TYPES = frozenset(("jug", "sloper", "edge", "pocket"))
_STAGE_DERIVED_FILES = {
    2: frozenset(
        (
            "candidate-hashes.json",
            "stage-2-candidate.json",
            "stage-2-labels.png",
            "stage-2-regions.json",
            "stage-2-review.png",
        )
    ),
    3: frozenset(
        (
            "candidate-hashes.json",
            "stage-3-candidate.json",
            "stage-3-vector-regions.json",
            "stage-3-vector.svg",
            "stage-3-review.png",
        )
    ),
}


def materialize_stage2_edit(
    context: RunContext,
    document: Mapping[str, object],
    artifact_root: Path,
) -> StageCheckpoint:
    """Build a new immutable Stage 2 candidate from reviewed contours."""
    validated = validate_stage_edit(2, document)
    rgba, evidence = generic_stage2._approved_stage1_rgba(context)
    _require_canvas(validated, width=rgba.shape[1], height=rgba.shape[0], stage=2)
    candidate, preserved, candidate_files, baseline = _pending_candidate(context, 2)
    original = _read_object(baseline / "stage-2-regions.json", "Stage 2 baseline")
    _require_stage2_identity(validated, original)
    labels, normalized = _stage2_labels(validated, rgba.shape[:2])
    region_document = deepcopy(dict(validated))
    region_document["regions"] = normalized
    if candidate.get("inputAcceptance") != evidence["acceptance"]:
        raise ConversionError("Stage 2 edit does not bind the approved Stage 1 input")

    def build(temporary_root: Path) -> dict[str, str]:
        return generic_stage2.build_stage2_artifacts(
            temporary_root,
            rgba=rgba,
            labels=labels,
            region_document=region_document,
            candidate=candidate,
            preserved_files=preserved,
            candidate_files=candidate_files,
        )

    hashes = _publish_transaction(artifact_root, stage=2, build=build)
    return StageCheckpoint(
        stage=2,
        artifact_root=artifact_root,
        candidate_hashes=MappingProxyType(hashes),
        review_path=artifact_root / "stage-2-review.png",
        machine_passed=True,
    )


def materialize_stage3_edit(
    context: RunContext,
    document: Mapping[str, object],
    artifact_root: Path,
) -> StageCheckpoint:
    """Build a new immutable Stage 3 candidate from reviewed display paths."""
    validated = validate_stage_edit(3, document)
    rgba, labels, source_regions, evidence = generic_stage3._approved_inputs(context)
    _require_canvas(validated, width=rgba.shape[1], height=rgba.shape[0], stage=3)
    candidate, preserved, candidate_files, baseline = _pending_candidate(context, 3)
    original = _read_object(baseline / "stage-3-vector-regions.json", "Stage 3 baseline")
    _require_stage3_order(validated, original, source_regions)
    vector_document = _stage3_document(validated, rgba, labels, evidence)

    def build(temporary_root: Path) -> dict[str, str]:
        return generic_stage3.build_stage3_artifacts(
            temporary_root,
            rgba=rgba,
            labels=labels,
            vector_document=vector_document,
            candidate=candidate,
            preserved_files=preserved,
            candidate_files=candidate_files,
        )

    hashes = _publish_transaction(artifact_root, stage=3, build=build)
    return StageCheckpoint(
        stage=3,
        artifact_root=artifact_root,
        candidate_hashes=MappingProxyType(hashes),
        review_path=artifact_root / "stage-3-review.png",
        machine_passed=True,
    )


def validate_stage_edit(stage: int, document: object) -> Mapping[str, object]:
    """Validate the shared, product-neutral geometry contract for a reviewed edit."""
    if stage not in (2, 3):
        raise ValueError("review edits are supported only for Stage 2 and Stage 3")
    if not isinstance(document, Mapping):
        raise ConversionError(f"Stage {stage} edit document must be an object")
    if document.get("stage") != stage:
        raise ConversionError(f"Stage {stage} edit document has the wrong stage")
    canvas = document.get("canvas")
    if not isinstance(canvas, Mapping):
        raise ConversionError(f"Stage {stage} edit canvas is missing")
    width = canvas.get("width")
    height = canvas.get("height")
    if type(width) is not int or type(height) is not int or width < 1 or height < 1:
        raise ConversionError(f"Stage {stage} edit canvas is invalid")
    raw_regions = document.get("regions")
    if not isinstance(raw_regions, list) or not raw_regions:
        raise ConversionError(f"Stage {stage} edit has no regions")

    keys: set[str] = set()
    for expected_id, raw in enumerate(raw_regions, start=1):
        if not isinstance(raw, Mapping):
            _region_error(stage, expected_id, "must be an object")
        if "id" not in raw:
            _region_error(stage, expected_id, "stable ID is missing, duplicated, or out of order")
        region_id = raw.get("id")
        if type(region_id) is not int or region_id != expected_id:
            _region_error(stage, region_id, "stable ID is missing, duplicated, or out of order")
        key = raw.get("key")
        if not isinstance(key, str) or not key or key in keys:
            _region_error(stage, region_id, "stable key is missing or duplicated")
        keys.add(key)
        if raw.get("type") not in _REGION_TYPES:
            _region_error(stage, region_id, "type is invalid")
        _validate_point(raw.get("anchor"), width, height, stage, region_id, "anchor")
        if stage == 2:
            _validate_bounds(raw.get("bounds"), width, height, stage, region_id)
            contour = raw.get("contour")
            if not isinstance(contour, list) or len(contour) < 3:
                _region_error(stage, region_id, "contour must have at least 3 vertices")
            for point in contour:
                _validate_point(point, width, height, stage, region_id, "contour")
            if _self_intersects(np.asarray(contour, dtype=np.float64)):
                _region_error(stage, region_id, "contour has a prohibited self-intersection")
        else:
            try:
                path = parse_display_path(
                    raw.get("displayPath"),
                    f"Stage 3 region {region_id} displayPath",
                    width,
                    height,
                    allow_linear_segments=True,
                )
            except ConversionError as error:
                raise ConversionError(f"Stage 3 region {region_id}: malformed displayPath") from error
            if path is None:
                _region_error(stage, region_id, "malformed displayPath")
            try:
                contour = flatten_display_path(path, curve_steps=32)
            except ValueError as error:
                raise ConversionError(f"Stage 3 region {region_id}: malformed displayPath") from error
            if _self_intersects(contour):
                _region_error(stage, region_id, "displayPath has a prohibited self-intersection")
    if stage == 2 and document.get("labelEncoding") != "uint16-region-id":
        raise ConversionError("Stage 2 edit label encoding is invalid")
    if stage == 3:
        _validate_silhouettes(document, width, height)
    return deepcopy(dict(document))


def _stage2_labels(
    document: Mapping[str, object], shape: tuple[int, int]
) -> tuple[np.ndarray, list[dict[str, object]]]:
    labels = np.zeros(shape, dtype=np.uint16)
    normalized: list[dict[str, object]] = []
    for raw in document["regions"]:
        region = deepcopy(dict(raw))
        region_id = int(region["id"])
        contour = np.rint(np.asarray(region["contour"], dtype=np.float64)).astype(np.int32)
        mask = np.zeros(shape, dtype=np.uint8)
        cv2.fillPoly(mask, [contour], 1, lineType=cv2.LINE_8)
        occupied = mask.astype(bool)
        if np.any(occupied & (labels != 0)):
            _region_error(2, region_id, "contour overlaps another region")
        area = int(occupied.sum())
        if area == 0:
            _region_error(2, region_id, "contour produces an empty label")
        anchor_x, anchor_y = (int(round(float(value))) for value in region["anchor"])
        if not occupied[anchor_y, anchor_x]:
            _region_error(2, region_id, "anchor is outside its contour")
        labels[occupied] = region_id
        ys, xs = np.nonzero(occupied)
        region["areaPixels"] = area
        region["bounds"] = [
            int(xs.min()),
            int(ys.min()),
            int(xs.max()) + 1,
            int(ys.max()) + 1,
        ]
        normalized.append(region)
    return labels, normalized


def _stage3_document(
    document: Mapping[str, object],
    rgba: np.ndarray,
    labels: np.ndarray,
    evidence: Mapping[str, object],
) -> dict[str, object]:
    result = deepcopy(dict(document))
    result["inputAcceptance"] = evidence["stage2Acceptance"]
    width, height = int(rgba.shape[1]), int(rgba.shape[0])
    piece_labels, piece_masks = generic_stage3._piece_masks(rgba[..., 3] > 0)
    result["pieceCount"] = len(piece_masks)
    for silhouette in result["silhouettePaths"]:
        identifier = silhouette["id"]
        piece_index = silhouette.get("pieceIndex")
        if type(piece_index) is not int or not 0 <= piece_index < len(piece_masks):
            raise ConversionError(
                f"Stage 3 silhouette {identifier} has an invalid piece index"
            )
        path = parse_display_path(
            silhouette["displayPath"],
            f"Stage 3 silhouette {identifier} displayPath",
            width,
            height,
            allow_linear_segments=True,
        )
        assert path is not None
        output_mask = generic_stage3._rasterize(path, width, height)
        source_mask = piece_masks[piece_index].astype(np.uint8)
        silhouette["outputMaskSha256"] = sha256(output_mask.tobytes()).hexdigest()
        silhouette["sourceMaskSha256"] = sha256(source_mask.tobytes()).hexdigest()
    for region in result["regions"]:
        region_id = int(region["id"])
        path = parse_display_path(
            region["displayPath"],
            f"Stage 3 region {region_id} displayPath",
            width,
            height,
            allow_linear_segments=True,
        )
        assert path is not None
        output_mask = generic_stage3._rasterize(path, width, height)
        source_mask = (labels == region_id).astype(np.uint8)
        region["pieceIndex"] = generic_stage3._piece_owner(
            source_mask.astype(bool), piece_labels
        )
        region["outputMaskSha256"] = sha256(output_mask.tobytes()).hexdigest()
        region["sourceMaskSha256"] = sha256(source_mask.tobytes()).hexdigest()
    return result


def _require_stage3_order(
    edited: Mapping[str, object],
    original: Mapping[str, object],
    source_regions: list[dict[str, object]],
) -> None:
    edited_regions = edited["regions"]
    original_regions = original.get("regions")
    if not isinstance(original_regions, list):
        raise ConversionError("Stage 3 baseline regions are invalid")
    edited_identity = [(region["id"], region["key"], region["type"]) for region in edited_regions]
    original_identity = [
        (region.get("id"), region.get("key"), region.get("type"))
        for region in original_regions
        if isinstance(region, Mapping)
    ]
    source_identity = [
        (region.get("id"), region.get("key"), region.get("type"))
        for region in source_regions
    ]
    if edited_identity != original_identity or edited_identity != source_identity:
        mismatch: object = "missing"
        reference = original_identity if original_identity != edited_identity else source_identity
        for index in range(max(len(edited_identity), len(reference))):
            if index >= len(edited_identity):
                mismatch = reference[index][0]
                break
            if index >= len(reference) or edited_identity[index] != reference[index]:
                mismatch = edited_identity[index][0]
                break
        _region_error(3, mismatch, "region order or stable identity changed")


def _require_stage2_identity(
    edited: Mapping[str, object], original: Mapping[str, object]
) -> None:
    original_regions = original.get("regions")
    if not isinstance(original_regions, list):
        raise ConversionError("Stage 2 baseline regions are invalid")
    edited_identity = [
        (region["id"], region["key"], region["type"])
        for region in edited["regions"]
    ]
    original_identity = [
        (region.get("id"), region.get("key"), region.get("type"))
        for region in original_regions
        if isinstance(region, Mapping)
    ]
    if edited_identity == original_identity:
        return
    mismatch: object = "missing"
    for index in range(max(len(edited_identity), len(original_identity))):
        if index >= len(edited_identity):
            mismatch = original_identity[index][0]
            break
        if index >= len(original_identity) or edited_identity[index] != original_identity[index]:
            mismatch = edited_identity[index][0]
            break
    _region_error(2, mismatch, "stable identity is missing or changed")


def _pending_candidate(
    context: RunContext, stage: int
) -> tuple[dict[str, object], dict[str, bytes], tuple[str, ...], Path]:
    pipeline = context.manifest.get("pipeline")
    if (
        not isinstance(pipeline, Mapping)
        or pipeline.get("status") != "awaiting_approval"
        or pipeline.get("currentStage") != stage
    ):
        raise ConversionError(f"Stage {stage} is not awaiting approval")
    stages = context.manifest.get("stages")
    if not isinstance(stages, list):
        raise ConversionError(f"Stage {stage} pending checkpoint is missing")
    record = next(
        (
            item
            for item in reversed(stages)
            if isinstance(item, Mapping)
            and item.get("stage") == stage
            and item.get("status") == "review_pending"
        ),
        None,
    )
    if record is None:
        raise ConversionError(f"Stage {stage} pending checkpoint is missing")
    baseline = _inside_root(context.root, record.get("artifactRoot"), stage)
    hashes_path = _inside_root(context.root, record.get("candidateHashesPath"), stage)
    if (
        hashes_path != baseline / "candidate-hashes.json"
        or _hash_file(hashes_path) != record.get("candidateHashesSha256")
    ):
        raise ConversionError(f"Stage {stage} pending candidate hashes changed")
    hashes = _read_object(hashes_path, f"Stage {stage} hashes")
    candidate_files = tuple(hashes)
    for name, expected in hashes.items():
        if not isinstance(name, str) or Path(name).name != name or not isinstance(expected, str):
            raise ConversionError(f"Stage {stage} candidate hash contract is invalid")
        if _hash_file(baseline / name) != expected:
            raise ConversionError(f"Stage {stage} pending candidate changed: {name}")
    candidate = _read_object(
        baseline / f"stage-{stage}-candidate.json", f"Stage {stage} candidate"
    )
    preserved: dict[str, bytes] = {}
    derived = _STAGE_DERIVED_FILES[stage]
    for path in baseline.iterdir():
        if path.name not in derived:
            if not path.is_file() or path.is_symlink():
                raise ConversionError(f"Stage {stage} pending artifact is invalid: {path.name}")
            preserved[path.name] = path.read_bytes()
    return candidate, preserved, candidate_files, baseline


def _publish_transaction(artifact_root: Path, *, stage: int, build) -> dict[str, str]:
    artifact_root = Path(artifact_root)
    if artifact_root.exists() or artifact_root.is_symlink():
        raise FileExistsError(f"Stage {stage} artifact root already exists: {artifact_root}")
    artifact_root.parent.mkdir(parents=True, exist_ok=True)
    temporary_root = Path(
        tempfile.mkdtemp(prefix=f".{artifact_root.name}.tmp-", dir=artifact_root.parent)
    )
    try:
        hashes = build(temporary_root)
        if artifact_root.exists() or artifact_root.is_symlink():
            raise FileExistsError(f"Stage {stage} artifact root already exists: {artifact_root}")
        temporary_root.rename(artifact_root)
        return hashes
    except Exception:
        shutil.rmtree(temporary_root, ignore_errors=True)
        raise


def _validate_silhouettes(document: Mapping[str, object], width: int, height: int) -> None:
    silhouettes = document.get("silhouettePaths")
    if not isinstance(silhouettes, list) or not silhouettes:
        raise ConversionError("Stage 3 edit silhouette paths are missing")
    identifiers: set[str] = set()
    for index, raw in enumerate(silhouettes):
        if not isinstance(raw, Mapping):
            raise ConversionError(f"Stage 3 silhouette {index} is invalid")
        identifier = raw.get("id")
        if not isinstance(identifier, str) or not identifier or identifier in identifiers:
            raise ConversionError(f"Stage 3 silhouette {identifier} has an invalid stable ID")
        identifiers.add(identifier)
        try:
            path = parse_display_path(
                raw.get("displayPath"),
                f"Stage 3 silhouette {identifier} displayPath",
                width,
                height,
                allow_linear_segments=True,
            )
        except ConversionError as error:
            raise ConversionError(
                f"Stage 3 silhouette {identifier} has a malformed displayPath"
            ) from error
        if path is None:
            raise ConversionError(f"Stage 3 silhouette {identifier} has a malformed displayPath")
        try:
            contour = flatten_display_path(path, curve_steps=32)
        except ValueError as error:
            raise ConversionError(
                f"Stage 3 silhouette {identifier} has a malformed displayPath"
            ) from error
        if _self_intersects(contour):
            raise ConversionError(
                f"Stage 3 silhouette {identifier} has a prohibited self-intersection"
            )


def _validate_point(
    value: object,
    width: int,
    height: int,
    stage: int,
    region_id: object,
    field: str,
) -> None:
    if not isinstance(value, list) or len(value) != 2:
        _region_error(stage, region_id, f"{field} coordinate is invalid")
    x, y = value
    if (
        isinstance(x, bool)
        or isinstance(y, bool)
        or not isinstance(x, (int, float))
        or not isinstance(y, (int, float))
        or not math.isfinite(float(x))
        or not math.isfinite(float(y))
        or not 0 <= float(x) < width
        or not 0 <= float(y) < height
    ):
        _region_error(stage, region_id, f"{field} coordinate is non-finite or out of bounds")


def _validate_bounds(
    value: object,
    width: int,
    height: int,
    stage: int,
    region_id: object,
) -> None:
    if not isinstance(value, list) or len(value) != 4:
        _region_error(stage, region_id, "bounds are invalid")
    if any(
        isinstance(item, bool)
        or not isinstance(item, (int, float))
        or not math.isfinite(float(item))
        for item in value
    ):
        _region_error(stage, region_id, "bounds are non-finite or out of bounds")
    x0, y0, x1, y1 = (float(item) for item in value)
    if not (0 <= x0 < x1 <= width and 0 <= y0 < y1 <= height):
        _region_error(stage, region_id, "bounds are non-finite or out of bounds")


def _self_intersects(contour: np.ndarray) -> bool:
    points = np.asarray(contour, dtype=np.float64)
    if len(points) > 1:
        points = points[
            np.concatenate((np.asarray([True]), np.any(points[1:] != points[:-1], axis=1)))
        ]
    if len(points) > 1 and np.array_equal(points[0], points[-1]):
        points = points[:-1]
    if len(points) < 3 or np.unique(points, axis=0).shape[0] < 3:
        return True
    count = len(points)
    for first_index in range(count):
        first_start = points[first_index]
        first_end = points[(first_index + 1) % count]
        if np.array_equal(first_start, first_end):
            return True
        for second_index in range(first_index + 1, count):
            if second_index == first_index + 1 or (
                first_index == 0 and second_index == count - 1
            ):
                continue
            second_start = points[second_index]
            second_end = points[(second_index + 1) % count]
            if _segments_intersect(first_start, first_end, second_start, second_end):
                return True
    return False


def _segments_intersect(
    first_start: np.ndarray,
    first_end: np.ndarray,
    second_start: np.ndarray,
    second_end: np.ndarray,
) -> bool:
    epsilon = 1e-9

    def cross(a: np.ndarray, b: np.ndarray, c: np.ndarray) -> float:
        first = b - a
        second = c - a
        return float(first[0] * second[1] - first[1] * second[0])

    def on_segment(a: np.ndarray, b: np.ndarray, point: np.ndarray) -> bool:
        return (
            min(a[0], b[0]) - epsilon <= point[0] <= max(a[0], b[0]) + epsilon
            and min(a[1], b[1]) - epsilon <= point[1] <= max(a[1], b[1]) + epsilon
        )

    first_cross = cross(first_start, first_end, second_start)
    second_cross = cross(first_start, first_end, second_end)
    third_cross = cross(second_start, second_end, first_start)
    fourth_cross = cross(second_start, second_end, first_end)
    if (
        ((first_cross > epsilon and second_cross < -epsilon) or (first_cross < -epsilon and second_cross > epsilon))
        and ((third_cross > epsilon and fourth_cross < -epsilon) or (third_cross < -epsilon and fourth_cross > epsilon))
    ):
        return True
    return any(
        abs(value) <= epsilon and on_segment(start, end, point)
        for value, start, end, point in (
            (first_cross, first_start, first_end, second_start),
            (second_cross, first_start, first_end, second_end),
            (third_cross, second_start, second_end, first_start),
            (fourth_cross, second_start, second_end, first_end),
        )
    )


def _require_canvas(
    document: Mapping[str, object], *, width: int, height: int, stage: int
) -> None:
    if document["canvas"] != {"height": height, "width": width}:
        raise ConversionError(f"Stage {stage} edit canvas does not match the approved input")


def _inside_root(root: Path, relative: object, stage: int) -> Path:
    if not isinstance(relative, str) or not relative or Path(relative).is_absolute():
        raise ConversionError(f"Stage {stage} pending artifact path is invalid")
    resolved_root = root.resolve()
    path = (root / relative).resolve()
    if path == resolved_root or resolved_root not in path.parents:
        raise ConversionError(f"Stage {stage} pending artifact path escapes the run")
    return path


def _read_object(path: Path, field: str) -> dict[str, object]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        raise ConversionError(f"{field} is invalid") from error
    if not isinstance(value, dict):
        raise ConversionError(f"{field} is invalid")
    return value


def _hash_file(path: Path) -> str:
    try:
        return sha256(path.read_bytes()).hexdigest()
    except OSError as error:
        raise ConversionError(f"could not read reviewed artifact: {path.name}") from error


def _region_error(stage: int, region_id: object, message: str) -> None:
    raise ConversionError(f"Stage {stage} region {region_id}: {message}")
