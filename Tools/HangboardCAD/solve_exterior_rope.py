"""Compute seated exterior leads against an approved closed display surface.

This authoring solver never creates a passage. The caller supplies an evidenced
exterior endpoint and a section direction; unsupported/embedded endpoints fail.
Shortest paths use an offset actual mesh section, then every segment is checked
against the full 3D surface with adaptive whole-segment clearance bounds. This is a planar static route,
not friction, elasticity, dynamic settling or a CAD-to-mesh error certificate.
"""
from __future__ import annotations

import heapq
import math
import numpy as np
import trimesh
from shapely.geometry import LineString, Point, Polygon


def sample_route(route, spacing=0.0005):
    route=np.asarray(route,dtype=float)
    samples=[]
    for a,b in zip(route,route[1:]):
        count=max(2,math.ceil(float(np.linalg.norm(b-a))/spacing)+1)
        if len(samples)+count>100000:
            raise ValueError('exterior route exceeds sampling budget')
        samples.extend(np.linspace(a,b,count))
    return np.asarray(samples)


def validate_route_clearance(mesh, route, radius, tolerance=1e-5):
    """Bound complete segments using signed distance's 1-Lipschitz property.

    Endpoint clearances da/db bound an interval of length L from below by
    (da + db - L)/2. Refine uncertain intervals; never accept from samples
    alone. The caller must supply the same closed, outward surface as solving.
    This numerical check retains a 10 µm authoring tolerance; it is not an
    outward-rounded CAD error certificate.
    """
    route = np.asarray(route, dtype=float)
    if (route.ndim != 2 or route.shape[1] != 3 or len(route) < 2
            or not np.isfinite(route).all() or not math.isfinite(radius) or radius <= 0
            or not math.isfinite(tolerance) or tolerance <= 0):
        raise ValueError('invalid exterior clearance inputs')
    points = route
    distances = -trimesh.proximity.signed_distance(mesh, points)
    threshold = radius - tolerance
    if not np.isfinite(distances).all() or min(distances) < threshold:
        raise ValueError('exterior route fails full-surface clearance')
    starts, ends = points[:-1], points[1:]
    da, db = distances[:-1], distances[1:]
    lower = math.inf
    count = len(points)
    for _ in range(25):
        lengths = np.linalg.norm(ends - starts, axis=1)
        bounds = (da + db - lengths) / 2
        accepted = bounds >= threshold
        if accepted.any():
            lower = min(lower, float(bounds[accepted].min()))
        if accepted.all():
            return lower
        starts, ends = starts[~accepted], ends[~accepted]
        da, db = da[~accepted], db[~accepted]
        mids = (starts + ends) / 2
        count += len(mids)
        if count > 100000:
            raise ValueError('exterior clearance exceeds refinement budget')
        dm = -trimesh.proximity.signed_distance(mesh, mids)
        if not np.isfinite(dm).all() or min(dm) < threshold:
            raise ValueError('exterior route fails full-surface clearance')
        starts, ends = np.vstack([starts, mids]), np.vstack([mids, ends])
        da, db = np.concatenate([da, dm]), np.concatenate([dm, db])
    raise ValueError('exterior clearance exceeds refinement depth')


def _path(obstacle,start,end):
    """Visibility graph on every exterior and hole boundary; no hull surrogate."""
    if obstacle.contains(Point(start)) or obstacle.contains(Point(end)):
        raise ValueError('endpoint cannot fit cord outside the actual surface')
    if LineString([start,end]).relate(obstacle)[0]=='F':
        return np.asarray([start,end])
    polygons=[obstacle] if obstacle.geom_type=='Polygon' else list(obstacle.geoms)
    boundary=[]
    for polygon in polygons:
        for ring in [polygon.exterior,*polygon.interiors]:
            boundary.extend(np.asarray(ring.coords)[:-1])
    points=np.vstack([start,end,boundary])
    if len(points)>2500:
        raise ValueError('exterior section exceeds visibility budget')
    # Search lazily: most sections need only a few expanded boundary vertices.
    distances=[math.inf]*len(points);distances[0]=0;previous={};queue=[(0.0,0)]
    while queue:
        length,i=heapq.heappop(queue)
        if length>distances[i]+1e-12:continue
        if i==1:
            path=[1]
            while path[-1]!=0:path.append(previous[path[-1]])
            return points[path[::-1]]
        for j,p in enumerate(points):
            if j==i:continue
            distance=float(np.linalg.norm(p-points[i]))
            candidate=length+distance
            if distance<1e-10 or candidate>=distances[j]-1e-12:continue
            if LineString([points[i],p]).relate(obstacle)[0]!='F':continue
            distances[j]=candidate;previous[j]=i;heapq.heappush(queue,(candidate,j))
    raise ValueError('no exterior route in the selected section')


