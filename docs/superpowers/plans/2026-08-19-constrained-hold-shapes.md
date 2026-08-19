# Constrained Hold Shapes Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Persist semantic hold-shape constraints and provide shape-preserving resize handles in Hangboard Workbench.

**Architecture:** Keep canonical `frame` and `shape` geometry authoritative for rendering while adding a strictly validated optional piece-level `shapeConstraint`. Workbench reconstructs intrinsic bounds from the path plus saved rotation and regenerates exact primitives during constrained transforms.

**Tech Stack:** Python 3.11, vanilla JavaScript/SVG, Node test runner, Swift 5.10/XCTest

**Spec:** `docs/superpowers/specs/2026-08-19-constrained-hold-shapes-design.md`

## Global Constraints

- `shapeConstraint.shape` is exactly `oval`, `circle`, `pill`, `roundedRectangle`, or `rectangle`.
- `shapeConstraint.rotationDegrees` is finite and normalized to `[-180, 180)`.
- Existing `frame` and `shape` remain the only runtime rendering geometry.
- Absence of `shapeConstraint` means Custom/freeform; no existing board is inferred or migrated.
- Constraint operations affect only the selected geometry piece except existing physical-hold rotation, which continues to rotate every sibling and updates each constrained sibling angle.
- No board-specific code, coordinates, templates, or tuning.

---

### Task 1: Persist and validate shape constraints

**Files:**
- Modify: `Tools/HangboardWorkbench/board_package.py`
- Modify: `Tools/HangboardWorkbench/tests/test_board_package.py`
- Modify: `Tools/HangboardPipeline/src/hangboard_vectorizer/board_catalog.py`
- Modify: `Tools/HangboardPipeline/tests/test_board_catalog.py`
- Modify: `HangTen/Models/BoardPackageStore.swift`
- Modify: `HangTenTests/BoardPackageStoreTests.swift`

**Interfaces:**
- Produces editor regions with optional `shapeConstraint: { shape: string, rotationDegrees: number }`.
- Consumes and persists the same optional region value on save.
- Runtime board shape adaptation remains unchanged.

- [ ] **Step 1: Write failing package round-trip and rejection tests**

Add tests proving a valid oval constraint is exposed, saved, and present after reopen; choosing Custom by omitting the region field removes the stored piece field; invalid shapes and angles are rejected; constraint-only changes count as dirty; unrelated treatment and sibling pieces are preserved.

- [ ] **Step 2: Run focused Python tests and verify RED**

Run: `rtk uv run --with pytest python -m pytest -q Tools/HangboardWorkbench/tests/test_board_package.py`

Expected: failures because geometry pieces and editor regions reject `shapeConstraint`.

- [ ] **Step 3: Implement the Workbench schema path**

Add one private parser returning a normalized copied constraint. Allow the piece and editor-region optional keys, carry the value through parsed editor tuples, include it in dirty detection, and add/remove it during `_apply_editor_document`. Do not change rendering geometry conversion.

- [ ] **Step 4: Add failing pipeline and Swift decoder tests**

Use literal valid and invalid JSON fixtures. Assert pipeline parsing retains the two fields, Swift accepts a constrained piece and produces the same runtime `BoardShape`, and both reject unknown fields, invalid enums, booleans/non-finite values, and out-of-range angles.

- [ ] **Step 5: Run focused cross-consumer tests and verify RED**

Run: `rtk uv run --with pytest python -m pytest -q Tools/HangboardPipeline/tests/test_board_catalog.py`

Run: `rtk xcodebuild test -project HangTen.xcodeproj -scheme HangTen -destination 'platform=iOS Simulator,name=iPhone 17 Pro' -only-testing:HangTenTests/BoardPackageStoreTests`

- [ ] **Step 6: Implement strict pipeline and Swift decoding**

Extend geometry-piece allowed keys and add focused value types that validate the exact object. Retain the pipeline value. Decode and validate, but intentionally discard, the Swift value before existing runtime adaptation.

- [ ] **Step 7: Run focused tests GREEN and commit**

Run the three focused commands above. Commit: `Persist hold shape constraints`.

### Task 2: Add reusable constrained-shape transforms

**Files:**
- Modify: `Tools/HangboardWorkbench/path-editor.js`
- Modify: `Tools/HangboardWorkbench/tests/path-editor.test.js`

