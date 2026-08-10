# Repository Board Library Implementation Plan

> **Historical plan:** Superseded by `2026-08-07-unified-hangboard-repository.md`. Direct discovery of canonical board runs and their `run.json` revision tokens is authoritative; the catalog and nested-version design below is preserved only as history.
>
> **For agentic workers:** REQUIRED SUB-SKILL: Use a fresh subagent for every implementation or configuration task, with separate implementation and review checkpoints for each task. Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make the local workbench list, open, edit, and save versioned hangboard packages in the repository while retaining URL/upload creation and never running Git.

**Architecture:** Add a repository-confined `RepositoryBoardLibrary` beside the transient `WorkbenchStore`. A library package owns immutable complete-run versions and atomically updated catalog/board pointers; `WorkbenchService` copies selected versions into runtime revisions and promotes complete runtime revisions back through that library. The loopback API and browser present repository boards, in-progress work, and URL/upload creation as separate concepts.

**Tech Stack:** Python 3.11, `pathlib`, JSON, `ThreadingHTTPServer`, vanilla JavaScript, Node's built-in test runner, pytest 8+

## Global Constraints

- The production workflow must remain programmatic, repeatable, scalable, and product-neutral.
- Do not add product-specific code paths, coordinates, masks, hold inventories, templates, or tuning.
- `Tools/HangboardOnboarding/board-library/catalog.json` is the only repository-board discovery source.
- Every published version contains a complete CLI-compatible run plus hashes for the approved Stage 4 definition, image, selectable SVG, and highlight document.
- URL and upload remain the browser create flow; the browser must not expose a CLI run-directory input.
- “Save locally” publishes repository working-tree files and updates runtime metadata; it never invokes Git.
- Generated artifacts and published versions are immutable; drafts, superseded attempts, approvals, and revision history remain recoverable.
- Repository, catalog, package, version, and run paths must remain confined and symlink-safe.
- One mutating job may run per board; independent boards may run concurrently.
- The editor remains dependency-free and loopback-only by default.

## Planned File Structure

- `Tools/HangboardOnboarding/src/hangboard_vectorizer/board_library.py` — validate the repository catalog/package schema, copy current versions into runtime, and publish immutable versions atomically.
- `Tools/HangboardOnboarding/src/hangboard_vectorizer/workbench_store.py` — persist an optional repository board/version link on runtime boards.
- `Tools/HangboardOnboarding/src/hangboard_vectorizer/workbench.py` — merge repository open/save operations with the existing guided workflow.
- `Tools/hold-highlight-editor/server.py` — expose library listing/opening and discover repository/workspace defaults.
- `Tools/hold-highlight-editor/workbench-client.js` — call the library HTTP endpoints.
- `Tools/hold-highlight-editor/workbench-model.js` — build deterministic repository/in-progress picker state.
- `Tools/hold-highlight-editor/app.js` — load the combined opening state and route repository selection.
- `Tools/hold-highlight-editor/index.html` and `styles.css` — replace the CLI-run input with repository and in-progress lists.
- `Tools/HangboardOnboarding/board-library/catalog.json` — commit the empty schema-versioned repository catalog.
- `Tools/HangboardOnboarding/README.md` and `Tools/hold-highlight-editor/README.md` — document package publishing, defaults, and the absence of Git mutations.
- Focused Python and Node tests accompany each responsibility.

---

### Task 1: Implement the Repository Board Library

**Files:**
- Create: `Tools/HangboardOnboarding/src/hangboard_vectorizer/board_library.py`
- Create: `Tools/HangboardOnboarding/tests/test_board_library.py`

**Interfaces:**
- Consumes: complete CLI-compatible run directories validated by `read_status(run_root)` and their approved Stage 4 acceptance records.
- Produces: `LibraryBoard`, `RepositoryBoardLibrary.list_boards()`, `RepositoryBoardLibrary.copy_current_run()`, and `RepositoryBoardLibrary.publish()`.

- [ ] **Step 1: Write failing catalog validation tests**

