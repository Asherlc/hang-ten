"""Re-author the delivered Escape Beta Board GLB into the manufacturer's 22
numbered positions.

The delivered GLB merges the continuous pinch wings (thin + wide per side) and
the continuous centre 50/31 mm sloper rails (left + right). The manufacturer's
numbered diagram (Escape Climbing Beta Board, EC72100) prints labels 1-11 on
BOTH left and right, i.e. 22 selectable positions. This script:

  * imports the delivered GLB,
  * bisects each pinch wing at its vertical centre (upper = thin pinch),
  * bisects each centre sloper rail at the board width centre,
  * bakes the coordinate-wrapper empties into the meshes and deletes them,
  * gives every material a 1x1 sRGB image derived from its Principled base
    colour (image-backed materials are required downstream), and
  * re-exports a compiler-ready GLB.

Run:
    blender --background --factory-startup --python-exit-code 1 \
        --python reauthor_escape.py -- <in.glb> <out.glb> <report.json>
"""
from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path

import bpy
from mathutils import Vector

NOMINAL_WIDTH_M = 0.6604
NOMINAL_VERTICAL_M = 0.1524
NOMINAL_DEPTH_M = 0.0508

# source object -> (contact-list order, right/upper name, left/lower name)
PINCH_SPLITS = {
    "left-pinch": ("left-thin-pinch", "left-wide-pinch"),
    "right-pinch": ("right-thin-pinch", "right-wide-pinch"),
}
SLOPER_SPLITS = {
    "centre-sloper-50": ("right-sloper-50", "left-sloper-50"),
    "centre-sloper-31": ("right-sloper-31", "left-sloper-31"),
}


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def to_srgb(value: float) -> float:
    if value <= 0.0031308:
        return 12.92 * value
    return 1.055 * (value ** (1.0 / 2.4)) - 0.055


def world_bounds(obj: bpy.types.Object) -> dict[str, tuple[float, float]]:
    points = [obj.matrix_world @ vertex.co for vertex in obj.data.vertices]
    if not points:
        raise SystemExit(f"mesh {obj.name!r} has no vertices")
    return {
        axis: (min(getattr(p, axis) for p in points), max(getattr(p, axis) for p in points))
        for axis in ("x", "y", "z")
    }


def centroid(obj: bpy.types.Object) -> Vector:
    points = [obj.matrix_world @ vertex.co for vertex in obj.data.vertices]
    total = Vector((0.0, 0.0, 0.0))
    for point in points:
        total += point
    return total / len(points)


def unit_axis(index: int) -> Vector:
    axis = Vector((0.0, 0.0, 0.0))
    axis[index] = 1.0
    return axis


def duplicate_object(obj: bpy.types.Object) -> bpy.types.Object:
    duplicate = obj.copy()
    duplicate.data = obj.data.copy()
    bpy.context.collection.objects.link(duplicate)
    return duplicate


def bisect(obj: bpy.types.Object, plane_co: Vector, plane_no: Vector, keep_positive: bool) -> None:
    bpy.ops.object.select_all(action="DESELECT")
    bpy.context.view_layer.objects.active = obj
    obj.select_set(True)
    bpy.ops.object.mode_set(mode="EDIT")
    bpy.ops.mesh.select_all(action="SELECT")
    result = bpy.ops.mesh.bisect(
        plane_co=plane_co,
        plane_no=plane_no,
        clear_inner=keep_positive,
        clear_outer=not keep_positive,
        use_fill=False,
    )
    bpy.ops.mesh.delete_loose(use_verts=True, use_edges=True, use_faces=False)
    bpy.ops.object.mode_set(mode="OBJECT")
    if "FINISHED" not in result:
        raise SystemExit(f"bisect did not finish for {obj.name!r}")
    if not obj.data.polygons:
        raise SystemExit(f"split produced an empty object: {obj.name!r}")


