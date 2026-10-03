#!/usr/bin/env python3
"""Independent exact-rational check of native bounds and strict optimized IR."""
import argparse,hashlib,json,os,re,signal,struct,sys
from fractions import Fraction as F
from pathlib import Path
sys.dont_write_bytecode=True
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from run_native_contact_screen import OwnedCommands,REPO
p=argparse.ArgumentParser();p.add_argument('--label',required=True);p.add_argument('--free-balls',action='store_true');p.add_argument('--union',action='store_true');a=p.parse_args()
assert a.label and all(c in 'abcdefghijklmnopqrstuvwxyz0123456789-' for c in a.label)
root=REPO/'.context'/f'{REPO.name}-clearance-bounds-proof-{a.label}';root.mkdir()
for name in ['Math.swift','Axis.swift','Proof.swift']:
    (root/('main.swift' if name=='Proof.swift' else name)).write_bytes(Path(__file__).with_name(name).read_bytes())
if a.free_balls:
    (root/'FreeBall.swift').write_bytes(Path(__file__).resolve().parents[1].joinpath('free_balls/Math.swift').read_bytes())
    main=root/'main.swift';text=main.read_text()
    text=text.replace('try clearanceBoundFixtures();','try freeBallFixtures();try clearanceBoundFixtures();')
    text=text.replace('try JSONSerialization.data(withJSONObject:records', '''for _ in 0..<10000 {
    let center=point(),p=center+point()*0.008,radius=RopeCertifiedClearance(lowerBound:0.0036)
    let ball=RopePointFreeBall(center:center,radius:radius,outsideKnown:true)!
    records.append(["kind":"ball","center":bits(center),"start":bits(p),"end":bits(p),
        "upper":bits(ball.distanceUpper(p)!),"radius":bits(radius.lowerBound),"insideBall":ball.contains(p)])
}
try JSONSerialization.data(withJSONObject:records''')
    main.write_text(text)
if a.union:
    (root/'PlaneCache.swift').write_bytes(Path(__file__).resolve().parents[1].joinpath('plane_reuse/Math.swift').read_bytes())
    main=root/'main.swift';text=main.read_text()
    text=text.replace('try clearanceBoundFixtures();','try unionSupportFixtures();try planeCacheFixtures();try clearanceBoundFixtures();')
    text=text.replace('try JSONSerialization.data(withJSONObject:records', '''for _ in 0..<10000 {
    let vertices=(0..<10).map{_ in point()},n=point(),p=point(),q=point()
    let support=RopeTriangleSupport(unionDirection:n,vertices:vertices)!,bound=support.bound(p,q)!
    records.append(["kind":"union","vertices":vertices.map{bits($0)},"n":bits(n),"start":bits(p),"end":bits(q),
        "lower":bits(support.lower),"upper":bits(support.upper),"normUpper":bits(support.normUpper),"bound":bits(bound.lowerBound)])
}
try JSONSerialization.data(withJSONObject:records''')
    main.write_text(text)
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
    rows=json.loads((root/'cases.json').read_text());counts={'support':0,'axis':0,'bvh':0,'ball':0,'union':0};positive=0;pruned=0
    for row in rows:
        k=row['kind'];counts[k]+=1;start=vector(row['start']);end=vector(row['end'])
        if k in ('support','union'):
            n=vector(row['n']);vertices=list(map(vector,row['vertices']));lo=min(dot(v,n) for v in vertices);hi=max(dot(v,n) for v in vertices)
            assert number(row['lower'])<=lo and number(row['upper'])>=hi
            square=dot(n,n);assert number(row['normUpper'])**2>=square
            bound=number(row['bound']);gap=max(F(0),min(dot(start,n),dot(end,n))-hi,lo-max(dot(start,n),dot(end,n)))
            assert bound>=0 and bound**2*square<=gap**2,row
            positive+=bound>0
        elif k=='axis':
            axis=row['axis'];plane=number(row['coordinate']);exact=max(F(0),min(start[axis],end[axis])-plane,plane-max(start[axis],end[axis]))
            assert 0<=number(row['bound'])<=exact,row
        elif k=='ball':
            center=vector(row['center']);delta=[p-c for p,c in zip(start,center)]
            upper=number(row['upper']);square=dot(delta,delta)
            assert upper>=0 and upper**2>=square,row
            if row['insideBall']:assert square<number(row['radius'])**2,row
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
