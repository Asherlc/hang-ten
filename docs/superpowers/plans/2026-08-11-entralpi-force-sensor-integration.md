# Entralpi Force-Sensor Integration Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Connect Entralpi force plates through a profile-driven CoreBluetooth stack while retaining Motherboard behaviour.

**Architecture:** Keep `MotherboardMeasurement` as the normalized workout shape. Configure scanning and connection from a selected `ForceSensorConnectionProtocol`; Motherboard keeps its UART parser and commands, while Entralpi calibrates a standing baseline then emits baseline-minus-raw pulling force.

**Tech Stack:** Swift 6, SwiftUI, Combine, CoreBluetooth, XCTest, Xcode project build phases.

## Global Constraints

- Entralpi values are exact: name prefix `ENTRALPI`; service `0000181D-0000-1000-8000-00805F9B34FB`; notification `0000FFF1-0000-1000-8000-00805F9B34FB`; two-byte unsigned big-endian kg centigrams.
- Do not subscribe to `FFF4`; do not add Entralpi writes or hardware tare/start/stop commands.
- Entralpi calibration is ten standing samples, mean `1...200` kg, population standard deviation `<= 0.5` kg, followed by `max(0, baselineKGF + addedLoadKGF - rawScaleLoadKGF)`.
- Reject frames shorter than two bytes and never publish before calibration completes.
- Preserve Motherboard's `C`, `S30`, parser, bounded reconnect, and software tare behaviour exactly.
- Preserve `MotherboardMeasurement` and `WorkoutSessionRecord` coding keys; persist the selected force-sensor profile for new sessions.
- Use test-first red-green-refactor. Each reviewed task is committed and pushed.

---

### Task 1: Add Entralpi Protocol Rules

**Files:**
- Create: `HangTen/Models/EntralpiProtocol.swift`
- Create: `HangTenTests/EntralpiProtocolTests.swift`
- Modify: `HangTen/Models/ForceSensorModels.swift`
- Modify: `HangTenTests/ForceSensorModelsTests.swift`
- Modify: `HangTen.xcodeproj/project.pbxproj`

**Interfaces:** Produce `ForceSensorConnectionProtocol` (`.motherboard`, `.entralpi`, `init?(profile:)`, `automaticCandidates`, `serviceUUIDs`, `notificationCharacteristics`, `matches(_:)`), `EntralpiRawScaleSample`, `EntralpiCalibration`, and `EntralpiProtocolAdapter`.

- [ ] **Step 1: Write failing protocol tests**

```swift
func testEntralpiUsesVendorPrefixAndWeightCharacteristic() throws {
    let adapter = EntralpiProtocolAdapter()
    let service = try XCTUnwrap(UUID(uuidString: "0000181D-0000-1000-8000-00805F9B34FB"))
    let notify = try XCTUnwrap(UUID(uuidString: "0000FFF1-0000-1000-8000-00805F9B34FB"))
    XCTAssertTrue(adapter.matches(.init(name: "ENTRALPI-42", serviceUUIDs: [])))
    XCTAssertFalse(adapter.matches(.init(name: "entralpi-42", serviceUUIDs: [service])))
    XCTAssertEqual(adapter.contract.serviceUUIDs, [service])
    XCTAssertEqual(adapter.contract.notificationCharacteristics, [.init(serviceUUID: service, characteristicUUID: notify)])
}

func testEntralpiPreservesBigEndianCentigramsAndRejectsShortFrame() throws {
    let adapter = EntralpiProtocolAdapter()
    XCTAssertEqual(try XCTUnwrap(adapter.decodeRawScaleSample(Data([0x04, 0xD2]))).kilograms, 12.34, accuracy: 0.000_001)
    XCTAssertNil(adapter.decodeRawScaleSample(Data([0x04])))
}
```

- [ ] **Step 2: Verify red**

