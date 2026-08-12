# Workbench Drawer, Direct Editing, and Trackpad Navigation Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development for every implementation task, with a fresh subagent and a review checkpoint before commit. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Keep the inspector accessible through a responsive drawer, make the editor a single **Edit holds** experience, and support two-finger trackpad pan without losing pinch zoom.

**Architecture:** Keep one inspector form and switch only its responsive presentation: a normal third grid column on wide windows and an accessible fixed drawer at 1,250px and below. Put wheel classification in a dependency-free interaction-model module so Node tests prove pan versus cursor-anchored zoom intent; `app.js` owns DOM state, focus, and rendering. Existing geometry data and backend stages remain unchanged while the editor hides their terminology and gives selected freeforms direct vertex controls.

**Tech Stack:** Vanilla HTML/CSS/JavaScript, Node built-in test runner, Python 3.11+ pytest.

## Global Constraints

- At `max-width: 1250px`, use a two-column workspace (`250px minmax(0, 1fr)`) plus an off-canvas right inspector drawer; do not hide or duplicate the inspector.
- Above 1,250px, keep the normal three-column inspector layout.
- The drawer must have an opener, close button, backdrop close, `role="dialog"`, `aria-modal="true"`, focus trap, Escape close, and opener-focus restoration.
- Every viewport wheel event calls `preventDefault()`; only `ctrlKey` zooms and non-`ctrlKey` pans by both deltas.
- The visible editor has one step named `Edit holds`; do not show stage, checkpoint, hold-contour refinement, smoothing, or vector refinement copy there.
- Freeform vertices are directly editable by default and are not scale-locked; primitive non-freeforms retain bounding-box resize controls.
- Delete/Backspace removes a targeted freeform vertex only when at least three
  vertices remain; otherwise it deletes the selected hold.
- Escape must cancel an active operation before closing the drawer or deselecting a hold.
- Board info owns manufacturer, display name, subtitle/product context,
  dimensions, aspect ratio, and product/source URL; Promotion has no editable
  metadata or iOS board-ID field and derives `boardID` from canonical `boardId`.
- Do not infer Board info from images, geometry, or model values; absent
  source-backed metadata remains absent and blocks promotion.
- Do not change geometry artifact schemas, pipeline execution, or add third-party dependencies.

---

### Task 1: Specify and implement deterministic viewport interaction decisions

**Files:**

- Create: `Tools/hold-highlight-editor/editor-interaction-model.js`
- Modify: `Tools/hold-highlight-editor/index.html`
- Modify: `Tools/hold-highlight-editor/app.js`
- Test: `Tools/hold-highlight-editor/tests/editor_interaction_model.test.js`
- Test: `Tools/hold-highlight-editor/tests/editor_ui.test.js`

**Interfaces:**

- Produces: `globalThis.HoldEditorInteractionModel.viewportWheelAction({ ctrlKey: boolean, deltaX: number, deltaY: number }): { kind: "pan", deltaX: number, deltaY: number } | { kind: "zoom", scale: number }`.
- Consumes: the listener event's `ctrlKey`, `deltaX`, `deltaY`, `clientX`, and `clientY`; existing `state.panX`, `state.panY`, `state.zoom`, `renderTransform()`, and `setZoom()`.

- [ ] **Step 1: Write failing wheel-decision tests**

Create `Tools/hold-highlight-editor/tests/editor_interaction_model.test.js`:

```js
const test = require("node:test");
const assert = require("node:assert/strict");
const { viewportWheelAction } = require("../editor-interaction-model.js");

test("normal trackpad wheel input pans by both deltas", () => {
  assert.deepEqual(
    viewportWheelAction({ ctrlKey: false, deltaX: 18, deltaY: -24 }),
    { kind: "pan", deltaX: 18, deltaY: -24 },
  );
});

test("ctrl wheel input preserves exponential pinch zoom semantics", () => {
  const action = viewportWheelAction({ ctrlKey: true, deltaX: 18, deltaY: 120 });
  assert.equal(action.kind, "zoom");
  assert.equal(action.scale, Math.exp(-120 * 0.0012));
});
```

Append a source-contract test to `editor_ui.test.js` that requires the new
script to load between `curve-gesture-model.js` and `app.js`, requires the
non-passive wheel listener to call `event.preventDefault()`, and checks that
the `pan` branch updates both `state.panX` and `state.panY` while the `zoom`
branch calls `setZoom(..., event.clientX, event.clientY)`.

