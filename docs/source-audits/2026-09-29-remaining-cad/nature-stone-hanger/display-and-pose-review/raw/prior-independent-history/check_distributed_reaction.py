"""Read retained diagnostics and recompute arithmetic; no optimizer or CAD runtime."""
from pathlib import Path
from itertools import combinations
import hashlib
import json
import math

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
PROBE = ROOT / 'notch-guide-implementation'
INPUTS = [
    PROBE / 'offset-anchor-probe.json',
    PROBE / 'offset-anchor-probe-distributed-reaction-dense.json',
    PROBE / 'distributed_reaction_dense.py',
    PROBE / 'distributed_reaction_probe.py',
    PROBE / 'optimize_offset_anchor.py',
    ROOT / 'pose-review/native-collision-final-source.json',
    ROOT / 'pose-review/native-contact-orientation.json',
    HERE / 'inspection.json',
    ROOT / 'review-preparation/packet-config.json',
]
RAW = {p: p.read_bytes() for p in INPUTS}
SHA = lambda b: hashlib.sha256(b).hexdigest()


def sub(a, b):
    return [x - y for x, y in zip(a, b)]


def dot(a, b):
    return sum(x * y for x, y in zip(a, b))


def cross(a, b):
    return [a[1] * b[2] - a[2] * b[1], a[2] * b[0] - a[0] * b[2],
            a[0] * b[1] - a[1] * b[0]]


def norm(a):
    return math.sqrt(dot(a, a))


def cone_distance(normals, target):
    # A cone in R3 needs at most three generators. Enumerate these tiny exact
    # linear bases; do not run NNLS, a route solver, or a geometry runtime.
    best = (norm(target), None)
    for k in (1, 2, 3):
        for ids in combinations(range(len(normals)), k):
            ns = [normals[i] for i in ids]
            if k == 1:
                cs = [dot(ns[0], target)]
            elif k == 2:
                s = dot(ns[0], ns[1])
                den = 1 - s * s
                if den < 1e-14:
                    continue
                u, v = dot(ns[0], target), dot(ns[1], target)
                cs = [(u - s * v) / den, (v - s * u) / den]
            else:
                det = dot(ns[0], cross(ns[1], ns[2]))
                if abs(det) < 1e-12:
                    continue
                cs = [dot(target, cross(ns[1], ns[2])) / det,
                      dot(ns[0], cross(target, ns[2])) / det,
                      dot(ns[0], cross(ns[1], target)) / det]
            if min(cs) < -1e-10:
                continue
            fitted = [sum(c * n[j] for c, n in zip(cs, ns)) for j in range(3)]
            error = norm(sub(target, fitted))
            if error < best[0]:
                best = (error, {'basis': list(ids), 'weights': cs})
    return best


path_report = json.loads(RAW[INPUTS[0]])
reaction = json.loads(RAW[INPUTS[1]])
mesh = json.loads(RAW[INPUTS[5]])
config = json.loads(RAW[INPUTS[-1]])
p = path_report['path']
dirs = []
for a, b in zip(p, p[1:]):
    delta = sub(b, a)
    dirs.append([x / norm(delta) for x in delta])
required = [sub(a, b) for a, b in zip(dirs, dirs[1:])]
assembled = [[0.0] * 3 for _ in required]
vertices = mesh['vertices']
faces = []
signed_volume = 0.0
for index, ids in enumerate(mesh['triangles']):
    a, b, c = [vertices[i] for i in ids]
    u, v = sub(b, a), sub(c, a)
    raw_normal = cross(u, v)
    magnitude = norm(raw_normal)
    if not magnitude:
        continue
    normal = [x / magnitude for x in raw_normal]
    bounds = [(min(a[j], b[j], c[j]), max(a[j], b[j], c[j])) for j in range(3)]
    faces.append((index, ids, a, u, v, normal, bounds))
    signed_volume += dot(a, cross(b, c)) / 6

