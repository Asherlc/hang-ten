"""Manual surface authoring for Batch 05. No image processing/tracing is used.

All constructor inputs are millimetres in a right-handed X-right/Z-up/-Y-front
frame. Cavities are real interior surfaces connected to the exterior. Contact
objects are disjoint face partitions of the assembled solid, not highlight shells.
"""
from __future__ import annotations
from dataclasses import dataclass
from typing import Callable, Iterable
import math
import numpy as np
import shapely
from shapely.geometry import Polygon, Point
from shapely.geometry.polygon import orient
import trimesh


def smooth(a: float,b: float,x: float) -> float:
    if isinstance(x,np.ndarray):
        t=np.clip((x-a)/(b-a),0,1)
    else:t=max(0.,min(1.,(x-a)/(b-a)))
    return t*t*(3-2*t)


def band(x: float,a: float,b: float,r: float=2) -> float:
    return smooth(a-r,a+r,x)*(1-smooth(b-r,b+r,x))


def densify(points,step=3.0):
    """Subdivide already-authored straight segments; does not inspect images."""
    p=np.asarray(points,float); out=[]
    for a,b in zip(p,np.roll(p,-1,axis=0)):
        n=max(1,int(np.ceil(np.linalg.norm(b-a)/step)))
        out.extend(a+(b-a)*j/n for j in range(n))
    return np.array(out)


def rounded_outline(points,radii,step=3.0):
    """Explicit quadratic corner transitions on a hand-authored control polygon.

    Each radius is a deliberate local tangent distance, not a global bevel.
    """
    p=np.asarray(points,float); out=[]
    for j,v in enumerate(p):
        prev=p[j-1]; nxt=p[(j+1)%len(p)]
        r=min(float(radii[j]),.45*np.linalg.norm(prev-v),.45*np.linalg.norm(nxt-v))
        a=v+(prev-v)/np.linalg.norm(prev-v)*r
        b=v+(nxt-v)/np.linalg.norm(nxt-v)*r
        n=max(3,int(np.ceil(r/1.4)))
        for t in np.linspace(0,1,n,endpoint=False):
            out.append((1-t)**2*a+2*t*(1-t)*v+t*t*b)
        out.append(b)
    poly=orient(Polygon(densify(out,step)),sign=1)
    assert poly.is_valid, shapely.is_valid_reason(poly)
    return np.asarray(poly.exterior.coords[:-1])


def roundrect(cx,cz,w,h,r,step=2.5):
    assert w>2*r and h>=2*r-1e-8,(w,h,r)
    pts=[]
    for ax,az,start in [(cx+w/2-r,cz+h/2-r,0),(cx-w/2+r,cz+h/2-r,90),
                       (cx-w/2+r,cz-h/2+r,180),(cx+w/2-r,cz-h/2+r,270)]:
        # traverse top-right -> top-left -> bottom-left -> bottom-right CCW
        for ang in np.linspace(start,start+90,9):
            a=np.deg2rad(ang);pts.append([ax+r*np.cos(a),az+r*np.sin(a)])
    # The arc construction begins on the right vertical tangent and is CCW.
    poly=orient(Polygon(pts),sign=1)
    return densify(np.asarray(poly.exterior.coords[:-1]),step)


def ellipse(cx,cz,rx,rz=None,n=36):
    rz=rx if rz is None else rz
    a=np.linspace(0,2*np.pi,n,endpoint=False)
    return np.c_[cx+rx*np.cos(a),cz+rz*np.sin(a)]


