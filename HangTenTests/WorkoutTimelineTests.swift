import XCTest
import SwiftUI
import UIKit
@testable import HangTen

final class WorkoutTimelineTests: XCTestCase {
    func testHoldCuePrefersSingleTargetStepGripOverride() {
        let hold = BoardHold(
            id: "cue-edge",
            name: "Cue edge",
            shortLabel: "E",
            detail: "Edge",
            kind: .edge,
            frame: HoldFrame(x: 0, y: 0, width: 1, height: 1),
            gripType: .openHand
        )
        let step = WorkoutStep(
            id: "cue-step",
            number: 1,
            title: "Cue step",
            instruction: "Cue instruction",
            accessory: "Cue accessory",
            duration: 10,
            phase: .hang,
            targets: [.kind(.edge)],
            gripType: .halfCrimp
        )

        let cue = WorkoutHoldCuePolicy.resolve(step: step, hold: hold)

        XCTAssertEqual(cue?.hold, hold)
        XCTAssertEqual(cue?.gripType, .halfCrimp)
    }

    func testHoldCueFallsBackToBoardHoldGrip() {
        let hold = BoardHold(
            id: "cue-pocket",
            name: "Cue pocket",
            shortLabel: "P",
            detail: "Pocket",
            kind: .pocket,
            frame: HoldFrame(x: 0, y: 0, width: 1, height: 1),
            gripType: .threeFingerPocket
        )
        let step = WorkoutStep(
            id: "cue-step",
            number: 1,
            title: "Cue step",
            instruction: "Cue instruction",
            accessory: "Cue accessory",
            duration: 10,
            phase: .hang,
            targets: [.kind(.pocket)]
        )

        let cue = WorkoutHoldCuePolicy.resolve(step: step, hold: hold)

        XCTAssertEqual(cue?.gripType, .threeFingerPocket)
    }

    func testHoldCueIsUnavailableForMultiTargetSteps() {
        let hold = BoardHold(
            id: "cue-edge",
            name: "Cue edge",
            shortLabel: "E",
            detail: "Edge",
            kind: .edge,
            frame: HoldFrame(x: 0, y: 0, width: 1, height: 1)
        )
        let step = WorkoutStep(
            id: "cue-step",
            number: 1,
            title: "Cue step",
            instruction: "Cue instruction",
            accessory: "Cue accessory",
            duration: 10,
            phase: .hang,
            targets: [.kind(.edge), .kind(.jug)]
        )

        XCTAssertNil(WorkoutHoldCuePolicy.resolve(step: step, hold: hold))
    }

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

    func testBoardCueUsesNextWorkStepAndPreviewModeDuringRest() {
        let timeline = WorkoutTimeline(steps: restPreviewSteps)

        let cue = timeline.boardCue(at: 35, countdown: 0, isComplete: false)

        XCTAssertEqual(cue.step?.id, "next-work")
        XCTAssertEqual(cue.mode, .preview)
        XCTAssertTrue(cue.isResting)
        XCTAssertFalse(cue.isSuppressed)
    }

    func testBoardCuePreviewsDestinationWorkStepDuringSkipCountdown() {
        let timeline = WorkoutTimeline(steps: restPreviewSteps)

        let cue = timeline.boardCue(
            currentStep: restPreviewSteps[3],
            stepElapsed: 0,
            countdown: 3,
            isComplete: false,
            isSkipCountdown: true
        )

        XCTAssertEqual(cue.step?.id, "next-work")
        XCTAssertEqual(cue.mode, .preview)
        XCTAssertFalse(cue.isResting)
        XCTAssertFalse(cue.isSuppressed)
    }

    func testBoardCueUsesProvidedTimedRestLocationWithoutRecomputingIt() {
        let timeline = WorkoutTimeline(steps: restPreviewSteps)

        let elapsedCue = timeline.boardCue(at: 20, countdown: 0, isComplete: false)
        let suppliedCue = timeline.boardCue(
            currentStep: restPreviewSteps[0],
            stepElapsed: 20,
            countdown: 0,
            isComplete: false
        )

        XCTAssertEqual(elapsedCue.step?.id, "next-work")
        XCTAssertEqual(elapsedCue.mode, .preview)
        XCTAssertTrue(elapsedCue.isResting)
        XCTAssertEqual(suppliedCue, elapsedCue)
    }

