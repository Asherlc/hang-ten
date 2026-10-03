"""Certified immutable temporal BVH leaf rosters; original facet arithmetic."""
from pathlib import Path
from armijo.snapshot import once


def collider_source(source):
    source="import Foundation\n"+source
    source=once(source,'    private let supportDomain:Bool','    private let supportDomain:Bool\n    private let neighborhoodIdentity=UUID()')
    source=once(source,'endInside:Bool,certifyBounds:Bool=false)',
        'endInside:Bool,certifyBounds:Bool=false,retainNeighborhood:Bool=false,neighborhood:RopeQueryNeighborhood?=nil,verifyNeighborhood:Bool=false)')
    source=source.replace('clearance:Double?,bound:RopeCertifiedClearance?)','clearance:Double?,bound:RopeCertifiedClearance?,neighborhood:RopeQueryNeighborhood?,reused:Bool,maskConflict:Bool)')
    source=once(source,'radius:rowRadius)],nil,nil)','radius:rowRadius)],nil,nil,nil,false,false)')
    start=source.index('        let low=simd_min(start,end),high=simd_max(start,end)',source.index('func fusedContactEvaluation'))
    stop=source.index('        let validDomain=',start)
    source=source[:start]+'''        let rowSquare=rowRadius*rowRadius,meritSquare=meritRadius*meritRadius
        let traversal=neighborhoodFaces(start:start,end:end,rowRadius:rowRadius,meritRadius:meritRadius,
            enabled:retainNeighborhood,prior:neighborhood,verify:verifyNeighborhood)
        let faces=traversal.faces
        var firstHits:[RopeSegmentContact]=[],rowHits:[RopeSegmentContact]=[],meritHits:[RopeSegmentContact]=[],lastHits:[RopeSegmentContact]=[]
'''+source[stop:]
    source=once(source,'boundKnown && boundMinimum.isFinite ? RopeCertifiedClearance(lowerBound:boundMinimum):nil)',
        'boundKnown && boundMinimum.isFinite ? RopeCertifiedClearance(lowerBound:boundMinimum):nil,traversal.neighborhood,traversal.reused,traversal.conflict)')
    source=once(source,'results.initialize(repeating:([],nil,nil),count:linkCount)','results.initialize(repeating:([],nil,nil,nil,false,false),count:linkCount)')
    source=once(source,'verifyFreeBalls:Bool=false)->(points:',
        'verifyFreeBalls:Bool=false,retainNeighborhoods:Bool=false,neighborhoods:[RopeQueryNeighborhood?]?=nil,verifyNeighborhoods:Bool=false)->(points:')
    source=once(source,'certifiedParities:Int,parityConflicts:Int) {',
        'certifiedParities:Int,parityConflicts:Int,neighborhoods:[RopeQueryNeighborhood?],reusedNeighborhoods:Int,maskConflicts:Int) {')
    source=once(source,'        precondition(points.count>=2)',
        '        precondition(points.count>=2)\n        precondition(neighborhoods==nil || neighborhoods!.count==points.count-1)')
    source=once(source,'endInside:storage.inside[i+1],certifyBounds:certifyBounds)',
        'endInside:storage.inside[i+1],certifyBounds:certifyBounds,retainNeighborhood:retainNeighborhoods,neighborhood:neighborhoods?[i],verifyNeighborhood:verifyNeighborhoods)')
    source=once(source,'        return (p,r,m,clearances,bounds,certified,conflicts)', '''        var next:[RopeQueryNeighborhood?]=[],reused=0,maskConflicts=0
        if retainNeighborhoods {
            for i in 0..<links {
                next.append(storage.results[i].neighborhood)
                if storage.results[i].reused {reused += 1}
                if storage.results[i].maskConflict {maskConflicts += 1}
            }
        }
        return (p,r,m,clearances,bounds,certified,conflicts,next,reused,maskConflicts)''')
    return source+'\n'+Path(__file__).with_name('Traversal.swift').read_text()


def solver_source(source):
    source=once(source,'    var freeBallExperiment=false','''    var freeBallExperiment=false
    var neighborhoodExperiment=false
    var verifyNeighborhoodMasks=false
    private var queryNeighborhoods:[[RopeQueryNeighborhood?]]?=nil
    var reusedNeighborhoods=0
    var neighborhoodMaskConflicts=0''')
    source=once(source,'        freeBallCertifiedParities=0;freeBallParityConflicts=0',
        '        freeBallCertifiedParities=0;freeBallParityConflicts=0;reusedNeighborhoods=0;neighborhoodMaskConflicts=0')
    source=once(source,'        if let cached=cachedEvaluation,cached.bits==bits',
        '        bits += [clearanceBoundExperiment ? 1:0,freeBallExperiment ? 1:0,neighborhoodExperiment ? 1:0,verifyFreeBallParity ? 1:0,verifyNeighborhoodMasks ? 1:0]\n        if let cached=cachedEvaluation,cached.bits==bits')
    source=once(source,'            let batch=collider.fusedChainContacts(points:board', '''            if neighborhoodExperiment,queryNeighborhoods==nil {
                queryNeighborhoods=candidate.ropes.map{Array(repeating:nil,count:$0.restLengths.count)}
            }
            let prior=neighborhoodExperiment ? queryNeighborhoods?[r]:nil
            let batch=collider.fusedChainContacts(points:board''')
    source=once(source,'verifyFreeBalls:verifyFreeBallParity)',
        'verifyFreeBalls:verifyFreeBallParity,retainNeighborhoods:neighborhoodExperiment,neighborhoods:prior,verifyNeighborhoods:verifyNeighborhoodMasks)')
    source=once(source,'            clearances.append(batch.clearances)', '''            if neighborhoodExperiment {queryNeighborhoods?[r]=batch.neighborhoods}
            reusedNeighborhoods += batch.reusedNeighborhoods;neighborhoodMaskConflicts += batch.maskConflicts
            clearances.append(batch.clearances)''')
    source+='''
extension RopeDynamicsSolver {
    func neighborhoodSnapshot()->[[Any]] {
        (queryNeighborhoods ?? []).map {$0.map {value -> Any in
            guard let value else {return NSNull()}
            return ["identity":value.identity.uuidString,"radius":String(value.rowRadius.bitPattern,radix:16),
                "low":[value.low.x,value.low.y,value.low.z].map{String($0.bitPattern,radix:16)},
                "high":[value.high.x,value.high.y,value.high.z].map{String($0.bitPattern,radix:16)},"leaves":value.leaves] as [String:Any]
        }}
    }
}
'''
    return source


