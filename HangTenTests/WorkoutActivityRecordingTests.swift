import XCTest
import HealthKit
import Combine
@testable import HangTen

@MainActor
final class WorkoutActivityRecordingTests: XCTestCase {
    private var sessionStoreDirectory: URL!
    private var sessionStores: [WorkoutSessionStore] = []

    override func setUp() {
        super.setUp()
        sessionStoreDirectory = FileManager.default.temporaryDirectory
            .appendingPathComponent(
                "WorkoutActivityRecordingTests-\(UUID().uuidString)",
                isDirectory: true
            )
    }

    override func tearDown() {
        cleanUpSessionStores()
        super.tearDown()
    }

    private let board = TrainingBoard(
        id: "fixture.board",
        manufacturer: "Fixture",
        name: "Board",
        subtitle: "",
        dimensions: "",
        aspectRatio: 2,
        holds: [
            BoardHold(
                id: "edge-left",
                name: "Left medium edge",
                shortLabel: "L",
                detail: "Medium edge",
                kind: .edge,
                frame: HoldFrame(x: 0, y: 0, width: 0.2, height: 0.2),
                sizeMillimeters: 21,
                features: [.mediumEdge]
            ),
            BoardHold(
                id: "edge-right",
                name: "Right medium edge",
                shortLabel: "R",
                detail: "Medium edge",
                kind: .edge,
                frame: HoldFrame(x: 0.8, y: 0, width: 0.2, height: 0.2),
                sizeMillimeters: 21,
                features: [.mediumEdge]
            ),
            BoardHold(
                id: "edge-deep",
                name: "Deep edge",
                shortLabel: "D",
                detail: "Large edge",
                kind: .edge,
                frame: HoldFrame(x: 0.3, y: 0.3, width: 0.2, height: 0.2),
                sizeMillimeters: 35,
                features: [.largeEdge]
            ),
            BoardHold(
                id: "jug-center",
                name: "Center jug",
                shortLabel: "J",
                detail: "Jug",
                kind: .jug,
                frame: HoldFrame(x: 0.4, y: 0.7, width: 0.2, height: 0.2)
            )
        ],
        productURL: URL(string: "https://example.com/board")!,
        photoAssetName: nil
    )

    private func makeDefaults() -> UserDefaults {
        let suiteName = "WorkoutActivityRecordingTests.\(UUID().uuidString)"
        let defaults = UserDefaults(suiteName: suiteName)!
        defaults.removePersistentDomain(forName: suiteName)
        return defaults
    }

    private func makeHealthConnectedDefaults() -> UserDefaults {
        let defaults = makeDefaults()
        defaults.set(true, forKey: "HangTen.healthAuthorizationRequested.v1")
        return defaults
    }

    private func makeSessionStore(
        defaults: UserDefaults,
        fileManager: FileManager = .default
    ) -> WorkoutSessionStore {
        let store = WorkoutSessionStore(
            defaults: defaults,
            directory: sessionStoreDirectory,
            fileManager: fileManager
        )
        sessionStores.append(store)
        return store
    }

    private func cleanUpSessionStores() {
        sessionStores.forEach { $0.flush() }
        sessionStores.removeAll()
        if let sessionStoreDirectory {
            try? FileManager.default.removeItem(at: sessionStoreDirectory)
        }
        sessionStoreDirectory = nil
    }

    func testSessionStoreCleanupWaitsForQueuedPersistenceBeforeRemovingDirectory() async {
        let directory = sessionStoreDirectory!
        let writeStarted = expectation(description: "session write started")
        let writeFinished = expectation(description: "session write finished")
        let fileManager = BlockingWorkoutActivityFileManager(
            writeStarted: writeStarted,
            writeFinished: writeFinished
        )
        let store = makeSessionStore(defaults: makeDefaults(), fileManager: fileManager)
        let record = WorkoutSessionRecord(
            id: UUID(),
            planID: "plan",
            planTitle: "Plan",
            recordedAt: Date(timeIntervalSinceReferenceDate: 1_010),
            startDate: Date(timeIntervalSinceReferenceDate: 1_000),
            endDate: Date(timeIntervalSinceReferenceDate: 1_010),
            motherboardIdentifier: nil,
            batteryValue: nil,
            steps: []
        )

        store.append(record)
        await fulfillment(of: [writeStarted], timeout: 30)
        let allowWrite = fileManager.allowWrite
        DispatchQueue.global().asyncAfter(deadline: .now() + 0.1) {
            allowWrite.signal()
        }

        cleanUpSessionStores()

        await fulfillment(of: [writeFinished], timeout: 30)
        XCTAssertFalse(FileManager.default.fileExists(atPath: directory.path))
    }

