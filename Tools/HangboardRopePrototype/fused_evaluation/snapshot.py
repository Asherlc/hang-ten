from pathlib import Path

def once(source,old,new):
    assert source.count(old)==1,old
    return source.replace(old,new)

def collider_source(source):
    if 'func queryParity' not in source:
        source=once(source,'    private func contains(', '    func queryParity(_ point:SIMD3<Double>)->Bool {contains(point)}\n    private func contains(')
    return source+'\n'+Path(__file__).with_name('FusedQueries.swift').read_text()

def solver_source(source):
    source=once(source,'    private var lastStepDuration=1.0/240', '    private var lastStepDuration=1.0/240\n    private var cachedEvaluation:RopeConfigurationEvaluation?')
    source=once(source,'        let prediction=state\n        do {', '        let prediction=state\n        cachedEvaluation=nil\n        do {')
    source=once(source,'        var candidate=self\n        let preflight=', '        var candidate=self\n        candidate.cachedEvaluation=nil\n        let preflight=')
    source=once(source,'        var rows:[ConstraintRow]=[]', '        let evaluation=configurationEvaluation(state)\n        var rows:[ConstraintRow]=[]')
    source=once(source,'for hit in collider.segmentContacts(from:state.boardPoint(rope.positions[i]),to:state.boardPoint(rope.positions[i]),\n                    radius:rope.radius+RopeRegionGeometry.clearance+0.00005)', 'for hit in evaluation.points[r][i]')
    source=once(source,'for hit in collider.segmentContacts(from:a,to:b,radius:rope.radius+RopeRegionGeometry.clearance+0.00005)', 'for hit in evaluation.rows[r][i]')
    source=once(source,'for pair in RopeSimulationMetrics.selfContactPairs(positions:rope.positions,radius:rope.radius,supports:rope.supports,margin:0.0001,restLengths:rope.restLengths)', 'for pair in evaluation.selfPairs[r]') if source.count('for pair in RopeSimulationMetrics.selfContactPairs(positions:rope.positions,radius:rope.radius,supports:rope.supports,margin:0.0001,restLengths:rope.restLengths)')==1 else source.replace('for pair in RopeSimulationMetrics.selfContactPairs(positions:rope.positions,radius:rope.radius,supports:rope.supports,margin:0.0001,restLengths:rope.restLengths)', 'for pair in evaluation.selfPairs[r]')
    source=once(source,'for hit in RopeCordContacts.between(state.ropes[first],state.ropes[second],margin:0.0001)', 'for hit in evaluation.cordContacts[SIMD2(first,second)]!')
    source=once(source,'    private func merit(', '    private mutating func merit(')
    source=once(source,'        var objective=0.5*state.boardMass', '        let evaluation=configurationEvaluation(candidate)\n        var meritInputs=[state.boardMass.bitPattern,prediction.boardHeight.bitPattern]\n        for (r,rope) in prediction.ropes.enumerated() {for i in rope.positions.indices {\n            let p=rope.positions[i];meritInputs += [p.x.bitPattern,p.y.bitPattern,p.z.bitPattern,weights[r][i].bitPattern]\n        }}\n        if let parts=evaluation.meritParts,evaluation.meritInputs==meritInputs {return parts.0+penalty*parts.1}\n        var objective=0.5*state.boardMass')
    source=once(source,'let hits=collider.segmentContacts(from:candidate.boardPoint(rope.positions[i]),to:candidate.boardPoint(rope.positions[i+1]),\n                    radius:rope.radius+RopeRegionGeometry.clearance)', 'let hits=evaluation.merits[r][i]')
    source=once(source,'for contact in RopeCordContacts.between(candidate.ropes[first],candidate.ropes[second],margin:0.0001)', 'for contact in evaluation.cordContacts[SIMD2(first,second)]!')
    source=once(source,'        return objective+penalty*violation', '        cachedEvaluation?.meritParts=(objective,violation)\n        cachedEvaluation?.meritInputs=meritInputs\n        return objective+penalty*violation')
    return source+'\n'+Path(__file__).with_name('Evaluation.swift').read_text()
