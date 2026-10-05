#!/usr/bin/env python3
"""Bounded stdlib-only analysis of retained diagnostics, not a route solver."""
from pathlib import Path
import hashlib
import json
import math

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[4]
BASE = ROOT / ".context/placid-badger/nature-stone-review9"
PROBE = BASE / "notch-guide-implementation"
CONFIG = HERE.parent / "packet-config.json"


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def vector_sub(a, b):
    return [x-y for x, y in zip(a, b)]


def norm(value):
    return math.sqrt(sum(x*x for x in value))


def unit(value):
    size = norm(value)
    return [x/size for x in value]


names = ["pose-review/native-contact-orientation.json", "pose-review/per-contact-pose-plan.json",
         "pose-review/source-geometry-equivalence.json", "human-feedback.json",
         "notch-guide-implementation/terminal-intervals-native-v2.json",
         "notch-guide-implementation/native-guides.json",
         "notch-guide-implementation/anchor-plane-failed-path.json",
         "notch-guide-implementation/optimization-probe-inset.json",
         "notch-guide-implementation/optimization-probe-inset-pitch60.json",
         "notch-guide-implementation/optimization-probe-inset-pitch60-reaction-cone.json",
         "notch-guide-implementation/reaction_cone_probe.py",
         "notch-guide-implementation/optimize_inset_pitch60.py",
         "notch-guide-implementation/optimize_interior_bearing.py"]
inputs = {name: (BASE/name).read_bytes() for name in names}
hashes = {str((BASE/name).relative_to(ROOT)): hashlib.sha256(data).hexdigest()
          for name, data in inputs.items()}
compiler_policy = ROOT / "Tools/HangboardCAD/native_cord_routes.py"
hashes[str(compiler_policy.relative_to(ROOT))] = digest(compiler_policy)
config_before = digest(CONFIG)
config = json.loads(CONFIG.read_text())
assert config["finalReady"] is False
source = config["identity"]["sourceSHA256"]
assert source == "1b0113f264ee1d0b31d7b30b68f8b1e64839268ecd53b97a2ba8067e29a01108"
native_source = ROOT / "Hangboards/nature-stone-hanger/nature-stone-hanger.FCStd"
assert digest(native_source) == source
hashes[str(native_source.relative_to(ROOT))] = source


def raw(name):
    return json.loads(inputs["notch-guide-implementation/"+name])


terminals = raw("terminal-intervals-native-v2.json")
assert terminals["sourceSHA256"] == source and terminals["bodyValid"]
assert terminals["cachedBoundBoxIsNotMouthEvidence"]
for row in terminals["terminals"]:
    assert abs(abs(row["selectedTerminalNativeMM"][0])-49.75) < 1e-9
    assert abs(abs(row["nominalOuterMouthMM"][0])-52.5) < 1e-9
    assert abs(abs(row["nativeDisplayCutoffMM"][0])-47) < 1e-9
    assert abs(row["nativeTerminalClearanceMM"]-2) < 1e-9

guides = raw("native-guides.json")
normal_bounds = {}
for guide in guides["guides"]:
    normals = [entry["normal"] for face in guide["nativeCylinderFaces"]
               for entry in face["nativeNormals"]]
    normal_bounds[guide["feature"]] = {
        "nativeComponentBounds": [[min(n[i] for n in normals), max(n[i] for n in normals)]
                                  for i in range(3)],
        "actualExposedAxialBoundsMM": guide["actualExposedAxialBoundsMM"]}
    opening = guide["openingDirectionNative"]
    assert all(sum(n*o for n, o in zip(normal, opening)) >= -1e-10 for normal in normals)

candidate = raw("optimization-probe-inset-pitch60.json")
cone = raw("optimization-probe-inset-pitch60-reaction-cone.json")
assert candidate["sourceSHA256"] == cone["sourceSHA256"] == source
path = candidate["path"]  # Retained data only: do not generate or optimize any route.
checks = []
for row in cone["rows"]:
    if row["turnDegrees"] <= .5:
        continue
    i = row["index"]
    a = unit(vector_sub(path[i-1], path[i]))
    b = unit(vector_sub(path[i+1], path[i]))
    reaction = [-(x+y) for x, y in zip(a, b)]
    assert max(abs(x-y) for x, y in zip(reaction, row["reaction"])) < 1e-12
    fitted = [sum(entry["weight"]*entry["normal"][axis] for entry in row["activeContacts"])
              for axis in range(3)]
    relative = norm(vector_sub(fitted, reaction))/norm(reaction)
    assert abs(relative-row["nonnegativeResidualRelative"]) < 1e-8
    checks.append({"index": i, "turnDegrees": row["turnDegrees"],
                   "distanceMM": row["nearestDistanceMM"],
                   "reaction": reaction, "nonnegativeConeResidualRelative": relative,
                   "materialContactAtActualRadiusWithin10um": abs(row["nearestDistanceMM"]-1.5) <= .01,
                   "materialContactAtOldInflatedRadiusWithin10um": row["nearWallAtInflatedRadius"]})
