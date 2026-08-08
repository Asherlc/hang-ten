# Local Hangboard Workbench Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a local guided workbench that creates or resumes hangboard onboarding runs, automatically advances to visual checkpoints, supports Stage 2 contour refinement and Stage 3 vector refinement, and saves one approved local revision without publishing it.

**Architecture:** Keep the onboarding pipeline authoritative and place a filesystem-backed board/revision store above CLI-compatible run directories. A dependency-free loopback server calls shared Python workflow APIs and exposes job, artifact, draft, approval, and save endpoints; the browser provides the guided shell around the existing editor. Editing a pending checkpoint publishes a new immutable attempt, while revising an approved upstream stage forks a new revision and marks previous descendants stale in the board manifest.

**Tech Stack:** Python 3.11, `ThreadingHTTPServer`, Pillow, OpenCV, NumPy, vanilla JavaScript, SVG, Node's built-in test runner, pytest 8+

## Global Constraints

- The production workflow must remain programmatic, repeatable, scalable, and product-neutral.
- Do not add product-specific code paths, coordinates, masks, hold inventories, templates, or tuning.
- The CLI and UI must call the same Python orchestration APIs and resume each other's run directories.
- Generated artifacts are immutable; drafts, superseded attempts, approvals, and revision history remain recoverable.
- “Save” updates the local filesystem-backed store only; syncing to Hang Ten is outside this plan.
- One mutating job may run per board; independent boards may run concurrently.
- The editor remains dependency-free and loopback-only by default.

## Planned File Structure

- `Tools/HangboardOnboarding/src/hangboard_vectorizer/onboarding_run.py` — retain the CLI-compatible run state machine and add safe pending-checkpoint replacement.
- `Tools/HangboardOnboarding/src/hangboard_vectorizer/workbench_store.py` — own board manifests, revision records, drafts, stale lineage state, and atomic saved-revision pointers.
- `Tools/HangboardOnboarding/src/hangboard_vectorizer/review_edits.py` — validate and materialize Stage 2 contour or Stage 3 display-path edits as complete pipeline checkpoints.
- `Tools/HangboardOnboarding/src/hangboard_vectorizer/workbench.py` — provide the shared guided workflow service used by the browser server.
- `Tools/hold-highlight-editor/job_manager.py` — run bounded background mutations with one lock per board.
- `Tools/hold-highlight-editor/server.py` — become thin HTTP routing and static-file wiring over the workflow service.
- `Tools/hold-highlight-editor/workbench-client.js` — contain browser API calls and status polling.
- `Tools/hold-highlight-editor/workbench-model.js` — contain pure timeline, stale-state, and checkpoint-view transformations.
- `Tools/hold-highlight-editor/vector-path-model.js` — parse, transform, bend, mirror, and serialize Stage 3 SVG display paths.
- `Tools/hold-highlight-editor/app.js` — retain canvas interaction and expose stage-aware load/save hooks.
- `Tools/hold-highlight-editor/index.html` and `styles.css` — implement the approved guided layout.
- Focused Python and Node test files accompany each responsibility.

---

### Task 1: Publish Edited Pending Checkpoints Without Breaking CLI Runs

**Files:**
- Modify: `Tools/HangboardOnboarding/src/hangboard_vectorizer/onboarding_run.py`
- Test: `Tools/HangboardOnboarding/tests/test_onboarding_run_revisions.py`

**Interfaces:**
- Consumes: existing `RunContext`, `StageCheckpoint`, run locks, checkpoint hashing, and `read_status()`.
- Produces: `replace_pending_checkpoint(output: Path, checkpoint: StageCheckpoint) -> Mapping[str, object]` and `cached_source_path(output: Path) -> Path`.

- [ ] **Step 1: Write failing tests for immutable attempt replacement**

