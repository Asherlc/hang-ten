import HealthKit
import XCTest
@testable import HangTen

final class WorkoutHistoryServiceTests: XCTestCase {
    private let startDate = Date(timeIntervalSinceReferenceDate: 1_000)
    private let endDate = Date(timeIntervalSinceReferenceDate: 1_600)

    func testEmptyHealthKitFallsBackToLocalRecords() {
        let local = pendingRecord(title: "Local Plan", uploadAttempted: true)
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

    func testEmptyHealthKitWithoutLocalRecordsIsUnavailable() {
        let persistence = FakeWorkoutHistoryPersistence()
        let service = WorkoutHistoryService(
            healthStore: FakeWorkoutHealthStore(),
            persistence: persistence
        )

        refresh(service)

        XCTAssertEqual(service.snapshot.source, .unavailable)
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
        healthStore.onFetch = { firstFetch.fulfill() }
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

    private func pendingRecord(
        title: String,
        uploadAttempted: Bool = false
    ) -> PendingWorkoutRecord {
        PendingWorkoutRecord(
            id: UUID(),
            planTitle: title,
            startDate: startDate,
            endDate: endDate,
            healthUploadAttempted: uploadAttempted,
            healthWorkoutUUID: nil
        )
    }

    private func workoutRecord(
        title: String,
        sessionID: UUID? = UUID()
    ) -> HealthWorkoutRecord {
        HealthWorkoutRecord(
            id: UUID(),
            activityTypeRawValue: HKWorkoutActivityType.functionalStrengthTraining.rawValue,
            brandName: HangTenHealthMetadata.brandName,
            planTitle: title,
            sessionID: sessionID,
            startDate: startDate,
            endDate: endDate
        )
    }
}

private enum TestError: Error {
    case failed
}

private final class FakeWorkoutHistoryPersistence: WorkoutHistoryPersistence {
    private var records: [PendingWorkoutRecord]

    init(records: [PendingWorkoutRecord] = []) {
        self.records = records
    }

    func load() -> [PendingWorkoutRecord] {
        records
    }

    func replace(_ records: [PendingWorkoutRecord]) {
        self.records = records
    }
}

private final class FakeWorkoutHealthStore: WorkoutHealthStore {
    var isHealthDataAvailable = true
    var authorizationState: HealthAuthorizationState = .authorized
    var fetchResult: Result<[HealthWorkoutRecord], Error>
    var saveResult: Result<UUID, Error>
    var onSave: ((UUID, String, Date, Date) -> Void)?
    var onFetch: (() -> Void)?
    var deferFetch: Bool
    var deferSave: Bool
    private(set) var saveCallCount = 0
    private var fetchCompletions: [(Result<[HealthWorkoutRecord], Error>) -> Void] = []
    private var saveCompletions: [(Result<UUID, Error>) -> Void] = []

    init(
        fetchResult: Result<[HealthWorkoutRecord], Error> = .success([]),
        saveResult: Result<UUID, Error> = .success(UUID()),
        deferFetch: Bool = false,
        deferSave: Bool = false
    ) {
        self.fetchResult = fetchResult
        self.saveResult = saveResult
        self.deferFetch = deferFetch
        self.deferSave = deferSave
    }

    func requestAuthorization(
        completion: @escaping (HealthAuthorizationState, Error?) -> Void
    ) {
        completion(authorizationState, nil)
    }

    func fetchHangTenWorkouts(
        completion: @escaping (Result<[HealthWorkoutRecord], Error>) -> Void
    ) {
        onFetch?()
        if deferFetch {
            fetchCompletions.append(completion)
        } else {
            completion(fetchResult)
        }
    }

    func completeNextFetch() {
        fetchCompletions.removeFirst()(fetchResult)
    }

    func completeNextSave() {
        saveCompletions.removeFirst()(saveResult)
    }

    func saveCompletedWorkout(
        id: UUID,
        title: String,
        startDate: Date,
        endDate: Date,
        completion: @escaping (Result<UUID, Error>) -> Void
    ) {
        saveCallCount += 1
        onSave?(id, title, startDate, endDate)
        if deferSave {
            saveCompletions.append(completion)
        } else {
            completion(saveResult)
        }
    }
}
