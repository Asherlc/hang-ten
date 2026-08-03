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

    private func date(_ seconds: TimeInterval) -> Date {
        Date(timeIntervalSinceReferenceDate: seconds)
    }
}
