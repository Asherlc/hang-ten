# Griptonite Motherboard Bluetooth Integration Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use `superpowers:subagent-driven-development` for this plan. Dispatch a fresh implementer subagent for each task, then require a separate task-scoped spec-compliance and code-quality review checkpoint before moving on; after all tasks, run a broad whole-branch review. This workflow is mandatory. Steps use checkbox syntax for tracking.

**Goal:** Add native CoreBluetooth support for the Griptonite Motherboard, show live calibrated force during timer-led workouts, record actual loaded intervals and peaks, and persist session summaries with configurable display settings.

**Architecture:** Keep the BLE protocol parser, threshold recorder, and Codable session models as pure Swift units. Put CoreBluetooth behind a transport adapter and observable service, inject that service through AppStore, and let SwiftUI observe the same service in the Progress card and WorkoutView. The timer remains the sole source of workout progression; incoming measurements are timestamped observations.

**Tech Stack:** Swift 5, iOS 17, SwiftUI, CoreBluetooth, XCTest, the existing hand-maintained Xcode project, and the isolated simulator validation workflow already documented in the repository.

## Global Constraints

- Target iOS 17.0 and keep the existing Swift 5/Xcode 26 project settings.
- Use only Apple frameworks; do not add a JavaScript runtime or third-party BLE dependency.
- Connect only after an explicit user action; do not request Bluetooth permission or connect at launch.
- Target the Griptonite Motherboard Nordic UART service 6E400001-B5A3-F393-E0A9-E50E24DCCA9E, RX 6E400002-B5A3-F393-E0A9-E50E24DCCA9E, and TX 6E400003-B5A3-F393-E0A9-E50E24DCCA9E.
- Enable TX notifications before writing C, wait for calibration rows, then write S30.
- Parse CRLF-framed ASCII with a persistent receive buffer and decode 32-character hexadecimal 16-byte stream reports, including signed 24-bit ADC values.
- Store calibrated measurements canonically as kgf; default display unit is kgf and default detection threshold is 2.5 kgf.
- Keep the workout timer authoritative: Bluetooth never pauses, advances, or changes scheduled step transitions.
- Record derived session results only; do not persist every raw 30 Hz sample.
- Preserve the existing Apple Health completion behavior and do not log an ended, incomplete session.
- Use apply_patch for edits, prefix shell commands with rtk, and commit each completed task.
- Follow test-first cycles: write one focused failing test, run it to confirm the expected failure, implement the smallest passing change, run the focused and full tests, then refactor only while green.

---

## File map

Create these focused files:

- HangTen/Models/MotherboardModels.swift — force units, connection state, raw/calibrated measurement values, detection configuration, load intervals, and Codable session records.
- HangTen/Models/MotherboardProtocol.swift — UUIDs, command construction, line framing, packet decoding, calibration parsing, and interpolation.
- HangTen/Models/MotherboardWorkoutRecorder.swift — threshold/hysteresis state machine and per-step actual-load results.
- HangTen/Models/MotherboardBluetoothService.swift — CoreBluetooth transport adapter and observable Motherboard connection service.
- HangTen/Models/WorkoutSessionStore.swift — injected Codable local history store.
- HangTen/Views/MotherboardViews.swift — Training sensor card, live meter, Settings content, and force formatting.
- HangTen/Views/WorkoutSummaryView.swift — saved-session summary UI.
- HangTenTests/... — unit tests for each pure component and the injected transport coordinator.

Modify these existing files:

- HangTen.xcodeproj/project.pbxproj — add all production files, the HangTenTests unit-test target, Bluetooth usage text, and the test target build settings.
- HangTen.xcodeproj/xcshareddata/xcschemes/HangTen.xcscheme — add the shared Test action for HangTenTests so xcodebuild test runs the new target.
- HangTen/HangTenApp.swift — construct one shared Motherboard service, settings store, and session store and inject them into the app environment/store.
- HangTen/Models/AppStore.swift — accept injected Motherboard/session dependencies, expose session history, and save force summaries along with existing completion/HealthKit behavior.
- HangTen/Views/RootView.swift — add Progress navigation to Settings/Training sensor, observe measurements in WorkoutView, and present the completion summary.
- README.md — document Motherboard support, physical-device validation, and the protocol reference.
- docs/IOS_RUNTIME_SERVICES.md — document Bluetooth permission, timer/measurement separation, disconnect behavior, and simulator limitations.

## Task 1: Add the XCTest target and shared scheme

**Files:**

- Create: HangTenTests/TestTargetSmokeTests.swift
- Modify: HangTen.xcodeproj/project.pbxproj
- Create: HangTen.xcodeproj/xcshareddata/xcschemes/HangTen.xcscheme

**Interfaces:**

- Produces a buildable HangTenTests XCTest bundle that imports the app as @testable import HangTen.
- Later tasks use rtk xcodebuild test -project HangTen.xcodeproj -scheme HangTen -destination 'platform=iOS Simulator,name=iPhone 17 Pro'.

- [x] **Step 1: Write the test-target smoke test**

Create the test before any feature production code:

~~~swift
import XCTest
@testable import HangTen

final class TestTargetSmokeTests: XCTestCase {
    func testUnitTestTargetLoadsTheHangTenModule() {
        XCTAssertEqual(1 + 1, 2)
    }
}
~~~

- [x] **Step 2: Run the test and verify the target is missing**

Run:

~~~sh
rtk xcodebuild test -project HangTen.xcodeproj -scheme HangTen \
  -destination 'platform=iOS Simulator,name=iPhone 17 Pro' \
  -only-testing:HangTenTests/TestTargetSmokeTests/testUnitTestTargetLoadsTheHangTenModule
~~~

