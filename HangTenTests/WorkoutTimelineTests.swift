import XCTest
@testable import HangTen

final class WorkoutTimelineTests: XCTestCase {
    private let steps: [WorkoutStep] = [
        WorkoutStep(
            id: "first",
            number: 1,
            title: "First",
            instruction: "First instruction",
            accessory: "First accessory",
            duration: 60,
            phase: .hang,
            targets: [.kind(.jug)],
            timedWorkDuration: 30
        ),
        WorkoutStep(
            id: "second",
            number: 2,
            title: "Second",
            instruction: "Second instruction",
            accessory: "Second accessory",
            duration: 20,
            phase: .rest,
            targets: []
        ),
        WorkoutStep(
            id: "third",
            number: 3,
            title: "Third",
            instruction: "Third instruction",
            accessory: "Third accessory",
            duration: 10,
            phase: .hang,
            targets: [.kind(.jug)]
        )
    ]

    func testDurationAndOffsetsIncludeWholeSteps() {
        let timeline = WorkoutTimeline(steps: steps)

        XCTAssertEqual(timeline.duration, 90)
        XCTAssertEqual(timeline.startOffset(for: "first"), 0)
        XCTAssertEqual(timeline.startOffset(for: "second"), 60)
        XCTAssertEqual(timeline.startOffset(for: "third"), 80)
    }

    func testExactBoundaryResolvesToFollowingStep() {
        let timeline = WorkoutTimeline(steps: steps)

        XCTAssertEqual(timeline.step(at: 60)?.id, "second")
        XCTAssertEqual(timeline.elapsedInStep(at: 65), 5)
    }

    func testNegativeElapsedClampsToTheFirstStep() {
        let timeline = WorkoutTimeline(steps: steps)

        XCTAssertEqual(timeline.step(at: -1)?.id, "first")
        XCTAssertEqual(timeline.elapsedInStep(at: -1), 0)
    }

    func testElapsedAtOrPastPlanDurationClampsToTheFinalStep() {
        let timeline = WorkoutTimeline(steps: steps)

        XCTAssertEqual(timeline.step(at: 90)?.id, "third")
        XCTAssertEqual(timeline.elapsedInStep(at: 90), 10)
        XCTAssertEqual(timeline.step(at: 120)?.id, "third")
        XCTAssertEqual(timeline.elapsedInStep(at: 120), 10)
    }

    func testSelectionTargetsDifferentStepStartsAndCurrentStepIsNoOp() {
        let timeline = WorkoutTimeline(steps: steps)

        XCTAssertEqual(timeline.selectionTarget(for: "third", at: 10), 80)
        XCTAssertEqual(timeline.selectionTarget(for: "first", at: 75), 0)
        XCTAssertNil(timeline.selectionTarget(for: "second", at: 75))
    }

    func testSkipUsesTheFullStepBoundaryIncludingRest() {
        let timeline = WorkoutTimeline(steps: steps)

        XCTAssertEqual(timeline.skipTarget(from: 45), 60)
        XCTAssertEqual(timeline.skipTarget(from: 65), 80)
    }

    func testSkippingTheFinalStepStopsAtPlanDuration() {
        let timeline = WorkoutTimeline(steps: steps)

        XCTAssertEqual(timeline.skipTarget(from: 85), 90)
        XCTAssertEqual(timeline.selectionTarget(for: "third", at: 65), 80)
    }

    func testEmptyTimelineHasNoNavigationTargets() {
        let timeline = WorkoutTimeline(steps: [])

        XCTAssertEqual(timeline.duration, 0)
        XCTAssertNil(timeline.step(at: 0))
        XCTAssertNil(timeline.startOffset(for: "missing"))
        XCTAssertNil(timeline.selectionTarget(for: "missing", at: 0))
        XCTAssertNil(timeline.skipTarget(from: 0))
    }

