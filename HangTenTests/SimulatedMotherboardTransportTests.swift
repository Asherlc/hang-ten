#if DEBUG
import XCTest
@testable import HangTen

final class SimulatedMotherboardTransportTests: XCTestCase {
    func testDefaultFixtureStartsWithTareAndRelaxedJugHangPhases() {
        let samples = SimulatedMotherboardTransport.defaultSamples
        let tareSamples = samples.prefix(15)
        let bodyweightSamples = samples.dropFirst(15).prefix(40)

        XCTAssertEqual(tareSamples.count, 15)
        XCTAssertTrue(tareSamples.allSatisfy {
            abs($0.aggregateLoadKGF - 0.08) < 0.0001
        })
        XCTAssertTrue(tareSamples.allSatisfy {
            $0.sensorLoadsKGF == [0.03, 0.02, 0.03, 0.02]
        })
        XCTAssertGreaterThanOrEqual(bodyweightSamples.count, 40)
        XCTAssertTrue(bodyweightSamples.allSatisfy {
            abs($0.aggregateLoadKGF - 64) < 0.0001
        })
        XCTAssertTrue(bodyweightSamples.allSatisfy {
            $0.sensorLoadsKGF == [25.6, 12.8, 25.6, 12.8]
        })
        XCTAssertTrue(samples.allSatisfy {
            abs($0.aggregateLoadKGF - $0.sensorLoadsKGF.prefix(3).reduce(0, +)) < 0.0001
        })
    }

    func testDefaultFixtureProvidesChangingNonEqualBalanceForActiveWorkout() {
        let activeSamples = SimulatedMotherboardTransport.defaultSamples.dropFirst(55)

        XCTAssertGreaterThanOrEqual(activeSamples.count, 4)
        zip(activeSamples.map(\.aggregateLoadKGF), [80, 72, 90, 76]).forEach { actual, expected in
            XCTAssertEqual(actual, expected, accuracy: 0.0001)
        }
        XCTAssertEqual(
            activeSamples.map(\.sensorLoadsKGF),
            [
                [40, 16, 24, 16],
                [18, 21.6, 32.4, 21.6],
                [45, 18, 27, 18],
                [14.25, 24.7, 37.05, 24.7]
            ]
        )
        zip(activeSamples.map(\.leftShare), [0.6, 0.4, 0.6, 0.35]).forEach { actual, expected in
            XCTAssertEqual(actual, expected, accuracy: 0.0001)
        }
        XCTAssertTrue(activeSamples.allSatisfy { $0.leftShare != 0.5 && $0.rightShare != 0.5 })
    }

    func testMaximumPreparationCaptureConsumesOnlyRelaxedJugHangSamples() {
        let relaxedSamples = SimulatedMotherboardTransport.defaultSamples.dropFirst(15).prefix(40)
        let firstActiveSample = SimulatedMotherboardTransport.defaultSamples[55]

        XCTAssertEqual(relaxedSamples.count, 40)
        XCTAssertTrue(relaxedSamples.allSatisfy {
            abs($0.aggregateLoadKGF - 64) < 0.0001
        })
        XCTAssertEqual(firstActiveSample.aggregateLoadKGF, 80)
        XCTAssertNotEqual(firstActiveSample.leftShare, 0.5, accuracy: 0.0001)
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
        XCTAssertEqual(service.latestMeasurement!.sensorLoadsKGF[0], 0.2, accuracy: 0.05)
        XCTAssertEqual(service.latestMeasurement!.sensorLoadsKGF[1], 0, accuracy: 0.05)
        XCTAssertEqual(service.latestMeasurement!.sensorLoadsKGF[2], 0.2, accuracy: 0.05)
        XCTAssertEqual(service.latestMeasurement!.sensorLoadsKGF[3], 0.1, accuracy: 0.05)
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
            sensorLoadsKGF: [load / 2, 0, load / 2, load / 4],
            aggregateLoadKGF: load
        )
    }
}
#endif
