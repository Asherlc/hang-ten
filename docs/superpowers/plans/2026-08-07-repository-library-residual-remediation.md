# Repository Library Residual Remediation Implementation Plan

> **Historical plan:** Superseded by `2026-08-07-unified-hangboard-repository.md`. Direct discovery and canonical `run.json` revision tokens are authoritative; persisted publication-operation identity and nested immutable versions below are preserved only as history.

> **For agentic workers:** REQUIRED SUB-SKILL: Use a fresh subagent for every implementation or configuration task, with separate implementation and review checkpoints for each task. Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Resolve the four load-bearing residual findings from the repository-library final review without weakening repository confinement, optimistic conflicts, or job recovery.

**Architecture:** Treat the canonical repository root as the trusted boundary and perform no-follow traversal only below it; persist a globally unique publication operation on the runtime revision and reconcile it against exact output evidence across immutable version history; separate a job’s logical board identity from its stable conflict key so repository opens and linked-board mutations serialize throughout the whole job lifetime.

**Tech Stack:** Python 3.11, `pathlib`, `os`/`fcntl`, UUID, JSON, `ThreadingHTTPServer`, vanilla JavaScript, Node built-in test runner, pytest 8+

## Global Constraints

- The production workflow must remain programmatic, repeatable, scalable, and product-neutral.
- Do not add product-specific code paths, coordinates, masks, hold inventories, templates, or tuning.
- The trusted repository root may be supplied through a filesystem alias; symlinks beneath that canonical root must never be traversed for repository-library reads or writes.
- Validation must happen before any directory creation or write through an untrusted descendant.
- Publication retry identity must be globally unique, durably persisted before publication, and bound to the exact approved Stage 4 output evidence.
- Reconciliation must search immutable version history without converting an unrelated stale save into success.
- Repository opens and every mutation of their linked runtime board must use one stable conflict key for the entire accepted job.
- Logical job/board identity in API payloads must remain distinct from internal conflict-lock identity.
- Existing package/runtime manifests and direct programmatic callers remain backward compatible.
- Save never invokes Git, and no protected image may change.

---

### Task 1: Canonical Trusted Root and No-Follow Descendant Creation

**Files:**
- Modify: `Tools/HangboardOnboarding/src/hangboard_vectorizer/board_library.py`
- Modify: `Tools/HangboardOnboarding/tests/test_board_library.py`

**Interfaces:**
- Consumes: existing `RepositoryBoardLibrary` public API and repository layout.
- Produces: a canonical trusted root plus descendant validation/creation that performs no write before proving each existing component is non-symlinked.

- [ ] **Step 1: Add focused failing boundary regressions**

```python
def test_publish_rejects_descendant_symlink_before_creating_outside(tmp_path: Path) -> None:
    repository, outside = _repository_with_symlinked_tools(tmp_path)
    library = RepositoryBoardLibrary(repository)
    with pytest.raises(BoardLibraryError, match="symlink"):
        library.publish(
            display_name="Example Board",
            run_root=_complete_fixture_run(tmp_path / "run"),
            board_id=None,
            expected_current_version_id=None,
        )
    assert not (outside / "HangboardOnboarding" / "board-library" / "boards").exists()


def test_repository_root_alias_is_trusted_but_descendant_symlinks_are_not(tmp_path: Path) -> None:
    physical = _empty_repository(tmp_path / "physical")
    alias = tmp_path / "repository-alias"
    alias.symlink_to(physical, target_is_directory=True)
    library = RepositoryBoardLibrary(alias)
    published = library.publish(
        display_name="Example Board",
        run_root=_complete_fixture_run(tmp_path / "run"),
        board_id=None,
        expected_current_version_id=None,
    )
    assert published.board.board_id == "example-board"
```

- [ ] **Step 2: Run focused tests and verify both current defects**

Run: `rtk pytest -q Tools/HangboardOnboarding/tests/test_board_library.py -k 'descendant_symlink_before or root_alias'`

Expected: the first test observes an outside directory created before failure;
the second rejects the trusted alias.

- [ ] **Step 3: Implement the trusted-root boundary**

Canonicalize an existing repository root once with `resolve(strict=True)` and
require it to be a directory. All later confinement comparisons start from this
canonical root. Do not reject symlink components above or including that trusted
root.

Replace create-then-check behavior with one private helper that walks the
relative components beneath the trusted root. For each component, use `lstat`
or an `O_NOFOLLOW` directory descriptor before descent; reject existing
symlinks/non-directories, and create a missing directory only from its already
validated parent before reopening/verifying it. The helper must never call
`mkdir(parents=True)` across an unvalidated chain.

Use this helper before catalog/package/version staging and publication-lock
creation. Keep existing read-time member/tree symlink validation.

- [ ] **Step 4: Run library and complete-run coverage**

Run: `rtk pytest -q Tools/HangboardOnboarding/tests/test_board_library.py`

Expected: all library tests pass, including no outside side effect and trusted
root alias compatibility.

