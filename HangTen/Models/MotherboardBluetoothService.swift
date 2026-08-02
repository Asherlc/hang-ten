import Combine
import CoreBluetooth
import Foundation

enum MotherboardBluetoothPowerState: Equatable {
    case unknown
    case resetting
    case unsupported
    case unauthorized
    case poweredOff
    case poweredOn
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
    case notificationsReady
    case notification(Data, Date)
    case disconnected(String?)
}

struct MotherboardServiceTimeouts {
    let scan: TimeInterval
    let connect: TimeInterval
    let calibration: TimeInterval
    let streamAcknowledgement: TimeInterval

    static let production = MotherboardServiceTimeouts(
        scan: 15,
        connect: 10,
        calibration: 10,
        streamAcknowledgement: 5
    )
}

@MainActor
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
    @Published private(set) var state: MotherboardConnectionState = .idle
    @Published private(set) var latestMeasurement: MotherboardMeasurement?
    @Published private(set) var batteryValue: UInt16?
    @Published private(set) var lastError: String?
    @Published private(set) var connectedDeviceID: UUID?
    @Published private(set) var isTaring = false
    @Published private(set) var tareSamplesCollected = 0

    let tareSampleTarget: Int

    private let transport: MotherboardTransport
    private let timeouts: MotherboardServiceTimeouts
    private var parser: MotherboardProtocolParser
    private var calibrationRows: [MotherboardCalibrationRow] = []
    private var calibration: MotherboardCalibration?
    private var tareKGF = Array(repeating: 0.0, count: 4)
    private var tareAccumulatorKGF = Array(repeating: 0.0, count: 4)
    private var wantsConnection = false
    private var reconnectAttempts = 0
    private var timeoutTask: Task<Void, Never>?
    private var lastPowerState: MotherboardBluetoothPowerState = .unknown

    init(
        transport: MotherboardTransport,
        parser: MotherboardProtocolParser = .init(),
        timeouts: MotherboardServiceTimeouts = .production,
        tareSampleCount: Int = 15
    ) {
        self.transport = transport
        self.parser = parser
        self.timeouts = timeouts
        tareSampleTarget = max(1, tareSampleCount)
        transport.eventHandler = { [weak self] event in
            self?.handle(event)
        }
    }

    func connect() {
        wantsConnection = true
        reconnectAttempts = 0
        lastError = nil
        resetSession()
        state = .scanning
        scheduleTimeout(after: timeouts.scan, message: "Motherboard scan timed out. Move the sensor closer and try again.")
        transport.startScan()
    }

    func disconnect() {
        wantsConnection = false
        reconnectAttempts = 0
        cleanupTransportSession()
        state = .disconnected
    }

    func startStreaming() {
        guard calibration != nil, state != .streaming else { return }
        scheduleTimeout(
            after: timeouts.streamAcknowledgement,
            message: "Motherboard did not acknowledge the 30 Hz stream. Reconnect the sensor and try again."
        )
        transport.write(MotherboardProtocol.streamCommand(rate: 30))
    }

    func stopStreaming() {
        guard state == .streaming else { return }
        transport.setTXNotificationsEnabled(false)
        state = .calibrating
    }

    func tare() {
        guard state == .streaming, !isTaring else { return }
        tareAccumulatorKGF = Array(repeating: 0.0, count: 4)
        tareSamplesCollected = 0
        isTaring = true
    }

    private func handle(_ event: MotherboardTransportEvent) {
        switch event {
        case .powerChanged(let powerState):
            handle(powerState)

        case .discovered(let device):
            guard wantsConnection, state == .scanning else { return }
            cancelTimeout()
            transport.stopScan()
            connectedDeviceID = device.id
            state = .connecting
            scheduleTimeout(after: timeouts.connect, message: "Motherboard connection timed out. Move the sensor closer and try again.")
            transport.connect(to: device)

        case .connected:
            guard wantsConnection else { return }
            state = .connecting

        case .characteristicsReady:
            guard wantsConnection else { return }
            state = .calibrating
            transport.setTXNotificationsEnabled(true)

        case .notificationsReady:
            guard wantsConnection, state == .calibrating else { return }
            cancelTimeout()
            scheduleTimeout(after: timeouts.calibration, message: "Motherboard calibration timed out. Reconnect the sensor and try again.")
            transport.write(MotherboardProtocol.command("C"))

        case .notification(let data, let receivedAt):
            handleNotification(data, receivedAt: receivedAt)

        case .disconnected(let message):
            handleDisconnect(message)
        }
    }

    private func handle(_ powerState: MotherboardBluetoothPowerState) {
        let previousPowerState = lastPowerState
        lastPowerState = powerState

        switch powerState {
        case .poweredOn:
            guard state == .bluetoothUnavailable,
                  previousPowerState == .poweredOff ||
                    previousPowerState == .unknown ||
                    previousPowerState == .resetting else { return }
            lastError = nil
            state = .idle

        case .unauthorized:
            wantsConnection = false
            cleanupTransportSession()
            state = .unauthorized

        case .unknown, .resetting, .unsupported, .poweredOff:
            guard state != .unauthorized else { return }
            wantsConnection = false
            cleanupTransportSession()
            state = .bluetoothUnavailable
        }
    }

    private func handleNotification(_ data: Data, receivedAt: Date) {
        for event in parser.append(data, receivedAt: receivedAt) {
            switch event {
            case .calibration(let row):
                guard (0...3).contains(row.sensor), (0...3).contains(row.calibrationPoint) else {
                    continue
                }
                calibrationRows.removeAll {
                    $0.sensor == row.sensor && $0.calibrationPoint == row.calibrationPoint
                }
                calibrationRows.append(row)

                guard hasCompleteCalibration else { continue }
                calibration = MotherboardCalibration(rows: calibrationRows)
                startStreaming()

            case .rawPacket(let packet, let timestamp):
                guard state == .streaming, let calibration else { continue }
                let measurement = MotherboardProtocol.decode(
                    packet,
                    timestamp: timestamp,
                    calibration: calibration,
                    tareKGF: tareKGF
                )
                latestMeasurement = measurement
                batteryValue = measurement.batteryValue
                collectTareSample(measurement)

            case .streamStarted(let rate):
                guard rate == 30, calibration != nil else { continue }
                cancelTimeout()
                state = .streaming
                reconnectAttempts = 0
                lastError = nil

            case .error(let message):
                fail(message)
            }
        }
    }

    private func handleDisconnect(_ message: String?) {
        cleanupTransportSession()
        lastError = message

        guard wantsConnection, reconnectAttempts < 3 else {
            state = .disconnected
            return
        }

        reconnectAttempts += 1
        state = .scanning
        scheduleTimeout(after: timeouts.scan, message: "Motherboard scan timed out. Move the sensor closer and try again.")
        transport.startScan()
    }

    private var hasCompleteCalibration: Bool {
        (0..<4).allSatisfy { sensor in
            (0..<4).allSatisfy { calibrationPoint in
                calibrationRows.contains {
                    $0.sensor == sensor && $0.calibrationPoint == calibrationPoint
                }
            }
        }
    }

    private func cleanupTransportSession() {
        cancelTimeout()
        transport.stopScan()
        transport.setTXNotificationsEnabled(false)
        transport.disconnect()
        resetSession()
    }

    private func resetSession() {
        parser = .init()
        calibrationRows = []
        calibration = nil
        tareKGF = Array(repeating: 0.0, count: 4)
        cancelTare()
        latestMeasurement = nil
        batteryValue = nil
        connectedDeviceID = nil
    }

    private func collectTareSample(_ measurement: MotherboardMeasurement) {
        guard isTaring, measurement.sensorLoadsKGF.count == tareAccumulatorKGF.count else { return }
        tareAccumulatorKGF = zip(tareAccumulatorKGF, measurement.sensorLoadsKGF).map(+)
        tareSamplesCollected += 1

        guard tareSamplesCollected >= tareSampleTarget else { return }
        let divisor = Double(tareSamplesCollected)
        let average = tareAccumulatorKGF.map { $0 / divisor }
        tareKGF = zip(tareKGF, average).map(+)
        cancelTare()
    }

    private func cancelTare() {
        isTaring = false
        tareSamplesCollected = 0
        tareAccumulatorKGF = Array(repeating: 0.0, count: 4)
    }

    private func scheduleTimeout(after delay: TimeInterval, message: String) {
        cancelTimeout()
        let nanoseconds = UInt64(max(0, delay) * 1_000_000_000)
        timeoutTask = Task { [weak self] in
            do {
                try await Task.sleep(nanoseconds: nanoseconds)
            } catch {
                return
            }
            guard !Task.isCancelled else { return }
            self?.fail(message)
        }
    }

    private func cancelTimeout() {
        timeoutTask?.cancel()
        timeoutTask = nil
    }

    private func fail(_ message: String) {
        wantsConnection = false
        cleanupTransportSession()
        lastError = message
        state = .failed
    }
}

