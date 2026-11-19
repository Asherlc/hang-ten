import Foundation

struct MotherboardWorkoutRecorder {
    private struct StepState {
        let plannedActiveDuration: TimeInterval
        let stepStartElapsed: TimeInterval
        var intervals: [LoadInterval] = []
        var openStart: TimeInterval?
        var pendingStart: TimeInterval?
        var pendingRelease: TimeInterval?
        var peakLoadKGF: Double?
        var sampleCount = 0
        var status: WorkoutStepMeasurement.Status = .unmeasured
        var permitsMergeWithPrevious = true
        var lastMeasurementTimestamp: Date?
        var observedElapsed: TimeInterval?

        // Per-effort bookkeeping, parallel to `intervals`. A self-paced step can
        // contain several auto-detected efforts; each needs its own peak and
        // sample count when it is surfaced as a separate workout step.
        var effortPeaks: [Double] = []
        var effortSampleCounts: [Int] = []
        var currentEffortPeak: Double?
        var currentEffortSampleCount = 0

        // Frames observed after the first released frame but before the release
        // debounce completes. They fall outside the interval that closes at the
        // first released frame, so they are held here and dropped on a confirmed
        // close (or folded back in if the effort resumes before the close).
        var pendingReleasePeak: Double?
        var pendingReleaseSampleCount = 0

        func clippedTime(_ time: TimeInterval) -> TimeInterval {
            plannedActiveDuration == 0 ? time : min(time, plannedEnd)
        }

        func closingTime(_ scheduledTime: TimeInterval) -> TimeInterval {
            plannedActiveDuration == 0 ? (observedElapsed ?? scheduledTime) : scheduledTime
        }

        var plannedEnd: TimeInterval {
            stepStartElapsed + plannedActiveDuration
        }
    }

    private let configuration: MotherboardDetectionConfiguration
    private var states: [String: StepState] = [:]
    private var stepOrder: [String] = []
    private(set) var currentStepID: String?

    private(set) var currentPeakLoadKGF: Double?
    private(set) var currentLoadedDuration: TimeInterval = 0

    var recordedWorkStepIDs: Set<String> {
        Set(states.compactMap { id, state in
            let hasWork = state.intervals.contains { $0.duration > 0 }
                || (id == currentStepID && currentLoadedDuration > 0)
            return hasWork ? id : nil
        })
    }

    init(configuration: MotherboardDetectionConfiguration = .init()) {
        self.configuration = configuration
    }

    mutating func consume(
        _ measurement: MotherboardMeasurement,
        stepID: String,
        plannedActiveDuration: TimeInterval,
        workoutElapsed: TimeInterval,
        stepStartElapsed: TimeInterval? = nil,
        isActive: Bool
    ) {
        if currentStepID != stepID {
            currentPeakLoadKGF = nil
            currentLoadedDuration = 0
        }
        currentStepID = stepID

        var state = state(
            for: stepID,
            plannedActiveDuration: plannedActiveDuration,
            stepStartElapsed: stepStartElapsed ?? workoutElapsed
        )
        guard isActive else {
            if plannedActiveDuration == 0 { state.lastMeasurementTimestamp = nil }
            states[stepID] = state
            return
        }

        state.sampleCount += 1
        state.peakLoadKGF = max(state.peakLoadKGF ?? measurement.aggregateLoadKGF, measurement.aggregateLoadKGF)
        currentPeakLoadKGF = state.peakLoadKGF

        let time: TimeInterval
        if plannedActiveDuration == 0 {
            // A self-paced step has no scheduled seconds. Observe sensor time
            // without advancing the navigation clock or including paused gaps.
            let delta = state.lastMeasurementTimestamp.map {
                max(0, measurement.timestamp.timeIntervalSince($0))
            } ?? 0
            time = (state.observedElapsed ?? state.stepStartElapsed) + delta
            state.observedElapsed = time
            state.lastMeasurementTimestamp = measurement.timestamp
        } else {
            time = state.clippedTime(workoutElapsed)
        }
        let isQualifying = measurement.aggregateLoadKGF >= configuration.thresholdKGF
        let isReleased = measurement.aggregateLoadKGF < configuration.thresholdKGF * configuration.releaseRatio

        // Track peak and sample count for the effort currently being detected,
        // including the debounce samples that precede the interval opening.
        // Post-release debounce frames are counted separately so a confirmed
        // close does not count frames after the interval's end timestamp.
        if measurement.aggregateLoadKGF.isFinite {
            if state.openStart != nil || isQualifying {
                if state.openStart != nil, state.pendingRelease != nil {
                    state.pendingReleasePeak = max(
                        state.pendingReleasePeak ?? measurement.aggregateLoadKGF,
                        measurement.aggregateLoadKGF
                    )
                    state.pendingReleaseSampleCount += 1
                } else {
                    state.currentEffortPeak = max(
                        state.currentEffortPeak ?? measurement.aggregateLoadKGF,
                        measurement.aggregateLoadKGF
                    )
                    state.currentEffortSampleCount += 1
                }
            } else {
                state.currentEffortPeak = nil
                state.currentEffortSampleCount = 0
                state.pendingReleasePeak = nil
                state.pendingReleaseSampleCount = 0
            }
        }

        if state.openStart == nil {
            if isQualifying {
                if let pendingStart = state.pendingStart {
                    if time - pendingStart >= configuration.debounceDuration {
                        openInterval(in: &state, at: pendingStart)
                    }
                } else {
                    state.pendingStart = time
                    if configuration.debounceDuration == 0 {
                        openInterval(in: &state, at: time)
                    }
                }
            } else {
                state.pendingStart = nil
            }
        } else if isReleased {
            if let pendingRelease = state.pendingRelease {
                if time - pendingRelease >= configuration.debounceDuration {
                    closeInterval(in: &state, at: pendingRelease)
                }
            } else {
                state.pendingRelease = time
                if configuration.debounceDuration == 0 {
                    closeInterval(in: &state, at: time)
                }
            }
        } else {
            // Load returned before the release debounce completed. The held
            // frames are inside the still-open effort, so fold them back in.
            commitPendingRelease(in: &state)
            state.pendingRelease = nil
        }

        states[stepID] = state
        currentLoadedDuration = loadedDuration(in: state, at: time)
    }

