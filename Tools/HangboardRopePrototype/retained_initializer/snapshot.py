"""Retained frozen active-KKT initial guess followed by authoritative fresh correction."""
from armijo.snapshot import once
from arrival_stop.snapshot import driver_source as arrival_driver

def contact_source(source):
    source=once(source,'        let activeIDs: [Int]','        let activeIDs: [Int]\n        var retained:Prepared?=nil')
    source=once(source,'                      maxIterations: Int=2048, fallback:', '                      retainOperator:Bool=false, maxIterations: Int=2048, fallback:')
    source=once(source,'initialMultipliers:initialMultipliers,maxIterations:maxIterations)',
        'initialMultipliers:initialMultipliers,retainOperator:retainOperator,maxIterations:maxIterations)')
    source=once(source,'                                     maxIterations: Int) throws -> Solution {',
        '                                     retainOperator:Bool,maxIterations: Int) throws -> Solution {')
    source=once(source,'            return Solution(base:Array(correction.prefix(size)),border:Array(correction.dropFirst(size)),\n                            multipliers:multipliers,activeIDs:active)', '''            let retained:Prepared? = retainOperator ? Prepared(factor:factor,contacts:active.map{contacts[$0]},
                responses:try active.map{try response($0)},lower:cholesky.lower):nil
            return Solution(base:Array(correction.prefix(size)),border:Array(correction.dropFirst(size)),
                            multipliers:multipliers,activeIDs:active,retained:retained)''')
    source+='''
extension RopeContactSystem {
    struct Prepared:Sendable {
        let factor:RopeBandedFactorization
        let contacts:[RopeLinearContact]
        let responses:[[Double]]
        let lower:[Double]
        func solveLoads(rhs:[Double],borderRHS:[Double],contactResiduals:[Double])throws->(base:[Double],border:[Double]) {
            guard contactResiduals.count==contacts.count,contactResiduals.allSatisfy({$0.isFinite}) else {
                throw RopePhysicsError.invalid("invalid retained active KKT loads")
            }
            let solved=try factor.solve(rhs:rhs,borderRHS:borderRHS)
            let size=rhs.count,n=contacts.count
            var values=solved.base+solved.border
            var lambda=contacts.indices.map{contactResiduals[$0]+contacts[$0].dot(values,size:size)}
            for i in 0..<n {
                for j in 0..<i {lambda[i] -= lower[i*n+j]*lambda[j]}
                lambda[i] /= lower[i*n+i]
            }
            for i in (0..<n).reversed() {
                for j in (i+1)..<n {lambda[i] -= lower[j*n+i]*lambda[j]}
                lambda[i] /= lower[i*n+i]
            }
            for k in 0..<n {for i in values.indices {values[i] -= responses[k][i]*lambda[k]}}
            guard values.allSatisfy({$0.isFinite}) else {throw RopePhysicsError.invalid("nonfinite retained active KKT result")}
            return (Array(values.prefix(size)),Array(values.dropFirst(size)))
        }
    }
}
'''
    return source

