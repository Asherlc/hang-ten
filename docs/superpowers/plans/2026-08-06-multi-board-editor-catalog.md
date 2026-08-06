# Multi-board Hold Editor Catalog Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Let reviewers select and edit any pipeline-generated hangboard run in one hold-region editor.

**Architecture:** Normalize standard run directories and catalog entries into an immutable `EditorCatalog`. Every HTTP request selects a session by opaque ID, while the browser keeps the selected ID and includes it in artifact and save URLs.

**Tech Stack:** Python standard-library HTTP server, vanilla JavaScript, SVG, pytest, Node test runner.

## Global Constraints

- Product identities and artifact locations are run data, never product-specific editor code.
- Artifact paths must remain inside their configured run root.
- Auto-generated Stage 1 and Stage 2 artifacts are read-only.
- Save writes the standard edited-regions and human-corrections files atomically beside Stage 2.
- Existing single-run `--run-dir` usage remains compatible.

---

### Task 1: Server-side run catalog

**Files:**
- Modify: `Tools/hold-highlight-editor/server.py`
- Test: `Tools/hold-highlight-editor/tests/test_server.py`

**Interfaces:**
- Produces: `CatalogSession(id, label, session)`, `EditorCatalog(sessions)`, and `load_catalog(path)`.
- Produces: `EditorCatalog.get(run_id)` where missing IDs select the default and unknown IDs raise `EditorError`.
- Consumes: existing `EditorSession`, `discover_session`, and `save_review`.

- [ ] **Step 1: Write failing catalog tests**

Add tests that construct two runs, assert stable distinct opaque IDs and labels, load explicit relative artifacts from a catalog JSON file, reject escaping paths, and preserve one-run discovery.

- [ ] **Step 2: Verify the tests fail**

Run: `rtk pytest Tools/hold-highlight-editor/tests/test_server.py -q`

- [ ] **Step 3: Implement catalog normalization and validation**

Add frozen catalog dataclasses, deterministic IDs derived from entry order and label, confined explicit artifact resolution, and JSON parsing for:

```json
{"runs":[{"label":"Board label","runDir":"/pipeline/run","image":"stages/01/attempt-0001/stage-1-auto-rgba.png","regions":"stages/02/attempt-0001/stage-2-regions.json"}]}
```

Paths in `image` and `regions` are resolved relative to `runDir`; catalog-relative `runDir` values resolve relative to the catalog file.

- [ ] **Step 4: Verify catalog tests pass**

Run: `rtk pytest Tools/hold-highlight-editor/tests/test_server.py -q`

### Task 2: Run-selectable HTTP API and CLI

**Files:**
- Modify: `Tools/hold-highlight-editor/server.py`
- Modify: `Tools/hold-highlight-editor/README.md`
- Test: `Tools/hold-highlight-editor/tests/test_server.py`

**Interfaces:**
- Consumes: `EditorCatalog` from Task 1.
- Produces: `GET /api/sessions` and run-aware existing endpoints using `?run=<opaque-id>`.
- Produces: repeatable `--run-dir` plus optional `--catalog` CLI inputs.

- [ ] **Step 1: Write failing API routing tests**

Test that `/api/sessions` lists two safe summaries, each artifact endpoint returns its selected run, an unknown ID returns 404, save writes only beside the selected run, and unparameterized one-run requests still work.

- [ ] **Step 2: Verify the API tests fail**

Run: `rtk pytest Tools/hold-highlight-editor/tests/test_server.py -q`

- [ ] **Step 3: Implement stateless request selection**

Normalize `create_server(EditorSession | EditorCatalog)` to a catalog. Parse `run` with `parse_qs`, use it for session/image/regions/save handlers, and emit URLs containing `run=<id>`. Make `--run-dir` repeatable and allow `--catalog` to supply historical artifact layouts.

- [ ] **Step 4: Update usage documentation and verify**

Document single-run, repeated-run, and catalog invocations. Run: `rtk pytest Tools/hold-highlight-editor/tests/test_server.py -q`

### Task 3: Browser board selector

**Files:**
- Modify: `Tools/hold-highlight-editor/index.html`
- Modify: `Tools/hold-highlight-editor/styles.css`
- Modify: `Tools/hold-highlight-editor/app.js`

**Interfaces:**
- Consumes: `GET /api/sessions` and run-specific session URLs from Task 2.
- Produces: `#board-select`, `loadServerCatalog()`, and `switchServerSession(runId)`.

- [ ] **Step 1: Add selector markup and state**

Place a labeled `<select id="board-select">` in the toolbar, hidden in static mode. Track `serverSessions`, `selectedRunId`, and `loadingSession` in application state.

- [ ] **Step 2: Implement catalog loading and safe switching**

Fetch `/api/sessions`, populate options, and load the first run. On changes, call `confirm` before discarding dirty edits; restore the old option if declined. Fetch the new session and regions before replacing current state so failures preserve the current document.

- [ ] **Step 3: Route saves and reset transient state**

Save through the selected session's returned save URL. Reset selection, edit modes, history, saved state, and viewport after a successful switch. Keep file-upload mode static and hide the selector.

- [ ] **Step 4: Verify browser behavior manually**

Start the editor with a three-run catalog. Confirm the selector shows Beastmaker, Wood Grips Compact II, and Simulator 3D; each selection changes the image and inventory; declined dirty switching preserves edits; accepted switching loads the target; saving routes to the selected run.

### Task 4: End-to-end verification and publication

**Files:**
- Modify: `Tools/hold-highlight-editor/README.md` if verification finds unclear launch instructions.

**Interfaces:**
- Consumes: completed server and editor.
- Produces: verified PR update and visual review checkpoint.

- [ ] **Step 1: Run focused tests**

Run: `rtk pytest Tools/hold-highlight-editor/tests/test_server.py -q && rtk node --test Tools/hold-highlight-editor/tests/editor_model.test.js`

- [ ] **Step 2: Run repository verification**

Run the repository's existing Python and JavaScript test commands documented in the PR, then inspect `rtk git diff --check` and `rtk git status --short`.

- [ ] **Step 3: Commit and push**

Commit only the catalog/editor changes and push `codex/add-hangboard-onboarding`.

- [ ] **Step 4: Present the visual checkpoint**

Open the three-board editor in the in-app browser with the actual generated pipeline artifacts and leave the selector visible for user review.
