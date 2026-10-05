import Foundation

struct PlanFilters: Equatable {
    var levels: Set<String> = []
    var provenances: Set<RoutineProvenance> = []
    var categories: Set<String> = []
    var tags: Set<String> = []

    var isEmpty: Bool { activeFacetCount == 0 }

    var activeFacetCount: Int {
        [levels.isEmpty, provenances.isEmpty, categories.isEmpty, tags.isEmpty]
            .filter { !$0 }
            .count
    }

    func matches(_ metadata: PlanMetadata) -> Bool {
        (levels.isEmpty || levels.contains(metadata.level)) &&
        (provenances.isEmpty || provenances.contains(metadata.provenance)) &&
        (categories.isEmpty || categories.contains(metadata.category)) &&
        (tags.isEmpty || !tags.isDisjoint(with: metadata.athleteFacingLabels))
    }

    mutating func clear() {
        levels.removeAll()
        provenances.removeAll()
        categories.removeAll()
        tags.removeAll()
    }

    mutating func toggle(level: String) { levels = Self.toggled(level, in: levels) }
    mutating func toggle(provenance: RoutineProvenance) { provenances = Self.toggled(provenance, in: provenances) }
    mutating func toggle(category: String) { categories = Self.toggled(category, in: categories) }
    mutating func toggle(tag: String) { tags = Self.toggled(tag, in: tags) }

    private static func toggled<Value: Hashable>(_ value: Value, in values: Set<Value>) -> Set<Value> {
        var toggledValues = values
        if !toggledValues.insert(value).inserted {
            toggledValues.remove(value)
        }
        return toggledValues
    }
}

struct PlanFilterOptions: Hashable {
    let levels: [String]
    let provenances: [RoutineProvenance]
    let categories: [String]
    let tags: [String]

    init(metadata: [PlanMetadata]) {
        levels = Self.sortedUnique(metadata.map(\.level))
        provenances = Array(Set(metadata.map(\.provenance))).sorted { $0.label < $1.label }
        categories = Self.sortedUnique(metadata.map(\.category))
        tags = Self.sortedUnique(metadata.flatMap(\.athleteFacingLabels))
    }

    private static func sortedUnique(_ values: [String]) -> [String] {
        Array(Set(values)).sorted {
            $0.localizedCaseInsensitiveCompare($1) == .orderedAscending
        }
    }
}



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
                of: #"\b(?:do not|don['’]t|never|no)\b[^.!?]*"#,
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

    var hasEstimatedDuration: Bool {
        steps.contains { step in
            step.duration <= 0 || step.segments.contains { $0.timing != .fixed }
                || step.instruction.localizedCaseInsensitiveContains("optional")
                || step.instruction.range(
                    of: #"\d+\s*[–-]\s*\d+\s*(?:seconds?|minutes?|s\b|m\b)"#,
                    options: [.regularExpression, .caseInsensitive]
                ) != nil
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
