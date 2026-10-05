"""Analytic regressions for optional native 3D cord shortening."""
from pathlib import Path
import sys
import numpy as np
import pytest
import trimesh

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from native_cord_routes import checked_clearance, length
from hangboard_packages.cord_paths import validate_cord_paths


def tighten(mesh, paths, radii, mouths):
    import native_cord_routes as native
    return native.tighten_native_paths(mesh, paths, radii, mouths)


def test_unobstructed_oblique_front_entry_releases_the_artificial_collar():
    mesh = trimesh.creation.box(extents=[.08, .08, .01])
    mesh.apply_translation([0, 0, -.03])
    path = np.array([[0, .10, .02], [0, 0, .02], [0, 0, 0]])
    initial = path.copy()
    paths, report = tighten(mesh, {"lead": path}, {"lead": .002}, {"lead": [0, 0, 1]})
    result = paths["lead"]
    direct = np.linalg.norm(path[0]-path[-1])
    assert length(result) == pytest.approx(direct, abs=1e-8), "unsupported free-space collar bend remains"
    assert np.array_equal(path, initial), "shortening must not mutate its certified seed"
    assert np.array_equal(result[0], initial[0]) and np.array_equal(result[-1], initial[-1])
    assert np.dot(result[-2]-result[-1], [0,0,1]) > 0
    assert checked_clearance(mesh, result, .002) >= .002-1e-5
    assert report["converged"]


def test_shortening_preserves_native_obstacle_and_other_occupied_cord():
    mesh = trimesh.creation.box(extents=[.02, .02, .02])
    path = np.array([[-.04, 0, .02], [-.025, .025, .025], [.025, .025, .025], [.04, 0, .02]])
    other = np.array([[0, -.025, .02], [0, .025, .02]])
    seed = {"lead": path, "occupied": other}
    radii = {"lead": .002, "occupied": .002}
    validate_cord_paths(seed, radii)
    paths, report = tighten(mesh, seed, radii, {"lead": [0,0,1]})
    assert length(paths["lead"]) < length(path)-.005, "safe 3D shortening was not attempted"
    assert np.max(np.abs(paths["lead"][:,1]))<.001, "the bearing chain retained its unnecessary lateral excursion"
    assert np.array_equal(paths["occupied"], other)
    assert np.dot(paths["lead"][-2]-path[-1], [0,0,1]) > 0
    for identifier, route in paths.items():
        assert checked_clearance(mesh, route, radii[identifier]) >= radii[identifier]-1e-5
    validate_cord_paths(paths, radii)


def test_shortening_never_uses_rear_entry_even_when_its_chord_is_clear():
    mesh = trimesh.creation.box(extents=[.01, .01, .01])
    mesh.apply_translation([.1, 0, 0])
    path = np.array([[0,.10,-.02], [0,.03,.01], [0,0,.01], [0,0,0]])
    paths, _ = tighten(mesh, {"lead": path}, {"lead": .002}, {"lead": [0,0,1]})
    assert length(paths["lead"]) < length(path)-.001
    assert np.dot(paths["lead"][-2]-path[-1], [0,0,1]) > 0
    assert np.array_equal(paths["lead"][0], path[0]) and np.array_equal(paths["lead"][-1], path[-1])


def test_shortening_is_deterministic_and_independent_of_mapping_insertion_order():
    mesh = trimesh.creation.box(extents=[.02,.02,.02]); mesh.apply_translation([0,0,-.1])
    routes = {"b": np.array([[.02,.1,.01],[.04,.04,.04],[.02,0,0]]),
              "a": np.array([[-.02,.1,.01],[-.04,.04,.04],[-.02,0,0]])}
    radii={identifier:.002 for identifier in routes}; axes={identifier:[0,0,1] for identifier in routes}
    first, _ = tighten(mesh, routes, radii, axes)
    second, _ = tighten(mesh, dict(reversed(list(routes.items()))), radii, axes)
    assert all(np.array_equal(first[key], second[key]) for key in routes)
    assert sum(map(length, first.values())) < sum(map(length, routes.values()))-.01


