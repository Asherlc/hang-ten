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
    if not isinstance(hold_ids, list) or set(hold_ids) != set(expected_ids):
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
    if not isinstance(attachment, Mapping):
        raise ValueError("report must identify the actual attachment node")
    if not isinstance(attachment.get("nodeID"), str) or not attachment["nodeID"]:
        raise ValueError("attachment node must identify the imported body node")
    if attachment.get("sourceNodeID") != ATTACHMENT_SOURCE_NODE_ID:
        raise ValueError("attachment source node must be the reviewed body node")
    if attachment.get("role") not in {"body", "attachment"}:
        raise ValueError("attachment node must be body or attachment role")
    if attachment.get("accessible") is not True:
        raise ValueError("attachment node and point must be importer-accessible")

    probes = report.get("positionProbes")
    if not isinstance(probes, Mapping) or set(probes) != set(POSITION_HOLD_IDS):
        raise ValueError("position ray/clearance probes must cover all four positions")
    for position_id, expected_hold_ids in POSITION_HOLD_IDS.items():
        result = probes[position_id]
        if not isinstance(result, Mapping):
            raise ValueError(f"position probe is not an object: {position_id}")
        if result.get("expectedHoldIDs") != list(expected_hold_ids):
            raise ValueError(f"position probe hold inventory changed: {position_id}")
        if result.get("allRayProbesPassed") is not True:
            raise ValueError(f"ray probes failed for position {position_id}")
        if result.get("allClearanceProbesPassed") is not True or result.get("actualMeshClearance") is not True:
            raise ValueError(f"clearance probes failed for position {position_id}")
        if _integer(result, "rayProbeCount") != len(expected_hold_ids):
            raise ValueError(f"ray probe count is incomplete: {position_id}")
        if _integer(result, "clearanceProbeCount") <= 0:
            raise ValueError(f"clearance probe count is empty: {position_id}")
    return dict(report)


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
    minimum = tuple(float(value) for value in bounds["min"])
    maximum = tuple(float(value) for value in bounds["max"])
    offset = tuple(float(value) for value in suspension["anchor"]["offsetFromBoardBounds"])
    anchor = (
        (minimum[0] + maximum[0]) / 2 + offset[0],
        maximum[1] + offset[1],
        (minimum[2] + maximum[2]) / 2 + offset[2],
    )
    attachment = _transform_point(suspension["attachment"]["pointInModel"], pose)
    rest_length = float(suspension["cord"]["restLength"])
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
) -> dict[str, object]:
    """Apply the runtime segment/tube clearance rule to a nearest-mesh query."""
    if len(samples) < 2:
        raise ValueError("suspension catenary must contain at least two samples")
    minimum = math.inf
    checked = 0
    last_segment = len(samples) - 2
    endpoint = samples[-1]
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
                    node_id == attachment_node_id
                    and segment_index == last_segment
                    and fraction >= 1 - 1e-5
                    and math.dist(nearest_point, endpoint) <= 1e-5
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
            hit, location, _, _, nearest, _ = scene.ray_cast(
                depsgraph, origin, direction, distance=0.2
            )
            nearest_hold_id = _property(nearest, "hold_id") if nearest else None
            passed = bool(hit and nearest_hold_id == hold_id)
            probes.append(
                {
                    "expectedID": hold_id,
                    "nearestID": nearest_hold_id,
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
            "rayProbes": probes,
            "allRayProbesPassed": True,
        }
    return result


def _attachment_point(bounds: Mapping[str, object]) -> tuple[float, float, float]:
    """Use the reviewed left integral passage, expressed in model metres."""
    minimum = tuple(float(v) for v in bounds["min"])
    maximum = tuple(float(v) for v in bounds["max"])
    return (
        minimum[0] + (maximum[0] - minimum[0]) * (17.0 / 500.0),
        minimum[1] + (maximum[1] - minimum[1]) * (48.0 / 76.0),
        maximum[2],
    )


def validate_attachment_point(
    attachment: Mapping[str, object], bounds: Mapping[str, object]
) -> tuple[float, float, float]:
    """Match the package endpoint to the approved integral-passage estimate."""
    declared = attachment.get("pointInModel")
    try:
        valid = isinstance(declared, (list, tuple)) and len(declared) == 3 and all(
            type(value) in (int, float) and math.isfinite(value) for value in declared
        )
    except OverflowError:
        valid = False
    if not valid:
        raise ValueError("attachment point must be a finite three-component vector")
    expected = _attachment_point(bounds)
    minimum, maximum = bounds["min"], bounds["max"]
    if not all(
        low <= actual <= high and low <= approved <= high
        for actual, approved, low, high in zip(declared, expected, minimum, maximum)
    ):
        raise ValueError("attachment point is outside actual descriptor bounds")
    if any(abs(actual - approved) > 1e-6 for actual, approved in zip(declared, expected)):
        raise ValueError("attachment point does not match the approved integral passage")
    return expected


def _clearance_probes(
    objects: Mapping[str, object],
    descriptor: Mapping[str, object],
    suspension: Mapping[str, object],
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
    required = float(suspension["cord"]["radius"]) + CORD_CLEARANCE_METERS
    attachment_node_id = str(suspension["attachment"]["nodeID"])
    for position_id in POSITION_HOLD_IDS:
        pose = suspension["canonicalPoses"][position_id]
        samples = _suspension_samples(bounds, suspension, pose)
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

        check = _check_centerline_clearance(
            samples,
            required_clearance=required,
            attachment_node_id=attachment_node_id,
            nearest=Query(),
        )
        if not check["passed"]:
            raise ValueError(
                f"actual mesh cord clearance probe failed for {position_id}: "
                f"{check['minimumDistanceMeters']:.9f} < {required:.9f}; "
                f"node={check.get('failedNodeID')} segment={check.get('failedSegmentIndex')} "
                f"fraction={check.get('failedSegmentFraction')}"
            )
        result[position_id] = {
            "clearanceProbeCount": check["sampleCount"],
            "clearanceMetersMinimum": check["minimumDistanceMeters"],
            "clearanceRequiredMeters": required,
            "clearanceProbes": {"centerlineSamples": len(samples), "segmentSubdivisions": CENTERLINE_SUBDIVISIONS},
            "allClearanceProbesPassed": True,
            "actualMeshClearance": True,
            "canonicalPoseTested": True,
            "transformedAttachment": list(samples[-1]),
        }
    return result


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
    body_binding = next(binding for binding in bindings if binding.role == "body")
    attachment = {
        "nodeID": body_binding.node_id,
        "role": body_binding.role,
        "sourceNodeID": source_correspondence[body_binding.node_id],
    }
    validate_attachment_node(attachment, bindings)
    position_probes = _ray_probes(objects, descriptor)
    board_document = load_json_object(BOARD_JSON)
    suspension = board_document["presentations"][0]["media"]["suspension"]
    if not isinstance(suspension, Mapping):
        raise ValueError("Flash Board package suspension metadata is missing")
    point = validate_attachment_point(suspension["attachment"], descriptor["modelBounds"])
    clearance = _clearance_probes(objects, descriptor, suspension)
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
        "attachment": {
            "nodeID": body_binding.node_id,
            "role": body_binding.role,
            "sourceNodeID": source_correspondence[body_binding.node_id],
            "pointInModel": list(point),
            "accessible": True,
            "provenance": "estimatedFromApprovedModel; integral cord passage on body",
        },
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
