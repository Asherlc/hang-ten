"""Explicit Trango derivative preparation; native import/compiler remain unchanged."""
import hashlib,json,sys,struct,zlib
from pathlib import Path
HERE=Path(__file__).resolve().parent
sys.path.insert(0,str(HERE))
import bpy,numpy as np
from mathutils import Matrix,Vector
def digest(path):return hashlib.sha256(path.read_bytes()).hexdigest()
def clip(poly,sign,keep):
    out=[]
    for a,b in zip(poly,poly[1:]+poly[:1]):
        da=keep*(sign*a[0][0]-.2292);db=keep*(sign*b[0][0]-.2292)
        if da>=-1e-12:out.append(a)
        if (da>1e-12 and db< -1e-12) or (da< -1e-12 and db>1e-12):
            t=da/(da-db);p=a[0]+t*(b[0]-a[0]);n=a[1]+t*(b[1]-a[1]);n/=np.linalg.norm(n);out.append((p,n))
    return out
def prepare(slug):
    source = HERE.parent / "source-delivery/models" / slug / (slug + ".glb")
    expected = {"trango-rock-prodigy-forge":"cb905fe6eaac9161b40e8e0f5d972343e424925316bf15d76e59e4e033adeaba","trango-rock-prodigy-natural":"a9a2087a263fc08ea489947ad5d41edad36c7af210b734de0873edf927586b90"}[slug]
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
    material=meshes[0].data.materials[0]
    for obj in meshes:bpy.data.objects.remove(obj,do_unlink=True)
    authored=Path.cwd()/'.context/hangboards-batch-05-astra-migration/prepared'/(slug+'-authored.npz')
    arrays=np.load(authored);verts=arrays['vertices'];normals=arrays['normals'];faces=arrays['faces'];labels=arrays['labels']
    groups={};partition_records=[]
    for label in sorted(set(labels)):
        selected=faces[labels==label]
        if label.endswith('-imr'):
            # F2 deep is the outer lobe. One exact vertical cut partitions the
            # continuous cavity without adding any coplanar highlight shell.
            side=label.split('-')[0];sign=-1 if side=='left' else 1
            for name,keep in [('im-deep',1),('im-shallow',-1)]:
                tris=[]
                for face in selected:
                    poly=[(verts[i].copy(),normals[i].copy()) for i in face]
                    poly=clip(poly,sign,keep)
                    for j in range(1,len(poly)-1):tris.append([poly[0],poly[j],poly[j+1]])
                groups['hold--'+side+'-'+name]=tris
            partition_records.append({'originalNode':'hold--'+label,'cutLocalXMillimetres':153,'deep':'outer half','shallow':'inner half','overlappingMeshes':False})
        else:
            name=label if label.startswith('body--') else 'hold--'+label
            groups[name]=[[(verts[i],normals[i]) for i in face] for face in selected]
    meshes=[]
    for name,tris in groups.items():
        vv=[];ff=[];ns=[];lookup={}
        for tri in tris:
            f=[]
            for point,normal in tri:
                key=tuple(round(float(x),10) for x in point)
                if key not in lookup:lookup[key]=len(vv);vv.append(tuple(point))
                f.append(lookup[key]);ns.append(tuple(normal))
            ff.append(f)
        mesh=bpy.data.meshes.new(name);mesh.from_pydata(vv,[],ff);mesh.materials.append(material)
        for poly in mesh.polygons:poly.use_smooth=True
        mesh.normals_split_custom_set(ns)
        uv=mesh.uv_layers.new(name='UVMap')
        for loop in uv.data:loop.uv=(.5,.5)
        obj=bpy.data.objects.new(name,mesh);bpy.context.collection.objects.link(obj);meshes.append(obj)
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
    report={'sourcePath':str(source.relative_to(Path.cwd())),'sourceSHA256':expected,'preparedSHA256':digest(prepared),'preparedPath':str(prepared.relative_to(Path.cwd())),'blenderVersion':bpy.app.version_string,'removedTransformOnlyNodes':removed,'maximumWorldVertexDeltaMetres':max_delta,'geometryChanged':True,'authoredGeometrySHA256':digest(authored),'authoringSHA256':{name:digest(HERE/'trango-authoring'/name) for name in ['author_trango.py','authored_geometry.py','geometry.py']},'geometryAuthoring':'trango-authoring/author_trango.py; explicit drafted cavity, crimp/shoulder, jaw/brow corrections and screw omissions. Original GLB retained immutable.','contactOwnershipEdits':partition_records,'mountingOpeningsRemoved':8 if slug.endswith('forge') else 6,'preservedLargePassages':2,'coordinatePreparation':'Native GLB world bake checked once; derivative uses same native Blender Z-up/front -Y metres basis; no additional axis/scale transform.','materialConversions':material_adaptations,'sourceMaterialLinearRGBA':colors,'meshInventory':[{'name':o.name,'vertices':len(o.data.vertices),'polygons':len(o.data.polygons)} for o in sorted(meshes,key=lambda o:o.name)]}
    (output / "preparation-report.json").write_text(json.dumps(report, indent=2)+"\n")
    manifest = {"schemaVersion":1,"packageID": "trango.rock-prodigy-"+slug.rsplit("-",1)[-1], "manufacturerPhysicalAuthority":{"publisher":"Trango","evidencePacket":str(HERE.parent.relative_to(Path.cwd()))+"/REVIEW.md"},"historicalSource":{"status":"missing","notes":"The old app raster authoring source is not a native contact-tagged model. Immutable user delivery GLB is retained separately."},"auditedModelSource":{"provenanceType":"user-provided","authorization":"User authorized evidence-led native migration; exact evidence approved 2026-09-20. Explicit derivative preparation documented here; no model acceptance implied.","retainedPath":str(prepared.relative_to(Path.cwd())),"sha256":digest(prepared)},"supersessionRuling":"Prepared native derivative of hash-bound original GLB. Source root transforms are baked once for basis verification. Explicit analytic derivative corrects documented shape discrepancies and omits screws; it preserves distinct physical cavities. Constant material image adaptation is explicit. Manufacturer facts and stable app IDs govern mapping."}
    (output / "source-manifest.json").write_text(json.dumps(manifest,indent=2)+"\n")


if __name__ == "__main__":
    for slug in sys.argv[sys.argv.index("--")+1:]:
        prepare(slug)
