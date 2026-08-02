# Task 6 Report — Persist summaries and inject shared app dependencies

## Status

DONE

## Delivered scope

- `AppStore` is now main-actor isolated and accepts injected `MotherboardBluetoothService`, `MotherboardSettingsStore`, and `WorkoutSessionStoring` dependencies. Production defaults preserve the prior HealthKit service and create a CoreBluetooth-backed Motherboard service only when an explicit service is not injected.
- `sessionHistory` is a published, read-only snapshot initialized from the supplied session store.
- `markSessionComplete(_:startDate:endDate:session:)` persists a supplied record and updates `sessionHistory` before retaining the existing completion counter, title, HealthKit write, and HealthKit error behavior. A nil record preserves existing/incomplete-session history unchanged.
- `HangTenApp` now creates exactly one `CoreBluetoothMotherboardTransport`-backed service, settings store, session store, and `AppStore`. The same service/settings instances are provided to the SwiftUI environment and injected into `AppStore`; the session store is injected through `AppStore`.
- Startup constructs the CoreBluetooth manager only. It does not invoke `connect()` and does not request HealthKit authorization.

## Exact files

Modified:

- `HangTen/Models/AppStore.swift`
- `HangTen/HangTenApp.swift`
- `HangTen.xcodeproj/project.pbxproj`

Created:

- `HangTenTests/AppStoreTests.swift`
- `.superpowers/sdd/2026-08-02-motherboard-bluetooth/task-6-report.md`

Preserved without modification:

- `HangTen/Models/WorkoutSessionStore.swift` and `HangTenTests/WorkoutSessionStoreTests.swift` from `b6cc64e`
- `HangTen/Models/MotherboardBluetoothService.swift` and `HangTenTests/MotherboardBluetoothServiceTests.swift` from `ccaeb0f`

## TDD evidence

RED:

```sh
rtk proxy xcodebuild build-for-testing -project HangTen.xcodeproj -scheme HangTen \
  -destination 'platform=iOS Simulator,name=iPhone 17 Pro'
```

Exit 65. The new tests failed to compile because the old `AppStore` initializer accepted only `healthKitService`; the injected Motherboard/settings/session arguments were rejected.

GREEN:

```sh
rtk proxy xcodebuild build-for-testing -project HangTen.xcodeproj -scheme HangTen \
  -destination 'platform=iOS Simulator,name=iPhone 17 Pro'
```

Exit 0; `** TEST BUILD SUCCEEDED **` in 7.5 seconds.

Focused runtime verification:

```sh
rtk proxy xcodebuild test-without-building -project HangTen.xcodeproj -scheme HangTen \
  -destination 'platform=iOS Simulator,name=iPhone 17 Pro' \
  -only-testing:HangTenTests/AppStoreTests
```

Exit 0; both AppStore tests passed in 0.013 seconds (5.5 seconds wall time).

## Test limitations

- The full `test-without-building` suite was bounded by a 30-second observation window and completed in 23.1 seconds, but exited 65 with five failures in two unchanged BLE tests: `testCalibrationRequiresEverySensorAndValidPointBeforeStartingStream` and `testFragmentedRawPacketPublishesMeasurementAndBatteryAfterCalibration` (four assertions). The focused reproduction of those two tests also failed; no Task 6 diff touches either source or test file.
- The same full run passed all Task 6 AppStore tests (2/2), all workout-session-store tests (5/5), and the remaining 26 tests. Simulator output also contained CoreBluetooth XPC/API-misuse warnings while the required startup manager was constructed; no startup `connect()` or HealthKit authorization call is added by Task 6.

## Commit

`feat: inject shared Motherboard app dependencies`
