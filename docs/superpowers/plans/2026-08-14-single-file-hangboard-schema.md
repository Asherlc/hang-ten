# Single-File Hangboard Schema Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace catalog-and-sidecar board packages with directory-discovered single-file physical board documents, then author accurate selectable holds for every board under `Hangboards/`.

**Architecture:** `board.json` is the only structured document in a finished board directory and embeds each hold's physical metadata and exact normalized geometry. Repository tooling and the iOS app discover direct child directories, derive runtime bounds from geometry, and leave undocumented optional facts unknown. Rendering policy and training-plan semantics remain outside board data.

**Tech Stack:** JSON, Python 3.11+, pytest, Swift 5, XCTest, SwiftUI, Xcode.

## Global Constraints

- A finished board directory contains exactly `board.json` and `assets/primary.png`.
- Remove `Hangboards/catalog.json`, `artwork.json`, `semantics.json`, and `evidence.json` from the canonical format.
- Every hold requires `id`, `name`, `kind`, and nonempty `geometry`; `kind` is exactly `jug`, `edge`, `pocket`, `pinch`, or `sloper` and may be classified through reviewed photos/specifications.
- `sizeMillimeters`, `depthRangeMillimeters`, `fingerCapacity`, `gripType`, and `features` are optional and omitted when unknown. Runtime code must not supply invented defaults.
- `cueStyle`, `shortLabel`, coaching detail, palettes, colors, shadows, and gradients are not board data.
- The same geometry piece paths draw normal contact, active contact, and hit-testing geometry. Runtime bounds are the union of a hold's pieces.
- `aspectRatio` is the presentation PNG's pixel width divided by height and must match it within 0.1% relative error.
- Board packages contain no routine semantic mappings or source/provenance metadata.
- Direct-child packages sort deterministically by manufacturer, name, then ID; duplicates, malformed packages, unsafe paths, and symlinks fail closed.
- Primary-only directories may be ignored during migration. Final inventory validation requires every `Hangboards/` board directory to contain a valid `board.json`.
- Use a fresh implementation subagent per task, run task-scoped review after every task, commit intentionally, and push every new commit to `origin` automatically.

---

### Task 1: Define the physical schema and unknown-value runtime model

**Files:**
- Modify: `HangTen/Models/TrainingModels.swift`
- Modify: `HangTen/Models/BoardStorage.swift`
- Modify: `HangTen/Views/BoardMapView.swift`
- Modify: `HangTen/Views/GripDiagramView.swift`
- Test: `HangTenTests/BoardStorageTests.swift`
- Test: `HangTenTests/BoardPackageStoreTests.swift`

**Interfaces:**
- Produces: a decodable hold document with required `id`, `name`, `kind`, and `[BoardHoldPieceDocument]` geometry.
- Produces: `BoardHold` values whose measurement, capacity, grip posture, and features remain optional when absent.
- Produces: geometry-derived bounds and one path source for normal, active, and interactive states.

- [x] **Step 1: Write failing model tests.**
  Add fixtures omitting all optional physical metadata; assert decoded runtime values remain `nil` rather than becoming open-hand/four-finger defaults. Add tests that empty geometry and invalid kinds fail.
- [x] **Step 2: Verify RED.**
  Run `xcodebuild test -project HangTen.xcodeproj -scheme HangTen -destination 'platform=iOS Simulator,name=iPhone 17 Pro' -only-testing:HangTenTests/BoardStorageTests -only-testing:HangTenTests/BoardPackageStoreTests` and confirm the new expectations fail for the missing schema.
- [x] **Step 3: Implement the minimal physical model.**
  Remove package-facing cue/label/detail fields, preserve optionals end to end, embed piece documents on holds, and derive the runtime frame from their union. Keep compatibility only where non-package test fixtures require it.
- [x] **Step 4: Make rendering and hit testing share geometry.**
  Route normal fill, active fill, and interactions through the same piece paths. Derive display cue behavior inside app views and show neutral UI when physical metadata is absent.
