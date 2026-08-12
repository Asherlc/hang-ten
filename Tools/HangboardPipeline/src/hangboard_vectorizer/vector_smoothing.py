"""Mask-derived mixed-corner vectorization with scale-relative tolerances."""

from __future__ import annotations

from dataclasses import dataclass
from hashlib import sha256
import math
from typing import Literal, TypeAlias

import cv2
import numpy as np

from .display_paths import DisplayPath, flatten_display_path, parse_display_path


RegionType: TypeAlias = Literal["pocket", "jug", "sloper"]
PrimitiveType: TypeAlias = Literal["rounded-mouth", "feature-spline"]
Point: TypeAlias = tuple[float, float]


def _frozen(value: np.ndarray, dtype: np.dtype | type[np.generic]) -> np.ndarray:
    array = np.asarray(value, dtype=dtype)
    return np.frombuffer(array.tobytes(), dtype=array.dtype).reshape(array.shape)


@dataclass(frozen=True, slots=True)
class Stage2MaskRegion:
    id: str
    piece_index: int
    grip_type: RegionType
    visual_mode: Literal["aperture", "surface"]
    row: int
    mask: np.ndarray
    raw_mask_sha256: str = ""

    def __post_init__(self) -> None:
        if not self.id or type(self.piece_index) is not int or self.piece_index < 0:
            raise ValueError("Stage 2 region identity is invalid")
        if self.grip_type not in {"pocket", "jug", "sloper"}:
            raise ValueError("Stage 2 region type is invalid")
        if self.visual_mode not in {"aperture", "surface"} or (
            (self.grip_type == "pocket") != (self.visual_mode == "aperture")
        ):
            raise ValueError("Stage 2 region visual mode is invalid")
        mask = np.asarray(self.mask)
        if mask.ndim != 2 or not np.all((mask == 0) | (mask == 1)) or not np.any(mask):
            raise ValueError("Stage 2 region mask must be a nonempty binary raster")
        count, _ = cv2.connectedComponents(mask.astype(np.uint8))
        if count != 2:
            raise ValueError("Stage 2 region mask must contain one connected component")
        frozen = _frozen(mask, np.uint8)
        digest = sha256(frozen.tobytes()).hexdigest()
        if self.raw_mask_sha256 and self.raw_mask_sha256 != digest:
            raise ValueError("Stage 2 region raw mask hash mismatch")
        object.__setattr__(self, "mask", frozen)
        object.__setattr__(self, "raw_mask_sha256", digest)


@dataclass(frozen=True, slots=True)
class VectorizationProfile:
    profile_id: str = "scale-relative-mixed-corner-v1"
    supersample: int = 4
    contour_epsilon_fraction: float = 0.012
    persistent_corner_turn_degrees: float = 34.0
    persistence_distance_fraction: float = 0.035
    rounded_residual_iou: float = 0.95
    rounded_max_concavity_fraction: float = 0.025
    rounded_max_concavity_depth_fraction: float = 0.10
    rounded_centroid_fraction: float = 0.025
    rounded_hd95_fraction: float = 0.06
    local_iou_floor: float = 0.95
    local_centroid_fraction: float = 0.02
    local_hd95_fraction: float = 0.05
    line_residual_fraction: float = 0.008
    curve_error_fraction: float = 0.018
    validity_flatten_fraction: float = 0.0025

    def __post_init__(self) -> None:
        if (
            not self.profile_id
            or type(self.supersample) is not int
            or self.supersample < 2
        ):
            raise ValueError("invalid vectorization profile")
        fractions = (
            self.contour_epsilon_fraction,
            self.persistence_distance_fraction,
            self.rounded_max_concavity_fraction,
            self.rounded_max_concavity_depth_fraction,
            self.rounded_centroid_fraction,
            self.rounded_hd95_fraction,
            self.local_centroid_fraction,
            self.local_hd95_fraction,
            self.line_residual_fraction,
            self.curve_error_fraction,
            self.validity_flatten_fraction,
        )
        if any(not math.isfinite(value) or value <= 0 for value in fractions):
            raise ValueError("vectorization fractions must be positive and finite")
        if not 0 < self.rounded_residual_iou <= 1 or not 0 < self.local_iou_floor <= 1:
            raise ValueError("vectorization IoU thresholds must be in (0, 1]")
        if not 0 < self.persistent_corner_turn_degrees < 180:
            raise ValueError("corner threshold must be between zero and 180 degrees")


@dataclass(frozen=True, slots=True)
class PathSegment:
    command: Literal["L", "C"]
    end: Point
    control_1: Point | None = None
    control_2: Point | None = None

    def __post_init__(self) -> None:
        if self.command == "L" and (
            self.control_1 is not None or self.control_2 is not None
        ):
            raise ValueError("line segment cannot have controls")
        if self.command == "C" and (self.control_1 is None or self.control_2 is None):
            raise ValueError("cubic segment requires two controls")


@dataclass(frozen=True, slots=True)
class OpenPath:
    start: Point
    segments: tuple[PathSegment, ...]

    @property
    def end(self) -> Point:
        return self.segments[-1].end if self.segments else self.start

    @property
    def data(self) -> str:
        return _open_path_data(self)

    def reversed(self) -> "OpenPath":
        current = self.start
        starts: list[Point] = []
        for segment in self.segments:
            starts.append(current)
            current = segment.end
        reversed_segments: list[PathSegment] = []
        for segment, start in zip(
            reversed(self.segments), reversed(starts), strict=True
        ):
            if segment.command == "L":
                reversed_segments.append(PathSegment("L", start))
            else:
                reversed_segments.append(
                    PathSegment("C", start, segment.control_2, segment.control_1)
                )
        return OpenPath(self.end, tuple(reversed_segments))


@dataclass(frozen=True, slots=True)
class CanonicalSeam:
    id: str
    kind: Literal["region", "piece"]
    first_id: str
    second_id: str
    path: OpenPath
    raw_coordinates: tuple[Point, ...]


@dataclass(frozen=True, slots=True)
class VectorizedPiece:
    id: str
    piece_index: int
    display_path: DisplayPath
    raw_mask_sha256: str
    output_mask_sha256: str
    shared_seam_ids: tuple[str, ...] = ()


