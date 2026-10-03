#!/usr/bin/env python3
"""Test-first synthetic contact-bundle progress with the original coupled QP."""
import argparse,pathlib,sys,json,hashlib,os,signal
sys.dont_write_bytecode=True
repo=pathlib.Path.cwd();assert repo.name=='strong-owl-live-physics'
tool=pathlib.Path(__file__).resolve().parent;sys.path.insert(0,str(tool))
from run_native_contact_screen import OwnedCommands
from run_live_speed_screen import NAMES
p=argparse.ArgumentParser(description=__doc__);p.add_argument('--label',required=True);args=p.parse_args()
assert args.label and all(c in 'abcdefghijklmnopqrstuvwxyz0123456789-' for c in args.label)
root=repo/'.context'/(repo.name+'-contact-bundle-'+args.label);root.mkdir()
source=root/'sources';source.mkdir()
inputs=[repo/'HangTen/Models'/name for name in NAMES]
bundle=tool/'contact_bundle/Bundle.swift'
for path in inputs:
    text=path.read_text()
    if path.name=='RopeTriangleCollider.swift':text+='\n'+bundle.read_text()
    (source/path.name).write_text(text)
control=tool/'contact_bundle/Control.swift'
fixture=tool/'contact_bundle/Fixtures.swift'
(source/'main.swift').write_text(control.read_text()+'\n'+fixture.read_text())
files=sorted(source.glob('*.swift'));binary=root/(repo.name+'-contact-bundle-fixtures')
cmd=['xcrun','swiftc','-O','-D','DEBUG','-whole-module-optimization','-Xcc','-DACCELERATE_NEW_LAPACK','-module-cache-path',str(root/'module-cache'),*map(str,files),'-o',str(binary)]
inputs += [*files,bundle,control,fixture,pathlib.Path(__file__)]
(root/'provenance.json').write_text(json.dumps({'owner':repo.name,'command':cmd,'sha256':{str(x.relative_to(repo)):hashlib.sha256(x.read_bytes()).hexdigest() for x in inputs}},indent=2))
c=OwnedCommands(repo.name,root)
for sig in [signal.SIGINT,signal.SIGTERM]:signal.signal(sig,c.interrupted)
try:
    status=c.run('compile',['perl','-e','alarm 150;exec @ARGV',*cmd],root/'compile.log',dict(os.environ))
    if not status:status=c.run('run',['perl','-e','alarm 30;exec @ARGV',str(binary),str(root)],root/'run.log',dict(os.environ))
    print((root/('run.log' if (root/'run.log').exists() else 'compile.log')).read_text())
finally:c.cleanup()
raise SystemExit(status)