- [x] **Step 5: Verify GREEN, commit, and push.**
  Re-run the focused tests, commit as `refactor: model physical hangboard holds`, and run `git push -u origin HEAD`.

### Task 2: Replace catalog loading with directory discovery

**Files:**
- Modify: `HangTen/Models/BoardPackageStore.swift`
- Modify: `Tools/HangboardWorkbench/board_package.py`
- Modify: `Tools/HangboardWorkbench/server.py`
- Modify: `scripts/stage-board-packages.py`
- Test: `HangTenTests/BoardPackageStoreTests.swift`
- Test: `Tools/HangboardWorkbench/tests/test_board_package.py`
- Test: `Tools/HangboardWorkbench/tests/test_server.py`

**Interfaces:**
- Produces: direct-child discovery for repositories, staged bundles, and `BoardPackageStore`.
- Produces: deterministic manufacturer/name/ID ordering and fail-closed validation.

- [x] **Step 1: Write failing discovery tests.**
  Cover multiple direct-child packages without a catalog, primary-only draft exclusion, duplicate board IDs, malformed completed packages, missing `primary.png`, symlinks/path escapes, and deterministic sorting.
- [x] **Step 2: Verify RED.**
  Run `rtk uv run --with pytest python -m pytest -q Tools/HangboardWorkbench/tests/test_board_package.py Tools/HangboardWorkbench/tests/test_server.py` and the focused `BoardPackageStoreTests` target.
- [x] **Step 3: Implement directory discovery.**
  Remove catalog decoding and sidecar requirements from the Workbench and iOS store. Enumerate only direct children, load `board.json`, validate the exact package shape, expose the same packages through the direct server API, and stage completed directories without generating a registry.
- [x] **Step 4: Preserve migration and final modes.**
  Keep a validator mode that ignores primary-only drafts during migration and add a final-inventory mode that rejects them. Maintain all symlink and traversal protections.
- [x] **Step 5: Verify GREEN, commit, and push.**
  Re-run Python and Swift-focused tests, commit as `refactor: discover hangboards by directory`, and run `git push origin HEAD`.

### Task 3: Migrate the Compact II reference package

**Files:**
- Modify: `Hangboards/metolius-wood-grips-compact-ii/board.json`
- Delete: `Hangboards/metolius-wood-grips-compact-ii/artwork.json`
- Delete: `Hangboards/metolius-wood-grips-compact-ii/semantics.json`
- Delete: `Hangboards/metolius-wood-grips-compact-ii/evidence.json`
- Delete: `Hangboards/catalog.json`
- Modify: `Tools/HangboardWorkbench/tests/test_board_package.py`
- Modify: `Tools/HangboardWorkbench/tests/test_board_geometry.py`
- Modify: `Tools/HangboardWorkbench/tests/test_server.py`
- Modify: `HangTenTests/BoardSourceBoundaryTests.swift`

**Interfaces:**
- Consumes: the current Compact II physical holds and artwork paths.
- Produces: the first complete single-file package and an end-to-end fixture for later batches.

- [x] **Step 1: Write the failing migrated-package assertions.**
  Assert the directory contains only `board.json` and `assets/primary.png`, every hold has geometry, optional facts preserve their current sourced values, and no removed sidecar/root catalog remains.
- [x] **Step 2: Verify RED.**
  Run the focused Workbench package/geometry/server tests plus the Swift source-boundary and package-store tests.
- [x] **Step 3: Merge physical data and exact paths.**
  Move each current hold's pieces into its board record, remove UI-only fields, preserve multiple pieces where applicable, and delete obsolete sidecars and root catalog.
- [x] **Step 4: Validate visual invariants.**
  Assert hold IDs are unique, each geometry set is nonempty, mirrored pairs remain exact mirrors where applicable, and interaction bounds equal piece unions.