    private func plan(
        instruction: String = "Use the named board feature",
        _ segments: [WorkoutSegment]
    ) -> TrainingPlan {
        TrainingPlan(
            id: "plan",
            title: "Plan",
            subtitle: "",
            level: "",
            sourceLabel: "",
            sourceURL: URL(string: "https://example.com/plan")!,
            provenance: .adapted,
            boardID: board.id,
            steps: [
                WorkoutStep(
                    id: "step",
                    number: 1,
                    title: "Step",
                    instruction: instruction,
                    accessory: "",
                    duration: 60,
                    phase: .hang,
                    targets: [],
                    segments: segments
                )
            ]
        )
    }

    func testSemanticTargetUsesBoardTypeSizeAndFixedDuration() throws {
        let workout = plan(
            instruction: "Hang from the medium edge",
            [
                WorkoutSegment(
                    kind: .work,
                    target: .feature(.mediumEdge),
                    timing: .fixed,
                    duration: 12
                )
            ]
        )

        let records = try WorkoutActivityRecorder().segments(for: workout, on: board)

        XCTAssertEqual(records.count, 1)
        XCTAssertEqual(records[0].holdType, "edge")
        XCTAssertEqual(records[0].sizeMillimeters, 21)
        XCTAssertEqual(records[0].durationSeconds, 12)
    }

    func testMultiTargetWorkRecordsAllHoldsWithOneDuration() throws {
        let segment = WorkoutSegment(
            kind: .work,
            targets: [.ids("edge-left"), .ids("jug-center")],
            timing: .fixed,
            duration: 10
        )

        let records = try WorkoutActivityRecorder().segments(
            for: plan([segment]),
            on: board
        )

        XCTAssertEqual(records.count, 1)
        XCTAssertEqual(records[0].holdIDs, ["edge-left", "jug-center"])
        XCTAssertNil(records[0].holdType)
        XCTAssertNil(records[0].sizeMillimeters)
        XCTAssertEqual(records[0].durationSeconds, 10)
    }

    func testFixedWorkFollowedByRestPreservesOrderAndDurations() throws {
        let workout = plan([
            WorkoutSegment(
                kind: .work,
                target: .ids("edge-left"),
                timing: .fixed,
                duration: 20
            ),
            WorkoutSegment(kind: .rest, target: nil, timing: .fixed, duration: 10)
        ])

        let records = try WorkoutActivityRecorder().segments(for: workout, on: board)

        XCTAssertEqual(records.map(\.kind), [.work, .rest])
        XCTAssertEqual(records.map(\.durationSeconds), [20, 10])
        XCTAssertEqual(records[1].holdIDs, [])
        XCTAssertNil(records[1].holdType)
        XCTAssertNil(records[1].sizeMillimeters)
    }

    func testStopwatchWorkUsesSuppliedObservedDuration() throws {
        let workout = plan([
            WorkoutSegment(
                kind: .work,
                target: .ids("edge-left"),
                timing: .stopwatch,
                duration: nil
            )
        ])
        let key = WorkoutActivitySegmentKey(stepID: "step", segmentIndex: 0)

        let records = try WorkoutActivityRecorder().segments(
            for: workout,
            on: board,
            stopwatchDurations: [key: 8.75]
        )

        XCTAssertEqual(records[0].durationSeconds, 8.75)
    }

    func testStopwatchWorkWithoutObservedDurationIsNil() throws {
        let workout = plan([
            WorkoutSegment(
                kind: .work,
                target: .ids("edge-left"),
                timing: .stopwatch,
                duration: nil
            )
        ])

        let records = try WorkoutActivityRecorder().segments(for: workout, on: board)

        XCTAssertNil(records[0].durationSeconds)
    }

    func testUndefinedWorkDurationIsNil() throws {
        let workout = plan([
            WorkoutSegment(
                kind: .work,
                target: .ids("edge-left"),
                timing: .undefined,
                duration: 30
            )
        ])

        let records = try WorkoutActivityRecorder().segments(for: workout, on: board)

        XCTAssertNil(records[0].durationSeconds)
    }

    func testLeftAndRightHoldsWithMatchingDescriptorsStayGrouped() throws {
        let workout = plan([
            WorkoutSegment(
                kind: .work,
                target: .ids("edge-left", "edge-right"),
                timing: .fixed,
                duration: 10
            )
        ])

        let records = try WorkoutActivityRecorder().segments(for: workout, on: board)

        XCTAssertEqual(records.count, 1)
        XCTAssertEqual(records[0].holdIDs, ["edge-left", "edge-right"])
    }

