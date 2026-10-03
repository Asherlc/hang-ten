import Foundation

struct WorkoutAudioMoment: Hashable {
	let key: String
	let phrase: String
	let countdownSchedule: CountdownAudioSchedule?

	init(
		key: String,
		phrase: String,
		countdownSchedule: CountdownAudioSchedule? = nil
	) {
		self.key = key
		self.phrase = phrase
		self.countdownSchedule = countdownSchedule
	}
}

enum WorkoutAudioCueAction: Equatable {
	case none
	case speak(WorkoutAudioMoment)
	case startCountdown(schedule: CountdownAudioSchedule, startUptime: TimeInterval)
}

@MainActor
enum WorkoutAudioCueRouter {
	@discardableResult
	static func route(
		_ action: WorkoutAudioCueAction,
		to audioCoach: WorkoutAudioCoach
	) -> Bool {
		switch action {
		case .none:
			return false
		case .speak(let moment):
			audioCoach.speak(moment.phrase)
			return true
		case .startCountdown(let schedule, let startUptime):
			return audioCoach.startCountdown(schedule, startUptime: startUptime)
		}
	}
}

enum WorkoutCountdownKind: Equatable {
    case initial
    case skip
}

struct MotherboardWorkoutMeasurementCollector {
    static let maximumMeasurementCount = 20_000
    private(set) var measurements: [MotherboardMeasurement] = []
    private(set) var didTruncate = false

    mutating func capture(
        _ measurement: MotherboardMeasurement,
        startedAt: Date?,
        countdownRemaining: Int,
        workoutElapsed: TimeInterval,
        planDuration: TimeInterval
    ) {
        guard let startedAt,
              WorkoutSessionPolicy.isMeasurementEligible(
                routineStartedAt: startedAt,
                measurementTimestamp: measurement.timestamp
              ),
              countdownRemaining == 0,
              workoutElapsed < planDuration else { return }

        if measurements.count >= Self.maximumMeasurementCount {
            didTruncate = true
            return
        }

        measurements.append(measurement)
    }

    mutating func reset() {
        measurements = []
        didTruncate = false
    }
}

enum WorkoutAudioCuePolicy {
	static func scheduledMoment(
		stepID: String,
		segmentName: String,
		initialCountdown: Int,
		intervalSecondsRemaining: Int,
		intervalDuration: TimeInterval? = nil,
		followingShortSegmentDurations: [TimeInterval] = [],
		isComplete: Bool,
		countdownKind: WorkoutCountdownKind? = nil
	) -> WorkoutAudioMoment? {
		if initialCountdown == 0,
		   let intervalDuration,
		   intervalDuration <= 3 {
			return nil
		}
		if initialCountdown == 0, intervalSecondsRemaining == 4, !isComplete {
			let schedule = CountdownAudioSchedule(remainingFrom: "3")
				.appendingShortIntervals(
					followingShortSegmentDurations,
					startingAt: 3
				)
			return WorkoutAudioMoment(
				key: "\(stepID)-\(segmentName)-3",
				phrase: "3",
				countdownSchedule: schedule
			)
		}
		return moment(
			stepID: stepID,
			segmentName: segmentName,
			initialCountdown: initialCountdown,
			intervalSecondsRemaining: intervalSecondsRemaining,
			isComplete: isComplete,
			countdownKind: countdownKind
		)
	}

	static func moment(
		stepID: String,
		segmentName: String,
		initialCountdown: Int,
		intervalSecondsRemaining: Int,
		isComplete: Bool,
		countdownKind: WorkoutCountdownKind? = nil
	) -> WorkoutAudioMoment? {
		guard !isComplete else { return nil }

		if (1...3).contains(initialCountdown) {
			return WorkoutAudioMoment(
				key: "\(countdownKind == .skip ? "skip" : "initial")-\(initialCountdown)",
				phrase: "\(initialCountdown)"
			)
		}

		guard (1...3).contains(intervalSecondsRemaining) else {
			return nil
		}

		return WorkoutAudioMoment(
			key: "\(stepID)-\(segmentName)-\(intervalSecondsRemaining)",
			phrase: "\(intervalSecondsRemaining)"
		)
	}

