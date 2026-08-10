# Per-Segment Hold Curves Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add explicit per-edge quadratic curve handles to the dependency-free hold editor on `main`, preserving Stage 2 artifact compatibility and making quarter-circle-like edges practical.

**Architecture:** Keep the current Stage 2 contour as the source of vertex topology and add validated `metadata.edgeCurves` controls keyed by starting edge index. Centralize path construction, curve flattening, edge-index maintenance, and geometric transforms in `editor-model.js`; keep `app.js` responsible for SVG controls, pointer sessions, and history. Export a deterministic flattened contour while retaining editable curve metadata.

**Tech Stack:** Browser SVG, vanilla JavaScript, Node's built-in `node:test`, Python loopback editor server.

## Global Constraints

- Base all implementation commits on `main` at `94bc20b`.
- Keep the editor dependency-free and compatible with existing Stage 2 JSON artifacts.
- Missing `metadata.edgeCurves` means every edge is straight; existing documents load unchanged.
- Curve controls use finite canvas coordinates and valid edge indexes only.
- Ordinary object dragging remains unchanged when **Edit points** is off.
- Every curve gesture creates one undoable history entry on pointer release.
- Stage 2 exports a deterministic flattened `contour` and preserves editable `edgeCurves` metadata.
- Do not port or create the absent Stage 3 vector editor in this change.

---

### Task 1: Add pure per-edge curve geometry and persistence

**Files:**
- Modify: `Tools/hold-highlight-editor/editor-model.js`
- Test: `Tools/hold-highlight-editor/tests/editor_model.test.js`

**Interfaces:**
- Produces `normalizeEdgeCurves(edgeCurves, pointCount) -> object` that returns a detached, validated map of integer edge indexes to `{ kind: "quadratic", control: [x, y] }` and throws on malformed supplied entries.
- Produces `contourPath(points, style, tension, edgeCurves) -> string`, using `L` for missing edge entries and `Q control endpoint` for quadratic entries while preserving the existing smooth path behavior when no per-edge curves exist.
- Produces `flattenContour(points, style, tension, edgeCurves, curveSteps = 32) -> number[][]`, returning a closed ring without a duplicate endpoint and sampling quadratic/smooth segments deterministically.
- Produces `setEdgeCurveControl(edgeCurves, edgeIndex, control, pointCount) -> object`, `translateEdgeCurves(edgeCurves, dx, dy, pointCount) -> object`, `mapEdgeCurves(edgeCurves, pointCount, mapper) -> object`, and `mirrorEdgeCurves(edgeCurves, pointCount, canvasWidth) -> object` as detached pure helpers.
- Produces `insertEdgeCurves(edgeCurves, insertionIndex, pointCount) -> object` to shift unaffected edge indexes and discard the split edge's stale control.

- [x] **Step 1: Write failing model tests for normalization and path output.**

Add tests with these exact behaviors:

```js
test("contourPath emits a quadratic only for the selected edge", () => {
  assert.equal(
    contourPath(
      [[0, 0], [10, 0], [10, 10]],
      "straight",
      0.8,
      { 0: { kind: "quadratic", control: [5, -4] } },
    ),
    "M 0 0 Q 5 -4 10 0 L 10 10 L 0 0 Z",
  );
});

test("flattenContour samples a quadratic edge without duplicating the ring endpoint", () => {
  const result = flattenContour(
    [[0, 0], [10, 0], [10, 10]],
    "straight",
    0.8,
    { 0: { kind: "quadratic", control: [5, -10] } },
    4,
  );
  assert.deepEqual(result.slice(0, 5), [[0, 0], [2.5, -3.75], [5, -5], [7.5, -3.75], [10, 0]]);
  assert.notDeepEqual(result[0], result.at(-1));
});

test("normalizeEdgeCurves rejects invalid edge indexes, kinds, and coordinates", () => {
  assert.throws(() => normalizeEdgeCurves({ 3: { kind: "quadratic", control: [1, 1] } }, 3), /edge/i);
  assert.throws(() => normalizeEdgeCurves({ 0: { kind: "cubic", control: [1, 1] } }, 3), /kind/i);
  assert.throws(() => normalizeEdgeCurves({ 0: { kind: "quadratic", control: [Infinity, 1] } }, 3), /finite/i);
});
```

