import XCTest
@testable import HangTen

final class AppStoreTests: XCTestCase {
    private static let healthAuthorizationRequestedKey = "HangTen.healthAuthorizationRequested.v1"

    deinit {}

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

    func testWriteOnlyHealthStoreUsesLocalFallbackWhenHistoryReadIsUnsupported() {
        let suiteName = "AppStoreTests.\(UUID().uuidString)"
        let defaults = UserDefaults(suiteName: suiteName)!
        defer { defaults.removePersistentDomain(forName: suiteName) }
        defaults.set(true, forKey: Self.healthAuthorizationRequestedKey)

        let local = PendingWorkoutRecord(
            id: UUID(),
            planTitle: "Write-only Plan",
            startDate: Date(timeIntervalSinceReferenceDate: 1_000),
            endDate: Date(timeIntervalSinceReferenceDate: 1_600),
            healthUploadAttempted: false,
            healthWorkoutUUID: nil,
            shouldUploadToHealthKit: false
        )
        let historyStore = LocalWorkoutHistoryStore(defaults: defaults)
        historyStore.replace([local])
        let healthStore = FakeHealthWorkoutSaving()
        let appStore = AppStore(
            healthKitService: healthStore,
            workoutHistoryStore: historyStore,
            defaults: defaults
        )

        appStore.refreshWorkoutHistory()
        waitUntil { appStore.healthAuthorizationError != nil }

        XCTAssertEqual(appStore.workoutHistory.source, .localFallback)
        XCTAssertEqual(appStore.workoutHistory.entries.map(\.id), [local.id])
        XCTAssertEqual(
            appStore.healthAuthorizationError,
            "Apple Health history could not sync. Local history remains available."
        )
    }

    func testCompletionAfterConnectPreservesActivityContextForHealthWorkoutSaving() throws {
        let suiteName = "AppStoreTests.\(UUID().uuidString)"
        let defaults = UserDefaults(suiteName: suiteName)!
        defer { defaults.removePersistentDomain(forName: suiteName) }

        let healthStore = FakeHealthWorkoutSaving()
        healthStore.authorizationState = .notDetermined
        let appStore = AppStore(
            healthKitService: healthStore,
            workoutHistoryStore: LocalWorkoutHistoryStore(defaults: defaults),
            defaults: defaults
        )
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

        healthStore.authorizationState = .authorized
        appStore.requestHealthAuthorization()
        waitUntil { appStore.healthAuthorizationState == .authorized }
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
        XCTAssertTrue(defaults.bool(forKey: Self.healthAuthorizationRequestedKey))
    }

