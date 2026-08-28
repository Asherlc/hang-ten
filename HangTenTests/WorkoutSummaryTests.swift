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

    func testLoadAdjustmentTextDescribesAddedWeightAndPulleyAssistanceInGlobalLoadAdjustmentUnit() {
        XCTAssertEqual(
            WorkoutSummaryFormatting.loadAdjustmentText(for: 10, unit: .pounds),
            "Added weight: +22.0 lb"
        )
        XCTAssertEqual(
            WorkoutSummaryFormatting.loadAdjustmentText(for: -10, unit: .kilograms),
            "Pulley assistance: -10.0 kg"
        )
    }

    func testLoadAdjustmentTextOmitsNoAdjustment() {
        XCTAssertNil(WorkoutSummaryFormatting.loadAdjustmentText(for: 0, unit: .kilograms))
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

    func testStepRowTitleUsesPersistedTitleAndFallsBackForLegacySessions() {
        let measuredStep = WorkoutStepMeasurement(
            stepID: "edge-if-001",
            plannedActiveDuration: 7,
            intervals: [],
            peakLoadKGF: nil,
            sampleCount: 0,
            status: .unmeasured
        )
        let titledSession = WorkoutSessionRecord(
            id: UUID(),
            planID: "plan",
            planTitle: "Test plan",
            recordedAt: Date(timeIntervalSince1970: 100),
            startDate: Date(timeIntervalSince1970: 0),
            endDate: Date(timeIntervalSince1970: 60),
            motherboardIdentifier: nil,
            batteryValue: nil,
            steps: [measuredStep],
            stepTitles: ["Maximum hang"]
        )
        let legacySession = WorkoutSessionRecord(
            id: UUID(),
            planID: "legacy-plan",
            planTitle: "Legacy plan",
            recordedAt: Date(timeIntervalSince1970: 100),
            startDate: Date(timeIntervalSince1970: 0),
            endDate: Date(timeIntervalSince1970: 60),
            motherboardIdentifier: nil,
            batteryValue: nil,
            steps: [measuredStep]
        )

        let persistedTitle = WorkoutSummaryFormatting.stepRowTitle(for: titledSession, at: 0)
        XCTAssertEqual(persistedTitle, "Maximum hang")
        XCTAssertNotEqual(persistedTitle, measuredStep.stepID)
        XCTAssertEqual(
            WorkoutSummaryFormatting.stepRowTitle(for: legacySession, at: 0),
            "Step 1"
        )
    }
}
