"""Contact-first model compiler boundary tests."""

from __future__ import annotations

import importlib
import json
import shutil
import subprocess
import tempfile
import textwrap
import unittest
from pathlib import Path
from types import SimpleNamespace


class ContactModelPackageTests(unittest.TestCase):
    def module(self):
        try:
            return importlib.import_module("contact_model_package")
        except ModuleNotFoundError as error:
            self.fail(f"contact-first model package compiler is missing: {error}")

    def test_board_loader_accepts_only_v3_contact_inventory(self) -> None:
        compiler = self.module()
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            current = root / "current.json"
            legacy = root / "legacy.json"
            current.write_text(json.dumps({"schemaVersion": 3, "contacts": [{"id": "left"}, {"id": "right"}]}))
            legacy.write_text(json.dumps({"schemaVersion": 2, "holds": [{"id": "left"}]}))

            self.assertEqual(
                compiler.load_logical_contact_ids(current),
                frozenset({"left", "right"}),
            )
            with self.assertRaisesRegex(ValueError, "schemaVersion must be 3"):
                compiler.load_logical_contact_ids(legacy)

    def test_compiler_rejects_unknown_descriptor_version_before_opening_scene(self) -> None:
        compiler = self.module()

        with self.assertRaisesRegex(ValueError, "descriptor_version must be 1 or 2"):
            compiler.compile_model_package(
                Path("source.blend"),
                Path("board.json"),
                Path("output"),
                descriptor_version=3,
            )

    def test_reusable_scene_must_declare_at_least_one_contact_slot(self) -> None:
        compiler = self.module()
        scene = SimpleNamespace(
            objects=(
                SimpleNamespace(type="MESH", get=lambda *_args, **_kwargs: None),
                SimpleNamespace(type="EMPTY", get=lambda *_args, **_kwargs: "ignored"),
            )
        )
        slot_ids = compiler._declared_contact_slot_ids(scene, imported=False)
        self.assertEqual(slot_ids, frozenset())
        with self.assertRaisesRegex(ValueError, "at least one contact slot"):
            compiler._require_reusable_contact_slots(slot_ids)
        self.assertEqual(
            compiler._require_reusable_contact_slots(frozenset({"edge"})),
            frozenset({"edge"}),
        )

    @unittest.skipUnless(shutil.which("blender"), "Blender is required for USDZ round-trip coverage")
    def test_compiled_usdz_ships_unbound_even_when_the_source_has_materials(self) -> None:
        """Exporting materials would violate the model material policy (AGENTS.md)."""
        compiler_path = Path(__file__).resolve().parent
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            script_path = root / "unbound_round_trip.py"
            script_path.write_text(_BLENDER_UNBOUND_ROUND_TRIP_SCRIPT, encoding="utf-8")
            result = subprocess.run(
                [
                    shutil.which("blender") or "blender",
                    "--background",
                    "--factory-startup",
                    "--python-exit-code",
                    "1",
                    "--python",
                    str(script_path),
                    "--",
                    str(compiler_path),
                    str(root / "materialed.blend"),
                    str(root / "board.json"),
                    str(root / "package"),
                ],
                capture_output=True,
                text=True,
                check=False,
            )
            self.assertEqual(result.returncode, 0, msg=result.stdout + result.stderr)
            self.assertIn("UNBOUND_ROUND_TRIP_OK", result.stdout)


_BLENDER_UNBOUND_ROUND_TRIP_SCRIPT = textwrap.dedent(
    """
    import json
    import sys
    import zipfile
    from pathlib import Path

    import bpy
    from pxr import Usd, UsdShade

    compiler_directory, blend_path, board_path, output_path = map(Path, sys.argv[-4:])
    sys.path.insert(0, str(compiler_directory))
    import contact_model_package as compiler

    bpy.ops.wm.read_factory_settings(use_empty=True)
    material = bpy.data.materials.new("authored-wood")
    material.use_nodes = True
    material.node_tree.nodes.get("Principled BSDF").inputs["Base Color"].default_value = (
        0.69, 0.49, 0.28, 1.0,
    )

    def add_cube(name, role, location, contact_id=None):
        bpy.ops.mesh.primitive_cube_add(size=1, location=location)
        item = bpy.context.active_object
        item.name = name
        item["role"] = role
        if contact_id is not None:
            item["contact_id"] = contact_id
        item.data.materials.append(material)

    add_cube("body", "body", (0, 0, 0))
    add_cube("contact-edge", "contact", (2, 0, 0), "edge")
    bpy.ops.wm.save_as_mainfile(filepath=str(blend_path))
    board_path.write_text(json.dumps({"schemaVersion": 3, "contacts": [{"id": "edge"}]}))
    compiler.compile_model_package(blend_path, board_path, output_path)

    usdz = output_path / "assets/primary.usdz"
    with zipfile.ZipFile(usdz) as archive:
        members = archive.namelist()
    assert all(Path(name).suffix in {".usd", ".usda", ".usdc"} for name in members), members
    stage = Usd.Stage.Open(str(usdz))
    prims = list(stage.Traverse())
    meshes = [prim for prim in prims if prim.GetTypeName() == "Mesh"]
    assert len(meshes) == 2, [str(prim.GetPath()) for prim in meshes]
    shading = [str(prim.GetPath()) for prim in prims if prim.IsA(UsdShade.Material) or prim.IsA(UsdShade.Shader)]
    assert not shading, shading
    bound = [
        str(prim.GetPath())
        for prim in meshes
        if UsdShade.MaterialBindingAPI(prim).ComputeBoundMaterial()[0]
    ]
    assert not bound, bound
    print("UNBOUND_ROUND_TRIP_OK", len(meshes))
    """
)


if __name__ == "__main__":
    unittest.main()
