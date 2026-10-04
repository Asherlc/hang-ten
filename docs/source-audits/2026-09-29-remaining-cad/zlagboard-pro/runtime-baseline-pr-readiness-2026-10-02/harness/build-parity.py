from pathlib import Path
import json,hashlib,subprocess
s=Path('.context/placid-badger-cad-second-half/pr-readiness-repair-2026-10-02/ios-diagnosis');app=s/'DerivedData-placid-badger-cad-second-half/Build/Products/Debug-iphonesimulator/HangTen.app';sha=lambda b:hashlib.sha256(b).hexdigest();expected=subprocess.check_output(['rtk','proxy','python3','Tools/HangboardCAD/board_manifest.py','--package','zlagboard-pro']);checks=[]
for name,data in [('board.json',expected),('primary.usdz',Path('Hangboards/zlagboard-pro/assets/primary.usdz').read_bytes()),('primary.model.json',Path('Hangboards/zlagboard-pro/assets/primary.model.json').read_bytes())]:
 paths=[p for p in app.rglob(name) if 'zlagboard-pro' in p.relative_to(app).parts];assert len(paths)==1,(name,paths);actual=paths[0].read_bytes();checks.append({'file':str(paths[0].relative_to(app)),'sha256':sha(actual),'expectedSHA256':sha(data),'bytesEqual':actual==data})
(s/'staged-package-parity.json').write_text(json.dumps(checks,indent=2)+'\n');assert all(c['bytesEqual'] for c in checks)
magic={bytes.fromhex(x) for x in ['feedface','cefaedfe','feedfacf','cffaedfe','cafebabe','bebafeca','cafebabf','bfbafeca']};code={}
for p in app.rglob('*'):
 if p.is_file():
  with p.open('rb') as f:m=f.read(4)
  if m in magic:code[str(p.relative_to(app))]={'sha256':sha(p.read_bytes()),'bytes':p.stat().st_size}
(s/'built-mach-o-sha256.json').write_text(json.dumps(code,indent=2)+'\n');(s/'generated-board-at-build.json').write_bytes(expected);print('Fresh built package parity:',len(checks),'exact; Mach-O payloads:',len(code))