Expected: failure because HangTenTests is not yet present in the project.

- [x] **Step 3: Add the test target and shared Test action**

Add a HangTenTests group, file reference, build-file entry, and native unit-test target to the hand-maintained project. Configure it with GENERATE_INFOPLIST_FILE = YES, PRODUCT_BUNDLE_IDENTIFIER = com.hangten.training.tests, IPHONEOS_DEPLOYMENT_TARGET = 17.0, SWIFT_VERSION = 5.0, TEST_HOST = $(BUILT_PRODUCTS_DIR)/HangTen.app/HangTen, and a dependency on the HangTen app target. Link XCTest.framework in the test target’s Frameworks phase. Add the smoke test to the test target Sources phase.

Create a shared scheme whose Test action builds the HangTen app and runs HangTenTests, with the same iOS Simulator destination used by the repository validation guide.

- [x] **Step 4: Run the focused test and verify it passes**

Run the command from Step 2. Expected: one passing test and no compiler warnings.

- [x] **Step 5: Commit the test infrastructure**

~~~sh
rtk git add HangTenTests HangTen.xcodeproj/project.pbxproj HangTen.xcodeproj/xcshareddata/xcschemes/HangTen.xcscheme
rtk git commit -m "test: add Hang Ten unit test target"
~~~

## Task 2: Add force, settings, and session value types

**Files:**

- Create: HangTenTests/MotherboardModelsTests.swift
- Create: HangTen/Models/MotherboardModels.swift
- Modify: HangTen.xcodeproj/project.pbxproj

**Interfaces:**

Define these app types:

~~~swift
enum MotherboardForceUnit: String, CaseIterable, Codable, Identifiable {
    case kgf
    case lbf
    case newtons

    var id: String { rawValue }
    var label: String { get }
    func value(fromKilogramsForce kgf: Double) -> Double
}

struct MotherboardMeasurement: Codable, Equatable {
    let timestamp: Date
    let sampleNumber: UInt16
    let batteryValue: UInt16
    let sensorLoadsKGF: [Double]
    let aggregateLoadKGF: Double
}

enum MotherboardConnectionState: Equatable {
    case bluetoothUnavailable
    case unauthorized
    case idle
    case scanning
    case connecting
    case calibrating
    case streaming
    case disconnected
    case failed
}

struct MotherboardDetectionConfiguration: Codable, Equatable {
    var thresholdKGF: Double = 2.5
    var releaseRatio: Double = 0.8
    var debounceDuration: TimeInterval = 0.10
    var mergeGapDuration: TimeInterval = 0.15
}

struct LoadInterval: Codable, Equatable {
    let start: TimeInterval
    let end: TimeInterval
    var duration: TimeInterval { max(0, end - start) }
}

struct WorkoutStepMeasurement: Codable, Equatable {
    let stepID: String
    let plannedActiveDuration: TimeInterval
    let intervals: [LoadInterval]
    let peakLoadKGF: Double?
    let sampleCount: Int
    let status: Status
    enum Status: String, Codable { case measured, unmeasured, interrupted }
    var actualLoadedDuration: TimeInterval { get }
}

struct WorkoutSessionRecord: Codable, Equatable, Identifiable {
    let id: UUID
    let planID: String
    let planTitle: String
    let recordedAt: Date
    let startDate: Date
    let endDate: Date
    let motherboardIdentifier: String?
    let batteryValue: UInt16?
    let steps: [WorkoutStepMeasurement]
}
~~~

Also add MotherboardSettingsStore, backed by an injected UserDefaults, with @Published var forceUnit (default .kgf) and @Published var thresholdKGF (default 2.5). Keep all saved/session values canonical in kgf.

- [x] **Step 1: Write failing model and settings tests**

~~~swift
import XCTest
@testable import HangTen

final class MotherboardModelsTests: XCTestCase {
    func testForceUnitConversionUsesKilogramsForceAsCanonicalValue() {
        XCTAssertEqual(MotherboardForceUnit.kgf.value(fromKilogramsForce: 2), 2, accuracy: 0.0001)
        XCTAssertEqual(MotherboardForceUnit.lbf.value(fromKilogramsForce: 2), 4.40925, accuracy: 0.0001)
        XCTAssertEqual(MotherboardForceUnit.newtons.value(fromKilogramsForce: 2), 19.6133, accuracy: 0.0001)
    }

    func testSettingsUseDefaultsAndRoundTripThroughUserDefaults() {
        let defaults = UserDefaults(suiteName: "MotherboardModelsTests")!
        defaults.removePersistentDomain(forName: "MotherboardModelsTests")
        let first = MotherboardSettingsStore(defaults: defaults)
        XCTAssertEqual(first.forceUnit, .kgf)
        XCTAssertEqual(first.thresholdKGF, 2.5, accuracy: 0.0001)

        first.forceUnit = .newtons
        first.thresholdKGF = 4.25
        let second = MotherboardSettingsStore(defaults: defaults)
        XCTAssertEqual(second.forceUnit, .newtons)
        XCTAssertEqual(second.thresholdKGF, 4.25, accuracy: 0.0001)
    }

    func testSessionRecordRoundTripsThroughCodable() throws {
        let record = WorkoutSessionRecord(
            id: UUID(uuidString: "AAAAAAAA-BBBB-CCCC-DDDD-EEEEEEEEEEEE")!,
            planID: "plan",
            planTitle: "Test plan",
            recordedAt: Date(timeIntervalSince1970: 100),
            startDate: Date(timeIntervalSince1970: 0),
            endDate: Date(timeIntervalSince1970: 600),
            motherboardIdentifier: "Motherboard-1",
            batteryValue: 80,
            steps: [WorkoutStepMeasurement(
                stepID: "step-1",
                plannedActiveDuration: 7,
                intervals: [LoadInterval(start: 1, end: 6)],
                peakLoadKGF: 12,
                sampleCount: 150,
                status: .measured
            )]
        )
        let data = try JSONEncoder().encode(record)
        XCTAssertEqual(try JSONDecoder().decode(WorkoutSessionRecord.self, from: data), record)
    }
}
~~~