def driver_source(source):
    source=once(source,'"window":[121,140],"freeBalls":true','"window":[121,140],"freeBalls":true,"neighborhoods":true')
    source=once(source,'enabled:Bool,verify:Bool)throws->FreeBallWindow','enabled:Bool,verify:Bool,rosters:Bool=false)throws->FreeBallWindow')
    source=once(source,'x.verifyFreeBallParity=verify','x.verifyFreeBallParity=verify;x.neighborhoodExperiment=rosters;x.verifyNeighborhoodMasks=verify && rosters')
    source=once(source,'    guard x.freeBallAnchorSnapshot().isEmpty else',
        '    guard x.neighborhoodSnapshot().isEmpty,x.freeBallAnchorSnapshot().isEmpty else')
    source=once(source,'guard x.reviewStepCaps==0,x.reviewStepRetries==0 else',
        'guard x.reviewStepCaps==0,x.reviewStepRetries==0,x.neighborhoodMaskConflicts==0 else')
    source=once(source,'"certifiedParities":x.freeBallCertifiedParities,',
        '"reusedNeighborhoods":x.reusedNeighborhoods,"maskConflicts":x.neighborhoodMaskConflicts,"certifiedParities":x.freeBallCertifiedParities,')
    source=once(source,'            try serialize(["anchors":a.states[i].freeBallAnchorSnapshot()])',
        '            try serialize(["rosters":a.states[i].neighborhoodSnapshot()])==serialize(["rosters":b.states[i].neighborhoodSnapshot()]),\n            try serialize(["anchors":a.states[i].freeBallAnchorSnapshot()])')
    source=source.replace('"anchors":rollback.freeBallAnchorSnapshot()', '"anchors":rollback.freeBallAnchorSnapshot(),"rosters":rollback.neighborhoodSnapshot()')
    source=once(source,'guard strict.freeBallAnchorSnapshot().isEmpty else',
        'guard strict.neighborhoodSnapshot().isEmpty,strict.freeBallAnchorSnapshot().isEmpty else')
    source=once(source,'    try clearanceBoundFixtures();try freeBallFixtures()',
        '    try neighborhoodFixtures();try clearanceBoundFixtures();try freeBallFixtures()')
    source=once(source,'let verified=try window(initial,enabled:true,verify:true)',
        'let verified=try window(initial,enabled:true,verify:true,rosters:true)')
    source=once(source,'let candidate=try window(initial,enabled:true,verify:false)', '''let candidate=try window(initial,enabled:true,verify:false,rosters:true)
    let freeBall=try window(initial,enabled:true,verify:false)
    result["freeBallControlWindow"]=freeBall.records''')
    source=once(source,'        let a:FreeBallWindow,b:FreeBallWindow','        let a:FreeBallWindow,b:FreeBallWindow,f:FreeBallWindow')
    source=once(source,'        if iteration%2==0 {a=try window(initial,enabled:false,verify:false);b=try window(initial,enabled:true,verify:false)}\n        else {b=try window(initial,enabled:true,verify:false);a=try window(initial,enabled:false,verify:false)}', '''        if iteration%3==0 {a=try window(initial,enabled:false,verify:false);f=try window(initial,enabled:true,verify:false);b=try window(initial,enabled:true,verify:false,rosters:true)}
        else if iteration%3==1 {b=try window(initial,enabled:true,verify:false,rosters:true);f=try window(initial,enabled:true,verify:false);a=try window(initial,enabled:false,verify:false)}
        else {f=try window(initial,enabled:true,verify:false);a=try window(initial,enabled:false,verify:false);b=try window(initial,enabled:true,verify:false,rosters:true)}''')
    source=once(source,'        try verifyDeterminism(a,original);try verifyDeterminism(b,candidate)',
        '        try verifyDeterminism(a,original);try verifyDeterminism(b,candidate);try verifyDeterminism(f,freeBall)')
    source=once(source,'pairs.append(["originalSeconds":a.seconds,"candidateSeconds":b.seconds,"ratio":b.seconds/a.seconds])',
        'pairs.append(["originalSeconds":a.seconds,"candidateSeconds":b.seconds,"freeBallSeconds":f.seconds,"ratio":b.seconds/a.seconds,"freeBallRatio":b.seconds/f.seconds])')
    source=once(source,'    guard median<=0.80 else', '''    let incremental=pairs.map{$0["freeBallRatio"] as! Double}.sorted()[3];result["medianFreeBallRatio"]=incremental
    try persist(nil)
    guard median<=0.80,incremental<=0.80 else''')
    return source.replace('fixed twenty-step median <=0.80 speed gate','fixed twenty-step total and incremental <=0.80 speed gates')
