"""Immutable support planes and typed lower bounds in copied native sources."""
from armijo.snapshot import once
from spectral_step.snapshot import driver_source as checkpoint_source


def collider_source(source):
    source=once(source,'    private let tree: [Node]','''    private let tree: [Node]
    private let supportPlanes:[RopeTriangleSupport?]
    private let supportDomain:Bool''')
    source=once(source,'        self.mesh=mesh; self.tree=nodes','''        self.mesh=mesh; self.tree=nodes
        supportDomain=mesh.vertices.allSatisfy {max(abs($0.x),max(abs($0.y),abs($0.z)))<=0.5}
        supportPlanes=mesh.triangles.map {face in
            let a=mesh.vertices[face.x],b=mesh.vertices[face.y],c=mesh.vertices[face.z]
            return RopeTriangleSupport(simd_cross(b-a,c-a),a,b,c)
        }''')
    prefix,source=source.split('// Share triangle arithmetic across queries',1)
    # Tuple provenance is separate from the original computed-distance receipt.
    source=source.replace('clearance:Double?)','clearance:Double?,bound:RopeCertifiedClearance?)')
    source=once(source,'startInside:Bool,endInside:Bool)->(hits:',
        'startInside:Bool,endInside:Bool,certifyBounds:Bool=false)->(hits:')
    source=once(source,'segmentContacts(from:end,to:end,radius:rowRadius)],nil)',
        'segmentContacts(from:end,to:end,radius:rowRadius)],nil,nil)')
    source=once(source,'        var minimum=Double.infinity\n        for (index,mask) in faces.sorted','''        let validDomain=certifyBounds && supportDomain && rowRadius.isFinite && meritRadius.isFinite &&
            rowRadius>=0.001 && rowRadius<=0.01 && rowRadius>=meritRadius && meritRadius>0 &&
            [start,end].allSatisfy {$0.x.isFinite && $0.y.isFinite && $0.z.isFinite && max(abs($0.x),max(abs($0.y),abs($0.z)))<=0.5}
        var minimum=Double.infinity,prunedAny=false
        // All faces omitted by link BVH pruning have this conservative bound.
        var boundMinimum=(rowRadius-1e-9).nextDown,boundKnown=validDomain
        for (index,mask) in faces.sorted''')
    source=once(source,'            let normal=simd_normalize(simd_cross(b-a,c-a))','''            if validDomain,let plane=supportPlanes[index],let bound=plane.bound(start,end),bound.lowerBound>rowRadius+1e-9 {
                // Geometric separation never replaces the original rounded ray hit.
                if !(start != end && mask & 6 != 0 && Self.rayTriangle(start,end-start,a,b,c).map{$0>=0 && $0<=1} == true) {
                    prunedAny=true;continue
                }
            }
            let normal=simd_normalize(simd_cross(b-a,c-a))''')
    source=once(source,'var row=FusedWitness(best:rowSquare,radius:rowRadius,faceNormal:normal)',
        'var row=FusedWitness(best:rowSquare,radius:rowRadius,faceNormal:normal,trackSupport:validDomain && mask & 2 != 0)')
    source=once(source,'            if row.best<rowSquare {minimum=min(minimum,sqrt(row.best))}','''            if validDomain,mask & 2 != 0 {
                if let delta=row.supportDelta,let support=RopeTriangleSupport(delta,a,b,c),let bound=support.bound(start,end) {
                    boundMinimum=min(boundMinimum,bound.lowerBound)
                } else {boundKnown=false}
            }
            if row.best<rowSquare {minimum=min(minimum,sqrt(row.best))}''')
    source=once(source,'return ([firstHits,rowHits,meritHits,lastHits],minimum<1e-10 ? 0:minimum)','''return ([firstHits,rowHits,meritHits,lastHits],
            validDomain || prunedAny ? nil:(minimum<1e-10 ? 0:minimum),
            boundKnown && boundMinimum.isFinite ? RopeCertifiedClearance(lowerBound:boundMinimum):nil)''')
    source=once(source,'        var hit:RopeSegmentContact?\n        mutating func consider','''        var hit:RopeSegmentContact?
        var trackSupport=false
        var supportSquare=Double.infinity
        var supportDelta:SIMD3<Double>?=nil
        mutating func consider''')
    beginning,tail=source.split('    private struct FusedWitness {',1)
    tail=once(tail,'            guard distanceSquared<best else{return}','''            if trackSupport,distanceSquared<supportSquare {supportSquare=distanceSquared;supportDelta=p-q}
            guard distanceSquared<best else{return}''')
    source=beginning+'    private struct FusedWitness {'+tail
    source=once(source,'results.initialize(repeating:([],nil),count:linkCount)',
        'results.initialize(repeating:([],nil,nil),count:linkCount)')
    source=once(source,'func fusedChainContacts(points:[SIMD3<Double>],rowRadius:Double,meritRadius:Double)',
        'func fusedChainContacts(points:[SIMD3<Double>],rowRadius:Double,meritRadius:Double,certifyBounds:Bool=false)')
    source=once(source,'clearances:[Double?]) {','clearances:[Double?],bounds:[RopeCertifiedClearance?]) {')
    source=once(source,'startInside:storage.inside[i],endInside:storage.inside[i+1])',
        'startInside:storage.inside[i],endInside:storage.inside[i+1],certifyBounds:certifyBounds)')
    source=once(source,'        var clearances:[Double?]=[]','        var clearances:[Double?]=[],bounds:[RopeCertifiedClearance?]=[]')
    source=once(source,'clearances.append(storage.results[i].clearance);p[i]',
        'clearances.append(storage.results[i].clearance);bounds.append(storage.results[i].bound);p[i]')
    source=once(source,'return (p,r,m,clearances)','return (p,r,m,clearances,bounds)')
    return prefix+'// Share triangle arithmetic across queries'+source


