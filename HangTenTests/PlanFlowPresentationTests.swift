import XCTest
@testable import HangTen

final class PlanFlowPresentationTests: XCTestCase {
    func testTenIdenticalStagesShowOnePrescriptionWithTenRepeats() throws {
        let steps = (1...10).map { step(number: $0) }

        let groups = PlanFlowPresentation.groups(for: steps)

        XCTAssertEqual(groups.count, 1)
        let group = try XCTUnwrap(groups.first)
        XCTAssertEqual(group.repeatCount, 10)
        XCTAssertEqual(group.sourceSteps, steps)
        XCTAssertEqual(group.children.count, 1)
        XCTAssertEqual(group.children.first?.title, "Edge hang")
        XCTAssertEqual(group.duration, 70)
    }

    func testConsecutiveHangRestCyclesKeepFinalRecoveryOutsideTheNextHoldPreview() throws {
        let steps = (1...3).flatMap { repeatNumber in
            [step(number: repeatNumber * 2 - 1), step(number: repeatNumber * 2, phase: .rest)]
        }

        let groups = PlanFlowPresentation.groups(for: steps)

        XCTAssertEqual(groups.count, 3)
        let group = try XCTUnwrap(groups.first)
        XCTAssertEqual(group.repeatCount, 2)
        XCTAssertEqual(group.children.map(\.title), ["Edge hang", "Rest"])
        XCTAssertEqual(group.children.last?.nextInstruction, "Hang for 7 seconds.")
        XCTAssertNil(groups.last?.nextInstruction)
        XCTAssertEqual(groups.reduce(0) { $0 + $1.duration }, 30)
        XCTAssertEqual(groups.flatMap(\.sourceSteps), steps)
    }

    func testNumberedTitlesGroupWithoutRemovingHoldSizesOrExerciseCounts() {
        let titles = [
            "7/3 · set 1 · 20 mm edge · rep 1 of 3",
            "7/3 · set 1 · 20 mm edge · rep 2 of 3",
            "7/3 · set 1 · 20 mm edge · rep 3 of 3"
        ]
        let groups = PlanFlowPresentation.groups(for: titles.enumerated().map {
            step(number: $0.offset + 1, title: $0.element)
        })

        XCTAssertEqual(groups.count, 1)
        XCTAssertEqual(groups.first?.repeatCount, 3)
        XCTAssertEqual(groups.first?.children.first?.title, "7/3 · 20 mm edge")

        for titles in [["10 mm hang", "20 mm hang"], ["5 pull-ups", "10 pull-ups"],
                       ["Ladder 10 mm hang", "Ladder 20 mm hang"],
                       ["Minute 10 second hang", "Minute 20 second hang"],
                       ["Hang · optional set 1", "Hang · optional set 2"]] {
            let distinct = PlanFlowPresentation.groups(for: titles.enumerated().map {
                step(number: $0.offset + 1, title: $0.element)
            })
            XCTAssertEqual(distinct.count, 2, "Meaningful title differences must stay visible: \(titles)")
        }
    }

    func testCombinedRoundAndRepCountersCanGroupNestedSequences() throws {
        var steps: [WorkoutStep] = []
        for round in 1...3 {
            for rep in 1...2 {
                let number = (round - 1) * 3 + rep
                let title = "Repeaters · round \(round), rep \(rep)"
                steps.append(step(number: number, title: title))
            }
            steps.append(step(number: round * 3, phase: .rest))
        }

        let group = try XCTUnwrap(PlanFlowPresentation.groups(for: steps).first)

        XCTAssertEqual(group.repeatCount, 2)
        XCTAssertEqual(group.sourceSteps.count, 6)
        XCTAssertEqual(group.children.count, 2)
        XCTAssertEqual(group.children.first?.repeatCount, 2)
        XCTAssertEqual(group.children.first?.children.first?.title, "Repeaters")
    }

