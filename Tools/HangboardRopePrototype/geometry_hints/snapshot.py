"""Changed intermediate floating-contact contract, exact-geometric pruning."""
from armijo.snapshot import once
from spectral_step.snapshot import driver_source as checkpoint_source


def collider_source(source):
    prefix,source=source.split('// Share triangle arithmetic across queries',1)
    source=once(source,'startInside:Bool,endInside:Bool)->(hits:',
        'startInside:Bool,endInside:Bool,hintCache:RopeGeometryHintCache?=nil)->(hits:')
    source=once(source,'        var minimum=Double.infinity\n        for (index,mask) in faces.sorted',
        '        var minimum=Double.infinity,prunedAny=false\n        for (index,mask) in faces.sorted')
    source=once(source,'            let normal=simd_normalize(simd_cross(b-a,c-a))','''            if let cache=hintCache,rowRadius.isFinite,meritRadius.isFinite,rowRadius>=meritRadius,meritRadius>0 {
                cache.visits += 1
                if let hint=cache.hints[index],hint.separates(start,end,rowRadius) {
                    // Preserve the original rounded ray result even with geometric separation.
                    if start != end,mask & 6 != 0,let t=Self.rayTriangle(start,end-start,a,b,c),t>=0,t<=1 {cache.rayBlocks += 1}
                    else {cache.pruned += 1;prunedAny=true;continue}
                } else if cache.hints[index]==nil {cache.misses += 1}
            }
            let normal=simd_normalize(simd_cross(b-a,c-a))''')
    # Scope the row initializer to this function; other functions use similar names.
    source=once(source,'var row=FusedWitness(best:rowSquare,radius:rowRadius,faceNormal:normal)',
        'var row=FusedWitness(best:rowSquare,radius:rowRadius,faceNormal:normal,trackHint:hintCache != nil)')
    source=once(source,'            if row.best<rowSquare {minimum=min(minimum,sqrt(row.best))}','''            if let delta=row.hintDelta {
                hintCache?.hints[index]=RopeGeometryHintFactory.make(delta,a,b,c)
            }
            if row.best<rowSquare {minimum=min(minimum,sqrt(row.best))}''')
    source=once(source,'return ([firstHits,rowHits,meritHits,lastHits],minimum<1e-10 ? 0:minimum)',
        'return ([firstHits,rowHits,meritHits,lastHits],prunedAny ? nil:(minimum<1e-10 ? 0:minimum))')
    source=once(source,'        var hit:RopeSegmentContact?\n        mutating func consider','''        var hit:RopeSegmentContact?
        var trackHint=false
        var hintSquare=Double.infinity
        var hintDelta:SIMD3<Double>?=nil
        mutating func consider''')
    beginning,tail=source.split('    private struct FusedWitness {',1)
    tail=once(tail,'            guard distanceSquared<best else{return}','''            if trackHint,distanceSquared<hintSquare {hintSquare=distanceSquared;hintDelta=p-q}
            guard distanceSquared<best else{return}''')
    source=beginning+'    private struct FusedWitness {'+tail
    source=once(source,'func fusedChainContacts(points:[SIMD3<Double>],rowRadius:Double,meritRadius:Double)',
        'func fusedChainContacts(points:[SIMD3<Double>],rowRadius:Double,meritRadius:Double,hintCaches:[RopeGeometryHintCache]?=nil)')
    source=once(source,'startInside:storage.inside[i],endInside:storage.inside[i+1])',
        'startInside:storage.inside[i],endInside:storage.inside[i+1],hintCache:hintCaches?[i])')
    return prefix+'// Share triangle arithmetic across queries'+source


