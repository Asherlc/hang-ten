"""Load the delivered GLB bytes independently; inspect topology, mapping and cavity rays.
Structural verification is intentionally separate from photographic fidelity.
"""
from pathlib import Path
import json,struct,tempfile,shutil
import numpy as np,trimesh
from asset_io import sha256,ROT


def glb_json(path):
    b=Path(path).read_bytes(); magic,version,n=struct.unpack_from('<4sII',b)
    assert magic==b'glTF' and version==2 and n==len(b)
    length,kind=struct.unpack_from('<I4s',b,12); assert kind==b'JSON'
    doc=json.loads(b[20:20+length]); off=20+length; blen,bkind=struct.unpack_from('<I4s',b,off)
    assert bkind==b'BIN\0' and off+8+blen==len(b)
    return doc,b[off+8:]


def read_accessor(doc,b,idx):
    ac=doc['accessors'][idx]; view=doc['bufferViews'][ac['bufferView']]
    types={5126:'<f4',5125:'<u4',5123:'<u2',5121:'u1'}; n={'SCALAR':1,'VEC2':2,'VEC3':3,'VEC4':4}[ac['type']]
    offset=view.get('byteOffset',0)+ac.get('byteOffset',0)
    return np.frombuffer(b,dtype=types[ac['componentType']],count=ac['count']*n,offset=offset).reshape(-1,n)


def ray_first(tris,origin,direction=(0,1,0)):
    """Vectorized double-precision Moller-Trumbore, no spatial index dependency."""
    d=np.array(direction,float); e1=tris[:,1]-tris[:,0]; e2=tris[:,2]-tris[:,0]
    h=np.cross(d,e2); a=np.einsum('ij,ij->i',e1,h); active=np.abs(a)>1e-14
    inv=np.divide(1.,a,out=np.zeros_like(a),where=active); s=np.array(origin)-tris[:,0]
    u=inv*np.einsum('ij,ij->i',s,h); q=np.cross(s,e1); v=inv*(q@d)
    t=inv*np.einsum('ij,ij->i',e2,q)
    mask=active&(u>=-1e-8)&(v>=-1e-8)&(u+v<=1+1e-8)&(t>=0)
    return None if not mask.any() else float(t[mask].min())


