# Direct Board Editor Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Load a repository board's packaged holds directly in the Workbench and remove user-facing run terminology.

**Architecture:** Add an explicit editor-document artifact to every board view. The Python service identifies the verified document and clean image; the HTTP boundary exposes both URLs; the browser uses that URL directly and only replaces state after both assets load. Completed boards reuse their immutable Stage 3 vector document, so package-backed holds remain visible without inferring paths from pipeline review files.

**Tech Stack:** Python 3.11, dependency-free browser JavaScript, Swift/AppKit/WebKit, pytest, Node test runner, SwiftPM tests.

## Global Constraints

- Do not manufacture hold geometry: direct documents must come from the package-backed, hash-validated artifact already produced by the repository library.
- Preserve public board IDs and all existing workspace board drafts.
- Do not expose filesystem paths in HTTP responses or browser errors.
- Do not use user-facing `run`, `stage`, or `checkpoint` language in primary board-loading UI.
- Use test-driven development: observe each new regression test fail before the production change.

---

### Task 1: Expose a verified editor document for completed boards

**Files:**
- Modify: `Tools/HangboardPipeline/src/hangboard_vectorizer/workbench.py:45-78, 760-1018`
- Modify: `Tools/HangboardPipeline/tests/test_workbench.py:61-78`

**Interfaces:**
- Produces: `WorkbenchView.editor_document_path: Path | None`.
- Consumes: the existing `stage-3-vector-regions.json` artifact and Stage 1 clean-image evidence stored in a completed revision.
- Preserves: `normal_artifact_path` and `hold_count` for completed-board inspection.

- [ ] **Step 1: Write the failing service regression test**

```python
def test_completed_board_view_exposes_verified_editor_document(
    complete_board: WorkbenchView,
) -> None:
    assert complete_board.editor_image_path is not None
    assert complete_board.editor_image_path.name == "stage-1-auto-rgba.png"
    assert complete_board.editor_document_path is not None
    assert complete_board.editor_document_path.name == "stage-3-vector-regions.json"
```

- [ ] **Step 2: Run the test to verify it fails**

Run: `uv run --project Tools/HangboardPipeline --extra dev python -m pytest -q Tools/HangboardPipeline/tests/test_workbench.py -k completed_board_view_exposes_verified_editor_document`

Expected: FAIL because `WorkbenchView` has no `editor_document_path` and completed views expose no editable image.

- [ ] **Step 3: Write the minimal verified completed-editor artifact resolver**

```python
@dataclass(frozen=True, slots=True)
class WorkbenchView:
    editor_image_path: Path | None
    editor_document_path: Path | None

def __completed_editor_artifacts(self, revision: RevisionRecord) -> tuple[Path, Path]:
    manifest = self.__manifest(revision.run_root)
    editor_path = self.__editor_image_path(revision, 3, manifest)
    document_path = self.__editable_document_path(
        revision, 3, manifest["stages"][3]
    )
    return editor_path, document_path
```

Make `__view` populate the new field for reviewable Stage 2/3 views and for completed views. Keep each path confined to the revision root and hash-validated through the existing helper logic.

- [ ] **Step 4: Run the focused service test to verify it passes**

Run: `uv run --project Tools/HangboardPipeline --extra dev python -m pytest -q Tools/HangboardPipeline/tests/test_workbench.py -k 'completed_board_view_exposes_verified_editor_document or editable_stages_expose_a_clean_canvas_aligned_image_separate_from_review'`

Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add Tools/HangboardPipeline/src/hangboard_vectorizer/workbench.py Tools/HangboardPipeline/tests/test_workbench.py
git commit -m "fix: expose completed board editor geometry"
```

### Task 2: Return explicit document URLs from the board HTTP resource

**Files:**
- Modify: `Tools/HangboardWorkbench/server.py:421-462`
- Modify: `Tools/HangboardWorkbench/tests/test_server.py:320-390, 1471-1504`

**Interfaces:**
- Consumes: `WorkbenchView.editor_document_path`.
- Produces: `editorDocumentUrl` in every public board view with editable geometry.
- Preserves: artifact confinement through `/api/artifact?boardId=…&revisionId=…&path=…`.

- [ ] **Step 1: Write the failing API test**

```python
def test_completed_board_api_exposes_editor_document_and_clean_image(
    running_workbench_server,
):
    view = _complete_board(running_workbench_server)
    assert view["editorImageUrl"] is not None
    assert view["editorDocumentUrl"] is not None
    status, document = read_json(running_workbench_server + view["editorDocumentUrl"])
    assert status == 200
    assert len(document["regions"]) == 4
