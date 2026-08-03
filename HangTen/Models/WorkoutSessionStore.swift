import Foundation

protocol WorkoutSessionStoring: AnyObject {
    var sessions: [WorkoutSessionRecord] { get }
    var persistenceError: String? { get }
    /// Loads the persisted snapshot without blocking the caller.
    /// Completion handlers are delivered asynchronously on the main queue.
    func load(completion: @escaping (Result<Void, Error>) -> Void)
    /// Completion handlers are delivered asynchronously on the main queue.
    func append(_ session: WorkoutSessionRecord, completion: @escaping (Result<Void, Error>) -> Void)
    func remove(_ session: WorkoutSessionRecord, completion: @escaping (Result<Void, Error>) -> Void)
    /// Waits for all queued persistence work to finish.
    func flush()
    /// Queues a completion after all currently queued persistence work finishes.
    /// This method never waits for the persistence queue on the caller's thread.
    func flush(completion: @escaping (Result<Void, Error>) -> Void)
}

extension WorkoutSessionStoring {
    func load(completion: @escaping (Result<Void, Error>) -> Void) {
        DispatchQueue.main.async {
            completion(.success(()))
        }
    }

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
    private let persistenceQueueIdentity = DispatchSpecificKey<UInt8>()
    private let sessionsLock = NSLock()
    private let persistenceErrorLock = NSLock()
    private let migrationStateLock = NSLock()
    private var persistenceErrorStorage: String?
    private var sessionsStorage: [WorkoutSessionRecord] = []
    private var didFinishLoading = false
    private var pendingMutations: [SessionMutation] = []
    private var loadResult: Result<Void, Error>?
    private var loadCompletions: [(Result<Void, Error>) -> Void] = []
    private var migrationState: LegacyMigrationState = .unknown

    var sessions: [WorkoutSessionRecord] {
        sessionsLock.lock()
        defer { sessionsLock.unlock() }
        return sessionsStorage
    }

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
        persistenceQueue.setSpecific(key: persistenceQueueIdentity, value: 1)

