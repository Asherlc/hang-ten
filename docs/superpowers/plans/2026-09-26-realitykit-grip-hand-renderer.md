# RealityKit grip-hand renderer Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace Hang Ten's last SceneKit renderer, the interactive 3D grip-hand illustration, with a visually and behaviorally equivalent RealityKit view.

**Architecture:** Retain `GripHandAsset`, `GripHandPose`, JSON validation, and all call sites. Bake per-finger highlight colors from authored `digitIndices` and `highlightWeights` into a RealityKit `LowLevelMesh`; use a Metal `CustomMaterial` surface shader to read interpolated vertex colors and preserve PBR lighting. Host the model plus orthographic camera in `RealityView`, move pan/pinch handling to SwiftUI gestures, and remove SceneKit-only orbit fixtures.

**Tech Stack:** Swift, SwiftUI `RealityView`, RealityKit `LowLevelMesh`/`MeshResource`/`CustomMaterial`, Metal surface shader, `OrthographicCameraComponent`, XCTest, iOS Simulator.

**Spec:** `docs/superpowers/specs/2026-09-26-realitykit-grip-hand-renderer-design.md`

## Global Constraints

- Keep the `hand-mesh.json` schema and Blender authoring/export pipeline unchanged.
- Preserve all existing `GripHandCueCardTests` and their source-fidelity guarantees.
- Remove SceneKit imports and APIs from the grip-hand renderer and its tests; after migration, application and test targets must have no SceneKit dependency.
- Use a RealityKit `CustomMaterial` surface shader to read interpolated `LowLevelMesh` vertex colors; a standard PBR material alone ignored the color attribute in the device probe.
- Do not add a SceneKit fallback, new package dependency, anatomical claims, or changes to workout prescription data.
- Preserve explicit finger membership; never infer it from grip type or finger count.

## Review Focus

- A missing or invalid bundled mesh must continue to show “3D hand unavailable.” Test via a failed/injected asset load and assert the unavailable state is presented.
- An empty finger selection must render the warm neutral hand. Test the `Neutral` color buffer for an empty set.
- Selected-finger highlights must not bleed onto another digit, and authored weights must remain smooth. Test vertices for one selected finger and compare the RealityKit render probe with expected colors.
- Mirroring must not invert visible faces or corrupt normals. Test left/right transforms and visually inspect both sides.
- Zero-size viewports and invalid/non-finite gesture deltas must not produce invalid camera transforms. Test no-op behavior and a subsequent valid resize/orbit.

---

### Task 1: Add exact highlight-color mapping

**Files:**
- Modify: `HangTen/Views/GripHandModelView.swift`
- Test: `HangTenTests/GripHandOrbitTests.swift`

**Interfaces:**
- Consumes: `GripHandAsset`, `GripHandPose`, `FingerSlot`.
- Produces: `GripHandRealityMeshBuilder.vertexColors(asset:action:selectedFingers:) throws -> [SIMD4<Float>]`.

- [x] **Step 1: Write the failing color-mapping tests**

Add tests using a decoded three-vertex fixture with `digitIndices = [2, 3, 4]`, `highlightWeights = [1, 0.5, 1]`, and shared test pose buffers. Assert empty selection returns the exact base linear color `[0.687, 0.392, 0.242, 1]`; selecting `.index` returns `[0.966, 0.0615, 0.0108, 1]` at vertex 0 and leaves vertices 1 and 2 at base; selecting `.middle` produces the 50% interpolation at vertex 1; selecting `.index` and `.ring` highlights only those two vertices. Test `Pocket0` and a posture with explicit fingers to prove geometry action and color membership remain independent.

- [x] **Step 2: Run tests and verify the missing-builder failure**

Run: `rtk xcodebuild test -project HangTen.xcodeproj -scheme HangTen -sdk iphonesimulator -configuration Debug -derivedDataPath .context/DerivedData -only-testing:HangTenTests/GripHandOrbitTests`
Expected: compile failure because `GripHandRealityMeshBuilder.vertexColors` is not implemented.

- [x] **Step 3: Implement the pure color builder**

Add `GripHandRealityMeshBuilder.vertexColors(asset:action:selectedFingers:) throws -> [SIMD4<Float>]`. Map `.index/.middle/.ring/.pinky` to authored digit indices `2/3/4/5`, ignore thumb/palm digits `0/1`, clamp each selected authored weight to `0...1`, and linearly interpolate the exact base/highlight values above. Read the requested action's already-validated pose and preserve one output color per authored vertex.

