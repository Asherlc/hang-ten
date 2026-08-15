from __future__ import annotations

from pathlib import Path

import pytest

from hangboard_vectorizer.board_catalog import load_board_package


REPO_ROOT = Path(__file__).resolve().parents[3]
PACKAGE_ROOT = REPO_ROOT / "Hangboards" / "evolv-kilter-basic-long"
EXPECTED_HOLDS = (
    ("rounded-jug", "jug", None, (0.055, 0.391, 0.89, 0.117)),
    ("rounded-edge-20", "edge", 20, (0.056, 0.535, 0.888, 0.028)),
    ("rounded-edge-15", "edge", 15, (0.057, 0.594, 0.886, 0.027)),
    ("rounded-edge-10", "edge", 10, (0.057, 0.655, 0.886, 0.031)),
)


def test_evolv_kilter_basic_long_has_four_continuous_rounded_contacts() -> None:
    board = load_board_package(PACKAGE_ROOT).board

    assert board.id == "evolv-kilter-basic-long"
    assert board.manufacturer == "Evolv"
    assert board.name == "Basic Training Board (Long)"
    assert board.facts["dimensions"] == "79 × 16 × 6 cm"
    assert board.facts["aspectRatio"] == 79 / 16
    assert board.presentation_asset_path == "assets/primary.png"
    assert tuple(
        (hold.id, hold.kind, hold.size_millimeters) for hold in board.holds
    ) == tuple(expected[:3] for expected in EXPECTED_HOLDS)

    for hold, expected in zip(board.holds, EXPECTED_HOLDS, strict=True):
        assert len(hold.geometry) == 1
        piece = hold.geometry[0]
        assert (
            piece.frame.x,
            piece.frame.y,
            piece.frame.width,
            piece.frame.height,
        ) == pytest.approx(expected[3], abs=1e-9)
        assert piece.shape.type == "path"
        assert piece.shape.commands[0].command == "move"
        assert piece.shape.commands[-1].command == "close"
        assert sum(command.command == "curve" for command in piece.shape.commands) >= 4
        assert piece.frame.width * piece.frame.height > 0
        assert piece.frame.x == pytest.approx(1 - piece.frame.x - piece.frame.width)
        assert piece.treatment == {"type": "surface"}
        assert hold.depth_range_millimeters is None
        assert hold.grip_type is None
        assert hold.finger_capacity is None
        assert hold.features is None