Add fixtures that write the exact schema from the design and assert ordering,
duplicates, traversal, symlinks, bad hashes, and unsupported schema versions:

```python
def test_list_boards_returns_validated_casefold_order(tmp_path: Path) -> None:
    library = _library_with_packages(tmp_path, ("Zulu", "alpha", "Alpha"))
    assert [(item.display_name, item.board_id) for item in library.list_boards()] == [
        ("alpha", "alpha"),
        ("Alpha", "alpha-2"),
        ("Zulu", "zulu"),
    ]


@pytest.mark.parametrize("package_path", ("../outside", "/tmp/outside"))
def test_catalog_rejects_package_paths_outside_library(
    tmp_path: Path, package_path: str
) -> None:
    library = _library_with_catalog_entry(tmp_path, package_path=package_path)
    with pytest.raises(BoardLibraryError, match="packagePath"):
        library.list_boards()
```

`_library_with_packages()` must construct complete product-neutral fixture runs
with the existing stub-runner pattern; it must not use network/model calls or
copy real product data.

- [ ] **Step 2: Run the focused tests and confirm the missing module failure**

Run: `rtk pytest -q Tools/HangboardOnboarding/tests/test_board_library.py`

Expected: collection fails because `hangboard_vectorizer.board_library` does not
exist.

- [ ] **Step 3: Implement schema types and strict reads**

Create these public immutable values:

```python
@dataclass(frozen=True, slots=True)
class LibraryBoard:
    board_id: str
    display_name: str
    package_path: Path
    current_version_id: str
    current_run_path: Path


@dataclass(frozen=True, slots=True)
class PublishedBoard:
    board: LibraryBoard
    version_id: str


class BoardLibraryError(ValueError):
    pass
```

Implement `RepositoryBoardLibrary(repository_root: Path)` with these methods:

```python
def list_boards(self) -> tuple[LibraryBoard, ...]: ...
def get_board(self, board_id: str) -> LibraryBoard: ...
def copy_current_run(self, board_id: str, destination: Path) -> LibraryBoard: ...
def publish(
    self,
    *,
    display_name: str,
    run_root: Path,
    board_id: str | None,
    expected_current_version_id: str | None,
) -> PublishedBoard: ...
```

Use native `#` private members. Validate IDs with
`[a-z0-9](?:[a-z0-9.-]*[a-z0-9])?`, validate every JSON member explicitly,
reject unknown schema versions, resolve every member beneath the configured
repository/library/package/version root, and reject symlinks for packages,
versions, copied run members, and write targets.

- [ ] **Step 4: Write failing copy and publication transaction tests**

```python
def test_copy_current_run_stages_then_atomically_renames(tmp_path: Path) -> None:
    library, expected = _complete_library(tmp_path)
    destination = tmp_path / "runtime" / "run"
    opened = library.copy_current_run(expected.board_id, destination)
    assert opened.current_run_path != destination
    assert read_status(destination) == read_status(opened.current_run_path)
    assert not list(destination.parent.glob(f".{destination.name}.tmp-*"))


def test_publish_appends_version_without_mutating_previous_version(tmp_path: Path) -> None:
    library, original = _complete_library(tmp_path)
    old_hashes = _tree_hashes(original.current_run_path)
    result = library.publish(
        display_name=original.display_name,
        run_root=_complete_fixture_run(tmp_path / "new-run"),
        board_id=original.board_id,
        expected_current_version_id=original.current_version_id,
    )
    assert result.version_id == "revision-0002"
    assert _tree_hashes(original.current_run_path) == old_hashes
    assert library.get_board(original.board_id).current_version_id == "revision-0002"


def test_publish_conflict_leaves_current_pointer_unchanged(tmp_path: Path) -> None:
    library, original = _complete_library(tmp_path)
    with pytest.raises(BoardLibraryError, match="expected revision-0000.*revision-0001"):
        library.publish(
            display_name=original.display_name,
            run_root=_complete_fixture_run(tmp_path / "new-run"),
            board_id=original.board_id,
            expected_current_version_id="revision-0000",
        )
    assert library.get_board(original.board_id).current_version_id == "revision-0001"
```

