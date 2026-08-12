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
    let profile: ForceSensorProfile

    init(id: UUID, name: String, profile: ForceSensorProfile = .motherboard) {
        self.id = id
        self.name = name
        self.profile = profile
    }
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

extension MotherboardTransport {
    func configure(profile: ForceSensorProfile) {}
}

#if DEBUG
@MainActor
protocol MotherboardSimulationControlling: AnyObject {
    func resetSimulationStream()
}
#endif

@MainActor
final class MotherboardBluetoothService: ObservableObject {
    @Published private(set) var state: MotherboardConnectionState = .idle
    @Published private(set) var latestMeasurement: MotherboardMeasurement?
    @Published private(set) var batteryValue: UInt16?
    @Published private(set) var lastError: String?
    @Published private(set) var connectedDeviceID: UUID?
    @Published private(set) var connectedProfile: ForceSensorProfile?
    @Published private(set) var isTaring = false
    @Published private(set) var tareSamplesCollected = 0
    @Published private(set) var tareCompletionCount = 0
    @Published private(set) var bodyweightKGF: Double?
    @Published private(set) var isMeasuringBodyweight = false
    @Published private(set) var bodyweightMeasurementStartedAt: Date?
    @Published private(set) var bodyweightSampleCount = 0

    let tareSampleTarget: Int

    private let transport: MotherboardTransport
    private let timeouts: MotherboardServiceTimeouts
    private let bodyweightMeasurementSleep: @Sendable (UInt64) async throws -> Void
    private var parser: MotherboardProtocolParser
    private var calibrationRows: [MotherboardCalibrationRow] = []
    private var calibration: MotherboardCalibration?
    private var tareKGF = Array(repeating: 0.0, count: 4)
    private var tareAccumulatorKGF = Array(repeating: 0.0, count: 4)
    private var bodyweightMeanKGF: Double?
    private var wantsConnection = false
    private var reconnectAttempts = 0
    private var timeoutTask: Task<Void, Never>?
    private var bodyweightMeasurementTask: Task<Void, Never>?
    private var lastPowerState: MotherboardBluetoothPowerState = .unknown
    private var consecutiveStreamingParserErrors = 0
    private var requestedProfile: ForceSensorProfile = .motherboard
    private var activeProfile: ForceSensorProfile?
    private var nextForceSensorSampleNumber: UInt16 = 0

    private static let maximumBodyweightMeasurementDuration = TimeInterval(UInt64.max / 1_000_000_000)
    private static let maximumConsecutiveStreamingParserErrors = 3

    init(
        transport: MotherboardTransport,
        parser: MotherboardProtocolParser = .init(),
        timeouts: MotherboardServiceTimeouts = .production,
        tareSampleCount: Int = 15,
        bodyweightMeasurementSleep: @escaping @Sendable (UInt64) async throws -> Void = { nanoseconds in
            try await Task.sleep(nanoseconds: nanoseconds)
        }
    ) {
        self.transport = transport
        self.parser = parser
        self.timeouts = timeouts
        self.bodyweightMeasurementSleep = bodyweightMeasurementSleep
        tareSampleTarget = max(1, tareSampleCount)
        transport.eventHandler = { [weak self] event in
            self?.handle(event)
        }
    }

    func connect(profile: ForceSensorProfile = .motherboard) {
        guard ForceSensorProfile.connectableCases.contains(profile) else {
            wantsConnection = false
            lastError = "\(profile.label) is not available yet."
            state = .failed
            return
        }

        wantsConnection = true
        reconnectAttempts = 0
        lastError = nil
        requestedProfile = profile
        resetSession()
        transport.configure(profile: profile)
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
        guard activeProfile == .motherboard, calibration != nil, state != .streaming else { return }
        scheduleTimeout(
            after: timeouts.streamAcknowledgement,
            message: "Motherboard did not acknowledge the 30 Hz stream. Reconnect the sensor and try again."
        )
        transport.write(MotherboardProtocol.streamCommand(rate: 30))
    }

    func stopStreaming() {
        guard state == .streaming else { return }
        if let adapter = activeProfile.flatMap(ForceSensorAdapterRegistry.adapter(for:)),
           adapter.capabilities.contains(.explicitStartStop) {
            transport.write(adapter.payload(for: .stop))
        }
        wantsConnection = false
        reconnectAttempts = 0
        cleanupTransportSession()
        lastError = nil
        state = .idle
    }

