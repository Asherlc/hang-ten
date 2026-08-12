from __future__ import annotations

from hashlib import sha256

import cv2
import numpy as np
import pytest

from hangboard_vectorizer.display_paths import flatten_display_path, parse_display_path
from hangboard_vectorizer.stage3_evaluation import _raw_preservation
from hangboard_vectorizer.vector_smoothing import (
    OpenPath,
    Stage2MaskRegion,
    VectorizationProfile,
    _mask_edge_polygon,
    _ordered_seam,
    display_path_contains_open_path,
    display_path_open_segments,
    rasterize_display_path,
    rasterize_paths_independent,
    rasterize_paths_half_open,
    validate_display_path,
    vectorize_layout,
)


def test_residual_selects_rounded_pocket_and_concavity_falls_back() -> None:
    rgba = _rgba(160, 90)
    rounded = _rounded_mask(90, 160, 12, 15, 62, 42, 9)
    irregular = _rounded_mask(90, 160, 88, 18, 58, 38, 7)
    irregular[34:44, 88:106] = 0
    regions = (
        _region("piece-01-hold-01", "pocket", rounded),
        _region("piece-01-hold-02", "pocket", irregular),
    )
    layout = vectorize_layout(rgba, _labels(regions), regions, profile=VectorizationProfile())
    assert len(layout.pieces) == 1
    assert layout.regions[0].primitive == "rounded-mouth"
    assert layout.regions[1].primitive == "feature-spline"
    assert "C" in layout.regions[0].display_path.commands
    for raw, vector in zip(regions, layout.regions, strict=True):
        output = rasterize_display_path(vector.display_path, layout.width, layout.height)
        assert _iou(raw.mask, output) >= 0.985
        assert vector.raw_mask_sha256 == sha256(raw.mask.tobytes()).hexdigest()


def test_mixed_hard_corners_shared_seam_chromatic_pixels_and_non_top_surface() -> None:
    rgba = _rgba(140, 100)
    rgba[20:80, 10:130, :3] = (23, 210, 119)
    left = np.zeros((100, 140), dtype=np.uint8)
    right = np.zeros_like(left)
    cv2.rectangle(left, (18, 35), (69, 70), 1, -1)
    cv2.rectangle(right, (70, 35), (121, 70), 1, -1)
    left[35:43, 18:28] = 0
    regions = (
        _region("piece-01-hold-01", "jug", left),
        _region("piece-01-hold-02", "sloper", right),
    )
    layout = vectorize_layout(rgba, _labels(regions), regions, profile=VectorizationProfile())
    region_seams = [seam for seam in layout.canonical_seams if seam.kind == "region"]
    assert len(region_seams) == 1
    seam = region_seams[0]
    assert (seam.first_id, seam.second_id) == (
        "piece-01-hold-01", "piece-01-hold-02"
    )
    assert seam.raw_coordinates[0][0] == seam.raw_coordinates[-1][0] == 70
    assert display_path_contains_open_path(layout.regions[0].display_path, seam.path)
    assert display_path_contains_open_path(layout.regions[1].display_path, seam.path.reversed())
    assert all(region.primitive == "feature-spline" for region in layout.regions)
    assert any(region.locked_corners for region in layout.regions)
    assert any("L" in region.display_path.commands for region in layout.regions)
    assert all(region.shared_seam_ids == (seam.id,) for region in layout.regions)


