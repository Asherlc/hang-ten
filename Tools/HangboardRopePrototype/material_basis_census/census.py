"""Necessary representability census; stdlib only, no reduced dynamics solve."""
import argparse,json,hashlib,math
from pathlib import Path

def norm(v):return math.sqrt(sum(x*x for x in v))
def distance(a,b):return norm([x-y for x,y in zip(a,b)])

def basis(points,rest,protected):
    """Input-only knots; immutable material-linear chord error <=5um."""
    arc=[0.]
    for length in rest:arc.append(arc[-1]+length)
    knots=set(protected)|{0,len(points)-1}
    def refine(a,b):
        if b<=a+1:return
        errors=[]
        for k in range(a+1,b):
            t=(arc[k]-arc[a])/(arc[b]-arc[a])
            errors.append(distance(points[k],[(1-t)*x+t*y for x,y in zip(points[a],points[b])]))
        k=max(range(a+1,b),key=lambda k:errors[k-a-1])
        if errors[k-a-1]>5e-6:knots.add(k);refine(a,k);refine(k,b)
    ks=sorted(knots)
    for a,b in zip(ks,ks[1:]):refine(a,b)
    ks=sorted(knots);P=[{} for _ in points]
    for column,(a,b) in enumerate(zip(ks,ks[1:])):
        for i in range(a,b+1):
            t=(arc[i]-arc[a])/(arc[b]-arc[a]);P[i]={column:1-t,column+1:t}
    return ks,P

def project(rope,protected):
    x=rope['positions'];d=rope['displacements'];w=rope['weights'];rest=rope['restLengths']
    knots,P=basis(x,rest,protected)
    fixed=set(rope['supports'])|set(rope['attachments'])
    free=[j for j,k in enumerate(knots) if k not in fixed];slots={column:i for i,column in enumerate(free)}
    offset=[[sum(v*d[knots[j]][axis] for j,v in row.items() if knots[j] in fixed) for axis in range(3)] for row in P]
    mass=[1/value if value>0 else 0. for value in w]
    n=len(free);G=[[0.]*n for _ in free];rhs=[[0.]*3 for _ in free]
    for i,row in enumerate(P):
        terms=[(slots[j],v) for j,v in row.items() if j in slots]
        for j,v in terms:
            for axis in range(3):rhs[j][axis]+=mass[i]*v*(d[i][axis]-offset[i][axis])
            for k,u in terms:G[j][k]+=mass[i]*v*u
    assert all(G[i][j]==0 for i in range(n) for j in range(n) if abs(i-j)>1)
    diag=[];sub=[];y=[[0.]*3 for _ in free]
    for i in range(n):
        lower=G[i][i-1]/diag[i-1] if i else 0.;sub.append(lower)
        pivot=G[i][i]-lower*lower;assert pivot>0
        diag.append(math.sqrt(pivot))
        for axis in range(3):y[i][axis]=(rhs[i][axis]-(lower*y[i-1][axis] if i else 0.))/diag[i]
    z=[[0.]*3 for _ in free]
    for i in reversed(range(n)):
        for axis in range(3):z[i][axis]=(y[i][axis]-(sub[i+1]*z[i+1][axis] if i+1<n else 0.))/diag[i]
    fitted=[[offset[i][axis]+sum(v*z[slots[j]][axis] for j,v in row.items() if j in slots) for axis in range(3)] for i,row in enumerate(P)]
    assert all(distance(fitted[i],d[i])<=1e-15 for i in fixed)
    residual=[[0.]*3 for _ in free]
    for i,row in enumerate(P):
        for j,v in row.items():
            if j in slots:
                for axis in range(3):residual[slots[j]][axis]+=mass[i]*v*(fitted[i][axis]-d[i][axis])
    return {'knots':knots,'particleDOFsBefore':3*sum(value>0 for value in w),'particleDOFsAfter':3*n,
        'maxUndampedDisplacementError':max(distance(a,b) for a,b in zip(fitted,d)),
        'projectionStationarity':max((abs(v) for row in residual for v in row),default=0.)},fitted

