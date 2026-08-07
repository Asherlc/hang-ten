import XCTest
@testable import HangTen

final class CustomRoutineStoreTests: XCTestCase {
    func testCompactIIPocketsExposeCapacityWithoutChangingOpenHandPosture() throws {
        let twoFingerPocket = try XCTUnwrap(
            BoardCatalog.compactII.holds.first { $0.id == "pocket-29-two-left" }
        )
        let threeFingerPocket = try XCTUnwrap(
            BoardCatalog.compactII.holds.first { $0.id == "pocket-29-three-left" }
        )
        let fourFingerPocket = try XCTUnwrap(
            BoardCatalog.compactII.holds.first { $0.id == "pocket-29-four-center" }
        )

        XCTAssertEqual(twoFingerPocket.fingerCapacity, 2)
        XCTAssertEqual(threeFingerPocket.fingerCapacity, 3)
        XCTAssertEqual(fourFingerPocket.fingerCapacity, 4)
        XCTAssertEqual(twoFingerPocket.gripType, .openHand)
        XCTAssertEqual(threeFingerPocket.gripType, .openHand)
        XCTAssertEqual(fourFingerPocket.gripType, .openHand)
    }

    func testPlanResolutionRetainsExactFingerConfiguration() throws {
        let expectedConfiguration = FingerConfiguration(engagedFingers: [.index])
        let step = WorkoutStepDefinition(
            id: "exact-finger-step",
            title: "One-finger hang",
            instruction: "Hang with the index finger.",
            accessory: "10s",
            duration: 10,
            phase: .hang,
            targets: [.feature(.threeFingerPocket, fallbacks: [])],
            gripType: .openHand,
            fingerConfiguration: expectedConfiguration,
            activeDuration: 10
        )
        let library = PlanLibraryDefinition(
            metadata: PlanLibraryMetadata(
                id: "exact-finger-library",
                version: "1",
                title: "Exact fingers",
                generatedAt: "2026-08-07"
            ),
            boardMappings: [],
            blocks: [WorkoutBlockDefinition(id: "exact-finger-block", steps: [step])],
            plans: [
                PlanDefinition(
                    id: "exact-finger-plan",
                    metadata: PlanMetadata(
                        title: "Exact fingers",
                        subtitle: "",
                        level: "Test",
                        sourceLabel: "Created in Hang Ten",
                        sourceURL: nil,
                        provenance: .custom
                    ),
                    boardID: nil,
                    blocks: [WorkoutBlockReference(blockID: "exact-finger-block")]
                )
            ]
        )

        let resolved = try PlanDefinitionResolver(library: library).resolve(library.plans[0])

        XCTAssertEqual(resolved.steps.map(\.fingerConfiguration), [expectedConfiguration])
    }

    func testCustomRoutineSaveAndLoadPreservesNonContiguousExactFingers() throws {
        let suite = "CustomRoutineStoreTests.\(UUID().uuidString)"
        let defaults = try XCTUnwrap(UserDefaults(suiteName: suite))
        defer { defaults.removePersistentDomain(forName: suite) }
        let expectedConfiguration = FingerConfiguration(engagedFingers: [.index, .ring])
        let definition = CustomRoutineDefinition(
            id: "custom.exact-fingers",
            title: "Exact finger routine",
            subtitle: "",
            difficulty: nil,
            category: nil,
            tags: [],
            targetMode: .generic,
            steps: [
                WorkoutStepDefinition(
                    id: "exact-finger-step",
                    title: "Exact finger hang",
                    instruction: "Use index and ring fingers.",
                    accessory: "10s",
                    duration: 10,
                    phase: .hang,
                    targets: [.feature(.threeFingerPocket, fallbacks: [])],
                    gripType: .openHand,
                    fingerConfiguration: expectedConfiguration,
                    activeDuration: 10
                )
            ]
        )
        let store = CustomRoutineStore(defaults: defaults)

        try store.save(definition)

        let reloaded = CustomRoutineStore(defaults: defaults)
        XCTAssertEqual(reloaded.routines.first?.steps.first?.fingerConfiguration, expectedConfiguration)
    }

