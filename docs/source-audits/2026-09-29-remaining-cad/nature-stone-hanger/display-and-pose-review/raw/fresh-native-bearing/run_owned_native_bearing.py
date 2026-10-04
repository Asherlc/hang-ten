"""Bound and clean the one explicitly requested read-only native job."""
import datetime
import hashlib
import json
import os
from pathlib import Path
import shutil
import signal
import subprocess
import sys
import time

HERE = Path(__file__).resolve().parent
ROOT = Path.cwd().resolve()
OWNER = Path(os.environ.get("PASEO_WORKTREE_PATH", str(ROOT))).name
NAME = OWNER + "-stone-vertical-native-bearing"
TMP = HERE / (NAME + "-tmp")
RECEIPT = HERE / (NAME + "-ownership.json")
LOG = HERE / (NAME + ".log")
assert OWNER == "placid-badger" and not TMP.exists() and not RECEIPT.exists()
TMP.mkdir()
command = [sys.executable, "-B", "Tools/HangboardCAD/run_freecad.py", str(HERE / "check_new_native_bearing.py")]
record = {"workspaceOwner": OWNER, "name": NAME, "command": command,
          "timeoutSeconds": 90, "temporaryRoot": str(TMP.relative_to(ROOT)),
          "startedUTC": datetime.datetime.now(datetime.timezone.utc).isoformat(),
          "resourceScope": "Exact owned process group and exclusive temporary root only."}
RECEIPT.write_text(json.dumps(record, indent=2) + "\n")
process = None
started = time.monotonic()


def interrupted(signum, frame):
    raise KeyboardInterrupt("Owned native job interrupted")


for sig in (signal.SIGINT, signal.SIGTERM):
    signal.signal(sig, interrupted)
try:
    environment = dict(os.environ, TMPDIR=str(TMP), PYTHONDONTWRITEBYTECODE="1")
    with LOG.open("w") as output:
        process = subprocess.Popen(command, cwd=ROOT, env=environment, stdout=output,
                                   stderr=subprocess.STDOUT, start_new_session=True)
        record["ownedProcessGroup"] = process.pid
        RECEIPT.write_text(json.dumps(record, indent=2) + "\n")
        process.wait(timeout=90)
        record["exitCode"] = process.returncode
except BaseException as error:
    record["error"] = type(error).__name__ + ": " + str(error)
finally:
    if process is not None:
        try:
            os.killpg(process.pid, signal.SIGTERM)
        except ProcessLookupError:
            pass
        try:
            process.wait(timeout=5)
        except subprocess.TimeoutExpired:
            try:
                os.killpg(process.pid, signal.SIGKILL)
            except ProcessLookupError:
                pass
            process.wait(timeout=5)
        record["exitCode"] = process.returncode
        group_absent = False
        for _ in range(50):
            try:
                os.killpg(process.pid, 0)
            except ProcessLookupError:
                group_absent = True
                break
            time.sleep(0.1)
        record["ownedProcessGroupAbsent"] = group_absent
    else:
        record["ownedProcessGroupAbsent"] = True
    shutil.rmtree(TMP)
    record["temporaryRootAbsent"] = not TMP.exists()
    record["elapsedSeconds"] = time.monotonic() - started
    record["logSHA256"] = hashlib.sha256(LOG.read_bytes()).hexdigest() if LOG.exists() else None
    record["status"] = "pass" if record.get("exitCode") == 0 and record["ownedProcessGroupAbsent"] and record["temporaryRootAbsent"] else "fail"
    RECEIPT.write_text(json.dumps(record, indent=2) + "\n")
print(json.dumps(record))
sys.exit(0 if record["status"] == "pass" else 1)
