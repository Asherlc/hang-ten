from pathlib import Path
import json,sys,zipfile,hashlib,shutil
n=Path('.context/placid-badger-cad-second-half/main-sync-2026-10-03');owned=json.loads((n/'ios/ownership.json').read_text());rpath=Path(owned['testResultBundle']);assert rpath.is_dir() and not rpath.is_symlink()
out=n/'raw-results';q=out/(sys.argv[1]+'-placid-badger-cad-second-half.xcresult.zip');assert not q.exists();rows=[]
with zipfile.ZipFile(q,'w',compression=zipfile.ZIP_DEFLATED,compresslevel=6) as z:
 for p in sorted(rpath.rglob('*')):
  if p.is_file():
   b=p.read_bytes();name=p.relative_to(rpath).as_posix();z.writestr(name,b);rows.append({'path':name,'bytes':len(b),'sha256':hashlib.sha256(b).hexdigest()})
with zipfile.ZipFile(q) as z:
 assert z.testzip() is None
 for row in rows:assert hashlib.sha256(z.read(row['path'])).hexdigest()==row['sha256']
(out/(sys.argv[1]+'-archive.json')).write_text(json.dumps({'archive':str(q),'archiveSHA256':hashlib.sha256(q.read_bytes()).hexdigest(),'rows':rows},indent=2)+'\n')
if '--remove' in sys.argv:shutil.rmtree(rpath);assert not rpath.exists()
print('Raw archive verified',len(rows))