- [x] **Step 2: Run the tests to verify the expected missing-type failures**

~~~sh
rtk xcodebuild test -project HangTen.xcodeproj -scheme HangTen \
  -destination 'platform=iOS Simulator,name=iPhone 17 Pro' \
  -only-testing:HangTenTests/MotherboardModelsTests
~~~

Expected: compilation failures naming the not-yet-defined Motherboard types.

- [x] **Step 3: Implement the models and settings store**

Use 9.80665 N per kgf and 2.20462262185 lbf per kgf. Store settings under stable keys motherboard.forceUnit and motherboard.thresholdKGF; decode invalid stored values back to the defaults. Clamp a loaded threshold below 0.1 kgf back to 2.5 kgf so corrupted defaults cannot create an always-on detector.

- [x] **Step 4: Run focused and full tests**

Run both the model test command and:

~~~sh
rtk xcodebuild test -project HangTen.xcodeproj -scheme HangTen \
  -destination 'platform=iOS Simulator,name=iPhone 17 Pro'
~~~

Expected: all tests pass.

- [x] **Step 5: Commit the value types**

~~~sh
rtk git add HangTen/Models/MotherboardModels.swift HangTenTests/MotherboardModelsTests.swift HangTen.xcodeproj/project.pbxproj
rtk git commit -m "feat: add Motherboard measurement models"
~~~

## Task 3: Implement the pure Motherboard protocol parser and calibration

**Files:**

- Create: HangTenTests/MotherboardProtocolTests.swift
- Create: HangTen/Models/MotherboardProtocol.swift
- Modify: HangTen.xcodeproj/project.pbxproj

**Interfaces:**

~~~swift
struct MotherboardCalibrationRow: Equatable {
    let sensor: Int
    let calibrationPoint: Int
    let massKGF: Double
    let adc: Int32
}

struct MotherboardRawPacket: Equatable {
    let sampleNumber: UInt16
    let batteryValue: UInt16
    let adcValues: [Int32]
}

enum MotherboardProtocolEvent: Equatable {
    case calibration(MotherboardCalibrationRow)
    case rawPacket(MotherboardRawPacket, timestamp: Date)
    case streamStarted(rate: Int)
    case error(String)
}

struct MotherboardProtocolParser {
    init()
    mutating func append(_ data: Data, receivedAt: Date) -> [MotherboardProtocolEvent]
}

struct MotherboardCalibration: Equatable {
    init(rows: [MotherboardCalibrationRow])
    func massKGF(sensor: Int, adc: Int32) -> Double?
}

enum MotherboardProtocol {
    static let serviceUUID: UUID
    static let rxUUID: UUID
    static let txUUID: UUID
    static func command(_ text: String) -> Data
    static func streamCommand(rate: Int) -> Data
    static func decode(_ packet: MotherboardRawPacket, timestamp: Date, calibration: MotherboardCalibration, tareKGF: [Double]) -> MotherboardMeasurement
}
~~~

- [x] **Step 1: Write failing parser tests**

Use the 16-byte fixture 34126400020100feffff030201000000, which represents sample 0x1234, battery 0x0064, ADC values 0x000102, -2, 0x010203, and 0.

~~~swift
import XCTest
@testable import HangTen

final class MotherboardProtocolTests: XCTestCase {
    func testParserBuffersFragmentsAndEmitsCompleteRawPacket() {
        let date = Date(timeIntervalSince1970: 42)
        var parser = MotherboardProtocolParser()
        XCTAssertEqual(parser.append(Data("34126400020100fe".utf8), receivedAt: date), [])

        let events = parser.append(Data("ffff030201000000\r\n".utf8), receivedAt: date)
        XCTAssertEqual(events, [.rawPacket(
            MotherboardRawPacket(sampleNumber: 0x1234, batteryValue: 0x0064, adcValues: [0x000102, -2, 0x010203, 0]),
            timestamp: date
        )])
    }

    func testParserHandlesCalibrationStreamAndDeviceErrors() {
        var parser = MotherboardProtocolParser()
        let data = Data("0,1,2.5,100\r\nStream:30\r\nError VAL\r\n".utf8)
        XCTAssertEqual(parser.append(data, receivedAt: Date(timeIntervalSince1970: 1)), [
            .calibration(MotherboardCalibrationRow(sensor: 0, calibrationPoint: 1, massKGF: 2.5, adc: 100)),
            .streamStarted(rate: 30),
            .error("Error VAL")
        ])
    }

    func testCalibrationInterpolatesAndSubtractsPerSensorTare() {
        let calibration = MotherboardCalibration(rows: [
            MotherboardCalibrationRow(sensor: 0, calibrationPoint: 0, massKGF: 0, adc: 0),
            MotherboardCalibrationRow(sensor: 0, calibrationPoint: 1, massKGF: 10, adc: 100)
        ])
        let packet = MotherboardRawPacket(sampleNumber: 1, batteryValue: 2, adcValues: [50, 0, 0, 0])
        let result = MotherboardProtocol.decode(
            packet,
            timestamp: Date(timeIntervalSince1970: 1),
            calibration: calibration,
            tareKGF: [1, 0, 0, 0]
        )
        XCTAssertEqual(result.sensorLoadsKGF[0], 4, accuracy: 0.0001)
        XCTAssertEqual(result.aggregateLoadKGF, 4, accuracy: 0.0001)
    }
}
~~~