        persistenceQueue.async { [self] in
            loadPersistedState()
        }
    }

    func load(completion: @escaping (Result<Void, Error>) -> Void) {
        sessionsLock.lock()
        if let loadResult {
            sessionsLock.unlock()
            deliverLoadResult(loadResult, to: completion)
        } else {
            loadCompletions.append(completion)
            sessionsLock.unlock()
        }
    }

    func append(_ session: WorkoutSessionRecord, completion: @escaping (Result<Void, Error>) -> Void) {
        let previousSessions: [WorkoutSessionRecord]
        let updatedSessions: [WorkoutSessionRecord]
        sessionsLock.lock()
        previousSessions = sessionsStorage
        sessionsStorage = Self.appending(session, to: sessionsStorage)
        updatedSessions = sessionsStorage
        if !didFinishLoading {
            pendingMutations.append(.append(session))
        }
        sessionsLock.unlock()

        let retainedIDs = Set(updatedSessions.map(\.id))
        var removedIDs = Set(previousSessions.map(\.id)).subtracting(retainedIDs)
        if !retainedIDs.contains(session.id) {
            removedIDs.insert(session.id)
        }
        let completesLegacyMigration = hasPendingLegacyMigration
        enqueueWrite(
            removing: removedIDs,
            markLegacyMigrationComplete: completesLegacyMigration,
            removeLegacyHistoryOnSuccess: completesLegacyMigration,
            completion: completion
        )
    }

    func remove(_ session: WorkoutSessionRecord, completion: @escaping (Result<Void, Error>) -> Void) {
        sessionsLock.lock()
        sessionsStorage = Self.removing(session.id, from: sessionsStorage)
        if !didFinishLoading {
            pendingMutations.append(.remove(session.id))
        }
        sessionsLock.unlock()

        let completesLegacyMigration = hasPendingLegacyMigration
        enqueueWrite(
            removing: [session.id],
            markLegacyMigrationComplete: completesLegacyMigration,
            removeLegacyHistoryOnSuccess: completesLegacyMigration,
            completion: completion
        )
    }

    func flush(completion: @escaping (Result<Void, Error>) -> Void) {
        persistenceQueue.async { [self] in
            let result = currentPersistenceResult()
            DispatchQueue.main.async {
                completion(result)
            }
        }
    }

    func flush() {
        guard DispatchQueue.getSpecific(key: persistenceQueueIdentity) == nil else { return }
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

    private static func appending(
        _ session: WorkoutSessionRecord,
        to sessions: [WorkoutSessionRecord]
    ) -> [WorkoutSessionRecord] {
        var updatedSessions = sessions
        updatedSessions.removeAll { $0.id == session.id }
        updatedSessions.append(session)
        updatedSessions.sort(by: isOrderedNewestFirst)
        return Array(updatedSessions.prefix(maximumSessionCount))
    }

    private static func removing(
        _ id: UUID,
        from sessions: [WorkoutSessionRecord]
    ) -> [WorkoutSessionRecord] {
        sessions.filter { $0.id != id }
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

    private func enqueueWrite(
        removing idsToRemove: Set<UUID>,
        markLegacyMigrationComplete: Bool = false,
        removeLegacyHistoryOnSuccess: Bool = false,
        completion: @escaping (Result<Void, Error>) -> Void
    ) {
        persistenceQueue.async { [self] in
            let result: Result<Void, Error>
            do {
                let sessionsToWrite = sessions
                let retainedIDs = Set(sessionsToWrite.map(\.id))
                try fileManager.createDirectory(at: directory, withIntermediateDirectories: true)
                for session in sessionsToWrite {
                    let data = try encoder.encode(session)
                    try data.write(to: fileURL(for: session.id), options: .atomic)
                }
                for id in idsToRemove.subtracting(retainedIDs) {
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
                if markLegacyMigrationComplete {
                    setMigrationState(.notPending)
                }
                setPersistenceError(nil)
                result = .success(())
            } catch {
                setPersistenceError("Could not save workout sessions: \(error.localizedDescription)")
                result = .failure(error)
            }
            DispatchQueue.main.async {
                completion(result)
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
        migrationStateLock.lock()
        defer { migrationStateLock.unlock() }
        if case .pending = migrationState {
            return true
        }
        return false
    }

    private func loadPersistedState() {
        let loaded = Self.load(from: directory, decoder: decoder, fileManager: fileManager)
        setPersistenceError(loaded.errorDescription)

        let legacySessions: [WorkoutSessionRecord]?
        if fileManager.fileExists(atPath: migrationMarkerURL.path) {
            legacySessions = nil
            setMigrationState(.notPending)
        } else if let decodedLegacySessions = Self.loadLegacy(from: defaults, decoder: decoder) {
            legacySessions = decodedLegacySessions
            setMigrationState(.pending(decodedLegacySessions))
        } else {
            legacySessions = nil
            setMigrationState(.notPending)
        }

        var mergedSessions = loaded.sessions
        if let legacySessions {
            mergedSessions = Self.merge(mergedSessions, with: legacySessions)
        }

        sessionsLock.lock()
        for mutation in pendingMutations {
            switch mutation {
            case .append(let session):
                mergedSessions = Self.appending(session, to: mergedSessions)
            case .remove(let id):
                mergedSessions = Self.removing(id, from: mergedSessions)
            }
        }
        pendingMutations.removeAll()
        sessionsStorage = mergedSessions
        didFinishLoading = true
        sessionsLock.unlock()

        let loadResult: Result<Void, Error> = loaded.errorDescription.map {
            .failure(PersistenceFailure(message: $0))
        } ?? .success(())

        guard legacySessions != nil else {
            finishLoading(loadResult)
            return
        }

        enqueueWrite(
            removing: [],
            markLegacyMigrationComplete: true,
            removeLegacyHistoryOnSuccess: true,
            completion: { [weak self] migrationResult in
                guard let self else { return }
                switch migrationResult {
                case .success:
                    if case .failure(let error) = loadResult {
                        self.setPersistenceError(error.localizedDescription)
                    }
                    self.finishLoading(loadResult)
                case .failure:
                    self.finishLoading(migrationResult)
                }
            }
        )
    }

    private func finishLoading(_ result: Result<Void, Error>) {
        sessionsLock.lock()
        loadResult = result
        let completions = loadCompletions
        loadCompletions.removeAll()
        sessionsLock.unlock()

        for completion in completions {
            deliverLoadResult(result, to: completion)
        }
    }

    private func deliverLoadResult(
        _ result: Result<Void, Error>,
        to completion: @escaping (Result<Void, Error>) -> Void
    ) {
        DispatchQueue.main.async {
            completion(result)
        }
    }

    private func currentPersistenceResult() -> Result<Void, Error> {
        if let persistenceError {
            return .failure(PersistenceFailure(message: persistenceError))
        }
        return .success(())
    }

    private func setMigrationState(_ state: LegacyMigrationState) {
        migrationStateLock.lock()
        migrationState = state
        migrationStateLock.unlock()
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

    private enum SessionMutation {
        case append(WorkoutSessionRecord)
        case remove(UUID)
    }

    private enum LegacyMigrationState {
        case unknown
        case pending([WorkoutSessionRecord])
        case notPending
    }
}
