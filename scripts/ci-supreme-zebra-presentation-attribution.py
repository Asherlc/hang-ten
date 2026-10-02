"""Temporary one-attempt watcher; never substitutes for XCTest acceptance."""
import argparse
import ctypes
import json
import math
import os
import re
import shlex
import signal
import subprocess
import time
from pathlib import Path


def eligible_marker(value, owner):
    try:
        return (isinstance(value, dict) and value["owner"] == owner
                and value["boardID"] == "zlagboard.evo"
                and isinstance(value["pid"], int) and value["pid"] > 0
                and value["cameraSettled"] is True
                and all(value[k] is True for k in ("rootActive", "cameraActive", "sameScene"))
                and all(math.isfinite(float(value[k])) for k in ("azimuth", "elevation"))
                and (float(value["azimuth"]) != 0 or float(value["elevation"]) != 0)
                and sum(layer.get("matchesMap") is True for layer in value["layers"]) == 1)
    except (KeyError, TypeError, ValueError):
        return False


def matches_app(command, installed_app):
    return Path(command.strip()).resolve() == (Path(installed_app) / "HangTen").resolve()


def executable_path(pid):
    library = ctypes.CDLL("/usr/lib/libproc.dylib")
    lookup = library.proc_pidpath
    lookup.argtypes = [ctypes.c_int, ctypes.c_void_p, ctypes.c_uint32]
    lookup.restype = ctypes.c_int
    buffer = ctypes.create_string_buffer(4096)
    if lookup(pid, buffer, len(buffer)) <= 0:
        raise RuntimeError("Kernel executable-path query failed")
    return os.fsdecode(buffer.value)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--device", required=True)
    parser.add_argument("--owner", required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--stop-pid", type=int)
    args = parser.parse_args()
    assert re.fullmatch(r"[A-Za-z0-9_-]+", args.owner)
    if args.stop_pid:
        receipt_path = args.output / "receipt.json"
        if receipt_path.exists():
            receipt = json.loads(receipt_path.read_text())
            assert receipt["owner"] == args.owner and receipt["controllerPID"] == args.stop_pid
        command = subprocess.run(["ps", "-p", str(args.stop_pid), "-o", "command="],
                                 capture_output=True, text=True, check=False)
        if command.returncode == 0:
            argv = shlex.split(command.stdout)
            assert len(argv) >= 7 and Path(argv[-7]).resolve() == Path(__file__).resolve()
            assert argv[-6:] == ["--device", args.device, "--owner", args.owner, "--output", str(args.output)]
            try:
                os.kill(args.stop_pid, signal.SIGTERM)
            except ProcessLookupError:
                pass
        return
    args.output.mkdir(parents=True, exist_ok=False)
    receipt = args.output / "receipt.json"
    state = {"owner": args.owner, "controllerPID": os.getpid(), "device": args.device,
             "appAttempts": 0, "activeChildGroups": [], "stoppingRule": "one attempt only",
             "startedAtUnix": time.time()}
    children = []
    marker = None
    stop_requested = False

    def record():
        temporary = receipt.with_suffix(".pending")
        temporary.write_text(json.dumps(state, indent=2) + "\n")
        temporary.replace(receipt)

    def stop(signum, frame):
        nonlocal stop_requested
        stop_requested = True

    def start(command, log):
        handle = log.open("wb")
        child = subprocess.Popen(command, stdout=handle, stderr=subprocess.STDOUT, start_new_session=True)
        children.append((child, handle))
        state["activeChildGroups"].append(child.pid)
        record()
        return child

    def finish(child, timeout):
        try:
            return child.wait(timeout=timeout)
        finally:
            if child.poll() is None:
                os.killpg(child.pid, signal.SIGINT)
                try:
                    child.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    os.killpg(child.pid, signal.SIGKILL)
                    child.wait(timeout=5)
            try:
                os.killpg(child.pid, 0)
            except ProcessLookupError:
                state["activeChildGroups"].remove(child.pid)
            else:
                raise RuntimeError("Owned child group remains after exit; retain ownership receipt")
            record()

    signal.signal(signal.SIGTERM, stop)
    signal.signal(signal.SIGINT, stop)
    record()
    source = args.output / f"{args.owner}-debugger-fixture.c"
    binary = args.output / f"{args.owner}-debugger-fixture"
    try:
        source.write_text('''#import <QuartzCore/QuartzCore.h>
#include <stdio.h>
#include <unistd.h>
@interface Probe : NSObject
@property(nonatomic, strong) CAMetalLayer *layer;
@end
@implementation Probe
@end
int main(void) { @autoreleasepool {
    Probe *probe = [Probe new]; probe.layer = [CAMetalLayer layer];
    printf("%p %p\\n", (__bridge void *)probe, (__bridge void *)probe.layer);
    fflush(stdout); sleep(60);
} return 0; }
''')
        compiler = start(["xcrun", "clang", "-x", "objective-c", "-fobjc-arc", "-g",
                          "-framework", "Foundation", "-framework", "QuartzCore",
                          str(source), "-o", str(binary)], args.output / "fixture-build.log")
        assert finish(compiler, 30) == 0
        target = start([str(binary)], args.output / "fixture-target.log")
        for _ in range(100):
            pointers = (args.output / "fixture-target.log").read_text().split()
            if len(pointers) == 2:
                break
            time.sleep(0.05)
        assert len(pointers) == 2 and all(re.fullmatch(r"0x[0-9a-fA-F]+", p) for p in pointers)
        preflight = start(["xcrun", "lldb", "--batch", "-o", f"process attach --pid {target.pid}",
                           "-o", "expression -l objc -- @import QuartzCore", "-o",
                           f"expression -l objc -- (void *)[(id<CAMetalDrawable>){pointers[0]} layer]",
                           "-o", "process detach"], args.output / "fixture-attach.log")
        assert finish(preflight, 25) == 0, "Debugger attachment preflight failed"
        values = re.findall(r"\$\d+ = (0x[0-9a-fA-F]+)", (args.output / "fixture-attach.log").read_text())
        assert values and int(values[-1], 16) == int(pointers[1], 16), "Read-only layer getter preflight failed"
        os.killpg(target.pid, signal.SIGTERM)
        finish(target, 5)
        source.unlink()
        binary.unlink()
        state["attachmentPreflightPassed"] = True
        state["layerGetterPreflightPassed"] = True
        record()

        deadline = time.monotonic() + 3300
        data_container = None
        while not stop_requested and time.monotonic() < deadline:
            if data_container is None:
                query = subprocess.run(["xcrun", "simctl", "get_app_container", args.device,
                                        "com.hangten.training", "data"], capture_output=True, text=True, timeout=5)
                if query.returncode == 0:
                    data_container = Path(query.stdout.strip())
                    marker = data_container / "Documents" / f"{args.owner}-presentation-attribution.json"
            if marker and marker.exists():
                try:
                    value = json.loads(marker.read_text())
                except (OSError, ValueError):
                    value = None
                if (eligible_marker(value, args.owner)
                        and marker.stat().st_mtime >= state["startedAtUnix"]
                        and time.time() - marker.stat().st_mtime > 1):
                    app_query = subprocess.run(["xcrun", "simctl", "get_app_container", args.device,
                                                "com.hangten.training", "app"], capture_output=True, text=True, timeout=5)
                    command = executable_path(value["pid"])
                    assert app_query.returncode == 0 and matches_app(command, app_query.stdout.strip()), "App PID provenance failed"
                    state["appAttempts"] = 1
                    state["nativeMarker"] = value
                    record()
                    module = Path(__file__).with_name("ci_supreme_zebra_lldb_attribution.py").resolve()
                    trace_output = args.output / "drawable-transaction-trace.json"
                    expected_layer = next(layer["pointer"] for layer in value["layers"] if layer.get("matchesMap"))
                    debugger = start(["xcrun", "lldb", "--batch", "-o",
                                      "command script import " + shlex.quote(str(module)), "-o",
                                      f"script ci_supreme_zebra_lldb_attribution.trace(lldb.debugger, {value['pid']}, {str(trace_output)!r}, {expected_layer!r}, {str(Path(command).resolve())!r}, 8)"],
                                     args.output / "debugger.log")
                    state["debuggerExit"] = finish(debugger, 25)
                    if trace_output.exists():
                        trace = json.loads(trace_output.read_text())
                        state["matchedMapDrawableEvents"] = sum(
                            event.get("kind") == "drawable-present"
                            and int(event.get("layer", "0"), 16) == int(expected_layer, 16)
                            for event in trace["events"])
                        state["traceCaptureCompleted"] = trace.get("captureCompleted", False)
                        state["detached"] = trace.get("detached", False)
                    break
            time.sleep(0.25)
        state["tracePhaseFinished"] = True
    except BaseException as error:
        state["error"] = type(error).__name__ + ": " + str(error)
    finally:
        for child, handle in reversed(children):
            if child.pid in state["activeChildGroups"]:
                try:
                    os.killpg(child.pid, signal.SIGINT)
                    try:
                        child.wait(timeout=5)
                    except subprocess.TimeoutExpired:
                        os.killpg(child.pid, signal.SIGKILL)
                        child.wait(timeout=5)
                    # A debugger helper may briefly outlive its front end.
                    for _ in range(20):
                        try:
                            os.killpg(child.pid, 0)
                        except ProcessLookupError:
                            break
                        time.sleep(0.05)
                    else:
                        os.killpg(child.pid, signal.SIGKILL)
                except ProcessLookupError:
                    pass
                try:
                    os.killpg(child.pid, 0)
                except ProcessLookupError:
                    state["activeChildGroups"].remove(child.pid)
                else:
                    state["cleanupError"] = "Owned child group remains: " + str(child.pid)
            handle.close()
        source.unlink(missing_ok=True)
        binary.unlink(missing_ok=True)
        state["fixtureFilesDeletedVerified"] = not source.exists() and not binary.exists()
        # Keep the controller PID owned until the XCTest shell's EXIT trap stops it.
        record()
        while not stop_requested:
            time.sleep(0.25)
        if marker and marker.exists():
            try:
                value = json.loads(marker.read_text())
                if value.get("owner") == args.owner and marker.stat().st_mtime >= state["startedAtUnix"]:
                    marker.unlink()
                    state["markerDeletedVerified"] = not marker.exists()
            except (OSError, ValueError) as error:
                state["markerCleanupError"] = str(error)
        state["controllerStopped"] = True
        state["allOwnedChildrenExited"] = all(child.poll() is not None for child, _ in children)
        record()
        if state.get("cleanupError") or state.get("markerCleanupError") or not state["allOwnedChildrenExited"]:
            raise SystemExit(1)


if __name__ == "__main__":
    main()
