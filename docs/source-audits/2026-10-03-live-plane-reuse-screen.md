# Query-local exact plane union reuse: closed speed screen

This distinct native-only representation shares a conservative support calculation
over every actual vertex in an exact rational plane group. It keeps each triangle's
original ray, eligible narrow phase, fractions, edge checks and merging. No facet
or contact row is discarded just because it shares a plane. Offline IDs are tied
to the descriptor; runtime union supports cover actual member vertices.

The prior census's necessary 50% threshold rejects consecutive-only reuse at
25.11% removed calls. A fixed eight-entry direct-mapped cache removes 50.74%
(14,934→7,356) at step140, allowing one implementation. Cache collisions force
recomputation; nil supports are cached as unknown. No dictionary, cache-size
search or cross-step mutable cache is used. The prior standalone generic/axis/
free-ball speed versions stay closed; this screen tests a new contribution.

The absent union support failed its fixture (RED). The absent cache failed its
collision fixture after union implementation (RED). Both implemented primitives
passed their geometric/empty/collision/unknown fixtures (GREEN). Three intermediate
compiles failed on an ambiguous Swift infinity literal and ran no physics; they
are retained as tooling failures, not geometric RED evidence.

Independent exact-rational checks pass 50,000 support, axis, BVH, free-ball and
union cases. Optimized scalar LLVM has no unsafe floating arithmetic flags. Every
actual runtime union was independently checked: **9,233 groups, 28,680 distinct
member vertices, zero unknown groups**. Stored projection intervals enclose all
exact vertex projections and norm upper bounds dominate the exact squared norm.
These checks do not assert generic equivalence to rounded triangle narrow phase.

The cold 20-step window121–140 retains identical poses against the current
control, 75 QPs on each side, zero caps/retries and independent mesh/material
acceptance. Original parity agrees on all 28,280 certified skips. Verification and
timed candidate retain identical persisted states, anchors and decisions; strict
step140 difference is 1.728 µm, and restored-anchor/invalid-dt rollback checks pass.

Seven alternating cold triplets give median candidate/original **0.806163**
(required <=0.80), and candidate/free-ball **0.962630** (required <=0.90). Both
speed gates fail. Candidate totals are 145.97–152.19 ms per 20-step window;
free-ball totals 152.81–164.33 ms. The new representation adds about 3.7% median
saving, insufficient to open trajectory or simulator stages. No changed threshold,
additional sampling, product adoption or workable video claim follows.

All newly owned fixture/proof/window compiler and run groups were cleaned and
independently verified absent. The companion JSON binds outputs and source hashes.
Product/seated sources and intentionally failing inventory WIP remain untouched.
Plan: `.context/strong-owl-live-physics-plane-reuse-proposal/PLAN.md`.