def triangulate(poly: Polygon,max_edge: float|None=None,height_func=None):
    """Constrained triangulation preserving all boundary vertices.

    Optional conforming longest-edge refinement changes only long interior
    edges. Input boundaries are explicitly sampled <= 3 mm before this call.
    """
    if poly.is_empty:return np.zeros((0,2)),np.zeros((0,3),int)
    assert poly.is_valid,shapely.is_valid_reason(poly)
    result=shapely.constrained_delaunay_triangles(poly)
    vv=[];ff=[]; ids={}
    def vertex(p):
        k=tuple(np.round(p,9))
        if k not in ids:ids[k]=len(vv);vv.append(np.array(p,float))
        return ids[k]
    for t in result.geoms:
        coords=list(t.exterior.coords)[:3]
        f=[vertex(p) for p in coords]
        a,b,c=[vv[j] for j in f]
        if (b[0]-a[0])*(c[1]-a[1])-(b[1]-a[1])*(c[0]-a[0])<0:f=[f[0],f[2],f[1]]
        ff.append(f)
    v=np.array(vv);f=np.array(ff,int)
    if max_edge is None:return v,f
    def split_edges(v,f,chosen):
        mids={tuple(e):len(v)+i for i,e in enumerate(chosen)}
        v=np.vstack((v,(v[chosen[:,0]]+v[chosen[:,1]])/2))
        out=[]
        for a,b,c in f:
            m=mids.get(tuple(sorted((a,b))));n=mids.get(tuple(sorted((b,c))));p=mids.get(tuple(sorted((c,a))))
            mask=(m is not None)+2*(n is not None)+4*(p is not None)
            if mask==0:out.append([a,b,c])
            elif mask==1:out.extend([[a,m,c],[m,b,c]])
            elif mask==2:out.extend([[a,b,n],[a,n,c]])
            elif mask==4:out.extend([[a,b,p],[b,c,p]])
            elif mask==3:out.extend([[a,m,c],[m,n,c],[m,b,n]])
            elif mask==5:out.extend([[a,m,p],[m,b,c],[m,c,p]])
            elif mask==6:out.extend([[a,b,n],[a,n,p],[p,n,c]])
            else:out.extend([[a,m,p],[m,b,n],[p,n,c],[m,n,p]])
        return v,np.asarray(out,int)
    # Boundary vertices survive unchanged: connected cavity/outer rings share them.
    for iteration in range(13):
        ee=np.sort(np.vstack((f[:,[0,1]],f[:,[1,2]],f[:,[2,0]])),axis=1)
        ue,ct=np.unique(ee,axis=0,return_counts=True)
        lengths=np.linalg.norm(v[ue[:,0]]-v[ue[:,1]],axis=1)
        chosen=ue[(lengths>max_edge)&(ct==2)]
        if len(chosen)==0:break
        v,f=split_edges(v,f,chosen)
    # Resolve actual authored relief, not just its vertex-normal approximation.
    # Local error refinement avoids uniformly increasing every flat surface.
    if height_func is not None:
        vectorized=None
        def evaluate(points):
            nonlocal vectorized
            if vectorized is not False:
                try:
                    vals=np.broadcast_to(np.asarray(height_func(points[:,0],points[:,1]),float),(len(points),))
                    vectorized=True
                    return vals
                except (TypeError,ValueError):vectorized=False
            return np.array([height_func(x,z) for x,z in points])
        for iteration in range(8):
            ee=np.sort(np.vstack((f[:,[0,1]],f[:,[1,2]],f[:,[2,0]])),axis=1)
            ue,ct=np.unique(ee,axis=0,return_counts=True)
            candidates=ue[ct==2]
            values=evaluate(v)
            pa=v[candidates[:,0]];pb=v[candidates[:,1]]
            va=values[candidates[:,0]];vb=values[candidates[:,1]]
            error=np.zeros(len(candidates))
            for t in (.25,.5,.75):
                q=pa*(1-t)+pb*t
                actual=evaluate(q)
                error=np.maximum(error,np.abs(actual-(va*(1-t)+vb*t)))
            chosen=candidates[error>.070]
            if len(chosen)==0:break
            v,f=split_edges(v,f,chosen)

    return v,f


