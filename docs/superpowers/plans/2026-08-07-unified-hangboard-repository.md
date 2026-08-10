# Unified Hangboard Repository Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use a fresh subagent for every implementation or configuration task, with separate implementation and review checkpoints for each task. Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace catalog and nested repository versions with one directly discovered, Stage 4-complete run directory per board, using Git as published history.

**Architecture:** `RepositoryBoardLibrary` scans `Tools/HangboardOnboarding/boards/<board-id>/run.json`, validates each run independently, and exposes valid boards plus diagnostics. Workbench edits remain under `.context`; save publishes the completed run into the canonical directory with optimistic manifest tokens and a recoverable directory swap. The accepted Compact II run moves into the canonical directory without changing bytes.

**Tech Stack:** Python 3.11, dataclasses, pathlib, SHA-256, `fcntl`, atomic filesystem renames and fsync, pytest, dependency-free browser JavaScript, Node test runner, Git.

## Global Constraints

- Prefix every shell command with `rtk`.
- Preserve all existing work; inspect Git status before every task and never discard unrelated changes.
- The Swift app remains a downstream consumer and is not changed by this plan.
- Only Stage 4-complete, fully approved runs may be committed beneath `Tools/HangboardOnboarding/boards/`.
- Unfinished work remains beneath ignored `.context/hangboard-workbench/` storage.
- Git is the sole history of published board states; do not create catalog, pointer, published-output, or repository-local version manifests.
- Do not run Git commands from the workbench service.
- Do not change visual-generation behavior or accepted image bytes.
- Production code must remain product-neutral: no per-board branches, coordinates, masks, templates, inventories, or tuning.
- Use the same discovery, open, publish, and recovery code for Beastmaker 1000, Metolius Wood Grips Compact II, and Metolius Simulator 3D fixtures.

---

### Task 1: Reconcile the feature branch with current `main`

**Files:**
- Merge only; resolve paths if Git reports conflicts.

**Interfaces:**
- Consumes: clean `codex/local-hangboard-workbench` worktree and fetched `origin/main`.
- Produces: one branch containing both the workbench implementation and the committed Compact II accepted run.

- [ ] **Step 1: Verify the exact branch and worktree state**

Run:

```bash
rtk git status --short --branch
rtk git rev-list --left-right --count HEAD...origin/main
```

Expected: the only difference is committed branch history; stop and preserve any unexpected working-tree changes before merging.

- [ ] **Step 2: Merge current main without rewriting either history**

Run:

```bash
rtk git merge --no-edit origin/main
```

If Git reports conflicts, resolve only the conflicting files by combining the workbench changes with current main. Do not choose an entire side for unrelated files.

- [ ] **Step 3: Verify the accepted run and workbench both survived**

Run:

```bash
rtk git status --short --branch
rtk git ls-files Tools/HangboardOnboarding/reference/metolius-compact-ii/accepted-run/run.json
rtk python -m pytest Tools/HangboardOnboarding/tests/test_workbench.py -q
```

Expected: the accepted `run.json` is tracked and focused workbench tests pass.

- [ ] **Step 4: Record the reconciliation gate**

If the merge created a merge commit, do not create another empty commit. Record its SHA for the task review:

```bash
rtk git log -1 --oneline
```

---

### Task 2: Replace catalog discovery with self-describing board discovery

**Files:**
- Modify: `Tools/HangboardOnboarding/src/hangboard_vectorizer/board_library.py`
- Rewrite: `Tools/HangboardOnboarding/tests/test_board_library.py`

**Interfaces:**
- Consumes: complete-run validation through `read_status(run_root)` and the existing Stage 4 acceptance contract.
- Produces:
  - `LibraryBoard(board_id: str, display_name: str, run_path: Path, revision_token: str)`
  - `LibraryDiagnostic(path: str, code: str, message: str)`
  - `LibrarySnapshot(boards: tuple[LibraryBoard, ...], diagnostics: tuple[LibraryDiagnostic, ...])`
  - `RepositoryBoardLibrary.snapshot() -> LibrarySnapshot`
  - `RepositoryBoardLibrary.get_board(board_id: str) -> LibraryBoard`
  - `RepositoryBoardLibrary.copy_current_run(board_id: str, destination: Path) -> LibraryBoard`