    func testBoardSpecificDefinitionRoundTripsAndResolvesToTrainingPlan() throws {
        let suite = "CustomRoutineStoreTests.\(UUID().uuidString)"
        let defaults = try XCTUnwrap(UserDefaults(suiteName: suite))
        defer { defaults.removePersistentDomain(forName: suite) }

        let definition = CustomRoutineDefinition(
            id: "custom.board",
            title: "Edge strength",
            subtitle: "Short edge work",
            difficulty: "Advanced",
            category: "strength",
            tags: ["custom", "edges"],
            targetMode: .boardSpecific(boardID: BoardCatalog.compactII.id),
            steps: [
                WorkoutStepDefinition(
                    id: "step-1",
                    title: "Hang",
                    instruction: "Hang from the 19 mm edges.",
                    accessory: "10s",
                    duration: 10,
                    phase: .hang,
                    targets: [.holdIDs(["edge-19-left", "edge-19-right"])],
                    gripType: .halfCrimp,
                    activeDuration: 10
                )
            ]
        )
        let store = CustomRoutineStore(defaults: defaults)

        try store.save(definition)

        let persisted = try XCTUnwrap(store.routines.first)
        let reloaded = CustomRoutineStore(defaults: defaults)
        XCTAssertEqual(reloaded.routines, [persisted])
        XCTAssertEqual(persisted.steps.map(\.id), ["step-1"])
        XCTAssertEqual(persisted.steps.map { $0.segments.count }, [1])
        let plan = try reloaded.plan(for: persisted)
        XCTAssertEqual(plan.id, definition.id)
        XCTAssertEqual(plan.title, definition.title)
        XCTAssertEqual(plan.steps[0].targets, [.ids("edge-19-left", "edge-19-right")])
        XCTAssertEqual(plan.provenance, .custom)
        XCTAssertNil(plan.sourceURL)
    }

    func testGenericDefinitionRequiresTargetsThatResolveOnARegisteredBoard() throws {
        let definition = CustomRoutineDefinition(
            id: "custom.generic",
            title: "Generic edge work",
            subtitle: "",
            difficulty: nil,
            category: nil,
            tags: [],
            targetMode: .generic,
            steps: [
                WorkoutStepDefinition(
                    id: "step-1",
                    title: "Edge hang",
                    instruction: "Hang.",
                    accessory: "10s",
                    duration: 10,
                    phase: .hang,
                    targets: [.feature(.mediumEdge, fallbacks: [])],
                    activeDuration: 10
                )
            ]
        )

        XCTAssertTrue(CustomRoutineValidator.issues(for: definition, availableBoards: BoardCatalog.all).isEmpty)
    }

    func testSaveAndResolveAllowsEmptyOptionalSubtitle() throws {
        let suite = "CustomRoutineStoreTests.\(UUID().uuidString)"
        let defaults = try XCTUnwrap(UserDefaults(suiteName: suite))
        defer { defaults.removePersistentDomain(forName: suite) }
        let definition = genericDefinition(id: "custom.empty-subtitle")
        let store = CustomRoutineStore(defaults: defaults)

        try store.save(definition)

        let persisted = try XCTUnwrap(store.routines.first)
        let plan = try store.plan(for: persisted)

        XCTAssertEqual(plan.id, definition.id)
        XCTAssertEqual(plan.title, definition.title)
        XCTAssertEqual(plan.subtitle, "")
        XCTAssertEqual(plan.provenance, .custom)
    }

    func testValidationRejectsBlankNameMissingTargetsAndInvalidDuration() {
        let definition = CustomRoutineDefinition(
            id: "custom.invalid",
            title: "   ",
            subtitle: "",
            difficulty: nil,
            category: nil,
            tags: [],
            targetMode: .generic,
            steps: [
                WorkoutStepDefinition(
                    id: "step-1",
                    title: "Hang",
                    instruction: "Hang.",
                    accessory: "",
                    duration: 0,
                    phase: .hang,
                    targets: []
                )
            ]
        )

        let issues = CustomRoutineValidator.issues(for: definition, availableBoards: BoardCatalog.all)

        XCTAssertTrue(issues.contains(.emptyTitle))
        XCTAssertTrue(issues.contains(.invalidDuration(stepIndex: 0)))
        XCTAssertTrue(issues.contains(.missingTargets(stepIndex: 0)))
    }

