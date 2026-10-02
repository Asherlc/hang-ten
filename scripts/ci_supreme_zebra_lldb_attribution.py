"""Temporary read-only LLDB attribution. Remove after the single retained run."""
import datetime
import json
import time
from pathlib import Path


def trace(debugger, pid, output_path, expected_layer, expected_executable, seconds=8):
    import lldb

    output = Path(output_path)
    result = {"pid": pid, "events": [], "debuggerPausesSeconds": 0,
              "readOnlyGetterExpressions": True, "detached": False}
    process = None
    target = None
    previous_async = debugger.GetAsync()
    presentation_threads = set()
    transaction_threads = set()
    layer_by_thread = {}
    try:
        debugger.SetAsync(True)
        target = debugger.CreateTarget(None)
        error = lldb.SBError()
        attached_at = time.monotonic()
        process = target.AttachToProcessWithID(lldb.SBListener("supreme-zebra-attribution"), pid, error)
        if error.Fail():
            raise RuntimeError("attach: " + error.GetCString())
        actual_executable = target.GetExecutable().fullpath
        result["actualExecutable"] = actual_executable
        if not actual_executable or Path(actual_executable).resolve() != Path(expected_executable).resolve():
            raise RuntimeError("Attached executable differs from the guarded installed app")
        present = target.BreakpointCreateByName("-[CAMetalDrawable present]")
        transaction_pattern = r"CA::Transaction::(push|commit|release_thread)"
        transactions = target.BreakpointCreateByRegex(transaction_pattern)
        transactions.SetEnabled(False)
        transaction_ids = set()
        result["breakpointLocations"] = {"present": present.GetNumLocations(),
                                        "transactions": transactions.GetNumLocations()}
        if not present.GetNumLocations() or not transactions.GetNumLocations():
            raise RuntimeError("Required presentation/transaction symbols did not resolve")
        result["debuggerPausesSeconds"] += time.monotonic() - attached_at
        deadline = time.monotonic() + seconds
        resume_error = process.Continue()
        if resume_error.Fail():
            raise RuntimeError("Initial resume failed: " + resume_error.GetCString())
        last_running_at = time.monotonic()
        handled_stop_id = None
        drawable_samples = 0
        while time.monotonic() < deadline:
            state = process.GetState()
            if state in (lldb.eStateExited, lldb.eStateCrashed, lldb.eStateDetached, lldb.eStateInvalid):
                result["earlyProcessState"] = state
                raise RuntimeError("Target exited, crashed or detached before capture completed")
            if state != lldb.eStateStopped:
                last_running_at = time.monotonic()
                time.sleep(0.005)
                continue
            stop_id = process.GetStopID()
            if stop_id == handled_stop_id:
                time.sleep(0.005)
                continue
            handled_stop_id = stop_id
            thread = next((t for t in process if t.GetStopReason() == lldb.eStopReasonBreakpoint), None)
            if thread is None:
                raise RuntimeError("Unexpected debugger stop; trace is inconclusive")
            frame = thread.GetFrameAtIndex(0)
            tid = thread.GetThreadID()
            breakpoint_id = thread.GetStopReasonDataAtIndex(0)
            stack = [thread.GetFrameAtIndex(i).GetFunctionName() or "<unknown>"
                     for i in range(min(thread.GetNumFrames(), 16))]
            event = {"utc": datetime.datetime.now(datetime.timezone.utc).isoformat(),
                     "thread": tid, "function": frame.GetFunctionName(), "stack": stack}
            if breakpoint_id == present.GetID():
                drawable_samples += 1
                pointer = frame.FindRegister("x0").GetValueAsUnsigned()
                options = lldb.SBExpressionOptions()
                options.SetLanguage(lldb.eLanguageTypeObjC)
                options.SetPrefix("@import QuartzCore;")
                options.SetIgnoreBreakpoints(True)
                options.SetUnwindOnError(True)
                options.SetTimeoutInMicroSeconds(300000)
                value = frame.EvaluateExpression(f"(void *)[(id<CAMetalDrawable>){pointer:#x} layer]", options)
                if value.GetError().Fail():
                    raise RuntimeError("Drawable layer getter failed: " + value.GetError().GetCString())
                layer = value.GetValueAsUnsigned()
                if not layer:
                    raise RuntimeError("Drawable layer getter returned no identity")
                event.update(kind="drawable-present", drawable=hex(pointer), layer=hex(layer))
                presentation_threads.add(tid)
                layer_by_thread[tid] = hex(layer)
                result["events"].append(event)
                if layer == int(expected_layer, 16) and tid not in transaction_threads:
                    filtered = target.BreakpointCreateByRegex(transaction_pattern)
                    filtered.SetThreadID(tid)
                    transaction_ids.add(filtered.GetID())
                    transaction_threads.add(tid)
                if drawable_samples >= 8:
                    present.SetEnabled(False)
            elif breakpoint_id in transaction_ids and tid in presentation_threads and len(result["events"]) < 64:
                event.update(kind="transaction", lastPresentedLayer=layer_by_thread.get(tid),
                             insideDrawablePresentation=any("CAMetalDrawable" in s and "present" in s for s in stack))
                result["events"].append(event)
            if len(result["events"]) >= 64:
                present.SetEnabled(False)
                for identifier in transaction_ids:
                    target.FindBreakpointByID(identifier).SetEnabled(False)
            result["debuggerPausesSeconds"] += time.monotonic() - last_running_at
            if result["debuggerPausesSeconds"] > 2:
                raise RuntimeError("Debugger pause budget exceeded; trace is inconclusive")
            resume_error = process.Continue()
            if resume_error.Fail():
                raise RuntimeError("Breakpoint resume failed: " + resume_error.GetCString())
            last_running_at = time.monotonic()
        result["captureCompleted"] = True
    except BaseException as error:
        result["error"] = type(error).__name__ + ": " + str(error)
    finally:
        if process and process.IsValid() and process.GetState() not in (
                lldb.eStateExited, lldb.eStateDetached, lldb.eStateInvalid):
            detach_started = time.monotonic()
            process.Stop()
            if target:
                target.DeleteAllBreakpoints()
            detach_error = process.Detach()
            result["detached"] = detach_error.Success()
            if detach_error.Fail():
                result["detachError"] = detach_error.GetCString()
            result["debuggerPausesSeconds"] += time.monotonic() - detach_started
        else:
            result["targetAlreadyExitedOrDetached"] = True
        if result["debuggerPausesSeconds"] > 2:
            result["error"] = "Debugger pause budget exceeded; trace is inconclusive"
            result["captureCompleted"] = False
        debugger.SetAsync(previous_async)
        output.write_text(json.dumps(result, indent=2) + "\n")