- [ ] **Step 1: Replace catalog tests with failing direct-discovery tests**

Build complete generic fixture runs with the existing test helpers, copied directly to `Tools/HangboardOnboarding/boards/<product-key>/`. Add tests equivalent to:

```python
def test_snapshot_discovers_self_describing_runs_and_sorts_them(tmp_path: Path) -> None:
    _complete_board(tmp_path, "charlie", "charlie")
    _complete_board(tmp_path, "alpha-2", "Alpha")
    _complete_board(tmp_path, "alpha-1", "alpha")

    snapshot = RepositoryBoardLibrary(tmp_path).snapshot()

    assert [board.board_id for board in snapshot.boards] == ["alpha-1", "alpha-2", "charlie"]
    assert snapshot.diagnostics == ()
    assert all(len(board.revision_token) == 64 for board in snapshot.boards)


def test_invalid_board_is_diagnostic_without_hiding_valid_boards(tmp_path: Path) -> None:
    _complete_board(tmp_path, "valid-board", "Valid Board")
    invalid = _complete_board(tmp_path, "wrong-directory", "Invalid Board")
    manifest = _read_json(invalid / "run.json")
    manifest["product"]["key"] = "different-key"
    _write_json(invalid / "run.json", manifest)

    snapshot = RepositoryBoardLibrary(tmp_path).snapshot()

    assert [board.board_id for board in snapshot.boards] == ["valid-board"]
    assert [(item.path, item.code) for item in snapshot.diagnostics] == [
        ("wrong-directory", "identity_mismatch")
    ]
```

Also cover hidden-directory exclusion, symlink rejection, invalid IDs, missing `run.json`, incomplete stages, bad approval hashes, bad Stage 4 output hashes, deterministic revision tokens, confined copies, and `get_board()` rejecting an invalid or missing board.

- [ ] **Step 2: Run the direct-discovery tests and verify RED**

Run:

```bash
rtk python -m pytest Tools/HangboardOnboarding/tests/test_board_library.py -q
```

Expected: failures because `snapshot`, diagnostics, and the direct `boards/` root do not exist.

- [ ] **Step 3: Implement the minimal direct-discovery model**

Rewrite catalog and version parsing around this public shape:

```python
@dataclass(frozen=True, slots=True)
class LibraryBoard:
    board_id: str
    display_name: str
    run_path: Path
    revision_token: str


@dataclass(frozen=True, slots=True)
class LibraryDiagnostic:
    path: str
    code: str
    message: str


@dataclass(frozen=True, slots=True)
class LibrarySnapshot:
    boards: tuple[LibraryBoard, ...]
    diagnostics: tuple[LibraryDiagnostic, ...]
```

Set the root to `Tools/HangboardOnboarding/boards`. Scan immediate children only. Reserve dot-prefixed children for transaction machinery. Validate each non-hidden child independently, derive the display name from `product.normalizedName`, require `product.key == directory.name`, derive approved output paths directly from Stage 4 acceptance, and compute `revision_token = sha256((run / "run.json").read_bytes()).hexdigest()` only after complete validation.

Use stable diagnostic codes defined in one private mapping or enum-like constant set: `invalid_path`, `invalid_board_id`, `missing_manifest`, `identity_mismatch`, `invalid_run`, and `invalid_outputs`. Messages must use repository-relative paths.

Delete catalog parsing, `board.json`, `published.json`, `currentVersionId`, revision-directory allocation, and publication-operation metadata from this task's read path. Preserve the existing confinement, symlink, copy, hash, and fsync helpers that still apply.

- [ ] **Step 4: Run the library tests and verify GREEN**

Run:

```bash
rtk python -m pytest Tools/HangboardOnboarding/tests/test_board_library.py -q
```

Expected: all discovery, validation, diagnostic, and copy tests pass.

- [ ] **Step 5: Commit direct discovery**

Run:

```bash
rtk git add Tools/HangboardOnboarding/src/hangboard_vectorizer/board_library.py Tools/HangboardOnboarding/tests/test_board_library.py
rtk git commit -m "Discover canonical hangboard runs directly"
```

