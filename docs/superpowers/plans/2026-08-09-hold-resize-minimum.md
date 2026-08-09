# Hold Resize Minimum Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Keep browser Hold Editor highlights at least 6 canvas pixels wide and tall during resize operations.

**Architecture:** Preserve the pure `resizeContour` geometry function and its rotated local-coordinate math. Replace its scale-only floor with a dimension-aware scale floor derived from the original local bounds; keep opposite-edge anchoring and Shift aspect-ratio behavior. Verify the pure model independently through the existing Node test suite.

**Tech Stack:** Plain JavaScript, Node’s built-in `node:test`, SVG pointer interaction.

## Global Constraints

- Keep the existing normalized, rotated resize algorithm and opposite-edge anchoring.
- Use a fixed minimum of 6 canvas pixels for each active resize axis.
- Do not change persistence schemas, rendering, pointer-event wiring, or UI copy.
- Preserve existing normal side, corner, and aspect-ratio resize behavior.
- Leave unrelated worktree edits untouched.

## Task 1: Add failing resize minimum regression tests

**Files:**
- Modify: `Tools/hold-highlight-editor/tests/editor_model.test.js`
- Test: `Tools/hold-highlight-editor/tests/editor_model.test.js`

**Interfaces:**
- Consumes: `resizeContour({ points, rotation, handle, pointer, preserveAspect })` from `editor-model.js`.
- Produces: regression coverage that requires side and corner resizes to retain a 6 px active dimension.

- [ ] **Step 1: Add a side-resize failure test**

Add this test immediately after the existing `resizeContour limits a side handle to one local axis` test:

```js
test("resizeContour keeps a side resize above the minimum canvas width", () => {
  const result = resizeContour({
    points: [[0, 0], [40, 0], [40, 20], [0, 20]],
    rotation: 0,
    handle: "e",
    pointer: [-20, 10],
  });

  const xs = result.map(([x]) => x);
  assert.ok(Math.max(...xs) - Math.min(...xs) >= 6);
});
```

- [ ] **Step 2: Add a corner-resize failure test**

Add this test immediately after the side minimum test:

```js
test("resizeContour keeps both dimensions above minimum for an inward corner resize", () => {
  const result = resizeContour({
    points: [[0, 0], [40, 0], [40, 20], [0, 20]],
    rotation: 0,
    handle: "se",
    pointer: [-20, -20],
  });

  const xs = result.map(([x]) => x);
  const ys = result.map(([, y]) => y);
  assert.ok(Math.max(...xs) - Math.min(...xs) >= 6);
  assert.ok(Math.max(...ys) - Math.min(...ys) >= 6);
});
```

- [ ] **Step 3: Run the focused tests and confirm the new tests fail for the expected reason**

Run:

```bash
rtk node --test Tools/hold-highlight-editor/tests/editor_model.test.js
```

Expected: the existing tests pass, and both new tests fail because the current `0.05` scale floor produces a 2 px minimum dimension for the 40 px-wide fixture.

- [ ] **Step 4: Commit the failing tests**

```bash
rtk git add Tools/hold-highlight-editor/tests/editor_model.test.js
rtk git commit -m "test: cover minimum hold resize dimensions"
```

## Task 2: Implement dimension-aware minimum resize scaling

**Files:**
- Modify: `Tools/hold-highlight-editor/editor-model.js:126-159`

**Interfaces:**
- Consumes: the failing tests and the existing `resizeContour` signature.
- Produces: a `resizeContour` implementation that never returns less than 6 canvas pixels on an active axis.

- [ ] **Step 1: Replace the percentage-only scale floor**

In `resizeContour`, after computing `[minX, minY, maxX, maxY]`, derive the local dimensions and use them to floor each active scale:

```js
const localWidth = Math.max(maxX - minX, 1e-6);
const localHeight = Math.max(maxY - minY, 1e-6);
const minimumSize = 6;
const minimumScaleX = minimumSize / localWidth;
const minimumScaleY = minimumSize / localHeight;
scaleX = scalesX ? Math.max(minimumScaleX, scaleX) : 1;
scaleY = scalesY ? Math.max(minimumScaleY, scaleY) : 1;
```

Keep inactive axes at `1`. Keep the existing Shift branch after these floors, and when aspect ratio is preserved choose the dominant scale as today, then raise the shared scale to `Math.max(minimumScaleX, minimumScaleY)` so both dimensions remain at least 6 px.

- [ ] **Step 2: Run the focused tests and confirm they pass**

Run:

```bash
rtk node --test Tools/hold-highlight-editor/tests/editor_model.test.js
```

Expected: all model tests pass, including the new side and corner minimum tests and the existing normal/aspect-ratio tests.

- [ ] **Step 3: Review the diff for scope and whitespace**

Run:

```bash
rtk git diff --check HEAD~1
rtk git diff --stat HEAD~1
```

Confirm only `Tools/hold-highlight-editor/editor-model.js` and the focused test file are part of this implementation commit; do not include unrelated Hang Ten edits.

- [ ] **Step 4: Commit the implementation**

```bash
rtk git add Tools/hold-highlight-editor/editor-model.js
rtk git commit -m "fix: prevent hold resize collapse"
```

## Task 3: Final verification

**Files:**
- Verify: `Tools/hold-highlight-editor/editor-model.js`
- Verify: `Tools/hold-highlight-editor/tests/editor_model.test.js`

**Interfaces:**
- Consumes: the completed implementation and focused regression suite.
- Produces: evidence that the editor model is green and the final diff is scoped.

- [ ] **Step 1: Run all hold-highlight-editor tests**

Run:

```bash
rtk node --test Tools/hold-highlight-editor/tests/*.test.js
```

Expected: all JavaScript editor tests pass.

- [ ] **Step 2: Inspect the final repository state**

Run:

```bash
rtk git status --short
rtk git log -3 --oneline
```

Confirm the two implementation commits are present and the pre-existing unrelated modifications remain uncommitted and unchanged.

- [ ] **Step 3: Report verification limits**

Report that the pure model and source-level browser editor tests passed. Do not run Hang Ten iOS simulator validation because this change is confined to `Tools/hold-highlight-editor`, not the SwiftUI app.
