# Package-Driven 3D Runtime and Tools Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace Compact II’s board-specific display bridge with a generic package-driven model renderer, typed synchronization, and explicit read-only model handling in both editors.

**Architecture:** This plan consumes schema-v2 typed media and descriptor-v1 from the schema/compiler plan. `TrainingBoard` resolves logical workout frames from selected media while SceneKit uses the same descriptor-bound USD nodes for render, highlight, and nearest-hit picking. Packages, rather than a Swift registry or separate app resource, own model bytes.

**Tech Stack:** SwiftUI, SceneKit, Foundation/CryptoKit, XCTest, Python Workbench backend, TypeScript/React Workbench, GitHub REST client.

**Spec:** `docs/superpowers/specs/2026-09-08-beastmaker-1000-3d-design.md`

## Global Constraints

- Execute every task through a fresh implementation subagent and fresh review subagent. Luna owns bounded mechanics; Sol or Terra own involved non-geometry work; Astra is not used.
- Depend on completed `2026-09-08-model-first-package-schema-and-compiler.md`; do not create a parallel descriptor or a board ID registry.
- Models are sourced only from `BoardPresentationMedia.model`; model cache key is `(boardID, presentationID, modelSHA256)`. No raster fallback, derived/inverted model media, partial interaction, automatic axis guessing, or node-name normalisation is permitted.
- Node matching is exact `descriptor.nodes[].nodeID`; body nodes remain nonselectable. The same hold nodes implement normal render, highlighting, and nearest-hit selection.
- Runtime missing/invalid media presents a generic unavailable state and never attempts a PNG. Workbench raster editing remains unchanged; model geometry is visibly read-only.
- Tests/builds use `.context/DerivedData`; the owner deletes only ephemeral runtime resources and preserves durable `.context/shaky-rat-*` evidence artifacts.

## Dependency Order

`Task 1 -> Task 2 -> Task 3 -> Task 4 -> Task 5`; Task 6 consumes Task 1 and Task 5; Task 7 consumes Tasks 2–6. Target migrations are deliberately deferred to the third plan.

## Isolated XCTest Device Lifecycle

Before the first XCTest command, create one simulator named `Hang Ten Paseo shaky-rat Review`, verify its exact returned UUID and name, record it immediately in `.context/paseo-pending-simulators` then `.context/paseo-owned-simulators`, and export `HANG_TEN_TEST_DEVICE_UDID` to that UUID. Install EXIT/INT/TERM cleanup before creation; it invokes `PASEO_WORKTREE_PATH="$PWD" scripts/paseo-resource-cleanup.sh archive`, deletes only this verified workspace-named simulator and `.context/DerivedData`, and preserves durable `.context/shaky-rat-*` evidence artifacts. Every XCTest command below uses this exported UUID; never use a named/shared or `booted` destination.

## File Map

| File | Change | Responsibility |
| --- | --- | --- |
| `HangTen/Models/TrainingModels.swift` | Modify | `BoardPresentationMedia`, `BoardHold.resolvedFrame(in:)`, media-aware content selection. |
| `HangTen/Models/BoardPackageStore.swift` | Modify | Typed package media URLs/descriptor APIs from plan one. |
| `HangTen/Views/BoardModelView.swift` | Replace board registry | Generic scene source/cache/binding/renderer/unavailable view. |
| `HangTen/Views/BoardMapView.swift` | Modify | Route raster and model media explicitly. |
| `HangTen/Models/WorkoutActivityRecording.swift` | Modify | Use resolved frame instead of stored raster-path frame. |
| `HangTen/Models/GitHubBoardSyncService.swift` | Modify | Pull every declared typed asset, not default PNG only. |
| `HangTen/Models/BoardEditorStore.swift` | Modify | Preserve arbitrary typed assets and return editable/read-only package state. |
| `HangTen/Models/BoardPackageWriter.swift` | Modify | Encode schema-v2 editable raster documents, reject editing model geometry. |
| `HangTen/Views/BoardEditor/*.swift` | Modify | Show model read-only state; suppress path canvas/save geometry controls. |
| `Tools/HangboardWorkbench/board_package.py`, `server.py` | Modify | Load typed media and serve explicit read-only presentation metadata. |
| `Tools/HangboardWorkbench/src/types.ts`, `workbench-client.ts`, `useWorkbench.ts`, `components/HoldCanvas.tsx`, `components/ValidationPanel.tsx` | Modify | Model read-only UI and no image/path reconstruction. |
| `HangTenTests/BoardModelTests.swift`, `HangTenTests/BoardPackageStoreTests.swift`, `HangTenTests/GitHubBoardSyncServiceTests.swift`, `HangTenTests/BoardEditorStoreTests.swift`, `HangTenTests/BoardPackageWriterTests.swift` | Modify | Native semantic and typed storage/sync regressions. |
| `HangTenTests/BoardTargetSubstitutionTests.swift` | Test unchanged | Preserve the existing Compact II round-sloper target result through the media-frame change. |
| `Tools/HangboardWorkbench/tests/test_board_package.py`, `test_server.py`, `react-app.test.tsx` | Modify | Model read-only backend and UI regressions. |

