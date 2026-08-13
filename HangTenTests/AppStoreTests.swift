import XCTest
import Combine
import HealthKit
import UIKit
@testable import HangTen

@MainActor
final class AppStoreTests: XCTestCase {
    private static let healthAuthorizationRequestedKey = "HangTen.healthAuthorizationRequested.v1"

    deinit {}

    func testSelectingBoardUpdatesSelectionAndEmitsOnlyBoardFamily() {
        let telemetry = RecordingTelemetry()
        let store = AppStore(
            defaults: makeDefaults(),
            telemetry: telemetry.dependencies
        )

        let board = BoardCatalog.board(for: "trango.rock-prodigy-training-center")
        store.selectBoard(board)

        XCTAssertEqual(store.selectedBoard, board)
        XCTAssertEqual(telemetry.events, [
            .boardSelected(family: .rockProdigyTrainingCenter)
        ])
    }

    func testTelemetryDependenciesDoNotRetainRecordingTelemetry() {
        weak var releasedTelemetry: RecordingTelemetry?

        do {
            let telemetry = RecordingTelemetry()
            releasedTelemetry = telemetry
            _ = telemetry.dependencies
        }

        XCTAssertNil(releasedTelemetry)
    }

    func testSavingCustomRoutineEmitsEventAfterPersistenceSucceeds() throws {
        let telemetry = RecordingTelemetry()
        let store = AppStore(
            defaults: makeDefaults(),
            telemetry: telemetry.dependencies
        )
        let definition = try store.duplicateRoutine(PlanCatalog.all[0])

        try store.saveCustomRoutine(definition)

        XCTAssertEqual(telemetry.events, [.customRoutineSaved])
    }

    func testFailingCustomRoutineSaveRecordsCategoricalPersistenceDiagnostic() throws {
        let telemetry = RecordingTelemetry()
        let store = AppStore(
            customRoutineStore: FailingCustomRoutineStore(),
            defaults: makeDefaults(),
            telemetry: telemetry.dependencies
        )
        let definition = try store.duplicateRoutine(PlanCatalog.all[0])

        XCTAssertThrowsError(try store.saveCustomRoutine(definition))

        XCTAssertEqual(telemetry.diagnostics.count, 1)
        XCTAssertEqual(telemetry.diagnostics[0].category, .persistence)
        XCTAssertEqual(telemetry.diagnostics[0].operation, .save)
        XCTAssertEqual(telemetry.diagnostics[0].errorKind, .other)
    }

    func testHealthAuthorizationDeniedEmitsCategoricalResult() {
        let telemetry = RecordingTelemetry()
        let healthStore = FakeWorkoutHealthStore()
        healthStore.authorizationState = .denied
        let store = AppStore(
            healthKitService: healthStore,
            defaults: makeDefaults(),
            telemetry: telemetry.dependencies
        )

        store.requestHealthAuthorization()

        waitUntil {
            telemetry.events == [.healthAuthorizationFinished(outcome: .denied)]
        }
        XCTAssertEqual(telemetry.events, [.healthAuthorizationFinished(outcome: .denied)])
    }

    func testHealthAuthorizationPausesReplayUntilTheAuthorizationResultIsHandled() {
        let telemetry = RecordingTelemetry()
        let healthStore = FakeWorkoutHealthStore()
        healthStore.authorizationState = .denied
        let store = AppStore(
            healthKitService: healthStore,
            defaults: makeDefaults(),
            telemetry: telemetry.dependencies
        )

        store.requestHealthAuthorization()

        XCTAssertEqual(telemetry.actions, [.replayStopped])
        waitUntil {
            telemetry.actions == [
                .replayStopped,
                .healthAuthorizationFinished(outcome: .denied),
                .replayStarted
            ]
        }
    }

    func testHealthAuthorizationNotDeterminedDoesNotEmitOutcome() {
        let telemetry = RecordingTelemetry()
        let healthStore = FakeWorkoutHealthStore()
        healthStore.authorizationState = .notDetermined
        let store = AppStore(
            healthKitService: healthStore,
            defaults: makeDefaults(),
            telemetry: telemetry.dependencies
        )

        store.requestHealthAuthorization()
        let expectation = expectation(description: "authorization callback completes")
        DispatchQueue.main.async { expectation.fulfill() }
        wait(for: [expectation], timeout: 1)

        XCTAssertEqual(telemetry.events, [])
    }

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
        healthStore.authorizationState = .notDetermined
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
        healthStore.authorizationState = .notDetermined
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
        healthStore.authorizationState = .notDetermined
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