def test_curved_diagonal_seam_has_exact_reversal_and_half_open_ownership() -> None:
    height, width = 110, 150
    rgba = _rgba(width, height)
    left = np.zeros((height, width), dtype=np.uint8)
    right = np.zeros_like(left)
    for y in range(20, 91):
        seam_x = int(72 + 9 * np.sin((y - 20) / 70 * np.pi))
        left[y, 18:seam_x] = 1
        right[y, seam_x:132] = 1
    regions = (
        _region("piece-01-hold-01", "jug", left),
        _region("piece-01-hold-02", "sloper", right),
    )
    layout = vectorize_layout(rgba, _labels(regions), regions, profile=VectorizationProfile())
    seam = next(value for value in layout.canonical_seams if value.kind == "region")
    assert any(segment.command == "C" for segment in seam.path.segments)
    assert display_path_contains_open_path(layout.regions[0].display_path, seam.path)
    assert display_path_contains_open_path(layout.regions[1].display_path, seam.path.reversed())
    masks = rasterize_paths_half_open(
        tuple(region.display_path for region in layout.regions), width, height, scale=4
    )
    assert np.count_nonzero(masks[0] & masks[1]) == 0
    paths = {
        region.id: vector.display_path
        for region, vector in zip(regions, layout.regions, strict=True)
    }
    independent = rasterize_paths_independent(
        tuple(paths.values()), width, height, scale=4
    )
    assert np.count_nonzero(independent[0] & independent[1]) == 83
    shared_region_seams = {
        frozenset((seam.first_id, seam.second_id)): seam.path
    }
    metrics, _ = _raw_preservation(rgba, regions, paths, shared_region_seams)
    assert metrics["newOverlapPixels"] == 0

    incursion_data = layout.regions[0].display_path.data.replace(
        "M 18 20 L 72 20", "M 18 20 L 90 10 L 90 30 L 72 20"
    )
    incursion = parse_display_path(
        incursion_data,
        "curved-seam-interior-incursion",
        width,
        height,
        allow_linear_segments=True,
    )
    assert incursion is not None
    validate_display_path(
        incursion, scale_basis=71, profile=VectorizationProfile()
    )
    assert display_path_contains_open_path(incursion, seam.path)
    incursion_metrics, _ = _raw_preservation(
        rgba,
        regions,
        {regions[0].id: incursion, regions[1].id: layout.regions[1].display_path},
        shared_region_seams,
    )
    assert incursion_metrics["newOverlapPixels"] > 0


def test_feature_fallback_is_genuinely_curved_and_reduces_staircase() -> None:
    rgba = _rgba(180, 100)
    mask = np.zeros((100, 180), dtype=np.uint8)
    cv2.ellipse(mask, (90, 54), (62, 30), 0, 0, 360, 1, -1)
    mask[46:63, 28:57] = 0
    region = _region("piece-01-hold-01", "pocket", mask)
    layout = vectorize_layout(rgba, _labels((region,)), (region,), profile=VectorizationProfile())
    vector = layout.regions[0]
    assert vector.primitive == "feature-spline"
    open_path = display_path_open_segments(vector.display_path)
    _assert_all_cubics_are_genuinely_curved(open_path)
    assert len(open_path.segments) < len(_mask_edge_polygon(mask)) / 3
    assert any(abs(x - 57) < 2 and 45 <= y <= 64 for x, y in vector.locked_corners)


def test_piece_seam_fallback_is_compact_curved_contained_and_scale_relative() -> None:
    seams = []
    for scale in (1, 2):
        height, width = 300 * scale, 500 * scale
        piece = _rounded_mask(
            height,
            width,
            10 * scale,
            10 * scale,
            480 * scale,
            280 * scale,
            30 * scale,
        )
        surface = np.zeros_like(piece)
        surface[10 * scale : 150 * scale, 10 * scale : 150 * scale] = piece[
            10 * scale : 150 * scale, 10 * scale : 150 * scale
        ]
        rgba = np.zeros((height, width, 4), dtype=np.uint8)
        rgba[piece.astype(bool)] = (192, 144, 84, 255)
        region = Stage2MaskRegion(
            "piece-01-hold-01", 0, "jug", "surface", 1, surface
        )
        layout = vectorize_layout(
            rgba,
            _labels((region,)),
            (region,),
            profile=VectorizationProfile(),
        )
        seam = next(value for value in layout.canonical_seams if value.kind == "piece")
        _assert_all_cubics_are_genuinely_curved(seam.path)
        assert len(seam.path.segments) < len(seam.raw_coordinates) / 4
        assert any(
            segment.end not in set(seam.raw_coordinates)
            for segment in seam.path.segments[:-1]
        )
        assert display_path_contains_open_path(layout.regions[0].display_path, seam.path)
        assert display_path_contains_open_path(layout.pieces[0].display_path, seam.path)
        candidate = rasterize_display_path(
            layout.regions[0].display_path, width, height, scale=4
        )
        allowed = cv2.resize(
            piece, (width * 4, height * 4), interpolation=cv2.INTER_NEAREST
        )
        assert np.count_nonzero(candidate.astype(bool) & ~allowed.astype(bool)) == 0
        seams.append(seam)

    assert tuple(segment.command for segment in seams[0].path.segments) == tuple(
        segment.command for segment in seams[1].path.segments
    )
    assert np.allclose(
        _open_path_coordinates(seams[1].path) / 2,
        _open_path_coordinates(seams[0].path),
        atol=1.1,
    )


