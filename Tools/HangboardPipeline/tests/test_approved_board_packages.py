from __future__ import annotations

import hashlib
import json
from pathlib import Path
import shutil

import pytest

from PIL import Image

from conftest import load_board_catalog_module


REPO_ROOT = Path(__file__).resolve().parents[3]
HANGBOARDS_ROOT = REPO_ROOT / "Hangboards"
COMPACT_ROOT = HANGBOARDS_ROOT / "metolius-wood-grips-compact-ii"
RUNTIME_HOLD_FIELDS = frozenset(
    {
        "id",
        "name",
        "shortLabel",
        "detail",
        "kind",
        "frame",
        "sizeMillimeters",
        "depthRangeMillimeters",
        "gripType",
        "fingerCapacity",
        "cueStyle",
        "features",
    }
)

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
    "jug-left": (0.000, 0.000, 0.165, 0.255),
    "sloper-flat-left": (0.158, 0.035, 0.190, 0.128),
    "sloper-round-center": (0.352, 0.035, 0.296, 0.128),
    "sloper-flat-right": (0.652, 0.035, 0.190, 0.128),
    "jug-right": (0.835, 0.000, 0.165, 0.255),
    "edge-29-left": (0.021, 0.245, 0.165, 0.270),
    "pocket-29-three-left": (0.199, 0.365, 0.109, 0.148),
    "pocket-29-two-left": (0.328, 0.370, 0.077, 0.147),
    "pocket-29-four-center": (0.425, 0.365, 0.150, 0.148),
    "pocket-29-two-right": (0.595, 0.370, 0.077, 0.147),
    "pocket-29-three-right": (0.692, 0.365, 0.109, 0.148),
    "edge-29-right": (0.814, 0.245, 0.165, 0.270),
    "edge-19-left": (0.035, 0.620, 0.160, 0.245),
    "pocket-19-three-left": (0.216, 0.733, 0.104, 0.140),
    "pocket-19-three-right": (0.680, 0.733, 0.104, 0.140),
    "pocket-19-two-left": (0.336, 0.733, 0.073, 0.140),
    "pocket-19-two-right": (0.591, 0.733, 0.073, 0.140),
    "pocket-19-four-center": (0.425, 0.733, 0.150, 0.140),
    "edge-19-right": (0.805, 0.620, 0.160, 0.245),
}

COMPACT_HOLD_PHYSICAL_FACTS = {
    "jug-left": ("jug", None, "openHand", 4, ("jug",)),
    "sloper-flat-left": ("sloper", 56, "sloper", 4, ("largeSlope",)),
    "sloper-round-center": ("sloper", 56, "sloper", 4, ("roundSloper",)),
    "sloper-flat-right": ("sloper", 56, "sloper", 4, ("largeSlope",)),
    "jug-right": ("jug", None, "openHand", 4, ("jug",)),
    "edge-29-left": ("edge", 29, "openHand", 4, ("largeEdge",)),
    "pocket-29-three-left": (
        "pocket",
        29,
        "threeFingerPocket",
        3,
        ("pocket", "threeFingerPocket"),
    ),
    "pocket-29-two-left": (
        "pocket",
        29,
        "twoFingerPocket",
        2,
        ("pocket", "twoFingerPocket"),
    ),
    "pocket-29-four-center": (
        "pocket",
        29,
        "fourFingerPocket",
        4,
        ("pocket", "fourFingerPocket"),
    ),
    "pocket-29-two-right": (
        "pocket",
        29,
        "twoFingerPocket",
        2,
        ("pocket", "twoFingerPocket"),
    ),
    "pocket-29-three-right": (
        "pocket",
        29,
        "threeFingerPocket",
        3,
        ("pocket", "threeFingerPocket"),
    ),
    "edge-29-right": ("edge", 29, "openHand", 4, ("largeEdge",)),
    "edge-19-left": ("edge", 19, "openHand", 4, ("mediumEdge", "smallEdge")),
    "pocket-19-three-left": (
        "pocket",
        19,
        "threeFingerPocket",
        3,
        ("pocket", "threeFingerPocket"),
    ),
    "pocket-19-three-right": (
        "pocket",
        19,
        "threeFingerPocket",
        3,
        ("pocket", "threeFingerPocket"),
    ),
    "pocket-19-two-left": (
        "pocket",
        19,
        "twoFingerPocket",
        2,
        ("pocket", "twoFingerPocket"),
    ),
    "pocket-19-two-right": (
        "pocket",
        19,
        "twoFingerPocket",
        2,
        ("pocket", "twoFingerPocket"),
    ),
    "pocket-19-four-center": (
        "pocket",
        19,
        "fourFingerPocket",
        4,
        ("pocket", "fourFingerPocket"),
    ),
    "edge-19-right": ("edge", 19, "openHand", 4, ("mediumEdge", "smallEdge")),
}

