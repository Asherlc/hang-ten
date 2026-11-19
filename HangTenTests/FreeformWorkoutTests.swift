import XCTest
@testable import HangTen

final class FreeformWorkoutTests: XCTestCase {
    private let origin = Date(timeIntervalSince1970: 0)

    // MARK: - Depth validation

    func testDepthValidationAcceptsDotAndCommaDecimals() {
        XCTAssertEqual(FreeformWorkout.normalizedDepth(from: "18.5"), 18.5)
        XCTAssertEqual(FreeformWorkout.normalizedDepth(from: "18,5"), 18.5)
        XCTAssertEqual(FreeformWorkout.normalizedDepth(from: "  20 "), 20)
        XCTAssertNil(FreeformWorkout.normalizedDepth(from: ""))
        XCTAssertNil(FreeformWorkout.normalizedDepth(from: "   "))
        XCTAssertNil(FreeformWorkout.normalizedDepth(from: "0"))
        XCTAssertNil(FreeformWorkout.normalizedDepth(from: "-3"))
        XCTAssertNil(FreeformWorkout.normalizedDepth(from: "abc"))
    }

    // MARK: - Detection

    func testDistinctEffortsCarryDistinctPeaksAndDurations() {
        var workout = newWorkout(streamGapTimeout: 10)
        start(workout: &workout, depth: 18)

        receive(&workout, load: 10, at: 1)
        receive(&workout, load: 12, at: 2)
        receive(&workout, load: 0, at: 3)
        receive(&workout, load: 14, at: 5)
        receive(&workout, load: 0, at: 6)

        let efforts = workout.efforts
        XCTAssertEqual(efforts.count, 2)
        XCTAssertEqual(efforts[0].duration, 2, accuracy: 0.0001)
        XCTAssertEqual(efforts[1].duration, 1, accuracy: 0.0001)
        XCTAssertEqual(efforts.map(\.peakLoadKGF), [12, 14])
        XCTAssertEqual(efforts.map(\.sampleCount), [3, 2])
    }

    func testShortGapMergesEffortsWithoutLosingPeak() {
        var workout = newWorkout(
            configuration: MotherboardDetectionConfiguration(
                thresholdKGF: 2.5,
                releaseRatio: 0.8,
                debounceDuration: 0,
                mergeGapDuration: 0.5
            ),
            streamGapTimeout: 10
        )
        start(workout: &workout, depth: 18)

        receive(&workout, load: 10, at: 1)
        receive(&workout, load: 20, at: 2)
        receive(&workout, load: 0, at: 2.1)
        receive(&workout, load: 12, at: 2.3)
        receive(&workout, load: 0, at: 3)

        XCTAssertEqual(workout.efforts.count, 1)
        XCTAssertEqual(workout.efforts.first?.duration ?? 0, 2, accuracy: 0.0001)
        XCTAssertEqual(workout.efforts.first?.peakLoadKGF, 20)
    }

    func testPauseClosesAtLastSampleAndStaleOrNonfiniteSamplesAreIgnored() {
        var workout = newWorkout(streamGapTimeout: 10)
        start(workout: &workout, depth: 18)

        receive(&workout, load: 10, at: 1)
        receive(&workout, load: 12, at: 2)
        workout.pause(at: 3)
        XCTAssertEqual(workout.state, .paused)
        XCTAssertEqual(workout.efforts.first?.duration ?? 0, 1, accuracy: 0.0001)

        // Repeated and out-of-order samples must not reopen or extend the effort.
        workout.resume()
        receive(&workout, load: 10, at: 2, elapsed: 4)
        receive(&workout, load: 10, at: 1.5, elapsed: 5)
        receive(&workout, load: .nan, at: 6)
        XCTAssertEqual(workout.efforts.count, 1)
    }