- [x] **Step 2: Run the focused tests and verify they fail for missing parser types**

~~~sh
rtk xcodebuild test -project HangTen.xcodeproj -scheme HangTen \
  -destination 'platform=iOS Simulator,name=iPhone 17 Pro' \
  -only-testing:HangTenTests/MotherboardProtocolTests
~~~

Expected: compilation failures because the parser and protocol types do not exist.

- [x] **Step 3: Implement framing, decoding, and calibration**

Append incoming bytes to a Data buffer, split only on CRLF, and leave the final incomplete line in the buffer. Parse calibration rows with four fields and reject rows whose sensor is outside 0...3. Decode the hexadecimal frame only when it has exactly 32 hex characters. Implement signed 24-bit decoding by sign-extending bit 23 into an Int32. Sort calibration points by ADC before interpolating; use the first/last point for values outside the calibrated range. Return four sensor loads, subtract the supplied four-element tare vector, clamp aggregate load at zero, and keep the per-sensor values for distribution display.

Build commands with UTF-8 bytes and clamp streamCommand(rate:) to a positive decimal rate; streamCommand(rate: 30) must equal Data("S30".utf8).

- [x] **Step 4: Run focused and full tests**

Run the protocol test command and the full xcodebuild test command from Task 2. Expected: all parser, model, and existing tests pass.

- [x] **Step 5: Commit the parser**

~~~sh
rtk git add HangTen/Models/MotherboardProtocol.swift HangTenTests/MotherboardProtocolTests.swift HangTen.xcodeproj/project.pbxproj
rtk git commit -m "feat: parse Motherboard force packets"
~~~

## Task 4: Add threshold detection and timer-bound measurement recording

**Files:**

- Create: HangTenTests/MotherboardWorkoutRecorderTests.swift
- Create: HangTen/Models/MotherboardWorkoutRecorder.swift
- Modify: HangTen.xcodeproj/project.pbxproj

**Interfaces:**

~~~swift
struct MotherboardWorkoutRecorder {
    init(configuration: MotherboardDetectionConfiguration = .init())
    var currentLoadKGF: Double? { get }
    var currentPeakLoadKGF: Double? { get }
    var isLoaded: Bool { get }
    mutating func consume(
        _ measurement: MotherboardMeasurement,
        stepID: String,
        plannedActiveDuration: TimeInterval,
        workoutElapsed: TimeInterval,
        isActive: Bool
    )
    mutating func endStep(stepID: String, at workoutElapsed: TimeInterval, status: WorkoutStepMeasurement.Status = .measured)
    mutating func interrupt(at workoutElapsed: TimeInterval)
    mutating func finish(at workoutElapsed: TimeInterval) -> [WorkoutStepMeasurement]
}
~~~

- [x] **Step 1: Write failing recorder tests**

~~~swift
import XCTest
@testable import HangTen

final class MotherboardWorkoutRecorderTests: XCTestCase {
    private func measurement(load: Double, at time: TimeInterval) -> MotherboardMeasurement {
        MotherboardMeasurement(
            timestamp: Date(timeIntervalSince1970: time),
            sampleNumber: UInt16(time),
            batteryValue: 90,
            sensorLoadsKGF: [load, 0, 0, 0],
            aggregateLoadKGF: load
        )
    }

    func testLoadedIntervalsUseMeasurementTimesWithoutChangingScheduledDuration() {
        var recorder = MotherboardWorkoutRecorder(configuration: .init(thresholdKGF: 2.5, releaseRatio: 0.8, debounceDuration: 0, mergeGapDuration: 0))
        recorder.consume(measurement(load: 3, at: 1), stepID: "step", plannedActiveDuration: 7, workoutElapsed: 1, isActive: true)
        recorder.consume(measurement(load: 3, at: 6), stepID: "step", plannedActiveDuration: 7, workoutElapsed: 6, isActive: true)
        recorder.consume(measurement(load: 0, at: 7), stepID: "step", plannedActiveDuration: 7, workoutElapsed: 7, isActive: true)

        let result = recorder.finish(at: 7)
        XCTAssertEqual(result[0].plannedActiveDuration, 7)
        XCTAssertEqual(result[0].intervals, [LoadInterval(start: 1, end: 7)])
        XCTAssertEqual(result[0].intervals[0].duration, 6, accuracy: 0.0001)
        XCTAssertEqual(result[0].peakLoadKGF, 3, accuracy: 0.0001)
    }

    func testRestSamplesDoNotCreateIntervalsAndDisconnectMarksLaterStepInterrupted() {
        var recorder = MotherboardWorkoutRecorder(configuration: .init(thresholdKGF: 2.5, releaseRatio: 0.8, debounceDuration: 0, mergeGapDuration: 0))
        recorder.consume(measurement(load: 10, at: 1), stepID: "hang", plannedActiveDuration: 5, workoutElapsed: 1, isActive: true)
        recorder.endStep(stepID: "hang", at: 2)
        recorder.consume(measurement(load: 10, at: 3), stepID: "rest", plannedActiveDuration: 5, workoutElapsed: 3, isActive: false)
        recorder.interrupt(at: 4)

        let result = recorder.finish(at: 4)
        XCTAssertEqual(result.count, 2)
        XCTAssertEqual(result[0].status, .measured)
        XCTAssertEqual(result[1].status, .interrupted)
        XCTAssertTrue(result[1].intervals.isEmpty)
    }
}
~~~

- [x] **Step 2: Run the focused tests and verify the recorder is missing**

