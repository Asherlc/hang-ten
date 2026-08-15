from __future__ import annotations

from pathlib import Path

import pytest

from hangboard_vectorizer.board_catalog import load_board_package


REPO_ROOT = Path(__file__).resolve().parents[3]
PACKAGE_ROOT = REPO_ROOT / "Hangboards" / "lattice-triple-rung"
EXPECTED_HOLDS = (
    ("edge-45", "edge", 45, (0.046875, 0.328125, 0.90625, 0.044922)),
    ("edge-10", "edge", 10, (0.035156, 0.467773, 0.929688, 0.054688)),
    ("edge-20", "edge", 20, (0.029297, 0.594727, 0.941406, 0.06543)),
)


def test_lattice_triple_rung_has_three_exact_continuous_edge_regions() -> None:
    board = load_board_package(PACKAGE_ROOT).board

    assert board.id == "lattice-triple-rung"
    assert board.manufacturer == "Lattice Training"
    assert board.name == "Triple Rung"
    assert board.facts["dimensions"] == "55 × 13 × 5 cm"
    assert board.facts["aspectRatio"] == 55 / 13
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
        assert len(piece.shape.commands) >= 8
        assert piece.frame.width * piece.frame.height > 0.04
        assert piece.frame.x >= 0
        assert piece.frame.y >= 0
        assert piece.frame.x + piece.frame.width <= 1
        assert piece.frame.y + piece.frame.height <= 1
        assert hold.depth_range_millimeters is None
        assert hold.grip_type is None
        assert hold.finger_capacity is None
        assert hold.features is None
