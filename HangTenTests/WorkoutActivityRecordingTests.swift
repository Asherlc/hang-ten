import XCTest
import HealthKit
import Combine
@testable import HangTen

@MainActor
final class WorkoutActivityRecordingTests: XCTestCase {
    private enum CodingPathComponent: Equatable {
        case key(String)
        case index(Int)
    }

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

    private let board: BoardRevision = {
        let holds = [
            PhysicalContact(
                id: "edge-left",
                name: "Left medium edge",
                kind: .edge,
                depth: .range(.init(minimum: 21, maximum: 21))
            ),
            PhysicalContact(
                id: "edge-right",
                name: "Right medium edge",
                kind: .edge,
                depth: .range(.init(minimum: 21, maximum: 21))
            ),
            PhysicalContact(
                id: "edge-deep",
                name: "Deep edge",
                kind: .edge,
                depth: .range(.init(minimum: 35, maximum: 35))
            ),
            PhysicalContact(
                id: "jug-center",
                name: "Center jug",
                kind: .jug
            )
        ]
        let frames: [String: CGRect] = [
            "edge-left": CGRect(x: 0, y: 0, width: 0.2, height: 0.2),
            "edge-right": CGRect(x: 0.8, y: 0, width: 0.2, height: 0.2),
            "edge-deep": CGRect(x: 0.3, y: 0.3, width: 0.2, height: 0.2),
            "jug-center": CGRect(x: 0.4, y: 0.7, width: 0.2, height: 0.2)
        ]
        let geometry = Dictionary(uniqueKeysWithValues: frames.map { id, frame in
            (id, [BoardContactPiece(
                id: "\(id)-piece",
                contactID: id,
                frame: frame,
                shape: .roundedRect(cornerRadiusFraction: 0),
                treatment: .surface
            )])
        })
        return BoardRevision(
            id: "fixture.board",
            revisionID: "test-fixture",
            manufacturer: "Fixture",
            name: "Board",
            subtitle: "",
            dimensions: "",
            aspectRatio: 2,
            contacts: holds,
            productURL: URL(string: "https://example.com/board")!,
            photoAssetName: nil,
            presentations: [
                BoardPresentation(
                    id: "primary",
                    name: "Primary",
                    aspectRatio: 2,
                    isDefault: true,
                    media: .raster(BoardRasterMedia(assetPath: "", contactGeometry: geometry))
                )
            ]
        )
    }()

    func testResolverSelectsCenterNearestSingleRequirement() throws {
        let bilateralStep = WorkoutStep(
            id: "bilateral",
            number: 1,
            title: "Bilateral edge hang",
            instruction: "Hang with both hands.",
            accessory: "",
            duration: 10,
            phase: .hang)

        XCTAssertEqual(
            try ContactResolver.resolve(
                .edge(selection: .single),
                step: bilateralStep,
                board: board
            ).map(\.id),
            ["edge-deep"]
        )
    }

