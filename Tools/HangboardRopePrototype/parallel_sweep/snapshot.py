from pathlib import Path
def collider_source(s):return s+"\n"+Path(__file__).with_name("Sweep.swift").read_text()
def solver_source(s):
    start=s.index('            let radius=state.ropes[r].radius-0.00005')
    end=s.index('            guard RopeMotionSweep.selfContactValid',start)
    s=s[:start]+"""            guard collider.sweepChainIsClear(previous:old,next:state,rope:r,
                clearances:acceptedSegmentClearances?[r],globalClearance:acceptedMinimumClearance) else {throw StepFailure.sweptWoodTraversal}
"""+s[end:]
    return s
