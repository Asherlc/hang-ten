# Focused Hold Outline Editor Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make the Workbench a focused expert editor for correcting automatic hold outlines, while keeping advanced geometry tools available only in a selected-hold drawer.

**Architecture:** Replace the workbench suite shell with a single `Edit holds` surface and reduce the header to board context, history, save, board details, and a `More` overflow menu. Keep existing geometry operations and persistence unchanged; add a small browser/CommonJS UI model that decides which advanced controls apply to the selected region, then let `app.js` render those groups contextually.

**Tech Stack:** Dependency-free HTML, CSS, and browser JavaScript; Node.js built-in test runner; existing `editor-model.js`, `curve-gesture-model.js`, and Workbench client/controller modules.

## Global Constraints

- Preserve the current Stage 2 / Stage 3 geometry documents, autosave, validation, undo/redo, revision binding, and local-save semantics.
- Do not infer board metadata, training content, or hold geometry.
- The main editing surface must contain no user-facing stage, checkpoint, promotion, or validation wording.
- Expert controls must remain available only for applicable selected geometry; hide inapplicable controls rather than presenting disabled unexplained controls.
- `Save changes` must remain a local action and must never commit, push, or synchronize board changes.
- Every implementation commit is pushed to `origin simplify-board-editor`.

## File Structure

- `Tools/HangboardWorkbench/editor-ui-model.js` — pure selection-to-advanced-tool visibility model usable in the browser and Node tests.
- `Tools/HangboardWorkbench/index.html` — single editor markup, selected-hold Advanced tools groups, Board details popover, and More overflow menu.
- `Tools/HangboardWorkbench/styles.css` — two-column editor layout and styling for the contextual inspector, disclosure groups, Board details, and More menu.
- `Tools/HangboardWorkbench/app.js` — remove suite-view rendering/wiring, render current board context, and bind the new disclosure/overflow controls to existing operations.
- `Tools/HangboardWorkbench/tests/workbench_editor_ui_model.test.js` — behavioral unit tests for advanced-group applicability.
- `Tools/HangboardWorkbench/tests/workbench_app.test.js` — static shell and wiring assertions for the focused editor.
- `Tools/HangboardWorkbench/tests/editor_ui.test.js` — focused inspector/geometry UI assertions.
- `Tools/HangboardWorkbench/README.md` — operator documentation for the focused outlining workflow and the location of expert tools.

---

### Task 1: Define the contextual Advanced tools model

**Files:**
- Create: `Tools/HangboardWorkbench/editor-ui-model.js`
- Create: `Tools/HangboardWorkbench/tests/workbench_editor_ui_model.test.js`
- Modify: `Tools/HangboardWorkbench/index.html` (load the model immediately before `app.js`)

**Interfaces:**
- Consumes: selected regions with `metadata.shapeKind`, the current `editorMode`, `editable`, and `hasImagePixels` booleans.
- Produces: `advancedToolVisibility({ region, editorMode, editable, hasImagePixels })`, returning frozen booleans `{ outline, transform, assists, details, edgeSnap }`.
- Consumed by: `renderInspector()` in `app.js`, which maps each boolean to the corresponding `.advanced-tool-group` or individual snap control’s `hidden` state.

- [ ] **Step 1: Write the failing unit tests**

Create `workbench_editor_ui_model.test.js` with representative contour, primitive, vector, and no-selection regions. Assert the exact public result so the later DOM layer cannot accidentally expose irrelevant controls:

```js
const { advancedToolVisibility } = require("../editor-ui-model.js");

test("freeform contour holds expose outline, assists, and details", () => {
  assert.deepEqual(advancedToolVisibility({
    region: { metadata: { shapeKind: "freeform" } },
    editorMode: "contour", editable: true, hasImagePixels: true,
  }), {
    outline: true, transform: true, assists: true, details: true, edgeSnap: true,
  });
});

test("vector and no-selection states expose no contour expert controls", () => {
  assert.deepEqual(advancedToolVisibility({
    region: null, editorMode: "contour", editable: true, hasImagePixels: true,
  }), { outline: false, transform: false, assists: false, details: false, edgeSnap: false });
  assert.deepEqual(advancedToolVisibility({
    region: { metadata: { shapeKind: "freeform" } },
    editorMode: "vector", editable: true, hasImagePixels: true,
  }), { outline: false, transform: false, assists: false, details: true, edgeSnap: false });
});
```

