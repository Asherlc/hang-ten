from pathlib import Path

def solver_source(text):
    needle='    private var cachedEvaluation:RopeConfigurationEvaluation?\n'
    assert text.count(needle)==1
    text=text.replace(needle,needle+'    private let lazyOutputReplay=RopeLazyOutputReplay()\n')
    needle='    let bits:[UInt64]\n'
    assert text.count(needle)==1
    text=text.replace(needle,'    let fullGeometry:Bool\n'+needle)
    needle='private mutating func configurationEvaluation(_ candidate:RopeSimulationState)->RopeConfigurationEvaluation {'
    assert text.count(needle)==1
    text=text.replace(needle,'private mutating func configurationEvaluation(_ candidate:RopeSimulationState,output:Int=0)->RopeConfigurationEvaluation {')
    needle='        let evaluation=configurationEvaluation(candidate)\n'
    assert text.count(needle)==1
    text=text.replace(needle,'        let evaluation=configurationEvaluation(candidate,output:1)\n')
    needle='        let receipts=configurationEvaluation(state).clearances\n'
    assert text.count(needle)==1
    text=text.replace(needle,'        let receipts=configurationEvaluation(state,output:2).clearances\n')
    needle='        if let cached=cachedEvaluation,cached.bits==bits,cached.portalOrder==portalOrder {return cached}\n'
    assert text.count(needle)==1
    text=text.replace(needle,'''        let previous=cachedEvaluation.flatMap{$0.bits==bits && $0.portalOrder==portalOrder ? $0:nil}
        if let previous,previous.fullGeometry || output != 0 {return previous}
        let scalarOnly=lazyOutputReplay.mode==2 && output != 0
        if lazyOutputReplay.mode==2 {
            if scalarOnly {lazyOutputReplay.scalarLookups += 1;if output==2 {lazyOutputReplay.clearanceLookups += 1}}
            else {lazyOutputReplay.fullBuilds += 1;if previous != nil {lazyOutputReplay.rowUpgrades += 1}}
        }
''')
    needle='''            let batch=collider.fusedChainContacts(points:board,rowRadius:rope.radius+RopeRegionGeometry.clearance+0.00005,meritRadius:rope.radius+RopeRegionGeometry.clearance)
            clearances.append(batch.clearances)
            points.append(batch.points);rows.append(batch.rows);merits.append(batch.merits)
'''
    assert text.count(needle)==1
    text=text.replace(needle,'''            if scalarOnly {
                let original=lazyOutputReplay.lookup(bits:lazyGeometryKey(candidate)),r=points.count
                clearances.append(original.clearances[r])
                points.append([]);rows.append([])
                merits.append(original.depths[r].map{depth in depth==0 ? []:[
                    RopeSegmentContact(centerlinePoint:.zero,surfacePoint:.zero,normal:.zero,fraction:0,penetrationDepth:depth)]})
            } else {
                let batch=collider.fusedChainContacts(points:board,rowRadius:rope.radius+RopeRegionGeometry.clearance+0.00005,meritRadius:rope.radius+RopeRegionGeometry.clearance)
                clearances.append(batch.clearances)
                points.append(batch.points);rows.append(batch.rows);merits.append(batch.merits)
            }
''')
    needle='''            pairs.append(RopeSimulationMetrics.selfContactPairs(positions:rope.positions,radius:rope.radius,supports:rope.supports,margin:0.0001,restLengths:rope.restLengths))'''
    assert text.count(needle)==1
    text=text.replace(needle,'''            pairs.append(previous?.selfPairs[pairs.count] ?? RopeSimulationMetrics.selfContactPairs(positions:rope.positions,radius:rope.radius,supports:rope.supports,margin:0.0001,restLengths:rope.restLengths))''')
    needle='''            cords[SIMD2(first,second)]=RopeCordContacts.between(candidate.ropes[first],candidate.ropes[second],margin:0.0001)'''
    assert text.count(needle)==1
    text=text.replace(needle,'''            cords[SIMD2(first,second)]=previous?.cordContacts[SIMD2(first,second)] ?? RopeCordContacts.between(candidate.ropes[first],candidate.ropes[second],margin:0.0001)''')
    needle='''        let result=RopeConfigurationEvaluation(bits:bits,portalOrder:portalOrder,points:points,rows:rows,merits:merits,clearances:clearances,selfPairs:pairs,cordContacts:cords)
        cachedEvaluation=result'''
    assert text.count(needle)==1
    text=text.replace(needle,'''        var result=RopeConfigurationEvaluation(fullGeometry:!scalarOnly,bits:bits,portalOrder:portalOrder,points:points,rows:rows,merits:merits,clearances:clearances,selfPairs:pairs,cordContacts:cords)
        result.meritParts=previous?.meritParts;result.meritInputs=previous?.meritInputs
        if lazyOutputReplay.mode==1 {lazyOutputReplay.record(bits:lazyGeometryKey(candidate),merits:merits,clearances:clearances)}
        cachedEvaluation=result''')
    return text+'\n'+(Path(__file__).parent/'Replay.swift').read_text()
