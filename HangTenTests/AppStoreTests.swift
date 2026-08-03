import XCTest
import Combine
import UIKit
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
        XCTAssertEqual(store.sessionsCompleted, 1)
        XCTAssertEqual(store.lastSessionTitle, PlanCatalog.metoliusTenMinute.title)
    }

    func testReplacingSessionWithSameIDDoesNotIncreaseCompletedCount() {
        let defaults = makeDefaults()
        let sessionStore = WorkoutSessionStore(defaults: defaults, directory: directory)
        let store = AppStore(
            motherboardBluetoothService: MotherboardBluetoothService(transport: PassiveMotherboardTransport()),
            motherboardSettingsStore: MotherboardSettingsStore(defaults: defaults),
            workoutSessionStore: sessionStore
        )
        let first = workoutSessionRecord(planTitle: "First", recordedAt: 20)
        let replacement = workoutSessionRecord(
            id: first.id,
            planTitle: "Replacement",
            recordedAt: 30
        )

        store.markSessionComplete(
            PlanCatalog.metoliusTenMinute,
            startDate: first.startDate,
            endDate: first.endDate,
            session: first
        )
        store.markSessionComplete(
            PlanCatalog.metoliusTenMinute,
            startDate: replacement.startDate,
            endDate: replacement.endDate,
            session: replacement
        )

        XCTAssertEqual(store.sessionHistory, [replacement])
        XCTAssertEqual(store.sessionsCompleted, store.sessionHistory.count)
        XCTAssertEqual(store.sessionsCompleted, 1)
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

    func testBackgroundPersistenceKeepsBackgroundTaskUntilAsyncFlushCompletes() async {
        let sessionStore = DeferredFlushWorkoutSessionStore()
        let store = AppStore(
            motherboardBluetoothService: MotherboardBluetoothService(transport: PassiveMotherboardTransport()),
            motherboardSettingsStore: MotherboardSettingsStore(defaults: makeDefaults()),
            workoutSessionStore: sessionStore
        )
        let application = RecordingBackgroundTaskApplication()
        let taskEnded = expectation(description: "background task ended")
        application.onEnd = { taskEnded.fulfill() }

        RootViewSessionPersistenceCoordinator(application: application).flush(store: store)

        XCTAssertEqual(application.beginCount, 1)
        XCTAssertTrue(application.endedIdentifiers.isEmpty)
        XCTAssertNotNil(sessionStore.flushCompletion)

        sessionStore.completeFlush(.success(()))

        await fulfillment(of: [taskEnded], timeout: 2)
        XCTAssertEqual(application.endedIdentifiers, [application.taskIdentifier])
    }

    func testSynchronousAppStoreFlushUsesTerminationPath() {
        let sessionStore = DeferredFlushWorkoutSessionStore()
        let store = AppStore(
            motherboardBluetoothService: MotherboardBluetoothService(transport: PassiveMotherboardTransport()),
            motherboardSettingsStore: MotherboardSettingsStore(defaults: makeDefaults()),
            workoutSessionStore: sessionStore
        )

        store.flushSessionPersistenceSynchronously()

        XCTAssertEqual(sessionStore.synchronousFlushCount, 1)
        XCTAssertEqual(sessionStore.asynchronousFlushCount, 0)
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
private final class DeferredFlushWorkoutSessionStore: WorkoutSessionStoring {
    private(set) var sessions: [WorkoutSessionRecord] = []
    var persistenceError: String?
    var flushCompletion: ((Result<Void, Error>) -> Void)?
    private(set) var synchronousFlushCount = 0
    private(set) var asynchronousFlushCount = 0

    func append(
        _ session: WorkoutSessionRecord,
        completion: @escaping (Result<Void, Error>) -> Void
    ) {
        sessions.append(session)
        completion(.success(()))
    }

    func remove(
        _ session: WorkoutSessionRecord,
        completion: @escaping (Result<Void, Error>) -> Void
    ) {
        sessions.removeAll { $0.id == session.id }
        completion(.success(()))
    }

    func flush(completion: @escaping (Result<Void, Error>) -> Void) {
        asynchronousFlushCount += 1
        flushCompletion = completion
    }

    func flush() {
        synchronousFlushCount += 1
    }

    func completeFlush(_ result: Result<Void, Error>) {
        let completion = flushCompletion
        flushCompletion = nil
        DispatchQueue.main.async {
            completion?(result)
        }
    }
}

@MainActor
private final class RecordingBackgroundTaskApplication: RootViewBackgroundTaskApplication {
    let taskIdentifier = UIBackgroundTaskIdentifier(rawValue: 17)
    private(set) var beginCount = 0
    private(set) var endedIdentifiers: [UIBackgroundTaskIdentifier] = []
    var onEnd: (() -> Void)?

    func beginBackgroundTask(
        withName taskName: String?,
        expirationHandler handler: (() -> Void)?
    ) -> UIBackgroundTaskIdentifier {
        beginCount += 1
        return taskIdentifier
    }

    func endBackgroundTask(_ identifier: UIBackgroundTaskIdentifier) {
        endedIdentifiers.append(identifier)
        onEnd?()
    }
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
