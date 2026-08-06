"""Image-derived Stage 2 discovery and stable hold topology."""

from __future__ import annotations

from dataclasses import dataclass
from hashlib import sha256
import json
from typing import TypeAlias

import cv2
import numpy as np

from .hold_refinement import (
    HoldDiscoveryProfile, assign_aperture_candidates, generate_aperture_candidates,
    multiscale_local_contrast, refine_aperture, trace_surface_masks,
)
from .semantic_holds import (
    CoarseHoldHint, PieceDescriptor, SemanticGripProvider, SemanticGripRequest,
    SemanticGripResponse, validate_semantic_grip_response,
)
from .simplification import SimplifiedRaster


Point: TypeAlias = tuple[int, int]


def _freeze(mask: np.ndarray, dtype: np.dtype | type[np.generic] = np.uint8) -> np.ndarray:
    value = np.asarray(mask, dtype=dtype)
    return np.frombuffer(value.tobytes(), dtype=value.dtype).reshape(value.shape)


@dataclass(frozen=True, slots=True)
class DetectedHold:
    id: str
    hint_key: str
    piece_index: int
    grip_type: str
    visual_mode: str
    anchor: tuple[int, int]
    row: int
    mask: np.ndarray
    contour: tuple[Point, ...]
    center: tuple[float, float]
    bbox: tuple[int, int, int, int]
    area: int
    provenance: tuple[tuple[str, float | str], ...]

    def __post_init__(self) -> None:
        object.__setattr__(self, "mask", _freeze(self.mask))

    def as_document(self) -> dict[str, object]:
        return {
            "anchorCell": list(self.anchor),
            "areaPixels": self.area,
            "bbox": list(self.bbox),
            "center": [round(self.center[0], 6), round(self.center[1], 6)],
            "contour": [list(point) for point in self.contour],
            "id": self.id,
            "maskSha256": sha256(self.mask.astype(np.uint8).tobytes()).hexdigest(),
            "maskRle": _mask_rle(self.mask),
            "pieceIndex": self.piece_index,
            "provenance": {key: value for key, value in self.provenance},
            "row": self.row,
            "type": self.grip_type,
            "visualMode": self.visual_mode,
        }


@dataclass(frozen=True, slots=True)
class HoldDiscovery:
    holds: tuple[DetectedHold, ...]
    label_raster: np.ndarray
    candidate_evidence_rgb: np.ndarray
    provider_response: SemanticGripResponse
    pixel_sha256: str

    def __post_init__(self) -> None:
        object.__setattr__(self, "label_raster", _freeze(self.label_raster, np.uint16))
        object.__setattr__(self, "candidate_evidence_rgb", _freeze(self.candidate_evidence_rgb))

    def regions_document(self) -> dict[str, object]:
        return {
            "candidatePixelSha256": self.pixel_sha256,
            "height": int(self.label_raster.shape[0]),
            "regions": [hold.as_document() for hold in self.holds],
            "schemaVersion": 1,
            "stage": 2,
            "width": int(self.label_raster.shape[1]),
        }


DiscoveredHoldLayout = HoldDiscovery


