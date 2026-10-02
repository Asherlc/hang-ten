import sys,os,signal,json,hashlib,re,argparse
from pathlib import Path
sys.dont_write_bytecode=True
sys.path.insert(0,'Tools/HangboardRopePrototype')
from run_native_contact_screen import OwnedCommands,REPO
parser=argparse.ArgumentParser(description="Fresh original/experimental exact query accepted-step screen")
parser.add_argument('--label',required=True)
parser.add_argument('--kind',choices=['baseline','packed','projection','trace'],required=True)
args=parser.parse_args()
if not args.label or any(c not in 'abcdefghijklmnopqrstuvwxyz0123456789-' for c in args.label):parser.error('invalid label')
if Path(os.environ.get('PASEO_WORKTREE_PATH',REPO)).resolve()!=REPO or REPO.name!='strong-owl-live-physics':parser.error('wrong owner')
root=REPO/'.context'/f'{REPO.name}-exact-query-{args.label}'
if root.exists() or root.is_symlink():parser.error('fresh output required')
root.mkdir();stage=root/'native';stage.mkdir();snapshot=stage/'sources';snapshot.mkdir()
tool=REPO/'Tools/HangboardRopePrototype'
def transform(source):
 if args.kind=='packed':
  from packed_query.snapshot import packed_source
  return packed_source(source)
 if args.kind=='projection':
  from triangle_separation.snapshot import separated_source
  return separated_source(source)
 return source
native=REPO/'Tools/HangboardRopePrototype/native_contact'
names=['RopePhysicsDescriptor.swift','RopeTriangleCollider.swift','RopeSimulationState.swift',
 'RopeThreadedSeed.swift','RopeSimulationMetrics.swift','RopeCordContacts.swift',
 'RopeContactSystem.swift','RopeBandedSystem.swift','RopeDynamicsSolver.swift']
originals=[REPO/'HangTen/Models'/n for n in names]
scopes={
 'RopeDynamicsSolver.swift':['step','advanceBounded','advance','correctConstraints','contactCorrection','fullContactCorrection','constraintBackbone','merit','selfContactValid'],
 'RopeContactSystem.swift':['solve','solveFactored'],
 'RopeBandedSystem.swift':['factorized'],
 'RopeSimulationMetrics.swift':['measure','contacts'],
 'RopeSimulationState.swift':['refresh'],
 'RopeTriangleCollider.swift':['segmentContacts','segmentClearance','sweptSegmentContact','contains','closestSegment','closestSurface'],
 'RopeCordContacts.swift':['between']}
for p in originals:
 text=p.read_text()
 if p.name=='RopeTriangleCollider.swift':text=transform(text)

 if args.kind=='trace' and p.name=='RopeDynamicsSolver.swift':
  old='                    return alpha*max(maximum,abs(heightCorrection))'
  assert text.count(old)==1
  text=text.replace(old, '                    CorrectionTrace.events.append(["kind":"correction","alpha":alpha,"movement":alpha*max(maximum,abs(heightCorrection)),"strain":maximumStrain(),"rows":rows.count,"active":solved.ids.count-rows.filter{!$0.contact}.count,"penalty":penalty])\n'+old)
 if args.kind=='trace' and p.name=='RopeContactSystem.swift':
  text=text.replace('        for _ in 0..<maxIterations {','        for iteration in 0..<maxIterations {')
  old='            return Solution(base:Array(correction.prefix(size))'
  assert text.count(old)==1
  text=text.replace(old,'            CorrectionTrace.events.append(["kind":"qp","iterations":iteration+1,"responses":responses.count,"active":active.count,"contacts":contacts.count])\n'+old)
 for name in scopes.get(p.name,[]):
  pattern=r'(^[ \t]*(?:private |fileprivate |static |mutating )*func '+name+r'\([^\{]+\{\n)'
  if p.name=='RopeContactSystem.swift' and name=='solve':
   pattern=r'(^[ \t]*static func solve\(factor:[^\{]+\{\n)'
  key=p.stem+'.'+name
  text,count=re.subn(pattern,lambda m:m[0]+f'        AcceptedSolverProfile.enter("{key}")\n        defer {{AcceptedSolverProfile.leave("{key}")}}\n',text,flags=re.M)
  assert count==1,(p.name,name,count)
 if p.name=='RopeDynamicsSolver.swift':text='import Foundation\n'+text+'\n'+(tool/'stock_chain/CheckpointAdapter.swift').read_text()
 if p.name=='RopeBandedSystem.swift':
  old='        try RopeBandedFactorization(size:size'
  assert text.count(old)==1
  text=text.replace(old,'        return try RopeBandedFactorization(size:size')
 (snapshot/p.name).write_text(text)
for name in ['ExactCheckpointJSON.swift','AcceptedSolverProfile.swift']:(snapshot/name).write_bytes((native/name).read_bytes())
(snapshot/'main.swift').write_bytes((native/'AcceptedStepMain.swift').read_bytes())
if args.kind=='trace':
 (snapshot/'CorrectionTrace.swift').write_text('import Foundation\nenum CorrectionTrace {static var events:[[String:Any]]=[]}\n')
 main=(snapshot/'main.swift').read_text().replace('print("PASS whole-state', 'try JSONSerialization.data(withJSONObject:CorrectionTrace.events,options:[.sortedKeys,.prettyPrinted]).write(to:root.appendingPathComponent("trace.json"))\nprint("PASS whole-state')
 (snapshot/'main.swift').write_text(main)
