import Foundation
import Accelerate

enum MixedProfile {static var factors=0;static var factorSeconds=0.0;static var pivots:[[String:Int]]=[]}

/// Direct sparse factor of the original mixed H/E/height/active-contact KKT.
/// No penalty curvature, separate-loop solve or changed regularization.
enum SparseMixedKKT {
 static func solve(_ original:PrimalPrepared,_ contacts:[RopeLinearContact],_ rhs:[Double],_ diagonal:[Double]) throws -> [Double] {
  let n=original.baseCount,nb=original.borderCount,d=n+nb+contacts.count
  guard d>0,d<=50_256,rhs.count==d,diagonal.count==contacts.count,contacts.count<=100_000 else {throw RopePhysicsError.invalid("Mixed dimension budget")}
  let nonlocal=contacts.filter{($0.indices.max() ?? 0)-($0.indices.min() ?? 0)>original.system.bandwidth}.count
  guard nonlocal+nb<=256 else {throw RopePhysicsError.invalid("Mixed nonlocal budget")}
  var terms:[Int:Double]=[:]
  func add(_ r:Int,_ c:Int,_ v:Double) throws {
   if v != 0 {
    let key=min(r,c)*d+max(r,c)
    guard terms[key] != nil || terms.count<8_000_000 else {throw RopePhysicsError.invalid("Mixed matrix entry budget")}
    terms[key,default:0]+=v
   }
  }
  for (r,c,v) in original.system.lowerEntries() {try add(r,c,v)}
  for j in 0..<nb {
   for i in 0..<n {try add(n+j,i,original.columns[j][i])}
   for k in 0...j {try add(n+j,n+k,original.borderMatrix[j][k])}
  }
  for (id,row) in contacts.enumerated() {
   let variable=n+nb+id
   try add(variable,variable,diagonal[id])
   for k in row.indices.indices {try add(variable,row.indices[k],row.coefficients[k])}
   for k in 0..<nb {try add(variable,n+k,row.border[k])}
  }
  guard terms.count<=8_000_000,terms.values.allSatisfy({$0.isFinite}),rhs.allSatisfy({$0.isFinite}) else {
   throw RopePhysicsError.invalid("Mixed matrix entry budget or nonfinite input")
  }
  let ordered=terms.keys.sorted()
  var starts=[0],indices:[Int32]=[],column=0,values=ordered.map{terms[$0]!}
  for key in ordered {while column<key/d {starts.append(indices.count);column+=1};indices.append(Int32(key%d))}
  while starts.count<d+1 {starts.append(indices.count)}
  var attributes=SparseAttributes_t();attributes.kind=SparseSymmetric;attributes.triangle=SparseLowerTriangle
  let started=ProcessInfo.processInfo.systemUptime
  let numeric=starts.withUnsafeMutableBufferPointer{s in indices.withUnsafeMutableBufferPointer{i in values.withUnsafeMutableBufferPointer{v in
   SparseFactor(SparseFactorizationLDLTTPP,SparseMatrix_Double(structure:SparseMatrixStructure(rowCount:Int32(d),columnCount:Int32(d),
    columnStarts:s.baseAddress!,rowIndices:i.baseAddress!,attributes:attributes,blockSize:1),data:v.baseAddress!))
  }}}
  MixedProfile.factors+=1;MixedProfile.factorSeconds+=ProcessInfo.processInfo.systemUptime-started
  defer {SparseCleanup(numeric)}
  guard numeric.status==SparseStatusOK else {throw RopePhysicsError.invalid("Mixed sparse factorization failed")}
  func solve(_ load:[Double])->[Double] {
   var answer=load
   answer.withUnsafeMutableBufferPointer{SparseSolve(numeric,DenseVector_Double(count:Int32(d),data:$0.baseAddress!))}
   return answer
  }
  func product(_ x:[Double])->[Double] {
   var p=Array(repeating:0.0,count:d)
   for c in 0..<d {for k in starts[c]..<starts[c+1] {
    let r=Int(indices[k]),v=values[k];p[r]+=v*x[c];if r != c {p[c]+=v*x[r]}
   }}
   return p
  }
  var answer=solve(rhs)
  for _ in 0..<3 {
   let error=zip(rhs,product(answer)).map(-)
   if (error.map{abs($0)}.max() ?? 0)<=1e-12*max(1,rhs.map{abs($0)}.max() ?? 0) {break}
   answer=zip(answer,solve(error)).map(+)
  }
  guard answer.allSatisfy({$0.isFinite}) else {throw RopePhysicsError.invalid("Nonfinite mixed correction")}
  return answer
 }
}

