def once(source,old,new):
    assert source.count(old)==1,old
    return source.replace(old,new)

def metrics_source(source):
    source=once(source,'boardHistory:[Double],includeSelfContact:Bool=true,channelCache:RopeChannelColliderCache?=nil) throws -> Self',
      'boardHistory:[Double],includeSelfContact:Bool=true,channelCache:RopeChannelColliderCache?=nil,clearanceObserver:((Int,Int,Double)->Void)?=nil) throws -> Self')
    start=source.index('    static func measure(')
    head,tail=source[:start],source[start:]
    tail=once(tail,'        for rope in state.ropes {','        for (r,rope) in state.ropes.enumerated() {')
    tail=once(tail,'                let segmentClearance=collider.segmentClearance(from:a,to:b)',
      '                let segmentClearance=collider.segmentClearance(from:a,to:b)\n                clearanceObserver?(r,i,segmentClearance)')
    return head+tail

def solver_source(source):
    source=once(source,'    private var acceptedMinimumClearance:Double?', '    private var acceptedMinimumClearance:Double?\n    private var acceptedSegmentClearances:[[Double]]?')
    source=once(source,'        for iteration in 0...maxIterations {\n            let metrics=', '        for iteration in 0...maxIterations {\n            var perSegment=candidate.state.ropes.map{Array(repeating:Double.infinity,count:$0.restLengths.count)}\n            let metrics=')
    source=once(source,'boardHistory:[candidate.state.boardHeight],channelCache:candidate.channelColliderCache)',
      'boardHistory:[candidate.state.boardHeight],channelCache:candidate.channelColliderCache,clearanceObserver:{r,i,value in perSegment[r][i]=value})')
    source=once(source,'                candidate.acceptedMinimumClearance=metrics.minimumSegmentClearance',
      '                candidate.acceptedMinimumClearance=metrics.minimumSegmentClearance\n                candidate.acceptedSegmentClearances=perSegment')
    source=once(source,'                let oldClearance=acceptedMinimumClearance ?? collider.segmentClearance(from:a,to:b)',
      """                let oldClearance:Double
                if let cached=acceptedSegmentClearances {oldClearance=cached[r][i]}
                else {oldClearance=acceptedMinimumClearance ?? collider.segmentClearance(from:a,to:b)}""")
    source=once(source,'        let metrics=try RopeSimulationMetrics.measure(state:state,input:input,collider:collider,boardHistory:history.map{$0.1},channelCache:channelColliderCache)',
      """        var perSegment=state.ropes.map{Array(repeating:Double.infinity,count:$0.restLengths.count)}
        let metrics=try RopeSimulationMetrics.measure(state:state,input:input,collider:collider,boardHistory:history.map{$0.1},channelCache:channelColliderCache,clearanceObserver:{r,i,value in perSegment[r][i]=value})""")
    source=once(source,'        acceptedMinimumClearance=metrics.minimumSegmentClearance\n        lastStepDuration=dt',
      '        acceptedMinimumClearance=metrics.minimumSegmentClearance\n        acceptedSegmentClearances=perSegment\n        lastStepDuration=dt')
    source=once(source,'    private var lastStepDuration=1.0/240','    private var lastStepDuration=1.0/240\n    func sweepCacheIdentity()->[[UInt64]]? {acceptedSegmentClearances?.map{$0.map{$0.bitPattern}}}')
    return source
