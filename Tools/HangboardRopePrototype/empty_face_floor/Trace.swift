import Foundation
import simd
// Driver-thread state only. Masks are immutable during joined four-worker queries.
enum EmptyFaceFloor {
    struct Record {let bits:[UInt64];let drops:[[Bool]];let zeros:[[Bool]]}
    static var mode=0,cursor=0,seconds=0.0
    static var records:[Record]=[]
    static func bits(_ points:[SIMD3<Double>],_ rr:Double,_ rm:Double)->[UInt64] {
        [rr.bitPattern,rm.bitPattern]+points.flatMap{[$0.x.bitPattern,$0.y.bitPattern,$0.z.bitPattern]}
    }
    static func start(_ value:Int) {mode=value;cursor=0;seconds=0}
    static func begin(_ points:[SIMD3<Double>],_ rr:Double,_ rm:Double)->([[Bool]]?,Bool) {
        if mode==2 || mode==3 {
            precondition(cursor<records.count,"unexpected geometry evaluation")
            let record=records[cursor]
            precondition(record.bits==bits(points,rr,rm),"oracle configuration/schedule mismatch")
            cursor+=1
            return (mode==2 ? record.zeros:record.drops,false)
        }
        return (nil,mode==1)
    }
    static func end(_ points:[SIMD3<Double>],_ rr:Double,_ rm:Double,drops:[[Bool]],seconds elapsed:Double) {
        seconds+=elapsed
        if mode==1 {
            records.append(Record(bits:bits(points,rr,rm),drops:drops,zeros:drops.map{$0.map{_ in false}}))
        }
    }
}
