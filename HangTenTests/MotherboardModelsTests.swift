import XCTest
@testable import HangTen

final class MotherboardModelsTests: XCTestCase {
    func testForceUnitConversionUsesKilogramsForceAsCanonicalValue() {
        XCTAssertEqual(MotherboardForceUnit.kgf.value(fromKilogramsForce: 2), 2, accuracy: 0.0001)
        XCTAssertEqual(MotherboardForceUnit.lbf.value(fromKilogramsForce: 2), 4.40925, accuracy: 0.0001)
        XCTAssertEqual(MotherboardForceUnit.newtons.value(fromKilogramsForce: 2), 19.6133, accuracy: 0.0001)
    }

    func testMeasurementDistributesCalibratedChannelsAcrossBoardSides() {
        let balanced = measurement(sensorLoads: [2, 1, 3, 4], aggregate: 10)
        XCTAssertEqual(balanced.leftLoadKGF, 5, accuracy: 0.0001)
        XCTAssertEqual(balanced.rightLoadKGF, 5, accuracy: 0.0001)
        XCTAssertEqual(balanced.leftShare, 0.5, accuracy: 0.0001)
        XCTAssertEqual(balanced.rightShare, 0.5, accuracy: 0.0001)

        let uneven = measurement(sensorLoads: [3, 1, 1, 5], aggregate: 10)
        XCTAssertEqual(uneven.leftShare, 0.4, accuracy: 0.0001)
        XCTAssertEqual(uneven.rightShare, 0.6, accuracy: 0.0001)
    }

    func testMeasurementBodyweightPercentageUsesAggregateLoad() {
        let measurement = measurement(sensorLoads: [2.5, 2.5, 2.5, 2.5], aggregate: 10)
        XCTAssertEqual(measurement.bodyweightPercentage(for: 20), 50, accuracy: 0.0001)
    }

    func testMeasurementIgnoresNonFiniteAndNegativeSensorLoads() {
        let measurement = measurement(sensorLoads: [.nan, -1, .infinity, 2], aggregate: 10)

        XCTAssertEqual(measurement.leftLoadKGF, 0, accuracy: 0.0001)
        XCTAssertEqual(measurement.rightLoadKGF, 2, accuracy: 0.0001)
        XCTAssertEqual(measurement.leftShare, 0, accuracy: 0.0001)
        XCTAssertEqual(measurement.rightShare, 1, accuracy: 0.0001)
    }

    func testMeasurementSideLoadsSaturateFiniteOverflow() {
        let largestFinite = Double.greatestFiniteMagnitude
        let measurement = measurement(
            sensorLoads: [largestFinite, largestFinite, largestFinite, largestFinite],
            aggregate: largestFinite
        )

        XCTAssertEqual(measurement.leftLoadKGF, largestFinite)
        XCTAssertEqual(measurement.rightLoadKGF, largestFinite)
        XCTAssertTrue(measurement.leftLoadKGF.isFinite)
        XCTAssertTrue(measurement.rightLoadKGF.isFinite)
        XCTAssertEqual(measurement.leftShare, 0.5, accuracy: 0.0001)
        XCTAssertEqual(measurement.rightShare, 0.5, accuracy: 0.0001)
    }

    func testMeasurementBodyweightPercentageReturnsZeroForInvalidBaseline() {
        let measurement = measurement(sensorLoads: [2.5, 2.5, 2.5, 2.5], aggregate: 10)

        XCTAssertEqual(measurement.bodyweightPercentage(for: 0), 0, accuracy: 0.0001)
        XCTAssertEqual(measurement.bodyweightPercentage(for: .nan), 0, accuracy: 0.0001)
        XCTAssertEqual(measurement.bodyweightPercentage(for: .infinity), 0, accuracy: 0.0001)
    }

    func testMeasurementBodyweightPercentageSaturatesFiniteOverflow() {
        let largestFinite = Double.greatestFiniteMagnitude
        let measurement = measurement(sensorLoads: [], aggregate: largestFinite)

        XCTAssertEqual(measurement.bodyweightPercentage(for: 1), largestFinite)
        XCTAssertTrue(measurement.bodyweightPercentage(for: 1).isFinite)
    }

