# Unified Hangboard Repository Design

**Date:** 2026-08-07

**Supersedes:** `2026-08-07-repository-board-library-design.md`

## Summary

Store each published hangboard as one self-describing, Stage 4-complete
onboarding run under `Tools/HangboardOnboarding/boards/`. The workbench
discovers those directories directly and uses Git history for previous
published states. It does not maintain a catalog, mutable board pointer,
published-output index, or repository-local revision hierarchy.

The repository package is the source of truth for onboarding and workbench
editing. Hang Ten's Swift board definitions remain downstream consumers and
are outside this change. URL, upload, and CLI workflows remain interchangeable
producers of the same run contract.

## Goals

- Give the workbench one canonical location for every committed board.
- Discover committed boards without manual registration.
- Open and edit a board regardless of which programmatic tool produced it.
- Commit only complete, visually approved board runs.
- Use Git, rather than nested repository directories, to version published
  board states.
- Keep unfinished revisions in ignored runtime storage.
- Preserve the existing product-neutral onboarding and rendering pipeline.

## Non-goals

- Changing Hang Ten's Swift board models or making the app load onboarding
  packages directly.
- Improving generated illustrations or adding product-specific pipeline code,
  coordinates, masks, templates, inventories, or tuning.
- Committing incomplete onboarding runs.
- Running Git commands from the workbench.
- Providing long-term discovery compatibility for superseded `reference/` or
  `board-library/` layouts.
- Introducing a database or remote service.

## Canonical Repository Layout

The repository root for published boards is:

```text
Tools/HangboardOnboarding/boards/
  <board-id>/
    run.json
    inputs/
    stages/
    approvals/
```

Each immediate, non-hidden child directory is one complete onboarding run. Its
directory name is the stable `boardId` and must equal `run.json.product.key`.
The display name comes from `run.json.product.normalizedName`.

The full run is retained because editing may fork any approved stage. The
`approvals/` records bind each human review decision to the exact candidate
artifacts, review image, stage, and run identity. They are audit lineage, not
repository versions.

The approved Stage 4 acceptance record already identifies and hashes the four
consumer-facing outputs:

- geometry definition;
- normal board image;
- selectable SVG;
- highlight definition.

Consequently, the repository does not duplicate this information in
`catalog.json`, `board.json`, or `published.json`. It also does not contain
`versions/revision-*` directories. A prior board state is retrieved through
Git history.

## Board Identity and Revision Identity

`boardId` is a lowercase, path-safe product key. It is immutable after a board
is first published. Directory name and `run.json.product.key` disagreement is
a validation error. New-board publication uses the run's product key and
fails if that key names a different existing board.

The repository revision token is the SHA-256 of the exact `run.json` bytes
after complete-run validation. The manifest hashes the accepted source,
stages, approvals, and output lineage, so this token is a compact optimistic
concurrency identity. It is an API and runtime token only; it is not stored in
another repository manifest.

Changing a display name does not change `boardId`. Any workflow that supports
such a rename must preserve the existing product key in the completed run.

## Discovery

`RepositoryBoardLibrary` scans only the immediate children of
`Tools/HangboardOnboarding/boards/`. Hidden children are reserved for
transaction recovery and are never board candidates. Symlinked children are
rejected.

For every non-hidden child, discovery validates:

1. the directory and `run.json` are confined below the boards root;
2. the directory name is a valid board ID and equals the run product key;
3. the run is Stage 4 complete;
4. all five stage acceptances and approvals form a valid hash-bound lineage;
5. the approved Stage 4 outputs exist and match their recorded hashes.

Discovery returns valid boards sorted by case-insensitive display name and
then `boardId`. Invalid directories are reported as structured diagnostics
with their relative path and stable error code. One invalid package does not
hide valid boards, and invalid packages are never silently omitted.

There is no catalog to update or reconcile. Committing a valid board directory
is sufficient to make it discoverable.

## Runtime Workspace and User Flow

Unfinished work remains under the ignored runtime root:

```text
.context/hangboard-workbench/
```

The browser never asks for a repository path, catalog path, or CLI run
directory. Its opening screen continues to show:

1. **Boards in this repository** from canonical discovery;
2. **In progress** from runtime records;
3. **Create board** using a product name plus URL or upload.

Opening a repository board validates it, atomically copies its complete run
into the runtime workspace, and records its `boardId` and repository revision
token. The canonical package is never edited in place. Reopening the same
revision is idempotent; opening a newer committed revision preserves existing
local work and creates a new runtime revision.

URL, upload, and CLI tooling create ordinary runtime runs. The workbench does
not care which tool produced a run. A board joins the repository list only
after its selected runtime revision reaches a valid, approved Stage 4 state
and is saved.

## Save and Conflict Semantics

Saving performs the following steps under a repository publication lock:

1. Validate the selected runtime run as Stage 4 complete and derive its
   approved outputs from Stage 4 acceptance.
2. Copy it to a hidden sibling staging location and validate the copied run.
3. Compute the candidate repository revision token.
4. For a new board, require the canonical target to be absent. For an existing
   board, require its current token to match the token recorded when editing
   began.
5. Replace the canonical board directory using the recoverable transaction
   described below.
6. Record the new revision token in the runtime store and mark that revision
   saved.

If the current canonical package already has the candidate token, the save is
an idempotent success. Otherwise, a missing expected target or token mismatch
is a conflict. The response reports the expected and current tokens without
changing either the runtime run or repository package.

