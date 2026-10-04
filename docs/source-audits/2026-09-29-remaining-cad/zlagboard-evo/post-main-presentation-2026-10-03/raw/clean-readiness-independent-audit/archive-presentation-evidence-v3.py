"""Plan/copy exact frozen evidence; default only writes plan JSON to stdout. No runtime operations."""
from pathlib import Path
import argparse,hashlib,json,os
OWNER='placid-badger-cad-second-half'
ROOT=Path('.context')/OWNER/'post-main-render-fix-2026-10-03'
DEST=Path('docs/source-audits/2026-09-29-remaining-cad/zlagboard-evo/post-main-presentation-2026-10-03/raw')
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
def exclusive_json(path,obj):
 data=(json.dumps(obj,indent=2)+'\n').encode()
 if path.exists():
  assert path.read_bytes()==data,'Existing manifest differs; never overwrite: '+str(path)
 else:
  with path.open('xb') as f:f.write(data)
a=argparse.ArgumentParser();a.add_argument('--final',action='store_true');a.add_argument('--copy-plan',type=Path);args=a.parse_args()
if args.copy_plan:
 plan=json.loads(args.copy_plan.read_text());assert plan['sourceRoot']==str(ROOT) and plan['destinationRoot']==str(DEST)
 assert plan['owner']==OWNER and plan['schemaVersion']==1
 # Verify the entire source and every existing destination before any copy.
 for x in plan['files']:
  rel=Path(x['relativePath']);assert not rel.is_absolute() and '..' not in rel.parts
  source=ROOT/rel;target=DEST/rel
  assert not source.is_symlink() and sha(source)==x['sha256'] and source.stat().st_size==x['bytes'],'Source changed: '+str(source)
  if target.exists():assert not target.is_symlink() and sha(target)==x['sha256'],'Destination mismatch: '+str(target)
 for x in plan['files']:
  source=ROOT/x['relativePath'];target=DEST/x['relativePath'];target.parent.mkdir(parents=True,exist_ok=True)
  if not target.exists():
   data=source.read_bytes();assert hashlib.sha256(data).hexdigest()==x['sha256']
   with target.open('xb') as f:f.write(data)
  assert sha(target)==x['sha256']
 digest=hashlib.sha256(json.dumps(plan,sort_keys=True,separators=(',',':')).encode()).hexdigest()
 exclusive_json(DEST.parent/('raw-copy-manifest-'+digest+'.json'),plan)
 print(json.dumps({'copiedOrVerifiedFiles':len(plan['files']),'bytes':sum(x['bytes'] for x in plan['files']),'inventoryDigest':digest,'allCopiedHashesMatch':True,'finalSnapshot':plan['finalSnapshot']}))
else:
 excluded=[];files=[];deferred={}
 if args.final:
  cleanup=json.loads((ROOT/'ios/cleanup-verification.json').read_text())
  assert cleanup['owner']==OWNER and cleanup['passed'] is True and cleanup['simulatorDeleted'] is True and all(x['absent'] for x in cleanup['ownedPaths']) and not cleanup['errors']
 else:deferred['ios']='Controller-owned outputs deferred until final verified cleanup; no live snapshot.'
 for folder in ROOT.iterdir():
  if not folder.is_dir() or folder.name=='ios':continue
  if (folder/'runtime-release.json').exists() or folder.name=='hand-policy-control':
   c=folder/'completion.json';q=folder/'cleanup.json'
   if not c.exists() or not q.exists():deferred[folder.name]='Capture not finalized: completion/cleanup absent.'
   elif json.loads(q.read_text()).get('passed') is not True:deferred[folder.name]='Exact per-run cleanup not verified.'
 # Test logs are only frozen after raw bundle archive+deletion are retained.
 for folder in ROOT.iterdir():
  if folder.is_dir() and (folder/'command.json').exists() and (folder/'stdout.log').exists():
   required=['exit.json','bundle-archive.json','bundle-deletion.json']
   if not all((folder/name).exists() for name in required):
    deferred[folder.name]='Readiness test result lifecycle not frozen; require exit, exact bundle archive and deletion records.'
  if folder.is_dir() and (folder/'build.command.json').exists() and not (folder/'build.exit.json').exists():
   deferred[folder.name]='Readiness build still active; completed exit record absent.'
 # Final snapshot cannot silently omit any pending comparison or test evidence.
 if args.final:assert not deferred,'Final archive has unfinished evidence: '+str(deferred)
 def walk(folder):
  for path in sorted(folder.iterdir()):
   rel=path.relative_to(ROOT)
   if path.is_symlink():raise AssertionError('Symlink not silently followed: '+str(rel))
   if rel.parts[0] in deferred:
    if len(rel.parts)==1:excluded.append({'path':str(rel),'reason':deferred[rel.parts[0]],'deferred':True})
    continue
   if path.is_dir() and (path.name.startswith('DerivedData-') or path.name.endswith('.xcresult')):
    excluded.append({'path':str(rel),'reason':'Owned build product/result bundle excluded; result ZIP+per-file verification can be retained separately later.','deferred':False});continue
   if path.is_dir():walk(path)
   elif path.is_file():files.append({'relativePath':str(rel),'bytes':path.stat().st_size,'sha256':sha(path)})
 walk(ROOT)
 plan={'schemaVersion':1,'owner':OWNER,'sourceRoot':str(ROOT),'destinationRoot':str(DEST),'finalSnapshot':args.final,'files':files,'exclusions':excluded,'rawStatusesPreserved':True,'sourceTimingQualification':'Retain layer-receipts-build/source-timing-qualification.json exactly; its failed-source timing scope must not be relabeled as the later final source build.','reviewScope':'Board-only candidate failed; later hand-policy/readiness outcomes require their own complete raw reviews. Readiness82tests passing is not rendered-frame or full-workflow proof. Preserve all earlier red/green/revised statuses. No inferred pass from archive completion.'}
 print(json.dumps(plan,indent=2))
