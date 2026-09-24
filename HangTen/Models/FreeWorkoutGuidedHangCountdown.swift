import Foundation

/// Pure hang-countdown state for free-workout guided sets.
/// Mirrors `FreeWorkoutRestTimer`: injectable clock, no UIKit/SwiftUI.
struct FreeWorkoutGuidedHangCountdown: Equatable {
    /// Used when the focused set has no duration configured.
    static let defaultDuration: TimeInterval = 10

    enum Phase: Equatable {
        case idle
        case running(endsAt: Date)
        case paused(remaining: TimeInterval)
        case completed
    }

    private(set) var phase: Phase = .idle
    private(set) var plannedDuration: TimeInterval = 0

    var isRunning: Bool {
        if case .running = phase { return true }
        return false
    }

    var isPaused: Bool {
        if case .paused = phase { return true }
        return false
    }

    var isCompleted: Bool {
        if case .completed = phase { return true }
        return false
    }

    /// Resolves a set duration, falling back to `defaultDuration`.
    static func resolvedDuration(_ duration: TimeInterval?) -> TimeInterval {
        let value = duration ?? defaultDuration
        return max(1, value)
    }

    /// Starts a hang countdown of `duration` seconds from `now`.
    mutating func start(duration: TimeInterval, at now: Date = Date()) {
        let clamped = max(1, duration)
        plannedDuration = clamped
        phase = .running(endsAt: now.addingTimeInterval(clamped))
    }

    func remaining(at now: Date) -> TimeInterval {
        switch phase {
        case .idle, .completed:
            return 0
        case let .paused(remaining):
            return max(0, remaining)
        case let .running(endsAt):
            return max(0, endsAt.timeIntervalSince(now))
        }
    }

    /// Elapsed hang time for the current attempt (planned − remaining).
    func elapsed(at now: Date) -> TimeInterval {
        guard plannedDuration > 0 else { return 0 }
        return max(0, plannedDuration - remaining(at: now))
    }

    mutating func tick(at now: Date) {
        guard case let .running(endsAt) = phase else { return }
        if endsAt.timeIntervalSince(now) <= 0 {
            phase = .completed
        }
    }

    mutating func pause(at now: Date = Date()) {
        guard case .running = phase else { return }
        phase = .paused(remaining: remaining(at: now))
    }

    mutating func resume(at now: Date = Date()) {
        guard case let .paused(remaining) = phase else { return }
        if remaining <= 0 {
            phase = .completed
        } else {
            phase = .running(endsAt: now.addingTimeInterval(remaining))
        }
    }

    /// Marks the hang finished early (or at natural end).
    mutating func complete() {
        phase = .completed
    }

    mutating func cancel() {
        phase = .idle
        plannedDuration = 0
    }

    /// Delay from `now` until the 3-2-1 audio should start, and the schedule to play.
    /// Returns `nil` when remaining is too short for numeric cues (≤0) or when the
    /// original planned duration was ≤3 (matching `WorkoutAudioCuePolicy`).
    static func endCountdownAudio(
        plannedDuration: TimeInterval,
        remaining: TimeInterval
    ) -> (schedule: CountdownAudioSchedule, delay: TimeInterval)? {
        guard plannedDuration > 3, remaining > 0 else { return nil }

        if remaining > 3 {
            return (CountdownAudioSchedule(remainingFrom: "3"), remaining - 3)
        }

        let firstNumber = min(3, max(1, Int(ceil(remaining))))
        return (CountdownAudioSchedule(remainingFrom: String(firstNumber)), 0)
    }
}
