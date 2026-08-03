import XCTest
@testable import HangTen

final class AppStoreTests: XCTestCase {
    func testInitializationHydratesPersistedLocalHistoryWithoutHealthKitRead() {
        let suiteName = "AppStoreTests.\(UUID().uuidString)"
        let defaults = UserDefaults(suiteName: suiteName)!
        defer { defaults.removePersistentDomain(forName: suiteName) }

        let local = PendingWorkoutRecord(
            id: UUID(),
            planTitle: "Persisted Plan",
            startDate: Date(timeIntervalSinceReferenceDate: 1_000),
            endDate: Date(timeIntervalSinceReferenceDate: 1_600),
            healthUploadAttempted: false,
            healthWorkoutUUID: nil
        )
        let historyStore = LocalWorkoutHistoryStore(defaults: defaults)
        historyStore.replace([local])
        let healthStore = FakeWorkoutHealthStore()

        let appStore = AppStore(
            healthKitService: healthStore,
            workoutHistoryStore: historyStore,
            defaults: defaults
        )

        XCTAssertEqual(appStore.workoutHistory.source, .localFallback)
        XCTAssertEqual(appStore.workoutHistory.entries.map(\.id), [local.id])
        XCTAssertEqual(appStore.workoutHistory.latestSessionTitle, "Persisted Plan")
        XCTAssertEqual(healthStore.fetchCallCount, 0)
        XCTAssertEqual(healthStore.saveCallCount, 0)
    }

    func testRefreshBeforeConnectUsesLocalFallbackWithoutReadingOrMigrating() {
        let suiteName = "AppStoreTests.\(UUID().uuidString)"
        let defaults = UserDefaults(suiteName: suiteName)!
        defer { defaults.removePersistentDomain(forName: suiteName) }

        let local = PendingWorkoutRecord(
            id: UUID(),
            planTitle: "Waiting Plan",
            startDate: Date(timeIntervalSinceReferenceDate: 1_000),
            endDate: Date(timeIntervalSinceReferenceDate: 1_600),
            healthUploadAttempted: false,
            healthWorkoutUUID: nil
        )
        let historyStore = LocalWorkoutHistoryStore(defaults: defaults)
        historyStore.replace([local])
        let healthStore = FakeWorkoutHealthStore()
        let appStore = AppStore(
            healthKitService: healthStore,
            workoutHistoryStore: historyStore,
            defaults: defaults
        )

        appStore.refreshHealthAuthorization()
        waitUntil { appStore.workoutHistory.sessionCount == 1 }

        XCTAssertEqual(appStore.workoutHistory.source, .localFallback)
        XCTAssertEqual(healthStore.fetchCallCount, 0)
        XCTAssertEqual(healthStore.saveCallCount, 0)
        XCTAssertFalse(historyStore.load()[0].healthUploadAttempted)
    }

    func testCompletionBeforeConnectPersistsLocalFallbackWithoutHealthKitSave() {
        let suiteName = "AppStoreTests.\(UUID().uuidString)"
        let defaults = UserDefaults(suiteName: suiteName)!
        defer { defaults.removePersistentDomain(forName: suiteName) }

        let historyStore = LocalWorkoutHistoryStore(defaults: defaults)
        let healthStore = FakeWorkoutHealthStore()
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
        waitUntil { appStore.workoutHistory.sessionCount == 1 }

        XCTAssertEqual(appStore.workoutHistory.source, .localFallback)
        XCTAssertEqual(healthStore.fetchCallCount, 0)
        XCTAssertEqual(healthStore.saveCallCount, 0)
        XCTAssertEqual(historyStore.load().count, 1)
        XCTAssertFalse(historyStore.load()[0].healthUploadAttempted)
    }