~~~sh
rtk xcodebuild test -project HangTen.xcodeproj -scheme HangTen \
  -destination 'platform=iOS Simulator,name=iPhone 17 Pro' \
  -only-testing:HangTenTests/MotherboardWorkoutRecorderTests
~~~

Expected: compilation failures naming the missing recorder.

- [x] **Step 3: Implement the recorder state machine**

Keep a dictionary keyed by step ID plus an ordered step list. On the first sample at or above thresholdKGF, start a pending/active interval. Require debounceDuration of qualifying samples before committing a pending start. End the interval after debounceDuration below thresholdKGF × releaseRatio; merge a new start into the prior interval when the gap is no longer than mergeGapDuration. Update peak and sample count only for active samples. endStep closes an open interval at the boundary and writes .measured; interrupt closes any open interval and writes .interrupted for the current step; finish flushes and returns results in first-seen step order. A sample with isActive == false must not start or extend an interval.

- [x] **Step 4: Run focused and full tests**

Run the recorder test command and the full test command. Expected: all tests pass, including threshold hysteresis and step-boundary behavior.

- [x] **Step 5: Commit the recorder**

~~~sh
rtk git add HangTen/Models/MotherboardWorkoutRecorder.swift HangTenTests/MotherboardWorkoutRecorderTests.swift HangTen.xcodeproj/project.pbxproj
rtk git commit -m "feat: record actual Motherboard load intervals"
~~~

## Task 5: Add the CoreBluetooth transport and Motherboard service

**Files:**

- Create: HangTenTests/MotherboardBluetoothServiceTests.swift
- Create: HangTen/Models/MotherboardBluetoothService.swift
- Modify: HangTen.xcodeproj/project.pbxproj build settings

**Interfaces:**

Keep CoreBluetooth delegate details behind these app-level interfaces:

~~~swift
enum MotherboardBluetoothPowerState: Equatable {
    case unknown, resetting, unsupported, unauthorized, poweredOff, poweredOn
}

struct MotherboardDiscoveredDevice: Equatable, Identifiable {
    let id: UUID
    let name: String
}

enum MotherboardTransportEvent {
    case powerChanged(MotherboardBluetoothPowerState)
    case discovered(MotherboardDiscoveredDevice)
    case connected
    case characteristicsReady
    case notification(Data, Date)
    case disconnected(String?)
}

protocol MotherboardTransport: AnyObject {
    var eventHandler: ((MotherboardTransportEvent) -> Void)? { get set }
    func startScan()
    func stopScan()
    func connect(to device: MotherboardDiscoveredDevice)
    func disconnect()
    func setTXNotificationsEnabled(_ enabled: Bool)
    func write(_ data: Data)
}

@MainActor
final class MotherboardBluetoothService: ObservableObject {
    @Published private(set) var state: MotherboardConnectionState
    @Published private(set) var latestMeasurement: MotherboardMeasurement?
    @Published private(set) var batteryValue: UInt16?
    @Published private(set) var lastError: String?

    init(transport: MotherboardTransport, parser: MotherboardProtocolParser = .init())
    func connect()
    func disconnect()
    func startStreaming()
    func stopStreaming()
    func tare()
}
~~~

Implement CoreBluetoothMotherboardTransport with CBCentralManagerDelegate and CBPeripheralDelegate. Scan with the NUS service UUID, accept only a discovered name equal to Motherboard when a name is supplied, discover the NUS service, discover RX/TX characteristics, enable TX notifications, and map delegate callbacks to MotherboardTransportEvent. Use .withResponse when the RX characteristic supports it and .withoutResponse otherwise.

- [x] **Step 1: Write failing service/coordinator tests using a fake transport**

~~~swift
import XCTest
@testable import HangTen

@MainActor
final class MotherboardBluetoothServiceTests: XCTestCase {
    func testConnectCalibratesBeforeStartingThirtyHertzStream() {
        let transport = FakeMotherboardTransport()
        let service = MotherboardBluetoothService(transport: transport)

        service.connect()
        XCTAssertEqual(transport.commands, [])
        transport.emit(.powerChanged(.poweredOn))
        transport.emit(.discovered(MotherboardDiscoveredDevice(id: UUID(), name: "Motherboard")))
        transport.emit(.connected)
        transport.emit(.characteristicsReady)
        XCTAssertEqual(transport.commands, [Data("C".utf8)])

        for index in 0..<16 {
            transport.emit(.notification(Data("\(index / 4),\(index % 4),1,\r\n".utf8), Date(timeIntervalSince1970: Double(index))))
        }
        XCTAssertEqual(transport.commands, [Data("C".utf8), Data("S30".utf8)])
    }

    func testDisconnectPublishesUnavailableStateWithoutInventingMeasurement() {
        let transport = FakeMotherboardTransport()
        let service = MotherboardBluetoothService(transport: transport)
        transport.emit(.disconnected("lost"))
        XCTAssertEqual(service.state, .disconnected)
        XCTAssertNil(service.latestMeasurement)
        XCTAssertEqual(service.lastError, "lost")
    }
}

private final class FakeMotherboardTransport: MotherboardTransport {
    var eventHandler: ((MotherboardTransportEvent) -> Void)?
    var commands: [Data] = []
    func startScan() {}
    func stopScan() {}
    func connect(to device: MotherboardDiscoveredDevice) {}
    func disconnect() {}
    func setTXNotificationsEnabled(_ enabled: Bool) {}
    func write(_ data: Data) { commands.append(data) }
    func emit(_ event: MotherboardTransportEvent) { eventHandler?(event) }
}
~~~

- [x] **Step 2: Run the focused tests and verify service types are missing**

~~~sh
rtk xcodebuild test -project HangTen.xcodeproj -scheme HangTen \
  -destination 'platform=iOS Simulator,name=iPhone 17 Pro' \
  -only-testing:HangTenTests/MotherboardBluetoothServiceTests
