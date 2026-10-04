from pathlib import Path
import subprocess,json
E=Path('.context/placid-badger-cad-second-half/pr-readiness-repair-2026-10-02/evo');p=E/'weak-hand-census-landscape';h=E/'weak-hand-census-applied/runtime-helpers';results=[]
for name in ['check-cpu-semantics.py','check-frames.py','check-constructors.py','check-ownership.py','check-navigation.py','check-real-hands.py','check-weak-hand-census.py','compare-prior-real-hands.py']:
 args=[p.name] if name in ['check-cpu-semantics.py','check-frames.py','check-constructors.py'] else []
 out=p/(name+'.stdout');err=p/(name+'.stderr');assert not out.exists() and not err.exists()
 r=subprocess.run(['rtk','proxy','python3',str(h/name),*args],capture_output=True);out.write_bytes(r.stdout);err.write_bytes(r.stderr);results.append(dict(helper=name,exitStatus=r.returncode));print(name,r.returncode,flush=True)
 if r.returncode:break
(p/'validator-command-results.json').write_text(json.dumps(results,indent=2)+'\n')
assert len(results)==8 and all(x['exitStatus']==0 for x in results)
