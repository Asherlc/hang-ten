import XCTest
@testable import HangTen

final class MotherboardWorkoutRecorderTests: XCTestCase {
    private func measurement(load: Double, at time: TimeInterval) -> MotherboardMeasurement {
        MotherboardMeasurement(
            timestamp: Date(timeIntervalSince1970: time),
            sampleNumber: UInt16(time),
            batteryValue: 90,
            sensorLoadsKGF: [load, 0, 0, 0],
            aggregateLoadKGF: load
        )
    }

    func testLoadedIntervalsUseMeasurementTimesWithoutChangingScheduledDuration() {
        var recorder = MotherboardWorkoutRecorder(configuration: .init(thresholdKGF: 2.5, releaseRatio: 0.8, debounceDuration: 0, mergeGapDuration: 0))
        recorder.consume(measurement(load: 3, at: 1), stepID: "step", plannedActiveDuration: 7, workoutElapsed: 1, isActive: true)
        recorder.consume(measurement(load: 3, at: 6), stepID: "step", plannedActiveDuration: 7, workoutElapsed: 6, isActive: true)
        recorder.consume(measurement(load: 0, at: 7), stepID: "step", plannedActiveDuration: 7, workoutElapsed: 7, isActive: true)

        let result = recorder.finish(at: 7)
        XCTAssertEqual(result[0].plannedActiveDuration, 7)
        XCTAssertEqual(result[0].intervals, [LoadInterval(start: 1, end: 7)])
        XCTAssertEqual(result[0].intervals[0].duration, 6, accuracy: 0.0001)
        XCTAssertEqual(result[0].peakLoadKGF ?? -1, 3, accuracy: 0.0001)
    }

    func testRestSamplesDoNotCreateIntervalsAndDisconnectMarksLaterStepInterrupted() {
        var recorder = MotherboardWorkoutRecorder(configuration: .init(thresholdKGF: 2.5, releaseRatio: 0.8, debounceDuration: 0, mergeGapDuration: 0))
        recorder.consume(measurement(load: 10, at: 1), stepID: "hang", plannedActiveDuration: 5, workoutElapsed: 1, isActive: true)
        recorder.endStep(stepID: "hang", at: 2)
        recorder.consume(measurement(load: 10, at: 3), stepID: "rest", plannedActiveDuration: 5, workoutElapsed: 3, isActive: false)
        recorder.interrupt(at: 4)

        let result = recorder.finish(at: 4)
        XCTAssertEqual(result.count, 2)
        XCTAssertEqual(result[0].status, .measured)
        XCTAssertEqual(result[1].status, .interrupted)
        XCTAssertTrue(result[1].intervals.isEmpty)
    }

    func testFinishKeepsRestOnlyStepUnmeasured() {
        var recorder = MotherboardWorkoutRecorder()
        recorder.consume(measurement(load: 10, at: 3), stepID: "rest", plannedActiveDuration: 5, workoutElapsed: 3, isActive: false)

        let result = recorder.finish(at: 5)
        XCTAssertEqual(result[0].status, .unmeasured)
        XCTAssertTrue(result[0].intervals.isEmpty)
        XCTAssertEqual(result[0].sampleCount, 0)
    }

    func testDebounceUsesReleaseHysteresisAndTracksActiveSamples() {
        var recorder = MotherboardWorkoutRecorder(configuration: .init(thresholdKGF: 5, releaseRatio: 0.8, debounceDuration: 1, mergeGapDuration: 0))
        recorder.consume(measurement(load: 5, at: 1), stepID: "step", plannedActiveDuration: 10, workoutElapsed: 1, isActive: true)
        recorder.consume(measurement(load: 6, at: 2), stepID: "step", plannedActiveDuration: 10, workoutElapsed: 2, isActive: true)
        recorder.consume(measurement(load: 4.5, at: 3), stepID: "step", plannedActiveDuration: 10, workoutElapsed: 3, isActive: true)
        recorder.consume(measurement(load: 3, at: 4), stepID: "step", plannedActiveDuration: 10, workoutElapsed: 4, isActive: true)
        recorder.consume(measurement(load: 3, at: 5), stepID: "step", plannedActiveDuration: 10, workoutElapsed: 5, isActive: true)

        let result = recorder.finish(at: 5)[0]
        XCTAssertEqual(result.intervals, [LoadInterval(start: 1, end: 4)])
        XCTAssertEqual(result.peakLoadKGF ?? -1, 6, accuracy: 0.0001)
        XCTAssertEqual(result.sampleCount, 5)
    }

    func testShortGapsMergeAndEndStepClipsToPlannedTimerBoundary() {
        var recorder = MotherboardWorkoutRecorder(configuration: .init(thresholdKGF: 2.5, releaseRatio: 0.8, debounceDuration: 0, mergeGapDuration: 2))
        recorder.consume(measurement(load: 3, at: 10), stepID: "step", plannedActiveDuration: 5, workoutElapsed: 10, isActive: true)
        recorder.consume(measurement(load: 0, at: 11), stepID: "step", plannedActiveDuration: 5, workoutElapsed: 11, isActive: true)
        recorder.consume(measurement(load: 3, at: 12), stepID: "step", plannedActiveDuration: 5, workoutElapsed: 12, isActive: true)
        recorder.endStep(stepID: "step", at: 20)

        let result = recorder.finish(at: 20)[0]
        XCTAssertEqual(result.intervals, [LoadInterval(start: 10, end: 15)])
        XCTAssertEqual(result.status, .measured)
    }
}
