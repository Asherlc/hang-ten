// Workspace-only original-matrix access for the primal Newton screen.
extension RopeBandedSystem {
 func lowerEntries()->[(Int,Int,Double)] {
  var entries:[(Int,Int,Double)]=[]
  for column in 0..<size {for row in column...min(size-1,column+bandwidth) {
   let v=matrix[2*bandwidth+row-column+column*leadingDimension]
   if v != 0 {entries.append((row,column,v))}
  }}
  return entries
 }
 func product(_ vector:[Double])->[Double] {
  var result=Array(repeating:0.0,count:size)
  for column in 0..<size {
   for row in max(0,column-bandwidth)...min(size-1,column+bandwidth) {
    result[row] += matrix[2*bandwidth+row-column+column*leadingDimension]*vector[column]
   }
  }
  return result
 }
 func blasProduct(_ vector:[Double])->[Double] {
  precondition(vector.count == size)
  var result=Array(repeating:0.0,count:size)
  var trans:Int8=78,n=__LAPACK_int(size),band=__LAPACK_int(bandwidth)
  var leading=__LAPACK_int(leadingDimension),stride:__LAPACK_int=1
  var alpha=1.0,beta=0.0
  // DGBTRF stores the original diagonal at 2*bandwidth; DGBMV expects
  // bandwidth. Offset the input pointer, retaining the physical column stride.
  matrix.withUnsafeBufferPointer {values in
   vector.withUnsafeBufferPointer {input in
    dgbmv_(&trans,&n,&n,&band,&band,&alpha,values.baseAddress!+bandwidth,
      &leading,input.baseAddress!,&stride,&beta,&result,&stride)
   }
  }
  return result
 }
 func primalPrepared(borderColumns:[[Double]],borderMatrix:[[Double]],equalities:[Int]=[]) throws -> PrimalPrepared {
  try PrimalPrepared(system:self,columns:borderColumns,borderMatrix:borderMatrix,equalities:equalities)
 }
}

final class ResponseConstructionProfile {
 var seconds:[String:Double]=[:]
 func now()->Double {ProcessInfo.processInfo.systemUptime}
 func record(_ key:String,_ start:Double) {seconds[key,default:0] += now()-start}
 func count(_ key:String,_ count:Int=1) {seconds[key,default:0] += Double(count)}
}

struct PrimalPrepared {
 let system:RopeBandedSystem,columns:[[Double]],borderMatrix:[[Double]],equalities:[Int]
 let factor:RopeBandedFactorization
 let useBLASProducts:Bool
 let responseProfile:ResponseConstructionProfile?
 let primalProfile:ResponseConstructionProfile?
 let primalStatistics=ResponseConstructionProfile()
 var baseCount:Int {system.size}
 var borderCount:Int {columns.count}
 init(system:RopeBandedSystem,columns:[[Double]],borderMatrix:[[Double]],equalities:[Int]) throws {
  self.system=system;self.columns=columns;self.borderMatrix=borderMatrix;self.equalities=equalities
  useBLASProducts=ProcessInfo.processInfo.environment["HANGTEN_BLAS_RESPONSE_PRODUCT"] == "1"
  responseProfile=ProcessInfo.processInfo.environment["HANGTEN_PROFILE_CONTACT_RESPONSES"] == "1" ? ResponseConstructionProfile() : nil
  primalProfile=ProcessInfo.processInfo.environment["HANGTEN_PROFILE_PRIMAL"] == "1" ? ResponseConstructionProfile() : nil
  responseProfile?.count("responseProfileCumulative",1)
  primalProfile?.count("primalProfileCumulative",1)
  responseProfile?.count("responseBaseCount",system.size)
  responseProfile?.count("responseBandwidth",system.bandwidth)
  let started=primalProfile?.now() ?? 0
  factor=try system.factorized(borderColumns:columns,borderMatrix:borderMatrix)
  primalProfile?.record("primalPreparedSeconds",started)
 }
 func solve(rhs:[Double],borderRHS:[Double]) throws -> (base:[Double],border:[Double]) {
  try factor.solve(rhs:rhs,borderRHS:borderRHS)
 }
 func product(_ base:[Double],_ border:[Double])->(base:[Double],border:[Double]) {
  var result=useBLASProducts ? system.blasProduct(base) : system.product(base)
  var b=Array(repeating:0.0,count:borderCount)
  for i in 0..<borderCount {
   for k in base.indices {result[k] += columns[i][k]*border[i];b[i] += columns[i][k]*base[k]}
   for j in 0..<borderCount {b[i] += borderMatrix[i][j]*border[j]}
  }
  return (result,b)
 }
 func refined(_ rhs:[Double],_ borderRHS:[Double]) throws -> (base:[Double],border:[Double]) {
  var result=try solve(rhs:rhs,borderRHS:borderRHS)
  for _ in 0..<3 {
   let product=product(result.base,result.border)
   let error=zip(rhs,product.base).map(-),borderError=zip(borderRHS,product.border).map(-)
   if (error+borderError).map({abs($0)}).max()!<=1e-12*max(1,(rhs+borderRHS).map({abs($0)}).max()!) {break}
   let correction=try solve(rhs:error,borderRHS:borderError)
   result=(zip(result.base,correction.base).map(+),zip(result.border,correction.border).map(+))
  }
  return result
 }
 func refinedBatch(_ rhs:[[Double]],_ borderRHS:[[Double]]) throws -> [(base:[Double],border:[Double])] {
  let batchStarted=responseProfile?.now() ?? 0
  defer {responseProfile?.record("responseBatchSeconds",batchStarted)}
  let count=rhs.count,n=baseCount,nb=borderCount
  guard count<=64,count<=500_000/(n+nb),borderRHS.count==count,
   rhs.allSatisfy({$0.count==n && $0.allSatisfy({$0.isFinite})}),
   borderRHS.allSatisfy({$0.count==nb && $0.allSatisfy({$0.isFinite})}) else {
   throw RopePhysicsError.invalid("Invalid bounded response batch")
  }
  if count==0 {return []}
  var result=try factor.solveBatch(rhs:rhs.flatMap{$0},borderRHS:borderRHS.flatMap{$0},count:count,profile:responseProfile)
  let limits=(0..<count).map {j in
   1e-12*max(1,(rhs[j]+borderRHS[j]).map{abs($0)}.max()!)
  }
  var converged=Array(repeating:false,count:count)
  for _ in 0..<3 {
   let residualStarted=responseProfile?.now() ?? 0
   var error=Array(repeating:0.0,count:n*count),borderError=Array(repeating:0.0,count:nb*count)
   for j in 0..<count where !converged[j] {
    let productStarted=responseProfile?.now() ?? 0
    let value=product(Array(result.base[j*n..<(j+1)*n]),Array(result.border[j*nb..<(j+1)*nb]))
    responseProfile?.record("responseProductSeconds",productStarted)
    responseProfile?.count("responseProductCalls")
    var maximum=0.0
    for k in 0..<n {
     let e=rhs[j][k]-value.base[k]
     guard e.isFinite else {throw RopePhysicsError.invalid("Nonfinite batch refinement residual")}
     error[j*n+k]=e;maximum=max(maximum,abs(e))
    }
    for k in 0..<nb {
     let e=borderRHS[j][k]-value.border[k]
     guard e.isFinite else {throw RopePhysicsError.invalid("Nonfinite batch refinement residual")}
     borderError[j*nb+k]=e;maximum=max(maximum,abs(e))
    }
    if maximum<=limits[j] {
     converged[j]=true
     for k in 0..<n {error[j*n+k]=0}
     for k in 0..<nb {borderError[j*nb+k]=0}
    }
   }
   responseProfile?.record("responseResidualSeconds",residualStarted)
   if converged.allSatisfy({$0}) {break}
   responseProfile?.count("responseRefinementSolves")
   let correction=try factor.solveBatch(rhs:error,borderRHS:borderError,count:count,profile:responseProfile)
   for j in 0..<count where !converged[j] {
    for k in 0..<n {result.base[j*n+k] += correction.base[j*n+k]}
    for k in 0..<nb {result.border[j*nb+k] += correction.border[j*nb+k]}
   }
  }
  guard (result.base+result.border).allSatisfy({$0.isFinite}) else {
   throw RopePhysicsError.invalid("Nonfinite refined response batch")
  }
  return (0..<count).map {j in
   (Array(result.base[j*n..<(j+1)*n]),Array(result.border[j*nb..<(j+1)*nb]))
  }
 }
}

