# Live Hangboard Cords Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Deliver live geometry-derived cord settling, first on Clavellium and then every represented corded board, with three times the existing rope diameter.

**Architecture:** A pure Swift chain solver consumes a hash-bound collision and topology descriptor. It computes sliding contacts and the board's vertical motion; a scene controller publishes valid snapshots to a reusable RealityKit tube mesh. Package adapters preserve each board's evidenced threading graph.

**Tech Stack:** Swift/simd, XCTest, RealityKit on iOS 18+, existing FreeCAD/Python package tooling and pytest. No new physics engine dependency.

**Spec:** [Approved design](../specs/2026-09-29-live-hangboard-cords-design.md).

## Global Constraints

- Preserve the project's iOS 18 minimum and existing model identity/ODR contract.
- Use three times each existing rope's diameter throughout the rollout. Apply the same increased radius to the rendered tube and the physics collider.
- Do not use a thin invisible collider beneath a thick rendered rope. Keep real source dimensions unchanged.
- A passage identifies an opening through which the cord must remain threaded; its center is not a fixed rope attachment.
- The current Clavellium 8 mm presentation remains as accepted by the user. Unknown grip-to-channel mappings are not invented.
- The USDZ remains the only Apple On-Demand Resource and ships without cords, material bindings, or textures. Do not commit generated `board.json` for a CAD package.
- Cord entities remain transient, non-pickable, and outside accessibility.
- Camera orbit remains a camera operation and does not rotate the board relative to gravity.
- Completion of the Clavellium milestone does not complete the catalog rollout.
- Use workspace-owned `.context/strong-owl-live-cords` artifacts. Record and trap-clean exact owned external resources, verify deletion, and push every new commit automatically.

## Review Focus

- A hole admits the original diameter but not the threefold diameter: reject fit without changing wood or silently using a smaller collider (Tasks 1, 3, 8).
- A segment crosses wood although its two particles clear it: segment and swept collision must reject the move (Tasks 2, 4).
- Rapid position changes arrive during solving: cancel superseded work and never apply a snapshot from an older scene/pose generation (Task 5).
- Two instances reference one model: immutable geometry may be shared; particles, velocities, supports, and lifecycle remain independent (Tasks 5, 8).
- Backgrounding or a long frame creates accumulated elapsed time: discard paused time and bound resumed work without losing topology (Tasks 4, 5).

## Verification commands

Use `rtk` for shell commands. Use the existing workspace Python environment at `.context/strong-owl-clavellium/venv/bin/python` when available; otherwise create a workspace-owned environment using the retained tool requirements.

Python checks below use:

```sh
rtk proxy env PYTHONPATH=Tools/HangboardPackages/src .context/strong-owl-clavellium/venv/bin/python -m pytest <test-path> -q
```

For native checks use `scripts/ci-run-xctest.sh`, configuring its required `XCTEST_*` variables, `XCTEST_PARALLEL_WORKERS=1`, and `XCTEST_DESTINATION=platform=iOS Simulator,id=<exact-owned-UUID>`. Create/register/trap-clean that simulator using the repository `validate-hang-ten-ios` skill; never use or delete an unknown/shared simulator. Set `XCTEST_ONLY_TESTING=HangTenTests/<test-class>` for focused tests and `HangTenTests` for final checks. Success means test exit zero and zero failed tests in the result bundle. Register new Swift source/test files in `HangTen.xcodeproj/project.pbxproj` with their owning task.

## Task 1: Physics descriptor, source binding, and thickness contract

**Files:** Create `Tools/HangboardPackages/src/hangboard_packages/rope_physics.py`, `Tools/HangboardPackages/tests/test_rope_physics.py`, `HangTen/Models/RopePhysicsDescriptor.swift`, and `HangTenTests/RopePhysicsDescriptorTests.swift`. Modify `board_catalog.py`, `cad_source.py`, `HangTen/Models/BoardPackageStore.swift`, `HangTen/Models/TrainingModels.swift`, `scripts/stage-board-packages.py`, and the Xcode project.

