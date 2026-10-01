# Nonlinear primal rope experiment, 1 October 2026

**The tested configuration fails physical strain and final numerical convergence.**
It makes reproducible nonlinear progress and passes its final merit guard, unlike
the previous frozen inexact directions. It takes152–165ms; the same complete
original control accepts in56.805ms. Nothing is adopted into the app. Live settling
and the device performance gate remain unfinished; seated cords remain available.

The user's "Try it" followed the [primary-source research](2026-10-01-live-rope-web-research.md)
proposal, including the distinction between intermediate frozen-QP certificates
and nonlinear positional iterations. This authorizes this isolated adaptation,
not a physical tolerance change. PR529/original workspace are untouched.

## What was implemented and fixed before measurement

The prototype alternates current-position three-coordinate particle updates and
one shared board-height update with shared constraint multipliers/finite penalties.
It retains complete material chains, physical radius/masses/rest links, the
original predictor, sliding portal crossings and wood/self/intercord terms.
All admitted features remain for the step; discovery repeats each sweep and
before final certification. Each admitted triangle/whole-link distance and its
gradient follow current geometry, with the actual original facet as authority.
Distinct normals/material fractions are preserved under original manifold merging.
Intercord features retain the original clipped material-piece/knot bounds.

This is an unshifted, unwarmed adaptation, not stock AVBD or the closed16-sweep
frozen response algorithm. With original epsilon=1e-8, the augmented force is

    t = (lambda + rho*C)/(1 + rho*epsilon)

clamped to<=0 for contacts. Position energy is the corresponding squared
numerator divided by2*rho*(1+rho*epsilon); its gradient is t*J. Local SPD
Gauss–Newton curvature is rho/(1+rho*epsilon) on the active branch. The fixed
point preserves original regularized equality/complementarity. Penalties start
from the inverse effective mass across every free coordinate and shared height;
the exact prewritten ramp, cap1/epsilon,16sweeps and16local trial limit are bound
in the retained PLAN. Duals/penalties remain fixed throughout a primal sweep.
No previous-error offset or force warm start is injected.

Astra reviewed the derivation and implementation read-only. Before execution we
fixed structural height incidence even when an initial derivative vanishes,
rejected zero-distance/intersecting unsigned features rather than inventing their
gradient, described the original10%relative-link trust bound as applied **per
block**, and checked the1s budget after final guards before transaction publication.
The cumulative sweep is not claimed to obey a single10%trust bound.

Old frozen certificates are not intermediate iteration invariants here. Final
nonlinear stationarity uses stored updated lambda, not another augmented force
evaluation. Original numerical residual thresholds, original final global L1
merit, .02%strain/10nm movement convergence, physical strain/material/clearance,
topology, swept collision and transactional publication remain guards. Candidate
adaptive-dt rescue is disabled. No measured cap, penalty, tolerance or fixture
was changed to rescue a failure.

## Matched complete-step results

Input: the exact full accepted60-step Clavellium loaded checkpoint,280particles,
279links,7mm cord diameter and10,200original triangles. Restoration is byte
identical and physically preflighted before measurement. This is one Clavellium
loop, not a production-resolution Mini or loaded two-loop trajectory.

| Check | Nonlinear candidate / replay | Original matched control |
| --- | --- | --- |
| Complete host call |164.615 /152.469ms |56.805ms |
| Result |Reject and restore complete checkpoint |Accept |
| Maximum strain |0.984184% |8.34533e-8% |
| Material error |0.329422mm |2.30039e-7mm |
| Original whole-link clearance |3.599589mm |3.599999999544mm |
| Topology |Valid |Valid |

The rejected proposal's wood clearance and material error pass their physical
limits, but **strain exceeds the0.5%physical limit**. That independently rejects
it even if stricter numerical stopping rules were removed.

All16sweeps finished inside the wall bound. There were4,464local updates per run;
each accepted its first trial. Features grew472→493:279length,95point wood,
111whole-link wood and8portal terms. The final terms have no self/intercord rows;
generic handling exists, but this checkpoint cannot validate loaded nonlocal
coupling or joined-knot trajectories.

| Final nonlinear check | Measured | Required |
| --- | --- | --- |
| Stationarity |8.70518e-11 |<=1e-10, pass |
| Regularized equality residual |19.5987µm |<=0.01µm, fail |
| Minimum contact C |−0.411451µm |>=−0.01µm, fail |
| Minimum regularized gap |−0.411451µm |>=−0.0001µm, fail |
| Compression sign |Nonpositive |Pass |
| Complementarity |2.67482e-16 |<=1e-14, pass |
| Last sweep movement |4.42990µm |<0.01µm, fail |
| Max strain stopping rule |0.984184% |<0.02%, fail |