    private func modelPresentation(
        id: String = "model",
        isDefault: Bool = true,
        bounds: [String: HoldFrame]
    ) -> BoardPresentation {
        let descriptorHolds = Dictionary(uniqueKeysWithValues: bounds.map { id, frame in
            (
                id,
                BoardModelContactDescriptor(
                    nodeIDs: ["Board/Hold/\\(id)"],
                    facePlaneAABB: BoardModelFacePlaneAABB(
                        minimum: [frame.x, frame.y, 0],
                        maximum: [frame.x + frame.width, frame.y + frame.height, 0.1]
                    ),
                    center: [frame.x + frame.width / 2, frame.y + frame.height / 2, 0]
                )
            )
        })
        let descriptor = BoardModelDescriptor(
            schemaVersion: 1,
            coordinateFrame: "board-face-normalized-v1",
            modelSHA256: "fixture",
            modelBounds: BoardModelBounds(minimum: [0, 0, 0], maximum: [1, 1, 0.1]),
            nodes: [],
            contacts: descriptorHolds
        )
        return BoardPresentation(
            id: id,
            name: id,
            aspectRatio: 1,
            isDefault: isDefault,
            media: .model(
                BoardModelMedia(
                    assetPath: "assets/\\(id).usdz",
                    descriptorPath: "assets/\\(id).model.json",
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
    }

    private func rasterPresentation(
        id: String = "raster",
        isDefault: Bool = true,
        bounds: [String: HoldFrame]
    ) -> BoardPresentation {
        let geometry = Dictionary(uniqueKeysWithValues: bounds.map { id, frame in
            (
                id,
                [BoardContactPiece(
                    id: "\\(id)-piece",
                    contactID: id,
                    frame: frame.rect,
                    shape: .roundedRect(cornerRadiusFraction: 0),
                    treatment: .surface
                )]
            )
        })
        return BoardPresentation(
            id: id,
            name: id,
            aspectRatio: 1,
            isDefault: isDefault,
            media: .raster(BoardRasterMedia(assetPath: "assets/\\(id).png", contactGeometry: geometry))
        )
    }

    private func board(
        holds: [PhysicalContact],
        presentations: [BoardPresentation]
    ) -> BoardRevision {
        BoardRevision(
            id: "fixture.media-aware-board",
            revisionID: "test-fixture",
            manufacturer: "Fixture",
            name: "Media-aware Board",
            subtitle: "",
            dimensions: nil,
            aspectRatio: 1,
            contacts: holds,
            productURL: URL(string: "https://example.com/media-aware-board")!,
            photoAssetName: nil,
            presentations: presentations
        )
    }

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
        boardID: String? = "fixture.board",
        provenance: RoutineProvenance = .adapted,
        sourceURL: URL? = URL(string: "https://example.com/plan"),
        _ segments: [WorkoutSegment]
    ) -> TrainingPlan {
        return TrainingPlan(
            id: "plan",
            title: "Plan",
            subtitle: "",
            level: "",
            sourceLabel: "",
            sourceURL: sourceURL,
            provenance: provenance,
            boardID: boardID,
            steps: [
                WorkoutStep(
                    id: "step",
                    number: 1,
                    title: "Step",
                    instruction: instruction,
                    accessory: "",
                    duration: 60,
                    phase: .hang,
                    segments: segments
                )
            ]
        )
    }

    func testModelDescriptorFacePlaneAABBResolvesExactlyForWorkoutMatching() {
        let hold = PhysicalContact(id: "model-left", name: "Model left", kind: .edge)
        let expected = HoldFrame(x: 0.1, y: 0.2, width: 0.3, height: 0.4)
        let presentation = modelPresentation(bounds: [hold.id: expected])

        XCTAssertEqual(hold.resolvedFrame(in: presentation), expected)
        XCTAssertEqual(board(holds: [hold], presentations: [presentation]).contacts(in: presentation), [hold])
    }

    func testRecordedWorkStoresRevisionRequirementAndResolvedContacts() throws {
        let left = PhysicalContact(
            id: "left-edge",
            name: "Left edge",
            kind: .edge,
            depth: .category(.medium)
        )
        let right = PhysicalContact(
            id: "right-edge",
            name: "Right edge",
            kind: .edge,
            depth: .category(.medium)
        )
        let modelBoard = BoardRevision(
            id: "fixture.snapshot-board",
            revisionID: "2026-09-contact-first",
            manufacturer: "Fixture",
            name: "Snapshot Board",
            subtitle: "",
            dimensions: nil,
            aspectRatio: 1,
            contacts: [left, right],
            productURL: URL(string: "https://example.com/snapshot-board")!,
            photoAssetName: nil,
            presentations: [
                modelPresentation(bounds: [
                    left.id: HoldFrame(x: 0.1, y: 0.2, width: 0.2, height: 0.1),
                    right.id: HoldFrame(x: 0.75, y: 0.2, width: 0.2, height: 0.1)
                ])
            ]
        )
        let requirement = ContactRequirement.edge(depth: .category(.medium))
        let workout = plan([
            WorkoutSegment(
                kind: .work,
                target: .fromLegacyTargets([requirement]),
                timing: .fixed,
                duration: 10
            )
        ])

        let record = try XCTUnwrap(
            WorkoutActivityRecorder().segments(for: workout, on: modelBoard)
                .first(where: { $0.kind == .work })
        )
        let resolution = try XCTUnwrap(record.target?.resolvedContactSnapshot)

        XCTAssertEqual(resolution.boardID, modelBoard.id)
        XCTAssertEqual(resolution.revisionID, "2026-09-contact-first")
        XCTAssertEqual(resolution.contactIDs, ["left-edge"])
        XCTAssertEqual(resolution.modelSHA256, "fixture")
        XCTAssertEqual(resolution.requirement, requirement)
        let data = try JSONEncoder().encode(record)
        let document = try XCTUnwrap(JSONSerialization.jsonObject(with: data) as? [String: Any])
        XCTAssertNil(document["holdIDs"])
        XCTAssertNil(document["holdType"])
        XCTAssertNil(document["sizeMillimeters"])
    }

    func testWorkoutMatchingUsesOnlyContactsInTheDefaultPresentation() throws {
        let mapped = PhysicalContact(id: "mapped", name: "Mapped", kind: .edge)
        let missing = PhysicalContact(id: "missing", name: "Missing", kind: .edge)
        let presentation = modelPresentation(bounds: [
            mapped.id: HoldFrame(x: 0.1, y: 0.2, width: 0.3, height: 0.1)
        ])
        let board = board(holds: [mapped, missing], presentations: [presentation])

        XCTAssertNil(missing.resolvedFrame(in: presentation))
        XCTAssertEqual(board.contacts(in: presentation), [mapped])
        let requirement = ContactRequirement.kind(.edge, selection: .single)
        let workoutStep = step(targets: [requirement])
        XCTAssertEqual(
            try ContactResolver.resolve(requirement, step: workoutStep, board: board).map(\.id),
            [mapped.id]
        )
    }

    func testResolverReportsNoMatchesBeforeApplyingBilateralSelection() {
        let requirement = ContactRequirement.kind(.pocket, selection: .bilateralPair)

        XCTAssertThrowsError(
            try ContactResolver.resolve(requirement, step: step(targets: [requirement]), board: board)
        ) { error in
            XCTAssertEqual(error as? ContactResolutionError, .noMatches)
        }
    }

    func testResolverRejectsBilateralPairWhenAnExtremeIsOnThePresentationMidpoint() {
        let center = PhysicalContact(id: "center", name: "Center edge", kind: .edge)
        let right = PhysicalContact(id: "right", name: "Right edge", kind: .edge)
        let presentation = rasterPresentation(bounds: [
            center.id: HoldFrame(x: 0.4, y: 0.2, width: 0.2, height: 0.2),
            right.id: HoldFrame(x: 0.7, y: 0.2, width: 0.2, height: 0.2)
        ])
        let board = board(holds: [center, right], presentations: [presentation])
        let requirement = ContactRequirement.kind(.edge, selection: .bilateralPair)

        XCTAssertThrowsError(
            try ContactResolver.resolve(requirement, step: step(targets: [requirement]), board: board)
        ) { error in
            XCTAssertEqual(error as? ContactResolutionError, .invalidBilateralPair(candidateCount: 2))
        }
    }

    func testWorkoutMatchingUsesDefaultPresentationForSingleAndRejectsInvalidPair() throws {
        let left = PhysicalContact(
            id: "pocket-left",
            name: "Left pocket",
            kind: .pocket,
            fingerCapacity: 3,
            handCapacity: 1
        )
        let right = PhysicalContact(
            id: "pocket-right",
            name: "Right pocket",
            kind: .pocket,
            fingerCapacity: 3,
            handCapacity: 1
        )
        let defaultModel = modelPresentation(bounds: [
            left.id: HoldFrame(x: 0.1, y: 0.2, width: 0.2, height: 0.2)
        ])
        let alternateRaster = rasterPresentation(
            id: "alternate",
            isDefault: false,
            bounds: [right.id: HoldFrame(x: 0.7, y: 0.2, width: 0.2, height: 0.2)]
        )
        let board = board(holds: [left, right], presentations: [defaultModel, alternateRaster])

        let singleRequirement = ContactRequirement.kind(
            .pocket,
            fingerCapacity: 3,
            selection: .single
        )
        let singleStep = WorkoutStep(
            id: "single",
            number: 1,
            title: "Single",
            instruction: "",
            accessory: "",
            duration: 10,
            phase: .hang,
            handUse: .single,
            side: .right
        )
        XCTAssertEqual(
            try ContactResolver.resolve(singleRequirement, step: singleStep, board: board).map(\.id),
            ["pocket-left"]
        )

        let pairRequirement = ContactRequirement.kind(.pocket, selection: .bilateralPair)
        let pairStep = WorkoutStep(
            id: "pair",
            number: 1,
            title: "Pair",
            instruction: "",
            accessory: "",
            duration: 10,
            phase: .hang)
        XCTAssertThrowsError(
            try ContactResolver.resolve(pairRequirement, step: pairStep, board: board)
        )
    }

    func testRequirementAndResolvedContactsAreRecordedWithFixedDuration() throws {
        let workout = plan(
            instruction: "Hang from the medium edge",
            [
                WorkoutSegment(
                    kind: .work,
                    target: .fromLegacyTargets([.edge(depth: .category(.medium))]),
                    timing: .fixed,
                    duration: 12
                )
            ]
        )

        let records = try WorkoutActivityRecorder().segments(for: workout, on: board)

        XCTAssertEqual(records.count, 1)
        XCTAssertEqual(records[0].target?.resolvedContactSnapshot?.requirement, .edge(depth: .category(.medium)))
        XCTAssertEqual(records[0].target?.resolvedContactSnapshot?.contactIDs, ["edge-left"])
        XCTAssertNil(records[0].target?.resolvedContactSnapshot?.modelSHA256)
        XCTAssertEqual(records[0].durationSeconds, 12)
    }

    func testMultiRequirementWorkRecordsOneAuditableSnapshotPerRequirement() throws {
        let segment = WorkoutSegment(
            kind: .work,
            target: .fromLegacyTargets([.edge(depth: .category(.medium)), .kind(.jug)]),
            timing: .fixed,
            duration: 10
        )

        let records = try WorkoutActivityRecorder().segments(
            for: plan([segment]),
            on: board
        )

        XCTAssertEqual(records.count, 2)
        XCTAssertEqual(
            records.map { $0.target?.resolvedContactSnapshot?.requirement },
            [.edge(depth: .category(.medium)), .kind(.jug)]
        )
        XCTAssertEqual(records.map { $0.target?.resolvedContactSnapshot?.contactIDs }, [
            ["edge-left"],
            ["jug-center"]
        ])
        XCTAssertEqual(records.map(\.durationSeconds), [10, 10])
    }

    func testFixedWorkFollowedByRestPreservesOrderAndDurations() throws {
        let workout = plan([
            WorkoutSegment(
                kind: .work,
                target: .fromLegacyTargets([.edge(depth: .category(.medium))]),
                timing: .fixed,
                duration: 20
            ),
            WorkoutSegment(kind: .rest, target: nil, timing: .fixed, duration: 10)
        ])

        let records = try WorkoutActivityRecorder().segments(for: workout, on: board)

        XCTAssertEqual(records.map(\.kind), [.work, .rest])
        XCTAssertEqual(records.map(\.durationSeconds), [20, 10])
        XCTAssertNil(records[1].target)
    }

    func testRPTCRepeatersRecordSelfSelectedWorkWithoutBoardHolds() throws {
        let workout = try XCTUnwrap(
            PlanCatalog.plan(id: LegacyPlanSeedCatalog.rptcRepeaters.id)
        )

        let records = try WorkoutActivityRecorder().segments(
            for: workout,
            on: board
        )

        let workRecords = records.filter { $0.kind == .work }
        XCTAssertEqual(workRecords.count, 7)
        XCTAssertTrue(workRecords.allSatisfy { $0.target == .selfSelected })
        XCTAssertEqual(workRecords.map(\.durationSeconds), Array(repeating: 7, count: 7))
    }

    func testGenericSourceLinkedTargetlessWorkRecordsSelfSelected() throws {
        let workout = plan(boardID: nil, [
            WorkoutSegment(
                kind: .work,
                target: nil,
                timing: .fixed,
                duration: 7
            )
        ])

        let records = try WorkoutActivityRecorder().segments(for: workout, on: board)

        XCTAssertEqual(records.count, 1)
        XCTAssertEqual(records[0].kind, .work)
        XCTAssertEqual(records[0].durationSeconds, 7)
        let json = try WorkoutActivityRecorder().json(
            for: WorkoutActivityMetadata(segments: records)
        )
        XCTAssertEqual(
            json,
            #"{"segments":[{"durationSeconds":7,"handUse":"double","kind":"work","side":"both","stepID":"step","stepNumber":1,"target":{"kind":"selfSelected"}}],"version":3}"#
        )
        let decoded = try JSONDecoder().decode(
            WorkoutActivityMetadata.self,
            from: Data(json.utf8)
        )
        XCTAssertEqual(
            try WorkoutActivityRecorder().json(for: decoded),
            json
        )
    }

    func testBoardBoundSourceLinkedTargetlessWorkFailsClosedWithoutRecordingSelfSelected() {
        let workout = plan(boardID: board.id, [
            WorkoutSegment(
                kind: .work,
                target: nil,
                timing: .fixed,
                duration: 7
            )
        ])

        do {
            let records = try WorkoutActivityRecorder().segments(for: workout, on: board)
            XCTAssertFalse(
                records.contains { $0.target == .selfSelected },
                "Board-bound source work must never record a self-selected target."
            )
            XCTFail("Expected board-bound targetless work to fail closed.")
        } catch {
            XCTAssertEqual(
                error as? WorkoutActivityRecordingError,
                .unresolvedTarget(stepID: "step", segmentIndex: 0)
            )
        }
    }

    func testCustomTargetlessWorkFailsClosed() {
        let workout = plan(
            boardID: nil,
            provenance: .custom,
            sourceURL: nil,
            [
                WorkoutSegment(
                    kind: .work,
                    target: nil,
                    timing: .fixed,
                    duration: 7
                )
            ]
        )

        XCTAssertThrowsError(
            try WorkoutActivityRecorder().segments(for: workout, on: board)
        ) { error in
            XCTAssertEqual(
                error as? WorkoutActivityRecordingError,
                .unresolvedTarget(stepID: "step", segmentIndex: 0)
            )
        }
    }

    func testGenericMetoliusWorkRetainsSemanticRequirementsAndRecordsResolvedOrSelfSelected() throws {
        let compactII = try XCTUnwrap(
            BoardCatalog.all.first { $0.id == "metolius.wood-grips-compact-ii" }
        )
        let plans = [
            LegacyPlanSeedCatalog.metoliusEntry,
            LegacyPlanSeedCatalog.metoliusIntermediate,
            LegacyPlanSeedCatalog.metoliusAdvanced
        ]

        for plan in plans {
            let workSegments = plan.steps.flatMap(\.segments).filter { $0.kind == .work }
            XCTAssertFalse(workSegments.isEmpty, "Missing source work for \(plan.id).")
            XCTAssertTrue(
                workSegments.allSatisfy { !$0.contactRequirements.isEmpty },
                "Generic Metolius work must retain authored semantic requirements for \(plan.id)."
            )

            let recordedWork = try WorkoutActivityRecorder()
                .segments(for: plan, on: compactII)
                .filter { $0.kind == .work }
            let workStepIDs = Set(
                plan.steps.filter { step in
                    step.segments.contains { $0.kind == .work }
                }.map(\.id)
            )
            XCTAssertEqual(Set(recordedWork.map(\.stepID)), workStepIDs)
            XCTAssertTrue(
                recordedWork.allSatisfy {
                    if case .resolvedContacts = $0.target { return true }
                    return $0.target == .selfSelected
                },
                "Board-agnostic Metolius work must resolve or soft-fall to self-selected for \(plan.id)."
            )
        }
    }

    func testBoardAgnosticSourceLinkedUnmatchedRequirementsRecordSelfSelected() throws {
        let workout = plan(boardID: nil, [
            WorkoutSegment(
                kind: .work,
                target: .fromLegacyTargets([.kind(.pinch)]),
                timing: .fixed,
                duration: 7
            )
        ])

        let records = try WorkoutActivityRecorder().segments(for: workout, on: board)
        XCTAssertEqual(records.count, 1)
        XCTAssertEqual(records[0].target, .selfSelected)
    }

    func testBoardBoundUnmatchedRequirementsStillFailClosed() {
        let workout = plan(boardID: board.id, [
            WorkoutSegment(
                kind: .work,
                target: .fromLegacyTargets([.kind(.pinch)]),
                timing: .fixed,
                duration: 7
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

    func testStopwatchWorkUsesSuppliedObservedDuration() throws {
        let workout = plan([
            WorkoutSegment(
                kind: .work,
                target: .fromLegacyTargets([.edge(depth: .category(.medium))]),
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
                target: .fromLegacyTargets([ContactRequirement()]),
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
                target: .fromLegacyTargets([.edge(depth: .category(.medium))]),
                timing: .undefined,
                duration: 30
            )
        ])

        let records = try WorkoutActivityRecorder().segments(for: workout, on: board)

        XCTAssertNil(records[0].durationSeconds)
    }

    func testResolvedContactsStayInCanonicalBoardOrder() throws {
        let workout = plan([
            WorkoutSegment(
                kind: .work,
                target: .fromLegacyTargets([.edge(depth: .category(.medium))]),
                timing: .fixed,
                duration: 10
            )
        ])

        let records = try WorkoutActivityRecorder().segments(for: workout, on: board)

        XCTAssertEqual(records.count, 1)
        XCTAssertEqual(
            records[0].target?.resolvedContactSnapshot?.contactIDs,
            ["edge-left"]
        )
    }

    func testOneRequirementProducesOneSnapshotAcrossContactDescriptors() throws {
        let workout = plan([
            WorkoutSegment(
                kind: .work,
                target: .fromLegacyTargets([ContactRequirement()]),
                timing: .fixed,
                duration: 10
            )
        ])

        let records = try WorkoutActivityRecorder().segments(for: workout, on: board)

        XCTAssertEqual(records.count, 1)
        XCTAssertEqual(
            records[0].target?.resolvedContactSnapshot?.contactIDs,
            ["jug-center"]
        )
    }

    func testRepeatedSourceSegmentsRemainDistinct() throws {
        let repeated = WorkoutSegment(
            kind: .work,
            target: .fromLegacyTargets([.edge(depth: .category(.medium))]),
            timing: .fixed,
            duration: 5
        )
        let workout = plan([repeated, repeated])

        let records = try WorkoutActivityRecorder().segments(for: workout, on: board)

        XCTAssertEqual(records.count, 2)
        XCTAssertEqual(records[0], records[1])
    }

    func testVersionTwoJSONRoundTripsAndOmitsNilOptionalFields() throws {
        let metadata = WorkoutActivityMetadata(
            segments: [
                RecordedActivitySegment(
                    stepID: "step",
                    stepNumber: 1,
                    kind: .rest,
                    target: nil,
                    durationSeconds: nil
                )
            ]
        )

        let json: String = try WorkoutActivityRecorder().json(for: metadata)

        XCTAssertEqual(
            json,
            #"{"segments":[{"kind":"rest","stepID":"step","stepNumber":1}],"version":3}"#
        )
        let decoded = try JSONDecoder().decode(
            WorkoutActivityMetadata.self,
            from: Data(json.utf8)
        )
        XCTAssertEqual(decoded, metadata)
        XCTAssertEqual(decoded.version, 3)
        XCTAssertFalse(json.contains("durationSeconds"))
        XCTAssertFalse(json.contains("target"))
    }

    func testWorkSegmentWithoutExplicitTargetCannotBeEncoded() {
        let metadata = WorkoutActivityMetadata(
            segments: [
                RecordedActivitySegment(
                    stepID: "step",
                    stepNumber: 1,
                    kind: .work,
                    target: nil,
                    durationSeconds: 7
                )
            ]
        )

        XCTAssertThrowsError(try WorkoutActivityRecorder().json(for: metadata)) { error in
            guard case let EncodingError.invalidValue(_, context) = error else {
                return XCTFail("Expected explicit-target encoding rejection, got \(error)")
            }
            XCTAssertTrue(context.debugDescription.contains("explicit target"))
        }
    }

    func testMeasuredStepIsExportedOnceAlongsideDescriptorSegments() throws {
        let workout = plan([
            WorkoutSegment(
                kind: .work,
                target: .fromLegacyTargets([.kind(.edge)]),
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

        XCTAssertEqual(metadata.segments.count, 1)
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
                target: .fromLegacyTargets([.kind(.edge)]),
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
                target: .fromLegacyTargets([ContactRequirement(
                    kind: .edge,
                    shape: .round
                )]),
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
                target: .fromLegacyTargets([
                    .kind(.jug),
                    ContactRequirement(
                        kind: .edge,
                        shape: .round
                    )
                ]),
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
                target: .fromLegacyTargets([.kind(.edge)]),
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

    func testAppStoreResolutionInfersGeometricThreeFingerPocketPair() {
        let defaults = makeDefaults()
        let store = AppStore(
            healthKitService: HealthWorkoutSavingSpy(),
            workoutSessionStore: makeSessionStore(defaults: defaults),
            defaults: defaults
        )

        XCTAssertEqual(
            store.contactIDs(
                for: step(targets: [ContactRequirement(
                    kind: .pocket,
                    depth: .range(.init(minimum: 29, maximum: 29)),
                    fingerCapacity: 3,
                    selection: .bilateralPair
                )]),
                on: BoardCatalog.defaultBoard
            ),
            ["pocket-29-three-left", "pocket-29-three-right"]
        )
    }

    func testActivityRecordingSelectsNearestSemanticContactForSingleHandStep() throws {
        let board = portableBoard(handCapacity: nil, secondSide: .left)
        let workout = portablePlan(handUse: .single, side: .left)

        XCTAssertEqual(
            try WorkoutActivityRecorder().segments(for: workout, on: board)
                .first?.target?.resolvedContactSnapshot?.contactIDs,
            ["left-b"]
        )
    }

    func testActivityRecordingSingleHandStepDoesNotUseSideMetadataForSelection() throws {
        let board = BoardRevision(
            id: "paired-portable-board",
            revisionID: "test-fixture",
            manufacturer: "Fixture",
            name: "Paired portable board",
            subtitle: "",
            dimensions: "",
            aspectRatio: 1,
            equipmentObjects: [.init(id: "left"), .init(id: "right")],
            contacts: [
                PhysicalContact(id: "left-a", equipmentObjectID: "left", name: "Left", kind: .pocket, handCapacity: 1, side: .left),
                PhysicalContact(id: "right-a", equipmentObjectID: "right", name: "Right", kind: .pocket, handCapacity: 1, side: .right)
            ],
            productURL: URL(string: "https://example.com/paired-portable")!,
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
                            "left-a": [testPiece(id: "left-a", x: 0)],
                            "right-a": [testPiece(id: "right-a", x: 0.9)]
                        ]
                    ))
                )
            ]
        )
        let workout = portablePlan(handUse: .single, side: .right, boardID: board.id)

        let records = try WorkoutActivityRecorder().segments(for: workout, on: board)

        XCTAssertEqual(
            records.map { $0.target?.resolvedContactSnapshot?.contactIDs },
            [["left-a"]]
        )
    }

    func testActivityRecordingRejectsDoubleHandPairOnOneSideOfBoard() {
        let board = portableBoard(handCapacity: 2)
        let workout = portablePlan(handUse: .double, side: .both)

        XCTAssertThrowsError(try WorkoutActivityRecorder().segments(for: workout, on: board))
    }

    func testEitherHandActivityRequiresAChoiceAndRecordsTheSelectedRightHand() throws {
        let board = portableBoard(handCapacity: 1)
        let workout = portablePlan(handUse: .either, side: .both)
        let recorder = WorkoutActivityRecorder()

        XCTAssertThrowsError(try recorder.segments(for: workout, on: board)) { error in
            XCTAssertEqual(
                error as? WorkoutActivityRecordingError,
                .handSideRequired(stepID: "portable-step")
            )
        }

        let records = try recorder.segments(
            for: workout,
            on: board,
            selectedHandSide: .right
        )
        let record = try XCTUnwrap(records.first)
        XCTAssertEqual(record.handUse, .single)
        XCTAssertEqual(record.side, .right)
        XCTAssertEqual(record.target?.resolvedContactSnapshot?.contactIDs, ["left-b"])
        XCTAssertEqual(
            try JSONDecoder().decode(
                WorkoutActivityMetadata.self,
                from: JSONEncoder().encode(WorkoutActivityMetadata(segments: [record]))
            ).segments.first?.side,
            .right
        )
    }

    func testEitherHandActivityRecordsLeftRightPreferenceLikeSelectedHandSide() throws {
        let board = portableBoard(handCapacity: 1)
        let workout = portablePlan(handUse: .either, side: .both)
        let recorder = WorkoutActivityRecorder()

        let left = try XCTUnwrap(
            try recorder.segments(for: workout, on: board, handPreference: .left).first
        )
        XCTAssertEqual(left.handUse, .single)
        XCTAssertEqual(left.side, .left)

        let right = try XCTUnwrap(
            try recorder.segments(for: workout, on: board, handPreference: .right).first
        )
        XCTAssertEqual(right.handUse, .single)
        XCTAssertEqual(right.side, .right)
        XCTAssertEqual(right.target?.resolvedContactSnapshot?.contactIDs, ["left-b"])
    }

    func testEitherHandActivityRecordsBothPreferenceAsDoubleBoth() throws {
        let board = portableBoard(handCapacity: 1)
        let workout = portablePlan(handUse: .either, side: .both)

        let records = try WorkoutActivityRecorder().segments(
            for: workout,
            on: board,
            handPreference: .both
        )
        let record = try XCTUnwrap(records.first)
        XCTAssertEqual(record.handUse, .double)
        XCTAssertEqual(record.side, .both)
        XCTAssertEqual(record.stepID, "portable-step")
        XCTAssertEqual(
            record.target?.resolvedContactSnapshot?.requirement.selection,
            .single
        )
    }

    func testEitherHandActivityRecordsAlternateAsExpandedLeftThenRightSteps() throws {
        let board = portableBoard(handCapacity: 1)
        let workout = portablePlan(handUse: .either, side: .both)

        let records = try WorkoutActivityRecorder().segments(
            for: workout,
            on: board,
            handPreference: .alternate
        )

        XCTAssertEqual(records.count, 2)
        XCTAssertEqual(records.map(\.stepID), ["portable-step.left", "portable-step.right"])
        XCTAssertEqual(records.map(\.stepNumber), [1, 2])
        XCTAssertEqual(records.map(\.handUse), [.single, .single])
        XCTAssertEqual(records.map(\.side), [.left, .right])
    }

    func testSessionStepsArePreferredSourceOfTruthOverUnresolvedPlanSteps() throws {
        let board = portableBoard(handCapacity: 1)
        let workout = portablePlan(handUse: .either, side: .both)
        let sessionSteps = WorkoutSessionHandResolver.sessionSteps(
            from: workout.steps,
            preference: .alternate,
            boardIsOneHanded: board.isOneHanded
        )

        // Without sessionSteps/handPreference this would throw handSideRequired.
        let records = try WorkoutActivityRecorder().segments(
            for: workout,
            on: board,
            sessionSteps: sessionSteps
        )

        XCTAssertEqual(records.map(\.stepID), ["portable-step.left", "portable-step.right"])
        XCTAssertEqual(records.map(\.side), [.left, .right])
    }

    func testDoubleHandWorkOnOneHandedBoardRecordsThroughNormalizedSegmentTargets() throws {
        let board = oneHandedRecordingBoard()
        let requirement = ContactRequirement.kind(.pocket, selection: .bilateralPair)
        let workout = TrainingPlan(
            id: "one-handed-plan",
            title: "One-handed plan",
            subtitle: "",
            level: "",
            sourceLabel: "",
            sourceURL: URL(string: "https://example.com/one-handed-plan")!,
            provenance: .adapted,
            boardID: board.id,
            steps: [
                WorkoutStep(
                    id: "one-handed-step",
                    number: 1,
                    title: "One-handed step",
                    instruction: "",
                    accessory: "",
                    duration: 10,
                    phase: .hang,
                    segments: [WorkoutSegment(kind: .work, target: .fromLegacyTargets([requirement]), timing: .fixed, duration: 10)],
                    handUse: .double,
                    side: .both
                )
            ]
        )

        let records = try WorkoutActivityRecorder().segments(
            for: workout,
            on: board,
            selectedHandSide: .left
        )

        let record = try XCTUnwrap(records.first)
        XCTAssertEqual(record.handUse, .single)
        XCTAssertEqual(record.side, .left)
        XCTAssertEqual(record.target?.resolvedContactSnapshot?.contactIDs, ["one-handed-pocket"])
        XCTAssertEqual(
            record.target?.resolvedContactSnapshot?.requirement.selection,
            .single
        )
    }

    func testIsIncompatibleWithBilateralStepOnOneHandedBoard() throws {
        let board = oneHandedRecordingBoard()
        let requirement = ContactRequirement.kind(.pocket, selection: .bilateralPair)
        let workout = TrainingPlan(
            id: "one-handed-plan",
            title: "One-handed plan",
            subtitle: "",
            level: "",
            sourceLabel: "",
            sourceURL: URL(string: "https://example.com/one-handed-plan")!,
            provenance: .adapted,
            boardID: board.id,
            steps: [
                WorkoutStep(
                    id: "one-handed-step",
                    number: 1,
                    title: "One-handed step",
                    instruction: "",
                    accessory: "",
                    duration: 10,
                    phase: .hang,
                    segments: [WorkoutSegment(kind: .work, target: .fromLegacyTargets([requirement]), timing: .fixed, duration: 10)],
                    handUse: .double,
                    side: .both
                )
            ]
        )

        let store = AppStore(
            healthKitService: WorkoutHealthStoreSpy(),
            workoutSessionStore: makeSessionStore(defaults: makeHealthConnectedDefaults()),
            defaults: makeHealthConnectedDefaults()
        )
        store.selectBoard(board)

        XCTAssertFalse(
            store.isIncompatible(workout, on: board),
            "A .double step on a one-handed board should NOT be incompatible after resolution normalizes targets"
        )
    }

    func testActivityRecordingRejectsNonGeometricDoubleHandPairWithoutCapacity() {
        let board = portableBoard(
            id: "new-single-object-board",
            handCapacity: nil
        )
        let workout = portablePlan(handUse: .double, side: .both, boardID: board.id)

        XCTAssertThrowsError(try WorkoutActivityRecorder().segments(for: workout, on: board))
    }

    func testActivityRecordingDoesNotSpecialCaseBoardIDsForDoubleHandPairs() {
        let board = portableBoard(id: "beastmaker-1000", handCapacity: nil)
        let workout = portablePlan(handUse: .double, side: .both, boardID: board.id)

        XCTAssertThrowsError(try WorkoutActivityRecorder().segments(for: workout, on: board))
    }

    func testSevenThreeRepeatersRecordSourceWorkWithoutAppSelectedTargets() throws {
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
        XCTAssertTrue(
            workSteps.allSatisfy { !$0.workRequirements.isEmpty },
            "7/3 repeater titles prescribe concrete edge depths/finger capacities for highlighting"
        )

        let recordedWork = try WorkoutActivityRecorder()
            .segments(for: plan, on: board)
            .filter { $0.kind == .work }
        XCTAssertEqual(recordedWork.count, workSteps.count)
        XCTAssertTrue(
            recordedWork.allSatisfy {
                $0.target == .selfSelected || $0.target?.resolvedContactSnapshot != nil
            },
            "Board-agnostic source work resolves when possible, otherwise soft-falls to self-selected"
        )
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
                target: .fromLegacyTargets([.edge(depth: .category(.medium))]),
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
                target: .fromLegacyTargets([.kind(.edge)]),
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
                target: .fromLegacyTargets([.kind(.edge)]),
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
                target: .fromLegacyTargets([.kind(.edge)]),
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
                target: .fromLegacyTargets([ContactRequirement(
                    kind: .edge,
                    shape: .round
                )]),
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
        let requirement = ContactRequirement.edge(depth: .category(.medium))
        let activitySegments = [
            RecordedActivitySegment(
                stepID: "step",
                stepNumber: 1,
                kind: .work,
                target: .resolvedContacts(
                    ResolvedContactSnapshot(
                        boardID: board.id,
                        revisionID: board.revisionID,
                        modelSHA256: nil,
                        requirement: requirement,
                        contactIDs: ["edge-left"]
                    )
                ),
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
        XCTAssertNil(metadata["HangTen.ActivitySegments"])
        let json = try XCTUnwrap(metadata["HangTen.ActivitySegments.v2"] as? String)
        let decoded = try JSONDecoder().decode(
            WorkoutActivityMetadata.self,
            from: Data(json.utf8)
        )
        XCTAssertEqual(
            json,
            #"{"measurements":[{"actualLoadedDurationSeconds":3.5,"peakLoadKGF":37.25,"stepID":"step"}],"segments":[{"durationSeconds":8.75,"kind":"work","stepID":"step","stepNumber":1,"target":{"kind":"resolvedContacts","resolution":{"boardID":"fixture.board","contactIDs":["edge-left"],"requirement":{"depth":{"category":"medium"},"kind":"edge","selection":"single"},"revisionID":"test-fixture"}}}],"version":3}"#
        )
        XCTAssertEqual(
            decoded,
            WorkoutActivityMetadata(
                segments: activitySegments,
                measurements: activityMeasurements
            )
        )
    }

    func testLiteralVersionOnePayloadIsNotReinterpretedAsVersionTwo() {
        let json = #"{"segments":[{"holdIDs":[],"kind":"rest","stepID":"step","stepNumber":1}],"version":1}"#

        XCTAssertThrowsError(
            try JSONDecoder().decode(
                WorkoutActivityMetadata.self,
                from: Data(json.utf8)
            )
        )
    }

    func testVersionTwoPayloadRejectsProhibitedBareHoldFields() {
        let json = #"{"segments":[{"holdIDs":["edge"],"holdType":"edge","kind":"work","sizeMillimeters":20,"stepID":"step","stepNumber":1}],"version":2}"#

        XCTAssertThrowsError(
            try JSONDecoder().decode(
                WorkoutActivityMetadata.self,
                from: Data(json.utf8)
            )
        ) { error in
            guard case let DecodingError.dataCorrupted(context) = error else {
                return XCTFail("Expected strict segment-field rejection, got \(error)")
            }
            XCTAssertTrue(context.debugDescription.contains("Unsupported"))
        }
    }

    func testVersionTwoPayloadRejectsUnknownTopLevelLegacyField() {
        let json = #"{"segments":[],"version":2,"holdIDs":[]}"#

        XCTAssertThrowsError(
            try JSONDecoder().decode(
                WorkoutActivityMetadata.self,
                from: Data(json.utf8)
            )
        ) { error in
            guard case let DecodingError.dataCorrupted(context) = error else {
                return XCTFail("Expected strict metadata-field rejection, got \(error)")
            }
            XCTAssertTrue(context.debugDescription.contains("Unsupported workout activity metadata field holdIDs"))
        }
    }

    func testVersionTwoPayloadRejectsLegacyFieldNestedInContactSnapshot() {
        let json = #"{"segments":[{"kind":"work","stepID":"step","stepNumber":1,"target":{"kind":"resolvedContacts","resolution":{"boardID":"fixture.board","revisionID":"fixture","requirement":{"selection":"single"},"contactIDs":["edge"],"holdID":"edge"}}}],"version":2}"#

        XCTAssertThrowsError(
            try JSONDecoder().decode(
                WorkoutActivityMetadata.self,
                from: Data(json.utf8)
            )
        ) { error in
            guard case let DecodingError.dataCorrupted(context) = error else {
                return XCTFail("Expected strict contact-snapshot rejection, got \(error)")
            }
            XCTAssertTrue(context.debugDescription.contains("Unsupported resolved contact snapshot field holdID"))
        }
    }

    func testVersionTwoPayloadRejectsUnknownFieldNestedInRequirementDepthRange() {
        let json = #"{"segments":[{"kind":"work","stepID":"step","stepNumber":1,"target":{"kind":"resolvedContacts","resolution":{"boardID":"fixture.board","revisionID":"fixture","requirement":{"depth":{"range":{"maximum":22,"minimum":18,"unexpected":true}},"selection":"single"},"contactIDs":["edge"]}}}],"version":2}"#

        XCTAssertThrowsError(
            try JSONDecoder().decode(
                WorkoutActivityMetadata.self,
                from: Data(json.utf8)
            )
        ) { error in
            guard case let DecodingError.dataCorrupted(context) = error else {
                return XCTFail("Expected strict millimeter-range rejection, got \(error)")
            }
            XCTAssertEqual(
                context.debugDescription,
                "Unsupported millimeter range field unexpected."
            )
            XCTAssertEqual(
                normalizedCodingPath(context.codingPath),
                [
                    .key("segments"),
                    .index(0),
                    .key("target"),
                    .key("resolution"),
                    .key("requirement"),
                    .key("depth"),
                    .key("range"),
                    .key("unexpected")
                ]
            )
        }
    }

    func testVersionTwoPayloadRejectsLegacySizeFieldNestedInRequirementDepthRange() {
        let json = #"{"segments":[{"kind":"work","stepID":"step","stepNumber":1,"target":{"kind":"resolvedContacts","resolution":{"boardID":"fixture.board","revisionID":"fixture","requirement":{"depth":{"range":{"maximum":22,"minimum":18,"sizeMillimeters":20}},"selection":"single"},"contactIDs":["edge"]}}}],"version":2}"#

        XCTAssertThrowsError(
            try JSONDecoder().decode(
                WorkoutActivityMetadata.self,
                from: Data(json.utf8)
            )
        ) { error in
            guard case let DecodingError.dataCorrupted(context) = error else {
                return XCTFail("Expected legacy millimeter-range field rejection, got \(error)")
            }
            XCTAssertEqual(
                context.debugDescription,
                "Unsupported millimeter range field sizeMillimeters."
            )
            XCTAssertEqual(
                normalizedCodingPath(context.codingPath),
                [
                    .key("segments"),
                    .index(0),
                    .key("target"),
                    .key("resolution"),
                    .key("requirement"),
                    .key("depth"),
                    .key("range"),
                    .key("sizeMillimeters")
                ]
            )
        }
    }

    func testVersionTwoPayloadRejectsAlphabeticallyFirstUnknownDepthRangeField() {
        let json = #"{"segments":[{"kind":"work","stepID":"step","stepNumber":1,"target":{"kind":"resolvedContacts","resolution":{"boardID":"fixture.board","revisionID":"fixture","requirement":{"depth":{"range":{"maximum":22,"minimum":18,"zetaUnknown":true,"alphaUnknown":true}},"selection":"single"},"contactIDs":["edge"]}}}],"version":2}"#

        XCTAssertThrowsError(
            try JSONDecoder().decode(
                WorkoutActivityMetadata.self,
                from: Data(json.utf8)
            )
        ) { error in
            guard case let DecodingError.dataCorrupted(context) = error else {
                return XCTFail("Expected deterministic millimeter-range rejection, got \(error)")
            }
            XCTAssertEqual(
                context.debugDescription,
                "Unsupported millimeter range field alphaUnknown."
            )
            XCTAssertEqual(
                normalizedCodingPath(context.codingPath),
                [
                    .key("segments"),
                    .index(0),
                    .key("target"),
                    .key("resolution"),
                    .key("requirement"),
                    .key("depth"),
                    .key("range"),
                    .key("alphaUnknown")
                ]
            )
        }
    }

    func testVersionTwoPayloadRejectsLegacyFieldNestedInMeasurement() {
        let json = #"{"measurements":[{"stepID":"step","holdName":"Legacy edge"}],"segments":[],"version":2}"#

        XCTAssertThrowsError(
            try JSONDecoder().decode(
                WorkoutActivityMetadata.self,
                from: Data(json.utf8)
            )
        ) { error in
            guard case let DecodingError.dataCorrupted(context) = error else {
                return XCTFail("Expected strict measurement-field rejection, got \(error)")
            }
            XCTAssertTrue(context.debugDescription.contains("Unsupported activity measurement field holdName"))
        }
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

    private func normalizedCodingPath(_ codingPath: [CodingKey]) -> [CodingPathComponent] {
        codingPath.map { key in
            if let index = key.intValue {
                return .index(index)
            }
            return .key(key.stringValue)
        }
    }

    func testHealthKitMetadataEncodingFailureUsesLocalizedWriteError() {
        let invalidSegment = RecordedActivitySegment(
            stepID: "step",
            stepNumber: 1,
            kind: .work,
            target: .selfSelected,
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

    private func step(targets: [ContactRequirement]) -> WorkoutStep {
        WorkoutStep(
            id: "step",
            number: 1,
            title: "Step",
            instruction: "Instruction",
            accessory: "",
            duration: 60,
            phase: .hang,
            segments: [
                WorkoutSegment(
                    kind: .work,
                    target: .fromLegacyTargets(targets),
                    timing: .undefined,
                    duration: nil
                )
            ]
        )
    }

    private func plan(
        targets: [ContactRequirement],
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
                    segments: segments.isEmpty
                        ? [
                            WorkoutSegment(
                                kind: .work,
                                target: .fromLegacyTargets(targets),
                                timing: .undefined,
                                duration: nil
                            )
                        ]
                        : segments
                )
            ]
        )
    }

    private func portableBoard(
        id: String = "portable-board",
        handCapacity: Int?,
        secondSide: ContactSide = .right
    ) -> BoardRevision {
        BoardRevision(
            id: id,
            revisionID: "test-fixture",
            manufacturer: "Fixture",
            name: "Portable board",
            subtitle: "",
            dimensions: "",
            aspectRatio: 1,
            handCapacity: handCapacity ?? 2,
            equipmentObjects: [.init(id: "left")],
            contacts: [
                PhysicalContact(
                    id: "left-a",
                    equipmentObjectID: "left",
                    name: "Left A",
                    kind: .pocket,
                    handCapacity: handCapacity,
                    side: .left,
                    pairedContactID: "left-b"
                ),
                PhysicalContact(
                    id: "left-b",
                    equipmentObjectID: "left",
                    name: "Left B",
                    kind: .pocket,
                    handCapacity: handCapacity,
                    side: secondSide,
                    pairedContactID: "left-a"
                )
            ],
            productURL: URL(string: "https://example.com/portable")!,
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
                            "left-a": [testPiece(id: "left-a", x: 0)],
                            "left-b": [testPiece(id: "left-b", x: 0.2)]
                        ]
                    ))
                )
            ]
        )
    }

    private func oneHandedRecordingBoard() -> BoardRevision {
        let contact = PhysicalContact(
            id: "one-handed-pocket",
            name: "One-handed pocket",
            kind: .pocket,
            handCapacity: 1,
            side: .left
        )
        return BoardRevision(
            id: "one-handed-recording-board",
            revisionID: "test-fixture",
            manufacturer: "Fixture",
            name: "One-handed board",
            subtitle: "",
            dimensions: "",
            aspectRatio: 1,
            handCapacity: 1,
            contacts: [contact],
            productURL: URL(string: "https://example.com/one-handed-recording")!,
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
                            contact.id: [testPiece(id: contact.id, x: 0.5)]
                        ]
                    ))
                )
            ]
        )
    }

    private func testPiece(id: String, x: CGFloat) -> BoardContactPiece {
        BoardContactPiece(
            id: "\(id)-piece",
            contactID: id,
            frame: CGRect(x: x, y: 0, width: 0.1, height: 0.1),
            shape: .roundedRect(cornerRadiusFraction: 0),
            treatment: .surface
        )
    }

    private func portablePlan(
        handUse: WorkoutHandUse,
        side: WorkoutSide,
        boardID: String = "portable-board"
    ) -> TrainingPlan {
        let requirement = ContactRequirement.kind(
            .pocket,
            selection: handUse == .double ? .bilateralPair : .single
        )
        return TrainingPlan(
            id: "portable-plan",
            title: "Portable plan",
            subtitle: "",
            level: "",
            sourceLabel: "",
            sourceURL: URL(string: "https://example.com/portable-plan")!,
            provenance: .adapted,
            boardID: boardID,
            steps: [
                WorkoutStep(
                    id: "portable-step",
                    number: 1,
                    title: "Portable step",
                    instruction: "",
                    accessory: "",
                    duration: 10,
                    phase: .hang,
                    segments: [WorkoutSegment(kind: .work, target: .fromLegacyTargets([requirement]), timing: .fixed, duration: 10)],
                    handUse: handUse,
                    side: side
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