**Interfaces:**
- Python: `validate_rope_physics(document: dict, model_sha256: str) -> dict`; `derive_radius(baseline_radius: float, scale: float) -> float`.
- JSON file: `assets/primary.physics.json`, schema version 1; top-level model/source SHA-256, `coordinateSystem="hang-ten-board-v1"`, collision vertices/triangles, portals, channel regions, and profiles. `media.physicsDescriptorPath` selects it; profiles use `presentationID` and optional existing `instanceID` to identify their suspension setup.
- Each profile contains board-mass estimate/provenance and ropes. Each rope contains ID, baseline radius, thickness scale 3, derived radius, immutable total rest length, linear-mass estimate/provenance, support endpoints, ordered connection graph, and exterior winding where relevant. Node kinds are `support`, `attachment`, `portal`; edges are `free` or `channel`. Channel edges reference channel regions. A support is fixed in world space; an attachment in board space; a portal constrains a region rather than a point.
- Swift: `RopePhysicsDescriptor: Decodable, Sendable`, validated `RopePhysicsInput` with collision/portal/channel/profile data; `RopePhysicsDescriptor.validated(modelSHA256: String) throws -> RopePhysicsInput`. Positions/radii/lengths use metres and `Double`. Graph IDs are distinct strings. Profile rest lengths retain physical-rope rather than old display-branch semantics.
- Missing physics descriptor retains existing legacy behavior. Declared-but-invalid physics fails closed.

- [ ] Write matching Python/Swift tests for valid one-loop graph; dangling graph references; duplicate IDs/keys; unsupported coordinate basis; nonfinite/zero radius and length; missing estimate provenance; stale model hash; missing descriptor; unsafe/symlink path; repeated radius derivation.

```python
assert derive_radius(0.002, 3) == 0.006
assert derive_radius(0.002, 3) == derive_radius(0.002, 3)
# An impossible portal is not made larger by descriptor validation.
with pytest.raises(ValueError, match="fit"):
    validate_rope_physics(narrow_portal_with_12mm_rope, model_sha)
```

- [ ] Run the new Python suite and `RopePhysicsDescriptorTests`; verify the intended missing-contract failures.
- [ ] Implement the interfaces, validators, media parsing and staging. Keep physics JSON bundled alongside model descriptors, exclude authoring inputs, declare the generated asset in finished-package validation, and preserve canonical JSON ordering. Require length provenance for any legacy graph conversion; refuse an ambiguous total/per-lead split.
- [ ] Run descriptor and staging tests, including `test_board_package_staging.py` and existing `BoardPackageStoreTests`. Verify physics JSON remains available when the USDZ ODR asset is absent.
- [ ] Commit and push the contract changes.

## Task 2: Exact solid collision and sliding channel geometry

**Files:** Create `HangTen/Models/RopeTriangleCollider.swift`, `HangTenTests/RopeTriangleColliderTests.swift`, and `Tools/HangboardCAD/export_rope_physics.py`. Modify `Tools/HangboardCAD/compile_board.py`, `Tools/HangboardCAD/export_rope_collision_solid.py` only to share retained export code, and create `Tools/HangboardCAD/tests/test_rope_physics_export.py`.

**Interfaces:**
- Python/FreeCAD: `export_rope_physics(document, body_feature: str, channel_features: dict) -> dict` returns the Task 1 collision, portal, and region records. Authoring config resides in package `rope-physics.json`; it identifies body/channel features and topology facts, never pose contacts. Compilation adds geometry/source/model hashes and writes `assets/primary.physics.json` deterministically. Exclude `rope-physics.json` from staged resources.
- Swift: `RopeTriangleCollider.init(input: RopePhysicsInput) throws`; `signedDistance(at: SIMD3<Double>) -> Double` (positive outside); `closestSurface(at:) -> RopeSurfaceContact`; `segmentContact(from:to:radius:) -> RopeSegmentContact?`; `sweptSegmentContact(previousStart:previousEnd:start:end:radius:) -> RopeSegmentContact?`. Contact records carry closest centerline/surface points, outward normal, and penetration depth. Build a BVH once from immutable triangles.
- `RopePortalRegion` and `RopeChannelRegion` are geometric constraint regions in board space. Generated portal boundaries meet the actual body surface, not the overhanging tool ends. Derive regions from editable Box/Cylinder/pipe features; centerlines are only initialization hints.

- [ ] Write analytic closed-box and concave-channel tests. Assert signed distance is negative inside wood, positive in the channel; a segment through wood is detected with both endpoints outside; a swept segment cannot jump a wall; rotated importer-basis queries reproduce distances; oversized-radius portal erosion is empty and rejected. Test degenerate triangles and nonwatertight/mixed-winding input rejection.
- [ ] Run collider/native-export suites and verify failure before implementation.
- [ ] Implement the collider, conservative segment/swept queries, and FreeCAD exporter. Do not use the USDZ contact-overlay partition as a closed collider and do not fill channel voids with a convex hull. Export the Clavellium final `Pinch100BottomReliefCut` and `CenterChannelTool` identified in its approved audit.
- [ ] Run all new tests. Compare collider queries with exact native-solid geometry and independently sampled segments; repeat export twice and require identical JSON bytes. A coarse acceleration field cannot replace exact acceptance queries.
- [ ] Commit and push the collision/export changes.

