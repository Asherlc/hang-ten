import Foundation
import simd

struct GeometryDescriptor: Decodable {
    struct Mesh: Decodable {let vertices: [[Double]],triangles: [[Int]]}
    let collision: Mesh
}
struct GeometryFrozen: Decodable {
    let positions: [[[Double]]],weights: [[Double]],radii: [Double],restLengths: [[Double]]
    let boardHeight: Double,orientation: [Double]
}
struct GeometrySolution: Decodable {
    struct Last: Decodable {let x: [Double]}
    let last: Last
}
func decode<T: Decodable>(_ path: String, _ type: T.Type) throws -> T {
    try JSONDecoder().decode(type,from:Data(contentsOf:URL(fileURLWithPath:path)))
}
func vector(_ p: [Double]) -> SIMD3<Double> {precondition(p.count==3);return SIMD3(p[0],p[1],p[2])}
func now() -> Double {ProcessInfo.processInfo.systemUptime}
guard CommandLine.arguments.count==5 else {exit(2)}
let descriptor=try decode(CommandLine.arguments[1],GeometryDescriptor.self)
let frozen=try decode(CommandLine.arguments[2],GeometryFrozen.self)
let correction=try decode(CommandLine.arguments[3],GeometrySolution.self).last.x
guard frozen.orientation==[0,0,0,1],frozen.positions.map(\.count)==[715,715],
      frozen.weights.map(\.count)==[715,715],frozen.restLengths.map(\.count)==[714,714],
      frozen.radii==[0.0035,0.0035],correction.count==4279,correction.allSatisfy({$0.isFinite}) else {
    throw RopePhysicsError.invalid("Fixed production channel geometry input differs")
}
let buildStart=now()
let collider=try RopeTriangleCollider(mesh:RopeCollisionMesh(vertices:descriptor.collision.vertices.map(vector),
    triangles:descriptor.collision.triangles.map{SIMD3($0[0],$0[1],$0[2])}))
// Retained two U-bends. Use the upward-rounded worst retained wall envelope
// for both channels. This is slightly tighter than the earlier first-channel
// row proposal; no QP or physical acceptance is claimed by this pilot.
let channels=try [-0.063,0.063].map {x in try ExperimentUChannel(center:SIMD3(x,0.024,0.033),
    bendRadius:0.006,tubeRadius:0.0037,mouthZ:0.0658,envelope:0.000016319)}