The original merit decreases0.000411496565→0.000330012270 in the original
dt²-scaled energy convention (19.80%). This is an energy value, not a clearance
or displacement. The length component increases0.307671→0.329422mm; wood penalty
decreases0.103826→0.000590133mm. Merit reconstruction agrees with the unchanged
original merit function within1e-18. Augmented-energy descent alone is not
relabeled global-merit or physical acceptance.

Maximum strain decreases monotonically4.60643%→0.984184%, while its peak moves
only a few links inward from the fixed supports. Length error barely changes
after sweep2. This supports slow local constraint propagation/convergence, but
does not isolate it from slow dual/penalty convergence. The16-sweep configuration
is closed. No extra iterations, parameter search or trajectory expansion ran.

Because final convergence rejects first, candidate CCD/publication is **not
reached**. Its original whole-motion checks remain in the adapter, but there is
no candidate swept-motion acceptance claim. Both returned full checkpoints and
both detailed proposal traces are byte identical, so replay evidence is stronger
than merely observing two identical rollbacks. The accepted control retains the
unchanged physical/CCD lifecycle. There is no accepted candidate/control state
comparison or old frozen-QP1µm oracle pass.

Timers include trace construction and final diagnostic metrics, but exclude
subsequent JSON serialization; they are host single-run observations, not p95
or device benchmarks. Logging is not performance adoption evidence.

## One separate, discarded complete-chain direction

Following the focused Astra outcome review, a new root/contract tested one
direction from the retained **rejected** final proposal, with lambda/rho frozen.
It constructs H=M+sum(kappa JᵀJ), g=M(x−prediction)+sum(tJ), including all493
features and shared height. This835-variable system has bandwidth5 plus one
height border on this input. Nonlocal/out-of-band features explicitly reject.
One original band factor and one solve provide dx;16global trial slots are fixed,
with one whole-proposal10%trust limit and exact current-geometry augmented energy.
No step, dual/rho update, replay, new nonlinear loop or publication occurs.

The preregistered screen requires an accepted energy trial and>=2x reduction in
both peak strain and RMS length error. That is a chosen screen threshold, not a
mathematical necessity for useful chain acceleration generally.

| Diagnostic | Result |
| --- | --- |
| Assembly / factor / solve |1.602 /0.171 /0.038ms |
| Complete discarded diagnostic |7.015ms |
| Hdx+g max residual |7.75482e-26native;9.53196e-26independent accumulation |
| gᵀdx |−1.17851e-14 |
| Energy trial |First trial accepted |
| Peak strain |0.984184%→0.956368% (2.83%reduction) |
| RMS length residual |4.12423→4.01595µm (2.63%reduction) |
| Original physical diagnostic |Strain still fails; wood/topology valid |
| Screen |Fail; rejected input restored unchanged |

This closes this single-direction test at the retained dual/penalty state. It
shows that simply changing update locality there provides little improvement.
It does **not** establish that a separately designed whole-chain AL method is
impossible. The factor timing does not establish complete-step performance.

## Verification, evidence and lifecycle

The scalar/block kernel's test-first stub fails for the intended missing
compressive force, then all six behavioral groups pass: signs/release, actual
energy derivative, original epsilon fixed point, sequential shared constraint,
three-coordinate coupled solve, invalid numeric/mass rejection. Geometry fixtures
pass refreshed whole-link distance/translation derivative, intersection rejection,
original parity/facet ID depth and sliding-crossing derivative. A deliberate
fresh mutation removing intersection rejection fails the specific behavioral
fixture. The first geometry compilation failed for private parity access; an
experiment-only forwarding helper fixed compilation before any candidate run.
No failed build is counted as a behavioral red test.

Independent stdlib geometry recomputes all493retained feature residuals from
current positions and original triangles/portals, maximum difference3.12250e-17m.
It independently accumulates final stationarity from retained Jacobians, checks
all16dual updates, strain/material error, proposal replay and rollback. Separate
accumulation verifies the chain diagnostic Hdx+g and descent. Retained Jacobian
accumulation is not an independent nonlinear trajectory solver.

No app/model/renderer/CAD source changes were made. Broad Python/Bullet suites
were not rerun for isolated Swift prototypes; their previous61pass/3legacy fail
result remains unresolved rather than being relabeled green. The untracked
intentionally failing catalog inventory test remains untouched and uncommitted.
No performance/catalog/bearing/half-step/visual gate is marked complete.

Inputs, plans, source snapshots, detailed reports, rejected proposals, validation
and fresh resource receipts are under `.context/strong-owl-live-physics-nonlinear-augmented`
and `.context/strong-owl-live-physics-chain-augmented-discriminator`, hash-bound
in the accompanying summary. Parent plans/sources were not changed after their
first physical measurement; the second diagnostic has its own fresh contract.
All13fresh worker groups and7shell drivers are absent and verified. No server,
tunnel, simulator or device was started. No historical/shared/unknown resources
were touched. Both roots become immutable after this commit.