class Assembly:
    def __init__(self,slug):
        self.slug=slug; self.v=[];self.f=[];self.labels=[];self._ids={};self.probes=[]
        self.holds={};self.units=[];self.mounts=[];self.normal_fields={}
    def vertex(self,p):
        k=tuple(np.round(p,7))
        if k not in self._ids:self._ids[k]=len(self.v);self.v.append(np.asarray(p,float))
        return self._ids[k]
    def tri(self,pts,label):
        inds=[self.vertex(p) for p in pts]
        if len(set(inds))<3:raise ValueError('Degenerate authoring triangle')
        self.f.append(inds);self.labels.append(label)
    def mesh(self):
        m=trimesh.Trimesh(vertices=np.array(self.v)/1000,faces=np.array(self.f),process=False)
        trimesh.repair.fix_normals(m,multibody=True)
        self.f=m.faces.tolist()
        # Use the derivative of the authored surface field, not skinny-triangle
        # interpolation, on front/back graph surfaces. Curved cavity/loft walls
        # retain their assembled geometric normals. This changes shading only;
        # the explicit tessellated geometry is independently validated.
        normals=m.vertex_normals.copy()
        for index,normal in self.normal_fields.items():
            n=np.asarray(normal,float); n/=np.linalg.norm(n)
            if np.dot(n,normals[index])<0:n=-n
            normals[index]=n
        m.vertex_normals=normals
        return m
    def faces_for(self,name):return np.flatnonzero(np.array(self.labels)==name)
    def duplicate_faces(self):
        f=np.sort(np.asarray(self.f),axis=1)
        return len(f)-len(np.unique(f,axis=0))
    def hold(self,ident,description,refs,**extra):
        if ident in self.holds:raise ValueError(f'duplicate physical contact {ident}')
        self.holds[ident]={'holdId':ident,'nodeName':'hold--'+ident,'description':description,'evidenceReferences':refs,**extra}