### Task 1: Sol — make logical matching media-aware

**Files:**
- Modify: `HangTen/Models/TrainingModels.swift`, `HangTen/Views/BoardMapView.swift`, `HangTen/Models/WorkoutActivityRecording.swift`
- Test: `HangTenTests/BoardPackageStoreTests.swift`, `HangTenTests/WorkoutActivityRecordingTests.swift`

**Interfaces:**
- Consumes `BoardPresentation.media` and descriptor `holds[holdID].facePlaneAABB` from plan one.
- Produces `BoardHold.resolvedFrame(in presentation: BoardPresentation) -> HoldFrame?` and `TrainingBoard.holds(in presentation: BoardPresentation) -> [BoardHold]`.

- [ ] **Step 1: Write frame-resolution failures**

```swift
func testModelHoldUsesDescriptorBoundsForWorkoutMatching() {
    let model = modelPresentation(bounds: ["left": .init(x: 0.10, y: 0.20, width: 0.30, height: 0.40)])
    let hold = logicalHold(id: "left")
    XCTAssertEqual(hold.resolvedFrame(in: model), HoldFrame(x: 0.10, y: 0.20, width: 0.30, height: 0.40))
    XCTAssertNil(hold.resolvedFrame(in: rasterPresentationMissing("left")))
}
```

- [ ] **Step 2: Run focused tests**

Run: `rtk xcodebuild test -project HangTen.xcodeproj -scheme HangTen -destination "platform=iOS Simulator,id=$HANG_TEN_TEST_DEVICE_UDID" -derivedDataPath .context/DerivedData -only-testing:HangTenTests/WorkoutActivityRecordingTests -only-testing:HangTenTests/BoardTargetSubstitutionTests`

Expected: FAIL because model descriptor bounds are not used.

- [ ] **Step 3: Implement media-only frame resolution**

Remove `BoardHold.presentationID` and stored path-derived `frame` as authoritative data. For raster selected content, resolve the union of `BoardRasterMedia.holdGeometry[hold.id]`; for model resolve `BoardModelMedia.descriptor.holds[hold.id].facePlaneAABB`; map both to the existing `HoldFrame`. Update `BoardMapPresentationContent` and every `WorkoutActivityRecording` `hold.frame` use to require `resolvedFrame(in:)`, treating an unavailable mapping as unavailable rather than a guessed placement.

- [ ] **Step 4: Run matching and package tests**

Run: `rtk xcodebuild test -project HangTen.xcodeproj -scheme HangTen -destination "platform=iOS Simulator,id=$HANG_TEN_TEST_DEVICE_UDID" -derivedDataPath .context/DerivedData -only-testing:HangTenTests/WorkoutActivityRecordingTests -only-testing:HangTenTests/BoardTargetSubstitutionTests -only-testing:HangTenTests/BoardPackageStoreTests`

Expected: PASS; existing raster matching remains identical, synthetic model bounds drive same-row/side logic, and the unchanged `BoardTargetSubstitutionTests.testSloperFeatureTargetsOnCompactIIUseMatchingHoldIDs` still returns `["sloper-round-center"]` for `.feature(.roundSloper)`.

- [ ] **Step 5: Commit and review**

Run: `git add HangTen/Models/TrainingModels.swift HangTen/Views/BoardMapView.swift HangTen/Models/WorkoutActivityRecording.swift HangTenTests/BoardPackageStoreTests.swift HangTenTests/WorkoutActivityRecordingTests.swift && git commit -m "feat: resolve board matching geometry from media"`

Review gate: fresh Terra reviewer confirms no descriptor value is copied into logical hold JSON.

### Task 2: Sol — generic SceneKit model asset and cache

