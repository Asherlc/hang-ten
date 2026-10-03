from pathlib import Path
import json,subprocess,sys
E=Path('.context/placid-badger-cad-second-half/pr-readiness-repair-2026-10-02/evo');arm=sys.argv[1];assert arm in ['control','unmount'];name='train-postboot-'+arm+'-landscape';p=E/name
for script in ['check-normal-all-hand-workout.py','check-strict-hand-lifetime.py','check-normal-strict-hand-absence.py','check-normal-projection-hosts.py','train-host-proposal/check-train-constructors.py','train-postboot-protocol/check-trial.py','train-postboot-protocol/check-navigation.py']:
 tag=Path(script).stem;out=p/(tag+'.stdout');err=p/(tag+'.stderr');assert not out.exists() and not err.exists()
 r=subprocess.run(['rtk','proxy','python3',str(E/script),name],capture_output=True);out.write_bytes(r.stdout);err.write_bytes(r.stderr);print(tag,r.returncode,flush=True);r.check_returncode()
