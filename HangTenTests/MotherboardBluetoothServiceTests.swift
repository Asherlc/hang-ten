import CoreBluetooth
import XCTest
@testable import HangTen

@MainActor
final class MotherboardBluetoothServiceTests: XCTestCase {
    func testCoreBluetoothTransportCreatesCentralManagerOnlyWhenScanStarts() {
        let manager = FakeCentralManager()
        var factoryCallCount = 0
        let transport = CoreBluetoothMotherboardTransport { _ in
            factoryCallCount += 1
            return manager
        }

        XCTAssertEqual(factoryCallCount, 0)

        transport.startScan()

        XCTAssertEqual(factoryCallCount, 1)
        XCTAssertEqual(manager.scanCount, 1)
    }

    func testConnectCalibratesBeforeStartingThirtyHertzStream() {
        let transport = FakeMotherboardTransport()
        let service = MotherboardBluetoothService(transport: transport)

        service.connect()
        XCTAssertEqual(transport.commands, [])
        transport.emit(.powerChanged(.poweredOn))
        transport.emit(.discovered(MotherboardDiscoveredDevice(id: UUID(), name: "Motherboard")))
        transport.emit(.connected)
        transport.emit(.characteristicsReady)
        XCTAssertEqual(transport.commands, [])
        transport.emit(.notificationsReady)
        XCTAssertEqual(transport.commands, [Data("C".utf8)])

        for index in 0..<16 {
            transport.emit(.notification(Data("\(index / 4),\(index % 4),1,1\r\n".utf8), Date(timeIntervalSince1970: Double(index))))
        }
        XCTAssertEqual(transport.commands, [Data("C".utf8), Data("S30".utf8)])
        XCTAssertEqual(service.state, .calibrating)

        transport.emit(.notification(Data("Stream:30\r\n".utf8), Date()))
        XCTAssertEqual(service.state, .streaming)
    }

