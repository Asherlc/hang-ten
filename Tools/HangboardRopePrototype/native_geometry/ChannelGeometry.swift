import Foundation
import simd

// Experimental proposal only. Full wall coverage, foreign wood and signedness
// have no general region certificate. Original mesh checks remain mandatory.
struct ExperimentUChannel {
    let center: SIMD3<Double>
    let bendRadius: Double
    let tubeRadius: Double
    let mouthZ: Double
    let envelope: Double
    init(center: SIMD3<Double>, bendRadius: Double, tubeRadius: Double,
         mouthZ: Double, envelope: Double) throws {
        guard (0..<3).allSatisfy({center[$0].isFinite}),
              [bendRadius,tubeRadius,mouthZ,envelope].allSatisfy({$0.isFinite}),
              bendRadius > tubeRadius, tubeRadius > 0, envelope >= 0,
              mouthZ > center.z else {throw RopePhysicsError.invalid("Invalid experimental U channel")}
        self.center=center;self.bendRadius=bendRadius;self.tubeRadius=tubeRadius
        self.mouthZ=mouthZ;self.envelope=envelope
    }
    private func projection(_ p: SIMD3<Double>) throws -> (core: SIMD3<Double>, arc: Double, leg: Int) {
        guard (0..<3).allSatisfy({p[$0].isFinite && abs(p[$0])<=10}) else {throw RopePhysicsError.invalid("Invalid tube point domain")}
        let x=p.x-center.x,z=p.z-center.z
        if z >= 0 {
            let side=x >= 0 ? 1.0 : -1.0
            return (SIMD3(center.x+side*bendRadius,center.y,p.z),side*(bendRadius*Double.pi/2+z),Int(side))
        }
        let rho=hypot(x,z)
        return (center+SIMD3(bendRadius*x/rho,0,bendRadius*z/rho),
            bendRadius*(atan2(z,x)+Double.pi/2),0)
    }
    func core(_ p: SIMD3<Double>) throws -> SIMD3<Double> {try projection(p).core}
    func eligible(_ p: SIMD3<Double>) throws -> Bool {
        let projected=try projection(p)
        return p.z < mouthZ && simd_distance(p,projected.core)<tubeRadius
    }
    // Matches the prior frozen-row proposal: fixed material rest length,
    // 0.5% strain gate, projected endpoint-offset allowance and wall envelope.
    func tightening(length: Double, radius: Double, clearance: Double) throws -> Double? {
        let capacity=tubeRadius-radius-clearance
        guard [length,radius,clearance,capacity].allSatisfy({$0.isFinite && $0>0}) else {
            throw RopePhysicsError.invalid("Invalid finite-radius fit")
        }
        let chord=length*1.005+2*capacity
        guard chord<2*bendRadius else {return nil}
        let arc=2*bendRadius*asin(chord/(2*bendRadius))
        let allowance=(arc*arc/(8*bendRadius)).nextUp
        return allowance+envelope<min(capacity,0.0001) ? allowance:nil
    }
    func row(_ p: SIMD3<Double>, radius: Double, clearance: Double,
             tightening: Double = 0) throws -> (residual: Double, gradient: SIMD3<Double>)? {
        guard [radius,clearance,tightening].allSatisfy({$0.isFinite}),radius>0,clearance>0,tightening>=0 else {
            throw RopePhysicsError.invalid("Invalid tube row")
        }
        let capacity=tubeRadius-radius-clearance-envelope-tightening
        guard capacity>0 else {throw RopePhysicsError.invalid("No eroded tube remains")}
        let delta=p-(try core(p)),distance=simd_length(delta)
        guard distance>1e-12 else {return nil}
        return (capacity-distance,-delta/distance)
    }
    func clearance(from a: SIMD3<Double>, to b: SIMD3<Double>) throws -> Double? {
        let pa=try projection(a),pb=try projection(b)
        let ea=simd_distance(a,pa.core),eb=simd_distance(b,pb.core)
        guard a.z<mouthZ,b.z<mouthZ,ea<tubeRadius,eb<tubeRadius else {return nil}
        // Interpolating a unit-speed C1 core path bounds chord error by
        // |s_b-s_a|² max|core''|/8. Legs have zero curvature; a junction or
        // lower semicircle has curvature at most 1/R. Endpoint offsets add
        // max(ea,eb). This tests the complete link, never just its midpoint.
        // Transcendental rounding and region validity are not certified here.
        let arc=abs(pb.arc-pa.arc)
        let allowance=pa.leg != 0 && pa.leg==pb.leg ? 0:(arc*arc/(8*bendRadius)).nextUp
        guard allowance+envelope<0.0001 else {return nil}
        return tubeRadius-max(ea,eb)-allowance-envelope
    }
}
