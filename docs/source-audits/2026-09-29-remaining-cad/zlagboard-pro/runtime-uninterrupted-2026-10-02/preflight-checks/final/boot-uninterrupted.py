from pathlib import Path
import json, os, signal, subprocess, sys, time

uid, destination, deadline_text = sys.argv[1:]
out = Path(destination)
start = time.monotonic()
deadline = float(deadline_text)
start = deadline - 900
records = []
children = []
interrupted_signal = None

def terminate(proc):
    if proc.poll() is None:
        os.killpg(proc.pid, signal.SIGTERM)
        try:
            proc.wait(timeout=10)
        except subprocess.TimeoutExpired:
            os.killpg(proc.pid, signal.SIGKILL)
            proc.wait(timeout=5)

def interrupted(signum, _frame):
    global interrupted_signal
    interrupted_signal = signum
    for proc in children:
        terminate(proc)
    raise SystemExit(128 + signum)

signal.signal(signal.SIGINT, interrupted)
signal.signal(signal.SIGTERM, interrupted)

def command(label, args, budget=12):
    remaining = deadline - time.monotonic()
    if remaining <= 0:
        return None, b""
    cmd = ["rtk", "proxy", *map(str, args)]
    began = time.monotonic()
    stdout_path=out/(label+'.stdout');stderr_path=out/(label+'.stderr')
    stdout_file=stdout_path.open('xb');stderr_file=stderr_path.open('xb')
    proc = subprocess.Popen(cmd, stdout=stdout_file, stderr=stderr_file, start_new_session=True)
    children.append(proc)
    timed_out = False
    try:
        try:
            proc.wait(timeout=min(budget, remaining))
        except subprocess.TimeoutExpired:
            timed_out = True
            terminate(proc)
    finally:
        stdout_file.close();stderr_file.close()
        records.append({"label": label, "command": cmd, "exitStatus": proc.poll(),
                        "timedOut": timed_out, "interruptedBySignal": interrupted_signal,
                        "elapsedSeconds": time.monotonic() - began})
        (out / "readiness-commands.json").write_text(json.dumps(records, indent=2) + "\n")
    return proc.returncode, stdout_path.read_bytes()

def flatten(nodes):
    result = []
    for node in nodes:
        result.append(node)
        result.extend(flatten(node.get("children", [])))
    return result

boot_command = ["rtk", "proxy", "xcrun", "simctl", "bootstatus", uid, "-b"]
boot_log = (out / "boot-uninterrupted.log").open("wb")
boot = subprocess.Popen(boot_command, stdout=boot_log, stderr=subprocess.STDOUT, start_new_session=True)
children.append(boot)
ready = False
probe = 0
next_probe = start + 30
try:
    while time.monotonic() < deadline:
        if time.monotonic() < next_probe:
            time.sleep(min(1, max(0, deadline - time.monotonic())))
            continue
        probe += 1
        label = f"readiness-{probe:02d}"
        code, raw = command(label + "-ax", ["/opt/homebrew/bin/axe", "describe-ui", "--udid", uid])
        home_ids = set()
        if code == 0:
            try:
                rows = flatten(json.loads(raw))
                home_ids = {r.get("AXUniqueId") for r in rows if r.get("AXUniqueId")}
            except (ValueError, TypeError):
                pass
        candidate = {"simulator": uid, "elapsedSeconds": time.monotonic() - start,
                     "bootstatusExit": boot.poll(), "probe": probe,
                     "homeAXDetected": {"Home screen icons", "Settings", "Safari"}.issubset(home_ids)}
        (out / "readiness-progress.json").write_text(json.dumps(candidate, indent=2) + "\n")
        print(json.dumps(candidate), flush=True)
        if candidate["homeAXDetected"]:
            code, _ = command(label + "-screen", ["xcrun", "simctl", "io", uid, "screenshot", out / "home-candidate.png"])
            if code == 0 and (out / "home-candidate.png").exists() and time.monotonic() < deadline:
                candidate.update(responsiveAXConfirmed=True, actualHomeConfirmed=False,
                                 screenshot="home-candidate.png", accessibility=label + "-ax.stdout",
                                 needsVisualApprovalBeforeBuild=True)
                (out / "home-candidate.json").write_text(json.dumps(candidate, indent=2) + "\n")
                ready = True
                break
        next_probe = time.monotonic() + 30
finally:
    before = boot.poll()
    terminate(boot)
    boot_log.close()
    (out / "boot-monitor-summary.json").write_text(json.dumps({
        "simulator": uid, "maximumBootSeconds": 900, "elapsedSeconds": time.monotonic() - start,
        "uninterruptedDeviceBoot": True, "rebootsPerformed": 0, "readyForVisualApproval": ready,
        "bootstatusCommand": boot_command, "bootstatusExitBeforeMonitorStop": before,
        "bootstatusExitAfterMonitorStop": boot.returncode,
        "note": "Only the monitoring subprocess is stopped after success/deadline; the device is never rebooted. Build requires separate whole-screen visual approval."
    }, indent=2) + "\n")
if not ready:
    raise SystemExit(2)
