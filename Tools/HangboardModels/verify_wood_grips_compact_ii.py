"""Roundtrip actual runtime exports, verify IDs/texture/scale, render both."""
import json
from pathlib import Path
import sys
import bpy
from mathutils import Vector

ROOT=Path(__file__).resolve().parents[2]
OUT=Path(sys.argv[sys.argv.index("--")+1]).resolve() if "--" in sys.argv else ROOT/".context/epic-whale-wood-grips-compact-ii"
expected={h["id"] for h in json.loads((ROOT/"Hangboards/metolius-wood-grips-compact-ii/board.json").read_text())["holds"]}
results={}
for ext in ("glb","usdz"):
    bpy.ops.wm.open_mainfile(filepath=str(OUT/"wood-grips-compact-ii.blend"))
    for obj in list(bpy.data.objects):
        if obj.type=="MESH" and not obj.name.startswith("Studio"):
            bpy.data.objects.remove(obj,do_unlink=True)
    # Keep the image-free studio, but remove every source-scene material/image
    # that could otherwise conceal a missing texture in the exported artifact.
    for mat in list(bpy.data.materials):
        if mat.name!="Warm white studio":
            bpy.data.materials.remove(mat,do_unlink=True)
    for image in list(bpy.data.images):
        bpy.data.images.remove(image,do_unlink=True)
    assert len(bpy.data.images)==0,"Source images leaked into the import check"
    bpy.ops.object.select_all(action="DESELECT")
    if ext=="glb":
        bpy.ops.import_scene.gltf(filepath=str(OUT/f"wood-grips-compact-ii.{ext}"))
    else:
        bpy.ops.wm.usd_import(filepath=str(OUT/f"wood-grips-compact-ii.{ext}"))
    objects=[o for o in bpy.context.selected_objects if o.type=="MESH"]
    ids={o.get("hold_id",o.get("userProperties:hold_id",o.name.replace("_","-"))) for o in objects}
    assert expected.issubset(ids),(ext,expected-ids)
    assert len(objects)==20,(ext,len(objects))
    points=[o.matrix_world@Vector(v) for o in objects for v in o.bound_box]
    dims=[max(v[i] for v in points)-min(v[i] for v in points) for i in range(3)]
    expected_dims=(.610,.056,.157)
    tolerance_meters=1e-6  # One micrometer: allows float rounding, not size drift.
    assert all(abs(actual-expected)<tolerance_meters
               for actual,expected in zip(dims,expected_dims)),(ext,dims)
    textured=0
    for obj in objects:
        used={p.material_index for p in obj.data.polygons}
        for idx in used:
            mat=obj.data.materials[idx]
            assert mat.use_nodes
            images=[n.image for n in mat.node_tree.nodes if n.type=="TEX_IMAGE" and n.image]
            assert images,(ext,obj.name,"missing texture")
            # Blender lazily decodes imported packed images on first pixel access.
            for image in images:
                _=image.pixels[0]
            assert all(i.has_data for i in images),(ext,obj.name,"missing image data")
            assert any(i.size[0]==2048 for i in images),(ext,obj.name,"missing 2048 atlas")
        textured+=1
    scene=bpy.context.scene
    scene.camera.location=(.31,-1,.34)
    scene.camera.rotation_euler=(Vector((0,-.028,.0785))-scene.camera.location).to_track_quat("-Z","Y").to_euler()
    scene.render.filepath=str(OUT/f"{ext}-roundtrip.png")
    bpy.ops.render.render(write_still=True)
    results[ext]={"mesh_count":len(objects),"hold_ids_preserved":19,"textured_mesh_count":textured,
                  "bounds_meters":dims,"bounds_tolerance_meters":tolerance_meters,
                  "source_images_cleared_before_import":True,
                  "file_bytes":(OUT/f"wood-grips-compact-ii.{ext}").stat().st_size,
                  "roundtrip_render":f"{ext}-roundtrip.png"}
(OUT/"export-verification.json").write_text(json.dumps(results,indent=2)+"\n")
print("EXPORT_VERIFICATION",json.dumps(results))
