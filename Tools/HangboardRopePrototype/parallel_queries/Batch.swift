import Dispatch
// Each worker owns disjoint initialized slots. concurrentPerform joins before reads/destruction.
private final class RopeContactBatchStorage:@unchecked Sendable {
    let inside:UnsafeMutablePointer<Bool>
    let results:UnsafeMutablePointer<[[RopeSegmentContact]]>
    let pointCount:Int,linkCount:Int
    init(points:Int) {
        pointCount=points;linkCount=points-1
        inside = .allocate(capacity:points);inside.initialize(repeating:false,count:points)
        results = .allocate(capacity:linkCount);results.initialize(repeating:[],count:linkCount)
    }
    deinit {inside.deinitialize(count:pointCount);inside.deallocate();results.deinitialize(count:linkCount);results.deallocate()}
}
extension RopeTriangleCollider {
    func fusedChainContacts(points:[SIMD3<Double>],rowRadius:Double,meritRadius:Double)->(points:[[RopeSegmentContact]],rows:[[RopeSegmentContact]],merits:[[RopeSegmentContact]]) {
        precondition(points.count>=2)
        let storage=RopeContactBatchStorage(points:points.count),links=points.count-1
        let jobs=links>=64 ? 4:1
        func ranges(_ count:Int,_ job:Int)->Range<Int> {let chunk=(count+jobs-1)/jobs;return min(count,job*chunk)..<min(count,(job+1)*chunk)}
        DispatchQueue.concurrentPerform(iterations:jobs) {job in
            for i in ranges(points.count,job) {storage.inside[i]=queryParity(points[i])}
        }
        DispatchQueue.concurrentPerform(iterations:jobs) {job in
            for i in ranges(links,job) {
                storage.results[i]=fusedContacts(from:points[i],to:points[i+1],rowRadius:rowRadius,meritRadius:meritRadius,
                    startInside:storage.inside[i],endInside:storage.inside[i+1])
            }
        }
        var p=Array(repeating:[RopeSegmentContact](),count:points.count),r:[[RopeSegmentContact]]=[],m:[[RopeSegmentContact]]=[]
        for i in 0..<links {
            let result=storage.results[i];p[i]=result[0];r.append(result[1]);m.append(result[2])
            if i==links-1 {p[i+1]=result[3]}
        }
        return (p,r,m)
    }
}
