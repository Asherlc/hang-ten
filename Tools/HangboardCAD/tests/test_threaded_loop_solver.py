"""Acceptance of fixed-length, collision-free single-loop solutions."""
import importlib.util
from pathlib import Path

import numpy as np
import pytest
trimesh = pytest.importorskip('trimesh')
pytest.importorskip('shapely')

spec = importlib.util.spec_from_file_location('threaded_rope', Path(__file__).resolve().parents[1] / 'solve_threaded_rope.py')
solver = importlib.util.module_from_spec(spec)
spec.loader.exec_module(solver)


def fixture():
    path = [[-.1, .1, 0], [-.1, -.1, 0], [.1, -.1, 0], [.1, .1, 0]]
    setup = {
        'type': 'threadedLoopCord',
        'passages': {'left': [{'id': name, 'pointInModel': point} for name, point in zip(['a', 'b'], [path[0], path[-1]])], 'right': []},
        'branches': [{'id': 'loop', 'passageIDs': ['a', 'b'], 'radius': .002, 'restLength': 1.1}],
        'internalLoop': {'clearance': .0001, 'channelPointsByBranchID': {'loop': path}, 'channelLengthByBranchID': {'loop': .6}},
        'anchor': {'offsetFromBoardBounds': [0, .2, 0]},
        'canonicalPoses': {'primary': {'translation': [0, 0, 0], 'rotation': [0, 0, 0, 1]}},
    }
    mesh = trimesh.creation.box(extents=[.1, .1, .1])
    bounds = {'modelBounds': {'min': [-.05, -.05, -.05], 'max': [.05, .05, .05]}}
    return mesh, setup, bounds


def test_settled_loop_uses_full_native_channel_length():
    mesh, setup, bounds = fixture()
    result = solver.solve_package('fixture', mesh, {'suspension': setup}, bounds)['primary']
    support_y = .25 - result['height']
    required = .6 + 2 * np.hypot(.1, support_y - .1)
    assert required == pytest.approx(1.1, abs=1e-8)
    assert result['height'] < 0
    assert result['contacts'] == {'a': [[-.1, .1, 0]], 'b': [[.1, .1, 0]]}


def test_single_loop_rejects_a_spine_crossing_the_solid():
    mesh, setup, bounds = fixture()
    points = [[-.1, .1, 0], [0, 0, 0], [.1, .1, 0]]
    setup['internalLoop']['channelPointsByBranchID']['loop'] = points
    setup['internalLoop']['channelLengthByBranchID']['loop'] = sum(np.linalg.norm(np.array(b)-a) for a,b in zip(points,points[1:]))
    with pytest.raises(ValueError, match='collides'):
        solver.solve_package('fixture', mesh, {'suspension': setup}, bounds)


def test_single_loop_rejects_a_short_loop():
    mesh, setup, bounds = fixture()
    setup['branches'][0]['restLength'] = .8
    with pytest.raises(ValueError, match='bracket'):
        solver.solve_package('fixture', mesh, {'suspension': setup}, bounds)
