#!/usr/bin/env python3
"""Exact-rational necessary census, not a runtime pruning implementation."""
import json,hashlib,argparse
from fractions import Fraction as F
from pathlib import Path
parser=argparse.ArgumentParser(description=__doc__)
parser.add_argument('--corpus',type=Path,required=True);parser.add_argument('--output',type=Path,required=True)
a=parser.parse_args();a.corpus=a.corpus.resolve();repo=Path(__file__).resolve().parents[2]
assert repo.name=='strong-owl-live-physics' and a.output.resolve().is_relative_to(repo/'.context')
meshpath=repo/'Hangboards/clavellium-training-block/assets/primary.physics.json'
mesh=json.loads(meshpath.read_text())['collision'];corpus=json.loads(a.corpus.read_text())
v=[tuple(F(x) for x in row) for row in mesh['vertices']]
def sub(a,b):return tuple(x-y for x,y in zip(a,b))
def dot(a,b):return sum(x*y for x,y in zip(a,b))
def cross(a,b):return (a[1]*b[2]-a[2]*b[1],a[2]*b[0]-a[0]*b[2],a[0]*b[1]-a[1]*b[0])
planes=[]
for triangle in mesh['triangles']:
 p,q,r=(v[i] for i in triangle);n=cross(sub(q,p),sub(r,p));planes.append((n,dot(n,p),dot(n,n)))
# Match the original Double radius additions, then exact rational conversion.
radius=F((0.0035+0.0001)+0.00005)+F(1e-9)
records=[]
for step in [1,6,109,139,140,493]:
 item=next(x for x in corpus['steps'] if x['step']==step);count=0;rejected=0
 for query in item['census']['examples']:
  p=tuple(F(x) for x in query['start']);q=tuple(F(x) for x in query['end'])
  for face,mask in query['faces']:
   count+=1;n,h,square=planes[face]
   low=min(dot(n,p),dot(n,q))-h;high=h-max(dot(n,p),dot(n,q));gap=max(low,high)
   if square>0 and gap>0 and gap*gap>radius*radius*square:rejected+=1
 records.append({'step':step,'faceVisits':count,'planeSeparated':rejected,'fraction':rejected/count})
 print(records[-1],flush=True)
d={'owner':repo.name,'adopted':False,'kind':'normal-only subset reassessment of closed four-direction projection preflight',
 'scope':'exact rational same-side whole-segment/triangle-plane classification; no query arithmetic skipped or timings',
 'necessaryFraction':0.70,'pass':next(x for x in records if x['step']==140)['fraction']>=0.70,'records':records,
 'hashes':{str(p.relative_to(repo)):hashlib.sha256(p.read_bytes()).hexdigest() for p in [meshpath,a.corpus,Path(__file__)]}}
a.output.parent.mkdir(parents=True,exist_ok=True);a.output.write_text(json.dumps(d,indent=2)+'\n')
