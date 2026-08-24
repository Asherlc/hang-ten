# Unversioned Board Packages Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development or superpowers:executing-plans task-by-task.

**Goal:** Convert every board package to one unversioned multi-presentation document and delete v1/v2 parsing.

**Architecture:** A deterministic script converts the 33 single-presentation documents. Python Workbench/package tooling and Swift then require `presentations` and a declared `presentationID` for every hold.

**Tech Stack:** Python, JSON, pytest, Swift Codable, XCTest.

**Spec:** `docs/superpowers/specs/2026-08-24-unversioned-content-formats-design.md`

## Global Constraints

- No board document has `schemaVersion` or `presentation`.
- Every hold has a known `presentationID`; image, geometry, source text, and hold metadata remain unchanged.
- Stale versioned documents fail strict decoding; no fallback is retained.

### Task 1: Migrate the catalog deterministically

**Files:** Create `Tools/HangboardPackages/scripts/migrate_unversioned_board_packages.py`; modify `Hangboards/*/board.json`; test `Tools/HangboardPackages/tests/test_approved_board_packages.py`.

- [ ] Write `test_every_approved_board_uses_the_unversioned_presentation_shape`, asserting no version/legacy keys, exactly one default, and each hold ID is declared by `presentations`.
- [ ] Run `uv run --with pytest python -m pytest -q Tools/HangboardPackages/tests/test_approved_board_packages.py -k unversioned_presentation_shape`; expect failure on current documents.
- [ ] Implement `migrate(document)`: remove `schemaVersion`/`presentation`; add `[{"id":"primary","name":"Primary","assetPath":"assets/primary.png","aspectRatio":document["aspectRatio"],"default":true}]` when absent; add `presentationID: "primary"` only when absent; write stable formatted JSON.
- [ ] Run the script twice, then run `git diff --exit-code -- Hangboards`; expect no second-run diff.
- [ ] Run `uv run --with pytest python -m pytest -q Tools/HangboardPackages/tests/test_approved_board_packages.py`; expect pass.
- [ ] Commit: `git add Hangboards Tools/HangboardPackages/scripts Tools/HangboardPackages/tests/test_approved_board_packages.py && git commit -m "Migrate board packages to one unversioned shape"`.

### Task 2: Require the fixed shape in Python tooling

**Files:** Modify `Tools/HangboardWorkbench/board_package.py`, `Tools/HangboardWorkbench/github_board_store.py`, `Tools/HangboardPackages/src/hangboard_packages/board_catalog.py`, and their pytest fixtures/tests.

- [ ] Add failing tests that a valid unversioned board lists through `GitHubBoardStore` with one `board.json` blob fetch, while a `schemaVersion`, `presentation`, missing `presentations`, missing `presentationID`, or unknown `presentationID` raises the existing validation error.
- [ ] Run `uv run --with pytest python -m pytest -q Tools/HangboardWorkbench/tests/test_board_package.py Tools/HangboardWorkbench/tests/test_github_board_store.py Tools/HangboardPackages/tests/test_board_catalog.py`; expect new strict tests to fail.
- [ ] Replace `_BOARD_FIELDS` with the one unversioned field set; make `_parse_board_presentations` require it; remove schema dispatch, synthetic primary conversion, and v1 fixtures; call `_validate_hold(..., requires_presentation_id=True)` everywhere.
- [ ] Run `uv run --with pytest python -m pytest -q Tools/HangboardWorkbench/tests Tools/HangboardPackages/tests` and `(cd Tools/HangboardWorkbench && npm test)`; expect pass and no image fetch during catalog listing.
- [ ] Commit: `git add Tools/HangboardWorkbench Tools/HangboardPackages && git commit -m "Require unversioned board documents"`.

### Task 3: Require the fixed shape in iOS

**Files:** Modify `HangTen/Models/BoardPackageStore.swift`, `HangTen/Models/TrainingModels.swift`, `HangTenTests/BoardPackageStoreTests.swift`, `HangTenTests/BoardSourceBoundaryTests.swift`.

- [ ] Add failing XCTest assertions that bundled documents omit former keys and a fixture with `schemaVersion` fails decode.
- [ ] Remove `validateSchema`, `legacyPresentation`, v1 aspect-ratio/hold branches, and `presentationDocuments` synthesis. Decode required presentations and hold presentation IDs directly, rejecting unknown keys.
- [ ] Run `xcodebuild test -project HangTen.xcodeproj -scheme HangTen -destination 'platform=iOS Simulator,name=iPhone 16 Pro' -only-testing:HangTenTests/BoardPackageStoreTests -only-testing:HangTenTests/BoardSourceBoundaryTests`; expect pass.
- [ ] Commit: `git add HangTen/Models HangTenTests/BoardPackageStoreTests.swift HangTenTests/BoardSourceBoundaryTests.swift && git commit -m "Remove legacy board package decoding"`.
