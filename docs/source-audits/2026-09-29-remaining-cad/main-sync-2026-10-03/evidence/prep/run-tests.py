from pathlib import Path
import json,sys,time,subprocess
n=Path('.context/placid-badger-cad-second-half/main-sync-2026-10-03');tag=sys.argv[1];cfg=json.loads((n/'xctest-command.json').read_text());args=cfg['args'];assert not (n/(tag+'.stdout')).exists()
(n/(tag+'-command.json')).write_text(json.dumps({'args':args,'startedUTC':time.time()},indent=2)+'\n')
with (n/(tag+'.stdout')).open('wb') as a,(n/(tag+'.stderr')).open('wb') as b:r=subprocess.run(['rtk','proxy',*args],stdout=a,stderr=b)
(n/(tag+'-exit.json')).write_text(json.dumps({'exitStatus':r.returncode,'completedUTC':time.time()},indent=2)+'\n');print(tag,'exit',r.returncode)
