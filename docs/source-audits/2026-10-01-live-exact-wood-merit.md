# Exact wood-penalty floor: rejected before candidate timing

The original near-channel triangle work still costs **85–87 ms** after every
root-separated link is skipped. This fails the unchanged **1 ms** wood-only
discriminator. The conditional candidate was never timed. No tube penalty,
query tuning, additional timing runs or app adoption followed.

This checkpoint starts at `e7d9c71b3`. Opus distinguished the app's wood
penalty from the preceding pilot's point/full-link clearance evaluation.
The merit function uses maximum penetration from `segmentContacts` at rope
radius plus 0.1 mm, then subtracts its existing 10 nm contact tolerance.
Conservative tube clearance would introduce a nonzero penalty on a state
where the original penalty is zero; it cannot silently replace this term.
Exact positive clearance is also still consumed by verification and motion
checks. The previous 43.72× generation and 5.7–5.8 ms clearance failures
remain unchanged.

The exact candidate only moves the original mesh-root rejection ahead of
ray parity. Each complete link's box is tested against the complete original
mesh box. Under the existing ±10 m domain, subtracting `2e-12 m²` covers the
bounded SIMD squared-gap arithmetic; radius squared is rounded upward.
Uncertain links retain original `segmentContacts` unchanged. This is an
ordering of an existing prune, not a new broad phase or approximate collider.
Inside/crossing queries never substitute negative nearest distance for the
original penetration semantics.

Link-only exact-rational coverage and native masks agree: **602 of 1,428
links** are root-separated on each fixed state, leaving **826 original
queries**. Exactly one original control and one residual-query floor were
measured per state:

| Fixed state | Original wood term | Original queries on residual links | Original/floor penalty | Per-link depth and total-sum bit identity |
| --- | ---: | ---: | ---: | --- |
| Source | 86.319 ms | 86.502 ms | 0 / 0 | Pass |
| Corrected | 87.366 ms | 85.223 ms | 0 / 0 | Pass |

Every root-separated link had an empty original manifold and both endpoints
parity-outside. Independent exact-rational review checked every retained mask
and the actual vertex root bounds, with no false certificates. Removing the
distant links saved little in these samples; the slight source slowdown is
retained. These residual costs constrain this implementation's unchanged
queries, not every possible exact geometry algorithm.

Query transformation/packing, root-mask discovery and static collider build
(82.826 ms) are outside the control/floor clocks. The floor also omits the
candidate's root classification work. Both floors failed, so the fixed stop
prevented candidate timing. These are single host samples, not p95 or device
results. The corrected state still fails final strain/material gates; this
does not produce an accepted nonlinear frame.

Fixtures observed two failures against the root-test stub, then five passes,
covering whole-link separation, crossing, inside and finite-radius penalty
fallback, threshold uncertainty and invalid domains. Scoped review found no
Critical or Important issue. Its minor provenance request was addressed by
a **post-pilot semantic audit**: immutable app sources at `e7d9c71b3` bind
`RopeDynamicsSolver.contactLinearTolerance`, `RopeRegionGeometry.clearance`
and the exact wood-term mapping. Those references were not part of the
original timed source snapshots; no timing rerun is claimed.

Actual Opus advisor `20dbc826-4d74-4319-bf3a-8d3a1db8d57b` recommended this
bounded exact screen and a subsequent inner-free-region necessary-condition
check. Its mean-cost and sagitta estimates are advice, not measured per-link
costs or proof of an impossible budget. In particular, the 0.82 m / 714 mean
rest length does not describe every link: retained material links are
adaptive, ranging from about 0.248 to 2.000 mm. Local checks use actual
positions and projected core spans.

This is **wood penalty only**. Portal, self/intercord terms, objective and
length terms, generation, exact positive clearance, swept collision, QP,
mesh/rendering, healthy/jug full verification and device gates are excluded.
The original physical limits and seated cords remain unchanged.

The summary binds fixed inputs, exact coverage scripts, source snapshots,
full native masks/results, RED/GREEN evidence, post-pilot semantic audit,
review, advisor responses and cleanup receipts. All six compiler/probe groups
and three drivers are absent; the exact advisor is closed and its guard is
absent. No server, simulator or historical resource was touched.
