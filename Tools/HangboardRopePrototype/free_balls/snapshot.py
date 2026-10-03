"""Outside free-ball classification with immutable transactional anchors."""
from pathlib import Path
from armijo.snapshot import once


def collider_source(source):
    source=once(source,'    let pointCount:Int,linkCount:Int','''    let pointCount:Int,linkCount:Int
    let certified:UnsafeMutablePointer<Bool>
    let conflicts:UnsafeMutablePointer<Bool>''')
    source=once(source,'        pointCount=points;linkCount=points-1','''        pointCount=points;linkCount=points-1
        certified = .allocate(capacity:points);certified.initialize(repeating:false,count:points)
        conflicts = .allocate(capacity:points);conflicts.initialize(repeating:false,count:points)''')
    source=once(source,'    deinit {inside.deinitialize','''    deinit {certified.deinitialize(count:pointCount);certified.deallocate();conflicts.deinitialize(count:pointCount);conflicts.deallocate();inside.deinitialize''')
    source=once(source,'meritRadius:Double,certifyBounds:Bool=false)->(points:',
        'meritRadius:Double,certifyBounds:Bool=false,freeBalls:[RopePointFreeBall?]?=nil,verifyFreeBalls:Bool=false)->(points:')
    source=once(source,'bounds:[RopeCertifiedClearance?]) {','bounds:[RopeCertifiedClearance?],certifiedParities:Int,parityConflicts:Int) {')
    source=once(source,'        precondition(points.count>=2)','''        precondition(points.count>=2)
        precondition(freeBalls==nil || freeBalls!.count==points.count)''')
    source=once(source,'            for i in ranges(points.count,job) {storage.inside[i]=queryParity(points[i])}','''            for i in ranges(points.count,job) {
                if let ball=freeBalls?[i],ball.contains(points[i]) {
                    storage.certified[i]=true
                    storage.inside[i]=verifyFreeBalls ? queryParity(points[i]):false
                    storage.conflicts[i]=storage.inside[i]
                } else {storage.inside[i]=queryParity(points[i])}
            }''')
    source=once(source,'return (p,r,m,clearances,bounds)','''var certified=0,conflicts=0
        for i in 0..<points.count {if storage.certified[i] {certified += 1};if storage.conflicts[i] {conflicts += 1}}
        return (p,r,m,clearances,bounds,certified,conflicts)''')
    return source


def solver_source(source):
    source=once(source,'    var clearanceBoundExperiment=false','''    var clearanceBoundExperiment=false
    var freeBallExperiment=false
    var verifyFreeBallParity=false
    private var parityAnchors:[RopeParityAnchor]?=nil
    var freeBallCertifiedParities=0
    var freeBallParityConflicts=0''')
    source=once(source,'        let prediction=state\n        cachedEvaluation=nil','''        let prediction=state
        freeBallCertifiedParities=0;freeBallParityConflicts=0
        cachedEvaluation=nil''')
    source=once(source,'        for rope in candidate.ropes {\n            let board=',
        '        for (r,rope) in candidate.ropes.enumerated() {\n            let board=')
    source=once(source,'            let batch=collider.fusedChainContacts(points:board','''            let anchor=freeBallExperiment && r<(parityAnchors?.count ?? 0) ? parityAnchors?[r]:nil
            let balls=anchor?.ropeID==rope.id && anchor?.balls.count==board.count ? anchor?.balls:nil
            let batch=collider.fusedChainContacts(points:board''')
    source=once(source,'certifyBounds:clearanceBoundExperiment)',
        'certifyBounds:clearanceBoundExperiment,freeBalls:balls,verifyFreeBalls:verifyFreeBallParity)')
    source=once(source,'            clearances.append(batch.clearances)','''            freeBallCertifiedParities += batch.certifiedParities;freeBallParityConflicts += batch.parityConflicts
            clearances.append(batch.clearances)''')
    source=once(source,'        acceptedMinimumClearance=metrics.minimumSegmentClearance','''        if freeBallExperiment {
            parityAnchors=state.ropes.enumerated().map {r,rope in
                let bounds=evaluation.bounds[r]
                let balls=rope.positions.indices.map {i -> RopePointFreeBall? in
                    // Each available bound also proves its endpoints were classified outside.
                    var radius:Double?=nil
                    if i>0,let bound=bounds[i-1],bound.lowerBound>0 {radius=bound.lowerBound}
                    if i<bounds.count,let bound=bounds[i],bound.lowerBound>0 {radius=max(radius ?? 0,bound.lowerBound)}
                    guard let value=radius else {return nil}
                    return RopePointFreeBall(center:state.boardPoint(rope.positions[i]),
                        radius:RopeCertifiedClearance(lowerBound:value),outsideKnown:true)
                }
                return RopeParityAnchor(ropeID:rope.id,balls:balls)
            }
        }
        acceptedMinimumClearance=metrics.minimumSegmentClearance''')
    source+='''
extension RopeDynamicsSolver {
    func freeBallAnchorSnapshot()->[[String:Any]] {
        (parityAnchors ?? []).map {anchor in ["rope":anchor.ropeID,"balls":anchor.balls.map {ball -> Any in
            guard let ball else {return NSNull()}
            return ["center":[ball.center.x,ball.center.y,ball.center.z].map{String($0.bitPattern,radix:16)},
                "radius":String(ball.radius.lowerBound.bitPattern,radix:16)] as [String:Any]
        }]}
    }
}
'''
    return source


def driver_source(source):
    source=source[:source.index('func fixtures()throws {')]
    source=once(source,'"sigma":RopeArmijo.sigma,"step":109','"window":[121,140],"freeBalls":true')
    return source+Path(__file__).with_name('Window.swift').read_text()
