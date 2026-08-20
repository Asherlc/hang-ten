from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pytest

from PIL import Image

from conftest import load_board_catalog_module


REPO_ROOT = Path(__file__).resolve().parents[3]
HANGBOARDS_ROOT = REPO_ROOT / "Hangboards"
COMPACT_ROOT = HANGBOARDS_ROOT / "metolius-wood-grips-compact-ii"
COMPACT_HOLDS = (
    ("jug-left", "Left outer jug"),
    ("sloper-flat-left", "Left 56 mm flat sloper"),
    ("sloper-round-center", "Center 56 mm round sloper"),
    ("sloper-flat-right", "Right 56 mm flat sloper"),
    ("jug-right", "Right outer jug"),
    ("edge-29-left", "Left 29 mm edge"),
    ("pocket-29-three-left", "Left 29 mm three-finger pocket"),
    ("pocket-29-two-left", "Left 29 mm two-finger pocket"),
    ("pocket-29-four-center", "Center 29 mm four-finger pocket"),
    ("pocket-29-two-right", "Right 29 mm two-finger pocket"),
    ("pocket-29-three-right", "Right 29 mm three-finger pocket"),
    ("edge-29-right", "Right 29 mm edge"),
    ("edge-19-left", "Left 19 mm edge"),
    ("pocket-19-three-left", "Left 19 mm three-finger pocket"),
    ("pocket-19-three-right", "Right 19 mm three-finger pocket"),
    ("pocket-19-two-left", "Left 19 mm two-finger pocket"),
    ("pocket-19-two-right", "Right 19 mm two-finger pocket"),
    ("pocket-19-four-center", "Center 19 mm four-finger pocket"),
    ("edge-19-right", "Right 19 mm edge"),
)

COMPACT_HOLD_BOUNDS = {
    # jug-left/right, edge-29-*, and edge-19-* were retightened so their
    # declared frame exactly matches their path's flattened bounds; see
    # "Fix hold geometry bounds and aspect-ratio metadata mismatches".
    "jug-left": (0.038, 0.035, 0.127, 0.180),
    "sloper-flat-left": (0.158, 0.035, 0.190, 0.128),
    "sloper-round-center": (0.352, 0.035, 0.296, 0.128),
    "sloper-flat-right": (0.652, 0.035, 0.190, 0.128),
    "jug-right": (0.835, 0.035, 0.127, 0.180),
    "edge-29-left": (0.050, 0.255, 0.136, 0.235),
    "pocket-29-three-left": (0.199, 0.365, 0.109, 0.148),
    "pocket-29-two-left": (0.328, 0.370, 0.077, 0.147),
    "pocket-29-four-center": (0.425, 0.365, 0.150, 0.148),
    "pocket-29-two-right": (0.595, 0.370, 0.077, 0.147),
    "pocket-29-three-right": (0.692, 0.365, 0.109, 0.148),
    "edge-29-right": (0.814, 0.255, 0.136, 0.235),
    "edge-19-left": (0.060, 0.630, 0.135, 0.215),
    "pocket-19-three-left": (0.216, 0.733, 0.104, 0.140),
    "pocket-19-three-right": (0.680, 0.733, 0.104, 0.140),
    "pocket-19-two-left": (0.336, 0.733, 0.073, 0.140),
    "pocket-19-two-right": (0.591, 0.733, 0.073, 0.140),
    "pocket-19-four-center": (0.425, 0.733, 0.150, 0.140),
    "edge-19-right": (0.805, 0.630, 0.135, 0.215),
}