def test_chromatic_invariance_and_normalized_scale_equivalence() -> None:
    mask = _rounded_mask(90, 160, 28, 24, 92, 42, 9)
    region = _region("piece-01-hold-01", "pocket", mask)
    first_rgba = _rgba(160, 90)
    second_rgba = first_rgba.copy()
    second_rgba[..., :3] = (11, 221, 147)
    first = vectorize_layout(first_rgba, _labels((region,)), (region,), profile=VectorizationProfile())
    second = vectorize_layout(second_rgba, _labels((region,)), (region,), profile=VectorizationProfile())
    assert first.regions[0].display_path.data == second.regions[0].display_path.data
    assert first.pieces[0].display_path.data == second.pieces[0].display_path.data

    scaled_mask = cv2.resize(mask, None, fx=2, fy=2, interpolation=cv2.INTER_NEAREST)
    scaled_region = _region("piece-01-hold-01", "pocket", scaled_mask)
    scaled_rgba = cv2.resize(first_rgba, None, fx=2, fy=2, interpolation=cv2.INTER_NEAREST)
    scaled = vectorize_layout(scaled_rgba, _labels((scaled_region,)), (scaled_region,), profile=VectorizationProfile())
    assert first.regions[0].display_path.commands == scaled.regions[0].display_path.commands
    normalized = np.asarray(scaled.regions[0].display_path.coordinates) / 2
    assert np.allclose(normalized, first.regions[0].display_path.coordinates, atol=1.5)


def test_disconnected_and_branching_seam_graphs_fail_closed() -> None:
    disconnected = {
        ((0.0, 0.0), (1.0, 0.0)),
        ((3.0, 0.0), (4.0, 0.0)),
    }
    branching = {
        ((0.0, 0.0), (1.0, 0.0)),
        ((1.0, 0.0), (2.0, 0.0)),
        ((1.0, 0.0), (1.0, 1.0)),
    }
    with pytest.raises(ValueError, match="disconnected"):
        _ordered_seam(disconnected)
    with pytest.raises(ValueError, match="branches"):
        _ordered_seam(branching)


def test_independent_occupancy_exposes_overlap_before_half_open_ownership() -> None:
    path = parse_display_path(
        "M 2 2 L 8 2 L 8 8 L 2 8 Z",
        "rectangle",
        12,
        12,
        allow_linear_segments=True,
    )
    assert path is not None
    independent = rasterize_paths_independent((path, path), 12, 12)
    assert np.count_nonzero(independent[0] & independent[1]) == 36
    owned = rasterize_paths_half_open((path, path), 12, 12)
    assert np.count_nonzero(owned[0] & owned[1]) == 0
    assert np.count_nonzero(owned[0]) == 36
    assert np.count_nonzero(owned[1]) == 0

    first_raw = np.zeros((12, 12), dtype=np.uint8)
    first_raw[2:8, 2:5] = 1
    second_raw = np.zeros((12, 12), dtype=np.uint8)
    second_raw[2:8, 5:8] = 1
    overlapping_path = parse_display_path(
        "M 5 2 L 11 2 L 11 8 L 5 8 Z",
        "overlapping-rectangle",
        12,
        12,
        allow_linear_segments=True,
    )
    assert overlapping_path is not None
    raw_regions = (
        _region("piece-01-hold-01", "pocket", first_raw),
        _region("piece-01-hold-02", "pocket", second_raw),
    )
    metrics, regions = _raw_preservation(
        _rgba(12, 12), raw_regions,
        {raw_regions[0].id: path, raw_regions[1].id: overlapping_path},
        {},
    )
    assert metrics["newOverlapPixels"] == 288
    assert regions[1]["overlapPixels4x"] == 288


def test_display_path_validation_rejects_zero_area_contour() -> None:
    path = parse_display_path(
        "M 2 2 L 5 5 L 8 8 Z",
        "degenerate",
        12,
        12,
        allow_linear_segments=True,
    )
    assert path is not None
    with pytest.raises(ValueError, match="degenerate"):
        validate_display_path(
            path, scale_basis=6, profile=VectorizationProfile()
        )