    func testBodyweightCaptureDurationDefaultsClampsAndPersists() {
        let suite = "MotherboardModelsBodyweightDurationTests"
        let defaults = UserDefaults(suiteName: suite)!
        defaults.removePersistentDomain(forName: suite)

        let initial = MotherboardSettingsStore(defaults: defaults)
        XCTAssertEqual(initial.bodyweightCaptureDuration, 5, accuracy: 0.0001)

        defaults.set(1, forKey: "motherboard.bodyweightCaptureDuration")
        XCTAssertEqual(MotherboardSettingsStore(defaults: defaults).bodyweightCaptureDuration, 3, accuracy: 0.0001)
        defaults.set(20, forKey: "motherboard.bodyweightCaptureDuration")
        XCTAssertEqual(MotherboardSettingsStore(defaults: defaults).bodyweightCaptureDuration, 10, accuracy: 0.0001)
        defaults.set(Double.nan, forKey: "motherboard.bodyweightCaptureDuration")
        XCTAssertEqual(MotherboardSettingsStore(defaults: defaults).bodyweightCaptureDuration, 5, accuracy: 0.0001)
        defaults.set(Double.infinity, forKey: "motherboard.bodyweightCaptureDuration")
        XCTAssertEqual(MotherboardSettingsStore(defaults: defaults).bodyweightCaptureDuration, 5, accuracy: 0.0001)
        defaults.set(7.6, forKey: "motherboard.bodyweightCaptureDuration")
        XCTAssertEqual(MotherboardSettingsStore(defaults: defaults).bodyweightCaptureDuration, 8, accuracy: 0.0001)

        initial.bodyweightCaptureDuration = 1
        XCTAssertEqual(initial.bodyweightCaptureDuration, 3, accuracy: 0.0001)
        initial.bodyweightCaptureDuration = 7.4
        XCTAssertEqual(initial.bodyweightCaptureDuration, 7, accuracy: 0.0001)
        XCTAssertEqual(MotherboardSettingsStore(defaults: defaults).bodyweightCaptureDuration, 7, accuracy: 0.0001)
    }

    func testMeasurementRoundTripsRawADCValuesThroughCodable() throws {
        let measurement = MotherboardMeasurement(
            timestamp: Date(timeIntervalSince1970: 123),
            sampleNumber: 42,
            batteryValue: 88,
            rawADCValues: [0x000102, -2, 0x7FFFFF, -0x800000],
            sensorLoadsKGF: [1.25, -0.5, 3.75, 0],
            aggregateLoadKGF: 4.5
        )

        let decoded = try JSONDecoder().decode(
            MotherboardMeasurement.self,
            from: JSONEncoder().encode(measurement)
        )

        XCTAssertEqual(decoded, measurement)
    }

    func testMeasurementDecodesWithoutRawADCValues() throws {
        let measurement = MotherboardMeasurement(
            timestamp: Date(timeIntervalSince1970: 123),
            sampleNumber: 42,
            batteryValue: 88,
            rawADCValues: [1, 2, 3, 4],
            sensorLoadsKGF: [1.25, -0.5, 3.75, 0],
            aggregateLoadKGF: 4.5
        )
        let data = try JSONEncoder().encode(measurement)
        var object = try XCTUnwrap(JSONSerialization.jsonObject(with: data) as? [String: Any])
        object.removeValue(forKey: "rawADCValues")

        let decoded = try JSONDecoder().decode(
            MotherboardMeasurement.self,
            from: JSONSerialization.data(withJSONObject: object)
        )

        XCTAssertEqual(decoded.timestamp, measurement.timestamp)
        XCTAssertEqual(decoded.sampleNumber, measurement.sampleNumber)
        XCTAssertEqual(decoded.batteryValue, measurement.batteryValue)
        XCTAssertEqual(decoded.rawADCValues, [])
        XCTAssertEqual(decoded.sensorLoadsKGF, measurement.sensorLoadsKGF)
        XCTAssertEqual(decoded.aggregateLoadKGF, measurement.aggregateLoadKGF)
    }

    func testSessionRecordDecodesWithoutOptionalBodyweightOrGranularSamples() throws {
        let record = WorkoutSessionRecord(
            id: UUID(uuidString: "AAAAAAAA-BBBB-CCCC-DDDD-EEEEEEEEEEEE")!,
            planID: "plan",
            planTitle: "Test plan",
            recordedAt: Date(timeIntervalSince1970: 100),
            startDate: Date(timeIntervalSince1970: 0),
            endDate: Date(timeIntervalSince1970: 600),
            motherboardIdentifier: nil,
            batteryValue: nil,
            steps: []
        )
        let data = try JSONEncoder().encode(record)
        var object = try XCTUnwrap(JSONSerialization.jsonObject(with: data) as? [String: Any])
        object.removeValue(forKey: "bodyweightKGF")
        object.removeValue(forKey: "motherboardMeasurements")
        object.removeValue(forKey: "motherboardMeasurementsTruncated")
        let legacyData = try JSONSerialization.data(withJSONObject: object)

        let decoded = try JSONDecoder().decode(WorkoutSessionRecord.self, from: legacyData)
        XCTAssertNil(decoded.bodyweightKGF)
        XCTAssertEqual(decoded.motherboardMeasurements, [])
        XCTAssertFalse(decoded.motherboardMeasurementsTruncated)
    }

