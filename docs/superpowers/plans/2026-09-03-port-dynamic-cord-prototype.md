# Port-A-Board Dynamic Cord Prototype Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace the Frictitious Port-A-Board's baked-in cord pixels with one generic, deterministic, decorative two-anchor cord renderer while preserving exact cord-free face bytes, canonical hold geometry, alias projection, and every non-opted-in board's existing behavior.

**Architecture:** Canonical presentations optionally own a closed `directTwoAnchor` rig; aliases resolve that rig and share the canonical asset, while one `BoardPresentationGeometryProjection` rotates the opted-in face, holds, markers, hit shapes, accessibility shapes, and attachments. Swift, the package validator, and Workbench independently implement one frozen loop/knot/strand fixture contract, with strict relationship, bounds, and rig-only RGBA/alpha validation. A shared SwiftUI artwork layer and the Workbench SVG preview place the projected image below a world-up decorative cord and retain the legacy image branch byte-for-byte when no rig is resolved.

**Tech Stack:** Swift 5, SwiftUI/UIKit/ImageIO on iOS 17+, XCTest/XCUITest, Python 3.11+ standard-library PNG decoding with pytest, React 19/TypeScript 7/SVG with Node 22 tests, canonical JSON board packages.

**Spec:** `docs/superpowers/specs/2026-09-03-port-dynamic-cord-prototype-design.md`

## Global Constraints

- Phase one opts in only `frictitious.port-a-board`; do not change any other package merely because the generic renderer exists.
- Do not change any Port hold record, saved hold path, constraint, hold metadata, training content, or presentation name. The canonical JSON SHA-256 of the current Port `holds` value is `c9ed1d63504559f02e33a17527ee028ac077767d57b9c44e2293e78bd515bb68` when encoded with Python `json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)`.
- Runtime and tool logic must not branch on the Port board ID, manufacturer, presentation ID/name, or asset filename. Package data is the only opt-in.
- `assetPath` remains required. Rigged aliases must use the exact canonical path and aspect ratio; actual package assets must equal the unique set of declared paths.
- `cordRig` is a closed tagged object with exactly `type`, `attachmentPoints`, `supportPoint`, `cordColor`, `cordWidth`, and `loopRadius`; `type` is exactly `directTwoAnchor` and phase one accepts no other topology.
- A rig has exactly two distinct finite normalized attachment points, one finite normalized support point, opaque six-digit sRGB `#RRGGBB`, and finite positive width/radius. Freeze the standard minimum as `loopRadius >= 2 * cordWidth` in all three implementations.
- Define meaningful transparency identically in all validators as both at least one `alpha == 0` pixel and at least one `alpha > 0` pixel; separately require all four corner pixels to have `alpha == 0`. Require PNG IHDR color type `6` (RGBA), nonempty visible alpha bounds, and full decoding. These gates apply only to canonical assets that own rigs.
- Rig stroke-expanded geometry must remain inside the selected canvas. The support assembly's stroke-expanded maximum Y must be strictly above both projected attachments. Recheck both conditions for every alias of the canonical source.
- A rig may be declared only by a canonical, non-inverted presentation. An alias inherits but cannot declare/override a rig. Every inverted alias of a rigged source must declare an explicit finite normalized `geometryRotationAnchor`, including center `{ "x": 0.5, "y": 0.5 }`.
- A rigged asset's transformed nonzero-alpha bounds must remain inside each alias canvas. The final assertion that the restored raster contains no cord is manual visual review; do not add cord recognition, segmentation, masks, contours, registration, vectorization, automatic cropping, or any pixel-derived geometry.
- Restore `assets/primary.png`, `assets/back.png`, and `assets/side.png` byte-for-byte from commit `e12e7f66`, requiring 1400 × 1400 RGBA and SHA-256 values `6d345c8dd4bb9970b9b58a0800bbf340119cc74cc11028c9867551cc9a6a5cd0`, `39223f41fd3a0c77bea2c7d04e3567475e6b418eab52a25f519fa627107c258e`, and `cf1fe06bef3c374fd980d1168cf0279e885bc260401df914579c025e1e55e7ad`. Stop for user review if any gate fails; never repair or regenerate them.
- Project only the shared face, holds, markers, hit/accessibility shapes, and canonical attachment points by the projection's one affine transform. Keep the support point, loop, and knot in canvas/world coordinates.
- Freeze `directTwoAnchor` path topology, control coefficients, line cap/join, and declared attachment ordering through `HangTenTests/Fixtures/BoardPackageValidationFixtures.json`. A future topology change requires a new `type`.
- The cord is stateless, has no implicit animation or gesture, uses `.allowsHitTesting(false)` and `.accessibilityHidden(true)`, and sits below hold highlights/targets and detail markers.
- If the resolved canonical presentation has no rig, call the existing `BoardPresentationImage` path with the selected presentation ID, do not remap or transform the image, and add no cord view. Preserve identical image bytes, layer output, taps, and accessibility.
- If an opted-in image cannot load, suppress image and cord together and issue a debug assertion; never show a floating cord or fall back to a baked alias image.
- Do not add rope physics, sag, slack, collisions, animation, dragging, interactive rotation, springs, speculative enum cases, or a catalog-wide migration.
- Use a fresh implementation subagent for every task and a separate task reviewer after every task, following `superpowers:subagent-driven-development`; controller sessions do not edit implementation/configuration files.
- Put generated review/capture output under a workspace-owned path such as `.context/joyful-donkey-port-dynamic-cord/`. Name any external resource with owner `joyful-donkey`, record it immediately, install exact cleanup traps, and verify deletion before completion.
- For every Workbench HTTP server started on port `4173`, also start `/Users/asherlc/bin/paseo-quick-tunnel 4173`, keep it alive for the server lifetime, and report only its emitted `https://…trycloudflare.com` URL.
- Phase one is not complete until all automated gates pass and the user approves the six-presentation gallery; that approval does not authorize phase two.

---

## File Map

### Shared fixtures and Swift runtime

- Modify `HangTenTests/Fixtures/BoardPackageValidationFixtures.json`: add the one cross-language `directTwoAnchor` topology/geometry contract.
- Modify `HangTen/Models/TrainingModels.swift`: add normalized point/color and cord-rig runtime types, canonical rig ownership/resolution, and the reusable affine projection accessor.
- Create `HangTen/Models/BoardCordRigGeometry.swift`: pure path-element model, exact cubic bounds, fixed direct-two-anchor template, validation helpers, and SwiftUI `Path` conversion.
- Modify `HangTen/Models/BoardPackageStore.swift`: strict decoding, semantic/relationship checks, rig-only RGBA/alpha inspection, content projection, and runtime adaptation.
- Modify `HangTen/Models/BoardPackageWriter.swift`: editable rig decode, matching semantic validation, and canonical schema serialization.
- Create `HangTen/Views/BoardPresentationArtwork.swift`: shared image-plus-cord artwork, conditional legacy branch, projected opted-in image, and decorative cord view.
- Modify `HangTen/Views/BoardMapView.swift`: use one projection and the shared artwork from both map sites without changing hold/marker construction.
- Modify `HangTen.xcodeproj/project.pbxproj`: add new Swift production, unit-test, and UI-test files to the correct groups/targets.
- Modify `HangTenTests/BoardSourceBoundaryTrackedPaths.txt`: track the two new handwritten app files.
- Create `HangTenTests/BoardCordRigGeometryTests.swift`: model, affine projection, fixed geometry, and bounds tests.
- Create `HangTenTests/BoardPresentationArtworkTests.swift`: pre-refactor non-rig byte baseline, artwork resolution/layer ordering/failure-policy tests, and source-boundary assertions.
- Modify `HangTenTests/BoardPackageStoreTests.swift`: exhaustive strict loader, PNG, relationship, and inheritance tests.
- Modify `HangTenTests/BoardPackageWriterTests.swift`: exhaustive strict writer and round-trip tests.
- Modify `HangTenTests/BoardSourceBoundaryAudit.swift`: recognize the new generic model/artwork owners without granting package-literal exemptions beyond existing canonical vocabulary.
- Modify `HangTenTests/BoardSourceBoundaryTests.swift`: assert one projection/artwork layer, unchanged hold hit-shape ownership, decorative cord modifiers, and absence of Port hardcoding.
- Create `HangTenUITests/PortDynamicCordUITests.swift`: Port presentation, tap-through, accessibility, and screenshot acceptance probes.

### Python package validator

- Create `Tools/HangboardPackages/src/hangboard_packages/cord_rig.py`: immutable rig/path types, closed parser, deterministic geometry, cubic bounds, and semantic validation.
- Modify `Tools/HangboardPackages/src/hangboard_packages/board_catalog.py`: optional rig parsing, alias rules, RGBA alpha/content inspection, and package integration.
- Create `Tools/HangboardPackages/tests/test_cord_rig.py`: frozen shared-fixture and invalid-contract unit tests.
- Modify `Tools/HangboardPackages/tests/conftest.py`: valid RGBA cord-asset fixtures and rigged package builders.
- Modify `Tools/HangboardPackages/tests/test_board_catalog.py`: package-level strict schema, relationship, alpha, and fallback tests.
- Create `Tools/HangboardPackages/tests/test_frictitious_port_a_board_dynamic_cord.py`: exact Port hashes, assets, aliases, rigs, and hold-integrity assertions.
- Modify `Tools/HangboardPackages/README.md`: document the strict optional rig schema and shared-alias asset contract.

### Hangboard Workbench