~~~

Expected: compilation failures because the transport and service do not yet exist.

- [x] **Step 3: Implement the service and transport**

Wire the transport event handler in the service initializer. connect() calls startScan(), characteristicsReady enables notifications and writes C, and the service writes S30 only after it has received all four sensors × four calibration points. For each raw-packet event, run MotherboardProtocol.decode with the current calibration and four-element tare vector, publish the measurement, and update batteryValue. disconnect() stops scanning/streaming and clears the selected peripheral. Map power states and transport failures to the documented connection states without throwing into SwiftUI.

Add NSBluetoothAlwaysUsageDescription = "Hang Ten uses Bluetooth to receive live force measurements from your Griptonite Motherboard." to both Debug and Release target build settings. Do not add background Bluetooth modes because the existing workout pauses when inactive.

- [x] **Step 4: Run focused and full tests**

Run the service test command and the full test command. Expected: all tests pass, including command ordering and no-measurement-on-disconnect.

- [x] **Step 5: Commit the BLE service**

~~~sh
rtk git add HangTen/Models/MotherboardBluetoothService.swift HangTenTests/MotherboardBluetoothServiceTests.swift HangTen.xcodeproj/project.pbxproj
rtk git commit -m "feat: connect to Motherboard over CoreBluetooth"
~~~

## Task 6: Persist summaries and inject shared app dependencies

**Files:**

- Create: HangTenTests/WorkoutSessionStoreTests.swift
- Create: HangTen/Models/WorkoutSessionStore.swift
- Modify: HangTen/Models/AppStore.swift
- Modify: HangTen/HangTenApp.swift
- Modify: HangTen.xcodeproj/project.pbxproj

**Interfaces:**

~~~swift
protocol WorkoutSessionStoring: AnyObject {
    var sessions: [WorkoutSessionRecord] { get }
    func append(_ session: WorkoutSessionRecord)
}

final class WorkoutSessionStore: WorkoutSessionStoring {
    init(defaults: UserDefaults = .standard)
    var sessions: [WorkoutSessionRecord] { get }
    func append(_ session: WorkoutSessionRecord)
}
~~~

Update AppStore to accept MotherboardBluetoothService, MotherboardSettingsStore, and WorkoutSessionStoring dependencies with production defaults. Add @Published private(set) var sessionHistory. Change completion to:

~~~swift
func markSessionComplete(
    _ plan: TrainingPlan,
    startDate: Date,
    endDate: Date,
    session: WorkoutSessionRecord? = nil
)
~~~

Append a supplied session before incrementing the existing counter; retain the existing Apple Health write and error behavior.

- [x] **Step 1: Write failing store tests**

~~~swift
import XCTest
@testable import HangTen

final class WorkoutSessionStoreTests: XCTestCase {
    func testAppendPersistsSessionsAcrossStoreInstances() {
        let suite = "WorkoutSessionStoreTests"
        let defaults = UserDefaults(suiteName: suite)!
        defaults.removePersistentDomain(forName: suite)
        let session = WorkoutSessionRecord(
            id: UUID(), planID: "plan", planTitle: "Plan",
            recordedAt: Date(timeIntervalSince1970: 10),
            startDate: Date(timeIntervalSince1970: 0),
            endDate: Date(timeIntervalSince1970: 10),
            motherboardIdentifier: nil, batteryValue: nil, steps: []
        )
        WorkoutSessionStore(defaults: defaults).append(session)
        XCTAssertEqual(WorkoutSessionStore(defaults: defaults).sessions, [session])
    }
}
~~~

- [x] **Step 2: Run the focused test and verify the store is missing**

~~~sh
rtk xcodebuild test -project HangTen.xcodeproj -scheme HangTen \
  -destination 'platform=iOS Simulator,name=iPhone 17 Pro' \
  -only-testing:HangTenTests/WorkoutSessionStoreTests
~~~

Expected: compilation failure because WorkoutSessionStore is not defined.

- [x] **Step 3: Implement the store and AppStore injection**

Persist the array as JSON under workout.sessionHistory. If decoding fails, expose an empty history and replace the invalid value on the next append. In HangTenApp, construct one MotherboardBluetoothService using CoreBluetoothMotherboardTransport, one settings store, and one session store; inject them into AppStore so Progress and Workout observe the same connection and history.

- [x] **Step 4: Run focused and full tests**

Run the store test and full suite. Expected: existing AppStore/HealthKit behavior still compiles and all tests pass.

- [x] **Step 5: Commit persistence and dependency injection**

~~~sh
rtk git add HangTen/Models/WorkoutSessionStore.swift HangTen/Models/AppStore.swift HangTen/HangTenApp.swift HangTenTests/WorkoutSessionStoreTests.swift HangTen.xcodeproj/project.pbxproj
rtk git commit -m "feat: persist Motherboard workout summaries"
~~~

## Task 7: Add Training sensor, Settings, and force-formatting UI

**Files:**

- Create: HangTen/Views/MotherboardViews.swift
- Modify: HangTen/Views/RootView.swift
- Modify: HangTen.xcodeproj/project.pbxproj

**Interfaces:**

~~~swift
struct MotherboardCard: View {
    @ObservedObject var service: MotherboardBluetoothService
    @ObservedObject var settings: MotherboardSettingsStore
}

struct MotherboardSettingsView: View {
    @ObservedObject var service: MotherboardBluetoothService
    @ObservedObject var settings: MotherboardSettingsStore
}

struct MotherboardMeterView: View {
    let measurement: MotherboardMeasurement?
    let peakLoadKGF: Double?
    let actualLoadedTime: TimeInterval
    let plannedActiveDuration: TimeInterval
    let unit: MotherboardForceUnit
    let state: MotherboardConnectionState
}
~~~

