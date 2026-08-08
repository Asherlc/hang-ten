# Repository Board Library Design

**Date:** 2026-08-07

## Summary

Turn the local hangboard workbench into a repository-backed board editor. The
opening screen lists every valid board package registered in the repository,
regardless of whether its contents were produced by the browser, the CLI, or
another programmatic tool. URL and upload remain the two ways to create a new
board. The user never supplies a CLI run directory in the browser.

Saving publishes an immutable board version into the same repository and
updates the repository catalog. It deliberately does not run Git: the resulting
working-tree changes remain available for normal review and commit workflows.

## Goals

- List and open every board registered in the repository library.
- Let a user edit a registered board by forking its current immutable version
  into the existing workbench revision flow.
- Keep URL and image upload as the create flow.
- Publish completed new and edited boards back into the repository library.
- Treat browser and CLI output as interchangeable producers of the same board
  package contract.
- Preserve the product-neutral onboarding and rendering pipeline unchanged.

## Non-goals

- Improving any generated hangboard illustration.
- Adding product-specific cleanup, smoothing, rendering, coordinates, masks,
  templates, inventories, or tuning.
- Running `git add`, `git commit`, `git push`, or any other source-control
  mutation from the workbench.
- Automatically interpreting arbitrary legacy application source code as an
  editable pipeline run. Existing boards become library boards by conforming to
  the documented package contract, independent of how that package is committed.
- Introducing a database or remote service.

## Repository Layout

The repository library root is:

```text
Tools/HangboardOnboarding/board-library/
  catalog.json
  boards/
    <board-id>/
      board.json
      versions/
        revision-0001/
          published.json
          run/
            run.json
            source/
            stages/
            approvals/
```

`catalog.json` is the only discovery source. Its schema is:

```json
{
  "schemaVersion": 1,
  "boards": [
    {
      "boardId": "example-board",
      "displayName": "Example Board",
      "packagePath": "boards/example-board"
    }
  ]
}
```

Entries are sorted by case-insensitive display name, with `boardId` as the
stable tie-breaker. `boardId` and `packagePath` are unique. All paths are
relative, must resolve beneath the library root, and must not traverse symlinks
outside it.

`board.json` is the mutable pointer record for one board:

```json
{
  "schemaVersion": 1,
  "boardId": "example-board",
  "displayName": "Example Board",
  "currentVersionId": "revision-0001",
  "versions": [
    {
      "versionId": "revision-0001",
      "parentVersionId": null,
      "publishedAt": "2026-08-07T00:00:00Z",
      "publishedPath": "versions/revision-0001"
    }
  ]
}
```

Each immutable version contains a complete, CLI-compatible `run/` directory so
that every approved stage can be revised later, not merely viewed. It also
contains `published.json`, which identifies and hashes the consumer-facing
outputs from the approved Stage 4 checkpoint:

```json
{
  "schemaVersion": 1,
  "runIdentitySha256": "<sha256>",
  "definition": {"path": "run/stages/.../stage-4-manifest.json", "sha256": "<sha256>"},
  "image": {"path": "run/stages/.../stage-4-normal.png", "sha256": "<sha256>"},
  "selectableSvg": {"path": "run/stages/.../stage-4-product.svg", "sha256": "<sha256>"},
  "highlights": {"path": "run/stages/.../stage-4-highlights.json", "sha256": "<sha256>"}
}
```

The paths shown with `...` are the exact Stage 4 artifact paths recorded by the
copied run manifest. The publisher derives them from the approved acceptance
record; callers never supply them.

An initially empty repository commits `catalog.json` with schema version 1 and
an empty `boards` array. Any producer may add a package, but the workbench lists
it only after all catalog, board, run, and published-output validation succeeds.

## Runtime Workspace

Editable work remains in a separate ignored runtime workspace. When launched
from this checkout, the defaults are:

```text
repository root: discovered from the nearest parent containing .git
library root:    Tools/HangboardOnboarding/board-library
workspace root:  .context/hangboard-workbench
```

`--repository-root` and `--workspace-root` remain available for tests and
automation. The browser does not expose either path. Historical `--run-dir` and
`--catalog` server inputs may remain for the standalone legacy editor, but they
are not part of the guided workbench setup screen.

## User Experience

The opening state has three areas:

1. **Boards in this repository** lists validated catalog entries. Selecting one
   opens its current saved version immediately.
2. **In progress** lists unsaved runtime boards and newer working revisions so a
   browser refresh does not hide unfinished work.
3. **Create board** asks for a product name and either an image URL or upload.

There is no “Existing CLI run” choice and no run-directory field.

Opening a repository board imports its current immutable run into the runtime
workspace using the same validation used for CLI-compatible runs. The runtime
record retains the repository `boardId` and source `versionId`. The saved view is
readable immediately; choosing an approved earlier stage uses the existing
revision fork behavior. The committed package is never edited in place.

New URL/upload boards appear under **In progress** as soon as their runtime
record exists. They join **Boards in this repository** only after a complete
lineage is saved successfully.

