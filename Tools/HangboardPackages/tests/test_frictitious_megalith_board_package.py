from __future__ import annotations

from pathlib import Path

import pytest

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
EXPECTED_FEATURES = {
    "center-edge-25": ("incutEdge",),
}
RIGHT_BOTTOM_LEFT_BOUND = 0.629300570964
RIGHT_BOTTOM_DIVIDER = 0.719149326172
RIGHT_BOTTOM_RIGHT_BOUND = 0.853922458985
RIGHT_BOTTOM_Y = 0.572587926758
RIGHT_BOTTOM_HEIGHT = 0.056040568359


def test_megalith_has_eighteen_scalar_source_labelled_contacts() -> None:
    board = load_board_package(PACKAGE_ROOT).board

    assert tuple(
        (hold.id, hold.kind, hold.size_millimeters, hold.finger_capacity)
        for hold in board.holds
    ) == EXPECTED_HOLDS
    assert all(hold.depth_range_millimeters is None for hold in board.holds)
    assert all(len(hold.geometry) == 1 for hold in board.holds)
    assert {
        hold.id: tuple(hold.features)
        for hold in board.holds
        if hold.features is not None
    } == EXPECTED_FEATURES
    assert {
        hold.id: hold.hand_capacity
        for hold in board.holds
        if hold.hand_capacity is not None
    } == {"center-edge-25": 1}
    assert all(hold.grip_type is None for hold in board.holds)


def test_megalith_right_bottom_shelves_follow_the_asymmetric_source_footprint() -> None:
    holds = {hold.id: hold for hold in load_board_package(PACKAGE_ROOT).board.holds}
    edge_20 = holds["edge-20-right"].frame
    edge_15 = holds["edge-15-right"].frame
    mono = holds["mono-right"].frame

    assert edge_20.x == pytest.approx(RIGHT_BOTTOM_LEFT_BOUND, abs=1e-12)
    assert edge_20.x + edge_20.width == pytest.approx(RIGHT_BOTTOM_DIVIDER, abs=1e-12)
    assert edge_15.x == pytest.approx(RIGHT_BOTTOM_DIVIDER, abs=1e-12)
    assert edge_15.x + edge_15.width == pytest.approx(RIGHT_BOTTOM_RIGHT_BOUND, abs=1e-12)
    assert edge_20.y == edge_15.y == pytest.approx(RIGHT_BOTTOM_Y, abs=1e-12)
    assert edge_20.height == edge_15.height == pytest.approx(RIGHT_BOTTOM_HEIGHT, abs=1e-12)
    # The source cavity ends before the distinct mono cavity starts, so their
    # frames cannot share an interior point.
    assert edge_15.x + edge_15.width < mono.x
