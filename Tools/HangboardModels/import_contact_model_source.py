#!/usr/bin/env python3
"""Compile one SHA-bound user-provided model source through explicit contacts.

The source blend is opened read-only. Semantic tags are applied only to an
owned transport copy, and the contact-first compiler changes topology only on
disposable export meshes.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import shutil
import sys
import tempfile
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path

_TOOLS = Path(__file__).resolve().parent
if str(_TOOLS) not in sys.path:
    sys.path.insert(0, str(_TOOLS))


class MappingError(ValueError):
    """The explicit source-object/contact mapping is incomplete or ambiguous."""


class SourceManifestError(ValueError):
    """The user-provided source does not match its retained manifest."""


@dataclass(frozen=True)
class ValidatedMapping:
    roles_by_node: Mapping[str, str]
    contact_ids_by_node: Mapping[str, str]
    attachment_node_ids: tuple[str, ...]
    attachment_facts: tuple[Mapping[str, object], ...]
    logical_contact_ids: frozenset[str]
    logical_contact_order: tuple[str, ...]


def write_json(path: Path, value: object) -> None:
    destination = Path(path)
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(
        json.dumps(value, indent=2, sort_keys=True, allow_nan=False) + "\n",
        encoding="utf-8",
    )


def _load_object(path: Path, label: str) -> Mapping[str, object]:
    try:
        value = json.loads(Path(path).read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        raise ValueError(f"{label} is not readable valid JSON: {path}") from error
    if not isinstance(value, Mapping):
        raise ValueError(f"{label} must be an object")
    return value


def _sha256(path: Path) -> str:
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def verify_source_manifest(manifest_path: Path, package_id: str) -> Path:
    document = _load_object(manifest_path, "model source manifest")
    if document.get("schemaVersion") != 1:
        raise SourceManifestError("model source manifest schemaVersion must be 1")
    if document.get("packageID") != package_id:
        raise SourceManifestError("model source manifest packageID mismatch")
    authority = document.get("manufacturerPhysicalAuthority")
    if (
        not isinstance(authority, Mapping)
        or not isinstance(authority.get("publisher"), str)
        or not authority["publisher"]
        or not isinstance(authority.get("evidencePacket"), str)
        or not authority["evidencePacket"]
    ):
        raise SourceManifestError("manufacturer physical authority is incomplete")
    historical = document.get("historicalSource")
    if not isinstance(historical, Mapping) or historical.get("status") != "missing":
        raise SourceManifestError("historical source must be explicitly recorded as missing")
    source = document.get("auditedModelSource")
    if not isinstance(source, Mapping):
        raise SourceManifestError("auditedModelSource must be an object")
    if source.get("provenanceType") != "user-provided":
        raise SourceManifestError("audited model source must be user-provided")
    if not isinstance(source.get("authorization"), str) or not source["authorization"]:
        raise SourceManifestError("audited model source requires explicit authorization")
    raw_path = source.get("retainedPath")
    expected_hash = source.get("sha256")
    if not isinstance(raw_path, str) or not raw_path:
        raise SourceManifestError("audited model source retainedPath is missing")
    if not isinstance(expected_hash, str) or len(expected_hash) != 64:
        raise SourceManifestError("audited model source SHA-256 is invalid")
    path = Path(raw_path)
    if not path.is_absolute():
        path = Path.cwd() / path
    if path.is_symlink() or not path.is_file():
        raise SourceManifestError(f"audited model source is not a regular file: {path}")
    if _sha256(path) != expected_hash:
        raise SourceManifestError(f"audited model source hash mismatch: {path.name}")
    ruling = document.get("supersessionRuling")
    if not isinstance(ruling, str) or not ruling:
        raise SourceManifestError("source manifest requires a supersession ruling")
    return path.resolve()


def validate_mapping(
    document: Mapping[str, object], source_objects: Mapping[str, str]
) -> ValidatedMapping:
    if document.get("schemaVersion") != 1:
        raise MappingError("mapping schemaVersion must be 1")
    logical_values = document.get("logicalContactIDs")
    objects = document.get("objects")
    if not isinstance(logical_values, list) or any(
        not isinstance(value, str) or not value for value in logical_values
    ):
        raise MappingError("logicalContactIDs must contain non-empty strings")
    if len(logical_values) != len(set(logical_values)):
        raise MappingError("duplicate logical contact ID")
    logical_order = tuple(logical_values)
    logical_contact_ids = frozenset(logical_order)
    if not isinstance(objects, list):
        raise MappingError("objects must be an array")
    roles: dict[str, str] = {}
    contact_ids: dict[str, str] = {}
    attachments: list[Mapping[str, object]] = []
    for index, raw in enumerate(objects):
        if not isinstance(raw, Mapping):
            raise MappingError(f"objects[{index}] must be an object")
        node_id = raw.get("sourceNodeID")
        role = raw.get("role")
        if not isinstance(node_id, str) or not node_id:
            raise MappingError(f"objects[{index}].sourceNodeID must be non-empty")
        if node_id in roles:
            raise MappingError(f"duplicate source mapping: {node_id}")
        if node_id not in source_objects:
            raise MappingError(f"unknown source object: {node_id}")
        if role not in {"body", "contact", "attachment"}:
            raise MappingError(f"unknown mapping role for {node_id}: {role}")
        object_type = source_objects[node_id]
        if role in {"body", "contact"} and object_type != "MESH":
            raise MappingError(f"{role} mapping must name a mesh: {node_id}")
        if role == "attachment":
            if object_type == "MESH":
                raise MappingError(f"attachment mapping must be non-mesh: {node_id}")
            if raw.get("selectable") is not False:
                raise MappingError(f"attachment must be explicitly nonselectable: {node_id}")
            if "contactID" in raw or "holdID" in raw:
                raise MappingError(f"attachment may not declare a contact identity: {node_id}")
            order, position, metadata = raw.get("order"), raw.get("position"), raw.get("metadata")
            if not isinstance(order, int) or isinstance(order, bool) or order < 1:
                raise MappingError(f"attachment order must be a positive integer: {node_id}")
            if not isinstance(position, list) or len(position) != 3 or any(
                not isinstance(value, (int, float))
                or isinstance(value, bool)
                or not math.isfinite(value)
                for value in position
            ):
                raise MappingError(f"attachment position must be three finite numbers: {node_id}")
            if not isinstance(metadata, Mapping) or not metadata:
                raise MappingError(f"attachment metadata must be a non-empty object: {node_id}")
            attachments.append({
                "sourceNodeID": node_id,
                "order": order,
                "position": [float(value) for value in position],
                "metadata": dict(metadata),
            })
        elif role == "contact":
            contact_id = raw.get("contactID")
            if "holdID" in raw:
                raise MappingError(f"legacy holdID is not permitted: {node_id}")
            if not isinstance(contact_id, str) or not contact_id:
                raise MappingError(f"contact mapping requires contactID: {node_id}")
            if contact_id not in logical_contact_ids:
                raise MappingError(f"unknown logical contact ID for {node_id}: {contact_id}")
            contact_ids[node_id] = contact_id
        elif "contactID" in raw or "holdID" in raw:
            raise MappingError(f"body may not declare a contact identity: {node_id}")
        roles[node_id] = str(role)
    unknown = sorted(set(source_objects) - set(roles))
    if unknown:
        raise MappingError(f"unmapped source object: {unknown[0]}")
    if not any(role == "body" for role in roles.values()):
        raise MappingError("mapping requires a body mesh")
    missing = sorted(logical_contact_ids - set(contact_ids.values()))
    if missing:
        raise MappingError(f"unmapped logical contact IDs: {', '.join(missing)}")
    orders = [int(item["order"]) for item in attachments]
    if len(orders) != len(set(orders)):
        raise MappingError("attachment orders must be unique")
    facts = tuple(sorted(attachments, key=lambda item: int(item["order"])))
    return ValidatedMapping(
        roles,
        contact_ids,
        tuple(str(item["sourceNodeID"]) for item in facts),
        facts,
        logical_contact_ids,
        logical_order,
    )


def _json_property(value: object) -> object:
    if hasattr(value, "to_list"):
        return value.to_list()
    if not isinstance(value, (str, bytes, Mapping)) and hasattr(value, "__iter__"):
        return list(value)
    return value


def _require_attachment_facts(
    objects_by_name: Mapping[str, object], expected: Sequence[Mapping[str, object]]
) -> None:
    for fact in expected:
        source_id = str(fact["sourceNodeID"])
        item = objects_by_name.get(source_id)
        if item is None:
            raise MappingError(f"attachment marker missing from source scene: {source_id}")
        location = getattr(getattr(item, "matrix_world", None), "translation", None)
        if location is None or len(location) != 3:
            raise MappingError(f"attachment marker has no position: {source_id}")
        if any(
            abs(float(actual) - float(wanted)) > 0.000001
            for actual, wanted in zip(location, fact["position"])
        ):
            raise MappingError(f"attachment position mismatch: {source_id}")
        getter = getattr(item, "get", None)
        if callable(getter):
            for key, wanted in fact["metadata"].items():
                if _json_property(getter(key)) != wanted:
                    raise MappingError(f"attachment metadata mismatch for {source_id}: {key}")


def _preserve_attachment_evidence(
    objects_by_name: Mapping[str, object], validated: ValidatedMapping
) -> None:
    import bpy

    _require_attachment_facts(objects_by_name, validated.attachment_facts)
    body_names = [name for name, role in validated.roles_by_node.items() if role == "body"]
    payload = json.dumps(
        list(validated.attachment_facts),
        sort_keys=True,
        separators=(",", ":"),
        allow_nan=False,
    )
    for body_name in body_names:
        body = objects_by_name[body_name]
        body["hang_ten_attachments_v1"] = payload
        body.data["hang_ten_attachments_v1"] = payload
    archive_scene = bpy.data.scenes.get("Hang Ten source attachment evidence")
    if archive_scene is None:
        archive_scene = bpy.data.scenes.new("Hang Ten source attachment evidence")
    for source_id in validated.attachment_node_ids:
        marker = objects_by_name[source_id]
        archive_scene.collection.objects.link(marker)
        for collection in list(marker.users_collection):
            if collection != archive_scene.collection:
                collection.objects.unlink(marker)


def _ordered_board_contact_ids(board_json: Path) -> tuple[str, ...]:
    document = _load_object(board_json, "board JSON")
    values = document.get("contacts")
    if not isinstance(values, list):
        raise MappingError("board JSON contacts must be an array")
    result = tuple(item.get("id") if isinstance(item, Mapping) else None for item in values)
    if any(not isinstance(value, str) or not value for value in result):
        raise MappingError("board JSON contacts contain an invalid ID")
    return result  # type: ignore[return-value]


def import_package(
    manifest_path: Path,
    mapping_path: Path,
    package_id: str,
    board_json: Path,
    output_directory: Path,
) -> Mapping[str, object]:
    source_model = verify_source_manifest(manifest_path, package_id)
    mapping = _load_object(mapping_path, "contact mapping")
    if mapping.get("packageID") != package_id:
        raise MappingError("mapping packageID does not match requested package")
    try:
        import bpy
    except ImportError as error:
        raise RuntimeError("model import must run inside Blender") from error
    import contact_model_package as compiler

    output = Path(output_directory).resolve()
    if output.exists():
        raise ValueError(f"output directory must not already exist: {output}")
    output.parent.mkdir(parents=True, exist_ok=True)
    work = Path(tempfile.mkdtemp(prefix=f".{package_id}.contact-import-", dir=output.parent))
    try:
        bpy.ops.wm.open_mainfile(filepath=str(source_model))
        scene = bpy.context.scene
        source_objects = {item.name: item.type for item in scene.objects}
        validated = validate_mapping(mapping, source_objects)
        if _ordered_board_contact_ids(board_json) != validated.logical_contact_order:
            raise MappingError("mapping logicalContactIDs must match board contact order")
        by_name = {item.name: item for item in scene.objects}
        for node_id, role in validated.roles_by_node.items():
            item = by_name[node_id]
            if role == "attachment":
                continue
            item["role"] = role
            if role == "contact":
                item["contact_id"] = validated.contact_ids_by_node[node_id]
        _preserve_attachment_evidence(by_name, validated)
        adapted = work / "contact-source.blend"
        bpy.ops.wm.save_as_mainfile(filepath=str(adapted), check_existing=False)
        descriptor = compiler.compile_model_package(adapted, board_json, output)
        descriptor_path = output / "assets/primary.model.json"
        return {
            "packageID": package_id,
            "status": "converted",
            "sourceModelPath": str(source_model),
            "sourceModelSHA256": _sha256(source_model),
            "sourceGeometryChanged": False,
            "sourceObjectIDs": sorted(source_objects),
            "attachmentNodeIDs": list(validated.attachment_node_ids),
            "modelSHA256": descriptor.model_sha256,
            "descriptorSHA256": _sha256(descriptor_path),
            "modelBounds": descriptor.to_json()["modelBounds"],
            "nodeCount": len(descriptor.nodes),
            "contactCount": len(descriptor.contacts),
            "contactMappings": {
                source_id: validated.contact_ids_by_node[source_id]
                for source_id in sorted(validated.contact_ids_by_node)
            },
        }
    finally:
        shutil.rmtree(work)
        if work.exists():
            raise RuntimeError(f"failed to clean owned contact import directory: {work}")


def _arguments(argv: Sequence[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--mapping", type=Path, required=True)
    parser.add_argument("--package", required=True)
    parser.add_argument("--board-json", type=Path, required=True)
    parser.add_argument("--output-directory", type=Path, required=True)
    parser.add_argument("--report", type=Path, required=True)
    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> int:
    raw = (
        list(sys.argv[sys.argv.index("--") + 1 :])
        if argv is None and "--" in sys.argv
        else list(sys.argv[1:] if argv is None else argv)
    )
    arguments = _arguments(raw)
    report = import_package(
        arguments.manifest,
        arguments.mapping,
        arguments.package,
        arguments.board_json,
        arguments.output_directory,
    )
    write_json(arguments.report, report)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
