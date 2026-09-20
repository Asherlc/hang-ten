"""Read-only exact-export verification, including nearest rays against body geometry."""
import sys,json,hashlib,math
from pathlib import Path
from collections import Counter
HERE=Path(__file__).resolve().parent
sys.path.insert(0,str(HERE))
import bpy
from mathutils import Vector
from mathutils.bvhtree import BVHTree

def digest(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def triangles(obj):
    mesh=obj.data;mesh.calc_loop_triangles()
    vv=[obj.matrix_world@v.co for v in mesh.vertices]
    return Counter(tuple(sorted(tuple(round(c,7) for c in vv[i]) for i in tri.vertices)) for tri in mesh.loop_triangles)
def corner_normals(obj):
    transform=obj.matrix_world.to_3x3().inverted().transposed()
    positions=[tuple(round(c,7) for c in obj.matrix_world@v.co) for v in obj.data.vertices]
    values={}
    for loop,normal in zip(obj.data.loops,obj.data.corner_normals):
        key=positions[loop.vertex_index];n=(transform@normal.vector).normalized()
        if key in values:assert (n-values[key]).length<.001
        else:values[key]=n.copy()
    return values

def tree_for(meshes):
    vertices=[];faces=[];owners=[]
    for obj in meshes:
        offset=len(vertices);vertices.extend(obj.matrix_world@v.co for v in obj.data.vertices)
        faces.extend([offset+i for i in poly.vertices] for poly in obj.data.polygons)
        owners.extend([obj.name]*len(obj.data.polygons))
    return BVHTree.FromPolygons(vertices,faces,all_triangles=True),owners

def verify(product,source=False):
    root=Path.cwd();slug='trango-rock-prodigy-'+product;native=HERE/slug;package=root/'Hangboards'/slug
    model=package/'assets/primary.usdz';descriptor=json.loads((package/'assets/primary.model.json').read_text())
    mapping=json.loads((native/'contact-mapping.json').read_text())
    if not source:
        bpy.ops.wm.open_mainfile(filepath=str(root/'.context/hangboards-batch-05-astra-migration/prepared'/(slug+'.blend')))
        prepared={o['sourceNodeID']:triangles(bpy.data.objects[o['sourceNodeID']]) for o in mapping['objects']}
        prepared_normals={o['sourceNodeID']:corner_normals(bpy.data.objects[o['sourceNodeID']]) for o in mapping['objects']}
    bpy.ops.wm.read_factory_settings(use_empty=True)
    if source:bpy.ops.import_scene.gltf(filepath=str(HERE.parent/'source-delivery/models'/slug/(slug+'.glb')))
    else:bpy.ops.wm.usd_import(filepath=str(model))
    meshes={o.name:o for o in bpy.context.scene.objects if o.type=='MESH'}
    tree,owners=tree_for(meshes.values())
    def cast(x,z,back=False):
        return tree.ray_cast(Vector((x,.3 if back else -.3,z)),Vector((0,-1 if back else 1,0)))
    # Independent physical section checks: crimp return exists beyond old straight trough.
    if product=='natural':
        valley=cast(.05+.108,-.036)[0];tab=cast(.05+.121,-.029)[0]
        shape={'channelY':valley.y,'thumbTabY':tab.y,'hookHasDistinctRelief':valley.y-tab.y>.004}
    else:
        valley=cast(.0762+.111,-.025)[0];tab=cast(.0762+.119,-.022)[0]
        shape={'channelY':valley.y,'thumbTabY':tab.y,'hookHasDistinctRelief':valley.y-tab.y>.003}
    if source:
        out=root/'.context/hangboards-batch-05-astra-migration'/(slug+'-source-shape-red.json');out.write_text(json.dumps(shape,indent=2)+'\n')
        assert shape['hookHasDistinctRelief'],(product,'source lacks intended hooked crimp return',shape)
        return
    assert shape['hookHasDistinctRelief'],shape
    if product=='natural':
        inner=cast(.05+.144,-.056)[0];outer=cast(.05+.146,-.056)[0]
        assert outer.y-inner.y>.0025
        shape['supportedFloorStepMetres']=outer.y-inner.y
    else:
        inner=cast(.0762+.133,-.045)[0];outer=cast(.0762+.176,-.045)[0]
        assert outer.y-inner.y>.010
        shape['imLobeDepthTransitionMetres']=outer.y-inner.y

    assert set(meshes)=={n['nodeID'] for n in descriptor['nodes']}
    # Compare every exact triangle to its prepared source; names may receive importer suffix.
    correspondence=[];maximum_normal_delta=0.
    for entry in mapping['objects']:
        source_name=entry['sourceNodeID'];prefix=source_name.replace('-','_')
        matches=[n for n in meshes if n.startswith(prefix)]
        assert len(matches)==1,(source_name,matches)
        assert triangles(meshes[matches[0]])==prepared[source_name],source_name
        actual_normals=corner_normals(meshes[matches[0]])
        assert actual_normals.keys()==prepared_normals[source_name].keys()
        normal_delta=max((actual_normals[k]-n).length for k,n in prepared_normals[source_name].items())
        maximum_normal_delta=max(maximum_normal_delta,normal_delta)
        assert normal_delta<.001,(source_name,normal_delta)
        correspondence.append({'sourceNodeID':source_name,'importedNodeID':matches[0],'triangles':sum(prepared[source_name].values())})
    node_contact={n['nodeID']:n.get('contactID') for n in descriptor['nodes']}
    rays=[]
    for cid,contact in descriptor['contacts'].items():
        for node in contact['nodeIDs']:
            obj=meshes[node];vv=[obj.matrix_world@v.co for v in obj.data.vertices]
            candidates=sorted(obj.data.polygons,key=lambda p:p.area,reverse=True)
            found=None
            for poly in candidates[:600]:
                point=sum((vv[i] for i in poly.vertices),Vector())/len(poly.vertices)
                for direction in [Vector((0,-1,0)),Vector((0,-1,.6)).normalized(),Vector((.4,-1,.3)).normalized(),Vector((-.4,-1,.3)).normalized(),Vector((0,-.3,1)).normalized()]:
                    hit=tree.ray_cast(point+direction*.7,-direction)
                    if hit[0] is not None and owners[hit[2]]==node and (hit[0]-point).length<2e-5:
                        found={'expectedContactID':cid,'nearestContactID':node_contact[owners[hit[2]]],'nodeID':node,'pointSourceMetres':list(point),'directionTowardCamera':list(direction),'bodyIncluded':True};break
                if found:break
            assert found,(product,cid,node,'not visible in native all-mesh nearest-hit test')
            rays.append(found)
    # Exact authored screw positions: large passages intentionally excluded.
    coordinates=[(40,28),(79,-25),(214,2),(217,31)] if product=='forge' else [(35,48),(92,46),(150,43)]
    offset=.0762 if product=='forge' else .05
    closures=[]
    for sign in [-1,1]:
        for x,z in coordinates:
            front=cast(sign*(offset+x/1000),z/1000);back=cast(sign*(offset+x/1000),z/1000,True)
            assert front[0] is not None and back[0] is not None
            assert abs(back[0].y)<1e-6
            closures.append({'sourceXZ':[sign*(offset+x/1000),z/1000],'frontHit':True,'backHit':True,'frontY':front[0].y,'backY':back[0].y})
    passages=[]
    x,z=(157,-44) if product=='forge' else (162,-56)
    for sign in [-1,1]:
        hit=cast(sign*(offset+x/1000),z/1000)
        assert hit[0] is None,(product,'passage occluded',hit)
        passages.append({'sourceXZ':[sign*(offset+x/1000),z/1000],'hit':False,'purpose':'unresolved; not suspension'})
    for obj in meshes.values():
        assert all(len(p.vertices)==3 for p in obj.data.polygons)
        assert all(math.isfinite(c) for v in obj.data.vertices for c in v.co)
        assert all(any(n.type=='TEX_IMAGE' and n.image for n in mat.node_tree.nodes) for mat in obj.data.materials)
    assert descriptor['modelSHA256']==digest(model)
    report={'modelSHA256':digest(model),'descriptorSHA256':digest(package/'assets/primary.model.json'),'cleanEmptySceneImport':True,'allImportedImageMaterials':True,'allTriangles':True,'preparedTrianglesUnchanged':True,'preparedCustomNormalsUnchangedWithinTolerance':True,'normalVectorTolerance':.001,'maximumNormalVectorDelta':maximum_normal_delta,'sourceNodeCorrespondence':correspondence,'nativeContactRays':rays,'mountingClosureRays':closures,'preservedPassageRays':passages,'authoredCrimpSection':shape,'modelAcceptance':False,'remaining':'Current-source iOS materials/picking/highlight/clear/orbit/reset/unavailable and human review'}
    (native/'geometry-verification.json').write_text(json.dumps(report,indent=2)+'\n')
    print('VERIFIED',product,len(rays),'all-mesh nearest contact rays,',len(closures),'closed screws, 2 open passages')
if __name__=='__main__':
    for product in ['forge','natural']:
        try:verify(product,'--source-diagnosis' in sys.argv)
        except AssertionError as e:
            if '--source-diagnosis' not in sys.argv:raise
            print('EXPECTED SOURCE RED',e)