def solver_source(source):
    source=once(source,'    var armijoExperiment=false','''    var armijoExperiment=false
    var geometryHintExperiment=false
    private var geometryHints:[[RopeGeometryHintCache]]?=nil''')
    source=once(source,'        for rope in candidate.ropes {\n            let board=', '        for (r,rope) in candidate.ropes.enumerated() {\n            let board=')
    source=once(source,'            let batch=collider.fusedChainContacts(points:board,rowRadius:rope.radius+RopeRegionGeometry.clearance+0.00005,meritRadius:rope.radius+RopeRegionGeometry.clearance)','''            if geometryHintExperiment,geometryHints==nil {
                geometryHints=state.ropes.map{$0.restLengths.map{_ in RopeGeometryHintCache()}}
            }
            let batch=collider.fusedChainContacts(points:board,rowRadius:rope.radius+RopeRegionGeometry.clearance+0.00005,
                meritRadius:rope.radius+RopeRegionGeometry.clearance,hintCaches:geometryHintExperiment ? geometryHints?[r]:nil)''')
    source+='''
extension RopeDynamicsSolver {
    func geometryHintSnapshot()->[[[String:Any]]] {
        (geometryHints ?? []).map{$0.map {cache in
            ["visits":cache.visits,"pruned":cache.pruned,"misses":cache.misses,"rayBlocks":cache.rayBlocks,
             "hints":cache.hints.keys.sorted().map{id in
                let h=cache.hints[id]
                return ["face":id,"direction":h!.direction.array.map{String($0.bitPattern,radix:16)},
                    "upper":String(h!.triangleUpper.bitPattern,radix:16),"norm":String(h!.normUpper.bitPattern,radix:16)] as [String:Any]
             }] as [String:Any]
        }}
    }
}
'''
    source=source.replace('h!.direction.array.map','[h!.direction.x,h!.direction.y,h!.direction.z].map')
    return source


def driver_source(source):
    source=checkpoint_source(source,140)
    source=source.replace('spectralStepExperiment','geometryHintExperiment').replace('spectralFixtures()','geometryHintFixtures()').replace('result["spectralStep"]','result["geometryHints"]')
    source=once(source,'guard median<=1.10','guard median<=0.80')
    source=source.replace('fixed median <=1.10 ordinary-step overhead gate','fixed median <=0.80 complete-step speed gate')
    source=once(source,'    result["originalQPs"]=', '    result["geometryHintCache"]=candidate.geometryHintSnapshot()\n    result["originalQPs"]=')
    source=once(source,'        _ = try check(b)','''        guard try serialize(["cache":b.geometryHintSnapshot()])==serialize(["cache":candidate.geometryHintSnapshot()]) else {
            throw RopePhysicsError.invalid("identical cold-cache replay")
        }
        _ = try check(b)''')
    return source


def profile_solver(source):
    source=once(source,'    var geometryHintExperiment=false','''    var geometryHintExperiment=false
    var geometryFinalMetricSeconds=0.0
    var geometryBatchSeconds=0.0''')
    source=once(source,'        let prediction=state\n        cachedEvaluation=nil','        let prediction=state\n        geometryFinalMetricSeconds=0;geometryBatchSeconds=0\n        cachedEvaluation=nil')
    source=once(source,'        let metrics=try RopeSimulationMetrics.measure(state:state,input:input,collider:collider,boardHistory:history.map{$0.1},channelCache:channelColliderCache,clearanceReceipts:receipts,clearanceObserver:{r,i,value in perSegment[r][i]=value})','''        let metricStart=ProcessInfo.processInfo.systemUptime
        let metrics=try RopeSimulationMetrics.measure(state:state,input:input,collider:collider,boardHistory:history.map{$0.1},channelCache:channelColliderCache,clearanceReceipts:receipts,clearanceObserver:{r,i,value in perSegment[r][i]=value})
        geometryFinalMetricSeconds += ProcessInfo.processInfo.systemUptime-metricStart''')
    source=once(source,'            let batch=collider.fusedChainContacts(points:board',
        '            let batchStart=ProcessInfo.processInfo.systemUptime\n            let batch=collider.fusedChainContacts(points:board')
    source=once(source,'            clearances.append(batch.clearances)',
        '            geometryBatchSeconds += ProcessInfo.processInfo.systemUptime-batchStart\n            clearances.append(batch.clearances)')
    return source


def profile_driver(source):
    source=once(source,'    result["geometryHintCache"]=','''    result["originalFinalMetricSeconds"]=original.geometryFinalMetricSeconds
    result["candidateFinalMetricSeconds"]=candidate.geometryFinalMetricSeconds
    result["originalBatchSeconds"]=original.geometryBatchSeconds
    result["candidateBatchSeconds"]=candidate.geometryBatchSeconds
    result["geometryHintCache"]=''')
    source=once(source,'pairs.append(["originalSeconds":ca.0,"candidateSeconds":cb.0,"ratio":cb.0/ca.0])','''pairs.append(["originalSeconds":ca.0,"candidateSeconds":cb.0,"ratio":cb.0/ca.0,
            "originalFinalMetricSeconds":a.geometryFinalMetricSeconds,"candidateFinalMetricSeconds":b.geometryFinalMetricSeconds,
            "originalBatchSeconds":a.geometryBatchSeconds,"candidateBatchSeconds":b.geometryBatchSeconds])''')
    return source
