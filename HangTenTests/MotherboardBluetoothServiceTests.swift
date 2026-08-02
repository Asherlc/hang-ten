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
            transport.emit(.notification(Data("\(index / 4),\(index % 4),1,1\r\n".utf8), Date(timeIntervalSince1970: Double(index))))
        }
        XCTAssertEqual(transport.commands, [Data("C".utf8), Data("S30".utf8)])
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
    }
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