    mutating func pause(at workoutElapsed: TimeInterval) {
        guard let currentStepID, var state = states[currentStepID] else { return }
        let time = state.closingTime(workoutElapsed)
        closeInterval(in: &state, at: time, includePendingRelease: true)
        state.lastMeasurementTimestamp = nil
        state.pendingStart = nil
        state.pendingRelease = nil
        state.currentEffortPeak = nil
        state.currentEffortSampleCount = 0
        state.permitsMergeWithPrevious = false
        states[currentStepID] = state
        currentLoadedDuration = loadedDuration(in: state, at: time)
    }

    mutating func endStep(
        stepID: String,
        at workoutElapsed: TimeInterval,
        status: WorkoutStepMeasurement.Status = .measured
    ) {
        guard var state = states[stepID] else { return }
        let time = state.closingTime(workoutElapsed)
        closeInterval(in: &state, at: time, includePendingRelease: true)
        state.lastMeasurementTimestamp = nil
        state.pendingStart = nil
        state.pendingRelease = nil
        state.currentEffortPeak = nil
        state.currentEffortSampleCount = 0
        state.status = status
        states[stepID] = state
        currentStepID = stepID
        currentLoadedDuration = loadedDuration(in: state, at: time)
    }

    mutating func interrupt(at workoutElapsed: TimeInterval) {
        guard let currentStepID, let state = states[currentStepID] else { return }
        interrupt(
            stepID: currentStepID,
            plannedActiveDuration: state.plannedActiveDuration,
            stepStartElapsed: state.stepStartElapsed,
            at: workoutElapsed
        )
    }

    mutating func interrupt(
        stepID: String,
        plannedActiveDuration: TimeInterval,
        stepStartElapsed: TimeInterval,
        at workoutElapsed: TimeInterval
    ) {
        var state = state(
            for: stepID,
            plannedActiveDuration: plannedActiveDuration,
            stepStartElapsed: stepStartElapsed
        )
        let time = state.closingTime(workoutElapsed)
        closeInterval(in: &state, at: time, includePendingRelease: true)
        state.lastMeasurementTimestamp = nil
        state.pendingStart = nil
        state.pendingRelease = nil
        state.currentEffortPeak = nil
        state.currentEffortSampleCount = 0
        state.permitsMergeWithPrevious = false
        state.status = .interrupted
        states[stepID] = state
        currentStepID = stepID
        currentLoadedDuration = loadedDuration(in: state, at: time)
    }

    mutating func finish(at workoutElapsed: TimeInterval) -> [WorkoutStepMeasurement] {
        for stepID in stepOrder {
            guard var state = states[stepID] else { continue }
            let time = state.closingTime(workoutElapsed)
            closeInterval(in: &state, at: time, includePendingRelease: true)
            state.pendingStart = nil
            state.pendingRelease = nil
            state.currentEffortPeak = nil
            state.currentEffortSampleCount = 0
            if state.sampleCount > 0, state.status == .unmeasured {
                state.status = .measured
            }
            states[stepID] = state
        }

        return stepOrder.compactMap { stepID in
            guard let state = states[stepID] else { return nil }
            return WorkoutStepMeasurement(
                stepID: stepID,
                plannedActiveDuration: state.plannedActiveDuration,
                intervals: state.intervals,
                peakLoadKGF: state.peakLoadKGF,
                sampleCount: state.sampleCount,
                status: state.status
            )
        }
    }

