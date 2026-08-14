# Workbench Tools Suite Implementation Plan

> **For agentic workers:** Execute each task with a fresh implementation
> subagent and a separate review checkpoint. Start from a failing regression
> test, make the smallest direct change, run the listed checks, commit only the
> task's files, and push each commit.

**Goal:** Delete `Tools/HangboardPipeline/` and make Hangboard Workbench the
standalone, direct board-authoring suite: board library, image import, hold
editor, validation, and atomic package save.

**Architecture:** Workbench owns direct package modules and the HTTP boundary.
They read and write `Hangboards/<slug>/board.json`, `artwork.json`, and assets
without revisions, stages, artifacts, or a workspace store. Each physical hold
maps to one closed contiguous artwork outline and one `board.json` metadata
record. Save validates a full candidate package then atomically replaces the
package/catalog under a library lock.

**Tech stack:** Python 3.11, dependency-free JavaScript, Swift/AppKit/WebKit,
pytest, Node test runner, SwiftPM, PyInstaller.

## Constraints

- Remove—not hide—`Tools/HangboardPipeline/` and all production references to
  `hangboard_vectorizer`, pipeline, stages, runs, checkpoints, approval, and
  promotion.
- Retain only canonical package data and user-visible direct tools. Do not
  migrate old run directories or create compatibility imports.
- One hold ID has exactly one closed, contiguous outline; decorative artwork
  cannot be hold geometry.
- Constrain every file access to the selected repository/package and avoid
  exposing filesystem paths in HTTP errors.
- Every save must leave the prior package/catalog intact on validation or I/O
  failure.
- Update or delete tests with the code they cover. New behavior is test-first.

---

### Task 1: Establish standalone direct-package primitives

**Files:**
- Add: `Tools/HangboardWorkbench/board_package.py`
- Add: `Tools/HangboardWorkbench/board_geometry.py`
- Add: `Tools/HangboardWorkbench/tests/test_board_package.py`
- Add: `Tools/HangboardWorkbench/tests/test_board_geometry.py`
- Delete after migration: selected equivalent code under
  `Tools/HangboardPipeline/src/hangboard_vectorizer/`

**Work:**

1. Write failing tests for catalog/package discovery, canonical primary-image
   lookup, direct editor-document generation, and safe candidate replacement.
2. Write failing geometry tests for a valid single closed contour and rejected
   duplicate hold IDs, multiple contours, self-intersection, out-of-canvas
   coordinates, and mismatched board/artwork hold IDs.
3. Move only the package parsing, path confinement, display-path parsing,
   bounding-frame derivation, and validation needed by Workbench into direct
   Workbench modules. Name interfaces after boards and packages, not pipeline
   lifecycle concepts.
4. Implement a library-locked atomic package/catalog transaction that validates
   its staging tree before replacing the live package.
5. Run focused pytest tests and confirm the new modules contain no
   `hangboard_vectorizer` import.

**Verification:**

```sh
python -m pytest -q Tools/HangboardWorkbench/tests/test_board_package.py Tools/HangboardWorkbench/tests/test_board_geometry.py
rg -n 'hangboard_vectorizer|stage-|run_root|checkpoint' Tools/HangboardWorkbench/board_package.py Tools/HangboardWorkbench/board_geometry.py
```

---

### Task 2: Replace the Workbench server lifecycle API with direct board APIs

**Files:**
- Modify: `Tools/HangboardWorkbench/server.py`
- Modify: `Tools/HangboardWorkbench/job_manager.py` or delete it if no direct
  operation needs it
- Modify: `Tools/HangboardWorkbench/tests/test_server.py`
- Delete: lifecycle-only server tests and fixtures

**Work:**

1. First add API regressions for listing packages, opening a package with its
   image and full hold document, and saving an edited contour/frame pair.
2. Prove an invalid save leaves both the package and catalog byte-for-byte
   unchanged; prove an image/document load failure does not surface a path.
3. Replace `WorkbenchService`, `WorkbenchStore`, revision, artifact, and
   guided mutation calls with direct board-library/load/save calls.
4. Delete `--run-dir`, catalog-run parsing, stage-artifact discovery, retries,
   approvals, and polling endpoints. Retain only explicit direct tool actions.
5. Run the server suite, including an assertion that importing `server` works
   when `Tools/HangboardPipeline` is absent.

**Verification:**

```sh
python -m pytest -q Tools/HangboardWorkbench/tests/test_server.py
rg -n -i 'pipeline|stage|run|checkpoint|approval|promotion' Tools/HangboardWorkbench/server.py
```

---

### Task 3: Make the browser a board-and-tools UI

**Files:**
- Modify: `Tools/HangboardWorkbench/app.js`
- Modify: `Tools/HangboardWorkbench/index.html`
- Modify: `Tools/HangboardWorkbench/workbench-client.js`
- Modify: `Tools/HangboardWorkbench/workbench-controller.js`
- Modify/delete: `Tools/HangboardWorkbench/workbench-suite-*.js` as dictated by
  the direct model