COMPACT_SEMANTICS = {
    "edge-19": ("edge-19-left", "edge-19-right"),
    "edge-29": ("edge-29-left", "edge-29-right"),
    "flat-slopers": ("sloper-flat-left", "sloper-flat-right"),
    "outer-jugs": ("jug-left", "jug-right"),
    "pocket-19-four": ("pocket-19-four-center",),
    "pocket-19-three": ("pocket-19-three-left", "pocket-19-three-right"),
    "pocket-19-two": ("pocket-19-two-left", "pocket-19-two-right"),
    "pocket-29-four": ("pocket-29-four-center",),
    "pocket-29-three": ("pocket-29-three-left", "pocket-29-three-right"),
    "pocket-29-two": ("pocket-29-two-left", "pocket-29-two-right"),
    "round-sloper": ("sloper-round-center",),
}

CANONICAL_PACKAGE_SIDECARS = {
    "board.json",
    "evidence.json",
    "semantics.json",
    "artwork.json",
}
SOURCE_PHOTO_EXTENSIONS = {".jpg", ".jpeg", ".webp", ".heic"}


def _frame_tuple(frame: object) -> tuple[float, float, float, float]:
    return (frame.x, frame.y, frame.width, frame.height)  # type: ignore[attr-defined]


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


def test_registry_contains_only_the_fully_officially_sourced_runtime_board() -> None:
    module = load_board_catalog_module()
    catalog = module.validate_catalog(HANGBOARDS_ROOT / "catalog.json")
    approved = {entry.id: entry.path for entry in catalog.entries}

    assert approved == {
        "metolius.wood-grips-compact-ii": "metolius-wood-grips-compact-ii",
    }


def test_metolius_candidates_with_incomplete_hold_evidence_remain_primary_only() -> None:
    catalog = json.loads((HANGBOARDS_ROOT / "catalog.json").read_text(encoding="utf-8"))
    registered_paths = {entry["path"] for entry in catalog["boards"]}

    for slug in (
        "metolius-climbers-edge",
        "metolius-contact",
        "metolius-project",
        "metolius-simulator-3d",
    ):
        package_root = HANGBOARDS_ROOT / slug
        assert slug not in registered_paths
        assert {path.relative_to(package_root).as_posix() for path in package_root.rglob("*") if path.is_file()} == {
            "assets/primary.png"
        }


def test_soill_and_tension_candidates_with_incomplete_hold_evidence_remain_primary_only() -> None:
    catalog = json.loads((HANGBOARDS_ROOT / "catalog.json").read_text(encoding="utf-8"))
    registered_paths = {entry["path"] for entry in catalog["boards"]}

    for slug in (
        "soill-iron-palm-2",
        "soill-split-palm",
        "soill-training-tiles",
        "tension-grindstone",
        "tension-honestone",
        "tension-whetstone",
    ):
        package_root = HANGBOARDS_ROOT / slug
        assert slug not in registered_paths
        assert {path.relative_to(package_root).as_posix() for path in package_root.rglob("*") if path.is_file()} == {
            "assets/primary.png"
        }


def test_trango_candidates_with_non_exhaustive_hold_guides_remain_primary_only() -> None:
    catalog = json.loads((HANGBOARDS_ROOT / "catalog.json").read_text(encoding="utf-8"))
    registered_paths = {entry["path"] for entry in catalog["boards"]}

    for slug in (
        "trango-rock-prodigy-forge",
        "trango-rock-prodigy-natural",
        "trango-rock-prodigy-pivot",
        "trango-rock-prodigy-training-center",
    ):
        package_root = HANGBOARDS_ROOT / slug
        assert slug not in registered_paths
        assert {path.relative_to(package_root).as_posix() for path in package_root.rglob("*") if path.is_file()} == {
            "assets/primary.png"
        }


def test_yy_vertical_candidates_without_individual_hold_maps_remain_primary_only() -> None:
    catalog = json.loads((HANGBOARDS_ROOT / "catalog.json").read_text(encoding="utf-8"))
    registered_paths = {entry["path"] for entry in catalog["boards"]}

    for slug in (
        "yy-verticalboard-evo",
        "yy-verticalboard-first",
        "yy-verticalboard-light",
        "yy-verticalboard-one",
    ):
        package_root = HANGBOARDS_ROOT / slug
        assert slug not in registered_paths
        assert {path.relative_to(package_root).as_posix() for path in package_root.rglob("*") if path.is_file()} == {
            "assets/primary.png"
        }


