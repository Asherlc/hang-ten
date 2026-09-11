#!/usr/bin/env python3
"""Verify the actual exported Tension Flash Board USDZ.

The source `.blend` is compiled by ``compile_model_package.py`` first.  This
tool starts from an empty Blender scene, removes all source materials/images,
reimports only the USDZ, and verifies the importer-visible contract.  The
Flash Board has no separate attachment mesh: its approved integral passage is
addressed through the exported body node.  Cord and anchor checks are probes
against the actual imported board mesh; no cord or anchor geometry is written
to the package.

Example (inside the permitted host Blender runtime):

    blender --background --factory-startup --python-exit-code 1 \
      --python Tools/HangboardModels/verify_tension_flash_board.py -- \
      --output .context/pretty-crocodile-tension-flash-board/package \
      --skip-renders
"""

from __future__ import annotations

import argparse
from collections.abc import Mapping, Sequence
import hashlib
import json
import math
import re
from pathlib import Path
import sys
import struct
import zipfile

try:  # Keep pure report helpers importable by the host Python test runner.
    import bpy
except ModuleNotFoundError:  # pragma: no cover - exercised only outside Blender.
    bpy = None

TOOLS = Path(__file__).resolve().parent
if str(TOOLS) not in sys.path:
    sys.path.insert(0, str(TOOLS))

import compile_model_package as compiler


ROOT = TOOLS.parents[1]
BOARD_JSON = ROOT / "Hangboards/tension-flash-board/board.json"
EXPECTED_BOARD_ID = "tension.flash-board"
TRIANGLE_CEILING = 150_000
HOLD_IDS = (
    "three-edge-left",
    "three-edge-center",
    "three-edge-right",
    "two-edge-left",
    "two-edge-right",
    "small-crimp-left",
    "small-crimp-right",
)
POSITION_HOLD_IDS = {
    "three-edge-upright": (
        "three-edge-left",
        "three-edge-center",
        "three-edge-right",
    ),
    "three-edge-inverted": (
        "three-edge-left",
        "three-edge-center",
        "three-edge-right",
    ),
    "two-edge-upright": (
        "two-edge-left",
        "two-edge-right",
        "small-crimp-left",
        "small-crimp-right",
    ),
    "two-edge-inverted": (
        "two-edge-left",
        "two-edge-right",
        "small-crimp-left",
        "small-crimp-right",
    ),
}
POSITION_FACE_SIGN = {
    "three-edge-upright": 1,
    # Probes run against the unposed USDZ.  The inverted presentation rotates
    # the same physical face at runtime, so its source-space ray remains +Z.
    "three-edge-inverted": 1,
    "two-edge-upright": -1,
    "two-edge-inverted": -1,
}
LIGAMENT_IDS_BY_POSITION = {
    "three-edge-upright": (
        "exterior-left",
        "inter-pocket-three-edge-left-three-edge-center",
        "inter-pocket-three-edge-center-three-edge-right",
        "exterior-right",
    ),
    "three-edge-inverted": (
        "exterior-left",
        "inter-pocket-three-edge-left-three-edge-center",
        "inter-pocket-three-edge-center-three-edge-right",
        "exterior-right",
    ),
    "two-edge-upright": (
        "exterior-left",
        "inter-pocket-two-edge-left-two-edge-right",
        "inter-pocket-small-crimp-left-small-crimp-right",
        "exterior-right",
    ),
    "two-edge-inverted": (
        "exterior-left",
        "inter-pocket-two-edge-left-two-edge-right",
        "inter-pocket-small-crimp-left-small-crimp-right",
        "exterior-right",
    ),
}
LIGAMENT_GRID_SIZE = 3
ATTACHMENT_SOURCE_NODE_ID = "flash-board-body"
CORD_RADIUS_METERS = 0.002
CORD_CLEARANCE_METERS = 0.001
CANONICAL_TEXTURE_MEMBER = "textures/canonical-neutral-wood.png"
CENTERLINE_SUBDIVISIONS = 8
PASSAGE_TUBE_RADIUS_METERS = CORD_RADIUS_METERS + CORD_CLEARANCE_METERS
PASSAGE_INTERFACE_TOLERANCE_METERS = 1e-7
PASSAGE_CROSS_SECTION_RINGS = (
    (0.0, 1),
    (0.5, 8),
    (0.75, 8),
    (1.0, 16),
)
REVIEW_CANDIDATE_PATH = TOOLS / "fixtures/tension_flash_board_two_branch_review_candidate.json"
REVIEW_CANDIDATE_ID = "tension.flash-board.two-branch-review-v1"
REVIEW_PASSAGE_IDS = (
    "left-outer-passage",
    "left-inner-passage",
    "right-inner-passage",
    "right-outer-passage",
)
REVIEW_PASSAGE_MOUTHS = {
    "left-outer-passage": ((0.017, 0.047999999, 0.075999998), (0.017, 0.047999999, 0.0013394)),
    "left-inner-passage": ((0.031, 0.047999999, 0.075999998), (0.031, 0.047999999, 0.0013394)),
    "right-inner-passage": ((0.469, 0.047999999, 0.075999998), (0.469, 0.047999999, 0.0013394)),
    "right-outer-passage": ((0.483, 0.047999999, 0.075999998), (0.483, 0.047999999, 0.0013394)),
}
REVIEW_BRANCH_IDS = ("left-branch", "right-branch")


def load_review_candidate() -> dict[str, object]:
    candidate = load_json_object(REVIEW_CANDIDATE_PATH)
    validate_review_candidate(candidate)
    return candidate


def validate_review_candidate(candidate: Mapping[str, object]) -> None:
    """Validate the durable reference input; this does not assert native acceptance."""
    if candidate.get("candidateID") != REVIEW_CANDIDATE_ID:
        raise ValueError("review candidate ID is not the approved Flash Board candidate")
    if candidate.get("boardID") != EXPECTED_BOARD_ID:
        raise ValueError("review candidate board ID is not tension.flash-board")
    if candidate.get("status") != "reference fixture; production acceptance requires separate export and native verification":
        raise ValueError("review candidate must remain a reference input, not acceptance evidence")
    if candidate.get("actualExportStatus") != "retained separately in tension_flash_board_export_verification.json":
        raise ValueError("review candidate must identify its separate actual-export report")
    if candidate.get("type") != "twoBranchCord":
        raise ValueError("review candidate must declare twoBranchCord")
    provenance = candidate.get("provenance")
    if not isinstance(provenance, str) or "approved visual evidence" not in provenance or "display estimate" not in provenance:
        raise ValueError("review candidate must carry source-labeled display-estimate provenance")
    expected_model = candidate.get("expectedModel")
    if not isinstance(expected_model, Mapping) or set(expected_model) != {
        "identity", "sourceBodyNodeID", "modelSHA256", "descriptorSHA256", "coordinateFrame"
    }:
        raise ValueError("review candidate must pin the expected USDZ identity and hashes")
    if (
        not isinstance(expected_model.get("identity"), str)
        or not expected_model["identity"]
        or expected_model.get("sourceBodyNodeID") != ATTACHMENT_SOURCE_NODE_ID
        or expected_model.get("coordinateFrame") != "hang-ten-board-v1"
        or any(
            not isinstance(expected_model.get(key), str)
            or re.fullmatch(r"[0-9a-f]{64}", expected_model[key]) is None
            for key in ("modelSHA256", "descriptorSHA256")
        )
    ):
        raise ValueError("review candidate expected USDZ identity is invalid")
    passages = candidate.get("passages")
    if not isinstance(passages, Mapping) or set(passages) != {"left", "right"}:
        raise ValueError("review candidate must declare left and right passage pairs")
    records = [record for side in ("left", "right") for record in passages[side]]
    if len(records) != 4 or [record.get("id") for record in records] != list(REVIEW_PASSAGE_IDS):
        raise ValueError("review candidate passage IDs must match the four named physical passages")
    for record in records:
        passage_id = record.get("id")
        if record.get("physicalFeature") is None or record.get("nodeID") != expected_model["sourceBodyNodeID"]:
            raise ValueError(f"review candidate passage binding is invalid: {passage_id}")
        expected_entry, expected_exit = REVIEW_PASSAGE_MOUTHS[passage_id]
        for key, expected_point in (
            ("entryPointInModel", expected_entry),
            ("exitPointInModel", expected_exit),
        ):
            point = record.get(key)
            if not isinstance(point, list) or len(point) != 3 or any(
                not isinstance(value, (int, float)) or abs(float(value) - expected_point[index]) > 1e-9
                for index, value in enumerate(point)
            ):
                raise ValueError(f"review candidate passage {key} is not canonical: {passage_id}")
        passage_provenance = record.get("provenance")
        if not isinstance(passage_provenance, str) or "approved visual evidence" not in passage_provenance or "display estimate" not in passage_provenance:
            raise ValueError(f"review candidate passage lacks source-labeled provenance: {passage_id}")
    branches = candidate.get("branches")
    if not isinstance(branches, list) or len(branches) != 2 or [branch.get("id") for branch in branches] != list(REVIEW_BRANCH_IDS):
        raise ValueError("review candidate branch IDs must be left-branch and right-branch")
    expected_pairs = (
        ("left-outer-passage", "left-inner-passage"),
        ("right-inner-passage", "right-outer-passage"),
    )
    for branch, expected_pair in zip(branches, expected_pairs):
        if branch.get("passageIDs") != list(expected_pair):
            raise ValueError(f"review candidate branch passage linkage is not canonical: {branch.get('id')}")
        contact_sets = (
            ("entryContactPoints", 1),
            ("exteriorContactPoints", 2),
            ("exitContactPoints", 1),
        )
        if any(
            not isinstance(branch.get(key), list) or len(branch[key]) < minimum_count
            for key, minimum_count in contact_sets
        ) or any(
            not isinstance(point, list) or len(point) != 3
            or any(not isinstance(value, (int, float)) or not math.isfinite(float(value)) for value in point)
            for key, _ in contact_sets
            for point in branch[key]
        ):
            raise ValueError(f"review candidate branch must declare bounded contact points: {branch.get('id')}")
        if not isinstance(branch.get("restLength"), (int, float)) or float(branch["restLength"]) <= 0:
            raise ValueError(f"review candidate branch length is invalid: {branch.get('id')}")
        if not isinstance(branch.get("radius"), (int, float)) or float(branch["radius"]) <= 0:
            raise ValueError(f"review candidate branch radius is invalid: {branch.get('id')}")
        if not isinstance(branch.get("provenance"), str) or "display estimate" not in branch["provenance"]:
            raise ValueError(f"review candidate branch lacks display-estimate provenance: {branch.get('id')}")
    anchor = candidate.get("anchor")
    if (
        not isinstance(anchor, Mapping)
        or anchor.get("offsetFromBoardBounds") != [0, 0.5, 0]
        or anchor.get("visibility") != "invisible"
        or not isinstance(anchor.get("provenance"), str)
        or "display estimate" not in anchor["provenance"]
    ):
        raise ValueError("review candidate anchor is not the approved display estimate")
    poses = candidate.get("canonicalPoses")
    if not isinstance(poses, Mapping) or set(poses) != set(POSITION_HOLD_IDS):
        raise ValueError("review candidate poses must cover the exact four canonical positions")
    expected_poses = {
        "three-edge-upright": ([0, 0, 0, 1], [0, 0, 0]),
        "three-edge-inverted": ([0, 0, 1, 0], [0.5, 0.075999998, 0]),
        "two-edge-upright": ([1, 0, 0, 0], [0, 0.075999998, 0.075999998]),
        "two-edge-inverted": ([0, 1, 0, 0], [0.5, 0.075999998, 0.075999998]),
    }
    for position_id, (rotation, translation) in expected_poses.items():
        pose = poses[position_id]
        if pose.get("rotation") != rotation or pose.get("translation") != translation:
            raise ValueError(f"review candidate pose is not canonical: {position_id}")


