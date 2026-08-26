from __future__ import annotations

from pathlib import Path

from hangboard_packages.board_catalog import load_board_package


REPO_ROOT = Path(__file__).resolve().parents[3]
PACKAGE_ROOT = REPO_ROOT / "Hangboards" / "frictitious-megalith"
EXPECTED_HOLDS = (
    ("top-jug", "jug", None, None),
    ("center-edge-25", "edge", 25, None),
    ("mono-left", "pocket", None, 1),
    ("mono-right", "pocket", None, 1),
    ("edge-8-left", "edge", 8, None),
    ("edge-10-left", "edge", 10, None),
    ("edge-12-left", "edge", 12, None),
    ("edge-12-right", "edge", 12, None),
    ("edge-10-right", "edge", 10, None),
    ("edge-8-right", "edge", 8, None),
    ("edge-30-left", "edge", 30, None),
    ("edge-40-pocket-left", "edge", 40, None),
    ("edge-40-pocket-right", "edge", 40, None),
    ("edge-30-right", "edge", 30, None),
    ("edge-15-left", "edge", 15, None),
    ("edge-20-left", "edge", 20, None),
    ("edge-20-right", "edge", 20, None),
    ("edge-15-right", "edge", 15, None),
)


def test_megalith_has_eighteen_scalar_source_labelled_contacts() -> None:
    board = load_board_package(PACKAGE_ROOT).board

    assert tuple(
        (hold.id, hold.kind, hold.size_millimeters, hold.finger_capacity)
        for hold in board.holds
    ) == EXPECTED_HOLDS
    assert all(hold.depth_range_millimeters is None for hold in board.holds)
    assert all(len(hold.geometry) == 1 for hold in board.holds)