    func testCompletionBeforeConnectDoesNotAttachActivityContextWhenMigratedAfterConnect() {
        let suiteName = "AppStoreTests.\(UUID().uuidString)"
        let defaults = UserDefaults(suiteName: suiteName)!
        defer { defaults.removePersistentDomain(forName: suiteName) }

        let historyStore = LocalWorkoutHistoryStore(defaults: defaults)
        let healthStore = FakeWorkoutHealthStore()
        let appStore = AppStore(
            healthKitService: healthStore,
            workoutHistoryStore: historyStore,
            defaults: defaults
        )
        let plan = PlanCatalog.all[0]
        let board = appStore.board(for: plan)
        let startDate = Date(timeIntervalSinceReferenceDate: 1_000)
        let endDate = Date(timeIntervalSinceReferenceDate: 1_600)

        appStore.markSessionComplete(
            plan,
            board: board,
            stopwatchDurations: [:],
            startDate: startDate,
            endDate: endDate
        )
        waitForHistory(in: appStore)

        appStore.requestHealthAuthorization()
        waitUntil { healthStore.saveCallCount == 1 }

        XCTAssertEqual(healthStore.savedActivityContexts, [nil])
    }

    func testCompletionAfterConnectPreservesActivityContextForHealthWorkoutSaving() throws {
        let suiteName = "AppStoreTests.\(UUID().uuidString)"
        let defaults = UserDefaults(suiteName: suiteName)!
        defer { defaults.removePersistentDomain(forName: suiteName) }

        let healthStore = FakeHealthWorkoutSaving()
        let appStore = AppStore(healthKitService: healthStore, userDefaults: defaults)
        let plan = PlanCatalog.all[0]
        let board = appStore.board(for: plan)
        let startDate = Date(timeIntervalSinceReferenceDate: 1_000)
        let endDate = Date(timeIntervalSinceReferenceDate: 1_600)
        let expectedActivitySegments = try WorkoutActivityRecorder().segments(
            for: plan,
            on: board,
            stopwatchDurations: [:]
        )

        XCTAssertFalse(expectedActivitySegments.isEmpty)

        appStore.requestHealthAuthorization()
        appStore.markSessionComplete(
            plan,
            board: board,
            stopwatchDurations: [:],
            startDate: startDate,
            endDate: endDate
        )
        waitUntil { healthStore.savedWorkouts.count == 1 }

        let savedWorkout = try XCTUnwrap(healthStore.savedWorkouts.first)
        XCTAssertEqual(savedWorkout.boardID, board.id)
        XCTAssertEqual(savedWorkout.boardName, board.name)
        XCTAssertEqual(savedWorkout.activitySegments, expectedActivitySegments)
    }

    func testConnectEnablesHealthKitRefreshAndPendingMigration() {
        let suiteName = "AppStoreTests.\(UUID().uuidString)"
        let defaults = UserDefaults(suiteName: suiteName)!
        defer { defaults.removePersistentDomain(forName: suiteName) }

        let local = PendingWorkoutRecord(
            id: UUID(),
            planTitle: "Migration Plan",
            startDate: Date(timeIntervalSinceReferenceDate: 1_000),
            endDate: Date(timeIntervalSinceReferenceDate: 1_600),
            healthUploadAttempted: false,
            healthWorkoutUUID: nil
        )
        let historyStore = LocalWorkoutHistoryStore(defaults: defaults)
        historyStore.replace([local])
        let healthStore = FakeWorkoutHealthStore()
        let appStore = AppStore(
            healthKitService: healthStore,
            workoutHistoryStore: historyStore,
            defaults: defaults
        )

        appStore.refreshHealthAuthorization()
        waitUntil { appStore.workoutHistory.sessionCount == 1 }
        XCTAssertEqual(healthStore.fetchCallCount, 0)
        XCTAssertEqual(healthStore.saveCallCount, 0)

        appStore.requestHealthAuthorization()
        waitUntil { healthStore.saveCallCount == 1 }

        XCTAssertEqual(healthStore.requestCallCount, 1)
        XCTAssertGreaterThan(healthStore.fetchCallCount, 0)
        XCTAssertTrue(defaults.bool(forKey: "HangTen.healthAuthorizationRequested.v1"))
    }