Run: `xcodebuild test -project HangTen.xcodeproj -scheme HangTen -destination 'platform=iOS Simulator,name=iPhone 16' -only-testing:HangTenTests/EntralpiProtocolTests`

Expected: compile failure because `EntralpiProtocolAdapter` does not exist.

- [ ] **Step 3: Add the smallest protocol implementation**

```swift
struct EntralpiRawScaleSample: Equatable { let kilograms: Double }

struct EntralpiProtocolAdapter {
    static let weightServiceUUID = UUID(uuidString: "0000181D-0000-1000-8000-00805F9B34FB")!
    static let weightNotificationUUID = UUID(uuidString: "0000FFF1-0000-1000-8000-00805F9B34FB")!

    func decodeRawScaleSample(_ frame: Data) -> EntralpiRawScaleSample? {
        guard frame.count >= 2 else { return nil }
        let value = UInt16(frame[frame.startIndex]) << 8 | UInt16(frame[frame.index(after: frame.startIndex)])
        return .init(kilograms: Double(value) / 100)
    }
}
```

Define the connection-protocol contract from the interface block and add `ForceSensorProfile.connectableCases` equal to `[.automatic, .motherboard, .entralpi]`.

- [ ] **Step 4: Add failing calibration/conversion tests**

```swift
func testEntralpiCalibrationReturnsRoundedBaselineOnlyAfterTenStableSamples() {
    var calibration = EntralpiCalibration()
    for _ in 0..<9 { XCTAssertNil(calibration.append(70.04)) }
    XCTAssertEqual(calibration.append(70.04), 70.0, accuracy: 0.000_001)
}

func testEntralpiConvertsResidualScaleLoadToPullingForce() throws {
    let adapter = EntralpiProtocolAdapter()
    XCTAssertEqual(try XCTUnwrap(adapter.forceKGF(rawScaleLoadKG: 42.34, baselineKG: 70, addedLoadKG: 5)), 32.66, accuracy: 0.000_001)
}
```

- [ ] **Step 5: Implement calibration and conversion**

Implement `EntralpiCalibration.append(_:) -> Double?`: reject non-finite values outside `1...200`, collect exactly ten values, use population standard deviation, reject values above `0.5`, and return the mean rounded to one decimal. Implement `forceKGF(rawScaleLoadKG:baselineKG:addedLoadKG:)` with finite non-negative input checks and the constrained formula.

- [ ] **Step 6: Verify green, commit, and push**

Run: `xcodebuild test -project HangTen.xcodeproj -scheme HangTen -destination 'platform=iOS Simulator,name=iPhone 16' -only-testing:HangTenTests/EntralpiProtocolTests -only-testing:HangTenTests/ForceSensorModelsTests`

Then run:

```bash
git add HangTen/Models/EntralpiProtocol.swift HangTen/Models/ForceSensorModels.swift HangTenTests/EntralpiProtocolTests.swift HangTenTests/ForceSensorModelsTests.swift HangTen.xcodeproj/project.pbxproj
git commit -m "Add Entralpi force sensor protocol"
git push origin HEAD
```

### Task 2: Make CoreBluetooth Discovery and GATT Setup Protocol-Driven

**Files:**
- Modify: `HangTen/Models/MotherboardBluetoothService.swift`
- Modify: `HangTenTests/MotherboardBluetoothServiceTests.swift`

**Interfaces:** Consume `ForceSensorConnectionProtocol` from Task 1. Produce `CoreBluetoothForceSensorTransport(protocols:centralManagerFactory:)`, configured discovery, and a discovered device carrying its selected protocol.

- [ ] **Step 1: Write failing transport tests**

