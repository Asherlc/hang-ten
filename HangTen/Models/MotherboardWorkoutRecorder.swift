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

        func clippedTime(_ time: TimeInterval) -> TimeInterval {
            min(time, plannedEnd)
        }

        var plannedEnd: TimeInterval {
            stepStartElapsed + plannedActiveDuration
        }
    }

    private let configuration: MotherboardDetectionConfiguration
    private var states: [String: StepState] = [:]
    private var stepOrder: [String] = []
    private(set) var currentStepID: String?

    private(set) var currentLoadKGF: Double?
    private(set) var currentPeakLoadKGF: Double?
    private(set) var currentLoadedDuration: TimeInterval = 0

    var isLoaded: Bool {
        guard let currentStepID else { return false }
        return states[currentStepID]?.openStart != nil
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
        currentLoadKGF = measurement.aggregateLoadKGF
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
            states[stepID] = state
            return
        }

        state.sampleCount += 1
        state.peakLoadKGF = max(state.peakLoadKGF ?? measurement.aggregateLoadKGF, measurement.aggregateLoadKGF)
        currentPeakLoadKGF = state.peakLoadKGF

        let time = state.clippedTime(workoutElapsed)
        let isQualifying = measurement.aggregateLoadKGF >= configuration.thresholdKGF
        let isReleased = measurement.aggregateLoadKGF < configuration.thresholdKGF * configuration.releaseRatio

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
            state.pendingRelease = nil
        }

        states[stepID] = state
        currentLoadedDuration = loadedDuration(in: state, at: time)
    }

    mutating func pause(at workoutElapsed: TimeInterval) {
        guard let currentStepID, var state = states[currentStepID] else { return }
        closeInterval(in: &state, at: workoutElapsed)
        state.pendingStart = nil
        state.pendingRelease = nil
        state.permitsMergeWithPrevious = false
        states[currentStepID] = state
        currentLoadedDuration = loadedDuration(in: state, at: workoutElapsed)
    }

    mutating func endStep(
        stepID: String,
        at workoutElapsed: TimeInterval,
        status: WorkoutStepMeasurement.Status = .measured
    ) {
        guard var state = states[stepID] else { return }
        closeInterval(in: &state, at: workoutElapsed)
        state.pendingStart = nil
        state.pendingRelease = nil
        state.status = status
        states[stepID] = state
        currentStepID = stepID
        currentLoadedDuration = loadedDuration(in: state, at: workoutElapsed)
    }

    mutating func interrupt(at workoutElapsed: TimeInterval) {
        pause(at: workoutElapsed)
        guard let currentStepID, var state = states[currentStepID] else { return }
        state.status = .interrupted
        states[currentStepID] = state
    }

    mutating func finish(at workoutElapsed: TimeInterval) -> [WorkoutStepMeasurement] {
        for stepID in stepOrder {
            guard var state = states[stepID] else { continue }
            closeInterval(in: &state, at: workoutElapsed)
            state.pendingStart = nil
            state.pendingRelease = nil
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

        if state.permitsMergeWithPrevious,
           let previous = state.intervals.last,
           start - previous.end <= configuration.mergeGapDuration {
            state.intervals.removeLast()
            state.openStart = previous.start
        } else {
            state.openStart = start
        }
        state.permitsMergeWithPrevious = true
    }

    private func closeInterval(in state: inout StepState, at time: TimeInterval) {
        guard let start = state.openStart else { return }
        let end = max(start, state.clippedTime(time))
        state.intervals.append(LoadInterval(start: start, end: end))
        state.openStart = nil
        state.pendingRelease = nil
    }

    private func loadedDuration(in state: StepState, at time: TimeInterval) -> TimeInterval {
        let closedDuration = state.intervals.reduce(0) { $0 + $1.duration }
        guard let openStart = state.openStart else { return closedDuration }
        return closedDuration + max(0, state.clippedTime(time) - openStart)
    }
}
