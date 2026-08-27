import Foundation

enum WorkoutLaunchDecision: Equatable {
    case allowed
    case requiresPurchase
}

final class WorkoutAccessStore {
    private enum Key {
        static let freeWorkoutsUsed = "HangTen.freeWorkoutsUsed.v1"
    }

    private let defaults: UserDefaults
    private let freeWorkoutLimit = 2

    init(defaults: UserDefaults = .standard) {
        self.defaults = defaults
    }

    var freeWorkoutsUsed: Int {
        min(defaults.integer(forKey: Key.freeWorkoutsUsed), freeWorkoutLimit)
    }

    func launchDecision(hasLifetimeEntitlement: Bool) -> WorkoutLaunchDecision {
        hasLifetimeEntitlement || freeWorkoutsUsed < freeWorkoutLimit ? .allowed : .requiresPurchase
    }

    func recordSavedFreeWorkout(hasLifetimeEntitlement: Bool) {
        guard !hasLifetimeEntitlement, freeWorkoutsUsed < freeWorkoutLimit else { return }
        defaults.set(freeWorkoutsUsed + 1, forKey: Key.freeWorkoutsUsed)
    }
}
