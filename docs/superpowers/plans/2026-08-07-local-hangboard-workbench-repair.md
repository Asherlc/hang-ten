# Local Hangboard Workbench Repair Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Close the remaining workbench UI, persistence, and job-lifecycle gaps without changing visual-pipeline output quality.

**Architecture:** Preserve the existing CLI-compatible run format and thin browser/server split. Repair the mismatched identity and artifact contracts at their consumer boundaries, make accepted background work recoverable until a terminal outcome is known, and publish revision pointers only after their run data is usable.

**Tech Stack:** Python 3.11, `ThreadingHTTPServer`, Pillow, vanilla JavaScript, SVG, Node's built-in test runner, pytest 8+

## Global Constraints

- Scope is the local workbench UI/service and the pipeline contracts required by UI editing; do not change smoothing, material inference, shading, or visual output quality.
- Preserve existing work and CLI compatibility.
- Every accepted method remains programmatic, repeatable, scalable, and product-neutral.
- Do not add product-specific code paths, coordinates, masks, templates, inventories, or tuning.
- Generated artifacts and failed-attempt evidence remain immutable and hash-bound.
- Stage 2 stable IDs may be sparse after deletion and must never be renumbered downstream.
- Only a server-confirmed terminal job outcome may clear accepted-job recovery state.
- Prefix every shell command with `rtk`.
- Use test-driven development: add one behavioral regression, observe the expected failure, implement the minimum repair, and re-run focused plus surrounding coverage.

---

### Task 1: Preserve Sparse Stable IDs Through Production Stage 3 and Stage 4

**Files:**
- Modify: `Tools/HangboardOnboarding/src/hangboard_vectorizer/generic_stage3.py`
- Modify: `Tools/HangboardOnboarding/src/hangboard_vectorizer/generic_stage4.py`
- Create: `Tools/HangboardOnboarding/tests/test_generic_stable_ids.py`

**Interfaces:**
- Consumes: approved Stage 2 regions whose IDs are unique, strictly increasing, and may be sparse; accepted Stage 2 label pixels use those exact IDs.
- Produces: Stage 3 vector-region documents, Stage 4 runtime regions, manifests, and highlight selections keyed by the same exact IDs.

- [ ] **Step 1: Add a real sparse-ID production regression**

Create a deterministic accepted Stage 2 fixture with ordered IDs `(1, 3, 4)` and label pixels containing those values. Run the production `GenericStage3Runner`, then approve its checkpoint and run the production `GenericStage4Runner`. Assert the Stage 3 and Stage 4 region inventories remain exactly `(1, 3, 4)`, source masks are read from the matching label values, and the all-highlight scenario selects `(1, 3, 4)`.

- [ ] **Step 2: Run the regression and verify RED**

Run: `rtk pytest -q Tools/HangboardOnboarding/tests/test_generic_stable_ids.py`

Expected: Stage 3 fails with `Stage 2 region order changed`, or Stage 4 fails with `Stage 3 region order is invalid`, proving the ordinal consumer mismatch.

- [ ] **Step 3: Consume actual IDs without renumbering**

In `generic_stage3._approved_inputs()`, validate that each ID is an integer, positive, unique, and strictly increasing, then build masks with `labels == region_id`. In `generic_stage4._geometry()`, apply the same identity validation and construct `_Region` with the accepted `id`. Keep document order stable; do not alter any contour, smoothing, or rendering algorithm.

- [ ] **Step 4: Verify GREEN and surrounding contracts**

Run: `rtk pytest -q Tools/HangboardOnboarding/tests/test_generic_stable_ids.py Tools/HangboardOnboarding/tests/test_review_edits.py Tools/HangboardOnboarding/tests/test_workbench_end_to_end.py`

Expected: all tests pass and the exact sparse inventory reaches Stage 4.

- [ ] **Step 5: Commit**

```bash
rtk git add Tools/HangboardOnboarding/src/hangboard_vectorizer/generic_stage3.py Tools/HangboardOnboarding/src/hangboard_vectorizer/generic_stage4.py Tools/HangboardOnboarding/tests/test_generic_stable_ids.py
rtk git commit -m "Preserve sparse edited hold identities"
```

### Task 2: Enforce Editable Artifact Alignment and Show the Annotated Review Separately