---

### Task 3: Publish current packages with recoverable replacement

**Files:**
- Modify: `Tools/HangboardOnboarding/src/hangboard_vectorizer/board_library.py`
- Modify: `Tools/HangboardOnboarding/tests/test_board_library.py`
- Modify: `.gitignore`

**Interfaces:**
- Consumes: `LibraryBoard.revision_token` and complete-run validation from Task 2.
- Produces:
  - `PublishedBoard(board: LibraryBoard, revision_token: str)`
  - `RepositoryBoardLibrary.publish(run_root: Path, board_id: str | None, expected_revision_token: str | None) -> PublishedBoard`
  - private journaled recovery below `boards/.transactions/`.

- [ ] **Step 1: Write failing publication and recovery tests**

Add parameterized tests for new publication, existing replacement, identical retry, changed-current conflict, different-content new-board collision, and failures after each transaction phase. The core expectations should include:

```python
published = library.publish(
    run_root=candidate,
    board_id=existing.board_id,
    expected_revision_token=existing.revision_token,
)
assert published.revision_token != existing.revision_token
assert library.get_board(existing.board_id).revision_token == published.revision_token

retried = library.publish(
    run_root=candidate,
    board_id=existing.board_id,
    expected_revision_token=existing.revision_token,
)
assert retried == published
```

Inject failures before rollback move, after rollback move, after candidate installation, and before cleanup. Instantiate a fresh `RepositoryBoardLibrary`, call `snapshot()`, and assert recovery returns exactly one valid canonical package without losing the prior package. Add an ambiguity test that retains invalid transaction evidence and returns a diagnostic.

- [ ] **Step 2: Run publication tests and verify RED**

Run:

```bash
rtk python -m pytest Tools/HangboardOnboarding/tests/test_board_library.py -q
```

Expected: publication-signature and transaction-recovery failures.

- [ ] **Step 3: Implement optimistic publication without stored versions**

Use this public signature and derive new-board identity from the validated run:

```python
def publish(
    self,
    *,
    run_root: Path,
    board_id: str | None,
    expected_revision_token: str | None,
) -> PublishedBoard:
    candidate = self._validated_package(run_root)
    identifier = candidate.board_id if board_id is None else self._board_id(board_id, "board")
    if identifier != candidate.board_id:
        raise BoardLibraryError("board ID does not match run product key")
    with self._publication_lock():
        self._recover_transactions_locked()
        current = self._optional_board_locked(identifier)
        if current is not None and current.revision_token == candidate.revision_token:
            return PublishedBoard(current, current.revision_token)
        self._require_expected_revision(current, expected_revision_token)
        self._replace_board_locked(candidate, current)
    published = self.get_board(identifier)
    return PublishedBoard(published, published.revision_token)
```

Rules:

- If the canonical token equals the candidate token, return success before conflict checks.
- New publication requires an absent target and uses `run.json.product.key`.
- Existing publication requires `board_id == run.json.product.key` and current token equal to `expected_revision_token`.
- Any other existing target is a conflict that reports expected and current tokens.
- Copy into a same-filesystem transaction candidate, validate the copy, and fsync it before moving paths.
- Never write `publication.json`, `published.json`, `board.json`, a catalog, or a version directory.

Implement a schema-versioned journal with `boardId`, `expectedRevisionToken`, `candidateRevisionToken`, and `phase`. Under the repository `flock` plus in-process lock: fsync candidate and journal, move the prior package into the transaction rollback path, install candidate, fsync the boards root, and remove the transaction.

Recovery must finish a provably valid installed or staged candidate, restore a valid prior package when installation cannot be proven, and retain ambiguous evidence. Call recovery in `__init__` or before the first snapshot and before every publish while holding the same lock.

- [ ] **Step 4: Ignore transaction machinery**

Add exactly:

```gitignore
/Tools/HangboardOnboarding/boards/.transactions/
```

- [ ] **Step 5: Run publication tests and verify GREEN**

Run:

```bash
rtk python -m pytest Tools/HangboardOnboarding/tests/test_board_library.py -q
rtk git diff --check
```

