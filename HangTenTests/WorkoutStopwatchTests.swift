import XCTest
@testable import HangTen

final class WorkoutStopwatchTests: XCTestCase {
    func testNeverStartedStopwatchHasNilElapsed() {
        let stopwatch = WorkoutStopwatch()

        XCTAssertNil(stopwatch.elapsed(at: 100))
        XCTAssertFalse(stopwatch.hasStarted)
        XCTAssertFalse(stopwatch.isRunning)
        XCTAssertFalse(stopwatch.isFinalized)
    }

    func testStartMeasuresElapsedFromAnchor() {
        var stopwatch = WorkoutStopwatch()

        stopwatch.start(at: 10)

        XCTAssertEqual(stopwatch.elapsed(at: 16), 6)
        XCTAssertTrue(stopwatch.hasStarted)
        XCTAssertTrue(stopwatch.isRunning)
        XCTAssertFalse(stopwatch.isFinalized)
    }

    func testPauseAccumulatesElapsedAndStopsRunning() {
        var stopwatch = WorkoutStopwatch()
        stopwatch.start(at: 10)

        stopwatch.pause(at: 16)

        XCTAssertEqual(stopwatch.elapsed(at: 100), 6)
        XCTAssertFalse(stopwatch.isRunning)
    }

    func testResumeAddsNewActiveInterval() {
        var stopwatch = WorkoutStopwatch()
        stopwatch.start(at: 10)
        stopwatch.pause(at: 16)

        stopwatch.start(at: 30)

        XCTAssertEqual(stopwatch.elapsed(at: 34), 10)
        XCTAssertTrue(stopwatch.isRunning)
    }

    func testStopFinalizesElapsedTime() {
        var stopwatch = WorkoutStopwatch()
        stopwatch.start(at: 10)

        stopwatch.stop(at: 16)

        XCTAssertEqual(stopwatch.elapsed(at: 100), 6)
        XCTAssertFalse(stopwatch.isRunning)
        XCTAssertTrue(stopwatch.isFinalized)
    }

    func testRepeatedStopPreservesFinalizedElapsedTime() {
        var stopwatch = WorkoutStopwatch()
        stopwatch.start(at: 10)
        stopwatch.stop(at: 16)

        stopwatch.stop(at: 100)

        XCTAssertEqual(stopwatch.elapsed(at: 200), 6)
        XCTAssertTrue(stopwatch.isFinalized)
    }

    func testFinalizedStopwatchCannotRestart() {
        var stopwatch = WorkoutStopwatch()
        stopwatch.start(at: 10)
        stopwatch.stop(at: 16)

        stopwatch.start(at: 30)

        XCTAssertEqual(stopwatch.elapsed(at: 100), 6)
        XCTAssertFalse(stopwatch.isRunning)
        XCTAssertTrue(stopwatch.isFinalized)
    }

    func testClockMovingBackwardsContributesZeroElapsedTime() {
        var stopwatch = WorkoutStopwatch()
        stopwatch.start(at: 10)

        XCTAssertEqual(stopwatch.elapsed(at: 5), 0)

        stopwatch.pause(at: 5)

        XCTAssertEqual(stopwatch.elapsed(at: 100), 0)
    }

    func testSafeNoOpCallsPreserveState() {
        var stopwatch = WorkoutStopwatch()

        stopwatch.pause(at: 10)
        stopwatch.start(at: 10)
        stopwatch.start(at: 20)
        stopwatch.pause(at: 16)
        stopwatch.pause(at: 100)

        XCTAssertEqual(stopwatch.elapsed(at: 200), 6)
        XCTAssertTrue(stopwatch.hasStarted)
        XCTAssertFalse(stopwatch.isRunning)

        stopwatch.stop(at: 200)
        stopwatch.pause(at: 300)

        XCTAssertEqual(stopwatch.elapsed(at: 400), 6)
        XCTAssertTrue(stopwatch.isFinalized)
    }

    func testNeverStartedStopwatchCanBeFinalizedWithoutElapsedTime() {
        var stopwatch = WorkoutStopwatch()

        stopwatch.stop(at: 10)

        XCTAssertNil(stopwatch.elapsed(at: 100))
        XCTAssertFalse(stopwatch.hasStarted)
        XCTAssertTrue(stopwatch.isFinalized)
    }

