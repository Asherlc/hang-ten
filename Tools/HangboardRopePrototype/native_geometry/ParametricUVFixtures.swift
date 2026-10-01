import Foundation
import simd

var failures = 0,tests = 0
func check(_ name: String,_ body: () throws -> Bool) {
    tests += 1
    do {if try body() {print("PASS \(name)")} else {failures += 1;print("FAIL \(name)")}}
    catch {failures += 1;print("FAIL \(name): \(error)")}
}
let triangle = RopeUVTile(id:7,a:SIMD2(0,0),b:SIMD2(1,0),c:SIMD2(0,1))
check("inside both triangle windings") {
    try RopeUVIndex([triangle]).lookup(SIMD2(0.2,0.2))?.tile == 7 &&
    RopeUVIndex([RopeUVTile(id:8,a:triangle.a,b:triangle.c,c:triangle.b)]).lookup(SIMD2(0.2,0.2))?.tile == 8
}
check("bounding box cannot fill a trimmed hole") {
    let index = try RopeUVIndex([triangle])
    return index.lookup(SIMD2(0.8,0.8)) == nil && index.lookup(SIMD2(0.2,0.2)) != nil
}
check("boundary and uncertain near-edge keep original fallback") {
    let index = try RopeUVIndex([triangle])
    return index.lookup(SIMD2(0.5,0.5)) == nil && index.lookup(SIMD2(0.5,0.5-1e-12)) == nil &&
        index.lookup(SIMD2(0.5,0.5-1e-6)) != nil
}
check("chosen periodic chart is returned with its witness") {
    let p = Double.pi
    let index = try RopeUVIndex([RopeUVTile(id:9,a:SIMD2(p-0.02,0),b:SIMD2(p+0.02,0),c:SIMD2(p,1))])
    guard let hit = index.lookup(SIMD2(-p+0.001,0.2),periodicU:true) else {return false}
    return hit.tile == 9 && hit.point.x > 3 && hit.point.x < 3.2
}
check("invalid tile rejected") {
    do {_ = try RopeUVIndex([RopeUVTile(id:1,a:SIMD2(.nan,0),b:SIMD2(1,0),c:SIMD2(0,1))]);return false}
    catch {return true}
}
check("internal nodes preserve separated triangle islands") {
    var tiles: [RopeUVTile] = []
    for i in 0..<64 {
        let x = Double(i%8),y = Double(i/8)
        tiles.append(RopeUVTile(id:i,a:SIMD2(x,y),b:SIMD2(x+0.4,y),c:SIMD2(x,y+0.4)))
    }
    let index = try RopeUVIndex(tiles)
    for i in 0..<64 {
        let x = Double(i%8),y = Double(i/8)
        if index.lookup(SIMD2(x+0.1,y+0.1))?.tile != i || index.lookup(SIMD2(x+0.3,y+0.3)) != nil {return false}
    }
    return true
}
check("degenerate and nonfinite query do not certify") {
    let index = try RopeUVIndex([RopeUVTile(id:1,a:.zero,b:.zero,c:.zero)])
    return index.lookup(.zero) == nil && index.lookup(SIMD2(.infinity,0)) == nil
}
check("broad phase retains full link crossings and threshold boundary") {
    let low = SIMD3<Double>(repeating:-0.1),high = SIMD3<Double>(repeating:0.1)
    return RopeUVBroadPhase.mayTouch(start:SIMD3(0,-3,0),end:SIMD3(0,1,0),low:low,high:high,threshold:0.01) &&
        RopeUVBroadPhase.mayTouch(start:SIMD3(0.2,0,0),end:SIMD3(0.2,0,0),low:low,high:high,threshold:0.1) &&
        !RopeUVBroadPhase.mayTouch(start:SIMD3(0.3,0,0),end:SIMD3(0.3,0,0),low:low,high:high,threshold:0.1)
}
check("unbounded broad phase keeps original fallback") {
    RopeUVBroadPhase.mayTouch(start:SIMD3(.nan,0,0),end:.zero,low:.zero,high:.zero,threshold:0.1)
}
check("typed checkpoint input keeps binary64 source values") {
    let text = "[0.036151047000000006,0.0035,-0.0004394904458598727]"
    let values = try RopeUVJSON.decode([Double].self,data:Data(text.utf8))
    let expected = [0.036151047000000006,0.0035,-0.0004394904458598727]
    return zip(values,expected).allSatisfy {$0.bitPattern == $1.bitPattern}
}
print("\(tests-failures) passed; \(failures) failed")
exit(failures == 0 ? 0:1)
