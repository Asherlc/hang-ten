#!/usr/bin/env python3
"""Compile tagged Blender meshes into a validated model-first board package.

The compiler transports authored geometry; it never repairs shape, materials,
names, or topology. Only temporary export copies receive triangulation.
"""

from __future__ import annotations

import argparse
import json
import math
import os
import shutil
import sys
import tempfile
import zipfile
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Any

_SCRIPT_DIRECTORY = Path(__file__).resolve().parent
if str(_SCRIPT_DIRECTORY) not in sys.path:
    sys.path.insert(0, str(_SCRIPT_DIRECTORY))

from model_descriptor import ModelBounds, ModelDescriptorV1, NodeBinding, compile_descriptor


_BOUNDS_TOLERANCE_METERS = 0.000001
_IMPORTED_PROPERTY_PREFIX = "userProperties:"
_SOURCE_NODE_ID_PROPERTY = "hang_ten_source_node_id"
_DETERMINISTIC_ZIP_TIME = (1980, 1, 1, 0, 0, 0)


@dataclass(frozen=True)
class _SceneSnapshot:
    nodes: tuple[NodeBinding, ...]
    vertices_by_node_id: Mapping[str, tuple[tuple[float, float, float], ...]]


def load_logical_hold_ids(board_json_path: Path) -> frozenset[str]:
    """Read only logical ``holds[].id`` values from either package schema version."""
    path = Path(board_json_path)
    if path.is_symlink() or not path.is_file():
        raise ValueError(f"board JSON must be a regular file: {path}")
    try:
        document = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        raise ValueError(f"board JSON is not readable valid JSON: {path}") from error
    if not isinstance(document, Mapping):
        raise ValueError("board JSON must be an object")
    holds = document.get("holds")
    if not isinstance(holds, list) or not holds:
        raise ValueError("board JSON holds must be a non-empty array")
    hold_ids: list[str] = []
    for index, hold in enumerate(holds):
        if not isinstance(hold, Mapping):
            raise ValueError(f"board JSON holds[{index}] must be an object")
        hold_id = hold.get("id")
        if not isinstance(hold_id, str) or not hold_id:
            raise ValueError(f"board JSON holds[{index}].id must be a non-empty string")
        hold_ids.append(hold_id)
    if len(hold_ids) != len(set(hold_ids)):
        raise ValueError("board JSON contains duplicate logical hold IDs")
    return frozenset(hold_ids)


def validate_tagged_scene(
    scene: object,
    logical_hold_ids: frozenset[str],
    *,
    imported: bool = False,
) -> tuple[NodeBinding, ...]:
    """Validate the closed body/hold mesh-tag contract before geometry is read."""
    if not isinstance(logical_hold_ids, frozenset):
        raise ValueError("logical inventory must be a frozenset")
    objects = getattr(scene, "objects", None)
    if objects is None:
        raise ValueError("scene must expose objects")
    nodes: list[NodeBinding] = []
    for item in objects:
        name = getattr(item, "name", None)
        if not isinstance(name, str) or not name:
            raise ValueError("scene object name must be non-empty")
        if getattr(item, "type", None) != "MESH":
            if imported:
                continue
            raise ValueError(f"non-mesh authored geometry is not permitted: {name}")
        role = _object_property(item, "role", imported=imported)
        if role not in {"body", "hold", "attachment"}:
            raise ValueError(f"mesh {name} role must be body, hold, or attachment")
        hold_id = _object_property(item, "hold_id", imported=imported)
        if role == "body":
            if hold_id is not None:
                raise ValueError(f"body mesh {name} may not declare hold_id")
            nodes.append(NodeBinding(name, "body"))
            continue
        if role == "attachment":
            if hold_id is not None:
                raise ValueError(f"attachment mesh {name} may not declare hold_id")
            nodes.append(NodeBinding(name, "attachment"))
            continue
        if not isinstance(hold_id, str) or not hold_id:
            raise ValueError(f"hold mesh {name} requires hold_id")
        if hold_id not in logical_hold_ids:
            raise ValueError(f"hold mesh {name} has unknown hold_id: {hold_id}")
        nodes.append(NodeBinding(name, "hold", hold_id))

    node_ids = [node.node_id for node in nodes]
    if len(node_ids) != len(set(node_ids)):
        raise ValueError("scene contains duplicate mesh node IDs")
    body_count = sum(node.role == "body" for node in nodes)
    if body_count != 1:
        raise ValueError("scene requires exactly one body mesh")
    bound_hold_ids = {node.hold_id for node in nodes if node.role == "hold"}
    if bound_hold_ids != set(logical_hold_ids):
        raise ValueError("scene hold bindings must exactly match logical inventory")
    if sum(node.role == "attachment" for node in nodes) > 1:
        raise ValueError("scene permits at most one attachment mesh")
    return tuple(sorted(nodes, key=lambda node: node.node_id))