checks = []
max_point_error = max_radial_error = max_moment_error = 0.0
for ci, contact in enumerate(reaction['activeContacts']):
    i, t, weight = contact['segment'], contact['fraction'], contact['weight']
    q, foot, n = contact['point'], contact['foot'], contact['normal']
    interpolated = [(1 - t) * p[i][j] + t * p[i + 1][j] for j in range(3)]
    point_error = norm(sub(q, interpolated))
    radial = sub(q, foot)
    radial_error = norm(sub(n, [x / norm(radial) for x in radial]))
    force = [weight * x for x in n]
    f0, f1 = [[factor * x for x in force] for factor in (1 - t, t)]
    moment_error = norm(sub([a + b for a, b in zip(cross(p[i], f0), cross(p[i + 1], f1))],
                            cross(q, force)))
    if i > 0:
        assembled[i - 1] = [x + y for x, y in zip(assembled[i - 1], f0)]
    if i + 1 < len(p) - 1:
        assembled[i] = [x + y for x, y in zip(assembled[i], f1)]
    hits = []
    for fi, ids, a, u, v, outward, bounds in faces:
        if any(foot[j] < lo - 2e-9 or foot[j] > hi + 2e-9
               for j, (lo, hi) in enumerate(bounds)):
            continue
        s = sub(foot, a)
        if abs(dot(s, outward)) > 2e-9:
            continue
        uu, vv, uv = dot(u, u), dot(v, v), dot(u, v)
        us, vs = dot(u, s), dot(v, s)
        den = uu * vv - uv * uv
        if den <= 0:
            continue
        b0, c0 = (us * vv - vs * uv) / den, (vs * uu - us * uv) / den
        bary = [1 - b0 - c0, b0, c0]
        if min(bary) < -1e-6:
            continue
        hits.append({'triangle': fi, 'vertexIDs': ids, 'outwardNormal': outward,
                     'footBarycentric': bary})
    cone_error, basis = cone_distance([h['outwardNormal'] for h in hits], n)
    checks.append({'contact': ci, 'segment': i, 'fraction': t, 'weight': weight,
                   'point': q, 'foot': foot, 'normal': n,
                   'distanceMM': norm(radial) * 1000,
                   'actualRadiusGapMicrometres': norm(radial) * 1e6 - 1500,
                   'incidentFaces': hits, 'incidentConeResidual': cone_error,
                   'incidentConeBasis': basis,
                   'incidentConeAngleDegrees': math.degrees(math.asin(min(1, cone_error)))})
    max_point_error = max(max_point_error, point_error)
    max_radial_error = max(max_radial_error, radial_error)
    max_moment_error = max(max_moment_error, moment_error)

residuals = [norm(sub(r, a)) for r, a in zip(required, assembled)]
bad = [q for q in checks if q['incidentConeResidual'] > 1e-6]
unchanged = all(p.read_bytes() == raw for p, raw in RAW.items())
assert unchanged, 'An input changed during the independent arithmetic check'
assert not config['finalReady']
assert all(c['weight'] > 0 and 0 <= c['fraction'] <= 1 for c in reaction['activeContacts'])
assert all(c['incidentFaces'] for c in checks)
assert max_point_error < 1e-12 and max_radial_error < 1e-12
assert max(residuals) < 1e-12

