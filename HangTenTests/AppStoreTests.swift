import XCTest
import Combine
import HealthKit
import UIKit
@testable import HangTen

@MainActor
final class AppStoreTests: XCTestCase {
    private static let healthAuthorizationRequestedKey = "HangTen.healthAuthorizationRequested.v1"
    private static let selectedBoardIDKey = "HangTen.selectedBoardID.v1"

    deinit {}

    func testSelectingBoardUpdatesSelectionAndEmitsOnlyBoardFamily() {
        let telemetry = RecordingTelemetry()
        let store = AppStore(
            defaults: makeDefaults(),
            telemetry: telemetry.dependencies
        )

        let board = BoardCatalog.board(for: "metolius.wood-grips-compact-ii")
        store.selectBoard(board)

        XCTAssertEqual(store.selectedBoard, board)
        XCTAssertEqual(telemetry.events, [
            .boardSelected(family: .compactII)
        ])
    }

    func testSelectedBoardPersistsAndRestoresByStableID() throws {
        let defaults = makeDefaults()
        let board = try XCTUnwrap(
            BoardCatalog.all.first { $0.id != BoardCatalog.defaultBoard.id }
        )

        AppStore(defaults: defaults).selectBoard(board)
        let restored = AppStore(defaults: defaults)

        XCTAssertEqual(defaults.string(forKey: Self.selectedBoardIDKey), board.id)
        XCTAssertEqual(restored.selectedBoard.id, board.id)
    }

    func testUnknownPersistedBoardFallsBackToCatalogDefault() {
        let defaults = makeDefaults()
        defaults.set("removed.board", forKey: Self.selectedBoardIDKey)

        let store = AppStore(defaults: defaults)

        XCTAssertEqual(store.selectedBoard.id, BoardCatalog.defaultBoard.id)
    }

    func testMostRecentSavedLoadAdjustmentUsesLatestLocalSessionRegardlessOfPlan() {
        let olderSession = workoutSessionRecord(
            id: UUID(uuidString: "AAAAAAAA-BBBB-CCCC-DDDD-EEEEEEEEEEEE")!,
            planTitle: "Older plan",
            recordedAt: 100,
            loadAdjustmentKGF: 7.5
        )
        let latestSession = workoutSessionRecord(
            id: UUID(uuidString: "BBBBBBBB-BBBB-CCCC-DDDD-EEEEEEEEEEEE")!,
            planTitle: "Another plan",
            recordedAt: 200,
            loadAdjustmentKGF: -12,
            loadAdjustmentDisplayUnit: .pounds
        )
        let sessionStore = PreloadedWorkoutSessionStore(sessions: [olderSession, latestSession])
        let store = AppStore(
            workoutSessionStore: sessionStore,
            defaults: makeDefaults()
        )

        XCTAssertEqual(store.mostRecentSavedLoadAdjustmentKGF, -12, accuracy: 0.0001)
        XCTAssertEqual(store.mostRecentSavedLoadAdjustmentDisplayUnit, .pounds)
    }

