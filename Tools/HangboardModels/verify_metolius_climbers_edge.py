#!/usr/bin/env python3
"""Validate bore removal in the descriptor-bound shipped Climber's Edge USDZ.

Run inside Blender so the assertion is made against the actual imported USDZ,
not a source blend or compiler staging asset.
"""

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


BORE_CENTERS_METERS = (
    (-0.244, -0.069), (0.0, -0.069), (0.244, -0.069),
    (-0.260, -0.0169), (0.260, -0.0169),
    (-0.279, 0.04475), (0.0, 0.04475), (0.279, 0.04475),
)
EXPECTED_CAP_NODE_ID = "bore_free_body_caps_001"


def require_bore_free_results(results: Sequence[Mapping[str, object]]) -> None:
    """Require exactly the audited rays to hit the imported cap node."""
    if len(results) != len(BORE_CENTERS_METERS):
        raise ValueError("expected exactly eight bore-ray results")
    expected_centers = set(BORE_CENTERS_METERS)
    actual_centers = {
        (result.get("x"), result.get("z"))
        for result in results
    }
    if actual_centers != expected_centers:
        raise ValueError("bore-ray results do not match the audited centers")
    for result in results:
        if result.get("intersects") is not True:
            raise ValueError("a shipped USDZ bore ray remains open")
        if result.get("nodeID") != EXPECTED_CAP_NODE_ID:
            raise ValueError("a shipped USDZ bore ray did not hit the cap node")


def verify_shipped_package(package_root: Path) -> dict[str, object]:
    """Import the hash-bound package USDZ from an empty Blender scene."""
    try:
        import bpy
        import contact_model_package as compiler
        from mathutils import Vector
    except ImportError as error:
        raise RuntimeError("USDZ verification must run inside Blender") from error

    package = Path(package_root).resolve()
    model_path = package / "assets" / "primary.usdz"
    descriptor_path = package / "assets" / "primary.model.json"
    model_bytes = model_path.read_bytes()
    descriptor_value = json.loads(descriptor_path.read_text(encoding="utf-8"))
    descriptor = ModelDescriptorV1.from_json(descriptor_value)
    contact_ids = compiler.load_logical_contact_ids(package / "board.json")
    model_hash = hashlib.sha256(model_bytes).hexdigest()
    if descriptor.model_sha256 != model_hash:
        raise ValueError("descriptor model hash does not match the shipped USDZ")

    bpy.ops.wm.read_factory_settings(use_empty=True)
    if bpy.context.scene.objects or bpy.data.materials or bpy.data.images:
        raise ValueError("scene is not empty before shipped USDZ import")
    scene = compiler._import_usdz_into_empty_scene(model_path)
    nodes = compiler.validate_tagged_scene(scene, contact_ids, imported=True)
    snapshot = compiler._snapshot_scene(
        scene, nodes, transform_to_board_frame=True,
        require_imported_materials=True, require_triangles=True,
    )
    rebuilt = compile_descriptor(
        model_bytes, snapshot.nodes, snapshot.vertices_by_node_id, contact_ids,
    )
    if rebuilt.to_json() != descriptor_value:
        raise ValueError("descriptor does not match actual shipped USDZ triangles")
    depsgraph = bpy.context.evaluated_depsgraph_get()
    results: list[dict[str, object]] = []
    for x, z in BORE_CENTERS_METERS:
        hit, _, _, _, item, _ = bpy.context.scene.ray_cast(
            depsgraph, Vector((x, -0.2, z)), Vector((0, 1, 0)), distance=0.4
        )
        results.append({"x": x, "z": z, "intersects": hit, "nodeID": item.name if hit else None})
    require_bore_free_results(results)
    return {
        "package": str(package),
        "modelSHA256": model_hash,
        "descriptorModelSHA256": descriptor.model_sha256,
        "descriptorSHA256": hashlib.sha256(descriptor_path.read_bytes()).hexdigest(),
        "descriptorMatchesActualUSDZ": True,
        "nodeCount": len(nodes),
        "contactCount": len(contact_ids),
        "boreCenterResults": results,
    }


def _arguments(argv: Sequence[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--package-root",
        type=Path,
        default=Path(__file__).resolve().parents[2] / "Hangboards" / "metolius-climbers-edge",
    )
    parser.add_argument("--report", type=Path)
    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> int:
    raw = list(sys.argv[sys.argv.index("--") + 1 :]) if argv is None and "--" in sys.argv else list(sys.argv[1:] if argv is None else argv)
    arguments = _arguments(raw)
    result = verify_shipped_package(arguments.package_root)
    if arguments.report:
        arguments.report.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(f"verified {len(BORE_CENTERS_METERS)} shipped Climber's Edge bore rays hit {EXPECTED_CAP_NODE_ID}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
