# Port-A-Board Dynamic Cord Vertical-Slice Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Ship one narrow production proof in which the Port-A-Board back face and its inverted alias share the exact cord-free back image and render the visually approved, world-up dynamic cord over a transparent `1200 × 1464` scene.

**Architecture:** A canonical presentation may own a generic `directTwoAnchor` rig containing canonical scene, source-frame, inner-face-frame, attachment, pull-point, and eyelet-radius data. The selected presentation supplies a 0° or 180° two-dimensional clock-face transform for the face, holds, markers, attachments, and eyelet image fragments; support geometry remains world-up, and projected endpoints are paired by screen x. Presentations without a resolved rig retain the existing selected-asset/full-map path.

**Tech Stack:** Swift 5, SwiftUI/UIKit on iOS 17+, XCTest, Python 3.11+ with pytest, canonical JSON board packages.

**Spec:** `docs/superpowers/specs/2026-09-03-port-dynamic-cord-prototype-design.md`

## Global Constraints

- This plan supersedes the previous eleven-task plan. Do not execute any task from the superseded revision.
- Implement only `back` and `back-inverted` for `frictitious.port-a-board`; leave its other four presentations and every non-rig board unchanged.
- Rotate in the 2D image plane like a clock face. Do not use 3D rotation, perspective, skew, an x-axis flip, or a barber-pole transform.
- The canonical transparent scene is `1200 × 1464` (`50 / 61` aspect ratio). Its `sourceFrame` is `(0, 214, 1200, 1250)` and `innerFaceFrame`, relative to the source frame, is `(-100, -10, 1400, 1400)`.
- Preserve the board's scale: the added `214` units are transparent headroom, not a rescale of the former `1200 × 1250` composition.
- Port back source coordinates are: rotation center `(600, 690)`, attachments `(203, 712)` and `(997, 712)`, pull point `(600, 71.5)`, strand exits `(578, 71.5)` and `(622, 71.5)`, and eyelet radius `34`.
- The pull-point separation is exact: `712 - 71.5 == 1.5 * (712 - 285) == 640.5`.
- Sort projected attachments by screen x, then y as a deterministic tie-break, before pairing them with the left and right strand exits. This supersedes the old declared-order rule.
- Render the approved dark braided, path-driven cord with the fixed bight/knot template and direction-aware foreground eyelet crescent from the spec. The bight/knot is a generic illustration, not a manufacturer-proven knot.
- Keep the complete stroked cord inside the scene and keep the background transparent.
- Cord and eyelet-continuity layers are decorative: `.allowsHitTesting(false)` and `.accessibilityHidden(true)`.
- Commit `e12e7f66` is the source of truth for all three `1400 × 1400` RGBA cord-free Port faces. Verify all three historical hashes, but promote only exact `assets/back.png` in this slice.
- Do not change holds, hold paths, constraints, hold metadata, training content, presentation names, product URL, or the other four Port presentation records.
- Do not delete or deduplicate any Port asset in this slice. `back-inverted` retains its declared legacy file, while rigged artwork resolves the canonical `back.png` bytes.
- Do not implement Workbench support, exhaustive invalid-fixture matrices, a full unit/UI suite, an app-review screenshot gallery, the other Port faces, additional topology cases, or catalog-wide migration before the two production renders are approved.
- A catalog audit found 19 remaining cord-attached packages across multiple topology families. Do not model them all as `directTwoAnchor`.
- Use a fresh implementation subagent and a separate review gate for each task. Push each new task/fix commit to `origin` immediately.
- Generated review output belongs under `.context/joyful-donkey-port-dynamic-cord-back-review/`; record owner `joyful-donkey` before generation. Start no HTTP server.

---

## File Map

### Runtime geometry and artwork

