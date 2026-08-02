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

    @MainActor
    func testFixtureRepeatsSamplesWithCurrentTimestampsThroughMotherboardService() async throws {
        let samples = [
            measurement(timestamp: 0, sampleNumber: 1, load: 0.4),
            measurement(timestamp: 0.05, sampleNumber: 2, load: 5.2),
            measurement(timestamp: 0.10, sampleNumber: 3, load: 0.3)
        ]
        let service = MotherboardBluetoothService(
            transport: SimulatedMotherboardTransport(samples: samples)
        )

        let streamStartedAt = Date()
        service.connect()
        try await Task.sleep(for: .milliseconds(950))

        XCTAssertEqual(service.state, .streaming)
        XCTAssertNotNil(service.latestMeasurement)
        XCTAssertEqual(service.latestMeasurement!.sampleNumber, 1)
        XCTAssertEqual(service.latestMeasurement!.aggregateLoadKGF, 0.4, accuracy: 0.05)
        XCTAssertGreaterThanOrEqual(service.latestMeasurement!.timestamp, streamStartedAt)

        let firstCycleTimestamp = service.latestMeasurement!.timestamp
        try await Task.sleep(for: .milliseconds(350))

        XCTAssertEqual(service.latestMeasurement?.sampleNumber, 2)
        XCTAssertNotNil(service.latestMeasurement)
        XCTAssertEqual(service.latestMeasurement!.aggregateLoadKGF, 5.2, accuracy: 0.05)
        XCTAssertGreaterThan(service.latestMeasurement!.timestamp, firstCycleTimestamp)
    }

    private func measurement(timestamp: TimeInterval, sampleNumber: UInt16, load: Double) -> MotherboardMeasurement {
        MotherboardMeasurement(
            timestamp: Date(timeIntervalSince1970: timestamp),
            sampleNumber: sampleNumber,
            batteryValue: 88,
            sensorLoadsKGF: Array(repeating: load / 4, count: 4),
            aggregateLoadKGF: load
        )
    }
}
#endif