def test_optional_tightening_resettles_height_from_generated_seed_not_authored_cache(monkeypatch):
    import native_cord_routes as native
    mesh = trimesh.creation.box(extents=[.08,.04,.01]); mesh.apply_translation([0,0,-.03])
    descriptor={"modelBounds":{"min":mesh.bounds[0].tolist(),"max":mesh.bounds[1].tolist()}}
    data={"suspension":{
        "strands":[{"id":"lead","kind":"lead","radius":.002,"restLength":.25}],
        "anchor":{"offsetFromBoardBounds":[0,.1,.05]},
        "canonicalPoses":{"front":{"rotation":[0,0,0,1],"translation":[0,-.1,0],
            "wrappedRoutes":{"lead":[[999,999,999]]}}}},
        "ropeSolver":{"tightening":"coupled3D","clearance":.0002,"sectionPlane":"anchor",
            "terminalsByStrandID":{"lead":{"points":[[0,0,0]],"mouthAxis":[0,0,1]}}}}
    generated={"front":{"height":-.1,"routes":{"lead":[[0,0,.02],[0,0,0]]}}}
    calls=[]
    def seed(*args, **kwargs):
        calls.append(1)
        return generated
    # The synthetic native seed isolates height/rounding integration from the
    # already tested section search. Deliberately hostile authored caches must
    # never participate in the tightening objective or its initialization.
    monkeypatch.setattr(native, "_solve_native_routes", seed)
    result=native.solve_native_routes(mesh,data,descriptor)["front"]
    support=np.array([0,.12-result["height"],.02])
    full=np.vstack([support,result["routes"]["lead"]])
    assert length(full)==pytest.approx(.25,abs=2e-8), "tightened route did not re-settle declared length"
    assert result["height"]==pytest.approx(.12-np.sqrt(.25**2-.02**2),abs=2e-8)
    assert len(calls)==1
    assert result["coupledTightening"]["converged"]
    assert generated["front"]["height"]==-.1
    assert checked_clearance(mesh,full,.002)>=.002-1e-5


def test_tightening_sweep_budget_exhaustion_fails_closed():
    from native_cord_routes import tighten_native_paths
    mesh=trimesh.creation.box(extents=[.02,.02,.02]); mesh.apply_translation([0,0,-.1])
    path=np.array([[0,.1,.02],[.04,.05,.05],[0,0,0]])
    with pytest.raises(ValueError,match="did not converge within 1 sweeps"):
        tighten_native_paths(mesh,{"lead":path},{"lead":.002},{"lead":[0,0,1]},max_sweeps=1)


@pytest.mark.parametrize("invalid", [None, True, 1, "unrecognized", {}, []])
def test_absent_option_preserves_seed_exactly_and_invalid_option_fails(monkeypatch, invalid):
    import native_cord_routes as native
    data={"suspension":{"strands":[],"canonicalPoses":{}},"ropeSolver":{}}
    seed={"sentinel":{"routes":[1,2,3]}}
    monkeypatch.setattr(native,"_solve_native_routes",lambda *args,**kwargs:seed)
    assert native.solve_native_routes(None,data,{}) is seed
    data["ropeSolver"]["tightening"]=invalid
    with pytest.raises(ValueError,match="tightening"):
        native.solve_native_routes(None,data,{})


def test_dense_native_samples_do_not_pin_a_clear_lateral_bow():
    mesh=trimesh.creation.box(extents=[.02,.02,.02]); mesh.apply_translation([0,0,-.1])
    t=np.linspace(0,1,201)
    path=np.column_stack([.001*np.sin(np.pi*t), .1*(1-t), .01*(1-t)])
    paths,_=tighten(mesh,{"lead":path},{"lead":.002},{"lead":[0,0,1]})
    assert length(paths["lead"])==pytest.approx(np.linalg.norm(path[0]-path[-1]),abs=1e-8)
    assert np.max(np.abs(paths["lead"][:,0]))<1e-8, "tessellation-density froze a free-space lateral bow"


def test_small_certified_bearing_motion_is_not_misreported_as_convergence():
    mesh=trimesh.creation.box(extents=[.0002,.0379,.1]); mesh.apply_translation([0,.00895,0])
    path=np.array([[-.2,0,0],[0,.03,0],[.2,0,0]])
    paths,_=tighten(mesh,{"lead":path},{"lead":.002},{"lead":[0,1,0]})
    assert length(paths["lead"]) < length(path)-1e-5
    assert checked_clearance(mesh,paths["lead"],.002)>=.002-1e-5


