"""Read eight deliberately selected native faces; never edit or save a shape."""
import hashlib
import json
import math
from pathlib import Path

import FreeCAD as App
import Part

HERE = Path(__file__).resolve().parent
ROOT = Path.cwd().resolve()
BASE = ROOT / ".context/placid-badger/nature-stone-review9"
SOURCE = BASE / "vertical-groove-correction/native-author/nature-stone-hanger.FCStd"
EXPECTED_SOURCE = "ee189092c1727c096894b1223ce78fd5214f858de2908507cc5ee0e6fb1297e6"


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def components(vector):
    return [float(vector.x), float(vector.y), float(vector.z)]


def cross(a, b):
    return [a[1] * b[2] - a[2] * b[1], a[2] * b[0] - a[0] * b[2], a[0] * b[1] - a[1] * b[0]]


def rotate(q, vector):
    turn = [2 * x for x in cross(q[:3], vector)]
    second = cross(q[:3], turn)
    return [v + q[3] * t + s for v, t, s in zip(vector, turn, second)]


def main():
    assert ROOT.name == "placid-badger" and sha(SOURCE) == EXPECTED_SOURCE
    metadata_path = HERE / "pose-input-before-sidecar.json"
    assignment_path = HERE / "deliberate-bearing-assignments.json"
    metadata_raw, assignments_raw = metadata_path.read_bytes(), assignment_path.read_bytes()
    metadata, assignments = json.loads(metadata_raw), json.loads(assignments_raw)
    poses = metadata["suspension"]["canonicalPoses"]
    indices = {e["contactID"]: e["bearingFaceIndex"] for e in assignments["poses"]}
    assert len(indices) == len(poses) == 8 and set(indices) == set(poses)
    assert all(index == (5 if contact.endswith("granite") else 8) for contact, index in indices.items())
    report = {}
    doc = App.openDocument(str(SOURCE))
    try:
        doc.recompute()
        bodies = [o for o in doc.Objects if getattr(o, "NodeRole", "") == "body"]
        contacts = {o.ContactID: o for o in doc.Objects if getattr(o, "NodeRole", "") == "contact"}
        assert len(bodies) == 1 and bodies[0].Name == "CordSeat_Right"
        body = bodies[0].Shape
        assert body.isValid() and len(body.Solids) == 1 and set(contacts) == set(poses)
        for contact, pose in poses.items():
            shape = contacts[contact].Shape
            index = indices[contact]
            assert shape.isValid() and len(shape.Faces) >= index
            face = shape.Faces[index - 1]
            u0, u1, v0, v1 = face.ParameterRange
            q = pose["rotation"]
            assert len(q) == 4 and abs(sum(x * x for x in q) - 1) < 1e-12
            samples = []
            for uf in (0.25, 0.5, 0.75):
                u, v = u0 + (u1 - u0) * uf, (v0 + v1) / 2
                point = face.valueAt(u, v)
                assert face.distToShape(Part.Vertex(point))[0] < 1e-6
                normal = face.normalAt(u, v)
                normal.normalize()
                assert all(math.isfinite(x) for x in components(normal))
                probes, direction = [], None
                for epsilon in (0.005, 0.02):
                    plus = body.isInside(point + normal * epsilon, 1e-7, False)
                    minus = body.isInside(point - normal * epsilon, 1e-7, False)
                    assert plus != minus, (contact, uf, epsilon, plus, minus)
                    sign = -1 if plus else 1
                    if direction is not None:
                        assert direction == sign
                    direction = sign
                    probes.append({"epsilonMM": epsilon, "rawNormalPlusInside": plus,
                                   "rawNormalMinusInside": minus})
                outward = normal * direction
                native = components(outward)
                runtime = [native[0], native[2], -native[1]]
                world = rotate(q, runtime)
                assert world[1] > 0.98, (contact, world)
                samples.append({"uFraction": uf, "parametersUV": [u, v],
                                "pointNativeMM": components(point),
                                "rawNativeNormal": components(normal),
                                "outwardDirectionSign": direction,
                                "nativeOutwardBearingNormal": native,
                                "runtimeBearingNormal": runtime, "worldBearingNormal": world,
                                "worldUpDot": world[1], "materialSideProbes": probes})
            report[contact] = {"contactObject": contacts[contact].Name,
                               "bearingFaceIndexOneBased": index,
                               "nativeFaceCount": len(shape.Faces), "rotation": q,
                               "samples": samples,
                               "minimumWorldUpDot": min(s["worldUpDot"] for s in samples)}
        assert sha(SOURCE) == EXPECTED_SOURCE
        assert metadata_path.read_bytes() == metadata_raw and assignment_path.read_bytes() == assignments_raw
        result = {"status": "pass-fresh-native-upward-bearing-sidecar-binding-pending",
                  "sourceSHA256": EXPECTED_SOURCE,
                  "fileSHA256": {str(SOURCE.relative_to(ROOT)): EXPECTED_SOURCE,
                                  str(metadata_path.relative_to(ROOT)): sha(metadata_path),
                                  str(assignment_path.relative_to(ROOT)): sha(assignment_path)},
                  "bodyFeature": bodies[0].Name, "contactCount": 8, "sampleCount": 24,
                  "poses": report,
                  "minimumWorldUpDot": min(r["minimumWorldUpDot"] for r in report.values()),
                  "nativeToRuntimeDirectionMap": "(native X, native Z, -native Y)",
                  "deliberateAssignmentsRetained": True, "oldNormalsReused": False,
                  "oldThirtyDegreeAdaptationReused": False,
                  "sourceBytesUnchanged": True, "documentSaved": False,
                  "blockingFindings": [], "humanAcceptance": "pending",
                  "limits": ["Fresh face/interior/exterior and local normal check on the frozen native source, with three native parameter samples per deliberately assigned bearing face.",
                             "Proposed axis half-turn/identity poses are checked. The report still requires an exact immutable final-sidecar binding before it supplies that gate.",
                             "This upward local-bearing check is not a continuum rope or global board equilibrium/safety claim. Actual camera/selection usability remains a fresh app and human-review gate."]}
        output = HERE / "new-native-bearing.json"
        assert not output.exists()
        output.write_text(json.dumps(result, indent=2) + "\n")
        print(json.dumps({"status": result["status"], "contacts": 8, "samples": 24,
                          "minimumWorldUpDot": result["minimumWorldUpDot"], "sourceBytesUnchanged": True}))
    finally:
        App.closeDocument(doc.Name)


main()
