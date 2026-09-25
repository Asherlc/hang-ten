from __future__ import annotations

import hashlib
import json
import re
import shutil
import zipfile
from pathlib import Path

import pytest
from PIL import Image

from _board_package_helpers import document_contact_geometry
from conftest import (
    PRIMARY_PNG_BYTES,
    load_board_catalog_module,
    package_board_text,
    package_roots,
)


REPO_ROOT = Path(__file__).resolve().parents[3]
HANGBOARDS_ROOT = REPO_ROOT / "Hangboards"
COMPACT_ROOT = HANGBOARDS_ROOT / "metolius-wood-grips-compact-ii"
CLIMBERS_EDGE_ROOT = HANGBOARDS_ROOT / "metolius-climbers-edge"
CONTACT_ROOT = HANGBOARDS_ROOT / "metolius-contact"
DELUXE_ROOT = HANGBOARDS_ROOT / "metolius-wood-grips-deluxe-ii"
FOUNDRY_ROOT = HANGBOARDS_ROOT / "metolius-foundry"
PRIME_RIB_ROOT = HANGBOARDS_ROOT / "metolius-prime-rib"
PROJECT_ROOT = HANGBOARDS_ROOT / "metolius-project"
FLASH_BOARD_ROOT = HANGBOARDS_ROOT / "tension-flash-board"
LIGHT_RAIL_ROOT = HANGBOARDS_ROOT / "metolius-light-rail-2"
ROCK_RINGS_ROOT = HANGBOARDS_ROOT / "metolius-rock-rings-3d"
YY_TRAVELBOARD_ROOT = HANGBOARDS_ROOT / "yy-travelboard"
YY_BAGUETTE_ROOT = HANGBOARDS_ROOT / "yy-baguette"
YY_BAGUETTE_EVO_ROOT = HANGBOARDS_ROOT / "yy-baguette-evo"
YY_PENTA_EVO_ROOT = HANGBOARDS_ROOT / "yy-penta-evo"
TRAINING_TILES_ROOT = HANGBOARDS_ROOT / "soill-training-tiles"
MAMMUT_DIAMOND_ROOT = HANGBOARDS_ROOT / "mammut-diamond-finger"
PIVOT_ROOT = HANGBOARDS_ROOT / "trango-rock-prodigy-pivot"
SIMULATOR_3D_ROOT = HANGBOARDS_ROOT / "metolius-simulator-3d"
HELIUM_ROOT = HANGBOARDS_ROOT / "crimptonite-helium-mobile"
POKER_ROOT = HANGBOARDS_ROOT / "owl-climb-poker"
J_BRYANT_FTG32_ROOT = HANGBOARDS_ROOT / "j-bryant-ftg-32"


def test_poker_four_faces_keep_all_34_contacts_on_one_hash_bound_model() -> None:
    """Catch a dropped Face D restore, cross-face selection, or raster fallback."""
    board = json.loads(package_board_text(POKER_ROOT))
    assert board["schemaVersion"] == 3
    assert len(board["presentations"]) == 1
    presentation = board["presentations"][0]
    assert presentation["id"] == "primary" and presentation["isDefault"] is True
    media = presentation["media"]
    assert set(media) == {"type", "assetPath", "descriptorPath", "display", "orientation"}
    assert media["type"] == "model"
    assert {p.relative_to(POKER_ROOT).as_posix() for p in POKER_ROOT.rglob("*") if p.is_file()} == {
        "board.json", "assets/primary.usdz", "assets/primary.model.json"
    }
    base = {
        "left-outer-slot", "left-single-pocket", "left-dual-pocket", "center-pull-up-slot",
        "right-dual-pocket", "right-single-pocket", "right-outer-slot",
    }
    face_contacts = {
        "face-a": {"face-a-" + suffix for suffix in base},
        "face-b": {"face-b-" + suffix for suffix in base | {"left-deep-sloper", "right-deep-sloper"}},
        "face-c": {"face-c-" + suffix for suffix in base | {"left-shallow-half-round", "right-shallow-half-round"}},
        "face-d": {"face-d-" + suffix for suffix in base | {"left-deep-rounded-recess", "right-deep-rounded-recess"}},
    }
    expected = set().union(*face_contacts.values())
    assert len(expected) == 34
    assert {c["id"] for c in board["contacts"]} == expected
    assert {p["id"]: set(p["contactIDs"]) for p in board["positions"]} == face_contacts
    assert all(p["presentationID"] == "primary" for p in board["positions"])
    assert media["orientation"] == {"pivot": "modelBoundsCenter", "rotations": {
        "face-a": [0, 0, 0, 1], "face-b": [0.707106781, 0, 0, 0.707106781],
        "face-c": [1, 0, 0, 0], "face-d": [-0.707106781, 0, 0, 0.707106781],
    }}
    descriptor = json.loads((POKER_ROOT / media["descriptorPath"]).read_text())
    assert descriptor["schemaVersion"] == 1
    assert descriptor["modelSHA256"] == hashlib.sha256((POKER_ROOT / media["assetPath"]).read_bytes()).hexdigest()
    assert set(descriptor["contacts"]) == expected
    assert {n.get("contactID") for n in descriptor["nodes"] if n["role"] == "contact"} == expected
    for node in descriptor["nodes"]:
        assert node["role"] in {"body", "contact"}
        assert not any(word in node["nodeID"].lower() for word in ("screw", "mount", "bracket", "fastener", "cleat", "cord", "anchor"))
    assert descriptor["modelBounds"]["min"] == pytest.approx([-.33, -.05, -.05], abs=1e-6)
    assert descriptor["modelBounds"]["max"] == pytest.approx([.33, .05, .05], abs=1e-6)
    with zipfile.ZipFile(POKER_ROOT / media["assetPath"]) as archive:
        assert len(archive.namelist()) == 1
    package = load_board_catalog_module().load_board_package(POKER_ROOT)
    assert package.board.id == "owl-climb.poker"


def test_helium_is_one_model_with_six_exact_physical_contacts() -> None:
    """Catch lost lip merges, extra contacts, stale rasters, or an unbound model."""
    board = json.loads(package_board_text(HELIUM_ROOT))
    assert board["schemaVersion"] == 3
    assert len(board["presentations"]) == 1
    presentation = board["presentations"][0]
    assert presentation["id"] == "primary"
    assert presentation["isDefault"] is True
    assert presentation["derivation"] == {"type": "original"}
    media = presentation["media"]
    assert media["type"] == "model"
    assert set(media) == {"type", "assetPath", "descriptorPath", "display", "suspension"}
    assert {path.relative_to(HELIUM_ROOT).as_posix() for path in HELIUM_ROOT.rglob("*") if path.is_file()} == {
        "board.json", "assets/primary.usdz", "assets/primary.model.json"
    }
    assert media["assetPath"] == "assets/primary.usdz"
    assert media["descriptorPath"] == "assets/primary.model.json"
    descriptor = json.loads((HELIUM_ROOT / media["descriptorPath"]).read_text())
    assert descriptor["schemaVersion"] == 1
    assert descriptor["modelSHA256"] == hashlib.sha256((HELIUM_ROOT / media["assetPath"]).read_bytes()).hexdigest()
    with zipfile.ZipFile(HELIUM_ROOT / media["assetPath"]) as archive:
        assert len(archive.namelist()) == 1
        assert Path(archive.namelist()[0]).suffix in {".usda", ".usdc"}
    expected = {
        "edge-14": {"he-L-lower-14", "he-R-lower-14"},
        "edge-22": {"he-L-upper-22", "he-R-upper-22"},
        "center-edge-10": {"he-C-lower-10"},
        "center-edge-18": {"he-C-upper-18"},
        "top-jug": {"he-outer-top-jug"},
        "back-jug-sloper": {"he-rear-jug-sloper"},
    }
    assert {contact["id"] for contact in board["contacts"]} == set(expected)
    assert len(board["contacts"]) == 6
    assert set(descriptor["contacts"]) == set(expected)
    # USD identifiers sanitize hyphens; Blender's mesh child may add _001.
    def source_name(node_id: str) -> str:
        """Normalize a USD node ID to the board.json contact naming convention."""
        return node_id.removesuffix("_001").replace("_", "-")

    assert {contact_id: {source_name(node) for node in contact["nodeIDs"]}
            for contact_id, contact in descriptor["contacts"].items()} == expected
    assert {contact_id: {source_name(node["nodeID"]) for node in descriptor["nodes"]
                         if node.get("contactID") == contact_id}
            for contact_id in expected} == expected
    assert board["positions"] == [{"id": "primary", "presentationID": "primary", "contactIDs": [
        "edge-14", "center-edge-18", "edge-22", "center-edge-10", "back-jug-sloper", "top-jug"
    ]}]
    bounds = descriptor["modelBounds"]
    assert [bounds["max"][i] - bounds["min"][i] for i in range(3)] == pytest.approx([0.4, 0.058, 0.024], abs=0.000001)
    nodes = {source_name(node["nodeID"]): node for node in descriptor["nodes"]}
    assert {"front-lead-mouth", "reverse-lead-mouth"} <= set(nodes)
    assert nodes["front-lead-mouth"]["role"] == nodes["reverse-lead-mouth"]["role"] == "attachment"
    assert not any(token in name.lower() for name in nodes for token in ("mount", "screw", "fastener", "cleat", "bracket", "hardware", "cord", "anchor"))


def test_helium_represents_only_two_exterior_cord_leads() -> None:
    """Catch fabricated interior routing and attachments bound to selectable lips."""
    board = json.loads(package_board_text(HELIUM_ROOT))
    media = board["presentations"][0]["media"]
    assert media["type"] == "model"
    suspension = media["suspension"]
    assert suspension["type"] == "pairedLeadCord"
    assert set(suspension["passages"]) == {"left", "right"}
    for side in ("left", "right"):
        # Schema requires one point-only mouth per lead; no entry/exit route.
        assert len(suspension["passages"][side]) == 1
        mouth = suspension["passages"][side][0]
        assert set(mouth) == {"id", "nodeID", "pointInModel", "provenance"}
        lead = next(item for item in suspension["attachments"] if item["id"] == f"{side}-lead")
        assert mouth["nodeID"] == lead["nodeID"]
        assert mouth["pointInModel"] == lead["pointInModel"]
    assert len(suspension["attachments"]) == 2
    descriptor = json.loads((HELIUM_ROOT / media["descriptorPath"]).read_text())
    node_roles = {node["nodeID"]: node["role"] for node in descriptor["nodes"]}
    assert {tuple(lead["pointInModel"]) for lead in suspension["attachments"]} == {
        (-0.186, 0, 0.012), (0.186, 0, 0.012)
    }
    for lead in suspension["attachments"]:
        assert node_roles[lead["nodeID"]] == "attachment"
        assert "contactPointsInModel" not in lead
        assert "authored-display-estimate" in lead["provenance"]
    assert suspension["anchor"]["visibility"] == "invisible"
    assert set(suspension["canonicalPoses"]) == {"primary"}
    assert "authored-display-estimate" in suspension["anchor"]["provenance"]
    assert "authored-display-estimate" in suspension["cord"]["provenance"]


def test_light_rail_inversion_preserves_entry_identity_and_exposes_the_other_grips() -> None:
    """Catch lost reversibility or a pose that silently invents underside mouths."""
    board = json.loads(package_board_text(LIGHT_RAIL_ROOT))
    assert board.get("positions") == [
        {"id": "20mm-side", "presentationID": "primary", "contactIDs": ["jug-40-20mm-side", "edge-20"]},
        {"id": "15mm-side", "presentationID": "primary", "contactIDs": ["jug-40-15mm-side", "edge-15"]},
    ]
    suspension = board["presentations"][0]["media"]["suspension"]
    poses = suspension["canonicalPoses"]
    assert set(poses) == {"20mm-side", "15mm-side"}
    assert poses["20mm-side"]["rotation"] == [0, 0, 0, 1]
    assert poses["15mm-side"]["rotation"] == [0, 0, 1, 0]
    assert all("attachmentPoints" not in pose for pose in poses.values())
    routes = poses["15mm-side"]["cordContactPoints"]
    assert set(routes) == {"left-lead", "right-lead"}
    # Each route must approach its original physical entry from above in model
    # coordinates; inversion rotates that same entry underneath the model.
    for lead in suspension["attachments"]:
        route = routes[lead["id"]]
        assert route[-1][0] == lead["pointInModel"][0]
        assert route[-1][1] > lead["pointInModel"][1]
        assert any(abs(point[0]) > .2285 for point in route)


