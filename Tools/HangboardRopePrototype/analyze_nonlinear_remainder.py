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


# Read-only decomposition of an existing direction; never solve or publish a state.
workroot=Path(sys.argv[1])
for name,digest in json.loads((workroot/'inputs.json').read_text())['sha256'].items():assert hashlib.sha256(Path(name).read_bytes()).hexdigest()==digest,name
native=json.loads((workroot/'native-geometry.json').read_text())['records']
assert len(native)==1398
native_by={(r['sample'],r['key']):r for r in native}
explicit=json.loads(Path('.context/strong-owl-live-physics-explicit-wood-curvature/corpus-result.json').read_text())['runs'][0]['records']
wood_by={r['key']:r for r in explicit if r['iteration']==15};assert len(wood_by)==233
portal_by={r['key']:r for r in direction['curvature'] if r['derivativeMethod']=='direct-portal-rational'};assert len(portal_by)==8
original_state_at=state_at
samples={t['alpha']:t['state'] for t in direction['trials']}
def state_at(alpha):return samples.get(alpha,original_state_at(alpha))
size=len(masses)
scale_a=[m*min_rest if m else 1 for m in masses]
def scaled(v):return [x/s for x,s in zip(v,scale_a)]
def l2(v):return math.sqrt(sum(x*x for x in v))
def kind(term):return term['key'].split(':')[0]
def group(term):return 'wood' if kind(term) in ['point','link'] else kind(term)
def hdx(term):
    if group(term) in ['wood','portal']:
        record=(wood_by if group(term)=='wood' else portal_by)[term['key']]
        ids=record['variables'];h=record['hessian']
        return {i:sum(h[r][c]*direction['x'][j] for c,j in enumerate(ids)) for r,i in enumerate(ids)}
    key=term['key'].split(':');r=int(key[1]);i=int(key[2]);rope=checkpoint['ropes'][r]
    delta=sub(origin['state']['positions'][r][i+1],origin['state']['positions'][r][i]);length=norm(delta);normal=mul(delta,1/length)
    seeds={}
    for particle,sign in [(i,-1),(i+1,1)]:
        base=variable[r][particle]
        if base is not None:
            for axis in range(3):
                unit=[0.,0.,0.];unit[axis]=sign;seeds[base+axis]=unit
    attachedA=str(i) in rope['attachments'];attachedB=str(i+1) in rope['attachments']
    if attachedA!=attachedB:seeds[height]=[0.,float(attachedB)-float(attachedA),0.]
    return {ii:sum((dot(a,b)-dot(a,normal)*dot(b,normal))/length*direction['x'][jj] for jj,b in seeds.items()) for ii,a in seeds.items()}
score0,a0,groups0,rows0=evaluate(0)
assert abs(score0-origin['score'])/max(1,origin['score'])<=1e-8
ada=[m*dx for m,dx in zip(masses,direction['x'])]
derivatives=[]
for k,t in enumerate(terms):
    hj=hdx(t);dl=-direction['s'][k] if t['contact'] else direction['lambda'][k]
    C,J,_=rows0[k]
    for i in set(hj)|set(J):ada[i]+=t['lambda']*hj.get(i,0)+dl*J.get(i,0)
    derivatives.append((hj,dl))