    func testDifferentKindAndSizeDescriptorsProduceSeparateRecords() throws {
        let workout = plan([
            WorkoutSegment(
                kind: .work,
                target: .ids("edge-left", "edge-deep", "jug-center"),
                timing: .fixed,
                duration: 10
            )
        ])

        let records = try WorkoutActivityRecorder().segments(for: workout, on: board)

        XCTAssertEqual(records.count, 3)
        XCTAssertEqual(records[0].holdIDs, ["edge-left"])
        XCTAssertEqual(records[0].holdType, "edge")
        XCTAssertEqual(records[0].sizeMillimeters, 21)
        XCTAssertEqual(records[1].holdIDs, ["edge-deep"])
        XCTAssertEqual(records[1].holdType, "edge")
        XCTAssertEqual(records[1].sizeMillimeters, 35)
        XCTAssertEqual(records[2].holdIDs, ["jug-center"])
        XCTAssertEqual(records[2].holdType, "jug")
        XCTAssertNil(records[2].sizeMillimeters)
    }

    func testRepeatedSourceSegmentsRemainDistinct() throws {
        let repeated = WorkoutSegment(
            kind: .work,
            target: .ids("edge-left"),
            timing: .fixed,
            duration: 5
        )
        let workout = plan([repeated, repeated])

        let records = try WorkoutActivityRecorder().segments(for: workout, on: board)

        XCTAssertEqual(records.count, 2)
        XCTAssertEqual(records[0], records[1])
    }

    func testVersionOneJSONRoundTripsAndOmitsNilOptionalFields() throws {
        let metadata = WorkoutActivityMetadata(
            segments: [
                RecordedActivitySegment(
                    stepID: "step",
                    stepNumber: 1,
                    kind: .rest,
                    holdIDs: [],
                    holdType: nil,
                    sizeMillimeters: nil,
                    durationSeconds: nil
                )
            ]
        )

        let json: String = try WorkoutActivityRecorder().json(for: metadata)

        XCTAssertEqual(
            json,
            #"{"segments":[{"holdIDs":[],"kind":"rest","stepID":"step","stepNumber":1}],"version":1}"#
        )
        let decoded = try JSONDecoder().decode(
            WorkoutActivityMetadata.self,
            from: Data(json.utf8)
        )
        XCTAssertEqual(decoded, metadata)
        XCTAssertEqual(decoded.version, 1)
        XCTAssertFalse(json.contains("durationSeconds"))
        XCTAssertFalse(json.contains("holdType"))
        XCTAssertFalse(json.contains("sizeMillimeters"))
    }

    func testMeasuredStepIsExportedOnceAlongsideDescriptorSegments() throws {
        let workout = plan([
            WorkoutSegment(
                kind: .work,
                target: .ids("edge-left", "jug-center"),
                timing: .fixed,
                duration: 10
            )
        ])
        let measurement = WorkoutStepMeasurement(
            stepID: "step",
            plannedActiveDuration: 10,
            intervals: [LoadInterval(start: 1, end: 4.5)],
            peakLoadKGF: 37.25,
            sampleCount: 20,
            status: .measured
        )

        let metadata = try WorkoutActivityRecorder().metadata(
            for: workout,
            on: board,
            stepMeasurements: [measurement]
        )

        XCTAssertEqual(metadata.segments.count, 2)
        XCTAssertEqual(
            metadata.measurements,
            [
                RecordedActivityStepMeasurement(
                    stepID: "step",
                    peakLoadKGF: 37.25,
                    actualLoadedDurationSeconds: 3.5
                )
            ]
        )
    }

    func testUnmeasuredStepOmitsMeasurementCollection() throws {
        let workout = plan([
            WorkoutSegment(
                kind: .work,
                target: .ids("edge-left"),
                timing: .fixed,
                duration: 10
            )
        ])
        let measurement = WorkoutStepMeasurement(
            stepID: "step",
            plannedActiveDuration: 10,
            intervals: [],
            peakLoadKGF: nil,
            sampleCount: 0,
            status: .unmeasured
        )

        let metadata = try WorkoutActivityRecorder().metadata(
            for: workout,
            on: board,
            stepMeasurements: [measurement]
        )

        XCTAssertNil(metadata.measurements)
    }

    func testUnresolvedTargetThrowsItsSegmentKey() {
        let workout = plan([
            WorkoutSegment(
                kind: .work,
                target: .ids("missing"),
                timing: .fixed,
                duration: 1
            )
        ])

        XCTAssertThrowsError(
            try WorkoutActivityRecorder().segments(for: workout, on: board)
        ) { error in
            XCTAssertEqual(
                error as? WorkoutActivityRecordingError,
                .unresolvedTarget(stepID: "step", segmentIndex: 0)
            )
        }
    }

    func testPartiallyUnresolvedMultiTargetThrowsItsSegmentKey() {
        let workout = plan([
            WorkoutSegment(
                kind: .work,
                targets: [.ids("edge-left"), .ids("missing")],
                timing: .fixed,
                duration: 10
            )
        ])

        XCTAssertThrowsError(
            try WorkoutActivityRecorder().segments(for: workout, on: board)
        ) { error in
            XCTAssertEqual(
                error as? WorkoutActivityRecordingError,
                .unresolvedTarget(stepID: "step", segmentIndex: 0)
            )
        }
    }