def solve_route(mesh,anchor,endpoint,radius,section_direction,clearance=0.0001,approach_point=None):
    """Return anchor→endpoint, preserving the approved endpoint exactly.

    The selected section contains both endpoints and the supplied direction.
    A full 3D clearance failure increases the offset at most three times; it
    never changes wood, endpoint, topology, diameter or hidden connections.
    """
    anchor=np.asarray(anchor,dtype=float);endpoint=np.asarray(endpoint,dtype=float)
    direction=np.asarray(section_direction,dtype=float)
    if any(p.shape!=(3,) or not np.isfinite(p).all() for p in [anchor,endpoint,direction]) or not math.isfinite(radius) or radius<=0 or not math.isfinite(clearance) or clearance<=0:
        raise ValueError('invalid exterior route inputs')
    if not mesh.is_watertight or not mesh.is_winding_consistent or mesh.volume<=0:
        raise ValueError('exterior surface must be closed with outward winding')
    if np.linalg.norm(anchor-endpoint)<1e-9:raise ValueError('coincident exterior endpoints')
    distances=-trimesh.proximity.signed_distance(mesh,np.asarray([anchor,endpoint]))
    if min(distances)<radius-1e-5:raise ValueError('endpoint cannot fit cord outside the actual surface')
    up=(anchor-endpoint)/np.linalg.norm(anchor-endpoint)
    across=direction-up*np.dot(direction,up)
    if np.linalg.norm(across)<1e-9:raise ValueError('section direction parallel to lead')
    across/=np.linalg.norm(across);normal=np.cross(up,across)
    basis=np.stack([up,across],axis=1)
    approach=None
    if approach_point is not None:
        approach=np.asarray(approach_point,dtype=float)
        if approach.shape!=(3,) or not np.isfinite(approach).all():
            raise ValueError('invalid evidenced approach point')
        if abs(float(np.dot(approach-endpoint,normal)))>1e-8:
            raise ValueError('evidenced approach is outside selected section')
    cross=mesh.section(plane_origin=endpoint,plane_normal=normal)
    if cross is None:
        if approach is not None and float(np.dot(anchor-endpoint,direction))<=1e-9:
            raise ValueError('direct lead cannot preserve the evidenced approach')
        direct=np.asarray([anchor,endpoint])
        if float((-trimesh.proximity.signed_distance(mesh,sample_route(direct))).min())<radius-1e-5:
            raise ValueError('exterior route fails full-surface clearance')
        validate_route_clearance(mesh,direct,radius)
        return direct
    wood=Polygon()
    for loop in cross.discrete:
        polygon=Polygon((np.asarray(loop)-endpoint)@basis)
        if not polygon.is_valid:raise ValueError('invalid exterior mesh section')
        wood=wood.symmetric_difference(polygon)
    if wood.is_empty:raise ValueError('empty exterior mesh section')
    offset=radius+clearance
    for _ in range(3):
        # Round-buffer chords lie inside their arcs; inflate analytically so
        # the polygonal obstacle remains outside the requested radius offset.
        obstacle=wood.buffer(offset/math.cos(math.pi/48),quad_segs=12)
        start=(anchor-endpoint)@basis
        if approach_point is None:
            path=_path(obstacle,start,np.zeros(2))
        else:
            selected=(approach-endpoint)@basis
            path=_path(obstacle,start,selected)
            toward=direction@basis
            # Pull the selected exterior path taut up to its declared mouth.
            # Only shorten from a point on the evidenced approach side.
            for index,point in enumerate(path):
                if np.dot(point,toward)>1e-9 and LineString([point,np.zeros(2)]).relate(obstacle)[0]=='F':
                    path=np.vstack([path[:index+1],np.zeros(2)])
                    break
            else:
                raise ValueError('no clear route from the evidenced approach')
        world=endpoint+path@basis.T;world[0]=anchor;world[-1]=endpoint
        minimum=float((-trimesh.proximity.signed_distance(mesh,sample_route(world))).min())
        if minimum>=radius-1e-5:
            validate_route_clearance(mesh,world,radius)
            return world
        offset+=radius-minimum+clearance
    raise ValueError('exterior route fails full-surface clearance')


