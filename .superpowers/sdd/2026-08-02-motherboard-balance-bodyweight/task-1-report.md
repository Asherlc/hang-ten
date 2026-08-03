# Task 1 implementation and test evidence

## Scope

Implemented only the Task 1 model/settings work. Changed:

- `HangTen/Models/MotherboardModels.swift`
- `HangTenTests/MotherboardModelsTests.swift`
- This report

`HangTenTests/AppStoreTests.swift` and all Bluetooth, recorder, UI, and project files were left unchanged.

## TDD evidence

### RED

Added tests first for side distribution, bodyweight percentage, duration defaults/normalization/persistence, and decoding a legacy session record without `bodyweightKGF`.

Command:

```sh
rtk proxy xcodebuild test -quiet -project HangTen.xcodeproj -scheme HangTen -destination 'platform=iOS Simulator,id=5BD0C30F-C006-43F1-9EFC-4B47B93EA488' -derivedDataPath .context/DerivedData-bodyweight-red -parallel-testing-enabled NO -maximum-parallel-testing-workers 1 -only-testing:HangTenTests/MotherboardModelsTests -only-testing:HangTenTests/AppStoreTests
```

Result: intentional RED, exit 65. Compilation failed because the new `leftLoadKGF`, `rightLoadKGF`, `leftShare`, `rightShare`, `bodyweightPercentage(for:)`, `bodyweightCaptureDuration`, and `bodyweightKGF` symbols did not yet exist.

### GREEN

Command:

```sh
rtk proxy xcodebuild test -quiet -project HangTen.xcodeproj -scheme HangTen -destination 'platform=iOS Simulator,id=5BD0C30F-C006-43F1-9EFC-4B47B93EA488' -derivedDataPath .context/DerivedData-bodyweight-green -parallel-testing-enabled NO -maximum-parallel-testing-workers 1 -only-testing:HangTenTests/MotherboardModelsTests -only-testing:HangTenTests/AppStoreTests
```

Result: PASS, exit 0. The focused Motherboard model and AppStore test selections completed successfully. Xcode emitted only pre-existing simulator build-number warnings.

## Implementation

- Added one isolated side mapping helper: channels 0 and 2 are left; channels 1 and 3 are right.
- Added finite-safe, non-negative side loads and zero-safe left/right shares.
- Added aggregate-load bodyweight percentage as a computed, non-persisted metric.
- Added persisted `bodyweightCaptureDuration`, defaulting to 5 seconds; finite values below 3 use the default and values above 10 clamp to 10.
- Added optional `WorkoutSessionRecord.bodyweightKGF` with a defaulted initializer argument.
- Added custom session decoding with `decodeIfPresent` so records persisted before this field was introduced still decode unchanged. Computed measurement metrics are not Codable fields.
