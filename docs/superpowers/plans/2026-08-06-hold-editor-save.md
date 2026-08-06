# Hold Editor Local Save Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a loopback-only local editor server that loads one onboarding run and atomically saves reviewed Stage 2 regions and correction deltas into it.

**Architecture:** A standard-library Python HTTP server owns filesystem access and exposes only session-load and save endpoints. The existing browser editor consumes that API when available, retains download exports as fallback, and tracks dirty/saving/saved state.

**Tech Stack:** Python 3 standard library, browser JavaScript, HTML/CSS, pytest.

## Global Constraints

- Bind to `127.0.0.1` unless explicitly overridden.
- Confine every served and written path to the configured onboarding run.
- Preserve generated `stage-2-regions.json`; save review artifacts beside it.
- Write JSON atomically with temporary files and `os.replace`.
- Keep the editor dependency-free and board-independent.

---

### Task 1: Run discovery, validation, and atomic persistence

**Files:**
- Create: `Tools/hold-highlight-editor/server.py`
- Create: `Tools/hold-highlight-editor/tests/test_server.py`

**Interfaces:**
- Produces: `discover_session(run_dir: Path) -> EditorSession`, `validate_regions_document(value: object) -> dict`, `save_review(session: EditorSession, regions: object, corrections: object) -> dict`.

- [ ] **Step 1: Write failing unit tests**

Cover deterministic discovery of one `stage-2-regions.json` and one Stage 1 PNG, rejection of missing or ambiguous artifacts, region contours with fewer than three finite coordinate pairs, and successful writes to the Stage 2 directory.

```python
def test_save_review_preserves_proposal_and_writes_review_artifacts(tmp_path):
    session = make_run(tmp_path)
    original = session.regions_path.read_bytes()
    result = save_review(session, REGIONS, CORRECTIONS)
    assert session.regions_path.read_bytes() == original
    assert json.loads((session.regions_path.parent / "stage-2-regions.edited.json").read_text()) == REGIONS
    assert result["regionsPath"].endswith("stage-2-regions.edited.json")
```

- [ ] **Step 2: Verify the tests fail**

Run: `rtk python3 -m pytest Tools/hold-highlight-editor/tests/test_server.py -q`

Expected: collection fails because `server.py` does not exist.

- [ ] **Step 3: Implement the filesystem boundary**

Use a frozen `EditorSession` dataclass with resolved `run_dir`, `image_path`, and `regions_path`. Validate files with `Path.resolve()` plus `relative_to(run_dir)`. Validate canvas dimensions, unique integer region IDs, and finite numeric contour coordinates. Serialize with stable indentation to a named temporary file in the destination directory, flush and `os.fsync`, then call `os.replace`.

- [ ] **Step 4: Verify unit tests pass**

Run: `rtk python3 -m pytest Tools/hold-highlight-editor/tests/test_server.py -q`

Expected: all Task 1 tests pass.

### Task 2: Constrained HTTP API and static serving

**Files:**
- Modify: `Tools/hold-highlight-editor/server.py`
- Modify: `Tools/hold-highlight-editor/tests/test_server.py`

**Interfaces:**
- Produces: `create_server(session: EditorSession, host: str, port: int) -> ThreadingHTTPServer` and endpoints `GET /api/session`, `GET /api/artifact/image`, `GET /api/artifact/regions`, `PUT /api/save`.

- [ ] **Step 1: Write failing HTTP tests**

Start the server on port `0` in a test thread. Assert session URLs load, a valid save returns `200`, malformed or oversized JSON returns `400` or `413`, unknown paths return `404`, and traversal never serves files outside the run.

```python
with urlopen(Request(base + "/api/save", data=json.dumps(payload).encode(), method="PUT", headers={"Content-Type": "application/json"})) as response:
    assert response.status == 200
```

- [ ] **Step 2: Verify HTTP tests fail**

Run: `rtk python3 -m pytest Tools/hold-highlight-editor/tests/test_server.py -q`

Expected: failures identify the missing server factory and routes.

- [ ] **Step 3: Implement the HTTP handler and CLI**

Serve only the editor directory and the two explicit artifact routes. Limit request bodies to 10 MiB. Return JSON objects shaped as `{ "ok": true, ... }` or `{ "ok": false, "error": "..." }`. Add `--run-dir`, `--host`, and `--port`; default host to `127.0.0.1` and port to `4173`.

- [ ] **Step 4: Verify all server tests pass**

Run: `rtk python3 -m pytest Tools/hold-highlight-editor/tests/test_server.py -q`

Expected: all server and HTTP tests pass.

### Task 3: Browser Save control and dirty state

**Files:**
- Modify: `Tools/hold-highlight-editor/index.html`
- Modify: `Tools/hold-highlight-editor/styles.css`
- Modify: `Tools/hold-highlight-editor/app.js`
- Modify: `Tools/hold-highlight-editor/README.md`

**Interfaces:**
- Consumes: the four Task 2 API endpoints.
- Produces: `saveToRun()`, `buildEditedDocument()`, `buildCorrectionsDocument()`, and visible dirty/saving/saved/error states.

- [ ] **Step 1: Extract shared export document builders**

Refactor the two download actions to call pure builders. Save sends both builder results in one request so downloaded and persisted formats cannot diverge.

- [ ] **Step 2: Add session loading and Save behavior**

Probe `/api/session` before demo loading. When available, load its image and regions URLs and enable Save. Save sends `{ "regions": buildEditedDocument(), "corrections": buildCorrectionsDocument() }`; successful save refreshes the baseline and clears dirty state. Static mode disables Save with explanatory copy while leaving both exports active.

- [ ] **Step 3: Mark mutations dirty**

Set dirty state after history commits, undo, redo, and region metadata edits. Display `Unsaved changes`, `Saving…`, `Saved`, or the returned error without hiding existing action status.

- [ ] **Step 4: Document the local workflow**

Document the server command, exact output filenames, proposal preservation, static fallback, and recovery exports.

- [ ] **Step 5: Run complete verification**

Run:

```bash
rtk node --check Tools/hold-highlight-editor/app.js
rtk python3 -m pytest Tools/hold-highlight-editor/tests/test_server.py -q
rtk git diff --check
```

Expected: JavaScript syntax passes, all server tests pass, and the diff contains no whitespace errors.
