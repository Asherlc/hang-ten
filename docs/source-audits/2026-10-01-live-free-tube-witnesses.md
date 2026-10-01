# Isotropic free-tube certificates: rejected by actual wall witnesses

A uniform free radius for an entire U-passage cannot certify **262 straight
source links**. Restricting the core interval to each individual link still
fails for **18 source links**, above the fixed eight-link stop. Directed
actual-wall witnesses support both rejections. No runtime certificate,
native query system, changed penalty or app adoption was built.

This follows the 85–87 ms exact wood-penalty floor at `e7d9c71b3`.
The hypothesis is a sufficient **zero original penalty** certificate:
if every actual wood triangle is outside a connected core neighbourhood of
radius `rho`, and the complete material link is within `M` of that core,
then `rho - M` bounds wood clearance. It must meet the original 3.6 mm
requirement, with the existing 10 nm merit tolerance. Foreign wood and
signed-component agreement remain required. The earlier unsigned image
envelope alone does not prove such a region.

First, ordinary-float vertex/edge-midpoint/barycentre sampling selected actual
wall witnesses. They suggest whole-U free-radius ceilings of **3.695385 mm**
and **3.695832 mm**. Sampling does not prove the global minimum. Adding
endpoint offsets and a core-arc curvature allowance left 414 source links
uncertain. That allowance is a **sufficient upper bound** on material offset;
414 is a failed-bound count, not a geometric impossibility count.

The independent directed check instead uses exact midpoints of actual binary64
mesh vertices and 80-digit outward arithmetic. Those wall points bound any
whole-U free radius above. For 262 same-leg source links, their exact endpoint
offset alone requires a larger radius. The smallest straight-link shortfall
is **273.085 nm** using 3.6 mm, so rejection also survives subtracting the
merit's 10 nm tolerance. No trigonometric approximation is needed for this
directed counterexample.

Opus recommended a second necessary-condition screen with each link's own
projected core interval. Actual triangle samples, including foreign wood,
give free-radius upper witnesses; material endpoint/quarter/midpoint samples
give offset lower witnesses. A KD tree only selects sample witnesses. It
does not certify a minimum over the mesh or a maximum along the material.
The first attempt stopped on an empty witness-selection ball. A distinct
corrected script selects the nearest actual sample in that case; the failed
source, log and provenance remain retained. This integration fix changes no
physics, stop threshold or timing result.

The link-local float screen finds 18 source failures and zero corrected-state
failures. Directed rechecking verifies **all 18 source failures**, with a
smallest radius shortfall of **81.005 nm**. Each wall witness is an exact
triangle-edge midpoint. Exact rational cone predicates place its selected
polar core point on the link's narrow lower arc; alternatively, a core-arc
endpoint gives a valid distance upper bound. Full-circle endpoint distance
lower-bounds distance to the restricted core arc. These inequalities reject
the specified isotropic clearance certificate even before constructing it.
Independent review reproduced the enclosures at 110 digits.

The prior mean-length sagitta estimate is unsuitable here. Material links are
adaptive; the failed source bend links have approximately **0.248 mm** rest
length. Maximum actual projected-core curvature allowance over the tested
source links is **1.282 µm**, rather than the 27.5 µm obtained from averaging
0.82 m across 714 links. Local tests use actual geometry. The corrected state
still fails final strain/material gates, and zero sampled corrected failures
does not certify its geometry.

The eight-link cutoff was fixed before the local screen, informed by an
**inferred mean** original-query cost. Eighteen failures reject this chosen
continuation gate; they do not prove any runtime lower bound. No per-witness
native cost was measured. These findings reject scalar isotropic free-region
certificates, **not physical clearance**: the original mesh checks remain
clear. Directional certificates, other shapes and other algorithms are not
ruled out.

Scoped review found no Critical or Important issue. Its terminology and
10 nm distinction are recorded above. The companion summary binds retained
inputs, sample and directed scripts/results, both local attempts, actual
source snapshots, review and exact cleanup receipts. Both local worker groups
and drivers are verified absent. No simulator, server or historical process
was used. The model, seated cords, accepted CAD PR and every full physics and
performance gate remain unchanged.