**Interfaces:**
- Produces `constrainedOutlineModel(pathString, constraint)` with center, rotation, intrinsic bounds, and eight world-space handles.
- Produces `resizeConstrainedOutline(pathString, constraint, handle, pointer, minimumSize = 2)` returning `{ displayPath, shapeConstraint }`.
- Existing `createOutlineShapePath` remains the primitive generator and gains a constraint-returning companion only if needed to avoid duplication.

- [ ] **Step 1: Write failing literal geometry tests**

Cover unrotated and rotated rectangles/ovals, all eight handle identifiers, fixed opposite anchors, edge-versus-corner dimensions, two-pixel clamping, circle corner and edge aspect locking, horizontal/vertical pills, and true Q/C extrema. Expected values must be hand-derived literals.

- [ ] **Step 2: Run focused Node tests and verify RED**

Run: `rtk node --test Tools/HangboardWorkbench/tests/path-editor.test.js`

Expected: failures because constrained model and resize exports do not exist.

- [ ] **Step 3: Implement local-axis modeling and resizing**

Normalize angles into `[-180, 180)`. Use the tight path center, inverse rotation, and existing extrema math to obtain intrinsic bounds. Map the eight handles between local and world coordinates. Resize in local coordinates, clamp before inversion, regenerate the selected primitive, and rotate every anchor/control back.

- [ ] **Step 4: Run focused tests GREEN and commit**

Run: `rtk node --test Tools/HangboardWorkbench/tests/path-editor.test.js`.

Commit: `Add constrained outline transforms`.

### Task 3: Integrate stateful shape controls and handles

**Files:**
- Modify: `Tools/HangboardWorkbench/index.html`
- Modify: `Tools/HangboardWorkbench/app.js`
- Modify: `Tools/HangboardWorkbench/styles.css`
- Modify: `Tools/HangboardWorkbench/tests/workbench_direct.test.js`

**Interfaces:**
- Consumes Task 1 region `shapeConstraint` and Task 2 constrained model/resize functions.
- Produces editor requests with updated or absent constraints through the existing save client.

- [ ] **Step 1: Write failing browser behavior tests**

Test the stateful picker including Custom, primitive selection at zero rotation, eight shape-aligned handles without vertex/control handles, selected-piece-only resize, circle locking, constraint-preserving body/nudge operations, sibling-aware rotation angle updates, Custom unlock, cancellation/lost-capture rollback of path plus constraint, busy-state protection, save request persistence, and reload restoration.

- [ ] **Step 2: Run direct browser tests and verify RED**

Run: `rtk node --test Tools/HangboardWorkbench/tests/workbench_direct.test.js`

Expected: failures because the picker is action-only and constrained handles do not exist.

- [ ] **Step 3: Implement stateful picker and constrained overlay**

Render Custom for regions without a constraint and the matching label otherwise. Primitive selection regenerates the selected path and stores `{ shape, rotationDegrees: 0 }`; Custom deletes the field without changing the path. Render the oriented box, connector, and eight handles for constrained regions, leaving existing freeform handles untouched.

- [ ] **Step 4: Integrate drag, rotation, rollback, and busy behavior**

Add a constrained-resize drag type using Task 2. Snapshot both paths and constraints for rollback. Update constrained sibling rotations in button, keyboard, and pointer rotation flows. Preserve constraints during body drag/nudge. Disable and guard controls during operations.

- [ ] **Step 5: Run JavaScript suites GREEN and commit**

Run: `rtk node --test Tools/HangboardWorkbench/tests/*.test.js`.

Commit: `Keep preset hold shapes constrained`.

### Task 4: Verify the complete feature and update documentation

**Files:**
- Modify: `Tools/HangboardWorkbench/README.md`

**Interfaces:**
- Consumes the complete durable schema and constrained editor behavior.

- [ ] **Step 1: Document the user-visible behavior and schema**

Explain the stateful picker, shape-aligned handles, Custom unlock, persistence, and the optional `shapeConstraint` object without describing it as editor-specific metadata.

- [ ] **Step 2: Run complete verification**

Run: `rtk node --test Tools/HangboardWorkbench/tests/*.test.js`.

Run: `rtk uv run --with pytest python -m pytest -q Tools/HangboardWorkbench/tests Tools/HangboardPipeline/tests`.

Run: `rtk swift test --package-path Tools/HangboardWorkbench/macos`.

Run the focused iOS test command from Task 1.

Run: `rtk git diff --check`.

- [ ] **Step 3: Commit**

Commit: `Document constrained hold shapes`.