    func testCancelledAuthorizationKeepsConnectActionAvailableAfterRequestWasPersisted() {
        let suiteName = "AppStoreTests.\(UUID().uuidString)"
        let defaults = UserDefaults(suiteName: suiteName)!
        defer { defaults.removePersistentDomain(forName: suiteName) }
        defaults.set(true, forKey: Self.healthAuthorizationRequestedKey)

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
        defaults.set(true, forKey: Self.healthAuthorizationRequestedKey)

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
        defaults.set(true, forKey: Self.healthAuthorizationRequestedKey)

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
        defaults.set(true, forKey: Self.healthAuthorizationRequestedKey)
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
        defaults.set(true, forKey: Self.healthAuthorizationRequestedKey)
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

    func testActivityRecordingFailureKeepsLocalHistoryAndDoesNotSaveIncompleteHealthWorkout() {
        let suiteName = "AppStoreTests.\(UUID().uuidString)"
        let defaults = UserDefaults(suiteName: suiteName)!
        defer { defaults.removePersistentDomain(forName: suiteName) }
        defaults.set(true, forKey: Self.healthAuthorizationRequestedKey)
        let historyStore = LocalWorkoutHistoryStore(defaults: defaults)
        let healthStore = FakeWorkoutHealthStore()
        let appStore = AppStore(
            healthKitService: healthStore,
            workoutHistoryStore: historyStore,
            defaults: defaults
        )
        let plan = PlanCatalog.all.first { plan in
            plan.steps.contains { step in
                step.segments.contains { $0.timing == .stopwatch }
            }
        }!
        let stopwatchStep = plan.steps.first { step in
            step.segments.contains { $0.timing == .stopwatch }
        }!
        let stopwatchIndex = stopwatchStep.segments.firstIndex { $0.timing == .stopwatch }!
        let invalidDuration = WorkoutActivitySegmentKey(
            stepID: stopwatchStep.id,
            segmentIndex: stopwatchIndex
        )

        appStore.markSessionComplete(
            plan,
            board: appStore.board(for: plan),
            stopwatchDurations: [invalidDuration: -.infinity],
            startDate: Date(timeIntervalSinceReferenceDate: 1_000),
            endDate: Date(timeIntervalSinceReferenceDate: 1_600)
        )
        waitForHistory(in: appStore)

        XCTAssertEqual(appStore.workoutHistory.sessionCount, 1)
        XCTAssertEqual(historyStore.load().count, 1)
        XCTAssertEqual(
            appStore.healthAuthorizationError,
            "Session logged in Hang Ten, but Hang Ten could not use the recorded workout duration."
        )
        XCTAssertEqual(healthStore.saveCallCount, 0)
    }

    func testCoalescedRefreshPreservesCompletionErrorUntilIndependentRefresh() {
        let suiteName = "AppStoreTests.\(UUID().uuidString)"
        let defaults = UserDefaults(suiteName: suiteName)!
        defer { defaults.removePersistentDomain(forName: suiteName) }
        defaults.set(true, forKey: Self.healthAuthorizationRequestedKey)
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
        defaults.set(true, forKey: Self.healthAuthorizationRequestedKey)
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

    private let lock = NSLock()
    private var authorizationStateValue: HealthAuthorizationState = .authorized
    private var savedWorkoutsValue: [SavedWorkout] = []

    var authorizationState: HealthAuthorizationState {
        get { withLock { authorizationStateValue } }
        set { withLock { authorizationStateValue = newValue } }
    }

    var savedWorkouts: [SavedWorkout] {
        withLock { savedWorkoutsValue }
    }

    deinit {}

    func requestAuthorization(
        completion: @escaping (HealthAuthorizationState, Error?) -> Void
    ) {
        let state = withLock { authorizationStateValue }
        completion(state, nil)
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
        withLock {
            savedWorkoutsValue.append(
                SavedWorkout(
                    boardID: boardID,
                    boardName: boardName,
                    activitySegments: activitySegments
                )
            )
        }
        completion(nil)
    }

    private func withLock<T>(_ body: () -> T) -> T {
        lock.lock()
        defer { lock.unlock() }
        return body()
    }
}

private final class FakeWorkoutHealthStore: WorkoutHealthStore {
    struct SavedActivityContext: Equatable {
        let boardID: String
        let boardName: String
        let activitySegments: [RecordedActivitySegment]
    }

    private let lock = NSLock()
    private var isHealthDataAvailableValue = true
    private var authorizationStateValue: HealthAuthorizationState = .authorized
    private var fetchResultValue: Result<[HealthWorkoutRecord], Error>
    private var saveResultValue: Result<UUID, Error>
    private var deferSaveValue: Bool
    private var savedIDsValue: [UUID] = []
    private var savedActivityContextsValue: [SavedActivityContext?] = []
    private var requestCallCountValue = 0
    private var fetchCallCountValue = 0
    private var saveCallCountValue = 0
    private var saveCompletions: [(Result<UUID, Error>) -> Void] = []

    var isHealthDataAvailable: Bool {
        get { withLock { isHealthDataAvailableValue } }
        set { withLock { isHealthDataAvailableValue = newValue } }
    }

    var authorizationState: HealthAuthorizationState {
        get { withLock { authorizationStateValue } }
        set { withLock { authorizationStateValue = newValue } }
    }

    var fetchResult: Result<[HealthWorkoutRecord], Error> {
        get { withLock { fetchResultValue } }
        set { withLock { fetchResultValue = newValue } }
    }

    var saveResult: Result<UUID, Error> {
        get { withLock { saveResultValue } }
        set { withLock { saveResultValue = newValue } }
    }

    var deferSave: Bool {
        get { withLock { deferSaveValue } }
        set { withLock { deferSaveValue = newValue } }
    }

    var savedIDs: [UUID] {
        withLock { savedIDsValue }
    }

    var savedActivityContexts: [SavedActivityContext?] {
        withLock { savedActivityContextsValue }
    }

    var requestCallCount: Int {
        withLock { requestCallCountValue }
    }

    var fetchCallCount: Int {
        withLock { fetchCallCountValue }
    }

    var saveCallCount: Int {
        withLock { saveCallCountValue }
    }

    init(
        fetchResult: Result<[HealthWorkoutRecord], Error> = .success([]),
        saveResult: Result<UUID, Error> = .success(UUID()),
        deferSave: Bool = false
    ) {
        fetchResultValue = fetchResult
        saveResultValue = saveResult
        deferSaveValue = deferSave
    }

    deinit {}

    func requestAuthorization(
        completion: @escaping (HealthAuthorizationState, Error?) -> Void
    ) {
        let state = withLock {
            requestCallCountValue += 1
            return authorizationStateValue
        }
        completion(state, nil)
    }

    func fetchHangTenWorkouts(
        completion: @escaping (Result<[HealthWorkoutRecord], Error>) -> Void
    ) {
        let result = withLock {
            fetchCallCountValue += 1
            return fetchResultValue
        }
        completion(result)
    }

    func saveCompletedWorkout(
        id: UUID,
        title: String,
        startDate: Date,
        endDate: Date,
        completion: @escaping (Result<UUID, Error>) -> Void
    ) {
        let (result, shouldDefer) = withLock {
            savedIDsValue.append(id)
            savedActivityContextsValue.append(nil)
            saveCallCountValue += 1
            let shouldDefer = deferSaveValue
            if shouldDefer {
                saveCompletions.append(completion)
            }
            return (saveResultValue, shouldDefer)
        }
        if !shouldDefer {
            completion(result)
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
        let (result, shouldDefer) = withLock {
            savedIDsValue.append(id)
            savedActivityContextsValue.append(
                SavedActivityContext(
                    boardID: boardID,
                    boardName: boardName,
                    activitySegments: activitySegments
                )
            )
            saveCallCountValue += 1
            let shouldDefer = deferSaveValue
            if shouldDefer {
                saveCompletions.append(completion)
            }
            return (saveResultValue, shouldDefer)
        }
        if !shouldDefer {
            completion(result)
        }
    }

    func completeNextSave() {
        let (completion, result) = withLock {
            precondition(
                !saveCompletions.isEmpty,
                "Expected a deferred HealthKit save completion before completing the next save."
            )
            return (saveCompletions.removeFirst(), saveResultValue)
        }
        completion(result)
    }

    private func withLock<T>(_ body: () -> T) -> T {
        lock.lock()
        defer { lock.unlock() }
        return body()
    }
}
