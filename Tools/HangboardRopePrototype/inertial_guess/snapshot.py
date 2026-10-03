def solver_source(s):
    marker='        for _ in 0..<80 {\n            let movement=try correctConstraints(prediction:prediction)'
    assert s.count(marker)==1
    prefix="""        // Only the nonlinear initial guess changes. prediction retains gravity.
        let gravityOffset=9.81*damping*dt*dt
        let offsets=state.ropes.map{rope in rope.positions.indices.map{i in
            rope.supports[i] == nil && rope.attachments[i] == nil ? SIMD3<Double>(0,gravityOffset,0):.zero
        }}
        if Self.correctionFraction(ropes:state.ropes,corrections:offsets,heightCorrection:gravityOffset)==1 {
            state.boardHeight += gravityOffset
            for r in state.ropes.indices {
                for i in state.ropes[r].positions.indices {state.ropes[r].positions[i] += offsets[r][i]}
                for (i,local) in state.ropes[r].attachments {state.ropes[r].positions[i]=state.worldPoint(local)}
            }
            do {try RopePassageTopology.refresh(state:&state,input:input)}
            catch RopePhysicsError.invalid {state=prediction;try RopePassageTopology.refresh(state:&state,input:input)}
        }
"""
    return s.replace(marker,prefix+marker)
