"""Read frozen routes; check witnesses with arithmetic only, never a route solver."""
from pathlib import Path
from functools import lru_cache
import ast
import hashlib
import json
import math

HERE = Path(__file__).resolve().parent
BOARD_REVIEW = HERE.parents[1]
WORKSPACE = HERE.parents[4]
ATTEMPTS = BOARD_REVIEW / 'notch-guide-implementation'
CANDIDATE = ATTEMPTS / 'isolated-root/Hangboards/nature-stone-hanger'
CANONICAL = WORKSPACE / 'Hangboards/nature-stone-hanger'
RAW = {}
SHA = lambda data: hashlib.sha256(data).hexdigest()


def read(path):
    path = path.resolve()
    if path not in RAW:
        RAW[path] = path.read_bytes()
    return RAW[path]


def document(path):
    return json.loads(read(path))


utilities = HERE / 'check_material_normal_v4.py'
names = {'add', 'sub', 'scale', 'dot', 'norm', 'cross', 'closest_triangle',
         'box_distance_squared', 'global_nearest'}
tree = ast.parse(read(utilities))
functions = [n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name in names]
assert len(functions) == len(names)
exec(compile(ast.Module(body=functions, type_ignores=[]), str(utilities), 'exec'), globals())

report_path = ATTEMPTS / 'sixteen-guided-route-certificates.json'
report = document(report_path)
assert SHA(read(report_path)) == '1d64f315da41a96b521e530481eafc08e5ad2060f9822c765390e8d24378f7a1'
candidate = document(CANDIDATE / 'suspension.json')
mesh = document(ATTEMPTS / 'native-collision-with-guides.json')
freeze = document(ATTEMPTS / 'final-solver-code-freeze.json')
config = document(BOARD_REVIEW / 'review-preparation/packet-config.json')
descriptor = document(CANDIDATE / 'assets/primary.model.json')
assert not config['finalReady']
assert SHA(read(CANDIDATE / 'suspension.json')) == report['sidecarSHA256']
assert SHA(read(ATTEMPTS / 'native-collision-with-guides.json')) == report['colliderSHA256']
assert mesh['sourceSHA256'] == report['sourceSHA256'] == config['identity']['sourceSHA256']
assert SHA(read(CANDIDATE / 'nature-stone-hanger.FCStd')) == report['sourceSHA256']
assert candidate['modelSHA256'] == config['identity']['modelSHA256']
assert SHA(read(CANDIDATE / 'assets/primary.usdz')) == config['identity']['modelSHA256']
assert SHA(read(CANDIDATE / 'assets/primary.model.json')) == config['identity']['descriptorSHA256']
assert SHA(read(CANONICAL / 'nature-stone-hanger.FCStd')) == report['sourceSHA256']
canonical_sidecar_sha = SHA(read(CANONICAL / 'suspension.json'))
assert canonical_sidecar_sha == '32c9cd6a1b5ef45796615392efb4382f1d557e2622f7d2aec21a4ec1153c15d3'
assert canonical_sidecar_sha != report['sidecarSHA256']
loaded_path = WORKSPACE / report['loadedHelperPath']
assert SHA(read(loaded_path)) == report['helperSHA256']
for name, digest in freeze['files'].items():
    assert SHA(read(WORKSPACE / name)) == digest, name
for pin in report['inputs']:
    assert SHA(read(Path(pin['path']))) == pin['sha256']


def erase_straight_branch(source):
    tree = ast.parse(source)
    for node in tree.body:
        if isinstance(node, ast.FunctionDef) and node.name == 'certify_active_reactions':
            node.body = [n for n in node.body if not (
                isinstance(n, ast.If) and
                ast.unparse(n.test) == 'not len(required) or np.linalg.norm(required) < REACTION_RESIDUAL_LIMIT')]
    return ast.dump(tree, include_attributes=False)