protocol MotherboardCentralManaging: AnyObject {
    var state: CBManagerState { get }
    func scanForPeripherals(withServices serviceUUIDs: [CBUUID]?, options: [String: Any]?)
    func stopScan()
    func connect(_ peripheral: CBPeripheral, options: [String: Any]?)
    func cancelPeripheralConnection(_ peripheral: CBPeripheral)
}

extension CBCentralManager: MotherboardCentralManaging {}

@MainActor
final class CoreBluetoothMotherboardTransport: NSObject, MotherboardTransport {
    var eventHandler: ((MotherboardTransportEvent) -> Void)?

    private let centralManagerFactory: (CBCentralManagerDelegate) -> MotherboardCentralManaging
    private var centralManager: MotherboardCentralManaging?
    private var discoveredPeripherals: [UUID: CBPeripheral] = [:]
    private var selectedPeripheral: CBPeripheral?
    private var rxCharacteristic: CBCharacteristic?
    private var txCharacteristic: CBCharacteristic?
    private var scanRequested = false
    private var txNotificationsRequested = false

    override convenience init() {
        self.init { delegate in
            CBCentralManager(delegate: delegate, queue: .main)
        }
    }

    init(centralManagerFactory: @escaping (CBCentralManagerDelegate) -> MotherboardCentralManaging) {
        self.centralManagerFactory = centralManagerFactory
        super.init()
    }

