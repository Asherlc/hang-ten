# Curvature-complete finite-stencil screen

Following the independent contact-curvature diagnosis in the nonlinear primal-dual
audit, a separate configuration included all signed length curvature and centrally
differentiated actual-contact Jacobians. The stencil was fixed before measurement:
cbrt(Double.ulpOfOne) times minimum rest length. No physical/numerical gates,
predictor, cold initialization, barrier, cap, trust, line search or timestep changed.
Structural free-coordinate and shared-height derivatives were retained; raw and
symmetrized Hessians were specified. Existing local band LU can factor indefinite
matrices; the nonlocal sparse fallback retains rows but may reject pivot signs.

This configuration is CLOSED: the loaded native Clav checkpoint rejected during
curvature assembly, before any Newton factor/direction/update. Candidate 31.0405 ms,
identical rejection replay 9.04704 ms, matched original control accepted 105.220 ms.
These single-run timings are not comparable performance claims.

The actual predictor's portal fractions are 5.736609e-6 and 0.999994263 on adjacent
links. An endpoint is within the fixed stencil width of the portal plane. A central
probe leaves the current material segment, causing the original boundary derivative
to reject “Missing portal crossing.” No smaller stencil, clipping, omitted portal,
adapted cap or permissive physical trial was substituted. This is an invalid
derivative construction at this checkpoint, not a measured failure of a completed
curvature Newton direction.

Synthetic vertex/shared-height curvature, zero interior-plane curvature and invalid
input fixtures observed genuine behavioral RED then GREEN. One first mislabeled
RED stage ran the unchanged older core fixtures; the fresh preflight ledger records
that error, and it was not used as RED evidence. Full integration compiled. Astra
reviewed signed assembly, state restoration, central indexing, finite validation,
symmetrization and raw derivative retention before the physical run.

Independent 472-feature prediction residuals agree to 3.08e-17 m. The whole rejected
checkpoint and proposal trace replay are exact after excluding elapsed timers.
The initial prediction fails strain, so no accepted motion results. Final original
global-merit and whole-motion CCD were not reached. The independent Hessian oracle
has no completed direction to inspect; generic validator zero matrix/equation
residual fields mean zero checks, not successful solver certification. In-flight
partial curvature matrices were not retained after the assembly exception.

No app, seated-cord, geometry, renderer, device or trajectory changes. Fresh owned
groups/drivers were verified absent. Evidence and fixed contract are in
`.context/strong-owl-live-physics-curvature-newton`; the companion summary binds
their SHA-256 hashes, excluding module caches. This points to a direct portal
derivative evaluated at the current valid crossing as a distinct successor, rather
than manufacturing perturbed portal states to estimate its Hessian.
