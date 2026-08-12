import XCTest
@testable import HangTen

final class WorkoutSummaryTests: XCTestCase {
    func testHistorySummaryModeIsReadOnly() {
        XCTAssertFalse(WorkoutSummaryMode.pending.isReadOnly)
        XCTAssertTrue(WorkoutSummaryMode.history.isReadOnly)
    }

    func testSummaryUsesActualLoadedDurationAndPeakInSelectedUnit() {
        let step = WorkoutStepMeasurement(
            stepID: "step",
            plannedActiveDuration: 7,
            intervals: [LoadInterval(start: 1, end: 4)],
            peakLoadKGF: 2,
            sampleCount: 20,
            status: .measured
        )

        XCTAssertEqual(step.actualLoadedDuration, 3, accuracy: 0.0001)
        XCTAssertEqual(
            MotherboardForceUnit.lbf.value(fromKilogramsForce: step.peakLoadKGF!),
            4.40925,
            accuracy: 0.0001
        )
    }

    func testBodyweightBaselineTextUsesSelectedUnitAndOmitsAbsentBaseline() {
        XCTAssertEqual(
            WorkoutSummaryFormatting.bodyweightBaselineText(for: 60, unit: .lbf),
            "Captured baseline: 132.3 lbf"
        )
        XCTAssertNil(WorkoutSummaryFormatting.bodyweightBaselineText(for: nil, unit: .kgf))
    }

    func testGranularSampleTextUsesTheRecordedSensorProfile() throws {
        let measurement = MotherboardMeasurement(
            timestamp: Date(timeIntervalSince1970: 1),
            sampleNumber: 1,
            batteryValue: 0,
            sensorLoadsKGF: [],
            aggregateLoadKGF: 12
        )

        let text = try XCTUnwrap(
            WorkoutSummaryFormatting.granularSampleCountText(
                for: [measurement],
                profile: .progressor
            )
        )

        XCTAssertEqual(text, "1 granular Tindeq Progressor sample")
    }
}
