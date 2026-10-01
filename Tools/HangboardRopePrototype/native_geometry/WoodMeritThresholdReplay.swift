import Foundation
import simd

struct MeritDescriptor: Decodable {
    struct Mesh: Decodable {let vertices: [[Double]],triangles: [[Int]]}
    let collision: Mesh
}
struct MeritFrozen: Decodable {
    let positions: [[[Double]]],weights: [[Double]],radii: [Double]
    let boardHeight: Double,orientation: [Double]
}
struct MeritCorrection: Decodable {
    struct Last: Decodable {let x: [Double]}
    let last: Last
}
func decode<T: Decodable>(_ path: String,_ type: T.Type) throws -> T {
    try JSONDecoder().decode(type,from:Data(contentsOf:URL(fileURLWithPath:path)))
}
func vector(_ p: [Double]) -> SIMD3<Double> {precondition(p.count==3);return SIMD3(p[0],p[1],p[2])}
func now() -> Double {ProcessInfo.processInfo.systemUptime}
guard CommandLine.arguments.count==5 else {exit(2)}
let descriptor=try decode(CommandLine.arguments[1],MeritDescriptor.self)
let frozen=try decode(CommandLine.arguments[2],MeritFrozen.self)
let correction=try decode(CommandLine.arguments[3],MeritCorrection.self).last.x
guard frozen.orientation==[0,0,0,1],frozen.positions.map(\.count)==[715,715],
      frozen.weights.map(\.count)==[715,715],frozen.radii==[0.0035,0.0035],
      correction.count==4279,correction.allSatisfy({$0.isFinite}) else {
    throw RopePhysicsError.invalid("Fixed production wood-merit source differs")
}
let buildStart=now()
let collider=try RopeTriangleCollider(mesh:RopeCollisionMesh(vertices:descriptor.collision.vertices.map(vector),
    triangles:descriptor.collision.triangles.map{SIMD3($0[0],$0[1],$0[2])}))
