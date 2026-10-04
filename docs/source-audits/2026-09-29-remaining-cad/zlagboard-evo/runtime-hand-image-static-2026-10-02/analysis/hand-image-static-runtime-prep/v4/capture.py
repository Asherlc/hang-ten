"""SCRATCH DRAFT. Requires real prototype_schema.py before any launch."""
from pathlib import Path
import atexit, hashlib, json, os, re, signal, subprocess, sys, time, traceback
import prototype_schema as schema

OWNER = "placid-badger-cad-second-half"
BUNDLE = "com.hangten.training"
sha = lambda p: hashlib.sha256(Path(p).read_bytes()).hexdigest()
release_path = Path(sys.argv[1])
release = json.loads(release_path.read_text())
assert schema.READY, "Actual prototype event schema is not supplied; no commands authorized"
assert release["runtimeAuthorized"] is True and release["role"] in ("live", "image")
assert release["owner"] == OWNER and OWNER in release["runID"]
assert re.fullmatch(r"[A-Za-z0-9_-]+", release["runID"])
assert release["helperSHA256"] == sha(__file__)
assert release["schemaSHA256"] == sha(schema.__file__)
assert re.fullmatch(r"[A-Fa-f0-9-]{36}", release["simulatorUUID"])
# Executor supplies exact already-owned Simulator/controller record. No create/delete here.
assert release["ownedController"]["simulatorUUID"] == release["simulatorUUID"]
assert release["ownedController"]["owner"] == OWNER
for record in release["sourceAndPackageFiles"]:
    assert sha(record["path"]) == record["sha256"]
schema.validate_release(release)
out = Path(release["outputDirectory"])
owned = Path(".context") / OWNER
assert out.resolve().is_relative_to(owned.resolve())
out.mkdir(exist_ok=False)
(out / "runtime-release.json").write_bytes(release_path.read_bytes())
commands = []; child = None; app_pid = None; launch_attempted = False
tracefolder = None; postlaunch_end = None; failure = None; postflight_errors = []

def write(name, value):
    (out / name).write_text(json.dumps(value, indent=2) + "\n")

def stop_child():
    global child
    if child is not None and child.poll() is None:
        child.terminate()
        try: child.wait(timeout=.5)
        except subprocess.TimeoutExpired:
            child.kill(); child.wait(timeout=1)
    child = None

def command(args, env=None, limit=20, cleanup=False, allow_failure=False):
    global child
    if postlaunch_end is not None and not cleanup:
        limit = min(limit, postlaunch_end-time.monotonic())
    if limit <= 0: raise TimeoutError("postlaunch40s limit")
    n = len(commands)
    record = dict(command=["rtk", "proxy", *map(str,args)], startEpoch=time.time(), limitSeconds=limit)
    commands.append(record); write("commands.json", commands)
    stdout = out/f"{n:03d}-stdout.txt"; stderr = out/f"{n:03d}-stderr.txt"
    with stdout.open("xb") as a, stderr.open("xb") as b:
        child = subprocess.Popen(record["command"], stdout=a, stderr=b, env=env)
        record["pid"] = child.pid; write("commands.json", commands)
        try:
            child.wait(timeout=limit); record["exitStatus"] = child.returncode
        except BaseException:
            record["interruptedOrTimedOut"] = True
            stop_child(); raise
        finally:
            stop_child(); record["endEpoch"] = time.time(); write("commands.json", commands)
    if record["exitStatus"] and not allow_failure:
        raise RuntimeError("Command failed; retained exact output")
    return stdout.read_text().strip()

def rows():
    result=[]
    if tracefolder and tracefolder.exists():
        for p in sorted(tracefolder.glob("events-*.jsonl")):
            result.extend(json.loads(l) for l in p.read_bytes().splitlines(keepends=True) if l.endswith(b"\n"))
    return result

def pause_to(deadline):
    while time.monotonic()<deadline:
        if postlaunch_end is not None and time.monotonic()>=postlaunch_end:
            raise TimeoutError("postlaunch40s limit")
        time.sleep(min(.03, max(0, deadline-time.monotonic())))

