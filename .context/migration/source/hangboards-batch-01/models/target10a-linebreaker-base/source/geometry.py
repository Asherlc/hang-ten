"""Explicitly authored implicit solids in millimetres; no image data enters this module.
Author a physical body profile and subtract real pocket volumes. Mesh once, simplify the
ASSEMBLED watertight surface, then partition faces, so selectable objects never overlap.
"""
import numpy as np
import trimesh
from skimage.measure import marching_cubes
import vtk
from vtk.util.numpy_support import numpy_to_vtk, numpy_to_vtkIdTypeArray, vtk_to_numpy


def smax(a,b,k=0.):
    if k<=0: return np.maximum(a,b)
    h=np.maximum(k-np.abs(a-b),0.)/k
    return np.maximum(a,b)+h*h*k*.25


def rrect(x,z,cx,cz,w,h,r):
    qx=np.abs(x-cx)-(w*.5-r); qz=np.abs(z-cz)-(h*.5-r)
    return np.sqrt(np.maximum(qx,0.)**2+np.maximum(qz,0.)**2)+np.minimum(np.maximum(qx,qz),0.)-r


def polygon_sdf(u,v,poly):
    """Signed distance to a manually authored 2D polygon. Negative is interior."""
    shape=np.broadcast_shapes(np.shape(u),np.shape(v))
    d=np.full(shape,np.inf,dtype=np.float32); inside=np.zeros(shape,bool)
    p=np.asarray(poly,float)
    for a,b in zip(p,np.roll(p,-1,axis=0)):
        ex,ey=b-a; wx=u-a[0]; wy=v-a[1]
        t=np.clip((wx*ex+wy*ey)/(ex*ex+ey*ey),0,1)
        d=np.minimum(d,(wx-t*ex)**2+(wy-t*ey)**2)
        crossed=((a[1]>v)!=(b[1]>v)) & (u < (ex*(v-a[1])/(ey if abs(ey)>1e-15 else 1e-15)+a[0]))
        inside^=crossed
    return np.sqrt(d)*np.where(inside,-1.,1.)


def body_field(x,y,z,cfg):
    w,h,t=cfg['dimensionsMm']
    # Distinct authored longitudinal profile, not a shared slab for every board.
    if cfg.get('profileYZ'):
        yz=polygon_sdf(y,z,cfg['profileYZ'])
        body=smax(yz,np.abs(x)-w/2,cfg.get('endRoundMm',3.))
    else:
        front=t
        body=smax(rrect(x,z,0,h/2,w,h,cfg.get('cornerRadiusMm',10)),np.abs(y+t/2)-t/2,cfg.get('rimRadiusMm',3.))
    # Additional source-observed frontal silhouette, including shoulders and waists.
    if cfg.get('outlineXZ'):
        outline=polygon_sdf(x,z,cfg['outlineXZ'])
        body=smax(body,outline,cfg.get('outlineRoundMm',2.))
    # Hand-authored relief cuts may be full-width step transitions or top sloper planes.
    for cut in cfg.get('bodyCuts',[]):
        if cut['kind']=='planePatch':
            x0,x1=cut['xRange']; z0,z1=cut.get('zRange',[-1000,1000])
            # void above plane z = intercept + slope*y within selected X interval
            plane=cut['intercept']+cut['slope']*y-z
            bounded=smax(smax(plane,np.maximum(x0-x,x-x1),cut.get('blend',3.)),np.maximum(z0-z,z-z1),0)
            body=smax(body,-bounded,cut.get('rim',2.))
        elif cut['kind']=='profileVoid':
            void=polygon_sdf(y,z,cut['profileYZ'])
            if 'xRange' in cut:
                a,b=cut['xRange']; void=smax(void,np.maximum(a-x,x-b),cut.get('blend',2.))
            body=smax(body,-void,cut.get('rim',2.))
    return body


def cavity_field(x,y,z,p):
    shape=rrect(x,z,p['x'],p['z'],p['width'],p['height'],p.get('radius',p['height']/2))
    # floor may slope upward/downward in depth, deliberately specified when evidenced.
    floor=p['floorY'] + p.get('floorSlopeZ',0.)*(z-p['z'])
    return smax(shape,y-floor,p.get('floorFillet',1.2))


