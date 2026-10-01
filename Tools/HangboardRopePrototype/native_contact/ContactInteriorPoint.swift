import Foundation

/// Experimental Mehrotra solve of the unchanged regularized KKT. Both loops,
/// height, equalities and every admitted local/nonlocal contact participate in
/// one sparse factor. A fixed CSC pattern receives fresh numeric factors.
enum PrimalContactIP {
 static func solve(factor:PrimalPrepared,base:[Double],border:[Double],contacts:[RopeLinearContact],
  initialMultipliers:[Int:Double]=[:],maxIterations:Int=50,
  fallback:(() throws -> RopeContactSystem.Solution)?=nil) throws -> RopeContactSystem.Solution {
  let n=base.count,nb=border.count,m=contacts.count,epsilon=1e-8,equalities=Set(factor.equalities)
  let parity=ProcessInfo.processInfo.environment["HANGTEN_PRIMAL_PARITY"] == "1"
  let profile=factor.primalProfile,started=profile?.now() ?? 0
  defer {profile?.record("primalIPSeconds",started)}
  guard n==factor.baseCount,nb==factor.borderCount,n>0,n+nb<=50_256,
   (1...50).contains(maxIterations),m<=100_000,(base+border).allSatisfy({$0.isFinite}),
   contacts.allSatisfy({c in c.indices.count==c.coefficients.count && c.border.count==nb && c.residual.isFinite &&
    c.indices.allSatisfy({(0..<n).contains($0) && !equalities.contains($0)}) &&
    (c.coefficients+c.border).allSatisfy({$0.isFinite})}),
   initialMultipliers.allSatisfy({contacts.indices.contains($0.key) && $0.value.isFinite && $0.value<=0}) else {
    throw RopePhysicsError.invalid("Invalid primal contact screen")
  }
  // Combine repeated variable references exactly; zero coefficients are terms,
  // not independent contacts. Every row itself remains in the KKT checks.
  let rows=contacts.map {c -> RopeLinearContact in
   var combined:[Int:Double]=[:]
   for k in c.indices.indices {combined[c.indices[k],default:0] += c.coefficients[k]}
   let ids=combined.keys.filter{combined[$0] != 0}.sorted()
   return RopeLinearContact(indices:ids,coefficients:ids.map{combined[$0]!},border:c.border,residual:c.residual)
  }
  func norm(_ v:[Double])->Double {v.map{abs($0)}.max() ?? 0}
  func value(_ row:RopeLinearContact,_ x:[Double],_ b:[Double])->Double {
   var result=0.0
   for k in row.indices.indices {result += row.coefficients[k]*x[row.indices[k]]}
   for k in row.border.indices {result += row.border[k]*b[k]}
   return result
  }
  func transpose(_ values:[Double])->(base:[Double],border:[Double]) {
   var x=Array(repeating:0.0,count:n),b=Array(repeating:0.0,count:nb)
   for id in rows.indices {
    for k in rows[id].indices.indices {x[rows[id].indices[k]] += rows[id].coefficients[k]*values[id]}
    for k in 0..<nb {b[k] += rows[id].border[k]*values[id]}
   }
   return (x,b)
  }
  func fraction(_ values:[Double],_ change:[Double],_ safety:Double=1)->Double {
   var result=1.0
   for i in values.indices where change[i]<0 {result=min(result,-safety*values[i]/change[i])}
   return result
  }
  let rhs=factor.product(base,border)
  func recover(_ mu:[Double]) throws -> RopeContactSystem.Solution {
   let started=profile?.now() ?? 0
   defer {profile?.record("primalRecoverySeconds",started)}
   var load=rhs.base,loadBorder=rhs.border
   for id in contacts.indices {
    for k in contacts[id].indices.indices {load[contacts[id].indices[k]] += contacts[id].coefficients[k]*mu[id]}
    for k in 0..<nb {loadBorder[k] += contacts[id].border[k]*mu[id]}
   }
   let solved=try factor.refined(load,loadBorder)
   var product=factor.product(solved.base,solved.border)
   for id in contacts.indices {
    for k in contacts[id].indices.indices {product.base[contacts[id].indices[k]] -= contacts[id].coefficients[k]*mu[id]}
    for k in 0..<nb {product.border[k] -= contacts[id].border[k]*mu[id]}
   }
   let error=zip(product.base+product.border,rhs.base+rhs.border).map(-)
   let physicalEquality=norm(factor.equalities.map{error[$0]+epsilon*solved.base[$0]})
   // Certify the original ordered rows, including repeated references and the
   // residual before sparse additions. Canonical Newton rows are no substitute.
   func ordered(_ row:RopeLinearContact,_ start:Double)->Double {
    var result=start
    for k in row.indices.indices {result += row.coefficients[k]*solved.base[row.indices[k]]}
    for k in 0..<nb {result += row.border[k]*solved.border[k]}
    return result
   }
   let q=contacts.map{ordered($0,$0.residual)}
   let gap=contacts.indices.map{ordered(contacts[$0],contacts[$0].residual+epsilon*mu[$0])}
   guard norm(error)<=1e-10,physicalEquality<=1e-8,(q.min() ?? 0) >= -1e-8,
    (gap.min() ?? 0) >= -1e-10,norm(contacts.indices.map{mu[$0]*gap[$0]})<=1e-14,
    (mu.min() ?? 0)>=0,(solved.base+solved.border+gap+mu).allSatisfy({$0.isFinite}) else {
    throw RopePhysicsError.invalid("Primal recovery original-matrix certificate failed")
   }
   return RopeContactSystem.Solution(base:solved.base,border:solved.border,multipliers:mu.map{-$0},
    activeIDs:contacts.indices.filter{mu[$0]>1e-12})
  }
  var x=base,b=border,mu=Array(repeating:0.001,count:m)
  var slack=rows.map{max(1e-5,$0.residual+value($0,x,b)+epsilon*0.001)}
  var prepared:SparseNewtonPrepared?
  for iteration in 0...maxIterations {
   let product=factor.product(x,b),atMu=transpose(mu)
   let rd=base.indices.map{rhs.base[$0]-product.base[$0]+atMu.base[$0]}
   let rdb=border.indices.map{rhs.border[$0]-product.border[$0]+atMu.border[$0]}
   let q=rows.map{$0.residual+value($0,x,b)}
   let gap=rows.indices.map{q[$0]+epsilon*mu[$0]}
   let rp=rows.indices.map{slack[$0]-gap[$0]}
   let equalityError=factor.equalities.map{product.base[$0]-rhs.base[$0]+epsilon*x[$0]}
   let feasibility=max(norm(equalityError),max(0,-(q.min() ?? 0)))
   let complementarity=norm(rows.indices.map{mu[$0]*gap[$0]})
   if norm(rd+rdb)<=1e-10 && norm(rp)<=1e-10 && complementarity<=1e-14 && feasibility<=1e-8 &&
     (mu.min() ?? 0)>=0 && (slack.min() ?? 0)>=0 && (!parity || complementarity<=1e-18) {
    profile?.seconds["primalIterations"]=Double(iteration)
    profile?.seconds["primalWorkingRows"]=Double(m)
    factor.primalStatistics.seconds["primalIterations"]=Double(iteration)
    factor.primalStatistics.seconds["primalWorkingRows"]=Double(m)
    // Same internal barrier rule as GlobalSchurSession; all acceptance gates,
    // regularization, iteration caps and source rows remain unchanged.
    if parity {return try recover(mu)}
    return RopeContactSystem.Solution(base:x,border:b,multipliers:mu.map{-$0},
      activeIDs:rows.indices.filter{slack[$0]<1e-10})
   }
   guard iteration<maxIterations,m>0 else {
    throw RopePhysicsError.invalid("Primal contact iteration bound: stationarity \(norm(rd+rdb)), feasibility \(feasibility), contact \(norm(rp))")
   }
   let diagonal=rows.indices.map{1/(epsilon+slack[$0]/mu[$0])}
   guard diagonal.allSatisfy({$0.isFinite && $0>0}) else {throw RopePhysicsError.invalid("Invalid contact Newton weights")}
   if let prepared {try prepared.refactor(diagonal:diagonal)}
   else {prepared=try SparseNewtonPrepared(factor:factor,contacts:rows,diagonal:diagonal)}
   let augmented=prepared!
   let off:[Int]=[],nonlocal=Set<Int>()
   func direction(_ rc:[Double]) throws -> (x:[Double],b:[Double],mu:[Double],slack:[Double]) {
    let contactRHS=rows.indices.map{rp[$0]+rc[$0]/mu[$0]}
    var force=rd,forceBorder=rdb
    for id in rows.indices where !nonlocal.contains(id) {
     let scaled=diagonal[id]*contactRHS[id],c=rows[id]
     for k in c.indices.indices {force[c.indices[k]] += c.coefficients[k]*scaled}
     for k in 0..<nb {forceBorder[k] += c.border[k]*scaled}
    }
    forceBorder += off.map{contactRHS[$0]}
    let solution=try augmented.refined(force,forceBorder),dx=solution.base,db=Array(solution.border.prefix(nb))
    let dm=rows.indices.map{diagonal[$0]*(contactRHS[$0]-value(rows[$0],dx,db))}
    let ds=rows.indices.map{(rc[$0]-slack[$0]*dm[$0])/mu[$0]}
    return (dx,db,dm,ds)
   }
   let affine=try direction(rows.indices.map{-slack[$0]*mu[$0]})
   let ap=fraction(slack,affine.slack),ad=fraction(mu,affine.mu)
   let mean=zip(slack,mu).reduce(0.0){$0+$1.0*$1.1}/Double(m)
   let predicted=rows.indices.reduce(0.0){$0+(slack[$1]+ap*affine.slack[$1])*(mu[$1]+ad*affine.mu[$1])}/Double(m)
   let sigma=pow(min(1,max(0,predicted/mean)),3)
   let corrected=try direction(rows.indices.map{sigma*mean-slack[$0]*mu[$0]-affine.slack[$0]*affine.mu[$0]})
   let primalFraction=fraction(slack,corrected.slack,0.995),dualFraction=fraction(mu,corrected.mu,0.995)
   for i in x.indices {x[i] += (equalities.contains(i) ? dualFraction:primalFraction)*corrected.x[i]}
   for i in b.indices {b[i] += primalFraction*corrected.b[i]}
   for i in rows.indices {mu[i] += dualFraction*corrected.mu[i];slack[i] += primalFraction*corrected.slack[i]}
   guard (x+b+mu+slack).allSatisfy({$0.isFinite}) else {throw RopePhysicsError.invalid("Nonfinite primal contact iterate")}
  }
  throw RopePhysicsError.invalid("Unreachable contact screen")
 }
}
