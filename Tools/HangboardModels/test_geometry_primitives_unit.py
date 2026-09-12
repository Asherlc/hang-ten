"""Blender-free regressions for geometry helper call contracts."""

from __future__ import annotations

import ast
import importlib.util
import subprocess
import sys
import types
import unittest
from pathlib import Path


TOOLS = Path(__file__).resolve().parent
ROOT = TOOLS.parents[1]


def load_geometry_primitives():
    """Load the pure helper paths with minimal Blender import stubs."""
    module_name = "_geometry_primitives_unit_under_test"
    previous = {name: sys.modules.get(name) for name in ("bpy", "mathutils", module_name)}
    sys.modules["bpy"] = types.ModuleType("bpy")
    mathutils = types.ModuleType("mathutils")
    mathutils.Matrix = object
    mathutils.Vector = object
    sys.modules["mathutils"] = mathutils
    try:
        spec = importlib.util.spec_from_file_location(module_name, TOOLS / "geometry_primitives.py")
        assert spec is not None and spec.loader is not None
        module = importlib.util.module_from_spec(spec)
        sys.modules[module_name] = module
        spec.loader.exec_module(module)
        return module
    finally:
        for name, value in previous.items():
            if value is None:
                sys.modules.pop(name, None)
            else:
                sys.modules[name] = value


class _MeshData:
    def __init__(self):
        self.materials = []


class _MeshObject:
    def __init__(self):
        self.data = _MeshData()


class GeometryPrimitivesUnitTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.geometry_primitives = load_geometry_primitives()

    def test_mesh_factory_internal_type_error_is_not_retried(self):
        calls = []

        def factory(*args):
            calls.append(args)
            if len(args) == 4:
                raise TypeError("factory internal failure")
            raise AssertionError("factory must not be retried without materials")

        with self.assertRaisesRegex(TypeError, "factory internal failure"):
            self.geometry_primitives._create_mesh(
                "fixture", [(0, 0, 0)], [], ("wood",), mesh_factory=factory
            )
        self.assertEqual(1, len(calls))

    def test_legacy_mesh_factory_receives_materials_after_one_three_argument_call(self):
        calls = []
        mesh = _MeshObject()

        def factory(name, vertices, faces):
            calls.append((name, vertices, faces))
            return mesh

        result = self.geometry_primitives._create_mesh(
            "fixture", [(0, 0, 0)], [], ("wood",), mesh_factory=factory
        )

        self.assertIs(mesh, result)
        self.assertEqual([("fixture", [(0, 0, 0)], [])], calls)
        self.assertEqual(["wood"], mesh.data.materials)

    def test_material_binding_zips_are_strict(self):
        tree = ast.parse((TOOLS / "geometry_primitives.py").read_text(encoding="utf-8"))
        binding_zips = [
            node for node in ast.walk(tree)
            if isinstance(node, ast.Call)
            and isinstance(node.func, ast.Name)
            and node.func.id == "zip"
            and node.args
            and isinstance(node.args[0], ast.Name)
            and node.args[0].id in {"topology", "polygon_material_indices"}
        ]
        self.assertEqual(2, len(binding_zips))
        for call in binding_zips:
            self.assertTrue(
                any(
                    keyword.arg == "strict"
                    and isinstance(keyword.value, ast.Constant)
                    and keyword.value.value is True
                    for keyword in call.keywords
                )
            )

    def test_flash_recess_geometry_arguments_are_keyworded(self):
        tree = ast.parse((TOOLS / "tension_flash_board.py").read_text(encoding="utf-8"))
        build = next(node for node in tree.body if isinstance(node, ast.FunctionDef) and node.name == "build")
        recess_calls = [
            node for node in ast.walk(build)
            if isinstance(node, ast.Call) and isinstance(node.func, ast.Name) and node.func.id == "recess"
        ]
        self.assertTrue(recess_calls)
        required = {
            "name", "cx", "cy", "width", "height", "floor", "mouth", "radius",
            "back_fillet", "mouth_fillet",
        }
        for call in recess_calls:
            self.assertEqual(1, len(call.args), f"line {call.lineno}")
            names = {keyword.arg for keyword in call.keywords}
            self.assertTrue(required <= names, f"line {call.lineno}: {names}")

    def test_direct_non_blender_geometry_test_reports_a_successful_skip(self):
        result = subprocess.run(
            [sys.executable, str(TOOLS / "test_geometry_primitives.py")],
            cwd=ROOT,
            capture_output=True,
            text=True,
            check=False,
        )

        self.assertEqual(0, result.returncode, result.stderr)
        self.assertIn("GEOMETRY_PRIMITIVES_TEST skipped: requires Blender's bpy module", result.stdout)


if __name__ == "__main__":
    unittest.main()