class Unit:
    def __init__(self,assembly:Assembly,name:str,outline,thickness:Callable,*,offset=0,mirror=False,
                 top_profile=None,edge_label=None,front_label=None,front_resolution=5):
        self.a=assembly;self.name=name;self.outline=np.asarray(outline,float);self.thickness=thickness
        self.offset=float(offset);self.sign=-1 if mirror else 1
        self.top_profile=top_profile or (lambda x,z,t:0)
        self.edge_label=edge_label or (lambda x,z,t:'body')
        self.front_label=front_label or (lambda x,z:'body')
        self.front_resolution=front_resolution
        self.mouths=[];self.backholes=[]
        self.a.units.append({'unitId':name,'mirrorApplied':mirror,'sourceOffsetMm':offset})
    def point(self,x,y,z):return [self.offset+self.sign*x,y,z]
    def tri(self,pts,label):
        if label=='body':label='body--'+self.name
        self.a.tri([self.point(*p) for p in pts],label)
    def fill(self,poly,yfunc,label='body',refine=None):
        v,f=triangulate(poly,refine,height_func=yfunc if refine is not None else None)
        eps=.001
        try:
            def evaluate(x,z):return np.broadcast_to(np.asarray(yfunc(x,z),float),x.shape)
            x=v[:,0];z=v[:,1]
            yy=evaluate(x,z)
            dx=(evaluate(x+eps,z)-evaluate(x-eps,z))/(2*eps)
            dz=(evaluate(x,z+eps)-evaluate(x,z-eps))/(2*eps)
        except (TypeError,ValueError):
            yy=np.array([yfunc(x,z) for x,z in v])
            dx=np.array([(yfunc(x+eps,z)-yfunc(x-eps,z))/(2*eps) for x,z in v])
            dz=np.array([(yfunc(x,z+eps)-yfunc(x,z-eps))/(2*eps) for x,z in v])
        inds=[]
        for i,(x,z) in enumerate(v):
            index=self.a.vertex(self.point(x,yy[i],z));inds.append(index)
            self.a.normal_fields[index]=[self.sign*dx[i],-1,dz[i]]
        faces=np.asarray(inds,dtype=np.int64)[f]
        assert np.all(faces[:,0]!=faces[:,1]) and np.all(faces[:,1]!=faces[:,2]) and np.all(faces[:,2]!=faces[:,0])
        if callable(label):
            centers=v[f].mean(axis=1)
            tags=[label(float(x),float(z)) for x,z in centers]
        else:tags=[label]*len(f)
        self.a.f.extend(faces.tolist())
        self.a.labels.extend('body--'+self.name if tag=='body' else tag for tag in tags)
    def link(self,first,second,label):
        assert len(first)==len(second)
        n=len(first)
        for j in range(n):
            k=(j+1)%n
            for ids in [(0,j,0,k,1,k),(0,j,1,k,1,j)]:
                rings=[first,second];pts=[rings[ids[q]][ids[q+1]] for q in (0,2,4)]
                center=np.mean(pts,axis=0)
                tag=label(*center) if callable(label) else label
                self.tri(pts,tag)
    def hole(self,h,yfunc,record=True):
        cx,cz=h['center'];r=h['radius'];rz=h.get('radiusZ',r)
        loop=ellipse(cx,cz,r,rz,48)
        front=np.array([[x,yfunc(x,z),z] for x,z in loop]);back=np.c_[loop[:,0],np.zeros(len(loop)),loop[:,1]]
        self.link(front,back,'body');self.backholes.append(loop)
        if record:self.a.mounts.append({'unitId':self.name,'kind':h.get('kind','mounting-opening-not-hold'),'centerSourceMeters':(np.array(self.point(cx,0,cz))/1000).tolist(),'axis':[0,1,0],'radiusMm':r,'radiusZMm':rz,'placementClassification':'photo-derived-estimate'})
        return loop
    def front_hole(self,h):
        loop=self.hole(h,lambda x,z:-self.thickness(x,z));self.mouths.append(loop)
    def cavity(self,c:dict,through=None,*,base_y=None,register=True):
        """Routed/moulded recess with explicit mouth roll, walls and back radius.

        A stepped depth profile acts inside one continuous opening. Lower-half
        actual wall/floor faces are partitioned into physical contact IDs.
        """
        base_y=base_y or (lambda x,z:-self.thickness(x,z))
        cx,cz=c['center'];w=c['width'];h=c['height'];radius=c.get('radius',min(h/2-0.1,8))
        raw=roundrect(cx,cz,w,h,radius,step=c.get('sampling',2.4))
        slope=c.get('slope',0)
        dip=c.get('dip')
        def warp(q):
            x,z=q
            if dip and z<cz:
                z-=dip['amount']*band(x,dip['x0'],dip['x1'],dip.get('blend',2.5))*min(1,(cz-z)/(h*.3))
            return np.array([x,z+slope*(x-cx)])
        mouth=np.array([warp(q) for q in raw])
        if register:self.mouths.append(mouth)
        depth=c['depth']
        def dep(x):
            if isinstance(depth,(float,int)):return float(depth)
            if depth['kind']=='linear':return float(np.interp(x,depth['x'],depth['values']))
            vals=depth['values'];cuts=depth['cuts'];val=float(vals[0])
            for k,cut in enumerate(cuts):val+=(vals[k+1]-vals[k])*smooth(cut-depth.get('blend',.9),cut+depth.get('blend',.9),x)
            return val
        holds=c['holds']
        def who(x):
            if len(holds)==1:return holds[0]['id']
            for hold in holds:
                a,b=hold['xRange']
                if a-1e-6<=x<=b+1e-6:return hold['id']
            return min(holds,key=lambda a:abs(x-np.mean(a['xRange'])))['id']
        # Lip radius is a measured unknown, locally authored, and smaller for tiny edges.
        minD=min(dep(x) for x in (cx-w/2,cx,cx+w/2))
        rr=min(c.get('lipRadius',2.0),minD*.2,h*.12)
        levels=[('front',0,0)]
        for theta in np.linspace(np.pi/8,np.pi/2,4):levels.append(('front',rr*np.sin(theta),rr*(1-np.cos(theta))))
        levels.append(('rear',rr,rr))
        for theta in np.linspace(np.pi/8,np.pi/2,4):levels.append(('rear',rr+rr*(1-np.cos(theta)),rr*(1-np.sin(theta))))
        rings=[]
        angle=math.radians(c.get('floorAngleEstimateDeg',0))
        for typ,inset,d in levels:
            pts=[]
            for rawp in raw:
                x0,z0=rawp
                q=np.array([cx+(x0-cx)*(1-2*inset/w),cz+(z0-cz)*(1-2*inset/h)])
                x,z=warp(q)
                D=dep(x);advance=d if typ=='front' else D-d
                z+=advance*math.tan(angle)
                pts.append([x,base_y(x,z)+advance,z])
            rings.append(np.array(pts))
        # End rings must match the separately triangulated back wall exactly.
        for ringA,ringB in zip(rings,rings[1:]):
            # Fixed parametric strip boundaries avoid a jagged face-centroid
            # selection seam as drafted or inclined walls change orientation.
            for j in range(len(raw)):
                k=(j+1)%len(raw)
                midpoint=(raw[j]+raw[k])/2
                tag=who(midpoint[0]) if midpoint[1]<=cz else 'body'
                self.tri([ringA[j],ringA[k],ringB[k]],tag)
                self.tri([ringA[j],ringB[k],ringB[j]],tag)
        last=rings[-1];inner=last[:,[0,2]]
        def end_y(x,z):return base_y(x,z)+dep(x)
        # Linear interpolation at boundary is used only to eliminate float drift.
        ylookup={tuple(np.round(p[[0,2]],8)):p[1] for p in last}
        def cap_y(x,z):return ylookup.get(tuple(np.round([x,z],8)),end_y(x,z))
        holes=[]
        for hole in (through or []):
            loop=self.hole(hole,cap_y)
            assert Polygon(inner).contains(Polygon(loop)),('mount hole outside cavity',self.name,c,hole)
            holes.append(loop)
        for child in c.get('nestedCavities',[]):
            child_mouth=self.cavity(child,base_y=cap_y,register=False)
            assert Polygon(inner).contains(Polygon(child_mouth)),('nested mouth outside parent',self.name,c,child)
            holes.append(child_mouth)
        self.fill(Polygon(inner,holes),cap_y,'body',refine=5 if not isinstance(depth,(int,float)) else None)
        px=cx;pz=cz+slope*(px-cx)+dep(px)*math.tan(angle)
        self.a.probes.append({'unitId':self.name,'cavityCenterSourceMeters':(np.array(self.point(px,base_y(px,pz),pz))/1000).tolist(),'targetDepthMm':dep(px),'actualDepthMm':end_y(px,pz)-base_y(px,pz),'holdIds':[k['id'] for k in holds],'openingIsRealRecess':True,'nestedBackWallPocket':not register})
        return mouth
    def boss(self,center,width,height,radius,projection,hold_id):
        cx,cz=center;raw=roundrect(cx,cz,width,height,radius)
        self.mouths.append(raw);rings=[]
        for t,inset in [(0,0),(.15,.15),(.5,1),(.85,2.1),(1,3)]:
            q=raw.copy();q[:,0]=cx+(q[:,0]-cx)*(1-2*inset/width);q[:,1]=cz+(q[:,1]-cz)*(1-2*inset/height)
            rings.append(np.array([[x,-self.thickness(x,z)-t*projection,z] for x,z in q]))
        for a,b in zip(rings,rings[1:]):self.link(a,b,lambda x,y,z:hold_id if z>cz else 'body')
        last=rings[-1];self.fill(Polygon(last[:,[0,2]]),lambda x,z:-self.thickness(x,z)-projection,'body')
    def finish(self):
        outer=Polygon(self.outline)
        for i,mouth in enumerate(self.mouths):
            assert outer.contains(Polygon(mouth)),(self.name,'mouth outside outline',i)
        # Explicitly reject intersecting cavity mouths (nested contacts belong inside one cavity).
        for i,a in enumerate(self.mouths):
            for b in self.mouths[i+1:]:assert not Polygon(a).intersects(Polygon(b)),(self.name,'overlapping mouths')
        front=Polygon(self.outline,self.mouths)
        self.fill(front,lambda x,z:-self.thickness(x,z),self.front_label,self.front_resolution)
        rings=[]
        for t in [0,.035,.08,.16,.28,.42,.58,.73,.86,.95,1]:
            pts=[]
            for x,z in self.outline:
                z2=z+self.top_profile(x,z,t)
                pts.append([x,-self.thickness(x,z)*(1-t),z2])
            rings.append(np.array(pts))
        for k,(a,b) in enumerate(zip(rings,rings[1:])):
            t=([0,.035,.08,.16,.28,.42,.58,.73,.86,.95,1][k]+[0,.035,.08,.16,.28,.42,.58,.73,.86,.95,1][k+1])/2
            self.link(a,b,lambda x,y,z:self.edge_label(x,z,t))
        self.fill(Polygon(rings[-1][:,[0,2]],self.backholes),lambda x,z:0,'body')