    func tare() {
        guard state == .streaming, !isTaring else { return }
        if let adapter = activeProfile.flatMap(ForceSensorAdapterRegistry.adapter(for:)),
           adapter.capabilities.contains(.hardwareTare) {
            transport.write(adapter.payload(for: .tare))
            tareCompletionCount += 1
            return
        }
        tareAccumulatorKGF = Array(repeating: 0.0, count: 4)
        tareSamplesCollected = 0
        isTaring = true
    }

    #if DEBUG
    func resetSimulationForPreparation() {
        (transport as? MotherboardSimulationControlling)?.resetSimulationStream()
    }

    func injectSimulationFrameForTesting(_ data: Data, receivedAt: Date) {
        guard state == .streaming else { return }
        handleNotification(data, receivedAt: receivedAt)
    }
    #endif

    func cancelPreparationMeasurements() {
        cancelTare()
        cancelBodyweightMeasurement()
        bodyweightKGF = nil
    }

    @discardableResult
    func beginBodyweightMeasurement(duration: TimeInterval) -> Bool {
        guard state == .streaming, duration.isFinite, duration > 0 else { return false }

        cancelBodyweightMeasurement()
        bodyweightKGF = nil
        let measurementDuration = min(duration, Self.maximumBodyweightMeasurementDuration)
        let nanoseconds = UInt64(measurementDuration * 1_000_000_000)
        isMeasuringBodyweight = true
        bodyweightMeasurementStartedAt = Date()
        let sleep = bodyweightMeasurementSleep
        bodyweightMeasurementTask = Task { [weak self] in
            do {
                try await sleep(nanoseconds)
            } catch {
                return
            }
            guard !Task.isCancelled else { return }
            self?.completeBodyweightMeasurement()
        }
        return true
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
            activeProfile = device.profile
            connectedProfile = device.profile
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
            guard let activeProfile else { return }
            if activeProfile == .motherboard {
                scheduleTimeout(after: timeouts.calibration, message: "Motherboard calibration timed out. Reconnect the sensor and try again.")
                transport.write(MotherboardProtocol.command("C"))
            } else {
                if let adapter = ForceSensorAdapterRegistry.adapter(for: activeProfile),
                   adapter.capabilities.contains(.explicitStartStop) {
                    transport.write(adapter.payload(for: .start))
                }
                consecutiveStreamingParserErrors = 0
                state = .streaming
                reconnectAttempts = 0
                lastError = nil
            }

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
            guard (state == .bluetoothUnavailable || state == .unauthorized),
                  previousPowerState == .poweredOff ||
                    previousPowerState == .unknown ||
                    previousPowerState == .resetting ||
                    previousPowerState == .unauthorized else { return }
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
        guard activeProfile == .motherboard else {
            handleForceSensorNotification(data, receivedAt: receivedAt)
            return
        }

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
                guard state == .streaming else { continue }
                consecutiveStreamingParserErrors = 0
                guard let calibration else { continue }
                let measurement = MotherboardProtocol.decode(
                    packet,
                    timestamp: timestamp,
                    calibration: calibration,
                    tareKGF: tareKGF
                )
                latestMeasurement = measurement
                batteryValue = measurement.batteryValue
                collectTareSample(measurement)
                collectBodyweightSample(measurement)

            case .streamStarted(let rate):
                guard rate == 30, calibration != nil else { continue }
                cancelTimeout()
                consecutiveStreamingParserErrors = 0
                state = .streaming
                reconnectAttempts = 0
                lastError = nil

            case .error(let message):
                guard state == .streaming else {
                    fail(message)
                    continue
                }
                consecutiveStreamingParserErrors += 1
                if consecutiveStreamingParserErrors >= Self.maximumConsecutiveStreamingParserErrors {
                    fail(message)
                }
            }
        }
    }

    private func handleForceSensorNotification(_ data: Data, receivedAt: Date) {
        guard state == .streaming,
              let activeProfile,
              let adapter = ForceSensorAdapterRegistry.adapter(for: activeProfile) else {
            return
        }

        guard let samples = adapter.decode(data, receivedAt: receivedAt) else {
            consecutiveStreamingParserErrors += 1
            if consecutiveStreamingParserErrors >= Self.maximumConsecutiveStreamingParserErrors {
                fail("\(activeProfile.label) sent an invalid force sample.")
            }
            return
        }

        consecutiveStreamingParserErrors = 0
        for sample in samples {
            nextForceSensorSampleNumber &+= 1
            let measurement = MotherboardMeasurement(
                timestamp: sample.receivedAt,
                sampleNumber: nextForceSensorSampleNumber,
                batteryValue: 0,
                sensorLoadsKGF: [],
                aggregateLoadKGF: sample.kilogramsForce
            )
            latestMeasurement = measurement
            batteryValue = nil
            collectTareSample(measurement)
            collectBodyweightSample(measurement)
        }
    }

    private func handleDisconnect(_ message: String?) {
        cleanupTransportSession()
        lastError = message

        guard wantsConnection, reconnectAttempts < 3 else {
            state = wantsConnection ? .failed : .disconnected
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
        cancelBodyweightMeasurement()
        bodyweightKGF = nil
        latestMeasurement = nil
        batteryValue = nil
        connectedDeviceID = nil
        connectedProfile = nil
        activeProfile = nil
        nextForceSensorSampleNumber = 0
        consecutiveStreamingParserErrors = 0
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
        tareCompletionCount += 1
    }

    private func cancelTare() {
        isTaring = false
        tareSamplesCollected = 0
        tareAccumulatorKGF = Array(repeating: 0.0, count: 4)
    }

    private func collectBodyweightSample(_ measurement: MotherboardMeasurement) {
        guard isMeasuringBodyweight, measurement.aggregateLoadKGF.isFinite else { return }
        let previousCount = bodyweightSampleCount
        let nextCount = previousCount + 1
        let previousMean = bodyweightMeanKGF ?? measurement.aggregateLoadKGF
        let divisor = Double(nextCount)
        let mean = previousCount == 0
            ? measurement.aggregateLoadKGF
            : previousMean * (1 - 1 / divisor) + measurement.aggregateLoadKGF / divisor
        bodyweightMeanKGF = mean.isFinite ? mean : previousMean
        bodyweightSampleCount = nextCount
    }

    private func completeBodyweightMeasurement() {
        guard isMeasuringBodyweight else { return }
        bodyweightKGF = bodyweightMeanKGF
        cancelBodyweightMeasurement()
    }

    private func cancelBodyweightMeasurement() {
        bodyweightMeasurementTask?.cancel()
        bodyweightMeasurementTask = nil
        isMeasuringBodyweight = false
        bodyweightMeasurementStartedAt = nil
        bodyweightSampleCount = 0
        bodyweightMeanKGF = nil
    }

    private func scheduleTimeout(after delay: TimeInterval, message: String) {
        cancelTimeout()
        guard delay.isFinite, delay > 0, delay <= Self.maximumBodyweightMeasurementDuration else { return }
        let nanoseconds = UInt64(delay * 1_000_000_000)
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

    deinit {
        timeoutTask?.cancel()
        bodyweightMeasurementTask?.cancel()
        Task { @MainActor [transport] in
            transport.eventHandler = nil
        }
    }
}

protocol MotherboardPeripheralManaging: AnyObject {
    var identifier: UUID { get }
    var name: String? { get }
    var delegate: CBPeripheralDelegate? { get set }
    var services: [CBService]? { get }

    func discoverServices(_ serviceUUIDs: [CBUUID]?)
    func discoverCharacteristics(_ characteristicUUIDs: [CBUUID]?, for service: CBService)
    func setNotifyValue(_ enabled: Bool, for characteristic: CBCharacteristic)
    func writeValue(_ data: Data, for characteristic: CBCharacteristic, type: CBCharacteristicWriteType)
    func connect(using centralManager: CBCentralManager, options: [String: Any]?)
    func cancelConnection(using centralManager: CBCentralManager)
}

final class CoreBluetoothPeripheralAdapter: MotherboardPeripheralManaging {
    private let peripheral: CBPeripheral

    init(_ peripheral: CBPeripheral) {
        self.peripheral = peripheral
    }

    var identifier: UUID { peripheral.identifier }
    var name: String? { peripheral.name }
    var delegate: CBPeripheralDelegate? {
        get { peripheral.delegate }
        set { peripheral.delegate = newValue }
    }
    var services: [CBService]? { peripheral.services }

    func discoverServices(_ serviceUUIDs: [CBUUID]?) {
        peripheral.discoverServices(serviceUUIDs)
    }

    func discoverCharacteristics(_ characteristicUUIDs: [CBUUID]?, for service: CBService) {
        peripheral.discoverCharacteristics(characteristicUUIDs, for: service)
    }

    func setNotifyValue(_ enabled: Bool, for characteristic: CBCharacteristic) {
        peripheral.setNotifyValue(enabled, for: characteristic)
    }

    func writeValue(_ data: Data, for characteristic: CBCharacteristic, type: CBCharacteristicWriteType) {
        peripheral.writeValue(data, for: characteristic, type: type)
    }

    func connect(using centralManager: CBCentralManager, options: [String: Any]?) {
        centralManager.connect(peripheral, options: options)
    }

    func cancelConnection(using centralManager: CBCentralManager) {
        centralManager.cancelPeripheralConnection(peripheral)
    }
}

protocol MotherboardCentralManaging: AnyObject {
    var state: CBManagerState { get }
    func scanForPeripherals(withServices serviceUUIDs: [CBUUID]?, options: [String: Any]?)
    func stopScan()
    func connect(_ peripheral: MotherboardPeripheralManaging, options: [String: Any]?)
    func cancelPeripheralConnection(_ peripheral: MotherboardPeripheralManaging)
}

final class CoreBluetoothCentralAdapter: MotherboardCentralManaging {
    private let centralManager: CBCentralManager

    init(delegate: CBCentralManagerDelegate, queue: DispatchQueue?) {
        centralManager = CBCentralManager(delegate: delegate, queue: queue)
    }

    var state: CBManagerState { centralManager.state }

    func scanForPeripherals(withServices serviceUUIDs: [CBUUID]?, options: [String: Any]?) {
        centralManager.scanForPeripherals(withServices: serviceUUIDs, options: options)
    }

    func stopScan() {
        centralManager.stopScan()
    }

    func connect(_ peripheral: MotherboardPeripheralManaging, options: [String: Any]?) {
        peripheral.connect(using: centralManager, options: options)
    }

    func cancelPeripheralConnection(_ peripheral: MotherboardPeripheralManaging) {
        peripheral.cancelConnection(using: centralManager)
    }
}

@MainActor
final class CoreBluetoothMotherboardTransport: NSObject, MotherboardTransport {
    var eventHandler: ((MotherboardTransportEvent) -> Void)?

    private let centralManagerFactory: (CBCentralManagerDelegate) -> MotherboardCentralManaging
    private var centralManager: MotherboardCentralManaging?
    private var discoveredPeripherals: [UUID: (peripheral: MotherboardPeripheralManaging, profile: ForceSensorProfile)] = [:]
    private var selectedPeripheral: MotherboardPeripheralManaging?
    private var selectedProfile: ForceSensorProfile?
    private var rxCharacteristic: CBCharacteristic?
    private var txCharacteristic: CBCharacteristic?
    private var pendingCharacteristicServiceUUIDs: Set<CBUUID> = []
    private var scanRequested = false
    private var txNotificationsRequested = false
    private var requestedProfile: ForceSensorProfile = .motherboard

    override convenience init() {
        self.init { delegate in
            CoreBluetoothCentralAdapter(delegate: delegate, queue: .main)
        }
    }

    init(centralManagerFactory: @escaping (CBCentralManagerDelegate) -> MotherboardCentralManaging) {
        self.centralManagerFactory = centralManagerFactory
        super.init()
    }

    deinit {
        eventHandler = nil
        centralManager?.stopScan()
        selectedPeripheral?.delegate = nil
        if let selectedPeripheral {
            centralManager?.cancelPeripheralConnection(selectedPeripheral)
        }
    }

    private func isExpectedMotherboard(peripheralName: String?, advertisedLocalName: String?) -> Bool {
        (peripheralName ?? advertisedLocalName) == "Motherboard"
    }

    func configure(profile: ForceSensorProfile) {
        requestedProfile = profile
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
        guard let discovered = discoveredPeripherals[device.id] else {
            eventHandler?(.disconnected("Motherboard is no longer available."))
            return
        }

        let peripheral = discovered.peripheral
        selectedPeripheral = peripheral
        selectedProfile = discovered.profile
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
            withServices: serviceUUIDs(for: requestedProfile).map(CBUUID.init(nsuuid:)),
            options: nil
        )
    }

    private func serviceUUIDs(for profile: ForceSensorProfile) -> Set<UUID> {
        switch profile {
        case .automatic:
            return ForceSensorAdapterRegistry.automaticProfiles.reduce(into: Set<UUID>()) { result, profile in
                result.formUnion(serviceUUIDs(for: profile))
            }
        case .motherboard:
            return [MotherboardProtocol.serviceUUID]
        default:
            return ForceSensorAdapterRegistry.adapter(for: profile)?.contract.serviceUUIDs ?? []
        }
    }

    private func resolvedProfile(
        peripheralName: String?,
        advertisedLocalName: String?,
        advertisedServiceUUIDs: Set<UUID>
    ) -> ForceSensorProfile? {
        let advertisement = ForceSensorAdvertisement(
            name: peripheralName ?? advertisedLocalName,
            serviceUUIDs: advertisedServiceUUIDs
        )

        switch requestedProfile {
        case .automatic:
            if isExpectedMotherboard(peripheralName: peripheralName, advertisedLocalName: advertisedLocalName) {
                return .motherboard
            }
            return ForceSensorAdapterRegistry.automaticProfiles
                .filter { $0 != .motherboard }
                .first { profile in
                    ForceSensorAdapterRegistry.adapter(for: profile)?.matches(advertisement) == true
                }
        case .motherboard:
            return isExpectedMotherboard(peripheralName: peripheralName, advertisedLocalName: advertisedLocalName)
                ? .motherboard
                : nil
        default:
            return ForceSensorAdapterRegistry.adapter(for: requestedProfile)?.matches(advertisement) == true
                ? requestedProfile
                : nil
        }
    }

    private func clearSelectedPeripheral() {
        selectedPeripheral?.delegate = nil
        selectedPeripheral = nil
        rxCharacteristic = nil
        txCharacteristic = nil
        selectedProfile = nil
        pendingCharacteristicServiceUUIDs = []
        txNotificationsRequested = false
    }

    private func reportFailure(_ error: Error?, fallback: String) {
        disconnect()
        eventHandler?(.disconnected(error?.localizedDescription ?? fallback))
    }

    func handleDiscovery(
        peripheral: MotherboardPeripheralManaging,
        advertisementData: [String: Any]
    ) {
        let advertisedLocalName = advertisementData[CBAdvertisementDataLocalNameKey] as? String
        let advertisedServiceUUIDs = Set(
            (advertisementData[CBAdvertisementDataServiceUUIDsKey] as? [CBUUID] ?? []).compactMap {
                UUID(uuidString: $0.uuidString)
            }
        )
        guard let profile = resolvedProfile(
            peripheralName: peripheral.name,
            advertisedLocalName: advertisedLocalName,
            advertisedServiceUUIDs: advertisedServiceUUIDs
        ) else { return }
        let advertisedName = peripheral.name ?? advertisedLocalName ?? profile.label

        discoveredPeripherals[peripheral.identifier] = (peripheral, profile)
        eventHandler?(.discovered(MotherboardDiscoveredDevice(
            id: peripheral.identifier,
            name: advertisedName,
            profile: profile
        )))
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
        handleDiscovery(
            peripheral: CoreBluetoothPeripheralAdapter(peripheral),
            advertisementData: advertisementData
        )
    }

    func centralManager(_ central: CBCentralManager, didConnect peripheral: CBPeripheral) {
        guard selectedPeripheral?.identifier == peripheral.identifier,
              let selectedPeripheral else { return }
        selectedPeripheral.delegate = self
        selectedPeripheral.discoverServices(serviceUUIDs(for: selectedProfile ?? .motherboard).map(CBUUID.init(nsuuid:)))
        eventHandler?(.connected)
    }

    func centralManager(_ central: CBCentralManager, didFailToConnect peripheral: CBPeripheral, error: Error?) {
        guard selectedPeripheral?.identifier == peripheral.identifier else { return }
        reportFailure(error, fallback: "Could not connect to Motherboard.")
    }

    func centralManager(_ central: CBCentralManager, didDisconnectPeripheral peripheral: CBPeripheral, error: Error?) {
        guard selectedPeripheral?.identifier == peripheral.identifier else { return }
        reportFailure(error, fallback: "Motherboard disconnected.")
    }
}

