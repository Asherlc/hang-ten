# iOS Board Model Studio Appearance Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Render every board USDZ in iOS with believable form via a procedural studio IBL environment plus one neutral PBR material, without touching any committed model.

**Architecture:** Presentation-time pass only. A deterministic `StudioLightingEnvironment` builds a cached 1024x512 equirectangular UIImage with CoreGraphics; `BoardModelScene.applyStudioAppearance()` sets it as `scene.lightingEnvironment` and mutates existing geometry materials in place so highlight tint/restore keeps working. The view seam `BoardModelSCNView.display(_:)` calls it once per model identity.

**Tech Stack:** Swift, SceneKit (`SCNScene.lightingEnvironment`, `SCNMaterial.lightingModel = .physicallyBased`), UIKit (`UIGraphicsImageRenderer`), XCTest (`HangTenTests/BoardModelTests.swift`).

---

## File Structure

- Modify: `HangTen/Views/BoardModelView.swift`
  - Add `struct StudioLightingEnvironment` (cached procedural equirect image, 1024x512, scale 1, opaque). No new file on purpose: the Xcode project uses explicit `PBXFileReference` entries (no filesystem-synced groups), so a new file would require brittle `.pbxproj` surgery. The type still has a single responsibility and can be split out later.
  - Add `BoardModelScene.didApplyStudioAppearance` flag + `func applyStudioAppearance()`.
  - Edit `makeCordNode(for:)` to set `material.lightingModel = .physicallyBased` (keep dark diffuse).
  - Edit `configureCameraAndLighting(framing:)` ambient 250 -> 150.
  - Edit `BoardModelSCNView.display(_:)` to call `model.applyStudioAppearance()` after `scene = model.scene`.
- Modify: `HangTenTests/BoardModelTests.swift`
  - Add 6 tests reusing existing private helpers `modelDescriptor(nodes:minimum:maximum:)`, `display(...)`, `scene(nodes:materiallessPath:)`, `node(at:in:)`.
- No USDZ, `board.json`, descriptor, geometry, picking, or suspension changes. No new assets. No feature flag.

---

### Task 1: Isolate a clean baseline (RealityKit WIP is dirty in this worktree)

**Files:**
- Modify: none (verification only)

- [ ] **Step 1: Inspect dirty state**

```bash
git status --short
git log --oneline -3
```

Expected: `HangTen/Views/BoardModelView.swift`, `HangTen.xcodeproj/project.pbxproj`, and `docs/superpowers/specs/2026-09-25-realitykit-board-model-renderer-design.md` show as modified (uncommitted RealityKit `BoardRealityRenderer` work on branch `ios-model-rendering-options`). HEAD is `77cb2840f`.

- [ ] **Step 2: Stash the unrelated RealityKit WIP before touching studio appearance**

```bash
git stash push -m "wip-realitykit-renderer-2026-09-26" -- HangTen/Views/BoardModelView.swift HangTen.xcodeproj/project.pbxproj docs/superpowers/specs/2026-09-25-realitykit-board-model-renderer-design.md
git status --short
```

Expected: `git status --short` is clean (or shows only this plan file as untracked). If the stash fails or unrelated files remain dirty, STOP and ask the user — do not mix RealityKit renderer code with the studio-appearance change.

- [ ] **Step 3: Confirm the studio seam lines are at their committed positions**

```bash
rg -n "ambient.light\?.intensity|func display\(|func makeCordNode|private func configureCameraAndLighting" HangTen/Views/BoardModelView.swift
```

Expected: `ambient.light?.intensity = 250`, `func display(_ model: BoardModelScene)`, `private func makeCordNode(`, `private func configureCameraAndLighting(` all present. These are the four edit sites for Task 6.

---

### Task 2: Write failing tests, part A (environment + neutral materials, idempotency)

**Files:**
- Modify: `HangTenTests/BoardModelTests.swift` (append inside `final class BoardModelTests`, before the `private func modelDescriptor` helper at line ~3569)
- Test: `HangTenTests/BoardModelTests.swift`

- [ ] **Step 1: Append the two part-A tests**

