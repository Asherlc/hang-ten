import Foundation

enum WorkoutExercise: String, CaseIterable, Hashable, Identifiable {
    case hangs, pullUps, core
    var id: String { rawValue }
    var title: String {
        switch self {
        case .hangs: "Hangs"
        case .pullUps: "Pull-ups"
        case .core: "Core"
        }
    }
}

enum WorkoutDurationFilter: String, CaseIterable, Hashable, Identifiable {
    case any, underTenMinutes, tenToTwentyMinutes, twentyMinutesOrMore
    var id: String { rawValue }
    var title: String {
        switch self {
        case .any: "Any duration"
        case .underTenMinutes: "Under 10 minutes"
        case .tenToTwentyMinutes: "10–under 20 minutes"
        case .twentyMinutesOrMore: "20 minutes or more"
        }
    }
    func matches(_ duration: TimeInterval) -> Bool {
        switch self {
        case .any: true
        case .underTenMinutes: duration < 600
        case .tenToTwentyMinutes: duration >= 600 && duration < 1200
        case .twentyMinutesOrMore: duration >= 1200
        }
    }
}

struct WorkoutBrowserFilters: Equatable {
    var duration: WorkoutDurationFilter = .any
    var exercises: Set<WorkoutExercise> = []
    var levels: Set<String> = []

    var activeFacetCount: Int {
        (duration == .any ? 0 : 1) + (exercises.isEmpty ? 0 : 1) + (levels.isEmpty ? 0 : 1)
    }
    var isEmpty: Bool { activeFacetCount == 0 }

    func matches(_ plan: TrainingPlan, metadata: PlanMetadata?) -> Bool {
        duration.matches(plan.duration)
            && (exercises.isEmpty || !exercises.isDisjoint(with: plan.workoutExercises))
            && (levels.isEmpty || levels.contains(metadata?.level ?? plan.level))
    }

    mutating func clear() { self = Self() }
}

extension TrainingPlan {
    /// The legacy `pull` phase also contains knee raises and other core work.
    /// Match actual movement names, including source-authored conditioning rows,
    /// rather than treating that phase or the default action as pull-ups.
    var workoutExercises: Set<WorkoutExercise> {
        steps.reduce(into: []) { exercises, step in
            guard step.phase != .rest, step.phase != .coolDown else { return }
            let affirmativeInstruction = step.instruction.replacingOccurrences(
                of: #"\b(?:do not|don['’]t|never|no)\b(?:(?!,\s*(?:then|but|instead)\b)[^.!?;])*"#,
                with: "", options: [.regularExpression, .caseInsensitive]
            )
            let movement = Self.normalizedMovement(step.title + " " + affirmativeInstruction)
            if step.phase == .hang || movement.range(of: #"\b(?:dead-)?hangs?\b"#, options: .regularExpression) != nil {
                exercises.insert(.hangs)
            }
            if ["pull-up", "pull up", "pullup"].contains(where: movement.contains) {
                exercises.insert(.pullUps)
            }
            if ["knee raise", "leg raise", "l-sit", "l sit", "l-hang", "l hang", "front lever", "plank", "hollow", "flutter", "scissor kick", "bird dog", "sit-up", "sit up"].contains(where: movement.contains) {
                exercises.insert(.core)
            }
        }
    }

    /// Source guidance may retain a range while the adapted session chooses
    /// fixed timer defaults. Only executable timing and optional work affect
    /// whether the displayed session duration is an estimate.
    var hasEstimatedDuration: Bool {
        steps.contains { step in
            step.duration <= 0 || step.segments.contains { $0.timing != .fixed }
                || step.instruction.localizedCaseInsensitiveContains("optional")
        }
    }

    var browserDurationLabel: String {
        hasEstimatedDuration ? "Approx. \(durationLabel)" : durationLabel
    }

    func matchesWorkoutSearch(_ query: String, metadata: PlanMetadata?) -> Bool {
        let words = query.split(whereSeparator: \.isWhitespace)
        guard !words.isEmpty else { return true }
        let labels = metadata?.athleteFacingLabels ?? []
        let haystack = ([title, subtitle, level, metadata?.focus?.title ?? ""]
            + labels + workoutExercises.map(\.title)).joined(separator: " ")
        return words.allSatisfy {
            haystack.range(of: String($0), options: [.caseInsensitive, .diacriticInsensitive]) != nil
        }
    }

    private static func normalizedMovement(_ title: String) -> String {
        title.lowercased().replacingOccurrences(of: "‑", with: "-")
            .replacingOccurrences(of: "–", with: "-")
    }
}
