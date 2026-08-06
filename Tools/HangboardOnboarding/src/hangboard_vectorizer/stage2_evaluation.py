"""Oracle-isolated evaluation for serialized Stage 2 candidates."""

from __future__ import annotations

from hashlib import sha256
import json
from pathlib import Path
import re
from typing import Mapping

import cv2
import numpy as np
from PIL import Image, ImageDraw, ImageFont

from .hold_discovery import _mask_geometry, decode_mask_rle
from .semantic_holds import SEMANTIC_PROMPT_ID, SEMANTIC_PROMPT_SHA256


_CANDIDATE_ARTIFACT_NAMES = frozenset({
    "stage-2-proposals.json",
    "stage-2-source-rgba.png",
    "stage-2-labels.png",
    "stage-2-candidates.png",
    "stage-2-auto-regions.json",
    "stage-2-auto-regions-labeled.png",
    "stage-2-generation.json",
})
_THRESHOLDS = {
    # Stage 2 accepts raw, image-derived discovery geometry.  Presentation
    # smoothing and exact display contours are deliberately deferred to Stage 3.
    "microIou": (">=", 0.85),
    "medianRegionIou": (">=", 0.85),
    "minimumRegionIou": (">=", 0.70),
    "medianBoundaryFScore": (">=", 0.85),
    "minimumBoundaryFScore": (">=", 0.50),
    "medianCentroidDisplacementPx": ("<=", 3.0),
    "maximumCentroidDisplacementPx": ("<=", 10.0),
    "maximumHd95Px": ("<=", 10.0),
}


def evaluate_stage2_candidate(
    candidate_root: Path,
    *,
    oracle_paths: Mapping[str, str] | None = None,
) -> dict[str, object]:
    """Evaluate already-written candidate bytes, loading oracle data last."""
    regions_path = candidate_root / "stage-2-auto-regions.json"
    hashes_path = candidate_root / "stage-2-candidate-hashes.json"
    labels_path = candidate_root / "stage-2-labels.png"
    if not regions_path.is_file() or not hashes_path.is_file() or not labels_path.is_file():
        raise FileNotFoundError("serialized Stage 2 candidate bundle is incomplete")
    candidate_raw = regions_path.read_bytes()
    document = json.loads(candidate_raw.decode("utf-8"))
    hashes = json.loads(hashes_path.read_text(encoding="utf-8"))
    _verify_candidate_hashes(candidate_root, hashes)
    generation = json.loads((candidate_root / "stage-2-generation.json").read_text(encoding="utf-8"))
    source_rgba = _load_candidate_image(
        candidate_root / "stage-2-source-rgba.png", mode="RGBA"
    )
    height, width = source_rgba.shape[:2]
    labels = _load_label_raster(labels_path, (height, width))
    _validate_generation_evidence(
        generation,
        source_pixel_sha256=sha256(source_rgba.tobytes()).hexdigest(),
        response_sha256=sha256((candidate_root / "stage-2-proposals.json").read_bytes()).hexdigest(),
    )
    candidates = _candidate_masks(
        document, (height, width), labels=labels,
        source_pixel_sha256=sha256(source_rgba.tobytes()).hexdigest(),
    )
    _load_candidate_image(candidate_root / "stage-2-candidates.png", mode="RGB", shape=(height, width))
    auto_rgba = _load_candidate_image(
        candidate_root / "stage-2-auto-regions-labeled.png", mode="RGB", shape=(height, width)
    )

    # This is the first oracle access in the entire pipeline.  Importing here
    # keeps generation runnable when the evaluator and accepted evidence are absent.
    if oracle_paths is None:
        from .beastmaker_v14_paths import ACCEPTED_V14_PATHS
        oracle_paths = ACCEPTED_V14_PATHS
    oracle = _oracle_masks(oracle_paths, width, height)
    pairs = _pair_by_type(candidates, oracle)
    metrics = [_region_metrics(candidate_id, oracle_id, candidates[candidate_id][1], oracle[oracle_id][1]) for candidate_id, oracle_id in pairs]
    summary = _summary(metrics)
    accepted = _passes(summary) and len(metrics) == 22

    overlay = _oracle_overlay(source_rgba, pairs, candidates, oracle)
    residual = _residual_image(pairs, candidates, oracle)
    Image.fromarray(overlay).save(candidate_root / "stage-2-oracle-overlay.png", format="PNG", optimize=False, compress_level=9)
    Image.fromarray(residual).save(candidate_root / "stage-2-residual.png", format="PNG", optimize=False, compress_level=9)
    Image.fromarray(_review_image(auto_rgba, overlay)).save(candidate_root / "stage-2-review.png", format="PNG", optimize=False, compress_level=9)

    acceptance = {
        "accepted": accepted,
        "artifacts": {
            "candidateEvidence": "stage-2-candidates.png",
            "labels": "stage-2-labels.png",
            "oracleOverlay": "stage-2-oracle-overlay.png",
            "orderedRegions": "stage-2-auto-regions.json",
            "residual": "stage-2-residual.png",
            "review": "stage-2-review.png",
            "trace": "stage-2-auto-regions-labeled.png",
        },
        "candidateHashes": hashes["files"],
        "generationEvidence": generation,
        "metrics": summary,
        "pairing": [{"candidateId": c, "oracleId": o} for c, o in pairs],
        "regions": metrics,
        "schemaVersion": 1,
        "stage": 2,
        "thresholds": {key: {"operator": value[0], "value": value[1]} for key, value in _THRESHOLDS.items()},
    }
    _write_json(candidate_root / "stage-2-acceptance.json", acceptance)
    if not accepted:
        raise ValueError(f"Stage 2 candidate does not meet acceptance thresholds: {summary}")
    return acceptance


