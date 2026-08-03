# Task 4: Live balance and bodyweight UI/settings/history

## Scope

Implemented the Task 4 UI, summary, and DEBUG simulator work while preserving
the Task 3 preparation/lifecycle behavior. Added a narrowly scoped DEBUG-only
simulation reset at preparation start so the fixture phases remain aligned.

- `MotherboardMeterView` retains current force, peak force, and active loaded
  time. It now renders accessible left/right shares and a finite-safe current
  percent-of-bodyweight line. Missing or invalid baselines and measurements
  state why feedback is unavailable instead of fabricating a baseline.
- `MotherboardSettingsView` now persists its existing capture duration through
  a 3...10 second, one-second `Stepper`, with relaxed-jug-hang copy. Existing
  unit, threshold, tare, and connection controls remain unchanged.
- `WorkoutSummaryFormatting.bodyweightBaselineText(for:unit:)` is a pure
  formatter used by both the summary and tests. Captured finite positive
  baselines appear in the selected unit; old `nil` records simply omit that
  optional section, including read-only history.
- The DEBUG simulator starts with 15 unloaded tare frames, then 18 stable
  relaxed-jug-hang frames (enough for the default five-second capture at its
  300 ms stream cadence), then repeats four varying, non-50/50 active frames.
  Channels 0+2 are left and 1+3 are right. Explicit custom sample injection
  keeps its previous whole-fixture repeat behavior. Because the review route
  auto-connects on launch, preparation resets the DEBUG simulator immediately
  before tare: it cancels the active timer, rewinds the fixture index, and
  restarts the stream. This keeps tare and bodyweight capture aligned to the
  fixture even after the launch-time stream has advanced. The reset control is
  DEBUG-only; CoreBluetooth has no dependency on it.
- `MotherboardSettingsStore.bodyweightCaptureDuration` defaults to 5 seconds
  for absent or non-finite values, then rounds finite values to whole seconds
  and clamps them to the inclusive 3...10 second UI range.

## TDD evidence

### RED

Added the simulator reset/raw-packet integration test and fractional capture
duration persistence assertions before implementation, then ran:

```sh
rtk proxy xcodebuild test -quiet -project HangTen.xcodeproj -scheme HangTen -destination 'platform=iOS Simulator,id=0AF49AA7-BA1F-4317-BEB2-4DCA8AB31681' -parallel-testing-enabled NO -maximum-parallel-testing-workers 1 -only-testing:HangTenTests/MotherboardModelsTests -only-testing:HangTenTests/SimulatedMotherboardTransportTests -only-testing:HangTenTests/MotherboardBluetoothServiceTests
```

Result: intentional RED, exit 65. The test target could not compile because
the simulator did not yet accept an injected stream interval; the preparation
reset contract was likewise absent. The new fractional-duration assertions
specified the rounding behavior before the store was changed.

### GREEN

```sh
rtk proxy xcodebuild test -project HangTen.xcodeproj -scheme HangTen -destination 'platform=iOS Simulator,id=0AF49AA7-BA1F-4317-BEB2-4DCA8AB31681' -parallel-testing-enabled NO -maximum-parallel-testing-workers 1 -only-testing:HangTenTests/WorkoutSummaryTests -only-testing:HangTenTests/SimulatedMotherboardTransportTests -only-testing:HangTenTests/MotherboardModelsTests -only-testing:HangTenTests/MotherboardBluetoothServiceTests
```

Result: PASS, exit 0. The selected XCTest run reports 58 passed, 0 failed, and
0 skipped tests on the explicit simulator destination. The new integration
test delays launch-time streaming, resets immediately before tare, exercises
the real calibration/parser/raw-frame path, captures the stable post-tare
baseline at approximately 63.92 kgf, then observes an unequal active frame.
Xcode emitted only its existing simulator build-number warnings.

## Debug simulator build

```sh
rtk proxy xcodebuild build -quiet -project HangTen.xcodeproj -scheme HangTen -configuration Debug -sdk iphonesimulator -destination 'generic/platform=iOS Simulator' CODE_SIGNING_ALLOWED=NO CODE_SIGNING_REQUIRED=NO
```

Result: PASS, exit 0. The only output was the existing simulator build-number
warning.

## DEBUG review usage

- Launch with `HANGTEN_REVIEW_MOTHERBOARD=1` to use the simulator instead of
  CoreBluetooth; it auto-connects and opens the Progress tab’s sensor card.
- Switch to Today and start a routine normally to exercise the intended setup
  route: preparation resets the simulator, tare consumes the first 15 frames,
  the relaxed-jug-hang capture consumes the stable next frames, and continuing
  reaches live force, balance, and percentage feedback.
- `HANGTEN_REVIEW_WORKOUT=1` still opens the existing workout surface; adding
  `HANGTEN_REVIEW_AUTOSTART=1` retains its Task 3 behavior of skipping setup.
  That autostart path intentionally has no captured baseline, so it exercises
  force/balance and the explicit baseline-unavailable state. Use the setup
  route for percentage feedback.

## Concerns

No production Bluetooth dependency was introduced. Simulator frame values are
deterministic and encode through the existing raw packet path; their behavior
is DEBUG-only.
