import Foundation
import simd

guard CommandLine.arguments.count == 5 else {exit(2)}
func read<T: Decodable>(_ type: T.Type,_ path: String) throws -> T {
    try RopeUVJSON.decode(type,data:Data(contentsOf:URL(fileURLWithPath:path)))
}
func vector(_ p: [Double]) -> SIMD3<Double> {SIMD3(p[0],p[1],p[2])}
struct TileSource: Decodable {let triangle: Int,uv: [[Double]]}
struct PatchSource: Decodable {
    let id: Int,kind: String,axis: Int,center: [Double]?,majorRadius: Double?,tiles: [TileSource],originalTriangles: [Int]
}
struct TileDocument: Decodable {let enclosureCheckpointAccepted: Bool,patches: [PatchSource]}
struct FrozenSource: Decodable {let orientation: [Double],positions: [[[Double]]],boardHeight: Double,radii: [Double]}
struct MeshSource: Decodable {let vertices: [[Double]],triangles: [[Int]]}
struct DescriptorSource: Decodable {let collision: MeshSource}
let tiles = try read(TileDocument.self,CommandLine.arguments[1]),frozen = try read(FrozenSource.self,CommandLine.arguments[2]),descriptor = try read(DescriptorSource.self,CommandLine.arguments[3])
let vertices = descriptor.collision.vertices.map(vector),faces = descriptor.collision.triangles
let useBroadPhase = ProcessInfo.processInfo.environment["HANGTEN_UV_BROAD_PHASE"] == "1"
guard tiles.enclosureCheckpointAccepted,frozen.orientation == [0,0,0,1] else {throw RopeUVError.invalidDomain}
let positions = frozen.positions.map {$0.map(vector)}
let height = frozen.boardHeight,radii = frozen.radii
guard positions.map(\.count) == [715,715] else {throw RopeUVError.invalidDomain}
struct Query {let start: SIMD3<Double>,end: SIMD3<Double>,point: SIMD3<Double>,threshold: Double}
var queries: [Query] = []
for (r,rope) in positions.enumerated() {
    for i in rope.indices {
        let p = rope[i]-SIMD3(0,height,0)
        // Original contact window r+0.10mm+0.05mm, conservatively extended
        // by the authorized0.10mm representation budget. This *extends*
        // geometric admission, and does not relax a physical clearance gate.
        let threshold = radii[r]+0.0001+0.00005+0.0001
        queries.append(Query(start:p,end:p,point:p,threshold:threshold))
        if i+1 < rope.count {
            let end = rope[i+1]-SIMD3(0,height,0)
            queries.append(Query(start:p,end:end,point:(p+end)/2,threshold:threshold))
        }
    }
}
struct Patch {
    let id: Int,kind: String,axis: Int,orth: [Int],center: SIMD3<Double>
    let major: Double,index: RopeUVIndex
    let low: SIMD3<Double>,high: SIMD3<Double>
}
let buildStart = ProcessInfo.processInfo.systemUptime
let patches = try tiles.patches.filter {$0.kind != "unsupported"}.map {p -> Patch in
    let axis = p.axis
    let source = p.tiles.map {t -> RopeUVTile in
        let uv = t.uv
        return RopeUVTile(id:t.triangle,a:SIMD2(uv[0][0],uv[0][1]),b:SIMD2(uv[1][0],uv[1][1]),c:SIMD2(uv[2][0],uv[2][1]))
    }
    var low = SIMD3<Double>(repeating:.infinity),high = SIMD3<Double>(repeating:-.infinity)
    for face in p.originalTriangles {for vertex in faces[face] {
        low = simd_min(low,vertices[vertex]);high = simd_max(high,vertices[vertex])
    }}
    guard let center = p.center else {throw RopeUVError.invalidDomain}
    return Patch(id:p.id,kind:p.kind,axis:axis,orth:(0..<3).filter {$0 != axis},
                 center:vector(center),major:p.majorRadius ?? 0,index:try RopeUVIndex(source),low:low,high:high)
}
let buildSeconds = ProcessInfo.processInfo.systemUptime-buildStart
struct Answer {let query: Int,patch: Int,skipped: Bool,hit: RopeUVHit?}
var answers: [Answer] = [];answers.reserveCapacity(queries.count*patches.count)
let queryStart = ProcessInfo.processInfo.systemUptime
for patch in patches {
    for (i,query) in queries.enumerated() {
        if useBroadPhase && !RopeUVBroadPhase.mayTouch(start:query.start,end:query.end,low:patch.low,high:patch.high,threshold:query.threshold) {
            answers.append(Answer(query:i,patch:patch.id,skipped:true,hit:nil));continue
        }
        let p = query.point-patch.center,x = p[patch.orth[0]],y = p[patch.orth[1]]
        let uv: SIMD2<Double>
        if patch.kind == "Plane" {uv = SIMD2(x,y)}
        else {
            let u = atan2(y,x)
            let v = patch.kind == "Cylinder" ? p[patch.axis]:atan2(p[patch.axis],hypot(x,y)-patch.major)
            uv = SIMD2(u,v)
        }
        answers.append(Answer(query:i,patch:patch.id,skipped:false,
            hit:patch.index.lookup(uv,periodicU:patch.kind != "Plane",periodicV:patch.kind == "Toroid")))
    }
}
let seconds = ProcessInfo.processInfo.systemUptime-queryStart
let counters = patches.map {p -> [String:Any] in
    let a = answers.filter {$0.patch == p.id}
    return ["patch":p.id,"attempts":a.count,"distanceBoundSkips":a.filter {$0.skipped}.count,"strictInteriorHits":a.filter {$0.hit != nil}.count]
}
let report: [String:Any] = ["owner":ProcessInfo.processInfo.environment["HANGTEN_PARAMETRIC_OWNER"]!,
    "runtimeAdoption":false,"scope":"One fixed native trim lookup construction/query checkpoint. Every production point/link-support and supported-patch pair is considered; optional whole-support AABB separation skips distant pairs. Admitted pairs perform point/midpoint projection and strict UV membership only. No closest-distance/normal, signedness, whole-link minimum, manifold, CCD, global solver or complete geometry timing proof.",
    "broadPhase":useBroadPhase,"pointAndMidpointCount":queries.count,"patchCount":patches.count,"attempts":answers.count,
    "trimLookupAttempts":answers.filter {!$0.skipped}.count,
    "indexBuildSeconds":buildSeconds,"projectionAndTrimLookupSeconds":seconds,"patches":counters,
    "queries":queries.map {q in ["start":[q.start.x,q.start.y,q.start.z],"end":[q.end.x,q.end.y,q.end.z],"threshold":[q.threshold]]},
    "skippedPairs":answers.filter {$0.skipped}.map {a in ["query":a.query,"patch":a.patch]},
    "hits":answers.compactMap {a -> [String:Any]? in
        guard let hit = a.hit else {return nil}
        return ["query":a.query,"patch":a.patch,"triangle":hit.tile,"chosenUV":[hit.point.x,hit.point.y]]
    }]
try JSONSerialization.data(withJSONObject:report,options:[.sortedKeys]).write(to:URL(fileURLWithPath:CommandLine.arguments[4]))
print(String(data:try JSONSerialization.data(withJSONObject:report.filter {!["hits","skippedPairs","queries"].contains($0.key)},options:[.prettyPrinted,.sortedKeys]),encoding:.utf8)!)
