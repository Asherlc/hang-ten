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
 func primalPrepared(borderColumns:[[Double]],borderMatrix:[[Double]],equalities:[Int]=[]) throws -> PrimalPrepared {
  try PrimalPrepared(system:self,columns:borderColumns,borderMatrix:borderMatrix,equalities:equalities)
 }
}

struct PrimalPrepared {
 let system:RopeBandedSystem,columns:[[Double]],borderMatrix:[[Double]],equalities:[Int]
 let factor:RopeBandedFactorization
 var baseCount:Int {system.size}
 var borderCount:Int {columns.count}
 init(system:RopeBandedSystem,columns:[[Double]],borderMatrix:[[Double]],equalities:[Int]) throws {
  self.system=system;self.columns=columns;self.borderMatrix=borderMatrix;self.equalities=equalities
  factor=try system.factorized(borderColumns:columns,borderMatrix:borderMatrix)
 }
 func solve(rhs:[Double],borderRHS:[Double]) throws -> (base:[Double],border:[Double]) {
  try factor.solve(rhs:rhs,borderRHS:borderRHS)
 }
 func product(_ base:[Double],_ border:[Double])->(base:[Double],border:[Double]) {
  var result=system.product(base),b=Array(repeating:0.0,count:borderCount)
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
}
