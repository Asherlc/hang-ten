"""User-authorized native-only composed free predictor and endpoint response."""
from pathlib import Path
from armijo.snapshot import once


def solver_source(source):
    source=once(source,'    var armijoExperiment=false','    var armijoExperiment=false\n    var composedExperiment=false\n    private var composedResponseSquare:Double?=nil')
    source=once(source,'        let tensionScale=pow(dt/lastStepDuration,2)', '''        let composedActive=composedExperiment && dt==1.0/120
        let currentResponseSquare=composedActive ? RopeComposedStep.responseSquare:dt*dt
        let tensionScale=composedExperiment ? currentResponseSquare/(composedResponseSquare ?? pow(lastStepDuration,2)):pow(dt/lastStepDuration,2)''')
    source=once(source,'        state.orientation=simd_slerp(old.orientation,targetOrientation,fraction)', '''        var midpointOrientation=old.orientation
        if composedActive {
            let h=RopeComposedStep.h
            midpointOrientation=simd_slerp(old.orientation,targetOrientation,angle>1e-9 ? min(1,h*2.1/angle):1)
            let midDot=min(1,abs(simd_dot(midpointOrientation.vector,targetOrientation.vector)))
            let midAngle=2*acos(midDot)
            state.orientation=simd_slerp(midpointOrientation,targetOrientation,midAngle>1e-9 ? min(1,h*2.1/midAngle):1)
        } else {
            state.orientation=simd_slerp(old.orientation,targetOrientation,fraction)
        }''')
    source=once(source,'''        state.boardVerticalVelocity=(old.boardVerticalVelocity-9.81*dt)*damping
        state.boardHeight += state.boardVerticalVelocity*dt''', '''        if composedActive {
            let velocities=RopeComposedStep.heights(old.boardVerticalVelocity)
            state.boardVerticalVelocity=velocities.1
            state.boardHeight=(old.boardHeight+velocities.0*RopeComposedStep.h)+velocities.1*RopeComposedStep.h
        } else {
            state.boardVerticalVelocity=(old.boardVerticalVelocity-9.81*dt)*damping
            state.boardHeight += state.boardVerticalVelocity*dt
        }''')
    source=once(source,'                    state.ropes[r].positions[i] += (rope.velocities[i]+SIMD3(0,-9.81*dt,0))*damping*dt', '''                    if composedActive {
                        let velocities=RopeComposedStep.velocities(rope.velocities[i])
                        state.ropes[r].positions[i]=(rope.positions[i]+velocities.0*RopeComposedStep.h)+velocities.1*RopeComposedStep.h
                    } else {
                        state.ropes[r].positions[i] += (rope.velocities[i]+SIMD3(0,-9.81*dt,0))*damping*dt
                    }''')
    source=once(source,'let limit=convergenceExperiment ? (arrivedNow ? 0.001*dt:0.00005):1e-8',
                'let limit=convergenceExperiment ? (arrivedNow ? (composedActive ? RopeComposedStep.arrivalLimit:0.001*dt):0.00005):1e-8')
    needle='''        for r in state.ropes.indices {
            state.ropes[r].previousPositions=old.ropes[r].positions
            for i in state.ropes[r].positions.indices {
                state.ropes[r].velocities[i]=(state.ropes[r].positions[i]-old.ropes[r].positions[i])/dt
            }
        }
        state.boardVerticalVelocity=(state.boardHeight-old.boardHeight)/dt'''
    source=once(source,needle,'''        // This midpoint is only a velocity reconstruction device, not a solved
        // or accepted fine state. The unchanged CCD above certifies old-to-final.
        var midpoint=old
        if composedActive {
            midpoint.orientation=midpointOrientation
            let velocities=RopeComposedStep.heights(old.boardVerticalVelocity)
            midpoint.boardHeight=old.boardHeight+velocities.0*RopeComposedStep.h+(state.boardHeight-prediction.boardHeight)/(2+RopeComposedStep.damping)
        }
        for r in state.ropes.indices {
            state.ropes[r].previousPositions=old.ropes[r].positions
            for i in state.ropes[r].positions.indices {
                if composedActive {
                    if state.ropes[r].supports[i] != nil {state.ropes[r].velocities[i] = .zero}
                    else if let attachment=state.ropes[r].attachments[i] {
                        state.ropes[r].velocities[i]=(state.ropes[r].positions[i]-midpoint.worldPoint(attachment))/RopeComposedStep.h
                    } else {
                        let velocities=RopeComposedStep.velocities(old.ropes[r].velocities[i])
                        state.ropes[r].velocities[i]=velocities.1+RopeComposedStep.velocityCoefficient*(state.ropes[r].positions[i]-prediction.ropes[r].positions[i])/RopeComposedStep.h
                    }
                } else {
                    state.ropes[r].velocities[i]=(state.ropes[r].positions[i]-old.ropes[r].positions[i])/dt
                }
            }
        }
        if composedActive {
            state.boardVerticalVelocity=RopeComposedStep.heights(old.boardVerticalVelocity).1+RopeComposedStep.velocityCoefficient*(state.boardHeight-prediction.boardHeight)/RopeComposedStep.h
        } else {
            state.boardVerticalVelocity=(state.boardHeight-old.boardHeight)/dt
        }''')
    source=once(source,'        lastStepDuration=dt','        lastStepDuration=dt\n        composedResponseSquare=currentResponseSquare')
    return source+'\n'+(Path(__file__).parent/'Checkpoint.swift').read_text()


def driver_source(text):
    text=once(text,'var control=initial,candidate=initial,records:[[String:Any]]=[]',
              'var control=initial,candidate=initial,records:[[String:Any]]=[]\ncandidate.composedExperiment=true\ntry composedFixtures(initial:initial,input:input,collider:collider)')
    text=once(text,'"controlHz":240,"preflight":preflight,"armijoEnabled":false]',
              '"controlHz":240,"preflight":preflight,"armijoEnabled":false,"composedPredictor":true,"arrivalLimit":RopeComposedStep.arrivalLimit]')
    text=text.replace('candidate.bundleCheckpoint()','candidate.composedCheckpoint()').replace('control.bundleCheckpoint()','control.composedCheckpoint()')
    text=text.replace('RopeDynamicsSolver.restoreBundle(input:input,collider:collider,data:checkpoint,strict:true)',
                      'RopeDynamicsSolver.restoreComposedReference(input:input,collider:collider,data:checkpoint,strict:true)')
    text=text.replace('RopeDynamicsSolver.restoreBundle(input:input,collider:collider,data:serialize(candidate.composedCheckpoint()),strict:true)',
                      'RopeDynamicsSolver.restoreComposedReference(input:input,collider:collider,data:serialize(candidate.composedCheckpoint()),strict:true)')
    assert 'RopeDynamicsSolver.restoreBundle' not in text
    text=once(text,'"trace":measured.1,"difference":difference(control,candidate),"settled":measured.2.settled]', '''"trace":measured.1,"difference":difference(control,candidate),"settled":measured.2.settled,
            "boardHeightDifference":abs(control.state.boardHeight-candidate.state.boardHeight),
            "boardVelocityDifference":abs(control.state.boardVerticalVelocity-candidate.state.boardVerticalVelocity),
            "maximumVelocityDifference":zip(control.state.ropes,candidate.state.ropes).map {a,b in zip(a.velocities,b.velocities).map{simd_distance($0,$1)}.max()!}.max()!]''')
    return text