Expected: all library tests pass and no whitespace errors are reported.

- [ ] **Step 6: Commit recoverable publication**

Run:

```bash
rtk git add .gitignore Tools/HangboardOnboarding/src/hangboard_vectorizer/board_library.py Tools/HangboardOnboarding/tests/test_board_library.py
rtk git commit -m "Publish canonical hangboard packages safely"
```

---

### Task 4: Replace repository version IDs with revision tokens in runtime state

**Files:**
- Modify: `Tools/HangboardOnboarding/src/hangboard_vectorizer/workbench_store.py`
- Modify: `Tools/HangboardOnboarding/src/hangboard_vectorizer/workbench.py`
- Modify: `Tools/HangboardOnboarding/tests/test_workbench_store.py`
- Modify: `Tools/HangboardOnboarding/tests/test_workbench.py`
- Modify: `Tools/HangboardOnboarding/tests/test_workbench_end_to_end.py`

**Interfaces:**
- Consumes: Task 2's `LibrarySnapshot`, `LibraryBoard.revision_token`, and Task 3's `publish()`.
- Produces: `BoardRecord.repository_revision_token`, `WorkbenchView.repository_revision_token`, schema-2 runtime manifests, and token-based open/save behavior.

- [ ] **Step 1: Write failing store migration and token tests**

Rename repository-version assertions to revision-token assertions. Add a schema-1 migration test whose manifest contains `repositoryBoardId` and `repositoryVersionId`; loading must preserve the runtime board and all revisions, retain the repository board ID, set the unknown new token to `None`, and rewrite schema 2 only on the next normal store mutation.

Add tests for the relaxed safe invariant:

```python
assert legacy.repository_board_id == "example-board"
assert legacy.repository_revision_token is None
```

A token without a board ID remains invalid. New writes use `repositoryRevisionToken` and never persist `repositoryVersionId` or `publicationOperationId`.

- [ ] **Step 2: Run store tests and verify RED**

Run:

```bash
rtk python -m pytest Tools/HangboardOnboarding/tests/test_workbench_store.py -q
```

Expected: field, schema, and persistence failures.

- [ ] **Step 3: Implement runtime schema 2**

Change the records to:

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
    repository_board_id: str | None = None
    repository_revision_token: str | None = None
