# Native Hangboard Workbench Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development. Use a fresh subagent for every implementation or configuration task, with separate implementation and review checkpoints. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Release Hangboard Workbench as a self-contained, signed macOS app that opens a native window, selects a Hang Ten checkout at launch, and preserves a future hosted-server path.

**Architecture:** A small AppKit/WebKit Swift shell owns native launch behavior and embeds the existing HTTP editor in a `WKWebView`. The shell starts a signed, bundled Python backend on loopback against a validated checkout; the editor continues using HTTP only. The release workflow builds an unsigned test runtime for pull requests and rebuilds the same runtime with a Developer ID identity for the notarized release app.

**Tech Stack:** Swift 6/AppKit/WebKit, Swift Package Manager, Python 3.12, PyInstaller 6.22.0 `--onedir`, existing `http.server` backend, Node test runner, GitHub Actions, `codesign`, `notarytool`, and `stapler`.

## Global Constraints

- Target Apple Silicon macOS only; do not add Intel, Windows, Linux, accounts, sync, or a hosted service.
- The installed app must never open the default browser.
- First launch must present a native folder picker; later launches reuse only a revalidated last-valid Hang Ten checkout.
- A checkout is valid only when it contains `.git`, `Tools/HangboardOnboarding/boards`, and `Tools/hold-highlight-editor`.
- The selected checkout remains the sole source of board data and destination for saved work; the app never invokes Git.
- The Swift shell owns UI and process lifecycle only. Python remains the authority for workbench routes, jobs, and filesystem writes.
- Browser JavaScript accesses all workbench data through relative/versioned HTTP routes; it must not use filesystem APIs or hard-coded loopback URLs.
- Bundle no checkout, boards, user workspaces, certificates, private keys, or generated release artifacts.
- Pull requests run without Apple secrets. Main-release signing uses the existing Developer ID and App Store Connect credentials only in the protected release job.
- Use test-driven development. Every task begins with a failing focused regression and ends with focused and surrounding tests.
- Commit each completed task and push it to the remote.

## File Structure

- Modify `Tools/hold-highlight-editor/server.py`: expose loopback health and validate a Hang Ten checkout consistently for CLI and native launch.
- Modify `Tools/hold-highlight-editor/workbench_binary.py`: provide deterministic backend-only startup; never require or invoke browser launch from the app runtime.
- Modify `Tools/hold-highlight-editor/tests/test_server.py` and `tests/test_workbench_binary.py`: backend health, checkout validation, and no-browser regressions.
- Create `Tools/hold-highlight-editor/macos/Package.swift`: standalone native-shell Swift package.
- Create `Tools/hold-highlight-editor/macos/Sources/HangboardWorkbench/{CheckoutSelection,BackendController,WorkbenchApp}.swift`: validation/preferences, loopback child process lifecycle, and AppKit/WebKit UI.
- Create `Tools/hold-highlight-editor/macos/Tests/HangboardWorkbenchTests/{CheckoutSelectionTests,BackendControllerTests}.swift`: deterministic native-shell unit coverage.
- Modify `Tools/hold-highlight-editor/packaging/build.py`: create an arm64 PyInstaller `--onedir` runtime, optionally passing a Developer ID identity to PyInstaller.
- Modify `Tools/hold-highlight-editor/packaging/macos_app.py`: assemble a complete app from the Swift shell and runtime directory under `Contents/Resources/workbench-runtime`.
- Modify `Tools/hold-highlight-editor/tests/test_workbench_packaging.py` and `tests/test_macos_app.py`: enforce signed-runtime inputs and bundle layout.
- Modify `.github/workflows/hangboard-workbench-release.yml` and `Tools/hold-highlight-editor/tests/test_workbench_release_workflow.py`: build/smoke the final app before notarized publication.
- Modify `Tools/hold-highlight-editor/README.md` and `Tools/HangboardOnboarding/README.md`: document launch, selection, switching checkouts, and direct-save behavior.

---

### Task 1: Make the backend a native-shell-safe local service

