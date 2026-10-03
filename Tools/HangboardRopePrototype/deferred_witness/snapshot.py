"""Count discarded per-face witnesses without changing contact arithmetic."""


def count_snapshot(name, text):
    if name != 'RopeTriangleCollider.swift':
        return text
    needle = '                       startInside:Bool,endInside:Bool)->(hits:[[RopeSegmentContact]],clearance:Double?) {'
    assert text.count(needle) == 1
    text = text.replace(needle, '                       startInside:Bool,endInside:Bool,counts:UnsafeMutablePointer<Int>? = nil)->(hits:[[RopeSegmentContact]],clearance:Double?) {')
    needle = '        if startInside || endInside {\n'
    assert text.count(needle) == 1
    text = text.replace(needle, needle+'            if let counts {counts[5]+=1}\n')
    needle = '        var minimum=Double.infinity\n        for (index,mask) in faces.sorted(by:{$0.0<$1.0}) {'
    assert text.count(needle) == 1
    text = text.replace(needle, '        if let counts {counts[6]+=faces.count}\n'+needle)
    # Candidate IDs are shared between independently cut-off row/merit queries.
    for arguments, ordinal in [('start,q,0', '0'), ('end,q,0', '1'), ('end,q,1', '1'), ('p,p,t', '2'), ('q.0,q.1,q.2', '3+edgeIndex')]:
        text = text.replace('.consider('+arguments+')', '.consider('+arguments+',candidateID:'+ordinal+')')
    needle = '                for q in [ab,bc,ca] {'
    assert text.count(needle) == 1
    text = text.replace(needle, '                for (edgeIndex,q) in [ab,bc,ca].enumerated() {')
    needle = '            if row.best<rowSquare {minimum=min(minimum,sqrt(row.best))}'
    assert text.count(needle) == 1
    text = text.replace(needle, '''            if let counts {
                counts[0]+=first.updates+row.updates+merit.updates+last.updates
                for w in [first,row,merit,last] {
                    if w.hit != nil {counts[1]+=1;if w.divisionWinner {counts[4]+=1}}
                    counts[3]+=w.divisionUpdates
                }
                if row.hit != nil && merit.hit != nil && row.winnerID==merit.winnerID {counts[2]+=1}
            }
'''+needle)
    needle = '        var hit:RopeSegmentContact?\n        mutating func consider(_ p:SIMD3<Double>,_ q:SIMD3<Double>,_ fraction:Double) {'
    assert text.count(needle) == 1
    text = text.replace(needle, '''        var hit:RopeSegmentContact?
        var updates=0,divisionUpdates=0,winnerID = -1
        var divisionWinner=false
        mutating func consider(_ p:SIMD3<Double>,_ q:SIMD3<Double>,_ fraction:Double,candidateID:Int) {''')
    needle = '            let distance=sqrt(distanceSquared)\n            hit=RopeSegmentContact(centerlinePoint:p,surfacePoint:q,'
    assert text.count(needle) == 1
    text = text.replace(needle, '''            let distance=sqrt(distanceSquared)
            updates+=1;winnerID=candidateID;divisionWinner=distance>1e-10;if divisionWinner {divisionUpdates+=1}
            hit=RopeSegmentContact(centerlinePoint:p,surfacePoint:q,''')
    start = text.index('    func fusedChainContacts(')
    end = text.index('\n}\n', start)
    before, section, after = text[:start], text[start:end], text[end:]
    needle = '        func ranges(_ count:Int,_ job:Int)->Range<Int>'
    section = section.replace(needle, '''        let counts=UnsafeMutablePointer<Int>.allocate(capacity:jobs*7)
        counts.initialize(repeating:0,count:jobs*7)
        defer {counts.deinitialize(count:jobs*7);counts.deallocate()}
'''+needle)
    needle = '                    startInside:storage.inside[i],endInside:storage.inside[i+1])'
    assert section.count(needle) == 1
    section = section.replace(needle, '                    startInside:storage.inside[i],endInside:storage.inside[i+1],counts:DeferredWitnessCounts.enabled ? counts+job*7:nil)')
    needle = '        var p=Array(repeating:[RopeSegmentContact](),count:points.count)'
    section = section.replace(needle, '''        if DeferredWitnessCounts.enabled {
            DeferredWitnessCounts.rows.append((0..<jobs).map{job in Array(UnsafeBufferPointer(start:counts+job*7,count:7))})
        }
'''+needle)
    return before+section+after+'''

// Driver toggles and combines counters only outside joined regions.
enum DeferredWitnessCounts {
    static var enabled=false
    static var rows:[[[Int]]]=[]
}
'''
