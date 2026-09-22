"""Explicit Zlagboard source preparation; run in Blender from repository root.

No geometry inference, repair, rescaling, or extra axis conversion. Import applies
GLB root +Y-up transform and Blender's +Z-up conversion once. Bake that evaluated
world matrix before deleting transform-only empties. Constant material image is
an explicit compatibility adaptation outside the unchanged package compiler.
"""
import hashlib
import json
import sys
import struct
import zlib
from pathlib import Path

HERE = Path(__file__).resolve().parent
if str(HERE) not in sys.path:
    sys.path.insert(0, str(HERE))
import bpy
from mathutils import Matrix, Vector


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def prepare(slug):
    source = HERE.parent / "source-delivery/models" / slug / (slug + ".glb")
    expected = {"zlagboard-evo": "bf3c44e8538a22ffc5c86ca6b7410ce58b265dd33f70328c205490c3069d2f8b", "zlagboard-pro-2-0": "e71482d155485acd5ad710f7fb8cf2ac2a055ef14a634a6026733f2e970f3b56"}[slug]
    assert digest(source) == expected
    output = HERE / slug
    output.mkdir(exist_ok=True)
    bpy.ops.wm.read_factory_settings(use_empty=True)
    bpy.ops.import_scene.gltf(filepath=str(source))
    meshes = [o for o in bpy.context.scene.objects if o.type == "MESH"]
    removed = [o.name for o in bpy.context.scene.objects if o.type != "MESH"]
    before = {}
    for obj in meshes:
        world = obj.matrix_world.copy()
        before[obj.name] = [list(world @ v.co) for v in obj.data.vertices]
        obj.data.transform(world)
        obj.parent = None
        obj.matrix_world = Matrix.Identity(4)
    for obj in list(bpy.context.scene.objects):
        if obj.type != "MESH":
            bpy.data.objects.remove(obj, do_unlink=True)
    max_delta = max((v.co - Vector(old)).length for obj in meshes for v, old in zip(obj.data.vertices, before[obj.name]))
    assert max_delta < 1e-7
    colors = {}
    material_adaptations = {}
    for material in bpy.data.materials:
        tree = material.node_tree
        bsdf = next(n for n in tree.nodes if n.type == "BSDF_PRINCIPLED")
        assert not bsdf.inputs["Base Color"].is_linked
        rgba = list(bsdf.inputs["Base Color"].default_value)
        colors[material.name] = rgba
        # Encode a constant PNG explicitly: GLB factor is linear RGB; PNG bytes
        # are sRGB. Do not feed encoded values back into a linear float image.
        to_srgb = lambda x: 12.92*x if x <= .0031308 else 1.055*x**(1/2.4)-.055
        to_linear = lambda x: x/12.92 if x <= .04045 else ((x+.055)/1.055)**2.4
        encoded = [round(to_srgb(x)*255) for x in rgba[:3]] + [round(rgba[3]*255)]
        decoded = [to_linear(x/255) for x in encoded[:3]] + [encoded[3]/255]
        error = max(abs(a-b) for a,b in zip(rgba,decoded))
        assert error <= .004
        def chunk(kind, data):
            return struct.pack(">I", len(data))+kind+data+struct.pack(">I",zlib.crc32(kind+data)&0xffffffff)
        png = (b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", struct.pack(">IIBBBBB",1,1,8,6,0,0,0))
               + chunk(b"sRGB",b"\x00") + chunk(b"IDAT",zlib.compress(b"\x00"+bytes(encoded))) + chunk(b"IEND",b""))
        texture_path = Path.cwd()/".context/hangboards-batch-05-astra-migration/prepared"/(slug+"-substrate.png")
        texture_path.parent.mkdir(parents=True,exist_ok=True)
        texture_path.write_bytes(png)
        image = bpy.data.images.load(str(texture_path))
        image.colorspace_settings.name = "sRGB"
        image.pack()
        material_adaptations[material.name] = {"format":"PNG RGBA8 sRGB", "encodedSRGB8":encoded,"decodedLinearRGBA":decoded,"maximumLinearChannelError":error,"linearChannelTolerance":.004,"textureSHA256":digest(texture_path)}
        texture = tree.nodes.new("ShaderNodeTexImage")
        texture.image = image
        tree.links.new(texture.outputs["Color"], bsdf.inputs["Base Color"])
    prepared = Path.cwd() / ".context/hangboards-batch-05-astra-migration/prepared" / (slug + ".blend")
    prepared.parent.mkdir(parents=True, exist_ok=True)
    bpy.ops.wm.save_as_mainfile(filepath=str(prepared), check_existing=False)
    report = {"sourcePath": str(source.relative_to(Path.cwd())), "sourceSHA256": expected, "preparedSHA256": digest(prepared), "preparedPath": str(prepared.relative_to(Path.cwd())), "blenderVersion": bpy.app.version_string, "removedTransformOnlyNodes": removed, "maximumWorldVertexDeltaMetres": max_delta, "geometryChanged": False, "coordinatePreparation": "GLB native import + root world matrix bake only; Blender +Z up, front -Y, metres. Compiler transports to +Y up, front +Z.", "materialAdaptation": "One constant PNG RGBA8 sRGB image per source material, explicitly encoded from linear GLB factor with <=0.004 linear-channel error; no generated grain or source image use.", "sourceMaterialLinearRGBA": colors, "materialConversions": material_adaptations, "mountingOmission": "Both sources already omit external metal frame, phone holder/bands, screws and mounting holes. No mounting topology to remove; this does not describe physical product absence.", "meshInventory": [{"name":o.name,"vertices":len(o.data.vertices),"polygons":len(o.data.polygons)} for o in sorted(meshes,key=lambda o:o.name)]}
    (output / "preparation-report.json").write_text(json.dumps(report, indent=2)+"\n")
    manifest = {"schemaVersion":1,"packageID": "zlagboard.evo" if slug == "zlagboard-evo" else "zlagboard.pro", "manufacturerPhysicalAuthority":{"publisher":"Zlagboard / Vertical-Life","evidencePacket":str(HERE.parent.relative_to(Path.cwd()))+"/REVIEW.md"},"historicalSource":{"status":"missing","notes":"The old app raster authoring source is not a native contact-tagged model. Immutable user delivery GLB is retained separately."},"auditedModelSource":{"provenanceType":"user-provided","authorization":"User authorized evidence-led native migration; exact evidence approved 2026-09-20. Explicit derivative preparation documented here; no model acceptance implied.","retainedPath":str(prepared.relative_to(Path.cwd())),"sha256":digest(prepared)},"supersessionRuling":"Prepared native derivative of hash-bound original GLB. Source root transforms are baked without geometry change; constant material image adaptation is explicit. Manufacturer facts and stable app IDs govern mapping."}
    (output / "source-manifest.json").write_text(json.dumps(manifest,indent=2)+"\n")


if __name__ == "__main__":
    for slug in sys.argv[sys.argv.index("--")+1:]:
        prepare(slug)
