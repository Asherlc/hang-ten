# Task 5: Granular Motherboard sample persistence

## RED

Command:

```sh
rtk proxy timeout 180s xcodebuild test -quiet -project HangTen.xcodeproj -scheme HangTen -destination 'platform=iOS Simulator,id=5BD0C30F-C006-43F1-9EFC-4B47B93EA488' -derivedDataPath .context/DerivedData-task5-red -parallel-testing-enabled NO -maximum-parallel-testing-workers 1 -only-testing:HangTenTests/MotherboardModelsTests -only-testing:HangTenTests/MotherboardProtocolTests -only-testing:HangTenTests/AppStoreTests
```

Result: expected compile failure, with `MotherboardProtocolTests.swift:59:31: error: value of type 'MotherboardMeasurement' has no member 'rawADCValues'`. XCTest did not run because the new raw-packet persistence contract was absent.

## GREEN

Implemented:

- `MotherboardMeasurement.rawADCValues` with an empty default and missing-key Codable fallback.
- Raw ADC propagation from `MotherboardProtocol.decode`.
- `WorkoutSessionRecord.motherboardMeasurements` with a missing-key Codable fallback.
- Per-notification `onReceive` capture while the routine is running after countdown, including rests; the existing threshold-based recorder path remains unchanged.
- A read-only granular sample-count cue that is omitted for records without samples.

Focused command:

```sh
rtk proxy timeout 180s xcodebuild test -quiet -project HangTen.xcodeproj -scheme HangTen -destination 'platform=iOS Simulator,id=5BD0C30F-C006-43F1-9EFC-4B47B93EA488' -derivedDataPath .context/DerivedData-task5-green -parallel-testing-enabled NO -maximum-parallel-testing-workers 1 -only-testing:HangTenTests/MotherboardModelsTests -only-testing:HangTenTests/MotherboardProtocolTests -only-testing:HangTenTests/WorkoutSummaryTests -only-testing:HangTenTests/AppStoreTests
```

Result: 30 passed, 0 failed, 0 skipped.

Recorder/session regressions:

```sh
rtk proxy timeout 180s xcodebuild test -quiet -project HangTen.xcodeproj -scheme HangTen -destination 'platform=iOS Simulator,id=5BD0C30F-C006-43F1-9EFC-4B47B93EA488' -derivedDataPath .context/DerivedData-task5-regression -parallel-testing-enabled NO -maximum-parallel-testing-workers 1 -only-testing:HangTenTests/MotherboardWorkoutRecorderTests -only-testing:HangTenTests/WorkoutSessionStoreTests
```

Result: 15 passed, 0 failed, 0 skipped.

Debug simulator build:

```sh
rtk proxy timeout 180s xcodebuild build -quiet -project HangTen.xcodeproj -scheme HangTen -configuration Debug -destination 'platform=iOS Simulator,id=5BD0C30F-C006-43F1-9EFC-4B47B93EA488' -derivedDataPath .context/DerivedData-task5-final-build
```

Result: exit 0; `HangTen.app` exists at the expected Debug simulator product path. The app installed and launched on the dedicated `HangTen sucre-v1 Final Review` simulator. Simulator screenshot capture returned a blank canvas and then stalled, so no visual runtime pass is claimed.

## Data-volume note

At 30 Hz, a ten-minute routine stores about 18,000 measurements. JSON persistence therefore adds several megabytes per session and can grow to tens of megabytes when the session history retains up to 20 records. This task deliberately preserves every running-routine notification rather than downsampling it.

The collector persists granular raw ADC measurements up to
`MotherboardWorkoutMeasurementCollector.maximumMeasurementCount` (20,000) per
session. Once full, additional measurements are dropped and
`WorkoutSessionRecord` records whether truncation occurred. Retention is also
bounded by the collector's routine-start/countdown/plan-duration eligibility
boundary and the store's 20-newest-session history limit.

## Review-fix RED

Added deterministic tests for an extracted granular-sample collector. The tests cover setup and paused state exclusion, countdown exclusion, active and rest interval inclusion, plan-duration exclusion, and preserving every eligible low- or high-load publication unchanged.

Command:

```sh
rtk proxy timeout 180s xcodebuild test -quiet -project HangTen.xcodeproj -scheme HangTen -destination 'platform=iOS Simulator,id=5BD0C30F-C006-43F1-9EFC-4B47B93EA488' -derivedDataPath .context/DerivedData-task5-review-red -parallel-testing-enabled NO -maximum-parallel-testing-workers 1 -only-testing:HangTenTests/MotherboardModelsTests
```

Result: expected compile failure. `MotherboardModelsTests.swift` could not find `MotherboardWorkoutMeasurementCollector` in scope; XCTest did not run because the new pure collector was intentionally absent.

## Review-fix GREEN

Implemented:

- Restored the prior `onChange(of: motherboardBluetoothService.latestMeasurement)` callback for `consume(_:)` without adding capture work to it.
- Added `MotherboardWorkoutMeasurementCollector`; its sole boundary is started routine, post-countdown, and before plan duration, and it appends each eligible `MotherboardMeasurement` unchanged.
- Kept `onReceive(motherboardBluetoothService.$latestMeasurement...)` solely for granular capture, including rest intervals.
- Stored the collector in `WorkoutView`, reset it at a fresh routine start, and persisted its measurements in the completed session as before.
- Left the threshold recorder and actual-time calculation unchanged.

Focused collector/recorder/model/protocol/summary/App Store command:

```sh
rtk proxy timeout 180s xcodebuild test -quiet -project HangTen.xcodeproj -scheme HangTen -destination 'platform=iOS Simulator,id=5BD0C30F-C006-43F1-9EFC-4B47B93EA488' -derivedDataPath .context/DerivedData-task5-review-focused -resultBundlePath .context/task5-review-focused.xcresult -parallel-testing-enabled NO -maximum-parallel-testing-workers 1 -only-testing:HangTenTests/MotherboardModelsTests -only-testing:HangTenTests/MotherboardWorkoutRecorderTests -only-testing:HangTenTests/MotherboardProtocolTests -only-testing:HangTenTests/WorkoutSummaryTests -only-testing:HangTenTests/AppStoreTests
```

Result: 45 passed, 0 failed, 0 skipped (`xcresulttool` summary).

Debug simulator build:

```sh
rtk proxy timeout 180s xcodebuild build -quiet -project HangTen.xcodeproj -scheme HangTen -configuration Debug -destination 'platform=iOS Simulator,id=5BD0C30F-C006-43F1-9EFC-4B47B93EA488' -derivedDataPath .context/DerivedData-task5-review-build CODE_SIGNING_ALLOWED=NO
rtk proxy test -d .context/DerivedData-task5-review-build/Build/Products/Debug-iphonesimulator/HangTen.app
```

Result: build exit 0 and the expected `HangTen.app` directory exists.

Concern: the existing data-volume note still applies. Xcode also emitted two non-fatal simulator metadata warnings about an empty build number; all selected tests and the Debug build completed successfully.