assert erase_straight_branch(read(loaded_path)) == erase_straight_branch(read(WORKSPACE / 'Tools/HangboardCAD/native_cord_guides.py'))
expected_poses = {'edge-front-15mm-incut', 'edge-front-15mm-flat',
                  'edge-reverse-10mm-incut', 'edge-reverse-10mm-flat',
                  'edge-reverse-06mm-flat', 'edge-reverse-06mm-incut',
                  'edge-front-20mm-wood-flat', 'edge-front-20mm-granite'}
assert set(report['poses']) == set(candidate['suspension']['canonicalPoses']) == expected_poses
assert report['routeCount'] == 16 and report['status'] == 'pass'
features = mesh['nativeCordFeatures']
solver = candidate['ropeSolver']
assert solver['method'] == 'nativeRoutes'
assert solver['grooveGuides']['sourceSHA256'] == report['sourceSHA256']
strands = {s['id']: s for s in candidate['suspension']['strands']}
assert set(strands) == {'left-lead', 'right-lead'}
assert set(solver['grooveGuides']['byPoseID']) == expected_poses
vertices = mesh['vertices']
faces = []
volume = 0.0
edges = {}
for ids in mesh['triangles']:
    a, b, c = [vertices[i] for i in ids]
    n = cross(sub(b, a), sub(c, a))
    assert norm(n) > 0
    faces.append((a, b, c, scale(n, 1 / norm(n)),
                  [(min(a[j], b[j], c[j]), max(a[j], b[j], c[j])) for j in range(3)]))
    volume += dot(a, cross(b, c)) / 6
    for i, j in zip(ids, [ids[1], ids[2], ids[0]]):
        key = (min(i, j), max(i, j))
        count, winding = edges.get(key, (0, 0))
        edges[key] = (count + 1, winding + (1 if i < j else -1))
assert volume > 0 and all(count == 2 and winding == 0 for count, winding in edges.values())


@lru_cache(maxsize=None)
def closest_cached(q, initial):
    return global_nearest(list(q), initial)


def radial(point, origin, axis):
    d = sub(point, origin)
    return norm(sub(d, scale(axis, dot(d, axis))))


def frame(feature):
    axis = feature['axis']
    return feature['origin'], scale(axis, 1 / norm(axis))


def finite_tail_interval(path, radius, bore, clearance):
    origin, axis = frame(bore)
    start, end = path[-2:]
    delta = sub(end, start)
    d = sub(start, origin)
    axial0, axial_delta = dot(d, axis), dot(delta, axis)
    lo, hi = 0.0, 1.0
    amin, amax = radius + clearance - 1e-8, bore['outerMouthStation']
    if abs(axial_delta) > 1e-15:
        roots = sorted([(amin - axial0) / axial_delta, (amax - axial0) / axial_delta])
        lo, hi = max(lo, roots[0]), min(hi, roots[1])
    else:
        assert amin <= axial0 <= amax
    rv, rd = sub(d, scale(axis, axial0)), sub(delta, scale(axis, axial_delta))
    aa, bb, cc = dot(rd, rd), 2 * dot(rv, rd), dot(rv, rv) - (bore['radius'] - radius + 1e-8) ** 2
    if aa > 1e-30:
        discr = bb * bb - 4 * aa * cc
        assert discr >= 0
        roots = sorted([(-bb - math.sqrt(discr)) / (2 * aa), (-bb + math.sqrt(discr)) / (2 * aa)])
        lo, hi = max(lo, roots[0]), min(hi, roots[1])
    else:
        assert cc <= 0
    assert 0 <= lo < hi <= 1 and hi > 1 - 1e-10
    return lo, hi, (hi - lo) * norm(delta)


