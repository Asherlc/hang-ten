import Foundation

/// Pure rest-countdown state for free workout log mode.
/// Rest is UI chrome, not a workout step; this type holds no UIKit/SwiftUI.
struct FreeWorkoutRestTimer: Equatable {
    enum Phase: Equatable {
        case inactive
        case running(endsAt: Date)
        case completed
    }

    private(set) var phase: Phase = .inactive

    var isActive: Bool {
        if case .running = phase { return true }
        return false
    }

    var isCompleted: Bool {
        if case .completed = phase { return true }
        return false
    }

    /// Starts a countdown of `duration` seconds from `now`.
    /// Non-positive durations complete immediately.
    mutating func start(duration: TimeInterval, at now: Date = Date()) {
        let clamped = max(0, duration)
        if clamped == 0 {
            phase = .completed
            return
        }
        phase = .running(endsAt: now.addingTimeInterval(clamped))
    }

    /// Remaining seconds until `endsAt`, clamped at 0. Inactive/completed → 0.
    func remaining(at now: Date) -> TimeInterval {
        guard case let .running(endsAt) = phase else { return 0 }
        return max(0, endsAt.timeIntervalSince(now))
    }

    /// Transitions to `.completed` when remaining has hit 0.
    mutating func tick(at now: Date) {
        guard case let .running(endsAt) = phase else { return }
        if endsAt.timeIntervalSince(now) <= 0 {
            phase = .completed
        }
    }

    mutating func skip() {
        phase = .inactive
    }

    mutating func dismiss() {
        phase = .inactive
    }

    /// Adjusts remaining by `delta` (e.g. −30 / +30 / +60). Clamps at 0 → completed.
    mutating func adjust(by delta: TimeInterval, at now: Date = Date()) {
        guard case let .running(endsAt) = phase else { return }
        let newRemaining = max(0, endsAt.timeIntervalSince(now) + delta)
        if newRemaining == 0 {
            phase = .completed
        } else {
            phase = .running(endsAt: now.addingTimeInterval(newRemaining))
        }
    }

    mutating func subtract30(at now: Date = Date()) {
        adjust(by: -30, at: now)
    }

    mutating func add30(at now: Date = Date()) {
        adjust(by: 30, at: now)
    }

    mutating func add60(at now: Date = Date()) {
        adjust(by: 60, at: now)
    }
}
