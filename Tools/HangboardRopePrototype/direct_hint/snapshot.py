from pathlib import Path


def transform(name, text):
    if name == 'RopeBandedSystem.swift':
        return 'import Foundation\n'+text+'''
extension RopeBandedSystem {
    func hintResidual(base:[Double],border:[Double],rhs:[Double],columns:[[Double]],
        borderMatrix:[[Double]],borderRHS:[Double])->Double {
        var values=Array(repeating:0.0,count:size),other=Array(repeating:0.0,count:border.count)
        for column in 0..<size {
            for row in max(0,column-bandwidth)...min(size-1,column+bandwidth) {
                values[row] += matrix[2*bandwidth+row-column+column*leadingDimension]*base[column]
            }
        }
        for i in 0..<size {for j in border.indices {values[i] += columns[j][i]*border[j]}}
        for j in border.indices {
            for i in 0..<size {other[j] += columns[j][i]*base[i]}
            for k in border.indices {other[j] += borderMatrix[j][k]*border[k]}
        }
        let residuals=zip(values,rhs).map{abs($0-$1)}+zip(other,borderRHS).map{abs($0-$1)}
        guard residuals.allSatisfy({$0.isFinite}) else{return .infinity}
        return residuals.max() ?? 0
    }
}
'''
    if name != 'RopeDynamicsSolver.swift':
        return text
    start = text.index('    private func constraintBackbone(rows:')
    end = text.index('\n    private mutating func merit(', start)
    original = text[start:end]
    beginning = original.index('        let borderRows=')
    factor = original.index('        let factor=try system.factorized(')
    prepared = '''\nextension RopeDynamicsSolver {
    private func preparedHintBackbone(rows:[ConstraintRow],weights:[[Double]],prediction:RopeSimulationState) throws -> HintPrepared {
'''+original[beginning:factor]+'''        return HintPrepared(system:system,columns:columns,border:border,rhs:rhs,borderRHS:borderRHS,
            variables:variables,rowVariables:rowVariables,local:local,borderRows:borderRows,rows:rows)
    }
}
'''
    needle = '        let equalityIDs=rows.indices.filter{!rows[$0].contact}\n'
    assert text.count(needle) == 1
    text = text.replace(needle, '        let trialStart=HintTrialTrace.enabled ? ProcessInfo.processInfo.systemUptime:0\n'+needle)
    needle = '        return (particles,solved.border[0],ids.map{multipliers[$0]},ids)'
    assert text.count(needle) == 1
    text = text.replace(needle, '''        if HintTrialTrace.enabled {
            let originalSeconds=ProcessInfo.processInfo.systemUptime-trialStart
            let selectedIDs=(equalityIDs+initial.keys.map{contactIDs[$0]}).sorted()
            let selected=selectedIDs.map{rows[$0]}
            let prepared=try preparedHintBackbone(rows:selected,weights:weights,prediction:prediction)
            Self.hintTrials.append(HintTrial(prepared:prepared,allRows:rows,selectedIDs:selectedIDs,
                expectedParticles:particles,expectedHeight:solved.border[0],originalSeconds:originalSeconds))
        }
'''+needle)
    return text+prepared+'\n'+(Path(__file__).parent/'Trial.swift').read_text()


def candidate(name, text):
    if name == 'RopeBandedSystem.swift':
        return transform(name, text)
    if name != 'RopeDynamicsSolver.swift':
        return text
    changed = transform(name, text)
    # Remove observer-only capture and timer; retain the original prepared assembly.
    start=changed.index('        if HintTrialTrace.enabled {')
    end=changed.index('        return (particles,solved.border[0],ids.map{multipliers[$0]},ids)', start)
    changed=changed[:start]+changed[end:]
    changed=changed.replace('        let trialStart=HintTrialTrace.enabled ? ProcessInfo.processInfo.systemUptime:0\n','')
    start=changed.index('// This tool only observes frozen correction inputs.')
    changed=changed[:start]+changed[start:changed.index('    private struct HintTrial {',start)]+"}\n"
    needle='        let equalityIDs=rows.indices.filter{!rows[$0].contact}\n'
    assert changed.count(needle)==1
    changed=changed.replace(needle,"""        if convergenceExperiment {
            do {if let result=try oneShotHintCorrection(rows:rows,weights:weights,prediction:prediction) {return result}}
            catch {HintCandidateTrace.exceptions+=1}
        }
"""+needle)
    return changed+'\n'+(Path(__file__).parent/'Candidate.swift').read_text()