- Create `Tools/HangboardWorkbench/cord_rig.py`: independent Python parsing/geometry/bounds implementation matching the shared fixture.
- Modify `Tools/HangboardWorkbench/board_package.py`: strict rig validation, rig-only PNG alpha/content gates, editor-document round-trip, and alias inheritance.
- Modify `Tools/HangboardWorkbench/server.py`: expose resolved rig data in the selected editor document without adding a mutable alias path.
- Create `Tools/HangboardWorkbench/src/cord-rig.ts`: browser-side closed parser, projection, deterministic SVG commands, and bounds checks.
- Modify `Tools/HangboardWorkbench/src/types.ts`: exact rig/editor transport types.
- Modify `Tools/HangboardWorkbench/src/editor-model.ts`: deep-clone optional rig data for history/undo.
- Modify `Tools/HangboardWorkbench/src/workbench-client.ts`: strictly validate rig payloads and selected-presentation relationships.
- Modify `Tools/HangboardWorkbench/src/workbench-controller.ts`: validate rig-bearing editor documents before save.
- Create `Tools/HangboardWorkbench/src/components/CordRigInspector.tsx`: manual canonical rig authoring form with no image-derived defaults.
- Modify `Tools/HangboardWorkbench/src/components/HoldCanvas.tsx`: project only opted-in alias images/attachments and render decorative SVG cord below holds.
- Modify `Tools/HangboardWorkbench/src/WorkbenchApp.tsx`: connect the canonical-only rig inspector and keep aliases read-only.
- Modify `Tools/HangboardWorkbench/styles.css`: focused rig-inspector layout only.
- Modify `Tools/HangboardWorkbench/package.json`: add the focused browser geometry test to `test:modules`.
- Create `Tools/HangboardWorkbench/tests/cord-rig.test.ts`: frozen shared-fixture, projection, bounds, and parser tests.
- Modify `Tools/HangboardWorkbench/tests/workbench-modules.test.ts`: client/controller/clone/save validation tests.
- Modify `Tools/HangboardWorkbench/tests/react-editor.test.tsx`: authoring, layer order, alias image/attachment projection, hit-testing, and accessibility tests.
- Create `Tools/HangboardWorkbench/tests/test_cord_rig.py`: independent backend geometry fixture tests.
- Modify `Tools/HangboardWorkbench/tests/test_board_package.py`: backend parsing, alpha, alias, and round-trip tests.
- Modify `Tools/HangboardWorkbench/tests/test_server.py`: exact resolved-rig API payload tests.
- Modify `Tools/HangboardWorkbench/README.md`: manual authorship, alias read-only behavior, preview, and capture procedure.

### Port package and evidence

- Modify only presentation/rig fields in `Hangboards/frictitious-port-a-board/board.json`.
- Restore `Hangboards/frictitious-port-a-board/assets/primary.png`, `back.png`, and `side.png` from `e12e7f66`.
- Delete `Hangboards/frictitious-port-a-board/assets/front-inverted.png`, `back-inverted.png`, and `cord-option-4-20mm-incut.png` only after candidate validation passes.
- Create `docs/source-audits/2026-09-03-port-dynamic-cord-prototype.md`: exact source URLs, asset proof, operator-authored rig/anchor mapping, unchanged-hold proof, automated evidence, and final visual decisions.

### Task 1: Freeze the Non-Rig Compatibility Baseline

**Files:**
- Create: `HangTenTests/BoardPresentationArtworkTests.swift`
- Modify: `HangTen.xcodeproj/project.pbxproj`

**Interfaces:**
- Consumes: existing `BoardCatalog.packageStore`, `BoardPackageStore.presentationImageURL(for:presentationID:)`, and `tension.flash-board` package data.
- Produces: `BoardPresentationArtworkTests.sha256(_:) -> String`, a test-only `LegacyBoardPresentationImageReference`, and a committed regression test fixing the current non-rig canonical/alias inputs and pre-refactor rendering path before renderer work begins.

- [ ] **Step 1: Write the failing compatibility test.** Add `import CryptoKit` and this test while intentionally calling the not-yet-defined test helper:

```swift
@MainActor
func testNonRigCanonicalAndAliasLegacyImageBytesAreFrozenBeforeArtworkRefactor() throws {
    let board = try XCTUnwrap(
        BoardCatalog.packageStore.board(id: "tension.flash-board")
    )
    let expected = [
        "three-edge-upright": "a7e18e45fb3aed00c384b469778de3fb7697b176c5b4ba09582c8c7c479e0981",
        "three-edge-inverted": "81c5576eea23d6c74212fd2214be8ed7ac0b339968de285abf8ba97eb7b901a1",
    ]

    for (presentationID, expectedHash) in expected {
        let url = try XCTUnwrap(
            BoardCatalog.packageStore.presentationImageURL(
                for: board,
                presentationID: presentationID
            )
        )
        XCTAssertEqual(sha256(try Data(contentsOf: url)), expectedHash)
        XCTAssertNotNil(UIImage(contentsOfFile: url.path))
    }
}
```

- [ ] **Step 2: Verify red with the focused test.**

Run: `rtk xcodebuild test -project HangTen.xcodeproj -scheme HangTen -destination 'platform=iOS Simulator,name=iPhone 16' -only-testing:HangTenTests/BoardPresentationArtworkTests/testNonRigCanonicalAndAliasLegacyImageBytesAreFrozenBeforeArtworkRefactor`

Expected: FAIL to compile because `sha256(_:)` is undefined; do not change production code.

- [ ] **Step 3: Add the minimal deterministic test helper and frozen reference view.**

```swift
private func sha256(_ data: Data) -> String {
    SHA256.hash(data: data).map { String(format: "%02x", $0) }.joined()
}

private struct LegacyBoardPresentationImageReference: View {
    let board: TrainingBoard
    let presentationID: String

    @ViewBuilder
    var body: some View {
        if let url = BoardCatalog.packageStore.presentationImageURL(
            for: board,
            presentationID: presentationID
        ),
           let image = UIImage(contentsOfFile: url.path) {
            Image(uiImage: image).resizable()
        }
    }
}
```

Copy the existing `BoardPresentationImage.body` behavior verbatim into this test-only reference before refactoring production. Add the test file reference/build file to the `HangTenTests` group and test target in `project.pbxproj`.

- [ ] **Step 4: Verify green and preserve the baseline.**

Run the Step 2 command again.

Expected: PASS with both exact hashes. This freezes both representative non-rig inputs and the exact pre-refactor view used for the Task 9 before/after pixel comparison.

- [ ] **Step 5: Refactor and commit.** Keep hash logic private to the test file and run `rtk git diff --check`.

```bash
rtk git add HangTenTests/BoardPresentationArtworkTests.swift HangTen.xcodeproj/project.pbxproj
rtk git commit -m "test: freeze non-rig board artwork baseline"
```

### Task 2: Add the Shared Cord Model and Affine Projection API

**Files:**
- Modify: `HangTen/Models/TrainingModels.swift:51-91,721-862`
- Create: `HangTenTests/BoardCordRigGeometryTests.swift`
- Modify: `HangTen.xcodeproj/project.pbxproj`

**Interfaces:**
- Consumes: existing `BoardPresentation`, `TrainingBoard`, and `BoardPresentationGeometryProjection` behavior.
- Produces: `BoardNormalizedPoint`, `BoardGeometryRotationAnchor` alias, `BoardRGBColor`, `BoardCordRig`, `BoardDirectTwoAnchorCordRig`, `BoardPresentation.cordRig`, `TrainingBoard.canonicalPresentation(for:)`, `TrainingBoard.resolvedCordRig(for:)`, `BoardPresentationGeometryProjection.affineTransform(in:)`, and normalized-point projection.

- [ ] **Step 1: Write the failing model/projection tests.** Create `BoardCordRigGeometryTests` with exact tests:

```swift
func testAliasResolvesItsCanonicalCordRigWithoutCopyingOwnership() throws {
    let rig = BoardCordRig.directTwoAnchor(.fixture)
    let source = BoardPresentation(
        id: "front", name: "Front", aspectRatio: 2, isDefault: true,
        cordRig: rig
    )
    let alias = BoardPresentation(
        id: "front-inverted", name: "Front inverted", aspectRatio: 2,
        isDefault: false, sourcePresentationID: "front", isInverted: true,
        geometryRotationAnchor: .center
    )
    let board = fixtureBoard(presentations: [source, alias])

    XCTAssertEqual(board.canonicalPresentation(for: alias), source)
    XCTAssertEqual(board.resolvedCordRig(for: alias), rig)
    XCTAssertNil(alias.cordRig)
}

func testProjectionExposesTheSameAffineTransformForPointsAndPaths() {
    let rect = CGRect(x: 10, y: 20, width: 200, height: 100)
    let projection = BoardPresentationGeometryProjection(
        isInverted: true,
        rotationAnchor: BoardNormalizedPoint(x: 0.45, y: 0.60)
    )
    let point = CGPoint(x: 70, y: 92)

    XCTAssertEqual(projection.affineTransform(in: rect),
                   CGAffineTransform(a: -1, b: 0, c: 0, d: -1, tx: 200, ty: 160))
    XCTAssertEqual(projection.project(point, in: rect), point.applying(
        projection.affineTransform(in: rect)
    ))
    XCTAssertEqual(
        projection.project(BoardNormalizedPoint(x: 0.30, y: 0.72), in: rect),
        CGPoint(x: 130, y: 68)
    )
}
```

Define test-only `.fixture` with attachment points `(0.30, 0.72)` and `(0.70, 0.72)`, support `(0.50, 0.12)`, color bytes `(0x17, 0x17, 0x19)`, width `0.01`, radius `0.05`. Keep `fixtureBoard` wholly generic.

- [ ] **Step 2: Verify red.**

Run: `rtk xcodebuild test -project HangTen.xcodeproj -scheme HangTen -destination 'platform=iOS Simulator,name=iPhone 16' -only-testing:HangTenTests/BoardCordRigGeometryTests`

Expected: FAIL to compile because the new model and projection APIs do not exist.

- [ ] **Step 3: Implement the minimal shared model.** Use these exact public-to-module signatures:

```swift
struct BoardNormalizedPoint: Hashable {
    let x: Double
    let y: Double
    static let center = BoardNormalizedPoint(x: 0.5, y: 0.5)
    var hasFiniteNormalizedCoordinates: Bool {
        x.isFinite && y.isFinite && x >= 0 && x <= 1 && y >= 0 && y <= 1
    }
    func point(in rect: CGRect) -> CGPoint {
        CGPoint(
            x: rect.minX + CGFloat(x) * rect.width,
            y: rect.minY + CGFloat(y) * rect.height
        )
    }
}

typealias BoardGeometryRotationAnchor = BoardNormalizedPoint

struct BoardRGBColor: Hashable {
    let red: UInt8
    let green: UInt8
    let blue: UInt8
    var hexString: String {
        String(format: "#%02X%02X%02X", red, green, blue)
    }
}

enum BoardCordRig: Hashable {
    case directTwoAnchor(BoardDirectTwoAnchorCordRig)
}

struct BoardDirectTwoAnchorCordRig: Hashable {
    let attachmentPoints: [BoardNormalizedPoint]
    let supportPoint: BoardNormalizedPoint
    let cordColor: BoardRGBColor
    let cordWidth: Double
    let loopRadius: Double
}
```

Add `let cordRig: BoardCordRig?` to `BoardPresentation` with initializer default `nil`. Add exact `TrainingBoard` resolvers:

```swift
func canonicalPresentation(for presentation: BoardPresentation) -> BoardPresentation? {
    guard let sourceID = presentation.sourcePresentationID else { return presentation }
    return presentations.first { $0.id == sourceID && $0.sourcePresentationID == nil }
}

func resolvedCordRig(for presentation: BoardPresentation) -> BoardCordRig? {
    canonicalPresentation(for: presentation)?.cordRig
}
```

Refactor the projection so `project(CGPoint, in:)` and `project(Path, in:)` both apply the exact transform returned by:

```swift
func affineTransform(in rect: CGRect) -> CGAffineTransform
func project(_ point: BoardNormalizedPoint, in rect: CGRect) -> CGPoint
```

Identity presentations return `.identity`; inverted presentations rotate 180 degrees around the normalized anchor resolved inside `rect`.

- [ ] **Step 4: Verify green and existing projection compatibility.**

Run:

```bash
rtk xcodebuild test -project HangTen.xcodeproj -scheme HangTen -destination 'platform=iOS Simulator,name=iPhone 16' \
  -only-testing:HangTenTests/BoardCordRigGeometryTests \
  -only-testing:HangTenTests/BoardPackageStoreTests/testPresentationGeometryProjectionLeavesNonInvertedPointUnchanged \
  -only-testing:HangTenTests/BoardPackageStoreTests/testPresentationGeometryProjectionInvertsAroundBoardRectCenter \
  -only-testing:HangTenTests/BoardPackageStoreTests/testPresentationGeometryProjectionUsesNonCenterNormalizedAnchor \
  -only-testing:HangTenTests/BoardPackageStoreTests/testPresentationGeometryProjectionTransformsEveryPathSubpath
```

Expected: PASS. Existing hand-built presentation initializers compile unchanged because `cordRig` defaults to `nil`.

- [ ] **Step 5: Refactor and commit.** Remove the old duplicate normalized-coordinate logic from `BoardGeometryRotationAnchor`, keep names source-compatible through the typealias, and run `rtk git diff --check`.

```bash
rtk git add HangTen/Models/TrainingModels.swift HangTenTests/BoardCordRigGeometryTests.swift HangTen.xcodeproj/project.pbxproj
rtk git commit -m "feat: add generic board cord rig model"
```

### Task 3: Freeze and Implement Pure Direct-Two-Anchor Geometry

**Files:**
- Modify: `HangTenTests/Fixtures/BoardPackageValidationFixtures.json`
- Create: `HangTen/Models/BoardCordRigGeometry.swift`
- Modify: `HangTenTests/BoardCordRigGeometryTests.swift`
- Modify: `HangTen.xcodeproj/project.pbxproj`
- Modify: `HangTenTests/BoardSourceBoundaryTrackedPaths.txt`

**Interfaces:**
- Consumes: Task 2's cord models and one `BoardPresentationGeometryProjection`.
- Produces: `BoardCordPathElement`, `BoardCordPath`, `BoardCordStrand`, `BoardCordRigGeometry`, `BoardCordRigGeometry.make(rig:presentation:projection:in:)`, exact cubic bounds, `supportAssemblyStrokeBounds`, and `strokeBounds`.

- [ ] **Step 1: Add the frozen fixture and failing tests.** Add `cordRigDirectTwoAnchor` to the shared fixture with `version: 1` and this exact normalized template:

```json
{
  "minimumLoopRadiusToCordWidthRatio": 2.0,
  "circleBezier": 0.5522847498307936,
  "lineCap": "round",
  "lineJoin": "round",
  "supportLoop": [
    {"command":"move","to":[1,0]},
    {"command":"curve","control1":[1,0.5522847498307936],"control2":[0.5522847498307936,1],"to":[0,1]},
    {"command":"curve","control1":[-0.5522847498307936,1],"control2":[-1,0.5522847498307936],"to":[-1,0]},
    {"command":"curve","control1":[-1,-0.5522847498307936],"control2":[-0.5522847498307936,-1],"to":[0,-1]},
    {"command":"curve","control1":[0.5522847498307936,-1],"control2":[1,-0.5522847498307936],"to":[1,0]},
    {"command":"close"}
  ],
  "knot": [
    {"command":"move","to":[0,1]},
    {"command":"curve","control1":[-0.72,1.10],"control2":[-0.72,1.55],"to":[0,1.55]},
    {"command":"curve","control1":[0.72,1.55],"control2":[0.72,1.10],"to":[0,1.10]},
    {"command":"curve","control1":[-0.50,1.12],"control2":[-0.50,1.85],"to":[-0.36,2]},
    {"command":"move","to":[0,1.10]},
    {"command":"curve","control1":[0.50,1.12],"control2":[0.50,1.85],"to":[0.36,2]}
  ],
  "strandExits": [[-0.36,2],[0.36,2]]
}
```

Add two cases using the Task 2 fixture rig:

- `square-upright`: canvas `(0,0,100,100)`, non-inverted, expected attachments `(30,72)` and `(70,72)`, exits `(48.2,22)` and `(51.8,22)`, support bounds `(44.5,6.5,11,16)`, full bounds `(29.5,6.5,41,66)`.
- `centered-inverted`: canvas `(0,0,100,100)`, inverted around `(0.50,0.50)`, expected attachments `(70,28)` and `(30,28)`, exits `(48.2,22)` and `(51.8,22)`, support bounds `(44.5,6.5,11,16)`, full bounds `(29.5,6.5,41,22)`.
- `offset-noncenter-inverted`: canvas `(10,20,200,100)`, inverted around `(0.45,0.60)`, expected attachments `(130,68)` and `(50,68)`, exits `(108.2,42)` and `(111.8,42)`, support bounds `(104.5,26.5,11,16)`, full bounds `(49.5,26.5,81,42)`.

Write tests named `testDirectTwoAnchorTemplateMatchesFrozenPathElements`, `testDirectTwoAnchorGeometryMatchesFrozenCanvasCases`, `testSupportStaysWorldUpWhileAttachmentsProject`, `testLoopIsClosedAndStrandsAreSingleStraightSegments`, and `testCubicBoundsIncludeInteriorDerivativeExtrema`.

- [ ] **Step 2: Verify red.**

Run: `rtk xcodebuild test -project HangTen.xcodeproj -scheme HangTen -destination 'platform=iOS Simulator,name=iPhone 16' -only-testing:HangTenTests/BoardCordRigGeometryTests`

Expected: FAIL because `BoardCordRigGeometry` and path types do not exist.

- [ ] **Step 3: Implement the pure geometry.** Use these signatures:

```swift
enum BoardCordPathElement: Hashable {
    case move(CGPoint)
    case line(CGPoint)
    case cubicCurve(to: CGPoint, control1: CGPoint, control2: CGPoint)
    case close
}

struct BoardCordPath: Hashable {
    let elements: [BoardCordPathElement]
    var path: Path { get }
    var exactBounds: CGRect { get }
}

struct BoardCordStrand: Hashable {
    let start: CGPoint
    let end: CGPoint
    var path: Path { get }
}

struct BoardCordRigGeometry: Hashable {
    static let minimumLoopRadiusToCordWidthRatio = 2.0
    let supportLoop: BoardCordPath
    let knot: BoardCordPath
    let strands: [BoardCordStrand]
    let projectedAttachments: [CGPoint]
    let strokeWidth: CGFloat
    let supportAssemblyStrokeBounds: CGRect
    let strokeBounds: CGRect

    static func make(
        rig: BoardCordRig,
        presentation: BoardPresentation,
        projection: BoardPresentationGeometryProjection,
        in canvas: CGRect
    ) -> BoardCordRigGeometry
}
```

Scale all fixture template coordinates by `radius = rig.loopRadius * min(canvas.width, canvas.height)` and translate by `rig.supportPoint.point(in: canvas)`. Set `strokeWidth = rig.cordWidth * min(canvas.width, canvas.height)`. Pair strand exit zero with attachment zero and exit one with attachment one; never sort projected attachments. Compute exact cubic bounds by solving each derivative quadratic per axis for roots strictly inside `(0,1)`, evaluating those roots plus endpoints, then expand the union by `strokeWidth / 2`. Include `presentation` in the API as the selected presentation contract and add a debug precondition that the supplied projection equals `BoardPresentationGeometryProjection(presentation:)`.

- [ ] **Step 4: Verify green at both sizes.** Run the Step 2 command.

Expected: PASS with exact elements/bounds (use `accuracy: 1e-9` for floating-point assertions), unchanged support elements between upright/inverted fixtures, and exactly two one-line strands.

- [ ] **Step 5: Refactor and commit.** Keep geometry independent of `Color`, `View`, time, random state, and package identity. Add `BoardCordRigGeometry.swift` to app and test compilation in `project.pbxproj`, add its relative path to the sorted boundary manifest, then run `rtk git diff --check` and `rtk ./scripts/verify-board-source-boundary-manifest.sh`.

```bash
rtk git add HangTenTests/Fixtures/BoardPackageValidationFixtures.json HangTen/Models/BoardCordRigGeometry.swift HangTenTests/BoardCordRigGeometryTests.swift HangTen.xcodeproj/project.pbxproj HangTenTests/BoardSourceBoundaryTrackedPaths.txt
rtk git commit -m "feat: add deterministic board cord geometry"
```

### Task 4: Add Strict iOS Package Decoding and Rig-Only Image Validation

**Files:**
- Modify: `HangTen/Models/BoardPackageStore.swift:106-203,270-442,540-629,876-1110`
- Modify: `HangTenTests/BoardPackageStoreTests.swift`
- Modify: `HangTenTests/Fixtures/BoardPackageValidationFixtures.json`

**Interfaces:**
- Consumes: Tasks 2-3 models/geometry and the selected presentation's normalized-aspect canvas `CGRect(x: 0, y: 0, width: aspectRatio, height: 1)`.
- Produces: strict `BoardPackageCordRigDocument`, decoded `BoardCordRig`, `BoardPackagePNGInspection`, and `BoardPresentation.cordRig` only on validated canonical owners.

- [ ] **Step 1: Write valid decode/inheritance and legacy tests.** Add exact tests `testStoreDecodesValidDirectTwoAnchorRigAndAliasInheritance` and `testStoreKeepsOmittedCordRigNilAndLegacyAssetSelectionUnchanged`. The valid fixture must use a generated 40 × 20 color-type-6 PNG with a fully transparent border/corners and a nonzero-alpha centered rectangle; declare the alias path equal to its source and explicit center anchor. Assert the runtime source owns `.directTwoAnchor`, the alias's own `cordRig` is `nil`, `board.resolvedCordRig(for: alias)` equals the source rig, and both presentation URLs contain identical bytes.