- [ ] **Step 2: Run the test to verify it fails**

Run: `node --test Tools/HangboardWorkbench/tests/workbench_editor_ui_model.test.js`

Expected: FAIL because `editor-ui-model.js` does not exist.

- [ ] **Step 3: Implement the minimal pure model**

Create a UMD-style module matching the existing editor model files. Contour-specific controls require a selected region, `editable === true`, and `editorMode !== "vector"`; Details requires only a selected editable region; edge snapping additionally requires pixels:

```js
function advancedToolVisibility({ region = null, editorMode = "contour", editable = false, hasImagePixels = false } = {}) {
  const selected = Boolean(region);
  const editableSelection = selected && editable;
  const contourSelection = editableSelection && editorMode !== "vector";
  return Object.freeze({
    outline: contourSelection,
    transform: contourSelection,
    assists: contourSelection,
    details: editableSelection,
    edgeSnap: contourSelection && hasImagePixels,
  });
}
```

Export `advancedToolVisibility` through both `module.exports` and `globalThis.HoldEditorUIModel`. Add `<script src="editor-ui-model.js"></script>` after `editor-interaction-model.js` and before `app.js`.

- [ ] **Step 4: Run the new model test and existing UI tests**

Run: `node --test Tools/HangboardWorkbench/tests/workbench_editor_ui_model.test.js Tools/HangboardWorkbench/tests/editor_ui.test.js`

Expected: PASS, including the existing geometry-editor tests.

- [ ] **Step 5: Commit and push the model**

```bash
git add Tools/HangboardWorkbench/editor-ui-model.js Tools/HangboardWorkbench/tests/workbench_editor_ui_model.test.js Tools/HangboardWorkbench/index.html
git commit -m "feat: model contextual hold editor tools"
git push origin simplify-board-editor
```

### Task 2: Replace the suite shell with a focused editor shell

**Files:**
- Modify: `Tools/HangboardWorkbench/index.html:78-353`
- Modify: `Tools/HangboardWorkbench/styles.css:28-180, 435-520`
- Modify: `Tools/HangboardWorkbench/tests/workbench_app.test.js:22-113`

**Interfaces:**
- Consumes: existing element IDs used by direct editor controls in `app.js`, including `board-select`, `undo-button`, `redo-button`, `save-state`, `save-button`, `region-list`, `canvas-viewport`, and `inspector-panel`.
- Produces: `advanced-tools-toggle`, four `.advanced-tool-group` elements (`advanced-outline-tools`, `advanced-transform-tools`, `advanced-assist-tools`, `advanced-details-tools`), `more-actions`, and read-only Board details element IDs.
- Consumed by: Task 3 rendering and event binding.

- [ ] **Step 1: Write failing focused-shell assertions**

Replace the suite-navigation expectation in `workbench_app.test.js` with tests that demand the new visible contract:

```js
test("the workbench is a single focused hold-outline editor", () => {
  const ids = actualElementIds(markup);
  for (const id of [
    "board-select", "undo-button", "redo-button", "save-state", "save-button",
    "region-list", "canvas-viewport", "inspector-panel", "advanced-tools-toggle",
    "advanced-outline-tools", "advanced-transform-tools", "advanced-assist-tools",
    "advanced-details-tools", "more-actions", "board-details",
  ]) assert.equal(ids.has(id), true, `${id} must resolve to an element`);
  assert.doesNotMatch(markup, /tool-suite-sidebar|tool-onboard|tool-inspect|tool-promote|tool-validate/);
  assert.doesNotMatch(markup, />Promote to iOS<|>Validate</);
});
```