// This extension compiles in the same captured file as the authoritative
// factor. It reads immutable factors; only independent RHS columns mutate.
extension RopeBandedFactorization {
 func solveBatch(rhs:[Double],borderRHS:[Double],count:Int,profile:ResponseConstructionProfile?=nil) throws -> (base:[Double],border:[Double]) {
  let nb=columns.count
  guard (1...64).contains(count),count<=500_000/(size+nb),
   rhs.count==size*count,borderRHS.count==nb*count,
   (rhs+borderRHS).allSatisfy({$0.isFinite}) else {
   throw RopePhysicsError.invalid("Invalid reusable rope batch load")
  }
  var base=rhs,border=borderRHS
  var trans:Int8=78,n=__LAPACK_int(size),kl=__LAPACK_int(bandwidth),ku=kl
  var nrhs=__LAPACK_int(count),ldab=__LAPACK_int(leadingDimension),ldb=n,info:__LAPACK_int=0
  let bandStarted=profile?.now() ?? 0
  band.withUnsafeBufferPointer {numeric in
   pivots.withUnsafeBufferPointer {indices in
    dgbtrs_(&trans,&n,&kl,&ku,&nrhs,numeric.baseAddress!,&ldab,indices.baseAddress!,&base,&ldb,&info)
   }
  }
  profile?.record("responseBandSolveSeconds",bandStarted)
  profile?.count("responseBandSolveCalls")
  guard info==0 else {throw RopePhysicsError.invalid("Invalid reusable rope batch solve (\(info))")}
  if nb>0 {
   let borderStarted=profile?.now() ?? 0
   for j in 0..<count {for i in 0..<nb {
    var dot=0.0
    for k in 0..<size {dot += columns[i][k]*base[j*size+k]}
    border[j*nb+i] -= dot
   }}
   var borderSize=__LAPACK_int(nb),lda=borderSize,borderLeading=borderSize
   schur.withUnsafeBufferPointer {numeric in
    schurPivots.withUnsafeBufferPointer {indices in
     dgetrs_(&trans,&borderSize,&nrhs,numeric.baseAddress!,&lda,indices.baseAddress!,&border,&borderLeading,&info)
    }
   }
   guard info==0 else {throw RopePhysicsError.invalid("Invalid reusable rope batch border solve (\(info))")}
   for j in 0..<count {for k in 0..<size {for i in 0..<nb {
    base[j*size+k] -= inverseColumns[i*size+k]*border[j*nb+i]
   }}}
   profile?.record("responseBorderSeconds",borderStarted)
  }
  guard (base+border).allSatisfy({$0.isFinite}) else {throw RopePhysicsError.invalid("Nonfinite reusable rope batch result")}
  return (base,border)
 }
}