    func testAutomaticStepBoundaryFinalizesAllPreviousStepStopwatchesAtBoundary() throws {
        let steps = [
            WorkoutStep(
                id: "first",
                number: 1,
                title: "First",
                instruction: "First instruction",
                accessory: "",
                duration: 10,
                phase: .hang,
                targets: [.kind(.jug)],
                segments: [
                    WorkoutSegment(kind: .work, target: .kind(.jug), timing: .stopwatch, duration: nil),
                    WorkoutSegment(kind: .work, target: .kind(.jug), timing: .stopwatch, duration: nil)
                ]
            ),
            WorkoutStep(
                id: "second",
                number: 2,
                title: "Second",
                instruction: "Second instruction",
                accessory: "",
                duration: 10,
                phase: .hang,
                targets: [.kind(.jug)],
                segments: [
                    WorkoutSegment(kind: .work, target: .kind(.jug), timing: .stopwatch, duration: nil)
                ]
            )
        ]
        let timeline = WorkoutTimeline(steps: steps)
        let transitionElapsed = try XCTUnwrap(timeline.startOffset(for: "second"))
        let previousStep = try XCTUnwrap(timeline.step(at: transitionElapsed - 0.001))
        let nextStep = try XCTUnwrap(timeline.step(at: transitionElapsed))
        let transitionTime = 100 + transitionElapsed
        let laterTime: TimeInterval = 200

        XCTAssertEqual(previousStep.id, "first")
        XCTAssertEqual(nextStep.id, "second")

        let firstKey = WorkoutActivitySegmentKey(stepID: previousStep.id, segmentIndex: 0)
        let secondKey = WorkoutActivitySegmentKey(stepID: previousStep.id, segmentIndex: 1)
        let laterKey = WorkoutActivitySegmentKey(stepID: nextStep.id, segmentIndex: 0)
        var firstStopwatch = WorkoutStopwatch()
        firstStopwatch.start(at: 103)
        var secondStopwatch = WorkoutStopwatch()
        secondStopwatch.start(at: 105)
        var laterStopwatch = WorkoutStopwatch()
        laterStopwatch.start(at: transitionTime)
        var stopwatches = [
            firstKey: firstStopwatch,
            secondKey: secondStopwatch,
            laterKey: laterStopwatch
        ]

        WorkoutStopwatchLifecycle.finalizeStopwatches(for: previousStep.id, at: transitionTime, in: &stopwatches)

        XCTAssertEqual(stopwatches[firstKey]?.elapsed(at: laterTime), 7)
        XCTAssertEqual(stopwatches[secondKey]?.elapsed(at: laterTime), 5)
        XCTAssertTrue(stopwatches[firstKey]?.isFinalized == true)
        XCTAssertTrue(stopwatches[secondKey]?.isFinalized == true)
        XCTAssertTrue(stopwatches[laterKey]?.isRunning == true)
        XCTAssertFalse(stopwatches[laterKey]?.isFinalized == true)
    }

    func testNonUniformMonotonicSamplesAccumulateAcrossPauseAndResume() throws {
        var stopwatch = WorkoutStopwatch()

        stopwatch.start(at: 100)
        XCTAssertEqual(try XCTUnwrap(stopwatch.elapsed(at: 100.4)), 0.4, accuracy: 0.000_1)

        stopwatch.pause(at: 101.7)
        stopwatch.start(at: 130)
        XCTAssertEqual(try XCTUnwrap(stopwatch.elapsed(at: 130.25)), 1.95, accuracy: 0.000_1)

        stopwatch.stop(at: 132.6)
        XCTAssertEqual(try XCTUnwrap(stopwatch.elapsed(at: 200)), 4.3, accuracy: 0.000_1)
    }

    func testFinalizeAndSnapshotAllStopwatchesRecordsObservedDurations() throws {
        let firstKey = WorkoutActivitySegmentKey(stepID: "first", segmentIndex: 0)
        let secondKey = WorkoutActivitySegmentKey(stepID: "second", segmentIndex: 0)
        let neverStartedKey = WorkoutActivitySegmentKey(stepID: "second", segmentIndex: 1)
        var firstStopwatch = WorkoutStopwatch()
        firstStopwatch.start(at: 100)
        firstStopwatch.pause(at: 106)
        var secondStopwatch = WorkoutStopwatch()
        secondStopwatch.start(at: 110)
        var stopwatches = [
            firstKey: firstStopwatch,
            secondKey: secondStopwatch,
            neverStartedKey: WorkoutStopwatch()
        ]

        let durations = WorkoutStopwatchLifecycle.finalizeAndSnapshotStopwatches(
            at: 120,
            in: &stopwatches
        )

        XCTAssertEqual(durations[firstKey], 6)
        XCTAssertEqual(durations[secondKey], 10)
        XCTAssertNil(durations[neverStartedKey])
        XCTAssertTrue(stopwatches[firstKey]?.isFinalized == true)
        XCTAssertTrue(stopwatches[secondKey]?.isFinalized == true)
        XCTAssertTrue(stopwatches[neverStartedKey]?.isFinalized == true)
    }
}