    func testMaxHangsKeepTheFinalHangWithoutAnInventedRecovery() throws {
        let plan = try XCTUnwrap(PlanCatalog.plan(id: "research.max-hangs"))

        let groups = PlanFlowPresentation.groups(for: plan.steps)

        XCTAssertEqual(groups.count, 2)
        XCTAssertEqual(groups.first?.repeatCount, 4)
        XCTAssertEqual(groups.first?.children.map { $0.sourceSteps[0].duration }, [10, 180])
        XCTAssertEqual(groups.last?.repeatCount, 1)
        XCTAssertEqual(groups.last?.sourceSteps, [plan.steps.last!])
        XCTAssertEqual(groups.reduce(0) { $0 + $1.duration }, 770)
    }

    func testRPTCFinalRecoveryAndBetweenSetRestRemainSeparate() throws {
        let plan = try XCTUnwrap(PlanCatalog.plan(id: "rptc.seven-three-repeaters"))

        let groups = PlanFlowPresentation.groups(for: plan.steps)

        XCTAssertEqual(groups.count, 6)
        XCTAssertEqual(groups.first?.repeatCount, 5)
        XCTAssertEqual(groups.first?.children.map { $0.sourceSteps[0].duration }, [7, 3])
        XCTAssertEqual(groups.dropFirst().flatMap(\.sourceSteps).map(\.duration), [7, 3, 7, 173, 180])
        XCTAssertEqual(groups.flatMap(\.sourceSteps), plan.steps)
    }

    func testDifferentPrescriptionsNeverCollapseIntoOneRepeatedStage() throws {
        let original = step(number: 1)
        let oneFinger = try XCTUnwrap(FingerConfiguration(engagedFingers: [.index]))
        let variants: [WorkoutStep] = [
            step(number: 2, instruction: "Different instruction"),
            step(number: 2, accessory: "Different accessory"),
            step(number: 2, duration: 8),
            step(number: 2, phase: .warmUp),
            step(number: 2, target: .fromLegacyTargets([.kind(.jug)])),
            step(number: 2, timing: .stopwatch),
            step(number: 2, segmentDuration: 6),
            step(number: 2, grip: .openHand),
            step(number: 2, fingers: oneFinger),
            step(number: 2, handUse: .either),
            step(number: 2, handUse: .single, side: .left),
            step(number: 2, handUse: .single, side: .right),
            step(number: 2, action: .isometricPull),
            step(number: 2, action: .loadedLift, repetitions: 3),
            step(number: 2, load: 5),
            step(number: 2, timedWorkDuration: 6)
        ]

        for variant in variants {
            let groups = PlanFlowPresentation.groups(for: [original, variant])
            XCTAssertEqual(groups.count, 2, "Different prescription: \(variant)")
            XCTAssertTrue(groups.allSatisfy { $0.repeatCount == 1 })
        }
    }

    func testSideAndLiftRepetitionDifferencesStayVisibleWithMatchingTitles() {
        let pairs: [(WorkoutStep, WorkoutStep)] = [
            (step(number: 1, handUse: .single, side: .left),
             step(number: 2, handUse: .single, side: .right)),
            (step(number: 1, action: .loadedLift, repetitions: 3),
             step(number: 2, action: .loadedLift, repetitions: 4))
        ]
        for (first, second) in pairs {
            XCTAssertEqual(PlanFlowPresentation.groups(for: [first, second]).count, 2)
        }
    }

    func testNonAdjacentMatchesAndUniqueTitlesKeepTheirOriginalOrder() {
        let steps = [step(number: 1), step(number: 2, phase: .rest), step(number: 3)]
        let groups = PlanFlowPresentation.groups(for: steps)
        XCTAssertEqual(groups.count, 3)
        XCTAssertEqual(groups.flatMap(\.sourceSteps), steps)
        XCTAssertEqual(groups.map(\.title), steps.map(\.title))
        XCTAssertTrue(PlanFlowPresentation.groups(for: []).isEmpty)
    }