def discover_holds(
    raster: SimplifiedRaster,
    *,
    pieces: tuple[PieceDescriptor, ...],
    provider: SemanticGripProvider,
    profile: HoldDiscoveryProfile,
) -> HoldDiscovery:
    """Discover logical holds using semantic anchors followed only by pixels."""
    rgba = raster.rgba
    if rgba.ndim != 3 or rgba.shape[2] != 4 or rgba.dtype != np.uint8:
        raise ValueError("hold discovery requires a Stage 1 RGBA raster")
    request = SemanticGripRequest(rgba, pieces, _product_id(pieces))
    response = validate_semantic_grip_response(
        provider.propose(request), piece_count=len(pieces)
    )
    if response.input_pixel_sha256 != request.pixel_sha256:
        raise ValueError("semantic provider response belongs to different pixels")
    hints = response.inventory.hints
    if any(hint.piece_index >= len(pieces) for hint in hints):
        raise ValueError("semantic response references unavailable piece metadata")

    piece_masks = _piece_masks(rgba[..., 3], len(pieces))
    height, width = rgba.shape[:2]
    anchors = {hint.hint_key: _anchor_point(hint, width, height, profile) for hint in hints}
    gray = cv2.cvtColor(rgba[..., :3], cv2.COLOR_RGB2GRAY)
    contrast = multiscale_local_contrast(rgba[..., :3], profile)
    refined: dict[str, tuple[np.ndarray, tuple[tuple[str, float], ...]]] = {}

    for piece_index, piece_mask in enumerate(piece_masks):
        apertures = tuple(hint for hint in hints if hint.piece_index == piece_index and hint.visual_mode == "aperture")
        surfaces = tuple(hint for hint in hints if hint.piece_index == piece_index and hint.visual_mode == "surface")
        surface_refined = trace_surface_masks(
            surfaces, anchor_points=anchors, piece_mask=piece_mask,
            rgb=rgba[..., :3], profile=profile,
        )
        for key, value in surface_refined.items():
            refined[key] = (value.mask, value.evidence)
        candidates = (
            generate_aperture_candidates(
                piece_mask=piece_mask, contrast=contrast, gray=gray, profile=profile
            )
            if apertures else ()
        )
        supports = {
            hint.hint_key: _voronoi_support(
                hint, apertures, anchors, piece_mask,
                profile.aperture_support_expansion_px,
            )
            for hint in apertures
        }
        assignments = assign_aperture_candidates(
            apertures, candidates=candidates, anchor_points=anchors,
            support_masks=supports, piece_mask=piece_mask, profile=profile,
        )
        for hint in apertures:
            value = refine_aperture(
                hint,
                candidate=assignments[hint.hint_key],
                piece_mask=piece_mask,
                support_mask=supports[hint.hint_key],
                exclusion_masks=tuple(
                    value.mask for value in surface_refined.values()
                ),
                gray=gray,
                profile=profile,
            )
            refined[hint.hint_key] = (value.mask, value.evidence)
    ordered_hints = _stable_hint_order(hints)
    _validate_raw_refined_masks(hints, refined, piece_masks)
    occupied = np.zeros((height, width), dtype=np.uint8)
    holds: list[DetectedHold] = []
    piece_numbers: dict[int, int] = {}
    for row, hint in ordered_hints:
        piece_numbers[hint.piece_index] = piece_numbers.get(hint.piece_index, 0) + 1
        number = piece_numbers[hint.piece_index]
        raw_mask, evidence = refined[hint.hint_key]
        mask = raw_mask.astype(np.uint8).copy()
        # Raw geometry has already been validated. The only permitted overlap
        # is a pixel that is a one-pixel boundary in both masks; stable order
        # gives those explicitly shared raster-edge pixels one label owner.
        mask[occupied.astype(bool)] = 0
        occupied |= mask
        contour, center, bbox, area = _mask_geometry(mask)
        holds.append(
            DetectedHold(
                id=f"piece-{hint.piece_index + 1:02d}-hold-{number:02d}",
                hint_key=hint.hint_key,
                piece_index=hint.piece_index,
                grip_type=hint.grip_type,
                visual_mode=hint.visual_mode,
                anchor=hint.anchor,
                row=row,
                mask=mask,
                contour=contour,
                center=center,
                bbox=bbox,
                area=area,
                provenance=(("method", "local-contrast" if hint.visual_mode == "aperture" else "gradient-seam"), *evidence),
            )
        )
    labels = np.zeros((height, width), dtype=np.uint16)
    for index, hold in enumerate(holds, start=1):
        labels[hold.mask.astype(bool)] = index
    evidence_rgb = _candidate_evidence(contrast, gray, rgba[..., 3])
    return HoldDiscovery(tuple(holds), labels, evidence_rgb, response, request.pixel_sha256)


