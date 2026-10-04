"""Final-only exact Pro archive planner/copier. No runtime operations. Never overwrite mismatches."""
from pathlib import Path
import json,hashlib,argparse
OWNER='placid-badger-cad-second-half'
ROOT=Path('.context')/OWNER/'pro-app-review-2026-10-03'
DEST=Path('docs/source-audits/2026-09-29-remaining-cad/zlagboard-pro/app-review-2026-10-03/raw')
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
a=argparse.ArgumentParser();a.add_argument('--copy-plan',type=Path);args=a.parse_args()
def cleanup_gate():
 p=ROOT/'ios/cleanup-verification.json';j=json.loads(p.read_text());owned=json.loads((ROOT/'ios/ownership.json').read_text())
 assert j['owner']==OWNER and j['uuid']==owned['simulatorUUID'] and j['passed'] and j['simulatorDeleted'] and not j['errors'] and all(x['absent'] for x in j['ownedPaths'])
 for name in ['captures','captures-v2','captures-v3','captures-v4']:
  run=ROOT/name;assert (run/'completion.json').exists()
  c=json.loads((run/'cleanup.json').read_text());assert c['passed'] and c['allOwnedAppPIDsAbsent'] and c['uuid']==j['uuid']
 # Failed completed captures remain failed; no requirement that historical results pass.
 return {'path':'ios/cleanup-verification.json','sha256':sha(p)}
cleanup=cleanup_gate()
if args.copy_plan:
 plan=json.loads(args.copy_plan.read_text());assert plan['sourceRoot']==str(ROOT) and plan['destinationRoot']==str(DEST) and plan['cleanup']==cleanup
 for row in plan['files']:
  rel=Path(row['path']);assert not rel.is_absolute() and '..' not in rel.parts
  p=ROOT/rel;q=DEST/rel;assert not p.is_symlink() and sha(p)==row['sha256'] and p.stat().st_size==row['bytes']
  if q.exists():assert not q.is_symlink() and sha(q)==row['sha256'],'Never overwrite destination mismatch'
 for row in plan['files']:
  p=ROOT/row['path'];q=DEST/row['path'];q.parent.mkdir(parents=True,exist_ok=True)
  if not q.exists():
   data=p.read_bytes();assert hashlib.sha256(data).hexdigest()==row['sha256']
   with q.open('xb') as f:f.write(data)
  assert sha(q)==row['sha256']
 data=(json.dumps(plan,indent=2)+'\n').encode();key=hashlib.sha256(data).hexdigest();m=DEST.parent/('raw-manifest-'+key+'.json')
 if m.exists():assert m.read_bytes()==data
 else:
  with m.open('xb') as f:f.write(data)
 print(json.dumps({'files':len(plan['files']),'manifestSHA256':key,'exactCopyVerified':True}))
else:
 rows=[];excluded=[]
 def walk(p):
  for f in sorted(p.iterdir()):
   rel=str(f.relative_to(ROOT));assert not f.is_symlink(),'Unexpected symlink'
   if f.is_dir() and (f.name.startswith('DerivedData-') or f.name.endswith('.xcresult')):excluded.append({'path':rel,'reason':'Owned DerivedData/unpacked result excluded; preserve any needed raw result as exact verified ZIP before cleanup.'});continue
   if f.is_dir():walk(f)
   else:rows.append({'path':rel,'bytes':f.stat().st_size,'sha256':sha(f)})
 walk(ROOT)
 print(json.dumps({'sourceRoot':str(ROOT),'destinationRoot':str(DEST),'cleanup':cleanup,'files':rows,'exclusions':excluded,'rawPendingAndFailureStatusPreserved':True,'interpretation':'Archive equality does not establish app success or human acceptance.'},indent=2))
