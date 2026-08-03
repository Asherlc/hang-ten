# Task 3 implementation and test evidence

## Scope

Implemented the sensor-backed workout preparation sequence in the owned Task 3
files:

- `HangTen/Models/MotherboardWorkoutPreparation.swift`
- `HangTen/Views/MotherboardWorkoutPreparationView.swift`
- `HangTen/Views/RootView.swift`
- `HangTen.xcodeproj/project.pbxproj`
- `HangTenTests/MotherboardWorkoutPreparationTests.swift`
- This report

## TDD evidence

### RED

Added pure, deterministic preparation tests for tare-to-bodyweight-to-ready
transitions, skip clearing the baseline, and initial-streaming start gating.

Command:

```sh
rtk proxy xcodebuild test -quiet -project HangTen.xcodeproj -scheme HangTen -destination 'platform=iOS Simulator,id=5BD0C30F-C006-43F1-9EFC-4B47B93EA488' -derivedDataPath .context/DerivedData-preparation-red -parallel-testing-enabled NO -maximum-parallel-testing-workers 1 -only-testing:HangTenTests/MotherboardWorkoutPreparationTests
```

Result: intentional RED, exit 65. Compilation failed because
`MotherboardWorkoutPreparation` and its required steps/results did not yet
exist.

### GREEN

Command:

```sh
rtk proxy xcodebuild test -quiet -project HangTen.xcodeproj -scheme HangTen -destination 'platform=iOS Simulator,id=5BD0C30F-C006-43F1-9EFC-4B47B93EA488' -derivedDataPath .context/DerivedData-preparation-green -parallel-testing-enabled NO -maximum-parallel-testing-workers 1 -only-testing:HangTenTests/MotherboardWorkoutPreparationTests
```

Result: PASS, exit 0. All 3 preparation transition tests completed. Xcode
emitted only its existing simulator build-number warnings.

## Implementation

- Added a pure preparation state that advances tare → bodyweight → ready,
  keeps only a finite positive captured baseline, supports retry, and clears
  the baseline on skip.
- Added a non-dismissable sheet that tars the unloaded board, then starts the
  configured timed bodyweight capture only after tare completes. It displays
  progress, countdown, samples, captured-baseline confirmation, retry, skip,
  and continue actions.
- Initial streaming starts are gated by the sheet. Sensorless starts and
  resumed workouts start directly; completing or skipping setup then enters the
  existing three-second countdown. DEBUG autostart marks setup complete before
  calling `toggleRunning`.
- RootView stores the accepted baseline only for the active workout and saves
  it in `WorkoutSessionRecord`. The existing meter has no baseline input, so
  its display wiring remains intentionally deferred to Task 4.
- Recorder timing and sensor-loss interruption code were not changed.

## Final verification

Focused preparation plus recorder test command:

```sh
rtk proxy xcodebuild test -quiet -project HangTen.xcodeproj -scheme HangTen -destination 'platform=iOS Simulator,id=5BD0C30F-C006-43F1-9EFC-4B47B93EA488' -derivedDataPath .context/DerivedData-preparation-integration -parallel-testing-enabled NO -maximum-parallel-testing-workers 1 -only-testing:HangTenTests/MotherboardWorkoutPreparationTests -only-testing:HangTenTests/MotherboardWorkoutRecorderTests
```

Result: PASS, exit 0. The focused suites cover 13 tests (3 preparation and 10
recorder), with only the existing simulator build-number warnings.

Debug simulator build command:

```sh
rtk proxy xcodebuild -quiet -project HangTen.xcodeproj -scheme HangTen -configuration Debug -destination 'platform=iOS Simulator,id=5BD0C30F-C006-43F1-9EFC-4B47B93EA488' -derivedDataPath .context/DerivedData-preparation-build build
```

Result: PASS, exit 0. Xcode emitted only the existing simulator build-number
warnings.

## Latest review-fix lifecycle evidence

### RED

Added deterministic regression coverage for a ready capture invalidated by
stream loss, an empty second capture after a valid baseline, and cancellation
of tare/bodyweight work while the sensor keeps streaming.

Preparation RED command:

```sh
rtk proxy timeout 180s xcodebuild test -quiet -project HangTen.xcodeproj -scheme HangTen -destination 'platform=iOS Simulator,id=5BD0C30F-C006-43F1-9EFC-4B47B93EA488' -derivedDataPath .context/DerivedData-task-3-lifecycle-red -parallel-testing-enabled NO -maximum-parallel-testing-workers 1 -only-testing:HangTenTests/MotherboardWorkoutPreparationTests
```

Result: intentional RED, exit 65. The new test failed to compile because
`invalidateForStreamingLoss()` and streaming-aware `canContinue` did not yet
exist.

Service RED command:

```sh
rtk proxy timeout 180s xcodebuild test -quiet -project HangTen.xcodeproj -scheme HangTen -destination 'platform=iOS Simulator,id=5BD0C30F-C006-43F1-9EFC-4B47B93EA488' -derivedDataPath .context/DerivedData-task-3-lifecycle-service-red -parallel-testing-enabled NO -maximum-parallel-testing-workers 1 -only-testing:HangTenTests/MotherboardBluetoothServiceTests
```