```python
def test_replace_pending_checkpoint_selects_new_attempt_and_preserves_old(tmp_path):
    run = _started_run(tmp_path)
    old = read_status(run)
    edited = _make_checkpoint(run, stage=0, artifact_name="edited-stage-0")

    result = replace_pending_checkpoint(run, edited)

    assert result["status"] == "awaiting_approval"
    assert result["review"].endswith("stages/00/attempt-0002/stage-0-review.png")
    assert (run / old["review"]).is_file()
    assert read_status(run)["review"] == result["review"]


def test_replace_pending_checkpoint_rejects_approved_or_wrong_stage(tmp_path):
    run = _started_run(tmp_path)
    approve_stage(run, 0)
    with pytest.raises(OnboardingStateError, match="not awaiting approval"):
        replace_pending_checkpoint(run, _make_checkpoint(run, stage=0))
```

Define `_started_run(tmp_path)` in this test module with the existing stub-runner pattern from `test_onboarding.py`. Define `_make_checkpoint()` to write one review PNG, `stage-0-candidate.json`, and matching `candidate-hashes.json` beneath a temporary artifact root and return a `StageCheckpoint`; do not depend on a live source or model.

- [ ] **Step 2: Run the focused test and confirm the missing API failure**

Run: `rtk pytest -q Tools/HangboardOnboarding/tests/test_onboarding_run_revisions.py`

Expected: collection fails because `replace_pending_checkpoint` is not defined.

- [ ] **Step 3: Implement replacement under the existing run lock**

Add a function with this contract:

```python
def replace_pending_checkpoint(
    output: Path,
    checkpoint: StageCheckpoint,
) -> Mapping[str, object]:
    """Atomically select a new immutable attempt for the pending stage."""
```

It must validate the existing manifest, require `pipeline.status == "awaiting_approval"`, require `checkpoint.stage == pipeline.currentStage`, allocate the next `attempt-NNNN` directory, validate the staged checkpoint before publication, replace only that stage's active record in `run.json`, and leave the superseded artifact directory untouched. `cached_source_path()` must resolve and confine the manifest's cached source path for revision replay.

- [ ] **Step 4: Run onboarding state-machine coverage**

Run: `rtk pytest -q Tools/HangboardOnboarding/tests/test_onboarding_run_revisions.py Tools/HangboardOnboarding/tests/test_onboard_cli.py Tools/HangboardOnboarding/tests/test_onboarding.py`

Expected: all tests pass and the existing CLI status/approve/resume semantics are unchanged.

- [ ] **Step 5: Commit the state-machine seam**

```bash
rtk git add Tools/HangboardOnboarding/src/hangboard_vectorizer/onboarding_run.py Tools/HangboardOnboarding/tests/test_onboarding_run_revisions.py
rtk git commit -m "Add immutable onboarding checkpoint replacement"
```

### Task 2: Add the Filesystem Board and Revision Store

**Files:**
- Create: `Tools/HangboardOnboarding/src/hangboard_vectorizer/workbench_store.py`
- Create: `Tools/HangboardOnboarding/tests/test_workbench_store.py`

**Interfaces:**
- Consumes: CLI-compatible run directories and confined workspace paths.
- Produces: `WorkbenchStore`, `BoardRecord`, `RevisionRecord`, `create_board()`, `create_revision()`, `write_draft()`, `mark_descendants_stale()`, and `save_revision()`.

- [ ] **Step 1: Write failing manifest and atomic-save tests**

```python
def test_store_creates_cli_compatible_revision_layout(tmp_path):
    store = WorkbenchStore(tmp_path)
    board = store.create_board("Metolius Simulator 3D")
    revision = store.create_revision(board.id)
    assert revision.run_root == tmp_path / "boards" / board.id / "revisions" / "revision-0001" / "run"
    assert store.read_board(board.id).active_revision_id == "revision-0001"


def test_save_revision_is_atomic_and_rejects_stale_lineage(tmp_path):
    store, board, first = _populated_store(tmp_path)
    second = store.create_revision(board.id, parent_revision_id=first.id, fork_stage=2)
    store.mark_descendants_stale(board.id, first.id, from_stage=2)
    with pytest.raises(WorkbenchStoreError, match="stale"):
        store.save_revision(board.id, first.id)
    store.mark_revision_complete(board.id, second.id)
    assert store.save_revision(board.id, second.id).saved_revision_id == second.id
```