def _verify_candidate_hashes(root: Path, document: object) -> None:
    if not isinstance(document, dict) or set(document) != {"files", "schemaVersion"} or document["schemaVersion"] != 1:
        raise ValueError("invalid Stage 2 candidate hash manifest")
    files = document["files"]
    if not isinstance(files, dict) or set(files) != _CANDIDATE_ARTIFACT_NAMES:
        raise ValueError("invalid Stage 2 candidate hash manifest")
    for name, expected in files.items():
        if not isinstance(expected, str) or len(expected) != 64:
            raise ValueError("invalid Stage 2 candidate hash manifest")
        path = root / name
        if not path.is_file() or sha256(path.read_bytes()).hexdigest() != expected:
            raise ValueError(f"serialized Stage 2 candidate was changed: {name}")


def _load_candidate_image(
    path: Path, *, mode: str, shape: tuple[int, int] | None = None,
) -> np.ndarray:
    try:
        with Image.open(path) as image:
            if image.format != "PNG" or image.mode != mode:
                raise ValueError(f"invalid serialized Stage 2 image: {path.name}")
            value = np.asarray(image).copy()
    except OSError as error:
        raise ValueError(f"invalid serialized Stage 2 image: {path.name}") from error
    if shape is not None and value.shape[:2] != shape:
        raise ValueError(f"serialized Stage 2 image dimensions mismatch: {path.name}")
    return value


def _load_label_raster(path: Path, shape: tuple[int, int]) -> np.ndarray:
    try:
        with Image.open(path) as image:
            if image.format != "PNG" or image.mode != "I;16" or image.size != (shape[1], shape[0]):
                raise ValueError("invalid serialized Stage 2 16-bit label raster")
            labels = np.asarray(image).astype(np.uint16)
    except OSError as error:
        raise ValueError("invalid serialized Stage 2 16-bit label raster") from error
    return labels


