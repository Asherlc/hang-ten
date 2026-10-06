"""Opt-in native cylindrical groove guidance for visible exterior leads.

The CAD owns the finite cylinders and bore. Sections generate a seed; no path
points are supplied by an author or read from an old cache. The bounded 3D
search is followed by independent whole-solid, tube, finite traversal and
active-material reaction checks. The latter is discrete frictionless contact
feasibility at a numerical offset, not a continuous rope/safety simulation.
"""
from __future__ import annotations
import copy
import logging
_LOG=logging.getLogger(__name__)
import numpy as np
import trimesh
from scipy.optimize import minimize, nnls

PROPOSAL_MARGIN = 2e-5
CONTACT_NUMERICAL_ALLOWANCE = 1e-5
REACTION_RESIDUAL_LIMIT = 1e-5


def validate_guide_bindings(data, source):
    settings=data["ropeSolver"]["grooveGuides"]
    if not isinstance(source,dict) or settings["sourceSHA256"]!=source.get("sourceSHA256"):
        raise ValueError("native groove source binding is stale")
    features=source.get("nativeCordFeatures",{})
    poses=data["suspension"]["canonicalPoses"]
    strands={s["id"] for s in data["suspension"]["strands"]}
    if set(settings["byPoseID"])!=set(poses):
        raise ValueError("native groove selections must exactly match every pose")
    for selections in settings["byPoseID"].values():
        if set(selections)!=strands:raise ValueError("native groove selections must exactly match every lead")
        for selection in selections.values():
            for key,kind in (("feature","groove"),("boreFeature","bore")):
                feature=features.get(selection[key])
                if not isinstance(feature,dict) or feature.get("kind")!=kind or not feature.get("wallFaces"):
                    raise ValueError("native groove/bore feature has no source-bound final-solid wall")
    return features


def _frame(guide):
    origin=np.asarray(guide["origin"],float);axis=np.asarray(guide["axis"],float)
    axis=axis/np.linalg.norm(axis)
    return origin,axis


def certify_groove_traversal(path,radius,guide,exit_sign,terminal):
    """A finite inner span is required; touching the terminal is insufficient.

    The two witness sections partition the native bore-to-exit interval into
    thirds. They are validation witnesses, never constrained solver vertices.
    Convex radial bounds certify every segment between those crossings.
    """
    p=np.asarray(path,float);origin,axis=_frame(guide)
    available=float(guide["radius"])-radius
    if available<=PROPOSAL_MARGIN:raise ValueError("native groove radius cannot contain the finite cord")
    center=float((np.asarray(terminal)-origin)@axis)
    end=float(guide["axialBounds"][1 if exit_sign>0 else 0])
    if (end-center)*exit_sign<=2*radius:raise ValueError("native groove has no finite traversal interval")
    axial=(p-origin)@axis;witnesses=[]
    for fraction in (2/3,1/3):
        station=center+(end-center)*fraction;hits=[]
        for i,(a,b) in enumerate(zip(p,p[1:])):
            da,db=axial[i]-station,axial[i+1]-station
            if da*db>0 or abs(db-da)<1e-12:continue
            t=-da/(db-da);q=a+t*(b-a);radial=q-origin-axis*station
            hits.append((i+t,q,float(np.linalg.norm(radial))))
        seated=[h for h in hits if h[2]<=available+CONTACT_NUMERICAL_ALLOWANCE]
        if not seated:
            raise ValueError("native groove seating/traversal is absent or bypassed")
        at,q,radial=seated[-1]
        witnesses.append({"pathParameter":float(at),"point":q.tolist(),"radialDistance":radial,"axialStation":station})
    first,last=witnesses
    if last["pathParameter"]<=first["pathParameter"]:
        raise ValueError("native groove traversal runs away from its terminal")
    samples=[np.array(first["point"]),np.array(last["point"])]
    samples += [p[i] for i in range(int(np.floor(first["pathParameter"]))+1,int(np.ceil(last["pathParameter"]))) ]
    radial=[]
    for q in samples:
        delta=q-origin;radial.append(float(np.linalg.norm(delta-axis*(delta@axis))))
    if max(radial)>available+CONTACT_NUMERICAL_ALLOWANCE:
        raise ValueError("native groove seating leaves its finite-radius cylinder between witnesses")
    return {"status":"pass","availableCenterlineRadius":available,"witnesses":witnesses,"maximumInnerSpanRadialDistance":max(radial)}


