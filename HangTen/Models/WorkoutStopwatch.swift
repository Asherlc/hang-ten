import Foundation

struct WorkoutStopwatch: Equatable {
    private var accumulatedElapsed: TimeInterval = 0
    private var anchor: Date?
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

    func elapsed(at date: Date) -> TimeInterval? {
        guard started else { return nil }
        guard let anchor else { return accumulatedElapsed }

        return accumulatedElapsed + max(0, date.timeIntervalSince(anchor))
    }

    mutating func start(at date: Date) {
        guard !finalized, anchor == nil else { return }

        started = true
        anchor = date
    }

    mutating func pause(at date: Date) {
        guard !finalized, let anchor else { return }

        accumulatedElapsed += max(0, date.timeIntervalSince(anchor))
        self.anchor = nil
    }

    mutating func stop(at date: Date) {
        guard !finalized else { return }

        if let anchor {
            accumulatedElapsed += max(0, date.timeIntervalSince(anchor))
            self.anchor = nil
        }
        finalized = true
    }
}
