import Foundation
func retainedInitializerFixtures()throws {
    var system=try RopeBandedSystem(size:3,bandwidth:2)
    try system.addSymmetric(row:0,column:0,value:2)
    try system.addSymmetric(row:2,column:2,value:3)
    try system.addSymmetric(row:1,column:1,value:-1e-8)
    try system.addSymmetric(row:0,column:1,value:1)
    let factor=try system.factorized(borderColumns:[[0,0.3,0]],borderMatrix:[[7]])
    let unconstrained=try factor.solve(rhs:[0,-0.01,0],borderRHS:[0])
    let contact=RopeLinearContact(indices:[0,2],coefficients:[-0.5,1],border:[0.2],residual:-0.1)
    let solved=try RopeContactSystem.solve(factor:factor,base:unconstrained.base,border:unconstrained.border,
        contacts:[contact],retainOperator:true)
    guard let prepared=solved.retained,solved.activeIDs==[0] else {throw RopePhysicsError.invalid("retain actual converged active KKT")}
    func dense(_ a0:[[Double]],_ b0:[Double])->[Double] {
        var a=a0,b=b0
        for k in b.indices {
            let pivot=(k..<b.count).max{abs(a[$0][k])<abs(a[$1][k])}!
            if pivot != k {a.swapAt(pivot,k);b.swapAt(pivot,k)}
            for i in (k+1)..<b.count {
                let f=a[i][k]/a[k][k]
                for j in k..<b.count {a[i][j] -= f*a[k][j]}
                b[i] -= f*b[k]
            }
        }
        var x=b
        for i in b.indices.reversed() {
            for j in (i+1)..<b.count {x[i] -= a[i][j]*x[j]}
            x[i] /= a[i][i]
        }
        return x
    }
    let matrix:[[Double]]=[[2,1,0,0,-0.5],[1,-1e-8,0,0.3,0],[0,0,3,0,1],[0,0.3,0,7,0.2],[-0.5,0,1,0.2,-1e-8]]
    var outputs:[[Double]]=[]
    for rhs in [[0.0,-0.02,0,0,0.13],[0.1,0.005,-0.01,-0.03,0.09],[0,-0.02,0,0,0.13]] {
        let out=try prepared.solveLoads(rhs:Array(rhs.prefix(3)),borderRHS:[rhs[3]],contactResiduals:[-rhs[4]])
        let expected=dense(matrix,rhs),values=out.base+out.border
        guard zip(values,expected.prefix(4)).allSatisfy({abs($0-$1)<1e-10}) else {throw RopePhysicsError.invalid("retained KKT independent dense oracle")}
        outputs.append(values)
    }
    guard outputs[0].map({$0.bitPattern})==outputs[2].map({$0.bitPattern}) else {throw RopePhysicsError.invalid("immutable retained operator loads")}
    print("PASS retained active KKT independent loads/immutability")
}
