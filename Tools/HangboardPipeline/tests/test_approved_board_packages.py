from __future__ import annotations

import hashlib
import json
from pathlib import Path

from PIL import Image, ImageChops

from conftest import load_board_catalog_module


REPO_ROOT = Path(__file__).resolve().parents[3]
HANGBOARDS_ROOT = REPO_ROOT / "Hangboards"
COMPACT_ROOT = HANGBOARDS_ROOT / "metolius-wood-grips-compact-ii"
ROCK_PRODIGY_ROOT = HANGBOARDS_ROOT / "trango-rock-prodigy-training-center"

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

ROCK_PRODIGY_LEFT_HOLDS = (
    ("top-jug", "top jug"),
    ("large-open-rail", "20–33 mm variable-depth rail"),
    ("small-crimp-rail", "10–24 mm variable-depth rail"),
    ("three-finger-slot", "38 mm three-finger slot"),
    ("thin-crimp", "7.5 mm thin crimp"),
    ("deep-mr-pocket", "29 mm deep MR pocket"),
    ("shallow-mr-pocket", "19 mm shallow MR pocket"),
    ("medium-im-pocket", "26–36 mm medium IM pocket"),
    ("shallow-im-pocket", "19–24 mm shallow IM pocket"),
    ("wide-pinch", "87 mm wide pinch"),
    ("medium-pinch", "44 mm medium pinch"),
    ("small-pinch", "18 mm small pinch"),
    ("sloper", "outer sloper"),
)
ROCK_PRODIGY_HOLDS = tuple(
    item
    for slug, name in ROCK_PRODIGY_LEFT_HOLDS
    for item in (
        (f"trango.rptc.left.{slug}", f"Left {name}"),
        (f"trango.rptc.right.{slug}", f"Right {name}"),
    )
)
ROCK_PRODIGY_SEMANTICS = {
    "deep-two-finger-pocket": (
        "trango.rptc.left.deep-mr-pocket",
        "trango.rptc.right.deep-mr-pocket",
    ),
    "large-open-hand-rail": (
        "trango.rptc.left.large-open-rail",
        "trango.rptc.right.large-open-rail",
    ),
    "shallow-three-finger-slot": (
        "trango.rptc.left.three-finger-slot",
        "trango.rptc.right.three-finger-slot",
    ),
    "sloper": ("trango.rptc.left.sloper", "trango.rptc.right.sloper"),
    "thin-crimp": (
        "trango.rptc.left.thin-crimp",
        "trango.rptc.right.thin-crimp",
    ),
    "warmup-jug": ("trango.rptc.left.top-jug", "trango.rptc.right.top-jug"),
    "wide-pinch": (
        "trango.rptc.left.wide-pinch",
        "trango.rptc.right.wide-pinch",
    ),
}

# Canonical JSON digests freeze every expanded frame, path command, layer,
# hold-piece ID, and treatment after migration from the reviewed Swift designs.
EXPECTED_ARTWORK_DIGESTS = {
    "metolius.wood-grips-compact-ii": "525f7b9978a3b0a03f5ffb917ebe0c2a71809f3f34dcaa9c90bb46c73153e882",
    "trango.rock-prodigy-training-center": "055132a318df51d9427563701f06ed4b78449c8737133a9ac22093191a1a32cb",
}

COMPACT_REPAIR_MASKS = (
    (374, 148, 18),
    (743, 148, 18),
    (1035, 148, 18),
    (1400, 148, 18),
    (405, 309, 18),
    (1371, 309, 18),
)


def _canonical_digest(path: Path) -> str:
    payload = json.loads(path.read_text(encoding="utf-8"))
    canonical = json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def _frame_tuple(frame: object) -> tuple[float, float, float, float]:
    return (frame.x, frame.y, frame.width, frame.height)  # type: ignore[attr-defined]


def test_registry_approves_only_the_two_reviewed_runtime_boards() -> None:
    module = load_board_catalog_module()
    catalog = module.validate_catalog(HANGBOARDS_ROOT / "catalog.json")
    approved = {entry.id: entry.path for entry in catalog.entries if entry.status == "approved"}

    assert approved == {
        "metolius.wood-grips-compact-ii": "metolius-wood-grips-compact-ii",
        "trango.rock-prodigy-training-center": "trango-rock-prodigy-training-center",
    }


def test_compact_package_preserves_runtime_inventory_semantics_and_artwork() -> None:
    module = load_board_catalog_module()
    package = module.load_approved_package(COMPACT_ROOT)

    assert tuple((hold.id, hold.name) for hold in package.board.holds) == COMPACT_HOLDS
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
    assert package.board.presentation_asset_path == "assets/CompactBoardIllustration.png"
    assert _canonical_digest(COMPACT_ROOT / "artwork.json") == EXPECTED_ARTWORK_DIGESTS[package.board.id]


