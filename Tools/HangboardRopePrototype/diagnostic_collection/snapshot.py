"""Only native diagnostic storage changes; physical arithmetic is unchanged."""
def once(s,old,new):
    assert s.count(old)==1,(old,s.count(old))
    return s.replace(old,new)
def solver_source(s):
    start='                    ArmijoTrace.corrections.append(['
    end='"armijoRejected":armijoRejected,"originalRejected":originalRejected])'
    s=once(s,start,'                    if SolverCollection.collect {ArmijoTrace.corrections.append([')
    s=once(s,end,end+'}')
    s=once(s,'if preconditionedResidualExperiment {ResidualStopTrace.estimates.append(maximum)}',
        'if preconditionedResidualExperiment && SolverCollection.collect {ResidualStopTrace.estimates.append(maximum)}')
    return s
def collider_source(s):
    s=once(s,'        let storage=RopeContactBatchStorage(points:points.count),links=points.count-1',
        '        let batchStart=SolverCollection.profile ? DispatchTime.now().uptimeNanoseconds:0\n        defer {if SolverCollection.profile {SolverCollection.batchNanos += DispatchTime.now().uptimeNanoseconds-batchStart}}\n        let storage=RopeContactBatchStorage(points:points.count),links=points.count-1')
    anchor="""            for i in ranges(points.count,job) {storage.inside[i]=queryParity(points[i])}
        }
        DispatchQueue.concurrentPerform(iterations:jobs) {job in"""
    replacement="""            for i in ranges(points.count,job) {storage.inside[i]=queryParity(points[i])}
        }
        let narrowStart=SolverCollection.profile ? DispatchTime.now().uptimeNanoseconds:0
        defer {if SolverCollection.profile {SolverCollection.narrowNanos += DispatchTime.now().uptimeNanoseconds-narrowStart}}
        DispatchQueue.concurrentPerform(iterations:jobs) {job in"""
    return once(s,anchor,replacement)
