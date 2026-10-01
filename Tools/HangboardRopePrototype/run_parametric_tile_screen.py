"""Owned, fixed-input trimmed-reference preflight; no runtime adoption."""
from __future__ import annotations
import argparse
import hashlib
import json
import math
import os
from pathlib import Path
import signal
import sys
import time

sys.dont_write_bytecode = True
REPO = Path.cwd()
MESH_SHA = '071a553221179ef88fbeef9c1c8bbcddb1d8f5ae4ae039b6a30e87891c1473db'
PARTITION_SHA = '3f3197a465937a8b47a14845753583c6f9154e7b6869ee7e65240b9dbaabcad0'
TILES_SHA = '37a8bbfca168943da9176754427358073db3566a49af9fc7b62ebac9131d8fe2'
FROZEN_SHA = 'c43720bccda76df9df92c9a155f3d4a5a11195011a9eca17b7ba42b1e27d1f97'


def validate_uv_hits(report_path, tiles_path, descriptor_path, frozen_path):
    """Independent exact rational determinant oracle, outside query timing."""
    from fractions import Fraction
    report = json.loads(report_path.read_text())
    tiles = json.loads(tiles_path.read_text())
    mesh = json.loads(descriptor_path.read_text())['collision']
    frozen = json.loads(frozen_path.read_text())
    source = {p['id']: {t['triangle']: t['uv'] for t in p['tiles']} for p in tiles['patches'] if p['kind'] != 'unsupported'}
    seen = set()
    def point(p):
        return tuple(Fraction.from_float(float(x)) for x in p)
    def orient(a, b, c):
        return (b[0]-a[0])*(c[1]-a[1])-(b[1]-a[1])*(c[0]-a[0])
    for hit in report['hits']:
        key = hit['patch'], hit['query']
        if key in seen or not 0 <= hit['query'] < 2858:
            raise ValueError('Duplicate or invalid trim query hit')
        seen.add(key)
        a, b, c = map(point, source[hit['patch']][hit['triangle']])
        q = point(hit['chosenUV'])
        d = orient(a, b, c)
        nums = [orient(q, b, c), orient(q, c, a), orient(q, a, b)]
        if not (d > 0 and all(n > 0 for n in nums) or d < 0 and all(n < 0 for n in nums)):
            raise ValueError('Native trim hit is outside its exact parameter triangle')
    if report['pointAndMidpointCount'] != 2858 or report['attempts'] != 2858*len(source):
        raise ValueError('Fixed all-patch workload changed')
    expected_queries = []
    for r, rope in enumerate(frozen['positions']):
        threshold = frozen['radii'][r]+.0001+.00005+.0001
        points = [[p[0], p[1]-frozen['boardHeight'], p[2]] for p in rope]
        for i, p in enumerate(points):
            expected_queries.append(dict(start=p, end=p, threshold=[threshold]))
            if i+1 < len(points):
                expected_queries.append(dict(start=p, end=points[i+1], threshold=[threshold]))
    if frozen['orientation'] != [0, 0, 0, 1] or report['queries'] != expected_queries:
        raise ValueError('Actual whole-support broad-phase workload changed')
    boxes = {}
    for patch in tiles['patches']:
        if patch['kind'] == 'unsupported':
            continue
        vertices = [mesh['vertices'][vid] for tid in patch['originalTriangles'] for vid in mesh['triangles'][tid]]
        boxes[patch['id']] = ([Fraction.from_float(min(v[k] for v in vertices)) for k in range(3)],
                              [Fraction.from_float(max(v[k] for v in vertices)) for k in range(3)])
    skips = set()
    for skip in report['skippedPairs']:
        key = skip['patch'], skip['query']
        if key in skips or key in seen or skip['patch'] not in source or not 0 <= skip['query'] < 2858:
            raise ValueError('Duplicate/invalid broad-phase skip')
        skips.add(key)
        query = report['queries'][skip['query']]
        a, b = map(point, (query['start'], query['end']))
        low, high = boxes[skip['patch']]
        gap = [max(Fraction(0), low[k]-max(a[k], b[k]), min(a[k], b[k])-high[k]) for k in range(3)]
        threshold = Fraction.from_float(query['threshold'][0])
        if sum(x*x for x in gap) <= threshold*threshold:
            raise ValueError('Whole-link exact box separation does not justify omitted trim lookup')
    if report['trimLookupAttempts'] != report['attempts']-len(skips):
        raise ValueError('Lookup/skipped-pair accounting changed')
    return dict(runtimeAdoption=False, exactRationalInteriorHitsChecked=len(seen),
                exactRationalWholeSupportBoxSkipsChecked=len(skips),
                allReportedHitsStrictlyInside=True, completeGeometryPerformanceAccepted=False,
                scope='Exact chosen-UV triangle membership only. Unreported/ambiguous points require original fallback; no signed distance, whole-capsule, normal or physics/adoption proof.')


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def proof(output, descriptor, partition_path):
    from parametric_tiles import tile_envelope, unwrap_triangle
    from decimal import Decimal
    if digest(descriptor) != MESH_SHA or digest(partition_path) != PARTITION_SHA:
        raise ValueError('Retained checkpoint input changed')
    physics = json.loads(descriptor.read_text())
    mesh = physics['collision']
    partition = json.loads(partition_path.read_text())
    if partition['descriptorSHA256'] != MESH_SHA:
        raise ValueError('Partition belongs to a different mesh')
    seen, records = set(), []
    started = time.perf_counter()
    maximum = Decimal(0)
    for source in partition['patches']:
        guidance = source['guidance']
        kind = guidance['type']
        axis = max(range(3), key=lambda i: abs(guidance['Axis'][i]))
        orth = [i for i in range(3) if i != axis]
        supported = kind in ('Plane', 'Cylinder', 'Toroid') and abs(guidance['Axis'][axis]) > .999999
        # The one oblique planar patch remains original triangles. Arbitrary
        # axis approximation is not an unmeasured additional geometry change.
        supported = supported and all(abs(guidance['Axis'][k]) < 1e-12 for k in orth)
        patch = dict(id=source['id'], kind=kind if supported else 'unsupported', axis=axis,
                     center=guidance.get('Position', guidance.get('Center')),
                     radius=guidance.get('Radius'), majorRadius=guidance.get('MajorRadius'),
                     minorRadius=guidance.get('MinorRadius'))
        tiles, patch_max = [], Decimal(0)
        for tid in source['triangles']:
            if tid in seen or not 0 <= tid < len(mesh['triangles']):
                raise ValueError('Overlapping/invalid triangle partition')
            seen.add(tid)
            if not supported:
                continue
            vertices = [mesh['vertices'][i] for i in mesh['triangles'][tid]]
            uv = []
            for vertex in vertices:
                p = [x-c for x, c in zip(vertex, patch['center'])]
                if kind == 'Plane':
                    uv.append((p[orth[0]], p[orth[1]]))
                else:
                    u = math.atan2(p[orth[1]], p[orth[0]])
                    v = p[axis] if kind == 'Cylinder' else math.atan2(
                        p[axis], math.hypot(p[orth[0]], p[orth[1]]) - patch['majorRadius'])
                    uv.append((u, v))
            if kind != 'Plane':
                u = unwrap_triangle([p[0] for p in uv])
                v = unwrap_triangle([p[1] for p in uv]) if kind == 'Toroid' else [p[1] for p in uv]
                uv = list(zip(u, v))
            # atan2 and chart shifts choose coordinates, not certified inverse
            # functions. Directed evaluation measures their 3D vertex error.
            bound = tile_envelope(patch, uv, vertices)
            patch_max = max(patch_max, bound)
            tiles.append(dict(triangle=tid, uv=uv, twoSidedEnvelope=math.nextafter(float(bound), math.inf)))
        maximum = max(maximum, patch_max)
        records.append(dict(patch, originalTriangles=source['triangles'], tiles=tiles,
                            decimalUpperBound=str(patch_max)))
        print(json.dumps(dict(patch=source['id'], tiles=len(tiles), maxMicrometres=float(patch_max)*1e6)), flush=True)
    if seen != set(range(len(mesh['triangles']))):
        raise ValueError('Partition omits actual triangles')
    report = dict(owner=REPO.name, runtimeAdoption=False,
                  scope='Two-sided Hausdorff enclosure of each retained mesh triangle and its chosen trimmed parametric image. No native CAD accuracy, watertight/sign/seam topology, affine-normal/KKT bridge, nearest-point, whole-capsule/CCD, motion, timing or app adoption proof.',
                  inputSHA256={str(p.relative_to(REPO)): digest(p) for p in (descriptor, partition_path)},
                  triangleCount=len(seen), parametricTileCount=sum(len(p['tiles']) for p in records),
                  originalFallbackTriangleCount=sum(len(p['originalTriangles']) for p in records if p['kind']=='unsupported'),
                  decimalMaximumTwoSidedEnvelope=str(maximum),
                  isolatedAllowanceMetres=.0001, enclosureCheckpointAccepted=maximum <= Decimal('0.0001'),
                  seconds=time.perf_counter()-started, patches=records)
    (output/'tiles.json').write_text(json.dumps(report, separators=(',', ':'), allow_nan=False)+'\n')
    print(json.dumps({k: v for k, v in report.items() if k != 'patches'}, indent=2))
    return 0 if report['enclosureCheckpointAccepted'] else 3


