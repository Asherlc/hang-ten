from __future__ import annotations

import cv2
import numpy as np
import pytest

from hangboard_vectorizer.overrides import apply_overrides
from hangboard_vectorizer.regions import GripRegion


BOARD_WIDTH = 100
BOARD_HEIGHT = 60


def test_apply_overrides_renames_and_disables_regions_first():
    regions = (_region("pocket-a", (10, 10), (30, 30)), _region("slot-b", (50, 10), (80, 25)))
    document = {
        "version": 1,
        "rename": {"pocket-a": "warmup-pocket"},
        "disable": ["slot-b"],
    }

    result = apply_overrides(regions, document, BOARD_WIDTH, BOARD_HEIGHT)

    assert [region.id for region in result] == ["warmup-pocket", "slot-b"]
    assert [region.disabled for region in result] == [False, True]


def test_apply_overrides_splits_a_region_by_relative_x_ranges():
    region = _region("rail", (10, 10), (90, 30), region_type="rail", side="left")
    document = {
        "version": 1,
        "split": {
            "rail": [
                {"id": "rail-inner", "xRange": [0.0, 0.5]},
                {"id": "rail-outer", "xRange": [0.5, 1.0]},
            ]
        },
    }

    result = apply_overrides((region,), document, BOARD_WIDTH, BOARD_HEIGHT)

    assert [item.id for item in result] == ["rail-inner", "rail-outer"]
    assert max(result[0].contour[:, 0]) < min(result[1].contour[:, 0])
    assert all(item.opening_id == "opening-1" for item in result)
    assert all(item.type == "rail" for item in result)


def test_apply_overrides_merges_regions_by_raster_union():
    left = _region("left", (10, 10), (50, 30), region_type="rail", side="left")
    right = _region("right", (50, 10), (90, 30), region_type="rail", side="right")
    document = {
        "version": 1,
        "merge": [{"ids": ["left", "right"], "id": "combined"}],
    }

    result = apply_overrides((left, right), document, BOARD_WIDTH, BOARD_HEIGHT)

    assert [item.id for item in result] == ["combined"]
    assert result[0].bbox == (10, 10, 81, 21)
    assert result[0].center == pytest.approx((50.0, 20.0))
    assert result[0].side is None


def test_apply_overrides_preserves_every_disconnected_merge_component():
    left = _region("left", (10, 10), (30, 30))
    right = _region("right", (70, 10), (90, 30))

    (merged,) = apply_overrides(
        (left, right),
        {"version": 1, "merge": [{"ids": ["left", "right"], "id": "combined"}]},
        BOARD_WIDTH,
        BOARD_HEIGHT,
    )

    component_boxes = sorted(cv2.boundingRect(contour.astype(np.int32)) for contour in merged.contours)
    assert component_boxes == [(10, 10, 21, 21), (70, 10, 21, 21)]


def test_apply_overrides_split_clips_composite_region_components():
    left = _region("left", (10, 10), (30, 30))
    right = _region("right", (70, 10), (90, 30))
    (composite,) = apply_overrides(
        (left, right),
        {"version": 1, "merge": [{"ids": ["left", "right"], "id": "combined"}]},
        BOARD_WIDTH,
        BOARD_HEIGHT,
    )

    (left_piece,) = apply_overrides(
        (composite,),
        {
            "version": 1,
            "split": {"combined": [{"id": "left-piece", "xRange": [0.0, 0.5]}]},
        },
        BOARD_WIDTH,
        BOARD_HEIGHT,
    )

    assert left_piece.bbox == (10, 10, 21, 21)
    assert left_piece.contours == ()


def test_apply_overrides_uses_original_identity_after_rename_collision():
    renamed_source = _region("a", (5, 10), (15, 30))
    merge_left = _region("b", (30, 10), (50, 30))
    merge_right = _region("c", (50, 10), (70, 30))
    document = {
        "version": 1,
        "rename": {"a": "b"},
        "merge": [{"ids": ["b", "c"], "id": "combined"}],
    }

    result = apply_overrides(
        (renamed_source, merge_left, merge_right),
        document,
        BOARD_WIDTH,
        BOARD_HEIGHT,
    )

    assert [region.id for region in result] == ["b", "combined"]
    assert result[0].bbox == (5, 10, 11, 21)
    assert result[1].bbox == (30, 10, 41, 21)


def test_apply_overrides_adds_a_scaled_normalized_polygon():
    document = {
        "version": 1,
        "add": [
            {
                "id": "hidden-edge",
                "type": "unknown",
                "polygon": [[0.1, 0.1], [0.2, 0.1], [0.2, 0.2], [0.1, 0.2]],
            }
        ],
    }

    (added,) = apply_overrides((), document, BOARD_WIDTH, BOARD_HEIGHT)

    assert added.id == "hidden-edge"
    assert added.source == "override"
    assert added.opening_id == ""
    assert added.side is None
    assert added.contour.tolist() == [[10.0, 6.0], [20.0, 6.0], [20.0, 12.0], [10.0, 12.0]]


@pytest.mark.parametrize(
    "region_type", ["pocket", "edge", "rail", "jug", "sloper", "slot", "unknown"]
)
def test_apply_overrides_add_accepts_every_supported_region_type(region_type):
    """Override additions must accept the full semantic and legacy type union."""
    document = {
        "version": 1,
        "add": [
            {
                "id": "added-region",
                "type": region_type,
                "polygon": [[0.1, 0.1], [0.3, 0.1], [0.2, 0.3]],
            }
        ],
    }

    (added,) = apply_overrides((), document, BOARD_WIDTH, BOARD_HEIGHT)

    assert added.type == region_type


