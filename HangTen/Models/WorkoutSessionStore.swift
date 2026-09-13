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
    static let legacyKey = "workout.sessionHistory"

    private static let maximumSessionCount = 20
    private static let sessionFilePrefix = "session-v2-"

    private let encoder: JSONEncoder
    private let decoder: JSONDecoder
    private let directory: URL
    private let legacyDirectory: URL?
    private let fileManager: FileManager
    private let persistenceQueue = DispatchQueue(
        label: "com.hangten.workout-session-store",
        qos: .utility
    )
    private let persistenceQueueIdentity = DispatchSpecificKey<UInt8>()
    private let sessionsLock = NSLock()
    private let persistenceErrorLock = NSLock()
    private var persistenceErrorStorage: String?
    private var sessionsStorage: [WorkoutSessionRecord] = []
    private var didFinishLoading = false
    private var pendingMutations: [SessionMutation] = []
    private var loadResult: Result<Void, Error>?
    private var loadCompletions: [(Result<Void, Error>) -> Void] = []

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
        self.fileManager = fileManager
        encoder = JSONEncoder()
        decoder = JSONDecoder()
        self.directory = directory ?? Self.defaultDirectory(using: fileManager)
        legacyDirectory = directory == nil ? Self.legacyDirectory(using: fileManager) : nil
        defaults.removeObject(forKey: Self.legacyKey)
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
        enqueueWrite(
            removing: removedIDs,
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

        enqueueWrite(
            removing: [session.id],
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
            .appendingPathComponent("Workout Sessions v2", isDirectory: true)
    }

    private static func legacyDirectory(using fileManager: FileManager) -> URL {
        let applicationSupport = fileManager.urls(for: .applicationSupportDirectory, in: .userDomainMask)[0]
        return applicationSupport
            .appendingPathComponent("Hang Ten", isDirectory: true)
            .appendingPathComponent("Workout Sessions", isDirectory: true)
    }

    private static func load(
        from directory: URL,
        decoder: JSONDecoder,
        fileManager: FileManager
    ) -> (sessions: [WorkoutSessionRecord], errorDescription: String?) {
        var isDirectory: ObjCBool = false
        guard fileManager.fileExists(atPath: directory.path, isDirectory: &isDirectory) else {
            return ([], nil)
        }
        guard isDirectory.boolValue else {
            return ([], "Workout session storage is not a directory.")
        }

        do {
            let files = try fileManager.contentsOfDirectory(
                at: directory,
                includingPropertiesForKeys: nil
            )
            var storedSessions: [WorkoutSessionRecord] = []
            var loadError: String?
            for file in files where file.pathExtension == "json" {
                guard isCurrentSessionFile(file) else {
                    try fileManager.removeItem(at: file)
                    continue
                }
                do {
                    let data = try Data(contentsOf: file)
                    storedSessions.append(try decoder.decode(WorkoutSessionRecord.self, from: data))
                } catch {
                    loadError = loadError ?? "Could not load \(file.lastPathComponent): \(error.localizedDescription)"
                }
            }
            return (Array(storedSessions.sorted(by: isOrderedNewestFirst).prefix(maximumSessionCount)), loadError)
        } catch {
            return ([], "Could not load workout sessions: \(error.localizedDescription)")
        }
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

    private func enqueueWrite(
        removing idsToRemove: Set<UUID>,
        completion: @escaping (Result<Void, Error>) -> Void
    ) {
        persistenceQueue.async { [self] in
            let result = write(removing: idsToRemove)
            DispatchQueue.main.async {
                completion(result)
            }
        }
    }

    private func write(removing idsToRemove: Set<UUID>) -> Result<Void, Error> {
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
            setPersistenceError(nil)
            return .success(())
        } catch {
            setPersistenceError("Could not save workout sessions: \(error.localizedDescription)")
            return .failure(error)
        }
    }

    private func removeUnretainedSessionFiles(except retainedIDs: Set<UUID>) throws {
        let files = try fileManager.contentsOfDirectory(at: directory, includingPropertiesForKeys: nil)
        for file in files where Self.isCurrentSessionFile(file) {
            let filename = file.deletingPathExtension().lastPathComponent
            guard let id = UUID(
                uuidString: String(filename.dropFirst(Self.sessionFilePrefix.count))
            ),
                  !retainedIDs.contains(id) else { continue }
            try fileManager.removeItem(at: file)
        }
    }

    private func fileURL(for id: UUID) -> URL {
        directory.appendingPathComponent("\(Self.sessionFilePrefix)\(id.uuidString).json")
    }

    private static func isCurrentSessionFile(_ file: URL) -> Bool {
        file.pathExtension == "json"
            && file.deletingPathExtension().lastPathComponent.hasPrefix(sessionFilePrefix)
    }

    private func loadPersistedState() {
        let cleanupError = removeLegacyPersistence()
        let loaded = Self.load(from: directory, decoder: decoder, fileManager: fileManager)
        setPersistenceError(cleanupError ?? loaded.errorDescription)

        var mergedSessions = loaded.sessions

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

        let loadResult: Result<Void, Error> = (cleanupError ?? loaded.errorDescription).map {
            .failure(PersistenceFailure(message: $0))
        } ?? .success(())
        finishLoading(loadResult)
    }

    private func removeLegacyPersistence() -> String? {
        do {
            if let legacyDirectory,
               fileManager.fileExists(atPath: legacyDirectory.path) {
                try fileManager.removeItem(at: legacyDirectory)
            }
            guard fileManager.fileExists(atPath: directory.path) else { return nil }
            let migrationMarker = directory.appendingPathComponent("legacy-migration-complete")
            if fileManager.fileExists(atPath: migrationMarker.path) {
                try fileManager.removeItem(at: migrationMarker)
            }
            return nil
        } catch {
            return "Could not remove former workout sessions: \(error.localizedDescription)"
        }
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

}
