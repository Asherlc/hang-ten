import XCTest
@testable import HangTen

final class PlanFlowPresentationTests: XCTestCase {
    func testIdenticalStepsWithoutDeclaredRepetitionStaySeparate() {
        let steps = [step(number: 1), step(number: 2)]
        let groups = PlanFlowPresentation.groups(for: steps)
        XCTAssertEqual(groups.count, 2)
        XCTAssertTrue(groups.allSatisfy { $0.repeatCount == 1 })
        XCTAssertEqual(groups.flatMap(\.sourceSteps), steps)
    }

    func testTenDeclaredRunsShowOnePrescription() throws {
        let steps = (1...10).map { step(number: $0) }
        let groups = PlanFlowPresentation.groups(for: steps, repeats: [
            WorkoutStepRepeat(stepRange: 0..<10, repeatCount: 10)
        ])
        XCTAssertEqual(groups.count, 1)
        let group = try XCTUnwrap(groups.first)
        XCTAssertEqual(group.repeatCount, 10)
        XCTAssertEqual(group.sourceSteps, steps)
        XCTAssertEqual(group.children.count, 1)
        XCTAssertEqual(group.children.first?.title, "Edge hang")
        XCTAssertEqual(group.duration, 70)
    }

    func testDeclaredRangeDoesNotAbsorbAnIdenticalFollowingCycle() throws {
        let steps = (1...3).flatMap { repeatNumber in
            [step(number: repeatNumber * 2 - 1), step(number: repeatNumber * 2, phase: .rest)]
        }
        let groups = PlanFlowPresentation.groups(for: steps, repeats: [
            WorkoutStepRepeat(stepRange: 0..<4, repeatCount: 2)
        ])
        XCTAssertEqual(groups.count, 3)
        XCTAssertEqual(groups[0].repeatCount, 2)
        XCTAssertEqual(groups[0].children.map(\.title), ["Edge hang", "Rest"])
        XCTAssertEqual(groups[0].children.last?.nextInstruction, "Hang for 7 seconds.")
        XCTAssertNil(groups.last?.nextInstruction)
        XCTAssertEqual(groups.reduce(0) { $0 + $1.duration }, 30)
        XCTAssertEqual(groups.flatMap(\.sourceSteps), steps)
    }

    func testAuthoredTemplateLabelsPreserveOriginalOccurrenceLabels() {
        let titles = [
            "7/3 · set 1 · 20 mm edge · rep 1 of 3",
            "7/3 · set 1 · 20 mm edge · rep 2 of 3",
            "7/3 · set 1 · 20 mm edge · rep 3 of 3"
        ]
        let steps = titles.enumerated().map { step(number: $0.offset + 1, title: $0.element) }
        let groups = PlanFlowPresentation.groups(for: steps, repeats: [
            WorkoutStepRepeat(stepRange: 0..<3, repeatCount: 3, patternTitles: ["7/3 · 20 mm edge"])
        ])
        XCTAssertEqual(groups.count, 1)
        XCTAssertEqual(groups.first?.children.first?.title, "7/3 · 20 mm edge")
        XCTAssertEqual(groups.flatMap(\.sourceSteps).map(\.title), titles)
    }

    func testUnmarkedNumberedTitlesAreNotRewrittenOrGrouped() {
        let titles = ["Hang · rep 1", "Hang · rep 2", "10 mm hang", "20 mm hang", "5 pull-ups", "10 pull-ups"]
        let steps = titles.enumerated().map { step(number: $0.offset + 1, title: $0.element) }
        let groups = PlanFlowPresentation.groups(for: steps)
        XCTAssertEqual(groups.count, titles.count)
        XCTAssertEqual(groups.map(\.title), titles)
    }

