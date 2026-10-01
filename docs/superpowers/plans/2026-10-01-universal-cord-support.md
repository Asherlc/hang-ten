# Shared Cord Constraints Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Solve board translation and continuous cords together during controlled tilt, replacing the averaged pivot in the shared live solver.

**Architecture:** Keep prescribed orientation; add three translational degrees of freedom to the existing coupled mass-metric constraint solve. Publish that rigid transform directly to RealityKit. Establish generic fixtures and Clavellium first; catalog migration requires separate evidence-backed package work.

**Tech Stack:** Swift 5, SIMD, Accelerate/LAPACK, XCTest, RealityKit, Python package validators; existing iOS 18 minimum.

**Spec:** [Approved design](../specs/2026-10-01-universal-cord-support-design.md), approved by the user on 2026-10-01.

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

**Files:** Modify `HangTen/Models/RopeSimulationState.swift`, `RopeSimulationMetrics.swift`, `RopeDynamicsSolver.swift`, `RopeThreadedSeed.swift`, `RopeBandedSystem.swift`, and `BoardModelRealityTypes.swift`. Migrate affected constructors/assertions in `HangTenTests/RopeDynamicsSolverTests.swift`, `RopeThreadedSeedTests.swift`, `RopeInterContactTests.swift`, `ClavelliumRopePhysicsTests.swift`, `BoardModelRealityTests.swift`, and `LiveRopeControllerTests.swift`.

**Interfaces:**
- `RopeSimulationState`: `boardTranslation: SIMD3<Double>`, `boardLinearVelocity: SIMD3<Double>` replace scalar fields and pivot; retain `worldPoint(_:)` and `boardPoint(_:)` signatures. Linear velocity refers to the body's numerical mass-reference point, not an arbitrarily chosen importer origin.
- `RopeFrameSnapshot`: stored `boardTranslation: SIMD3<Double>` replaces height/pivot; retain orientation, ropes, settled, and metrics.
- `RopeSimulationMetrics.measure(state:input:collider:boardHistory:includeSelfContact:channelCache:)`: history becomes `[SIMD3<Double>]`.
- `RopeDynamicsSolver.correctionFraction(ropes:corrections:boardCorrection:) -> Double`: final argument is `SIMD3<Double>`.
- Public solver `init`, `step`, `settled`, and `prepareDisplay` signatures remain unchanged.

