# Task 4 validation report

Date: 2026-09-10  
Owner: `gray-horse`

## Scope

- Added Nature Stone Hanger catalog, default model/path, stable eight-hold
  identity, native highlight/clear, passage-marker selection/accessibility,
  unsupported suspension, workout-target resolution, and model/raster routing
  regressions in `HangTenTests/BoardModelTests.swift`.
- Added the previously tracked Task 1 source
  `HangTen/Views/SuspendedBoardPresentation.swift` to the existing source
  boundary manifest after the XCTest build gate reported the exact mismatch.
- No production Swift, Hangboards, Tools, Task 1 implementation, or Task 3
  package content was modified.

## Package checks

- `.context/import-hangboard-model-packages/gray-horse-hangboard-packages-venv/bin/hangboard-packages validate --root Hangboards --final-inventory`
  - PASS: 63 boards, no drafts; `nature.stone-hanger` present.
- `.context/import-hangboard-model-packages/gray-horse-hangboard-packages-venv/bin/pytest -q Tools/HangboardPackages/tests/test_model_first_packages.py`
  - PASS: 93 tests in 0.24 seconds.
- `git diff --check`
  - PASS.

The first `pytest` attempt used an unavailable PATH command and failed before
collection; rerunning the same focused file with the workspace-owned virtual
environment produced the passing result above.

## XCTest and simulator validation

Command:

```sh
xcodebuild -project HangTen.xcodeproj -scheme HangTen -configuration Debug \
  -destination 'platform=iOS Simulator,id=52CAE34D-9161-41FA-83EB-5148812F7CBB' \
  -derivedDataPath .context/DerivedData \
  -only-testing:HangTenTests/BoardModelTests test
```

- Simulator: `Hang Ten Paseo gray-horse Review`
- UUID: `52CAE34D-9161-41FA-83EB-5148812F7CBB`
- PASS: 16 tests, 0 failures; `** TEST SUCCEEDED **`.
- Installed the exact app from
  `.context/DerivedData/Build/Products/Debug-iphonesimulator/HangTen.app` and
  confirmed its container on the same UUID.
- Launched with `HANGTEN_REVIEW_BOARD_ID=nature.stone-hanger` and
  `HANGTEN_REVIEW_BOARD_DETAIL=1`.
- Visual review after first-launch initialization showed the Nature Climbing
  Stone Hanger detail, 105 × 105 × 35 mm copy, native oak/granite model, and
  the selected 15 mm incut highlight aligned to the top hold. No raster
  fallback or transient cord geometry was shown.
- The first screenshot at three seconds was blank while the first launch was
  still initializing. A second screenshot eight seconds later rendered the
  expected screen. This was transient initialization, not a retained blocker.
- Archive cleanup deleted the exact simulator UUID and removed
  `.context/DerivedData`, `.context/workout-raw.png`, and
  `.context/workout-landscape.png`; the final inventory contained no matching
  simulator or manifest entry.

## Boundaries

Nature's two observed lateral cord-port mouths remain nonselectable asset
metadata. The package intentionally declares no suspension because the hidden
route, cord length/radius, off-board anchor, and canonical poses are not
source-established. Tests assert the deterministic orthographic display camera
and explicit absence of suspension without duplicating Task 1 solver coverage
or inventing a Nature routine.

CoreSimulator access was initially blocked by the filesystem sandbox. The
approved CoreSimulator rerun succeeded. There is no unresolved infrastructure
blocker and no physical-device-only behavior in this test-only board-model
scope.