Define `_populated_store(tmp_path)` in this test module by constructing `WorkbenchStore(tmp_path)`, calling `create_board("Example Board")`, creating its first revision, and returning exactly `(store, board, revision)`.

- [ ] **Step 2: Run the store tests and confirm the missing module failure**

Run: `rtk pytest -q Tools/HangboardOnboarding/tests/test_workbench_store.py`

Expected: collection fails because `workbench_store` does not exist.

- [ ] **Step 3: Implement schema-versioned immutable records**

Use frozen dataclasses with these public fields:

```python
@dataclass(frozen=True, slots=True)
class RevisionRecord:
    id: str
    run_root: Path
    parent_revision_id: str | None
    fork_stage: int | None
    current_stage: int
    state: str
    stale_from_stage: int | None


@dataclass(frozen=True, slots=True)
class BoardRecord:
    id: str
    product_name: str
    active_revision_id: str
    saved_revision_id: str | None
    revisions: tuple[RevisionRecord, ...]
```

Write `board.json` atomically with `tempfile.mkstemp`, `fsync`, and `os.replace`. Confine all paths beneath the configured workspace. Drafts live at `revisions/<id>/drafts/stage-<n>/<draft-id>.json`; generated files are never overwritten.

- [ ] **Step 4: Run store and workspace confinement tests**

Run: `rtk pytest -q Tools/HangboardOnboarding/tests/test_workbench_store.py Tools/HangboardOnboarding/tests/test_onboard_cli.py`

Expected: all tests pass, including traversal and stale-save rejection.

- [ ] **Step 5: Commit the filesystem store**

```bash
rtk git add Tools/HangboardOnboarding/src/hangboard_vectorizer/workbench_store.py Tools/HangboardOnboarding/tests/test_workbench_store.py
rtk git commit -m "Add versioned hangboard workbench store"
```

### Task 3: Materialize Stage 2 and Stage 3 Human Edits

**Files:**
- Create: `Tools/HangboardOnboarding/src/hangboard_vectorizer/review_edits.py`
- Modify: `Tools/HangboardOnboarding/src/hangboard_vectorizer/generic_stage2.py`
- Modify: `Tools/HangboardOnboarding/src/hangboard_vectorizer/generic_stage3.py`
- Test: `Tools/HangboardOnboarding/tests/test_review_edits.py`
- Create: `Tools/HangboardOnboarding/tests/data/stage-2-regions-edited.json`
- Create: `Tools/HangboardOnboarding/tests/data/stage-3-vector-regions-edited.json`

**Interfaces:**
- Consumes: an awaiting-approval run root and an edited Stage 2 region document or Stage 3 vector-region document.
- Produces: `materialize_stage2_edit(context: RunContext, document: Mapping[str, object], artifact_root: Path) -> StageCheckpoint`, `materialize_stage3_edit(...) -> StageCheckpoint`, and `validate_stage_edit(stage: int, document: object) -> Mapping[str, object]`.

- [ ] **Step 1: Write failing edit-materialization tests**

```python
def test_stage2_edit_rebuilds_labels_review_and_candidate_hashes(accepted_stage1_run, tmp_path):
    edited = _load_fixture("stage-2-regions-edited.json")
    checkpoint = materialize_stage2_edit(_context(accepted_stage1_run), edited, tmp_path / "attempt")
    assert checkpoint.stage == 2
    assert (checkpoint.artifact_root / "stage-2-labels.png").is_file()
    assert (checkpoint.artifact_root / "stage-2-review.png").is_file()
    assert _candidate_hashes_match(checkpoint.artifact_root)


def test_stage3_edit_preserves_exact_display_paths(accepted_stage2_run, tmp_path):
    edited = _load_fixture("stage-3-vector-regions-edited.json")
    checkpoint = materialize_stage3_edit(_context(accepted_stage2_run), edited, tmp_path / "attempt")
    actual = json.loads((checkpoint.artifact_root / "stage-3-vector-regions.json").read_text())
    assert [r["displayPath"] for r in actual["regions"]] == [r["displayPath"] for r in edited["regions"]]
    assert _candidate_hashes_match(checkpoint.artifact_root)
```

