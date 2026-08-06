# Task 1 implementation report

## Scope completed

Implemented the model and persistence follow-up work without modifying SwiftUI views, `RootView`, or `project.pbxproj`.

### Production changes

- `CustomRoutineStoring` now exposes `plan(for:)`; `AppStore.reloadCustomRoutines()` resolves definitions through its injected store instead of constructing a new `CustomRoutineStore`.
- `CustomRoutineStore.metadata(for:)` is the single custom `PlanMetadata` factory. Both custom-plan resolution and `AppStore` metadata lookup use it.
- New drafts create one private custom UUID at initialization. Repeated `definition()` calls and retargeting retain that ID, while existing routine drafts retain their persisted ID and existing-editor behavior.
- Draft rest rows now serialize as targetless, gripless fixed rest segments with the row duration. Non-rest single-step stopwatch and undefined timing behavior remains unchanged.
- `CustomRoutineTagNormalizer` is shared by draft conversion and store persistence. Metadata options cache their default catalog metadata and use a lexical secondary sort for case-insensitive ties.
- Store saves rely on the existing planning/flattening validation path, preserve validation errors, label the flattened local clearly, avoid writes for unknown deletes, and retain only the first valid persisted routine for duplicate IDs while keeping the load warning.
- Plan-library and custom-routine validation now require compound segments to be fixed, duration-bearing segments whose total equals the enclosing step duration. Plan-library errors identify the relevant timing or step-duration path.
- `WorkoutStepNormalizer` retains its direct compound guard for non-fixed/missing-duration segments and now reports an explicit mismatched-duration error before expansion.

## Changed files

### Production

- `HangTen/Models/AppStore.swift`
- `HangTen/Models/CustomRoutineDraft.swift`
- `HangTen/Models/CustomRoutineStore.swift`
- `HangTen/Models/PlanStorage.swift`
- `HangTen/Models/WorkoutStepNormalization.swift`

### Tests

- `HangTenTests/CustomRoutineAppStoreTests.swift`
- `HangTenTests/CustomRoutineDraftTests.swift`
- `HangTenTests/CustomRoutineStoreTests.swift`
- `HangTenTests/PlanStorageTests.swift`
- `HangTenTests/WorkoutStepNormalizationTests.swift`

One existing PlanStorage JSON fixture changed its enclosing duration from 10 to 20 seconds because its two fixed 10-second segments must now total the enclosing duration.

## TDD evidence

- Initial focused red run failed because the new `compoundDurationMismatch` and `mismatchedCompoundDuration` APIs did not yet exist.
- The no-op-delete regression test was run red against the prior persistence behavior, then green after restoring the early return.
- The path-aware non-fixed compound PlanStorage test was run red without the compound timing check, then green after restoring it.
- The first integrated focused run surfaced the stale 10-second compound fixture described above; it passed after its literal duration was corrected.

## Verification

- Focused XCTest suites: 72 tests, 0 failures.
  - `CustomRoutineDraftTests`
  - `CustomRoutineStoreTests`
  - `CustomRoutineAppStoreTests`
  - `PlanStorageTests`
  - `WorkoutStepNormalizationTests`
- Full XCTest suite: 380 tests, 0 failures.
- `git diff --check`: clean.

## Review follow-up: compound literal-duration guard

- `WorkoutStepNormalizer.expand` now rejects compound steps when either the enclosing duration or any fixed segment duration is negative or non-finite. The new `invalidCompoundDuration` error identifies the offending segment when applicable, or the enclosing step when no segment is at fault.
- Existing `unsupportedCompoundTiming` and `mismatchedCompoundDuration` behavior remains unchanged and is covered by the same focused suite.
- Added focused tests for a negative fixed segment whose durations still sum to the enclosing step, a non-finite fixed segment, and a non-finite enclosing duration produced by overflow from two finite segments.
- TDD result: the three new assertions failed before the guards; after the minimal guard addition, `WorkoutStepNormalizationTests` executed 8 tests with 0 failures.

## Concerns

No implementation concerns. Xcode emitted pre-existing simulator/runtime diagnostics (DVT build-number, IOSurface, and duplicate accessibility-loader class warnings); the complete test suite still succeeded.
