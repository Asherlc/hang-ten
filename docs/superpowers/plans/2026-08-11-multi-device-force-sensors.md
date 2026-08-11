# Multi-Device Bluetooth Force Sensors Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add native CoreBluetooth streaming for Tindeq Progressor, PitchSix Force Board, Weiheng WH-C06, Entralpi, and Climbro, including generic Progressor-compatible and WH-C06-compatible profiles, while preserving Motherboard sessions and workout behavior.

**Architecture:** Keep `MotherboardMeasurement` as the persisted kgf data model and retain `MotherboardBluetoothService` as the observable workout dependency. Introduce a pure profile/protocol layer that declares each GATT or advertisement contract and decodes raw bytes to source-unit samples; make the CoreBluetooth transport profile-aware and normalize samples to kgf in the service. The existing Motherboard path stays intact behind its `.motherboard` profile.

**Tech Stack:** Swift 5, iOS 17, SwiftUI, CoreBluetooth, XCTest, and the existing hand-maintained Xcode project.

## Global Constraints

- Target iOS 17.0 and retain the existing Swift/Xcode project settings.
- Use only Apple frameworks. Do not add a JavaScript runtime or third-party BLE dependency.
- Connect only after an explicit user action; do not request Bluetooth permission or connect at launch.
- Store and record all samples canonically in finite, non-negative kgf. Preserve existing Codable keys and legacy Motherboard history decoding.
- Keep the workout timer authoritative; sensor samples never advance, pause, or modify routine steps.
- Retain the Motherboard UART protocol and its 30 Hz calibration flow unchanged.
- Automatic selection accepts only recognized advertisements. Generic Progressor scans for the Progressor service; generic WH-C06 accepts only manufacturer ID `0x0100` advertisements containing bytes 10 and 11.
- Display and expose only adapter-supported controls. Hardware tare is available for Progressor and PitchSix; software averaging tare remains for Motherboard, WH-C06, Entralpi, and Climbro. Only Progressor and PitchSix expose an explicit stop command.
- mySmartBoard is excluded from the picker and implementation until its BLE GATT and packet protocol is evidenced.
- Before implementing each non-Motherboard adapter, record the exact upstream source URL, Git blob SHA, service UUIDs, characteristic UUIDs, byte layout, source unit, kgf conversion, commands, and capabilities in `docs/source-audits/2026-08-11-force-sensor-protocols.md`.
- Use `apply_patch` for edits, prefix shell commands with `rtk`, run test-first cycles, commit each task, and push each commit to `origin relieved-peacock`.

---

## File Map

- Create `HangTen/Models/ForceSensorProtocols.swift`: stable profile identifiers, advertisement matching, BLE contracts, capability metadata, and pure packet decoders.
- Modify `HangTen/Models/MotherboardModels.swift`: profile selection persistence, source metadata, and backward-compatible session persistence.
- Modify `HangTen/Models/MotherboardBluetoothService.swift`: profile-aware transport lifecycle, characteristic validation, notification routing, and source-aware messages.
- Modify `HangTen/Models/SimulatedMotherboardTransport.swift`: deterministic samples and capabilities for every supported profile.
- Modify `HangTen/Views/MotherboardViews.swift`: Force sensor copy, profile picker, capability-driven controls, and unavailable-balance presentation.
- Modify `HangTen/Views/RootView.swift`: store the selected profile with each completed session.
- Modify `HangTen.xcodeproj/project.pbxproj`: compile the new Swift source and test target source.
- Create `HangTenTests/ForceSensorProtocolsTests.swift`: advertisement and packet-decoder behavior.
- Modify `HangTenTests/MotherboardBluetoothServiceTests.swift`: profile lifecycle, GATT validation, capability, and interruption tests.
- Modify `HangTenTests/MotherboardModelsTests.swift`: profile-setting and legacy Codable coverage.
- Create `docs/source-audits/2026-08-11-force-sensor-protocols.md`: field-level protocol evidence.

### Task 1: Define audited profiles and pure protocol decoders

**Files:**

- Create: `HangTen/Models/ForceSensorProtocols.swift`
- Create: `HangTenTests/ForceSensorProtocolsTests.swift`
- Create: `docs/source-audits/2026-08-11-force-sensor-protocols.md`
- Modify: `HangTen.xcodeproj/project.pbxproj`

**Interfaces:**

