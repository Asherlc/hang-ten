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

Final native suites: 51/51, optimized Debug (`SWIFT_OPTIMIZATION_LEVEL=-O`), 54.718 s. Native class counts: 38 RealityKit scene, 8 controller, 5 mesh. Log: `.context/universal-cord-support/native-optimized.log`. Current-source normal Debug `build-for-testing` also passes: `.context/universal-cord-support/task4-normal-build-final.log`. The enabled-failure scene test uses an invalid quaternion to verify unavailable delivery and retained entity pose; bounded physically infeasible tilt is covered by the pure solver fixture, not claimed as a native Clavellium failure.

Camera regression: settled framing previously retained the entire support-reachable volume (camera distance 1.8148 m), leaving the block ~40 pixels wide. `testLiveScenePausesThenPublishesAcceptedSettledFrame` reproduced this failure, then passed with framing refit at accepted rest. Conservative translation bounds are applied before target changes and held during motion. A repeated settled target does not reopen the envelope.

Native visual configuration: signed optimized Debug app, iPhone 17 Pro / iOS 26.5, exact app container recorded in `.context/universal-cord-support/visual-container.txt`. DEBUG routes select Clavellium detail and X rotation. Front/side/top +20° screenshots are `clavellium-x20-{front,side,top}.png` under that evidence directory; landscape bounds are `clavellium-x20-landscape.png` (native output already landscape; no rotation needed). All were inspected. No CAD geometry or material was changed; green/red highlighting is transient app selection rendering.

Interactive runtime controls: semantic contact tap changed 20 mm to 8 mm and back; drag orbited the board; tapping the contact reset the camera. Screenshots: `interactive-orbit.png`, `interactive-reset.png`. Home/foreground exercise retained the app scene. Clearing selection, pause/resume, Reduce Motion, stopping, superseded generations, independent lateral translations and failure retention are verified in the native scene/controller tests. The detail page deliberately retains one selected grip, so tapping the same grip is not a deselect action.

Ordered native motion: the same app scene runs `HANGTEN_REVIEW_ROPE_ROTATION_SEQUENCE=20,-20,0` after its initial upright settlement, using the side review camera. `.context/corded-pivot/vector-sequence-long.zsh` records the video and screenshots every second; screenshots take additional wall time, so frame numbers are capture indices, not exact video seconds. Frames 4, 17, 29, 56 show upright, positive X, negative X, and returned upright. `ordered-x-frames.png` presents these in order; the returned frame refits at accepted rest. `large-hyena-x-sequence-long.mp4` retains continuous motion; the shorter first recording ends during the return and is not evidence of final settlement. Requested angles come from the review route, not measurement from pixels; exact accepted quaternion/translation agreement is proven by the native rigid-transform tests.

Cleanup verified after native review: exact owned simulator UUID is absent from `simctl list devices --json`; pending/owned simulator manifests and workspace DerivedData are absent. The empty owned manifest left by archive cleanup was removed after checking it contained no identities. Video recorder terminated and ownership record removed; the named XcodeBuildMCP session profile was cleared. Receipt `.context/universal-cord-support/cleanup-verification.json`. Shared simulators and other worktrees were left alone. XCTest summaries were copied into the evidence directory before DerivedData deletion.
