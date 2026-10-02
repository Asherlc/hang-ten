# Coupled nonlinear primal-dual screen

User authorized demonstrating the complete nonlinear coupled solver. This screen
updates positions, shared height, signed length tensions, contact compressions and
slacks together. It does not solve an inner frozen contact QP to completion first.
The committed app and seated cords are unchanged. This configuration is CLOSED.

The original exact accepted Clavellium 60-step checkpoint, predictor, masses,
material, 3.5 mm radius, sliding portals and full actual-mesh point/link discovery
were retained. All admitted features persist. Self/intercord discovery is present;
neither is exercised by this single-loop checkpoint. Original final numerical,
physical, convergence, global merit, whole-motion CCD and rollback gates remain.
Sixteen common updates, sixteen trials per update, one-second candidate budget;
no adaptive timestep retry, warm forces, tolerance/cap change or product adoption.

The infeasible-start Mehrotra predictor/corrector uses the original mass backbone
plus positive length tension curvature. Contact curvature is omitted: this is
quasi-Newton. One mixed chain/equality/height factor serves two right-hand sides.
Nonlocal rows select a sparse fallback rather than being dropped. Strict positive
compression/slack fractions and original relative-material trust share one alpha.
Exact nonlinear scaled residual Armijo checks use fixed row sets and zero
complementarity target. Discovery between updates changes the residual function;
the overall residual-score decrease is not a fixed-objective convergence proof.

## Measured result

Candidate 175.009 ms; identical replay 173.344 ms; matched original control
55.152 ms accepted. Sixteen updates and 56 trials, 16 factors, 32 solves and zero
refinement solves. Final 529 features: 279 length, 128 point/114 link triangle
contacts, eight portal boundaries. Timed assembly 6.452 ms, factors 20.266 ms,
solves 3.660 ms, discovery 33.226 ms. These are partial buckets; the 175.009 ms
whole call includes trace construction and excludes later JSON serialization.

The rejected proposal passes the static physical diagnostic: strain 0.353316%
(limit 0.5%), material error 0.0659895 mm (limit 0.5 mm), actual whole-segment
clearance 3.502251 mm (required >=3.45 mm), topology valid. Diagnostic measurement
occurs after the candidate timer. It is not an accepted dynamical step.

Final stationarity 3.45694e-7 exceeds 1e-10; regularized equality 6.46040 um
exceeds 0.01 um; contact residual/gap -97.7492 um fails original numerical
constraints; complementarity 1.70384e-10 exceeds 1e-14, internal 2.75047e-10
exceeds 1e-18. Last movement 0.949616 um exceeds 0.01 um and strain exceeds the
original 0.02% convergence stop. Global final-merit certification and whole-motion
CCD were not reached. The original transaction restores the entire checkpoint.
No rejected positions are published to the app. Host time is about 3.17 times the
matched control; no phone performance or live-readiness claim follows.

## Verification and local diagnosis

Five kernel fixture groups observed behavioral RED then GREEN: four original
equations with nonzero contact infeasibility, corrector cross-term recovery,
signed tension/shared height, nonlocal coupling, positivity/invalid inputs.
Current full native integration compiled. Independent Python checks every
observed length/actual-triangle/portal residual to 3.56e-17 m, original Newton
matrix products to 3.25e-19, recovered original equations to 8.67e-19, and common
position/force/slack updates to 1.30e-17. Proposal trace is identical on replay
after excluding elapsed timers; returned checkpoint is byte-identical. These
checks use retained Jacobians; a separate independent derivative probe follows.

Astra found and reviewed a pre-run interrupted-admission defect. Alignment guards
prevent deferred rejection handling from indexing uninitialized slacks. A fresh
negative source fixture throws after two admissions before initialization: safe
partial trace, no crash, exact rollback/replay, untouched control accepted.

At retained update 15, admissible alpha 0.480718 backtracks eight times to
0.00187781. Stationarity contributes 99.4% of score. Independent reconstruction
of triangle witnesses/normals and portal plane-intersection derivatives agrees
with baseline Jacobians to 2.48e-14. Centered score slopes at fixed alpha
1e-4/1e-5 are about -43.8799 versus predicted -2918.1552. Contact geometric
curvature contributes +2874.2753; discrepancy after adding it is about 1.55e-5
at alpha 1e-5. Witness labels do not change and portals remain inside the same
material segments. All length tensions are positive there. Astra independently
reviewed this probe: omitted contact curvature explains the LOCAL loss of
predicted descent magnitude. Actual slope remains negative. This does not prove
that adding curvature yields a converged or faster step.

Evidence, premeasurement contract, fresh snapshots/binaries, outputs, independent
checks and exact-resource deletion receipts are under
`.context/strong-owl-live-physics-nonlinear-primal-dual`. The companion summary
binds SHA-256 for the retained inputs and evidence (module cache excluded). All
fresh owned process groups and drivers were checked absent. No servers,
simulators, shared/historical resources or original PR529 were touched. No app,
geometry, renderer or broader Python-suite acceptance claim is made.
