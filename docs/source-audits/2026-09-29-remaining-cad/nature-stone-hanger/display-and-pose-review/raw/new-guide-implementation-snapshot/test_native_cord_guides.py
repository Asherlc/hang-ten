"""Negative contracts for opt-in native groove guidance."""
from pathlib import Path
import sys
import numpy as np
import pytest
import trimesh
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from native_cord_guides import certify_groove_traversal, certify_active_reactions, validate_guide_bindings

GUIDE={"origin":[0,0,0],"axis":[0,0,1],"radius":.00175,"axialBounds":[-.02,.02],"wallFaces":[1],"kind":"groove"}

def test_a_collision_clear_side_bypass_is_not_groove_seating():
    path=np.array([[.003,0,.03],[.003,0,.005],[0,0,0]])
    with pytest.raises(ValueError,match="seating"):
        certify_groove_traversal(path,.0015,GUIDE,1,np.zeros(3))

def test_touching_only_the_groove_endpoint_is_not_traversal():
    path=np.array([[.02,.02,0],[0,0,0]])
    with pytest.raises(ValueError,match="traversal"):
        certify_groove_traversal(path,.0015,GUIDE,1,np.zeros(3))

def test_finite_inside_span_passes_and_undersize_groove_fails():
    path=np.array([[.0001,0,.03],[.0001,0,.001],[0,0,0]])
    assert certify_groove_traversal(path,.0015,GUIDE,1,np.zeros(3))["status"]=="pass"
    with pytest.raises(ValueError,match="radius"):
        certify_groove_traversal(path,.002,GUIDE,1,np.zeros(3))

def test_inactive_material_cannot_support_a_free_knee():
    mesh=trimesh.creation.box(extents=[.02,.02,.02]);mesh.apply_translation([.03,0,0])
    path=np.array([[0,-.02,0],[-.003,0,0],[0,.02,0]])
    with pytest.raises(ValueError,match="reaction"):
        certify_active_reactions(mesh,path,.0015)

def test_open_side_wall_cannot_pull_rope_toward_it():
    mesh=trimesh.creation.box(extents=[.02,.1,.1]);mesh.apply_translation([.01,0,0])
    # Wall outward normal is -X; this inward knee requires +X.
    path=np.array([[-.00152,-.01,0],[-.00151,0,0],[-.00152,.01,0]])
    with pytest.raises(ValueError,match="reaction"):
        certify_active_reactions(mesh,path,.0015)

def test_source_and_feature_bindings_fail_closed():
    data={"ropeSolver":{"grooveGuides":{"sourceSHA256":"a"*64,"byPoseID":{"front":{"lead":{"feature":"g","boreFeature":"b","exitSign":1}}}}},"suspension":{"canonicalPoses":{"front":{}},"strands":[{"id":"lead","kind":"lead"}]}}
    source={"sourceSHA256":"b"*64,"nativeCordFeatures":{}}
    with pytest.raises(ValueError,match="source"):
        validate_guide_bindings(data,source)
    source["sourceSHA256"]="a"*64
    with pytest.raises(ValueError,match="feature"):
        validate_guide_bindings(data,source)

def test_default_native_routes_do_not_read_guide_metadata(monkeypatch):
    import native_cord_routes as routes
    sentinel={"default":"unchanged"}
    monkeypatch.setattr(routes,"_solve_native_seed",lambda *a,**k:sentinel)
    data={"ropeSolver":{},"suspension":{"canonicalPoses":{},"strands":[]}}
    assert routes.solve_native_routes(None,data,{}) is sentinel


def test_real_native_nearby_triangle_vectors_cannot_supply_tangential_force():
    import json
    from native_cord_guides import material_normal_cone
    fixture=json.loads((Path(__file__).parent/"fixtures/native_groove_material_normals.json").read_text())
    for case in fixture["cases"]:
        _,bad=material_normal_cone(case["rejectedRadialDirection"],case["outwardNormals"])
        assert bad>.04, "nearby triangle radial vector was misclassified as material support"
        for actual in case["outwardNormals"]:
            _,good=material_normal_cone(actual,case["outwardNormals"])
            assert good<1e-10