def material_normal_cone(normal, outward_normals):
    """Return a real nonnegative witness; an empty cone supports only zero."""
    normal=np.asarray(normal,float);normals=np.asarray(outward_normals,float)
    if not len(normals):return np.zeros(0),float(np.linalg.norm(normal))
    weights,_=nnls(normals.T,normal,maxiter=max(100,20*len(normals)))
    # Some NNLS versions report zero for a 3-by-0 matrix. The independent
    # residual is the contract, including for all nonempty solves.
    return weights,float(np.linalg.norm(normal-normals.T@weights))


def incident_material_triangles(mesh,point):
    """Independent finite-facet incidence; no second closest-point query.

    Orthonormal triangle coordinates avoid the absolute tiny-triangle
    tolerances in generic closest-point routines for meter-scale CAD meshes.
    """
    point=np.asarray(point,float);tolerance=1e-8
    candidates=list(mesh.triangles_tree.intersection(np.r_[point-tolerance,point+tolerance]));incident=[]
    for face in candidates:
        a,b,c=mesh.triangles[face];ab=b-a;ac=c-a;length=np.linalg.norm(ab);normal=np.cross(ab,ac);area=np.linalg.norm(normal)
        if length<=1e-15 or area<=1e-30:continue
        normal/=area;delta=point-a
        if abs(delta@normal)>tolerance:continue
        along=ab/length;across=np.cross(normal,along);height=ac@across
        if abs(height)<=1e-15:continue
        v=float(delta@across/height);u=float((delta@along-v*(ac@along))/length)
        if min(u,v,1-u-v)>=-1e-6 and max(u,v,1-u-v)<=1+1e-6:incident.append(face)
    return incident


def facet_reconstructed_balance(mesh,required,contacts,weights):
    """Independently balance actual incident-facet forces, including fit error.

    A small per-direction cone error can be amplified by a large fitted force.
    Recompose actual material forces and retain the weighted nodal error bound.
    """
    required=np.asarray(required,float).reshape(-1,3)
    actual=np.zeros_like(required);bounds=np.zeros(len(required))
    for contact,weight in zip(contacts,weights):
        if weight<=0:continue
        incident=contact["incidentMaterialTriangles"]
        cone=np.asarray(contact["materialNormalConeWeights"],float)
        if not incident or len(cone)!=len(incident) or np.any(cone<0):
            raise ValueError("native reaction requires a nonempty nonnegative facet witness")
        direction=np.asarray(mesh.face_normals[incident]).T@cone
        mismatch=float(np.linalg.norm(np.asarray(contact["normal"])-direction))
        i,t=contact["segment"],contact["fraction"]
        for node,fraction in ((i-1,1-t),(i,t)):
            if 0<=node<len(required):
                actual[node]+=weight*fraction*direction
                bounds[node]+=weight*fraction*mismatch
    error=required-actual
    maximum=float(np.linalg.norm(error,axis=1).max()) if len(error) else 0.
    bound=float(bounds.max()) if len(bounds) else 0.
    return {"status":"pass" if maximum<=REACTION_RESIDUAL_LIMIT and bound<=REACTION_RESIDUAL_LIMIT else "fail",
            "maxFacetReconstructedNodalResidual":maximum,
            "facetReconstructedNodalResiduals":error.tolist(),
            "weightedMaterialConeErrorBounds":bounds.tolist(),
            "maximumWeightedMaterialConeErrorBound":bound}


