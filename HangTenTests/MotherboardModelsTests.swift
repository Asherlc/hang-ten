import XCTest
@testable import HangTen

final class MotherboardModelsTests: XCTestCase {
    func testForceUnitConversionUsesKilogramsForceAsCanonicalValue() {
        XCTAssertEqual(MotherboardForceUnit.kgf.value(fromKilogramsForce: 2), 2, accuracy: 0.0001)
        XCTAssertEqual(MotherboardForceUnit.lbf.value(fromKilogramsForce: 2), 4.40925, accuracy: 0.0001)
        XCTAssertEqual(MotherboardForceUnit.newtons.value(fromKilogramsForce: 2), 19.6133, accuracy: 0.0001)
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

    func testSessionRecordRoundTripsThroughCodable() throws {
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
            )]
        )
        let data = try JSONEncoder().encode(record)
        XCTAssertEqual(try JSONDecoder().decode(WorkoutSessionRecord.self, from: data), record)
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
}