- [ ] **Step 2: Run the focused tests and verify failure**

Run:

```bash
node --test Tools/hold-highlight-editor/tests/editor_interaction_model.test.js Tools/hold-highlight-editor/tests/editor_ui.test.js
```

Expected: FAIL because `editor-interaction-model.js` and its module export do
not exist, and `index.html` does not load it.

- [ ] **Step 3: Add the pure interaction model and wire the listener**

Create `editor-interaction-model.js` with this export pattern:

```js
(() => {
  "use strict";
  function viewportWheelAction({ ctrlKey, deltaX, deltaY }) {
    return ctrlKey
      ? { kind: "zoom", scale: Math.exp(-deltaY * 0.0012) }
      : { kind: "pan", deltaX, deltaY };
  }
  const api = Object.freeze({ viewportWheelAction });
  globalThis.HoldEditorInteractionModel = api;
  if (typeof module !== "undefined") module.exports = api;
})();
```

Load it after `curve-gesture-model.js` and before `app.js`. In `app.js`,
destructure `viewportWheelAction` from `globalThis.HoldEditorInteractionModel`.
Replace the current viewport wheel listener with a non-passive listener that
always prevents default, classifies the event, calls
`setZoom(state.zoom * action.scale, event.clientX, event.clientY)` for zoom,
and otherwise performs:

```js
state.panX -= action.deltaX;
state.panY -= action.deltaY;
renderTransform();
```

- [ ] **Step 4: Run focused tests and verify success**

Run:

```bash
node --test Tools/hold-highlight-editor/tests/editor_interaction_model.test.js Tools/hold-highlight-editor/tests/editor_ui.test.js
```

Expected: PASS. Normal wheels classify as pan, pinch wheels classify as zoom,
and the page script/listener contract is present.

- [ ] **Step 5: Commit Task 1**

```bash
git add Tools/hold-highlight-editor/editor-interaction-model.js Tools/hold-highlight-editor/index.html Tools/hold-highlight-editor/app.js Tools/hold-highlight-editor/tests/editor_interaction_model.test.js Tools/hold-highlight-editor/tests/editor_ui.test.js
git commit -m "feat: pan hold canvas with trackpad"
git push
```

### Task 2: Add the responsive, accessible single-DOM inspector drawer

**Files:**

- Modify: `Tools/hold-highlight-editor/index.html`
- Modify: `Tools/hold-highlight-editor/styles.css`
- Modify: `Tools/hold-highlight-editor/app.js`
- Test: `Tools/hold-highlight-editor/tests/workbench_app.test.js`
- Test: `Tools/hold-highlight-editor/tests/editor_ui.test.js`

**Interfaces:**

- Produces: `state.inspectorDrawerOpen: boolean`, `openInspectorDrawer(): void`, `closeInspectorDrawer({ restoreFocus: boolean }): void`, and `trapInspectorDrawerFocus(event: KeyboardEvent): void`.
- Consumes: elements `inspector-drawer-toggle`, `inspector-drawer-close`, `inspector-drawer-backdrop`, `inspector-panel`, and existing `inspector-title`.

- [ ] **Step 1: Write failing drawer markup, CSS, and keyboard-contract tests**

In `workbench_app.test.js`, add a test asserting that the real page has exactly
one each of `inspector-panel`, `inspector-drawer-toggle`,
`inspector-drawer-close`, and `inspector-drawer-backdrop`; that the panel has
`role="dialog"`, `aria-modal="true"`, and `aria-labelledby="inspector-title"`;
and that the toggle starts with `aria-expanded="false"` and controls the panel.

In `editor_ui.test.js`, add a test that reads `styles.css` and `app.js` and
asserts all of:

```js
assert.match(css, /@media \(max-width: 1250px\)[\s\S]*\.workspace-grid \{ grid-template-columns: 250px minmax\(0, 1fr\); \}/);
assert.match(css, /\.inspector-panel\.drawer-open/);
assert.doesNotMatch(css, /@media \(max-width: 980px\)[\s\S]*\.inspector-panel \{ display: none; \}/);
assert.match(app, /function openInspectorDrawer\(\)/);
assert.match(app, /function closeInspectorDrawer\(\{ restoreFocus = true \} = \{\}\)/);
assert.match(app, /function trapInspectorDrawerFocus\(event\)/);
```

Also assert that Escape calls drawer close before the no-active-operation
selection-clear branch, and that the toggle updates `aria-expanded`.

