from __future__ import annotations

import numpy as np
import cv2
import pytest

from fixtures import make_hangboard, perspective_distort
from hangboard_vectorizer.geometry import (
    Opening,
    RectifiedBoard,
    detect_openings,
    isolate_board,
    rectify_board,
)
from hangboard_vectorizer.models import ConversionError


def test_pipeline_records_keep_rectified_pixel_geometry():
    board = RectifiedBoard(
        rgb=np.zeros((20, 30, 3), dtype=np.uint8),
        mask=np.ones((20, 30), dtype=bool),
        width=30,
        height=20,
    )
    opening = Opening(
        contour=np.array([[2.0, 3.0], [4.0, 5.0]], dtype=float),
        center=(3.0, 4.0),
        bbox=(2, 3, 3, 3),
        area=4.5,
        aspect_ratio=1.0,
    )

    assert board.warnings == ()
    assert opening.contour.shape == (2, 2)
    assert opening.center == (3.0, 4.0)


def test_isolate_board_keeps_board_and_excludes_background():
    mask = isolate_board(make_hangboard())

    assert mask.dtype == bool
    assert mask[150, 200]
    assert not any((mask[0, 0], mask[0, -1], mask[-1, 0], mask[-1, -1]))
    component_count, _, stats, _ = cv2.connectedComponentsWithStats(mask.astype(np.uint8))
    assert component_count == 2
    assert stats[1, cv2.CC_STAT_AREA] > 50_000


def test_isolate_board_rejects_uniform_background():
    white = np.full((100, 100, 3), 255, dtype=np.uint8)

    with pytest.raises(ConversionError, match="could not isolate"):
        isolate_board(white)


def test_isolate_board_rejects_zero_sized_image():
    rgb = np.empty((0, 0, 3), dtype=np.uint8)

    with pytest.raises(ConversionError, match="could not isolate"):
        isolate_board(rgb)


def test_rectify_board_restores_distorted_board_ratio():
    distorted = perspective_distort(make_hangboard())

    rectified = rectify_board(distorted, isolate_board(distorted))

    assert rectified.width / rectified.height == pytest.approx(1.4, rel=0.08)
    assert rectified.mask[rectified.height // 2, rectified.width // 2]


@pytest.mark.parametrize("angle", [44.9, 45.0, 46.0, 73.0, 134.0])
def test_rectify_board_keeps_long_axis_horizontal_at_arbitrary_rotations(angle):
    """Sum/difference corner extrema duplicate or flip corners around 45 degrees."""
    rgb = np.full((500, 500, 3), 180, dtype=np.uint8)
    mask = np.zeros((500, 500), dtype=np.uint8)
    corners = cv2.boxPoints(((250.0, 250.0), (260.0, 80.0), angle))
    cv2.fillConvexPoly(mask, np.rint(corners).astype(np.int32), 1)

    rectified = rectify_board(rgb, mask.astype(bool))

    assert rectified.width > rectified.height
    assert rectified.width / rectified.height == pytest.approx(260 / 80, rel=0.08)


def test_rectify_board_keeps_perspective_board_long_axis_horizontal():
    """Cyclic perspective corners must stay unique and map the board length to width."""
    rgb = np.full((500, 500, 3), 180, dtype=np.uint8)
    mask = np.zeros((500, 500), dtype=np.uint8)
    unrotated = np.array(
        [[120.0, 170.0], [370.0, 145.0], [355.0, 235.0], [130.0, 245.0]],
        dtype=np.float32,
    )
    rotation = cv2.getRotationMatrix2D((250.0, 200.0), 63.0, 1.0)
    corners = cv2.transform(unrotated.reshape(1, -1, 2), rotation).reshape(-1, 2)
    cv2.fillConvexPoly(mask, np.rint(corners).astype(np.int32), 1)

    rectified = rectify_board(rgb, mask.astype(bool))

    assert rectified.width > rectified.height
    assert rectified.width / rectified.height == pytest.approx(2.8, rel=0.12)


def test_rectify_board_uses_minimum_area_rectangle_for_rounded_contour():
    rgb = np.full((200, 200, 3), 200, dtype=np.uint8)
    mask = np.zeros((200, 200), dtype=bool)
    cv2.circle(mask, (100, 100), 70, 1, thickness=-1)

    rectified = rectify_board(rgb, mask)

    assert "minimum-area rectangle fallback" in rectified.warnings


def test_rectify_board_keeps_foreground_beyond_an_inscribed_quadrilateral():
    rgb = np.full((500, 900, 3), 245, dtype=np.uint8)
    mask = np.zeros((500, 900), dtype=np.uint8)
    base = np.array(((100, 180), (800, 180), (750, 360), (150, 360)), dtype=np.int32)
    cv2.fillConvexPoly(mask, base, 1)
    rgb[mask.astype(bool)] = (100, 50, 20)
    for center, color in zip(
        ((250, 180), (650, 180), (115, 260)),
        ((255, 0, 0), (0, 255, 0), (0, 0, 255)),
        strict=True,
    ):
        protrusion = np.zeros_like(mask)
        cv2.circle(protrusion, center, 16, 1, -1)
        outside_base = protrusion.astype(bool) & ~mask.astype(bool)
        mask |= protrusion
        rgb[outside_base] = color

    rectified = rectify_board(rgb, mask.astype(bool))

    assert np.any((rectified.rgb[..., 0] > 200) & (rectified.rgb[..., 1] < 30))
    assert np.any((rectified.rgb[..., 1] > 200) & (rectified.rgb[..., 2] < 30))
    assert np.any((rectified.rgb[..., 2] > 200) & (rectified.rgb[..., 0] < 30))


def test_rectify_board_rejects_zero_sized_image():
    rgb = np.empty((0, 0, 3), dtype=np.uint8)
    mask = np.ones((2, 2), dtype=bool)

    with pytest.raises(ConversionError, match="could not rectify"):
        rectify_board(rgb, mask)


def test_detect_openings_finds_pockets_and_rail_without_board_edge():
    rgb = make_hangboard()
    board = rectify_board(rgb, isolate_board(rgb))

    openings = detect_openings(board)

    assert len(openings) == 3
    assert max(opening.aspect_ratio for opening in openings) > 3.0
    assert all(
        x > 0 and y > 0 and x + width < board.width and y + height < board.height
        for x, y, width, height in (opening.bbox for opening in openings)
    )


def test_detect_openings_rejects_board_without_dark_features():
    board = RectifiedBoard(
        rgb=np.full((100, 140, 3), (196, 148, 94), dtype=np.uint8),
        mask=np.ones((100, 140), dtype=bool),
        width=140,
        height=100,
    )

    with pytest.raises(ConversionError, match="no openings"):
        detect_openings(board)


def test_detect_openings_rejects_zero_sized_board():
    board = RectifiedBoard(
        rgb=np.empty((0, 0, 3), dtype=np.uint8),
        mask=np.empty((0, 0), dtype=bool),
        width=0,
        height=0,
    )

    with pytest.raises(ConversionError, match="could not detect openings"):
        detect_openings(board)
