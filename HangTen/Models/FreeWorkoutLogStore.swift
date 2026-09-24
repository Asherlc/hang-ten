import Foundation

// MARK: - Shared DEBUG reset

enum FreeWorkoutLogPersistence {
    /// Same review env flag as `FreeWorkoutDraftStore`; clears active / history / templates.
    static let reviewResetEnvironmentKey = "HANGTEN_REVIEW_RESET_FREE_WORKOUT"

    /// Process-local latch so UITest reset runs once per launch, not on every `load()`.
    private static var didResetThisProcess = false

    static func shouldResetForReview() -> Bool {
        #if DEBUG
        ProcessInfo.processInfo.environment[reviewResetEnvironmentKey] == "1"
        #else
        false
        #endif
    }

    /// Clears free-workout UserDefaults keys once when the review reset env is set.
    /// Safe to call from every store `load()` — subsequent calls are no-ops.
    static func resetForReviewIfNeeded(defaults: UserDefaults = .standard) {
        guard shouldResetForReview(), !didResetThisProcess else { return }
        didResetThisProcess = true
        defaults.removeObject(forKey: ActiveFreeWorkoutStore.key)
        defaults.removeObject(forKey: FreeWorkoutHistoryStore.key)
        defaults.removeObject(forKey: FreeWorkoutTemplateStore.key)
    }

    /// Strips set completion without regenerating IDs (stable template body).
    static func uncheckedInPlace(_ log: FreeWorkoutLog) -> FreeWorkoutLog {
        var copy = log
        for exerciseIndex in copy.exercises.indices {
            for setIndex in copy.exercises[exerciseIndex].sets.indices {
                copy.exercises[exerciseIndex].sets[setIndex].completedAt = nil
                copy.exercises[exerciseIndex].sets[setIndex].mode = nil
            }
        }
        return copy
    }
}

// MARK: - Active log

/// Single in-progress free workout log. Call `save` after every mutation (write-through).
enum ActiveFreeWorkoutStore {
    static let key = "HangTen.freeWorkout.activeLog.v1"

    static func load(defaults: UserDefaults = .standard) -> FreeWorkoutLog? {
        FreeWorkoutLogPersistence.resetForReviewIfNeeded(defaults: defaults)
        guard let data = defaults.data(forKey: key) else { return nil }
        return try? JSONDecoder().decode(FreeWorkoutLog.self, from: data)
    }

    static func save(_ log: FreeWorkoutLog, defaults: UserDefaults = .standard) {
        guard let data = try? JSONEncoder().encode(log) else { return }
        defaults.set(data, forKey: key)
    }

    static func clear(defaults: UserDefaults = .standard) {
        defaults.removeObject(forKey: key)
    }
}

// MARK: - History

/// Finished free logs, newest-first. Corrupt payloads decode as empty (no throw).
enum FreeWorkoutHistoryStore {
    static let key = "HangTen.freeWorkout.history.v1"

    static func load(defaults: UserDefaults = .standard) -> [FreeWorkoutLog] {
        FreeWorkoutLogPersistence.resetForReviewIfNeeded(defaults: defaults)
        guard let data = defaults.data(forKey: key) else { return [] }
        return (try? JSONDecoder().decode([FreeWorkoutLog].self, from: data)) ?? []
    }

    /// Prepends `log` so `latest` / `load().first` is the most recently finished workout.
    static func append(_ log: FreeWorkoutLog, defaults: UserDefaults = .standard) {
        var logs = load(defaults: defaults)
        logs.insert(log, at: 0)
        guard let data = try? JSONEncoder().encode(logs) else { return }
        defaults.set(data, forKey: key)
    }

    static func latest(defaults: UserDefaults = .standard) -> FreeWorkoutLog? {
        load(defaults: defaults).first
    }

    static func clear(defaults: UserDefaults = .standard) {
        defaults.removeObject(forKey: key)
    }
}

// MARK: - Templates

/// Named reusable log shape. Body should be unchecked sets.
///
/// Callers creating a template from a finished workout should pass
/// `finishedLog().templateClone()` (new IDs, cleared completion). This store also
/// normalizes on save by clearing `completedAt` / `mode` in place so completion
/// state is never persisted even if a caller omits the clone step.
struct FreeWorkoutTemplate: Codable, Hashable, Identifiable {
    var id: UUID
    var name: String
    var log: FreeWorkoutLog

    init(id: UUID = UUID(), name: String, log: FreeWorkoutLog) {
        self.id = id
        self.name = name
        self.log = log
    }
}

enum FreeWorkoutTemplateStore {
    static let key = "HangTen.freeWorkout.templates.v1"

    static func load(defaults: UserDefaults = .standard) -> [FreeWorkoutTemplate] {
        FreeWorkoutLogPersistence.resetForReviewIfNeeded(defaults: defaults)
        guard let data = defaults.data(forKey: key) else { return [] }
        return (try? JSONDecoder().decode([FreeWorkoutTemplate].self, from: data)) ?? []
    }

    /// Upserts by `id`. Normalizes the log body to unchecked sets (IDs preserved).
    static func save(_ template: FreeWorkoutTemplate, defaults: UserDefaults = .standard) {
        var normalized = template
        normalized.log = FreeWorkoutLogPersistence.uncheckedInPlace(template.log)
        var templates = load(defaults: defaults)
        if let index = templates.firstIndex(where: { $0.id == normalized.id }) {
            templates[index] = normalized
        } else {
            templates.append(normalized)
        }
        guard let data = try? JSONEncoder().encode(templates) else { return }
        defaults.set(data, forKey: key)
    }

    static func delete(id: UUID, defaults: UserDefaults = .standard) {
        var templates = load(defaults: defaults)
        templates.removeAll { $0.id == id }
        guard let data = try? JSONEncoder().encode(templates) else { return }
        defaults.set(data, forKey: key)
    }

    static func template(id: UUID, defaults: UserDefaults = .standard) -> FreeWorkoutTemplate? {
        load(defaults: defaults).first { $0.id == id }
    }

    static func clear(defaults: UserDefaults = .standard) {
        defaults.removeObject(forKey: key)
    }
}