    func testRestPreviewsWithDifferentUpcomingInstructionsDoNotCollapse() {
        let steps = [
            step(number: 1), step(number: 2, phase: .rest),
            step(number: 3), step(number: 4, phase: .rest),
            step(number: 5, instruction: "Use the next grip.")
        ]

        let groups = PlanFlowPresentation.groups(for: steps)

        XCTAssertEqual(groups.count, 5)
        XCTAssertTrue(groups.allSatisfy { $0.repeatCount == 1 })
        XCTAssertEqual(groups.flatMap(\.sourceSteps), steps)
        XCTAssertEqual(groups[1].nextInstruction, "Hang for 7 seconds.")
        XCTAssertEqual(groups[3].nextInstruction, "Use the next grip.")
    }

    func testRestPreviewSkipsConsecutiveRestsAndRetainsTheirSourceContent() throws {
        let steps = [
            step(number: 1, phase: .rest), step(number: 2, phase: .rest),
            step(number: 3, instruction: "Use the next grip.")
        ]
        let groups = PlanFlowPresentation.groups(for: steps)
        let rest = try XCTUnwrap(groups.first?.children.first)

        XCTAssertEqual(rest.nextInstruction, "Use the next grip.")
        XCTAssertEqual(rest.sourceSteps.first?.instruction, "")
        XCTAssertEqual(rest.sourceSteps.first?.accessory, "3s rest")
        XCTAssertEqual(groups.flatMap(\.sourceSteps), steps)
    }

    func testRestPreviewOmitsEmptyUpcomingInstructionsInsteadOfUsingLaterWork() {
        let steps = [
            step(number: 1, phase: .rest),
            step(number: 2, instruction: " \n "),
            step(number: 3, instruction: "Use the later grip.")
        ]

        XCTAssertNil(PlanFlowPresentation.groups(for: steps).first?.nextInstruction)
    }

    func testEveryCatalogPlanRetainsAllSourceStepsAndExactTotalDuration() {
        for plan in PlanCatalog.all {
            let groups = PlanFlowPresentation.groups(for: plan.steps)
            XCTAssertEqual(groups.flatMap(\.sourceSteps), plan.steps, plan.id)
            XCTAssertEqual(groups.reduce(0) { $0 + $1.duration }, plan.duration, plan.id)
            checkRepeatedPrescriptions(in: groups, planID: plan.id)
        }
    }

    private func checkRepeatedPrescriptions(in groups: [PlanFlowGroup], planID: String) {
        for group in groups where group.repeatCount > 1 {
            let pattern = group.children.flatMap(\.sourceSteps)
            XCTAssertEqual(group.sourceSteps.count, pattern.count * group.repeatCount, planID)
            for (index, actual) in group.sourceSteps.enumerated() {
                let expected = pattern[index % pattern.count]
                XCTAssertEqual(actual.instruction, expected.instruction, planID)
                XCTAssertEqual(actual.accessory, expected.accessory, planID)
                XCTAssertEqual(actual.duration, expected.duration, planID)
                XCTAssertEqual(actual.segments, expected.segments, planID)
                XCTAssertEqual(actual.gripType, expected.gripType, planID)
                XCTAssertEqual(actual.fingerConfiguration, expected.fingerConfiguration, planID)
                XCTAssertEqual(actual.side, expected.side, planID)
                XCTAssertEqual(actual.handUse, expected.handUse, planID)
                XCTAssertEqual(actual.phase, expected.phase, planID)
                XCTAssertEqual(actual.action, expected.action, planID)
                XCTAssertEqual(actual.repetitions, expected.repetitions, planID)
                XCTAssertEqual(actual.externalLoadKGF, expected.externalLoadKGF, planID)
                XCTAssertEqual(actual.timedWorkDuration, expected.timedWorkDuration, planID)
            }
            checkRepeatedPrescriptions(in: group.children, planID: planID)
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