- [ ] **Step 2: Write the failing strict-schema/semantic matrix.** Add these named tests, with table rows that mutate one rule at a time and assert `malformedJSON` for closed-decoding failures or exact `invalidPackage` reason prefixes for semantic failures:

```swift
func testStoreTreatsClosedCordRigDecodeFailuresAsMalformedJSON() throws
func testStoreRejectsInvalidDirectTwoAnchorValues() throws
func testStoreRejectsCordRigOwnershipAndAliasRelationshipViolations() throws
func testStoreRejectsCordGeometryOutsideTheCanvasOrBelowAttachments() throws
func testStoreRejectsRiggedPNGWithoutRGBAAlphaContentAndTransparentCorners() throws
func testStoreRejectsProjectedRiggedAlphaContentOutsideAliasCanvas() throws
func testStoreDoesNotApplyRigOnlyPNGRulesToLegacyPackages() throws
```

The closed-decode rows are: an unknown rig key, unknown point key, unknown `type`, every missing required key, `null`, boolean/string/array in every numeric/object slot, attachment array of the wrong JSON type, and color of the wrong JSON type. Semantic rows are: one/three attachment points, equal points, each finite coordinate at `-0.01` and `1.01`, colors missing `#`, three/eight hex digits, non-hex digits, nonpositive width/radius, `loopRadius < 2 * cordWidth`, cropped loop/knot/strand bounds, support assembly not strictly above both attachments, alias-owned rig, canonical inverted owner, mismatched alias asset, missing explicit inverted anchor, and failed alias projection. PNG rows are RGB, fully opaque RGBA, fully transparent RGBA, one nontransparent corner, corrupt compressed bytes, and nonempty content projected outside the alias canvas.

- [ ] **Step 3: Verify red.**

Run: `rtk xcodebuild test -project HangTen.xcodeproj -scheme HangTen -destination 'platform=iOS Simulator,name=iPhone 16' -only-testing:HangTenTests/BoardPackageStoreTests`

Expected: new tests FAIL because `cordRig` is an unknown presentation key and rig-only PNG/relationship rules do not exist; existing tests remain green before implementation.

- [ ] **Step 4: Implement strict decoding and semantic validation.** Add `cordRig` to only the presentation document's allowed/CodingKeys sets. Decode a closed raw document and adapt after decoding so malformed shape/type errors remain `malformedJSON`, while relationship/coordinate/appearance/geometry failures throw `.invalidPackage(boardID:reason:)` naming the presentation and rule. Parse color with exact regex `^#[0-9A-Fa-f]{6}$` and store byte channels; canonical writing later emits uppercase.

Refactor PNG validation to return:

```swift
private struct BoardPackagePNGInspection {
    let width: Int
    let height: Int
    let pngColorType: UInt8
    let hasTransparentPixel: Bool
    let hasVisiblePixel: Bool
    let cornersAreTransparent: Bool
    let normalizedVisibleBounds: CGRect?
}
```

Use the IHDR color-type byte and an ImageIO-decoded `CGImage` drawn into a known RGBA8 bitmap to inspect alpha for rigged asset paths only. Continue the existing lightweight size/PNG validation for non-rig assets. Cache inspection by unique asset path so aliases do not decode shared bytes twice. Validate source and every alias geometry using `BoardCordRigGeometry.make`; require the support assembly max-Y `<` each attachment Y and require `canvas.insetBy(dx: -1e-12, dy: -1e-12).contains(strokeBounds)`. Project visible alpha bounds with the same affine transform, not a second formula.

- [ ] **Step 5: Verify green and compatibility.**

Run:

```bash
rtk xcodebuild test -project HangTen.xcodeproj -scheme HangTen -destination 'platform=iOS Simulator,name=iPhone 16' \
  -only-testing:HangTenTests/BoardPackageStoreTests \
  -only-testing:HangTenTests/BoardPresentationArtworkTests/testNonRigCanonicalAndAliasLegacyImageBytesAreFrozenBeforeArtworkRefactor
```

Expected: PASS, including existing alias-chain, aspect, projected-hold, package-root, declared-asset-set, and ordinary PNG tests.

- [ ] **Step 6: Refactor and commit.** Centralize reason strings, keep Port literals out of production, run `rtk git diff --check`, then commit.

```bash
rtk git add HangTen/Models/BoardPackageStore.swift HangTenTests/BoardPackageStoreTests.swift HangTenTests/Fixtures/BoardPackageValidationFixtures.json
rtk git commit -m "feat: validate cord rigs in board packages"
```

### Task 5: Add Exact iOS Writer Round-Trip and Matching Validation

**Files:**
- Modify: `HangTen/Models/BoardPackageWriter.swift:3-196,428-670,820-890`
- Modify: `HangTenTests/BoardPackageWriterTests.swift`

**Interfaces:**
- Consumes: `BoardCordRig`, Task 3 geometry/bounds, `BoardEditablePresentation`, and canonical JSON serialization.
- Produces: `BoardEditablePresentation.cordRig: BoardCordRig?`, strict decode, writer validation, and canonical `cordRig` output ordered `type`, `attachmentPoints`, `supportPoint`, `cordColor`, `cordWidth`, `loopRadius`.

- [ ] **Step 1: Write failing writer round-trip tests.** Add `testWriterRoundTripsDirectTwoAnchorRigInCanonicalOrder` and `testWriterOmitsAbsentCordRigWithoutChangingLegacyBytes`. The first must decode a valid lowercase-color rig, write it, re-decode it, assert semantic equality/idempotent bytes, and assert canonical uppercase `"cordColor": "#171719"` and exact key order. The second compares the pre-change `makeDocument()` bytes to the writer output after the optional property exists.

- [ ] **Step 2: Write the failing writer validation matrix.** Add:

```swift
func testWriterRejectsClosedCordRigDecodeFailures()
func testWriterRejectsInvalidDirectTwoAnchorValues()
func testWriterRejectsAliasOwnedRigAndRiggedAliasContractViolations()
func testWriterRejectsCordGeometryOutsideCanvasOrBelowAttachments()
```

Use the same malformed and semantic rows from Task 4 except PNG/content tests, which are impossible for the document-only writer. Every hand-built semantic failure must be `.invalid` with the exact prefix `board test.board: presentation ` followed by the mutated presentation ID and failed-rule text.

- [ ] **Step 3: Verify red.**

Run: `rtk xcodebuild test -project HangTen.xcodeproj -scheme HangTen -destination 'platform=iOS Simulator,name=iPhone 16' -only-testing:HangTenTests/BoardPackageWriterTests`

Expected: FAIL because editable presentations do not decode/store/write rigs.

- [ ] **Step 4: Implement minimal writer support.** Add optional `cordRig` with initializer default `nil`, a closed private document decoder that maps into the shared model, and `canonicalCordRigValue(_:)`. Validate owner/alias/asset/anchor and normalized geometry before serializing, using the exact `2.0` ratio and Task 3 geometry. Keep image-dependent alpha checks exclusively in finished-package loaders.

- [ ] **Step 5: Verify green and full writer regression.** Run the Step 3 command.

Expected: PASS, including all pre-existing editable hold/alias/canonical-order tests.

- [ ] **Step 6: Refactor and commit.** Keep schema ordering in one serializer function, run `rtk git diff --check`, then commit.

```bash
rtk git add HangTen/Models/BoardPackageWriter.swift HangTenTests/BoardPackageWriterTests.swift
rtk git commit -m "feat: round trip cord rigs in board writer"
```

### Task 6: Implement Python Package-Validator Parity

**Files:**
- Create: `Tools/HangboardPackages/src/hangboard_packages/cord_rig.py`
- Modify: `Tools/HangboardPackages/src/hangboard_packages/board_catalog.py:1-190,380-440,609-750,850-1110`
- Create: `Tools/HangboardPackages/tests/test_cord_rig.py`
- Modify: `Tools/HangboardPackages/tests/conftest.py`
- Modify: `Tools/HangboardPackages/tests/test_board_catalog.py`

**Interfaces:**
- Consumes: shared fixture contract and package validator `NormalizedPoint`.
- Produces: immutable `DirectTwoAnchorCordRig`, `CordPathElement`, `CordGeometry`, `parse_cord_rig(value, source)`, `direct_two_anchor_geometry(rig, *, is_inverted, rotation_anchor, canvas)`, and `validate_cord_rig_relationships(presentations)` used by `board_catalog`.

- [ ] **Step 1: Write failing pure fixture tests.** In `test_cord_rig.py`, load `HangTenTests/Fixtures/BoardPackageValidationFixtures.json` and add exact tests `test_direct_two_anchor_template_matches_shared_fixture`, `test_direct_two_anchor_geometry_matches_both_shared_canvas_cases`, `test_cubic_bounds_include_interior_extrema`, and `test_projection_changes_only_attachments`. Compare floats with `pytest.approx(abs=1e-9)`.

- [ ] **Step 2: Write failing parser/package tests.** Add `test_direct_two_anchor_parser_rejects_every_closed_schema_failure`, `test_package_rejects_every_semantic_cord_rig_failure`, `test_package_rejects_rigged_alias_contract_failures`, `test_package_rejects_invalid_rigged_rgba_alpha_and_content_projection`, and `test_non_rig_packages_keep_accepting_existing_opaque_and_transparent_assets`. Reuse the complete Task 4 matrix and assert message substrings naming the presentation/rule.

- [ ] **Step 3: Verify red.**

Run: `rtk python3 -m pytest Tools/HangboardPackages/tests/test_cord_rig.py Tools/HangboardPackages/tests/test_board_catalog.py -q`

Expected: collection/import FAIL for missing `hangboard_packages.cord_rig` and rig package cases fail as unknown keys.

- [ ] **Step 4: Implement geometry/parser and catalog integration.** Mirror Task 3's exact constants and declared ordering without importing Swift/TypeScript artifacts. Use dataclasses and these signatures:

```python
@dataclass(frozen=True)
class DirectTwoAnchorCordRig:
    attachment_points: tuple[NormalizedPoint, NormalizedPoint]
    support_point: NormalizedPoint
    cord_color: tuple[int, int, int]
    cord_width: float
    loop_radius: float

def parse_cord_rig(value: object, source: str) -> DirectTwoAnchorCordRig:
    """Return the strict parsed rig or raise BoardPackageError naming source."""

def direct_two_anchor_geometry(
    rig: DirectTwoAnchorCordRig,
    *,
    is_inverted: bool,
    rotation_anchor: NormalizedPoint,
    canvas: tuple[float, float, float, float],
) -> CordGeometry:
    """Return deterministic paths, projected attachments, and exact bounds."""
```

