#!/usr/bin/env python3
"""Necessary temporal-BVH work census; no physics, timing or adoption."""
import argparse,hashlib,json,math
from pathlib import Path
p=argparse.ArgumentParser();p.add_argument('--corpus',type=Path,required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args()
repo=Path(__file__).resolve().parents[2];a.corpus=a.corpus.resolve()
assert repo.name=='strong-owl-live-physics' and a.output.resolve().is_relative_to(repo/'.context')
descriptor=repo/'Hangboards/clavellium-training-block/assets/primary.physics.json'
mesh=json.loads(descriptor.read_text())['collision'];v=mesh['vertices'];tri=mesh['triangles'];nodes=[]
def build(ids):
    points=[v[j] for i in ids for j in tri[i]]
    lo=tuple(min(x[k] for x in points) for k in range(3));hi=tuple(max(x[k] for x in points) for k in range(3))
    index=len(nodes);nodes.append((lo,hi,-1,-1,ids))
    if len(ids)>8:
        size=[hi[k]-lo[k] for k in range(3)];axis=0 if size[0]>=size[1] and size[0]>=size[2] else 1 if size[1]>=size[2] else 2
        ordered=sorted(ids,key=lambda i:((v[tri[i][0]][axis]+v[tri[i][1]][axis])+v[tri[i][2]][axis],i))
        half=len(ordered)//2;left=build(ordered[:half]);right=build(ordered[half:]);nodes[index]=(lo,hi,left,right,[])
    return index
build(list(range(len(tri))))
row=(0.0035+0.0001)+0.00005;merit=0.0035+0.0001;halo=0.001
expanded=math.nextafter((row+halo)+1e-9,math.inf)
def squareGap(node,lo,hi):
    g=[max(node[0][k]-hi[k],lo[k]-node[1][k],0.0) for k in range(3)]
    return (g[0]*g[0]+g[1]*g[1])+g[2]*g[2]
def bounds(start,end):return (tuple(min(x,y) for x,y in zip(start,end)),tuple(max(x,y) for x,y in zip(start,end)))
def mask(node,start,end,lo,hi):
    link=squareGap(node,lo,hi);first=squareGap(node,start,start);last=squareGap(node,end,end)
    return (1 if first<row*row else 0)|(2 if link<row*row else 0)|(4 if link<merit*merit else 0)|(8 if last<row*row else 0)
def original(start,end):
    lo,hi=bounds(start,end);stack=[(0,15)];faces=[];norms=0
    while stack:
        i,parent=stack.pop();n=nodes[i];m=parent & mask(n,start,end,lo,hi);norms+=3
        if not m:continue
        if n[2]>=0:stack.extend([(n[2],m),(n[3],m)])
        else:faces.extend((f,m) for f in n[4])
    return sorted(faces),norms
def acquire(lo,hi):
    stack=[0];leaves=[];norms=0
    while stack:
        i=stack.pop();n=nodes[i];norms+=1
        if squareGap(n,lo,hi)>=expanded*expanded:continue
        if n[2]>=0:stack.extend([n[2],n[3]])
        else:
            leaves.append(i)
            if len(leaves)>64:return None,norms
    return leaves,norms
def up(x):return math.nextafter(x,math.inf)
def down(x):return math.nextafter(x,-math.inf)
def movement(old,new):
    total=0.0
    for k in range(3):
        low=new[0][k]-old[0][k];high=new[1][k]-old[1][k]
        component=max(abs(down(low)),abs(up(low)),abs(down(high)),abs(up(high)))
        total=up(total+up(component*component))
    return up(math.sqrt(total))
d=json.loads(a.corpus.read_text());records=[]
for step in [1,6,109,139,140,493]:
    examples=next(x for x in d['steps'] if x['step']==step)['census']['examples'];cache={};oldWork=0;newWork=0;reused=0;fresh=0;fallbacks=0;maxLeaves=0
    for q in sorted(examples,key=lambda q:(q['batch'],q['link'])):
        start,end=tuple(q['start']),tuple(q['end']);current=bounds(start,end)
        assert all(math.isfinite(x) and abs(x)<=0.5 for x in (*start,*end)) and 0.001<=row<=0.01
        expected=sorted(tuple(x) for x in q['faces']);reference,work=original(start,end)
        assert reference==expected,('Python original candidate mismatch',step,q['batch'],q['link'])
        oldWork+=work;old=cache.get(q['link']);leaves=None
        if old is not None and movement(old[0],current)<halo-2e-9:leaves=old[1];reused+=1
        else:
            leaves,work=acquire(*current);newWork+=work;fresh+=1
            if leaves is not None:cache[q['link']]=(current,leaves)
        if leaves is None:
            fallbacks+=1;actual,work=original(start,end);newWork+=work
        else:
            maxLeaves=max(maxLeaves,len(leaves));actual=[]
            for i in leaves:
                m=mask(nodes[i],start,end,*current);newWork+=3
                if m:actual.extend((f,m) for f in nodes[i][4])
            actual.sort()
        assert actual==expected,('temporal leaf candidate mismatch',step,q['batch'],q['link'])
    records.append({'step':step,'nonemptyQueries':len(examples),'originalBBoxGapNorms':oldWork,'candidateBBoxGapNorms':newWork,'movementNormTests':len(examples)-fresh,'ratio':newWork/oldWork,
        'reused':reused,'acquisitions':fresh,'capFallbacks':fallbacks,'maxRetainedLeaves':maxLeaves,'candidateMasksIdentical':True})
    print(records[-1],flush=True)
result={'owner':repo.name,'adopted':False,'scope':'Python reconstruction and exact retained masks; nonempty queries only, no native outputs or timing',
    'haloMeters':halo,'leafCap':64,'necessaryNormRatio':1/3,'records':records,
    'pass':next(x for x in records if x['step']==140)['ratio']<=1/3,
    'hashes':{str(p.relative_to(repo)):hashlib.sha256(p.read_bytes()).hexdigest() for p in [descriptor,a.corpus,Path(__file__)]}}
a.output.parent.mkdir(parents=True,exist_ok=True);a.output.write_text(json.dumps(result,indent=2)+'\n')
