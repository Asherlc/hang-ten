"""Validate finite cord centerlines, permitting only intentional endpoint joins."""
from __future__ import annotations
import math


def _sub(a, b):
    return tuple(x-y for x, y in zip(a, b))


def _dot(a, b):
    return sum(x*y for x, y in zip(a, b))


def _point(a, u, parameter):
    return tuple(x+parameter*y for x, y in zip(a, u))


def _distance(a, b):
    delta = _sub(a, b)
    return math.sqrt(_dot(delta, delta))


def _closest(a, b, c, d):
    u, v, w = _sub(b, a), _sub(d, c), _sub(a, c)
    aa, bb, cc, dd, ee = _dot(u,u), _dot(u,v), _dot(v,v), _dot(u,w), _dot(v,w)
    clamp = lambda value: max(0.0, min(1.0, value))
    candidates = [(s, clamp((ee+bb*s)/cc)) for s in (0., 1.)]
    candidates += [(clamp((bb*t-dd)/aa), t) for t in (0., 1.)]
    determinant = aa*cc-bb*bb
    if determinant > aa*cc*1e-12:
        s, t = (bb*ee-cc*dd)/determinant, (aa*ee-bb*dd)/determinant
        if 0 <= s <= 1 and 0 <= t <= 1:
            candidates.append((s,t))
    distance, s, t = min((_distance(_point(a,u,s),_point(c,v,t)),s,t) for s,t in candidates)
    overlap = 0.0
    if determinant <= aa*cc*1e-12:
        projection = _dot(_sub(c,a),u)/aa
        if _distance(c,_point(a,u,projection)) <= 1e-8:
            interval = sorted((_dot(_sub(c,a),u)/aa, _dot(_sub(d,a),u)/aa))
            overlap = max(0., min(1.,interval[1])-max(0.,interval[0]))*math.sqrt(aa)
    return distance, s, t, overlap


def validate_cord_paths(paths, radii=None, tolerance=1e-6):
    """Reject crossings, retracing and nonlocal tube intersections.

    Shared support or mouth endpoints may join different strands. Within one
    strand only adjacent joins and its intentional first/last closure may meet.
    Radius checks exclude the immediate neighborhood of an ordinary bend.
    """
    segments = []
    for identifier, points in paths.items():
        if len(points) < 2 or any(len(p) != 3 or not all(math.isfinite(v) for v in p) for p in points):
            raise ValueError("native cord paths must be finite 3D polylines")
        arc = 0.0
        for index, (start,end) in enumerate(zip(points,points[1:])):
            span = _distance(start,end)
            if span <= 1e-7:
                raise ValueError("native cord path contains a duplicate point")
            segments.append((identifier,index,start,end,arc,arc+span,len(points)-2))
            arc += span
    for i, first in enumerate(segments):
        aid, ai, a, b, astart, aend, afinal = first
        for bid, bi, c, d, bstart, bend, bfinal in segments[i+1:]:
            same = aid == bid
            radius = radii[aid]+radii[bid] if radii is not None else tolerance
            if any(max(a[k],b[k])+radius < min(c[k],d[k]) or max(c[k],d[k])+radius < min(a[k],b[k]) for k in range(3)):
                continue
            distance, s, t, overlap = _closest(a,b,c,d)
            if overlap > tolerance:
                raise ValueError(f"native cord paths retrace: {aid}/{ai}, {bid}/{bi}")
            if same and bi == ai+1:
                continue
            closure = same and ai == 0 and bi == afinal and _distance(a,d) <= tolerance
            a_endpoint = (ai == 0 and s <= 1e-8) or (ai == afinal and s >= 1-1e-8)
            b_endpoint = (bi == 0 and t <= 1e-8) or (bi == bfinal and t >= 1-1e-8)
            shared = distance <= tolerance and a_endpoint and b_endpoint
            if shared and (not same or closure):
                continue
            if distance <= tolerance:
                raise ValueError(f"native cord paths intersect: {aid}/{ai}, {bid}/{bi}")
            if radii is not None and distance < radius-1e-8:
                separation = abs((astart+s*(aend-astart))-(bstart+t*(bend-bstart))) if same else float("inf")
                if separation > 2*radius:
                    raise ValueError(f"native cord tubes intersect: {aid}/{ai}, {bid}/{bi}")
