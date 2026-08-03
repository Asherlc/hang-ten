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
}

final class WorkoutSessionPolicyTests: XCTestCase {
    func testCountdownDurationsKeepInitialStartAtThreeAndSkipStartAtFive() {
        let now = Date(timeIntervalSinceReferenceDate: 2_000)

        XCTAssertEqual(
            WorkoutSessionPolicy.startDate(for: .initial, now: now),
            now.addingTimeInterval(3)
        )
        XCTAssertEqual(
            WorkoutSessionPolicy.startDate(for: .skip, now: now),
            now.addingTimeInterval(5)
        )
    }

    func testCountdownRemainingUsesCeilingAndReachesZeroAtStart() {
        let now = Date(timeIntervalSinceReferenceDate: 2_000)
        let start = now.addingTimeInterval(5)

        XCTAssertEqual(
            WorkoutSessionPolicy.countdownRemaining(startedAt: start, now: now),
            5
        )
        XCTAssertEqual(
            WorkoutSessionPolicy.countdownRemaining(
                startedAt: start,
                now: now.addingTimeInterval(1.1)
            ),
            4
        )
        XCTAssertEqual(
            WorkoutSessionPolicy.countdownRemaining(
                startedAt: start,
                now: start
            ),
            0
        )
        XCTAssertEqual(
            WorkoutSessionPolicy.countdownRemaining(startedAt: nil, now: now),
            0
        )
    }

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

final class WorkoutSessionStateTests: XCTestCase {
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

    func testSkipCountdownClearsPendingKindWhenItStartsRunning() {
        let now = Date(timeIntervalSinceReferenceDate: 3_000)
        let timeline = WorkoutTimeline(steps: steps)
        var state = WorkoutSessionState(
            startedAt: now.addingTimeInterval(-10),
            pausedElapsed: 10,
            routineStartedAt: now.addingTimeInterval(-20)
        )

        XCTAssertTrue(state.skipCurrentStep(timeline: timeline, planDuration: timeline.duration, now: now))
        XCTAssertEqual(state.pausedElapsed, 60)
        XCTAssertEqual(state.countdownKind, .skip)
        XCTAssertEqual(state.countdownRemaining(at: now), 5)
        XCTAssertFalse(state.canNavigate(planDuration: timeline.duration, now: now))

        let countdownStart = now.addingTimeInterval(5)
        XCTAssertEqual(state.countdownRemaining(at: countdownStart), 0)
        XCTAssertNil(state.countdownKind)
        XCTAssertEqual(state.currentElapsed(planDuration: timeline.duration, at: countdownStart), 60)
        XCTAssertTrue(state.canNavigate(planDuration: timeline.duration, now: countdownStart))
    }

    func testCancelSkipCountdownKeepsDestinationPaused() {
        let now = Date(timeIntervalSinceReferenceDate: 3_000)
        let timeline = WorkoutTimeline(steps: steps)
        var state = WorkoutSessionState(
            startedAt: now.addingTimeInterval(-10),
            pausedElapsed: 10,
            routineStartedAt: now.addingTimeInterval(-20)
        )

        XCTAssertTrue(state.skipCurrentStep(timeline: timeline, planDuration: timeline.duration, now: now))
        state.cancelCountdown()

        XCTAssertNil(state.startedAt)
        XCTAssertNil(state.countdownKind)
        XCTAssertEqual(state.pausedElapsed, 60)
        XCTAssertEqual(state.routineStartedAt, now.addingTimeInterval(-20))
    }

    func testInterruptionDuringSkipCountdownKeepsDestinationPaused() {
        let now = Date(timeIntervalSinceReferenceDate: 3_000)
        let timeline = WorkoutTimeline(steps: steps)
        var state = WorkoutSessionState(
            startedAt: now.addingTimeInterval(-10),
            pausedElapsed: 10,
            routineStartedAt: now.addingTimeInterval(-20)
        )

        XCTAssertTrue(state.skipCurrentStep(timeline: timeline, planDuration: timeline.duration, now: now))
        state.pauseForInterruption(now: now.addingTimeInterval(2))

        XCTAssertNil(state.startedAt)
        XCTAssertNil(state.countdownKind)
        XCTAssertEqual(state.pausedElapsed, 60)
        XCTAssertEqual(state.routineStartedAt, now.addingTimeInterval(-20))
    }

    func testDirectSeekClearsPendingSkipCountdownAndPreservesRunning() {
        let now = Date(timeIntervalSinceReferenceDate: 3_000)
        let timeline = WorkoutTimeline(steps: steps)
        var state = WorkoutSessionState(
            startedAt: now.addingTimeInterval(-10),
            pausedElapsed: 10,
            routineStartedAt: now.addingTimeInterval(-20)
        )

        XCTAssertTrue(state.skipCurrentStep(timeline: timeline, planDuration: timeline.duration, now: now))
        state.seek(to: 80, planDuration: timeline.duration, now: now.addingTimeInterval(2))

        XCTAssertNil(state.countdownKind)
        XCTAssertEqual(state.startedAt, now.addingTimeInterval(2))
        XCTAssertEqual(state.pausedElapsed, 80)
        XCTAssertEqual(
            state.currentElapsed(planDuration: timeline.duration, at: now.addingTimeInterval(4)),
            82
        )
    }

    func testFinalSkipSeeksDirectlyToCompletion() {
        let now = Date(timeIntervalSinceReferenceDate: 3_000)
        let timeline = WorkoutTimeline(steps: steps)
        var state = WorkoutSessionState(
            startedAt: now.addingTimeInterval(-1),
            pausedElapsed: 85,
            routineStartedAt: now.addingTimeInterval(-100)
        )

        XCTAssertTrue(state.skipCurrentStep(timeline: timeline, planDuration: timeline.duration, now: now))

        XCTAssertNil(state.countdownKind)
        XCTAssertEqual(state.startedAt, now)
        XCTAssertEqual(state.pausedElapsed, 90)
        XCTAssertEqual(state.currentElapsed(planDuration: timeline.duration, at: now.addingTimeInterval(10)), 90)
        XCTAssertFalse(state.canNavigate(planDuration: timeline.duration, now: now))
    }
}

final class WorkoutViewSessionStateTests: XCTestCase {
    func testWorkoutViewStoresTheTestedSessionStateAsItsSourceOfTruth() {
        let view = WorkoutView(plan: PlanCatalog.metoliusTenMinute)
        let storedStateNames = Set(Mirror(reflecting: view).children.compactMap(\.label))

        XCTAssertTrue(storedStateNames.contains("_sessionState"))
        XCTAssertFalse(storedStateNames.contains("_startedAt"))
        XCTAssertFalse(storedStateNames.contains("_countdownKind"))
        XCTAssertFalse(storedStateNames.contains("_pausedElapsed"))
        XCTAssertFalse(storedStateNames.contains("_routineStartedAt"))
    }
}
