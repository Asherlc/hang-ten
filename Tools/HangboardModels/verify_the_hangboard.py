#!/usr/bin/env python3
"""Verify the exact shipped The Hangboard USDZ from an empty Blender scene."""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from collections.abc import Mapping, Sequence
from pathlib import Path

_TOOLS = Path(__file__).resolve().parent
if str(_TOOLS) not in sys.path:
    sys.path.insert(0, str(_TOOLS))

from contact_model_descriptor import ModelDescriptorV1, compile_descriptor


EXPECTED_CONTACT_IDS = (
    "jug-left", "jug-right", "sloper-40-center",
    "edge-40-left", "edge-30-left", "edge-25-left",
    "edge-40-right", "edge-30-right", "edge-25-right",
    "edge-20-left", "edge-15-left", "edge-10-left",
    "edge-20-right", "edge-15-right", "edge-10-right",
)
MOUNTING_CAP_CENTERS_METERS = (
    (-0.258, 0.014), (-0.030, 0.014), (0.030, 0.014), (0.258, 0.014),
    (-0.258, -0.042), (-0.030, -0.042), (0.030, -0.042), (0.258, -0.042),
)
EXPECTED_CAP_NODE_ID = "mounting_hardware_omission_caps_001"


def require_hardware_free_results(results: Sequence[Mapping[str, object]]) -> None:
    """Require every reviewed hardware location to resolve to the body cap."""
    if len(results) != len(MOUNTING_CAP_CENTERS_METERS):
        raise ValueError("expected exactly eight mounting-cap ray results")
    if {(item.get("x"), item.get("z")) for item in results} != set(MOUNTING_CAP_CENTERS_METERS):
        raise ValueError("mounting-cap ray results do not match reviewed centers")
    for result in results:
        if result.get("intersects") is not True:
            raise ValueError("a shipped USDZ mounting-hardware cover is missing")
        if result.get("nodeID") != EXPECTED_CAP_NODE_ID:
            raise ValueError("a shipped USDZ mounting-hardware ray did not hit the cap node")


def verify_shipped_package(package_root: Path) -> dict[str, object]:
    """Hash-check, cleanly reimport, and rebuild the shipped descriptor."""
    try:
        import bpy
        from mathutils import Vector
        import contact_model_package as compiler
    except ImportError as error:
        raise RuntimeError("USDZ verification must run inside Blender") from error

    package = Path(package_root).resolve()
    files = {path.relative_to(package).as_posix() for path in package.rglob("*") if path.is_file()}
    if files != {"board.json", "assets/primary.usdz", "assets/primary.model.json"}:
        raise ValueError(f"model-only package inventory mismatch: {sorted(files)}")
    model_path = package / "assets/primary.usdz"
    descriptor_path = package / "assets/primary.model.json"
    model_bytes = model_path.read_bytes()
    descriptor_value = json.loads(descriptor_path.read_text(encoding="utf-8"))
    descriptor = ModelDescriptorV1.from_json(descriptor_value)
    if descriptor.model_sha256 != hashlib.sha256(model_bytes).hexdigest():
        raise ValueError("descriptor model hash does not match shipped USDZ")
    if tuple(descriptor.contacts) != tuple(sorted(EXPECTED_CONTACT_IDS)):
        raise ValueError("descriptor contacts do not match The Hangboard inventory")

    bpy.ops.wm.read_factory_settings(use_empty=True)
    if bpy.context.scene.objects or bpy.data.materials or bpy.data.images:
        raise ValueError("scene is not empty before shipped USDZ import")
    scene = compiler._import_usdz_into_empty_scene(model_path)
    nodes = compiler.validate_tagged_scene(scene, frozenset(EXPECTED_CONTACT_IDS), imported=True)
    snapshot = compiler._snapshot_scene(
        scene, nodes, transform_to_board_frame=True,
        require_imported_materials=True, require_triangles=True,
    )
    rebuilt = compile_descriptor(model_bytes, snapshot.nodes, snapshot.vertices_by_node_id, frozenset(EXPECTED_CONTACT_IDS))
    if rebuilt.to_json() != descriptor_value:
        raise ValueError("descriptor does not match actual shipped USDZ triangles")
    depsgraph = bpy.context.evaluated_depsgraph_get()
    results = []
    for x, z in MOUNTING_CAP_CENTERS_METERS:
        hit, _, _, _, item, _ = scene.ray_cast(depsgraph, Vector((x, 0.1, z)), Vector((0, -1, 0)), distance=0.2)
        results.append({"x": x, "z": z, "intersects": hit, "nodeID": item.name if hit else None})
    require_hardware_free_results(results)
    return {
        "status": "verified",
        "cleanReimport": True,
        "descriptorMatchesActualUSDZ": True,
        "modelSHA256": descriptor.model_sha256,
        "descriptorSHA256": hashlib.sha256(descriptor_path.read_bytes()).hexdigest(),
        "nodeCount": len(descriptor.nodes),
        "contactCount": len(descriptor.contacts),
        "hardwareCoverResults": results,
    }


def _arguments(argv: Sequence[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--package-root", type=Path, default=Path(__file__).resolve().parents[2] / "Hangboards/the-hangboard")
    parser.add_argument("--report", type=Path, required=True)
    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> int:
    raw = list(sys.argv[sys.argv.index("--") + 1:]) if argv is None and "--" in sys.argv else list(sys.argv[1:] if argv is None else argv)
    arguments = _arguments(raw)
    arguments.report.write_text(json.dumps(verify_shipped_package(arguments.package_root), indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
