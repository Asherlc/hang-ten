#if DEBUG
import Foundation

final class SimulatedMotherboardTransport: MotherboardTransport, MotherboardSimulationControlling {
    nonisolated static let tareSamples: [MotherboardMeasurement] = (0..<15).map { index in
        sample(
            timestamp: Double(index) * 0.3,
            number: UInt16(index + 1),
            sensorLoadsKGF: [0.03, 0.02, 0.03, 0.02]
        )
    }

    nonisolated static let bodyweightSamples: [MotherboardMeasurement] = (0..<40).map { index in
        sample(
            timestamp: Double(index + 15) * 0.3,
            number: UInt16(index + 16),
            sensorLoadsKGF: [25.6, 12.8, 25.6, 12.8]
        )
    }

    nonisolated static let activeWorkoutSamples: [MotherboardMeasurement] = [
        sample(timestamp: 9.9, number: 34, sensorLoadsKGF: [40, 16, 24, 16]),
        sample(timestamp: 10.2, number: 35, sensorLoadsKGF: [18, 21.6, 32.4, 21.6]),
        sample(timestamp: 10.5, number: 36, sensorLoadsKGF: [45, 18, 27, 18]),
        sample(timestamp: 10.8, number: 37, sensorLoadsKGF: [14.25, 24.7, 37.05, 24.7])
    ]

    nonisolated static let defaultSamples = tareSamples + bodyweightSamples + activeWorkoutSamples

    var eventHandler: ((MotherboardTransportEvent) -> Void)?

    private let samples: [MotherboardMeasurement]
    private let repeatStartIndex: Int
    private let streamInterval: DispatchTimeInterval
    private let device = MotherboardDiscoveredDevice(
        id: UUID(uuidString: "0F0F0F0F-0000-4000-8000-000000000009")!,
        name: "Motherboard Simulator"
    )
    private var streamTimer: DispatchSourceTimer?
    private var nextSampleIndex = 0
    private var isStreaming = false

    init(
        samples: [MotherboardMeasurement]? = nil,
        streamInterval: DispatchTimeInterval = .milliseconds(300)
    ) {
        self.streamInterval = streamInterval
        if let samples {
            self.samples = samples
            repeatStartIndex = 0
        } else {
            self.samples = Self.defaultSamples
            repeatStartIndex = Self.tareSamples.count + Self.bodyweightSamples.count
        }
    }

    deinit {
        streamTimer?.cancel()
        streamTimer = nil
        eventHandler = nil
    }

    func startScan() {
        eventHandler?(.powerChanged(.poweredOn))
        eventHandler?(.discovered(device))
    }

    func stopScan() {}

    func connect(to device: MotherboardDiscoveredDevice) {
        guard device.id == self.device.id else {
            eventHandler?(.disconnected("Simulated Motherboard was not found."))
            return
        }
        eventHandler?(.connected)
        eventHandler?(.characteristicsReady)
    }

    func disconnect() {
        cancelStream()
    }

    func setTXNotificationsEnabled(_ enabled: Bool) {
        if enabled {
            eventHandler?(.notificationsReady)
        } else {
            cancelStream()
        }
    }

    func write(_ data: Data) {
        switch String(decoding: data, as: UTF8.self) {
        case "C":
            emitCalibration()
        case "S30":
            eventHandler?(.notification(Data("Stream:30\r\n".utf8), Date()))
            scheduleStream()
        default:
            break
        }
    }

    func resetSimulationStream() {
        let shouldResumeStreaming = isStreaming
        cancelStream()
        guard shouldResumeStreaming else { return }
        scheduleStream()
    }

    private func emitCalibration() {
        for sensor in 0..<4 {
            for point in 0..<4 {
                let massKGF = (sensor == 1 || sensor == 2) ? -(point * 10) : point * 10
                let line = "\(sensor),\(point),\(massKGF),\(point * 10_000)\r\n"
                eventHandler?(.notification(Data(line.utf8), Date(timeIntervalSince1970: 0)))
            }
        }
    }

    private func scheduleStream() {
        cancelStream()
        guard !samples.isEmpty else { return }

        isStreaming = true
        let timer = DispatchSource.makeTimerSource(queue: .main)
        timer.setEventHandler { [weak self] in
            self?.emitNextSample()
        }
        timer.schedule(deadline: .now(), repeating: streamInterval)
        streamTimer = timer
        timer.resume()
    }

    private func emitNextSample() {
        guard isStreaming, !samples.isEmpty else { return }
        let sample = samples[nextSampleIndex]
        nextSampleIndex += 1
        if nextSampleIndex >= samples.count {
            nextSampleIndex = repeatStartIndex
        }
        eventHandler?(.notification(Self.rawFrame(for: sample), Date()))
    }

    private func cancelStream() {
        isStreaming = false
        nextSampleIndex = 0
        streamTimer?.cancel()
        streamTimer = nil
    }

    private static func rawFrame(for measurement: MotherboardMeasurement) -> Data {
        let sensorLoads = (0..<4).map { index in
            measurement.sensorLoadsKGF.indices.contains(index)
                ? measurement.sensorLoadsKGF[index]
                : measurement.aggregateLoadKGF / 4
        }
        var bytes = [
            UInt8(measurement.sampleNumber & 0x00FF),
            UInt8(measurement.sampleNumber >> 8),
            UInt8(measurement.batteryValue & 0x00FF),
            UInt8(measurement.batteryValue >> 8)
        ]

        for load in sensorLoads {
            let adc = Int32((load * 1_000).rounded())
            bytes.append(UInt8(truncatingIfNeeded: adc))
            bytes.append(UInt8(truncatingIfNeeded: adc >> 8))
            bytes.append(UInt8(truncatingIfNeeded: adc >> 16))
        }

        let line = bytes.map { String(format: "%02X", $0) }.joined() + "\r\n"
        return Data(line.utf8)
    }

    nonisolated private static func sample(
        timestamp: TimeInterval,
        number: UInt16,
        sensorLoadsKGF: [Double]
    ) -> MotherboardMeasurement {
        MotherboardMeasurement(
            timestamp: Date(timeIntervalSince1970: timestamp),
            sampleNumber: number,
            batteryValue: 88,
            sensorLoadsKGF: sensorLoadsKGF,
            aggregateLoadKGF: sensorLoadsKGF.prefix(3).reduce(0, +)
        )
    }
}
#endif
