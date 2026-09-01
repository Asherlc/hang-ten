# Board Editor Responsiveness Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make selecting and opening a board in the iOS board editor responsive by keeping package and image I/O off the main render/navigation path.

**Architecture:** The picker will use lazy rows with cancellable asynchronous thumbnail decoding. A new loading destination will prepare the editable package and selected image on a background queue, then construct the existing editor only after success. `BoardEditorStore.prepareEditablePackage(slug:)` serializes copy/reuse and document/image validation with reset for the same store, so reset cannot remove a package between preparation and loading.

**Tech Stack:** Swift 6-compatible SwiftUI, UIKit, Foundation, XCTest.

**Spec:** `docs/superpowers/specs/2026-08-31-board-editor-responsiveness-design.md`

## Global Constraints

- Preserve the existing editable package format and full-package copy semantics.
- Do not decode a thumbnail synchronously from a SwiftUI `body` or row builder.
- Do not perform `startEditing`, `loadDocument`, PNG validation, or selected-board image decoding on the main actor.
- Keep copy/reuse, document loading, and reset serialized through `prepareEditablePackage(slug:)` and the store's scoped synchronization; reset UI actions remain gated until the detached reset completes.
- Reuse an existing package only after its edited `board.json` and declared presentation image validate. Preserve an existing edited document and surface its explicit load error rather than replacing it from the bundled source.
- Keep the existing load-failure message and the existing editor UI unchanged after a successful load.
- Add a regression test that observes the loader state transition using real `BoardEditorStore` data.

---

### Task 1: Make board selection and loading asynchronous

**Files:**
- Create: `HangTen/Views/BoardEditor/BoardEditorLoadingView.swift`
- Modify: `HangTen/Views/BoardEditor/BoardEditorListView.swift`
- Modify: `HangTen/Views/BoardEditor/BoardEditorScreen.swift`
- Modify: `HangTenTests/BoardEditorStoreTests.swift` or create `HangTenTests/BoardEditorLoadingTests.swift`

**Interfaces:**
- Consumes: `BoardEditorStore.prepareEditablePackage(slug:)`.
- Produces: `BoardEditorLoadingView(slug:store:)`, used as the navigation destination instead of directly constructing `BoardEditorScreen`.
- Produces: a testable loading-state type or dependency-injected loader which publishes `.loading`, then `.loaded(BoardEditedPackage, UIImage)` or `.failed`.

- [ ] **Step 1: Write the failing regression test**

Create a test using the existing temporary source-library helpers that starts a loader for `fixture-board`, waits for its terminal state, and asserts that it changes from loading to loaded with the expected slug and image dimensions. Add a failure-path assertion using a missing source slug. The test must use the production loader and `BoardEditorStore`, not a mock of the state transition.

- [ ] **Step 2: Run the focused test to verify it fails**

Run: `xcodebuild test -project HangTen.xcodeproj -scheme HangTen -destination 'platform=iOS Simulator,name=iPhone 16 Pro' -only-testing:HangTenTests/BoardEditorLoadingTests`

Expected: FAIL because the loading destination/state type does not yet exist.

- [ ] **Step 3: Implement the minimal asynchronous loading path**

Create a loader owned by `BoardEditorLoadingView` that begins in `.loading`, performs `prepareEditablePackage(slug:)` and `UIImage(contentsOfFile:)` on a background queue, and publishes terminal state on the main actor. `prepareEditablePackage` holds scoped store synchronization across copy/reuse and document/image validation; the detached reset takes the same synchronization, while `BoardEditorResetCoordinator` gates a later open until reset completion. Render a `ProgressView` while loading, render the exact current failure copy on failure, and render `BoardEditorScreen` only after success. Change `BoardEditorScreen` so its initializer accepts an already loaded `BoardEditedPackage` and image rather than initiating synchronous work.

Change `BoardEditorListView` to use `LazyVStack` and a dedicated thumbnail view. The thumbnail view decodes from its URL in a task/background operation, cancels its retained worker when SwiftUI cancels the row task, and shows the current neutral placeholder while unavailable; preparation must cooperatively observe cancellation and must not call `UIImage(contentsOfFile:)` from `body`, `row`, or `thumbnail(for:)`. Route `navigationDestination` through `BoardEditorLoadingView`.

- [ ] **Step 4: Run the focused test to verify it passes**

Run: `xcodebuild test -project HangTen.xcodeproj -scheme HangTen -destination 'platform=iOS Simulator,name=iPhone 16 Pro' -only-testing:HangTenTests/BoardEditorLoadingTests`

Expected: PASS with both success and failure loading states verified.

- [ ] **Step 5: Run relevant regression coverage**

Run: `xcodebuild test -project HangTen.xcodeproj -scheme HangTen -destination 'platform=iOS Simulator,name=iPhone 16 Pro' -only-testing:HangTenTests/BoardEditorStoreTests -only-testing:HangTenTests/BoardEditorSessionTests`

Expected: PASS, proving package copy/load and editing behavior remain intact.

- [ ] **Step 6: Verify serialized package preparation and reset coordination**

Add store regressions for: preparation and reset of the same store remaining atomic; preparation in an independent store proceeding without a global lock stall; and existing edited `board.json` surviving a missing or unreadable declared presentation asset with an explicit load error. Add loader/image-preparer regressions that cancellation suppresses obsolete thumbnail results. The exact touched implementation and test files are `HangTen/Models/BoardEditorStore.swift`, `HangTen/Views/BoardEditor/BoardEditorLoadingView.swift`, `HangTen/Views/BoardEditor/BoardEditorListView.swift`, `HangTenTests/BoardEditorStoreTests.swift`, and `HangTenTests/BoardEditorLoadingTests.swift`.

- [ ] **Step 7: Commit**

```bash
git add HangTen/Models/BoardEditorStore.swift HangTen/Views/BoardEditor/BoardEditorLoadingView.swift HangTen/Views/BoardEditor/BoardEditorListView.swift HangTen/Views/BoardEditor/BoardEditorScreen.swift HangTenTests/BoardEditorStoreTests.swift HangTenTests/BoardEditorLoadingTests.swift docs/superpowers/specs/2026-08-31-board-editor-responsiveness-design.md docs/superpowers/plans/2026-08-31-board-editor-responsiveness.md
git commit -m "Fix board editor loading responsiveness"
```