    func testStartRejectsCachedDelayedAndFutureSamples() {
        var workout = newWorkout()
        receive(&workout, load: 10, at: 1)
        XCTAssertEqual(workout.state, .idle)
        XCTAssertTrue(workout.efforts.isEmpty)

        start(workout: &workout, depth: 18, latestSampleNumber: 5)
        receive(&workout, load: 80, at: 0, number: 5)
        receive(&workout, load: 80, at: -0.25, number: 6, elapsed: 0.25, sampleElapsed: -0.25)
        receive(&workout, load: 80, at: 0.5, number: 7, elapsed: 0.25, sampleElapsed: 0.5)
        XCTAssertNil(workout.liveMeasurement)
        receive(&workout, load: 12, at: 0.5, number: 8)
        XCTAssertEqual(workout.liveMeasurement?.sampleNumber, 8)
    }

    // MARK: - Default debounce, hysteresis and noise

    func testDefaultDebounceRejectsBriefNoiseBlip() {
        // Default configuration: 0.10s debounce. A single qualifying sample
        // followed by a release never opens an interval.
        var workout = FreeformWorkout()
        start(workout: &workout, depth: 18)

        receive(&workout, load: 10, at: 1)
        receive(&workout, load: 0, at: 1.05)
        receive(&workout, load: 0, at: 2)

        XCTAssertTrue(workout.efforts.isEmpty)
        XCTAssertNil(workout.finish(at: 2.5))
    }

    func testReleaseHysteresisKeepsEffortOpenUntilFullyReleased() {
        var workout = FreeformWorkout()
        start(workout: &workout, depth: 18)

        receive(&workout, load: 10, at: 1)
        receive(&workout, load: 10, at: 1.2)
        // 2.2 is below the 2.5 threshold but above 2.0 (threshold * 0.8).
        receive(&workout, load: 2.2, at: 1.5)
        receive(&workout, load: 2.2, at: 1.8)
        XCTAssertEqual(workout.efforts.count, 1, "Partial release must not close the effort")

        receive(&workout, load: 0, at: 2.2)
        receive(&workout, load: 0, at: 2.35)
        XCTAssertEqual(workout.efforts.count, 1)
        XCTAssertEqual(workout.efforts.first?.duration ?? 0, 1.2, accuracy: 0.0001)
        XCTAssertEqual(workout.efforts.first?.peakLoadKGF ?? 0, 10)
    }

    func testActiveEffortPeakIncludesPendingStartAndMergePeaks() {
        var workout = FreeformWorkout()
        start(workout: &workout, depth: 18)

        // Peak during the debounce (pending start) window.
        receive(&workout, load: 40, at: 1)
        receive(&workout, load: 10, at: 1.2)
        receive(&workout, load: 0, at: 1.4)
        receive(&workout, load: 0, at: 1.51)

        // A short-gap merge with a lower new peak must keep the earlier peak.
        receive(&workout, load: 25, at: 1.54)
        receive(&workout, load: 25, at: 1.75)
        receive(&workout, load: 0, at: 2)
        receive(&workout, load: 0, at: 2.2)

        XCTAssertEqual(workout.efforts.count, 1)
        XCTAssertEqual(workout.efforts.first?.peakLoadKGF ?? 0, 40)
    }

    func testSnapshotShowsCurrentEffortWithoutDroppingReleasedInterval() {
        var workout = FreeformWorkout()
        start(workout: &workout, depth: 18)

        receive(&workout, load: 10, at: 1)
        receive(&workout, load: 10, at: 1.2)
        receive(&workout, load: 0, at: 1.4)
        receive(&workout, load: 0, at: 1.6)
        XCTAssertEqual(workout.efforts.count, 1)

        // A new effort with observed duration must appear in the live snapshot
        // while the released interval remains. A lone pending spike must not.
        receive(&workout, load: 12, at: 2)
        XCTAssertEqual(workout.efforts.count, 1, "A pending one-sample candidate is not a live effort")
        receive(&workout, load: 12, at: 2.2)
        XCTAssertEqual(workout.efforts.count, 2)
        XCTAssertEqual(workout.efforts[0].duration, 0.4, accuracy: 0.0001)
        XCTAssertEqual(workout.efforts[1].duration, 0.2, accuracy: 0.0001)
        XCTAssertEqual(workout.efforts[1].peakLoadKGF, 12)
    }