**Files:**
- Modify: `HangTen/Views/BoardModelView.swift`
- Test: `HangTenTests/BoardModelTests.swift`

**Interfaces:**
- Produces `BoardModelKey(boardID: String, presentationID: String, modelSHA256: String)`, `BoardModelAsset.load(media: BoardModelMedia, packageURL: URL) -> SCNScene?`, `BoardModelScene.init?(source:descriptor:)`, `BoardModelScene.geometryNodes: [SCNNode]`, `BoardModelLoader.load(board:presentation:store:) -> BoardModelScene?`, and `BoardModelSurface` result states `.loading`, `.ready`, `.unavailable`.

- [ ] **Step 1: Replace registry assumptions with failing generic tests**

```swift
func testGenericModelBindingUsesExactDescriptorNodeIDs() throws {
    let scene = scene(nodes: ["Board/Body", "Board/Hold/Left"])
    let descriptor = descriptor(nodes: [.body("Board/Body"), .hold("Board/Hold/Left", "left")])
    let model = try XCTUnwrap(BoardModelScene(source: scene, descriptor: descriptor))
    XCTAssertEqual(model.holdNodes.keys, ["left"])
    XCTAssertNil(BoardModelScene(source: scene, descriptor: descriptorReplacing("Board/Hold/Left", with: "left")))
}
```

- [ ] **Step 2: Run native model test target**

Run: `rtk xcodebuild test -project HangTen.xcodeproj -scheme HangTen -destination "platform=iOS Simulator,id=$HANG_TEN_TEST_DEVICE_UDID" -derivedDataPath .context/DerivedData -only-testing:HangTenTests/BoardModelTests`

Expected: FAIL because `BoardModelKey` and descriptor binding do not exist.

- [ ] **Step 3: Implement generic decode/cache/binding**

Delete `BoardModelIdentity`, `BoardModelAsset.boardID`, `holdIDs`, underscore-to-hyphen lookup, `url(in:)`, and fallback closure. Obtain the package model URL/descriptor through `BoardPackageStore`; cache detached decode tasks by `BoardModelKey`; clone every scene and material per view. Traverse geometry nodes, compute canonical importer-visible paths using exact ancestor names separated by `/`, require set equality with descriptor node IDs, and bind only descriptor `role == hold`. Reject absent materials, wrong node inventory, duplicate paths, missing vertex sources, or body selection. Preserve `SCNTransaction.flush()` native picking precondition, same material restoration behavior, scene/camera rebinding, stable accessibility, on-demand rendering, and the current `.allowsHitTesting(onHoldTap != nil)` behavior.

- [ ] **Step 4: Run native semantic tests**

Run: `rtk xcodebuild test -project HangTen.xcodeproj -scheme HangTen -destination "platform=iOS Simulator,id=$HANG_TEN_TEST_DEVICE_UDID" -derivedDataPath .context/DerivedData -only-testing:HangTenTests/BoardModelTests`

Expected: PASS, including exact node identity, all logical contacts, body rejection, material cloning, highlight restore, camera rebind, unavailable state, and current pocket nearest-hit regression.

- [ ] **Step 5: Commit and review**

Run: `git add HangTen/Views/BoardModelView.swift HangTenTests/BoardModelTests.swift && git commit -m "feat: render package-owned board models"`

Review gate: fresh Sol reviewer confirms no `if boardID`, static asset path, or name normalisation survives.

### Task 3: Terra — media-aware board map and unavailable UI

**Files:**
- Modify: `HangTen/Views/BoardMapView.swift`, `HangTen/Views/BoardModelView.swift`
- Test: `HangTenTests/BoardModelTests.swift`, `HangTenUITests/OwlClimbPokerBoardMapInteractionUITests.swift`

**Interfaces:**
- Consumes `BoardPresentationMedia` and `BoardModelSurface` state.
- Produces `BoardModelUnavailableView` with accessibility identifier `boardModel.unavailable` and no selectable elements.

- [ ] **Step 1: Add presentation-state assertions**

```swift
func testInvalidModelUsesUnavailableViewAndNeverRasterFallback() {
    XCTAssertEqual(BoardModelSurface.displayState(media: invalidModelMedia), .unavailable)
    XCTAssertFalse(BoardModelSurface.displayState(media: invalidModelMedia).permitsHoldSelection)
}
```

- [ ] **Step 2: Run focused tests**

