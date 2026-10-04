"""Same-run optimistic numeric-work ceiling, without changing the solver."""
from pathlib import Path
from armijo.snapshot import once

def solver_source(source):
    source=once(source,'        let evaluation=configurationEvaluation(state)',
        '''        let assemblyStarted=MaterialBasisCost.enabled ? ProcessInfo.processInfo.systemUptime:0
        let configurationBefore=MaterialBasisCost.configurationSeconds
        let evaluation=configurationEvaluation(state)''')
    source=once(source,'        let basisQueryCosts=MaterialBasisTrace.lastBatchCosts\n        let solved=try contactCorrection',
        '''        let basisQueryCosts=MaterialBasisTrace.lastBatchCosts
        let numericStarted=MaterialBasisCost.enabled ? ProcessInfo.processInfo.systemUptime:0
        if MaterialBasisCost.enabled {MaterialBasisCost.assemblySeconds += numericStarted-assemblyStarted-(MaterialBasisCost.configurationSeconds-configurationBefore)}
        let solved=try contactCorrection''')
    source=once(source,'        let selected=solved.ids.map{rows[$0]},lambda=solved.multipliers',
        '''        if MaterialBasisCost.enabled {MaterialBasisCost.contactCorrectionSeconds += ProcessInfo.processInfo.systemUptime-numericStarted}
        let selected=solved.ids.map{rows[$0]},lambda=solved.multipliers''')
    marker='    private mutating func configurationEvaluation(_ candidate:RopeSimulationState)->RopeConfigurationEvaluation {'
    source=once(source,marker,marker+'''
        let geometryStarted=MaterialBasisCost.enabled ? ProcessInfo.processInfo.systemUptime:0
        defer {if MaterialBasisCost.enabled {MaterialBasisCost.configurationSeconds += ProcessInfo.processInfo.systemUptime-geometryStarted}}
''')
    return source

def driver_source(source):
    return source[:source.index('do {\n    var checkpoints:')]+Path(__file__).with_name('CostMain.swift.txt').read_text()