def open_scene(blend_path: Path) -> object:
    """Open one authored Blender file without changing its bytes."""
    path = Path(blend_path)
    if path.is_symlink() or not path.is_file():
        raise ValueError(f"blend input must be a regular file: {path}")
    bpy = _bpy()
    bpy.ops.wm.open_mainfile(filepath=str(path.resolve()))
    return bpy.context.scene


def compile_model_package(
    blend_path: Path,
    board_json_path: Path,
    output_directory: Path,
) -> ModelDescriptorV1:
    """Export, reimport, validate, and atomically publish one model package."""
    logical_hold_ids = load_logical_hold_ids(board_json_path)
    source_scene = open_scene(blend_path)
    source_nodes = validate_tagged_scene(source_scene, logical_hold_ids)
    source_snapshot = _snapshot_scene(
        source_scene, source_nodes, transform_to_board_frame=True
    )

    destination = Path(output_directory).resolve()
    if destination.exists():
        raise ValueError(f"output directory must not already exist: {destination}")
    destination.parent.mkdir(parents=True, exist_ok=True)
    staging = Path(
        tempfile.mkdtemp(
            prefix=f".{destination.name}.model-compiler-", dir=destination.parent
        )
    )
    try:
        assets = staging / "assets"
        assets.mkdir()
        model_path = assets / "primary.usdz"
        _export_temporary_copies(source_scene, source_nodes, model_path)
        _canonicalize_usdz(model_path)
        model_bytes = model_path.read_bytes()
        if not model_bytes:
            raise ValueError("USDZ export is empty")

        imported_scene = _import_usdz_into_empty_scene(model_path)
        imported_nodes = validate_tagged_scene(
            imported_scene, logical_hold_ids, imported=True
        )
        imported_snapshot = _snapshot_scene(
            imported_scene,
            imported_nodes,
            # Blender converts the Y-up USD stage back to its native Z-up
            # coordinates on import. Convert those importer-visible vertices
            # into the descriptor's fixed frame again.
            transform_to_board_frame=True,
            require_imported_materials=True,
            require_triangles=True,
        )
        imported_source_node_ids = _imported_source_node_ids(
            imported_scene, imported_snapshot.nodes
        )
        _require_bindings_unchanged(
            source_snapshot.nodes,
            imported_snapshot.nodes,
            imported_source_node_ids,
        )
        _require_bounds_stable(source_snapshot, imported_snapshot)
        descriptor = compile_descriptor(
            model_bytes,
            imported_snapshot.nodes,
            imported_snapshot.vertices_by_node_id,
            logical_hold_ids,
        )
        descriptor_path = assets / "primary.model.json"
        descriptor_path.write_text(
            json.dumps(
                descriptor.to_json(),
                indent=2,
                sort_keys=True,
                allow_nan=False,
            )
            + "\n",
            encoding="utf-8",
        )
        staged_files = {
            path.relative_to(staging).as_posix()
            for path in staging.rglob("*")
            if path.is_file()
        }
        if staged_files != {
            "assets/primary.model.json",
            "assets/primary.usdz",
        }:
            raise ValueError("compiler staging output contains unexpected files")
        os.replace(staging, destination)
        return descriptor
    finally:
        if staging.exists():
            shutil.rmtree(staging)


