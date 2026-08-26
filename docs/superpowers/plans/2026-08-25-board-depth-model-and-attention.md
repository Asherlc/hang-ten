# Board Depth Model and Attention Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Show incomplete board depth metadata in the Workbench, expose fixed and variable depth editing, and migrate confirmed discrete stepped contacts to individual fixed-depth holds.

**Architecture:** The Python board summary owns `needsAttention`; the TypeScript client transports and renders it. Editor regions carry mutually exclusive `sizeMillimeters` and `depthRangeMillimeters`, with a mode control that atomically changes all pieces of a logical hold. Board packages use scalar depth for directly authored discrete contacts and a range only for continuous variable contacts.

**Tech Stack:** Python 3, TypeScript, React, Swift 6, XCTest, node:test, pytest.

**Spec:** `docs/superpowers/specs/2026-08-25-board-depth-model-and-attention-design.md`

## Global Constraints

- Require depth only for `edge` and `pocket`; never flag `jug`, `sloper`, or `pinch` for a missing depth.
- `sizeMillimeters` and `depthRangeMillimeters` are mutually exclusive and positive finite when present.
- Preserve fractional measurements exactly.
- Paths for split holds are deliberately authored and visually reviewed; no image-derived or mechanical geometry splitting.
- Do not alter a range-backed continuous contact without manufacturer evidence that it contains distinct contacts.

### Task 1: Board-list attention status

**Files:**
- Modify: `Tools/HangboardWorkbench/server.py`
- Modify: `Tools/HangboardWorkbench/src/types.ts`
- Modify: `Tools/HangboardWorkbench/src/workbench-client.ts`
- Modify: `Tools/HangboardWorkbench/src/components/BoardLibrary.tsx`
- Test: `Tools/HangboardWorkbench/tests/test_server.py`
- Test: `Tools/HangboardWorkbench/tests/react-app.test.tsx`

**Interfaces:**
- Produces `BoardSummary.needsAttention: boolean`.
- Consumes a package hold's `kind`, `sizeMillimeters`, and `depthRangeMillimeters`.

- [ ] **Step 1: Write failing server and UI tests.**

```python
assert listed["boards"][0]["needsAttention"] is True
```

```ts
assert.equal(app.text("#board-list button"), "Board A1 holdsNeeds attention");
```

Include a jug, sloper, and pinch with no depth and assert they do not make the
summary true; include an edge and a pocket with no scalar or range and assert
they do. Assert both fixed and range depth clear the status.

- [ ] **Step 2: Run the focused tests and verify they fail.**

Run: `rtk python3 -m pytest Tools/HangboardWorkbench/tests/test_server.py -k attention` and `rtk pnpm --dir Tools/HangboardWorkbench exec tsx --test tests/react-app.test.tsx --test-name-pattern='attention'`.

- [ ] **Step 3: Implement the typed payload and list status.**

```python
def _hold_needs_attention(hold: dict[str, object]) -> bool:
    return (hold["kind"] in {"edge", "pocket"}
        and "sizeMillimeters" not in hold
        and "depthRangeMillimeters" not in hold)
```

Set `needsAttention` in `_board_payload`; require it in `isBoardSummary`; render
`<small className="region-type">Needs attention</small>` only for true.

- [ ] **Step 4: Run focused and full Workbench tests.**

Run: `rtk python3 -m pytest Tools/HangboardWorkbench/tests/test_server.py` and `rtk pnpm --dir Tools/HangboardWorkbench test`.

### Task 2: Fixed and variable depth editor controls

**Files:**
- Modify: `Tools/HangboardWorkbench/src/types.ts`
- Modify: `Tools/HangboardWorkbench/src/editor-model.ts`
- Modify: `Tools/HangboardWorkbench/src/useHoldEditor.ts`
- Modify: `Tools/HangboardWorkbench/src/components/HoldInspector.tsx`
- Modify: `Tools/HangboardWorkbench/src/WorkbenchApp.tsx`
- Test: `Tools/HangboardWorkbench/tests/react-editor.test.tsx`
- Test: `Tools/HangboardWorkbench/tests/workbench-modules.test.ts`

**Interfaces:**
- Adds `HoldRegion.sizeMillimeters?: number`.
- Adds actions `changeHoldSizeMillimeters(size: number | undefined)` and mode-safe range updates.

- [ ] **Step 1: Write failing inspector tests.**

```ts
await app.change("#depth-measurement-select", "fixed");
await app.change("#hold-depth-input", "12.5");
assert.equal(saved[0]?.regions[0].sizeMillimeters, 12.5);
assert.equal("depthRangeMillimeters" in (saved[0]?.regions[0] ?? {}), false);
```

Also assert `variable` clears scalar depth, `unset` clears both, and reopening
a range-backed or scalar-backed hold selects the matching mode.