## Service and HTTP Contract

A focused `RepositoryBoardLibrary` owns repository catalog and package I/O. The
existing `WorkbenchStore` continues to own transient board/revision state, and
`WorkbenchService` coordinates the two.

The guided server exposes:

- `GET /api/library` — validated repository entries plus their current version.
- `POST /api/library/<board-id>/open` — idempotently open the current version in
  the runtime workspace and return its workbench view.
- `GET /api/boards` — runtime/in-progress boards, preserving the existing view
  contract.
- `POST /api/boards` and `POST /api/boards/upload` — URL/upload creation.
- `POST /api/boards/<board-id>/save` — validate the selected complete runtime
  revision, publish it to the repository library, then mark the runtime revision
  saved with its repository version identity.

The current internal run-import service remains available to CLI/tooling code,
but `POST /api/boards/import` is removed from the browser flow. All mutating
requests retain the existing loopback Host/Origin protections and per-board job
serialization.

## Open and Save Transactions

Opening validates the catalog entry, board pointer, published hashes, complete
run manifest, approval chain, and confined paths before copying anything. The
copy is staged beside the target runtime revision and renamed into place. A
failure leaves no active partial revision.

Saving follows this order:

1. Require a non-stale complete Stage 4 revision.
2. Validate its complete run and derive the four published outputs from its
   approved Stage 4 acceptance record.
3. Copy the run into a new sibling staging directory and verify every copied
   published hash.
4. Write `published.json`, fsync files/directories, and atomically rename the
   immutable version directory into the package.
5. Atomically replace `board.json` so its current pointer selects the new
   version.
6. For a new board only, atomically replace `catalog.json` to expose the package.
7. Record the published version identity in the runtime store.

If a failure happens before step 5, the previous version remains current. If a
new-board catalog write fails after the package is complete, the package is an
unreferenced recoverable orphan and is not visible in the UI. Existing boards do
not require a catalog rewrite for each new version. Version identifiers are
allocated from immutable directory names and are never overwritten.

Concurrent publication of the same board is serialized with a library lock and
fails on an unexpected current-version token. Independent boards may publish
concurrently.

## Validation and Safety

- Repository root, library root, catalog paths, package paths, and copied run
  paths are resolved and confined before reads or writes.
- Symlinked packages, run members, and output targets are rejected.
- Catalog, board, and published manifests reject unknown schema versions,
  malformed IDs, duplicate entries, missing files, bad hashes, and mismatched
  board/run identities.
- Writes use sibling temporary files/directories, `fsync`, and atomic replace.
- Immutable version directories are never modified or reused.
- The server never shells out to Git.
- Product identity, material, piece count, hold inventory, and cleanup regions
  remain data generated by the unchanged shared pipeline, never production-code
  branches.

## Errors and Recovery

Invalid repository entries are not silently omitted. `GET /api/library` returns
a stable error identifying the offending `boardId` or catalog field so the
repository can be repaired. Opening an already-open current version returns the
existing runtime view. Opening a newer committed version creates a new runtime
revision without discarding local work.

Save conflicts report both the expected and current repository version IDs and
leave the runtime revision unsaved. A user can reload the repository version or
keep editing locally. Failed copies and temporary files are cleaned up; immutable
orphan versions are safe to inspect and remove separately.

## Verification

### Unit tests

- Catalog ordering, schema validation, duplicate detection, and confinement.
- Complete-run validation and published-output derivation.
- Product-neutral open/copy and atomic publish behavior.
- Existing-board version append, new-board catalog insertion, conflict handling,
  and injected failures at each pointer update.

### Service and API tests

- Repository entries open into the workbench without user-supplied paths.
- Reopening is idempotent and a newer version preserves local revisions.
- URL/upload creation remains unchanged.
- Save publishes repository files and never invokes Git.
- Foreign Host/Origin mutation requests remain rejected.

### Browser tests

- Existing repository boards and in-progress boards render separately.
- Selecting a repository board opens it.
- The setup screen has URL and upload creation only.
- Successful save moves a new board into the repository list.
- Library errors and save conflicts remain visible and actionable.

### Product-neutral replay

Use complete fixture packages named Beastmaker 1000, Metolius Wood Grips Compact
II, and Metolius Simulator 3D. Run the same open, revise, save, and reopen test
code for each. Names, dimensions, piece counts, materials, and hold inventories
are fixture data only; production code and parameters are identical.

## Acceptance Criteria

- The browser lists every valid board in the repository catalog without asking
  for a directory.
- A selected repository board opens with its current definition and image and
  can fork an editable revision.
- URL and upload create new boards and no CLI-run input appears in the UI.
- Saving a complete new or edited board publishes an immutable version into the
  repository and updates the visible catalog.
- Save performs no Git operation and leaves reviewable working-tree changes.
- Interrupted or conflicting saves cannot replace the prior current version or
  expose a partial new board.
- Browser, CLI, and other programmatic producers use the same package schema.
- The unchanged production implementation passes the three-board replay without
  product-specific branches or tuning.