Add assertions that `snap-button`, `compare-button`, `export-button`, and `corrections-button` occur under `more-actions` or Advanced tools—not as direct children of `.toolbar`.

- [ ] **Step 2: Run the shell test to verify it fails**

Run: `node --test Tools/HangboardWorkbench/tests/workbench_app.test.js`

Expected: FAIL because the suite shell and persistent tool controls are still present.

- [ ] **Step 3: Implement the single-surface HTML and CSS**

In `index.html`:

1. Remove `suite-shell`, `tool-suite-sidebar`, `suite-content`, all `tool-view` sections other than the current onboarding workspace, and the Inspect/Promote/Validate markup.
2. Retain the workspace, canvas, validation panel, and the one existing inspector DOM node.
3. Keep the header’s board selector, undo, redo, save state, and save button. Add a native `<details id="board-details" class="board-details">` with active board name, canonical ID, and revision as read-only text nodes.
4. Add native `<details id="more-actions" class="more-actions"><summary>More</summary>…</details>` and move Compare, Retry, Revise upstream, Export edited highlights, and Export corrections into it.
5. Keep Snap edges out of the header; move it into the Advanced Assists group.
6. Make Hold key, Hold type, point count, area, delete, and the `Advanced tools` button the only normal inspector content. Place the existing shape/path/tension/corner/simplify controls in `advanced-outline-tools`; duplicate/navigation help in `advanced-transform-tools`; snap/mirror controls in `advanced-assist-tools`; mode and notes in `advanced-details-tools`.

Use this required group structure, preserving the existing input/button IDs so the current handlers remain valid:

```html
<button id="advanced-tools-toggle" type="button" aria-expanded="false" aria-controls="advanced-tools">Advanced tools</button>
<div id="advanced-tools" class="advanced-tools hidden">
  <section id="advanced-outline-tools" class="advanced-tool-group hidden" aria-labelledby="advanced-outline-title">…</section>
  <section id="advanced-transform-tools" class="advanced-tool-group hidden" aria-labelledby="advanced-transform-title">…</section>
  <section id="advanced-assist-tools" class="advanced-tool-group hidden" aria-labelledby="advanced-assist-title">…</section>
  <section id="advanced-details-tools" class="advanced-tool-group hidden" aria-labelledby="advanced-details-title">…</section>
</div>
```

In `styles.css`, replace the 204px suite layout with `.suite-shell` removal and make the editor workspace fill the app below the top bar. Remove sidebar and inactive-tool layout rules. Style `more-actions` and `board-details` as anchored popovers, and Advanced groups as clear labelled sections with a small explanatory line. Preserve the existing 1,250px inspector drawer behavior.

- [ ] **Step 4: Run the focused-shell and geometry UI tests**

Run: `node --test Tools/HangboardWorkbench/tests/workbench_app.test.js Tools/HangboardWorkbench/tests/editor_ui.test.js`

Expected: PASS after updating only assertions made obsolete by the removed suite UI; existing direct vertex and curve tests remain green.

- [ ] **Step 5: Commit and push the shell**

```bash
git add Tools/HangboardWorkbench/index.html Tools/HangboardWorkbench/styles.css Tools/HangboardWorkbench/tests/workbench_app.test.js
git commit -m "feat: focus workbench on hold outlines"
git push origin simplify-board-editor
```

### Task 3: Wire contextual inspector state and retire suite-view wiring

**Files:**
- Modify: `Tools/HangboardWorkbench/app.js:1-210, 365-510, 760-830, 2002-2045, 3103-3179`
- Modify: `Tools/HangboardWorkbench/tests/editor_ui.test.js`
- Modify: `Tools/HangboardWorkbench/tests/workbench_app.test.js`