	static func action(
		previous: WorkoutAudioMoment?,
		current moment: WorkoutAudioMoment?,
		countdownStartUptime: TimeInterval?
	) -> WorkoutAudioCueAction {
		guard let moment else { return .none }
		guard let sequenceKey = numericSequenceKey(for: moment) else {
			return .speak(moment)
		}
		if let previous,
		   numericSequenceKey(for: previous) == sequenceKey {
			return .none
		}
		guard let countdownStartUptime else { return .none }
		return .startCountdown(
			schedule: moment.countdownSchedule
				?? CountdownAudioSchedule(remainingFrom: moment.phrase),
			startUptime: countdownStartUptime
		)
	}

	private static func numericSequenceKey(for moment: WorkoutAudioMoment) -> String? {
		guard ["3", "2", "1"].contains(moment.phrase) else { return nil }
		let suffix = "-\(moment.phrase)"
		guard moment.key.hasSuffix(suffix) else { return nil }
		return String(moment.key.dropLast(suffix.count))
	}
}

enum WorkoutCountdownIntervalPolicy {
	static func duration(
		for step: WorkoutStep,
		isTimedResting: Bool
	) -> TimeInterval {
		if step.phase == .rest {
			return step.duration
		}
		return isTimedResting
			? step.duration - step.activeDuration
			: step.activeDuration
	}

	static func shortDurations(
		in steps: [WorkoutStep],
		startingAt startElapsed: TimeInterval
	) -> [TimeInterval] {
		var cursor: TimeInterval = 0
		var result: [TimeInterval] = []
		var reachedStart = false

		for step in steps {
			let durations: [TimeInterval]
			if step.phase == .rest || !step.hasRestInterval {
				durations = [step.duration]
			} else {
				durations = [step.activeDuration, step.duration - step.activeDuration]
			}

			for duration in durations where duration > 0 {
				if !reachedStart {
					reachedStart = abs(cursor - startElapsed) < 0.001
				}
				if reachedStart {
					guard duration <= 3 else { return result }
					result.append(duration)
				}
				cursor += duration
			}
		}

		return result
	}
}

enum WorkoutSessionPolicy {
    static let initialCountdownDuration: TimeInterval = 3
    static let skipCountdownDuration: TimeInterval = 3

    static func countdownDuration(for kind: WorkoutCountdownKind) -> TimeInterval {
        kind == .initial ? initialCountdownDuration : skipCountdownDuration
    }

    static func shouldAutoStart(
        didAutoStart: Bool,
        isRunning: Bool,
        routineStartedAt: Date?
    ) -> Bool {
        !didAutoStart
            && !isRunning
            && isFirstStart(routineStartedAt: routineStartedAt)
    }

    static func isFirstStart(routineStartedAt: Date?) -> Bool {
        routineStartedAt == nil
    }

    static func isScaleTrackingReady(
        source: WorkoutInitialWeightSource,
        didCompleteInitialPreparation: Bool
    ) -> Bool {
        source == .sensor && didCompleteInitialPreparation
    }

    static func recordedForceSensorProfile(
        source: WorkoutInitialWeightSource,
        connectedProfile: ForceSensorProfile?,
        configuredProfile: ForceSensorProfile
    ) -> ForceSensorProfile {
        guard source == .sensor else { return .automatic }
        return connectedProfile ?? configuredProfile
    }

    static func shouldDeferCountdownStart(
        isFirstStart _: Bool,
        preparationState: CountdownAudioPreparationState
    ) -> Bool {
        preparationState == .preparing
    }

    enum PendingCountdownResolution: Equatable {
        case none
        case beginVisibly
        case requestAudioCountdown
    }

    static func shouldPrepareCountdownAudio(
        preparationState: CountdownAudioPreparationState
    ) -> Bool {
        preparationState == .idle || preparationState == .failed
    }

    static func consumePendingCountdown<Countdown>(
        _ pendingCountdown: inout Countdown?,
        afterPreparationState preparationState: CountdownAudioPreparationState
    ) -> PendingCountdownResolution {
        guard preparationState != .preparing, pendingCountdown != nil else {
            return .none
        }

        pendingCountdown = nil
        return preparationState == .failed ? .beginVisibly : .requestAudioCountdown
    }

