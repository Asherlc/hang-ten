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

final class WorkoutClockTests: XCTestCase {
    func testElapsedUsesNonUniformMonotonicSamplesInsteadOfCallbackCount() {
        var now: TimeInterval = 100
        var clock = WorkoutClock(now: { now })

        clock.start(initialCountdown: 0)
        now += 0.4
        XCTAssertEqual(clock.elapsed, 0.4, accuracy: 0.000_1)

        now += 1.3
        XCTAssertEqual(clock.elapsed, 1.7, accuracy: 0.000_1)
    }

    func testInitialCountdownShowsThreeTwoOneBeforeElapsedBegins() {
        var now: TimeInterval = 100
        var clock = WorkoutClock(now: { now })

        clock.start(initialCountdown: 3)
        XCTAssertEqual(clock.countdownRemaining, 3)

        now += 1
        XCTAssertEqual(clock.countdownRemaining, 2)

        now += 1
        XCTAssertEqual(clock.countdownRemaining, 1)

        now += 1
        XCTAssertEqual(clock.countdownRemaining, 0)
        XCTAssertEqual(clock.elapsed, 0)
    }

    func testSeekedClockShowsANewInitialCountdownBeforeElapsedResumes() {
        var now: TimeInterval = 100
        var clock = WorkoutClock(now: { now })

        clock.seek(to: 60)
        clock.start(initialCountdown: 3)

        XCTAssertEqual(clock.countdownRemaining, 3)

        now += 1.1
        XCTAssertEqual(clock.countdownRemaining, 2)

        now += 1
        XCTAssertEqual(clock.countdownRemaining, 1)

        now += 1
        XCTAssertEqual(clock.countdownRemaining, 0)
        XCTAssertEqual(clock.elapsed, 60.1, accuracy: 0.000_1)
    }

    func testPauseAndResumePreserveElapsedTime() {
        var now: TimeInterval = 100
        var clock = WorkoutClock(now: { now })

        clock.start(initialCountdown: 0)
        now += 1.7
        clock.pause()
        now += 20
        XCTAssertEqual(clock.elapsed, 1.7, accuracy: 0.000_1)

        clock.start(initialCountdown: 0)
        now += 0.4
        XCTAssertEqual(clock.elapsed, 2.1, accuracy: 0.000_1)
    }

    func testRunningSeekRebasesTheActiveAnchorWithoutDoubleCounting() {
        var now: TimeInterval = 100
        var clock = WorkoutClock(now: { now })

        clock.start(initialCountdown: 0)
        now += 1
        clock.seek(to: 10)
        now += 0.4

        XCTAssertEqual(clock.elapsed, 10.4, accuracy: 0.000_1)
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

    func testCompletionIntervalMapsExplicitActiveElapsedTimeOntoAbsoluteStartDate() {
        let sessionStart = Date(timeIntervalSinceReferenceDate: 1_000)

        let interval = WorkoutSessionPolicy.completedWorkoutInterval(
            sessionStartedAt: sessionStart,
            planDuration: 600,
            elapsed: 24.5
        )

        XCTAssertEqual(interval.start, sessionStart)
        XCTAssertEqual(interval.end, Date(timeIntervalSinceReferenceDate: 1_024.5))
    }

    func testCompletionIntervalExcludesPausedGapFromClockElapsedTime() {
        var now: TimeInterval = 100
        var clock = WorkoutClock(now: { now })
        let sessionStart = Date(timeIntervalSinceReferenceDate: 1_000)

        clock.start(initialCountdown: 0)
        now += 12.5
        clock.pause()
        now += 3_600
        clock.start(initialCountdown: 0)
        now += 7.5

        let interval = WorkoutSessionPolicy.completedWorkoutInterval(
            sessionStartedAt: sessionStart,
            planDuration: 600,
            elapsed: clock.elapsed
        )

        XCTAssertEqual(interval.duration, 20, accuracy: 0.000_1)
    }

    func testCompletionIntervalCapsExplicitActiveElapsedTimeAtPlanDuration() {
        let sessionStart = Date(timeIntervalSinceReferenceDate: 1_000)

        let interval = WorkoutSessionPolicy.completedWorkoutInterval(
            sessionStartedAt: sessionStart,
            planDuration: 60,
            elapsed: 80
        )

        XCTAssertEqual(interval.start, sessionStart)
        XCTAssertEqual(interval.end, Date(timeIntervalSinceReferenceDate: 1_060))
    }
}

final class WorkoutAudioCuePolicyTests: XCTestCase {
    private let stepID = "f80-set-2-rep-3"

    func testInitialCountdownReturnsOnlyNumericValues() {
        for countdown in [3, 2, 1] {
            let moment = WorkoutAudioCuePolicy.moment(
                stepID: stepID,
                segmentName: "active",
                initialCountdown: countdown,
                intervalSecondsRemaining: 60,
                isComplete: false
            )

            XCTAssertEqual(
                moment,
                WorkoutAudioMoment(
                    key: "initial-\(countdown)",
                    phrase: "\(countdown)"
                )
            )
        }
    }

