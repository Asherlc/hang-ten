from __future__ import annotations

import json
from pathlib import Path

import pytest


REPO_ROOT = Path(__file__).resolve().parents[3]


def _frame(hold: dict[str, object]) -> dict[str, float]:
    geometry = hold["geometry"]
    assert isinstance(geometry, list)
    assert len(geometry) == 1
    frame = geometry[0]["frame"]
    assert isinstance(frame, dict)
    return frame


def _overlaps(first: dict[str, float], second: dict[str, float]) -> bool:
    return not (
        first["x"] + first["width"] <= second["x"]
        or second["x"] + second["width"] <= first["x"]
        or first["y"] + first["height"] <= second["y"]
        or second["y"] + second["height"] <= first["y"]
    )


def test_moon_armstrong_right_layout_is_source_reviewed_and_collision_free() -> None:
    board = json.loads(
        (REPO_ROOT / "Hangboards" / "moon-armstrong" / "board.json").read_text(
            encoding="utf-8"
        )
    )
    holds = {hold["id"]: hold for hold in board["holds"]}

    assert len(holds) == 21
    expected_right_frames = {
        "jug-right": (0.789, 0.365, 0.15, 0.066289039482),
        "edge-25-right": (0.617, 0.374, 0.15, 0.053031231585),
        "edge-20-right": (0.617, 0.482, 0.15, 0.039),
        "edge-15-right": (0.786, 0.482, 0.156, 0.055152480848),
        "edge-10-right": (0.617, 0.526, 0.15, 0.045),
        "edge-8-right": (0.617, 0.586, 0.15, 0.045),
        "mono-right": (0.799, 0.586, 0.026, 0.036768333333),
        "two-finger-pocket-right": (0.84, 0.586, 0.09, 0.045),
    }
    for hold_id, expected in expected_right_frames.items():
        frame = _frame(holds[hold_id])
        assert (
            frame["x"],
            frame["y"],
            frame["width"],
            frame["height"],
        ) == pytest.approx(expected)

    # Moon's official front is deliberately staggered: it is not a mirrored
    # coordinate layout. Keep the outer jug/15/mono/pocket group apart from
    # the inner 25/20/10/8 stack.
    assert _frame(holds["jug-right"])["x"] != pytest.approx(
        1 - _frame(holds["jug-left"])["x"] - _frame(holds["jug-left"])["width"]
    )
    assert _frame(holds["edge-20-right"])["x"] != pytest.approx(
        1
        - _frame(holds["edge-20-left"])["x"]
        - _frame(holds["edge-20-left"])["width"]
    )

    edge_8 = _frame(holds["edge-8-right"])
    mono = _frame(holds["mono-right"])
    two_finger = _frame(holds["two-finger-pocket-right"])
    assert not _overlaps(edge_8, mono)
    assert not _overlaps(edge_8, two_finger)
    assert not _overlaps(mono, two_finger)