- [x] **Step 4: Run color-mapping tests**

Run the focused `GripHandOrbitTests` command above.
Expected: all color-mapping tests pass; existing orbit tests remain green.

- [x] **Step 5: Commit the color mapping**

```bash
rtk git add HangTen/Views/GripHandModelView.swift HangTenTests/GripHandOrbitTests.swift
rtk git commit -m "test: characterize grip hand highlight colors"
```

### Task 2: Build and render RealityKit hand meshes

**Files:**
- Modify: `HangTen/Views/GripHandModelView.swift`
- Create: `HangTen/Rendering/GripHandSurfaceShader.metal`
- Modify: `HangTen.xcodeproj/project.pbxproj`
- Test: `HangTenTests/GripHandOrbitTests.swift`

**Interfaces:**
- Consumes: `GripHandRealityMeshBuilder.vertexColors(asset:action:selectedFingers:)` from Task 1.
- Produces: `@MainActor final class GripHandRealitySurface` with `let root: Entity`, `let modelEntity: ModelEntity`, read-only `vertexCount` and `triangleCount` values, `func apply(_ pose: GripHandPose) throws`, and `func posedVerticesForFraming() -> [SIMD3<Float>]`.

- [ ] **Step 1: Add a failing RealityKit mesh test**

Add `testRealityMeshUsesBundledPosePositionsNormalsAndIndices` to load `GripHandAsset.bundled`, build the `HalfCrimp` RealityKit mesh, and assert `modelEntity.model` exists, vertex count equals `asset.vertexCount`, triangle count equals `asset.indices.count / 3`, and framed bounds are finite/nonempty. Run it against the absent `GripHandRealitySurface` API to capture RED before writing mesh code.

- [ ] **Step 2: Confirm the RealityKit CustomMaterial vertex-color path**

While the old SceneKit renderer remains intact, add `[[visible]] void gripHandSurfaceShader(realitykit::surface_parameters params)` in the new Metal file; it reads the interpolated geometry color and sets the fragment base color. Register the `.metal` file in the HangTen target. Add a minimal DEBUG-only RealityKit mesh probe to the existing review route. Feed the bundled `HalfCrimp` positions, normals, indices, and Task 1 colors through `LowLevelMesh` color attributes and `MeshResource`, use a `CustomMaterial` initialized from the neutral PBR material, then run on an isolated simulator and capture neutral, `.index`, and `.index/.ring` screenshots. Confirm authored interpolation, selected highlights, and unselected digits against SceneKit before implementing the production surface. If the CustomMaterial probe fails, stop and revise the design rather than approximating the appearance.

- [ ] **Step 3: Implement `GripHandRealitySurface`**

Create RealityKit mesh data from each existing pose's positions, normals, `asset.indices`, and Task 1 vertex colors. Keep at most three recently used colored pose meshes per surface, keyed by both action and selected finger set. Apply updates without implicit animation. Expose the posed positions for camera bounds. Use the verified `CustomMaterial` surface shader with a neutral PBR base (roughness 0.9, metalness 0) matching the existing matte appearance; retain the current mesh winding and double-sided visual behavior.

- [ ] **Step 4: Verify mesh creation and color rendering**

Run `GripHandOrbitTests` and inspect the neutral, one-finger, and two-finger DEBUG screenshots for left and right hands. Expected: same evaluated mesh silhouette, smooth warm-to-orange transition only on selected finger surfaces, no visible face loss after mirroring.

- [ ] **Step 5: Commit the RealityKit mesh**

```bash
rtk git add HangTen/Views/GripHandModelView.swift HangTen/Rendering/GripHandSurfaceShader.metal HangTen.xcodeproj/project.pbxproj HangTenTests/GripHandOrbitTests.swift
rtk git commit -m "feat: render grip hand mesh with RealityKit"
```

### Task 3: Port camera, bounds framing, lighting, and orbit controls

**Files:**
- Modify: `HangTen/Views/GripHandModelView.swift`
- Test: `HangTenTests/GripHandOrbitTests.swift`

