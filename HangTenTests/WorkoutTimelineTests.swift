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

    func testCompletionIntervalUsesActualCompletionDateAfterPausedGap() {
        let sessionStart = Date(timeIntervalSinceReferenceDate: 1_000)
        let recordedAt = Date(timeIntervalSinceReferenceDate: 4_600)

        let interval = WorkoutSessionPolicy.completedWorkoutInterval(
            sessionStartedAt: sessionStart,
            recordedAt: recordedAt
        )

        XCTAssertEqual(interval.start, sessionStart)
        XCTAssertEqual(interval.end, recordedAt)
        XCTAssertEqual(interval.duration, 3_600)
    }

    func testCompletionIntervalClampsPreStartCompletionToStartDate() {
        let sessionStart = Date(timeIntervalSinceReferenceDate: 1_000)
        let recordedAt = Date(timeIntervalSinceReferenceDate: 900)

        let interval = WorkoutSessionPolicy.completedWorkoutInterval(
            sessionStartedAt: sessionStart,
            recordedAt: recordedAt
        )

        XCTAssertEqual(interval.start, sessionStart)
        XCTAssertEqual(interval.end, sessionStart)
        XCTAssertEqual(interval.duration, 0)
    }

    func testWorkoutMeasurementEligibilityRejectsPreStartAndAcceptsBoundaryAndAfterStart() {
        let startedAt = Date(timeIntervalSince1970: 100)

        XCTAssertFalse(
            WorkoutSessionPolicy.isMeasurementEligible(
                routineStartedAt: startedAt,
                measurementTimestamp: Date(timeIntervalSince1970: 99.999)
            )
        )
        XCTAssertTrue(
            WorkoutSessionPolicy.isMeasurementEligible(
                routineStartedAt: startedAt,
                measurementTimestamp: startedAt
            )
        )
        XCTAssertTrue(
            WorkoutSessionPolicy.isMeasurementEligible(
                routineStartedAt: startedAt,
                measurementTimestamp: Date(timeIntervalSince1970: 100.001)
            )
        )
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