    func testInvalidObservedDurationsThrowTheirSegmentKey() {
        let workout = plan([
            WorkoutSegment(
                kind: .work,
                target: .ids("edge-left"),
                timing: .stopwatch,
                duration: nil
            )
        ])
        let key = WorkoutActivitySegmentKey(stepID: "step", segmentIndex: 0)

        for invalidDuration in [-1.0, .infinity, .nan] {
            XCTAssertThrowsError(
                try WorkoutActivityRecorder().segments(
                    for: workout,
                    on: board,
                    stopwatchDurations: [key: invalidDuration]
                )
            ) { error in
                XCTAssertEqual(
                    error as? WorkoutActivityRecordingError,
                    .invalidObservedDuration(key)
                )
            }
        }
    }

    func testAppStoreResolutionPreservesDirectFeatureFallbackAndKindBehavior() {
        let defaults = makeDefaults()
        let store = AppStore(
            healthKitService: HealthWorkoutSavingSpy(),
            workoutSessionStore: makeSessionStore(defaults: defaults),
            defaults: defaults
        )
        let exactFeatureTarget = HoldTarget.feature(
            .mediumEdge,
            fallbacks: [.largeEdge]
        )

        XCTAssertEqual(
            store.holdIDs(
                for: step(targets: [.ids("missing", "edge-right")]),
                on: board
            ),
            ["edge-right"]
        )
        XCTAssertEqual(
            store.holdIDs(for: step(targets: [exactFeatureTarget]), on: board),
            ["edge-left", "edge-right"]
        )
        XCTAssertEqual(
            store.holdIDs(
                for: step(
                    targets: [
                        .feature(.smallEdge, fallbacks: [.largeEdge])
                    ]
                ),
                on: board
            ),
            ["edge-deep"]
        )
        XCTAssertEqual(
            store.holdIDs(for: step(targets: [.kind(.jug)]), on: board),
            ["jug-center"]
        )

        XCTAssertFalse(
            store.usesFallbackMapping(
                plan(targets: [exactFeatureTarget], segments: []),
                on: board
            )
        )
        XCTAssertTrue(
            store.usesFallbackMapping(
                plan(
                    targets: [
                        .feature(.smallEdge, fallbacks: [.largeEdge])
                    ],
                    segments: []
                ),
                on: board
            )
        )
    }