    // MARK: - Stream sample identity (batch, replay, wrap)

    func testBatchSamplesSharingReceiveTimestampKeepInteriorPeak() {
        var workout = newWorkout()
        start(workout: &workout, depth: 18)

        // Progressor/PitchSix deliver several samples in one notification with
        // the same receive time but distinct, increasing sample numbers.
        receive(&workout, load: 3, at: 1, number: 10)
        receive(&workout, load: 25, at: 1, number: 11)
        receive(&workout, load: 3, at: 1, number: 12)
        receive(&workout, load: 0, at: 1.2, number: 13)

        XCTAssertEqual(workout.efforts.count, 1)
        XCTAssertEqual(workout.efforts.first?.peakLoadKGF ?? 0, 25)
    }

    func testReplayedSampleNumberWithFreshReceiveTimeIsRejected() {
        var workout = newWorkout()
        start(workout: &workout, depth: 18)

        receive(&workout, load: 10, at: 1, number: 7)
        receive(&workout, load: 12, at: 1.2, number: 8)
        // A replayed Motherboard frame keeps its device sample number but gets
        // a fresh transport time; it must not change the recorded peak.
        receive(&workout, load: 50, at: 2, number: 7)

        XCTAssertEqual(workout.liveMeasurement?.sampleNumber, 8)
        XCTAssertEqual(workout.efforts.first?.peakLoadKGF ?? 0, 12)
    }

    func testUInt16SampleNumberWrapAdvancesOrdering() {
        var workout = newWorkout()
        start(workout: &workout, depth: 18)

        receive(&workout, load: 10, at: 1, number: 65534)
        receive(&workout, load: 12, at: 1, number: 65535)
        receive(&workout, load: 14, at: 1, number: 0)
        receive(&workout, load: 0, at: 1.2, number: 1)

        XCTAssertEqual(workout.efforts.first?.peakLoadKGF ?? 0, 14)
    }

    func testStreamRestartResetsSampleNumberOrdering() {
        var workout = newWorkout()
        start(workout: &workout, depth: 18)
        receive(&workout, load: 10, at: 1, number: 400)
        receive(&workout, load: 12, at: 1.2, number: 401)
        receive(&workout, load: 0, at: 1.4, number: 402)
        workout.pause(at: 2)
        workout.resume(latestSampleNumber: 0, streamRestarted: true)

        // A confirmed new stream restarts the connected scale's counter.
        receive(&workout, load: 10, at: 5.2, number: 1, elapsed: 7)
        receive(&workout, load: 12, at: 5.4, number: 2, elapsed: 7.2)
        receive(&workout, load: 0, at: 5.6, number: 3, elapsed: 7.4)

        XCTAssertEqual(workout.efforts.count, 2)
    }

    // MARK: - Stream liveness gaps

    func testLateReleaseAfterStreamGapDoesNotBookStallTime() {
        var workout = newWorkout()
        start(workout: &workout, depth: 18)
        receive(&workout, load: 10, at: 1)
        receive(&workout, load: 12, at: 1.2)
        // The stream is silent for several seconds; a late release must not extend
        // the first effort across the gap.
        receive(&workout, load: 0, at: 8)

        XCTAssertEqual(workout.loadedDuration, 0.2, accuracy: 0.0001)
    }

    func testStreamGapPreventsTwoSpikesFromSatisfyingStartDebounce() {
        var workout = FreeformWorkout(
            configuration: MotherboardDetectionConfiguration(debounceDuration: 0.1),
            streamGapTimeout: FreeformWorkout.recordingGapTimeout(for: .motherboard)
        )
        start(workout: &workout, depth: 18)
        receive(&workout, load: 10, at: 1)
        receive(&workout, load: 10, at: 8)
        receive(&workout, load: 0, at: 8.2)

        XCTAssertTrue(workout.efforts.isEmpty)
        XCTAssertEqual(workout.loadedDuration, 0, accuracy: 0.001)
    }