out = []
positive_count = 0
for pose_id, pose_report in report['poses'].items():
    pose = candidate['suspension']['canonicalPoses'][pose_id]
    assert set(pose_report['leads']) == set(pose['wrappedRoutes']) == set(strands)
    assert set(solver['grooveGuides']['byPoseID'][pose_id]) == set(strands)
    for lead_id, lead in pose_report['leads'].items():
        p = lead['pathModelM']
        assert p[1:] == pose['wrappedRoutes'][lead_id]
        assert all(abs(x - round(x, 9)) < 1e-15 for q in p[1:] for x in q)
        bounds = descriptor['modelBounds']
        anchor = [(lo + hi) / 2 for lo, hi in zip(bounds['min'], bounds['max'])]
        anchor[1] = bounds['max'][1]
        anchor = add(anchor, candidate['suspension']['anchor']['offsetFromBoardBounds'])
        vector = sub(anchor, pose['translation'])
        q = pose['rotation']
        assert abs(dot(q, q) - 1) < 1e-12
        xyz = scale(q[:3], -1)
        turn = scale(cross(xyz, vector), 2)
        support = add(vector, add(scale(turn, q[3]), cross(xyz, turn)))
        assert norm(sub(support, p[0])) < 1e-12
        radius, rest = strands[lead_id]['radius'], strands[lead_id]['restLength']
        assert radius == .0015 and rest == .12
        length = sum(norm(sub(b, a)) for a, b in zip(p, p[1:]))
        assert abs(length / rest - lead['lengthRatio']) < 1e-12
        assert length / rest <= 1 + 1e-6
        assert lead['continuousClearanceLowerBound'] >= radius - 1e-5
        selection = solver['grooveGuides']['byPoseID'][pose_id][lead_id]
        guide, bore = features[selection['feature']], features[selection['boreFeature']]
        assert guide['kind'] == 'groove' and bore['kind'] == 'bore'
        assert guide['wallFaces'] and bore['wallFaces']
        origin, axis = frame(guide)
        available = guide['radius'] - radius
        terminal = p[-1]
        center = dot(sub(terminal, origin), axis)
        endpoint = guide['axialBounds'][1 if selection['exitSign'] > 0 else 0]
        assert (endpoint - center) * selection['exitSign'] > 2 * radius
        witnesses = []
        for fraction, stated in zip((2 / 3, 1 / 3), lead['seating']['witnesses']):
            station = center + (endpoint - center) * fraction
            candidates = []
            for i, (a, b) in enumerate(zip(p, p[1:])):
                da, db = dot(sub(a, origin), axis) - station, dot(sub(b, origin), axis) - station
                if da * db > 0 or abs(db - da) < 1e-12:
                    continue
                t = -da / (db - da)
                point = add(a, scale(sub(b, a), t))
                rd = radial(point, origin, axis)
                if rd <= available + 1e-5:
                    candidates.append((i + t, point, rd))
            assert candidates
            found = candidates[-1]
            assert abs(found[0] - stated['pathParameter']) < 1e-12
            assert norm(sub(found[1], stated['point'])) < 1e-12
            assert abs(found[2] - stated['radialDistance']) < 1e-12
            assert abs(station - stated['axialStation']) < 1e-12
            witnesses.append(found)
        first, last = witnesses
        assert first[0] < last[0]
        points = [first[1], last[1]] + p[math.floor(first[0]) + 1:math.ceil(last[0])]
        maximum_radial = max(radial(point, origin, axis) for point in points)
        assert maximum_radial <= available + 1e-5
        assert abs(maximum_radial - lead['seating']['maximumInnerSpanRadialDistance']) < 1e-12
        bore_origin, bore_axis = frame(bore)
        terminal_axial = dot(sub(terminal, bore_origin), bore_axis)
        terminal_radial = radial(terminal, bore_origin, bore_axis)
        inset = bore['outerMouthStation'] - terminal_axial
        assert terminal_radial + radius <= bore['radius'] + 1e-8
        assert terminal_axial >= radius + solver['clearance'] - 1e-8
        assert inset >= radius + solver['clearance'] - 1e-8
        assert abs(inset - lead['entry']['insetFromActualOuterPlane']) < 1e-12
        assert terminal == solver['terminalsByStrandID'][lead_id]['points'][0]
        mouth_axis = solver['terminalsByStrandID'][lead_id]['mouthAxis']
        assert dot(mouth_axis, bore_axis) >= 1 - 1e-8
        assert dot(sub(p[-2], terminal), mouth_axis) > 1e-8
        tail_lo, tail_hi, exact_tail_length = finite_tail_interval(p, radius, bore, solver['clearance'])
        assert 0 < lead['entry']['finiteTailLength'] <= exact_tail_length + 1e-12
        reactions = lead['reactions']
        assert reactions['proposalMargin'] == 2e-5 and reactions['contactNumericalAllowance'] == 1e-5
        assert reactions['closestFeatureTieAllowance'] == reactions['materialConeResidualLimit'] == 1e-5
        dirs = [scale(sub(b, a), 1 / norm(sub(b, a))) for a, b in zip(p, p[1:])]
        required = [sub(a, b) for a, b in zip(dirs, dirs[1:])]
        assert norm([x for row in required for x in row]) > 1e-5
        assert max(norm(sub(a, b)) for a, b in zip(required, reactions['requiredNodalReactions'])) < 1e-12
        actual = [[0.0] * 3 for _ in required]
        radial_forces = [[0.0] * 3 for _ in required]
        error_bounds = [0.0 for _ in required]
        checks = []
        for ci, c in enumerate(reactions['activeContacts']):
            i, t, weight = c['segment'], c['fraction'], c['weight']
            assert math.isfinite(weight) and weight > 0 and 0 <= t <= 1
            assert 0 <= i < len(p) - 1
            point, foot, n = c['point'], c['materialPoint'], c['normal']
            assert norm(sub(point, add(scale(p[i], 1 - t), scale(p[i + 1], t)))) < 1e-12
            distance = norm(sub(point, foot))
            assert abs(distance - c['distance']) < 1e-12
            assert norm(sub(n, scale(sub(point, foot), 1 / distance))) < 1e-12
            closest, _ = closest_cached(tuple(point), distance)
            tie_gap = distance - closest
            assert -1e-11 <= tie_gap <= 1e-5 + 1e-11
            assert distance <= radius + 2e-5 + 1e-5 + 1e-12
            incident, weights = c['incidentMaterialTriangles'], c['materialNormalConeWeights']
            assert incident and len(incident) == len(weights) and all(math.isfinite(w) and w >= 0 for w in weights)
            for fi in incident:
                a, b, d, _, _ = faces[fi]
                assert norm(sub(foot, closest_triangle(foot, a, b, d))) <= 1.01e-8
            direction = [sum(w * faces[fi][3][j] for fi, w in zip(incident, weights)) for j in range(3)]
            mismatch = norm(sub(n, direction))
            assert mismatch <= 1e-5 + 1e-10
            for node, fraction in ((i - 1, 1 - t), (i, t)):
                if 0 <= node < len(required):
                    actual[node] = add(actual[node], scale(direction, weight * fraction))
                    radial_forces[node] = add(radial_forces[node], scale(n, weight * fraction))
                    error_bounds[node] += weight * fraction * mismatch
            checks.append({'index': ci, 'segment': i, 'fraction': t, 'forceWeight': weight,
                           'incidentFacetCount': len(incident), 'coneResidual': mismatch,
                           'weightedConeResidual': weight * mismatch,
                           'independentTieGapMicrometres': tie_gap * 1e6,
                           'globalNearestFieldDifferenceM': abs(closest - c['globalClosestDistance'])})
        actual_errors = [sub(a, b) for a, b in zip(required, actual)]
        radial_errors = [norm(sub(a, b)) for a, b in zip(required, radial_forces)]
        actual_max = max(norm(e) for e in actual_errors)
        assert actual_max <= 1e-5 and max(radial_errors) <= 1e-5
        assert max(error_bounds) <= 1e-5
        facet_report = reactions['facetReconstructedBalance']
        assert max(norm(sub(a, b)) for a, b in zip(actual_errors, facet_report['facetReconstructedNodalResiduals'])) < 1e-12
        assert abs(actual_max - facet_report['maxFacetReconstructedNodalResidual']) < 1e-12
        assert max(abs(a - b) for a, b in zip(error_bounds, facet_report['weightedMaterialConeErrorBounds'])) < 1e-12
        assert all(norm(sub(a, b)) <= bound + 1e-12 for a, b, bound in zip(actual, radial_forces, error_bounds))
        positive_count += len(checks)
        out.append({'poseID': pose_id, 'leadID': lead_id, 'status': 'pass-scoped-rounded-candidate',
                    'positiveContactsChecked': len(checks), 'pathVertices': len(p),
                    'actualFacetMaxNodalResidual': actual_max,
                    'maxWeightedMaterialConeErrorBound': max(error_bounds),
                    'maxRadialNodalResidual': max(radial_errors),
                    'maxIndependentTieGapMicrometres': max(c['independentTieGapMicrometres'] for c in checks),
                    'lengthRatio': length / rest, 'retainedContinuousClearanceLowerBoundM': lead['continuousClearanceLowerBound'],
                    'finiteGuideSpanMaximumRadialM': maximum_radial,
                    'finiteGuideWitnessesOnActualPath': True,
                    'wholeInnerGuideSpanBoundedByConvexRadialNorm': True,
                    'actualMouthTerminalInsetM': inset,
                    'continuousFinalSegmentBoreInterval': [tail_lo, tail_hi],
                    'continuousFinalSegmentBoreLengthM': exact_tail_length,
                    'reportedSampledBoreLengthM': lead['entry']['finiteTailLength'],
                    'localPositiveWitnesses': checks})
    assert abs(max(l['lengthRatio'] for l in pose_report['leads'].values()) - 1) <= 1e-6

