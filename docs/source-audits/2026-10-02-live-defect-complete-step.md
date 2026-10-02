# Full-step nonlinear defect correction

The previously isolated full KKT defect correction now runs inside the native
nonlinear prototype's complete correction loop. It remains outside the app.
The loaded Clavellium checkpoint still **rejects** within the unchanged
sixteen-update cap. The original app solver and seated cords are unchanged.

`NonlinearKKTDefect` reconstructs the complete finite-step residual remainder
from the iteration-origin condensed matrix, Jacobians, forces and slacks. It
solves one extra right-hand side using that existing factor and certifies all
four recovered linear equations. The correction is added once to the rejected
proposal, without another alpha, centering term, clamp or correction.

The opt-in `HANGTEN_NONLINEAR_DEFECT=1` prototype attempts this only after a
finite, geometrically valid ordinary trial fails Armijo. Each ordinary trial
gets at most one correction and one corrected evaluation. Positivity is checked
against 0.005 of the iteration-origin force/slack, combined displacement against
the existing 0.1 relative-link trust bound, then original topology, sign and
Armijo checks. A failed correction restores the entire iteration state before
ordinary halving. The policy permits up to 256 extra right-hand sides and
corrected evaluations; their costs are additional work.

The existing sixteen ordinary trials per update, sixteen updates, one-second
work budget and ten-second failsafe remain unchanged. The initial plan called
the failsafe a work budget; this was clarified before measurement. Curvature,
normalization, regularization, material, geometry, final numerical/physical
checks, global merit, swept collision and rollback were unchanged.

## Verification and outcome

The helper's missing implementation first failed its native fixture. The
implemented helper then passed hand-derived curved-contact equations, including
the mixed force/geometry term, and matched the independently retained loaded
correction's x/s/v arrays within 1e-12. Five existing primal-dual fixture groups
also passed, including shared-height and nonlocal coupling. Astra found no
concrete sign or restoration defect in the helper or its integration.

The complete candidate and deterministic replay took 235.240 and 220.075 ms
on the host, including diagnostics; the accepted original control took
51.905 ms. The candidate made 21 extra RHS solves, no extra refinement solves,
ten corrected evaluations and seven accepted corrections. Whole-state and
proposal-trace replay were byte-identical. Both candidate failures restored the
complete checkpoint exactly.

The final discarded proposal passes the static physical diagnostic: strain
0.017076%, material error 0.007727 mm, clearance 3.592582 mm, and preserved
topology. Numerical stationarity 1.732e-7, equality 3.400e-7, gap -7.418 µm,
complementarity 2.671e-10, internal complementarity 2.479e-10 and last movement
28.493 µm still fail their original limits. No candidate state was published;
successful whole-motion CCD and accepted motion remain unproven. This complete
configuration is closed without cap or tolerance tuning.

## Measured remaining mechanism

An exact retained-output decomposition recovers each previous accepted trial's
score by removing only newly initialized rows from the next iteration's
residual calculation. Positions are identical across admission; this is an
analysis, not a changed solve or omitted-constraint acceptance.

At iteration 16, a newly admitted point row has positive C = 41.910 µm but
receives 3.5 mm slack, h = -3.45809 mm and s*v = 2.439e-10. Its initialization
raises the score from 71.565 to 123.125. The increase consists of 1.976 in its
constraint terms and 49.584 in stationarity, including cross terms with the
existing force residual. Four separated rows at iteration 13 raise the score
from 162.913 to 273.287, mostly through a 102.485 stationarity contribution.

This supports a separately specified admission-initialization discriminator;
it does not identify the sole blocker. An existing row still has greater
complementarity, and other final residuals fail. Keep the original `scale` and
`initialS` normalization when comparing initialization changes so score changes
cannot come from changing its denominator. The earlier finite-difference wood
Hessian limitation also remains unchanged.

Fresh evidence is under `.context/strong-owl-live-physics-defect-step/`.
All eight created command groups and completed driver processes were absent.
No simulator or server was started. [Evidence hashes](2026-10-02-live-defect-complete-step-summary.json)
bind the fresh sources, inputs, outputs and lifecycle checks. Full-step,
trajectory, device performance and catalog acceptance remain incomplete.
