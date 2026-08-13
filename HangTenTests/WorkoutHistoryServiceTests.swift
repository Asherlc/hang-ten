import HealthKit
import XCTest
@testable import HangTen

final class WorkoutHistoryServiceTests: XCTestCase {
    private let startDate = Date(timeIntervalSinceReferenceDate: 1_000)
    private let endDate = Date(timeIntervalSinceReferenceDate: 1_600)

    deinit {}

    func testEmptyHealthKitFallsBackToLocalRecords() {
        let local = pendingRecord(
            title: "Local Plan",
            uploadAttempted: false,
            shouldUploadToHealthKit: false
        )
        let persistence = FakeWorkoutHistoryPersistence(records: [local])
        let service = WorkoutHistoryService(
            healthStore: FakeWorkoutHealthStore(),
            persistence: persistence
        )

        refresh(service)

        XCTAssertEqual(service.snapshot.source, .localFallback)
        XCTAssertEqual(service.snapshot.entries.map(\.id), [local.id])
        XCTAssertEqual(service.snapshot.sessionCount, 1)
        XCTAssertEqual(service.snapshot.latestSessionTitle, "Local Plan")
        XCTAssertEqual(persistence.load(), [local])
    }

    func testVisibleHealthKitRecordsBecomeAuthoritative() {
        let healthRecord = workoutRecord(title: "Health Plan")
        let persistence = FakeWorkoutHistoryPersistence()
        let service = WorkoutHistoryService(
            healthStore: FakeWorkoutHealthStore(fetchResult: .success([healthRecord])),
            persistence: persistence
        )

        refresh(service)

        XCTAssertEqual(service.snapshot.source, .healthKit)
        XCTAssertEqual(service.snapshot.entries.map(\.id), [healthRecord.id])
        XCTAssertEqual(service.snapshot.sessionCount, 1)
        XCTAssertEqual(service.snapshot.latestSessionTitle, "Health Plan")
        XCTAssertEqual(persistence.load(), [])
    }

    func testEmptySuccessfulHealthKitQueryWithoutLocalRecordsIsHealthKit() {
        let persistence = FakeWorkoutHistoryPersistence()
        let service = WorkoutHistoryService(
            healthStore: FakeWorkoutHealthStore(),
            persistence: persistence
        )

        refresh(service)

        XCTAssertEqual(service.snapshot.source, .healthKit)
        XCTAssertEqual(service.snapshot.entries, [])
        XCTAssertEqual(service.snapshot.sessionCount, 0)
        XCTAssertNil(service.snapshot.latestSessionTitle)
        XCTAssertEqual(persistence.load(), [])
    }

    func testCompletionPersistsLocallyBeforeHealthKitSave() {
        let persistence = FakeWorkoutHistoryPersistence()
        let healthStore = FakeWorkoutHealthStore()
        var persistedBeforeSave = false
        healthStore.onSave = { _, _, _, _ in
            persistedBeforeSave = persistence.load().count == 1
        }
        let service = WorkoutHistoryService(healthStore: healthStore, persistence: persistence)

        recordCompletion(service, title: "Completed Plan")

        XCTAssertTrue(persistedBeforeSave)
        XCTAssertEqual(healthStore.saveCallCount, 1)
        XCTAssertEqual(service.snapshot.source, .localFallback)
        XCTAssertEqual(service.snapshot.entries.map(\.planTitle), ["Completed Plan"])
        XCTAssertEqual(service.snapshot.sessionCount, 1)
        XCTAssertEqual(service.snapshot.latestSessionTitle, "Completed Plan")
        XCTAssertEqual(persistence.load().count, 1)
        XCTAssertTrue(persistence.load()[0].healthUploadAttempted)
    }

    func testFailedHealthKitSaveRetainsLocalRecordAndError() {
        let local = pendingRecord(title: "Retry Plan")
        let persistence = FakeWorkoutHistoryPersistence(records: [local])
        let healthStore = FakeWorkoutHealthStore(saveResult: .failure(TestError.failed))
        let service = WorkoutHistoryService(healthStore: healthStore, persistence: persistence)

        refresh(service)

        XCTAssertEqual(healthStore.saveCallCount, 1)
        XCTAssertEqual(service.snapshot.source, .localFallback)
        XCTAssertEqual(service.snapshot.entries.map(\.id), [local.id])
        XCTAssertEqual(service.snapshot.sessionCount, 1)
        XCTAssertEqual(service.snapshot.latestSessionTitle, "Retry Plan")
        XCTAssertNotNil(service.lastError)
        XCTAssertEqual(persistence.load().count, 1)
        XCTAssertFalse(persistence.load()[0].healthUploadAttempted)
    }

