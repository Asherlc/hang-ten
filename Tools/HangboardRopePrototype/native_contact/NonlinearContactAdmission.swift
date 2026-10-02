import Foundation

// Experimental auxiliary initialization only; not linked to the app.
enum NonlinearContactAdmission {
    struct Values {
        let s: Double
        let v: Double
        let normalizationS: Double
        let continued: Bool
    }

    static func initialize(residual: Double, scale: Double, coldS: Double,
                           priorMeanSV: Double?) throws -> Values {
        guard residual.isFinite,scale.isFinite,scale>0,coldS.isFinite,coldS>0 else {
            throw RopePhysicsError.invalid("Invalid contact admission inputs")
        }
        if let mu=priorMeanSV {
            guard mu.isFinite,mu>0 else {throw RopePhysicsError.invalid("Invalid existing contact mean complementarity")}
            if residual>0 {
                let s=min(coldS,mu/scale),v=residual+1e-8*s
                guard s.isFinite,s>0,v.isFinite,v>0 else {
                    throw RopePhysicsError.invalid("Invalid or underflowed contact continuation")
                }
                if v<=scale {
                    guard (s*v).isFinite,s*v>0 else {
                        throw RopePhysicsError.invalid("Underflowed contact continuation complementarity")
                    }
                    return Values(s:s,v:v,normalizationS:coldS,continued:true)
                }
            }
        }
        let v=max(residual+1e-8*coldS,scale)
        guard v.isFinite,v>0 else {throw RopePhysicsError.invalid("Invalid cold contact slack")}
        return Values(s:coldS,v:v,normalizationS:coldS,continued:false)
    }
}