    /// Auto-detected efforts for a self-paced step, each with its own measured
    /// interval, peak load and sample count. Zero-length intervals (a single
    /// loaded sample with no observed duration) are not savable efforts and are
    /// omitted. When `includeCurrent` is true the in-progress effort is appended
    /// using the last observed sample time, without disturbing released efforts.
    /// Returns an empty array for paced steps or unknown step IDs; those continue
    /// to use `finish(at:)`.
    func recordedEfforts(stepID: String, includeCurrent: Bool = false) -> [RecordedEffort] {
        guard let state = states[stepID], state.plannedActiveDuration == 0 else { return [] }
        var efforts = state.intervals.enumerated().compactMap { index, interval -> RecordedEffort? in
            guard interval.duration > 0,
                  state.effortPeaks.indices.contains(index),
                  state.effortSampleCounts.indices.contains(index) else { return nil }
            return RecordedEffort(
                interval: interval,
                peakLoadKGF: state.effortPeaks[index],
                sampleCount: state.effortSampleCounts[index]
            )
        }
        // The live list shows only efforts with a confirmed open interval and
        // positive observed duration. A lone pending-start spike is a noise
        // candidate, not an effort row.
        guard includeCurrent, state.currentEffortSampleCount > 0,
              let start = state.openStart else { return efforts }
        let end = max(start, state.observedElapsed ?? start)
        guard end > start else { return efforts }
        efforts.append(
            RecordedEffort(
                interval: LoadInterval(start: start, end: end),
                peakLoadKGF: state.currentEffortPeak ?? 0,
                sampleCount: state.currentEffortSampleCount
            )
        )
        return efforts
    }

    private mutating func state(
        for stepID: String,
        plannedActiveDuration: TimeInterval,
        stepStartElapsed: TimeInterval
    ) -> StepState {
        if let state = states[stepID] { return state }

        let state = StepState(
            plannedActiveDuration: plannedActiveDuration,
            stepStartElapsed: stepStartElapsed
        )
        states[stepID] = state
        stepOrder.append(stepID)
        return state
    }

    private mutating func openInterval(in state: inout StepState, at time: TimeInterval) {
        let start = state.clippedTime(time)
        state.pendingStart = nil
        state.pendingRelease = nil

        var effortPeak = state.currentEffortPeak
        var effortSampleCount = state.currentEffortSampleCount
        if state.permitsMergeWithPrevious,
           let previous = state.intervals.last,
           start - previous.end <= configuration.mergeGapDuration {
            state.intervals.removeLast()
            if let previousPeak = state.effortPeaks.last {
                effortPeak = max(effortPeak ?? previousPeak, previousPeak)
            }
            effortSampleCount += state.effortSampleCounts.last ?? 0
            state.effortPeaks.removeLast()
            state.effortSampleCounts.removeLast()
            state.openStart = previous.start
        } else {
            state.openStart = start
        }
        state.currentEffortPeak = effortPeak
        state.currentEffortSampleCount = effortSampleCount
        state.permitsMergeWithPrevious = true
    }

    /// Folds post-release debounce frames back into the current effort. Used
    /// when an effort closes at the last observed frame (pause/interrupt/finish)
    /// or when load returns before the release debounce completes.
    private func commitPendingRelease(in state: inout StepState) {
        guard state.pendingReleaseSampleCount > 0 else { return }
        if let peak = state.pendingReleasePeak {
            state.currentEffortPeak = max(state.currentEffortPeak ?? peak, peak)
        }
        state.currentEffortSampleCount += state.pendingReleaseSampleCount
        state.pendingReleasePeak = nil
        state.pendingReleaseSampleCount = 0
    }

    private func closeInterval(
        in state: inout StepState,
        at time: TimeInterval,
        includePendingRelease: Bool = false
    ) {
        guard let start = state.openStart else { return }
        if includePendingRelease { commitPendingRelease(in: &state) }
        let end = max(start, state.clippedTime(time))
        state.intervals.append(LoadInterval(start: start, end: end))
        state.effortPeaks.append(state.currentEffortPeak ?? 0)
        state.effortSampleCounts.append(state.currentEffortSampleCount)
        state.openStart = nil
        state.pendingRelease = nil
        state.currentEffortPeak = nil
        state.currentEffortSampleCount = 0
        state.pendingReleasePeak = nil
        state.pendingReleaseSampleCount = 0
    }

    private func loadedDuration(in state: StepState, at time: TimeInterval) -> TimeInterval {
        let closedDuration = state.intervals.reduce(0) { $0 + $1.duration }
        guard let openStart = state.openStart else { return closedDuration }
        return closedDuration + max(0, state.clippedTime(time) - openStart)
    }
}