    func startScan() {
        scanRequested = true
        if centralManager == nil {
            centralManager = centralManagerFactory(self)
        }
        beginScanIfPossible()
    }

    func stopScan() {
        scanRequested = false
        centralManager?.stopScan()
    }

    func connect(to device: MotherboardDiscoveredDevice) {
        stopScan()
        guard let peripheral = discoveredPeripherals[device.id] else {
            eventHandler?(.disconnected("Motherboard is no longer available."))
            return
        }

        selectedPeripheral = peripheral
        peripheral.delegate = self
        centralManager?.connect(peripheral, options: nil)
    }

    func disconnect() {
        stopScan()
        txNotificationsRequested = false
        guard let selectedPeripheral else { return }
        clearSelectedPeripheral()
        centralManager?.cancelPeripheralConnection(selectedPeripheral)
    }

    func setTXNotificationsEnabled(_ enabled: Bool) {
        txNotificationsRequested = enabled
        guard let selectedPeripheral, let txCharacteristic else { return }
        selectedPeripheral.setNotifyValue(enabled, for: txCharacteristic)
    }

    func write(_ data: Data) {
        guard let selectedPeripheral, let rxCharacteristic else { return }
        let writeType: CBCharacteristicWriteType = rxCharacteristic.properties.contains(.write)
            ? .withResponse
            : .withoutResponse
        selectedPeripheral.writeValue(data, for: rxCharacteristic, type: writeType)
    }

    private func beginScanIfPossible() {
        guard let centralManager, centralManager.state == .poweredOn else { return }
        centralManager.scanForPeripherals(
            withServices: [CBUUID(nsuuid: MotherboardProtocol.serviceUUID)],
            options: nil
        )
    }

    private func clearSelectedPeripheral() {
        selectedPeripheral?.delegate = nil
        selectedPeripheral = nil
        rxCharacteristic = nil
        txCharacteristic = nil
        txNotificationsRequested = false
    }

    private func reportFailure(_ error: Error?, fallback: String) {
        disconnect()
        eventHandler?(.disconnected(error?.localizedDescription ?? fallback))
    }

    func handleNotificationStateUpdate(isNotifying: Bool, error: Error?) {
        if let error {
            guard txNotificationsRequested || isNotifying else { return }
            let action = txNotificationsRequested ? "enabled" : "disabled"
            reportFailure(error, fallback: "Motherboard notifications could not be \(action).")
        } else if txNotificationsRequested, isNotifying {
            eventHandler?(.notificationsReady)
        } else if txNotificationsRequested {
            reportFailure(nil, fallback: "Motherboard notifications could not be enabled.")
        } else if isNotifying {
            reportFailure(nil, fallback: "Motherboard notifications could not be disabled.")
        }
    }
}