- Modify `HangTen/Models/TrainingModels.swift`: add the generic rig values, canonical/alias rig resolution, a general 2D clock-face affine, and an optional canonical hold rectangle.
- Create `HangTen/Models/BoardCordRigGeometry.swift`: scale canonical scene data, construct the approved paths, screen-pair endpoints, and construct eyelet crescents.
- Create `HangTen/Views/BoardPresentationArtwork.swift`: resolve legacy versus rigged artwork and render the transparent image/cord/crescent stack.
- Modify `HangTen/Views/BoardMapView.swift`: give both map sites the resolved inner face rectangle while leaving hold and marker semantics intact.
- Modify `HangTen.xcodeproj/project.pbxproj`: add the two new production files and one focused test file.
- Modify `HangTenTests/BoardSourceBoundaryTrackedPaths.txt`: include the two new handwritten production files in sorted order.

### Package loading and writing

- Modify `HangTen/Models/BoardPackageStore.swift`: decode the closed rig object, validate canonical ownership and alias inheritance, and resolve the canonical artwork URL only for a rigged presentation.
- Modify `HangTen/Models/BoardPackageWriter.swift`: decode, validate, and canonically serialize the same optional rig object.
- Modify `Tools/HangboardPackages/src/hangboard_packages/board_catalog.py`: parse the same optional object and enforce the minimal ownership/aspect contract.

### Proportional tests

- Create `HangTenTests/BoardCordRigGeometryTests.swift`: one geometry test, also capable of writing isolated review artifacts when an output directory is supplied.
- Modify `HangTenTests/BoardPackageStoreTests.swift`: add one loader/alias/legacy-branch test.
- Modify `HangTenTests/BoardPackageWriterTests.swift`: add one exact writer round-trip test.
- Modify `Tools/HangboardPackages/tests/test_board_catalog.py`: add one parser-compatibility test.

### Port data and evidence

- Modify only `back` and `back-inverted` presentation fields in `Hangboards/frictitious-port-a-board/board.json`.
- Restore `Hangboards/frictitious-port-a-board/assets/back.png` byte-for-byte from `e12e7f66`.
- Create `docs/source-audits/2026-09-03-port-dynamic-cord-back-slice.md`: record manufacturer links, all approved constants, the three historical hashes, the promoted back hash, commands, and the two human review decisions.

## Exact Interfaces

Task implementers use these names across task boundaries:

```swift
struct BoardCordPoint: Hashable {
    let x: CGFloat
    let y: CGFloat
    var cgPoint: CGPoint { CGPoint(x: x, y: y) }
}

struct BoardCordSize: Hashable {
    let width: CGFloat
    let height: CGFloat
    var cgSize: CGSize { CGSize(width: width, height: height) }
}

struct BoardCordRect: Hashable {
    let x: CGFloat
    let y: CGFloat
    let width: CGFloat
    let height: CGFloat
    var cgRect: CGRect { CGRect(x: x, y: y, width: width, height: height) }
}

enum BoardCordRig: Hashable {
    case directTwoAnchor(BoardDirectTwoAnchorCordRig)
}

struct BoardDirectTwoAnchorCordRig: Hashable {
    let sceneSize: BoardCordSize
    let sourceFrame: BoardCordRect
    let innerFaceFrame: BoardCordRect
    let attachmentPoints: [BoardCordPoint]
    let pullPoint: BoardCordPoint
    let eyeletRadius: CGFloat
}
```

`BoardPresentation` gains `let cordRig: BoardCordRig?` with initializer default
`nil`. `TrainingBoard` gains:

```swift
func canonicalPresentation(for presentation: BoardPresentation) -> BoardPresentation?
func resolvedCordRig(for presentation: BoardPresentation) -> BoardCordRig?
```

The existing projection remains source compatible and adds:

```swift
init(rotationDegrees: CGFloat, rotationAnchor: BoardGeometryRotationAnchor? = nil)
func affineTransform(in rect: CGRect) -> CGAffineTransform
```

`init(presentation:)` maps `isInverted == true` to `180` and false to `0`.
Positive angles are clockwise in the y-down canvas. Existing point/path
projection methods call this single affine.

Geometry exposes only what the renderer and one test need:

