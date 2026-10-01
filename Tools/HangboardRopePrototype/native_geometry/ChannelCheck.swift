import Foundation
import simd

// Original-mesh authority for one experimental frozen correction. Never an
// accepted nonlinear frame, a region certificate, or a device timing result.
guard CommandLine.arguments.count == 6 else {exit(2)}
func read(_ path:String)throws->[String:Any] {
    try JSONDecoder().decode(ChannelJSON.self,from:Data(contentsOf:URL(fileURLWithPath:path))).value as! [String:Any]
}
func vector(_ p:[Double])->SIMD3<Double> {SIMD3(p[0],p[1],p[2])}
let descriptor=try read(CommandLine.arguments[1]),frozen=try read(CommandLine.arguments[2])
let candidate=try read(CommandLine.arguments[3]),control=try read(CommandLine.arguments[4])
let mesh=descriptor["collision"] as! [String:Any]
let collider=try RopeTriangleCollider(mesh:RopeCollisionMesh(vertices:(mesh["vertices"] as! [[Double]]).map(vector),
    triangles:(mesh["triangles"] as! [[Double]]).map{SIMD3(Int($0[0]),Int($0[1]),Int($0[2]))}))
let p=(frozen["positions"] as! [[[Double]]]).map{$0.map(vector)}
let weights=frozen["weights"] as! [[Double]],radii=frozen["radii"] as! [Double]
let rest=frozen["restLengths"] as! [[Double]],height=frozen["boardHeight"] as! Double
guard (frozen["orientation"] as! [Double]) == [0,0,0,1],p.map(\.count)==[715,715] else {exit(2)}
let x=(candidate["last"] as! [String:Any])["x"] as! [Double]
let oldX=(control["last"] as! [String:Any])["x"] as! [Double]
guard x.count==oldX.count,x.allSatisfy({$0.isFinite}),oldX.allSatisfy({$0.isFinite}) else {exit(2)}
func evaluate(_ correction:[Double])->[String:Any] {
    var offset=0,points:[[SIMD3<Double>]]=[],minimum=Double.infinity,margin=Double.infinity
    var strain=0.0,lengthError=0.0,sweepBlocks=0,queries=0
    for r in p.indices {
        var q:[SIMD3<Double>]=[]
        for i in p[r].indices {
            let delta:SIMD3<Double>
            if weights[r][i]>0 {delta=SIMD3(correction[offset],correction[offset+1],correction[offset+2]);offset+=3}
            else {delta = .zero}
            q.append(p[r][i]+delta-SIMD3(0,height+correction.last!,0))
        }
        points.append(q)
        var length=0.0
        for i in q.indices {
            let d=collider.segmentClearance(from:q[i],to:q[i]);queries+=1
            minimum=min(minimum,d);margin=min(margin,d-radii[r])
            if i+1<q.count {
                let d=collider.segmentClearance(from:q[i],to:q[i+1]);queries+=1
                minimum=min(minimum,d);margin=min(margin,d-radii[r])
                let l=simd_distance(q[i],q[i+1]);length+=l
                strain=max(strain,abs(l/rest[r][i]-1))
                if collider.sweptSegmentContact(previousStart:p[r][i]-SIMD3(0,height,0),
                    previousEnd:p[r][i+1]-SIMD3(0,height,0),start:q[i],end:q[i+1],radius:radii[r]) != nil {sweepBlocks+=1}
            }
        }
        lengthError=max(lengthError,abs(length-rest[r].reduce(0,+)))
    }
    precondition(offset+1==correction.count)
    return ["originalPointAndWholeLinkQueries":queries,"minimumSegmentClearance":minimum,
            "minimumClearanceMargin":margin,"maximumLocalStrain":strain,
            "maximumTotalLengthError":lengthError,"originalSweepBlocks":sweepBlocks,
            "isolatedWoodClearanceAccepted":margin >= -0.0001,
            "strictWoodClearanceAccepted":margin >= -0.00005]
}
let checked=evaluate(x),oldChecked=evaluate(oldX)
let difference=zip(x,oldX).map{abs($0-$1)}.max()!
let result:[String:Any]=["owner":ProcessInfo.processInfo.environment["HANGTEN_CHANNEL_OWNER"]!,
    "runtimeAdoption":false,"candidate":checked,"originalFacetControl":oldChecked,
    "maximumPrimalDifference":difference,"primalDifferenceAccepted":difference<=0.0001,
    "scope":"One frozen Newton correction checked with original signed point/full-link and sweep queries. Sweep blocks and strain are reported for both candidate and facet control; neither is a complete nonlinear accepted timestep. No region/topology/CCD-acceptance or runtime proof."]
try JSONSerialization.data(withJSONObject:result,options:[.prettyPrinted,.sortedKeys]).write(to:URL(fileURLWithPath:CommandLine.arguments[5]))
print(String(data:try JSONSerialization.data(withJSONObject:result,options:[.prettyPrinted,.sortedKeys]),encoding:.utf8)!)

private struct ChannelJSON:Decodable {
    let value:Any
    init(from decoder:Decoder)throws {
        let c=try decoder.singleValueContainer()
        if c.decodeNil(){value=NSNull()}
        else if let v=try? c.decode(Bool.self){value=v}
        else if let v=try? c.decode(Double.self){value=v}
        else if let v=try? c.decode(String.self){value=v}
        else if let v=try? c.decode([ChannelJSON].self){value=v.map{$0.value}}
        else{value=try c.decode([String:ChannelJSON].self).mapValues{$0.value}}
    }
}