Add the two edited documents under `Tools/HangboardOnboarding/tests/data/`. Define `_context(run)` as `RunContext(run, json.loads((run / "run.json").read_text()))`, and define `_candidate_hashes_match(root)` by recomputing every SHA-256 entry in `candidate-hashes.json`. Reuse the deterministic accepted-run fixtures from the existing generic-stage tests; no network or model calls are permitted.

- [ ] **Step 2: Run the focused tests and confirm missing materializers**

Run: `rtk pytest -q Tools/HangboardOnboarding/tests/test_review_edits.py`

Expected: collection fails because `review_edits` does not exist.

- [ ] **Step 3: Extract reusable deterministic artifact builders**

Refactor the private Stage 2 label/review writer and Stage 3 SVG/review writer into module functions that accept already-validated region documents. The normal automatic runners and human-edit materializers must call the same builders so their artifact names and candidate-hash contracts remain identical.

Validation must reject duplicate or missing stable IDs, non-finite or out-of-bounds coordinates, contours with fewer than three vertices, malformed `displayPath` data, prohibited self-intersections, and region order changes in Stage 3. Return errors with the affected region ID.

- [ ] **Step 4: Implement both materializers transactionally**

Each materializer writes a complete candidate into a temporary sibling directory, writes `candidate-hashes.json` last, verifies it, and atomically renames the directory to `artifact_root`. Stage 2 regenerates labels from contours. Stage 3 retains exact display paths and regenerates its SVG and review PNG.

- [ ] **Step 5: Run generic-stage and edit coverage**

Run: `rtk pytest -q Tools/HangboardOnboarding/tests/test_review_edits.py Tools/HangboardOnboarding/tests/test_generic_stage2.py Tools/HangboardOnboarding/tests/test_vector_smoothing.py Tools/HangboardOnboarding/tests/test_product_render.py`

Expected: all tests pass and automatic output remains deterministic.

- [ ] **Step 6: Commit the review adapters**

```bash
rtk git add Tools/HangboardOnboarding/src/hangboard_vectorizer/review_edits.py Tools/HangboardOnboarding/src/hangboard_vectorizer/generic_stage2.py Tools/HangboardOnboarding/src/hangboard_vectorizer/generic_stage3.py Tools/HangboardOnboarding/tests/test_review_edits.py Tools/HangboardOnboarding/tests/data/stage-2-regions-edited.json Tools/HangboardOnboarding/tests/data/stage-3-vector-regions-edited.json
rtk git commit -m "Materialize reviewed contour and vector edits"
```

### Task 4: Implement the Shared Guided Workflow Service

**Files:**
- Create: `Tools/HangboardOnboarding/src/hangboard_vectorizer/workbench.py`
- Create: `Tools/HangboardOnboarding/tests/test_workbench.py`

**Interfaces:**
- Consumes: `WorkbenchStore`, onboarding `start_run`/`approve_stage`/`resume_run`/`replace_pending_checkpoint`, and review-edit materializers.
- Produces: `WorkbenchService.create_from_url()`, `create_from_upload()`, `import_run()`, `list_boards()`, `get_board()`, `save_draft()`, `approve_and_advance()`, `revise_stage()`, `retry()`, and `save()`.

- [ ] **Step 1: Write failing automatic-progression and lineage tests**

```python
def test_approve_and_advance_stops_at_next_review(service, board_with_stage0):
    result = service.approve_and_advance(board_with_stage0.id, expected_stage=0)
    assert result.stage == 1
    assert result.state == "awaiting_review"
    assert result.review_path.name == "stage-1-review.png"


def test_revising_approved_stage_forks_revision_and_marks_old_descendants_stale(service, complete_board):
    revised = service.revise_stage(complete_board.id, stage=2)
    assert revised.revision_id != complete_board.saved_revision_id
    assert revised.parent_revision_id == complete_board.saved_revision_id
    old = service.store.read_revision(complete_board.id, complete_board.saved_revision_id)
    assert old.stale_from_stage == 2
```

- [ ] **Step 2: Run the workflow tests and confirm the missing service failure**

