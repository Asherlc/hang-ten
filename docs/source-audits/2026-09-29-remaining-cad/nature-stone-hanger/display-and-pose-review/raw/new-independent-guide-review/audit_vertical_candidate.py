"""Independent arithmetic audit for the corrected vertical-seat candidate.

No optimizer, NNLS, route solve, FreeCAD, compiler or external resource runs.
Reused vector/finite-triangle arithmetic is applied afresh to the pinned new mesh.
"""
from pathlib import Path
from functools import lru_cache
import argparse
import hashlib
import json
import math

HERE = Path(__file__).resolve().parent
WORKSPACE = HERE.parents[5]
BOARD_REVIEW = HERE.parents[2]
VERTICAL = BOARD_REVIEW / 'vertical-groove-correction'
EXPECTED_SOURCE = 'ee189092c1727c096894b1223ce78fd5214f858de2908507cc5ee0e6fb1297e6'
EXPECTED_COLLIDER = '9f1c7afee52db277aaef76ea3c92fcc8ceae8223b95fd43847314a9545466d77'
EXPECTED_MODEL = 'c4aa097bb61240f0596aca0db5bff5f4a9ea195f0436c4cb27dac9d261e672ba'
EXPECTED_DESCRIPTOR = '82c3c09be41b0fe28ff2f40ba969925b4048d07dc3222b60cc0eb303ccaf2b24'
PRIOR_SIDECAR = '7c24835c38c36ad16805c605970e939f02fa40007ee12b219a4d9da1860746fb'
SHA = lambda data: hashlib.sha256(data).hexdigest()
RAW = {}


def read(path):
    path = path.resolve()
    assert path.is_relative_to(WORKSPACE) and path.is_file() and not path.is_symlink(), path
    if path not in RAW:
        RAW[path] = path.read_bytes()
    return RAW[path]


def document(path):
    return json.loads(read(path))


parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('--report', type=Path, required=True)
parser.add_argument('--report-sha', required=True)
parser.add_argument('--sidecar', type=Path, required=True)
parser.add_argument('--sidecar-sha', required=True)
parser.add_argument('--freeze', type=Path, required=True)
parser.add_argument('--freeze-sha', required=True)
parser.add_argument('--source', type=Path, default=VERTICAL / 'native-author/nature-stone-hanger.FCStd')
parser.add_argument('--model', type=Path, default=VERTICAL / 'assets/primary.usdz')
parser.add_argument('--descriptor', type=Path, default=VERTICAL / 'assets/primary.model.json')
parser.add_argument('--mesh', type=Path, default=VERTICAL / 'native-collision-vertical.json')
parser.add_argument('--expected-canonical-sidecar-sha', default=PRIOR_SIDECAR)
parser.add_argument('--output', default='sixteen-vertical-candidate-audit.json')
args = parser.parse_args()
assert Path(args.output).name == args.output and args.output.endswith('.json')
destination = HERE / args.output
assert not destination.exists(), 'Retain an immutable audit; choose another output name.'
report_path = args.report.resolve()
report = document(report_path)
assert SHA(read(report_path)) == args.report_sha
assert report['sourceSHA256'] == EXPECTED_SOURCE
assert report['colliderSHA256'] == EXPECTED_COLLIDER
candidate = document(args.sidecar)
assert SHA(read(args.sidecar)) == args.sidecar_sha == report['sidecarSHA256']
assert args.sidecar_sha not in {PRIOR_SIDECAR, '32c9cd6a1b5ef45796615392efb4382f1d557e2622f7d2aec21a4ec1153c15d3', '9520befe472f49778c32fd1747e25114fab5d9b8030b13f13359baf3dc874658'}
mesh = document(args.mesh)
assert SHA(read(args.mesh)) == EXPECTED_COLLIDER
assert mesh['sourceSHA256'] == EXPECTED_SOURCE == SHA(read(args.source))
assert candidate['modelSHA256'] == EXPECTED_MODEL == SHA(read(args.model))
assert SHA(read(args.descriptor)) == EXPECTED_DESCRIPTOR
descriptor = document(args.descriptor)
assert descriptor['modelSHA256'] == EXPECTED_MODEL
freeze = document(args.freeze)
assert SHA(read(args.freeze)) == args.freeze_sha
config_path = HERE.parent / 'packet-config.json'
config = document(config_path)
assert config['finalReady'] is False and config['nativeBodyGeometryChanged'] is True
assert config['identity']['sourceSHA256'] == EXPECTED_SOURCE
assert config['identity']['modelSHA256'] == EXPECTED_MODEL
assert config['identity']['descriptorSHA256'] == EXPECTED_DESCRIPTOR
CANONICAL = WORKSPACE / 'Hangboards/nature-stone-hanger'
canonical_names = {'sourceSHA256': 'nature-stone-hanger.FCStd', 'modelSHA256': 'assets/primary.usdz', 'descriptorSHA256': 'assets/primary.model.json', 'sidecarSHA256': 'suspension.json'}
canonical_state = {key: SHA(read(CANONICAL / name)) for key, name in canonical_names.items()}
canonical_sidecar_sha = canonical_state['sidecarSHA256']
assert canonical_sidecar_sha == args.expected_canonical_sidecar_sha != args.sidecar_sha
loaded_path = Path(report['loadedHelperPath'])
loaded_path = loaded_path if loaded_path.is_absolute() else WORKSPACE / loaded_path
assert SHA(read(loaded_path)) == report['helperSHA256']
assert freeze['status'] == 'frozen'
code_hashes = freeze['codeSHA256']
for name, digest in {**code_hashes, **freeze['inputSHA256']}.items():
    path = Path(name)
    path = path if path.is_absolute() else WORKSPACE / path
    assert SHA(read(path)) == digest, name
