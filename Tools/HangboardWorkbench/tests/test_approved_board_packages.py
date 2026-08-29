from __future__ import annotations

from pathlib import Path
import sys


REPOSITORY_ROOT = Path(__file__).resolve().parents[3]
WORKBENCH_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(WORKBENCH_ROOT))

import board_package  # noqa: E402


def _assert_audited_single_hand_package(
    slug: str, board_id: str, hold_ids: set[str]
) -> None:
    package_root = REPOSITORY_ROOT / "Hangboards" / slug
    package = board_package.load_board_package(package_root)
    board = package.board

    assert board["id"] == board_id
    assert {hold["id"] for hold in board["holds"]} == hold_ids
    assert all(hold.get("handCapacity") == 1 for hold in board["holds"])
    for presentation in board["presentations"]:
        assert (package_root / presentation["assetPath"]).is_file()


def test_nature_stone_hanger_mini_matches_audited_inventory() -> None:
    _assert_audited_single_hand_package(
        "nature-stone-hanger-mini",
        "nature.stone-hanger-mini",
        {"granite-edge-15", "wood-edge-15-incut", "pinch-60", "pull-up-jug"},
    )


def test_nature_stone_hanger_mini_karma8a_matches_audited_inventory() -> None:
    _assert_audited_single_hand_package(
        "nature-stone-hanger-mini-karma8a",
        "nature.stone-hanger-mini-karma8a",
        {"granite-edge-15", "wood-edge-15", "pinch-60"},
    )


def test_lattice_mini_bar_matches_audited_inventory() -> None:
    _assert_audited_single_hand_package(
        "lattice-mini-bar",
        "lattice.mini-bar",
        {"edge-10", "edge-20", "ergonomic-jug", "mini-pinch"},
    )


def test_lattice_mxedge_lift_small_matches_audited_inventory() -> None:
    _assert_audited_single_hand_package(
        "lattice-mxedge-lift-small",
        "lattice.mxedge-lift-small",
        {"edge-18", "edge-14", "edge-8", "mono-25"},
    )


def test_lattice_mxedge_lift_large_matches_audited_inventory() -> None:
    _assert_audited_single_hand_package(
        "lattice-mxedge-lift-large",
        "lattice.mxedge-lift-large",
        {"edge-22", "edge-16", "edge-12", "mono-28"},
    )


def test_plateau_lifting_edge_matches_audited_inventory() -> None:
    _assert_audited_single_hand_package(
        "plateau-lifting-edge",
        "plateau.lifting-edge",
        {"edge-18", "blocker-edge-15", "blocker-edge-10"},
    )


def test_frictitious_nug_matches_audited_inventory() -> None:
    _assert_audited_single_hand_package(
        "frictitious-nug",
        "frictitious.nug",
        {"edge-8", "edge-13", "edge-20", "edge-25", "jug-40", "pinch-60"},
    )


def test_captain_fingerfood_pocket_matches_audited_inventory() -> None:
    _assert_audited_single_hand_package(
        "captain-fingerfood-pocket",
        "captain-fingerfood.pocket",
        {"edge-15", "edge-20", "pinch-body", "jug-outer-rim"},
    )


def test_captain_fingerfood_pocket_plus_matches_audited_inventory() -> None:
    _assert_audited_single_hand_package(
        "captain-fingerfood-pocket-plus",
        "captain-fingerfood.pocket-plus",
        {"edge-6", "edge-10", "edge-15", "edge-20", "pinch-body", "jug-outer-rim"},
    )


def test_captain_fingerfood_unlevel_matches_audited_inventory() -> None:
    _assert_audited_single_hand_package(
        "captain-fingerfood-unlevel",
        "captain-fingerfood.unlevel",
        {"curved-edge-20", "curved-edge-25"},
    )


def test_captain_fingerfood_dual_matches_audited_inventory() -> None:
    _assert_audited_single_hand_package(
        "captain-fingerfood-dual",
        "captain-fingerfood.dual",
        {"straight-edge-20", "curved-edge-20"},
    )


def test_aelith_cyclops_011_matches_audited_inventory() -> None:
    _assert_audited_single_hand_package(
        "aelith-cyclops-011",
        "aelith.cyclops-011",
        {"mono-20"},
    )


def test_crimptonite_helium_mobile_matches_audited_inventory() -> None:
    _assert_audited_single_hand_package(
        "crimptonite-helium-mobile",
        "crimptonite.helium-mobile",
        {
            "edge-14",
            "edge-22",
            "center-edge-10",
            "center-edge-18",
            "top-jug",
            "back-jug-sloper",
        },
    )


def test_port_a_board_has_one_object_and_declared_primary_asset() -> None:
    package_root = REPOSITORY_ROOT / "Hangboards" / "frictitious-port-a-board"
    package = board_package.load_board_package(package_root)
    board = package.board

    assert [item["id"] for item in board["equipmentObjects"]] == ["primary"]
    assert {hold["equipmentObjectID"] for hold in board["holds"]} == {"primary"}
    assert {hold["id"] for hold in board["holds"]} == {
        "edge-30",
        "pocket-30-two-finger-mono",
        "edge-25",
        "edge-20",
        "edge-15",
        "edge-12",
        "edge-10",
        "edge-8",
        "jug-outer-rim",
        "pinch-body",
    }
    assert all("handCapacity" not in hold for hold in board["holds"])
    assert {hold["kind"] for hold in board["holds"]} >= {"edge", "pocket", "jug", "pinch"}
    assert {presentation["id"] for presentation in board["presentations"]} == {
        "primary",
        "back",
        "side",
    }
    assert (package_root / "assets" / "primary.png").is_file()
    assert (package_root / "assets" / "side.png").is_file()
