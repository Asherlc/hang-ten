import Foundation
import simd
import Darwin

let root=URL(fileURLWithPath:CommandLine.arguments[1])
let data=try Data(contentsOf:URL(fileURLWithPath:"Hangboards/clavellium-training-block/assets/primary.physics.json"))
let raw=try JSONSerialization.jsonObject(with:data) as! [String:Any]
let input=try RopePhysicsDescriptor.decode(data).validated(modelSHA256:raw["modelSHA256"] as! String)
let collider=try RopeTriangleCollider(input:input)
let corpus=try decodeCheckpointJSON(Data(contentsOf:URL(fileURLWithPath:CommandLine.arguments[2])))
struct Query {
    let start:SIMD3<Double>,end:SIMD3<Double>
    let link:Int,batch:Int
    let faces:[(Int,Int)]
}
func queries(_ step:Int)->[Query] {
    let value=(corpus["steps"] as! [[String:Any]]).first{$0["step"] as! Int==step}!
    let census=value["census"] as! [String:Any]
    return (census["examples"] as! [[String:Any]]).map {q in
        let a=q["start"] as! [Double],b=q["end"] as! [Double]
        return Query(start:SIMD3(a[0],a[1],a[2]),end:SIMD3(b[0],b[1],b[2]),
            link:q["link"] as! Int,batch:q["batch"] as! Int,
            faces:(q["faces"] as! [[Int]]).map{($0[0],$0[1])})
    }.sorted{($0.batch,$0.link)<($1.batch,$1.link)}
}
let previous=queries(139),current=queries(140)
let meritRadius=0.0035+0.0001,radius=meritRadius+0.00005
// Serial replay makes chronology explicit. It is not a complete parallel engine clock.
func run(_ values:[Query],cache:inout [Int:RopeSeparationHint],mode:Int,verify:Bool)throws->[String:Int] {
    var faces=0,rejections=0,misses=0,refreshes=0,rayBlocks=0
    for q in values {
        for (face,mask) in q.faces {
            faces+=1
            let key=q.link*input.collision.triangles.count+face
            let hint=cache[key]
            if mode != 0 && hint==nil {misses+=1}
            var rejected=mode != 0 && (hint?.separates(q.start,q.end,radius) ?? false)
#if !SCREEN_EDGE_ONLY
            if rejected && collider.directionRayHit(from:q.start,to:q.end,face:face,mask:mask) {rejected=false;rayBlocks+=1}
#endif
            if rejected {rejections+=1}
            // Mode1 retains ALL original arithmetic and validates proposals.
            // Mode2 is a non-adoptable cost ceiling after mode1's validation.
#if !SCREEN_EDGE_ONLY
            if mode==2 && rejected {continue}
#endif
            let result=collider.directionFace(from:q.start,to:q.end,rowRadius:radius,meritRadius:meritRadius,face:face,mask:mask,trackHint:mode != 0 && !rejected,
                omitEdges:mode==2 && rejected)
            if verify && rejected {
#if SCREEN_EDGE_ONLY
                let omitted=collider.directionFace(from:q.start,to:q.end,rowRadius:radius,meritRadius:meritRadius,face:face,mask:mask,trackHint:false,omitEdges:true)
                guard result.bits==omitted.bits else {throw RopePhysicsError.invalid("proposal omitted original edge witness/receipt")}
#else
                if !result.empty {throw RopePhysicsError.invalid("proposal omitted original face witness/receipt")}
#endif
            }
            if verify && mode != 0 {
                let original=collider.directionFace(from:q.start,to:q.end,rowRadius:radius,meritRadius:meritRadius,face:face,mask:mask,trackHint:false)
                guard original.bits==result.bits else {throw RopePhysicsError.invalid("hint bookkeeping changed original arithmetic")}
            }
            if mode != 0 && !rejected,let n=result.direction {
                let f=input.collision.triangles[face],v=input.collision.vertices
                if let fresh=RopeSeparationHint(n,v[f.x],v[f.y],v[f.z]) {cache[key]=fresh;refreshes+=1}
            }
        }
    }
    return ["faces":faces,"proposedRejections":rejections,"firstUseMisses":misses,"refreshes":refreshes,"rayBlocks":rayBlocks,"cacheEntries":cache.count]
}
var cold=[Int:RopeSeparationHint]()
let coldCoverage=try run(current,cache:&cold,mode:1,verify:true)
var warm=[Int:RopeSeparationHint]()
let training=try run(previous,cache:&warm,mode:1,verify:true)
let warmInput=warm
let warmCoverage=try run(current,cache:&warm,mode:1,verify:true)
var pairs:[[String:Any]]=[]
for i in 0..<7 {
    var base=[Int:RopeSeparationHint](),candidate=warmInput
    var originalSeconds=0.0,ceilingSeconds=0.0
    func baseline()throws {let t=ProcessInfo.processInfo.systemUptime;_ = try run(current,cache:&base,mode:0,verify:false);originalSeconds=ProcessInfo.processInfo.systemUptime-t}
    func ceiling()throws {let t=ProcessInfo.processInfo.systemUptime;_ = try run(current,cache:&candidate,mode:2,verify:false);ceilingSeconds=ProcessInfo.processInfo.systemUptime-t}
    if i%2==0 {try baseline();try ceiling()} else {try ceiling();try baseline()}
    pairs.append(["run":i,"originalKernelSeconds":originalSeconds,"ceilingKernelSeconds":ceilingSeconds,"ratio":ceilingSeconds/originalSeconds])
}
let ratios=pairs.map{$0["ratio"] as! Double}.sorted(),median=ratios[3]
#if SCREEN_EDGE_ONLY
let kind="edge-only interpolation envelope; original point and ray kernels retained"
#else
let kind="whole-face hint oracle; rounded barycentric envelope unproved"
#endif
let result:[String:Any]=["owner":"strong-owl-live-physics","adopted":false,"kind":kind,
    "scope":"chronological hint coverage with every original face checked; non-adoptable serial predecoded corpus cost ceiling, not complete-step/device timing",
    "coldCoverage":coldCoverage,"training139":training,"warmCoverage":warmCoverage,
    "pairedRuns":pairs,"medianKernelRatio":median,"fixedMaximumKernelRatio":0.5,
    "necessaryCostScreenPassed":median<=0.5,"proposalValidationPassed":true,
    "limitations":["No general computed triangleClosest barycentric envelope proof.","Ray branch retained on every proposed skip.","Dictionary lookup, fresh support tests and refresh are timed; corpus decoding and previous-step training are outside the clock.","BVH discovery, original merge/row/solver costs, parallel execution, complete trajectory and simulator/video not measured."]]
try JSONSerialization.data(withJSONObject:result,options:[.prettyPrinted,.sortedKeys]).write(to:root.appendingPathComponent("result.json"))
print("coverage",warmCoverage,"kernel ratio",median)
if median>0.5 {exit(2)}
