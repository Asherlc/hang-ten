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
- Added persisted `bodyweightCaptureDuration`, defaulting to 5 seconds when absent or non-finite and clamping every finite value inclusively to 3...10.
- Added optional `WorkoutSessionRecord.bodyweightKGF` with a defaulted initializer argument.
- Added custom session decoding with `decodeIfPresent` so records persisted before this field was introduced still decode unchanged. Computed measurement metrics are not Codable fields.

## Review follow-up fix evidence

### Requirements addressed

- `bodyweightCaptureDuration` now defaults only when the persisted value is absent or non-finite; finite `1` normalizes to `3`, and values above `10` normalize to `10`.
- Derived load sums saturate at `Double.greatestFiniteMagnitude`. Side shares use scale-normalized inputs, so their denominator cannot overflow. Bodyweight percentages return zero for invalid baselines and saturate at `Double.greatestFiniteMagnitude` for finite arithmetic overflow.

### RED

After adding focused regressions, reran:

```sh
rtk proxy xcodebuild test -quiet -project HangTen.xcodeproj -scheme HangTen -destination 'platform=iOS Simulator,id=5BD0C30F-C006-43F1-9EFC-4B47B93EA488' -derivedDataPath .context/DerivedData-bodyweight-green -parallel-testing-enabled NO -maximum-parallel-testing-workers 1 -only-testing:HangTenTests/MotherboardModelsTests -only-testing:HangTenTests/AppStoreTests
```

Result: intentional RED, exit 65. The duration test failed because finite `1` normalized to `5`; finite-overflow regressions failed because side sums and bodyweight percentage became infinity.

### GREEN

Reran the same focused command after the fix.

Result: PASS, exit 0. `MotherboardModelsTests` and `AppStoreTests` completed successfully. The output contained only the existing simulator build-number warnings.
