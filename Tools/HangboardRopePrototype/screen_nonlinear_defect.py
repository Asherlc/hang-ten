"""Independent retained-output checks; not a new simulation or acceptance waiver."""
import json,math,hashlib,os,sys
from pathlib import Path
root=Path('.context/strong-owl-live-physics-portal-curvature')
stage=root/'clav-coupled-step'
report=json.loads((stage/'report.json').read_text())
checkpoint=json.loads((stage/'restored-checkpoint.json').read_text())
mesh=json.loads(Path('Hangboards/clavellium-training-block/assets/primary.physics.json').read_text())
def add(a,b):return [x+y for x,y in zip(a,b)]
def sub(a,b):return [x-y for x,y in zip(a,b)]
def mul(a,t):return [x*t for x in a]
def dot(a,b):return sum(x*y for x,y in zip(a,b))
def cross(a,b):return [a[1]*b[2]-a[2]*b[1],a[2]*b[0]-a[0]*b[2],a[0]*b[1]-a[1]*b[0]]
def square(a):return dot(a,a)
def norm(a):return math.sqrt(square(a))
def rotate(q,p):
    # Independent quaternion vector formula rather than simd's implementation.
    v=q[:3];return add(p,mul(add(cross(v,p),mul(cross(v,cross(v,p)),1/q[3])),2*q[3])) if q[3]!=0 else add(p,mul(cross(v,cross(v,p)),2))
def board(p,state):
    q=state['orientation'];return rotate([-q[0],-q[1],-q[2],q[3]],sub(p,[0,state['height'],0]))
def point_segment(p,a,b):
    d=sub(b,a);s=square(d)
    return add(a,mul(d,min(1,max(0,dot(sub(p,a),d)/s)))) if s else a
def point_triangle(p,a,b,c):
    u=sub(b,a);v=sub(c,a);n=cross(u,v);n2=square(n)
    projection=sub(p,mul(n,dot(sub(p,a),n)/n2))
    w=sub(projection,a);uu=dot(u,u);vv=dot(v,v);uv=dot(u,v)
    det=uu*vv-uv*uv
    if det:
        s=(dot(w,u)*vv-dot(w,v)*uv)/det;t=(dot(w,v)*uu-dot(w,u)*uv)/det
        if s>=0 and t>=0 and s+t<=1:return projection
    candidates=[point_segment(p,a,b),point_segment(p,b,c),point_segment(p,c,a)]
    return min(candidates,key=lambda q:square(sub(p,q)))
def segment_pair(a,b,c,d):
    candidates=[(a,point_segment(a,c,d)),(b,point_segment(b,c,d)),(point_segment(c,a,b),c),(point_segment(d,a,b),d)]
    u=sub(b,a);v=sub(d,c);w=sub(a,c);aa=square(u);bb=dot(u,v);cc=square(v)
    den=aa*cc-bb*bb
    if den>0:
        s=(bb*dot(v,w)-cc*dot(u,w))/den;t=(aa*dot(v,w)-bb*dot(u,w))/den
        if 0<=s<=1 and 0<=t<=1:candidates.append((add(a,mul(u,s)),add(c,mul(v,t))))
    return min(candidates,key=lambda pair:square(sub(*pair)))
def segment_triangle(p,q,a,b,c):
    distances=[norm(sub(p,point_triangle(p,a,b,c))),norm(sub(q,point_triangle(q,a,b,c)))]
    for x,y in [(a,b),(b,c),(c,a)]:distances.append(norm(sub(*segment_pair(p,q,x,y))))
    n=cross(sub(b,a),sub(c,a));den=dot(sub(q,p),n)
    if den:
        t=dot(sub(a,p),n)/den
        if 0<=t<=1:
            at=add(p,mul(sub(q,p),t))
            if norm(sub(at,point_triangle(at,a,b,c)))<1e-14:distances.append(0)
    return min(distances)

def residual(term,state):
    key=term['key'].split(':');r=int(key[1]);rope=checkpoint['ropes'][r]
    if key[0]=='length':
        i=int(key[2]);return math.dist(state['positions'][r][i],state['positions'][r][i+1])-rope['restLengths'][i]
    if key[0] in ['point','link']:
        i=int(key[2]);j=i if key[0]=='point' else i+1;face=mesh['collision']['triangles'][int(key[3])]
        return segment_triangle(board(state['positions'][r][i],state),board(state['positions'][r][j],state),
            *[mesh['collision']['vertices'][k] for k in face])-rope['radius']-.0001
    if key[0]=='portal':
        identifier=':'.join(key[2:-1]);edge=int(key[-1]);region=next(p for p in mesh['portals'] if p['id']==identifier)
        crossing=state['crossings'][r][identifier];i=int(crossing['segment']);f=crossing['fraction']
        p=board(add(state['positions'][r][i],mul(sub(state['positions'][r][i+1],state['positions'][r][i]),f)),state)
        a=region['boundary'][edge];b=region['boundary'][(edge+1)%len(region['boundary'])]
        n=cross(region['normal'],sub(b,a));n=mul(n,1/norm(n))
        if dot(n,sub(region['center'],a))<0:n=mul(n,-1)
        return dot(sub(p,a),n)-rope['radius']-.0001
    raise AssertionError('Unvalidated feature '+term['key'])