let staticBuildSeconds=now()-buildStart
let initial=frozen.positions.map{$0.map{vector($0)-SIMD3(0,frozen.boardHeight,0)}}
var cursor=0
let displaced=initial.indices.map {r in initial[r].indices.map {i -> SIMD3<Double> in
    let delta: SIMD3<Double>
    if frozen.weights[r][i]>0 {
        delta=SIMD3(correction[cursor],correction[cursor+1],correction[cursor+2]);cursor+=3
    } else {delta = .zero}
    return initial[r][i]+delta-SIMD3(0,correction.last!,0)
}}
precondition(cursor+1==correction.count)
struct WoodRow {
    let rope: Int,a: Int,b: Int
    let ga: SIMD3<Double>,gb: SIMD3<Double>,height: Double,residual: Double
}
struct Generation {
    let rows: [WoodRow],tubePoints: Int,tubeLinks: Int,fallbackQueries: Int
}
func generate(_ tube: Bool) throws -> Generation {
    // Discovery, whole-link eligibility, per-particle restrictions and complete
    // row construction are inside the clock. Nothing scans old frozen rows.
    var rows: [WoodRow]=[],tubePoints=0,tubeLinks=0,fallbackQueries=0
    for r in initial.indices {
        let points=initial[r],required=frozen.radii[r]+0.0001,window=required+0.00005
        var selected=[Int](repeating:-1,count:points.count)
        var allowance=[Double](repeating:0,count:points.count)
        var links=[Bool](repeating:false,count:points.count-1)
        if tube {
            for i in points.indices {
                let matches=try channels.indices.filter{try channels[$0].eligible(points[i])}
                if matches.count==1 {selected[i]=matches[0]}
            }
            for i in links.indices {
                let j=selected[i]
                if j>=0,j==selected[i+1],let restriction=try channels[j].tightening(
                    length:frozen.restLengths[r][i],radius:frozen.radii[r],clearance:0.0001) {
                    links[i]=true;allowance[i]=max(allowance[i],restriction)
                    allowance[i+1]=max(allowance[i+1],restriction)
                }
            }
        }
        func original(_ a: Int,_ b: Int) {
            fallbackQueries+=1
            let contacts=collider.segmentContacts(from:points[a],to:points[b],radius:window)
            for hit in contacts where a==b || (hit.fraction>1e-6 && hit.fraction<1-1e-6) {
                let ga=hit.normal*(1-hit.fraction),gb=hit.normal*hit.fraction
                rows.append(WoodRow(rope:r,a:a,b:b,ga:ga,gb:gb,height:-hit.normal.y,
                    residual:0.00005-hit.penetrationDepth))
            }
        }
        for i in points.indices {
            if selected[i]>=0 {
                tubePoints+=1
                if let hit=try channels[selected[i]].row(points[i],radius:frozen.radii[r],clearance:0.0001,tightening:allowance[i]) {
                    rows.append(WoodRow(rope:r,a:i,b:i,ga:hit.gradient,gb:.zero,height:-hit.gradient.y,residual:hit.residual))
                }
            } else {original(i,i)}
            if i<links.count {
                if links[i] {tubeLinks+=1} else {original(i,i+1)}
            }
        }
    }
    return Generation(rows:rows,tubePoints:tubePoints,tubeLinks:tubeLinks,fallbackQueries:fallbackQueries)
}
struct Clearances {
    let values: [Double],tubeQueries: Int,fallbackQueries: Int
}
func evaluate(_ points: [[SIMD3<Double>]],tube: Bool) throws -> Clearances {
    var values: [Double]=[],tubeQueries=0,fallbackQueries=0
    values.reserveCapacity(2858)
    for rope in points {for i in rope.indices {
        for end in i..<min(i+2,rope.count) {
            var proposal: Double?
            if tube {
                for channel in channels {
                    if let value=try channel.clearance(from:rope[i],to:rope[end]) {
                        // Disjoint proposal regions only. Ambiguous matches use
                        // original authority, rather than choosing a tube.
                        if proposal != nil {proposal=nil;break}
                        proposal=value
                    }
                }
            }
            if let proposal {values.append(proposal);tubeQueries+=1}
            else {values.append(collider.segmentClearance(from:rope[i],to:rope[end]));fallbackQueries+=1}
        }
    }}
    return Clearances(values:values,tubeQueries:tubeQueries,fallbackQueries:fallbackQueries)
}
let originalStart=now(),original=try generate(false),originalSeconds=now()-originalStart
let candidateStart=now(),candidate=try generate(true),candidateSeconds=now()-candidateStart
var checks: [[String:Any]]=[]
var physicalComparison=true,woodMeritCost=true
for (label,points) in [("source",initial),("corrected",displaced)] {
    let start=now(),reference=try evaluate(points,tube:false),baselineSeconds=now()-start
    let next=now(),value=try evaluate(points,tube:true),candidateSeconds=now()-next
    precondition(reference.values.count==2858 && value.values.count==2858)
    let difference=zip(reference.values,value.values).map{$1-$0}
    let maximumDifference=difference.map(abs).max()!
    let maximumOverstatement=difference.max()!
    let incorrectClear=zip(reference.values,value.values).filter{$0<0.0034 && $1>=0.0034}.count
    let compared=maximumDifference<=0.0001 && incorrectClear==0
    physicalComparison=physicalComparison && compared
    woodMeritCost=woodMeritCost && candidateSeconds<=0.001
    checks.append(["state":label,"queries":2858,"tubeQueries":value.tubeQueries,
        "fallbackQueries":value.fallbackQueries,"originalSeconds":baselineSeconds,
        "candidateSeconds":candidateSeconds,"maximumAbsoluteClearanceDifference":maximumDifference,
        "maximumClearanceOverstatement":maximumOverstatement,"incorrectlyClearSupports":incorrectClear,
        "originalMinimum":reference.values.min()!,"candidateMinimum":value.values.min()!,
        "isolatedMeshComparisonPassed":compared,"woodMeritCostPassed":candidateSeconds<=0.001])
}
// Keep materialized row coefficients observable, not just their counts.
func checksum(_ rows: [WoodRow]) -> Double {
    rows.reduce(0){$0+$1.residual+$1.height+$1.ga.x+$1.ga.y+$1.ga.z+$1.gb.x+$1.gb.y+$1.gb.z}
}
let countPassed=candidate.rows.count<=3000,speedup=originalSeconds/candidateSeconds
let pilotPassed=countPassed && speedup>=50 && physicalComparison && woodMeritCost
let report: [String:Any]=["owner":ProcessInfo.processInfo.environment["HANGTEN_CHANNEL_GEOMETRY_OWNER"]!,
    "runtimeAdoption":false,"regionCertified":false,"physicalStepAccepted":false,
    "completeGeometryPerformanceAccepted":false,"nativeQPMeasured":false,
    "scope":"One production wood-only row-generation and two nonlinear point/full-link clearance samples. Portal, self/intercord, swept collision, other merit terms, QP, rendering and device gates excluded. Tube domains and floating formulas are proposals checked against all original signed mesh queries on these two fixed states only.",
    "staticColliderAndChannelBuildSeconds":staticBuildSeconds,
    "originalWoodRows":original.rows.count,"candidateWoodRows":candidate.rows.count,
    "originalGenerationSeconds":originalSeconds,"candidateGenerationSeconds":candidateSeconds,
    "woodGenerationSpeedup":speedup,"woodRowCountPassed":countPassed,"woodGenerationCostPassed":speedup>=50,
    "tubePoints":candidate.tubePoints,"tubeWholeLinks":candidate.tubeLinks,
    "fallbackGenerationQueries":candidate.fallbackQueries,
    "originalRowChecksum":checksum(original.rows),"candidateRowChecksum":checksum(candidate.rows),
    "clearanceChecks":checks,"isolatedMeshComparisonPassed":physicalComparison,
    "woodMeritCostPassed":woodMeritCost,"pilotPassed":pilotPassed,"measuredRepetitions":1]
let data=try JSONSerialization.data(withJSONObject:report,options:[.prettyPrinted,.sortedKeys])
try data.write(to:URL(fileURLWithPath:CommandLine.arguments[4]))
print(String(data:data,encoding:.utf8)!)
// A partial pilot never becomes a green full physics/performance gate.
exit(3)
