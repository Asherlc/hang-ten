"""Separate solver execution, diagnostic/handoff span and idle from app logs."""
import argparse,json,math,re
from pathlib import Path
p=argparse.ArgumentParser();p.add_argument('root',type=Path);args=p.parse_args()
root=args.root

def analyze(path):
    batches={};order=[];latestEngine=None;targets={}
    for line in path.read_text().splitlines():
        if 'controller target ' in line:
            m=re.search(r'generation=(\d+) orientation=SIMD4<Double>\((.*)\)',line);assert m,line
            generation,vector=m.groups();targets[int(generation)]=[float(x.strip()) for x in vector.split(',')]
        elif 'controller batch start ' in line:
            m=re.search(r'steps=(\d+).*generation=(\d+) batch=(\d+) startNanos=(\d+) continuous=(\w+)',line)
            assert m,line
            steps,generation,batch,start,mode=m.groups();batch=int(batch)
            assert batch not in batches and 1<=int(steps)<=8
            batches[batch]={'requestedSteps':int(steps),'generation':int(generation),'startNanos':int(start),'continuous':mode=='true'}
            order.append(batch)
        elif 'engine batch=' in line:
            m=re.search(r'batch=(\d+) startNanos=(\d+) endNanos=(\d+) stepMs=(\[.*\])',line);assert m,line
            batch,start,end,values=m.groups();latestEngine=int(batch)
            b=batches[latestEngine];b.update(engineStartNanos=int(start),engineEndNanos=int(end),stepMs=json.loads(values))
        elif 'worker end ' in line and latestEngine is not None:
            batches[latestEngine]['settled']='settled=Optional(true)' in line
        elif 'worker metrics ' in line and latestEngine is not None:
            pairs=re.findall(r'(\w+)=([^ ]+)',line)
            batches[latestEngine]['metrics']={k:float(v) for k,v in pairs}
        elif 'controller batch returned ' in line:
            m=re.search(r'ms=([^ ]+) deliverable=(\w+) batch=(\d+) endNanos=(\d+)',line);assert m,line
            elapsed,deliverable,batch,end=m.groups()
            batches[int(batch)].update(endNanos=int(end),returnedMilliseconds=float(elapsed),deliverable=deliverable=='true')
        elif 'batch failed' in line or 'invalidSuspension' in line:
            raise AssertionError(line)
    rows=[batches[k] for k in order]
    assert rows and all('endNanos' in b and 'metrics' in b for b in rows)
    steps=[x for b in rows for x in b['stepMs']]
    assert steps and all(math.isfinite(x) and x>=0 for x in steps)
    for b in rows:
        assert len(b['stepMs'])==b['metrics']['acceptedSteps']
        assert b['metrics']['caps']==0 and b['metrics']['retries']==0
        assert b['metrics']['maximumStrain']<=.005 and b['metrics']['minimumClearanceMargin']>=-.00005
        assert b['startNanos']<=b['engineStartNanos']<=b['engineEndNanos']<=b['endNanos']
    settled=[b for b in rows if b['settled'] and b['deliverable']]
    assert len(settled)==2
    generations=list(dict.fromkeys(b['generation'] for b in rows))
    assert len(generations)==2 and [b['generation'] for b in settled]==generations
    phaseWork=[{'generation':g,'target':targets[g],
        'acceptedSteps':sum(len(b['stepMs']) for b in rows if b['generation']==g),
        'corrections':sum(b['metrics']['corrections'] for b in rows if b['generation']==g)} for g in generations]
    total=(rows[-1]['endNanos']-rows[0]['startNanos'])/1e6
    engine=sum((b['engineEndNanos']-b['engineStartNanos'])/1e6 for b in rows)
    before=sum((b['engineStartNanos']-b['startNanos'])/1e6 for b in rows)
    after=sum((b['endNanos']-b['engineEndNanos'])/1e6 for b in rows)
    idle=sum((b['startNanos']-a['endNanos'])/1e6 for a,b in zip(rows,rows[1:]))
    assert abs(total-engine-before-after-idle)<1e-6
    sortedSteps=sorted(steps);p95=sortedSteps[math.ceil(.95*len(steps))-1]
    delivered=[b for b in rows if b['deliverable']]
    deliveryGaps=[(b['endNanos']-a['endNanos'])/1e6 for a,b in zip(delivered,delivered[1:]) if a['generation']==b['generation']]
    sortedGaps=sorted(deliveryGaps)
    return {'batches':rows,'phaseWork':phaseWork,'acceptedSteps':len(steps),'simulatedMilliseconds':len(steps)/240*1000,
        'endToEndMilliseconds':total,'solverMilliseconds':sum(steps),'engineSpanMilliseconds':engine,
        'beforeWorkerMilliseconds':before,'afterWorkerIncludingDiagnosticWritesMilliseconds':after,
        'betweenBatchesIncludingDeliveryAndTargetTransitionMilliseconds':idle,'individualStepP95Milliseconds':p95,
        'corrections':sum(b['metrics']['corrections'] for b in rows),'settledDeliveries':2,
        'deliveryIntervalP95Milliseconds':sortedGaps[math.ceil(.95*len(sortedGaps))-1],
        'maximumStrain':max(b['metrics']['maximumStrain'] for b in rows),
        'minimumClearanceMargin':min(b['metrics']['minimumClearanceMargin'] for b in rows),
        'actualStepSpeedPassed':p95<4,'scope':'normal-speed simulator only; no physical iPhone evidence'}

baseline=analyze(root/'baseline-capture/stderr.log')
candidate=analyze(root/'candidate-capture/stderr.log')
assert baseline['phaseWork']==candidate['phaseWork'],'Different per-step target workload; wall ratio cannot establish scheduling gain'
assert all(not b['continuous'] for b in baseline['batches'])
assert all(b['continuous'] for b in candidate['batches'])
ratio=candidate['endToEndMilliseconds']/baseline['endToEndMilliseconds']
result={'owner':'strong-owl-live-physics','baseline':baseline,'candidate':candidate,
    'endToEndRatio':ratio,'fixedMaximumRatio':.8,'schedulingGatePassed':ratio<=.8,'adopted':False,
    'samePhysicsSource':True,'normalSpeed':True,'realTimeAccepted':False}
(root/'recording-analysis.json').write_text(json.dumps(result,indent=2)+'\n')
print(json.dumps({k:v for k,v in result.items() if k not in ['baseline','candidate']},indent=2))
for name,data in [('baseline',baseline),('candidate',candidate)]:
 print(name,json.dumps({k:v for k,v in data.items() if k!='batches'},indent=2))