def evaluate(x,y,z,cfg):
    field=body_field(x,y,z,cfg)
    for p in cfg.get('pockets',[]): field=smax(field,-cavity_field(x,y,z,p),p.get('lipRound',2.))
    for hole in cfg.get('mounts',[]):
        a=np.sqrt((x-hole['x'])**2+(z-hole['z'])**2)-hole.get('radius',2.5)
        field=np.maximum(field,-a)
        # A short counterbore only when visible. No external screw is authored.
        if hole.get('counterbore'):
            void=np.maximum(np.sqrt((x-hole['x'])**2+(z-hole['z'])**2)-hole['counterbore'],y-hole['counterboreFloorY'])
            field=smax(field,-void,.5)
    return field


def decimate(v,f,target):
    points=vtk.vtkPoints(); points.SetData(numpy_to_vtk(np.asarray(v,dtype=np.float64),deep=True))
    cells=vtk.vtkCellArray(); packed=np.column_stack((np.full(len(f),3),f)).astype(np.int64)
    cells.SetCells(len(f),numpy_to_vtkIdTypeArray(packed.ravel(),deep=True))
    poly=vtk.vtkPolyData(); poly.SetPoints(points); poly.SetPolys(cells)
    dec=vtk.vtkDecimatePro(); dec.SetInputData(poly); dec.SetTargetReduction(max(0,1-target/len(f)))
    dec.PreserveTopologyOn(); dec.SplittingOff(); dec.BoundaryVertexDeletionOff(); dec.SetMaximumError(.00001)
    dec.Update(); result=dec.GetOutput()
    return vtk_to_numpy(result.GetPoints().GetData()).copy(),vtk_to_numpy(result.GetPolys().GetData()).reshape(-1,4)[:,1:].copy()


def classify(mesh,cfg):
    c=mesh.triangles_center; x,y,z=c.T; labels=np.zeros(len(c),np.int32)
    # Authoring selectors are explicit physical contact extents, not inferred names/normals.
    ids=[]
    for surface in cfg.get('surfaceContacts',[]):
        ids.append(surface['id']); mask=np.ones(len(c),bool)
        for axis,key in enumerate(('xRange','yRange','zRange')):
            if key in surface:
                lo,hi=surface[key]; mask&=(c[:,axis]>=lo)&(c[:,axis]<=hi)
        if surface.get('topPlane'):
            intercept,slope=surface['topPlane']; mask&=np.abs(z-(intercept+slope*y))<surface.get('surfaceBand',5.)
        labels[mask]=len(ids)
    for p in cfg.get('pockets',[]):
        if not p.get('holdId'): continue
        ids.append(p['holdId'])
        radial=rrect(x,z,p['x'],p['z'],p['width'],p['height'],p.get('radius',p['height']/2))
        # Actual pocket walls/floor and a narrow integral lip; all are faces of the same solid.
        mask=(radial < p.get('lipSelectionMm',2.5)) & (y<p['floorY']+2) & (y<-.05)
        labels[mask]=len(ids)
    # Do not turn a mounting bore into a hold, even if a screw runs through a pocket floor.
    for hole in cfg.get('mounts',[]):
        radius=hole.get('counterbore',hole.get('radius',2.5))+.45
        radial=np.sqrt((x-hole['x'])**2+(z-hole['z'])**2)
        labels[radial<radius]=0
    assert len(ids)==len(set(ids)), 'Repeated logical contact identity'
    return labels,ids