**Files:**
- Modify: `Tools/hold-highlight-editor/server.py`
- Modify: `Tools/hold-highlight-editor/workbench_binary.py`
- Modify: `Tools/hold-highlight-editor/tests/test_server.py`
- Modify: `Tools/hold-highlight-editor/tests/test_workbench_binary.py`

**Interfaces:**
- Produces `server.validate_hang_ten_checkout(root: Path) -> Path`, returning the resolved root or raising `EditorError` with no absolute path.
- Produces `GET /api/health` as HTTP 200 JSON `{"ok": true}` before browser/editor routes are used.
- Produces `workbench_binary._run(arguments: list[str], *, server_factory: Callable[[list[str]], tuple[WorkbenchHTTPServer, EditorCatalog | None]]) -> int`; `--no-open` is accepted for compatibility and the app runtime never calls `webbrowser.open`.

- [ ] **Step 1: Write failing Python regressions**

Add tests that construct minimal valid and invalid checkout directories, assert `validate_hang_ten_checkout()` accepts only the valid layout, and assert `/api/health` returns exactly `{"ok": true}`. Replace the existing browser-opening test with a regression proving `_run()` starts and closes a fake server without calling its browser callback.

```python
def test_health_is_available_before_library_loading(tmp_path):
    with running_server(make_run(tmp_path / "legacy"), FakeWorkbenchService(tmp_path)) as base:
        status, payload = _raw_request(base, "GET", "/api/health")
    assert status == 200
    assert json.loads(payload) == {"ok": True}

def test_checkout_validation_requires_hang_ten_markers(tmp_path):
    root = tmp_path / "hang-ten"
    (root / ".git").mkdir(parents=True)
    (root / "Tools/HangboardOnboarding/boards").mkdir(parents=True)
    (root / "Tools/hold-highlight-editor").mkdir(parents=True)
    assert validate_hang_ten_checkout(root) == root.resolve()
```

- [ ] **Step 2: Run the focused regressions (RED)**

Run:

```bash
rtk python -m pytest Tools/hold-highlight-editor/tests/test_server.py -k 'health or checkout' -q
rtk python -m pytest Tools/hold-highlight-editor/tests/test_workbench_binary.py -k 'browser or no_open' -q
```

Expected: FAIL because no health route or shared checkout validator exists and the binary opens a browser by default.

- [ ] **Step 3: Implement the narrow service contract**

Add the health branch before route dispatch in `EditorRequestHandler.do_GET`. Add `validate_hang_ten_checkout()` beside repository discovery, have `_configured_repository_root()` call it for explicit roots, and have discovery return only a validated root. Make packaged startup backend-only: keep `--no-open` accepted, remove the `webbrowser.open` dependency, print the loopback URL for diagnostics, and preserve SIGINT/SIGTERM cleanup.

- [ ] **Step 4: Verify focused and adjacent Python coverage (GREEN)**

```bash
rtk python -m pytest Tools/hold-highlight-editor/tests/test_server.py Tools/hold-highlight-editor/tests/test_workbench_binary.py -q
```

- [ ] **Step 5: Commit and push Task 1**

```bash
git add Tools/hold-highlight-editor/server.py Tools/hold-highlight-editor/workbench_binary.py Tools/hold-highlight-editor/tests/test_server.py Tools/hold-highlight-editor/tests/test_workbench_binary.py
git commit -m "Prepare workbench backend for native launch"
git push origin HEAD
```

### Task 2: Build the native AppKit/WebKit shell

**Files:**
- Create: `Tools/hold-highlight-editor/macos/Package.swift`
- Create: `Tools/hold-highlight-editor/macos/Sources/HangboardWorkbench/CheckoutSelection.swift`
- Create: `Tools/hold-highlight-editor/macos/Sources/HangboardWorkbench/BackendController.swift`
- Create: `Tools/hold-highlight-editor/macos/Sources/HangboardWorkbench/WorkbenchApp.swift`
- Create: `Tools/hold-highlight-editor/macos/Tests/HangboardWorkbenchTests/CheckoutSelectionTests.swift`
- Create: `Tools/hold-highlight-editor/macos/Tests/HangboardWorkbenchTests/BackendControllerTests.swift`

