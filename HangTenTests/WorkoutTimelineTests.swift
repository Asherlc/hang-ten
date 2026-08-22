import AVFoundation
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
            gripType: .halfCrimp,
            fingerConfiguration: FingerConfiguration(engagedFingers: [.index, .ring])
        )

        let cue = WorkoutHoldCuePolicy.resolve(step: step, hold: hold, on: board(containing: [hold]))

        XCTAssertEqual(cue?.hold, hold)
        XCTAssertEqual(cue?.gripType, .halfCrimp)
        XCTAssertEqual(cue?.fingerConfiguration?.orderedFingers, [.index, .ring])
    }

    func testHoldCueDoesNotInferGripFromBoardMetadata() {
        let hold = BoardHold(
            id: "cue-pocket",
            name: "Cue pocket",
            shortLabel: "P",
            detail: "Pocket",
            kind: .pocket,
            frame: HoldFrame(x: 0, y: 0, width: 1, height: 1),
            gripType: .openHand,
            fingerCapacity: 3
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

        let cue = WorkoutHoldCuePolicy.resolve(step: step, hold: hold, on: board(containing: [hold]))

        XCTAssertNil(cue)
    }

    func testHoldCueAcceptsHighlightedFallbackFeatureHold() {
        let hold = BoardHold(
            id: "fallback-edge",
            name: "Fallback edge",
            shortLabel: "F",
            detail: "Fallback edge",
            kind: .edge,
            frame: HoldFrame(x: 0, y: 0, width: 1, height: 1),
            features: [.largeEdge]
        )
        let step = WorkoutStep(
            id: "cue-step",
            number: 1,
            title: "Cue step",
            instruction: "Cue instruction",
            accessory: "Cue accessory",
            duration: 10,
            phase: .hang,
            targets: [.feature(.smallEdge, fallbacks: [.largeEdge])],
            gripType: .halfCrimp
        )

        let cue = WorkoutHoldCuePolicy.resolve(step: step, hold: hold, on: board(containing: [hold]))

        XCTAssertEqual(cue?.hold, hold)
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

        XCTAssertNil(WorkoutHoldCuePolicy.resolve(step: step, hold: hold, on: board(containing: [hold])))
    }

    func testHoldCueResolvesWhenHighlightedHoldMatchesSingleTarget() {
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
            targets: [.ids(hold.id)],
            gripType: .halfCrimp
        )

        XCTAssertNotNil(
            WorkoutHoldCuePolicy.resolve(step: step, hold: hold, on: board(containing: [hold]))
        )
    }

    func testSourceBackedHoldCueRemainsVisibleAtCountdownZero() {
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
            targets: [.ids(hold.id)],
            gripType: .halfCrimp,
            fingerConfiguration: FingerConfiguration(engagedFingers: [.index, .ring])
        )
        let holdCue = WorkoutHoldCuePolicy.resolve(step: step, hold: hold, on: board(containing: [hold]))

        XCTAssertTrue(
            WorkoutHoldCueVisibilityPolicy.showsCue(
                holdCue: holdCue,
                countdown: 0,
                isComplete: false
            )
        )
    }

    func testHoldCueVisibilityShowsAvailableCueDuringSkipCountdown() {
        let holdCue = WorkoutHoldCue(
            hold: BoardHold(
                id: "cue-edge",
                name: "Cue edge",
                shortLabel: "E",
                detail: "Edge",
                kind: .edge,
                frame: HoldFrame(x: 0, y: 0, width: 1, height: 1)
            ),
            gripType: .openHand,
            fingerConfiguration: FingerConfiguration(engagedFingers: [.index, .ring])
        )

        XCTAssertTrue(
            WorkoutHoldCueVisibilityPolicy.showsCue(
                holdCue: holdCue,
                countdown: 3,
                isComplete: false,
                isSkipCountdown: true
            )
        )
    }

    func testHoldCueVisibilityStillSuppressesCountdownCompletionAndMissingCue() {
        let holdCue = WorkoutHoldCue(
            hold: BoardHold(
                id: "cue-edge",
                name: "Cue edge",
                shortLabel: "E",
                detail: "Edge",
                kind: .edge,
                frame: HoldFrame(x: 0, y: 0, width: 1, height: 1)
            ),
            gripType: .openHand
        )

        XCTAssertFalse(
            WorkoutHoldCueVisibilityPolicy.showsCue(
                holdCue: holdCue,
                countdown: 3,
                isComplete: false
            )
        )
        XCTAssertFalse(
            WorkoutHoldCueVisibilityPolicy.showsCue(
                holdCue: holdCue,
                countdown: 0,
                isComplete: true
            )
        )
        XCTAssertFalse(
            WorkoutHoldCueVisibilityPolicy.showsCue(
                holdCue: nil,
                countdown: 0,
                isComplete: false
            )
        )
    }

    func testHoldCueIsUnavailableWhenHighlightedHoldDoesNotMatchSingleTarget() {
        let targetHold = BoardHold(
            id: "target-edge",
            name: "Target edge",
            shortLabel: "T",
            detail: "Edge",
            kind: .edge,
            frame: HoldFrame(x: 0, y: 0, width: 1, height: 1)
        )
        let highlightedHold = BoardHold(
            id: "highlighted-jug",
            name: "Highlighted jug",
            shortLabel: "J",
            detail: "Jug",
            kind: .jug,
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
            targets: [.ids(targetHold.id)]
        )

        XCTAssertNil(
            WorkoutHoldCuePolicy.resolve(
                step: step,
                hold: highlightedHold,
                on: board(containing: [targetHold, highlightedHold])
            )
        )
    }

    private func board(containing holds: [BoardHold]) -> TrainingBoard {
        TrainingBoard(
            id: "cue-board",
            manufacturer: "Test",
            name: "Cue board",
            subtitle: "",
            dimensions: "",
            aspectRatio: 1,
            holds: holds,
            productURL: URL(string: "https://example.com/cue-board")!,
            photoAssetName: nil
        )
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

final class CountdownAudioSchedulerTests: XCTestCase {
    func testEmptyColdRenderRetriesBeforeCountdownArming() {
        XCTAssertTrue(
            CountdownAudioRenderAttemptPolicy.shouldRetry(
                completedAttempts: 1,
                renderedBufferCount: 0
            )
        )
        XCTAssertFalse(
            CountdownAudioRenderAttemptPolicy.shouldRetry(
                completedAttempts: 2,
                renderedBufferCount: 1
            )
        )
        XCTAssertTrue(
            CountdownAudioRenderAttemptPolicy.shouldIgnoreCallback(
                phraseIsAlreadyPrepared: true
            )
        )
    }

    func testEmptyRenderRetryExhaustionFailsWithoutScheduling() {
        XCTAssertFalse(
            CountdownAudioRenderAttemptPolicy.shouldRetry(
                completedAttempts: CountdownAudioRenderAttemptPolicy.maximumAttempts,
                renderedBufferCount: 0
            )
        )

        let backend = RecordingCountdownAudioSchedulingBackend(scheduleResult: false)
        let lifecycleLogger = RecordingCountdownAudioLifecycleLogger()
        let scheduler = CountdownAudioScheduler(
            backend: backend,
            lifecycleLogger: lifecycleLogger
        )
        scheduler.prewarm { _ in }

        XCTAssertFalse(scheduler.schedule(remainingFrom: "3", startHostTime: 100))
        XCTAssertFalse(lifecycleLogger.events.contains { event in
            if case .scheduleAccepted = event { return true }
            return false
        })
    }

    func testLifecycleLoggerRecordsPrewarmAndAcceptedHostTimeOffsets() {
        let backend = RecordingCountdownAudioSchedulingBackend()
        let lifecycleLogger = RecordingCountdownAudioLifecycleLogger()
        let scheduler = CountdownAudioScheduler(
            backend: backend,
            lifecycleLogger: lifecycleLogger
        )

        scheduler.prewarm { _ in }
        XCTAssertTrue(scheduler.schedule(remainingFrom: "3", startHostTime: 100))

        XCTAssertEqual(
            lifecycleLogger.events,
            [
                .prewarmCompleted(succeeded: true),
                .scheduleAccepted(phrases: ["3", "2", "1"], startHostTime: 100, offsets: [0, 1, 2])
            ]
        )
    }

    func testLifecycleLoggerRecordsRejectedScheduleWithoutFallback() {
        let backend = RecordingCountdownAudioSchedulingBackend(scheduleResult: false)
        let lifecycleLogger = RecordingCountdownAudioLifecycleLogger()
        let scheduler = CountdownAudioScheduler(
            backend: backend,
            lifecycleLogger: lifecycleLogger
        )

        XCTAssertFalse(scheduler.schedule(remainingFrom: "3", startHostTime: 100))
        XCTAssertEqual(
            lifecycleLogger.events,
            [.scheduleRejected(phrases: ["3", "2", "1"], startHostTime: 100)]
        )
    }

    func testPrewarmCompletesOnlyAfterBackendPreparation() {
        let backend = RecordingCountdownAudioSchedulingBackend(
            automaticallyCompletesPrewarm: false
        )
        let scheduler = CountdownAudioScheduler(backend: backend)
        var result: Bool?

        scheduler.prewarm { result = $0 }

        XCTAssertNil(result)
        backend.completePrewarm(succeeded: true)
        XCTAssertEqual(result, true)
    }

    // Catches a regression that schedules only the currently displayed countdown number.
    func testThreeSchedulesEveryCountdownCueAtOneSecondOffsets() {
        let backend = RecordingCountdownAudioSchedulingBackend()
        let scheduler = CountdownAudioScheduler(backend: backend)

        XCTAssertTrue(scheduler.schedule(remainingFrom: "3", startHostTime: 100))
        XCTAssertEqual(backend.schedules.count, 1)
        XCTAssertEqual(backend.schedules[0].schedule.cues.map(\.phrase), ["3", "2", "1"])
        XCTAssertEqual(backend.schedules[0].schedule.cues.map(\.offset), [0, 1, 2])
        XCTAssertEqual(backend.schedules[0].startHostTime, 100)
    }

    // Catches a regression that always restarts a full countdown after a later tick.
    func testTwoSchedulesOnlyTheRemainingCountdownCues() {
        let backend = RecordingCountdownAudioSchedulingBackend()
        let scheduler = CountdownAudioScheduler(backend: backend)

        XCTAssertTrue(scheduler.schedule(remainingFrom: "2", startHostTime: 101))
        XCTAssertEqual(backend.schedules[0].schedule.cues.map(\.phrase), ["2", "1"])
        XCTAssertEqual(backend.schedules[0].schedule.cues.map(\.offset), [0, 1])
    }

    // Catches a regression that queues a second sequence when SwiftUI publishes a later tick.
    func testDuplicateActiveCountdownDoesNotScheduleAnyAdditionalCue() {
        let backend = RecordingCountdownAudioSchedulingBackend()
        let scheduler = CountdownAudioScheduler(backend: backend)

        XCTAssertTrue(scheduler.schedule(remainingFrom: "3", startHostTime: 100))
        XCTAssertFalse(scheduler.schedule(remainingFrom: "2", startHostTime: 101))
        XCTAssertEqual(backend.schedules.count, 1)
        XCTAssertEqual(backend.schedules[0].schedule.cues.map(\.phrase), ["3", "2", "1"])
    }
}

final class CountdownAudioBufferSchedulingBackendTests: XCTestCase {
    func testPrewarmPreparesEngineBeforeAnyBufferIsScheduled() {
        let playback = RecordingCountdownAudioBufferPlayback()
        let backend = CountdownAudioBufferSchedulingBackend(
            buffersForSchedule: { _ in
                [
                    "3": [makeCountdownPCMBuffer(duration: 0.5)],
                    "2": [makeCountdownPCMBuffer(duration: 0.5)],
                    "1": [makeCountdownPCMBuffer(duration: 0.5)]
                ]
            },
            playback: playback,
            currentHostTime: { 0 }
        )

        XCTAssertTrue(backend.prewarm(CountdownAudioSchedule(remainingFrom: "3")))
        XCTAssertEqual(playback.events, [.prepare])

        XCTAssertTrue(
            backend.schedule(
                CountdownAudioSchedule(remainingFrom: "3"),
                startHostTime: AVAudioTime.hostTime(forSeconds: 100)
            )
        )
        XCTAssertEqual(playback.prepareCallCount, 1)
        XCTAssertEqual(playback.events.first, .prepare)
        XCTAssertEqual(playback.events.filter { $0 == .start }.count, 1)
    }

    // Catches cue offsets being converted from seconds with the wrong host-time scale.
    func testCueOffsetsConvertToExactHostTimesAndAllScheduleBeforePlay() {
        let playback = RecordingCountdownAudioBufferPlayback()
        let startHostTime = AVAudioTime.hostTime(forSeconds: 100)
        let backend = CountdownAudioBufferSchedulingBackend(
            buffersForSchedule: { _ in
                [
                    "3": [makeCountdownPCMBuffer(duration: 0.5)],
                    "2": [makeCountdownPCMBuffer(duration: 0.5)],
                    "1": [makeCountdownPCMBuffer(duration: 0.5)]
                ]
            },
            playback: playback,
            currentHostTime: { 0 }
        )

        XCTAssertTrue(
            backend.schedule(
                CountdownAudioSchedule(remainingFrom: "3"),
                startHostTime: startHostTime
            )
        )

        let oneSecond = AVAudioTime.hostTime(forSeconds: 1)
        XCTAssertEqual(
            playback.scheduledHostTimes,
            [startHostTime, startHostTime + oneSecond, startHostTime + (2 * oneSecond)]
        )
        let expectedEvents: [RecordingCountdownAudioBufferPlayback.Event] = [
            .prepare,
            .start,
            .schedule(startHostTime),
            .schedule(startHostTime + oneSecond),
            .schedule(startHostTime + (2 * oneSecond)),
            .play
        ]
        XCTAssertEqual(playback.events, expectedEvents)
    }

    // Catches callback chunks within one cue being scheduled at the same time.
    func testMultipleCueBuffersUseAccumulatedSampleDurationHostOffsets() {
        let playback = RecordingCountdownAudioBufferPlayback()
        let startHostTime = AVAudioTime.hostTime(forSeconds: 100)
        let backend = CountdownAudioBufferSchedulingBackend(
            buffersForSchedule: { _ in
                [
                    "1": [
                        makeCountdownPCMBuffer(duration: 0.25),
                        makeCountdownPCMBuffer(duration: 0.5)
                    ]
                ]
            },
            playback: playback,
            currentHostTime: { 0 }
        )

        XCTAssertTrue(
            backend.schedule(
                CountdownAudioSchedule(remainingFrom: "1"),
                startHostTime: startHostTime
            )
        )

        XCTAssertEqual(
            playback.scheduledHostTimes,
            [startHostTime, startHostTime + AVAudioTime.hostTime(forSeconds: 0.25)]
        )
    }

    // Catches a deadline crossing after buffers are queued but before playback starts.
    func testDeadlineCrossingImmediatelyBeforePlayClearsScheduledBuffers() {
        let playback = RecordingCountdownAudioBufferPlayback()
        let startHostTime = AVAudioTime.hostTime(forSeconds: 100)
        var observedHostTimes = [
            startHostTime - 3,
            startHostTime - 2,
            startHostTime
        ]
        let backend = CountdownAudioBufferSchedulingBackend(
            buffersForSchedule: { _ in ["1": [makeCountdownPCMBuffer(duration: 0.5)]] },
            playback: playback,
            currentHostTime: { observedHostTimes.removeFirst() }
        )

        XCTAssertFalse(
            backend.schedule(CountdownAudioSchedule(remainingFrom: "1"), startHostTime: startHostTime)
        )
        XCTAssertEqual(playback.scheduledBufferCountBeforeLastStop, 1)
        XCTAssertEqual(playback.scheduledBufferCount, 0)
        XCTAssertEqual(playback.playCallCount, 0)
        XCTAssertEqual(playback.stopCallCount, 1)
    }

    // Catches a rendered number that fills its slot and can delay or collide with the next cue.
    func testCueThatDoesNotFitStrictlyWithinOneSecondRejectsAllPlayback() {
        let playback = RecordingCountdownAudioBufferPlayback()
        let backend = CountdownAudioBufferSchedulingBackend(
            buffersForSchedule: { _ in
                [
                    "3": [makeCountdownPCMBuffer(duration: 1.0)],
                    "2": [makeCountdownPCMBuffer(duration: 0.5)],
                    "1": [makeCountdownPCMBuffer(duration: 0.5)]
                ]
            },
            playback: playback,
            currentHostTime: { 0 }
        )

        XCTAssertFalse(
            backend.schedule(
                CountdownAudioSchedule(remainingFrom: "3"),
                startHostTime: AVAudioTime.hostTime(forSeconds: 100)
            )
        )
        XCTAssertEqual(playback.prepareCallCount, 0)
        XCTAssertEqual(playback.scheduledBufferCount, 0)
        XCTAssertEqual(playback.playCallCount, 0)
    }

    // Catches a fractional short segment placing its second number before the
    // first number's rendered audio has finished.
    func testFractionalShortSegmentRejectsCueThatExceedsItsNextCueSlot() {
        let playback = RecordingCountdownAudioBufferPlayback()
        let backend = CountdownAudioBufferSchedulingBackend(
            buffersForSchedule: { _ in
                [
                    "3": [makeCountdownPCMBuffer(duration: 0.5)],
                    "2": [makeCountdownPCMBuffer(duration: 0.5)],
                    "1": [makeCountdownPCMBuffer(duration: 0.5)]
                ]
            },
            playback: playback,
            currentHostTime: { 0 }
        )
        let schedule = CountdownAudioSchedule(remainingFrom: "3")
            .appendingShortIntervals([1.2], startingAt: 3)

        XCTAssertFalse(
            backend.schedule(
                schedule,
                startHostTime: AVAudioTime.hostTime(forSeconds: 100)
            )
        )
        XCTAssertEqual(playback.prepareCallCount, 0)
        XCTAssertEqual(playback.scheduledBufferCount, 0)
        XCTAssertEqual(playback.playCallCount, 0)
    }

    // Catches the final cue using a one-second fallback deadline instead of
    // the actual end of a fractional short segment.
    func testFinalCueMustFitWithinFractionalShortSegmentEnd() {
        let playback = RecordingCountdownAudioBufferPlayback()
        let backend = CountdownAudioBufferSchedulingBackend(
            buffersForSchedule: { _ in
                [
                    "3": [makeCountdownPCMBuffer(duration: 0.5)],
                    "2": [makeCountdownPCMBuffer(duration: 0.5)],
                    "1": [makeCountdownPCMBuffer(duration: 0.5)]
                ]
            },
            playback: playback,
            currentHostTime: { 0 }
        )
        let schedule = CountdownAudioSchedule(remainingFrom: "3")
            .appendingShortIntervals([0.2], startingAt: 3)

        XCTAssertFalse(
            backend.schedule(
                schedule,
                startHostTime: AVAudioTime.hostTime(forSeconds: 100)
            )
        )
        XCTAssertEqual(playback.prepareCallCount, 0)
        XCTAssertEqual(playback.scheduledBufferCount, 0)
        XCTAssertEqual(playback.playCallCount, 0)
    }

    // Catches stop leaving pre-scheduled buffers owned by the player node.
    func testStopClearsScheduledPlayback() {
        let playback = RecordingCountdownAudioBufferPlayback()
        let backend = CountdownAudioBufferSchedulingBackend(
            buffersForSchedule: { _ in ["1": [makeCountdownPCMBuffer(duration: 0.5)]] },
            playback: playback,
            currentHostTime: { 0 }
        )

        XCTAssertTrue(
            backend.schedule(
                CountdownAudioSchedule(remainingFrom: "1"),
                startHostTime: AVAudioTime.hostTime(forSeconds: 100)
            )
        )
        XCTAssertEqual(playback.scheduledBufferCount, 1)

        backend.stop()

        XCTAssertEqual(playback.scheduledBufferCount, 0)
        XCTAssertEqual(playback.stopCallCount, 1)
    }
}

private final class RecordingCountdownAudioBufferPlayback: CountdownAudioBufferPlayback {
    enum Event: Equatable {
        case prepare
        case start
        case schedule(UInt64)
        case play
        case stop
    }

    private(set) var prepareCallCount = 0
    private(set) var scheduledBufferCount = 0
    private(set) var scheduledBufferCountBeforeLastStop = 0
    private(set) var playCallCount = 0
    private(set) var stopCallCount = 0
    private(set) var scheduledHostTimes: [UInt64] = []
    private(set) var events: [Event] = []

    func prepare(format: AVAudioFormat) {
        prepareCallCount += 1
        events.append(.prepare)
    }

    func start() throws {
        events.append(.start)
    }

    func schedule(_ buffer: AVAudioPCMBuffer, atHostTime hostTime: UInt64) {
        scheduledBufferCount += 1
        scheduledHostTimes.append(hostTime)
        events.append(.schedule(hostTime))
    }

    func play() {
        playCallCount += 1
        events.append(.play)
    }

    func stop() {
        stopCallCount += 1
        scheduledBufferCountBeforeLastStop = scheduledBufferCount
        scheduledBufferCount = 0
        scheduledHostTimes.removeAll()
        events.append(.stop)
    }
}

private func makeCountdownPCMBuffer(duration: TimeInterval) -> AVAudioPCMBuffer {
    let sampleRate = 100.0
    let format = AVAudioFormat(standardFormatWithSampleRate: sampleRate, channels: 1)!
    let frameCount = AVAudioFrameCount(duration * sampleRate)
    let buffer = AVAudioPCMBuffer(pcmFormat: format, frameCapacity: frameCount)!
    buffer.frameLength = frameCount
    return buffer
}

private final class RecordingCountdownAudioSchedulingBackend: CountdownAudioSchedulingBackend {
    struct ScheduledSequence {
        let schedule: CountdownAudioSchedule
        let startHostTime: UInt64
    }

    private(set) var schedules: [ScheduledSequence] = []
    private let automaticallyCompletesPrewarm: Bool
    private let scheduleResult: Bool
    private var prewarmCompletion: ((Bool) -> Void)?

    init(
        automaticallyCompletesPrewarm: Bool = true,
        scheduleResult: Bool = true
    ) {
        self.automaticallyCompletesPrewarm = automaticallyCompletesPrewarm
        self.scheduleResult = scheduleResult
    }

    func prewarm(completion: @escaping (Bool) -> Void) {
        if automaticallyCompletesPrewarm {
            completion(true)
        } else {
            prewarmCompletion = completion
        }
    }

    func completePrewarm(succeeded: Bool) {
        let completion = prewarmCompletion
        prewarmCompletion = nil
        completion?(succeeded)
    }

    func schedule(_ schedule: CountdownAudioSchedule, startHostTime: UInt64) -> Bool {
        guard scheduleResult else { return false }
        schedules.append(ScheduledSequence(schedule: schedule, startHostTime: startHostTime))
        return true
    }

    func stop() {}
}

private final class RecordingCountdownAudioLifecycleLogger: CountdownAudioLifecycleLogging {
    enum Event: Equatable {
        case prewarmCompleted(succeeded: Bool)
        case scheduleAccepted(phrases: [String], startHostTime: UInt64, offsets: [TimeInterval])
        case scheduleRejected(phrases: [String], startHostTime: UInt64)
    }

    private(set) var events: [Event] = []

    func prewarmCompleted(succeeded: Bool) {
        events.append(.prewarmCompleted(succeeded: succeeded))
    }

    func scheduleAccepted(_ schedule: CountdownAudioSchedule, startHostTime: UInt64) {
        events.append(
            .scheduleAccepted(
                phrases: schedule.cues.map(\.phrase),
                startHostTime: startHostTime,
                offsets: schedule.cues.map(\.offset)
            )
        )
    }

    func scheduleRejected(_ schedule: CountdownAudioSchedule, startHostTime: UInt64) {
        events.append(
            .scheduleRejected(
                phrases: schedule.cues.map(\.phrase),
                startHostTime: startHostTime
            )
        )
    }
}

@MainActor
final class WorkoutSpeechOwnershipTests: XCTestCase {
    func testRepeatedStopPreservesPendingStopOwnershipUntilCallback() {
        var ownership = WorkoutSpeechOwnership()
        let utterance = AVSpeechUtterance(string: "3")

        ownership.begin(utterance)
        ownership.requestStop()
        ownership.requestStop()

        XCTAssertTrue(ownership.ownsPendingStop(utterance))
        ownership.finishPendingStop(utterance)
        XCTAssertFalse(ownership.ownsPendingStop(utterance))
    }

    func testGenerationAndUtteranceIdentityProtectActiveAndPendingStopOwnership() {
        var ownership = WorkoutSpeechOwnership()
        let firstUtterance = AVSpeechUtterance(string: "3")
        let replacementUtterance = AVSpeechUtterance(string: "2")

        ownership.begin(firstUtterance)
        XCTAssertTrue(ownership.ownsActive(firstUtterance))

        ownership.requestStop()
        XCTAssertFalse(ownership.ownsActive(firstUtterance))
        XCTAssertTrue(ownership.ownsPendingStop(firstUtterance))
        ownership.finishPendingStop(firstUtterance)
        XCTAssertFalse(ownership.ownsPendingStop(firstUtterance))

        ownership.begin(replacementUtterance)
        XCTAssertFalse(ownership.ownsPendingStop(firstUtterance))
        XCTAssertTrue(ownership.ownsActive(replacementUtterance))

        ownership.finishActive(firstUtterance)
        XCTAssertTrue(ownership.ownsActive(replacementUtterance))
        ownership.finishActive(replacementUtterance)
        XCTAssertFalse(ownership.ownsActive(replacementUtterance))
    }
}

@MainActor
final class WorkoutAudioCoachTests: XCTestCase {
    // Catches a workout arming before numeric PCM and the audio engine are ready.
    func testCoachPublishesCountdownReadinessOnlyAfterPrewarmCompletes() async {
        let scheduler = RecordingCountdownAudioScheduler(automaticallyCompletesPrewarm: false)
        let coach = WorkoutAudioCoach(
            synthesizer: RecordingWorkoutSpeechSynthesizer(),
            audioSession: RecordingWorkoutAudioSession(),
            countdownScheduler: scheduler
        )

        XCTAssertEqual(coach.countdownPreparationState, .preparing)
        scheduler.completePrewarm(succeeded: true)
        await Task.yield()
        XCTAssertEqual(coach.countdownPreparationState, .ready)
    }

    // Catches a regression that lets later SwiftUI countdown ticks enqueue another sequence.
    func testCountdownStartsOnePreScheduledSequenceAndIgnoresLaterTicks() {
        let audioSession = RecordingWorkoutAudioSession()
        let synthesizer = RecordingWorkoutSpeechSynthesizer()
        let scheduler = RecordingCountdownAudioScheduler()
        let coach = WorkoutAudioCoach(
            synthesizer: synthesizer,
            audioSession: audioSession,
            countdownScheduler: scheduler
        )

        XCTAssertTrue(coach.startCountdown(remainingFrom: "3", startUptime: 100))
        XCTAssertFalse(coach.startCountdown(remainingFrom: "2", startUptime: 101))

        XCTAssertEqual(scheduler.startedSequences, [["3", "2", "1"]])
    }

    // Catches a regression that sends scheduler-owned numeric cues to live speech synthesis.
    func testScheduledCountdownDoesNotSpeakAnyNumberLive() {
        let audioSession = RecordingWorkoutAudioSession()
        let synthesizer = RecordingWorkoutSpeechSynthesizer()
        let scheduler = RecordingCountdownAudioScheduler()
        let coach = WorkoutAudioCoach(
            synthesizer: synthesizer,
            audioSession: audioSession,
            countdownScheduler: scheduler
        )

        coach.startCountdown(remainingFrom: "3", startUptime: 100)
        coach.startCountdown(remainingFrom: "2", startUptime: 101)
        coach.startCountdown(remainingFrom: "1", startUptime: 102)

        XCTAssertTrue(synthesizer.utterances.isEmpty)
        XCTAssertEqual(scheduler.startedSequences, [["3", "2", "1"]])
    }

    // Catches a regression that restores other-app audio before scheduled buffers are cancelled.
    func testStopCancelsCountdownBeforeDeactivatingAudioSession() {
        var events: [String] = []
        let audioSession = RecordingWorkoutAudioSession()
        audioSession.onSuccessfulNotificationAwareDeactivation = {
            events.append("session.deactivate")
        }
        let synthesizer = RecordingWorkoutSpeechSynthesizer()
        let scheduler = RecordingCountdownAudioScheduler(onStop: {
            events.append("countdown.stop")
        })
        let coach = WorkoutAudioCoach(
            synthesizer: synthesizer,
            audioSession: audioSession,
            countdownScheduler: scheduler
        )

        XCTAssertTrue(coach.startCountdown(remainingFrom: "3", startUptime: 100))
        coach.stop()

        XCTAssertEqual(events, ["countdown.stop", "session.deactivate"])
    }

    // Catches countdown ownership surviving after its final one-second slot.
    func testScheduledCountdownCompletionStopsPlaybackBeforeDeactivatingAudioSession() {
        var events: [String] = []
        let audioSession = RecordingWorkoutAudioSession()
        audioSession.onSuccessfulNotificationAwareDeactivation = {
            events.append("session.deactivate")
        }
        let synthesizer = RecordingWorkoutSpeechSynthesizer()
        let scheduler = RecordingCountdownAudioScheduler(onStop: {
            events.append("countdown.stop")
        })
        let completionScheduler = RecordingWorkoutCountdownCompletionScheduler()
        let coach = WorkoutAudioCoach(
            synthesizer: synthesizer,
            audioSession: audioSession,
            countdownScheduler: scheduler,
            countdownCompletionScheduler: completionScheduler
        )

        XCTAssertTrue(coach.startCountdown(remainingFrom: "3", startUptime: 100))
        XCTAssertEqual(completionScheduler.scheduledUptime, 103)

        completionScheduler.complete()

        XCTAssertEqual(events, ["countdown.stop", "session.deactivate"])

        XCTAssertTrue(coach.startCountdown(remainingFrom: "3", startUptime: 200))
        XCTAssertEqual(scheduler.startedSequences, [["3", "2", "1"], ["3", "2", "1"]])
    }

    // Catches a rejected late schedule falling back to queued live speech.
    func testRejectedCountdownScheduleStaysSilentAndReleasesAudioSession() {
        let audioSession = RecordingWorkoutAudioSession()
        let synthesizer = RecordingWorkoutSpeechSynthesizer()
        let scheduler = RecordingCountdownAudioScheduler(scheduleResult: false)
        let coach = WorkoutAudioCoach(
            synthesizer: synthesizer,
            audioSession: audioSession,
            countdownScheduler: scheduler
        )

        XCTAssertFalse(coach.startCountdown(remainingFrom: "3", startUptime: 100))
        XCTAssertTrue(synthesizer.utterances.isEmpty)
        XCTAssertEqual(audioSession.deactivationCount, 1)
    }

    func testSpeakDoesNotCallStopBeforeEachCue() {
        let audioSession = RecordingWorkoutAudioSession()
        let synthesizer = RecordingWorkoutSpeechSynthesizer()
        let coach = WorkoutAudioCoach(
            synthesizer: synthesizer,
            audioSession: audioSession
        )

        coach.speak("3")
        coach.speak("2")

        XCTAssertEqual(
            synthesizer.stopCallCount,
            0,
            "WorkoutAudioCoach should not stop the synthesizer before each successive cue."
        )
        XCTAssertEqual(synthesizer.utterances.count, 2)
        XCTAssertEqual(synthesizer.utterances.map(\.speechString), ["3", "2"])
    }

    func testStopStillStopsSynthesizerImmediately() {
        let audioSession = RecordingWorkoutAudioSession()
        let synthesizer = RecordingWorkoutSpeechSynthesizer()
        let coach = WorkoutAudioCoach(
            synthesizer: synthesizer,
            audioSession: audioSession
        )

        coach.stop()

        XCTAssertEqual(
            synthesizer.stopCallCount,
            1,
            "WorkoutAudioCoach.stop() must still stop speech immediately."
        )
    }

    func testStopWaitsForSpeechCancellationBeforeDeactivatingAudioSession() async {
        let audioSession = RecordingWorkoutAudioSession()
        let synthesizer = RecordingWorkoutSpeechSynthesizer()
        let coach = WorkoutAudioCoach(
            synthesizer: synthesizer,
            audioSession: audioSession
        )

        coach.speak("3")
        coach.stop()

        XCTAssertEqual(audioSession.activationCount, 1)
        XCTAssertEqual(audioSession.deactivationCount, 0)

        synthesizer.isSpeaking = false
        synthesizer.sendCancellation()
        await Task.yield()

        XCTAssertEqual(audioSession.deactivationCount, 1)
        XCTAssertTrue(audioSession.didDeactivateWithNotification)
    }

    func testReplacementCueKeepsAudioSessionActiveUntilReplacementFinishes() async {
        let audioSession = RecordingWorkoutAudioSession()
        let synthesizer = RecordingWorkoutSpeechSynthesizer()
        let coach = WorkoutAudioCoach(
            synthesizer: synthesizer,
            audioSession: audioSession
        )
        coach.speak("3")
        coach.speak("2")

        synthesizer.sendCancellation(of: synthesizer.utterances[0])
        await Task.yield()

        XCTAssertEqual(audioSession.activationCount, 1)
        XCTAssertEqual(audioSession.deactivationCount, 0)

        synthesizer.isSpeaking = false
        synthesizer.sendFinish(of: synthesizer.utterances[1])
        await Task.yield()

        XCTAssertEqual(audioSession.deactivationCount, 1)
        XCTAssertTrue(audioSession.didDeactivateWithNotification)

        coach.stop()

        XCTAssertEqual(audioSession.deactivationCount, 1)
        XCTAssertTrue(audioSession.didDeactivateWithNotification)
    }

    func testStaleCallbackFromReplacedCueDoesNotAffectReplacement() async {
        let audioSession = RecordingWorkoutAudioSession()
        let synthesizer = RecordingWorkoutSpeechSynthesizer()
        let coach = WorkoutAudioCoach(
            synthesizer: synthesizer,
            audioSession: audioSession
        )

        coach.speak("3")
        let replacedUtterance = synthesizer.utterances[0]
        coach.speak("2")
        let replacementUtterance = synthesizer.utterances[1]
        synthesizer.sendStart(of: replacementUtterance)

        synthesizer.sendCancellation(of: replacedUtterance)
        await Task.yield()

        XCTAssertTrue(coach.isSpeaking)
        XCTAssertEqual(audioSession.deactivationCount, 0)

        synthesizer.isSpeaking = false
        synthesizer.sendFinish(of: replacementUtterance)
        await Task.yield()

        XCTAssertFalse(coach.isSpeaking)
        XCTAssertEqual(audioSession.deactivationCount, 1)
    }

    func testCueCompletionImmediatelyDeactivatesAudioSessionAndNotifiesOtherApps() async {
        let audioSession = RecordingWorkoutAudioSession()
        let synthesizer = RecordingWorkoutSpeechSynthesizer()
        let coach = WorkoutAudioCoach(
            synthesizer: synthesizer,
            audioSession: audioSession
        )
        coach.speak("3")
        synthesizer.isSpeaking = false
        synthesizer.sendFinish(of: synthesizer.utterances[0])
        await Task.yield()

        XCTAssertEqual(audioSession.deactivationCount, 1)
        XCTAssertTrue(audioSession.didDeactivateWithNotification)
    }

    func testStopOwnsCancellationAndIgnoresLaterCallbacks() async {
        let audioSession = RecordingWorkoutAudioSession()
        let synthesizer = RecordingWorkoutSpeechSynthesizer()
        let coach = WorkoutAudioCoach(
            synthesizer: synthesizer,
            audioSession: audioSession
        )

        coach.speak("3")
        let stoppedUtterance = synthesizer.utterances[0]
        coach.stop()

        XCTAssertEqual(audioSession.deactivationCount, 0)

        synthesizer.isSpeaking = false
        synthesizer.sendCancellation(of: stoppedUtterance)
        await Task.yield()

        XCTAssertEqual(audioSession.deactivationCount, 1)
        XCTAssertFalse(coach.isSpeaking)

        synthesizer.sendFinish(of: stoppedUtterance)
        await Task.yield()

        XCTAssertEqual(audioSession.deactivationCount, 1)
    }

    func testNewCueAfterStopStartsFreshAudioSessionGeneration() async {
        let audioSession = RecordingWorkoutAudioSession()
        let synthesizer = RecordingWorkoutSpeechSynthesizer()
        let coach = WorkoutAudioCoach(
            synthesizer: synthesizer,
            audioSession: audioSession
        )

        coach.speak("3")
        let stoppedUtterance = synthesizer.utterances[0]
        coach.stop()

        coach.speak("2")
        let newUtterance = synthesizer.utterances[1]
        synthesizer.sendStart(of: newUtterance)
        synthesizer.sendCancellation(of: stoppedUtterance)
        await Task.yield()

        XCTAssertEqual(audioSession.activationCount, 1)
        XCTAssertEqual(audioSession.deactivationCount, 0)
        XCTAssertTrue(coach.isSpeaking)

        synthesizer.isSpeaking = false
        synthesizer.sendFinish(of: newUtterance)
        await Task.yield()
        coach.stop()

        XCTAssertEqual(audioSession.deactivationCount, 1)
    }

    func testDeactivationRetriesAfterTransientFailureOnceSpeechHasFinished() async {
        let audioSession = RecordingWorkoutAudioSession(failedDeactivationAttempts: 1)
        let synthesizer = RecordingWorkoutSpeechSynthesizer()
        let coach = WorkoutAudioCoach(
            synthesizer: synthesizer,
            audioSession: audioSession
        )
        let deactivation = expectation(description: "retries deactivation after a transient failure")
        audioSession.onSuccessfulNotificationAwareDeactivation = {
            deactivation.fulfill()
        }

        coach.speak("3")

        synthesizer.isSpeaking = false
        synthesizer.sendFinish(of: synthesizer.utterances[0])
        coach.stop()
        await fulfillment(of: [deactivation], timeout: 1)

        XCTAssertEqual(audioSession.deactivationAttemptCount, 2)
        XCTAssertEqual(audioSession.deactivationCount, 1)
        XCTAssertTrue(audioSession.didDeactivateWithNotification)
    }
}

private final class RecordingCountdownAudioScheduler: CountdownAudioScheduling {
    private let backend = RecordingCountdownAudioSchedulingBackend()
    private lazy var scheduler = CountdownAudioScheduler(backend: backend)
    private(set) var stopCallCount = 0
    private let onStop: () -> Void
    private let scheduleResult: Bool
    private let automaticallyCompletesPrewarm: Bool
    private var prewarmCompletion: ((Bool) -> Void)?

    var startedSequences: [[String]] {
        backend.schedules.map { sequence in
            sequence.schedule.cues.map(\.phrase)
        }
    }

    var startedOffsets: [[TimeInterval]] {
        backend.schedules.map { sequence in
            sequence.schedule.cues.map(\.offset)
        }
    }

    init(
        onStop: @escaping () -> Void = {},
        scheduleResult: Bool = true,
        automaticallyCompletesPrewarm: Bool = true
    ) {
        self.onStop = onStop
        self.scheduleResult = scheduleResult
        self.automaticallyCompletesPrewarm = automaticallyCompletesPrewarm
    }

    func prewarm(completion: @escaping (Bool) -> Void) {
        if automaticallyCompletesPrewarm {
            completion(true)
        } else {
            prewarmCompletion = completion
        }
    }

    func completePrewarm(succeeded: Bool) {
        let completion = prewarmCompletion
        prewarmCompletion = nil
        completion?(succeeded)
    }

    func schedule(_ schedule: CountdownAudioSchedule, startHostTime: UInt64) -> Bool {
        guard scheduleResult else { return false }
        return scheduler.schedule(schedule, startHostTime: startHostTime)
    }

    func stop() {
        stopCallCount += 1
        scheduler.stop()
        onStop()
    }
}

@MainActor
private final class RecordingWorkoutCountdownCompletionScheduler:
    WorkoutCountdownCompletionScheduling
{
    private(set) var scheduledUptime: TimeInterval?
    private var completion: (() -> Void)?

    func schedule(atUptime uptime: TimeInterval, completion: @escaping () -> Void) {
        scheduledUptime = uptime
        self.completion = completion
    }

    func cancel() {
        scheduledUptime = nil
        completion = nil
    }

    func complete() {
        let completion = completion
        cancel()
        completion?()
    }
}

@MainActor
private final class RecordingWorkoutSpeechSynthesizer: WorkoutSpeechSynthesizing {
    var delegate: AVSpeechSynthesizerDelegate?
    var isSpeaking = false
    private(set) var utterances: [AVSpeechUtterance] = []
    private(set) var stopCallCount = 0

    func stopSpeaking(at boundary: AVSpeechBoundary) -> Bool {
        // Cancellation remains in progress until a test delivers its delegate callback.
        stopCallCount += 1
        return true
    }

    func speak(_ utterance: AVSpeechUtterance) {
        utterances.append(utterance)
        isSpeaking = true
    }

    func sendStart(of utterance: AVSpeechUtterance) {
        delegate?.speechSynthesizer?(
            AVSpeechSynthesizer(),
            didStart: utterance
        )
    }

    func sendCancellation(of utterance: AVSpeechUtterance? = nil) {
        delegate?.speechSynthesizer?(
            AVSpeechSynthesizer(),
            didCancel: utterance ?? utterances[0]
        )
    }

    func sendFinish(of utterance: AVSpeechUtterance) {
        delegate?.speechSynthesizer?(AVSpeechSynthesizer(), didFinish: utterance)
    }
}

@MainActor
private final class RecordingWorkoutAudioSession: WorkoutAudioSessionManaging {
    private(set) var configurationCount = 0
    private(set) var activationCount = 0
    private(set) var deactivationAttemptCount = 0
    private(set) var deactivationCount = 0
    private(set) var didDeactivateWithNotification = false
    var onSuccessfulNotificationAwareDeactivation: (() -> Void)?
    private var failedDeactivationAttempts: Int

    init(failedDeactivationAttempts: Int = 0) {
        self.failedDeactivationAttempts = failedDeactivationAttempts
    }

    func configureForSpokenCues() throws {
        configurationCount += 1
    }

    func activate() throws {
        activationCount += 1
    }

    func deactivateAndNotifyOthers() throws {
        deactivationAttemptCount += 1
        guard failedDeactivationAttempts == 0 else {
            failedDeactivationAttempts -= 1
            throw RecordingWorkoutAudioSessionError.deactivationFailed
        }

        deactivationCount += 1
        didDeactivateWithNotification = true
        onSuccessfulNotificationAwareDeactivation?()
    }
}

private enum RecordingWorkoutAudioSessionError: Error {
    case deactivationFailed
}

final class WorkoutSessionPolicyTests: XCTestCase {
    func testDebugCountdownCaptureLeadDoesNotChangeVisibleCountdownDuration() {
        XCTAssertEqual(
            WorkoutSessionPolicy.countdownAudioArmLead(
                environment: ["HANGTEN_REVIEW_COUNTDOWN_CAPTURE": "1"]
            ),
            5
        )
        XCTAssertEqual(WorkoutSessionPolicy.countdownDuration(for: .initial), 3)
        XCTAssertEqual(WorkoutSessionPolicy.countdownDuration(for: .skip), 3)
    }

    // Catches a first start crossing its exact boundary before prewarm resolves.
    func testFirstCountdownWaitsForPrewarmButFailurePreservesVisualCountdown() {
        XCTAssertTrue(
            WorkoutSessionPolicy.shouldDeferCountdownStart(
                isFirstStart: true,
                preparationState: .preparing
            )
        )
        XCTAssertFalse(
            WorkoutSessionPolicy.shouldDeferCountdownStart(
                isFirstStart: true,
                preparationState: .ready
            )
        )
        XCTAssertFalse(
            WorkoutSessionPolicy.shouldDeferCountdownStart(
                isFirstStart: true,
                preparationState: .failed
            )
        )
        XCTAssertTrue(
            WorkoutSessionPolicy.shouldDeferCountdownStart(
                isFirstStart: false,
                preparationState: .preparing
            )
        )
    }

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

    @MainActor
    func testRoutePrearmsThreeSecondSegmentWithoutInterruptingOrDuplicatingPrecedingCountdown() {
        let scheduler = RecordingCountdownAudioScheduler()
        let completionScheduler = RecordingWorkoutCountdownCompletionScheduler()
        let coach = WorkoutAudioCoach(
            synthesizer: RecordingWorkoutSpeechSynthesizer(),
            audioSession: RecordingWorkoutAudioSession(),
            countdownScheduler: scheduler,
            countdownCompletionScheduler: completionScheduler
        )
        let startUptime = ProcessInfo.processInfo.systemUptime + 10
        let routeSteps = [
            WorkoutStep(
                id: "preceding",
                number: 1,
                title: "Preceding",
                instruction: "",
                accessory: "",
                duration: 10,
                phase: .hang,
                targets: []
            ),
            WorkoutStep(
                id: "short",
                number: 2,
                title: "Short",
                instruction: "",
                accessory: "",
                duration: 3,
                phase: .hang,
                targets: []
            ),
            WorkoutStep(
                id: "following",
                number: 3,
                title: "Following",
                instruction: "",
                accessory: "",
                duration: 10,
                phase: .rest,
                targets: []
            )
        ]
        let followingShortDurations = WorkoutCountdownIntervalPolicy.shortDurations(
            in: routeSteps,
            startingAt: 10
        )
        XCTAssertEqual(followingShortDurations, [3])
        let precedingMoment = WorkoutAudioCuePolicy.scheduledMoment(
            stepID: "preceding",
            segmentName: "active",
            initialCountdown: 0,
            intervalSecondsRemaining: 4,
            intervalDuration: 10,
            followingShortSegmentDurations: followingShortDurations,
            isComplete: false
        )
        let action = WorkoutAudioCuePolicy.action(
            previous: nil,
            current: precedingMoment,
            countdownStartUptime: startUptime
        )

        XCTAssertTrue(WorkoutAudioCueRouter.route(action, to: coach))
        XCTAssertEqual(scheduler.startedSequences, [["3", "2", "1", "3", "2", "1"]])
        XCTAssertEqual(scheduler.startedOffsets, [[0, 1, 2, 3, 4, 5]])
        XCTAssertEqual(scheduler.stopCallCount, 0)
        XCTAssertEqual(completionScheduler.scheduledUptime, startUptime + 6)

        let shortSegmentMoment = WorkoutAudioCuePolicy.scheduledMoment(
            stepID: "short",
            segmentName: "active",
            initialCountdown: 0,
            intervalSecondsRemaining: 3,
            intervalDuration: 3,
            followingShortSegmentDurations: [],
            isComplete: false
        )
        XCTAssertNil(shortSegmentMoment)
        XCTAssertFalse(
            WorkoutAudioCueRouter.route(
                WorkoutAudioCuePolicy.action(
                    previous: precedingMoment,
                    current: shortSegmentMoment,
                    countdownStartUptime: startUptime + 3
                ),
                to: coach
            )
        )
        XCTAssertEqual(scheduler.startedSequences.count, 1)
        XCTAssertEqual(scheduler.stopCallCount, 0)
    }

    func testMissingAudioMomentLeavesInFlightCueUntouched() {
        XCTAssertEqual(
            WorkoutAudioCuePolicy.action(
                previous: nil,
                current: nil,
                countdownStartUptime: nil
            ),
            .none
        )
    }

    func testNonnumericAudioMomentKeepsLiveSpeechRouting() {
        let moment = WorkoutAudioMoment(key: "step-start", phrase: "Begin minute one")

        XCTAssertEqual(
            WorkoutAudioCuePolicy.action(
                previous: nil,
                current: moment,
                countdownStartUptime: nil
            ),
            .speak(moment)
        )
    }

    // Catches an initial countdown being routed as three independent live-speech calls.
    func testInitialThreeStartsOneSchedulerOwnedSequence() {
        let three = WorkoutAudioMoment(key: "initial-3", phrase: "3")

        XCTAssertEqual(
            WorkoutAudioCuePolicy.action(
                previous: nil,
                current: three,
                countdownStartUptime: 100
            ),
            .startCountdown(
                schedule: CountdownAudioSchedule(remainingFrom: "3"),
                startUptime: 100
            )
        )
        assertLaterCountdownTicksHaveNoIndependentAction(
            three: three,
            two: WorkoutAudioMoment(key: "initial-2", phrase: "2"),
            one: WorkoutAudioMoment(key: "initial-1", phrase: "1")
        )
    }

    // Catches a skip countdown bypassing the scheduler-owned sequence route.
    func testSkipThreeStartsOneSchedulerOwnedSequence() {
        let three = WorkoutAudioMoment(key: "skip-3", phrase: "3")

        XCTAssertEqual(
            WorkoutAudioCuePolicy.action(
                previous: nil,
                current: three,
                countdownStartUptime: 200
            ),
            .startCountdown(
                schedule: CountdownAudioSchedule(remainingFrom: "3"),
                startUptime: 200
            )
        )
        assertLaterCountdownTicksHaveNoIndependentAction(
            three: three,
            two: WorkoutAudioMoment(key: "skip-2", phrase: "2"),
            one: WorkoutAudioMoment(key: "skip-1", phrase: "1")
        )
    }

    // Catches a fixed segment's final three seconds being sent to live speech.
    func testFinalSegmentThreeStartsOneSchedulerOwnedSequence() {
        let three = WorkoutAudioMoment(key: "\(stepID)-active-3", phrase: "3")

        XCTAssertEqual(
            WorkoutAudioCuePolicy.action(
                previous: nil,
                current: three,
                countdownStartUptime: 300
            ),
            .startCountdown(
                schedule: CountdownAudioSchedule(remainingFrom: "3"),
                startUptime: 300
            )
        )
        assertLaterCountdownTicksHaveNoIndependentAction(
            three: three,
            two: WorkoutAudioMoment(key: "\(stepID)-active-2", phrase: "2"),
            one: WorkoutAudioMoment(key: "\(stepID)-active-1", phrase: "1")
        )
    }

    // Catches delayed first delivery dropping the complete remaining numeric sequence.
    func testLaterNumberStartsRemainingSequenceWhenNoEarlierMomentWasDelivered() {
        XCTAssertEqual(
            WorkoutAudioCuePolicy.action(
                previous: nil,
                current: WorkoutAudioMoment(key: "initial-2", phrase: "2"),
                countdownStartUptime: 101
            ),
            .startCountdown(
                schedule: CountdownAudioSchedule(remainingFrom: "2"),
                startUptime: 101
            )
        )
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

    func testFixedSegmentArmsThreeAtThePrecedingFourSecondTick() {
        XCTAssertEqual(
            WorkoutAudioCuePolicy.scheduledMoment(
                stepID: stepID,
                segmentName: "active",
                initialCountdown: 0,
                intervalSecondsRemaining: 4,
                isComplete: false
            ),
            WorkoutAudioMoment(
                key: "\(stepID)-active-3",
                phrase: "3",
                countdownSchedule: CountdownAudioSchedule(remainingFrom: "3")
            )
        )
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

    func testCompletionDuringInitialCountdownLeavesInFlightCueUntouched() {
        XCTAssertEqual(
            WorkoutAudioCuePolicy.action(
                previous: nil,
                current: WorkoutAudioCuePolicy.moment(
                    stepID: stepID,
                    segmentName: "active",
                    initialCountdown: 3,
                    intervalSecondsRemaining: 60,
                    isComplete: true
                ),
                countdownStartUptime: 100
            ),
            .none
        )
    }

    func testCompletionDuringSkipCountdownLeavesInFlightCueUntouched() {
        XCTAssertEqual(
            WorkoutAudioCuePolicy.action(
                previous: nil,
                current: WorkoutAudioCuePolicy.moment(
                    stepID: stepID,
                    segmentName: "active",
                    initialCountdown: 2,
                    intervalSecondsRemaining: 60,
                    isComplete: true,
                    countdownKind: .skip
                ),
                countdownStartUptime: 100
            ),
            .none
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

    private func assertLaterCountdownTicksHaveNoIndependentAction(
        three: WorkoutAudioMoment,
        two: WorkoutAudioMoment,
        one: WorkoutAudioMoment,
        file: StaticString = #filePath,
        line: UInt = #line
    ) {
        XCTAssertEqual(
            WorkoutAudioCuePolicy.action(
                previous: three,
                current: two,
                countdownStartUptime: 101
            ),
            .none,
            file: file,
            line: line
        )
        XCTAssertEqual(
            WorkoutAudioCuePolicy.action(
                previous: two,
                current: one,
                countdownStartUptime: 102
            ),
            .none,
            file: file,
            line: line
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

    func testPreparedInitialCountdownBeginsAtArmBoundaryAndRemainsExactlyThreeSeconds() {
        let armedAt: TimeInterval = 100.1
        let wallClockArm = Date(timeIntervalSinceReferenceDate: 3_000.1)
        var state = WorkoutSessionState()

        XCTAssertNil(state.activeStartUptime)
        state.toggleRunning(uptime: armedAt, now: wallClockArm)

        XCTAssertEqual(state.countdownRemaining(at: armedAt), 3)
        XCTAssertEqual(state.countdownRemaining(at: armedAt + 2.999), 1)
        XCTAssertEqual(state.countdownRemaining(at: armedAt + 3), 0)
        XCTAssertEqual(state.activeStartUptime, armedAt + 3)
    }

    func testPreparedSkipCountdownBeginsAtArmBoundaryAndRemainsExactlyThreeSeconds() {
        let armedAt: TimeInterval = 200.1
        var state = WorkoutSessionState(
            activeStartUptime: 190,
            pausedElapsed: 0,
            routineStartedAt: Date(timeIntervalSinceReferenceDate: 2_900)
        )

        state.startSkipCountdown(to: 60, at: armedAt)

        XCTAssertEqual(state.countdownRemaining(at: armedAt), 3)
        XCTAssertEqual(state.countdownRemaining(at: armedAt + 3), 0)
        XCTAssertEqual(state.activeStartUptime, armedAt + 3)
    }

    func testRunningSkipIntoRestTransitionsImmediatelyAndKeepsRunning() {
        let now: TimeInterval = 100
        let timeline = WorkoutTimeline(steps: steps)
        var state = WorkoutSessionState(
            activeStartUptime: now - 10,
            pausedElapsed: 10,
            routineStartedAt: Date(timeIntervalSinceReferenceDate: 2_980)
        )

        XCTAssertTrue(state.skipCurrentStep(timeline: timeline, planDuration: timeline.duration, at: now))

        XCTAssertNil(state.countdownKind)
        XCTAssertEqual(state.activeStartUptime, now)
        XCTAssertEqual(state.pausedElapsed, 60)
        XCTAssertEqual(state.currentElapsed(planDuration: timeline.duration, at: now), 60)
        XCTAssertEqual(state.currentElapsed(planDuration: timeline.duration, at: now + 1), 61)
    }

    func testPausedSkipIntoRestTransitionsImmediatelyAndKeepsPaused() {
        let now: TimeInterval = 100
        let timeline = WorkoutTimeline(steps: steps)
        var state = WorkoutSessionState(
            activeStartUptime: nil,
            pausedElapsed: 10,
            routineStartedAt: Date(timeIntervalSinceReferenceDate: 2_980)
        )

        XCTAssertTrue(state.skipCurrentStep(timeline: timeline, planDuration: timeline.duration, at: now))

        XCTAssertNil(state.countdownKind)
        XCTAssertNil(state.activeStartUptime)
        XCTAssertEqual(state.pausedElapsed, 60)
        XCTAssertEqual(state.currentElapsed(planDuration: timeline.duration, at: now + 10), 60)
    }

    func testPausedSessionSkipCountsDownThenExplicitExpiryStartsRunningDestination() {
        let now: TimeInterval = 100
        let timeline = WorkoutTimeline(steps: steps)
        var state = WorkoutSessionState(
            activeStartUptime: nil,
            pausedElapsed: 65,
            routineStartedAt: Date(timeIntervalSinceReferenceDate: 2_980)
        )

        XCTAssertTrue(state.skipCurrentStep(timeline: timeline, planDuration: timeline.duration, at: now))
        XCTAssertEqual(state.pausedElapsed, 80)
        XCTAssertEqual(state.countdownKind, .skip)
        XCTAssertEqual(state.countdownRemaining(at: now), 3)
        XCTAssertFalse(state.canNavigate(planDuration: timeline.duration, at: now))

        let countdownStart = now + 3
        XCTAssertEqual(state.countdownRemaining(at: countdownStart), 0)
        XCTAssertEqual(state.countdownKind, .skip)
        state.transitionExpiredCountdown(at: countdownStart)
        XCTAssertNil(state.countdownKind)
        XCTAssertEqual(state.activeStartUptime, countdownStart)
        XCTAssertEqual(state.currentElapsed(planDuration: timeline.duration, at: countdownStart), 80)
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
            activeStartUptime: now - 65,
            pausedElapsed: 0,
            routineStartedAt: Date(timeIntervalSinceReferenceDate: 2_980)
        )

        XCTAssertTrue(state.skipCurrentStep(timeline: timeline, planDuration: timeline.duration, at: now))
        state.cancelCountdown(at: now + 2)

        XCTAssertNil(state.activeStartUptime)
        XCTAssertNil(state.countdownKind)
        XCTAssertEqual(state.pausedElapsed, 80)
        XCTAssertEqual(state.routineStartedAt, Date(timeIntervalSinceReferenceDate: 2_980))
    }

    func testInterruptionDuringSkipCountdownKeepsDestinationPaused() {
        let now: TimeInterval = 100
        let timeline = WorkoutTimeline(steps: steps)
        var state = WorkoutSessionState(
            activeStartUptime: now - 65,
            pausedElapsed: 0,
            routineStartedAt: Date(timeIntervalSinceReferenceDate: 2_980)
        )

        XCTAssertTrue(state.skipCurrentStep(timeline: timeline, planDuration: timeline.duration, at: now))
        state.pauseForInterruption(at: now + 2)

        XCTAssertNil(state.activeStartUptime)
        XCTAssertNil(state.countdownKind)
        XCTAssertEqual(state.pausedElapsed, 80)
        XCTAssertEqual(state.routineStartedAt, Date(timeIntervalSinceReferenceDate: 2_980))
    }

    func testDirectSeekClearsPendingSkipCountdownAndPreservesRunning() {
        let now: TimeInterval = 100
        let timeline = WorkoutTimeline(steps: steps)
        var state = WorkoutSessionState(
            activeStartUptime: now - 65,
            pausedElapsed: 0,
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