**Interfaces:**
- Consumes: `GripHandRealitySurface` from Task 2.
- Produces: `@MainActor final class GripHandRealityScene` with `init(assetResult: Result<GripHandAsset, Error> = GripHandAsset.bundled)`, `let root: Entity`, `let camera: Entity`, `var isUnavailable: Bool { get }`, `func update(pose: GripHandPose, side: GripCueSide, viewportSize: CGSize, resetToken: Int)`, `func orbit(azimuthDelta: Float, elevationDelta: Float, zoomScale: Float = 1)`, and `func resetCamera()`.

- [ ] **Step 1: Write failing camera and transform tests**

Replace the SceneKit-specific test harness with RealityKit scene setup. Keep `testFullAzimuthOrbitReturnsCameraToItsStartingPosition` and `testOrbitZoomIsBoundedAndResetRestoresCanonicalFraming`, asserting the same full-turn tolerance (`1e-3` positions), zoom bounds (`0.75...1.35`), elevation bounds (`-0.55...0.55`), and reset behavior through the RealityKit camera entity. Add tests that side changes mirror the hand, pose/side changes refit the authored posed bounds, zero-size frames avoid NaN/infinity, and invalid gesture deltas do not move the camera.

- [ ] **Step 2: Run tests to confirm missing RealityKit scene behavior**

Run: `rtk xcodebuild test -project HangTen.xcodeproj -scheme HangTen -sdk iphonesimulator -configuration Debug -derivedDataPath .context/DerivedData -only-testing:HangTenTests/GripHandOrbitTests`
Expected: compile failures for the new `GripHandRealityScene` camera API.

- [ ] **Step 3: Implement `GripHandRealityScene`**

Own the root, hand entity, and entity with `OrthographicCameraComponent`. Port the current explicit camera basis calculation, palm-oblique offsets `(±5.8, 2.75, 9.4)`, fit padding `1.08`, fallback aspect `0.85`, bounded azimuth/elevation/zoom, and reset-token behavior. Recompute canonical framing on viewport, pose, or side change. Add RealityKit lighting/environment components that bring neutral and highlighted hand appearance close to the existing SceneKit reference; tune against Task 2's neutral, index, and index+ring reference screenshots, preserving the exact vertex-color interpolation. Expose the entity camera for the RealityView host; Task 4 installs it as the active RealityView camera.

- [ ] **Step 4: Run camera, transform, and lighting visual checks**

Run focused `GripHandOrbitTests` and capture the three Task 2 color states for both sides on the isolated simulator.
Expected: full azimuth returns to canonical camera transform; scale clamps to canonical `/1.35` and `/0.75`; reset restores camera framing; bad inputs leave transforms finite and unchanged; the neutral material remains warm matte and selected-finger brightness/contrast is close to the SceneKit reference without changing which vertices are highlighted.

- [ ] **Step 5: Commit camera/orbit support**

```bash
rtk git add HangTen/Views/GripHandModelView.swift HangTenTests/GripHandOrbitTests.swift
rtk git commit -m "feat: add RealityKit grip hand camera controls"
```

### Task 4: Replace the SwiftUI host and preserve fallback/accessibility

**Files:**
- Modify: `HangTen/Views/GripHandModelView.swift`
- Test: `HangTenTests/GripHandOrbitTests.swift`, `HangTenTests/GripHandCueCardTests.swift`

**Interfaces:**
- Consumes: `GripHandRealityScene` from Task 3.
- Produces: `GripHandModelView: View` hosted by `RealityView`, retaining `init(posture: GripType?, fingerConfiguration: FingerConfiguration?, side: GripCueSide, resetToken: Int = 0)` and all existing call sites. `GripHandRealityScene` accepts `init(assetResult: Result<GripHandAsset, Error> = GripHandAsset.bundled)` so failure rendering can be tested without corrupting the bundled asset.

- [ ] **Step 1: Add a failing host/update test**

Add `testRealitySceneShowsUnavailableStateForAssetFailure` using `.failure(GripHandAsset.AssetError.missingResource)`; assert `isUnavailable == true` and no hand mesh is installed. Add scene-update assertions that posture, explicit fingers, side, viewport size, and `resetToken` reach the RealityKit scene. Add a focused drag-intent test proving a vertical-first drag stays a scroll and an orbit starts from its claimed translation without applying earlier motion. Keep existing accessibility labels unchanged.

- [ ] **Step 2: Run the new host test to verify it fails**

Run `GripHandOrbitTests` and the targeted cue-card tests.
Expected: failure until the view uses the RealityKit scene and sync path.

- [ ] **Step 3: Replace `UIViewRepresentable` with `RealityView`**

