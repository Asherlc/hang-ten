from pathlib import Path
import fcntl
import json
import subprocess
import time
lane = Path(__file__).resolve().parent
lock = (lane/'app-captures/exclusive-ui-driver.lock').open('a')
fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
receipt = lane/'workout-multi.json'
assert not receipt.exists()
records = []
for number, orientation in [(10,'portrait'),(11,'landscape'),(12,'landscape'),(13,'landscape'),(14,'landscape'),(15,'landscape')]:
    command = ['rtk','proxy','python3',str(lane/'workout_capture.py'),str(number),orientation]
    record = {'command':command,'number':number,'orientation':orientation,'startedAt':time.time()}
    records.append(record)
    receipt.write_text(json.dumps({'owner':'placid-badger','records':records},indent=2)+'\n')
    result = subprocess.run(command,capture_output=True,text=True,timeout=250)
    record.update(exitCode=result.returncode,stdout=result.stdout,stderr=result.stderr,elapsedSeconds=time.time()-record['startedAt'])
    receipt.write_text(json.dumps({'owner':'placid-badger','records':records},indent=2)+'\n')
    print(json.dumps({'number':number,'orientation':orientation,'exitCode':result.returncode}),flush=True)
    if result.returncode:
        print(result.stderr[-2000:],flush=True)
        raise SystemExit(result.returncode)
print('All source-plan work/rest states captured; visual workflow judgment remains separate.',flush=True)
