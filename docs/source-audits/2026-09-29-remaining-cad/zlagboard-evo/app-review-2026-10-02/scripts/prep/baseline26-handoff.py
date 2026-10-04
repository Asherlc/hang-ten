from pathlib import Path
import sys,json,hashlib,subprocess,time
old,s,products=map(Path,sys.argv[1:]);original=old/'DerivedData-placid-badger-cad-second-half/Build/Products/Debug-iphonesimulator/HangTen.app';copy=products/'HangTen.app'
def hashes(base):return {str(p.relative_to(base)):hashlib.sha256(p.read_bytes()).hexdigest() for p in base.rglob('*') if p.is_file()}
a,b=hashes(original),hashes(copy);assert a==b
(s/'preserved-app-sha256.json').write_text(json.dumps({'original':str(original),'preserved':str(copy),'allFilesIdentical':True,'files':b},indent=2)+'\n')
(old/'cleanup-requested').touch()
for _ in range(120):
 if (old/'cleanup-verification.json').exists():
  r=json.loads((old/'cleanup-verification.json').read_text())
  if all(r[k] for k in ['simulatorDeleted','derivedDataDeleted','resultBundleDeleted','testResultBundleDeleted']):
   (s/'predecessor-cleanup-verification.json').write_bytes((old/'cleanup-verification.json').read_bytes());break
 time.sleep(1)
else:raise RuntimeError('Old lifecycle cleanup not verified; no newdevice creation allowed')
rows=json.loads(subprocess.check_output(['rtk','proxy','xcrun','simctl','list','devices','--json']))['devices'];assert not any(d['udid']==r['uuid'] for ds in rows.values() for d in ds)
print('Baseline app byte-exact preserved; prior lifecycle cleanup verified before newUUID creation')
