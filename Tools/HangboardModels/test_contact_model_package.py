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

    def test_imported_material_gate_accepts_finite_constant_principled_pbr(self) -> None:
        """Removing Principled constants must reject an imported usable PBR material."""
        compiler = self.module()
        material = _constant_principled_material()

        compiler._require_image_materials(_mesh_with_material(material), "body")

    def test_imported_material_gate_rejects_materialless_and_empty_node_tree_branches(self) -> None:
        """Removing material-bearing face and node-tree checks must reject malformed imports."""
        compiler = self.module()

        with self.assertRaisesRegex(ValueError, "no material-bearing faces"):
            compiler._require_image_materials(
                SimpleNamespace(materials=(), polygons=()), "body"
            )
        with self.assertRaisesRegex(ValueError, "materialless"):
            compiler._require_image_materials(
                SimpleNamespace(
                    materials=(), polygons=(SimpleNamespace(material_index=0),)
                ),
                "body",
            )
        with self.assertRaisesRegex(ValueError, "no usable constant PBR material"):
            compiler._require_image_materials(
                _mesh_with_material(SimpleNamespace(node_tree=None)), "body"
            )

    def test_imported_material_gate_rejects_nonfinite_or_linked_constant_pbr_values(self) -> None:
        """Accepting NaN, transparent, or linked inputs would bless unusable materials."""
        compiler = self.module()
        nonfinite = _constant_principled_material(base_color=(float("nan"), 0.2, 0.3, 1.0))
        transparent = _constant_principled_material(alpha=0.0)
        linked = _constant_principled_material(base_color_is_linked=True)

        with self.assertRaisesRegex(ValueError, "no usable constant PBR material"):
            compiler._require_image_materials(_mesh_with_material(nonfinite), "body")
        with self.assertRaisesRegex(ValueError, "no usable constant PBR material"):
            compiler._require_image_materials(_mesh_with_material(transparent), "body")
        with self.assertRaisesRegex(ValueError, "no usable constant PBR material"):
            compiler._require_image_materials(_mesh_with_material(linked), "body")

    def test_imported_material_gate_preserves_broken_image_rejection(self) -> None:
        """Falling back to constants for a broken image path would hide a bad export."""
        compiler = self.module()
        material = _constant_principled_material(
            extra_nodes=(SimpleNamespace(type="TEX_IMAGE", image=None),)
        )

        with self.assertRaisesRegex(ValueError, "no usable image data"):
            compiler._require_image_materials(_mesh_with_material(material), "body")

    @unittest.skipUnless(shutil.which("blender"), "Blender is required for USDZ round-trip coverage")
    def test_constant_principled_pbr_survives_blender_usdz_round_trip(self) -> None:
        """Changing constant-PBR acceptance must retain usable importer-visible values."""
        compiler_path = Path(__file__).resolve().parent
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            script_path = root / "constant_pbr_round_trip.py"
            script_path.write_text(
                _BLENDER_CONSTANT_PBR_ROUND_TRIP_SCRIPT,
                encoding="utf-8",
            )
            result = subprocess.run(
                [
                    shutil.which("blender") or "blender",
                    "--background",
                    "--factory-startup",
                    "--python",
                    str(script_path),
                    "--",
                    str(compiler_path),
                    str(root / "constant-pbr.blend"),
                    str(root / "board.json"),
                    str(root / "package"),
                ],
                capture_output=True,
                text=True,
                check=False,
            )
            self.assertEqual(result.returncode, 0, msg=result.stdout + result.stderr)
            self.assertIn("CONSTANT_PBR_ROUND_TRIP_OK", result.stdout)


def _mesh_with_material(material: object) -> object:
    return SimpleNamespace(
        materials=(material,),
        polygons=(SimpleNamespace(material_index=0),),
    )


def _constant_principled_material(
    *,
    base_color: tuple[float, float, float, float] = (0.2, 0.4, 0.6, 0.8),
    alpha: float = 0.8,
    base_color_is_linked: bool = False,
    extra_nodes: tuple[object, ...] = (),
) -> object:
    def socket(value: object, *, is_linked: bool = False) -> object:
        return SimpleNamespace(default_value=value, is_linked=is_linked)

    principled = SimpleNamespace(
        type="BSDF_PRINCIPLED",
        inputs={
            "Base Color": socket(base_color, is_linked=base_color_is_linked),
            "Roughness": socket(0.55),
            "Metallic": socket(0.1),
            "Alpha": socket(alpha),
        },
    )
    return SimpleNamespace(node_tree=SimpleNamespace(nodes=(principled, *extra_nodes)))


_BLENDER_CONSTANT_PBR_ROUND_TRIP_SCRIPT = textwrap.dedent(
    """
    import json
    import math
    import sys
    from pathlib import Path

    import bpy

    compiler_directory, blend_path, board_path, output_path = map(Path, sys.argv[-4:])
    sys.path.insert(0, str(compiler_directory))
    import contact_model_package as compiler

    bpy.ops.wm.read_factory_settings(use_empty=True)
    bpy.ops.object.select_all(action="SELECT")
    bpy.ops.object.delete(use_global=False)
    material = bpy.data.materials.new("constant-pbr")
    material.use_nodes = True
    principled = material.node_tree.nodes.get("Principled BSDF")
    principled.inputs["Base Color"].default_value = (0.2, 0.4, 0.6, 0.8)
    principled.inputs["Roughness"].default_value = 0.55
    principled.inputs["Metallic"].default_value = 0.1
    principled.inputs["Alpha"].default_value = 0.8

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

    imported_scene = compiler._import_usdz_into_empty_scene(output_path / "assets/primary.usdz")
    values = []
    for item in imported_scene.objects:
        if item.type != "MESH":
            continue
        for imported_material in item.data.materials:
            nodes = imported_material.node_tree.nodes
            imported_principled = next(
                node for node in nodes if node.type == "BSDF_PRINCIPLED"
            )
            base_color = tuple(imported_principled.inputs["Base Color"].default_value)
            roughness = imported_principled.inputs["Roughness"].default_value
            metallic = imported_principled.inputs["Metallic"].default_value
            alpha = imported_principled.inputs["Alpha"].default_value
            values.extend(base_color)
            values.extend(
                (
                    roughness,
                    metallic,
                    alpha,
                )
            )
            assert all(abs(actual - expected) < 0.000001 for actual, expected in zip(base_color[:3], (0.2, 0.4, 0.6)))
            assert abs(roughness - 0.55) < 0.000001, roughness
            assert abs(metallic - 0.1) < 0.000001, metallic
            assert alpha == 1.0, alpha
    assert values and all(math.isfinite(float(value)) for value in values), values
    assert all(0.0 <= float(value) <= 1.0 for value in values), values
    print("CONSTANT_PBR_ROUND_TRIP_OK", values)
    """
)


if __name__ == "__main__":
    unittest.main()
