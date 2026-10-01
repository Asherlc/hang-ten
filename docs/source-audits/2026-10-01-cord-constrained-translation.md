# Cord-constrained translation: implementation evidence

Date: 2026-10-01. Worktree: `large-hyena`; branch: `corded-board-cord-rotation`.

## Scope and model

Approved core plan: [design](../superpowers/specs/2026-10-01-universal-cord-support-design.md), [implementation](../superpowers/plans/2026-10-01-universal-cord-support.md), and [Opus corrections](2026-10-01-universal-cord-plan-review.md). Runtime changes prescribe orientation and solve three-dimensional translation together with continuous cord constraints. Supports remain world-fixed, attachments remain local, passage crossings slide. Collision-bounds midpoint is a numerical reference, not a hinge. No centering force was introduced.

Initialization uses a bounded damped three-variable route-length fit, up to 64 shared corrections and four certified route rebuilds. Scalar height bracketing supplies an optional candidate. Every initial chain must match its immutable source budget within 1e-8 m; incompatible taut budgets reject explicitly as unsupported slack initialization. This is a known adoption boundary.

## Verification

- Current pure suite: 111/111 Apple XCTest host tests, optimized Swift, 853.466 s. Log: `.context/universal-cord-support/task2-all.log`. Covers true attachments, asymmetric and short leads, lateral translation, portal/contact derivatives in every axis, accumulated-tension Hessian, primary and fallback factors, swept wood rejection, transactional rollback, twin continuous loops, determinism, half steps and large coordinate-origin shifts.
- Clavellium X20: settles in 2.216667 simulated seconds; half-step 2.175 s. Body half-step difference about 1.98 micrometres, within unchanged 0.2 mm gate. Return: 1.5625 s, half-step 1.53125 s. Independent two-loop X20: 2.2125 s.
- Z90 flat-bearing rest: sideways difference between step sizes is 0.104205 mm, below unchanged 0.2 mm gate. Reference and bearing heights pass. Neutral sideways drift is physically permitted and is not corrected by a spring.
- Normal Debug build-for-testing passes. Unoptimized native runtime pause/resume hit the existing 30 s settling timeout; no timeout or acceptance gate was loosened. Optimized Debug native suites validate renderer, controller and tube mesh separately; final receipt below.
- Package validation: 66/66, zero drafts; `rtk proxy env PYTHONPATH=Tools/HangboardPackages/src python3 -m hangboard_packages.cli validate --root Hangboards --final-inventory`. Log `.context/universal-cord-support/package-validation.log`.
- Physical-device performance has not been measured. Simulator timings are not device-performance evidence.

## Asset integrity

No CAD, USDZ, model, suspension or physics-package edits. Retained SHA-256 values:

| Path | SHA-256 |
| --- | --- |
| `Hangboards/clavellium-training-block/assets/primary.usdz` | `35417e90919ff4bb75c2e4faaffe04547457e67032de8601451d799d789ca64d` |
| `Hangboards/clavellium-training-block/assets/primary.model.json` | `0e344ccdc6529eccb4b94e1c05ba835388f1a6fe1e9394d47e637ee55ab9818e` |
| `Hangboards/clavellium-training-block/assets/primary.physics.json` | `c60fbd6dfaf59bfd5fb7e6aa8d806f78af7e828a7f64074d326865e08f13e853` |
| `Hangboards/clavellium-training-block/suspension.json` | `514366d1579ad467b0c6ef761f1841aa8f5147fa2b868b1007b12ad23b08d85c` |

## Catalog adoption handoff

Discovery used the 66 generated bundled manifests produced by the current native build, not stale on-disk authoring manifests. Record: `.context/universal-cord-support/catalog-cords.json`. The core implementation does not enable these static packages. Current setup labels do not establish hidden channel topology. Each migration must retain primary evidence, author a compatible graph/collision descriptor, pass admission/rotation/rollback gates, and collect native visual and device performance evidence before enablement.