Run: `rtk xcodebuild test -project HangTen.xcodeproj -scheme HangTen -destination "platform=iOS Simulator,id=$HANG_TEN_TEST_DEVICE_UDID" -derivedDataPath .context/DerivedData -only-testing:HangTenTests/BoardModelTests`

Expected: FAIL because unavailable display state is absent.

- [ ] **Step 3: Implement exhaustive media switch**

Render `BoardRasterMedia` through the existing path/image surface. Render valid `BoardModelMedia` through generic SceneKit. Show a generic textual unavailable model view when decode/semantic validation fails; do not pass a raster closure or image URL into that branch. Keep ordinary raster cards/taps identical, and make model accessibility enumerate only descriptor-bound holds.

- [ ] **Step 4: Run UI and native tests**

Run: `rtk xcodebuild test -project HangTen.xcodeproj -scheme HangTen -destination "platform=iOS Simulator,id=$HANG_TEN_TEST_DEVICE_UDID" -derivedDataPath .context/DerivedData -only-testing:HangTenTests/BoardModelTests -only-testing:HangTenUITests/OwlClimbPokerBoardMapInteractionUITests`

Expected: PASS.

- [ ] **Step 5: Commit and review**

Run: `git add HangTen/Views/BoardMapView.swift HangTen/Views/BoardModelView.swift HangTenTests/BoardModelTests.swift HangTenUITests/OwlClimbPokerBoardMapInteractionUITests.swift && git commit -m "feat: surface unavailable package models"`

Review gate: fresh Luna reviewer verifies model failure cannot reach a PNG or a partially interactive scene.

### Task 4: Terra — typed GitHub package synchronization

**Files:**
- Modify: `HangTen/Models/GitHubBoardSyncService.swift`, `HangTen/Models/BoardEditorStore.swift`, `HangTenTests/GitHubBoardSyncServiceTests.swift`, `HangTenTests/BoardEditorStoreTests.swift`

**Interfaces:**
- Replaces `GitHubBoardPackagePayload(boardJSON, primaryPNG, assetPath)` with `GitHubBoardPackagePayload(boardJSON: Data, assets: [String: Data])`.
- Replaces `persistPulledImage` with `persistPulledAsset(slug:assetPath:data:)`.

- [ ] **Step 1: Add multi-asset pull test**

```swift
func testFetchBoardPackageDownloadsExactDeclaredModelAndDescriptor() async throws {
    let payload = try await service.fetchBoardPackage(token: "token", branch: "main", slug: "fixture-model")
    XCTAssertEqual(Set(payload.assets.keys), ["assets/primary.usdz", "assets/primary.model.json"])
    XCTAssertEqual(payload.assets["assets/primary.usdz"], Data("USDZ".utf8))
}
```

- [ ] **Step 2: Run focused sync tests**

Run: `rtk xcodebuild test -project HangTen.xcodeproj -scheme HangTen -destination "platform=iOS Simulator,id=$HANG_TEN_TEST_DEVICE_UDID" -derivedDataPath .context/DerivedData -only-testing:HangTenTests/GitHubBoardSyncServiceTests -only-testing:HangTenTests/BoardEditorStoreTests`

Expected: FAIL because the payload is PNG-only.

- [ ] **Step 3: Fetch and persist declared typed assets**

Decode `board.json` with the same typed asset path extractor as the package loader; find every exact `Hangboards/<slug>/<path>` blob; reject omissions, duplicate paths, paths outside `assets/`, or unlisted tree files. Store all assets atomically using `persistPulledAsset`; keep a typed media model intact rather than pretending an USDZ has pixels. Retain existing branch/auth/error semantics.

- [ ] **Step 4: Run typed sync/storage regressions**

Run: `rtk xcodebuild test -project HangTen.xcodeproj -scheme HangTen -destination "platform=iOS Simulator,id=$HANG_TEN_TEST_DEVICE_UDID" -derivedDataPath .context/DerivedData -only-testing:HangTenTests/GitHubBoardSyncServiceTests -only-testing:HangTenTests/BoardEditorStoreTests`

Expected: PASS, including v2 raster PNG, model USDZ+descriptor, absent descriptor, and rejected traversal asset path.

- [ ] **Step 5: Commit and review**

Run: `git add HangTen/Models/GitHubBoardSyncService.swift HangTen/Models/BoardEditorStore.swift HangTenTests/GitHubBoardSyncServiceTests.swift HangTenTests/BoardEditorStoreTests.swift && git commit -m "feat: sync typed board package assets"`