- [ ] **Step 2: Run the focused tests and verify they fail.**

Run: `rtk pnpm --dir Tools/HangboardWorkbench exec tsx --test tests/react-editor.test.tsx --test-name-pattern='depth measurement'`.

- [ ] **Step 3: Implement atomic depth-mode changes.**

```ts
if (mode === "fixed") {
  region.sizeMillimeters = size;
  delete region.depthRangeMillimeters;
}
```

Use the inverse operation for variable mode and delete both for unset. Clone,
validate, parse, and save `sizeMillimeters` with the same finite-positive rules
already used for ranges.

- [ ] **Step 4: Run full Workbench validation.**

Run: `rtk pnpm --dir Tools/HangboardWorkbench test && rtk pnpm --dir Tools/HangboardWorkbench run check:bundle`.

### Task 3: Package-model exclusivity

**Files:**
- Modify: `Tools/HangboardWorkbench/board_package.py`
- Modify: `Tools/HangboardPackages/src/hangboard_packages/board_catalog.py`
- Modify: `HangTen/Models/BoardPackageStore.swift`
- Modify: `HangTen/Models/BoardPackageWriter.swift`
- Modify: `HangTen/Models/TrainingModels.swift`
- Test: `Tools/HangboardWorkbench/tests/test_board_package.py`
- Test: `Tools/HangboardPackages/tests/test_board_catalog.py`
- Test: `HangTenTests/BoardPackageStoreTests.swift`
- Test: `HangTenTests/BoardPackageWriterTests.swift`

**Interfaces:**
- Consumes the two optional depth fields and rejects documents containing both.
- Keeps `BoardHold.depthRangeMillimeters` for continuous contacts.

- [ ] **Step 1: Write failing parser and writer tests for conflicting depth fields.**

```python
with pytest.raises(ValueError, match="must not specify both"):
    parse_hold({"sizeMillimeters": 10, "depthRangeMillimeters": {"lowerBound": 8, "upperBound": 10}})
```

Add equivalent Workbench and iOS load/write coverage plus a fractional scalar
round-trip assertion.

- [ ] **Step 2: Run focused tests and verify they fail.**

Run: `rtk python3 -m pytest Tools/HangboardWorkbench/tests/test_board_package.py Tools/HangboardPackages/tests/test_board_catalog.py -k depth`.

- [ ] **Step 3: Reject conflicting forms at every package boundary.**

```swift
if sizeMillimeters != nil && depthRangeMillimeters != nil {
    throw invalid("hold \(hold.id) must not specify both a size and depth range", document)
}
```

Keep range support in the training model and depth substitution so existing
continuous contacts remain selectable by any in-range target.

- [ ] **Step 4: Run focused package and Swift tests.**

Run: `rtk scripts/hangboard-packages.sh validate --root Hangboards --final-inventory` and the repository's focused `xcodebuild test` command for `BoardPackageStoreTests` and `BoardPackageWriterTests`.

### Task 4: Discrete-contact catalog migration and visual review

**Files:**
- Modify: affected `Hangboards/*/board.json` packages only after evidence review
- Modify: `docs/source-audits/2026-08-25-hold-metadata-completeness-appendendum.md`
- Test: corresponding package-specific tests

**Interfaces:**
- Replaces a confirmed discrete range-backed contact with one scalar-depth hold
  per directly authored physical contact.
- Retains range-backed continuous contacts unchanged.

- [ ] **Step 1: Write failing package inventory tests for each confirmed split.**

```python
assert {hold["sizeMillimeters"] for hold in holds if hold["id"].startswith("edge-10-")} == {8, 10}
assert "depthRangeMillimeters" not in split_hold
```

Name the exact new IDs and expected logical count from the official product
mapping before altering package data.

- [ ] **Step 2: Run each package test and verify it fails before data edits.**

Run the relevant `pytest` package tests one at a time.

- [ ] **Step 3: Research, author, and review each split manually.**

Use the official Tension Grindstone, Honestone, Whetstone, and Frictitious
Megalith sources. For each source-confirmed discrete contact, draw a new closed
canonical path in Workbench, create a stable descriptive ID and scalar depth,
and mirror the reviewed source side only for verified symmetric boards. Retain
Forge and Pivot variable rails as ranges.

- [ ] **Step 4: Record the URLs, hold-ID mapping, resulting inventory, and visual review.**

Document why each split is a distinct contact and why each retained range is
continuous. Do not claim a per-contact mapping the manufacturer evidence does
not establish.

- [ ] **Step 5: Validate package, app, and visual results.**

Run: `rtk scripts/hangboard-packages.sh validate --root Hangboards --final-inventory`, package tests, and the isolated-simulator review procedure in `validate-hang-ten-ios`.