def _object_property(item: object, key: str, *, imported: bool) -> object:
    getter = getattr(item, "get", None)
    if not callable(getter):
        return None
    value = getter(key)
    if value is None and imported:
        value = getter(f"{_IMPORTED_PROPERTY_PREFIX}{key}")
    return value


def _snapshot_scene(
    scene: object,
    nodes: Sequence[NodeBinding],
    *,
    transform_to_board_frame: bool,
    require_imported_materials: bool = False,
    require_triangles: bool = False,
) -> _SceneSnapshot:
    bpy = _bpy()
    by_name = {item.name: item for item in scene.objects}
    depsgraph = bpy.context.evaluated_depsgraph_get()
    axis_transform = _board_axis_transform() if transform_to_board_frame else None
    vertices: dict[str, tuple[tuple[float, float, float], ...]] = {}
    for node in nodes:
        item = by_name[node.node_id]
        evaluated = item.evaluated_get(depsgraph)
        mesh = evaluated.to_mesh(preserve_all_data_layers=True, depsgraph=depsgraph)
        try:
            if not mesh.vertices:
                raise ValueError(f"mesh {node.node_id} has no vertices")
            matrix = evaluated.matrix_world
            if axis_transform is not None:
                matrix = axis_transform @ matrix
            vertices[node.node_id] = tuple(
                tuple(float(coordinate) for coordinate in (matrix @ vertex.co))
                for vertex in mesh.vertices
            )
            if require_triangles and any(len(polygon.vertices) != 3 for polygon in mesh.polygons):
                raise ValueError(f"imported mesh {node.node_id} is not triangulated")
            if require_imported_materials:
                _require_image_materials(mesh, node.node_id)
        finally:
            evaluated.to_mesh_clear()
    return _SceneSnapshot(tuple(nodes), vertices)


def _require_image_materials(mesh: object, node_id: str) -> None:
    materials = getattr(mesh, "materials", ())
    polygons = getattr(mesh, "polygons", ())
    used_indexes = {polygon.material_index for polygon in polygons}
    if not used_indexes:
        raise ValueError(f"imported mesh {node_id} has no material-bearing faces")
    for index in used_indexes:
        if index >= len(materials) or materials[index] is None:
            raise ValueError(f"imported mesh {node_id} is materialless")
        material = materials[index]
        nodes = getattr(getattr(material, "node_tree", None), "nodes", ())
        image_nodes = [
            node for node in nodes if getattr(node, "type", None) == "TEX_IMAGE"
        ]
        if not image_nodes:
            raise ValueError(f"imported mesh {node_id} has no image material")
        if not any(
            _image_has_usable_data(getattr(node, "image", None))
            for node in image_nodes
        ):
            raise ValueError(f"imported mesh {node_id} has no usable image data")


def _image_has_usable_data(image: object | None) -> bool:
    if image is None:
        return False
    if not bool(getattr(image, "has_data", False)):
        try:
            getattr(image, "pixels")[0]
        except (AttributeError, IndexError, RuntimeError, TypeError):
            return False
    size = getattr(image, "size", ())
    return (
        bool(getattr(image, "has_data", False))
        and len(size) == 2
        and all(int(dimension) > 0 for dimension in size)
    )


