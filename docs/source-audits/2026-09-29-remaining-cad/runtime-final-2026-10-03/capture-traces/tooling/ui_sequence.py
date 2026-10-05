from pathlib import Path
import fcntl
import json
import subprocess
import sys
import time
lane = Path(__file__).resolve().parent
lock = (lane/'app-captures/exclusive-ui-driver.lock').open('a')
fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
spec = lane/sys.argv[1]
receipt = spec.with_name(spec.stem+'-receipt.json')
assert not receipt.exists()
records = []
for args in json.loads(spec.read_text()):
    command = ['rtk','proxy','python3',str(lane/'app_review.py'),*map(str,args)]
    record = {'command': command, 'startedAt': time.time()}
    records.append(record)
    receipt.write_text(json.dumps({'owner':'placid-badger','commands':records},indent=2)+'\n')
    result = subprocess.run(command,capture_output=True,text=True,timeout=120)
    record.update(exitCode=result.returncode,stdout=result.stdout,stderr=result.stderr,elapsedSeconds=time.time()-record['startedAt'])
    receipt.write_text(json.dumps({'owner':'placid-badger','commands':records},indent=2)+'\n')
    print(result.stdout[-1800:],end='',flush=True)
    if result.returncode:
        print(result.stderr[-1800:],flush=True)
        raise SystemExit(result.returncode)