extension CoreBluetoothMotherboardTransport: @preconcurrency CBCentralManagerDelegate {
    func centralManagerDidUpdateState(_ central: CBCentralManager) {
        let powerState: MotherboardBluetoothPowerState
        switch central.state {
        case .unknown: powerState = .unknown
        case .resetting: powerState = .resetting
        case .unsupported: powerState = .unsupported
        case .unauthorized: powerState = .unauthorized
        case .poweredOff: powerState = .poweredOff
        case .poweredOn: powerState = .poweredOn
        @unknown default: powerState = .unknown
        }
        eventHandler?(.powerChanged(powerState))
        if powerState == .poweredOn, scanRequested {
            beginScanIfPossible()
        }
    }

    func centralManager(
        _ central: CBCentralManager,
        didDiscover peripheral: CBPeripheral,
        advertisementData: [String: Any],
        rssi RSSI: NSNumber
    ) {
        let advertisedName = peripheral.name ?? advertisementData[CBAdvertisementDataLocalNameKey] as? String
        guard advertisedName == nil || advertisedName == "Motherboard" else { return }

        discoveredPeripherals[peripheral.identifier] = peripheral
        eventHandler?(.discovered(MotherboardDiscoveredDevice(
            id: peripheral.identifier,
            name: advertisedName ?? "Motherboard"
        )))
    }

    func centralManager(_ central: CBCentralManager, didConnect peripheral: CBPeripheral) {
        guard peripheral == selectedPeripheral else { return }
        peripheral.delegate = self
        peripheral.discoverServices([CBUUID(nsuuid: MotherboardProtocol.serviceUUID)])
        eventHandler?(.connected)
    }

    func centralManager(_ central: CBCentralManager, didFailToConnect peripheral: CBPeripheral, error: Error?) {
        guard peripheral == selectedPeripheral else { return }
        reportFailure(error, fallback: "Could not connect to Motherboard.")
    }

    func centralManager(_ central: CBCentralManager, didDisconnectPeripheral peripheral: CBPeripheral, error: Error?) {
        guard peripheral == selectedPeripheral else { return }
        reportFailure(error, fallback: "Motherboard disconnected.")
    }
}

extension CoreBluetoothMotherboardTransport: @preconcurrency CBPeripheralDelegate {
    func peripheral(_ peripheral: CBPeripheral, didDiscoverServices error: Error?) {
        guard error == nil,
              let service = peripheral.services?.first(where: {
                  $0.uuid == CBUUID(nsuuid: MotherboardProtocol.serviceUUID)
              }) else {
            reportFailure(error, fallback: "Motherboard UART service was not found.")
            return
        }

        peripheral.discoverCharacteristics([
            CBUUID(nsuuid: MotherboardProtocol.rxUUID),
            CBUUID(nsuuid: MotherboardProtocol.txUUID)
        ], for: service)
    }

    func peripheral(_ peripheral: CBPeripheral, didDiscoverCharacteristicsFor service: CBService, error: Error?) {
        guard error == nil else {
            reportFailure(error, fallback: "Motherboard UART characteristics could not be discovered.")
            return
        }

        for characteristic in service.characteristics ?? [] {
            switch characteristic.uuid {
            case CBUUID(nsuuid: MotherboardProtocol.rxUUID):
                rxCharacteristic = characteristic
            case CBUUID(nsuuid: MotherboardProtocol.txUUID):
                txCharacteristic = characteristic
            default:
                break
            }
        }

        guard rxCharacteristic != nil, txCharacteristic != nil else {
            reportFailure(nil, fallback: "Motherboard UART characteristics were not found.")
            return
        }
        eventHandler?(.characteristicsReady)
    }

    func peripheral(_ peripheral: CBPeripheral, didUpdateNotificationStateFor characteristic: CBCharacteristic, error: Error?) {
        guard characteristic == txCharacteristic else { return }
        handleNotificationStateUpdate(isNotifying: characteristic.isNotifying, error: error)
    }

    func peripheral(_ peripheral: CBPeripheral, didUpdateValueFor characteristic: CBCharacteristic, error: Error?) {
        guard characteristic == txCharacteristic else { return }
        guard let value = characteristic.value else {
            if let error {
                reportFailure(error, fallback: "Motherboard notification failed.")
            }
            return
        }
        eventHandler?(.notification(value, Date()))
    }

    func peripheral(_ peripheral: CBPeripheral, didWriteValueFor characteristic: CBCharacteristic, error: Error?) {
        guard characteristic == rxCharacteristic, let error else { return }
        reportFailure(error, fallback: "Motherboard command could not be sent.")
    }
}