```swift
func testTransportScansEntralpiWeightServiceAndConnectsPrefixMatchedDevice() throws {
    let manager = FakeCentralManager()
    let transport = CoreBluetoothForceSensorTransport(protocols: [.entralpi]) { _ in manager }
    let peripheral = FakeMotherboardPeripheral(name: "ENTRALPI-42")

    transport.startScan()
    XCTAssertEqual(manager.scannedServiceUUIDs, [CBUUID(string: "181D")])
    deliverDiscovery(peripheral, to: transport, advertisementData: [CBAdvertisementDataLocalNameKey: "ENTRALPI-42"])
    transport.connect(to: try XCTUnwrap(discoveredDevice(from: transport)))
    deliverConnection(peripheral, to: transport)

    XCTAssertEqual(peripheral.requestedServiceUUIDs, [CBUUID(string: "181D")])
}

func testTransportDoesNotTreatEntralpiUARTFFF4AsAWeightNotification() {
    let transport = CoreBluetoothForceSensorTransport(protocols: [.entralpi]) { _ in FakeCentralManager() }
    XCTAssertFalse(transport.isExpectedNotificationCharacteristic(CBUUID(string: "FFF4"), service: CBUUID(string: "FFF0")))
}
```

- [ ] **Step 2: Verify red**

Run: `xcodebuild test -project HangTen.xcodeproj -scheme HangTen -destination 'platform=iOS Simulator,name=iPhone 16' -only-testing:HangTenTests/MotherboardBluetoothServiceTests`

Expected: compile failure because the protocol-driven transport does not exist.

- [ ] **Step 3: Refactor the transport around the selected protocol**

Replace hard-coded service/name/characteristic checks in `CoreBluetoothMotherboardTransport` with `CoreBluetoothForceSensorTransport`. At scan, union configured protocol services. At discovery, evaluate each protocol against peripheral name, advertised local name, and advertised services; retain both peripheral and matched protocol. At connection, request only matched services; at service discovery, request and resolve only matched notification characteristics. Keep a write characteristic only for Motherboard's existing RX characteristic; Entralpi has none.

- [ ] **Step 4: Preserve Motherboard coverage while updating fakes**

Extend fake central/peripheral helpers to record scanned services, requested services, and notification characteristics. Preserve existing assertions for Motherboard service `6E400001-B5A3-F393-E0A9-E50E24DCCA9E`, RX/TX discovery, TX notification, response write type, and disconnect error handling.

- [ ] **Step 5: Verify green, commit, and push**

Run: `xcodebuild test -project HangTen.xcodeproj -scheme HangTen -destination 'platform=iOS Simulator,name=iPhone 16' -only-testing:HangTenTests/MotherboardBluetoothServiceTests`

Then run:

```bash
git add HangTen/Models/MotherboardBluetoothService.swift HangTenTests/MotherboardBluetoothServiceTests.swift
git commit -m "Generalize force sensor Bluetooth transport"
git push origin HEAD
```

### Task 3: Make Lifecycle and Measurement Publishing Profile-Aware

**Files:**
- Modify: `HangTen/Models/MotherboardBluetoothService.swift`
- Modify: `HangTenTests/MotherboardBluetoothServiceTests.swift`

**Interfaces:** Consume the selected protocol from Task 2 and `EntralpiCalibration` from Task 1. Produce `connect(profile:)`, `connectedForceSensorProfile`, Entralpi baseline handling, and normalized `MotherboardMeasurement` output.

- [ ] **Step 1: Write failing Entralpi lifecycle tests**

```swift
func testEntralpiDoesNotPublishBeforeStandingCalibrationCompletes() {
    let transport = FakeMotherboardTransport(protocol: .entralpi)
    let service = MotherboardBluetoothService(transport: transport)
    connectEntralpi(service, with: transport)

    transport.emit(.notification(Data([0x1B, 0x5C]), Date()))
    XCTAssertNil(service.latestMeasurement)
    XCTAssertEqual(service.state, .calibrating)
}

func testEntralpiPublishesBaselineMinusRawScaleLoadAfterTenStableSamples() throws {
    let transport = FakeMotherboardTransport(protocol: .entralpi)
    let service = MotherboardBluetoothService(transport: transport)
    connectEntralpi(service, with: transport)
    for _ in 0..<10 { transport.emit(.notification(Data([0x1B, 0x5C]), Date())) }
    transport.emit(.notification(Data([0x10, 0x8A]), Date(timeIntervalSince1970: 2)))

    XCTAssertEqual(service.state, .streaming)
    XCTAssertEqual(service.bodyweightKGF, 70)
    XCTAssertEqual(try XCTUnwrap(service.latestMeasurement).aggregateLoadKGF, 28.9, accuracy: 0.000_001)
}
```

