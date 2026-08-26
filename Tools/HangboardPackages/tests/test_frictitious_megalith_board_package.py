from __future__ import annotations

from pathlib import Path

from hangboard_packages.board_catalog import load_board_package


REPO_ROOT = Path(__file__).resolve().parents[3]
PACKAGE_ROOT = REPO_ROOT / "Hangboards" / "frictitious-megalith"
EXPECTED_HOLDS = (
    "top-jug",
    "stepped-8-10-12-left",
    "stepped-8-10-12-right",
    "stepped-30-40-pocket-left",
    "stepped-30-40-pocket-right",
    "center-edge-25",
    "stepped-15-20-left",
    "stepped-15-20-right",
    "mono-left",
    "mono-right",
)


def test_megalith_has_one_record_per_continuous_physical_contact() -> None:
    board = load_board_package(PACKAGE_ROOT).board
    holds = {hold.id: hold for hold in board.holds}

    assert tuple(holds) == EXPECTED_HOLDS
    assert {hold_id: hold.kind for hold_id, hold in holds.items()} == {
        "top-jug": "jug",
        "stepped-8-10-12-left": "edge",
        "stepped-8-10-12-right": "edge",
        "stepped-30-40-pocket-left": "edge",
        "stepped-30-40-pocket-right": "edge",
        "center-edge-25": "edge",
        "stepped-15-20-left": "edge",
        "stepped-15-20-right": "edge",
        "mono-left": "pocket",
        "mono-right": "pocket",
    }
    assert all(len(hold.geometry) == 1 for hold in holds.values())

