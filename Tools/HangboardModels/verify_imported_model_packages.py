#!/usr/bin/env python3
"""Reimport a converted USDZ and verify its generated descriptor and mapping."""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import sys
from collections.abc import Mapping, Sequence
from pathlib import Path

_TOOLS = Path(__file__).resolve().parent
if str(_TOOLS) not in sys.path:
    sys.path.insert(0, str(_TOOLS))

from import_model_package import validate_mapping, write_json
from model_descriptor import ModelDescriptorV1, compile_descriptor


def mesh_node_ids(object_types: Mapping[str, str]) -> set[str]:
    return {node_id for node_id, object_type in object_types.items() if object_type == "MESH"}


def report_node_pairs(imported_to_source: Mapping[str, str]) -> list[tuple[str, str]]:
    return [(node_id, imported_to_source[node_id]) for node_id in sorted(imported_to_source)]


def require_source_correspondence(
    imported_to_source: Mapping[str, str], expected_source_ids: set[str]
) -> None:
    if set(imported_to_source.values()) != expected_source_ids:
        raise ValueError("actual USDZ source mesh IDs do not match explicit mapping")
    if len(imported_to_source) != len(set(imported_to_source.values())):
        raise ValueError("actual USDZ duplicates source mesh IDs")


def validate_report_document(report: Mapping[str, object]) -> None:
    if report.get("status") != "verified":
        raise ValueError("verification report status must be verified")
    if report.get("cleanReimport") is not True:
        raise ValueError("verification must use a clean reimport")
    if report.get("descriptorMatchesActualUSDZ") is not True:
        raise ValueError("descriptor must match actual USDZ")
    meshes = report.get("meshes")
    if not isinstance(meshes, list) or not meshes:
        raise ValueError("verification report requires meshes")
    for mesh in meshes:
        if not isinstance(mesh, Mapping):
            raise ValueError("mesh report must be an object")
        triangles = mesh.get("triangles")
        if not isinstance(triangles, int) or isinstance(triangles, bool) or triangles <= 0:
            raise ValueError(f"mesh must have positive triangles: {mesh.get('nodeID')}")
        materials = mesh.get("materials")
        if not isinstance(materials, list) or not materials:
            raise ValueError(f"mesh requires native material payload: {mesh.get('nodeID')}")


def _load_object(path: Path, label: str) -> Mapping[str, object]:
    try:
        value = json.loads(Path(path).read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        raise ValueError(f"{label} is not readable valid JSON: {path}") from error
    if not isinstance(value, Mapping):
        raise ValueError(f"{label} must be an object")
    return value


def verify_package(package_directory: Path, mapping_path: Path) -> Mapping[str, object]:
    try:
        import bpy
    except ImportError as error:
        raise RuntimeError("USDZ verification must run inside Blender") from error
    import compile_model_package as compiler

    package = Path(package_directory).resolve()
    files = {
        path.relative_to(package).as_posix()
        for path in package.rglob("*")
        if path.is_file()
    }
    expected_files = {"assets/primary.usdz", "assets/primary.model.json"}
    if files != expected_files:
        raise ValueError(f"converted package inventory mismatch: {sorted(files)}")
    model_path = package / "assets/primary.usdz"
    descriptor_value = _load_object(package / "assets/primary.model.json", "descriptor")
    descriptor = ModelDescriptorV1.from_json(descriptor_value)
    model_bytes = model_path.read_bytes()
    if hashlib.sha256(model_bytes).hexdigest() != descriptor.model_sha256:
        raise ValueError("descriptor model hash does not match actual USDZ")
    mapping = _load_object(mapping_path, "mapping")

    bpy.ops.wm.read_factory_settings(use_empty=True)
    clean_before = not bpy.context.scene.objects and not bpy.data.materials and not bpy.data.images
    if not clean_before:
        raise ValueError("source images/materials were present before USDZ reimport")
    scene = compiler._import_usdz_into_empty_scene(model_path)
    object_types = {item.name: item.type for item in scene.objects}
    expected_objects = {
        str(item["sourceNodeID"]): "MESH"
        for item in mapping.get("objects", [])
        if isinstance(item, Mapping) and item.get("role") in {"body", "hold"}
    }
    validation_objects = dict(expected_objects)
    for item in mapping.get("objects", []):
        if isinstance(item, Mapping) and item.get("role") == "attachment":
            validation_objects[str(item["sourceNodeID"])] = "EMPTY"
    validated_mapping = validate_mapping(mapping, validation_objects)
    nodes = compiler.validate_tagged_scene(scene, validated_mapping.logical_hold_ids, imported=True)
    correspondence = compiler._imported_source_node_ids(scene, nodes)
    require_source_correspondence(correspondence, set(expected_objects))
    if mesh_node_ids(object_types) != set(correspondence):
        raise ValueError("actual USDZ contains unbound importer-visible mesh IDs")
    snapshot = compiler._snapshot_scene(
        scene,
        nodes,
        transform_to_board_frame=True,
        require_imported_materials=True,
        require_triangles=True,
    )
    rebuilt = compile_descriptor(
        model_bytes,
        snapshot.nodes,
        snapshot.vertices_by_node_id,
        validated_mapping.logical_hold_ids,
    )
    if rebuilt.to_json() != descriptor_value:
        raise ValueError("descriptor hashes/bounds/centers do not match actual USDZ")

    meshes: list[dict[str, object]] = []
    by_name = {item.name: item for item in scene.objects}
    roles = {node.node_id: node.role for node in nodes}
    holds = {node.node_id: node.hold_id for node in nodes}
    for node_id, source_node_id in report_node_pairs(correspondence):
        item = by_name[node_id]
        mesh = item.data
        triangle_count = sum(max(0, len(polygon.vertices) - 2) for polygon in mesh.polygons)
        used_materials = sorted(
            {
                mesh.materials[polygon.material_index].name
                for polygon in mesh.polygons
                if polygon.material_index < len(mesh.materials)
                and mesh.materials[polygon.material_index] is not None
            }
        )
        meshes.append(
            {
                "holdID": holds[node_id],
                "materials": used_materials,
                "nodeID": node_id,
                "role": roles[node_id],
                "sourceNodeID": source_node_id,
                "triangles": triangle_count,
            }
        )
    report: dict[str, object] = {
        "attachmentNodeIDs": list(validated_mapping.attachment_node_ids),
        "cleanReimport": clean_before,
        "coordinateFrame": descriptor_value["coordinateFrame"],
        "descriptorMatchesActualUSDZ": True,
        "descriptorSHA256": hashlib.sha256(
            (package / "assets/primary.model.json").read_bytes()
        ).hexdigest(),
        "holdCount": len(descriptor.holds),
        "holds": descriptor_value["holds"],
        "meshes": meshes,
        "modelBounds": descriptor_value["modelBounds"],
        "modelSHA256": descriptor.model_sha256,
        "status": "verified",
    }
    validate_report_document(report)
    return report


def _arguments(argv: Sequence[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--package-directory", type=Path, required=True)
    parser.add_argument("--mapping", type=Path, required=True)
    parser.add_argument("--report", type=Path, required=True)
    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> int:
    raw = (
        list(sys.argv[sys.argv.index("--") + 1 :])
        if argv is None and "--" in sys.argv
        else list(sys.argv[1:] if argv is None else argv)
    )
    arguments = _arguments(raw)
    write_json(arguments.report, verify_package(arguments.package_directory, arguments.mapping))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
