"""Bind the completed fresh native-face proof to an immutable final sidecar."""
import argparse
import hashlib
import json
import math
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[6]
VERTICAL = ROOT / ".context/placid-badger/nature-stone-review9/vertical-groove-correction"
NATIVE_SHA = "b3f52e79fa12d5a090c92c0c07afb295e18012e139b0996006ddff185a898137"
CLEANUP_SHA = "26911d5ea5a87f5fc73dcdbef0d7764d6423085d36c1c72fffda27c80016441a"


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def cross(a, b):
    return [a[1] * b[2] - a[2] * b[1], a[2] * b[0] - a[0] * b[2], a[0] * b[1] - a[1] * b[0]]


def rotate(q, vector):
    turn = [2 * x for x in cross(q[:3], vector)]
    second = cross(q[:3], turn)
    return [v + q[3] * t + s for v, t, s in zip(vector, turn, second)]


parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument("--sidecar", type=Path, required=True)
parser.add_argument("--sidecar-sha", required=True)
args = parser.parse_args()
sidecar = args.sidecar.resolve()
assert sidecar.is_relative_to(ROOT) and sidecar.is_file() and not sidecar.is_symlink()
sidecar_raw = sidecar.read_bytes()
assert hashlib.sha256(sidecar_raw).hexdigest() == args.sidecar_sha
setup = json.loads(sidecar_raw)
native_path = HERE / "new-native-bearing.json"
cleanup_path = HERE / "placid-badger-stone-vertical-native-bearing-ownership.json"
assert sha(native_path) == NATIVE_SHA and sha(cleanup_path) == CLEANUP_SHA
native, cleanup = json.loads(native_path.read_text()), json.loads(cleanup_path.read_text())
assert native["status"] == "pass-fresh-native-upward-bearing-sidecar-binding-pending"
assert cleanup["status"] == "pass" and cleanup["ownedProcessGroupAbsent"] and cleanup["temporaryRootAbsent"]
assert not (ROOT / cleanup["temporaryRoot"]).exists()
assert native["sourceBytesUnchanged"] and not native["oldNormalsReused"] and not native["oldThirtyDegreeAdaptationReused"]
for path, digest in native["fileSHA256"].items():
    assert sha(ROOT / path) == digest
source = VERTICAL / "native-author/nature-stone-hanger.FCStd"
model, descriptor = VERTICAL / "assets/primary.usdz", VERTICAL / "assets/primary.model.json"
assert sha(source) == native["sourceSHA256"]
assert setup["modelSHA256"] == sha(model) == json.loads(descriptor.read_text())["modelSHA256"]
poses = setup["suspension"]["canonicalPoses"]
assert set(poses) == set(native["poses"]) and len(poses) == 8
results = {}
for contact, pose in poses.items():
    q = pose["rotation"]
    assert q == native["poses"][contact]["rotation"]
    assert all(math.isfinite(x) for x in q) and abs(sum(x * x for x in q) - 1) < 1e-12
    samples = []
    for sample in native["poses"][contact]["samples"]:
        n = sample["nativeOutwardBearingNormal"]
        world = rotate(q, [n[0], n[2], -n[1]])
        assert world[1] > 0.98
        assert max(abs(a - b) for a, b in zip(world, sample["worldBearingNormal"])) < 1e-12
        samples.append({"parametersUV": sample["parametersUV"], "worldBearingNormal": world,
                        "worldUpDot": world[1]})
    results[contact] = {"status": "pass", "rotation": q,
                        "bearingFaceIndexOneBased": native["poses"][contact]["bearingFaceIndexOneBased"],
                        "samples": samples, "minimumWorldUpDot": min(s["worldUpDot"] for s in samples)}
assert sidecar.read_bytes() == sidecar_raw
result = {"status": "pass-final-sidecar-bound-native-bearing",
          "sourceSHA256": native["sourceSHA256"], "modelSHA256": sha(model),
          "descriptorSHA256": sha(descriptor), "sidecarSHA256": args.sidecar_sha,
          "fileSHA256": {str(native_path.relative_to(ROOT)): NATIVE_SHA,
                          str(cleanup_path.relative_to(ROOT)): CLEANUP_SHA,
                          str(sidecar.relative_to(ROOT)): args.sidecar_sha},
          "poses": results, "contactCount": 8, "sampleCount": 24,
          "minimumWorldUpDot": min(p["minimumWorldUpDot"] for p in results.values()),
          "finalQuaternionsMatchFreshNativeCheck": True, "oldThirtyDegreeAdaptationReused": False,
          "legacyProposalUsedOnlyForDeliberateFaceIndices": True,
          "sourceBytesUnchanged": True, "ownedNativeResourcesVerifiedCleaned": True,
          "blockingFindings": [], "humanAcceptance": "pending",
          "limits": ["Native normals and body-side membership were freshly checked on the new source; final immutable quaternions are rechecked by arithmetic. Settled translations do not alter direction normals.",
                     "This proves sampled local upward bearing for the deliberately assigned faces. It does not prove continuum cable/global board equilibrium, real load safety or actual camera/picking usability.",
                     "Final cord, regeneration, app and human acceptance remain separate gates."],
          "newNativeJobOrSolveAtBinding": False, "canonicalMutation": False}
output = HERE / "final-sidecar-native-bearing.json"
assert not output.exists(), "Keep this hash-bound report immutable"
output.write_text(json.dumps(result, indent=2) + "\n")
print(json.dumps({"status": result["status"], "sha256": sha(output),
                  "contacts": 8, "minimumWorldUpDot": result["minimumWorldUpDot"]}))