- [ ] **Step 2: Verify red**

Run: `xcodebuild test -project HangTen.xcodeproj -scheme HangTen -destination 'platform=iOS Simulator,name=iPhone 16' -only-testing:HangTenTests/MotherboardBluetoothServiceTests`

Expected: Entralpi frames enter the existing Motherboard parser and the tests fail.

- [ ] **Step 3: Add protocol-specific state transitions**

Add `connect(profile: ForceSensorProfile)` and preserve `connect()` as `connect(profile: .automatic)`. Resolve automatic discovery using Task 1 candidates; reject every unsupported profile before scanning with a visible error. Motherboard must retain its exact `characteristicsReady → notificationsReady → C → sixteen rows → S30 → Stream:30 → streaming` transition.

For Entralpi, create `EntralpiCalibration` at notification readiness, remain `.calibrating` through baseline collection, then set `bodyweightKGF`, `connectedForceSensorProfile`, and `.streaming`. Emit valid post-baseline frames as `MotherboardMeasurement(timestamp:sampleNumber:batteryValue:rawADCValues:sensorLoadsKGF:aggregateLoadKGF:)` with zero battery, empty raw/channel arrays, an increasing sample number, and converted force as the aggregate.

- [ ] **Step 4: Add invalid-calibration and Motherboard regression tests**

```swift
func testEntralpiFailsCalibrationForUnstableBaseline() {
    let transport = FakeMotherboardTransport(protocol: .entralpi)
    let service = MotherboardBluetoothService(transport: transport)
    connectEntralpi(service, with: transport)
    for kilograms in [70.0, 70.0, 70.0, 70.0, 70.0, 70.0, 70.0, 70.0, 70.0, 71.0] {
        transport.emit(entralpiFrame(kilograms), Date())
    }
    XCTAssertEqual(service.state, .failed)
    XCTAssertNil(service.latestMeasurement)
}
```

Re-run existing tests for `C` then `S30`, parser error threshold, Motherboard software tare, and bodyweight capture without changing their expected values.

- [ ] **Step 5: Verify green, commit, and push**

Run: `xcodebuild test -project HangTen.xcodeproj -scheme HangTen -destination 'platform=iOS Simulator,name=iPhone 16' -only-testing:HangTenTests/MotherboardBluetoothServiceTests -only-testing:HangTenTests/MotherboardModelsTests -only-testing:HangTenTests/MotherboardWorkoutRecorderTests`

Then run:

```bash
git add HangTen/Models/MotherboardBluetoothService.swift HangTenTests/MotherboardBluetoothServiceTests.swift
git commit -m "Add profile-aware Entralpi connection lifecycle"
git push origin HEAD
```

### Task 4: Wire Profile Selection, Preparation, and Persistence

**Files:**
- Modify: `HangTen/Views/MotherboardViews.swift`
- Modify: `HangTen/Views/MotherboardWorkoutPreparationView.swift`
- Modify: `HangTen/Views/RootView.swift`
- Modify: `HangTenTests/ForceSensorModelsTests.swift`
- Modify: `HangTenTests/MotherboardWorkoutPreparationTests.swift`

**Interfaces:** Consume `ForceSensorProfile.connectableCases`, `MotherboardBluetoothService.connect(profile:)`, and `connectedForceSensorProfile`. Produce a supported profile picker, profile-correct preparation, and persisted `WorkoutSessionRecord.forceSensorProfile`.