```swift
func testStudioAppearanceSetsEnvironmentAndNeutralMaterials() throws {
    let descriptor = modelDescriptor(nodes: [
        .init(nodeID: "Board/Body", role: .body, contactID: nil),
        .init(nodeID: "Board/Hold/Left", role: .contact, contactID: "left"),
    ])
    let model = try XCTUnwrap(BoardModelScene(
        source: scene(nodes: ["Board/Body", "Board/Hold/Left"]),
        descriptor: descriptor,
        display: display(),
        allowedPositionIDs: ["front"]
    ))
    model.applyStudioAppearance()
    XCTAssertNotNil(model.scene.lightingEnvironment.contents)
    XCTAssertGreaterThan(model.scene.lightingEnvironment.intensity, 0)
    XCTAssertEqual(model.scene.lightingEnvironment.intensity, 1.5, accuracy: 0.001)
    let expectedDiffuse = UIColor(red: 0.82, green: 0.80, blue: 0.77, alpha: 1.0)
    for node in model.geometryNodes {
        let material = try XCTUnwrap(node.geometry?.firstMaterial)
        XCTAssertEqual(material.lightingModel, .physicallyBased)
        XCTAssertEqual(material.diffuse.contents as? UIColor, expectedDiffuse)
        XCTAssertEqual((material.roughness.contents as? NSNumber)?.doubleValue ?? -1, 0.5, accuracy: 0.001)
        XCTAssertEqual((material.metalness.contents as? NSNumber)?.doubleValue ?? -1, 0.0, accuracy: 0.001)
        XCTAssertNil(material.emission.contents)
        XCTAssertNil(material.normal.contents)
        XCTAssertNil(material.specular.contents)
    }
}

func testStudioAppearanceIsIdempotent() throws {
    let descriptor = modelDescriptor(nodes: [
        .init(nodeID: "Board/Body", role: .body, contactID: nil),
        .init(nodeID: "Board/Hold/Left", role: .contact, contactID: "left"),
    ])
    let model = try XCTUnwrap(BoardModelScene(
        source: scene(nodes: ["Board/Body", "Board/Hold/Left"]),
        descriptor: descriptor,
        display: display(),
        allowedPositionIDs: ["front"]
    ))
    model.applyStudioAppearance()
    let first = try model.geometryNodes.map { ObjectIdentifier(try XCTUnwrap($0.geometry?.firstMaterial)) }
    model.applyStudioAppearance()
    let second = try model.geometryNodes.map { ObjectIdentifier(try XCTUnwrap($0.geometry?.firstMaterial)) }
    XCTAssertEqual(first, second)
    XCTAssertEqual(model.scene.lightingEnvironment.intensity, 1.5, accuracy: 0.001)
}
```

- [ ] **Step 2: Run part A to verify it fails (no implementation yet)**

```bash
rtk xcodebuild test -project HangTen.xcodeproj -scheme HangTen -destination 'platform=iOS Simulator,name=iPhone 17 Pro,OS=latest' -derivedDataPath .context/DerivedData -only-testing:HangTenTests/BoardModelTests/testStudioAppearanceSetsEnvironmentAndNeutralMaterials -only-testing:HangTenTests/BoardModelTests/testStudioAppearanceIsIdempotent
```

Expected: FAIL with `value of type 'BoardModelScene' has no member 'applyStudioAppearance'`. This is the correct TDD red.

- [ ] **Step 3: Commit the failing tests**

```bash
git add HangTenTests/BoardModelTests.swift
git commit -m "test: add failing studio appearance tests part A"
git push
```

Expected: commit created and pushed; CI may fail (implementation missing) — that is intended at this step.

---

### Task 3: Write failing tests, part B (highlight restore, environment image, cords)

**Files:**
- Modify: `HangTenTests/BoardModelTests.swift` (same insertion point as Task 2)
- Test: `HangTenTests/BoardModelTests.swift`

- [ ] **Step 1: Append the highlight-restore test**

```swift
func testStudioHighlightRestoreReturnsNeutralMaterial() throws {
    let descriptor = modelDescriptor(nodes: [
        .init(nodeID: "Board/Body", role: .body, contactID: nil),
        .init(nodeID: "Board/Hold/Left", role: .contact, contactID: "left"),
    ])
    let model = try XCTUnwrap(BoardModelScene(
        source: scene(nodes: ["Board/Body", "Board/Hold/Left"]),
        descriptor: descriptor,
        display: display(),
        allowedPositionIDs: ["front"]
    ))
    model.applyStudioAppearance()
    let node = try XCTUnwrap(model.contactNodes["left"]?.first)
    let neutral = try XCTUnwrap(node.geometry?.firstMaterial)
    XCTAssertEqual(neutral.lightingModel, .physicallyBased)
    model.highlight(["left"], mode: .active)
    XCTAssertFalse(node.geometry?.firstMaterial === neutral)
    XCTAssertEqual(node.geometry?.firstMaterial?.diffuse.contents as? UIColor, UIColor(Color.holdActive))
    model.highlight([], mode: .active)
    XCTAssertTrue(node.geometry?.firstMaterial === neutral)
}
```