    func testTimerGapInterruptClosesOpenEffortAtLastSample() {
        var workout = newWorkout()
        start(workout: &workout, depth: 18)
        receive(&workout, load: 10, at: 1)
        receive(&workout, load: 12, at: 1.2)

        XCTAssertTrue(
            workout.interruptStreamGapIfNeeded(at: 8)
        )
        XCTAssertEqual(workout.loadedDuration, 0.2, accuracy: 0.0001)
        XCTAssertNil(workout.liveMeasurement)
        XCTAssertFalse(
            workout.interruptStreamGapIfNeeded(at: 9)
        )
    }

    // MARK: - Sensor identity on resume

    func testResumeRequiresCapturedDeviceAndProfile() {
        var workout = newWorkout()
        start(workout: &workout, depth: 18)
        workout.pause(at: 2)

        XCTAssertTrue(workout.canResume(deviceID: "sensor-1", profile: .motherboard))
        XCTAssertFalse(workout.canResume(deviceID: "sensor-2", profile: .motherboard))
        XCTAssertFalse(workout.canResume(deviceID: "sensor-1", profile: .pitchSix))
        XCTAssertFalse(workout.canResume(deviceID: nil, profile: .motherboard))
    }

    // MARK: - Per-effort release bookkeeping

    func testConfirmedReleaseExcludesPostEndDebounceFrames() {
        var workout = FreeformWorkout()
        start(workout: &workout, depth: 18)
        receive(&workout, load: 10, at: 1)
        receive(&workout, load: 12, at: 1.2)
        receive(&workout, load: 0, at: 2.2)
        receive(&workout, load: 0, at: 2.25)
        XCTAssertEqual(workout.efforts.first?.duration ?? 0, 1.25, accuracy: 0.001)
        XCTAssertEqual(workout.efforts.first?.sampleCount, 4)
        receive(&workout, load: 0, at: 2.35)

        XCTAssertEqual(workout.efforts.first?.duration ?? 0, 1.2, accuracy: 0.001)
        XCTAssertEqual(workout.efforts.first?.sampleCount, 3)
        XCTAssertEqual(workout.efforts.first?.peakLoadKGF ?? 0, 12)
    }

    func testShortGapMergeKeepsAcceptedCountsWithoutReleasedFrames() {
        var workout = newWorkout(
            configuration: MotherboardDetectionConfiguration(
                thresholdKGF: 2.5,
                releaseRatio: 0.8,
                debounceDuration: 0.1,
                mergeGapDuration: 0.5
            ),
            streamGapTimeout: 10
        )
        start(workout: &workout, depth: 18)
        receive(&workout, load: 10, at: 1)
        receive(&workout, load: 10, at: 1.2)
        receive(&workout, load: 0, at: 2.2)
        receive(&workout, load: 0, at: 2.4)
        receive(&workout, load: 10, at: 2.6)
        receive(&workout, load: 10, at: 2.8)
        receive(&workout, load: 0, at: 3.5)
        receive(&workout, load: 0, at: 3.7)

        XCTAssertEqual(workout.efforts.count, 1)
        XCTAssertEqual(workout.efforts.first?.sampleCount, 6)
        XCTAssertEqual(workout.efforts.first?.peakLoadKGF ?? 0, 10)
    }

    // MARK: - Replay identity across gaps and pauses

    func testTimerInterruptDoesNotForgetReplayIdentity() {
        var workout = newWorkout()
        start(workout: &workout, depth: 18)
        receive(&workout, load: 10, at: 1, number: 8)
        receive(&workout, load: 12, at: 1.2, number: 9)

        XCTAssertTrue(workout.interruptStreamGapIfNeeded(at: 8))
        // A replayed frame 8 with a fresh receive time must not reopen the effort.
        receive(&workout, load: 40, at: 8.2, number: 8)
        XCTAssertNil(workout.liveMeasurement)
        XCTAssertEqual(workout.efforts.first?.peakLoadKGF ?? 0, 12)
    }