```

Remove publication-operation preparation and persistence. Replace the repository version regex with a 64-character lowercase SHA-256 regex. Read schema 1 as described above; write schema 2. Rename link/finalize/publish parameters and methods to use `repository_revision_token` consistently.

- [ ] **Step 4: Run store tests and verify GREEN**

Run:

```bash
rtk python -m pytest Tools/HangboardOnboarding/tests/test_workbench_store.py -q
```

Expected: all runtime persistence and concurrency tests pass.

- [ ] **Step 5: Write failing service tests for token-based open and save**

Update end-to-end fixtures to place complete runs directly below `boards/`. Test that opening the same token is idempotent, opening a changed manifest creates a new runtime revision without deleting old work, saving passes the recorded token, identical save retries succeed, and an unknown legacy token fails safe with a repository conflict.

Add one parameterized `test_product_neutral_repository_replay` using fixture
data named Beastmaker 1000, Metolius Wood Grips Compact II, and Metolius
Simulator 3D. The test body and service parameters must be identical for all
three cases; only generated run data may differ.

- [ ] **Step 6: Run service tests and verify RED**

Run:

```bash
rtk python -m pytest Tools/HangboardOnboarding/tests/test_workbench.py Tools/HangboardOnboarding/tests/test_workbench_end_to_end.py -q
```

Expected: service references to current version IDs and publication operations fail.

- [ ] **Step 7: Implement token-based service coordination**

Change `WorkbenchView.repository_version_id` to `repository_revision_token` and replace `list_library_boards()` with `library_snapshot()`. Open identity comparisons use `LibraryBoard.revision_token`. Save calls:

```python
published = self.__library.publish(
    run_root=revision.run_root,
    board_id=board.repository_board_id,
    expected_revision_token=board.repository_revision_token,
)
```

Finalize the runtime revision with `published.revision_token`. Keep the stable per-repository-board job reservation key and atomic open behavior unchanged.

- [ ] **Step 8: Run service tests and verify GREEN**

Run:

```bash
rtk python -m pytest Tools/HangboardOnboarding/tests/test_workbench_store.py Tools/HangboardOnboarding/tests/test_workbench.py Tools/HangboardOnboarding/tests/test_workbench_end_to_end.py -q
```

Expected: all store and service tests pass.

- [ ] **Step 9: Commit runtime token integration**

Run:

```bash
rtk git add Tools/HangboardOnboarding/src/hangboard_vectorizer/workbench_store.py Tools/HangboardOnboarding/src/hangboard_vectorizer/workbench.py Tools/HangboardOnboarding/tests/test_workbench_store.py Tools/HangboardOnboarding/tests/test_workbench.py Tools/HangboardOnboarding/tests/test_workbench_end_to_end.py
rtk git commit -m "Track repository boards by manifest token"
```

---

### Task 5: Expose boards and diagnostics in the workbench UI

**Files:**
- Modify: `Tools/hold-highlight-editor/server.py`
- Modify: `Tools/hold-highlight-editor/workbench-client.js`
- Modify: `Tools/hold-highlight-editor/workbench-model.js`
- Modify: `Tools/hold-highlight-editor/workbench-controller.js`
- Modify: `Tools/hold-highlight-editor/app.js`
- Modify: `Tools/hold-highlight-editor/index.html`
- Modify: `Tools/hold-highlight-editor/styles.css`
- Modify: `Tools/hold-highlight-editor/tests/test_server.py`
- Modify: `Tools/hold-highlight-editor/tests/workbench_client.test.js`
- Modify: `Tools/hold-highlight-editor/tests/workbench_model.test.js`
- Modify: `Tools/hold-highlight-editor/tests/workbench_controller.test.js`

**Interfaces:**
- Consumes: `WorkbenchService.library_snapshot()` and runtime repository revision tokens from Task 4.
- Produces: `GET /api/library -> {ok, boards, diagnostics}`, `revisionToken`, `repositoryRevisionToken`, and visible per-package diagnostics.

- [ ] **Step 1: Write failing server contract tests**

Change the expected response to:

```json
{
  "ok": true,
  "boards": [
    {
      "boardId": "example-board",
      "displayName": "Example Board",
      "revisionToken": "<64 lowercase hex>"
    }
  ],
  "diagnostics": [
    {
      "path": "broken-board",
      "code": "invalid_run",
      "message": "broken-board: run is not Stage 4 complete"
    }
  ]
}
```

Update workbench payload assertions from `repositoryVersionId` to `repositoryRevisionToken`. Retain loopback Host/Origin, open-job serialization, and public-error redaction tests.

- [ ] **Step 2: Run server tests and verify RED**

Run:

```bash
rtk python -m pytest Tools/hold-highlight-editor/tests/test_server.py -q
```

Expected: old `currentVersionId` and missing diagnostics fail.

- [ ] **Step 3: Implement the HTTP contract**

Serialize `service.library_snapshot().boards` and `.diagnostics` without exposing absolute paths. Rename workbench payload fields to `repositoryRevisionToken`. Do not add a catalog or arbitrary path endpoint.

- [ ] **Step 4: Write failing browser model and controller tests**

Make the client return the complete library payload. Update `openingSections()` to compare `board.revisionToken` with `runtime.repositoryRevisionToken`. Add tests that diagnostics render while valid boards remain selectable and that an empty board list plus diagnostics does not display the misleading “no published boards yet” state by itself.

- [ ] **Step 5: Run Node tests and verify RED**

Run:

```bash
rtk node --test Tools/hold-highlight-editor/tests/*.test.js
```

Expected: client return shape, revision-token comparisons, and diagnostics rendering fail.

- [ ] **Step 6: Implement browser diagnostics and token labels**

Update initial loading to pass `{boards, diagnostics}` through the controller. Keep board cards product-focused; replace the old visible `Version revision-0001` detail with neutral saved-state copy or omit it. Render diagnostics in a compact repository warning region with the relative path and message. Valid board cards remain enabled.

- [ ] **Step 7: Run server and browser tests and verify GREEN**

Run:

```bash
rtk python -m pytest Tools/hold-highlight-editor/tests/test_server.py -q
rtk node --test Tools/hold-highlight-editor/tests/*.test.js
```

Expected: Python server and Node UI tests pass.

- [ ] **Step 8: Commit the API and UI update**

Run:

```bash
rtk git add Tools/hold-highlight-editor
rtk git commit -m "Show canonical repository boards and diagnostics"
```

---

### Task 6: Migrate the accepted board and remove the superseded layout

**Files:**
- Move: `Tools/HangboardOnboarding/reference/metolius-compact-ii/accepted-run/**` to `Tools/HangboardOnboarding/boards/metolius-wood-grips-compact-ii/**`
- Delete: `Tools/HangboardOnboarding/board-library/catalog.json`
- Modify: `scripts/hangboard-tools.sh`
- Modify: `docs/ADDING_A_BOARD.md`
- Modify: `Tools/HangboardOnboarding/README.md`
- Modify: `Tools/HangboardOnboarding/UPSTREAM.md`
- Modify: `Tools/HangboardOnboarding/TESTING.md`
- Modify: `Tools/HangboardOnboarding/tests/test_semantic_benchmark.py`
- Modify: `Tools/HangboardOnboarding/tests/test_workbench_end_to_end.py`

**Interfaces:**
- Consumes: canonical discovery and publication from Tasks 2-5.
- Produces: one committed Compact II package in the canonical location and no active catalog/reference package contract.

- [ ] **Step 1: Record protected accepted-run hashes**

Run before moving files:

```bash
rtk git ls-files -s Tools/HangboardOnboarding/reference/metolius-compact-ii/accepted-run
rtk shasum -a 256 Tools/HangboardOnboarding/reference/metolius-compact-ii/accepted-run/stages/04/attempt-0001/stage-4-normal.png
rtk shasum -a 256 Tools/HangboardOnboarding/reference/metolius-compact-ii/accepted-run/stages/04/attempt-0001/stage-4-product.svg
```

Expected normal PNG SHA-256: `f4c1fa4b4354a412a85be767614a127152a0c0150666e3af3d7cae6cafe33021`.

- [ ] **Step 2: Write the failing checkout-discovery and benchmark-path assertions**

Change the end-to-end checkout test to assert that the real repository snapshot includes `metolius-wood-grips-compact-ii`. Update semantic benchmark test helpers to resolve the canonical directory. Run them before the move and confirm they fail at the new path.

- [ ] **Step 3: Move the complete run without rewriting its contents**

Run:

```bash
rtk mkdir -p Tools/HangboardOnboarding/boards
rtk git mv Tools/HangboardOnboarding/reference/metolius-compact-ii/accepted-run Tools/HangboardOnboarding/boards/metolius-wood-grips-compact-ii
```

Remove empty superseded reference directories if Git no longer tracks content. Delete `Tools/HangboardOnboarding/board-library/catalog.json` with an `apply_patch` deletion so only the canonical location remains.

> **Authoritative repository contract:** This unified plan supersedes the earlier repository-board-library and repository-library residual-remediation plans. Direct discovery of one canonical Stage 4 run per board, with `run.json` revision tokens, is the source of truth; catalog/version layouts and publication-operation records are historical designs only.

- [ ] **Step 4: Update benchmark entrypoints and documentation**

Point `scripts/hangboard-tools.sh benchmark`, benchmark tests, `docs/ADDING_A_BOARD.md`, `README.md`, `UPSTREAM.md`, and `TESTING.md` to `Tools/HangboardOnboarding/boards/<board-id>/`. State that only complete approved runs belong there and all unfinished runs belong under `.context`.

Link the active design to `docs/superpowers/specs/2026-08-07-unified-hangboard-repository-design.md`; label the prior repository-board-library spec superseded rather than deleting historical design records.

- [ ] **Step 5: Verify exact content preservation and canonical discovery**

Run:

```bash
rtk shasum -a 256 Tools/HangboardOnboarding/boards/metolius-wood-grips-compact-ii/stages/04/attempt-0001/stage-4-normal.png
rtk shasum -a 256 Tools/HangboardOnboarding/boards/metolius-wood-grips-compact-ii/stages/04/attempt-0001/stage-4-product.svg
rtk python -m pytest Tools/HangboardOnboarding/tests/test_semantic_benchmark.py Tools/HangboardOnboarding/tests/test_workbench_end_to_end.py -q
rtk scripts/hangboard-tools.sh benchmark
```

Expected: hashes match Step 1, the real checkout exposes Compact II, and semantic replay makes zero live model calls.

- [ ] **Step 6: Assert no active code or operator docs retain the old contract**

Run:

```bash
rtk rg -n 'board-library|currentVersionId|repositoryVersionId|versions/revision-|reference/metolius-compact-ii/accepted-run' Tools scripts docs/ADDING_A_BOARD.md --glob '!docs/superpowers/specs/2026-08-07-repository-board-library-design.md' --glob '!docs/superpowers/plans/2026-08-07-repository-board-library.md' --glob '!docs/superpowers/plans/2026-08-07-repository-library-residual-remediation.md'
```

Expected: no matches in production code, current tests, current operator docs, or browser code. Historical superseded specs and plans may still describe the prior design.

- [ ] **Step 7: Commit the migration**

Run:

```bash
rtk git add .gitignore Tools/HangboardOnboarding scripts/hangboard-tools.sh docs/ADDING_A_BOARD.md
rtk git commit -m "Unify committed hangboard packages"
```

---

### Task 7: Full verification and local visual checkpoint

**Files:**
- Modify only if verification exposes a defect, with a failing regression test first.

**Interfaces:**
- Consumes: the complete unified repository implementation.
- Produces: verified tests, unchanged visual artifacts, and a running local workbench showing the committed board.

- [ ] **Step 1: Run all Python and browser tests**

Run:

```bash
rtk python -m pytest Tools/HangboardOnboarding/tests Tools/hold-highlight-editor/tests/test_server.py -q
rtk node --test Tools/hold-highlight-editor/tests/*.test.js
```

Expected: all tests pass with no skips introduced for this work.

- [ ] **Step 2: Run static and repository checks**

Run:

```bash
rtk python -m compileall -q Tools/HangboardOnboarding/src Tools/hold-highlight-editor/server.py
rtk node --check Tools/hold-highlight-editor/app.js
rtk node --check Tools/hold-highlight-editor/workbench-client.js
rtk node --check Tools/hold-highlight-editor/workbench-controller.js
rtk node --check Tools/hold-highlight-editor/workbench-model.js
rtk git diff --check
rtk git status --short --branch
```

Expected: compile, syntax, and diff checks pass; only intentional commits remain.

- [ ] **Step 3: Recheck protected visual hashes**

Run:

```bash
rtk shasum -a 256 Tools/HangboardOnboarding/boards/metolius-wood-grips-compact-ii/stages/04/attempt-0001/stage-4-normal.png
rtk shasum -a 256 Tools/HangboardOnboarding/boards/metolius-wood-grips-compact-ii/stages/04/attempt-0001/stage-4-product.svg
```

Expected: byte-identical values from Task 6; no visual-pipeline output changed.

- [ ] **Step 4: Start the workbench and verify the repository checkpoint**

Restart the existing guided workbench using the repository root and ignored runtime workspace, then verify:

```bash
rtk curl --fail --silent http://127.0.0.1:4173/api/library
```

Expected: Compact II appears immediately with a revision token and no catalog registration. Open the local browser checkpoint and confirm the published-board card is visible and selectable; no generated-board visual judgment is required because image bytes did not change.

- [ ] **Step 5: Perform final internal reviews**

Use `superpowers:requesting-code-review` for a spec-compliance review and a code-quality review. Address every load-bearing finding with a regression test and rerun Steps 1-3.

- [ ] **Step 6: Record the verified head**

Run:

```bash
rtk git status --short --branch
rtk git log -8 --oneline --decorate
```

Expected: a clean worktree on `codex/local-hangboard-workbench` with the implementation commits above the reconciliation commit.