    func testContextualCompletionPersistsContextAndRetriesItAfterFailedSaveAndRelaunch() {
        let persistence = FakeWorkoutHistoryPersistence()
        let healthStore = FakeWorkoutHealthStore(saveResult: .failure(TestError.failed))
        let activityContext = workoutActivityContext()
        let service = WorkoutHistoryService(healthStore: healthStore, persistence: persistence)

        let completion = expectation(description: "record completion")
        service.recordCompletion(
            planTitle: "Context Plan",
            startDate: startDate,
            endDate: endDate,
            activityContext: activityContext
        ) {
            completion.fulfill()
        }
        wait(for: [completion], timeout: 1)

        XCTAssertEqual(healthStore.savedActivityContexts, [activityContext])
        XCTAssertEqual(persistence.load().count, 1)
        XCTAssertEqual(persistence.load()[0].activityContext, activityContext)
        XCTAssertFalse(persistence.load()[0].healthUploadAttempted)

        let relaunchedStore = FakeWorkoutHealthStore()
        let relaunchedService = WorkoutHistoryService(
            healthStore: relaunchedStore,
            persistence: persistence
        )

        refresh(relaunchedService)

        XCTAssertEqual(relaunchedStore.savedActivityContexts, [activityContext])
    }

    func testFailedContextualSaveRetainsPendingContextUntilHealthKitReconciliation() {
        let healthWorkoutUUID = UUID()
        let activityContext = workoutActivityContext()
        let local = pendingRecord(title: "Reconcile Plan", activityContext: activityContext)
        let persistence = FakeWorkoutHistoryPersistence(records: [local])
        let healthStore = FakeWorkoutHealthStore(saveResult: .failure(TestError.failed))
        let service = WorkoutHistoryService(healthStore: healthStore, persistence: persistence)

        refresh(service)

        XCTAssertEqual(persistence.load().count, 1)
        XCTAssertEqual(persistence.load()[0].activityContext, activityContext)

        healthStore.saveResult = .success(healthWorkoutUUID)
        healthStore.fetchResult = .success([
            workoutRecord(title: "Reconcile Plan", id: healthWorkoutUUID, sessionID: local.id)
        ])

        refresh(service)

        XCTAssertEqual(persistence.load(), [])
    }

    func testSyncRetriesPersistedUploadAttemptWithoutHealthWorkoutUUID() {
        let local = pendingRecord(title: "Interrupted Upload", uploadAttempted: true)
        let persistence = FakeWorkoutHistoryPersistence(records: [local])
        let healthStore = FakeWorkoutHealthStore()
        let service = WorkoutHistoryService(healthStore: healthStore, persistence: persistence)

        refresh(service)

        XCTAssertEqual(healthStore.saveCallCount, 1)
    }

    func testMigrationUploadsEachPendingRecordOnce() {
        let local = pendingRecord(title: "Migration Plan")
        let persistence = FakeWorkoutHistoryPersistence(records: [local])
        let healthStore = FakeWorkoutHealthStore()
        let service = WorkoutHistoryService(healthStore: healthStore, persistence: persistence)

        refresh(service)
        refresh(service)

        XCTAssertEqual(healthStore.saveCallCount, 1)
        XCTAssertEqual(service.snapshot.source, .localFallback)
        XCTAssertEqual(service.snapshot.entries.map(\.id), [local.id])
        XCTAssertEqual(service.snapshot.sessionCount, 1)
        XCTAssertEqual(service.snapshot.latestSessionTitle, "Migration Plan")
        XCTAssertEqual(persistence.load().count, 1)
        XCTAssertTrue(persistence.load()[0].healthUploadAttempted)
    }