- [x] **Step 5: Verify GREEN, commit, and push.**
  Run focused Python/Swift tests plus `xcodebuild build -project HangTen.xcodeproj -scheme HangTen -destination 'generic/platform=iOS Simulator'`, commit as `refactor: migrate Compact II board package`, and run `git push origin HEAD`.

### Task 4: Author every remaining board in audited batches

**Files:**
- Create: `Hangboards/<board>/board.json` for every primary-only board directory.
- Modify: batch expectations in `Tools/HangboardWorkbench/tests/test_board_package.py`.
- Modify when API behavior changes: `Tools/HangboardWorkbench/tests/test_server.py`.
- Modify: `HangTenTests/BoardSourceBoundaryTests.swift`.

**Interfaces:**
- Consumes: each board's `assets/primary.png`, current manufacturer documentation, supplemental geometry imagery, and `.context/hangboard-audits/group-*.md` research.
- Produces: required physical hold inventories and smooth normalized geometry with optional facts only where reliable.

- [ ] **Step 1: Dispatch one fresh implementer per small non-overlapping batch.**
  Each brief names exact board slugs, proposed hold IDs/kinds, symmetry rules, measurements safe to retain, and unresolved image cautions from its audit report.
- [ ] **Step 2: Author geometry from silhouette to contact pieces.**
  Define mirrored geometry once where supported, omit screws/branding, keep continuous rails continuous, split genuinely distinct contacts, and use smooth paths with normalized coordinates.
- [ ] **Step 3: Validate and review each batch.**
  Run focused Workbench package/geometry tests, the real staging script into an owned temporary resource directory, and board-specific ID/geometry assertions. Dispatch an independent reviewer for spec compliance and geometry/data quality; fix every Critical/Important finding before the next batch.
- [ ] **Step 4: Commit and push each accepted batch.**
  Use a manufacturer/batch-specific commit message and run `git push origin HEAD` after every new commit.
- [ ] **Step 5: Close the migration gate.**
  When all directories are authored, enable final-inventory validation so no primary-only draft remains.

### Task 5: Run integrated verification and visual review

**Files:**
- Modify only if a verified defect is found: package tests, rendering code, or affected `board.json` documents.

**Interfaces:**
- Consumes: every completed direct-child package.
- Produces: fresh automated, build, and screenshot evidence for the whole catalog.

- [ ] **Step 1: Run complete package verification.**
  Run `rtk uv run --with pytest python -m pytest -q Tools/HangboardWorkbench/tests`, run `rtk node --test Tools/HangboardWorkbench/tests/workbench*.test.js`, and invoke `scripts/stage-board-packages.py` against the final directory inventory in an owned temporary Xcode resource destination.
- [ ] **Step 2: Run complete iOS verification.**
  Run `xcodebuild test -project HangTen.xcodeproj -scheme HangTen -destination 'platform=iOS Simulator,name=iPhone 17 Pro'` and `xcodebuild build -project HangTen.xcodeproj -scheme HangTen -destination 'generic/platform=iOS Simulator'`.
- [ ] **Step 3: Capture owned-simulator screenshots.**
  Follow `validate-hang-ten-ios`; create and record an exact workspace-owned simulator, inspect every board inactive and active in portrait and landscape, save requested screenshots under `.context`, and delete the exact simulator through the cleanup trap.
- [ ] **Step 4: Run whole-branch review and one fix wave.**
  Give the final reviewer the complete branch diff and all deferred findings. Dispatch one fresh fixer for Critical/Important issues, then one scoped re-review.
- [ ] **Step 5: Verify, commit, and push final fixes.**
  Re-run every command that supports the final claims, commit any verified fix, and run `git push origin HEAD`.

## Self-review

- The plan covers the user-approved removal of every catalog/sidecar schema and preserves only `board.json` plus `primary.png`.
- Required and optional hold fields are consistent across model, loader, authoring, and tests.
- Geometry has one source for drawing, highlighting, interaction, and derived bounds.
- Migration and final inventory behavior are explicitly separate.
- Every implementation task has a focused red/green test cycle, review gate, commit, and push.
