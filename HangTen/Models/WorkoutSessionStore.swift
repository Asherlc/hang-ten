import Foundation

protocol WorkoutSessionStoring: AnyObject {
    var sessions: [WorkoutSessionRecord] { get }
    func append(_ session: WorkoutSessionRecord)
    func remove(_ session: WorkoutSessionRecord)
}

final class WorkoutSessionStore: WorkoutSessionStoring {
    private enum Key {
        static let sessionHistory = "workout.sessionHistory"
    }

    private static let maximumSessionCount = 20

    private let defaults: UserDefaults
    private let encoder: JSONEncoder
    private let decoder: JSONDecoder

    private(set) var sessions: [WorkoutSessionRecord]

    init(defaults: UserDefaults = .standard) {
        self.defaults = defaults
        encoder = JSONEncoder()
        decoder = JSONDecoder()
        sessions = Self.load(from: defaults, decoder: decoder)
    }

    func append(_ session: WorkoutSessionRecord) {
        sessions.removeAll { $0.id == session.id }
        sessions.append(session)
        sessions.sort(by: Self.isOrderedNewestFirst)
        sessions = Array(sessions.prefix(Self.maximumSessionCount))
        persist()
    }

    func remove(_ session: WorkoutSessionRecord) {
        sessions.removeAll { $0.id == session.id }
        persist()
    }

    private static func load(from defaults: UserDefaults, decoder: JSONDecoder) -> [WorkoutSessionRecord] {
        guard let data = defaults.data(forKey: Key.sessionHistory),
              let storedSessions = try? decoder.decode([WorkoutSessionRecord].self, from: data) else {
            return []
        }

        return Array(storedSessions.sorted(by: isOrderedNewestFirst).prefix(maximumSessionCount))
    }

    private static func isOrderedNewestFirst(_ lhs: WorkoutSessionRecord, _ rhs: WorkoutSessionRecord) -> Bool {
        if lhs.recordedAt != rhs.recordedAt {
            return lhs.recordedAt > rhs.recordedAt
        }
        return lhs.id.uuidString < rhs.id.uuidString
    }

    private func persist() {
        guard let data = try? encoder.encode(sessions) else { return }
        defaults.set(data, forKey: Key.sessionHistory)
    }
}
