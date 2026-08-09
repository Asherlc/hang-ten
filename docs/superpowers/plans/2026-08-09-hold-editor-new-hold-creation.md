# Hold Editor New Hold Creation Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Ensure Enter/Escape work while drawing regardless of focused controls and preserve the selected primitive shape when creating a new hold highlight.

**Architecture:** Keep the existing dependency-free browser editor flow. Adjust only the global keyboard event ordering in `app.js` and the metadata assignment in `finishDraw()`, with source-level regression tests in the existing Node test file because this tool has no browser-test dependency.

**Tech Stack:** Vanilla JavaScript, HTML, Node.js built-in `node:test` and `node:assert/strict`.

## Global Constraints

- Existing shape choices remain the source of truth: freeform and curved freeform use point tracing; rectangle, rounded rectangle, arced rectangle, ellipse, and capsule use drag-to-create geometry.
- Curved freeform continues to store `shapeKind: "freeform"` with smooth path styling.
- Existing editing, text-entry, and global shortcuts keep their current behavior when no drawing session is active.
- Do not add runtime dependencies or refactor unrelated editor behavior.

---

### Task 1: Make new-hold completion focus-safe and shape-aware

**Files:**
- Modify: `Tools/hold-highlight-editor/app.js`
- Test: `Tools/hold-highlight-editor/tests/editor_ui.test.js`

**Interfaces:**
- Consumes: `state.drawing`, `state.drawShape`, `finishDraw()`, and the existing global `window` keydown handler.
- Produces: Enter and Escape handling that runs while a drawing session is active even when a text control or shape picker is focused; new primitive regions whose `metadata.shapeKind` equals the selected primitive shape.

- [ ] **Step 1: Write the failing regression tests**

Add two tests to `Tools/hold-highlight-editor/tests/editor_ui.test.js`:

```js
test("handles drawing Enter and Escape before the focused-control guard", () => {
  const drawingShortcut = app.indexOf('event.key === "Enter" && state.drawing');
  const focusedControlGuard = app.indexOf('if (editingText) return;');

  assert.notEqual(drawingShortcut, -1);
  assert.notEqual(focusedControlGuard, -1);
  assert.ok(drawingShortcut < focusedControlGuard);
  assert.match(app, /event\.key === "Escape" && state\.drawing/);
});

test("preserves the selected primitive shape when adding a highlight", () => {
  assert.match(app, /shapeKind: state\.drawShape === "curved-freeform" \? "freeform" : state\.drawShape/);
});
```

- [ ] **Step 2: Run the focused tests and verify they fail for the missing behavior**

Run:

```bash
node --test Tools/hold-highlight-editor/tests/editor_ui.test.js
```

Expected: the existing UI tests pass, while the two new tests fail because the keyboard guard precedes the drawing shortcut and `finishDraw()` hard-codes `shapeKind: "freeform"`.

- [ ] **Step 3: Implement the minimal keyboard-ordering and metadata changes**

In the global `window.addEventListener("keydown", ...)` handler, keep the Space state update, then handle drawing-specific Enter and Escape before the `if (editingText) return;` guard. The relevant structure must be equivalent to:

```js
if (event.code === "Space" && !editingText) { state.spacePressed = true; event.preventDefault(); }
if (event.key === "Enter" && state.drawing) {
  event.preventDefault();
  finishDraw();
  return;
}
if (event.key === "Escape" && state.drawing) {
  event.preventDefault();
  cancelDraw();
  return;
}
if (editingText) return;
```

Preserve the existing non-drawing shortcut branches after the guard. In `finishDraw()`, replace the hard-coded `shapeKind: "freeform"` with:

```js
shapeKind: state.drawShape === "curved-freeform" ? "freeform" : state.drawShape,
```

Keep the existing `pathStyle` mapping so curved freeform remains smooth and all other draw modes remain straight.

- [ ] **Step 4: Run the focused tests and verify they pass**

Run:

```bash
node --test Tools/hold-highlight-editor/tests/editor_ui.test.js
```

Expected: all UI tests pass, including both new regression tests.

- [ ] **Step 5: Run the complete editor test suite**

Run:

```bash
node --test Tools/hold-highlight-editor/tests/*.test.js
```

Expected: every editor model, UI, and server test passes with zero failures.

- [ ] **Step 6: Commit the implementation**

```bash
git add Tools/hold-highlight-editor/app.js Tools/hold-highlight-editor/tests/editor_ui.test.js
git commit -m "fix: preserve new hold shape and keyboard completion"
```
