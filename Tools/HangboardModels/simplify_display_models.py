#!/usr/bin/env python3
"""Hash-bound, offline display-mesh optimization; never a runtime fallback.

Nodes, materials, all position/UV seam boundaries and physical contact IDs stay
separate. The simplifier selects existing vertices only; it never moves a locked
boundary or invents holes. Crease-aware authored normals remove accidental flat
triangle shading without changing vertex positions. Each export is reopened and
its contact descriptor is compiled from actual referenced vertices.
"""
from __future__ import annotations
import argparse
import ctypes as C
import hashlib
import json
import os
from pathlib import Path
import shutil
import sys
import tempfile
import zipfile
import numpy as np
from numba import njit
from pxr import Usd, UsdGeom, UsdShade, Vt, Sdf, Work

sys.path.insert(0, str(Path(__file__).resolve().parent))
from remove_mounting_bores import _read_mesh, package_board_bytes
from contact_model_package import _canonicalize_usdz
from contact_model_descriptor import NodeBinding, compile_descriptor

PROFILES = {
    'conservative': {'ratio': .20, 'error': .001, 'crease': 35.},
    'lean': {'ratio': .08, 'error': .003, 'crease': 35.},
}


def write_layer_canonical(layer, destination):
    """Fresh, single-threaded crate serialization from deterministic layer text."""
    Work.SetConcurrencyLimit(1)
    copy=Sdf.Layer.CreateAnonymous('canonical.usda')
    if not copy.ImportFromString(layer.ExportToString()):
        raise ValueError('canonical layer parse failed')
    if not copy.Export(str(destination),args={'format':'usdc'}):
        raise ValueError('canonical layer export failed')