def certify_active_reactions(mesh,path,radius):
    """Nonnegative native contact forces balance all free route nodes.

    Contacts are sampled on segments, not just vertices of a circumscribed
    polyline. Barycentric nodal forces preserve each sampled contact's point
    and moment. Inactive nearby walls cannot contribute. No groove constraint
    or virtual support appears in this fit. Unit tension is the force scale.
    """
    p=np.asarray(path,float);delta=np.diff(p,axis=0);lengths=np.linalg.norm(delta,axis=1)
    if np.any(lengths<=1e-9):raise ValueError("native reaction path contains duplicate vertices")
    dirs=delta/lengths[:,None];required=(dirs[:-1]-dirs[1:]).ravel()
    if not len(required) or np.linalg.norm(required)<REACTION_RESIDUAL_LIMIT:
        error=required.reshape(-1,3)
        maximum=float(np.linalg.norm(error,axis=1).max()) if len(error) else 0.
        return {"status":"pass","maxNodalResidual":maximum,"activeContacts":[],
                "requiredNodalReactions":error.tolist(),"nodalResiduals":error.tolist(),
                "facetReconstructedBalance":facet_reconstructed_balance(mesh,required,[],[]),
                "discreteFrictionless":True}
    points=[];maps=[]
    for i,span in enumerate(lengths):
        count=max(51,int(np.ceil(span/2e-5))+1)
        if count>20000:raise ValueError("native reaction sampling budget exceeded")
        for t in np.linspace(0,1,count):points.append(p[i]*(1-t)+p[i+1]*t);maps.append((i,float(t)))
    points=np.asarray(points)
    if len(points)>65536:raise ValueError("native reaction sampling budget exceeded")
    _,dist,_=trimesh.proximity.closest_point(mesh,points)
    active_radius=radius+PROPOSAL_MARGIN+CONTACT_NUMERICAL_ALLOWANCE
    columns=[];contacts=[]
    for si in np.where(dist<=active_radius)[0]:
        q=points[si];i,t=maps[si]
        ids=list(mesh.triangles_tree.intersection(np.r_[q-active_radius,q+active_radius]))
        feet=trimesh.triangles.closest_point(mesh.triangles[ids],np.repeat(q[None,:],len(ids),axis=0))
        distances=np.linalg.norm(q-feet,axis=1)
        for face,foot,distance in zip(ids,feet,distances):
            if distance>active_radius or distance>dist[si]+CONTACT_NUMERICAL_ALLOWANCE or distance<1e-10:continue
            normal=(q-foot)/distance
            # A nearby triangle is not necessarily the closest material
            # feature. Prove the radial direction is in the outward normal
            # cone of actual facets incident at this exact feature point.
            incident=incident_material_triangles(mesh,foot)
            if not incident:continue
            material_normals=mesh.face_normals[incident]
            cone_weights,cone_error=material_normal_cone(normal,material_normals)
            if cone_error>1e-5:continue
            column=np.zeros((len(p)-2,3))
            if i>0:column[i-1]+=(1-t)*normal
            if i+1<len(p)-1:column[i]+=t*normal
            if np.linalg.norm(column)<1e-12:continue
            columns.append(column.ravel());contacts.append({"segment":int(i),"fraction":t,"point":q.tolist(),"materialPoint":foot.tolist(),"distance":float(distance),"globalClosestDistance":float(dist[si]),"closestFeatureTieGap":float(distance-dist[si]),"normal":normal.tolist(),"triangle":int(face),"incidentMaterialTriangles":list(map(int,incident)),"materialNormalConeResidual":float(cone_error),"materialNormalConeWeights":cone_weights.tolist()})
    if not columns:raise ValueError("native reaction has no active material support")
    matrix=np.column_stack(columns);weights,residual=nnls(matrix,required,maxiter=20000)
    error=(required-matrix@weights).reshape(-1,3);maximum=float(np.linalg.norm(error,axis=1).max())
    facet_balance=facet_reconstructed_balance(mesh,required,contacts,weights)
    report={"status":"pass" if maximum<=REACTION_RESIDUAL_LIMIT and facet_balance["status"]=="pass" else "fail","maxNodalResidual":maximum,"residualNorm":float(residual),"unitTension":1.,"proposalMargin":PROPOSAL_MARGIN,"contactNumericalAllowance":CONTACT_NUMERICAL_ALLOWANCE,"closestFeatureTieAllowance":CONTACT_NUMERICAL_ALLOWANCE,"materialConeResidualLimit":1e-5,"discreteFrictionless":True,"nodalResiduals":error.tolist(),"requiredNodalReactions":required.reshape(-1,3).tolist(),"activeContacts":[dict(c,weight=float(v)) for c,v in zip(contacts,weights) if v>0],"facetReconstructedBalance":facet_balance}
    if report["status"]!="pass":
        failure=ValueError(f"native reaction requires unsupported force: radial residual {maximum:.9g}, actual facet residual {facet_balance['maxFacetReconstructedNodalResidual']:.9g}")
        failure.report=report
        raise failure
    return report



