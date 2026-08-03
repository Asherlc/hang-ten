import XCTest
@testable import HangTen

final class AppStoreTests: XCTestCase {
    func testCompletingSessionSendsPersistedLocalIDToHealthStore() {
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

        let persistedRecords = historyStore.load()
        XCTAssertEqual(persistedRecords.count, 1)
        XCTAssertEqual(healthStore.savedIDs, [persistedRecords[0].id])
        XCTAssertEqual(persistedRecords[0].planTitle, PlanCatalog.all[0].title)
        XCTAssertEqual(persistedRecords[0].startDate, startDate)
        XCTAssertEqual(persistedRecords[0].endDate, endDate)
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
