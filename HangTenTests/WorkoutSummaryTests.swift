import XCTest
@testable import HangTen

final class WorkoutSummaryTests: XCTestCase {
    func testActualRepCountsAndCycleRestSurviveHistoryRoundTrip() throws {
        let target = WorkoutRepTarget(id: "pull-ups", title: "Pull-ups", minimum: 10)
        let row = WorkoutStepMeasurement(stepID: "reps", plannedActiveDuration: 0, intervals: [],
            peakLoadKGF: nil, sampleCount: 0, status: .unmeasured,
            repResults: [.init(target: target, completed: 8)], cycleWorkEnd: 20, cycleRestDuration: 15)
        let restored = try JSONDecoder().decode(WorkoutStepMeasurement.self, from: JSONEncoder().encode(row))
        XCTAssertEqual(restored.repResults.first?.completed, 8)
        XCTAssertEqual(restored.repResults.first?.target.minimum, 10)
        XCTAssertEqual(restored.cycleRestDuration, 15)
        var legacy = try XCTUnwrap(JSONSerialization.jsonObject(with: JSONEncoder().encode(row)) as? [String: Any])
        for field in ["repResults", "cycleWorkEnd", "cycleRestDuration"] { legacy.removeValue(forKey: field) }
        let old = try JSONDecoder().decode(WorkoutStepMeasurement.self, from: JSONSerialization.data(withJSONObject: legacy))
        XCTAssertTrue(old.repResults.isEmpty)
        XCTAssertNil(old.cycleRestDuration)
    }
    func testGeneralActivityRetainsItsIdentityWithoutInventedHangCues() throws {
        let step = WorkoutStepMeasurement(stepID: "warmup", plannedActiveDuration: 0,
            intervals: [], peakLoadKGF: nil, sampleCount: 0, status: .unmeasured,
            isGeneralActivity: true)
        let restored = try JSONDecoder().decode(WorkoutStepMeasurement.self, from: JSONEncoder().encode(step))
        XCTAssertTrue(restored.isGeneralActivity)
        XCTAssertEqual(WorkoutSummaryFormatting.semanticText(for: restored, unit: .kgf), "General activity")
        var legacy = try XCTUnwrap(JSONSerialization.jsonObject(with: JSONEncoder().encode(step)) as? [String: Any])
        legacy.removeValue(forKey: "isGeneralActivity")
        XCTAssertFalse(try JSONDecoder().decode(WorkoutStepMeasurement.self,
            from: JSONSerialization.data(withJSONObject: legacy)).isGeneralActivity)
    }
    func testInitialWeightTextClearlyDescribesManualStandaloneAndBodyweightModes() {
        XCTAssertNil(
            WorkoutSummaryFormatting.initialWeightText(for: .untracked, unit: .kilograms)
        )
        XCTAssertEqual(
            WorkoutSummaryFormatting.initialWeightText(
                for: .manual(weightKGF: 10, includesBodyweight: false),
                unit: .kilograms
            ),
            "Manual weight: 10.0 kg standalone"
        )
        XCTAssertEqual(
            WorkoutSummaryFormatting.initialWeightText(
                for: .manual(weightKGF: 10, includesBodyweight: true),
                unit: .pounds
            ),
            "Manual weight: +22.0 lb plus bodyweight"
        )
        XCTAssertEqual(
            WorkoutSummaryFormatting.initialWeightText(for: .sensor, unit: .kilograms),
            "Supported scale"
        )
    }

    func testLoadedLiftSummaryUsesSignedLoadCopy() {
        XCTAssertEqual(
            WorkoutStepFormatting.externalLoadText(-5, unit: .kilograms),
            "5 kg assistance"
        )
        XCTAssertEqual(
            WorkoutStepFormatting.externalLoadText(10, unit: .kilograms), "+10 kg")
    }

    func testHistorySummaryModeIsReadOnly() {
        XCTAssertFalse(WorkoutSummaryMode.pending.isReadOnly)
        XCTAssertTrue(WorkoutSummaryMode.history.isReadOnly)
    }

    func testRestSummaryDoesNotClaimHangOrBothHands() {
        let rest = WorkoutStepMeasurement(
            stepID: "rest",
            plannedActiveDuration: 30,
            intervals: [],
            peakLoadKGF: nil,
            sampleCount: 0,
            status: .unmeasured,
            isRest: true
        )

        XCTAssertEqual(WorkoutSummaryFormatting.semanticText(for: rest, unit: .kgf), "Rest")
        XCTAssertFalse(WorkoutSummaryFormatting.semanticText(for: rest, unit: .kgf).contains("Hang"))
        XCTAssertFalse(WorkoutSummaryFormatting.semanticText(for: rest, unit: .kgf).contains("hands"))
    }

    func testLoadedLiftSemanticTextUsesSelectedForceUnit() {
        let lift = WorkoutStepMeasurement(
            stepID: "lift",
            plannedActiveDuration: 20,
            intervals: [],
            peakLoadKGF: nil,
            sampleCount: 0,
            status: .unmeasured,
            handUse: .single,
            side: .left,
            action: .loadedLift,
            repetitions: 3,
            completedRepetitions: 2,
            externalLoadKGF: 10,
            isRest: false
        )

        XCTAssertEqual(
            WorkoutSummaryFormatting.semanticText(for: lift, unit: .lbf),
            "Loaded lift • Left hand • 2 of 3 lifts complete • +22.0 lbf"
        )
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
