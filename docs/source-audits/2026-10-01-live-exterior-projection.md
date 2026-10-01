# Complete exterior support family: proof passes, mouth-query floor fails

Owner `strong-owl-live-physics`, branch `feat/live-hangboard-physics`, base
`e9497778054440411779231a79eb9fd98f259aac`. No app or physical-model change.

The fixed262direction screen missed exterior wrapping links with micrometre
clearance. Its direction set was not enlarged. This successor tests the entire
global support-plane family with n_x=0, as recommended by Opus: exact distance
from the complete link's YZ projection to the filled convex envelope of **all
21,388 actual mesh vertex projections**. Every actual triangle is contained,
including foreign wood; no extrusion assumption is necessary.

This envelope is a zero-only *exterior separation certificate*. It is never a
hull collider, force, inside/penetration proxy or approximation of the holes.
Anything it cannot certify retains the original triangle query. A complete
projected segment at distance at least the original3.6mm capsule radius plus
fixed1nm certificate padding clears the whole 3D capsule. The padding tightens
only this sufficient certificate; no physical radius or tolerance changes.

Exact Fraction monotonic-chain construction produced **242 envelope vertices**.
An independent exact containment check covers every actual vertex against every
edge. Exact segment distance checks inside endpoints, segment crossings and
collinear overlaps before taking the minimum of the four endpoint-to-segment
distances per edge. In 2D this covers the complete disjoint-segment minimum,
including parallel and degenerate cases. Seven independent fixtures ran
RED (seven failures) → GREEN (seven passes).

Of the same150 non-tube root-residual links, **128 certify in each fixed state**,
leaving **22**. This passes the predeclared100-link necessary coverage gate.
Offline construction/vertex proof took26.605s; total exact classification32.555s.
Neither is a runtime query timing. The negative results concern this entire
X-parallel support family at the fixed padded radius, rather than a sampled
direction resolution limit.

The native discriminator gives those128 exterior certificates and the retained
676 tube certificates free exclusions, alongside602 root-separated links. The
remaining22 still call unchanged `segmentContacts` at the original radius:

| State | Original1,428-link wood control | Remaining22 original queries |
|---|---:|---:|
| Source | 96.136ms | **1.767ms** |
| Corrected | 92.916ms | **1.706ms** |

Both miss the fixed **1ms** gate before any runtime classification cost.
Per-link maximum depths and the summed wood penalty are bit-identical, and all
masked links are original-query-empty / parity-outside. The penalty remains zero.
There are **zero candidate runs** and no native envelope certificate implementation.
Static collider construction96.587ms, source transforms and all masks are outside
the clocks. The full merit, exact positive clearance, contact generation, CCD,
solver, trajectories and device work are not measured here.

The22 residual links are near the entry and exit mouths. Their measured query
cost explains most of the earlier150-query floor; spreading that floor uniformly
over links would have given a misleading estimate. This closes the envelope plus
unchanged-mouth-query runtime candidate, not all potential mouth algorithms.
The accurate cold solver (~30ms versus2ms) and complete geometry (43.72× versus
50×) remain failed. No live rollout or accepted nonlinear step is established.

Focused review found Critical0 / Important0 and verified complete IDs, exact
thresholds, source endpoints, radii, flags, input hashes and geometry semantics.
General numerical sign/parity and other-state/runtime/device claims remain outside
the proof. The companion summary binds all sources, inputs, reports and exact
owned-resource deletion receipts. Seated cords and the intentional inventory WIP
remain untouched; no original workspace, PR529 or historical resource was modified.