**Files:**
- Modify: `Tools/HangboardOnboarding/src/hangboard_vectorizer/workbench.py`
- Modify: `Tools/HangboardOnboarding/tests/test_workbench.py`
- Modify: `Tools/hold-highlight-editor/workbench-controller.js`
- Modify: `Tools/hold-highlight-editor/app.js`
- Modify: `Tools/hold-highlight-editor/index.html`
- Modify: `Tools/hold-highlight-editor/styles.css`
- Modify: `Tools/hold-highlight-editor/tests/workbench_controller.test.js`

**Interfaces:**
- Consumes: an editable Stage 2 or Stage 3 geometry document, the hash-bound Stage 1 clean RGBA, and the current annotated review PNG.
- Produces: a workbench view only when clean raster dimensions equal the geometry canvas and clean/review artifacts are distinct; the Compare control displays the annotated review as its own view rather than stretching it into editor coordinates.

- [ ] **Step 1: Add service regressions for artifact integrity**

Add tests that mutate an otherwise valid editable run so the accepted clean image dimensions disagree with `document.canvas`, and so the review resolves to the same path or SHA-256 as the clean image. Assert `get_board()` rejects each run with a safe `WorkbenchServiceError` naming inconsistent editable evidence.

- [ ] **Step 2: Add browser regressions for alignment and comparison selection**

Add pure controller helpers and tests that reject an image asset whose `naturalWidth`/`naturalHeight` disagree with the geometry canvas and that select `reviewUrl` only as the separate comparison artifact for editable views. The test must distinguish the normal `editorImageUrl` from the comparison `reviewUrl`.

- [ ] **Step 3: Run both focused suites and verify RED**

Run: `rtk pytest -q Tools/HangboardOnboarding/tests/test_workbench.py -k 'editor_image or editable_artifact'`

Run: `rtk node --test Tools/hold-highlight-editor/tests/workbench_controller.test.js`

Expected: the mismatched evidence is currently accepted and the new browser helpers are absent.

- [ ] **Step 4: Validate the service artifact contract**

Decode the clean image with Pillow, read the current hash-bound Stage 2/3 document canvas, require exact integer dimension equality, and require review and editor artifacts to differ by confined path and file hash before returning an editable `WorkbenchView`. Convert decode, filesystem, and schema failures to safe `WorkbenchServiceError` messages.

- [ ] **Step 5: Render a separate review view**

Add a dedicated annotated-review image container beside the SVG editor. In guided editable stages, Compare toggles between the coordinate-aligned editor and the review image at its own aspect ratio; it does not overlay or rescale review pixels into geometry coordinates. Legacy comparison behavior remains unchanged. Validate image/document dimensions before `loadCheckpoint()` commits state.

- [ ] **Step 6: Verify focused UI and server coverage**

Run: `rtk pytest -q Tools/HangboardOnboarding/tests/test_workbench.py Tools/hold-highlight-editor/tests/test_server.py`

Run: `rtk node --test Tools/hold-highlight-editor/tests/workbench_controller.test.js Tools/hold-highlight-editor/tests/editor_model.test.js`

Expected: all tests pass, mismatched evidence is rejected, and clean/review URLs retain distinct roles.

- [ ] **Step 7: Commit**

```bash
rtk git add Tools/HangboardOnboarding/src/hangboard_vectorizer/workbench.py Tools/HangboardOnboarding/tests/test_workbench.py Tools/hold-highlight-editor/workbench-controller.js Tools/hold-highlight-editor/app.js Tools/hold-highlight-editor/index.html Tools/hold-highlight-editor/styles.css Tools/hold-highlight-editor/tests/workbench_controller.test.js
rtk git commit -m "Validate and separate editable review artifacts"
```

### Task 3: Persist and Retry Stage 0 Failures

**Files:**
- Modify: `Tools/HangboardOnboarding/src/hangboard_vectorizer/onboarding_run.py`
- Modify: `Tools/HangboardOnboarding/src/hangboard_vectorizer/workbench.py`
- Modify: `Tools/HangboardOnboarding/tests/test_onboarding_run_revisions.py`
- Modify: `Tools/HangboardOnboarding/tests/test_workbench.py`

**Interfaces:**
- Consumes: a run whose source and initial manifest were published before its Stage 0 runner failed.
- Produces: immutable `stages/00/attempt-NNNN/stage-0-failure.log` evidence, a failed pipeline with `nextStage: 0`, and workbench retry that uses the cached source to create the next Stage 0 attempt.

