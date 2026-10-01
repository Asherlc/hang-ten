import Foundation
import CryptoKit
import simd

struct CapturedQuery {
    let mesh: Int, method: String, stage: String
    let points: [SIMD3<Double>]
    let radius: Double
}
struct GeometryOutput {
    var contacts: [RopeSegmentContact] = []
    var scalar: Double = 0
}
func same(_ a: GeometryOutput, _ b: GeometryOutput) -> Bool {
    guard a.scalar == b.scalar, a.contacts.count == b.contacts.count else { return false }
    return zip(a.contacts,b.contacts).allSatisfy { x,y in
        x.centerlinePoint == y.centerlinePoint && x.surfacePoint == y.surfacePoint && x.normal == y.normal && x.fraction == y.fraction && x.penetrationDepth == y.penetrationDepth && x.timeOfImpact == y.timeOfImpact
    }
}
func stats(_ values: [Double]) -> [String: Double] {
    let sorted = values.sorted()
    return ["mean":values.reduce(0,+)/Double(values.count),"p95":sorted[Int(ceil(Double(values.count)*0.95))-1],"minimum":sorted.first!]
}
func now() -> Double { ProcessInfo.processInfo.systemUptime }
let arguments = CommandLine.arguments
guard arguments.count == 3 else { throw RopePhysicsError.invalid("Expected fixed corpus and output") }
let inputData = try Data(contentsOf: URL(fileURLWithPath:arguments[1]))
let input = try JSONSerialization.jsonObject(with:inputData) as! [String:Any]
let meshes = input["meshes"] as! [[String:Any]]
let colliders = try meshes.map { m -> RopeTriangleCollider in
    let vertices = (m["vertices"] as! [[Double]]).map { SIMD3<Double>($0[0],$0[1],$0[2]) }
    let triangles = (m["triangles"] as! [[Int]]).map { SIMD3<Int>($0[0],$0[1],$0[2]) }
    return try RopeTriangleCollider(mesh:RopeCollisionMesh(vertices:vertices,triangles:triangles))
}
let queries = (input["queries"] as! [[String:Any]]).map { q in
    CapturedQuery(mesh:q["mesh"] as! Int,method:q["method"] as! String,stage:q["stage"] as! String,
        points:(q["points"] as! [[Double]]).map { SIMD3<Double>($0[0],$0[1],$0[2]) },radius:q["radius"] as? Double ?? 0)
}
guard queries.count == 6167, colliders.count == 3,
      queries.filter({$0.method == "segmentContacts"}).count == 5440,
      queries.allSatisfy({$0.mesh >= 0 && $0.mesh < colliders.count && ["segmentContacts","segmentClearance","signedDistance"].contains($0.method)}) else { throw RopePhysicsError.invalid("Fixed healthy corpus shape") }
let selected = queries.indices.filter { queries[$0].method == "segmentContacts" }
guard selected.allSatisfy({queries[$0].mesh == 0}) else { throw RopePhysicsError.invalid("Unexpected contact mesh") }
let tree = try colliders[0].screenTree()
let stream = try BVHStream(nodes:tree.0,faces:tree.1,triangles:tree.2)
func evaluate(_ candidateFaces: [[Int]]?) -> [GeometryOutput] {
    var next = 0, output: [GeometryOutput] = []; output.reserveCapacity(queries.count)
    for q in queries {
        let collider = colliders[q.mesh]
        switch q.method {
        case "segmentContacts":
            let hits: [RopeSegmentContact]
            if let candidateFaces {
                hits = collider.screenSegmentContacts(from:q.points[0],to:q.points[1],radius:q.radius,faces:candidateFaces[next])
            } else { hits = collider.segmentContacts(from:q.points[0],to:q.points[1],radius:q.radius) }
            next += 1; output.append(GeometryOutput(contacts:hits))
        case "segmentClearance": output.append(GeometryOutput(scalar:collider.segmentClearance(from:q.points[0],to:q.points[1])))
        default: output.append(GeometryOutput(scalar:collider.signedDistance(at:q.points[0])))
        }
    }
    return output
}
var baseline: [Double] = [], accelerated: [Double] = [], gpu: [Double] = [], broadphase: [Double] = [], narrowphase: [Double] = []
var reference: [GeometryOutput] = [], candidateCount = 0, checksum = 0
// Same complete fixed query corpus and outputs for each run. No result cache.
// Static source mesh/BVH/pipeline setup is outside both steady-state clocks.
for iteration in 0..<60 {
    let start = now(), output = evaluate(nil), elapsed = now()-start
    if iteration == 0 { reference = output }
    if iteration >= 10 { baseline.append(elapsed) }
    checksum += output.reduce(0) { $0+$1.contacts.count }
}
for iteration in 0..<60 {
    let start = now()
    let packed = try selected.map { i in try BVHQuery(queries[i].points,queries[i].radius) }
    let faces = try stream.candidates(packed), split = now()
    let output = evaluate(faces), end = now()
    if iteration == 0 || iteration == 59 {
        guard zip(reference,output).allSatisfy({same($0,$1)}) else {
            let mismatches = queries.indices.filter { !same(reference[$0],output[$0]) }
            throw RopePhysicsError.invalid("Exact query output mismatch: \(mismatches.prefix(20))")
        }
    }
    if iteration >= 10 {
        accelerated.append(end-start); broadphase.append(split-start); narrowphase.append(end-split); gpu.append(stream.gpuSeconds)
    }
    candidateCount = stream.candidateCount; checksum += output.reduce(0) { $0+$1.contacts.count }
}
let speedup = stats(baseline)["p95"]! / stats(accelerated)["p95"]!
let owner = ProcessInfo.processInfo.environment["HANGTEN_GEOMETRY_SCREEN_OWNER"]!
let report: [String:Any] = ["owner":owner,"runtimeAdoption":false,
    "scope":"All 6167 frozen healthy geometry queries; GPU conservative integer BVH, CPU exact witnesses/manifolds/classification and unchanged metric queries. No solver, CCD, full-step or device proof.",
    "inputSHA256":SHA256.hash(data:inputData).map {String(format:"%02x",$0)}.joined(),
    "queryCount":queries.count,"acceleratedQueryCount":selected.count,"candidateCount":candidateCount,
    "device":stream.deviceName,"baselineSeconds":stats(baseline),"completeGeometrySeconds":stats(accelerated),
    "packingTraversalCompactionReadbackSeconds":stats(broadphase),"exactCPUOutputSeconds":stats(narrowphase),"gpuCommandSeconds":stats(gpu),
    "p95Speedup":speedup,"requiredCompleteGeometrySpeedup":50,"performancePassed":speedup >= 50,
    "strictOutputEqualityPassed":true,"comparedQueryOutputs":queries.count*2,"warmups":10,"measuredRepetitions":50,"checksum":checksum,
    "limits":["Only retained healthy coarse step corpus; no jug geometry corpus","No affine-row generation, CCD, convergence or CAD tessellation bound","Static mesh/BVH/pipeline creation excluded equally from steady-state query clocks","Shared host, not iPhone 16 Pro"]]
let data = try JSONSerialization.data(withJSONObject:report,options:[.prettyPrinted,.sortedKeys])
try data.write(to:URL(fileURLWithPath:arguments[2]))
print(String(data:data,encoding:.utf8)!)
exit(speedup >= 50 ? 0 : 3)