    func testCompletionQueuedDuringRefreshIsNotOverwrittenByStaleLocalRecords() {
        let persistence = FakeWorkoutHistoryPersistence()
        let healthStore = FakeWorkoutHealthStore(deferFetch: true)
        let service = WorkoutHistoryService(healthStore: healthStore, persistence: persistence)
        let firstFetch = expectation(description: "initial fetch")
        var observedInitialFetch = false
        healthStore.onFetch = {
            guard !observedInitialFetch else { return }
            observedInitialFetch = true
            firstFetch.fulfill()
        }
        let completions = expectation(description: "both refresh completions")
        completions.expectedFulfillmentCount = 2

        service.refresh { completions.fulfill() }
        wait(for: [firstFetch], timeout: 1)
        service.recordCompletion(
            planTitle: "Concurrent Plan",
            startDate: startDate,
            endDate: endDate
        ) {
            completions.fulfill()
        }
        waitForPersistence(persistence, count: 1)
        healthStore.deferFetch = false
        healthStore.completeNextFetch()
        wait(for: [completions], timeout: 1)

        XCTAssertEqual(service.snapshot.source, .localFallback)
        XCTAssertEqual(service.snapshot.entries.map(\.planTitle), ["Concurrent Plan"])
        XCTAssertEqual(service.snapshot.sessionCount, 1)
        XCTAssertEqual(service.snapshot.latestSessionTitle, "Concurrent Plan")
        XCTAssertEqual(persistence.load().count, 1)
    }

    func testCompletionQueuedDuringSaveIsPreservedThroughFinalRefetch() {
        let initialRecord = pendingRecord(title: "Initial Plan")
        let persistence = FakeWorkoutHistoryPersistence(records: [initialRecord])
        let healthStore = FakeWorkoutHealthStore(deferSave: true)
        let service = WorkoutHistoryService(healthStore: healthStore, persistence: persistence)
        let saveStarted = expectation(description: "initial save started")
        var observedInitialSave = false
        healthStore.onSave = { _, _, _, _ in
            guard !observedInitialSave else { return }
            observedInitialSave = true
            saveStarted.fulfill()
        }
        let completions = expectation(description: "both refresh completions")
        completions.expectedFulfillmentCount = 2

        service.refresh { completions.fulfill() }
        wait(for: [saveStarted], timeout: 1)
        service.recordCompletion(
            planTitle: "Queued Plan",
            startDate: startDate,
            endDate: endDate
        ) {
            completions.fulfill()
        }
        waitForPersistence(persistence, count: 2)
        healthStore.deferSave = false
        healthStore.completeNextSave()
        wait(for: [completions], timeout: 1)

        XCTAssertEqual(service.snapshot.source, .localFallback)
        XCTAssertEqual(Set(service.snapshot.entries.map(\.planTitle)), ["Initial Plan", "Queued Plan"])
        XCTAssertEqual(service.snapshot.sessionCount, 2)
        XCTAssertEqual(persistence.load().map(\.planTitle), ["Initial Plan", "Queued Plan"])
    }

    func testCompletionQueuedDuringFinalRefetchTriggersSecondSyncBeforeCompletionCallbacks() {
        let persistence = FakeWorkoutHistoryPersistence()
        let healthStore = FakeWorkoutHealthStore(deferFetch: true)
        let service = WorkoutHistoryService(healthStore: healthStore, persistence: persistence)
        var fetchCountAtQueuedCompletion: Int?
        let refreshCompletion = expectation(description: "refresh completion")
        let recordCompletion = expectation(description: "record completion")

        service.refresh {
            refreshCompletion.fulfill()
        }
        waitUntil({ healthStore.pendingFetchCount == 1 })
        healthStore.completeNextFetch()
        waitUntil({ healthStore.pendingFetchCount == 1 && healthStore.fetchCallCount == 2 })

        service.recordCompletion(
            planTitle: "Final Refetch Plan",
            startDate: startDate,
            endDate: endDate
        ) {
            fetchCountAtQueuedCompletion = healthStore.fetchCallCount
            recordCompletion.fulfill()
        }
        waitForPersistence(persistence, count: 1)

        XCTAssertEqual(healthStore.saveCallCount, 0)
        healthStore.completeNextFetch()
        waitUntil({ healthStore.pendingFetchCount == 1 && healthStore.fetchCallCount == 3 })
        XCTAssertNil(fetchCountAtQueuedCompletion)

        healthStore.completeNextFetch()
        waitUntil({ healthStore.pendingFetchCount == 1 && healthStore.saveCallCount == 1 })
        XCTAssertNil(fetchCountAtQueuedCompletion)

        healthStore.completeNextFetch()
        wait(for: [refreshCompletion, recordCompletion], timeout: 1)

        XCTAssertEqual(fetchCountAtQueuedCompletion, 4)
        XCTAssertEqual(healthStore.saveCallCount, 1)
        XCTAssertEqual(service.snapshot.entries.map(\.planTitle), ["Final Refetch Plan"])
    }