Inject failures immediately before the version rename, `board.json` replace, and
new-board `catalog.json` replace. Assert the old board pointer remains readable
and no partial catalog entry is visible.

- [ ] **Step 5: Implement immutable copy and atomic publication**

For `copy_current_run`, stage a complete copy beside `destination`, validate the
copied manifest and Stage 4 published hashes, then use an atomic rename. Reject a
destination that already exists.

For `publish`, require `read_status(run_root)` to report Stage 4 complete. Read
the Stage 4 approval path from `run.json`, derive `stage-4-manifest.json`,
`stage-4-normal.png`, `stage-4-product.svg`, and `stage-4-highlights.json` from
that approved acceptance, and verify their hashes. Allocate `revision-NNNN`
under a per-board `RLock`, copy into a sibling staging directory, write
`published.json`, fsync, rename the version, then atomically update `board.json`.
Only a new board updates `catalog.json`, and only after its complete package is
readable. Slug new IDs from normalized display names and append `-2`, `-3`, etc.
on collision. Never call a shell command or Git executable.

- [ ] **Step 6: Run the library and run-state coverage**

Run: `rtk pytest -q Tools/HangboardOnboarding/tests/test_board_library.py Tools/HangboardOnboarding/tests/test_onboarding_run.py Tools/HangboardOnboarding/tests/test_onboarding_run_revisions.py`

Expected: all tests pass, old version tree hashes are unchanged, and injected
failures leave the previous current pointer valid.

- [ ] **Step 7: Commit the library boundary**

```bash
rtk git add Tools/HangboardOnboarding/src/hangboard_vectorizer/board_library.py Tools/HangboardOnboarding/tests/test_board_library.py
rtk git commit -m "Add repository hangboard library"
```

### Task 2: Connect Repository Versions to Runtime Workbench Revisions

**Files:**
- Modify: `Tools/HangboardOnboarding/src/hangboard_vectorizer/workbench_store.py`
- Modify: `Tools/HangboardOnboarding/src/hangboard_vectorizer/workbench.py`
- Modify: `Tools/HangboardOnboarding/tests/test_workbench_store.py`
- Modify: `Tools/HangboardOnboarding/tests/test_workbench.py`
- Modify: `Tools/HangboardOnboarding/tests/test_workbench_end_to_end.py`

**Interfaces:**
- Consumes: Task 1's `RepositoryBoardLibrary`, `LibraryBoard`, and `PublishedBoard`.
- Produces: repository identity fields on runtime records/views,
  `WorkbenchService.list_library_boards()`, `open_library_board()`, and a
  repository-publishing `save()`.

- [ ] **Step 1: Write failing runtime-link persistence tests**

Extend `BoardRecord` and its JSON schema with optional
`repository_board_id`/`repository_version_id` fields and test round trips:

```python
def test_store_persists_repository_link_without_changing_runtime_id(tmp_path: Path) -> None:
    store = WorkbenchStore(tmp_path)
    board, revision = store.reserve_initial_revision("Example Board")
    linked = store.link_repository_version(
        board.id,
        repository_board_id="example-board",
        repository_version_id="revision-0001",
    )
    assert linked.id == board.id
    assert linked.repository_board_id == "example-board"
    assert linked.repository_version_id == "revision-0001"
    assert store.read_board(board.id) == linked
```

Old manifests without either optional key must still load as `None`. Reject one
key without the other and invalid identifiers.

- [ ] **Step 2: Run store tests and confirm missing fields/methods**

Run: `rtk pytest -q Tools/HangboardOnboarding/tests/test_workbench_store.py`

Expected: the new test fails because the repository link is not implemented.

- [ ] **Step 3: Implement repository link metadata**

Append defaulted public fields to `BoardRecord`:

```python
repository_board_id: str | None = None
repository_version_id: str | None = None
```