- [ ] **Step 5: Commit**

```bash
rtk git add Tools/HangboardOnboarding/src/hangboard_vectorizer/board_library.py Tools/HangboardOnboarding/tests/test_board_library.py
rtk git commit -m "Constrain repository writes below trusted root"
```

### Task 2: Durable Globally Unique Publication Operations

**Files:**
- Modify: `Tools/HangboardOnboarding/src/hangboard_vectorizer/board_library.py`
- Modify: `Tools/HangboardOnboarding/src/hangboard_vectorizer/workbench_store.py`
- Modify: `Tools/HangboardOnboarding/src/hangboard_vectorizer/workbench.py`
- Modify: `Tools/HangboardOnboarding/tests/test_board_library.py`
- Modify: `Tools/HangboardOnboarding/tests/test_workbench_store.py`
- Modify: `Tools/HangboardOnboarding/tests/test_workbench_end_to_end.py`

**Interfaces:**
- Consumes: Task 1 safe library paths and existing atomic `publish_repository_revision()`.
- Produces: persisted per-runtime-revision operation UUID, exact published-evidence digest, and history-wide idempotent reconciliation.

- [ ] **Step 1: Add failing operation-identity tests**

```python
def test_prepare_publication_operation_is_persisted_and_stable(tmp_path: Path) -> None:
    store, board, revision = _populated_store(tmp_path)
    first = store.prepare_repository_publication(board.id, revision.id)
    second = store.prepare_repository_publication(board.id, revision.id)
    assert first == second
    assert UUID(first).version == 4
    assert store.read_revision(board.id, revision.id).publication_operation_id == first


def test_independent_workspaces_never_share_publication_operation(tmp_path: Path) -> None:
    first = _complete_runtime_board(tmp_path / "workspace-a")
    second = _complete_runtime_board(tmp_path / "workspace-b")
    assert first.store.prepare_repository_publication(first.board_id, first.revision_id) != second.store.prepare_repository_publication(second.board_id, second.revision_id)
```

Old revision records without `publicationOperationId` must continue loading as
`None`. The preparing method performs one atomic manifest replacement and never
changes an existing operation ID.

- [ ] **Step 2: Add failing exact-evidence/history reconciliation tests**

```python
def test_reconciliation_requires_unique_operation_and_exact_published_evidence(tmp_path: Path) -> None:
    library, entry = _complete_library(tmp_path)
    run = _complete_fixture_run(tmp_path / "run")
    first = library.publish(
        display_name=entry.display_name,
        run_root=run,
        board_id=entry.board_id,
        expected_current_version_id=entry.current_version_id,
        publication_operation_id=str(uuid4()),
    )
    with pytest.raises(BoardLibraryError, match="conflict"):
        library.publish(
            display_name=entry.display_name,
            run_root=run,
            board_id=entry.board_id,
            expected_current_version_id=entry.current_version_id,
            publication_operation_id=str(uuid4()),
        )
    assert first.version_id == "revision-0002"


def test_retry_finds_its_exact_operation_after_a_newer_version_is_current(tmp_path: Path) -> None:
    library, entry, run = _published_operation_fixture(tmp_path)
    retried = library.publish(
        display_name=entry.display_name,
        run_root=run,
        board_id=entry.board_id,
        expected_current_version_id=entry.current_version_id,
        publication_operation_id=entry.operation_id,
    )
    assert retried.version_id == "revision-0002"
    assert library.get_board(entry.board_id).current_version_id == "revision-0003"
```

Add a cross-workspace service regression: two workspaces with identical local
board/revision IDs open the same repository version; after workspace A saves,
workspace B must conflict rather than reconcile to A's version.

- [ ] **Step 3: Implement operation persistence and exact digest**

Append `publication_operation_id: str | None = None` to `RevisionRecord`; persist
it as optional `publicationOperationId`. Add:

```python
def prepare_repository_publication(self, board_id: str, revision_id: str) -> str: ...
```

Generate `str(uuid4())` only when absent and atomically replace the board
manifest. `WorkbenchService.save()` calls this before `library.publish()` and
passes it as `publication_operation_id`.

In `board_library.py`, derive a canonical SHA-256 digest over the exact approved
Stage 4 published output records (paths plus hashes for definition, image,
selectable SVG, and highlights). Persist schema-versioned publication metadata
containing operation UUID, run identity, and exact evidence digest. Optional
metadata remains valid for historical/direct callers.

When an operation UUID is supplied, search all immutable versions in the target
board—or all catalog boards for a new-board retry—before optimistic conflict
checks. Reconcile only when operation UUID, run identity, and exact evidence
digest all match; mismatched evidence for the same UUID is corruption. A
different UUID never reconciles, even when runtime IDs/content happen to match.

- [ ] **Step 4: Run library/store/service coverage**

Run: `rtk pytest -q Tools/HangboardOnboarding/tests/test_board_library.py Tools/HangboardOnboarding/tests/test_workbench_store.py Tools/HangboardOnboarding/tests/test_workbench.py Tools/HangboardOnboarding/tests/test_workbench_end_to_end.py`