def build(cfg):
    w,h,t=cfg['dimensionsMm']; pitch=cfg.get('voxelMm',.85)
    axes=[np.arange(-w/2-3,w/2+3+pitch,pitch,dtype=np.float32),
          np.arange(-t-3,3+pitch,pitch,dtype=np.float32),
          np.arange(-3,h+3+pitch,pitch,dtype=np.float32)]
    # Chunk X to keep memory bounded during independent implicit primitives.
    vol=np.empty(tuple(len(a) for a in axes),np.float32)
    for i in range(0,len(axes[0]),40):
        vol[i:i+40]=evaluate(axes[0][i:i+40,None,None],axes[1][None,:,None],axes[2][None,None,:],cfg)
    assert np.isfinite(vol).all() and vol.min()<0 and vol.max()>0
    v,f,_,_=marching_cubes(vol,level=0,spacing=(pitch,pitch,pitch),allow_degenerate=False)
    v+=np.array([a[0] for a in axes]); rawcount=len(f)
    v,f=decimate(v,f,cfg.get('targetTriangles',42000))
    mesh=trimesh.Trimesh(vertices=v,faces=f,process=True)
    if mesh.volume<0: mesh.invert()
    mesh.fix_normals()
    # Meshing can miss the extremum by < one voxel. Record, don't stretch coordinates.
    labels,ids=classify(mesh,cfg)
    # Centroid selectors can leave a one-triangle island at a curved patch boundary.
    # Reassign only tiny isolated label fragments to nonselectable body; do not alter
    # the physical mesh or hide a meaningful disconnected contact component.
    partition_cleanup=[]
    adjacency=mesh.face_adjacency
    for index,hold_id in enumerate(ids,1):
        face_ids=np.flatnonzero(labels==index)
        edges=adjacency[np.all(labels[adjacency]==index,axis=1)]
        groups=trimesh.graph.connected_components(edges,nodes=face_ids,min_len=1)
        groups=sorted(groups,key=len,reverse=True)
        if len(groups)>1:
            tiny=np.concatenate(groups[1:])
            if len(tiny)>4:
                raise ValueError(f'Meaningful disconnected physical contact needs review: {hold_id}: {[len(g) for g in groups]}')
            labels[tiny]=0
            partition_cleanup.append({'holdId':hold_id,'trianglesReassignedToBody':len(tiny),'reason':'isolated centroid-selection boundary fragment; physical geometry unchanged'})
    # Normals from the authored implicit surface, not area-biased averages of long
    # decimated triangles. Planar faces get exact plane normals at every corner.
    eps=.03; xyz=mesh.vertices.T
    grad=[]
    for axis in range(3):
        a=xyz.copy(); b=xyz.copy(); a[axis]+=eps; b[axis]-=eps
        grad.append((evaluate(*a,cfg)-evaluate(*b,cfg))/(2*eps))
    normals=np.stack(grad,axis=1); normals/=np.maximum(np.linalg.norm(normals,axis=1,keepdims=True),1e-10)
    corner_normals=normals[mesh.faces].copy()
    centre_grad=[]; centre_second=[]
    centres=mesh.triangles_center.T
    centre_value=evaluate(*centres,cfg)
    for axis in range(3):
        a=centres.copy(); b=centres.copy(); a[axis]+=eps; b[axis]-=eps
        va=evaluate(*a,cfg); vb=evaluate(*b,cfg)
        centre_grad.append((va-vb)/(2*eps))
        centre_second.append((va+vb-2*centre_value)/(eps*eps))
    centre_grad=np.stack(centre_grad,axis=1)
    centre_grad/=np.maximum(np.linalg.norm(centre_grad,axis=1,keepdims=True),1e-10)
    locally_planar=np.max(np.abs(np.stack(centre_second,axis=1)),axis=1)<1e-4
    agree=np.einsum('ij,ij->i',centre_grad,mesh.face_normals)>.97
    corner_normals[locally_planar & agree]=centre_grad[locally_planar & agree,None,:]
    for axis in range(3):
        planar=np.abs(centre_grad[:,axis])>.99999
        planar &= np.abs(mesh.face_normals[:,axis])>.97
        exact=np.zeros((int(planar.sum()),3)); exact[:,axis]=np.sign(centre_grad[planar,axis])
        corner_normals[planar]=exact[:,None,:]
    reversed_shading=np.einsum('ij,ij->i',corner_normals.mean(axis=1),mesh.face_normals)<0
    corner_normals[reversed_shading]=mesh.face_normals[reversed_shading,None,:]
    parts=[]
    for index,name in enumerate(['body']+ids):
        faceids=np.flatnonzero(labels==index)
        if not len(faceids): raise ValueError('Contact has no actual surface: '+name)
        faces=mesh.faces[faceids]; vertids,inverse=np.unique(faces.ravel(),return_inverse=True)
        parts.append(dict(name='body' if index==0 else 'hold-'+name,hold_id=None if index==0 else name,
                          vertices=mesh.vertices[vertids]/1000,faces=inverse.reshape(-1,3),normals=normals[vertids],corner_normals=corner_normals[faceids]))
    return mesh,parts,labels,dict(rawTriangles=rawcount,finalTriangles=len(mesh.faces),voxelMm=pitch,
                                 boundsMm=mesh.bounds.tolist(),watertight=bool(mesh.is_watertight),
                                 windingConsistent=bool(mesh.is_winding_consistent),volumeMm3=float(mesh.volume),
                                 contactIds=ids,partitionCleanup=partition_cleanup)