    func testOrdinaryResumeDoesNotForgetReplayIdentity() {
        var workout = newWorkout()
        start(workout: &workout, depth: 18)
        receive(&workout, load: 10, at: 1, number: 5)
        receive(&workout, load: 12, at: 1.2, number: 6)
        workout.pause(at: 2)
        workout.resume()

        receive(&workout, load: 40, at: 5.2, number: 5, elapsed: 7)
        XCTAssertNil(workout.liveMeasurement)
        XCTAssertEqual(workout.efforts.first?.peakLoadKGF ?? 0, 12)
    }

    func testRegressiveReceiveTimeIsRejectedAndEqualTimesAreAccepted() {
        var workout = newWorkout()
        start(workout: &workout, depth: 18)
        receive(&workout, load: 10, at: 10, number: 1)
        receive(&workout, load: 999, at: 9, number: 2, elapsed: 11, sampleElapsed: 9)
        XCTAssertEqual(workout.liveMeasurement?.sampleNumber, 1)
        receive(&workout, load: 14, at: 10.2, number: 3, elapsed: 12, sampleElapsed: 10.2)

        XCTAssertLessThan(workout.efforts.first?.peakLoadKGF ?? 999, 100)
        XCTAssertLessThan(workout.loadedDuration, 0.5)

        var batch = newWorkout()
        start(workout: &batch, depth: 18)
        receive(&batch, load: 10, at: 1, number: 1)
        receive(&batch, load: 12, at: 1, number: 2, elapsed: 1.001, sampleElapsed: 1)
        XCTAssertEqual(batch.liveMeasurement?.sampleNumber, 2)
        XCTAssertTrue(batch.efforts.isEmpty)
        receive(&batch, load: 0, at: 1.2, number: 3)
        XCTAssertEqual(batch.efforts.first?.peakLoadKGF, 12)
    }

    func testRecordingGapToleranceIsSelectedByProfile() {
        XCTAssertEqual(FreeformWorkout.recordingGapTimeout(for: .motherboard), 0.5)
        XCTAssertEqual(FreeformWorkout.recordingGapTimeout(for: .progressor), 1)
        XCTAssertEqual(FreeformWorkout.recordingGapTimeout(for: .genericProgressor), 1)
        XCTAssertEqual(FreeformWorkout.recordingGapTimeout(for: .pitchSix), 1)
        XCTAssertEqual(
            FreeformWorkout.recordingGapTimeout(for: .whC06),
            WHC06ProtocolAdapter.advertisementLivenessTimeout
        )
    }

    // MARK: - Live depth presentation

    func testDepthTextPreservesAcceptedPrecision() {
        let locale = Locale(identifier: "en_US")
        XCTAssertEqual(FreeformWorkout.depthText(18.5, locale: locale), "18.5 mm")
        XCTAssertEqual(FreeformWorkout.depthText(18.55, locale: locale), "18.55 mm")
        XCTAssertEqual(FreeformWorkout.depthText(0.04, locale: locale), "0.04 mm")
        XCTAssertEqual(FreeformWorkout.depthText(0.004, locale: locale), "0.004 mm")
    }

    // MARK: - Pause / reconnect gaps

    func testResumeCutoffPreventsPausedGapFromBeingBridged() {
        var workout = FreeformWorkout()
        start(workout: &workout, depth: 18)

        receive(&workout, load: 10, at: 1)
        receive(&workout, load: 10, at: 1.2)
        receive(&workout, load: 0, at: 1.5)
        receive(&workout, load: 0, at: 1.7)
        XCTAssertEqual(workout.efforts.count, 1)

        workout.pause(at: 2)
        workout.resume()

        // Sample captured during the pause but delivered after resume is rejected.
        receive(&workout, load: 10, at: 4.875, elapsed: 2.125, sampleElapsed: 1.875)
        XCTAssertNil(workout.liveMeasurement)
        receive(&workout, load: 10, at: 5, elapsed: 2.125, sampleElapsed: 2)
        XCTAssertNil(workout.liveMeasurement)
        XCTAssertEqual(workout.efforts.count, 1)

        // Fresh samples form a distinct effort; the gap is not loaded time.
        receive(&workout, load: 10, at: 5.2, elapsed: 2.2)
        receive(&workout, load: 10, at: 5.4, elapsed: 2.4)
        receive(&workout, load: 0, at: 6, elapsed: 3)
        receive(&workout, load: 0, at: 6.2, elapsed: 3.2)
        XCTAssertEqual(workout.efforts.count, 2)
        // 0.5s before the pause + 0.8s after resume; the 3.5s gap is not loaded.
        XCTAssertEqual(workout.loadedDuration, 1.3, accuracy: 0.0001)
    }

