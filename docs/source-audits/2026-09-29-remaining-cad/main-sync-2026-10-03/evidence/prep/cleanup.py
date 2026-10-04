from pathlib import Path
import sys,json,subprocess,shutil
out,name,uid=sys.argv[1:];out=Path(out);owner='placid-badger-cad-second-half';errors=[];commands=[]
assert out.resolve().is_relative_to((Path('.context')/owner/'main-sync-2026-10-03').resolve()) and owner in name

def call(args):
 try:
  p=subprocess.run(['rtk','proxy',*args],capture_output=True,timeout=30)
  n=len(commands);(out/f'cleanup-{n:02d}.stdout').write_bytes(p.stdout);(out/f'cleanup-{n:02d}.stderr').write_bytes(p.stderr)
  commands.append({'args':args,'exitStatus':p.returncode});return p
 except Exception as e:errors.append(repr(e));return None
p=call(['xcrun','simctl','list','devices','--json']);devices=[]
try:devices=[d for ds in json.loads(p.stdout)['devices'].values() for d in ds]
except Exception as e:errors.append(repr(e))
if not uid:
 match=[d for d in devices if d['name']==name]
 if len(match)>1:errors.append('Ambiguous exact creation name')
 elif match:
  uid=match[0]['udid']
  for n in ['paseo-pending-simulators','paseo-owned-simulators']:
   with (Path('.context')/n).open('a') as f:f.write(uid+'\n')
  (out/'recovered-create-uuid').write_text(uid+'\n')
match=[d for d in devices if d['udid']==uid]
if match:
 if len(match)==1 and match[0]['name']==name:
  call(['xcrun','simctl','shutdown',uid]);call(['xcrun','simctl','delete',uid])
 else:errors.append('Exact UUID ownership/name mismatch; no removal')
paths=[out/('DerivedData-'+owner),out/('build-'+owner+'.xcresult'),out/('tests-'+owner+'.xcresult')]
for p in paths:
 try:
  if p.is_symlink():p.unlink()
  elif p.is_dir():shutil.rmtree(p)
  elif p.exists():p.unlink()
 except Exception as e:errors.append(repr(e))
p=call(['xcrun','simctl','list','devices','--json']);absent=False
try:
 ds=[d for v in json.loads(p.stdout)['devices'].values() for d in v];absent=not any(d['udid']==uid or (not uid and d['name']==name) for d in ds)
except Exception as e:errors.append(repr(e))
record={'owner':owner,'uuid':uid,'simulatorDeleted':absent,'ownedPaths':[{'path':str(p),'absent':not p.exists()} for p in paths],'errors':errors,'commands':commands}
record['passed']=absent and all(x['absent'] for x in record['ownedPaths']) and not errors
if record['passed'] and uid:
 for filename in ['paseo-owned-simulators','paseo-pending-simulators']:
  manifest=Path('.context')/filename
  if manifest.exists():
   rows=manifest.read_text().splitlines()
   manifest.write_text(''.join(row+'\n' for row in rows if row.upper()!=uid.upper()))
 record['exactOwnershipRecordsConsumed']=True
(out/'cleanup-verification.json').write_text(json.dumps(record,indent=2)+'\n')
raise SystemExit(0 if record['passed'] else 1)