def certify_bore_entry(path,radius,bore,mouth_axis,clearance):
    p=np.asarray(path,float);origin,axis=_frame(bore);terminal=p[-1]
    axial=float((terminal-origin)@axis);radial=float(np.linalg.norm(terminal-origin-axis*axial))
    outer=float(bore["outerMouthStation"])
    if radial+radius>float(bore["radius"])+1e-8 or axial<radius+clearance-1e-8 or outer-axial<radius+clearance-1e-8:
        raise ValueError("native bore terminal lacks finite radius/end-cap entry clearance")
    outward=np.asarray(mouth_axis,float);outward/=np.linalg.norm(outward)
    if outward@axis<1-1e-8 or float((p[-2]-terminal)@outward)<=1e-8:
        raise ValueError("native bore route does not enter along the actual visible mouth axis")
    # The final segment must contain a nonzero interval wholly in the bore's
    # finite-radius eroded cross-section; no connection after the cutoff.
    values=np.linspace(0,1,129);tail=p[-2][None,:]*(1-values[:,None])+terminal[None,:]*values[:,None]
    d=tail-origin;u=d@axis;r=np.linalg.norm(d-u[:,None]*axis,axis=1)
    valid=(r+radius<=float(bore["radius"])+1e-8)&(u>=radius+clearance-1e-8)&(u<=outer)
    if not valid[-1] or valid.sum()<2:raise ValueError("native bore entry is only an endpoint touch")
    return {"status":"pass","terminal":terminal.tolist(),"insetFromActualOuterPlane":outer-axial,"radialDistance":radial,"finiteTailLength":float(np.linalg.norm(tail[np.where(valid)[0][0]]-terminal)),"cutoffPolicy":"Existing visible bore only; no hidden connection."}


def _remove_free_bends(mesh,path,radius,only_small=False):
    from native_cord_routes import checked_clearance
    p=np.asarray(path,float).copy();removed=0
    for i in range(len(p)-2,0,-1):
        a,b=p[i]-p[i-1],p[i+1]-p[i];la,lb=np.linalg.norm(a),np.linalg.norm(b)
        if min(la,lb)<1e-8:
            candidate=np.delete(p,i,axis=0)
        else:
            if only_small and np.degrees(np.arccos(np.clip(a@b/(la*lb),-1,1)))>5:continue
            _,distance,_=trimesh.proximity.closest_point(mesh,p[i:i+1])
            if distance[0]<=radius+PROPOSAL_MARGIN+CONTACT_NUMERICAL_ALLOWANCE:continue
            candidate=np.delete(p,i,axis=0)
        try:checked_clearance(mesh,np.array([p[i-1],p[i+1]]),radius+PROPOSAL_MARGIN)
        except ValueError:continue
        p=candidate;removed+=1
    return p,removed


