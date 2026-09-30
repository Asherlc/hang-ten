# Packed immutable contact source

This is a bounded successor to the
[reviewed streaming experiment](2026-09-30-live-streamed-contact.md), addressing
repeated construction of frozen affine rows. The native replay tool now accepts
`--packed`. The app backend, all physical/numerical gates and catalog profiles
remain unchanged. The [summary](2026-09-30-live-packed-contact-summary.json)
binds the fixed inputs, code, results and ownership snapshots to SHA-256 hashes.

The packed source validates and captures every original row once. It retains
row order, coefficients, references, border terms and residuals, including
initially clear rows. Subsequent certificates scan every packed inequality in
the same floating-point operation order as the streamed implementation, using
the existing `1e-10` regularized-contact threshold. Variable-reference groups
select initial representatives only. No row is inferred redundant. Only
admitted rows become working-QP inputs; the 100,000-row working budget and
existing iteration, dimension, nonlocal/border and entry guards stay intact.
Packing happens inside each cold measurement, never as an unreported warmup.

A capture-count fixture failed against the prior stream (producer visits
`[5,4]` instead of `[1,1]`) and passed with packing. All 15 context fixtures
using the packed path pass, including the late, initially clear inequality
beyond row 100,000, malformed clear rows, joint loop/height coupling and strict
contact certification. The tracked tool's 15 numerical fixtures and four real
lifecycle tests pass. Focused review found no issues in the packed changes.

| Fixed replay through the tracked tool | Numerical checks | Shared-host time |
| --- | --- | --- |
| Original hard QP, 50 cold runs | Strict full-matrix residuals pass; oracle difference 0.866 µm; 8 admissions end at 402 rows | p95 225.272 ms |
| Production Mini first correction, one cold run | All 119,953 inequalities checked; strict residuals pass; 158 working rows | 151.907 ms; no p95 |

Both runs explicitly reject the 2 ms cold-QP performance gate with exit status
`3`. Host load and compilation differed between experiments, so these figures
do not establish a controlled speedup over the prior 295.673 ms p95 and
231.229 ms single sample. The row-construction hypothesis is confirmed by the
capture-count fixture; the performance hypothesis still fails its fixed gate.
The packing option stays unadopted in the app. A context prototype's completed
50-run replay is retained separately; the tracked tool results above are the
reviewable operator measurements.

One preliminary context replay is explicitly excluded: a source dimension
guard changed while compilation was pending, so the exact built source could
not be bound to that provenance. Its log/report remain under
`packed-frozen-rows/hard-unbound-build/` with a rejection record. A fresh
unchanged-source replay was then run, and final source hashes were verified.
This was an evidence-binding correction, without changing the workload, gates
or resource caps.

This experiment changes frozen contact representation only. Triangle contact
generation, sign classification, whole-segment CCD, full nonlinear merit and
verification remain authoritative and still cost too much. It establishes no
50× complete-geometry result, settled Mini trajectory, CAD tessellation error
bound, iPhone performance or live-catalog readiness. Seated cords remain
available. All exact resources created for this screen were deleted and
verified; no Simulator, device installation or server was created.
