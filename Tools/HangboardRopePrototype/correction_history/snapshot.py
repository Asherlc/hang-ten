from pathlib import Path

def once(source,old,new):
    assert source.count(old)==1,old
    return source.replace(old,new)

def warm_source(source):
    source=once(source,'    private var lastStepDuration=1.0/240',"""    private var lastStepDuration=1.0/240
    private struct CorrectionGuess:Sendable {
        let particles:[[SIMD3<Double>]]
        let height:Double
        let dt:Double
    }
    private var correctionGuesses:[CorrectionGuess]=[]
    mutating func clearCorrectionGuesses() {correctionGuesses=[]}
    func guessIdentity()->[[[UInt64]]] {
        correctionGuesses.map {g in [[g.height.bitPattern,g.dt.bitPattern]]+g.particles.map{$0.flatMap{[$0.x.bitPattern,$0.y.bitPattern,$0.z.bitPattern]}}}
    }""")
    source=once(source,'try trial.advance(dt:dt,targetOrientation:targetOrientation)','try trial.advance(dt:dt,targetOrientation:targetOrientation,allowGuess:depth==0)')
    source=once(source,'            trial=self\n            _ = try trial.advanceBounded','            trial=self\n            trial.correctionGuesses=[]\n            HistoryTrace.retries += 1\n            _ = try trial.advanceBounded')
    source=once(source,'private mutating func advance(dt:Double,targetOrientation:simd_quatd)','private mutating func advance(dt:Double,targetOrientation:simd_quatd,allowGuess:Bool)')
    old="""        for _ in 0..<80 {
            let movement=try correctConstraints(prediction:prediction)"""
    new="""        if allowGuess,let last=correctionGuesses.last {
            let prior=correctionGuesses.count==2 ? correctionGuesses[0]:nil
            let linear=prior != nil && last.dt==dt && prior!.dt==dt
            let scale=pow(dt/last.dt,2)
            let guess=last.particles.enumerated().map {r,points in
                points.enumerated().map {i,p in linear ? 2*p-prior!.particles[r][i]:p*scale}
            }
            let height=linear ? 2*last.height-prior!.height:last.height*scale
            let trust=Self.correctionFraction(ropes:state.ropes,corrections:guess,heightCorrection:height)
            HistoryTrace.guessTrust=trust
            if trust==1 {
                let plain=state
                state.boardHeight += height
                for r in state.ropes.indices {
                    for i in state.ropes[r].positions.indices where state.ropes[r].supports[i]==nil && state.ropes[r].attachments[i]==nil {
                        state.ropes[r].positions[i] += guess[r][i]
                    }
                    for (i,local) in state.ropes[r].attachments {state.ropes[r].positions[i]=state.worldPoint(local)}
                }
                do {try RopePassageTopology.refresh(state:&state,input:input);HistoryTrace.guessKind=linear ? "linear":"constant"}
                catch RopePhysicsError.invalid {state=plain;HistoryTrace.fallbacks += 1}
            } else {HistoryTrace.fallbacks += 1}
        }
        for _ in 0..<80 {
            let movement=try correctConstraints(prediction:prediction)"""
    source=once(source,old,new)
    old='        acceptedMinimumClearance=metrics.minimumSegmentClearance\n        lastStepDuration=dt'
    new="""        if allowGuess {
            let particles=state.ropes.enumerated().map {r,rope in
                rope.positions.enumerated().map {i,p in
                    rope.supports[i] != nil || rope.attachments[i] != nil ? SIMD3<Double>.zero:p-prediction.ropes[r].positions[i]
                }
            }
            correctionGuesses.append(CorrectionGuess(particles:particles,height:state.boardHeight-prediction.boardHeight,dt:dt))
            if correctionGuesses.count>2 {correctionGuesses.removeFirst()}
        }
        acceptedMinimumClearance=metrics.minimumSegmentClearance
        lastStepDuration=dt"""
    source=once(source,old,new)
    # The trace leaves calculations/conditions unchanged.
    source=once(source,'        let before=state\n        let maximum=', '        HistoryTrace.lastRows=rows.count\n        HistoryTrace.lastActive=solved.ids.count-rows.filter{!$0.contact}.count\n        let before=state\n        let maximum=')
    source=once(source,'                    return alpha*max(maximum,abs(heightCorrection))','                    HistoryTrace.corrections.append(["movement":alpha*max(maximum,abs(heightCorrection)),"strain":maximumStrain(),"alpha":alpha,"rows":Double(rows.count),"active":Double(HistoryTrace.lastActive)])\n                    return alpha*max(maximum,abs(heightCorrection))')
    source=once(source,'        var objective=0.5*state.boardMass','        HistoryTrace.merits += 1\n        var objective=0.5*state.boardMass')
    source=once(source,'        for _ in 0..<16 {\n            state=before','        for _ in 0..<16 {\n            HistoryTrace.trials += 1\n            state=before')
    return source

def contact_trace(source):
    source=once(source,'        for _ in 0..<maxIterations {','        for iteration in 0..<maxIterations {')
    source=once(source,'            return Solution(base:Array(correction.prefix(size))','            HistoryTrace.qps.append(["iterations":iteration+1,"active":active.count,"responses":responses.count,"contacts":contacts.count])\n            return Solution(base:Array(correction.prefix(size))')
    return source
