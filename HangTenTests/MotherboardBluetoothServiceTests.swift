import Combine
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

    func testCoreBluetoothTransportDelegateDoesNotEmitOrStoreAnonymousPeripheral() {
        let manager = FakeCentralManager()
        let transport = CoreBluetoothMotherboardTransport { _ in manager }
        let peripheral = FakeMotherboardPeripheral(name: nil)
        var discoveredDevices: [MotherboardDiscoveredDevice] = []
        transport.eventHandler = { event in
            guard case .discovered(let device) = event else { return }
            discoveredDevices.append(device)
        }

        transport.startScan()

        deliverDiscovery(
            peripheral,
            to: transport,
            advertisementData: [:]
        )

        XCTAssertTrue(discoveredDevices.isEmpty)
        transport.connect(to: MotherboardDiscoveredDevice(id: peripheral.deviceID, name: "Motherboard"))
        XCTAssertTrue(manager.connectedPeripherals.isEmpty)
    }

    func testCoreBluetoothTransportDelegateDoesNotEmitOrStoreNonMotherboardPeripheral() {
        let manager = FakeCentralManager()
        let transport = CoreBluetoothMotherboardTransport { _ in manager }
        let peripheral = FakeMotherboardPeripheral(name: "Another peripheral")
        var discoveredDevices: [MotherboardDiscoveredDevice] = []
        transport.eventHandler = { event in
            guard case .discovered(let device) = event else { return }
            discoveredDevices.append(device)
        }

        transport.startScan()

        deliverDiscovery(
            peripheral,
            to: transport,
            advertisementData: [:]
        )

        XCTAssertTrue(discoveredDevices.isEmpty)
        transport.connect(to: MotherboardDiscoveredDevice(id: peripheral.deviceID, name: "Motherboard"))
        XCTAssertTrue(manager.connectedPeripherals.isEmpty)
    }

    func testCoreBluetoothTransportDelegateEmitsLocalNameMotherboardAndRetainsPeripheralForConnection() throws {
        let manager = FakeCentralManager()
        let transport = CoreBluetoothMotherboardTransport { _ in manager }
        let peripheral = FakeMotherboardPeripheral(name: nil)
        var discoveredDevices: [MotherboardDiscoveredDevice] = []
        transport.eventHandler = { event in
            guard case .discovered(let device) = event else { return }
            discoveredDevices.append(device)
        }

        transport.startScan()

        deliverDiscovery(
            peripheral,
            to: transport,
            advertisementData: [CBAdvertisementDataLocalNameKey: "Motherboard"]
        )

        XCTAssertEqual(discoveredDevices, [MotherboardDiscoveredDevice(id: peripheral.deviceID, name: "Motherboard")])
        transport.connect(to: try XCTUnwrap(discoveredDevices.first))
        XCTAssertIdentical(manager.connectedPeripherals.first, peripheral)
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

    func testOneStreamingParserErrorPreservesStreamingAndTransportSession() {
        let transport = FakeMotherboardTransport()
        let service = MotherboardBluetoothService(transport: transport)
        connectAndStartStreaming(service, with: transport)

        transport.emit(.notification(Data("Error:transient\r\n".utf8), Date()))

        XCTAssertEqual(service.state, .streaming)
        XCTAssertEqual(transport.disconnectCount, 0)
        XCTAssertTrue(transport.hasSelectedPeripheral)
    }

    func testThreeConsecutiveStreamingParserErrorsFailAndCleanUpTransport() {
        let transport = FakeMotherboardTransport()
        let service = MotherboardBluetoothService(transport: transport)
        connectAndStartStreaming(service, with: transport)

        transport.emit(.notification(Data("Error:first\r\n".utf8), Date()))
        transport.emit(.notification(Data("Error:second\r\n".utf8), Date()))
        XCTAssertEqual(service.state, .streaming)

        transport.emit(.notification(Data("Error:third\r\n".utf8), Date()))

        XCTAssertEqual(service.state, .failed)
        XCTAssertEqual(service.lastError, "Error:third")
        XCTAssertEqual(transport.disconnectCount, 1)
        XCTAssertFalse(transport.hasSelectedPeripheral)
    }

    func testValidRawPacketResetsConsecutiveStreamingParserErrors() {
        let transport = FakeMotherboardTransport()
        let service = MotherboardBluetoothService(transport: transport)
        connectAndStartStreaming(service, with: transport)

        transport.emit(.notification(Data("Error:first\r\n".utf8), Date()))
        transport.emit(.notification(Data("Error:second\r\n".utf8), Date()))
        emitRawPacket(on: transport, sampleNumber: 1, adc: 100)
        transport.emit(.notification(Data("Error:after-reset-one\r\n".utf8), Date()))
        transport.emit(.notification(Data("Error:after-reset-two\r\n".utf8), Date()))
        transport.emit(.notification(Data("Stream:30\r\n".utf8), Date()))
        transport.emit(.notification(Data("Error:after-stream-reset-one\r\n".utf8), Date()))
        transport.emit(.notification(Data("Error:after-stream-reset-two\r\n".utf8), Date()))

        XCTAssertEqual(service.state, .streaming)
        XCTAssertEqual(transport.disconnectCount, 0)
    }

    func testFourthRawChannelDoesNotAffectAggregateOrBalanceButRemainsAvailable() throws {
        let transport = FakeMotherboardTransport()
        let service = MotherboardBluetoothService(transport: transport)
        connectAndStartStreaming(service, with: transport)

        emitRawPacket(on: transport, sampleNumber: 1, adcValues: [800, 400, 400, 100])
        let baseline = try XCTUnwrap(service.latestMeasurement)

        emitRawPacket(on: transport, sampleNumber: 2, adcValues: [800, 400, 400, 900])
        let changedFourthChannel = try XCTUnwrap(service.latestMeasurement)

        XCTAssertEqual(baseline.aggregateLoadKGF, 16, accuracy: 0.0001)
        XCTAssertEqual(changedFourthChannel.aggregateLoadKGF, 16, accuracy: 0.0001)
        XCTAssertEqual(baseline.leftLoadKGF, 10, accuracy: 0.0001)
        XCTAssertEqual(changedFourthChannel.leftLoadKGF, 10, accuracy: 0.0001)
        XCTAssertEqual(baseline.rightLoadKGF, 6, accuracy: 0.0001)
        XCTAssertEqual(changedFourthChannel.rightLoadKGF, 6, accuracy: 0.0001)
        XCTAssertEqual(baseline.leftShare, changedFourthChannel.leftShare, accuracy: 0.0001)
        XCTAssertEqual(baseline.rightShare, changedFourthChannel.rightShare, accuracy: 0.0001)
        XCTAssertEqual(baseline.sensorLoadsKGF[3], 1, accuracy: 0.0001)
        XCTAssertEqual(changedFourthChannel.sensorLoadsKGF[3], 9, accuracy: 0.0001)
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

    func testUnauthorizedStateRecoversWhenBluetoothBecomesPoweredOn() {
        let transport = FakeMotherboardTransport()
        let service = MotherboardBluetoothService(transport: transport)

        service.connect()
        transport.emit(.powerChanged(.unauthorized))
        XCTAssertEqual(service.state, .unauthorized)

        transport.emit(.powerChanged(.unauthorized))
        XCTAssertEqual(service.state, .unauthorized)

        transport.emit(.powerChanged(.poweredOn))

        XCTAssertEqual(service.state, .idle)
        XCTAssertEqual(transport.startScanCount, 1)

        service.connect()
        XCTAssertEqual(service.state, .scanning)
        XCTAssertEqual(transport.startScanCount, 2)
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

    func testTareAveragesTheNextMeasurementWindowAndPublishesCompletionSignalAtTarget() {
        let transport = FakeMotherboardTransport()
        let service = MotherboardBluetoothService(transport: transport, tareSampleCount: 3)
        connectAndStartStreaming(service, with: transport)

        XCTAssertEqual(service.tareCompletionCount, 0)
        service.tare()
        XCTAssertTrue(service.isTaring)
        XCTAssertEqual(service.tareSamplesCollected, 0)
        XCTAssertEqual(service.tareSampleTarget, 3)

        emitRawPacket(on: transport, sampleNumber: 1, adc: 100)
        XCTAssertTrue(service.isTaring)
        XCTAssertEqual(service.tareSamplesCollected, 1)
        XCTAssertEqual(service.tareCompletionCount, 0)
        emitRawPacket(on: transport, sampleNumber: 2, adc: 200)
        XCTAssertEqual(service.tareSamplesCollected, 2)
        XCTAssertEqual(service.tareCompletionCount, 0)
        emitRawPacket(on: transport, sampleNumber: 3, adc: 300)

        XCTAssertFalse(service.isTaring)
        XCTAssertEqual(service.tareSamplesCollected, 0)
        XCTAssertEqual(service.tareCompletionCount, 1)

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

    func testBodyweightMeasurementAveragesFiniteAggregateLoadsAndClearsActiveState() async throws {
        let transport = FakeMotherboardTransport()
        let sleepGate = ManualSleepGate()
        let service = makeBodyweightService(transport: transport, sleepGate: sleepGate)
        connectAndStartStreaming(service, with: transport)

        XCTAssertTrue(service.beginBodyweightMeasurement(duration: 0.05))
        await sleepGate.waitForSleepRequests(1)
        XCTAssertTrue(service.isMeasuringBodyweight)
        XCTAssertNotNil(service.bodyweightMeasurementStartedAt)
        XCTAssertEqual(service.bodyweightSampleCount, 0)

        emitRawPacket(on: transport, sampleNumber: 1, adc: 200)
        emitRawPacket(on: transport, sampleNumber: 2, adc: 250)
        emitRawPacket(on: transport, sampleNumber: 3, adc: 300)
        await completeBodyweightMeasurement(on: service, byReleasing: sleepGate)

        XCTAssertEqual(try XCTUnwrap(service.bodyweightKGF), 10, accuracy: 0.0001)
        XCTAssertFalse(service.isMeasuringBodyweight)
        XCTAssertNil(service.bodyweightMeasurementStartedAt)
        XCTAssertEqual(service.bodyweightSampleCount, 0)
    }

    #if DEBUG
    func testMaximumDurationPreparationConsumesOnlyExplicitlyAdvancedSimulationFrames() async throws {
        let transport = SimulatedMotherboardTransport(samples: [])
        let sleepGate = ManualSleepGate()
        let service = MotherboardBluetoothService(
            transport: transport,
            bodyweightMeasurementSleep: { nanoseconds in
                try await sleepGate.sleep(nanoseconds: nanoseconds)
            }
        )
        defer { service.disconnect() }

        service.connect()
        XCTAssertEqual(service.state, .streaming)

        let frames = DeterministicSimulationFrames()
        service.tare()

        frames.advance(frames.tare, on: service, count: frames.tareFrameCount)

        XCTAssertEqual(service.tareCompletionCount, 1)
        XCTAssertEqual(
            try XCTUnwrap(service.latestMeasurement).aggregateLoadKGF,
            frames.tare.expectedAggregateLoadKGF,
            accuracy: 0.0001
        )

        XCTAssertTrue(service.beginBodyweightMeasurement(duration: 10))
        await sleepGate.waitForSleepRequests(1)
        frames.advance(frames.bodyweight, on: service, count: frames.bodyweightFrameCount)

        XCTAssertEqual(service.bodyweightSampleCount, frames.bodyweightFrameCount)
        XCTAssertEqual(
            try XCTUnwrap(service.latestMeasurement).aggregateLoadKGF,
            frames.bodyweight.expectedAggregateLoadKGF,
            accuracy: 0.0001
        )
        await completeBodyweightMeasurement(on: service, byReleasing: sleepGate)

        XCTAssertEqual(
            try XCTUnwrap(service.bodyweightKGF),
            frames.bodyweight.expectedAggregateLoadKGF,
            accuracy: 0.0001
        )

        frames.advance(frames.active, on: service)
        let activeMeasurement = try XCTUnwrap(service.latestMeasurement)
        XCTAssertEqual(activeMeasurement.leftShare, frames.active.expectedLeftShare, accuracy: 0.0001)
    }
    #endif

    func testBodyweightMeasurementRejectsDisconnectedService() {
        let service = MotherboardBluetoothService(transport: FakeMotherboardTransport())

        XCTAssertFalse(service.beginBodyweightMeasurement(duration: 0.05))
        XCTAssertNil(service.bodyweightKGF)
        XCTAssertFalse(service.isMeasuringBodyweight)
        XCTAssertNil(service.bodyweightMeasurementStartedAt)
        XCTAssertEqual(service.bodyweightSampleCount, 0)
    }

    func testBodyweightMeasurementRejectsInvalidDurationsAndCapsHugeFiniteDuration() async {
        let transport = FakeMotherboardTransport()
        let sleepGate = ManualSleepGate()
        let service = makeBodyweightService(transport: transport, sleepGate: sleepGate)
        connectAndStartStreaming(service, with: transport)

        XCTAssertFalse(service.beginBodyweightMeasurement(duration: 0))
        XCTAssertFalse(service.beginBodyweightMeasurement(duration: -0.01))
        XCTAssertFalse(service.beginBodyweightMeasurement(duration: .nan))
        XCTAssertFalse(service.beginBodyweightMeasurement(duration: .infinity))
        XCTAssertFalse(service.isMeasuringBodyweight)

        XCTAssertTrue(service.beginBodyweightMeasurement(duration: .greatestFiniteMagnitude))
        await sleepGate.waitForSleepRequests(1)
        let requestedDurations = await sleepGate.requestedNanoseconds
        XCTAssertEqual(requestedDurations.count, 1)
        guard let requestedNanoseconds = requestedDurations.first else { return }
        XCTAssertGreaterThan(requestedNanoseconds, 0)
        XCTAssertLessThanOrEqual(requestedNanoseconds, UInt64.max)

        await completeBodyweightMeasurement(on: service, byReleasing: sleepGate)
        XCTAssertNil(service.bodyweightKGF)
    }

    func testBodyweightMeasurementPublishesFiniteSamplesWhenFiniteCalibrationOverflows() async throws {
        let transport = FakeMotherboardTransport()
        let sleepGate = ManualSleepGate()
        let service = makeBodyweightService(transport: transport, sleepGate: sleepGate)
        connect(service, with: transport)
        emitCompleteCalibration(on: transport) { sensor, point in
            point == 0 ? Double.greatestFiniteMagnitude.description : String(point)
        }
        emitStreamAcknowledgement(on: transport)

        XCTAssertTrue(service.beginBodyweightMeasurement(duration: 0.05))
        await sleepGate.waitForSleepRequests(1)
        emitRawPacket(on: transport, sampleNumber: 1, adc: 0)

        let measurement = try XCTUnwrap(service.latestMeasurement)
        XCTAssertTrue(measurement.sensorLoadsKGF.allSatisfy(\.isFinite))
        XCTAssertTrue(measurement.aggregateLoadKGF.isFinite)
        XCTAssertNoThrow(try JSONEncoder().encode(measurement))
        XCTAssertEqual(service.bodyweightSampleCount, 1)

        await completeBodyweightMeasurement(on: service, byReleasing: sleepGate)
        XCTAssertEqual(try XCTUnwrap(service.bodyweightKGF), .greatestFiniteMagnitude)
    }

    func testBodyweightMeasurementKeepsFiniteBaselineForExtremeFiniteSamples() async throws {
        let transport = FakeMotherboardTransport()
        let sleepGate = ManualSleepGate()
        let service = makeBodyweightService(transport: transport, sleepGate: sleepGate)
        connect(service, with: transport)
        emitCompleteCalibration(on: transport) { sensor, point in
            sensor == 0 && point == 0 ? Double.greatestFiniteMagnitude.description : String(point)
        }
        emitStreamAcknowledgement(on: transport)

        XCTAssertTrue(service.beginBodyweightMeasurement(duration: 0.05))
        await sleepGate.waitForSleepRequests(1)
        emitRawPacket(on: transport, sampleNumber: 1, adc: 0)
        emitRawPacket(on: transport, sampleNumber: 2, adc: 0)

        XCTAssertTrue(try XCTUnwrap(service.latestMeasurement).aggregateLoadKGF.isFinite)
        await completeBodyweightMeasurement(on: service, byReleasing: sleepGate)

        XCTAssertEqual(try XCTUnwrap(service.bodyweightKGF), .greatestFiniteMagnitude)
    }

    func testTareAndBodyweightMeasurementCollectIndependently() async throws {
        let transport = FakeMotherboardTransport()
        let sleepGate = ManualSleepGate()
        let service = makeBodyweightService(transport: transport, sleepGate: sleepGate, tareSampleCount: 3)
        connectAndStartStreaming(service, with: transport)

        service.tare()
        XCTAssertTrue(service.beginBodyweightMeasurement(duration: 0.05))
        await sleepGate.waitForSleepRequests(1)

        emitRawPacket(on: transport, sampleNumber: 1, adc: 200)
        XCTAssertTrue(service.isTaring)
        XCTAssertEqual(service.tareSamplesCollected, 1)
        XCTAssertEqual(service.bodyweightSampleCount, 1)

        emitRawPacket(on: transport, sampleNumber: 2, adc: 250)
        emitRawPacket(on: transport, sampleNumber: 3, adc: 300)
        XCTAssertFalse(service.isTaring)
        XCTAssertEqual(service.bodyweightSampleCount, 3)

        await completeBodyweightMeasurement(on: service, byReleasing: sleepGate)
        XCTAssertEqual(try XCTUnwrap(service.bodyweightKGF), 10, accuracy: 0.0001)
    }

    func testStopStreamingCancelsBodyweightMeasurement() async {
        let transport = FakeMotherboardTransport()
        let sleepGate = ManualSleepGate()
        let service = makeBodyweightService(transport: transport, sleepGate: sleepGate)
        connectAndStartStreaming(service, with: transport)

        XCTAssertTrue(service.beginBodyweightMeasurement(duration: 0.05))
        await sleepGate.waitForSleepRequests(1)
        emitRawPacket(on: transport, sampleNumber: 1, adc: 250)
        XCTAssertEqual(service.bodyweightSampleCount, 1)

        service.stopStreaming()

        XCTAssertNil(service.bodyweightKGF)
        XCTAssertFalse(service.isMeasuringBodyweight)
        XCTAssertNil(service.bodyweightMeasurementStartedAt)
        XCTAssertEqual(service.bodyweightSampleCount, 0)
        await sleepGate.releaseNext()
    }

    func testExplicitDisconnectCancelsBodyweightMeasurementAndClearsBaseline() async throws {
        let transport = FakeMotherboardTransport()
        let sleepGate = ManualSleepGate()
        let service = makeBodyweightService(transport: transport, sleepGate: sleepGate)
        connectAndStartStreaming(service, with: transport)

        XCTAssertTrue(service.beginBodyweightMeasurement(duration: 0.05))
        await sleepGate.waitForSleepRequests(1)
        emitRawPacket(on: transport, sampleNumber: 1, adc: 200)
        await completeBodyweightMeasurement(on: service, byReleasing: sleepGate)
        XCTAssertEqual(try XCTUnwrap(service.bodyweightKGF), 8, accuracy: 0.0001)

        XCTAssertTrue(service.beginBodyweightMeasurement(duration: 0.05))
        await sleepGate.waitForSleepRequests(2)
        emitRawPacket(on: transport, sampleNumber: 2, adc: 250)
        XCTAssertTrue(service.isMeasuringBodyweight)
        XCTAssertNotNil(service.bodyweightMeasurementStartedAt)
        XCTAssertEqual(service.bodyweightSampleCount, 1)

        service.disconnect()

        XCTAssertEqual(service.state, .disconnected)
        XCTAssertNil(service.bodyweightKGF)
        XCTAssertFalse(service.isMeasuringBodyweight)
        XCTAssertNil(service.bodyweightMeasurementStartedAt)
        XCTAssertEqual(service.bodyweightSampleCount, 0)
        await sleepGate.releaseNext()
    }

    func testTransportDisconnectCancelsBodyweightMeasurementBeforeReconnect() async {
        let transport = FakeMotherboardTransport()
        let sleepGate = ManualSleepGate()
        let service = makeBodyweightService(transport: transport, sleepGate: sleepGate)
        connectAndStartStreaming(service, with: transport)

        XCTAssertTrue(service.beginBodyweightMeasurement(duration: 0.05))
        await sleepGate.waitForSleepRequests(1)
        emitRawPacket(on: transport, sampleNumber: 1, adc: 250)

        transport.emit(.disconnected("lost"))

        XCTAssertEqual(service.state, .scanning)
        XCTAssertNil(service.bodyweightKGF)
        XCTAssertFalse(service.isMeasuringBodyweight)
        XCTAssertNil(service.bodyweightMeasurementStartedAt)
        XCTAssertEqual(service.bodyweightSampleCount, 0)

        connectAfterScan(service, with: transport)
        emitCompleteCalibration(on: transport)
        emitStreamAcknowledgement(on: transport)
        XCTAssertEqual(service.state, .streaming)
        await sleepGate.releaseNext()
    }

    func testFreshConnectResetsActiveBodyweightMeasurement() async {
        let transport = FakeMotherboardTransport()
        let sleepGate = ManualSleepGate()
        let service = makeBodyweightService(transport: transport, sleepGate: sleepGate)
        connectAndStartStreaming(service, with: transport)

        XCTAssertTrue(service.beginBodyweightMeasurement(duration: 0.05))
        await sleepGate.waitForSleepRequests(1)
        emitRawPacket(on: transport, sampleNumber: 1, adc: 250)

        service.connect()

        XCTAssertEqual(service.state, .scanning)
        XCTAssertNil(service.bodyweightKGF)
        XCTAssertFalse(service.isMeasuringBodyweight)
        XCTAssertNil(service.bodyweightMeasurementStartedAt)
        XCTAssertEqual(service.bodyweightSampleCount, 0)
        await sleepGate.releaseNext()
    }

    func testSecondBodyweightMeasurementReplacesExistingBaseline() async throws {
        let transport = FakeMotherboardTransport()
        let sleepGate = ManualSleepGate()
        let service = makeBodyweightService(transport: transport, sleepGate: sleepGate)
        connectAndStartStreaming(service, with: transport)

        XCTAssertTrue(service.beginBodyweightMeasurement(duration: 0.05))
        await sleepGate.waitForSleepRequests(1)
        emitRawPacket(on: transport, sampleNumber: 1, adc: 200)
        await completeBodyweightMeasurement(on: service, byReleasing: sleepGate)
        XCTAssertEqual(try XCTUnwrap(service.bodyweightKGF), 8, accuracy: 0.0001)

        XCTAssertTrue(service.beginBodyweightMeasurement(duration: 0.05))
        await sleepGate.waitForSleepRequests(2)
        emitRawPacket(on: transport, sampleNumber: 2, adc: 300)
        await completeBodyweightMeasurement(on: service, byReleasing: sleepGate)

        XCTAssertEqual(try XCTUnwrap(service.bodyweightKGF), 12, accuracy: 0.0001)
        XCTAssertFalse(service.isMeasuringBodyweight)
    }

    func testSecondEmptyBodyweightMeasurementClearsThePreviousBaselineWithoutReusingIt() async throws {
        let transport = FakeMotherboardTransport()
        let sleepGate = ManualSleepGate()
        let service = makeBodyweightService(transport: transport, sleepGate: sleepGate)
        connectAndStartStreaming(service, with: transport)

        XCTAssertTrue(service.beginBodyweightMeasurement(duration: 0.05))
        await sleepGate.waitForSleepRequests(1)
        emitRawPacket(on: transport, sampleNumber: 1, adc: 200)
        await completeBodyweightMeasurement(on: service, byReleasing: sleepGate)
        XCTAssertEqual(try XCTUnwrap(service.bodyweightKGF), 8, accuracy: 0.0001)

        XCTAssertTrue(service.beginBodyweightMeasurement(duration: 0.05))
        XCTAssertNil(service.bodyweightKGF)
        await sleepGate.waitForSleepRequests(2)
        await completeBodyweightMeasurement(on: service, byReleasing: sleepGate)

        XCTAssertNil(service.bodyweightKGF)
        XCTAssertFalse(service.isMeasuringBodyweight)

        var preparation = MotherboardWorkoutPreparation()
        XCTAssertTrue(preparation.startTare())
        preparation.completeTare(isStreaming: true)
        XCTAssertTrue(preparation.startBodyweightCapture())
        preparation.completeBodyweight(with: service.bodyweightKGF, isStreaming: true)
        XCTAssertEqual(preparation.step, .bodyweight)
        XCTAssertFalse(preparation.canContinue(isStreaming: true))
    }

    func testCancelPreparationMeasurementsDoesNotPublishTareCompletionWhileStreaming() {
        let transport = FakeMotherboardTransport()
        let service = MotherboardBluetoothService(transport: transport, tareSampleCount: 3)
        connectAndStartStreaming(service, with: transport)

        service.tare()
        emitRawPacket(on: transport, sampleNumber: 1, adc: 200)
        service.cancelPreparationMeasurements()

        XCTAssertEqual(service.state, .streaming)
        XCTAssertFalse(service.isTaring)
        XCTAssertEqual(service.tareSamplesCollected, 0)
        XCTAssertEqual(service.tareCompletionCount, 0)
    }

    func testCancelPreparationMeasurementsStopsBodyweightCaptureAndClearsTheBaseline() async throws {
        let transport = FakeMotherboardTransport()
        let sleepGate = ManualSleepGate()
        let service = makeBodyweightService(transport: transport, sleepGate: sleepGate)
        connectAndStartStreaming(service, with: transport)

        XCTAssertTrue(service.beginBodyweightMeasurement(duration: 0.05))
        await sleepGate.waitForSleepRequests(1)
        emitRawPacket(on: transport, sampleNumber: 1, adc: 200)
        await completeBodyweightMeasurement(on: service, byReleasing: sleepGate)
        XCTAssertEqual(try XCTUnwrap(service.bodyweightKGF), 8, accuracy: 0.0001)

        XCTAssertTrue(service.beginBodyweightMeasurement(duration: 0.05))
        await sleepGate.waitForSleepRequests(2)
        emitRawPacket(on: transport, sampleNumber: 2, adc: 250)
        service.cancelPreparationMeasurements()

        XCTAssertEqual(service.state, .streaming)
        XCTAssertNil(service.bodyweightKGF)
        XCTAssertFalse(service.isMeasuringBodyweight)
        XCTAssertNil(service.bodyweightMeasurementStartedAt)
        XCTAssertEqual(service.bodyweightSampleCount, 0)
        await sleepGate.releaseNext()
    }

    func testStopStreamingCleansUpToIdleAndAllowsExplicitReconnect() {
        let transport = FakeMotherboardTransport()
        let service = MotherboardBluetoothService(transport: transport)
        connectAndStartStreaming(service, with: transport)
        emitRawPacket(on: transport, sampleNumber: 1, adc: 100)

        service.stopStreaming()

        XCTAssertEqual(service.state, .idle)
        XCTAssertNil(service.latestMeasurement)
        XCTAssertNil(service.batteryValue)
        XCTAssertNil(service.connectedDeviceID)
        XCTAssertEqual(
            Array(transport.operations.suffix(3)),
            ["stopScan", "notify:off", "disconnect"]
        )

        service.connect()

        XCTAssertEqual(service.state, .scanning)
        XCTAssertEqual(transport.operations.last, "scan")
        XCTAssertEqual(transport.startScanCount, 2)
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
        XCTAssertEqual(service.state, .failed)
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
        XCTAssertEqual(service.state, .failed)
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

    func testInvalidScanTimeoutsAreIgnored() async throws {
        for delay in [
            TimeInterval.nan,
            -.infinity,
            .infinity,
            0,
            -0.01,
            .greatestFiniteMagnitude
        ] {
            let transport = FakeMotherboardTransport()
            let service = MotherboardBluetoothService(
                transport: transport,
                timeouts: .init(scan: delay, connect: 1, calibration: 1, streamAcknowledgement: 1)
            )

            service.connect()
            try await Task.sleep(for: .milliseconds(10))

            XCTAssertEqual(service.state, .scanning)
            XCTAssertEqual(transport.startScanCount, 1)
        }
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

    private func emitCompleteCalibration(
        on transport: FakeMotherboardTransport,
        massKGF: ((Int, Int) -> String)? = nil
    ) {
        for sensor in 0..<4 {
            for point in 0..<4 {
                let defaultMass = Double(point * 10)
                let requestedMass = massKGF?(sensor, point) ?? defaultMass.description
                let calibratedMass: String
                if let parsedMass = Double(requestedMass), parsedMass.isFinite {
                    let sign = (sensor == 1 || sensor == 2) ? -1.0 : 1.0
                    calibratedMass = (parsedMass * sign).description
                } else {
                    calibratedMass = requestedMass
                }
                transport.emit(.notification(
                    Data("\(sensor),\(point),\(calibratedMass),\(point * 1_000)\r\n".utf8),
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
        emitRawPacket(
            on: transport,
            sampleNumber: sampleNumber,
            adcValues: [adc * 2, adc, adc, adc]
        )
    }

    private func emitRawPacket(
        on transport: FakeMotherboardTransport,
        sampleNumber: UInt16,
        adcValues: [Int32]
    ) {
        precondition(adcValues.count == 4)
        var bytes = [
            UInt8(sampleNumber & 0x00FF),
            UInt8(sampleNumber >> 8),
            UInt8(90),
            UInt8(0)
        ]
        for adc in adcValues {
            bytes.append(UInt8(truncatingIfNeeded: adc))
            bytes.append(UInt8(truncatingIfNeeded: adc >> 8))
            bytes.append(UInt8(truncatingIfNeeded: adc >> 16))
        }
        let line = bytes.map { String(format: "%02X", $0) }.joined() + "\r\n"
        transport.emit(.notification(Data(line.utf8), Date()))
    }

    private func makeBodyweightService(
        transport: FakeMotherboardTransport,
        sleepGate: ManualSleepGate,
        tareSampleCount: Int = 15
    ) -> MotherboardBluetoothService {
        MotherboardBluetoothService(
            transport: transport,
            tareSampleCount: tareSampleCount,
            bodyweightMeasurementSleep: { nanoseconds in
                try await sleepGate.sleep(nanoseconds: nanoseconds)
            }
        )
    }

    private func completeBodyweightMeasurement(
        on service: MotherboardBluetoothService,
        byReleasing sleepGate: ManualSleepGate
    ) async {
        let completion = expectation(description: "bodyweight measurement completes")
        let cancellable = service.$isMeasuringBodyweight
            .dropFirst()
            .filter { !$0 }
            .sink { _ in completion.fulfill() }

        await sleepGate.releaseNext()
        await fulfillment(of: [completion], timeout: 1)
        withExtendedLifetime(cancellable) {}
    }

    private func waitForService(
        _ description: String,
        timeout: TimeInterval = 2,
        condition: @escaping () -> Bool
    ) async throws {
        let deadline = Date().addingTimeInterval(timeout)
        while !condition(), Date() < deadline {
            try await Task.sleep(for: .milliseconds(5))
        }
        XCTAssertTrue(condition(), "Timed out waiting for \(description).")
    }

    private func deliverDiscovery(
        _ peripheral: MotherboardPeripheralManaging,
        to transport: CoreBluetoothMotherboardTransport,
        advertisementData: [String: Any]
    ) {
        transport.handleDiscovery(peripheral: peripheral, advertisementData: advertisementData)
    }
}

private actor ManualSleepGate {
    private var requestedNanosecondsStorage: [UInt64] = []
    private var sleepers: [CheckedContinuation<Void, Error>] = []
    private var requestWaiters: [(Int, CheckedContinuation<Void, Never>)] = []

    var requestedNanoseconds: [UInt64] { requestedNanosecondsStorage }

    func sleep(nanoseconds: UInt64) async throws {
        try await withCheckedThrowingContinuation { continuation in
            sleepers.append(continuation)
            requestedNanosecondsStorage.append(nanoseconds)
            resumeRequestWaiters()
        }
    }

    func waitForSleepRequests(_ count: Int) async {
        guard requestedNanosecondsStorage.count < count else { return }
        await withCheckedContinuation { requestWaiters.append((count, $0)) }
    }

    func releaseNext() {
        guard !sleepers.isEmpty else { return }
        sleepers.removeFirst().resume()
    }

    private func resumeRequestWaiters() {
        let readyWaiters = requestWaiters.enumerated().compactMap { index, waiter in
            waiter.0 <= requestedNanosecondsStorage.count ? index : nil
        }
        for index in readyWaiters.reversed() {
            requestWaiters.remove(at: index).1.resume()
        }
    }
}

private final class FakeCentralManager: MotherboardCentralManaging {
    var state: CBManagerState = .poweredOn
    var scanCount = 0
    var connectedPeripherals: [MotherboardPeripheralManaging] = []

    func scanForPeripherals(withServices serviceUUIDs: [CBUUID]?, options: [String: Any]?) {
        scanCount += 1
    }

    func stopScan() {}
    func connect(_ peripheral: MotherboardPeripheralManaging, options: [String: Any]?) {
        connectedPeripherals.append(peripheral)
    }
    func cancelPeripheralConnection(_ peripheral: MotherboardPeripheralManaging) {}
}

private final class FakeMotherboardPeripheral: NSObject, MotherboardPeripheralManaging {
    let deviceID = UUID()
    let name: String?
    var identifier: UUID { deviceID }
    var delegate: CBPeripheralDelegate?
    var services: [CBService]? { nil }

    init(name: String?) {
        self.name = name
        super.init()
    }

    func discoverServices(_ serviceUUIDs: [CBUUID]?) {}
    func discoverCharacteristics(_ characteristicUUIDs: [CBUUID]?, for service: CBService) {}
    func setNotifyValue(_ enabled: Bool, for characteristic: CBCharacteristic) {}
    func writeValue(_ data: Data, for characteristic: CBCharacteristic, type: CBCharacteristicWriteType) {}
    func connect(using centralManager: CBCentralManager, options: [String: Any]?) {}
    func cancelConnection(using centralManager: CBCentralManager) {}
}

#if DEBUG
private struct DeterministicSimulationFrame {
    let data: Data
    let expectedAggregateLoadKGF: Double
    let expectedLeftShare: Double
}

private struct DeterministicSimulationFrames {
    let tareFrameCount = 15
    let bodyweightFrameCount = 40
    let tare = DeterministicSimulationFrame(
        data: deterministicRawFrame(adcValues: [0, 0, 0, 0]),
        expectedAggregateLoadKGF: 0,
        expectedLeftShare: 0.5
    )
    let bodyweight = DeterministicSimulationFrame(
        data: deterministicRawFrame(adcValues: [30_000, 20_000, 30_000, 20_000]),
        expectedAggregateLoadKGF: 80,
        expectedLeftShare: 0.5
    )
    let active = DeterministicSimulationFrame(
        data: deterministicRawFrame(adcValues: [30_000, 20_000, 10_000, 20_000]),
        expectedAggregateLoadKGF: 60,
        expectedLeftShare: 2.0 / 3.0
    )

    @MainActor
    func advance(
        _ frame: DeterministicSimulationFrame,
        on service: MotherboardBluetoothService,
        count: Int = 1
    ) {
        for index in 0..<count {
            service.injectSimulationFrameForTesting(
                frame.data,
                receivedAt: Date(timeIntervalSince1970: TimeInterval(index))
            )
        }
    }

}

private func deterministicRawFrame(adcValues: [Int32]) -> Data {
    var bytes = [UInt8(0), UInt8(0), UInt8(88), UInt8(0)]
    for adc in adcValues {
        bytes.append(UInt8(truncatingIfNeeded: adc))
        bytes.append(UInt8(truncatingIfNeeded: adc >> 8))
        bytes.append(UInt8(truncatingIfNeeded: adc >> 16))
    }
    let line = bytes.map { String(format: "%02X", $0) }.joined() + "\r\n"
    return Data(line.utf8)
}
#endif

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
        operations.append("write:\(String(data: data, encoding: .utf8) ?? "")")
    }
    func emit(_ event: MotherboardTransportEvent) { eventHandler?(event) }
}