    func testInnerMatchesAreNotInferredInsideAnAuthoredRepeat() throws {
        let steps = (1...3).flatMap { round in
            [step(number: round * 3 - 2), step(number: round * 3 - 1), step(number: round * 3, phase: .rest)]
        }
        let groups = PlanFlowPresentation.groups(for: steps, repeats: [
            WorkoutStepRepeat(stepRange: 0..<6, repeatCount: 2)
        ])
        let group = try XCTUnwrap(groups.first)
        XCTAssertEqual(group.repeatCount, 2)
        XCTAssertEqual(group.children.count, 3)
        XCTAssertTrue(group.children.allSatisfy { $0.repeatCount == 1 && $0.children.isEmpty })
        XCTAssertEqual(groups.flatMap(\.sourceSteps), steps)
    }

    func testMaxHangsKeepTheFinalHangWithoutAnInventedRecovery() throws {
        let plan = try XCTUnwrap(PlanCatalog.plan(id: "research.max-hangs"))
        let groups = PlanFlowPresentation.groups(for: plan)
        XCTAssertEqual(groups.count, 2)
        XCTAssertEqual(groups.first?.repeatCount, 4)
        XCTAssertEqual(groups.first?.children.map { $0.sourceSteps[0].duration }, [10, 180])
        XCTAssertEqual(groups.last?.repeatCount, 1)
        XCTAssertEqual(groups.last?.sourceSteps, [plan.steps.last!])
        XCTAssertEqual(groups.reduce(0) { $0 + $1.duration }, 770)
    }

    func testRPTCDeclaredCyclesKeepExceptionalFinalRecoverySeparate() throws {
        let plan = try XCTUnwrap(PlanCatalog.plan(id: "rptc.seven-three-repeaters"))
        let groups = PlanFlowPresentation.groups(for: plan)
        XCTAssertEqual(groups.count, 4)
        XCTAssertEqual(groups.first?.repeatCount, 6)
        XCTAssertEqual(groups.first?.children.map { $0.sourceSteps[0].duration }, [7, 3])
        XCTAssertEqual(groups.dropFirst().flatMap(\.sourceSteps).map(\.duration), [7, 173, 180])
        XCTAssertEqual(groups.flatMap(\.sourceSteps), plan.steps)
    }

    func testRestPreviewSkipsConsecutiveRestsAndRetainsTheirSourceContent() throws {
        let steps = [step(number: 1, phase: .rest), step(number: 2, phase: .rest),
                     step(number: 3, instruction: "Use the next grip.")]
        let groups = PlanFlowPresentation.groups(for: steps, repeats: [
            WorkoutStepRepeat(stepRange: 0..<2, repeatCount: 2)
        ])
        let rest = try XCTUnwrap(groups.first?.children.first)
        XCTAssertEqual(rest.nextInstruction, "Use the next grip.")
        XCTAssertEqual(rest.sourceSteps.first?.instruction, "")
        XCTAssertEqual(rest.sourceSteps.first?.accessory, "3s rest")
        XCTAssertEqual(groups.flatMap(\.sourceSteps), steps)
    }

    func testRestPreviewOmitsAnInstructionThatDoesNotApplyToEveryRun() {
        let steps = [step(number: 1), step(number: 2, phase: .rest), step(number: 3),
                     step(number: 4, phase: .rest), step(number: 5, instruction: "Use the next grip.")]
        let groups = PlanFlowPresentation.groups(for: steps, repeats: [
            WorkoutStepRepeat(stepRange: 0..<4, repeatCount: 2)
        ])
        XCTAssertNil(groups.first?.children.last?.nextInstruction)
        XCTAssertEqual(groups.flatMap(\.sourceSteps), steps)
    }

    func testRestPreviewOmitsEmptyUpcomingInstructionsInsteadOfUsingLaterWork() {
        let steps = [step(number: 1, phase: .rest), step(number: 2, instruction: " \n "),
                     step(number: 3, instruction: "Use the later grip.")]
        XCTAssertNil(PlanFlowPresentation.groups(for: steps).first?.nextInstruction)
    }