| Board | Current renderer / setup | Required migration evidence and fit |
| --- | --- | --- |
| `captain-fingerfood.unlevel` | Static / pairedLeadCord | Retained attachment/passage/bearing evidence and compatible exterior graph; do not infer bores from the adapter name. |
| `j-bryant.ftg-32` | Static / pairedLeadCord | Retained attachment/passage/bearing evidence and compatible exterior graph; do not infer bores from the adapter name. |
| `metolius.rock-rings-3d` | Static / threadedLoopCord internalLoop, threadedLoopCord internalLoop | Native channel geometry, collision/hash pairing, continuous graph and strict initialization; curved channels need routing validation. Separate per-instance physics with preserved base placement and independent state. |
| `tension.flash-board` | Static / twoBranchCord | Retained attachment/passage/bearing evidence and compatible exterior graph; do not infer bores from the adapter name. |
| `captain-fingerfood.pocket` | Static / pairedLeadCord | Retained attachment/passage/bearing evidence and compatible exterior graph; do not infer bores from the adapter name. |
| `clavellium-training-block` | Live / twoBranchCord internalLoop | Core numerical/native gates; device performance unmeasured. |
| `metolius.light-rail-2` | Static / pairedLeadCord | Retained attachment/passage/bearing evidence and compatible exterior graph; do not infer bores from the adapter name. |
| `crimptonite.helium-mobile` | Static / twoBranchCord internalLoop | Native channel geometry, collision/hash pairing, continuous graph and strict initialization; curved channels need routing validation. |
| `lattice.mxedge-lift-large` | Static / pairedLeadCord | Retained attachment/passage/bearing evidence and compatible exterior graph; do not infer bores from the adapter name. |
| `nature.stone-hanger` | Static / pairedLeadCord | Retained attachment/passage/bearing evidence and compatible exterior graph; do not infer bores from the adapter name. |
| `captain-fingerfood.dual` | Static / pairedLeadCord | Retained attachment/passage/bearing evidence and compatible exterior graph; do not infer bores from the adapter name. |
| `yy.penta-evo` | Static / pairedLeadCord, pairedLeadCord | Retained attachment/passage/bearing evidence and compatible exterior graph; do not infer bores from the adapter name. Separate per-instance physics with preserved base placement and independent state. |
| `lattice.mini-bar` | Static / twoBranchCord internalLoop | Native channel geometry, collision/hash pairing, continuous graph and strict initialization; curved channels need routing validation. |
| `yy.baguette-evo` | Static / twoBranchCord | Retained attachment/passage/bearing evidence and compatible exterior graph; do not infer bores from the adapter name. |
| `lattice.mxedge-lift-small` | Static / pairedLeadCord | Retained attachment/passage/bearing evidence and compatible exterior graph; do not infer bores from the adapter name. |

The user’s universal catalog goal remains open. Mini Bar, Helium Mobile, exterior graphs, and independent paired models require their own evidence-backed package workstreams; this is not a metadata flag flip. No merge into the separately owned `feat/live-hangboard-physics` worktree is part of this plan.

## Native visual review and cleanup

Current-source native receipt and ordered visual provenance appear below. Owned simulator: `5E5846BA-438C-4423-9CF1-A2335E4D6C70`, name `Hang Ten Paseo large-hyena Review`; exact EXIT cleanup guard installed before creation. Resource deletion must be verified before completion.

Before the final Opus correction, native suites: 51/51, optimized Debug (`SWIFT_OPTIMIZATION_LEVEL=-O`), 54.718 s. Native class counts: 38 RealityKit scene, 8 controller, 5 mesh. Log: `.context/universal-cord-support/native-optimized-before-review.log`. That source’s normal Debug `build-for-testing` also passes: `.context/universal-cord-support/task4-normal-build-final.log`. The enabled-failure scene test uses an invalid quaternion to verify unavailable delivery and retained entity pose; bounded physically infeasible tilt is covered by the pure solver fixture, not claimed as a native Clavellium failure.

Before the final Opus correction, camera regression: settled framing previously retained the entire support-reachable volume (camera distance 1.8148 m), leaving the block ~40 pixels wide. `testLiveScenePausesThenPublishesAcceptedSettledFrame` reproduced this failure, then passed with framing refit at accepted rest. Conservative translation bounds are applied before target changes and held during motion. A repeated settled target does not reopen the envelope.

Native visual configuration: signed optimized Debug app, iPhone 17 Pro / iOS 26.5, exact app container recorded in `.context/universal-cord-support/visual-container.txt`. DEBUG routes select Clavellium detail and X rotation. Front/side/top +20° screenshots are `clavellium-x20-{front,side,top}.png` under that evidence directory; landscape bounds are `clavellium-x20-landscape.png` (native output already landscape; no rotation needed). All were inspected. No CAD geometry or material was changed; green/red highlighting is transient app selection rendering.

