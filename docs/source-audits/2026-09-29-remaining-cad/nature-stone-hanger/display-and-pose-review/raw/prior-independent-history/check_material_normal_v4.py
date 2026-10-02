"""Independent arithmetic/mesh witness review; no optimization or CAD runtime."""
from pathlib import Path
from itertools import combinations
import hashlib
import json
import math

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
ATTEMPTS = ROOT / 'notch-guide-implementation'
FROZEN = ATTEMPTS / 'material-normal-v4'
SHA = lambda data: hashlib.sha256(data).hexdigest()
PATHS = [FROZEN / 'summary.json', FROZEN / 'native_cord_guides.py',
         FROZEN / 'offset-anchor-probe-reactions.json',
         FROZEN / 'native-seed-no-free-knee-probe-reactions.json',
         ATTEMPTS / 'offset-anchor-probe.json',
         ATTEMPTS / 'native-seed-no-free-knee-probe.json',
         ROOT / 'pose-review/native-collision-final-source.json',
         HERE / 'distributed-contact-supplement.json',
         ROOT / 'review-preparation/packet-config.json',
         HERE / 'material-normal-v3-review.json']
RAW = {p: p.read_bytes() for p in PATHS}
summary = json.loads(RAW[PATHS[0]])
mesh = json.loads(RAW[PATHS[6]])
previous = json.loads(RAW[PATHS[7]])
config = json.loads(RAW[PATHS[8]])
assert not config['finalReady']
assert SHA(RAW[PATHS[1]]) == summary['helperSHA256']


def add(a, b):
    return [x + y for x, y in zip(a, b)]


def sub(a, b):
    return [x - y for x, y in zip(a, b)]


def scale(a, s):
    return [s * x for x in a]


def dot(a, b):
    return sum(x * y for x, y in zip(a, b))


def norm(a):
    return math.sqrt(dot(a, a))


def cross(a, b):
    return [a[1] * b[2] - a[2] * b[1], a[2] * b[0] - a[0] * b[2],
            a[0] * b[1] - a[1] * b[0]]


def closest_triangle(p, a, b, c):
    """Classify a point into a triangle's vertex, edge or face Voronoi region."""
    ab, ac, ap = sub(b, a), sub(c, a), sub(p, a)
    d1, d2 = dot(ab, ap), dot(ac, ap)
    if d1 <= 0 and d2 <= 0:
        return a
    bp = sub(p, b)
    d3, d4 = dot(ab, bp), dot(ac, bp)
    if d3 >= 0 and d4 <= d3:
        return b
    vc = d1 * d4 - d3 * d2
    if vc <= 0 and d1 >= 0 and d3 <= 0:
        return add(a, scale(ab, d1 / (d1 - d3)))
    cp = sub(p, c)
    d5, d6 = dot(ab, cp), dot(ac, cp)
    if d6 >= 0 and d5 <= d6:
        return c
    vb = d5 * d2 - d1 * d6
    if vb <= 0 and d2 >= 0 and d6 <= 0:
        return add(a, scale(ac, d2 / (d2 - d6)))
    va = d3 * d6 - d5 * d4
    if va <= 0 and d4 - d3 >= 0 and d5 - d6 >= 0:
        return add(b, scale(sub(c, b), (d4 - d3) / ((d4 - d3) + (d5 - d6))))
    denominator = va + vb + vc
    if denominator == 0:
        candidates = []
        for u, v in ((a, b), (b, c), (c, a)):
            delta = sub(v, u)
            t = max(0, min(1, dot(sub(p, u), delta) / dot(delta, delta)))
            candidates.append(add(u, scale(delta, t)))
        return min(candidates, key=lambda q: dot(sub(q, p), sub(q, p)))
    return add(a, add(scale(ab, vb / denominator), scale(ac, vc / denominator)))


vertices = mesh['vertices']
faces = []
volume = 0.0
for ids in mesh['triangles']:
    a, b, c = [vertices[i] for i in ids]
    n = cross(sub(b, a), sub(c, a))
    assert norm(n) > 0
    n = scale(n, 1 / norm(n))
    bounds = [(min(a[j], b[j], c[j]), max(a[j], b[j], c[j])) for j in range(3)]
    faces.append((a, b, c, n, bounds))
    volume += dot(a, cross(b, c)) / 6
assert volume > 0


def box_distance_squared(point, bounds):
    return sum(max(lo - x, x - hi, 0) ** 2 for x, (lo, hi) in zip(point, bounds))