```

- [ ] **Step 2: Run the test to verify it fails**

Run: `uv run --project Tools/HangboardPipeline --extra dev python -m pytest -q Tools/HangboardWorkbench/tests/test_server.py -k completed_board_api_exposes_editor_document_and_clean_image`

Expected: FAIL because the response lacks `editorDocumentUrl`.

- [ ] **Step 3: Add the public URL field**

```python
editor_document_url = artifact_url(
    getattr(view, "editor_document_path", None), "editor document"
)

return {
    "editorImageUrl": editor_image_url,
    "editorDocumentUrl": editor_document_url,
}
```

Extend the fake view/test fixture with a confined JSON artifact so all existing API contracts remain explicit.

- [ ] **Step 4: Run the focused server tests to verify they pass**

Run: `uv run --project Tools/HangboardPipeline --extra dev python -m pytest -q Tools/HangboardWorkbench/tests/test_server.py -k 'editor_document or editable_board_api or completed_board_api'`

Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add Tools/HangboardWorkbench/server.py Tools/HangboardWorkbench/tests/test_server.py
git commit -m "fix: publish direct board editor documents"
```

### Task 3: Load explicit documents atomically and rename the board rail

**Files:**
- Modify: `Tools/HangboardWorkbench/app.js:1935-2055, 2588-2610`
- Modify: `Tools/HangboardWorkbench/index.html:127-131`
- Modify: `Tools/HangboardWorkbench/workbench-controller.js:180-235`
- Modify: `Tools/HangboardWorkbench/tests/workbench_app.test.js:102-132, 215-245`
- Modify: `Tools/HangboardWorkbench/tests/workbench_controller.test.js:1-180`

**Interfaces:**
- Consumes: `view.editorImageUrl`, `view.editorDocumentUrl`, and `view.editorMode`.
- Produces: an editor state populated with regions for a completed package-backed board.
- Preserves: the prior loaded document when a new image/document request fails.

- [ ] **Step 1: Write failing browser regression tests**

```javascript
test("loads a completed board from its explicit editor document URL", async () => {
  const source = extractFunction(appSource, "loadCheckpoint");
  assert.match(source, /view\.editorDocumentUrl/);
  assert.doesNotMatch(source, /checkpointDocumentUrl\(/);
});

test("the board rail has no user-facing run terminology", () => {
  assert.doesNotMatch(markup, />Recent runs</);
  assert.doesNotMatch(appSource, /function renderRecentRuns\(/);
});
```

- [ ] **Step 2: Run the tests to verify they fail**

Run: `node --test Tools/HangboardWorkbench/tests/workbench_app.test.js Tools/HangboardWorkbench/tests/workbench_controller.test.js`

Expected: FAIL because the client derives a document path from `reviewUrl` and the rail is labelled `Recent runs`.

- [ ] **Step 3: Make document/image loading transactional**

```javascript
const documentUrl = view.editorDocumentUrl;
if (!documentUrl || !imageUrl) throw new Error("Hold data is unavailable for this board");
const [imageAsset, response] = await Promise.all([
  loadImageAsset(imageUrl, "Board image"),
  fetch(documentUrl, { cache: "no-store" }),
]);
if (!response.ok) throw new Error("Could not load holds for this board");
const baselineDocument = await response.json();
validateEditableImageAlignment(view, imageAsset, baselineDocument);
```

Install the new assets only inside `load.commit`, regardless of the board's historical stage. Rename `recent-runs`/`renderRecentRuns` to `open-boards`/`renderOpenBoards`, and update the visible heading to `Open boards`. Keep legacy static catalog controls out of the guided UI.

- [ ] **Step 4: Run focused browser tests to verify they pass**

