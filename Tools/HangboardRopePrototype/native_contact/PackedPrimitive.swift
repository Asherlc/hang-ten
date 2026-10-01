import Foundation

/// Buffers for the isolated primitive ceiling; no app input or acceptance.
final class PrimitiveBuffer<T> {
 let pointer:UnsafeMutablePointer<T>,count:Int
 init(count:Int,repeating:T) {
  self.count=count;pointer = .allocate(capacity:max(1,count));pointer.initialize(repeating:repeating,count:count)
 }
 convenience init(_ values:[T]) {self.init(count:values.count,repeating:values[0]);for i in values.indices {pointer[i]=values[i]}}
 deinit {pointer.deinitialize(count:count);pointer.deallocate()}
 func array()->[T] {Array(UnsafeBufferPointer(start:pointer,count:count))}
}
/// Exported only from an independently validated reference SparseLDL.
final class PrimitivePattern {
 let size:Int,entries:Int
 let inputStarts,inputIndices,permutation,upperStarts,upperRows,upperSlots:PrimitiveBuffer<Int32>
 let rowStarts,rowItems,lowerStarts,lowerRows:PrimitiveBuffer<Int32>
 let negative:PrimitiveBuffer<UInt8>
 init(_ p:[String:[Int]]) {
  size=p["size"]![0];entries=p["inputIndices"]!.count
  func index(_ key:String)->PrimitiveBuffer<Int32> {PrimitiveBuffer(p[key]!.map{Int32($0)})}
  inputStarts=index("inputStarts");inputIndices=index("inputIndices");permutation=index("permutation")
  upperStarts=index("upperStarts");upperRows=index("upperRows");upperSlots=index("upperSlots")
  rowStarts=index("rowStarts");rowItems=index("rowItems");lowerStarts=index("lowerStarts");lowerRows=index("lowerRows")
  negative=PrimitiveBuffer(p["negative"]!.map{UInt8($0)})
 }
}
/// Original scalar arithmetic/guards, flat pointers and no numeric-loop allocation.
/// Constructor allocation and workspace first touch remain inside the cold timer.
final class PackedPrimitive {
 let pattern:PrimitivePattern
 private let diagonal,lowerValues,scale,work,maximum,answer,original,result:PrimitiveBuffer<Double>
 private let used:PrimitiveBuffer<Int32>
 private var valid=false
 init(_ p:PrimitivePattern) {
  pattern=p;diagonal=PrimitiveBuffer(count:p.size,repeating:0);lowerValues=PrimitiveBuffer(count:p.lowerRows.count,repeating:0)
  scale=PrimitiveBuffer(count:p.size,repeating:1);work=PrimitiveBuffer(count:p.size,repeating:0)
  maximum=PrimitiveBuffer(count:p.size,repeating:0);answer=PrimitiveBuffer(count:p.size,repeating:0)
  original=PrimitiveBuffer(count:p.size,repeating:0);result=PrimitiveBuffer(count:p.size,repeating:0)
  used=PrimitiveBuffer(count:p.size,repeating:0)
 }
 func refactor(_ values:[Double])->Bool {
  guard values.count==pattern.entries else {return false}
  return values.withUnsafeBufferPointer {refactor($0.baseAddress!)}
 }
 func refactor(_ values:UnsafePointer<Double>)->Bool {
  let n=pattern.size,nnz=pattern.entries
  for i in 0..<nnz {if !values[i].isFinite {return false}}
  valid=false
  let starts=pattern.inputStarts.pointer,indices=pattern.inputIndices.pointer,permutation=pattern.permutation.pointer
  let maxValue=maximum.pointer,s=scale.pointer,y=work.pointer,count=used.pointer,l=lowerValues.pointer,d=diagonal.pointer
  for i in 0..<n {maxValue[i]=0}
  for c in 0..<n {for p in Int(starts[c])..<Int(starts[c+1]) {
   let r=Int(indices[p]),v=abs(values[p]);maxValue[c]=max(maxValue[c],v);maxValue[r]=max(maxValue[r],v)
  }}
  for i in 0..<n {if !(maxValue[i]>0 && maxValue[i].isFinite) {return false}}
  for i in 0..<n {s[i]=1/sqrt(maxValue[Int(permutation[i])]);y[i]=0;count[i]=0}
  let ap=pattern.upperStarts.pointer,ai=pattern.upperRows.pointer,slots=pattern.upperSlots.pointer
  let lp=pattern.lowerStarts.pointer,lr=pattern.lowerRows.pointer,rp=pattern.rowStarts.pointer,items=pattern.rowItems.pointer
  let negative=pattern.negative.pointer
  for k in 0..<n {
   for p in Int(ap[k])..<Int(ap[k+1]) {let row=Int(ai[p]);y[row] += values[Int(slots[p])]*s[row]*s[k]}
   var pivot=y[k];y[k]=0
   for p in Int(rp[k])..<Int(rp[k+1]) {
    let i=Int(items[p]),yi=y[i];y[i]=0;let finish=Int(lp[i])+Int(count[i])
    for q in Int(lp[i])..<finish {y[Int(lr[q])] -= l[q]*yi}
    let coefficient=yi/d[i]
    if !coefficient.isFinite || finish>=Int(lp[i+1]) || Int(lr[finish]) != k {return false}
    pivot -= coefficient*yi;l[finish]=coefficient;count[i]+=1
   }
   if !pivot.isFinite || !(negative[Int(permutation[k])] != 0 ? pivot<0:pivot>0) {return false}
   d[k]=pivot
  }
  valid=true;return true
 }
 func solve(_ rhs:[Double])->[Double]? {
  guard rhs.count==pattern.size else {return nil}
  return rhs.withUnsafeBufferPointer {solve($0.baseAddress!) ? original.array():nil}
 }
 func solve(_ rhs:UnsafePointer<Double>)->Bool {
  guard valid else {return false};let n=pattern.size
  for i in 0..<n {if !rhs[i].isFinite {return false}}
  let permutation=pattern.permutation.pointer,s=scale.pointer,x=answer.pointer,l=lowerValues.pointer,d=diagonal.pointer
  let lp=pattern.lowerStarts.pointer,lr=pattern.lowerRows.pointer,o=original.pointer
  for i in 0..<n {x[i]=rhs[Int(permutation[i])]*s[i]}
  for c in 0..<n {for p in Int(lp[c])..<Int(lp[c+1]) {x[Int(lr[p])] -= l[p]*x[c]}}
  for i in 0..<n {x[i] /= d[i]}
  for c in (0..<n).reversed() {for p in Int(lp[c])..<Int(lp[c+1]) {x[c] -= l[p]*x[Int(lr[p])]}}
  for i in 0..<n {o[Int(permutation[i])]=x[i]*s[i]}
  for i in 0..<n {if !o[i].isFinite {return false}}
  return true
 }
 func product(_ values:[Double],_ rhs:[Double])->[Double]? {
  guard values.count==pattern.entries,rhs.count==pattern.size else {return nil}
  values.withUnsafeBufferPointer {v in rhs.withUnsafeBufferPointer {x in product(v.baseAddress!,x.baseAddress!)}}
  return result.array()
 }
 func product(_ values:UnsafePointer<Double>,_ rhs:UnsafePointer<Double>) {
  let n=pattern.size,starts=pattern.inputStarts.pointer,indices=pattern.inputIndices.pointer,o=result.pointer
  for i in 0..<n {o[i]=0}
  for c in 0..<n {for k in Int(starts[c])..<Int(starts[c+1]) {
   let r=Int(indices[k]),v=values[k];o[r] += v*rhs[c];if r != c {o[c] += v*rhs[r]}
  }}
 }
 func productOfLastSolve(_ values:UnsafePointer<Double>) {product(values,UnsafePointer(original.pointer))}
 var checksum:Double {original.pointer[0]+result.pointer[0]}
 func state()->[[Double]] {[diagonal.array(),lowerValues.array(),scale.array()]}
}