    func testLongPauseTracksSequenceWithoutRecordingForce() {
        var workout = newWorkout()
        start(workout: &workout, depth: 18)
        receive(&workout, load: 10, at: 1, number: 50_000)
        receive(&workout, load: 0, at: 1.2, number: 50_001)
        workout.pause(at: 2)

        // The same stream wraps and advances 40,000 frames during the pause.
        receive(&workout, load: 90, at: 334, number: 60_001, elapsed: 2)
        receive(&workout, load: 90, at: 668, number: 4_465, elapsed: 2)
        receive(&workout, load: 90, at: 1_002, number: 14_465, elapsed: 2)
        receive(&workout, load: 90, at: 1_336, number: 24_465, elapsed: 2)
        XCTAssertNil(workout.liveMeasurement)
        XCTAssertEqual(workout.peakLoadKGF, 10)
        XCTAssertEqual(workout.elapsed, 2)

        // The service can have published a last replay while paused.
        workout.resume(latestSampleNumber: 24_464)
        receive(&workout, load: 90, at: 1_336.2, number: 24_465, elapsed: 2.2)
        XCTAssertNil(workout.liveMeasurement)
        receive(&workout, load: 12, at: 1_336.3, number: 24_466, elapsed: 2.3)
        receive(&workout, load: 0, at: 1_336.5, number: 24_467, elapsed: 2.5)
        XCTAssertEqual(workout.efforts.map(\.peakLoadKGF), [10, 12])
        XCTAssertEqual(workout.loadedDuration, 0.4, accuracy: 0.0001)
    }

    func testClockChangesPreserveResumeFreshnessAndMeasuredDuration() {
        var workout = newWorkout()
        start(workout: &workout, depth: 18)
        receive(&workout, load: 10, at: 1, number: 1)
        receive(&workout, load: 0, at: 1.25, number: 2)
        workout.pause(at: 2)
        workout.resume()

        // Close the pause after a 60s rollback. Fresh wall stamps are now
        // earlier than the session start. Monotonic receive time identifies stale
        // packets, and replay identity does not depend on the wall clock.
        receive(&workout, load: 90, at: -56.25, number: 3, elapsed: 2.25, sampleElapsed: 1.75)
        receive(&workout, load: 90, at: -55.75, number: 2, elapsed: 2.25)
        XCTAssertNil(workout.liveMeasurement)
        receive(&workout, load: 12, at: -55.75, number: 4, elapsed: 2.25)
        receive(&workout, load: 20, at: -55.75, number: 5, elapsed: 2.25)
        XCTAssertEqual(workout.liveMeasurement?.timestamp, origin.addingTimeInterval(-55.75))
        XCTAssertEqual(workout.liveMeasurement?.sampleNumber, 5)

        // A forward jump during the next effort cannot stretch its duration or
        // split it from the release while the monotonic stream is continuous.
        receive(&workout, load: 0, at: 120, number: 6, elapsed: 2.55, sampleElapsed: 2.5)
        XCTAssertEqual(workout.efforts.map(\.peakLoadKGF), [10, 20])
        XCTAssertEqual(workout.loadedDuration, 0.5, accuracy: 0.0001)
    }

    // MARK: - Finish

