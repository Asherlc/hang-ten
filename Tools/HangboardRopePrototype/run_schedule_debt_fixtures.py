"""Extract current schedule; RED/GREEN bounded worker-busy clock checks."""
import argparse,hashlib,json,os,signal,sys
from pathlib import Path
sys.dont_write_bytecode=True
sys.path.insert(0,str(Path(__file__).resolve().parent))
from run_native_contact_screen import REPO,OwnedCommands
p=argparse.ArgumentParser();p.add_argument('--label',required=True);args=p.parse_args()
assert args.label and all(c in 'abcdefghijklmnopqrstuvwxyz0123456789-' for c in args.label)
root=REPO/'.context'/(REPO.name+'-schedule-debt-'+args.label);root.mkdir()
source=REPO/'HangTen/Models/LiveRopeController.swift'
fixture=Path(__file__).resolve().parent/'schedule_debt/Fixtures.swift'
text=source.read_text();text=text[:text.index('struct LiveRopeDeliveryIdentity')]
(root/'main.swift').write_text(text+'\n'+fixture.read_text())
cmd=['xcrun','swiftc','-O',str(root/'main.swift'),'-o',str(root/(REPO.name+'-clock'))]
(root/'provenance.json').write_text(json.dumps({'owner':REPO.name,'command':cmd,'sha256':{str(x.relative_to(REPO)):hashlib.sha256(x.read_bytes()).hexdigest() for x in [source,fixture,root/'main.swift',Path(__file__)]}},indent=2))
c=OwnedCommands(REPO.name,root)
for sig in [signal.SIGINT,signal.SIGTERM]:signal.signal(sig,c.interrupted)
try:
 status=c.run('compile',['perl','-e','alarm 30;exec @ARGV',*cmd],root/'compile.log',dict(os.environ))
 if not status:status=c.run('run',['perl','-e','alarm 10;exec @ARGV',str(root/(REPO.name+'-clock'))],root/'run.log',dict(os.environ))
 print((root/('run.log' if (root/'run.log').exists() else 'compile.log')).read_text())
finally:c.cleanup()
raise SystemExit(status)
