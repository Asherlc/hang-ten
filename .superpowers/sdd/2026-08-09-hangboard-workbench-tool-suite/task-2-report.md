# Task 2 implementation report

## Status

Blocked before implementation: the required workbench foundation is absent from
the mandated current HEAD (`8333181326dc716cce56b3fe4b7cbe49adacdb07`).

## Evidence

- `Tools/HangboardOnboarding/src/hangboard_vectorizer/workbench.py` does not
  exist.
- `RepositoryBoardLibrary`, the workbench store, and the hold editor job
  manager do not exist in this checkout.
- The specified new focused test files do not exist either.
- The required test command could not start because this environment's
  `python3` has no `pytest` installed:
  `No module named pytest`.

The required foundation exists only on the divergent historical commit
`dafff53` (the local workbench replacement), where it spans workbench service,
board library, workbench store, review editing, job manager, server, and UI
files. Importing that history into this task would be a substantial unrelated
change and would violate the instruction not to begin Task 3+ UI work.

## Files changed

- `.superpowers/sdd/2026-08-09-hangboard-workbench-tool-suite/task-2-report.md`

## Tests

Attempted:

```sh
rtk python3 -m pytest Tools/HangboardOnboarding/tests/test_workbench_promotion.py Tools/HangboardOnboarding/tests/test_workbench_validation.py Tools/hold-highlight-editor/tests/test_server.py -q
```

Output:

```text
/opt/homebrew/opt/python@3.12/bin/python3.12: No module named pytest
```

## Assumptions and warnings

- The current HEAD and isolated worktree are intentional, as required by the
  task brief.
- No production or test files were changed, and no commit was created, because
  the missing prerequisite layer must be restored or explicitly authorized
  before Task 2 can be implemented safely.

## Continuation — implemented after foundation merge

The authorized foundation merge `5a6be6c` and promotion-baseline fix
`1686b85` supplied the required workbench, repository library, job manager,
and clean native targets. Task 2 is implemented only in the isolated
`hangboard-workbench-tool-suite` worktree.

### Files changed

- `Tools/HangboardOnboarding/src/hangboard_vectorizer/workbench.py`
- `Tools/HangboardOnboarding/src/hangboard_vectorizer/workbench_promotion.py`
- `Tools/HangboardOnboarding/src/hangboard_vectorizer/workbench_validation.py`
- `Tools/HangboardOnboarding/tests/test_workbench_promotion.py`
- `Tools/HangboardOnboarding/tests/test_workbench_validation.py`
- `Tools/hold-highlight-editor/server.py`
- `Tools/hold-highlight-editor/tests/test_server.py`

### Focused tests

Ran with `.context/hangboard-suite-venv`:

```sh
rtk .context/hangboard-suite-venv/bin/python -m pytest Tools/HangboardOnboarding/tests/test_workbench_promotion.py Tools/HangboardOnboarding/tests/test_workbench_validation.py Tools/hold-highlight-editor/tests/test_server.py -q
```

Output completed successfully (93 collected tests; no failures):

```text
........................................................................ [ 77%]
...........
```

The focused tests cover active-revision binding, stale tokens, dirty native
targets, no-write preview behavior, bounded plan-library invocation, safe
job-result JSON, and all five requested routes.

### Assumptions and warnings

- Browser promotion requests supply the explicit versioned iOS profile as a
  `profile` JSON object; it is parsed in memory and is never written to the
  onboarding package.
- GET promotion and validation routes verify the selected board/revision
  context. Preview, save, and validation execution remain job-backed POST
  operations, with their typed result returned from job polling.
- `validation_report` runs only `scripts/export-plan-library.sh --check` with
  a 30-second subprocess timeout. It creates no simulator and does not write
  repository files; a real run still requires the local Xcode command-line
  tools used by that existing script.

## Review follow-up — promotion identity and preview retrieval

Addressed review findings against the Task 2 service and server contract.

### Identity safety

- Added one shared `WorkbenchService` promotion-context check used by both
  `preview_promotion` and `save_promotion`.
- It resolves the active `BoardRecord`, requires its repository identity, and
  rejects a profile whose `board_id` differs from `repository_board_id` before
  native preview generation or any save operation. It is rechecked after
  generation and before cache publication or the write call.
- Regression tests inject a generation sentinel for mismatched profiles in
  both paths and assert that all native target files are unchanged.

### Cached promotion preview GET

- Added a lock-protected, process-local `PromotionPreview` cache keyed by
  `(board_id, revision_id)`. Only successful `preview_promotion` calls add an
  entry; switching the active revision isolates and evicts prior entries.
- Added `get_promotion_preview`, which validates the requested active revision
  and returns the cached preview or `None`; it performs no generation, writes,
  or profile inference.
- `GET /api/boards/{board}/promotion?revisionId=...` now returns
  `boardId`, `revisionId`, and serialized `preview` (or `null` before a
  preview). POST preview/save remains profile-explicit and job-backed.

### Verification

Ran with `.context/hangboard-suite-venv`:

```sh
rtk .context/hangboard-suite-venv/bin/python -m pytest Tools/HangboardOnboarding/tests/test_workbench_promotion.py Tools/HangboardOnboarding/tests/test_workbench_validation.py Tools/hold-highlight-editor/tests/test_server.py -q
rtk git diff --check
rtk .context/hangboard-suite-venv/bin/python -m py_compile Tools/HangboardOnboarding/src/hangboard_vectorizer/workbench.py Tools/hold-highlight-editor/server.py
```

All focused tests passed, the diff check was clean, and both edited Python
modules compiled successfully. `ios_promotion.py` was not modified, preserving
its main-relative target conflict guard.

## Continuation — native iOS profile identity adapter

The review follow-up identified that the canonical iOS promotion profile uses
the native ID `metolius.wood-grips.compact-ii`, while the repository package
uses the stable path ID `metolius-wood-grips-compact-ii`. Direct equality in
the shared promotion context therefore rejected a valid profile before preview
generation.

### Fix

- Added a documented, deterministic adapter in `workbench.py` that maps only
  native iOS dot separators to repository hyphen separators before identity
  comparison.
- The adapter is used only for profile-to-repository identity comparison.
  Missing repository identity and mismatched profiles still raise before
  generation or writes; revision and preview-token checks are unchanged.
- Left the iOS promotion profile schema and its fixture unchanged.

### Regression coverage

- Added a test that reads the canonical fixture unchanged, proves its dotted
  ID is preserved, and verifies a preview succeeds without modifying native
  checkout targets.
- Existing mismatch tests keep generation guarded by a sentinel and assert all
  native target files remain unchanged for both preview and save paths.

### Verification

Ran with `.context/hangboard-suite-venv`:

```sh
rtk .context/hangboard-suite-venv/bin/python -m pytest Tools/HangboardOnboarding/tests/test_workbench_promotion.py::test_preview_accepts_the_canonical_ios_profile_without_rewriting_its_board_id -q
rtk .context/hangboard-suite-venv/bin/python -m pytest Tools/HangboardOnboarding/tests/test_workbench_promotion.py Tools/HangboardOnboarding/tests/test_workbench_validation.py Tools/hold-highlight-editor/tests/test_server.py -q
rtk .context/hangboard-suite-venv/bin/python -m py_compile Tools/HangboardOnboarding/src/hangboard_vectorizer/workbench.py
rtk git diff --check
```
