from __future__ import annotations

import json
from pathlib import Path


REPOSITORY_ROOT = Path(__file__).resolve().parents[3]


def _board(slug: str) -> dict[str, object]:
    return json.loads(
        (REPOSITORY_ROOT / "Hangboards" / slug / "board.json").read_text(
            encoding="utf-8"
        )
    )


def _depth_inventory(slug: str) -> dict[str, int]:
    board = _board(slug)
    return {
        hold["id"]: hold["sizeMillimeters"]
        for hold in board["holds"]
        if "sizeMillimeters" in hold
    }


def test_grindstone_discrete_steps_are_individual_scalar_depth_holds() -> None:
    board = _board("tension-grindstone")

    assert len(board["holds"]) == 14
    assert _depth_inventory("tension-grindstone") == {
        "edge-10-left": 10,
        "edge-8-left": 8,
        "edge-10-right": 10,
        "edge-8-right": 8,
        "edge-30-left": 30,
        "edge-25-left": 25,
        "edge-30-right": 30,
        "edge-25-right": 25,
        "edge-50-center": 50,
        "edge-20-left": 20,
        "edge-15-left": 15,
        "edge-20-right": 20,
        "edge-15-right": 15,
    }
    assert all("depthRangeMillimeters" not in hold for hold in board["holds"])


def test_honestone_discrete_steps_are_individual_scalar_depth_holds() -> None:
    board = _board("tension-honestone")

    assert len(board["holds"]) == 12
    assert _depth_inventory("tension-honestone") == {
        "mono-left": 25,
        "mono-right": 25,
        "edge-20-left": 20,
        "edge-15-left": 15,
        "edge-20-right": 20,
        "edge-15-right": 15,
        "edge-25-center": 25,
        "edge-10-left": 10,
        "edge-8-left": 8,
        "edge-10-right": 10,
        "edge-8-right": 8,
    }
    assert all("depthRangeMillimeters" not in hold for hold in board["holds"])


def test_whetstone_discrete_steps_are_individual_scalar_depth_holds() -> None:
    board = _board("tension-whetstone")

    assert len(board["holds"]) == 12
    assert _depth_inventory("tension-whetstone") == {
        "pocket-40-left": 40,
        "pocket-40-right": 40,
        "edge-40-left": 40,
        "edge-30-left": 30,
        "edge-40-right": 40,
        "edge-30-right": 30,
        "edge-40-center": 40,
        "edge-25-left": 25,
        "edge-20-left": 20,
        "edge-25-right": 25,
        "edge-20-right": 20,
    }
    assert all("depthRangeMillimeters" not in hold for hold in board["holds"])


def test_megalith_discrete_steps_are_individual_scalar_depth_holds() -> None:
    board = _board("frictitious-megalith")

    assert len(board["holds"]) == 18
    assert _depth_inventory("frictitious-megalith") == {
        "edge-8-left": 8,
        "edge-10-left": 10,
        "edge-12-left": 12,
        "edge-8-right": 8,
        "edge-10-right": 10,
        "edge-12-right": 12,
        "edge-30-left": 30,
        "edge-40-pocket-left": 40,
        "edge-30-right": 30,
        "edge-40-pocket-right": 40,
        "center-edge-25": 25,
        "edge-15-left": 15,
        "edge-20-left": 20,
        "edge-15-right": 15,
        "edge-20-right": 20,
    }
    assert all("depthRangeMillimeters" not in hold for hold in board["holds"])


def test_continuously_variable_forge_and_pivot_rails_remain_ranges() -> None:
    forge = {
        hold["id"]: hold for hold in _board("trango-rock-prodigy-forge")["holds"]
    }
    pivot = {
        hold["id"]: hold for hold in _board("trango-rock-prodigy-pivot")["holds"]
    }

    assert forge["variable-edge-rail-left"]["depthRangeMillimeters"] == {
        "lowerBound": 7,
        "upperBound": 20,
    }
    assert forge["variable-edge-rail-right"]["depthRangeMillimeters"] == {
        "lowerBound": 7,
        "upperBound": 20,
    }
    assert pivot["variable-edge-left"]["depthRangeMillimeters"] == {
        "lowerBound": 16,
        "upperBound": 31,
    }
    assert pivot["variable-edge-right"]["depthRangeMillimeters"] == {
        "lowerBound": 16,
        "upperBound": 31,
    }
