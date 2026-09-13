#!/usr/bin/env python3
"""Verify the actual exported YY Baguette Evo contact-first package.

The verifier starts from an empty Blender scene, imports the package USDZ,
and rebuilds its descriptor from importer-visible triangles.  It also proves
the retained source-object correspondence and attachment evidence survived
the export.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from collections.abc import Mapping, Sequence
from pathlib import Path

_TOOLS = Path(__file__).resolve().parent
if str(_TOOLS) not in sys.path:
    sys.path.insert(0, str(_TOOLS))

from contact_model_descriptor import ModelDescriptorV1, compile_descriptor
from import_contact_model_source import validate_mapping, write_json


EXPECTED_CONTACT_IDS = (
    "edge-20-left",
    "edge-10-left",
    "edge-25-left",
    "edge-15-left",
    "edge-15-right",
    "edge-25-right",
    "edge-10-right",
    "edge-20-right",
    "edge-12-left",
    "edge-12-right",
    "edge-8-left",
    "edge-8-right",
    "edge-6-upper",
    "edge-6-lower",
    "edge-central-30",
    "edge-central-25",
    "edge-central-20",
    "edge-central-6",
    "rounded-tray",
)

EXPECTED_SOURCE_MESH_IDS = (
    "body",
    "hold-central-06mm",
    "hold-central-20mm",
    "hold-central-25mm",
    "hold-central-30mm",
    "hold-edge-06mm-left",
    "hold-edge-06mm-right",
    "hold-edge-08mm-left",
    "hold-edge-08mm-right",
    "hold-edge-10mm-left",
    "hold-edge-10mm-right",
    "hold-edge-12mm-left",
    "hold-edge-12mm-right",
    "hold-edge-15mm-left",
    "hold-edge-15mm-right",
    "hold-edge-20mm-left",
    "hold-edge-20mm-right",
    "hold-edge-25mm-left",
    "hold-edge-25mm-right",
    "hold-rounded-left",
    "hold-rounded-right",
)


def _load_object(path: Path, label: str) -> Mapping[str, object]:
    try:
        value = json.loads(Path(path).read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        raise ValueError(f"{label} is not readable valid JSON: {path}") from error
    if not isinstance(value, Mapping):
        raise ValueError(f"{label} must be an object")
    return value


def require_source_correspondence(imported_to_source: Mapping[str, str]) -> None:
    """Require a one-to-one import mapping for every authorized source mesh."""
    expected = set(EXPECTED_SOURCE_MESH_IDS)
    if set(imported_to_source.values()) != expected:
        raise ValueError("actual USDZ source mesh IDs do not match the source mesh inventory")
    if len(imported_to_source) != len(set(imported_to_source.values())):
        raise ValueError("actual USDZ duplicates a source mesh ID")


def _attachment_facts(mapping: Mapping[str, object]) -> list[Mapping[str, object]]:
    facts: list[Mapping[str, object]] = []
    objects = mapping.get("objects")
    if not isinstance(objects, list):
        raise ValueError("mapping objects must be an array")
    for item in objects:
        if isinstance(item, Mapping) and item.get("role") == "attachment":
            facts.append(
                {
                    "sourceNodeID": item.get("sourceNodeID"),
                    "order": item.get("order"),
                    "position": item.get("position"),
                    "metadata": item.get("metadata"),
                }
            )
    return sorted(facts, key=lambda item: int(item["order"]))


def _verify_attachment_payload(
    payload: object, expected: Sequence[Mapping[str, object]]
) -> list[Mapping[str, object]]:
    if not isinstance(payload, str):
        raise ValueError("actual USDZ is missing exported attachment facts")
    try:
        actual = json.loads(payload)
    except json.JSONDecodeError as error:
        raise ValueError("actual USDZ attachment facts are invalid JSON") from error
    wanted = json.loads(json.dumps(list(expected), sort_keys=True, allow_nan=False))
    if actual != wanted:
        raise ValueError("actual USDZ attachment facts do not match explicit mapping")
    return actual


def validate_report_document(report: Mapping[str, object]) -> None:
    """Validate the current contact-first report contract without Blender."""
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
        role = mesh.get("role")
        if role not in {"body", "contact", "attachment"}:
            raise ValueError(f"mesh role is not current: {role}")
        if "holdID" in mesh:
            raise ValueError("legacy holdID is not permitted in a current report")
        contact_id = mesh.get("contactID")
        if role == "contact":
            if not isinstance(contact_id, str) or not contact_id:
                raise ValueError("contact mesh requires contactID")
        elif contact_id is not None:
            raise ValueError(f"{role} mesh may not declare contactID")
        triangles = mesh.get("triangles")
        if not isinstance(triangles, int) or isinstance(triangles, bool) or triangles <= 0:
            raise ValueError(f"mesh must have positive triangles: {mesh.get('nodeID')}")
        materials = mesh.get("materials")
        if not isinstance(materials, list) or not materials:
            raise ValueError(f"mesh requires native material payload: {mesh.get('nodeID')}")


def verify_package(package_directory: Path, mapping_path: Path) -> Mapping[str, object]:
    try:
        import bpy
    except ImportError as error:
        raise RuntimeError("USDZ verification must run inside Blender") from error
    import contact_model_package as compiler

    package = Path(package_directory).resolve()
    files = {
        path.relative_to(package).as_posix()
        for path in package.rglob("*")
        if path.is_file()
    }
    package_only = {"assets/primary.usdz", "assets/primary.model.json"}
    final_package = package_only | {"board.json"}
    if files not in {frozenset(package_only), frozenset(final_package)}:
        raise ValueError(f"model-only package inventory mismatch: {sorted(files)}")

    model_path = package / "assets/primary.usdz"
    descriptor_path = package / "assets/primary.model.json"
    descriptor_value = _load_object(descriptor_path, "descriptor")
    descriptor = ModelDescriptorV1.from_json(descriptor_value)
    model_bytes = model_path.read_bytes()
    if hashlib.sha256(model_bytes).hexdigest() != descriptor.model_sha256:
        raise ValueError("descriptor model hash does not match actual USDZ")
    if tuple(descriptor.contacts) != tuple(sorted(EXPECTED_CONTACT_IDS)):
        raise ValueError("descriptor contacts do not match expected inventory")

    mapping = _load_object(mapping_path, "mapping")
    objects = mapping.get("objects")
    if not isinstance(objects, list):
        raise ValueError("mapping objects must be an array")
    source_types = {
        str(item.get("sourceNodeID")): (
            "EMPTY" if item.get("role") == "attachment" else "MESH"
        )
        for item in objects
        if isinstance(item, Mapping)
    }
    validated = validate_mapping(mapping, source_types)
    if validated.logical_contact_order != EXPECTED_CONTACT_IDS:
        raise ValueError("mapping contact order does not match expected inventory")

    bpy.ops.wm.read_factory_settings(use_empty=True)
    clean_before = not bpy.context.scene.objects and not bpy.data.materials and not bpy.data.images
    if not clean_before:
        raise ValueError("source images/materials were present before USDZ reimport")
    scene = compiler._import_usdz_into_empty_scene(model_path)
    nodes = compiler.validate_tagged_scene(
        scene, frozenset(EXPECTED_CONTACT_IDS), imported=True
    )
    correspondence = compiler._imported_source_node_ids(scene, nodes)
    require_source_correspondence(correspondence)
    importer_mesh_ids = {item.name for item in scene.objects if item.type == "MESH"}
    if importer_mesh_ids != set(correspondence):
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
        frozenset(EXPECTED_CONTACT_IDS),
    )
    if rebuilt.to_json() != descriptor_value:
        raise ValueError("descriptor hashes/bounds/centers do not match actual USDZ")

    bodies = [node.node_id for node in nodes if node.role == "body"]
    if not bodies:
        raise ValueError("actual USDZ has no body mesh")
    by_name = {item.name: item for item in scene.objects}
    body = by_name[bodies[0]]
    payload = compiler._object_property(body, "hang_ten_attachments_v1", imported=True)
    if payload is None:
        payload = compiler._object_property(
            body.data, "hang_ten_attachments_v1", imported=True
        )
    attachments = _verify_attachment_payload(payload, _attachment_facts(mapping))

    bindings = {node.node_id: node for node in nodes}
    meshes: list[dict[str, object]] = []
    for node_id in sorted(correspondence):
        item = by_name[node_id]
        mesh = item.data
        materials = sorted(
            {
                mesh.materials[polygon.material_index].name
                for polygon in mesh.polygons
                if polygon.material_index < len(mesh.materials)
                and mesh.materials[polygon.material_index] is not None
            }
        )
        binding = bindings[node_id]
        meshes.append(
            {
                "nodeID": node_id,
                "sourceNodeID": correspondence[node_id],
                "role": binding.role,
                "contactID": binding.contact_id,
                "triangles": sum(
                    max(0, len(polygon.vertices) - 2) for polygon in mesh.polygons
                ),
                "materials": materials,
            }
        )

    report: dict[str, object] = {
        "status": "verified",
        "cleanReimport": clean_before,
        "descriptorMatchesActualUSDZ": True,
        "coordinateFrame": descriptor_value["coordinateFrame"],
        "modelSHA256": descriptor.model_sha256,
        "descriptorSHA256": hashlib.sha256(descriptor_path.read_bytes()).hexdigest(),
        "modelBounds": descriptor_value["modelBounds"],
        "contactCount": len(descriptor.contacts),
        "contacts": descriptor_value["contacts"],
        "attachments": attachments,
        "attachmentNodeIDs": [item["sourceNodeID"] for item in attachments],
        "sourceCorrespondence": dict(sorted(correspondence.items())),
        "meshes": meshes,
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
    write_json(
        arguments.report,
        verify_package(arguments.package_directory, arguments.mapping),
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