extension CoreBluetoothMotherboardTransport: @preconcurrency CBPeripheralDelegate {
    func peripheral(_ peripheral: CBPeripheral, didDiscoverServices error: Error?) {
        let peripheral = CoreBluetoothPeripheralAdapter(peripheral)
        let profile = selectedProfile ?? .motherboard
        let expectedServiceUUIDs = Set(serviceUUIDs(for: profile).map(CBUUID.init(nsuuid:)))
        guard error == nil,
              let services = peripheral.services,
              expectedServiceUUIDs.isSubset(of: Set(services.map(\.uuid))) else {
            reportFailure(error, fallback: "Sensor BLE service was not found.")
            return
        }

        pendingCharacteristicServiceUUIDs = expectedServiceUUIDs
        for service in services where expectedServiceUUIDs.contains(service.uuid) {
            peripheral.discoverCharacteristics(characteristicUUIDs(for: service.uuid, profile: profile), for: service)
        }
    }

    func peripheral(_ peripheral: CBPeripheral, didDiscoverCharacteristicsFor service: CBService, error: Error?) {
        guard error == nil else {
            reportFailure(error, fallback: "Sensor BLE characteristics could not be discovered.")
            return
        }

        let profile = selectedProfile ?? .motherboard
        for characteristic in service.characteristics ?? [] {
            if let writeUUID = writeCharacteristicUUID(for: profile), characteristic.uuid == writeUUID {
                rxCharacteristic = characteristic
            }
            if let notificationUUID = notificationCharacteristicUUID(for: profile), characteristic.uuid == notificationUUID {
                txCharacteristic = characteristic
            }
        }
        pendingCharacteristicServiceUUIDs.remove(service.uuid)

        guard pendingCharacteristicServiceUUIDs.isEmpty else { return }
        guard rxCharacteristic != nil, txCharacteristic != nil else {
            reportFailure(nil, fallback: "Sensor BLE characteristics were not found.")
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
        reportFailure(error, fallback: "Sensor command could not be sent.")
    }
}

private extension CoreBluetoothMotherboardTransport {
    func notificationCharacteristicUUID(for profile: ForceSensorProfile) -> CBUUID? {
        switch profile {
        case .motherboard:
            CBUUID(nsuuid: MotherboardProtocol.txUUID)
        default:
            ForceSensorAdapterRegistry.adapter(for: profile)
                .flatMap { adapter in
                    adapter.contract.notificationCharacteristics.first
                }
                .map { CBUUID(nsuuid: $0.characteristicUUID) }
        }
    }