    private let restPreviewSteps: [WorkoutStep] = [
        WorkoutStep(
            id: "work",
            number: 1,
            title: "Work",
            instruction: "Work instruction",
            accessory: "Work accessory",
            duration: 30,
            phase: .hang,
            targets: [.kind(.jug)],
            timedWorkDuration: 15
        ),
        WorkoutStep(
            id: "rest-one",
            number: 2,
            title: "Rest one",
            instruction: "Rest instruction",
            accessory: "Rest accessory",
            duration: 10,
            phase: .rest,
            targets: []
        ),
        WorkoutStep(
            id: "rest-two",
            number: 3,
            title: "Rest two",
            instruction: "Rest instruction",
            accessory: "Rest accessory",
            duration: 10,
            phase: .rest,
            targets: []
        ),
        WorkoutStep(
            id: "next-work",
            number: 4,
            title: "Next work",
            instruction: "Next work instruction",
            accessory: "Next work accessory",
            duration: 20,
            phase: .pull,
            targets: [.kind(.edge)]
        ),
        WorkoutStep(
            id: "final-rest",
            number: 5,
            title: "Final rest",
            instruction: "Final rest instruction",
            accessory: "Final rest accessory",
            duration: 5,
            phase: .rest,
            targets: []
        )
    ]

    func testNextWorkStepSkipsConsecutiveRestSteps() {
        let timeline = WorkoutTimeline(steps: restPreviewSteps)

        XCTAssertEqual(timeline.nextWorkStep(after: "work")?.id, "next-work")
        XCTAssertEqual(timeline.nextWorkStep(after: "rest-one")?.id, "next-work")
        XCTAssertEqual(timeline.nextWorkStep(after: "rest-two")?.id, "next-work")
        XCTAssertNil(timeline.nextWorkStep(after: "next-work"))
    }

    func testHoldPreviewUsesNextWorkStepDuringTimedAndExplicitRest() {
        let timeline = WorkoutTimeline(steps: restPreviewSteps)

        XCTAssertEqual(timeline.holdPreviewStep(at: 5)?.id, "work")
        XCTAssertEqual(timeline.holdPreviewStep(at: 20)?.id, "next-work")
        XCTAssertEqual(timeline.holdPreviewStep(at: 35)?.id, "next-work")
    }

    func testHoldPreviewWithCurrentStepAndElapsedUsesProvidedLocation() {
        let timeline = WorkoutTimeline(steps: restPreviewSteps)

        XCTAssertEqual(
            timeline.holdPreviewStep(
                currentStep: restPreviewSteps[0],
                stepElapsed: 15
            )?.id,
            "next-work"
        )
        XCTAssertEqual(
            timeline.holdPreviewStep(
                currentStep: restPreviewSteps[0],
                stepElapsed: 5
            )?.id,
            "work"
        )
        XCTAssertEqual(
            timeline.holdPreviewStep(
                currentStep: restPreviewSteps[1],
                stepElapsed: 2
            )?.id,
            "next-work"
        )
    }

    func testHoldPreviewHasNoHighlightSourceAfterTheFinalRestStep() {
        let timeline = WorkoutTimeline(steps: restPreviewSteps)

        XCTAssertNil(timeline.holdPreviewStep(at: 72))
    }
}

final class WorkoutSessionPolicyTests: XCTestCase {
    func testPausedSessionAtStepOneIsNotAFirstStartAndResumesImmediately() {
        let originalRoutineStart = Date(timeIntervalSinceReferenceDate: 1_000)
        let resumedAt = Date(timeIntervalSinceReferenceDate: 1_120)

        XCTAssertTrue(WorkoutSessionPolicy.isFirstStart(routineStartedAt: nil))
        XCTAssertFalse(WorkoutSessionPolicy.isFirstStart(routineStartedAt: originalRoutineStart))
        XCTAssertEqual(
            WorkoutSessionPolicy.runStartDate(routineStartedAt: originalRoutineStart, now: resumedAt),
            resumedAt
        )
    }

    func testCompletionIntervalPreservesSessionStartAndNeverEndsAfterLogTime() {
        let sessionStart = Date(timeIntervalSinceReferenceDate: 1_000)
        let loggedAt = Date(timeIntervalSinceReferenceDate: 1_120)

        let interval = WorkoutSessionPolicy.completedWorkoutInterval(
            sessionStartedAt: sessionStart,
            planDuration: 600,
            loggedAt: loggedAt
        )

        XCTAssertEqual(interval.start, sessionStart)
        XCTAssertEqual(interval.end, loggedAt)
    }
}
