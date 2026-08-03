import Foundation

struct WorkoutClock {
    private let now: () -> TimeInterval
    private var pausedElapsed: TimeInterval = 0
    private var activeStart: TimeInterval?

    init(now: @escaping () -> TimeInterval = { ProcessInfo.processInfo.systemUptime }) {
        self.now = now
    }

    var isRunning: Bool {
        activeStart != nil
    }

    var elapsed: TimeInterval {
        let activeElapsed = activeStart.map { max(0, now() - $0) } ?? 0
        return pausedElapsed + activeElapsed
    }

    var countdownRemaining: Int {
        guard pausedElapsed == 0, let activeStart else {
            return 0
        }

        let remaining = activeStart - now()
        guard remaining > 0 else {
            return 0
        }
        return max(1, Int(ceil(remaining)))
    }

    mutating func start(initialCountdown: TimeInterval) {
        guard activeStart == nil else {
            return
        }
        activeStart = now() + max(0, initialCountdown)
    }

    mutating func pause() {
        pausedElapsed = elapsed
        activeStart = nil
    }

    mutating func reset() {
        pausedElapsed = 0
        activeStart = nil
    }

    mutating func seek(to elapsed: TimeInterval) {
        pausedElapsed = max(0, elapsed)
        if activeStart != nil {
            activeStart = now()
        }
    }
}

struct WorkoutTimeline {
    private let steps: [WorkoutStep]
    private let startOffsets: [TimeInterval]

    init(steps: [WorkoutStep]) {
        self.steps = steps

        var cursor: TimeInterval = 0
        self.startOffsets = steps.map { step in
            defer { cursor += step.duration }
            return cursor
        }
        self.duration = cursor
    }

    let duration: TimeInterval

    func step(at elapsed: TimeInterval) -> WorkoutStep? {
        guard let location = location(at: elapsed) else {
            return nil
        }
        return steps[location.index]
    }

    func elapsedInStep(at elapsed: TimeInterval) -> TimeInterval {
        guard let location = location(at: elapsed) else {
            return 0
        }

        let stepDuration = steps[location.index].duration
        return min(max(0, clampedElapsed(elapsed) - location.start), stepDuration)
    }

    func startOffset(for stepID: String) -> TimeInterval? {
        guard let index = steps.firstIndex(where: { $0.id == stepID }) else {
            return nil
        }
        return startOffsets[index]
    }

    func selectionTarget(for stepID: String, at elapsed: TimeInterval) -> TimeInterval? {
        guard step(at: elapsed)?.id != stepID else {
            return nil
        }
        return startOffset(for: stepID)
    }

    func skipTarget(from elapsed: TimeInterval) -> TimeInterval? {
        guard let location = location(at: elapsed) else {
            return nil
        }

        let stepEnd = location.start + steps[location.index].duration
        return min(stepEnd, duration)
    }

    private func clampedElapsed(_ elapsed: TimeInterval) -> TimeInterval {
        min(max(0, elapsed), duration)
    }

    private func location(at elapsed: TimeInterval) -> (index: Int, start: TimeInterval)? {
        guard !steps.isEmpty else {
            return nil
        }

        let clamped = clampedElapsed(elapsed)
        for index in steps.indices {
            let start = startOffsets[index]
            let end = start + steps[index].duration
            if clamped < end {
                return (index, start)
            }
        }

        let finalIndex = steps.index(before: steps.endIndex)
        return (finalIndex, startOffsets[finalIndex])
    }
}
