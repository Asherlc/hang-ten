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
ATTACHMENT_SOURCE_NODE_ID = "flash-board-body"
CORD_RADIUS_METERS = 0.002
CORD_CLEARANCE_METERS = 0.001
CANONICAL_TEXTURE_MEMBER = "textures/canonical-neutral-wood.png"
CENTERLINE_SUBDIVISIONS = 8


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
    _validate_passage_correspondence(report)
    if (
        report.get("coordinateFrame") != "hang-ten-board-v1"
        or report.get("exactDescriptorForActualUSDZ") is not True
        or report.get("sourceImagesClearedBeforeImport") is not True
    ):
        raise ValueError("report must prove isolated actual-USDZ verification")
    for hash_key in ("modelSHA256", "descriptorSHA256"):
        hash_value = report.get(hash_key)
        if not isinstance(hash_value, str) or re.fullmatch(r"[0-9a-f]{64}", hash_value) is None:
            raise ValueError(f"report {hash_key} must be a SHA-256 digest")
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
    elif report.get("suspensionType") != "twoBranchCord":
        raise ValueError("report must identify the actual attachment node")

    probes = report.get("positionProbes")
    if not isinstance(probes, Mapping) or set(probes) != set(POSITION_HOLD_IDS):
        raise ValueError("position ray/clearance probes must cover all four positions")
    for position_id, expected_hold_ids in POSITION_HOLD_IDS.items():
        result = probes[position_id]
        if not isinstance(result, Mapping):
            raise ValueError(f"position probe is not an object: {position_id}")
        if result.get("expectedHoldIDs") != list(expected_hold_ids):
            raise ValueError(f"position probe hold inventory changed: {position_id}")
        ligaments = result.get("ligamentResults")
        if not isinstance(ligaments, list) or not ligaments:
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
        if not isinstance(rays, list) or len(rays) != len(expected_hold_ids):
            raise ValueError(f"surface ray results are incomplete: {position_id}")
        if [item.get("expectedID") for item in rays if isinstance(item, Mapping)] != list(expected_hold_ids):
            raise ValueError(f"surface ray hold order changed: {position_id}")
        if not all(
            isinstance(item, Mapping)
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
        if result.get("allClearanceProbesPassed") is not True or result.get("actualMeshClearance") is not True:
            raise ValueError(f"clearance probes failed for position {position_id}")
        if _integer(result, "rayProbeCount") != len(expected_hold_ids):
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


def _validate_passage_correspondence(report: Mapping[str, object]) -> None:
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
    for passage in passages:
        if not isinstance(passage, Mapping):
            raise ValueError("passage correspondence must be an object")
        passage_id = passage.get("passageID")
        node_id = passage.get("nodeID")
        source_node_id = passage.get("sourceNodeID")
        role = passage.get("role")
        point = passage.get("pointInModel")
        if (
            not isinstance(passage_id, str)
            or not passage_id
            or passage_id in passage_ids
            or not isinstance(node_id, str)
            or not node_id
            or not isinstance(source_node_id, str)
            or not source_node_id
            or role not in {"body", "attachment"}
            or not isinstance(point, list)
            or len(point) != 3
            or not all(isinstance(coordinate, (int, float)) and math.isfinite(coordinate) for coordinate in point)
        ):
            raise ValueError("passage correspondence is incomplete or duplicated")
        binding = by_node.get(node_id)
        if binding is None or binding.get("role") != role:
            raise ValueError("passage correspondence must target a body or attachment binding")
        passage_ids.append(passage_id)


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
) -> dict[str, object]:
    """Apply the runtime segment/tube clearance rule to a nearest-mesh query."""
    if len(samples) < 2:
        raise ValueError("suspension catenary must contain at least two samples")
    minimum = math.inf
    checked = 0
    node_ids = tuple(getattr(nearest, "node_ids", (attachment_node_id,)))
    for segment_index, (start, end) in enumerate(zip(samples, samples[1:])):
        for subdivision in range(CENTERLINE_SUBDIVISIONS + 1):
            fraction = subdivision / CENTERLINE_SUBDIVISIONS
            point = tuple(start[axis] + (end[axis] - start[axis]) * fraction for axis in range(3))
            for node_id in node_ids:
                distance, nearest_point = nearest(node_id, point)
                minimum = min(minimum, distance)
                checked += 1
                if distance >= required_clearance:
                    continue
                interface = (
                    any(
                        interface_node == node_id
                        and math.dist(point, interface_point) <= 1e-5
                        for interface_node, interface_point in interface_points
                    )
                    if interface_points
                    else node_id == attachment_node_id
                    and segment_index == len(samples) - 2
                    and fraction >= 1 - 1e-5
                    and math.dist(nearest_point, samples[-1]) <= 1e-5
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
            center = holds[hold_id]["center"]
            origin = (
                minimum[0] + (maximum[0] - minimum[0]) * float(center[0]),
                minimum[1] + (maximum[1] - minimum[1]) * float(center[1]),
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
                    f"ray probe missed {hold_id} for {position_id}; nearest={nearest_hold_id}"
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
    x_samples: list[tuple[str, float, float]] = [
        ("exterior-left", 0.02, 0.5),
        ("exterior-right", 0.98, 0.5),
    ]
    intervals = []
    for left_id, right_id in zip(expected_hold_ids, expected_hold_ids[1:]):
        left = descriptor["holds"][left_id]["facePlaneAABB"]
        right = descriptor["holds"][right_id]["facePlaneAABB"]
        gap_min = max(float(left["max"][0]), float(right["min"][0]))
        gap_max = min(float(right["max"][0]), float(left["min"][0]))
        if gap_min >= gap_max:
            left_max = float(left["max"][0])
            right_min = float(right["min"][0])
            if right_min - left_max > 0.005:
                y_min = max(float(left["min"][1]), float(right["min"][1]))
                y_max = min(float(left["max"][1]), float(right["max"][1]))
                intervals.append((left_max + right_min) / 2, (y_min + y_max) / 2 if y_min < y_max else 0.5)
    x_samples.extend(
        (f"inter-pocket-{index}", x, y)
        for index, (x, y) in enumerate(intervals)
    )
    results: list[dict[str, object]] = []
    for probe_id, normalized_x, normalized_y in x_samples:
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
            "probeID": probe_id,
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
            raise ValueError(f"ligament ray missed body at {probe_id}")
    return results


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
        first = _transform_point(first_record["pointInModel"], pose)
        second = _transform_point(second_record["pointInModel"], pose)
        interior = math.dist(first, second)
        first_distance = math.dist(anchor, first)
        second_distance = math.dist(anchor, second)
        declared = float(branch["restLength"])
        minimum_route = first_distance + interior + second_distance
        if declared < minimum_route - 1e-5:
            raise ValueError(f"branch {branch['id']} is shorter than its posed route")
        free_length = declared - interior
        endpoint_sum = first_distance + second_distance
        if endpoint_sum <= 1e-7 or free_length < endpoint_sum - 1e-5:
            raise ValueError(f"branch {branch['id']} has no valid free span")
        first_free = free_length * (first_distance / endpoint_sum)
        second_free = free_length - first_free
        first_span = _catenary_samples(anchor, first, first_free)
        second_span = list(reversed(_catenary_samples(anchor, second, second_free)))
        samples = first_span + [second] + second_span[1:]
        specs.append({
            "branchID": str(branch["id"]),
            "samples": samples,
            "interfacePoints": [
                (passage_node_ids[str(first_record["id"])], first),
                (passage_node_ids[str(second_record["id"])], second),
            ],
            "passageIDs": list(branch["passageIDs"]),
            "radius": float(branch["radius"]),
            "declaredRestLengthMeters": declared,
            "interiorPassageLengthMeters": interior,
        })
    if len(specs) != 2 or len({spec["branchID"] for spec in specs}) != 2:
        raise ValueError("two-branch suspension must expose two distinct branches")
    return specs


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
                "minimumDistanceMeters": check["minimumDistanceMeters"],
                "requiredClearanceMeters": required,
                "sampleCount": check["sampleCount"],
                "centerlineSampleCount": len(branch["samples"]),
                "centerlineSamples": [list(point) for point in branch["samples"]],
                "segmentSubdivisions": CENTERLINE_SUBDIVISIONS,
                "declaredRestLengthMeters": branch.get("declaredRestLengthMeters"),
                "interiorPassageLengthMeters": branch.get("interiorPassageLengthMeters"),
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
        point = record.get("pointInModel")
        if not isinstance(point, Sequence) or isinstance(point, (str, bytes)) or len(point) != 3:
            raise ValueError(f"suspension passage {passage_id} point is invalid")
        point_values = [float(value) for value in point]
        if not all(math.isfinite(value) for value in point_values):
            raise ValueError(f"suspension passage {passage_id} point is non-finite")
        if not all(low <= value <= high for value, low, high in zip(point_values, minimum, maximum)):
            raise ValueError(f"suspension passage {passage_id} point is outside actual descriptor bounds")
        if passage_id in seen_ids:
            raise ValueError(f"duplicate suspension passage ID: {passage_id}")
        seen_ids.add(passage_id)
        passage_nodes[passage_id] = imported_node
        result.append({
            "passageID": passage_id,
            "nodeID": imported_node,
            "sourceNodeID": source_correspondence[imported_node],
            "role": binding.role,
            "pointInModel": point_values,
            "provenance": record.get("provenance"),
        })
    if suspension.get("type") == "twoBranchCord" and len(result) != 4:
        raise ValueError("two-branch suspension must expose exactly four passages")
    return result, passage_nodes


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
    board_document = load_json_object(BOARD_JSON)
    suspension = board_document["presentations"][0]["media"]["suspension"]
    if not isinstance(suspension, Mapping):
        raise ValueError("Flash Board package suspension metadata is missing")
    passage_correspondence, passage_node_ids = _passage_correspondence(
        suspension, bindings, source_correspondence, descriptor["modelBounds"]
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
        "suspensionType": suspension.get("type"),
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