    func testSettingsUseDefaultsAndRoundTripThroughUserDefaults() {
        let defaults = UserDefaults(suiteName: "MotherboardModelsTests")!
        defaults.removePersistentDomain(forName: "MotherboardModelsTests")
        let first = MotherboardSettingsStore(defaults: defaults)
        XCTAssertEqual(first.forceUnit, .kgf)
        XCTAssertEqual(first.thresholdKGF, 2.5, accuracy: 0.0001)

        first.forceUnit = .newtons
        first.thresholdKGF = 4.25
        let second = MotherboardSettingsStore(defaults: defaults)
        XCTAssertEqual(second.forceUnit, .newtons)
        XCTAssertEqual(second.thresholdKGF, 4.25, accuracy: 0.0001)
    }

    func testThresholdNormalizesPersistedAndAssignedValuesToUIRange() {
        let suite = "MotherboardModelsThresholdTests"
        let defaults = UserDefaults(suiteName: suite)!
        defaults.removePersistentDomain(forName: suite)
        defaults.set(75.0, forKey: "motherboard.thresholdKGF")

        let store = MotherboardSettingsStore(defaults: defaults)
        XCTAssertEqual(store.thresholdKGF, 50, accuracy: 0.0001)

        store.thresholdKGF = 0
        XCTAssertEqual(store.thresholdKGF, 2.5, accuracy: 0.0001)
        store.thresholdKGF = 75
        XCTAssertEqual(store.thresholdKGF, 50, accuracy: 0.0001)
        store.thresholdKGF = .infinity
        XCTAssertEqual(store.thresholdKGF, 2.5, accuracy: 0.0001)
        XCTAssertEqual(defaults.double(forKey: "motherboard.thresholdKGF"), 2.5, accuracy: 0.0001)
    }

    func testSessionRecordRoundTripsMultipleGranularMeasurementsThroughCodable() throws {
        let record = WorkoutSessionRecord(
            id: UUID(uuidString: "AAAAAAAA-BBBB-CCCC-DDDD-EEEEEEEEEEEE")!,
            planID: "plan",
            planTitle: "Test plan",
            recordedAt: Date(timeIntervalSince1970: 100),
            startDate: Date(timeIntervalSince1970: 0),
            endDate: Date(timeIntervalSince1970: 600),
            motherboardIdentifier: "Motherboard-1",
            batteryValue: 80,
            steps: [WorkoutStepMeasurement(
                stepID: "step-1",
                plannedActiveDuration: 7,
                intervals: [LoadInterval(start: 1, end: 6)],
                peakLoadKGF: 12,
                sampleCount: 150,
                status: .measured
            )],
            motherboardMeasurements: [
                MotherboardMeasurement(
                    timestamp: Date(timeIntervalSince1970: 120),
                    sampleNumber: 101,
                    batteryValue: 79,
                    rawADCValues: [120, -121, 122, -123],
                    sensorLoadsKGF: [1.5, 2.5, 3.5, 4.5],
                    aggregateLoadKGF: 12
                ),
                MotherboardMeasurement(
                    timestamp: Date(timeIntervalSince1970: 121),
                    sampleNumber: 102,
                    batteryValue: 78,
                    rawADCValues: [220, -221, 222, -223],
                    sensorLoadsKGF: [5.5, 6.5, 7.5, 8.5],
                    aggregateLoadKGF: 28
                )
            ],
            motherboardMeasurementsTruncated: true
        )
        let data = try JSONEncoder().encode(record)
        XCTAssertEqual(try JSONDecoder().decode(WorkoutSessionRecord.self, from: data), record)
        XCTAssertTrue(try JSONDecoder().decode(WorkoutSessionRecord.self, from: data).motherboardMeasurementsTruncated)
    }

    func testGranularMeasurementCollectorExcludesSetupAndPausedSamples() {
        var collector = MotherboardWorkoutMeasurementCollector()
        let measurement = granularMeasurement(sampleNumber: 1, at: 100, load: 8)

        collector.capture(
            measurement,
            startedAt: nil,
            countdownRemaining: 0,
            workoutElapsed: 0,
            planDuration: 10
        )

        XCTAssertTrue(collector.measurements.isEmpty)
    }

    func testGranularMeasurementCollectorExcludesPreCountdownSamples() {
        var collector = MotherboardWorkoutMeasurementCollector()
        let startedAt = Date(timeIntervalSince1970: 100)

        collector.capture(
            granularMeasurement(sampleNumber: 1, at: 99, load: 8),
            startedAt: startedAt,
            countdownRemaining: 1,
            workoutElapsed: 0,
            planDuration: 10
        )

        XCTAssertTrue(collector.measurements.isEmpty)
    }

