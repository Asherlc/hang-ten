func checkFPBounds() throws {
    func lower(_ p:SIMD3<Double>,_ q:SIMD3<Double>,_ a:SIMD3<Double>,_ b:SIMD3<Double>)->Double? {
        guard let pair=RopeTriangleCollider.fpPairBox(p,q) else{return nil}
        return RopeTriangleCollider.fpEdgeSquaredBound(low:pair.0,high:pair.1,a:a,b:b)
    }
    let a=SIMD3<Double>(0.75,0,0),b=SIMD3<Double>(0.1,0,0),rounded=a+(b-a)
    let p=rounded,q=rounded+SIMD3<Double>(-0.01,0.005,0)
    let original=RopeTriangleCollider.segmentPair(p,q,a,b)
    let square=simd_length_squared(original.0-original.1)
    let rawSeparation=simd_max(simd_max(simd_min(a,b)-simd_max(p,q),simd_min(p,q)-simd_max(a,b)),SIMD3<Double>(repeating:0))
    let unsafe=simd_length_squared(rawSeparation),threshold=unsafe/2
    guard square==0,unsafe>0,lower(p,q,a,b)!<threshold else {throw RopePhysicsError.invalid("rounded endpoint RED did not discriminate")}
    let tieP=SIMD3<Double>(0,1,0),tieQ=SIMD3<Double>(1,1,0),tieA=SIMD3<Double>(0,0,0),tieB=SIMD3<Double>(1,0,0)
    guard lower(tieP,tieQ,tieA,tieB)==1,lower(tieP,tieQ,tieA,tieB)!<Double(1).nextUp else {throw RopePhysicsError.invalid("strict comparison tie GREEN")}
    let huge=Double.greatestFiniteMagnitude
    guard RopeTriangleCollider.fpPairBox(SIMD3(huge,0,0),SIMD3(-huge,0,0))==nil else {throw RopePhysicsError.invalid("nonfinite interpolation must fallback")}
    var random:UInt64=0x3259248757
    func sample()->Double {random=random &* 6364136223846793005 &+ 1442695040888963407;return Double(random>>11)/Double(UInt64(1)<<53)*2-1}
    var checked=0
    for scale in [1e-12,1e-9,1e-6,1e-3,0.1,1,100,1e8,1e100] {
        for index in 0..<2000 {
            func vector()->SIMD3<Double> {SIMD3(sample()*scale,sample()*scale,sample()*scale)}
            let p=vector(),a=vector(),q=index%11==0 ? p:vector(),b=index%13==0 ? a:vector()
            let hit=RopeTriangleCollider.segmentPair(p,q,a,b),squared=simd_length_squared(hit.0-hit.1)
            if let bound=lower(p,q,a,b),squared.isFinite {
                guard bound<=squared else {throw RopePhysicsError.invalid("computed witness box lowerbound exceeded original")}
                checked+=1
            }
        }
    }
    print("PASS computed witness box fixtures",checked,"finite cases, rounded-endpoint RED, tie and nonfinite fallback")
}
try checkFPBounds()
