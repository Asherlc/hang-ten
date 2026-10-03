#!/usr/bin/env python3
"""Exact mesh planar-region topology; no geometry modification."""
import argparse,collections,hashlib,json,math,sys
from pathlib import Path
sys.dont_write_bytecode=True
sys.path.insert(0,str(Path(__file__).resolve().parent))
from plane_reuse.atlas import generate

def generate_regions(path):
    _,atlas=generate(path);mesh=json.loads(path.read_text())['collision'];v=mesh['vertices'];tri=mesh['triangles']
    groups=collections.defaultdict(list)
    for i,g in enumerate(atlas['facePlaneIDs']):groups[g].append(i)
    ratios=[[float(x).as_integer_ratio() for x in p] for p in v];den=max(d for p in ratios for _,d in p)
    iv=[[n*(den//d) for n,d in p] for p in ratios]
    regions=[];face_ids=[-1]*len(tri)
    def cross(a,b,c):return (b[0]-a[0])*(c[1]-a[1])-(b[1]-a[1])*(c[0]-a[0])
    def overlap(a,b):
        for t in [a,b]:
            for i in range(3):
                p,q=t[i],t[(i+1)%3];n=(p[1]-q[1],q[0]-p[0])
                da=[x[0]*n[0]+x[1]*n[1] for x in a];db=[x[0]*n[0]+x[1]*n[1] for x in b]
                if max(min(da),min(db))>=min(max(da),max(db)):return False
        return True
    for group,faces in groups.items():
        if len(faces)<20:continue
        vids=set(j for i in faces for j in tri[i]);axes=[k for k in range(3) if len(set(v[j][k] for j in vids))==1]
        if len(axes)!=1:continue
        axis=axes[0];project=[k for k in range(3) if k!=axis];xy={j:tuple(iv[j][k] for k in project) for j in vids}
        sign=None;edges=collections.defaultdict(list)
        for i in faces:
            t=tri[i];area=cross(*[xy[j] for j in t]);assert area!=0
            winding=1 if area>0 else -1
            if sign is None:sign=winding
            assert sign==winding
            for j in range(3):edges[tuple(sorted((t[j],t[(j+1)%3])))].append((t[j],t[(j+1)%3]))
        boundaries=[]
        for edge,directed in edges.items():
            assert len(directed) in (1,2)
            if len(directed)==2:assert directed[0]==tuple(reversed(directed[1]))
            else:boundaries.append(directed[0])
        nxt={}
        for p,q in boundaries:assert p not in nxt;nxt[p]=q
        assert set(nxt)==set(nxt.values())
        loops=[];remaining=set(nxt)
        while remaining:
            first=min(remaining);loop=[first];remaining.remove(first);j=nxt[first]
            while j!=first:assert j in remaining;remaining.remove(j);loop.append(j);j=nxt[j]
            assert len(loop)>=3;loops.append(loop)
        for n,i in enumerate(faces):
            a=[xy[j] for j in tri[i]]
            for other in faces[n+1:]:assert not overlap(a,[xy[j] for j in tri[other]]),(group,i,other)
        r={'group':group,'axis':axis,'coordinate':v[next(iter(vids))][axis],'faces':faces,'edges':boundaries,'loops':loops,'orientation':sign,'interiorsDisjoint':True}
        id=len(regions);regions.append(r)
        for i in faces:face_ids[i]=id
    source='// Exact atlas of mesh SHA256 '+hashlib.sha256(path.read_bytes()).hexdigest()+'\n'
    source+='struct RopePlanarRegionAtlas {\nstatic let faceIDs:[Int]='+json.dumps(face_ids)+'\n'
    source+='static let axes:[Int]='+json.dumps([r['axis'] for r in regions])+'\n'
    source+='static let faceLists:[[Int]]='+json.dumps([r['faces'] for r in regions])+'\n'
    source+='static let boundaryEdges:[[[Int]]]='+json.dumps([r['edges'] for r in regions])+'\n'
    vertex_ids=sorted(set(j for r in regions for i in r['faces'] for j in tri[i]))
    face_list=[i for r in regions for i in r['faces']]
    source+='static let vertexIDs:[Int]='+json.dumps(vertex_ids)+'\n'
    source+='static let vertices:[[Double]]='+json.dumps([v[j] for j in vertex_ids])+'\n'
    source+='static let selectedFaces:[Int]='+json.dumps(face_list)+'\n'
    source+='static let triangles:[[Int]]='+json.dumps([tri[i] for i in face_list])+'\n}\n'
    return source,{'owner':'strong-owl-live-physics','adopted':False,'regions':regions,'faceIDs':face_ids,'descriptorSHA256':hashlib.sha256(path.read_bytes()).hexdigest(),'topologyExactChecksPass':True}

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--output',type=Path,required=True);a=p.parse_args()
    repo=Path(__file__).resolve().parents[2];assert a.output.resolve().is_relative_to(repo/'.context')
    _,report=generate_regions(repo/'Hangboards/clavellium-training-block/assets/primary.physics.json')
    a.output.write_text(json.dumps(report,indent=2)+'\n');print([(r['group'],len(r['faces']),len(r['edges']),len(r['loops'])) for r in report['regions']])
