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
        XCTAssertEqual(WorkoutSessionStore(defaults: defaults, directory: directory).sessions, [])

        defaults.set(Data("not JSON".utf8), forKey: "workout.sessionHistory")
        XCTAssertEqual(WorkoutSessionStore(defaults: defaults, directory: directory).sessions, [])
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
