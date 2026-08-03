import XCTest
@testable import HangTen

final class WorkoutSessionStoreTests: XCTestCase {
    private var suite: String!
    private var directory: URL!

    override func setUp() {
        super.setUp()
        suite = "WorkoutSessionStoreTests-\(UUID().uuidString)"
        UserDefaults(suiteName: suite)?.removePersistentDomain(forName: suite)
        directory = FileManager.default.temporaryDirectory
            .appendingPathComponent("WorkoutSessionStoreTests-\(UUID().uuidString)", isDirectory: true)
    }

    override func tearDown() {
        try? FileManager.default.removeItem(at: directory)
        UserDefaults(suiteName: suite)?.removePersistentDomain(forName: suite)
        super.tearDown()
    }

    func testAbsentOrMalformedHistoryLoadsAsEmpty() {
        let defaults = UserDefaults(suiteName: suite)!
        let emptyStore = WorkoutSessionStore(defaults: defaults, directory: directory)
        emptyStore.flush()
        XCTAssertEqual(emptyStore.sessions, [])

        defaults.set(Data("not JSON".utf8), forKey: "workout.sessionHistory")
        let malformedStore = WorkoutSessionStore(defaults: defaults, directory: directory)
        malformedStore.flush()
        XCTAssertEqual(malformedStore.sessions, [])
    }

    func testInitializationReturnsBeforeHistoryReadCompletes() throws {
        let defaults = UserDefaults(suiteName: suite)!
        try FileManager.default.createDirectory(at: directory, withIntermediateDirectories: true)
        let fileManager = BlockingHistoryFileManager()
        let initializationReturned = DispatchSemaphore(value: 0)
        let storeFinishedInitializing = DispatchSemaphore(value: 0)

        DispatchQueue.global().async {
            let store = WorkoutSessionStore(
                defaults: defaults,
                directory: self.directory,
                fileManager: fileManager
            )
            initializationReturned.signal()
            _ = store
            storeFinishedInitializing.signal()
        }

        XCTAssertEqual(
            initializationReturned.wait(timeout: .now() + 1),
            .success,
            "Store initialization should not wait for the full history read"
        )
        XCTAssertEqual(fileManager.historyReadStarted.wait(timeout: .now() + 1), .success)

        fileManager.allowHistoryRead.signal()
        XCTAssertEqual(storeFinishedInitializing.wait(timeout: .now() + 1), .success)
    }

    func testMigratesLegacyHistoryToIndividualSessionFilesAndClearsTheBlob() throws {
        let defaults = UserDefaults(suiteName: suite)!
        let older = session(id: "00000000-0000-0000-0000-000000000002", recordedAt: 10)
        let newer = session(id: "00000000-0000-0000-0000-000000000001", recordedAt: 20)
        defaults.set(try JSONEncoder().encode([older, newer]), forKey: "workout.sessionHistory")

        let store = WorkoutSessionStore(defaults: defaults, directory: directory)
        store.flush()

        XCTAssertEqual(store.sessions, [newer, older])
        XCTAssertNil(defaults.data(forKey: "workout.sessionHistory"))
        XCTAssertEqual(try sessionFiles().count, 2)
        XCTAssertEqual(WorkoutSessionStore(defaults: defaults, directory: directory).sessions, [newer, older])
    }

    func testUnmarkedStoreRetriesMigrationFromValidLegacyHistory() throws {
        let defaults = UserDefaults(suiteName: suite)!
        let older = session(id: "00000000-0000-0000-0000-000000000002", recordedAt: 10)
        let newer = session(id: "00000000-0000-0000-0000-000000000001", recordedAt: 20)
        let partialExtra = session(id: "00000000-0000-0000-0000-000000000003", recordedAt: 30)
        defaults.set(try JSONEncoder().encode([older, newer]), forKey: "workout.sessionHistory")
        try FileManager.default.createDirectory(at: directory, withIntermediateDirectories: true)
        try JSONEncoder().encode(partialExtra).write(
            to: directory.appendingPathComponent("session-\(partialExtra.id.uuidString).json")
        )

        let store = WorkoutSessionStore(defaults: defaults, directory: directory)
        store.flush()

        XCTAssertEqual(store.sessions, [partialExtra, newer, older])
        XCTAssertNil(defaults.data(forKey: "workout.sessionHistory"))
        XCTAssertEqual(try sessionFiles().map(\.lastPathComponent), [
            "session-\(newer.id.uuidString).json",
            "session-\(older.id.uuidString).json",
            "session-\(partialExtra.id.uuidString).json"
        ].sorted())
    }