- [ ] **Step 1: Add onboarding state-machine regressions**

Use a Stage 0 runner that raises after the source is cached. Assert `start_run()` re-raises but leaves a valid run at the requested output, with sanitized immutable failed-attempt evidence and `read_status()` reporting failed Stage 0. Replace the runner with a succeeding Stage 0 runner and assert `resume_run()` publishes `attempt-0002` awaiting approval without changing the first failure log.

- [ ] **Step 2: Add workbench recovery regressions**

Assert a failed Stage 0 creation remains listed as the board's active failed revision, exposes Stage 0 to `retry()`, and reaches review after retry. Preserve the existing pre-cache rollback contract and assert temporary upload cleanup for failures that never produced a retryable cached run.

- [ ] **Step 3: Run focused tests and verify RED**

Run: `rtk pytest -q Tools/HangboardOnboarding/tests/test_onboarding_run_revisions.py Tools/HangboardOnboarding/tests/test_workbench.py -k 'stage0 or Stage_0 or failed_creation'`

Expected: the output is deleted or the failed revision is not active/retryable.

- [ ] **Step 4: Publish Stage 0 failure evidence transactionally**

Allow failed-attempt validation for Stage 0, set its failed pipeline to `currentStage: 0`, `nextStage: 0`, and `nextAction: retry-stage-0`, and publish the temporary run directory after failure evidence is durably written. If no initial manifest/cache exists, retain the existing full rollback.

- [ ] **Step 5: Keep retryable failures active in the workbench**

When creation leaves a valid failed run, mark the revision failed while retaining it as the board's active revision. Let the existing retry path call `resume_run()` for failed Stage 0. Delete the upload only after either the source is cached or a non-retryable creation has been rolled back.

- [ ] **Step 6: Verify state-machine and service coverage**

Run: `rtk pytest -q Tools/HangboardOnboarding/tests/test_onboarding_run_revisions.py Tools/HangboardOnboarding/tests/test_workbench.py Tools/HangboardOnboarding/tests/test_onboard_cli.py`

Expected: all tests pass and attempt 1 failure evidence remains byte-identical after retry.

- [ ] **Step 7: Commit**

```bash
rtk git add Tools/HangboardOnboarding/src/hangboard_vectorizer/onboarding_run.py Tools/HangboardOnboarding/src/hangboard_vectorizer/workbench.py Tools/HangboardOnboarding/tests/test_onboarding_run_revisions.py Tools/HangboardOnboarding/tests/test_workbench.py
rtk git commit -m "Persist retryable Stage 0 failures"
```

### Task 4: Keep Accepted Jobs Frozen Until a Terminal Outcome

**Files:**
- Modify: `Tools/hold-highlight-editor/workbench-client.js`
- Modify: `Tools/hold-highlight-editor/workbench-controller.js`
- Modify: `Tools/hold-highlight-editor/app.js`
- Modify: `Tools/hold-highlight-editor/tests/workbench_client.test.js`
- Modify: `Tools/hold-highlight-editor/tests/workbench_controller.test.js`

**Interfaces:**
- Consumes: a POST-accepted job ID and subsequent job-poll results or transport failures.
- Produces: terminal errors only for server-confirmed `failed` jobs; nonterminal uncertainty retains the persisted job ID, busy state, and editing freeze for reconnect.

- [ ] **Step 1: Add client regressions for transient polling**

Test an accepted job whose first GET fails transiently and whose later GET reports running then succeeded. Assert polling recovers the same job result and never submits another mutation. Test a confirmed failed job separately and assert its error has `terminal === true` and retains the job ID.

- [ ] **Step 2: Add controller regressions for freeze semantics**

Test that `runFrozenApproval()` restores editing after a pre-acceptance or confirmed terminal failure, but leaves editing frozen after an error carrying an accepted nonterminal job ID. Assert active-job storage clears only for the matching terminal job.

- [ ] **Step 3: Run Node coverage and verify RED**

Run: `rtk node --test Tools/hold-highlight-editor/tests/workbench_client.test.js Tools/hold-highlight-editor/tests/workbench_controller.test.js`

Expected: the first transport error aborts polling and the approval controller unfreezes indiscriminately.

- [ ] **Step 4: Implement terminal-aware recovery**