Add:

```python
def link_repository_version(
    self,
    board_id: str,
    *,
    repository_board_id: str,
    repository_version_id: str,
) -> BoardRecord: ...
```

Update `_board_to_json()` and `_board_from_json()` symmetrically. The method is
metadata-locked and atomically replaces `board.json` without changing the
runtime board ID, active revision, saved revision, or history.

- [ ] **Step 4: Write failing service open/save tests**

```python
def test_open_library_board_copies_current_version_and_is_idempotent(tmp_path: Path) -> None:
    library, entry = _repository_library(tmp_path)
    service = _service(tmp_path / "workspace", library=library)
    first = service.open_library_board(entry.board_id)
    second = service.open_library_board(entry.board_id)
    assert second.board_id == first.board_id
    assert second.revision_id == first.revision_id
    assert second.repository_board_id == entry.board_id
    assert second.repository_version_id == entry.current_version_id


def test_save_new_board_publishes_then_links_runtime_record(tmp_path: Path) -> None:
    library = _empty_repository_library(tmp_path)
    service, complete = _complete_runtime_board(tmp_path / "workspace", library)
    saved = service.save(complete.board_id, expected_revision_id=complete.revision_id)
    entries = library.list_boards()
    assert [(entry.board_id, entry.display_name) for entry in entries] == [
        (saved.repository_board_id, complete.product_name)
    ]
    assert saved.repository_version_id == "revision-0001"
    assert saved.saved is True


def test_save_existing_board_uses_expected_repository_version(tmp_path: Path) -> None:
    service, opened = _opened_complete_library_board(tmp_path)
    revised = _complete_revision(service, opened, fork_stage=3)
    saved = service.save(revised.board_id, expected_revision_id=revised.revision_id)
    assert saved.repository_version_id == "revision-0002"
```

Also test opening a newer repository version creates a new runtime revision
without deleting a divergent in-progress revision, a publish conflict leaves
the runtime revision unsaved, and library absence preserves the old transient
save behavior for compatibility callers.

- [ ] **Step 5: Implement library-aware service behavior**

Change construction to:

```python
def __init__(
    self,
    store: WorkbenchStore,
    *,
    runners: Mapping[int, StageRunner] | None = None,
    library: RepositoryBoardLibrary | None = None,
) -> None: ...

def list_library_boards(self) -> tuple[LibraryBoard, ...]: ...
def open_library_board(self, board_id: str) -> WorkbenchView: ...
```

Opening checks for an existing runtime board with the same repository board and
version and returns it. Otherwise reserve a new runtime board/revision, call
`copy_current_run()` into the reserved run root, mark the complete revision,
activate it, and link the repository identity. Cleanup uses the existing failed
initial-reservation transaction so a failed copy leaves no active partial board.

Extend `WorkbenchView` and `_view()` with `repository_board_id` and
`repository_version_id`. When a library is configured, `save()` calls
`library.publish()` before `store.save_revision()` and
`store.link_repository_version()`. New runtime boards pass `board_id=None`;
opened boards pass both recorded repository IDs as the optimistic token. The
runtime is marked saved only after publication succeeds.

- [ ] **Step 6: Add unchanged three-board open/edit/save replay**

Parameterize one service-level test over fixture package data only:

```python
@pytest.mark.parametrize(
    ("display_name", "color", "region_keys"),
    (
        ("Beastmaker 1000", (77, 52, 34), ("grip-001", "grip-002")),
        ("Metolius Wood Grips Compact II", (103, 70, 42), ("grip-001", "grip-002", "grip-003")),
        ("Metolius Simulator 3D", (64, 82, 96), ("grip-001", "grip-002", "grip-003", "grip-004")),
    ),
)
def test_repository_open_edit_save_replay_is_product_neutral(
    tmp_path: Path,
    display_name: str,
    color: tuple[int, int, int],
    region_keys: tuple[str, ...],
) -> None:
    service, entry = _library_fixture_service(tmp_path, display_name, color, region_keys)
    opened = service.open_library_board(entry.board_id)
    revised = service.revise_stage(
        opened.board_id, stage=3, expected_revision_id=opened.revision_id
    )
    complete = _approve_to_completion(service, revised)
    saved = service.save(complete.board_id, expected_revision_id=complete.revision_id)
    reopened = service.open_library_board(entry.board_id)
    assert saved.repository_version_id == "revision-0002"
    assert reopened.repository_version_id == "revision-0002"
```

