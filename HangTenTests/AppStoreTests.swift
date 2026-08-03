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
}

private final class FakeWorkoutHealthStore: WorkoutHealthStore {
    var isHealthDataAvailable = true
    var authorizationState: HealthAuthorizationState = .authorized
    private(set) var savedIDs: [UUID] = []

    func requestAuthorization(
        completion: @escaping (HealthAuthorizationState, Error?) -> Void
    ) {
        completion(authorizationState, nil)
    }

    func fetchHangTenWorkouts(
        completion: @escaping (Result<[HealthWorkoutRecord], Error>) -> Void
    ) {
        completion(.success([]))
    }

    func saveCompletedWorkout(
        id: UUID,
        title: String,
        startDate: Date,
        endDate: Date,
        completion: @escaping (Result<UUID, Error>) -> Void
    ) {
        savedIDs.append(id)
        completion(.success(UUID()))
    }
}