def interrupted(number, frame): raise InterruptedError("signal "+str(number))
signal.signal(signal.SIGINT, interrupted); signal.signal(signal.SIGTERM, interrupted)
atexit.register(stop_child)  # Before the first child/app command.
uid=release["simulatorUUID"]
try:
    app=Path(command(["xcrun","simctl","get_app_container",uid,BUNDLE,"app"]))
    actual_binary=sha(app/"HangTen.debug.dylib")
    write("installed-binary-gate.json",dict(path=str(app/"HangTen.debug.dylib"),
        sha256=actual_binary,expectedSHA256=release["binarySHA256"]))
    assert actual_binary==release["binarySHA256"]
    data=Path(command(["xcrun","simctl","get_app_container",uid,BUNDLE,"data"]))
    tracefolder=data/"Documents"/("HighlightDiagnostic-"+release["runID"])
    assert not tracefolder.exists(), "Fresh run path required"
    flags={"HANGTEN_REVIEW_GRIP_MODEL":"1", "HANGTEN_REVIEW_GRIP_POSE":"halfCrimp",
           "HANGTEN_REVIEW_GRIP_FINGERS":"index,middle,ring,pinky",
           "HANGTEN_REVIEW_DIAGNOSTIC_RUN":release["runID"]}
    flags.update(schema.extra_flags(release["role"]))
    schema.validate_flags(flags, release["role"])
    env={k:v for k,v in os.environ.items() if not k.startswith("SIMCTL_CHILD_HANGTEN_REVIEW_")}
    env.update({"SIMCTL_CHILD_"+k:v for k,v in flags.items()})
    write("launch-environment.json",flags)
    launch_start=time.monotonic(); postlaunch_end=launch_start+40
    launch_attempted=True
    launch=command(["xcrun","simctl","launch","--terminate-running-process",uid,BUNDLE],env=env)
    matched=re.search(r":\s*(\d+)\s*$",launch)
    if matched: app_pid=int(matched.group(1))
    write("app-registration.json",dict(simulatorUUID=uid,bundle=BUNDLE,pid=app_pid,owner=OWNER))
    assert app_pid is not None, "Launch PID missing; cleanup still targets exact owned Simulator/bundle"
    ready=None
    while time.monotonic()<launch_start+30:
        ready=schema.readiness(rows(),release["role"])
        if ready is not None: break
        pause_to(min(time.monotonic()+.03,launch_start+30))
    assert ready is not None, "30s readiness expired"
    write("readiness.json",ready)
    ready_time=time.monotonic(); pause_to(ready_time+2)
    before=rows(); write("before-screenshot-observation.json",schema.snapshot(before,release["role"]))
    # One whole-app screenshot; command timeout shares the same40s cap.
    shot_start=time.time()
    command(["xcrun","simctl","io",uid,"screenshot",out/"whole-app.png"])
    write("screenshot.json",dict(startEpoch=shot_start,endEpoch=time.time(),sha256=sha(out/"whole-app.png")))
    idle_start=time.monotonic(); idle_before=rows()
    pause_to(idle_start+3)
    final=rows(); write("idle-observation.json",schema.idle_evidence(idle_before,final,release["role"]))
    schema.assert_completed_static_run(final,release["role"])
    if release["role"]=="image":
        # Adapter must return actual published artifact metadata; no guessed schema/path.
        artifact=schema.published_artifact(final)
        path=Path(artifact["path"])
        assert path.resolve().is_relative_to(tracefolder.resolve()) and path.suffix.lower()==".png"
        assert sha(path)==artifact["sha256"]
        (out/"generated-hand.png").write_bytes(path.read_bytes())
        write("image-artifact-copy.json",dict(source=str(path),sha256=sha(out/"generated-hand.png")))
    write("observation-end.json",dict(completed=True,epoch=time.time(),elapsedPostlaunch=time.monotonic()-launch_start))
except BaseException:
    failure=traceback.format_exc(); (out/"failure.txt").write_text(failure)
finally:
    stop_child()
    cleanup={"scope":"Only launched app on exact preowned Simulator; controller retains Simulator/DD ownership"}
    if launch_attempted:
        try:
            command(["xcrun","simctl","terminate",uid,BUNDLE],limit=10,cleanup=True,allow_failure=True)
            if app_pid:
                ps=command(["ps","-p",app_pid,"-o","pid=,comm="],limit=3,cleanup=True,allow_failure=True)
                cleanup["pidQueryExitStatus"]=commands[-1]["exitStatus"]
                cleanup["recordedAppPIDAbsent"]=commands[-1]["exitStatus"]==1 and not ps.strip()
            else: cleanup["recordedAppPIDAbsent"]=False
        except BaseException as exc: cleanup["error"]=repr(exc)
    cleanup["directChildReaped"]=child is None
    cleanup["passed"]=(not launch_attempted or cleanup.get("recordedAppPIDAbsent") is True) and "error" not in cleanup and cleanup["directChildReaped"]
    write("app-cleanup.json",cleanup)
    if not cleanup["passed"]: postflight_errors.append("Exact app/child cleanup not verified")
    # Preserve exact complete or partial trace, including failures, after termination attempt.
    copies=[]
    if tracefolder and tracefolder.exists():
        for p in sorted(tracefolder.glob("events-*.jsonl")):
            (out/p.name).write_bytes(p.read_bytes()); copies.append(dict(source=str(p),sha256=sha(out/p.name)))
    write("trace-copy.json",copies)
    # Validate only the frozen copied bytes, never partial/live reads as final proof.
    # Adapter uses prototype's actual fields: complete newline JSONL, contiguous sequence,
    # required event evidence and byte hashes including the copied generated PNG.
    try:
        retained_check=schema.validate_retained_trace(out,copies,release)
        write("retained-trace-validation.json",retained_check)
        if retained_check["passed"] is not True:
            postflight_errors.append("Retained trace/hash validation failed")
    except BaseException:
        (out/"retained-trace-validation-error.txt").write_text(traceback.format_exc())
        postflight_errors.append("Retained trace/hash validation raised; raw bytes retained")
    write("completion.json",dict(observationFailed=failure is not None,
        postflightErrors=postflight_errors,passed=failure is None and not postflight_errors))
if failure or postflight_errors: raise SystemExit(1)