Expected: all pass, including cross-workspace stale conflict and history retry.

- [ ] **Step 5: Commit**

```bash
rtk git add Tools/HangboardOnboarding/src/hangboard_vectorizer/board_library.py Tools/HangboardOnboarding/src/hangboard_vectorizer/workbench_store.py Tools/HangboardOnboarding/src/hangboard_vectorizer/workbench.py Tools/HangboardOnboarding/tests/test_board_library.py Tools/HangboardOnboarding/tests/test_workbench_store.py Tools/HangboardOnboarding/tests/test_workbench_end_to_end.py
rtk git commit -m "Make repository publication retries globally idempotent"
```

### Task 3: Stable Conflict Keys Across Repository Open and Mutation

**Files:**
- Modify: `Tools/hold-highlight-editor/job_manager.py`
- Modify: `Tools/hold-highlight-editor/server.py`
- Modify: `Tools/hold-highlight-editor/tests/test_job_manager.py`
- Modify: `Tools/hold-highlight-editor/tests/test_server.py`

**Interfaces:**
- Consumes: `WorkbenchService.library_open_reservation_key()` and repository link metadata.
- Produces: separate logical `board_id` and internal `conflict_key` in `BoardJobManager.submit()` plus stable server key selection for opens and linked mutations.

- [ ] **Step 1: Add failing job-manager identity/key separation test**

```python
def test_submit_uses_conflict_key_without_changing_logical_board_identity() -> None:
    manager = BoardJobManager(max_workers=2)
    first = manager.submit("board-0001", _blocking_job, conflict_key="repository-board:example")
    with pytest.raises(BoardJobConflict):
        manager.submit("board-0002", lambda: None, conflict_key="repository-board:example")
    assert manager.get(first.id).board_id == "board-0001"
```

Add cleanup/event coordination using the existing job-manager test patterns.

- [ ] **Step 2: Add the key-transition server regression**

Build a fake service whose first repository open exposes the linked runtime
board before it releases its blocking operation. While that first job remains
running:

- a second open of the same repository board returns HTTP 409;
- a mutation for the newly linked runtime board returns HTTP 409;
- accepted job payloads retain their expected logical board IDs.

The regression must exercise the state after the repository-to-runtime mapping
exists, not only before it.

- [ ] **Step 3: Implement separate conflict keys**

Extend:

```python
def submit(
    self,
    board_id: str,
    operation: Callable[[], object],
    *,
    conflict_key: str | None = None,
) -> BoardJob: ...
```

Job records and API payloads retain `board_id`; active-lock bookkeeping uses
`conflict_key or board_id` and releases that exact key on terminal completion.

Add `WorkbenchService.mutation_reservation_key(board_id: str) -> str`, returning
`repository-board:<repositoryBoardId>` for a linked runtime board and the runtime
board ID otherwise. `library_open_reservation_key()` always returns that same
repository key. Change the server `_submit_job()` seam to accept a distinct
conflict key and route every existing board mutation through
`mutation_reservation_key()`. Creation jobs retain unique keys.

- [ ] **Step 4: Run job/server and browser recovery suites**

Run: `rtk pytest -q Tools/hold-highlight-editor/tests/test_job_manager.py Tools/hold-highlight-editor/tests/test_server.py`

Expected: all Python job/server tests pass, including post-link transition.

Run: `rtk node --test Tools/hold-highlight-editor/tests/workbench_controller.test.js Tools/hold-highlight-editor/tests/workbench_app.test.js`

Expected: accepted repository-open polling recovery tests remain green.

- [ ] **Step 5: Run full verification**

Run: `rtk pytest -q Tools/HangboardOnboarding/tests Tools/hold-highlight-editor/tests/test_server.py Tools/hold-highlight-editor/tests/test_job_manager.py`

Expected: all Python tests pass.

Run: `rtk node --test Tools/hold-highlight-editor/tests/*.test.js`

Expected: all Node tests pass.

Run: `rtk python -m py_compile Tools/HangboardOnboarding/src/hangboard_vectorizer/*.py Tools/hold-highlight-editor/*.py`

Run: `rtk node --check Tools/hold-highlight-editor/app.js && rtk node --check Tools/hold-highlight-editor/workbench-controller.js && rtk node --check Tools/hold-highlight-editor/workbench-client.js`

Run: `rtk git diff --check`

Run: `rtk git diff --name-only origin/codex/add-hangboard-onboarding...HEAD -- '*.png' '*.jpg'`

Expected: syntax/compile/diff commands exit 0 and no protected image appears.

- [ ] **Step 6: Commit**

```bash
rtk git add Tools/hold-highlight-editor/job_manager.py Tools/hold-highlight-editor/server.py Tools/hold-highlight-editor/tests/test_job_manager.py Tools/hold-highlight-editor/tests/test_server.py
rtk git commit -m "Stabilize repository board job conflicts"
```