## Task 3: Geometry-derived threaded initialization

**Files:** Create `HangTen/Models/RopeThreadedSeed.swift`, `HangTen/Models/RopeSimulationState.swift`, `HangTenTests/RopeThreadedSeedTests.swift`, and package `Hangboards/clavellium-training-block/rope-physics.json`. Modify CAD metadata using `Tools/HangboardCAD/set_board_manifest.py`, then compile the generated descriptor with the Task 2 exporter.

**Interfaces:** `RopeThreadedSeed.make(input: RopePhysicsInput, profileID: String, orientation: simd_quatd, collider: RopeTriangleCollider) throws -> RopeSimulationState`. State contains board height/vertical velocity and per-rope particle positions, previous positions/velocities, immutable link rest lengths, support-index constraints, and channel traversal membership. Start with at most 2 mm link spacing; refine near rims as necessary without changing total rest length. No mouth-center pinned particles.

- [ ] Test the central Clavellium loop: one chain from support through both portals/hidden channel back to support; total rest length 0.55 m; radius 0.006 m; each internal segment stays in the chosen channel; every finite-radius segment clears wood. Assert impossible length or eroded portal throws. Assert source opening centers may remain unchanged while seed bearing coordinates differ. Ignore `cordContactPoints` when generating the seed.
- [ ] Run `RopeThreadedSeedTests` and the package exporter test to establish failure.
- [ ] Implement an automatically derived collision-free seed within the connection/winding class and solve initial board height for feasible loop length. Retained offline pathfinding can inform the algorithm; copied cached pose contacts cannot become fixed constraints. Use annotated display estimates of board mass 1 kg and rope linear mass 0.01 kg/m only if primary measurements are absent; initial gravity is `(0,-9.81,0)` m/s². These estimates must appear in descriptor provenance.
- [ ] Regenerate Clavellium metadata/physics and run seed, fit, package and source-hash tests. Verify the threefold radius derives from a retained baseline, not from already enlarged metadata.
- [ ] Commit and push initialization and the source-bound physics inputs, without enabling unproven live rendering.

## Task 4: Coupled live dynamics and numerical acceptance

**Files:** Create `HangTen/Models/RopeDynamicsSolver.swift`, `HangTen/Models/RopeSimulationMetrics.swift`, `HangTenTests/RopeDynamicsSolverTests.swift`, and `HangTenTests/ClavelliumRopePhysicsTests.swift`. Modify the unfinished `test_rectangular_channel_section.py` regression only to replace the nonexistent static seating-helper expectation with coverage of the actual sliding-contact mechanism; retain the floating-mouth defect assertion in native physics tests.

**Interfaces:** `RopeDynamicsSolver.init(input: RopePhysicsInput, state: RopeSimulationState, collider: RopeTriangleCollider)`; `mutating step(dt: Double, targetOrientation: simd_quatd) throws -> RopeFrameSnapshot`; `mutating settled(targetOrientation: simd_quatd, maxDuration: Double) throws -> RopeFrameSnapshot`. Snapshot contains board transform, rope positions/radii, settled flag and `RopeSimulationMetrics` (total-length error, max local strain, minimum segment clearance, topology validity, maximum speed, and board displacement history).

- [ ] Write deterministic chain, contact and coupled-board tests, then actual Clavellium tests for upright/90°/180° physical rotations, repeated reversals, initial perturbation, time-step halving, impossible input, and nonfinite state. Upright expected bearing lies within 0.0003 m of the wood beyond the 0.006 m radius; require automatic portal sliding rather than pin movement in authoring data.

```swift
XCTAssertLessThanOrEqual(metrics.totalLengthError, 0.0005)
XCTAssertLessThanOrEqual(metrics.maximumLocalStrain, 0.005)
XCTAssertGreaterThanOrEqual(metrics.minimumSegmentClearance, 0.00595)
XCTAssertTrue(metrics.topologyValid)
// After <= 5 simulated seconds, require speed < .001 m/s and
// board displacement < .0001 m over the final .5 s.
// Half-step/repeat contact and endpoint differences must be < .0002 m.
```

