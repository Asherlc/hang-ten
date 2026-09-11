"""Small, renderer-facing primitives shared by authored board generators.

These helpers are intentionally boring.  They create meshes from coordinates
already authored by a board generator and attach the compiler's semantic tags;
they do not inspect images, simplify geometry, apply booleans, or alter vertex
and face data.  A generator may provide its existing mesh factory when its
coordinates need a board-specific unit conversion.
"""

from __future__ import annotations

import hashlib
import struct
from pathlib import Path
from typing import Any, Callable, Iterable, Sequence

import bpy
from mathutils import Matrix, Vector


MeshFactory = Callable[..., object]


def _new_mesh(
    name: str,
    vertices: Sequence[Sequence[float]],
    faces: Sequence[Sequence[int]],
    materials: Iterable[object] = (),
) -> object:
    data = bpy.data.meshes.new(name)
    data.from_pydata(vertices, [], faces)
    data.update()
    obj = bpy.data.objects.new(name, data)
    bpy.context.collection.objects.link(obj)
    for material in materials:
        data.materials.append(material)
    return obj


def _create_mesh(
    name: str,
    vertices: Sequence[Sequence[float]],
    faces: Sequence[Sequence[int]],
    materials: Iterable[object] = (),
    *,
    mesh_factory: MeshFactory | None = None,
) -> object:
    """Call an existing board factory, preserving its coordinate contract."""
    if mesh_factory is None:
        return _new_mesh(name, vertices, faces, materials)
    if materials:
        try:
            return mesh_factory(name, vertices, faces, materials)
        except TypeError:
            # Compact II's existing factory takes no material argument; its
            # caller appends slots immediately after construction.
            obj = mesh_factory(name, vertices, faces)
            for material in materials:
                obj.data.materials.append(material)
            return obj
    return mesh_factory(name, vertices, faces)


def create_rounded_body(
    name: str,
    vertices: Sequence[Sequence[float]],
    faces: Sequence[Sequence[int]],
    *,
    materials: Iterable[object] = (),
    mesh_factory: MeshFactory | None = None,
) -> object:
    """Create a body from an already-authored rounded silhouette."""
    return _create_mesh(name, vertices, faces, materials, mesh_factory=mesh_factory)


def create_recess(
    name: str,
    vertices: Sequence[Sequence[float]],
    faces: Sequence[Sequence[int]],
    *,
    materials: Iterable[object] = (),
    mesh_factory: MeshFactory | None = None,
) -> object:
    """Create a disposable recess cutter without changing authored topology."""
    return _create_mesh(name, vertices, faces, materials, mesh_factory=mesh_factory)


def create_stepped_edge(
    name: str,
    vertices: Sequence[Sequence[float]],
    faces: Sequence[Sequence[int]],
    *,
    materials: Iterable[object] = (),
    mesh_factory: MeshFactory | None = None,
) -> object:
    """Create an authored stepped-edge construction mesh."""
    return _create_mesh(name, vertices, faces, materials, mesh_factory=mesh_factory)


def create_passage(
    name: str,
    vertices: Sequence[Sequence[float]],
    faces: Sequence[Sequence[int]],
    *,
    materials: Iterable[object] = (),
    mesh_factory: MeshFactory | None = None,
) -> object:
    """Create an authored integral passage mesh or disposable cutter."""
    return _create_mesh(name, vertices, faces, materials, mesh_factory=mesh_factory)


def tag_piece(
    obj: object,
    role: str,
    hold_id: str | None = None,
    *,
    coordinate_frame: str | None = None,
    display_estimate: bool | None = None,
) -> object:
    """Attach the closed compiler role/identity contract to one mesh piece."""
    if role not in {"body", "hold", "attachment"}:
        raise ValueError(f"unsupported mesh role: {role}")
    if role == "hold" and (not isinstance(hold_id, str) or not hold_id):
        raise ValueError("hold pieces require a non-empty hold_id")
    if role != "hold" and hold_id is not None:
        raise ValueError(f"{role} pieces may not declare hold_id")
    obj["role"] = role
    if hold_id is not None:
        obj["hold_id"] = hold_id
    elif "hold_id" in obj:
        del obj["hold_id"]
    if coordinate_frame is not None:
        obj["coordinate_frame"] = coordinate_frame
    if display_estimate is not None:
        obj["display_estimate"] = display_estimate
    return obj


def split_contact_surface(
    body: object,
    hold_ids: Iterable[str],
    *,
    tag: bool = False,
    body_name: str | None = None,
    name_for_material: Callable[[str], str] | None = None,
    coordinate_frame: str | None = None,
    display_estimate: bool | None = None,
) -> list[object]:
    """Separate material-bound contact surfaces into selectable mesh pieces.

    Blender performs the split on the existing mesh, so this operation does
    not create replacement coordinates or topology.  ``tag=False`` is useful
    for generators that retain a board-specific material/name pass afterward.
    """
    valid_ids = frozenset(hold_ids)
    bpy.ops.object.select_all(action="DESELECT")
    body.select_set(True)
    bpy.context.view_layer.objects.active = body
    bpy.ops.object.mode_set(mode="EDIT")
    bpy.ops.mesh.select_all(action="SELECT")
    bpy.ops.mesh.separate(type="MATERIAL")
    bpy.ops.object.mode_set(mode="OBJECT")
    objects = list(bpy.context.selected_objects)
    for obj in objects:
        used = {polygon.material_index for polygon in obj.data.polygons}
        if len(used) != 1:
            raise ValueError(f"contact split produced mixed material piece: {obj.name}")
        material = obj.data.materials[next(iter(used))]
        material_name = material.name
        is_hold = material_name in valid_ids
        if name_for_material is not None:
            obj.name = name_for_material(material_name)
        elif is_hold:
            obj.name = material_name
        elif body_name is not None:
            obj.name = body_name
        if tag:
            tag_piece(
                obj,
                "hold" if is_hold else "body",
                material_name if is_hold else None,
                coordinate_frame=coordinate_frame,
                display_estimate=display_estimate,
            )
    return objects