def _export_temporary_copies(
    source_scene: object, nodes: Sequence[NodeBinding], model_path: Path
) -> None:
    bpy = _bpy()
    source_by_name = {item.name: item for item in source_scene.objects}
    depsgraph = bpy.context.evaluated_depsgraph_get()
    export_scene = bpy.data.scenes.new("Hang Ten model compiler export")
    copies: list[tuple[object, str]] = []
    source_objects = list(source_scene.objects)
    try:
        for node in nodes:
            source = source_by_name[node.node_id]
            evaluated = source.evaluated_get(depsgraph)
            mesh = bpy.data.meshes.new_from_object(
                evaluated, preserve_all_data_layers=True, depsgraph=depsgraph
            )
            copied = bpy.data.objects.new(f"__export__{node.node_id}", mesh)
            copied["role"] = node.role
            copied[_SOURCE_NODE_ID_PROPERTY] = node.node_id
            if node.role == "hold":
                assert node.hold_id is not None
                copied["hold_id"] = node.hold_id
            copied.matrix_world = evaluated.matrix_world
            export_scene.collection.objects.link(copied)
            triangulator = copied.modifiers.new("Temporary USDZ triangulation", "TRIANGULATE")
            triangulator.quad_method = "FIXED"
            triangulator.ngon_method = "BEAUTY"
            copies.append((copied, node.node_id))

        # Blender object names are global. Unlink the loaded source objects only
        # in memory so temporary copies can retain their authored node IDs.
        for source in source_objects:
            bpy.data.objects.remove(source, do_unlink=True)
        for copied, node_id in copies:
            copied.name = node_id

        window = bpy.context.window
        if window is None:
            raise ValueError("Blender export requires an active context window")
        window.scene = export_scene
        bpy.ops.object.select_all(action="DESELECT")
        for copied, _ in copies:
            copied.select_set(True)
        bpy.context.view_layer.objects.active = copies[0][0]
        result = bpy.ops.wm.usd_export(
            filepath=str(model_path),
            selected_objects_only=True,
            export_materials=True,
            generate_preview_surface=True,
            export_custom_properties=True,
            convert_orientation=True,
            export_global_forward_selection="NEGATIVE_Z",
            export_global_up_selection="Y",
        )
        if "FINISHED" not in result:
            raise ValueError("USDZ export did not finish")
    finally:
        # All changed topology exists only in this disposable scene. The source
        # .blend on disk is never saved or changed.
        if export_scene.name in bpy.data.scenes:
            bpy.data.scenes.remove(export_scene)


def _canonicalize_usdz(model_path: Path) -> None:
    """Sort USD specs and write a byte-stable, 64-byte-aligned USDZ archive."""
    from pxr import Sdf

    path = Path(model_path)
    with tempfile.TemporaryDirectory(
        prefix=f".{path.stem}.canonical-", dir=path.parent
    ) as raw_directory:
        directory = Path(raw_directory)
        with zipfile.ZipFile(path) as archive:
            members = sorted(archive.namelist())
            if any(
                name.startswith("/") or ".." in Path(name).parts
                for name in members
            ):
                raise ValueError("USDZ export contains unsafe member paths")
            for name in members:
                destination = directory / name
                destination.parent.mkdir(parents=True, exist_ok=True)
                destination.write_bytes(archive.read(name))
        layers = [
            name
            for name in members
            if Path(name).suffix in {".usd", ".usda", ".usdc"}
        ]
        if len(layers) != 1:
            raise ValueError("USDZ export must contain exactly one USD layer")
        source_layer = Sdf.Layer.FindOrOpen(str(directory / layers[0]))
        if source_layer is None:
            raise ValueError("USDZ export layer is unreadable")
        source_layer_path = directory / layers[0]
        canonical_layer = source_layer_path.with_suffix(".usda")
        temporary_layer = canonical_layer.with_name(
            f"canonical{canonical_layer.suffix}"
        )
        destination_layer = Sdf.Layer.CreateNew(str(temporary_layer))
        if destination_layer is None:
            raise ValueError("USDZ canonical layer creation failed")
        for key in source_layer.pseudoRoot.ListInfoKeys():
            destination_layer.pseudoRoot.SetInfo(
                key, source_layer.pseudoRoot.GetInfo(key)
            )
        _copy_usd_specs_sorted(
            Sdf, source_layer, destination_layer, source_layer.rootPrims
        )
        destination_layer.Save()
        if source_layer_path != canonical_layer:
            source_layer_path.unlink()
        os.replace(temporary_layer, canonical_layer)
        members = sorted(
            canonical_layer.relative_to(directory).as_posix()
            if name == layers[0]
            else name
            for name in members
        )

        temporary_archive = path.with_name(f".{path.name}.canonical")
        try:
            with temporary_archive.open("wb") as destination:
                with zipfile.ZipFile(
                    destination, "w", compression=zipfile.ZIP_STORED
                ) as archive:
                    for name in members:
                        offset = destination.tell()
                        encoded_name = name.encode("utf-8")
                        padding = (-(offset + 30 + len(encoded_name) + 4)) % 64
                        info = zipfile.ZipInfo(name, _DETERMINISTIC_ZIP_TIME)
                        info.compress_type = zipfile.ZIP_STORED
                        info.create_system = 3
                        info.external_attr = 0o100644 << 16
                        info.extra = (
                            b"\xff\xff"
                            + padding.to_bytes(2, "little")
                            + bytes(padding)
                        )
                        archive.writestr(info, (directory / name).read_bytes())
            os.replace(temporary_archive, path)
        finally:
            temporary_archive.unlink(missing_ok=True)