- [ ] **Step 2: Run focused tests and verify failure**

Run:

```bash
node --test Tools/hold-highlight-editor/tests/workbench_app.test.js Tools/hold-highlight-editor/tests/editor_ui.test.js
```

Expected: FAIL because drawer controls, responsive drawer rules, and the
drawer focus functions do not exist.

- [ ] **Step 3: Implement the drawer without duplicating the inspector**

Add the toggle to the editor toolbar/canvas actions and the backdrop adjacent
to the existing inspector. Add the close button as the first focusable child
of the existing `.inspector-panel`; preserve all current inspector form IDs.
Add every new ID once to `el`.

Initialize `state.inspectorDrawerOpen` to `false` and retain the opener in
`state.inspectorDrawerOpener`. `openInspectorDrawer()` records the opener,
adds `.drawer-open` to the panel and backdrop, sets toggle
`aria-expanded="true"`, and focuses the close control. `closeInspectorDrawer`
removes those classes, sets `aria-expanded="false"`, and restores focus when
requested. Backdrop and close clicks call close. On narrow layouts, Tab and
Shift+Tab cycle through focusable controls in the panel; on wide layouts the
drawer code is inert. `matchMedia("(max-width: 1250px)")` closes a drawer that
is open when resizing to the normal three-column layout.

At the 1,250px media query, set the workspace to the required two columns and
make the inspector fixed, right-anchored, translated off canvas by default,
and translated to zero with `.drawer-open`. Give the backdrop a fixed inset,
opacity/visibility state, and pointer events only while open. Remove the
980px `display: none` rule. Above the breakpoint, hide drawer-only controls
and retain the current inspector column behavior.

- [ ] **Step 4: Run focused tests and verify success**

Run:

```bash
node --test Tools/hold-highlight-editor/tests/workbench_app.test.js Tools/hold-highlight-editor/tests/editor_ui.test.js
```

Expected: PASS. The drawer has one inspector form, narrow layout does not hide
it, and keyboard/focus behavior is represented in application code.

- [ ] **Step 5: Commit Task 2**

```bash
git add Tools/hold-highlight-editor/index.html Tools/hold-highlight-editor/styles.css Tools/hold-highlight-editor/app.js Tools/hold-highlight-editor/tests/workbench_app.test.js Tools/hold-highlight-editor/tests/editor_ui.test.js
git commit -m "feat: add responsive hold inspector drawer"
git push
```

### Task 3: Make editing a single direct hold task with freeform vertices and Escape deselection

**Files:**

- Modify: `Tools/hold-highlight-editor/index.html`
- Modify: `Tools/hold-highlight-editor/styles.css`
- Modify: `Tools/hold-highlight-editor/app.js`
- Test: `Tools/hold-highlight-editor/tests/workbench_app.test.js`
- Test: `Tools/hold-highlight-editor/tests/editor_ui.test.js`

**Interfaces:**

- Produces: `isFreeformRegion(region): boolean`, `deleteSelectedFreeformVertex(): boolean`, and `clearSelection(): void` in `app.js`.
- Consumes: current `region.metadata.shapeKind`, `startHandleDrag(event, id, index)`, `selectRegion(null)`, gesture session state, and existing backend approval/autosave methods.

- [ ] **Step 1: Write failing direct-editing tests**

In `workbench_app.test.js`, assert the Onboard page includes `Edit holds` and
does not include the literal editor labels `Hold-contour refinement`,
`Smoothing`, or `Vector refinement`.

In `editor_ui.test.js`, add source tests requiring:

```js
assert.match(app, /function isFreeformRegion\(region\)/);
assert.match(app, /if \(isFreeformRegion\(region\)\) renderFreeformVertexHandles\(group, region\);/);
assert.match(app, /if \(!isFreeformRegion\(region\)\) renderObjectControls\(group, region\);/);
assert.match(app, /function clearSelection\(\) \{[\s\S]*selectRegion\(null\);/);
assert.match(app, /function deleteSelectedFreeformVertex\(\)/);
```

Add a VM keyboard-handler test with `drawing: false`, all gesture sessions
`null`, `inspectorDrawerOpen: false`, and a selected ID. Dispatch Escape and
assert it prevents default and calls `clearSelection()` exactly once. Add a
second case with `drawing: true` proving `cancelDraw()` runs and
`clearSelection()` does not.

