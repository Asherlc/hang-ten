# Post-review follow-up fix report

## Status

DONE

Implemented the complete scoped follow-up in `post-review-fix-brief.md` while preserving the existing Motherboard protocol, timeout, calibration, parser, lazy-central-manager, and recorder boundary fixes.

## Changes implemented

### Bluetooth power recovery

- Track the last Core Bluetooth power state in `MotherboardBluetoothService`.
- Recover `.bluetoothUnavailable` to `.idle` when `.poweredOn` follows `.poweredOff`, `.unknown`, or `.resetting`.
- Do not scan automatically on recovery; a new explicit `connect()` starts the next scan.
- Preserve `.unauthorized` across later power-state notifications.
- Added a regression that verifies the exact fake-transport scan count and operation sequence through powered-off, powered-on, and explicit reconnect.

### Persisted sensor interruptions

- Changed the actual `WorkoutView` streaming-to-non-streaming observer to call `MotherboardWorkoutRecorder.interrupt(at:)` instead of `pause(at:)`.
- Kept timer pauses, scene interruption, step transitions, rest transitions, manual end, and completion on their existing pause/flush paths.
- Did not use the one-shot view-dismiss interruption flag for sensor state changes, so reconnecting and then losing the stream again can interrupt a later step.
- Resolve the active step from the workout clock when the stream is lost, allowing interruption to be persisted even when that step has not received its first sensor sample.
- Added recorder regressions proving both the no-first-sample case and two separate active steps across an intervening resumed measurement.

### Reviewable session history and discard behavior

- Added a compact Session history card to Progress, backed directly by `AppStore.sessionHistory`.
- Added a saved-session list and read-only detail destination.
- Reused the existing summary content while omitting Save and Discard actions for historical records; the read-only path has no store-mutating callbacks.
- Added an explicit, tested summary mode so the history path remains read-only independently of callback wiring.
- Updated active-workout Discard to clear both the summary and pending completed session, stop the workout/audio, and dismiss the workout, preventing the discarded summary from being reopened.

### Asynchronous windowed tare

- Replaced single-sample tare capture with an asynchronous, bounded measurement window on the existing `@MainActor` service.
- The default window is 15 raw measurements and is configurable for focused tests.
- Average each of the four decoded sensor-load channels and add the averaged residual vector to the current tare baseline.
- Publish `isTaring`, collected-sample count, and target count for UI feedback.
- Relabel and disable the Tare button while collection is active.
- Cancel and clear pending tare accumulation on disconnect or any session reset.
- Added regressions proving the averaged window is used and no pending state survives disconnect.

### Notification cleanup

- Track the requested TX notification state in `CoreBluetoothMotherboardTransport`.
- Treat a successful notification-disable callback as intentional cleanup without emitting a disconnect failure.
- Continue reporting enable failures, callback errors, and unexpected notification-state mismatches.

## Test-first evidence

The new service and recorder regressions were added before the production changes. The first focused run failed as expected because the service did not yet accept `tareSampleCount` and the transport did not yet expose the notification-state handling seam. Production and UI changes were then applied, followed by the focused green run.

## Verification

All commands were bounded where a simulator operation could stall and used the explicit dedicated simulator UUID `5BD0C30F-C006-43F1-9EFC-4B47B93EA488`.

### Focused service, recorder, and summary tests

Command:

```sh
rtk perl -e 'alarm 180; exec @ARGV' xcodebuild test \
  -project HangTen.xcodeproj -scheme HangTen \
  -destination 'platform=iOS Simulator,id=5BD0C30F-C006-43F1-9EFC-4B47B93EA488' \
  -parallel-testing-enabled NO -maximum-parallel-testing-workers 1 \
  -derivedDataPath .context/DerivedData-post-review-fixes-shared \
  -only-testing:HangTenTests/MotherboardBluetoothServiceTests \
  -only-testing:HangTenTests/MotherboardWorkoutRecorderTests \
  -only-testing:HangTenTests/WorkoutSummaryTests
```

Result: **PASS** — 35 tests executed, 0 failures, `** TEST SUCCEEDED **`.

An immediately preceding integration run executed the same 35 tests and reported two assertion failures in the notification regression because it expected the fallback string even though a supplied `Error` correctly takes precedence. The assertion was corrected to verify that the real error remains visible without depending on its synthesized localized text; no production behavior was weakened.

### Complete HangTen XCTest suite

Command:

```sh
rtk perl -e 'alarm 300; exec @ARGV' xcodebuild test \
  -project HangTen.xcodeproj -scheme HangTen \
  -destination 'platform=iOS Simulator,id=5BD0C30F-C006-43F1-9EFC-4B47B93EA488' \
  -parallel-testing-enabled NO -maximum-parallel-testing-workers 1 \
  -derivedDataPath .context/DerivedData-post-review-fixes-shared
```

Result: **PASS** — 59 tests executed, 0 failures, `** TEST SUCCEEDED **`.

Result bundle:

`.context/DerivedData-post-review-fixes-shared/Logs/Test/Test-HangTen-2026.08.02_12-09-40--0700.xcresult`

### Debug simulator build

Command:

```sh
rtk perl -e 'alarm 300; exec @ARGV' xcodebuild build \
  -project HangTen.xcodeproj -scheme HangTen -configuration Debug \
  -destination 'platform=iOS Simulator,id=5BD0C30F-C006-43F1-9EFC-4B47B93EA488' \
  -derivedDataPath .context/DerivedData-post-review-fixes-shared
```

Result: **PASS** — signed simulator application built successfully, `** BUILD SUCCEEDED **`. The generated simulator entitlement included HealthKit. Xcode emitted its existing empty-device-build-number warning, which did not affect the successful build or tests.

### Static checks

- `rtk git diff --check`: **PASS** (no whitespace errors).
- No physical-hardware or Bluetooth-radio validation was attempted, as scoped.
- No UI redesign, physical-device testing, or unrelated documentation/plan changes were made.

## Files changed

- `HangTen/Models/MotherboardBluetoothService.swift`
- `HangTen/Models/MotherboardWorkoutRecorder.swift`
- `HangTen/Views/MotherboardViews.swift`
- `HangTen/Views/RootView.swift`
- `HangTen/Views/WorkoutSummaryView.swift`
- `HangTenTests/MotherboardBluetoothServiceTests.swift`
- `HangTenTests/MotherboardWorkoutRecorderTests.swift`
- `HangTenTests/WorkoutSummaryTests.swift`
- `.superpowers/sdd/2026-08-02-motherboard-bluetooth/post-review-fix-report.md`