def native_feature_plane(support,terminal,guide,bore):
    """Optional analytic search plane; never substitutes for 3D certificates."""
    go,ga=_frame(guide);bo,ba=_frame(bore);normal=np.cross(ga,ba)
    if np.linalg.norm(normal)<1e-10:return None
    normal/=np.linalg.norm(normal)
    if max(abs(normal))<1-1e-10:return None
    if any(abs(float((np.asarray(p)-bo)@normal))>1e-10 for p in (go,terminal,support)):return None
    return {"point":bo.tolist(),"normal":normal.tolist(),"fixedCoordinate":int(np.argmax(abs(normal))),"provenance":"Intersecting selected native guide/bore axes, terminal and anchor are coplanar; full 3D gates remain required."}


def unit_tension_chain_jacobian(path):
    """Derivative of incoming-minus-outgoing unit tangents at free nodes."""
    p=np.asarray(path,float);n=len(p)-2;matrix=np.zeros((3*n,3*n))
    for k,vector in enumerate(np.diff(p,axis=0)):
        length=np.linalg.norm(vector)
        if length<=1e-9:raise ValueError("material settling has duplicate route vertices")
        direction=vector/length;stiffness=(np.eye(3)-np.outer(direction,direction))/length
        for a,sa in ((k,-1),(k+1,1)):
            if not 0<a<len(p)-1:continue
            for b,sb in ((k,-1),(k+1,1)):
                if 0<b<len(p)-1:matrix[3*(a-1):3*a,3*(b-1):3*b]+=sa*sb*stiffness
    return matrix


def settle_material_forces(mesh,path,radius):
    """Bounded 3D correction of actual facet-force residual, never a waiver.

    Endpoints remain fixed. Each trial gets fresh closest-feature/cone forces
    and full 3D clearance. The 10 micrometre step bound and five-step budget
    limit numerical search; physical acceptance thresholds are unchanged.
    """
    from native_cord_routes import checked_clearance
    p=np.asarray(path,float).copy();history=[]
    if len(p)>128:raise ValueError("native guided optimization vertex budget exceeded")
    for iteration in range(6):
        clearance=checked_clearance(mesh,p,radius)
        try:
            forces=certify_active_reactions(mesh,p,radius)
            return p,{"status":"pass","iterations":iteration,"corrections":history,
                "continuousClearanceLowerBound":clearance,"reactions":forces,
                "method":"Full 3D unit-tension chain Jacobian; independently reconstructed actual facet residual; fixed endpoints; <=10 micrometre steps; <=5 corrections."}
        except ValueError as error:
            failure=getattr(error,"report",None)
            if failure is None or iteration==5:raise
            residual=np.asarray(failure["facetReconstructedBalance"]["facetReconstructedNodalResiduals"],float).ravel()
            correction=np.linalg.lstsq(unit_tension_chain_jacobian(p),-residual,rcond=1e-10)[0].reshape(-1,3)
            maximum=float(np.linalg.norm(correction,axis=1).max())
            if not np.isfinite(maximum) or maximum>1e-5:raise ValueError("native material settling correction exceeds bounded search")
            history.append({"iteration":iteration,"maxCorrectionM":maximum,"pathBefore":p.tolist(),"actualFacetResidualBefore":failure["facetReconstructedBalance"]["maxFacetReconstructedNodalResidual"]})
            p[1:-1]+=correction
            _LOG.info("Native material settling correction %d: %.9g m",iteration,maximum)
    raise AssertionError("unreachable material settling state")