def package_paths(package: Path) -> tuple[Path, Path]:
    """Return the only two compiler-owned package assets."""
    root = Path(package).resolve()
    if root.is_symlink() or not root.is_dir():
        raise ValueError(f"package directory must be a regular directory: {root}")
    actual = {
        path.relative_to(root).as_posix()
        for path in root.rglob("*")
        if path.is_file() and not path.is_symlink()
    }
    expected = {"assets/primary.usdz", "assets/primary.model.json"}
    if actual != expected:
        raise ValueError(f"compiler package assets must equal {sorted(expected)}")
    model = root / "assets/primary.usdz"
    descriptor = root / "assets/primary.model.json"
    return model, descriptor


def load_json_object(path: Path) -> dict[str, object]:
    try:
        value = json.loads(Path(path).read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        raise ValueError(f"JSON document is not readable: {path}") from error
    if not isinstance(value, dict):
        raise ValueError(f"JSON document must be an object: {path}")
    return value


def _integer(report: Mapping[str, object], key: str) -> int:
    value = report.get(key)
    if isinstance(value, bool) or not isinstance(value, int):
        raise ValueError(f"report field {key} must be an integer")
    return value


def verify_report(
    report: Mapping[str, object], *, expected_ids: frozenset[str]
) -> dict[str, object]:
    """Validate the durable report contract without requiring Blender."""
    if not isinstance(report, Mapping):
        raise ValueError("report must be an object")
    if report.get("boardID") != EXPECTED_BOARD_ID:
        raise ValueError("report boardID must identify tension.flash-board")
    candidate = load_review_candidate()
    if report.get("candidateID") != candidate["candidateID"] or report.get("suspensionType") != "twoBranchCord":
        raise ValueError("report must identify the review-only two-branch candidate")
    model_bounds = report.get("modelBounds")
    if not isinstance(model_bounds, Mapping) or set(model_bounds) != {"min", "max"}:
        raise ValueError("report must include actual model bounds for probe correspondence")
    hold_ids = report.get("holdIDs")
    if (
        not isinstance(hold_ids, list)
        or len(hold_ids) != len(expected_ids)
        or any(not isinstance(value, str) for value in hold_ids)
        or set(hold_ids) != set(expected_ids)
    ):
        raise ValueError("report holdIDs must equal the exact logical inventory")
    if _integer(report, "hold_ids_preserved") != len(expected_ids):
        raise ValueError("report must preserve all seven Flash Board hold IDs")
    if _integer(report, "body_mesh_count") != 1:
        raise ValueError("report must contain exactly one body mesh")
    if _integer(report, "attachment_mesh_count") not in (0, 1):
        raise ValueError("report permits at most one attachment mesh")
    for key in ("hardware_mesh_count", "baked_cord_mesh_count", "baked_anchor_mesh_count"):
        if _integer(report, key) != 0:
            raise ValueError(f"report must contain no {key.removesuffix('_mesh_count')} meshes")
    _validate_logical_bindings(report, expected_ids)
    _validate_passage_correspondence(report, candidate)
    if (
        report.get("coordinateFrame") != "hang-ten-board-v1"
        or report.get("exactDescriptorForActualUSDZ") is not True
        or report.get("sourceImagesClearedBeforeImport") is not True
    ):
        raise ValueError("report must prove isolated actual-USDZ verification")
    if report.get("modelIdentity") != candidate["expectedModel"]["identity"]:
        raise ValueError("report model identity does not match the review candidate")
    for hash_key in ("modelSHA256", "descriptorSHA256"):
        hash_value = report.get(hash_key)
        if not isinstance(hash_value, str) or re.fullmatch(r"[0-9a-f]{64}", hash_value) is None:
            raise ValueError(f"report {hash_key} must be a SHA-256 digest")
        if hash_value != candidate["expectedModel"][hash_key]:
            raise ValueError(f"report {hash_key} is not bound to the review candidate")
    textured = _integer(report, "texturedMeshCount")
    mesh_count = _integer(report, "meshCount")
    material_checks = report.get("materialChecks")
    if textured != mesh_count or not isinstance(material_checks, list) or len(material_checks) != mesh_count:
        raise ValueError("every imported board/contact mesh must have material and image evidence")
    material_nodes = [
        item.get("nodeID")
        for item in material_checks
        if isinstance(item, Mapping)
    ]
    binding_nodes = [
        item.get("nodeID")
        for item in report["logicalBindings"]
        if isinstance(item, Mapping)
    ]
    if material_nodes != binding_nodes or any(
        not isinstance(item, Mapping)
        or not isinstance(item.get("material"), str)
        or not item.get("material")
        or not isinstance(item.get("images"), list)
        or not item["images"]
        for item in material_checks
    ):
        raise ValueError("material evidence must cover every imported board/contact binding")
    source_mapping = report.get("sourcePieceCorrespondence")
    if not isinstance(source_mapping, Mapping) or set(source_mapping) != set(binding_nodes):
        raise ValueError("report source correspondence must cover every imported binding")
    for binding in report["logicalBindings"]:
        if binding.get("sourceNodeID") != source_mapping.get(binding.get("nodeID")):
            raise ValueError("logical binding source correspondence is inconsistent")
    if report.get("explicitTriangles") is not True:
        raise ValueError("report must prove explicit imported triangles")
    triangles = _integer(report, "triangles")
    ceiling = _integer(report, "triangleCeiling")
    if triangles <= 0 or ceiling != TRIANGLE_CEILING or triangles >= ceiling:
        raise ValueError("actual export triangles must be positive and below the recorded ceiling")
    texture = report.get("canonicalTexture")
    if not isinstance(texture, Mapping):
        raise ValueError("report must prove the canonical embedded texture")
    if texture.get("member") != CANONICAL_TEXTURE_MEMBER:
        raise ValueError("report must identify the canonical texture member")
    if texture.get("sha256") != hashlib.sha256(_canonical_texture_bytes()).hexdigest():
        raise ValueError("report canonical texture hash does not match the source")
    profile = texture.get("profile")
    if not isinstance(profile, Mapping) or set(profile) != {"sRGB", "gAMA", "cHRM"}:
        raise ValueError("report must retain the canonical PNG color profile")

    attachment = report.get("attachment")
    if attachment is not None:
        if not isinstance(attachment, Mapping):
            raise ValueError("report attachment must be an object")
        if not isinstance(attachment.get("nodeID"), str) or not attachment["nodeID"]:
            raise ValueError("attachment node must identify the imported body node")
        if attachment.get("sourceNodeID") is not None and not isinstance(attachment.get("sourceNodeID"), str):
            raise ValueError("attachment source node must be a string")
        if attachment.get("role") not in {"body", "attachment"}:
            raise ValueError("attachment node must be body or attachment role")
        if attachment.get("accessible") is not True:
            raise ValueError("attachment node and point must be importer-accessible")

    probes = report.get("positionProbes")
    if not isinstance(probes, Mapping) or set(probes) != set(POSITION_HOLD_IDS):
        raise ValueError("position ray/clearance probes must cover all four positions")
    _validate_branch_probe_evidence(report, candidate)
    for position_id, expected_hold_ids in POSITION_HOLD_IDS.items():
        result = probes[position_id]
        if not isinstance(result, Mapping):
            raise ValueError(f"position probe is not an object: {position_id}")
        if result.get("expectedHoldIDs") != list(expected_hold_ids):
            raise ValueError(f"position probe hold inventory changed: {position_id}")
        ligaments = result.get("ligamentResults")
        expected_ligament_ids = LIGAMENT_IDS_BY_POSITION[position_id]
        expected_ligament_samples = [
            (region_id, row, column)
            for region_id in expected_ligament_ids
            for row in range(LIGAMENT_GRID_SIZE)
            for column in range(LIGAMENT_GRID_SIZE)
        ]
        if not isinstance(ligaments, list) or [
            (item.get("regionID"), item.get("sampleRow"), item.get("sampleColumn"))
            for item in ligaments if isinstance(item, Mapping)
        ] != expected_ligament_samples:
            raise ValueError(f"ligament ray results are incomplete: {position_id}")
        if result.get("allLigamentProbesPassed") is not True or not all(
            isinstance(item, Mapping)
            and item.get("expectedRole") == "body"
            and item.get("nearestRole") == "body"
            and item.get("passed") is True
            and isinstance(item.get("nearestTriangleIndex"), int)
            and item["nearestTriangleIndex"] >= 0
            for item in ligaments
        ):
            raise ValueError(f"ligament ray probe failed for position {position_id}")
        rays = result.get("surfaceRayResults")
        expected_ray_ids = [hold_id for hold_id in expected_hold_ids for _ in range(5)]
        if not isinstance(rays, list) or len(rays) != len(expected_ray_ids):
            raise ValueError(f"surface ray results are incomplete: {position_id}")
        if [item.get("expectedID") for item in rays if isinstance(item, Mapping)] != expected_ray_ids:
            raise ValueError(f"surface ray hold order changed: {position_id}")
        if any(
            [ray.get("sampleIndex") for ray in rays[offset : offset + 5]] != list(range(5))
            for offset in range(0, len(rays), 5)
        ):
            raise ValueError(f"surface ray sample coverage is incomplete: {position_id}")
        if not all(
            isinstance(item, Mapping)
            and item.get("hit") is True
            and item.get("nearestID") == item.get("expectedID")
            and item.get("passed") is True
            and isinstance(item.get("nearestTriangleIndex"), int)
            and item["nearestTriangleIndex"] >= 0
            for item in rays
        ):
            raise ValueError(f"surface ray probe failed for position {position_id}")
        branches = result.get("branchClearanceResults")
        if not isinstance(branches, list) or len(branches) != 2:
            raise ValueError(f"branch clearance results must contain both branches: {position_id}")
        branch_ids = [item.get("branchID") for item in branches if isinstance(item, Mapping)]
        if len(branch_ids) != 2 or len(set(branch_ids)) != 2 or any(not isinstance(value, str) or not value for value in branch_ids):
            raise ValueError(f"branch clearance IDs are incomplete: {position_id}")
        if not all(
            isinstance(item, Mapping)
            and item.get("passed") is True
            and isinstance(item.get("minimumDistanceMeters"), (int, float))
            and isinstance(item.get("requiredClearanceMeters"), (int, float))
            and item["minimumDistanceMeters"] >= item["requiredClearanceMeters"]
            and _positive_integer(item, "sampleCount")
            and isinstance(item.get("centerlineSamples"), list)
            and len(item["centerlineSamples"]) == item.get("centerlineSampleCount")
            for item in branches
        ):
            raise ValueError(f"branch clearance probe failed for position {position_id}")
        if result.get("allRayProbesPassed") is not True:
            raise ValueError(f"ray probes failed for position {position_id}")
        if result.get("canonicalPoseTested") is not True:
            raise ValueError(f"canonical pose was not tested for position {position_id}")
        if result.get("allClearanceProbesPassed") is not True or result.get("actualMeshClearance") is not True:
            raise ValueError(f"clearance probes failed for position {position_id}")
        if _integer(result, "rayProbeCount") != len(expected_ray_ids):
            raise ValueError(f"ray probe count is incomplete: {position_id}")
        if _integer(result, "clearanceProbeCount") <= 0:
            raise ValueError(f"clearance probe count is empty: {position_id}")
    return dict(report)


def _positive_integer(value: Mapping[str, object], key: str) -> bool:
    number = value.get(key)
    return isinstance(number, int) and not isinstance(number, bool) and number > 0


def _validate_logical_bindings(
    report: Mapping[str, object], expected_ids: frozenset[str]
) -> None:
    """Require exactly the selectable hold inventory plus one body binding.

    The imported mesh, rather than a camera mask or a material name, is the
    source of truth.  In particular, a shallow ledge or a passage mouth must
    not be able to acquire a hold ID and become selectable by accident.
    """
    bindings = report.get("logicalBindings")
    if not isinstance(bindings, list):
        raise ValueError("report must contain logical binding inventory")
    node_ids: list[str] = []
    hold_ids: list[str] = []
    body_count = 0
    for binding in bindings:
        if not isinstance(binding, Mapping):
            raise ValueError("logical binding must be an object")
        node_id = binding.get("nodeID")
        role = binding.get("role")
        if not isinstance(node_id, str) or not node_id or node_id in node_ids:
            raise ValueError("logical binding node IDs must be unique")
        node_ids.append(node_id)
        if role == "body":
            body_count += 1
            if binding.get("holdID") is not None:
                raise ValueError("body binding may not declare holdID")
        elif role == "hold":
            hold_id = binding.get("holdID")
            if not isinstance(hold_id, str) or not hold_id:
                raise ValueError("hold binding requires holdID")
            hold_ids.append(hold_id)
        elif role == "attachment":
            if binding.get("holdID") is not None:
                raise ValueError("attachment binding may not declare holdID")
        else:
            raise ValueError("logical binding role is not selectable or physical")
    if body_count != 1:
        raise ValueError("logical binding inventory must contain one body")
    if len(hold_ids) != len(expected_ids) or set(hold_ids) != set(expected_ids):
        raise ValueError("logical binding inventory must contain exactly seven holds")
    mesh_count = report.get("meshCount")
    if isinstance(mesh_count, bool) or not isinstance(mesh_count, int) or mesh_count != len(bindings):
        raise ValueError("meshCount must equal the imported logical binding inventory")


def _validate_passage_correspondence(
    report: Mapping[str, object], candidate: Mapping[str, object]
) -> None:
    passages = report.get("passageCorrespondence")
    if not isinstance(passages, list) or len(passages) != 4:
        raise ValueError("report must contain exactly four passage correspondences")
    bindings = report["logicalBindings"]
    by_node = {
        binding["nodeID"]: binding
        for binding in bindings
        if isinstance(binding, Mapping) and isinstance(binding.get("nodeID"), str)
    }
    passage_ids: list[str] = []
    expected_records = {
        record["id"]: record
        for side in ("left", "right")
        for record in candidate["passages"][side]
    }
    source_mapping = report.get("sourcePieceCorrespondence")
    if not isinstance(source_mapping, Mapping):
        raise ValueError("passage correspondence requires source-node mapping")
    for passage in passages:
        if not isinstance(passage, Mapping):
            raise ValueError("passage correspondence must be an object")
        passage_id = passage.get("passageID")
        node_id = passage.get("nodeID")
        source_node_id = passage.get("sourceNodeID")
        role = passage.get("role")
        entry = passage.get("entryPointInModel")
        exit = passage.get("exitPointInModel")
        if (
            not isinstance(passage_id, str)
            or not passage_id
            or passage_id in passage_ids
            or not isinstance(node_id, str)
            or not node_id
            or not isinstance(source_node_id, str)
            or not source_node_id
            or role not in {"body", "attachment"}
            or any(
                not isinstance(point, list) or len(point) != 3
                or not all(isinstance(coordinate, (int, float)) and math.isfinite(coordinate) for coordinate in point)
                for point in (entry, exit)
            )
        ):
            raise ValueError("passage correspondence is incomplete or duplicated")
        expected = expected_records.get(passage_id)
        if (
            expected is None
            or passage.get("sourceNodeID") != source_mapping.get(node_id)
            or source_node_id != expected["nodeID"]
            or role != "body"
        ):
            raise ValueError("passage correspondence does not match candidate/source mapping")
        for actual_point, expected_point in (
            (entry, expected["entryPointInModel"]),
            (exit, expected["exitPointInModel"]),
        ):
            if any(abs(float(value) - float(expected_point[index])) > 1e-9 for index, value in enumerate(actual_point)):
                raise ValueError("passage correspondence mouth does not match the review candidate")
        binding = by_node.get(node_id)
        if binding is None or binding.get("role") != role:
            raise ValueError("passage correspondence must target a body or attachment binding")
        passage_ids.append(passage_id)
    if passage_ids != list(REVIEW_PASSAGE_IDS):
        raise ValueError("passage correspondence IDs are not the canonical physical passages")
    ray_results = report.get("passageRayResults")
    correspondence_by_id = {item["passageID"]: item for item in passages}
    if not isinstance(ray_results, list) or [
        item.get("passageID") for item in ray_results if isinstance(item, Mapping)
    ] != list(REVIEW_PASSAGE_IDS) or not all(
        isinstance(item, Mapping)
        and item.get("behavior") == "through-passage"
        and item.get("nodeID") == correspondence_by_id[item["passageID"]]["nodeID"]
        and item.get("sourceNodeID") == correspondence_by_id[item["passageID"]]["sourceNodeID"]
        and _is_swept_tube_probe(item.get("sweptTubeProbe"))
        and item.get("passed") is True
        for item in ray_results
    ):
        raise ValueError("passage ray proof does not establish all four physical openings")


def _is_clear_aperture_ray(value: object) -> bool:
    """A swept-tube sample must be continuously clear along the full axis."""
    return (
        isinstance(value, Mapping)
        and value.get("hit") is False
        and value.get("nearestRole") is None
        and value.get("nearestNodeID") is None
        and value.get("nearestTriangleIndex") is None
        and value.get("passed") is True
    )


def _passage_cross_section_offsets(radius: float) -> list[tuple[float, float]]:
    """Return the deterministic radial samples for the swept passage tube."""
    if not math.isfinite(radius) or radius <= 0:
        raise ValueError("passage tube radius must be finite and positive")
    offsets: list[tuple[float, float]] = []
    for fraction, count in PASSAGE_CROSS_SECTION_RINGS:
        if count == 1:
            offsets.append((0.0, 0.0))
            continue
        ring_radius = radius * fraction
        for index in range(count):
            angle = 2 * math.pi * index / count
            offsets.append((ring_radius * math.cos(angle), ring_radius * math.sin(angle)))
    return offsets


def _is_swept_tube_probe(value: object) -> bool:
    """Require the exact cord-sized cross-section at every full-depth ray."""
    expected = _passage_cross_section_offsets(PASSAGE_TUBE_RADIUS_METERS)
    return (
        isinstance(value, Mapping)
        and value.get("cordRadiusMeters") == CORD_RADIUS_METERS
        and value.get("clearanceToleranceMeters") == CORD_CLEARANCE_METERS
        and value.get("requiredRadiusMeters") == PASSAGE_TUBE_RADIUS_METERS
        and value.get("axis") == "model-z"
        and value.get("sampleCount") == len(expected)
        and value.get("axisContinuouslyTested") is True
        and isinstance(value.get("solidTubeProbe"), Mapping)
        and value["solidTubeProbe"].get("method") == "clipped-triangle-cylinder"
        and _positive_integer(value["solidTubeProbe"], "triangleCount")
        and value["solidTubeProbe"].get("requiredRadiusMeters") == PASSAGE_TUBE_RADIUS_METERS
        and value["solidTubeProbe"].get("passed") is True
        and (
            value["solidTubeProbe"].get("minimumRadiusMeters") is None
            or (isinstance(value["solidTubeProbe"].get("minimumRadiusMeters"), (int, float))
                and math.isfinite(value["solidTubeProbe"]["minimumRadiusMeters"])
                and value["solidTubeProbe"]["minimumRadiusMeters"] >= PASSAGE_TUBE_RADIUS_METERS)
        )
        and isinstance(value.get("samples"), list)
        and len(value["samples"]) == len(expected)
        and [item.get("sampleIndex") for item in value["samples"] if isinstance(item, Mapping)] == list(range(len(expected)))
        and all(
            isinstance(item, Mapping)
            and isinstance(item.get("sampleIndex"), int)
            and not isinstance(item.get("sampleIndex"), bool)
            and 0 <= item["sampleIndex"] < len(expected)
            and isinstance(item.get("offsetMeters"), list)
            and len(item["offsetMeters"]) == 2
            and all(
                isinstance(item["offsetMeters"][axis], (int, float))
                and math.isfinite(float(item["offsetMeters"][axis]))
                and abs(float(item["offsetMeters"][axis]) - expected[item["sampleIndex"]][axis]) <= 1e-9
                for axis in range(2)
            )
            and _is_clear_aperture_ray(item.get("frontToRear"))
            and _is_clear_aperture_ray(item.get("rearToFront"))
            and item.get("passed") is True
            for item in value["samples"]
        )
        and value.get("passed") is True
    )


def _validate_branch_probe_evidence(
    report: Mapping[str, object], candidate: Mapping[str, object]
) -> None:
    bounds = report["modelBounds"]
    branch_records = {branch["id"]: branch for branch in candidate["branches"]}
    passages = {
        record["id"]: record
        for side in ("left", "right")
        for record in candidate["passages"][side]
    }
    for position_id in POSITION_HOLD_IDS:
        if position_id not in report["positionProbes"]:
            raise ValueError(f"position probe is missing: {position_id}")
        result = report["positionProbes"][position_id]
        branch_results = result["branchClearanceResults"]
        if [branch.get("branchID") for branch in branch_results] != list(REVIEW_BRANCH_IDS):
            raise ValueError(f"branch clearance IDs are not canonical: {position_id}")
        for branch_result in branch_results:
            branch_id = branch_result["branchID"]
            branch = branch_records[branch_id]
            passage_ids = branch["passageIDs"]
            if branch_result.get("passageIDs") != passage_ids:
                raise ValueError(f"branch passage linkage changed: {branch_id}")
            declared_length = branch_result.get("declaredRestLengthMeters")
            if (
                isinstance(declared_length, bool)
                or not isinstance(declared_length, (int, float))
                or abs(float(declared_length) - float(branch["restLength"])) > 1e-9
            ):
                raise ValueError(f"branch rest length changed: {branch_id}")
            required_clearance = branch_result.get("requiredClearanceMeters")
            if (
                isinstance(required_clearance, bool)
                or not isinstance(required_clearance, (int, float))
                or abs(float(required_clearance) - (float(branch["radius"]) + CORD_CLEARANCE_METERS)) > 1e-9
            ):
                raise ValueError(f"branch clearance threshold changed: {branch_id}")
            interface_points = branch_result.get("interfacePoints")
            if not isinstance(interface_points, list) or [
                point.get("passageID") for point in interface_points if isinstance(point, Mapping)
            ] != passage_ids:
                raise ValueError(f"branch interface IDs are incomplete: {branch_id}")
            pose = candidate["canonicalPoses"][position_id]
            expected_points = [
                _transform_point(passages[passage_id]["entryPointInModel"], pose)
                for passage_id in passage_ids
            ]
            for interface, expected_point in zip(interface_points, expected_points):
                point = interface.get("entryPointInModel")
                expected_node = report["passageCorrespondence"][
                    REVIEW_PASSAGE_IDS.index(interface["passageID"])
                ]["nodeID"]
                if interface.get("nodeID") != expected_node:
                    raise ValueError(f"branch interface node is not importer-visible: {branch_id}")
                if not isinstance(point, list) or len(point) != 3 or any(
                    abs(float(point[index]) - expected_point[index]) > 1e-8
                    for index in range(3)
                ):
                    raise ValueError(f"branch interface point is not posed candidate geometry: {branch_id}")
            generated = next(
                spec for spec in _branch_probe_specs(
                    bounds,
                    candidate,
                    pose,
                    {
                        item["passageID"]: item["nodeID"]
                        for item in report["passageCorrespondence"]
                    },
                ) if spec["branchID"] == branch_id
            )
            samples = branch_result.get("centerlineSamples")
            if not isinstance(samples, list) or len(samples) != len(generated["samples"]):
                raise ValueError(f"branch centerline samples are incomplete: {branch_id}")
            if branch_result.get("contactSegments") != generated["contactSegments"]:
                raise ValueError(f"branch exterior contact topology changed: {branch_id}")
            anchor = _suspension_anchor(bounds, candidate)
            if any(abs(float(samples[0][index]) - anchor[index]) > 1e-8 for index in range(3)):
                raise ValueError(f"branch centerline anchor is inconsistent: {branch_id}")
            if any(abs(float(samples[-1][index]) - anchor[index]) > 1e-8 for index in range(3)):
                raise ValueError(f"branch centerline closure is inconsistent: {branch_id}")
            # The two free catenaries terminate at the declared front-shoulder
            # contacts.  The entry mouths remain independently recorded in
            # interfacePoints, one contact segment later; treating their
            # indices as the free-span endpoints would silently reintroduce
            # the bore-centre departure defect this contract prevents.
            for sample, expected_point in zip(
                (samples[31], samples[-32]),
                (generated["samples"][31], generated["samples"][-32]),
            ):
                if any(abs(float(sample[index]) - expected_point[index]) > 1e-8 for index in range(3)):
                    raise ValueError(f"branch centerline passage join is inconsistent: {branch_id}")


def validate_attachment_node(attachment: Mapping[str, object], bindings: Sequence[object]) -> None:
    """Require a real imported body/attachment binding, never a hold."""
    node_id = attachment.get("nodeID")
    role = attachment.get("role")
    matching = [binding for binding in bindings if getattr(binding, "node_id", None) == node_id]
    if len(matching) != 1:
        raise ValueError("attachment node is not importer-visible")
    actual_role = getattr(matching[0], "role", None)
    if actual_role not in {"body", "attachment"} or role != actual_role:
        raise ValueError("attachment node must be a body or attachment binding")


def _property(item: object, key: str) -> object:
    getter = getattr(item, "get", None)
    if not callable(getter):
        return None
    value = getter(key)
    return value if value is not None else getter(f"userProperties:{key}")


def _material_checks(bindings: Sequence[object], objects: Mapping[str, object]) -> list[dict[str, object]]:
    checks: list[dict[str, object]] = []
    for binding in bindings:
        node_id = binding.node_id
        item = objects[node_id]
        mesh = item.data
        used_indexes = {polygon.material_index for polygon in mesh.polygons}
        if not used_indexes:
            raise ValueError(f"imported mesh {node_id} has no material-bearing faces")
        for index in used_indexes:
            if index >= len(mesh.materials) or mesh.materials[index] is None:
                raise ValueError(f"imported mesh {node_id} is materialless")
            material = mesh.materials[index]
            images = [
                node.image
                for node in material.node_tree.nodes
                if node.type == "TEX_IMAGE" and node.image is not None
            ]
            if not images or not all(image.has_data and min(image.size) > 0 for image in images):
                raise ValueError(f"imported mesh {node_id} has no usable image material")
            checks.append(
                {
                    "nodeID": node_id,
                    "material": material.name,
                    "images": [
                        {"name": image.name, "width": image.size[0], "height": image.size[1]}
                        for image in images
                    ],
                }
            )
    return checks


def _canonical_texture_bytes() -> bytes:
    import canonical_neutral_wood

    return canonical_neutral_wood.CANONICAL_TEXTURE_PATH.read_bytes()


def _png_profile_metadata(payload: bytes) -> dict[str, bytes]:
    """Read the canonical PNG profile chunks without decoding pixels."""
    if not payload.startswith(b"\x89PNG\r\n\x1a\n"):
        raise ValueError("canonical texture must be a PNG")
    metadata: dict[str, bytes] = {}
    offset = 8
    while offset < len(payload):
        if offset + 12 > len(payload):
            raise ValueError("canonical texture has a truncated PNG chunk")
        length = struct.unpack(">I", payload[offset : offset + 4])[0]
        kind = payload[offset + 4 : offset + 8]
        end = offset + 12 + length
        if end > len(payload):
            raise ValueError("canonical texture has a truncated PNG payload")
        if kind in {b"sRGB", b"gAMA", b"cHRM"}:
            metadata[kind.decode("ascii")] = payload[offset + 8 : offset + 8 + length]
        offset = end
        if kind == b"IEND":
            break
    required = {"sRGB", "gAMA", "cHRM"}
    if set(metadata) != required:
        raise ValueError("canonical texture must declare sRGB, gAMA, and cHRM metadata")
    return metadata


def _verify_canonical_texture_archive(archive: zipfile.ZipFile) -> dict[str, object]:
    """Require the exact canonical wood bytes and explicit profile metadata."""
    names = [name for name in archive.namelist() if name.lower().endswith((".png", ".jpg", ".jpeg"))]
    if names != [CANONICAL_TEXTURE_MEMBER]:
        raise ValueError("USDZ must contain exactly the canonical wood texture member")
    expected = _canonical_texture_bytes()
    embedded = archive.read(CANONICAL_TEXTURE_MEMBER)
    if not embedded:
        raise ValueError("USDZ canonical texture must be non-empty")
    if hashlib.sha256(embedded).digest() != hashlib.sha256(expected).digest() or embedded != expected:
        raise ValueError("USDZ canonical texture must be byte-identical to the source")
    expected_profile = _png_profile_metadata(expected)
    embedded_profile = _png_profile_metadata(embedded)
    if embedded_profile != expected_profile:
        raise ValueError("USDZ canonical texture profile metadata does not match the source")
    return {
        "member": CANONICAL_TEXTURE_MEMBER,
        "sha256": hashlib.sha256(embedded).hexdigest(),
        "profile": {key: value.hex() for key, value in expected_profile.items()},
    }


def _transform_point(point: Sequence[float], pose: Mapping[str, object]) -> tuple[float, float, float]:
    rotation = pose["rotation"]
    translation = pose["translation"]
    x, y, z, w = (float(value) for value in rotation)
    px, py, pz = (float(value) for value in point)
    tx = 2 * (y * pz - z * py)
    ty = 2 * (z * px - x * pz)
    tz = 2 * (x * py - y * px)
    return (
        px + w * tx + (y * tz - z * ty) + float(translation[0]),
        py + w * ty + (z * tx - x * tz) + float(translation[1]),
        pz + w * tz + (x * ty - y * tx) + float(translation[2]),
    )


def _suspension_samples(
    bounds: Mapping[str, object],
    suspension: Mapping[str, object],
    pose: Mapping[str, object],
) -> list[tuple[float, float, float]]:
    """Reproduce the app's fixed-sample catenary for one canonical pose."""
    anchor = _suspension_anchor(bounds, suspension)
    attachment = _transform_point(suspension["attachment"]["pointInModel"], pose)
    rest_length = float(suspension["cord"]["restLength"])
    return _catenary_samples(anchor, attachment, rest_length)


def _suspension_anchor(
    bounds: Mapping[str, object], suspension: Mapping[str, object]
) -> tuple[float, float, float]:
    minimum = tuple(float(value) for value in bounds["min"])
    maximum = tuple(float(value) for value in bounds["max"])
    offset = tuple(float(value) for value in suspension["anchor"]["offsetFromBoardBounds"])
    return (
        (minimum[0] + maximum[0]) / 2 + offset[0],
        maximum[1] + offset[1],
        (minimum[2] + maximum[2]) / 2 + offset[2],
    )


def _catenary_samples(
    anchor: tuple[float, float, float],
    attachment: tuple[float, float, float],
    rest_length: float,
) -> list[tuple[float, float, float]]:
    """Reproduce the runtime's fixed-sample span solver for two endpoints."""
    delta = tuple(attachment[index] - anchor[index] for index in range(3))
    endpoint_distance = math.sqrt(sum(value * value for value in delta))
    if rest_length < endpoint_distance - 1e-5:
        raise ValueError("canonical pose cord is shorter than its endpoints")
    if abs(rest_length - endpoint_distance) <= 1e-5:
        return [
            tuple(anchor[axis] + delta[axis] * index / 31 for axis in range(3))
            for index in range(32)
        ]

    vertical = -delta[1]
    horizontal_vector = (delta[0], 0.0, delta[2])
    horizontal = math.sqrt(horizontal_vector[0] ** 2 + horizontal_vector[2] ** 2)
    horizontal_arc = math.sqrt(rest_length * rest_length - vertical * vertical)
    if horizontal <= 1e-7 or horizontal_arc <= horizontal:
        raise ValueError("canonical pose has no finite catenary solution")

    def residual(parameter: float) -> float:
        argument = horizontal / (2 * parameter)
        if argument >= 80:
            return math.inf
        return 2 * parameter * math.sinh(argument) - horizontal_arc

    lower = min(horizontal, horizontal_arc) * 1e-6
    upper = max(horizontal, horizontal_arc) / 2
    for _ in range(64):
        if residual(lower) >= 0:
            break
        lower /= 2
    for _ in range(64):
        if residual(upper) <= 0:
            break
        upper *= 2
    if residual(lower) < 0 or residual(upper) > 0:
        raise ValueError("canonical pose catenary is unbracketed")
    for _ in range(128):
        midpoint = (lower + upper) / 2
        if residual(midpoint) > 0:
            lower = midpoint
        else:
            upper = midpoint
        if upper - lower <= 1e-6:
            break
    parameter = (lower + upper) / 2
    horizontal_axis = (horizontal_vector[0] / horizontal, 0.0, horizontal_vector[2] / horizontal)
    shift = horizontal / 2 + parameter * math.asinh(vertical / horizontal_arc)
    crest = parameter * math.cosh(shift / parameter)
    samples: list[tuple[float, float, float]] = []
    for index in range(32):
        x = horizontal * index / 31
        sag = crest - parameter * math.cosh((x - shift) / parameter)
        samples.append(
            tuple(
                anchor[axis] + horizontal_axis[axis] * x + (sag if axis == 1 else 0.0) * (-1 if axis == 1 else 1)
                for axis in range(3)
            )
        )
    samples[0] = anchor
    samples[-1] = attachment
    return samples


def _check_centerline_clearance(
    samples: Sequence[tuple[float, float, float]],
    *,
    required_clearance: float,
    attachment_node_id: str,
    nearest,
    interface_points: Sequence[tuple[str, tuple[float, float, float]]] = (),
    segment_modes: Sequence[str] | None = None,
) -> dict[str, object]:
    """Apply the runtime segment/tube clearance rule to a nearest-mesh query."""
    if len(samples) < 2:
        raise ValueError("suspension catenary must contain at least two samples")
    minimum = math.inf
    checked = 0
    node_ids = tuple(getattr(nearest, "node_ids", (attachment_node_id,)))
    for segment_index, (start, end) in enumerate(zip(samples, samples[1:])):
        mode = segment_modes[segment_index] if segment_modes is not None else "free"
        if mode not in {"free", "through-bore", "exterior-contact"}:
            raise ValueError(f"unknown cord route segment mode: {mode}")
        if mode == "through-bore":
            continue
        for subdivision in range(CENTERLINE_SUBDIVISIONS + 1):
            fraction = subdivision / CENTERLINE_SUBDIVISIONS
            point = tuple(start[axis] + (end[axis] - start[axis]) * fraction for axis in range(3))
            for node_id in node_ids:
                distance, nearest_point = nearest(node_id, point)
                # Report the minimum that is subject to the general 3 mm
                # free-span rule. A declared body-only bearing has its own
                # independently enforced cord-radius rule below.
                if mode != "exterior-contact" or node_id != attachment_node_id:
                    minimum = min(minimum, distance)
                checked += 1
                if mode == "exterior-contact":
                    # A physical bearing is allowed only on the integral body,
                    # while every selectable hold retains the full free-span
                    # threshold. The body centreline must remain at least one
                    # cord radius outside the imported mesh.
                    contact_clearance = required_clearance - CORD_CLEARANCE_METERS
                    threshold = contact_clearance if node_id == attachment_node_id else required_clearance
                    if distance >= threshold:
                        continue
                    return {
                        "passed": False,
                        "minimumDistanceMeters": minimum,
                        "requiredClearanceMeters": required_clearance,
                        "sampleCount": checked,
                        "failedNodeID": node_id,
                        "failedSegmentIndex": segment_index,
                        "failedSegmentFraction": fraction,
                    }
                if distance >= required_clearance:
                    continue
                interface = (
                    any(
                        interface_node == node_id
                        and math.dist(point, interface_point) <= PASSAGE_INTERFACE_TOLERANCE_METERS
                        and math.dist(nearest_point, interface_point) <= PASSAGE_INTERFACE_TOLERANCE_METERS
                        for interface_node, interface_point in interface_points
                    )
                    if interface_points
                    else node_id == attachment_node_id
                    and segment_index == len(samples) - 2
                    and fraction >= 1 - PASSAGE_INTERFACE_TOLERANCE_METERS
                    and math.dist(point, samples[-1]) <= PASSAGE_INTERFACE_TOLERANCE_METERS
                    and math.dist(nearest_point, samples[-1]) <= PASSAGE_INTERFACE_TOLERANCE_METERS
                )
                if not interface:
                    return {
                        "passed": False,
                        "minimumDistanceMeters": minimum,
                        "requiredClearanceMeters": required_clearance,
                        "sampleCount": checked,
                        "failedNodeID": node_id,
                        "failedSegmentIndex": segment_index,
                        "failedSegmentFraction": fraction,
                    }
    return {
        "passed": True,
        "minimumDistanceMeters": minimum,
        "requiredClearanceMeters": required_clearance,
        "sampleCount": checked,
    }


def _ray_probes(
    objects: Mapping[str, object],
    descriptor: Mapping[str, object],
) -> dict[str, dict[str, object]]:
    if bpy is None:
        raise RuntimeError("ray probes require Blender")
    bounds = descriptor["modelBounds"]
    minimum = tuple(float(v) for v in bounds["min"])
    maximum = tuple(float(v) for v in bounds["max"])
    scene = bpy.context.scene
    depsgraph = bpy.context.evaluated_depsgraph_get()
    holds = descriptor["holds"]
    result: dict[str, dict[str, object]] = {}
    for position_id, expected_hold_ids in POSITION_HOLD_IDS.items():
        sign = POSITION_FACE_SIGN[position_id]
        probes = []
        for hold_id in expected_hold_ids:
            aabb = holds[hold_id]["facePlaneAABB"]
            x_min, y_min = (float(value) for value in aabb["min"])
            x_max, y_max = (float(value) for value in aabb["max"])
            # Center plus four interior samples proves the complete authored
            # face-plane extent instead of trusting a single center proxy.
            face_samples = ((0.5, 0.5), (0.25, 0.25), (0.75, 0.25), (0.25, 0.75), (0.75, 0.75))
            for sample_index, (x_fraction, y_fraction) in enumerate(face_samples):
                origin = (
                    minimum[0] + (maximum[0] - minimum[0]) * (x_min + (x_max - x_min) * x_fraction),
                    minimum[1] + (maximum[1] - minimum[1]) * (y_min + (y_max - y_min) * y_fraction),
                    maximum[2] + 0.05 if sign > 0 else minimum[2] - 0.05,
                )
                direction = (0.0, 0.0, -1.0 if sign > 0 else 1.0)
                hit, location, _, triangle_index, nearest, _ = scene.ray_cast(
                    depsgraph, origin, direction, distance=0.2
                )
                nearest_hold_id = _property(nearest, "hold_id") if nearest else None
                passed = bool(hit and nearest_hold_id == hold_id)
                probes.append(
                    {
                        "expectedID": hold_id,
                        "sampleIndex": sample_index,
                        "nearestID": nearest_hold_id,
                        "nearestTriangleIndex": int(triangle_index) if hit else None,
                        "origin": [float(v) for v in origin],
                        "direction": [float(v) for v in direction],
                        "hit": bool(hit),
                        "location": [float(v) for v in location] if hit else None,
                        "passed": passed,
                    }
                )
                if not passed:
                    raise ValueError(
                        f"ray probe missed {hold_id} surface sample {sample_index} for {position_id}; nearest={nearest_hold_id}"
                    )
        result[position_id] = {
            "expectedHoldIDs": list(expected_hold_ids),
            "rayProbeCount": len(probes),
            "surfaceRayResults": probes,
            "allRayProbesPassed": True,
        }
        ligament_results = _ligament_probes(scene, depsgraph, objects, descriptor, sign, expected_hold_ids)
        result[position_id]["ligamentResults"] = ligament_results
        result[position_id]["allLigamentProbesPassed"] = True
    return result


def _ligament_probes(
    scene: object,
    depsgraph: object,
    objects: Mapping[str, object],
    descriptor: Mapping[str, object],
    sign: int,
    expected_hold_ids: Sequence[str],
) -> list[dict[str, object]]:
    """Ray-check exterior and inter-pocket wood ligaments in the real mesh."""
    body_ids = [node_id for node_id, item in objects.items() if _property(item, "role") == "body"]
    if len(body_ids) != 1:
        raise ValueError("actual export must expose one body for ligament probes")
    body_id = body_ids[0]
    bounds = descriptor["modelBounds"]
    minimum = tuple(float(value) for value in bounds["min"])
    maximum = tuple(float(value) for value in bounds["max"])
    all_aabbs = [descriptor["holds"][hold_id]["facePlaneAABB"] for hold_id in expected_hold_ids]
    face_y_min = min(float(aabb["min"][1]) for aabb in all_aabbs)
    face_y_max = max(float(aabb["max"][1]) for aabb in all_aabbs)
    left_edge = min(float(aabb["min"][0]) for aabb in all_aabbs)
    right_edge = max(float(aabb["max"][0]) for aabb in all_aabbs)
    regions: list[tuple[str, tuple[float, float], tuple[float, float]]] = [
        ("exterior-left", (0.01, left_edge - 0.01), (face_y_min, face_y_max)),
    ]
    pair_ids = {
        3: (
            ("three-edge-left", "three-edge-center"),
            ("three-edge-center", "three-edge-right"),
        ),
        4: (
            ("two-edge-left", "two-edge-right"),
            ("small-crimp-left", "small-crimp-right"),
        ),
    }.get(len(expected_hold_ids))
    if pair_ids is None:
        raise ValueError("unsupported Flash Board ligament inventory")
    for left_id, right_id in pair_ids:
        left = descriptor["holds"][left_id]["facePlaneAABB"]
        right = descriptor["holds"][right_id]["facePlaneAABB"]
        left_max = float(left["max"][0])
        right_min = float(right["min"][0])
        y_min = max(float(left["min"][1]), float(right["min"][1]))
        y_max = min(float(left["max"][1]), float(right["max"][1]))
        if right_min - left_max <= 0.005 or y_min >= y_max:
            raise ValueError(f"actual descriptor has no full ligament between {left_id} and {right_id}")
        regions.append((
            f"inter-pocket-{left_id}-{right_id}",
            (left_max, right_min),
            (y_min, y_max),
        ))
    regions.append(("exterior-right", (right_edge + 0.01, 0.99), (face_y_min, face_y_max)))
    results: list[dict[str, object]] = []
    for region_id, x_range, y_range in regions:
        if x_range[0] >= x_range[1] or y_range[0] >= y_range[1]:
            raise ValueError(f"actual descriptor has no full ligament region: {region_id}")
        for sample_row in range(LIGAMENT_GRID_SIZE):
            for sample_column in range(LIGAMENT_GRID_SIZE):
                normalized_x = x_range[0] + (x_range[1] - x_range[0]) * (sample_column + 0.5) / LIGAMENT_GRID_SIZE
                normalized_y = y_range[0] + (y_range[1] - y_range[0]) * (sample_row + 0.5) / LIGAMENT_GRID_SIZE
                origin = (
                    minimum[0] + (maximum[0] - minimum[0]) * normalized_x,
                    minimum[1] + (maximum[1] - minimum[1]) * normalized_y,
                    maximum[2] + 0.05 if sign > 0 else minimum[2] - 0.05,
                )
                direction = (0.0, 0.0, -1.0 if sign > 0 else 1.0)
                hit, location, _, triangle_index, nearest, _ = scene.ray_cast(
                    depsgraph, origin, direction, distance=0.2
                )
                nearest_role = _property(nearest, "role") if nearest else None
                results.append({
                    "regionID": region_id,
                    "sampleRow": sample_row,
                    "sampleColumn": sample_column,
                    "expectedRole": "body",
                    "nearestRole": nearest_role,
                    "nearestNodeID": nearest.name if nearest else None,
                    "nearestTriangleIndex": int(triangle_index) if hit else None,
                    "origin": [float(value) for value in origin],
                    "direction": [float(value) for value in direction],
                    "location": [float(value) for value in location] if hit else None,
                    "hit": bool(hit),
                    "passed": bool(hit and nearest_role == "body"),
                })
                if not results[-1]["passed"]:
                    raise ValueError(
                        f"ligament continuity ray missed body at {region_id} row={sample_row} column={sample_column}"
                    )
    return results


def _validate_closed_centerline(samples: Sequence[Sequence[float]], tolerance: float = 1e-6) -> None:
    """Reject segment crossings and backtracking, allowing only anchor closure."""
    def sub(a, b):
        return tuple(x - y for x, y in zip(a, b))

    def dot(a, b):
        return sum(x * y for x, y in zip(a, b))

    segments = list(zip(samples, samples[1:]))
    for i, (a, b) in enumerate(segments):
        u = sub(b, a)
        uu = dot(u, u)
        if uu <= 1e-20:
            raise ValueError("cord centerline self-intersects at a repeated point")
        for j in range(i + 1, len(segments)):
            c, d = segments[j]
            v, w = sub(d, c), sub(a, c)
            vv, uv, uw, vw = dot(v, v), dot(u, v), dot(u, w), dot(v, w)
            if vv <= 1e-20:
                raise ValueError("cord centerline self-intersects at a repeated point")
            clamp = lambda x: min(1.0, max(0.0, x))
            candidates = [(0.0, clamp(vw / vv)), (1.0, clamp((vw + uv) / vv)),
                          (clamp(-uw / uu), 0.0), (clamp((uv - uw) / uu), 1.0)]
            determinant = uu * vv - uv * uv
            if determinant > 1e-15 * uu * vv:
                s, t = (uv * vw - vv * uw) / determinant, (uu * vw - uv * uw) / determinant
                if 0 <= s <= 1 and 0 <= t <= 1:
                    candidates.append((s, t))
            for s, t in candidates:
                p = tuple(a[k] + s * u[k] for k in range(3))
                q = tuple(c[k] + t * v[k] for k in range(3))
                if math.dist(p, q) > tolerance:
                    continue
                shared = b if j == i + 1 else a if i == 0 and j == len(segments) - 1 and a == d else None
                if shared is not None and math.dist(p, shared) <= tolerance and math.dist(q, shared) <= tolerance:
                    continue
                raise ValueError(f"cord centerline self-intersects between segments {i} and {j}")


def _branch_probe_specs(
    bounds: Mapping[str, object],
    suspension: Mapping[str, object],
    pose: Mapping[str, object],
    passage_node_ids: Mapping[str, str],
) -> list[dict[str, object]]:
    """Build the exact two-branch centerlines used by the runtime solver."""
    if suspension.get("type") != "twoBranchCord":
        attachment = suspension["attachment"]
        return [{
            "branchID": "single-cord",
            "samples": _suspension_samples(bounds, suspension, pose),
            "interfacePoints": [(passage_node_ids.get("attachment", str(attachment["nodeID"])), _transform_point(attachment["pointInModel"], pose))],
            "radius": float(suspension["cord"]["radius"]),
        }]

    anchor = _suspension_anchor(bounds, suspension)
    passages = {
        passage["id"]: passage
        for side in ("left", "right")
        for passage in suspension["passages"][side]
    }
    specs: list[dict[str, object]] = []
    for branch in suspension["branches"]:
        first_record = passages[branch["passageIDs"][0]]
        second_record = passages[branch["passageIDs"][1]]
        first_entry = _transform_point(first_record["entryPointInModel"], pose)
        first_exit = _transform_point(first_record["exitPointInModel"], pose)
        second_exit = _transform_point(second_record["exitPointInModel"], pose)
        second_entry = _transform_point(second_record["entryPointInModel"], pose)
        entry_contacts = _pose_aware_shoulder_contacts(
            branch["entryContactPoints"],
            anchor=anchor,
            bounds=bounds,
            pose=pose,
            is_entry=True,
        )
        contact_points = [
            _transform_point(point, pose) for point in branch["exteriorContactPoints"]
        ]
        exit_contacts = _pose_aware_shoulder_contacts(
            branch["exitContactPoints"],
            anchor=anchor,
            bounds=bounds,
            pose=pose,
            is_entry=False,
        )
        if len(entry_contacts) < 1 or len(contact_points) < 2 or len(exit_contacts) < 1:
            raise ValueError(f"branch {branch['id']} must declare a bounded exterior contact route")
        rigid_route = [
            *entry_contacts,
            first_entry,
            first_exit,
            *contact_points,
            second_exit,
            second_entry,
            *exit_contacts,
        ]
        rigid_length = sum(math.dist(start, end) for start, end in zip(rigid_route, rigid_route[1:]))
        bore_length = math.dist(first_entry, first_exit) + math.dist(second_exit, second_entry)
        first_distance = math.dist(anchor, entry_contacts[0])
        second_distance = math.dist(anchor, exit_contacts[-1])
        declared = float(branch["restLength"])
        minimum_route = first_distance + rigid_length + second_distance
        if declared < minimum_route - 1e-5:
            raise ValueError(f"branch {branch['id']} is shorter than its posed route")
        free_length = declared - rigid_length
        endpoint_sum = first_distance + second_distance
        if endpoint_sum <= 1e-7 or free_length < endpoint_sum - 1e-5:
            raise ValueError(f"branch {branch['id']} has no valid free span")
        first_free = free_length * (first_distance / endpoint_sum)
        second_free = free_length - first_free
        first_span = _catenary_samples(anchor, entry_contacts[0], first_free)
        second_span = list(reversed(_catenary_samples(anchor, exit_contacts[-1], second_free)))
        first_bore = _line_samples(first_entry, first_exit)
        second_bore = _line_samples(second_exit, second_entry)
        samples = (
            first_span
            + entry_contacts[1:]
            + [first_entry]
            + first_bore[1:]
            + contact_points
            + [second_exit]
            + second_bore[1:]
            + exit_contacts
            + second_span[1:]
        )
        segment_modes = (
            ["free"] * (len(first_span) - 1)
            + ["exterior-contact"] * len(entry_contacts)
            + ["through-bore"] * (len(first_bore) - 1)
            + ["exterior-contact"] * (len(contact_points) + 1)
            + ["through-bore"] * (len(second_bore) - 1)
            + ["exterior-contact"] * len(exit_contacts)
            + ["free"] * (len(second_span) - 1)
        )
        if len(segment_modes) != len(samples) - 1:
            raise ValueError(f"branch {branch['id']} has a discontinuous directed route")
        _validate_closed_centerline(samples)
        specs.append({
            "branchID": str(branch["id"]),
            "samples": samples,
            "interfacePoints": [
                (passage_node_ids[str(first_record["id"])], first_entry),
                (passage_node_ids[str(second_record["id"])], second_entry),
            ],
            "passageIDs": list(branch["passageIDs"]),
            "radius": float(branch["radius"]),
            "declaredRestLengthMeters": declared,
            "interiorPassageLengthMeters": bore_length,
            "rigidRouteLengthMeters": rigid_length,
            "segmentModes": segment_modes,
            "contactSegments": [
                {"kind": "exterior-contact", "pointCount": len(entry_contacts)},
                {"kind": "through-bore", "passageID": str(first_record["id"])},
                {"kind": "exterior-contact", "pointCount": len(contact_points)},
                {"kind": "through-bore", "passageID": str(second_record["id"])},
                {"kind": "exterior-contact", "pointCount": len(exit_contacts)},
            ],
        })
    if len(specs) != 2 or len({spec["branchID"] for spec in specs}) != 2:
        raise ValueError("two-branch suspension must expose two distinct branches")
    return specs


def _pose_aware_shoulder_contacts(
    contacts: Sequence[Sequence[float]],
    *,
    anchor: tuple[float, float, float],
    bounds: Mapping[str, object],
    pose: Mapping[str, object],
    is_entry: bool,
) -> list[tuple[float, float, float]]:
    """Let the free cord slide to the anchor-facing rounded end shoulder.

    The first entry (or last exit) guide point is the documented outer
    shoulder.  A static point is valid only for one board orientation; for a
    rotated board the physical cord instead bears at the corresponding point
    on that same rounded shoulder.  The generated arc stays at the existing
    end exterior and is never an implied wood channel.
    """
    # The review contract records the one bounded exterior guide proven by the
    # actual-mesh sweep for every canonical pose. Keeping it as authored route
    # geometry, rather than generating a new arc, preserves Python/Swift
    # parity and prevents an unreviewed wrap heuristic from crossing wood.
    return [_transform_point(point, pose) for point in contacts]


def _line_samples(
    start: tuple[float, float, float], end: tuple[float, float, float], count: int = 9
) -> list[tuple[float, float, float]]:
    if count < 2 or math.dist(start, end) <= 1e-7:
        raise ValueError("directed bore must have a finite non-zero axis")
    return [
        tuple(start[axis] + (end[axis] - start[axis]) * index / (count - 1) for axis in range(3))
        for index in range(count)
    ]


def _attachment_point(bounds: Mapping[str, object]) -> tuple[float, float, float]:
    """Use the reviewed left integral passage, expressed in model metres."""
    minimum = tuple(float(v) for v in bounds["min"])
    maximum = tuple(float(v) for v in bounds["max"])
    return (
        minimum[0] + (maximum[0] - minimum[0]) * (17.0 / 500.0),
        minimum[1] + (maximum[1] - minimum[1]) * (48.0 / 76.0),
        maximum[2],
    )


def _clearance_probes(
    objects: Mapping[str, object],
    descriptor: Mapping[str, object],
    suspension: Mapping[str, object],
    passage_node_ids: Mapping[str, str] | None = None,
) -> dict[str, dict[str, object]]:
    """Check every posed catenary against the reimported mesh triangles.

    The temporary cord is absent from the USDZ.  This verifier builds a BVH
    from each actual imported mesh after applying the same canonical pose used
    by the renderer, then probes fixed subdivisions of every catenary segment.
    Only the exact final endpoint on the declared attachment node receives the
    runtime's integral-passage interface exception.
    """
    if bpy is None:
        raise RuntimeError("mesh clearance probes require Blender")
    from mathutils.bvhtree import BVHTree

    bounds = descriptor["modelBounds"]
    trees: dict[str, object] = {}
    for node_id, item in objects.items():
        vertices = [tuple(item.matrix_world @ vertex.co) for vertex in item.data.vertices]
        polygons = [tuple(polygon.vertices) for polygon in item.data.polygons]
        if not vertices or not polygons:
            raise ValueError(f"actual imported mesh has no triangles: {node_id}")
        trees[node_id] = (vertices, polygons)
    result: dict[str, dict[str, object]] = {}
    resolved_passage_nodes = passage_node_ids or {}
    for position_id in POSITION_HOLD_IDS:
        pose = suspension["canonicalPoses"][position_id]
        posed_trees: dict[str, object] = {}
        for node_id, (vertices, polygons) in trees.items():
            posed_vertices = [_transform_point(vertex, pose) for vertex in vertices]
            posed_trees[node_id] = BVHTree.FromPolygons(
                posed_vertices, polygons, all_triangles=True
            )

        class Query:
            node_ids = tuple(posed_trees)

            def __call__(self, node_id, point):
                nearest = posed_trees[node_id].find_nearest(point)
                if nearest[0] is None or nearest[3] is None:
                    return math.inf, point
                return float(nearest[3]), tuple(nearest[0])

        branch_results: list[dict[str, object]] = []
        for branch in _branch_probe_specs(bounds, suspension, pose, resolved_passage_nodes):
            required = float(branch["radius"]) + CORD_CLEARANCE_METERS
            interface_points = [
                (str(node_id), tuple(point))
                for node_id, point in branch["interfacePoints"]
            ]
            attachment_node_id = interface_points[0][0]
            check = _check_centerline_clearance(
                branch["samples"],
                required_clearance=required,
                attachment_node_id=attachment_node_id,
                interface_points=interface_points,
                segment_modes=branch.get("segmentModes"),
                nearest=Query(),
            )
            if not check["passed"]:
                raise ValueError(
                    f"actual mesh cord clearance probe failed for {position_id} branch {branch['branchID']}: "
                    f"{check['minimumDistanceMeters']:.9f} < {required:.9f}; "
                    f"node={check.get('failedNodeID')} segment={check.get('failedSegmentIndex')} "
                    f"fraction={check.get('failedSegmentFraction')}"
                )
            branch_results.append({
                "branchID": branch["branchID"],
                "passageIDs": branch.get("passageIDs", []),
                "interfacePoints": [
                    {
                        "passageID": passage_id,
                        "nodeID": node_id,
                        "entryPointInModel": list(point),
                    }
                    for passage_id, (node_id, point) in zip(
                        branch.get("passageIDs", []), interface_points
                    )
                ],
                "minimumDistanceMeters": check["minimumDistanceMeters"],
                "requiredClearanceMeters": required,
                "sampleCount": check["sampleCount"],
                "centerlineSampleCount": len(branch["samples"]),
                "centerlineSamples": [list(point) for point in branch["samples"]],
                "segmentSubdivisions": CENTERLINE_SUBDIVISIONS,
                "declaredRestLengthMeters": branch.get("declaredRestLengthMeters"),
                "interiorPassageLengthMeters": branch.get("interiorPassageLengthMeters"),
                "rigidRouteLengthMeters": branch.get("rigidRouteLengthMeters"),
                "contactSegments": branch.get("contactSegments"),
                "passed": True,
            })
        if not branch_results:
            raise ValueError(f"no branch clearance probes generated for {position_id}")
        result[position_id] = {
            "clearanceProbeCount": sum(int(branch["sampleCount"]) for branch in branch_results),
            "clearanceMetersMinimum": min(float(branch["minimumDistanceMeters"]) for branch in branch_results),
            "clearanceRequiredMeters": max(float(branch["requiredClearanceMeters"]) for branch in branch_results),
            "branchClearanceResults": branch_results,
            "allClearanceProbesPassed": True,
            "actualMeshClearance": True,
            "canonicalPoseTested": True,
        }
    return result


def _passage_correspondence(
    suspension: Mapping[str, object],
    bindings: Sequence[object],
    source_correspondence: Mapping[str, str],
    bounds: Mapping[str, object],
) -> tuple[list[dict[str, object]], dict[str, str]]:
    """Resolve declared passage IDs to importer-visible body/attachment nodes."""
    if suspension.get("type") != "twoBranchCord":
        attachment = suspension.get("attachment")
        if not isinstance(attachment, Mapping):
            raise ValueError("single-cord suspension attachment is missing")
        records = [attachment]
    else:
        passages = suspension.get("passages")
        if not isinstance(passages, Mapping):
            raise ValueError("two-branch suspension passages are missing")
        records = [
            passage
            for side in ("left", "right")
            for passage in passages.get(side, ())
        ]
    by_id = {binding.node_id: binding for binding in bindings}
    source_to_imported = {source: imported for imported, source in source_correspondence.items()}
    minimum = tuple(float(value) for value in bounds["min"])
    maximum = tuple(float(value) for value in bounds["max"])
    result: list[dict[str, object]] = []
    passage_nodes: dict[str, str] = {}
    seen_ids: set[str] = set()
    for index, record in enumerate(records):
        if not isinstance(record, Mapping):
            raise ValueError(f"suspension passage {index} is not an object")
        passage_id = str(record.get("id", "attachment"))
        requested_node = record.get("nodeID")
        if not isinstance(requested_node, str) or not requested_node:
            raise ValueError(f"suspension passage {passage_id} has no nodeID")
        imported_node = requested_node if requested_node in by_id else source_to_imported.get(requested_node)
        if imported_node is None:
            raise ValueError(f"suspension passage node is absent from imported bindings: {requested_node}")
        binding = by_id[imported_node]
        if binding.role not in {"body", "attachment"}:
            raise ValueError(f"suspension passage node is selectable: {requested_node}")
        mouth_values: dict[str, list[float]] = {}
        for key in ("entryPointInModel", "exitPointInModel"):
            point = record.get(key)
            if not isinstance(point, Sequence) or isinstance(point, (str, bytes)) or len(point) != 3:
                raise ValueError(f"suspension passage {passage_id} {key} is invalid")
            values = [float(value) for value in point]
            if not all(math.isfinite(value) for value in values):
                raise ValueError(f"suspension passage {passage_id} {key} is non-finite")
            if not all(low <= value <= high for value, low, high in zip(values, minimum, maximum)):
                raise ValueError(f"suspension passage {passage_id} {key} is outside actual descriptor bounds")
            mouth_values[key] = values
        if math.dist(mouth_values["entryPointInModel"], mouth_values["exitPointInModel"]) <= 1e-7:
            raise ValueError(f"suspension passage {passage_id} must be a non-zero directed bore")
        if passage_id in seen_ids:
            raise ValueError(f"duplicate suspension passage ID: {passage_id}")
        seen_ids.add(passage_id)
        passage_nodes[passage_id] = imported_node
        result.append({
            "passageID": passage_id,
            "nodeID": imported_node,
            "sourceNodeID": source_correspondence[imported_node],
            "role": binding.role,
            "entryPointInModel": mouth_values["entryPointInModel"],
            "exitPointInModel": mouth_values["exitPointInModel"],
            "provenance": record.get("provenance"),
        })
    if suspension.get("type") == "twoBranchCord" and len(result) != 4:
        raise ValueError("two-branch suspension must expose exactly four passages")
    return result, passage_nodes


def _passage_ray_probes(
    scene: object,
    depsgraph: object,
    descriptor: Mapping[str, object],
    passages: Sequence[Mapping[str, object]],
) -> list[dict[str, object]]:
    """Prove the cord-sized solid cylinder is clear of every imported triangle.

    Bidirectional rays remain diagnostic evidence; the clipped-triangle solid
    test supplies the conservative aperture proof. No interface exception applies.
    """
    minimum = tuple(float(value) for value in descriptor["modelBounds"]["min"])
    maximum = tuple(float(value) for value in descriptor["modelBounds"]["max"])

    def aperture_ray(origin: tuple[float, float, float], direction: tuple[float, float, float]) -> dict[str, object]:
        hit, location, _, triangle_index, nearest, _ = scene.ray_cast(
            depsgraph, origin, direction, distance=0.2
        )
        nearest_role = _property(nearest, "role") if nearest else None
        return {
            "origin": list(origin),
            "direction": list(direction),
            "hit": bool(hit),
            "nearestRole": nearest_role,
            "nearestNodeID": nearest.name if nearest else None,
            "nearestTriangleIndex": int(triangle_index) if hit else None,
            "location": [float(value) for value in location] if hit else None,
            "passed": not bool(hit),
        }

    results: list[dict[str, object]] = []
    for passage in passages:
        entry = tuple(float(value) for value in passage["entryPointInModel"])
        exit = tuple(float(value) for value in passage["exitPointInModel"])
        if abs(entry[0] - exit[0]) > 1e-7 or abs(entry[1] - exit[1]) > 1e-7:
            raise ValueError("Flash Board physical passages must remain directed along their imported Z axis")
        swept_probe = _swept_passage_probe(
            entry,
            minimum_z=min(entry[2], exit[2]),
            maximum_z=max(entry[2], exit[2]),
            aperture_ray=aperture_ray,
            triangles=[
                [tuple(item.matrix_world @ item.data.vertices[index].co) for index in triangle.vertices]
                for item in scene.objects if item.type == "MESH"
                for triangle in item.data.loop_triangles
            ],
        )
        results.append({
            "passageID": passage["passageID"],
            "nodeID": passage["nodeID"],
            "sourceNodeID": passage["sourceNodeID"],
            "behavior": "through-passage",
            "sweptTubeProbe": swept_probe,
            "passed": swept_probe["passed"],
        })
        if not swept_probe["passed"]:
            raise ValueError(f"actual mesh passage cannot fit the cord tube: {passage['passageID']}")
    return results


def _solid_passage_probe(point, minimum_z, maximum_z, triangles):
    """Exact cylinder test: clip each triangle to the depth slab, then project.

    Projection of a clipped triangle is convex. Its closest point to the axis
    is either inside that polygon or on an edge; no radial sampling is used.
    """
    minimum = math.inf
    count = 0
    for triangle in triangles:
        count += 1
        polygon = [tuple(float(v) for v in vertex) for vertex in triangle]
        if len(polygon) != 3 or any(len(p) != 3 or not all(math.isfinite(v) for v in p) for p in polygon):
            raise ValueError("passage solid probe requires finite triangles")
        for boundary, direction in ((minimum_z, 1), (maximum_z, -1)):
            clipped = []
            for a, b in zip(polygon, polygon[1:] + polygon[:1]):
                a_inside = direction * (a[2] - boundary) >= 0
                b_inside = direction * (b[2] - boundary) >= 0
                if a_inside:
                    clipped.append(a)
                if a_inside != b_inside:
                    t = (boundary - a[2]) / (b[2] - a[2])
                    clipped.append(tuple(a[k] + t * (b[k] - a[k]) for k in range(3)))
            polygon = clipped
        if not polygon:
            continue
        projected = [(p[0] - point[0], p[1] - point[1]) for p in polygon]
        crosses = []
        for a, b in zip(projected, projected[1:] + projected[:1]):
            dx, dy = b[0] - a[0], b[1] - a[1]
            denominator = dx * dx + dy * dy
            t = max(0, min(1, -(a[0] * dx + a[1] * dy) / denominator)) if denominator else 0
            minimum = min(minimum, math.hypot(a[0] + t * dx, a[1] + t * dy))
            crosses.append(a[0] * b[1] - a[1] * b[0])
        # Degenerate projections have no interior; their edges above suffice.
        area = sum(crosses)
        if abs(area) > 1e-20 and (all(c >= 0 for c in crosses) or all(c <= 0 for c in crosses)):
            minimum = 0.0
    return {"method": "clipped-triangle-cylinder", "triangleCount": count,
            "requiredRadiusMeters": PASSAGE_TUBE_RADIUS_METERS,
            "minimumRadiusMeters": minimum if math.isfinite(minimum) else None,
            "passed": count > 0 and minimum >= PASSAGE_TUBE_RADIUS_METERS}


def _swept_passage_probe(
    point: tuple[float, float, float],
    *,
    minimum_z: float,
    maximum_z: float,
    aperture_ray,
    triangles=(),
) -> dict[str, object]:
    """Combine diagnostic full-depth rays with conservative solid-cylinder proof."""
    offsets = _passage_cross_section_offsets(PASSAGE_TUBE_RADIUS_METERS)
    samples: list[dict[str, object]] = []
    for sample_index, (x_offset, y_offset) in enumerate(offsets):
        front_to_rear = aperture_ray(
            (point[0] + x_offset, point[1] + y_offset, maximum_z + 0.02),
            (0.0, 0.0, -1.0),
        )
        rear_to_front = aperture_ray(
            (point[0] + x_offset, point[1] + y_offset, minimum_z - 0.02),
            (0.0, 0.0, 1.0),
        )
        passed = bool(_is_clear_aperture_ray(front_to_rear) and _is_clear_aperture_ray(rear_to_front))
        samples.append({
            "sampleIndex": sample_index,
            "offsetMeters": [x_offset, y_offset],
            "frontToRear": front_to_rear,
            "rearToFront": rear_to_front,
            "passed": passed,
        })
    solid = _solid_passage_probe(point, minimum_z - .02, maximum_z + .02, triangles)
    return {
        "cordRadiusMeters": CORD_RADIUS_METERS,
        "clearanceToleranceMeters": CORD_CLEARANCE_METERS,
        "requiredRadiusMeters": PASSAGE_TUBE_RADIUS_METERS,
        "axis": "model-z",
        "axisContinuouslyTested": True,
        "sampleCount": len(samples),
        "samples": samples,
        "solidTubeProbe": solid,
        "passed": solid["passed"] and all(sample["passed"] for sample in samples),
    }


def verify_package(package: Path, *, skip_renders: bool) -> dict[str, object]:
    """Reimport one compiler package and return actual-export evidence."""
    if not skip_renders:
        raise ValueError("Flash Board export verification currently requires --skip-renders")
    if bpy is None:
        raise RuntimeError("Flash Board export verification must run inside Blender")
    model_path, descriptor_path = package_paths(package)
    expected = frozenset(compiler.load_logical_hold_ids(BOARD_JSON))
    if expected != frozenset(HOLD_IDS) or len(expected) != 7:
        raise ValueError("Flash Board logical inventory changed")
    descriptor = load_json_object(descriptor_path)
    model_bytes = model_path.read_bytes()
    if descriptor.get("modelSHA256") != hashlib.sha256(model_bytes).hexdigest():
        raise ValueError("descriptor hash does not match actual USDZ bytes")
    suspension = load_review_candidate()
    expected_model = suspension["expectedModel"]
    if (
        hashlib.sha256(model_bytes).hexdigest() != expected_model["modelSHA256"]
        or hashlib.sha256(descriptor_path.read_bytes()).hexdigest() != expected_model["descriptorSHA256"]
        or descriptor.get("coordinateFrame") != expected_model["coordinateFrame"]
    ):
        raise ValueError("actual USDZ does not match the hash-bound review candidate")
    with zipfile.ZipFile(model_path) as archive:
        canonical_texture = _verify_canonical_texture_archive(archive)

    bpy.ops.wm.read_factory_settings(use_empty=True)
    for material in list(bpy.data.materials):
        bpy.data.materials.remove(material, do_unlink=True)
    for image in list(bpy.data.images):
        bpy.data.images.remove(image, do_unlink=True)
    if bpy.data.images:
        raise ValueError("source images leaked into the actual-export import")
    imported = bpy.ops.wm.usd_import(filepath=str(model_path), merge_parent_xform=True)
    if "FINISHED" not in imported:
        raise ValueError("USDZ import did not finish")

    scene = bpy.context.scene
    bindings = compiler.validate_tagged_scene(scene, expected, imported=True)
    snapshot = compiler._snapshot_scene(
        scene,
        bindings,
        transform_to_board_frame=True,
        require_imported_materials=True,
        require_triangles=True,
    )
    actual_descriptor = compiler.compile_descriptor(
        model_bytes, snapshot.nodes, snapshot.vertices_by_node_id, expected
    ).to_json()
    if descriptor != actual_descriptor:
        raise ValueError("descriptor does not exactly describe the actual USDZ bytes")

    objects = {item.name: item for item in scene.objects if item.type == "MESH"}
    if set(objects) != {binding.node_id for binding in bindings}:
        raise ValueError("USDZ contains unbound or unexpected mesh geometry")
    # The USD importer exposes Blender-native Z-up coordinates.  Put only the
    # in-memory review scene into the descriptor's board frame before ray and
    # clearance probes; the package bytes remain untouched.
    board_axis = compiler._board_axis_transform()
    for item in objects.values():
        item.matrix_world = board_axis @ item.matrix_world
    bpy.context.view_layer.update()
    forbidden = ("cord", "anchor", "rope", "knot", "nail", "hook", "hardware", "mount")
    for item in objects.values():
        if any(token in item.name.lower() for token in forbidden):
            raise ValueError(f"USDZ contains prohibited baked geometry: {item.name}")
    for item in scene.objects:
        if item.type != "MESH" and item.name.lower().find("cord") >= 0:
            raise ValueError(f"USDZ contains prohibited cord object: {item.name}")

    material_checks = _material_checks(bindings, objects)
    triangles = sum(
        len(polygon.vertices)
        for item in objects.values()
        for polygon in item.data.polygons
    )
    if any(len(polygon.vertices) != 3 for item in objects.values() for polygon in item.data.polygons):
        raise ValueError("actual imported mesh is not explicitly triangulated")
    if triangles >= TRIANGLE_CEILING:
        raise ValueError("actual USDZ exceeds the Flash Board triangle ceiling")

    source_correspondence = compiler._imported_source_node_ids(scene, bindings)
    passage_correspondence, passage_node_ids = _passage_correspondence(
        suspension, bindings, source_correspondence, descriptor["modelBounds"]
    )
    passage_rays = _passage_ray_probes(
        scene, bpy.context.evaluated_depsgraph_get(), descriptor, passage_correspondence
    )
    position_probes = _ray_probes(objects, descriptor)
    clearance = _clearance_probes(objects, descriptor, suspension, passage_node_ids)
    for position_id in POSITION_HOLD_IDS:
        position_probes[position_id].update(clearance[position_id])
    report = {
        "boardID": EXPECTED_BOARD_ID,
        "format": "usdz",
        "modelSHA256": hashlib.sha256(model_bytes).hexdigest(),
        "descriptorSHA256": hashlib.sha256(descriptor_path.read_bytes()).hexdigest(),
        "modelIdentity": expected_model["identity"],
        "coordinateFrame": descriptor["coordinateFrame"],
        "modelBounds": descriptor["modelBounds"],
        "exactDescriptorForActualUSDZ": True,
        "sourceImagesClearedBeforeImport": True,
        "meshCount": len(bindings),
        "holdIDs": sorted(expected),
        "hold_ids_preserved": len(expected),
        "body_mesh_count": sum(binding.role == "body" for binding in bindings),
        "attachment_mesh_count": sum(binding.role == "attachment" for binding in bindings),
        "hardware_mesh_count": 0,
        "baked_cord_mesh_count": 0,
        "baked_anchor_mesh_count": 0,
        "texturedMeshCount": len({record["nodeID"] for record in material_checks}),
        "materialChecks": material_checks,
        "canonicalTexture": canonical_texture,
        "triangles": triangles,
        "triangleCeiling": TRIANGLE_CEILING,
        "explicitTriangles": True,
        "sourcePieceCorrespondence": source_correspondence,
        "candidateID": suspension["candidateID"],
        "suspensionType": "twoBranchCord",
        "logicalBindings": [
            {
                "nodeID": binding.node_id,
                "role": binding.role,
                **({"holdID": binding.hold_id} if binding.hold_id is not None else {}),
                "sourceNodeID": source_correspondence[binding.node_id],
            }
            for binding in bindings
        ],
        "passageCorrespondence": passage_correspondence,
        "passageRayResults": passage_rays,
        "positionProbes": position_probes,
        "rendersSkipped": True,
    }
    return verify_report(report, expected_ids=expected)


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--skip-renders", action="store_true")
    raw = list(argv) if argv is not None else list(sys.argv[sys.argv.index("--") + 1 :]) if "--" in sys.argv else []
    args = parser.parse_args(raw)
    package = args.output.resolve()
    report = verify_package(package, skip_renders=args.skip_renders)
    destination = package.parent / "export-verification.json"
    destination.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print("FLASH_BOARD_EXPORT_VERIFIED", json.dumps({
        key: report[key]
        for key in ("modelSHA256", "descriptorSHA256", "triangles", "hold_ids_preserved", "body_mesh_count", "hardware_mesh_count")
    }, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