def _validate_generation_evidence(
    document: object, *, source_pixel_sha256: str, response_sha256: str,
) -> None:
    expected_fields = {
        "candidateIdentity", "profile", "provider", "schemaVersion",
        "stage1AcceptanceRawSha256", "stage1AcceptancePolicyId",
        "stage1ChainSha256", "stage1PixelSha256",
    }
    if (
        not isinstance(document, dict)
        or set(document) != expected_fields
        or type(document.get("schemaVersion")) is not int
        or document.get("schemaVersion") != 1
        or document.get("profile") != "generic-local-contrast-seams-v1"
        or document.get("stage1AcceptancePolicyId") != "beastmaker-1000-tulipwood-stage1-v3"
    ):
        raise ValueError("invalid Stage 2 generation evidence")
    for field in (
        "candidateIdentity", "stage1AcceptanceRawSha256", "stage1ChainSha256",
        "stage1PixelSha256",
    ):
        if not isinstance(document[field], str) or not re.fullmatch(r"[0-9a-f]{64}", document[field]):
            raise ValueError("invalid Stage 2 generation evidence")
    provider = document.get("provider")
    if not isinstance(provider, dict) or set(provider) != {
        "id", "inputPixelSha256", "model", "promptId", "promptSha256",
        "responseSha256",
    }:
        raise ValueError("invalid Stage 2 provider generation evidence")
    if (
        provider["promptId"] != SEMANTIC_PROMPT_ID
        or provider["promptSha256"] != SEMANTIC_PROMPT_SHA256
        or provider["responseSha256"] != response_sha256
        or provider["inputPixelSha256"] != source_pixel_sha256
        or document["stage1PixelSha256"] != source_pixel_sha256
    ):
        raise ValueError("Stage 2 generation evidence identity mismatch")


def _candidate_masks(
    document: object, shape: tuple[int, int], *, labels: np.ndarray,
    source_pixel_sha256: str,
) -> dict[str, tuple[str, np.ndarray]]:
    expected_root = {
        "candidatePixelSha256", "height", "regions", "schemaVersion", "stage", "width",
    }
    if (
        not isinstance(document, dict)
        or set(document) != expected_root
        or type(document.get("schemaVersion")) is not int
        or document.get("schemaVersion") != 1
        or type(document.get("stage")) is not int
        or document.get("stage") != 2
        or type(document.get("height")) is not int
        or type(document.get("width")) is not int
        or (document.get("height"), document.get("width")) != shape
        or document.get("candidatePixelSha256") != source_pixel_sha256
    ):
        raise ValueError("invalid serialized Stage 2 regions")
    raw_regions = document.get("regions")
    if not isinstance(raw_regions, list) or len(raw_regions) != 22:
        raise ValueError("invalid serialized Stage 2 region count")
    result: dict[str, tuple[str, np.ndarray]] = {}
    reconstructed = np.zeros(shape, dtype=np.uint16)
    occupied = np.zeros(shape, dtype=bool)
    expected_region_fields = {
        "anchorCell", "areaPixels", "bbox", "center", "contour", "id",
        "maskRle", "maskSha256", "pieceIndex", "provenance", "row", "type",
        "visualMode",
    }
    for index, item in enumerate(raw_regions, start=1):
        if (
            not isinstance(item, dict)
            or set(item) != expected_region_fields
            or not isinstance(item.get("id"), str)
            or not re.fullmatch(r"piece-[0-9]{2}-hold-[0-9]{2}", item["id"])
            or item.get("type") not in {"pocket", "jug", "sloper"}
            or item.get("visualMode") not in {"aperture", "surface"}
            or (item["type"] == "pocket") != (item["visualMode"] == "aperture")
            or type(item.get("pieceIndex")) is not int
            or type(item.get("row")) is not int
            or not isinstance(item.get("provenance"), dict)
        ):
            raise ValueError("invalid serialized Stage 2 region")
        anchor = item.get("anchorCell")
        if (
            not isinstance(anchor, list) or len(anchor) != 2
            or any(type(value) is not int for value in anchor)
            or not (0 <= anchor[0] < 20 and 0 <= anchor[1] < 8)
        ):
            raise ValueError("invalid serialized Stage 2 region")
        mask = decode_mask_rle(item["maskRle"], shape)
        if np.any(mask.astype(bool) & occupied):
            raise ValueError("serialized Stage 2 region masks overlap")
        occupied |= mask.astype(bool)
        contour, center, bbox, area = _mask_geometry(mask)
        expected_metadata = (
            item.get("areaPixels") == area
            and item.get("bbox") == list(bbox)
            and item.get("center") == [round(center[0], 6), round(center[1], 6)]
            and item.get("contour") == [list(point) for point in contour]
            and item.get("maskSha256") == sha256(mask.astype(np.uint8).tobytes()).hexdigest()
        )
        if not expected_metadata:
            raise ValueError("serialized Stage 2 region metadata does not match mask geometry")
        reconstructed[mask.astype(bool)] = index
        result[item["id"]] = (item["type"], mask)
    if len(result) != len(raw_regions):
        raise ValueError("duplicate serialized Stage 2 region ID")
    if not np.array_equal(labels, reconstructed):
        raise ValueError("Stage 2 label raster does not match ordered region masks")
    return result