def pair_clearance(first, second, shared_anchor=True):
    """Complete-segment gap, optionally excluding shared initial straight rays.

    Evaluate the interior closest approach and all four endpoint/edge cases.
    Cross products avoid cancellation in the near-parallel determinant.
    """
    first = np.asarray(first, dtype=float)
    second = np.asarray(second, dtype=float)
    if (first.ndim != 2 or second.ndim != 2
            or first.shape[1] != 3 or second.shape[1] != 3
            or len(first) < 2 or len(second) < 2
            or not np.isfinite(first).all() or not np.isfinite(second).all()
            or (shared_anchor and not np.allclose(first[0], second[0], rtol=0, atol=1e-9))
            or np.any(np.linalg.norm(np.diff(first, axis=0), axis=1) < 1e-9)
            or np.any(np.linalg.norm(np.diff(second, axis=0), axis=1) < 1e-9)):
        raise ValueError('invalid paired exterior routes')
    u = (first[1:] - first[:-1])[:, None, :]
    v = (second[1:] - second[:-1])[None, :, :]
    w = first[:-1, None, :] - second[None, :-1, :]
    aa = (u*u).sum(-1)
    bb = (u*v).sum(-1)
    cc = (v*v).sum(-1)
    dd = (u*w).sum(-1)
    ee = (v*w).sum(-1)
    normal = np.cross(u, v)
    determinant = (normal*normal).sum(-1)
    s = np.divide((np.cross(v, w)*normal).sum(-1), determinant,
                  out=np.zeros_like(determinant), where=determinant > 0)
    t = np.divide((np.cross(u, w)*normal).sum(-1), determinant,
                  out=np.zeros_like(determinant), where=determinant > 0)
    inside = (s >= 0) & (s <= 1) & (t >= 0) & (t <= 1) & (determinant > 0)
    distances = np.where(inside, ((w+s[..., None]*u-t[..., None]*v)**2).sum(-1), np.inf)
    for s in [0, 1]:
        t = np.clip((ee+s*bb)/cc, 0, 1)
        distances = np.minimum(distances, ((w+s*u-t[..., None]*v)**2).sum(-1))
    for t in [0, 1]:
        s = np.clip((t*bb-dd)/aa, 0, 1)
        distances = np.minimum(distances, ((w+s[..., None]*u-t*v)**2).sum(-1))
    # Initial straight rays share the support knot and can only diverge.
    if shared_anchor:
        first_ray = first[1] - first[0]
        second_ray = second[1] - second[0]
        if (np.dot(first_ray, second_ray) > 0
                and np.linalg.norm(np.cross(first_ray, second_ray))
                    <= 1e-12*np.linalg.norm(first_ray)*np.linalg.norm(second_ray)):
            return 0.0
        distances[0, 0] = np.inf
    return float(np.sqrt(distances.min()))


def solve_pair(mesh, anchor, endpoints, radius, approaches, additional_clearance=.001):
    """Choose the shortest clear pair in a fixed nine-plane family per lead.

    Attachment and approach coordinates remain authored display evidence.
    Approach points select the entry side, not mandatory material pins: their
    projection into each candidate plane must stay on the original side.
    Every accepted route clears the full wood surface; complete segment pairs
    have 2*radius + clearance separation after their shared initial rays.
    This is a bounded static approximation, not a global 3D equilibrium solve.
    """
    anchor = np.asarray(anchor, dtype=float)
    endpoints = np.asarray(endpoints, dtype=float)
    approaches = np.asarray(approaches, dtype=float)
    if (anchor.shape != (3,) or endpoints.shape != (2,3) or approaches.shape != (2,3)
            or not all(np.isfinite(p).all() for p in [anchor,endpoints,approaches])
            or not math.isfinite(additional_clearance) or additional_clearance <= 0):
        raise ValueError('invalid paired exterior inputs')
    candidates = []
    for end, guide in zip(endpoints, approaches):
        separation = np.linalg.norm(anchor-end)
        if separation < 1e-9:
            raise ValueError('coincident exterior endpoints')
        up = (anchor-end)/separation
        direction = guide-end
        across = direction-up*np.dot(direction,up)
        if np.linalg.norm(across) < 1e-9:
            raise ValueError('approach parallel to lead')
        across /= np.linalg.norm(across)
        normal = np.cross(up,across)
        routes = []
        for angle in [0,15,-15,30,-30,45,-45,60,-60]:
            theta = math.radians(angle)
            newdir = across*math.cos(theta)+normal*math.sin(theta)
            n = np.cross(up,newdir)
            approach = guide-n*np.dot(guide-end,n)
            if np.dot(approach-end,direction) <= 1e-9:
                continue
            try:
                route = solve_route(mesh,anchor,end,radius,newdir,approach_point=approach)
            except ValueError:
                continue
            if np.dot(route[-2]-end, direction) <= 1e-9:
                continue
            length = float(np.linalg.norm(np.diff(route,axis=0),axis=1).sum())
            routes.append((length,route))
        candidates.append(routes)
    best = None
    for left in candidates[0]:
        for right in candidates[1]:
            if pair_clearance(left[1],right[1]) < 2*radius+additional_clearance:
                continue
            length = left[0]+right[0]
            if best is None or length < best[0]:
                best = (length,left[1],right[1])
    if best is None:
        raise ValueError('no clear pair within the exterior routing budget')
    return best[1],best[2]