    func testLegacyMigrationDeduplicatesRepeatedSessionIDs() throws {
        let defaults = UserDefaults(suiteName: suite)!
        let olderCopy = session(id: "00000000-0000-0000-0000-000000000001", recordedAt: 10)
        let newerCopy = session(id: "00000000-0000-0000-0000-000000000001", recordedAt: 20)
        defaults.set(try JSONEncoder().encode([olderCopy, newerCopy]), forKey: "workout.sessionHistory")

        let store = WorkoutSessionStore(defaults: defaults, directory: directory)
        store.flush()

        XCTAssertEqual(store.sessions, [newerCopy])
        XCTAssertEqual(WorkoutSessionStore(defaults: defaults, directory: directory).sessions, [newerCopy])
    }

    func testAppendWritesOneRoundTrippableFilePerSession() throws {
        let defaults = UserDefaults(suiteName: suite)!
        let record = session(id: "00000000-0000-0000-0000-000000000001", recordedAt: 20)
        let store = WorkoutSessionStore(defaults: defaults, directory: directory)

        store.append(record)
        store.flush()

        let files = try sessionFiles()
        XCTAssertEqual(files.map(\.lastPathComponent), ["session-\(record.id.uuidString).json"])
        XCTAssertEqual(try JSONDecoder().decode(WorkoutSessionRecord.self, from: Data(contentsOf: files[0])), record)
        XCTAssertEqual(WorkoutSessionStore(defaults: defaults, directory: directory).sessions, [record])
    }

    func testAppendCompletesSuccessfullyAfterWriting() {
        let expectation = expectation(description: "append completion")
        let store = WorkoutSessionStore(defaults: UserDefaults(suiteName: suite)!, directory: directory)

        store.append(session(id: "00000000-0000-0000-0000-000000000001", recordedAt: 20)) { result in
            if case .success = result {
                expectation.fulfill()
            }
        }

        wait(for: [expectation], timeout: 2)
    }

    func testAppendCompletionRunsOnMainQueueAndCanFlush() {
        let completion = expectation(description: "append completion flushes")
        let store = WorkoutSessionStore(defaults: UserDefaults(suiteName: suite)!, directory: directory)

        store.append(session(id: "00000000-0000-0000-0000-000000000001", recordedAt: 20)) { result in
            XCTAssertTrue(Thread.isMainThread)
            store.flush()

            switch result {
            case .success:
                completion.fulfill()
            case .failure(let error):
                XCTFail("Expected append to succeed, got \(error)")
            }
        }

        wait(for: [completion], timeout: 2)
    }

    func testRemoveCompletionRunsOnMainQueueAndCanFlush() {
        let completion = expectation(description: "remove completion flushes")
        let record = session(id: "00000000-0000-0000-0000-000000000001", recordedAt: 20)
        let store = WorkoutSessionStore(defaults: UserDefaults(suiteName: suite)!, directory: directory)
        store.append(record)

        store.remove(record) { result in
            XCTAssertTrue(Thread.isMainThread)
            store.flush()

            switch result {
            case .success:
                completion.fulfill()
            case .failure(let error):
                XCTFail("Expected remove to succeed, got \(error)")
            }
        }

        wait(for: [completion], timeout: 2)
    }