Review gate: fresh Terra reviewer verifies sync does not choose a default image or recreate a model fallback.

### Task 5: Luna — iOS editor model read-only storage and screens

**Files:**
- Modify: `HangTen/Models/BoardEditorStore.swift`, `HangTen/Models/BoardPackageWriter.swift`, `HangTen/Views/BoardEditor/BoardEditorScreen.swift`, `HangTen/Views/BoardEditor/HoldEditorCanvasView.swift`, `HangTen/Views/BoardEditor/HoldInspectorView.swift`
- Test: `HangTenTests/BoardEditorStoreTests.swift`, `HangTenTests/BoardPackageWriterTests.swift`, `HangTenTests/BoardEditorSessionTests.swift`

**Interfaces:**
- `BoardEditedPackage.editingCapability` is `.rasterGeometry` or `.modelReadOnly(reason: String)`.
- `BoardPackageWriter.data(for:)` accepts `BoardEditableDocument` containing raster media only and rejects model geometry edits.

- [ ] **Step 1: Write model editor failure test**

```swift
func testModelPackageLoadsReadOnlyWithoutSynthesizingImageOrPaths() throws {
    let package = try store.loadDocument(slug: "fixture-model")
    XCTAssertEqual(package.editingCapability, .modelReadOnly(reason: "3D model geometry editing is unavailable."))
    XCTAssertNil(package.imageURL)
    XCTAssertTrue(package.document.holds.allSatisfy { $0.geometry.isEmpty })
}
```

- [ ] **Step 2: Run editor focused tests**

Run: `rtk xcodebuild test -project HangTen.xcodeproj -scheme HangTen -destination "platform=iOS Simulator,id=$HANG_TEN_TEST_DEVICE_UDID" -derivedDataPath .context/DerivedData -only-testing:HangTenTests/BoardEditorStoreTests -only-testing:HangTenTests/BoardPackageWriterTests -only-testing:HangTenTests/BoardEditorSessionTests`

Expected: FAIL because editor always requires a PNG and geometry.

- [ ] **Step 3: Implement explicit read-only branch**

Make `imageURL`, `pixelWidth`, and `pixelHeight` optional in `BoardEditedPackage`. Raster retains current writable dimensions/canvas. Model validates/stores all exact assets, returns `.modelReadOnly`, shows the named read-only explanation in `BoardEditorScreen`, and hides hold path creation, dragging, inspector geometry controls, and save mutations. The writer preserves v2 raster fields and returns its existing invalid-document error if given model media; it never serializes descriptor AABBs as editor paths.

- [ ] **Step 4: Run editor suite**

Run: `rtk xcodebuild test -project HangTen.xcodeproj -scheme HangTen -destination "platform=iOS Simulator,id=$HANG_TEN_TEST_DEVICE_UDID" -derivedDataPath .context/DerivedData -only-testing:HangTenTests/BoardEditorStoreTests -only-testing:HangTenTests/BoardPackageWriterTests -only-testing:HangTenTests/BoardEditorSessionTests`

Expected: PASS.

- [ ] **Step 5: Commit and review**

Run: `git add HangTen/Models/BoardEditorStore.swift HangTen/Models/BoardPackageWriter.swift HangTen/Views/BoardEditor HangTenTests/BoardEditorStoreTests.swift HangTenTests/BoardPackageWriterTests.swift HangTenTests/BoardEditorSessionTests.swift && git commit -m "feat: make model packages editor read-only"`

Review gate: fresh Luna reviewer confirms a model cannot acquire reconstructed raster geometry.

### Task 6: Terra — Workbench typed-media read-only mode

**Files:**
- Modify: `Tools/HangboardWorkbench/board_package.py`, `Tools/HangboardWorkbench/server.py`, `Tools/HangboardWorkbench/src/types.ts`, `Tools/HangboardWorkbench/src/workbench-client.ts`, `Tools/HangboardWorkbench/src/useWorkbench.ts`, `Tools/HangboardWorkbench/src/components/HoldCanvas.tsx`, `Tools/HangboardWorkbench/src/components/ValidationPanel.tsx`
- Test: `Tools/HangboardWorkbench/tests/test_board_package.py`, `Tools/HangboardWorkbench/tests/test_server.py`, `Tools/HangboardWorkbench/tests/react-app.test.tsx`

**Interfaces:**
- API board response has `mediaType: "raster" | "model"`, `readOnlyReason: string | null`, and `imageUrl` only for raster.

