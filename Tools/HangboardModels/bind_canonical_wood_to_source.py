#!/usr/bin/env python3
"""Refresh one authored model source with the committed canonical wood image."""

from __future__ import annotations

import argparse
from pathlib import Path
import sys

import bpy


TOOLS = Path(__file__).resolve().parent
if str(TOOLS) not in sys.path:
    sys.path.insert(0, str(TOOLS))

import canonical_neutral_wood


parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument("--blend", type=Path, required=True)
args = parser.parse_args(sys.argv[sys.argv.index("--") + 1 :] if "--" in sys.argv else [])
blend = args.blend.resolve()
if blend.is_symlink() or not blend.is_file():
    raise ValueError(f"source blend must be a regular file: {blend}")
bpy.ops.wm.open_mainfile(filepath=str(blend))
materials = []
for item in bpy.context.scene.objects:
    if item.type == "MESH":
        materials.extend(material for material in item.data.materials if material is not None)
if not materials:
    raise ValueError("authored source contains no mesh materials")
canonical_neutral_wood.attach_to_materials(dict.fromkeys(materials))
bpy.ops.wm.save_as_mainfile(filepath=str(blend))
print(
    "CANONICAL_WOOD_SOURCE_BOUND",
    f"blend={blend}",
    f"texture={canonical_neutral_wood.CANONICAL_TEXTURE_NAME}",
    f"dimensions={canonical_neutral_wood.WIDTH}x{canonical_neutral_wood.HEIGHT}",
)