def _validate_raw_refined_masks(
    hints: tuple[CoarseHoldHint, ...],
    refined: dict[str, tuple[np.ndarray, tuple[tuple[str, float], ...]]],
    piece_masks: tuple[np.ndarray, ...],
) -> None:
    """Reject invalid tracer geometry before any boundary ownership is assigned."""
    validated: list[tuple[CoarseHoldHint, np.ndarray, np.ndarray]] = []
    for hint in hints:
        if hint.hint_key not in refined:
            raise ValueError(f"semantic hint has no refined mask: {hint.hint_key}")
        mask = np.asarray(refined[hint.hint_key][0])
        piece = piece_masks[hint.piece_index].astype(bool)
        if mask.shape != piece.shape or mask.ndim != 2:
            raise ValueError("raw refined mask dimensions mismatch")
        if not np.all((mask == 0) | (mask == 1)):
            raise ValueError("raw refined mask must be binary")
        selected = mask.astype(bool)
        if not np.any(selected):
            raise ValueError("raw refined mask is empty")
        if np.any(selected & ~piece):
            raise ValueError("raw refined mask extends outside its Stage 1 silhouette")
        interior = cv2.erode(
            selected.astype(np.uint8), np.ones((3, 3), np.uint8),
            borderType=cv2.BORDER_CONSTANT, borderValue=0,
        ).astype(bool)
        validated.append((hint, selected, interior))
    for index, (first_hint, first, first_interior) in enumerate(validated):
        for second_hint, second, second_interior in validated[index + 1 :]:
            if first_hint.piece_index != second_hint.piece_index:
                continue
            overlap = first & second
            if np.any(overlap & (first_interior | second_interior)):
                raise ValueError(
                    "raw refined masks have overlapping interiors: "
                    f"{first_hint.hint_key}/{second_hint.hint_key}"
                )


def _product_id(pieces: tuple[PieceDescriptor, ...]) -> str:
    if not pieces:
        raise ValueError("hold discovery requires at least one piece")
    return pieces[0].id


def _anchor_point(hint: CoarseHoldHint, width: int, height: int, profile: HoldDiscoveryProfile) -> tuple[float, float]:
    return ((hint.anchor[0] + 0.5) * width / profile.grid_width, (hint.anchor[1] + 0.5) * height / profile.grid_height)


