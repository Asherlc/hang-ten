import Foundation

/// A presentation of contiguous source steps. Workout execution continues to
/// use the original steps, including every repeated work and rest interval.
struct PlanFlowGroup: Identifiable {
    let sourceSteps: [WorkoutStep]
    let repeatCount: Int
    let children: [PlanFlowGroup]
    let title: String

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
    static func groups(for steps: [WorkoutStep]) -> [PlanFlowGroup] {
        let prescriptions = steps.map(prescription)
        return groups(in: steps.indices, steps: steps, prescriptions: prescriptions, isRepeated: false)
    }

    private static func groups(
        in range: Range<Int>,
        steps: [WorkoutStep],
        prescriptions: [WorkoutStep],
        isRepeated: Bool
    ) -> [PlanFlowGroup] {
        var result: [PlanFlowGroup] = []
        var start = range.lowerBound

        while start < range.upperBound {
            let remaining = range.upperBound - start
            var patternLength = 1
            var repeatCount = 1
            var savedRows = 0

            if remaining >= 2 {
                // Prefer the sequence that removes the most duplicate rows.
                // Ties retain the shortest pattern, keeping simple repeats clear.
                for length in 1...(remaining / 2) {
                    guard remaining - length > savedRows else { break }
                    let pattern = prescriptions[start..<(start + length)]
                    var count = 1
                    while start + (count + 1) * length <= range.upperBound,
                          pattern.elementsEqual(
                            prescriptions[(start + count * length)..<(start + (count + 1) * length)]
                          ) {
                        count += 1
                    }
                    let savings = (count - 1) * length
                    if savings > savedRows {
                        patternLength = length
                        repeatCount = count
                        savedRows = savings
                    }
                }
            }

            let end = start + patternLength * repeatCount
            let children = repeatCount > 1
                ? groups(
                    in: start..<(start + patternLength), steps: steps,
                    prescriptions: prescriptions, isRepeated: true
                )
                : []
            result.append(PlanFlowGroup(
                sourceSteps: Array(steps[start..<end]),
                repeatCount: repeatCount,
                children: children,
                title: isRepeated ? prescriptions[start].title : steps[start].title
            ))
            start = end
        }
        return result
    }

    /// Only explicit position counters are presentation-only. Numbers in hold
    /// sizes, durations, exercise counts, and optional cues remain meaningful.
    private static func titleWithoutPositionCounters(_ title: String) -> String {
        let counter = #"^(?:set|rep|round|effort|interval) [1-9][0-9]*(?: of [1-9][0-9]*)?$"#
        let components = title.components(separatedBy: " · ").compactMap { component -> String? in
            let phrases = component.components(separatedBy: ", ").compactMap { phrase -> String? in
                if phrase.range(of: counter, options: [.regularExpression, .caseInsensitive]) != nil {
                    return nil
                }
                return phrase.replacingOccurrences(
                    of: #"^(minute|ladder) [1-9][0-9]*( rest)?$"#,
                    with: "$1$2", options: [.regularExpression, .caseInsensitive]
                )
            }
            return phrases.isEmpty ? nil : phrases.joined(separator: ", ")
        }
        return components.isEmpty
            ? title.components(separatedBy: " ")[0]
            : components.joined(separator: " · ")
    }

    /// Compare the complete prescription, excluding only its identity, position,
    /// and explicit title counters. No instruction or accessory text is rewritten.
    private static func prescription(for step: WorkoutStep) -> WorkoutStep {
        WorkoutStep(
            id: "", number: 0, title: titleWithoutPositionCounters(step.title),
            instruction: step.instruction, accessory: step.accessory,
            duration: step.duration, phase: step.phase, segments: step.segments,
            gripType: step.gripType, fingerConfiguration: step.fingerConfiguration,
            handUse: step.handUse, side: step.side, action: step.action,
            repetitions: step.repetitions, externalLoadKGF: step.externalLoadKGF,
            timedWorkDuration: step.timedWorkDuration
        )
    }
}
