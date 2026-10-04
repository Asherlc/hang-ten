import json,pathlib,shutil
p=pathlib.Path(__file__).resolve().parent
d=json.loads((p/'python-deps-ownership.json').read_text())
owned=p/'python-deps'
assert d['owner']=='placid-badger-cad-second-half' and d['path']==str(owned)
assert not owned.is_symlink()
if owned.exists():shutil.rmtree(owned)
assert not owned.exists()
(p/'python-deps-cleanup-verification.json').write_text(json.dumps({'owner':d['owner'],'exactPath':str(owned),'absent':True},indent=2)+'\n')