def split_object(
    source: bpy.types.Object,
    plane_co: Vector,
    plane_no: Vector,
    positive_name: str,
    negative_name: str,
) -> tuple[bpy.types.Object, bpy.types.Object]:
    """Keep the +normal half as positive_name and the -normal half as negative_name."""
    positive = duplicate_object(source)
    positive.name = positive_name
    bisect(positive, plane_co, plane_no, keep_positive=True)

    negative = duplicate_object(source)
    negative.name = negative_name
    bisect(negative, plane_co, plane_no, keep_positive=False)

    for new in (positive, negative):
        for key, value in source.items():
            new[key] = value
        new["holdId"] = new.name
        new["selectable"] = True

    original_name = source.name
    bpy.data.objects.remove(source, do_unlink=True)
    print(
        f"split {original_name!r}: +n -> {positive_name!r} "
        f"({len(positive.data.polygons)} faces), -n -> {negative_name!r} "
        f"({len(negative.data.polygons)} faces)"
    )
    return positive, negative


def bake_wrappers(meshes: list[bpy.types.Object]) -> None:
    bpy.ops.object.select_all(action="DESELECT")
    for mesh in meshes:
        mesh.select_set(True)
    bpy.context.view_layer.objects.active = meshes[0]
    bpy.ops.object.parent_clear(type="CLEAR_KEEP_TRANSFORM")
    bpy.ops.object.transform_apply(location=True, rotation=True, scale=True)
    for obj in [o for o in bpy.context.scene.objects if o.type != "MESH"]:
        bpy.data.objects.remove(obj, do_unlink=True)
    leftovers = [o.name for o in bpy.context.scene.objects if o.type != "MESH"]
    if leftovers:
        raise SystemExit(f"non-mesh objects remain: {leftovers}")


def normalize_materials() -> None:
    for material in bpy.data.materials:
        tree = getattr(material, "node_tree", None)
        if tree is None:
            continue
        bsdf = next((n for n in tree.nodes if n.type == "BSDF_PRINCIPLED"), None)
        if bsdf is None:
            continue
        if bsdf.inputs["Base Color"].is_linked:
            continue
        color = list(bsdf.inputs["Base Color"].default_value)
        image = bpy.data.images.new(
            f"neutral-{material.name}", width=1, height=1, alpha=True
        )
        image.colorspace_settings.name = "sRGB"
        image.pixels = [
            to_srgb(color[0]),
            to_srgb(color[1]),
            to_srgb(color[2]),
            1.0,
        ]
        texture = tree.nodes.new("ShaderNodeTexImage")
        texture.image = image
        texture.location = (bsdf.location.x - 320, bsdf.location.y)
        tree.links.new(texture.outputs["Color"], bsdf.inputs["Base Color"])
    for material in bpy.data.materials:
        tree = getattr(material, "node_tree", None)
        if tree is None:
            continue
        if not any(
            n.type == "TEX_IMAGE" and getattr(n.image, "has_data", False)
            for n in tree.nodes
        ):
            raise SystemExit(f"material {material.name!r} has no usable image node")


def make_camera(name: str, location: Vector, target: Vector, ortho_scale: float):
    camera_data = bpy.data.cameras.new(name)
    camera_data.type = "ORTHO"
    camera_data.ortho_scale = ortho_scale
    camera = bpy.data.objects.new(name, camera_data)
    bpy.context.scene.collection.objects.link(camera)
    camera.location = location
    direction = target - location
    camera.rotation_euler = direction.to_track_quat("-Z", "Y").to_euler()
    return camera


def assign_viewport_colors(objects: list[bpy.types.Object]) -> None:
    contacts = sorted((o for o in objects if o.name != "body-board"), key=lambda o: o.name)
    palette = [
        (0.90, 0.20, 0.20, 1.0),
        (0.20, 0.55, 0.90, 1.0),
        (0.25, 0.75, 0.35, 1.0),
        (0.90, 0.65, 0.15, 1.0),
        (0.65, 0.30, 0.85, 1.0),
        (0.15, 0.80, 0.80, 1.0),
    ]
    for index, obj in enumerate(contacts):
        obj.color = palette[index % len(palette)]
    for obj in objects:
        if obj.name == "body-board":
            obj.color = (0.55, 0.12, 0.13, 1.0)


