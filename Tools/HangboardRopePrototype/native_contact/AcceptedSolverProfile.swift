import Foundation

// Snapshot-only nested timings. Never linked into the app; single-threaded driver.
enum AcceptedSolverProfile {
    struct Frame {let name:String;let start:Double;var children=0.0}
    static var enabled=false
    static var stack:[Frame]=[]
    static var buckets:[String:(calls:Int,inclusive:Double,exclusive:Double)]=[:]
    static func enter(_ name:String) {
        guard enabled else {return}
        stack.append(Frame(name:name,start:ProcessInfo.processInfo.systemUptime))
    }
    static func leave(_ name:String) {
        guard enabled else {return}
        let end=ProcessInfo.processInfo.systemUptime
        guard let frame=stack.popLast(),frame.name==name else {fatalError("Profile stack mismatch")}
        let elapsed=end-frame.start
        var b=buckets[name] ?? (0,0,0)
        b.calls += 1;b.inclusive += elapsed;b.exclusive += elapsed-frame.children
        buckets[name]=b
        if !stack.isEmpty {stack[stack.count-1].children += elapsed}
    }
    static func output()->[String:Any] {
        precondition(stack.isEmpty)
        return buckets.mapValues{["calls":Double($0.calls),"inclusiveSeconds":$0.inclusive,"exclusiveSeconds":$0.exclusive]}
    }
}