```swift
struct BoardCordStrand: Equatable {
    let start: CGPoint
    let end: CGPoint
}

struct BoardCordRigGeometry {
    let sceneRect: CGRect
    let sourceRect: CGRect
    let faceRect: CGRect
    let faceTransform: CGAffineTransform
    let projectedAttachments: [CGPoint]
    let pairedAttachments: [CGPoint]
    let strands: [BoardCordStrand]
    let supportPaths: [Path]
    let knotOverpass: Path
    let eyeletForegroundCrescents: [Path]
    let strokeBounds: CGRect

    static func make(
        rig: BoardDirectTwoAnchorCordRig,
        projection: BoardPresentationGeometryProjection,
        in canvas: CGRect
    ) -> BoardCordRigGeometry
}
```

The loader keeps `presentationImageURL(for:presentationID:)` unchanged and
adds the opt-in resolver used by artwork:

```swift
func presentationArtworkImageURL(
    for board: TrainingBoard,
    presentationID: String
) -> URL?
```

It returns the selected presentation's own URL when no rig resolves. When a
rig resolves, it returns the canonical source presentation's URL.

---

### Task 1: Add the Approved Clock-Face Geometry

**Files:**

- Modify: `HangTen/Models/TrainingModels.swift`
- Create: `HangTen/Models/BoardCordRigGeometry.swift`
- Create: `HangTenTests/BoardCordRigGeometryTests.swift`
- Modify: `HangTen.xcodeproj/project.pbxproj`
- Modify: `HangTenTests/BoardSourceBoundaryTrackedPaths.txt`

**Interfaces:**

- Produces every Swift type and geometry signature in **Exact Interfaces**.
- Does not decode package JSON or render a SwiftUI view.

- [ ] **Step 1: Add one failing geometry test.**

Create `BoardCordRigGeometryTests.swift` with one test named
`testApprovedPortGeometryUsesClockFaceProjectionAndWorldUpSupport`. Construct
the exact rig below in a private helper:

```swift
private let portBackRig = BoardDirectTwoAnchorCordRig(
    sceneSize: BoardCordSize(width: 1200, height: 1464),
    sourceFrame: BoardCordRect(x: 0, y: 214, width: 1200, height: 1250),
    innerFaceFrame: BoardCordRect(x: -100, y: -10, width: 1400, height: 1400),
    attachmentPoints: [
        BoardCordPoint(x: 203, y: 712),
        BoardCordPoint(x: 997, y: 712),
    ],
    pullPoint: BoardCordPoint(x: 600, y: 71.5),
    eyeletRadius: 34
)
```

In that single test, assert all of the following:

```swift
XCTAssertEqual(portBackRig.attachmentPoints.map(\.y).reduce(0, +) / 2 - portBackRig.pullPoint.y, 640.5)
XCTAssertEqual(640.5, 1.5 * 427)

let canvas = CGRect(x: 0, y: 0, width: 1200, height: 1464)
let ninety = BoardPresentationGeometryProjection(
    rotationDegrees: 90,
    rotationAnchor: BoardGeometryRotationAnchor(x: 0.5, y: 113.0 / 183.0)
)
let ninetyGeometry = BoardCordRigGeometry.make(
    rig: portBackRig, projection: ninety, in: canvas
)
XCTAssertEqual(ninetyGeometry.projectedAttachments[0], CGPoint(x: 578, y: 507))
XCTAssertEqual(ninetyGeometry.projectedAttachments[1], CGPoint(x: 578, y: 1301))

let inverted = BoardPresentationGeometryProjection(
    rotationDegrees: 180,
    rotationAnchor: BoardGeometryRotationAnchor(x: 0.5, y: 113.0 / 183.0)
)
let invertedGeometry = BoardCordRigGeometry.make(
    rig: portBackRig, projection: inverted, in: canvas
)
XCTAssertEqual(invertedGeometry.faceRect, CGRect(x: -100, y: 204, width: 1400, height: 1400))
XCTAssertEqual(invertedGeometry.projectedAttachments, [CGPoint(x: 997, y: 882), CGPoint(x: 203, y: 882)])
XCTAssertEqual(invertedGeometry.pairedAttachments, [CGPoint(x: 203, y: 882), CGPoint(x: 997, y: 882)])
XCTAssertEqual(invertedGeometry.strands[0].start, CGPoint(x: 578, y: 285.5))
XCTAssertEqual(invertedGeometry.strands[1].start, CGPoint(x: 622, y: 285.5))
XCTAssertTrue(canvas.contains(invertedGeometry.strokeBounds))
XCTAssertEqual(invertedGeometry.eyeletForegroundCrescents.count, 2)
```