Run: `rtk pytest -q Tools/HangboardOnboarding/tests/test_workbench.py`

Expected: collection fails because `WorkbenchService` is not defined.

- [ ] **Step 3: Implement one service result contract**

```python
@dataclass(frozen=True, slots=True)
class WorkbenchView:
    board_id: str
    revision_id: str
    parent_revision_id: str | None
    run_root: Path
    product_name: str
    stage: int
    state: str
    review_path: Path | None
    editor_mode: str | None
    saved: bool
    stale_from_stage: int | None
```

Define the `service`, `board_with_stage0`, and `complete_board` pytest fixtures in this test module using stub `StageRunner` implementations that publish deterministic review files. They must use a `WorkbenchStore(tmp_path)` and make zero network or model calls.

`approve_and_advance()` must validate the expected revision and stage, publish a draft through the relevant materializer when present, approve the selected checkpoint, call `resume_run()` exactly once when another stage exists, and return at the next review checkpoint. It must not approve that next checkpoint automatically.

- [ ] **Step 4: Implement URL/upload creation, retry, revision fork, and local save**

Uploads are written to a confined temporary file, passed to `start_run()`, and deleted after the immutable source cache succeeds. Revision forking creates a new CLI-compatible run root, replays already accepted stages automatically from the cached source, stops at the requested upstream checkpoint, and records the parent/fork relationship. `save()` requires a complete, non-stale lineage and atomically updates `savedRevisionId`.

- [ ] **Step 5: Run service and CLI compatibility tests**

Run: `rtk pytest -q Tools/HangboardOnboarding/tests/test_workbench.py Tools/HangboardOnboarding/tests/test_onboarding_run_revisions.py Tools/HangboardOnboarding/tests/test_onboard_cli.py`

Expected: all tests pass; a UI-created revision run can be inspected with `hangboard-onboard --status`.

- [ ] **Step 6: Commit the shared service**

```bash
rtk git add Tools/HangboardOnboarding/src/hangboard_vectorizer/workbench.py Tools/HangboardOnboarding/tests/test_workbench.py
rtk git commit -m "Add guided hangboard workbench service"
```

### Task 5: Add Bounded Background Jobs and Workbench HTTP APIs

**Files:**
- Create: `Tools/hold-highlight-editor/job_manager.py`
- Modify: `Tools/hold-highlight-editor/server.py`
- Modify: `Tools/hold-highlight-editor/tests/test_server.py`
- Create: `Tools/hold-highlight-editor/tests/test_job_manager.py`

**Interfaces:**
- Consumes: `WorkbenchService` methods from Task 4.
- Produces: `BoardJobManager.submit(board_id: str, operation: Callable[[], WorkbenchView]) -> JobRecord`; JSON endpoints under `/api/boards`, `/api/jobs`, `/api/drafts`, `/api/approve`, `/api/revise`, `/api/retry`, and `/api/final-save`.

- [ ] **Step 1: Write failing job serialization tests**

```python
def test_job_manager_rejects_second_mutation_for_same_board():
    gate = Event()
    manager = BoardJobManager(max_workers=2)
    first = manager.submit("board-a", lambda: gate.wait(1))
    with pytest.raises(JobConflictError, match="already running"):
        manager.submit("board-a", lambda: None)
    second = manager.submit("board-b", lambda: "ok")
    gate.set()
    assert manager.wait(first.id).state == "succeeded"
    assert manager.wait(second.id).state == "succeeded"
```

- [ ] **Step 2: Run the focused tests and confirm the missing job manager**

Run: `rtk pytest -q Tools/hold-highlight-editor/tests/test_job_manager.py`

Expected: collection fails because `job_manager` does not exist.

- [ ] **Step 3: Implement bounded jobs with immutable status records**

Use `ThreadPoolExecutor`, a private `Lock`, a `dict[str, JobRecord]`, and a `dict[str, str]` mapping board IDs to active job IDs. Store only serializable result summaries and safe error messages. Release the board lock in a `finally` block.

- [ ] **Step 4: Write failing API tests for create, draft, approve, reconnect, and save**