    func testFlushCompletionRunsOnMainQueue() {
        let completion = expectation(description: "flush completion")
        let store = WorkoutSessionStore(defaults: UserDefaults(suiteName: suite)!, directory: directory)

        DispatchQueue.global().async {
            store.flush { result in
                XCTAssertTrue(Thread.isMainThread)

                switch result {
                case .success:
                    completion.fulfill()
                case .failure(let error):
                    XCTFail("Expected flush to succeed, got \(error)")
                }
            }
        }

        wait(for: [completion], timeout: 2)
    }

    func testAsynchronousFlushDoesNotBlockCallerOnPendingWrite() {
        let defaults = UserDefaults(suiteName: suite)!
        let fileManager = BlockingWriteFileManager()
        let store = WorkoutSessionStore(
            defaults: defaults,
            directory: directory,
            fileManager: fileManager
        )
        store.append(session(id: "00000000-0000-0000-0000-000000000001", recordedAt: 20))

        XCTAssertEqual(fileManager.writeStarted.wait(timeout: .now() + 1), .success)

        let flushReturned = DispatchSemaphore(value: 0)
        let completion = expectation(description: "flush completion")
        DispatchQueue.global().async {
            store.flush { result in
                if case .failure(let error) = result {
                    XCTFail("Expected flush to succeed, got \(error)")
                }
                completion.fulfill()
            }
            flushReturned.signal()
        }

        XCTAssertEqual(
            flushReturned.wait(timeout: .now() + 1),
            .success,
            "Asynchronous flush should return before pending persistence finishes"
        )
        fileManager.allowWrite.signal()
        wait(for: [completion], timeout: 2)
    }

    func testAppendUsesStableIDOrderingWhenRecordedDatesMatch() {
        let defaults = UserDefaults(suiteName: suite)!
        let laterID = session(id: "00000000-0000-0000-0000-000000000002", recordedAt: 10)
        let earlierID = session(id: "00000000-0000-0000-0000-000000000001", recordedAt: 10)

        let store = WorkoutSessionStore(defaults: defaults, directory: directory)
        store.append(laterID)
        store.append(earlierID)

        XCTAssertEqual(store.sessions, [earlierID, laterID])
    }

    func testAppendKeepsOnlyTwentyNewestSessions() throws {
        let defaults = UserDefaults(suiteName: suite)!
        let store = WorkoutSessionStore(defaults: defaults, directory: directory)
        for index in 0..<21 {
            store.append(session(id: String(format: "00000000-0000-0000-0000-%012d", index), recordedAt: TimeInterval(index)))
        }

        XCTAssertEqual(store.sessions.count, 20)
        XCTAssertEqual(store.sessions.first?.recordedAt, Date(timeIntervalSince1970: 20))
        XCTAssertEqual(store.sessions.last?.recordedAt, Date(timeIntervalSince1970: 1))
        store.flush()
        XCTAssertEqual(try sessionFiles().count, 20)
    }

    func testConcurrentAppendsExposeCoherentSnapshots() {
        let defaults = UserDefaults(suiteName: suite)!
        let store = WorkoutSessionStore(defaults: defaults, directory: directory)

        DispatchQueue.concurrentPerform(iterations: 40) { index in
            store.append(
                session(
                    id: String(format: "00000000-0000-0000-0000-%012d", index),
                    recordedAt: TimeInterval(index)
                )
            )
            _ = store.sessions
        }
        store.flush()

        XCTAssertEqual(store.sessions.count, 20)
        XCTAssertEqual(store.sessions.first?.recordedAt, Date(timeIntervalSince1970: 39))
        XCTAssertEqual(store.sessions.last?.recordedAt, Date(timeIntervalSince1970: 20))
        XCTAssertEqual(Set(store.sessions.map(\.id)).count, store.sessions.count)
    }

