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
}
SOURCE_PHOTO_EXTENSIONS = {".jpg", ".jpeg", ".webp", ".heic"}


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


def test_compact_package_uses_the_official_hold_inventory_and_semantics() -> None:
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
    assert package.board.presentation_asset_path == "assets/primary.png"
    assert not COMPACT_ROOT.joinpath("artwork.json").exists()


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