    func testCorruptStoredDataLoadsEmptyAndPublishesPersistenceError() throws {
        let suite = "CustomRoutineStoreTests.\(UUID().uuidString)"
        let defaults = try XCTUnwrap(UserDefaults(suiteName: suite))
        defer { defaults.removePersistentDomain(forName: suite) }
        defaults.set(Data("not-json".utf8), forKey: CustomRoutineStore.defaultKey)

        let store = CustomRoutineStore(defaults: defaults)

        XCTAssertTrue(store.routines.isEmpty)
        XCTAssertNotNil(store.persistenceError)
    }

    func testLoadKeepsTheFirstPersistedRoutineForEachDuplicateIDAndWarns() throws {
        let suite = "CustomRoutineStoreTests.\(UUID().uuidString)"
        let defaults = try XCTUnwrap(UserDefaults(suiteName: suite))
        defer { defaults.removePersistentDomain(forName: suite) }
        let first = genericDefinition(id: "custom.duplicate", subtitle: "First")
        let duplicate = genericDefinition(id: "custom.duplicate", subtitle: "Second")
        defaults.set(
            try JSONEncoder().encode(CustomRoutineLibrary(routines: [first, duplicate])),
            forKey: CustomRoutineStore.defaultKey
        )

        let store = CustomRoutineStore(defaults: defaults)

        XCTAssertEqual(store.routines, [first])
        XCTAssertEqual(store.persistenceError, "Some custom routines could not be loaded.")
    }

    func testDeletingAnUnknownRoutineLeavesPersistedDataUntouched() throws {
        let suite = "CustomRoutineStoreTests.\(UUID().uuidString)"
        let defaults = try XCTUnwrap(UserDefaults(suiteName: suite))
        defer { defaults.removePersistentDomain(forName: suite) }
        let persistedData = try JSONEncoder().encode(
            CustomRoutineLibrary(routines: [genericDefinition(id: "custom.persisted")])
        )
        defaults.set(persistedData, forKey: CustomRoutineStore.defaultKey)
        let store = CustomRoutineStore(defaults: defaults)

        try store.delete(id: "custom.unknown")

        XCTAssertEqual(defaults.data(forKey: CustomRoutineStore.defaultKey), persistedData)
    }

    func testSaveNormalizesOptionalMetadataAndDuplicateTags() throws {
        let suite = "CustomRoutineStoreTests.\(UUID().uuidString)"
        let defaults = try XCTUnwrap(UserDefaults(suiteName: suite))
        defer { defaults.removePersistentDomain(forName: suite) }
        let definition = genericDefinition(
            subtitle: "  Short session  ",
            difficulty: "  ",
            category: "  strength ",
            tags: ["  Edges ", "edges", "Custom", " CUSTOM "]
        )
        let store = CustomRoutineStore(defaults: defaults)

        try store.save(definition)

        let saved = try XCTUnwrap(store.routines.first)
        XCTAssertEqual(saved.subtitle, "Short session")
        XCTAssertNil(saved.difficulty)
        XCTAssertEqual(saved.category, "strength")
        XCTAssertEqual(saved.tags, ["Edges", "Custom"])
    }

    func testSaveSplitsCommaSeparatedTagsInOrder() throws {
        let suite = "CustomRoutineStoreTests.\(UUID().uuidString)"
        let defaults = try XCTUnwrap(UserDefaults(suiteName: suite))
        defer { defaults.removePersistentDomain(forName: suite) }
        let definition = genericDefinition(tags: [" edges, custom "])
        let store = CustomRoutineStore(defaults: defaults)

        try store.save(definition)

        XCTAssertEqual(store.routines.first?.tags, ["edges", "custom"])
    }

    func testValidationRejectsUnknownBoardAndHoldIDsForBoardSpecificRoutine() {
        let definition = CustomRoutineDefinition(
            id: "custom.unknown-board",
            title: "Unknown board",
            subtitle: "",
            difficulty: nil,
            category: nil,
            tags: [],
            targetMode: .boardSpecific(boardID: "unknown-board"),
            steps: [validStep(targets: [.holdIDs(["missing-hold"])])]
        )

        let issues = CustomRoutineValidator.issues(for: definition, availableBoards: BoardCatalog.all)

        XCTAssertTrue(issues.contains(.unknownBoard(boardID: "unknown-board")))
        XCTAssertTrue(issues.contains(.unknownHoldID(stepIndex: 0, holdID: "missing-hold")))
    }

    func testValidationRejectsGenericTargetsThatCannotResolve() {
        let definition = genericDefinition(targets: [.feature(.fourFingerIncutEdge, fallbacks: [])])

        let issues = CustomRoutineValidator.issues(for: definition, availableBoards: BoardCatalog.all)

        XCTAssertTrue(issues.contains(.unresolvableTargets(stepIndex: 0)))
    }