    func testCancelledAuthorizationKeepsConnectActionAvailableAfterRequestWasPersisted() {
        let suiteName = "AppStoreTests.\(UUID().uuidString)"
        let defaults = UserDefaults(suiteName: suiteName)!
        defer { defaults.removePersistentDomain(forName: suiteName) }
        defaults.set(true, forKey: "HangTen.healthAuthorizationRequested.v1")

        let healthStore = FakeWorkoutHealthStore()
        healthStore.authorizationState = .notDetermined
        let appStore = AppStore(
            healthKitService: healthStore,
            workoutHistoryStore: LocalWorkoutHistoryStore(defaults: defaults),
            defaults: defaults
        )

        appStore.requestHealthAuthorization()
        waitUntil { healthStore.requestCallCount == 1 }

        XCTAssertEqual(appStore.healthAuthorizationState, .notDetermined)
        XCTAssertTrue(appStore.hasRequestedHealthAuthorization)
        XCTAssertTrue(appStore.shouldShowConnectAppleHealth)
    }

    func testAuthorizedEmptyHealthKitHistoryKeepsConnectActionAvailableAfterRefresh() {
        let suiteName = "AppStoreTests.\(UUID().uuidString)"
        let defaults = UserDefaults(suiteName: suiteName)!
        defer { defaults.removePersistentDomain(forName: suiteName) }
        defaults.set(true, forKey: "HangTen.healthAuthorizationRequested.v1")

        let healthStore = FakeWorkoutHealthStore(fetchResult: .success([]))
        healthStore.authorizationState = .authorized
        let appStore = AppStore(
            healthKitService: healthStore,
            workoutHistoryStore: LocalWorkoutHistoryStore(defaults: defaults),
            defaults: defaults
        )

        appStore.refreshHealthAuthorization()
        waitUntil { appStore.workoutHistory.source == .healthKit }

        XCTAssertTrue(appStore.workoutHistory.entries.isEmpty)
        XCTAssertTrue(appStore.shouldShowConnectAppleHealth)
    }