    func testLegacyHealthWorkoutReconcilesLocalRecordByExactDatesAndTitle() {
        let local = pendingRecord(title: "Legacy Plan", uploadAttempted: true)
        let healthRecord = workoutRecord(title: "Legacy Plan", sessionID: nil)
        let persistence = FakeWorkoutHistoryPersistence(records: [local])
        let service = WorkoutHistoryService(
            healthStore: FakeWorkoutHealthStore(fetchResult: .success([healthRecord])),
            persistence: persistence
        )

        refresh(service)

        XCTAssertEqual(service.snapshot.source, .healthKit)
        XCTAssertEqual(service.snapshot.entries.map(\.id), [healthRecord.id])
        XCTAssertEqual(service.snapshot.sessionCount, 1)
        XCTAssertEqual(service.snapshot.latestSessionTitle, "Legacy Plan")
        XCTAssertEqual(persistence.load(), [])
    }

    func testQueryFailureWithLocalRecordsUsesFallback() {
        let local = pendingRecord(title: "Offline Plan", uploadAttempted: true)
        let persistence = FakeWorkoutHistoryPersistence(records: [local])
        let service = WorkoutHistoryService(
            healthStore: FakeWorkoutHealthStore(fetchResult: .failure(TestError.failed)),
            persistence: persistence
        )

        refresh(service)

        XCTAssertEqual(service.snapshot.source, .localFallback)
        XCTAssertEqual(service.snapshot.entries.map(\.id), [local.id])
        XCTAssertEqual(service.snapshot.sessionCount, 1)
        XCTAssertEqual(service.snapshot.latestSessionTitle, "Offline Plan")
        XCTAssertEqual(persistence.load(), [local])
        XCTAssertNotNil(service.lastError)
    }

    func testReadNotSupportedUploadsPendingRecordThenFallsBackWithoutRefetch() {
        let local = pendingRecord(title: "Write-only Plan")
        let persistence = FakeWorkoutHistoryPersistence(records: [local])
        let savedWorkoutID = UUID()
        let healthStore = FakeWorkoutHealthStore(
            fetchResult: .failure(HealthWorkoutReadError.readNotSupported),
            saveResult: .success(savedWorkoutID)
        )
        let service = WorkoutHistoryService(healthStore: healthStore, persistence: persistence)

        refresh(service)

        XCTAssertEqual(healthStore.fetchCallCount, 1)
        XCTAssertEqual(healthStore.saveCallCount, 1)
        XCTAssertEqual(service.snapshot.source, .localFallback)
        XCTAssertEqual(service.snapshot.entries.map(\.id), [local.id])
        XCTAssertEqual(service.snapshot.sessionCount, 1)
        XCTAssertEqual(service.snapshot.latestSessionTitle, "Write-only Plan")
        XCTAssertEqual(service.lastError as? HealthWorkoutReadError, .readNotSupported)
        XCTAssertEqual(persistence.load().count, 1)
        XCTAssertTrue(persistence.load()[0].healthUploadAttempted)
        XCTAssertEqual(persistence.load()[0].healthWorkoutUUID, savedWorkoutID)
    }

    func testQueryFailureWithoutLocalRecordsIsUnavailable() {
        let persistence = FakeWorkoutHistoryPersistence()
        let service = WorkoutHistoryService(
            healthStore: FakeWorkoutHealthStore(fetchResult: .failure(TestError.failed)),
            persistence: persistence
        )

        refresh(service)

        XCTAssertEqual(service.snapshot.source, .unavailable)
        XCTAssertEqual(service.snapshot.entries, [])
        XCTAssertEqual(service.snapshot.sessionCount, 0)
        XCTAssertNil(service.snapshot.latestSessionTitle)
        XCTAssertEqual(persistence.load(), [])
        XCTAssertNotNil(service.lastError)
    }