@dataclass(frozen=True, slots=True)
class VectorizedRegion:
    id: str
    piece_index: int
    grip_type: RegionType
    display_path: DisplayPath
    primitive: PrimitiveType
    raw_mask_sha256: str
    output_mask_sha256: str
    locked_corners: tuple[Point, ...] = ()
    shared_seam_ids: tuple[str, ...] = ()


@dataclass(frozen=True, slots=True)
class VectorizedLayout:
    width: int
    height: int
    pieces: tuple[VectorizedPiece, ...]
    regions: tuple[VectorizedRegion, ...]
    canonical_seams: tuple[CanonicalSeam, ...] = ()


def vectorize_layout(
    rgba: np.ndarray,
    labels: np.ndarray,
    regions: tuple[Stage2MaskRegion, ...],
    *,
    profile: VectorizationProfile,
) -> VectorizedLayout:
    """Vectorize the supplied Stage 2 masks without consulting product geometry."""
    rgba = np.asarray(rgba)
    labels = np.asarray(labels)
    if rgba.dtype != np.uint8 or rgba.ndim != 3 or rgba.shape[2] != 4:
        raise ValueError("vectorization requires an RGBA uint8 raster")
    height, width = rgba.shape[:2]
    if labels.shape != (height, width) or labels.dtype != np.uint16:
        raise ValueError("vectorization labels must be a matching uint16 raster")
    if not regions or len({region.id for region in regions}) != len(regions):
        raise ValueError("vectorization regions must have unique IDs")
    reconstructed = np.zeros((height, width), dtype=np.uint16)
    for index, region in enumerate(regions, start=1):
        if region.mask.shape != (height, width):
            raise ValueError("Stage 2 region dimensions mismatch")
        if np.any(reconstructed[region.mask.astype(bool)]):
            raise ValueError("Stage 2 region masks overlap")
        reconstructed[region.mask.astype(bool)] = index
    if not np.array_equal(reconstructed, labels):
        raise ValueError("Stage 2 labels do not match ordered masks")

    piece_masks = _piece_masks(
        rgba[..., 3], max(region.piece_index for region in regions) + 1
    )
    for region in regions:
        if np.any(
            region.mask.astype(bool) & ~piece_masks[region.piece_index].astype(bool)
        ):
            raise ValueError("Stage 2 region extends outside its piece silhouette")

    seams = _canonical_seams(regions, piece_masks, profile)
    piece_ids = tuple(
        f"piece-{index + 1:02d}-silhouette" for index in range(len(piece_masks))
    )
    seam_ids: dict[str, list[str]] = {
        **{region.id: [] for region in regions},
        **{identifier: [] for identifier in piece_ids},
    }
    for seam in seams:
        seam_ids[seam.first_id].append(seam.id)
        seam_ids[seam.second_id].append(seam.id)

    vectorized_pieces: list[VectorizedPiece] = []
    for piece_index, piece_mask in enumerate(piece_masks):
        identifier = piece_ids[piece_index]
        piece_seams = tuple(
            seam for seam in seams if identifier in {seam.first_id, seam.second_id}
        )
        scale_basis = float(min(_bbox_size(piece_mask)))
        locked = _persistent_corners(
            _remove_collinear(_mask_edge_polygon(piece_mask)), scale_basis, profile
        )
        path = _fit_mask_path(piece_mask, locked, piece_seams, width, height, profile)
        validate_display_path(path, scale_basis=scale_basis, profile=profile)
        output = rasterize_display_path(path, width, height)
        if _iou(piece_mask, output) < 0.98:
            raise ValueError(
                f"piece silhouette vector residual is too large: {identifier}"
            )
        vectorized_pieces.append(
            VectorizedPiece(
                identifier,
                piece_index,
                path,
                sha256(piece_mask.tobytes()).hexdigest(),
                sha256(output.tobytes()).hexdigest(),
                tuple(sorted(seam_ids[identifier])),
            )
        )

    candidates: list[
        tuple[Stage2MaskRegion, DisplayPath, PrimitiveType, tuple[Point, ...]]
    ] = []
    for region in regions:
        piece = piece_masks[region.piece_index]
        region_seams = tuple(
            seam for seam in seams if region.id in {seam.first_id, seam.second_id}
        )
        path, primitive, locked = _vectorize_region(
            region, piece, region_seams, width, height, profile
        )
        validate_display_path(
            path, scale_basis=float(min(_bbox_size(region.mask))), profile=profile
        )
        output = rasterize_display_path(path, width, height)
        if np.any(output.astype(bool) & ~piece.astype(bool)):
            raise ValueError(f"vectorized path leaves piece silhouette: {region.id}")
        candidates.append((region, path, primitive, locked))

    output_masks = rasterize_paths_half_open(
        tuple(value[1] for value in candidates), width, height
    )
    vectorized: list[VectorizedRegion] = []
    for (region, path, primitive, locked), output in zip(
        candidates, output_masks, strict=True
    ):
        faithful = (
            _rounded_faithful(
                region.mask,
                path,
                width,
                height,
                float(min(_bbox_size(region.mask))),
                profile,
            )
            if primitive == "rounded-mouth"
            else _locally_faithful(
                region.mask, output, float(min(_bbox_size(region.mask))), profile
            )
        )
        if not faithful:
            raise ValueError(
                f"joint vectorization changed raw geometry too much: {region.id}"
            )
        vectorized.append(
            VectorizedRegion(
                id=region.id,
                piece_index=region.piece_index,
                grip_type=region.grip_type,
                display_path=path,
                primitive=primitive,
                raw_mask_sha256=region.raw_mask_sha256,
                output_mask_sha256=sha256(output.tobytes()).hexdigest(),
                locked_corners=locked,
                shared_seam_ids=tuple(sorted(seam_ids[region.id])),
            )
        )
    return VectorizedLayout(
        width, height, tuple(vectorized_pieces), tuple(vectorized), seams
    )