Use `accuracy: 1e-9` helpers for point/rect comparisons affected by sine and
cosine. Also assert the support path elements are equal at 0° and 180° while
the face transform differs.

- [ ] **Step 2: Run the one test and confirm it is red.**

```bash
rtk xcodebuild test -project HangTen.xcodeproj -scheme HangTen -destination 'platform=iOS Simulator,name=iPhone 16' -only-testing:HangTenTests/BoardCordRigGeometryTests/testApprovedPortGeometryUsesClockFaceProjectionAndWorldUpSupport
```

Expected: compile failure because the rig and geometry types do not exist.

- [ ] **Step 3: Add the minimal model and affine.**

Add the exact value types and rig enum above to `TrainingModels.swift`. Add
optional canonical ownership to `BoardPresentation`, the two `TrainingBoard`
resolution methods, and the general `rotationDegrees` initializer. Construct
the affine by translating to the resolved scene pivot, rotating by
`rotationDegrees * .pi / 180`, and translating back. Keep the existing
`isInverted` initializer and all current call sites source compatible.

Extend `BoardHoldPathShape` with optional `canonicalRect: CGRect? = nil`.
Build each canonical hold path in `canonicalRect ?? rect`, then project it in
the outer `rect`. This is inert for every existing caller.

- [ ] **Step 4: Implement only the approved deterministic geometry.**

In `BoardCordRigGeometry.swift`:

1. aspect-fit `sceneSize` into the supplied canvas;
2. map `sourceFrame` into the scene;
3. map `innerFaceFrame` relative to the source frame without rescaling it
   independently;
4. add the source-frame origin to attachment and pull-point coordinates;
5. apply only the supplied clock-face affine to the face and attachments;
6. derive exits at pull x `-22` and `+22`;
7. sort projected endpoints by `(x, y)` and create two straight strands;
8. transcribe the exact bight/knot commands from the spec relative to the pull
   point;
9. compute stroke bounds using the widest `35`-unit shadow plus its offset and
   blur; and
10. construct each major-arc crescent with `r = eyeletRadius` and canonical
    chord offset `7`, directed toward its paired exit.

Scale every canonical distance once by the scene-to-canvas factor. Do not add
time, randomness, simulation state, collision behavior, or product IDs.

- [ ] **Step 5: Run the single green gate.**

Run the Step 2 command again.

Expected: PASS for canonical frames, 1.5× spacing, the 90° axis proof, the 180°
endpoint values, screen-x pairing, world-up support, complete bounds, and two
crescents.

- [ ] **Step 6: Commit and push.**

Add the two new files to the app/test targets in `project.pbxproj`, add their
production paths to the sorted boundary manifest, then run:

```bash
rtk git diff --check
rtk git add HangTen/Models/TrainingModels.swift HangTen/Models/BoardCordRigGeometry.swift HangTenTests/BoardCordRigGeometryTests.swift HangTen.xcodeproj/project.pbxproj HangTenTests/BoardSourceBoundaryTrackedPaths.txt
rtk git commit -m "feat: add dynamic cord scene geometry"
rtk git push origin HEAD
```

### Task 2: Add Minimal Loader, Writer, and Python Schema Compatibility

**Files:**