    func testStateReturnsSnapshotAndLastErrorFromOneSynchronizedRead() {
        let persistence = FakeWorkoutHistoryPersistence()
        let service = WorkoutHistoryService(
            healthStore: FakeWorkoutHealthStore(fetchResult: .failure(TestError.failed)),
            persistence: persistence
        )

        refresh(service)

        let state = service.state
        XCTAssertEqual(state.snapshot.source, .unavailable)
        XCTAssertEqual(state.snapshot.entries, [])
        XCTAssertNotNil(state.lastError)
    }

    private func refresh(_ service: WorkoutHistoryService, file: StaticString = #filePath, line: UInt = #line) {
        let completion = expectation(description: "refresh completion")
        service.refresh {
            XCTAssertTrue(Thread.isMainThread, file: file, line: line)
            completion.fulfill()
        }
        wait(for: [completion], timeout: 1)
    }

    private func recordCompletion(
        _ service: WorkoutHistoryService,
        title: String,
        file: StaticString = #filePath,
        line: UInt = #line
    ) {
        let completion = expectation(description: "record completion")
        service.recordCompletion(planTitle: title, startDate: startDate, endDate: endDate) {
            XCTAssertTrue(Thread.isMainThread, file: file, line: line)
            completion.fulfill()
        }
        wait(for: [completion], timeout: 1)
    }

    private func waitForPersistence(
        _ persistence: FakeWorkoutHistoryPersistence,
        count: Int,
        file: StaticString = #filePath,
        line: UInt = #line
    ) {
        let deadline = Date().addingTimeInterval(1)
        while persistence.load().count != count, Date() < deadline {
            RunLoop.main.run(until: Date().addingTimeInterval(0.01))
        }
        XCTAssertEqual(persistence.load().count, count, file: file, line: line)
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

    private func pendingRecord(
        title: String,
        uploadAttempted: Bool = false,
        activityContext: PendingWorkoutActivityContext? = nil,
        shouldUploadToHealthKit: Bool = true
    ) -> PendingWorkoutRecord {
        PendingWorkoutRecord(
            id: UUID(),
            planTitle: title,
            startDate: startDate,
            endDate: endDate,
            healthUploadAttempted: uploadAttempted,
            healthWorkoutUUID: nil,
            activityContext: activityContext,
            shouldUploadToHealthKit: shouldUploadToHealthKit
        )
    }

    private func workoutRecord(
        title: String,
        id: UUID = UUID(),
        sessionID: UUID? = UUID()
    ) -> HealthWorkoutRecord {
        HealthWorkoutRecord(
            id: id,
            activityTypeRawValue: HKWorkoutActivityType.functionalStrengthTraining.rawValue,
            brandName: HangTenHealthMetadata.brandName,
            planTitle: title,
            sessionID: sessionID,
            startDate: startDate,
            endDate: endDate
        )
    }

    private func workoutActivityContext() -> PendingWorkoutActivityContext {
        PendingWorkoutActivityContext(
            boardID: "board-a",
            boardName: "Board A",
            activityMetadata: WorkoutActivityMetadata(segments: [
                RecordedActivitySegment(
                    stepID: "step-a",
                    stepNumber: 1,
                    kind: .work,
                    holdIDs: ["a1", "a2"],
                    holdType: "edge",
                    sizeMillimeters: 20,
                    durationSeconds: 7
                )
            ])
        )
    }
}

private enum TestError: Error {
    case failed
}

private final class FakeWorkoutHistoryPersistence: WorkoutHistoryPersistence {
    private let lock = NSLock()
    private var recordsValue: [PendingWorkoutRecord]

    init(records: [PendingWorkoutRecord] = []) {
        recordsValue = records
    }

    deinit {}

    func load() -> [PendingWorkoutRecord] {
        withLock { recordsValue }
    }

    func replace(_ records: [PendingWorkoutRecord]) {
        withLock { recordsValue = records }
    }

    private func withLock<T>(_ body: () -> T) -> T {
        lock.lock()
        defer { lock.unlock() }
        return body()
    }
}

private final class FakeWorkoutHealthStore: WorkoutHealthStore {
    private let lock = NSLock()
    private var isHealthDataAvailableValue = true
    private var authorizationStateValue: HealthAuthorizationState = .authorized
    private var fetchResultValue: Result<[HealthWorkoutRecord], Error>
    private var saveResultValue: Result<UUID, Error>
    private var onSaveValue: ((UUID, String, Date, Date) -> Void)?
    private var onFetchValue: (() -> Void)?
    private var deferFetchValue: Bool
    private var deferSaveValue: Bool
    private var saveCallCountValue = 0
    private var fetchCallCountValue = 0
    private var fetchCompletions: [(Result<[HealthWorkoutRecord], Error>) -> Void] = []
    private var saveCompletions: [(Result<UUID, Error>) -> Void] = []
    private var savedActivityContextsValue: [PendingWorkoutActivityContext?] = []

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

