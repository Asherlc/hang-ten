#!/usr/bin/env python3
"""Import one supplied ZIP through explicit mappings and the existing compiler.

Run this entry point inside Blender.  It only adds semantic tags to an in-memory
copy of the supplied scene; it never infers identities from geometry or position.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import shutil
import sys
import tempfile
import zipfile
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Any

_TOOLS = Path(__file__).resolve().parent
if str(_TOOLS) not in sys.path:
    sys.path.insert(0, str(_TOOLS))


class MappingError(ValueError):
    """An explicit source-object mapping is incomplete or ambiguous."""


class SourceManifestError(ValueError):
    """A supplied archive does not match its recorded manifest."""


@dataclass(frozen=True)
class ValidatedMapping:
    roles_by_node: Mapping[str, str]
    hold_ids_by_node: Mapping[str, str]
    attachment_node_ids: tuple[str, ...]
    attachment_facts: tuple[Mapping[str, object], ...]
    logical_hold_ids: frozenset[str]


def write_json(path: Path, value: object) -> None:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(value, indent=2, sort_keys=True, allow_nan=False) + "\n",
        encoding="utf-8",
    )


def _sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _load_json(path: Path, label: str) -> Mapping[str, object]:
    try:
        value = json.loads(Path(path).read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        raise ValueError(f"{label} is not readable valid JSON: {path}") from error
    if not isinstance(value, Mapping):
        raise ValueError(f"{label} must be an object")
    return value


def verify_source_entry(entry: Mapping[str, object]) -> None:
    archive = Path(str(entry.get("zipPath", "")))
    if archive.is_symlink() or not archive.is_file():
        raise SourceManifestError(f"source ZIP is not a regular file: {archive}")
    expected_archive_hash = entry.get("zipSHA256")
    if _sha256(archive.read_bytes()) != expected_archive_hash:
        raise SourceManifestError(f"source ZIP hash mismatch: {archive.name}")
    source_model = entry.get("sourceModel")
    retained = entry.get("retainedMembers")
    retained_root_value = entry.get("retainedEvidenceRoot")
    if not isinstance(source_model, str) or not source_model.endswith(".blend"):
        raise SourceManifestError("sourceModel must name a .blend archive member")
    if not isinstance(retained, Mapping) or not retained:
        raise SourceManifestError("retainedMembers must be a non-empty object")
    if not isinstance(retained_root_value, str) or not retained_root_value:
        raise SourceManifestError("retainedEvidenceRoot must name the owned evidence directory")
    retained_root = Path(retained_root_value)
    with zipfile.ZipFile(archive) as bundle:
        names = set(bundle.namelist())
        if source_model not in names:
            raise SourceManifestError(f"source model missing from ZIP: {source_model}")
        for member, expected_hash in retained.items():
            if not isinstance(member, str) or member not in names:
                raise SourceManifestError(f"retained member missing from ZIP: {member}")
            if _sha256(bundle.read(member)) != expected_hash:
                raise SourceManifestError(f"retained member hash mismatch: {member}")
            retained_path = retained_root / member
            if retained_path.is_symlink() or not retained_path.is_file():
                raise SourceManifestError(f"retained evidence missing: {member}")
            if _sha256(retained_path.read_bytes()) != expected_hash:
                raise SourceManifestError(f"retained evidence hash mismatch: {member}")


def validate_mapping(
    document: Mapping[str, object], source_objects: Mapping[str, str]
) -> ValidatedMapping:
    if document.get("schemaVersion") != 1:
        raise MappingError("mapping schemaVersion must be 1")
    logical_values = document.get("logicalHoldIDs")
    objects = document.get("objects")
    if not isinstance(logical_values, list) or any(
        not isinstance(value, str) or not value for value in logical_values
    ):
        raise MappingError("logicalHoldIDs must contain non-empty strings")
    if len(logical_values) != len(set(logical_values)):
        raise MappingError("duplicate logical hold ID")
    logical_hold_ids = frozenset(logical_values)
    if not isinstance(objects, list):
        raise MappingError("objects must be an array")
    roles: dict[str, str] = {}
    hold_ids: dict[str, str] = {}
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
        if role not in {"body", "hold", "attachment"}:
            raise MappingError(f"unknown mapping role for {node_id}: {role}")
        object_type = source_objects[node_id]
        if role in {"body", "hold"} and object_type != "MESH":
            raise MappingError(f"{role} mapping must name a mesh: {node_id}")
        if role == "attachment":
            if object_type == "MESH":
                raise MappingError(f"attachment mapping must be non-mesh: {node_id}")
            if raw.get("selectable") is not False:
                raise MappingError(f"attachment must be explicitly nonselectable: {node_id}")
            if "holdID" in raw:
                raise MappingError(f"attachment may not declare holdID: {node_id}")
            order, position, metadata = raw.get("order"), raw.get("position"), raw.get("metadata")
            if not isinstance(order, int) or isinstance(order, bool) or order < 1:
                raise MappingError(f"attachment order must be a positive integer: {node_id}")
            if not isinstance(position, list) or len(position) != 3 or any(
                not isinstance(value, (int, float)) or isinstance(value, bool) or not math.isfinite(value)
                for value in position
            ):
                raise MappingError(f"attachment position must be three finite numbers: {node_id}")
            if not isinstance(metadata, Mapping) or not metadata:
                raise MappingError(f"attachment metadata must be a non-empty object: {node_id}")
            attachments.append({"sourceNodeID": node_id, "order": order,
                                "position": [float(value) for value in position],
                                "metadata": dict(metadata)})
        elif role == "hold":
            hold_id = raw.get("holdID")
            if not isinstance(hold_id, str) or not hold_id:
                raise MappingError(f"hold mapping requires holdID: {node_id}")
            if hold_id not in logical_hold_ids:
                raise MappingError(f"unknown logical hold ID for {node_id}: {hold_id}")
            hold_ids[node_id] = hold_id
        elif "holdID" in raw:
            raise MappingError(f"body may not declare holdID: {node_id}")
        roles[node_id] = str(role)
    unknown = sorted(set(source_objects) - set(roles))
    if unknown:
        raise MappingError(f"unmapped source object: {unknown[0]}")
    if not any(role == "body" for role in roles.values()):
        raise MappingError("mapping requires a body mesh")
    bound = set(hold_ids.values())
    missing = sorted(logical_hold_ids - bound)
    if missing:
        raise MappingError(f"unmapped logical hold IDs: {', '.join(missing)}")
    orders = [int(item["order"]) for item in attachments]
    if len(orders) != len(set(orders)):
        raise MappingError("attachment orders must be unique")
    facts = tuple(sorted(attachments, key=lambda item: int(item["order"])))
    return ValidatedMapping(roles, hold_ids,
                            tuple(str(item["sourceNodeID"]) for item in facts),
                            facts, logical_hold_ids)


def attachment_facts_from_mapping(
    document: Mapping[str, object],
) -> tuple[Mapping[str, object], ...]:
    """Read explicit attachment facts without inventing source scene objects."""
    objects = document.get("objects")
    if not isinstance(objects, list):
        raise MappingError("objects must be an array")
    facts: list[Mapping[str, object]] = []
    for index, raw in enumerate(objects):
        if not isinstance(raw, Mapping) or raw.get("role") != "attachment":
            continue
        source_id, order = raw.get("sourceNodeID"), raw.get("order")
        position, metadata = raw.get("position"), raw.get("metadata")
        if not isinstance(source_id, str) or not source_id:
            raise MappingError(f"objects[{index}].sourceNodeID must be non-empty")
        if raw.get("selectable") is not False:
            raise MappingError(f"attachment must be explicitly nonselectable: {source_id}")
        if not isinstance(order, int) or isinstance(order, bool) or order < 1:
            raise MappingError(f"attachment order must be a positive integer: {source_id}")
        if not isinstance(position, list) or len(position) != 3 or any(
            not isinstance(value, (int, float)) or isinstance(value, bool) or not math.isfinite(value)
            for value in position
        ):
            raise MappingError(f"attachment position must be three finite numbers: {source_id}")
        if not isinstance(metadata, Mapping) or not metadata:
            raise MappingError(f"attachment metadata must be a non-empty object: {source_id}")
        facts.append({"sourceNodeID": source_id, "order": order,
                      "position": [float(value) for value in position], "metadata": dict(metadata)})
    if len({item["sourceNodeID"] for item in facts}) != len(facts):
        raise MappingError("duplicate attachment source ID")
    if len({item["order"] for item in facts}) != len(facts):
        raise MappingError("attachment orders must be unique")
    return tuple(sorted(facts, key=lambda item: int(item["order"])))


def require_actual_attachment_facts(
    objects_by_name: Mapping[str, object], expected: Sequence[Mapping[str, object]]
) -> None:
    for fact in expected:
        source_id = str(fact["sourceNodeID"])
        item = objects_by_name.get(source_id)
        if item is None:
            raise MappingError(f"attachment marker missing from source scene: {source_id}")
        location = getattr(getattr(item, "matrix_world", None), "translation", None)
        if location is None:
            location = getattr(item, "location", None)
        if location is None or len(location) != 3:
            raise MappingError(f"attachment marker has no coordinates: {source_id}")
        if any(abs(float(left) - float(right)) > 0.000001
               for left, right in zip(location, fact["position"])):
            raise MappingError(f"attachment coordinate mismatch: {source_id}")
        getter = getattr(item, "get", None)
        if callable(getter):
            for key, wanted in fact["metadata"].items():
                actual = getter(key)
                if hasattr(actual, "to_list"):
                    actual = actual.to_list()
                elif not isinstance(actual, (str, bytes, Mapping)) and hasattr(actual, "__iter__"):
                    actual = list(actual)
                if actual != wanted:
                    raise MappingError(f"attachment metadata mismatch for {source_id}: {key}")


def _attachment_payload(facts: Sequence[Mapping[str, object]]) -> str:
    return json.dumps(list(facts), sort_keys=True, separators=(",", ":"), allow_nan=False)


def _preserve_attachments_for_compilation(
    objects_by_name: Mapping[str, object], validated: ValidatedMapping
) -> None:
    import bpy
    require_actual_attachment_facts(objects_by_name, validated.attachment_facts)
    body_name = next(name for name, role in validated.roles_by_node.items() if role == "body")
    payload = _attachment_payload(validated.attachment_facts)
    body = objects_by_name[body_name]
    body["hang_ten_attachments_v1"] = payload
    body.data["hang_ten_attachments_v1"] = payload
    if not validated.attachment_node_ids:
        return
    archive_scene = bpy.data.scenes.get("Hang Ten source attachment evidence")
    if archive_scene is None:
        archive_scene = bpy.data.scenes.new("Hang Ten source attachment evidence")
    for source_id in validated.attachment_node_ids:
        marker = objects_by_name[source_id]
        archive_scene.collection.objects.link(marker)
        for collection in list(marker.users_collection):
            if collection != archive_scene.collection:
                collection.objects.unlink(marker)


def _safe_extract(bundle: zipfile.ZipFile, destination: Path) -> None:
    root = destination.resolve()
    for info in bundle.infolist():
        target = (destination / info.filename).resolve()
        if root != target and root not in target.parents:
            raise SourceManifestError(f"unsafe ZIP member path: {info.filename}")
    bundle.extractall(destination)


def _source_entry(manifest: Mapping[str, object], package_id: str) -> Mapping[str, object]:
    packages = manifest.get("packages")
    if not isinstance(packages, list):
        raise SourceManifestError("source manifest packages must be an array")
    matches = [item for item in packages if isinstance(item, Mapping) and item.get("packageID") == package_id]
    if len(matches) != 1:
        raise SourceManifestError(f"source manifest requires one package: {package_id}")
    return matches[0]


def import_package(
    manifest_path: Path, mapping_path: Path, package_id: str, output_directory: Path
) -> Mapping[str, object]:
    manifest = _load_json(manifest_path, "source manifest")
    mapping = _load_json(mapping_path, "mapping")
    entry = _source_entry(manifest, package_id)
    if mapping.get("packageID") != package_id:
        raise MappingError("mapping packageID does not match requested package")
    verify_source_entry(entry)
    if mapping.get("promotionStatus") == "rejected" and "expectedError" not in mapping:
        reasons = mapping.get("rejectionReasons")
        if not isinstance(reasons, list) or not reasons:
            raise MappingError("rejected mapping requires rejectionReasons")
        return {"packageID": package_id, "status": "rejected", "reasons": reasons}

    try:
        import bpy
    except ImportError as error:
        raise RuntimeError("model import must run inside Blender") from error
    from compile_model_package import compile_model_package

    archive = Path(str(entry["zipPath"]))
    output = Path(output_directory).resolve()
    if output.exists():
        raise ValueError(f"output directory must not already exist: {output}")
    output.parent.mkdir(parents=True, exist_ok=True)
    work = Path(tempfile.mkdtemp(prefix=f".{package_id}.import-", dir=output.parent))
    try:
        with zipfile.ZipFile(archive) as bundle:
            _safe_extract(bundle, work)
        source_model = work / str(entry["sourceModel"])
        bpy.ops.wm.open_mainfile(filepath=str(source_model))
        scene = bpy.context.scene
        source_objects = {item.name: item.type for item in scene.objects}
        validated = validate_mapping(mapping, source_objects)
        by_name = {item.name: item for item in scene.objects}
        for node_id, role in validated.roles_by_node.items():
            item = by_name[node_id]
            if role == "attachment":
                continue
            item["role"] = role
            if role == "hold":
                item["hold_id"] = validated.hold_ids_by_node[node_id]
        _preserve_attachments_for_compilation(by_name, validated)
        adapted = work / "adapted.blend"
        bpy.ops.wm.save_as_mainfile(filepath=str(adapted), check_existing=False)
        board_json = work / "board.json"
        write_json(board_json, {"holds": [{"id": value} for value in sorted(validated.logical_hold_ids)]})
        descriptor = compile_model_package(adapted, board_json, output)
        return {
            "packageID": package_id,
            "status": "converted",
            "sourceObjectIDs": sorted(source_objects),
            "attachmentNodeIDs": list(validated.attachment_node_ids),
            "modelSHA256": descriptor.model_sha256,
            "modelBounds": descriptor.to_json()["modelBounds"],
            "nodeCount": len(descriptor.nodes),
            "holdCount": len(descriptor.holds),
        }
    finally:
        shutil.rmtree(work)
        if work.exists():
            raise RuntimeError(f"failed to clean owned import directory: {work}")


def _arguments(argv: Sequence[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--mapping", type=Path, required=True)
    parser.add_argument("--package", required=True)
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
    mapping = _load_json(arguments.mapping, "mapping")
    try:
        report = import_package(arguments.manifest, arguments.mapping, arguments.package, arguments.output_directory)
    except Exception as error:
        expected = mapping.get("expectedError")
        if mapping.get("promotionStatus") != "rejected" or not isinstance(expected, str) or expected not in str(error):
            raise
        report = {"packageID": arguments.package, "status": "rejected",
                  "errorType": type(error).__name__, "error": str(error),
                  "expectedError": expected}
    write_json(arguments.report, report)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