def test_zlagboard_candidates_without_model_specific_hold_maps_remain_primary_only() -> None:
    catalog = json.loads((HANGBOARDS_ROOT / "catalog.json").read_text(encoding="utf-8"))
    registered_paths = {entry["path"] for entry in catalog["boards"]}

    for slug in ("zlagboard-evo", "zlagboard-pro"):
        package_root = HANGBOARDS_ROOT / slug
        assert slug not in registered_paths
        assert {path.relative_to(package_root).as_posix() for path in package_root.rglob("*") if path.is_file()} == {
            "assets/primary.png"
        }


def test_every_registered_package_has_one_presentation_and_complete_evidence() -> None:
    module = load_board_catalog_module()
    catalog = module.validate_catalog(HANGBOARDS_ROOT / "catalog.json")

    for entry in catalog.entries:
        package_root = HANGBOARDS_ROOT / entry.path
        package = module.load_board_package(package_root)
        assert package.board.presentation_asset_path == "assets/primary.png"
        assert {path.name for path in package_root.glob("*.json")} == CANONICAL_PACKAGE_SIDECARS

        asset_paths = {
            path.relative_to(package_root).as_posix()
            for path in (package_root / "assets").iterdir()
        }
        assert "assets/primary.png" in asset_paths
        source_photos = asset_paths - {"assets/primary.png"}
        assert len(source_photos) <= 1
        assert all(Path(path).suffix.lower() in SOURCE_PHOTO_EXTENSIONS for path in source_photos)
        assert set(package.evidence.asset_evidence) == asset_paths


def test_compact_board_embeds_each_legacy_piece_under_its_unique_physical_hold(
) -> None:
    board = json.loads((COMPACT_ROOT / "board.json").read_text(encoding="utf-8"))
    artwork = json.loads((COMPACT_ROOT / "artwork.json").read_text(encoding="utf-8"))
    holds = board["holds"]
    hold_ids = [hold["id"] for hold in holds]
    pieces_by_hold: dict[str, list[dict[str, object]]] = {}
    piece_ids: list[str] = []

    for source_piece in artwork["holdPieces"]:
        piece = dict(source_piece)
        piece_ids.append(piece.pop("id"))
        hold_id = piece.pop("holdID")
        pieces_by_hold.setdefault(hold_id, []).append(piece)

    assert board["id"] == artwork["boardID"] == "metolius.wood-grips-compact-ii"
    assert tuple((hold["id"], hold["name"]) for hold in holds) == COMPACT_HOLDS
    assert len(hold_ids) == len(set(hold_ids))
    assert len(piece_ids) == len(set(piece_ids))
    assert set(hold_ids) == set(pieces_by_hold)
    assert all(hold.get("geometry") for hold in holds)
    assert {
        hold["id"]: hold["geometry"]
        for hold in holds
    } == pieces_by_hold


def test_compact_hold_records_keep_only_supported_sourced_physical_facts() -> None:
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
        "gripType",
        "fingerCapacity",
        "features",
    }

    assert all(not (set(hold) & retired_fields) for hold in holds)
    assert all({"id", "name", "kind", "geometry"} <= set(hold) for hold in holds)
    assert all(set(hold) <= supported_fields for hold in holds)
    assert all("depthRangeMillimeters" not in hold for hold in holds)
    assert {
        hold["id"]: (
            hold.get("kind"),
            hold.get("sizeMillimeters"),
            hold.get("gripType"),
            hold.get("fingerCapacity"),
            tuple(hold.get("features", ())),
        )
        for hold in holds
    } == COMPACT_HOLD_PHYSICAL_FACTS


def test_compact_hold_bounds_are_derived_from_embedded_piece_unions() -> None:
    board = json.loads((COMPACT_ROOT / "board.json").read_text(encoding="utf-8"))
    bounds_by_hold = {
        hold["id"]: _embedded_geometry_bounds(hold.get("geometry"))
        for hold in board["holds"]
    }

    assert set(bounds_by_hold) == set(COMPACT_HOLD_BOUNDS)
    for hold_id, expected_bounds in COMPACT_HOLD_BOUNDS.items():
        assert bounds_by_hold[hold_id] == pytest.approx(expected_bounds)


