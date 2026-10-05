from pathlib import Path
import subprocess,json,time,hashlib,sys
base=Path('.context/placid-badger-cad-second-half/pr-readiness-repair-2026-10-02/evo')
run=sys.argv[1]; out=base/(run+'-landscape')
r=subprocess.run(['rtk','proxy','xcrun','simctl','get_app_container','BDCA0D77-94C2-4A97-900B-443F75C64691','com.hangten.training','data'],capture_output=True,check=True,timeout=30)
(out/'data-container.txt').write_bytes(r.stdout)
p=Path(r.stdout.decode().strip())/('Documents/HighlightDiagnostic-placid-badger-cad-second-half-'+run)
records=[]
for src in p.glob('*.jsonl'):
 data=src.read_bytes(); dest=out/src.name; assert not dest.exists(); dest.write_bytes(data)
 rows=[json.loads(x) for x in data.splitlines()]
 records.append({'source':str(src),'copy':str(dest),'sha256':hashlib.sha256(data).hexdigest(),'copyEpoch':time.time(),'records':len(rows),'newlineComplete':data.endswith(b'\n'),'allComplete':all(x.get('complete') for x in rows),'contiguousSequences':[r['sequence'] for r in rows]==list(range(1,len(rows)+1)),'limitReached':any(x.get('eventLimitReached') for x in rows)})
assert records
(out/'trace-copy.json').write_text(json.dumps(records,indent=2)+'\n')
print(json.dumps(records,indent=2))
