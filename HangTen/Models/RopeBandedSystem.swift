import Accelerate

/// Pivoted band LU plus a small Schur border. Local chain constraints stay
/// sparse; board height and nonlocal cord contacts occupy the border.
struct RopeBandedSystem: Sendable {
    let size: Int
    let bandwidth: Int
    private let leadingDimension: Int
    private var matrix: [Double]

    init(size: Int, bandwidth: Int) throws {
        guard size>0,size<50_000,bandwidth>=0,bandwidth<size,
              size*(3*bandwidth+1)<=8_000_000 else {
            throw RopePhysicsError.invalid("Invalid or excessive rope band system")
        }
        self.size=size;self.bandwidth=bandwidth
        leadingDimension=3*bandwidth+1
        matrix=Array(repeating:0,count:size*leadingDimension)
    }

    mutating func addSymmetric(row: Int,column: Int,value: Double) throws {
        guard (0..<size).contains(row),(0..<size).contains(column),
              abs(row-column)<=bandwidth,value.isFinite else {
            throw RopePhysicsError.invalid("Invalid or out-of-band rope matrix term")
        }
        matrix[2*bandwidth+row-column+column*leadingDimension] += value
        if row != column {matrix[2*bandwidth+column-row+row*leadingDimension] += value}
    }

    /// Reuse only while every matrix coefficient and border column is fixed.
    /// The immutable factor owns a snapshot; later authoring changes cannot
    /// alter it. Loads may change without another band or Schur factorization.
    func factorized(borderColumns:[[Double]],borderMatrix:[[Double]]) throws -> RopeBandedFactorization {
        try RopeBandedFactorization(size:size,bandwidth:bandwidth,matrix:matrix,
            borderColumns:borderColumns,borderMatrix:borderMatrix)
    }

    func solve(rhs: [Double],borderColumns: [[Double]],borderMatrix: [[Double]],borderRHS: [Double]) throws
        -> (base: [Double],border: [Double]) {
        let count=borderColumns.count
        // A thick loop can have many simultaneous nonlocal contact witnesses
        // near its attachment. Bound both border count and the working array;
        // a 32-row cap discarded otherwise valid contact manifolds.
        guard rhs.count==size,count<=256,size*(count+1)<=8_000_000,
              borderRHS.count==count,borderMatrix.count==count,
              borderColumns.allSatisfy({$0.count==size}),borderMatrix.allSatisfy({$0.count==count}),
              (rhs+borderRHS+borderColumns.flatMap{$0}+borderMatrix.flatMap{$0}+matrix).allSatisfy({$0.isFinite}) else {
            throw RopePhysicsError.invalid("Invalid rope linear solve")
        }
        var band=matrix,solutions=rhs+borderColumns.flatMap{$0}
        var n=__LAPACK_int(size),kl=__LAPACK_int(bandwidth),ku=kl,nrhs=__LAPACK_int(count+1)
        var ldab=__LAPACK_int(leadingDimension),ldb=n,info:__LAPACK_int=0
        var pivots=Array(repeating:__LAPACK_int(0),count:size)
        dgbsv_(&n,&kl,&ku,&nrhs,&band,&ldab,&pivots,&solutions,&ldb,&info)
        guard info==0 else {throw RopePhysicsError.invalid("Singular rope band factorization (\(info))")}
        let base=Array(solutions.prefix(size))
        guard base.allSatisfy({$0.isFinite}) else {throw RopePhysicsError.invalid("Nonfinite rope linear result")}
        guard count>0 else{return (base,[])}
        var schur=Array(repeating:0.0,count:count*count),border=borderRHS
        for i in 0..<count {
            border[i] -= zip(borderColumns[i],base).reduce(0){$0+$1.0*$1.1}
            for j in 0..<count {
                var value=borderMatrix[i][j]
                for k in 0..<size {value -= borderColumns[i][k]*solutions[(j+1)*size+k]}
                schur[i+j*count]=value
            }
        }
        var borderSize=__LAPACK_int(count),one:__LAPACK_int=1,borderLeading=borderSize
        var borderPivots=Array(repeating:__LAPACK_int(0),count:count)
        dgesv_(&borderSize,&one,&schur,&borderLeading,&borderPivots,&border,&borderLeading,&info)
        guard info==0 else {throw RopePhysicsError.invalid("Singular rope border factorization (\(info))")}
        var result=base
        for i in 0..<size {for j in 0..<count {result[i] -= solutions[(j+1)*size+i]*border[j]}}
        guard (result+border).allSatisfy({$0.isFinite}) else {throw RopePhysicsError.invalid("Nonfinite rope linear result")}
        return (result,border)
    }
}

/// LAPACK factors are immutable inputs to DGBTRS/DGETRS. Each solve owns only
/// its right-hand sides, so transactional copies can share the factors safely.
struct RopeBandedFactorization: Sendable {
    private let size:Int
    private let bandwidth:Int
    private let leadingDimension:Int
    private let band:[Double]
    private let pivots:[__LAPACK_int]
    private let columns:[[Double]]
    private let inverseColumns:[Double]
    private let schur:[Double]
    private let schurPivots:[__LAPACK_int]

