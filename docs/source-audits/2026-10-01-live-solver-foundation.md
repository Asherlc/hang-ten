# Live rope foundation reassessment — 2026-10-01

The cold 16-sweep complete-chain block-impulse experiment **failed** at a native
contact-loaded Clavellium checkpoint. No solver, geometry or tolerance change is
adopted in the app. The accepted seated cords and frozen PR529 remain available.
This result does not establish that game-style rope simulation is unsuitable.

## Why reassess

The user challenged the foundation after repeated closed geometry/linear-solver
screens. The approved [design](../superpowers/specs/2026-09-29-live-hangboard-cords-design.md)
selected XPBD first, then a stiff-chain/simultaneous fallback if local iteration
could not meet strain. Solver history starts at 9972d22ad with the global nonlinear
solve already implemented. No valid corrected-model XPBD failure was found. The
plan's previously checked XPBD comparison is corrected to incomplete; the existing
simultaneous implementation is not denied or removed.

The old Bullet/pin/hull/smaller-radius prototype does not establish a matched-model
failure. Likewise, the retained exact-QP failures show failure of those algorithms
and gates, not impossibility of the physical feature. Ordinary XPBD approximates
implicit stationarity; a naive local replacement would not prove fidelity to the
retained inertia/gravity objective ([primary paper, equations12–18](https://mmacklin.com/xpbd.pdf)).

Actual Opus advisor a686df11-7f6c-433e-a812-e6aed1044a72 and independently authorized
Astra examined this distinction. Opus's single-feature/batch proposal was not
adopted: deepest-only and batch active-set lines are already closed, and changing
internal convergence/affine gates cannot be inferred from physical tolerances.
Astra proposed the complete-chain response baseline below. Advice is evidence of
analysis, not a certificate or authority to relax requirements.

## Implementation and fixed experiment

[BlockImpulse.swift](../../Tools/HangboardRopePrototype/native_contact/BlockImpulse.swift)
is experimental and is not linked into the app. It keeps every source contact,
solves equality/board coupling with the existing backbone, and updates compressive
impulses using each complete-chain/board response. The update is
`lambda=min(0,lambda+(q-epsilon*lambda)/(J K^-1 J^T+epsilon))`;
correction is `unconstrained-K^-1 J^T lambda`. Epsilon remains1e-8.
No dense contact-compliance matrix, one-row refactor, tensile equality batch,
independent-cord solve or local particle-only effective mass is substituted.

Fresh snapshot code under `.context/strong-owl-live-physics-solver-foundation`
retains original prediction/masses, tension Hessian, actual triangle enumeration,
material, sliding portals, prescribed rotation, global merit, relative-trust bound,
topology, full wood/self/intercord CCD and transactional acceptance. Every
correction requires original-matrix stationarity<=1e-10, equality<=1e-8,
all q>=-1e-8, regularized gap>=-1e-10, nonpositive multiplier and
complementarity<=1e-14. A passing correction also compares physical particle
vectors and height against the current contact solve within1um. No gates tuned.

Frozen bounds:16contact sweeps,8nonlinear corrections TOTAL across retries,
original16globalization trials and original .02%strain/10nm stopping criterion.
Exhaustion rejects. Native alarms bound setup60s and each physical step1s.

No full valid production-resolution Mini pre-step checkpoint exists. Its frozen QP
and unaccepted correction are not a substitute; no coarse trajectory is interpolated.
The development fixture is current-source Clavellium,280particles,10200wood
triangles. Exact retained private checkpoints include velocities, previous
positions, material, supports/attachments, topology, board motion, time/history,
accepted clearance, tension and last timestep. Cache geometry is derived from the
bound input; it is not mutated or replaced.

## Results and limits

Initial upright→jug first step:30.593/30.371ms including comparison controls;
six corrections,50–54candidate contacts but **zero active responses**. Physical
metrics and original KKT/1um comparison pass; after-checkpoints are byte-identical.
This is a valid equality/transaction plumbing check, not a contact discriminator,
trajectory, settling, bearing, half-step or performance pass. Certified-solve times
exclude equality/backbone preparation, row discovery and other frame work.

The next prescribed checkpoint was frozen before execution:exactly60 accepted
current-source steps toward jug, dt1/240, orientation30.080degrees, accepted
minimum clearance3.600mm. One cold block-impulse attempt and identical replay:

| Quantity | Attempt1 | Attempt2 |
| --- | ---: | ---: |
| Candidate source rows |189|189|
| Complete-chain responses |83|83|
| Sweeps |16|16|
| Kernel time |14.241ms|14.155ms|
| Complete rejected attempt |16.498ms|16.244ms|
| Worst affine q |−253.567um|−253.567um|
| Regularized gap violation |253.567um|253.567um|
| Complementarity |2.2640e-9|2.2640e-9|

Both reject their FIRST correction before globalization/nonlinear physical checks.
The full solver checkpoint after each rejection is byte-identical to the retained
input. The253.567um number is an affine residual, **not wood penetration in an
accepted state**. No state or motion was published. This closes the bounded exact
16-sweep baseline; no cap increase, favorable checkpoint search or held-out rescue.

## Verification and review

Native [fixtures](../../Tools/HangboardRopePrototype/native_contact/BlockImpulseFixtures.swift)
exercise coupled board response, empty contact sets, separating contacts exerting
no force, contradictory rows rejecting, and rejection of recovered-vector gap,
multiplier-sign and nonfinite failures. Initial stub failed RED; implementation
passed GREEN. Astra caught checking contacts before reconstruction rather than on
the returned vector. A new certificate regression failed RED and passed GREEN;
the returned vector is now checked. Shared eight-total budget and explicit
serialized replay comparison were also corrected. Final focused Astra review
found no remaining false-acceptance issue.

Prototype suite first could not collect without numpy/pxr. Fresh workspace-owned
pinned dependencies resolved collection:61passed,3failed,14third-party deprecation
warnings. Failures are all legacy `tests/test_solver.py` calls to missing historical
`.context/frantic-kiwi/rope-build/rope_solver`:
`test_rope_settles_around_outside_of_round_bar`,
`test_wrong_wrap_topology_is_rejected`, and
`test_fresh_simulations_are_repeatable`. No old executable was run or rebuilt to
make those unrelated historical tests green. This is not a green whole suite.

All16owned worker groups, shell drivers and exact Opus guard are absent after
cleanup. Advisor is archived/closed; temporary test venv was deleted and verified.
No servers, tunnels, simulators or devices were created. Compiler/download caches
and pytest scratch are workspace-local, excluded from acceptance inputs. Substantive
source/input/output/binary/log/resource hashes are bound in the
[summary](2026-10-01-live-solver-foundation-summary.json). Root is immutable after
commit; historical ownership is not permission to rerun or clean its resources.

## Concrete next decision

The retained [proposal](../../.context/strong-owl-live-physics-solver-foundation/NEXT_EXPERIMENT.md)
asks whether bounded inexact intermediate contact directions can progress through
the existing nonlinear merit while meeting unchanged final physical checks.
This would move affine/complementarity/inner-oracle failure from rejection to a
reported intermediate diagnostic in an isolated experiment. The handoff explicitly
requires "exact affine separation, convergence/global merit", so this numerical
acceptance change requires an explicit owner ruling; it is not silently authorized
by the50um physical clearance or the isolated100um geometry allowance.

No inexact experiment has run. Staged2ms cold-QP,50x complete geometry and1ms
healthy+jug verification gates remain unmet; full device-frame performance remains
unmeasured. The requested live rollout remains incomplete.