def test_light_rail_inverted_guides_stay_close_to_the_existing_end_silhouette() -> None:
    """Catch floating end hooks that pass clearance but misrepresent flexible cord."""
    board = json.loads(package_board_text(LIGHT_RAIL_ROOT))
    media = board["presentations"][0]["media"]
    descriptor = json.loads((LIGHT_RAIL_ROOT / media["descriptorPath"]).read_text())
    suspension = media["suspension"]
    bounds = descriptor["modelBounds"]
    for route in suspension["canonicalPoses"]["15mm-side"]["cordContactPoints"].values():
        for point in route:
            # Existing native clearance tests enforce the minimum gap. The
            # maximum should stay within two tube radii of the real envelope.
            envelope_gap = max(max(bounds["min"][i] - point[i], point[i] - bounds["max"][i], 0)
                               for i in range(3))
            assert envelope_gap <= 2 * suspension["cord"]["radius"]


def _scalar_depth(contact: dict[str, object]) -> int | float | None:
    """Return the scalar depth value if the contact has a single fixed depth, else None."""
    depth = contact.get("depth")
    if not isinstance(depth, dict):
        return None
    range_value = depth.get("range")
    if not isinstance(range_value, dict) or range_value.get("minimum") != range_value.get("maximum"):
        return None
    value = range_value["minimum"]
    assert isinstance(value, (int, float)) and not isinstance(value, bool)
    return value


def _single_grip_type(contact: dict[str, object]) -> str | None:
    """Return the sole grip type if the contact has exactly one, else None."""
    grip_types = contact.get("gripTypes")
    if not isinstance(grip_types, list) or len(grip_types) != 1:
        return None
    value = grip_types[0]
    assert isinstance(value, str)
    return value


def _assert_model_descriptor(
    root: Path, board: dict[str, object], body_node_ids: str | set[str]
) -> dict[str, object]:
    """Validate the first presentation is a model asset and return the loaded descriptor."""
    presentations = board["presentations"]
    assert isinstance(presentations, list)
    media = presentations[0]["media"]
    assert media["type"] == "model"
    assert media["assetPath"] == "assets/primary.usdz"
    assert media["descriptorPath"] == "assets/primary.model.json"
    assert "contactGeometry" not in media
    # A CAD-backed package carries its own authoring source, named after its
    # directory, instead of board.json: board.json is generated from the FCStd
    # at build time. The source is not a runtime resource.
    source = f"{root.name}.FCStd"
    metadata = source if (root / source).is_file() else "board.json"
    assert {
        path.relative_to(root).as_posix()
        for path in root.rglob("*")
        if path.is_file()
    } == {metadata, "assets/primary.usdz", "assets/primary.model.json"}
    descriptor = json.loads(
        (root / media["descriptorPath"]).read_text(encoding="utf-8")
    )
    assert descriptor["schemaVersion"] == 1
    assert descriptor["coordinateFrame"] == "hang-ten-board-v1"
    assert descriptor["modelSHA256"] == hashlib.sha256(
        (root / media["assetPath"]).read_bytes()
    ).hexdigest()
    contacts = board["contacts"]
    assert isinstance(contacts, list)
    assert set(descriptor["contacts"]) == {contact["id"] for contact in contacts}
    expected_body_ids = {body_node_ids} if isinstance(body_node_ids, str) else body_node_ids
    assert [node for node in descriptor["nodes"] if node["role"] == "body"] == [
        {"nodeID": node_id, "role": "body"} for node_id in sorted(expected_body_ids)
    ]
    for contact_id, contact in descriptor["contacts"].items():
        assert contact["nodeIDs"] == [
            node["nodeID"]
            for node in descriptor["nodes"]
            if node.get("contactID") == contact_id
        ]
    return descriptor


def test_j_bryant_ftg32_is_one_hash_bound_model_with_exact_half_turn_positions() -> None:
    board = json.loads(package_board_text(J_BRYANT_FTG32_ROOT))
    descriptor = _assert_model_descriptor(J_BRYANT_FTG32_ROOT, board, "Cube_001")
    assert board["id"] == "j-bryant.ftg-32"
    assert board["revisionID"] == "amazon-b0fzgy19t9-ftg-32-2026-09"
    assert board["manufacturer"] == "J Bryant"
    assert board["name"] == "FTG-32 Portable Grip Block"
    assert board["dimensions"] == "10.5 × 7.7 × 3.7 cm"
    assert board["aspectRatio"] == pytest.approx(105 / 77)
    assert "handCapacity" not in board
    assert board["equipmentObjects"] == [{"id": "primary"}]
    assert len(board["presentations"]) == 1
    assert [(c["id"], c["kind"], c["depth"]["range"], c["gripTypes"]) for c in board["contacts"]] == [
        ("edge-16", "edge", {"minimum": 16, "maximum": 16}, []),
        ("edge-25", "edge", {"minimum": 25, "maximum": 25}, []),
    ]
    assert all(set(c) == {"id", "equipmentObjectID", "name", "kind", "depth", "gripTypes"} for c in board["contacts"])
    assert [(p["id"], p["contactIDs"]) for p in board["positions"]] == [
        ("edge-25-down", ["edge-25"]),
        ("edge-16-down", ["edge-16"]),
    ]
    media = board["presentations"][0]["media"]
    assert list(media["orientation"]["rotations"]) == ["edge-16-down", "edge-25-down"]
    assert media["orientation"]["rotations"] == {
        "edge-25-down": [0, 0, 0, 1],
        "edge-16-down": [0, 0, 1, 0],
    }
    suspension = media["suspension"]
    assert suspension["type"] == "pairedLeadCord"
    # Pose-local directions compensate for the exact in-plane half-turn so
    # either selected lower ledge is viewed from above in the canonical scene.
    assert {
        position_id: pose["camera"]["viewDirection"]
        for position_id, pose in suspension["canonicalPoses"].items()
    } == {
        "edge-25-down": [0, -0.3746065934, -0.9271838546],
        "edge-16-down": [0, 0.3746065934, -0.9271838546],
    }
    assert [a["id"] for a in suspension["attachments"]] == ["left-lead", "right-lead"]
    assert len({tuple(a["pointInModel"]) for a in suspension["attachments"]}) == 2
    assert all(a["nodeID"] == "Cube_001" for a in suspension["attachments"])
    assert all("displayEstimate" in a["provenance"] for a in suspension["attachments"])
    assert suspension["anchor"]["visibility"] == "invisible"
    assert "displayEstimate" in suspension["anchor"]["provenance"]
    assert "displayEstimate" in suspension["cord"]["provenance"]
    assert all(
        p["nodeID"] == "Cube_001" and "displayEstimate" in p["provenance"]
        for passages in suspension["passages"].values() for p in passages
    )
    assert "rear" not in " ".join(node["nodeID"].casefold() for node in descriptor["nodes"])
    spans = [descriptor["modelBounds"]["max"][i] - descriptor["modelBounds"]["min"][i] for i in range(3)]
    assert spans == pytest.approx([0.105, 0.077, 0.037], abs=1e-6)
    assert [(node["nodeID"], node["role"], node.get("contactID")) for node in descriptor["nodes"]] == [
        ("Cube_001", "body", None),
        ("edge_16_mesh_001", "contact", "edge-16"),
        ("edge_25_mesh_001", "contact", "edge-25"),
    ]


def test_climbers_edge_is_a_hash_bound_model_only_package() -> None:
    board = json.loads(package_board_text(CLIMBERS_EDGE_ROOT))
    assert len(board["presentations"]) == 1
    descriptor = _assert_model_descriptor(
        CLIMBERS_EDGE_ROOT, board, {"body_001"}
    )
    bounds = descriptor["modelBounds"]
    front_aspect = (bounds["max"][0] - bounds["min"][0]) / (
        bounds["max"][1] - bounds["min"][1]
    )
    assert board["aspectRatio"] == pytest.approx(front_aspect)
    assert board["presentations"][0]["aspectRatio"] == pytest.approx(front_aspect)


def test_simulator_3d_models_flat_and_round_sloper_zones_separately() -> None:
    board = json.loads(package_board_text(SIMULATOR_3D_ROOT))
    descriptor = _assert_model_descriptor(
        SIMULATOR_3D_ROOT, board, {"board_body_001"}
    )
    contacts = {contact["id"]: contact for contact in board["contacts"]}

    assert {"flat-sloper-2-left", "round-sloper-3-center", "flat-sloper-2-right"} <= set(contacts)
    assert "round-sloper-3-left" not in contacts
    assert "round-sloper-3-right" not in contacts
    assert contacts["flat-sloper-2-left"]["shape"] == "flat"
    assert contacts["round-sloper-3-center"]["shape"] == "round"
    assert contacts["flat-sloper-2-right"]["shape"] == "flat"
    assert descriptor["contacts"]["flat-sloper-2-left"]["nodeIDs"] == ["hold_02_left_001"]
    assert descriptor["contacts"]["round-sloper-3-center"]["nodeIDs"] == [
        "hold_03_left_001", "hold_03_right_001"
    ]
    assert descriptor["contacts"]["flat-sloper-2-right"]["nodeIDs"] == ["hold_02_right_001"]


SOURCE_REGISTER = (
    REPO_ROOT / "docs/source-audits/2026-09-20-batch-04-3d-source-register.json"
)

PIVOT_SLOTS = (
    "upper-sloped-crimp",
    "outer-sloped-crimp",
    "variable-edge",
    "medium-crimp",
    "large-crimp",
    "two-finger-pocket",
    "three-finger-pocket",
    "outer-wedge-pinch",
    "lower-sloper",
)

PIVOT_APERTURES = ("three-finger-end-window", "two-finger-opening")

HARDWARE_TOKENS = (
    "fastener",
    "screw",
    "mount",
    "cleat",
    "bracket",
    "hardware",
    "bolt",
    "counterbore",
    "set-screw",
    "rail-backer",
    "anchor",
    "cord",
)


def _source_node_name(node_id: str) -> str:
    """USD identifiers sanitize hyphens; Blender's mesh child may add _001."""
    return node_id.removesuffix("_001").replace("_", "-")


def test_batch04_model_geometry_retains_only_documented_attachment_openings() -> None:
    """Catch a lost finger opening, an invented fastener bore, or a stray p4."""
    source_boards = json.loads(SOURCE_REGISTER.read_text())["boards"]
    expected = {
        "crimptonite-helium-mobile": {
            "boardID": "crimptonite.helium-mobile",
            "apertures": {"front-lead-mouth", "reverse-lead-mouth"},
        },
        "metolius-light-rail-2": {
            "boardID": "metolius.light-rail-2",
            "apertures": {"left-upper-entry", "right-upper-entry"},
        },
        "metolius-rock-rings-3d": {
            "boardID": "metolius.rock-rings-3d",
            "apertures": {"roof-exit", "lateral-window"},
        },
        "owl-climb-poker": {"boardID": "owl-climb.poker", "apertures": set()},
        "yy-penta-evo": {
            "boardID": "yy.penta-evo",
            "apertures": {"central-ring", "upper-band-exterior"},
        },
        "trango-rock-prodigy-pivot": {
            "boardID": "trango.rock-prodigy-pivot",
            "apertures": {"two-finger-opening", "three-finger-end-window"},
        },
    }
    for slug, requirement in expected.items():
        descriptor = json.loads(
            (HANGBOARDS_ROOT / slug / "assets/primary.model.json").read_text()
        )
        node_ids = {_source_node_name(node["nodeID"]) for node in descriptor["nodes"]}
        attachments = {
            _source_node_name(node["nodeID"])
            for node in descriptor["nodes"]
            if node["role"] == "attachment"
        }
        assert requirement["apertures"] <= node_ids, slug
        assert attachments == requirement["apertures"], slug
        assert not any(
            token in node_id
            for node_id in node_ids
            for token in HARDWARE_TOKENS
        ), slug
        assert source_boards[requirement["boardID"]]["approvedApertures"] == sorted(
            requirement["apertures"]
        ), slug
    board = json.loads(package_board_text(PIVOT_ROOT))
    assert [position["id"] for position in board["positions"]] == ["p1", "p2", "p3", "p5"]