**Interfaces:**
- Consumes: `globalThis.HoldEditorUIModel.advancedToolVisibility`, the preserved existing control IDs, `state.board`, `state.editorMode`, `state.imagePixels`, and `canEditGeometry()`.
- Produces: `state.advancedToolsOpen`, `setAdvancedToolsOpen(open)`, `renderBoardDetails()`, and contextual group visibility from `renderInspector()`.
- Removes: `HoldWorkbenchSuiteModel`, `HoldWorkbenchSuiteController`, `HoldPromotionView`, and `HoldValidationView` imports and all app-shell rendering/event wiring for their views.

- [ ] **Step 1: Write failing behavior/wiring assertions**

Add these assertions to `editor_ui.test.js` and `workbench_app.test.js`:

```js
test("the inspector keeps direct correction controls visible while Advanced tools are closed", () => {
  assert.match(app, /advancedToolsOpen: false/);
  assert.match(app, /function setAdvancedToolsOpen\(open\)/);
  assert.match(app, /advancedToolVisibility\(\{[\s\S]*region,[\s\S]*editorMode: state\.editorMode/);
  assert.match(app, /advanced-tools"\]\.classList\.toggle\("hidden", !state\.advancedToolsOpen \|\| !region\)/);
});

test("the focused app no longer initializes suite, promotion, or validation views", () => {
  assert.doesNotMatch(app, /createToolSuiteController|createPromotionController|createValidationController/);
  assert.doesNotMatch(app, /renderSuite\(|renderPromotionView|renderValidationView/);
});
```

- [ ] **Step 2: Run the UI tests to verify they fail**

Run: `node --test Tools/HangboardWorkbench/tests/editor_ui.test.js Tools/HangboardWorkbench/tests/workbench_app.test.js`

Expected: FAIL because the application still imports and initializes the suite controllers and has no Advanced tools state.

- [ ] **Step 3: Implement the minimal state and rendering changes**

1. Destructure `advancedToolVisibility` from `globalThis.HoldEditorUIModel`; remove suite/promotion/validation destructuring and controller variables.
2. Replace `state.suiteState` with `advancedToolsOpen: false`; include all new HTML IDs in `el`.
3. Remove `renderSuite()` and `renderInspectView()` and stop calling `renderSuite()` from `render()`. Add `renderBoardDetails()` that sets the three read-only values from `state.board` with empty-state fallback text.
4. In `loadCheckpoint()`, remove `suiteController?.setBoard(view)`, retain `state.board = view`, and reset `advancedToolsOpen` to `false` whenever the board/revision changes.
5. At the start of `renderInspector()`, call the model with the current selection, mode, editability, and pixel availability. Hide `advanced-tools` unless both `state.advancedToolsOpen` and a region exist; hide each group according to the returned visibility; independently hide Snap edges according to `edgeSnap`.
6. Add `setAdvancedToolsOpen(open)` that refuses to open without a selected region, updates `aria-expanded`, and calls `renderInspector()` and `renderToolState()`. Bind `advanced-tools-toggle` click to its inverse. In `selectRegion()`, reset the drawer closed when selection changes or clears.
7. Keep the existing handlers for shape, curve, tension, corner, mode, notes, snap, mirror, compare, retry, revise, and exports; bind no tool-suite navigation. Existing More controls keep their exact behavior.
8. Initialize only the existing opening-board and autosave paths; remove the script dependencies from `index.html` for `workbench-suite-model.js`, `workbench-suite-controller.js`, `promotion-view.js`, and `validation-view.js`. Leave their standalone source and tests in place so developer workflows are not deleted as part of the UI simplification.

- [ ] **Step 4: Run the focused Node test suite**

Run: `node --test Tools/HangboardWorkbench/tests/workbench*.test.js Tools/HangboardWorkbench/tests/editor_ui.test.js`

Expected: PASS. The existing suite-model/controller tests may remain because their independent modules remain supported, while the browser shell is verified not to initialize them.

- [ ] **Step 5: Commit and push the application wiring**

```bash
git add Tools/HangboardWorkbench/app.js Tools/HangboardWorkbench/index.html Tools/HangboardWorkbench/tests/editor_ui.test.js Tools/HangboardWorkbench/tests/workbench_app.test.js
git commit -m "feat: contextualize hold editor expert tools"
git push origin simplify-board-editor
```