- Modify: `HangTen/Models/BoardPackageStore.swift`
- Modify: `HangTen/Models/BoardPackageWriter.swift`
- Modify: `Tools/HangboardPackages/src/hangboard_packages/board_catalog.py`
- Modify: `HangTenTests/BoardPackageStoreTests.swift`
- Modify: `HangTenTests/BoardPackageWriterTests.swift`
- Modify: `Tools/HangboardPackages/tests/test_board_catalog.py`

**Interfaces:**

- Consumes Task 1's exact rig types and canonical/alias resolvers.
- Produces the exact closed `cordRig` JSON from the spec and
  `presentationArtworkImageURL(for:presentationID:)`.

- [ ] **Step 1: Add one failing loader/alias test.**

Add
`testDirectTwoAnchorRigLoadsAndAliasUsesCanonicalArtworkWithoutChangingLegacySelection`
to `BoardPackageStoreTests.swift`. Its temporary package has:

- canonical `back` with the exact rig JSON from the spec and `assets/back.png`;
- `back-inverted` sourcing `back`, with `isInverted: true`, normalized anchor
  `{ "x": 0.5, "y": 0.6174863387978142 }`, and a distinct existing
  `assets/back-inverted.png`; and
- one non-rig `primary` presentation with `assets/primary.png`.

Assert that only `back` owns the rig, `back-inverted` resolves the same value,
`presentationArtworkImageURL` returns `back.png` for both back presentations,
and both `presentationImageURL` and `presentationArtworkImageURL` still return
`primary.png` for the non-rig presentation.

- [ ] **Step 2: Add one failing writer round-trip test.**

Add `testDirectTwoAnchorCordRigRoundTripsInCanonicalOrder` to
`BoardPackageWriterTests.swift`. Decode the spec's exact object, write it,
decode the emitted bytes again, and assert semantic equality plus idempotent
bytes. Assert key order:

```text
type, sceneSize, sourceFrame, innerFaceFrame,
attachmentPoints, pullPoint, eyeletRadius
```

- [ ] **Step 3: Add one failing Python compatibility test.**

Add `test_direct_two_anchor_cord_rig_matches_ios_vertical_slice` to
`test_board_catalog.py`. Load the same three-presentation fixture and assert
the seven closed keys and exact numeric values, canonical ownership, alias
source/aspect/anchor, and no rig on `primary`.

- [ ] **Step 4: Run only the three red gates.**

```bash
rtk xcodebuild test -project HangTen.xcodeproj -scheme HangTen -destination 'platform=iOS Simulator,name=iPhone 16' -only-testing:HangTenTests/BoardPackageStoreTests/testDirectTwoAnchorRigLoadsAndAliasUsesCanonicalArtworkWithoutChangingLegacySelection -only-testing:HangTenTests/BoardPackageWriterTests/testDirectTwoAnchorCordRigRoundTripsInCanonicalOrder
rtk python3 -m pytest Tools/HangboardPackages/tests/test_board_catalog.py::test_direct_two_anchor_cord_rig_matches_ios_vertical_slice -q
```

Expected: both commands fail because `cordRig` is not recognized.

- [ ] **Step 5: Implement the closed iOS document and resolver.**

In `BoardPackageStore.swift`, add private decodable point, size, rect, and
tagged-rig documents. `rejectUnknownKeys` allows exactly the seven keys above;
the nested values allow only their exact coordinate/dimension keys. Adapt the
document to `.directTwoAnchor` after checking:

- finite numeric values;
- positive scene, source, inner-face sizes, and eyelet radius;
- exactly two finite, distinct attachment points;
- canonical non-inverted ownership; and
- `presentation.aspectRatio == sceneSize.width / sceneSize.height` within the
  store's existing aspect tolerance.

Aliases cannot own `cordRig`; they resolve from their direct canonical source.
Do not require the transitional alias `assetPath` to equal the canonical path.
For every resolved rig, compare the presentation ratio to `sceneSize` and its
declared PNG ratio to `innerFaceFrame`; this keeps both transitional square
files valid inside the taller scene. Preserve the existing presentation-to-PNG
ratio check for non-rig presentations.
For a rigged alias, update projected-hold validation to map each canonical hold
corner through `innerFaceFrame` and `sourceFrame` before applying the scene
affine; retain the existing normalized validation path for non-rig aliases.
Add `presentationArtworkImageURL` with the exact opt-in behavior in **Exact
Interfaces**. Keep `presentationImageURL` unchanged.

