"""Prospective fixed0.1s clock-offset spread gate. No runtime/host mutation."""
import math
THRESHOLD_SECONDS=.1

def audit(rows,commands,captures,transitions):
    errors=[]
    def req(ok,label):
        if not ok:errors.append(label)
    app=[];host=[]
    for r in rows:
        ok=all(type(r.get(k)) in (int,float) and math.isfinite(r[k]) for k in ('epoch','uptime'))
        req(ok,'finite app epoch/uptime at sequence '+str(r.get('sequence')))
        if ok:app.append(dict(sequence=r['sequence'],event=r['event'],offset=r['epoch']-r['uptime']))
    for i,c in enumerate(commands):
        for prefix in ('start','end'):
            ok=all(type(c.get(prefix+k)) in (int,float) and math.isfinite(c[prefix+k]) for k in ('Epoch','Monotonic'))
            req(ok,'finite host '+prefix+' clock pair at command '+str(i))
            if ok:host.append(dict(commandIndex=i,boundary=prefix,offset=c[prefix+'Epoch']-c[prefix+'Monotonic']))
    def extent(items):
        if not items:return dict(count=0,minimum=None,maximum=None,spread=None,passed=False)
        values=[x['offset'] for x in items];spread=max(values)-min(values)
        return dict(count=len(items),minimum=min(values),maximum=max(values),spread=spread,passed=spread<=THRESHOLD_SECONDS)
    appExtent=extent(app);hostExtent=extent(host)
    req(appExtent['passed'],'app max-min(epoch-uptime) exceeds0.1s or absent')
    req(hostExtent['passed'],'host max-min(epoch-monotonic) exceeds0.1s or absent')
    req(len(captures)==12 and len(transitions)==3,'original12 captures and3 phases')
    details=[]
    for c in captures:
        matches=[x for x in commands if c['path'] in x['command']]
        req(len(matches)==1,'unique command for '+c['path'])
        if len(matches)!=1:continue
        cmd=matches[0];phase=c['phaseIndex'];req(phase in (0,1,2) and c['offset'] in (.25,1,3,5),'original capture phase/offset')
        if phase not in range(len(transitions)):continue
        mutation=transitions[phase]['actualMutation'];wall=cmd['startEpoch']-mutation['epoch']-c['offset'];mono=cmd['startMonotonic']-mutation['uptime']-c['offset']
        req(c['startEpoch']==cmd['startEpoch'] and c['endEpoch']==cmd['endEpoch'],'capture/command timestamp identity')
        req(0<=wall<=.150 and 0<=mono<=.150,'original150ms capture start deadline in both recorded clock domains')
        req(cmd['endEpoch']>=cmd['startEpoch'] and cmd['endMonotonic']>=cmd['startMonotonic'],'nonnegative command duration')
        details.append(dict(path=c['path'],epochStartLateness=wall,monotonicStartLateness=mono,epochDuration=cmd['endEpoch']-cmd['startEpoch'],monotonicDuration=cmd['endMonotonic']-cmd['startMonotonic']))
    req(sorted((c['phaseIndex'],c['offset']) for c in captures)==[(p,o) for p in range(3) for o in [.25,1,3,5]],'exact original phase/offset inventory')
    return dict(criterion='PROSPECTIVE_AWAKE_CONTEXT_CLOCK_STABILITY',thresholdSeconds=THRESHOLD_SECONDS,passed=not errors,errors=errors,appClock=appExtent,hostClock=hostExtent,appOffsets=app,hostOffsets=host,captureTiming=details,causalComparisonEligible=not errors,limits=['Clock stability does not prove uninterrupted OS scheduling, continuous GPU state or an underlying cause.','Failure forbids the planned causal comparison; raw prior validator results are never rewritten.','This checks recorded clock pairs only; assertion-wrapper operation is separate evidence.'])