        healthStore.authorizationState = .authorized
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
        healthStore.authorizationState = .notDetermined
        let appStore = AppStore(
            healthKitService: healthStore,
            workoutHistoryStore: historyStore,
            defaults: defaults
        )

        appStore.refreshHealthAuthorization()
        waitUntil { appStore.workoutHistory.sessionCount == 1 }
        XCTAssertEqual(healthStore.fetchCallCount, 0)
        XCTAssertEqual(healthStore.saveCallCount, 0)

        healthStore.authorizationState = .authorized
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

    func testAuthorizedEmptyHealthKitHistoryHidesConnectActionAfterRefresh() {
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

        XCTAssertEqual(appStore.healthAuthorizationState, .authorized)
        XCTAssertTrue(appStore.workoutHistory.entries.isEmpty)
        XCTAssertFalse(appStore.shouldShowConnectAppleHealth)
    }

    func testAuthorizedHealthKitHidesConnectActionWithoutPersistedRequestFlag() {
        let suiteName = "AppStoreTests.\(UUID().uuidString)"
        let defaults = UserDefaults(suiteName: suiteName)!
        defer { defaults.removePersistentDomain(forName: suiteName) }

        let healthStore = FakeWorkoutHealthStore(fetchResult: .success([]))
        healthStore.authorizationState = .authorized
        let appStore = AppStore(
            healthKitService: healthStore,
            workoutHistoryStore: LocalWorkoutHistoryStore(defaults: defaults),
            defaults: defaults
        )

        XCTAssertFalse(appStore.hasRequestedHealthAuthorization)
        XCTAssertFalse(appStore.shouldShowConnectAppleHealth)
    }

    func testAuthorizedHealthKitReconcilesSyncAndImportsHistoryWithoutPrompting() {
        let suiteName = "AppStoreTests.\(UUID().uuidString)"
        let defaults = UserDefaults(suiteName: suiteName)!
        defer { defaults.removePersistentDomain(forName: suiteName) }

        let healthRecord = HealthWorkoutRecord(
            id: UUID(),
            activityTypeRawValue: HKWorkoutActivityType.functionalStrengthTraining.rawValue,
            brandName: HangTenHealthMetadata.brandName,
            planTitle: "Authorized Plan",
            sessionID: UUID(),
            startDate: Date(timeIntervalSinceReferenceDate: 1_000),
            endDate: Date(timeIntervalSinceReferenceDate: 1_600)
        )
        let healthStore = FakeWorkoutHealthStore(fetchResult: .success([healthRecord]))
        healthStore.authorizationState = .authorized
        let appStore = AppStore(
            healthKitService: healthStore,
            workoutHistoryStore: LocalWorkoutHistoryStore(defaults: defaults),
            defaults: defaults
        )

        XCTAssertFalse(appStore.hasRequestedHealthAuthorization)
        XCTAssertFalse(defaults.bool(forKey: Self.healthAuthorizationRequestedKey))

        appStore.refreshHealthAuthorization()
        waitUntil { appStore.workoutHistory.source == .healthKit }

        XCTAssertEqual(appStore.healthAuthorizationState, .authorized)
        XCTAssertTrue(appStore.hasRequestedHealthAuthorization)
        XCTAssertTrue(defaults.bool(forKey: Self.healthAuthorizationRequestedKey))
        XCTAssertEqual(appStore.workoutHistory.entries.map(\.id), [healthRecord.id])
        XCTAssertGreaterThan(healthStore.fetchCallCount, 0)
        XCTAssertEqual(healthStore.requestCallCount, 0)
        XCTAssertEqual(healthStore.saveCallCount, 0)
        XCTAssertFalse(appStore.shouldShowConnectAppleHealth)
    }

