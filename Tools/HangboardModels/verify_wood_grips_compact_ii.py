"""Verify the actual compiler-produced Compact II USDZ package.

This does not load or modify the source ``.blend``. The generic compiler has
already checked source-to-USDZ stability; this verifier checks the bytes and
the fresh importer-visible scene. The Compact evidence does not establish an
overall body depth, so this tool deliberately does not assert one.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import sys

import bpy


TOOLS = Path(__file__).resolve().parent
if str(TOOLS) not in sys.path:
    sys.path.insert(0, str(TOOLS))

import compile_model_package as compiler


ROOT = Path(__file__).resolve().parents[2]
parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument(
    "output",
    nargs="?",
    type=Path,
    default=ROOT / ".context" / f"{ROOT.name}-wood-grips-compact-ii",
)
parser.add_argument("--format", choices=("usdz",), action="append")
parser.add_argument("--skip-renders", action="store_true")
args = parser.parse_args(sys.argv[sys.argv.index("--") + 1 :] if "--" in sys.argv else [])


def package_paths(package: Path) -> tuple[Path, Path]:
    """Return only the compiler-owned USDZ and descriptor paths."""
    root = Path(package).resolve()
    if root.is_symlink() or not root.is_dir():
        raise ValueError(f"package directory must be a regular directory: {root}")
    model_path = root / "assets" / "primary.usdz"
    descriptor_path = root / "assets" / "primary.model.json"
    expected_assets = {"assets/primary.model.json", "assets/primary.usdz"}
    actual_assets = {
        path.relative_to(root).as_posix()
        for path in root.rglob("*")
        if path.is_file() and not path.is_symlink()
    }
    if actual_assets != expected_assets:
        raise ValueError("compiler package must contain only its USDZ and descriptor assets")
    for path in (model_path, descriptor_path):
        if path.is_symlink() or not path.is_file():
            raise ValueError(f"compiler package is missing required asset: {path}")
    return model_path, descriptor_path


def load_json_object(path: Path) -> dict[str, object]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        raise ValueError(f"JSON document is not readable: {path}") from error
    if not isinstance(value, dict):
        raise ValueError(f"JSON document must be an object: {path}")
    return value


def imported_material_checks(bindings: tuple[object, ...]) -> list[dict[str, object]]:
    """Record the image-bearing material actually attached to every mesh."""
    by_name = {item.name: item for item in bpy.context.scene.objects if item.type == "MESH"}
    checks: list[dict[str, object]] = []
    for binding in bindings:
        mesh = by_name[binding.node_id].data
        used_indexes = {polygon.material_index for polygon in mesh.polygons}
        if not used_indexes:
            raise ValueError(f"imported mesh {binding.node_id} has no material-bearing faces")
        for index in used_indexes:
            if index >= len(mesh.materials) or mesh.materials[index] is None:
                raise ValueError(f"imported mesh {binding.node_id} is materialless")
            material = mesh.materials[index]
            images = [
                node.image
                for node in material.node_tree.nodes
                if node.type == "TEX_IMAGE" and node.image is not None
            ]
            if not images:
                raise ValueError(f"imported mesh {binding.node_id} has no image material")
            for image in images:
                _ = image.pixels[0]
            if not all(image.has_data and min(image.size) > 0 for image in images):
                raise ValueError(f"imported mesh {binding.node_id} has unusable image data")
            checks.append(
                {
                    "nodeID": binding.node_id,
                    "material": material.name,
                    "images": [
                        {"name": image.name, "width": image.size[0], "height": image.size[1]}
                        for image in images
                    ],
                }
            )
    return checks


def verify_package(package: Path, *, skip_renders: bool) -> dict[str, object]:
    """Reimport one compiler package and return its actual-export report."""
    if not skip_renders:
        raise ValueError(
            "Compact actual-export rendering awaits a reviewed source rig; use --skip-renders"
        )
    model_path, descriptor_path = package_paths(package)
    expected = compiler.load_logical_hold_ids(
        ROOT / "Hangboards/metolius-wood-grips-compact-ii/board.json"
    )
    if len(expected) != 19:
        raise ValueError("Compact II logical inventory must contain exactly 19 hold IDs")
    descriptor = load_json_object(descriptor_path)

    bpy.ops.wm.read_factory_settings(use_empty=True)
    for material in list(bpy.data.materials):
        bpy.data.materials.remove(material, do_unlink=True)
    for image in list(bpy.data.images):
        bpy.data.images.remove(image, do_unlink=True)
    if bpy.data.images:
        raise ValueError("source images leaked into the import check")
    result = bpy.ops.wm.usd_import(filepath=str(model_path), merge_parent_xform=True)
    if "FINISHED" not in result:
        raise ValueError("USDZ import did not finish")

    scene = bpy.context.scene
    bindings = compiler.validate_tagged_scene(scene, expected, imported=True)
    snapshot = compiler._snapshot_scene(
        scene,
        bindings,
        transform_to_board_frame=True,
        require_imported_materials=True,
        require_triangles=True,
    )
    actual_descriptor = compiler.compile_descriptor(
        model_path.read_bytes(),
        snapshot.nodes,
        snapshot.vertices_by_node_id,
        expected,
    ).to_json()
    if descriptor != actual_descriptor:
        raise ValueError("descriptor does not exactly describe the actual USDZ bytes")

    objects = {item.name: item for item in scene.objects if item.type == "MESH"}
    if set(objects) != {binding.node_id for binding in bindings}:
        raise ValueError("USDZ contains unbound mesh geometry")
    material_checks = imported_material_checks(bindings)
    triangles = sum(
        len(polygon.vertices) - 2
        for item in objects.values()
        for polygon in item.data.polygons
    )
    if triangles >= 150_000:
        raise ValueError("Compact II actual USDZ exceeds its recorded triangle ceiling")
    ids = {binding.hold_id for binding in bindings if binding.role == "hold"}
    if ids != set(expected):
        raise ValueError("actual USDZ did not preserve the exact Compact II hold inventory")
    report = {
        "boardID": "metolius-wood-grips-compact-ii",
        "format": "usdz",
        "modelSHA256": hashlib.sha256(model_path.read_bytes()).hexdigest(),
        "descriptorSHA256": hashlib.sha256(descriptor_path.read_bytes()).hexdigest(),
        "coordinateFrame": descriptor["coordinateFrame"],
        "modelBounds": descriptor["modelBounds"],
        "exactDescriptorForActualUSDZ": True,
        "sourceImagesClearedBeforeImport": True,
        "meshCount": len(bindings),
        "hold_ids_preserved": len(expected & ids),
        "hardware_mesh_count": 0,
        "texturedMeshCount": len({record["nodeID"] for record in material_checks}),
        "materialChecks": material_checks,
        "triangles": triangles,
        "triangleCeiling": 150_000,
        "explicitTriangles": True,
        "reviewViews": [],
        "rendersSkipped": True,
    }
    if report["hold_ids_preserved"] != len(expected):
        raise ValueError("actual USDZ did not preserve all Compact II hold IDs")
    if report["texturedMeshCount"] != len(bindings):
        raise ValueError("every Compact II mesh must carry an imported image material")
    return report


def main() -> int:
    if args.format not in (None, ["usdz"]):
        raise ValueError("only the compiler-produced USDZ format is supported")
    package = args.output.resolve()
    report = verify_package(package, skip_renders=args.skip_renders)
    report_path = package.parent / "export-verification.json"
    report_path.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print("COMPACT_EXPORT_VERIFIED", json.dumps(report, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