def test_rock_prodigy_package_preserves_runtime_inventory_semantics_and_artwork() -> None:
    module = load_board_catalog_module()
    package = module.load_approved_package(ROCK_PRODIGY_ROOT)

    assert tuple((hold.id, hold.name) for hold in package.board.holds) == ROCK_PRODIGY_HOLDS
    assert dict(package.semantics.semantic_holds) == ROCK_PRODIGY_SEMANTICS
    assert _frame_tuple(package.artwork.canvas_frame) == (0.015, 0.020, 0.970, 0.960)
    assert tuple(layer.id for layer in package.artwork.layers) == (
        "left-main-face", "left-upper-tab", "left-lower-tab", "left-outer-block",
        "left-top-jug", "center-separator", "right-main-face", "right-upper-tab",
        "right-lower-tab", "right-outer-block", "right-top-jug",
    )
    expected_piece_ids = tuple(
        piece_id
        for slug, _ in ROCK_PRODIGY_LEFT_HOLDS
        for piece_id in (
            f"trango.rptc.left.{slug}.{'surface' if slug == 'top-jug' else 'rail' if slug in {'large-open-rail', 'small-crimp-rail'} else 'slot' if slug == 'three-finger-slot' else 'crimp' if slug == 'thin-crimp' else 'pocket' if slug.endswith('pocket') else 'outer-contact'}",
            f"trango.rptc.right.{slug}.{'surface' if slug == 'top-jug' else 'rail' if slug in {'large-open-rail', 'small-crimp-rail'} else 'slot' if slug == 'three-finger-slot' else 'crimp' if slug == 'thin-crimp' else 'pocket' if slug.endswith('pocket') else 'outer-contact'}",
        )
    )
    assert tuple(piece.id for piece in package.artwork.hold_pieces) == expected_piece_ids
    assert package.artwork.hold_ids == {hold_id for hold_id, _ in ROCK_PRODIGY_HOLDS}
    assert package.board.presentation_asset_path is None
    assert _canonical_digest(ROCK_PRODIGY_ROOT / "artwork.json") == EXPECTED_ARTWORK_DIGESTS[package.board.id]


def test_compact_screwless_asset_is_a_six_mask_pixel_local_repair() -> None:
    source_path = COMPACT_ROOT / "review" / "presentation-repair" / "CompactBoardIllustration.original.png"
    repaired_path = COMPACT_ROOT / "assets" / "CompactBoardIllustration.png"
    source = Image.open(source_path).convert("RGB")
    repaired = Image.open(repaired_path).convert("RGB")

    assert source.size == repaired.size == (1774, 457)
    assert hashlib.sha256(source_path.read_bytes()).hexdigest() == "5d687fb6e1a33f0f1d9ae221facfc2c831de66d0f9b95b1febadfd924c631b34"
    difference = ImageChops.difference(source, repaired)
    changed_pixels = set()
    for y in range(source.height):
        for x in range(source.width):
            if difference.getpixel((x, y)) != (0, 0, 0):
                changed_pixels.add((x, y))

    assert changed_pixels
    assert all(
        any((x - center_x) ** 2 + (y - center_y) ** 2 <= radius ** 2 for center_x, center_y, radius in COMPACT_REPAIR_MASKS)
        for x, y in changed_pixels
    )
    for center_x, center_y, radius in COMPACT_REPAIR_MASKS:
        assert any(
            (x - center_x) ** 2 + (y - center_y) ** 2 <= radius ** 2
            for x, y in changed_pixels
        )
        repaired_pixels = [
            repaired.getpixel((x, y))
            for y in range(center_y - radius, center_y + radius + 1)
            for x in range(center_x - radius, center_x + radius + 1)
            if (x - center_x) ** 2 + (y - center_y) ** 2 <= radius ** 2
        ]
        # Every formerly dark fastener pixel is now in the surrounding wood-tone range.
        assert min(sum(pixel) for pixel in repaired_pixels) > 500

    evidence = json.loads((COMPACT_ROOT / "evidence.json").read_text(encoding="utf-8"))
    assert evidence["assetEvidence"]["assets/CompactBoardIllustration.png"]["method"] == "external-generative-adaptation"


def test_reference_assets_and_unreviewed_rock_catalog_material_stay_segregated() -> None:
    compact_reference = COMPACT_ROOT / "assets" / "WoodGripsCompactII.jpg"
    assert hashlib.sha256(compact_reference.read_bytes()).hexdigest() == "c101a319076448be38977c606b5be57f1f254e2fe273b0c56a69ca2f52bdb596"

    quarantine = ROCK_PRODIGY_ROOT / "review" / "unreviewed-generated-catalog"
    assert hashlib.sha256((quarantine / "assets" / "primary.png").read_bytes()).hexdigest() == "8d5c4e853a4186a0ca21cca32b57cd6844d9644a4a9b5dacdedfc9287fc22a35"
    assert hashlib.sha256((quarantine / "assets" / "flat.png").read_bytes()).hexdigest() == "f6904ef9ce7b64d35cc5b776a5249769f9fb108f86066886db2c0bd2427fed44"
    assert hashlib.sha256((quarantine / "review" / "outline.approx.json").read_bytes()).hexdigest() == "5284b158e75150b1328bd0610e50537aff2280439b3e9bf2aba97e9586465319"
    assert not (ROCK_PRODIGY_ROOT / "assets").exists()
    assert set(json.loads((ROCK_PRODIGY_ROOT / "evidence.json").read_text(encoding="utf-8"))["assetEvidence"]) == set()
