import Foundation

protocol WorkoutSessionStoring: AnyObject {
    var sessions: [WorkoutSessionRecord] { get }
    var persistenceError: String? { get }
    func append(_ session: WorkoutSessionRecord, completion: @escaping (Result<Void, Error>) -> Void)
    func remove(_ session: WorkoutSessionRecord, completion: @escaping (Result<Void, Error>) -> Void)
    func flush()
    func flush(completion: @escaping (Result<Void, Error>) -> Void)
}

extension WorkoutSessionStoring {
    func append(_ session: WorkoutSessionRecord) {
        append(session) { _ in }
    }

    func remove(_ session: WorkoutSessionRecord) {
        remove(session) { _ in }
    }

}

final class WorkoutSessionStore: WorkoutSessionStoring {
    private enum Key {
        static let sessionHistory = "workout.sessionHistory"
        static let legacyMigrationComplete = "legacy-migration-complete"
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

        let legacySessions = Self.loadLegacy(from: defaults, decoder: decoder)
        if !fileManager.fileExists(atPath: migrationMarkerURL.path), let legacySessions {
            let mergedSessions = Self.merge(loaded.sessions, with: legacySessions)
            sessions = mergedSessions
            migrateLegacyHistory(mergedSessions)
        }
    }

    func append(_ session: WorkoutSessionRecord, completion: @escaping (Result<Void, Error>) -> Void) {
        let previousSessions = sessions
        sessions.removeAll { $0.id == session.id }
        sessions.append(session)
        sessions.sort(by: Self.isOrderedNewestFirst)
        sessions = Array(sessions.prefix(Self.maximumSessionCount))

        let retainedIDs = Set(sessions.map(\.id))
        var removedIDs = Set(previousSessions.map(\.id)).subtracting(retainedIDs)
        if !retainedIDs.contains(session.id) {
            removedIDs.insert(session.id)
        }
        let completesLegacyMigration = hasPendingLegacyMigration
        enqueueWrite(
            sessions: sessions,
            retainedIDs: retainedIDs,
            removing: removedIDs,
            markLegacyMigrationComplete: completesLegacyMigration,
            removeLegacyHistoryOnSuccess: completesLegacyMigration,
            completion: completion
        )
    }

    func remove(_ session: WorkoutSessionRecord, completion: @escaping (Result<Void, Error>) -> Void) {
        sessions.removeAll { $0.id == session.id }
        let completesLegacyMigration = hasPendingLegacyMigration
        enqueueWrite(
            sessions: sessions,
            retainedIDs: Set(sessions.map(\.id)),
            removing: [session.id],
            markLegacyMigrationComplete: completesLegacyMigration,
            removeLegacyHistoryOnSuccess: completesLegacyMigration,
            completion: completion
        )
    }

    func flush(completion: @escaping (Result<Void, Error>) -> Void) {
        flush()
        if let persistenceError {
            completion(.failure(PersistenceFailure(message: persistenceError)))
        } else {
            completion(.success(()))
        }
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
            var storedSessions: [WorkoutSessionRecord] = []
            var loadError: String?
            for file in files where file.pathExtension == "json" {
                do {
                    let data = try Data(contentsOf: file)
                    storedSessions.append(try decoder.decode(WorkoutSessionRecord.self, from: data))
                } catch {
                    loadError = loadError ?? "Could not load \(file.lastPathComponent): \(error.localizedDescription)"
                }
            }
            return (Array(storedSessions.sorted(by: isOrderedNewestFirst).prefix(maximumSessionCount)), true, loadError)
        } catch {
            return ([], true, "Could not load workout sessions: \(error.localizedDescription)")
        }
    }

    private static func loadLegacy(from defaults: UserDefaults, decoder: JSONDecoder) -> [WorkoutSessionRecord]? {
        guard let data = defaults.data(forKey: Key.sessionHistory),
              let storedSessions = try? decoder.decode([WorkoutSessionRecord].self, from: data) else {
            return nil
        }
        return Array(storedSessions.sorted(by: isOrderedNewestFirst).prefix(maximumSessionCount))
    }

    private static func isOrderedNewestFirst(_ lhs: WorkoutSessionRecord, _ rhs: WorkoutSessionRecord) -> Bool {
        if lhs.recordedAt != rhs.recordedAt {
            return lhs.recordedAt > rhs.recordedAt
        }
        return lhs.id.uuidString < rhs.id.uuidString
    }

    private static func merge(
        _ granularSessions: [WorkoutSessionRecord],
        with legacySessions: [WorkoutSessionRecord]
    ) -> [WorkoutSessionRecord] {
        var sessionsByID: [UUID: WorkoutSessionRecord] = [:]
        for session in legacySessions + granularSessions {
            guard let existing = sessionsByID[session.id] else {
                sessionsByID[session.id] = session
                continue
            }
            if session.recordedAt >= existing.recordedAt {
                sessionsByID[session.id] = session
            }
        }
        return Array(sessionsByID.values.sorted(by: isOrderedNewestFirst).prefix(maximumSessionCount))
    }

    private func migrateLegacyHistory(_ sessions: [WorkoutSessionRecord]) {
        enqueueWrite(
            sessions: sessions,
            retainedIDs: Set(sessions.map(\.id)),
            removing: [],
            markLegacyMigrationComplete: true,
            removeLegacyHistoryOnSuccess: true,
            completion: { _ in }
        )
    }

    private func enqueueWrite(
        sessions sessionsToWrite: [WorkoutSessionRecord],
        retainedIDs: Set<UUID>,
        removing idsToRemove: Set<UUID>,
        markLegacyMigrationComplete: Bool = false,
        removeLegacyHistoryOnSuccess: Bool = false,
        completion: @escaping (Result<Void, Error>) -> Void
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
                try removeUnretainedSessionFiles(except: retainedIDs)
                if markLegacyMigrationComplete {
                    try Data().write(to: migrationMarkerURL, options: .atomic)
                }
                if removeLegacyHistoryOnSuccess {
                    defaults.removeObject(forKey: Key.sessionHistory)
                }
                setPersistenceError(nil)
                completion(.success(()))
            } catch {
                setPersistenceError("Could not save workout sessions: \(error.localizedDescription)")
                completion(.failure(error))
            }
        }
    }

    private func removeUnretainedSessionFiles(except retainedIDs: Set<UUID>) throws {
        let files = try fileManager.contentsOfDirectory(at: directory, includingPropertiesForKeys: nil)
        for file in files where file.pathExtension == "json" {
            let filename = file.deletingPathExtension().lastPathComponent
            guard filename.hasPrefix("session-"),
                  let id = UUID(uuidString: String(filename.dropFirst("session-".count))),
                  !retainedIDs.contains(id) else { continue }
            try fileManager.removeItem(at: file)
        }
    }

    private func fileURL(for id: UUID) -> URL {
        directory.appendingPathComponent("session-\(id.uuidString).json")
    }

    private var migrationMarkerURL: URL {
        directory.appendingPathComponent(Key.legacyMigrationComplete)
    }

    private var hasPendingLegacyMigration: Bool {
        !fileManager.fileExists(atPath: migrationMarkerURL.path) &&
            Self.loadLegacy(from: defaults, decoder: decoder) != nil
    }

    private func setPersistenceError(_ error: String?) {
        persistenceErrorLock.lock()
        persistenceErrorStorage = error
        persistenceErrorLock.unlock()
    }

    private struct PersistenceFailure: LocalizedError {
        let message: String

        var errorDescription: String? { message }
    }
}
