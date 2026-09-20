"""Read-only exact USDZ/source geometry checks; run inside Blender from repo root."""
import sys,json,hashlib,zipfile
from pathlib import Path
from collections import Counter
HERE=Path(__file__).resolve().parent
if str(HERE) not in sys.path:sys.path.insert(0,str(HERE))
import bpy
from mathutils import Vector

def digest(path):return hashlib.sha256(path.read_bytes()).hexdigest()
def triangles(obj):
    obj.data.calc_loop_triangles()
    vertices=[obj.matrix_world@v.co for v in obj.data.vertices]
    return Counter(tuple(sorted(tuple(round(c,7) for c in vertices[i]) for i in tri.vertices)) for tri in obj.data.loop_triangles)

def contact_corner_normals(objects):
    result={}
    for obj in objects:
        mesh=obj.data;world=obj.matrix_world;normal_matrix=world.to_3x3().inverted().transposed()
        for polygon in mesh.polygons:
            coords=tuple(sorted(tuple(round(c,7) for c in world@mesh.vertices[i].co) for i in polygon.vertices))
            for loop in polygon.loop_indices:
                index=mesh.loops[loop].vertex_index
                point=tuple(round(c,7) for c in world@mesh.vertices[index].co)
                result[(coords,point)]=normal_matrix@mesh.corner_normals[loop].vector
    return result

def verify(slug):
    root=Path.cwd();native=HERE/slug;package=root/'Hangboards'/slug
    mapping=json.loads((native/'contact-mapping.json').read_text())
    bpy.ops.wm.read_factory_settings(use_empty=True)
    bpy.ops.import_scene.gltf(filepath=str(HERE.parent/'source-delivery/models'/slug/(slug+'.glb')))
    original={o['contactID']:triangles(bpy.data.objects[o['sourceNodeID']]) for o in mapping['objects'] if o['role']=='contact'}
    source_normals=contact_corner_normals([bpy.data.objects[o['sourceNodeID']] for o in mapping['objects'] if o['role']=='contact'])
    original_counts={cid:sum(tris.values()) for cid,tris in original.items()}
    if slug.endswith('megalith'):
        assert original_counts['edge-15-left']==720 and original_counts['edge-20-left']==702
        assert original_counts['edge-15-right']==702 and original_counts['edge-20-right']==720
    original_union=sum(original.values(),Counter())
    ownership_edits=json.loads((native/'preparation-report.json').read_text())['contactOwnershipEdits']
    for edit in ownership_edits:
        moved=Counter(tuple(sorted(tuple(round(c,7) for c in point) for point in tri)) for tri in edit['triangleCoordinatesSourceMetres'])
        assert sum(moved.values())==18
        assert all(original['edge-20-right'][tri]>=count for tri,count in moved.items())
        original['edge-20-right']-=moved;original['edge-15-right']+=moved
    bpy.ops.wm.read_factory_settings(use_empty=True)
    model=package/'assets/primary.usdz';bpy.ops.wm.usd_import(filepath=str(model))
    descriptor=json.loads((package/'assets/primary.model.json').read_text())
    meshes={o.name:o for o in bpy.context.scene.objects if o.type=='MESH'}
    assert set(meshes)=={n['nodeID'] for n in descriptor['nodes']}
    final_normals=contact_corner_normals([meshes[n['nodeID']] for n in descriptor['nodes'] if n['role']=='contact'])
    assert source_normals.keys()==final_normals.keys()
    normal_delta=max((normal-final_normals[key]).length for key,normal in source_normals.items())
    assert normal_delta<.001,normal_delta
    contact_checks=[]
    for cid,contact in descriptor['contacts'].items():
        current=Counter()
        for name in contact['nodeIDs']:current.update(triangles(meshes[name]))
        assert current==original[cid],(slug,cid,'contact triangles moved/removed/added')
        contact_checks.append({'contactID':cid,'triangleCount':sum(current.values()),'sourceWorldTrianglesPreservedAfterExplicitOwnershipRuling':True,'ownershipReconciled': bool(ownership_edits and cid in ('edge-20-right','edge-15-right'))})
    assert sum(original.values(),Counter())==original_union
    body=next(meshes[n['nodeID']] for n in descriptor['nodes'] if n['role']=='body')
    preparation=json.loads((native/'preparation-report.json').read_text());rays=[]
    for edit in preparation['mountingEdits']:
        cx,_,cz=edit['centerSourceMetres'];fy=edit['frontSupportYMetres']
        front=body.ray_cast(Vector((cx,-.1,cz)),Vector((0,1,0)))
        back=body.ray_cast(Vector((cx,.1,cz)),Vector((0,-1,0)))
        assert front[0] and abs(front[1].y-fy)<1e-6
        assert back[0] and abs(back[1].y)<1e-6
        rays.append({'centerSourceMetres':[cx,0,cz],'frontHit':bool(front[0]),'backHit':bool(back[0]),'frontYMetres':front[1].y,'backYMetres':back[1].y})
    for obj in meshes.values():
        assert all(len(poly.vertices)==3 for poly in obj.data.polygons)
        assert obj.data.materials
        for material in obj.data.materials:
            assert any(n.type=='TEX_IMAGE' and n.image for n in material.node_tree.nodes)
    assert descriptor['modelSHA256']==digest(model)
    assert (package/'assets/primary.model.json').read_text()==json.dumps(descriptor,indent=2,sort_keys=True)+'\n'
    report={'modelSHA256':digest(model),'descriptorSHA256':digest(package/'assets/primary.model.json'),'cleanEmptySceneImport':True,'contactCount':len(original),'meshCount':len(meshes),'unionOfAllContactTrianglesUnchanged':True,'ownershipTransferTriangles':18 if ownership_edits else 0,'originalContactTriangleCounts':original_counts,'contactTriangleChecks':contact_checks,'mountingClosureRays':rays,'maximumSourceContactCornerNormalDelta':normal_delta,'allImportedImageMaterials':True,'allTriangles':True,'descriptorCanonicalSorted':True,'modelAcceptance':False,'remaining':'Current-source iOS SceneKit materials, all-contact nearest picking, highlight isolation/clear, orbit/reset, unavailable state.'}
    (native/'geometry-verification.json').write_text(json.dumps(report,indent=2)+'\n')
    print('VERIFIED',slug,len(original),'contact triangle sets match explicit ownership ruling;',len(rays),'omitted bores closed')

if __name__=='__main__':
    for slug in ('frictitious-doormount-pro-7','frictitious-megalith'):verify(slug)
