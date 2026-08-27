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


def test_whetstone_source_side_shelves_have_independently_authored_paths() -> None:
    holds = {hold["id"]: hold for hold in _board("tension-whetstone")["holds"]}
    source_side_shapes = {
        json.dumps(holds[hold_id]["geometry"][0]["shape"], sort_keys=True)
        for hold_id in (
            "edge-40-left",
            "edge-30-left",
            "edge-25-left",
            "edge-20-left",
        )
    }

    assert len(source_side_shapes) == 4


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
    actual_pivot_ranges = {
        hold_id: hold["depthRangeMillimeters"]
        for hold_id, hold in pivot.items()
        if "depthRangeMillimeters" in hold
    }
    base_pivot_ranges = {
        "variable-edge-left": {"lowerBound": 16, "upperBound": 31},
        "variable-edge-right": {"lowerBound": 16, "upperBound": 31},
        "medium-crimp-left": {"lowerBound": 9, "upperBound": 10},
        "medium-crimp-right": {"lowerBound": 9, "upperBound": 10},
        "large-crimp-left": {"lowerBound": 11, "upperBound": 12},
        "large-crimp-right": {"lowerBound": 11, "upperBound": 12},
        "two-finger-pocket-left": {"lowerBound": 28, "upperBound": 32},
        "two-finger-pocket-right": {"lowerBound": 28, "upperBound": 32},
        "three-finger-pocket-left": {"lowerBound": 17, "upperBound": 28},
        "three-finger-pocket-right": {"lowerBound": 17, "upperBound": 28},
    }
    assert actual_pivot_ranges == {
        f"{hold_id}{suffix}": depth_range
        for suffix in ("", "-orientation-2", "-orientation-3", "-orientation-4")
        for hold_id, depth_range in base_pivot_ranges.items()
    }