@pytest.mark.parametrize(
    "operation",
    [
        {"rename": {"missing": "renamed"}},
        {"disable": ["missing"]},
        {"split": {"missing": [{"id": "piece", "xRange": [0.0, 1.0]}]}},
        {"merge": [{"ids": ["known", "missing"], "id": "combined"}]},
    ],
)
def test_apply_overrides_rejects_unknown_source_selectors(operation):
    document = {"version": 1, **operation}

    with pytest.raises(ValueError, match="unknown region"):
        apply_overrides((_region("known", (10, 10), (30, 30)),), document, BOARD_WIDTH, BOARD_HEIGHT)


@pytest.mark.parametrize(
    "document",
    [
        {"version": 1, "rename": {"first": "second"}},
        {
            "version": 1,
            "split": {"first": [{"id": "second", "xRange": [0.0, 1.0]}]},
        },
        {
            "version": 1,
            "merge": [{"ids": ["first", "third"], "id": "second"}],
        },
        {
            "version": 1,
            "add": [
                {
                    "id": "second",
                    "type": "unknown",
                    "polygon": [[0.1, 0.1], [0.2, 0.1], [0.2, 0.2]],
                }
            ],
        },
    ],
)
def test_apply_overrides_rejects_duplicate_final_ids(document):
    regions = (
        _region("first", (10, 10), (30, 30)),
        _region("second", (50, 10), (70, 30)),
        _region("third", (75, 10), (90, 30)),
    )

    with pytest.raises(ValueError, match="duplicate region ID"):
        apply_overrides(regions, document, BOARD_WIDTH, BOARD_HEIGHT)


@pytest.mark.parametrize(
    "x_range",
    [[-0.1, 0.5], [0.5, 1.1], [0.5, 0.5], [0.75, 0.25], [0.0]],
)
def test_apply_overrides_rejects_invalid_split_ranges(x_range):
    document = {
        "version": 1,
        "split": {"known": [{"id": "piece", "xRange": x_range}]},
    }

    with pytest.raises(ValueError, match="xRange"):
        apply_overrides((_region("known", (10, 10), (30, 30)),), document, BOARD_WIDTH, BOARD_HEIGHT)


@pytest.mark.parametrize("coordinate", [-0.01, 1.01])
def test_apply_overrides_rejects_polygons_outside_normalized_canvas(coordinate):
    document = {
        "version": 1,
        "add": [
            {
                "id": "outside",
                "type": "unknown",
                "polygon": [[coordinate, 0.1], [0.2, 0.1], [0.2, 0.2]],
            }
        ],
    }

    with pytest.raises(ValueError, match="polygon"):
        apply_overrides((), document, BOARD_WIDTH, BOARD_HEIGHT)


def test_apply_overrides_rejects_an_unsupported_version():
    with pytest.raises(ValueError, match="version"):
        apply_overrides((), {"version": 2}, BOARD_WIDTH, BOARD_HEIGHT)


def test_apply_overrides_rejects_boolean_version():
    with pytest.raises(ValueError, match="version"):
        apply_overrides((), {"version": True}, BOARD_WIDTH, BOARD_HEIGHT)


@pytest.mark.parametrize(
    "polygon",
    [
        [[0.1, 0.1], [0.3, 0.1], [0.3, 0.3], [0.1, 0.1]],
        [[0.1, 0.1], [0.2, 0.2], [0.3, 0.3]],
    ],
)
def test_apply_overrides_rejects_repeated_or_zero_area_polygons(polygon):
    document = {
        "version": 1,
        "add": [{"id": "invalid", "type": "edge", "polygon": polygon}],
    }

    with pytest.raises(ValueError, match="polygon"):
        apply_overrides((), document, BOARD_WIDTH, BOARD_HEIGHT)


def test_apply_overrides_rejects_overlapping_operations_on_one_source():
    document = {
        "version": 1,
        "rename": {"known": "renamed"},
        "disable": ["known"],
    }

    with pytest.raises(ValueError, match="multiple operations"):
        apply_overrides((_region("known", (10, 10), (30, 30)),), document, BOARD_WIDTH, BOARD_HEIGHT)


@pytest.mark.parametrize("invalid_id", ["1region", "has space", "has.period", ""])
def test_apply_overrides_rejects_ids_that_are_unsafe_for_svg_selectors(invalid_id):
    document = {
        "version": 1,
        "add": [
            {
                "id": invalid_id,
                "type": "unknown",
                "polygon": [[0.1, 0.1], [0.2, 0.1], [0.2, 0.2]],
            }
        ],
    }

    with pytest.raises(ValueError, match="invalid region ID"):
        apply_overrides((), document, BOARD_WIDTH, BOARD_HEIGHT)


def _region(
    region_id: str,
    top_left: tuple[int, int],
    bottom_right: tuple[int, int],
    *,
    region_type: str = "pocket",
    side: str | None = None,
) -> GripRegion:
    contour = np.array(
        [
            top_left,
            (bottom_right[0], top_left[1]),
            bottom_right,
            (top_left[0], bottom_right[1]),
        ],
        dtype=float,
    )
    integer_contour = np.rint(contour).astype(np.int32)
    x, y, width, height = cv2.boundingRect(integer_contour)
    moments = cv2.moments(integer_contour)
    return GripRegion(
        id=region_id,
        opening_id="opening-1",
        type=region_type,
        side=side,
        contour=contour,
        center=(moments["m10"] / moments["m00"], moments["m01"] / moments["m00"]),
        bbox=(x, y, width, height),
    )