- [x] **Step 1: Add the UI files and project references with no behavior change**

Add the new Swift file references/build entries and compile the app. Keep the existing tab layout unchanged until the card is wired.

- [x] **Step 2: Implement the Training sensor card**

Add a card below boardInfo in ProgressDashboardView. Render the state label, latest formatted force, battery value, and the last error. The primary action calls service.connect() from idle/disconnected/failed and service.disconnect() while connected/streaming. If Bluetooth is unauthorized or powered off, show explanatory text and use UIApplication.openSettingsURLString for the existing app-settings behavior.

- [x] **Step 3: Implement Settings navigation and controls**

Add a gear toolbar button to ProgressDashboardView that pushes MotherboardSettingsView. Use a Picker for .kgf, .lbf, and .newtons; use a decimal Slider/stepper bound to settings.thresholdKGF; show the canonical kgf threshold alongside the converted display value; and add a Tare button that calls service.tare() only when streaming. Changing a setting must update UserDefaults through MotherboardSettingsStore.

- [x] **Step 4: Build and review the UI without Bluetooth hardware**

~~~sh
rtk xcodebuild build -project HangTen.xcodeproj -scheme HangTen \
  -sdk iphonesimulator -configuration Debug CODE_SIGNING_ALLOWED=NO
~~~

Expected: the app compiles with no new warnings. Resolve SwiftUI type-checking issues before proceeding.

- [x] **Step 5: Commit the sensor and settings UI**

~~~sh
rtk git add HangTen/Views/MotherboardViews.swift HangTen/Views/RootView.swift HangTen.xcodeproj/project.pbxproj
rtk git commit -m "feat: add Motherboard sensor settings"
~~~

## Task 8: Integrate live measurements into timer-led workouts and summaries

**Files:**

- Create: HangTen/Views/WorkoutSummaryView.swift
- Modify: HangTen/Views/RootView.swift
- Modify: HangTen.xcodeproj/project.pbxproj
- Create or extend: HangTenTests/WorkoutSummaryTests.swift

**Interfaces:**

~~~swift
struct WorkoutSummaryView: View {
    let session: WorkoutSessionRecord
    let unit: MotherboardForceUnit
    let onSave: () -> Void
    let onDiscard: () -> Void
}
~~~

- [x] **Step 1: Write failing summary-formatting tests**

Add pure formatting helpers in MotherboardModels.swift or WorkoutSummaryView.swift only after the test is written:

~~~swift
import XCTest
@testable import HangTen

final class WorkoutSummaryTests: XCTestCase {
    func testSummaryUsesActualLoadedDurationAndPeakInSelectedUnit() {
        let step = WorkoutStepMeasurement(
            stepID: "step", plannedActiveDuration: 7,
            intervals: [LoadInterval(start: 1, end: 4)],
            peakLoadKGF: 2, sampleCount: 20, status: .measured
        )
        XCTAssertEqual(step.actualLoadedDuration, 3, accuracy: 0.0001)
        XCTAssertEqual(MotherboardForceUnit.lbf.value(fromKilogramsForce: step.peakLoadKGF!), 4.40925, accuracy: 0.0001)
    }
}
~~~

- [x] **Step 2: Run the focused test and verify the summary helper is missing**

~~~sh
rtk xcodebuild test -project HangTen.xcodeproj -scheme HangTen \
  -destination 'platform=iOS Simulator,name=iPhone 17 Pro' \
  -only-testing:HangTenTests/WorkoutSummaryTests
~~~

Expected: compilation failure because actualLoadedDuration is not yet defined.

- [x] **Step 3: Implement summary data and view**

Add actualLoadedDuration as the sum of interval durations. Render a summary header with plan/date, then one row per step showing planned duration, actual loaded duration, interval count/details when there is more than one, peak force, and .unmeasured/.interrupted status. The Save action is the only path that invokes the existing AppStore completion method; Discard dismisses without incrementing sessions or writing Apple Health.

- [x] **Step 4: Attach the recorder to WorkoutView**

Observe the shared MotherboardBluetoothService.latestMeasurement in WorkoutView. For each new measurement, calculate the workout elapsed time using the sample timestamp and existing startedAt/pausedElapsed state, find the current WorkoutStep, and call recorder.consume only when countdown is zero, the routine is not complete, and isRestInterval is false. Keep the existing TimelineView clock and audio code unchanged apart from passing live meter values into portrait and landscape layouts.

When the routine reaches completion, call recorder.finish(at: plan.duration), construct a WorkoutSessionRecord with the service identifier/battery and plan steps, then present WorkoutSummaryView. On summary Save, call store.markSessionComplete(plan:startDate:endDate:session:) and dismiss. On WorkoutView.onDisappear, call recorder.interrupt only for an active unfinished session and never call the completion path.

- [x] **Step 5: Add the live meter to both layouts**

Place MotherboardMeterView in the existing portrait cue stack and landscape lower row. Display current/peak force in the selected unit, actual loaded / planned active time, and a compact connection status. If no measurement exists, show “Not measured”; do not disable Start, Pause, End, or Log session.

- [x] **Step 6: Run focused and full tests**

Run summary tests and the full XCTest command. Expected: all tests pass and the app builds in Debug.

- [x] **Step 7: Commit workout integration**

~~~sh
rtk git add HangTen/Views/WorkoutSummaryView.swift HangTen/Views/RootView.swift HangTenTests/WorkoutSummaryTests.swift HangTen.xcodeproj/project.pbxproj
rtk git commit -m "feat: show actual Motherboard load in workouts"
~~~