- [ ] **Step 1: Write failing profile and preparation tests**

```swift
func testConnectableProfilesExposeOnlyImplementedProtocols() {
    XCTAssertEqual(ForceSensorProfile.connectableCases, [.automatic, .motherboard, .entralpi])
}

func testEntralpiDoesNotRequireMotherboardTareAndRelaxedHangPreparation() {
    XCTAssertFalse(MotherboardWorkoutPreparation.requiresPreparation(
        isInitialStart: true,
        isStreaming: true,
        profile: .entralpi
    ))
}
```

- [ ] **Step 2: Verify red**

Run: `xcodebuild test -project HangTen.xcodeproj -scheme HangTen -destination 'platform=iOS Simulator,name=iPhone 16' -only-testing:HangTenTests/ForceSensorModelsTests -only-testing:HangTenTests/MotherboardWorkoutPreparationTests`

Expected: compile failure because profile-aware preparation is absent.

- [ ] **Step 3: Implement the selected-profile UI path**

In `MotherboardSettingsView`, add `Picker("Sensor type", selection: $settings.forceSensorProfile)` over `ForceSensorProfile.connectableCases`. In `MotherboardCard`, connect using `service.connect(profile: settings.forceSensorProfile)`.

Change `MotherboardWorkoutPreparation.requiresPreparation` to accept `profile`. Return `false` for Entralpi because it completes the vendor standing baseline during connection; preserve existing Motherboard behaviour. Pass `service.connectedForceSensorProfile` from `RootView`. Hide or disable manual tare for Entralpi and show exactly: `Entralpi calibrates bodyweight while you stand still after connecting.` Preserve Motherboard's existing tare copy and button behaviour.

When saving `WorkoutSessionRecord`, set `forceSensorProfile` to `service.connectedForceSensorProfile ?? settings.forceSensorProfile`; retain all existing measurement and bodyweight persistence fields.

- [ ] **Step 4: Add model/UI-adjacent regression assertions**

Add tests that named unsupported profiles are absent from `connectableCases`, automatic and Motherboard still require preparation, and Entralpi selection persists through `MotherboardSettingsStore`. Retain force-unit, threshold, and bodyweight-duration assertions.

- [ ] **Step 5: Verify green, run full tests, commit, and push**

Run: `xcodebuild test -project HangTen.xcodeproj -scheme HangTen -destination 'platform=iOS Simulator,name=iPhone 16'`

Then run:

```bash
git add HangTen/Views/MotherboardViews.swift HangTen/Views/MotherboardWorkoutPreparationView.swift HangTen/Views/RootView.swift HangTen/Models/ForceSensorModels.swift HangTenTests/ForceSensorModelsTests.swift HangTenTests/MotherboardWorkoutPreparationTests.swift
git commit -m "Wire Entralpi sensor profile into workouts"
git push origin HEAD
```

- [ ] **Step 6: Validate the DEBUG application**

Use the `validate-hang-ten-ios` skill. Build, install, launch, and inspect the DEBUG app. Confirm sensor settings exposes only Automatic, Motherboard, and Entralpi; Motherboard preparation copy remains unchanged; selecting Entralpi suppresses the Motherboard tare preparation.

## Final Verification

- [ ] Re-read `docs/superpowers/specs/2026-08-11-entralpi-force-sensor-integration-design.md` against Tasks 1–4 and verify every scoped requirement has a test or a direct validation step.
- [ ] Run `xcodebuild test -project HangTen.xcodeproj -scheme HangTen -destination 'platform=iOS Simulator,name=iPhone 16'` after all task fixes and reviews.
- [ ] Use `validate-hang-ten-ios` for final DEBUG build/install/launch inspection.
- [ ] Run `git status --short`; it must be empty before reporting completion.
