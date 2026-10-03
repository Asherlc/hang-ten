# Original floating edge-witness bounds

This native-only screen bounds the original computed segment-pair witnesses,
then omits an edge only when its lower bound cannot beat either running row or
merit witness. The interpolation box ends at `a + (b - a)`, rather than raw `b`:
rounded subtraction and addition can reconstruct a point outside the raw
endpoint box. Nonfinite bounds retain the original calculation. This mechanism
does not depend on the separately rejected feature-agreement census.

The single-type optimized IR retains separate multiply/add interpolation and
the same squared-length reduction in the bound and original witness. Cross/ray
math still contains unchanged `llvm.fmuladd`; there is no blanket no-FMA claim.
The independent advisor found no blocker in these specific arithmetic conditions.

All 18,000 finite primitive cases passed, with rounded-endpoint RED, tie and
nonfinite controls. All 934 query and 2,802 swept-output bit checks passed, as did
20 strict paired steps, conservative clearance receipts and transaction rollback.
The 139-step prefix and seven complete step-140 pairs retained exact physical
checkpoint and correction schedule identity: two corrections, no caps or retries.

The median complete-step ratio was **0.846527** against the original and
**1.088166** against the matched unrolled control. Both had to be **≤0.80**.
This is **FAIL/CLOSED**: the predicate did not demonstrate the required saving,
and adds cost relative to the control that removes the necessary edge array.
There is no timing retry, predicate tuning, combination with rejected candidates,
540-step expansion or product adoption. The adjacent JSON retains both controls,
compiler proof, input hashes and independent deletion checks for all seven owned
child process groups. No simulator or real-time improvement follows.
