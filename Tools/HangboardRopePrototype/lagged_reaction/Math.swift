import Foundation
import simd

enum RopeLaggedReaction {
    static let h=1.0/240
    static let damping=exp(-18*h)
    static func position(_ prediction:Double,_ held:Double)->Double {
        prediction+held
    }
    static func fixtures()throws {
        var count=0
        for velocity in [-0.2,0.0,0.2] {for first in [-30.0,0.0,30.0] {for second in [-20.0,0.0,20.0] {
            let x=0.3,g = -9.81,h=Self.h,D=damping
            let free1=D*(velocity+g*h),reaction1=h*h*first
            let v1=free1+h*first,x1=x+h*v1
            let heldX=position(x+h*free1,reaction1),heldV=(heldX-x)/h
            let free2=D*(heldV+g*h),reaction2=h*h*second
            let actualX=heldX+h*free2+reaction2,actualV=(actualX-heldX)/h
            let v2=D*(v1+g*h)+h*second,x2=x1+h*v2
            guard abs(heldX-x1)<1e-14,abs(actualX-x2)<1e-14,abs(actualV-v2)<1e-13 else {
                throw RopePhysicsError.invalid("staggered first reaction must enter position and velocity once")
            }
            count += 1
        }}}
        // Old composed endpoint constant-force velocity is wrong when reactions change.
        let first=3.0,second = -4.0,h=Self.h,D=damping
        let delta=h*h*((1+D)*first+second)
        let composed=(1+D)/(2+D)*delta/h,exact=h*(D*first+second)
        guard abs(composed-exact)>1e-3 else {throw RopePhysicsError.invalid("changing-force endpoint negative control")}
        print("PASS staggered changing-force fixtures",count)
    }
}