- Produces `ForceSensorProfile`, `ForceSensorCapability`, `ForceSensorBLEContract`, `ForceSensorAdvertisement`, and `ForceSensorDecoder.decode(_:profile:receivedAt:) -> [ForceSensorDecodedSample]`.
- Later tasks consume the profile IDs, matching behavior, BLE contracts, and decoded source-unit sample values.

- [ ] **Step 1: Write the failing profile and decoder tests**

```swift
func testAutomaticMatchingRecognizesNamedProfilesButNeverGenericProfiles() {
    XCTAssertEqual(ForceSensorProfile.automaticMatch(name: "Progressor 123", manufacturerData: nil), .progressor)
    XCTAssertEqual(ForceSensorProfile.automaticMatch(name: "Force Board", manufacturerData: nil), .pitchSix)
    XCTAssertEqual(ForceSensorProfile.automaticMatch(name: "ENTRALPI", manufacturerData: nil), .entralpi)
    XCTAssertEqual(ForceSensorProfile.automaticMatch(name: "Climbro 2", manufacturerData: nil), .climbro)
    XCTAssertEqual(ForceSensorProfile.automaticMatch(name: "IF_B7", manufacturerData: Data([0, 1])), .whC06)
    XCTAssertNil(ForceSensorProfile.automaticMatch(name: "Unknown", manufacturerData: nil))
}

func testProgressorDecoderReadsLittleEndianFloatKilogramsAndTimestamp() throws {
    let data = Data([1, 8, 0, 0, 72, 65, 64, 226, 1, 0])
    XCTAssertEqual(try ForceSensorDecoder.decode(data, profile: .progressor, receivedAt: Date(timeIntervalSince1970: 1)).first?.value, 12.5, accuracy: 0.0001)
}

func testPitchSixDecoderReadsBigEndianThreeBytePounds() throws {
    XCTAssertEqual(try ForceSensorDecoder.decode(Data([0, 1, 0, 0, 22]), profile: .pitchSix, receivedAt: .now).first?.value, 22)
}

func testWHC06DecoderReadsManufacturerBytesTenAndEleven() throws {
    var data = Data(repeating: 0, count: 12)
    data[10] = 0x04
    data[11] = 0xD2
    XCTAssertEqual(try ForceSensorDecoder.decode(data, profile: .whC06, receivedAt: .now).first?.value, 12.34, accuracy: 0.0001)
}
```

- [ ] **Step 2: Run the focused tests to confirm the expected missing-symbol failure**

Run: `rtk xcodebuild test -project HangTen.xcodeproj -scheme HangTen -destination 'platform=iOS Simulator,name=iPhone 17 Pro' -only-testing:HangTenTests/ForceSensorProtocolsTests`

Expected: compilation fails because `ForceSensorProfile` and `ForceSensorDecoder` are not defined.

- [ ] **Step 3: Implement the minimal profile contracts and decoders**

```swift
enum ForceSensorProfile: String, CaseIterable, Codable, Identifiable {
    case automatic, motherboard, progressor, pitchSix, whC06, entralpi, climbro, genericProgressor, genericWHC06
    var id: String { rawValue }
}

struct ForceSensorDecodedSample: Equatable {
    let value: Double
    let unit: ForceSensorSourceUnit
    let receivedAt: Date
}

enum ForceSensorSourceUnit { case kilogramsForce, poundsForce }
```

Implement these evidence-backed decoders and contracts:

- Progressor service `7E4E1701-1EA6-40C9-9DCC-13D34FFEAD57`, notify `...1702...`, write `...1703...`; TLV type `1`, length divisible by 8, then `(Float32 LE kgf, UInt32 LE microseconds)` pairs; commands `0x64` tare, `0x65` start, `0x66` stop.
- PitchSix Force Board service `9A88D67F-8DF2-4AFE-9E0D-C2BBBE773DD0`, force notify `...D682`, tare `...D683`, mode write service `467A8516-6E39-11EB-9439-0242AC130002` characteristic `...8517`; packet `(UInt16 BE count, count × UInt24 BE pounds)`; commands `0x04` stream, `0x05` tare, `0x07` idle; convert pounds by `value / 2.20462262185` only in the service task.
- WH-C06 manufacturer company ID `0x0100`, data bytes 10 and 11 as `UInt16 BE / 100` kgf; no GATT contract, commands, or hardware battery value.
- Entralpi name `ENTRALPI`, notify characteristic `0000FFF1-0000-1000-8000-00805F9B34FB` under service `0000FFF0-0000-1000-8000-00805F9B34FB`; first `UInt16 BE / 100` kgf; battery service `180F`, characteristic `2A19`.
- Climbro name prefix `Climbro`, UART service `49535343-FE7D-4AE5-8FA9-9FAFD205E455`, notify `49535343-1E4D-4BD9-BA61-23C647249616`; preserve marker state across notifications: `0xF0` selects battery, `0xF5` selects kgf force, and force byte `0xF6` means `36`; battery percent is `(raw - 112) * 100 / 118` clamped to `0...100`.

