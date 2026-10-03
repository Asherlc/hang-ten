"""Query-local union support proof cache; original per-face narrow phase."""
from armijo.snapshot import once


def collider_source(source):
    source=once(source,'    private let supportDomain:Bool','''    private let supportDomain:Bool
    private let faceGroups:[Int]
    private let planeGroups:[RopeTriangleSupport?]''')
    source=once(source,'        supportDomain=mesh.vertices.allSatisfy','''        if mesh.triangles.count==RopePlaneAtlas.faceIDs.count {
            faceGroups=RopePlaneAtlas.faceIDs
            let count=(faceGroups.max() ?? -1)+1
            var groups=Array(repeating:[SIMD3<Double>](),count:count)
            var directions=Array(repeating:SIMD3<Double>.zero,count:count)
            for i in mesh.triangles.indices {
                let face=mesh.triangles[i],a=mesh.vertices[face.x],b=mesh.vertices[face.y],c=mesh.vertices[face.z],group=faceGroups[i]
                if groups[group].isEmpty {directions[group]=simd_cross(b-a,c-a)}
                groups[group] += [a,b,c]
            }
            planeGroups=zip(directions,groups).map{RopeTriangleSupport(unionDirection:$0.0,vertices:$0.1)}
        } else {faceGroups=[];planeGroups=[]}
        supportDomain=mesh.vertices.allSatisfy''')
    source=once(source,'endInside:Bool,certifyBounds:Bool=false)',
        'endInside:Bool,certifyBounds:Bool=false,planeReuse:Bool=false)')
    source=once(source,'        var minimum=Double.infinity,prunedAny=false','''        var planeCache=RopePlaneBoundCache(start:start,end:end)
        var minimum=Double.infinity,prunedAny=false''')
    source=once(source,'            if validDomain,let plane=supportPlanes[index],let bound=plane.bound(start,end),bound.lowerBound>rowRadius+1e-9 {','''            var preflight:RopeCertifiedClearance?=nil
            if validDomain {
                if planeReuse,faceGroups.count==mesh.triangles.count {
                    let id=faceGroups[index];preflight=planeCache.value(id:id,support:planeGroups[id])
                } else {preflight=supportPlanes[index]?.bound(start,end)}
            }
            if let bound=preflight,bound.lowerBound>rowRadius+1e-9 {''')
    source=once(source,'meritRadius:Double,certifyBounds:Bool=false,freeBalls:',
        'meritRadius:Double,certifyBounds:Bool=false,planeReuse:Bool=false,freeBalls:')
    source=once(source,'endInside:storage.inside[i+1],certifyBounds:certifyBounds)',
        'endInside:storage.inside[i+1],certifyBounds:certifyBounds,planeReuse:planeReuse)')
    source+='''
extension RopeTriangleCollider {
    func planeUnionSnapshot()->[[String:Any]] {
        var vertices=Array(repeating:Set<Int>(),count:planeGroups.count)
        for i in faceGroups.indices {let f=mesh.triangles[i];vertices[faceGroups[i]].formUnion([f.x,f.y,f.z])}
        func bits(_ p:SIMD3<Double>)->[String] {[p.x,p.y,p.z].map{String($0.bitPattern,radix:16)}}
        return planeGroups.indices.map {i in
            guard let support=planeGroups[i] else {return ["group":i,"unknown":true]}
            return ["group":i,"n":bits(support.direction),"lower":String(support.lower.bitPattern,radix:16),
                "upper":String(support.upper.bitPattern,radix:16),"normUpper":String(support.normUpper.bitPattern,radix:16),
                "vertices":vertices[i].sorted().map{bits(mesh.vertices[$0])}] as [String:Any]
        }
    }
}
'''
    return source


def solver_source(source):
    source=once(source,'    var freeBallExperiment=false','    var freeBallExperiment=false\n    var planeReuseExperiment=false')
    source=once(source,'certifyBounds:clearanceBoundExperiment,freeBalls:',
        'certifyBounds:clearanceBoundExperiment,planeReuse:planeReuseExperiment,freeBalls:')
    return source


def driver_source(source):
    source=once(source,'let collider=try RopeTriangleCollider(input:input)','''let collider=try RopeTriangleCollider(input:input)
try JSONSerialization.data(withJSONObject:collider.planeUnionSnapshot(),options:[.sortedKeys]).write(to:root.appendingPathComponent("plane-unions.json"))''')
    source=once(source,'"window":[121,140],"freeBalls":true','"window":[121,140],"freeBalls":true,"planeReuse":true')
    source=once(source,'enabled:Bool,verify:Bool)throws->FreeBallWindow','enabled:Bool,verify:Bool,planes:Bool=false)throws->FreeBallWindow')
    source=once(source,'x.verifyFreeBallParity=verify','x.verifyFreeBallParity=verify;x.planeReuseExperiment=planes')
    source=once(source,'    try clearanceBoundFixtures();try freeBallFixtures()','    try unionSupportFixtures();try planeCacheFixtures();try clearanceBoundFixtures();try freeBallFixtures()')
    source=once(source,'let verified=try window(initial,enabled:true,verify:true)','let verified=try window(initial,enabled:true,verify:true,planes:true)')
    source=once(source,'let candidate=try window(initial,enabled:true,verify:false)','''let candidate=try window(initial,enabled:true,verify:false,planes:true)
    let freeBall=try window(initial,enabled:true,verify:false)
    result["freeBallControlWindow"]=freeBall.records''')
    source=once(source,'        let a:FreeBallWindow,b:FreeBallWindow','        let a:FreeBallWindow,b:FreeBallWindow,f:FreeBallWindow')
    source=once(source,'        if iteration%2==0 {a=try window(initial,enabled:false,verify:false);b=try window(initial,enabled:true,verify:false)}\n        else {b=try window(initial,enabled:true,verify:false);a=try window(initial,enabled:false,verify:false)}','''        if iteration%3==0 {a=try window(initial,enabled:false,verify:false);f=try window(initial,enabled:true,verify:false);b=try window(initial,enabled:true,verify:false,planes:true)}
        else if iteration%3==1 {b=try window(initial,enabled:true,verify:false,planes:true);f=try window(initial,enabled:true,verify:false);a=try window(initial,enabled:false,verify:false)}
        else {f=try window(initial,enabled:true,verify:false);a=try window(initial,enabled:false,verify:false);b=try window(initial,enabled:true,verify:false,planes:true)}''')
    source=once(source,'        try verifyDeterminism(a,original);try verifyDeterminism(b,candidate)','        try verifyDeterminism(a,original);try verifyDeterminism(b,candidate);try verifyDeterminism(f,freeBall)')
    source=once(source,'pairs.append(["originalSeconds":a.seconds,"candidateSeconds":b.seconds,"ratio":b.seconds/a.seconds])','pairs.append(["originalSeconds":a.seconds,"candidateSeconds":b.seconds,"freeBallSeconds":f.seconds,"ratio":b.seconds/a.seconds,"freeBallRatio":b.seconds/f.seconds])')
    source=once(source,'    guard median<=0.80 else','''    let incremental=pairs.map{$0["freeBallRatio"] as! Double}.sorted()[3];result["medianFreeBallRatio"]=incremental
    try persist(nil)
    guard median<=0.80,incremental<=0.90 else''')
    source=source.replace('fixed twenty-step median <=0.80 speed gate','fixed twenty-step total <=0.80 and incremental <=0.90 speed gates')
    return source