    func testSevenThreeRepeatersResolveExpectedLeftRightEdgePairs() throws {
        let defaults = makeDefaults()
        let store = AppStore(
            healthKitService: HealthWorkoutSavingSpy(),
            workoutSessionStore: makeSessionStore(defaults: defaults),
            defaults: defaults
        )
        let plan = LegacyPlanSeedCatalog.repeaters
        let board = BoardCatalog.defaultBoard
        let repeaterSteps = plan.steps.filter { $0.id.hasPrefix(LegacyPlanSeedCatalog.repeaterStepIDPrefix) }
        let workSteps = repeaterSteps.filter { $0.phase == .hang }
        let interRepRestSteps = workSteps.filter { $0.restDuration == 3 }
        let seriesRecoverySteps = repeaterSteps.filter {
            $0.phase == .rest &&
                $0.id.contains("-series-") &&
                $0.id.hasSuffix("-recovery")
        }
        let setRecoverySteps = repeaterSteps.filter {
            $0.id.hasSuffix("set-1-recovery")
        }

        XCTAssertEqual(workSteps.count, 84)
        XCTAssertEqual(interRepRestSteps.count, 72)
        XCTAssertTrue(interRepRestSteps.allSatisfy { $0.activeDuration == 7 })
        XCTAssertTrue(interRepRestSteps.allSatisfy { $0.restDuration == 3 })
        XCTAssertEqual(seriesRecoverySteps.count, 10)
        XCTAssertEqual(seriesRecoverySteps.map(\.duration), Array(repeating: 150, count: 10))
        XCTAssertEqual(setRecoverySteps.count, 1)
        XCTAssertEqual(setRecoverySteps.first?.duration, 360)

        struct ProgressionCue {
            let targetIDs: [String]
            let sizeMillimeters: Int
            let features: Set<HoldFeature>
            let gripType: GripType
            let fingerConfiguration: FingerConfiguration?
        }

        let expectedProgressionCues = [
            ProgressionCue(
                targetIDs: ["edge-29-left", "edge-29-right"],
                sizeMillimeters: 29,
                features: [.largeEdge],
                gripType: .openHand,
                fingerConfiguration: nil
            ),
            ProgressionCue(
                targetIDs: ["edge-19-left", "edge-19-right"],
                sizeMillimeters: 19,
                features: [.mediumEdge, .smallEdge],
                gripType: .openHand,
                fingerConfiguration: nil
            ),
            ProgressionCue(
                targetIDs: ["edge-19-left", "edge-19-right"],
                sizeMillimeters: 19,
                features: [.mediumEdge, .smallEdge],
                gripType: .halfCrimp,
                fingerConfiguration: nil
            ),
            ProgressionCue(
                targetIDs: ["edge-19-left", "edge-19-right"],
                sizeMillimeters: 19,
                features: [.mediumEdge, .smallEdge],
                gripType: .openHand,
                fingerConfiguration: FingerConfiguration(engagedFingers: [.index, .middle, .ring])
            ),
            ProgressionCue(
                targetIDs: ["edge-19-left", "edge-19-right"],
                sizeMillimeters: 19,
                features: [.mediumEdge, .smallEdge],
                gripType: .halfCrimp,
                fingerConfiguration: FingerConfiguration(engagedFingers: [.middle, .ring, .pinky])
            ),
            ProgressionCue(
                targetIDs: ["edge-19-left", "edge-19-right"],
                sizeMillimeters: 19,
                features: [.mediumEdge, .smallEdge],
                gripType: .openHand,
                fingerConfiguration: FingerConfiguration(engagedFingers: [.index, .middle])
            )
        ]

        for set in 1...2 {
            let setWorkSteps = workSteps.filter { $0.id.contains("set-\(set)-") }
            XCTAssertEqual(setWorkSteps.count, 42)

            for (seriesIndex, cue) in expectedProgressionCues.enumerated() {
                let seriesSteps = setWorkSteps.filter {
                    $0.id.contains("series-\(seriesIndex + 1)-")
                }
                XCTAssertEqual(seriesSteps.count, 7)
                XCTAssertTrue(seriesSteps.allSatisfy { $0.activeDuration == 7 })
                XCTAssertTrue(seriesSteps.allSatisfy {
                    store.holdIDs(for: $0, on: board).sorted() == cue.targetIDs.sorted()
                })
                XCTAssertTrue(seriesSteps.allSatisfy { $0.gripType == cue.gripType })
                XCTAssertTrue(seriesSteps.allSatisfy {
                    $0.fingerConfiguration == cue.fingerConfiguration
                })

                let holds = board.holds.filter { cue.targetIDs.contains($0.id) }
                XCTAssertEqual(holds.count, 2)
                XCTAssertTrue(holds.allSatisfy {
                    $0.kind == .edge &&
                        $0.sizeMillimeters == cue.sizeMillimeters &&
                        $0.fingerCapacity == 4 &&
                        $0.features == cue.features
                })
            }
        }

        let resolvedPairs = workSteps.map { store.holdIDs(for: $0, on: board).sorted() }
        XCTAssertEqual(Set(resolvedPairs), Set(expectedProgressionCues.map { $0.targetIDs.sorted() }))

        for holdIDs in Set(resolvedPairs) {
            XCTAssertEqual(holdIDs.count, 2)
            XCTAssertEqual(holdIDs.filter { $0.hasSuffix("-left") }.count, 1)
            XCTAssertEqual(holdIDs.filter { $0.hasSuffix("-right") }.count, 1)

            let holds = board.holds.filter { holdIDs.contains($0.id) }
            XCTAssertEqual(holds.count, 2)
            guard holds.count == 2 else { continue }

            let leftHold = try XCTUnwrap(holds.first { $0.id.hasSuffix("-left") })
            let rightHold = try XCTUnwrap(holds.first { $0.id.hasSuffix("-right") })
            XCTAssertLessThan(leftHold.frame.x, rightHold.frame.x)
            XCTAssertEqual(leftHold.kind, .edge)
            XCTAssertEqual(rightHold.kind, .edge)
            XCTAssertEqual(leftHold.sizeMillimeters, rightHold.sizeMillimeters)
            XCTAssertEqual(leftHold.fingerCapacity, rightHold.fingerCapacity)
            XCTAssertEqual(leftHold.features, rightHold.features)
            XCTAssertTrue(leftHold.name.hasPrefix("Left "))
            XCTAssertTrue(rightHold.name.hasPrefix("Right "))
        }

        let centeredFourFingerPocketIDs = Set(
            board.holds
                .filter {
                    $0.kind == .pocket &&
                    $0.fingerCapacity == 4 &&
                    abs(($0.frame.x + ($0.frame.width / 2)) - 0.5) < 0.0001
                }
                .map(\.id)
        )
        XCTAssertTrue(Set(resolvedPairs.flatMap { $0 }).isDisjoint(with: centeredFourFingerPocketIDs))
    }