    func writeCharacteristicUUID(for profile: ForceSensorProfile) -> CBUUID? {
        switch profile {
        case .motherboard:
            CBUUID(nsuuid: MotherboardProtocol.rxUUID)
        default:
            ForceSensorAdapterRegistry.adapter(for: profile)
                .map { CBUUID(nsuuid: $0.writeCharacteristic.characteristicUUID) }
        }
    }

    func characteristicUUIDs(for serviceUUID: CBUUID, profile: ForceSensorProfile) -> [CBUUID]? {
        switch profile {
        case .motherboard:
            return [CBUUID(nsuuid: MotherboardProtocol.rxUUID), CBUUID(nsuuid: MotherboardProtocol.txUUID)]
        default:
            guard let adapter = ForceSensorAdapterRegistry.adapter(for: profile) else { return nil }
            var identifiers = adapter.contract.notificationCharacteristics
                .filter { CBUUID(nsuuid: $0.serviceUUID) == serviceUUID }
                .map { CBUUID(nsuuid: $0.characteristicUUID) }
            if CBUUID(nsuuid: adapter.writeCharacteristic.serviceUUID) == serviceUUID {
                identifiers.append(CBUUID(nsuuid: adapter.writeCharacteristic.characteristicUUID))
            }
            return identifiers
        }
    }
}