def rasterize_display_path(
    path: DisplayPath, width: int, height: int, *, scale: int = 1
) -> np.ndarray:
    """Rasterize an absolute path by sampling the pixel grid at cell centers."""
    if type(scale) is not int or scale < 1:
        raise ValueError("raster scale must be a positive integer")
    # A two-phase grid is sufficient to put every output sample strictly at
    # its pixel center while keeping 4x acceptance rasterization memory bounded.
    sampling = 2
    render_scale = scale * sampling
    contour = flatten_display_path(path, scale=float(render_scale), curve_steps=64)
    high = np.zeros((height * render_scale, width * render_scale), dtype=np.uint8)
    cv2.fillPoly(high, [np.rint(contour).astype(np.int32)], 1)
    # Cell edges lie on integer coordinates; the offset sample is strictly
    # inside one side of every shared edge, avoiding double-owned seam pixels.
    offset = sampling // 2
    return high[offset::sampling, offset::sampling].copy()


def rasterize_paths_half_open(
    paths: tuple[DisplayPath, ...], width: int, height: int, *, scale: int = 1
) -> tuple[np.ndarray, ...]:
    """Rasterize ordered regions with explicit lowest-index boundary ownership."""
    occupied = np.zeros((height * scale, width * scale), dtype=bool)
    result: list[np.ndarray] = []
    for independent in rasterize_paths_independent(paths, width, height, scale=scale):
        mask = independent.copy()
        mask[occupied] = 0
        occupied |= mask.astype(bool)
        result.append(mask)
    return tuple(result)


def rasterize_paths_independent(
    paths: tuple[DisplayPath, ...], width: int, height: int, *, scale: int = 1
) -> tuple[np.ndarray, ...]:
    """Rasterize every path without allowing ownership to hide interior overlap."""
    return tuple(
        rasterize_display_path(path, width, height, scale=scale) for path in paths
    )


def _vectorize_region(
    region: Stage2MaskRegion,
    piece_mask: np.ndarray,
    seams: tuple[CanonicalSeam, ...],
    width: int,
    height: int,
    profile: VectorizationProfile,
) -> tuple[DisplayPath, PrimitiveType, tuple[Point, ...]]:
    raw = region.mask
    scale_basis = float(min(_bbox_size(raw)))
    concavity_area, concavity_depth = _concavity_metrics(raw)
    if (
        region.grip_type == "pocket"
        and concavity_area <= profile.rounded_max_concavity_fraction
        and concavity_depth <= profile.rounded_max_concavity_depth_fraction
    ):
        rounded = _best_rounded_path(raw, width, height, profile)
        if rounded is not None:
            candidate = rasterize_display_path(rounded, width, height)
            if _rounded_faithful(
                raw, rounded, width, height, scale_basis, profile
            ) and not np.any(candidate.astype(bool) & ~piece_mask.astype(bool)):
                return rounded, "rounded-mouth", ()

    polygon = _mask_edge_polygon(raw)
    locked = _persistent_corners(_remove_collinear(polygon), scale_basis, profile)
    for multiplier in (1.0, 0.7, 0.45, 0.25):
        path = _fit_mask_path(
            raw,
            locked,
            seams,
            width,
            height,
            profile,
            epsilon_multiplier=multiplier,
        )
        candidate = rasterize_display_path(path, width, height)
        if _locally_faithful(raw, candidate, scale_basis, profile) and not np.any(
            candidate.astype(bool) & ~piece_mask.astype(bool)
        ):
            return path, "feature-spline", locked
    raise ValueError(f"could not vectorize Stage 2 region faithfully: {region.id}")


def _piece_masks(alpha: np.ndarray, piece_count: int) -> tuple[np.ndarray, ...]:
    binary = (np.asarray(alpha) >= 128).astype(np.uint8)
    count, labels, stats, centroids = cv2.connectedComponentsWithStats(binary)
    area_floor = binary.size / 1000.0
    components = [
        index
        for index in range(1, count)
        if stats[index, cv2.CC_STAT_AREA] >= area_floor
    ]
    components.sort(key=lambda index: (centroids[index][0], centroids[index][1], index))
    if len(components) != piece_count:
        raise ValueError("RGBA silhouette does not match Stage 2 piece indexes")
    return tuple((labels == index).astype(np.uint8) for index in components)


def _mask_edge_polygon(mask: np.ndarray) -> np.ndarray:
    selected = mask.astype(bool)
    edges: dict[tuple[int, int], list[tuple[int, int]]] = {}

    def add(start: tuple[int, int], end: tuple[int, int]) -> None:
        edges.setdefault(start, []).append(end)

    height, width = selected.shape
    for y, x in np.argwhere(selected):
        if y == 0 or not selected[y - 1, x]:
            add((int(x), int(y)), (int(x + 1), int(y)))
        if x == width - 1 or not selected[y, x + 1]:
            add((int(x + 1), int(y)), (int(x + 1), int(y + 1)))
        if y == height - 1 or not selected[y + 1, x]:
            add((int(x + 1), int(y + 1)), (int(x), int(y + 1)))
        if x == 0 or not selected[y, x - 1]:
            add((int(x), int(y + 1)), (int(x), int(y)))
    if not edges:
        raise ValueError("cannot trace an empty mask")
    start = min(edges)
    points = [start]
    current = start
    previous_direction = (1, 0)
    remaining = sum(len(values) for values in edges.values())
    for _ in range(remaining + 1):
        choices = edges.get(current, [])
        if not choices:
            break
        if len(choices) == 1:
            end = choices.pop()
        else:
            end = min(
                choices,
                key=lambda value: _turn_rank(
                    previous_direction, (value[0] - current[0], value[1] - current[1])
                ),
            )
            choices.remove(end)
        direction = (end[0] - current[0], end[1] - current[1])
        previous_direction = direction
        current = end
        points.append(current)
        if current == start:
            break
    if current != start or any(values for values in edges.values()):
        raise ValueError("Stage 2 mask does not have one simple exterior boundary")
    return np.asarray(points[:-1], dtype=np.float64)


def _turn_rank(previous: tuple[int, int], current: tuple[int, int]) -> int:
    directions = ((1, 0), (0, 1), (-1, 0), (0, -1))
    before = directions.index(previous)
    after = directions.index(current)
    return ((after - before) % 4 + 1) % 4