def _optimize_lead(mesh,seed,radius,mouth_axis,plane=None):
    from native_cord_routes import checked_clearance,length
    seed=np.asarray(seed,float);axis=np.asarray(mouth_axis,float);axis/=np.linalg.norm(axis)
    initial_plane=copy.deepcopy(plane);native_precision=plane is not None
    if plane is not None:
        coordinate=plane["fixedCoordinate"];value=plane["point"][coordinate]
        if max(abs(seed[[0,-1],coordinate]-value))>1e-10:raise ValueError("native feature plane does not contain fixed endpoints")
        seed=seed.copy();seed[:,coordinate]=value
    seed,_=_remove_free_bends(mesh,seed,radius,only_small=True)
    feasible_seed=None
    try:
        checked_clearance(mesh,seed,radius)
        feasible_seed=seed.copy()
    except ValueError:
        pass  # Optimization may recover an initially infeasible section seed.
    reports=[]
    for phase in range(4):
        _LOG.info("Native guided lead phase %d, %d vertices",phase,len(seed))
        if len(seed)>128:raise ValueError("native guided optimization vertex budget exceeded")
        if native_precision and plane is None:
            try:
                settled,proof=settle_material_forces(mesh,seed,radius)
                return settled,{"phases":reports,"materialEquilibrium":proof,"continuousClearanceLowerBound":proof["continuousClearanceLowerBound"],"reactions":proof["reactions"],"nativeSearchPlane":initial_plane}
            except ValueError as error:
                _LOG.info("Native material settling rejected: %s",error)
        target=radius+PROPOSAL_MARGIN;last={};maps=[]
        for i,span in enumerate(np.linalg.norm(np.diff(seed,axis=0),axis=1)):
            for t in np.linspace(0,1,max(13,int(np.ceil(span/.0005))+1))[:-1]:maps.append((i,float(t)))
        maps.append((len(seed)-2,1.))
        def path(x):return np.vstack([seed[0],x.reshape(-1,3)/1000,seed[-1]])
        def objective(x):
            p=path(x);delta=np.diff(p,axis=0);ll=np.linalg.norm(delta,axis=1);directions=delta/np.maximum(ll[:,None],1e-12)
            return float(ll.sum())*1000,(directions[:-1]-directions[1:]).ravel()
        def constraints(x):
            if "x" in last and np.array_equal(last["x"],x):return last["value"],last["jacobian"]
            p=path(x);points=np.array([p[i]*(1-t)+p[i+1]*t for i,t in maps]);near,dist,_=trimesh.proximity.closest_point(mesh,points)
            signed=-trimesh.proximity.signed_distance(mesh,points);normals=(points-near)/np.maximum(dist[:,None],1e-12);normals[signed<0]*=-1
            values=np.r_[signed-target,float((p[-2]-p[-1])@axis)-1e-8]*1000
            jac=np.zeros((len(values),len(x)))
            for row,((i,t),normal) in enumerate(zip(maps,normals)):
                for k,weight in ((i,1-t),(i+1,t)):
                    if 0<k<len(p)-1:jac[row,3*(k-1):3*k]+=weight*normal
            jac[-1,-3:]=axis;last.update(x=x.copy(),value=values,jacobian=jac);return values,jac
        bounds=list(zip((seed[1:-1].ravel()-.025)*1000,(seed[1:-1].ravel()+.025)*1000))
        if plane is not None:
            for i in range(len(seed)-2):bounds[3*i+coordinate]=(value*1000,value*1000)
        # Retain the native seed's precision after releasing its plane. A loose
        # 3D stop can leave reaction residuals too large for independent gates.
        result=minimize(objective,seed[1:-1].ravel()*1000,jac=True,method="SLSQP",bounds=bounds,constraints=[{"type":"ineq","fun":lambda x:constraints(x)[0],"jac":lambda x:constraints(x)[1]}],options={"ftol":1e-9 if native_precision else 1e-6,"maxiter":200 if plane is not None else 100})
        candidate=path(result.x);candidate,removed=_remove_free_bends(mesh,candidate,radius)
        record={"phase":phase,"optimizerSuccess":bool(result.success),"optimizerMessage":str(result.message),"iterations":int(result.nit),"removedInactiveBends":removed,"length":length(candidate)};reports.append(record)
        try:
            clearance=checked_clearance(mesh,candidate,radius)
            feasible_seed=candidate.copy()
        except ValueError as error:
            # A failed SLSQP iterate can cross the solid. Re-centering bounded
            # searches on that path traps later phases inside the same wall.
            # Keep the last clearance-certified native seed; it must still pass
            # all material, groove, entry, length and tube gates before delivery.
            record["independentGateFailure"]=str(error)
            if plane is not None:
                record["nativePlaneSeedReleasedTo3D"]=True
                plane=None
            if feasible_seed is not None:
                seed=feasible_seed.copy()
            else:
                # With no certified path to preserve, retain optimizer progress
                # as a recovery start instead of repeating the same failed solve.
                # This iterate remains uncertified and cannot bypass any gate.
                seed=candidate.copy()
            _LOG.info("Native guided phase %d collision rejected: %s",phase,error)
            continue
        if plane is not None:
            # The analytic plane supplies a deterministic native seed only.
            # Every final lead is tightened and certified in full 3D, including
            # when the seed happened to satisfy a force test already.
            record["nativePlaneSeedReleasedTo3D"]=True
            plane=None;seed=candidate
            continue
        try:
            reactions=certify_active_reactions(mesh,candidate,radius)
            _LOG.info("Native guided lead certified after %d iterations",result.nit)
            return candidate,{"phases":reports,"continuousClearanceLowerBound":clearance,"reactions":reactions,"nativeSearchPlane":initial_plane}
        except ValueError as error:
            record["independentGateFailure"]=str(error);seed=candidate
            _LOG.info("Native guided phase %d rejected: %s",phase,error)
    raise ValueError(f"native guided optimization exhausted its bounded phases: {reports}")


