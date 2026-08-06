from __future__ import annotations

from dataclasses import FrozenInstanceError

import cv2
import numpy as np
import pytest

from hangboard_vectorizer.geometry import Opening
from hangboard_vectorizer.regions import GripRegion, build_regions


def test_build_regions_classifies_pocket_slot_and_rail():
    openings = (
        _opening_from_circle((120, 100), radius=20),
        _opening_from_rectangle((260, 90), (320, 110)),
        _opening_from_rectangle((500, 180), (720, 200)),
    )

    layout = build_regions(openings, board_width=1_000, board_height=500)

    assert [region.type for region in layout.regions] == ["pocket", "slot", "rail", "rail"]
    assert all(not region.disabled for region in layout.regions)
    assert all(region.source == "automatic" for region in layout.regions)


def test_region_layout_records_are_frozen_slotted_and_opening_id_defaults_empty():
    opening = _opening_from_circle((120, 100), radius=20)

    layout = build_regions((opening,), board_width=1_000, board_height=500)

    assert opening.id == ""
    assert not hasattr(layout, "__dict__")
    assert not hasattr(layout.regions[0], "__dict__")
    with pytest.raises(FrozenInstanceError):
        layout.regions[0].disabled = True  # type: ignore[misc]


def test_grip_region_accepts_template_semantics_without_changing_legacy_defaults():
    """Template regions need semantic attributes while automatic regions retain defaults."""
    region = GripRegion(
        id="jug-left",
        opening_id="",
        type="jug",  # type: ignore[arg-type]
        side="left",
        contour=np.array([[0.0, 0.0], [1.0, 0.0], [0.0, 1.0]]),
        center=(0.5, 0.5),
        bbox=(0, 0, 1, 1),
        source="template",  # type: ignore[arg-type]
        label="Left jug",
        metadata=(("fingerCount", 4),),
    )

    assert (region.source, region.label, region.metadata) == (
        "template",
        "Left jug",
        (("fingerCount", 4),),
    )


def test_build_regions_classifies_degenerate_opening_as_unknown():
    degenerate = Opening(
        contour=np.array([[10.0, 20.0], [10.0, 20.0]]),
        center=(10.0, 20.0),
        bbox=(10, 20, 0, 0),
        area=0.0,
        aspect_ratio=0.0,
    )

    layout = build_regions((degenerate,), board_width=1_000, board_height=500)

    assert [region.type for region in layout.regions] == ["unknown"]


def test_build_regions_splits_rail_into_opposite_sides_that_preserve_area():
    rail = _opening_from_rectangle((500, 180), (720, 200))

    layout = build_regions((rail,), board_width=1_000, board_height=500)

    assert [region.side for region in layout.regions] == ["left", "right"]
    split_x = rail.bbox[0] + rail.bbox[2] // 2
    assert all(point[0] < split_x for point in layout.regions[0].contour)
    assert all(point[0] >= split_x for point in layout.regions[1].contour)
    original_area = _raster_area((rail.contour,), rail.bbox)
    split_area = _raster_area(
        tuple(region.contour for region in layout.regions), rail.bbox
    )
    assert split_area / original_area >= 0.95


def test_build_regions_assigns_stable_row_major_ids_independent_of_input_order():
    pocket = _opening_from_circle((150, 100), radius=20)
    rail = _opening_from_rectangle((600, 90), (820, 110))
    slot = _opening_from_rectangle((400, 300), (460, 320))

    first = build_regions((slot, rail, pocket), board_width=1_000, board_height=500)
    second = build_regions((pocket, slot, rail), board_width=1_000, board_height=500)

    expected_ids = [
        "r01-h01-pocket",
        "r01-h02-rail-left",
        "r01-h02-rail-right",
        "r02-h01-slot",
    ]
    assert [region.id for region in first.regions] == expected_ids
    assert [opening.id for opening in first.openings] == ["r01-h01", "r01-h02", "r02-h01"]
    assert [(region.id, region.center) for region in second.regions] == [
        (region.id, region.center) for region in first.regions
    ]


def _opening_from_circle(center: tuple[int, int], *, radius: int) -> Opening:
    mask = np.zeros((500, 1_000), dtype=np.uint8)
    cv2.circle(mask, center, radius, 1, thickness=-1)
    return _opening_from_mask(mask)


def _opening_from_rectangle(
    top_left: tuple[int, int], bottom_right: tuple[int, int]
) -> Opening:
    mask = np.zeros((500, 1_000), dtype=np.uint8)
    cv2.rectangle(mask, top_left, bottom_right, 1, thickness=-1)
    return _opening_from_mask(mask)


def _opening_from_mask(mask: np.ndarray) -> Opening:
    contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    contour = contours[0]
    x, y, width, height = cv2.boundingRect(contour)
    moments = cv2.moments(contour)
    return Opening(
        contour=contour.reshape(-1, 2).astype(float),
        center=(moments["m10"] / moments["m00"], moments["m01"] / moments["m00"]),
        bbox=(x, y, width, height),
        area=float(cv2.contourArea(contour)),
        aspect_ratio=width / height,
    )


def _raster_area(contours: tuple[np.ndarray, ...], bbox: tuple[int, int, int, int]) -> int:
    x, y, width, height = bbox
    mask = np.zeros((height, width), dtype=np.uint8)
    shifted = tuple(
        np.rint(contour - np.array([x, y])).astype(np.int32) for contour in contours
    )
    cv2.drawContours(mask, list(shifted), -1, 1, thickness=-1)
    return int(mask.sum())
