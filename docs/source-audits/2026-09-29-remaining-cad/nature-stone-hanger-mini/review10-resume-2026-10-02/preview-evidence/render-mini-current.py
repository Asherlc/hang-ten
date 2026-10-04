"""Whole frozen Mini CAD and cached-cord previews with shared per-pixel depth."""
from pathlib import Path
import ast
import hashlib
import json
import sys
import numpy as np
from PIL import Image, ImageDraw

sys.dont_write_bytecode = True
REPO = Path.cwd()
OUT = Path(__file__).resolve().parent
PACKAGE = REPO/'Hangboards/nature-stone-hanger-mini'
H = lambda p: hashlib.sha256(Path(p).read_bytes()).hexdigest()


def json_hash(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(',', ':')).encode()).hexdigest()


def extract_functions(path, names, scope):
    tree = ast.parse(path.read_text())
    selected = [node for node in tree.body if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and node.name in names]
    assert {node.name for node in selected} == set(names)
    module = ast.Module(body=selected, type_ignores=[])
    exec(compile(module, str(path), 'exec'), scope)


def main():
    identity = json.loads((OUT/'input-identity.json').read_text())
    before = {name: H(PACKAGE/name) for name in identity['canonical4']}
    assert before == identity['canonical4']
    manifest = OUT/'generated-board.json'
    assert H(manifest) == identity['generatedManifestSHA256']
    board = json.loads(manifest.read_text())
    setup = board['presentations'][0]['media']['suspension']
    sidecar = json.loads((PACKAGE/'suspension.json').read_text())
    assert setup == sidecar['suspension']
    descriptor = json.loads((PACKAGE/'assets/primary.model.json').read_text())
    assert descriptor['modelSHA256'] == before['assets/primary.usdz'] == sidecar['modelSHA256']
    scene_script = REPO/'.context/placid-badger/flash-board-review14/post-handoff-preparation/render-cord-views.py'
    depth_script = REPO/'.context/placid-badger/flash-board-review14/independent-shape/crossed-display-review/placid-badger-crossed-depth-review.py'
    pose_helper = REPO/'Tools/HangboardCAD/solve_threaded_rope.py'
    reader = REPO/'Tools/HangboardCAD/usdz_writer.py'
    scope = {'np': np, 'Image': Image}
    extract_functions(pose_helper, {'rotate_inverse'}, scope)
    extract_functions(scene_script, {'rotate', 'tube_triangles'}, scope)
    extract_functions(depth_script, {'render'}, scope)
    sys.path.insert(0, str(REPO/'Tools/HangboardCAD'))
    from usdz_writer import read_usdz
    model = read_usdz(PACKAGE/'assets/primary.usdz')
    bindings = {node['nodeID']: node for node in descriptor['nodes']}
    assert set(model['nodes']) == set(bindings)
    assert len(bindings) == 5
    assert not model['materials'] and all(node['material'] is None for node in model['nodes'].values())
    bound_min, bound_max = (np.asarray(descriptor['modelBounds'][k]) for k in ('min', 'max'))
    anchor = (bound_min + bound_max) / 2
    anchor[1] = bound_max[1]
    anchor += np.asarray(setup['anchor']['offsetFromBoardBounds'])
    assert setup['anchor']['visibility'] == 'invisible'
    packet = REPO/'docs/source-audits/2026-09-29-remaining-cad/nature-stone-hanger-mini/completion-review'
    certificate = json.loads((packet/'continuous-cached-route-certificate.json').read_text())
    views = [
        {'file': 'mini-current-upright-granite-selection.png', 'pose': 'front-upright',
         'selected': 'granite-edge-15', 'eye': [0.65, 0.38, 1.0],
         'title': 'Current Stone Hanger Mini | Upright granite edge | Neutral CAD diagnostic selection'},
        {'file': 'mini-current-jug-open-up-selection.png', 'pose': 'jug-open-up',
         'selected': 'pull-up-jug', 'eye': [1.2, 1.35, 0.8],
         'title': 'Current Stone Hanger Mini | Jug opening up | Neutral CAD diagnostic selection'},
    ]
    records = []
    for view in views:
        pose_id = view['pose']
        pose = setup['canonicalPoses'][pose_id]
        rotation, translation = pose['rotation'], np.asarray(pose['translation'])
        selected_nodes = descriptor['contacts'][view['selected']]['nodeIDs']
        assert selected_nodes == [node['nodeID'] for node in descriptor['nodes'] if node.get('contactID') == view['selected']]
        parts, colors, node_records, strands = [], [], {}, []
        for node_id, node in model['nodes'].items():
            vertices = scope['rotate'](rotation, node['points_m']) + translation
            triangle_indices = np.asarray(node['triangles'])
            triangles = vertices[triangle_indices]
            parts.append(triangles)
            selected = node_id in selected_nodes
            colors.extend([(211, 50, 46) if selected else (174, 174, 174)] * len(triangles))
            node_records[node_id] = {'descriptorRole': bindings[node_id]['role'],
                'contactID': bindings[node_id].get('contactID'), 'selectedRed': selected,
                'vertices': len(vertices), 'triangles': len(triangles),
                'posedBoundsM': [vertices.min(axis=0).tolist(), vertices.max(axis=0).tolist()]}
        board_triangles = np.concatenate(parts)
        board_bounds = [board_triangles.min(axis=(0, 1)).tolist(), board_triangles.max(axis=(0, 1)).tolist()]
        for strand in setup['strands']:
            cached = pose['wrappedRoutes'][strand['id']]
            path = scope['rotate'](rotation, cached) + translation
            if strand['kind'] in ('lead', 'loop'):
                path = np.vstack([anchor, path])
            if strand['kind'] == 'loop':
                path = np.vstack([path, anchor])
            triangles = scope['tube_triangles'](path, strand['radius'])
            parts.append(triangles)
            colors.extend([(54, 54, 54)] * len(triangles))
            cert = certificate['poses'][pose_id]['strands'][strand['id']]
            assert len(path) == cert['pointCount'] and strand['radius'] == cert['radiusMeters']
            strands.append({'id': strand['id'], 'kind': strand['kind'], 'radiusMeters': strand['radius'],
                'restLengthMeters': strand['restLength'], 'cachedBoardLocalPoints': cached,
                'cachedBoardLocalPointsSHA256': json_hash(cached), 'derivedWorldPath': path.tolist(),
                'pointCountIncludingMetadataAnchor': len(path),
                'derivedPathLengthMeters': float(np.linalg.norm(np.diff(path, axis=0), axis=1).sum()),
                'tubeTriangles': len(triangles), 'tubeRadialFacets': 12})
        triangles = np.concatenate(parts)
        eye = np.asarray(view['eye'], dtype=float)
        eye /= np.linalg.norm(eye)
        right = np.cross([0.0, 1.0, 0.0], eye)
        right /= np.linalg.norm(right)
        camera_up = np.cross(eye, right)
        matrix = np.stack([right, camera_up, eye])
        projected = triangles @ matrix.T
        bounds = (projected[:, :, :2].min(axis=(0, 1)), projected[:, :, :2].max(axis=(0, 1)))
        assert np.all(projected[:, :, :2] >= bounds[0]-1e-12)
        assert np.all(projected[:, :, :2] <= bounds[1]+1e-12)
        whole = scope['render'](projected, np.asarray(colors), bounds)
        image = Image.new('RGB', (1000, 700), 'white')
        image.paste(whole, (0, 64))
        draw = ImageDraw.Draw(image)
        draw.text((20, 12), view['title'], fill=(25, 25, 25))
        draw.text((20, 36), 'Exact current mesh + saved cord cache | Whole scene, shared depth | Current app appearance unverified', fill=(55, 55, 55))
        target = OUT/view['file']
        image.save(target)
        span = bounds[1]-bounds[0]
        record = {'path': str(target), 'sha256': H(target), 'canvasPixels': list(image.size),
            'poseID': pose_id, 'poseQuaternionXYZW': rotation, 'poseTranslationMeters': pose['translation'],
            'savedPoseCameraMetadata': pose.get('camera'), 'poseAndCachedRoutesSHA256': json_hash(pose),
            'operatorReviewCamera': {'projection': 'orthographic', 'eyeDirectionWorld': eye.tolist(),
                'lookDirectionWorld': (-eye).tolist(), 'rightWorld': right.tolist(), 'upWorld': camera_up.tolist(),
                'worldToCameraRotationRows': matrix.tolist(), 'projectedFullSceneBoundsMeters': [b.tolist() for b in bounds],
                'projectedCenterMeters': ((bounds[0]+bounds[1])/2).tolist(),
                'scalePixelsPerMeter': float(min(960/span[0], 566/span[1])),
                'geometryCanvasPixels': [1000, 636], 'geometryCanvasOffsetPixels': [0, 64],
                'canvasSelection': 'operator-selected whole-scene canvas; geometry bounds fit without crop'},
            'selectedContactID': view['selected'], 'selectedNodeIDs': selected_nodes,
            'redGeometry': 'only all triangles in exact descriptor-bound selected USDZ nodes',
            'nodes': node_records, 'boardWorldBoundsMeters': board_bounds,
            'wholeBoardCordWorldBoundsMeters': [triangles.min(axis=(0,1)).tolist(), triangles.max(axis=(0,1)).tolist()],
            'anchorWorldMeters': anchor.tolist(), 'anchorVisibility': 'invisible', 'strands': strands,
            'meshTriangleCount': len(board_triangles), 'derivedCordTubeTriangleCount': len(triangles)-len(board_triangles),
            'singleSharedPerPixelDepthBuffer': True, 'pixelOcclusion': 'barycentric orthographic depth; larger camera Z wins for both CAD and cord triangles',
            'runtimeVerified': False, 'currentAppFrames': 0}
        records.append(record)
        print(json.dumps({'image': view['file'], 'sha256': record['sha256'], 'pose': pose_id}), flush=True)
    after = {name: H(PACKAGE/name) for name in before}
    assert before == after
    provenance = {'owner': 'placid-badger', 'scope': 'current Mini whole CAD/cache review previews only',
        'canonicalPackage': str(PACKAGE), 'canonicalHashesBefore': before, 'canonicalHashesAfter': after,
        'canonicalFourBytesUnchanged': True, 'generatedManifest': {'path': str(manifest), 'sha256': H(manifest)},
        'runtimeCanonicalPosesAndCachesSHA256': json_hash(setup['canonicalPoses']),
        'runtimeSuspensionSHA256': json_hash(setup), 'sourcePacketReferences': {name: {'path': str(packet/name), 'sha256': H(packet/name)} for name in
            ('review.md', 'frozen-files.json', 'source-mapping.json', 'provenance.json', 'continuous-cached-route-certificate.json')},
        'rendererSHA256': H(Path(__file__)), 'referenceToolHashes': {str(path.relative_to(REPO)): H(path) for path in
            (depth_script, scene_script, pose_helper, reader, REPO/'Tools/HangboardPackages/src/hangboard_packages/cad_source.py')},
        'sceneConstruction': 'Actual USDZ world triangles receive only saved canonical quaternion/translation. Exact cached routes receive same transform. Lead anchor derives from descriptor bounds plus authored offset. Existing twelve-sided tube display tessellation uses exact radius. No invented routes, knots, support geometry or concealed connections.',
        'routeSolveReauthorCompileTestsBuildOrSimulatorRun': False, 'productionSharedOrExistingPacketMutation': False,
        'materialDisplay': 'neutral CAD only; exact descriptor selection red; no texture or runtime finish simulation',
        'runtimeVerified': False, 'currentAppFrames': 0, 'images': records}
    (OUT/'preview-provenance.json').write_text(json.dumps(provenance, indent=2)+'\n')


if __name__ == '__main__':
    main()