Interactive runtime controls: semantic contact tap changed 20 mm to 8 mm and back; drag orbited the board; tapping the contact reset the camera. Screenshots: `interactive-orbit.png`, `interactive-reset.png`. Home/foreground exercise retained the app scene. Clearing selection, pause/resume, Reduce Motion, stopping, superseded generations, independent lateral translations and failure retention are verified in the native scene/controller tests. The detail page deliberately retains one selected grip, so tapping the same grip is not a deselect action.

Ordered native motion: the same app scene runs `HANGTEN_REVIEW_ROPE_ROTATION_SEQUENCE=20,-20,0` after its initial upright settlement, using the side review camera. `.context/corded-pivot/vector-sequence-long.zsh` records the video and screenshots every second; screenshots take additional wall time, so frame numbers are capture indices, not exact video seconds. Frames 4, 17, 29, 56 show upright, positive X, negative X, and returned upright. `ordered-x-frames.png` presents these in order; the returned frame refits at accepted rest. `large-hyena-x-sequence-long.mp4` retains continuous motion; the shorter first recording ends during the return and is not evidence of final settlement. Requested angles come from the review route, not measurement from pixels; exact accepted quaternion/translation agreement is proven by the native rigid-transform tests.

Cleanup verified after native review: exact owned simulator UUID is absent from `simctl list devices --json`; pending/owned simulator manifests and workspace DerivedData are absent. The empty owned manifest left by archive cleanup was removed after checking it contained no identities. Video recorder terminated and ownership record removed; the named XcodeBuildMCP session profile was cleared. Receipt `.context/universal-cord-support/cleanup-verification.json`. Shared simulators and other worktrees were left alone. XCTest summaries were copied into the evidence directory before DerivedData deletion.

## Final Opus review and camera correction

Opus 5.5 (xhigh) independently reviewed `0da36b441..9099c55e7`, all five Review Focus conditions, the complete source/diff, ledger decisions and extracted screenshots. It found no Critical issues and confirmed the vector solver, seed and accepted rendered transform. Its Important finding was a usability defect in the full reachable-space camera cube: it made the board too small during motion and introduced a large zoom under Reduce Motion. Full review: `.context/final-opus-review/review.md`. The exact advisor `3f69ac98-6e8e-4008-8310-3451e9fc8526` was deleted and confirmed not found.

One fix pass followed. `testLiveMotionFramingKeepsBoardReadable` failed with 8.60583% viewport occupancy on opening, normal-motion camera distance 2.4217634 m against 0.814673 m at rest, and a Reduce Motion matrix change before any final frame. The replacement fits the accepted rotation sphere with a display margin `max(25% of body radius, twice cord radius)`. It keeps the fit fixed while actual accepted board/tube bounds remain inside, expands only on escape, and refits when all matching-generation instances finish. The margin never constrains physics. Cached pose restoration does not trigger intermediate framing. Reduced Motion skips preparatory fitting.

The test passes: opening occupancy exceeds 15%, normal tilt distance stays within 1.35 times the rest distance, the first accepted moving frame leaves the camera unchanged, and Reduced Motion leaves the accepted camera unchanged until publication. All 52 native tests pass, 63.093 s; log `.context/universal-cord-support/native-optimized.log`. The 111/111 pure physics receipt remains hash-identical and valid. No acceptance thresholds or physics constants were relaxed. The simulator’s first-launch migration/HealthKit bootstrap failure was retried after its 8:12 boot migration; the test failures used for RED are the completed method runs, not that startup error.

Current-source visual evidence is recaptured under `.context/universal-cord-support/post-review/`; earlier images remain historical evidence of the review finding. Final normal Debug `build-for-testing` passes (`normal-build-after-review.log`). Revised front/side/top and landscape views were inspected. Same-scene captures 3, 5, 7, 10 show upright, positive X, negative X, and upright return. All 90 captures and the full recording remain in `post-review/`; capture indices are observations, not simulated times. Source hashes and capture timestamps appear in `post-review/visual-provenance.json`. Owned simulator `EB6BEE72-4234-4EF4-B565-B35FD591DF43`, recorder, manifests and DerivedData were removed and deletion verified (`cleanup-verification-after-review.json`); the prior Xcode session profile remains cleared.

## Execution decisions and deferred review findings

The exhaustive execution rulings below preserve the approved scope, reasons and risks. They include historical decisions superseded by the final camera correction.