    func testExactBoardCompletionRecordsObservedSegmentsAndLocalCompletion() {
        let service = HealthWorkoutSavingSpy()
        let workoutSaved = expectation(description: "HealthKit workout save")
        service.onSave = {
            workoutSaved.fulfill()
        }
        let defaults = makeHealthConnectedDefaults()
        let store = AppStore(
            healthKitService: service,
            workoutSessionStore: makeSessionStore(defaults: defaults),
            defaults: defaults
        )
        let localCompletionPublished = expectation(description: "Local completion published")
        let completionObservation = store.$workoutHistory
            .map(\.sessionCount)
            .filter { $0 == 1 }
            .first()
            .sink { _ in
                localCompletionPublished.fulfill()
            }
        let workout = plan([
            WorkoutSegment(
                kind: .work,
                target: .ids("edge-left"),
                timing: .stopwatch,
                duration: nil
            )
        ])
        let key = WorkoutActivitySegmentKey(stepID: "step", segmentIndex: 0)
        let startDate = Date(timeIntervalSinceReferenceDate: 1_000)
        let endDate = Date(timeIntervalSinceReferenceDate: 1_012)

        store.markSessionComplete(
            workout,
            board: board,
            stopwatchDurations: [key: 8.75],
            startDate: startDate,
            endDate: endDate
        )

        wait(for: [workoutSaved, localCompletionPublished], timeout: 5)
        withExtendedLifetime(completionObservation) {}
        XCTAssertEqual(store.sessionsCompleted, 1)
        XCTAssertTrue(store.sessionHistory.isEmpty)
        XCTAssertEqual(store.lastSessionTitle, "Plan")
        XCTAssertNotNil(defaults.data(forKey: LocalWorkoutHistoryStore.defaultKey))
        XCTAssertEqual(service.savedWorkouts.count, 1)
        XCTAssertEqual(service.savedWorkouts[0].title, "Plan")
        XCTAssertEqual(service.savedWorkouts[0].startDate, startDate)
        XCTAssertEqual(service.savedWorkouts[0].endDate, endDate)
        XCTAssertEqual(service.savedWorkouts[0].boardID, board.id)
        XCTAssertEqual(service.savedWorkouts[0].boardName, board.name)
        XCTAssertEqual(service.savedWorkouts[0].activitySegments.count, 1)
        XCTAssertEqual(
            service.savedWorkouts[0].activitySegments[0].durationSeconds,
            8.75
        )
    }

    func testCompletionExportsMeasuredLoadThroughHealthKitSegments() {
        let service = HealthWorkoutSavingSpy()
        let defaults = makeHealthConnectedDefaults()
        let store = AppStore(
            healthKitService: service,
            workoutSessionStore: makeSessionStore(defaults: defaults),
            defaults: defaults
        )
        let workout = plan([
            WorkoutSegment(
                kind: .work,
                target: .ids("edge-left"),
                timing: .fixed,
                duration: 10
            )
        ])
        let startDate = Date(timeIntervalSinceReferenceDate: 1_000)
        let endDate = Date(timeIntervalSinceReferenceDate: 1_010)
        let session = WorkoutSessionRecord(
            id: UUID(),
            planID: workout.id,
            planTitle: workout.title,
            recordedAt: endDate,
            startDate: startDate,
            endDate: endDate,
            motherboardIdentifier: nil,
            batteryValue: nil,
            steps: [
                WorkoutStepMeasurement(
                    stepID: "step",
                    plannedActiveDuration: 10,
                    intervals: [LoadInterval(start: 1, end: 4.5)],
                    peakLoadKGF: 37.25,
                    sampleCount: 20,
                    status: .measured
                )
            ]
        )

        store.markSessionComplete(
            workout,
            board: board,
            stopwatchDurations: [:],
            startDate: startDate,
            endDate: endDate,
            session: session
        )

        guard waitUntil({ service.savedWorkouts.count == 1 }) else {
            return
        }
        XCTAssertEqual(
            service.savedWorkouts[0].activityMeasurements,
            [
                RecordedActivityStepMeasurement(
                    stepID: "step",
                    peakLoadKGF: 37.25,
                    actualLoadedDurationSeconds: 3.5
                )
            ]
        )
    }

    func testPrimaryAppStoreInitializerStoresHistoryInSuppliedDefaults() {
        let defaults = makeDefaults()
        let store = AppStore(
            healthKitService: WorkoutHealthStoreSpy(),
            workoutSessionStore: makeSessionStore(defaults: defaults),
            defaults: defaults
        )
        let workout = plan([
            WorkoutSegment(
                kind: .work,
                target: .ids("edge-left"),
                timing: .fixed,
                duration: 8
            )
        ])

        store.markSessionComplete(
            workout,
            board: board,
            stopwatchDurations: [:],
            startDate: Date(timeIntervalSinceReferenceDate: 1_000),
            endDate: Date(timeIntervalSinceReferenceDate: 1_008)
        )

        waitUntil { store.sessionsCompleted == 1 }
        XCTAssertNotNil(defaults.data(forKey: LocalWorkoutHistoryStore.defaultKey))
    }