    func testIntervalCountdownReturnsNumericValuesWithStableSegmentKeys() {
        for secondsRemaining in [3, 2, 1] {
            let moment = WorkoutAudioCuePolicy.moment(
                stepID: stepID,
                segmentName: "active",
                initialCountdown: 0,
                intervalSecondsRemaining: secondsRemaining,
                isComplete: false
            )

            XCTAssertEqual(
                moment,
                WorkoutAudioMoment(
                    key: "\(stepID)-active-\(secondsRemaining)",
                    phrase: "\(secondsRemaining)"
                )
            )
        }
    }

    func testSegmentStartAndNormalIntervalReturnNoCue() {
        XCTAssertNil(
            WorkoutAudioCuePolicy.moment(
                stepID: stepID,
                segmentName: "rest",
                initialCountdown: 0,
                intervalSecondsRemaining: 60,
                isComplete: false
            )
        )
    }

    func testCompletionReturnsNoCueEvenDuringTheFinalThreeSeconds() {
        XCTAssertNil(
            WorkoutAudioCuePolicy.moment(
                stepID: stepID,
                segmentName: "active",
                initialCountdown: 0,
                intervalSecondsRemaining: 3,
                isComplete: true
            )
        )
    }

    func testShortIntervalReturnsOnlyTheApplicableNumber() {
        let moment = WorkoutAudioCuePolicy.moment(
            stepID: stepID,
            segmentName: "rest",
            initialCountdown: 0,
            intervalSecondsRemaining: 2,
            isComplete: false
        )

        XCTAssertEqual(
            moment,
            WorkoutAudioMoment(
                key: "\(stepID)-rest-2",
                phrase: "2"
            )
        )
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

    func testPausedSessionSkipCountsDownThenExplicitExpiryStartsRunningDestination() {
        let now = Date(timeIntervalSinceReferenceDate: 3_000)
        let timeline = WorkoutTimeline(steps: steps)
        var state = WorkoutSessionState(
            startedAt: nil,
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
        XCTAssertEqual(state.countdownKind, .skip)
        state.transitionExpiredCountdown(at: countdownStart)
        XCTAssertNil(state.countdownKind)
        XCTAssertEqual(state.startedAt, countdownStart)
        XCTAssertEqual(state.currentElapsed(planDuration: timeline.duration, at: countdownStart), 60)
        XCTAssertTrue(state.canNavigate(planDuration: timeline.duration, now: countdownStart))
    }

    func testPausedDirectSeekPreservesPausedState() {
        let now = Date(timeIntervalSinceReferenceDate: 3_000)
        let timeline = WorkoutTimeline(steps: steps)
        var state = WorkoutSessionState(
            startedAt: nil,
            pausedElapsed: 10,
            routineStartedAt: now.addingTimeInterval(-20)
        )

        state.seek(to: 80, planDuration: timeline.duration, now: now)

        XCTAssertNil(state.startedAt)
        XCTAssertNil(state.countdownKind)
        XCTAssertEqual(state.pausedElapsed, 80)
        XCTAssertEqual(state.currentElapsed(planDuration: timeline.duration, at: now.addingTimeInterval(4)), 80)
    }

    func testInitialStartCancelAndRestartLifecycle() {
        let now = Date(timeIntervalSinceReferenceDate: 3_000)
        var state = WorkoutSessionState()

        state.toggleRunning(now: now)

        let firstStart = now.addingTimeInterval(3)
        XCTAssertEqual(state.startedAt, firstStart)
        XCTAssertEqual(state.routineStartedAt, firstStart)
        XCTAssertEqual(state.countdownKind, .initial)
        XCTAssertEqual(state.countdownRemaining(at: now), 3)

        state.cancelCountdown()

        XCTAssertNil(state.startedAt)
        XCTAssertNil(state.routineStartedAt)
        XCTAssertNil(state.countdownKind)
        XCTAssertEqual(state.pausedElapsed, 0)

        let restart = now.addingTimeInterval(10)
        state.toggleRunning(now: restart)

        XCTAssertEqual(state.startedAt, restart.addingTimeInterval(3))
        XCTAssertEqual(state.routineStartedAt, restart.addingTimeInterval(3))
        XCTAssertEqual(state.countdownKind, .initial)
    }

    func testCountdownExpiryReadIsPureUntilExplicitTransitionClearsKind() {
        let now = Date(timeIntervalSinceReferenceDate: 3_000)
        let expiry = now.addingTimeInterval(5)
        let immutableState = WorkoutSessionState(
            startedAt: expiry,
            countdownKind: .skip,
            pausedElapsed: 60,
            routineStartedAt: now.addingTimeInterval(-20)
        )
        var state = WorkoutSessionState(
            startedAt: expiry,
            countdownKind: .skip,
            pausedElapsed: 60,
            routineStartedAt: now.addingTimeInterval(-20)
        )

        XCTAssertEqual(immutableState.countdownRemaining(at: expiry), 0)
        XCTAssertEqual(state.countdownRemaining(at: expiry), 0)
        XCTAssertEqual(state.countdownKind, .skip)
        XCTAssertEqual(state.startedAt, expiry)

        state.transitionExpiredCountdown(at: expiry.addingTimeInterval(-0.1))

        XCTAssertEqual(state.countdownKind, .skip)
        XCTAssertEqual(state.startedAt, expiry)

        state.transitionExpiredCountdown(at: expiry)

        XCTAssertNil(state.countdownKind)
        XCTAssertEqual(state.startedAt, expiry)
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
