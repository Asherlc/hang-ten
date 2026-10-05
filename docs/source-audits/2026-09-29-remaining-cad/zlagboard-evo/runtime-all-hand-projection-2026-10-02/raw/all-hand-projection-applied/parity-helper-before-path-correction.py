from pathlib import Path
import json,hashlib,sys
p=Path('.context/placid-badger-cad-second-half/pr-readiness-repair-2026-10-02/evo');sha=lambda f:hashlib.sha256(Path(f).read_bytes()).hexdigest();rows=[]
for f in (p/'all-hand-projection-applied/source').rglob('*.swift'):
 actual=Path(f.relative_to(p/'all-hand-projection-applied/source'));rows.append(dict(category='source',path=str(actual),sha256=sha(actual),expected=sha(f),equal=sha(actual)==sha(f)))
c=json.loads((p/'all-hand-projection-code-parity/mach-o-parity.json').read_text())
for stage in ['built','installed']:
 for name,r in c[stage+'MachO'].items():
  f=Path(c[stage+'App'])/name;rows.append(dict(category=stage+'MachO',path=str(f),sha256=sha(f),expected=r['sha256'],equal=sha(f)==r['sha256']))
for r in json.loads((p/'strict-hand-suppression-package-parity.json').read_text())['packages']:
 rows.append(dict(category='package',path=r['path'],sha256=sha(r['path']),expected=r['expectedSHA256'],equal=sha(r['path'])==r['expectedSHA256']))
r=dict(allEqual=all(x['equal'] for x in rows),checks=rows);out=p/sys.argv[1];assert not out.exists();out.write_text(json.dumps(r,indent=2)+'\n');print(dict(allEqual=r['allEqual'],count=len(rows)));assert r['allEqual']