The helper varies data only and uses the same runners, APIs, stages, and
assertions for all three names.

- [ ] **Step 7: Run service/store/end-to-end coverage**

Run: `rtk pytest -q Tools/HangboardOnboarding/tests/test_workbench_store.py Tools/HangboardOnboarding/tests/test_workbench.py Tools/HangboardOnboarding/tests/test_workbench_end_to_end.py`

Expected: all tests pass, including the unchanged three-board replay.

- [ ] **Step 8: Commit runtime/library integration**

```bash
rtk git add Tools/HangboardOnboarding/src/hangboard_vectorizer/workbench_store.py Tools/HangboardOnboarding/src/hangboard_vectorizer/workbench.py Tools/HangboardOnboarding/tests/test_workbench_store.py Tools/HangboardOnboarding/tests/test_workbench.py Tools/HangboardOnboarding/tests/test_workbench_end_to_end.py
rtk git commit -m "Connect workbench revisions to repository boards"
```

### Task 3: Expose Repository Browsing Through the Loopback API

**Files:**
- Modify: `Tools/hold-highlight-editor/server.py`
- Modify: `Tools/hold-highlight-editor/workbench-client.js`
- Modify: `Tools/hold-highlight-editor/tests/test_server.py`
- Modify: `Tools/hold-highlight-editor/tests/workbench_client.test.js`

**Interfaces:**
- Consumes: Task 2's `list_library_boards()`, `open_library_board()`, and extended `WorkbenchView`.
- Produces: `GET /api/library`, `POST /api/library/<board-id>/open`, repository-aware final save responses, and browser client methods `listLibraryBoards()`/`openLibraryBoard()`.

- [ ] **Step 1: Write failing server route and payload tests**

```python
def test_get_library_lists_validated_repository_boards(server_url: str) -> None:
    status, payload = _json_request(server_url, "GET", "/api/library")
    assert status == HTTPStatus.OK
    assert payload == {
        "ok": True,
        "boards": [
            {
                "boardId": "example-board",
                "displayName": "Example Board",
                "currentVersionId": "revision-0001",
            }
        ],
    }


def test_post_library_open_is_a_tracked_board_job(server_url: str) -> None:
    status, accepted = _json_request(
        server_url, "POST", "/api/library/example-board/open", {}
    )
    assert status == HTTPStatus.ACCEPTED
    terminal = _poll_job(server_url, accepted["jobId"])
    assert terminal["result"]["repositoryBoardId"] == "example-board"
    assert terminal["result"]["repositoryVersionId"] == "revision-0001"
```

Add 404 coverage for an unknown board, 400 coverage for invalid catalog data,
and Host/Origin rejection for the new mutation route using the existing boundary
test helpers.

- [ ] **Step 2: Run the focused server tests and confirm route failures**

Run: `rtk pytest -q Tools/hold-highlight-editor/tests/test_server.py -k 'library or repository'`

Expected: the new tests fail with 404 or missing payload keys.

- [ ] **Step 3: Add the HTTP routes and serializers**

Serialize library entries with exactly `boardId`, `displayName`, and
`currentVersionId`. Add `repositoryBoardId` and `repositoryVersionId` to
`_workbench_view_payload()`. Route `GET /api/library` synchronously because it is
read-only. Route `POST /api/library/<quoted-board-id>/open` through
`BoardJobManager` using a reservation key until the runtime board is known. Keep
`POST /api/boards/import` for programmatic compatibility but do not add it to the
browser setup flow.

