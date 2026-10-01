import Foundation

/// Isolated sparse scalar LDL of a symmetric quasi-definite Newton matrix.
/// This is a textbook elimination-tree/left-looking implementation, not copied
/// SuiteSparse code. Real-arithmetic existence is not a stability certificate:
/// zero/wrong-sign/nonfinite pivots reject; the caller refines the ORIGINAL
/// matrix and retains the full original KKT and displacement comparison gates.
final class SparseLDL {
 static func originalIndices(fromSDKOrder order:[Int32]) throws -> [Int32] {
  guard !order.isEmpty,order.count<=50_256,order.allSatisfy({(0..<order.count).contains(Int($0))}),
   Set(order).count==order.count else {throw RopePhysicsError.invalid("Invalid SDK permutation")}
  var inverse=Array(repeating:Int32(0),count:order.count)
  for original in order.indices {inverse[Int(order[original])]=Int32(original)}
  return inverse
 }
 let size:Int
 let factorNonzeros:Int
 private let inputStarts:[Int],inputIndices:[Int32],permutation:[Int],negative:Set<Int>
 private let upperStarts:[Int],upperRows:[Int],upperSlots:[Int]
 private let rowStarts:[Int],rowItems:[Int],lowerStarts:[Int],lowerRows:[Int]
 private var diagonal:[Double],lowerValues:[Double],scale:[Double],work:[Double],used:[Int]
 private var valid=false
 init(size:Int,starts:[Int],indices:[Int32],permutation:[Int32],equalities:Set<Int>) throws {
  guard size>0,size<=50_256,starts.count==size+1,starts.first==0,starts.last==indices.count,
   indices.count<=8_000_000,starts.allSatisfy({(0...indices.count).contains($0)}),
   (0..<size).allSatisfy({starts[$0]<=starts[$0+1]}),permutation.count==size,
   permutation.allSatisfy({(0..<size).contains(Int($0))}),Set(permutation).count==size,
   equalities.allSatisfy({(0..<size).contains($0)}) else {throw RopePhysicsError.invalid("Invalid sparse LDL pattern")}
  for c in 0..<size {
   var previous=c-1
   for p in starts[c]..<starts[c+1] {
    let row=Int(indices[p])
    guard row>=c,row<size,row>previous else {throw RopePhysicsError.invalid("Invalid sparse LDL lower column")}
    previous=row
   }
  }
  self.size=size
  inputStarts=starts;inputIndices=indices;self.permutation=permutation.map{Int($0)};negative=equalities
  var inverse=Array(repeating:0,count:size)
  for k in 0..<size {inverse[Int(permutation[k])]=k}
  var columns=Array(repeating:[(row:Int,slot:Int)](),count:size)
  for c in 0..<size {for p in starts[c]..<starts[c+1] {
   let a=inverse[c],b=inverse[Int(indices[p])]
   columns[max(a,b)].append((min(a,b),p))
  }}
  var ap=[0],ai:[Int]=[],slots:[Int]=[]
  for entries in columns {
   for term in entries.sorted(by:{$0.row<$1.row}) {ai.append(term.row);slots.append(term.slot)}
   ap.append(ai.count)
  }
  upperStarts=ap;upperRows=ai;upperSlots=slots
  // Build the elimination tree and each row's predecessor set once. Numeric
  // refactors scatter into that immutable pattern without sets or dictionaries.
  var parent=Array(repeating:-1,count:size),marked=Array(repeating:-1,count:size)
  var rows=Array(repeating:[Int](),count:size),counts=Array(repeating:0,count:size),total=0
  for k in 0..<size {
   marked[k]=k
   for p in ap[k]..<ap[k+1] where ai[p]<k {
    var i=ai[p]
    while marked[i] != k {
     marked[i]=k;rows[k].append(i)
     if parent[i]<0 {parent[i]=k}
     i=parent[i]
    }
   }
   rows[k].sort()
   total += rows[k].count
   guard total<=8_000_000 else {throw RopePhysicsError.invalid("Excessive sparse LDL fill")}
   for i in rows[k] {counts[i]+=1}
  }
  var lp=[0],rp=[0],items:[Int]=[]
  for k in 0..<size {lp.append(lp.last!+counts[k]);items+=rows[k];rp.append(items.count)}
  var lr=Array(repeating:0,count:total),cursor=Array(lp.prefix(size))
  for k in 0..<size {for i in rows[k] {lr[cursor[i]]=k;cursor[i]+=1}}
  rowStarts=rp;rowItems=items;lowerStarts=lp;lowerRows=lr;factorNonzeros=total+size
  diagonal=Array(repeating:0,count:size);lowerValues=Array(repeating:0,count:total)
  scale=Array(repeating:1,count:size);work=Array(repeating:0,count:size);used=Array(repeating:0,count:size)
 }
 func refactor(_ values:[Double]) throws {
  guard values.count==inputIndices.count,values.allSatisfy({$0.isFinite}) else {
   throw RopePhysicsError.invalid("Invalid sparse LDL values")
  }
  valid=false
  var maximum=Array(repeating:0.0,count:size)
  for c in 0..<size {for p in inputStarts[c]..<inputStarts[c+1] {
   let r=Int(inputIndices[p]),v=abs(values[p]);maximum[c]=max(maximum[c],v);maximum[r]=max(maximum[r],v)
  }}
  guard maximum.allSatisfy({$0>0 && $0.isFinite}) else {throw RopePhysicsError.invalid("Zero sparse LDL row")}
  scale=permutation.map{1/sqrt(maximum[$0])}
  let ap=upperStarts,ai=upperRows,slots=upperSlots,lp=lowerStarts,lr=lowerRows,rp=rowStarts,items=rowItems
  try lowerValues.withUnsafeMutableBufferPointer {l in
   try diagonal.withUnsafeMutableBufferPointer {d in
    try work.withUnsafeMutableBufferPointer {y in
     try used.withUnsafeMutableBufferPointer {count in
      for i in 0..<size {y[i]=0;count[i]=0}
      for k in 0..<size {
       for p in ap[k]..<ap[k+1] {y[ai[p]] += values[slots[p]]*scale[ai[p]]*scale[k]}
       var pivot=y[k];y[k]=0
       for p in rp[k]..<rp[k+1] {
        let i=items[p],yi=y[i];y[i]=0
        let finish=lp[i]+count[i]
        for q in lp[i]..<finish {y[lr[q]] -= l[q]*yi}
        let coefficient=yi/d[i]
        guard coefficient.isFinite,finish<lp[i+1],lr[finish]==k else {
         throw RopePhysicsError.invalid("Invalid sparse LDL numeric pattern")
        }
        pivot -= coefficient*yi;l[finish]=coefficient;count[i]+=1
       }
       guard pivot.isFinite,(negative.contains(permutation[k]) ? pivot<0:pivot>0) else {
        throw RopePhysicsError.invalid("Sparse LDL zero or wrong-sign pivot at \(k)")
       }
       d[k]=pivot
      }
     }
    }
   }
  }
  valid=true
 }
 func solve(_ rhs:[Double]) throws -> [Double] {
  guard valid,rhs.count==size,rhs.allSatisfy({$0.isFinite}) else {throw RopePhysicsError.invalid("Invalid sparse LDL solve")}
  var answer=(0..<size).map{rhs[permutation[$0]]*scale[$0]}
  let lp=lowerStarts,lr=lowerRows
  lowerValues.withUnsafeBufferPointer {l in
   diagonal.withUnsafeBufferPointer {d in
    answer.withUnsafeMutableBufferPointer {x in
     for c in 0..<size {for p in lp[c]..<lp[c+1] {x[lr[p]] -= l[p]*x[c]}}
     for i in 0..<size {x[i] /= d[i]}
     for c in (0..<size).reversed() {for p in lp[c]..<lp[c+1] {x[c] -= l[p]*x[lr[p]]}}
    }
   }
  }
  var original=Array(repeating:0.0,count:size)
  for i in 0..<size {original[permutation[i]]=answer[i]*scale[i]}
  guard original.allSatisfy({$0.isFinite}) else {throw RopePhysicsError.invalid("Nonfinite sparse LDL correction")}
  return original
 }
}
