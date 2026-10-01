import Foundation
func fixture() throws {
 var system=try RopeBandedSystem(size:1,bandwidth:0)
 try system.addSymmetric(row:0,column:0,value:2)
 let factor=try system.factorized(borderColumns:[[0.5]],borderMatrix:[[1]])
 let row=RopeLinearContact(indices:[0],coefficients:[1],border:[1],residual:-1)
 let solved=try BlockImpulse.solve(factor:factor,base:[0],border:[0],contacts:[row])
 // Invert [[2,.5],[.5,1]], apply [1,1], then normalize by 8/7.
 guard abs(solved.base[0]-0.25)<1e-8,abs(solved.border[0]-0.75)<1e-8,
       abs(solved.multipliers[0]+0.875)<1e-8 else {fatalError("Shared-board response mismatch")}
 print("PASS coupled board response")
 guard !BlockImpulse.certifies([0,0],multipliers:[-0.875],contacts:[row],size:1) else {fatalError("Uncertified recovered correction accepted")}
 guard !BlockImpulse.certifies([0.25,0.75],multipliers:[0.875],contacts:[row],size:1) else {fatalError("Tensile multiplier accepted")}
 guard !BlockImpulse.certifies([Double.nan,0],multipliers:[0],contacts:[row],size:1) else {fatalError("Nonfinite correction accepted")}
 print("PASS returned-vector certificate rejects gap, sign and nonfinite failures")
 let empty=try BlockImpulse.solve(factor:factor,base:[0],border:[0],contacts:[])
 guard empty.base == [0],empty.border == [0] else {fatalError("Unconstrained correction changed")}
 print("PASS empty unilateral set")
 let release=try BlockImpulse.solve(factor:factor,base:[0],border:[0],contacts:[
   RopeLinearContact(indices:[0],coefficients:[1],border:[1],residual:1)])
 guard release.base == [0],release.border == [0],release.multipliers == [0] else {fatalError("Separating row pulls rope")}
 print("PASS separating contacts exert no force")
 do {
   _ = try BlockImpulse.solve(factor:factor,base:[0],border:[0],contacts:[
      RopeLinearContact(indices:[0],coefficients:[1],border:[0],residual:-1),
      RopeLinearContact(indices:[0],coefficients:[-1],border:[0],residual:0)])
   fatalError("Contradictory affine rows falsely certified")
 } catch RopePhysicsError.invalid {print("PASS conflicting rows reject within budget")}

}
do {try fixture()} catch {print("FAIL",error);exit(1)}