Add direct helper tests proving a targeted four-point freeform removes only
the selected index, returns `true`, clears `selectedCornerIndex`, and records
`Deleted control point`; a three-point freeform, primitive, or missing target
returns `false` without mutation. Add keyboard cases proving Delete and
Backspace call this helper before `deleteSelected()`, and only a `false` result
falls through to selected-hold deletion.

- [ ] **Step 2: Run focused tests and verify failure**

Run:

```bash
node --test Tools/hold-highlight-editor/tests/workbench_app.test.js Tools/hold-highlight-editor/tests/editor_ui.test.js
```

Expected: FAIL because pipeline copy remains, freeform controls depend on
`state.editPoints`, and idle Escape does not clear selection.

- [ ] **Step 3: Implement one-step direct editing and Escape priority**

Replace the Pipeline/Recent visual block in `index.html` with an editor heading
whose user-visible task label is exactly `Edit holds`; retain recent-board
selection and hold inventory. Remove stage timeline DOM and the associated
`STAGE_LABELS`, `PIPELINE_TO_TIMELINE_STAGE`, `timelineView`, and
`renderGuidedShell` construction. Set the canvas header identity to `Edit
holds`, not checkpoint/stage copy. Replace the toolbar and status strings that
tell the editor user to approve/continue to neutral save/complete wording;
leave `workbenchClient.approve`, autosave, validation, and internal backend
state untouched.

Implement `isFreeformRegion(region)` as
`region.metadata?.shapeKind === "freeform"`. In selected contour rendering,
always add the existing vertex handles for a freeform and bind them to
`startHandleDrag`; do not call `renderObjectControls` for that region. Retain
object controls and resize sessions for all non-freeform primitive regions.
Remove the Edit points button/control-state presentation because it is no
longer a prerequisite for freeform vertices. Do not alter vector-mode handle
logic.

Implement `deleteSelectedFreeformVertex()` to return `false` unless the
selected region is a freeform, `selectedCornerIndex` is a valid contour index,
and `region.contour.length > 3`. On success, splice only that index, clear
`selectedCornerIndex`, commit `Deleted control point`, call `render()`, and
return `true`. In the Delete/Backspace branch call this helper first, then call
the existing `deleteSelected()` only if it returns `false`; preserve text-input
protection and existing vector behavior.

Implement `clearSelection()` by clearing selected ID/corner and calling
`render()`/status update. In the keydown listener order: cancel drawing;
finish/release any active pan, primitive, drag, handle, edge, or transform
session; close the narrow drawer if open; then, when a region is selected,
prevent default and call `clearSelection()`. Keep text-input protection after
the Escape branches so Escape remains available for cancellation/deselection.

- [ ] **Step 4: Run focused tests and verify success**

Run:

```bash
node --test Tools/hold-highlight-editor/tests/workbench_app.test.js Tools/hold-highlight-editor/tests/editor_ui.test.js
```

Expected: PASS. The visible editor language is single-step, freeform vertices
are direct, freeform point deletion preserves the three-point minimum,
primitive resize remains conditional, and Escape follows the required priority.

- [ ] **Step 5: Commit Task 3**

```bash
git add Tools/hold-highlight-editor/index.html Tools/hold-highlight-editor/styles.css Tools/hold-highlight-editor/app.js Tools/hold-highlight-editor/tests/workbench_app.test.js Tools/hold-highlight-editor/tests/editor_ui.test.js
git commit -m "feat: streamline direct hold editing"
git push
```

### Task 4: Move reusable board metadata out of iOS promotion

**Files:**

- Create: `Tools/hold-highlight-editor/board-info-view.js`
- Modify: `Tools/hold-highlight-editor/index.html`
- Modify: `Tools/hold-highlight-editor/app.js`
- Modify: `Tools/hold-highlight-editor/promotion-view.js`
- Modify: `Tools/hold-highlight-editor/workbench-client.js`
- Modify: `Tools/hold-highlight-editor/server.py`
- Modify: `Tools/HangboardOnboarding/hangboard_vectorizer/workbench.py`
- Modify: `Tools/HangboardOnboarding/hangboard_vectorizer/workbench_promotion.py`
- Test: `Tools/hold-highlight-editor/tests/board_info_view.test.js`
- Test: `Tools/hold-highlight-editor/tests/promotion_view.test.js`
- Test: `Tools/hold-highlight-editor/tests/workbench_client.test.js`
- Test: `Tools/hold-highlight-editor/tests/workbench_app.test.js`
- Test: `Tools/hold-highlight-editor/tests/test_server.py`
- Test: `Tools/HangboardOnboarding/tests/test_workbench_promotion.py`