## Task 9: Add deterministic simulator review support and documentation

**Files:**

- Create: HangTen/Models/SimulatedMotherboardTransport.swift
- Modify: HangTen/HangTenApp.swift
- Modify: HangTen/Views/RootView.swift
- Modify: README.md
- Modify: docs/IOS_RUNTIME_SERVICES.md
- Modify: HangTen.xcodeproj/project.pbxproj
- Create or extend: HangTenTests/SimulatedMotherboardTransportTests.swift

**Interfaces:**

~~~swift
#if DEBUG
final class SimulatedMotherboardTransport: MotherboardTransport {
    init(samples: [MotherboardMeasurement] = SimulatedMotherboardTransport.defaultSamples)
    static let defaultSamples: [MotherboardMeasurement]
}
#endif
~~~

- [x] **Step 1: Write the simulator fixture test**

~~~swift
#if DEBUG
import XCTest
@testable import HangTen

final class SimulatedMotherboardTransportTests: XCTestCase {
    func testDefaultFixtureCyclesLoadedAndUnloadedSamples() {
        let samples = SimulatedMotherboardTransport.defaultSamples
        XCTAssertFalse(samples.isEmpty)
        XCTAssertTrue(samples.contains { $0.aggregateLoadKGF >= 2.5 })
        XCTAssertTrue(samples.contains { $0.aggregateLoadKGF < 2.0 })
    }
}
#endif
~~~

- [x] **Step 2: Run the focused test and verify the fixture is missing**

~~~sh
rtk xcodebuild test -project HangTen.xcodeproj -scheme HangTen \
  -destination 'platform=iOS Simulator,name=iPhone 17 Pro' \
  -only-testing:HangTenTests/SimulatedMotherboardTransportTests
~~~

Expected: compilation failure because the DEBUG transport is not defined.

- [x] **Step 3: Implement the deterministic transport and review route**

Make the fixture emit a fixed sequence of unloaded, loaded, peak, and unloaded measurements at stable timestamps. When HANGTEN_REVIEW_MOTHERBOARD=1 is set in DEBUG, construct MotherboardBluetoothService with the simulated transport and make the Progress card show Connected/Streaming without requiring system Bluetooth. Keep production builds on CoreBluetoothMotherboardTransport regardless of the environment variable.

- [x] **Step 4: Document runtime behavior and limitations**

Add a README “Motherboard sensor” bullet and link to the protocol notes. In docs/IOS_RUNTIME_SERVICES.md, document the user-initiated Bluetooth permission flow, notification buffering, calibration, timer-led recording, disconnect/unmeasured behavior, DEBUG simulator route, and physical-device validation requirement. State that the protocol is reverse-engineered and not an official manufacturer SDK.

- [ ] **Step 5: Run simulator build and visual review** *(blocked: the dedicated simulator rendered blank/boot-spinner surfaces; the simulator build passed, but no visual pass is claimed.)*

Follow docs/IOS_SIMULATOR_VALIDATION.md and the repository’s validate-hang-ten-ios skill. Use an isolated simulator and HANGTEN_REVIEW_MOTHERBOARD=1 to verify:

- Progress shows the connected sensor card and Settings navigation;
- kgf/lbf/N formatting and threshold changes persist after relaunch;
- portrait and landscape workout layouts show current/peak/actual time;
- a simulated completed routine presents measured and unmeasured summary states;
- disconnect/error state leaves the timer controls usable.

- [x] **Step 6: Commit simulator support and docs**

~~~sh
rtk git add HangTen/Models/SimulatedMotherboardTransport.swift HangTen/HangTenApp.swift HangTen/Views/RootView.swift README.md docs/IOS_RUNTIME_SERVICES.md HangTenTests/SimulatedMotherboardTransportTests.swift HangTen.xcodeproj/project.pbxproj
rtk git commit -m "docs: add Motherboard simulator review flow"
~~~

## Task 10: Final verification and physical-device handoff

**Files:**

- Modify only files required by verification fixes; do not broaden the feature.

- [x] **Step 1: Run the complete unit-test suite**

~~~sh
rtk xcodebuild test -project HangTen.xcodeproj -scheme HangTen \
  -destination 'platform=iOS Simulator,name=iPhone 17 Pro'
~~~

Expected: all XCTest cases pass with no warnings.

- [x] **Step 2: Run the standard simulator Debug build**

~~~sh
rtk xcodebuild -project HangTen.xcodeproj -scheme HangTen \
  -sdk iphonesimulator -configuration Debug build
~~~

Expected: a successful simulator Debug build according to the local environment.

- [ ] **Step 3: Run the isolated visual validation** *(blocked: the dedicated simulator rendered blank/boot-spinner surfaces; no visual pass is claimed.)*

Use the repository’s isolated simulator guide and validate-hang-ten-ios skill. Validate portrait, landscape, countdown, pause/resume, session summary, settings, and error states with the DEBUG simulator transport.

- [ ] **Step 4: Validate a real Motherboard on a physical iPhone** *(pending physical-device release-gate validation.)*

With the Motherboard powered and disconnected from Grippy/other apps, verify: Bluetooth permission, discovery by NUS/name, calibration completion, 30 Hz stream, current and peak load, software tare, threshold crossings, multiple hangs in one step, pause/rest exclusion, disconnect recovery, and saved summary values. Confirm that the existing Apple Health workout is still saved only from the completed summary Save path.

- [x] **Step 5: Review the final diff and commit any verification-only fixes**

~~~sh
rtk git status --short
rtk git diff origin/main... --stat
rtk git diff origin/main... --check
~~~

Expected: only the spec, plan, Motherboard implementation, tests, project configuration, and runtime documentation are present; whitespace validation is clean.