def sha(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def compact_corners(v, f, channels):
    """Exact reindex of complete vertex records, not a positional weld."""
    v=np.asarray(v,dtype=np.float32); f=np.asarray(f,dtype=np.int64)
    if v.ndim!=2 or v.shape[1]!=3 or f.ndim!=2 or f.shape[1]!=3:
        raise ValueError('expected triangle geometry')
    if not len(f) or f.min()<0 or f.max()>=len(v) or not np.isfinite(v).all():
        raise ValueError('invalid geometry values or indices')
    columns=[v[f].reshape(-1,3)]; spans={};offset=3
    for key in sorted(channels):
        a=np.asarray(channels[key],dtype=np.float32)
        if a.shape[:2]!=f.shape or not np.isfinite(a).all():
            raise ValueError('invalid corner channel '+key)
        a=a.reshape(len(f)*3,-1)
        columns.append(a); spans[key]=(offset,offset+a.shape[1]);offset+=a.shape[1]
    records=np.concatenate(columns,axis=1)
    unique,inverse=np.unique(records,axis=0,return_inverse=True)
    attrs={k:np.ascontiguousarray(unique[:,a:b]) for k,(a,b) in spans.items()}
    return np.ascontiguousarray(unique[:,:3]),attrs,inverse.reshape(-1,3).astype(np.uint32)


def _geometric_edges(v, f):
    points,inv=np.unique(np.asarray(v,np.float32),axis=0,return_inverse=True)
    q=inv[np.asarray(f)]
    e=np.sort(q[:,[[0,1],[1,2],[2,0]]].reshape(-1,2),axis=1)
    edges,counts=np.unique(e,axis=0,return_counts=True)
    return points,inv,edges,counts


def topology_signature(v, f):
    """Position-welded invariants, without welding the delivered mesh itself."""
    from scipy.sparse import coo_matrix
    from scipy.sparse.csgraph import connected_components
    p,inv,e,c=_geometric_edges(v,f);q=inv[f];used=np.unique(q)
    graph=coo_matrix((np.ones(len(e)*2),(np.r_[e[:,0],e[:,1]],np.r_[e[:,1],e[:,0]])),shape=(len(p),len(p))).tocsr()[used][:,used]
    return {'components':int(connected_components(graph,directed=False,return_labels=False)),
      'boundaryEdges':int(np.sum(c==1)), 'nonmanifoldEdges':int(np.sum(c>2)),
      'euler':int(len(used)-len(e)+len(f)),
      'degenerateFaces':int(np.sum((q[:,0]==q[:,1])|(q[:,0]==q[:,2])|(q[:,1]==q[:,2])))}


def boundary_edge_positions(v, f):
    p,_,e,c=_geometric_edges(v,f)
    return {tuple(map(tuple,x)) for x in p[e[c==1]]}


@njit(cache=True)
def _average_corners(order, starts, counts, face_normals, weights, threshold):
    result=np.zeros((len(order),3),np.float64)
    for g in range(len(starts)):
        s=starts[g];n=counts[g]
        for j in range(s,s+n):
            c=order[j];face=c//3
            total=np.zeros(3,np.float64)
            for k in range(s,s+n):
                other=order[k];f=other//3
                dot=np.dot(face_normals[face],face_normals[f])
                if dot>=threshold:
                    total+=face_normals[f]*weights[other]
            length=np.sqrt(np.dot(total,total))
            if length>1.e-20:result[c]=total/length
            else:result[c]=face_normals[face]
    return result


def crease_normals(v, f, angle_degrees=35., orientation=1.):
    """Angle-weighted corner normals; discontinuous across a reviewed crease."""
    v=np.asarray(v,np.float64);f=np.asarray(f,np.int64)
    _,inv=np.unique(np.asarray(v,np.float32),axis=0,return_inverse=True)
    ids=inv[f].ravel();order=np.argsort(ids,kind='stable')
    _,start,count=np.unique(ids[order],return_index=True,return_counts=True)
    t=v[f];fn=np.cross(t[:,1]-t[:,0],t[:,2]-t[:,0])
    fn/=np.maximum(np.linalg.norm(fn,axis=1,keepdims=True),1.e-30)
    weights=np.empty((len(f),3),np.float64)
    for k in range(3):
        a=t[:,(k+1)%3]-t[:,k];b=t[:,(k+2)%3]-t[:,k]
        weights[:,k]=np.arctan2(np.linalg.norm(np.cross(a,b),axis=1),np.sum(a*b,axis=1))
    n=_average_corners(order,start,count,fn,weights.ravel(),np.cos(np.deg2rad(angle_degrees)))
    return (n.reshape(-1,3,3)*orientation).astype(np.float32)


def stabilize_planar_normals(p,f,n,orientation=1.):
    """Keep actual axis-aligned machined faces flat, not inflated by lip normals."""
    t=np.asarray(p,dtype=np.float64)[f]
    fn=np.cross(t[:,1]-t[:,0],t[:,2]-t[:,0])
    length=np.linalg.norm(fn,axis=1)
    fn/=np.maximum(length[:,None],1.e-30)
    axes=np.abs(fn).argmax(1)
    selected=(np.abs(fn[np.arange(len(fn)),axes])>=np.cos(np.deg2rad(.25)))&(length>1.e-20)
    result=n.copy();unit=np.zeros((len(fn),3),np.float32)
    unit[np.arange(len(fn)),axes]=np.sign(fn[np.arange(len(fn)),axes])*orientation
    result[selected]=unit[selected,None,:]
    return result


def is_uniform_texture(data: bytes) -> bool:
    from PIL import Image
    import io
    try:
        image=np.asarray(Image.open(io.BytesIO(data)).convert('RGBA'))
        return bool(np.all(image==image[0,0]))
    except Exception:
        return False


def uniform_st_is_safe(stage, root: Path, names) -> bool:
    """Only collapse st for a verified constant-image, repeat/clamp UV graph."""
    textures=[n for n in names if Path(n).suffix.lower() in {'.png','.jpg','.jpeg'}]
    if not textures or not all(is_uniform_texture((root/n).read_bytes()) for n in textures):
        return False
    readers=set();shaders=[]
    for prim in stage.Traverse():
        if not prim.IsA(UsdShade.Shader):continue
        kind=prim.GetAttribute('info:id').Get();shaders.append(prim)
        if kind=='UsdPrimvarReader_float2':
            if prim.GetAttribute('inputs:varname').Get()!='st':return False
            readers.add(str(prim.GetPath())+'.outputs:result')
        elif kind not in {'UsdPreviewSurface','UsdUVTexture'}:return False
        if kind=='UsdUVTexture':
            asset=prim.GetAttribute('inputs:file').Get()
            if asset is None:return False
            image=(root/asset.path).resolve()
            if not image.is_relative_to(root.resolve()) or not image.is_file():return False
            if image.relative_to(root.resolve()).as_posix() not in textures:return False
            for axis in ('S','T'):
                wrap=prim.GetAttribute('inputs:wrap'+axis).Get()
                if wrap not in {'repeat','clamp'}:return False
    for prim in shaders:
        for attr in prim.GetAttributes():
            if any(str(c) in readers for c in attr.GetConnections()):
                if prim.GetAttribute('info:id').Get()!='UsdUVTexture' or attr.GetName()!='inputs:st':
                    return False
    return bool(readers)


def _library():
    name=os.environ.get('MESHOPT_LIBRARY')
    if not name:
        name=str(Path(__file__).resolve().parents[2]/'.context/deps/libmeshoptimizer.so')
    lib=C.CDLL(name)
    ptr=C.c_void_p;sz=C.c_size_t
    fn=lib.meshopt_simplifyWithAttributes
    fn.argtypes=[ptr,ptr,sz,ptr,sz,sz,ptr,sz,ptr,sz,ptr,sz,C.c_float,C.c_uint,ptr]
    fn.restype=sz
    return lib


def reduce_mesh(v,f,attrs,*,target_ratio,error_relative,extra_lock=None,permissive=False):
    if not 0<target_ratio<=1 or not 0<=error_relative<=.02:
        raise ValueError('invalid simplification budget')
    v=np.ascontiguousarray(v,dtype=np.float32);f=np.ascontiguousarray(f,dtype=np.uint32)
    if not np.isfinite(v).all() or f.size==0 or f.max()>=len(v):
        raise ValueError('invalid mesh')
    p,inv,e,c=_geometric_edges(v,f)
    # Non-manifold edges are also protected; no attempt is made to repair them.
    protected=np.unique(e[c!=2]);lock=np.isin(inv,protected).astype(np.uint8)
    # Keep exact bounds without locking every point on a flat plane.
    lock[np.r_[v.argmin(0),v.argmax(0)]]=1
    if extra_lock is not None:lock|=np.asarray(extra_lock,np.uint8)
    attribute_parts=[];weights=[]
    for key in sorted(attrs):
        a=np.ascontiguousarray(attrs[key],np.float32)
        if not np.isfinite(a).all() or len(a)!=len(v):raise ValueError('invalid attributes')
        attribute_parts.append(a)
        weights.extend([1.0]*a.shape[1])
    att=np.ascontiguousarray(np.concatenate(attribute_parts,1)) if attribute_parts else np.zeros((len(v),1),np.float32)
    w=np.asarray(weights or [0.],np.float32);out=np.empty(f.size,np.uint32);error=C.c_float()
    target=max(3,int(f.size*target_ratio)//3*3)
    lib=_library()
    before_topology=topology_signature(v,f)
    original_bad={tuple(map(tuple,x)) for x in p[e[c>2]]}
    for attempt in range(16):
        size=lib.meshopt_simplifyWithAttributes(out.ctypes.data,f.ctypes.data,f.size,
            v.ctypes.data,len(v),v.strides[0],att.ctypes.data,att.strides[0],
            w.ctypes.data,len(w),lock.ctypes.data,target,error_relative,1|(32 if permissive else 0),C.byref(error))
        if size==0 or size%3:raise ValueError('invalid simplifier output')
        g=out[:size].reshape(-1,3)
        if topology_signature(v,g)==before_topology:break
        # Reject this candidate; protect its source one-ring and retry FROM the
        # original mesh. This never edits a bad result or fills an opening.
        op,_,oe,oc=_geometric_edges(v,g)
        bad=[x for x in op[oe[oc>2]] if tuple(map(tuple,x)) not in original_bad]
        if not bad:raise ValueError('simplification changed geometric topology')
        bad_positions={tuple(x) for edge in bad for x in edge}
        touched=np.array([tuple(x) in bad_positions for x in p])
        neighborhoods=np.unique(e[np.any(touched[e],axis=1)])
        extra=np.isin(inv,neighborhoods)
        if np.all(lock[extra]):raise ValueError('cannot protect collapsing topology')
        lock[extra]=1
    else:raise ValueError('topology-preserving simplification did not converge')
    used,remap=np.unique(g,return_inverse=True)
    new_v=v[used];new_f=remap.reshape(-1,3).astype(np.uint32)
    new_attrs={k:a[used] for k,a in attrs.items()}
    # Locked complete records may have unused duplicates; protect geometric loci.
    retained={tuple(x) for x in new_v}
    ok=all(tuple(x) in retained for x in v[lock!=0])
    if not ok:raise ValueError('simplifier removed protected geometry')
    if boundary_edge_positions(v,f)!=boundary_edge_positions(new_v,new_f):
        raise ValueError('simplifier changed an open seam boundary')
    return {'points':new_v,'faces':new_f,'attributes':new_attrs,
            'error':float(error.value),'protected_preserved':ok,
            'locked_vertices':int(np.count_nonzero(lock)), 'topologyRetries':attempt, 'topologyPreserved':True}


def optimize_file(source:Path,destination:Path,spec:dict,profile:str):
    source=Path(source);destination=Path(destination)
    if source.resolve()==destination.resolve():raise ValueError('use a separate output path')
    if sha(source)!=spec['sha256']:raise ValueError('source SHA mismatch')
    cfg={**PROFILES[profile],**spec.get(profile,{})}
    destination.parent.mkdir(parents=True,exist_ok=True)
    reports=[]
    with tempfile.TemporaryDirectory(prefix='simplify-',dir=destination.parent) as td:
        root=Path(td)
        with zipfile.ZipFile(source) as z:
            names=z.namelist()
            if len(names)!=len(set(names)) or any(Path(n).is_absolute() or '..' in Path(n).parts for n in names):
                raise ValueError('unsafe USDZ entries')
            z.extractall(root)
        layer=names[0]
        if Path(layer).suffix not in {'.usd','.usda','.usdc'}:raise ValueError('expected root USD layer')
        stage=Usd.Stage.Open(str(root/layer));cache=UsdGeom.XformCache()
        uniform_st=uniform_st_is_safe(stage,root,names)
        records=[_read_mesh(p,cache) for p in stage.Traverse() if p.IsA(UsdGeom.Mesh)]
        for m in records:
            prim=m['prim'];mesh=m['mesh'];v=m['v'];f=m['f'];ch=dict(m['channels'])
            if mesh.GetSubdivisionSchemeAttr().Get()!='none':raise ValueError('subdivision mesh requires separate authoring')
            old_normals=ch.get('normals')
            collapsed_uv=False
            if uniform_st and 'primvars:st' in ch:
                ch['primvars:st']=np.full_like(ch['primvars:st'],.5)
                collapsed_uv=True
            if cfg.get('shade',True):
                ch['normals']=crease_normals(v,f,cfg['crease'],-1. if mesh.GetOrientationAttr().Get()=='leftHanded' else 1.)
            p,attrs,g=compact_corners(v,f,ch)
            node_cfg={**cfg,**spec.get('nodes',{}).get(prim.GetName(),{}).get(profile,{})}
            reduced=reduce_mesh(p,g,attrs,target_ratio=node_cfg['ratio'],error_relative=node_cfg['error'],permissive=bool(cfg.get('permissive',False) and uniform_st))
            p,g,a=reduced['points'],reduced['faces'],reduced['attributes']
            if cfg.get('planarNormals',False):
                corners={k:value[g] for k,value in a.items()}
                corners['normals']=stabilize_planar_normals(p,g,corners['normals'],-1. if mesh.GetOrientationAttr().Get()=='leftHanded' else 1.)
                p,a,g=compact_corners(p,g,corners)
            mesh.GetPointsAttr().Set(Vt.Vec3fArray.FromNumpy(p))
            mesh.GetFaceVertexCountsAttr().Set(Vt.IntArray.FromNumpy(np.full(len(g),3,np.int32)))
            mesh.GetFaceVertexIndicesAttr().Set(Vt.IntArray.FromNumpy(g.ravel().astype(np.int32)))
            mesh.GetExtentAttr().Set(Vt.Vec3fArray.FromNumpy(np.array([p.min(0),p.max(0)],np.float32)))
            for key,values in a.items():
                if key=='normals':
                    mesh.SetNormalsInterpolation('vertex');attr=mesh.GetNormalsAttr()
                else:
                    attr=prim.GetAttribute(key);pv=UsdGeom.Primvar(attr)
                    pv.SetInterpolation('vertex');pv.BlockIndices()
                cls=type(attr.Get())
                attr.Set(cls.FromNumpy(values))
            reports.append({'node':prim.GetName(),'beforeTriangles':len(f),'afterTriangles':len(g),
                'beforePoints':len(v),'afterPoints':len(p),'constantTextureUVCollapsed':collapsed_uv,'errorRelative':reduced['error'],
                'lockedVertices':reduced['locked_vertices'],'boundaryEdgesPreserved':True,'topologyRetries':reduced['topologyRetries'],'topologyPreserved':True,
                'localExtentsPreserved':bool(np.array_equal(v.min(0).astype(np.float32),p.min(0)) and np.array_equal(v.max(0).astype(np.float32),p.max(0)))})
        canonical=root/'canonical-output.usdc'
        write_layer_canonical(stage.GetRootLayer(),canonical)
        os.replace(canonical,root/layer)
        del stage,cache,records,m,prim,mesh
        with zipfile.ZipFile(destination,'w',compression=zipfile.ZIP_STORED) as z:
            for n in names:z.write(root/n,n)
    _canonicalize_usdz(destination)
    stage=Usd.Stage.Open(str(destination));cache=UsdGeom.XformCache();vertices={}
    for prim in stage.Traverse():
        if prim.IsA(UsdGeom.Mesh):
            m=_read_mesh(prim,cache);vertices[prim.GetName()]=m['world'][np.unique(m['f'])].tolist()
    old=json.loads(source.with_suffix('.model.json').read_text())
    if set(vertices)!={n['nodeID'] for n in old['nodes']}:raise ValueError('node inventory changed')
    nodes=[NodeBinding(n['nodeID'],n['role'],n.get('contactID')) for n in old['nodes']]
    compiled=compile_descriptor(destination.read_bytes(),nodes,vertices,frozenset(old['contacts']))
    desc=destination.with_suffix('.model.json');desc.write_text(json.dumps(compiled.to_json(),indent=2,sort_keys=True)+'\n')
    with zipfile.ZipFile(source) as a,zipfile.ZipFile(destination) as b:
        for n in names[1:]:
            if a.read(n)!=b.read(n):raise ValueError('embedded image/resource changed')
    return {'profile':profile,'settings':cfg,'sourceSHA256':sha(source),'modelSHA256':sha(destination),
        'descriptorSHA256':sha(desc),'inputBytes':source.stat().st_size,'outputBytes':destination.stat().st_size,
        'beforeTriangles':sum(r['beforeTriangles'] for r in reports),'afterTriangles':sum(r['afterTriangles'] for r in reports),
        'beforePoints':sum(r['beforePoints'] for r in reports),'afterPoints':sum(r['afterPoints'] for r in reports),
        'nodes':reports,'texturesUnchanged':True,'contactIDsUnchanged':True}


def main():
    ap=argparse.ArgumentParser();ap.add_argument('--root',type=Path,required=True)
    ap.add_argument('--output',type=Path,required=True);ap.add_argument('--manifest',type=Path,required=True)
    ap.add_argument('--profile',choices=PROFILES,default='conservative');ap.add_argument('--board')
    args=ap.parse_args();manifest=json.loads(args.manifest.read_text());results={}
    for slug,spec in manifest['models'].items():
        if args.board and slug!=args.board:continue
        source=args.root/'Hangboards'/slug/'assets/primary.usdz';dest=args.output/'Hangboards'/slug/'assets/primary.usdz'
        r=optimize_file(source,dest,spec,args.profile)
        # A CAD-backed package commits no board.json; write the generated one.
        board_bytes=package_board_bytes(source.parents[1])
        if board_bytes is not None:(dest.parents[1]/'board.json').write_bytes(board_bytes)
        results[slug]=r
        print(slug,r['beforeTriangles'],'->',r['afterTriangles'],'triangles;',r['inputBytes'],'->',r['outputBytes'],'bytes',flush=True)
    args.output.mkdir(parents=True,exist_ok=True)
    (args.output/'simplification-report.json').write_text(json.dumps(results,indent=2)+'\n')

if __name__=='__main__':main()
