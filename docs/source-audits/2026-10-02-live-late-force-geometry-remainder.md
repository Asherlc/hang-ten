# Late nonlinear force–geometry remainder

This read-only discriminator explains backtracking on one already retained
update-15 direction from the rejected direct-portal/central-wood solve. No new
direction or trajectory is computed. Late iterations 9–16 admit no new rows;
the fixed row set and scales rule out admissions as the immediate late blocker.
The infinitesimal last-iterate Hessian oracle previously passed.

Original native closest witnesses and branch metadata were recomputed on the
baseline and all five recorded trials (1,398 wood records). Independent Python
rows reproduce native C to 3.43e-17 m and J to 7.01e-14. Full original residual
scores match to 4.23e-13 relative; world-state updates match exactly. For wood,
the local Hessian comes from the validated explicit corpus; direct portal matrices
come from the independently checked retained output; length Hessians are computed
from the original norm. Closed derivative cost configurations remain unchanged;
this reuses mathematical outputs as an audit reference, not as solver adoption.

For each signed force lambda, split the finite-step stationarity remainder into:

- geometric: lambda (Jtrial - J0 - alpha H dx);
- force–geometry: alpha dlambda (Jtrial - J0).

Mass terms are linear. Sum these contributions with the original signs and
mass/rest scaling. Reconstructed stationarity remainder matches the independently
computed actual-minus-linear residual to 1.25e-12 normalized. Complementarity's
exact alpha-squared ds dv term is accounted separately.

| alpha | local linear residual score | actual score | geometric remainder norm | force–geometry remainder norm | wood branch changes |
| --- | ---: | ---: | ---: | ---: | ---: |
| 0.477458 | 119.465 | 16299.878 | 0.6420 | 119.4877 | 2 |
| 0.238729 | 252.131 | 1833.222 | 0.1472 | 29.8606 | 0 |
| 0.119364 | 337.066 | 591.934 | 0.0368 | 7.4631 | 0 |
| 0.059682 | 384.184 | 440.820 | 0.0092 | 1.8655 | 0 |
| 0.029841 | 408.906 | 422.833 | 0.0023 | 0.4663 | 0 |

Norms use the unchanged stationarity scaling; scores also include equality,
contact feasibility and complementarity. Initial score 434.403 has stationarity
430.366. At the first two trials, force–geometry interaction projects 99.9523% and
99.9407% onto the total remainder. The length/wood projection split is about
55%/45%; portal interaction is about 0.002%. Projections, rather than adding
individual norms, account for vector cancellation. The exact complementarity
quadratic term barely changes the predicted score. No portal material segment
changes occur. Branch transitions cannot explain the second and later trials.

This local evidence identifies a smooth finite-step changing-force/changing-J
interaction as the immediate late backtracking cause. It does not prove that a
correction will converge, meet performance, or preserve a whole trajectory. Astra
reviewed the interpretation and distinguishes any future full nonlinear KKT
defect correction from stock IPOPT feasibility SOC. The primary reference is
[Wachter–Biegler section 2.4](https://optimization-online.org/wp-content/uploads/2004/03/836.pdf);
its method reuses a factorization but corrects constraint feasibility. No filter,
inertia correction or convergence theorem is claimed for our residual formulation.

Audit checks PASS under preregistered agreement limits. All three fresh groups and
two drivers were cleaned and checked absent. No new solver/app/CAD/render/device
or accepted-motion result. No full Python/Xcode suite rerun; the existing live
inventory test remains untracked WIP. Evidence, provenance, raw vectors, per-feature
remainders and exact-resource receipts are in
`.context/strong-owl-live-physics-late-residual-remainder`; companion SHA summary
binds them and the standalone analyzer. A future direction requires a separate
bounded checkpoint; it is not computed by this audit.
