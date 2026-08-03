import XCTest
@testable import HangTen

final class WorkoutStopwatchTests: XCTestCase {
    func testNeverStartedStopwatchHasNilElapsed() {
        let stopwatch = WorkoutStopwatch()

        XCTAssertNil(stopwatch.elapsed(at: date(100)))
        XCTAssertFalse(stopwatch.hasStarted)
        XCTAssertFalse(stopwatch.isRunning)
        XCTAssertFalse(stopwatch.isFinalized)
    }

    func testStartMeasuresElapsedFromAnchor() {
        var stopwatch = WorkoutStopwatch()

        stopwatch.start(at: date(10))

        XCTAssertEqual(stopwatch.elapsed(at: date(16)), 6)
        XCTAssertTrue(stopwatch.hasStarted)
        XCTAssertTrue(stopwatch.isRunning)
        XCTAssertFalse(stopwatch.isFinalized)
    }

    func testPauseAccumulatesElapsedAndStopsRunning() {
        var stopwatch = WorkoutStopwatch()
        stopwatch.start(at: date(10))

        stopwatch.pause(at: date(16))

        XCTAssertEqual(stopwatch.elapsed(at: date(100)), 6)
        XCTAssertFalse(stopwatch.isRunning)
    }

    func testResumeAddsNewActiveInterval() {
        var stopwatch = WorkoutStopwatch()
        stopwatch.start(at: date(10))
        stopwatch.pause(at: date(16))

        stopwatch.start(at: date(30))

        XCTAssertEqual(stopwatch.elapsed(at: date(34)), 10)
        XCTAssertTrue(stopwatch.isRunning)
    }

    func testStopFinalizesElapsedTime() {
        var stopwatch = WorkoutStopwatch()
        stopwatch.start(at: date(10))

        stopwatch.stop(at: date(16))

        XCTAssertEqual(stopwatch.elapsed(at: date(100)), 6)
        XCTAssertFalse(stopwatch.isRunning)
        XCTAssertTrue(stopwatch.isFinalized)
    }

    func testRepeatedStopPreservesFinalizedElapsedTime() {
        var stopwatch = WorkoutStopwatch()
        stopwatch.start(at: date(10))
        stopwatch.stop(at: date(16))

        stopwatch.stop(at: date(100))

        XCTAssertEqual(stopwatch.elapsed(at: date(200)), 6)
        XCTAssertTrue(stopwatch.isFinalized)
    }

    func testFinalizedStopwatchCannotRestart() {
        var stopwatch = WorkoutStopwatch()
        stopwatch.start(at: date(10))
        stopwatch.stop(at: date(16))

        stopwatch.start(at: date(30))

        XCTAssertEqual(stopwatch.elapsed(at: date(100)), 6)
        XCTAssertFalse(stopwatch.isRunning)
        XCTAssertTrue(stopwatch.isFinalized)
    }

    func testClockMovingBackwardsContributesZeroElapsedTime() {
        var stopwatch = WorkoutStopwatch()
        stopwatch.start(at: date(10))

        XCTAssertEqual(stopwatch.elapsed(at: date(5)), 0)

        stopwatch.pause(at: date(5))

        XCTAssertEqual(stopwatch.elapsed(at: date(100)), 0)
    }

    func testSafeNoOpCallsPreserveState() {
        var stopwatch = WorkoutStopwatch()

        stopwatch.pause(at: date(10))
        stopwatch.start(at: date(10))
        stopwatch.start(at: date(20))
        stopwatch.pause(at: date(16))
        stopwatch.pause(at: date(100))

        XCTAssertEqual(stopwatch.elapsed(at: date(200)), 6)
        XCTAssertTrue(stopwatch.hasStarted)
        XCTAssertFalse(stopwatch.isRunning)

        stopwatch.stop(at: date(200))
        stopwatch.pause(at: date(300))

        XCTAssertEqual(stopwatch.elapsed(at: date(400)), 6)
        XCTAssertTrue(stopwatch.isFinalized)
    }

    func testNeverStartedStopwatchCanBeFinalizedWithoutElapsedTime() {
        var stopwatch = WorkoutStopwatch()

        stopwatch.stop(at: date(10))

        XCTAssertNil(stopwatch.elapsed(at: date(100)))
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
        let transitionDate = date(100 + transitionElapsed)
        let laterDate = date(200)

        XCTAssertEqual(previousStep.id, "first")
        XCTAssertEqual(nextStep.id, "second")

        let firstKey = WorkoutActivitySegmentKey(stepID: previousStep.id, segmentIndex: 0)
        let secondKey = WorkoutActivitySegmentKey(stepID: previousStep.id, segmentIndex: 1)
        let laterKey = WorkoutActivitySegmentKey(stepID: nextStep.id, segmentIndex: 0)
        var firstStopwatch = WorkoutStopwatch()
        firstStopwatch.start(at: date(103))
        var secondStopwatch = WorkoutStopwatch()
        secondStopwatch.start(at: date(105))
        var laterStopwatch = WorkoutStopwatch()
        laterStopwatch.start(at: transitionDate)
        var stopwatches = [
            firstKey: firstStopwatch,
            secondKey: secondStopwatch,
            laterKey: laterStopwatch
        ]

        WorkoutStopwatchLifecycle.finalizeStopwatches(for: previousStep.id, at: transitionDate, in: &stopwatches)

        XCTAssertEqual(stopwatches[firstKey]?.elapsed(at: laterDate), 7)
        XCTAssertEqual(stopwatches[secondKey]?.elapsed(at: laterDate), 5)
        XCTAssertTrue(stopwatches[firstKey]?.isFinalized == true)
        XCTAssertTrue(stopwatches[secondKey]?.isFinalized == true)
        XCTAssertTrue(stopwatches[laterKey]?.isRunning == true)
        XCTAssertFalse(stopwatches[laterKey]?.isFinalized == true)
    }

    private func date(_ seconds: TimeInterval) -> Date {
        Date(timeIntervalSinceReferenceDate: seconds)
    }
}