    func testCalibrationRequiresEverySensorAndValidPointBeforeStartingStream() {
        let transport = FakeMotherboardTransport()
        let service = MotherboardBluetoothService(transport: transport)
        connect(service, with: transport)

        for point in 0..<16 {
            transport.emit(.notification(
                Data("0,\(point),1,\(point * 100),\r\n".utf8),
                Date(timeIntervalSince1970: Double(point))
            ))
        }

        XCTAssertEqual(transport.commands, [Data("C".utf8)])

        for sensor in 0..<4 {
            for point in 0..<4 {
                transport.emit(.notification(
                    Data("\(sensor),\(point),\(point),\(point * 100),\r\n".utf8),
                    Date(timeIntervalSince1970: Double(sensor * 4 + point))
                ))
            }
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

    func testInitializationDoesNotStartBluetoothWork() {
        let transport = FakeMotherboardTransport()
        _ = MotherboardBluetoothService(transport: transport)

        XCTAssertEqual(transport.startScanCount, 0)
        XCTAssertEqual(transport.connectCount, 0)
    }

    func testNotificationsAreEnabledBeforeCalibrationCommand() {
        let transport = FakeMotherboardTransport()
        let service = MotherboardBluetoothService(transport: transport)
        connect(service, with: transport)

        XCTAssertEqual(transport.operations, ["scan", "stopScan", "connect", "notify:on", "write:C"])
    }

    func testWrongStreamAcknowledgementDoesNotPublishStreaming() {
        let transport = FakeMotherboardTransport()
        let service = MotherboardBluetoothService(transport: transport)
        connect(service, with: transport)
        emitCompleteCalibration(on: transport)

        transport.emit(.notification(Data("Stream:15\r\n".utf8), Date()))

        XCTAssertEqual(service.state, .calibrating)
    }

    func testFragmentedRawPacketPublishesMeasurementAndBatteryAfterCalibration() {
        let transport = FakeMotherboardTransport()
        let service = MotherboardBluetoothService(transport: transport)
        connect(service, with: transport)

        for sensor in 0..<4 {
            for point in 0..<4 {
                transport.emit(.notification(
                    Data("\(sensor),\(point),\(point),\(point * 100),\r\n".utf8),
                    Date(timeIntervalSince1970: Double(point))
                ))
            }
        }
        emitStreamAcknowledgement(on: transport)

        let date = Date(timeIntervalSince1970: 99)
        let frame = Data("01006400000000000000000000000000\r\n".utf8)
        transport.emit(.notification(frame.subdata(in: 0..<11), date))
        XCTAssertNil(service.latestMeasurement)
        transport.emit(.notification(frame.subdata(in: 11..<frame.count), date))

        XCTAssertEqual(service.latestMeasurement?.sampleNumber, 1)
        XCTAssertEqual(service.latestMeasurement?.batteryValue, 100)
        XCTAssertEqual(service.batteryValue, 100)
        XCTAssertEqual(service.latestMeasurement?.timestamp, date)
    }

    func testUnauthorizedStateRemainsUnauthorizedWhenPowerChanges() {
        let transport = FakeMotherboardTransport()
        let service = MotherboardBluetoothService(transport: transport)

        service.connect()
        transport.emit(.powerChanged(.unauthorized))
        XCTAssertEqual(service.state, .unauthorized)

        transport.emit(.powerChanged(.poweredOn))
        XCTAssertEqual(service.state, .unauthorized)
    }

    func testPoweredOnRecoversFromPoweredOffAndAllowsExplicitRescan() {
        let transport = FakeMotherboardTransport()
        let service = MotherboardBluetoothService(transport: transport)

        service.connect()
        transport.emit(.powerChanged(.poweredOff))
        XCTAssertEqual(service.state, .bluetoothUnavailable)

        transport.emit(.powerChanged(.poweredOn))
        XCTAssertEqual(service.state, .idle)
        XCTAssertEqual(transport.startScanCount, 1)

        service.connect()
        XCTAssertEqual(service.state, .scanning)
        XCTAssertEqual(transport.startScanCount, 2)
        XCTAssertEqual(
            transport.operations,
            ["scan", "stopScan", "notify:off", "disconnect", "scan"]
        )
    }

    func testPoweredOnRecoversAfterTransientBluetoothReset() {
        let transport = FakeMotherboardTransport()
        let service = MotherboardBluetoothService(transport: transport)

        service.connect()
        transport.emit(.powerChanged(.resetting))
        XCTAssertEqual(service.state, .bluetoothUnavailable)

        transport.emit(.powerChanged(.poweredOn))

        XCTAssertEqual(service.state, .idle)
        XCTAssertEqual(transport.startScanCount, 1)
    }

    func testTareAveragesTheNextMeasurementWindow() {
        let transport = FakeMotherboardTransport()
        let service = MotherboardBluetoothService(transport: transport, tareSampleCount: 3)
        connectAndStartStreaming(service, with: transport)

        service.tare()
        XCTAssertTrue(service.isTaring)
        XCTAssertEqual(service.tareSamplesCollected, 0)
        XCTAssertEqual(service.tareSampleTarget, 3)

        emitRawPacket(on: transport, sampleNumber: 1, adc: 100)
        XCTAssertTrue(service.isTaring)
        XCTAssertEqual(service.tareSamplesCollected, 1)
        emitRawPacket(on: transport, sampleNumber: 2, adc: 200)
        XCTAssertEqual(service.tareSamplesCollected, 2)
        emitRawPacket(on: transport, sampleNumber: 3, adc: 300)

        XCTAssertFalse(service.isTaring)
        XCTAssertEqual(service.tareSamplesCollected, 0)

        emitRawPacket(on: transport, sampleNumber: 4, adc: 200)
        XCTAssertEqual(service.latestMeasurement?.sensorLoadsKGF ?? [], [0, 0, 0, 0])
        XCTAssertEqual(service.latestMeasurement?.aggregateLoadKGF ?? -1, 0, accuracy: 0.0001)
    }

    func testDisconnectCancelsTareWindowAndClearsItsSamples() {
        let transport = FakeMotherboardTransport()
        let service = MotherboardBluetoothService(transport: transport, tareSampleCount: 3)
        connectAndStartStreaming(service, with: transport)

        service.tare()
        emitRawPacket(on: transport, sampleNumber: 1, adc: 100)
        XCTAssertTrue(service.isTaring)
        XCTAssertEqual(service.tareSamplesCollected, 1)

        service.disconnect()

        XCTAssertFalse(service.isTaring)
        XCTAssertEqual(service.tareSamplesCollected, 0)
        service.tare()
        XCTAssertFalse(service.isTaring)
    }

    func testIntentionalNotificationDisableIsNotReportedAsFailure() {
        let manager = FakeCentralManager()
        let transport = CoreBluetoothMotherboardTransport { _ in manager }
        var disconnectMessages: [String?] = []
        transport.eventHandler = { event in
            guard case .disconnected(let message) = event else { return }
            disconnectMessages.append(message)
        }

        transport.setTXNotificationsEnabled(false)
        transport.handleNotificationStateUpdate(isNotifying: false, error: nil)
        XCTAssertTrue(disconnectMessages.isEmpty)
        transport.handleNotificationStateUpdate(isNotifying: false, error: TestNotificationError.failed)
        XCTAssertTrue(disconnectMessages.isEmpty)

        transport.handleNotificationStateUpdate(isNotifying: true, error: TestNotificationError.failed)
        XCTAssertEqual(disconnectMessages.count, 1)
        XCTAssertNotNil(disconnectMessages[0])

        transport.setTXNotificationsEnabled(true)
        transport.handleNotificationStateUpdate(isNotifying: false, error: nil)
        XCTAssertEqual(disconnectMessages.count, 2)
        XCTAssertEqual(disconnectMessages[1], "Motherboard notifications could not be enabled.")
    }

    func testUnexpectedDisconnectRetriesAtMostThreeTimes() {
        let transport = FakeMotherboardTransport()
        let service = MotherboardBluetoothService(transport: transport)

        service.connect()
        for _ in 0..<4 {
            transport.emit(.disconnected("lost"))
        }

        XCTAssertEqual(transport.startScanCount, 4)
        XCTAssertEqual(transport.disconnectCount, 4)
        XCTAssertFalse(transport.hasSelectedPeripheral)
        XCTAssertEqual(service.state, .disconnected)
        XCTAssertEqual(service.lastError, "lost")
    }

    func testSuccessfulStreamClearsDisconnectErrorAndResetsReconnectBudget() {
        let transport = FakeMotherboardTransport()
        let service = MotherboardBluetoothService(transport: transport)

        service.connect()
        transport.emit(.disconnected("first loss"))
        connectAfterScan(service, with: transport)
        emitCompleteCalibration(on: transport)
        emitStreamAcknowledgement(on: transport)

        XCTAssertNil(service.lastError)
        for _ in 0..<4 {
            transport.emit(.disconnected("later loss"))
        }
        XCTAssertEqual(transport.startScanCount, 5)
        XCTAssertEqual(service.state, .disconnected)
    }

    func testScanTimeoutFailsWithActionableError() async throws {
        let transport = FakeMotherboardTransport()
        let service = MotherboardBluetoothService(
            transport: transport,
            timeouts: .init(scan: 0.01, connect: 1, calibration: 1, streamAcknowledgement: 1)
        )

        service.connect()
        try await Task.sleep(for: .milliseconds(30))

        XCTAssertEqual(service.state, .failed)
        XCTAssertEqual(service.lastError, "Motherboard scan timed out. Move the sensor closer and try again.")
    }

    func testConnectTimeoutFailsWithActionableError() async throws {
        let transport = FakeMotherboardTransport()
        let service = MotherboardBluetoothService(
            transport: transport,
            timeouts: .init(scan: 1, connect: 0.01, calibration: 1, streamAcknowledgement: 1)
        )

        service.connect()
        transport.emit(.discovered(MotherboardDiscoveredDevice(id: UUID(), name: "Motherboard")))
        try await Task.sleep(for: .milliseconds(30))

        XCTAssertEqual(service.state, .failed)
        XCTAssertEqual(service.lastError, "Motherboard connection timed out. Move the sensor closer and try again.")
    }

    func testCalibrationTimeoutFailsWithActionableError() async throws {
        let transport = FakeMotherboardTransport()
        let service = MotherboardBluetoothService(
            transport: transport,
            timeouts: .init(scan: 1, connect: 1, calibration: 0.01, streamAcknowledgement: 1)
        )

        connect(service, with: transport)
        try await Task.sleep(for: .milliseconds(30))

        XCTAssertEqual(service.state, .failed)
        XCTAssertEqual(service.lastError, "Motherboard calibration timed out. Reconnect the sensor and try again.")
    }

    func testStreamAcknowledgementTimeoutFailsWithActionableError() async throws {
        let transport = FakeMotherboardTransport()
        let service = MotherboardBluetoothService(
            transport: transport,
            timeouts: .init(scan: 1, connect: 1, calibration: 1, streamAcknowledgement: 0.01)
        )

        connect(service, with: transport)
        emitCompleteCalibration(on: transport)
        try await Task.sleep(for: .milliseconds(30))

        XCTAssertEqual(service.state, .failed)
        XCTAssertEqual(service.lastError, "Motherboard did not acknowledge the 30 Hz stream. Reconnect the sensor and try again.")
    }

    func testSuccessfulStreamCancelsPendingTimeout() async throws {
        let transport = FakeMotherboardTransport()
        let service = MotherboardBluetoothService(
            transport: transport,
            timeouts: .init(scan: 0.02, connect: 0.02, calibration: 0.02, streamAcknowledgement: 0.02)
        )

        connect(service, with: transport)
        emitCompleteCalibration(on: transport)
        emitStreamAcknowledgement(on: transport)
        try await Task.sleep(for: .milliseconds(50))

        XCTAssertEqual(service.state, .streaming)
        XCTAssertNil(service.lastError)
    }

    func testDisconnectCleansTransportAndSessionBeforeRetrying() {
        let transport = FakeMotherboardTransport()
        let service = MotherboardBluetoothService(transport: transport)
        connect(service, with: transport)

        transport.emit(.disconnected("lost"))

        XCTAssertEqual(
            transport.operations.suffix(4),
            ["stopScan", "notify:off", "disconnect", "scan"]
        )
        XCTAssertEqual(transport.disconnectCount, 1)
        XCTAssertFalse(transport.hasSelectedPeripheral)
        XCTAssertNil(service.latestMeasurement)
        XCTAssertNil(service.batteryValue)
        XCTAssertEqual(service.lastError, "lost")
        XCTAssertEqual(service.state, .scanning)
    }

    func testExplicitDisconnectClearsSelectedTransportImmediately() {
        let transport = FakeMotherboardTransport()
        let service = MotherboardBluetoothService(transport: transport)
        connect(service, with: transport)

        service.disconnect()

        XCTAssertEqual(transport.disconnectCount, 1)
        XCTAssertFalse(transport.hasSelectedPeripheral)
        XCTAssertEqual(service.state, .disconnected)
    }

    private func connect(
        _ service: MotherboardBluetoothService,
        with transport: FakeMotherboardTransport
    ) {
        service.connect()
        transport.emit(.powerChanged(.poweredOn))
        transport.emit(.discovered(MotherboardDiscoveredDevice(id: UUID(), name: "Motherboard")))
        transport.emit(.connected)
        transport.emit(.characteristicsReady)
        transport.emit(.notificationsReady)
    }

    private func connectAfterScan(
        _ service: MotherboardBluetoothService,
        with transport: FakeMotherboardTransport
    ) {
        transport.emit(.powerChanged(.poweredOn))
        transport.emit(.discovered(MotherboardDiscoveredDevice(id: UUID(), name: "Motherboard")))
        transport.emit(.connected)
        transport.emit(.characteristicsReady)
        transport.emit(.notificationsReady)
    }

    private func emitCompleteCalibration(on transport: FakeMotherboardTransport) {
        for sensor in 0..<4 {
            for point in 0..<4 {
                transport.emit(.notification(
                    Data("\(sensor),\(point),\(point),\(point * 100)\r\n".utf8),
                    Date(timeIntervalSince1970: Double(sensor * 4 + point))
                ))
            }
        }
    }

    private func emitStreamAcknowledgement(on transport: FakeMotherboardTransport) {
        transport.emit(.notification(Data("Stream:30\r\n".utf8), Date()))
    }

    private func connectAndStartStreaming(
        _ service: MotherboardBluetoothService,
        with transport: FakeMotherboardTransport
    ) {
        connect(service, with: transport)
        emitCompleteCalibration(on: transport)
        emitStreamAcknowledgement(on: transport)
        XCTAssertEqual(service.state, .streaming)
    }

    private func emitRawPacket(
        on transport: FakeMotherboardTransport,
        sampleNumber: UInt16,
        adc: Int32
    ) {
        var bytes = [
            UInt8(sampleNumber & 0x00FF),
            UInt8(sampleNumber >> 8),
            UInt8(90),
            UInt8(0)
        ]
        for _ in 0..<4 {
            bytes.append(UInt8(truncatingIfNeeded: adc))
            bytes.append(UInt8(truncatingIfNeeded: adc >> 8))
            bytes.append(UInt8(truncatingIfNeeded: adc >> 16))
        }
        let line = bytes.map { String(format: "%02X", $0) }.joined() + "\r\n"
        transport.emit(.notification(Data(line.utf8), Date()))
    }
}

private final class FakeCentralManager: MotherboardCentralManaging {
    var state: CBManagerState = .poweredOn
    var scanCount = 0

    func scanForPeripherals(withServices serviceUUIDs: [CBUUID]?, options: [String: Any]?) {
        scanCount += 1
    }

    func stopScan() {}
    func connect(_ peripheral: CBPeripheral, options: [String: Any]?) {}
    func cancelPeripheralConnection(_ peripheral: CBPeripheral) {}
}

private enum TestNotificationError: Error {
    case failed
}

private final class FakeMotherboardTransport: MotherboardTransport {
    var eventHandler: ((MotherboardTransportEvent) -> Void)?
    var commands: [Data] = []
    var operations: [String] = []
    var startScanCount = 0
    var connectCount = 0
    var disconnectCount = 0
    var hasSelectedPeripheral = false
    func startScan() {
        startScanCount += 1
        operations.append("scan")
    }
    func stopScan() { operations.append("stopScan") }
    func connect(to device: MotherboardDiscoveredDevice) {
        connectCount += 1
        hasSelectedPeripheral = true
        operations.append("connect")
    }
    func disconnect() {
        disconnectCount += 1
        hasSelectedPeripheral = false
        operations.append("disconnect")
    }
    func setTXNotificationsEnabled(_ enabled: Bool) {
        operations.append(enabled ? "notify:on" : "notify:off")
    }
    func write(_ data: Data) {
        commands.append(data)
        operations.append("write:\(String(decoding: data, as: UTF8.self))")
    }
    func emit(_ event: MotherboardTransportEvent) { eventHandler?(event) }
}