def test_pivot_renders_one_reflected_half_with_eighteen_physical_contacts() -> None:
    """Catch a duplicated right half, a retained raster record, or a lost slot map."""
    raw_board = package_board_text(PIVOT_ROOT)
    board = json.loads(raw_board)
    assert board["schemaVersion"] == 3
    assert board["id"] == "trango.rock-prodigy-pivot"
    assert [item["id"] for item in board["equipmentObjects"]] == ["left-half", "right-half"]
    assert {
        path.relative_to(PIVOT_ROOT).as_posix()
        for path in PIVOT_ROOT.rglob("*")
        if path.is_file()
    } == {"board.json", "assets/primary.usdz", "assets/primary.model.json"}

    assert len(board["contacts"]) == 18
    expected_contacts = {f"{slot}-{side}" for slot in PIVOT_SLOTS for side in ("left", "right")}
    assert {contact["id"] for contact in board["contacts"]} == expected_contacts
    for contact in board["contacts"]:
        side = contact["id"].rsplit("-", 1)[1]
        assert contact["equipmentObjectID"] == f"{side}-half", contact["id"]
    assert not any(
        "orientation-" in contact["id"] for contact in board["contacts"]
    )

    assert len(board["presentations"]) == 1
    presentation = board["presentations"][0]
    assert presentation["isDefault"] is True
    media = presentation["media"]
    assert media["type"] == "model"
    assert set(media) == {"type", "assetPath", "descriptorPath", "display", "instances"}
    assert "orientation" not in media and "suspension" not in media
    assert "contactGeometry" not in raw_board
    assert "raster" not in raw_board

    instances = media["instances"]
    assert len(instances) == 2
    left, right = instances
    assert [item["equipmentObjectID"] for item in instances] == ["left-half", "right-half"]
    assert "reflection" not in left["baseTransform"]
    assert right["baseTransform"]["reflection"] == "x"
    for instance in instances:
        assert instance["baseTransform"]["rotation"] == [0, 0, 0, 1]
        assert instance["baseTransform"]["translation"] == [0, 0, 0]
        assert "suspension" not in instance
        side = instance["equipmentObjectID"].split("-", 1)[0]
        assert instance["contactIDsBySlotID"] == {
            slot: f"{slot}-{side}" for slot in PIVOT_SLOTS
        }
        transforms = instance["positionTransforms"]
        assert list(transforms) == ["p1", "p2", "p3", "p5"]
        for position_id, transform in transforms.items():
            assert set(transform) == {"translation", "rotation"}, position_id
            assert len(transform["translation"]) == 3
            assert len(transform["rotation"]) == 4

    # Nine-decimal lexemes are a raw-text contract, not a decoded-float one.
    lexemes = re.findall(r'"translation"\s*:\s*\[([^\]]*)\]', raw_board)
    expected_translation_count = sum(
        1 + len(instance["positionTransforms"]) for instance in instances
    )
    assert len(lexemes) == expected_translation_count
    for lexeme in lexemes:
        for component in lexeme.replace("\n", " ").split(","):
            assert re.fullmatch(r"-?(?:0|[1-9][0-9]*)\.[0-9]{9}", component.strip())

    assert [position["id"] for position in board["positions"]] == ["p1", "p2", "p3", "p5"]
    for position in board["positions"]:
        assert position["presentationID"] == presentation["id"]
    assert "p4" not in raw_board

    # The right half is mirrored metadata, never a second baked mesh.
    descriptor = json.loads((PIVOT_ROOT / media["descriptorPath"]).read_text())
    assert descriptor["schemaVersion"] == 2
    assert descriptor["coordinateFrame"] == "hang-ten-board-v1"
    assert set(descriptor["contactSlots"]) == set(PIVOT_SLOTS)
    nodes = {_source_node_name(node["nodeID"]): node for node in descriptor["nodes"]}
    assert sum(node["role"] == "body" for node in descriptor["nodes"]) == 1
    assert sorted(
        name for name, node in nodes.items() if node["role"] == "attachment"
    ) == list(PIVOT_APERTURES)
    assert not any(
        token in name for name in nodes for token in HARDWARE_TOKENS
    )
    assert not any("left" in name or "right" in name for name in nodes)
    assert (
        hashlib.sha256((PIVOT_ROOT / media["assetPath"]).read_bytes()).hexdigest()
        == descriptor["modelSHA256"]
    )


def test_pivot_retires_all_72_presentation_ids_through_the_tracked_map() -> None:
    """Catch a retired orientation ID resurrected as a physical contact."""
    register = json.loads(SOURCE_REGISTER.read_text())["boards"]["trango.rock-prodigy-pivot"]
    retired = register["retiredPresentationIDToContactID"]
    assert len(retired) == 72
    board = json.loads(package_board_text(PIVOT_ROOT))
    contact_ids = {contact["id"] for contact in board["contacts"]}
    assert set(retired.values()) == contact_ids
    assert set(retired) >= contact_ids
    assert {
        retired_id for retired_id in retired if "orientation-" in retired_id
    } == set(retired) - contact_ids
    assert register["selectablePositions"] == ["p1", "p2", "p3", "p5"]
    assert register["transitionOnlyPositions"] == ["p4"]
    assert set(register["pivotPatchMappings"].values()) == set(PIVOT_SLOTS)
    assert len(register["pivotPatchMappings"]) == 14
    assert len(register["pivotPatchMappingsByDeliveredID"]) == 28


def test_pivot_is_one_catalog_board_with_orientation_presentations() -> None:
    """A Pivot orientation added as another direct child is a duplicate product."""
    pivot_package_roots = sorted(
        path
        for path in package_roots(HANGBOARDS_ROOT)
        if path.name.startswith("trango-rock-prodigy-pivot")
    )

    assert pivot_package_roots == [PIVOT_ROOT]


def _global_path_segment_signatures(
    geometry: dict[str, object], *, mirror_horizontally: bool = False
) -> list[tuple[object, ...]]:
    """Return canonical global segments, independent of traversal direction."""
    frame = geometry["frame"]
    commands = geometry["shape"]["commands"]

    def global_point(local: list[float]) -> tuple[float, float]:
        """Convert local [0,1] coordinates to global with optional horizontal mirror."""
        x = frame["x"] + local[0] * frame["width"]
        if mirror_horizontally:
            x = 1 - x
        y = frame["y"] + local[1] * frame["height"]
        return (round(x, 12), round(y, 12))

    def line_signature(
        start: tuple[float, float], end: tuple[float, float]
    ) -> tuple[object, ...]:
        """Return an order-invariant signature for a line segment."""
        ordered = min((start, end), (end, start))
        return ("line", *ordered)

    def curve_signature(
        start: tuple[float, float],
        control1: tuple[float, float],
        control2: tuple[float, float],
        end: tuple[float, float],
    ) -> tuple[object, ...]:
        """Return an order-invariant signature for a cubic Bezier curve."""
        forward = (start, control1, control2, end)
        reverse = (end, control2, control1, start)
        return ("curve", *min(forward, reverse))

    start: tuple[float, float] | None = None
    current: tuple[float, float] | None = None
    segments: list[tuple[object, ...]] = []
    for command in commands:
        operation = command["command"]
        if operation == "move":
            start = current = global_point(command["to"])
        elif operation == "line":
            assert current is not None
            end = global_point(command["to"])
            segments.append(line_signature(current, end))
            current = end
        elif operation == "curve":
            assert current is not None
            end = global_point(command["to"])
            segments.append(
                curve_signature(
                    current,
                    global_point(command["control1"]),
                    global_point(command["control2"]),
                    end,
                )
            )
            current = end
        else:
            assert operation == "close"
            assert current is not None and start is not None
            if current != start:
                segments.append(line_signature(current, start))
            current = start
    return sorted(segments)


def _assert_global_paths_are_horizontal_mirrors(
    left: dict[str, object], right: dict[str, object]
) -> None:
    """Assert that two contact geometries are horizontal mirrors of each other."""
    assert _global_path_segment_signatures(
        left, mirror_horizontally=True
    ) == _global_path_segment_signatures(right)


