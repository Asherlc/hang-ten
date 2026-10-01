
import Foundation
import simd
import Accelerate
guard CommandLine.arguments.count==4,let repetitions=Int(CommandLine.arguments[3]),(1...50).contains(repetitions) else {exit(2)}
let inputPath=CommandLine.arguments[1],outputPath=CommandLine.arguments[2]
let owner=ProcessInfo.processInfo.environment["HANGTEN_CONTACT_SCREEN_OWNER"] ?? "unknown"
let doc=try JSONDecoder().decode(DiagnosticJSON.self,from:Data(contentsOf:URL(fileURLWithPath:inputPath))).value as! [String:Any]
let raw=doc["rows"] as! [[String:Any]],weights=doc["weights"] as! [[Double]]
let positions=doc["positions"] as! [[[Double]]],prediction=doc["prediction"] as! [[[Double]]]
let tensions=doc["distanceTension"] as! [[Double]],attachments=doc["attachments"] as! [[String:[Double]]]
let epsilon=doc["regularization"] as! Double
struct Row {
 let id:Int,rope:Int,other:Int,particles:[Int],gradients:[[Double]],board:Double,residual:Double,contact:Bool
}
let rows=raw.enumerated().map {index,row in
 Row(id:index,rope:Int(row["rope"] as! Double),other:Int(row["secondRope"] as! Double),
     particles:(row["particles"] as! [Double]).map{Int($0)},gradients:row["gradients"] as! [[Double]],
     board:row["boardGradient"] as! Double,residual:row["residual"] as! Double,contact:row["contact"] as! Bool)
}
let eq=rows.indices.filter{!rows[$0].contact}
var vars=weights.map{Array(repeating:SIMD3<Int>(repeating:-1),count:$0.count)}
var eqVars:[Int:Int]=[:],size=0
for r in weights.indices {for i in weights[r].indices {
 if weights[r][i]>0 {vars[r][i]=SIMD3(size,size+1,size+2);size+=3}
 for id in eq where rows[id].rope==r && rows[id].particles.min()! == i {eqVars[id]=size;size+=1}
}}
var bandwidth=2
for id in eq {for particle in rows[id].particles {for axis in 0..<3 where vars[rows[id].rope][particle][axis]>=0 {
 bandwidth=max(bandwidth,abs(eqVars[id]!-vars[rows[id].rope][particle][axis]))
}}}
for r in weights.indices {for i in 0..<(weights[r].count-1) where weights[r][i]>0 && weights[r][i+1]>0 {
 bandwidth=max(bandwidth,vars[r][i+1].z-vars[r][i].x)
}}
func terms(_ row:Row)->[(Int,Double)] {
 var result:[(Int,Double)]=[]
 for k in row.particles.indices {
  let r=k>=2 && row.other>=0 ? row.other:row.rope
  for axis in 0..<3 {let v=vars[r][row.particles[k]][axis];if v>=0 {result.append((v,row.gradients[k][axis]))}}
 }
 result.append((size,row.board));return result
}
let rowTerms=Dictionary(uniqueKeysWithValues:eq.map{($0,terms(rows[$0]))})
let contactsIDs=rows.indices.filter{rows[$0].contact}
let contacts=FrozenContactStream(count:contactsIDs.count,row:{offset in
 let row=rows[contactsIDs[offset]],t=terms(row)
 return RopeLinearContact(indices:t.filter{$0.0<size}.map{$0.0},coefficients:t.filter{$0.0<size}.map{$0.1},border:[row.board],residual:row.residual)
})

