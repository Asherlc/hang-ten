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
