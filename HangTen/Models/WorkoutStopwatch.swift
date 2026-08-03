import Foundation

struct WorkoutStopwatch: Equatable {
    private var accumulatedElapsed: TimeInterval = 0
    private var anchor: TimeInterval?
    private var started = false
    private var finalized = false

    var isRunning: Bool {
        !finalized && anchor != nil
    }

    var isFinalized: Bool {
        finalized
    }

    var hasStarted: Bool {
        started
    }

    func elapsed(at monotonicTime: TimeInterval) -> TimeInterval? {
        guard started else { return nil }
        guard let anchor else { return accumulatedElapsed }

        return accumulatedElapsed + max(0, monotonicTime - anchor)
    }

    mutating func start(at monotonicTime: TimeInterval) {
        guard !finalized, anchor == nil else { return }

        started = true
        anchor = monotonicTime
    }

    mutating func pause(at monotonicTime: TimeInterval) {
        guard !finalized, let anchor else { return }

        accumulatedElapsed += max(0, monotonicTime - anchor)
        self.anchor = nil
    }

    mutating func stop(at monotonicTime: TimeInterval) {
        guard !finalized else { return }

        if let anchor {
            accumulatedElapsed += max(0, monotonicTime - anchor)
            self.anchor = nil
        }
        finalized = true
    }
}
