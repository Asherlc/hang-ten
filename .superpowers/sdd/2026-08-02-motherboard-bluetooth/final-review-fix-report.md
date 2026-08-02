# Final review fix report

Status: DONE with simulator XCTest execution limitation documented below.

## Scope completed

Implemented the complete fix set from `final-review-fix-brief.md` without changing unrelated behavior or redesigning UI.

### Critical fixes

- `CoreBluetoothMotherboardTransport` now stores a central-manager factory and does not construct `CBCentralManager` during transport or app initialization. The manager is created only by `startScan()`, preserving the DEBUG simulated route and Release CoreBluetooth selection.
- Added the explicit `.notificationsReady` transport event. CoreBluetooth emits it only from a successful `didUpdateNotificationStateFor` callback with `isNotifying == true`; the simulated transport emits the same lifecycle event. The service waits for that event before writing `C`.
- Calibration completion now writes `S30` without publishing `.streaming`. Only a parsed `Stream:30` acknowledgement cancels the acknowledgement timeout and publishes `.streaming`; raw packets are ignored until that acknowledgement.
- Recorder intervals now use workout elapsed coordinates, receive the actual scheduled step-start elapsed coordinate, and clamp to `stepStartElapsed + plannedActiveDuration`.
- Added recorder `pause(at:)`, which closes pending/open intervals and installs a merge barrier so a later sample cannot bridge a pause, disconnect, rest boundary, or transition.
- `WorkoutView` flushes the recorder on manual timer pause, scene interruption, loss of streaming state, timed-rest entry, step changes, manual end through `interrupt(at:)`, and completion. Explicit rest-step and timed-rest sample exclusion remains intact.

### Important fixes

- The live peak resets when a different active step first records a sample. The per-step stored peak remains unchanged for summaries, and the meter hides a stale peak before the current step has a sample.
- Calibration below/above a sensor's ADC table now returns the nearest endpoint mass; interpolation remains unchanged between points.
- Added one cancellable bounded timeout covering each connection phase: scan (15 seconds), connection/characteristic/notification readiness (10 seconds), calibration (10 seconds), and `Stream:30` acknowledgement (5 seconds). Each timeout cleans up transport state and publishes `.failed` with an actionable error. Progression, successful stream, explicit disconnect, power loss, and error cleanup cancel the active timeout.

### Hardening

- Threshold values normalize to the settings UI range `0.1...50 kgf`: high values clamp to 50; non-finite or values below 0.1 use the existing 2.5 default. Normalized assigned values are persisted.
- The protocol parser's unterminated receive buffer is capped at 4,096 bytes by default. Overflow clears the buffer and emits a protocol error instead of retaining unbounded data.
- A successful `Stream:30` clears stale disconnect errors and resets the three-attempt reconnect budget.
- Timeout scheduling occurs before transport calls so the synchronous simulated transport cannot leave a stale timeout behind during reentrant lifecycle events.

## Regression coverage added first

- Lazy central-manager factory creation and scan-time creation.
- Notification-ready ordering, exact `Stream:30` acknowledgement gating, and rejection of the wrong stream rate.
- Scan, connection, calibration, and stream-ack timeout failures plus success cancellation.
- Reconnect error cleanup and retry-budget reset after a successful stream.
- Endpoint-clamped calibration and bounded parser recovery.
- Persisted and assigned threshold normalization.
- Late-first-sample scheduled-boundary clipping, pause/resume merge barriers, and per-step live peak reset.

The initial focused RED command was run before production implementation:

```sh
rtk perl -e 'alarm 120; exec @ARGV' xcodebuild test \
  -project HangTen.xcodeproj -scheme HangTen \
  -destination 'platform=iOS Simulator,id=5BD0C30F-C006-43F1-9EFC-4B47B93EA488' \
  -parallel-testing-enabled NO -maximum-parallel-testing-workers 1 \
  -derivedDataPath .context/DerivedData-final-review-fixes \
  -only-testing:HangTenTests/MotherboardBluetoothServiceTests \
  -only-testing:HangTenTests/MotherboardProtocolTests \
  -only-testing:HangTenTests/MotherboardModelsTests \
  -only-testing:HangTenTests/MotherboardWorkoutRecorderTests
```

Result: exit 65 / `TEST FAILED` at test compilation with the expected missing test-first API, `cannot find type 'MotherboardCentralManaging' in scope`. No production fix existed at that point.

## Verification obtained

Focused test target compile/link after implementation:

```sh
rtk perl -e 'alarm 120; exec @ARGV' xcodebuild build-for-testing \
  -project HangTen.xcodeproj -scheme HangTen \
  -destination 'generic/platform=iOS Simulator' \
  -derivedDataPath .context/DerivedData-final-review-fixes \
  CODE_SIGNING_ALLOWED=NO
```

Result: exit 0 with `** TEST BUILD SUCCEEDED **`. Both the app and `HangTenTests` bundle compiled and linked. Xcode emitted the branch's existing `DVTDeviceOperation` empty build-number diagnostics and the non-blocking AppIntents metadata warning.

Two bounded focused XCTest execution attempts were made:

1. Workspace final-review simulator `HangTen sucre-v1 Final Review`, UUID `5BD0C30F-C006-43F1-9EFC-4B47B93EA488`, iOS 26.5. The simulator booted, but `xcodebuild test` emitted only the existing `DVTDeviceOperation` diagnostics and did not begin XCTest execution within 60 seconds. The exact workspace process was interrupted with Ctrl-C; exit 1, no assertion result.
2. Existing workspace simulator `HangTen sucre-v1 Task8 20260802`, UUID `D5CDA3E4-6EE5-48E0-9AD2-66C10D00F536`, iOS 26.5. The same focused suite again emitted only the `DVTDeviceOperation` diagnostics and did not begin XCTest execution within 30 seconds. The exact process was interrupted with Ctrl-C; exit 1, no assertion result.

After interruption, `rtk pgrep -fl 'DerivedData-final-review-fixes'` returned exit 1 with no matching process, confirming no scoped test command remained running.

Final quick verification before commit:

- `rtk git diff --check`: exit 0, no whitespace errors.
- Worktree contained only the ten scoped source/test files plus this report.

## Verification limitations

- No focused XCTest assertion completed because both explicit workspace simulators stalled before XCTest startup.
- Per the final user directive, no further simulator waiting or full XCTest attempt was made after those bounded stalls.
- The successful generic Debug `build-for-testing` preceded three small source-only corrections: reentrant timeout scheduling order, normalized assignment persistence, and routing `interrupt(at:)` through `pause(at:)`. Those corrections were inspected and `git diff --check` passed, but a fresh post-correction build was not run because the user directed immediate report and commit.
- No physical Motherboard or physical iPhone validation was attempted, as required.

## Files changed

- `HangTen/Models/MotherboardBluetoothService.swift`
- `HangTen/Models/MotherboardModels.swift`
- `HangTen/Models/MotherboardProtocol.swift`
- `HangTen/Models/MotherboardWorkoutRecorder.swift`
- `HangTen/Models/SimulatedMotherboardTransport.swift`
- `HangTen/Views/RootView.swift`
- `HangTenTests/MotherboardBluetoothServiceTests.swift`
- `HangTenTests/MotherboardModelsTests.swift`
- `HangTenTests/MotherboardProtocolTests.swift`
- `HangTenTests/MotherboardWorkoutRecorderTests.swift`
- `.superpowers/sdd/2026-08-02-motherboard-bluetooth/final-review-fix-report.md`
