# Region-bound arithmetic checkpoint — 30 September 2026

The optional `--regions --fast-boxes` pilot addresses the arithmetic cost left
by the [pre-generation experiment](2026-09-30-live-pre-generation-contact.md).
It replaces repeated per-operation outward rounding of region AABB distance
with one SIMD squared-gap calculation and a conservative absolute margin.
The original triangle mesh, sign, whole-segment tests and uncertain-leaf
fallback remain unchanged. No geometry backend is adopted by the application.

Every input coordinate and the mesh root bounds are at most 10 metres in
magnitude. Thus exact gap components are at most 20 metres and their squared
sum at most 1,200 m². With binary64 unit roundoff `u = 2^-53`, the component
perturbation contributes at most `2400u + 1200u²`; the dot contributes at most
`gamma_5 * 1200 * (1+u)²`. Include `(1200+2e-12)u` for the final subtraction.
The combined bound is 1.065814104e-12 m². Subtracting 2e-12 m² therefore gives
a conservative lower bound. Underflow cannot exhaust the margin; fused
arithmetic improves the bound. Root bounds enclose every child and triangle.
This derivation covers region-box arithmetic, not the separately unresolved
general floating triangle-kernel certificate.

All eight geometry fixtures pass. One production replay independently checks
all 119,693 original generated wood inequalities and all 119,781 retained
frozen support rows. Every one of 2,858 queries is clear, minimum checked
original affine gap 3.182306 µm, with zero omitted multipliers. Candidate time
is 50.061 ms versus 195.315 ms original wood generation: one host sample,
3.902×, excluding the other geometry work and solver. There is no p95,
complete 50× geometry, motion or device proof. It fails the cost checkpoint
and is not expanded to 50 repeats. Review found no correctness issue with
the arithmetic derivation or flag propagation.

A separate ordinary-float pruning ceiling combines retained one-sided global
CAD patch envelopes with whole-segment midpoint/Lipschitz bounds and actual
patch AABBs. All 42,796 source triangles belong to exactly one retained patch.
For the same candidate it could cover only 1,784 of 2,858 queries and 40,250
of 119,781 wood/portal support rows. This supplies no sign or floating-kernel
certificate and is not a timing experiment. Ruling: do not reopen the closed
global-envelope adapter. A possible bounded successor would need smaller
trimmed regions and per-region envelopes; first discriminate its coverage
before writing or adopting a runtime index. No tolerances were increased.

The [manifest](2026-09-30-live-region-bound-cost-summary.json) binds immutable
compiled sources, inputs, results, arithmetic/ceiling evidence and verified
exact owned cleanup. All earlier numerical, geometry and device limits remain.