def deterministic(value):
    if isinstance(value,dict):return {k:deterministic(v) for k,v in value.items() if not k.endswith('Seconds')}
    if isinstance(value,list):return list(map(deterministic,value))
    return value

phases=report['reports'][0]['phases'];origin=next(p for p in phases if p['phase']=='iteration' and p['iteration']==15)
direction=next(p for p in phases if p['phase']=='direction' and p['iteration']==15)
prediction=next(p for p in phases if p['phase']=='prediction');variable=prediction['variable'];height=prediction['heightVariable']
terms=origin['terms'];masses=prediction['masses'];min_rest=prediction['minimumRest'];eps=1e-8

def state_at(alpha):
    state=json.loads(json.dumps(origin['state']));state['height']+=alpha*direction['x'][height]
    for r,points in enumerate(state['positions']):
        for i,p in enumerate(points):
            base=variable[r][i]
            if base is not None:points[i]=add(p,mul(direction['x'][base:base+3],alpha))
            elif str(i) in checkpoint['ropes'][r]['attachments']:
                points[i]=add(rotate(state['orientation'],checkpoint['ropes'][r]['attachments'][str(i)]),[0,state['height'],0])
    return state

def row(t,state):
    key=t['key'].split(':');r=int(key[1]);rope=checkpoint['ropes'][r];kind=key[0]
    if kind=='length':
        i=int(key[2]);delta=sub(state['positions'][r][i+1],state['positions'][r][i]);length=norm(delta);n=mul(delta,1/length)
        C=length-rope['restLengths'][i];refs=[(r,i),(r,i+1)];gradients=[mul(n,-1),n];wood=False;witness=None
    elif kind in ['point','link']:
        i=int(key[2]);j=i if kind=='point' else i+1;face=mesh['collision']['triangles'][int(key[3])]
        a,b,c=[mesh['collision']['vertices'][k] for k in face];p=board(state['positions'][r][i],state);q=board(state['positions'][r][j],state)
        candidates=[(p,point_triangle(p,a,b,c),0,'start')]
        if i!=j:
            candidates.append((q,point_triangle(q,a,b,c),1,'end'))
            for edge,(u,v) in enumerate([(a,b),(b,c),(c,a)]):
                first,second=segment_pair(p,q,u,v);fraction=dot(sub(first,p),sub(q,p))/square(sub(q,p))
                candidates.append((first,second,fraction,'edge'+str(edge)))
        first,second,f,witness=min(candidates,key=lambda pair:square(sub(pair[0],pair[1])))
        distance=norm(sub(first,second));assert distance>1e-10
        n=rotate(state['orientation'],mul(sub(first,second),1/distance));refs=[(r,i),(r,j)];gradients=[mul(n,1-f),mul(n,f)]
        C=distance-rope['radius']-.0001;wood=True
    elif kind=='portal':
        id=':'.join(key[2:-1]);edge=int(key[-1]);portal=next(p for p in mesh['portals'] if p['id']==id)
        i=int(state['crossings'][r][id]['segment']);p=board(state['positions'][r][i],state);q=board(state['positions'][r][i+1],state)
        delta=sub(q,p);den=dot(delta,portal['normal']);f=dot(sub(portal['center'],p),portal['normal'])/den
        a=portal['boundary'][edge];b=portal['boundary'][(edge+1)%len(portal['boundary'])]
        inward=cross(portal['normal'],sub(b,a));inward=mul(inward,1/norm(inward))
        if dot(inward,sub(portal['center'],a))<0:inward=mul(inward,-1)
        base=sub(inward,mul(portal['normal'],dot(inward,delta)/den));refs=[(r,i),(r,i+1)]
        gradients=[rotate(state['orientation'],mul(base,1-f)),rotate(state['orientation'],mul(base,f))]
        C=dot(sub(add(p,mul(delta,f)),a),inward)-rope['radius']-.0001;wood=True;witness=i
    else:raise AssertionError('Unsupported derivative feature '+t['key'])
    dh=-sum(g[1] for g in gradients) if wood else 0
    j={}
    for (rr,i),g in zip(refs,gradients):
        base=variable[rr][i]
        if base is not None:
            for axis in range(3):j[base+axis]=j.get(base+axis,0)+g[axis]
        if str(i) in checkpoint['ropes'][rr]['attachments']:dh+=g[1]
    j[height]=j.get(height,0)+dh
    return C,j,witness