Write the audit with the six source URLs and Git blob SHAs observed during design: Progressor `c19d8b73885edda5ea8cfb2b567024f0a6e2a35b`, PitchSix `565d58d9603f41e0ea82097fe9e10541dc9aefa8`, WH-C06 `90d693c649ea1cce4157d73c9a04caa8b77dfc47`, Entralpi `c6cdd037207bee0299bf94000e1fdb40ac3b7ca9`, Climbro `4257b024609ebf545f6131319d65fd61e2cadd3e`, and Tindeq's official API URL. State that all non-Tindeq mappings are upstream open-source evidence, not manufacturer assertions.

- [ ] **Step 4: Run the focused tests and the protocol suite**

Run: `rtk xcodebuild test -project HangTen.xcodeproj -scheme HangTen -destination 'platform=iOS Simulator,name=iPhone 17 Pro' -only-testing:HangTenTests/ForceSensorProtocolsTests -only-testing:HangTenTests/MotherboardProtocolTests`

Expected: all selected tests pass.

- [ ] **Step 5: Commit and push**

```sh
rtk git add HangTen/Models/ForceSensorProtocols.swift HangTenTests/ForceSensorProtocolsTests.swift HangTen.xcodeproj/project.pbxproj docs/source-audits/2026-08-11-force-sensor-protocols.md
rtk git commit -m "feat: define force sensor protocol adapters"
rtk git push origin relieved-peacock
```

### Task 2: Make transport and service profile-aware

**Files:**

- Modify: `HangTen/Models/MotherboardBluetoothService.swift`
- Modify: `HangTen/Models/MotherboardModels.swift`
- Modify: `HangTen/Models/SimulatedMotherboardTransport.swift`
- Modify: `HangTenTests/MotherboardBluetoothServiceTests.swift`
- Modify: `HangTenTests/MotherboardModelsTests.swift`

**Interfaces:**

- Consumes `ForceSensorProfile`, `ForceSensorBLEContract`, and `ForceSensorDecoder` from Task 1.
- Produces `MotherboardBluetoothService.connect(profile:)`, published `connectedProfile`, published `capabilities`, and profile-tagged persisted session data.

- [ ] **Step 1: Write the failing service and persistence tests**

```swift
func testProgressorTransitionsToStreamingAndPublishesKilogramsForce() {
    let transport = FakeMotherboardTransport()
    let service = MotherboardBluetoothService(transport: transport)
    service.connect(profile: .progressor)
    transport.emit(.discovered(.init(id: UUID(), name: "Progressor 1", profile: .progressor)))
    transport.emit(.connected)
    transport.emit(.characteristicsReady)
    transport.emit(.notificationsReady)
    transport.emit(.notification(Data([1, 8, 0, 0, 32, 65, 0, 0, 0, 0]), Date()))
    XCTAssertEqual(service.state, .streaming)
    XCTAssertEqual(service.latestMeasurement?.aggregateLoadKGF, 10, accuracy: 0.0001)
}

func testLegacySessionDecodesWithoutSensorProfile() throws {
    let record = try JSONDecoder().decode(WorkoutSessionRecord.self, from: legacySessionJSON)
    XCTAssertEqual(record.forceSensorProfile, .motherboard)
}

func testUnsupportedTareDoesNotWriteToWHC06() {
    let service = MotherboardBluetoothService(transport: FakeMotherboardTransport())
    XCTAssertFalse(service.capabilities.contains(.hardwareTare))
}
```

- [ ] **Step 2: Run the focused tests to confirm the expected API failure**

Run: `rtk xcodebuild test -project HangTen.xcodeproj -scheme HangTen -destination 'platform=iOS Simulator,name=iPhone 17 Pro' -only-testing:HangTenTests/MotherboardBluetoothServiceTests -only-testing:HangTenTests/MotherboardModelsTests`

