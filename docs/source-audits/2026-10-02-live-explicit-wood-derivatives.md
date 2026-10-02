# Explicit selected-branch wood derivatives

The prior direct second-order AD screen passed fidelity but failed its fixed
2 ms derivative-corpus gate at 9.134 ms. This successor replaces generic AD
propagation with the distance-envelope Hessian Hxx - M inverse(B) M^T over at
most two free closest-point parameters. It retains the native triangle/segment
witnesses, ordering, clamp/parallel branches, ties and internal boundary metadata.
The mixed rope-fraction derivative includes n dot (DB - DA); omitting it loses
moving-witness and negative curvature. Point-face distance has zero Hessian.

Only interior stationary native parameters are eliminated. Normalized parameter
stationarity must meet the existing 1e-10 gradient comparison threshold; invalid,
singular or nonfinite cases reject. No denominator floor, pseudoinverse, damping,
force sign change or curvature clipping. Shared-height endpoint seeds remain the
inverse-rotated -up for free/support endpoints and zero for attached endpoints.
Selected-branch derivatives do not establish global smoothness at boundaries.

## Fixed result

All 418 retained wood features from failed Clavellium updates 0 and 15, including
six exact candidate-tie rows, match the independently verified AD reference.
Maximum normalized Hessian difference 8.07e-15 (limit 1e-4), gradient difference
1.98e-14 (limit 1e-10), distance difference 6.94e-18 m (limit 1e-12). Native witness
metadata is identical; original gradient difference remains 1.87e-11. Maximum
normalized free-parameter stationarity is 5.14e-15. There are 108 zero-, 112 one-
and 198 two-parameter primary branches. Deterministic replay records are identical.

Cost FAIL: complete cold corpus 2.06154 ms versus the fixed 2 ms gate; replay
1.88213 ms does not change that verdict. Native selection plus original authority
crosscheck costs 0.297 ms, explicit derivatives 0.649 ms. The same whole-clock
AD-to-explicit corpus comparison is 4.43x; derivative-bucket comparison 12.08x.
Neither is frame, complete-geometry, QP or device performance. Decode/typed packing
precedes timing; board transforms/seeds, selection, authority crosscheck,
derivatives and trace construction are inside; serialization follows timing.

Configuration CLOSED without rerunning or adjusting timer, cap, thresholds,
containers or input. No full-step integration or app adoption. Both old plane
failures are corrected in the verified reference; that does not prove they caused
the prior full-step convergence failure. Eight fixture groups passed after an
intended behavioral stub failure, including literal two-free-parameter negative
curvature, AD agreement and singular elimination rejection. Two compile failures
from Swift operator whitespace/type inference were corrected before measurement;
they are retained, not represented as behavioral REDs. Astra reviewed the formula
and required strict native projected-parameter interior checks before the corpus.

All eight fresh compile/run groups and five drivers were cleaned and verified
absent. No app, CAD, seated-cord, renderer, physical gate, CCD, branch/workspace or
PR529 changes. Existing failing live inventory test remains untracked. Broader
Python/Xcode suites were not rerun; no whole-suite green claim.

Evidence is `.context/strong-owl-live-physics-explicit-wood-curvature`; companion
summary binds input/reference hashes, preregistration, sources, outputs and exact
resource receipts. The next discriminator is read-only finite-step residual
remainder on the already retained late direction and trials, because late
admission is zero and infinitesimal Hessians pass. It must not compute a new
direction or rescue the closed full-step configuration.
