import XCTest
@testable import HangTen

final class WorkoutSessionStoreTests: XCTestCase {
    private let suite = "WorkoutSessionStoreTests"

    override func setUp() {
        super.setUp()
        UserDefaults(suiteName: suite)?.removePersistentDomain(forName: suite)
    }

    func testAbsentOrMalformedHistoryLoadsAsEmpty() {
        let defaults = UserDefaults(suiteName: suite)!
        XCTAssertEqual(WorkoutSessionStore(defaults: defaults).sessions, [])

        defaults.set(Data("not JSON".utf8), forKey: "workout.sessionHistory")
        XCTAssertEqual(WorkoutSessionStore(defaults: defaults).sessions, [])
    }

    func testAppendPersistsNewestSessionsFirstAcrossStoreInstances() {
        let defaults = UserDefaults(suiteName: suite)!
        let older = session(id: "00000000-0000-0000-0000-000000000002", recordedAt: 10)
        let newer = session(id: "00000000-0000-0000-0000-000000000001", recordedAt: 20)

        let store = WorkoutSessionStore(defaults: defaults)
        store.append(older)
        store.append(newer)

        XCTAssertEqual(WorkoutSessionStore(defaults: defaults).sessions, [newer, older])
    }

    func testAppendUsesStableIDOrderingWhenRecordedDatesMatch() {
        let defaults = UserDefaults(suiteName: suite)!
        let laterID = session(id: "00000000-0000-0000-0000-000000000002", recordedAt: 10)
        let earlierID = session(id: "00000000-0000-0000-0000-000000000001", recordedAt: 10)

        let store = WorkoutSessionStore(defaults: defaults)
        store.append(laterID)
        store.append(earlierID)

        XCTAssertEqual(store.sessions, [earlierID, laterID])
    }

    func testAppendKeepsOnlyTwentyNewestSessions() {
        let defaults = UserDefaults(suiteName: suite)!
        let store = WorkoutSessionStore(defaults: defaults)
        for index in 0..<21 {
            store.append(session(id: String(format: "00000000-0000-0000-0000-%012d", index), recordedAt: TimeInterval(index)))
        }

        XCTAssertEqual(store.sessions.count, 20)
        XCTAssertEqual(store.sessions.first?.recordedAt, Date(timeIntervalSince1970: 20))
        XCTAssertEqual(store.sessions.last?.recordedAt, Date(timeIntervalSince1970: 1))
    }

    func testRemoveDeletesSavedSessionAndPersistsTheChange() {
        let defaults = UserDefaults(suiteName: suite)!
        let first = session(id: "00000000-0000-0000-0000-000000000001", recordedAt: 10)
        let second = session(id: "00000000-0000-0000-0000-000000000002", recordedAt: 20)
        let store = WorkoutSessionStore(defaults: defaults)
        store.append(first)
        store.append(second)

        store.remove(first)

        XCTAssertEqual(WorkoutSessionStore(defaults: defaults).sessions, [second])
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