- [ ] **Step 1: Add backend/UI failure tests**

```python
def test_model_package_is_listed_read_only_without_png_endpoint(client):
    response = client.get("/api/boards/fixture.model")
    assert response.json["mediaType"] == "model"
    assert response.json["readOnlyReason"] == "3D model geometry editing is unavailable."
    assert "imageUrl" not in response.json
```

```tsx
it("renders model read-only message instead of canvas", async () => {
  render(<WorkbenchApp client={modelClient} />);
  expect(await screen.findByText("3D model geometry editing is unavailable.")).toBeVisible();
  expect(screen.queryByTestId("hold-canvas")).toBeNull();
});
```

- [ ] **Step 2: Run focused Workbench tests**

Run: `rtk proxy python3 -B -m pytest Tools/HangboardWorkbench/tests/test_board_package.py Tools/HangboardWorkbench/tests/test_server.py -q && rtk npm --prefix Tools/HangboardWorkbench run test:react`

Expected: FAIL because model media is treated as image data.

- [ ] **Step 3: Implement typed read-only API/UI**

Port strict v2 media parsing (without USDZ decoding) into Workbench package loading; serve only raster image endpoints. Model responses carry logical hold metadata and read-only state, never a PNG proxy or derived SVG. Disable client mutations that alter paths/presentations for a model; keep all existing raster editor flows unchanged.

- [ ] **Step 4: Run Workbench regression group**

Run: `rtk proxy python3 -B -m pytest Tools/HangboardWorkbench/tests/test_board_package.py Tools/HangboardWorkbench/tests/test_server.py -q && rtk npm --prefix Tools/HangboardWorkbench run test:react`

Expected: PASS.

- [ ] **Step 5: Commit and review**

Run: `git add Tools/HangboardWorkbench/board_package.py Tools/HangboardWorkbench/server.py Tools/HangboardWorkbench/src Tools/HangboardWorkbench/tests && git commit -m "feat: expose model packages read-only in workbench"`

Review gate: fresh Terra reviewer verifies browser responses never contain automatic geometry or a raster substitute for model media.

### Task 7: Sol — runtime integration and native contract verification

**Files:**
- Modify: `HangTenTests/BoardModelTests.swift`, `HangTenTests/BoardPackageStoreTests.swift`, `HangTenTests/BoardSourceBoundaryTrackedPaths.txt`

- [ ] **Step 1: Add semantic fixture suite**

Add a package-local test USDZ and descriptor fixture through `makeFixtureBundle`, asserting: exact asset/descriptor hash; every descriptor hold can be nearest-hit; body hit produces nil; each mesh has material; cache separation for same board/different SHA; rebind replaces both scene/camera; model absent produces `boardModel.unavailable`; and a model does not report an image URL.

- [ ] **Step 2: Run native and source-boundary checks**

Run: `rtk xcodebuild test -project HangTen.xcodeproj -scheme HangTen -destination "platform=iOS Simulator,id=$HANG_TEN_TEST_DEVICE_UDID" -derivedDataPath .context/DerivedData -only-testing:HangTenTests/BoardModelTests -only-testing:HangTenTests/BoardPackageStoreTests`

Expected: PASS.

Run: `rtk scripts/verify-board-source-boundary-manifest.sh`

Expected: PASS after regenerating `HangTenTests/BoardSourceBoundaryTrackedPaths.txt` with the tracked source list when files changed.

- [ ] **Step 3: Commit and review**

Run: `git add HangTenTests/BoardModelTests.swift HangTenTests/BoardPackageStoreTests.swift HangTenTests/BoardSourceBoundaryTrackedPaths.txt && git commit -m "test: verify package-driven model runtime"`

Review gate: fresh Sol reviewer rejects any board-specific conditional or separate `HangTen/Resources/BoardModels` dependency.

## Final Verification

- [ ] `rtk scripts/hangboard-packages.sh validate --root Hangboards --final-inventory` exits 0.
- [ ] Focused XCTest suites from Tasks 1–5 and 7 exit 0 with `.context/DerivedData`.
- [ ] Workbench Python and React focused suites from Task 6 exit 0.
- [ ] `rtk scripts/verify-board-source-boundary-manifest.sh` and `rtk git diff --check` exit 0.
- [ ] The exact owned simulator and `.context/DerivedData` are deleted and absence verified; durable `.context/shaky-rat-*` evidence artifacts remain for audit.