def test_empty_material_cone_cannot_support_nonzero_force():
    from native_cord_guides import material_normal_cone
    weights,residual=material_normal_cone([1,0,0],[])
    assert len(weights)==0 and residual==pytest.approx(1.)


def test_bore_entry_requires_finite_inset_and_respects_native_cutoff():
    from native_cord_guides import certify_bore_entry
    bore={"origin":[-.047,-.0024,0],"axis":[-1,0,0],"radius":.002,"outerMouthStation":.0055}
    path=np.array([[-.055,-.0024,0],[-.0525,-.0024,0],[-.04975,-.0024,0]])
    result=certify_bore_entry(path,.0015,bore,[-1,0,0],.0002)
    assert result["insetFromActualOuterPlane"]==pytest.approx(.00275)
    assert result["finiteTailLength"]>0
    for endpoint in ([-.0525,-.0024,0],[-.0475,-.0024,0],[-.04975,-.001,0]):
        rejected=path.copy();rejected[-1]=endpoint
        with pytest.raises(ValueError,match="finite radius/end-cap"):
            certify_bore_entry(rejected,.0015,bore,[-1,0,0],.0002)


def test_facet_reconstructed_balance_rejects_amplified_direction_error():
    from native_cord_guides import facet_reconstructed_balance
    mesh=trimesh.creation.box()
    face=int(np.argmax(mesh.face_normals[:,0]))
    contact={"segment":0,"fraction":1.,"normal":[1.,5e-6,0.],
             "incidentMaterialTriangles":[face],"materialNormalConeWeights":[1.]}
    required=np.array([[100.,.0005,0.]])
    result=facet_reconstructed_balance(mesh,required,[contact],[100.])
    assert result["maxFacetReconstructedNodalResidual"]==pytest.approx(.0005)
    assert result["maximumWeightedMaterialConeErrorBound"]==pytest.approx(.0005)
    assert result["status"]=="fail"
    with pytest.raises(ValueError,match="nonempty"):
        facet_reconstructed_balance(mesh,required,[dict(contact,incidentMaterialTriangles=[],materialNormalConeWeights=[])],[100.])


def test_longitudinal_vertical_seat_rejects_old_transverse_route():
    # Runtime Y is native Z: the new vertical guide is not the old depth-axis
    # adjustment notch. Exercise both physically upward canonical orientations.
    guide={**GUIDE,"axis":[0,1,0],"axialBounds":[-.05,.05]}
    for sign in (-1,1):
        seated=np.array([[.0001,sign*.06,0],[.0001,sign*.001,0],[0,0,0]])
        assert certify_groove_traversal(seated,.0015,guide,sign,np.zeros(3))["status"]=="pass"
        old_transverse=np.array([[.0001,0,.025],[.0001,0,.001],[0,0,0]])
        with pytest.raises(ValueError,match="traversal"):
            certify_groove_traversal(old_transverse,.0015,guide,sign,np.zeros(3))


def test_native_search_plane_requires_both_axes_anchor_and_terminal():
    from native_cord_guides import native_feature_plane
    guide={"origin":[-.0525,-.055,0],"axis":[0,1,0]}
    bore={"origin":[-.047,-.0024,0],"axis":[-1,0,0]}
    plane=native_feature_plane([0,.09,0],[-.04975,-.0024,0],guide,bore)
    assert plane["fixedCoordinate"]==2 and abs(plane["normal"][2])==1
    assert native_feature_plane([0,.09,.001],[-.04975,-.0024,0],guide,bore) is None
    assert native_feature_plane([0,.09,0],[-.04975,-.0024,.001],guide,bore) is None
    assert native_feature_plane([0,.09,0],[-.04975,-.0024,0],{**guide,"origin":[-.0525,-.055,.001]},bore) is None
    assert native_feature_plane([0,.09,0],[-.04975,-.0024,0],guide,{**bore,"axis":[0,1,0]}) is None



