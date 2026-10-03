#!/usr/bin/env python3
"""Chronological adaptive-direction coverage and non-adoptable kernel cost ceiling."""
import argparse,hashlib,json,os,signal,sys
from pathlib import Path
sys.dont_write_bytecode=True
sys.path.insert(0,str(Path(__file__).resolve().parent))
from run_native_contact_screen import REPO,OwnedCommands
p=argparse.ArgumentParser(description=__doc__)
p.add_argument('--label',required=True);p.add_argument('--corpus',required=True,type=Path)
p.add_argument('--edge-only',action='store_true',help='retain original point/ray kernels, bound only computed edge witnesses')
args=p.parse_args()
assert args.label and all(c in 'abcdefghijklmnopqrstuvwxyz0123456789-' for c in args.label)
assert REPO.name=='strong-owl-live-physics'
root=REPO/'.context'/(REPO.name+'-separating-hint-'+args.label);root.mkdir()
stage=root/'native';stage.mkdir();sources=stage/'sources';sources.mkdir()
tool=Path(__file__).resolve().parent
collider=REPO/'HangTen/Models/RopeTriangleCollider.swift'
text=collider.read_text()
# This pure triangle corpus never calls the dynamics-dependent chain sweep.
needle='private final class RopeSweepBatch:@unchecked Sendable {'
assert text.count(needle)==1
text=text[:text.index(needle)]
# Extract the original per-face body, with exact operation and candidate order.
start=text.index('            let face=mesh.triangles[index]',text.index('    func fusedContactEvaluation('))
end=text.index('            Self.mergeFused(first.hit',start)
body=text[start:end]
assert body.count('mesh.triangles[index]')==1
body=body.replace('mesh.triangles[index]','mesh.triangles[faceID]')
needle='var row=FusedWitness(best:rowSquare,radius:rowRadius,faceNormal:normal)'
assert body.count(needle)==1
body=body.replace(needle,'var row=FusedWitness(best:rowSquare,radius:rowRadius,faceNormal:normal,trackHint:trackHint)')
needle='''                let ab=Self.segmentPair(start,end,a,b),bc=Self.segmentPair(start,end,b,c),ca=Self.segmentPair(start,end,c,a)
                for q in [ab,bc,ca] {if mask & 2 != 0 {row.consider(q.0,q.1,q.2)};if mask & 4 != 0 {merit.consider(q.0,q.1,q.2)}}'''
assert body.count(needle)==1
body=body.replace(needle,'                if !omitEdges {\n'+needle+'\n                }')
needle='        var hit:RopeSegmentContact?\n        mutating func consider('
assert text.count(needle)==1
text=text.replace(needle,'        var hintSquared=Double.infinity\n        var hintDirection:SIMD3<Double>?=nil\n        var trackHint=false\n'+needle)
needle='            let distanceSquared=simd_length_squared(p-q)\n            guard distanceSquared<best else{return}'
# There are two distinct original helpers; change only FusedWitness's section.
begin=text.index('    private struct FusedWitness')
head,tail=text[:begin],text[begin:]
assert tail.count(needle)==1
tail=tail.replace(needle,'            let distanceSquared=simd_length_squared(p-q)\n            if trackHint && distanceSquared<hintSquared {hintSquared=distanceSquared;hintDirection=p-q}\n            guard distanceSquared<best else{return}')
text=head+tail
text+='''
extension RopeTriangleCollider {
    func directionFace(from start:SIMD3<Double>,to end:SIMD3<Double>,rowRadius:Double,meritRadius:Double,face faceID:Int,mask:Int,trackHint:Bool,omitEdges:Bool = false)->RopeDirectionFaceResult {
        let rowSquare=rowRadius*rowRadius,meritSquare=meritRadius*meritRadius
        var minimum=Double.infinity
'''+body+'''
        return RopeDirectionFaceResult(first:first.hit,row:row.hit,merit:merit.hit,last:last.hit,clearance:minimum,direction:row.hintDirection)
    }
    func directionRayHit(from start:SIMD3<Double>,to end:SIMD3<Double>,face:Int,mask:Int)->Bool {
        guard start != end && mask & 6 != 0 else{return false}
        let f=mesh.triangles[face],v=mesh.vertices
        if let t=Self.rayTriangle(start,end-start,v[f.x],v[f.y],v[f.z]),t>=0,t<=1 {return true}
        return false
    }
}
'''
(sources/collider.name).write_text(text)
for name in ('RopePhysicsDescriptor.swift',):
    (sources/name).write_bytes((REPO/'HangTen/Models'/name).read_bytes())
for name in ('Hint.swift','main.swift'):(sources/name).write_bytes((tool/'separating_hint'/name).read_bytes())
(sources/'ExactCheckpointJSON.swift').write_bytes((tool/'native_contact/ExactCheckpointJSON.swift').read_bytes())
(stage/'PLAN.md').write_text(('Edge-only stage retains original triangleClosest/ray kernels; only computed segmentPair interpolation envelopes bounded.\n' if args.edge_only else '')+'''Fixed step140 chronological corpus, trained only on preceding step139 queries.
Cold misses, refreshes, proposals and ray blockers recorded; all original per-face
point/link/merit witnesses and finite clearance receipts independently checked.
Seven alternating predecoded serial kernel cost pairs; retain only if ratio<=.50.
Every unknown/nonfinite predicate falls back. No original narrowphase skipped in
coverage validation. Timed omitted-branch run is a non-adoptable cost ceiling,
pending general rounded triangleClosest envelope proof and full engine checks.
No whole-step, device, physical rollout, correctness theorem or video claim.
''')
files=sorted(sources.glob('*.swift'));binary=stage/(REPO.name+'-separating-hint')
cmd=['xcrun','swiftc','-O','-whole-module-optimization',*(['-D','SCREEN_EDGE_ONLY'] if args.edge_only else []),'-module-cache-path',str(stage/'module-cache'),*map(str,files),'-o',str(binary)]
args.corpus=args.corpus.resolve()
inputs=[*files,collider,Path(__file__),args.corpus,stage/'PLAN.md',REPO/'Hangboards/clavellium-training-block/assets/primary.physics.json']
(stage/'provenance.json').write_text(json.dumps({'owner':REPO.name,'command':cmd,'hashes':{str(x.relative_to(REPO)):hashlib.sha256(x.read_bytes()).hexdigest() for x in inputs}},indent=2))
c=OwnedCommands(REPO.name,stage)
for sig in (signal.SIGINT,signal.SIGTERM):signal.signal(sig,c.interrupted)
try:
    status=c.run('compile',['perl','-e','alarm 150;exec @ARGV',*cmd],stage/'compile.log',dict(os.environ))
    if not status:status=c.run('run',['perl','-e','alarm 120;exec @ARGV',str(binary),str(stage),str(args.corpus)],stage/'run.log',dict(os.environ))
    print((stage/('run.log' if (stage/'run.log').exists() else 'compile.log')).read_text())
finally:c.cleanup()
raise SystemExit(status)