    func testFinishWhileLoadedClosesAtObservedSample() throws {
        var workout = newWorkout(streamGapTimeout: 10)
        start(workout: &workout, depth: 18)
        receive(&workout, load: 10, at: 1)
        receive(&workout, load: 12, at: 2)

        let endDate = origin.addingTimeInterval(9)
        let session = try XCTUnwrap(workout.finish(at: 9, endDate: endDate))
        let step = try XCTUnwrap(session.steps.first)
        XCTAssertEqual(step.intervals, [LoadInterval(start: 1, end: 2)])
        XCTAssertEqual(step.peakLoadKGF, 12)
        XCTAssertEqual(session.stepTitles, ["Effort 1"])
        XCTAssertEqual(session.startDate, origin)
        XCTAssertEqual(session.endDate, endDate)
        XCTAssertEqual(session.recordedAt, endDate)
    }

    func testFinishExtendsReversedOrShortWallIntervalAfterClockRollback() throws {
        for (finishOffset, expectedStartOffset) in [(-3.0, -12.0), (4.0, -5.0)] {
            var workout = newWorkout(streamGapTimeout: 10)
            start(workout: &workout, depth: 18)
            receive(&workout, load: 10, at: 1)
            receive(&workout, load: 12, at: 2)

            let endDate = origin.addingTimeInterval(finishOffset)
            let session = try XCTUnwrap(workout.finish(at: 9, endDate: endDate))
            XCTAssertEqual(session.startDate, origin.addingTimeInterval(expectedStartOffset))
            XCTAssertEqual(session.endDate, endDate)
            XCTAssertEqual(session.recordedAt, endDate)
        }
    }

    func testFinishWhilePausedPreservesOriginalWallBounds() throws {
        var workout = newWorkout(streamGapTimeout: 10)
        start(workout: &workout, depth: 18)
        receive(&workout, load: 10, at: 1)
        receive(&workout, load: 12, at: 2)
        workout.pause(at: 3)

        let endDate = origin.addingTimeInterval(60)
        let session = try XCTUnwrap(workout.finish(at: 3, endDate: endDate))
        XCTAssertEqual(session.startDate, origin)
        XCTAssertEqual(session.endDate, endDate)
        XCTAssertEqual(session.recordedAt, endDate)
    }

    func testEmptySessionFinishesToNilAndStaysLive() {
        var workout = newWorkout()
        start(workout: &workout, depth: 18)
        XCTAssertNil(workout.finish(at: 3))
        XCTAssertEqual(workout.state, .active)
        // A single pending sample is not yet a savable effort.
        receive(&workout, load: 10, at: 4)
        XCTAssertTrue(workout.efforts.isEmpty)
        // "Keep training" can still build a positive-duration effort.
        receive(&workout, load: 12, at: 4.2)
        XCTAssertEqual(workout.efforts.first?.duration ?? 0, 0.2, accuracy: 0.001)
    }

    func testSingleLoadedSampleIsNotSavableEffort() {
        // Default debounce: one qualifying sample only opens a pending start.
        var defaultDebounce = FreeformWorkout()
        start(workout: &defaultDebounce, depth: 18)
        receive(&defaultDebounce, load: 10, at: 1)
        XCTAssertNil(defaultDebounce.finish(at: 1.1))
        XCTAssertEqual(defaultDebounce.state, .active)
        receive(&defaultDebounce, load: 12, at: 1.2)
        XCTAssertEqual(defaultDebounce.efforts.first?.duration ?? 0, 0.2, accuracy: 0.001)
        XCTAssertEqual(defaultDebounce.efforts.first?.sampleCount, 2)

        // Zero debounce opens an interval immediately, but with no observed
        // duration it must still be filtered out at finish.
        var zeroDebounce = newWorkout()
        start(workout: &zeroDebounce, depth: 18)
        receive(&zeroDebounce, load: 10, at: 1)
        XCTAssertNil(zeroDebounce.finish(at: 1))
    }

    func testDiscardWhileLoadedSavesNothing() {
        var workout = newWorkout(streamGapTimeout: 10)
        start(workout: &workout, depth: 18)
        receive(&workout, load: 10, at: 1)
        receive(&workout, load: 12, at: 2)
        XCTAssertFalse(workout.efforts.isEmpty)

        workout.discard()
        XCTAssertEqual(workout.state, .finished)
        XCTAssertNil(workout.finish(at: 3))
    }

