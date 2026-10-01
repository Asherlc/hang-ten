# Shared Cord Constraints Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Solve board translation and continuous cords together during controlled tilt, replacing the averaged pivot in the shared live solver.

**Architecture:** Keep prescribed orientation; add three translational degrees of freedom to the existing coupled mass-metric constraint solve. Publish that rigid transform directly to RealityKit. Establish generic fixtures and Clavellium first; catalog migration requires separate evidence-backed package work.

**Tech Stack:** Swift 5, SIMD, Accelerate/LAPACK, XCTest, RealityKit, Python package validators; existing iOS 18 minimum.

**Spec:** [Approved design](../specs/2026-10-01-universal-cord-support-design.md), approved by the user on 2026-10-01.

**Advisor review:** Opus 5.5 reviewed revision `4777344d0` and endorsed the approach while requesting corrections before implementation. This revision addresses the verified findings below; Opus has not reviewed this revised text. Execute Tasks 1, 3, 2, then 4: prove the existing Clavellium motion before extending seed placement.

## Global Constraints

- Prescribed orientation remains an input; there is no physical `rotationPivot` state.
- Fixed supports stay fixed in solver world; attachments stay fixed in board coordinates; passage crossings slide through material.
- Total rope-length error at most 0.5 mm; local strain at most 0.5%; finite-radius segment clearance at least radius minus 0.05 mm.
- Convergence within five simulated seconds: speed below 1 mm/s, displacement below 0.1 mm over the final half-second; half-step contact/endpoint differences below 0.2 mm.
- Confirmed Clavellium and Mini Bar cord diameter stays 7 mm. Preserve immutable rest lengths, topology, self/inter-cord checks, collision geometry, resource hashes, and package evidence.
- Preserve bounded display work, transactional retries, cancellation, independent instances, Reduce Motion, non-pickable cords, and the existing unavailable state after a failed enabled profile.
- Require gravity-preserving instance placement. No unrelated hold, routine, USDZ, or material changes.
- All shell commands use `rtk`; generated artifacts stay under `.context`; exact workspace-owned resources have recorded identities and exit-trap cleanup. Push each new commit automatically.
- Under-4-ms p95/60-fps performance requires physical iPhone evidence. An optimized simulator run is not device evidence.
- Flat bearings can admit a range of equally stable sideways positions. Do not add a centering force or hinge to force a unique rest position. Keep the strict 0.2 mm world-position checks for equivalent initial conditions, coordinate-origin changes, and symmetric half-step fixtures; supplement asymmetric neutral-motion cases with reference/bearing heights and all geometry metrics, without claiming those cases passed the strict positional comparison if they did not.

## Review Focus

1. Lateral velocity with steady height must prevent sleeping; test in Task 1.
2. Changing model coordinates must not change physical support or bearing; test in Task 2.
3. Near-dependent contacts must exercise the fallback with all three body variables; test in Task 3.
4. An infeasible requested tilt must preserve the accepted state and fail explicitly after bounded retries; test in Task 3.
5. Paused or superseded deliveries must not apply an old lateral translation to another instance; test in Task 4.

## Verification setup

At execution, read the spec, applicable skills, and repository instructions. Inspect the existing worktree before creating another: the `feat/live-hangboard-physics` branch is owned by a different worktree. Continue this isolated branch unless the user directs otherwise.

Use the repository's `validate-hang-ten-ios` skill and `docs/IOS_SIMULATOR_VALIDATION.md` to create an isolated simulator named with the current workspace owner, recording its exact UUID before boot. Set `HANGTEN_SIMULATOR_UUID` only to that owned device. Install the required cleanup trap before creation. The following command is the native test template; replace `CLASS` with the task's listed class and repeat for each class:

```sh
rtk proxy xcodebuild -project HangTen.xcodeproj -scheme HangTen \
  -configuration Debug \
  -destination "platform=iOS Simulator,id=$HANGTEN_SIMULATOR_UUID" \
  -derivedDataPath .context/DerivedData -parallel-testing-enabled NO \
  -only-testing:HangTenTests/CLASS test
```

For faster pure physics iterations, reuse the verified macOS XCTest-suite runner recipe retained in `.context/corded-pivot/verification.md`; compile current `Rope*.swift` sources and all affected test files anew with `swiftc -O`, Accelerate, and Apple's XCTest overlay/framework paths. If those local artifacts are missing, use the native template instead. Record optimization level in every timing report. Pure physics suites must pass before UI validation; no class is silently omitted after a failure.

---

### Task 1: Replace scalar motion with the coupled vector transform