- [ ] **Step 2: Append the environment-image test**

```swift
func testStudioLightingEnvironmentImageIs1024x512AndTopLit() throws {
    let image = try XCTUnwrap(StudioLightingEnvironment.image())
    XCTAssertEqual(image.size, CGSize(width: 1024, height: 512))
    let cg = try XCTUnwrap(image.cgImage)
    XCTAssertEqual(cg.width, 1024)
    XCTAssertEqual(cg.height, 512)
    func brightness(at point: CGPoint) throws -> CGFloat {
        let provider = try XCTUnwrap(cg.dataProvider)
        let data = try XCTUnwrap(provider.data)
        let ptr = try XCTUnwrap(CFDataGetBytePtr(data))
        let bytesPerPixel = cg.bitsPerPixel / 8
        let x = min(max(Int(point.x * CGFloat(cg.width) / image.size.width), 0), cg.width - 1)
        let y = min(max(Int(point.y * CGFloat(cg.height) / image.size.height), 0), cg.height - 1)
        let offset = y * cg.bytesPerRow + x * bytesPerPixel
        let r = CGFloat(ptr[offset]) / 255.0
        let g = CGFloat(ptr[offset + 1]) / 255.0
        let b = CGFloat(ptr[offset + 2]) / 255.0
        return 0.2126 * r + 0.7152 * g + 0.0722 * b
    }
    let top = try brightness(at: CGPoint(x: 512, y: 60))
    let bottom = try brightness(at: CGPoint(x: 512, y: 450))
    XCTAssertGreaterThan(top, bottom)
}
```

- [ ] **Step 3: Append the cord-material test (paired-lead fixture copied from the existing cord test)**

```swift
func testStudioCordMaterialsArePBRAndDark() throws {
    let selectedPose = BoardModelCanonicalPose(
        rotation: [0, 0, 0, 1],
        translation: [0, 0, 0],
        camera: BoardModelCanonicalCamera(viewDirection: [0, 0, -1], fitPadding: 0.08)
    )
    let suspension = BoardModelPairedLeadCord(
        attachments: [
            BoardModelPairedLeadAttachment(id: "left", nodeID: "Lead/Left", pointInModel: [-0.6, 0.4, 0.05], provenance: "test"),
            BoardModelPairedLeadAttachment(id: "right", nodeID: "Lead/Right", pointInModel: [0.6, 0.4, -0.05], provenance: "test"),
        ],
        passages: BoardModelPassagePairs(
            left: [BoardModelPassage(id: "left-lip", nodeID: "Lead/Left", pointInModel: [-0.6, 0.4, 0.05], provenance: "test")],
            right: [BoardModelPassage(id: "right-lip", nodeID: "Lead/Right", pointInModel: [0.6, 0.4, -0.05], provenance: "test")]
        ),
        anchor: BoardModelInvisibleAnchor(offsetFromBoardBounds: [0, 0, 0], visibility: "invisible", provenance: "test", position: [0, 2, 0]),
        cord: BoardModelCord(restLength: 2, radius: 0.01, material: "test-cord", provenance: "test"),
        canonicalPoses: ["primary": selectedPose]
    )
    let descriptor = modelDescriptor(
        nodes: [
            .init(nodeID: "Body", role: .body, contactID: nil),
            .init(nodeID: "Hold", role: .contact, contactID: "hold"),
            .init(nodeID: "Lead/Left", role: .attachment, contactID: nil),
            .init(nodeID: "Lead/Right", role: .attachment, contactID: nil),
        ],
        minimum: [-1, -0.5, -0.2],
        maximum: [1, 0.5, 0.2]
    )
    let source = scene(nodes: ["Body", "Hold", "Lead/Left", "Lead/Right"])
    for path in ["Body", "Hold", "Lead/Left", "Lead/Right"] {
        node(at: path, in: source)?.simdPosition = SIMD3<Float>(10, 10, 10)
    }
    let model = try XCTUnwrap(BoardModelScene(
        source: source, descriptor: descriptor, display: display(), suspension: .pairedLeadCord(suspension)
    ))
    model.applyStudioAppearance()
    XCTAssertTrue(model.select(positionID: "primary"))
    let cord = try XCTUnwrap(model.transientCordNode)
    XCTAssertFalse(cord.childNodes.isEmpty)
    for segment in cord.childNodes {
        let material = try XCTUnwrap(segment.geometry?.firstMaterial)
        XCTAssertEqual(material.lightingModel, .physicallyBased)
        let diffuse = try XCTUnwrap(material.diffuse.contents as? UIColor)
        var white: CGFloat = -1
        var alpha: CGFloat = -1
        XCTAssertTrue(diffuse.getWhite(&white, alpha: &alpha))
        XCTAssertEqual(white, 0.08, accuracy: 0.001)
    }
}
```