def _seed(mesh,support,terminal,guide,exit_sign,radius,clearance):
    from native_cord_routes import NativeSection
    origin,axis=_frame(guide);center=float((terminal-origin)@axis);end=guide["axialBounds"][1 if exit_sign>0 else 0]
    station=origin+axis*(center+end)/2
    first=NativeSection.for_span(mesh,support,station,axis,radius,clearance,plane_axis=axis,path_search="aStar").route(support,station)
    normal=np.cross(axis,terminal-station)
    second=NativeSection.for_span(mesh,station,terminal,normal,radius,clearance,path_search="aStar").route(station,terminal)
    return np.vstack([first,second[1:]])


def _certify_guided_paths(mesh,full,radii,rests,features,selections,terminals,clearance):
    from native_cord_routes import checked_clearance,length
    from hangboard_packages.cord_paths import validate_cord_paths
    minimums={};ratios={};certificates={}
    for k,p in full.items():
        selection=selections[k];terminal=terminals[k]
        minimums[k]=checked_clearance(mesh,p,radii[k]);ratios[k]=length(p)/rests[k]
        certificates[k]={"seating":certify_groove_traversal(p,radii[k],features[selection["feature"]],selection["exitSign"],p[-1]),"entry":certify_bore_entry(p,radii[k],features[selection["boreFeature"]],terminal["mouthAxis"],clearance),"reactions":certify_active_reactions(mesh,p,radii[k])}
    validate_cord_paths(full,radii)
    if max(ratios.values())>1+1e-6 or abs(max(ratios.values())-1)>1e-6:raise ValueError("native guided cache does not match settled length")
    return minimums,ratios,certificates


