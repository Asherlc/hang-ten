import XCTest
@testable import HangTen

final class CustomRoutineStoreTests: XCTestCase {
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

        let reloaded = CustomRoutineStore(defaults: defaults)
        XCTAssertEqual(reloaded.routines, [definition])
        let plan = try reloaded.plan(for: definition)
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
        subtitle: String = "",
        difficulty: String? = nil,
        category: String? = nil,
        tags: [String] = [],
        targets: [WorkoutTargetDefinition] = [.kind(.jug)],
        segments: [WorkoutSegmentDefinition] = []
    ) -> CustomRoutineDefinition {
        CustomRoutineDefinition(
            id: "custom.generic",
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
