# Beastmaker Bilateral Highlight Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Highlight both mirrored outer lower Beastmaker 2000 edges for the 29 mm open-hand cue.

**Architecture:** The board-preview renderer already receives all resolved IDs. Correct the physical inventory so the existing target resolver recognizes the mirrored right outer lower contact as an edge, then protect that resolution with an app-store regression test. Preserve all canonical geometry.

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
