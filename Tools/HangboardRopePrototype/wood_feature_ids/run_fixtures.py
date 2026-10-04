import os,signal,sys,json,hashlib
from pathlib import Path
sys.dont_write_bytecode=True
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from run_native_contact_screen import REPO,OwnedCommands
root=REPO/'.context'/f'{REPO.name}-wood-feature-id-fixtures-{sys.argv[1]}'
root.mkdir();(root/'main.swift').write_text('import Foundation\ndo {try woodFeatureFixtures();print("PASS wood feature fixtures")} catch {print("FAIL",error);exit(2)}\n')
p=Path(__file__).resolve().parent
math=(p/'Math.swift').read_text()
assert '--red' not in sys.argv
(root/'Math.swift').write_text(math);(root/'Fixtures.swift').write_bytes((p/'Fixtures.swift').read_bytes())
(root/'provenance.json').write_text(json.dumps({'owner':REPO.name,'hashes':{f.name:hashlib.sha256(f.read_bytes()).hexdigest() for f in [root/'main.swift',root/'Math.swift',root/'Fixtures.swift']}},indent=2))
owner=OwnedCommands(REPO.name,root)
for s in [signal.SIGINT,signal.SIGTERM]:signal.signal(s,owner.interrupted)
try:
    status=owner.run('compile',['perl','-e','alarm 120;exec @ARGV','xcrun','swiftc','-O',str(root/'Math.swift'),str(root/'Fixtures.swift'),str(root/'main.swift'),'-module-cache-path',str(root/'module-cache'),'-o',str(root/'fixtures')],root/'compile.log',dict(os.environ))
    if not status:status=owner.run('fixtures',[str(root/'fixtures')],root/'run.log',dict(os.environ))
    print((root/('run.log' if (root/'run.log').exists() else 'compile.log')).read_text())
finally:owner.cleanup()
raise SystemExit(status)