def test_compact_package_uses_the_official_hold_inventory_semantics_and_artwork() -> None:
    module = load_board_catalog_module()
    package = module.load_board_package(COMPACT_ROOT)

    assert tuple((hold.id, hold.name) for hold in package.board.holds) == COMPACT_HOLDS
    assert package.board.facts == {
        "manufacturer": "Metolius",
        "name": "Wood Grips Compact II",
        "subtitle": "A compact FSC-certified wood board for everyday strength work.",
        "productURL": "https://www.metoliusclimbing.com/collections/training-boards/products/wood-grips-ii-training-boards",
        "dimensions": '24" × 6.2"',
        "aspectRatio": 3.88,
    }
    assert set(package.evidence.hold_evidence) == {
        f"{hold_id}.{field}"
        for hold_id, _ in COMPACT_HOLDS
        for field in RUNTIME_HOLD_FIELDS
    }
    assert all(
        mapping.method == "reviewed-human-authored-normalization"
        and "hold-depth-diagram" in mapping.source_ids
        for mapping in package.evidence.hold_evidence.values()
    )
    assert all(
        "training-board-manual" in mapping.source_ids
        for key, mapping in package.evidence.hold_evidence.items()
        if key.endswith(".gripType")
    )
    assert dict(package.semantics.semantic_holds) == COMPACT_SEMANTICS
    assert _frame_tuple(package.artwork.canvas_frame) == (0.025, 0.005, 0.950, 0.965)
    assert tuple(layer.id for layer in package.artwork.layers) == (
        "top-plane",
        "middle-separator",
        "bottom-plane",
        "left-top-seam",
        "right-top-seam",
    )
    assert tuple(piece.id for piece in package.artwork.hold_pieces) == (
        "jug-left-top-cap", "jug-right-top-cap",
        "sloper-flat-left-top-surface", "sloper-flat-right-top-surface",
        "sloper-round-center-surface",
        "edge-29-left-upper-side-rail", "edge-29-right-upper-side-rail",
        "pocket-29-three-left-upper", "pocket-29-three-right-upper",
        "pocket-29-two-left-upper", "pocket-29-two-right-upper",
        "pocket-29-four-center-upper",
        "edge-19-left-lower-side-rail", "edge-19-right-lower-side-rail",
        "pocket-19-three-left-lower", "pocket-19-three-right-lower",
        "pocket-19-two-left-lower", "pocket-19-two-right-lower",
        "pocket-19-four-center-lower",
    )
    assert package.artwork.hold_ids == {hold_id for hold_id, _ in COMPACT_HOLDS}
    assert package.board.presentation_asset_path == "assets/primary.png"


def test_compact_screwless_asset_is_the_single_generated_presentation() -> None:
    repaired_path = COMPACT_ROOT / "assets" / "primary.png"
    repaired = Image.open(repaired_path).convert("RGB")

    assert repaired.size == (1774, 457)
    assert hashlib.sha256(repaired_path.read_bytes()).hexdigest() == "7e39c41e0e3bfb3d61d2ba0c331281bc04c06e98817ecc0fa8e3180f7923216e"

    evidence = json.loads((COMPACT_ROOT / "evidence.json").read_text(encoding="utf-8"))
    assert evidence["assetEvidence"]["assets/primary.png"]["method"] == "external-generative-adaptation"


def test_registered_packages_keep_only_canonical_presentation_assets() -> None:
    compact_reference = COMPACT_ROOT / "assets" / "WoodGripsCompactII.jpg"
    assert hashlib.sha256(compact_reference.read_bytes()).hexdigest() == "c101a319076448be38977c606b5be57f1f254e2fe273b0c56a69ca2f52bdb596"

    assert {path.name for path in (COMPACT_ROOT / "assets").iterdir()} == {
        "primary.png",
        "WoodGripsCompactII.jpg",
    }


def test_source_photo_requires_its_exact_package_relative_evidence_path(tmp_path: Path) -> None:
    module = load_board_catalog_module()
    package_root = tmp_path / "compact"
    shutil.copytree(COMPACT_ROOT, package_root)
    evidence_path = package_root / "evidence.json"
    evidence = json.loads(evidence_path.read_text(encoding="utf-8"))
    assert (package_root / "assets" / "WoodGripsCompactII.jpg").is_file()
    evidence["assetEvidence"].pop("assets/WoodGripsCompactII.jpg")
    evidence_path.write_text(json.dumps(evidence), encoding="utf-8")

    with pytest.raises(ValueError, match="assetEvidence keys must equal package assets"):
        module.load_board_package(package_root)