Extend `BoardPresentation` with `cord_rig: DirectTwoAnchorCordRig | None`. In `_validate_finished_shape`, inspect RGBA alpha only for rig owners. Extend the existing standard-library PNG decoder to unfilter every RGBA8/RGBA16 scanline, including each Adam7 pass, map pass coordinates back to the full image, and return zero/nonzero counts, four corner alpha values, and inclusive visible-pixel bounds normalized with `(max - min + 1) / dimension`. Do not add Pillow to runtime validation.

- [ ] **Step 5: Verify green and the complete package suite.**

Run:

```bash
rtk python3 -m pytest Tools/HangboardPackages/tests/test_cord_rig.py Tools/HangboardPackages/tests/test_board_catalog.py -q
rtk python3 -m pytest Tools/HangboardPackages/tests -q
rtk scripts/hangboard-packages.sh validate --root Hangboards --final-inventory
```

Expected: focused and full suites PASS; current catalog validation still passes because no package is opted in yet.

- [ ] **Step 6: Refactor and commit.** Keep parsing/geometry in `cord_rig.py`, file/container logic in `board_catalog.py`, and no Port literals in either. Run `rtk git diff --check`.

```bash
rtk git add Tools/HangboardPackages/src/hangboard_packages/cord_rig.py Tools/HangboardPackages/src/hangboard_packages/board_catalog.py Tools/HangboardPackages/tests/test_cord_rig.py Tools/HangboardPackages/tests/conftest.py Tools/HangboardPackages/tests/test_board_catalog.py
rtk git commit -m "feat: validate cord rigs in package tools"
```

### Task 7: Add Workbench Backend Validation and Round-Trip Parity

**Files:**
- Create: `Tools/HangboardWorkbench/cord_rig.py`
- Modify: `Tools/HangboardWorkbench/board_package.py:1-210,262-370,1147-1370,2190-2525`
- Modify: `Tools/HangboardWorkbench/server.py:159-232`
- Create: `Tools/HangboardWorkbench/tests/test_cord_rig.py`
- Modify: `Tools/HangboardWorkbench/tests/workbench_fixtures.py`
- Modify: `Tools/HangboardWorkbench/tests/test_board_package.py`
- Modify: `Tools/HangboardWorkbench/tests/test_server.py`

**Interfaces:**
- Consumes: shared fixture contract and Workbench's selected-presentation/editor-document flow.
- Produces: independent backend `DirectTwoAnchorCordRig`, `direct_two_anchor_geometry`, strict finished-package validation, `BoardPresentation.cord_rig`, the `cordRig` value returned by `editor_document`, and canonical-only persistence back to the selected presentation.

- [ ] **Step 1: Write failing independent geometry/parser tests.** Add the same four shared-fixture tests from Task 6 to Workbench's new `test_cord_rig.py`, importing only `Tools/HangboardWorkbench/cord_rig.py`. Add the complete closed/semantic parser matrix so this implementation cannot pass by importing the package-validator module.

- [ ] **Step 2: Write failing package and server tests.** Add exact test names `test_loads_and_round_trips_a_valid_canonical_direct_two_anchor_rig`, `test_alias_editor_document_inherits_rig_but_save_remains_read_only`, `test_save_can_add_update_and_remove_a_canonical_rig_without_changing_holds`, `test_rejects_rigged_alias_ownership_path_anchor_and_bounds_failures`, `test_rejects_rigged_assets_without_rgba_transparency_corners_or_visible_content`, `test_rejects_alias_projected_alpha_content_outside_canvas`, `test_non_rig_package_behavior_is_unchanged`, and `test_board_payload_exposes_the_exact_resolved_rig_for_source_and_alias`.

Assert that `editor_document` carries raw canonical normalized attachments for both source and alias; the selected presentation metadata controls preview projection. Snapshot `board.json` holds before save and assert exact equality after rig edits.

- [ ] **Step 3: Verify red.**

Run: `rtk python3 -m pytest Tools/HangboardWorkbench/tests/test_cord_rig.py Tools/HangboardWorkbench/tests/test_board_package.py Tools/HangboardWorkbench/tests/test_server.py -q`

Expected: import FAIL for `cord_rig` and package/API tests fail on unknown rig data.

- [ ] **Step 4: Implement backend parity.** Independently encode the exact Task 3 constants/signatures in Workbench `cord_rig.py`. Extend `BoardPresentation` with `cord_rig: DirectTwoAnchorCordRig | None`; resolve aliases from their canonical source only after validating no alias owns a rig. Add `cordRig` to editor documents, `_validate_editor_document`, and `_apply_editor_document` for canonical selections; aliases remain rejected by `save_editor_document`.

Extend Workbench's standard-library PNG decoder with the same RGBA8/RGBA16 Adam7 unfilter/alpha inspection contract as Task 6. Keep header-only catalog discovery lightweight; full open/save must decode and enforce rig-only alpha/content rules. `_write_json(path, value)` must continue serializing with `allow_nan=False` and emit exact `cordRig` field names without changing unrelated keys.

- [ ] **Step 5: Verify green and all Workbench Python tests.**

Run:

```bash
rtk python3 -m pytest Tools/HangboardWorkbench/tests/test_cord_rig.py Tools/HangboardWorkbench/tests/test_board_package.py Tools/HangboardWorkbench/tests/test_server.py -q
rtk python3 -m pytest Tools/HangboardWorkbench/tests -q
```

Expected: PASS, including local/hosted save, alias edit rejection, package atomicity, and PNG corruption tests.

- [ ] **Step 6: Refactor and commit.** Keep geometry free of Flask/server/package identity and verify `rtk rg -n 'frictitious|port-a-board|Port-A-Board' Tools/HangboardWorkbench/cord_rig.py Tools/HangboardWorkbench/board_package.py Tools/HangboardWorkbench/server.py` returns no matches.

```bash
rtk git add Tools/HangboardWorkbench/cord_rig.py Tools/HangboardWorkbench/board_package.py Tools/HangboardWorkbench/server.py Tools/HangboardWorkbench/tests/test_cord_rig.py Tools/HangboardWorkbench/tests/workbench_fixtures.py Tools/HangboardWorkbench/tests/test_board_package.py Tools/HangboardWorkbench/tests/test_server.py
rtk git commit -m "feat: round trip cord rigs in workbench backend"
```

### Task 8: Add Workbench Manual Authoring and Deterministic Preview

**Files:**
- Create: `Tools/HangboardWorkbench/src/cord-rig.ts`
- Modify: `Tools/HangboardWorkbench/src/types.ts:1-145,312-380`
- Modify: `Tools/HangboardWorkbench/src/editor-model.ts:1-75`
- Modify: `Tools/HangboardWorkbench/src/workbench-client.ts:1-190`
- Modify: `Tools/HangboardWorkbench/src/workbench-controller.ts:1-150`
- Create: `Tools/HangboardWorkbench/src/components/CordRigInspector.tsx`
- Modify: `Tools/HangboardWorkbench/src/components/HoldCanvas.tsx:1-420`
- Modify: `Tools/HangboardWorkbench/src/WorkbenchApp.tsx:1-370`
- Modify: `Tools/HangboardWorkbench/styles.css`
- Modify: `Tools/HangboardWorkbench/package.json`
- Create: `Tools/HangboardWorkbench/tests/cord-rig.test.ts`
- Modify: `Tools/HangboardWorkbench/tests/workbench-modules.test.ts`
- Modify: `Tools/HangboardWorkbench/tests/react-editor.test.tsx`

**Interfaces:**
- Consumes: Task 7's `EditorDocument.cordRig` JSON and selected `BoardPresentation` inversion/anchor metadata.
- Produces: TypeScript `DirectTwoAnchorCordRig`, `CordRigGeometry`, `parseCordRig`, `directTwoAnchorGeometry`, deep clone/save validation, canonical-only `CordRigInspector`, and SVG preview/image projection.

- [ ] **Step 1: Write failing browser geometry/client tests.** Add `cord-rig.test.ts` to `test:modules`, load the shared fixture with `readFileSync`, and implement failing tests named `browser template matches the shared direct-two-anchor fixture`, `browser geometry matches both shared canvas cases`, `browser projects only attachments`, and `browser parser rejects every closed and semantic failure`. In `workbench-modules.test.ts`, add failing payload tests for exact rig preservation, unknown/missing keys, duplicate points, invalid color/ratio/bounds, rig on alias, and deep clone/history isolation.

- [ ] **Step 2: Write failing React authoring/layer tests.** In `react-editor.test.tsx`, add:

```text
"canonical cord inspector applies only a fully entered evidence-reviewed rig"
"cord rig changes participate in undo redo autosave and explicit save"
"alias cord inspector is read only and cannot mutate inherited data"
"rigged alias image and attachments share one 180 degree transform"
"support loop and knot remain world up across source and alias"
"cord preview is between image and holds and has no pointer or accessibility surface"
"non rig canvas keeps the original image and hold DOM without a cord group"
```

Assert DOM child order `#board-image`, `#cord-overlay`, then `#hold-overlay`; `#cord-overlay` has `aria-hidden="true"` and `pointer-events="none"`; an event fired on a strand targets the underlying SVG/hold, never a cord handler.

- [ ] **Step 3: Verify red.**

Run:

```bash
rtk npm --prefix Tools/HangboardWorkbench run typecheck
rtk npm --prefix Tools/HangboardWorkbench run test:modules
rtk npm --prefix Tools/HangboardWorkbench run test:react
```

Expected: typecheck/test FAIL because rig types, parser, inspector, and preview do not exist.

- [ ] **Step 4: Implement exact browser types and geometry.** Define:

```typescript
export interface DirectTwoAnchorCordRig {
  type: "directTwoAnchor";
  attachmentPoints: [Point, Point];
  supportPoint: Point;
  cordColor: string;
  cordWidth: number;
  loopRadius: number;
}

export interface EditorDocument {
  presentationID?: string;
  equipmentObjects?: string[];
  cordRig?: DirectTwoAnchorCordRig;
  canvas: { width: number; height: number };
  regions: HoldRegion[];
}

export function parseCordRig(value: unknown): DirectTwoAnchorCordRig;
export function directTwoAnchorGeometry(
  rig: DirectTwoAnchorCordRig,
  presentation: Pick<BoardPresentation, "isInverted" | "geometryRotationAnchor">,
  canvas: { width: number; height: number },
): CordRigGeometry;
```

Implement constants independently from the shared fixture and validate them against it in tests. Update every exact-key guard in client/controller, and deep-copy both attachment objects/support object in `cloneEditorDocument`.