- [ ] Run the solver test classes and verify failure before implementation.
- [ ] Implement fixed-step XPBD at 1/240 s, coupled vertical board motion, fixed supports/true attachments, sliding region constraints, length/contact corrections and segment self-contact. Exclude connected neighboring links and the intentional common-support endpoint from self-contact; test that this exclusion does not permit crossings at a mouth or along free spans. Warm-start state through bounded physical rotations. Use displacement-limited substeps/swept queries to prevent wood traversal. Measure both local and global residuals; replace local length projection with a stiff-chain/simultaneous solve if it cannot pass the specified gates.
- [ ] Run deterministic acceptance, 1/480 s comparisons and self-intersection tests against the actual CAD collision solid. Reject a nonconverged/nonfinite solution explicitly; never report a stretched but visually plausible rope as passing.
- [ ] Commit and push only after the numerical gate passes. If it fails, continue correcting the core before adding an enabled app integration.

## Task 5: Scene controller, pose transitions, and lifecycle

**Files:** Create `HangTen/Models/LiveRopeController.swift`, `HangTenTests/LiveRopeControllerTests.swift`; modify `HangTen/Models/BoardModelRealityTypes.swift`, `HangTen/Views/BoardModelView.swift`, and `HangTenTests/BoardModelRealityTests.swift`.

**Interfaces:** A controller owns one Task 4 solver per physical board instance, on a dedicated serial worker; `setTarget(orientation: simd_quatd, generation: UInt64)`, `advance(elapsed: Double)`, `pause()`, `resume()`, `stop()`. Main-actor frame delivery includes scene and pose generation IDs. A clock-independent test interface returns snapshots after an exact step count. Shared collider data remains immutable.

- [ ] Write fake-clock tests for rapid A→B→A selection, two independent instance states, obsolete async snapshots, deallocation and repeated clear/reselect. Assert paused time is discarded; elapsed time is capped at 1/30 s and at most eight 1/240 s substeps per displayed frame; solver sleeps after acceptance and wakes only for physical changes. Camera orbit must leave simulation state unchanged.
- [ ] Run `LiveRopeControllerTests` and the corresponding scene tests to establish failure.
- [ ] Implement the worker/controller and one cancellable `SceneEvents.Update` subscription per active scene. Integrate pause/resume with visibility and app activity, and stop on scene release. Position selection changes target orientation rather than replacing the chain. Keep the current 8 mm canonical presentation; add DEBUG physical-rotation controls only for testing.
- [ ] Run lifecycle/scene tests. Declared invalid physics enters the existing unavailable state; legacy profiles lacking physics retain the existing path. Verify no subscriptions or work survive scene teardown and no stale snapshot moves a new scene.
- [ ] Commit and push the controller/integration changes.

## Task 6: Dynamic tube mesh, accessibility, and Reduce Motion

**Files:** Create `HangTen/Models/LiveRopeMesh.swift`, `HangTenTests/LiveRopeMeshTests.swift`; modify the scene/view integration from Task 5 and existing suspended-camera framing as needed.

**Interfaces:** `LiveRopeMesh.init(capacity: Int, radialSegments: Int, radius: Float) throws`; `update(snapshot: RopeFrameSnapshot) throws`; reusable mesh/entity buffers, radius derived from Task 1. Render hidden chain segments through normal depth occlusion. Main-thread entity updates consume immutable snapshots.

- [ ] Test tube radius 0.006 m, finite normals for straight/near-collinear chain spans, stable buffer/entity identity over 1,000 updates, and capacity growth without dangling buffers. Assert no collision/picking component or cord accessibility element. Assert camera framing contains board and rope during transitions and after sleep.
- [ ] Run mesh and scene accessibility tests before implementation.
- [ ] Implement reusable `LowLevelMesh` updates without per-frame entity trees. Respect Reduce Motion by computing a validated settled snapshot on the worker and applying it without visible dynamics. Give display-only picker cards a settled snapshot rather than keeping every offscreen card ticking. Keep camera stable during motion and refit once settled.
- [ ] Run mesh, picking, framing and Reduce Motion tests; verify retained ODR lease and board contact highlight identity. Validate geometry before publishing a frame.
- [ ] Commit and push dynamic rendering changes.

## Task 7: Clavellium delivery, visual proof, and performance

**Files:** Modify `docs/source-audits/2026-09-29-clavellium-suspension-and-accuracy.md`, its evidence directory, `docs/model-delivery-lock.json`, `docs/HANGBOARD_CORD_AUTHORING.md`, and `docs/3D_SUSPENSION_AND_ODR.md`. Include the existing uncommitted outward-pinch-normal correction and its regression only after its separate validation succeeds; keep the accepted 8 mm pose.

**Interfaces:** The public package enables physics only after Tasks 1–6 gates pass. Retain physics/source/model hashes, exact test results and screenshot/recording provenance in its audit.

