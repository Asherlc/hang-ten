import Foundation

/// One-shot conversion of the last legacy `FreeWorkoutDraft` into free-log history
/// so “Last workout” can prefill via `FreeWorkoutHistoryStore.latest` + `uncheckedClone()`.
///
/// **Seed shape:** migrate to an unchecked log, then mark every set completed with
/// `completedAt = startedAt` and `mode = nil`, and append that finished-shaped log
/// to history. Callers that start from last workout get an unchecked clone.
///
/// **Draft key:** after a successful seed, the draft is cleared
/// (`FreeWorkoutDraftStore.lastDraftKey`) so a restored draft does not keep
/// reappearing as a migration source.
///
/// **Idempotency:** no-ops when history already has entries, the draft is missing,
/// migration yields nothing, or `migratedFlagKey` is already set.
enum FreeWorkoutDraftMigration {
    /// Persisted once a successful seed (or an explicit skip after a failed migrate)
    /// has run, so subsequent launches do not re-read a restored draft.
    static let migratedFlagKey = "HangTen.freeWorkout.draftMigrated.v1"

    /// Result of `runIfNeeded` for tests and diagnostics.
    enum Outcome: Equatable {
        case skippedAlreadyMigrated
        case skippedHistoryExists
        case skippedNoDraft
        case skippedNothingMigratable
        case seeded(logID: UUID)
    }

    /// Seeds history from the last draft when appropriate. Clears the draft on
    /// successful seed. Safe to call on every Train / start-sheet appear.
    @discardableResult
    static func runIfNeeded(defaults: UserDefaults = .standard) -> Outcome {
        if defaults.bool(forKey: migratedFlagKey) {
            return .skippedAlreadyMigrated
        }
        if FreeWorkoutHistoryStore.latest(defaults: defaults) != nil {
            defaults.set(true, forKey: migratedFlagKey)
            return .skippedHistoryExists
        }
        guard let draft = FreeWorkoutDraftStore.load(defaults: defaults) else {
            return .skippedNoDraft
        }
        guard var log = FreeWorkoutLog.migrating(from: draft) else {
            // Rest-only / empty draft: mark done so we do not retry forever.
            defaults.set(true, forKey: migratedFlagKey)
            defaults.removeObject(forKey: FreeWorkoutDraftStore.lastDraftKey)
            return .skippedNothingMigratable
        }

        let startedAt = log.startedAt
        for exerciseIndex in log.exercises.indices {
            for setIndex in log.exercises[exerciseIndex].sets.indices {
                log.exercises[exerciseIndex].sets[setIndex].completedAt = startedAt
                log.exercises[exerciseIndex].sets[setIndex].mode = nil
            }
        }

        FreeWorkoutHistoryStore.append(log, defaults: defaults)
        defaults.removeObject(forKey: FreeWorkoutDraftStore.lastDraftKey)
        defaults.set(true, forKey: migratedFlagKey)
        return .seeded(logID: log.id)
    }

    /// Test helper: clears the migrated flag without touching history/draft.
    static func clearMigratedFlag(defaults: UserDefaults = .standard) {
        defaults.removeObject(forKey: migratedFlagKey)
    }
}