- [ ] **Step 4: Write failing browser-client tests**

```javascript
test("listLibraryBoards returns the repository catalog", async () => {
  root.fetch = response({ ok: true, boards: [{ boardId: "example-board" }] });
  assert.deepEqual(await client.listLibraryBoards(), [{ boardId: "example-board" }]);
  assert.equal(root.fetch.mock.calls[0].arguments[0], "/api/library");
});

test("openLibraryBoard posts to the encoded repository route", async () => {
  root.fetch = acceptedThenSucceeded("job-1", { boardId: "board-0001" });
  const result = await client.openLibraryBoard("example board");
  assert.equal(result.boardId, "board-0001");
  assert.equal(root.fetch.mock.calls[0].arguments[0], "/api/library/example%20board/open");
});
```

- [ ] **Step 5: Implement client methods and run API/client coverage**

Add and export:

```javascript
async function listLibraryBoards() {
  return (await request("/api/library")).boards;
}

async function openLibraryBoard(boardId, options = {}) {
  return postJob(`/api/library/${encodeURIComponent(boardId)}/open`, {}, options);
}
```

Run: `rtk pytest -q Tools/hold-highlight-editor/tests/test_server.py && rtk node --test Tools/hold-highlight-editor/tests/workbench_client.test.js`

Expected: all server and client tests pass.

- [ ] **Step 6: Add repository/workspace launch defaults**

Write CLI tests asserting `--repository-root` constructs
`RepositoryBoardLibrary`, `--workspace-root` remains supported, and a launch
from a checkout defaults to nearest `.git`,
`Tools/HangboardOnboarding/board-library`, and
`.context/hangboard-workbench`. Fail clearly when no repository can be found.
The server launch must not execute Git; ancestor discovery uses filesystem
checks only. Keep standalone `--run-dir`/`--catalog` legacy editor launch modes.

Run: `rtk pytest -q Tools/hold-highlight-editor/tests/test_server.py -k 'cli or repository or workspace'`

Expected: all focused launch and route tests pass.

- [ ] **Step 7: Commit the loopback contract**

```bash
rtk git add Tools/hold-highlight-editor/server.py Tools/hold-highlight-editor/workbench-client.js Tools/hold-highlight-editor/tests/test_server.py Tools/hold-highlight-editor/tests/workbench_client.test.js
rtk git commit -m "Expose repository boards in workbench API"
```

### Task 4: Replace CLI Run Setup With Repository and In-Progress Pickers

**Files:**
- Modify: `Tools/hold-highlight-editor/index.html`
- Modify: `Tools/hold-highlight-editor/styles.css`
- Modify: `Tools/hold-highlight-editor/app.js`
- Modify: `Tools/hold-highlight-editor/workbench-model.js`
- Modify: `Tools/hold-highlight-editor/tests/workbench_model.test.js`
- Modify: `Tools/hold-highlight-editor/tests/workbench_app.test.js`

**Interfaces:**
- Consumes: Task 3's browser `listLibraryBoards()`, `openLibraryBoard()`, and existing runtime `listBoards()`.
- Produces: a setup/library screen with repository boards, in-progress runtime boards, and URL/upload creation only.

- [ ] **Step 1: Write failing pure picker-model tests**

Add and test:

```javascript
function openingSections(libraryBoards = [], runtimeBoards = []) { /* pure */ }
```

Required behavior:

```javascript
test("openingSections separates repository boards from unfinished runtime work", () => {
  assert.deepEqual(openingSections(
    [{ boardId: "alpha", displayName: "Alpha", currentVersionId: "revision-0001" }],
    [
      { boardId: "board-0001", productName: "Alpha", repositoryBoardId: "alpha", repositoryVersionId: "revision-0001", saved: true },
      { boardId: "board-0002", productName: "Beta", repositoryBoardId: null, repositoryVersionId: null, saved: false },
      { boardId: "board-0003", productName: "Alpha edit", repositoryBoardId: "alpha", repositoryVersionId: "revision-0001", saved: false },
    ],
  ), {
    library: [{ boardId: "alpha", displayName: "Alpha", currentVersionId: "revision-0001" }],
    inProgress: [
      { boardId: "board-0003", productName: "Alpha edit", repositoryBoardId: "alpha", repositoryVersionId: "revision-0001", saved: false },
      { boardId: "board-0002", productName: "Beta", repositoryBoardId: null, repositoryVersionId: null, saved: false },
    ],
  });
});
```

