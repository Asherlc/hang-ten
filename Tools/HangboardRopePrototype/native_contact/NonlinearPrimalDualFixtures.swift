import Foundation
do {
    // Catches omitted h, compression/equality signs and double affine addition.
    let d=try NonlinearPrimalDual.eliminate(s:0.4,v:0.2,h:0.05,rc: -0.079)
    let matrix=try NonlinearPrimalDualFactor(size:2,equalities:[0],entries:[(1,1,2+4*d.diagonal),(0,0,-1e-8),(1,0,1)])
    let solved=try matrix.solve([0.03,-0.7+2*d.load])
    let dl=solved[0],dx=solved[1]
    let contact=try NonlinearPrimalDual.recover(s:0.4,v:0.2,h:0.05,rc: -0.079,jdx:2*dx)
    guard abs(2*dx+dl-2*contact.s+0.7)<1e-11,
          abs(dx-1e-8*dl-0.03)<1e-11,
          abs(2*dx+1e-8*contact.s-contact.v+0.05)<1e-11,
          abs(0.2*contact.s+0.4*contact.v+0.079)<1e-11 else {throw RopePhysicsError.invalid("Eliminated direction does not recover four original equations")}
    print("PASS full four-equation recovery with nonzero gap residual")
    let corrected=try NonlinearPrimalDual.eliminate(s:0.4,v:0.2,h:0.05,rc: -0.099)
    let corrector=try matrix.solve([0.03,-0.7+2*corrected.load])
    let c=try NonlinearPrimalDual.recover(s:0.4,v:0.2,h:0.05,rc: -0.099,jdx:2*corrector[1])
    guard abs(0.2*c.s+0.4*c.v+0.099)<1e-11,abs(corrector[1]-1e-8*corrector[0]-0.03)<1e-11 else {throw RopePhysicsError.invalid("Corrector cross term or full RHS accounting wrong")}
    print("PASS corrector includes affine cross term once")
    let coupled=try NonlinearPrimalDualFactor(size:4,equalities:[1],entries:[(0,0,3),(1,1,-1e-8),(2,2,4),(3,3,5),
        (1,0,1),(2,0,-0.4),(3,0,-0.6),(2,1,-1),(3,1,1),(3,2,0.5)])
    let x=try coupled.solve([1,0.699999997,-1.93,0.48])
    let want=[0.2,0.3,-0.4,0.1]
    guard zip(x,want).allSatisfy({abs($0-$1)<1e-10}) else {throw RopePhysicsError.invalid("Signed tension/shared-height saddle coupling wrong")}
    print("PASS signed tension and shared-height saddle solve")
    // Four-particle/nonlocal coupling cannot be dropped to fit the band.
    var terms=(0..<13).map{($0,$0,$0==6 ? -1e-8:2.0)}
    terms += [(0,0,1),(11,11,1),(11,0,-1),(6,0,1),(11,6,1),(12,6,-1)]
    let nonlocal=try NonlinearPrimalDualFactor(size:13,equalities:[6],entries:terms)
    var rhs=Array(repeating:0.0,count:13);rhs[0]=1.1;rhs[11] = -0.1;rhs[12]=0.2;rhs[6] = -0.200000004
    let y=try nonlocal.solve(rhs)
    guard abs(y[0]-0.2)<1e-9,abs(y[11]+0.1)<1e-9,abs(y[12]-0.3)<1e-9,abs(y[6]-0.4)<1e-9 else {throw RopePhysicsError.invalid("Nonlocal coupling omitted or wrong")}
    print("PASS nonlocal cross-particle coupling")
    let fraction=try NonlinearPrimalDual.fraction(values:[0.2,0.4],change:[-0.4,0.1],safety:0.995)
    guard abs(fraction-0.4975)<1e-15,0.2+fraction*(-0.4)>0 else {throw RopePhysicsError.invalid("Strict positivity fraction wrong")}
    do {_ = try NonlinearPrimalDual.eliminate(s:0,v:1,h:0,rc:0);throw RopePhysicsError.invalid("Zero compression accepted")}
    catch RopePhysicsError.invalid(let reason) {guard reason != "Zero compression accepted" else {throw RopePhysicsError.invalid(reason)}}
    print("PASS strict positivity and invalid input rejection")
} catch {print("FAIL",error);exit(1)}