def solver_source(source):
    source=once(source,'    var armijoExperiment=false','    var armijoExperiment=false\n    var clearanceBoundExperiment=false')
    source=once(source,'    let clearances:[[Double?]]','    let clearances:[[Double?]]\n    let bounds:[[RopeCertifiedClearance?]]')
    source=once(source,'        var clearances:[[Double?]]=[]','        var clearances:[[Double?]]=[],bounds:[[RopeCertifiedClearance?]]=[]')
    source=once(source,'meritRadius:rope.radius+RopeRegionGeometry.clearance)',
        'meritRadius:rope.radius+RopeRegionGeometry.clearance,certifyBounds:clearanceBoundExperiment)')
    source=once(source,'            clearances.append(batch.clearances)',
        '            clearances.append(batch.clearances);bounds.append(batch.bounds)')
    source=once(source,'clearances:clearances,selfPairs:pairs','clearances:clearances,bounds:bounds,selfPairs:pairs')
    source=once(source,'        let receipts=configurationEvaluation(state).clearances','''        let evaluation=configurationEvaluation(state)
        let receipts=evaluation.clearances''')
    source=once(source,'clearanceReceipts:receipts,clearanceObserver:',
        'clearanceReceipts:receipts,certifiedLowerBounds:clearanceBoundExperiment ? evaluation.bounds:nil,clearanceObserver:')
    source+='''
extension RopeDynamicsSolver {
    mutating func clearanceBoundSnapshot()->[[Double?]] {
        configurationEvaluation(state).bounds.map{$0.map{$0?.lowerBound}}
    }
}
'''
    return source


def metrics_source(source):
    source=once(source,'    let boardDisplacement: Double','    let boardDisplacement: Double\n    var minimumClearanceIsLowerBound=false')
    source=once(source,'clearanceReceipts:[[Double?]]?=nil,clearanceObserver:',
        'clearanceReceipts:[[Double?]]?=nil,certifiedLowerBounds:[[RopeCertifiedClearance?]]?=nil,clearanceObserver:')
    source=once(source,'        var failure:String?','        var failure:String?\n        var usedBound=false')
    source=once(source,'        for (r,rope) in state.ropes.enumerated() {','''        if let bounds=certifiedLowerBounds {
            precondition(bounds.count==state.ropes.count)
            for r in bounds.indices {precondition(bounds[r].count==state.ropes[r].restLengths.count)}
        }
        for (r,rope) in state.ropes.enumerated() {''')
    source=once(source,'                if let receipt=clearanceReceipts?[r][i],receipt.isFinite {segmentClearance=receipt}','''                if let bound=certifiedLowerBounds?[r][i],bound.lowerBound.isFinite,
                   bound.lowerBound>=max(0,rope.radius-0.00005) {
                    segmentClearance=bound.lowerBound;usedBound=true
                } else if certifiedLowerBounds != nil {
                    // A loose bound cannot reject a physically valid segment.
                    segmentClearance=collider.segmentClearance(from:a,to:b)
                } else if let receipt=clearanceReceipts?[r][i],receipt.isFinite {segmentClearance=receipt}''')
    source=once(source,'        return Self(totalLengthError:', '        var result=Self(totalLengthError:')
    source=once(source,'maximumSpeed:speed,boardDisplacement:displacement)','''maximumSpeed:speed,boardDisplacement:displacement)
        result.minimumClearanceIsLowerBound=usedBound
        return result''')
    return source