def _remove_collinear(points: np.ndarray) -> np.ndarray:
    keep: list[np.ndarray] = []
    for index, point in enumerate(points):
        previous = points[index - 1]
        following = points[(index + 1) % len(points)]
        if abs(float(_cross_2d(point - previous, following - point))) > 1e-9:
            keep.append(point)
    result = np.asarray(keep, dtype=np.float64)
    if len(result) < 3:
        raise ValueError("mask boundary is degenerate")
    return result


def _simplify_polygon(points: np.ndarray, epsilon: float) -> np.ndarray:
    if epsilon <= 0:
        return points.copy()
    simplified = cv2.approxPolyDP(
        points.astype(np.float32).reshape(-1, 1, 2), epsilon, True
    )
    result = simplified.reshape(-1, 2).astype(np.float64)
    return result if len(result) >= 3 else points.copy()


def _persistent_corners(
    polygon: np.ndarray, scale_basis: float, profile: VectorizationProfile
) -> tuple[Point, ...]:
    fine = _simplify_polygon(polygon, scale_basis * profile.contour_epsilon_fraction)
    coarse = _simplify_polygon(
        polygon, scale_basis * profile.contour_epsilon_fraction * 2.0
    )
    tolerance = scale_basis * profile.persistence_distance_fraction
    corners: list[Point] = []
    for index, point in enumerate(fine):
        previous = fine[index - 1]
        following = fine[(index + 1) % len(fine)]
        first, second = previous - point, following - point
        denominator = float(np.linalg.norm(first) * np.linalg.norm(second))
        if denominator == 0:
            continue
        interior = math.degrees(
            math.acos(float(np.clip(np.dot(first, second) / denominator, -1, 1)))
        )
        turn = 180.0 - interior
        if turn < profile.persistent_corner_turn_degrees:
            continue
        if float(np.min(np.linalg.norm(coarse - point, axis=1))) <= tolerance:
            corners.append((float(point[0]), float(point[1])))
    return tuple(corners)


def _fit_mask_path(
    mask: np.ndarray,
    locked: tuple[Point, ...],
    seams: tuple[CanonicalSeam, ...],
    width: int,
    height: int,
    profile: VectorizationProfile,
    *,
    epsilon_multiplier: float = 1.0,
) -> DisplayPath:
    polygon = _mask_edge_polygon(mask)
    matches: dict[tuple[int, int], OpenPath] = {}
    seam_interior: set[Point] = set()
    breakpoints: set[int] = set()
    for seam in seams:
        match = _match_cyclic_run(polygon, np.asarray(seam.raw_coordinates))
        if match is None:
            raise ValueError(
                f"canonical seam is absent from neighboring path: {seam.id}"
            )
        start, length, forward = match
        end = (start + length - 1) % len(polygon)
        oriented = seam.path if forward else seam.path.reversed()
        if oriented.start != tuple(polygon[start]) or oriented.end != tuple(
            polygon[end]
        ):
            raise ValueError(f"canonical seam endpoint mismatch: {seam.id}")
        matches[(start, end)] = oriented
        breakpoints.update((start, end))
        raw = seam.raw_coordinates if forward else tuple(reversed(seam.raw_coordinates))
        seam_interior.update(raw[1:-1])
    for corner in locked:
        if corner in seam_interior:
            continue
        distances = np.linalg.norm(polygon - np.asarray(corner), axis=1)
        breakpoints.add(int(np.argmin(distances)))
    if not breakpoints:
        breakpoints.update(int(index * len(polygon) / 4) for index in range(4))
    indexes = sorted(breakpoints)
    start_index = indexes[0]
    ordered = indexes + [start_index + len(polygon)]
    segments: list[PathSegment] = []
    for first, second_unwrapped in zip(ordered, ordered[1:]):
        second = second_unwrapped % len(polygon)
        seam_path = matches.get((first, second))
        if seam_path is not None:
            segments.extend(seam_path.segments)
            continue
        span_indexes = [
            value % len(polygon) for value in range(first, second_unwrapped + 1)
        ]
        span = polygon[span_indexes]
        fitted = _fit_open_path(
            span,
            float(min(_bbox_size(mask))),
            profile,
            epsilon_multiplier=epsilon_multiplier,
        )
        segments.extend(fitted.segments)
    path = _closed_path(
        OpenPath(tuple(polygon[start_index]), tuple(segments)), width, height
    )
    return path


