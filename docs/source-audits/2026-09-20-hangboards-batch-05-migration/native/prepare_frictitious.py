"""Explicit Frictitious body-only mounting omission; immutable contact geometry.
Run in Blender from repository root; no automatic topology repair.
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



def omit_mounting_openings(obj, slug):
    """Surgical edit of seven known authored body bores, not hole detection.

    Centers/radii come from immutable mounting-interface.json/products.py.
    Source geometry.Unit.hole writes a48-segment ellipse tube between the front
    support plane and rear Y0. Delete its96triangles and cap each exact loop.
    No contact mesh is touched. All existing coordinates/normals outside those
    specific mouth vertices remain unchanged.
    """
    import math
    spec=json.loads((HERE.parent/'source-delivery/models'/slug/'mounting-interface.json').read_text())
    mesh=obj.data
    vertices=[tuple(v.co) for v in mesh.vertices]
    normals=[tuple(v.vector) for v in mesh.corner_normals]
    faces=[list(p.vertices) for p in mesh.polygons]
    face_normals=[[normals[i] for i in p.loop_indices] for p in mesh.polygons]
    smooth=[p.use_smooth for p in mesh.polygons]
    records=[]
    for opening in spec['openings']:
        cx,_,cz=opening['centerSourceMeters'];rx=opening['radiusMm']/1000;rz=opening['radiusZMm']/1000
        # Published authoring definitions: hole surfaces are locally planar.
        fy=(-.02615 if slug.endswith('7') else -.022 if abs(cx)>.28 else -.037 if abs(cx)>.12 else -.026)
        ring={i for i,(x,y,z) in enumerate(vertices) if abs(((x-cx)/rx)**2+((z-cz)/rz)**2-1)<2e-5 and abs(y)<.06}
        front={i for i in ring if abs(vertices[i][1]-fy)<1e-7}
        back={i for i in ring if abs(vertices[i][1])<1e-7}
        unique = lambda ids: {tuple(round(v,8) for v in vertices[i]): i for i in sorted(ids)}
        front_unique=unique(front);back_unique=unique(back)
        assert len(front_unique)==len(back_unique)==48, (slug,cx,cz,len(front_unique),len(back_unique))
        tubes={j for j,f in enumerate(faces) if set(f)<=ring and set(f)&front and set(f)&back}
        assert len(tubes)==96,(slug,cx,cz,len(tubes))
        keep=[j for j in range(len(faces)) if j not in tubes]
        faces=[faces[j] for j in keep];face_normals=[face_normals[j] for j in keep];smooth=[smooth[j] for j in keep]
        # Restore plane normals at the filled mouth, removing tube influence.
        for f,ns in zip(faces,face_normals):
            for k,idx in enumerate(f):
                if idx in front:ns[k]=(0,-1,0)
                elif idx in back:ns[k]=(0,1,0)
        for ids,y,normal in [(front_unique.values(),fy,(0,-1,0)),(back_unique.values(),0,(0,1,0))]:
            loop=sorted(ids,key=lambda i: math.atan2((vertices[i][2]-cz)/rz,(vertices[i][0]-cx)/rx))
            center=len(vertices);vertices.append((cx,y,cz))
            for i in range(48):
                tri=[center,loop[i],loop[(i+1)%48]]
                if y==0:tri.reverse()
                faces.append(tri);face_normals.append([normal]*3);smooth.append(True)
        records.append({'centerSourceMetres':[cx,0,cz],'frontSupportYMetres':fy,'removedTubeTriangles':96,'addedCapTriangles':96,'authority':'source-delivery mounting-interface.json and original analytic products.py; mounting omission required by native migration contract'})
    material=mesh.materials[0]
    replacement=bpy.data.meshes.new(mesh.name+'-mounting-omitted')
    replacement.from_pydata(vertices,[],faces);replacement.materials.append(material)
    for polygon,value in zip(replacement.polygons,smooth):polygon.use_smooth=value
    replacement.normals_split_custom_set([n for group in face_normals for n in group])
    obj.data=replacement
    return records


def reconcile_megalith_step_ownership():
    """Reassign one explicit source strip, never change its triangles/normals.

    products.py gives the lower right opening inclusive ranges [147,229]20mm
    and [229,311]15mm. A strip centered exactly229 was given to the first range,
    unlike its mirrored left counterpart. The approved M2 symmetric steps
    establish that the mirrored boundary owns this strip as15mm on both sides.
    """
    source=bpy.data.objects['hold--right-edge-20'];target=bpy.data.objects['hold--right-edge-15']
    def extract(obj):
        m=obj.data;ns=[tuple(n.vector) for n in m.corner_normals]
        return [tuple(v.co) for v in m.vertices],[(list(p.vertices),[ns[i] for i in p.loop_indices],p.use_smooth) for p in m.polygons]
    sv,sf=extract(source);tv,tf=extract(target)
    selected=[f for f in sf if max(sv[i][0] for i in f[0])>.2290001]
    assert len(selected)==18, len(selected)
    transferred=[]
    for face,normals,smooth in selected:
        offset=len(tv);tv.extend(sv[i] for i in face)
        tf.append((list(range(offset,offset+3)),normals,smooth));transferred.append([sv[i] for i in face])
    sf=[f for f in sf if f not in selected]
    for obj,vertices,faces in [(source,sv,sf),(target,tv,tf)]:
        used=sorted({i for face,_,_ in faces for i in face});remap={old:new for new,old in enumerate(used)}
        vertices=[vertices[i] for i in used]
        faces=[([remap[i] for i in face],normals,smooth) for face,normals,smooth in faces]
        material=obj.data.materials[0];name=obj.data.name
        mesh=bpy.data.meshes.new(name+'-ownership');mesh.from_pydata(vertices,[],[f[0] for f in faces]);mesh.materials.append(material)
        for polygon,f in zip(mesh.polygons,faces):polygon.use_smooth=f[2]
        mesh.normals_split_custom_set([n for f in faces for n in f[1]])
        obj.data=mesh
    return {'fromSourceNode':'hold--right-edge-20','toSourceNode':'hold--right-edge-15','triangleCount':18,'reason':'Inclusive cut ordering assigned the229mm-centered strip asymmetrically; M2 symmetric physical layout governs ownership.','physicalGeometryChanged':False,'triangleCoordinatesSourceMetres':transferred}

def prepare(slug):
    source = HERE.parent / "source-delivery/models" / slug / (slug + ".glb")
    expected = {"frictitious-doormount-pro-7": "8b639807ff660566dca2fd313f00abfadaae0bfbaf0c28ecbc82477f2732113f", "frictitious-megalith": "d8a9fb8c1f308d0d11e90f760e30f1cfde3bf36cb19b212ef24a368835adceb1"}[slug]
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
    ownership_edits = [reconcile_megalith_step_ownership()] if slug.endswith('megalith') else []
    hole_edits = omit_mounting_openings(bpy.data.objects["body--board"], slug)
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
    report = {"sourcePath": str(source.relative_to(Path.cwd())), "sourceSHA256": expected, "preparedSHA256": digest(prepared), "preparedPath": str(prepared.relative_to(Path.cwd())), "blenderVersion": bpy.app.version_string, "removedTransformOnlyNodes": removed, "maximumWorldVertexDeltaMetres": max_delta, "geometryChanged": True, "contactOwnershipEdits": ownership_edits, "mountingOpeningsRemoved": len(hole_edits), "mountingEdits": hole_edits, "maximumContactVertexDeltaMetres": max_delta, "coordinatePreparation": "GLB native import + root world matrix bake only; Blender +Z up, front -Y, metres. Compiler transports to +Y up, front +Z.", "materialAdaptation": "One constant PNG RGBA8 sRGB image per source material, explicitly encoded from linear GLB factor with <=0.004 linear-channel error; no generated grain or source image use.", "sourceMaterialLinearRGBA": colors, "materialConversions": material_adaptations, "mountingOmission": "Only the mounting-interface authored body tubes are omitted, closing exact front/rear loops at their analytic support planes. Actual central relief, contact cavities, nested pockets and stepped depths remain unchanged. Physical products retain their mounting openings.", "meshInventory": [{"name":o.name,"vertices":len(o.data.vertices),"polygons":len(o.data.polygons)} for o in sorted(meshes,key=lambda o:o.name)]}
    (output / "preparation-report.json").write_text(json.dumps(report, indent=2)+"\n")
    manifest = {"schemaVersion":1,"packageID": "frictitious.doormount-pro-7" if slug.endswith("7") else "frictitious.megalith", "manufacturerPhysicalAuthority":{"publisher":"Frictitious Climbing","evidencePacket":str(HERE.parent.relative_to(Path.cwd()))+"/REVIEW.md"},"historicalSource":{"status":"missing","notes":"The old app raster authoring source is not a native contact-tagged model. Immutable user delivery GLB is retained separately."},"auditedModelSource":{"provenanceType":"user-provided","authorization":"User authorized evidence-led native migration; exact evidence approved 2026-09-20. Explicit derivative preparation documented here; no model acceptance implied.","retainedPath":str(prepared.relative_to(Path.cwd())),"sha256":digest(prepared)},"supersessionRuling":"Prepared native derivative of hash-bound original GLB. Source root transforms are baked once; explicit mounting-only tube removal and support-plane caps are recorded, preserving contact geometry; constant material image adaptation is explicit. Manufacturer facts and stable app IDs govern mapping."}
    (output / "source-manifest.json").write_text(json.dumps(manifest,indent=2)+"\n")


if __name__ == "__main__":
    for slug in sys.argv[sys.argv.index("--")+1:]:
        prepare(slug)
