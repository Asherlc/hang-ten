// Required full-output narrow-phase corpus. Original board parity is packed once
// for both variants; it is not included in this kernel-only time and not a step claim.
struct RegionQuery {
    let step:Int
    let start:SIMD3<Double>,end:SIMD3<Double>
    let startInside:Bool,endInside:Bool
}
let corpusPath=".context/strong-owl-live-physics-coplanar-query-5a12d1ee2-chronological-corpus/native/result.json"
let corpus=try JSONSerialization.jsonObject(with:Data(contentsOf:URL(fileURLWithPath:corpusPath))) as! [String:Any]
var queries:[RegionQuery]=[]
for step in [1,6,109,140,493] {
    let data=(corpus["steps"] as! [[String:Any]]).first{$0["step"] as! Int==step}!
    for q in (data["census"] as! [String:Any])["examples"] as! [[String:Any]] {
        let a=q["start"] as! [Double],b=q["end"] as! [Double],p=SIMD3(a[0],a[1],a[2]),s=SIMD3(b[0],b[1],b[2])
        queries.append(RegionQuery(step:step,start:p,end:s,startInside:collider.queryParity(p),endInside:collider.queryParity(s)))
    }
}
func evaluateRegions(_ enabled:Bool)->(Double,[[[RopeSegmentContact]]],RopePlanarWork) {
    var outputs:[[[RopeSegmentContact]]]=[],work=RopePlanarWork()
    let start=ProcessInfo.processInfo.systemUptime
    for q in queries {
        let result=collider.fusedContactEvaluation(from:q.start,to:q.end,rowRadius:(0.0035+0.0001)+0.00005,
            meritRadius:0.0035+0.0001,startInside:q.startInside,endInside:q.endInside,planarRegionExperiment:enabled)
        outputs.append(result.hits)
        work.calls += result.regionWork.calls;work.boundaryPairs += result.regionWork.boundaryPairs;work.fallbacks += result.regionWork.fallbacks
        // Full outputs are retained, including normals/fractions. Required minima are consumed inside the clock.
        _ = result.hits.map{$0.map{$0.penetrationDepth}.max() ?? 0}
    }
    return (ProcessInfo.processInfo.systemUptime-start,outputs,work)
}
func validateRegions(_ a:[[[RopeSegmentContact]]],_ b:[[[RopeSegmentContact]]])throws->Double {
    var maximum=0.0
    guard a.count==b.count else {throw RopePhysicsError.invalid("region corpus length")}
    for i in a.indices {for query in 0..<4 {
        let original=a[i][query].map{$0.penetrationDepth}.max() ?? 0,candidate=b[i][query].map{$0.penetrationDepth}.max() ?? 0
        let error=abs(original-candidate);maximum=max(maximum,error)
        guard error<=1e-9 else {
            result["pendingMismatch"]=["index":i,"step":queries[i].step,"query":query,"originalDepth":original,"candidateDepth":candidate]
            throw RopePhysicsError.invalid("planar union depth within1nm")
        }
        for hit in b[i][query] {
            guard hit.fraction.isFinite,hit.penetrationDepth.isFinite,[hit.normal,hit.surfacePoint,hit.centerlinePoint].allSatisfy({$0.x.isFinite && $0.y.isFinite && $0.z.isFinite}) else {
                throw RopePhysicsError.invalid("region finite full output")
            }
        }
    }}
    return maximum
}
do {
    try planarRegionFixtures()
    let a=evaluateRegions(false),b=evaluateRegions(true)
    result=["owner":"strong-owl-live-physics","adopted":false,"scope":"fixed nonempty full-output narrowphase corpus, parity packing excluded, no step or device claim",
        "queries":queries.count,"insideQueries":queries.filter{$0.startInside || $0.endInside}.count,
        "regionCalls":b.2.calls,"boundaryPairs":b.2.boundaryPairs,"wholePatchFallbacks":b.2.fallbacks,
        "maximumDepthDifferenceMeters":try validateRegions(a.1,b.1)]
    for iteration in 0..<7 {
        let a:(Double,[[[RopeSegmentContact]]],RopePlanarWork),b:(Double,[[[RopeSegmentContact]]],RopePlanarWork)
        if iteration%2==0 {a=evaluateRegions(false);b=evaluateRegions(true)} else {b=evaluateRegions(true);a=evaluateRegions(false)}
        _ = try validateRegions(a.1,b.1)
        pairs.append(["originalSeconds":a.0,"candidateSeconds":b.0,"ratio":b.0/a.0])
    }
    result["accuracyPass"]=true
    let median=pairs.map{$0["ratio"] as! Double}.sorted()[3];result["medianRatio"]=median
    try persist(nil)
    guard median<=2.0/3 else {throw RopePhysicsError.invalid("planar full-output corpus ratio<=2/3")}
    result["queryScreenPass"]=true;try persist(nil);print("PASS planar full-output corpus",queries.count,"median",median)
} catch {try persist(String(describing:error));print("FAIL planar full-output corpus",error);exit(2)}
