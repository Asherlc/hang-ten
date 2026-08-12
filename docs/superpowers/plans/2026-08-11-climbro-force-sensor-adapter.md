# Climbro Force-Sensor Adapter Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a source-faithful, protocol-level Climbro BLE adapter and tests without runtime Bluetooth integration.

**Architecture:** `ClimbroProtocolAdapter` declares named discovery, services, notification characteristics, and battery-only capabilities. `ClimbroProtocolParser` owns marker-state across BLE notifications and returns normalized `ForceSensorSample` values.

**Tech Stack:** Swift 5, Foundation `Data` and `UUID`, XCTest, Xcode project registration.

## Global Constraints

- Source authority is blob `4257b024609ebf545f6131319d65fd61e2cadd3e` at `packages/core/src/models/device/climbro.model.ts` in `Stevie-Ray/hangtime-grip-connect`.
- Do not invent Climbro writes, commands, start/stop behavior, hardware tare, battery clamping, packet-size limits, timeout/resynchronization rules, or runtime Bluetooth integration.
- Named discovery is case-sensitive `name.hasPrefix("Climbro")`; no advertised-service requirement is added.
- UART notification service and characteristic are `49535343-fe7d-4ae5-8fa9-9fafd205e455` and `49535343-1e4d-4bd9-ba61-23c647249616`.
- Parser state persists across `append(_:receivedAt:)`: `0xF0` selects battery mode, `0xF5` selects sensor mode, and `0xF6` is a 36 kg sensor sentinel.
- The adapter capability set is exactly `[.batteryLevel]`; do not add a write characteristic or `payload(for:)` API.
- Existing Climbro profile/model files remain unchanged.
- Commit and push all implementation changes to `origin agent/force-sensor-climbro`; do not create a PR.

---

## File structure

- `HangTen/Models/ClimbroProtocol.swift`: adapter and stateful byte-stream parser.
- `HangTenTests/ClimbroProtocolTests.swift`: executable source fixtures and discovery coverage.
- `docs/source-audits/2026-08-11-climbro-protocol.md`: immutable source link and field mapping.
- `HangTen.xcodeproj/project.pbxproj`: file references, groups, and source build phases for both Swift files.

### Task 1: Implement and audit the Climbro protocol adapter

**Files:**

- Create: `HangTen/Models/ClimbroProtocol.swift`
- Create: `HangTenTests/ClimbroProtocolTests.swift`
- Create: `docs/source-audits/2026-08-11-climbro-protocol.md`
- Modify: `HangTen.xcodeproj/project.pbxproj:30-35,111-116,226-230,457-489`

**Interfaces:**

- Consumes: `ForceSensorProfile.climbro`, `ForceSensorCapability`, `ForceSensorBLEContract`, `ForceSensorBLECharacteristic`, `ForceSensorAdvertisement`, and `ForceSensorSample`.
- Produces: `ClimbroProtocolAdapter.init?(profile:)`, `capabilities`, `contract`, `matches(_:)`; `ClimbroProtocolParser.init()`, `private(set) var batteryPercentage: Double`, and `mutating func append(_ frame: Data, receivedAt: Date) -> [ForceSensorSample]`.

- [ ] **Step 1: Write the failing tests and add their Xcode target membership**

Create `HangTenTests/ClimbroProtocolTests.swift` and register it in the `HangTenTests` group and `CC0000000000000000000005` sources phase. Add a pending `ClimbroProtocol.swift` file reference/build file to the Models group and `CC0000000000000000000002` sources phase, so the red run fails for absent symbols rather than a missing test file.

