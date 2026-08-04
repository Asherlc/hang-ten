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

        XCTAssertEqual(rest.activeDuration, 0)
        XCTAssertTrue(rest.hasRestInterval)
        XCTAssertEqual(rest.restDuration, 30)
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
