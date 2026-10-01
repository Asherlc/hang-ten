"""Exterior routes must follow the actual surface, without inventing a bore."""
import importlib.util
from pathlib import Path
import pytest

np = pytest.importorskip("numpy")
trimesh = pytest.importorskip("trimesh")
pytest.importorskip("shapely")

SPEC=importlib.util.spec_from_file_location('exterior_rope',Path(__file__).parents[1]/'solve_exterior_rope.py')

def solver():
    assert SPEC is not None
    module=importlib.util.module_from_spec(SPEC)
    SPEC.loader.exec_module(module)
    return module

def test_loaded_route_seats_on_real_box_instead_of_inflated_bounds():
    mesh=trimesh.creation.box(extents=[1,1,1])
    route=solver().solve_route(mesh,[0,2,0],[0,-2,0],0.1,[0,0,1])
    assert np.allclose(route[0],[0,2,0])
    assert np.allclose(route[-1],[0,-2,0])
    samples=np.vstack([np.linspace(a,b,101) for a,b in zip(route,route[1:])])
    clearance=-trimesh.proximity.signed_distance(mesh,samples)
    assert clearance.min()>=0.1-1e-5
    assert clearance.min()<=0.1005
    assert np.linalg.norm(np.diff(route,axis=0),axis=1).sum()>4

def test_clear_direct_lead_stays_straight():
    mesh=trimesh.creation.box(extents=[1,1,1])
    route=solver().solve_route(mesh,[0,2,0],[0,1,0],0.1,[0,0,1])
    assert np.asarray(route).shape==(2,3)

def test_wood_endpoint_does_not_author_a_hidden_connection():
    mesh=trimesh.creation.box(extents=[1,1,1])
    with pytest.raises(ValueError,match='endpoint'):
        solver().solve_route(mesh,[0,2,0],[0,0,0],0.1,[0,0,1])

def test_evidenced_front_entry_is_preserved_when_rear_is_shorter():
    mesh=trimesh.creation.annulus(r_min=0.3,r_max=0.5,height=1,sections=32)
    route=solver().solve_route(mesh,[0,1.2,-0.3],[0,0,0],0.05,[0,0,1],approach_point=[0,0,1])
    assert route[-2,2]>0
    samples=np.vstack([np.linspace(a,b,101) for a,b in zip(route,route[1:])])
    assert (-trimesh.proximity.signed_distance(mesh,samples)).min()>=0.05-1e-5

def test_empty_section_cannot_skip_full_surface_clearance():
    mesh=trimesh.creation.box(extents=[1,1,1])
    with pytest.raises(ValueError,match='full-surface clearance'):
        solver().solve_route(mesh,[-2,0,0.55],[2,0,0.55],0.1,[0,1,0])

@pytest.mark.parametrize('approach',[[float('nan'),0,0],[3,1,1],[2,1,1]])
def test_empty_section_still_validates_evidenced_approach(approach):
    mesh=trimesh.creation.box(extents=[1,1,1])
    with pytest.raises(ValueError,match='approach'):
        solver().solve_route(mesh,[2,2,0],[2,1,0],0.1,[0,0,1],approach_point=approach)


def test_clearance_between_samples_is_not_silently_accepted():
    validate_route_clearance=solver().validate_route_clearance
    mesh=trimesh.creation.box(extents=[.00002,1,1])
    route=np.array([[-.00025,0,0],[.00025,0,0]])
    # Both endpoints clear the wood; the segment passes through it.
    with pytest.raises(ValueError,match='clearance'):
        validate_route_clearance(mesh,route,.0001)


def test_whole_segment_clearance_accepts_a_seated_tangent():
    validate_route_clearance=solver().validate_route_clearance
    mesh=trimesh.creation.box(extents=[1,1,1])
    route=np.array([[-2,.6001,0],[2,.6001,0]])
    assert validate_route_clearance(mesh,route,.1)>=.1-1e-5


def test_joint_routes_avoid_independently_overlapping_leads():
    module=solver()
    mesh=trimesh.creation.box(extents=[1,1,1])
    anchor=[0,2,0]
    endpoints=[[0,-.8,0],[0,-1.1,0]]
    approaches=[[0,-.8,.6],[0,-1.1,.6]]
    routes=module.solve_pair(mesh,anchor,endpoints,.02,approaches)
    assert module.pair_clearance(*routes, knot_radius=4*.02)>=.041
    for route,end,guide in zip(routes,endpoints,approaches):
        assert np.dot(route[-2]-end,np.asarray(guide)-end)>0
        assert module.validate_route_clearance(mesh,route,.02)>=.02-1e-5


def test_separate_units_do_not_share_the_anchor_clearance_exception():
    first=[[0,2,0],[0,0,0]]
    second=[[1,2,0],[-1,0,0]]
    assert solver().pair_clearance(first,second,shared_anchor=False)==pytest.approx(0)


def test_coincident_initial_rays_are_not_reported_as_clear():
    assert solver().pair_clearance([[0,2,0],[0,0,0]],[[0,2,0],[0,-1,0]])==0


def test_thin_cord_embedded_endpoint_is_rejected():
    mesh = trimesh.creation.box(extents=[1,1,1])
    with pytest.raises(ValueError, match="endpoint"):
        solver().solve_route(mesh, [0,2,0], [0,.5-1e-6,0], 1e-6, [0,0,1])


def test_nearly_parallel_first_segments_are_checked_outside_knot():
    first = [[0,0,0], [0,1,0]]
    second = [[0,0,0], [.0001,1,0]]
    assert solver().pair_clearance(first, second, knot_radius=.008) < 1e-6


def test_endpoint_tolerance_never_admits_negative_distance(monkeypatch):
    mesh = trimesh.creation.box(extents=[1,1,1])
    # Isolate the endpoint gate from later planar/path rejection.
    monkeypatch.setattr(trimesh.proximity, "signed_distance", lambda mesh, points: np.asarray([-2, 1e-6]))
    def unexpected_section(**kwargs):
        raise AssertionError("embedded endpoint reached section solving")
    monkeypatch.setattr(mesh, "section", unexpected_section)
    with pytest.raises(ValueError, match="endpoint"):
        solver().solve_route(mesh, [0,2,0], [0,.5-1e-6,0], 1e-6, [0,0,1])