Keep `GripHandModelView(posture:fingerConfiguration:side:resetToken:)` at the call sites. Create/add the RealityKit root in `RealityView` and set its active camera to `GripHandRealityScene.camera`; route drag and magnification deltas through the scene orbit API; reset gesture state when a gesture ends; update for pose/side/size/reset-token changes. Retain the non-accessible decorative model and accessible label, and overlay the existing unavailable text when asset loading fails.

- [ ] **Step 4: Run host and cue-card tests**

Run:

```bash
rtk xcodebuild test -project HangTen.xcodeproj -scheme HangTen -sdk iphonesimulator -configuration Debug -derivedDataPath .context/DerivedData -only-testing:HangTenTests/GripHandOrbitTests -only-testing:HangTenTests/GripHandCueCardTests
```

Expected: both suites pass and existing cue-card/source validation assertions remain unchanged.

- [ ] **Step 5: Commit the RealityView host**

```bash
rtk git add HangTen/Views/GripHandModelView.swift HangTenTests/GripHandOrbitTests.swift HangTenTests/GripHandCueCardTests.swift
rtk git commit -m "refactor: host grip hand in RealityView"
```

### Task 5: Remove SceneKit and verify app flows

**Files:**
- Modify: `HangTen/Views/GripHandModelView.swift`, `HangTenTests/GripHandOrbitTests.swift`
- Verify: `HangTenTests/GripHandCueCardTests.swift`, app and test targets

**Interfaces:**
- Consumes: completed RealityKit view/scene/mesh from Tasks 1–4.
- Produces: grip-hand implementation and tests with no SceneKit references.

- [ ] **Step 1: Delete SceneKit renderer code and test imports**

Remove `UIViewRepresentable`, `SCNView`, `SCNScene`, `SCNNode`, `SCNGeometry`, `SCNMaterial`, `SCNTransaction`, `SCNVector*`, the custom `GripHandSceneView`, and SceneKit-only helpers. Keep `GripHandAsset`, `GripHandPose`, `GripHandRealityMeshBuilder`, `GripHandRealitySurface`, and `GripHandRealityScene`. Keep the `.metal` file and its Xcode target registration. Remove `import SceneKit` from `GripHandOrbitTests` and assert renderer state through RealityKit entities.

- [ ] **Step 2: Search for all SceneKit dependencies**

Run: `rtk rg -n 'import SceneKit|SCN(View|Scene|Node|Geometry|Material|Transaction|Vector|Matrix|Camera|Light)' HangTen HangTenTests --glob '*.swift'`
Expected: no matches. Existing unrelated historical design documents are not code dependencies and remain unchanged.

- [ ] **Step 3: Build and run all tests**

Run:

```bash
rtk xcodebuild build -project HangTen.xcodeproj -scheme HangTen -sdk iphonesimulator -configuration Debug -derivedDataPath .context/DerivedData
rtk xcodebuild test -project HangTen.xcodeproj -scheme HangTen -sdk iphonesimulator -configuration Debug -destination 'platform=iOS Simulator,name=iPhone 17 Pro' -derivedDataPath .context/DerivedData
```

Expected: build succeeds and the full test target passes.

- [ ] **Step 4: Visually verify hand variants in the isolated iOS Simulator**

Launch `HANGTEN_REVIEW_GRIP_MODEL=1` on the workspace-owned simulator. Capture `.context` screenshots for neutral, single finger, and multi-finger variants, left and right sides; inspect posture changes, drag, pinch, viewport resize, and reset. Expected: authored silhouettes and smooth color selection match the pre-migration renderer; controls, card layout, fallback copy, and accessibility labels remain intact. Leave workspace-owned simulator state for the archive hook; do not delete shared simulators.

- [ ] **Step 5: Commit the SceneKit removal and verification-ready code**

```bash
rtk git add HangTen/Views/GripHandModelView.swift HangTenTests/GripHandOrbitTests.swift
rtk git commit -m "refactor: remove final SceneKit renderer"
```

---

## Completion Criteria

- `GripHandModelView` renders authored mesh data through RealityKit only.
- Exact finger highlight mapping and existing posture surfaces are preserved.
- Side mirroring, orthographic framing, drag orbit, pinch zoom, reset, resize, fallback, and accessibility behavior are verified.
- Existing `GripHandCueCardTests` pass unchanged.
- No SceneKit imports or symbols remain in application or test Swift sources.