PRIME_RIB_HOLDS = (
    ("edge-38", "38 mm edge", "edge", 38),
    ("edge-23", "23 mm edge", "edge", 23),
    ("edge-15", "15 mm edge", "edge", 15),
)
FOUNDRY_HOLDS = (
    ("pinch-1-left", "Left #1 variable pinch", "pinch", None, None),
    ("jug-2-left", "Left #2 outer jug", "jug", None, None),
    ("pocket-3-left", "Left #3 32 mm 4-finger pocket", "pocket", 32, 4),
    ("pocket-4-left", "Left #4 22 mm 3-finger pocket", "pocket", 22, 3),
    ("pocket-5-left", "Left #5 30 mm 2-finger pocket", "pocket", 30, 2),
    ("pocket-6-left", "Left #6 15 mm 3-finger pocket", "pocket", 15, 3),
    ("pocket-7-left", "Left #7 21 mm 2-finger pocket", "pocket", 21, 2),
    ("sloper-8-center", "Center #8 53 mm flat sloper", "sloper", None, None),
    ("edge-9-center", "Center #9 16 mm edge", "edge", 16, None),
    ("edge-10-center", "Center #10 30 mm edge", "edge", 30, None),
    ("edge-11-center", "Center #11 23 mm edge", "edge", 23, None),
    ("pocket-7-right", "Right #7 21 mm 2-finger pocket", "pocket", 21, 2),
    ("pocket-6-right", "Right #6 15 mm 3-finger pocket", "pocket", 15, 3),
    ("pocket-5-right", "Right #5 30 mm 2-finger pocket", "pocket", 30, 2),
    ("pocket-4-right", "Right #4 22 mm 3-finger pocket", "pocket", 22, 3),
    ("pocket-3-right", "Right #3 32 mm 4-finger pocket", "pocket", 32, 4),
    ("jug-2-right", "Right #2 outer jug", "jug", None, None),
    ("pinch-1-right", "Right #1 variable pinch", "pinch", None, None),
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

# Each value is (source-backed kind, scalar depth, capacity, structural pocket
# grip, shape). Sloper descriptors are not scalar depths, non-pocket
# capacities are not published, and the manufacturer publishes no additional
# shape metadata for edges or pockets.
COMPACT_HOLD_SOURCE_FACTS = {
    "jug-left": ("jug", None, None, None, None),
    "sloper-flat-left": ("sloper", None, None, None, "flat"),
    "sloper-round-center": ("sloper", None, None, None, "round"),
    "sloper-flat-right": ("sloper", None, None, None, "flat"),
    "jug-right": ("jug", None, None, None, None),
    "edge-29-left": ("edge", 29, None, None, None),
    "pocket-29-three-left": ("pocket", 29, 3, "threeFingerPocket", None),
    "pocket-29-two-left": ("pocket", 29, 2, "twoFingerPocket", None),
    "pocket-29-four-center": ("pocket", 29, 4, "fourFingerPocket", None),
    "pocket-29-two-right": ("pocket", 29, 2, "twoFingerPocket", None),
    "pocket-29-three-right": ("pocket", 29, 3, "threeFingerPocket", None),
    "edge-29-right": ("edge", 29, None, None, None),
    "edge-19-left": ("edge", 19, None, None, None),
    "pocket-19-three-left": ("pocket", 19, 3, "threeFingerPocket", None),
    "pocket-19-three-right": ("pocket", 19, 3, "threeFingerPocket", None),
    "pocket-19-two-left": ("pocket", 19, 2, "twoFingerPocket", None),
    "pocket-19-two-right": ("pocket", 19, 2, "twoFingerPocket", None),
    "pocket-19-four-center": ("pocket", 19, 4, "fourFingerPocket", None),
    "edge-19-right": ("edge", 19, None, None, None),
}

def test_direct_discovery_finds_the_exact_complete_inventory_without_drafts() -> None:
    inventory = load_board_catalog_module().discover_board_packages(HANGBOARDS_ROOT)

    discovered = {(package.board.id, package.root.name) for package in inventory.packages}

    expected_packages = {
        ("metolius.wood-grips-compact-ii", "metolius-wood-grips-compact-ii"),
        ("metolius.wood-grips-deluxe-ii", "metolius-wood-grips-deluxe-ii"),
        ("beastmaker-1000", "beastmaker-1000"),
        ("beastmaker-2000", "beastmaker-2000"),
        ("dewoodstok-woodbord", "dewoodstok-woodbord"),
        ("owl-climb.poker", "owl-climb-poker"),
        ("escape-beta-22", "escape-beta-22"),
        ("escape.unlimited", "escape-unlimited"),
        ("evolv-kilter-basic-long", "evolv-kilter-basic-long"),
        ("frictitious.doormount-pro-7", "frictitious-doormount-pro-7"),
        ("frictitious.megalith", "frictitious-megalith"),
        ("frictitious.port-a-board", "frictitious-port-a-board"),
        ("j-bryant.ftg-32", "j-bryant-ftg-32"),
        ("lattice-triple-rung", "lattice-triple-rung"),
        ("mammut.diamond-finger", "mammut-diamond-finger"),
        ("metolius.climbers-edge", "metolius-climbers-edge"),
        ("metolius.contact", "metolius-contact"),
        ("metolius.foundry", "metolius-foundry"),
        ("metolius.light-rail-2", "metolius-light-rail-2"),
        ("metolius.rock-rings-3d", "metolius-rock-rings-3d"),
        ("metolius.prime-rib", "metolius-prime-rib"),
        ("metolius.project", "metolius-project"),
        ("metolius.simulator-3d", "metolius-simulator-3d"),
        ("moon.armstrong", "moon-armstrong"),
        ("nature.stoak-board-iii", "nature-stoak-board-iii"),
        ("nature.stone-hanger", "nature-stone-hanger"),
        ("soill.iron-palm-2", "soill-iron-palm-2"),
        ("soill.split-palm", "soill-split-palm"),
        ("soill.training-tiles", "soill-training-tiles"),
        ("target10a.linebreaker-base", "target10a-linebreaker-base"),
        ("the-hangboard.the-hangboard", "the-hangboard"),
        ("trango.rock-prodigy-forge", "trango-rock-prodigy-forge"),
        ("trango.rock-prodigy-natural", "trango-rock-prodigy-natural"),
        ("trango.rock-prodigy-pivot", "trango-rock-prodigy-pivot"),
        (
            "trango.rock-prodigy-training-center",
            "trango-rock-prodigy-training-center",
        ),
        ("tension.grindstone", "tension-grindstone"),
        ("tension.grindstone-original", "tension-grindstone-original"),
        ("tension.grindstone-pro", "tension-grindstone-pro"),
        ("tension.flash-board", "tension-flash-board"),
        ("tension.honestone", "tension-honestone"),
        ("tension.whetstone", "tension-whetstone"),
        ("yy.verticalboard-evo", "yy-verticalboard-evo"),
        ("yy.verticalboard-first", "yy-verticalboard-first"),
        ("yy.verticalboard-light", "yy-verticalboard-light"),
        ("yy.verticalboard-one", "yy-verticalboard-one"),
        ("yy.travelboard", "yy-travelboard"),
        ("yy.baguette", "yy-baguette"),
        ("yy.baguette-evo", "yy-baguette-evo"),
        ("yy.penta-evo", "yy-penta-evo"),
        ("zlagboard.evo", "zlagboard-evo"),
        ("zlagboard.pro", "zlagboard-pro"),
        ("aelith.cyclops-011", "aelith-cyclops-011"),
        ("captain-fingerfood.dual", "captain-fingerfood-dual"),
        ("captain-fingerfood.pocket", "captain-fingerfood-pocket"),
        ("captain-fingerfood.unlevel", "captain-fingerfood-unlevel"),
        ("crimptonite.helium-mobile", "crimptonite-helium-mobile"),
        ("frictitious.nug", "frictitious-nug"),
        ("lattice.mini-bar", "lattice-mini-bar"),
        ("lattice.mxedge-lift-small", "lattice-mxedge-lift-small"),
        ("lattice.mxedge-lift-large", "lattice-mxedge-lift-large"),
        ("nature.stone-hanger-mini", "nature-stone-hanger-mini"),
        ("nature.stone-hanger-mini-karma8a", "nature-stone-hanger-mini-karma8a"),
        ("plateau.lifting-edge", "plateau-lifting-edge"),
        ("clavellium-training-block", "clavellium-training-block"),
    }
    assert discovered == expected_packages
    assert inventory.drafts == ()
    assert not (HANGBOARDS_ROOT / "catalog.json").exists()


def _original_contact_owners(document: dict[str, object]) -> dict[str, str]:
    """Map each contact ID to the original raster presentation that owns it."""
    owners: dict[str, str] = {}
    for presentation in document["presentations"]:
        if presentation["derivation"]["type"] != "original":
            continue
        media = presentation["media"]
        if media["type"] != "raster":
            continue
        for contact_id in media["contactGeometry"]:
            assert contact_id not in owners
            owners[contact_id] = presentation["id"]
    return owners


def _presentation_summary(document: dict[str, object]) -> list[tuple[object, ...]]:
    """Return a compact summary tuple for each presentation in the document."""
    return [
        (
            presentation["id"],
            presentation["name"],
            presentation["media"]["assetPath"],
            presentation["aspectRatio"],
            presentation["isDefault"],
            presentation["derivation"].get("sourcePresentationID"),
            presentation["derivation"].get("isInverted", False),
        )
        for presentation in document["presentations"]
    ]


def test_every_approved_board_uses_schema_v3_typed_presentations() -> None:
    for package_root in package_roots(HANGBOARDS_ROOT):
        document = json.loads(package_board_text(package_root))

        assert document["schemaVersion"] == 3
        assert "presentation" not in document

        presentations = document["presentations"]
        assert sum(
            presentation.get("isDefault") is True for presentation in presentations
        ) == 1
        contact_ids = {contact["id"] for contact in document["contacts"]}
        if any(presentation["media"]["type"] == "model" for presentation in presentations):
            assert all(presentation["media"]["type"] == "model" for presentation in presentations)
        else:
            assert set(_original_contact_owners(document)) == contact_ids
        assert all(
            "geometry" not in contact and "presentationID" not in contact
            for contact in document["contacts"]
        )


def test_approved_packages_declare_their_complete_presentation_asset_set() -> None:
    inventory = load_board_catalog_module().discover_board_packages(HANGBOARDS_ROOT)

    for package in inventory.packages:
        document = json.loads(package_board_text(package.root))
        actual_assets = {
            path.relative_to(package.root).as_posix()
            for path in (package.root / "assets").rglob("*")
            if path.is_file()
        }
        assert document["schemaVersion"] == 3
        assert "presentation" not in document
        assert all(
            isinstance(presentation["aspectRatio"], (int, float))
            and not isinstance(presentation["aspectRatio"], bool)
            and presentation["aspectRatio"] > 0
            for presentation in document["presentations"]
        )
        declared_assets = set()
        for presentation in document["presentations"]:
            media = presentation["media"]
            declared_assets.add(media["assetPath"])
            if media["type"] == "model":
                declared_assets.add(media["descriptorPath"])
        assert actual_assets == declared_assets


def test_compact_finished_package_has_exactly_one_document_and_primary_asset() -> None:
    relative_paths = {
        path.relative_to(COMPACT_ROOT).as_posix()
        for path in COMPACT_ROOT.rglob("*")
    }

    assert relative_paths == {
        "assets",
        "assets/primary.usdz",
        "assets/primary.model.json",
        # A CAD-backed package carries its own authoring source, named after its
        # own directory, instead of board.json: board.json is generated from the
        # FCStd at build time. It is not a runtime resource.
        "metolius-wood-grips-compact-ii.FCStd",
    }


def test_mammut_diamond_freezes_the_documented_16_contact_inventory() -> None:
    board = json.loads(package_board_text(MAMMUT_DIAMOND_ROOT))

    assert board["id"] == "mammut.diamond-finger"
    assert [(contact["id"], contact["kind"], _scalar_depth(contact), contact.get("fingerCapacity"), _single_grip_type(contact)) for contact in board["contacts"]] == [
        ("mam-jug-l", "jug", None, None, None),
        ("mam-jug-r", "jug", None, None, None),
        ("mam-sloper-c", "sloper", None, None, None),
        ("mam-mid-edge-c", "edge", None, None, None),
        ("mam-mono-l", "pocket", None, None, None),
        ("mam-mono-r", "pocket", None, None, None),
        ("mam-upper-pocket-l", "pocket", None, None, None),
        ("mam-upper-pocket-r", "pocket", None, None, None),
        ("mam-lateral-ledge-l", "edge", None, None, None),
        ("mam-lateral-ledge-r", "edge", None, None, None),
        ("mam-upper-pocket-c", "pocket", None, None, None),
        ("mam-lower-edge-c", "edge", None, None, None),
        ("mam-upper-open-bay-l", "edge", None, None, None),
        ("mam-upper-open-bay-r", "edge", None, None, None),
        ("mam-upper-inset-l", "pocket", None, None, None),
        ("mam-upper-inset-r", "pocket", None, None, None),
    ]

    descriptor = json.loads(
        (
            MAMMUT_DIAMOND_ROOT / board["presentations"][0]["media"]["descriptorPath"]
        ).read_text(encoding="utf-8")
    )
    for left_id, right_id in (
        ("mam-jug-l", "mam-jug-r"),
        ("mam-mono-l", "mam-mono-r"),
        ("mam-upper-pocket-l", "mam-upper-pocket-r"),
        ("mam-lateral-ledge-l", "mam-lateral-ledge-r"),
        ("mam-upper-open-bay-l", "mam-upper-open-bay-r"),
        ("mam-upper-inset-l", "mam-upper-inset-r"),
    ):
        left = descriptor["contacts"][left_id]
        right = descriptor["contacts"][right_id]
        assert not set(left["nodeIDs"]) & set(right["nodeIDs"])
        # Imported float32 coordinates retain symmetry within export precision.
        assert right["center"] == pytest.approx(
            [1 - left["center"][0], left["center"][1]], abs=1e-4
        )
        left_bounds, right_bounds = left["facePlaneAABB"], right["facePlaneAABB"]
        assert right_bounds["min"] == pytest.approx(
            [1 - left_bounds["max"][0], left_bounds["min"][1]], abs=1e-4
        )
        assert right_bounds["max"] == pytest.approx(
            [1 - left_bounds["min"][0], left_bounds["max"][1]], abs=1e-4
        )


def test_foundry_package_freezes_the_official_numbered_inventory() -> None:
    board = json.loads(package_board_text(FOUNDRY_ROOT))

    assert board["id"] == "metolius.foundry"
    assert _presentation_summary(board) == [
        ("front", "Front", "assets/primary.usdz", 2.6588197894316767, True, None, False)
    ]
    assert tuple(
        (
            contact["id"],
            contact["name"],
            contact["kind"],
            _scalar_depth(contact),
            contact.get("fingerCapacity"),
        )
        for contact in board["contacts"]
    ) == FOUNDRY_HOLDS
    _assert_model_descriptor(FOUNDRY_ROOT, board, "body_board_001")


def test_foundry_paired_contacts_use_exact_horizontal_mirrors() -> None:
    board = json.loads(package_board_text(FOUNDRY_ROOT))
    descriptor = json.loads(
        (
            FOUNDRY_ROOT / board["presentations"][0]["media"]["descriptorPath"]
        ).read_text(encoding="utf-8")
    )

    for position in range(1, 8):
        prefix = "pinch" if position == 1 else "jug" if position == 2 else "pocket"
        left = descriptor["contacts"][f"{prefix}-{position}-left"]
        right = descriptor["contacts"][f"{prefix}-{position}-right"]
        assert not set(left["nodeIDs"]) & set(right["nodeIDs"])
        left_bounds, right_bounds = left["facePlaneAABB"], right["facePlaneAABB"]
        # Imported float32 coordinates retain symmetry within export precision.
        assert right_bounds["min"] == pytest.approx(
            [1 - left_bounds["max"][0], left_bounds["min"][1]], abs=1e-4
        )
        assert right_bounds["max"] == pytest.approx(
            [1 - left_bounds["min"][0], left_bounds["max"][1]], abs=1e-4
        )


def test_prime_rib_package_freezes_the_official_three_edge_inventory() -> None:
    board = json.loads(package_board_text(PRIME_RIB_ROOT))

    assert board["id"] == "metolius.prime-rib"
    assert board["dimensions"] == "20 × 4.2 × 1.5 in"
    assert _presentation_summary(board) == [
        ("primary", "Primary", "assets/primary.usdz", 4.7619050011605735, True, None, False)
    ]
    assert tuple(
        (
            contact["id"],
            contact["name"],
            contact["kind"],
            _scalar_depth(contact),
        )
        for contact in board["contacts"]
    ) == PRIME_RIB_HOLDS
    _assert_model_descriptor(PRIME_RIB_ROOT, board, "body_mesh_001")


def test_flash_board_package_freezes_the_official_surface_inventories() -> None:
    board = json.loads(package_board_text(FLASH_BOARD_ROOT))

    assert board["id"] == "tension.flash-board"
    assert "dimensions" not in board
    assert _presentation_summary(board) == [
        ("primary", "Primary suspended model", "assets/primary.usdz", 1.5, True, None, False),
    ]
    assert [(contact["id"], contact["name"], contact["kind"]) for contact in board["contacts"]] == [
        ("three-edge-left", "Left edge on three-edge surface", "edge"),
        ("three-edge-center", "Center edge on three-edge surface", "edge"),
        ("three-edge-right", "Right edge on three-edge surface", "edge"),
        ("two-edge-left", "Left edge on two-edge surface", "edge"),
        ("two-edge-right", "Right edge on two-edge surface", "edge"),
        ("small-crimp-left", "Left small crimp", "edge"),
        ("small-crimp-right", "Right small crimp", "edge"),
    ]
    assert all("depth" not in contact for contact in board["contacts"])
    # Four positions over the shared model: upright/inverted for each usable face.
    # The small-crimp contacts are independently modeled on the suspended asset.
    assert board["positions"] == [
        {
            "id": "three-edge-upright",
            "presentationID": "primary",
            "contactIDs": ["three-edge-left", "three-edge-center", "three-edge-right"],
        },
        {
            "id": "three-edge-inverted",
            "presentationID": "primary",
            "contactIDs": ["three-edge-left", "three-edge-center", "three-edge-right"],
        },
        {
            "id": "two-edge-upright",
            "presentationID": "primary",
            "contactIDs": ["two-edge-left", "two-edge-right", "small-crimp-left", "small-crimp-right"],
        },
        {
            "id": "two-edge-inverted",
            "presentationID": "primary",
            "contactIDs": ["two-edge-left", "two-edge-right", "small-crimp-left", "small-crimp-right"],
        },
    ]

    media = board["presentations"][0]["media"]
    assert media["type"] == "model"
    assert media["descriptorPath"] == "assets/primary.model.json"
    assert "contactGeometry" not in media
    assert media.get("orientation") is None
    assert media["suspension"]["type"] == "twoBranchCord"
    assert [branch["id"] for branch in media["suspension"]["branches"]] == ["left-branch", "right-branch"]
    _assert_model_descriptor(FLASH_BOARD_ROOT, board, "flash_board_body_008")


def test_project_package_freezes_the_official_numbered_inventory_as_model() -> None:
    board = json.loads(package_board_text(PROJECT_ROOT))

    assert board["id"] == "metolius.project"
    assert board["dimensions"] == "24.5 × 6 in"
    assert _presentation_summary(board) == [
        ("primary", "Primary", "assets/primary.usdz", 4.083333463473314, True, None, False),
    ]
    assert [
        (contact["id"], contact["kind"], _scalar_depth(contact)) for contact in board["contacts"]
    ] == [
        ("jug-1-left", "jug", None),
        ("round-sloper-8-center", "sloper", None),
        ("jug-1-right", "jug", None),
        ("flat-sloper-2-left", "sloper", 55),
        ("flat-sloper-2-right", "sloper", 55),
        ("pocket-3-left", "pocket", 45),
        ("edge-4-left", "edge", 30),
        ("pocket-5-left", "pocket", 40),
        ("pocket-6-left", "pocket", 22),
        ("pocket-7-left", "pocket", 22),
        ("edge-9-center", "edge", 39),
        ("edge-10-center", "edge", 16),
        ("pocket-7-right", "pocket", 22),
        ("pocket-6-right", "pocket", 22),
        ("pocket-5-right", "pocket", 40),
        ("edge-4-right", "edge", 30),
        ("pocket-3-right", "pocket", 45),
    ]
    _assert_model_descriptor(
        PROJECT_ROOT, board, "project_body_partition_mesh_001"
    )


def test_project_model_pairs_preserve_mirrored_bounds_and_node_ownership() -> None:
    descriptor = json.loads(
        (PROJECT_ROOT / "assets/primary.model.json").read_text(encoding="utf-8")
    )
    for left_id, right_id in (
        ("jug-1-left", "jug-1-right"),
        ("flat-sloper-2-left", "flat-sloper-2-right"),
        ("pocket-3-left", "pocket-3-right"),
        ("edge-4-left", "edge-4-right"),
        ("pocket-5-left", "pocket-5-right"),
        ("pocket-6-left", "pocket-6-right"),
        ("pocket-7-left", "pocket-7-right"),
    ):
        left = descriptor["contacts"][left_id]
        right = descriptor["contacts"][right_id]
        assert left["nodeIDs"] == [left_id.replace("-", "_") + "_partition_mesh_001"]
        assert right["nodeIDs"] == [right_id.replace("-", "_") + "_partition_mesh_001"]
        # Imported float32 coordinates retain symmetry within export precision.
        assert right["center"] == pytest.approx(
            [1 - left["center"][0], left["center"][1]], abs=1e-4
        )
        left_bounds, right_bounds = left["facePlaneAABB"], right["facePlaneAABB"]
        assert right_bounds["min"] == pytest.approx(
            [1 - left_bounds["max"][0], left_bounds["min"][1]], abs=1e-4
        )
        assert right_bounds["max"] == pytest.approx(
            [1 - left_bounds["min"][0], left_bounds["max"][1]], abs=1e-4
        )


def test_light_rail_package_freezes_the_official_reversible_inventory() -> None:
    board = json.loads(package_board_text(LIGHT_RAIL_ROOT))

    assert board["id"] == "metolius.light-rail-2"
    assert board["dimensions"] == "18 × 3 × 1.5 in"
    assert board["schemaVersion"] == 3
    assert len(board["presentations"]) == 1
    presentation = board["presentations"][0]
    assert presentation["id"] == "primary"
    assert presentation["isDefault"] is True
    assert presentation["derivation"] == {"type": "original"}
    media = presentation["media"]
    assert set(media) == {"type", "assetPath", "descriptorPath", "display", "suspension"}
    assert media["type"] == "model"
    descriptor = _assert_model_descriptor(LIGHT_RAIL_ROOT, board, "light_rail_body_001")
    assert tuple(
        (
            contact["id"],
            contact["name"],
            contact["kind"],
            _scalar_depth(contact),
            contact["equipmentObjectID"],
        )
        for contact in board["contacts"]
    ) == (
        (
            "jug-40-20mm-side",
            "40 mm rounded jug on 20 mm side",
            "jug",
            40,
            "primary",
        ),
        ("edge-20", "20 mm edge", "edge", 20, "primary"),
        (
            "jug-40-15mm-side",
            "40 mm rounded jug on 15 mm side",
            "jug",
            40,
            "primary",
        ),
        ("edge-15", "15 mm edge", "edge", 15, "primary"),
    )
    assert {contact: value["nodeIDs"] for contact, value in descriptor["contacts"].items()} == {
        "jug-40-20mm-side": ["lr_top_jug_40_001"],
        "edge-20": ["lr_recess_lower_20_001"],
        "jug-40-15mm-side": ["lr_bottom_jug_40_001"],
        "edge-15": ["lr_recess_upper_15_001"],
    }
    assert {contact for position in board["positions"] for contact in position["contactIDs"]} == {
        "jug-40-20mm-side", "edge-20", "jug-40-15mm-side", "edge-15"
    }
    with zipfile.ZipFile(LIGHT_RAIL_ROOT / media["assetPath"]) as archive:
        assert len(archive.namelist()) == 1
        assert Path(archive.namelist()[0]).suffix in {".usda", ".usdc"}
    assert not any(token in node["nodeID"].lower() for node in descriptor["nodes"]
                   for token in ("screw", "mount", "fastener", "hardware", "cleat", "bracket", "underside", "bore", "anchor"))


def test_light_rail_cord_uses_only_two_upper_exterior_entries() -> None:
    """Catch invented underside/through routes and selectable cord bindings."""
    board = json.loads(package_board_text(LIGHT_RAIL_ROOT))
    media = board["presentations"][0]["media"]
    assert media["type"] == "model"
    suspension = media["suspension"]
    assert suspension["type"] == "pairedLeadCord"
    assert len(suspension["attachments"]) == 2
    expected_points = {"left_upper_entry_001": [-0.213, 0.038, 0],
                       "right_upper_entry_001": [0.213, 0.038, 0]}
    assert {lead["nodeID"] for lead in suspension["attachments"]} == set(expected_points)
    for lead in suspension["attachments"]:
        # Export float32 bounds may move the upper surface inward by 1 nm.
        assert lead["pointInModel"] == pytest.approx(expected_points[lead["nodeID"]], abs=1e-8)
    descriptor = json.loads((LIGHT_RAIL_ROOT / media["descriptorPath"]).read_text())
    assert {node["nodeID"] for node in descriptor["nodes"] if node["role"] == "attachment"} == {
        "left_upper_entry_001", "right_upper_entry_001"
    }
    for lead, side in zip(suspension["attachments"], ("left", "right"), strict=True):
        assert "contactPointsInModel" not in lead
        assert "authored-display-estimate" in lead["provenance"]
        assert len(suspension["passages"][side]) == 1
        passage = suspension["passages"][side][0]
        assert set(passage) == {"id", "nodeID", "pointInModel", "provenance"}
        assert passage["nodeID"] == lead["nodeID"]
        assert passage["pointInModel"] == lead["pointInModel"]
    assert suspension["anchor"]["visibility"] == "invisible"
    assert "authored-display-estimate" in suspension["anchor"]["provenance"]
    assert "authored-display-estimate" in suspension["cord"]["provenance"]


def test_rock_rings_package_freezes_the_official_two_unit_inventory() -> None:
    board = json.loads(package_board_text(ROCK_RINGS_ROOT))

    assert board["id"] == "metolius.rock-rings-3d"
    assert board["dimensions"] == "184 × 146 × 57 mm"
    assert _presentation_summary(board) == [
        ("primary", "Front pair", "assets/primary.usdz", 1.5, True, None, False)
    ]

    owners = {contact["id"]: contact["equipmentObjectID"] for contact in board["contacts"]}
    assert tuple(
        (
            contact["id"],
            contact["name"],
            contact["kind"],
            _scalar_depth(contact),
            contact.get("fingerCapacity"),
            owners[contact["id"]],
        )
        for contact in board["contacts"]
    ) == (
        ("jug-left", "Left unit jug", "jug", None, None, "left-ring"),
        (
            "pocket-40-four-left",
            "Left unit 40 mm four-finger pocket",
            "pocket",
            40,
            4,
            "left-ring",
        ),
        (
            "pocket-32-three-left",
            "Left unit 32 mm three-finger pocket",
            "pocket",
            32,
            3,
            "left-ring",
        ),
        (
            "pocket-25-two-left",
            "Left unit 25 mm two-finger pocket",
            "pocket",
            25,
            2,
            "left-ring",
        ),
        ("jug-right", "Right unit jug", "jug", None, None, "right-ring"),
        (
            "pocket-40-four-right",
            "Right unit 40 mm four-finger pocket",
            "pocket",
            40,
            4,
            "right-ring",
        ),
        (
            "pocket-32-three-right",
            "Right unit 32 mm three-finger pocket",
            "pocket",
            32,
            3,
            "right-ring",
        ),
        (
            "pocket-25-two-right",
            "Right unit 25 mm two-finger pocket",
            "pocket",
            25,
            2,
            "right-ring",
        ),
    )
    assert board["equipmentObjects"] == [{"id": "left-ring"}, {"id": "right-ring"}]
    assert all(contact["equipmentObjectID"] == f"{contact['id'].rsplit('-', 1)[1]}-ring"
               for contact in board["contacts"])


def test_rock_rings_has_one_four_slot_asset_and_two_unreflected_instances() -> None:
    """Catch baked duplicates, reflected units, lost ownership, or raster fallback."""
    board = json.loads(package_board_text(ROCK_RINGS_ROOT))
    assert len(board["presentations"]) == 1
    media = board["presentations"][0]["media"]
    assert media["type"] == "model"
    assert set(media) == {"type", "assetPath", "descriptorPath", "display", "instances"}
    assert {p.relative_to(ROCK_RINGS_ROOT).as_posix() for p in ROCK_RINGS_ROOT.rglob("*") if p.is_file()} == {
        "assets/primary.usdz", "assets/primary.model.json",
        # A CAD-backed package carries its own authoring source, named after its
        # own directory, instead of board.json: board.json is generated from the
        # FCStd at build time. It is not a runtime resource.
        "metolius-rock-rings-3d.FCStd",
    }
    descriptor = json.loads((ROCK_RINGS_ROOT / media["descriptorPath"]).read_text())
    assert descriptor["schemaVersion"] == 2
    assert descriptor["modelSHA256"] == hashlib.sha256((ROCK_RINGS_ROOT / media["assetPath"]).read_bytes()).hexdigest()
    assert "contacts" not in descriptor
    assert set(descriptor["contactSlots"]) == {"jug", "pocket-40", "pocket-32", "pocket-25"}
    assert all("contactID" not in node for node in descriptor["nodes"])
    bounds = descriptor["modelBounds"]
    assert [bounds["max"][i] - bounds["min"][i] for i in range(3)] == pytest.approx([.146, .184, .057], abs=.000001)
    # A source asset has unit-local bounds and one body, never a baked pair.
    assert sum(node["role"] == "body" for node in descriptor["nodes"]) == 1
    with zipfile.ZipFile(ROCK_RINGS_ROOT / media["assetPath"]) as archive:
        assert len(archive.namelist()) == 1
        assert Path(archive.namelist()[0]).suffix in {".usda", ".usdc"}
    assert len(media["instances"]) == 2
    mapped = []
    for side, instance in zip(("left", "right"), media["instances"], strict=True):
        assert instance["equipmentObjectID"] == f"{side}-ring"
        assert instance["contactIDsBySlotID"] == {
            "jug": f"jug-{side}", "pocket-40": f"pocket-40-four-{side}",
            "pocket-32": f"pocket-32-three-{side}", "pocket-25": f"pocket-25-two-{side}"
        }
        mapped.extend(instance["contactIDsBySlotID"].values())
        assert "reflection" not in instance["baseTransform"]
        assert instance["baseTransform"]["rotation"] == [0, 0, 0, 1]
        assert "positionTransforms" not in instance
    assert len(mapped) == len(set(mapped)) == 8
    assert set(mapped) == {c["id"] for c in board["contacts"]}
    assert board["positions"] == [{"id": "primary", "presentationID": "primary", "contactIDs": [c["id"] for c in board["contacts"]]}]
    catalog = load_board_catalog_module()
    assert catalog.load_board_package(ROCK_RINGS_ROOT).board.id == board["id"]


def test_rock_rings_cords_have_independent_anchors_and_only_evidenced_openings() -> None:
    """Catch a shared anchor, inter-unit route, fake central bore or contact binding."""
    board = json.loads(package_board_text(ROCK_RINGS_ROOT))
    media = board["presentations"][0]["media"]
    assert media["type"] == "model"
    descriptor = json.loads((ROCK_RINGS_ROOT / media["descriptorPath"]).read_text())
    roles = {node["nodeID"].removesuffix("_001").replace("_", "-"): node["role"] for node in descriptor["nodes"]}
    assert roles["roof-exit"] == roles["lateral-window"] == "attachment"
    assert not any(token in name for name in roles for token in (
        "mount", "screw", "fastener", "cleat", "bracket", "hardware", "central", "bore", "cord", "anchor"
    ))
    anchors = []
    attachment_ids = []
    for instance in media["instances"]:
        suspension = instance["suspension"]
        assert suspension["type"] == "pairedLeadCord"
        assert len(suspension["attachments"]) == 2
        assert set(suspension["passages"]) == {"left", "right"}
        assert all(len(v) == 1 for v in suspension["passages"].values())
        for passage in suspension["passages"].values():
            assert set(passage[0]) == {"id", "nodeID", "pointInModel", "provenance"}
        for attachment in suspension["attachments"]:
            assert roles[attachment["nodeID"].removesuffix("_001").replace("_", "-")] == "attachment"
            assert "contactPointsInModel" not in attachment
            attachment_ids.append(attachment["id"])
        assert len({tuple(a["pointInModel"]) for a in suspension["attachments"]}) == 2
        assert suspension["anchor"]["visibility"] == "invisible"
        anchors.append(tuple(suspension["anchor"]["offsetFromBoardBounds"]))
        assert set(suspension["canonicalPoses"]) == {"primary"}
        assert "authored-display-estimate" in suspension["anchor"]["provenance"]
        assert "authored-display-estimate" in suspension["cord"]["provenance"]
    assert len(set(anchors)) == 2
    assert len(set(attachment_ids)) == 4


def test_deluxe_model_package_freezes_the_independent_official_inventory() -> None:
    board = json.loads(package_board_text(DELUXE_ROOT))

    assert board["id"] == "metolius.wood-grips-deluxe-ii"
    assert board["dimensions"] == "24 × 8.5 in"
    assert _presentation_summary(board) == [
        ("front", "Front", "assets/primary.usdz", 2.8240740604423875, True, None, False)
    ]
    assert {
        (
            contact["id"],
            contact["kind"],
            _scalar_depth(contact),
            contact.get("fingerCapacity"),
            _single_grip_type(contact),
        )
        for contact in board["contacts"]
    } == {
        ("jug-1-left", "jug", None, None, None),
        ("jug-1-right", "jug", None, None, None),
        ("sloper-2-flat-left", "sloper", None, None, None),
        ("sloper-2-flat-right", "sloper", None, None, None),
        ("sloper-12-round-center", "sloper", None, None, None),
        ("edge-3-31-left", "edge", 31, None, None),
        ("edge-3-31-right", "edge", 31, None, None),
        ("pocket-4-32-three-left", "pocket", 32, 3, "threeFingerPocket"),
        ("pocket-4-32-three-right", "pocket", 32, 3, "threeFingerPocket"),
        ("pocket-5-38-two-left", "pocket", 38, 2, "twoFingerPocket"),
        ("pocket-5-38-two-right", "pocket", 38, 2, "twoFingerPocket"),
        ("pocket-13-32-four-center", "pocket", 32, 4, "fourFingerPocket"),
        ("edge-6-25-left", "edge", 25, None, None),
        ("edge-6-25-right", "edge", 25, None, None),
        ("pocket-7-25-three-left", "pocket", 25, 3, "threeFingerPocket"),
        ("pocket-7-25-three-right", "pocket", 25, 3, "threeFingerPocket"),
        ("pocket-8-28-two-left", "pocket", 28, 2, "twoFingerPocket"),
        ("pocket-8-28-two-right", "pocket", 28, 2, "twoFingerPocket"),
        ("pocket-14-25-four-center", "pocket", 25, 4, "fourFingerPocket"),
        ("edge-9-19-left", "edge", 19, None, None),
        ("edge-9-19-right", "edge", 19, None, None),
        ("pocket-10-19-three-left", "pocket", 19, 3, "threeFingerPocket"),
        ("pocket-10-19-three-right", "pocket", 19, 3, "threeFingerPocket"),
        ("pocket-11-19-two-left", "pocket", 19, 2, "twoFingerPocket"),
        ("pocket-11-19-two-right", "pocket", 19, 2, "twoFingerPocket"),
        ("pocket-15-19-four-center", "pocket", 19, 4, "fourFingerPocket"),
    }
    assert len(board["contacts"]) == 26
    _assert_model_descriptor(DELUXE_ROOT, board, "body_001")

    compact = json.loads(package_board_text(COMPACT_ROOT))
    assert board["dimensions"] != compact["dimensions"]
    assert len(board["contacts"]) != len(compact["contacts"])


def test_deluxe_descriptor_completely_and_consistently_owns_every_contact() -> None:
    board = json.loads(package_board_text(DELUXE_ROOT))
    descriptor = _assert_model_descriptor(DELUXE_ROOT, board, "body_001")
    contact_ids = {contact["id"] for contact in board["contacts"]}
    descriptor_contacts = descriptor["contacts"]
    contact_nodes = [
        node for node in descriptor["nodes"] if node["role"] == "contact"
    ]

    assert set(descriptor_contacts) == contact_ids
    assert {node["contactID"] for node in contact_nodes} == contact_ids
    assert len(contact_nodes) == len(contact_ids) == 26
    assert len({node["nodeID"] for node in contact_nodes}) == len(contact_nodes)
    assert all(
        descriptor_contacts[contact_id]["nodeIDs"]
        == [
            node["nodeID"]
            for node in contact_nodes
            if node["contactID"] == contact_id
        ]
        for contact_id in contact_ids
    )


def test_compact_board_keeps_the_literal_hold_inventory_with_model_descriptor() -> None:
    board = json.loads(package_board_text(COMPACT_ROOT))
    contacts = board["contacts"]
    contact_ids = [contact["id"] for contact in contacts]

    assert board["id"] == "metolius.wood-grips-compact-ii"
    assert tuple((contact["id"], contact["name"]) for contact in contacts) == COMPACT_HOLDS
    assert len(contact_ids) == len(set(contact_ids))
    media = board["presentations"][0]["media"]
    assert media["type"] == "model"
    assert media["assetPath"] == "assets/primary.usdz"
    assert media["descriptorPath"] == "assets/primary.model.json"
    descriptor = json.loads(
        (COMPACT_ROOT / media["descriptorPath"]).read_text(encoding="utf-8")
    )
    assert set(descriptor["contacts"]) == set(contact_ids)
    assert {
        node["contactID"] for node in descriptor["nodes"] if node["role"] == "contact"
    } == set(contact_ids)


def test_training_tiles_freezes_source_limited_adapted_contact_model() -> None:
    board = json.loads(package_board_text(TRAINING_TILES_ROOT))

    assert board["id"] == "soill.training-tiles"
    assert tuple((contact["id"], contact["name"], contact["kind"]) for contact in board["contacts"]) == (
        ("upper-sloper-outer-left", "Outer left upper sloper", "sloper"),
        ("upper-sloper-outer-right", "Outer right upper sloper", "sloper"),
        ("upper-sloper-inner-left", "Inner left upper sloper", "sloper"),
        ("upper-sloper-inner-right", "Inner right upper sloper", "sloper"),
        ("middle-edge-outer-left", "Outer left middle edge", "edge"),
        ("middle-edge-outer-right", "Outer right middle edge", "edge"),
        ("middle-edge-inner-left", "Inner left middle edge", "edge"),
        ("middle-edge-inner-right", "Inner right middle edge", "edge"),
        ("bottom-edge-center-left", "Center left bottom edge", "edge"),
        ("bottom-edge-center-right", "Center right bottom edge", "edge"),
        ("top-pocket-outer-left", "Outer left top pocket", "pocket"),
        ("top-pocket-outer-right", "Outer right top pocket", "pocket"),
        ("bottom-edge-inner-left", "Inner left bottom edge", "edge"),
        ("bottom-edge-inner-right", "Inner right bottom edge", "edge"),
        ("bottom-edge-outer-left", "Outer left bottom edge", "edge"),
        ("bottom-edge-outer-right", "Outer right bottom edge", "edge"),
        ("top-pocket-inner-left", "Inner left top pocket", "pocket"),
        ("top-pocket-inner-right", "Inner right top pocket", "pocket"),
        ("top-jug-left", "Left top jug", "jug"),
        ("top-jug-right", "Right top jug", "jug"),
    )
    media = board["presentations"][0]["media"]
    assert media["type"] == "model"
    assert media["assetPath"] == "assets/primary.usdz"
    assert media["descriptorPath"] == "assets/primary.model.json"
    assert "contactGeometry" not in media
    descriptor = json.loads((TRAINING_TILES_ROOT / media["descriptorPath"]).read_text(encoding="utf-8"))
    contact_ids = {contact["id"] for contact in board["contacts"]}
    assert set(descriptor["contacts"]) == contact_ids
    assert {
        node["contactID"] for node in descriptor["nodes"] if node["role"] == "contact"
    } == contact_ids


def test_compact_hold_records_keep_only_source_audited_physical_facts() -> None:
    board = json.loads(package_board_text(COMPACT_ROOT))
    contacts = board["contacts"]
    retired_fields = {"frame", "shortLabel", "detail", "cueStyle"}
    supported_fields = {
        "id",
        "name",
        "kind",
        "depth",
        "shape",
        "fingerCapacity",
        "handCapacity",
        "equipmentObjectID",
        "gripTypes",
        "side",
        "pairedContactID",
    }

    assert all(not (set(contact) & retired_fields) for contact in contacts)
    assert all({"id", "name", "kind"} <= set(contact) for contact in contacts)
    assert all("geometry" not in contact and "presentationID" not in contact for contact in contacts)
    assert all(set(contact) <= supported_fields for contact in contacts)
    assert {contact.get("equipmentObjectID") for contact in contacts} == {"primary"}
    assert all(
        "depth" not in contact
        or "category" in contact["depth"]
        or contact["depth"]["range"]["minimum"]
        == contact["depth"]["range"]["maximum"]
        for contact in contacts
    )
    expected_pocket_grips = {
        2: "twoFingerPocket",
        3: "threeFingerPocket",
        4: "fourFingerPocket",
    }
    assert all(
        _single_grip_type(contact) == expected_pocket_grips[contact["fingerCapacity"]]
        for contact in contacts
        if contact["kind"] == "pocket"
    )
    assert all(
        contact["gripTypes"] == []
        for contact in contacts
        if contact["kind"] != "pocket"
    )
    assert {
        contact["id"]: (
            contact.get("kind"),
            _scalar_depth(contact),
            contact.get("fingerCapacity"),
            _single_grip_type(contact),
            contact.get("shape"),
        )
        for contact in contacts
    } == COMPACT_HOLD_SOURCE_FACTS


def test_compact_model_descriptor_is_hash_bound_to_actual_asset() -> None:
    model_path = COMPACT_ROOT / "assets/primary.usdz"
    descriptor_path = COMPACT_ROOT / "assets/primary.model.json"
    descriptor = json.loads(descriptor_path.read_text(encoding="utf-8"))

    model_sha = hashlib.sha256(model_path.read_bytes()).hexdigest()
    descriptor_sha = hashlib.sha256(descriptor_path.read_bytes()).hexdigest()
    assert model_sha == "25d0e5e4705a819c71bf621e617c5f12e08962b87f3ce47756321103ccddbdbe"
    assert descriptor["modelSHA256"] == model_sha
    assert descriptor["schemaVersion"] == 1
    assert descriptor["coordinateFrame"] == "hang-ten-board-v1"


def test_contact_is_a_bore_free_model_only_package_with_its_existing_contacts() -> None:
    board = json.loads(package_board_text(CONTACT_ROOT))
    media = board["presentations"][0]["media"]

    assert media["type"] == "model"
    assert media["assetPath"] == "assets/primary.usdz"
    assert media["descriptorPath"] == "assets/primary.model.json"
    assert "contactGeometry" not in media
    assert {
        path.relative_to(CONTACT_ROOT).as_posix()
        for path in CONTACT_ROOT.rglob("*")
        if path.is_file()
    } == {"board.json", "assets/primary.usdz", "assets/primary.model.json"}
    descriptor = json.loads((CONTACT_ROOT / media["descriptorPath"]).read_text(encoding="utf-8"))
    contact_ids = {contact["id"] for contact in board["contacts"]}
    assert len(contact_ids) == 33
    assert set(descriptor["contacts"]) == contact_ids
    assert {
        node["contactID"] for node in descriptor["nodes"] if node["role"] == "contact"
    } == contact_ids
    assert [node["nodeID"] for node in descriptor["nodes"] if node["role"] == "body"] == [
        "body_001",
    ]
    assert descriptor["modelSHA256"] == hashlib.sha256(
        (CONTACT_ROOT / media["assetPath"]).read_bytes()
    ).hexdigest()


def test_compact_package_loader_preserves_identity_inventory_and_model_frames() -> None:
    module = load_board_catalog_module()
    package = module.load_board_package(COMPACT_ROOT)

    assert tuple((contact.id, contact.name) for contact in package.board.contacts) == COMPACT_HOLDS
    assert package.board.facts == {
        "manufacturer": "Metolius",
        "name": "Wood Grips Compact II",
        "subtitle": "FSC-certified wood training board.",
        "productURL": "https://www.metoliusclimbing.com/products/wood-grips-ii-training-boards",
        "dimensions": '24" × 6.2"',
        "aspectRatio": 3.88,
    }
    assert package.board.presentation_asset_path == "assets/primary.usdz"
    presentation_id = next(
        presentation.id
        for presentation in package.board.presentations
        if presentation.is_default
    )
    media = package.board.presentations[0].media
    assert isinstance(media, module.PresentationMediaModel)
    assert media.descriptor_path == "assets/primary.model.json"
    for contact in package.board.contacts:
        frame = package.board.contact_frame(contact.id, presentation_id)
        actual = (frame.x, frame.y, frame.width, frame.height)
        assert all(value == pytest.approx(value) for value in actual)
        assert actual[2] > 0
        assert actual[3] > 0


def test_target_model_package_rejects_legacy_png_fallback(tmp_path: Path) -> None:
    module = load_board_catalog_module()
    for slug in ("beastmaker-1000", "metolius-wood-grips-compact-ii"):
        package = tmp_path / slug
        shutil.copytree(HANGBOARDS_ROOT / slug, package)
        (package / "assets/primary.png").write_bytes(PRIMARY_PNG_BYTES)
        with pytest.raises(ValueError, match="undeclared presentation asset"):
            module.load_board_package(package)


def test_compact_model_package_has_no_raster_fallback() -> None:
    board = json.loads(package_board_text(COMPACT_ROOT))
    media = board["presentations"][0]["media"]
    assert media["type"] == "model"
    assert not (COMPACT_ROOT / "assets/primary.png").exists()
    assert sorted(path.name for path in (COMPACT_ROOT / "assets").iterdir()) == [
        "primary.model.json",
        "primary.usdz",
    ]


def test_yy_travelboard_freezes_the_official_six_grip_inventory() -> None:
    board = json.loads(package_board_text(YY_TRAVELBOARD_ROOT))

    assert board["id"] == "yy.travelboard"
    assert board["dimensions"] == "34 × 10 × 3 cm"
    assert [
        (item["id"], item["media"]["assetPath"])
        for item in board["presentations"]
    ] == [
        ("front-25-15", "assets/primary.png"),
        ("reverse-10", "assets/reverse.png"),
    ]
    owners = _original_contact_owners(board)
    assert {
        (
            contact["id"],
            contact["kind"],
            _scalar_depth(contact),
            contact.get("fingerCapacity"),
            owners[contact["id"]],
        )
        for contact in board["contacts"]
    } == {
        ("tray", "jug", None, None, "front-25-15"),
        ("edge-25", "edge", 25, None, "front-25-15"),
        ("edge-15", "edge", 15, None, "front-25-15"),
        ("mono-left", "pocket", None, 1, "front-25-15"),
        ("mono-right", "pocket", None, 1, "front-25-15"),
        ("edge-10", "edge", 10, None, "reverse-10"),
    }


def test_yy_baguette_freezes_six_documented_grips_across_two_faces() -> None:
    board = json.loads(package_board_text(YY_BAGUETTE_ROOT))

    assert board["id"] == "yy.baguette"
    assert board["dimensions"] == "47 × 4 × 4 cm"
    assert _presentation_summary(board) == [
        (
            "stepped-face",
            "30 / 25 / 20 mm and tray face",
            "assets/primary.png",
            1.5,
            True,
            None,
            False,
        ),
        (
            "reverse-face",
            "15 / 10 mm face",
            "assets/reverse.png",
            1.5,
            False,
            None,
            False,
        ),
    ]
    assert {
        (contact["id"], contact["kind"], _scalar_depth(contact))
        for contact in board["contacts"]
    } == {
        ("tray", "jug", None),
        ("edge-30", "edge", 30),
        ("edge-25", "edge", 25),
        ("edge-20", "edge", 20),
        ("edge-15", "edge", 15),
        ("edge-10", "edge", 10),
    }
    owners = _original_contact_owners(board)
    assert [(contact["id"], owners[contact["id"]]) for contact in board["contacts"]] == [
        ("edge-30", "stepped-face"),
        ("tray", "stepped-face"),
        ("edge-20", "stepped-face"),
        ("edge-25", "stepped-face"),
        ("edge-15", "reverse-face"),
        ("edge-10", "reverse-face"),
    ]


def test_yy_baguette_evo_freezes_twelve_grip_types_as_nineteen_contacts() -> None:
    board = json.loads(package_board_text(YY_BAGUETTE_EVO_ROOT))

    assert board["id"] == "yy.baguette-evo"
    assert board["dimensions"] == "52 × 5 × 5 cm"
    assert _presentation_summary(board) == [
        ("primary", "Primary", "assets/primary.usdz", 10.4, True, None, False),
    ]
    media = board["presentations"][0]["media"]
    assert media["type"] == "model"
    assert media["descriptorPath"] == "assets/primary.model.json"
    suspension = media["suspension"]
    assert suspension["type"] == "twoBranchCord"
    assert len(suspension["passages"]["left"]) == 2
    assert len(suspension["passages"]["right"]) == 2
    assert [branch["id"] for branch in suspension["branches"]] == [
        "left-branch",
        "right-branch",
    ]
    assert "contactGeometry" not in media
    assert "holdGeometry" not in media
    assert {path.relative_to(YY_BAGUETTE_EVO_ROOT).as_posix()
            for path in YY_BAGUETTE_EVO_ROOT.rglob("*") if path.is_file()} == {
        "board.json", "assets/primary.usdz", "assets/primary.model.json",
    }
    descriptor = json.loads(
        (YY_BAGUETTE_EVO_ROOT / media["descriptorPath"]).read_text(encoding="utf-8")
    )
    assert descriptor["schemaVersion"] == 1
    assert descriptor["coordinateFrame"] == "hang-ten-board-v1"
    assert descriptor["modelSHA256"] == hashlib.sha256(
        (YY_BAGUETTE_EVO_ROOT / media["assetPath"]).read_bytes()
    ).hexdigest()
    assert set(descriptor["contacts"]) == {contact["id"] for contact in board["contacts"]}
    assert [node for node in descriptor["nodes"] if node["role"] == "body"] == [
        {"nodeID": "body_mesh_001", "role": "body"},
    ]
    for contact_id, contact in descriptor["contacts"].items():
        assert contact["nodeIDs"] == [
            node["nodeID"] for node in descriptor["nodes"]
            if node.get("contactID") == contact_id
        ]
        assert len(contact["nodeIDs"]) == (2 if contact_id == "rounded-tray" else 1)
    assert descriptor["contacts"]["rounded-tray"]["nodeIDs"] == [
        "hold_rounded_left_mesh_001", "hold_rounded_right_mesh_001",
    ]
    assert len(board["contacts"]) == 19
    assert sorted(
        _scalar_depth(contact)
        for contact in board["contacts"]
        if not contact["id"].startswith("edge-central") and contact["kind"] == "edge"
    ) == [6, 6, 8, 8, 10, 10, 12, 12, 15, 15, 20, 20, 25, 25]
    assert {
        (contact["id"], _scalar_depth(contact))
        for contact in board["contacts"]
        if contact["id"].startswith("edge-central")
    } == {
        ("edge-central-30", 30),
        ("edge-central-25", 25),
        ("edge-central-20", 20),
        ("edge-central-6", 6),
    }
    assert [(contact["id"], contact["kind"]) for contact in board["contacts"] if contact["kind"] == "jug"] == [
        ("rounded-tray", "jug")
    ]
    assert board["equipmentObjects"] == [{"id": "primary"}]
    assert [(contact["id"], contact["equipmentObjectID"]) for contact in board["contacts"]] == [
        ("edge-20-left", "primary"),
        ("edge-10-left", "primary"),
        ("edge-25-left", "primary"),
        ("edge-15-left", "primary"),
        ("edge-15-right", "primary"),
        ("edge-25-right", "primary"),
        ("edge-10-right", "primary"),
        ("edge-20-right", "primary"),
        ("edge-12-left", "primary"),
        ("edge-12-right", "primary"),
        ("edge-8-left", "primary"),
        ("edge-8-right", "primary"),
        ("edge-6-upper", "primary"),
        ("edge-6-lower", "primary"),
        ("edge-central-30", "primary"),
        ("edge-central-25", "primary"),
        ("edge-central-20", "primary"),
        ("edge-central-6", "primary"),
        ("rounded-tray", "primary"),
    ]


def test_yy_baguette_evo_model_central_30_25_contacts_are_centered_and_distinct() -> None:
    descriptor = json.loads(
        (YY_BAGUETTE_EVO_ROOT / "assets/primary.model.json").read_text(encoding="utf-8")
    )
    for size, y_min, y_max in ((30, 0.5, 0.7), (25, 0.3, 0.5)):
        contact = descriptor["contacts"][f"edge-central-{size}"]
        assert contact["nodeIDs"] == [f"hold_central_{size}mm_mesh_001"]
        assert contact["center"] == pytest.approx([0.5, (y_min + y_max) / 2], abs=1e-7)
        assert contact["facePlaneAABB"]["min"] == pytest.approx(
            [0.423076922, y_min], abs=1e-7
        )
        assert contact["facePlaneAABB"]["max"] == pytest.approx(
            [0.576923078, y_max], abs=1e-7
        )


def test_yy_baguette_evo_model_pairs_preserve_mirrored_bounds_and_node_ownership() -> None:
    descriptor = json.loads(
        (YY_BAGUETTE_EVO_ROOT / "assets/primary.model.json").read_text(encoding="utf-8")
    )
    for size in (25, 20, 15, 12, 10, 8, 6):
        left_id = f"edge-{size}-left" if size != 6 else "edge-6-upper"
        right_id = f"edge-{size}-right" if size != 6 else "edge-6-lower"
        left = descriptor["contacts"][left_id]
        right = descriptor["contacts"][right_id]
        assert left["nodeIDs"] == [f"hold_edge_{size:02d}mm_left_mesh_001"]
        assert right["nodeIDs"] == [f"hold_edge_{size:02d}mm_right_mesh_001"]
        # Imported float32 coordinates retain symmetry within export precision.
        assert right["center"] == pytest.approx(
            [1 - left["center"][0], left["center"][1]], abs=1e-7
        )
        left_bounds, right_bounds = left["facePlaneAABB"], right["facePlaneAABB"]
        assert right_bounds["min"] == pytest.approx(
            [1 - left_bounds["max"][0], left_bounds["min"][1]], abs=1e-7
        )
        assert right_bounds["max"] == pytest.approx(
            [1 - left_bounds["min"][0], left_bounds["max"][1]], abs=1e-7
        )


def test_yy_penta_evo_freezes_seven_contacts_per_official_pair_unit() -> None:
    board = json.loads(package_board_text(YY_PENTA_EVO_ROOT))

    assert board["id"] == "yy.penta-evo"
    assert board["dimensions"] == "Not published by YY Vertical"
    assert len(board["presentations"]) == 1
    assert len(board["contacts"]) == 14
    assert sorted(
        (contact["kind"], _scalar_depth(contact), contact.get("fingerCapacity"))
        for contact in board["contacts"]
    ) == sorted(
        2
        * [
            ("edge", 25, None),
            ("edge", 20, None),
            ("edge", 15, None),
            ("edge", 10, None),
            ("pocket", None, 1),
            ("pocket", None, 2),
            ("jug", None, None),
        ]
    )
    assert board["equipmentObjects"] == [{"id": "left-penta"}, {"id": "right-penta"}]
    assert {contact["id"]: contact["equipmentObjectID"] for contact in board["contacts"]} == {
        f"{slot}-{side}": f"{side}-penta"
        for side in ("left", "right")
        for slot in ("edge-25", "edge-20", "edge-15", "edge-10", "mono", "duo", "tray")
    }


def test_yy_penta_evo_pair_reuses_one_asymmetric_unit_without_reflection() -> None:
    """Catch baked pairs or the old raster's incorrectly mirrored right unit."""
    board = json.loads(package_board_text(YY_PENTA_EVO_ROOT))
    media = board["presentations"][0]["media"]
    assert media["type"] == "model"
    assert set(media) == {"type", "assetPath", "descriptorPath", "display", "instances"}
    assert {p.relative_to(YY_PENTA_EVO_ROOT).as_posix() for p in YY_PENTA_EVO_ROOT.rglob("*") if p.is_file()} == {
        "board.json", "assets/primary.usdz", "assets/primary.model.json"
    }
    descriptor = json.loads((YY_PENTA_EVO_ROOT / media["descriptorPath"]).read_text())
    assert descriptor["schemaVersion"] == 2
    assert descriptor["modelSHA256"] == hashlib.sha256((YY_PENTA_EVO_ROOT / media["assetPath"]).read_bytes()).hexdigest()
    slots = {"edge-25", "edge-20", "edge-15", "edge-10", "mono", "duo", "tray"}
    assert set(descriptor["contactSlots"]) == slots
    assert "contacts" not in descriptor
    assert sum(node["role"] == "body" for node in descriptor["nodes"]) == 1
    assert len(media["instances"]) == 2
    for side, instance in zip(("left", "right"), media["instances"], strict=True):
        assert instance["equipmentObjectID"] == f"{side}-penta"
        assert instance["contactIDsBySlotID"] == {slot: f"{slot}-{side}" for slot in slots}
        assert instance["baseTransform"] == {"translation": [0, 0, 0], "rotation": [0, 0, 0, 1]}
        assert "positionTransforms" not in instance
    assert load_board_catalog_module().load_board_package(YY_PENTA_EVO_ROOT).board.id == "yy.penta-evo"


def test_yy_penta_evo_cords_use_existing_ring_and_independent_exterior_routes() -> None:
    """Catch false small passage holes, contact-bound leads or joined pair cords."""
    board = json.loads(package_board_text(YY_PENTA_EVO_ROOT))
    media = board["presentations"][0]["media"]
    assert media["type"] == "model"
    descriptor = json.loads((YY_PENTA_EVO_ROOT / media["descriptorPath"]).read_text())
    roles = {n["nodeID"].removesuffix("_001").replace("_", "-"): n["role"] for n in descriptor["nodes"]}
    assert roles["central-ring"] == roles["upper-band-exterior"] == "attachment"
    assert not any(token in name for name in roles for token in (
        "mount", "screw", "fastener", "cleat", "bracket", "hardware", "passage", "bore", "cord", "anchor"
    ))
    anchors, lead_ids = [], []
    for instance in media["instances"]:
        suspension = instance["suspension"]
        assert suspension["type"] == "pairedLeadCord"
        assert len(suspension["attachments"]) == 2
        assert set(suspension["passages"]) == {"left", "right"}
        assert all(len(route) == 1 for route in suspension["passages"].values())
        for lead in suspension["attachments"]:
            assert roles[lead["nodeID"].removesuffix("_001").replace("_", "-")] == "attachment"
            assert len(lead["contactPointsInModel"]) >= 2
            assert "authored-display-estimate" in lead["provenance"]
            lead_ids.append(lead["id"])
        assert len({tuple(a["pointInModel"]) for a in suspension["attachments"]}) == 2
        assert suspension["anchor"]["visibility"] == "invisible"
        anchors.append(tuple(suspension["anchor"]["offsetFromBoardBounds"]))
        assert "authored-display-estimate" in suspension["cord"]["provenance"]
        assert set(suspension["canonicalPoses"]) == {p["id"] for p in board["positions"]}
    assert len(set(anchors)) == 2
    assert len(set(lead_ids)) == 4


def test_yy_penta_evo_positions_expose_only_contacts_reachable_on_that_face() -> None:
    """Keep workout resolution from selecting the hidden rear 10mm on primary."""
    board = json.loads(package_board_text(YY_PENTA_EVO_ROOT))
    positions = {position["id"]: set(position["contactIDs"]) for position in board["positions"]}
    assert positions == {
        "primary": {f"{slot}-{side}" for side in ("left", "right")
                    for slot in ("edge-25", "edge-20", "edge-15", "mono", "duo", "tray")},
        "reverse": {f"{slot}-{side}" for side in ("left", "right")
                    for slot in ("edge-10", "mono", "duo", "tray")},
    }
    for instance in board["presentations"][0]["media"]["instances"]:
        suspension = instance["suspension"]
        for pose in suspension["canonicalPoses"].values():
            # The runtime uses explicit pose routes for surface wraps; default
            # contactPoints alone describe only the last approach stub.
            assert pose["cordContactPoints"] == {
                lead["id"]: lead["contactPointsInModel"] for lead in suspension["attachments"]
            }