Expected: compilation fails because profile-aware discovery, `connect(profile:)`, and `forceSensorProfile` do not exist.

- [ ] **Step 3: Implement profile-aware lifecycle without changing Motherboard behavior**

```swift
func connect(profile: ForceSensorProfile) {
    selectedProfile = profile
    transport.startScan(profile: profile)
}

private func publish(_ sample: ForceSensorDecodedSample) {
    let kgf = sample.unit == .poundsForce ? sample.value / 2.20462262185 : sample.value
    guard kgf.isFinite else { return }
    latestMeasurement = MotherboardMeasurement(timestamp: sample.receivedAt, sampleNumber: nextSampleNumber(), sensorLoadsKGF: [max(0, kgf)], aggregateLoadKGF: max(0, kgf))
}
```

Extend transport events with the selected profile and optional advertisement payload. For named profiles, discover the exact service set, reject a missing required service or characteristic with `"<profile label> is missing the required Bluetooth service."`, subscribe to the profile's notify characteristic, and emit raw notifications. For Progressor and PitchSix, issue the audited start command after notifications. For Entralpi and Climbro, subscription starts streaming. For WH-C06, remain in scanning mode, accept only the selected peripheral's company-ID payload, decode its advertisement as streaming data, and fail after ten seconds without a new matching advertisement. Do not issue a CoreBluetooth GATT connection for WH-C06.

Retain Motherboard calibration code and commands only when `selectedProfile == .motherboard`. Preserve software tare for non-hardware-tare profiles by averaging their single normalized channel. Add `forceSensorProfile: ForceSensorProfile` to `WorkoutSessionRecord`, decode a missing key as `.motherboard`, and record `connectedProfile` from `RootView`.

- [ ] **Step 4: Run the focused state, recorder, history, and model suites**

Run: `rtk xcodebuild test -project HangTen.xcodeproj -scheme HangTen -destination 'platform=iOS Simulator,name=iPhone 17 Pro' -only-testing:HangTenTests/MotherboardBluetoothServiceTests -only-testing:HangTenTests/MotherboardWorkoutRecorderTests -only-testing:HangTenTests/WorkoutHistoryTests -only-testing:HangTenTests/MotherboardModelsTests`

Expected: all selected tests pass.

- [ ] **Step 5: Commit and push**

```sh
rtk git add HangTen/Models/MotherboardBluetoothService.swift HangTen/Models/MotherboardModels.swift HangTen/Models/SimulatedMotherboardTransport.swift HangTen/Views/RootView.swift HangTenTests/MotherboardBluetoothServiceTests.swift HangTenTests/MotherboardModelsTests.swift
rtk git commit -m "feat: stream force sensors through bluetooth service"
rtk git push origin relieved-peacock
```

### Task 3: Expose profile selection and capability-driven sensor controls

**Files:**

- Modify: `HangTen/Views/MotherboardViews.swift`
- Modify: `HangTen/Views/RootView.swift`
- Modify: `HangTenTests/AppStoreTests.swift`
- Modify: `HangTenTests/MotherboardBluetoothServiceTests.swift`

**Interfaces:**

- Consumes `MotherboardBluetoothService.connect(profile:)`, `connectedProfile`, and `capabilities` from Task 2.
- Produces the Force sensor picker and controls that match the active adapter.

- [ ] **Step 1: Write the failing behavioral tests**

```swift
func testSettingsPersistTheSelectedForceSensorProfile() {
    let defaults = UserDefaults(suiteName: "ForceSensorProfileTests")!
    defaults.removePersistentDomain(forName: "ForceSensorProfileTests")
    let first = MotherboardSettingsStore(defaults: defaults)
    first.forceSensorProfile = .genericProgressor
    XCTAssertEqual(MotherboardSettingsStore(defaults: defaults).forceSensorProfile, .genericProgressor)
}

func testWHC06DoesNotExposeHardwareTareOrStopCapabilities() {
    XCTAssertFalse(ForceSensorProfile.whC06.capabilities.contains(.hardwareTare))
    XCTAssertFalse(ForceSensorProfile.whC06.capabilities.contains(.explicitStop))
}
```

- [ ] **Step 2: Run the focused tests to confirm the expected failure**

Run: `rtk xcodebuild test -project HangTen.xcodeproj -scheme HangTen -destination 'platform=iOS Simulator,name=iPhone 17 Pro' -only-testing:HangTenTests/MotherboardModelsTests -only-testing:HangTenTests/MotherboardBluetoothServiceTests`