    static func countdownAudioArmLead(environment: [String: String]) -> TimeInterval {
        #if DEBUG
        if environment["HANGTEN_REVIEW_COUNTDOWN_CAPTURE"] == "1" {
            return 5
        }
        #endif
        return 0.1
    }

    static func startDate(for kind: WorkoutCountdownKind, now: Date) -> Date {
        now.addingTimeInterval(countdownDuration(for: kind))
    }

    static func startUptime(for kind: WorkoutCountdownKind, at uptime: TimeInterval) -> TimeInterval {
        uptime + countdownDuration(for: kind)
    }

    static func countdownRemaining(startUptime: TimeInterval?, nowUptime: TimeInterval) -> Int {
        guard let startUptime, startUptime > nowUptime else { return 0 }
        return max(1, Int(ceil(startUptime - nowUptime)))
    }

    static func runStartDate(routineStartedAt: Date?, now: Date) -> Date {
        isFirstStart(routineStartedAt: routineStartedAt)
            ? startDate(for: .initial, now: now)
            : now
    }

    static func completedWorkoutInterval(
        sessionStartedAt: Date,
        planDuration: TimeInterval,
        elapsed: TimeInterval
    ) -> DateInterval {
        let activeElapsed = min(planDuration, max(0, elapsed))
        return DateInterval(
            start: sessionStartedAt,
            end: sessionStartedAt.addingTimeInterval(activeElapsed)
        )
    }

    static func completedWorkoutInterval(
        sessionStartedAt: Date,
        recordedAt: Date
    ) -> DateInterval {
        DateInterval(start: sessionStartedAt, end: max(sessionStartedAt, recordedAt))
    }

    static func isMeasurementEligible(
        routineStartedAt: Date?,
        measurementTimestamp: Date
    ) -> Bool {
        guard let routineStartedAt else { return false }
        return routineStartedAt <= measurementTimestamp
    }
}

struct WorkoutSessionState: Equatable {
    var activeStartUptime: TimeInterval?
    var countdownKind: WorkoutCountdownKind?
    var pausedElapsed: TimeInterval
    var routineStartedAt: Date?

    init(
        activeStartUptime: TimeInterval? = nil,
        countdownKind: WorkoutCountdownKind? = nil,
        pausedElapsed: TimeInterval = 0,
        routineStartedAt: Date? = nil
    ) {
        self.activeStartUptime = activeStartUptime
        self.countdownKind = countdownKind
        self.pausedElapsed = pausedElapsed
        self.routineStartedAt = routineStartedAt
    }

    func currentElapsed(planDuration: TimeInterval, at uptime: TimeInterval) -> TimeInterval {
        let activeElapsed = activeStartUptime.map { max(0, uptime - $0) } ?? 0
        return min(planDuration, pausedElapsed + max(0, activeElapsed))
    }

    func countdownRemaining(at uptime: TimeInterval) -> Int {
        pendingCountdownRemaining(at: uptime)
    }

    private func pendingCountdownRemaining(at uptime: TimeInterval) -> Int {
        guard countdownKind != nil else { return 0 }
        return WorkoutSessionPolicy.countdownRemaining(
            startUptime: activeStartUptime,
            nowUptime: uptime
        )
    }

    mutating func transitionExpiredCountdown(at uptime: TimeInterval) {
        guard countdownKind != nil, pendingCountdownRemaining(at: uptime) == 0 else { return }
        countdownKind = nil
    }

    func canNavigate(planDuration: TimeInterval, at uptime: TimeInterval) -> Bool {
        routineStartedAt != nil
            && pendingCountdownRemaining(at: uptime) == 0
            && currentElapsed(planDuration: planDuration, at: uptime) < planDuration
    }