```python
def test_create_url_run_returns_job_and_can_be_polled(running_workbench_server):
    status, created = post_json(running_workbench_server + "/api/boards", {
        "productName": "Example Board",
        "source": "https://example.test/board.png",
    })
    assert status == 202
    final = poll_job(running_workbench_server, created["jobId"])
    assert final["state"] == "succeeded"


def test_artifact_endpoint_rejects_paths_outside_revision(running_workbench_server):
    with pytest.raises(HTTPError) as error:
        urlopen(running_workbench_server + "/api/artifact?path=../../secret")
    assert error.value.code == 400
```

Extend the existing `running_server()` test helper to accept a fake `WorkbenchService`. Add private `_post_json()` and `_poll_job()` helpers using `urllib.request`; `_poll_job()` performs bounded immediate polls against the fake deterministic job and never sleeps.

- [ ] **Step 5: Implement the JSON and raw-upload routes**

Use JSON for URL creation and all mutation commands. Use `POST /api/boards/upload?productName=<encoded>` with an `image/*` body for local uploads. Enforce request limits, content types, optimistic `expectedRevisionId` and `expectedStage` fields, loopback defaults, path confinement, and consistent `{ "ok": false, "error": "..." }` responses. Existing `/api/session` and `/api/save` compatibility routes remain until the new UI no longer needs them.

- [ ] **Step 6: Run all server tests**

Run: `rtk pytest -q Tools/hold-highlight-editor/tests/test_job_manager.py Tools/hold-highlight-editor/tests/test_server.py`

Expected: all tests pass, including reconnect polling, same-board conflict, independent-board concurrency, request-size limits, and artifact confinement.

- [ ] **Step 7: Commit server orchestration**

```bash
rtk git add Tools/hold-highlight-editor/job_manager.py Tools/hold-highlight-editor/server.py Tools/hold-highlight-editor/tests/test_job_manager.py Tools/hold-highlight-editor/tests/test_server.py
rtk git commit -m "Expose local hangboard workbench APIs"
```

### Task 6: Build Pure Browser Models for Workflow and Vector Paths

**Files:**
- Create: `Tools/hold-highlight-editor/workbench-model.js`
- Create: `Tools/hold-highlight-editor/vector-path-model.js`
- Create: `Tools/hold-highlight-editor/tests/workbench_model.test.js`
- Create: `Tools/hold-highlight-editor/tests/vector_path_model.test.js`

**Interfaces:**
- Consumes: workbench view JSON and Stage 3 `displayPath` strings.
- Produces: `timelineFor(view)`, `canApprove(view, draft)`, `parseDisplayPath(data)`, `serializeDisplayPath(commands)`, `transformPath(commands, matrix)`, `bendPath(commands, amount, bounds)`, and `mirrorPath(commands, axisX)`.

- [ ] **Step 1: Write failing stage-timeline and stale-state tests**

```javascript
test("timeline marks current, complete, upcoming, and stale stages", () => {
  const rows = timelineFor({ stage: 3, state: "awaiting_review", staleFromStage: 2 });
  assert.deepEqual(rows.map((row) => row.state), ["complete", "complete", "stale", "current", "upcoming", "upcoming", "upcoming"]);
});
```

- [ ] **Step 2: Write failing exact SVG path round-trip and transform tests**

```javascript
test("cubic display paths round-trip without flattening", () => {
  const source = "M 10 20 C 15 10 25 10 30 20 L 30 40 Z";
  assert.equal(serializeDisplayPath(parseDisplayPath(source)), source);
});

test("mirrorPath reflects endpoints and control handles", () => {
  const mirrored = mirrorPath(parseDisplayPath("M 10 20 C 15 10 25 10 30 20 Z"), 50);
  assert.equal(serializeDisplayPath(mirrored), "M 90 20 C 85 10 75 10 70 20 Z");
});
```

- [ ] **Step 3: Run Node tests and confirm missing modules**

Run: `rtk node --test Tools/hold-highlight-editor/tests/workbench_model.test.js Tools/hold-highlight-editor/tests/vector_path_model.test.js`