In `BoardPackageWriter.swift`, add the optional rig to
`BoardEditablePresentation`, use the same minimal semantic checks, and emit the
seven keys in the stated order. Omitted rigs produce no key and retain the
existing presentation encoding.

- [ ] **Step 6: Implement the independent Python parser.**

In `board_catalog.py`, add immutable `CordPoint`, `CordSize`, `CordRect`, and
`DirectTwoAnchorCordRig` values and parse the same closed keys with the same
finite/positive/count/ownership/scene-and-inner-image-aspect checks. Add
`cord_rig: DirectTwoAnchorCordRig | None = None` to `BoardPresentation`.
Do not implement cord paths, raster inspection, Workbench transport, or
additional types in Python.

- [ ] **Step 7: Run only the three green gates.**

Run the two commands from Step 4.

Expected: one iOS loader/alias test, one iOS writer round-trip test, and one
Python compatibility test all PASS.

- [ ] **Step 8: Commit and push.**

```bash
rtk git diff --check
rtk git add HangTen/Models/BoardPackageStore.swift HangTen/Models/BoardPackageWriter.swift Tools/HangboardPackages/src/hangboard_packages/board_catalog.py HangTenTests/BoardPackageStoreTests.swift HangTenTests/BoardPackageWriterTests.swift Tools/HangboardPackages/tests/test_board_catalog.py
rtk git commit -m "feat: load and round trip dynamic cord rigs"
rtk git push origin HEAD
```

### Task 3: Render and Review the Port Back Vertical Slice

**Files:**

- Create: `HangTen/Views/BoardPresentationArtwork.swift`
- Modify: `HangTen/Views/BoardMapView.swift`
- Modify: `HangTen/Models/TrainingModels.swift`
- Modify: `HangTenTests/BoardCordRigGeometryTests.swift`
- Modify: `HangTen.xcodeproj/project.pbxproj`
- Modify: `HangTenTests/BoardSourceBoundaryTrackedPaths.txt`
- Modify: `Hangboards/frictitious-port-a-board/board.json`
- Modify: `Hangboards/frictitious-port-a-board/assets/back.png`
- Create: `docs/source-audits/2026-09-03-port-dynamic-cord-back-slice.md`

**Interfaces:**

- Consumes Task 1 geometry and Task 2 canonical artwork URL resolution.
- Produces `BoardPresentationArtwork`, the unchanged non-rig branch, and the
  two isolated transparent review images.

- [ ] **Step 1: Restore and verify the approved source bytes.**

Verify all three historical blobs without modifying the tree:

```bash
rtk proxy git show e12e7f66:Hangboards/frictitious-port-a-board/assets/primary.png | shasum -a 256
rtk proxy git show e12e7f66:Hangboards/frictitious-port-a-board/assets/back.png | shasum -a 256
rtk proxy git show e12e7f66:Hangboards/frictitious-port-a-board/assets/side.png | shasum -a 256
```

Expected, in order:

```text
6d345c8dd4bb9970b9b58a0800bbf340119cc74cc11028c9867551cc9a6a5cd0
39223f41fd3a0c77bea2c7d04e3567475e6b418eab52a25f519fa627107c258e
cf1fe06bef3c374fd980d1168cf0279e885bc260401df914579c025e1e55e7ad
```

Restore only the exact back face and confirm format/hash:

```bash
rtk git restore --source=e12e7f66 -- Hangboards/frictitious-port-a-board/assets/back.png
rtk shasum -a 256 Hangboards/frictitious-port-a-board/assets/back.png
rtk file Hangboards/frictitious-port-a-board/assets/back.png
```

Expected: the back hash above and `1400 x 1400, 8-bit/color RGBA`. Do not
process, crop, regenerate, or recompress the file.