### Task 4: Document and verify the streamlined operator workflow

**Files:**
- Modify: `Tools/HangboardWorkbench/README.md:52-130`
- Modify: `Tools/HangboardWorkbench/tests/workbench_app.test.js`

**Interfaces:**
- Consumes: the completed single-surface editor contract from Tasks 1–3.
- Produces: accurate operator-facing instructions for selecting a board, editing an outline directly, revealing Advanced tools, using More, and saving locally.

- [ ] **Step 1: Write the failing documentation/markup regression assertion**

Add a test that protects the new task model in the main editor markup:

```js
test("the main editor copy explains direct outlining without pipeline terminology", () => {
  const onboard = markup.match(/<section class="workspace-grid"[\s\S]*?<\/section>\s*<\/main>/);
  assert.ok(onboard);
  assert.match(onboard[0], /Edit holds/);
  assert.doesNotMatch(onboard[0], /Stage [0-9]|checkpoint|Promote to iOS|>Validate</);
});
```

- [ ] **Step 2: Run the regression test to verify it fails**

Run: `node --test Tools/HangboardWorkbench/tests/workbench_app.test.js`

Expected: FAIL until the suite/lifecycle copy is fully removed from the main editor markup.

- [ ] **Step 3: Update the README and finish copy cleanup**

Replace the “Run the single-board tool suite” section with a concise “Correct hold outlines” section that says:

1. Choose a board.
2. Click a detected hold and drag its outline points on the image.
3. Add a highlight only when detection missed one; delete one when it is wrong.
4. Open **Advanced tools** only for shape, curve, transform, edge snap, mirror, and metadata work.
5. Use **More** for comparison or artifact exports.
6. Save locally; saving does not commit, push, or synchronize changes.

Keep the later developer workflow material, but label it as command-line/developer use rather than part of the editor’s main task. Ensure the main HTML labels use “outline,” “hold,” “Advanced tools,” and “More,” rather than stage/checkpoint terms.

- [ ] **Step 4: Run complete automated verification**

Run:

```bash
node --test Tools/HangboardWorkbench/tests/workbench*.test.js Tools/HangboardWorkbench/tests/editor_ui.test.js
rtk python3 -m pytest Tools/HangboardWorkbench/tests -q
```

Expected: both commands exit 0. The Node suite proves the browser shell and interaction model; the Python suite proves server and packaging behavior remain intact.

- [ ] **Step 5: Manually verify one auto-detected board**

Run: `rtk python3 Tools/HangboardWorkbench/server.py`

Open the local workbench and verify: select a repository or in-progress board; select and drag a freeform vertex with Advanced tools closed; open Advanced tools and use one applicable control; use More to toggle Compare; save; refresh; and confirm the corrected outline reloads. Stop the server with `Ctrl-C` after the check.

- [ ] **Step 6: Commit and push the documentation and final regression coverage**

```bash
git add Tools/HangboardWorkbench/README.md Tools/HangboardWorkbench/tests/workbench_app.test.js
git commit -m "docs: explain focused hold outlining workflow"
git push origin simplify-board-editor
```

## Plan Self-Review

### Spec coverage

- Single `Edit holds` surface and no workflow sidebar: Task 2 and Task 3.
- Direct canvas correction as the default: Task 2 markup and Task 4 manual verification.
- Expert tools retained, grouped, contextual, and initially closed: Tasks 1–3.
- Board context and local-save boundary: Task 2 header/Board details and Task 4 documentation.
- More menu for compare/export and preserved lifecycle behavior: Tasks 2–3.
- Existing persistence and geometry behavior: Task 3 retains existing handlers; Task 4 runs Node/Python regression suites and manual save/reload verification.

### Placeholder and consistency check

The plan names every added public function, element ID, test file, command, and commit. `advancedToolVisibility` is the only new UI-model interface and its signature matches all consuming steps. No requirements are deferred outside the listed tasks.