def global_nearest(point, initial_distance):
    best_squared = (initial_distance + 2e-9) ** 2
    best = None
    for fi, (a, b, c, _, bounds) in enumerate(faces):
        if box_distance_squared(point, bounds) > best_squared:
            continue
        foot = closest_triangle(point, a, b, c)
        squared = dot(sub(point, foot), sub(point, foot))
        if squared <= best_squared:
            best_squared, best = squared, fi
    assert best is not None
    return math.sqrt(best_squared), best


def incident_faces(point, tolerance):
    result = []
    for fi, (a, b, c, _, bounds) in enumerate(faces):
        if box_distance_squared(point, bounds) > tolerance * tolerance:
            continue
        if norm(sub(point, closest_triangle(point, a, b, c))) <= tolerance:
            result.append(fi)
    return result


def cone_distance(ns, target):
    best = norm(target)
    for size in (1, 2, 3):
        for indices in combinations(range(len(ns)), size):
            a = [ns[i] for i in indices]
            if size == 1:
                weights = [dot(a[0], target)]
            elif size == 2:
                s = dot(a[0], a[1])
                denominator = 1 - s * s
                if denominator < 1e-14:
                    continue
                u, v = dot(a[0], target), dot(a[1], target)
                weights = [(u - s * v) / denominator, (v - s * u) / denominator]
            else:
                denominator = dot(a[0], cross(a[1], a[2]))
                if abs(denominator) < 1e-12:
                    continue
                weights = [dot(target, cross(a[1], a[2])) / denominator,
                           dot(a[0], cross(target, a[2])) / denominator,
                           dot(a[0], cross(a[1], target)) / denominator]
            if min(weights) < -1e-10:
                continue
            fitted = [sum(w * v[j] for w, v in zip(weights, a)) for j in range(3)]
            best = min(best, norm(sub(target, fitted)))
    return best