initial_stationarity_score=sum((v/s)**2 for v,s in zip(a0,scale_a))
trials=[];max_score_error=max_C_error=max_J_error=max_state_error=max_reconstruction=0
for sample,trial in enumerate(direction['trials']):
    alpha=trial['alpha'];state=state_at(alpha);affine=original_state_at(alpha)
    state_error=max(abs(state['height']-affine['height']),max(abs(v-w) for actual,pred in zip(state['positions'],affine['positions']) for pa,pb in zip(actual,pred) for v,w in zip(pa,pb)))
    score,actual,groups,rows=evaluate(alpha)
    score_error=abs(score-trial['score'])/max(1,trial['score'])
    max_state_error=max(max_state_error,state_error);max_score_error=max(max_score_error,score_error)
    linear=[v+alpha*dv for v,dv in zip(a0,ada)]
    remainder=sub(actual,linear)
    geometry=[0.]*size;interaction=[0.]*size
    grouped={name:{'geometry':[0.]*size,'interaction':[0.]*size} for name in ['length','wood','portal']}
    details=[];switches=[];portal_changes=[]
    linear_other_score=quadratic_score=exact_other_score=0
    for k,t in enumerate(terms):
        C0,J0,witness0=rows0[k];C,J,witness=rows[k];hj,dl=derivatives[k];ids=sorted(set(J0)|set(J)|set(hj))
        geometric={i:t['lambda']*(J.get(i,0)-J0.get(i,0)-alpha*hj.get(i,0)) for i in ids}
        force_geometry={i:alpha*dl*(J.get(i,0)-J0.get(i,0)) for i in ids}
        for i in ids:
            geometry[i]+=geometric[i];interaction[i]+=force_geometry[i]
            grouped[group(t)]['geometry'][i]+=geometric[i];grouped[group(t)]['interaction'][i]+=force_geometry[i]
        Cdot=sum(v*direction['x'][i] for i,v in J0.items());dual=t['lambda']+alpha*dl
        if t['contact']:
            s=-t['lambda'];ds=-dl;v=t['v'];dv=direction['v'][k]
            h0=C0+eps*s-v;hd=Cdot+eps*ds-dv;h=C+eps*(s+alpha*ds)-(v+alpha*dv)
            comp0=s*v;compd=ds*v+s*dv;compq=alpha*alpha*ds*dv
            comp=(s+alpha*ds)*(v+alpha*dv)
            assert abs(comp-(comp0+alpha*compd+compq))<=1e-24+1e-14*abs(comp)
            comp_scale=t['initialS']*t['scale']
            linear_other_score+=((h0+alpha*hd)/t['scale'])**2+((comp0+alpha*compd)/comp_scale)**2
            quadratic_score+=((h0+alpha*hd)/t['scale'])**2+((comp0+alpha*compd+compq)/comp_scale)**2
            exact_other_score+=(h/t['scale'])**2+(comp/comp_scale)**2
        else:
            b0=C0-eps*t['lambda'];bd=Cdot-eps*dl;b=C-eps*dual
            linear_other_score+=((b0+alpha*bd)/t['scale'])**2
            quadratic_score+=((b0+alpha*bd)/t['scale'])**2;exact_other_score+=(b/t['scale'])**2
        if group(t)=='wood':
            hit=native_by[(sample,t['key'])];orig_hit=native_by[(-1,t['key'])]
            rope=checkpoint['ropes'][int(t['key'].split(':')[1])]
            max_C_error=max(max_C_error,abs(C-(hit['distance']-rope['radius']-.0001)))
            max_J_error=max(max_J_error,max(abs(J.get(i,0)-g) for i,g in zip(hit['variables'],hit['gradient'])))
            changed=(hit['candidate'],hit['decisions'])!=(orig_hit['candidate'],orig_hit['decisions'])
            if changed:switches.append({'key':t['key'],'before':[orig_hit['candidate'],orig_hit['decisions']],'after':[hit['candidate'],hit['decisions']]})
        else:changed=False
        if group(t)=='portal':
            r=int(t['key'].split(':')[1]);identifier=':'.join(t['key'].split(':')[2:-1])
            before=origin['state']['crossings'][r][identifier];after=state['crossings'][r][identifier]
            if before['segment']!=after['segment']:portal_changes.append({'key':t['key'],'before':before,'after':after})
        combined={i:geometric[i]+force_geometry[i] for i in ids}
        details.append({'key':t['key'],'group':group(t),'nativeBranchChanged':changed,'variables':ids,'geometryRemainder':[geometric[i] for i in ids],'forceGeometryRemainder':[force_geometry[i] for i in ids],
            'scaledGeometryL2':l2([geometric[i]/scale_a[i] for i in ids]),'scaledForceGeometryL2':l2([force_geometry[i]/scale_a[i] for i in ids]),'scaledCombinedL2':l2([combined[i]/scale_a[i] for i in ids])})
    reconstructed=add(geometry,interaction)
    error=l2(scaled(sub(remainder,reconstructed)))/max(1,l2(scaled(remainder)))
    max_reconstruction=max(max_reconstruction,error)
    sr=scaled(remainder);den=sum(v*v for v in sr)
    def describe(v):return {'rawL2':l2(v),'scaledL2':l2(scaled(v)),'projectionOnTotalRemainder':dot(scaled(v),sr)/den if den else 0}
    actual_a_score=sum(v*v for v in scaled(actual));linear_a_score=sum(v*v for v in scaled(linear))
    trials.append({'sample':sample,'alpha':alpha,'nativeRecordedScore':trial['score'],'independentScore':score,'scoreRelativeError':score_error,'stateUpdateMaxError':state_error,
        'initialStationarityScore':initial_stationarity_score,'linearResidualScore':linear_a_score+linear_other_score,'linearPlusExactComplementarityQuadraticScore':linear_a_score+quadratic_score,
        'actualStationarityScore':actual_a_score,'actualOtherResidualScore':exact_other_score,'linearStationarityScore':linear_a_score,
        'remainder':describe(remainder),'geometricRemainder':describe(geometry),'forceGeometryRemainder':describe(interaction),'reconstructionNormalizedError':error,
        'grouped':{name:{part:describe(vec) for part,vec in entry.items()} for name,entry in grouped.items()},
        'nativeWoodBranchChanges':switches,'portalMaterialSegmentChanges':portal_changes,
        'topContributors':sorted(details,key=lambda r:r['scaledCombinedL2'],reverse=True)[:12],'features':details,
        'stationarityVectors':{'actual':actual,'linear':linear,'geometricRemainder':geometry,'forceGeometryRemainder':interaction}})
checks={'scoreMaxRelativeError':max_score_error,'stateUpdateMaxError':max_state_error,'nativeWoodCMaxError':max_C_error,'nativeWoodJMaxError':max_J_error,'remainderMaxNormalizedReconstructionError':max_reconstruction}
passed=max_score_error<=1e-8 and max_state_error<=1e-12 and max_C_error<=1e-12 and max_J_error<=1e-10 and max_reconstruction<=1e-8
result={'scope':'read-only retained late direction finite-step residual remainder, no new solve/step/acceptance','checksPassed':passed,'checks':checks,'originalIteration':15,'fixedRows':len(terms),'initialScore':score0,'initialStationarityScore':initial_stationarity_score,'trials':trials}
(workroot/'result.json').write_text(json.dumps(result,indent=2)+'\n')
print(json.dumps({**{k:v for k,v in result.items() if k!='trials'},'trials':[{k:v for k,v in t.items() if k not in ['features','stationarityVectors']} for t in trials]},indent=2))
raise SystemExit(0 if passed else 1)