- [ ] **Step 4: Run part B to verify it fails**

```bash
rtk xcodebuild test -project HangTen.xcodeproj -scheme HangTen -destination 'platform=iOS Simulator,name=iPhone 17 Pro,OS=latest' -derivedDataPath .context/DerivedData -only-testing:HangTenTests/BoardModelTests/testStudioHighlightRestoreReturnsNeutralMaterial -only-testing:HangTenTests/BoardModelTests/testStudioLightingEnvironmentImageIs1024x512AndTopLit -only-testing:HangTenTests/BoardModelTests/testStudioCordMaterialsArePBRAndDark
```

Expected: FAIL — `applyStudioAppearance` and `StudioLightingEnvironment` do not exist yet. Correct TDD red.

- [ ] **Step 5: Commit the failing tests**

```bash
git add HangTenTests/BoardModelTests.swift
git commit -m "test: add failing studio appearance tests part B"
git push
```

Expected: pushed; implementation still missing.

---

### Task 4: Implement StudioLightingEnvironment

**Files:**
- Modify: `HangTen/Views/BoardModelView.swift` (insert after the `BoardModelScene` closing brace, before `private extension SCNVector3` at line ~2563)
- Test: `HangTenTests/BoardModelTests/testStudioLightingEnvironmentImageIs1024x512AndTopLit`

- [ ] **Step 1: Add the environment type**

```swift
/// Deterministic procedural studio environment for board rendering.
///
/// Produces a cached 1024x512 equirectangular image drawn with CoreGraphics:
/// a bright-ceiling to dark-floor vertical gradient, a warm key softbox in
/// the upper third, and a faint cool fill blob. No randomness, no bundled
/// asset, no network. Returns nil only if gradient construction fails; the
/// caller then renders with the existing lights and PBR materials.
struct StudioLightingEnvironment {
    static let width: CGFloat = 1024
    static let height: CGFloat = 512
    static let intensity: CGFloat = 1.5
    private static var cached: UIImage?

    static func image() -> UIImage? {
        if let cached { return cached }
        let size = CGSize(width: width, height: height)
        let format = UIGraphicsImageRendererFormat()
        format.scale = 1
        format.opaque = true
        let renderer = UIGraphicsImageRenderer(size: size, format: format)
        var gradientFailed = false
        let rendered = renderer.image { context in
            let cg = context.cgContext
            let top = UIColor(white: 1.0, alpha: 1.0).cgColor
            let mid = UIColor(white: 0.45, alpha: 1.0).cgColor
            let bottom = UIColor(white: 0.08, alpha: 1.0).cgColor
            guard let gradient = CGGradient(
                colorsSpace: CGColorSpaceCreateDeviceRGB(),
                colors: [top, mid, bottom] as CFArray,
                locations: [0.0, 0.55, 1.0]
            ) else {
                gradientFailed = true
                return
            }
            cg.drawLinearGradient(
                gradient,
                start: CGPoint(x: 0, y: 0),
                end: CGPoint(x: 0, y: size.height),
                options: []
            )
            cg.setFillColor(UIColor(red: 1.0, green: 0.95, blue: 0.85, alpha: 0.9).cgColor)
            cg.fillEllipse(in: CGRect(
                x: size.width * 0.28, y: size.height * 0.08,
                width: size.width * 0.44, height: size.height * 0.30
            ))
            cg.setFillColor(UIColor(red: 0.6, green: 0.7, blue: 0.9, alpha: 0.35).cgColor)
            cg.fillEllipse(in: CGRect(
                x: size.width * 0.05, y: size.height * 0.45,
                width: size.width * 0.30, height: size.height * 0.30
            ))
        }
        guard !gradientFailed else { return nil }
        cached = rendered
        return rendered
    }
}
```

Notes for the implementer: `UIGraphicsImageRenderer` requires UIKit (already imported in this file). `format.scale = 1` keeps `image.size` exactly 1024x512 so the size test is deterministic. Do not add randomness.

