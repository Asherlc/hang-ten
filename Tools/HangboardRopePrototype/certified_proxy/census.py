#!/usr/bin/env python3
"""Bounded actual-mesh proxy census. No physics adoption or native timing."""
import argparse,collections,hashlib,json,math,sys
from fractions import Fraction as F
from pathlib import Path
sys.dont_write_bytecode=True
from geometry import proposal,fixtures,LIMIT


class BVH:
    def __init__(self,vertices,triangles):
        self.vertices=vertices;self.triangles=triangles;self.nodes=[]
        self.build(list(range(len(triangles))))
    def build(self,ids):
        v=self.vertices;tri=self.triangles
        points=[v[j] for i in ids for j in tri[i]]
        lo=tuple(min(x[k] for x in points) for k in range(3));hi=tuple(max(x[k] for x in points) for k in range(3))
        index=len(self.nodes);self.nodes.append((lo,hi,-1,-1,ids))
        if len(ids)>8:
            size=[hi[k]-lo[k] for k in range(3)];axis=0 if size[0]>=size[1] and size[0]>=size[2] else 1 if size[1]>=size[2] else 2
            ordered=sorted(ids,key=lambda i:((v[tri[i][0]][axis]+v[tri[i][1]][axis])+v[tri[i][2]][axis],i))
            half=len(ordered)//2;left=self.build(ordered[:half]);right=self.build(ordered[half:]);self.nodes[index]=(lo,hi,left,right,[])
        return index
    def query(self,start,end):
        lo=tuple(min(x,y) for x,y in zip(start,end));hi=tuple(max(x,y) for x,y in zip(start,end))
        row=(0.0035+0.0001)+0.00005;merit=0.0035+0.0001
        def square(n,a,b):
            g=[max(n[0][k]-b[k],a[k]-n[1][k],0.0) for k in range(3)]
            return (g[0]*g[0]+g[1]*g[1])+g[2]*g[2]
        stack=[(0,15)];faces=[];norms=0
        while stack:
            i,parent=stack.pop();n=self.nodes[i]
            first=square(n,start,start);link=square(n,lo,hi);last=square(n,end,end);norms+=3
            mask=parent & ((1 if first<row*row else 0)|(2 if link<row*row else 0)|(4 if link<merit*merit else 0)|(8 if last<row*row else 0))
            if not mask:continue
            if n[2]>=0:stack.extend([(n[2],mask),(n[3],mask)])
            else:faces.extend((f,mask) for f in n[4])
        return sorted(faces),norms


def closed(faces):
    edges=collections.defaultdict(list)
    for i,t in faces.items():
        assert len(set(t))==3
        for j in range(3):
            a,b=t[j],t[(j+1)%3];edges[tuple(sorted((a,b)))].append((a,b))
    assert all(len(v)==2 and v[0]==tuple(reversed(v[1])) for v in edges.values()),'oriented closed edge incidence'


def simplify(mesh):
    vertices=[tuple(F.from_float(x) for x in p) for p in mesh['vertices']]
    faces={i:tuple(t) for i,t in enumerate(mesh['triangles'])};errors={i:F(0) for i in faces};next_id=len(faces)
    certificates=[];rounds=[];closed(faces)
    for iteration in range(12):
        incident=collections.defaultdict(list)
        for i,t in faces.items():
            for v in t:incident[v].append(i)
        blocked=set();selected=[]
        for center in sorted(incident):
            ids=incident[center]
            if any(i in blocked for i in ids):continue
            p=proposal(vertices,faces,errors,center,ids)
            if p is None:continue
            blocked.update(ids);selected.append(p)
        if not selected:break
        for p in selected:
            for i in p['oldFaces']:del faces[i];del errors[i]
            ids=[]
            for t in p['triangles']:
                faces[next_id]=tuple(t);errors[next_id]=F(*p['bound']);ids.append(next_id);next_id+=1
            p['newFaces']=ids;p['round']=iteration+1;certificates.append(p)
        closed(faces)
        record={'round':iteration+1,'replacements':len(selected),'triangles':len(faces),'maximumBoundMeters':float(max(errors.values()))}
        rounds.append(record);print(record,flush=True)
    return {'vertices':mesh['vertices'],'triangles':[list(t) for _,t in sorted(faces.items())]},certificates,rounds


