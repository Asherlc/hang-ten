"""Render all 19 real contact meshes without modifying the source model.

blender --background --factory-startup --python-exit-code 1 \
  --python Tools/HangboardModels/render_hold_highlights.py -- --blend MODEL.blend

Labels come verbatim from the canonical board package. Generated annotations
exist only in the review scene; the input .blend is never saved or overwritten.
"""
import argparse
import colorsys
import hashlib
import html
import json
from pathlib import Path
import sys

import bpy
from bpy_extras.object_utils import world_to_camera_view
from mathutils import Vector


ROOT = Path(__file__).resolve().parents[2]
DEFAULT = ROOT / ".context" / f"{ROOT.name}-wood-grips-compact-ii"
parser = argparse.ArgumentParser()
parser.add_argument("--blend", type=Path, default=DEFAULT / "wood-grips-compact-ii.blend")
parser.add_argument("--output", type=Path, default=DEFAULT / "highlights")
modes = parser.add_mutually_exclusive_group()
modes.add_argument("--overview-only", action="store_true")
modes.add_argument("--contact-sheet-only", action="store_true",
                   help="Rebuild the contact sheet from a completed render set")
args = parser.parse_args(sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else [])
source = args.blend.resolve()
out = args.output.resolve()
out.mkdir(parents=True, exist_ok=True)
(out / "ownership.json").write_text(json.dumps({
    "owner": ROOT.name, "resources": [str(out)], "external_resources": []
}, indent=2) + "\n")
source_sha = hashlib.sha256(source.read_bytes()).hexdigest()
if args.contact_sheet_only:
    previous = json.loads((out / "highlight-report.json").read_text())
    assert previous["source_sha256"] == source_sha, "Existing renders belong to a different model"
    assert len(previous["individual_holds"]) == 19, "A complete set of 19 renders is required"
bpy.ops.wm.open_mainfile(filepath=str(source))
scene = bpy.context.scene
cam = scene.camera
assert cam is not None, "Source model needs its studio review camera"
holds = json.loads((ROOT / "Hangboards/metolius-wood-grips-compact-ii/board.json").read_text())["holds"]
# Read each row left to right; package storage order is not consistently spatial.
holds.sort(key=lambda h: (0 if h["kind"] in ("jug", "sloper") else
                          1 if h.get("sizeMillimeters") == 29 else 2,
                          h["geometry"][0]["frame"]["x"]))
contacts = {obj["hold_id"]: obj for obj in scene.objects if obj.type == "MESH" and "hold_id" in obj}
assert len(holds) == len(contacts) == 19
assert set(contacts) == {h["id"] for h in holds}
original_materials = {key: list(obj.data.materials) for key, obj in contacts.items()}
model_signature = {obj.name: (len(obj.data.vertices), len(obj.data.polygons))
                   for obj in scene.objects if obj.type == "MESH"}
annotations = bpy.data.collections.new("Hold review annotations")
scene.collection.children.link(annotations)


def linear(channel):
    return channel / 12.92 if channel <= .04045 else ((channel + .055) / 1.055) ** 2.4


def material(name, rgb, emission=False):
    mat = bpy.data.materials.new(name)
    mat.use_nodes = True
    mat.diffuse_color = (*rgb, 1)
    nodes = mat.node_tree.nodes
    shader = nodes.get("Principled BSDF")
    if emission:
        nodes.remove(shader)
        shader = nodes.new("ShaderNodeEmission")
        shader.inputs["Color"].default_value = (*rgb, 1)
        mat.node_tree.links.new(shader.outputs[0], nodes.get("Material Output").inputs["Surface"])
    else:
        shader.inputs["Base Color"].default_value = (*rgb, 1)
        shader.inputs["Roughness"].default_value = .43
    return mat


colors = [colorsys.hsv_to_rgb((.03 + i * .61803398875) % 1, .76, .87) for i in range(19)]
highlights = [material(f"Review hold {i+1:02d}", tuple(map(linear, color))) for i, color in enumerate(colors)]
ink = material("Review charcoal", (.025, .033, .046), True)
white = material("Review white", (1, 1, 1), True)
muted = material("Review secondary text", (.15, .17, .19), True)


def restore():
    for hold_id, obj in contacts.items():
        for index, mat in enumerate(original_materials[hold_id]):
            obj.data.materials[index] = mat


def highlight(hold_id, mat):
    obj = contacts[hold_id]
    for index in range(len(obj.data.materials)):
        obj.data.materials[index] = mat


def clear_annotations():
    for obj in list(annotations.objects):
        bpy.data.objects.remove(obj, do_unlink=True)