let buildSeconds=now()-buildStart
let initial=frozen.positions.map{$0.map{vector($0)-SIMD3(0,frozen.boardHeight,0)}}
var cursor=0
let corrected=initial.indices.map {r in initial[r].indices.map {i -> SIMD3<Double> in
    let delta: SIMD3<Double>
    if frozen.weights[r][i]>0 {delta=SIMD3(correction[cursor],correction[cursor+1],correction[cursor+2]);cursor+=3}
    else {delta = .zero}
    return initial[r][i]+delta-SIMD3(0,correction.last!,0)
}}
precondition(cursor+1==correction.count)
struct Link {let a:SIMD3<Double>,b:SIMD3<Double>,radius:Double}
struct WoodOutput {let depths:[Double],counts:[Int],violation:Double}
// Match RopeDynamicsSolver's original wood-only term exactly. No negative
// signed nearest-distance substitution for inside endpoints or crossings.
func run(_ links:[Link],indices:[Int],candidate:Bool) throws -> WoodOutput {
    var depths=[Double](repeating:0,count:links.count),counts=[Int](repeating:0,count:links.count)
    var violation=0.0
    for i in indices {
        let q=links[i]
        let hits=candidate ? try collider.screenExactWoodContacts(from:q.a,to:q.b,radius:q.radius):
            collider.segmentContacts(from:q.a,to:q.b,radius:q.radius)
        depths[i]=hits.map(\.penetrationDepth).max() ?? 0;counts[i]=hits.count
        violation+=max(0,depths[i]-1e-8)
    }
    return WoodOutput(depths:depths,counts:counts,violation:violation)
}
var retained:[([Link],[Int],WoodOutput)]=[],states:[[String:Any]]=[]
var correctness=true,floorPassed=true
for (label,points) in [("source",initial),("corrected",corrected)] {
    let links=points.indices.flatMap {r in (0..<points[r].count-1).map {i in
        Link(a:points[r][i],b:points[r][i+1],radius:frozen.radii[r]+0.0001)
    }}
    let all=Array(links.indices)
    let masks=try links.map{try collider.screenRootSeparated(from:$0.a,to:$0.b,radius:$0.radius)}
    let residual=links.indices.filter{!masks[$0]}
    let start=now(),original=try run(links,indices:all,candidate:false),originalSeconds=now()-start
    let next=now(),floor=try run(links,indices:residual,candidate:false),floorSeconds=now()-next
    // Independent original parity for every pruned link, outside both clocks.
    let parityExceptions=links.indices.filter {masks[$0] &&
        (original.counts[$0] != 0 || !collider.screenRootParityOutside(from:links[$0].a,to:links[$0].b))}.count
    let identical=zip(original.depths,floor.depths).allSatisfy{$0.bitPattern==$1.bitPattern} &&
        original.violation.bitPattern==floor.violation.bitPattern
    correctness=correctness && parityExceptions==0 && identical
    floorPassed=floorPassed && floorSeconds<=0.001
    states.append(["state":label,"links":links.count,"rootSeparatedLinks":masks.filter{$0}.count,
        "residualLinks":residual.count,"originalWoodSeconds":originalSeconds,
        "residualOriginalQuerySeconds":floorSeconds,"originalWoodViolation":original.violation,
        "floorWoodViolation":floor.violation,"residualBitIdentityPassed":identical,
        "parityOrOriginalEmptyExceptions":parityExceptions,"residualCostPassed":floorSeconds<=0.001,
        "rootSeparationMask":masks])
    retained.append((links,all,original))
}
var candidateRuns=0,candidatePassed=false
if correctness && floorPassed {
    candidatePassed=true
    for i in retained.indices {
        let (links,all,reference)=retained[i]
        let start=now(),value=try run(links,indices:all,candidate:true),seconds=now()-start
        let identical=zip(reference.depths,value.depths).allSatisfy{$0.bitPattern==$1.bitPattern} &&
            reference.violation.bitPattern==value.violation.bitPattern
        candidatePassed=candidatePassed && identical && seconds<=0.001;candidateRuns+=1
        states[i]["candidateWoodSeconds"]=seconds;states[i]["candidateBitIdentityPassed"]=identical
    }
}
let bounds=collider.screenRootBounds()
let report:[String:Any]=["owner":ProcessInfo.processInfo.environment["HANGTEN_WOOD_MERIT_OWNER"]!,
    "runtimeAdoption":false,"physicalStepAccepted":false,"completeMeritPerformanceAccepted":false,
    "completeGeometryPerformanceAccepted":false,"clearanceReplacement":false,"tubeUsed":false,
    "staticColliderBuildSeconds":buildSeconds,"states":states,"candidateRuns":candidateRuns,
    "fixedResidualCostGateSeconds":0.001,"correctnessPassed":correctness,
    "residualCostPassed":floorPassed,"woodMeritDiscriminatorPassed":candidatePassed,
    "reason":!correctness ? "original output/parity mismatch; stop":!floorPassed ? "residual original-query floor exceeds1ms; stop before candidate timing":"conditional candidate completed",
    "rootMinimum":[bounds.0.x,bounds.0.y,bounds.0.z],"rootMaximum":[bounds.1.x,bounds.1.y,bounds.1.z],
    "scope":"One original wood-penalty control and residual-query floor per fixed state, links only, exact unchanged max original manifold depth and10nm tolerance. Conditional candidate only if both floors<=1ms and correctness passes. Source transform/query packing, root masks and static collider outside floor/control clocks; root masks included in conditional candidate. No other merit terms, generation, exactpositiveclearance, CCD, QP, fullstep/device or adoption proof."]
let data=try JSONSerialization.data(withJSONObject:report,options:[.prettyPrinted,.sortedKeys])
try data.write(to:URL(fileURLWithPath:CommandLine.arguments[4]))
var displayed=report
displayed["states"]=states.map {x -> [String:Any] in var v=x;v.removeValue(forKey:"rootSeparationMask");return v}
print(String(data:try JSONSerialization.data(withJSONObject:displayed,options:[.prettyPrinted,.sortedKeys]),encoding:.utf8)!)
exit(3)
