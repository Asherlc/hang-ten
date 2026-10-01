# Actual-triangle slab and batch checkpoint — 30 September 2026

The user chose to keep physical limits and simplify rendering first, with
possible future tolerance changes if simplification is insufficient. The
rendering checkpoint saves only a few hundredths of a millisecond. This
checkpoint keeps all physics, geometry, material, solver and acceptance limits.
It changes experimental geometry-query representation only; the app continues
using its accepted backend and seated cords. No runtime adoption follows.

A coverage preflight rederives directed 80-digit one-sided envelopes for every
actual triangle, reproducing every retained global patch maximum exactly. Each
CAD-patch BVH then combines actual triangle bounds with its local envelope.
A whole-segment Taylor lower bound uses midpoint gradient and a Hessian bound
valid on the segment; ordinary-float coverage alone supplies no certificate.
Local Taylor could cover 1,926/2,858 queries and 47,864/119,781 frozen wood/portal
support rows. Global and local Lipschitz both cover 1,890 queries and the same
47,864 rows when using these smaller actual-triangle AABBs. The earlier global
patch-AABB ceiling was looser. Fewer uncertain triangles does not resolve most
rows. Ruling: reject a new analytic-envelope runtime index at this preflight.

The successor uses actual mesh vertex projections onto arbitrary stored
binary64 directions to bound each complete triangle and each BVH node. Exact
triangle normals are unnecessary for this bounding direction. Components at
most 2 and coordinates at most 10 metres bound dot-product absolute sums by
60 metres. `gamma_5*60 < 3.34e-14 m`; expanding projected extrema by 1e-12 m
covers dot error and bound expansion. Upward-rounded squared sums and square
root bound the direction norm above; downward-rounded gaps and division bound
Euclidean separation below. Zero/invalid directions supply no certificate.
Vertex extrema enclose the complete triangles. Endpoint extrema enclose the
complete query segment. Original sign and uncertain triangle kernels remain.
The immutable index retains the collider it bounds.

The optional `--slabs --batch` path builds a second tree over all original
point/segment queries, including their maximum board-relative affine correction
thresholds. Every rope packet encloses whole segments; a packet certificate
uses its maximum threshold. Splitting either tree partitions the Cartesian
pairs without losing coverage. Uncertain leaves retain the original triangle,
ray-crossing and segment-pair tests. Original ray/parity sign is cached only
for identical finite endpoint coordinates within this batch and immutable mesh.
No temporal sign shortcut, physical remesh or independent loop solve is used.

Slab separation produced one expected RED fixture, then 11 GREEN. The batch
stub produced one expected RED fixture, then 14 GREEN, including 128 cube
point/segment cases checked against original nearest/sign authority, mixed
inside/inward/crossing cases, nonfinite rejection and empty input. Scoped
independent reviews found no slab or batch correctness findings. The general
1 nm floating triangle-kernel-to-affine bridge remains explicitly unproved;
independent original-row checks support only the retained fixed candidate.

First slab sample: 29.158 ms versus 198.208 ms, static index build 55.328 ms.
The sign-cost checkpoint: 29.627 ms versus 192.494 ms; original 4,286 sign
queries take 7.576 ms and 1,427 unique queries take 3.304 ms. Initial batch:
22.949 ms versus 198.976 ms, with possible fixture-compiler overlap retained.
Final batch construction-cost sample: **23.532 ms versus 198.713 ms (8.444×)**,
static index build 57.602 ms. All 2,858 queries are clear; independently checked
119,693 original generated wood inequalities and 119,781 retained frozen
support rows have minimum affine gap 3.182306 µm and zero omitted multipliers.
Portal rows are still required and never removed by this wood-only experiment.
The final independent sign checkpoint is 7.931 ms for original endpoint calls
and 3.394 ms for unique points, outside both generation clocks.

Ruling: this is useful measured reduction but fails the cost checkpoint. Do
not expand it to 50 runs or adopt it. One host sample is not p95; portal,
self/inter-cord, CCD, complete geometry, solver, motion, visual and device
validation remain outside its clock. The required 50× complete-geometry and
4 ms device-step gates remain open, as do cold QP 2 ms and verification 1 ms.

Full prototype Python suite: 42 passed, 3 failed because the legacy integration
harness hardcodes missing `.context/frantic-kiwi/rope-build/rope_solver`:
`test_rope_settles_around_outside_of_round_bar`,
`test_wrong_wrap_topology_is_rejected`, and
`test_fresh_simulations_are_repeatable`. No historical resource was recreated.
The intentionally failing live catalog inventory WIP remains untouched.

The [manifest](2026-09-30-live-triangle-slab-batch-summary.json) binds immutable
compiled sources, RED/GREEN logs, fixed inputs, proof/coverage scripts, reviews
and verified exact owned cleanup. A math-launcher stdout path was reused by
the coverage run; the complete directed proof JSON remains retained, and its
original stdout is not claimed as an independent artifact. All native/math
child groups and drivers were deleted and verified. No server, simulator or
CAD/model/material changes were made. Conditional openness to tolerances does
not authorize changing them; the current limits remain in force.
