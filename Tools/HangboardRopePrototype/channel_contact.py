"""Isolated channel-row hypothesis; no app import or region certificate.

The original mesh must check every proposed correction. A nearest-core formula
alone does not certify trimmed coverage, sign, foreign wood, or old affine rows.
"""
from __future__ import annotations
from dataclasses import dataclass
import math
import time


@dataclass(frozen=True)
class UChannel:
    center: tuple[float, float, float]
    bend_radius: float
    tube_radius: float
    mouth_z: float
    envelope: float

    def __post_init__(self):
        if (not all(math.isfinite(x) for x in (*self.center, self.bend_radius,
                self.tube_radius, self.mouth_z, self.envelope)) or
                not 0 < self.tube_radius < self.bend_radius or self.envelope < 0 or
                self.mouth_z <= self.center[2]):
            raise ValueError('Invalid non-overlapping U channel')

    @staticmethod
    def point(point):
        if len(point) != 3 or not all(math.isfinite(x) for x in point):
            raise ValueError('Invalid point')
        return point

    def core(self, point):
        x, _, z = self.point(point)
        cx, cy, cz = self.center
        x, z = x-cx, z-cz
        if z >= 0:
            return (cx + (self.bend_radius if x >= 0 else -self.bend_radius), cy, cz+z)
        rho = math.hypot(x, z)
        return (cx+self.bend_radius*x/rho, cy, cz+self.bend_radius*z/rho)

    def eligible(self, point):
        return point[2] < self.mouth_z and math.dist(point, self.core(point)) < self.tube_radius

    def tightening(self, length, rope_radius, clearance):
        # This is a conservative candidate restriction, not a directed
        # floating-point region proof. Original full-link checks remain required.
        e = self.tube_radius-rope_radius-clearance
        if not all(math.isfinite(x) and x > 0 for x in (length, rope_radius, clearance, e)):
            raise ValueError('Invalid finite-radius fit')
        chord = length*1.005 + 2*e
        if chord >= 2*self.bend_radius:
            return None
        arc = 2*self.bend_radius*math.asin(chord/(2*self.bend_radius))
        bound = math.nextafter(arc*arc/(8*self.bend_radius), math.inf)
        return bound if bound+self.envelope < min(e, .0001) else None

    def row(self, point, rope_radius, clearance, tightening=0):
        self.point(point)
        if not all(math.isfinite(x) for x in (rope_radius, clearance, tightening)) or min(rope_radius, clearance) <= 0 or tightening < 0:
            raise ValueError('Invalid physical row')
        capacity = self.tube_radius-rope_radius-clearance-self.envelope-tightening
        if capacity <= 0:
            raise ValueError('No eroded tube remains')
        q = self.core(point)
        delta = tuple(a-b for a,b in zip(point,q))
        distance = math.hypot(*delta)
        if distance <= 1e-12:
            # As in the original inactive contact window, an on-core point
            # has no active wall. A later nonlinear check may reject its move.
            return None
        return capacity-distance, tuple(-x/distance for x in delta)


def build_rows(frozen, channels, clearance=.0001):
    start = time.perf_counter()
    if frozen['orientation'] != [0, 0, 0, 1]:
        raise ValueError('Fixed experiment requires identity orientation')
    points = [[[p[0], p[1]-frozen['boardHeight'], p[2]] for p in rope]
              for rope in frozen['positions']]
    selected, links, tighten = {}, set(), {}
    for r, rope in enumerate(points):
        for i,p in enumerate(rope):
            matches = [j for j,c in enumerate(channels) if c.eligible(p)]
            if len(matches) == 1:
                selected[r,i] = matches[0]
                tighten[r,i] = 0
        for i,length in enumerate(frozen['restLengths'][r]):
            j = selected.get((r,i))
            if j is None or j != selected.get((r,i+1)):
                continue
            value = channels[j].tightening(length, frozen['radii'][r], clearance)
            if value is not None:
                links.add((r,i,i+1))
                tighten[r,i] = max(tighten[r,i], value)
                tighten[r,i+1] = max(tighten[r,i+1], value)
    kept, removed, rows = [], [], []
    for n,row in enumerate(frozen['rows']):
        ps, r = row['particles'], row['rope']
        replace = row['contact'] and row['secondRope'] < 0 and (
            len(ps) == 1 and (r,ps[0]) in selected or
            len(ps) == 2 and (r,*ps) in links)
        # Eligibility is a proposal domain, not provenance/sign certification.
        # Portal crossing supports are beyond the deliberately retained mouths.
        if replace:
            removed.append(n)
        else:
            kept.append(n)
            rows.append(row)
    added = []
    for (r,i),j in selected.items():
        hit = channels[j].row(points[r][i], frozen['radii'][r], clearance, tighten[r,i])
        if hit is None:
            continue
        residual, normal = hit
        row = dict(rope=r, secondRope=-1, particles=[i], gradients=[list(normal)],
                   boardGradient=-normal[1], residual=residual, contact=True)
        rows.append(row)
        added.append(dict(rope=r, particle=i, channel=j, tightening=tighten[r,i]))
    report = dict(runtimeAdoption=False, regionCertified=False, clearance=clearance,
                  originalContacts=sum(x['contact'] for x in frozen['rows']),
                  candidateContacts=sum(x['contact'] for x in rows),
                  removedRows=len(removed), tubeRows=len(added),
                  retainedOriginalRowIDs=kept, removedOriginalRowIDs=removed,
                  tubeSupports=added, eligibleWholeLinks=len(links),
                  builderSeconds=time.perf_counter()-start,
                  scope='Offline frozen-row replacement hypothesis. No wall-ring, foreign-wood, sign, original-affine or runtime proof. Every proposed correction needs original mesh checks.')
    return {**frozen, 'rows':rows}, report