    func testGranularMeasurementCollectorIncludesActiveAndRestIntervalSamples() {
        var collector = MotherboardWorkoutMeasurementCollector()
        let startedAt = Date(timeIntervalSince1970: 100)
        let activeSample = granularMeasurement(sampleNumber: 1, at: 102, load: 8)
        let restSample = granularMeasurement(sampleNumber: 2, at: 106, load: 0)

        collector.capture(
            activeSample,
            startedAt: startedAt,
            countdownRemaining: 0,
            workoutElapsed: 2,
            planDuration: 10
        )
        collector.capture(
            restSample,
            startedAt: startedAt,
            countdownRemaining: 0,
            workoutElapsed: 6,
            planDuration: 10
        )

        XCTAssertEqual(collector.measurements, [activeSample, restSample])
    }

    func testGranularMeasurementCollectorExcludesSamplesAfterPlanDuration() {
        var collector = MotherboardWorkoutMeasurementCollector()

        collector.capture(
            granularMeasurement(sampleNumber: 1, at: 110, load: 8),
            startedAt: Date(timeIntervalSince1970: 100),
            countdownRemaining: 0,
            workoutElapsed: 10,
            planDuration: 10
        )

        XCTAssertTrue(collector.measurements.isEmpty)
    }

    func testGranularMeasurementCollectorCapsEligibleSamplesAndReportsTruncation() {
        var collector = MotherboardWorkoutMeasurementCollector()
        let startedAt = Date(timeIntervalSince1970: 100)

        for sampleNumber in 0...20_000 {
            collector.capture(
                granularMeasurement(sampleNumber: UInt16(sampleNumber), at: 101, load: 1),
                startedAt: startedAt,
                countdownRemaining: 0,
                workoutElapsed: 1,
                planDuration: 10
            )
        }

        XCTAssertEqual(collector.measurements.count, 20_000)
        XCTAssertTrue(collector.didTruncate)
        XCTAssertEqual(collector.measurements.last?.sampleNumber, 19_999)
    }

    func testGranularMeasurementCollectorResetClearsMeasurementsAndTruncation() {
        var collector = MotherboardWorkoutMeasurementCollector()
        let startedAt = Date(timeIntervalSince1970: 100)

        for sampleNumber in 0...20_000 {
            collector.capture(
                granularMeasurement(sampleNumber: UInt16(sampleNumber), at: 101, load: 1),
                startedAt: startedAt,
                countdownRemaining: 0,
                workoutElapsed: 1,
                planDuration: 10
            )
        }

        collector.reset()

        XCTAssertTrue(collector.measurements.isEmpty)
        XCTAssertFalse(collector.didTruncate)
    }

    func testGranularMeasurementCollectorAppendsEveryEligiblePublicationWithoutLoadFiltering() {
        var collector = MotherboardWorkoutMeasurementCollector()
        let startedAt = Date(timeIntervalSince1970: 100)
        let samples = [
            granularMeasurement(sampleNumber: 1, at: 101, load: 0),
            granularMeasurement(sampleNumber: 2, at: 102, load: 0.1),
            granularMeasurement(sampleNumber: 3, at: 103, load: 80)
        ]

        for (elapsed, sample) in zip([1.0, 2.0, 3.0], samples) {
            collector.capture(
                sample,
                startedAt: startedAt,
                countdownRemaining: 0,
                workoutElapsed: elapsed,
                planDuration: 10
            )
        }

        XCTAssertEqual(collector.measurements, samples)
    }

    func testRestStepsAreDistinctFromActiveStepsWhenTheirFullDurationIsRest() {
        let rest = WorkoutStep(
            id: "rest",
            number: 1,
            title: "Rest",
            instruction: "Shake out.",
            accessory: "Recovery",
            duration: 10,
            phase: .rest,
            targets: []
        )
        let hang = WorkoutStep(
            id: "hang",
            number: 2,
            title: "Hang",
            instruction: "Hang on.",
            accessory: "Active",
            duration: 10,
            phase: .hang,
            targets: []
        )

        XCTAssertEqual(rest.activeDuration, rest.duration)
        XCTAssertTrue(rest.isRestStep)
        XCTAssertFalse(hang.isRestStep)
    }

    private func measurement(sensorLoads: [Double], aggregate: Double) -> MotherboardMeasurement {
        MotherboardMeasurement(
            timestamp: Date(timeIntervalSince1970: 0),
            sampleNumber: 1,
            batteryValue: 100,
            sensorLoadsKGF: sensorLoads,
            aggregateLoadKGF: aggregate
        )
    }

    private func granularMeasurement(
        sampleNumber: UInt16,
        at time: TimeInterval,
        load: Double
    ) -> MotherboardMeasurement {
        MotherboardMeasurement(
            timestamp: Date(timeIntervalSince1970: time),
            sampleNumber: sampleNumber,
            batteryValue: 80,
            rawADCValues: [1, -2, 3, -4],
            sensorLoadsKGF: [load, 0, 0, 0],
            aggregateLoadKGF: load
        )
    }
}
