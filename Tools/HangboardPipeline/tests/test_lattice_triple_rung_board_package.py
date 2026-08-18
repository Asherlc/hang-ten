from __future__ import annotations

from pathlib import Path

import pytest

from hangboard_vectorizer.board_catalog import load_board_package


REPO_ROOT = Path(__file__).resolve().parents[3]
PACKAGE_ROOT = REPO_ROOT / "Hangboards" / "lattice-triple-rung"
EXPECTED_HOLDS = (
    ("edge-45", "edge", 45, (0.046875, 0.328125, 0.90625, 0.04357434), ("largeEdge",)),
    ("edge-10", "edge", 10, (0.035156, 0.46941354729647444, 0.929688, 0.05140681270352551), ("smallEdge",)),
    ("edge-20", "edge", 20, (0.029297, 0.5973440890873374, 0.941406, 0.06085001091266235), ("mediumEdge",)),
)


def test_lattice_triple_rung_has_three_exact_continuous_edge_regions() -> None:
    board = load_board_package(PACKAGE_ROOT).board

    assert board.id == "lattice-triple-rung"
    assert board.manufacturer == "Lattice Training"
    assert board.name == "Triple Rung"
    assert board.facts["dimensions"] == "55 × 13 × 5 cm"
    # aspectRatio is the presentation canvas ratio (matches primary.png's
    # actual pixel dimensions), not the physical product envelope.
    assert board.facts["aspectRatio"] == 1.5
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
        # Frames were retightened to their path's exact flattened bounds
        # (see "Fix hold geometry bounds and aspect-ratio metadata
        # mismatches"), so this is a sanity floor, not a precise figure.
        assert piece.frame.width * piece.frame.height > 0.03
        assert piece.frame.x >= 0
        assert piece.frame.y >= 0
        assert piece.frame.x + piece.frame.width <= 1
        assert piece.frame.y + piece.frame.height <= 1
        assert hold.depth_range_millimeters is None
        # Each edge has a sourced sizeMillimeters, so it also carries derived
        # gripType/fingerCapacity/features. See "Add sourced hold
        # depth/feature metadata for 4 new boards".
        assert hold.grip_type == "openHand"
        assert hold.finger_capacity == 4
        assert set(hold.features) == set(expected[4])
