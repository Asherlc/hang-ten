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

    func testPowerAuthorizationAndAvailabilityArePublished() {
        let transport = FakeMotherboardTransport()
        let service = MotherboardBluetoothService(transport: transport)

        service.connect()
        transport.emit(.powerChanged(.unauthorized))
        XCTAssertEqual(service.state, .unauthorized)

        transport.emit(.powerChanged(.poweredOff))
        XCTAssertEqual(service.state, .bluetoothUnavailable)
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
        transport.emit(.notification(Data("Stream:30\r\n".utf8), Date()))

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
        transport.emit(.notification(Data("Stream:30\r\n".utf8), Date()))
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