report = {
    'status': 'diagnostic-requires-admissible-material-normal-check',
    'sourceSHA256': mesh['sourceSHA256'],
    'scriptSHA256': SHA(Path(__file__).read_bytes()),
    'inputSHA256': {str(p.relative_to(ROOT)): SHA(b) for p, b in RAW.items()},
    'method': 'Stdlib arithmetic on retained reports and triangulated native mesh; no optimization, CAD job, route authoring, or new resource.',
    'forceConvention': 'Material-on-rope R=T*(incomingForwardUnit-outgoingForwardUnit), equivalent to -T*(two outgoing unit tangents). T is normalized to 1.',
    'localAssembly': {
        'passes': True, 'activeContributions': len(checks), 'polylineVertices': len(p),
        'nonnegativeWeights': True, 'allPointsOnNamedLocalSegments': True,
        'maxPointInterpolationErrorM': max_point_error,
        'maxRadialVectorError': max_radial_error,
        'maxForceFirstMomentError': max_moment_error,
        'independentMaxNodalResidual': max(residuals),
        'reportedMaxNodalResidual': reaction['maxNodalResidual'],
        'noRemoteConeTransfer': 'Each force is applied only to its own segment endpoints using (1-t),t; no unrelated route node receives the force.',
    },
    'materialNormalCheck': {
        'meshSignedVolumeM3': signed_volume,
        'footPlaneToleranceM': 2e-9, 'footBarycentricTolerance': 1e-6,
        'coneMethod': 'Enumerate nonnegative combinations of one, two, or three incident outward facet normals. Positive cone membership is a necessary local check; it does not prove exact native curved-surface pressure or global closest-feature activity.',
        'allFootPointsOnRetainedMesh': True,
        'notInIncidentConeCount': len(bad),
        'largestIncidentConeResidual': max(q['incidentConeResidual'] for q in checks),
        'largestIncidentConeAngleDegrees': max(q['incidentConeAngleDegrees'] for q in checks),
        'finding': 'The script collects triangle-wise closest feet from every triangle within 1.53 mm, not solely globally closest material features. Radial vectors to some non-nearest vertex feet are outside the material outward-normal cone and can create tangential directions in NNLS.',
        'perContribution': checks,
    },
    'contactEnvelope': {
        'physicalRadiusMM': 1.5, 'proposalMarginMM': .02, 'numericalAllowanceMM': .01,
        'candidateWallDistanceMM': [min(c['distanceMM'] for c in checks), max(c['distanceMM'] for c in checks)],
        'physicalRadiusGapMicrometres': [min(c['actualRadiusGapMicrometres'] for c in checks), max(c['actualRadiusGapMicrometres'] for c in checks)],
        'limitation': 'These are near contacts of the explicitly inflated display-authoring envelope, not demonstrated exact contact of a 1.5 mm physical tube. Do not conflate 20 micrometre proposal margin with the unchanged full-radius clearance certificate.',
    },
    'retainedClearanceCertificate': path_report['certificate'],
    'fixedHeightLengthMM': path_report['length'] * 1000,
    'requestedRestLengthMM': 120,
    'action': 'Before a final reaction gate, retain triangle and closest-feature witnesses and use admissible outward material normals (including genuine active edge/vertex cones). Recompute the same local nonnegative fit after that filter. If the witness remains approximate, explicitly bound and label the approximation rather than claiming exact frictionless string equilibrium.',
    'limits': [
        'One left lead, one estimated 30 degree pose and 50 mm anchor offset only; height and all sixteen final routes remain unresolved.',
        'Barycentric assembly preserves force resultant and moment and establishes a weak/discrete nodal balance. It does not establish continuum equilibrium of each straight polyline edge or board force/torque equilibrium.',
        'Increasing contact sampling density alone does not refine the 13-vertex centerline or prove continuum convergence.',
        'The retained triangulated native mesh is the independent normal-check boundary. No fresh FreeCAD normal or topology job was launched.',
        'This finding does not prove the unchanged groove/bore geometry incapable of a supported route and does not authorize changing it or relaxing any gate.',
    ],
    'initialInspectionSHA256': SHA(RAW[HERE / 'inspection.json']),
    'inputBytesUnchanged': unchanged, 'packetFinalReady': False,
    'packetConfigUnchanged': True, 'resourcesCreated': False,
    'canonicalOrSharedMutation': False,
}
(HERE / 'distributed-contact-supplement.json').write_text(json.dumps(report, indent=2) + '\n')
text = f"""# Independent distributed-reaction diagnostic check

The local assembly passes: all {len(checks)} positive-weight forces use their reported segment and fraction; the reaction sign, barycentric resultant and moment are correct. Independent maximum nodal residual is {max(residuals):.3g}. No remote route node or virtual guide station supplies these forces.

Normal admissibility remains unresolved. The generator admits every triangle foot within 1.53 mm, including non-nearest vertices. Against the exact retained collision mesh, {len(bad)} of {len(checks)} positive-weight radial vectors lie outside the cone of all incident outward facet normals. The largest residual is {max(q['incidentConeResidual'] for q in checks):.9f}, equivalent to {max(q['incidentConeAngleDegrees'] for q in checks):.5f} degrees; contacts 0 and 1 give 0.047398 and 0.182615. A zero NNLS residual can therefore use directions that are not demonstrated unilateral wall-pressure normals. This is a check on the retained mesh, not fresh native-surface validation.

Use genuinely closest material-feature normals, retain triangle/feature IDs and active edge/vertex cone witnesses, then repeat the nonnegative local fit. The 1.514616–1.529957 mm reported distances are near contacts of the inflated proposal envelope, leaving about 14.6–30.0 micrometres beyond the actual 1.5 mm radius; label that approximation explicitly. Keep the unchanged whole-segment full-radius certificate separate.

The 30-degree / 50-mm-offset probe remains diagnostic at 118.476 mm against the 120 mm rest estimate. Barycentric balance is a discrete contact approximation, not continuum or global board equilibrium. Neither dense force sampling nor this one lead proves all poses. No geometry change, gate relaxation, new solve/resource, packet build, promotion or shared edit was performed. `finalReady` remains false; the prior inspection remains byte-exact.
"""
(HERE / 'distributed-contact-supplement.md').write_text(text)
print(json.dumps({'reportSHA256': SHA((HERE / 'distributed-contact-supplement.json').read_bytes()),
                  'notInIncidentConeCount': len(bad), 'maxNodalResidual': max(residuals),
                  'inputBytesUnchanged': unchanged, 'finalReady': config['finalReady']}, indent=2))
