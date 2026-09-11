"""Semantic snapshot regression tests for the shared Blender geometry helpers.

Run with Blender from the repository root::

    blender --background --factory-startup --python-exit-code 1 \
      --python Tools/HangboardModels/test_geometry_primitives.py

The test deliberately snapshots authored data rather than image pixels.  Review
objects are explicitly marked non-exportable and are required to remain outside
the model set.
"""

from __future__ import annotations

import json
import sys
import unittest
from pathlib import Path

try:
    import bpy
except ModuleNotFoundError:
    bpy = None

TOOLS = Path(__file__).resolve().parent
if str(TOOLS) not in sys.path:
    sys.path.insert(0, str(TOOLS))

if bpy is not None:
    from geometry_primitives import (  # noqa: E402
        create_passage,
        create_recess,
        create_rounded_body,
        create_stepped_edge,
        make_review_rig,
        semantic_snapshot,
        split_contact_surface,
        tag_piece,
    )


def _reset() -> None:
    bpy.ops.object.select_all(action="SELECT")
    bpy.ops.object.delete(use_global=False)
    for datablocks in (bpy.data.meshes, bpy.data.materials, bpy.data.cameras, bpy.data.lights):
        for item in list(datablocks):
            if item.users == 0:
                datablocks.remove(item)


def _material(name: str):
    material = bpy.data.materials.new(name)
    material.use_nodes = True
    return material


def _image_material(name: str):
    material = _material(name)
    image = bpy.data.images.new(name + " image", width=1, height=1)
    image.generated_color = (0.2, 0.3, 0.4, 1.0)
    texture = material.node_tree.nodes.new("ShaderNodeTexImage")
    texture.image = image
    shader = material.node_tree.nodes.get("Principled BSDF")
    material.node_tree.links.new(texture.outputs["Color"], shader.inputs["Base Color"])
    return material


def main() -> None:
    if bpy is None:
        raise unittest.SkipTest("requires Blender's bpy module")
    _reset()
    wood = _image_material("semantic wood")
    body = create_rounded_body(
        "semantic-body",
        [(0, 0, 0), (1, 0, 0), (1, 1, 0), (0, 1, 0)],
        [(0, 1, 2, 3)],
        materials=(wood,),
    )
    tag_piece(body, "body", coordinate_frame="hang-ten-board-v1")
    hold = create_recess(
        "semantic-hold",
        [(0.2, 0.2, 0), (0.8, 0.2, 0), (0.8, 0.8, 0), (0.2, 0.8, 0)],
        [(0, 1, 2, 3)],
        materials=(wood,),
    )
    tag_piece(hold, "hold", "semantic-hold", coordinate_frame="hang-ten-board-v1")
    before = semantic_snapshot(bpy.context.scene)
    before_by_name = {item["name"]: item for item in before["objects"]}

    # The remaining families are deliberately exercised through their public
    # contracts; all must preserve authored coordinate/topology inputs.
    stepped = create_stepped_edge(
        "semantic-stepped",
        [(0, 0, 0), (1, 0, 0), (1, 1, 0), (0, 1, 0)],
        [(0, 1, 2, 3)],
        materials=(wood,),
    )
    passage = create_passage(
        "semantic-passage",
        [(0, 0, 0), (0, 1, 0), (0, 0, 1)],
        [(0, 1, 2)],
        materials=(wood,),
    )
    tag_piece(stepped, "hold", "semantic-stepped")
    tag_piece(passage, "body")
    split_contact_surface(hold, ("semantic-hold",))
    camera, _ = make_review_rig(owner="geometry-primitives-test")
    after = semantic_snapshot(bpy.context.scene)

    after_by_name = {item["name"]: item for item in after["objects"]}
    for name, item in before_by_name.items():
        assert after_by_name[name] == item, name
    assert all(item["role"] in {"body", "hold"} for item in after["objects"] if item["export"])
    review_names = {camera.name, "ReviewKey", "ReviewFill", "ReviewRim"}
    assert all(not item["export"] for item in after["objects"] if item["name"] in review_names)
    assert after["reviewObjectNames"] == sorted(review_names)
    assert after["materialImageBytes"] == before["materialImageBytes"]
    print("GEOMETRY_PRIMITIVES_TEST passed", json.dumps(after, sort_keys=True))


if __name__ == "__main__":
    main()
