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
    private let directory: URL
    private let fileManager: FileManager
    private let persistenceQueue = DispatchQueue(
        label: "com.hangten.workout-session-store",
        qos: .utility
    )
    private let persistenceErrorLock = NSLock()
    private var persistenceErrorStorage: String?

    private(set) var sessions: [WorkoutSessionRecord]

    var persistenceError: String? {
        persistenceErrorLock.lock()
        defer { persistenceErrorLock.unlock() }
        return persistenceErrorStorage
    }

    init(
        defaults: UserDefaults = .standard,
        directory: URL? = nil,
        fileManager: FileManager = .default
    ) {
        self.defaults = defaults
        self.fileManager = fileManager
        encoder = JSONEncoder()
        decoder = JSONDecoder()
        self.directory = directory ?? Self.defaultDirectory(using: fileManager)

        let loaded = Self.load(from: self.directory, decoder: decoder, fileManager: fileManager)
        sessions = loaded.sessions
        persistenceErrorStorage = loaded.errorDescription

        guard !loaded.fileStoreExists else { return }
        let legacySessions = Self.loadLegacy(from: defaults, decoder: decoder)
        sessions = legacySessions
        if legacySessions.isEmpty {
            defaults.removeObject(forKey: Key.sessionHistory)
        } else {
            migrateLegacyHistory(legacySessions)
        }
    }

    func append(_ session: WorkoutSessionRecord) {
        let previousSessions = sessions
        sessions.removeAll { $0.id == session.id }
        sessions.append(session)
        sessions.sort(by: Self.isOrderedNewestFirst)
        sessions = Array(sessions.prefix(Self.maximumSessionCount))

        let retainedIDs = Set(sessions.map(\.id))
        let removedIDs = Set(previousSessions.map(\.id)).subtracting(retainedIDs)
        enqueueWrite(sessions: [session], removing: removedIDs)
    }

    func remove(_ session: WorkoutSessionRecord) {
        sessions.removeAll { $0.id == session.id }
        enqueueWrite(sessions: [], removing: [session.id])
    }

    func flush() {
        persistenceQueue.sync {}
    }

    private static func defaultDirectory(using fileManager: FileManager) -> URL {
        let applicationSupport = fileManager.urls(for: .applicationSupportDirectory, in: .userDomainMask)[0]
        return applicationSupport
            .appendingPathComponent("Hang Ten", isDirectory: true)
            .appendingPathComponent("Workout Sessions", isDirectory: true)
    }

    private static func load(
        from directory: URL,
        decoder: JSONDecoder,
        fileManager: FileManager
    ) -> (sessions: [WorkoutSessionRecord], fileStoreExists: Bool, errorDescription: String?) {
        var isDirectory: ObjCBool = false
        guard fileManager.fileExists(atPath: directory.path, isDirectory: &isDirectory) else {
            return ([], false, nil)
        }
        guard isDirectory.boolValue else {
            return ([], true, "Workout session storage is not a directory.")
        }

        do {
            let files = try fileManager.contentsOfDirectory(
                at: directory,
                includingPropertiesForKeys: nil
            )
            let storedSessions = files
                .filter { $0.pathExtension == "json" }
                .compactMap { try? decoder.decode(WorkoutSessionRecord.self, from: Data(contentsOf: $0)) }
            return (Array(storedSessions.sorted(by: isOrderedNewestFirst).prefix(maximumSessionCount)), true, nil)
        } catch {
            return ([], true, "Could not load workout sessions: \(error.localizedDescription)")
        }
    }

    private static func loadLegacy(from defaults: UserDefaults, decoder: JSONDecoder) -> [WorkoutSessionRecord] {
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

    private func migrateLegacyHistory(_ sessions: [WorkoutSessionRecord]) {
        enqueueWrite(sessions: sessions, removing: [], removeLegacyHistoryOnSuccess: true)
    }

    private func enqueueWrite(
        sessions sessionsToWrite: [WorkoutSessionRecord],
        removing idsToRemove: Set<UUID>,
        removeLegacyHistoryOnSuccess: Bool = false
    ) {
        persistenceQueue.async { [self] in
            do {
                try fileManager.createDirectory(at: directory, withIntermediateDirectories: true)
                for session in sessionsToWrite {
                    let data = try encoder.encode(session)
                    try data.write(to: fileURL(for: session.id), options: .atomic)
                }
                for id in idsToRemove {
                    let fileURL = fileURL(for: id)
                    guard fileManager.fileExists(atPath: fileURL.path) else { continue }
                    try fileManager.removeItem(at: fileURL)
                }
                if removeLegacyHistoryOnSuccess {
                    defaults.removeObject(forKey: Key.sessionHistory)
                }
                setPersistenceError(nil)
            } catch {
                setPersistenceError("Could not save workout sessions: \(error.localizedDescription)")
            }
        }
    }

    private func fileURL(for id: UUID) -> URL {
        directory.appendingPathComponent("session-\(id.uuidString).json")
    }

    private func setPersistenceError(_ error: String?) {
        persistenceErrorLock.lock()
        persistenceErrorStorage = error
        persistenceErrorLock.unlock()
    }
}