- [ ] **Step 2: Build only (no test run yet)**

```bash
rtk xcodebuild -project HangTen.xcodeproj -scheme HangTen -sdk iphonesimulator -configuration Debug -derivedDataPath .context/DerivedData build
```

Expected: BUILD SUCCEEDED. Only `StudioLightingEnvironment` is new; nothing calls it yet.

- [ ] **Step 3: Commit**

```bash
git add HangTen/Views/BoardModelView.swift
git commit -m "feat: add procedural StudioLightingEnvironment"
git push
```

Expected: pushed.

---

### Task 5: Implement applyStudioAppearance plus seam, lighting, and cords

**Files:**
- Modify: `HangTen/Views/BoardModelView.swift` (4 edits below, all in this file)
- Test: all 5 `testStudio*` tests from Tasks 2-3

- [ ] **Step 1: Add the idempotency flag next to the highlight state (line ~600)**

Old:

```swift
    private var originalMaterials: [ObjectIdentifier: [SCNMaterial]] = [:]
```

New:

```swift
    private var originalMaterials: [ObjectIdentifier: [SCNMaterial]] = [:]
    private var didApplyStudioAppearance = false
```

- [ ] **Step 2: Add applyStudioAppearance next to highlight(_:mode:) (after line ~2293)**

```swift
    /// Applies the studio look: procedural IBL environment plus one neutral
    /// physically based material. Mutates the existing materials in place so
    /// the highlight system (which captured these same objects in
    /// `originalMaterials`) keeps working with no rebinding. Idempotent.
    func applyStudioAppearance() {
        if didApplyStudioAppearance { return }
        didApplyStudioAppearance = true
        if let environment = StudioLightingEnvironment.image() {
            scene.lightingEnvironment.contents = environment
            scene.lightingEnvironment.intensity = StudioLightingEnvironment.intensity
        }
        let neutral = UIColor(red: 0.82, green: 0.80, blue: 0.77, alpha: 1.0)
        for node in geometryNodes {
            guard let geometry = node.geometry else { continue }
            for material in geometry.materials {
                material.lightingModel = .physicallyBased
                material.diffuse.contents = neutral
                material.roughness.contents = 0.5
                material.metalness.contents = 0.0
                material.emission.contents = nil
                material.emission.intensity = 0
                material.normal.contents = nil
                material.specular.contents = nil
            }
        }
        scene.rootNode.enumerateChildNodes { node, _ in
            guard node.categoryBitMask == Self.cordCategory,
                  let geometry = node.geometry else { return }
            for material in geometry.materials {
                material.lightingModel = .physicallyBased
            }
        }
    }
```

Why in place: `prepareModel` copied materials per node and `originalMaterials` points at those same objects; replacing the array would orphan the highlight-restore table, mutating preserves it. The trailing enumeration covers cords created before this call; cords created after are covered by Step 4.

- [ ] **Step 3: Reduce ambient so the environment carries form (in configureCameraAndLighting, line ~2541)**

Old:

```swift
        ambient.light?.intensity = 250
```

New:

```swift
        ambient.light?.intensity = 150
```

Keep the directional key (850, shadow), SSAO, and `view.backgroundColor = .clear` unchanged. Only `lightingEnvironment` is set, so the SwiftUI card behind still shows.

- [ ] **Step 4: Make future cords PBR at creation (in makeCordNode, after line ~1768)**

Old:

```swift
                let material = SCNMaterial()
                material.diffuse.contents = UIColor(white: 0.08, alpha: 1)
                material.roughness.contents = 0.8
```

New:

```swift
                let material = SCNMaterial()
                material.lightingModel = .physicallyBased
                material.diffuse.contents = UIColor(white: 0.08, alpha: 1)
                material.roughness.contents = 0.8
```

Diffuse stays `0.08`; only the lighting model changes.

- [ ] **Step 5: Call the pass once per model at the view seam (in display(_:), line ~2799)**

Old:

```swift
    func display(_ model: BoardModelScene) {
        guard self.model !== model else { return }
        self.model = model
        scene = model.scene
```

New:

```swift
    func display(_ model: BoardModelScene) {
        guard self.model !== model else { return }
        self.model = model
        model.applyStudioAppearance()
        scene = model.scene
```

The `!==` guard makes this once-per-model-identity. `updateUIView`/`selectPositionIfNeeded` must NOT call it (idempotency is a backstop, not the mechanism).

