"""Deliberate feasibility-stop revisit with fresh full-step and actual-quiet guards."""
from armijo.snapshot import once
from quiet_strain.snapshot import driver_source as quiet_driver,trajectory_source as quiet_trajectory,solver_source as quiet_solver

def solver_source(source):
    source=quiet_solver(source).replace('quietStrainExperiment','fullstepFeasibleExperiment')
    source=once(source,'                terminating=maximumStrain()<0.0002 && lastCorrectionFullStep && (!quiet || movement<0.001*dt)', '                let materialError=state.ropes.reduce(0.0){value,rope in\n                    let length=rope.restLengths.indices.reduce(0.0){$0+simd_distance(rope.positions[$1],rope.positions[$1+1])}\n                    return max(value,abs(length-rope.restLengths.reduce(0,+)))\n                }\n                let strain=maximumStrain()\n                terminating=lastCorrectionFullStep && (quiet ? (strain<0.0002 && movement<0.001*dt):(strain<0.005 && materialError<0.0005))')
    return source

def driver_source(source,checkpoint=109):
    return quiet_driver(source,checkpoint).replace('quietStrainExperiment','fullstepFeasibleExperiment').replace('quietStrainStop','fullstepFeasibleStop')

def trajectory_source(source):
    return quiet_trajectory(source).replace('quietStrainExperiment','fullstepFeasibleExperiment').replace('quietStrainStop','fullstepFeasibleStop')