    func testLegacyCompletionUsesSelectedBoardAndNoStopwatchDurations() {
        let service = HealthWorkoutSavingSpy()
        let defaults = makeHealthConnectedDefaults()
        let store = AppStore(
            healthKitService: service,
            workoutSessionStore: makeSessionStore(defaults: defaults),
            defaults: defaults
        )
        store.selectBoard(board)
        let workout = plan([
            WorkoutSegment(
                kind: .work,
                target: .ids("edge-left"),
                timing: .stopwatch,
                duration: nil
            )
        ])

        store.markSessionComplete(
            workout,
            startDate: Date(timeIntervalSinceReferenceDate: 1_000),
            endDate: Date(timeIntervalSinceReferenceDate: 1_012)
        )

        guard waitUntil({ service.savedWorkouts.count == 1 }) else {
            return
        }
        XCTAssertEqual(service.savedWorkouts.count, 1)
        XCTAssertEqual(service.savedWorkouts[0].boardID, board.id)
        XCTAssertNil(service.savedWorkouts[0].activitySegments[0].durationSeconds)
    }

    func testRecorderFailureSurfacesErrorWithoutCallingHealthKit() {
        let service = HealthWorkoutSavingSpy()
        let defaults = makeDefaults()
        let store = AppStore(
            healthKitService: service,
            workoutSessionStore: makeSessionStore(defaults: defaults),
            defaults: defaults
        )
        let expectedError = "Session logged in Hang Ten, but Hang Ten could not match a workout activity to the selected board."
        let localCompletionPublished = expectation(description: "Local completion published")
        let completionObservation = store.$workoutHistory
            .map(\.sessionCount)
            .filter { $0 == 1 }
            .first()
            .sink { _ in
                localCompletionPublished.fulfill()
            }
        let recordingErrorPublished = expectation(description: "Recording error published")
        let errorObservation = store.$healthAuthorizationError
            .compactMap { $0 }
            .filter { $0 == expectedError }
            .first()
            .sink { _ in
                recordingErrorPublished.fulfill()
            }
        let workout = plan([
            WorkoutSegment(
                kind: .work,
                target: .ids("missing"),
                timing: .fixed,
                duration: 10
            )
        ])
        store.markSessionComplete(
            workout,
            board: board,
            stopwatchDurations: [:],
            startDate: Date(timeIntervalSinceReferenceDate: 1_000),
            endDate: Date(timeIntervalSinceReferenceDate: 1_012)
        )

        wait(for: [localCompletionPublished, recordingErrorPublished], timeout: 5)
        withExtendedLifetime(completionObservation) {}
        withExtendedLifetime(errorObservation) {}
        XCTAssertEqual(
            store.healthAuthorizationError,
            expectedError
        )
        XCTAssertEqual(store.sessionsCompleted, 1)
        XCTAssertTrue(store.sessionHistory.isEmpty)
        XCTAssertEqual(store.lastSessionTitle, "Plan")
        XCTAssertTrue(service.savedWorkouts.isEmpty)
    }

    func testHealthKitMetadataContainsBoardAndVersionedActivityPayload() throws {
        let activitySegments = [
            RecordedActivitySegment(
                stepID: "step",
                stepNumber: 1,
                kind: .work,
                holdIDs: ["edge-left"],
                holdType: "edge",
                sizeMillimeters: 21,
                durationSeconds: 8.75
            )
        ]
        let activityMeasurements = [
            RecordedActivityStepMeasurement(
                stepID: "step",
                peakLoadKGF: 37.25,
                actualLoadedDurationSeconds: 3.5
            )
        ]

        let metadata = try HealthKitService.workoutMetadata(
            title: "Plan",
            boardID: board.id,
            boardName: board.name,
            activitySegments: activitySegments,
            activityMeasurements: activityMeasurements
        )

        XCTAssertEqual(metadata[HKMetadataKeyWorkoutBrandName] as? String, "Hang Ten")
        XCTAssertEqual(metadata["HangTen.PlanName"] as? String, "Plan")
        XCTAssertEqual(metadata["HangTen.BoardID"] as? String, board.id)
        XCTAssertEqual(metadata["HangTen.BoardName"] as? String, board.name)
        let json = try XCTUnwrap(metadata["HangTen.ActivitySegments"] as? String)
        let decoded = try JSONDecoder().decode(
            WorkoutActivityMetadata.self,
            from: Data(json.utf8)
        )
        XCTAssertEqual(
            json,
            #"{"measurements":[{"actualLoadedDurationSeconds":3.5,"peakLoadKGF":37.25,"stepID":"step"}],"segments":[{"durationSeconds":8.75,"holdIDs":["edge-left"],"holdType":"edge","kind":"work","sizeMillimeters":21,"stepID":"step","stepNumber":1}],"version":1}"#
        )
        XCTAssertEqual(
            decoded,
            WorkoutActivityMetadata(
                version: 1,
                segments: activitySegments,
                measurements: activityMeasurements
            )
        )
    }

