"""Fresh-Jacobian fixed-working-set certificate; estimates never applied."""
from pathlib import Path
from armijo.snapshot import once

def solver_source(source):
    source=once(source,'    var woodFeatureIdentityExperiment=false',
        '    var woodFeatureIdentityExperiment=false\n    var freshActiveStopExperiment=false')
    source=once(source,'        guard Set(ids).count==ids.count else{return nil}',
        '''        guard Set(ids).count==ids.count else{return nil}
        if freshActiveStopExperiment {
            return freshActiveEstimate(rows:rows,weights:weights,prediction:prediction,ids:ids,context:context)
        }''')
    return source+'\n'+Path(__file__).with_name('Solver.swift.txt').read_text()

def driver_source(source,enabled=True):
    source=source.replace('candidate.woodFeatureIdentityExperiment=true',
        'candidate.woodFeatureIdentityExperiment=true;candidate.freshActiveStopExperiment='+str(enabled).lower())
    source=source.replace('b.woodFeatureIdentityExperiment=true',
        'b.woodFeatureIdentityExperiment=true;b.freshActiveStopExperiment='+str(enabled).lower())
    source=once(source,'"woodFeatureIdentity":true','"woodFeatureIdentity":true,"freshActiveStop":'+str(enabled).lower())
    return source