def solve_groove_guided_routes(mesh,data,descriptor,source):
    from native_cord_routes import length
    from solve_threaded_rope import rotate_inverse
    if not mesh.is_watertight or not mesh.is_winding_consistent or mesh.volume<=0:
        raise ValueError("native guided collider must be a closed consistently outward solid")
    features=validate_guide_bindings(data,source);setup=data["suspension"];solver=data["ropeSolver"];settings=solver["grooveGuides"]
    radii={s["id"]:s["radius"] for s in setup["strands"]};rests={s["id"]:s["restLength"] for s in setup["strands"]}
    bounds=descriptor["modelBounds"];anchor=(np.array(bounds["min"])+np.array(bounds["max"]))/2;anchor[1]=bounds["max"][1];anchor+=np.array(setup["anchor"]["offsetFromBoardBounds"])
    output={};dedup={}
    for pose_id,pose in setup["canonicalPoses"].items():
        selections=settings["byPoseID"][pose_id]
        translation=np.array(pose["translation"],float)
        def support(height):
            t=translation.copy();t[1]=height;return rotate_inverse(pose["rotation"],anchor-t)
        # Physics is expressed in native coordinates. Different presentation
        # rotations may resolve to the exact same support line; reuse only
        # within this fresh invocation, never from a saved route cache.
        origin=tuple(support(0.));direction=tuple(rotate_inverse(pose["rotation"],np.array([0.,1.,0.])))
        key=(origin,direction,tuple((k,tuple(sorted(v.items()))) for k,v in sorted(selections.items())))
        if key in dedup:
            first=dedup[key];result=copy.deepcopy(output[first]);height=result["height"]
            full={k:np.vstack([support(height),p]) for k,p in result["routes"].items()}
            minimums,ratios,certificates=_certify_guided_paths(mesh,full,radii,rests,features,selections,solver["terminalsByStrandID"],solver["clearance"])
            result.update(minimumClearance=minimums,lengthRatios=ratios)
            result["nativeGrooveGuidance"].update(certificates=certificates,freshComputationReuse={"sourcePoseID":first,"nativeSupportOrigin":origin,"nativeHeightDirection":direction,"independentlyRecertified":True})
            output[pose_id]=result;continue
        height=float(anchor[1]-.75*min(rests.values()));paths={};history=[]
        for strand in sorted(radii):
            g=solver["terminalsByStrandID"][strand];selection=selections[strand];terminal=np.array(g["points"][0],float)
            paths[strand]=_seed(mesh,support(height),terminal,features[selection["feature"]],selection["exitSign"],radii[strand],solver["clearance"])
        for iteration in range(12):
            _LOG.info("Native guided pose %s settling iteration %d, height %.9f",pose_id,iteration,height)
            record={"iteration":iteration,"heightBefore":height,"leads":{}}
            for strand in sorted(paths):
                selection=selections[strand]
                plane=native_feature_plane(paths[strand][0],paths[strand][-1],features[selection["feature"]],features[selection["boreFeature"]])
                paths[strand],record["leads"][strand]=_optimize_lead(mesh,paths[strand],radii[strand],solver["terminalsByStrandID"][strand]["mouthAxis"],plane=plane)
            def ratio(candidate):
                point=support(candidate)
                return max((np.linalg.norm(point-p[1])+length(p[1:]))/rests[k] for k,p in paths.items())
            near,far=0.,-2*max(rests.values())
            if ratio(near)>1+1e-6 or ratio(far)<1:raise ValueError("native guided height cannot be bracketed")
            for _ in range(40):
                mid=(near+far)/2
                if ratio(mid)>1:far=mid
                else:near=mid
            settled=round(float((near+far)/2),9);record["heightAfter"]=settled;history.append(record)
            for k,p in paths.items():paths[k]=np.vstack([support(settled),p[1:]])
            converged=abs(settled-height)<=1e-8;height=settled
            if converged:break
        else:raise ValueError("native guided height did not converge within 12 iterations")
        routes={k:np.round(p[1:],9).tolist() for k,p in paths.items()};full={k:np.vstack([support(height),p]) for k,p in routes.items()}
        minimums,ratios,certificates=_certify_guided_paths(mesh,full,radii,rests,features,selections,solver["terminalsByStrandID"],solver["clearance"])
        output[pose_id]={"height":height,"routes":routes,"minimumClearance":minimums,"lengthRatios":ratios,"nativeGrooveGuidance":{"sourceSHA256":source["sourceSHA256"],"certificates":certificates,"settling":history,"policy":"Native-generated seeds; bounded local search; discrete frictionless feasibility only; no global minimum or safety claim."}}
        dedup[key]=pose_id
    return output
