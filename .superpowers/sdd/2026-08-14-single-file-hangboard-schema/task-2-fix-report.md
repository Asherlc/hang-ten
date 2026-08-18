# Task 2 review-fix report

Date: 2026-08-14

Status: complete

## Review findings and fixes

1. Plan-owned semantic mappings were being replaced by board-package data when the bundled plan library was loaded. Validation and resolution also reconstructed mappings from `TrainingBoard`, and the migration seed still read removed package semantics. The store now preserves the plan document unchanged, validation and resolution use `PlanLibraryDefinition.boardMappings`, and the migration fallback owns the exact existing Compact II mappings. The physical board package remains semantic-free.

2. Workbench discovery had a second, incompatible ID grammar, accepted dotted directory slugs, treated non-minimal directories as drafts, and exposed duplicate published board IDs. Discovery now uses the canonical catalog predicates, accepts canonical IDs containing `_`, restricts package slugs to the canonical flat slug grammar, accepts only an exact `assets/primary.png` draft, and diagnoses/removes every ambiguous published ID.

3. Canonical package materialization collapsed multi-piece holds onto repeated keys, repeated `pieceIndex = 0`, reported physical-hold counts as region counts, and used union hold bounds for each piece. Every geometry piece now receives a stable unique region key, integer ID, local piece index, and piece-specific bounds/anchor, while `metadata.holdID` preserves the physical hold identity. Stage 4 continues to group paths by physical hold and validation deduplicates semantic mappings by that identity.

4. Package replacement is rollback-safe but cannot be reader-atomic for raw filesystem readers because the existing directory is temporarily renamed away. The code and tests now state that boundary accurately. Workbench publication takes an exclusive lock on the stable `Hangboards` root inode and repository snapshots take a shared lock, so cooperating readers never observe the rename-away window.

## Test-first evidence

RED evidence was captured before each implementation change:

- Four focused Swift plan tests failed because `edge-19`/`edge-29` disappeared from the effective plan mappings and the fallback seed attempted to read package semantics.
- Six focused Python tests failed for extra-file drafts, incompatible slug/ID handling, duplicate IDs, repeated multi-piece keys and metadata, and a reader observing the package rename-away window.

GREEN verification:

- Focused Swift plan regressions: 4 passed (`PlanStorageTests` mapping preservation, migration fallback, validation authority, and resolver override).
- Directly impacted Python suites: 72 passed, 19 existing Pillow deprecation warnings.
- Full Task 2 Python set: 96 passed, 19 existing Pillow deprecation warnings.
- Workbench server suite: 120 passed.
- `git diff --check`: passed.

A broader `PlanStorageTests` + `BoardPackageStoreTests` Xcode run was time-boxed and stopped while still building; it emitted no test failure and did not reach the test runner. Its exact isolated simulator and derived data were deleted afterward. No broader-suite success is claimed here.

## Files changed

- `HangTen/Models/PlanStorage.swift`
- `HangTen/Models/TrainingModels.swift`
- `HangTenTests/PlanStorageTests.swift`
- `Tools/HangboardPipeline/src/hangboard_vectorizer/board_catalog.py`
- `Tools/HangboardPipeline/src/hangboard_vectorizer/board_library.py`
- `Tools/HangboardPipeline/src/hangboard_vectorizer/workbench_promotion.py`
- `Tools/HangboardPipeline/src/hangboard_vectorizer/workbench_validation.py`
- `Tools/HangboardPipeline/tests/test_board_library.py`
- `Tools/HangboardPipeline/tests/test_workbench_end_to_end.py`

## Remaining concern

Non-cooperating raw filesystem readers are outside the publication lock protocol and may still observe the rename-away interval. The supported Workbench reader path is coordinated and covered by a deterministic concurrency regression test.