# Each value is (source-backed kind, depth, capacity, structural pocket grip,
# app semantic routing). Pocket grip types are the direct semantic encoding of
# visible/source-backed capacity, not manufacturer posture prescriptions. The
# feature tuple is an app compatibility adaptation, not a manufacturer grip fact.
COMPACT_HOLD_SOURCE_FACTS_AND_ROUTING = {
    "jug-left": ("jug", None, 4, None, ("jug",)),
    "sloper-flat-left": ("sloper", 56, 4, None, ("largeSlope",)),
    "sloper-round-center": ("sloper", 56, 4, None, ("roundSloper",)),
    "sloper-flat-right": ("sloper", 56, 4, None, ("largeSlope",)),
    "jug-right": ("jug", None, 4, None, ("jug",)),
    "edge-29-left": ("edge", 29, 4, None, ("largeEdge",)),
    "pocket-29-three-left": ("pocket", 29, 3, "threeFingerPocket", ("pocket",)),
    "pocket-29-two-left": ("pocket", 29, 2, "twoFingerPocket", ("pocket",)),
    "pocket-29-four-center": ("pocket", 29, 4, "fourFingerPocket", ("pocket",)),
    "pocket-29-two-right": ("pocket", 29, 2, "twoFingerPocket", ("pocket",)),
    "pocket-29-three-right": ("pocket", 29, 3, "threeFingerPocket", ("pocket",)),
    "edge-29-right": ("edge", 29, 4, None, ("largeEdge",)),
    "edge-19-left": ("edge", 19, 4, None, ("mediumEdge", "smallEdge")),
    "pocket-19-three-left": ("pocket", 19, 3, "threeFingerPocket", ("pocket",)),
    "pocket-19-three-right": ("pocket", 19, 3, "threeFingerPocket", ("pocket",)),
    "pocket-19-two-left": ("pocket", 19, 2, "twoFingerPocket", ("pocket",)),
    "pocket-19-two-right": ("pocket", 19, 2, "twoFingerPocket", ("pocket",)),
    "pocket-19-four-center": ("pocket", 19, 4, "fourFingerPocket", ("pocket",)),
    "edge-19-right": ("edge", 19, 4, None, ("mediumEdge", "smallEdge")),
}

def _embedded_geometry_bounds(
    geometry: object,
) -> tuple[float, float, float, float] | None:
    if not isinstance(geometry, list) or not geometry:
        return None
    frames = [piece["frame"] for piece in geometry]
    min_x = min(frame["x"] for frame in frames)
    min_y = min(frame["y"] for frame in frames)
    max_x = max(frame["x"] + frame["width"] for frame in frames)
    max_y = max(frame["y"] + frame["height"] for frame in frames)
    return (min_x, min_y, max_x - min_x, max_y - min_y)


def test_direct_discovery_finds_the_exact_complete_inventory_without_drafts() -> None:
    inventory = load_board_catalog_module().discover_board_packages(HANGBOARDS_ROOT)

    discovered = {(package.board.id, package.root.name) for package in inventory.packages}

    expected_packages = {
        ("metolius.wood-grips-compact-ii", "metolius-wood-grips-compact-ii"),
        ("beastmaker-1000", "beastmaker-1000"),
        ("beastmaker-2000", "beastmaker-2000"),
        ("dewoodstok-woodbord", "dewoodstok-woodbord"),
        ("escape-beta-22", "escape-beta-22"),
        ("escape.unlimited", "escape-unlimited"),
        ("evolv-kilter-basic-long", "evolv-kilter-basic-long"),
        ("frictitious.doormount-pro-7", "frictitious-doormount-pro-7"),
        ("frictitious.megalith", "frictitious-megalith"),
        ("lattice-triple-rung", "lattice-triple-rung"),
        ("metolius.climbers-edge", "metolius-climbers-edge"),
        ("metolius.contact", "metolius-contact"),
        ("metolius.project", "metolius-project"),
        ("metolius.simulator-3d", "metolius-simulator-3d"),
        ("moon.armstrong", "moon-armstrong"),
        ("nature.stoak-board-iii", "nature-stoak-board-iii"),
        ("soill.iron-palm-2", "soill-iron-palm-2"),
        ("soill.split-palm", "soill-split-palm"),
        ("soill.training-tiles", "soill-training-tiles"),
        ("target10a.linebreaker-base", "target10a-linebreaker-base"),
        ("trango.rock-prodigy-forge", "trango-rock-prodigy-forge"),
        ("trango.rock-prodigy-natural", "trango-rock-prodigy-natural"),
        ("trango.rock-prodigy-pivot", "trango-rock-prodigy-pivot"),
        (
            "trango.rock-prodigy-training-center",
            "trango-rock-prodigy-training-center",
        ),
        ("tension.grindstone", "tension-grindstone"),
        ("tension.honestone", "tension-honestone"),
        ("tension.whetstone", "tension-whetstone"),
        ("yy.verticalboard-evo", "yy-verticalboard-evo"),
        ("yy.verticalboard-first", "yy-verticalboard-first"),
        ("yy.verticalboard-light", "yy-verticalboard-light"),
        ("yy.verticalboard-one", "yy-verticalboard-one"),
        ("zlagboard.evo", "zlagboard-evo"),
        ("zlagboard.pro", "zlagboard-pro"),
    }
    assert discovered == expected_packages
    assert inventory.drafts == ()
    assert not (HANGBOARDS_ROOT / "catalog.json").exists()


