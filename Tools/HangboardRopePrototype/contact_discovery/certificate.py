import math

def reference_certificate(d,checkpoint):
    ref=d['reference'];x=ref['particles'];height=ref['height'];lam=ref['rowMultipliers'];eps=d['regularization']
    assert all(not p['attachments'] for p in checkpoint['ropes'])
    stat=[[[0.0]*3 for p in rope] for rope in x];board=d['boardMass']*(height+d['boardHeight']-d['predictionHeight'])
    for ri,rope in enumerate(x):
     for i,v in enumerate(rope):
      if not d['weights'][ri][i]:continue
      for axis in range(3):stat[ri][i][axis]=(v[axis]+d['positions'][ri][i][axis]-d['prediction'][ri][i][axis])/d['weights'][ri][i]
     for i,tension in enumerate(d['distanceTension'][ri]):
      if tension<=0:continue
      delta=[b-a for a,b in zip(d['positions'][ri][i],d['positions'][ri][i+1])];length=math.sqrt(sum(t*t for t in delta));t=[v/length for v in delta]
      dx=[b-a for a,b in zip(x[ri][i],x[ri][i+1])];projection=sum(a*b for a,b in zip(dx,t))
      force=[tension/length*(a-projection*b) for a,b in zip(dx,t)]
      for particle,sign in [(i,-1),(i+1,1)]:
       if d['weights'][ri][particle]:
        for axis in range(3):stat[ri][particle][axis]+=sign*force[axis]
    q=[]
    for row,mult in zip(d['rows'],lam):
     value=row['residual']+row['boardGradient']*height;board+=row['boardGradient']*mult
     for k,(particle,g) in enumerate(zip(row['particles'],row['gradients'])):
      ri=row['secondRope'] if k>=2 and row['secondRope']>=0 else row['rope'];value+=sum(a*b for a,b in zip(g,x[ri][particle]))
      if d['weights'][ri][particle]:
       for axis in range(3):stat[ri][particle][axis]+=g[axis]*mult
     q.append(value)
    eq=[(v,m) for row,v,m in zip(d['rows'],q,lam) if not row['contact']];con=[(v,m) for row,v,m in zip(d['rows'],q,lam) if row['contact']]
    checks={'stationarity':max([abs(board)]+[abs(v) for rope in stat for p in rope for v in p]),'regularizedEquality':max(abs(v-eps*m) for v,m in eq),'equality':max(abs(v) for v,m in eq),'minContactQ':min(v for v,m in con),'minRegularizedGap':min(v-eps*m for v,m in con),'positiveContactMultiplier':max(0,max(m for v,m in con)),'complementarity':max(abs(m*(v-eps*m)) for v,m in con)}
    passed=checks['stationarity']<=1e-10 and checks['regularizedEquality']<=1e-8 and checks['equality']<=1e-8 and checks['minContactQ']>=-1e-8 and checks['minRegularizedGap']>=-1e-10 and checks['positiveContactMultiplier']==0 and checks['complementarity']<=1e-14
    return {"checks":checks,"passed":passed}
