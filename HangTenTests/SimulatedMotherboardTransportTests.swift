#if DEBUG
import XCTest
@testable import HangTen

final class SimulatedMotherboardTransportTests: XCTestCase {
    func testDefaultFixtureStartsWithTareAndRelaxedJugHangPhases() {
        let samples = SimulatedMotherboardTransport.defaultSamples
        let tareSamples = samples.prefix(15)
        let bodyweightSamples = samples.dropFirst(15).prefix(18)

        XCTAssertEqual(tareSamples.count, 15)
        XCTAssertTrue(tareSamples.allSatisfy { $0.aggregateLoadKGF == 0.08 })
        XCTAssertEqual(bodyweightSamples.count, 18)
        XCTAssertTrue(bodyweightSamples.allSatisfy { $0.aggregateLoadKGF == 64 })
        XCTAssertTrue(bodyweightSamples.allSatisfy {
            $0.sensorLoadsKGF == [19.2, 12.8, 19.2, 12.8]
        })
    }

    func testDefaultFixtureProvidesChangingNonEqualBalanceForActiveWorkout() {
        let activeSamples = SimulatedMotherboardTransport.defaultSamples.dropFirst(33)

        XCTAssertGreaterThanOrEqual(activeSamples.count, 4)
        XCTAssertEqual(activeSamples.map(\.aggregateLoadKGF), [80, 72, 90, 76])
        zip(activeSamples.map(\.leftShare), [0.6, 0.4, 0.6, 0.35]).forEach { actual, expected in
            XCTAssertEqual(actual, expected, accuracy: 0.0001)
        }
        XCTAssertTrue(activeSamples.allSatisfy { $0.leftShare != 0.5 && $0.rightShare != 0.5 })
    }

    @MainActor
    func testFixtureRepeatsSamplesWithCurrentTimestampsThroughMotherboardService() async throws {
        let samples = [
            measurement(timestamp: 0, sampleNumber: 1, load: 0.4),
            measurement(timestamp: 0.05, sampleNumber: 2, load: 5.2),
            measurement(timestamp: 0.10, sampleNumber: 3, load: 0.3)
        ]
        let service = MotherboardBluetoothService(
            transport: SimulatedMotherboardTransport(
                samples: samples,
                streamInterval: .milliseconds(300)
            )
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
