"""Self-contained deterministic GLB writer. Source coordinates are metres, Blender Z-up.
No photograph, pixel tracing, texture, external buffer, or rendering dependency is used.
"""
from pathlib import Path
import json, struct, hashlib
import numpy as np

ROT=np.array([[1.,0.,0.],[0.,0.,1.],[0.,-1.,0.]])

def sha256(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()

def atomic_bytes(path,data):
    path=Path(path); path.parent.mkdir(parents=True,exist_ok=True)
    tmp=path.with_name(path.name+'.tmp'); tmp.write_bytes(data); tmp.replace(path)

def write_glb(path,parts,color=(.64,.49,.31),roughness=.75,metadata=None):
    """parts = iterable of {name,vertices,faces,normals,hold_id} in source XYZ metres.
    A separate, isometric triangle-island UV atlas is generated per mesh. UV density varies
    across islands, but triangles are not stretched. No image maps are created or used.
    """
    doc={'asset':{'version':'2.0','generator':'Batch01 repair / explicit geometry + asset_io.py'},
         'scene':0,'scenes':[{'name':'production','nodes':[]}], 'nodes':[], 'meshes':[],
         'buffers':[], 'bufferViews':[], 'accessors':[],
         'materials':[{'name':'neutral-product-material','pbrMetallicRoughness':{
             'baseColorFactor':list(color)+[1.], 'metallicFactor':0.,'roughnessFactor':roughness},
             'doubleSided':False}], 'extras':metadata or {}}
    chunks=bytearray()
    def arr(a,component_type,type_name,target=None,bounds=False):
        a=np.ascontiguousarray(a)
        while len(chunks)%4: chunks.append(0)
        off=len(chunks); chunks.extend(a.tobytes())
        vi=len(doc['bufferViews']); view={'buffer':0,'byteOffset':off,'byteLength':a.nbytes}
        if target: view['target']=target
        doc['bufferViews'].append(view)
        ac={'bufferView':vi,'byteOffset':0,'componentType':component_type,'count':len(a),'type':type_name}
        if bounds:
            ac['min']=a.min(axis=0).tolist(); ac['max']=a.max(axis=0).tolist()
        ai=len(doc['accessors']); doc['accessors'].append(ac); return ai
    for part in parts:
        v=np.asarray(part['vertices'],dtype=float); f=np.asarray(part['faces'],dtype=np.int64)
        n=np.asarray(part['normals'],dtype=float)
        triangles=(v[f]@ROT.T)
        pos=triangles.reshape(-1,3).astype('<f4')
        norm=(np.asarray(part.get('corner_normals',n[f]))@ROT.T).reshape(-1,3).astype('<f4')
        # Per-triangle orthogonal flattening, followed by uniform scaling into a tile.
        a=triangles[:,1]-triangles[:,0]; b=triangles[:,2]-triangles[:,0]
        length=np.linalg.norm(a,axis=1); u=a/np.maximum(length[:,None],1e-15)
        bx=(u*b).sum(axis=1); by=np.sqrt(np.maximum((b*b).sum(axis=1)-bx*bx,0))
        uv=np.stack([np.stack([np.zeros(len(f)),np.zeros(len(f))],axis=1),
                     np.stack([length,np.zeros(len(f))],axis=1),np.stack([bx,by],axis=1)],axis=1)
        uv-=uv.min(axis=1,keepdims=True)
        scale=np.maximum(np.ptp(uv,axis=1).max(axis=1),1e-15)
        uv=.06+.88*uv/scale[:,None,None]
        side=int(np.ceil(np.sqrt(len(f))))
        tile=np.stack([np.arange(len(f))%side,np.arange(len(f))//side],axis=1)
        uv=((uv+tile[:,None,:])/side).reshape(-1,2).astype('<f4')
        indices=np.arange(len(pos),dtype='<u4')
        attr={'POSITION':arr(pos,5126,'VEC3',34962,True), 'NORMAL':arr(norm,5126,'VEC3',34962),
              'TEXCOORD_0':arr(uv,5126,'VEC2',34962)}
        ix=arr(indices,5125,'SCALAR',34963)
        name=part['name']; hi=part.get('hold_id')
        extras={'selectable':hi is not None,'logicalHoldId':hi,'sourceUnits':'metre'}
        mi=len(doc['meshes']); doc['meshes'].append({'name':name,'primitives':[
            {'attributes':attr,'indices':ix,'material':0,'mode':4}],'extras':extras})
        ni=len(doc['nodes']); doc['nodes'].append({'name':name,'mesh':mi,'extras':extras})
        doc['scenes'][0]['nodes'].append(ni)
    while len(chunks)%4: chunks.append(0)
    doc['buffers']=[{'byteLength':len(chunks)}]
    js=json.dumps(doc,ensure_ascii=True,separators=(',',':')).encode()
    js+=b' '*((-len(js))%4)
    total=12+8+len(js)+8+len(chunks)
    data=struct.pack('<4sII',b'glTF',2,total)+struct.pack('<I4s',len(js),b'JSON')+js+struct.pack('<I4s',len(chunks),b'BIN\0')+chunks
    atomic_bytes(path,data)
    return {'bytes':len(data),'sha256':sha256(path),'triangles':sum(len(p['faces']) for p in parts),'objects':len(parts)}
