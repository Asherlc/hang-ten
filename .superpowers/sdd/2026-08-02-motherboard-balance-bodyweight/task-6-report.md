# Task 6 hardening report

## RED

- Added focused preparation, protocol/Codable, granular-store, service, and simulator regressions before production changes.
- `xcodebuild test` initially failed as expected because `MotherboardWorkoutPreparation` did not expose the explicit `startTare` / `startBodyweightCapture` state-machine actions or bodyweight-capture state. The build stopped before the remaining new assertions could execute.

## GREEN

- Preparation now requires a user action to start tare and, after the service's tare-completion signal, a separate user action to start the timed relaxed-jug-hang capture. The DEBUG simulator reset remains immediately before the service tare request.
- Decoding preserves raw ADC values and signed sensor-load semantics while converting overflowed or NaN derived loads to finite saturated values. The regression verifies JSON encoding succeeds.
- Workout records now persist as `session-<UUID>.json` files under Application Support/Hang Ten/Workout Sessions on a serial utility queue. The in-memory history updates immediately; `flush()` makes queued writes deterministic for tests; `persistenceError` exposes write/load failures. Valid legacy history migrates only when the file store does not exist, and the legacy UserDefaults blob is removed after successful migration.
- The DEBUG fixture has 40 relaxed jug-hang samples at 300 ms (12 seconds), then retains dynamic unequal active samples. The maximum 10-second preparation regression confirms the active phase is not consumed.

## Final evidence

- Focused preparation/protocol/service/store/simulator run: 68 tests, 0 failures, before the later Xcode runner hang.
- The models/recorder/AppStore regression invocation (33 selected tests) was stopped before a final result after the Xcode runner hung; it needs independent verification.
- Debug iOS Simulator build: `BUILD SUCCEEDED`.

## Storage details

- Per-session round trip, legacy migration, 20-session cap, removal, and unwritable-directory error reporting are covered with unique temporary directories.
- Failed writes leave the in-memory session available and set `persistenceError`; migration removes the legacy blob only after its file writes succeed.

## Concern

- Xcode emitted the pre-existing `DVTDeviceOperation` build-number and AppIntents metadata warnings. No compile error was present in the captured output, but the later test invocations hung and were stopped at the user's request.