- [ ] **Step 5: Implement manual authoring and SVG preview.** `CordRigInspector` must use local string fields for two attachment X/Y pairs, support X/Y, color, width, and radius. For an absent rig, all fields start blank; no model is created and no default geometry is suggested. Enable `Apply rig` only when the closed parser and bounds check succeed; `Remove rig` deletes only the optional field. Existing rigs prefill exactly. Call `actions.editDocument` so changes enter history/dirty/autosave. On aliases, render values read-only with the exact prefix `Cord rig inherited from ` followed by the source presentation ID.

In `HoldCanvas`, resolve the selected presentation and create geometry from `document.cordRig`. The direct children of `#editor-svg` must preserve this exact relative order: `image#board-image`, optional `g#cord-overlay`, existing `g#guide-overlay`, then existing `g#hold-overlay`. Set the image's `transform` to `riggedAliasTransformOrUndefined`; set the cord group to `aria-hidden="true"` and `pointerEvents="none"`; append its paths in the exact order support loop, knot, strand zero, strand one.

Use SVG `rotate(180 anchorX anchorY)` only when a rig is present and the selected presentation is inverted. Apply `strokeLinecap="round"`, `strokeLinejoin="round"`, `fill="none"`, exact color/width, and no transition/animation class. Do not transform the support group. Keep existing backend-projected hold paths unchanged.

- [ ] **Step 6: Verify green and browser bundle.**

Run:

```bash
rtk npm --prefix Tools/HangboardWorkbench test
rtk npm --prefix Tools/HangboardWorkbench run check:bundle
```

Expected: typecheck, modules, React, and bundle PASS; non-rig DOM snapshots remain unchanged except test assertions explicitly covering the absent optional field.

- [ ] **Step 7: Refactor and commit.** Keep `CordRigInspector` separate from hold editing, ensure no Port literal appears in production TypeScript, and run `rtk git diff --check`.

```bash
rtk git add Tools/HangboardWorkbench/src/cord-rig.ts Tools/HangboardWorkbench/src/types.ts Tools/HangboardWorkbench/src/editor-model.ts Tools/HangboardWorkbench/src/workbench-client.ts Tools/HangboardWorkbench/src/workbench-controller.ts Tools/HangboardWorkbench/src/components/CordRigInspector.tsx Tools/HangboardWorkbench/src/components/HoldCanvas.tsx Tools/HangboardWorkbench/src/WorkbenchApp.tsx Tools/HangboardWorkbench/styles.css Tools/HangboardWorkbench/package.json Tools/HangboardWorkbench/tests/cord-rig.test.ts Tools/HangboardWorkbench/tests/workbench-modules.test.ts Tools/HangboardWorkbench/tests/react-editor.test.tsx
rtk git commit -m "feat: preview and author cord rigs in workbench"
```

### Task 9: Add the Shared SwiftUI Artwork Layer

**Files:**
- Create: `HangTen/Views/BoardPresentationArtwork.swift`
- Modify: `HangTen/Views/BoardMapView.swift:250-325,440-530,535-607`
- Modify: `HangTenTests/BoardPresentationArtworkTests.swift`
- Modify: `HangTenTests/BoardSourceBoundaryAudit.swift`
- Modify: `HangTenTests/BoardSourceBoundaryTests.swift:275-345,390-490`
- Modify: `HangTen.xcodeproj/project.pbxproj`
- Modify: `HangTenTests/BoardSourceBoundaryTrackedPaths.txt`

**Interfaces:**
- Consumes: `TrainingBoard.resolvedCordRig(for:)`, one caller-created projection, Task 3 geometry, selected package image URL, and exact `boardBounds`.
- Produces: `BoardPresentationArtwork`, `BoardCordRigView`, `BoardPresentationArtworkResolution`, `BoardPresentationArtworkLayer`, and the same shared layer in both map screens.

- [ ] **Step 1: Write failing resolution/layer tests.** Extend `BoardPresentationArtworkTests` with:

```swift
func testArtworkResolutionUsesExplicitLegacyBranchWhenRigIsAbsent()
func testArtworkResolutionSharesCanonicalBytesAndProjectsOnlyRiggedAliasImage()
func testRiggedArtworkLayerOrderIsImageThenCordAndMapLayersRemainAbove()
func testMissingRiggedImageSuppressesImageAndCordTogether()
func testCordViewIsDecorativeNonAnimatedAndGestureFree()
func testNonRigCanonicalAndAliasPixelSnapshotsMatchLegacyReference()
```

Use a pure resolution value so tests can assert `imagePresentationID`, `cordRig`, `projectsImage`, `layerOrder`, and `failurePolicy` without view introspection. For the pixel regression, render the Task 1 `LegacyBoardPresentationImageReference` and the new legacy branch at exactly `600 × 400` points with `ImageRenderer.scale = 1`, convert both `CGImage` results through the same RGBA8 bitmap helper, and require equal SHA-256 hashes for `three-edge-upright` and `three-edge-inverted`; also retain Task 1's exact input-byte checks. Update source-boundary tests to require both map sites to pass the same local `projection` and `boardBounds` into `BoardPresentationArtwork`, and to reject `frictitious`, Port IDs/names, or asset names in both new runtime files.

- [ ] **Step 2: Verify red.**

Run:

```bash
rtk xcodebuild test -project HangTen.xcodeproj -scheme HangTen -destination 'platform=iOS Simulator,name=iPhone 16' \
  -only-testing:HangTenTests/BoardPresentationArtworkTests \
  -only-testing:HangTenTests/BoardSourceBoundaryTests
```

Expected: FAIL because the shared artwork types and map wiring do not exist.

- [ ] **Step 3: Implement the minimal shared artwork.** Use these interfaces:

```swift
struct BoardPresentationArtworkResolution: Hashable {
    enum FailurePolicy: Hashable { case omitArtworkAndAssert }
    let imagePresentationID: String
    let cordRig: BoardCordRig?
    let projectsImage: Bool
    let layerOrder: [BoardPresentationArtworkLayer]
    let failurePolicy: FailurePolicy?

    static func resolve(
        board: TrainingBoard,
        presentation: BoardPresentation
    ) -> BoardPresentationArtworkResolution
}

enum BoardPresentationArtworkLayer: Hashable {
    case legacyImage
    case image
    case cord
}

struct BoardPresentationArtwork: View {
    let board: TrainingBoard
    let presentation: BoardPresentation
    let projection: BoardPresentationGeometryProjection
    let boardBounds: CGSize
}

struct BoardCordRigView: View {
    let rig: BoardCordRig
    let presentation: BoardPresentation
    let projection: BoardPresentationGeometryProjection
    let boardRect: CGRect
}
```

For `cordRig == nil`, `BoardPresentationArtwork.body` must directly return `BoardPresentationImage(board:presentationID:)` with the selected ID and no transform/wrapper cord. For a rig, load the selected shared path once via a factored `BoardPresentationImage.loadUIImage`; on failure call `assertionFailure` in DEBUG and return no image/cord. On success, frame the resizable image to exact bounds and apply `projection.affineTransform(in: boardRect)` through `.transformEffect` only when `projectsImage` is true, then place `BoardCordRigView` above it.

`BoardCordRigView` converts Task 3 paths, uses `StrokeStyle(lineWidth:lineCap:.round,lineJoin:.round)`, `.foregroundStyle` from RGB bytes, `.transaction { $0.animation = nil }`, `.allowsHitTesting(false)`, and `.accessibilityHidden(true)`. Add no identifiers, labels, content shapes, gestures, focus, or hover.

- [ ] **Step 4: Wire both map screens.** Each `GeometryReader` constructs exactly one projection. Replace only the old image child with `BoardPresentationArtwork`; retain the current `ForEach` hold visuals, their explicit full-canvas frames, marker placement, picker labels, and outer aspect-fit frame. Detail markers stay after hold visuals; cord stays inside artwork below both.

- [ ] **Step 5: Verify green, fallback hashes, and interactions.**

Run:

```bash
rtk xcodebuild test -project HangTen.xcodeproj -scheme HangTen -destination 'platform=iOS Simulator,name=iPhone 16' \
  -only-testing:HangTenTests/BoardPresentationArtworkTests \
  -only-testing:HangTenTests/BoardSourceBoundaryTests \
  -only-testing:HangTenTests/BoardPackageStoreTests/testBoardMapSelectionKeepsAnInvertedAliasForItsSourceHolds \
  -only-testing:HangTenTests/BoardPackageStoreTests/testProjectedRectangularHoldContainsTheProjectedMarkerCenter
```

Expected: PASS; the Task 1 canonical/alias byte hashes are unchanged, both `600 × 400` before/after RGBA pixel hashes are identical, and source audit still sees one physical hold path for fill/stroke/hit/accessibility.

- [ ] **Step 6: Refactor and commit.** Add the new view to app/test targets, add its sorted path to the boundary manifest, grant only `BoardCordRigGeometry.swift` and `BoardPresentationArtwork.swift` generic-owner status in `BoardSourceBoundaryAudit`, run boundary verification and `rtk git diff --check`.

```bash
rtk ./scripts/verify-board-source-boundary-manifest.sh
rtk git add HangTen/Views/BoardPresentationArtwork.swift HangTen/Views/BoardMapView.swift HangTenTests/BoardPresentationArtworkTests.swift HangTenTests/BoardSourceBoundaryAudit.swift HangTenTests/BoardSourceBoundaryTests.swift HangTen.xcodeproj/project.pbxproj HangTenTests/BoardSourceBoundaryTrackedPaths.txt
rtk git commit -m "feat: render shared dynamic board artwork"
```

### Task 10: Restore and Configure the Port Package from Operator-Reviewed Evidence

**Files:**
- Modify: `Hangboards/frictitious-port-a-board/board.json` (presentation/rig fields only)
- Modify: `Hangboards/frictitious-port-a-board/assets/primary.png`
- Modify: `Hangboards/frictitious-port-a-board/assets/back.png`
- Modify: `Hangboards/frictitious-port-a-board/assets/side.png`
- Delete after candidate passes: `Hangboards/frictitious-port-a-board/assets/front-inverted.png`
- Delete after candidate passes: `Hangboards/frictitious-port-a-board/assets/back-inverted.png`
- Delete after candidate passes: `Hangboards/frictitious-port-a-board/assets/cord-option-4-20mm-incut.png`
- Create: `Tools/HangboardPackages/tests/test_frictitious_port_a_board_dynamic_cord.py`
- Create: `docs/source-audits/2026-09-03-port-dynamic-cord-prototype.md`
- Modify: `Tools/HangboardPackages/README.md`
- Modify: `Tools/HangboardWorkbench/README.md`

