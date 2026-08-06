# Task 2 Report

## Changed files

- `HangTen/Models/CustomRoutineDraft.swift`
  - Made `init(duplicate:)` create an unsaved draft with a fresh, stable `custom.<UUID>` definition ID.
  - Added `init(editing:)` for persisted definitions; it retains the saved ID and consequently keeps target-mode editing locked.
- `HangTen/Views/CustomRoutineEditorView.swift`
  - Added local duration validation for zero, negative, infinite, and NaN values before persistence, using the existing inline validation presentation.
  - Rest phase selection now clears target/grip data and forces fixed timing; rest rows show fixed timing while non-rest rows keep the timing picker.
  - Added `customRoutine.stepTarget` to the generic target picker.
- `HangTen/Views/RootView.swift`
  - Partitioned `myRoutines` directly from `filteredPlans` using the custom ID set.
  - Added `customRoutine.create` and `customRoutine.actions` accessibility identifiers.
  - The detail view resolves `currentPlan` from the store by ID, with the original plan as fallback, for displayed metadata, board preview, source, session flow, and workout navigation.
  - Kept duplicate behavior as an unsaved creation draft and changed edit behavior to the persisted-ID draft initializer.
- `HangTenTests/CustomRoutineDraftTests.swift`
  - Updated retained-ID round-trip expectations to use `editing:`.
  - Added coverage for duplicate identity/stability, edit identity/target locking, and non-positive/non-finite local duration validation.
- `HangTenTests/CustomRoutineStoreTests.swift`
  - Updated the persisted round-trip assertion to use `editing:`.

## Test evidence

Red phase:

- `xcodebuild test -project HangTen.xcodeproj -scheme HangTen -destination 'platform=iOS Simulator,name=iPhone 16 Pro' -only-testing:HangTenTests/CustomRoutineDraftTests`
  - Failed as expected because `CustomRoutineDraft(editing:)` did not yet exist.
- `xcodebuild test -project HangTen.xcodeproj -scheme HangTen -destination 'platform=iOS Simulator,name=iPhone 16 Pro' -only-testing:HangTenTests/CustomRoutineDraftTests/testEditorLocalValidationRejectsNonFiniteAndNonPositiveStepDurations`
  - Failed as expected because editor local validation was private instance-only and did not expose the requested duration contract.

Green phase:

- Focused tests: `CustomRoutineDraftTests`, `CustomRoutineStoreTests`, and existing `CustomRoutineAppStoreTests` passed (exit status 0).
- Full suite: `xcodebuild test -project HangTen.xcodeproj -scheme HangTen -destination 'platform=iOS Simulator,name=iPhone 16 Pro'` passed (exit status 0).
- `git diff --check` passed.

## Concerns

- Xcode emitted `DVTDeviceOperation: Encountered a build number "" that is incompatible with DVTBuildVersion` during test invocations. Tests still completed with exit status 0; no task code changes were made for this environment diagnostic.
- No persistence model files beyond `CustomRoutineDraft` and no project-file or `CustomRoutineAppStoreTests` changes were made.
