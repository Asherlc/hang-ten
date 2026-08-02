#if DEBUG
import Foundation

final class SimulatedMotherboardTransport: MotherboardTransport {
    nonisolated static let defaultSamples: [MotherboardMeasurement] = [
        sample(timestamp: 0.00, number: 1, load: 0.3),
        sample(timestamp: 0.30, number: 2, load: 4.2),
        sample(timestamp: 0.60, number: 3, load: 8.6),
        sample(timestamp: 0.90, number: 4, load: 1.1),
        sample(timestamp: 1.20, number: 5, load: 0.2),
        sample(timestamp: 1.50, number: 6, load: 5.4),
        sample(timestamp: 1.80, number: 7, load: 7.8),
        sample(timestamp: 2.10, number: 8, load: 0.4)
    ]

    var eventHandler: ((MotherboardTransportEvent) -> Void)?

    private let samples: [MotherboardMeasurement]
    private let device = MotherboardDiscoveredDevice(
        id: UUID(uuidString: "0F0F0F0F-0000-4000-8000-000000000009")!,
        name: "Motherboard Simulator"
    )
    private var streamTimer: DispatchSourceTimer?
    private var nextSampleIndex = 0
    private var isStreaming = false

    init(samples: [MotherboardMeasurement] = SimulatedMotherboardTransport.defaultSamples) {
        self.samples = samples
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
        if !enabled {
            cancelStream()
        }
    }

    func write(_ data: Data) {
        switch String(decoding: data, as: UTF8.self) {
        case "C":
            emitCalibration()
        case "S30":
            scheduleStream()
        default:
            break
        }
    }

    private func emitCalibration() {
        for sensor in 0..<4 {
            for point in 0..<4 {
                let line = "\(sensor),\(point),\(point * 10),\(point * 10_000)\r\n"
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
        timer.schedule(deadline: .now(), repeating: .milliseconds(300))
        streamTimer = timer
        timer.resume()
    }

    private func emitNextSample() {
        guard isStreaming, !samples.isEmpty else { return }
        let sample = samples[nextSampleIndex]
        nextSampleIndex = (nextSampleIndex + 1) % samples.count
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

    nonisolated private static func sample(timestamp: TimeInterval, number: UInt16, load: Double) -> MotherboardMeasurement {
        MotherboardMeasurement(
            timestamp: Date(timeIntervalSince1970: timestamp),
            sampleNumber: number,
            batteryValue: 88,
            sensorLoadsKGF: Array(repeating: load / 4, count: 4),
            aggregateLoadKGF: load
        )
    }
}
#endif