**Interfaces:**

- Produces: `globalThis.HoldBoardInfoView.normalizedBoardInfo(value)`, `isBoardInfoComplete(value)`, and `promotionProfileForBoard(board, boardInfo)`.
- Produces: `GET/PUT /api/boards/:boardId/info?revisionId=:revisionId`; PUT accepts `{ boardId, expectedRevisionId, info }`, whose `info` contains exactly `manufacturer`, `name`, `subtitle`, `dimensions`, `aspectRatio`, and `productURL`.
- Consumes: `WorkbenchView.board_id` as the only promotion `boardID`; existing `IosPromotionProfile` receives the derived payload.

- [ ] **Step 1: Write failing Board info and derived-ID tests**

Create `Tools/hold-highlight-editor/tests/board_info_view.test.js`:

```js
const test = require("node:test");
const assert = require("node:assert/strict");
const { normalizedBoardInfo, promotionProfileForBoard } = require("../board-info-view.js");

test("board info trims sourced fields without inventing absent metadata", () => {
  assert.deepEqual(normalizedBoardInfo({ manufacturer: " Metolius ", name: "", subtitle: "", dimensions: "", aspectRatio: "", productURL: "" }), {
    manufacturer: "Metolius", name: "", subtitle: "", dimensions: "", aspectRatio: "", productURL: "",
  });
});

test("promotion derives board ID from the canonical active board", () => {
  assert.equal(promotionProfileForBoard(
    { boardId: "metolius.compact-ii" },
    { manufacturer: "Metolius", name: "Compact II", subtitle: "Wood board", dimensions: "24 × 6", aspectRatio: 4, productURL: "https://example.test" },
  ).boardID, "metolius.compact-ii");
});
```

In `promotion_view.test.js`, replace editable-profile fixtures with Board info
fixtures and assert preview receives a derived `boardID`; assert no public
promotion field accepts `boardID`. In `workbench_app.test.js`, assert Board
info fields occur in `inspect-view`, no field has `data-promotion-field`, and
`promotion-board-id` is absent. In `test_server.py`, assert that a mismatched
caller-supplied ID is rejected and the service accepts the canonical active
board ID derived server-side.

- [ ] **Step 2: Run focused tests and verify failure**

Run:

```bash
node --test Tools/hold-highlight-editor/tests/board_info_view.test.js Tools/hold-highlight-editor/tests/promotion_view.test.js Tools/hold-highlight-editor/tests/workbench_client.test.js Tools/hold-highlight-editor/tests/workbench_app.test.js
pytest Tools/hold-highlight-editor/tests/test_server.py -q
pytest Tools/HangboardOnboarding/tests/test_workbench_promotion.py -q
```

Expected: FAIL because Board info has no reusable view/API, promotion owns the
metadata fields, and `boardID` remains editable.

- [ ] **Step 3: Implement revision-bound Board info and consume it in promotion**

Create `board-info-view.js` with the six-field normalization/completeness and
`promotionProfileForBoard` derivation. Load it before `promotion-view.js`. Add
a Board info card to `inspect-view`: read-only canonical Board ID followed by
the six source-backed inputs and their existing evidence help text. Do not
prepopulate an empty field from a product image or any guessed value.

Add workbench service/store support to read and atomically save Board info
against the active revision, include it in the board-view payload, and add the
client get/save methods. The Inspect UI persists explicit edits. Update the
promotion controller to use the active board's Board info, derive the legacy
payload with `board.boardId`, and block preview with `Complete Board info before
generating an iOS preview.` when incomplete. Remove all profile inputs and
`promotion-board-id` from `promote-view`; retain preview, refresh, save, issues,
and diffs.

Update `profile_from_payload` so the route/service supplies canonical board ID
from the matched board, not request body. Preserve the downstream
`IosPromotionProfile` shape by constructing it from canonical ID and Board
info, reject mismatched/extra identity keys, and retain evidence and revision
checks.

- [ ] **Step 4: Run focused tests and verify success**

Run:

```bash
node --test Tools/hold-highlight-editor/tests/board_info_view.test.js Tools/hold-highlight-editor/tests/promotion_view.test.js Tools/hold-highlight-editor/tests/workbench_client.test.js Tools/hold-highlight-editor/tests/workbench_app.test.js
pytest Tools/hold-highlight-editor/tests/test_server.py -q
pytest Tools/HangboardOnboarding/tests/test_workbench_promotion.py -q
```

