import Foundation

struct WorkoutClock {
    static var monotonicTime: TimeInterval {
        ProcessInfo.processInfo.systemUptime
    }

    private let now: () -> TimeInterval
    private var pausedElapsed: TimeInterval = 0
    private var activeStart: TimeInterval?

    init(now: @escaping () -> TimeInterval = { WorkoutClock.monotonicTime }) {
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
        guard let activeStart else {
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

enum BoardHighlightMode: Hashable {
    case active
    case preview
}

struct WorkoutBoardCue: Equatable {
    let step: WorkoutStep?
    let mode: BoardHighlightMode
    let isResting: Bool
    let isSuppressed: Bool
}

struct WorkoutHoldCue: Equatable {
    let hold: BoardHold
    let gripType: GripType
}

enum WorkoutHoldCuePolicy {
    static func resolve(
        step: WorkoutStep?,
        hold: BoardHold?,
        on board: TrainingBoard
    ) -> WorkoutHoldCue? {
        guard let step,
              step.targets.count == 1,
              let target = step.targets.first,
              let hold,
              BoardTargetResolver.resolveHoldIDs(for: target, on: board).contains(hold.id)
        else {
            return nil
        }

        return WorkoutHoldCue(
            hold: hold,
            gripType: step.gripType ?? hold.gripType
        )
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

    func nextWorkStep(after stepID: String) -> WorkoutStep? {
        guard let index = steps.firstIndex(where: { $0.id == stepID }) else {
            return nil
        }

        return steps.dropFirst(index + 1).first { $0.phase != .rest }
    }

    func holdPreviewStep(at elapsed: TimeInterval) -> WorkoutStep? {
        guard let currentStep = step(at: elapsed) else {
            return nil
        }

        return holdPreviewStep(
            currentStep: currentStep,
            stepElapsed: elapsedInStep(at: elapsed)
        )
    }

    func boardCue(
        at elapsed: TimeInterval,
        countdown: Int,
        isComplete: Bool,
        isSkipCountdown: Bool = false
    ) -> WorkoutBoardCue {
        boardCue(
            currentStep: step(at: elapsed),
            stepElapsed: elapsedInStep(at: elapsed),
            countdown: countdown,
            isComplete: isComplete,
            isSkipCountdown: isSkipCountdown
        )
    }

    func boardCue(
        currentStep: WorkoutStep?,
        stepElapsed: TimeInterval,
        countdown: Int,
        isComplete: Bool,
        isSkipCountdown: Bool = false
    ) -> WorkoutBoardCue {
        guard !isComplete,
              (countdown == 0 || (countdown > 0 && isSkipCountdown)),
              let currentStep else {
            return WorkoutBoardCue(
                step: nil,
                mode: .active,
                isResting: false,
                isSuppressed: true
            )
        }

        let resolvedStep = holdPreviewStep(
            currentStep: currentStep,
            stepElapsed: stepElapsed
        )

        if countdown > 0 {
            return WorkoutBoardCue(
                step: resolvedStep,
                mode: .preview,
                isResting: resolvedStep?.phase == .rest,
                isSuppressed: false
            )
        }

        let isResting = currentStep.phase == .rest
            || (currentStep.hasRestInterval && stepElapsed >= currentStep.activeDuration)

        return WorkoutBoardCue(
            step: resolvedStep,
            mode: isResting ? .preview : .active,
            isResting: isResting,
            isSuppressed: false
        )
    }

    func holdPreviewStep(
        currentStep: WorkoutStep,
        stepElapsed: TimeInterval
    ) -> WorkoutStep? {
        let isResting = currentStep.phase == .rest
            || (currentStep.hasRestInterval && stepElapsed >= currentStep.activeDuration)

        return isResting
            ? nextWorkStep(after: currentStep.id)
            : currentStep
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