**Interfaces:**
- `CheckoutSelection.validatedURL(_:) throws -> URL` implements the same three checkout markers as Task 1.
- `CheckoutSelection.lastValidCheckout() -> URL?`, `remember(_:)`, and `clear()` persist only a normalized path in `UserDefaults` and revalidate it on read.
- `BackendController.start(repositoryRoot: URL, port: UInt16 = 0) async throws -> URL` starts the bundled executable with `--repository-root`, `--host 127.0.0.1`, `--port`, and `--no-open`, waits for `/api/health`, and returns the editor URL.
- `BackendController.stop() async` terminates and waits for its exact child process.
- The shell accepts `--headless --repository-root PATH --port PORT` only for CI: it starts the same backend without creating a window and exits cleanly on SIGTERM.

- [ ] **Step 1: Create package metadata and failing pure Swift tests**

Declare macOS 14 minimum and an executable target `HangboardWorkbench` with an XCTest target. Test valid/stale preference behavior against an isolated `UserDefaults` suite, command construction, health polling with an injected URL-session closure, startup timeout, and exactly-once process termination with fake process handles.

```swift
func testRememberedCheckoutIsDiscardedWhenMarkersDisappear() throws {
    let root = try makeCheckout()
    selection.remember(root)
    try FileManager.default.removeItem(at: root.appending(path: ".git"))
    XCTAssertNil(selection.lastValidCheckout())
}

func testStartPassesOnlyLoopbackBackendArguments() async throws {
    let url = try await controller.start(repositoryRoot: try makeCheckout(), port: 0)
    XCTAssertEqual(url.host, "127.0.0.1")
    XCTAssertEqual(process.arguments?.contains("--no-open"), true)
}
```

- [ ] **Step 2: Run Swift tests (RED)**

```bash
rtk swift test --package-path Tools/hold-highlight-editor/macos
```

Expected: FAIL because the package and shell types do not exist.

- [ ] **Step 3: Implement selection and backend lifecycle**

Keep UI-dependent `NSOpenPanel` code in `WorkbenchApp.swift`; keep validator, preferences, process abstraction, free-port selection, health polling, timeout, and shutdown in testable Foundation files. Locate the runtime at `Bundle.main.resourceURL!/workbench-runtime/hangboard-workbench`. On cancellation, terminate without starting a process. On a failed child/health probe, expose stderr text in a recoverable native error view; do not leave a blank web view.

- [ ] **Step 4: Implement the native app surface**

Use `NSApplicationDelegate`, one `NSWindow`, and `WKWebView`. At launch, load the remembered valid checkout or show `NSOpenPanel` configured for directories only. Add **Choose Hang Ten Checkout…** and **Quit Hangboard Workbench** menu commands. Switching checkouts stops the old backend before starting the new one. Closing the last window requests web-view confirmation for unsaved work, then awaits `BackendController.stop()`. Parse the CI-only `--headless` form before AppKit setup, require both explicit repository root and port, start the same controller, and wait for SIGTERM without creating a window.

- [ ] **Step 5: Verify native-shell behavior**

```bash
rtk swift test --package-path Tools/hold-highlight-editor/macos
rtk swift build -c release --arch arm64 --package-path Tools/hold-highlight-editor/macos
```

Expected: all XCTest cases pass and `.build/arm64-apple-macosx/release/HangboardWorkbench` is an arm64 Mach-O executable.

- [ ] **Step 6: Commit and push Task 2**

```bash
git add Tools/hold-highlight-editor/macos
git commit -m "Add native Hangboard Workbench shell"
git push origin HEAD
```

### Task 3: Package a signed embedded runtime and complete app bundle

**Files:**
- Modify: `Tools/hold-highlight-editor/packaging/build.py`
- Modify: `Tools/hold-highlight-editor/packaging/macos_app.py`
- Modify: `Tools/hold-highlight-editor/tests/test_workbench_packaging.py`
- Modify: `Tools/hold-highlight-editor/tests/test_macos_app.py`