- [ ] **Step 2: Opt in only the two back presentations.**

Use `apply_patch` on `board.json`:

- add the exact spec `cordRig` to `back`;
- change `back.aspectRatio` to `0.819672131147541`;
- change `back-inverted.aspectRatio` to the same value;
- retain `back-inverted.sourcePresentationID == "back"` and
  `isInverted == true`;
- add `geometryRotationAnchor` with x `0.5` and y
  `0.6174863387978142`; and
- leave `back-inverted.assetPath == "assets/back-inverted.png"`.

Before and after the patch, calculate the canonical JSON hash of `holds` with:

```bash
rtk python3 -c 'import hashlib,json; d=json.load(open("Hangboards/frictitious-port-a-board/board.json")); b=json.dumps(d["holds"],sort_keys=True,separators=(",",":"),ensure_ascii=False).encode(); print(hashlib.sha256(b).hexdigest())'
```

Require the same value both times. Record it in the source audit. Do not touch
the other presentation objects or any asset besides `back.png`.

- [ ] **Step 3: Implement the shared artwork with the approved cord style.**

Create `BoardPresentationArtwork.swift` with:

```swift
struct BoardPresentationArtwork: View {
    let board: TrainingBoard
    let presentation: BoardPresentation
    let projection: BoardPresentationGeometryProjection
    let canvasSize: CGSize
}
```

For no resolved rig, return the existing
`BoardPresentationImage(board:presentationID:)` directly with the selected ID.
For `.directTwoAnchor`:

1. load the URL from `presentationArtworkImageURL` once;
2. draw it in the geometry's `faceRect` and apply only `faceTransform`;
3. draw the bight, knot, and two strands with round caps/joins using the six
   exact canonical-scale passes in the spec;
4. clip the diagonal braid to the stroked paths so no raster cord asset is
   introduced;
5. redraw the same transformed face image through each direction-aware
   crescent above the cord; and
6. apply `.allowsHitTesting(false)` and `.accessibilityHidden(true)` to the
   entire decorative overlay.

Use `Canvas` for the path/stroke/clip work. Scale widths, dashes, blur, pattern,
and offsets by the geometry's single scene scale. Add no background fill,
animation, or gesture.

- [ ] **Step 4: Give holds and markers the same inner face frame.**

In both `BoardMapView` map sites, resolve geometry once for a rigged
presentation. Pass its `faceRect` as `BoardHoldPathShape.canonicalRect`; keep
the outer scene rectangle as the projection rectangle. For detail markers,
derive the canonical marker center in `faceRect`, then apply the same
projection in the outer scene rectangle. The artwork stays below existing
holds and markers.

When no rig resolves, pass no canonical override, keep the existing full
rectangle, selected presentation image, holds, markers, hit shapes, and
accessibility behavior.

- [ ] **Step 5: Add optional isolated artifact output to the one geometry test.**

Without adding another test method, extend
`testApprovedPortGeometryUsesClockFaceProjectionAndWorldUpSupport`: when
`HANGTEN_CORD_REVIEW_DIR` is present, load the real Port package, render only
`BoardPresentationArtwork` for `back` and `back-inverted` through
`ImageRenderer` at exactly `1200 × 1464` points and scale `1`, and write
`back.png` and `back-inverted.png` to that exact directory. Assert both PNGs
decode as `1200 × 1464` and have transparent corner pixels. With the variable
absent, retain only the Task 1 geometry assertions.

- [ ] **Step 6: Write the evidence audit.**

Create `docs/source-audits/2026-09-03-port-dynamic-cord-back-slice.md` with:

- the spec path and four manufacturer URLs;
- the explicit generic-knot caveat;
- all scene/frame/pivot/attachment/pull/exit/radius values;
- the exact 1.5× equation;
- all three historical hashes and dimensions;
- the promoted back hash and unchanged-holds hash;
- an explicit statement that no image detection, vectorization, cropping, or
  regeneration occurred;
