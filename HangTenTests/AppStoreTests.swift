import XCTest
import Combine
@testable import HangTen

@MainActor
final class AppStoreTests: XCTestCase {
    private var directory: URL!

    override func setUp() {
        super.setUp()
        directory = FileManager.default.temporaryDirectory
            .appendingPathComponent("AppStoreTests-\(UUID().uuidString)", isDirectory: true)
    }

    override func tearDown() {
        try? FileManager.default.removeItem(at: directory)
        super.tearDown()
    }

    func testLaunchRestoresDashboardCountersFromNewestSavedHistory() {
        let defaults = makeDefaults()
        let sessionStore = WorkoutSessionStore(defaults: defaults, directory: directory)
        let older = workoutSessionRecord(
            id: UUID(uuidString: "AAAAAAAA-BBBB-CCCC-DDDD-EEEEEEEEEEEE")!,
            planTitle: "Older plan",
            recordedAt: 20
        )
        let newer = workoutSessionRecord(
            id: UUID(uuidString: "BBBBBBBB-CCCC-DDDD-EEEE-FFFFFFFFFFFF")!,
            planTitle: "Newest plan",
            recordedAt: 30
        )
        sessionStore.append(older)
        sessionStore.append(newer)

        let store = AppStore(
            motherboardBluetoothService: MotherboardBluetoothService(transport: PassiveMotherboardTransport()),
            motherboardSettingsStore: MotherboardSettingsStore(defaults: defaults),
            workoutSessionStore: sessionStore
        )

        XCTAssertEqual(store.sessionHistory, [newer, older])
        XCTAssertEqual(store.sessionsCompleted, 2)
        XCTAssertEqual(store.lastSessionTitle, "Newest plan")
    }

    func testCompletionPersistsSuppliedRecordAndExposesSessionHistory() {
        let defaults = makeDefaults()
        let sessionStore = WorkoutSessionStore(defaults: defaults, directory: directory)
        let record = workoutSessionRecord()
        let store = AppStore(
            motherboardBluetoothService: MotherboardBluetoothService(transport: PassiveMotherboardTransport()),
            motherboardSettingsStore: MotherboardSettingsStore(defaults: defaults),
            workoutSessionStore: sessionStore
        )

        store.markSessionComplete(
            PlanCatalog.metoliusTenMinute,
            startDate: record.startDate,
            endDate: record.endDate,
            session: record
        )

        XCTAssertEqual(store.sessionHistory, [record])
        XCTAssertEqual(sessionStore.sessions, [record])
        XCTAssertEqual(store.sessionsCompleted, 1)
        XCTAssertEqual(store.lastSessionTitle, PlanCatalog.metoliusTenMinute.title)
    }

    func testCompletionWithoutRecordPreservesExistingHistory() {
        let defaults = makeDefaults()
        let sessionStore = WorkoutSessionStore(defaults: defaults, directory: directory)
        let existingRecord = workoutSessionRecord()
        sessionStore.append(existingRecord)
        let store = AppStore(
            motherboardBluetoothService: MotherboardBluetoothService(transport: PassiveMotherboardTransport()),
            motherboardSettingsStore: MotherboardSettingsStore(defaults: defaults),
            workoutSessionStore: sessionStore
        )

        store.markSessionComplete(
            PlanCatalog.metoliusTenMinute,
            startDate: Date(timeIntervalSince1970: 100),
            endDate: Date(timeIntervalSince1970: 200)
        )

        XCTAssertEqual(store.sessionHistory, [existingRecord])
        XCTAssertEqual(sessionStore.sessions, [existingRecord])
        XCTAssertEqual(store.sessionsCompleted, 2)
        XCTAssertEqual(store.lastSessionTitle, PlanCatalog.metoliusTenMinute.title)
    }

    func testCompletionExposesSessionPersistenceFailure() async {
        let sessionStore = FailingWorkoutSessionStore()
        let store = AppStore(
            motherboardBluetoothService: MotherboardBluetoothService(transport: PassiveMotherboardTransport()),
            motherboardSettingsStore: MotherboardSettingsStore(defaults: makeDefaults()),
            workoutSessionStore: sessionStore
        )
        let errorUpdated = expectation(description: "persistence error updated")
        let observation = store.$sessionPersistenceError.dropFirst().sink { error in
            guard error == "Session history could not be saved: Storage is unavailable." else { return }
            errorUpdated.fulfill()
        }

        let record = workoutSessionRecord()
        store.markSessionComplete(
            PlanCatalog.metoliusTenMinute,
            startDate: record.startDate,
            endDate: record.endDate,
            session: record
        )

        await fulfillment(of: [errorUpdated], timeout: 2)
        withExtendedLifetime(observation) {}
    }

    private func makeDefaults() -> UserDefaults {
        let suite = "AppStoreTests-\(UUID().uuidString)"
        let defaults = UserDefaults(suiteName: suite)!
        defaults.removePersistentDomain(forName: suite)
        return defaults
    }

    private func workoutSessionRecord(
        id: UUID = UUID(uuidString: "AAAAAAAA-BBBB-CCCC-DDDD-EEEEEEEEEEEE")!,
        planTitle: String = "Plan",
        recordedAt: TimeInterval = 20
    ) -> WorkoutSessionRecord {
        WorkoutSessionRecord(
            id: id,
            planID: "plan",
            planTitle: planTitle,
            recordedAt: Date(timeIntervalSince1970: recordedAt),
            startDate: Date(timeIntervalSince1970: recordedAt - 10),
            endDate: Date(timeIntervalSince1970: recordedAt),
            motherboardIdentifier: nil,
            batteryValue: nil,
            steps: []
        )
    }
}

private final class FailingWorkoutSessionStore: WorkoutSessionStoring {
    private struct Failure: LocalizedError {
        var errorDescription: String? { "Storage is unavailable." }
    }

    private(set) var sessions: [WorkoutSessionRecord] = []
    var persistenceError: String? { nil }

    func append(
        _ session: WorkoutSessionRecord,
        completion: @escaping (Result<Void, Error>) -> Void
    ) {
        sessions.append(session)
        DispatchQueue.main.async {
            completion(.failure(Failure()))
        }
    }

    func remove(
        _ session: WorkoutSessionRecord,
        completion: @escaping (Result<Void, Error>) -> Void
    ) {
        sessions.removeAll { $0.id == session.id }
        DispatchQueue.main.async {
            completion(.failure(Failure()))
        }
    }

    func flush(completion: @escaping (Result<Void, Error>) -> Void) {
        DispatchQueue.main.async {
            completion(.failure(Failure()))
        }
    }

    func flush() {}
}

@MainActor
private final class PassiveMotherboardTransport: MotherboardTransport {
    var eventHandler: ((MotherboardTransportEvent) -> Void)?

    func startScan() {}
    func stopScan() {}
    func connect(to device: MotherboardDiscoveredDevice) {}
    func disconnect() {}
    func setTXNotificationsEnabled(_ enabled: Bool) {}
    func write(_ data: Data) {}
}