def test_unit_tension_jacobian_matches_independent_finite_difference():
    from native_cord_guides import unit_tension_chain_jacobian
    path=np.array([[0,.1,0],[.05,.05,.001],[.051,.002,0],[.049,0,0]])
    def forces(p):
        directions=np.diff(p,axis=0);directions/=np.linalg.norm(directions,axis=1)[:,None]
        return (directions[:-1]-directions[1:]).ravel()
    numerical=np.zeros((6,6));epsilon=1e-8
    for column in range(6):
        a=path.copy();b=path.copy();a[1+column//3,column%3]+=epsilon;b[1+column//3,column%3]-=epsilon
        numerical[:,column]=(forces(a)-forces(b))/(2*epsilon)
    np.testing.assert_allclose(unit_tension_chain_jacobian(path),numerical,rtol=1e-7,atol=1e-6)


def test_material_settling_cannot_accept_missing_support_or_collision(monkeypatch):
    import native_cord_guides as module
    import native_cord_routes
    path=np.array([[0,.1,0],[.05,.05,0],[.05,0,0]])
    monkeypatch.setattr(native_cord_routes,"checked_clearance",lambda *a:.002)
    def unsupported(*a):raise ValueError("no active material support")
    monkeypatch.setattr(module,"certify_active_reactions",unsupported)
    with pytest.raises(ValueError,match="no active"):module.settle_material_forces(None,path,.0015)
    def collision(*a):raise ValueError("native solid collision")
    monkeypatch.setattr(native_cord_routes,"checked_clearance",collision)
    with pytest.raises(ValueError,match="collision"):module.settle_material_forces(None,path,.0015)


@pytest.mark.parametrize("depth_offset,expected_frames",[(0.,2),(.01,4)])
def test_native_physics_reuse_recertifies_every_presentation(monkeypatch,depth_offset,expected_frames):
    import native_cord_guides as module
    poses={"a":{"rotation":[0,0,0,1],"translation":[0,0,0]},"b":{"rotation":[0,1,0,0],"translation":[0,0,0]},"c":{"rotation":[1,0,0,0],"translation":[0,0,0]},"d":{"rotation":[0,0,1,0],"translation":[0,0,0]}}
    features={};terminals={};selections={};calls=[]
    for side,sign in (("left",-1),("right",1)):
        features[side+"Guide"]={"origin":[sign*.05,-.05,0],"axis":[0,1,0]}
        features[side+"Bore"]={"origin":[sign*.05,0,0],"axis":[sign,0,0]}
        terminals[side]={"points":[[sign*.05,0,0]],"mouthAxis":[sign,0,0]}
    for name in poses:
        selections[name]={side:{"feature":side+"Guide","boreFeature":side+"Bore","exitSign":1 if name in ('a','b') else -1} for side in ('left','right')}
    data={"suspension":{"strands":[{"id":side,"radius":.0015,"restLength":.12} for side in ('left','right')],"anchor":{"offsetFromBoardBounds":[0,.025,depth_offset]},"canonicalPoses":poses},"ropeSolver":{"clearance":.0002,"terminalsByStrandID":terminals,"grooveGuides":{"byPoseID":selections}}}
    monkeypatch.setattr(module,"validate_guide_bindings",lambda *a:features)
    monkeypatch.setattr(module,"_seed",lambda mesh,support,terminal,*a:np.vstack([support,terminal]))
    monkeypatch.setattr(module,"_optimize_lead",lambda mesh,path,*a,**kw:(path,{"testStub":True}))
    def certify(mesh,full,*args):
        calls.append({k:v.copy() for k,v in full.items()})
        return {k:.002 for k in full},{k:1. for k in full},{k:{"status":"pass"} for k in full}
    monkeypatch.setattr(module,"_certify_guided_paths",certify)
    descriptor={"modelBounds":{"min":[-.05,-.05,-.01],"max":[.05,.05,.01]}}
    result=module.solve_groove_guided_routes(trimesh.creation.box(),data,descriptor,{"sourceSHA256":"test"})
    assert len(calls)==len(poses)  # every copied output is independently certified
    unique=[k for k,v in result.items() if 'freshComputationReuse' not in v['nativeGrooveGuidance']]
    assert len(unique)==expected_frames
    if depth_offset==0:
        assert result['b']['nativeGrooveGuidance']['freshComputationReuse']['sourcePoseID']=='a'
        assert result['d']['nativeGrooveGuidance']['freshComputationReuse']['sourcePoseID']=='c'
