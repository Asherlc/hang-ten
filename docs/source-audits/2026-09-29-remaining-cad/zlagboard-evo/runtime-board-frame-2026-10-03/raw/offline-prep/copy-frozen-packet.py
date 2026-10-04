"""Copy only root-frozen explicit inventory; no directory discovery or live-file copy."""
from pathlib import Path
import json,sys,hashlib,shutil
OWNER='placid-badger-cad-second-half'
SOURCE=Path('.context')/OWNER/'board-frame-fix-2026-10-03'
DEST=Path('docs/source-audits/2026-09-29-remaining-cad/zlagboard-evo/runtime-board-frame-2026-10-03')
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
gatePath=Path(sys.argv[1]);expectedGateHash=sys.argv[2]
assert sha(gatePath)==expectedGateHash
g=json.loads(gatePath.read_text());assert g['copyAuthorizedByRoot'] is True and g['allIncludedTreesFrozen'] is True
assert g['destination']==str(DEST) and g['owner']==OWNER
assert g['runtimeResourcesReferencedOnly'] is True
inventory=Path(g['inventoryPath']);assert sha(inventory)==g['inventorySHA256']
rows=json.loads(inventory.read_text())['files'];assert rows
seen=set()
for x in rows:
 p=Path(x['source']);relative=Path(x['retained'])
 assert p.resolve().is_relative_to(SOURCE.resolve()) and p.is_file() and not p.is_symlink()
 assert not relative.is_absolute() and '..' not in relative.parts and str(relative) not in seen
 assert relative.parts[0]=='raw';seen.add(str(relative))
 assert sha(p)==x['sha256'] and p.stat().st_size==x['bytes']
for x in rows:
 p=Path(x['source']);q=DEST/x['retained'];q.parent.mkdir(parents=True,exist_ok=True)
 if q.exists():assert sha(q)==x['sha256'] and q.stat().st_size==x['bytes'],'Never overwrite different historical bytes'
 else:shutil.copyfile(p,q)
 assert sha(p)==sha(q)==x['sha256'] and q.stat().st_size==x['bytes']
report={'copyGatePath':str(gatePath),'copyGateSHA256':expectedGateHash,'inventoryPath':str(inventory),'inventorySHA256':sha(inventory),'copiedFiles':len(rows),'entries':rows,'status':'Exact copies only; root-authored summary/final manifest separate','sourceOrRuntimeModified':False}
out=SOURCE/'offline-prep/copy-verification.json';assert not out.exists();out.write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps({'copiedFiles':len(rows),'report':str(out),'sha256':sha(out)},indent=2))