**Interfaces:**
- `packaging/build.py --commit SHA --dist-dir DIR --work-dir DIR [--codesign-identity IDENTITY]` produces exactly `DIR/hangboard-workbench/` using PyInstaller `--onedir`.
- `packaging/macos_app.py --shell EXECUTABLE --runtime-dir DIR --output APP --version VERSION` creates `Hangboard Workbench.app` with `Contents/MacOS/HangboardWorkbench` and `Contents/Resources/workbench-runtime/hangboard-workbench`.

- [ ] **Step 1: Add failing packaging tests**

Assert PyInstaller arguments contain `--onedir`, never `--onefile`, include `--codesign-identity` only when supplied, and retain the explicit asset manifest. Assert the app bundler preserves shell/runtime modes, rejects a missing runtime executable, writes `CFBundleExecutable=HangboardWorkbench`, and never replaces a pre-existing bundle before validation.

```python
def test_pyinstaller_uses_onedir_and_optional_identity(tmp_path):
    metadata = tmp_path / "metadata"
    metadata.mkdir()
    (metadata / "build-commit.txt").write_text("a" * 40 + "\n", encoding="ascii")
    arguments = build._pyinstaller_arguments(
        REPOSITORY_ROOT, metadata, tmp_path / "dist", tmp_path / "work",
        codesign_identity="Developer ID Application: Test (TEAM)",
    )
    assert "--onedir" in arguments
    assert "--onefile" not in arguments
    assert arguments[arguments.index("--codesign-identity") + 1].startswith("Developer ID Application:")
```

- [ ] **Step 2: Run packaging tests (RED)**

```bash
rtk python -m pytest Tools/hold-highlight-editor/tests/test_workbench_packaging.py Tools/hold-highlight-editor/tests/test_macos_app.py -q
```

Expected: FAIL because the build emits one file and the bundler has no shell/runtime contract.

- [ ] **Step 3: Implement runtime and bundle assembly**

Make `_require_expected_output()` require the executable directory and its `hangboard-workbench` child. Pass `--codesign-identity` to PyInstaller only after validating a non-empty identity. Refactor the app builder to stage a shell executable and recursively copy the runtime to `Contents/Resources/workbench-runtime`; preserve paths and modes, then atomically replace the output. Keep signing out of the builder.

- [ ] **Step 4: Verify packaging contracts (GREEN)**

```bash
rtk python -m pytest Tools/hold-highlight-editor/tests/test_workbench_packaging.py Tools/hold-highlight-editor/tests/test_macos_app.py -q
rtk python Tools/hold-highlight-editor/packaging/build.py --commit "$(git rev-parse HEAD)" --dist-dir /tmp/hangboard-runtime --work-dir /tmp/hangboard-build
```

Expected: tests pass and `/tmp/hangboard-runtime/hangboard-workbench/hangboard-workbench` exists. Remove only those exact `/tmp` directories after inspection.

- [ ] **Step 5: Commit and push Task 3**

```bash
git add Tools/hold-highlight-editor/packaging/build.py Tools/hold-highlight-editor/packaging/macos_app.py Tools/hold-highlight-editor/tests/test_workbench_packaging.py Tools/hold-highlight-editor/tests/test_macos_app.py
git commit -m "Bundle native workbench runtime"
git push origin HEAD
```

### Task 4: Verify the final native app in CI and publish it safely

**Files:**
- Modify: `.github/workflows/hangboard-workbench-release.yml`
- Modify: `Tools/hold-highlight-editor/tests/test_workbench_release_workflow.py`

**Interfaces:**
- Pull-request build creates an unsigned final app, invokes its noninteractive `--headless --repository-root "$GITHUB_WORKSPACE" --port 41739` launcher, verifies `/api/health`, `/`, static assets, and `/api/library`, then stops the owned child.
- Release rebuilds the onedir runtime using the unique Developer ID Application identity, builds the Swift shell, assembles the app, signs nested runtime code and app shell, notarizes, staples, Gatekeeper-assesses, launch-smoke-tests, and publishes the ZIP/checksum pair.

- [ ] **Step 1: Add failing workflow assertions**

