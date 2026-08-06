# Efficient Hold Editor Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make complete commercial-board tracing practical in 15–20 minutes through oriented resizing, sparse curves, symmetry tools, fast navigation, and optional local edge snapping.

**Architecture:** Extend the tested `editor-model.js` geometry module with board-independent pure operations, then keep `app.js` responsible for gestures and UI state. Export remains ordinary contour JSON, and every geometry operation enters existing undo/redo history.

**Tech Stack:** Browser SVG/Canvas JavaScript, Node's built-in test runner, Python local editor server.

## Global Constraints

- Do not add product-specific geometry, coordinates, or hold inventories.
- Derive symmetry from `canvas.width / 2`.
- Never snap or simplify without an explicit operator gesture.
- Preserve the Stage 2 JSON artifact and correction formats.
- Keep all operations undoable and dependency-free.

---

### Task 1: Tested geometry operations

**Files:**
- Modify: `Tools/hold-highlight-editor/editor-model.js`
- Modify: `Tools/hold-highlight-editor/tests/editor_model.test.js`

**Interfaces:**
- Produces: `resizeContour(options)`, `simplifyClosedContour(points, tolerance)`, `mirrorContour(points, canvasWidth)`, and `findStrongestEdge(options)`.

- [ ] **Step 1: Write failing geometry tests**

Test oriented corner scaling around the opposite corner, side-only scaling, Shift-style aspect preservation, centerline mirroring with reversed winding, closed-curve simplification with bounded deviation, and edge selection against a synthetic black/white boundary.

```js
assert.deepEqual(mirrorContour([[10, 5], [20, 5], [20, 10]], 100), [[80, 10], [80, 5], [90, 5]]);
assert.deepEqual(findStrongestEdge({rgba, width: 20, height: 10, point: [8, 5], radius: 5, threshold: 20}), [10, 5]);
```

- [ ] **Step 2: Verify the tests fail for missing exports**

Run: `rtk node --test Tools/hold-highlight-editor/tests/editor_model.test.js`

Expected: failures identify the four missing geometry functions.

- [ ] **Step 3: Implement the pure operations**

Perform resize in coordinates unrotated around the contour centroid. Use the handle name (`nw`, `n`, `ne`, `e`, `se`, `s`, `sw`, `w`) to select fixed axes and the opposite anchor. Implement closed Ramer–Douglas–Peucker by splitting the ring at a farthest-point pair and simplifying both chains. Compute edge score from horizontal and vertical luminance differences and return `null` below threshold.

- [ ] **Step 4: Verify geometry tests pass**

Run: `rtk node --test Tools/hold-highlight-editor/tests/editor_model.test.js`

Expected: all existing and new model tests pass.

### Task 2: Oriented resize and sparse curve controls

**Files:**
- Modify: `Tools/hold-highlight-editor/app.js`
- Modify: `Tools/hold-highlight-editor/index.html`
- Modify: `Tools/hold-highlight-editor/styles.css`

**Interfaces:**
- Consumes: `resizeContour` and `simplifyClosedContour` from Task 1.
- Produces: eight `.resize-handle` SVG controls and `simplifySelectedCurve()`.

- [ ] **Step 1: Render resize handles**

Place four square corner handles and four rectangular side handles on the existing oriented transform frame. Each handle carries a stable `data-resize-handle` value and starts a transform session with the original contour and rotation.

- [ ] **Step 2: Apply resize gestures**

On pointer move, convert the current pointer through the pure resize operation. Pass `event.shiftKey` to preserve aspect ratio. Commit one `Resized region` history item on pointer release.

- [ ] **Step 3: Add explicit curve simplification**

Add **Simplify curve** beside **Edit points**. Use tolerance `max(1.5, hypot(canvas.width, canvas.height) * 0.0025)`, keep at least four controls, set `pathStyle` to `smooth`, and commit one undoable operation. Disable the action for contours with fewer than six points.

- [ ] **Step 4: Verify syntax and model regression**

Run:

```bash
rtk node --check Tools/hold-highlight-editor/app.js
rtk node --test Tools/hold-highlight-editor/tests/editor_model.test.js
```

Expected: syntax and model tests pass.

### Task 3: Symmetry and navigation workflow

**Files:**
- Modify: `Tools/hold-highlight-editor/app.js`
- Modify: `Tools/hold-highlight-editor/index.html`
- Modify: `Tools/hold-highlight-editor/styles.css`

**Interfaces:**
- Consumes: `mirrorContour` from Task 1.
- Produces: `mirrorSelectedCopy()`, `beginMirrorOnto()`, `navigateRegion(direction)`.

- [ ] **Step 1: Add inspector actions**

Add **Mirror copy**, **Mirror onto…**, **Previous**, and **Next** controls. Mirror copy creates a new ID/key and mirrored contour. Mirror onto waits for the next different region selection, replaces geometry metadata and contour, and preserves target ID, key, type, interaction mode, and human notes.

- [ ] **Step 2: Add efficient shortcuts**

When text controls are unfocused, bind `[` and `]` to navigation, `M` to mirror copy, and `E` to point editing. Navigation follows sorted numeric IDs and scrolls the selected inventory item into view.

- [ ] **Step 3: Verify undo and dirty state**

Confirm mirror copy and mirror replacement each produce one history entry, enable Save, and fully restore through Undo.

### Task 4: Optional local edge snapping

**Files:**
- Modify: `Tools/hold-highlight-editor/app.js`
- Modify: `Tools/hold-highlight-editor/index.html`
- Modify: `Tools/hold-highlight-editor/styles.css`

**Interfaces:**
- Consumes: `findStrongestEdge` from Task 1.
- Produces: `state.snapEnabled`, offscreen image sample data, and `snapPoint(point, bypass)`.

- [ ] **Step 1: Capture source pixels**

After image load, draw the loaded image into an offscreen canvas and retain `{rgba, width, height}`. On a canvas security or decode failure, clear pixels, disable snapping, and show a concise status message.

- [ ] **Step 2: Add the snap toggle**

Add a toolbar **Snap edges** toggle and bind `S` outside text controls. Store only session UI state; do not write a product parameter. Indicate active state visually.

- [ ] **Step 3: Apply snapping to direct geometry gestures**

Before updating a contour point or resize pointer, call `findStrongestEdge` with radius `max(4, round(canvasDiagonal * 0.008))` and threshold `24`. Holding Alt bypasses snapping for that event. Do not snap move, rotate, bend, mirror, load, or save operations.

### Task 5: Documentation and browser verification

**Files:**
- Modify: `Tools/hold-highlight-editor/README.md`

**Interfaces:**
- Documents: gestures, shortcuts, symmetry behavior, snapping limitations, and undo recovery.

- [ ] **Step 1: Update operator documentation**

Explain the recommended trace loop: draw or duplicate, resize/rotate/bend, simplify only when needed, mirror symmetric holds, optionally snap direct handles, then Save.

- [ ] **Step 2: Run full automated verification**

Run:

```bash
rtk node --check Tools/hold-highlight-editor/app.js
rtk node --test Tools/hold-highlight-editor/tests/editor_model.test.js
rtk python3 -m pytest Tools/hold-highlight-editor/tests/test_server.py -q
rtk git diff --check
```

- [ ] **Step 3: Browser-test a real run**

Against Simulator 3D or Compact II, verify resize changes the selected outline, Mirror copy creates a symmetric selectable region, Simplify curve reduces point count, navigation changes selection, snap toggles, Undo restores each operation, and Save becomes enabled. Confirm no console errors.