def _copy_usd_specs_sorted(
    sdf: object,
    source_layer: object,
    destination_layer: object,
    children: object,
) -> None:
    for source_prim in sorted(list(children), key=lambda child: child.name):
        destination_prim = sdf.CreatePrimInLayer(destination_layer, source_prim.path)
        _copy_usd_prim_contents_sorted(
            sdf,
            source_layer,
            destination_layer,
            source_prim,
            destination_prim,
        )


def _copy_usd_prim_contents_sorted(
    sdf: object,
    source_layer: object,
    destination_layer: object,
    source_prim: object,
    destination_prim: object,
) -> None:
    for key in source_prim.ListInfoKeys():
        destination_prim.SetInfo(key, source_prim.GetInfo(key))
    for source_property in sorted(
        list(source_prim.properties), key=lambda prop: prop.name
    ):
        if not sdf.CopySpec(
            source_layer,
            source_property.path,
            destination_layer,
            source_property.path,
        ):
            raise ValueError(
                f"USDZ canonical property copy failed: {source_property.path}"
            )
    _copy_usd_specs_sorted(
        sdf, source_layer, destination_layer, source_prim.nameChildren
    )
    for source_variant_set in sorted(
        list(source_prim.variantSets.values()), key=lambda item: item.name
    ):
        for source_variant in sorted(
            list(source_variant_set.variants.values()), key=lambda item: item.name
        ):
            destination_variant = sdf.CreateVariantInLayer(
                destination_layer,
                source_prim.path,
                source_variant_set.name,
                source_variant.name,
            )
            _copy_usd_prim_contents_sorted(
                sdf,
                source_layer,
                destination_layer,
                source_variant.primSpec,
                destination_variant.primSpec,
            )


def _import_usdz_into_empty_scene(model_path: Path) -> object:
    bpy = _bpy()
    bpy.ops.wm.read_factory_settings(use_empty=True)
    result = bpy.ops.wm.usd_import(filepath=str(model_path), merge_parent_xform=True)
    if "FINISHED" not in result:
        raise ValueError("USDZ reimport did not finish")
    return bpy.context.scene


def _board_axis_transform() -> object:
    from mathutils import Matrix

    # Authored Blender convention: +X right, +Z up, front toward -Y.
    # hang-ten-board-v1: +X right, +Y up, +Z from back toward front.
    return Matrix(
        (
            (1.0, 0.0, 0.0, 0.0),
            (0.0, 0.0, 1.0, 0.0),
            (0.0, -1.0, 0.0, 0.0),
            (0.0, 0.0, 0.0, 1.0),
        )
    )


def _imported_source_node_ids(
    scene: object, imported_nodes: Sequence[NodeBinding]
) -> dict[str, str]:
    by_name = {item.name: item for item in scene.objects}
    correspondence: dict[str, str] = {}
    for node in imported_nodes:
        source_node_id = _object_property(
            by_name[node.node_id], _SOURCE_NODE_ID_PROPERTY, imported=True
        )
        if not isinstance(source_node_id, str) or not source_node_id:
            raise ValueError(
                f"USDZ reimport lost source-node correspondence for {node.node_id}"
            )
        correspondence[node.node_id] = source_node_id
    if len(set(correspondence.values())) != len(correspondence):
        raise ValueError("USDZ reimport duplicated source-node correspondence")
    return correspondence