Run: `node --test Tools/HangboardWorkbench/tests/workbench_app.test.js Tools/HangboardWorkbench/tests/workbench_controller.test.js Tools/HangboardWorkbench/tests/editor_ui.test.js`

Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add Tools/HangboardWorkbench/app.js Tools/HangboardWorkbench/index.html Tools/HangboardWorkbench/workbench-controller.js Tools/HangboardWorkbench/tests/workbench_app.test.js Tools/HangboardWorkbench/tests/workbench_controller.test.js
git commit -m "fix: load board holds directly in the editor"
```

### Task 4: Stop on a packaged-runtime/checkout mismatch

**Files:**
- Modify: `Tools/HangboardWorkbench/macos/Sources/HangboardWorkbench/BackendController.swift:32-190`
- Modify: `Tools/HangboardWorkbench/macos/Sources/HangboardWorkbench/WorkbenchApp.swift:300-340, 505-510`
- Modify: `Tools/HangboardWorkbench/macos/Tests/HangboardWorkbenchTests/BackendControllerTests.swift`

**Interfaces:**
- Consumes: the runtime build SHA beside `hangboard-workbench` and the selected checkout HEAD SHA.
- Produces: `BackendController.Error.runtimeCheckoutMismatch` before WebKit loads the editor.
- Preserves: startup when either identity is unavailable, such as a development build without `build-commit.txt`.

- [ ] **Step 1: Write the failing native test**

```swift
func testStartRejectsKnownRuntimeAndCheckoutIdentityMismatch() async {
    let runtime = try makeRuntime(commit: String(repeating: "a", count: 40))
    let checkout = try makeCheckout(head: String(repeating: "b", count: 40))
    let process = FakeBackendProcess()
    let backend = BackendController(
        executableURL: runtime.appending(path: "hangboard-workbench"),
        processFactory: { process }, healthProbe: { _ in true }, sleep: { _ in },
        portSelector: { 4173 }
    )
    await XCTAssertThrowsErrorAsync(try await backend.start(repositoryRoot: checkout, port: 4173)) { error in
        XCTAssertEqual(error as? BackendController.Error, .runtimeCheckoutMismatch)
    }
    XCTAssertEqual(process.runCount, 0)
}
```

- [ ] **Step 2: Run the test to verify it fails**

Run: `swift test --package-path Tools/HangboardWorkbench/macos --filter BackendControllerTests.testStartRejectsKnownRuntimeAndCheckoutIdentityMismatch`

Expected: FAIL because a mismatched session still starts.

- [ ] **Step 3: Add mismatch preflight and recovery copy**

```swift
case runtimeCheckoutMismatch

guard runtimeIdentity == "unknown" || checkoutIdentity == "unknown" || runtimeIdentity == checkoutIdentity else {
    throw Error.runtimeCheckoutMismatch
}
```

Perform the comparison after checkout validation and before starting the backend process. Present a recovery message instructing the user to install a Workbench build matching the selected checkout; do not open a web view backed by a potentially incompatible runtime.

- [ ] **Step 4: Run the focused native test to verify it passes**

Run: `swift test --package-path Tools/HangboardWorkbench/macos --filter BackendControllerTests.testStartRejectsKnownRuntimeAndCheckoutIdentityMismatch`

Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add Tools/HangboardWorkbench/macos/Sources/HangboardWorkbench/BackendController.swift Tools/HangboardWorkbench/macos/Sources/HangboardWorkbench/WorkbenchApp.swift Tools/HangboardWorkbench/macos/Tests/HangboardWorkbenchTests/BackendControllerTests.swift
git commit -m "fix: reject mismatched workbench backends"
```

### Task 5: Verify the integrated board editor

**Files:**
- Verify: `Tools/HangboardPipeline/tests/test_workbench.py`
- Verify: `Tools/HangboardWorkbench/tests/test_server.py`
- Verify: `Tools/HangboardWorkbench/tests/workbench_app.test.js`
- Verify: `Tools/HangboardWorkbench/tests/workbench_client.test.js`
- Verify: `Tools/HangboardWorkbench/tests/workbench_controller.test.js`
- Verify: `Tools/HangboardWorkbench/macos/Tests/HangboardWorkbenchTests/`

- [ ] **Step 1: Run all targeted Python tests**

Run: `uv run --project Tools/HangboardPipeline --extra dev python -m pytest -q Tools/HangboardPipeline/tests/test_workbench.py Tools/HangboardWorkbench/tests/test_server.py`

Expected: PASS.

- [ ] **Step 2: Run all Workbench browser tests**

Run: `node --test Tools/HangboardWorkbench/tests/workbench*.test.js Tools/HangboardWorkbench/tests/editor_ui.test.js`

Expected: PASS.

- [ ] **Step 3: Run native Workbench tests**

Run: `swift test --package-path Tools/HangboardWorkbench/macos`

Expected: PASS.

- [ ] **Step 4: Confirm the real published package document has holds**

Run: `uv run --project Tools/HangboardPipeline python Tools/HangboardWorkbench/server.py --workspace-root .context/direct-board-editor-check --port 4174`

Expected: opening `metolius.wood-grips-compact-ii` returns a non-empty `editorDocumentUrl`; the document's region count matches the package's hold pieces. Stop the server and remove only `.context/direct-board-editor-check` after the check.

- [ ] **Step 5: Commit and push any verification-only updates**

```bash
git add -A
git commit -m "test: verify direct board editor loading"
git push origin HEAD
```