Extend workflow tests to require Swift build/test, `--onedir`, `--codesign-identity` only in the release job, a final-app headless smoke step, `GET /api/health`, and signing of every nested runtime Mach-O before the outer app. Assert pull-request jobs contain no Apple credentials and no `notarytool` invocation.

- [ ] **Step 2: Run workflow test (RED)**

```bash
rtk python -m pytest Tools/hold-highlight-editor/tests/test_workbench_release_workflow.py -q
```

Expected: FAIL because CI tests only the intermediate one-file executable.

- [ ] **Step 3: Implement CI stages**

In `build`, build the Python onedir runtime and release Swift shell, assemble an unsigned `.app`, and test the app’s headless launcher against `$GITHUB_WORKSPACE`. In `release`, set up Python and Swift, import the existing certificate, identify the one matching `APPLE_TEAM_ID`, rebuild the runtime with `--codesign-identity`, assemble the app, sign every Mach-O under `Contents/Resources/workbench-runtime`, sign the shell and outer app with hardened runtime, then reuse the current notarize/staple/checksum/release safeguards. Keep cleanup traps limited to the exact app processes and temporary key file created by this job.

- [ ] **Step 4: Verify workflow parsing and all focused suites (GREEN)**

```bash
rtk python -m pytest Tools/hold-highlight-editor/tests/test_workbench_release_workflow.py Tools/hold-highlight-editor/tests/test_workbench_packaging.py Tools/hold-highlight-editor/tests/test_macos_app.py -q
rtk swift test --package-path Tools/hold-highlight-editor/macos
```

- [ ] **Step 5: Commit and push Task 4**

```bash
git add .github/workflows/hangboard-workbench-release.yml Tools/hold-highlight-editor/tests/test_workbench_release_workflow.py
git commit -m "Test native workbench releases end to end"
git push origin HEAD
```

### Task 5: Document the native workflow and run the release regression suite

**Files:**
- Modify: `Tools/hold-highlight-editor/README.md`
- Modify: `Tools/HangboardOnboarding/README.md`

**Interfaces:**
- Documents the released app as a native window that chooses a checkout on launch, remembers the last valid checkout, offers a switch command, and writes only to the selected checkout.

- [ ] **Step 1: Add documentation assertions where the repository uses them**

Extend the release-workflow/documentation test to require the native launch wording and reject instructions to open a localhost URL, run the app from a checkout, remove quarantine, or launch a default browser.

- [ ] **Step 2: Update both quick starts**

Keep ZIP/checksum and `open "Hangboard Workbench.app"` instructions. Explain the first-launch folder picker, remembered checkout behavior, **Choose Hang Ten Checkout…**, direct local saves with normal Git review, native failure/retry behavior, and that remote hosting is not yet shipped.

- [ ] **Step 3: Run the full local regression boundary**

```bash
rtk python -m pytest Tools/hold-highlight-editor/tests Tools/HangboardOnboarding/tests -q
rtk node --test Tools/hold-highlight-editor/tests/workbench*.test.js
rtk swift test --package-path Tools/hold-highlight-editor/macos
git diff --check
```

Expected: all suites pass with no whitespace errors.

- [ ] **Step 4: Commit and push Task 5**

```bash
git add Tools/hold-highlight-editor/README.md Tools/HangboardOnboarding/README.md Tools/hold-highlight-editor/tests/test_workbench_release_workflow.py
git commit -m "Document native workbench launch flow"
git push origin HEAD
```

## Final Acceptance Check

- [ ] Download the published Apple Silicon ZIP on a clean Mac, open the app, select a valid checkout, and confirm the editor appears only in its native window.
- [ ] Quit and relaunch; confirm the same valid checkout is selected without a picker. Rename or remove a required marker; confirm the picker returns.
- [ ] Switch to a second checkout, save an edit, and verify only that checkout has Git-visible changes.
- [ ] Verify the app has a valid Developer ID signature, notarization ticket, stapled ticket, and Gatekeeper assessment.
- [ ] Confirm the editor UI retains only HTTP relative API calls, so serving that UI and API together remotely remains an additive future deployment.