open_side = next(row for row in checks if row["index"] == 51)
assert open_side["reaction"][0] > 0
open_side["leftOpeningNormalConeNecessaryCondition"] = "reactionX <= 0"
open_side["necessaryConditionPassed"] = False
open_side["minimumRelativeResidualFromHalfspace"] = open_side["reaction"][0]/norm(open_side["reaction"])

allowances = [{"policy": label, "effectiveRadiusMM": radius,
               "nominalGrooveCenterlineRadialAllowanceMM": 1.75-radius,
               "nominalBoreCenterlineRadialAllowanceMM": 2-radius}
              for label, radius in [("actual tube", 1.5), ("existing proposal policy", 1.52),
                                    ("old section-seed inflation", 1.7)]]
report = {
    "status": "read-only-analytical-review-complete-final-routing-still-pending",
    "reviewScriptSHA256": digest(Path(__file__)),
    "sourceSHA256": source, "inputSHA256": hashes,
    "method": "Read retained native reports/code; stdlib arithmetic on already generated path/force rows. No native query, route solve, centerline authoring or image measurement.",
    "assumptions": ["Massless, taut, frictionless display-cord segments with equal tension on both sides of an interior point.",
                    "Material contact can push along outward normals into free space, not pull through an open half-groove.",
                    "Nominal perpendicular-cylinder local section is an analytical bound; rounded broad-face exit still requires whole native-solid certification."],
    "terminalWitness": terminals,
    "nativeGuideNormalBounds": normal_bounds,
    "radiusPolicyAllowances": allowances,
    "forceConvention": {"outgoingTangents": "a=(previous-p)/length; b=(next-p)/length",
                        "ropeTensionOnPoint": "T(a+b)", "materialOnRopeReaction": "-T(a+b)",
                        "cone": "sum(lambda_j*n_material_outward_j), lambda_j>=0",
                        "existingScratchSignIsCorrect": True},
    "retainedCandidateChecks": checks,
    "retainedCandidateRadiusCertificate": candidate["certificate"],
    "localFeasibility": {
        "nominalCylinderIntersectionIsNotProvenImpossible": True,
        "reason": "Groove1.75mm and bore2mm both exceed tube1.5mm and proposal envelope1.52mm. In a local material-side corner, outward groove/bore wall normals can jointly balance a right-angle turn; one nearest normal is insufficient.",
        "broadFaceExitFinalTautPathProven": False,
        "uniformConcaveBarrelLimit": "A frictionless cord following nonzero circumferential curvature of an inner cylindrical wall would require a reaction opposite the cavity-facing wall normal. Only straight/zero-normal-curvature passage is supported there; convex rims/junctions can supply other normal cones.",
        "fullLengthTraversalLimit": "Do not interpret user notch guidance as a sourced fixed full axial traverse at arbitrary stations. Such equalities or a full cylindrical disk constraint in the open half can create virtual reactions. This review rejects the retained probes, not every possible3D path."},
    "findings": [
        "The terminal-v2 witness±49.75mm is a valid finite endpoint inside the existing side bore; cached bounding-box extrema are not mouth evidence.",
        "Pitch60 retained node51 requires+X reaction on the left open side; every available groove-wall outward normal has X<=0. Nonnegative support is impossible at that point.",
        "NNLS zero residual at nodes52/56 is not support: material distances1.7505/1.9995mm leave the actual1.5mm tube off the wall. Active-contact filtering/complementarity is mandatory.",
        "Retained pitch60 candidate also fails the unchanged whole-segment tube certificate at1.311624mm. Optimizer success and nearly zero sample constraints cannot waive that failure.",
        "The0.2mm section/seed clearance and0.02mm tightening proposal margin are not the physical radius gate. Aligning proposal policy preserves the1.5mm radius and10um final certificate; it does not rehabilitate older failed candidates.",
        "A positive cone of equally near active material walls is needed at groove/bore/rim junctions. Inactive walls and an authoring station's constraint gradient cannot act as a peg."],
    "smallestChange": [
        "Keep native geometry, real bore endpoint, contact facts and tube gates. Replace arbitrary full-length fixed guide stations with evidence-compatible groove traversal/contact windows using only real native surfaces.",
        "Treat required groove membership as topology, not a force-bearing virtual constraint. Reject any meaningful interior turn off all active material walls or outside their nonnegative cone.",
        "Allow only a deliberately selected, labeled display-pose pitch/departure side that points toward support and preserves the selected native bearing-up witness; choose the smallest passing change, then regenerate and certify all16 routes.",
        "If no such pose/topology passes, retain infeasibility rather than close the open groove, add a support, shrink the radius or relax gates. A new geometric adaptation would need source review and fresh native/export/app comparisons."],
    "limits": ["No final route, global equilibrium, friction coefficient, bending stiffness, real-use loading or factory dimensions are certified.",
               "Ongoing interior-bearing/margin-aligned solves are excluded. Existing scratch code may change after the recorded input hashes.",
               "Force-cone checks on an inflated clearance surface must identify that approximation; they do not by themselves prove contact of the actual-radius tube."],
    "resourceCreated": False, "sharedOrCanonicalMutation": False,
    "packetFinalReady": False, "packetConfigUnchanged": digest(CONFIG) == config_before}