def test_shortening_does_not_spend_final_certificate_numerical_tolerance():
    mesh=trimesh.creation.box(extents=[.0002,.0379,.1]); mesh.apply_translation([0,.00895,0])
    path=np.array([[-.2,0,0],[0,.03,0],[.2,0,0]])
    paths,_=tighten(mesh,{"lead":path},{"lead":.002},{"lead":[0,1,0]})
    minimum=checked_clearance(mesh,paths["lead"],.00201)
    assert minimum>=.002, "optimization spent the final gate's10micrometre tolerance instead of reserving rounding room"


def test_aperture_constraint_does_not_pin_an_unsupported_free_space_knee():
    from shapely.geometry import Point,box
    from shapely.ops import triangulate
    profile=box(-.06,-.03,.06,.03).difference(Point(0,0).buffer(.003,quad_segs=8))
    vertices,faces=[],[]
    for triangle in triangulate(profile):
        if profile.covers(triangle):
            face=[]
            for point in list(triangle.exterior.coords)[:3]:
                if point not in vertices:vertices.append(point)
                face.append(vertices.index(point))
            faces.append(face)
    mesh=trimesh.creation.extrude_triangulation(vertices,faces,.01)
    mesh.apply_translation([0,0,-.01])
    initial=np.array([[-.05,0,.025],[0,0,.025],[0,0,0]])
    paths,report=tighten(mesh,{"lead":initial},{"lead":.002},{"lead":[0,0,1]})
    path=paths["lead"]
    # Movement of the one old collar vertex can stall because its entire last
    # segment is aperture-constrained. A local corner cut introduces the missing
    # freedom without pinning a new point; it must be searched before stopping.
    for index in range(1,len(path)-1):
        a,b,c=path[index-1:index+2];u=b-a;v=c-b
        trim=min(.0005,.1*np.linalg.norm(u),.1*np.linalg.norm(v))
        first=b-trim*u/np.linalg.norm(u);last=b+trim*v/np.linalg.norm(v)
        gain=2*trim-np.linalg.norm(last-first)
        if gain<=report["minimumAcceptedGain"]:continue
        candidate=np.vstack([path[:index],first,last,path[index+1:]])
        try:
            checked_clearance(mesh,[first,last],.002)
            validate_cord_paths({"lead":candidate},{"lead":.002})
        except ValueError:continue
        pytest.fail(f"unsupported aperture knee still permits {gain*1000:.6f} mm shortening")


@pytest.mark.parametrize("budget,expected", [({"max_vertices":3},"vertex budget"),({"max_checks":1},"candidate-check budget")])
def test_tightening_resource_limits_fail_closed(budget,expected):
    from native_cord_routes import tighten_native_paths
    mesh=trimesh.creation.box(extents=[.02,.02,.02])
    path=np.array([[-.04,0,0],[-.03,0,.03],[.03,0,.03],[.04,0,0]])
    with pytest.raises(ValueError,match=expected):
        tighten_native_paths(mesh,{"lead":path},{"lead":.002},{"lead":[0,0,1]},**budget)


def test_proposal_margin_does_not_freeze_a_remote_bend_due_to_unchanged_pair():
    mesh=trimesh.creation.box(extents=[.02,.02,.02]);mesh.apply_translation([0,0,-.1])
    routes={"a":np.array([[0,.1,.01],[0,0,0]]),
            "b":np.array([[.004001,.1,.01],[.004001,0,0]]),
            "c":np.array([[.1,.1,.01],[.14,.05,.04],[.1,0,0]])}
    radii={key:.002 for key in routes};axes={key:[0,0,1] for key in routes}
    validate_cord_paths(routes,radii)
    paths,_=tighten(mesh,routes,radii,axes)
    assert length(paths["c"])==pytest.approx(np.linalg.norm(routes["c"][0]-routes["c"][-1]),abs=1e-8)
    assert np.array_equal(paths["a"],routes["a"]) and np.array_equal(paths["b"],routes["b"])