def render_reviews(objects: list[bpy.types.Object], review_dir: Path, report: dict) -> None:
    scene = bpy.context.scene
    scene.render.engine = "BLENDER_WORKBENCH"
    scene.render.resolution_x = 900
    scene.render.resolution_y = 700
    scene.render.film_transparent = False
    shading = scene.display.shading
    shading.light = "STUDIO"
    shading.color_type = "OBJECT"
    shading.show_shadows = False
    shading.show_cavity = True
    assign_viewport_colors(objects)

    body = bpy.data.objects["body-board"]
    bounds = world_bounds(body)
    center = Vector(
        (
            (bounds["x"][0] + bounds["x"][1]) / 2,
            (bounds["y"][0] + bounds["y"][1]) / 2,
            (bounds["z"][0] + bounds["z"][1]) / 2,
        )
    )
    width = bounds["x"][1] - bounds["x"][0]
    height = bounds["z"][1] - bounds["z"][0]

    renders: list[dict] = []

    def render(name: str, location: Vector, target: Vector, ortho_scale: float) -> None:
        camera = make_camera(f"review-{name}", location, target, ortho_scale)
        scene.camera = camera
        path = review_dir / f"{name}.png"
        scene.render.filepath = str(path)
        bpy.ops.render.render(write_still=True)
        renders.append({"name": name, "path": str(path), "orthoScale": ortho_scale})
        print(f"rendered {path}")

    front_scale = max(width, height) * 1.15
    render("front", center + Vector((0.0, -1.0, 0.0)), center, front_scale)
    render(
        "oblique",
        center + Vector((-0.55, -0.85, 0.45)),
        center,
        front_scale * 1.05,
    )

    region_groups: dict[str, list[bpy.types.Object]] = {}
    for source_name, names in {**PINCH_SPLITS, **SLOPER_SPLITS}.items():
        halves = [bpy.data.objects[n] for n in names if n in bpy.data.objects]
        if len(halves) == 2:
            region_groups[source_name] = halves

    for source_name, halves in region_groups.items():
        points = [obj.matrix_world @ v.co for obj in halves for v in obj.data.vertices]
        region = {
            axis: (min(getattr(p, axis) for p in points), max(getattr(p, axis) for p in points))
            for axis in ("x", "y", "z")
        }
        region_center = Vector(
            (
                (region["x"][0] + region["x"][1]) / 2,
                (region["y"][0] + region["y"][1]) / 2,
                (region["z"][0] + region["z"][1]) / 2,
            )
        )
        region_scale = max(
            region["x"][1] - region["x"][0],
            region["z"][1] - region["z"][0],
        ) * 1.5
        render(
            f"closeup-{source_name}",
            region_center + Vector((0.0, -1.0, 0.0)),
            region_center,
            region_scale,
        )

    report["renders"] = renders


def build_hold_map(source_hold_map: dict, face_counts: dict, split_geometry: dict) -> dict:
    depth_meta = {c["nodeName"]: c for c in source_hold_map["contacts"]}
    contacts: list[dict] = []
    for contact in source_hold_map["contacts"]:
        hold_id = contact["holdId"]
        if hold_id in PINCH_SPLITS:
            thin, wide = PINCH_SPLITS[hold_id]
            for new_name, prefix, side in (
                (thin, "Thin ", "thin"),
                (wide, "Wide ", "wide"),
            ):
                entry = dict(contact)
                entry["holdId"] = new_name
                entry["nodeName"] = new_name
                entry["name"] = f"{prefix}{contact['name']}"
                entry["triangleCount"] = face_counts[new_name]
                contacts.append(entry)
        elif hold_id in SLOPER_SPLITS:
            right, left = SLOPER_SPLITS[hold_id]
            for new_name, prefix in ((left, "Left "), (right, "Right ")):
                entry = dict(contact)
                entry["holdId"] = new_name
                entry["nodeName"] = new_name
                entry["name"] = f"{prefix}{contact['name']}"
                entry["triangleCount"] = face_counts[new_name]
                contacts.append(entry)
        else:
            entry = dict(contact)
            entry["triangleCount"] = face_counts[hold_id]
            contacts.append(entry)

    result = dict(source_hold_map)
    result["contacts"] = contacts
    result["reauthoring"] = {
        "agent": "reauthor_escape.py",
        "manufacturerPositions": 22,
        "splitCoordinates": split_geometry,
        "sourceHoldMapContacts": len(source_hold_map["contacts"]),
        "note": (
            "Thin/wide pinch and left/right sloper halves inherit their source "
            "region's metadata; thin pinch is the upper (positive vertical) half, "
            "wide pinch the lower half; sloper halves are split at the board width "
            "centre with left = negative width direction."
        ),
    }
    return result