def evaluate(alpha):
    state=state_at(alpha);a=[0.0]*len(masses);groups={'length':[0.0]*len(masses),'contact':[0.0]*len(masses)}
    for r,points in enumerate(state['positions']):
        for i,p in enumerate(points):
            base=variable[r][i]
            if base is not None:
                for axis in range(3):a[base+axis]=masses[base+axis]*(p[axis]-prediction['state']['positions'][r][i][axis])
    a[height]=masses[height]*(state['height']-prediction['state']['height'])
    score=0;rows=[]
    for k,t in enumerate(terms):
        C,j,witness=row(t,state);dl=-direction['s'][k] if t['contact'] else direction['lambda'][k]
        dual=t['lambda']+alpha*dl;v=t['v']+alpha*direction['v'][k];group=groups['contact' if t['contact'] else 'length']
        for index,value in j.items():a[index]+=dual*value;group[index]+=dual*value
        if t['contact']:
            h=C-eps*dual-v;score+=(h/t['scale'])**2+(-dual*v/(t['initialS']*t['scale']))**2
        else:score+=((C-eps*dual)/t['scale'])**2
        rows.append((C,j,witness))
    for i,m in enumerate(masses):
        if m:score+=(a[i]/(m*min_rest))**2
    return score,a,groups,rows



# A separately registered one-shot mathematical screen. No accepted state publication.
workroot=Path(sys.argv[1]);mode=sys.argv[2];alpha=0.23872889767888264
assert direction['trials'][1]['alpha']==alpha
for path,digest in json.loads((workroot/'inputs.json').read_text())['sha256'].items():assert hashlib.sha256(Path(path).read_bytes()).hexdigest()==digest,path
score0,a0,_,rows0=evaluate(0);scorep,ap,_,rowsp=evaluate(alpha)
size=len(masses);p=[alpha*v for v in direction['x']];kp=[0.]*size
for ir,jr,value in direction['entries']:
    i,j=int(ir),int(jr);kp[i]+=value*p[j]
    if i!=j:kp[j]+=value*p[i]
Ra=sub(ap,a0);Rb=[0.]*len(terms);Rh=Rb.copy();Rsv=Rb.copy();weights=Rb.copy();loads=Rb.copy();rhs=[0.]*size
for k,t in enumerate(terms):
    C0,J,_=rows0[k];Cp,_,_=rowsp[k];jdx=sum(v*p[i] for i,v in J.items())
    if t['contact']:
        s=-t['lambda'];v=t['v'];ps=alpha*direction['s'][k];pv=alpha*direction['v'][k]
        D=s/(v+eps*s)
        # Undo the condensation terms to obtain the COMPLETE physical Kp.
        for i,value in J.items():kp[i]-=value*(D*jdx+ps)
        Rh[k]=(Cp+eps*(s+ps)-(v+pv))-(C0+eps*s-v)-(jdx+eps*ps-pv)
        Rsv[k]=(s+ps)*(v+pv)-s*v-(v*ps+s*pv)
        weights[k]=D;loads[k]=(-Rsv[k]-s*Rh[k])/(v+eps*s)
    else:
        r,i=map(int,t['key'].split(':')[1:]);index=prediction['lengthVariable'][r][i]
        Rb[k]=(Cp-eps*(t['lambda']+alpha*direction['lambda'][k]))-(C0-eps*t['lambda'])-kp[index]
for i,m in enumerate(masses):
    if m:Ra[i]-=kp[i];rhs[i]=-Ra[i]
    else:Ra[i]=0
for k,t in enumerate(terms):
    if t['contact']:
        for i,v in rows0[k][1].items():rhs[i]+=v*loads[k]
    else:
        r,i=map(int,t['key'].split(':')[1:]);rhs[prediction['lengthVariable'][r][i]]=-Rb[k]
if mode=='prepare':
    out={'size':size,'equalities':[j for line in prediction['lengthVariable'] for j in line],'entries':direction['entries'],'rhs':rhs,'R_a':Ra,'R_b':Rb,'R_h':Rh,'R_sv':Rsv,'alpha':alpha}
    (workroot/'linear-input.json').write_text(json.dumps(out,indent=2)+'\n');print('Prepared original-matrix one-shot defect RHS',size);raise SystemExit(0)