def test_rounding_room_does_not_pin_an_unchanged_segment_of_the_moving_strand():
    mesh=trimesh.creation.box(extents=[.02,.02,.02]);mesh.apply_translation([0,0,-.1])
    routes={"a":np.array([[-.05,.1,.01],[-.05,0,.01],[.05,0,.01],[.08,-.04,.04],[.05,-.1,0]]),
            "b":np.array([[-.045999,.1,.01],[-.045999,.06,.006]])}
    radii={key:.002 for key in routes};axes={key:[0,0,1] for key in routes}
    paths,_=tighten(mesh,routes,radii,axes)
    assert length(paths["a"])<length(routes["a"])-.02
    validate_cord_paths(paths,radii)


def test_submicron_display_shortening_is_not_chased_as_visible_improvement():
    mesh=trimesh.creation.box(extents=[.02,.02,.02]);mesh.apply_translation([0,0,-.1])
    path=np.array([[0,.1,.01],[.00015,.05,.005],[0,0,0]])
    gain=length(path)-np.linalg.norm(path[0]-path[-1])
    assert 1e-7<gain<1e-6
    paths,report=tighten(mesh,{"lead":path},{"lead":.002},{"lead":[0,0,1]})
    assert np.array_equal(paths["lead"],path)
    assert report["minimumAcceptedGain"]==1e-6
    assert report["acceptedMoves"]==0


@pytest.mark.parametrize("tilt", [0, 15])
def test_separate_rim_and_aperture_bearings_can_slide_without_pinning_each_other(tilt):
    from shapely.geometry import Point,box
    from shapely.ops import triangulate
    from native_cord_routes import tighten_native_paths
    profile=box(-.06,-.03,.06,.03).difference(Point(-.026,0).buffer(.003,quad_segs=8))
    vertices,faces=[],[]
    for triangle in triangulate(profile):
        if profile.covers(triangle):
            face=[]
            for point in list(triangle.exterior.coords)[:3]:
                if point not in vertices:vertices.append(point)
                face.append(vertices.index(point))
            faces.append(face)
    mesh=trimesh.creation.extrude_triangulation(vertices,faces,.01);mesh.apply_translation([0,0,-.005])
    angle=np.linspace(0,np.pi/2,25)
    rim=np.column_stack([.06+.0022*np.cos(angle),np.full(25,-.02),.005+.0022*np.sin(angle)])
    seed=np.vstack([[.15,0,-.03],rim,[-.026,0,.0072],[-.026,0,.005]])
    transform=trimesh.transformations.rotation_matrix(np.radians(tilt),[1,0,0])
    mesh.apply_transform(transform);seed=trimesh.transform_points(seed,transform)
    axis=transform[:3,:3]@np.array([0,0,1])
    paths,report=tighten_native_paths(mesh,{"lead":seed},{"lead":.002},{"lead":axis},max_checks=3000)
    local=trimesh.transform_points(paths["lead"],np.linalg.inv(transform))
    assert np.max(np.abs(local[:,1]))<.001, "the aperture still pins the separate rim bearing sideways"
    assert checked_clearance(mesh,paths["lead"],.002)>=.002-1e-5
    assert report["candidateChecks"]<=3000


def test_native_tangent_proposal_lifts_and_slides_when_axis_motion_clips_wood():
    import native_cord_routes as native
    mesh=trimesh.creation.box(extents=[.1,.1,.01])
    transform=trimesh.transformations.rotation_matrix(np.radians(15),[1,0,0])
    mesh.apply_transform(transform)
    points=trimesh.transform_points(np.array([[-.001,0,.00702],[.001,0,.00702]]),transform)
    sideways=np.array([0,.001,0])
    with pytest.raises(ValueError,match="collision"):
        checked_clearance(mesh,points+sideways,.00202)
    desired=np.array([0,.001,-.0002])
    steps=native.native_slide_steps(mesh,points,desired,.002)
    # This is a direction-proposal test: every actual accepted path still has
    # its true polyline objective and complete solid/tube certificates checked.
    feasible=[]
    for step in steps:
        if step[1]<=.0005 or step[2]<=0 or step@np.array([0,-1,1])>=0:continue
        try:checked_clearance(mesh,points+step,.00202)
        except ValueError:continue
        feasible.append(step)
    assert feasible, "no native-normal-derived coupled lift-and-slide proposal"
