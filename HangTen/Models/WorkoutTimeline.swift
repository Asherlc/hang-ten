import Foundation

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