**Files:** Modify `HangTen/Models/RopePhysicsDescriptor.swift`, `RopeSimulationState.swift`, `RopeSimulationMetrics.swift`, `RopeDynamicsSolver.swift`, `RopeThreadedSeed.swift`, `RopeBandedSystem.swift`, and `BoardModelRealityTypes.swift`. Migrate affected constructors/assertions in `HangTenTests/RopeDynamicsSolverTests.swift`, `RopeContactSystemTests.swift`, `RopeThreadedSeedTests.swift`, `RopeInterContactTests.swift`, `ClavelliumRopePhysicsTests.swift`, `BoardModelRealityTests.swift`, and `LiveRopeControllerTests.swift`.

**Interfaces:**
- `RopeSimulationState`: `boardTranslation: SIMD3<Double>`, `boardLinearVelocity: SIMD3<Double>` replace scalar fields and pivot; retain `worldPoint(_:)` and `boardPoint(_:)` signatures. Linear velocity refers to the body's numerical mass-reference point, not an arbitrarily chosen importer origin.
- `RopeFrameSnapshot`: stored `boardTranslation: SIMD3<Double>` replaces height/pivot; retain orientation, ropes, settled, and metrics.
- `RopeSimulationMetrics.measure(state:input:collider:boardHistory:includeSelfContact:channelCache:)`: history becomes `[SIMD3<Double>]`.
- `RopeDynamicsSolver.correctionFraction(ropes:corrections:boardCorrection:) -> Double`: final argument is `SIMD3<Double>`.
- Public solver `init`, `step`, `settled`, and `prepareDisplay` signatures remain unchanged.
- Add shared internal `RopePhysicsInput.bodyReferencePoint: SIMD3<Double>`, computed from collision bounds. Do not add a descriptor field or physical pin.
- Make `RopeDynamicsSolver.ConstraintRow` internal and extract internal `assembledConstraintRows() throws -> [ConstraintRow]`, called by production correction. Make the existing `constraintBackbone(rows:weights:prediction:)` and `contactCorrection(rows:weights:prediction:)` internal for production-path tests; preserve their existing input shapes and replace scalar correction return values with `boardCorrection: SIMD3<Double>`.