Expected: the selected-profile setting and capabilities are absent or have no UI-consumable representation.

- [ ] **Step 3: Implement the Force sensor UI**

```swift
Picker("Device profile", selection: $settings.forceSensorProfile) {
    ForEach(ForceSensorProfile.selectableCases) { profile in
        Text(profile.label).tag(profile)
    }
}

Button(service.state.shouldDisconnect ? "Disconnect sensor" : "Connect sensor") {
    service.state.shouldDisconnect ? service.disconnect() : service.connect(profile: settings.forceSensorProfile)
}
```

Rename visible "Training sensor" and "Sensor settings" copy to "Force sensor". Display the resolved connected profile on the card, retain the existing unit and threshold controls, hide hardware-tare buttons unless the capability is present, and keep software tare for profiles that stream samples. Keep the balance display unavailable for one-channel sensors; do not derive left/right shares. Exclude mySmartBoard from `selectableCases` and all visible strings.

- [ ] **Step 4: Run the focused UI-adjacent tests and a simulator build**

Run: `rtk xcodebuild test -project HangTen.xcodeproj -scheme HangTen -destination 'platform=iOS Simulator,name=iPhone 17 Pro' -only-testing:HangTenTests/AppStoreTests -only-testing:HangTenTests/MotherboardBluetoothServiceTests -only-testing:HangTenTests/MotherboardModelsTests`

Run: `rtk xcodebuild build -project HangTen.xcodeproj -scheme HangTen -destination 'platform=iOS Simulator,name=iPhone 17 Pro'`

Expected: all selected tests pass and the simulator build succeeds.

- [ ] **Step 5: Commit and push**

```sh
rtk git add HangTen/Views/MotherboardViews.swift HangTen/Views/RootView.swift HangTenTests/AppStoreTests.swift HangTenTests/MotherboardBluetoothServiceTests.swift HangTenTests/MotherboardModelsTests.swift
rtk git commit -m "feat: add force sensor profile controls"
rtk git push origin relieved-peacock
```

### Task 4: Run full verification and validate the app on iOS Simulator

**Files:**

- Modify only if verification reveals a failing test or build issue: the exact affected production and test files from Tasks 1–3.

**Interfaces:**

- Consumes the complete profile-aware transport, service, protocol, persistence, and UI implementation.
- Produces fresh full-test, build, and simulator-launch evidence for the completed feature.

- [ ] **Step 1: Run the full test target**

Run: `rtk xcodebuild test -project HangTen.xcodeproj -scheme HangTen -destination 'platform=iOS Simulator,name=iPhone 17 Pro'`

Expected: exit code 0 with no failed tests.

- [ ] **Step 2: Run the app in the simulator and inspect the Force sensor surface**

Run the repository’s `validate-hang-ten-ios` workflow. Confirm the app launches, the Progress surface says "Force sensor", the picker contains Automatic, Tindeq/Progressor, PitchSix Force Board, WH-C06, Entralpi, Climbro, Generic Progressor-compatible, and Generic WH-C06-compatible, and it does not contain mySmartBoard.

- [ ] **Step 3: Re-run focused coverage if any verification fix was needed**

Run the exact failing test target from Step 1 plus the full test target again.

Expected: exit code 0 for both commands.

- [ ] **Step 4: Commit and push verification fixes only when they exist**

```sh
rtk git add HangTen HangTenTests HangTen.xcodeproj
rtk git commit -m "fix: verify multi-device force sensors"
rtk git push origin relieved-peacock
```

When no verification fix is needed, make no empty commit.

## Plan Self-Review

- Spec coverage: Tasks 1–3 implement all six auditable profiles, generic modes, automatic matching, normalized kgf samples, capability-driven controls, persistence compatibility, errors, simulation, and tests. Task 4 verifies the user-visible picker and regression suite. mySmartBoard remains intentionally deferred with documented evidence.
- Placeholder scan: this plan uses concrete files, types, BLE identifiers, packet layouts, commands, test bodies, and commands; no implementation placeholder remains.
- Type consistency: Tasks 2 and 3 consume the exact `ForceSensorProfile`, `ForceSensorCapability`, `ForceSensorDecoder`, `connect(profile:)`, `connectedProfile`, and `capabilities` interfaces produced earlier.
