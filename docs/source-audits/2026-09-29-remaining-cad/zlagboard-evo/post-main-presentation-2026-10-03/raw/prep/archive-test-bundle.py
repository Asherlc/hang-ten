from pathlib import Path
import sys,json,hashlib,zipfile,shutil
n=Path(__file__).parent.parent;p=n/'ios/tests-placid-badger-cad-second-half.xcresult';d=n/sys.argv[1];assert d.is_dir();z=d/'tests-placid-badger-cad-second-half.xcresult.zip';entries=[]
with zipfile.ZipFile(z,'x',compression=zipfile.ZIP_DEFLATED) as a:
 for f in sorted(p.rglob('*')):
  if f.is_file():
   data=f.read_bytes();rel=str(f.relative_to(p));entries.append(dict(path=rel,sha256=hashlib.sha256(data).hexdigest()));a.writestr(rel,data)
with zipfile.ZipFile(z) as a:assert all(hashlib.sha256(a.read(e['path'])).hexdigest()==e['sha256'] for e in entries)
(d/'bundle-archive.json').write_text(json.dumps(dict(source=str(p.resolve()),archive=str(z.resolve()),sha256=hashlib.sha256(z.read_bytes()).hexdigest(),members=entries,verified=True),indent=2)+'\n');shutil.rmtree(p);assert not p.exists();(d/'bundle-deletion.json').write_text(json.dumps(dict(exactOwnedPath=str(p.resolve()),deleted=True))+'\n')
