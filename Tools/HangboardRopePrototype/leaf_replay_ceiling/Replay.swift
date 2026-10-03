// Snapshot-only prerecorded candidate lists. This is never a production cache.
// Modes change on the driver only, outside the joined query workers.
import Foundation
private final class RopeLeafReplay:@unchecked Sendable {
    private let lock=NSLock()
    private var lists:[[UInt64]:[(Int,Int)]]=[:]
    private var entries=0
    var mode=0
    func key(_ a:SIMD3<Double>,_ b:SIMD3<Double>,_ row:Double,_ merit:Double)->[UInt64] {
        [a.x.bitPattern,a.y.bitPattern,a.z.bitPattern,b.x.bitPattern,b.y.bitPattern,b.z.bitPattern,row.bitPattern,merit.bitPattern]
    }
    func lookup(_ key:[UInt64])->[(Int,Int)] {
        lock.lock();defer{lock.unlock()}
        guard let list=lists[key] else {fatalError("Prerecorded leaf-list input mismatch")}
        return list
    }
    func record(_ key:[UInt64],_ value:[(Int,Int)]) {
        lock.lock();defer{lock.unlock()}
        if let old=lists[key] {
            precondition(old.count==value.count && zip(old,value).allSatisfy{$0.0.0==$0.1.0 && $0.0.1==$0.1.1})
        } else {
            entries += value.count
            precondition(entries<=8_000_000 && lists.count<100_000)
            lists[key]=value
        }
    }
    var summary:[String:Int] {
        lock.lock();defer{lock.unlock()}
        return ["keys":lists.count,"faceMaskEntries":entries]
    }
}
extension RopeTriangleCollider {
    func setLeafReplayMode(_ mode:Int) {precondition((0...2).contains(mode));leafReplay.mode=mode}
    var leafReplaySummary:[String:Int] {leafReplay.summary}
}