    func testAppendDoesNotPersistARecordTrimmedFromRetainedHistory() throws {
        let defaults = UserDefaults(suiteName: suite)!
        let store = WorkoutSessionStore(defaults: defaults, directory: directory)
        for index in 1...20 {
            store.append(session(id: String(format: "00000000-0000-0000-0000-%012d", index), recordedAt: TimeInterval(index)))
        }
        store.flush()

        let oldRecord = session(id: "00000000-0000-0000-0000-000000000000", recordedAt: 0)
        store.append(oldRecord)
        store.flush()

        XCTAssertFalse(try sessionFiles().contains {
            $0.lastPathComponent == "session-\(oldRecord.id.uuidString).json"
        })
        XCTAssertFalse(WorkoutSessionStore(defaults: defaults, directory: directory).sessions.contains(oldRecord))
    }

    func testReappendedTrimmedIDIsNotRemovedByEarlierWrite() throws {
        let defaults = UserDefaults(suiteName: suite)!
        let reused = session(id: "00000000-0000-0000-0000-000000000000", recordedAt: 0)
        let store = WorkoutSessionStore(defaults: defaults, directory: directory)
        store.append(reused)
        store.flush()

        for index in 1...20 {
            store.append(session(
                id: String(format: "00000000-0000-0000-0000-%012d", index),
                recordedAt: TimeInterval(index)
            ))
        }
        let reappended = session(id: reused.id.uuidString, recordedAt: 21)
        store.append(reappended)
        store.flush()

        XCTAssertTrue(try sessionFiles().contains {
            $0.lastPathComponent == "session-\(reappended.id.uuidString).json"
        })
        XCTAssertEqual(WorkoutSessionStore(defaults: defaults, directory: directory).sessions.first, reappended)
    }

    func testAppendRecoveryRewritesAnEarlierFailedSession() throws {
        let defaults = UserDefaults(suiteName: suite)!
        let first = session(id: "00000000-0000-0000-0000-000000000001", recordedAt: 10)
        let second = session(id: "00000000-0000-0000-0000-000000000002", recordedAt: 20)
        defaults.set(try JSONEncoder().encode([first]), forKey: "workout.sessionHistory")
        try Data("not a directory".utf8).write(to: directory)
        let store = WorkoutSessionStore(defaults: defaults, directory: directory)

        store.flush()
        XCTAssertNotNil(store.persistenceError)

        try FileManager.default.removeItem(at: directory)
        try FileManager.default.createDirectory(at: directory, withIntermediateDirectories: true)
        store.append(second)
        store.flush()

        XCTAssertNil(store.persistenceError)
        XCTAssertNil(defaults.data(forKey: "workout.sessionHistory"))
        XCTAssertEqual(WorkoutSessionStore(defaults: defaults, directory: directory).sessions, [second, first])
    }

    func testFailedLegacyMigrationKeepsCachedPendingStateForRetry() throws {
        let defaults = UserDefaults(suiteName: suite)!
        let first = session(id: "00000000-0000-0000-0000-000000000001", recordedAt: 10)
        let second = session(id: "00000000-0000-0000-0000-000000000002", recordedAt: 20)
        defaults.set(try JSONEncoder().encode([first]), forKey: "workout.sessionHistory")
        try Data("not a directory".utf8).write(to: directory)

        let store = WorkoutSessionStore(defaults: defaults, directory: directory)
        store.flush()
        XCTAssertNotNil(store.persistenceError)

        try FileManager.default.removeItem(at: directory)
        try FileManager.default.createDirectory(at: directory, withIntermediateDirectories: true)
        defaults.set(Data("legacy payload changed after the first attempt".utf8), forKey: "workout.sessionHistory")

        store.append(second)
        store.flush()

        XCTAssertNil(store.persistenceError)
        XCTAssertTrue(FileManager.default.fileExists(
            atPath: directory.appendingPathComponent("legacy-migration-complete").path
        ))
        XCTAssertEqual(WorkoutSessionStore(defaults: defaults, directory: directory).sessions, [second, first])
    }