files=sorted(snapshot.iterdir())
command=['xcrun','swiftc','-O','-whole-module-optimization','-Xcc','-DACCELERATE_NEW_LAPACK','-module-cache-path',str(stage/'module-cache'),*map(str,files),'-o',str(stage/'strong-owl-live-physics-accepted-profile')]
checkpoint=REPO/'.context/strong-owl-live-physics-solver-foundation/clav-contact-step/checkpoint.json'
prior=REPO/'.context/strong-owl-live-physics-accepted-profile/native/after-1.json'
inputs=[*files,*originals,checkpoint,prior,tool/'stock_chain/CheckpointAdapter.swift',native/'AcceptedStepMain.swift',Path(__file__),REPO/'Hangboards/clavellium-training-block/assets/primary.physics.json']
(stage/'provenance.json').write_text(json.dumps({'owner':REPO.name,'command':command,'hashes':{str(p.relative_to(REPO)):hashlib.sha256(p.read_bytes()).hexdigest() for p in inputs}},indent=2))
assert hashlib.sha256(checkpoint.read_bytes()).hexdigest()=='cad349812c3c0c33384378fe368abff97411f2a0c9aeb385d99edebef151c464'
assert hashlib.sha256((REPO/'Hangboards/clavellium-training-block/assets/primary.physics.json').read_bytes()).hexdigest()=='c60fbd6dfaf59bfd5fb7e6aa8d806f78af7e828a7f64074d326865e08f13e853'
c=OwnedCommands(REPO.name,stage)
for sig in [signal.SIGINT,signal.SIGTERM]:signal.signal(sig,c.interrupted)

def check_queries(c,root,transform,kind):
 q=root/'query-identity';q.mkdir()
 source=(REPO/'HangTen/Models/RopeTriangleCollider.swift').read_text()
 source=source.replace('    private func contains(', '    func queryParity(_ point:SIMD3<Double>)->Bool {contains(point)}\n    private func contains(')
 (q/'RopeTriangleCollider.swift').write_text(transform(source))
 reference=source[source.index('/// Exact triangle queries'):].replace('struct RopeTriangleCollider:', 'struct ReferenceTriangleCollider:')
 (q/'ReferenceTriangleCollider.swift').write_text('import simd\n'+reference)
 (q/'RopePhysicsDescriptor.swift').write_bytes((REPO/'HangTen/Models/RopePhysicsDescriptor.swift').read_bytes())
 (q/'main.swift').write_bytes((tool/'packed_query/query_identity.swift').read_bytes())
 def run(label,argv):
  status=c.run(label,['perl','-e','alarm 150;exec @ARGV',*map(str,argv)],q/(label+'.log'),dict(os.environ))
  if status:raise RuntimeError((q/(label+'.log')).read_text()[-6000:])
 run('query-compile',['xcrun','swiftc','-O','-whole-module-optimization','-module-cache-path',q/'module-cache',*sorted(q.glob('*.swift')),'-o',q/'strong-owl-live-physics-query'])
 run('query-check',[q/'strong-owl-live-physics-query','Hangboards/clavellium-training-block/assets/primary.physics.json','.context/strong-owl-live-physics-candidate-discovery-reviewed/capture/frozen.json'])
 print((q/'query-check.log').read_text())
 if kind=='projection':
  from fractions import Fraction
  import struct
  z=root/'interval-check';z.mkdir()
  projection=(tool/'triangle_separation/Projection.swift').read_text().replace('private struct RopeTriangleProjection','struct RopeTriangleProjection')
  (z/'main.swift').write_text(projection+'\n'+(tool/'triangle_separation/IntervalMain.swift').read_text())
  run('interval-compile',['xcrun','swiftc','-O','-module-cache-path',z/'module-cache',z/'main.swift','-o',z/'strong-owl-live-physics-interval'])
  run('interval-export',[z/'strong-owl-live-physics-interval','Hangboards/clavellium-training-block/assets/primary.physics.json',z/'intervals.json'])
  def exact(bits):return Fraction.from_float(struct.unpack('d',struct.pack('Q',int(bits)))[0])
  rows=json.loads((z/'intervals.json').read_text())
  for i,row in enumerate(rows):
   x=sum((exact(p)*exact(n) for p,n in zip(row['p'],row['n'])),Fraction(0))
   assert exact(row['lo'])<=x<=exact(row['hi']),(i,row)
  (z/'result.json').write_text(json.dumps({'owner':REPO.name,'checked':len(rows),'allEncloseExactDot':True},indent=2))
  print('PASS',len(rows),'independent exact-rational interval checks')
 return 0

try:
 status=c.run('accepted-profile-compile',['perl','-e','alarm 150; exec @ARGV',*command],stage/'compile.log',dict(os.environ))
 if not status:status=c.run('accepted-profile-run',[str(stage/'strong-owl-live-physics-accepted-profile'),str(stage),str(checkpoint),str(prior)],stage/'run.log',dict(os.environ))
 if status==0 and args.kind in ('packed','projection'):
  status=check_queries(c,root,transform,args.kind)
 print((stage/('run.log' if (stage/'run.log').exists() else 'compile.log')).read_text())
finally:c.cleanup()
raise SystemExit(status)