- Task 1: Ruling: seed world-reference location must derive from fixed supports, not the numeric local reference — c - q*c shifts the whole seed when local coordinates shift; use world lateral support centroid and a vertical bracket, with T = worldReference - q*c — cost if wrong: initial placement changes on unusual support arrangements, covered by origin/attachment fixtures.
- Task 1: Ruling: fixed-inside-wood regression now reaches CCD rejection instead of scalar nonlinear rejection — full translation permits an attempted escape but no accepted traversal; assert bounded failure and full rollback rather than obsolete failure subtype — cost if wrong: could conceal a changed internal failure reason, geometry/rollback remain checked.
- Task 1: Ruling: add a read-only accumulatedLinkTensions test seam — the finite-difference Hessian must use the actual accumulated multipliers and production factorization, without injecting a debug backend or duplicating stiffness assembly — cost if wrong: one additional internal accessor, no mutable API.
- Task 1: Ruling: task-done verifies completed current-source suite receipts instead of rerunning unchanged expensive suites — developer instructions prohibit redundant test repetition; guard checks all required class receipts and source timestamps — cost if wrong: stale receipt could conceal a regression, source provenance is checked. Native optimized Debug 49/49 passed, 37.824 s; packages 66/66 pass.
- Final: Ruling: replace absolute camera freezing/full reachable-space fit with a readable accepted-pose rotation envelope plus a local translation margin, and expand only if actual accepted geometry leaves it; skip preparatory zoom for Reduce Motion — the old camera contract conflicts with watching the board move — cost if wrong: unusual motion may require a camera expansion during motion, every accepted frame remains framed; physics unchanged.
- Final: minor (deferred): quadratic pairwise reference-history displacement computation; optimize conservatively after device profiling.
- Final: minor (deferred): seed fit error conflates unsupported taut/slack geometry with correction or line-search exhaustion.
- Final: minor (deferred): solver-step lateral sleeping regression absent; current test checks vector metrics only.
- Final: minor (deferred): near-dependent fallback fixture checks Y as zero rather than with a nonzero Y correction.
- Final: minor (deferred): attached wood-segment/portal finite differences and explicit portal-boundary-row presence not asserted; formulas reviewed by hand.
- Final: minor (deferred): native failure uses invalid quaternion rather than exhaustion of nonlinear retries; pure solver checks bounded physical rejection.
- Final: Ruling: device p95/60 fps remains unmeasured and no performance acceptance is claimed — numerical core evidence is separate from device rollout — cost if wrong: hardware may need further optimization before shipping.
- Final: Ruling: other 14 cord setups remain static pending catalog work — approved core scope and geometry evidence boundary — cost if wrong: universal catalog behavior remains unfinished.
- Final: Ruling: slack and exterior-wrap seed adapters stay deferred — do not invent topology or relax strict taut admission — cost if wrong: otherwise feasible packages can be unavailable until adapters exist.
- Final: Ruling: leave frozen prototype boardHeight references alone — they are outside runtime and do not alter the shipped solver — cost if wrong: prototype users see legacy behavior.
- Final: Ruling: live reflected/yaw-rotated paired bases need additional enablement evidence; translation pairs are the current verified path — no package enables these other placements and gravity preservation is guarded — cost if wrong: future paired adopters need coordinate-adapter tests.
- Final: Ruling: keep pre-existing worker advancement after undelivered in-flight steps — delivery tokens prevent stale render updates and each step remains transactional — cost if wrong: resume can start from a newer internal state than the last visible frame.
- Final: Ruling: disclose the unchanged unoptimized Debug timeout; optimized Debug and normal build results stand — production optimization and simulator expense differ — cost if wrong: unoptimized debugging remains slow.
- Final: Ruling: retain the 1 kg estimate and damping 18 — approved data/constants, not new measured manufacturer facts — cost if wrong: timing may differ from a real board.
- Final: Ruling: use ordered extracted PNGs for visual review and retain full recordings — the reviewer did not inspect every video frame — cost if wrong: an uncaptured transient visual glitch may remain.
- Final: Ruling: rely on fresh hash-matched full suite receipts rather than repeat unchanged pure tests — developer instruction forbids redundant reruns; changed native camera is rerun — cost if wrong: a deficient receipt guard may miss stale evidence.
- Final: Ruling: retain pre-existing initialization projection without a swept-motion step — certified route/contact admission and prior audit govern the initial snapshot — cost if wrong: future graph types need expanded admission evidence.
- Final: Ruling: enabled failure remains unavailable after bounded failure — approved explicit failure path avoids guessed fallback geometry — cost if wrong: a recoverable view requires reload.
- Final: Ruling: retain and push the isolated branch/worktree without merging — approved plan excludes the separately owned feature worktree and developer requires automatic push; no additional integration approval is needed — cost if wrong: integration remains pending.