- [x] **Step 2: Run the model tests and verify the new tests fail for missing APIs.**

Run:

```bash
rtk node --test Tools/hold-highlight-editor/tests/editor_model.test.js
```

Expected: the existing tests pass and the new tests fail because the curve helpers are not exported yet.

- [x] **Step 3: Implement validated command construction and flattening.**

Implement quadratic sampling with `remaining = 1 - progress` and the standard quadratic Bézier equation. Preserve the current smooth tangent algorithm when `edgeCurves` is empty. When any edge curve exists, emit one closed command per edge and use straight `L` commands for uncurved edges. Round only at export boundaries; keep in-memory controls finite numbers.

- [x] **Step 4: Implement pure edge-map mutation and mirror/index helpers.**

`setEdgeCurveControl` must create a quadratic entry, `translateEdgeCurves` must add the delta to every control, `mapEdgeCurves` must apply a finite two-coordinate mapper to every control, and `mirrorEdgeCurves` must map an old edge `k` to new edge `(pointCount - 2 - k + pointCount) % pointCount` while reflecting its control across `canvasWidth`. `insertEdgeCurves` must preserve entries before the split and shift entries at or after the insertion boundary without leaving an index equal to the new point count.

- [x] **Step 5: Integrate export, normalization, comparison, and existing geometry operations.**

Update `normalizePipelineDocument` to preserve validated `metadata.edgeCurves` or omit it when absent. Update `regionForExport` to flatten the rendered contour before calculating `anchor`, `areaPixels`, and `bounds`, while retaining the editable metadata. Include normalized `edgeCurves` in `comparisonKey` so curve-only changes appear in corrections. Ensure malformed persisted metadata is rejected through the existing load error path rather than silently exported.

Checkpoint: `regionForExport` also retains `metadata.editableContour` whenever flattening changes the contour topology. Smooth contours without `metadata.edgeCurves` whose non-empty corner treatments cause flattening preserve their editable topology after export and reload, and the regression test covers that case alongside existing edge-curve behavior.

- [x] **Step 6: Run the complete model suite and commit.**

Run:

```bash
rtk node --test Tools/hold-highlight-editor/tests/editor_model.test.js
rtk git diff --check
```

Commit:

```bash
rtk git add Tools/hold-highlight-editor/editor-model.js Tools/hold-highlight-editor/tests/editor_model.test.js
rtk git commit -m "feat: add per-edge curve geometry"
```

---

### Task 2: Add curve handles and pointer editing to the SVG editor

**Files:**
- Modify: `Tools/hold-highlight-editor/app.js`
- Modify: `Tools/hold-highlight-editor/index.html`
- Modify: `Tools/hold-highlight-editor/styles.css`
- Create: `Tools/hold-highlight-editor/tests/editor_ui.test.js`

**Interfaces:**
- Consumes all curve helpers from Task 1.
- Produces `state.edgeSession` with `{ pointerId, index, changed }` and renders `.edge-curve-handle` plus `.edge-curve-line` controls only for the selected region while edit mode is enabled.
- Keeps `startRegionDrag`, `startHandleDrag`, `onSvgPointerMove`, and `onSvgPointerUp` behavior unchanged for object and vertex sessions.

- [x] **Step 1: Write failing UI contract tests.**

Create a dependency-free contract test that reads the HTML, CSS, and app source and asserts:

```js
test("editor exposes curve-editing affordances", () => {
  const html = fs.readFileSync(path.join(__dirname, "..", "index.html"), "utf8");
  const css = fs.readFileSync(path.join(__dirname, "..", "styles.css"), "utf8");
  const app = fs.readFileSync(path.join(__dirname, "..", "app.js"), "utf8");
  assert.match(html, /Edit points/);
  assert.match(app, /edge-curve-handle/);
  assert.match(app, /startEdgeCurveDrag/);
  assert.match(css, /\.edge-curve-handle/);
});
```

Also add a model-backed test that a region with `metadata.edgeCurves` renders a `Q` path through the exported `contourPath` helper.

- [x] **Step 2: Run the UI contract test and verify it fails.**

Run:

```bash
rtk node --test Tools/hold-highlight-editor/tests/editor_ui.test.js
```

Expected: failure because the new handle class and drag function do not exist.

- [x] **Step 3: Render per-edge handles and control lines.**

Replace the local `pathFor` implementation with the model's `contourPath` call. In the selected region's `state.editPoints` branch, render existing vertex circles and then one edge handle for each segment. Use the stored control when present; otherwise use the segment midpoint. Render a control line from the first endpoint to the control and from the control to the second endpoint, with `aria-label="Curve edge N"` on the handle. Use inverse zoom sizing so controls remain usable at every zoom.

- [x] **Step 4: Implement curve-handle pointer capture and one-entry history.**

Add `startEdgeCurveDrag(event, id, index)` with the same left-button guard and pointer capture as vertex editing. During `onSvgPointerMove`, snap the pointer only when edge snapping is enabled and call `setEdgeCurveControl` on the selected region's metadata. During `onSvgPointerUp`, commit `Moved edge curve` once when `changed` is true and clear the session. Do not let a curve-handle event fall through to object dragging.

- [x] **Step 5: Keep edge metadata correct during existing editor mutations.**

Translate controls during whole-region drag and duplicate operations. Map controls through rotate, bend, and resize operations using the same local-to-world transforms applied to contour points. Mirror controls with `mirrorEdgeCurves` for Mirror copy and Mirror onto. Call `insertEdgeCurves` when double-clicking an edge to add a contour point. Clear edge curves when Simplify curve replaces the contour with a new topology. Keep deleting a region naturally discarding its metadata.

- [x] **Step 6: Update controls, status copy, and operator documentation.**

Change the Edit points status text to mention vertices and edges, update the footer shortcut hint to say `Edit points` includes curves, and add a concise README section: enable Edit points, drag an edge handle to bow it, use the existing image snap behavior when useful, and undo if the curve is too aggressive. Do not add a new persistent form field.

- [x] **Step 7: Run syntax, model, and UI tests and commit.**

Run:

```bash
rtk node --check Tools/hold-highlight-editor/app.js
rtk node --test Tools/hold-highlight-editor/tests/editor_model.test.js Tools/hold-highlight-editor/tests/editor_ui.test.js
rtk git diff --check
```

Commit:

```bash
rtk git add Tools/hold-highlight-editor/app.js Tools/hold-highlight-editor/index.html Tools/hold-highlight-editor/styles.css Tools/hold-highlight-editor/README.md Tools/hold-highlight-editor/tests/editor_ui.test.js
rtk git commit -m "feat: edit individual hold edges"
```

---

### Task 3: Regression verification and browser smoke test

**Files:**
- Modify: `Tools/hold-highlight-editor/README.md` only if smoke testing finds a documentation mismatch.

**Interfaces:**
- Consumes the completed Stage 2 editor and existing Python server tests.
- Produces fresh verification evidence for model behavior, UI wiring, server compatibility, and the user-visible quarter-circle workflow.

- [x] **Step 1: Run all JavaScript editor tests.**

Run:

```bash
rtk node --test Tools/hold-highlight-editor/tests/*.test.js
```

Expected: zero failures, including the new geometry and UI contract tests.

- [x] **Step 2: Run editor server tests and source checks.**

Run:

```bash
rtk python3 -m pytest Tools/hold-highlight-editor/tests/test_server.py -q
rtk node --check Tools/hold-highlight-editor/app.js
rtk git diff --check
```

- [ ] **Step 3: Smoke-test the actual editor.**

Start the local server against the existing demo, select a region, enable **Edit points**, and verify:

1. Each edge has a visible curve handle and control lines.
2. Dragging one handle changes only that edge and leaves vertices fixed.
3. A bowed edge can be shaped into a quarter-circle-like arc.
4. Undo restores the prior path in one step; redo reapplies it.
5. Object drag, rotate, resize, bend, mirror copy, and export preserve the curve metadata.
6. Reloading the exported JSON restores the visible curve.

- [x] **Step 4: Perform final whole-branch review before handoff.**

Review the complete diff against `main`, confirm no Stage 3 feature-branch files were imported, verify the design requirements line by line, and only then report the exact test commands and results.
