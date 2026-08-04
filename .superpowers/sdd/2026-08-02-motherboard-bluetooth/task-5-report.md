# Task 5 report — Motherboard CoreBluetooth service

## DONE

Implemented the Task 5 CoreBluetooth transport and `@MainActor` Motherboard service without changing the completed `WorkoutSessionStore` prework from `b6cc64e`.

## Files changed

- `HangTen/Models/MotherboardBluetoothService.swift` — app-level transport events/models, service coordinator, Nordic UART CoreBluetooth delegate transport, calibration/streaming/tare handling, measurement and battery publishing, and disconnect/retry cleanup.
- `HangTen/Models/MotherboardProtocol.swift` — accepts the Motherboard firmware’s single empty trailing calibration field while rejecting extra non-empty fields.
- `HangTenTests/MotherboardBluetoothServiceTests.swift` — existing RED fake-transport tests retained for command ordering, calibration, fragmented packets, power states, and reconnect limits.
- `HangTenTests/MotherboardProtocolTests.swift` — parser regression coverage for one empty trailing calibration field and rejection of non-empty/extra fields.
- `HangTen.xcodeproj/project.pbxproj` — service and test target references plus the Debug/Release Bluetooth usage description.

## Behavior delivered

- Scans for Nordic UART service `6E400001-B5A3-F393-E0A9-E50E24DCCA9E`, filters supplied names to `Motherboard`, discovers RX/TX, enables TX notifications, and writes with response when available.
- Notification enable precedes `C`; the service waits for all sixteen calibration rows before writing `S30`.
- Parsed raw packets publish decoded measurements and battery state. Disconnects clear session data, retain the reported error, and make no measurements.
- Calibration notifications such as `0,0,1,0,\r\n` now parse successfully, allowing the service to complete calibration and issue `S30`.

## Verification

- RED confirmed with bounded `xcodebuild build-for-testing ... -only-testing:HangTenTests/MotherboardBluetoothServiceTests`: expected missing `MotherboardBluetoothService`, `MotherboardTransport`, event, and device types.
- GREEN passed with the same bounded build-for-testing command: `** TEST BUILD SUCCEEDED **`.
- Pre-fix RED runtime evidence: the new parser regression failed on the healthy booted iPhone 17 Pro simulator because the five-field trailing-comma row was discarded. The named `HangTen bariloche Task5 20260802` simulator could not launch tests due to CoreSimulator `Invalid device state` / Mach `-308`.
- Post-fix runtime evidence: `MotherboardProtocolTests.testParserAcceptsOneEmptyTrailingCalibrationField` passed, and the focused service tests `testConnectCalibratesBeforeStartingThirtyHertzStream` and `testFragmentedRawPacketPublishesMeasurementAndBatteryAfterCalibration` passed on the healthy booted iPhone 17 Pro simulator, each under a 60-second timeout.
- The full project `build-for-testing` check also passed under a 120-second timeout. Full XCTest execution was not used.

## Review follow-up

- Calibration now starts streaming only when every `(sensor, calibrationPoint)` pair in `0...3 × 0...3` has arrived; rows with out-of-range points cannot contribute.
- The fake transport now verifies that a disconnect clears its selected connection before retrying or reporting final disconnection. New tests cover incomplete/out-of-range calibration, retry cleanup, and explicit disconnect cleanup.
- `CoreBluetoothMotherboardTransport.disconnect()` clears its selected peripheral synchronously before cancelling it. Failure reporting and service error/disconnect handling stop scanning/notifications, disconnect, clear parser/calibration/measurement state, and only then publish failure or retry state.
- The bounded focused `build-for-testing` command passed again after the review fix.

## Commit

`feat: connect to Motherboard over CoreBluetooth`

Review follow-up commit: `fix: harden Motherboard calibration and disconnect cleanup`

Parser compatibility fix commit: `fix: accept trailing comma in calibration rows`
