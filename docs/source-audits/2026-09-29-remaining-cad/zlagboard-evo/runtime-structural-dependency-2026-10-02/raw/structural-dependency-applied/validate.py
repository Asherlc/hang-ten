from pathlib import Path
import sys,subprocess
E=Path('.context/placid-badger-cad-second-half/pr-readiness-repair-2026-10-02/evo');arm=sys.argv[1];assert arm in ['retained-detach','ordinary'];p=E/('structural-dependency-'+arm+'-landscape');helpers=E/'structural-dependency-applied/runtime-helpers'
for n in ['check-cpu-semantics.py','check-frames.py','check-constructors.py','check-hands.py','check-ownership.py','check-navigation.py']:
 arg=arm if n in ['check-ownership.py','check-navigation.py'] else p.name;out=p/(n+'.stdout');err=p/(n+'.stderr');assert not out.exists() and not err.exists();r=subprocess.run(['rtk','proxy','python3',str(helpers/n),arg],capture_output=True);out.write_bytes(r.stdout);err.write_bytes(r.stderr);print(n,r.returncode,flush=True);r.check_returncode()