    func testFinishedSessionIsScaleOnlyWithDepthAndOneStepPerEffort() throws {
        var workout = newWorkout(streamGapTimeout: 10)
        start(workout: &workout, depth: 18)
        receive(&workout, load: 10, at: 1)
        receive(&workout, load: 0, at: 2)
        receive(&workout, load: 9, at: 4)
        receive(&workout, load: 0, at: 5)

        let session = try XCTUnwrap(workout.finish(at: 6))
        XCTAssertEqual(session.planID, "freeform")
        XCTAssertEqual(session.planTitle, "Freeform")
        XCTAssertEqual(session.initialWeight.source, .sensor)
        XCTAssertEqual(session.edgeDepthMM, 18)
        XCTAssertEqual(session.motherboardIdentifier, "sensor-1")
        XCTAssertEqual(session.batteryValue, 80)
        XCTAssertEqual(session.forceSensorProfile, .motherboard)
        XCTAssertEqual(session.steps.count, 2)
        XCTAssertTrue(session.steps.allSatisfy { $0.status == .measured && $0.isGeneralActivity })
        XCTAssertTrue(session.steps.allSatisfy { $0.side == .both && $0.action == .hang })
    }

    // MARK: - Persistence compatibility

    func testLegacyRecordsDecodeWithoutDepthAndDepthRoundTrips() throws {
        let session = WorkoutSessionRecord(
            id: UUID(),
            planID: "freeform",
            planTitle: "Freeform",
            recordedAt: origin,
            startDate: origin,
            endDate: origin.addingTimeInterval(10),
            motherboardIdentifier: nil,
            batteryValue: nil,
            steps: [],
            edgeDepthMM: 18
        )
        let data = try JSONEncoder().encode(session)
        let roundTrip = try JSONDecoder().decode(WorkoutSessionRecord.self, from: data)
        XCTAssertEqual(roundTrip.edgeDepthMM, 18)

        var legacy = try XCTUnwrap(JSONSerialization.jsonObject(with: data) as? [String: Any])
        legacy.removeValue(forKey: "edgeDepthMM")
        let legacyData = try JSONSerialization.data(withJSONObject: legacy)
        let decoded = try JSONDecoder().decode(WorkoutSessionRecord.self, from: legacyData)
        XCTAssertNil(decoded.edgeDepthMM)
    }

    // MARK: - Helpers

    private func newWorkout(
        configuration: MotherboardDetectionConfiguration = MotherboardDetectionConfiguration(
            thresholdKGF: 2.5,
            releaseRatio: 0.8,
            debounceDuration: 0,
            mergeGapDuration: 0
        ),
        streamGapTimeout: TimeInterval = 0.5
    ) -> FreeformWorkout {
        FreeformWorkout(
            configuration: configuration,
            streamGapTimeout: streamGapTimeout
        )
    }

    private func start(workout: inout FreeformWorkout, depth: Double, latestSampleNumber: UInt16? = nil) {
        workout.start(
            depthMM: depth,
            startDate: origin,
            sensorIdentifier: "sensor-1",
            sensorBatteryValue: 80,
            forceSensorProfile: .motherboard,
            latestSampleNumber: latestSampleNumber
        )
    }

    private func receive(
        _ workout: inout FreeformWorkout,
        load: Double,
        at seconds: TimeInterval,
        number: UInt16? = nil,
        elapsed: TimeInterval? = nil,
        sampleElapsed: TimeInterval? = nil
    ) {
        let measurement = MotherboardMeasurement(
            timestamp: origin.addingTimeInterval(seconds),
            sampleNumber: number ?? UInt16(round(seconds * 100)),
            batteryValue: 80,
            sensorLoadsKGF: [load, 0, 0, 0],
            aggregateLoadKGF: load
        )
        workout.consume(
            measurement,
            sampleElapsed: sampleElapsed ?? elapsed ?? seconds,
            elapsed: elapsed ?? seconds
        )
    }
}