assert len(out) == 16
assert all(path.read_bytes() == data for path, data in RAW.items())
output = {
    'status': 'pass-independent-rounded-candidate-scope-only',
    'sourceSHA256': report['sourceSHA256'], 'colliderSHA256': report['colliderSHA256'],
    'scratchCandidateSidecarSHA256': report['sidecarSHA256'],
    'canonicalIntermediateSidecarSHA256AtInspection': canonical_sidecar_sha,
    'loadedHelperSHA256': report['helperSHA256'],
    'finalFrozenHelperSHA256': freeze['files']['Tools/HangboardCAD/native_cord_guides.py'],
    'loadedVsFinalDifferenceOnlyUnusedStraightForceBranch': True,
    'allReviewedRoutesUseNonzeroForceBranch': True,
    'reportSHA256': SHA(read(report_path)), 'scriptSHA256': SHA(Path(__file__).read_bytes()),
    'inputSHA256': {str(path.relative_to(WORKSPACE)): SHA(data) for path, data in RAW.items()},
    'method': 'Stdlib vector arithmetic, retained finite triangles, supplied outward-normal cone reconstruction and analytical cylinder/linear-span intervals. No NNLS, optimizer, route solver, FreeCAD or resource.',
    'poseIDs': sorted(expected_poses), 'poseCount': 8, 'routeCount': 16,
    'positiveReactionWitnessesChecked': positive_count,
    'maximumActualFacetNodalResidual': max(x['actualFacetMaxNodalResidual'] for x in out),
    'maximumWeightedMaterialConeErrorBound': max(x['maxWeightedMaterialConeErrorBound'] for x in out),
    'maximumIndependentTieGapMicrometres': max(x['maxIndependentTieGapMicrometres'] for x in out),
    'reactionResidualLimitUnchanged': 1e-5, 'closestFeatureTieLimitMUnchanged': 1e-5,
    'closedOutwardCollider': {'edgeIncidenceTwo': True, 'windingConsistent': True, 'signedVolumeM3': volume},
    'blockingFindings': [], 'routes': out,
    'remainingGates': ['Fresh full native-derived regeneration/check, final visual comparisons, current-source all-eight actual app review, broader tests/cleanup, root integration and human acceptance.'],
    'limits': ['This exact 7c248 scratch candidate is distinct from eventual canonical sidecar bytes; no canonical application or human approval is implied.',
               'Reaction proof is numerical near-contact and discrete unit-tension feasibility, not continuum rope dynamics or global board equilibrium.',
               'The 20 micrometre proposal margin, 10 micrometre contact envelope, 10 micrometre feature-tie rule and physical full-radius clearance gate remain separate.',
               'Whole-solid/tube clearance lower bounds are bound to the retained author report and inspected for unchanged gate compliance; a new collision certificate was not run.',
               'Finite groove and bore assertions were independently recomputed from exact rounded paths and pinned analytic feature metadata; no native geometry or unseen connection was authored.',
               'Material points and projected distances retain the documented mesh-incidence and generic projection limitations of the prior v4 review.',
               'Positions, pitch, anchor offsets, rest length and radius remain operator display estimates; this audit does not source their numeric values or certify load safety.'],
    'inputBytesUnchanged': True, 'packetConfigUnchanged': True, 'packetFinalReady': False,
    'canonicalMutation': False, 'newSolveOrResource': False,
}
destination = HERE / 'sixteen-candidate-7c248-audit.json'
assert not destination.exists(), 'This candidate audit is immutable; use a new filename for another audit.'
destination.write_text(json.dumps(output, indent=2) + '\n')
text = f"""# Independent rounded candidate review

The exact scratch sidecar `{report['sidecarSHA256']}` passes this scoped review: eight pose IDs, sixteen rounded leads, and {positive_count} positive reaction witnesses. Actual outward-facet forces give maximum nodal residual {output['maximumActualFacetNodalResidual']:.9g}; force-weighted normal approximation bound {output['maximumWeightedMaterialConeErrorBound']:.9g}; both are below unchanged 1e-5. Independent near-tie gaps remain at most {output['maximumIndependentTieGapMicrometres']:.6f} micrometres against unchanged 10 micrometres.

Every witness maps to its actual local segment/fraction and nonempty nonnegative incident-facet cone. The collider is closed and consistently outward. Groove stations, path order and the complete intermediate radial span were independently recomputed; final bore entry has a positive continuous eroded-cylinder interval, proper approach and terminal inset. All exact path caches match the candidate sidecar and settled support transforms; lead ratios satisfy the unchanged 120 mm display estimate gates.

Exact source, collider, candidate, four solver outputs, retained loaded helper and six-file solver freeze hashes close. The loaded helper differs from the frozen helper only in an unused straight-force reporting branch. Retained whole-solid clearance bounds were checked for gate compliance; no new collision/solver job ran.

This candidate remains separate from canonical `32c9…`, with fresh regeneration/check, final comparisons, actual-app review and acceptance pending. The proof remains numerical near-contact and discrete frictionless feasibility; it does not certify exact continuum cable behavior, global board equilibrium, sourced cord dimensions or safety. Configuration and every input remain byte-exact; `finalReady=false`. No resource, shared edit, canonical application or packet build occurred.
"""
(HERE / 'sixteen-candidate-7c248-audit.md').write_text(text)
print(json.dumps({'status': output['status'], 'auditSHA256': SHA(destination.read_bytes()),
                  'positiveWitnesses': positive_count,
                  'actualFacetMaximum': output['maximumActualFacetNodalResidual'],
                  'weightedErrorBound': output['maximumWeightedMaterialConeErrorBound'],
                  'finalReady': False}, indent=2))