    func testValidationRejectsTargetStorageThatDoesNotMatchRoutineMode() {
        let boardSpecific = CustomRoutineDefinition(
            id: "custom.board-mode-mismatch",
            title: "Board mismatch",
            subtitle: "",
            difficulty: nil,
            category: nil,
            tags: [],
            targetMode: .boardSpecific(boardID: BoardCatalog.compactII.id),
            steps: [validStep(
                targets: [.kind(.jug)],
                segments: [
                    WorkoutSegmentDefinition(
                        kind: .work,
                        targets: [.feature(.mediumEdge, fallbacks: [])],
                        timing: .fixed,
                        duration: 10
                    )
                ]
            )]
        )
        let generic = genericDefinition(
            targets: [.holdIDs(["edge-19-left"])],
            segments: [
                WorkoutSegmentDefinition(
                    kind: .work,
                    targets: [.holdIDs(["edge-19-right"])],
                    timing: .fixed,
                    duration: 10
                )
            ]
        )

        let boardIssues = CustomRoutineValidator.issues(
            for: boardSpecific,
            availableBoards: BoardCatalog.all
        )
        let genericIssues = CustomRoutineValidator.issues(
            for: generic,
            availableBoards: BoardCatalog.all
        )

        XCTAssertTrue(boardIssues.contains(.targetModeMismatch(stepIndex: 0, segmentIndex: nil)))
        XCTAssertTrue(boardIssues.contains(.targetModeMismatch(stepIndex: 0, segmentIndex: 0)))
        XCTAssertTrue(genericIssues.contains(.targetModeMismatch(stepIndex: 0, segmentIndex: nil)))
        XCTAssertTrue(genericIssues.contains(.targetModeMismatch(stepIndex: 0, segmentIndex: 0)))
    }

    func testSavePersistsOnlyLiteralRowsThroughSharedNormalization() throws {
        let suite = "CustomRoutineStoreTests.\(UUID().uuidString)"
        let defaults = try XCTUnwrap(UserDefaults(suiteName: suite))
        defer { defaults.removePersistentDomain(forName: suite) }
        let source = CustomRoutineDefinition(
            id: "custom.compound",
            title: "Compound source",
            subtitle: "",
            difficulty: nil,
            category: nil,
            tags: [],
            targetMode: .boardSpecific(boardID: BoardCatalog.compactII.id),
            steps: [
                WorkoutStepDefinition(
                    id: "repeat",
                    title: "Repeat",
                    instruction: "Work then rest.",
                    accessory: "8s · 4s",
                    duration: 12,
                    phase: .hang,
                    targets: [.holdIDs(["edge-19-left"])],
                    segments: [
                        WorkoutSegmentDefinition(
                            kind: .work,
                            targets: [.holdIDs(["edge-19-right"])],
                            timing: .fixed,
                            duration: 8
                        ),
                        WorkoutSegmentDefinition(
                            kind: .rest,
                            targets: [],
                            timing: .fixed,
                            duration: 4
                        )
                    ],
                    gripType: .halfCrimp
                ),
                WorkoutStepDefinition(
                    id: "implicit",
                    title: "Open hang",
                    instruction: "Hang with open timing.",
                    accessory: "Up to 20s",
                    duration: 20,
                    phase: .hang,
                    targets: [.holdIDs(["edge-19-left"])]
                ),
                WorkoutStepDefinition(
                    id: "stopwatch",
                    title: "Maximum hang",
                    instruction: "Stop when you release.",
                    accessory: "Up to 30s",
                    duration: 30,
                    phase: .hang,
                    targets: [.holdIDs(["edge-19-right"])],
                    segments: [
                        WorkoutSegmentDefinition(
                            kind: .work,
                            targets: [.holdIDs(["edge-19-right"])],
                            timing: .stopwatch,
                            duration: nil
                        )
                    ],
                    gripType: .openHand
                )
            ]
        )
        let store = CustomRoutineStore(defaults: defaults)

        try store.save(source)

        let stored = try XCTUnwrap(store.routines.first)
        XCTAssertEqual(stored.steps.map(\.id), [
            "repeat.segment-1", "repeat.segment-2", "implicit", "stopwatch"
        ])
        XCTAssertEqual(stored.steps.map(\.phase), [.hang, .rest, .hang, .hang])
        XCTAssertEqual(stored.steps.map(\.targets), [
            [.holdIDs(["edge-19-right"])],
            [],
            [.holdIDs(["edge-19-left"])],
            [.holdIDs(["edge-19-right"])]
        ])
        XCTAssertEqual(stored.steps.map { $0.segments.count }, [1, 1, 1, 1])
        let persistedData = try XCTUnwrap(defaults.data(forKey: CustomRoutineStore.defaultKey))
        let persistedJSON = try XCTUnwrap(
            try JSONSerialization.jsonObject(with: persistedData) as? [String: Any]
        )
        let persistedRoutines = try XCTUnwrap(persistedJSON["routines"] as? [[String: Any]])
        let persistedSteps = try XCTUnwrap(persistedRoutines.first?["steps"] as? [[String: Any]])
        XCTAssertEqual(persistedSteps.first?["activeDuration"] as? Double, 8)
        XCTAssertEqual(stored.steps[2].segments[0].timing, .undefined)
        XCTAssertEqual(stored.steps[3].segments[0].timing, .stopwatch)
        XCTAssertEqual(CustomRoutineDraft(editing: stored).definition(), stored)

        let reloaded = CustomRoutineStore(defaults: defaults)
        XCTAssertEqual(reloaded.routines, [stored])
    }