def _fit_open_path(
    points: np.ndarray,
    scale_basis: float,
    profile: VectorizationProfile,
    *,
    epsilon_multiplier: float = 1.0,
) -> OpenPath:
    points = np.asarray(points, dtype=np.float64)
    if len(points) < 2:
        raise ValueError("open contour needs two endpoints")
    chord = points[-1] - points[0]
    chord_length = float(np.linalg.norm(chord))
    if chord_length == 0:
        raise ValueError("open contour endpoints must differ")
    residual = np.abs(_cross_2d(chord, points - points[0])) / chord_length
    if float(residual.max()) <= scale_basis * profile.line_residual_fraction:
        return OpenPath(tuple(points[0]), (PathSegment("L", tuple(points[-1])),))
    epsilon = scale_basis * profile.contour_epsilon_fraction * epsilon_multiplier
    simplified = (
        cv2.approxPolyDP(points.astype(np.float32).reshape(-1, 1, 2), epsilon, False)
        .reshape(-1, 2)
        .astype(np.float64)
    )
    if not np.array_equal(simplified[0], points[0]):
        simplified = np.vstack((points[0], simplified))
    if not np.array_equal(simplified[-1], points[-1]):
        simplified = np.vstack((simplified, points[-1]))
    if len(simplified) == 2:
        midpoint = points[len(points) // 2]
        simplified = np.vstack((simplified[0], midpoint, simplified[1]))
    segments: list[PathSegment] = []
    for index in range(len(simplified) - 1):
        start = simplified[index]
        end = simplified[index + 1]
        previous = simplified[index - 1] if index else start
        following = simplified[index + 2] if index + 2 < len(simplified) else end
        control_1 = start + (end - previous) / 6.0
        control_2 = end - (following - start) / 6.0
        segments.append(
            PathSegment(
                "C",
                tuple(end),
                tuple(control_1),
                tuple(control_2),
            )
        )
    return OpenPath(tuple(simplified[0]), tuple(segments))


def _closed_path(path: OpenPath, width: int, height: int) -> DisplayPath:
    parts = ["M", _number(path.start[0]), _number(path.start[1])]
    for segment in path.segments:
        if segment.command == "L":
            parts.extend(("L", _number(segment.end[0]), _number(segment.end[1])))
        else:
            if segment.control_1 is None or segment.control_2 is None:
                raise ValueError("cubic closed-path segment requires two controls")
            control_1 = np.clip(
                segment.control_1, (0.0, 0.0), (float(width), float(height))
            )
            control_2 = np.clip(
                segment.control_2, (0.0, 0.0), (float(width), float(height))
            )
            parts.extend(
                (
                    "C",
                    _number(control_1[0]),
                    _number(control_1[1]),
                    _number(control_2[0]),
                    _number(control_2[1]),
                    _number(segment.end[0]),
                    _number(segment.end[1]),
                )
            )
    parts.append("Z")
    parsed = parse_display_path(
        " ".join(parts), "vectorPath", width, height, allow_linear_segments=True
    )
    if parsed is None:
        raise ValueError("vector path unexpectedly missing")
    return parsed


def _open_path_data(path: OpenPath) -> str:
    parts = ["M", _number(path.start[0]), _number(path.start[1])]
    for segment in path.segments:
        if segment.command == "L":
            parts.extend(("L", _number(segment.end[0]), _number(segment.end[1])))
        else:
            if segment.control_1 is None or segment.control_2 is None:
                raise ValueError("cubic open-path segment requires two controls")
            parts.extend(
                (
                    "C",
                    _number(segment.control_1[0]),
                    _number(segment.control_1[1]),
                    _number(segment.control_2[0]),
                    _number(segment.control_2[1]),
                    _number(segment.end[0]),
                    _number(segment.end[1]),
                )
            )
    return " ".join(parts)


def parse_open_path_data(
    value: object, width: int, height: int, *, allow_closed: bool = False
) -> OpenPath:
    if not isinstance(value, str) or not value:
        raise ValueError("canonical seam path must be a nonempty string")
    tokens = value.split()
    if len(tokens) < 4 or tokens[0] != "M":
        raise ValueError("canonical seam path must start with M")
    index = 1

    def point() -> Point:
        nonlocal index
        if index + 2 > len(tokens):
            raise ValueError("canonical seam path has incomplete coordinates")
        try:
            result = (float(tokens[index]), float(tokens[index + 1]))
        except ValueError as error:
            raise ValueError("canonical seam path has invalid coordinates") from error
        index += 2
        if not all(math.isfinite(item) for item in result) or not (
            0 <= result[0] <= width and 0 <= result[1] <= height
        ):
            raise ValueError("canonical seam coordinates leave the view box")
        return result

    start = point()
    segments: list[PathSegment] = []
    while index < len(tokens):
        command = tokens[index]
        index += 1
        if command == "L":
            segments.append(PathSegment("L", point()))
        elif command == "C":
            control_1, control_2, end = point(), point(), point()
            segments.append(PathSegment("C", end, control_1, control_2))
        else:
            raise ValueError("canonical seam path has an unsupported command")
    if not segments or (not allow_closed and start == segments[-1].end):
        raise ValueError("canonical seam path must be nonempty and open")
    return OpenPath(start, tuple(segments))


def display_path_open_segments(path: DisplayPath) -> OpenPath:
    tokens = path.data.split()
    if tokens[0] != "M" or tokens[-1] != "Z":
        raise ValueError("display path must be closed")
    open_data = " ".join(tokens[:-1])
    # Coordinates have already been validated by DisplayPath parsing; derive a
    # permissive local view box from them for the canonical segment model.
    maximum_x = max((coordinate[0] for coordinate in path.coordinates), default=0.0)
    maximum_y = max((coordinate[1] for coordinate in path.coordinates), default=0.0)
    return parse_open_path_data(
        open_data, math.ceil(maximum_x), math.ceil(maximum_y), allow_closed=True
    )


def display_path_contains_open_path(path: DisplayPath, seam: OpenPath) -> bool:
    closed = display_path_open_segments(path)
    starts = [closed.start]
    for segment in closed.segments[:-1]:
        starts.append(segment.end)
    for index, start in enumerate(starts):
        if start != seam.start:
            continue
        candidate = tuple(
            closed.segments[(index + offset) % len(closed.segments)]
            for offset in range(len(seam.segments))
        )
        if candidate == seam.segments:
            return True
    return False


def _match_cyclic_run(
    polygon: np.ndarray, raw: np.ndarray
) -> tuple[int, int, bool] | None:
    count = len(polygon)
    for forward, candidate in ((True, raw), (False, raw[::-1])):
        starts = np.flatnonzero(np.all(polygon == candidate[0], axis=1))
        for start in starts:
            indexes = [
                (int(start) + offset) % count for offset in range(len(candidate))
            ]
            if np.array_equal(polygon[indexes], candidate):
                return int(start), len(candidate), forward
    return None


def _best_rounded_path(
    raw: np.ndarray, width: int, height: int, profile: VectorizationProfile
) -> DisplayPath | None:
    ys, xs = np.nonzero(raw)
    left, right = float(xs.min()), float(xs.max() + 1)
    top, bottom = float(ys.min()), float(ys.max() + 1)
    short = min(right - left, bottom - top)
    best: tuple[float, DisplayPath] | None = None
    # Fractions, rather than absolute radii, let the same fit operate on any hold size.
    for fraction in np.linspace(0.08, 0.5, 29):
        radius = short * float(fraction)
        path = _rounded_rect_path(left, top, right, bottom, radius, width, height)
        mask = rasterize_display_path(path, width, height)
        iou = _iou(raw, mask)
        if best is None or iou > best[0]:
            best = (iou, path)
    if best is None or best[0] < profile.rounded_residual_iou:
        return None
    return best[1]


def _rounded_rect_path(
    left: float,
    top: float,
    right: float,
    bottom: float,
    radius: float,
    width: int,
    height: int,
) -> DisplayPath:
    radius = min(radius, (right - left) / 2.0, (bottom - top) / 2.0)
    kappa = 0.5522847498307936
    k = radius * kappa
    parts = [
        "M",
        _number(left + radius),
        _number(top),
        "L",
        _number(right - radius),
        _number(top),
        "C",
        _number(right - radius + k),
        _number(top),
        _number(right),
        _number(top + radius - k),
        _number(right),
        _number(top + radius),
        "L",
        _number(right),
        _number(bottom - radius),
        "C",
        _number(right),
        _number(bottom - radius + k),
        _number(right - radius + k),
        _number(bottom),
        _number(right - radius),
        _number(bottom),
        "L",
        _number(left + radius),
        _number(bottom),
        "C",
        _number(left + radius - k),
        _number(bottom),
        _number(left),
        _number(bottom - radius + k),
        _number(left),
        _number(bottom - radius),
        "L",
        _number(left),
        _number(top + radius),
        "C",
        _number(left),
        _number(top + radius - k),
        _number(left + radius - k),
        _number(top),
        _number(left + radius),
        _number(top),
        "Z",
    ]
    parsed = parse_display_path(
        " ".join(parts), "roundedMouth", width, height, allow_linear_segments=True
    )
    if parsed is None:
        raise ValueError("rounded path unexpectedly missing")
    return parsed


def _canonical_seams(
    regions: tuple[Stage2MaskRegion, ...],
    piece_masks: tuple[np.ndarray, ...],
    profile: VectorizationProfile,
) -> tuple[CanonicalSeam, ...]:
    pending: list[
        tuple[
            str,
            str,
            Literal["region", "piece"],
            tuple[Point, ...],
            float,
            np.ndarray | None,
        ]
    ] = []
    surfaces = [region for region in regions if region.visual_mode == "surface"]
    for index, first in enumerate(surfaces):
        for second in surfaces[index + 1 :]:
            if first.piece_index != second.piece_index:
                continue
            shared = _shared_edges(first.mask, second.mask)
            if not shared:
                continue
            coordinates = _orient_seam_for_mask(_ordered_seam(shared), first.mask)
            pending.append(
                (
                    first.id,
                    second.id,
                    "region",
                    coordinates,
                    float(min(_bbox_size(first.mask))),
                    None,
                )
            )
    for region in surfaces:
        piece_id = f"piece-{region.piece_index + 1:02d}-silhouette"
        shared = _mask_boundary_edges(region.mask) & _mask_boundary_edges(
            piece_masks[region.piece_index]
        )
        if not shared:
            continue
        coordinates = _orient_seam_for_mask(_ordered_seam(shared), region.mask)
        pending.append(
            (
                region.id,
                piece_id,
                "piece",
                coordinates,
                float(min(_bbox_size(region.mask))),
                piece_masks[region.piece_index],
            )
        )
    seams: list[CanonicalSeam] = []
    for index, (
        first_id,
        second_id,
        kind,
        coordinates,
        scale_basis,
        allowed_mask,
    ) in enumerate(pending, start=1):
        path = (
            _fit_piece_seam(
                np.asarray(coordinates),
                scale_basis,
                profile,
                allowed_mask
                if allowed_mask is not None
                else np.empty((0, 0), dtype=np.uint8),
            )
            if kind == "piece"
            else _fit_open_seam(np.asarray(coordinates), scale_basis, profile)
        )
        path = parse_open_path_data(
            path.data, piece_masks[0].shape[1], piece_masks[0].shape[0]
        )
        seams.append(
            CanonicalSeam(
                f"seam-{index:03d}", kind, first_id, second_id, path, coordinates
            )
        )
    return tuple(seams)


def _fit_piece_seam(
    points: np.ndarray,
    scale_basis: float,
    profile: VectorizationProfile,
    piece_mask: np.ndarray,
) -> OpenPath:
    for multiplier in (1.0, 0.7):
        candidate = _fit_open_seam(
            points, scale_basis, profile, epsilon_multiplier=multiplier
        )
        if _open_path_within_mask(candidate, piece_mask):
            return candidate
    for epsilon_multiplier in (1.5, 2.0, 1.0, 0.75):
        for inset_multiplier in (1.25, 1.5, 2.0):
            candidate = _fit_inset_open_spline(
                points,
                scale_basis,
                profile,
                epsilon_multiplier=epsilon_multiplier,
                inset_multiplier=inset_multiplier,
            )
            if _open_path_within_mask(candidate, piece_mask):
                return candidate
    return _fit_open_lines(points, scale_basis, profile)


def _fit_inset_open_spline(
    points: np.ndarray,
    scale_basis: float,
    profile: VectorizationProfile,
    *,
    epsilon_multiplier: float,
    inset_multiplier: float,
) -> OpenPath:
    points = np.asarray(points, dtype=np.float64)
    epsilon = scale_basis * profile.contour_epsilon_fraction * epsilon_multiplier
    anchors = (
        cv2.approxPolyDP(points.astype(np.float32).reshape(-1, 1, 2), epsilon, False)
        .reshape(-1, 2)
        .astype(np.float64)
    )
    if not np.array_equal(anchors[0], points[0]):
        anchors = np.vstack((points[0], anchors))
    if not np.array_equal(anchors[-1], points[-1]):
        anchors = np.vstack((anchors, points[-1]))
    inset = anchors.copy()
    distance = scale_basis * profile.curve_error_fraction * inset_multiplier
    for index in range(1, len(inset) - 1):
        tangent = anchors[index + 1] - anchors[index - 1]
        length = float(np.linalg.norm(tangent))
        if length <= 1e-9:
            continue
        # Canonical outer seams follow the cell-edge polygon orientation, whose
        # interior is consistently on the left in image coordinates.
        inward = np.asarray((-tangent[1], tangent[0])) / length
        inset[index] += inward * distance
    tension = 0.25
    segments: list[PathSegment] = []
    for index in range(len(inset) - 1):
        previous = inset[max(index - 1, 0)]
        start = inset[index]
        end = inset[index + 1]
        following = inset[min(index + 2, len(inset) - 1)]
        control_1 = start + (end - previous) * tension / 6
        control_2 = end - (following - start) * tension / 6
        segments.append(
            PathSegment("C", tuple(end), tuple(control_1), tuple(control_2))
        )
    return OpenPath(tuple(inset[0]), tuple(segments))


def _open_path_within_mask(path: OpenPath, mask: np.ndarray) -> bool:
    polygon = _mask_edge_polygon(mask).astype(np.float32).reshape(-1, 1, 2)
    start = np.asarray(path.start, dtype=np.float64)
    for segment in path.segments:
        end = np.asarray(segment.end, dtype=np.float64)
        for step in range(1, 33):
            t = step / 32
            if segment.command == "L":
                point = (1 - t) * start + t * end
            else:
                if segment.control_1 is None or segment.control_2 is None:
                    raise ValueError("cubic open-path segment requires two controls")
                control_1 = np.asarray(segment.control_1)
                control_2 = np.asarray(segment.control_2)
                point = (
                    (1 - t) ** 3 * start
                    + 3 * (1 - t) ** 2 * t * control_1
                    + 3 * (1 - t) * t**2 * control_2
                    + t**3 * end
                )
            if (
                cv2.pointPolygonTest(polygon, (float(point[0]), float(point[1])), False)
                < 0
            ):
                return False
        start = end
    return True


def _orient_seam_for_mask(
    coordinates: tuple[Point, ...], mask: np.ndarray
) -> tuple[Point, ...]:
    match = _match_cyclic_run(_mask_edge_polygon(mask), np.asarray(coordinates))
    if match is None:
        raise ValueError("canonical seam is absent from its first mask")
    return coordinates if match[2] else tuple(reversed(coordinates))


def _fit_open_lines(
    points: np.ndarray, scale_basis: float, profile: VectorizationProfile
) -> OpenPath:
    del scale_basis, profile
    points = np.asarray(points, dtype=np.float64)
    keep = [0]
    for index in range(1, len(points) - 1):
        if (
            abs(
                float(
                    _cross_2d(
                        points[index] - points[index - 1],
                        points[index + 1] - points[index],
                    )
                )
            )
            > 1e-9
        ):
            keep.append(index)
    keep.append(len(points) - 1)
    simplified = points[keep]
    return OpenPath(
        tuple(simplified[0]),
        tuple(PathSegment("L", tuple(point)) for point in simplified[1:]),
    )


def _fit_open_seam(
    points: np.ndarray,
    scale_basis: float,
    profile: VectorizationProfile,
    *,
    epsilon_multiplier: float = 1.0,
) -> OpenPath:
    points = np.asarray(points, dtype=np.float64)
    epsilon = scale_basis * profile.contour_epsilon_fraction * epsilon_multiplier
    simplified = (
        cv2.approxPolyDP(points.astype(np.float32).reshape(-1, 1, 2), epsilon, False)
        .reshape(-1, 2)
        .astype(np.float64)
    )
    if not np.array_equal(simplified[0], points[0]):
        simplified = np.vstack((points[0], simplified))
    if not np.array_equal(simplified[-1], points[-1]):
        simplified = np.vstack((simplified, points[-1]))
    raw_index = 0
    segments: list[PathSegment] = []
    for start, end in zip(simplified, simplified[1:]):
        matches = np.flatnonzero(np.all(points[raw_index:] == end, axis=1))
        if not len(matches):
            raise ValueError("simplified seam point is absent from raw boundary")
        end_index = raw_index + int(matches[0])
        span = points[raw_index : end_index + 1]
        chord = end - start
        residual = np.abs(_cross_2d(chord, span - start)) / max(
            float(np.linalg.norm(chord)), 1e-9
        )
        if float(residual.max()) <= scale_basis * profile.line_residual_fraction:
            segments.append(PathSegment("L", tuple(end)))
        else:
            control_1 = span[int((len(span) - 1) / 3)]
            control_2 = span[int((len(span) - 1) * 2 / 3)]
            segments.append(
                PathSegment("C", tuple(end), tuple(control_1), tuple(control_2))
            )
        raw_index = end_index
    return OpenPath(tuple(simplified[0]), tuple(segments))


def _shared_edges(first: np.ndarray, second: np.ndarray) -> set[tuple[Point, Point]]:
    return _mask_boundary_edges(first) & _mask_boundary_edges(second)


def _mask_boundary_edges(mask: np.ndarray) -> set[tuple[Point, Point]]:
    selected = mask.astype(bool)
    height, width = selected.shape
    result: set[tuple[Point, Point]] = set()

    def add(first: Point, second: Point) -> None:
        result.add(tuple(sorted((first, second))))

    for y, x in np.argwhere(selected):
        if y == 0 or not selected[y - 1, x]:
            add((float(x), float(y)), (float(x + 1), float(y)))
        if x == width - 1 or not selected[y, x + 1]:
            add((float(x + 1), float(y)), (float(x + 1), float(y + 1)))
        if y == height - 1 or not selected[y + 1, x]:
            add((float(x), float(y + 1)), (float(x + 1), float(y + 1)))
        if x == 0 or not selected[y, x - 1]:
            add((float(x), float(y)), (float(x), float(y + 1)))
    return result


def _ordered_seam(edges: set[tuple[Point, Point]]) -> tuple[Point, ...]:
    adjacency: dict[Point, set[Point]] = {}
    for first, second in edges:
        adjacency.setdefault(first, set()).add(second)
        adjacency.setdefault(second, set()).add(first)
    if any(len(values) > 2 for values in adjacency.values()):
        raise ValueError("canonical seam graph branches")
    endpoints = sorted(point for point, values in adjacency.items() if len(values) == 1)
    if len(endpoints) != 2:
        message = (
            "canonical seam graph is disconnected"
            if len(endpoints) > 2
            else "canonical seam graph must be one open path"
        )
        raise ValueError(message)
    current = endpoints[0]
    previous: Point | None = None
    points = [current]
    while True:
        choices = sorted(value for value in adjacency[current] if value != previous)
        if not choices:
            break
        following = choices[0]
        points.append(following)
        previous, current = current, following
    if len(points) != len(edges) + 1 or current != endpoints[1]:
        raise ValueError("canonical seam graph is disconnected")
    return tuple(points)


def _concavity_metrics(mask: np.ndarray) -> tuple[float, float]:
    contours, _ = cv2.findContours(
        mask.astype(np.uint8), cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE
    )
    contour = max(contours, key=cv2.contourArea)
    hull = cv2.convexHull(contour)
    hull_area = max(float(cv2.contourArea(hull)), 1.0)
    area_fraction = max(0.0, (hull_area - float(cv2.contourArea(contour))) / hull_area)
    hull_indexes = cv2.convexHull(contour, returnPoints=False)
    defects = cv2.convexityDefects(contour, hull_indexes)
    depth = (
        0.0 if defects is None else float(defects.reshape(-1, 4)[:, 3].max()) / 256.0
    )
    depth_fraction = depth / max(1.0, float(min(_bbox_size(mask))))
    return area_fraction, depth_fraction


def _rounded_faithful(
    raw: np.ndarray,
    path: DisplayPath,
    width: int,
    height: int,
    scale_basis: float,
    profile: VectorizationProfile,
) -> bool:
    scale = profile.supersample
    candidate = rasterize_display_path(path, width, height, scale=scale)
    reference = cv2.resize(
        raw, (width * scale, height * scale), interpolation=cv2.INTER_NEAREST
    )
    return (
        _iou(reference, candidate) >= profile.rounded_residual_iou
        and _centroid_shift(reference, candidate) / scale
        <= scale_basis * profile.rounded_centroid_fraction
        and _hd95(reference, candidate) / scale
        <= scale_basis * profile.rounded_hd95_fraction
    )


def _locally_faithful(
    raw: np.ndarray,
    candidate: np.ndarray,
    scale_basis: float,
    profile: VectorizationProfile,
) -> bool:
    if _iou(raw, candidate) < profile.local_iou_floor:
        return False
    centroid_limit = scale_basis * profile.local_centroid_fraction
    hd95_limit = scale_basis * profile.local_hd95_fraction
    return (
        _centroid_shift(raw, candidate) <= centroid_limit
        and _hd95(raw, candidate) <= hd95_limit
    )


def _bbox_size(mask: np.ndarray) -> tuple[int, int]:
    ys, xs = np.nonzero(mask)
    return int(xs.max() - xs.min() + 1), int(ys.max() - ys.min() + 1)


def _iou(first: np.ndarray, second: np.ndarray) -> float:
    intersection = int(np.count_nonzero(first.astype(bool) & second.astype(bool)))
    union = int(np.count_nonzero(first.astype(bool) | second.astype(bool)))
    return intersection / union if union else 1.0


def _centroid_shift(first: np.ndarray, second: np.ndarray) -> float:
    def center(mask: np.ndarray) -> tuple[float, float]:
        moments = cv2.moments(mask.astype(np.uint8), binaryImage=True)
        return moments["m10"] / moments["m00"], moments["m01"] / moments["m00"]

    left, right = center(first), center(second)
    return float(math.hypot(left[0] - right[0], left[1] - right[1]))


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


def validate_display_path(
    path: DisplayPath, *, scale_basis: float, profile: VectorizationProfile
) -> None:
    if not math.isfinite(scale_basis) or scale_basis <= 0:
        raise ValueError("path scale basis must be positive and finite")
    curve_count = max(1, sum(command in {"Q", "C"} for command in path.commands))
    coarse = flatten_display_path(path, curve_steps=8)
    perimeter = float(np.linalg.norm(np.diff(coarse, axis=0), axis=1).sum())
    target = scale_basis * profile.validity_flatten_fraction
    curve_steps = int(
        np.clip(math.ceil(perimeter / max(target * curve_count, 1e-9)), 8, 128)
    )
    contour = flatten_display_path(path, curve_steps=curve_steps)
    keep = np.concatenate(
        ([True], np.linalg.norm(np.diff(contour, axis=0), axis=1) > 1e-10)
    )
    contour = contour[keep]
    points = contour[:-1]
    segment_count = len(points)
    if segment_count < 3:
        raise ValueError("display path has too few segments")
    signed_double_area = float(np.sum(_cross_2d(points, np.roll(points, -1, axis=0))))
    if abs(signed_double_area) <= max(1e-10, scale_basis**2 * 1e-8):
        raise ValueError("display path is degenerate or has zero area")
    starts = points
    ends = np.roll(points, -1, axis=0)
    minima = np.minimum(starts, ends)
    maxima = np.maximum(starts, ends)
    active: list[int] = []
    for second_index in np.argsort(minima[:, 0], kind="stable").tolist():
        active = [
            first_index
            for first_index in active
            if maxima[first_index, 0] >= minima[second_index, 0]
        ]
        for first_index in active:
            if (first_index - second_index) % segment_count in {1, segment_count - 1}:
                continue
            if np.any(maxima[first_index] < minima[second_index]) or np.any(
                maxima[second_index] < minima[first_index]
            ):
                continue
            if _segments_intersect_or_touch(
                starts[first_index],
                ends[first_index],
                starts[second_index],
                ends[second_index],
            ):
                raise ValueError("display path self-intersects or self-contacts")
        active.append(second_index)


def _segments_intersect_or_touch(
    a: np.ndarray, b: np.ndarray, c: np.ndarray, d: np.ndarray
) -> bool:
    def orientation(first: np.ndarray, second: np.ndarray, third: np.ndarray) -> float:
        return float(_cross_2d(second - first, third - first))

    first = orientation(a, b, c)
    second = orientation(a, b, d)
    third = orientation(c, d, a)
    fourth = orientation(c, d, b)
    tolerance = 1e-8
    if first * second < -tolerance and third * fourth < -tolerance:
        return True

    def on_segment(
        first_point: np.ndarray,
        second_point: np.ndarray,
        value: np.ndarray,
        cross: float,
    ) -> bool:
        return (
            abs(cross) <= tolerance
            and np.all(value >= np.minimum(first_point, second_point) - tolerance)
            and np.all(value <= np.maximum(first_point, second_point) + tolerance)
        )

    return (
        on_segment(a, b, c, first)
        or on_segment(a, b, d, second)
        or on_segment(c, d, a, third)
        or on_segment(c, d, b, fourth)
    )


def _number(value: float) -> str:
    rounded = 0.0 if abs(float(value)) < 5e-10 else float(value)
    return f"{rounded:.6f}".rstrip("0").rstrip(".")


def _cross_2d(first: np.ndarray, second: np.ndarray) -> np.ndarray:
    return first[..., 0] * second[..., 1] - first[..., 1] * second[..., 0]