- [ ] **Write the failing lateral-support regression.** Extend the existing two-attachment cube fixture: local attachments `(x, 0.02, 0.008)`, supports `(x, 0.12, 0.018)`, `x = ±0.008`, two 0.1 m ropes. Run upright settling from its taut slanted seed. Expected translation is `(0, 0, 0.01)` within 0.2 mm; both supports are exact and attachment particles equal `state.worldPoint(local)`. The scalar solver can adjust height but cannot reach this lateral equilibrium. Record its failing result before changing implementation.
- [ ] **Add tests `testLateralBoardVelocityPreventsSettling` and `testVectorTrustUsesAttachmentMotion`.** Keep height steady while assigning 0.01 m/s X or Z velocity; metrics must report at least 0.01 m/s. For a 0.1 m link with one fixed support and a 0.02 m transverse attachment correction, the relative-link trust fraction must be 0.5. A common 0.02 m particle/body translation with no fixed support must have fraction 1.
- [ ] **Run `RopeDynamicsSolverTests` and `RopeThreadedSeedTests` with the verification template.** Expect the lateral behavior assertion to fail on current code; subsequently missing vector interfaces may fail compilation until the atomic migration is complete. Preserve the behavioral red-run log.
- [ ] **Migrate state, frames, metrics, and callers atomically.** Implement `worldPoint(p) = q.act(p) + translation` and its inverse. Use vector gravity `(0, -9.81, 0)`, existing damping 18 and angular-speed bound 2.1 rad/s. Compute speed with vector norm and history displacement as the maximum Euclidean distance between any two samples in the retained final-half-second history. Validate every translation/velocity component as finite.
- [ ] **Keep prediction independent of importer origin.** Derive private solver `bodyReferencePoint: SIMD3<Double>` from the collision bounds midpoint, explicitly a numerical mass-location estimate. It translates with model coordinates and is never pinned. Preserve this point's world position when applying the orientation predictor: add `oldQ.act(reference) - newQ.act(reference)` to predicted translation, then integrate its gravity/damped linear velocity. Reconstruct velocity and displacement history from `state.worldPoint(reference)`. The correction mass metric still uses the difference of translations because orientation is fixed during that solve. This reference must not add a hinge constraint or average portal positions.
- [ ] **Generalize the complete coupled solve.** `ConstraintRow.boardGradient` becomes `SIMD3<Double>`; correction results use `boardCorrection`. Board border indices are X/Y/Z at 0/1/2, with nonlocal constraint borders starting at 3. Mass block is `mass * identity(3)`. For distance constraints, sum gradients of attached endpoints; for wood/portal contact, also subtract the sum of all endpoint world gradients. Include attachment effects in self/inter-cord rows. Expand tension curvature into the full 3×3 board block and particle/body cross terms. Update merit, fallback extraction, inactive inequalities, line search, relative trust, velocity reconstruction, and transactional state together.
- [ ] **Update seed and renderer call sites for the new representation.** For this task only, retain height bracketing as a candidate generator with zero lateral translation; remove averaged-pivot compensation. Seed and render use the identical rigid transform. Camera rotation bounds use the transformed model-bounds center and its corner radius, never a physical pivot. Replace old fixed-mouth-center assertions with transform agreement/physical acceptance; preserve tests of true attachments and fixed supports.
- [ ] **Run all six pure suites:** `RopePhysicsDescriptorTests`, `RopeTriangleColliderTests`, `RopeThreadedSeedTests`, `RopeDynamicsSolverTests`, `RopeInterContactTests`, `ClavelliumRopePhysicsTests`. Expect zero failures, including lateral support and existing upright/threading regressions. Compile the native app to catch migrated UI callers.
- [ ] **Commit and push** the coherent vector migration: `feat: solve cord-supported board translation in three dimensions`.

### Task 2: Admit feasible translated seeds without an authored pivot

**Files:** Modify `HangTen/Models/RopeThreadedSeed.swift`, `RopeDynamicsSolver.swift` initialization only, `HangTenTests/RopeThreadedSeedTests.swift`.

**Interfaces:** Keep `RopeThreadedSeed.make(input:profileID:orientation:collider:placement:) throws -> RopeSimulationState`. Extract private `makeRoutes(translation: SIMD3<Double>) throws -> [Route]` and `solvePlacement(initial: SIMD3<Double>) throws -> SIMD3<Double>` within the seed implementation; route type remains private. Callers still use `prepareDisplay` for first-frame admission.

- [ ] **Write `testAsymmetricLeadsHaveFeasibleTranslatedSeed`.** Reuse two local X-separated attachments but choose distinct support offsets/rest lengths whose exact common translation is known. Construct supports from common translation `(0, 0, 0.03)` plus distinct vertical lead lengths 0.1 and 0.12 m. Verify first admitted frame has exact supports, immutable declared total lengths, and accepted geometry. The old scalar-height solve rejects these incompatible seed heights, despite the known feasible lateral placement.
- [ ] **Write `testChangingBoardOriginPreservesWorldSimulation`.** Shift every board-local collision vertex, portal, channel vertex/spine, and attachment by `(0.013, -0.009, 0.017)` while leaving supports unchanged. Compare original and shifted fixtures through upright and X ±20° settling: `q.act(p)` changes by `q.act(shift)`, so translations must differ by its negative. World attachment, rope, and bearing differences must stay below 0.2 mm. Cover the synthetic attachment fixture and actual Clavellium input.
- [ ] **Run the seed class; expect scalar-candidate placement failure and/or origin-dependent world results.** Retain the red log.
- [ ] **Implement bounded deterministic placement.** Retain the existing bracket as a fast candidate. When it cannot provide mutually compatible routes, minimize route-length residuals over the three translation variables using a damped least-squares step with finite-difference route evaluations, deterministic ordering, and backtracking. Cap placement at 64 iterations and the existing bounded seed workspace; reject nonfinite/oversized candidates before index conversion. Recompute geometry-derived bearing and exterior routes for every candidate. Never adopt a route's measured length as its source rope budget.
- [ ] **Admit only validated geometry.** Resample routes using the existing 2 mm segment target and each declared rope length once. `prepareDisplay` must jointly correct candidate translation and particles before publication. If a candidate needs recovery of length residuals, initialization preflight may admit those residuals only; exact wood clearance, ordered threading, and proper centerline-crossing rejection remain mandatory. The final first frame must pass every geometry metric. Test an impossible short rope and unsupported winding still fail explicitly with no published frame.
- [ ] **Run seed, solver, inter-cord, and Clavellium suites.** Expect zero failures including bounded-coordinate failures, cached-channel checks, initialization overlap separation, and the new origin/asymmetric fixtures.
- [ ] **Commit and push:** `fix: solve translated cord seed placement before admission`.