assert mode=='evaluate'
linear=json.loads((workroot/'linear-result.json').read_text());ex=linear['e'];es=[0.]*len(terms);ev=es.copy();el=es.copy()
for k,t in enumerate(terms):
    jex=sum(v*ex[i] for i,v in rows0[k][1].items())
    if t['contact']:
        es[k]=loads[k]-weights[k]*jex;ev[k]=jex+eps*es[k]+Rh[k];el[k]=-es[k]
    else:
        r,i=map(int,t['key'].split(':')[1:]);el[k]=ex[prediction['lengthVariable'][r][i]]
# Independent complete KKT linear-system certificate, including recovery signs.
pe=[0.]*size
for ir,jr,val in direction['entries']:
    i,j=int(ir),int(jr);pe[i]+=val*ex[j]
    if i!=j:pe[j]+=val*ex[i]
maxb=maxh=maxcomp=0
for k,t in enumerate(terms):
    jex=sum(v*ex[i] for i,v in rows0[k][1].items())
    if t['contact']:
        for i,v in rows0[k][1].items():pe[i]-=v*(weights[k]*jex+es[k])
        maxh=max(maxh,abs(jex+eps*es[k]-ev[k]+Rh[k]))
        maxcomp=max(maxcomp,abs(t['v']*es[k]-t['lambda']*ev[k]+Rsv[k]))
    else:
        r,i=map(int,t['key'].split(':')[1:]);index=prediction['lengthVariable'][r][i]
        maxb=max(maxb,abs(pe[index]+Rb[k]))
maxa=max(abs(pe[i]+Ra[i]) for i,m in enumerate(masses) if m)
old_state=state_at(alpha);new_state=json.loads(json.dumps(old_state));new_state['height']+=ex[height]
for r,points in enumerate(new_state['positions']):
    for i,point in enumerate(points):
        base=variable[r][i]
        if base is not None:points[i]=add(point,ex[base:base+3])
        elif str(i) in checkpoint['ropes'][r]['attachments']:
            points[i]=add(rotate(new_state['orientation'],checkpoint['ropes'][r]['attachments'][str(i)]),[0,new_state['height'],0])
original_terms=json.loads(json.dumps(terms));positiveS=positiveV=float('inf')
for k,t in enumerate(terms):
    t['lambda']+=alpha*(-direction['s'][k] if t['contact'] else direction['lambda'][k])+el[k]
    if t['contact']:
        t['v']+=alpha*direction['v'][k]+ev[k]
        positiveS=min(positiveS,(-t['lambda'])/(-original_terms[k]['lambda']))
        positiveV=min(positiveV,t['v']/original_terms[k]['v'])
# One corrected evaluation; native topology/sign checks follow only if cheap guards pass.
def state_at(ignored):return new_state
score,a,groups,rows=evaluate(0)
maxtrust=0;movement=abs(new_state['height']-origin['state']['height'])
for r,rope in enumerate(checkpoint['ropes']):
    displacement=[sub(q,p) for p,q in zip(origin['state']['positions'][r],new_state['positions'][r])]
    movement=max(movement,max(map(norm,displacement)))
    for i,rest in enumerate(rope['restLengths']):maxtrust=max(maxtrust,norm(sub(displacement[i+1],displacement[i]))/rest)
checks={'matrixResidual':linear['maximumMatrixResidual'],'recoveredStationarityResidual':maxa,'recoveredEqualityResidual':maxb,'recoveredContactResidual':maxh,'recoveredComplementarityResidual':maxcomp,'sFractionMinimum':positiveS,'vFractionMinimum':positiveV,'combinedRelativeDisplacementMaximum':maxtrust,'correctedScore':score,'armijoMaximum':(1-1e-4*alpha)*score0}
failed=[]
if maxa>1e-10 or maxb>1e-8 or maxh>1e-10 or maxcomp>1e-14:failed.append('full recovered linear certificate')
if positiveS<.005 or positiveV<.005:failed.append('original positivity margin')
if maxtrust>.1:failed.append('combined original displacement trust')
if score>(1-1e-4*alpha)*score0:failed.append('unchanged Armijo')
out={'scope':'one-shot mathematical fullKKT defect correction; not a dynamics step','alpha':alpha,'baseScore':score0,'uncorrectedScore':scorep,'correctedScore':score,'checks':checks,'failed':failed,'cheapGuardsPassed':not failed,'nativeTopologySign':'not-run; required only after cheap guard pass','correction':{'x':ex,'s':es,'v':ev,'lambda':el},'correctedState':new_state,'updatedForceSlackTermsWithOriginGeometry':terms,'maximumMovement':movement,'solveCalls':linear['solveCalls'],'refinementSolves':linear['refinementSolves']}
(workroot/'result.json').write_text(json.dumps(out,indent=2)+'\n');print(json.dumps({k:v for k,v in out.items() if k not in ['correction','correctedState','correctedTerms']},indent=2))
raise SystemExit(0 if not failed else 1)