**Interfaces:**
- Consumes: all strict validators/previews, exact historical blobs, current six presentation records, and a human operator's deliberate review of cited manufacturer evidence/restored art.
- Produces: three unique exact assets, three canonical rigs (`primary`, `back`, `side`), three rig-inheriting aliases with explicit anchors/shared paths, the immutable Port audit, and no hold changes.

- [ ] **Step 1: Write the failing Port package test before changing bytes.** Assert:

```python
EXPECTED_ASSETS = {
    "assets/primary.png": "6d345c8dd4bb9970b9b58a0800bbf340119cc74cc11028c9867551cc9a6a5cd0",
    "assets/back.png": "39223f41fd3a0c77bea2c7d04e3567475e6b418eab52a25f519fa627107c258e",
    "assets/side.png": "cf1fe06bef3c374fd980d1168cf0279e885bc260401df914579c025e1e55e7ad",
}
EXPECTED_PRESENTATIONS = {
    "primary": (None, "assets/primary.png", False, True),
    "front-inverted": ("primary", "assets/primary.png", True, False),
    "cord-option-4-20mm-incut": ("primary", "assets/primary.png", True, False),
    "back": (None, "assets/back.png", False, True),
    "back-inverted": ("back", "assets/back.png", True, False),
    "side": (None, "assets/side.png", False, True),
}
EXPECTED_HOLDS_SHA256 = "c9ed1d63504559f02e33a17527ee028ac077767d57b9c44e2293e78bd515bb68"
```

For each canonical, assert exact `directTwoAnchor` keys and validator acceptance. For each alias, assert no local `cordRig`, the expected shared path/source/inversion, and an explicit anchor. Assert exactly three actual/declared paths, 1400 × 1400 RGBA, transparency/corners/content, and the sorted/minified holds hash.

- [ ] **Step 2: Verify red on current Port data.**

Run: `rtk python3 -m pytest Tools/HangboardPackages/tests/test_frictitious_port_a_board_dynamic_cord.py -q`

Expected: FAIL because current assets/hashes/paths are six baked-cord files and no rig exists.

- [ ] **Step 3: Prepare an owned, recoverable candidate and exact historical assets.** Create `.context/joyful-donkey-port-dynamic-cord/OWNERSHIP.md` with `apply_patch`, immediately recording owner `joyful-donkey`, the exact candidate checkout path, source commit `e12e7f66`, the three asset targets, and later the exact Workbench process identifier. Then run:

```bash
owner_root="$PWD/.context/joyful-donkey-port-dynamic-cord"
candidate_checkout="$owner_root/candidate-checkout"
rtk mkdir -p "$owner_root"
rtk git worktree add --detach "$candidate_checkout" HEAD
rtk git -C "$candidate_checkout" restore --source=e12e7f66 -- \
  Hangboards/frictitious-port-a-board/assets/primary.png \
  Hangboards/frictitious-port-a-board/assets/back.png \
  Hangboards/frictitious-port-a-board/assets/side.png
rtk shasum -a 256 \
  "$candidate_checkout/Hangboards/frictitious-port-a-board/assets/primary.png" \
  "$candidate_checkout/Hangboards/frictitious-port-a-board/assets/back.png" \
  "$candidate_checkout/Hangboards/frictitious-port-a-board/assets/side.png"
rtk file \
  "$candidate_checkout/Hangboards/frictitious-port-a-board/assets/primary.png" \
  "$candidate_checkout/Hangboards/frictitious-port-a-board/assets/back.png" \
  "$candidate_checkout/Hangboards/frictitious-port-a-board/assets/side.png"
```

Expected: the three exact hashes from Global Constraints and `1400 x 1400, 8-bit/color RGBA`. Never process the restored images. Install an exit trap that closes the exact locally built Workbench app/process, runs `rtk git worktree remove --force "$candidate_checkout"`, runs `rtk git worktree prune`, and verifies `rtk test ! -e "$candidate_checkout"`; the trap must refuse to act if either path differs from the recorded absolute owner path.

- [ ] **Step 4: Have the operator author evidence-backed values in the local Workbench.** Build the generated browser bundle and packaged macOS Workbench under the owned root:

```bash
owner_root="$PWD/.context/joyful-donkey-port-dynamic-cord"
candidate_checkout="$owner_root/candidate-checkout"
workbench_build="$owner_root/workbench-build"
workbench_python="$workbench_build/venv/bin/python"
rtk mkdir -p "$workbench_build"
rtk python3 -m venv "$workbench_build/venv"
rtk "$workbench_python" -m pip install -e 'Tools/HangboardWorkbench[dev]'
rtk npm --prefix Tools/HangboardWorkbench ci
rtk npm --prefix Tools/HangboardWorkbench run check:bundle
commit_sha=$(rtk git rev-parse HEAD)
rtk "$workbench_python" Tools/HangboardWorkbench/packaging/build.py \
  --commit "$commit_sha" \
  --dist-dir "$workbench_build/runtime-dist" \
  --work-dir "$workbench_build/runtime-work"
rtk swift build -c release --arch arm64 --package-path Tools/HangboardWorkbench/macos
shell_bin_dir=$(rtk swift build -c release --arch arm64 \
  --package-path Tools/HangboardWorkbench/macos --show-bin-path)
rtk "$workbench_python" Tools/HangboardWorkbench/packaging/macos_app.py \
  --shell "$shell_bin_dir/HangboardWorkbench" \
  --runtime-dir "$workbench_build/runtime-dist/hangboard-workbench" \
  --output "$workbench_build/Hangboard Workbench.app" \
  --version 1
rtk open "$workbench_build/Hangboard Workbench.app"
```

Choose `$candidate_checkout` as the app's local repository, record the app/process identity in `OWNERSHIP.md`, and use the Task 8 canonical inspector. This supported local-checkout authoring path starts no HTTP server. The operator deliberately selects, for each canonical face, the two real eyelet centers in declared order, a world-up support center, cord color, width, and loop radius; then selects each inverted alias and deliberately sets its rotation anchor. Use only these cited sources and the exact restored raster:

- current official product page: `https://frictitiousclimbing.com/products/the-port-a-board-portable-and-mountable-portable-hangboard`
- official front: `https://frictitiousclimbing.com/cdn/shop/files/PAB-Front.jpg?v=1780418977&width=3840`
- official back: `https://frictitiousclimbing.com/cdn/shop/files/PAB-Back.jpg?v=1780418977&width=3840`
- official side: `https://frictitiousclimbing.com/cdn/shop/files/PAB-Side.jpg?v=1780418977&width=3840`
- manufacturer manual mirror for option semantics: `https://manuals.plus/m/5cffc637e35befbac3738553e529f0eb508e575af7073cf198b9592e35a4a5c0`

The operator must explicitly record every chosen numeric/color value, source URL, visible feature used, and review timestamp in the new audit. If the evidence cannot support a value or any restored asset gate fails, stop and request user review; do not infer from holds or pixels. The option-4 alias uses the exact front inverted face/orientation/rig and receives no unique route.

- [ ] **Step 5: Validate the complete candidate before deleting tracked redundant assets.** At the top of the new Port test, resolve the package root exactly as `Path(os.environ["HANGTEN_PORT_PACKAGE_ROOT"])` when that variable exists, otherwise `REPOSITORY_ROOT / "Hangboards/frictitious-port-a-board"`. Candidate `board.json` must retain all names and hold JSON while declaring three unique paths. Remove only the candidate's redundant files, then run:

```bash
candidate_checkout="$PWD/.context/joyful-donkey-port-dynamic-cord/candidate-checkout"
rtk git -C "$candidate_checkout" rm -- \
  Hangboards/frictitious-port-a-board/assets/front-inverted.png \
  Hangboards/frictitious-port-a-board/assets/back-inverted.png \
  Hangboards/frictitious-port-a-board/assets/cord-option-4-20mm-incut.png
rtk env HANGTEN_PORT_PACKAGE_ROOT="$candidate_checkout/Hangboards/frictitious-port-a-board" \
  python3 -m pytest Tools/HangboardPackages/tests/test_frictitious_port_a_board_dynamic_cord.py -q
rtk scripts/hangboard-packages.sh validate --root "$candidate_checkout/Hangboards" --final-inventory
rtk python3 -c 'from pathlib import Path; import sys; sys.path.insert(0,"Tools/HangboardWorkbench"); from board_package import load_board_package; load_board_package(Path(".context/joyful-donkey-port-dynamic-cord/candidate-checkout/Hangboards/frictitious-port-a-board"))'
```

Expected: PASS. Do not promote a failing candidate.

- [ ] **Step 6: Promote exact candidate data and prove hold preservation.** Use `rtk git restore --source=e12e7f66 --` with the three exact tracked canonical paths, inspect the candidate-versus-tracked presentation diff, and use `apply_patch` to transcribe only those presentation/rig changes into tracked `board.json`. Use `rtk git rm` on the three exact redundant files. Run the Port test against the repository. Recompute the holds hash with the exact Python encoding from Global Constraints and require the full value `c9ed1d63504559f02e33a17527ee028ac077767d57b9c44e2293e78bd515bb68`.

- [ ] **Step 7: Refactor the source audit and authoring docs.** Keep all package-specific evidence in the audit and all reusable rules in the two READMEs; do not duplicate Port constants into generic documentation or implementation. The audit must contain: the approved spec path; all five URLs above; historical commit plus exact hashes/dimensions/color type/alpha checks; one table row per canonical rig with the operator's exact values/evidence; one row per alias with exact source/path/anchor; the unchanged-holds hash; an explicit statement that attachment/anchor values were manually authored and no detection/segmentation/registration/vectorization/cropping occurred; no-cord original-resolution human result; automated commands/results; and pending final app/Workbench gallery slots. Update both READMEs with the schema, `loopRadius >= 2 * cordWidth`, canonical ownership, shared paths, manual authoring, alias read-only preview, RGBA gates, and legacy fallback.

- [ ] **Step 8: Verify green and commit the package/evidence atomically.**

Run:

```bash
rtk python3 -m pytest Tools/HangboardPackages/tests/test_frictitious_port_a_board_dynamic_cord.py -q
rtk scripts/hangboard-packages.sh validate --root Hangboards --final-inventory
rtk python3 -m pytest Tools/HangboardWorkbench/tests/test_board_package.py Tools/HangboardWorkbench/tests/test_server.py -q
rtk git diff --check
```

Expected: PASS, exactly three Port assets, exact hashes, six presentations, three canonical rigs, no alias rig, and unchanged holds.

