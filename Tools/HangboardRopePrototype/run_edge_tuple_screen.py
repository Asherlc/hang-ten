#!/usr/bin/env python3
"""Complete-step screen of observed per-face edge tuple allocation removal."""
import argparse, hashlib, json, os, re, signal, sys
from pathlib import Path
sys.dont_write_bytecode = True
sys.path.insert(0, str(Path(__file__).resolve().parent))
from run_native_contact_screen import REPO, OwnedCommands
from run_live_speed_screen import NAMES
from edge_tuple.snapshot import collider_source
def instrument(name,text):
    return collider_source(text) if name=='RopeTriangleCollider.swift' else text

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('--label', required=True)
args = parser.parse_args()
assert args.label and all(c in 'abcdefghijklmnopqrstuvwxyz0123456789-' for c in args.label)
assert REPO.name == 'strong-owl-live-physics'
root = REPO/'.context'/(REPO.name+'-edge-tuple-'+args.label)
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
main = (tool/'triangle_kernel_cache/main.swift').read_text()
(sources/'main.swift').write_text(main)
files = sorted(sources.glob('*.swift'))
binary = stage/(REPO.name+'-edge-tuple')
command = ['xcrun','swiftc','-O','-D','DEBUG','-whole-module-optimization','-Xcc','-DACCELERATE_NEW_LAPACK',
           '-module-cache-path',str(stage/'module-cache'),*map(str,files),'-o',str(binary)]
inputs += [*files,Path(__file__),tool/'edge_tuple/snapshot.py',tool/'triangle_kernel_cache/main.swift',
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