def main():
    if len(sys.argv) > 1 and sys.argv[1] == '--worker':
        output, descriptor, partition = map(Path, sys.argv[2:])
        root = REPO/'.context'/f'{REPO.name}-parametric-tiles'
        if output.parent != root or os.environ.get('HANGTEN_PARAMETRIC_OWNER') != REPO.name:
            raise ValueError('Worker is not owned by this workspace')
        return proof(output, descriptor, partition)
    from run_native_contact_screen import OwnedCommands
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('mode', choices=['fixtures', 'proof', 'uv-fixtures', 'uv-replay', 'uv-near-replay'])
    parser.add_argument('--label', required=True)
    parser.add_argument('--tiles', type=Path)
    parser.add_argument('--frozen', type=Path)
    args = parser.parse_args()
    if not args.label or any(c not in 'abcdefghijklmnopqrstuvwxyz0123456789-_' for c in args.label):
        parser.error('Use a unique lowercase owned output label')
    workspace = Path(os.environ.get('PASEO_WORKTREE_PATH', REPO)).resolve()
    if workspace != REPO or os.environ.get('HANGTEN_PARAMETRIC_OWNER') != REPO.name:
        parser.error('Use the owned shell launcher from this workspace')
    root = REPO/'.context'/f'{REPO.name}-parametric-tiles'
    output = root/f'{args.mode}-{args.label}'
    for path in (REPO/'.context', root, output):
        if path.is_symlink():
            parser.error('Owned output cannot be a symlink')
    root.mkdir(exist_ok=True)
    output.mkdir()  # Never overwrite a retained result or its provenance.
    snapshot = output/'source-inputs'
    snapshot.mkdir()
    source = REPO/'Tools/HangboardRopePrototype'
    sources = [Path(__file__), Path(__file__).with_suffix('.sh'), source/'parametric_tiles.py',
               source/'run_native_contact_screen.py', source/'tests/test_parametric_tiles.py']
    if args.mode.startswith('uv-'):
        sources += [source/'native_geometry/ParametricUV.swift', source/'native_geometry'/
                    ('ParametricUVFixtures.swift' if args.mode == 'uv-fixtures' else 'ParametricUVReplay.swift')]
    for path in sources:
        (snapshot/path.name).write_bytes(path.read_bytes())
    descriptor = REPO/'.context/strong-owl-live-physics-handoff/mini-seven-mm/candidate.physics.json'
    partition = REPO/'.context/strong-owl-live-physics-handoff/mini-dynamics-probe/strong-owl-mini-native-patches.json'
    if digest(descriptor) != MESH_SHA or digest(partition) != PARTITION_SHA:
        parser.error('Input differs from fixed retained checkpoint')
    inputs = [descriptor, partition]
    if args.mode in ('uv-replay', 'uv-near-replay'):
        if not args.tiles or not args.frozen or digest(args.tiles) != TILES_SHA or digest(args.frozen) != FROZEN_SHA:
            parser.error('Native trim replay requires the fixed proved tiles and production frozen state')
        args.tiles, args.frozen = args.tiles.resolve(), args.frozen.resolve()
        inputs += [args.tiles, args.frozen]
    provenance = dict(owner=REPO.name, runtimeAdoption=False,
                      sources={str(p.relative_to(REPO)): dict(snapshot=str((snapshot/p.name).relative_to(REPO)), sha256=digest(snapshot/p.name)) for p in sources},
                      inputSHA256={str(p.relative_to(REPO)): digest(p) for p in inputs})
    (output/'provenance.json').write_text(json.dumps(provenance, indent=2)+'\n')
    commands = OwnedCommands(REPO.name, root)
    signal.signal(signal.SIGINT, commands.interrupted)
    signal.signal(signal.SIGTERM, commands.interrupted)
    env = dict(os.environ, PYTHONPATH=str(snapshot), HANGTEN_UV_BROAD_PHASE='1' if args.mode == 'uv-near-replay' else '0')
    argv = ([sys.executable, '-B', '-m', 'unittest', 'discover', '-s', str(snapshot), '-p', 'test_parametric_tiles.py', '-v']
            if args.mode == 'fixtures' else
            [sys.executable, '-B', str(snapshot/Path(__file__).name), '--worker', str(output), str(descriptor), str(partition)])
    try:
        if args.mode.startswith('uv-'):
            main_source = 'ParametricUVFixtures.swift' if args.mode == 'uv-fixtures' else 'ParametricUVReplay.swift'
            (output/'main.swift').write_bytes((snapshot/main_source).read_bytes())
            binary = output/f'{REPO.name}-trim-probe'
            compile_argv = ['xcrun', 'swiftc', '-O', '-whole-module-optimization', '-module-cache-path', str(output/'module-cache'),
                            str(snapshot/'ParametricUV.swift'), str(output/'main.swift'), '-o', str(binary)]
            status = commands.run('parametric-uv-compile', compile_argv, output/'compile.log', env)
            if status:
                print((output/'compile.log').read_text())
                return status
            invocation = [str(binary)]
            if args.mode in ('uv-replay', 'uv-near-replay'):
                invocation += [str(args.tiles), str(args.frozen), str(descriptor), str(output/'replay.json')]
            status = commands.run('parametric-uv-probe', invocation, output/'run.log', env)
            print((output/'run.log').read_text())
            if status == 0 and args.mode in ('uv-replay', 'uv-near-replay'):
                validation = validate_uv_hits(output/'replay.json', args.tiles, descriptor, args.frozen)
                (output/'validation.json').write_text(json.dumps(validation, indent=2)+'\n')
                print(json.dumps(validation, indent=2))
            return status
        status = commands.run('parametric-'+args.mode, argv, output/'run.log', env)
        print((output/'run.log').read_text())
        return status
    finally:
        commands.cleanup()


if __name__ == '__main__':
    raise SystemExit(main())
