#!/usr/bin/env python3
"""Independent exact-rational check of native bounds and strict optimized IR."""
import argparse,hashlib,json,os,re,signal,struct,sys
from fractions import Fraction as F
from pathlib import Path
sys.dont_write_bytecode=True
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from run_native_contact_screen import OwnedCommands,REPO
p=argparse.ArgumentParser();p.add_argument('--label',required=True);a=p.parse_args()
assert a.label and all(c in 'abcdefghijklmnopqrstuvwxyz0123456789-' for c in a.label)
root=REPO/'.context'/f'{REPO.name}-clearance-bounds-proof-{a.label}';root.mkdir()
for name in ['Math.swift','Axis.swift','Proof.swift']:
    (root/('main.swift' if name=='Proof.swift' else name)).write_bytes(Path(__file__).with_name(name).read_bytes())
sources=sorted(root.glob('*.swift'));binary=root/f'{REPO.name}-proof'
common=['xcrun','swiftc','-O','-whole-module-optimization','-module-cache-path',str(root/'module-cache'),*map(str,sources)]
c=OwnedCommands(REPO.name,root)
for sig in [signal.SIGINT,signal.SIGTERM]:signal.signal(sig,c.interrupted)
def execute(label,args):
    status=c.run(label,['perl','-e','alarm 120;exec @ARGV',*args],root/(label+'.log'),dict(os.environ))
    if status:raise RuntimeError((root/(label+'.log')).read_text())
def number(s):return F.from_float(struct.unpack('>d',struct.pack('>Q',int(s,16)))[0])
def vector(x):return list(map(number,x))
def dot(a,b):return sum((x*y for x,y in zip(a,b)),F(0))
try:
    execute('proof-compile',[*common,'-o',str(binary)])
    execute('proof-export',[str(binary),str(root/'cases.json')])
    execute('proof-ir',[*common,'-emit-ir','-o',str(root/'bounds.ll')])
    rows=json.loads((root/'cases.json').read_text());counts={'support':0,'axis':0,'bvh':0};positive=0;pruned=0
    for row in rows:
        k=row['kind'];counts[k]+=1;start=vector(row['start']);end=vector(row['end'])
        if k=='support':
            n=vector(row['n']);vertices=list(map(vector,row['vertices']));lo=min(dot(v,n) for v in vertices);hi=max(dot(v,n) for v in vertices)
            assert number(row['lower'])<=lo and number(row['upper'])>=hi
            square=dot(n,n);assert number(row['normUpper'])**2>=square
            bound=number(row['bound']);gap=max(F(0),min(dot(start,n),dot(end,n))-hi,lo-max(dot(start,n),dot(end,n)))
            assert bound>=0 and bound**2*square<=gap**2,row
            positive+=bound>0
        elif k=='axis':
            axis=row['axis'];plane=number(row['coordinate']);exact=max(F(0),min(start[axis],end[axis])-plane,plane-max(start[axis],end[axis]))
            assert 0<=number(row['bound'])<=exact,row
        elif row['pruned']:
            low=vector(row['low']);high=vector(row['high']);gaps=[max(F(0),low[i]-max(start[i],end[i]),min(start[i],end[i])-high[i]) for i in range(3)]
            assert dot(gaps,gaps)>=number(row['floor'])**2,row
            pruned+=1
    ir=(root/'bounds.ll').read_text()
    forbidden=re.findall(r'\b(?:fadd|fsub|fmul|fdiv|fcmp)\s+(?:fast|reassoc|nnan|ninf|nsz|arcp|contract|afn)\b',ir)
    assert not forbidden,forbidden
    report={'owner':REPO.name,'adopted':False,'counts':counts,'positiveSupportBounds':positive,'prunedBVHCases':pruned,
        'exactRationalChecksPass':True,'scalarOptimizedIRNoFastFlags':True,
        'scope':'bounded deterministic native scalar corpus; operation-level BVH argument is separate; not generic rounded narrow-phase equivalence',
        'hashes':{str(p.relative_to(REPO)):hashlib.sha256(p.read_bytes()).hexdigest() for p in [*sources,Path(__file__),root/'cases.json',root/'bounds.ll']}}
    (root/'result.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report,indent=2))
finally:c.cleanup()
