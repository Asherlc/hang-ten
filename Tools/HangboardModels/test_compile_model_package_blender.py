"""Real-Blender regressions for model compiler tags and export round-tripping."""

from __future__ import annotations

import contextlib
import hashlib
import io
import json
import runpy
import shutil
import sys
import tempfile
import unittest
import warnings
import zipfile
from pathlib import Path

try:
    import bpy
except ModuleNotFoundError:
    if __name__ != "__main__":
        raise unittest.SkipTest("requires Blender's bpy module")
    raise


TOOLS = Path(__file__).resolve().parent


def assert_documented_cli_help_is_self_contained() -> None:
    """Catches relying on a caller to add the compiler directory to sys.path."""
    original_argv = sys.argv
    original_path = list(sys.path)
    output = io.StringIO()
    try:
        sys.path[:] = [entry for entry in sys.path if entry != str(TOOLS)]
        sys.modules.pop("model_descriptor", None)
        sys.argv = [str(TOOLS / "compile_model_package.py"), "--", "--help"]
        with contextlib.redirect_stdout(output):
            try:
                runpy.run_path(
                    str(TOOLS / "compile_model_package.py"), run_name="__main__"
                )
            except SystemExit as error:
                assert error.code == 0, error.code
            else:
                raise AssertionError("documented compiler --help did not exit")
    finally:
        sys.argv = original_argv
        sys.path[:] = original_path
    assert "--blend" in output.getvalue()


assert_documented_cli_help_is_self_contained()

if str(TOOLS) not in sys.path:
    sys.path.insert(0, str(TOOLS))

import compile_model_package as compiler

from compile_model_package import compile_model_package, validate_tagged_scene


def write_unordered_usdz(path: Path, layer_text: str, member_order: tuple[str, ...]) -> None:
    payloads = {
        "root.usda": layer_text.encode("utf-8"),
        "textures/a.bin": b"a",
        "textures/z.bin": b"z",
    }
    with zipfile.ZipFile(path, "w") as archive:
        for member in member_order:
            archive.writestr(member, payloads[member])


canonical_layer_a = '''#usda 1.0
(
    upAxis = "Y"
)
def Xform "Zeta" {}
def Xform "Alpha" {}
'''
canonical_layer_b = '''#usda 1.0
(
    upAxis = "Y"
)
def Xform "Alpha" {}
def Xform "Zeta" {}
'''
canonical_context_directory = TOOLS.parents[1] / ".context"
canonical_context_directory.mkdir(exist_ok=True)
canonical_fixture_directory = Path(
    tempfile.mkdtemp(
        prefix=f"{TOOLS.parents[1].name}-model-compiler-canonical-",
        dir=canonical_context_directory,
    )
)
try:
    (canonical_fixture_directory / "ownership.json").write_text(
        json.dumps(
            {
                "owner": TOOLS.parents[1].name,
                "resources": [str(canonical_fixture_directory)],
                "external_resources": [],
            }
        ),
        encoding="utf-8",
    )
    first_usdz = canonical_fixture_directory / "first.usdz"
    second_usdz = canonical_fixture_directory / "second.usdz"
    write_unordered_usdz(
        first_usdz,
        canonical_layer_a,
        ("textures/z.bin", "root.usda", "textures/a.bin"),
    )
    write_unordered_usdz(
        second_usdz,
        canonical_layer_b,
        ("textures/a.bin", "root.usda", "textures/z.bin"),
    )
    compiler._canonicalize_usdz(first_usdz)
    compiler._canonicalize_usdz(second_usdz)
    assert first_usdz.read_bytes() == second_usdz.read_bytes()
    with zipfile.ZipFile(first_usdz) as archive:
        assert archive.namelist() == sorted(archive.namelist())
        assert all(info.date_time == (1980, 1, 1, 0, 0, 0) for info in archive.infolist())
        assert all(
            (
                info.header_offset
                + 30
                + len(info.filename.encode("utf-8"))
                + len(info.extra)
            )
            % 64
            == 0
            for info in archive.infolist()
        )
finally:
    shutil.rmtree(canonical_fixture_directory)

print("MODEL_COMPILER_CANONICALIZATION_TEST passed")


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
unusable_mesh = mesh("UnusableImageMesh")
unusable_material = bpy.data.materials.new("Unusable image material")
with warnings.catch_warnings():
    warnings.simplefilter("ignore", DeprecationWarning)
    unusable_material.use_nodes = True