assert report['helperSHA256'] == code_hashes['Tools/HangboardCAD/native_cord_guides.py'], 'Loaded/final helpers must be exact; no historical branch alias.'
for pin in report['inputs']:
    path = Path(pin['path'])
    path = path if path.is_absolute() else WORKSPACE / path
    assert SHA(read(path)) == pin['sha256']
assert all(len(q) == 3 and all(math.isfinite(x) for x in q) for q in mesh['vertices'])


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
        assert all(len(q) == 3 and all(isinstance(x, (int, float)) and math.isfinite(x) for x in q) for q in p)
        assert len(p) <= 128
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
        expected_guide, expected_bore = ('LeftVerticalCordGroove', 'LeftVisibleMouth') if lead_id == 'left-lead' else ('RightVerticalCordGroove', 'RightVisibleMouth')
        assert selection['feature'] == expected_guide and selection['boreFeature'] == expected_bore
        merged = bore['mergedApertureWitness']
        assert merged['guideFeature'] == expected_guide and merged['sharedWallEdges'] > 0
        assert merged['finiteToolOverlapMM3'] > 0
        assert merged['nativeCavityMaterialVolumeMM3'] == 0
        assert merged['apertureMaterialAreaMM2'] == merged['axisMaterialLengthMM'] == 0
        assert abs(bore['outerMouthStation'] - merged['outerPlaneStationMM'] / 1000) < 1e-12
        assert bore['axialBounds'][1] < bore['outerMouthStation']
        assert abs(bore['outerMouthStation'] - .0055) < 1e-12
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
            primary = c['triangle']
            assert isinstance(primary, int) and 0 <= primary < len(faces)
            assert norm(sub(foot, closest_triangle(foot, *faces[primary][:3]))) <= 1.01e-8
            incident, weights = c['incidentMaterialTriangles'], c['materialNormalConeWeights']
            assert len(set(incident)) == len(incident)
            assert all(isinstance(fi, int) and 0 <= fi < len(faces) for fi in incident)
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
    'status': 'pass-independent-new-geometry-rounded-candidate-only',
    'sourceSHA256': EXPECTED_SOURCE, 'modelSHA256': EXPECTED_MODEL,
    'descriptorSHA256': EXPECTED_DESCRIPTOR, 'colliderSHA256': EXPECTED_COLLIDER,
    'scratchCandidateSidecarSHA256': args.sidecar_sha,
    'canonicalPackageSHA256AtInspection': canonical_state,
    'loadedHelperSHA256': report['helperSHA256'],
    'finalFrozenHelperSHA256': code_hashes['Tools/HangboardCAD/native_cord_guides.py'],
    'loadedAndFrozenHelperBytesIdentical': True,
    'reportSHA256': SHA(read(report_path)), 'codeFreezeSHA256': SHA(read(args.freeze)),
    'scriptSHA256': SHA(Path(__file__).read_bytes()),
    'inputSHA256': {str(path.relative_to(WORKSPACE)): SHA(data) for path, data in RAW.items()},
    'method': 'Independent stdlib vector arithmetic, actual finite triangles and outward-facet cone recomposition; analytical linear-span cylinder intervals. No NNLS, optimization, route solve, native resource or old-shape proof reuse.',
    'poseIDs': sorted(expected_poses), 'poseCount': 8, 'routeCount': 16,
    'positiveReactionWitnessesChecked': positive_count,
    'maximumActualFacetNodalResidual': max(x['actualFacetMaxNodalResidual'] for x in out),
    'maximumWeightedMaterialConeErrorBound': max(x['maxWeightedMaterialConeErrorBound'] for x in out),
    'maximumIndependentTieGapMicrometres': max(x['maxIndependentTieGapMicrometres'] for x in out),
    'reactionResidualLimitUnchanged': 1e-5, 'weightedConeErrorBoundLimitUnchanged': 1e-5,
    'closestFeatureTieLimitMUnchanged': 1e-5,
    'closedOutwardCollider': {'edgeIncidenceTwo': True, 'windingConsistent': True, 'signedVolumeM3': volume},
    'anchorOffsetFromBoardBoundsAtInspection': candidate['suspension']['anchor']['offsetFromBoardBounds'],
    'blockingFindings': [], 'routes': out,
    'remainingGates': ['Fresh native-derived regeneration/check, all-pose visual/app review, tests and cleanup, root integration and human acceptance.'],
    'limits': [
        'This immutable scratch candidate is separate from the canonical package state at inspection. Those mutable canonical/configuration paths in inputSHA256 are historical inspection pins, not post-integration assertions.',
        'Numerical near-contact and discrete unit-tension frictionless feasibility; no continuum cable, global equilibrium, global minimum, real load or safety certification.',
        'Physical 1.5 mm radius, 20 micrometre proposal envelope, 10 micrometre numerical contact/feature-tie allowance and reaction limit remain separate unchanged policies.',
        'Whole-solid clearance lower bounds are checked against the unchanged radius-minus-10-micrometre gate in the exact retained report; no new native collision certificate or solve runs here.',
        'Finite guide traversal, local material forces and bore intervals were recomputed from the exact rounded candidate and pinned new-shape collider. Native merged-aperture metadata is hash-bound to the author collider; no new CAD Boolean operation was performed.',
        'Groove dimensions, cord dimensions, poses and support offsets are display estimates. The concealed connection remains unspecified.',
        'Reuse of general arithmetic does not carry any earlier 1b/7f/7c shape pass to this ee1890/c4aa/82c3 candidate.'
    ],
    'inputBytesUnchanged': True, 'packetFinalReady': False,
    'canonicalMutation': False, 'newSolveOrResource': False,
}
destination.write_text(json.dumps(output, indent=2) + '\n')
text = f"""# Independent vertical-seat candidate audit

The exact source `{EXPECTED_SOURCE}` and scratch sidecar `{args.sidecar_sha}` pass this scoped independent arithmetic review: all eight pose IDs, sixteen rounded leads and {positive_count} positive reaction witnesses against the new collider `{EXPECTED_COLLIDER}`.

Actual incident outward-facet reconstruction gives maximum nodal residual {output['maximumActualFacetNodalResidual']:.9g}; force-weighted cone approximation bound {output['maximumWeightedMaterialConeErrorBound']:.9g}. Both remain below unchanged 1e-5. Independent nearest-feature tie gaps reach {output['maximumIndependentTieGapMicrometres']:.6f} micrometres against the separate unchanged 10 micrometre allowance.

Each positive contribution is local to its actual segment/fraction and finite incident material feature. The exact closed, outward collider and all nonnegative cone coefficients were checked. The complete radial span between finite vertical-seat witnesses is bounded, and every final side-bore approach has a positive continuous eroded-cylinder interval and valid finite end-cap inset. Candidate caches, support transforms and 120 mm length bounds close against exact source/model/descriptor/collider/loaded-helper/code-freeze bytes.

Prior geometry proofs are history only. The canonical package state and pending config read during inspection remain historical hash pins after any later integration; this report does not apply the candidate or assert future canonical bytes. Fresh regeneration/app/test/cleanup and human acceptance are separate gates. No solve, FreeCAD, compiler, resource or shared mutation ran. Numerical near-contact/discrete feasibility does not certify continuum rope behavior, global board equilibrium or safety.
"""
destination.with_suffix('.md').write_text(text)
print(json.dumps({'status': output['status'], 'auditSHA256': SHA(destination.read_bytes()),
                  'positiveWitnesses': positive_count,
                  'actualFacetMaximum': output['maximumActualFacetNodalResidual'],
                  'weightedErrorBound': output['maximumWeightedMaterialConeErrorBound'],
                  'finalReady': False}, indent=2))