    var onSave: ((UUID, String, Date, Date) -> Void)? {
        get { withLock { onSaveValue } }
        set { withLock { onSaveValue = newValue } }
    }

    var onFetch: (() -> Void)? {
        get { withLock { onFetchValue } }
        set { withLock { onFetchValue = newValue } }
    }

    var deferFetch: Bool {
        get { withLock { deferFetchValue } }
        set { withLock { deferFetchValue = newValue } }
    }

    var deferSave: Bool {
        get { withLock { deferSaveValue } }
        set { withLock { deferSaveValue = newValue } }
    }

    var saveCallCount: Int {
        withLock { saveCallCountValue }
    }

    var fetchCallCount: Int {
        withLock { fetchCallCountValue }
    }

    var pendingFetchCount: Int {
        withLock { fetchCompletions.count }
    }

    var savedActivityContexts: [PendingWorkoutActivityContext?] {
        withLock { savedActivityContextsValue }
    }

    init(
        fetchResult: Result<[HealthWorkoutRecord], Error> = .success([]),
        saveResult: Result<UUID, Error> = .success(UUID()),
        deferFetch: Bool = false,
        deferSave: Bool = false
    ) {
        fetchResultValue = fetchResult
        saveResultValue = saveResult
        deferFetchValue = deferFetch
        deferSaveValue = deferSave
    }

    deinit {}

    func requestAuthorization(
        completion: @escaping (HealthAuthorizationState, Error?) -> Void
    ) {
        let state = withLock { authorizationStateValue }
        completion(state, nil)
    }

    func fetchHangTenWorkouts(
        completion: @escaping (Result<[HealthWorkoutRecord], Error>) -> Void
    ) {
        let (shouldDefer, onFetch) = withLock {
            fetchCallCountValue += 1
            let shouldDefer = deferFetchValue
            if shouldDefer {
                fetchCompletions.append(completion)
            }
            return (shouldDefer, onFetchValue)
        }
        onFetch?()
        if !shouldDefer {
            let result = withLock { fetchResultValue }
            completion(result)
        }
    }

    func completeNextFetch() {
        let (completion, result) = withLock {
            precondition(
                !fetchCompletions.isEmpty,
                "Expected a deferred HealthKit fetch completion before completing the next fetch."
            )
            return (fetchCompletions.removeFirst(), fetchResultValue)
        }
        completion(result)
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

    func saveCompletedWorkout(
        id: UUID,
        title: String,
        startDate: Date,
        endDate: Date,
        completion: @escaping (Result<UUID, Error>) -> Void
    ) {
        let (shouldDefer, onSave) = withLock {
            saveCallCountValue += 1
            savedActivityContextsValue.append(nil)
            let shouldDefer = deferSaveValue
            if shouldDefer {
                saveCompletions.append(completion)
            }
            return (shouldDefer, onSaveValue)
        }
        onSave?(id, title, startDate, endDate)
        if !shouldDefer {
            let result = withLock { saveResultValue }
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
        activityMeasurements: [RecordedActivityStepMeasurement]?,
        completion: @escaping (Result<UUID, Error>) -> Void
    ) {
        let (shouldDefer, onSave) = withLock {
            saveCallCountValue += 1
            savedActivityContextsValue.append(
                PendingWorkoutActivityContext(
                    boardID: boardID,
                    boardName: boardName,
                    activityMetadata: WorkoutActivityMetadata(
                        segments: activitySegments,
                        measurements: activityMeasurements
                    )
                )
            )
            let shouldDefer = deferSaveValue
            if shouldDefer {
                saveCompletions.append(completion)
            }
            return (shouldDefer, onSaveValue)
        }
        onSave?(id, title, startDate, endDate)
        if !shouldDefer {
            let result = withLock { saveResultValue }
            completion(result)
        }
    }

    private func withLock<T>(_ body: () -> T) -> T {
        lock.lock()
        defer { lock.unlock() }
        return body()
    }
}