- [ ] **Write the failing lateral-support regression.** Extend the existing two-attachment cube fixture: local attachments `(x, 0.02, 0.008)`, supports `(x, 0.12, 0.018)`, `x = ±0.008`, two 0.1 m ropes. Run upright settling from its taut slanted seed. Expected translation is `(0, 0, 0.01)` within 0.2 mm; both supports are exact and attachment particles equal `state.worldPoint(local)`. The scalar solver can adjust height but cannot reach this lateral equilibrium. Record its failing result before changing implementation.
- [ ] **Add `testXTiltRequiresLateralTranslation` and `testSingleAttachmentSettlesUnderItsSupport`.** For X ±0.4 rad, use the same X-separated attachment axis at local `(x, 0.02, 0.008)` but derive each fixed support from the desired target orientation, known translation `(0, 0, 0.03)`, and a vertical 0.1 m lead. Construct exact taut initial chains in that selected tilted pose; require solver world translation to match the known equilibrium within 0.2 mm and source supports to remain exact. The averaged-pivot/scalar-height transform cannot represent the 30 mm lateral placement. Also settle the original symmetric pair through X tilt and return, checking steady attachment axis within 0.2 mm after settlement. Repeat with one true attachment to cover the single-lead graph. Do not require two non-collinear attachment points to remain world-fixed under X rotation; rigid-body geometry forbids that.
- [ ] **Add tests `testLateralBoardVelocityPreventsSettling` and `testVectorTrustUsesAttachmentMotion`.** Keep height steady while assigning 0.01 m/s X or Z velocity; metrics must report at least 0.01 m/s. For a 0.1 m link with one fixed support and a 0.02 m transverse attachment correction, the relative-link trust fraction must be 0.5. A common 0.02 m particle/body translation with no fixed support must have fraction 1.
- [ ] **Run `RopeDynamicsSolverTests` and `RopeThreadedSeedTests` with the verification template.** Expect the lateral behavior assertion to fail on current code; subsequently missing vector interfaces may fail compilation until the atomic migration is complete. Preserve the behavioral red-run log.
- [ ] **Test real constraint assembly before generalizing it.** Use `assembledConstraintRows()` to finite-difference translation by ±1e-7 m along all three axes against independently evaluated geometric residuals, accuracy 1e-6. Cover length, wood point/segment, sliding portal, self-contact, and inter-cord rows with free and attached endpoints. Test the assembled 3×3 tension block/cross terms against a finite-difference link Hessian. Keep fixtures away from witness switches; the test must consume production derivatives rather than recompute their formula. Add a near-dependent frozen row fixture whose primary `RopeContactSystem` solve without fallback throws `illConditioned`; invoke the solver's actual `contactCorrection` on that same backbone and verify its fallback mapping satisfies every row, including X/Z and nonlocal border terms.
- [ ] **Migrate state, frames, metrics, and callers atomically.** Implement `worldPoint(p) = q.act(p) + translation` and its inverse. Use vector gravity `(0, -9.81, 0)`, existing damping 18 and angular-speed bound 2.1 rad/s. Compute speed with vector norm and history displacement as the maximum Euclidean distance between any two samples in the retained final-half-second history. Validate every translation/velocity component as finite.
- [ ] **Keep prediction independent of importer origin.** Use the shared `input.bodyReferencePoint`, explicitly a numerical mass-location estimate that shifts with model coordinates and is never pinned. Preserve this point's world position when applying the orientation predictor: add `oldQ.act(reference) - newQ.act(reference)` to predicted translation, then integrate its gravity/damped linear velocity. Reconstruct velocity and displacement history from `state.worldPoint(reference)`. The correction mass metric still uses the difference of translations because orientation is fixed during that solve. Use the same reference for seed candidate rotation, sweep deviation bounds, and camera envelope. This reference must not add a hinge constraint or average portal positions.
- [ ] **Generalize the complete coupled solve.** `ConstraintRow.boardGradient` becomes `SIMD3<Double>`; correction results use `boardCorrection`. Board border indices are X/Y/Z at 0/1/2, with nonlocal constraint borders starting at 3. Mass block is `mass * identity(3)`. For distance constraints, sum gradients of attached endpoints; for wood/portal contact, also subtract the sum of all endpoint world gradients. Include attachment effects in self/inter-cord rows. Expand tension curvature into the full 3×3 board block and particle/body cross terms. Update merit, fallback extraction, inactive inequalities, line search, relative trust, velocity reconstruction, and transactional state together.
- [ ] **Update seed and renderer call sites for the new representation.** Retain height bracketing as a candidate generator, with translation `reference - q.act(reference) + (0, height, 0)`; remove averaged-cord-pivot compensation. Seed and render use the identical rigid transform. Camera rotation bounds use the shared reference and its corner radius. Add a conservative full-translation allowance derived from fixed supports and declared rope lengths; keep the camera stationary during motion and refit at accepted rest. Check that the whole board and cord remain inside that envelope. Replace pivot-based assertions in all affected classes now, including the 60° seed and Clavellium tests; the attachment-axis assertion belongs after physical settlement, not in raw seed geometry.
- [ ] **Run all six pure suites:** `RopePhysicsDescriptorTests`, `RopeTriangleColliderTests`, `RopeThreadedSeedTests`, `RopeDynamicsSolverTests`, `RopeInterContactTests`, `ClavelliumRopePhysicsTests`. Expect zero failures, including lateral support and existing upright/threading regressions. Using the owned simulator, run `build-for-testing` with the native template's project/scheme/configuration/destination and run `BoardModelRealityTests` plus `LiveRopeControllerTests` before committing this migration.
- [ ] **Commit and push** the coherent vector migration: `feat: solve cord-supported board translation in three dimensions`.

### Task 2: Admit feasible translated seeds without an authored pivot

**Files:** Modify `HangTen/Models/RopeThreadedSeed.swift`, `RopeDynamicsSolver.swift` initialization only, `HangTenTests/RopeThreadedSeedTests.swift`.

**Interfaces:** Keep `RopeThreadedSeed.make(input:profileID:orientation:collider:placement:) throws -> RopeSimulationState`. Extract private `makeRoutes(translation: SIMD3<Double>) throws -> [Route]` and `solvePlacement(initial: SIMD3<Double>) throws -> SIMD3<Double>` within the seed implementation; route type remains private. Callers still use `prepareDisplay` for first-frame admission.