- the focused command results below; and
- separate pending decision rows for `back` and `back-inverted`, filled only
  after the user reviews each isolated output.

- [ ] **Step 7: Run the proportional automated gates.**

Run only the already-defined focused tests and focused build:

```bash
rtk xcodebuild test -project HangTen.xcodeproj -scheme HangTen -destination 'platform=iOS Simulator,name=iPhone 16' -only-testing:HangTenTests/BoardCordRigGeometryTests/testApprovedPortGeometryUsesClockFaceProjectionAndWorldUpSupport -only-testing:HangTenTests/BoardPackageStoreTests/testDirectTwoAnchorRigLoadsAndAliasUsesCanonicalArtworkWithoutChangingLegacySelection -only-testing:HangTenTests/BoardPackageWriterTests/testDirectTwoAnchorCordRigRoundTripsInCanonicalOrder
rtk python3 -m pytest Tools/HangboardPackages/tests/test_board_catalog.py::test_direct_two_anchor_cord_rig_matches_ios_vertical_slice -q
rtk xcodebuild build -project HangTen.xcodeproj -scheme HangTen -destination 'generic/platform=iOS Simulator'
```

Expected: the one geometry test, one loader/alias test, one writer round-trip,
one Python parser test, and focused build all PASS. Do not expand to the full
test suites before visual review.

- [ ] **Step 8: Generate the two isolated transparent board canvases.**

Create
`.context/joyful-donkey-port-dynamic-cord-back-review/OWNERSHIP.md` with
`apply_patch` before running the renderer. Record owner `joyful-donkey`, the
absolute directory, the two intended PNG paths, and that no server/process is
owned. Then run:

```bash
rtk env HANGTEN_CORD_REVIEW_DIR="$PWD/.context/joyful-donkey-port-dynamic-cord-back-review" xcodebuild test -project HangTen.xcodeproj -scheme HangTen -destination 'platform=iOS Simulator,name=iPhone 16' -only-testing:HangTenTests/BoardCordRigGeometryTests/testApprovedPortGeometryUsesClockFaceProjectionAndWorldUpSupport
rtk file .context/joyful-donkey-port-dynamic-cord-back-review/back.png .context/joyful-donkey-port-dynamic-cord-back-review/back-inverted.png
rtk shasum -a 256 .context/joyful-donkey-port-dynamic-cord-back-review/back.png .context/joyful-donkey-port-dynamic-cord-back-review/back-inverted.png
```

Expected: two distinct `1200 × 1464` RGBA PNGs with transparent corners,
complete uncropped upper cords, unchanged board scale, continuous eyelet
entries, and gravity pulling toward the top of each scene.

- [ ] **Step 9: Commit and push the vertical slice.**

Add the new production view to the app target and sorted boundary manifest.
Do not add `.context` artifacts. Run:

```bash
rtk git diff --check
rtk git add HangTen/Views/BoardPresentationArtwork.swift HangTen/Views/BoardMapView.swift HangTen/Models/TrainingModels.swift HangTenTests/BoardCordRigGeometryTests.swift HangTen.xcodeproj/project.pbxproj HangTenTests/BoardSourceBoundaryTrackedPaths.txt Hangboards/frictitious-port-a-board/board.json Hangboards/frictitious-port-a-board/assets/back.png docs/source-audits/2026-09-03-port-dynamic-cord-back-slice.md
rtk git commit -m "feat: render Port back with dynamic cords"
rtk git push origin HEAD
```

- [ ] **Step 10: Stop for one-by-one production visual review.**

Show only the isolated `back.png` first, with the official product link. After
an explicit decision, record it in the audit and show only
`back-inverted.png`, again with the product link. Do not show app chrome or a
contact sheet. If either is rejected, keep fixes inside this task and repeat
the relevant focused gate/output/commit/push cycle.

After both are approved, remove only the recorded `.context` review directory,
verify it is absent, and record the approval in a small audit-only commit that
is pushed immediately. The next plan may add Workbench parity and migrate the
remaining Port faces; it must not silently begin the 19-package catalog
migration.