assert report["packetConfigUnchanged"]
(HERE/"inspection.json").write_text(json.dumps(report, indent=2)+"\n")
text = """# Independent Stone Hanger guide feasibility review

The retained probes do not provide a supported final route. The reaction sign
is correct: for unit tangents directed away from a point, material-on-rope
reaction is `−T(a+b)`. It must lie in the nonnegative cone of **active** outward
material normals. Left pitch60 node51 asks for +X reaction while its open groove
can only supply X≤0; it is an unsupported turn. Nodes 52 and 56 have zero cone
residual but are 1.7505 and 1.9995 mm from material, so they cannot bear a 1.5 mm tube.
The retained pitch60 path separately fails continuous radius clearance at
1.311624 mm; optimizer success is insufficient.

The corrected endpoint ±49.75 mm is inside the existing 5.5 mm visible bore interval,
between the real ±52.5 mm side plane and ±47 mm cutoff. The nominal groove/bore
intersection has positive radial room: 0.25/0.50 mm for the actual tube,
0.23/0.48 mm with the existing 0.02 mm proposal margin, and 0.05/0.30 mm under the old
0.2 mm seed inflation. This does not prove the full topology impossible. A
material-side junction can support a cone of both wall normals. The rounded
broad-face departure remains unproven by the retained failures.

Full-length forced station traversal is stronger than “Enters side holes;
notches guide it”. A half-open groove cannot pull a rope inward at an open-side
bend. A taut frictionless cord also cannot follow nonzero circumferential
curvature on a concave cylindrical inner wall; its required reaction has the
opposite sign. Straight passage and supported turns at real convex rims or
junctions are different cases. Arbitrary station equalities and an entire
circular-disk constraint on the open half can supply a fictitious force.

The smallest justified change is authoring/pose work: preserve the native body,
endpoint and tube gates; use actual guide-contact windows rather than forced
full axial stations; reject off-wall or inadmissible-cone turns; and select only
an explicitly estimated pitch/exit side that passes native bearing-up and all 16
route certificates. Use 0.02 mm as the existing proposal margin without changing
the 1.5 mm radius/10 µm final certificate. If no such pose passes, retain
infeasibility rather than add a peg, close the opening or relax gates.

This is a local analytical/code review, not a generated route or global
mechanical-equilibrium certificate. It excludes the active margin-aligned
probes. Exact input hashes, independently recomputed force rows and limits are
in inspection.json. No native jobs, resources, images, shared files or packet
configuration were changed; finalReady remains false.
"""
(HERE/"inspection.md").write_text(text)
print(json.dumps({"status": report["status"], "report": str((HERE/"inspection.json").relative_to(ROOT)),
                  "reportSHA256": digest(HERE/"inspection.json"), "forceRowsChecked": len(checks),
                  "packetConfigUnchanged": True, "finalReady": False}))