    func testNotDeterminedWithoutPersistedRequestFlagKeepsConnectActionAndLocalHistory() {
        let suiteName = "AppStoreTests.\(UUID().uuidString)"
        let defaults = UserDefaults(suiteName: suiteName)!
        defer { defaults.removePersistentDomain(forName: suiteName) }

        let healthStore = FakeWorkoutHealthStore(fetchResult: .success([]))
        healthStore.authorizationState = .notDetermined
        let appStore = AppStore(
            healthKitService: healthStore,
            workoutHistoryStore: LocalWorkoutHistoryStore(defaults: defaults),
            defaults: defaults
        )

        XCTAssertEqual(appStore.healthAuthorizationState, .notDetermined)
        XCTAssertFalse(appStore.hasRequestedHealthAuthorization)
        XCTAssertFalse(defaults.bool(forKey: Self.healthAuthorizationRequestedKey))
        XCTAssertTrue(appStore.shouldShowConnectAppleHealth)

        appStore.refreshHealthAuthorization()

        XCTAssertEqual(appStore.healthAuthorizationState, .notDetermined)
        XCTAssertEqual(appStore.workoutHistory.source, .unavailable)
        XCTAssertEqual(healthStore.fetchCallCount, 0)
        XCTAssertEqual(healthStore.requestCallCount, 0)
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
        activityMeasurements: [RecordedActivityStepMeasurement]?,
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
        activityMeasurements: [RecordedActivityStepMeasurement]?,
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

    // Main-branch session persistence coverage continues in the same test case.
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
            workoutSessionStore: sessionStore,
            defaults: defaults
        )
        store.flushSessionPersistenceSynchronously()

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
            workoutSessionStore: sessionStore,
            defaults: defaults
        )
        store.flushSessionPersistenceSynchronously()

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
            workoutSessionStore: sessionStore,
            defaults: defaults
        )
        store.flushSessionPersistenceSynchronously()

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
            workoutSessionStore: sessionStore,
            defaults: defaults
        )
        store.flushSessionPersistenceSynchronously()
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
        let defaults = makeDefaults()
        let sessionStore = FailingWorkoutSessionStore()
        let store = AppStore(
            motherboardBluetoothService: MotherboardBluetoothService(transport: PassiveMotherboardTransport()),
            motherboardSettingsStore: MotherboardSettingsStore(defaults: defaults),
            workoutSessionStore: sessionStore,
            defaults: defaults
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
        let defaults = makeDefaults()
        let sessionStore = DeferredFlushWorkoutSessionStore()
        let store = AppStore(
            motherboardBluetoothService: MotherboardBluetoothService(transport: PassiveMotherboardTransport()),
            motherboardSettingsStore: MotherboardSettingsStore(defaults: defaults),
            workoutSessionStore: sessionStore,
            defaults: defaults
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
        let defaults = makeDefaults()
        let sessionStore = DeferredFlushWorkoutSessionStore()
        let store = AppStore(
            motherboardBluetoothService: MotherboardBluetoothService(transport: PassiveMotherboardTransport()),
            motherboardSettingsStore: MotherboardSettingsStore(defaults: defaults),
            workoutSessionStore: sessionStore,
            defaults: defaults
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

@MainActor
private final class RecordingTelemetry: TelemetryTracking, DiagnosticReporting, SessionReplayControlling {
    enum Action: Equatable {
        case healthAuthorizationFinished(outcome: HangTenTelemetryEvent.HealthAuthorizationOutcome)
        case replayStarted
        case replayStopped
    }

    private(set) var events: [HangTenTelemetryEvent] = []
    private(set) var diagnostics: [HangTenDiagnostic] = []
    private(set) var actions: [Action] = []

    var dependencies: TelemetryDependencies {
        TelemetryDependencies(
            tracking: self,
            diagnostics: self,
            flags: NoOpTelemetry(),
            replay: self,
            isNoOp: false
        )
    }

    deinit {}

    func track(_ event: HangTenTelemetryEvent) {
        events.append(event)
        if case let .healthAuthorizationFinished(outcome) = event {
            actions.append(.healthAuthorizationFinished(outcome: outcome))
        }
    }

    func record(_ diagnostic: HangTenDiagnostic) {
        diagnostics.append(diagnostic)
    }

    func start() {
        actions.append(.replayStarted)
    }

    func stop() {
        actions.append(.replayStopped)
    }
}

private final class FailingCustomRoutineStore: CustomRoutineStoring {
    private struct Failure: Error {}

    let routines: [CustomRoutineDefinition] = []
    let persistenceError: String? = nil

    deinit {}

    func save(_ routine: CustomRoutineDefinition) throws {
        throw Failure()
    }

    func delete(id: String) throws {}

    func plan(for definition: CustomRoutineDefinition) throws -> TrainingPlan {
        fatalError("The failing store contains no routines.")
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
        expirationHandler handler: (@MainActor @Sendable () -> Void)?
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