    var baseCount: Int {size}
    var borderCount: Int {columns.count}

    fileprivate init(size:Int,bandwidth:Int,matrix:[Double],borderColumns:[[Double]],borderMatrix:[[Double]]) throws {
        let count=borderColumns.count,leadingDimension=3*bandwidth+1
        guard count<=256,size*(count+1)<=8_000_000,
              borderMatrix.count==count,borderColumns.allSatisfy({$0.count==size}),
              borderMatrix.allSatisfy({$0.count==count}),
              (matrix+borderColumns.flatMap{$0}+borderMatrix.flatMap{$0}).allSatisfy({$0.isFinite}) else {
            throw RopePhysicsError.invalid("Invalid reusable rope matrix")
        }
        var band=matrix,pivots=Array(repeating:__LAPACK_int(0),count:size)
        var n=__LAPACK_int(size),kl=__LAPACK_int(bandwidth),ku=kl,ldab=__LAPACK_int(leadingDimension),info:__LAPACK_int=0
        dgbtrf_(&n,&n,&kl,&ku,&band,&ldab,&pivots,&info)
        guard info==0 else {throw RopePhysicsError.invalid("Singular reusable rope band factorization (\(info))")}
        var inverseColumns=borderColumns.flatMap{$0}
        if count>0 {
            var trans:Int8=78,nrhs=__LAPACK_int(count),ldb=n
            dgbtrs_(&trans,&n,&kl,&ku,&nrhs,&band,&ldab,&pivots,&inverseColumns,&ldb,&info)
            guard info==0 else {throw RopePhysicsError.invalid("Invalid reusable rope border response (\(info))")}
        }
        var schur=Array(repeating:0.0,count:count*count)
        for i in 0..<count {for j in 0..<count {
            var value=borderMatrix[i][j]
            for k in 0..<size {value -= borderColumns[i][k]*inverseColumns[j*size+k]}
            schur[i+j*count]=value
        }}
        var schurPivots=Array(repeating:__LAPACK_int(0),count:count)
        if count>0 {
            var borderSize=__LAPACK_int(count),lda=borderSize
            dgetrf_(&borderSize,&borderSize,&schur,&lda,&schurPivots,&info)
            guard info==0 else {throw RopePhysicsError.invalid("Singular reusable rope border factorization (\(info))")}
        }
        guard (band+inverseColumns+schur).allSatisfy({$0.isFinite}) else {
            throw RopePhysicsError.invalid("Nonfinite reusable rope factor")
        }
        self.size=size;self.bandwidth=bandwidth;self.leadingDimension=leadingDimension
        self.band=band;self.pivots=pivots;columns=borderColumns
        self.inverseColumns=inverseColumns;self.schur=schur;self.schurPivots=schurPivots
    }

    func solve(rhs:[Double],borderRHS:[Double]) throws -> (base:[Double],border:[Double]) {
        let count=columns.count
        guard rhs.count==size,borderRHS.count==count,(rhs+borderRHS).allSatisfy({$0.isFinite}) else {
            throw RopePhysicsError.invalid("Invalid reusable rope load")
        }
        var base=rhs,border=borderRHS
        var trans:Int8=78,n=__LAPACK_int(size),kl=__LAPACK_int(bandwidth),ku=kl
        var nrhs:__LAPACK_int=1,ldab=__LAPACK_int(leadingDimension),ldb=n,info:__LAPACK_int=0
        // LAPACK declares these buffers as input-only. Passing their immutable
        // pointers avoids a copy of the factor on every contact response.
        band.withUnsafeBufferPointer {factor in
            pivots.withUnsafeBufferPointer {indices in
                dgbtrs_(&trans,&n,&kl,&ku,&nrhs,factor.baseAddress!,&ldab,indices.baseAddress!,&base,&ldb,&info)
            }
        }
        guard info==0 else {throw RopePhysicsError.invalid("Invalid reusable rope band solve (\(info))")}
        if count>0 {
            for i in 0..<count {border[i] -= zip(columns[i],base).reduce(0){$0+$1.0*$1.1}}
            var borderSize=__LAPACK_int(count),lda=borderSize,borderLeading=borderSize
            schur.withUnsafeBufferPointer {factor in
                schurPivots.withUnsafeBufferPointer {indices in
                    dgetrs_(&trans,&borderSize,&nrhs,factor.baseAddress!,&lda,indices.baseAddress!,&border,&borderLeading,&info)
                }
            }
            guard info==0 else {throw RopePhysicsError.invalid("Invalid reusable rope border solve (\(info))")}
            for i in 0..<size {for j in 0..<count {base[i] -= inverseColumns[j*size+i]*border[j]}}
        }
        guard (base+border).allSatisfy({$0.isFinite}) else {throw RopePhysicsError.invalid("Nonfinite reusable rope result")}
        return (base,border)
    }
}

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
