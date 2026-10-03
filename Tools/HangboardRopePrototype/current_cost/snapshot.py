"""Driver-thread scopes only: parallel kernels never mutate the timing stack."""
import re

SCOPES = {
    'RopeDynamicsSolver.swift': ['step', 'advance', 'correctConstraints', 'contactCorrection',
                                'constraintBackbone', 'merit', 'configurationEvaluation', 'selfContactValid'],
    'RopeContactSystem.swift': ['solveFactored'],
    'RopeBandedSystem.swift': ['factorized', 'solveBatch'],
    'RopeTriangleCollider.swift': ['fusedChainContacts', 'sweepChainIsClear'],
    'RopeSimulationMetrics.swift': ['measure', 'contacts'],
    'RopeCordContacts.swift': ['between', 'sweepValid'],
    'RopeSimulationState.swift': ['refresh'],
}

def instrument(name, text):
    for symbol in SCOPES.get(name, []):
        pattern = r'(^[ \t]*(?:private |fileprivate |static |mutating )*func '+symbol+r'\([^\{]+\{\n)'
        key = name[:-6]+'.'+symbol
        text, count = re.subn(pattern, lambda m: m[0]+f'        AcceptedSolverProfile.enter("{key}");defer {{AcceptedSolverProfile.leave("{key}")}}\n', text, flags=re.M)
        assert count == 1, (name, symbol, count)
    if name == 'RopeBandedSystem.swift':
        text = text.replace('        try RopeBandedFactorization(size:size', '        return try RopeBandedFactorization(size:size')
        for prefix, key in [('    fileprivate init(size:Int,bandwidth:Int,matrix:', 'factorInit'),
                            ('    func solve(rhs:[Double],borderRHS:', 'scalarSolve')]:
            pattern = r'(^'+re.escape(prefix)+r'[^\{]+\{\n)'
            text, count = re.subn(pattern, lambda m: m[0]+f'        AcceptedSolverProfile.enter("RopeBandedFactorization.{key}");defer {{AcceptedSolverProfile.leave("RopeBandedFactorization.{key}")}}\n', text, flags=re.M)
            assert count == 1, (name, key, count)
    if name == 'RopeDynamicsSolver.swift':
        needle = '        if let cached=cachedEvaluation,cached.bits==bits,cached.portalOrder==portalOrder {return cached}\n'
        assert text.count(needle) == 1
        text = text.replace(needle, needle+'        AcceptedSolverProfile.enter("configurationMiss");defer {AcceptedSolverProfile.leave("configurationMiss")}\n')
    if name == 'RopeTriangleCollider.swift':
        needle = '        DispatchQueue.concurrentPerform(iterations:jobs) {job in\n'
        first = text.index(needle, text.index('    func fusedChainContacts('))
        second = text.index(needle, first+len(needle))
        text = text[:second]+'        AcceptedSolverProfile.leave("chainParity")\n        AcceptedSolverProfile.enter("chainNarrowphase")\n'+text[second:]
        text = text[:first]+'        AcceptedSolverProfile.enter("chainParity")\n'+text[first:]
        needle = '        var p=Array(repeating:[RopeSegmentContact](),count:points.count)'
        assert text.count(needle) == 1
        text = text.replace(needle, '        AcceptedSolverProfile.leave("chainNarrowphase")\n'+needle)
    return text
