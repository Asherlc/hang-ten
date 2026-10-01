"""Experimental two-sided mesh/reference tile bounds; never used by the app.

Each parameter triangle maps onto a *trimmed* reference surface. Matching
barycentric coordinates pair every reference point with a mesh point and vice
versa. This proves a Hausdorff envelope, not orientation, watertightness, a CAD
error bound, nearest-point coverage or a replacement collision/CCD kernel.
"""
from decimal import Decimal, localcontext, ROUND_FLOOR, ROUND_CEILING
from functools import lru_cache
import math


class Interval:
    def __init__(self, lo, hi=None):
        self.lo = Decimal.from_float(lo) if isinstance(lo, float) else Decimal(lo)
        self.hi = self.lo if hi is None else Decimal(hi)

    @staticmethod
    def rounded(fn, rounding):
        with localcontext() as ctx:
            ctx.prec, ctx.rounding = 80, rounding
            return fn()

    def __add__(self, other):
        other = interval(other)
        return Interval(self.rounded(lambda: self.lo + other.lo, ROUND_FLOOR),
                        self.rounded(lambda: self.hi + other.hi, ROUND_CEILING))

    def __sub__(self, other):
        other = interval(other)
        return Interval(self.rounded(lambda: self.lo - other.hi, ROUND_FLOOR),
                        self.rounded(lambda: self.hi - other.lo, ROUND_CEILING))

    def __mul__(self, other):
        other = interval(other)
        pairs = [(a, b) for a in (self.lo, self.hi) for b in (other.lo, other.hi)]
        return Interval(min(self.rounded(lambda: a*b, ROUND_FLOOR) for a, b in pairs),
                        max(self.rounded(lambda: a*b, ROUND_CEILING) for a, b in pairs))

    def __truediv__(self, other):
        other = interval(other)
        if other.lo <= 0:
            raise ValueError('Denominator must be positive')
        return self * Interval(self.rounded(lambda: 1/other.hi, ROUND_FLOOR),
                               self.rounded(lambda: 1/other.lo, ROUND_CEILING))

    def squared(self):
        lo = Decimal(0) if self.lo <= 0 <= self.hi else min(self.lo.copy_abs(), self.hi.copy_abs())
        hi = max(self.lo.copy_abs(), self.hi.copy_abs())
        return Interval(self.rounded(lambda: lo*lo, ROUND_FLOOR),
                        self.rounded(lambda: hi*hi, ROUND_CEILING))

    def sqrt(self):
        if self.lo < 0:
            raise ValueError('Square root domain')
        with localcontext() as ctx:
            ctx.prec = 80
            # Decimal.sqrt is correctly rounded, independently of ctx.rounding.
            return Interval(max(Decimal(0), self.lo.sqrt().next_minus()),
                            self.hi.sqrt().next_plus())


def interval(x):
    return x if isinstance(x, Interval) else Interval(x)


def norm(values):
    total = Interval(0)
    for value in values:
        total = total + value.squared()
    return total.sqrt()


@lru_cache(maxsize=131072)
def trig_enclosure(angle, cosine=False):
    """Enclose sin/cos of an exact chosen binary64 angle, without libm error.

    Polynomial through degree159 (including the zero parity coefficient).
    Lagrange remainder <= |angle|^160/160!, since all real derivatives have
    magnitude <=1. Directed interval arithmetic also encloses cancellation.
    """
    if not math.isfinite(angle) or abs(angle) > 10:
        raise ValueError('Angle outside the finite [-10,10] chart domain')
    x = Interval(angle)
    term = Interval(1) if cosine else x
    result = term
    negative_square = Interval(0) - x.squared()
    for k in range(1, 80):
        a = 2*k-1 if cosine else 2*k
        term = term * negative_square / (a*(a+1))
        result = result + term
    tail = Interval(1)
    for k in range(1, 161):
        tail = tail * abs(angle) / k
    return result + Interval(tail.hi.copy_negate(), tail.hi)


def unwrap_triangle(angles):
    if len(angles) != 3 or not all(math.isfinite(x) and abs(x) <= math.pi for x in angles):
        raise ValueError('Expected three finite canonical angles')
    # These are chosen floating coordinates, not claimed exact inverse trig or
    # periodic translations. tile_envelope measures their actual 3D residual.
    base = angles[0]
    return [base] + [x + round((base-x)/math.tau)*math.tau for x in angles[1:]]


def reference_point(patch, uv):
    axis = patch['axis']
    orth = [k for k in range(3) if k != axis]
    p = [Interval(x) for x in patch['center']]
    u, v = uv
    kind = patch['kind']
    if kind == 'Plane':
        p[orth[0]] = p[orth[0]] + u
        p[orth[1]] = p[orth[1]] + v
    elif kind == 'Cylinder':
        p[orth[0]] = p[orth[0]] + trig_enclosure(u, True)*patch['radius']
        p[orth[1]] = p[orth[1]] + trig_enclosure(u)*patch['radius']
        p[axis] = p[axis] + v
    elif kind == 'Toroid':
        radius = Interval(patch['majorRadius']) + trig_enclosure(v, True)*patch['minorRadius']
        p[orth[0]] = p[orth[0]] + radius*trig_enclosure(u, True)
        p[orth[1]] = p[orth[1]] + radius*trig_enclosure(u)
        p[axis] = p[axis] + trig_enclosure(v)*patch['minorRadius']
    else:
        raise ValueError('Unsupported reference surface')
    return p


def tile_envelope(patch, uv, vertices):
    """Outward Decimal upper bound for both directions of a triangle pair.

    ||F(sum lambda_i uv_i) - sum lambda_i F(uv_i)|| is bounded by
    sum_{i<j} lambda_i lambda_j Q(uv_i-uv_j)/2 <= max(Q)/6.
    Q = (R+r)du²+2r|du dv|+r dv² for a torus, r du² for a
    cylinder, zero for a plane. The maximum vertex residual is added. Using
    coordinate diameters bounds every Q and retains its mixed derivative.
    """
    if (patch.get('axis') not in (0, 1, 2) or len(patch.get('center', [])) != 3
            or len(uv) != 3 or len(vertices) != 3
            or any(len(p) != 2 for p in uv) or any(len(p) != 3 for p in vertices)
            or not all(math.isfinite(x) and abs(x) <= 10 for p in [*uv, *vertices, patch['center']] for x in p)):
        raise ValueError('Invalid bounded tile domain')
    kind = patch['kind']
    for key in {'Cylinder': ['radius'], 'Toroid': ['majorRadius', 'minorRadius']}.get(kind, []):
        if not math.isfinite(patch[key]) or not 0 < patch[key] <= 10:
            raise ValueError('Invalid reference radius')
    residual = max(norm([q-Interval(x) for q, x in zip(reference_point(patch, chart), point)]).hi
                   for chart, point in zip(uv, vertices))
    du = Interval((Interval(max(p[0] for p in uv))-min(p[0] for p in uv)).hi)
    dv = Interval((Interval(max(p[1] for p in uv))-min(p[1] for p in uv)).hi)
    if kind == 'Plane':
        curvature = Interval(0)
    elif kind == 'Cylinder':
        curvature = du.squared()*patch['radius']/6
    elif kind == 'Toroid':
        r = Interval(patch['minorRadius'])
        curvature = ((Interval(patch['majorRadius'])+r)*du.squared() + r*du*dv*2 + r*dv.squared())/6
    else:
        raise ValueError('Unsupported reference surface')
    return (Interval(residual)+curvature).hi
