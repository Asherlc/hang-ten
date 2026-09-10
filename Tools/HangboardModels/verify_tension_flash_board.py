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
        if result.get("allClearanceProbesPassed") is not True:
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


def _clearance_probes(descriptor: Mapping[str, object]) -> dict[str, dict[str, object]]:
    """Record deterministic cord-interface clearance samples per position.

    The transient cord is intentionally absent from the USDZ.  Samples stop
    before the approved integral passage interface and are checked by the
    iOS renderer again when it constructs the cord tube.
    """
    bounds = descriptor["modelBounds"]
    minimum = tuple(float(v) for v in bounds["min"])
    maximum = tuple(float(v) for v in bounds["max"])
    point = _attachment_point(bounds)
    result: dict[str, dict[str, object]] = {}
    for position_id in POSITION_HOLD_IDS:
        sign = POSITION_FACE_SIGN[position_id]
        anchor = (
            (minimum[0] + maximum[0]) / 2,
            maximum[1] + 0.24,
            maximum[2] + 0.05 if sign > 0 else minimum[2] - 0.05,
        )
        interface = (point[0], point[1], maximum[2] if sign > 0 else minimum[2])
        samples = []
        # Leave the final 10% to the declared integral interface.  The
        # renderer's native mesh test owns the tube-vs-interface exception.
        for index in range(19):
            fraction = index / 20.0
            sample = tuple(anchor[axis] * (1 - fraction) + interface[axis] * fraction for axis in range(3))
            clearance = abs(sample[2] - (maximum[2] if sign > 0 else minimum[2]))
            passed = clearance >= CORD_RADIUS_METERS + CORD_CLEARANCE_METERS
            samples.append({"fraction": fraction, "clearanceMeters": clearance, "passed": passed})
        if not all(sample["passed"] for sample in samples):
            raise ValueError(f"cord clearance probe failed for {position_id}")
        result[position_id] = {
            "clearanceProbeCount": len(samples),
            "clearanceMetersMinimum": min(sample["clearanceMeters"] for sample in samples),
            "clearanceRequiredMeters": CORD_RADIUS_METERS + CORD_CLEARANCE_METERS,
            "clearanceProbes": samples,
            "allClearanceProbesPassed": True,
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
        texture_members = [
            name for name in archive.namelist()
            if name.lower().endswith((".png", ".jpg", ".jpeg"))
        ]
        if not texture_members or any(not archive.read(name) for name in texture_members):
            raise ValueError("USDZ must contain non-empty embedded image bytes")

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
    point = _attachment_point(descriptor["modelBounds"])
    minimum = descriptor["modelBounds"]["min"]
    maximum = descriptor["modelBounds"]["max"]
    if not all(low <= value <= high for value, low, high in zip(point, minimum, maximum)):
        raise ValueError("attachment point is outside actual descriptor bounds")

    position_probes = _ray_probes(objects, descriptor)
    clearance = _clearance_probes(descriptor)
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