def test_scale_invariance_and_split_piece_isolation() -> None:
    small_rgba = np.zeros((90, 200, 4), dtype=np.uint8)
    small_rgba[8:82, 5:95] = (210, 70, 140, 255)
    small_rgba[8:82, 105:195] = (35, 180, 225, 255)
    first = _rounded_mask(90, 200, 18, 24, 62, 42, 9)
    second = _rounded_mask(90, 200, 118, 24, 62, 42, 9)
    regions = (
        _region("piece-01-hold-01", "pocket", first, piece_index=0),
        _region("piece-02-hold-02", "pocket", second, piece_index=1),
    )
    layout = vectorize_layout(small_rgba, _labels(regions), regions, profile=VectorizationProfile())
    assert [region.piece_index for region in layout.regions] == [0, 1]

    large_rgba = cv2.resize(small_rgba, None, fx=2, fy=2, interpolation=cv2.INTER_NEAREST)
    large_regions = tuple(
        Stage2MaskRegion(
            region.id, region.piece_index, region.grip_type, region.visual_mode,
            region.row, cv2.resize(region.mask, None, fx=2, fy=2, interpolation=cv2.INTER_NEAREST),
        )
        for region in regions
    )
    scaled = vectorize_layout(large_rgba, _labels(large_regions), large_regions, profile=VectorizationProfile())
    assert [region.primitive for region in scaled.regions] == [region.primitive for region in layout.regions]
    for region in (*layout.regions, *scaled.regions):
        contour = flatten_display_path(region.display_path, curve_steps=16)
        assert np.isfinite(contour).all()
        assert np.array_equal(contour[0], contour[-1])


def _rgba(width: int, height: int) -> np.ndarray:
    rgba = np.empty((height, width, 4), dtype=np.uint8)
    rgba[...] = (192, 144, 84, 255)
    return rgba


def _rounded_mask(
    height: int, width: int, x: int, y: int, box_width: int, box_height: int, radius: int
) -> np.ndarray:
    mask = np.zeros((height, width), dtype=np.uint8)
    cv2.rectangle(mask, (x + radius, y), (x + box_width - radius - 1, y + box_height - 1), 1, -1)
    cv2.rectangle(mask, (x, y + radius), (x + box_width - 1, y + box_height - radius - 1), 1, -1)
    for center in (
        (x + radius, y + radius),
        (x + box_width - radius - 1, y + radius),
        (x + radius, y + box_height - radius - 1),
        (x + box_width - radius - 1, y + box_height - radius - 1),
    ):
        cv2.circle(mask, center, radius, 1, -1)
    return mask


def _region(
    identifier: str,
    grip_type: str,
    mask: np.ndarray,
    *,
    piece_index: int = 0,
) -> Stage2MaskRegion:
    return Stage2MaskRegion(
        identifier,
        piece_index,
        grip_type,  # type: ignore[arg-type]
        "aperture" if grip_type == "pocket" else "surface",
        1,
        mask,
    )


def _labels(regions: tuple[Stage2MaskRegion, ...]) -> np.ndarray:
    labels = np.zeros(regions[0].mask.shape, dtype=np.uint16)
    for index, region in enumerate(regions, start=1):
        labels[region.mask.astype(bool)] = index
    return labels


def _assert_all_cubics_are_genuinely_curved(path: OpenPath) -> None:
    current = np.asarray(path.start, dtype=float)
    cubic_count = 0
    for segment in path.segments:
        end = np.asarray(segment.end, dtype=float)
        if segment.command == "C":
            assert segment.control_1 is not None and segment.control_2 is not None
            chord = end - current
            first = np.asarray(segment.control_1, dtype=float) - current
            second = np.asarray(segment.control_2, dtype=float) - current
            cross_first = chord[0] * first[1] - chord[1] * first[0]
            cross_second = chord[0] * second[1] - chord[1] * second[0]
            assert max(abs(cross_first), abs(cross_second)) > 1e-6
            cubic_count += 1
        current = end
    assert cubic_count > 0


def _open_path_coordinates(path: OpenPath) -> np.ndarray:
    coordinates = [path.start]
    for segment in path.segments:
        if segment.command == "C":
            assert segment.control_1 is not None and segment.control_2 is not None
            coordinates.extend((segment.control_1, segment.control_2))
        coordinates.append(segment.end)
    return np.asarray(coordinates, dtype=float)


def _iou(first: np.ndarray, second: np.ndarray) -> float:
    intersection = np.count_nonzero(first.astype(bool) & second.astype(bool))
    union = np.count_nonzero(first.astype(bool) | second.astype(bool))
    return intersection / union
