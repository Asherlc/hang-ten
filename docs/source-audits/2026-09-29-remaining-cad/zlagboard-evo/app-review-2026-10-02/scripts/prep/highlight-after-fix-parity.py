from pathlib import Path
import hashlib,json,subprocess
s=Path('.context/placid-badger-cad-second-half/zlagboard-evo/ios-resume-2026-10-02')
built=s/('DerivedData-'+Path.cwd().name)/'Build/Products/Debug-iphonesimulator/HangTen.app'
out=s/'highlight-regression'/'after-fix-parity';out.mkdir(parents=True,exist_ok=False)
uid=(s/'simulator-ready').read_text().strip()
container=subprocess.check_output(['rtk','proxy','xcrun','simctl','get_app_container',uid,'com.hangten.training','app'])
(out/'installed-container.txt').write_bytes(container)
installed=Path(container.decode().strip())
expected=subprocess.check_output(['rtk','proxy','python3','Tools/HangboardCAD/board_manifest.py','--package','zlagboard-evo'])
sha=lambda data:hashlib.sha256(data).hexdigest()
r=[]
for label,base in [('staged',built),('installed',installed)]:
 for name,original in [('board.json',expected),('assets/primary.model.json',Path('Hangboards/zlagboard-evo/assets/primary.model.json').read_bytes()),('assets/primary.usdz',Path('Hangboards/zlagboard-evo/assets/primary.usdz').read_bytes())]:
  paths=[p for p in base.rglob(Path(name).name) if 'zlagboard-evo' in p.relative_to(base).parts]
  assert len(paths)==1,(label,name,paths)
  data=paths[0].read_bytes(); r.append({'stage':label,'relativePath':str(paths[0].relative_to(base)),'sha256':sha(data),'expectedSHA256':sha(original),'bytesEqual':data==original})
(out/'package-parity.json').write_text(json.dumps(r,indent=2)+'\n')
assert all(x['bytesEqual'] for x in r)
record={'builtBinarySHA256':sha((built/'HangTen').read_bytes()),'installedBinarySHA256':sha((installed/'HangTen').read_bytes())}
record['identical']=record['builtBinarySHA256']==record['installedBinarySHA256']; assert record['identical']
(out/'binary-parity.json').write_text(json.dumps(record,indent=2)+'\n')
print('6 package comparisons and built/installed binary parity passed')
