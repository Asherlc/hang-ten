"""Real-Blender regressions for model compiler tags and export round-tripping."""

from __future__ import annotations

import json
import shutil
import sys
import tempfile
import unittest
import warnings
from pathlib import Path

try:
    import bpy
except ModuleNotFoundError:
    if __name__ != "__main__":
        raise unittest.SkipTest("requires Blender's bpy module")
    raise


TOOLS = Path(__file__).resolve().parent
if str(TOOLS) not in sys.path:
    sys.path.insert(0, str(TOOLS))

from compile_model_package import compile_model_package, validate_tagged_scene


def reset_scene() -> None:
    bpy.ops.object.select_all(action="SELECT")
    bpy.ops.object.delete(use_global=False)


def mesh(name: str) -> object:
    data = bpy.data.meshes.new(name)
    data.from_pydata([(0, 0, 0), (1, 0, 0), (0, 1, 0)], [], [(0, 1, 2)])
    item = bpy.data.objects.new(name, data)
    bpy.context.scene.collection.objects.link(item)
    return item


def expect_value_error(fragment: str, action) -> None:
    try:
        action()
    except ValueError as error:
        assert fragment in str(error), (fragment, str(error))
    else:
        raise AssertionError(f"expected ValueError containing {fragment!r}")


reset_scene()
untagged_body = mesh("UntaggedBody")
expect_value_error(
    "role", lambda: validate_tagged_scene(bpy.context.scene, frozenset())
)

reset_scene()
body = mesh("Body")
body["role"] = "body"
unknown_hold = mesh("UnknownHold")
unknown_hold["role"] = "hold"
unknown_hold["hold_id"] = "unknown"
expect_value_error(
    "unknown hold_id",
    lambda: validate_tagged_scene(bpy.context.scene, frozenset({"known"})),
)

print("MODEL_COMPILER_BLENDER_TESTS passed")


reset_scene()
context_root = TOOLS.parents[1] / ".context"
context_root.mkdir(exist_ok=True)
temporary_root = Path(
    tempfile.mkdtemp(prefix=f"{TOOLS.parents[1].name}-model-compiler-test-", dir=context_root)
)
try:
    (temporary_root / "ownership.json").write_text(
        json.dumps(
            {
                "owner": TOOLS.parents[1].name,
                "resources": [str(temporary_root)],
                "external_resources": [],
            }
        ),
        encoding="utf-8",
    )
    image = bpy.data.images.new("Compiler test image", width=1, height=1)
    image.generated_color = (0.6, 0.4, 0.2, 1.0)
    material = bpy.data.materials.new("Compiler test material")
    with warnings.catch_warnings():
        warnings.simplefilter("ignore", DeprecationWarning)
        material.use_nodes = True
    texture = material.node_tree.nodes.new("ShaderNodeTexImage")
    texture.image = image
    shader = material.node_tree.nodes.get("Principled BSDF")
    material.node_tree.links.new(texture.outputs["Color"], shader.inputs["Base Color"])

    compiled_body = mesh("Body")
    compiled_body["role"] = "body"
    compiled_body.data.materials.append(material)
    compiled_hold = mesh("Hold")
    compiled_hold["role"] = "hold"
    compiled_hold["hold_id"] = "left"
    compiled_hold.data.materials.append(material)
    compiled_hold.location = (0.2, -0.1, 0.2)

    blend_path = temporary_root / "source.blend"
    bpy.ops.wm.save_as_mainfile(filepath=str(blend_path))
    board_json = temporary_root / "board.json"
    board_json.write_text('{"holds":[{"id":"left"}]}', encoding="utf-8")
    output = temporary_root / "compiled"

    descriptor = compile_model_package(blend_path, board_json, output)
    assert set(descriptor.holds) == {"left"}
    assert len(descriptor.holds["left"].node_ids) == 1
    assert {
        path.relative_to(output).as_posix()
        for path in output.rglob("*")
        if path.is_file()
    } == {"assets/primary.model.json", "assets/primary.usdz"}
finally:
    shutil.rmtree(temporary_root)
    assert not temporary_root.exists()

print("MODEL_COMPILER_EXPORT_TEST passed")
