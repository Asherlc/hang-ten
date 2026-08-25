# Beastmaker Bilateral Highlight Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Highlight both mirrored outer lower Beastmaker 2000 edges for the 29 mm open-hand cue.

**Architecture:** The board-preview renderer already receives all resolved IDs. Correct the physical inventory so the target resolver recognizes the mirrored right outer lower contact as an edge, then preserve a bounded bilateral selection when a metadata-light edge fallback has one candidate on each board half. Protect the app-store result with a regression test. Preserve all canonical geometry.

**Tech Stack:** Swift/XCTest, JSON board packages, Hang Ten package validator.

**Spec:** User report and screenshot (2026-08-25); [Beastmaker 2000 Series](https://www.beastmaker.co.uk/products/beastmaker-2000-series), which lists plural “Big and little edges.”

## Global Constraints

- Change only source-backed physical inventory metadata; do not alter geometry.
- `front-lower-9` is the exact mirror of `front-lower-1` in the existing reviewed board geometry.
- Do not add unsupported dimensions, capacity, feature, or coaching metadata.
- Preserve the existing resolver and board-preview API.

---

### Task 1: Correct the mirrored outer lower edge inventory

**Files:**
- Modify: `Hangboards/beastmaker-2000/board.json:2309`
- Modify: `docs/source-audits/2026-08-25-all-board-hold-audit.md:48`
- Test: `HangTenTests/BoardTargetSubstitutionTests.swift`

**Interfaces:**
- Consumes: `AppStore.holdIDs(for:on:) -> Set<String>` and the bundled `beastmaker-2000` board.
- Produces: a 29 mm (`.largeEdge`) open-hand step resolving both `front-lower-1` and `front-lower-9`.

- [ ] **Step 1: Write the failing test**

```swift
func testBeastmaker2000OpenHandLargeEdgeHighlightsMirroredOuterEdges() throws {
    let board = try XCTUnwrap(BoardCatalog.board(for: "beastmaker-2000"))
    let suiteName = "BoardTargetSubstitutionTests-\(UUID().uuidString)"
    let defaults = try XCTUnwrap(UserDefaults(suiteName: suiteName))
    defer { defaults.removePersistentDomain(forName: suiteName) }
    let store = AppStore(defaults: defaults)
    let step = WorkoutStep(
        id: "open-hand-29-mm",
        number: 1,
        title: "29 mm open edge",
        instruction: "",
        accessory: "",
        duration: 7,
        phase: .hang,
        targets: [.feature(.largeEdge)],
        gripType: .openHand
    )
    XCTAssertEqual(store.holdIDs(for: step, on: board), ["front-lower-1", "front-lower-9"])
}
```

The production change this test must catch is returning only `front-lower-1` because its mirrored physical edge is categorized as a pocket.

- [ ] **Step 2: Run the focused test to verify it fails**

Run: `rtk xcodebuild test -project HangTen.xcodeproj -scheme HangTen -destination 'platform=iOS Simulator,name=iPhone 16' -only-testing:HangTenTests/BoardTargetSubstitutionTests/testBeastmaker2000OpenHandLargeEdgeHighlightsMirroredOuterEdges`

Expected: FAIL because the resolver returns only `front-lower-1`.

- [ ] **Step 3: Apply the minimal inventory correction**

Change only `front-lower-9.kind` from `pocket` to `edge`. Update the Beastmaker 2000 row in the current all-board audit from `edge 1; pocket 21; sloper 5` to `edge 2; pocket 20; sloper 5`, and add a brief mapping note that the direct geometry mirror and manufacturer’s plural edge inventory support the mirrored outer-edge classification. Do not change path, frame, capacity, size, feature, or presentation fields.

- [ ] **Step 4: Run focused and package validations**

Run: `rtk xcodebuild test -project HangTen.xcodeproj -scheme HangTen -destination 'platform=iOS Simulator,name=iPhone 16' -only-testing:HangTenTests/BoardTargetSubstitutionTests`

Run: `rtk scripts/hangboard-packages.sh validate --root Hangboards --final-inventory`

Run: `rtk scripts/hangboard-packages.sh status --root Hangboards`

Expected: all commands exit 0.

- [ ] **Step 5: Commit**

```bash
git add Hangboards/beastmaker-2000/board.json docs/source-audits/2026-08-25-all-board-hold-audit.md HangTenTests/BoardTargetSubstitutionTests.swift docs/superpowers/plans/2026-08-25-beastmaker-bilateral-highlight.md
git commit -m "Fix Beastmaker bilateral edge highlighting"
```

### Task 2: Preserve a bounded two-hand fallback for paired edges

**Files:**
- Modify: `HangTen/Models/WorkoutActivityRecording.swift:294-312`
- Test: `HangTenTests/BoardTargetSubstitutionTests.swift`

**Interfaces:**
- Consumes: the metadata-light same-kind candidate list in `BoardTargetResolver.sameKindOrGroup(_:target:among:)`.
- Produces: at most one eligible edge from each half of the board for an untagged edge fallback; leaves a one-sided or positionless candidate set as one representative.

- [ ] **Step 1: Write the failing resolver test**

```swift
func testMetadataLightEdgeFallbackSelectsOneEdgePerBoardHalf() {
    let board = board(holds: [
        hold(id: "left-edge", x: 0.1),
        hold(id: "left-extra", x: 0.3),
        hold(id: "right-edge", x: 0.8)
    ])

    let result = BoardTargetResolver.substituteHoldIDs(
        for: .feature(.largeEdge),
        on: board
    )

    XCTAssertEqual(result, ["left-edge", "right-edge"])
}
```

The production change this test must catch is choosing only one representative after the package correctly identifies a left/right pair of physical edges.

- [ ] **Step 2: Run the focused test to verify it fails**

Run: `rtk xcodebuild test -project HangTen.xcodeproj -scheme HangTen -destination 'platform=iOS Simulator,name=iPhone 16' -only-testing:HangTenTests/BoardTargetSubstitutionTests/testMetadataLightEdgeFallbackSelectsOneEdgePerBoardHalf`

Expected: FAIL because the resolver returns only `left-edge`.

- [ ] **Step 3: Apply the minimal resolver correction**

When the same-kind edge fallback has eligible holds on both sides of the board, return the first hold from each side in board order. Keep the existing depth-ranking behavior, cap the output at one hold per side, and retain the existing one-representative behavior when no right-side hold exists. Generalize the helper name and pocket-specific comment so the same tested one-per-side behavior serves both pockets and untagged edges.

- [ ] **Step 4: Run resolver and package validations**

Run: `rtk xcodebuild test -project HangTen.xcodeproj -scheme HangTen -destination 'platform=iOS Simulator,name=iPhone 16' -only-testing:HangTenTests/BoardTargetSubstitutionTests`

Run: `rtk scripts/hangboard-packages.sh validate --root Hangboards --final-inventory`

Expected: all commands exit 0.

- [ ] **Step 5: Commit**

```bash
git add HangTen/Models/WorkoutActivityRecording.swift HangTenTests/BoardTargetSubstitutionTests.swift docs/superpowers/plans/2026-08-25-beastmaker-bilateral-highlight.md
git commit -m "Resolve paired metadata-light edges per hand"
```

### Task 3: Restore the generalized helper call and remove generated output

**Files:**
- Modify: `HangTen/Models/WorkoutActivityRecording.swift:101`
- Delete: `.superpowers/sdd/2026-08-25-beastmaker-bilateral-highlight/task-2-report.md`
- Modify: `docs/superpowers/plans/2026-08-25-beastmaker-bilateral-highlight.md`

**Interfaces:**
- Consumes: `oneHoldPerHand(from:) -> [BoardHold]`.
- Produces: all bilateral fallback branches compile against the one generalized helper.

- [ ] **Step 1: Verify the compile failure**

Run: `rtk xcodebuild build-for-testing -project HangTen.xcodeproj -scheme HangTen -destination 'generic/platform=iOS Simulator'`

Expected: FAIL with the unresolved `onePocketPerHand` call left by the helper rename.

- [ ] **Step 2: Apply the minimal correction**

Replace the stale `onePocketPerHand(from:)` call with `oneHoldPerHand(from:)`. Remove the accidentally committed SDD task report because it is generated execution output, not product documentation. Do not modify selection behavior or tests.

- [ ] **Step 3: Verify the compile and package contract**

Run: `rtk xcodebuild build-for-testing -project HangTen.xcodeproj -scheme HangTen -destination 'generic/platform=iOS Simulator'`

Run: `rtk scripts/hangboard-packages.sh validate --root Hangboards --final-inventory`

Expected: both commands exit 0.

- [ ] **Step 4: Commit**

```bash
git add HangTen/Models/WorkoutActivityRecording.swift docs/superpowers/plans/2026-08-25-beastmaker-bilateral-highlight.md
git rm .superpowers/sdd/2026-08-25-beastmaker-bilateral-highlight/task-2-report.md
git commit -m "Fix generalized bilateral hold helper"
```

### Task 4: Compile the ranked bilateral fallback binding

**Files:**
- Modify: `HangTen/Models/WorkoutActivityRecording.swift:248-251`
- Modify: `docs/superpowers/plans/2026-08-25-beastmaker-bilateral-highlight.md`

**Interfaces:**
- Consumes: `preferredSameKind.min(by:) -> BoardHold?`.
- Produces: the same optional representative used by the existing one-sided fallback, in valid Swift syntax.

- [ ] **Step 1: Verify the failing compile**

Run: `rtk xcodebuild build-for-testing -project HangTen.xcodeproj -scheme HangTen -destination 'generic/platform=iOS Simulator'`

Expected: FAIL at the `guard` binding because the `min` trailing closure is parsed as outside the guard condition.

- [ ] **Step 2: Apply the minimal syntax correction**

Bind the `min(by:)` result to a local optional before the `guard`, then unwrap that local in the `guard`. Keep the comparison closure, depth ranking, bilateral-pair branch, and test assertions identical.

- [ ] **Step 3: Verify build and package contract**

Run: `rtk xcodebuild build-for-testing -project HangTen.xcodeproj -scheme HangTen -destination 'generic/platform=iOS Simulator'`

Run: `rtk scripts/hangboard-packages.sh validate --root Hangboards --final-inventory`

Expected: both commands exit 0.

- [ ] **Step 4: Commit**

```bash
git add HangTen/Models/WorkoutActivityRecording.swift docs/superpowers/plans/2026-08-25-beastmaker-bilateral-highlight.md
git commit -m "Compile bilateral edge fallback"
```

### Task 5: Update the Beastmaker package inventory expectation

**Files:**
- Modify: `Tools/HangboardPackages/tests/test_beastmaker_2000_board_package.py:45,492-496`
- Modify: `docs/superpowers/plans/2026-08-25-beastmaker-bilateral-highlight.md`

**Interfaces:**
- Consumes: the Beastmaker 2000 package's canonical `kind` metadata.
- Produces: the package test's exact expected map and count for the two mirrored outer lower edges.

- [ ] **Step 1: Verify the existing test fails**

Run: `python -m pytest tests/test_beastmaker_2000_board_package.py::test_beastmaker_2000_inventory_shapes_and_symmetry -q`

Expected: FAIL because `front-lower-9` is still expected as a pocket and the count still expects one edge / 21 pockets.

- [ ] **Step 2: Apply the minimal expectation correction**

Change only the expected kind for `front-lower-9` to `edge`, and update the matching expected kind counts to five slopers, two edges, and 20 pockets. Do not change package geometry, production code, or unrelated fixture values.

- [ ] **Step 3: Verify focused and full Python suites**

Run: `python -m pytest tests/test_beastmaker_2000_board_package.py::test_beastmaker_2000_inventory_shapes_and_symmetry -q`

Run: `python -m pytest tests -q`

Expected: both commands exit 0.

- [ ] **Step 4: Commit and push**

```bash
git add Tools/HangboardPackages/tests/test_beastmaker_2000_board_package.py docs/superpowers/plans/2026-08-25-beastmaker-bilateral-highlight.md
git commit -m "Update Beastmaker edge inventory test"
git push
```

### Task 6: Preserve depth ranking before bilateral edge selection

**Files:**
- Modify: `HangTen/Models/WorkoutActivityRecording.swift:243-258`
- Modify: `docs/superpowers/plans/2026-08-25-beastmaker-bilateral-highlight.md`

**Interfaces:**
- Consumes: `depthDistance(of:from:) -> Double` and `oneHoldPerHand(from:) -> [BoardHold]`.
- Produces: one hold per board half only when those holds are tied for the closest documented depth; otherwise preserves the single nearest representative.

- [x] **Step 1: Use the existing fractional-depth regression test**

`testFallbackResolutionPrefersNearestFractionalDepthMeasurement` already defines a 20.5...21 mm left edge and 19.75 mm right edge and asserts that resolving `.mediumEdge` returns only `scalar-edge`. It is the regression test because selecting left/right candidates before applying the distance ranking returns both holds.

- [x] **Step 2: Verify the focused test fails on the current implementation**

Run:

```bash
rtk xcodebuild test -project HangTen.xcodeproj -scheme HangTen -destination 'platform=iOS Simulator,name=iPhone 16' -only-testing:HangTenTests/WorkoutActivityRecordingTests/testFallbackResolutionPrefersNearestFractionalDepthMeasurement
```

Expected: FAIL because both `range-edge` and `scalar-edge` are returned, despite only `scalar-edge` being nearest to the 20 mm source-backed medium-edge depth.

- [x] **Step 3: Apply the minimal resolver correction**

After selecting the ranked representative, restrict edge pairing to candidates whose `depthDistance` equals that representative's distance. Return a left/right pair only when that nearest set contains one eligible hold on each half; otherwise return the representative alone. Do not change exact feature resolution, capacity preference, group-tag resolution, or the source-backed depth values.

- [x] **Step 4: Verify the focused regression, bilateral behavior, and compile contract**

Run:

```bash
rtk xcodebuild test -project HangTen.xcodeproj -scheme HangTen -destination 'platform=iOS Simulator,name=iPhone 16' -only-testing:HangTenTests/WorkoutActivityRecordingTests/testFallbackResolutionPrefersNearestFractionalDepthMeasurement
rtk xcodebuild test -project HangTen.xcodeproj -scheme HangTen -destination 'platform=iOS Simulator,name=iPhone 16' -only-testing:HangTenTests/BoardTargetSubstitutionTests/testMetadataLightEdgeFallbackSelectsOneEdgePerBoardHalf
rtk xcodebuild build-for-testing -project HangTen.xcodeproj -scheme HangTen -destination 'generic/platform=iOS Simulator'
```

Expected: all commands exit 0. If the local Simulator runner is unavailable, record that limitation and run the compile contract; GitHub Actions is the required end-to-end XCTest verification.

Local focused XCTest runs could not initialize CoreSimulatorService or write a result bundle. The generic iOS Simulator `build-for-testing` contract passed; GitHub Actions will run both focused XCTest cases end-to-end.

- [x] **Step 5: Commit and push**

```bash
git add HangTen/Models/WorkoutActivityRecording.swift docs/superpowers/plans/2026-08-25-beastmaker-bilateral-highlight.md
git commit -m "Preserve depth ranking for paired edge fallback"
git push
```

### Task 7: Make the Task 1 fixture example self-contained

**Files:**
- Modify: `docs/superpowers/plans/2026-08-25-beastmaker-bilateral-highlight.md:36-50`

**Interfaces:**
- Consumes: the setup from the implemented `BoardTargetSubstitutionTests.testBeastmaker2000OpenHandLargeEdgeHighlightsMirroredOuterEdges`.
- Produces: a standalone Task 1 test example whose `store` is initialized before use.

- [ ] **Step 1: Verify the documentation discrepancy**

Compare the Task 1 Swift example with the implemented test. The example calls `store.holdIDs` without declaring `store`, while the implementation creates an isolated `UserDefaults` suite and `AppStore(defaults:)`.

- [ ] **Step 2: Apply the minimal documentation correction**

Add the same isolated `UserDefaults` suite setup, cleanup `defer`, and `AppStore(defaults:)` declaration before the example's `WorkoutStep`. Do not change the product implementation, board metadata, expected hold IDs, or other plan tasks.

- [ ] **Step 3: Verify scope and commit/push**

Run:

```bash
rtk git diff --check
```

Expected: no whitespace errors. Commit and push only the plan document:

```bash
git add docs/superpowers/plans/2026-08-25-beastmaker-bilateral-highlight.md
git commit -m "Document Beastmaker test fixture setup"
git push
```