    func testBoardCueUsesActiveModeDuringWork() {
        let timeline = WorkoutTimeline(steps: restPreviewSteps)

        let cue = timeline.boardCue(at: 5, countdown: 0, isComplete: false)

        XCTAssertEqual(cue.step?.id, "work")
        XCTAssertEqual(cue.mode, .active)
        XCTAssertFalse(cue.isResting)
        XCTAssertFalse(cue.isSuppressed)
    }

    func testBoardCueSuppressesCountdownAndCompletion() {
        let timeline = WorkoutTimeline(steps: restPreviewSteps)

        let countdownCue = timeline.boardCue(at: 5, countdown: 3, isComplete: false)
        XCTAssertNil(countdownCue.step)
        XCTAssertTrue(countdownCue.isSuppressed)

        let completionCue = timeline.boardCue(at: 72, countdown: 0, isComplete: true)
        XCTAssertNil(completionCue.step)
        XCTAssertTrue(completionCue.isSuppressed)
    }

    func testBoardCueKeepsFinalRestAsRecoveryWithoutPreviewStep() {
        let timeline = WorkoutTimeline(steps: restPreviewSteps)

        let cue = timeline.boardCue(at: 72, countdown: 0, isComplete: false)

        XCTAssertNil(cue.step)
        XCTAssertEqual(cue.mode, .preview)
        XCTAssertTrue(cue.isResting)
        XCTAssertFalse(cue.isSuppressed)
    }

    func testRestPreviewStrokeCompanionIsOpaqueAndDarkerThanRestBlue() {
        let fill = UIColor(Color.restBlue)
        let stroke = UIColor(Color.restBlueDeep)
        var fillRed: CGFloat = 0
        var fillGreen: CGFloat = 0
        var fillBlue: CGFloat = 0
        var fillAlpha: CGFloat = 0
        var strokeRed: CGFloat = 0
        var strokeGreen: CGFloat = 0
        var strokeBlue: CGFloat = 0
        var strokeAlpha: CGFloat = 0

        XCTAssertTrue(fill.getRed(&fillRed, green: &fillGreen, blue: &fillBlue, alpha: &fillAlpha))
        XCTAssertTrue(stroke.getRed(&strokeRed, green: &strokeGreen, blue: &strokeBlue, alpha: &strokeAlpha))
        XCTAssertEqual(strokeAlpha, 1, accuracy: 0.001)
        XCTAssertLessThan(strokeRed, fillRed)
        XCTAssertLessThan(strokeGreen, fillGreen)
        XCTAssertLessThan(strokeBlue, fillBlue)
    }
}

final class WorkoutClockTests: XCTestCase {
    deinit {}

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
    func testCountdownDurationsKeepInitialAndSkipStartAtThree() {
        let now = Date(timeIntervalSinceReferenceDate: 2_000)

        XCTAssertEqual(
            WorkoutSessionPolicy.startDate(for: .initial, now: now),
            now.addingTimeInterval(3)
        )
        XCTAssertEqual(
            WorkoutSessionPolicy.startDate(for: .skip, now: now),
            now.addingTimeInterval(3)
        )
    }

    func testMonotonicCountdownRemainingUsesCeilingAndReachesZeroAtStart() {
        let now: TimeInterval = 100
        let start = now + 5

        XCTAssertEqual(
            WorkoutSessionPolicy.countdownRemaining(startUptime: start, nowUptime: now),
            5
        )
        XCTAssertEqual(
            WorkoutSessionPolicy.countdownRemaining(startUptime: start, nowUptime: now + 1.1),
            4
        )
        XCTAssertEqual(
            WorkoutSessionPolicy.countdownRemaining(startUptime: start, nowUptime: start),
            0
        )
        XCTAssertEqual(
            WorkoutSessionPolicy.countdownRemaining(startUptime: nil, nowUptime: now),
            0
        )
    }

    func testImmediateStartIsAllowedOnlyForAnUnstartedFirstAppearance() {
        XCTAssertTrue(
            WorkoutSessionPolicy.shouldAutoStart(
                startsImmediately: true,
                didAutoStart: false,
                isRunning: false,
                routineStartedAt: nil
            )
        )
    }

