import Foundation
import simd

let channel = try ExperimentUChannel(center:.zero,bendRadius:0.006,tubeRadius:0.0037,
    mouthZ:0.033,envelope:0.0000164)
var failures=0
func check(_ name: String, _ action: () throws -> Bool) {
    do {if try action() {print("PASS",name)} else {failures+=1;print("FAIL",name)}}
    catch {failures+=1;print("FAIL",name,error)}
}
check("radius and original clearance are both subtracted") {
    guard let row=try channel.row(SIMD3(0.0061,0,0.01),radius:0.0035,clearance:0.0001) else {return false}
    return abs(row.residual + 0.0000164)<1e-15 && simd_distance(row.gradient,SIMD3(-1,0,0))<1e-15
}
check("free sliding leg gradient and inactive core") {
    guard let row=try channel.row(SIMD3(0.0061,0,0.01),radius:0.0035,clearance:0.0001) else {return false}
    return try row.gradient.z==0 && channel.row(SIMD3(0.006,0,0.01),radius:0.0035,clearance:0.0001)==nil
}
check("lower semicircle core and upper straight leg") {
    try simd_distance(channel.core(SIMD3(0,0,-0.0062)),SIMD3(0,0,-0.006))<1e-15 &&
        simd_distance(channel.core(SIMD3(0.0059,0,0.002)),SIMD3(0.006,0,0.002))<1e-15
}
check("rest-link allowance includes offsets and fixed strain limit") {
    guard let value=try channel.tightening(length:0.00077,radius:0.0035,clearance:0.0001) else {return false}
    return try value>0.000019 && value<0.000021 && channel.tightening(length:0.002,radius:0.0035,clearance:0.0001)==nil
}
check("straight whole link adds no artificial bend allowance") {
    guard let value=try channel.clearance(from:SIMD3(0.0061,0,0.01),to:SIMD3(0.0061,0,0.011)) else {return false}
    return abs(value-(0.0037-0.0001-0.0000164))<1e-15
}
check("bend chord accounts for interior despite on-core endpoints") {
    let theta=0.00077/0.006/2
    let a=SIMD3<Double>(-0.006*sin(theta),0,-0.006*cos(theta))
    let b=SIMD3<Double>(0.006*sin(theta),0,-0.006*cos(theta))
    guard let value=try channel.clearance(from:a,to:b) else {return false}
    let interior=0.0037-0.006*(1-cos(theta))
    return value<interior && interior-value<0.000017
}
check("mouth, distant and long opposite-leg links use fallback") {
    try channel.clearance(from:SIMD3(0.006,0,0.032),to:SIMD3(0.006,0,0.033))==nil &&
        channel.clearance(from:SIMD3(-0.006,0,0.01),to:SIMD3(0.006,0,0.01))==nil &&
        !channel.eligible(SIMD3(0,0,0.01))
}
check("G1 leg-bend junction keeps complete link") {
    guard let value=try channel.clearance(from:SIMD3(0.006,0,0.0002),
        to:SIMD3(0.006*cos(0.04),0,-0.006*sin(0.04))) else {return false}
    return value>0.00367 && value<0.0037-0.0000164
}
check("nonfinite coordinates reject before proposing a domain") {
    do {_ = try channel.eligible(SIMD3(.nan,0,0));return false} catch {return true}
}
print("fixtures",9,"failures",failures)
exit(failures==0 ? 0:1)
