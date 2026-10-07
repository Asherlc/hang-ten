import Foundation

/// A presentation of contiguous source steps. Workout execution continues to
/// use the original steps, including every repeated work and rest interval.
struct PlanFlowGroup: Identifiable {
    let sourceSteps: [WorkoutStep]
    let repeatCount: Int
    let children: [PlanFlowGroup]
    let title: String
    let nextInstruction: String?

    var id: String { sourceSteps[0].id }
    var duration: TimeInterval { sourceSteps.reduce(0) { $0 + $1.duration } }

    var durationLabel: String {
        let seconds = Int(duration)
        let minutes = seconds / 60
        let remainder = seconds % 60
        if minutes == 0 { return "\(remainder)s" }
        if remainder == 0 { return "\(minutes)m" }
        return "\(minutes)m \(remainder)s"
    }
}

enum PlanFlowPresentation {
    static func groups(for plan: TrainingPlan) -> [PlanFlowGroup] {
        groups(for: plan.steps, repeats: plan.stepRepeats)
    }

    static func groups(for steps: [WorkoutStep], repeats: [WorkoutStepRepeat] = []) -> [PlanFlowGroup] {
        var nextInstructions = [String?](repeating: nil, count: steps.count)
        var upcomingInstruction: String?
        for index in steps.indices.reversed() {
            if steps[index].isRestStep {
                nextInstructions[index] = upcomingInstruction
            } else {
                let instruction = steps[index].instruction.trimmingCharacters(in: .whitespacesAndNewlines)
                upcomingInstruction = instruction.isEmpty ? nil : instruction
            }
        }

        // Ranges come from authored block references. Invalid/stale metadata
        // falls back to individual intervals, preserving every runtime step.
        var repeatsByStart: [Int: WorkoutStepRepeat] = [:]
        var previousEnd = 0
        for item in repeats.sorted(by: { $0.stepRange.lowerBound < $1.stepRange.lowerBound }) {
            guard item.repeatCount > 1,
                  item.stepRange.lowerBound >= previousEnd,
                  item.stepRange.upperBound <= steps.count,
                  !item.stepRange.isEmpty,
                  item.stepRange.count % item.repeatCount == 0,
                  item.patternTitles.isEmpty || item.patternTitles.count == item.patternStepCount else { continue }
            repeatsByStart[item.stepRange.lowerBound] = item
            previousEnd = item.stepRange.upperBound
        }

        var groups: [PlanFlowGroup] = []
        var index = 0
        while index < steps.count {
            if let item = repeatsByStart[index] {
                let children = (0..<item.patternStepCount).map { offset in
                    let childIndex = index + offset
                    let nextInstruction = nextInstructions[childIndex]
                    // A final recovery can lead to a different grip. Show an
                    // upcoming instruction only when it applies to every run.
                    let sameNextInstruction = (0..<item.repeatCount).allSatisfy {
                        nextInstructions[childIndex + $0 * item.patternStepCount] == nextInstruction
                    }
                    return PlanFlowGroup(
                        sourceSteps: [steps[childIndex]], repeatCount: 1, children: [],
                        title: item.patternTitles.isEmpty ? steps[childIndex].title : item.patternTitles[offset],
                        nextInstruction: sameNextInstruction ? nextInstruction : nil
                    )
                }
                groups.append(PlanFlowGroup(
                    sourceSteps: Array(steps[item.stepRange]), repeatCount: item.repeatCount, children: children,
                    title: children[0].title, nextInstruction: nextInstructions[index]
                ))
                index = item.stepRange.upperBound
            } else {
                groups.append(PlanFlowGroup(
                    sourceSteps: [steps[index]], repeatCount: 1, children: [],
                    title: steps[index].title, nextInstruction: nextInstructions[index]
                ))
                index += 1
            }
        }
        return groups
    }
}
