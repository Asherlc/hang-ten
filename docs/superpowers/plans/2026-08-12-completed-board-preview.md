# Completed Board Preview Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Render a completed Stage 4 board's normal artifact in the Onboard canvas when it has no editable or review image URL.

**Architecture:** Keep image selection centralized in `checkpointImageUrl()`, which is already used by `loadCheckpoint()`. Add the completed-board artifact as its final fallback, preserving the existing editable-image and review-image precedence. Lock the behavior with the controller's Node test suite.

**Tech Stack:** Vanilla JavaScript, Node.js built-in test runner.

## Global Constraints

- Preserve existing URL precedence: `editorImageUrl`, then `reviewUrl`, then `normalArtifactUrl`.
- Return `null` when the view is absent or none of those artifact URLs is available.
- Do not change board APIs, persistence, image-loading behavior, or Stage 2/3 comparison behavior.
- Add no dependencies.

---

### Task 1: Select the completed-board normal artifact for the canvas

**Files:**
- Modify: `Tools/HangboardWorkbench/workbench-controller.js:332-335`
- Modify: `Tools/HangboardWorkbench/tests/workbench_controller.test.js`

**Interfaces:**
- Consumes: a board view with optional `editorImageUrl`, `reviewUrl`, and `normalArtifactUrl` fields.
- Produces: `checkpointImageUrl(view)`, returning the first available URL in the required precedence order or `null`.

- [ ] **Step 1: Write the failing regression test**

In `Tools/HangboardWorkbench/tests/workbench_controller.test.js`, add this test beside the existing `checkpointImageUrl` coverage:

```javascript
test("checkpoint image selection uses the completed board normal artifact when no editor or review image exists", () => {
  assert.equal(
    checkpointImageUrl({
      editorImageUrl: null,
      reviewUrl: null,
      normalArtifactUrl: "/api/artifact?path=stage-4-normal.png",
    }),
    "/api/artifact?path=stage-4-normal.png",
  );
});
```

- [ ] **Step 2: Run the focused test and verify it fails**

Run:

```bash
node --test Tools/HangboardWorkbench/tests/workbench_controller.test.js
```

Expected: the new test fails because `checkpointImageUrl()` returns `null` when `editorImageUrl` and `reviewUrl` are absent.

- [ ] **Step 3: Implement the smallest production change**

In `Tools/HangboardWorkbench/workbench-controller.js`, replace the `checkpointImageUrl()` return statement with:

```javascript
return view.editorImageUrl || view.reviewUrl || view.normalArtifactUrl || null;
```

- [ ] **Step 4: Run the focused test and verify it passes**

Run:

```bash
node --test Tools/HangboardWorkbench/tests/workbench_controller.test.js
```

Expected: PASS, including the new completed-board fallback regression test.

- [ ] **Step 5: Run the affected browser and server tests**

Run:

```bash
node --test Tools/HangboardWorkbench/tests/workbench_controller.test.js Tools/HangboardWorkbench/tests/workbench_app.test.js
pytest Tools/HangboardWorkbench/tests/test_server.py -q
```

Expected: PASS. The server test confirms completed boards expose `normalArtifactUrl`; the controller test confirms the canvas selects it.

- [ ] **Step 6: Commit and push the implementation**

```bash
git add Tools/HangboardWorkbench/workbench-controller.js Tools/HangboardWorkbench/tests/workbench_controller.test.js
git commit -m "fix: render completed workbench boards"
git push
```

## Self-Review

- Spec coverage: the task covers the Stage 4 URL that the server already publishes and preserves every prior fallback.
- Placeholder scan: no deferred work or unspecified commands remain.
- Type consistency: all three URL fields are optional strings on the existing view payload, and `checkpointImageUrl()` continues to return a URL or `null`.
