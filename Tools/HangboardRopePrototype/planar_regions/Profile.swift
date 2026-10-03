// Serial, opt-in corpus diagnosis only. No product timing or concurrent use.
import Foundation
enum RopeRegionProfile {
    nonisolated(unsafe) static var enabled=false
    nonisolated(unsafe) static var seconds=Array(repeating:0.0,count:5)
    nonisolated(unsafe) static var calls=Array(repeating:0,count:5)
    static func begin()->Double? {enabled ? ProcessInfo.processInfo.systemUptime:nil}
    static func end(_ bucket:Int,_ start:Double?) {
        guard let start else{return}
        seconds[bucket] += ProcessInfo.processInfo.systemUptime-start
        calls[bucket] += 1
    }
    static func reset() {seconds=Array(repeating:0,count:5);calls=Array(repeating:0,count:5)}
}

func regionOutputBits(_ values:[[[RopeSegmentContact]]])->[UInt64] {
    var bits:[UInt64]=[UInt64(values.count)]
    for output in values {
        bits.append(UInt64(output.count))
        for hits in output {
            bits.append(UInt64(hits.count))
            for hit in hits {
                for point in [hit.centerlinePoint,hit.surfacePoint,hit.normal] {
                    bits += [point.x.bitPattern,point.y.bitPattern,point.z.bitPattern]
                }
                bits += [hit.fraction.bitPattern,hit.penetrationDepth.bitPattern]
            }
        }
    }
    return bits
}
