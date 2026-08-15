from __future__ import annotations

import json
import re
import sys
from pathlib import Path

import pytest


WORKBENCH_ROOT = Path(__file__).resolve().parents[1]
REPOSITORY_ROOT = Path(__file__).resolve().parents[3]
VALIDATION_FIXTURES = json.loads(
    (
        REPOSITORY_ROOT
        / "HangTenTests"
        / "Fixtures"
        / "BoardPackageValidationFixtures.json"
    ).read_text(encoding="utf-8")
)
sys.path.insert(0, str(WORKBENCH_ROOT))

import board_geometry  # noqa: E402
from board_geometry import (  # noqa: E402
    GeometryError,
    NormalizedFrame,
    display_path_for_shape,
    normalized_frame_for_path,
    parse_closed_path,
    shape_for_path,
)


def test_unions_multiple_normalized_piece_frames() -> None:
    frame = board_geometry.union_normalized_frames(
        (
            NormalizedFrame(x=0.05, y=0.2, width=0.1, height=0.3),
            NormalizedFrame(x=0.35, y=0.1, width=0.1, height=0.2),
        )
    )

    assert frame.to_json() == {
        "x": 0.05,
        "y": 0.1,
        "width": 0.4,
        "height": 0.4,
    }


def test_serialized_normalized_frame_stays_within_canvas_after_rounding() -> None:
    x = 75918 / 91672
    width = (91672 - 75918) / 91672
    assert round(x, 12) + round(width, 12) == 1.000000000001

    serialized = NormalizedFrame(x=x, y=x, width=width, height=width).to_json()

    assert serialized["width"] == 0.17185181953
    assert serialized["height"] == 0.17185181953
    assert json.dumps(serialized, separators=(",", ":")) == (
        '{"x":0.82814818047,"y":0.82814818047,'
        '"width":0.17185181953,"height":0.17185181953}'
    )
    assert serialized["x"] + serialized["width"] <= 1
    assert serialized["y"] + serialized["height"] <= 1
    assert NormalizedFrame.from_json(serialized) == NormalizedFrame(**serialized)


def test_parses_one_closed_contiguous_contour_and_derives_its_frame() -> None:
    path = parse_closed_path("M 10 20 L 50 20 L 50 60 L 10 60 Z", 100, 100)

    assert path.data == "M 10 20 L 50 20 L 50 60 L 10 60 Z"
    assert normalized_frame_for_path(path, 100, 100).to_json() == {
        "x": 0.1,
        "y": 0.2,
        "width": 0.4,
        "height": 0.4,
    }


def test_round_trips_two_cubic_segments_with_controls_outside_the_visual_bounds() -> None:
    path = parse_closed_path(
        "M 20 20 C 0 20 0 80 20 80 C 100 80 100 20 20 20 Z", 100, 100
    )

    frame, shape = shape_for_path(path, 100, 100)

    assert frame.to_json() == {"x": 0.0, "y": 0.2, "width": 1.0, "height": 0.6}
    assert display_path_for_shape(frame.to_json(), shape, 100, 100, label="hold").data == path.data


def test_parses_a_pill_shaped_rounded_rectangle() -> None:
    path = display_path_for_shape(
        {"x": 0.1, "y": 0.1, "width": 0.1, "height": 0.8},
        {"type": "roundedRect", "cornerRadiusFraction": 0.5},
        100,
        100,
        label="pill",
    )

    assert path.data.endswith(" Z")


@pytest.mark.parametrize(
    ("display_path", "message"),
    [
        (
            "M 10 10 L 30 10 L 30 30 L 10 30 Z M 50 50 L 70 50 L 70 70 L 50 70 Z",
            "exactly one closed contour",
        ),
        (
            "M 10 10 L 70 70 L 10 70 L 70 10 Z",
            "self-intersect",
        ),
        (
            "M -1 10 L 30 10 L 30 30 L 10 30 Z",
            "inside the canvas",
        ),
    ],
)
def test_rejects_invalid_hold_geometry(display_path: str, message: str) -> None:
    with pytest.raises(GeometryError, match=message):
        parse_closed_path(display_path, 100, 100)


@pytest.mark.parametrize(
    "fixture",
    VALIDATION_FIXTURES["malformedPathShapes"],
    ids=lambda fixture: fixture["name"],
)
def test_rejects_shared_malformed_package_path_shapes(
    fixture: dict[str, object],
) -> None:
    with pytest.raises(
        GeometryError,
        match=re.escape(str(fixture["expectedMessage"])),
    ):
        display_path_for_shape(
            {"x": 0, "y": 0, "width": 1, "height": 1},
            {"type": "path", "commands": fixture["commands"]},
            100,
            100,
            label=str(fixture["name"]),
        )
