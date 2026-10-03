#!/usr/bin/env python3
"""Complete original floating edge-witness bounding screen with matched unrolled control."""
import argparse, hashlib, json, os, re, signal, sys
from pathlib import Path
sys.dont_write_bytecode = True
sys.path.insert(0, str(Path(__file__).resolve().parent))
from run_native_contact_screen import REPO, OwnedCommands
from run_live_speed_screen import NAMES
from fp_edge_bounds.snapshot import collider_source
from edge_tuple.snapshot import collider_source as unrolled_source
def instrument(name,text):
    return collider_source(text) if name=='RopeTriangleCollider.swift' else text

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('--label', required=True)
args = parser.parse_args()
assert args.label and all(c in 'abcdefghijklmnopqrstuvwxyz0123456789-' for c in args.label)
assert REPO.name == 'strong-owl-live-physics'
root = REPO/'.context'/(REPO.name+'-fp-edge-bounds-'+args.label)
root.mkdir()
stage = root/'native'; stage.mkdir()
sources = stage/'sources'; sources.mkdir()
tool = Path(__file__).resolve().parent
adapter = (tool/'stock_chain/CheckpointAdapter.swift').read_text()
inputs = [REPO/'HangTen/Models'/name for name in NAMES]
for path in inputs:
    original = path.read_text()
    text = instrument(path.name, original)
    if path.name == 'RopeDynamicsSolver.swift':
        text = text.replace('private extension SIMD4', 'extension SIMD4')+'\n'+adapter
        original = re.sub(r'private extension SIMD4 where Scalar == Double \{\s*var xyz:SIMD3<Double>\{SIMD3\(x,y,z\)\}\s*\}', '', original)+'\n'+adapter
    (sources/path.name).write_text(text)
    control = re.sub(r'\bRope[A-Z]\w*', lambda m: 'Control'+m[0], original)
    (sources/('Control'+path.name)).write_text(control)
    matched=unrolled_source(original) if path.name=='RopeTriangleCollider.swift' else original
    matched=re.sub(r'\bRope[A-Z]\w*',lambda m:'Matched'+m[0],matched)
    (sources/('Matched'+path.name)).write_text(matched)
(sources/'ExactCheckpointJSON.swift').write_bytes((tool/'native_contact/ExactCheckpointJSON.swift').read_bytes())
main = (tool/'triangle_kernel_cache/main.swift').read_text()
for line in main.splitlines():
    if any(key in line for key in ['let controlInput=','let controlSeed=','var control=']):
        counterpart=line.replace('ControlRope','MatchedRope').replace('controlInput','matchedInput').replace('controlSeed','matchedSeed').replace('controlCollider','matchedCollider').replace('var control=','var matched=')
        main=main.replace(line,line+'\n'+counterpart)
needle='let collider=try RopeTriangleCollider(input:input),controlCollider=try ControlRopeTriangleCollider(input:controlInput)'
assert main.count(needle)==1
main=main.replace(needle,needle+'\nlet matchedCollider=try MatchedRopeTriangleCollider(input:matchedInput)')
a=main.index('func compare(');b=main.index('for step in 1...139',a)
main=main[:b]+main[a:b].replace('ControlRope','MatchedRope')+main[b:]
main=main.replace('    _ = try control.step(dt:1.0/240,targetOrientation:target)','    _ = try control.step(dt:1.0/240,targetOrientation:target)\n    _ = try matched.step(dt:1.0/240,targetOrientation:target)')
main=main.replace('    try compare(candidate,control)','    try compare(candidate,control);try compare(candidate,matched)')
main=main.replace('    var x=candidate,y=control','    var x=candidate,y=control,z=matched')
main=main.replace('candidateSeconds=0.0,controlSeconds=0.0','candidateSeconds=0.0,controlSeconds=0.0,matchedSeconds=0.0')
needle='    alarm(10)\n    if index%2==0'
assert main.count(needle)==1
main=main.replace(needle,'''    func measureMatched() throws {
        let t=ProcessInfo.processInfo.systemUptime
        _ = try z.step(dt:1.0/240,targetOrientation:target)
        matchedSeconds=ProcessInfo.processInfo.systemUptime-t
    }
'''+needle)
main=main.replace('try measureControl();try measureCandidate()','try measureControl();try measureMatched();try measureCandidate()').replace('try measureCandidate();try measureControl()','try measureCandidate();try measureMatched();try measureControl()')
main=main.replace('    try compare(x,y)','    try compare(x,y);try compare(x,z)')
main=main.replace('"ratio":candidateSeconds/controlSeconds','"ratio":candidateSeconds/controlSeconds,"matchedSeconds":matchedSeconds,"matchedRatio":candidateSeconds/matchedSeconds')
main=main.replace('let result:[String:Any]=','let matchedMedian=reports.map{$0["matchedRatio"] as! Double}.sorted()[3]\nlet passed=median<=0.8 && matchedMedian<=0.8\nlet result:[String:Any]=')
main=main.replace('"medianRatio":median,','"medianRatio":median,"medianMatchedRatio":matchedMedian,').replace('"performancePassed":median<=0.8','"performancePassed":passed')
main=main.replace('print(median<=0.8 ?', 'print(passed ?').replace('if median>0.8 {exit(2)}','if !passed {exit(2)}')
main='import Foundation\nimport simd\n'+(tool/'fp_edge_bounds/Fixtures.swift').read_text()+'\n'+main

(sources/'main.swift').write_text(main)
files = sorted(sources.glob('*.swift'))
binary = stage/(REPO.name+'-fp-edge-bounds')
command = ['xcrun','swiftc','-O','-D','DEBUG','-whole-module-optimization','-Xcc','-DACCELERATE_NEW_LAPACK',
           '-module-cache-path',str(stage/'module-cache'),*map(str,files),'-o',str(binary)]
inputs += [*files,Path(__file__),tool/'fp_edge_bounds/snapshot.py',tool/'fp_edge_bounds/Bounds.swift',tool/'fp_edge_bounds/Fixtures.swift',tool/'edge_tuple/snapshot.py',tool/'triangle_kernel_cache/main.swift',
           REPO/'Hangboards/clavellium-training-block/assets/primary.physics.json']
(stage/'provenance.json').write_text(json.dumps({'owner':REPO.name,'command':command,
    'hashes':{str(p.relative_to(REPO)):hashlib.sha256(p.read_bytes()).hexdigest() for p in inputs}},indent=2))
c = OwnedCommands(REPO.name,stage)
for sig in [signal.SIGINT,signal.SIGTERM]:signal.signal(sig,c.interrupted)
env = dict(os.environ,HANGTEN_REVIEW_PHYSICAL_CONVERGENCE='1')
try:
    status = c.run('compile',['perl','-e','alarm 150;exec @ARGV',*command],stage/'compile.log',env)
    if not status:status = c.run('run',['perl','-e','alarm 300;exec @ARGV',str(binary),str(stage)],stage/'run.log',env)
    print((stage/('run.log' if (stage/'run.log').exists() else 'compile.log')).read_text())
finally:c.cleanup()
raise SystemExit(status)