def main(src: Path, dst: Path, report_path: Path) -> None:
    if not src.is_file():
        raise SystemExit(f"input GLB not found: {src}")
    source_hold_map_path = Path(dst).parent.parent / "source" / "escape-beta-board" / "hold-map.json"
    if not source_hold_map_path.is_file():
        raise SystemExit(f"source hold-map not found: {source_hold_map_path}")

    bpy.ops.wm.read_factory_settings(use_empty=True)
    bpy.ops.import_scene.gltf(filepath=str(src))

    meshes = [o for o in bpy.context.scene.objects if o.type == "MESH"]
    body = bpy.data.objects.get("body-board")
    if body is None:
        raise SystemExit("body-board mesh not found in input GLB")

    bounds = world_bounds(body)
    extents = {axis: bounds[axis][1] - bounds[axis][0] for axis in ("x", "y", "z")}
    largest = max(extents, key=extents.get)
    smallest = min(extents, key=extents.get)
    vertical = next(a for a in ("x", "y", "z") if a not in (largest, smallest))
    indices = {"x": 0, "y": 1, "z": 2}
    dimensions_ok = (
        abs(extents[largest] - NOMINAL_WIDTH_M) < 0.03
        and abs(extents[vertical] - NOMINAL_VERTICAL_M) < 0.02
        and abs(extents[smallest] - NOMINAL_DEPTH_M) < 0.02
    )
    print(
        f"body-board extents: width({largest})={extents[largest]:.4f} "
        f"vertical({vertical})={extents[vertical]:.4f} "
        f"depth({smallest})={extents[smallest]:.4f} nominal_match={dimensions_ok}"
    )
    if not dimensions_ok:
        raise SystemExit("body-board extents do not match the Escape Beta nominal dimensions")

    right_axis = unit_axis(indices[largest])
    up_axis = unit_axis(indices[vertical])
    left_ref = bpy.data.objects.get("left-jug-38")
    right_ref = bpy.data.objects.get("right-jug-38")
    if left_ref and right_ref:
        if centroid(left_ref).dot(right_axis) > centroid(right_ref).dot(right_axis):
            right_axis = -right_axis
    upper_ref = bpy.data.objects.get("left-jug-38")
    lower_ref = bpy.data.objects.get("left-incut-12")
    if upper_ref and lower_ref:
        if centroid(upper_ref).dot(up_axis) < centroid(lower_ref).dot(up_axis):
            up_axis = -up_axis
    print(f"width/right axis = {tuple(right_axis)}, vertical/up axis = {tuple(up_axis)}")

    split_geometry: dict[str, dict] = {}

    for source_name, (positive_name, negative_name) in PINCH_SPLITS.items():
        source = bpy.data.objects.get(source_name)
        if source is None:
            raise SystemExit(f"missing pinch source object: {source_name}")
        wing_bounds = world_bounds(source)
        axis_key = vertical
        mid = (wing_bounds[axis_key][0] + wing_bounds[axis_key][1]) / 2
        plane_co = up_axis * mid
        positive, negative = split_object(source, plane_co, up_axis, positive_name, negative_name)
        split_geometry[source_name] = {
            "axis": vertical,
            "planeCoordinateMeters": mid,
            "planeNormal": list(up_axis),
            "upper": positive_name,
            "lower": negative_name,
        }

    board_center_width = (bounds[largest][0] + bounds[largest][1]) / 2
    for source_name, (positive_name, negative_name) in SLOPER_SPLITS.items():
        source = bpy.data.objects.get(source_name)
        if source is None:
            raise SystemExit(f"missing sloper source object: {source_name}")
        plane_co = right_axis * board_center_width
        positive, negative = split_object(source, plane_co, right_axis, positive_name, negative_name)
        split_geometry[source_name] = {
            "axis": largest,
            "planeCoordinateMeters": board_center_width,
            "planeNormal": list(right_axis),
            "right": positive_name,
            "left": negative_name,
        }

    expected_contacts = set()
    for thin, wide in PINCH_SPLITS.values():
        expected_contacts.update((thin, wide))
    for right, left in SLOPER_SPLITS.values():
        expected_contacts.update((right, left))
    expected_contacts.update(
        c["nodeName"] for c in json.loads(source_hold_map_path.read_text())["contacts"]
        if c["nodeName"] not in PINCH_SPLITS and c["nodeName"] not in SLOPER_SPLITS
    )
    present_contacts = {o.name for o in bpy.context.scene.objects if o.type == "MESH" and o.name != "body-board"}
    if present_contacts != expected_contacts:
        raise SystemExit(
            f"contact set mismatch: missing={sorted(expected_contacts - present_contacts)} "
            f"extra={sorted(present_contacts - expected_contacts)}"
        )

    meshes = [o for o in bpy.context.scene.objects if o.type == "MESH"]
    empty = [o.name for o in meshes if len(o.data.polygons) == 0]
    if empty:
        raise SystemExit(f"objects with no faces: {empty}")
    print(f"contact objects before bake: {len(present_contacts)}")

    bake_wrappers(meshes)

    meshes = [o for o in bpy.context.scene.objects if o.type == "MESH"]
    empty = [o.name for o in meshes if len(o.data.polygons) == 0]
    if empty:
        raise SystemExit(f"objects with no faces after bake: {empty}")

    normalize_materials()

    poly_counts = {o.name: len(o.data.polygons) for o in meshes}
    triangle_counts = {
        o.name: sum(len(polygon.vertices) - 2 for polygon in o.data.polygons)
        for o in meshes
    }
    print("triangle counts:", json.dumps(triangle_counts, indent=2, sort_keys=True))

    bpy.ops.export_scene.gltf(
        filepath=str(dst),
        export_format="GLB",
        use_selection=False,
        export_extras=True,
    )
    print(f"exported {dst}")

    source_hold_map = json.loads(source_hold_map_path.read_text())
    hold_map = build_hold_map(source_hold_map, triangle_counts, split_geometry)
    hold_map_path = Path(dst).parent / "hold-map.json"
    hold_map_path.write_text(json.dumps(hold_map, indent=2, ensure_ascii=False) + "\n")

    report = {
        "schemaVersion": 1,
        "inputPath": str(src),
        "inputSHA256": sha256_file(src),
        "outputPath": str(dst),
        "outputSHA256": sha256_file(dst),
        "holdMapPath": str(hold_map_path),
        "contactCount": len(present_contacts),
        "meshObjectCount": len(meshes),
        "boardBoundsMeters": {axis: list(bounds[axis]) for axis in ("x", "y", "z")},
        "axes": {
            "width": largest,
            "vertical": vertical,
            "depth": smallest,
            "rightDirection": list(right_axis),
            "upDirection": list(up_axis),
        },
        "nominalDimensionsMatch": dimensions_ok,
        "splitCoordinates": split_geometry,
        "objectTriangleCounts": triangle_counts,
        "objectFaceCounts": poly_counts,
        "emptyObjects": [],
        "materials": sorted(m.name for m in bpy.data.materials),
    }

    review_dir = Path(dst).parent / "review"
    review_dir.mkdir(parents=True, exist_ok=True)
    render_reviews(meshes, review_dir, report)

    report_path.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n")
    print(f"wrote {report_path}")


if __name__ == "__main__":
    arguments = sys.argv[sys.argv.index("--") + 1 :]
    if len(arguments) != 3:
        raise SystemExit("usage: -- <in.glb> <out.glb> <report.json>")
    main(*(Path(argument) for argument in arguments))