```swift
import Foundation
import XCTest
@testable import HangTen

final class ClimbroProtocolTests: XCTestCase {
    private let receivedAt = Date(timeIntervalSince1970: 3_579)

    func testParserMapsAuditedBatteryAndSensorFixture() throws {
        var parser = ClimbroProtocolParser()
        let samples = parser.append(Data([0xF0, 112, 0xF5, 10, 0xF6, 20]), receivedAt: receivedAt)

        XCTAssertEqual(parser.batteryPercentage, 0, accuracy: 0.000_001)
        XCTAssertEqual(samples.map(\.kilogramsForce), [10, 36, 20])
        XCTAssertTrue(samples.allSatisfy { $0.receivedAt == receivedAt })
    }

    func testParserRetainsSensorModeAcrossNotifications() {
        var parser = ClimbroProtocolParser()
        XCTAssertEqual(parser.append(Data([0xF5, 10]), receivedAt: receivedAt).map(\.kilogramsForce), [10])
        XCTAssertEqual(parser.append(Data([11, 0xF6]), receivedAt: receivedAt).map(\.kilogramsForce), [11, 36])
    }

    func testParserRetainsBatteryModeAcrossNotifications() {
        var parser = ClimbroProtocolParser()
        XCTAssertTrue(parser.append(Data([0xF0]), receivedAt: receivedAt).isEmpty)
        XCTAssertTrue(parser.append(Data([171]), receivedAt: receivedAt).isEmpty)
        XCTAssertEqual(parser.batteryPercentage, 50, accuracy: 0.000_001)
    }

    func testMarkersChangeModeAndBytesBeforeAMarkerEmitNothing() {
        var parser = ClimbroProtocolParser()
        XCTAssertTrue(parser.append(Data([10, 20]), receivedAt: receivedAt).isEmpty)
        XCTAssertTrue(parser.append(Data([0xF0, 230]), receivedAt: receivedAt).isEmpty)
        XCTAssertEqual(parser.batteryPercentage, 100, accuracy: 0.000_001)
        XCTAssertEqual(parser.append(Data([0xF5, 1]), receivedAt: receivedAt).map(\.kilogramsForce), [1])
    }

    func testAdapterUsesAuditedNamedContractAndBatteryOnlyCapability() throws {
        let adapter = try XCTUnwrap(ClimbroProtocolAdapter(profile: .climbro))
        let uart = try XCTUnwrap(UUID(uuidString: "49535343-FE7D-4AE5-8FA9-9FAFD205E455"))
        let notification = try XCTUnwrap(UUID(uuidString: "49535343-1E4D-4BD9-BA61-23C647249616"))
        let deviceInformation = try XCTUnwrap(UUID(uuidString: "0000180A-0000-1000-8000-00805F9B34FB"))

        XCTAssertEqual(adapter.capabilities, [.batteryLevel])
        XCTAssertEqual(adapter.contract.serviceUUIDs, [uart, deviceInformation])
        XCTAssertEqual(adapter.contract.notificationCharacteristics, [
            ForceSensorBLECharacteristic(serviceUUID: uart, characteristicUUID: notification)
        ])
        XCTAssertTrue(adapter.matches(ForceSensorAdvertisement(name: "Climbro Mini", serviceUUIDs: [])))
        XCTAssertFalse(adapter.matches(ForceSensorAdvertisement(name: "CLIMBRO", serviceUUIDs: [uart])))
        XCTAssertNil(ClimbroProtocolAdapter(profile: .progressor))
    }
}
```

- [ ] **Step 2: Run the focused test to verify RED**

Run:

```bash
xcodebuild test -project HangTen.xcodeproj -scheme HangTen -destination 'platform=iOS Simulator,name=iPhone 16' -only-testing:HangTenTests/ClimbroProtocolTests -derivedDataPath /private/tmp/hangten-climbro-derived-data
```

Expected: compilation fails because `ClimbroProtocolParser` and `ClimbroProtocolAdapter` do not exist. If no simulator is available, record its exact environmental error and complete the available verification after implementation.

- [ ] **Step 3: Implement the minimal adapter and parser**

Create `HangTen/Models/ClimbroProtocol.swift` with `ClimbroProtocolAdapter` constants for the UART service, notification characteristic, and Device Information service. Its failable initializer accepts only `.climbro`; `capabilities` returns `[.batteryLevel]`; `contract` has both services and only the UART notification characteristic; `matches(_:)` returns `advertisement.name?.hasPrefix("Climbro") == true`.

Implement `ClimbroProtocolParser` with a private `Mode` enum (`uninitialized`, `battery`, `sensor`), persistent `mode`, and `batteryPercentage = 0`. In `append`, process each byte in order: `0xF0` switches to battery; `0xF5` switches to sensor; other values pass through `0xF6 -> 36`; battery mode updates `100 * (Double(value) - 112) / 118`; sensor mode appends `ForceSensorSample(value: Double(value), unit: .kilogramsForce, receivedAt: receivedAt)` when non-nil; uninitialized mode emits nothing.

Do not add any command, write characteristic, parser reset, clamp, or unsupported recovery behavior.

- [ ] **Step 4: Write the source audit**

Create `docs/source-audits/2026-08-11-climbro-protocol.md` linking `https://github.com/Stevie-Ray/hangtime-grip-connect/blob/02dd6ff227ffb0fc521fd547a83e85453351eb3b/packages/core/src/models/device/climbro.model.ts` and recording blob `4257b024609ebf545f6131319d65fd61e2cadd3e`. Map the `Climbro` prefix, UART/Device Information contract, automatic notification streaming, marker fields, `0xF6` sentinel, kilograms, and battery formula. Explicitly state that known writable UART/control-point UUIDs are not exposed because no Climbro command payload is sourced.

- [ ] **Step 5: Run GREEN verification**

Run the focused command from Step 2, then:

```bash
xcodebuild test -project HangTen.xcodeproj -scheme HangTen -destination 'platform=iOS Simulator,name=iPhone 16' -derivedDataPath /private/tmp/hangten-climbro-derived-data
```

Expected: focused and full `HangTenTests` test runs pass. If simulation is unavailable, run a generic iOS build, report the test-environment blocker, and retain the exact command output.

- [ ] **Step 6: Verify registration, audit scope, commit, and push**

Run:

```bash
git diff --check
rg -n 'ClimbroProtocol' HangTen.xcodeproj/project.pbxproj
git add HangTen/Models/ClimbroProtocol.swift HangTenTests/ClimbroProtocolTests.swift docs/source-audits/2026-08-11-climbro-protocol.md HangTen.xcodeproj/project.pbxproj
git commit -m "feat: add Climbro force sensor adapter"
git push origin agent/force-sensor-climbro
```

Confirm each Swift file appears exactly once in its group and source phase, and that the audit contains no unsupported command claim.
