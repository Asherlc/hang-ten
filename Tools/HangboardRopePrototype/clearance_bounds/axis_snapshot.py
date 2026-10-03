"""Separate immutable one-coordinate support preflight experiment."""
from armijo.snapshot import once


def collider_source(source):
    source=once(source,'    private let supportDomain:Bool','    private let supportDomain:Bool\n    private let axisPlanes:[RopeAxisSupport?]')
    source=once(source,'        supportDomain=mesh.vertices.allSatisfy','''        axisPlanes=mesh.triangles.map {RopeAxisSupport(mesh.vertices[$0.x],mesh.vertices[$0.y],mesh.vertices[$0.z])}
        supportDomain=mesh.vertices.allSatisfy''')
    source=once(source,'endInside:Bool,certifyBounds:Bool=false)',
        'endInside:Bool,certifyBounds:Bool=false,axisBounds:Bool=false)')
    source=once(source,'            if validDomain,let plane=supportPlanes[index],let bound=plane.bound(start,end),bound.lowerBound>rowRadius+1e-9 {','''            let preflight=validDomain ? (axisBounds ? axisPlanes[index]?.bound(start,end) ?? supportPlanes[index]?.bound(start,end):supportPlanes[index]?.bound(start,end)):nil
            if let bound=preflight,bound.lowerBound>rowRadius+1e-9 {''')
    source=once(source,'meritRadius:Double,certifyBounds:Bool=false)->(points:',
        'meritRadius:Double,certifyBounds:Bool=false,axisBounds:Bool=false)->(points:')
    source=once(source,'endInside:storage.inside[i+1],certifyBounds:certifyBounds)',
        'endInside:storage.inside[i+1],certifyBounds:certifyBounds,axisBounds:axisBounds)')
    return source


def solver_source(source):
    source=once(source,'    var clearanceBoundExperiment=false','    var clearanceBoundExperiment=false\n    var axisBoundExperiment=false')
    source=once(source,'certifyBounds:clearanceBoundExperiment)',
        'certifyBounds:clearanceBoundExperiment,axisBounds:axisBoundExperiment)')
    return source


def driver_source(source):
    source=source.replace('candidate.clearanceBoundExperiment=true','candidate.clearanceBoundExperiment=true;candidate.axisBoundExperiment=true')
    source=source.replace('b.clearanceBoundExperiment=true','b.clearanceBoundExperiment=true;b.axisBoundExperiment=true')
    source=once(source,'    try clearanceBoundFixtures();','    try axisBoundFixtures();try clearanceBoundFixtures();')
    source=once(source,'result["clearanceBounds"]=true','result["clearanceBounds"]=true;result["axisBounds"]=true')
    return source