    func testSavePersistsGenericCompoundWorkAndTargetlessRestRows() throws {
        let suite = "CustomRoutineStoreTests.\(UUID().uuidString)"
        let defaults = try XCTUnwrap(UserDefaults(suiteName: suite))
        defer { defaults.removePersistentDomain(forName: suite) }
        let definition = CustomRoutineDefinition(
            id: "custom.generic-compound",
            title: "Generic repeaters",
            subtitle: "",
            difficulty: nil,
            category: nil,
            tags: [],
            targetMode: .generic,
            steps: [
                WorkoutStepDefinition(
                    id: "repeat",
                    title: "Repeat",
                    instruction: "Work, then rest.",
                    accessory: "8s · 4s",
                    duration: 12,
                    phase: .hang,
                    targets: [.kind(.jug)],
                    segments: [
                        WorkoutSegmentDefinition(
                            kind: .work,
                            targets: [.kind(.jug)],
                            timing: .fixed,
                            duration: 8
                        ),
                        WorkoutSegmentDefinition(
                            kind: .rest,
                            targets: [],
                            timing: .fixed,
                            duration: 4
                        )
                    ]
                )
            ]
        )
        let store = CustomRoutineStore(defaults: defaults)

        try store.save(definition)

        let stored = try XCTUnwrap(store.routines.first)
        XCTAssertEqual(stored.steps.map(\.phase), [.hang, .rest])
        XCTAssertEqual(stored.steps.map(\.targets), [[.kind(.jug)], []])
        XCTAssertEqual(stored.steps.map { $0.segments.count }, [1, 1])

        let reloaded = CustomRoutineStore(defaults: defaults)
        XCTAssertEqual(reloaded.routines, [stored])
    }

    func testValidationRejectsInvalidNamespaceAndBuiltInCollisionIDs() throws {
        let blank = genericDefinition(id: "   ")
        let foreign = genericDefinition(id: "routine.foreign")
        let builtInID = try XCTUnwrap(PlanCatalog.all.first?.id)
        let collision = genericDefinition(id: builtInID)

        XCTAssertTrue(
            CustomRoutineValidator.issues(for: blank, availableBoards: BoardCatalog.all)
                .contains(.invalidID(id: "   "))
        )
        XCTAssertTrue(
            CustomRoutineValidator.issues(for: foreign, availableBoards: BoardCatalog.all)
                .contains(.invalidID(id: "routine.foreign"))
        )
        XCTAssertTrue(
            CustomRoutineValidator.issues(for: collision, availableBoards: BoardCatalog.all)
                .contains(.builtInIDCollision(id: builtInID))
        )
    }