def _require_bindings_unchanged(
    source_nodes: Sequence[NodeBinding],
    imported_nodes: Sequence[NodeBinding],
    imported_source_node_ids: Mapping[str, str],
) -> None:
    source_by_id = {node.node_id: node for node in source_nodes}
    imported_by_id = {node.node_id: node for node in imported_nodes}
    if set(imported_source_node_ids) != set(imported_by_id) or set(
        imported_source_node_ids.values()
    ) != set(source_by_id):
        raise ValueError("USDZ reimport changed mesh-to-hold bindings")
    for imported_node_id, source_node_id in imported_source_node_ids.items():
        source = source_by_id[source_node_id]
        imported = imported_by_id[imported_node_id]
        if (source.role, source.hold_id) != (imported.role, imported.hold_id):
            raise ValueError("USDZ reimport changed mesh-to-hold bindings")


def _require_bounds_stable(source: _SceneSnapshot, imported: _SceneSnapshot) -> None:
    _require_bounds_pair(
        _bounds(source.vertices_by_node_id), _bounds(imported.vertices_by_node_id)
    )
    source_by_binding = _bounds_by_binding(source)
    imported_by_binding = _bounds_by_binding(imported)
    if set(source_by_binding) != set(imported_by_binding):
        raise ValueError("USDZ reimport bounds drift changed binding inventory")
    for binding in source_by_binding:
        _require_bounds_pair(
            source_by_binding[binding], imported_by_binding[binding]
        )


def _require_bounds_pair(source_bounds: ModelBounds, imported_bounds: ModelBounds) -> None:
    for source_value, imported_value in zip(
        (*source_bounds.min, *source_bounds.max),
        (*imported_bounds.min, *imported_bounds.max),
    ):
        delta = abs(source_value - imported_value)
        if not math.isfinite(delta) or delta > _BOUNDS_TOLERANCE_METERS:
            raise ValueError("USDZ reimport bounds drift exceeds 0.000001 metres")


def _bounds_by_binding(
    snapshot: _SceneSnapshot,
) -> dict[tuple[str, str | None], ModelBounds]:
    vertices: dict[tuple[str, str | None], dict[str, Sequence[tuple[float, float, float]]]] = {}
    for node in snapshot.nodes:
        binding = (node.role, node.hold_id)
        vertices.setdefault(binding, {})[node.node_id] = snapshot.vertices_by_node_id[
            node.node_id
        ]
    return {binding: _bounds(values) for binding, values in vertices.items()}


def _bounds(
    vertices_by_node_id: Mapping[str, Sequence[tuple[float, float, float]]]
) -> ModelBounds:
    vertices = [vertex for values in vertices_by_node_id.values() for vertex in values]
    if not vertices:
        raise ValueError("model has no vertices")
    return ModelBounds(
        tuple(min(vertex[axis] for vertex in vertices) for axis in range(3)),
        tuple(max(vertex[axis] for vertex in vertices) for axis in range(3)),
    )


def _bpy() -> Any:
    try:
        import bpy
    except ImportError as error:
        raise RuntimeError("the model package compiler must run inside Blender") from error
    return bpy


def _arguments(argv: Sequence[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--blend", type=Path, required=True)
    parser.add_argument("--board-json", type=Path, required=True)
    parser.add_argument("--output-directory", type=Path, required=True)
    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> int:
    if argv is None and "--" in sys.argv:
        raw_arguments = list(sys.argv[sys.argv.index("--") + 1 :])
    else:
        raw_arguments = list(argv or ())
    arguments = _arguments(raw_arguments)
    compile_model_package(
        arguments.blend, arguments.board_json, arguments.output_directory
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
