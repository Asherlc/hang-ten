"""Prospective adapter for corrected prototype v2; requires explicit runtime release."""
from pathlib import Path
import hashlib, json, math, re
READY = True
EXPECTED_EVENT_SCHEMA_SHA256 = "ee895ad76f0a4ed48b6ade3c0e4ad83b018e9418b1a0dd849606a7df480f3b8e"  # Revised v2 only; no launch authorization.
sha = lambda p: hashlib.sha256(Path(p).read_bytes()).hexdigest()

def validate_release(release):
    assert EXPECTED_EVENT_SCHEMA_SHA256 is not None
    assert release["eventSchemaSHA256"] == EXPECTED_EVENT_SCHEMA_SHA256
    assert sha(release["eventSchemaPath"]) == EXPECTED_EVENT_SCHEMA_SHA256
    assert len(release["binarySHA256"]) == 64

def extra_flags(role):
    flags={"HANGTEN_REVIEW_HIGHLIGHT_DIAGNOSTIC":"1", "HANGTEN_REVIEW_HAND_LIFETIME_CENSUS":"1"}
    if role=="image": flags["HANGTEN_REVIEW_HAND_IMAGE"]="1"
    return flags

def validate_flags(flags, role):
    expected={"HANGTEN_REVIEW_GRIP_MODEL":"1", "HANGTEN_REVIEW_GRIP_POSE":"halfCrimp",
        "HANGTEN_REVIEW_GRIP_FINGERS":"index,middle,ring,pinky",
        "HANGTEN_REVIEW_DIAGNOSTIC_RUN":flags["HANGTEN_REVIEW_DIAGNOSTIC_RUN"], **extra_flags(role)}
    assert flags==expected  # No audio/workout/suppression/projection/dark flags.

def image_rows(rows): return [r for r in rows if r.get("event")=="hand-image"]
def key(r): return r["sessionID"],r["revision"]
def arviews(census):
    return [p for s in census["windowScenes"] for w in s["windows"]
            for p in w["rendererPlacements"] if p["class"]=="RealityKit.ARView"]

def image_protocol(rows):
    events=image_rows(rows); pending=None; latest={}; stages={}; publications=[]; max_flight=0
    for r in events:
        k=key(r); event=r["imageEvent"]
        assert isinstance(k[1],int) and k[1]>0 and re.fullmatch(r"[A-Fa-f0-9-]{36}",k[0])
        if event=="requested":
            assert k[1]>latest.get(k[0],0); latest[k[0]]=k[1]
        elif event=="submitted":
            assert pending is None and latest[k[0]]>=k[1]
            assert r["kind"]=="pair" and r["orthographic"] is True and r["perspective"] is False
            assert r["textureFormat"]=="bgra8Unorm_srgb" and r["inputColorSpace"]=="sRGB"
            assert r["displayScale"]>0 and all(math.isfinite(v) and v>0 for v in r["viewport"])
            assert r["textureWidth"]==math.ceil(r["viewport"][0]*r["displayScale"])
            assert r["textureHeight"]==math.ceil(r["viewport"][1]*r["displayScale"])
            pending=k; stages[k]={"submitted":r}; max_flight=max(max_flight,1)
        elif event=="gpu-completion-callback":
            assert pending==k and "gpu-completion-callback" not in stages[k]
            assert r["metalCommandBufferStatusAvailable"] is False
            assert stages[k]["submitted"]["uptime"]<=r["callbackUptime"]<=r["uptime"]
            stages[k][event]=r
        elif event=="conversion-complete":
            assert pending==k and "gpu-completion-callback" in stages[k]
            assert r["eagerMaterialization"] is True and r["orientation"]=="up"
            assert r["cgWidth"]==stages[k]["submitted"]["textureWidth"]
            assert r["cgHeight"]==stages[k]["submitted"]["textureHeight"]
            assert r["cgBitsPerComponent"]==8 and r["cgAlphaInfo"] in (1,2,3,4)
            assert isinstance(r["cgColorSpace"],str) and r["cgColorSpace"]!="nil"
            stages[k][event]=r
        elif event=="published":
            assert pending==k and "conversion-complete" in stages[k]
            assert r["currentRevision"]==k[1]==latest[k[0]]
            assert not arviews(r["applicationCensus"])
            assert r["pngByteCount"]>0 and re.fullmatch(r"[a-f0-9]{64}",r["pngSHA256"])
            stages[k][event]=r; publications.append(r); pending=None
        elif event=="stale-completion-discarded":
            assert pending==k and "gpu-completion-callback" in stages[k]; pending=None
        elif event=="failed": raise AssertionError("Prototype failed: "+r["error"])
        elif event=="disappear": latest[k[0]]=k[1]
        else: raise AssertionError("Unknown prototype event "+event)
    makes=[r for r in rows if r.get("event")=="hand-lifecycle" and r.get("lifecycleEvent")=="make-entry"]
    assert not makes, "Image route constructed live hand host"
    current=[p for p in publications if p["revision"]==latest[p["sessionID"]]]
    return dict(events=events,pending=pending,current=current,maximumInFlight=max_flight)