    mutating func toggleRunning(uptime: TimeInterval, now: Date? = nil) {
        if let activeStartUptime {
            if activeStartUptime > uptime {
                cancelCountdown(at: uptime)
                return
            }
            pausedElapsed += max(0, uptime - activeStartUptime)
            self.activeStartUptime = nil
            countdownKind = nil
        } else {
            let isFirstStart = WorkoutSessionPolicy.isFirstStart(routineStartedAt: routineStartedAt)
            if isFirstStart {
                guard let now else { return }
                routineStartedAt = WorkoutSessionPolicy.startDate(for: .initial, now: now)
                activeStartUptime = WorkoutSessionPolicy.startUptime(for: .initial, at: uptime)
                countdownKind = .initial
            } else {
                activeStartUptime = uptime
                countdownKind = nil
            }
        }
    }

    mutating func cancelCountdown(at uptime: TimeInterval) {
        guard countdownKind != nil, countdownRemaining(at: uptime) > 0 else { return }

        switch countdownKind {
        case .skip:
            activeStartUptime = nil
            countdownKind = nil
        case .initial, nil:
            activeStartUptime = nil
            routineStartedAt = nil
            countdownKind = nil
        }
    }

    mutating func pauseForInterruption(at uptime: TimeInterval) {
        guard let activeStartUptime else {
            return
        }
        if activeStartUptime > uptime {
            cancelCountdown(at: uptime)
            return
        }

        pausedElapsed += max(0, uptime - activeStartUptime)
        self.activeStartUptime = nil
        countdownKind = nil
    }

    mutating func seek(to targetElapsed: TimeInterval, planDuration: TimeInterval, at uptime: TimeInterval) {
        let target = min(max(0, targetElapsed), planDuration)
        let wasActive = activeStartUptime != nil
        countdownKind = nil
        pausedElapsed = target
        if wasActive {
            activeStartUptime = uptime
        }
    }

    mutating func skipCurrentStep(timeline: WorkoutTimeline, planDuration: TimeInterval, at uptime: TimeInterval) -> Bool {
        guard canNavigate(planDuration: planDuration, at: uptime) else { return false }

        let elapsed = currentElapsed(planDuration: planDuration, at: uptime)
        guard let target = timeline.skipTarget(from: elapsed) else { return false }

        if target >= planDuration {
            seek(to: target, planDuration: planDuration, at: uptime)
        } else if timeline.step(at: target)?.phase == .rest {
            seek(to: target, planDuration: planDuration, at: uptime)
        } else {
            startSkipCountdown(to: target, at: uptime)
        }
        return true
    }

    mutating func startSkipCountdown(to targetElapsed: TimeInterval, at uptime: TimeInterval) {
        pausedElapsed = targetElapsed
        activeStartUptime = WorkoutSessionPolicy.startUptime(for: .skip, at: uptime)
        countdownKind = .skip
    }
}

enum WorkoutStopwatchLifecycle {
    static func finalizeStopwatches(
        for stepID: String,
        at monotonicTime: TimeInterval,
        in stopwatches: inout [WorkoutActivitySegmentKey: WorkoutStopwatch]
    ) {
        for key in stopwatches.keys where key.stepID == stepID {
            finalizeStopwatch(for: key, at: monotonicTime, in: &stopwatches)
        }
    }

    static func finalizeStopwatch(
        for key: WorkoutActivitySegmentKey,
        at monotonicTime: TimeInterval,
        in stopwatches: inout [WorkoutActivitySegmentKey: WorkoutStopwatch]
    ) {
        guard var stopwatch = stopwatches[key], !stopwatch.isFinalized else { return }
        stopwatch.stop(at: monotonicTime)
        stopwatches[key] = stopwatch
    }

    static func finalizeAndSnapshotStopwatches(
        at monotonicTime: TimeInterval,
        in stopwatches: inout [WorkoutActivitySegmentKey: WorkoutStopwatch]
    ) -> [WorkoutActivitySegmentKey: TimeInterval] {
        for key in stopwatches.keys {
            finalizeStopwatch(for: key, at: monotonicTime, in: &stopwatches)
        }

        return stopwatches.reduce(into: [WorkoutActivitySegmentKey: TimeInterval]()) { result, entry in
            guard entry.value.hasStarted, let elapsed = entry.value.elapsed(at: monotonicTime) else { return }
            result[entry.key] = elapsed
        }
    }
}