def _oracle_masks(paths: Mapping[str, str], width: int, height: int) -> dict[str, tuple[str, np.ndarray]]:
    from .display_paths import flatten_display_path, parse_display_path
    result: dict[str, tuple[str, np.ndarray]] = {}
    for identifier, data in paths.items():
        grip_type = "pocket" if identifier.startswith("pocket-") else "jug" if identifier.startswith("jug-") else "sloper"
        parsed = parse_display_path(data, identifier, width, height, allow_linear_segments=True)
        if parsed is None:
            raise ValueError("oracle path is missing")
        contour = np.rint(flatten_display_path(parsed, curve_steps=64)).astype(np.int32)
        mask = np.zeros((height, width), dtype=np.uint8)
        cv2.fillPoly(mask, [contour], 1)
        result[identifier] = (grip_type, mask)
    return result


def _pair_by_type(
    candidates: Mapping[str, tuple[str, np.ndarray]], oracle: Mapping[str, tuple[str, np.ndarray]]
) -> tuple[tuple[str, str], ...]:
    pairs: list[tuple[str, str]] = []
    for grip_type in ("jug", "sloper", "pocket"):
        candidate_ids = sorted(identifier for identifier, value in candidates.items() if value[0] == grip_type)
        oracle_ids = sorted(identifier for identifier, value in oracle.items() if value[0] == grip_type)
        if len(candidate_ids) != len(oracle_ids):
            raise ValueError(f"Stage 2 {grip_type} topology does not match oracle")
        costs = np.asarray(
            [[_pair_cost(candidates[c][1], oracle[o][1]) for o in oracle_ids] for c in candidate_ids], dtype=np.float64
        )
        assignment = _minimum_assignment(costs)
        pairs.extend((candidate_ids[row], oracle_ids[column]) for row, column in enumerate(assignment))
    return tuple(pairs)


def _pair_cost(first: np.ndarray, second: np.ndarray) -> float:
    c1, c2 = _centroid(first), _centroid(second)
    distance = float(np.hypot(c1[0] - c2[0], c1[1] - c2[1]))
    area_delta = abs(int(np.count_nonzero(first)) - int(np.count_nonzero(second))) / max(1, int(np.count_nonzero(second)))
    return distance + area_delta * 25


