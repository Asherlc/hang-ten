from __future__ import annotations

from pathlib import Path

import pytest
from PIL import Image

from hangboard_vectorizer.board_catalog import load_board_package


REPO_ROOT = Path(__file__).resolve().parents[3]
PACKAGE_ROOT = REPO_ROOT / "Hangboards" / "lattice-triple-rung"
EXPECTED_HOLDS = (
    ("edge-45", "edge", 45, ("largeEdge",)),
    ("edge-10", "edge", 10, ("smallEdge",)),
    ("edge-20", "edge", 20, ("mediumEdge",)),
)


def test_lattice_triple_rung_has_three_exact_continuous_edge_regions() -> None:
    board = load_board_package(PACKAGE_ROOT).board

    assert board.id == "lattice-triple-rung"
    assert board.manufacturer == "Lattice Training"
    assert board.name == "Triple Rung"
    assert board.facts["dimensions"] == "55 × 13 × 5 cm"
    assert board.presentation_asset_path == "assets/primary.png"
    with Image.open(PACKAGE_ROOT / board.presentation_asset_path) as image:
        presentation_size = image.size
    # aspectRatio is the presentation canvas ratio, not the physical product
    # envelope, so it must follow the runtime presentation asset dimensions.
    assert board.facts["aspectRatio"] == pytest.approx(
        presentation_size[0] / presentation_size[1]
    )
    assert tuple(
        (hold.id, hold.kind, hold.size_millimeters) for hold in board.holds
    ) == tuple(expected[:3] for expected in EXPECTED_HOLDS)

    edge_frames = []
    for hold, expected in zip(board.holds, EXPECTED_HOLDS, strict=True):
        assert len(hold.geometry) == 1
        piece = hold.geometry[0]
        assert piece.shape.type == "path"
        assert piece.shape.commands[0].command == "move"
        assert piece.shape.commands[-1].command == "close"
        assert len(piece.shape.commands) >= 8
        frame_width = piece.frame.width * presentation_size[0]
        frame_height = piece.frame.height * presentation_size[1]
        # A continuous rung occupies the overwhelming majority of the
        # presentation width rather than being split into separate grips.
        assert frame_width >= presentation_size[0] * 0.9
        # The source board is rendered at 512 px tall; a rung shorter than
        # 20 px would be too small to preserve as an independently editable
        # continuous edge region.
        assert frame_height >= 20
        assert piece.frame.x >= 0
        assert piece.frame.y >= 0
        assert piece.frame.x + piece.frame.width <= 1
        assert piece.frame.y + piece.frame.height <= 1
        edge_frames.append(piece.frame)
        assert hold.depth_range_millimeters is None
        # Each edge has a sourced sizeMillimeters, so it also carries derived
        # gripType/fingerCapacity/features. See "Add sourced hold
        # depth/feature metadata for 4 new boards".
        assert hold.grip_type == "openHand"
        assert hold.finger_capacity == 4
        assert set(hold.features) == set(expected[3])

    assert edge_frames[0].y + edge_frames[0].height < edge_frames[1].y
    assert edge_frames[1].y + edge_frames[1].height < edge_frames[2].y