def screen_position(x, y, depth=.2):
    frame = cam.data.view_frame(scene=scene)
    width = max(v.x for v in frame) - min(v.x for v in frame)
    height = max(v.y for v in frame) - min(v.y for v in frame)
    return cam.matrix_world @ Vector(((x - .5) * width, (y - .5) * height, -depth))


def no_shadow(obj):
    if hasattr(obj, "visible_shadow"):
        obj.visible_shadow = False


def text(body, x, y, pixels, mat=ink, align="LEFT"):
    data = bpy.data.curves.new("Review label", "FONT")
    data.body = body
    frame = cam.data.view_frame(scene=scene)
    width = max(v.x for v in frame) - min(v.x for v in frame)
    data.size = pixels / scene.render.resolution_x * width
    data.align_x = align
    data.align_y = "CENTER"
    obj = bpy.data.objects.new("Review label", data)
    annotations.objects.link(obj)
    obj.location = screen_position(x, y, .19)
    obj.rotation_euler = cam.rotation_euler
    data.materials.append(mat)
    no_shadow(obj)
    return obj


def rectangle(x, y, width, height, mat, depth=.2):
    verts = [screen_position(x + dx * width, y + dy * height, depth)
             for dx, dy in [(-.5, -.5), (.5, -.5), (.5, .5), (-.5, .5)]]
    mesh = bpy.data.meshes.new("Review swatch")
    mesh.from_pydata(verts, [], [(0, 1, 2, 3)])
    obj = bpy.data.objects.new("Review swatch", mesh)
    annotations.objects.link(obj)
    mesh.materials.append(mat)
    no_shadow(obj)
    return obj


def configure(width, height, overview=False):
    clear_annotations()
    scene.render.resolution_x = width
    scene.render.resolution_y = height
    scene.render.resolution_percentage = 100
    scene.render.image_settings.file_format = "PNG"
    scene.render.engine = "CYCLES"
    scene.cycles.samples = 32 if overview else 20
    scene.cycles.use_denoising = True
    scene.view_layers[0].material_override = None
    cam.data.type = "ORTHO"
    cam.data.ortho_scale = .75
    cam.location = (.12, -1, .49)
    cam.rotation_euler = (Vector((0, -.028, .0785)) - cam.location).to_track_quat("-Z", "Y").to_euler()
    if overview:
        cam.location -= cam.rotation_euler.to_matrix() @ Vector((0, .069, 0))
    bpy.context.view_layer.update()


def render(filename):
    if args.contact_sheet_only and filename != "all-holds-contact-sheet.png":
        assert (out / filename).is_file(), filename
        return
    scene.render.filepath = str(out / filename)
    bpy.ops.render.render(write_still=True)
    print("HOLD_REVIEW_RENDER", filename, flush=True)


configure(2400, 1450, overview=True)
for index, hold in enumerate(holds):
    highlight(hold["id"], highlights[index])
text("Wood Grips Compact II", .055, .952, 63)
text("All 19 physical holds highlighted", .055, .902, 33, muted)
for index, hold in enumerate(holds):
    obj = contacts[hold["id"]]
    coords = [obj.matrix_world @ Vector(corner) for corner in obj.bound_box]
    center = sum(coords, Vector()) / len(coords)
    point = world_to_camera_view(scene, cam, center)
    rectangle(point.x, point.y, .016, .0265, ink)
    text(str(index + 1), point.x, point.y, 30, white, "CENTER")
    column = 0 if index < 5 else 1 if index < 12 else 2
    row = index if column == 0 else index - 5 if column == 1 else index - 12
    x = [.055, .345, .665][column]
    y = .302 - row * .032
    swatch = material(f"Legend swatch {index+1}", tuple(map(linear, colors[index])), True)
    rectangle(x + .007, y, .014, .020, swatch)
    text(f"{index+1:02d}  {hold['name']}", x + .020, y, 25)
for label, x in [("TOP CONTACTS", .055), ("UPPER ROW", .345), ("LOWER ROW", .665)]:
    text(label, x, .345, 29, muted)
text("Display model · geometry estimates; labels from the existing Hang Ten board package", .055, .035, 23, muted)
render("all-holds-overview.png")

entries = []
if not args.overview_only:
    for index, hold in enumerate(holds):
        restore()
        configure(1200, 560)
        highlight(hold["id"], highlights[index])
        text(f"{index+1:02d}  {hold['name']}", .045, .935, 34)
        text(hold["id"], .045, .054, 22, muted)
        filename = f"{index+1:02d}-{hold['id']}.png"
        render(filename)
        entries.append({"number": index+1, "id": hold["id"], "name": hold["name"], "image": filename})