    func testCompletingSessionUpdatesHistorySnapshotAndSendsPersistedLocalIDToHealthStore() {
        let suiteName = "AppStoreTests.\(UUID().uuidString)"
        let defaults = UserDefaults(suiteName: suiteName)!
        defer { defaults.removePersistentDomain(forName: suiteName) }
        defaults.set(true, forKey: "HangTen.healthAuthorizationRequested.v1")

        let historyStore = LocalWorkoutHistoryStore(defaults: defaults)
        let healthStore = FakeWorkoutHealthStore()
        let appStore = AppStore(
            healthKitService: healthStore,
            workoutHistoryStore: historyStore,
            defaults: defaults
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
        defaults.set(true, forKey: "HangTen.healthAuthorizationRequested.v1")
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
        defaults.set(true, forKey: "HangTen.healthAuthorizationRequested.v1")
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

    func testCoalescedRefreshPreservesCompletionErrorUntilIndependentRefresh() {
        let suiteName = "AppStoreTests.\(UUID().uuidString)"
        let defaults = UserDefaults(suiteName: suiteName)!
        defer { defaults.removePersistentDomain(forName: suiteName) }
        defaults.set(true, forKey: "HangTen.healthAuthorizationRequested.v1")
        let historyStore = LocalWorkoutHistoryStore(defaults: defaults)
        let healthStore = FakeWorkoutHealthStore(
            saveResult: .failure(FakeHealthError.failed),
            deferSave: true
        )
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
        waitUntil { healthStore.saveCallCount == 1 }
        appStore.refreshWorkoutHistory()
        healthStore.completeNextSave()
        waitUntil { appStore.healthAuthorizationError != nil }

        XCTAssertEqual(
            appStore.healthAuthorizationError,
            "Session was saved locally and will retry Apple Health sync."
        )

        healthStore.saveResult = .success(UUID())
        healthStore.deferSave = false
        appStore.refreshWorkoutHistory()
        waitUntil { appStore.healthAuthorizationError == nil }
        XCTAssertNil(appStore.healthAuthorizationError)

        healthStore.fetchResult = .failure(FakeHealthError.failed)
        appStore.refreshWorkoutHistory()
        waitUntil { appStore.healthAuthorizationError != nil }

        XCTAssertEqual(
            appStore.healthAuthorizationError,
            "Apple Health history could not sync. Local history remains available."
        )
    }

    func testAuthorizationRequestResetsCompletionErrorPriorityBeforeRefreshFailure() {
        let suiteName = "AppStoreTests.\(UUID().uuidString)"
        let defaults = UserDefaults(suiteName: suiteName)!
        defer { defaults.removePersistentDomain(forName: suiteName) }
        defaults.set(true, forKey: "HangTen.healthAuthorizationRequested.v1")
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
        healthStore.fetchResult = .failure(FakeHealthError.failed)

        appStore.requestHealthAuthorization()
        waitUntil { appStore.healthAuthorizationError != nil }

        XCTAssertEqual(
            appStore.healthAuthorizationError,
            "Apple Health history could not sync. Local history remains available."
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

private final class FakeHealthWorkoutSaving: HealthWorkoutSaving {
    struct SavedWorkout {
        let boardID: String
        let boardName: String
        let activitySegments: [RecordedActivitySegment]
    }

    var authorizationState: HealthAuthorizationState = .authorized
    private(set) var savedWorkouts: [SavedWorkout] = []

    func requestAuthorization(
        completion: @escaping (HealthAuthorizationState, Error?) -> Void
    ) {
        completion(authorizationState, nil)
    }

    func saveCompletedWorkout(
        title: String,
        startDate: Date,
        endDate: Date,
        boardID: String,
        boardName: String,
        activitySegments: [RecordedActivitySegment],
        completion: @escaping (Error?) -> Void
    ) {
        savedWorkouts.append(
            SavedWorkout(
                boardID: boardID,
                boardName: boardName,
                activitySegments: activitySegments
            )
        )
        completion(nil)
    }
}

private final class FakeWorkoutHealthStore: WorkoutHealthStore {
    struct SavedActivityContext: Equatable {
        let boardID: String
        let boardName: String
        let activitySegments: [RecordedActivitySegment]
    }

    var isHealthDataAvailable = true
    var authorizationState: HealthAuthorizationState = .authorized
    var fetchResult: Result<[HealthWorkoutRecord], Error>
    var saveResult: Result<UUID, Error>
    var deferSave: Bool
    private(set) var savedIDs: [UUID] = []
    private(set) var savedActivityContexts: [SavedActivityContext?] = []
    private(set) var requestCallCount = 0
    private(set) var fetchCallCount = 0
    private(set) var saveCallCount = 0
    private var saveCompletions: [(Result<UUID, Error>) -> Void] = []

    init(
        fetchResult: Result<[HealthWorkoutRecord], Error> = .success([]),
        saveResult: Result<UUID, Error> = .success(UUID()),
        deferSave: Bool = false
    ) {
        self.fetchResult = fetchResult
        self.saveResult = saveResult
        self.deferSave = deferSave
    }

    func requestAuthorization(
        completion: @escaping (HealthAuthorizationState, Error?) -> Void
    ) {
        requestCallCount += 1
        completion(authorizationState, nil)
    }

    func fetchHangTenWorkouts(
        completion: @escaping (Result<[HealthWorkoutRecord], Error>) -> Void
    ) {
        fetchCallCount += 1
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
        savedActivityContexts.append(nil)
        saveCallCount += 1
        if deferSave {
            saveCompletions.append(completion)
        } else {
            completion(saveResult)
        }
    }

    func saveCompletedWorkout(
        id: UUID,
        title: String,
        startDate: Date,
        endDate: Date,
        boardID: String,
        boardName: String,
        activitySegments: [RecordedActivitySegment],
        completion: @escaping (Result<UUID, Error>) -> Void
    ) {
        savedIDs.append(id)
        savedActivityContexts.append(
            SavedActivityContext(
                boardID: boardID,
                boardName: boardName,
                activitySegments: activitySegments
            )
        )
        saveCallCount += 1
        if deferSave {
            saveCompletions.append(completion)
        } else {
            completion(saveResult)
        }
    }

    func completeNextSave() {
        saveCompletions.removeFirst()(saveResult)
    }
}
