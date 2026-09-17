#!/usr/bin/env python3
"""Import a GLB file into Blender and save as .blend."""
import sys
import bpy

def convert(glb_path: str, blend_path: str) -> None:
    bpy.ops.wm.read_factory_settings(use_empty=True)
    bpy.ops.import_scene.gltf(filepath=glb_path)
    bpy.ops.wm.save_as_mainfile(filepath=blend_path, check_existing=False)

if __name__ == "__main__":
    convert(sys.argv[-2], sys.argv[-1])