def _piece_masks(alpha: np.ndarray, piece_count: int) -> tuple[np.ndarray, ...]:
    binary = (alpha >= 128).astype(np.uint8)
    count, labels, stats, centroids = cv2.connectedComponentsWithStats(binary)
    components = [index for index in range(1, count) if stats[index, cv2.CC_STAT_AREA] >= max(16, binary.size // 1000)]
    components.sort(key=lambda index: (centroids[index][0], centroids[index][1], index))
    if len(components) != piece_count:
        raise ValueError("Stage 1 silhouette does not match piece metadata")
    return tuple((labels == index).astype(np.uint8) for index in components)


def _voronoi_support(
    target: CoarseHoldHint,
    hints: tuple[CoarseHoldHint, ...],
    anchors: dict[str, tuple[float, float]],
    piece_mask: np.ndarray,
    expansion: int,
) -> np.ndarray:
    yy, xx = np.indices(piece_mask.shape)
    tx, ty = anchors[target.hint_key]
    target_distance = (xx - tx) ** 2 + (yy - ty) ** 2
    support = piece_mask.astype(bool)
    for hint in hints:
        if hint.hint_key == target.hint_key or hint.anchor[1] != target.anchor[1]:
            continue
        ox, oy = anchors[hint.hint_key]
        other = (xx - ox) ** 2 + (yy - oy) ** 2
        support &= target_distance <= other
    if expansion:
        support = cv2.dilate(support.astype(np.uint8), cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (expansion * 2 + 1, expansion * 2 + 1))) > 0
    return (support & piece_mask.astype(bool)).astype(np.uint8)


def _stable_hint_order(hints: tuple[CoarseHoldHint, ...]) -> tuple[tuple[int, CoarseHoldHint], ...]:
    rows: list[list[CoarseHoldHint]] = []
    for hint in sorted(hints, key=lambda value: (value.piece_index, value.anchor[1], value.anchor[0], value.hint_key)):
        if not rows or rows[-1][0].piece_index != hint.piece_index or hint.anchor[1] != rows[-1][0].anchor[1]:
            rows.append([hint])
        else:
            rows[-1].append(hint)
    ordered: list[tuple[int, CoarseHoldHint]] = []
    piece_rows: dict[int, int] = {}
    for row in rows:
        piece = row[0].piece_index
        piece_rows[piece] = piece_rows.get(piece, 0) + 1
        ordered.extend((piece_rows[piece], hint) for hint in sorted(row, key=lambda value: (value.anchor[0], value.hint_key)))
    return tuple(ordered)


def _mask_geometry(mask: np.ndarray) -> tuple[tuple[Point, ...], tuple[float, float], tuple[int, int, int, int], int]:
    if not np.any(mask):
        raise ValueError("discovered hold is empty")
    count, _ = cv2.connectedComponents(mask.astype(np.uint8))
    if count != 2:
        raise ValueError("one semantic hint must produce one connected region")
    contours, _ = cv2.findContours(mask.astype(np.uint8), cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    contour = max(contours, key=cv2.contourArea)
    epsilon = max(0.75, cv2.arcLength(contour, True) * 0.0015)
    contour = cv2.approxPolyDP(contour, epsilon, True).reshape(-1, 2)
    x, y, width, height = cv2.boundingRect(contour)
    moments = cv2.moments(mask.astype(np.uint8), binaryImage=True)
    center = (float(moments["m10"] / moments["m00"]), float(moments["m01"] / moments["m00"]))
    return tuple((int(px), int(py)) for px, py in contour), center, (x, y, width, height), int(np.count_nonzero(mask))


def _mask_rle(mask: np.ndarray) -> list[int]:
    flat = mask.astype(np.uint8).ravel()
    runs: list[int] = []
    current, length = 0, 0
    for value in flat:
        bit = int(value != 0)
        if bit == current:
            length += 1
        else:
            runs.append(length)
            current, length = bit, 1
    runs.append(length)
    return runs


def decode_mask_rle(runs: list[int], shape: tuple[int, int]) -> np.ndarray:
    values: list[np.ndarray] = []
    bit = 0
    for length in runs:
        if type(length) is not int or length < 0:
            raise ValueError("invalid candidate mask RLE")
        values.append(np.full(length, bit, dtype=np.uint8))
        bit ^= 1
    flat = np.concatenate(values) if values else np.empty(0, dtype=np.uint8)
    if flat.size != shape[0] * shape[1]:
        raise ValueError("candidate mask RLE size mismatch")
    return flat.reshape(shape)


def _candidate_evidence(contrast: np.ndarray, gray: np.ndarray, alpha: np.ndarray) -> np.ndarray:
    scaled = np.clip(contrast * 5, 0, 255).astype(np.uint8)
    gradient = np.clip(cv2.magnitude(cv2.Sobel(gray, cv2.CV_32F, 1, 0), cv2.Sobel(gray, cv2.CV_32F, 0, 1)), 0, 255).astype(np.uint8)
    result = np.dstack((gradient, scaled, gray))
    result[alpha < 128] = 0
    return result


def discovery_identity(discovery: HoldDiscovery) -> str:
    document = discovery.regions_document()
    payload = json.dumps(document, sort_keys=True, separators=(",", ":")).encode()
    return sha256(payload + discovery.label_raster.tobytes() + discovery.candidate_evidence_rgb.tobytes()).hexdigest()
