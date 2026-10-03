"""Opt-in serial corpus instrumentation; no timing-gate retry."""
from pathlib import Path
from armijo.snapshot import once


def collider_source(source):
    source=once(source,'        let low=simd_min(start,end),high=simd_max(start,end)\n        let rowSquare=',
        '        let traversalTimer=RopeRegionProfile.begin()\n        let low=simd_min(start,end),high=simd_max(start,end)\n        let rowSquare=')
    source=once(source,'        for (index,mask) in faces.sorted(by:{$0.0<$1.0}) {',
        '        let sortedFaces=faces.sorted(by:{$0.0<$1.0})\n        RopeRegionProfile.end(0,traversalTimer)\n        for (index,mask) in sortedFaces {')
    source=once(source,'                    if let candidates=region.candidates',
        '                    let candidateTimer=RopeRegionProfile.begin()\n                    if let candidates=region.candidates')
    source=once(source,'                        regionWork.boundaryPairs += candidates.boundaryPairs',
        '                        RopeRegionProfile.end(1,candidateTimer)\n                        let hitsTimer=RopeRegionProfile.begin()\n                        regionWork.boundaryPairs += candidates.boundaryPairs')
    source=once(source,'                    } else {\n                        regionWork.fallbacks += 1',
        '                        RopeRegionProfile.end(3,hitsTimer)\n                    } else {\n                        RopeRegionProfile.end(1,candidateTimer)\n                        regionWork.fallbacks += 1')
    source=once(source,'            let face=mesh.triangles[index],a=mesh.vertices[face.x],b=mesh.vertices[face.y],c=mesh.vertices[face.z]\n            let normal=simd_normalize(simd_cross(b-a,c-a))\n            var first=FusedWitness',
        '            let triangleTimer=RopeRegionProfile.begin()\n            let face=mesh.triangles[index],a=mesh.vertices[face.x],b=mesh.vertices[face.y],c=mesh.vertices[face.z]\n            let normal=simd_normalize(simd_cross(b-a,c-a))\n            var first=FusedWitness')
    source=once(source,'            Self.mergeFused(merit.hit,into:&meritHits);Self.mergeFused(last.hit,into:&lastHits)',
        '            Self.mergeFused(merit.hit,into:&meritHits);Self.mergeFused(last.hit,into:&lastHits)\n            RopeRegionProfile.end(4,triangleTimer)')
    return source


def math_source(source):
    return once(source,'    func containsProjection(_ point:SIMD3<Double>)->Bool? {',
        '    func containsProjection(_ point:SIMD3<Double>)->Bool? {\n        let membershipTimer=RopeRegionProfile.begin()\n        defer {RopeRegionProfile.end(2,membershipTimer)}')


def driver_source(source):
    source=source[:source.index('do {\n    try clippedPlanarFixtures()')]
    source+='''do {
    try clippedPlanarFixtures();try planarRegionFixtures()
    let original=evaluateRegions(false),plain=evaluateRegions(true,true)
    RopeRegionProfile.reset();RopeRegionProfile.enabled=true
    let measured=evaluateRegions(true,true)
    RopeRegionProfile.enabled=false
    guard regionOutputBits(plain.1)==regionOutputBits(measured.1) else {
        throw RopePhysicsError.invalid("instrumented full outputs bit identity")
    }
    let labels=["traversalAndSort","candidatesIncludingMembership","membershipNested","planarHitsAndMerge","originalTrianglesAndMerge"]
    var buckets:[String:Any]=[:]
    for i in labels.indices {buckets[labels[i]]=["seconds":RopeRegionProfile.seconds[i],"calls":RopeRegionProfile.calls[i]]}
    let remainder=measured.0-[0,1,3,4].map{RopeRegionProfile.seconds[$0]}.reduce(0,+)
    // Empty pair cost is a diagnostic scale, never subtracted to create an acceptance time.
    RopeRegionProfile.reset();RopeRegionProfile.enabled=true
    let emptyStart=ProcessInfo.processInfo.systemUptime
    for _ in 0..<10000 {RopeRegionProfile.end(0,RopeRegionProfile.begin())}
    let emptySeconds=ProcessInfo.processInfo.systemUptime-emptyStart
    RopeRegionProfile.enabled=false
    result=["owner":"strong-owl-live-physics","adopted":false,"scope":"instrumentation-only serial query corpus; no timing-gate retry",
        "queries":queries.count,"outputsBitIdentical":true,"maximumDepthDifferenceMeters":try validateRegions(original.1,measured.1),
        "instrumentedSeconds":measured.0,"buckets":buckets,"remainderSeconds":remainder,"emptyTimerPairs":10000,"emptyTimerSeconds":emptySeconds,
        "regionCalls":measured.2.calls,"boundaryPairs":measured.2.boundaryPairs,"fallbacks":measured.2.fallbacks]
    try persist(nil);print("PASS planar query diagnostic",queries.count,"seconds",measured.0,"buckets",buckets)
} catch {try persist(String(describing:error));print("FAIL planar query diagnostic",error);exit(2)}
'''
    return source


def profile_source():
    return Path(__file__).with_name('Profile.swift').read_text()