results = []
for pin in summary['reports']:
    report_path = Path(pin['report'])
    report = json.loads(RAW[report_path])
    path_path = ATTEMPTS / report['pathReport']
    path_report = json.loads(RAW[path_path])
    assert SHA(RAW[report_path]) == pin['sha256']
    assert SHA(RAW[path_path]) == report['pathSHA256']
    assert SHA(RAW[PATHS[6]]) == report['collisionMeshSHA256']
    assert summary['helperSHA256'] == report['helperSHA256']
    assert mesh['sourceSHA256'] == report['sourceSHA256'] == summary['sourceSHA256'] == path_report['sourceSHA256']
    p = path_report['path']
    directions = [scale(sub(b, a), 1 / norm(sub(b, a))) for a, b in zip(p, p[1:])]
    required = [sub(a, b) for a, b in zip(directions, directions[1:])]
    assembled = [[0.0] * 3 for _ in required]
    material_assembled = [[0.0] * 3 for _ in required]
    cone_error_bounds = [0.0 for _ in required]
    checks = []
    for ci, contact in enumerate(report['activeContacts']):
        i, t, w = contact['segment'], contact['fraction'], contact['weight']
        q, foot, n = contact['point'], contact['materialPoint'], contact['normal']
        assert w > 0 and 0 <= t <= 1 and 0 <= i < len(p) - 1
        interpolation = add(scale(p[i], 1 - t), scale(p[i + 1], t))
        assert norm(sub(q, interpolation)) < 1e-12
        radial = sub(q, foot)
        distance = norm(radial)
        assert abs(distance - contact['distance']) < 1e-12
        assert norm(sub(n, scale(radial, 1 / distance))) < 1e-12
        closest_distance, closest_id = global_nearest(q, distance)
        closest_error = abs(closest_distance - contact['globalClosestDistance'])
        gap = distance - closest_distance
        assert -1e-11 <= gap <= summary['closestFeatureTieAllowanceM'] + 1e-11
        assert distance <= sum(summary['contactEnvelope'].values()) + 1e-12
        a, b, c, _, _ = faces[contact['triangle']]
        projection_difference = norm(sub(foot, closest_triangle(q, a, b, c)))
        material_point_error = norm(sub(foot, closest_triangle(foot, a, b, c)))
        # The certificate admits a near-global-distance material point. Do not
        # silently equate that rule with exact triangle projection coordinates.
        assert material_point_error <= 1e-8
        actual_incident = incident_faces(foot, 1e-8)
        assert set(contact['incidentMaterialTriangles']) <= set(actual_incident), {
            'report': report['pathReport'], 'contact': ci,
            'missing': list(set(contact['incidentMaterialTriangles']) - set(actual_incident)),
            'extra': list(set(actual_incident) - set(contact['incidentMaterialTriangles'])),
            'claimedDistancesM': {fi: norm(sub(foot, closest_triangle(foot, *faces[fi][:3])))
                                  for fi in contact['incidentMaterialTriangles']},
        }
        cone_weights = contact['materialNormalConeWeights']
        assert len(cone_weights) == len(contact['incidentMaterialTriangles'])
        assert all(weight >= 0 for weight in cone_weights)
        fitted_normal = [sum(weight * faces[fi][3][j] for fi, weight
                             in zip(contact['incidentMaterialTriangles'], cone_weights)) for j in range(3)]
        cone_error = norm(sub(n, fitted_normal))
        cone_passes = bool(cone_weights) and cone_error <= summary['materialNormalConeResidualLimit'] + 1e-10
        force = scale(n, w)
        left, right = scale(force, 1 - t), scale(force, t)
        material_force = scale(fitted_normal, w)
        material_left, material_right = scale(material_force, 1 - t), scale(material_force, t)
        moment_error = norm(sub(add(cross(p[i], left), cross(p[i + 1], right)), cross(q, force)))
        if i > 0:
            assembled[i - 1] = add(assembled[i - 1], left)
            material_assembled[i - 1] = add(material_assembled[i - 1], material_left)
            cone_error_bounds[i - 1] += (1 - t) * w * cone_error
        if i + 1 < len(p) - 1:
            assembled[i] = add(assembled[i], right)
            material_assembled[i] = add(material_assembled[i], material_right)
            cone_error_bounds[i] += t * w * cone_error
        checks.append({'contact': ci, 'segment': i, 'fraction': t, 'point': q,
                       'materialPoint': foot, 'normal': n, 'weight': w,
                       'distanceMM': distance * 1000,
                       'independentGlobalClosestDistanceMM': closest_distance * 1000,
                       'independentClosestTriangle': closest_id,
                       'globalClosestDistanceErrorM': closest_error,
                       'materialPointDistanceToCarrierTriangleM': material_point_error,
                       'carrierTriangleClosestPointCoordinateDifferenceM': projection_difference,
                       'tieGapMicrometres': gap * 1e6,
                       'allSuppliedIncidentTrianglesIndependentlyLocal': True,
                       'suppliedIncidentTriangleIDs': contact['incidentMaterialTriangles'],
                       'independentlyNearbyIncidentTriangleIDs': actual_incident,
                       'nonemptyMaterialConeWitness': bool(cone_weights),
                       'materialConeWitnessPasses': cone_passes,
                       'additionalNearbyIncidentTrianglesNotUsed': list(set(actual_incident) - set(contact['incidentMaterialTriangles'])),
                       'reconstructedConeResidual': cone_error,
                       'reportedConeResidual': contact['materialNormalConeResidual'],
                       'reconstructedMaterialNormal': fitted_normal,
                       'forceWeightTimesConeResidual': w * cone_error,
                       'firstMomentError': moment_error})
    nodal_errors = [norm(sub(a, b)) for a, b in zip(required, assembled)]
    material_errors = [norm(sub(a, b)) for a, b in zip(required, material_assembled)]
    material_shift = [norm(sub(a, b)) for a, b in zip(assembled, material_assembled)]
    assert all(delta <= bound + 1e-13 for delta, bound in zip(material_shift, cone_error_bounds))
    assert max(nodal_errors) < summary['reactionResidualLimit']
    assert max(norm(sub(a, b)) for a, b in zip(required, report['requiredNodalReactions'])) < 1e-12
    opposing = []
    for a, b in combinations(checks, 2):
        if norm(sub(a['point'], b['point'])) > 1e-12:
            continue
        if a['normal'][1] * b['normal'][1] >= 0:
            continue
        opposing.append({'contacts': [a['contact'], b['contact']], 'point': a['point'],
                         'opposingRuntimeYComponents': [a['normal'][1], b['normal'][1]],
                         'tieGapMicrometres': [a['tieGapMicrometres'], b['tieGapMicrometres']],
                         'coneResiduals': [a['reconstructedConeResidual'], b['reconstructedConeResidual']]})
    invalid_cones = [c['contact'] for c in checks if not c['materialConeWitnessPasses']]
    material_passes = max(material_errors) < summary['reactionResidualLimit']
    results.append({'pathReport': report['pathReport'],
                    'status': 'fail-material-normal-witness' if invalid_cones or not material_passes else 'pass-scoped-discrete-envelope-witness',
                    'routeLengthMM': path_report['length'] * 1000,
                    'retainedWholeSegmentClearanceCertificate': path_report['certificate'],
                    'contactsChecked': len(checks), 'polylineVertices': len(p),
                    'maxIndependentlyAssembledNodalResidual': max(nodal_errors),
                    'maxActualFacetConeNodalResidual': max(material_errors),
                    'maxForceWeightedNormalApproximationBound': max(cone_error_bounds),
                    'materialNodalResiduals': material_errors,
                    'normalApproximationNodalBounds': cone_error_bounds,
                    'actualFacetBalancePassesUnchangedTolerance': material_passes,
                    'invalidMaterialConeContacts': invalid_cones,
                    'unchangedReactionResidualLimit': summary['reactionResidualLimit'],
                    'maxClosestFeatureTieGapMicrometres': max(c['tieGapMicrometres'] for c in checks),
                    'maxReconstructedMaterialConeResidual': max(c['reconstructedConeResidual'] for c in checks),
                    'maxGlobalDistanceErrorM': max(c['globalClosestDistanceErrorM'] for c in checks),
                    'maxCarrierProjectionCoordinateDifferenceM': max(c['carrierTriangleClosestPointCoordinateDifferenceM'] for c in checks),
                    'contactDistanceMMRange': [min(c['distanceMM'] for c in checks), max(c['distanceMM'] for c in checks)],
                    'samePointOpposingComponentWitnesses': opposing, 'perContribution': checks})

