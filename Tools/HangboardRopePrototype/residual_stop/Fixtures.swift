// Independent direct regularized KKT solves verify signs and coupled height.
do {
    var system=try RopeBandedSystem(size:2,bandwidth:0)
    try system.addSymmetric(row:0,column:0,value:2)
    try system.addSymmetric(row:1,column:1,value:3)
    let factor=try system.factorized(borderColumns:[[0,0]],borderMatrix:[[5]])
    let contacts=[RopeLinearContact(indices:[0,1],coefficients:[-1,1],border:[0],residual:-1),
                  RopeLinearContact(indices:[0],coefficients:[1],border:[-1],residual:-0.25)]
    let solved=try RopeContactSystem.solve(factor:factor,base:[0,0],border:[0],contacts:contacts)
    guard solved.activeIDs==[0,1],let op=solved.residualOperator else {fatalError("Fixture active set")}
    for k in 1...8 {
        let rhs=[0.2*Double(k),-0.1*Double(k)],height=[0.05*Double(k)],residual=[0.03*Double(k),-0.04*Double(k)]
        let x=try op.solve(rhs:rhs,borderRHS:height,contactResiduals:residual)
        let direct=try system.solve(rhs:rhs,borderColumns:[[0,0],[-1,1],[1,0]],
            borderMatrix:[[5,0,-1],[0,-1e-8,0],[-1,0,-1e-8]],borderRHS:height+residual.map{-($0)})
        let expected=direct.base+direct.border
        guard zip(x.base+x.border+x.contactDelta,expected).allSatisfy({abs($0.0-$0.1)<1e-12}) else {fatalError("Residual KKT sign/coupling")}
        let flipped=try op.solve(rhs:rhs,borderRHS:height,contactResiduals:residual.map{-($0)})
        guard zip(flipped.base+flipped.border,Array(expected.prefix(3))).contains(where:{abs($0.0-$0.1)>1e-5}) else {fatalError("RED wrong residual sign was invisible")}
    }
    print("PASS eight independent direct active-KKT residual solves; reversed-sign RED rejected")
}
do {
    var system=try RopeBandedSystem(size:3,bandwidth:2)
    try system.addSymmetric(row:0,column:0,value:0.005)
    try system.addSymmetric(row:1,column:1,value:0.005)
    try system.addSymmetric(row:2,column:0,value:-1)
    try system.addSymmetric(row:2,column:1,value:1)
    try system.addSymmetric(row:2,column:2,value:-1e-8)
    let factor=try system.factorized(borderColumns:[[0,0,-1]],borderMatrix:[[1]])
    let base=try factor.solve(rhs:[0,0,-0.022],borderRHS:[-0.004])
    let contact=RopeLinearContact(indices:[0,1],coefficients:[1,-1],border:[0],residual:-0.03)
    let solved=try RopeContactSystem.solve(factor:factor,base:base.base,border:base.border,contacts:[contact])
    guard let op=solved.residualOperator,solved.activeIDs==[0] else {fatalError("Fixture equality active set")}
    let rhs=[0.0002,-0.0001,0.00003],height=[0.00005],residual=[0.00004]
    let x=try op.solve(rhs:rhs,borderRHS:height,contactResiduals:residual)
    let direct=try system.solve(rhs:rhs,borderColumns:[[0,0,-1],[1,-1,0]],
        borderMatrix:[[1,0],[0,-1e-8]],borderRHS:height+residual.map{-($0)})
    guard zip(x.base+x.border+x.contactDelta,direct.base+direct.border).allSatisfy({abs($0.0-$0.1)<1e-10}) else {fatalError("Residual equality KKT")}
    print("PASS independent equality+contact+height residual KKT")
}