def _minimum_assignment(cost: np.ndarray) -> tuple[int, ...]:
    """Hungarian minimum assignment with deterministic column tie-breaking."""
    n = cost.shape[0]
    if cost.shape != (n, n):
        raise ValueError("assignment matrix must be square")
    u = np.zeros(n + 1); v = np.zeros(n + 1); p = np.zeros(n + 1, dtype=int); way = np.zeros(n + 1, dtype=int)
    for i in range(1, n + 1):
        p[0] = i; j0 = 0; minimum = np.full(n + 1, np.inf); used = np.zeros(n + 1, dtype=bool)
        while True:
            used[j0] = True; i0 = p[j0]; delta = np.inf; j1 = 0
            for j in range(1, n + 1):
                if used[j]: continue
                current = cost[i0 - 1, j - 1] - u[i0] - v[j]
                if current < minimum[j]: minimum[j], way[j] = current, j0
                if minimum[j] < delta: delta, j1 = minimum[j], j
            for j in range(n + 1):
                if used[j]: u[p[j]] += delta; v[j] -= delta
                else: minimum[j] -= delta
            j0 = j1
            if p[j0] == 0: break
        while True:
            j1 = way[j0]; p[j0] = p[j1]; j0 = j1
            if j0 == 0: break
    assignment = np.empty(n, dtype=int)
    for j in range(1, n + 1): assignment[p[j] - 1] = j - 1
    return tuple(int(value) for value in assignment)


def _region_metrics(candidate_id: str, oracle_id: str, candidate: np.ndarray, oracle: np.ndarray) -> dict[str, object]:
    intersection = int(np.count_nonzero(candidate & oracle)); union = int(np.count_nonzero(candidate | oracle))
    iou = intersection / union if union else 1.0
    cb, ob = _boundary(candidate), _boundary(oracle)
    kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (7, 7))
    precision = np.count_nonzero(cb & (cv2.dilate(ob, kernel) > 0)) / max(1, np.count_nonzero(cb))
    recall = np.count_nonzero(ob & (cv2.dilate(cb, kernel) > 0)) / max(1, np.count_nonzero(ob))
    boundary_f = 2 * precision * recall / (precision + recall) if precision + recall else 0.0
    cc, oc = _centroid(candidate), _centroid(oracle)
    centroid = float(np.hypot(cc[0] - oc[0], cc[1] - oc[1]))
    return {
        "boundaryFScore": boundary_f, "candidateId": candidate_id,
        "centroidDisplacementPx": centroid, "hd95Px": _hd95(cb, ob),
        "intersectionPixels": intersection, "iou": iou, "oracleId": oracle_id,
        "unionPixels": union,
    }


def _summary(regions: list[dict[str, object]]) -> dict[str, float]:
    ious = np.asarray([item["iou"] for item in regions], dtype=float)
    boundaries = np.asarray([item["boundaryFScore"] for item in regions], dtype=float)
    centroids = np.asarray([item["centroidDisplacementPx"] for item in regions], dtype=float)
    hd95 = np.asarray([item["hd95Px"] for item in regions], dtype=float)
    return {
        "maximumCentroidDisplacementPx": float(centroids.max()),
        "maximumHd95Px": float(hd95.max()),
        "medianBoundaryFScore": float(np.median(boundaries)),
        "medianCentroidDisplacementPx": float(np.median(centroids)),
        "medianRegionIou": float(np.median(ious)),
        "microIou": _micro_iou(regions),
        "minimumBoundaryFScore": float(boundaries.min()),
        "minimumRegionIou": float(ious.min()),
    }


def _micro_iou(regions: list[dict[str, object]]) -> float:
    intersection = sum(int(item["intersectionPixels"]) for item in regions)
    union = sum(int(item["unionPixels"]) for item in regions)
    return intersection / union if union else 1.0


def _passes(summary: Mapping[str, float]) -> bool:
    return all(summary[key] >= threshold if op == ">=" else summary[key] <= threshold for key, (op, threshold) in _THRESHOLDS.items())


def _boundary(mask: np.ndarray) -> np.ndarray:
    eroded = cv2.erode(
        mask.astype(np.uint8), np.ones((3, 3), np.uint8),
        borderType=cv2.BORDER_CONSTANT, borderValue=0,
    )
    return (mask.astype(bool) & ~(eroded > 0)).astype(np.uint8)


