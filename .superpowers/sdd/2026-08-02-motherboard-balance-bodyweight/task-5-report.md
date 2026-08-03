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