### Task 3: Prove vector contact, sweep, fallback, and physical tilt

**Files:** Modify `HangTenTests/RopeDynamicsSolverTests.swift`, `RopeContactSystemTests.swift`, `RopeInterContactTests.swift`, `ClavelliumRopePhysicsTests.swift`; fix affected solver/contact/sweep code only when a regression exposes it.

**Interfaces:** Use Task 1's vector state and unchanged solver `step(dt:targetOrientation:)` / `settled(targetOrientation:maxDuration:)`. `RopeLinearContact.border` remains `[Double]` and must match the complete backbone border count. Do not add a shipping debug backend switch merely to force a test.

- [ ] **Add finite-difference tests for all three body derivatives.** Extend `testSlidingPortalGradientsIncludeBoardHeightAndAttachments` into a vector test: perturb translation by ±1e-7 m per axis and compare the central-difference residual derivative with the row derivative within 1e-6. Cover free/free and attached/free capsule contact and sliding boundaries. Add lateral swept-wood traversal with clear endpoint poses and a colliding intermediate pose; it must reject transactionally.
- [ ] **Add three-body-border contact tests.** Extend existing ill-conditioned contact fixtures to a three-variable board block with nonzero X/Z coefficients. Assert the fallback executes, all inactive residuals are at least -1e-8, and its solution agrees with the direct regularized system within 1e-7. Cover nonlocal cord borders following the three body variables; retain all existing resource limits.
- [ ] **Extend rollback tests.** In the immovable-contact and lost-crossing fixtures, save full translation, linear velocity, orientation, positions, previous positions, and rest lengths. An infeasible tilt must exhaust only bounded retries, throw, and leave every saved field unchanged. A later valid command must still operate on the accepted state.
- [ ] **Replace Clavellium's fixed-pivot test with `testXTiltAndReturnPreserveCordConstraints`.** Test targets X +20°, -20°, 0 and retain Z 90°/180° reversal coverage. Require settlement within 5 simulated seconds, exact supports, unchanged rest lengths, the same central channel, and all engineering thresholds in Global Constraints. Assert loaded crossings are within radius plus declared clearance plus 0.2 mm of the relevant wood bearing. The average mouth center is not asserted steady.
- [ ] **Test time-step and origin invariance through rotation.** Repeat identical sequences for exact deterministic results; compare 1/240 with 1/480 s steps at settled targets with position/contact differences below 0.2 mm. Add two continuous synthetic threaded loops using the same solver; both retain their own material budgets and avoid inter-cord contact.
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

State/transform, three-variable coupled solve, history, and rendering are Task 1; initialization and coordinate-origin invariance are Task 2; fallback, sweeps, rollback, physical constraints, and determinism are Task 3; native lifecycle, visual review, package boundaries, documentation, and resource cleanup are Task 4. Catalog adoption is explicitly the next workstream. All five Review Focus conditions have named owning tasks. No device-performance claim is made without the required device measurement.

Execution recommendation: **Native**. These tasks change tightly coupled solver interfaces and share physical fixtures, so keeping implementation in one session avoids repeated interface handoffs. Use `superpowers:executing-plans` after the user reviews this plan and chooses the execution method.
