from run_native_contact_screen import REPO

def replace_once(text, old, new):
    if text.count(old) != 1:
        raise ValueError('Source hook changed or ambiguous: ' + old[:100])
    return text.replace(old, new)

def capture_sources(r, stage):
    sources = stage / 'sources'
    sources.mkdir()
    names = ['RopePhysicsDescriptor.swift', 'RopeTriangleCollider.swift', 'RopeSimulationState.swift', 'RopeThreadedSeed.swift', 'RopeSimulationMetrics.swift', 'RopeCordContacts.swift', 'RopeContactSystem.swift', 'RopeBandedSystem.swift', 'RopeDynamicsSolver.swift']
    for name in names:
        text = (REPO / 'HangTen/Models' / name).read_text()
        if name == 'RopeTriangleCollider.swift':
            text = replace_once(text, '    var timeOfImpact: Double? = nil', '    var timeOfImpact: Double? = nil\n    var triangleID:Int = -1')
            text = replace_once(text, '        if contains(start) || (start != end && contains(end)) {\n            return segmentContact(from:start,to:end,radius:radius).map{[$0]} ?? []\n        }', '        let queryID=DiscoveryCapture.query(start,end,radius)\n        if contains(start) || (start != end && contains(end)) {\n            let hits=segmentContact(from:start,to:end,radius:radius).map{[$0]} ?? []\n            DiscoveryCapture.finish(queryID,hits);return hits\n        }')
            text = replace_once(text, '        while let index=stack.popLast() {\n            let node=tree[index],separation=simd_max(simd_max(node.minimum-high,low-node.maximum),SIMD3(repeating:0))', '        if let proposed=DiscoveryCapture.faces(queryID){faces=proposed;stack=[]}\n        while let index=stack.popLast() {\n            let node=tree[index],separation=simd_max(simd_max(node.minimum-high,low-node.maximum),SIMD3(repeating:0))')
            text = replace_once(text, 'fraction:fraction,penetrationDepth:radius-distance)', 'fraction:fraction,penetrationDepth:radius-distance,triangleID:index)')
            needle = '        return result\n    }\n\n    /// Conservative advancement'
            assert text.count(needle) == 1
            text = replace_once(text, needle, '        DiscoveryCapture.finish(queryID,result)\n' + needle)
        if name == 'RopeDynamicsSolver.swift':
            text = 'import Foundation\n' + text + '\n' + (REPO / 'Tools/HangboardRopePrototype/stock_chain/CheckpointAdapter.swift').read_text()
            text = replace_once(text, '        var rows:[ConstraintRow]=[]', '        DiscoveryCapture.begin()\n        var rows:[ConstraintRow]=[]')
            needle = '        let solved=try contactCorrection(rows:rows,weights:weights,prediction:prediction)'
            assert text.count(needle) == 1
            addition = '        if DiscoveryCapture.enabled{DiscoveryCapture.solveStart=ProcessInfo.processInfo.systemUptime}\n        let solved=try contactCorrection(rows:rows,weights:weights,prediction:prediction)\n        DiscoveryCapture.solveEnd=ProcessInfo.processInfo.systemUptime\n        if DiscoveryCapture.enabled {\n            func points(_ x:[[SIMD3<Double>]])->[[[Double]]]{x.map{$0.map{DiscoveryCapture.v($0)}}}\n            let rawRows=rows.map{row in ["rope":row.rope,"secondRope":row.secondRope ?? -1,"particles":row.particles,"gradients":row.gradients.map{DiscoveryCapture.v($0)},"boardGradient":row.boardGradient,"residual":row.residual,"contact":row.contact] as [String:Any]}\n            var lambda=Array(repeating:0.0,count:rows.count)\n            for (index,id) in solved.ids.enumerated(){lambda[id]=solved.multipliers[index]}\n            try DiscoveryCapture.write(["rows":rawRows,"weights":weights,"positions":points(state.ropes.map{$0.positions}),"prediction":points(prediction.ropes.map{$0.positions}),"distanceTension":distanceTension,"boardMass":state.boardMass,"boardHeight":state.boardHeight,"predictionHeight":prediction.boardHeight,"regularization":1e-8,"reference":["particles":points(solved.particles),"height":solved.height,"rowMultipliers":lambda]])\n        }'
            text = replace_once(text, needle, addition)
        (sources / name).write_text(text)
    for name in ['Capture.swift', 'main.swift']:
        (sources / name).write_bytes((r / name).read_bytes())
    (sources / 'ExactCheckpointJSON.swift').write_bytes((REPO / 'Tools/HangboardRopePrototype/native_contact/ExactCheckpointJSON.swift').read_bytes())
    return sorted(sources.iterdir())