Sort both sections by case-insensitive label and stable ID. A saved runtime copy
at the repository's current version is not duplicated under In progress; any
unsaved runtime board remains visible.

- [ ] **Step 2: Run model tests and confirm the missing API failure**

Run: `rtk node --test Tools/hold-highlight-editor/tests/workbench_model.test.js`

Expected: the new test fails because `openingSections` is not exported.

- [ ] **Step 3: Implement and export the pure picker model**

Normalize absent arrays to empty arrays, copy rather than mutate input, filter
only the exact saved/current duplicate described above, and compare labels with
`localeCompare(..., undefined, { sensitivity: "base" })` followed by ID.

- [ ] **Step 4: Write failing setup markup/controller tests**

Assert the document contains:

- `repository-board-list`, `in-progress-board-list`, and `create-board-form`.
- Source radios for `url` and `upload` only.
- No `import` source radio, `setup-import-path`, “Existing CLI run”, or “Import run”.

Add controller tests that stub both list endpoints, click a repository row and
assert `openLibraryBoard(boardId)` is called, click an in-progress row and assert
`getBoard(runtimeBoardId)` is called, and create from URL/upload through the
unchanged client methods. Test empty and library-error states without hiding the
create form.

- [ ] **Step 5: Implement the opening screen and selection behavior**

Replace the import radio/field with semantic list containers and buttons. On
guided startup and after any successful mutation, fetch library and runtime
lists together with `Promise.all`, derive `openingSections()`, and render both.
Repository selection runs the tracked open job, then loads its returned
checkpoint. In-progress selection calls `getBoard()`. “Boards” navigation returns
to this screen even when lists are non-empty; creating does not require the
lists to be empty.

Do not remove the legacy standalone editor picker controlled by `/api/sessions`.
Remove `importRun()` calls from guided browser code only. Change successful final
save copy to “Saved to this repository.”

- [ ] **Step 6: Style responsive lists and preserve the editor layout**

Use existing color/type variables. Each row displays the board name and a quiet
version/status line, has a visible keyboard focus state, and is a real button.
At narrow widths the two lists stack above Create board; at desktop widths the
repository list is primary and Create board remains visible without horizontal
scrolling. Do not add board-specific image treatments.

- [ ] **Step 7: Run browser model/controller tests**

Run: `rtk node --test Tools/hold-highlight-editor/tests/*.test.js`

Expected: all Node tests pass, the old CLI-run copy is absent, and legacy editor
tests remain green.

- [ ] **Step 8: Commit the repository-first UI**

```bash
rtk git add Tools/hold-highlight-editor/index.html Tools/hold-highlight-editor/styles.css Tools/hold-highlight-editor/app.js Tools/hold-highlight-editor/workbench-model.js Tools/hold-highlight-editor/tests/workbench_model.test.js Tools/hold-highlight-editor/tests/workbench_app.test.js
rtk git commit -m "Add repository board picker to workbench"
```

### Task 5: Commit the Library Contract, Documentation, and Full Verification

**Files:**
- Create: `Tools/HangboardOnboarding/board-library/catalog.json`
- Modify: `Tools/HangboardOnboarding/README.md`
- Modify: `Tools/hold-highlight-editor/README.md`
- Modify: `.gitignore`
- Modify: `Tools/HangboardOnboarding/tests/test_workbench_end_to_end.py`

**Interfaces:**
- Consumes: Tasks 1–4 complete repository/browser behavior.
- Produces: a committed empty catalog, documented programmatic producer contract, ignored default runtime workspace, and final three-board verification evidence.