Expected: PASS. Board info is reusable and source-preserving, promotion derives
the canonical ID, and redundant promotion inputs are removed.

- [ ] **Step 5: Commit Task 4**

```bash
git add Tools/hold-highlight-editor/board-info-view.js Tools/hold-highlight-editor/index.html Tools/hold-highlight-editor/app.js Tools/hold-highlight-editor/promotion-view.js Tools/hold-highlight-editor/workbench-client.js Tools/hold-highlight-editor/server.py Tools/HangboardOnboarding/hangboard_vectorizer/workbench.py Tools/HangboardOnboarding/hangboard_vectorizer/workbench_promotion.py Tools/hold-highlight-editor/tests/board_info_view.test.js Tools/hold-highlight-editor/tests/promotion_view.test.js Tools/hold-highlight-editor/tests/workbench_client.test.js Tools/hold-highlight-editor/tests/workbench_app.test.js Tools/hold-highlight-editor/tests/test_server.py Tools/HangboardOnboarding/tests/test_workbench_promotion.py
git commit -m "feat: separate board info from promotion"
git push
```

### Task 5: Verify the complete workbench contract and responsive behavior

**Files:**

- Modify: `Tools/hold-highlight-editor/README.md`
- Test: `Tools/hold-highlight-editor/tests/test_server.py`
- Test: `Tools/hold-highlight-editor/tests/test_workbench_packaging.py`

**Interfaces:**

- Consumes: the script asset manifest and all production/editor tests from Tasks 1–4.
- Produces: user instructions accurately describing trackpad pan and the inspector drawer.

- [ ] **Step 1: Write the failing user-facing guidance test**

In `workbench_app.test.js`, add:

```js
test("documents responsive inspector and trackpad navigation", () => {
  assert.match(readme, /two-finger trackpad scroll pans the board/i);
  assert.match(readme, /pinch to zoom at the pointer/i);
  assert.match(readme, /inspector opens as a right drawer/i);
});
```

- [ ] **Step 2: Run the guidance test and verify failure**

Run:

```bash
node --test Tools/hold-highlight-editor/tests/workbench_app.test.js
```

Expected: FAIL because the README does not yet document the responsive editor
navigation behavior.

- [ ] **Step 3: Document and execute the complete verification suite**

In the guided-workbench section of `Tools/hold-highlight-editor/README.md`,
add this paragraph:

```markdown
At narrower desktop widths, use the Inspector button to open the selected
hold's details in a right drawer. Two-finger trackpad scroll pans the board;
pinch to zoom at the pointer. Press Escape to cancel an active edit, close the
drawer, or clear the current hold selection.
```

Run:

```bash
node --test Tools/hold-highlight-editor/tests/*.test.js
pytest Tools/hold-highlight-editor/tests/test_server.py Tools/hold-highlight-editor/tests/test_workbench_packaging.py Tools/hold-highlight-editor/tests/test_workbench_binary.py -q
```

Expected: PASS. Node confirms editor markup, interactions, and workbench
contracts; pytest confirms served and packaged assets remain valid.

Then manually validate with:

```bash
rtk python3 Tools/hold-highlight-editor/server.py
```

Open `http://127.0.0.1:4173` at 1,250px width or less, select a board, open
and close Inspector with keyboard and backdrop, pan with two fingers, pinch to
zoom, select a freeform hold, move and delete one vertex, and press Escape
while idle. In Inspect, save only source-backed Board info and confirm Promote
uses that data without an editable board ID.
Stop the server with Ctrl-C after validation.

- [ ] **Step 4: Commit Task 5**

```bash
git add Tools/hold-highlight-editor/README.md Tools/hold-highlight-editor/tests/workbench_app.test.js
git commit -m "docs: explain responsive hold editor navigation"
git push
```

## Self-Review

- Spec coverage: Tasks 1–2 implement and test trackpad behavior and a
  persistent accessible inspector drawer; Task 3 covers one-step copy,
  freeform vertices, point deletion, and Escape priority; Task 4 separates
  Board info from promotion; Task 5 verifies/documentation.
- Placeholder scan: all files, exported interfaces, assertions, commands,
  breakpoint values, and commit commands are explicit.
- Type consistency: `viewportWheelAction` uses the same action names in tests
  and app wiring; drawer IDs/state/functions and freeform helper names are
  identical across tasks.