def test_compact_finished_package_has_exactly_one_document_and_primary_asset() -> None:
    relative_paths = {
        path.relative_to(COMPACT_ROOT).as_posix()
        for path in COMPACT_ROOT.rglob("*")
    }

    assert relative_paths == {"assets", "assets/primary.png", "board.json"}


def test_compact_board_keeps_the_literal_hold_inventory_with_embedded_geometry() -> None:
    board = json.loads((COMPACT_ROOT / "board.json").read_text(encoding="utf-8"))
    holds = board["holds"]
    hold_ids = [hold["id"] for hold in holds]

    assert board["id"] == "metolius.wood-grips-compact-ii"
    assert tuple((hold["id"], hold["name"]) for hold in holds) == COMPACT_HOLDS
    assert len(hold_ids) == len(set(hold_ids))
    assert all(hold.get("geometry") for hold in holds)


def test_compact_hold_records_keep_sourced_physical_facts_and_app_routing() -> None:
    board = json.loads((COMPACT_ROOT / "board.json").read_text(encoding="utf-8"))
    holds = board["holds"]
    retired_fields = {"frame", "shortLabel", "detail", "cueStyle"}
    supported_fields = {
        "id",
        "name",
        "kind",
        "geometry",
        "sizeMillimeters",
        "depthRangeMillimeters",
        "fingerCapacity",
        "gripType",
        "features",
    }

    assert all(not (set(hold) & retired_fields) for hold in holds)
    assert all({"id", "name", "kind", "geometry"} <= set(hold) for hold in holds)
    assert all(set(hold) <= supported_fields for hold in holds)
    assert all("depthRangeMillimeters" not in hold for hold in holds)
    expected_pocket_grips = {
        2: "twoFingerPocket",
        3: "threeFingerPocket",
        4: "fourFingerPocket",
    }
    assert all(
        hold.get("gripType") == expected_pocket_grips[hold["fingerCapacity"]]
        for hold in holds
        if hold["kind"] == "pocket"
    )
    assert all(
        "gripType" not in hold
        for hold in holds
        if hold["kind"] != "pocket"
    )
    assert {
        hold["id"]: (
            hold.get("kind"),
            hold.get("sizeMillimeters"),
            hold.get("fingerCapacity"),
            hold.get("gripType"),
            tuple(hold.get("features", ())),
        )
        for hold in holds
    } == COMPACT_HOLD_SOURCE_FACTS_AND_ROUTING


def test_compact_hold_bounds_are_derived_from_embedded_piece_unions() -> None:
    board = json.loads((COMPACT_ROOT / "board.json").read_text(encoding="utf-8"))
    bounds_by_hold = {
        hold["id"]: _embedded_geometry_bounds(hold.get("geometry"))
        for hold in board["holds"]
    }

    assert set(bounds_by_hold) == set(COMPACT_HOLD_BOUNDS)
    for hold_id, expected_bounds in COMPACT_HOLD_BOUNDS.items():
        assert bounds_by_hold[hold_id] == pytest.approx(expected_bounds)


def test_compact_package_loader_preserves_identity_inventory_and_bounds() -> None:
    module = load_board_catalog_module()
    package = module.load_board_package(COMPACT_ROOT)

    assert tuple((hold.id, hold.name) for hold in package.board.holds) == COMPACT_HOLDS
    assert package.board.facts == {
        "manufacturer": "Metolius",
        "name": "Wood Grips Compact II",
        "subtitle": "FSC-certified wood training board.",
        "productURL": "https://www.metoliusclimbing.com/products/wood-grips-ii-training-boards",
        "dimensions": '24" × 6.2"',
        "aspectRatio": 3.88,
    }
    assert package.board.presentation_asset_path == "assets/primary.png"
    for hold in package.board.holds:
        actual = (hold.frame.x, hold.frame.y, hold.frame.width, hold.frame.height)
        assert actual == pytest.approx(COMPACT_HOLD_BOUNDS[hold.id])


def test_compact_screwless_asset_is_the_single_generated_presentation() -> None:
    repaired_path = COMPACT_ROOT / "assets" / "primary.png"
    repaired = Image.open(repaired_path).convert("RGB")

    assert repaired.size == (1774, 457)
    assert hashlib.sha256(repaired_path.read_bytes()).hexdigest() == "7e39c41e0e3bfb3d61d2ba0c331281bc04c06e98817ecc0fa8e3180f7923216e"
