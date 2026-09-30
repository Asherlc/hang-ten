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

    func solve(rhs: [Double],borderColumns: [[Double]],borderMatrix: [[Double]],borderRHS: [Double]) throws
        -> (base: [Double],border: [Double]) {
        let count=borderColumns.count
        guard rhs.count==size,count<=32,borderRHS.count==count,borderMatrix.count==count,
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