def driver_source(source):
    source=checkpoint_source(source,140)
    source=source.replace('spectralStepExperiment','clearanceBoundExperiment').replace('spectralFixtures()','clearanceBoundFixtures()').replace('result["spectralStep"]','result["clearanceBounds"]')
    source=once(source,'guard median<=1.10','guard median<=0.80')
    source=source.replace('fixed median <=1.10 ordinary-step overhead gate','fixed median <=0.80 complete-step speed gate')
    source=once(source,'    result["originalQPs"]=', '''    let bounds=candidate.clearanceBoundSnapshot()
    var validBounds=0,fallbackBounds=0,minimumSlack=Double.infinity
    for r in bounds.indices {for i in bounds[r].indices {
        if let bound=bounds[r][i] {
            let a=candidate.state.boardPoint(candidate.state.ropes[r].positions[i])
            let b=candidate.state.boardPoint(candidate.state.ropes[r].positions[i+1])
            let originalClearance=collider.segmentClearance(from:a,to:b)
            guard bound<=originalClearance+1e-9 else {throw RopePhysicsError.invalid("per-link original clearance oracle")}
            minimumSlack=min(minimumSlack,originalClearance-bound)
            if bound>=candidate.state.ropes[r].radius-0.00005 {validBounds += 1} else {fallbackBounds += 1}
        } else {fallbackBounds += 1}
    }}
    result["validClearanceBounds"]=validBounds;result["fallbackClearanceBounds"]=fallbackBounds
    result["minimumBoundOracleSlack"]=minimumSlack
    result["originalQPs"]=''')
    return source


def profile_solver(source):
    source=once(source,'    var clearanceBoundExperiment=false','''    var clearanceBoundExperiment=false
    var boundMetricSeconds=0.0
    var boundBatchSeconds=0.0''')
    source=once(source,'        let prediction=state\n        cachedEvaluation=nil','''        let prediction=state
        boundMetricSeconds=0;boundBatchSeconds=0
        cachedEvaluation=nil''')
    source=once(source,'        let metrics=try RopeSimulationMetrics.measure(state:state,input:input,collider:collider,boardHistory:history.map{$0.1},channelCache:channelColliderCache,clearanceReceipts:receipts,certifiedLowerBounds:clearanceBoundExperiment ? evaluation.bounds:nil,clearanceObserver:{r,i,value in perSegment[r][i]=value})','''        let metricStart=ProcessInfo.processInfo.systemUptime
        let metrics=try RopeSimulationMetrics.measure(state:state,input:input,collider:collider,boardHistory:history.map{$0.1},channelCache:channelColliderCache,clearanceReceipts:receipts,certifiedLowerBounds:clearanceBoundExperiment ? evaluation.bounds:nil,clearanceObserver:{r,i,value in perSegment[r][i]=value})
        boundMetricSeconds += ProcessInfo.processInfo.systemUptime-metricStart''')
    source=once(source,'            let batch=collider.fusedChainContacts(points:board',
        '            let batchStart=ProcessInfo.processInfo.systemUptime\n            let batch=collider.fusedChainContacts(points:board')
    source=once(source,'            clearances.append(batch.clearances)',
        '            boundBatchSeconds += ProcessInfo.processInfo.systemUptime-batchStart\n            clearances.append(batch.clearances)')
    return source


def profile_driver(source):
    source=once(source,'    result["originalQPs"]=', '''    result["originalMetricSeconds"]=original.boundMetricSeconds
    result["candidateMetricSeconds"]=candidate.boundMetricSeconds
    result["originalBatchSeconds"]=original.boundBatchSeconds
    result["candidateBatchSeconds"]=candidate.boundBatchSeconds
    result["originalQPs"]=''')
    source=once(source,'pairs.append(["originalSeconds":ca.0,"candidateSeconds":cb.0,"ratio":cb.0/ca.0])','''pairs.append(["originalSeconds":ca.0,"candidateSeconds":cb.0,"ratio":cb.0/ca.0,
            "originalMetricSeconds":a.boundMetricSeconds,"candidateMetricSeconds":b.boundMetricSeconds,
            "originalBatchSeconds":a.boundBatchSeconds,"candidateBatchSeconds":b.boundBatchSeconds])''')
    return source
