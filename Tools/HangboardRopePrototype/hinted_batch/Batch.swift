extension RopeBandedFactorization {
 func solveBatch(rhs:[Double],borderRHS:[Double],count:Int) throws -> (base:[Double],border:[Double]) {
  let nb=columns.count
  guard (1...64).contains(count),count<=500_000/(size+nb),
   rhs.count==size*count,borderRHS.count==nb*count,
   (rhs+borderRHS).allSatisfy({$0.isFinite}) else {
   throw RopePhysicsError.invalid("Invalid reusable rope batch load")
  }
  var base=rhs,border=borderRHS
  var trans:Int8=78,n=__LAPACK_int(size),kl=__LAPACK_int(bandwidth),ku=kl
  var nrhs=__LAPACK_int(count),ldab=__LAPACK_int(leadingDimension),ldb=n,info:__LAPACK_int=0
  band.withUnsafeBufferPointer {numeric in
   pivots.withUnsafeBufferPointer {indices in
    dgbtrs_(&trans,&n,&kl,&ku,&nrhs,numeric.baseAddress!,&ldab,indices.baseAddress!,&base,&ldb,&info)
   }
  }
  guard info==0 else {throw RopePhysicsError.invalid("Invalid reusable rope batch solve (\(info))")}
  if nb>0 {
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
  }
  guard (base+border).allSatisfy({$0.isFinite}) else {throw RopePhysicsError.invalid("Nonfinite reusable rope batch result")}
  return (base,border)
 }
}
