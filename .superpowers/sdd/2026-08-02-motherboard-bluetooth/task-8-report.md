# Task 8 report — live workout integration and summary

## Status

DONE

## Implementation

- Added `WorkoutSummaryView`, with per-step planned/actual loaded time, multi-interval detail, peak force in the selected unit, measurement status, and explicit Save/Discard actions.
- Wired `WorkoutView` to the shared Motherboard service. Measurements are consumed only while the workout is running past its countdown, before routine completion, and outside rest intervals. The recorder uses each sample timestamp through the existing elapsed-time mapping.
- Completion finalizes a `WorkoutSessionRecord` and presents the summary. Only the summary Save calls `AppStore.markSessionComplete`; Discard just closes the summary. An unfinished recorder is interrupted on view disappearance.
- Added the live meter to portrait and landscape layouts, including the selected force unit, loaded/planned active time, no-measurement text, and compact connection state.
- Exposed the selected Bluetooth identifier for session records and added live loaded-duration tracking to the recorder.

## Exact files

- `HangTen/Views/WorkoutSummaryView.swift` (new)
- `HangTen/Views/RootView.swift`
- `HangTen/Views/MotherboardViews.swift`
- `HangTen/Models/MotherboardBluetoothService.swift`
- `HangTen/Models/MotherboardWorkoutRecorder.swift`
- `HangTenTests/WorkoutSummaryTests.swift` (new)
- `HangTen.xcodeproj/project.pbxproj`

## TDD evidence

- Added `WorkoutSummaryTests.testSummaryUsesActualLoadedDurationAndPeakInSelectedUnit` before summary-view production code.
- RED exception: the brief expected a compile failure for `actualLoadedDuration`, but Task 4 had already implemented that property in `MotherboardModels.swift`. The newly added focused test therefore compiled and passed immediately; removing the existing property would have regressed Task 4.
- GREEN: focused summary test passed (1 test, 0 failures).
- GREEN: full XCTest passed (35 tests, 0 failures).

## Verification

- `rtk xcodebuild build-for-testing -project HangTen.xcodeproj -scheme HangTen -destination 'platform=iOS Simulator,name=iPhone 17 Pro'` — `TEST BUILD SUCCEEDED`.
- `rtk xcodebuild build -project HangTen.xcodeproj -scheme HangTen -configuration Debug -destination 'platform=iOS Simulator,id=D5CDA3E4-6EE5-48E0-9AD2-66C10D00F536' -derivedDataPath .context/DerivedData-task8` — `BUILD SUCCEEDED`.
- `rtk xcodebuild test -project HangTen.xcodeproj -scheme HangTen -destination 'platform=iOS Simulator,name=iPhone 17 Pro'` — 35 tests, 0 failures.
- `rtk git diff --check` — clean before commit.

## Limitations

- A dedicated `HangTen sucre-v1 Task8 20260802` simulator was created, but its boot-status command was deliberately bounded to 40 seconds and expired during LaunchServices migration. No install, launch, screenshot, sensor-hardware, or HealthKit runtime validation was attempted after that bound.
- No Task 9 work was started.

## Commits

- `ec8ef62 feat: show actual Motherboard load in workouts`