restore()
assert model_signature == {obj.name: (len(obj.data.vertices), len(obj.data.polygons))
                           for obj in scene.objects if obj.type == "MESH" and obj.name in model_signature}
assert hashlib.sha256(source.read_bytes()).hexdigest() == source_sha, "Source blend changed during render"
report = {"owner": ROOT.name, "source_blend": str(source), "source_sha256": source_sha,
          "hold_count": len(holds), "geometry_modified": False,
          "overview": "all-holds-overview.png", "individual_holds": entries}
(out / "highlight-report.json").write_text(json.dumps(report, indent=2) + "\n")

if entries:
    cards = "\n".join(f'<a href="{html.escape(e["image"])}"><img src="{html.escape(e["image"])}" '
                      f'alt="{html.escape(e["name"])}"><span>{e["number"]:02d} · '
                      f'{html.escape(e["name"])}</span></a>' for e in entries)
    (out / "index.html").write_text('''<!doctype html><html lang="en"><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Wood Grips Compact II — all 19 holds</title><style>
body{margin:0;background:#f3f1ec;color:#222;font:16px system-ui,sans-serif;padding:24px}
main{max-width:1600px;margin:auto}h1{font-size:28px}p{color:#555}.overview{width:100%;display:block}
.grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(min(100%,360px),1fr));gap:18px;margin-top:24px}
a{display:block;color:inherit;text-decoration:none;background:white;border-radius:12px;overflow:hidden}
img{width:100%;display:block}span{display:block;padding:10px 16px 16px}</style>
<main><h1>Wood Grips Compact II</h1><p>All 19 physical holds. Select a card to inspect its full image.</p>
<a href="all-holds-overview.png"><img class="overview" src="all-holds-overview.png" alt="All 19 holds highlighted and numbered"></a>
<div class="grid">''' + cards + '</div></main></html>\n')
    # Lay out the exact per-hold renders as image planes in a separate Blender
    # scene. This is a review contact sheet, never a modification of board art.
    scene = bpy.data.scenes.new("All holds contact sheet")
    bpy.context.window.scene = scene
    annotations = bpy.data.collections.new("Contact sheet panels")
    scene.collection.children.link(annotations)
    cam_data = bpy.data.cameras.new("Contact sheet camera")
    cam = bpy.data.objects.new("Contact sheet camera", cam_data)
    scene.collection.objects.link(cam)
    scene.camera = cam
    cam.location = (0, 0, 1)
    cam.data.type = "ORTHO"
    cam.data.ortho_scale = 3.10
    scene.render.resolution_x = 2700
    scene.render.resolution_y = 3180
    scene.render.resolution_percentage = 100
    scene.render.engine = "CYCLES"
    scene.cycles.samples = 1
    scene.view_settings.view_transform = "Standard"
    scene.world = bpy.data.worlds.new("Contact sheet background")
    scene.world.use_nodes = True
    scene.world.node_tree.nodes.get("Background").inputs["Color"].default_value = (.9, .89, .87, 1)
    scene.render.image_settings.file_format = "PNG"
    bpy.context.view_layer.update()
    text("Wood Grips Compact II · 19 physical holds", .025, .971, 51)
    text("Each panel highlights one actual contact mesh", .025, .949, 30, muted)
    for index, entry in enumerate(entries):
        mat = material(f"Contact panel {index+1}", (1, 1, 1), True)
        shader = next(node for node in mat.node_tree.nodes if node.type == "EMISSION")
        texture = mat.node_tree.nodes.new("ShaderNodeTexImage")
        texture.image = bpy.data.images.load(str(out / entry["image"]), check_existing=True)
        mat.node_tree.links.new(texture.outputs["Color"], shader.inputs["Color"])
        x = .025 + (index % 3) * .323 + .313 / 2
        y = .859 - (index // 3) * .130
        obj = rectangle(x, y, .313, .124, mat)
        obj.data.uv_layers.new(name="UVMap")
        for loop, uv in zip(obj.data.uv_layers.active.data, [(0, 0), (1, 0), (1, 1), (0, 1)]):
            loop.uv = uv
    render("all-holds-contact-sheet.png")
    report["contact_sheet"] = "all-holds-contact-sheet.png"
    (out / "highlight-report.json").write_text(json.dumps(report, indent=2) + "\n")
print("HOLD_REVIEW_REPORT", json.dumps(report), flush=True)