def solver_source(source):
    source=once(source,'    var armijoExperiment=false','''    var armijoExperiment=false
    var retainedInitializerExperiment=false
    private var retainedOperator:RetainedModel?=nil
    private var retainedDraft:RetainedModel?=nil
    private var retainedDuration=0.0
    private struct RetainedModel:Sendable {
        let operatorValue:RopeContactSystem.Prepared
        let anchor:RopeSimulationState
        let weights:[[Double]]
        let variables:[[SIMD3<Int>]]
        let rowVariables:[Int:Int]
        let equalities:[ConstraintRow]
        let activeContacts:[ConstraintRow]
        let duration:Double
    }''')
    source=once(source,'    private struct ConstraintRow {','    private struct ConstraintRow:Sendable {')
    source=once(source,'            let frame=try trial.advance(dt:dt,targetOrientation:targetOrientation)',
        '            if depth>0 {trial.retainedOperator=nil}\n            let frame=try trial.advance(dt:dt,targetOrientation:targetOrientation)')
    source=once(source,'        let old=state','        let old=state\n        retainedDraft=nil;retainedDuration=dt')
    source=once(source,'        #if DEBUG\n        var reviewConverged = false',
        '''        if retainedInitializerExperiment {try applyRetainedInitializer(prediction:prediction,dt:dt)}
        #if DEBUG
        var reviewConverged = false''')
    source=once(source,'contacts:contacts,initialMultipliers:initial,maxIterations:',
        'contacts:contacts,initialMultipliers:initial,retainOperator:retainedInitializerExperiment,maxIterations:')
    source=once(source,'        contactHints=solved.activeIDs.map{(contacts[$0],solved.multipliers[$0])}', '''        if retainedInitializerExperiment {
            if let operatorValue=solved.retained {
                retainedDraft=RetainedModel(operatorValue:operatorValue,anchor:state,weights:weights,
                    variables:variables,rowVariables:backbone.rowVariables,equalities:equalityIDs.map{rows[$0]},
                    activeContacts:solved.activeIDs.map{rows[contactIDs[$0]]},duration:retainedDuration)
                RetainedInitializerTrace.captures += 1
            } else {retainedDraft=nil}
        }
        contactHints=solved.activeIDs.map{(contacts[$0],solved.multipliers[$0])}''')
    source=once(source,'        let settled=arrived && time>=0.5 && metrics.maximumSpeed<0.001 && metrics.boardDisplacement<0.0001',
        '''        let settled=arrived && time>=0.5 && metrics.maximumSpeed<0.001 && metrics.boardDisplacement<0.0001
        if retainedInitializerExperiment {retainedOperator=retainedDraft}''')
    source=once(source,'"strain":maximumStrain(),"rows":rows.count,"slope":armijoSlope as Any? ?? NSNull(),',
        '''"strain":maximumStrain(),"rows":rows.count,"initializerApplied":RetainedInitializerTrace.applied,
                        "initializerSeconds":RetainedInitializerTrace.seconds,"operatorCaptures":RetainedInitializerTrace.captures,
                        "slope":armijoSlope as Any? ?? NSNull(),''')
    source+='''
extension RopeDynamicsSolver {
    private mutating func applyRetainedInitializer(prediction:RopeSimulationState,dt:Double)throws {
        guard let model=retainedOperator,model.duration==dt,
              model.anchor.orientation.vector==prediction.orientation.vector,
              model.anchor.ropes.count==prediction.ropes.count else {return}
        for r in prediction.ropes.indices {
            let a=model.anchor.ropes[r],b=prediction.ropes[r]
            guard a.id==b.id,a.positions.count==b.positions.count,a.radius==b.radius,a.restLengths==b.restLengths,
                  a.supports==b.supports,a.attachments==b.attachments else {return}
        }
        let start=ProcessInfo.processInfo.systemUptime
        defer {RetainedInitializerTrace.seconds += ProcessInfo.processInfo.systemUptime-start}
        let size=model.operatorValue.factor.baseCount
        let heightOffset=prediction.boardHeight-model.anchor.boardHeight
        let offsets=prediction.ropes.indices.map{r in prediction.ropes[r].positions.indices.map{i in
            prediction.ropes[r].positions[i]-model.anchor.ropes[r].positions[i]
        }}
        func residual(_ row:ConstraintRow)->Double {
            var value=row.residual+row.boardGradient*heightOffset
            for k in row.particles.indices where model.weights[row.ropeIndex(k)][row.particles[k]]>0 {
                value += simd_dot(row.gradients[k],offsets[row.ropeIndex(k)][row.particles[k]])
            }
            return value
        }
        var rhs=Array(repeating:0.0,count:size)
        for i in model.equalities.indices {rhs[model.rowVariables[i]!] = -residual(model.equalities[i])}
        let out=try model.operatorValue.solveLoads(rhs:rhs,borderRHS:[0],contactResiduals:model.activeContacts.map{residual($0)})
        var corrections=prediction.ropes.map{Array(repeating:SIMD3<Double>.zero,count:$0.positions.count)}
        for r in prediction.ropes.indices {for i in prediction.ropes[r].positions.indices where model.weights[r][i]>0 {
            let v=model.variables[r][i]
            corrections[r][i]=SIMD3(out.base[v.x],out.base[v.y],out.base[v.z])
        }}
        guard Self.correctionFraction(ropes:prediction.ropes,corrections:corrections,heightCorrection:out.border[0])==1 else {return}
        var guess=prediction
        guess.boardHeight += out.border[0]
        for r in guess.ropes.indices {
            for i in guess.ropes[r].positions.indices {guess.ropes[r].positions[i] += corrections[r][i]}
            for (index,local) in guess.ropes[r].attachments {guess.ropes[r].positions[index]=guess.worldPoint(local)}
        }
        do {try RopePassageTopology.refresh(state:&guess,input:input)} catch RopePhysicsError.invalid {return}
        state=guess;cachedEvaluation=nil;RetainedInitializerTrace.applied=true
    }
}
'''
    return source

def driver_source(source):
    source=arrival_driver(source,140).replace('arrivalStopExperiment','retainedInitializerExperiment').replace('guardedArrivalStop','retainedInitializer')
    source=once(source,'    try fixtures();result["fixturesPass"]=true','    try retainedInitializerFixtures();try fixtures();result["fixturesPass"]=true')
    source=once(source,'candidate.reviewStepCorrections<=2','candidate.reviewStepCorrections<=1')
    source=source.replace('fixed <=2-QP ordinary-step work gate','fixed <=1 fresh QP initializer work gate')
    source=once(source,'guard median<=1.10','guard median<=0.80')
    source=source.replace('fixed median <=1.10 ordinary-step overhead gate','fixed median <=0.80 initializer speed gate')
    source=once(source,'    ArmijoTrace.corrections=[];alarm(10)',
        '    ArmijoTrace.corrections=[];RetainedInitializerTrace.reset();alarm(10)')
    source=once(source,'for step in 1...139','for step in 1...138')
    source=once(source,'    result["prefixIdentitySteps"]=139','''    result["prefixIdentitySteps"]=138
    var baselinePrime=initial
    let baselineTrace=try run(&baselinePrime).1
    initial.retainedInitializerExperiment=true
    let primedTrace=try run(&initial).1
    guard baselineTrace.count==primedTrace.count,try serialize(baselinePrime.bundleCheckpoint())==serialize(initial.bundleCheckpoint()) else {
        throw RopePhysicsError.invalid("actual preceding accepted solve prime physical identity")
    }
    result["primeStep"]=139;result["primeCheckpointIdentity"]=true''')
    source=once(source,'    var original=initial,candidate=initial',
        '    var original=initial,candidate=initial\n    original.retainedInitializerExperiment=false')
    source=once(source,'    result["candidateMetrics"]=try check(candidate)',
        '''    guard probe.1.first?["initializerApplied"] as? Bool == true else {throw RopePhysicsError.invalid("actual retained initializer must apply")}
    result["candidateMetrics"]=try check(candidate)''')
    source=once(source,'        var a=initial,b=initial;b.retainedInitializerExperiment=true',
        '        var a=initial,b=initial;a.retainedInitializerExperiment=false;b.retainedInitializerExperiment=true')
    return source