def validate(path,cfg,hold_map):
    path=Path(path); doc,b=glb_json(path); checks=[]
    def check(name,passed,detail=None):
        checks.append({'check':name,'pass':bool(passed),'detail':detail})
    check('glb_payload_integrity',True)
    expected=['body']+[x['objectName'] for x in hold_map['holds']]
    names=[n.get('name') for n in doc.get('nodes',[])]
    check('exact_node_names',set(names)==set(expected) and len(names)==len(expected),names)
    check('one_node_per_contact',len(names)==len(set(names)))
    check('baked_identity_transforms',all(not any(k in n for k in ('matrix','translation','rotation','scale')) for n in doc['nodes']))
    check('no_external_buffers',all('uri' not in z for z in doc['buffers']))
    check('no_external_images',not doc.get('images'))
    check('no_cameras_lights_rigs_animations',not any(doc.get(k) for k in ('cameras','skins','animations')) and not doc.get('extensions'))
    check('no_forbidden_production_objects',set(names)==set(expected))
    check('one_neutral_material_no_highlight_materials',len(doc['materials'])==1)
    check('no_cord_markers_on_fixed_board',not any('cord' in n for n in names))
    total=0; minarea=np.inf; finite=True; nd=True; normalsok=True; uvok=True; matok=True; windingn=True
    source_triangles=[]
    for node in doc['nodes']:
        mesh=doc['meshes'][node['mesh']]
        hi=node.get('extras',{}).get('logicalHoldId')
        check('mapping_'+node['name'],hi==(None if node['name']=='body' else next(h['holdId'] for h in hold_map['holds'] if h['objectName']==node['name'])))
        for prim in mesh['primitives']:
            v=read_accessor(doc,b,prim['attributes']['POSITION']).astype(float)
            f=read_accessor(doc,b,prim['indices']).astype(int).ravel().reshape(-1,3)
            n=read_accessor(doc,b,prim['attributes']['NORMAL']).astype(float)
            uv=read_accessor(doc,b,prim['attributes']['TEXCOORD_0']).astype(float)
            cross=np.cross(v[f[:,1]]-v[f[:,0]],v[f[:,2]]-v[f[:,0]])
            area=np.linalg.norm(cross,axis=1)/2; minarea=min(minarea,float(area.min()))
            total+=len(f); finite &= np.isfinite(v).all() and np.isfinite(n).all(); nd &= np.all(area>1e-18)
            normalsok &= np.allclose(np.linalg.norm(n,axis=1),1,atol=.0001)
            uvok &= np.isfinite(uv).all() and np.all(uv>=0) and np.all(uv<=1)
            matok &= 'material' in prim
            # At least the average imported normal should face the same hemisphere.
            windingn &= np.all(np.einsum('ij,ij->i',cross,n[f].mean(axis=1))>=-1e-12)
            source_triangles.append((v[f]@ROT))
    check('all_finite_geometry',finite);check('nondegenerate_triangles',nd,{'minimumAreaM2':minarea})
    check('unit_normals',normalsok);check('normals_winding_hemisphere',windingn)
    check('all_uvs_finite_in_unit_square',uvok);check('material_assigned_every_mesh',matok)
    tris=np.concatenate(source_triangles); flat=tris.reshape(-1,3)
    # Same shared coordinates were exported to multiple nodes with identical float32 values.
    unique,inv=np.unique(flat,axis=0,return_inverse=True)
    faces=inv.reshape(-1,3)
    assembled=trimesh.Trimesh(vertices=unique,faces=faces,process=False)
    sortedfaces=np.sort(faces,axis=1)
    check('no_duplicate_surfaces',len(np.unique(sortedfaces,axis=0))==len(faces))
    check('assembled_watertight',assembled.is_watertight)
    check('assembled_consistent_winding',assembled.is_winding_consistent)
    check('assembled_positive_volume',assembled.volume>0,assembled.volume)
    check('one_connected_physical_board',len(assembled.split(only_watertight=False))==1)
    w,h,t=cfg['dimensionsMm']; expected_extent=np.array([w,t,h])/1000
    error=np.abs(assembled.extents-expected_extent)*1000
    check('metric_envelope_within_1p5_mm',np.all(error<1.5),{'sourceXYZExtentsM':assembled.extents.tolist(),'absoluteErrorMm':error.tolist()})
    check('declared_rear_bottom_origin',abs(assembled.bounds[1,1])<.0015 and abs(assembled.bounds[0,2])<.0015)
    rayresults=[]
    for p in cfg.get('pockets',[]):
        for offset in [-.17,.17]:
            origin=np.array([p['x']+offset*p['width'],-t-10,p['z']])/1000
            distance=ray_first(tris,origin)
            hitY=None if distance is None else (origin[1]+distance)*1000
            through=p.get('throughOpening',False)
            ok=(hitY is None) if through else (hitY is not None and abs(hitY-p['floorY'])<1.5)
            rayresults.append({'holdId':p.get('holdId'),'xOffsetFraction':offset,
                'expectedFloorYmm':None if through else p['floorY'],'expectedThroughOpening':through,
                'actualFirstHitYmm':hitY,'pass':bool(ok)})
    check('pocket_rays_reach_recess_floors_not_front_caps',all(r['pass'] for r in rayresults),rayresults)
    feature_rays=[]
    for probe in cfg.get('verificationRays',[]):
        origin=np.asarray(probe['originMm'])/1000; direction=probe['direction']
        distance=ray_first(tris,origin,direction)
        actual=None if distance is None else (origin+np.asarray(direction)*distance)*1000
        expected_hit=probe.get('expectedHitMm')
        ok=actual is None if expected_hit is None else actual is not None and np.linalg.norm(actual-np.asarray(expected_hit))<probe.get('toleranceMm',1.5)
        feature_rays.append({'feature':probe['feature'],'actualHitMm':None if actual is None else actual.tolist(),
            'expectedHitMm':expected_hit,'pass':bool(ok)})
    if feature_rays:check('source_correction_feature_rays',all(r['pass'] for r in feature_rays),feature_rays)
    mountresults=[]
    for hole in cfg.get('mounts',[]):
        origin=np.array([hole['x'],-t-10,hole['z']])/1000
        hit=ray_first(tris,origin)
        mountresults.append({'centreXmm':hole['x'],'centreZmm':hole['z'],'unobstructedThroughBore':hit is None})
    check('mount_bores_are_actual_openings',all(r['unobstructedThroughBore'] for r in mountresults),mountresults)
    with tempfile.TemporaryDirectory(prefix='glb_isolated_check_') as tmp:
        isolated=Path(tmp)/'asset.glb';shutil.copyfile(path,isolated)
        scene=trimesh.load(isolated,force='scene',process=False)
        check('isolated_trimesh_import',len(scene.geometry)==len(expected),{'reader':trimesh.__version__,'geometryCount':len(scene.geometry),'directoryContents':[p.name for p in Path(tmp).iterdir()]})
        check('import_triangle_count',sum(len(m.faces) for m in scene.geometry.values())==total,total)
    return {'schemaVersion':1,'asset':path.name,'assetSha256':sha256(path),'structuralPass':all(c['pass'] for c in checks),
        'triangleCount':total,'contactCount':len(hold_map['holds']),'nodeCount':len(names),'checks':checks,
        'evidenceCoverage':'See sources.md; dimensional conflict rulings and display estimates are not physical metrology.',
        'visualReview':'Separate visual-review.json is required; a structural pass is not source-fidelity certification.',
        'nativeBlenderAvailable':False}
