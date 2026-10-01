import Foundation

enum RopePhysicsError:Error {case invalid(String)}
let arguments=CommandLine.arguments
precondition(arguments.count==3)
let raw=try JSONSerialization.jsonObject(with:Data(contentsOf:URL(fileURLWithPath:arguments[1]))) as! [String:Any]
let n=raw["size"] as! Int,starts=raw["starts"] as! [Int],indices=(raw["indices"] as! [Int]).map{Int32($0)}
let permutation=(raw["inverse"] as! [Int]).map{Int32($0)},equalities=Set(raw["equalities"] as! [Int])
let reference=try SparseLDL(size:n,starts:starts,indices:indices,permutation:permutation,equalities:equalities)
let pattern=reference.ceilingPattern()
var values=Array(repeating:0.0,count:indices.count),diagonalSlots=Array(repeating:-1,count:n),sums=Array(repeating:0.0,count:n)
for c in 0..<n {for p in starts[c]..<starts[c+1] {
 let r=Int(indices[p])
 if r==c {diagonalSlots[c]=p}
 else {let value=Double((p*17+3)%13-6)/4096;values[p]=value;sums[r]+=abs(value);sums[c]+=abs(value)}
}}
precondition(diagonalSlots.allSatisfy{$0>=0})
let matrices=(0..<15).map {iteration -> [Double] in
 var result=values
 for i in 0..<n {result[diagonalSlots[i]]=(equalities.contains(i) ? -1:1)*(2+sums[i]+Double(iteration)/1024)}
 return result
}
let rhs=(0..<n).map{Double(($0*13+7)%97-48)/128}
func identical(_ a:[Double],_ b:[Double])->Bool {
 a.count==b.count && zip(a,b).allSatisfy{$0.bitPattern==$1.bitPattern}
}
func originalProduct(_ values:[Double],_ x:[Double])->[Double] {
 var result=Array(repeating:0.0,count:n)
 for c in 0..<n {for k in starts[c]..<starts[c+1] {
  let r=Int(indices[k]),v=values[k];result[r]+=v*x[c]
  if r != c {result[c]+=v*x[r]}
 }}
 return result
}
var report:[String:Any]=["owner":"strong-owl-live-physics","runtimeAdoption":false,"physicalStepAccepted":false,
 "scope":"Synthetic well-scaled SQD numerical primitives only; no row/IP/KKT/geometry/recovery/device acceptance",
 "firstTouchIncluded":true,"symbolicAndInputPackingExcluded":true,"diagnosticCutoffSeconds":0.001,
 "codePatternAndInputsWarmedByCorrectnessChecks":true,"freshWorkspaceEachSchedule":true,
 "observedScheduleFollowsFavorable":true,"scopeIsNotMathematicalLowerBound":true]
func finish(_ status:Int32)->Never {
 try! JSONSerialization.data(withJSONObject:report,options:[.prettyPrinted,.sortedKeys]).write(to:URL(fileURLWithPath:arguments[2]))
 print(String(data:try! JSONSerialization.data(withJSONObject:report,options:[.prettyPrinted,.sortedKeys]),encoding:.utf8)!)
 exit(status)
}
let packedPattern=PrimitivePattern(pattern)
let checked=PackedPrimitive(packedPattern)
for matrix in matrices {
 try reference.refactor(matrix)
 guard checked.refactor(matrix),let solved=checked.solve(rhs),let product=checked.product(matrix,solved),
  checked.state().count==reference.ceilingState().count,
  zip(checked.state(),reference.ceilingState()).allSatisfy({identical($0,$1)}),
  identical(solved,try reference.solve(rhs)),identical(product,originalProduct(matrix,solved)) else {
  report["correctnessAccepted"]=false;report["reason"]="Primitive factor/solve/product did not match reference bits";finish(4)
 }
}
report["correctnessAccepted"]=true
// Transition guards, independent of throughput.
precondition(!checked.refactor(Array(repeating:Double.nan,count:values.count)))
precondition(!checked.refactor(Array(repeating:Double.infinity,count:values.count)))
precondition(!checked.refactor([]))
precondition(checked.solve(rhs) != nil)
precondition(!checked.refactor(Array(repeating:0.0,count:values.count)))
precondition(checked.solve(rhs)==nil)
precondition(checked.refactor(matrices[0]))
precondition(checked.solve(Array(repeating:Double.infinity,count:n))==nil)
precondition(checked.solve([])==nil)
var wrongSign=matrices[0];wrongSign[diagonalSlots[0]] *= -1
precondition(!checked.refactor(wrongSign))
precondition(checked.solve(rhs)==nil)
precondition(checked.refactor(matrices[0]))
if ProcessInfo.processInfo.environment["HANGTEN_PRIMITIVE_VALIDATE_ONLY"]=="1" {
 report["reason"]="Reviewed correctness and transition guards only; no additional timing"
 finish(0)
}
let packedMatrices=matrices.map{PrimitiveBuffer($0)},packedRHS=PrimitiveBuffer(rhs)
func timed(_ solveCount:Int)->[String:Any] {
 let start=ProcessInfo.processInfo.systemUptime
 let kernel=PackedPrimitive(packedPattern)
 let prepared=ProcessInfo.processInfo.systemUptime
 var refactorSeconds=0.0,solveSeconds=0.0,productSeconds=0.0,checksum=0.0,completed=0
 for i in 0..<15 {
  var stage=ProcessInfo.processInfo.systemUptime
  precondition(kernel.refactor(UnsafePointer(packedMatrices[i].pointer)))
  refactorSeconds += ProcessInfo.processInfo.systemUptime-stage
  for _ in 0..<2 {
   stage=ProcessInfo.processInfo.systemUptime
   precondition(kernel.solve(UnsafePointer(packedRHS.pointer)))
   solveSeconds += ProcessInfo.processInfo.systemUptime-stage
   stage=ProcessInfo.processInfo.systemUptime
   kernel.productOfLastSolve(UnsafePointer(packedMatrices[i].pointer))
   productSeconds += ProcessInfo.processInfo.systemUptime-stage
   checksum += kernel.checksum;completed+=1
  }
 }
 for _ in completed..<solveCount {
  var stage=ProcessInfo.processInfo.systemUptime
  precondition(kernel.solve(UnsafePointer(packedRHS.pointer)))
  solveSeconds += ProcessInfo.processInfo.systemUptime-stage
  stage=ProcessInfo.processInfo.systemUptime
  kernel.productOfLastSolve(UnsafePointer(packedMatrices[14].pointer))
  productSeconds += ProcessInfo.processInfo.systemUptime-stage
  checksum += kernel.checksum
 }
 let total=ProcessInfo.processInfo.systemUptime-start
 precondition(checksum.isFinite)
 return ["combinedSeconds":total,"workspaceFirstTouchSeconds":prepared-start,"refactorSeconds":refactorSeconds,
  "solveSeconds":solveSeconds,"productSeconds":productSeconds,"refactors":15,"solves":solveCount,"products":solveCount,"checksum":checksum]
}
let favorable=timed(30),observed=timed(46)
report["favorableSchedule"]=favorable;report["observedSchedule"]=observed
let proceed=(favorable["combinedSeconds"] as! Double)<=0.001
report["packedIPContinuationAllowed"]=proceed
report["reason"]=proceed ? "Primitive ceiling passes diagnostic cutoff only; full packed IP cold2ms still unproved":"Primitive ceiling fails fixed1ms cutoff; stop packing this15iteration schedule"
finish(proceed ? 0:3)