    func testCorruptSessionFilePreservesReadableHistoryAndSurfacesLoadError() throws {
        let defaults = UserDefaults(suiteName: suite)!
        try FileManager.default.createDirectory(at: directory, withIntermediateDirectories: true)
        let valid = session(id: "00000000-0000-0000-0000-000000000001", recordedAt: 10)
        try JSONEncoder().encode(valid).write(
            to: directory.appendingPathComponent("session-\(valid.id.uuidString).json")
        )
        try Data("not JSON".utf8).write(
            to: directory.appendingPathComponent("session-00000000-0000-0000-0000-000000000002.json")
        )

        let store = WorkoutSessionStore(defaults: defaults, directory: directory)
        store.flush()

        XCTAssertEqual(store.sessions, [valid])
        XCTAssertNotNil(store.persistenceError)
    }

    func testRemoveDeletesSavedSessionAndPersistsTheChange() throws {
        let defaults = UserDefaults(suiteName: suite)!
        let first = session(id: "00000000-0000-0000-0000-000000000001", recordedAt: 10)
        let second = session(id: "00000000-0000-0000-0000-000000000002", recordedAt: 20)
        let store = WorkoutSessionStore(defaults: defaults, directory: directory)
        store.append(first)
        store.append(second)

        store.remove(first)
        store.flush()

        XCTAssertEqual(WorkoutSessionStore(defaults: defaults, directory: directory).sessions, [second])
        XCTAssertEqual(try sessionFiles().map(\.lastPathComponent), ["session-\(second.id.uuidString).json"])
    }

    func testReportsPersistenceErrorWhenStorageDirectoryCannotBeCreated() throws {
        let defaults = UserDefaults(suiteName: suite)!
        try Data("not a directory".utf8).write(to: directory)
        let store = WorkoutSessionStore(defaults: defaults, directory: directory)

        store.append(session(id: "00000000-0000-0000-0000-000000000001", recordedAt: 10))
        store.flush()

        XCTAssertEqual(store.sessions.count, 1)
        XCTAssertNotNil(store.persistenceError)
    }

    private func sessionFiles() throws -> [URL] {
        try FileManager.default.contentsOfDirectory(
            at: directory,
            includingPropertiesForKeys: nil
        )
        .filter { $0.pathExtension == "json" }
        .sorted { $0.lastPathComponent < $1.lastPathComponent }
    }

    private func session(id: String, recordedAt: TimeInterval) -> WorkoutSessionRecord {
        WorkoutSessionRecord(
            id: UUID(uuidString: id)!,
            planID: "plan",
            planTitle: "Plan",
            recordedAt: Date(timeIntervalSince1970: recordedAt),
            startDate: Date(timeIntervalSince1970: 0),
            endDate: Date(timeIntervalSince1970: recordedAt),
            motherboardIdentifier: nil,
            batteryValue: nil,
            steps: []
        )
    }
}

private final class BlockingHistoryFileManager: FileManager {
    let historyReadStarted = DispatchSemaphore(value: 0)
    let allowHistoryRead = DispatchSemaphore(value: 0)

    override func contentsOfDirectory(
        at url: URL,
        includingPropertiesForKeys keys: [URLResourceKey]?,
        options mask: FileManager.DirectoryEnumerationOptions = []
    ) throws -> [URL] {
        historyReadStarted.signal()
        allowHistoryRead.wait()
        return try super.contentsOfDirectory(
            at: url,
            includingPropertiesForKeys: keys,
            options: mask
        )
    }
}

private final class BlockingWriteFileManager: FileManager {
    let writeStarted = DispatchSemaphore(value: 0)
    let allowWrite = DispatchSemaphore(value: 0)

    override func createDirectory(
        at url: URL,
        withIntermediateDirectories createIntermediates: Bool,
        attributes: [FileAttributeKey: Any]? = nil
    ) throws {
        writeStarted.signal()
        allowWrite.wait()
        try super.createDirectory(
            at: url,
            withIntermediateDirectories: createIntermediates,
            attributes: attributes
        )
    }
}