- [ ] **Write `testAsymmetricLeadsHaveFeasibleTranslatedSeed`.** Reuse two local X-separated attachments but choose distinct support offsets/rest lengths whose exact common translation is known. Construct supports from common translation `(0, 0, 0.03)` plus distinct vertical lead lengths 0.1 and 0.12 m. Verify first admitted frame has exact supports, immutable declared total lengths, and accepted geometry. The old scalar-height solve rejects these incompatible seed heights, despite the known feasible lateral placement.
- [ ] **Write `testChangingBoardOriginPreservesWorldSimulation`.** Shift every board-local collision vertex, portal, channel vertex/spine, and attachment by each of `(0.013, -0.009, 0.017)` and `(0.25, -0.20, 0.30)` while leaving supports unchanged. Compare original and shifted fixtures through upright and X ±20° settling: `q.act(p)` changes by `q.act(shift)`, so translations must differ by its negative. World attachment, rope, and bearing differences must stay below 0.2 mm. Cover the synthetic attachment fixture and actual Clavellium input, including tilted initial seeding. Diagnose contact ordering and shared-reference inconsistencies if this fails; origin changes do not justify a different physical trajectory.
- [ ] **Run the seed class; expect scalar-candidate placement failure and/or origin-dependent world results.** Retain the red log.
- [ ] **Implement bounded deterministic placement.** Retain the existing bracket as a fast candidate. Build the geometry-derived routes once; during placement move fixed-support endpoints in board coordinates analytically as existing `moved()` does. Form route-length gradients from the endpoint-adjacent segment tangents, avoiding finite differences of the discrete exterior grid search. Use damped minimum-norm corrections from the bracket candidate, deterministic ordering, and backtracking; the regularized solve selects among underdetermined solutions. Cap placement at 64 corrections. Rebuild exact exterior routes and bearings only at the candidate selected for admission; permit at most four route-rebuild/placement cycles. Apply existing workspace bounds before index conversion. Require all final route-length residuals to be at most 1e-8 m. Never adopt a route's measured length as its source rope budget.
- [ ] **Admit only validated geometry.** Resample routes using the existing 2 mm segment target and each declared rope length once. Keep `projectInitialization`'s existing `geometryAccepted` preflight, including length/strain; do not use its contact projection as unrestricted length recovery. Require exact wood clearance, ordered threading, and proper centerline-crossing rejection before publication. An inconsistent taut-route system or a setup needing unsupported slack initialization fails explicitly and remains a catalog gap; do not reject merely by rope count when a feasible solution exists. Add one such slack setup as an explicit rejection regression, and retain it in the rollout record for a later swept, topology-preserving slack-seed adapter. Impossible short ropes and unsupported winding still fail without a published frame.
- [ ] **Run seed, solver, inter-cord, and Clavellium suites.** Expect zero failures including bounded-coordinate failures, cached-channel checks, initialization overlap separation, and the new origin/asymmetric fixtures.
- [ ] **Commit and push:** `fix: solve translated cord seed placement before admission`.

### Task 3: Prove vector contact, sweep, fallback, and physical tilt

**Files:** Modify `HangTenTests/RopeDynamicsSolverTests.swift`, `RopeContactSystemTests.swift`, `RopeInterContactTests.swift`, `ClavelliumRopePhysicsTests.swift`; fix affected solver/contact/sweep code only when a regression exposes it.

**Interfaces:** Use Task 1's vector state and unchanged solver `step(dt:targetOrientation:)` / `settled(targetOrientation:maxDuration:)`. `RopeLinearContact.border` remains `[Double]` and must match the complete backbone border count. Do not add a shipping debug backend switch merely to force a test.

- [ ] **Extend Task 1's production derivative/fallback coverage to motion.** Add lateral swept-wood traversal with clear endpoint poses and a colliding intermediate pose; it must reject transactionally. Extend the near-dependent production correction fixture to moving attached endpoints; require inactive linear residuals at least -1e-8 and agreement with the direct regularized system within 1e-7. Retain all existing resource limits and verify extra nonlocal borders follow the three board variables.
- [ ] **Extend rollback tests.** In the immovable-contact and lost-crossing fixtures, save full translation, linear velocity, orientation, positions, previous positions, and rest lengths. An infeasible tilt must exhaust only bounded retries, throw, and leave every saved field unchanged. A later valid command must still operate on the accepted state.
- [ ] **Replace Clavellium's fixed-pivot test with `testXTiltAndReturnPreserveCordConstraints`.** Test targets X +20°, -20°, 0 and retain Z 90°/180° reversal coverage. Require settlement within 5 simulated seconds, exact supports, unchanged rest lengths, the same central channel, and all engineering thresholds in Global Constraints. Assert loaded crossings are within radius plus declared clearance plus 0.2 mm of the relevant wood bearing. The average mouth center is not asserted steady.
- [ ] **Test time-step invariance through rotation.** Repeat identical sequences for exact deterministic results; compare 1/240 with 1/480 s steps on symmetric upright/X-tilt fixtures with position/contact differences below 0.2 mm. For asymmetric or Z-rotated flat-bearing cases, also report any neutral sideways displacement and compare reference height, bearing height, fixed supports, and all length/contact/topology metrics. Keep any failure of the strict positional gate explicit instead of broadening the tolerance or adding a centering spring. Add two continuous synthetic threaded loops using the same solver; both retain their own material budgets and avoid inter-cord contact. Log settling duration per target and keep damping 18 unchanged if a longer suspension misses the five-second gate.
- [ ] **Run the affected classes and full pure suite.** First capture each exposed failure, then make the minimum correction and expect zero failures. If a physical gate fails, record and fix that failure; do not loosen the tolerances to complete the task.
- [ ] **Commit and push:** `test: verify cord-constrained tilt and vector contact recovery` (include any regression-driven solver fixes).

