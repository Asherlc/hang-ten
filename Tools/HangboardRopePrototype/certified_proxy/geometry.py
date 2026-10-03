"""Exact-rational local height-graph replacements; original vertices retained."""
from fractions import Fraction as F

LIMIT=F(1,100000)


def orient(a,b,c):
    return (b[0]-a[0])*(c[1]-a[1])-(b[1]-a[1])*(c[0]-a[0])


def normal(a,b,c):
    u=[b[i]-a[i] for i in range(3)];v=[c[i]-a[i] for i in range(3)]
    return (u[1]*v[2]-u[2]*v[1],u[2]*v[0]-u[0]*v[2],u[0]*v[1]-u[1]*v[0])


def proposal(vertices,faces,errors,center,ids):
    if len(ids)<3:return None
    boundary={}
    for i in ids:
        t=faces[i]
        if center not in t:return None
        j=t.index(center);a,b=t[(j+1)%3],t[(j+2)%3]
        if a in boundary:return None
        boundary[a]=b
    if set(boundary)!=set(boundary.values()):return None
    first=min(boundary);loop=[first];current=boundary[first]
    while current!=first:
        if current in loop or current not in boundary:return None
        loop.append(current);current=boundary[current]
    if len(loop)!=len(ids):return None
    anchor_face=max(ids,key=lambda i:sum(x*x for x in normal(*[vertices[j] for j in faces[i]])))
    a,b,c=[vertices[j] for j in faces[anchor_face]];n=normal(a,b,c)
    axis=max(range(3),key=lambda i:abs(n[i]))
    if n[axis]==0:return None
    projected=[i for i in range(3) if i!=axis]
    xy={i:tuple(vertices[i][k] for k in projected) for i in [center,*loop]}
    sign=1 if n[axis]>0 else -1
    # Dropping Y reverses the cross-product orientation.
    if axis==1:sign = -sign
    for i in ids:
        if sign*orient(*[xy[j] for j in faces[i]])<=0:return None
    # Exact convex polygon and an interior center. These imply the old fan
    # covers the polygon once, with no gaps, folds or holes.
    for j,start in enumerate(loop):
        end=loop[(j+1)%len(loop)]
        if sign*orient(xy[start],xy[end],xy[center])<=0:return None
        if any(sign*orient(xy[start],xy[end],xy[k])<0 for k in loop):return None
    replacement=None
    for anchor in sorted(loop):
        k=loop.index(anchor);order=loop[k:]+loop[:k]
        candidate=[(order[0],order[j],order[j+1]) for j in range(1,len(order)-1)]
        if all(sign*orient(*[xy[k] for k in tri])>0 for tri in candidate):
            replacement=candidate;break
    if replacement is None:return None
    residuals=[]
    for i in [center,*loop]:
        p=vertices[i]
        plane=a[axis]-sum(n[k]*(p[k]-a[k]) for k in projected)/n[axis]
        residuals.append(p[axis]-plane)
    local=max(residuals)-min(residuals)
    inherited=max(errors[i] for i in ids);bound=inherited+local
    if bound>LIMIT:return None
    return {'center':center,'oldFaces':list(ids),'boundary':loop,'planeFace':anchor_face,'axis':axis,
        'localBound':[local.numerator,local.denominator],
        'inheritedBound':[inherited.numerator,inherited.denominator],
        'bound':[bound.numerator,bound.denominator],'triangles':[list(t) for t in replacement]}


def fixtures():
    vertices=[tuple(map(F,p)) for p in [(0,0,F(1,1000000)),(-1,-1,0),(1,-1,0),(1,1,0),(-1,1,0)]]
    faces={i:t for i,t in enumerate([(0,1,2),(0,2,3),(0,3,4),(0,4,1)])};errors={i:F(0) for i in faces}
    p=proposal(vertices,faces,errors,0,list(faces))
    assert p is not None and len(p['triangles'])==2 and F(*p['bound'])<=LIMIT,'shallow curved fan must certify'
    high=list(vertices);high[0]=(F(0),F(0),F(1,100))
    assert proposal(high,faces,errors,0,list(faces)) is None,'high curvature must reject'
    reversed_faces=dict(faces);reversed_faces[1]=tuple(reversed(reversed_faces[1]))
    assert proposal(vertices,reversed_faces,errors,0,list(faces)) is None,'winding must reject'
    nonconvex=[tuple(map(F,p)) for p in [(0,0,F(1,1000000)),(-1,-1,0),(1,-1,0),(F(7,10),0,0),(1,1,0),(-1,1,0)]]
    nonconvex_faces={i:(0,i+1,(i+1)%5+1) for i in range(5)}
    assert proposal(nonconvex,nonconvex_faces,{i:F(0) for i in nonconvex_faces},0,list(nonconvex_faces)) is None,'nonconvex graph must reject'
    inherited={i:LIMIT for i in faces}
    assert proposal(vertices,faces,inherited,0,list(faces)) is None,'inherited error must count'
    print('PASS exact graph replacement fixtures')
