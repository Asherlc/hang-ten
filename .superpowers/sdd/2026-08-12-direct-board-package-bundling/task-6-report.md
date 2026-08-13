# Task 6: Remove duplicate board delivery artifacts and route plans through package semantics

## Status

Complete and pushed to `origin/audit-hangboard-image-source-of-truth`.

Commit: `df70ada` (`refactor: consume bundled board packages directly`)

## Delivered

- Removed the generated board catalog, legacy board-library resource, both
  handwritten board-design files, and both obsolete Compact Board imagesets.
- Removed every corresponding PBX file, source-build, and resource-build
  reference while preserving the generic asset catalog.
- Removed the disabled handwritten board geometry and all temporary
  `BoardCatalog` board-specific convenience aliases.
- Changed `AppStore` and the generic custom-routine editor path to use
  `BoardCatalog.defaultBoard`.
- Changed exact seed-plan board/hold selection to resolve package semantics at
  runtime, including deterministic indexed selection for the two one-hand
  targets whose persisted plan representation remains board-specific.
- Changed `BuiltInPlanLibraryDefinition` to construct mappings for every
  approved runtime board from `BoardPackageStore.semantics(for:)` rather than
  handwritten board/hold dictionaries.
- Updated the plan exporter to stage approved package resources into its
  isolated `.context` build directory and compile against the package decoder.
  The canonical `PlanLibrary.json` remains byte-for-byte unchanged.
- Added source-boundary coverage for the exact approved board IDs, plan target
  resolution, removed legacy artifacts/Xcode references, and package-owned
  board/hold IDs in handwritten app Swift.

## TDD evidence

The initial selected run failed for the intended legacy boundary only:

```sh
xcodebuild test -project HangTen.xcodeproj -scheme HangTen \
  -destination 'platform=iOS Simulator,name=iPhone 17 Pro' \
  -only-testing:HangTenTests/BoardSourceBoundaryTests \
  -only-testing:HangTenTests/PlanStorageTests
# ** TEST FAILED **
# BoardSourceBoundaryTests.testHandwrittenAppSourcesDoNotContainPackageBoardOrHoldIDs()
# BoardSourceBoundaryTests.testLegacyBoardDeliveryArtifactsAreAbsent() (six artifact assertions)
```

The semantic-mapping and plan-resolution assertions compiled and exercised the
real bundled package store; the failures were the expected checked-in duplicate
sources and assets.

## Final verification

```sh
scripts/export-plan-library.sh --check
# Exported 20 plans
# PlanLibrary.json matches the source-audited definitions

xcodebuild test -project HangTen.xcodeproj -scheme HangTen \
  -destination 'platform=iOS Simulator,name=iPhone 17 Pro' \
  -only-testing:HangTenTests/BoardSourceBoundaryTests \
  -only-testing:HangTenTests/BoardPackageStoreTests \
  -only-testing:HangTenTests/PlanStorageTests \
  -only-testing:HangTenTests/BoardStorageTests
# exit 0; ** TEST SUCCEEDED **

xcodebuild build -project HangTen.xcodeproj -scheme HangTen \
  -destination 'generic/platform=iOS Simulator'
# ** BUILD SUCCEEDED **

git diff --check
# exit 0

plutil -lint HangTen.xcodeproj/project.pbxproj
# HangTen.xcodeproj/project.pbxproj: OK
```

Xcode emitted its pre-existing empty device-build-number diagnostic and the
App Intents metadata-skip warning; neither affected the passing tests or build.

## Scope and concerns

- No training-plan source text, counts, durations, grip/finger cues, package
  metadata, package artwork, Workbench files, CI configuration, or Task 7 docs
  were changed.
- `PlanLibrary.json` did not change. Its existing persisted mappings are now
  regenerated from approved package semantics, preserving all plan behavior.
- The legacy board import/export tools remain outside the active app delivery
  path and were not changed in this task.

## Review-finding fix — 2026-08-12

### Status

Complete. The bundled `PlanLibrary.json` is no longer an active semantic
authority, and the tracked handwritten app boundary audit now covers board
metadata, mappings, presentation assets, and concrete geometry.

### Delivered

- Added a package-backed built-in plan-library load path. It preserves the
  decoded plan metadata, blocks, plans, and canonical JSON bytes, but replaces
  every embedded board mapping with mappings decoded by
  `BoardPackageStore.semantics(for:)` before validation or resolution.
- Removed plan-mapping precedence from generic validation and target
  resolution. Board-owned semantic mappings are now authoritative; persisted
  plan mappings are independently validated only as compatibility data and
  cannot mask invalid board semantics or alter a resolved target.
- Added a regression fixture whose plan mapping points at a different valid
  physical hold. The built-in loader replaces the divergent mapping, retains
  exactly the package boards, and resolves the package-owned hold IDs.
- Strengthened `BoardSourceBoundaryTests` to scan tracked app sources,
  resources, and the Xcode project for legacy artifact tokens (including
  `CompactBoardIllustration`), package board/hold/artwork/asset identifiers,
  hardcoded semantic/asset maps, and concrete board geometry constructors.
