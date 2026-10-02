# Direct portal Hessian in the coupled nonlinear screen

The user asked for a working demonstration. Three bounded native configurations
were implemented in this continuation, preserving the original acceptance gates.
None produced a newly accepted dynamical step or an app demonstration. The earlier
recording is not evidence of these solver experiments. Seated cords remain available.

This final configuration is CLOSED. It replaces the invalid finite portal probe
with the direct rational Hessian of its eroded-aperture constraint, evaluated at
the current valid material segment. It retains centrally differentiated wood
curvature, all signed length curvature, compression/slack predictor-corrector,
all coupled coordinates/shared height, and original predictor/discovery/trials.
No aperture, radius, material, force scale, cap, timestep, threshold or gate changes.

For U=np·(center-a), E=inward·(b-a), D=np·(b-a), N=UE, the nonlinear part is N/D.
Its Hessian is Nij/D-(Ni Dj+Nj Di)/D²+2N Di Dj/D³. Affine endpoint/height changes
give Nij=Ui Ej+Uj Ei. Free/support height derivatives in board coordinates are
inverse-rotated -up; attachments are zero. The direct Hessian rejects a tangent or
out-of-segment current crossing, and original trial refresh governs migration to
neighboring segments. It does not manufacture an invalid perturbed portal state.

## Matched result

One candidate, identical replay and original control start from the exact accepted
full Clavellium 60-step checkpoint. Original dt=1/240, sixteen common updates,
sixteen trials per update, one-second candidate bound and all original final gates.
Candidate 229.044 ms/replay 227.246 ms reject at the update cap; control accepts
52.769 ms. Sixteen factors, 32 solves, no refinement, 45 trials. Final 520 terms:
279 lengths, 121 point/112 link triangle features, eight portal boundaries; self
and intercord discovery remain present but are not exercised by this single loop.

The rejected proposal's static diagnostic passes: 0.203316% strain (limit 0.5%),
0.0912111 mm material-length error (limit 0.5 mm), original whole-segment mesh
clearance 3.523457 mm for radius 3.5 mm (required >=3.45 mm), topology valid.
This diagnostic is outside the candidate timer. It is not an accepted motion step.

Stationarity 1.64386e-7 fails 1e-10; regularized equality 4.04877 um fails 0.01 um;
contact C/gap -76.54307 um fails the original numerical certificate;
complementarity 2.92563e-10 fails 1e-14, internal 1.62894e-10 fails 1e-18.
Last movement 16.3202 um fails 0.01 um and strain fails original 0.02% convergence.
Final original global-merit certification and complete-motion CCD were not reached.
The entire rejected state rolls back. No rejected geometry is published to the app.

Timed assembly 79.151 ms includes 71.989 ms curvature construction; factors
25.595 ms, solves 3.525 ms, discovery 30.412 ms. These partial buckets do not sum
to the whole call. The whole host call includes trace construction and excludes
subsequent JSON serialization. No device, trajectory, halfstep, bearing, production
Mini, speed-readiness or catalog-live claim follows.

## Verification and failed derivative oracle

The literal rational/shared-height Hessian fixture observed behavioral RED then
GREEN. Valid near-endpoint derivatives and out-of-segment/tangent rejection pass.
Full integration compiled. Astra reviewed quotient algebra, signs, shared-height
incidence and current-branch limits before measurement.

Independent all observed length/triangle/portal residuals agree to 3.82e-17 m;
original mixed-matrix products to 8.13e-19; recovered original equations to
8.67e-19; common position/force/slack updates to 1.38e-17. Raw matrices and
symmetrization are retained. Proposal replay is exact after excluding elapsed
timers; complete returned checkpoint is byte-identical.

The separate independent curvature oracle FAILS its fixed normalized 1e-4 gate
on two initial point features: point:0:92:5070 (0.00135436) and
point:0:187:5068 (0.00105341). Of 193 initial contact Hessians, these two fail;
all 241 final-direction Hessians pass, maximum normalized difference 3.55e-7.
The locked fail-fast oracle remains unchanged. A separate comprehensive report
uses the same comparisons/threshold, records every failure, and exits 1. No
threshold or stencil adjustment rescues this result. The actual fixed central
stencil is 6.055454452e-9 m; earlier advisor shorthand of approximately 12 nm was
incorrect. Successful mixed equations do not prove the curvature approximation.

Evidence, premeasurement plan, source snapshots/binaries, outputs and cleanup
receipts are under `.context/strong-owl-live-physics-portal-curvature`. Companion
summary binds their SHA-256 hashes (module cache excluded). All exact fresh owned
groups/drivers were verified absent. No app/CAD/renderer/server/simulator changes,
shared/historical resources, original workspace or PR529 were touched. The known
untracked failing inventory test remains WIP. Broader Python tests were not rerun;
no whole-suite green claim is made.
