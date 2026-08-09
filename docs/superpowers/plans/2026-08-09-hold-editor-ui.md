# Hold Editor UI Implementation Plan

> **For agentic workers:** REQUIRED WORKFLOW: For every task in this plan, dispatch a fresh subagent and use superpowers:subagent-driven-development, including implementation and review checkpoints. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Reframe the existing onboarding browser UI as a single-screen, full-feature Hold Editor for editing, adding, and deleting typed hold highlights.

**Architecture:** Keep the existing dependency-free HTML/CSS/vanilla-JavaScript editor, normalized region model, catalog server, and artifact contracts. Make the server-loaded session the primary experience, hide manual file-loading controls while a server catalog is active, and rewrite visible copy around hold highlights while preserving the full inspector and geometry tools.

**Tech Stack:** Static HTML, CSS, vanilla JavaScript, Node's built-in test runner, Python standard-library HTTP server, pytest.

## Global Constraints

- The editor remains a complete hold-level authoring tool; simplification removes the staged onboarding workflow from the UI, not hold metadata or geometry capabilities.
- Adding a new highlight must retain hold-type choice: jug, sloper, edge, or pocket.
- Deleting an existing highlight remains available and undoable.
- The existing region document schema and save API remain unchanged.
- Product identities and artifact locations remain run data, never product-specific editor code.
- Generated Stage 1 and automatic Stage 2 artifacts remain read-only.
- Static file-loading support remains available as a fallback for offline/manual use.
- The UI and documentation must describe a Hold Editor and hold-highlight editing, not a staged onboarding wizard.

---

### Task 1: Rename and simplify the editor surface

**Files:**
- Modify: `Tools/hold-highlight-editor/index.html`
- Modify: `Tools/hold-highlight-editor/styles.css`
- Test: `Tools/hold-highlight-editor/tests/editor_ui.test.js`

**Interfaces:**
- Consumes: existing element IDs used by `Tools/hold-highlight-editor/app.js`.
- Produces: a single-screen Hold Editor surface with accessible labels for the board selector, hold inventory, add-highlight control, full inspector, delete action, and static-only loading controls.

- [ ] **Step 1: Write failing source-level UI tests**

Create `Tools/hold-highlight-editor/tests/editor_ui.test.js` using `node:test`, `node:assert/strict`, `node:fs`, and `node:path`. Define shared fixtures at the top of the file:

```js
const root = path.join(__dirname, "..");
const index = fs.readFileSync(path.join(root, "index.html"), "utf8");
const app = fs.readFileSync(path.join(root, "app.js"), "utf8");
const readme = fs.readFileSync(path.join(root, "README.md"), "utf8");
```

Read `../index.html` as UTF-8 and assert the following exact behaviors:

```js
test("brands the workspace as a Hold Editor", () => {
  assert.match(index, /<title>Hold Editor<\/title>/);
  assert.match(index, /<h1>Hold Editor<\/h1>/);
  assert.doesNotMatch(index, /Hold Region Editor/);
  assert.match(index, /Edit and save hold highlights/);
});

test("keeps full hold editing controls", () => {
  assert.match(index, /id="new-shape-select"/);
  assert.match(index, /id="region-type-select"/);
  assert.match(index, /value="jug"/);
  assert.match(index, /value="sloper"/);
  assert.match(index, /value="edge"/);
  assert.match(index, /value="pocket"/);
  assert.match(index, /id="add-region-button"/);
  assert.match(index, /id="delete-button"/);
});

test("marks manual file loading as a static fallback", () => {
  assert.match(index, /id="static-load-controls"/);
  assert.match(index, /id="load-image-button"/);
  assert.match(index, /id="load-regions-button"/);
});
```

- [ ] **Step 2: Run the new UI tests and verify the intended failure**

Run:

```bash
rtk node --test Tools/hold-highlight-editor/tests/editor_ui.test.js
```

Expected: the test fails because the current title/copy and static fallback wrapper do not match the new Hold Editor surface.

- [ ] **Step 3: Update the HTML surface**

In `index.html`:

1. Change the document title and brand heading to `Hold Editor`.
2. Change the brand description to `Edit and save hold highlights.`.
3. Wrap the existing Load image and Load regions buttons in an element with `id="static-load-controls"` and a class that can be hidden while a server session is active. Keep both existing button IDs unchanged for `app.js`.
4. Change the inventory eyebrow/heading and list label from grip/region wording to `Hold highlights` while keeping `region-list` and `region-count` IDs.
5. Change the add-row select label to `New highlight shape` and the button’s accessible/name copy to `Add highlight`; keep `new-shape-select` and `add-region-button` IDs.
6. Change the canvas SVG accessible label to `Hangboard hold highlight editor`.
7. Change the empty inspector copy to tell the user to select a hold highlight to edit its shape and details.
8. Change the inspector title label from `Region key` to `Hold key`, the interaction copy to hold terminology, and the destructive button text to `Delete highlight`; keep all IDs and the four existing type options.

Do not remove the full geometry, type, shape, path style, interaction mode, notes, metrics, or inspector action controls.

- [ ] **Step 4: Add static/server visibility styles**

In `styles.css`, add a selector for the static fallback wrapper that follows the existing `.hidden` behavior, for example:

```css
#static-load-controls { display: flex; align-items: center; gap: 7px; }
#static-load-controls.hidden { display: none; }
```

Keep the existing toolbar and three-pane layout intact. Do not hide the inspector on desktop or remove the mobile breakpoint behavior.

- [ ] **Step 5: Run the UI tests and inspect the diff**

Run:

```bash
rtk node --test Tools/hold-highlight-editor/tests/editor_ui.test.js
rtk git diff --check
```

Expected: the UI tests pass and `git diff --check` reports no whitespace errors.

- [ ] **Step 6: Commit the surface change**

```bash
rtk git add Tools/hold-highlight-editor/index.html Tools/hold-highlight-editor/styles.css Tools/hold-highlight-editor/tests/editor_ui.test.js
rtk git commit -m "feat: rebrand hold highlight editor surface"
```

### Task 2: Make server sessions feel like direct Hold Editor sessions

**Files:**
- Modify: `Tools/hold-highlight-editor/app.js`
- Test: `Tools/hold-highlight-editor/tests/editor_ui.test.js`

**Interfaces:**
- Consumes: the `static-load-controls` element and unchanged editor element IDs from Task 1.
- Produces: `showStaticLoadControls(visible)` behavior that hides manual file loading for server-loaded sessions and restores it for static fallback; hold-oriented status and inspector copy without changing document payloads.

- [ ] **Step 1: Extend the failing UI test with app behavior contracts**

Append tests that read `../app.js` and assert the app owns the static fallback visibility and uses hold-oriented copy:

```js
test("switches between server-first and static fallback entry states", () => {
  assert.match(app, /function showStaticLoadControls\(visible\)/);
  assert.match(app, /static-load-controls/);
  assert.match(app, /showStaticLoadControls\(false\)/);
  assert.match(app, /showStaticLoadControls\(true\)/);
});

test("uses hold language for selection and editing status", () => {
  assert.match(app, /Hold \$\{region\.id\}/);
  assert.match(app, /Added \$\{region\.key\}/);
  assert.match(app, /Deleted \$\{region\.key\}/);
  assert.doesNotMatch(app, /Select a region to edit its shape and metadata/);
});
```

- [ ] **Step 2: Run the extended UI tests and verify the intended failure**

Run:

```bash
rtk node --test Tools/hold-highlight-editor/tests/editor_ui.test.js
```

Expected: the new app-contract assertions fail because `showStaticLoadControls` does not exist and current status messages use region terminology.

- [ ] **Step 3: Add server/static fallback visibility state**

Add `static-load-controls` to the `el` lookup and implement:

```js
function showStaticLoadControls(visible) {
  el["static-load-controls"].classList.toggle("hidden", !visible);
}
```

Update the session transitions as follows:

- In `loadInitialSession`, after a successful `loadServerCatalog()`, keep the static controls hidden; when server loading falls back to demo/static mode, show them.
- In `loadImageFile` and `loadRegionsFile`, show the static controls after clearing `serverSession` so manual editing remains discoverable.
- In a successful `loadServerSession`, keep the static controls hidden and preserve the existing board-selector/save-state behavior.
- Do not change the server URLs, selected run ID, confirmation dialog, or artifact payloads.

- [ ] **Step 4: Rewrite runtime copy around hold highlights**

Update only user-visible wording in `app.js`, preserving IDs, state names, and behavior:

- `renderInspector`: use `Hold ${region.id}` and `Select a hold highlight to edit its shape and details.`.
- `beginDraw`, `finishDraw`, `deleteSelected`, duplicate/mirror actions, and draw error messages should say highlight/hold rather than region where they describe the user’s action.
- `setRegions`, `loadDemo`, and server-session messages should say loaded/selected/edited hold highlights rather than describe a staged onboarding sequence.
- `saveToRun` should say it saved edited highlights/corrections while retaining the actual returned artifact paths.
- Keep internal `region` terminology in model keys, element IDs, payload fields, and server API names; this is a copy-only refactor.

- [ ] **Step 5: Run focused tests and the existing model suite**

Run:

```bash
rtk node --test Tools/hold-highlight-editor/tests/editor_ui.test.js Tools/hold-highlight-editor/tests/editor_model.test.js
```

Expected: all UI contract and existing editor-model tests pass.

- [ ] **Step 6: Commit the session/copy change**

```bash
rtk git add Tools/hold-highlight-editor/app.js Tools/hold-highlight-editor/tests/editor_ui.test.js
rtk git commit -m "feat: make hold editor server-first"
```

### Task 3: Align documentation and perform end-to-end verification

**Files:**
- Modify: `Tools/hold-highlight-editor/README.md`
- Modify: `Tools/hold-highlight-editor/index.html`
- Modify: `Tools/hold-highlight-editor/server.py`
- Test: `Tools/hold-highlight-editor/tests/editor_ui.test.js`

**Interfaces:**
- Consumes: the completed single-screen Hold Editor UI and existing server/catalog behavior.
- Produces: documentation whose workflow matches the UI and a verified editor branch with no changes to generated artifacts.

- [ ] **Step 1: Write a failing documentation assertion**

Add a test using the shared `readme` fixture and assert:

```js
test("documents the direct hold-highlight workflow", () => {
  assert.match(readme, /^# Hold Editor/m);
  assert.match(readme, /choose a board.*edit.*add.*delete.*save/is);
  assert.match(readme, /hold type/i);
  assert.doesNotMatch(readme, /# Hold Region Editor/);
});
```

- [ ] **Step 2: Run the documentation test and verify it fails**

Run:

```bash
rtk node --test Tools/hold-highlight-editor/tests/editor_ui.test.js
```

Expected: the README assertions fail against the current `Hold Region Editor` title and workflow wording.

- [ ] **Step 3: Rewrite the editor README**

Update `Tools/hold-highlight-editor/README.md` to:

1. Use `# Hold Editor` as the title.
2. Explain the direct workflow: choose a board/run, edit existing highlights, add a new highlight and choose its type, delete incorrect highlights, then save/export.
3. Keep the current server launch, catalog, static fallback, artifact-output, geometry, shortcut, and safety details.
4. Replace language that presents Stage 1/Stage 2 as user-facing steps with language that identifies them as generated input artifacts. Keep exact artifact filenames where they are part of the server contract.
5. State that the full inspector retains hold key, type, shape, path style, interaction mode, and review notes.
6. Change the visible add button label to `Add highlight` while preserving its existing ID and click behavior.
7. Change the server’s user-facing startup/error labels from `Hold Region Editor` to `Hold Editor`; preserve the CLI command, routes, artifact paths, and error behavior.

- [ ] **Step 4: Run focused and repository tests**

Run:

```bash
rtk node --test Tools/hold-highlight-editor/tests/editor_ui.test.js Tools/hold-highlight-editor/tests/editor_model.test.js
rtk pytest Tools/hold-highlight-editor/tests/test_server.py -q
rtk git diff --check
```

Expected: every test passes, pytest reports zero failures, and the diff check is clean.

- [ ] **Step 5: Perform a source-level acceptance review**

Confirm all of the following against the final files:

- `index.html` has one Hold Editor workspace, not a stage/wizard control.
- The type selector still exposes jug, sloper, edge, and pocket.
- Add and delete controls remain present.
- The full inspector and geometry actions remain present.
- Server mode hides manual image/region loading while static fallback restores it.
- Save, export, board switching, dirty-state confirmation, and correction payloads are untouched.
- Only the intended editor files plus the design/plan docs changed; pre-existing unrelated working-tree edits are not staged.

- [ ] **Step 6: Commit documentation and final verification changes**

```bash
rtk git add Tools/hold-highlight-editor/README.md Tools/hold-highlight-editor/tests/editor_ui.test.js
rtk git commit -m "docs: describe direct hold editor workflow"
```
