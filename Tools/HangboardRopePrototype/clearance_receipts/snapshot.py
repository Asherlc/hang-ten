def once(s,a,b):
    assert s.count(a)==1,a
    return s.replace(a,b)
def collider_source(s):
    s=once(s,'    func fusedContacts(from start:', '    func fusedContactEvaluation(from start:')
    s=once(s,'startInside:Bool,endInside:Bool)->[[RopeSegmentContact]] {','startInside:Bool,endInside:Bool)->(hits:[[RopeSegmentContact]],clearance:Double?) {')
    s=once(s,'            return [segmentContacts(from:start,to:start,radius:rowRadius),','            return ([segmentContacts(from:start,to:start,radius:rowRadius),')
    s=once(s,'segmentContacts(from:end,to:end,radius:rowRadius)]','segmentContacts(from:end,to:end,radius:rowRadius)],nil)')
    s=once(s,'        for (index,mask) in faces.sorted(by:{$0.0<$1.0}) {','        var minimum=Double.infinity\n        for (index,mask) in faces.sorted(by:{$0.0<$1.0}) {')
    s=once(s,'            Self.mergeFused(first.hit,into:&firstHits);','            if row.best<rowSquare {minimum=min(minimum,sqrt(row.best))}\n            Self.mergeFused(first.hit,into:&firstHits);')
    s=once(s,'        return [firstHits,rowHits,meritHits,lastHits]','        return ([firstHits,rowHits,meritHits,lastHits],minimum<1e-10 ? 0:minimum)')
    s=once(s,'UnsafeMutablePointer<[[RopeSegmentContact]]>','UnsafeMutablePointer<(hits:[[RopeSegmentContact]],clearance:Double?)>')
    s=once(s,'results.initialize(repeating:[],count:linkCount)','results.initialize(repeating:([],nil),count:linkCount)')
    s=once(s,'merits:[[RopeSegmentContact]]) {','merits:[[RopeSegmentContact]],clearances:[Double?]) {')
    s=once(s,'storage.results[i]=fusedContacts(', 'storage.results[i]=fusedContactEvaluation(')
    s=once(s,'        for i in 0..<links {','        var clearances:[Double?]=[]\n        for i in 0..<links {')
    s=once(s,'let result=storage.results[i];p[i]=result[0];','let result=storage.results[i].hits;clearances.append(storage.results[i].clearance);p[i]=result[0];')
    s=once(s,'        return (p,r,m)','        return (p,r,m,clearances)')
    s += "\nextension RopeTriangleCollider {\n func fusedContacts(from a:SIMD3<Double>,to b:SIMD3<Double>,rowRadius:Double,meritRadius:Double,startInside:Bool,endInside:Bool)->[[RopeSegmentContact]] {fusedContactEvaluation(from:a,to:b,rowRadius:rowRadius,meritRadius:meritRadius,startInside:startInside,endInside:endInside).hits}\n}\n"
    return s

def solver_source(s):
    s=once(s,'    let merits:[[[RopeSegmentContact]]]','    let merits:[[[RopeSegmentContact]]]\n    let clearances:[[Double?]]')
    s=once(s,'        var points:[[[RopeSegmentContact]]]=[],','        var clearances:[[Double?]]=[]\n        var points:[[[RopeSegmentContact]]]=[],')
    s=once(s,'            points.append(batch.points);','            clearances.append(batch.clearances)\n            points.append(batch.points);')
    s=once(s,'points:points,rows:rows,merits:merits,selfPairs:', 'points:points,rows:rows,merits:merits,clearances:clearances,selfPairs:')
    # Final state key evaluated after velocities, which aren't part of geometry key.
    s=once(s,'        var perSegment=state.ropes.map{Array(repeating:Double.infinity,count:$0.restLengths.count)}',
      '        let receipts=configurationEvaluation(state).clearances\n        var perSegment=state.ropes.map{Array(repeating:Double.infinity,count:$0.restLengths.count)}')
    s=once(s,'boardHistory:history.map{$0.1},channelCache:channelColliderCache,clearanceObserver:',
      'boardHistory:history.map{$0.1},channelCache:channelColliderCache,clearanceReceipts:receipts,clearanceObserver:')
    return s

def metrics_source(s):
    s=once(s,'clearanceObserver:((Int,Int,Double)->Void)?=nil)', 'clearanceReceipts:[[Double?]]?=nil,clearanceObserver:((Int,Int,Double)->Void)?=nil)')
    s=once(s,'        for (r,rope) in state.ropes.enumerated() {',"""        var receiptMinimum=Double.infinity,receiptMargin=Double.infinity
        if let receipts=clearanceReceipts {
            precondition(receipts.count==state.ropes.count)
            for r in receipts.indices {
                precondition(receipts[r].count==state.ropes[r].restLengths.count)
                for value in receipts[r].compactMap({$0}) where value.isFinite {
                    receiptMinimum=min(receiptMinimum,value);receiptMargin=min(receiptMargin,value-state.ropes[r].radius)
                }
            }
        }
        for (r,rope) in state.ropes.enumerated() {""")
    s=once(s,'                let segmentClearance=collider.segmentClearance(from:a,to:b)',"""                let segmentClearance:Double
                if let receipt=clearanceReceipts?[r][i],receipt.isFinite {segmentClearance=receipt}
                else if let receipt=clearanceReceipts?[r][i],receipt==Double.infinity {
                    let lowerBound=rope.radius+RopeRegionGeometry.clearance+0.00005
                    if receiptMinimum<=lowerBound && receiptMargin<=lowerBound-rope.radius {segmentClearance=lowerBound}
                    else {segmentClearance=collider.segmentClearance(from:a,to:b)}
                } else {segmentClearance=collider.segmentClearance(from:a,to:b)}""")
    return s