Expected: tests fail because the modules do not exist.

- [ ] **Step 4: Implement deterministic pure models**

Support absolute `M`, `L`, `Q`, `C`, and `Z` commands used by pipeline display paths. Preserve command types during translate, rotate, resize, bend, and mirror operations. Reject non-finite values and unsupported commands instead of flattening them. Keep DOM and network access out of both modules.

- [ ] **Step 5: Run all editor model tests**

Run: `rtk node --test Tools/hold-highlight-editor/tests/*.test.js`

Expected: all existing contour tests and new workflow/vector tests pass.

- [ ] **Step 6: Commit the browser models**

```bash
rtk git add Tools/hold-highlight-editor/workbench-model.js Tools/hold-highlight-editor/vector-path-model.js Tools/hold-highlight-editor/tests/workbench_model.test.js Tools/hold-highlight-editor/tests/vector_path_model.test.js
rtk git commit -m "Add workbench and vector path browser models"
```

### Task 7: Implement the Guided Shell and Dual-Mode Editor

**Files:**
- Create: `Tools/hold-highlight-editor/workbench-client.js`
- Modify: `Tools/hold-highlight-editor/index.html`
- Modify: `Tools/hold-highlight-editor/styles.css`
- Modify: `Tools/hold-highlight-editor/app.js`
- Modify: `Tools/hold-highlight-editor/editor-model.js`
- Modify: `Tools/hold-highlight-editor/tests/editor_model.test.js`

**Interfaces:**
- Consumes: Task 5 HTTP endpoints and Task 6 pure models.
- Produces: setup screen, recent-run picker, stage timeline, automatic job polling, contour editor mode, exact vector editor mode, debounced draft autosave, validation display, compare view, retry, approve-and-continue, upstream revise, and final local Save.

- [ ] **Step 1: Add failing editor adapter tests**

```javascript
test("normalizePipelineDocument keeps Stage 3 display paths exact", () => {
  const source = { width: 1000, height: 300, regions: [{ id: 13, key: "hold-13", type: "edge", displayPath: "M 10 20 C 15 10 25 10 30 20 Z" }] };
  const result = normalizePipelineDocument(source, { width: 10, height: 10 }, "vector");
  assert.equal(result.regions[0].displayPath, source.regions[0].displayPath);
  assert.equal(result.editorMode, "vector");
});
```

- [ ] **Step 2: Run the adapter tests and verify failure**

Run: `rtk node --test Tools/hold-highlight-editor/tests/editor_model.test.js`

Expected: the vector-mode assertion fails against the contour-only adapter.

- [ ] **Step 3: Build the approved workbench shell**

Add the left progress/recent-runs rail, central checkpoint canvas, contextual inspector, draft status, undo/compare controls, and persistent primary action. The initial form accepts product name and either URL or image upload. Keep exactly one active board in the main workspace.

- [ ] **Step 4: Add one stage-aware editor controller**

Expose these functions from `app.js`:

```javascript
window.HoldEditor = Object.freeze({
  loadCheckpoint,
  serializeDraft,
  markDraftSaved,
  focusRegion,
  setCompareEnabled,
});
```

Contour mode uses existing point/shape tools. Vector mode renders the original `displayPath`, transforms Bézier endpoints and handles through `vector-path-model.js`, and serializes exact paths without contour conversion. Geometry errors call `focusRegion(regionId)` and block approval.

- [ ] **Step 5: Add API progression and autosave behavior**

`workbench-client.js` must expose `listBoards`, `createFromUrl`, `createFromUpload`, `getBoard`, `getJob`, `saveDraft`, `approve`, `revise`, `retry`, and `finalSave`. Debounce drafts by 500 ms, include `expectedRevisionId` and `expectedStage`, flush pending drafts before approval, and poll only while a job is queued or running.

- [ ] **Step 6: Run all browser model tests and manually smoke the three editor states**

Run: `rtk node --test Tools/hold-highlight-editor/tests/*.test.js`

Expected: all tests pass.

Manual smoke command: `rtk python3 Tools/hold-highlight-editor/server.py --workspace-root /absolute/path/to/onboarding-workspace`

