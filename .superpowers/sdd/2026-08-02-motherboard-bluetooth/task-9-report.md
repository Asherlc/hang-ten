# Task 9 report — DONE

## Delivered scope

Task 9 adds a DEBUG-only `SimulatedMotherboardTransport` and the
`HANGTEN_REVIEW_MOTHERBOARD=1` review route. In DEBUG, the route injects the
fixture, connects it automatically, and selects Progress. Release builds
always construct `CoreBluetoothMotherboardTransport`, even when the review
environment variable is present; there is no production-build bypass.

The fixture sends the complete calibration exchange and encoded raw
notifications through the existing `MotherboardBluetoothService`. Its
deterministic unloaded, loaded, peak, and released pattern repeats at a
bounded cadence while streaming. Each delivered notification receives a
current `Date`, so `WorkoutView.consume` can accept measurements after a
routine starts. The deterministic timestamps in `defaultSamples` remain
fixture inputs for assertions and are not forwarded as measurement timestamps.

The initial Task 9 work also added target entries, README sensor guidance, and
runtime-service documentation covering permissions, buffering, calibration,
recorder timing, disconnect behavior, reverse-engineered protocol status,
fixture scope, and physical-device requirements.

## Follow-up root cause and fix

The review regression was caused by the original stream scheduling: it queued
the sample array once over about 2.1 seconds and forwarded each sample's
deterministic 1970 timestamp. `WorkoutView.consume` correctly rejects a
measurement older than the routine's `startedAt`, and a user could not start a
routine during that one-shot sequence.

The follow-up replaces the array of delayed work items with one repeating
`DispatchSourceTimer` on the main queue. It advances `nextSampleIndex`, wraps
at the end of `samples`, emits every 300 ms, and stamps each raw notification
with `Date()` at delivery. `cancelStream()` cancels and clears the timer and
resets the index on disconnect, notification disable, and stream restart; no
unbounded work-item accumulation remains.

## Exact follow-up files

- `HangTen/Models/SimulatedMotherboardTransport.swift`
- `HangTenTests/SimulatedMotherboardTransportTests.swift`
- `docs/IOS_RUNTIME_SERVICES.md`
- `.superpowers/sdd/2026-08-02-motherboard-bluetooth/task-9-report.md`

The original Task 9 commit also contains the route, app wiring, project
entries, README, and initial runtime documentation. No Task 10 work was
started.

## TDD and verification

The original RED focused test failed before the fixture existed with
`Cannot find 'SimulatedMotherboardTransport' in scope`:

```sh
rtk xcodebuild test -project HangTen.xcodeproj -scheme HangTen \
  -destination 'platform=iOS Simulator,name=iPhone 17 Pro' \
  -only-testing:HangTenTests/SimulatedMotherboardTransportTests
```

The review regression test then failed against the one-shot implementation:
after the wait, the service had sample `3` instead of the expected repeated
sample `1`. That RED result established that the test exercised the actual
`MotherboardBluetoothService` path rather than merely inspecting fixture data.

The focused follow-up test passed with the repeating implementation using the
same command above. It verifies loaded/unloaded fixture coverage, repeated
sample delivery, current timestamps, calibration, and decoded aggregate load.

The bounded full suite passed on the available named iPhone 17 Pro simulator:
38 tests, 0 failures, 0 skipped. Result bundle:
`.context/task9-followup-full-tests.xcresult`.

```sh
rtk perl -e 'alarm 55; exec @ARGV' xcodebuild test \
  -project HangTen.xcodeproj -scheme HangTen \
  -destination 'platform=iOS Simulator,name=iPhone 17 Pro' \
  -resultBundlePath .context/task9-followup-full-tests.xcresult
```

The DEBUG build for the dedicated Task 9 simulator completed successfully:

```sh
rtk xcodebuild -project HangTen.xcodeproj -scheme HangTen \
  -configuration Debug \
  -destination 'platform=iOS Simulator,id=4E3EEDE4-D7C8-4D0E-B82B-5D025741F33F' \
  -derivedDataPath .context/DerivedData-task9-followup build
```

The original Release build with `HANGTEN_REVIEW_MOTHERBOARD=1` also passed,
confirming the DEBUG-only fixture is absent from the production configuration:

```sh
rtk env HANGTEN_REVIEW_MOTHERBOARD=1 xcodebuild \
  -project HangTen.xcodeproj -scheme HangTen -configuration Release \
  -destination 'platform=iOS Simulator,id=4E3EEDE4-D7C8-4D0E-B82B-5D025741F33F' \
  -derivedDataPath .context/DerivedData-task9-release build
```

A bounded full-test attempt against the dedicated UUID did not produce a
complete result bundle because the simulator reported
`CoreBluetooth XPC connection invalid`; this is recorded as simulator
environment noise. The fixture-focused tests and the available full suite
passed independently. `rtk git diff --check` passed before commit.

## Runtime validation

Dedicated simulator: `HangTen sucre-v1 Task9 Review`
(`4E3EEDE4-D7C8-4D0E-B82B-5D025741F33F`), explicitly owned for this workspace.
The built app was installed and launched with the review variable:

```sh
rtk xcrun simctl terminate 4E3EEDE4-D7C8-4D0E-B82B-5D025741F33F com.hangten.training || true
rtk xcrun simctl install 4E3EEDE4-D7C8-4D0E-B82B-5D025741F33F \
  .context/DerivedData-task9-followup/Build/Products/Debug-iphonesimulator/HangTen.app
rtk xcrun simctl get_app_container \
  4E3EEDE4-D7C8-4D0E-B82B-5D025741F33F com.hangten.training app
rtk perl -e 'alarm 40; exec @ARGV' env \
  SIMCTL_CHILD_HANGTEN_REVIEW_MOTHERBOARD=1 \
  xcrun simctl launch 4E3EEDE4-D7C8-4D0E-B82B-5D025741F33F com.hangten.training
```

The launch returned bundle/pid `com.hangten.training: 3391`. Screenshot
captured and inspected:

- `.context/task9-followup-progress.png` — blank white app scene with the
  status bar; no Hang Ten content rendered.

The earlier initial-pass screenshot `.context/task9-progress.png` showed only
the iOS boot spinner. Because this dedicated simulator did not render the app
surface, Progress streaming, Settings persistence, portrait/landscape
workout views, measured/unmeasured summaries, and disconnect timer usability
could not be visually inspected. This is the remaining UI validation
limitation, not a fixture test or build failure. Physical-device validation is
still required for Bluetooth permissions, discovery/GATT behavior, calibration
and force accuracy, firmware compatibility, and real disconnect timing.

## Commits

- `43a7c62 docs: add Motherboard simulator review flow`
- Follow-up commit: `fix: repeat Motherboard simulator stream`