def _centroid(mask: np.ndarray) -> tuple[float, float]:
    moments = cv2.moments(mask.astype(np.uint8), binaryImage=True)
    if not moments["m00"]: return (0.0, 0.0)
    return (moments["m10"] / moments["m00"], moments["m01"] / moments["m00"])


def _hd95(first: np.ndarray, second: np.ndarray) -> float:
    if not np.any(first) or not np.any(second): return float("inf")
    d_second = cv2.distanceTransform((~second.astype(bool)).astype(np.uint8), cv2.DIST_L2, 5)
    d_first = cv2.distanceTransform((~first.astype(bool)).astype(np.uint8), cv2.DIST_L2, 5)
    return float(np.percentile(np.concatenate((d_second[first.astype(bool)], d_first[second.astype(bool)])), 95))


def _oracle_overlay(rgba: np.ndarray, pairs: tuple[tuple[str, str], ...], candidates: Mapping[str, tuple[str, np.ndarray]], oracle: Mapping[str, tuple[str, np.ndarray]]) -> np.ndarray:
    base = rgba[..., :3].copy(); base[rgba[..., 3] < 128] = 245
    result = (base.astype(np.float32) * 0.38).astype(np.uint8)
    combined_candidate = np.zeros(rgba.shape[:2], dtype=np.uint8); combined_oracle = np.zeros_like(combined_candidate)
    for candidate_id, oracle_id in pairs: combined_candidate |= candidates[candidate_id][1]; combined_oracle |= oracle[oracle_id][1]
    result[(combined_candidate > 0) & (combined_oracle > 0)] = (58, 190, 94)
    result[(combined_candidate > 0) & (combined_oracle == 0)] = (224, 48, 168)
    result[(combined_candidate == 0) & (combined_oracle > 0)] = (244, 205, 54)
    result[_boundary(combined_candidate).astype(bool)] = (25, 230, 240)
    result[_boundary(combined_oracle).astype(bool)] = (255, 255, 255)
    return result


def _residual_image(pairs: tuple[tuple[str, str], ...], candidates: Mapping[str, tuple[str, np.ndarray]], oracle: Mapping[str, tuple[str, np.ndarray]]) -> np.ndarray:
    result = np.zeros((*next(iter(candidates.values()))[1].shape, 3), dtype=np.uint8)
    for candidate_id, oracle_id in pairs:
        candidate, accepted = candidates[candidate_id][1], oracle[oracle_id][1]
        result[(candidate > 0) & (accepted == 0)] = (224, 48, 168)
        result[(candidate == 0) & (accepted > 0)] = (244, 205, 54)
    return result


def _review_image(candidate: np.ndarray, overlay: np.ndarray) -> np.ndarray:
    gap, top = 32, 52; height, width = candidate.shape[:2]
    canvas = Image.new("RGB", (width * 2 + gap * 3, height + top + 24), (248, 247, 244)); draw = ImageDraw.Draw(canvas); font = ImageFont.load_default()
    canvas.paste(Image.fromarray(candidate), (gap, top)); canvas.paste(Image.fromarray(overlay), (width + gap * 2, top))
    draw.text((gap, 18), "IMAGE-DERIVED AUTOMATED TRACE - 22 REGIONS", fill=(28, 28, 28), font=font)
    draw.text((width + gap * 2, 12), "ORACLE COMPARISON - green overlap / magenta over / yellow missed", fill=(28, 28, 28), font=font)
    draw.text((width + gap * 2, 28), "cyan candidate boundary / white oracle boundary", fill=(28, 28, 28), font=font)
    return np.asarray(canvas)


def _write_json(path: Path, document: Mapping[str, object]) -> None:
    path.write_text(json.dumps(document, indent=2, sort_keys=True) + "\n", encoding="utf-8")