    func testValidationRejectsRestStepTargets() {
        let definition = CustomRoutineDefinition(
            id: "custom.rest-targets",
            title: "Rest target",
            subtitle: "",
            difficulty: nil,
            category: nil,
            tags: [],
            targetMode: .generic,
            steps: [
                WorkoutStepDefinition(
                    id: "rest",
                    title: "Rest",
                    instruction: "Rest.",
                    accessory: "10s",
                    duration: 10,
                    phase: .rest,
                    targets: [.kind(.jug)]
                )
            ]
        )

        XCTAssertTrue(
            CustomRoutineValidator.issues(for: definition, availableBoards: BoardCatalog.all)
                .contains(.restStepHasTargets(stepIndex: 0))
        )
    }

    func testValidationRejectsInvalidSegmentTimingDurations() {
        let definition = genericDefinition(
            segments: [
                WorkoutSegmentDefinition(kind: .work, targets: [.kind(.jug)], timing: .fixed, duration: nil),
                WorkoutSegmentDefinition(kind: .work, targets: [.kind(.jug)], timing: .stopwatch, duration: 10)
            ]
        )

        let issues = CustomRoutineValidator.issues(for: definition, availableBoards: BoardCatalog.all)

        XCTAssertTrue(issues.contains(.missingFixedSegmentDuration(stepIndex: 0, segmentIndex: 0)))
        XCTAssertTrue(issues.contains(.unexpectedSegmentDuration(stepIndex: 0, segmentIndex: 1)))
        XCTAssertTrue(issues.contains(.invalidCompoundSegmentTiming(stepIndex: 0, segmentIndex: 1)))
    }

    func testValidationRejectsCompoundSegmentDurationsThatDoNotMatchTheStepDuration() {
        let definition = genericDefinition(
            segments: [
                WorkoutSegmentDefinition(kind: .work, targets: [.kind(.jug)], timing: .fixed, duration: 7),
                WorkoutSegmentDefinition(kind: .rest, targets: [], timing: .fixed, duration: 4)
            ]
        )

        XCTAssertTrue(
            CustomRoutineValidator.issues(for: definition, availableBoards: BoardCatalog.all)
                .contains(.compoundDurationMismatch(stepIndex: 0))
        )
    }

    func testCustomProvenanceIsOnlyPlanMetadataAllowedToOmitSourceURL() {
        let custom = PlanMetadata(
            title: "Custom",
            subtitle: "Local",
            level: "Custom",
            sourceLabel: "Created in Hang Ten",
            sourceURL: nil,
            provenance: .custom
        )
        let adapted = PlanMetadata(
            title: "Adapted",
            subtitle: "Linked",
            level: "Test",
            sourceLabel: "Test source",
            sourceURL: nil,
            provenance: .adapted
        )

        XCTAssertTrue(PlanLibraryValidator.issues(for: library(metadata: custom), availableBoards: BoardCatalog.all).isEmpty)
        XCTAssertFalse(PlanLibraryValidator.issues(for: library(metadata: adapted), availableBoards: BoardCatalog.all).isEmpty)
    }

    private func genericDefinition(
        id: String = "custom.generic",
        subtitle: String = "",
        difficulty: String? = nil,
        category: String? = nil,
        tags: [String] = [],
        targets: [WorkoutTargetDefinition] = [.kind(.jug)],
        segments: [WorkoutSegmentDefinition] = []
    ) -> CustomRoutineDefinition {
        CustomRoutineDefinition(
            id: id,
            title: "Generic routine",
            subtitle: subtitle,
            difficulty: difficulty,
            category: category,
            tags: tags,
            targetMode: .generic,
            steps: [validStep(targets: targets, segments: segments)]
        )
    }

    private func validStep(
        targets: [WorkoutTargetDefinition],
        segments: [WorkoutSegmentDefinition] = []
    ) -> WorkoutStepDefinition {
        WorkoutStepDefinition(
            id: "step-1",
            title: "Hang",
            instruction: "Hang.",
            accessory: "10s",
            duration: 10,
            phase: .hang,
            targets: targets,
            segments: segments,
            activeDuration: 10
        )
    }

    private func library(metadata: PlanMetadata) -> PlanLibraryDefinition {
        PlanLibraryDefinition(
            metadata: PlanLibraryMetadata(
                id: "test.library",
                version: "1",
                title: "Test library",
                generatedAt: "2026-08-05"
            ),
            boardMappings: [],
            blocks: [WorkoutBlockDefinition(id: "test.block", steps: [validStep(targets: [.kind(.jug)])])],
            plans: [PlanDefinition(id: "test.plan", metadata: metadata, boardID: nil, blocks: [WorkoutBlockReference(blockID: "test.block")])]
        )
    }
}