    func testImmediateStartIsDisabledAfterTheOneShotHasRun() {
        XCTAssertFalse(
            WorkoutSessionPolicy.shouldAutoStart(
                startsImmediately: true,
                didAutoStart: true,
                isRunning: false,
                routineStartedAt: nil
            )
        )
    }

    func testImmediateStartDoesNotRestartAStartedOrPausedSession() {
        let routineStart = Date(timeIntervalSinceReferenceDate: 1_000)

        XCTAssertFalse(
            WorkoutSessionPolicy.shouldAutoStart(
                startsImmediately: true,
                didAutoStart: false,
                isRunning: true,
                routineStartedAt: routineStart
            )
        )
        XCTAssertFalse(
            WorkoutSessionPolicy.shouldAutoStart(
                startsImmediately: true,
                didAutoStart: false,
                isRunning: false,
                routineStartedAt: routineStart
            )
        )
    }

    func testManualWorkoutRouteDoesNotAutoStart() {
        XCTAssertFalse(
            WorkoutSessionPolicy.shouldAutoStart(
                startsImmediately: false,
                didAutoStart: false,
                isRunning: false,
                routineStartedAt: nil
            )
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

final class WorkoutStepDurationTests: XCTestCase {
    deinit {}

    func testRestPhaseHasFullDurationAsRest() {
        let rest = WorkoutStep(
            id: "rest",
            number: 1,
            title: "Rest",
            instruction: "Rest.",
            accessory: "",
            duration: 30,
            phase: .rest,
            targets: []
        )

        XCTAssertEqual(rest.activeDuration, 30)
        XCTAssertFalse(rest.hasRestInterval)
        XCTAssertEqual(rest.restDuration, 0)
    }

    func testTimedPullTaskHasNoFollowingRest() {
        let pull = WorkoutStep(
            id: "pull",
            number: 1,
            title: "Pull",
            instruction: "Do 2 pull-ups.",
            accessory: "",
            duration: 10,
            phase: .pull,
            targets: [.feature(.jug)],
            timedWorkDuration: 10
        )

        XCTAssertEqual(pull.activeDuration, 10)
        XCTAssertFalse(pull.hasRestInterval)
    }
}

final class MetoliusTaskExpansionTests: XCTestCase {
    deinit {}

    func testPullUpTasksUseFiveSecondsPerPullUp() throws {
        let task = MetoliusCycleBuilder.pullUps(
            count: 3,
            title: "Three pull-ups",
            instruction: "Do 3 pull-ups on the jugs.",
            phase: .pull,
            targets: [.feature(.jug)]
        )

        let steps = try MetoliusCycleBuilder.expand(planID: "test", minute: 1, tasks: [task])

        XCTAssertEqual(steps[0].duration, 15)
        XCTAssertEqual(steps[1].phase, .rest)
        XCTAssertEqual(steps[1].duration, 45)
    }

    func testExpansionKeepsTaskOrderAndAddsRemainingMinuteRest() throws {
        let first = MetoliusCycleBuilder.fixed(
            title: "First hang",
            instruction: "Hang for 15 seconds.",
            duration: 15,
            phase: .hang,
            targets: [.feature(.largeEdge)]
        )
        let second = MetoliusCycleBuilder.pullUps(
            count: 2,
            title: "Pull-ups",
            instruction: "Do 2 pull-ups.",
            phase: .pull,
            targets: [.feature(.jug)]
        )

        let steps = try MetoliusCycleBuilder.expand(planID: "test", minute: 2, tasks: [first, second])

        XCTAssertEqual(steps.map(\.id), ["test.minute-2.task-1", "test.minute-2.task-2", "test.minute-2.rest"])
        XCTAssertEqual(steps.map(\.duration), [15, 10, 35])
        XCTAssertEqual(steps[0].targets, first.targets)
        XCTAssertEqual(steps[1].targets, second.targets)
    }

    func testExpansionRejectsTasksThatExceedTheMinute() {
        let overfull = MetoliusTaskDefinition(
            title: "Overfull",
            instruction: "Overfull",
            accessory: "",
            duration: 61,
            phase: .hang,
            targets: [.feature(.largeEdge)],
            gripType: nil
        )

        XCTAssertThrowsError(try MetoliusCycleBuilder.expand(planID: "test", minute: 3, tasks: [overfull]))
    }
}

final class MetoliusCatalogExpansionTests: XCTestCase {
    deinit {}

    private let sourceURL = URL(
        string: "https://www.metoliusclimbing.com/pages/10-minute-sequences-hangboard-training-guide"
    )!

    func testIntermediateMinuteTwoIsTwoTaskStepsThenRest() {
        let steps = PlanCatalog.metoliusIntermediate.steps.filter {
            $0.id.hasPrefix("intermediate.minute-2.")
        }

        XCTAssertEqual(
            steps.map(\.title),
            ["Round sloper pull-ups", "Medium-edge hang", "Minute 2 rest"]
        )
        XCTAssertEqual(steps.map(\.duration), [10, 20, 30])
        XCTAssertEqual(steps[0].targets, [.feature(.roundSloper)])
        XCTAssertEqual(steps[1].targets, [.feature(.mediumEdge)])
        XCTAssertEqual(steps[2].phase, .rest)
    }

    func testIntermediateOffsetPullsTellTheHandSwitchAsSeparateSteps() {
        let steps = PlanCatalog.metoliusIntermediate.steps.filter {
            $0.id.hasPrefix("intermediate.minute-6.")
        }

        XCTAssertEqual(steps.map(\.duration), [15, 15, 30])
        XCTAssertEqual(
            steps.prefix(2).map(\.targets),
            [
                [.feature(.jug), .feature(.smallEdge)],
                [.feature(.jug), .feature(.smallEdge)]
            ]
        )
        XCTAssertTrue(steps[1].instruction.lowercased().contains("change hands"))
        XCTAssertTrue(steps[1].instruction.lowercased().contains("repeat"))
        XCTAssertEqual(steps[2].phase, .rest)
    }

    func testMaxEffortMetoliusStepsUseStopwatchTiming() {
        let step = PlanCatalog.metoliusEntry.steps.first { $0.title == "Maximum sloper hang" }!

        XCTAssertEqual(step.duration, 60)
        XCTAssertEqual(step.timedWorkDuration, nil)
        XCTAssertEqual(step.segments, [
            WorkoutSegment(
                kind: .work,
                target: .feature(.roundSloper),
                timing: .stopwatch,
                duration: nil
            )
        ])
    }

    func testAdvancedMinuteFourLeavesTwentySecondsToRest() {
        let steps = PlanCatalog.metoliusAdvanced.steps.filter { $0.id.hasPrefix("advanced.minute-4.") }

        XCTAssertEqual(steps.map(\.duration), [40, 20])
        XCTAssertEqual(steps.last?.phase, .rest)
    }

    func testMetoliusPlansRemainTenMinutesAndAreMarkedAdapted() {
        let plans = [
            PlanCatalog.metoliusEntry,
            PlanCatalog.metoliusIntermediate,
            PlanCatalog.metoliusAdvanced
        ]

        XCTAssertEqual(plans.map(\.steps.count), [20, 26, 27])
        for plan in plans {
            XCTAssertEqual(plan.duration, 600)
            XCTAssertEqual(plan.provenance, .adapted)
            XCTAssertEqual(plan.sourceURL, sourceURL)
            XCTAssertTrue(plan.subtitle.contains("guided task timing"))
            XCTAssertTrue(plan.subtitle.contains("5 seconds"))
            XCTAssertEqual(plan.steps.map(\.number), Array(1...plan.steps.count))
            XCTAssertEqual(Set(plan.steps.map(\.id)).count, plan.steps.count)
        }
    }

    func testExpandedCatalogPreservesCompoundTasksChoicesAndMaximumEfforts() {
        let entry = PlanCatalog.metoliusEntry.steps
        let advanced = PlanCatalog.metoliusAdvanced.steps

        let pocketShrugs = entry.filter { $0.id.hasPrefix("entry.minute-4.") }
        XCTAssertEqual(pocketShrugs.map(\.duration), [15, 45])
        XCTAssertTrue(pocketShrugs[0].instruction.contains("3 shrugs"))

        let entryMinuteSix = entry.filter { $0.id.hasPrefix("entry.minute-6.") }
        XCTAssertEqual(entryMinuteSix.map(\.duration), [10, 5, 45])
        XCTAssertEqual(entryMinuteSix[0].targets, [.feature(.roundSloper)])
        XCTAssertEqual(entryMinuteSix[1].targets, [.feature(.pocket)])

        let advancedMinuteEight = advanced.filter { $0.id.hasPrefix("advanced.minute-8.") }
        XCTAssertEqual(advancedMinuteEight.map(\.duration), [15, 15, 30])
        XCTAssertEqual(advancedMinuteEight.count, 3)
        XCTAssertTrue(advancedMinuteEight[1].title.lowercased().contains("choose one"))
        XCTAssertTrue(advancedMinuteEight[1].instruction.lowercased().contains("choose one"))
        XCTAssertTrue(advancedMinuteEight[1].instruction.contains("5-second front lever"))
        XCTAssertTrue(advancedMinuteEight[1].instruction.contains("15-second straight-arm hang"))
        XCTAssertTrue(advancedMinuteEight[1].accessory.lowercased().contains("choose one"))
        XCTAssertTrue(advancedMinuteEight[1].accessory.contains("5 seconds"))
        XCTAssertTrue(advancedMinuteEight[1].accessory.contains("15 seconds"))

        let advancedMinuteTen = advanced.filter { $0.id.hasPrefix("advanced.minute-10.") }
        XCTAssertEqual(advancedMinuteTen.map(\.duration), [60])
        XCTAssertTrue(advancedMinuteTen[0].instruction.lowercased().contains("to failure"))
        XCTAssertTrue(advancedMinuteTen[0].instruction.lowercased().contains("no rest"))
    }
}

final class WorkoutAudioCuePolicyTests: XCTestCase {
    private let stepID = "f80-set-2-rep-3"

    func testMissingAudioMomentRequestsImmediateStop() {
        XCTAssertEqual(WorkoutAudioCuePolicy.action(for: nil), .stop)
    }

    func testNumericAudioMomentRequestsSpeechWithoutAStageLabel() {
        let moment = WorkoutAudioMoment(key: "skip-3", phrase: "3")

        XCTAssertEqual(
            WorkoutAudioCuePolicy.action(for: moment),
            .speak(moment)
        )
        XCTAssertTrue(moment.phrase.allSatisfy { $0.isNumber })
    }

    func testSkipCountdownCueUsesOnlyTheCountdownNumber() {
        XCTAssertEqual(
            WorkoutAudioCuePolicy.moment(
                stepID: stepID,
                segmentName: "active",
                initialCountdown: 3,
                intervalSecondsRemaining: 60,
                isComplete: false,
                countdownKind: .skip
            ),
            WorkoutAudioMoment(key: "skip-3", phrase: "3")
        )
    }

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

    func testCompletionDuringInitialCountdownRequestsStop() {
        XCTAssertEqual(
            WorkoutAudioCuePolicy.action(for: WorkoutAudioCuePolicy.moment(
                stepID: stepID,
                segmentName: "active",
                initialCountdown: 3,
                intervalSecondsRemaining: 60,
                isComplete: true
            )),
            .stop
        )
    }

    func testCompletionDuringSkipCountdownRequestsStop() {
        XCTAssertEqual(
            WorkoutAudioCuePolicy.action(for: WorkoutAudioCuePolicy.moment(
                stepID: stepID,
                segmentName: "active",
                initialCountdown: 2,
                intervalSecondsRemaining: 60,
                isComplete: true,
                countdownKind: .skip
            )),
            .stop
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

    func testInitialStartUsesMonotonicUptimeForElapsedAndCountdown() {
        let wallClockStart = Date(timeIntervalSinceReferenceDate: 3_000)
        let uptime: TimeInterval = 100
        var state = WorkoutSessionState()

        state.toggleRunning(uptime: uptime, now: wallClockStart)

        XCTAssertEqual(state.activeStartUptime, 103)
        XCTAssertEqual(state.routineStartedAt, wallClockStart.addingTimeInterval(3))
        XCTAssertEqual(state.countdownRemaining(at: uptime), 3)
        XCTAssertEqual(state.countdownRemaining(at: uptime + 1.1), 2)
        XCTAssertEqual(
            state.currentElapsed(planDuration: 90, at: uptime + 2.9),
            0,
            accuracy: 0.000_1
        )

        state.transitionExpiredCountdown(at: uptime + 3)

        XCTAssertEqual(state.currentElapsed(planDuration: 90, at: uptime + 4.25), 1.25, accuracy: 0.000_1)
    }

    func testPausedSessionSkipCountsDownThenExplicitExpiryStartsRunningDestination() {
        let now: TimeInterval = 100
        let timeline = WorkoutTimeline(steps: steps)
        var state = WorkoutSessionState(
            activeStartUptime: nil,
            pausedElapsed: 10,
            routineStartedAt: Date(timeIntervalSinceReferenceDate: 2_980)
        )

        XCTAssertTrue(state.skipCurrentStep(timeline: timeline, planDuration: timeline.duration, at: now))
        XCTAssertEqual(state.pausedElapsed, 60)
        XCTAssertEqual(state.countdownKind, .skip)
        XCTAssertEqual(state.countdownRemaining(at: now), 3)
        XCTAssertFalse(state.canNavigate(planDuration: timeline.duration, at: now))

        let countdownStart = now + 3
        XCTAssertEqual(state.countdownRemaining(at: countdownStart), 0)
        XCTAssertEqual(state.countdownKind, .skip)
        state.transitionExpiredCountdown(at: countdownStart)
        XCTAssertNil(state.countdownKind)
        XCTAssertEqual(state.activeStartUptime, countdownStart)
        XCTAssertEqual(state.currentElapsed(planDuration: timeline.duration, at: countdownStart), 60)
        XCTAssertTrue(state.canNavigate(planDuration: timeline.duration, at: countdownStart))
    }

    func testPausedDirectSeekPreservesPausedState() {
        let now: TimeInterval = 100
        let timeline = WorkoutTimeline(steps: steps)
        var state = WorkoutSessionState(
            activeStartUptime: nil,
            pausedElapsed: 10,
            routineStartedAt: Date(timeIntervalSinceReferenceDate: 2_980)
        )

        state.seek(to: 80, planDuration: timeline.duration, at: now)

        XCTAssertNil(state.activeStartUptime)
        XCTAssertNil(state.countdownKind)
        XCTAssertEqual(state.pausedElapsed, 80)
        XCTAssertEqual(state.currentElapsed(planDuration: timeline.duration, at: now + 4), 80)
    }

    func testInitialStartCancelAndRestartLifecycle() {
        let now: TimeInterval = 100
        let wallClockStart = Date(timeIntervalSinceReferenceDate: 3_000)
        var state = WorkoutSessionState()

        state.toggleRunning(uptime: now, now: wallClockStart)

        let firstStart = now + 3
        XCTAssertEqual(state.activeStartUptime, firstStart)
        XCTAssertEqual(state.routineStartedAt, wallClockStart.addingTimeInterval(3))
        XCTAssertEqual(state.countdownKind, .initial)
        XCTAssertEqual(state.countdownRemaining(at: now), 3)

        state.cancelCountdown(at: now + 1)

        XCTAssertNil(state.activeStartUptime)
        XCTAssertNil(state.routineStartedAt)
        XCTAssertNil(state.countdownKind)
        XCTAssertEqual(state.pausedElapsed, 0)

        let restart = now + 10
        state.toggleRunning(uptime: restart, now: wallClockStart.addingTimeInterval(10))

        XCTAssertEqual(state.activeStartUptime, restart + 3)
        XCTAssertEqual(state.routineStartedAt, wallClockStart.addingTimeInterval(13))
        XCTAssertEqual(state.countdownKind, .initial)
    }

    func testCountdownExpiryReadIsPureUntilExplicitTransitionClearsKind() {
        let now: TimeInterval = 100
        let expiry = now + 5
        let immutableState = WorkoutSessionState(
            activeStartUptime: expiry,
            countdownKind: .skip,
            pausedElapsed: 60,
            routineStartedAt: Date(timeIntervalSinceReferenceDate: 2_980)
        )
        var state = WorkoutSessionState(
            activeStartUptime: expiry,
            countdownKind: .skip,
            pausedElapsed: 60,
            routineStartedAt: Date(timeIntervalSinceReferenceDate: 2_980)
        )

        XCTAssertEqual(immutableState.countdownRemaining(at: expiry), 0)
        XCTAssertEqual(state.countdownRemaining(at: expiry), 0)
        XCTAssertEqual(state.countdownKind, .skip)
        XCTAssertEqual(state.activeStartUptime, expiry)

        state.transitionExpiredCountdown(at: expiry - 0.1)

        XCTAssertEqual(state.countdownKind, .skip)
        XCTAssertEqual(state.activeStartUptime, expiry)

        state.transitionExpiredCountdown(at: expiry)

        XCTAssertNil(state.countdownKind)
        XCTAssertEqual(state.activeStartUptime, expiry)
    }

    func testCancelSkipCountdownKeepsDestinationPaused() {
        let now: TimeInterval = 100
        let timeline = WorkoutTimeline(steps: steps)
        var state = WorkoutSessionState(
            activeStartUptime: now - 10,
            pausedElapsed: 10,
            routineStartedAt: Date(timeIntervalSinceReferenceDate: 2_980)
        )

        XCTAssertTrue(state.skipCurrentStep(timeline: timeline, planDuration: timeline.duration, at: now))
        state.cancelCountdown(at: now + 2)

        XCTAssertNil(state.activeStartUptime)
        XCTAssertNil(state.countdownKind)
        XCTAssertEqual(state.pausedElapsed, 60)
        XCTAssertEqual(state.routineStartedAt, Date(timeIntervalSinceReferenceDate: 2_980))
    }

    func testInterruptionDuringSkipCountdownKeepsDestinationPaused() {
        let now: TimeInterval = 100
        let timeline = WorkoutTimeline(steps: steps)
        var state = WorkoutSessionState(
            activeStartUptime: now - 10,
            pausedElapsed: 10,
            routineStartedAt: Date(timeIntervalSinceReferenceDate: 2_980)
        )

        XCTAssertTrue(state.skipCurrentStep(timeline: timeline, planDuration: timeline.duration, at: now))
        state.pauseForInterruption(at: now + 2)

        XCTAssertNil(state.activeStartUptime)
        XCTAssertNil(state.countdownKind)
        XCTAssertEqual(state.pausedElapsed, 60)
        XCTAssertEqual(state.routineStartedAt, Date(timeIntervalSinceReferenceDate: 2_980))
    }

    func testDirectSeekClearsPendingSkipCountdownAndPreservesRunning() {
        let now: TimeInterval = 100
        let timeline = WorkoutTimeline(steps: steps)
        var state = WorkoutSessionState(
            activeStartUptime: now - 10,
            pausedElapsed: 10,
            routineStartedAt: Date(timeIntervalSinceReferenceDate: 2_980)
        )

        XCTAssertTrue(state.skipCurrentStep(timeline: timeline, planDuration: timeline.duration, at: now))
        state.seek(to: 80, planDuration: timeline.duration, at: now + 2)

        XCTAssertNil(state.countdownKind)
        XCTAssertEqual(state.activeStartUptime, now + 2)
        XCTAssertEqual(state.pausedElapsed, 80)
        XCTAssertEqual(
            state.currentElapsed(planDuration: timeline.duration, at: now + 4),
            82
        )
    }

    func testFinalSkipSeeksDirectlyToCompletion() {
        let now: TimeInterval = 100
        let timeline = WorkoutTimeline(steps: steps)
        var state = WorkoutSessionState(
            activeStartUptime: now - 1,
            pausedElapsed: 85,
            routineStartedAt: Date(timeIntervalSinceReferenceDate: 2_900)
        )

        XCTAssertTrue(state.skipCurrentStep(timeline: timeline, planDuration: timeline.duration, at: now))

        XCTAssertNil(state.countdownKind)
        XCTAssertEqual(state.activeStartUptime, now)
        XCTAssertEqual(state.pausedElapsed, 90)
        XCTAssertEqual(state.currentElapsed(planDuration: timeline.duration, at: now + 10), 90)
        XCTAssertFalse(state.canNavigate(planDuration: timeline.duration, at: now))
    }
}
