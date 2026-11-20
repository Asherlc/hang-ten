#if DEBUG
import Combine
import XCTest
@testable import HangTen

final class SimulatedMotherboardTransportTests: XCTestCase {
    func testLoadScriptDropsValuesOutsideSigned24BitADC() {
        let samples = SimulatedMotherboardTransport.samples(
            fromLoadScript: "12, nan, inf, 9000, -9000, 8388.608, -8388.609, -8388.608, 8388.607, 0"
        )
        XCTAssertEqual(samples.map(\.aggregateLoadKGF), [12, -8388.608, 8388.607, 0])
        XCTAssertTrue(SimulatedMotherboardTransport.samples(fromLoadScript: "oops,nan,9000").isEmpty)
    }

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
        // The fixture script repeats, but the transport emits a running UInt16
        // sample counter, so the latest frame is not pinned to a wall-clock slot.
        // Subscribe first and collect exactly two complete fixture cycles.
        let expectedCount = samples.count * 2
        let collected = expectation(description: "two complete fixture cycles")
        var received: [MotherboardMeasurement] = []
        let observation = service.$latestMeasurement
            .compactMap { $0 }
            .prefix(expectedCount)
            .sink { _ in
                collected.fulfill()
            } receiveValue: { measurement in
                received.append(measurement)
            }
        defer {
            observation.cancel()
            service.disconnect()
        }

        service.connect()
        XCTAssertEqual(service.state, .streaming)
        await fulfillment(of: [collected], timeout: 5)

        XCTAssertEqual(received.count, expectedCount)
        var expectedSampleNumber: UInt16 = 0
        var previousTimestamp = streamStartedAt
        for (index, measurement) in received.enumerated() {
            let expected = samples[index % samples.count]
            XCTAssertEqual(measurement.sampleNumber, expectedSampleNumber)
            expectedSampleNumber &+= 1
            XCTAssertEqual(measurement.aggregateLoadKGF, expected.aggregateLoadKGF, accuracy: 0.05)
            for channel in 0..<4 {
                XCTAssertEqual(
                    measurement.sensorLoadsKGF[channel],
                    expected.sensorLoadsKGF[channel],
                    accuracy: 0.05
                )
            }
            XCTAssertGreaterThanOrEqual(measurement.timestamp, streamStartedAt)
            if index > 0 {
                XCTAssertGreaterThan(measurement.timestamp, previousTimestamp)
            }
            previousTimestamp = measurement.timestamp
        }
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
