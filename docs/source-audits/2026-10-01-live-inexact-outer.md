# Approved isolated inexact outer experiment — 2026-10-01

**Rejected; no experimental physical step accepted.** Candidate attempts take
191.897/192.979ms including diagnostic oracles; the unchanged solver accepts the
same complete step in53.748ms. No app physics, geometry or product rollout changes.

## Explicit owner ruling

The user replied "y" to the concrete
[isolated proposal](../../.context/strong-owl-live-physics-solver-foundation/NEXT_EXPERIMENT.md)
after the [strict foundation baseline](2026-10-01-live-solver-foundation.md).
This permits intermediate affine/gap/complementarity and1um frozen-QP oracle
failures to become diagnostics in this experiment. It does not relax physical
clearance/strain/material, gravity/inertia, stationarity/equality, merit,
convergence, topology, CCD, transactional acceptance, caps or product gates.
The older bound proposal's "not authorized" text describes its pre-ruling state;
the new root's AUTHORIZATION.md records this superseding user decision.

## Implementation and matched input

The [experimental block solver](../../Tools/HangboardRopePrototype/native_contact/BlockImpulse.swift)
adds explicit `allowInexact:true`. Strict/default behavior still rejects on
exhaustion. The optional path reconstructs from complete-chain/board responses,
checks finite values and compressive signs, and reports EVERY original q,
regularized gap and multiplier. Failed certificates remain labeled failed.
All original rows remain. Existing original-matrix stationarity<=1e-10 and
equality<=1e-8 remain hard checks in the probe. Frozen-oracle difference is
reported instead of rejecting before the existing global merit can evaluate it.

The input is the exact accepted Clavellium280particle/10200triangle private
checkpoint after60prescribed steps, not a recreated/interpolated trajectory or
frozen QP. Full numeric/state roundtrip is verified byte-identical BEFORE
experiment; original physical preflight passes. Material, sliding crossings,
velocities, previous positions, board state, history, tensions and timestep are
preserved. Cache inputs are derived from the identical bound descriptor/geometry.

16sweeps per correction,8COMPUTED corrections TOTAL across retries,16merit trials,
10%relative trust, dt1/240, original .02%strain/10nm movement stopping rule,
original global merit/penalty, physical metrics and whole wood/self/intercord CCD
are unchanged. The counter records ninth ENTRY before its guard throws; that
entry performs no assembly, factor or correction. One candidate attempt, identical
replay, one full unchanged solver control; each step alarm1s. No cap/fixture search.

## Harness failure isolated and fixed

The first native run rejected in setup, before any candidate solve. Foundation
`JSONSerialization`'s decimal/NSNumber bridge restored radius with IEEE754 bits
4570216873058560376; the authored descriptor's `JSONDecoder` radius is
4570216873058560377. This violated the initializer's unchanged EXACT source-fact
comparison. All dimensions/finiteness/mass/material otherwise matched.

A real native scalar integration regression failed RED with that one-ULP mismatch,
then passed GREEN using
[ExactCheckpointJSON.swift](../../Tools/HangboardRopePrototype/native_contact/ExactCheckpointJSON.swift).
The helper uses the SAME numeric decoder as the descriptor; no epsilon was added,
no radius altered and no initializer validation bypassed. The completed rerun uses
the identical source checkpoint, now full byte-identical after restoration.
Setup failure evidence is retained separately; it is not a physics outcome or a
held-out candidate replay. Final independent literal numeric/structure fixture
passes. No historical binaries/ownership scripts were executed.

## Measured results

| Quantity | Candidate1 | Candidate2 | Existing solver |
| --- | ---: | ---: | ---: |
| Whole attempt, including diagnostics |191.897ms|192.979ms|53.748ms|
| Contact kernel sum |64.744ms|64.250ms|not instrumented|
| Diagnostic frozen-oracle sum |7.066ms|7.078ms|not applicable|
| Computed corrections |8|8|not instrumented|
| Recorded candidate merit trials |88|88|not instrumented|
| Experimental step accepted |no|no|not experimental: accepted|

All eight proposals per candidate retain stationarity/equality but fail their
contact certificates and frozen1um comparisons, explicitly recorded. Original
control accepts topology, minimum segment clearance3.599999999544mm,
length error2.3004e-10m and max strain8.3453e-10. This host single-step control is
not a device-frame runtime result or a new trajectory acceptance.

Corrections2,4,7 fail ALL16global-merit trials and trigger existing bounded retries.
Accepted intermediate directions require alpha1/128,1/64,1/4096 or1/8. Retried
smaller timesteps reduce inner residuals, but the shared8correction budget expires
before a complete candidate step passes convergence/physical/CCD acceptance.
Both rejected after-checkpoints are byte-identical to the source and each other.
No trial was published. There is no accepted experimental full-step comparison;
`comparison.json` explicitly says false. Diagnostic timings include oracle work
and logging; removing the measured7ms diagnostic work would not close this gap.

## Discriminating retained calculation

Astra's focused review verified the authorization boundary and identified that
failure precedes the10nm stop. An independent offline Fraction calculation using
ONLY retained merit scores tests whether tiny-step rejection is rounding-level.
No new physical runs or cap variants were performed.

For corrections2and4, small-step secants `(M(alpha)-M(0))/alpha` approach
+3.38134e-5 and +2.56522e-5. Three-point quadratic extrapolated offsets are
2.724e-17 and1.68e-18: strong evidence of ascent over the RECORDED local range.
At minimum tested alpha, increases exceed the1e-18 allowance by1.032billion and
783million. Correction7also rejects by217million allowances, but its extrapolated
offset−8.36e-11 suggests an unsampled kink; do not claim a derivative-at-zero or
universal non-descent proof. These are finite-score diagnostics, not certificates.

This rejects "only the strict stopping threshold caused failure": globalization
already rejects before that threshold is evaluated. It does not prove game ropes,
XPBD or every inexact method impossible, nor isolate individual merit terms.
Per-correction states/directions/component values would be needed for that
attribution; they were not retained. No extra kernel/cap/threshold rescue justified.

## Verification, lifecycle and remaining limits

Native [block fixtures](../../Tools/HangboardRopePrototype/native_contact/BlockImpulseFixtures.swift)
pass all6behavioral groups, including an inexact contradictory-row proposal that
keeps original stationarity and correctly FAILED contact certification. The new
branch failed RED under the old strict rejection, then passed GREEN. Final builds
compile the exact committed sources. The numeric regression likewise records
RED/GREEN plus final literal numeric/structure verification. Existing Python
prototype61pass/3legacymissing-Bullet failures from the prior audit are unchanged;
that suite was not rerun for these isolated Swift changes.

All17new owned child groups and shell drivers are deleted/absent and verified.
No HTTP servers, tunnels, simulators, devices or new external advisors started.
The authorized existing Astra collaboration was a focused no-edit review.
Substantive sources, checkpoint, outputs, binaries, logs and ownership receipts
are bound in the [summary](2026-10-01-live-inexact-outer-summary.json); compiler
module caches are excluded. New root is immutable after commit. Previous
root/PR529/original workspace remain untouched.

Close this fixed-budget baseline without increases or physical tolerance changes.
Cold2ms QP,50x complete geometry,1ms healthy+jug verification remain unmet;
production Mini/live catalog and physical iPhone frame performance remain unproved.
Requested accurate live settling is unfinished.
