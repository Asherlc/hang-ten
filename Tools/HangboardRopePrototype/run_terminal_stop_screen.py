#!/usr/bin/env python3
"""Isolated pre-update terminal stationarity complete-step discriminator."""
import argparse, hashlib, json, os, re, signal, sys
from pathlib import Path
sys.dont_write_bytecode = True
sys.path.insert(0, str(Path(__file__).resolve().parent))
from run_native_contact_screen import REPO, OwnedCommands
from run_live_speed_screen import NAMES
from terminal_stop.snapshot import solver_source
def instrument(name,text):
    return solver_source(text) if name=='RopeDynamicsSolver.swift' else text

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('--label', required=True)
parser.add_argument('--diagnostic',action='store_true',help='no timers or speed retry; record rejected fixed schedule')
args = parser.parse_args()
assert args.label and all(c in 'abcdefghijklmnopqrstuvwxyz0123456789-' for c in args.label)
assert REPO.name == 'strong-owl-live-physics'
root = REPO/'.context'/(REPO.name+'-terminal-stop-'+args.label)
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
(sources/'ExactCheckpointJSON.swift').write_bytes((tool/'native_contact/ExactCheckpointJSON.swift').read_bytes())
main = (tool/'terminal_stop/main.swift').read_text()
if args.diagnostic:
    candidate=sources/'RopeDynamicsSolver.swift'
    text=candidate.read_text()
    needle='        if Self.terminalEligible(limit:terminalLimit,norm:max(maximum,abs(heightCorrection)),'
    assert text.count(needle)==1
    text=text.replace(needle,'''        if TerminalDiagnostic.enabled {
            TerminalDiagnostic.rows.append(["norm":max(maximum,abs(heightCorrection)),"strain":maximumStrain(),
                "trust":alpha,"previousFull":lastCorrectionFullStep,"limit":terminalLimit ?? -1])
        }
'''+needle)
    candidate.write_text(text+'\nenum TerminalDiagnostic {static var enabled=false;static var rows:[[String:Any]]=[]}\n')
    a=main.index('    for index in 0..<7 {');b=main.index('} catch {',a)
    main=main[:a]+'''    TerminalDiagnostic.enabled=true
    let frame=try candidate.step(dt:1.0/240,targetOrientation:target)
    TerminalDiagnostic.enabled=false
    let controlFrame=try control.step(dt:1.0/240,targetOrientation:target)
    let d:[String:Any]=["owner":"strong-owl-live-physics","closedScreenDiagnosticOnly":true,
        "candidateCorrections":candidate.reviewStepCorrections,"controlCorrections":control.reviewStepCorrections,
        "terminalStops":candidate.reviewTerminalStops,"candidatePhysical":frame.metrics.geometryAccepted,
        "controlPhysical":controlFrame.metrics.geometryAccepted,"differenceMeters":try compare(candidate,control),
        "proposals":TerminalDiagnostic.rows,"timersEnabled":false]
    try JSONSerialization.data(withJSONObject:d,options:[.prettyPrinted,.sortedKeys]).write(to:root.appendingPathComponent("diagnostic.json"))
    print("PASS diagnostic only",d);fflush(stdout)
'''+main[b:]
main='import Foundation\nimport simd\n'+(tool/'terminal_stop/Fixtures.swift').read_text()+'\n'+main
(sources/'main.swift').write_text(main)
files = sorted(sources.glob('*.swift'))
binary = stage/(REPO.name+'-terminal-stop')
command = ['xcrun','swiftc','-O','-D','DEBUG','-whole-module-optimization','-Xcc','-DACCELERATE_NEW_LAPACK',
           '-module-cache-path',str(stage/'module-cache'),*map(str,files),'-o',str(binary)]
inputs += [*files,Path(__file__),tool/'terminal_stop/snapshot.py',tool/'terminal_stop/Eligibility.swift',tool/'terminal_stop/Fixtures.swift',tool/'terminal_stop/main.swift',
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