Retry bounded transient GET failures inside `pollJob()` without changing the accepted job ID. If transport uncertainty is surfaced, tag it with the accepted job ID and `terminal === false`. Clear storage and unfreeze only when no job was accepted or the server confirms terminal failure. Keep `state.busy` and `state.editingFrozen` true for nonterminal uncertainty and present reconnecting status.

- [ ] **Step 5: Apply the same rule during startup reconnect**

In `loadGuidedWorkbench()`, retain the persisted active job and busy/frozen state on nonterminal polling errors. Clear it only on success or confirmed terminal failure. A later refresh must poll the same ID.

- [ ] **Step 6: Verify all browser state coverage**

Run: `rtk node --test Tools/hold-highlight-editor/tests/*.test.js`

Expected: all tests pass with no duplicate accepted mutation and no transient unfreeze.

- [ ] **Step 7: Commit**

```bash
rtk git add Tools/hold-highlight-editor/workbench-client.js Tools/hold-highlight-editor/workbench-controller.js Tools/hold-highlight-editor/app.js Tools/hold-highlight-editor/tests/workbench_client.test.js Tools/hold-highlight-editor/tests/workbench_controller.test.js
rtk git commit -m "Keep accepted workbench jobs recoverable"
```

### Task 5: Activate Revisions Only After Their Runs Are Usable

**Files:**
- Modify: `Tools/HangboardOnboarding/src/hangboard_vectorizer/workbench_store.py`
- Modify: `Tools/HangboardOnboarding/src/hangboard_vectorizer/workbench.py`
- Modify: `Tools/HangboardOnboarding/tests/test_workbench_store.py`
- Modify: `Tools/HangboardOnboarding/tests/test_workbench.py`

**Interfaces:**
- Consumes: a reserved initial or fork revision whose run is still being created/replayed.
- Produces: a pending revision that is retained in history but not returned as active until one atomic store update activates it; fork activation and parent stale marking occur together.

- [ ] **Step 1: Add store regressions for reservation and activation**

Assert `create_revision()` appends a `pending` revision without changing `active_revision_id`. Add `activate_revision(board_id, revision_id, stale_parent_revision_id=None, stale_from_stage=None)` coverage proving initial activation is atomic and fork activation changes the active pointer and parent stale marker in one manifest replacement.

- [ ] **Step 2: Add concurrent service regressions**

Block initial creation and fork replay in a runner. While each job is blocked, assert `list_boards()`/`get_board()` expose the previous usable active revision (or no active revision for a new board), never the pending run. On success assert the child becomes active exactly once; on failure assert the parent remained active throughout and the child is retained as failed evidence.

- [ ] **Step 3: Run focused tests and verify RED**

Run: `rtk pytest -q Tools/HangboardOnboarding/tests/test_workbench_store.py Tools/HangboardOnboarding/tests/test_workbench.py -k 'pending or activate or concurrent or replay_failure'`

Expected: `create_revision()` immediately changes the active pointer and concurrent reads observe the partial child.

- [ ] **Step 4: Split reservation from activation**

Permit `RevisionRecord.state == "pending"`. Make `create_revision()` publish only the revision history entry and directory reservation. Add the synchronized activation method; validate paired stale arguments and write the active pointer, child state, and optional parent stale marker in one atomic board-manifest replacement.

- [ ] **Step 5: Move service activation after successful work**

Activate initial revisions only after `start_run()` returns a usable checkpoint. For forks, finish replay first and then atomically activate the child while marking the parent stale. On failure mark the pending child failed without changing the existing active pointer; for a durable initial Stage 0 failure, deliberately activate that failed retryable revision.

- [ ] **Step 6: Verify persistence, concurrency, and workflow coverage**

Run: `rtk pytest -q Tools/HangboardOnboarding/tests/test_workbench_store.py Tools/HangboardOnboarding/tests/test_workbench.py Tools/HangboardOnboarding/tests/test_workbench_end_to_end.py Tools/hold-highlight-editor/tests/test_server.py`

Expected: all tests pass and no read observes an uninitialized active run.

- [ ] **Step 7: Commit**

```bash
rtk git add Tools/HangboardOnboarding/src/hangboard_vectorizer/workbench_store.py Tools/HangboardOnboarding/src/hangboard_vectorizer/workbench.py Tools/HangboardOnboarding/tests/test_workbench_store.py Tools/HangboardOnboarding/tests/test_workbench.py
rtk git commit -m "Activate workbench revisions atomically"
```