unusable_texture = unusable_material.node_tree.nodes.new("ShaderNodeTexImage")
unusable_image = bpy.data.images.new("Unloaded image", width=1, height=1)
unusable_image.source = "FILE"
unusable_image.filepath_raw = "/definitely/missing/model-compiler-image.png"
unusable_image.buffers_free()
unusable_texture.image = unusable_image
unusable_mesh.data.materials.append(unusable_material)
expect_value_error(
    "usable image data",
    lambda: compiler._require_image_materials(unusable_mesh.data, unusable_mesh.name),
)


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
    attachment_payload = (
        '[{"metadata":{"asset_role":"cord_passage","bore_index":1,'
        '"diameter_estimate_m":0.0072},"order":1,'
        '"position":[-0.2460000067949295,0.0,0.0],'
        '"sourceNodeID":"cord-passage-1"}]'
    )
    compiled_body["hang_ten_attachments_v1"] = attachment_payload
    compiled_body.data["hang_ten_attachments_v1"] = attachment_payload
    compiled_body.data.materials.append(material)
    compiled_hold = mesh("Hold")
    compiled_hold["role"] = "hold"
    compiled_hold["hold_id"] = "left"
    compiled_hold.data.materials.append(material)
    compiled_hold.location = (0.2, -0.1, 0.2)
    compiled_hold_piece = mesh("HoldPiece")
    compiled_hold_piece["role"] = "hold"
    compiled_hold_piece["hold_id"] = "left"
    compiled_hold_piece.data.materials.append(material)
    compiled_hold_piece.location = (0.4, -0.1, 0.2)

    blend_path = temporary_root / "source.blend"
    bpy.ops.wm.save_as_mainfile(filepath=str(blend_path))
    board_json = temporary_root / "board.json"
    board_json.write_text('{"holds":[{"id":"left"}]}', encoding="utf-8")
    output = temporary_root / "compiled-1"

    descriptor = compile_model_package(blend_path, board_json, output)
    assert set(descriptor.holds) == {"left"}
    assert len(descriptor.holds["left"].node_ids) == 2
    assert {
        path.relative_to(output).as_posix()
        for path in output.rglob("*")
        if path.is_file()
    } == {"assets/primary.model.json", "assets/primary.usdz"}

    imported = compiler._import_usdz_into_empty_scene(
        output / "assets" / "primary.usdz"
    )
    imported_body = next(
        item
        for item in imported.objects
        if compiler._object_property(item, "role", imported=True) == "body"
    )
    exported_payload = compiler._object_property(
        imported_body, "hang_ten_attachments_v1", imported=True
    )
    if exported_payload is None:
        exported_payload = compiler._object_property(
            imported_body.data, "hang_ten_attachments_v1", imported=True
        )
    assert exported_payload == attachment_payload

    output_2 = temporary_root / "compiled-2"
    descriptor_2 = compile_model_package(blend_path, board_json, output_2)
    model_1 = (output / "assets" / "primary.usdz").read_bytes()
    model_2 = (output_2 / "assets" / "primary.usdz").read_bytes()
    assert model_1 == model_2, (
        hashlib.sha256(model_1).hexdigest(), hashlib.sha256(model_2).hexdigest()
    )
    assert (
        output / "assets" / "primary.model.json"
    ).read_bytes() == (
        output_2 / "assets" / "primary.model.json"
    ).read_bytes()
    assert descriptor.to_json() == descriptor_2.to_json()

    # The supplied model packages use a Principled material with no image
    # texture. A renderer-visible material remains required, but image-backed
    # wood is not the only valid model material contract.
    reset_scene()
    untextured_material = bpy.data.materials.new("Untextured compiler material")
    with warnings.catch_warnings():
        warnings.simplefilter("ignore", DeprecationWarning)
        untextured_material.use_nodes = True
    untextured_body = mesh("UntexturedBody")
    untextured_body["role"] = "body"
    untextured_body.data.materials.append(untextured_material)
    untextured_hold = mesh("UntexturedHold")
    untextured_hold["role"] = "hold"
    untextured_hold["hold_id"] = "untextured-left"
    untextured_hold.data.materials.append(untextured_material)
    untextured_hold.location = (0.2, 0.1, 0.2)
    untextured_blend = temporary_root / "untextured-source.blend"
    bpy.ops.wm.save_as_mainfile(filepath=str(untextured_blend))
    untextured_board = temporary_root / "untextured-board.json"
    untextured_board.write_text('{"holds":[{"id":"untextured-left"}]}', encoding="utf-8")
    untextured_output = temporary_root / "compiled-untextured"
    untextured_descriptor = compile_model_package(
        untextured_blend, untextured_board, untextured_output
    )
    assert set(untextured_descriptor.holds) == {"untextured-left"}
    assert {
        path.relative_to(untextured_output).as_posix()
        for path in untextured_output.rglob("*")
        if path.is_file()
    } == {"assets/primary.model.json", "assets/primary.usdz"}
finally:
    shutil.rmtree(temporary_root)
    assert not temporary_root.exists()

print("MODEL_COMPILER_EXPORT_TEST passed")