Saving leaves ordinary working-tree additions, modifications, and deletions
for the user to review and commit. The service never invokes Git.

## Recoverable Directory Replacement

Replacing a non-empty directory is not a single portable filesystem operation,
so the library uses a short, journaled swap while all library readers and
writers hold the same repository lock.

Transaction state lives beneath an ignored
`Tools/HangboardOnboarding/boards/.transactions/` directory on the same
filesystem. A transaction contains the validated candidate, the prior package
when one exists, and a small journal containing `boardId`, expected token,
candidate token, and phase.

Publication fsyncs the candidate and journal before moving the current package
to the transaction's rollback location, moves the candidate into the canonical
path, fsyncs the boards directory, and then removes the transaction. Locked
readers never observe the intermediate absence.

On startup and before each publication, recovery examines incomplete journals:

- If the canonical target is the valid candidate, recovery completes cleanup.
- If the target is absent and a valid candidate is staged, recovery completes
  installation.
- If candidate installation cannot be proven valid and a prior package exists,
  recovery restores the prior package.
- Ambiguous or invalid transaction state produces a diagnostic and is not
  deleted automatically.

The transaction directory is runtime machinery, not board history, and must
remain ignored by Git.

## HTTP Contract

The guided workbench keeps the same conceptual endpoints with a smaller
repository representation:

- `GET /api/library` returns `boards` and `diagnostics`. Each board includes
  `boardId`, `displayName`, and `revisionToken`.
- `POST /api/library/<board-id>/open` opens the currently discovered package.
- `GET /api/boards` lists runtime and in-progress work.
- `POST /api/boards` and `POST /api/boards/upload` retain URL and upload
  creation.
- `POST /api/boards/<runtime-board-id>/save` publishes the selected complete
  runtime revision using its recorded repository token.

The browser still has no arbitrary repository-path or run-directory input.
The internal run-import capability may remain available to CLI and tests, but
it is not a separate repository discovery mechanism.

All mutating requests retain loopback Host and Origin protection and existing
per-board job serialization. Repository publication additionally uses the
repository lock so separate server processes cannot race.

## Migration

This change performs a one-time repository migration:

1. Move the committed Compact II complete run from
   `reference/metolius-compact-ii/accepted-run/` to
   `boards/metolius-wood-grips-compact-ii/` without changing its files.
2. Point the semantic replay benchmark at the canonical board package.
3. Remove the empty `board-library/catalog.json` and the catalog, pointer,
   published-manifest, and nested-version contract from code and tests.
4. Update onboarding, workbench, and contributor documentation to name
   `boards/<board-id>/` as the only committed board location.
5. Preserve the accepted Compact II file hashes during the move.

The production loader does not scan both layouts. Tests may construct legacy
trees solely to verify a migration helper, but compatibility paths do not
remain in normal discovery.

## Errors and Diagnostics

Library-wide failures, such as an inaccessible boards root or unresolved
transaction, return a stable service error. Per-board validation failures are
returned in `diagnostics` while other valid boards remain usable. Diagnostics
identify repository-relative paths and never expose arbitrary host paths.

Opening a board that became invalid after discovery fails before copying any
runtime state. Save validation and conflict failures leave both the canonical
package and runtime work unchanged. Recoverable temporary state is cleaned up;
ambiguous recovery evidence is retained for inspection.

## Verification

### Unit tests

- Direct directory discovery, deterministic ordering, and identity matching.
- Complete-run and approved-output validation.
- Symlink and path-confinement rejection.
- Per-board diagnostics without suppressing valid boards.
- New publication, existing replacement, and identical retry behavior.
- Optimistic token conflicts and cross-process locking.
- Injected failures and recovery at every swap phase.

### Service and API tests

- Every valid committed directory appears without catalog registration.
- Repository boards open without a user-supplied path.
- Newer Git working-tree content opens without discarding existing runtime
  revisions.
- URL and upload creation remain unchanged.
- Save creates or replaces exactly one canonical package and never invokes
  Git.
- Library responses contain valid boards alongside actionable diagnostics.
- Host and Origin protections remain enforced.

### Browser tests

- The Compact II board appears on first launch after migration.
- Selecting a repository board opens its current saved state.
- In-progress and repository boards remain separate.
- Successful save makes a new board discoverable without catalog mutation.
- Validation and conflict diagnostics are visible and actionable.

### Product-neutral replay

Run the same discover, open, revise, save, and reopen test code against fixture
packages for Beastmaker 1000, Metolius Wood Grips Compact II, and Metolius
Simulator 3D. Product names, materials, dimensions, regions, and output hashes
are fixture data only. Production code and parameters remain identical.

The migration must not change accepted image bytes or introduce any visual
pipeline behavior. Existing visual-review checkpoints remain the only points
that require user judgment.

## Acceptance Criteria

- `Tools/HangboardOnboarding/boards/<board-id>/` is the only committed
  onboarding/workbench board location.
- Each board directory is a complete, self-describing run whose directory name
  matches its product key.
- No catalog, board pointer, published-output duplicate, or repository-local
  version hierarchy remains.
- The workbench discovers the committed Compact II board automatically.
- URL, upload, and CLI runs publish through the same validated package path.
- Existing-board saves detect concurrent repository changes and identical
  retries succeed.
- Interrupted saves recover without silently losing the prior valid package.
- Git history is the sole history of published board states.
- The Swift app and visual-generation behavior remain outside the change.
