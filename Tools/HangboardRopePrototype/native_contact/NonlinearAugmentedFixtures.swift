import Foundation
import simd

// These fixtures catch force-sign/clamp, energy-gradient, regularization,
// inactive curvature, shared-block mass, and nonfinite-input mistakes.
do {
    let compressive = try NonlinearAugmented.force(-0.1,dual:-0.2,penalty:2,contact:true)
    guard abs(compressive + 0.3999999920000002)<1e-14 else {throw RopePhysicsError.invalid("Compressive augmented force missing or wrong sign")}
    let released = try NonlinearAugmented.force(0.2,dual:-0.2,penalty:2,contact:true)
    guard released == 0,try NonlinearAugmented.curvature(0.2,dual:-0.2,penalty:2,contact:true)==0 else {throw RopePhysicsError.invalid("Separating contact pulls or adds active curvature")}
    print("PASS compressive force and separating contact release")
    let delta=1e-6
    let a=try NonlinearAugmented.energy(-0.1+delta,dual:-0.2,penalty:2,contact:true)
    let b=try NonlinearAugmented.energy(-0.1-delta,dual:-0.2,penalty:2,contact:true)
    guard abs((a-b)/(2*delta)-compressive)<1e-10 else {throw RopePhysicsError.invalid("Augmented gradient is not energy derivative")}
    print("PASS actual augmented energy derivative")
    // At lambda=-3, C=-3e-8, the regularized contact is already a fixed point.
    let fixed=try NonlinearAugmented.force(-3e-8,dual:-3,penalty:1e8,contact:true)
    guard abs(fixed + 3)<1e-14 else {throw RopePhysicsError.invalid("Original epsilon target hardened or shifted")}
    print("PASS original regularized fixed point")
    let dx=try NonlinearAugmented.direction(masses:[2],offset:[0],gradients:[[1]],
        residuals:[-1],duals:[0],penalties:[2.0/3],contacts:[false])
    guard abs(dx[0]-0.25)<1e-8 else {throw RopePhysicsError.invalid("Shared constraint first-block response wrong")}
    let dy=try NonlinearAugmented.direction(masses:[1],offset:[0],gradients:[[-1]],
        residuals:[dx[0]-1],duals:[0],penalties:[2.0/3],contacts:[false])
    guard abs(dy[0]+0.3)<1e-8 else {throw RopePhysicsError.invalid("Shared constraint loses coupling after position update")}
    print("PASS sequential primal blocks share updated constraint geometry")
    let plane=try NonlinearAugmented.direction(masses:[2,3,4],offset:[0,0,0],gradients:[[1,1,0]],
        residuals:[-1],duals:[0],penalties:[1],contacts:[true])
    // (diag(2,3,4)+jj^T)dx=j gives [3/11,2/11,0], before tiny epsilon.
    guard abs(plane[0]-3.0/11)<1e-8,abs(plane[1]-2.0/11)<1e-8,plane[2]==0 else {throw RopePhysicsError.invalid("Three-coordinate SPD block response wrong")}
    print("PASS coupled three-coordinate block")
    do {
        _ = try NonlinearAugmented.force(.nan,dual:0,penalty:1,contact:true)
        throw RopePhysicsError.invalid("Nonfinite force accepted")
    } catch RopePhysicsError.invalid(let reason) {
        guard reason != "Nonfinite force accepted" else {throw RopePhysicsError.invalid(reason)}
    }
    do {
        _ = try NonlinearAugmented.direction(masses:[0],offset:[0],gradients:[],residuals:[],duals:[],penalties:[],contacts:[])
        throw RopePhysicsError.invalid("Zero-mass block accepted")
    } catch RopePhysicsError.invalid(let reason) {
        guard reason != "Zero-mass block accepted" else {throw RopePhysicsError.invalid(reason)}
    }
    print("PASS invalid numeric and block inputs reject")
} catch {print("FAIL",error);exit(1)}