def _aim(obj: object, target: Sequence[float]) -> None:
    forward = (Vector(target) - obj.location).normalized()
    right = forward.cross(Vector((0, 1, 0))).normalized()
    up = right.cross(forward).normalized()
    obj.rotation_euler = Matrix((right, up, -forward)).transposed().to_euler()


def make_review_rig(samples: int = 48, *, owner: str | None = None):
    """Create transient camera/lights for review; none are exportable model data.

    The return shape intentionally matches Beastmaker's existing ``review_rig``
    contract: ``(camera, light-report-list)``.
    """
    scene = bpy.context.scene
    scene.render.resolution_percentage = 100
    scene.render.image_settings.file_format = "PNG"
    scene.render.film_transparent = False
    scene.render.engine = "CYCLES"
    scene.cycles.device = "CPU"
    scene.cycles.samples = samples
    scene.cycles.use_denoising = True
    scene.world.color = (.35, .35, .35)
    scene.world.use_nodes = True
    background = scene.world.node_tree.nodes.get("Background")
    background.inputs["Color"].default_value = (.82, .85, .89, 1)
    background.inputs["Strength"].default_value = .45
    scene.view_settings.view_transform = "AgX"
    scene.view_settings.look = "AgX - Medium High Contrast"
    scene.view_settings.exposure = -1.0

    camera_data = bpy.data.cameras.new("ReviewCamera")
    camera = bpy.data.objects.new("ReviewCamera", camera_data)
    scene.collection.objects.link(camera)
    camera_data.type = "ORTHO"
    camera_data.clip_start, camera_data.clip_end = .001, 10
    camera["no_export"] = True
    camera["review_owner"] = owner or Path.cwd().name
    scene.camera = camera
    lights = []
    for name, location, power, size in [
        ("Key", (.06, .48, .55), 22, .38),
        ("Fill", (.65, .18, .32), 6, .32),
        ("Rim", (.3, .36, -.18), 13, .30),
    ]:
        data = bpy.data.lights.new("Review" + name, "AREA")
        data.energy, data.shape, data.size = power, "DISK", size
        obj = bpy.data.objects.new("Review" + name, data)
        scene.collection.objects.link(obj)
        obj.location = location
        _aim(obj, (.29, .075, .03))
        obj["no_export"] = True
        obj["review_owner"] = owner or Path.cwd().name
        lights.append(dict(name=name, locationMeters=location, watts=power, sizeMeters=size))
    return camera, lights


def _digest(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _image_digest(image: object) -> str:
    packed = getattr(image, "packed_file", None)
    if packed is not None:
        try:
            return _digest(bytes(packed.data))
        except (AttributeError, TypeError):
            pass
    width, height = getattr(image, "size", (0, 0))
    pixels = [0.0] * (max(1, width * height * 4))
    try:
        image.pixels.foreach_get(pixels)
        payload = struct.pack(f"<{len(pixels)}f", *pixels)
    except (AttributeError, RuntimeError, TypeError):
        payload = repr((image.name, width, height)).encode()
    return _digest(payload)


def semantic_snapshot(scene: object) -> dict[str, object]:
    """Capture names, tags, transforms, topology, and image payload identity."""
    objects = []
    image_bytes: dict[str, str] = {}
    for obj in sorted(scene.objects, key=lambda item: item.name):
        export = not bool(obj.get("no_export", False))
        if obj.type == "MESH":
            vertices = [tuple(float(value) for value in obj.matrix_world @ vertex.co)
                        for vertex in obj.data.vertices]
            topology = [tuple(int(index) for index in polygon.vertices)
                        for polygon in obj.data.polygons]
            vertex_payload = repr(vertices).encode()
            topology_payload = repr(topology).encode()
            materials = [material.name for material in obj.data.materials]
            for material in obj.data.materials:
                for node in material.node_tree.nodes if material.use_nodes else ():
                    image = getattr(node, "image", None)
                    if image is not None:
                        image_bytes[image.name] = _image_digest(image)
            objects.append({
                "name": obj.name,
                "role": obj.get("role"),
                "holdID": obj.get("hold_id"),
                "export": export,
                "transform": tuple(tuple(float(value) for value in row) for row in obj.matrix_world),
                "vertexCount": len(vertices),
                "topologyCount": len(topology),
                "vertexHash": _digest(vertex_payload),
                "topologyHash": _digest(topology_payload),
                "materials": materials,
            })
        elif not export:
            objects.append({"name": obj.name, "role": obj.get("role"), "holdID": obj.get("hold_id"), "export": False})
    return {
        "objects": objects,
        "materialImageBytes": dict(sorted(image_bytes.items())),
        "reviewObjectNames": sorted(item["name"] for item in objects if not item["export"]),
    }