### Task 4: Validate accepted transforms and lifecycle in the app

**Files:** Modify `HangTenTests/BoardModelRealityTests.swift`, `LiveRopeControllerTests.swift`, and `HangTen/Models/BoardModelRealityTypes.swift` / `LiveRopeController.swift` only as failures require. Update `docs/3D_SUSPENSION_AND_ODR.md`; create `docs/source-audits/2026-10-01-cord-constrained-translation.md` with actual results.

**Interfaces:** RealityKit receives Task 1's stored frame translation and composes `instanceBase * physicalTransform`. Controller scene/generation delivery contract and mesh radius contract remain unchanged.

- [ ] **Rewrite `testRenderedXTiltSharesPhysicsCordPivot` as `testRenderedXTiltMatchesAcceptedRigidTransform`.** Transform model origin and two distinct local points by the rendered entity matrix; compare against `base * (q.act(point) + frame.boardTranslation)` within 1e-7 m. Also verify support/tube geometry uses only the instance base transform. This proves render/physics agreement without an invented hinge.
- [ ] **Add lifecycle vector assertions.** In paired-instance placement, Reduce Motion, pause/resume, and stale-delivery tests, include nonzero X/Z translations. Pausing and stopping prevent stale lateral updates; one instance's translation never changes the other. Failed enabled physics enters the existing unavailable path after retaining the last accepted frame during retries.
- [ ] **Run native `BoardModelRealityTests`, `LiveRopeControllerTests`, and `LiveRopeMeshTests`.** Capture configuration and any timing-related timeout. Run a normal Debug build; if optimized Debug is used for expensive settling tests, report it separately and preserve the normal build result.
- [ ] **Validate current packages.** Run `rtk proxy env PYTHONPATH=Tools/HangboardPackages/src python3 -m hangboard_packages.cli validate --root Hangboards --final-inventory`. Expect exit 0 and unchanged Clavellium source/model/suspension/physics hashes for the runtime-only change.
- [ ] **Perform current-source isolated native review.** Read `validate-hang-ten-ios`; use DEBUG X rotation review routes to capture upright, +20°, -20°, and return frames, plus front/side/top views. Verify actual motion, board/cord contact, selecting and clearing a grip, orbit/reset, portrait/landscape bounds, Reduce Motion, and pause/resume. Save screenshots, ordered-frame provenance, commit/build configuration, and logs under `.context`. Present the screenshots before claiming completion.
- [ ] **Record truthful acceptance and cleanup.** Document numerical results, unavailable physical-device performance evidence if applicable, and exact simulator deletion verification. Update the ODR guide to replace the averaged pivot paragraph with the shared solved transform. Run `rtk proxy git diff --check`; commit and push documentation and verified integration fixes.

## Catalog handoff and completion boundary

This plan delivers the approved core workstream, not universal shipping coverage. After its gates pass, rediscover every represented setup from current manifests/sidecars and prepare package migration plans against retained evidence. Curved Mini Bar and Helium Mobile, exterior graphs, and independent paired models must each meet the same gates before live enablement. That work may need separate source/geometry specifications; it is not a metadata flag flip and is not authorized to invent hidden topology.

Maintain a per-package record of current renderer, supported graph, evidence/fit gaps, collision/admission/rotation results, and performance status. The user's full goal remains open until all represented cord setups are migrated and validated. Do not merge into the separately owned feature branch or claim full catalog completion as part of this core plan.

## Self-review

State/transform, shared reference, three-variable coupled solve, production assembly/fallback tests, history, and rendering are Task 1; initialization and large coordinate-origin changes are Task 2; motion sweeps, rollback, physical constraints, and determinism are Task 3; native lifecycle, visual review, package boundaries, documentation, and resource cleanup are Task 4. Catalog adoption, including unsupported slack seed adapters, is explicitly the next workstream. All five Review Focus conditions have named owning tasks. No device-performance claim is made without the required device measurement.

Execution recommendation: **Native**. These tasks change tightly coupled solver interfaces and share physical fixtures, so keeping implementation in one session avoids repeated interface handoffs. Use `superpowers:executing-plans` after the user reviews this plan and chooses the execution method.
