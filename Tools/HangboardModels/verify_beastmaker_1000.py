#!/usr/bin/env python3
"""Verify and render the actual Beastmaker USDZ without loading source images.

rtk proxy blender --background --factory-startup --python-exit-code 1 \
  --python Tools/HangboardModels/verify_beastmaker_1000.py -- \
  --output .context/shaky-rat-beastmaker-1000/package

This verifier does not compile/promote a package or repair shape. Imported
objects receive only the known native-Blender-to-board rigid axis transform
for matched review cameras; their vertices/topology/materials stay unchanged.
"""

from __future__ import annotations

import argparse
from collections.abc import Mapping
import json
from pathlib import Path
import sys
import zipfile

import bpy

TOOLS = Path(__file__).resolve().parent
if str(TOOLS) not in sys.path:
    sys.path.insert(0, str(TOOLS))

import beastmaker_1000 as authored
import compile_model_package as compiler


def load_report(path: Path) -> dict[str, object]:
    """Read one JSON report without importing Blender state into the check."""
    try:
        report = json.loads(Path(path).read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        raise ValueError(f"report is not readable valid JSON: {path}") from error
    if not isinstance(report, Mapping):
        raise ValueError("report must be a JSON object")
    return dict(report)


def verify_report(
    report: Mapping[str, object], *, expected_ids: frozenset[str]
) -> dict[str, object]:
    """Enforce the Beastmaker report's fixed logical inventory and omissions."""
    if not isinstance(report, Mapping):
        raise ValueError("report must be an object")
    if len(expected_ids) != 22:
        raise ValueError("Beastmaker logical inventory must contain exactly 22 hold IDs")
    if report.get("hold_ids_preserved") != len(expected_ids):
        raise ValueError("report must preserve all 22 Beastmaker hold IDs")
    if report.get("hardware_mesh_count") != 0:
        raise ValueError("report must contain no hardware meshes")
    return dict(report)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--skip-renders", action="store_true")
    args = parser.parse_args(sys.argv[sys.argv.index("--")+1:] if "--" in sys.argv else [])
    package = args.output.resolve()
    out = package.parent
    assert out.parent == authored.ROOT/".context"
    assert out.name == authored.ROOT.name+"-beastmaker-1000"
    source = load_report(out/"model-report.json")
    expected = compiler.load_logical_hold_ids(authored.ROOT/"Hangboards/beastmaker-1000/board.json")
    model_path = package/"assets/primary.usdz"
    descriptor_path = package/"assets/primary.model.json"
    descriptor = load_report(descriptor_path)
    assert descriptor["coordinateFrame"] == authored.FRAME
    assert descriptor["modelSHA256"] == authored.sha(model_path)
    assert set(descriptor["holds"]) == set(expected)
    with zipfile.ZipFile(model_path) as archive:
        texture_members = [name for name in archive.namelist() if name.lower().endswith((".png", ".jpg", ".jpeg"))]
        assert texture_members, "USDZ must embed its texture bytes"
        assert all(len(archive.read(name)) > 0 for name in texture_members)

    bpy.ops.wm.read_factory_settings(use_empty=True)
    for material in list(bpy.data.materials):
        bpy.data.materials.remove(material, do_unlink=True)
    for image in list(bpy.data.images):
        bpy.data.images.remove(image, do_unlink=True)
    assert len(bpy.data.images) == 0
    assert "FINISHED" in bpy.ops.wm.usd_import(filepath=str(model_path), merge_parent_xform=True)
    scene = bpy.context.scene
    bindings = compiler.validate_tagged_scene(scene, expected, imported=True)
    snapshot = compiler._snapshot_scene(scene, bindings, transform_to_board_frame=True,
                                        require_imported_materials=True, require_triangles=True)
    by_name = {obj.name: obj for obj in scene.objects if obj.type == "MESH"}
    assert set(by_name) == {node["nodeID"] for node in descriptor["nodes"]}
    source_nodes = {item["nodeID"]: item for item in source["meshes"]}
    source_correspondence = compiler._imported_source_node_ids(scene, bindings)
    materials = []
    for binding in bindings:
        original = source_nodes[source_correspondence[binding.node_id]]
        assert original["role"] == binding.role
        assert original.get("holdID") == binding.hold_id
        descriptor_node = next(n for n in descriptor["nodes"] if n["nodeID"] == binding.node_id)
        assert descriptor_node["role"] == binding.role
        assert descriptor_node.get("holdID") == binding.hold_id
        obj = by_name[binding.node_id]
        for index in {p.material_index for p in obj.data.polygons}:
            material = obj.data.materials[index]
            images = [n.image for n in material.node_tree.nodes if n.type == "TEX_IMAGE" and n.image]
            assert images and all(image.has_data and min(image.size) > 0 for image in images)
            materials.append(dict(nodeID=obj.name, material=material.name,
                                  images=[dict(name=i.name, width=i.size[0], height=i.size[1]) for i in images]))
        # These explicit properties alias verified importer-visible metadata
        # for the shared authored-ray helper. They do not infer identities.
        obj["role"] = binding.role
        if binding.hold_id is not None:
            obj["hold_id"] = binding.hold_id
        obj.matrix_world = compiler._board_axis_transform()@obj.matrix_world
        obj.color = (.66, .66, .66, 1)
    objects = list(by_name.values())
    checks = authored.verify_model(objects, list(expected))
    assert checks["triangles"] == source["triangles"]
    for axis in ("min", "max"):
        assert all(abs(a-b) < 1e-6 for a, b in zip(checks["boundsMeters"][axis], descriptor["modelBounds"][axis]))
    views = []
    if not args.skip_renders:
        if scene.world is None:
            scene.world = bpy.data.worlds.new("Isolated export review world")
        camera, _ = authored.review_rig(source["renderer"]["samples"])
        for source_view in source["reviewViews"]:
            if source_view["file"] not in {"front.png", "three-quarter.png", "clay-detail.png"}:
                continue
            view = source_view["camera"]
            views.append(authored.render_view(out, "usdz-"+Path(source_view["file"]).stem, camera,
                         view["locationMeters"], view["targetMeters"], view["orthographicScaleMeters"],
                         view["resolution"], clay=source_view["engine"] == "BLENDER_WORKBENCH"))
    report = dict(boardID="beastmaker-1000", modelSHA256=authored.sha(model_path),
                  descriptorSHA256=authored.sha(descriptor_path), sourceBlendSHA256=source["sourceSHA256"],
                  compilerInputSHA256=source["compilerInput"]["sha256"], evidencePacketSHA256=source["evidencePacketSHA256"],
                  coordinateFrame=authored.FRAME, sourceImagesClearedBeforeImport=True,
                  embeddedTextureMembers=texture_members, materialChecks=materials,
                  texturedMeshCount=len({record["nodeID"] for record in materials}),
                  explicitTriangles=True, sourcePieceCorrespondence=source_correspondence,
                  exactDescriptorNodeInventory=True, reviewViews=views,
                  nativeSceneKitVerification="pending subsequent app integration task",
                  humanVisualApproval="pending", **checks)
    assert report["texturedMeshCount"] == 23
    report = verify_report(report, expected_ids=expected)
    (out/"export-verification.json").write_text(json.dumps(report, indent=2)+"\n")
    print("BEASTMAKER_EXPORT_VERIFIED", json.dumps({key: report[key] for key in (
        "modelSHA256", "descriptorSHA256", "boundsMeters", "triangles", "hold_ids_preserved",
        "texturedMeshCount", "hardware_mesh_count", "authoredHeadOnNearestHitCount")}))


if __name__ == "__main__":
    main()