func cold() throws -> (RopeContactSystem.Solution,[[String:Any]],[[String:Double]],[[String:Double]]) {
var system=try RopeBandedSystem(size:size,bandwidth:bandwidth)
var rhs=Array(repeating:0.0,count:size),column=rhs,boardMass=doc["boardMass"] as! Double
let boardRHS = -boardMass*((doc["boardHeight"] as! Double)-(doc["predictionHeight"] as! Double))
for r in weights.indices {for i in weights[r].indices where weights[r][i]>0 {
 let mass=1/weights[r][i]
 for axis in 0..<3 {let v=vars[r][i][axis];try system.addSymmetric(row:v,column:v,value:mass);rhs[v] = -mass*(positions[r][i][axis]-prediction[r][i][axis])}
}}
for r in weights.indices {for i in tensions[r].indices where tensions[r][i]>0 {
 let a=positions[r][i],b=positions[r][i+1],delta=SIMD3(b[0]-a[0],b[1]-a[1],b[2]-a[2]),length=simd_length(delta),t=delta/length
 let stiffness=tensions[r][i]/length
 func coefficient(_ a:Int,_ b:Int)->Double {stiffness*((a==b ? 1.0:0)-t[a]*t[b])}
 for particle in [i,i+1] where weights[r][particle]>0 {for a in 0..<3 {for b in 0...a {
  try system.addSymmetric(row:vars[r][particle][a],column:vars[r][particle][b],value:coefficient(a,b))
 }}}
 if weights[r][i]>0 && weights[r][i+1]>0 {for a in 0..<3 {for b in 0..<3 {
  try system.addSymmetric(row:vars[r][i][a],column:vars[r][i+1][b],value:-coefficient(a,b))
 }}}
 let attached=(attachments[r][String(i+1)] == nil ? 0.0:1)-(attachments[r][String(i)] == nil ? 0.0:1)
 if attached != 0 {
  boardMass += coefficient(1,1)*attached*attached
  for (particle,sign) in [(i,-1.0),(i+1,1.0)] where weights[r][particle]>0 {for axis in 0..<3 {column[vars[r][particle][axis]] += sign*coefficient(axis,1)*attached}}
 }
}}
for id in eq {
 let v=eqVars[id]!;rhs[v] = -rows[id].residual
 try system.addSymmetric(row:v,column:v,value:-epsilon);column[v]=rows[id].board
 for (variable,coefficient) in rowTerms[id]! where variable<size {try system.addSymmetric(row:v,column:variable,value:coefficient)}
}

 let factor=try system.primalPrepared(borderColumns:[column],borderMatrix:[[boardMass]],equalities:eq.map{eqVars[$0]!})
 let predictorStart=factor.primalProfile?.now() ?? 0
 let initial=try factor.solve(rhs:rhs,borderRHS:[boardRHS])
 factor.primalProfile?.record("primalPredictorSeconds",predictorStart)
 var trace:[[String:Any]]=[]
 var certificates:[[String:Double]]=[]
 var solverStatistics:[[String:Double]]=[]
 let result=try StreamedContactAdmission.solve(factor:factor,base:initial.base,border:initial.border,contacts:contacts,
  packSource:ProcessInfo.processInfo.environment["HANGTEN_PACKED_CONTACT_SOURCE"]=="1",
  regionSource:ProcessInfo.processInfo.environment["HANGTEN_AFFINE_REGION_CERTIFICATES"]=="1",
  crossCheckRegions:ProcessInfo.processInfo.environment["HANGTEN_AFFINE_REGION_CROSS_CHECK"]=="1",
  observeCertificate:{certificates.append($0)},
  observeSolve:{solverStatistics.append($0)},
  observe:{iteration,selected,added in trace.append(["admission":iteration,"selected":selected,"added":added])})
 // Stream teardown/full-source certification happens after observeSolve.
 if let profile=factor.primalProfile {
  var statistics=factor.primalStatistics.seconds
  statistics.merge(profile.seconds,uniquingKeysWith:{_,new in new})
  solverStatistics=[statistics]
 }
 return (result,trace,certificates,solverStatistics)
}
var timings:[Double]=[],failure:String?,last:[String:Any]=[:],regionRuns:[[[String:Double]]]=[],solverRuns:[[[String:Double]]]=[]
var solutions:[[String:Any]]=[]
for run in 0..<repetitions {
 let start=ProcessInfo.processInfo.systemUptime
 do {
  let (solution,trace,certificates,solverStatistics)=try cold()
  let seconds=ProcessInfo.processInfo.systemUptime-start
  timings.append(seconds)
  regionRuns.append(certificates)
  solverRuns.append(solverStatistics)
  var x:[Double]=[]
  for r in weights.indices {for i in weights[r].indices where weights[r][i]>0 {
   for axis in 0..<3 {x.append(solution.base[vars[r][i][axis]])}
  }}
  x.append(solution.border[0])
  let lambda=eq.map{solution.base[eqVars[$0]!]}
  // Retain every accepted cold solution for independent posthoc certification.
  // Exactly zero source forces are represented sparsely, without dropping rows.
  let entries=solution.multipliers.indices.filter{solution.multipliers[$0] != 0}.map{
    [Double($0),-solution.multipliers[$0]]
  }
  solutions.append(["x":x,"lambda":lambda,"forceEntries":entries])
  last=["x":x,"lambda":lambda,"mu":solution.multipliers.map{-$0},"trace":trace]
  print("cold",run,"seconds",seconds,"selected",trace.last!);fflush(stdout)
 } catch {
  failure=String(describing:error);print("rejected",failure!);fflush(stdout);break
 }
}
let report:[String:Any]=["owner":owner,"scope":"cold equality matrix/factor plus streamed row construction/discovery/solve/full affine certification; frozen input decoding/references, geometry and mesh excluded",
 "runtimeAdoption":false,"inputPath":inputPath,"sourceRows":contacts.count,"times":timings,
 "regionRuns":regionRuns,"solverRuns":solverRuns,"solutions":solutions,
 "failure":failure as Any? ?? NSNull(),"last":last]
try JSONSerialization.data(withJSONObject:report,options:[.prettyPrinted,.sortedKeys]).write(to:URL(fileURLWithPath:outputPath))
if failure != nil {exit(1)}
private struct DiagnosticJSON:Decodable {
 let value:Any
 init(from decoder:Decoder) throws {
  let c=try decoder.singleValueContainer()
  if c.decodeNil() {value=NSNull()}
  else if let v=try? c.decode(Bool.self) {value=v}
  else if let v=try? c.decode(Double.self) {value=v}
  else if let v=try? c.decode(String.self) {value=v}
  else if let v=try? c.decode([DiagnosticJSON].self) {value=v.map{$0.value}}
  else {value=try c.decode([String:DiagnosticJSON].self).mapValues{$0.value}}
 }
}