def main():
    ap=argparse.ArgumentParser();ap.add_argument('input',type=Path);ap.add_argument('output',type=Path)
    ap.add_argument('--require-every-trial-physical',action='store_true');args=ap.parse_args()
    raw=json.loads(args.input.read_text());records=[]
    for checkpoint in raw['checkpoints']:
        for index,correction in enumerate(checkpoint['corrections']):
            data=correction['basisData'];protected=[set(r['supports'])|set(r['attachments']) for r in data['ropes']]
            for r,rope in enumerate(data['ropes']):
                for p in rope['portals']:protected[r].update([p,p+1])
            for row in data['contacts']:
                for r,p in row:protected[r].add(p)
            ropes=[];physical=[];queryWork=[]
            for r,rope in enumerate(data['ropes']):
                report,fit=project(rope,protected[r]);ropes.append(report)
                trial=[[x+correction['alpha']*y for x,y in zip(p,d)] for p,d in zip(rope['positions'],fit)]
                lengths=[distance(a,b) for a,b in zip(trial,trial[1:])];rest=rope['restLengths']
                physical.append({'strain':max(abs(a/b-1) for a,b in zip(lengths,rest)),
                    'materialError':abs(sum(lengths)-sum(rest))})
                if data.get('queryCosts'):
                    assert len(data['ropes'])==1 and len(data['queryCosts'])==len(rest)
                    costs=data['queryCosts'];knots=set(report['knots']);n=len(costs);chunk=(n+3)//4
                    totals=[];retained=[]
                    for worker in range(4):
                        indices=range(min(n,worker*chunk),min(n,(worker+1)*chunk))
                        totals.append(sum(costs[i] for i in indices))
                        retained.append(sum(costs[i] for i in indices if i in knots and i+1 in knots))
                    queryWork.append({'workerOriginalQuerySeconds':totals,'workerRetainedQuerySeconds':retained,
                        'optimisticRemovedQueryWallSeconds':max(totals)-max(retained),
                        'retainedWeightedQueryFraction':sum(retained)/sum(totals),
                        'coalescedSpanQueryCostAssumedZero':True,'parityJoinAndFinalVerificationExcluded':True})
            before=1+data['equalityRows']+sum(r['particleDOFsBefore'] for r in ropes)
            after=1+data['equalityRows']+sum(r['particleDOFsAfter'] for r in ropes)
            records.append({'step':checkpoint['step'],'correction':index+1,'alpha':correction['alpha'],
                'ropes':ropes,'reconstructedLengthChecks':physical,'equalityRowsRetained':data['equalityRows'],
                'contactRowsRetained':data['contactRows'],'baseKKTBefore':before,'baseKKTAfter':after,
                'baseKKTRatio':after/before,'fullMeshVerified':False,
                'publishedStepState':index+1==len(checkpoint['corrections']),
                'originalTrialStrain':correction['strain'],'queryWork':queryWork,
                'displacementFitPass':max(r['maxUndampedDisplacementError'] for r in ropes)<=50e-6,
                'lengthPass':all(r['strain']<=.005 and r['materialError']<=.0005 for r in physical)})
    result={'owner':'strong-owl-live-physics','adopted':False,'reducedBackend':False,'queryWeightedSpeedProof':False,
        'basisConstruction':'input-only5um material chord; all candidate contact/portal/support/attachment coordinates retained',
        'inputSHA256':hashlib.sha256(args.input.read_bytes()).hexdigest(),'records':records,
        'physicalPhaseRule':'every-trial' if args.require_every_trial_physical else 'published-step-only; intermediate diagnostics retained',
        'necessaryRepresentabilityPass':all(r['displacementFitPass'] and (r['lengthPass'] or (not r['publishedStepState'] and not args.require_every_trial_physical)) for r in records),
        'maxDisplacementError':max(p['maxUndampedDisplacementError'] for r in records for p in r['ropes'])}
    args.output.write_text(json.dumps(result,indent=2)+'\n')
    print('MATERIAL BASIS',result['necessaryRepresentabilityPass'],'maxfit',result['maxDisplacementError'],
        'KKT ratios',[round(r['baseKKTRatio'],3) for r in records])
    return 0 if result['necessaryRepresentabilityPass'] else 3

if __name__=='__main__':raise SystemExit(main())