Result: intentional RED, exit 65. Compilation failed because the preparation
view called the not-yet-existing `cancelPreparationMeasurements()` service API.

### GREEN

- A state loss now converts a ready capture back to bodyweight/retry,
  clears its baseline, and prevents Continue unless the service remains
  streaming.
- Beginning a capture clears `bodyweightKGF`; completion assigns the sampled
  mean directly, including `nil` for zero valid samples.
- `cancelPreparationMeasurements()` cancels tare and capture without changing
  connection state and clears the temporary baseline. Skip invokes it before
  starting the workout countdown.
- The accepted workout baseline now reaches `MotherboardMeterView`; the sensor
  card passes the service baseline. Rendering remains deferred to Task 4.

### Final verification

Focused test command:

```sh
rtk proxy timeout 240s xcodebuild test -quiet -project HangTen.xcodeproj -scheme HangTen -destination 'platform=iOS Simulator,id=5BD0C30F-C006-43F1-9EFC-4B47B93EA488' -derivedDataPath .context/DerivedData-task-3-lifecycle-final-tests -parallel-testing-enabled NO -maximum-parallel-testing-workers 1 -only-testing:HangTenTests/MotherboardWorkoutPreparationTests -only-testing:HangTenTests/MotherboardWorkoutRecorderTests -only-testing:HangTenTests/MotherboardBluetoothServiceTests
```

Result: PASS, exit 0. 55 tests ran: 7 preparation, 10 recorder, and 38
Bluetooth-service tests. Xcode emitted only the pre-existing simulator
build-number warnings.

Debug simulator build command:

```sh
rtk proxy timeout 240s xcodebuild -quiet -project HangTen.xcodeproj -scheme HangTen -configuration Debug -destination 'platform=iOS Simulator,id=5BD0C30F-C006-43F1-9EFC-4B47B93EA488' -derivedDataPath .context/DerivedData-task-3-lifecycle-final-build build
```

Result: PASS, exit 0. Xcode emitted only the pre-existing simulator
build-number warnings.

## Review-fix evidence

### Cancellation and invalid-baseline handling

- The preparation state now treats a tare/bodyweight completion as successful
  only when the caller confirms the service is still streaming. A lost stream
  leaves the active step in place with a recoverable interruption failure.
- An absent, NaN, infinite, zero, or negative bodyweight capture leaves the
  user on the bodyweight step with a retry/skip path. Only a finite positive
  baseline transitions to ready and exposes Continue.
- Skip is terminal in the pure state. Subsequent tare completion, bodyweight
  completion, and retry events leave the skipped result and cleared baseline
  unchanged.
- The preparation view now observes `service.state` directly, treats a
  non-streaming state as interruption, and checks for `.streaming` again when
  either service completion flag becomes false. It therefore cannot call the
  workout-completion path from a service reset, disconnect, or cancellation.

### TDD regression coverage

RED command:

```sh
rtk proxy timeout 180s xcodebuild test -quiet -project HangTen.xcodeproj -scheme HangTen -destination 'platform=iOS Simulator,id=5BD0C30F-C006-43F1-9EFC-4B47B93EA488' -derivedDataPath .context/DerivedData-task-3-review-red -parallel-testing-enabled NO -maximum-parallel-testing-workers 1 -only-testing:HangTenTests/MotherboardWorkoutPreparationTests
```

Result: intentional RED, exit 65. The test target failed to compile because
the streaming-aware completion APIs, preparation failure state, and
`canContinue` invariant did not yet exist.

GREEN command:

```sh
rtk proxy timeout 180s xcodebuild test -quiet -project HangTen.xcodeproj -scheme HangTen -destination 'platform=iOS Simulator,id=5BD0C30F-C006-43F1-9EFC-4B47B93EA488' -derivedDataPath .context/DerivedData-task-3-review-green -parallel-testing-enabled NO -maximum-parallel-testing-workers 1 -only-testing:HangTenTests/MotherboardWorkoutPreparationTests
```

Result: PASS, exit 0. The deterministic preparation tests cover valid capture,
invalid non-positive/non-finite/absent captures, tare cancellation, bodyweight
cancellation, and terminal skip events.

### Final review-fix verification

Focused preparation plus recorder test command:

```sh
rtk proxy timeout 240s xcodebuild test -quiet -project HangTen.xcodeproj -scheme HangTen -destination 'platform=iOS Simulator,id=5BD0C30F-C006-43F1-9EFC-4B47B93EA488' -derivedDataPath .context/DerivedData-task-3-review-integration -parallel-testing-enabled NO -maximum-parallel-testing-workers 1 -only-testing:HangTenTests/MotherboardWorkoutPreparationTests -only-testing:HangTenTests/MotherboardWorkoutRecorderTests
```

Result: PASS, exit 0. Xcode emitted only the existing simulator build-number
warnings.

Debug simulator build command:

```sh
rtk proxy timeout 240s xcodebuild -quiet -project HangTen.xcodeproj -scheme HangTen -configuration Debug -destination 'platform=iOS Simulator,id=5BD0C30F-C006-43F1-9EFC-4B47B93EA488' -derivedDataPath .context/DerivedData-task-3-review-build build
```

Result: PASS, exit 0. Xcode emitted only the existing simulator build-number
warnings.
