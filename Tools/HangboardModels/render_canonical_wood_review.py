#!/usr/bin/env python3
"""Render matched front and oblique actual-USDZ reviews for shipped wood models."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

import bpy
from mathutils import Vector


ROOT = Path(__file__).resolve().parents[2]
parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument("--output", type=Path, required=True)
args = parser.parse_args(sys.argv[sys.argv.index("--") + 1 :] if "--" in sys.argv else [])
out = args.output.resolve()
out.mkdir(parents=True, exist_ok=True)
(out / "ownership.json").write_text(json.dumps({"owner": ROOT.name, "resources": [str(out)], "external_resources": []}, indent=2) + "\n")


def aim(item, target):
    item.rotation_euler = (Vector(target) - item.location).to_track_quat("-Z", "Y").to_euler()


def render_board(slug: str):
    bpy.ops.wm.read_factory_settings(use_empty=True)
    model = ROOT / "Hangboards" / slug / "assets/primary.usdz"
    if "FINISHED" not in bpy.ops.wm.usd_import(filepath=str(model), merge_parent_xform=True):
        raise RuntimeError(f"could not import {model}")
    meshes = [item for item in bpy.context.scene.objects if item.type == "MESH"]
    vertices = [item.matrix_world @ vertex.co for item in meshes for vertex in item.data.vertices]
    lo = [min(point[index] for point in vertices) for index in range(3)]
    hi = [max(point[index] for point in vertices) for index in range(3)]
    center = [(lo[index] + hi[index]) / 2 for index in range(3)]
    width, height, depth = hi[0] - lo[0], hi[2] - lo[2], hi[1] - lo[1]
    span = max(width, height)
    scene = bpy.context.scene
    scene.render.engine = "BLENDER_EEVEE"
    scene.render.resolution_x, scene.render.resolution_y = 1200, 700
    scene.render.resolution_percentage = 100
    scene.render.image_settings.file_format = "PNG"
    # Match the exported model review transform.  The neutral background and
    # broad area lights otherwise clip a pale diffuse texture toward white,
    # obscuring the intentionally restrained wood grain at mobile scale.
    scene.view_settings.view_transform = "AgX"
    scene.view_settings.look = "AgX - Medium High Contrast"
    scene.view_settings.exposure = -1.0
    if scene.world is None:
        scene.world = bpy.data.worlds.new("Canonical wood review world")
    scene.world.color = (0.055, 0.065, 0.08)
    camera_data = bpy.data.cameras.new("Canonical wood review camera")
    camera = bpy.data.objects.new("Canonical wood review camera", camera_data)
    scene.collection.objects.link(camera)
    scene.camera = camera
    camera_data.type = "ORTHO"
    camera_data.ortho_scale = span * 1.24
    for name, location, energy, size in (
        ("soft key", (center[0] - span * 0.35, lo[1] - span * 0.9, center[2] + span * 0.65), 110, span * 0.7),
        ("fill", (center[0] + span * 0.45, lo[1] - span * 0.5, center[2] + span * 0.2), 35, span * 0.5),
    ):
        data = bpy.data.lights.new(name, "AREA")
        data.energy, data.shape, data.size = energy, "DISK", size
        light = bpy.data.objects.new(name, data)
        scene.collection.objects.link(light)
        light.location = location
        aim(light, center)
    views = {
        "front": (center[0], lo[1] - max(span, depth) * 1.8, center[2]),
        "oblique": (center[0] + span * 0.55, lo[1] - max(span, depth) * 1.45, center[2] + span * 0.32),
    }
    for name, location in views.items():
        camera.location = location
        aim(camera, center)
        scene.render.filepath = str(out / f"{slug}-{name}.png")
        bpy.ops.render.render(write_still=True)


for board_slug in ("beastmaker-1000", "metolius-wood-grips-compact-ii"):
    render_board(board_slug)
print("CANONICAL_WOOD_REVIEW_RENDERS", out)