Verify the setup screen, a Stage 2 contour checkpoint, and a Stage 3 exact-vector checkpoint render without console errors; browser refresh restores the current draft.

- [ ] **Step 7: Commit the guided browser application**

```bash
rtk git add Tools/hold-highlight-editor/workbench-client.js Tools/hold-highlight-editor/index.html Tools/hold-highlight-editor/styles.css Tools/hold-highlight-editor/app.js Tools/hold-highlight-editor/editor-model.js Tools/hold-highlight-editor/tests/editor_model.test.js
rtk git commit -m "Build guided hangboard workbench UI"
```

### Task 8: Verify Cross-Interface Recovery and Three-Board Scalability

**Files:**
- Create: `Tools/HangboardOnboarding/tests/test_workbench_end_to_end.py`
- Modify: `Tools/hold-highlight-editor/README.md`
- Modify: `Tools/HangboardOnboarding/README.md`

**Interfaces:**
- Consumes: the complete shared workflow, server, and browser artifacts.
- Produces: regression coverage and operator documentation for local Save and later sync boundaries.

- [ ] **Step 1: Add an end-to-end CLI/UI interoperability test**

```python
def test_ui_created_run_is_resumable_by_cli_and_cli_run_is_listed_by_ui(tmp_path):
    service = _fixture_service(tmp_path)
    created = service.create_from_upload("Example Board", _fixture_image_bytes())
    assert main(["--output", str(created.run_root), "--status"]) == 0
    cli_run = _create_cli_fixture_run(tmp_path / "cli-run")
    imported = service.import_run(cli_run)
    assert imported.run_root == cli_run
    assert any(board.id == imported.board_id for board in service.list_boards())
```

Define `_fixture_image_bytes()` with Pillow as one deterministic RGB PNG. Define `_fixture_service(tmp_path)` with the production store plus deterministic stub runners, and `_create_cli_fixture_run(path)` by calling `start_run()` with those same runners and returning the created run path.

- [ ] **Step 2: Add a product-neutral fixture replay assertion**

Parametrize the same service calls over Beastmaker 1000, Wood Grips Compact II, and Simulator 3D fixture inputs. Assert common schema, stable IDs through Stage 2 to Stage 4, successful local Save, and absence of product-key conditionals in workbench modules. Fixture data may differ; production control flow may not.

- [ ] **Step 3: Run the complete Python and Node suites**

Run: `rtk pytest -q Tools/HangboardOnboarding/tests Tools/hold-highlight-editor/tests`

Run: `rtk node --test Tools/hold-highlight-editor/tests/*.test.js`

Expected: all tests pass.

- [ ] **Step 4: Perform a real visual workflow replay**

Start one workbench instance against the existing generated workspace. Open Beastmaker 1000, Wood Grips Compact II, and Simulator 3D from the recent-runs picker. For each board, verify Stage 2 editing, Stage 3 editing, stale-lineage handling, refresh recovery, and final local Save. Capture one fully highlighted final review image per board for the user's only required visual checkpoint.

- [ ] **Step 5: Document operation and the Save/sync boundary**

Document the single local start command, URL and upload creation, automatic checkpoint progression, retry behavior, Stage 2 versus Stage 3 editing, revision history, filesystem layout, local Save semantics, and that Hang Ten synchronization requires a separate future command.

- [ ] **Step 6: Commit end-to-end verification and documentation**

```bash
rtk git add Tools/HangboardOnboarding/tests/test_workbench_end_to_end.py Tools/hold-highlight-editor/README.md Tools/HangboardOnboarding/README.md
rtk git commit -m "Verify and document hangboard workbench workflow"
```

## Final Verification

- [ ] Run: `rtk git diff --check`
- [ ] Run: `rtk pytest -q Tools/HangboardOnboarding/tests Tools/hold-highlight-editor/tests`
- [ ] Run: `rtk node --test Tools/hold-highlight-editor/tests/*.test.js`
- [ ] Confirm `rtk git status --short` contains only intended files.
- [ ] Present only the three final fully highlighted board images for visual review.
