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
# Mandatory explicit completed cleanup, independently hash-bound and retained.
cleanupPath=Path(g['finalCleanupPath']);assert cleanupPath.is_file()
assert sha(cleanupPath)==g['finalCleanupSHA256']
cleanup=json.loads(cleanupPath.read_text())
assert cleanup['passed'] is True and cleanup['simulatorDeleted'] is True
assert cleanup['uuid']==g['simulatorUUID'] and cleanup['owner']==OWNER
expectedOwned=[SOURCE/'ios'/('DerivedData-'+OWNER),SOURCE/'ios'/('build-'+OWNER+'.xcresult'),SOURCE/'ios'/('tests-'+OWNER+'.xcresult')]
assert {Path(x['path']).resolve() for x in cleanup['ownedPaths']}=={x.resolve() for x in expectedOwned}
assert all(x['absent'] is True for x in cleanup['ownedPaths']) and not cleanup['errors']
assert any(Path(x['source']).resolve()==cleanupPath.resolve() and x['sha256']==g['finalCleanupSHA256'] for x in rows)
# All already-frozen setup/control bytes must remain represented exactly.
baseInventory=Path(g['frozenControlInventoryPath']);assert sha(baseInventory)==g['frozenControlInventorySHA256']
baseRows=json.loads(baseInventory.read_text())['files'];lookup={x['source']:x for x in rows}
assert len(lookup)==len(rows)
for x in baseRows:assert lookup.get(x['source'])==x,x['source']
assert g['includedCompletedArmPaths'] and g['allIncludedArmsComplete'] is True
for arm in g['includedCompletedArmPaths']:
 p=Path(arm);assert p.resolve().is_relative_to(SOURCE.resolve())
 assert json.loads((p/'completion.json').read_text())['captureCompleted'] is True
 assert any(Path(x['source']).resolve()==(p/'completion.json').resolve() for x in rows)

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
out=SOURCE/'offline-prep/copy-verification-v2.json';assert not out.exists();out.write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps({'copiedFiles':len(rows),'report':str(out),'sha256':sha(out)},indent=2))