```bash
rtk git add Hangboards/frictitious-port-a-board Tools/HangboardPackages/tests/test_frictitious_port_a_board_dynamic_cord.py Tools/HangboardPackages/README.md Tools/HangboardWorkbench/README.md docs/source-audits/2026-09-03-port-dynamic-cord-prototype.md
rtk git commit -m "feat: opt Port-A-Board into dynamic cords"
```

- [ ] **Step 9: Clean Task 10 resources before review handoff.** Close the exact owned Workbench app/process, remove the candidate with `rtk git worktree remove --force "$candidate_checkout"`, prune its worktree registration, then remove only the recorded `$owner_root/workbench-build` and `OWNERSHIP.md`. Remove `$owner_root` after confirming it contains nothing else. Verify the Workbench PID is dead, `rtk test ! -e "$candidate_checkout"`, `rtk test ! -e "$owner_root"`, and `rtk git worktree list` has no candidate entry. Do not leave these resources for Task 11; its fresh subagent recreates its own acceptance resources.

### Task 11: Prove Package, Interaction, Accessibility, and Visual Acceptance

**Files:**
- Create: `HangTenUITests/PortDynamicCordUITests.swift`
- Modify: `HangTenTests/BoardPresentationArtworkTests.swift`
- Modify: `HangTenTests/BoardSourceBoundaryTests.swift`
- Modify: `Tools/HangboardWorkbench/tests/react-editor.test.tsx`
- Modify: `Tools/HangboardPackages/tests/test_frictitious_port_a_board_dynamic_cord.py`
- Modify: `docs/source-audits/2026-09-03-port-dynamic-cord-prototype.md`
- Modify: `HangTen.xcodeproj/project.pbxproj`

**Interfaces:**
- Consumes: completed generic stack, operator-recorded Port probes, `HANGTEN_REVIEW_BOARD_PICKER=1`, and the spec's human approval gate.
- Produces: final automated gates, six-presentation × two-size app/Workbench gallery, interaction/accessibility evidence, user approval record, and no phase-two changes.

- [ ] **Step 1: Write failing end-to-end assertions.** Add test cases:

```swift
func testAllPortPresentationsResolveOneRiggedArtworkWithExpectedProjection()
func testPortSourceAndAliasUseOneAffineForImageHoldMarkerAndAttachments()
func testNonRigCanonicalAndAliasRenderThroughLegacyBranch()
```

In the UI test class add `testPortCordIsDecorativeAndHoldRemainsHittableThroughStrand` and `testPortAllSixPresentationsCaptureCompleteWorldUpSupport`. Search `Port-A-Board`, open `train.boardDetails`, select all six exact picker labels, assert the map and a real hold element are hittable, tap the operator-recorded strand-only normalized map coordinate and assert selected-hold state does not change, then tap the operator-recorded under-strand hold and assert the identifier `"boardDetail.selectedHold.\(operatorHoldID)"` appears. Assert no descendant with a cord/support accessibility identifier or label exists and capture named screenshots.

In React, repeat the strand-only/hold event dispatch with an opted-in fixture and assert no extra role/name is exposed. Extend the Port Python test to cross-check every audit table value against `board.json` so documentation cannot drift.

- [ ] **Step 2: Verify red before final test wiring.**

Run:

```bash
rtk xcodebuild test -project HangTen.xcodeproj -scheme HangTen -destination 'platform=iOS Simulator,name=iPhone 16' -only-testing:HangTenTests/BoardPresentationArtworkTests
rtk npm --prefix Tools/HangboardWorkbench run test:react
rtk python3 -m pytest Tools/HangboardPackages/tests/test_frictitious_port_a_board_dynamic_cord.py -q
```

Expected: FAIL for missing final probe helpers/audit cross-checks; UI test must compile after its project reference is added but is not yet run.

- [ ] **Step 3: Add the minimal deterministic probe support.** Read the exact under-strand hold ID and strand-only map offset from the operator audit written in Task 10; transcribe them into the package-specific UI test only, never runtime/tool code. Set `app.launchEnvironment["HANGTEN_REVIEW_BOARD_PICKER"] = "1"` before launch. Consume Task 9's `BoardPresentationArtworkResolution.layerOrder` (`[.image, .cord]` for rigged and `[.legacyImage]` for non-rig) so unit tests assert layering without private view inspection. Keep the visible hold path the sole tap/accessibility shape.

- [ ] **Step 4: Run all focused automated gates.**

```bash
rtk python3 -m pytest Tools/HangboardPackages/tests/test_cord_rig.py Tools/HangboardPackages/tests/test_board_catalog.py Tools/HangboardPackages/tests/test_frictitious_port_a_board_dynamic_cord.py -q
rtk python3 -m pytest Tools/HangboardWorkbench/tests/test_cord_rig.py Tools/HangboardWorkbench/tests/test_board_package.py Tools/HangboardWorkbench/tests/test_server.py -q
rtk npm --prefix Tools/HangboardWorkbench test
rtk npm --prefix Tools/HangboardWorkbench run check:bundle
rtk xcodebuild test -project HangTen.xcodeproj -scheme HangTen -destination 'platform=iOS Simulator,name=iPhone 16' \
  -only-testing:HangTenTests/BoardCordRigGeometryTests \
  -only-testing:HangTenTests/BoardPackageStoreTests \
  -only-testing:HangTenTests/BoardPackageWriterTests \
  -only-testing:HangTenTests/BoardPresentationArtworkTests \
  -only-testing:HangTenTests/BoardSourceBoundaryTests
rtk xcodebuild test -project HangTen.xcodeproj -scheme HangTen -destination 'platform=iOS Simulator,name=iPhone 16' -only-testing:HangTenUITests/PortDynamicCordUITests
```

Expected: all PASS. UI screenshots show complete support and selected highlights; taps prove a strand-only point does nothing and a covered hold remains selectable; the accessibility tree has no cord/support element.

- [ ] **Step 5: Run full regression gates.**

```bash
rtk python3 -m pytest Tools/HangboardPackages/tests -q
rtk scripts/hangboard-packages.sh validate --root Hangboards --final-inventory
rtk scripts/hangboard-packages.sh status --root Hangboards
rtk python3 -m pytest Tools/HangboardWorkbench/tests -q
rtk npm --prefix Tools/HangboardWorkbench test
rtk xcodebuild test -project HangTen.xcodeproj -scheme HangTen -destination 'platform=iOS Simulator,name=iPhone 16'
rtk xcodebuild build-for-testing -project HangTen.xcodeproj -scheme HangTen -destination 'generic/platform=iOS Simulator'
rtk ./scripts/verify-board-source-boundary-manifest.sh
rtk git diff --check
```

Expected: all PASS. Then run:

```bash
merge_base=$(rtk git merge-base HEAD origin/main)
rtk git diff --name-only "$merge_base"..HEAD -- Hangboards
rtk rg -n 'frictitious\.port-a-board|frictitious-port-a-board|Port-A-Board' \
  HangTen Tools/HangboardPackages/src Tools/HangboardWorkbench \
  --glob '!**/tests/**' --glob '!**/README.md'
```

The first command names only `Hangboards/frictitious-port-a-board/*`; the second returns no production matches.

- [ ] **Step 6: Capture the human visual gallery at both sizes in both surfaces.** Create `.context/joyful-donkey-port-dynamic-cord-acceptance/OWNERSHIP.md` with owner `joyful-donkey`, install the same exact-path/PID cleanup trap as Task 10, and store generated captures under its `gallery/{app,workbench}/{compact,large}/` directories. Use the iOS UI test's `XCTAttachment` screenshots for the app. Rebuild a fresh owned packaged local Workbench app with Task 10 Step 4's commands, changing only `owner_root` to `$PWD/.context/joyful-donkey-port-dynamic-cord-acceptance`; open the repository root as its local checkout and resize each surface to the exact compact/large dimensions recorded in the audit before capture. No HTTP server is needed for this workflow. If an implementation subagent nevertheless starts any HTTP server on port `4173`, it must simultaneously run `/Users/asherlc/bin/paseo-quick-tunnel 4173`, record/clean both exact PIDs, and disclose only the emitted `https://…trycloudflare.com` URL. Capture Front Upright, Front Inverted, Cord Option 4 — 20 mm In-cut, Back Upright, Back Inverted, and Pinch Side with one real hold selected for each physical face. This yields 24 labeled captures grouped into six presentation rows.

At original resolution, the operator records pass/fail for unchanged face pixels below the vector layer, hold/highlight/marker/hit-target alignment, endpoint centering, straight strands, complete uncropped loop/knot, transparent surroundings, no lower support, no generated/erased board detail, and for aliases the exact affine transform with world-up support. Record device/simulator, map pixel size, Workbench viewport, capture paths/hashes, and decisions in the audit.

- [ ] **Step 7: Stop for the spec-required user approval.** Present the six-row gallery and audit results. Do not mark phase one complete, commit an approval claim, or begin phase two until the user explicitly approves all six presentations. If rejected, keep the implementation scoped to this phase-one branch and route exact visual findings back through the task review/fix loop; do not alter restored raster bytes or hold JSON.

- [ ] **Step 8: Refactor, record approval, rerun impacted gates, and commit.** After explicit approval, consolidate only duplicated test probe/gallery helpers without changing their recorded coordinates or assertions, record reviewer/date/decision in the audit, rerun the UI test, Port package test, and `git diff --check`, then commit only final test/audit wiring:

```bash
rtk git add HangTenUITests/PortDynamicCordUITests.swift HangTenTests/BoardPresentationArtworkTests.swift HangTenTests/BoardSourceBoundaryTests.swift Tools/HangboardWorkbench/tests/react-editor.test.tsx Tools/HangboardPackages/tests/test_frictitious_port_a_board_dynamic_cord.py docs/source-audits/2026-09-03-port-dynamic-cord-prototype.md HangTen.xcodeproj/project.pbxproj
rtk git commit -m "test: verify Port dynamic cord prototype"
```

- [ ] **Step 9: Final whole-branch review, resource cleanup, and push.** The controller uses the subagent-driven-development final review package, dispatches the required broad reviewer, resolves findings through the skill's single final fix wave, then closes the exact acceptance Workbench process, removes only `.context/joyful-donkey-port-dynamic-cord-acceptance`, and verifies its PID is dead and its absolute recorded root is absent. Verify no Task 10 candidate/worktree remains, then push the current branch:

```bash
rtk git status --short
rtk git log --oneline --decorate -11
rtk git push origin HEAD
```

Expected: clean tracked worktree, no owned candidate/build/gallery/tunnel/server resource remains, every task commit is present, and the configured remote reports the current branch up to date.
