# Pre-update terminal stationarity: closed

This isolated convergence screen retains the fresh original coupled QP and
attempts to stop at the already accepted iterate, avoiding only its tiny terminal
update and new geometry/merit evaluation. Eligibility resets every physical
advance and requires the most recent applied correction and proposed trust
fraction both equal one, current strain below .0002, and fresh full correction
below the unchanged phase limit. A distinct stationary status preserves the
proposal norm; no unapplied proposal is claimed to have passed merit. Physical
metrics, CCD, velocities, history and rollback remain original.

Eligibility boundary/epoch/damping/nonfinite RED/GREEN fixtures passed. The
independently propagated current control and candidate passed all physical
checks through 139 steps, with maximum pose/height difference **13.558 µm**.
Only **eight** steps used the terminal stop. The first fixed step-140 pair
failed its required terminal-stop work-count condition, so the seven-pair speed
gate was not reached. This is **FAIL/CLOSED**, not a measured speed improvement.

A separate no-timer diagnostic explains the rejection: both solvers perform two
fresh QPs, but the candidate uses zero terminal stops. Its second proposal is
2.774 µm, below the arrived 4.167 µm limit; current strain is **.000213078**,
above the unchanged **.0002** stop gate. The ordinary second correction must
still be applied. The diagnostic is not a timing retry or new acceptance screen.

No strain threshold, eligibility condition, fixture or speed gate was changed.
No 540-step expansion or product adoption follows. The adjacent JSON retains
both runs, exact inputs, proposal diagnostics and independent deletion checks
for the four owned child process groups. Product physics remains 597333b47.