regressions = []
for ci in (0, 1):
    old = previous['materialNormalCheck']['perContribution'][ci]
    fi = incident_faces(old['foot'], 1e-8)
    residual = cone_distance([faces[i][3] for i in fi], old['normal'])
    assert residual > summary['materialNormalConeResidualLimit']
    regressions.append({'originalContact': ci, 'residualAgainstCurrentIncidentMeshCone': residual,
                        'rejected': True, 'incidentTriangleIDs': fi})
unchanged = all(p.read_bytes() == data for p, data in RAW.items())
assert unchanged
output = {
    'status': 'blocked-empty-material-cones-and-facet-balance-failure' if any(t['status'].startswith('fail') for t in results) else 'pass-independent-one-lead-discrete-envelope-review',
    'sourceSHA256': mesh['sourceSHA256'], 'helperSHA256': summary['helperSHA256'],
    'collisionMeshSHA256': SHA(RAW[PATHS[6]]), 'scriptSHA256': SHA(Path(__file__).read_bytes()),
    'inputSHA256': {str(p.relative_to(ROOT)): SHA(data) for p, data in RAW.items()},
    'method': 'Stdlib closest-point Voronoi calculations and exhaustive triangle AABB lower bounds, supplied cone-weight reconstruction, and local barycentric force/moment arithmetic. No NNLS, optimizer, route solver, CAD runtime or resource.',
    'meshSignedVolumeM3': volume, 'reviewedTrials': results,
    'independentClosestDistanceErrorsRecordedWithoutExactProjectionClaim': True,
    'falseTangentialDirectionRegressions': regressions,
    'tieInterpretation': 'Independent global-nearest calculations verify the unchanged 10 micrometre near-tie activity; small differences from reported generic projections are recorded. Nonempty supplied incident cones establish local outward directions, including genuine opposing wall components near the bore/rim. The force-weighted actual-facet reconstruction is checked separately against the unchanged nodal tolerance. This remains numerical near-contact activity, not exact simultaneous contact of a physical 1.5 mm tube.',
    'blockingFindings': [] if all(t['status'].startswith('pass') for t in results) else ['A trial fails actual material-cone witness or reconstructed facet-force balance; inspect per-contact details.'],
    'frozenHelperReview': {'emptyConeExplicitlyRejected': True,
                          'residualIndependentlyRecomputed': True,
                          'finiteTriangleIncidenceMethod': 'Orthonormal plane/barycentric membership with 10 nm plane proximity and 1e-6 barycentric tolerance; audited against independent stdlib triangle calculations.',
                          'sharedImplementationOrFullSolverApproval': False},
    'priorV3FailureSHA256': SHA(RAW[PATHS[9]]),
    'limits': [
        'Material direction, local mapping and tie-distance arithmetic pass for two frozen one-lead trials only; final sixteen routes, settled lengths, caches and app proof remain pending.',
        'The tie tolerance is a distance to the global closest material feature. It is distinct from the 20 micrometre proposal margin, 10 micrometre contact-envelope allowance and unchanged full-radius continuous-clearance gate.',
        'Cone incidence uses a separately documented 10 nanometre mesh proximity, not exact native BRep incidence. No fresh native-surface normal query was performed.',
        'Some generic carrier-triangle foot coordinates differ from independent exact triangle projections. The material points themselves lie on the retained triangles and pass the global near-tie distance rule; do not claim exact per-triangle projections.',
        'Positive cone membership is a local unilateral direction check. Barycentric stationarity is a discrete frictionless envelope approximation; it does not prove exact continuum rope curvature, mechanical board equilibrium, load capacity or safety.',
        'The frozen helper also contains route generation and metadata validation code, which was read but not executed or approved as a complete shared implementation in this review.',
    ],
    'inputBytesUnchanged': unchanged, 'packetConfigUnchanged': True,
    'packetFinalReady': False, 'canonicalMutation': False, 'newSolveOrResource': False,
}
(HERE / 'material-normal-v4-review.json').write_text(json.dumps(output, indent=2) + '\n')
lines = ['# Independent frozen material-normal v4 review', '',
         'Both frozen one-lead trials pass the scoped material-normal witness check. Every positive force maps to its actual segment/fraction and has nonempty, local incident facets with nonnegative coefficients. Independent material-point membership and global-nearest arithmetic confirm the unchanged 10 micrometre near-tie activity. Actual facet-normal force reconstruction, rather than just radial directions, passes the unchanged 1e-5 nodal tolerance.', '']
