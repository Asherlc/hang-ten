"""Owned, isolated arithmetic ceiling; never an app or cold-QP acceptance."""
import sys,os,json,hashlib,signal,atexit,argparse
from pathlib import Path
from run_native_contact_screen import OwnedCommands,REPO
parser=argparse.ArgumentParser();parser.add_argument('--label',required=True);parser.add_argument('--validate-only',action='store_true');args=parser.parse_args()
owner=Path(os.environ.get('PASEO_WORKTREE_PATH',REPO)).resolve()
if owner!=REPO or os.environ.get('HANGTEN_PRIMITIVE_OWNER')!=owner.name:parser.error('Use owned launcher')
if not args.label or any(c not in 'abcdefghijklmnopqrstuvwxyz0123456789-_'for c in args.label):parser.error('Invalid label')
root=REPO/'.context'/f'{owner.name}-packed-primitives';output=root/args.label
if any(p.is_symlink()for p in [REPO/'.context',root,output]):parser.error('Symlink output')
output.mkdir();snapshot=output/'source-inputs';snapshot.mkdir()
inputs=[Path(__file__),Path(__file__).with_suffix('.sh'),REPO/'Tools/HangboardRopePrototype/run_native_contact_screen.py',REPO/'Tools/HangboardRopePrototype/native_contact/SparseLDL.swift',REPO/'Tools/HangboardRopePrototype/native_contact/PackedPrimitive.swift',REPO/'Tools/HangboardRopePrototype/native_contact/PrimitiveCeiling.swift']
for p in inputs:(snapshot/p.name).write_bytes(p.read_bytes())
# Read-only same-file extension exposes actual private patterns/state for exact
# diagnostic comparison; reference numeric arithmetic is never replaced.
reference=snapshot/'SparseLDL.swift'
reference.write_text(reference.read_text()+"""
extension SparseLDL {
 func ceilingPattern()->[String:[Int]] {
  ["size":[size],"inputStarts":inputStarts,"inputIndices":inputIndices.map{Int($0)},"permutation":permutation,
   "upperStarts":upperStarts,"upperRows":upperRows,"upperSlots":upperSlots,"rowStarts":rowStarts,"rowItems":rowItems,
   "lowerStarts":lowerStarts,"lowerRows":lowerRows,"negative":(0..<size).map{negative.contains($0) ? 1:0}]
 }
 func ceilingState()->[[Double]] {[diagonal,lowerValues,scale]}
}
""")
pattern=REPO/'.context/strong-owl-live-physics-sparse-ldl/ordering-discriminator/pattern.json'
expected='b9ab3794ceb32de076e1399d097aca0aea7f651a15fcfd6bcd907827275e237e'
assert hashlib.sha256(pattern.read_bytes()).hexdigest()==expected
(snapshot/'pattern.json').write_bytes(pattern.read_bytes())
(snapshot/'main.swift').write_bytes((snapshot/'PrimitiveCeiling.swift').read_bytes())
binary=output/f'{owner.name}-primitive-ceiling'
command=['xcrun','swiftc','-O','-whole-module-optimization','-module-cache-path',str(output/'module-cache'),str(reference),str(snapshot/'PackedPrimitive.swift'),str(snapshot/'main.swift'),'-o',str(binary)]
provenance={'owner':owner.name,'runtimeAdoption':False,'referenceExtension':'Read-only private pattern/state exposure appended; arithmetic unchanged','sourceSHA256':{str(p):hashlib.sha256(p.read_bytes()).hexdigest()for p in snapshot.iterdir()},'compileCommand':command,'patternSHA256':expected,'validationOnly':args.validate_only}
(output/'provenance.json').write_text(json.dumps(provenance,indent=2)+'\n')
environment=dict(os.environ,HANGTEN_PRIMITIVE_VALIDATE_ONLY='1'if args.validate_only else'0')
commands=OwnedCommands(owner.name,root);atexit.register(commands.cleanup)
for sig in [signal.SIGINT,signal.SIGTERM]:signal.signal(sig,commands.interrupted)
try:
 status=commands.run('primitive-compile',command,output/'compile.log',environment)
 if not status:status=commands.run('primitive-probe',[str(binary),str(snapshot/'pattern.json'),str(output/'result.json')],output/'run.log',environment)
 print((output/('compile.log'if status and not(output/'run.log').exists()else'run.log')).read_text())
finally:commands.cleanup()
raise SystemExit(status)