    func testLiteralVersionOnePayloadWithoutMeasurementsDecodes() throws {
        let json = #"{"segments":[{"holdIDs":[],"kind":"rest","stepID":"step","stepNumber":1}],"version":1}"#

        let decoded = try JSONDecoder().decode(
            WorkoutActivityMetadata.self,
            from: Data(json.utf8)
        )

        XCTAssertEqual(decoded.version, 1)
        XCTAssertNil(decoded.measurements)
        XCTAssertEqual(decoded.segments.count, 1)
    }

    @discardableResult
    private func waitUntil(
        _ condition: @escaping () -> Bool,
        file: StaticString = #filePath,
        line: UInt = #line
    ) -> Bool {
        let deadline = Date().addingTimeInterval(1)
        while !condition(), Date() < deadline {
            RunLoop.main.run(until: Date().addingTimeInterval(0.01))
        }
        let conditionMet = condition()
        XCTAssertTrue(conditionMet, file: file, line: line)
        return conditionMet
    }

    func testHealthKitMetadataEncodingFailureUsesLocalizedWriteError() {
        let invalidSegment = RecordedActivitySegment(
            stepID: "step",
            stepNumber: 1,
            kind: .work,
            holdIDs: ["edge-left"],
            holdType: "edge",
            sizeMillimeters: 21,
            durationSeconds: .nan
        )

        XCTAssertThrowsError(
            try HealthKitService.workoutMetadata(
                title: "Plan",
                boardID: board.id,
                boardName: board.name,
                activitySegments: [invalidSegment]
            )
        ) { error in
            XCTAssertEqual(error as? HealthWorkoutWriteError, .encodeActivitySegments)
            XCTAssertEqual(
                error.localizedDescription,
                "Hang Ten could not prepare the workout activity details for Apple Health."
            )
        }
    }

    private func step(targets: [HoldTarget]) -> WorkoutStep {
        WorkoutStep(
            id: "step",
            number: 1,
            title: "Step",
            instruction: "Instruction",
            accessory: "",
            duration: 60,
            phase: .hang,
            targets: targets
        )
    }

    private func plan(
        targets: [HoldTarget],
        segments: [WorkoutSegment]
    ) -> TrainingPlan {
        TrainingPlan(
            id: "resolution-plan",
            title: "Resolution Plan",
            subtitle: "",
            level: "",
            sourceLabel: "",
            sourceURL: URL(string: "https://example.com/resolution-plan")!,
            provenance: .adapted,
            boardID: board.id,
            steps: [
                WorkoutStep(
                    id: "step",
                    number: 1,
                    title: "Step",
                    instruction: "Instruction",
                    accessory: "",
                    duration: 60,
                    phase: .hang,
                    targets: targets,
                    segments: segments
                )
            ]
        )
    }
}

private final class HealthWorkoutSavingSpy: HealthWorkoutSaving {
    struct SavedWorkout {
        let title: String
        let startDate: Date
        let endDate: Date
        let boardID: String
        let boardName: String
        let activitySegments: [RecordedActivitySegment]
        let activityMeasurements: [RecordedActivityStepMeasurement]?
    }

    var authorizationState: HealthAuthorizationState = .authorized
    private(set) var savedWorkouts: [SavedWorkout] = []
    var onSave: (() -> Void)?

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
        activityMeasurements: [RecordedActivityStepMeasurement]?,
        completion: @escaping (Error?) -> Void
    ) {
        savedWorkouts.append(
            SavedWorkout(
                title: title,
                startDate: startDate,
                endDate: endDate,
                boardID: boardID,
                boardName: boardName,
                activitySegments: activitySegments,
                activityMeasurements: activityMeasurements
            )
        )
        onSave?()
        completion(nil)
    }
}

private final class WorkoutHealthStoreSpy: WorkoutHealthStore {
    var isHealthDataAvailable = true
    var authorizationState: HealthAuthorizationState = .authorized

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
        completion(.success(UUID()))
    }
}

private final class BlockingWorkoutActivityFileManager: FileManager {
    private let writeStarted: XCTestExpectation
    private let writeFinished: XCTestExpectation
    let allowWrite = DispatchSemaphore(value: 0)

    init(writeStarted: XCTestExpectation, writeFinished: XCTestExpectation) {
        self.writeStarted = writeStarted
        self.writeFinished = writeFinished
        super.init()
    }

    override func createDirectory(
        at url: URL,
        withIntermediateDirectories createIntermediates: Bool,
        attributes: [FileAttributeKey: Any]? = nil
    ) throws {
        writeStarted.fulfill()
        allowWrite.wait()
        defer { writeFinished.fulfill() }
        try super.createDirectory(
            at: url,
            withIntermediateDirectories: createIntermediates,
            attributes: attributes
        )
    }
}