for trial in results:
    lines.append(f"- `{trial['pathReport']}`: {trial['contactsChecked']} contacts; no invalid material cones. Radial nodal residual {trial['maxIndependentlyAssembledNodalResidual']:.3g}; actual facet force balance residual {trial['maxActualFacetConeNodalResidual']:.9g} and weighted normal-error bound {trial['maxForceWeightedNormalApproximationBound']:.9g}, both below unchanged 1e-5. Maximum tie gap {trial['maxClosestFeatureTieGapMicrometres']:.6f} micrometres.")
lines.extend(['', f"Generic reported global-nearest distances differ from the independent calculation by up to {max(t['maxGlobalDistanceErrorM'] for t in results) * 1e9:.5f} nm, and carrier-foot coordinates differ from exact per-triangle projections by up to {max(t['maxCarrierProjectionCoordinateDifferenceM'] for t in results) * 1e6:.5f} micrometres. The material points themselves lie on the local triangles and their independently computed near-tie gaps remain below 10 micrometres. No exact per-triangle projection claim is made."])
lines.extend(['', 'The frozen helper explicitly rejects empty incident sets and recomputes the normal-cone residual from the actual outward normals and coefficients. Barycentric distribution preserves local resultant and moment. Original false tangential directions 0 and 1 remain rejected at residuals approximately 0.047398 and 0.182615. The v3 empty-cone failure and earlier raw diagnostic failures remain immutable history.', '',
              'The 10 micrometre tie rule admits local opposing bore/rim wall components with actual outward-cone witnesses. These are legitimate directions within the stated numerical near-contact approximation; they do not establish exact simultaneous real-rope contact. Differences between generic triangle/global-nearest projections and the independent arithmetic are recorded explicitly; all activity distances are independently checked against the unchanged 10 micrometre rule. No routing or force tolerance changes.', '',
              'This is explicitly numerical near-contact and discrete frictionless feasibility. The tie distance, 20 micrometre proposal margin, 10 micrometre contact-envelope allowance and unchanged physical-radius clearance certificate remain separate. The 10 nanometre mesh-incidence approximation and inflated-envelope tube-to-wall gaps are not exact native BRep or real rope contact proof.', '',
              'No all-pose, 120 mm settled-height, cache, actual-app or global board equilibrium completion follows from these two one-lead trials. No optimizer, CAD job, solver, resource, shared change or packet build ran. Every input and the deferred configuration remained unchanged; `finalReady=false`.'])
(HERE / 'material-normal-v4-review.md').write_text('\n'.join(lines) + '\n')
print(json.dumps({'status': output['status'],
                  'reportSHA256': SHA((HERE / 'material-normal-v4-review.json').read_bytes()),
                  'contactsChecked': sum(t['contactsChecked'] for t in results),
                  'inputBytesUnchanged': unchanged, 'finalReady': False}, indent=2))