- [ ] Build/test current source on an isolated owned iOS Simulator using `validate-hang-ten-ios`; run the full `HangTenTests` suite. Test actual portrait/landscape selection, workout-driven position, orbit/reset, clear/reappear, pause/resume, accessibility and Reduce Motion. Review a recording of upright/DEBUG90°/DEBUG180° settling at threefold thickness.
- [ ] Render front/side/top before/after comparisons against the prior committed model and present native screenshots plus the settling recording. Compare actual mouth bearing with the source-approved channel; never assign unknown grip/channel mappings. Confirm the corrected 80 mm pinch faces remain visible and pickable.
- [ ] Run all model/package Python tests, final inventory validation, deterministic CAD/physics rebuild, staging parity and `rtk proxy python3 scripts/verify-model-delivery.py`. Refresh the delivery lock only from final promoted bytes and final validation evidence. Resolve the unfinished static helper regression from Task 4 before the broad suite.
- [ ] Profile on an available physical iPhone, record model/OS and p95 simulation-plus-mesh cost, targeting <4 ms and 60 fps. If no device is accessible, deliver the numerical/Simulator evidence and explicitly retain the device-performance gate as unverified; do not claim it passed or mark all required work complete.
- [ ] Clean/verify deletion of all exact owned resources, then commit and push final Clavellium assets, audits and evidence. Do not claim catalog rollout complete.

## Task 8: Catalog adapters and every corded-board promotion

**Files:** Extend Task 2 exporter for curved pipes and cylinders; add `Tools/HangboardPackages/tests/test_live_cord_inventory.py` and `HangTenTests/CatalogRopePhysicsTests.swift`. Modify the 15 package inputs listed in the spec and their audits/physics descriptors, plus `Tools/HangboardPackages/src/hangboard_packages/cord_audit.py` and the delivery lock. Source-based CAD migrations use `migrate-hangboard-to-3d`; all suspension decisions use `audit-3d-hangboard-suspension`.

**Interfaces:** The same Task 1 graph and Task 4 solver handle fixed attachment leads, sliding through-passages and exterior wraps. Each paired instance receives its own profile/support/state. `CatalogRopePhysicsTests` discovers enabled profiles at execution time rather than hard-coding the current count.

- [ ] Write inventory tests that discover native manifests and sidecars alongside legacy board documents, initially finding 15 corded boards/17 setups. Assert each represented setup has a reviewed graph, retained baseline radius, threefold rendered/collision radius, fit verdict, and per-canonical-pose numerical/visual coverage. A board omitted from promotion remains a failing coverage item with an explicit reason.
- [ ] Run catalog coverage to establish the unpromoted-board failures.
- [ ] Promote Mini Bar curved channels and Helium Mobile rounded ends first; run the full numerical gate for every canonical pose and both loops. Then audit and adapt the remaining exterior leads/wraps and paired Rock Rings/Penta instances. Preserve sourced Captain Fingerfood lip-to-recess paths without inventing bores. Refuse ambiguous rope-length conversion. Obtain missing evidence only where the existing retained source cannot establish topology; do not invent it.
- [ ] For every thick rope, erode its actual passage by the increased radius and verify a connected feasible region. Report genuine fit conflicts; changing source dimensions or using a thinner collider requires a changed user requirement and is outside this plan. Improve collision/source geometry only from approved primary evidence, with front/side/top before/after review.
- [ ] Run numerical and native visual gates for every profile/pose, including rapid transitions, paired-state independence, self-contact and lifecycle. Legacy nonwatertight meshes require a validated source-based collision solid before promotion. Run final package inventory, cord audit, staging/hash parity, Python/native suites, source rebuilds and cleanup checks.
- [ ] Update each source audit and delivery lock, commit and push board groups as they pass. Final completion requires all catalog profiles passing; any evidence, fit, convergence or device gate left unresolved must be reported concretely rather than counted as coverage.

## Plan self-review and execution handoff

Spec coverage: contract/estimates/thickness (Tasks 1, 3, 8); exact geometry and topology (2–4); live motion and numerical gates (4); lifecycle/instances (5); mesh/camera/accessibility/Reduce Motion (6); visual/device/delivery evidence (7); complete catalog (8). Every Review Focus condition has a named owning test step. Task interfaces carry matching input/state/snapshot types; tests precede implementation and each completed task ends with a pushed commit.

Recommended execution: Native, implementing the tasks sequentially in this session with a fresh whole-branch review. The collision, initialization, solver and scene interfaces are tightly coupled, so parallel implementation would add coordination before the first numerical gate is established. A delegated execution method remains available if selected by the user.
