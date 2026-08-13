from __future__ import annotations

import hashlib
import json
from pathlib import Path

from PIL import Image, ImageChops

from conftest import load_board_catalog_module


REPO_ROOT = Path(__file__).resolve().parents[3]
HANGBOARDS_ROOT = REPO_ROOT / "Hangboards"
FIXTURE_ROOT = Path(__file__).parent / "fixtures" / "approved_board_packages"
COMPACT_ROOT = HANGBOARDS_ROOT / "metolius-wood-grips-compact-ii"
ROCK_PRODIGY_ROOT = HANGBOARDS_ROOT / "trango-rock-prodigy-training-center"
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

COMPACT_REPAIR_MASKS = (
    (374, 148, 18),
    (743, 148, 18),
    (1035, 148, 18),
    (1400, 148, 18),
    (405, 309, 18),
    (1371, 309, 18),
)


def _frame_tuple(frame: object) -> tuple[float, float, float, float]:
    return (frame.x, frame.y, frame.width, frame.height)  # type: ignore[attr-defined]


def _load_preservation_fixture(name: str) -> dict[str, object]:
    return json.loads(
        (FIXTURE_ROOT / f"{name}.pre-migration.json").read_text(encoding="utf-8")
    )


def _assert_runtime_metadata_preserved(package: object, expected: dict[str, object]) -> None:
    board = package.board  # type: ignore[attr-defined]
    assert board.id == expected["id"]
    assert board.facts["manufacturer"] == expected["manufacturer"]
    assert board.facts["name"] == expected["name"]
    assert board.facts["subtitle"] == expected["subtitle"]
    assert board.facts["productURL"] == expected["productURL"]
    assert board.facts["dimensions"] == expected["dimensions"]
    assert board.facts["aspectRatio"] == expected["aspectRatio"]

    expected_holds = expected["holds"]
    assert isinstance(expected_holds, list)
    assert len(board.holds) == len(expected_holds)
    for actual, raw in zip(board.holds, expected_holds, strict=True):
        assert isinstance(raw, dict)
        assert actual.id == raw["id"]
        assert actual.name == raw["name"]
        assert actual.short_label == raw["shortLabel"]
        assert actual.detail == raw["detail"]
        assert actual.kind == raw["kind"]
        assert _frame_tuple(actual.frame) == tuple(raw["frame"][key] for key in ("x", "y", "width", "height"))
        assert actual.size_millimeters == raw["sizeMillimeters"]
        expected_range = raw["depthRangeMillimeters"]
        if expected_range is None:
            assert actual.depth_range_millimeters is None
        else:
            assert actual.depth_range_millimeters is not None
            assert actual.depth_range_millimeters.lower_bound == expected_range["lowerBound"]
            assert actual.depth_range_millimeters.upper_bound == expected_range["upperBound"]
        assert actual.grip_type == raw["gripType"]
        assert actual.finger_capacity == raw["fingerCapacity"]
        assert actual.cue_style == raw["cueStyle"]
        assert actual.features == tuple(raw["features"])

    expected_evidence_keys = {
        f"{raw['id']}.{field}"
        for raw in expected_holds
        for field in RUNTIME_HOLD_FIELDS
    }
    assert set(package.evidence.hold_evidence) == expected_evidence_keys  # type: ignore[attr-defined]
    for mapping in package.evidence.hold_evidence.values():  # type: ignore[attr-defined]
        assert mapping.method == "reviewed-human-authored-normalization"
        assert "pre-migration-runtime" in mapping.source_ids
    subtitle_evidence = package.evidence.field_evidence["subtitle"]  # type: ignore[attr-defined]
    assert subtitle_evidence.method == "reviewed-human-authored-normalization"
    assert "pre-migration-runtime" in subtitle_evidence.source_ids


def _assert_artwork_preserved(package_root: Path, expected: dict[str, object]) -> None:
    actual = json.loads((package_root / "artwork.json").read_text(encoding="utf-8"))
    assert actual["schemaVersion"] == expected["schemaVersion"]
    assert actual["boardID"] == expected["boardID"]
    assert actual["canvasFrame"] == expected["canvasFrame"]
    assert actual["palette"] == expected["palette"]
    # These deep comparisons independently freeze every path command, role,
    # frame, shape, piece association, and hold treatment from the Swift design.
    assert actual["silhouette"] == expected["silhouette"]
    assert actual["layers"] == expected["layers"]
    assert actual["holdPieces"] == expected["holdPieces"]


def test_registry_approves_only_the_two_reviewed_runtime_boards() -> None:
    module = load_board_catalog_module()
    catalog = module.validate_catalog(HANGBOARDS_ROOT / "catalog.json")
    approved = {entry.id: entry.path for entry in catalog.entries}

    assert approved == {
        "metolius.wood-grips-compact-ii": "metolius-wood-grips-compact-ii",
        "trango.rock-prodigy-training-center": "trango-rock-prodigy-training-center",
    }


def test_compact_package_preserves_runtime_inventory_semantics_and_artwork() -> None:
    module = load_board_catalog_module()
    package = module.load_board_package(COMPACT_ROOT)
    fixture = _load_preservation_fixture("metolius-wood-grips-compact-ii")
    assert fixture["sourceRevision"] == "f1761e7"
    assert fixture["runtimeMetadataSource"] == "HangTen/Models/GeneratedBoardCatalog.swift"
    assert fixture["artworkSource"] == "HangTen/Views/MetoliusCompactIIDesign.swift"
    expected_board = fixture["board"]
    expected_artwork = fixture["artwork"]
    assert isinstance(expected_board, dict)
    assert isinstance(expected_artwork, dict)

    assert tuple((hold.id, hold.name) for hold in package.board.holds) == COMPACT_HOLDS
    _assert_runtime_metadata_preserved(package, expected_board)
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
    _assert_artwork_preserved(COMPACT_ROOT, expected_artwork)


def test_rock_prodigy_package_preserves_runtime_inventory_semantics_and_artwork() -> None:
    module = load_board_catalog_module()
    package = module.load_board_package(ROCK_PRODIGY_ROOT)
    fixture = _load_preservation_fixture("trango-rock-prodigy-training-center")
    assert fixture["sourceRevision"] == "f1761e7"
    assert fixture["runtimeMetadataSource"] == "HangTen/Models/TrainingModels.swift"
    assert fixture["artworkSource"] == "HangTen/Views/RockProdigyTrainingCenterDesign.swift"
    expected_board = fixture["board"]
    expected_artwork = fixture["artwork"]
    assert isinstance(expected_board, dict)
    assert isinstance(expected_artwork, dict)

    assert tuple((hold.id, hold.name) for hold in package.board.holds) == ROCK_PRODIGY_HOLDS
    _assert_runtime_metadata_preserved(package, expected_board)
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
    _assert_artwork_preserved(ROCK_PRODIGY_ROOT, expected_artwork)


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