- [ ] **Step 6: Run all new studio tests**

```bash
rtk xcodebuild test -project HangTen.xcodeproj -scheme HangTen -destination 'platform=iOS Simulator,name=iPhone 17 Pro,OS=latest' -derivedDataPath .context/DerivedData -only-testing:HangTenTests/BoardModelTests/testStudioAppearanceSetsEnvironmentAndNeutralMaterials -only-testing:HangTenTests/BoardModelTests/testStudioAppearanceIsIdempotent -only-testing:HangTenTests/BoardModelTests/testStudioHighlightRestoreReturnsNeutralMaterial -only-testing:HangTenTests/BoardModelTests/testStudioLightingEnvironmentImageIs1024x512AndTopLit -only-testing:HangTenTests/BoardModelTests/testStudioCordMaterialsArePBRAndDark
```

Expected: all 5 PASS (TDD green).

- [ ] **Step 7: Commit**

```bash
git add HangTen/Views/BoardModelView.swift
git commit -m "feat: apply studio IBL plus neutral PBR materials at display seam"
git push
```

Expected: pushed.

---

### Task 6: Regression sweep and visual verification

**Files:**
- Modify: none (verification only)

- [ ] **Step 1: Run the full BoardModelTests suite — existing decode/material-preservation tests must pass unchanged**

```bash
rtk xcodebuild test -project HangTen.xcodeproj -scheme HangTen -destination 'platform=iOS Simulator,name=iPhone 17 Pro,OS=latest' -derivedDataPath .context/DerivedData -only-testing:HangTenTests/BoardModelTests
```

Expected: all tests PASS, including the `.brown` material-preservation assertions (decode contract untouched — appearance runs at the view seam, outside `BoardModelScene.init`/`prepareModel`).

- [ ] **Step 2: Re-render the SceneKit before/after harness**

```bash
swiftc -O -o .context/married-crocodile/render-options/render .context/married-crocodile/render-options/RenderOptions.swift && .context/married-crocodile/render-options/render trango-rock-prodigy-pivot
```

Expected: `out/1-baseline.png` (flat) vs the studio variant showing soft form shading on the same USDZ. If the harness sources were cleaned up, re-derive the comparison from `BoardModelView.swift:configureCameraAndLighting` values instead of inventing a new renderer.

- [ ] **Step 3: Capture real iOS-simulator before/after on an isolated simulator**

Use the `validate-hang-ten-ios` skill on at least one model-media board. Simulators must be isolated per that skill (never the user's booted device).

Expected: side-by-side screenshots showing the board with believable shading and the SwiftUI card background still visible through the clear view.

- [ ] **Step 4: Restore or rebase the stashed RealityKit WIP (do not drop it silently)**

```bash
git stash list
```

Expected: `wip-realitykit-renderer-2026-09-26` still present. Either `git stash pop` onto a separate branch for the RealityKit track, or leave stashed and tell the user. Never `git stash drop` without the user confirming the RealityKit diff is expendable.

---

## Self-Review (run by the plan author, not a subagent)

1. **Spec coverage:** environment image (Task 4, test 6) ✓; env contents + intensity (Task 5, test 1) ✓; neutral PBR diffuse/roughness/metalness + cleared maps (Task 5, test 1) ✓; idempotency (test 2) ✓; highlight tint→clear identity (test 3) ✓; cord PBR dark (test 5) ✓; ambient 150 + intensity 1.5 + shadow/SSAO/clear-bg preserved (Task 5 Steps 3-5) ✓; error path (nil env → materials only, Task 5 Step 2) ✓; visual harness + simulator (Task 6) ✓. Non-goals honored: no USDZ edits, no role colors/shaders/RealityKit, no geometry/picking/suspension changes, no flag.
2. **Placeholder scan:** no TBD/TODO/later/appropriate/edge-case language; every code step shows complete compilable Swift; every run step shows the exact `rtk xcodebuild` invocation and expected PASS/FAIL text.
3. **Type consistency:** `StudioLightingEnvironment.image() -> UIImage?`, `.intensity: CGFloat = 1.5` used as `scene.lightingEnvironment.intensity`; `applyStudioAppearance()` takes no args, returns Void; test helper names (`modelDescriptor`, `display`, `scene`, `node(at:in:)`) match `BoardModelTests.swift:3569-3639`; `UIColor(Color.holdActive)` matches the existing highlight test at line ~569; cord `getWhite` matches the `UIColor(white: 0.08)` creation.
