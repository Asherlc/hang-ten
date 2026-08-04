import Foundation

protocol WorkoutHistoryPersistence: AnyObject {
    func load() -> [PendingWorkoutRecord]
    func replace(_ records: [PendingWorkoutRecord])
}

final class LocalWorkoutHistoryStore: WorkoutHistoryPersistence {
    static let defaultKey = "HangTen.pendingWorkoutHistory.v1"

    private let defaults: UserDefaults
    private let key: String

    init(
        defaults: UserDefaults = .standard,
        key: String = LocalWorkoutHistoryStore.defaultKey
    ) {
        self.defaults = defaults
        self.key = key
    }

    deinit {}

    func load() -> [PendingWorkoutRecord] {
        guard let data = defaults.data(forKey: key) else { return [] }
        return (try? JSONDecoder().decode([PendingWorkoutRecord].self, from: data)) ?? []
    }

    func replace(_ records: [PendingWorkoutRecord]) {
        guard let data = try? JSONEncoder().encode(records) else { return }
        defaults.set(data, forKey: key)
    }
}