- Modify: corresponding `Tools/HangboardWorkbench/tests/*.test.js`

**Work:**

1. Add failing browser tests for the single Board library, direct editor load,
   saved-contour rendering, save errors retaining editor state, and direct new
   board creation.
2. Remove Recent runs, In progress, static mode, stage navigation, approval,
   retry, final-save, and pipeline messages from the UI and client state.
3. Use direct Board/Image/Holds/Validation/Save actions; do not create a
   replacement “run” or background workspace concept.
4. Make hold selection and save operate on one contour per hold. The editor
   should reject invalid geometry before a server request where practical and
   show the server's validation message when necessary.
5. Run all browser tests and scan visible markup/client source for prohibited
   product language.

**Verification:**

```sh
node --test Tools/HangboardWorkbench/tests/workbench*.test.js Tools/HangboardWorkbench/tests/editor*.test.js
rg -n -i 'recent runs|in progress|stage|checkpoint|approval|pipeline|promotion' Tools/HangboardWorkbench/app.js Tools/HangboardWorkbench/index.html Tools/HangboardWorkbench/workbench-*.js
```

---

### Task 4: Make the packaged macOS Workbench self-contained

**Files:**
- Modify: `Tools/HangboardWorkbench/packaging/build.py`
- Modify: `Tools/HangboardWorkbench/workbench_binary.py`
- Modify: `Tools/HangboardWorkbench/macos/Sources/HangboardWorkbench/CheckoutSelection.swift`
- Modify: `Tools/HangboardWorkbench/macos/Sources/HangboardWorkbench/BackendController.swift`
- Modify: matching Python and Swift tests

**Work:**

1. Add failing packaging tests that build the runtime with only Workbench and
   `Hangboards/` present, and assert no hidden import/path points at the
   deleted pipeline package.
2. Bundle Workbench's direct modules with the executable and update checkout
   validation to require the direct server/package layout instead of pipeline
   sources.
3. Preserve runtime/checkout identity preflight, but make its recovery copy
   describe a direct Workbench version mismatch.
4. Run Python packaging/binary tests and the SwiftPM test suite.

**Verification:**

```sh
python -m pytest -q Tools/HangboardWorkbench/tests/test_workbench_binary.py Tools/HangboardWorkbench/tests/test_workbench_packaging.py Tools/HangboardWorkbench/tests/test_macos_app.py
swift test --package-path Tools/HangboardWorkbench/macos
```

---

### Task 5: Delete the pipeline and remove repository-wide references

**Files:**
- Delete: `Tools/HangboardPipeline/`
- Modify/delete: `scripts/hangboard-tools.sh`
- Modify: `scripts/stage-board-packages.py`
- Modify: `.github/actions/build-hangboard-workbench/action.yml`
- Modify: `.github/workflows/ci.yml`
- Modify: `.github/workflows/hangboard-workbench-release.yml`
- Modify: `.github/ci-paths.yml`, `.github/dependabot.yml`
- Modify: `README.md`, Workbench README, and active contributor guides
- Delete/update: pipeline-only tests, fixtures, and source-audit instructions

**Work:**

1. Replace CI/install/cache configuration with explicit Workbench test and
   packaging dependencies. Remove obsolete pipeline CLI/release jobs rather
   than rerouting them through compatibility wrappers.
2. Remove user documentation for runs, Stage 2 review, and pipeline commands;
   document direct package validation through Workbench instead.
3. Delete the pipeline directory only after the standalone checks pass.
4. Add an integration regression that a clean checkout missing that directory
   lists and opens the registered Metolius package with its hold count.
5. Scan the repository for deleted concepts and allow only historical records
   under `docs/history/` when needed to preserve factual project history.

**Verification:**

```sh
test ! -e Tools/HangboardPipeline
python -m pytest -q Tools/HangboardWorkbench/tests
node --test Tools/HangboardWorkbench/tests/workbench*.test.js Tools/HangboardWorkbench/tests/editor*.test.js
swift test --package-path Tools/HangboardWorkbench/macos
rg -n -i 'Tools/HangboardPipeline|hangboard_vectorizer' --glob '!docs/history/**' --glob '!docs/superpowers/specs/2026-08-13-direct-board-editor-design.md' --glob '!docs/superpowers/plans/2026-08-13-direct-board-editor.md'
git diff --check
```

---

### Task 6: Final integration, review, and PR

**Work:**

1. Run the direct Workbench Python/browser/native suites and relevant app
   catalog validation.
2. Manually open the packaged/direct server against this checkout: select the
   Metolius board, verify holds appear, edit one contour, save, reload, and
   verify the change persists without an In progress/Recent runs screen.
3. Run a final code review focused on deletion completeness, atomic save
   rollback, geometry invariants, and filesystem confinement.
4. Push all commits and create the requested pull request with a concise
   migration summary and verification results.
