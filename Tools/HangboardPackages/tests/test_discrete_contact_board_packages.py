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


def test_honestone_discrete_steps_and_macro_selection_regions_are_source_safe() -> None:
    board = _board("tension-honestone")

    assert len(board["holds"]) == 15
    assert {
        kind: sum(hold["kind"] == kind for hold in board["holds"])
        for kind in ("edge", "pocket", "sloper")
    } == {"edge": 9, "pocket": 2, "sloper": 4}
    macro_slopers = [
        hold
        for hold in board["holds"]
        if hold["id"].startswith("macro-sloper-")
    ]
    assert [hold["id"] for hold in macro_slopers] == [
        "macro-sloper-left",
        "macro-sloper-right-center",
        "macro-sloper-left-center",
        "macro-sloper-right",
    ]
    assert all(
        "sizeMillimeters" not in hold
        and "fingerCapacity" not in hold
        and "gripType" not in hold
        for hold in macro_slopers
    )
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


def test_split_palm_and_training_tiles_expose_descriptive_adapted_contacts() -> None:
    split_palm = _board("soill-split-palm")
    assert {
        hold["id"]: (hold["name"], hold["kind"])
        for hold in split_palm["holds"]
        if hold["kind"] == "pinch"
    } == {
        "lower-pinch-left": ("Left lower pinch", "pinch"),
        "lower-pinch-right": ("Right lower pinch", "pinch"),
    }

    training_tiles = _board("soill-training-tiles")
    assert len(training_tiles["holds"]) == 20
    assert training_tiles["productURL"] == (
        "https://soill.ca/products/training-tiles-so-ill-x-meagan-martin"
    )
    assert training_tiles["dimensions"] == "Not published by manufacturer"
    assert all(
        all(
            field not in hold
            for field in (
                "sizeMillimeters",
                "depthRangeMillimeters",
                "fingerCapacity",
                "handCapacity",
                "gripType",
                "features",
            )
        )
        for hold in training_tiles["holds"]
    )
    assert {
        hold["id"]: (hold["name"], hold["kind"])
        for hold in training_tiles["holds"]
    } == {
        "top-jug-left": ("Left top jug", "jug"),
        "top-jug-right": ("Right top jug", "jug"),
        "top-pocket-outer-left": ("Outer left top pocket", "pocket"),
        "top-pocket-inner-left": ("Inner left top pocket", "pocket"),
        "top-pocket-inner-right": ("Inner right top pocket", "pocket"),
        "top-pocket-outer-right": ("Outer right top pocket", "pocket"),
        "upper-sloper-outer-left": ("Outer left upper sloper", "sloper"),
        "upper-sloper-inner-left": ("Inner left upper sloper", "sloper"),
        "upper-sloper-inner-right": ("Inner right upper sloper", "sloper"),
        "upper-sloper-outer-right": ("Outer right upper sloper", "sloper"),
        "middle-edge-outer-left": ("Outer left middle edge", "edge"),
        "middle-edge-inner-left": ("Inner left middle edge", "edge"),
        "middle-edge-inner-right": ("Inner right middle edge", "edge"),
        "middle-edge-outer-right": ("Outer right middle edge", "edge"),
        "bottom-edge-outer-left": ("Outer left bottom edge", "edge"),
        "bottom-edge-center-left": ("Center left bottom edge", "edge"),
        "bottom-edge-inner-left": ("Inner left bottom edge", "edge"),
        "bottom-edge-inner-right": ("Inner right bottom edge", "edge"),
        "bottom-edge-center-right": ("Center right bottom edge", "edge"),
        "bottom-edge-outer-right": ("Outer right bottom edge", "edge"),
    }
    assert all(
        "sizeMillimeters" not in hold
        and "depthRangeMillimeters" not in hold
        and "fingerCapacity" not in hold
        and "handCapacity" not in hold
        for hold in training_tiles["holds"]
    )


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
    assert {
        hold_id: hold["depthRangeMillimeters"]
        for hold_id, hold in pivot.items()
        if "depthRangeMillimeters" in hold
    } == {
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