def readiness(rows, role):
    if role=="image":
        state=image_protocol(rows)
        if not state["current"] or state["pending"] is not None:return None
        p=state["current"][-1]
        return dict(publication=p,maximumInFlight=state["maximumInFlight"])
    assert not image_rows(rows)
    for fit in reversed(rows):
        if fit.get("event")!="hand-camera" or fit.get("cameraEvent")!="reset-fitted" or fit.get("handKind")!="pair":continue
        token=fit["handLifetimeToken"]
        make=[x for x in rows if x.get("event")=="hand-lifecycle" and x.get("lifecycleEvent")=="make-entry" and x.get("handLifetimeToken")==token and x["sequence"]<fit["sequence"]]
        ctor=[x for x in rows if x.get("event")=="hand-lifecycle" and x.get("lifecycleEvent")=="constructor-entry" and x.get("handLifetimeToken")==token]
        if make and ctor and fit["orthographicPresent"] and not fit["perspectivePresent"] and fit["allDepthsFinite"] and fit["allDepthsInsideUnchangedClips"]:
            return dict(make=make[-1],fit=fit,constructor=ctor[0])
    return None

def snapshot(rows, role):
    return dict(recordCount=len(rows),lastSequence=rows[-1]["sequence"] if rows else None,
                readiness=readiness(rows,role),imageEventCount=len(image_rows(rows)))

def idle_evidence(before, after, role):
    a=[(r["sequence"],r["imageEvent"]) for r in image_rows(before)]
    b=[(r["sequence"],r["imageEvent"]) for r in image_rows(after)]
    assert a==b, "New image event during static idle interval"
    return dict(noNewImageEvents=True,before=snapshot(before,role),after=snapshot(after,role),scope="App event counts only; not GPU-idle proof")

def assert_completed_static_run(rows, role): assert readiness(rows,role) is not None

def published_artifact(rows):
    p=image_protocol(rows)["current"][-1]
    return dict(path=p["pngPath"],sha256=p["pngSHA256"],bytes=p["pngByteCount"],sessionID=p["sessionID"],revision=p["revision"])

def validate_retained_trace(output, copies, release):
    checks={}; rows=[]
    checks["exactlyOneTrace"]=len(copies)==1
    for c in copies:
        p=output/Path(c["source"]).name;raw=p.read_bytes()
        checks["traceHash:"+p.name]=sha(p)==c["sha256"]
        checks["completeLines:"+p.name]=bool(raw) and raw.endswith(b"\n")
        rows.extend(json.loads(l) for l in raw.splitlines())
    checks["contiguousComplete"]=bool(rows) and [r["sequence"] for r in rows]==list(range(1,len(rows)+1)) and all(r["complete"] is True for r in rows)
    checks["finiteTimes"]=all(math.isfinite(r["epoch"]) and math.isfinite(r["uptime"]) for r in rows)
    endpoint=json.loads((output/"observation-end.json").read_text())
    observed=[r for r in rows if r["epoch"]<=endpoint["epoch"]]
    checks["roleReadiness"]=readiness(observed,release["role"]) is not None
    before=json.loads((output/"before-screenshot-observation.json").read_text())["readiness"]
    after=readiness(observed,release["role"])
    if release["role"]=="image":
        checks["samePublicationAcrossScreenshot"]=key(before["publication"])==key(after["publication"])
    else:
        checks["sameLivePairAcrossScreenshot"]=before["fit"]["handLifetimeToken"]==after["fit"]["handLifetimeToken"]
    checks["noNewIdleImageEvents"]=json.loads((output/"idle-observation.json").read_text())["noNewImageEvents"] is True
    for record in release["sourceAndPackageFiles"]:checks["sourcePackage:"+record["path"]]=sha(record["path"])==record["sha256"]
    binary=json.loads((output/"installed-binary-gate.json").read_text())
    checks["installedBinaryBound"]=binary["sha256"]==binary["expectedSHA256"]==release["binarySHA256"]
    shot=json.loads((output/"screenshot.json").read_text());checks["wholeScreenshotHash"]=sha(output/"whole-app.png")==shot["sha256"]
    if release["role"]=="image":
        a=published_artifact(observed); copied=output/"generated-hand.png"
        checks["publishedPNGHash"]=sha(copied)==a["sha256"]
        checks["publishedPNGByteCount"]=copied.stat().st_size==a["bytes"]
        # Exact registered runfolder constraint is enforced by capture before copying.
    return dict(passed=all(checks.values()),checks=checks,records=len(rows),limits=["Callback receipt is not an actual Metal command-buffer status; source reports status unavailable.","No pixel analysis or visual equivalence assertion."])
