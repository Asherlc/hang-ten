# Task 4: Live balance and bodyweight UI/settings/history

## Scope

Implemented the Task 4 UI, summary, and DEBUG simulator work without changing
the Task 3 preparation/lifecycle plumbing.

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
  keeps its previous whole-fixture repeat behavior.

## TDD evidence

### RED

Added the pure summary formatter test and deterministic simulator phase tests
before implementation, then ran:

```sh
rtk xcodebuild -project HangTen.xcodeproj -scheme HangTen -destination 'platform=iOS Simulator,id=0F2FE770-996B-40A8-A546-3CD611D97EEF' -only-testing:HangTenTests/WorkoutSummaryTests -only-testing:HangTenTests/SimulatedMotherboardTransportTests test
```

Result: intentional RED, exit 65. The test target could not find
`WorkoutSummaryFormatting`, which was the new formatter contract being added.

### GREEN

```sh
rtk proxy xcodebuild test -quiet -project HangTen.xcodeproj -scheme HangTen -destination 'platform=iOS Simulator,id=0F2FE770-996B-40A8-A546-3CD611D97EEF' -parallel-testing-enabled NO -maximum-parallel-testing-workers 1 -only-testing:HangTenTests/WorkoutSummaryTests -only-testing:HangTenTests/SimulatedMotherboardTransportTests
```

Result: PASS, exit 0. The XCTest result bundle reports 6 passed, 0 failed, and
0 skipped tests on iPhone 17 Pro (iOS 26.4). Xcode emitted only its existing
simulator build-number warnings.

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
  route: tare consumes the first 15 frames, the relaxed-jug-hang capture
  consumes the stable next frames, and continuing reaches live force, balance,
  and percentage feedback.
- `HANGTEN_REVIEW_WORKOUT=1` still opens the existing workout surface; adding
  `HANGTEN_REVIEW_AUTOSTART=1` retains its Task 3 behavior of skipping setup.
  That autostart path intentionally has no captured baseline, so it exercises
  force/balance and the explicit baseline-unavailable state. Use the setup
  route for percentage feedback.

## Concerns

No production Bluetooth dependency was introduced. Simulator frame values are
deterministic and encode through the existing raw packet path; their behavior
is DEBUG-only.