    func testInvalidRepeatMetadataPreservesIndividualIntervals() {
        let steps = [step(number: 1), step(number: 2)]
        for item in [WorkoutStepRepeat(stepRange: 0..<4, repeatCount: 2),
                     WorkoutStepRepeat(stepRange: 0..<2, repeatCount: 0),
                     WorkoutStepRepeat(stepRange: -1..<1, repeatCount: 2)] {
            let groups = PlanFlowPresentation.groups(for: steps, repeats: [item])
            XCTAssertEqual(groups.count, steps.count)
            XCTAssertEqual(groups.flatMap(\.sourceSteps), steps)
        }
        XCTAssertTrue(PlanFlowPresentation.groups(for: []).isEmpty)
    }

    func testEveryCatalogPlanRetainsEveryIntervalAndExactDuration() {
        for plan in PlanCatalog.all {
            let groups = PlanFlowPresentation.groups(for: plan)
            XCTAssertEqual(groups.flatMap(\.sourceSteps), plan.steps, plan.id)
            XCTAssertEqual(groups.reduce(0) { $0 + $1.duration }, plan.duration, plan.id)
            XCTAssertEqual(groups.filter { $0.repeatCount > 1 }.map(\.repeatCount), plan.stepRepeats.map(\.repeatCount), plan.id)
            for group in groups where group.repeatCount > 1 {
                let pattern = group.children.flatMap(\.sourceSteps)
                XCTAssertEqual(group.sourceSteps.count, pattern.count * group.repeatCount, plan.id)
                for (index, actual) in group.sourceSteps.enumerated() {
                    let expected = pattern[index % pattern.count]
                    XCTAssertEqual(actual.instruction, expected.instruction, plan.id)
                    XCTAssertEqual(actual.accessory, expected.accessory, plan.id)
                    XCTAssertEqual(actual.duration, expected.duration, plan.id)
                    XCTAssertEqual(actual.segments, expected.segments, plan.id)
                    XCTAssertEqual(actual.gripType, expected.gripType, plan.id)
                    XCTAssertEqual(actual.fingerConfiguration, expected.fingerConfiguration, plan.id)
                    XCTAssertEqual(actual.side, expected.side, plan.id)
                    XCTAssertEqual(actual.handUse, expected.handUse, plan.id)
                    XCTAssertEqual(actual.phase, expected.phase, plan.id)
                    XCTAssertEqual(actual.action, expected.action, plan.id)
                    XCTAssertEqual(actual.repetitions, expected.repetitions, plan.id)
                    XCTAssertEqual(actual.externalLoadKGF, expected.externalLoadKGF, plan.id)
                    XCTAssertEqual(actual.timedWorkDuration, expected.timedWorkDuration, plan.id)
                }
            }
        }
    }

    private func step(
        number: Int,
        title: String? = nil,
        instruction: String = "Hang for 7 seconds.",
        accessory: String = "7s hang",
        duration: TimeInterval? = nil,
        phase: WorkoutPhase = .hang,
        target: WorkoutSegmentTarget = .fromLegacyTargets([.kind(.edge)]),
        timing: WorkoutSegmentTiming = .fixed,
        segmentDuration: TimeInterval? = nil,
        grip: GripType = .halfCrimp,
        fingers: FingerConfiguration? = nil,
        handUse: WorkoutHandUse = .double,
        side: WorkoutSide = .both,
        action: WorkoutAction = .hang,
        repetitions: Int? = nil,
        load: Double? = nil,
        timedWorkDuration: TimeInterval? = nil
    ) -> WorkoutStep {
        let isRest = phase == .rest
        let duration = duration ?? (isRest ? 3 : 7)
        return WorkoutStep(
            id: "step-\(number)", number: number,
            title: title ?? (isRest ? "Rest" : "Edge hang"),
            instruction: isRest ? "" : instruction,
            accessory: isRest ? "3s rest" : accessory,
            duration: duration, phase: phase,
            segments: [WorkoutSegment(
                kind: isRest ? .rest : .work, target: isRest ? nil : target,
                timing: timing, duration: segmentDuration ?? duration
            )],
            gripType: isRest ? nil : grip, fingerConfiguration: fingers,
            handUse: handUse, side: side, action: action, repetitions: repetitions,
            externalLoadKGF: load, timedWorkDuration: timedWorkDuration
        )
    }
}
