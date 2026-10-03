"""Instrumentation only; each joined worker writes its own initialized slots."""

def instrument(name, text):
    if name != 'RopeTriangleCollider.swift':
        return text
    needle = '                       startInside:Bool,endInside:Bool)->(hits:[[RopeSegmentContact]],clearance:Double?) {'
    assert text.count(needle) == 1
    text = text.replace(needle, '                       startInside:Bool,endInside:Bool,faceCount:UnsafeMutablePointer<Int>? = nil)->(hits:[[RopeSegmentContact]],clearance:Double?) {')
    needle = '        var minimum=Double.infinity\n        for (index,mask) in faces.sorted(by:{$0.0<$1.0}) {'
    assert text.count(needle) == 1
    text = text.replace(needle, '        faceCount?.pointee += faces.count\n'+needle)
    start = text.index('    func fusedChainContacts(')
    end = text.index('\n}\n', start)
    before, section, after = text[:start], text[start:end], text[end:]
    needle = '        DispatchQueue.concurrentPerform(iterations:jobs) {job in\n'
    assert section.count(needle) == 2
    section = section.replace(needle, needle+'''            let began = RopeWorkerBalanceProfile.enabled ? ProcessInfo.processInfo.systemUptime : 0
            defer {if RopeWorkerBalanceProfile.enabled {timings[job]=ProcessInfo.processInfo.systemUptime-began}}
''', 1)
    first = section.index(needle)
    second = section.index(needle, first+len(needle))
    section = section[:second]+section[second:].replace(needle, needle+'''            let began = RopeWorkerBalanceProfile.enabled ? ProcessInfo.processInfo.systemUptime : 0
            defer {if RopeWorkerBalanceProfile.enabled {timings[jobs+job]=ProcessInfo.processInfo.systemUptime-began}}
''', 1)
    needle = '                    startInside:storage.inside[i],endInside:storage.inside[i+1])'
    assert section.count(needle) == 1
    section = section.replace(needle, '                    startInside:storage.inside[i],endInside:storage.inside[i+1],faceCount:RopeWorkerBalanceProfile.enabled ? counts+job:nil)')
    needle = '        func ranges(_ count:Int,_ job:Int)->Range<Int>'
    section = section.replace(needle, '''        let timings=UnsafeMutablePointer<Double>.allocate(capacity:jobs*2)
        let counts=UnsafeMutablePointer<Int>.allocate(capacity:jobs)
        timings.initialize(repeating:0,count:jobs*2);counts.initialize(repeating:0,count:jobs)
        defer {timings.deinitialize(count:jobs*2);timings.deallocate();counts.deinitialize(count:jobs);counts.deallocate()}
'''+needle)
    needle = '        var p=Array(repeating:[RopeSegmentContact](),count:points.count)'
    section = section.replace(needle, '''        if RopeWorkerBalanceProfile.enabled {
            RopeWorkerBalanceProfile.rows.append([
                "paritySeconds":Array(UnsafeBufferPointer(start:timings,count:jobs)),
                "narrowphaseSeconds":Array(UnsafeBufferPointer(start:timings+jobs,count:jobs)),
                "candidateFaces":Array(UnsafeBufferPointer(start:counts,count:jobs)),"jobs":jobs])
        }
'''+needle)
    return 'import Foundation\n'+before+section+after+'''

// Enabled changes only on the driver, outside joined parallel regions.
enum RopeWorkerBalanceProfile {
    static var enabled=false
    static var rows:[[String:Any]]=[]
}
'''