enum PrimalContactIP {
 static func solve(factor:PrimalPrepared,base:[Double],border:[Double],contacts:[RopeLinearContact],
  initialMultipliers:[Int:Double]=[:],maxIterations:Int=50,
  fallback:(() throws -> RopeContactSystem.Solution)?=nil) throws -> RopeContactSystem.Solution {
  let n=base.count,nb=border.count,equalities=Set(factor.equalities),epsilon=1e-8
  guard n==factor.baseCount,nb==factor.borderCount,n>0,n+nb+contacts.count<=50_256,(1...50).contains(maxIterations),
   contacts.count<=100_000,(base+border).allSatisfy({$0.isFinite}),
   initialMultipliers.allSatisfy({contacts.indices.contains($0.key) && $0.value.isFinite && $0.value<=0}),
   contacts.allSatisfy({c in c.indices.count==c.coefficients.count && c.border.count==nb && c.residual.isFinite &&
    c.indices.allSatisfy({(0..<n).contains($0) && !equalities.contains($0)}) &&
    (c.coefficients+c.border).allSatisfy({$0.isFinite})}) else {throw RopePhysicsError.invalid("Invalid FB contact input")}
  let nonlocal=contacts.filter{($0.indices.max() ?? 0)-($0.indices.min() ?? 0)>factor.system.bandwidth}.count
  guard nonlocal+nb<=256 else {throw RopePhysicsError.invalid("FB working nonlocal budget")}
  var entries=0
  for row in contacts {
   let count=row.indices.count+row.coefficients.count+row.border.count
   guard count<=8_000_000-entries else {throw RopePhysicsError.invalid("FB working array budget")}
   entries+=count
  }
  let rows=contacts.map{c -> RopeLinearContact in
   var combined:[Int:Double]=[:];for k in c.indices.indices {combined[c.indices[k],default:0]+=c.coefficients[k]}
   let ids=combined.keys.filter{combined[$0] != 0}.sorted()
   return RopeLinearContact(indices:ids,coefficients:ids.map{combined[$0]!},border:c.border,residual:c.residual)
  }
  var h=Array(repeating:0.0,count:n)
  for (r,c,v) in factor.system.lowerEntries() where r==c {h[r]=v}
  let scales=try rows.map{ row -> Double in
   var compliance=0.0
   for k in row.indices.indices {
    guard h[row.indices[k]]>0 else {throw RopePhysicsError.invalid("FB primal local diagonal")}
    compliance += row.coefficients[k]*row.coefficients[k]/h[row.indices[k]]
   }
   for k in 0..<nb where row.border[k] != 0 {
    guard factor.borderMatrix[k][k]>0 else {throw RopePhysicsError.invalid("FB border local diagonal")}
    compliance += row.border[k]*row.border[k]/factor.borderMatrix[k][k]
   }
   return compliance > 0 ? 1/compliance:1
  }
  guard scales.allSatisfy({$0.isFinite && $0>0}) else {throw RopePhysicsError.invalid("FB local scaling")}
  let load=factor.product(base,border)
  func norm(_ v:[Double])->Double {v.map{abs($0)}.max() ?? 0}
  func value(_ row:RopeLinearContact,_ x:[Double],_ b:[Double])->Double {
   var result=row.residual
   for k in row.indices.indices {result += row.coefficients[k]*x[row.indices[k]]}
   for k in 0..<nb {result += row.border[k]*b[k]}
   return result
  }
  struct Evaluation {
   let q:[Double],gap:[Double],phi:[Double],force:[Double],a:[Double],b:[Double],error:[Double]
   let merit:Double,accepted:Bool
  }
  func evaluate(_ x:[Double],_ b:[Double],_ mu:[Double]) throws -> Evaluation {
   let q=rows.map{value($0,x,b)},gap=rows.indices.map{q[$0]-epsilon*mu[$0]}
   let forces=rows.indices.map{-mu[$0]/scales[$0]}
   var phi:[Double]=[],da:[Double]=[],db:[Double]=[]
   for i in rows.indices {
    let l=forces[i],g=gap[i],r=hypot(l,g)
    // Subtract the larger term first. Subtracting a tiny force before a
    // large positive gap can round both operations to zero, hiding a still
    // significant multiplier*gap residual from the Newton direction.
    phi.append((r-max(l,g))-min(l,g))
    // Stable derivatives avoid cancellation near inactive or active contacts.
    da.append(r==0 ? -1:(l>0 ? -g*g/(r*(r+l)):l/r-1))
    db.append(r==0 ? -1:(g>0 ? -l*l/(r*(r+g)):g/r-1))
   }
   var p=factor.product(x,b)
   for i in rows.indices {
    for k in rows[i].indices.indices {p.base[rows[i].indices[k]] += rows[i].coefficients[k]*mu[i]}
    for k in 0..<nb {p.border[k] += rows[i].border[k]*mu[i]}
   }
   let error=zip(p.base+p.border,load.base+load.border).map(-)
   let physicalEquality=norm(factor.equalities.map{error[$0]+epsilon*x[$0]})
   let complementarity=norm(rows.indices.map{mu[$0]*gap[$0]})
   let accepted=norm(error)<=1e-10 && physicalEquality<=1e-8 && (q.min() ?? 0)>=(-1e-8) &&
    (gap.min() ?? 0)>=(-1e-10) && complementarity<=1e-14 && (mu.max() ?? 0)<=1e-12
   var merit=phi.reduce(0){$0+$1*$1}
   for i in 0..<n {
    let scale=equalities.contains(i) ? 1:abs(h[i])
    let residual=error[i]/scale;merit += residual*residual
   }
   for i in 0..<nb {let residual=error[n+i]/abs(factor.borderMatrix[i][i]);merit += residual*residual}
   guard merit.isFinite,(phi+da+db+error).allSatisfy({$0.isFinite}) else {throw RopePhysicsError.invalid("Nonfinite FB evaluation")}
   return Evaluation(q:q,gap:gap,phi:phi,force:forces,a:da,b:db,error:error,merit:merit,accepted:accepted)
  }
  var x=base,b=border,mu=rows.indices.map{initialMultipliers[$0] ?? 0}
  for iteration in 0..<maxIterations {
   let current=try evaluate(x,b,mu)
   if current.accepted {return RopeContactSystem.Solution(base:x,border:b,multipliers:mu,activeIDs:rows.indices.filter{mu[$0]<(-1e-12)})}
   var diagonals:[Double]=[],loads=current.error.map(-),contactRHS:[Double]=[]
   let coupledRows=rows.indices.map{ i -> RopeLinearContact in
    if current.b[i]==0 {
     // Exact inactive FB derivative: dmu=-mu. Eliminate that known force
     // from stationarity rather than create a nonsymmetric Newton matrix.
     diagonals.append(-1);contactRHS.append(mu[i])
     for k in rows[i].indices.indices {loads[rows[i].indices[k]] += rows[i].coefficients[k]*mu[i]}
     for k in 0..<nb {loads[n+k] += rows[i].border[k]*mu[i]}
     return RopeLinearContact(indices:[],coefficients:[],border:Array(repeating:0,count:nb),residual:0)
    }
    diagonals.append(-epsilon-current.a[i]/(scales[i]*current.b[i]))
    contactRHS.append(-current.phi[i]/current.b[i])
    return rows[i]
   }
   let delta=try SparseMixedKKT.solve(factor,coupledRows,loads+contactRHS,diagonals)
   var alpha=1.0,accepted=false
   for trial in 0..<20 {
    let candidateX=(0..<n).map{x[$0]+alpha*delta[$0]},candidateB=(0..<nb).map{b[$0]+alpha*delta[n+$0]}
    let candidateMu=rows.indices.map{mu[$0]+alpha*delta[n+nb+$0]}
    let candidate=try evaluate(candidateX,candidateB,candidateMu)
    if candidate.accepted || candidate.merit <= (1-1e-4*alpha)*current.merit {
     x=candidateX;b=candidateB;mu=candidateMu;accepted=true
     if MixedProfile.pivots.count<1000 {MixedProfile.pivots.append(["iteration":iteration,"active":coupledRows.filter{!$0.indices.isEmpty || $0.border.contains(where:{$0 != 0})}.count,"lineSearchTrials":trial+1])}
     break
    }
    alpha *= 0.5
   }
   guard accepted else {throw RopePhysicsError.invalid("FB global merit line-search bound at iteration \(iteration)")}
  }
  let final=try evaluate(x,b,mu)
  if final.accepted {return RopeContactSystem.Solution(base:x,border:b,multipliers:mu,activeIDs:rows.indices.filter{mu[$0]<(-1e-12)})}
  throw RopePhysicsError.invalid("FB iteration bound: merit \(final.merit), stationarity \(norm(final.error)), physical \(final.q.min() ?? 0)")
 }
}