    func testSelectingBoardDerivesTelemetryFamilyFromBoardIDSuffix() {
        let telemetry = RecordingTelemetry()
        let store = AppStore(
            defaults: makeDefaults(),
            telemetry: telemetry.dependencies
        )
        let board = BoardRevision(
            id: "fixture.rock-prodigy-training-center",
            revisionID: "test-fixture",
            manufacturer: "Fixture",
            name: "Rock Prodigy Training Center",
            subtitle: "Fixture board",
            dimensions: "Fixture dimensions",
            aspectRatio: 1,
            contacts: [],
            productURL: URL(string: "https://example.com")!,
            photoAssetName: nil
        )

        store.selectBoard(board)

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
        let definition = try validCustomRoutineDefinition()

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
        let definition = try validCustomRoutineDefinition()

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
            activityPlan(requirement: nil),
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

    func testCompletionBeforeConnectPersistsResolvedActivityContextAndUploadsItAfterConnect() throws {
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
        let requirement = ContactRequirement.edge(depth: .category(.medium))
        let plan = activityPlan(requirement: requirement)
        let board = modelActivityBoard(
            contact: PhysicalContact(
                id: "medium-edge",
                name: "Medium edge",
                kind: .edge,
                depth: .category(.medium)
            )
        )
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

        let pendingContext = try XCTUnwrap(historyStore.load().first?.activityContext)
        let snapshot = try XCTUnwrap(
            pendingContext.activitySegments.first?.target?.resolvedContactSnapshot
        )
        XCTAssertEqual(snapshot.boardID, "activity-board")
        XCTAssertEqual(snapshot.revisionID, "activity-board-revision")
        XCTAssertEqual(snapshot.modelSHA256, "activity-board-model-sha256")
        XCTAssertEqual(snapshot.requirement, requirement)
        XCTAssertEqual(snapshot.contactIDs, ["medium-edge"])

        healthStore.authorizationState = .authorized
        appStore.requestHealthAuthorization()
        waitUntil { healthStore.saveCallCount == 1 }

        XCTAssertEqual(
            healthStore.savedActivityContexts,
            [FakeWorkoutHealthStore.SavedActivityContext(
                boardID: board.id,
                boardName: board.name,
                activitySegments: pendingContext.activitySegments
            )]
        )
    }

    func testCompletionConvenienceOverloadForwardsSelectedEitherHand() throws {
        let suiteName = "AppStoreTests.\(UUID().uuidString)"
        let defaults = UserDefaults(suiteName: suiteName)!
        defer { defaults.removePersistentDomain(forName: suiteName) }
        defaults.set("lattice.mxedge-lift-small", forKey: "HangTen.selectedBoardID.v1")
        defaults.set(true, forKey: "HangTen.healthAuthorizationRequested.v1")
        let historyStore = LocalWorkoutHistoryStore(defaults: defaults)
        let healthStore = FakeWorkoutHealthStore()
        let appStore = AppStore(
            healthKitService: healthStore,
            workoutHistoryStore: historyStore,
            defaults: defaults
        )
        let plan = activityPlan(
            requirement: ContactRequirement(
                kind: .edge,
                depth: .range(.init(minimum: 14, maximum: 14)),
                handCapacity: 1,
                selection: .single
            ),
            handUse: .either,
            side: .both
        )

        appStore.markSessionComplete(
            plan,
            startDate: Date(timeIntervalSinceReferenceDate: 1_000),
            endDate: Date(timeIntervalSinceReferenceDate: 1_010),
            selectedHandSide: .right
        )
        waitUntil { healthStore.saveCallCount == 1 }

        let context = try XCTUnwrap(healthStore.savedActivityContexts.first ?? nil)
        let segment = try XCTUnwrap(context.activitySegments.first)
        XCTAssertEqual(segment.handUse, .single)
        XCTAssertEqual(segment.side, .right)
    }

    func testCompletionForwardsAlternateHandPreferenceWithoutHandSideRequired() throws {
        let suiteName = "AppStoreTests.\(UUID().uuidString)"
        let defaults = UserDefaults(suiteName: suiteName)!
        defer { defaults.removePersistentDomain(forName: suiteName) }
        defaults.set("lattice.mxedge-lift-small", forKey: "HangTen.selectedBoardID.v1")
        defaults.set(true, forKey: "HangTen.healthAuthorizationRequested.v1")
        let historyStore = LocalWorkoutHistoryStore(defaults: defaults)
        let healthStore = FakeWorkoutHealthStore()
        let appStore = AppStore(
            healthKitService: healthStore,
            workoutHistoryStore: historyStore,
            defaults: defaults
        )
        let plan = activityPlan(
            requirement: ContactRequirement(
                kind: .edge,
                depth: .range(.init(minimum: 14, maximum: 14)),
                handCapacity: 1,
                selection: .single
            ),
            handUse: .either,
            side: .both
        )
        let sessionSteps = WorkoutSessionHandResolver.sessionSteps(
            from: plan.steps,
            preference: .alternate,
            boardIsOneHanded: appStore.board(for: plan).isOneHanded
        )

        appStore.markSessionComplete(
            plan,
            startDate: Date(timeIntervalSinceReferenceDate: 1_000),
            endDate: Date(timeIntervalSinceReferenceDate: 1_020),
            handPreference: .alternate,
            sessionSteps: sessionSteps
        )
        waitUntil { healthStore.saveCallCount == 1 }

        let context = try XCTUnwrap(healthStore.savedActivityContexts.first ?? nil)
        XCTAssertEqual(context.activitySegments.count, 2)
        XCTAssertEqual(context.activitySegments.map(\.side), [.left, .right])
        XCTAssertEqual(
            context.activitySegments.map(\.handUse),
            [.single, .single]
        )
        XCTAssertNil(appStore.healthAuthorizationError)
    }

    func testCompletionForwardsBothHandPreferenceAsDoubleBoth() throws {
        let suiteName = "AppStoreTests.\(UUID().uuidString)"
        let defaults = UserDefaults(suiteName: suiteName)!
        defer { defaults.removePersistentDomain(forName: suiteName) }
        defaults.set("lattice.mxedge-lift-small", forKey: "HangTen.selectedBoardID.v1")
        defaults.set(true, forKey: "HangTen.healthAuthorizationRequested.v1")
        let historyStore = LocalWorkoutHistoryStore(defaults: defaults)
        let healthStore = FakeWorkoutHealthStore()
        let appStore = AppStore(
            healthKitService: healthStore,
            workoutHistoryStore: historyStore,
            defaults: defaults
        )
        let plan = activityPlan(
            requirement: ContactRequirement(
                kind: .edge,
                depth: .range(.init(minimum: 14, maximum: 14)),
                handCapacity: 1,
                selection: .single
            ),
            handUse: .either,
            side: .both
        )

        appStore.markSessionComplete(
            plan,
            startDate: Date(timeIntervalSinceReferenceDate: 1_000),
            endDate: Date(timeIntervalSinceReferenceDate: 1_010),
            handPreference: .both
        )
        waitUntil { healthStore.saveCallCount == 1 }

        let context = try XCTUnwrap(healthStore.savedActivityContexts.first ?? nil)
        let segment = try XCTUnwrap(context.activitySegments.first)
        XCTAssertEqual(segment.handUse, .double)
        XCTAssertEqual(segment.side, .both)
        XCTAssertNil(appStore.healthAuthorizationError)
    }

    func testBilateralDoubleOnOneHandedBoardIsCompatibleViaBothModeSingleHold() {
        let board = oneHandedCompatibilityBoard()
        let requirement = ContactRequirement.kind(.pocket, selection: .bilateralPair)
        let plan = TrainingPlan(
            id: "one-handed-bilateral",
            title: "One-handed bilateral",
            subtitle: "",
            level: "",
            sourceLabel: "",
            sourceURL: URL(string: "https://example.com/one-handed-bilateral")!,
            provenance: .adapted,
            boardID: board.id,
            steps: [
                WorkoutStep(
                    id: "bilateral-step",
                    number: 1,
                    title: "Bilateral",
                    instruction: "",
                    accessory: "",
                    duration: 10,
                    phase: .hang,
                    segments: [
                        WorkoutSegment(
                            kind: .work,
                            target: .fromLegacyTargets([requirement]),
                            timing: .fixed,
                            duration: 10
                        )
                    ],
                    handUse: .double,
                    side: .both
                )
            ]
        )
        let store = AppStore(defaults: makeDefaults())

        XCTAssertFalse(
            store.isIncompatible(plan, on: board),
            "Both-hands on a one-handed board must be compatible when single-hold materialization resolves"
        )
        XCTAssertEqual(
            store.contactIDs(for: plan.steps[0], on: board),
            ["one-handed-pocket"]
        )
    }

    func testEitherHandOnOneHandedBoardContactIDsIncludeBothModeSingleHold() {
        let board = oneHandedCompatibilityBoard()
        let requirement = ContactRequirement.kind(.pocket, selection: .single)
        let step = WorkoutStep(
            id: "either-step",
            number: 1,
            title: "Either",
            instruction: "",
            accessory: "",
            duration: 10,
            phase: .hang,
            segments: [
                WorkoutSegment(
                    kind: .work,
                    target: .fromLegacyTargets([requirement]),
                    timing: .fixed,
                    duration: 10
                )
            ],
            handUse: .either,
            side: .both
        )
        let plan = TrainingPlan(
            id: "one-handed-either",
            title: "One-handed either",
            subtitle: "",
            level: "",
            sourceLabel: "",
            sourceURL: URL(string: "https://example.com/one-handed-either")!,
            provenance: .adapted,
            boardID: board.id,
            steps: [step]
        )
        let store = AppStore(defaults: makeDefaults())

        XCTAssertFalse(store.isIncompatible(plan, on: board))
        XCTAssertEqual(store.contactIDs(for: step, on: board), ["one-handed-pocket"])
    }

    func testUnresolvableEitherHandOnOneHandedBoardRemainsIncompatible() {
        let board = oneHandedCompatibilityBoard()
        let requirement = ContactRequirement.kind(.sloper, selection: .single)
        let plan = TrainingPlan(
            id: "one-handed-missing",
            title: "Missing hold",
            subtitle: "",
            level: "",
            sourceLabel: "",
            sourceURL: URL(string: "https://example.com/one-handed-missing")!,
            provenance: .adapted,
            boardID: board.id,
            steps: [
                WorkoutStep(
                    id: "missing-step",
                    number: 1,
                    title: "Missing",
                    instruction: "",
                    accessory: "",
                    duration: 10,
                    phase: .hang,
                    segments: [
                        WorkoutSegment(
                            kind: .work,
                            target: .fromLegacyTargets([requirement]),
                            timing: .fixed,
                            duration: 10
                        )
                    ],
                    handUse: .either,
                    side: .both
                )
            ]
        )
        let store = AppStore(defaults: makeDefaults())

        XCTAssertTrue(
            store.isIncompatible(plan, on: board),
            "Alternate and both-mode paths must both fail when no contact matches"
        )
        XCTAssertEqual(store.contactIDs(for: plan.steps[0], on: board), [])
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
        let plan = activityPlan(requirement: nil)
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

        let plan = activityPlan(requirement: nil)
        appStore.markSessionComplete(plan, startDate: startDate, endDate: endDate)

        waitForHistory(in: appStore)

        let persistedRecords = historyStore.load()
        XCTAssertEqual(persistedRecords.count, 1)
        XCTAssertEqual(healthStore.savedIDs, [persistedRecords[0].id])
        XCTAssertEqual(persistedRecords[0].planTitle, plan.title)
        XCTAssertEqual(persistedRecords[0].startDate, startDate)
        XCTAssertEqual(persistedRecords[0].endDate, endDate)
        XCTAssertEqual(appStore.workoutHistory.source, .localFallback)
        XCTAssertEqual(appStore.workoutHistory.entries.map(\.id), [persistedRecords[0].id])
        XCTAssertEqual(appStore.workoutHistory.sessionCount, 1)
        XCTAssertEqual(appStore.workoutHistory.latestSessionTitle, plan.title)
        XCTAssertEqual(appStore.sessionsCompleted, 1)
        XCTAssertEqual(appStore.lastSessionTitle, plan.title)
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
            activityPlan(requirement: nil),
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
        let plan = activityPlan(requirement: nil, timing: .stopwatch)
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
            activityPlan(requirement: nil),
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
            activityPlan(requirement: nil),
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

    func testCompletionFailsClosedWhenStepGripMetadataIsUnknown() {
        let contact = PhysicalContact(
            id: "edge",
            name: "Edge",
            kind: .edge,
            gripTypes: [.openHand]
        )
        let board = activityBoard(contacts: [contact])
        assertCompletionFailsForUnresolvedTarget(
            plan: activityPlan(
                requirement: .kind(.edge, selection: .single),
                gripType: .halfCrimp,
                boardID: board.id
            ),
            board: board
        )
    }

    func testCompletionRecordsSingleSemanticTargetWithoutSideMetadata() throws {
        let contact = PhysicalContact(id: "edge", name: "Edge", kind: .edge)
        let defaults = makeDefaults()
        defaults.set(true, forKey: Self.healthAuthorizationRequestedKey)
        let healthStore = FakeWorkoutHealthStore()
        let appStore = AppStore(healthKitService: healthStore, defaults: defaults)

        appStore.markSessionComplete(
            activityPlan(
                requirement: .kind(.edge, selection: .single),
                handUse: .single,
                side: .left
            ),
            board: activityBoard(contacts: [contact]),
            stopwatchDurations: [:],
            startDate: Date(timeIntervalSinceReferenceDate: 1_000),
            endDate: Date(timeIntervalSinceReferenceDate: 1_010)
        )
        waitUntil { healthStore.saveCallCount == 1 }

        XCTAssertNil(appStore.healthAuthorizationError)
        let context = try XCTUnwrap(healthStore.savedActivityContexts.first ?? nil)
        XCTAssertEqual(
            context.activitySegments.first?.target?.resolvedContactSnapshot?.contactIDs,
            ["edge"]
        )
    }

    func testCompletionFailsClosedWhenBilateralPairMetadataIsUnknown() {
        let contacts = [
            PhysicalContact(id: "left", name: "Left edge", kind: .edge),
            PhysicalContact(id: "right", name: "Right edge", kind: .edge)
        ]
        let board = activityBoard(contacts: contacts)
        assertCompletionFailsForUnresolvedTarget(
            plan: activityPlan(
                requirement: .kind(.edge, selection: .bilateralPair),
                boardID: board.id
            ),
            board: board
        )
    }

    func testCompletionRecordsSourceLinkedTargetlessWorkWithoutFabricatedHold() throws {
        let defaults = makeDefaults()
        defaults.set(true, forKey: Self.healthAuthorizationRequestedKey)
        let healthStore = FakeWorkoutHealthStore()
        let appStore = AppStore(
            healthKitService: healthStore,
            defaults: defaults
        )
        let plan = activityPlan(requirement: nil)
        let board = activityBoard(contacts: [])

        appStore.markSessionComplete(
            plan,
            board: board,
            stopwatchDurations: [:],
            startDate: Date(timeIntervalSinceReferenceDate: 1_000),
            endDate: Date(timeIntervalSinceReferenceDate: 1_010)
        )
        waitUntil { healthStore.saveCallCount == 1 }

        XCTAssertNil(appStore.healthAuthorizationError)
        let context = try XCTUnwrap(healthStore.savedActivityContexts.first ?? nil)
        XCTAssertEqual(context.activitySegments.count, 1)
        let activityJSON = try WorkoutActivityRecorder().json(
            for: WorkoutActivityMetadata(segments: context.activitySegments)
        )
        XCTAssertTrue(activityJSON.contains(#""target":{"kind":"selfSelected"}"#))
    }

    private func assertCompletionFailsForUnresolvedTarget(
        plan: TrainingPlan,
        board: BoardRevision,
        file: StaticString = #filePath,
        line: UInt = #line
    ) {
        let defaults = makeDefaults()
        defaults.set(true, forKey: Self.healthAuthorizationRequestedKey)
        let healthStore = FakeWorkoutHealthStore()
        let appStore = AppStore(
            healthKitService: healthStore,
            defaults: defaults
        )

        appStore.markSessionComplete(
            plan,
            board: board,
            stopwatchDurations: [:],
            startDate: Date(timeIntervalSinceReferenceDate: 1_000),
            endDate: Date(timeIntervalSinceReferenceDate: 1_010)
        )
        waitUntil({ appStore.healthAuthorizationError != nil }, file: file, line: line)

        XCTAssertEqual(
            appStore.healthAuthorizationError,
            "Session logged in Hang Ten, but Hang Ten could not match a workout activity to the selected board.",
            file: file,
            line: line
        )
        XCTAssertEqual(healthStore.saveCallCount, 0, file: file, line: line)
    }

    private func activityPlan(
        requirement: ContactRequirement?,
        gripType: GripType? = nil,
        handUse: WorkoutHandUse = .double,
        side: WorkoutSide = .both,
        timing: WorkoutSegmentTiming = .fixed,
        boardID: String? = nil
    ) -> TrainingPlan {
        let targets = requirement.map { [$0] } ?? []
        return TrainingPlan(
            id: "activity-plan",
            title: "Activity plan",
            subtitle: "",
            level: "",
            sourceLabel: "Source fixture",
            sourceURL: URL(string: "https://example.com/source")!,
            provenance: .adapted,
            boardID: boardID,
            steps: [
                WorkoutStep(
                    id: "activity-step",
                    number: 1,
                    title: "Activity step",
                    instruction: "Perform the source task.",
                    accessory: "10s",
                    duration: 10,
                    phase: .hang,
                    segments: [
                        WorkoutSegment(
                            kind: .work,
                            target: .fromLegacyTargets(targets),
                            timing: timing,
                            duration: timing == .fixed ? 10 : nil
                        )
                    ],
                    gripType: gripType,
                    handUse: handUse,
                    side: side,
                    timedWorkDuration: timing == .fixed ? 10 : nil
                )
            ]
        )
    }

    private func validCustomRoutineDefinition() throws -> CustomRoutineDefinition {
        let plan = activityPlan(
            requirement: .kind(.jug)
        )
        return try CustomRoutineStore.definition(
            from: plan,
            metadata: PlanMetadata(
                title: plan.title,
                subtitle: plan.subtitle,
                level: plan.level,
                sourceLabel: plan.sourceLabel,
                sourceURL: plan.sourceURL,
                provenance: .custom
            ),
            id: "custom.\(UUID().uuidString)"
        )
    }

    private func activityBoard(contacts: [PhysicalContact]) -> BoardRevision {
        let geometry = Dictionary(uniqueKeysWithValues: contacts.map { contact in
            (
                contact.id,
                [BoardContactPiece(
                    id: "\(contact.id)-piece",
                    contactID: contact.id,
                    frame: CGRect(x: 0, y: 0, width: 0.1, height: 0.1),
                    shape: .roundedRect(cornerRadiusFraction: 0),
                    treatment: .surface
                )]
            )
        })
        return BoardRevision(
            id: "activity-board",
            revisionID: "fixture",
            manufacturer: "Fixture",
            name: "Activity board",
            subtitle: "",
            dimensions: nil,
            aspectRatio: 1,
            contacts: contacts,
            productURL: URL(string: "https://example.com/board")!,
            photoAssetName: nil,
            presentations: [
                BoardPresentation(
                    id: "front",
                    name: "Front",
                    aspectRatio: 1,
                    isDefault: true,
                    media: .raster(
                        BoardRasterMedia(assetPath: "", contactGeometry: geometry)
                    )
                )
            ]
        )
    }

    private func modelActivityBoard(contact: PhysicalContact) -> BoardRevision {
        let descriptor = BoardModelDescriptor(
            schemaVersion: 1,
            coordinateFrame: "board-face-normalized-v1",
            modelSHA256: "activity-board-model-sha256",
            modelBounds: BoardModelBounds(
                minimum: [0, 0, 0],
                maximum: [1, 1, 0.1]
            ),
            nodes: [],
            contacts: [
                contact.id: BoardModelContactDescriptor(
                    nodeIDs: ["Board/Contact/medium-edge"],
                    facePlaneAABB: BoardModelFacePlaneAABB(
                        minimum: [0.1, 0.1, 0],
                        maximum: [0.9, 0.3, 0.1]
                    ),
                    center: [0.5, 0.2, 0.05]
                )
            ]
        )
        return BoardRevision(
            id: "activity-board",
            revisionID: "activity-board-revision",
            manufacturer: "Fixture",
            name: "Activity board",
            subtitle: "",
            dimensions: nil,
            aspectRatio: 1,
            contacts: [contact],
            productURL: URL(string: "https://example.com/board")!,
            photoAssetName: nil,
            presentations: [
                BoardPresentation(
                    id: "model",
                    name: "Model",
                    aspectRatio: 1,
                    isDefault: true,
                    media: .model(
                        BoardModelMedia(
                            assetPath: "assets/board.usdz",
                            descriptorPath: "assets/board.model.json",
                            descriptor: descriptor,
                            display: BoardModelDisplay(
                                camera: BoardModelCamera(
                                    type: "orthographic",
                                    viewDirection: [0, 0, -1],
                                    up: [0, 1, 0],
                                    fitPadding: 0
                                )
                            )
                        )
                    )
                )
            ]
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

    func testSavingCompletedSessionsConsumesOnlyTheTwoFreeCredits() {
        let defaults = makeDefaults()
        let accessStore = WorkoutAccessStore(defaults: defaults)
        let purchases = PurchaseManager(client: FakeStoreKitClient())
        let store = AppStore(
            defaults: defaults,
            workoutAccessStore: accessStore,
            purchaseManager: purchases
        )

        store.recordSavedWorkoutAccess()
        store.recordSavedWorkoutAccess()
        store.recordSavedWorkoutAccess()

        XCTAssertEqual(accessStore.freeWorkoutsUsed, 2)
        XCTAssertEqual(store.workoutLaunchDecision, .requiresPurchase)
    }

    func testPaidAccessDoesNotConsumeFreeWorkoutWhenSessionIsSaved() async {
        let defaults = makeDefaults()
        let accessStore = WorkoutAccessStore(defaults: defaults)
        let purchases = PurchaseManager(
            client: FakeStoreKitClient(
                currentEntitlement: .verified(
                    productID: PurchaseManager.lifetimeProductID
                )
            )
        )
        await purchases.prepare()
        let store = AppStore(
            defaults: defaults,
            workoutAccessStore: accessStore,
            purchaseManager: purchases
        )

        store.recordSavedWorkoutAccess()

        XCTAssertEqual(accessStore.freeWorkoutsUsed, 0)
        XCTAssertEqual(store.workoutLaunchDecision, .allowed)
    }

    func testVerifiedEntitlementAllowsLaunchWhenProductPreparationFails() async {
        let defaults = makeDefaults()
        let purchases = PurchaseManager(
            client: FakeStoreKitClient(
                product: nil,
                currentEntitlement: .verified(
                    productID: PurchaseManager.lifetimeProductID
                )
            )
        )
        await purchases.prepare()
        let store = AppStore(defaults: defaults, purchaseManager: purchases)

        XCTAssertEqual(purchases.state, .productLoadFailed)
        XCTAssertEqual(store.workoutLaunchDecision, .allowed)
    }

    func testSuccessfulSessionPersistenceConsumesCreditOnlyAfterCompletion() {
        let defaults = makeDefaults()
        let accessStore = WorkoutAccessStore(defaults: defaults)
        let sessionStore = ControllableAppendWorkoutSessionStore()
        let store = AppStore(
            workoutSessionStore: sessionStore,
            defaults: defaults,
            workoutAccessStore: accessStore,
            purchaseManager: PurchaseManager(client: FakeStoreKitClient())
        )
        let record = workoutSessionRecord()

        store.markSessionComplete(
            PlanCatalog.metoliusTenMinute,
            startDate: record.startDate,
            endDate: record.endDate,
            session: record
        )

        XCTAssertEqual(accessStore.freeWorkoutsUsed, 0)

        sessionStore.completeAppend(.success(()))
        waitUntil { accessStore.freeWorkoutsUsed == 1 }

        XCTAssertEqual(accessStore.freeWorkoutsUsed, 1)
    }

    func testFailedSessionPersistenceDoesNotConsumeCredit() async {
        let defaults = makeDefaults()
        let accessStore = WorkoutAccessStore(defaults: defaults)
        let sessionStore = ControllableAppendWorkoutSessionStore()
        let store = AppStore(
            workoutSessionStore: sessionStore,
            defaults: defaults,
            workoutAccessStore: accessStore,
            purchaseManager: PurchaseManager(client: FakeStoreKitClient())
        )
        let record = workoutSessionRecord()
        let persistenceFailed = expectation(description: "persistence failure recorded")
        let observation = store.$sessionPersistenceError.dropFirst().sink { error in
            guard error != nil else { return }
            persistenceFailed.fulfill()
        }

        store.markSessionComplete(
            PlanCatalog.metoliusTenMinute,
            startDate: record.startDate,
            endDate: record.endDate,
            session: record
        )
        sessionStore.completeAppend(.failure(SessionAppendTestError.failed))
        await fulfillment(of: [persistenceFailed], timeout: 1)

        XCTAssertEqual(accessStore.freeWorkoutsUsed, 0)
        withExtendedLifetime(observation) {}
    }

    func testLoadingHistoricSessionsDoesNotConsumeCredits() {
        let defaults = makeDefaults()
        let accessStore = WorkoutAccessStore(defaults: defaults)
        let sessionStore = WorkoutSessionStore(defaults: defaults, directory: directory)
        sessionStore.append(workoutSessionRecord())
        sessionStore.flush()

        let store = AppStore(
            workoutSessionStore: sessionStore,
            defaults: defaults,
            workoutAccessStore: accessStore,
            purchaseManager: PurchaseManager(client: FakeStoreKitClient())
        )
        store.flushSessionPersistenceSynchronously()

        XCTAssertEqual(store.sessionHistory.count, 1)
        XCTAssertEqual(accessStore.freeWorkoutsUsed, 0)
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

    func testTwoHandedLatticePlansResolvePairedHoldsOnAtLeastOneBoard() throws {
        let store = AppStore(defaults: makeDefaults())

        for planID in ["research.max-hangs", "research.abrahangs"] {
            let plan = try XCTUnwrap(store.plans.first { $0.id == planID })

            let compatibleBoards = BoardCatalog.all.filter { !store.isIncompatible(plan, on: $0) }
            XCTAssertFalse(
                compatibleBoards.isEmpty,
                "\(planID) must resolve on at least one registered board"
            )

            let resolvesAPair = compatibleBoards.contains { board in
                plan.steps.contains { step in
                    guard !step.isRestStep else { return false }
                    let contacts = (try? ContactResolver.resolve(
                        step.workRequirements,
                        step: step,
                        board: board
                    )) ?? []
                    return contacts.count == 2
                }
            }
            XCTAssertTrue(resolvesAPair, "\(planID) should resolve a two-hold pair on a compatible board")
        }
    }

    private func makeDefaults() -> UserDefaults {
        let suite = "AppStoreTests-\(UUID().uuidString)"
        let defaults = UserDefaults(suiteName: suite)!
        defaults.removePersistentDomain(forName: suite)
        return defaults
    }

    private func oneHandedCompatibilityBoard() -> BoardRevision {
        let contact = PhysicalContact(
            id: "one-handed-pocket",
            name: "One-handed pocket",
            kind: .pocket,
            handCapacity: 1,
            side: .left
        )
        return BoardRevision(
            id: "one-handed-compatibility-board",
            revisionID: "test-fixture",
            manufacturer: "Fixture",
            name: "One-handed board",
            subtitle: "",
            dimensions: "",
            aspectRatio: 1,
            handCapacity: 1,
            contacts: [contact],
            productURL: URL(string: "https://example.com/one-handed-compatibility")!,
            photoAssetName: nil,
            presentations: [
                BoardPresentation(
                    id: "primary",
                    name: "Primary",
                    aspectRatio: 1,
                    isDefault: true,
                    media: .raster(BoardRasterMedia(
                        assetPath: "",
                        contactGeometry: [
                            contact.id: [
                                BoardContactPiece(
                                    id: "\(contact.id)-piece",
                                    contactID: contact.id,
                                    frame: CGRect(x: 0.5, y: 0, width: 0.1, height: 0.1),
                                    shape: .roundedRect(cornerRadiusFraction: 0),
                                    treatment: .surface
                                )
                            ]
                        ]
                    ))
                )
            ]
        )
    }

    private func workoutSessionRecord(
        id: UUID = UUID(uuidString: "AAAAAAAA-BBBB-CCCC-DDDD-EEEEEEEEEEEE")!,
        planTitle: String = "Plan",
        recordedAt: TimeInterval = 20,
        loadAdjustmentKGF: Double = 0,
        loadAdjustmentDisplayUnit: WorkoutLoadAdjustmentDisplayUnit = .kilograms
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
            steps: [],
            loadAdjustmentKGF: loadAdjustmentKGF,
            loadAdjustmentDisplayUnit: loadAdjustmentDisplayUnit
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
            userReports: NoOpTelemetry(),
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

private final class PreloadedWorkoutSessionStore: WorkoutSessionStoring {
    private(set) var sessions: [WorkoutSessionRecord]
    var persistenceError: String? { nil }

    init(sessions: [WorkoutSessionRecord]) {
        self.sessions = sessions
    }

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
        completion(.success(()))
    }

    func flush() {}
}

private enum SessionAppendTestError: Error {
    case failed
}

private final class ControllableAppendWorkoutSessionStore: WorkoutSessionStoring {
    private(set) var sessions: [WorkoutSessionRecord] = []
    var persistenceError: String? { nil }
    private var appendCompletion: ((Result<Void, Error>) -> Void)?

    func append(
        _ session: WorkoutSessionRecord,
        completion: @escaping (Result<Void, Error>) -> Void
    ) {
        sessions.append(session)
        appendCompletion = completion
    }

    func remove(
        _ session: WorkoutSessionRecord,
        completion: @escaping (Result<Void, Error>) -> Void
    ) {
        sessions.removeAll { $0.id == session.id }
        completion(.success(()))
    }

    func flush(completion: @escaping (Result<Void, Error>) -> Void) {
        completion(.success(()))
    }

    func flush() {}

    func completeAppend(_ result: Result<Void, Error>) {
        let completion = appendCompletion
        appendCompletion = nil
        completion?(result)
    }
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
