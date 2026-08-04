# Task 2 implementation and test evidence

## Scope

Implemented only the Task 2 Bluetooth-service bodyweight capture work. Changed:

- `HangTen/Models/MotherboardBluetoothService.swift`
- `HangTenTests/MotherboardBluetoothServiceTests.swift`
- This report

## TDD evidence

### RED

Added focused `@MainActor` service tests first for a timed 8/10/12 kgf average,
rejection while disconnected, disconnect cancellation, and baseline replacement.

Command:

```sh
rtk proxy xcodebuild test -quiet -project HangTen.xcodeproj -scheme HangTen -destination 'platform=iOS Simulator,id=5BD0C30F-C006-43F1-9EFC-4B47B93EA488' -derivedDataPath .context/DerivedData-bodyweight-red -parallel-testing-enabled NO -maximum-parallel-testing-workers 1 -only-testing:HangTenTests/MotherboardBluetoothServiceTests
```

Result: intentional RED, exit 65. Compilation failed because
`MotherboardBluetoothService` did not yet provide
`beginBodyweightMeasurement`, `bodyweightKGF`, or the published capture-state
properties.

### GREEN

Command:

```sh
rtk proxy xcodebuild test -quiet -project HangTen.xcodeproj -scheme HangTen -destination 'platform=iOS Simulator,id=5BD0C30F-C006-43F1-9EFC-4B47B93EA488' -derivedDataPath .context/DerivedData-bodyweight-green -parallel-testing-enabled NO -maximum-parallel-testing-workers 1 -only-testing:HangTenTests/MotherboardBluetoothServiceTests
```

Result: PASS, exit 0. The restricted service suite completed successfully with
the existing connection, timeout, reconnect, and tare tests. Xcode emitted only
the existing simulator build-number warnings.

## Implementation

- Added published baseline and capture-state properties plus
  `beginBodyweightMeasurement(duration:)`.
- Timed capture collects only finite aggregate raw-measurement loads and
  publishes their average at completion.
- Capture uses its own cancellable task and sample storage, independent from
  the existing 15-sample tare window.
- Session cleanup/reset cancels active capture, clears capture state, and
  clears the session baseline. A later successful capture replaces a prior
  baseline.

## Review-fix evidence

### RED

Replaced the capture tests' fixed wall-clock sleeps with a manual async sleep
gate and added focused coverage for invalid/huge durations, non-finite and
extreme finite samples, concurrent tare/bodyweight capture, stop-streaming
cleanup, disconnect/reconnect cleanup, fresh-connect reset, and baseline
replacement.

Command:

```sh
rtk proxy xcodebuild test -quiet -project HangTen.xcodeproj -scheme HangTen -destination 'platform=iOS Simulator,id=5BD0C30F-C006-43F1-9EFC-4B47B93EA488' -derivedDataPath .context/DerivedData-task-2-review-red -parallel-testing-enabled NO -maximum-parallel-testing-workers 1 -only-testing:HangTenTests/MotherboardBluetoothServiceTests
```

Result: intentional RED, exit 65. The new tests failed to compile with
`extra argument 'bodyweightMeasurementSleep' in call`, proving the tests
required an injectable capture sleeper that the service did not yet expose.

### GREEN

Added a narrowly scoped initializer injection with the existing `Task.sleep`
behavior as its production default. The service now rejects non-positive and
non-finite durations before conversion, caps finite duration before converting
to nanoseconds, and uses a guarded weighted running mean so finite extreme
samples cannot make the published baseline non-finite.

Command:

```sh
rtk proxy xcodebuild test -quiet -project HangTen.xcodeproj -scheme HangTen -destination 'platform=iOS Simulator,id=5BD0C30F-C006-43F1-9EFC-4B47B93EA488' -derivedDataPath .context/DerivedData-task-2-review-green -parallel-testing-enabled NO -maximum-parallel-testing-workers 1 -only-testing:HangTenTests/MotherboardBluetoothServiceTests
```

Result: PASS, exit 0. The focused suite completed with only the existing
simulator build-number warnings.

### Final review fixes

- Replaced the fragile exact `Double`-to-`UInt64` conversion assertion in
  `testBodyweightMeasurementRejectsInvalidDurationsAndCapsHugeFiniteDuration`
  with a behavioral check that the injected sleeper receives one positive,
  representable nanosecond duration.
- Added `testExplicitDisconnectCancelsBodyweightMeasurementAndClearsBaseline`.
  It seeds a baseline, starts another capture, calls the public
  `service.disconnect()`, and verifies the active flag, start time, samples,
  and baseline are cleared. The unexpected transport disconnect/reconnect test
  remains in place.
- Corrected the non-finite aggregate fixture to use finite maximum calibration
  values for all sensors. The protocol parser intentionally rejects `nan`
  calibration rows; the revised fixture reaches the service's non-finite sample
  guard by producing an infinite aggregate from valid finite inputs.

Command:

```sh
rtk proxy xcodebuild test -project HangTen.xcodeproj -scheme HangTen -destination 'platform=iOS Simulator,id=5BD0C30F-C006-43F1-9EFC-4B47B93EA488' -derivedDataPath .context/DerivedData-task-2-review-final -parallel-testing-enabled NO -maximum-parallel-testing-workers 1 -only-testing:HangTenTests/MotherboardBluetoothServiceTests
```

Result: PASS, exit 0. `MotherboardBluetoothServiceTests` executed 35 tests
with 0 failures (0 unexpected) in 0.221 seconds. Xcode emitted only the
existing simulator build-number warnings.
