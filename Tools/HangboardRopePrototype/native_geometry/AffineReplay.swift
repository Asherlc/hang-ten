import Foundation
import simd

let arguments = CommandLine.arguments
guard arguments.count == 6,let runs = Int(arguments[5]),[1,50].contains(runs) else {exit(2)}
func read(_ path: String) throws -> [String:Any] {
    try JSONSerialization.jsonObject(with:Data(contentsOf:URL(fileURLWithPath:path))) as! [String:Any]
}
func vector(_ p: [Double]) -> SIMD3<Double> {SIMD3(p[0],p[1],p[2])}
func now() -> Double {ProcessInfo.processInfo.systemUptime}
let corpus = try read(arguments[1]),frozen = try read(arguments[2]),solution = try read(arguments[3])
let mesh = (corpus["meshes"] as! [[String:Any]])[0]
let collider = try RopeTriangleCollider(mesh:RopeCollisionMesh(
    vertices:(mesh["vertices"] as! [[Double]]).map(vector),
    triangles:(mesh["triangles"] as! [[Int]]).map {SIMD3($0[0],$0[1],$0[2])}))
let positions = (frozen["positions"] as! [[[Double]]]).map {$0.map(vector)}
let weights = frozen["weights"] as! [[Double]],radii = frozen["radii"] as! [Double]
let attachments = frozen["attachments"] as! [[String:[Double]]]
let height = frozen["boardHeight"] as! Double
let q = frozen["orientation"] as! [Double]
let orientation = simd_quatd(ix:q[0],iy:q[1],iz:q[2],r:q[3])
let last = solution["last"] as! [String:Any],x = last["x"] as! [Double]
let thresholdRegions = ProcessInfo.processInfo.environment["HANGTEN_AFFINE_GEOMETRY_METHOD"] == "regions"
let multipliers = last["mu"] as! [Double]
guard positions.map(\.count) == [715,715],weights.map(\.count) == [715,715],
      abs(simd_length(orientation.vector)-1) < 1e-8,
      x.allSatisfy({$0.isFinite}),multipliers.allSatisfy({$0.isFinite && $0 >= 0}) else {
    throw RopePhysicsError.invalid("Production frozen geometry/solution shape")
}
var offset = 0
let corrections = positions.indices.map {r in positions[r].indices.map {i -> SIMD3<Double> in
    if weights[r][i] > 0 {
        defer {offset += 3}
        return SIMD3(x[offset],x[offset+1],x[offset+2])
    }
    return attachments[r][String(i)] == nil ? .zero:SIMD3(0,x.last!,0)
}}
guard offset+1 == x.count else {throw RopePhysicsError.invalid("Original material variable mapping")}
struct Query {
    let rope: Int,a: Int,b: Int
    let start: SIMD3<Double>,end: SIMD3<Double>,da: SIMD3<Double>,db: SIMD3<Double>
    let required: Double
}
func queries() -> [Query] {
    var result: [Query] = [];result.reserveCapacity(2858)
    for r in positions.indices {for i in positions[r].indices {
        let p = orientation.inverse.act(positions[r][i]-SIMD3(0,height,0))
        let d = orientation.inverse.act(corrections[r][i]-SIMD3(0,x.last!,0))
        result.append(Query(rope:r,a:i,b:i,start:p,end:p,da:d,db:d,required:radii[r]+0.0001))
        if i+1 < positions[r].count {
            result.append(Query(rope:r,a:i,b:i+1,start:p,
                end:orientation.inverse.act(positions[r][i+1]-SIMD3(0,height,0)),da:d,
                db:orientation.inverse.act(corrections[r][i+1]-SIMD3(0,x.last!,0)),required:radii[r]+0.0001))
        }
    }}
    return result
}
func contacts(_ query: Query) -> [RopeSegmentContact] {
    collider.segmentContacts(from:query.start,to:query.end,radius:query.required+0.00005).filter {
        query.a == query.b || ($0.fraction > 1e-6 && $0.fraction < 1-1e-6)
    }
}
struct Output {let clear: [Bool],contacts: [[RopeSegmentContact]]}
func evaluate(_ certified: Bool) throws -> Output {
    var flags: [Bool] = [],output: [[RopeSegmentContact]] = []
    for query in queries() {
        let clear = certified ? try collider.screenAffinelyClear(from:query.start,to:query.end,
            requiredClearance:query.required,startCorrection:query.da,endCorrection:query.db,
            thresholdRegions:thresholdRegions):false
        flags.append(clear);output.append(clear ? []:contacts(query))
    }
    return Output(clear:flags,contacts:output)
}
var original: Output!,candidate: Output!,baseline: [Double] = [],accelerated: [Double] = []
for _ in 0..<runs {
    let start = now();let value = try evaluate(false);baseline.append(now()-start);original = value
}
for _ in 0..<runs {
    let start = now();let value = try evaluate(true);accelerated.append(now()-start);candidate = value
}
let inputs = queries()
var certifiedRows = 0,minimumOriginalAffineGap = Double.infinity,certifiedFrozenRows = 0
for i in inputs.indices {
    if candidate.clear[i] {
        for hit in original.contacts[i] {
            let d = inputs[i].da*(1-hit.fraction)+inputs[i].db*hit.fraction
            let gap = 0.00005-hit.penetrationDepth+simd_dot(hit.normal,d)
            guard gap.isFinite && gap >= -1e-10 else {throw RopePhysicsError.invalid("Omitted original geometry row violates frozen affine inequality")}
            minimumOriginalAffineGap = min(minimumOriginalAffineGap,gap);certifiedRows += 1
        }
    } else {
        guard original.contacts[i].count == candidate.contacts[i].count,
              zip(original.contacts[i],candidate.contacts[i]).allSatisfy({a,b in
                  a.centerlinePoint == b.centerlinePoint && a.surfacePoint == b.surfacePoint &&
                  a.normal == b.normal && a.fraction == b.fraction && a.penetrationDepth == b.penetrationDepth
              }) else {throw RopePhysicsError.invalid("Uncertain geometry fallback differs from original authority")}
    }
}
let bySupport = Dictionary(uniqueKeysWithValues:inputs.indices.map {i in
    ("\(inputs[i].rope):\(inputs[i].a):\(inputs[i].b)",i)
})
var contactID = 0
for row in frozen["rows"] as! [[String:Any]] where row["contact"] as! Bool {
    defer {contactID += 1}
    let particles = row["particles"] as! [Int]
    guard (row["secondRope"] as! Int) < 0,particles.count <= 2 else {continue}
    let r = row["rope"] as! Int
    let key = "\(r):\(particles[0]):\(particles.last!)"
    guard let id = bySupport[key],candidate.clear[id] else {continue}
    // Stronger independent cross-check against the retained frozen rows,
    // including any portal rows sharing the support. Portal constraints are
    // outside this wood-only generation experiment and are never discarded.
    let gradients = (row["gradients"] as! [[Double]]).map(vector)
    var gap = row["residual"] as! Double
    for k in particles.indices where weights[r][particles[k]] > 0 {
        for axis in 0..<3 {gap += gradients[k][axis]*corrections[r][particles[k]][axis]}
    }
    gap += (row["boardGradient"] as! Double)*x.last!
    guard multipliers[contactID] == 0,gap.isFinite,gap >= -1e-10 else {
        throw RopePhysicsError.invalid("Certified support has a retained active or violated frozen row")
    }
    certifiedFrozenRows += 1
}
guard contactID == multipliers.count else {throw RopePhysicsError.invalid("Frozen source force shape")}
func percentile(_ values: [Double]) -> Double {values.sorted()[Int(ceil(0.95*Double(values.count)))-1]}
let speedup = percentile(baseline)/percentile(accelerated)
let report: [String:Any] = ["owner":ProcessInfo.processInfo.environment["HANGTEN_AFFINE_GEOMETRY_OWNER"]!,
    "runtimeAdoption":false,"method":thresholdRegions ? "threshold-regions":"original-nearest",
    "scope":"Production first frozen candidate: all point/segment wood manifold generation or original geometry affine proof with exact fallback. Original portal, self/intercord, CCD, solver and mesh are excluded; this is not a complete geometry gate.",
    "queryCount":inputs.count,"certifiedQueries":candidate.clear.filter {$0}.count,
    "originalWoodRows":original.contacts.reduce(0) {$0+$1.count},"certifiedOriginalWoodRows":certifiedRows,
    "fallbackWoodRows":candidate.contacts.reduce(0) {$0+$1.count},"independentlyCheckedFrozenSupportRows":certifiedFrozenRows,
    "minimumOriginalAffineGap":minimumOriginalAffineGap.isFinite ? minimumOriginalAffineGap:NSNull(),
    "measuredRepetitions":runs,"baselineSeconds":baseline,"preGenerationSeconds":accelerated,
    "p95Speedup":runs == 50 ? speedup:NSNull(),"singleRunSpeedup":runs == 1 ? speedup:NSNull(),
    "numericalAccepted":true,"requiredCompleteGeometrySpeedup":50,"completeGeometryPerformanceAccepted":false]
try JSONSerialization.data(withJSONObject:report,options:[.prettyPrinted,.sortedKeys]).write(to:URL(fileURLWithPath:arguments[4]))
print(String(data:try JSONSerialization.data(withJSONObject:report,options:[.prettyPrinted,.sortedKeys]),encoding:.utf8)!)
exit(3)
