# Direct selected-branch wood derivatives

User asked whether work was being abandoned. It continues with a derivative-only
discriminator, before another coupled nonlinear solve. The preceding numerical
wood stencil failed two initial plane-contact Hessians and cost 71.989 ms in a
complete sixteen-update call. This screen checks direct differentiation against
the actual retained failures; it does not rerun or tune the closed full solver.

The native private triangle/segment/ray primitives and strict winning-candidate
ordering remain authority. A fresh snapshot adds metadata for triangle regions,
clamping and parallel branches. Second-order forward automatic differentiation
then evaluates only the selected mathematical distance branch. Closest fractions
and barycentrics move with their formulas. An interior point-face branch uses the
equivalent absolute plane distance, whose Hessian is exactly zero. Shared height
seeds inverse-rotated -up for free/support endpoints, zero for attached endpoints.
No physical radius, material, collider, contact rows, trial merit or CCD changes.

Six fixture groups observed behavioral RED/GREEN: vertex/shared height, plane,
edge, moving whole-link witness (including negative curvature), internal triangle
boundary without an inter-candidate tie, and intersection rejection. Astra reviewed
AD arithmetic, branch preservation and moving-witness signs. The review identified
that candidate ties alone do not cover internal region/clamp boundaries; exact
predicate boundary flags were added and verified before the corpus run. No
branch averaging or unique-Hessian inference from an empty tie list is allowed.

## Fixed corpus result

All 418 wood contacts from retained Clavellium iterations 0 and 15 pass the fixed
derivative fidelity checks. Native winning witnesses match the original helper.
Maximum distance error 3.12e-17 m (limit 1e-12), gradient error 1.87e-11 (limit
1e-10), independently recomputed selected-branch normalized Hessian difference
4.50e-9 (limit 1e-4). The independent oracle uses different closest-branch gradient
formulas and a fixed central derivative; it does not mirror the AD arithmetic.

Both previously failed initial plane contacts now return zero Hessian exactly.
Their later edge-contact Hessians also pass. Six exact inter-candidate tie rows
were differentiated separately and checked; none has a differing gradient under
the fixed comparison. No internal predicate boundary is flagged in this corpus.
That does not prove general smoothness: the synthetic boundary fixture explicitly
records a case with differing neighboring Hessians. The verdict is selected-branch
derivative fidelity, not a global differentiability or solver convergence theorem.

Cost FAIL: 9.134 ms cold, 8.892 ms identical replay versus the fixed 2 ms derivative
checkpoint. Native selection plus original-witness crosscheck 0.291 ms;
differentiation 7.834 ms. Whole-clock time includes affine transforms/seeding and
trace construction. JSON decoding/typed input packing precede the clock; JSON
serialization follows it. This is neither complete geometry nor a cold contact QP.
No comparison to the former 71.989 ms whole-step bucket is a valid measured speedup:
the workloads differ. The AD implementation is a verified reference, not adopted.

Configuration CLOSED on cost with no kernel/container/stencil/threshold tuning.
No full dynamics, app, seated-cord, model, renderer, device, trajectory or original
PR529 change. Six fresh compile/run groups pairs and their drivers were cleaned
and checked absent. The existing failing inventory test remains untracked WIP.
Broader Python/Xcode suites were not rerun for this standalone native prototype;
no whole-suite green claim is made.

Evidence and premeasurement plan are in
`.context/strong-owl-live-physics-direct-wood-curvature`. Companion summary binds
SHA-256 for retained inputs, source snapshots, outputs and exact-resource receipts
(module cache excluded). The reference now permits checking a cheaper explicit
curvature formula without guessing whether moving-witness terms were omitted.