def main():
    parser=argparse.ArgumentParser();parser.add_argument('--output',type=Path,required=True);parser.add_argument('--fixtures-only',action='store_true');a=parser.parse_args()
    repo=Path(__file__).resolve().parents[3];assert repo.name=='strong-owl-live-physics' and a.output.resolve().is_relative_to(repo/'.context')
    fixtures()
    if a.fixtures_only:return
    source=repo/'Hangboards/clavellium-training-block/assets/primary.physics.json'
    descriptor=json.loads(source.read_text());original=descriptor['collision']
    proxy,certificates,rounds=simplify(original)
    corpus_path=repo/'.context/strong-owl-live-physics-coplanar-query-5a12d1ee2-chronological-corpus/native/result.json'
    corpus=json.loads(corpus_path.read_text());old=BVH(original['vertices'],original['triangles']);new=BVH(proxy['vertices'],proxy['triangles'])
    records=[]
    for step in [1,6,109,140,493]:
        examples=next(x for x in corpus['steps'] if x['step']==step)['census']['examples']
        old_faces=new_faces=old_norms=new_norms=0
        for q in examples:
            expected=sorted(tuple(x) for x in q['faces']);before,work=old.query(q['start'],q['end'])
            assert before==expected,('original masks mismatch',step,q['batch'],q['link'])
            after,cost=new.query(q['start'],q['end']);old_faces+=len(before);new_faces+=len(after);old_norms+=work;new_norms+=cost
        record={'step':step,'queries':len(examples),'originalFaceVisits':old_faces,'proxyFaceVisits':new_faces,
            'faceRatio':new_faces/old_faces,'originalBBoxGapNorms':old_norms,'proxyBBoxGapNorms':new_norms,'normRatio':new_norms/old_norms,'originalMasksMatch':True}
        records.append(record);print(record,flush=True)
    a.output.mkdir()
    (a.output/'proxy.json').write_text(json.dumps(proxy,separators=(',',':'))+'\n')
    (a.output/'certificates.json').write_text(json.dumps(certificates,indent=2)+'\n')
    face_ratio=sum(r['proxyFaceVisits'] for r in records)/sum(r['originalFaceVisits'] for r in records)
    norm_ratio=sum(r['proxyBBoxGapNorms'] for r in records)/sum(r['originalBBoxGapNorms'] for r in records)
    result={'owner':repo.name,'adopted':False,'scope':'exact graph metric certificate and retained nonempty query BVH work counts, no native outputs or timing',
        'originalTriangles':len(original['triangles']),'proxyTriangles':len(proxy['triangles']),'limitMeters':float(LIMIT),'roundLimit':12,'rounds':rounds,'records':records,
        'faceRatio':face_ratio,'normRatio':norm_ratio,'necessaryScreenPass':face_ratio<=.4 and norm_ratio<=.75,
        'limits':['Signedness/global embedding/contact normals/trajectory not certified; original parity required.','Per-face composed map bounds supply original-surface two-sided proximity; no claim of CAD accuracy.','Independent exact replay still required before native query stage.'],
        'hashes':{str(p.relative_to(repo)):hashlib.sha256(p.read_bytes()).hexdigest() for p in [source,corpus_path,Path(__file__),Path(__file__).with_name('geometry.py'),a.output/'proxy.json',a.output/'certificates.json']}}
    (a.output/'result.json').write_text(json.dumps(result,indent=2)+'\n')
    print('Necessary screen',result['necessaryScreenPass'],'faces',face_ratio,'norms',norm_ratio,flush=True)
    if not result['necessaryScreenPass']:sys.exit(2)


if __name__=='__main__':main()
