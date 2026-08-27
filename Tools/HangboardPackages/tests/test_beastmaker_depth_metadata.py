from __future__ import annotations

from pathlib import Path

from hangboard_packages.board_catalog import load_board_package


REPO_ROOT = Path(__file__).resolve().parents[3]


def _depths(package_slug: str) -> dict[str, float]:
    board = load_board_package(REPO_ROOT / "Hangboards" / package_slug).board
    return {
        hold.id: hold.size_millimeters
        for hold in board.holds
        if hold.size_millimeters is not None
    }


def test_beastmaker_1000_prefers_primary_depth_for_the_conflicting_small_edge_pair() -> None:
    assert _depths("beastmaker-1000") == {
        "pocket-top-outer-left": 10,
        "pocket-top-outer-right": 10,
        "pocket-top-left": 30,
        "pocket-top-right": 30,
        "pocket-middle-outer-left": 45,
        "pocket-middle-outer-right": 45,
        "pocket-middle-mid-left": 50,
        "pocket-middle-mid-right": 50,
        "pocket-middle-inner-left": 45,
        "pocket-middle-inner-right": 45,
        "pocket-middle-center": 50,
        "pocket-bottom-outer-left": 20,
        "pocket-bottom-outer-right": 20,
        "pocket-bottom-mid-left": 25,
        "pocket-bottom-mid-right": 25,
        "pocket-bottom-inner-left": 20,
        "pocket-bottom-inner-right": 20,
    }


def test_beastmaker_2000_exposes_positioned_secondary_source_depths() -> None:
    assert _depths("beastmaker-2000") == {
        "front-upper-1": 40,
        "front-upper-2": 20,
        "front-middle-1": 33,
        "front-middle-9": 33,
        "front-middle-2": 55,
        "front-middle-8": 55,
        "front-middle-3": 35,
        "front-middle-7": 35,
        "hold-26": 50,
        "hold-27": 50,
        "front-middle-4": 30,
        "front-middle-6": 30,
        "front-middle-5": 50,
        "front-lower-1": 15,
        "front-lower-9": 15,
        "front-lower-2": 25,
        "front-lower-8": 25,
        "front-lower-3": 20,
        "front-lower-7": 20,
        "front-lower-4": 20,
        "front-lower-6": 20,
        "front-lower-5": 22,
    }


def test_beastmaker_center_edges_use_the_source_labelled_50_millimeter_names() -> None:
    assert {
        package_slug: next(
            hold.name
            for hold in load_board_package(REPO_ROOT / "Hangboards" / package_slug).board.holds
            if hold.id == hold_id
        )
        for package_slug, hold_id in (
            ("beastmaker-1000", "pocket-middle-center"),
            ("beastmaker-2000", "front-middle-5"),
        )
    } == {
        "beastmaker-1000": "50 mm 4 Finger Edge Center",
        "beastmaker-2000": "50 mm 4 Finger Edge Center",
    }


def test_beastmaker_positioned_secondary_sources_correct_hold_types_and_capacities() -> None:
    expected_edges = {
        "beastmaker-1000": {
            "pocket-top-outer-left",
            "pocket-top-outer-right",
            "pocket-top-left",
            "pocket-top-right",
            "pocket-middle-outer-left",
            "pocket-middle-outer-right",
            "pocket-middle-center",
            "pocket-bottom-outer-left",
            "pocket-bottom-outer-right",
        },
        "beastmaker-2000": {
            "front-middle-1",
            "front-middle-5",
            "front-middle-9",
        },
    }
    expected_capacities = {
        "beastmaker-1000": {
            "pocket-middle-mid-left": 2,
            "pocket-middle-mid-right": 2,
            "pocket-middle-inner-left": 3,
            "pocket-middle-inner-right": 3,
            "pocket-bottom-mid-left": 2,
            "pocket-bottom-mid-right": 2,
            "pocket-bottom-inner-left": 3,
            "pocket-bottom-inner-right": 3,
        },
        "beastmaker-2000": {
            "front-upper-1": 3,
            "front-upper-2": 3,
            "front-middle-2": 1,
            "front-middle-8": 1,
            "front-middle-3": 2,
            "front-middle-7": 2,
            "hold-26": 2,
            "hold-27": 2,
            "front-middle-4": 2,
            "front-middle-6": 2,
            "front-lower-2": 1,
            "front-lower-8": 1,
            "front-lower-3": 2,
            "front-lower-7": 2,
            "front-lower-4": 2,
            "front-lower-6": 2,
        },
    }

    for package_slug, edge_ids in expected_edges.items():
        board = load_board_package(REPO_ROOT / "Hangboards" / package_slug).board
        holds = {hold.id: hold for hold in board.holds}
        assert {hold_id for hold_id, hold in holds.items() if hold.kind == "edge"} >= edge_ids
        assert {
            hold_id: holds[hold_id].finger_capacity for hold_id in expected_capacities[package_slug]
        } == expected_capacities[package_slug]
