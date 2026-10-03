import Dispatch
private final class RopeSweepBatch:@unchecked Sendable {
    let values:UnsafeMutablePointer<Bool>
    let count:Int
    init(_ count:Int) {self.count=count;values = .allocate(capacity:count);values.initialize(repeating:true,count:count)}
    deinit {values.deinitialize(count:count);values.deallocate()}
}
extension RopeTriangleCollider {
    func sweepChainIsClear(previous:RopeSimulationState,next:RopeSimulationState,rope r:Int,clearances:[Double]?,globalClearance:Double?)->Bool {
        let chain=next.ropes[r],old=previous.ropes[r],links=chain.restLengths.count
        let radius=chain.radius-0.00005
        let angle=2*acos(min(1,abs(simd_dot(previous.orientation.vector,next.orientation.vector))))
        func deviation(_ i:Int)->Double {
            if chain.attachments[i] != nil {return 0}
            return RopeMotionSweep.rotationalDeviation(start:old.positions[i]-SIMD3(0,previous.boardHeight,0),
                end:chain.positions[i]-SIMD3(0,next.boardHeight,0),angle:angle)
        }
        let output=RopeSweepBatch(links),jobs=links>=64 ? 4:1,chunk=(links+jobs-1)/jobs
        DispatchQueue.concurrentPerform(iterations:jobs) {job in
            for i in min(links,job*chunk)..<min(links,(job+1)*chunk) {
                let a=previous.boardPoint(old.positions[i]),b=previous.boardPoint(old.positions[i+1])
                let nextA=next.boardPoint(chain.positions[i]),nextB=next.boardPoint(chain.positions[i+1])
                let movement=max(simd_distance(a,nextA),simd_distance(b,nextB))
                let curveDeviation=max(deviation(i),deviation(i+1))
                let clearance=clearances?[i] ?? globalClearance ?? segmentClearance(from:a,to:b)
                if movement+curveDeviation<=clearance-radius {continue}
                output.values[i]=sweptSegmentContact(previousStart:a,previousEnd:b,start:nextA,end:nextB,radius:radius+curveDeviation)==nil
            }
        }
        return (0..<links).allSatisfy{output.values[$0]}
    }
}
