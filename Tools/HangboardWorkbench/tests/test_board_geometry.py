from __future__ import annotations

import sys
from pathlib import Path

import pytest


WORKBENCH_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(WORKBENCH_ROOT))

from board_geometry import GeometryError, normalized_frame_for_path, parse_closed_path  # noqa: E402


def test_parses_one_closed_contiguous_contour_and_derives_its_frame() -> None:
    path = parse_closed_path("M 10 20 L 50 20 L 50 60 L 10 60 Z", 100, 100)

    assert path.data == "M 10 20 L 50 20 L 50 60 L 10 60 Z"
    assert normalized_frame_for_path(path, 100, 100).to_json() == {
        "x": 0.1,
        "y": 0.2,
        "width": 0.4,
        "height": 0.4,
    }


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
