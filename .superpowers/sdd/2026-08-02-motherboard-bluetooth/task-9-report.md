# Task 9 report — BLOCKED

## Delivered scope

- Added the DEBUG-only `SimulatedMotherboardTransport` fixture. It emits the
  complete calibration exchange and encoded raw notifications so
  `MotherboardBluetoothService` continues to parse, calibrate, and publish
  timestamped measurements through its production service path.
- Added `HANGTEN_REVIEW_MOTHERBOARD=1`. In DEBUG it constructs that fixture,
  connects it automatically, and selects Progress. In Release, the app always
  constructs `CoreBluetoothMotherboardTransport`, including when the variable
  is present in the process environment.
- Added fixture tests, Xcode target entries, README sensor guidance, and
  runtime-service documentation covering permissions, buffering, calibration,
  recorder timing, disconnect behavior, reverse-engineered protocol status,
  fixture scope, and physical-device requirements.

## Files

- `HangTen/Models/SimulatedMotherboardTransport.swift`
- `HangTenTests/SimulatedMotherboardTransportTests.swift`
- `HangTen/HangTenApp.swift`
- `HangTen/Views/RootView.swift`
- `HangTen.xcodeproj/project.pbxproj`
- `README.md`
- `docs/IOS_RUNTIME_SERVICES.md`
- `.superpowers/sdd/2026-08-02-motherboard-bluetooth/task-9-report.md`

## TDD and verification

RED (before the fixture existed):

```sh
rtk xcodebuild test -project HangTen.xcodeproj -scheme HangTen \
  -destination 'platform=iOS Simulator,name=iPhone 17 Pro' \
  -only-testing:HangTenTests/SimulatedMotherboardTransportTests
```

It failed as expected with `Cannot find 'SimulatedMotherboardTransport' in
scope`. GREEN reran the same focused command successfully. The fixture tests
cover both loaded/unloaded defaults and real calibration/raw-frame delivery to
`MotherboardBluetoothService`, including the final sample timestamp.

The complete isolated test run was bounded to 55 seconds and passed: 38 tests,
0 failures, 0 skipped. Its result bundle is
`.context/DerivedData-task9-tests/Logs/Test/Test-HangTen-2026.08.02_10-43-02--0700.xcresult`.

```sh
rtk perl -e 'alarm 55; exec @ARGV' xcodebuild test -project HangTen.xcodeproj \
  -scheme HangTen -destination 'platform=iOS Simulator,id=4E3EEDE4-D7C8-4D0E-B82B-5D025741F33F' \
  -derivedDataPath .context/DerivedData-task9-tests

rtk env HANGTEN_REVIEW_MOTHERBOARD=1 xcodebuild -project HangTen.xcodeproj \
  -scheme HangTen -configuration Release \
  -destination 'platform=iOS Simulator,id=4E3EEDE4-D7C8-4D0E-B82B-5D025741F33F' \
  -derivedDataPath .context/DerivedData-task9-release build
```

The Release build succeeded with the review variable set, confirming the
DEBUG-only fixture does not prevent the production configuration from building.
`rtk git diff --check` also passed.

## Runtime validation

Dedicated simulator: `HangTen sucre-v1 Task9 Review`
(`4E3EEDE4-D7C8-4D0E-B82B-5D025741F33F`), newly created for this workspace.
It was built with `.context/DerivedData-task9`, installed explicitly, and
launched with:

```sh
rtk perl -e 'alarm 40; exec @ARGV' env SIMCTL_CHILD_HANGTEN_REVIEW_MOTHERBOARD=1 \
  xcrun simctl launch 4E3EEDE4-D7C8-4D0E-B82B-5D025741F33F com.hangten.training
```

Both bounded launch attempts completed, and `simctl list devices` reported the
UUID as Booted. However, the display stayed on the iOS boot spinner after the
initial bounded readiness poll and a bounded 45-second `bootstatus` retry.
Screenshot captured and inspected:

- `.context/task9-progress.png` — iOS boot spinner only; no Hang Ten surface.

Therefore Progress connected/streaming card, Settings unit/threshold
persistence, portrait/landscape current/peak/actual-time views, summary
measured/unmeasured states, and disconnect timer usability were not inspected.
This is the reason for BLOCKED status; it is a simulator runtime limitation,
not a failed build/test. Physical Motherboard validation remains mandatory for
Bluetooth permissions, discovery/GATT, calibration/force accuracy, firmware
compatibility, and real disconnect behavior.

## Commit

Scoped commit message: `docs: add Motherboard simulator review flow`.
No Task 10 work was started.