- Added explicit, justified exclusions for package authority, tests, generated
  `PlanLibrary.json`, generated/build workspace paths, and historical docs;
  generic package/storage/renderer geometry types remain allowed.

### TDD evidence

The first RED run failed because the plan mapping masked a board-owned invalid
mapping and resolved the plan-owned jug instead of the board-owned edge:

```sh
xcodebuild test -project HangTen.xcodeproj -scheme HangTen \
  -destination 'platform=iOS Simulator,name=iPhone 17 Pro' \
  -only-testing:HangTenTests/PlanStorageTests/testBoardSemanticMappingsRemainAuthoritativeDuringValidation \
  -only-testing:HangTenTests/PlanStorageTests/testBoardLoadedSemanticMappingsCannotBeOverriddenByPlanMappings
# ** TEST FAILED **; both regression tests failed for the intended precedence bug
```

After removing plan precedence, both tests passed. The built-in divergent-data
test then failed to compile because the package-backed initializer did not yet
exist; after adding the initializer and routing runtime load through it, the
test passed.

### Final verification

```sh
scripts/export-plan-library.sh --check
# Exported 20 plans; PlanLibrary.json matches the source-audited definitions

xcodebuild test -project HangTen.xcodeproj -scheme HangTen \
  -destination 'platform=iOS Simulator,name=iPhone 17 Pro' \
  -only-testing:HangTenTests/BoardSourceBoundaryTests \
  -only-testing:HangTenTests/BoardPackageStoreTests \
  -only-testing:HangTenTests/PlanStorageTests \
  -only-testing:HangTenTests/BoardStorageTests
# exit 0; ** TEST SUCCEEDED **

xcodebuild build -project HangTen.xcodeproj -scheme HangTen \
  -destination 'generic/platform=iOS Simulator'
# exit 0; ** BUILD SUCCEEDED **

git diff --check
# exit 0

plutil -lint HangTen.xcodeproj/project.pbxproj
# HangTen.xcodeproj/project.pbxproj: OK
```

Xcode emitted its pre-existing empty device-build-number diagnostic and App
Intents metadata-skip warning; neither affected the passing tests or build.

### Scope and concerns

- `HangTen/Resources/PlanLibrary.json` remains byte-for-byte unchanged.
- No training-plan content, package metadata/artwork, Workbench/CI/docs Task 7
  work, or legacy board import/export tooling changed.
- Full manual visual/runtime validation was not repeated because this fix
  changes semantic authority and source auditing without changing board data,
  geometry, rendering, routine content, or runtime service behavior. Focused
  simulator tests exercise actual package decode and target resolution.

## Boundary-audit follow-up — 2026-08-12

### Status

Complete and pushed to `origin/audit-hangboard-image-source-of-truth`.

Commit: `fbb7a7c` (`test: restrict board boundary audit to tracked files`)

### Delivered

- Replaced working-tree enumeration in `BoardSourceBoundaryTests` with the
  exact candidate set from `git ls-files -- HangTen
  HangTen.xcodeproj/project.pbxproj`. The checked-in list is necessary because
  this iOS simulator test target cannot launch `git` at runtime.
- Preserved every currently tracked handwritten app source, resource, asset
  child, entitlement, and project file before existing exclusions are applied.
- Added a regression that writes an untracked Swift scratch file containing a
  prohibited legacy-artifact token, confirms it is ignored, and confirms a
  tracked app source remains a boundary-audit candidate.

### Verification

```sh
git ls-files -- HangTen HangTen.xcodeproj/project.pbxproj
# 58 paths; matches the boundary-audit candidate manifest

xcodebuild test -project HangTen.xcodeproj -scheme HangTen \
  -destination 'platform=iOS Simulator,id=51BF665F-2E2B-45AE-B3F0-43B81676E576' \
  -only-testing:HangTenTests/BoardSourceBoundaryTests
# focused simulator run completed successfully

git diff --check
# exit 0
```

## Boundary-manifest completeness follow-up — 2026-08-12

### Delivered

- Moved the simulator boundary audit's candidate paths to
  `HangTenTests/BoardSourceBoundaryTrackedPaths.txt`.
- Added a `HangTenTests` build phase that runs
  `scripts/verify-board-source-boundary-manifest.sh`, requiring that manifest
  to exactly equal `git ls-files -- HangTen HangTen.xcodeproj/project.pbxproj`
  before the boundary tests execute. This prevents a future tracked app source
  or resource from silently escaping the audit, while the test target itself
  remains unable to launch Git from the simulator.
- Preserved the explicit exclusions and the regression proving that an
  untracked scratch Swift file containing a prohibited token is ignored.

### Verification

```sh
# Removing a tracked path from the manifest produced the intended failure:
error: BoardSourceBoundaryTrackedPaths.txt must exactly match git ls-files -- HangTen HangTen.xcodeproj/project.pbxproj.

xcodebuild test -project HangTen.xcodeproj -scheme HangTen \
  -destination 'platform=iOS Simulator,id=51BF665F-2E2B-45AE-B3F0-43B81676E576' \
  -only-testing:HangTenTests/BoardSourceBoundaryTests
# exit 0; focused simulator boundary test passed
```