- [ ] **Step 1: Write the committed empty catalog**

Create exactly:

```json
{
  "schemaVersion": 1,
  "boards": []
}
```

Add a test that constructs `RepositoryBoardLibrary(repository_root)` against the
checkout fixture and asserts the committed catalog loads as an empty tuple.

- [ ] **Step 2: Ignore only the default transient workspace**

Add `/.context/hangboard-workbench/` to the repository `.gitignore`. Do not
ignore `Tools/HangboardOnboarding/board-library/boards/` or any published package
path; saved boards must remain visible to Git review.

- [ ] **Step 3: Document browser and programmatic producer flows**

Document the default launch:

```bash
rtk python Tools/hold-highlight-editor/server.py
```

Document `--repository-root`/`--workspace-root` automation overrides, the exact
catalog/package schemas by linking the design spec, URL/upload creation, opening
repository boards, immutable version publication, and that Save locally writes
files but never commits or pushes. State explicitly that CLI runs are producers:
programmatic callers pass a completed run to `RepositoryBoardLibrary.publish()`;
the browser never asks the user for its directory.

- [ ] **Step 4: Run focused product-neutral replay**

Run: `rtk pytest -q Tools/HangboardOnboarding/tests/test_workbench_end_to_end.py -k repository_open_edit_save_replay_is_product_neutral`

Expected: the Beastmaker 1000, Metolius Wood Grips Compact II, and Metolius
Simulator 3D fixture cases all pass through the identical open/edit/save/reopen
implementation.

- [ ] **Step 5: Run complete automated verification**

Run: `rtk pytest -q Tools/HangboardOnboarding/tests Tools/hold-highlight-editor/tests/test_server.py`

Expected: all Python tests pass.

Run: `rtk node --test Tools/hold-highlight-editor/tests/*.test.js`

Expected: all Node tests pass.

Run: `rtk python -m py_compile Tools/HangboardOnboarding/src/hangboard_vectorizer/*.py Tools/hold-highlight-editor/*.py`

Expected: command exits 0.

Run: `rtk git diff --check`

Expected: command exits 0.

Run: `rtk git diff --name-only origin/codex/add-hangboard-onboarding...HEAD -- '*.png'`

Expected: no protected PNG path appears.

- [ ] **Step 6: Verify the protected visual fixtures are byte-identical**

Run:

```bash
rtk shasum -a 256 \
  Tools/HangboardOnboarding/src/hangboard_vectorizer/products/beastmaker-1000-render.png \
  HangTen/Resources/Assets.xcassets/CompactBoard.imageset/WoodGripsCompactII.jpg
```

Expected hashes:

```text
4bd615d34bf60d083d4bb7da945cdbe23a59858a430d268d25c2c67308f23627  Tools/HangboardOnboarding/src/hangboard_vectorizer/products/beastmaker-1000-render.png
c101a319076448be38977c606b5be57f1f254e2fe273b0c56a69ca2f52bdb596  HangTen/Resources/Assets.xcassets/CompactBoard.imageset/WoodGripsCompactII.jpg
```

The user-facing highlighted checkpoints remain outside the repository and are
not rewritten by this UI-only plan.

- [ ] **Step 7: Launch and inspect the visual checkpoint**

Start the server from the repository root with its defaults, open
`http://127.0.0.1:4173/`, and verify:

- the repository and in-progress sections are visible;
- URL/upload Create board remains visible;
- no CLI run-directory input appears;
- keyboard focus and narrow-width stacking are legible;
- opening, editor, and final-save states preserve the existing visual layout.

This is the only human review gate for this plan.

- [ ] **Step 8: Commit documentation and verification fixtures**

```bash
rtk git add .gitignore Tools/HangboardOnboarding/board-library/catalog.json Tools/HangboardOnboarding/README.md Tools/hold-highlight-editor/README.md Tools/HangboardOnboarding/tests/test_workbench_end_to_end.py
rtk git commit -m "Document repository board workflow"
```
