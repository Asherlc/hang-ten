import XCTest
@testable import HangTen

final class AppStoreTests: XCTestCase {
    func testCompletingSessionUpdatesHistorySnapshotAndSendsPersistedLocalIDToHealthStore() {
        let suiteName = "AppStoreTests.\(UUID().uuidString)"
        let defaults = UserDefaults(suiteName: suiteName)!
        defer { defaults.removePersistentDomain(forName: suiteName) }

        let historyStore = LocalWorkoutHistoryStore(defaults: defaults)
        let healthStore = FakeWorkoutHealthStore()
        let appStore = AppStore(
            healthKitService: healthStore,
            workoutHistoryStore: historyStore
        )
        let startDate = Date(timeIntervalSinceReferenceDate: 1_000)
        let endDate = Date(timeIntervalSinceReferenceDate: 1_600)

        appStore.markSessionComplete(PlanCatalog.all[0], startDate: startDate, endDate: endDate)

        waitForHistory(in: appStore)

        let persistedRecords = historyStore.load()
        XCTAssertEqual(persistedRecords.count, 1)
        XCTAssertEqual(healthStore.savedIDs, [persistedRecords[0].id])
        XCTAssertEqual(persistedRecords[0].planTitle, PlanCatalog.all[0].title)
        XCTAssertEqual(persistedRecords[0].startDate, startDate)
        XCTAssertEqual(persistedRecords[0].endDate, endDate)
        XCTAssertEqual(appStore.workoutHistory.source, .localFallback)
        XCTAssertEqual(appStore.workoutHistory.entries.map(\.id), [persistedRecords[0].id])
        XCTAssertEqual(appStore.workoutHistory.sessionCount, 1)
        XCTAssertEqual(appStore.workoutHistory.latestSessionTitle, PlanCatalog.all[0].title)
        XCTAssertEqual(appStore.sessionsCompleted, 1)
        XCTAssertEqual(appStore.lastSessionTitle, PlanCatalog.all[0].title)
    }

    func testRefreshFailureShowsHistorySyncErrorAndSuccessfulRefreshClearsIt() {
        let suiteName = "AppStoreTests.\(UUID().uuidString)"
        let defaults = UserDefaults(suiteName: suiteName)!
        defer { defaults.removePersistentDomain(forName: suiteName) }
        let historyStore = LocalWorkoutHistoryStore(defaults: defaults)
        historyStore.replace([
            PendingWorkoutRecord(
                id: UUID(),
                planTitle: "Local Plan",
                startDate: Date(timeIntervalSinceReferenceDate: 1_000),
                endDate: Date(timeIntervalSinceReferenceDate: 1_600),
                healthUploadAttempted: true,
                healthWorkoutUUID: nil
            )
        ])
        let healthStore = FakeWorkoutHealthStore(fetchResult: .failure(FakeHealthError.failed))
        let appStore = AppStore(
            healthKitService: healthStore,
            workoutHistoryStore: historyStore,
            defaults: defaults
        )

        appStore.refreshWorkoutHistory()
        waitUntil { appStore.healthAuthorizationError != nil }

        XCTAssertEqual(
            appStore.healthAuthorizationError,
            "Apple Health history could not sync. Local history remains available."
        )
        healthStore.fetchResult = .success([])

        appStore.refreshWorkoutHistory()
        waitUntil { appStore.healthAuthorizationError == nil }

        XCTAssertNil(appStore.healthAuthorizationError)
        XCTAssertEqual(appStore.workoutHistory.source, .localFallback)
    }

    func testCompletionFailureShowsRetrySyncError() {
        let suiteName = "AppStoreTests.\(UUID().uuidString)"
        let defaults = UserDefaults(suiteName: suiteName)!
        defer { defaults.removePersistentDomain(forName: suiteName) }
        let historyStore = LocalWorkoutHistoryStore(defaults: defaults)
        let healthStore = FakeWorkoutHealthStore(saveResult: .failure(FakeHealthError.failed))
        let appStore = AppStore(
            healthKitService: healthStore,
            workoutHistoryStore: historyStore,
            defaults: defaults
        )

        appStore.markSessionComplete(
            PlanCatalog.all[0],
            startDate: Date(timeIntervalSinceReferenceDate: 1_000),
            endDate: Date(timeIntervalSinceReferenceDate: 1_600)
        )
        waitUntil { appStore.healthAuthorizationError != nil }

        XCTAssertEqual(
            appStore.healthAuthorizationError,
            "Session was saved locally and will retry Apple Health sync."
        )
    }

    private func waitForHistory(
        in appStore: AppStore,
        file: StaticString = #filePath,
        line: UInt = #line
    ) {
        let deadline = Date().addingTimeInterval(1)
        while appStore.workoutHistory.sessionCount == 0, Date() < deadline {
            RunLoop.main.run(until: Date().addingTimeInterval(0.01))
        }
        XCTAssertEqual(appStore.workoutHistory.sessionCount, 1, file: file, line: line)
    }

    private func waitUntil(
        _ condition: @escaping () -> Bool,
        file: StaticString = #filePath,
        line: UInt = #line
    ) {
        let deadline = Date().addingTimeInterval(1)
        while !condition(), Date() < deadline {
            RunLoop.main.run(until: Date().addingTimeInterval(0.01))
        }
        XCTAssertTrue(condition(), file: file, line: line)
    }
}

private enum FakeHealthError: Error {
    case failed
}

private final class FakeWorkoutHealthStore: WorkoutHealthStore {
    var isHealthDataAvailable = true
    var authorizationState: HealthAuthorizationState = .authorized
    var fetchResult: Result<[HealthWorkoutRecord], Error>
    var saveResult: Result<UUID, Error>
    private(set) var savedIDs: [UUID] = []

    init(
        fetchResult: Result<[HealthWorkoutRecord], Error> = .success([]),
        saveResult: Result<UUID, Error> = .success(UUID())
    ) {
        self.fetchResult = fetchResult
        self.saveResult = saveResult
    }

    func requestAuthorization(
        completion: @escaping (HealthAuthorizationState, Error?) -> Void
    ) {
        completion(authorizationState, nil)
    }

    func fetchHangTenWorkouts(
        completion: @escaping (Result<[HealthWorkoutRecord], Error>) -> Void
    ) {
        completion(fetchResult)
    }

    func saveCompletedWorkout(
        id: UUID,
        title: String,
        startDate: Date,
        endDate: Date,
        completion: @escaping (Result<UUID, Error>) -> Void
    ) {
        savedIDs.append(id)
        completion(saveResult)
    }
}
