import XCTest
@testable import HangTen

@MainActor
final class CustomRoutineAppStoreTests: XCTestCase {
    deinit {}

    private func makeDefaults() -> (suiteName: String, defaults: UserDefaults) {
        let suiteName = "CustomRoutineAppStoreTests.\(UUID().uuidString)"
        return (suiteName, UserDefaults(suiteName: suiteName)!)
    }

    private func makeRoutine(
        id: String = "custom.edge",
        mode: CustomRoutineTargetMode = .boardSpecific(boardID: BoardCatalog.compactII.id)
    ) -> CustomRoutineDefinition {
        CustomRoutineDefinition(
            id: id,
            title: "Custom edge routine",
            subtitle: "A local routine",
            difficulty: nil,
            category: nil,
            tags: ["custom"],
            targetMode: mode,
            steps: [WorkoutStepDefinition(
                id: "step-1",
                title: "Edge hang",
                instruction: "Hang from the edges.",
                accessory: "10s",
                duration: 10,
                phase: .hang,
                targets: mode == .generic
                    ? [.feature(.mediumEdge, fallbacks: [])]
                    : [.holdIDs(["edge-19-left", "edge-19-right"])],
                gripType: .halfCrimp,
                activeDuration: 10
            )]
        )
    }

    func testPlansCombinesBuiltInAndCustomThroughTrainingPlan() throws {
        let (suiteName, defaults) = makeDefaults()
        defer { defaults.removePersistentDomain(forName: suiteName) }
        let customStore = CustomRoutineStore(defaults: defaults)
        try customStore.save(makeRoutine())

        let store = AppStore(customRoutineStore: customStore, defaults: defaults)

        XCTAssertTrue(store.plans.contains { $0.id == "custom.edge" })
        XCTAssertTrue(store.plans.contains { $0.id == PlanCatalog.all[0].id })
        let custom = try XCTUnwrap(store.plans.first { $0.id == "custom.edge" })
        XCTAssertEqual(store.board(for: custom).id, BoardCatalog.compactII.id)
        XCTAssertEqual(
            store.holdIDs(for: custom.steps[0], on: BoardCatalog.compactII),
            ["edge-19-left", "edge-19-right"] as Set
        )
    }

    func testGenericCustomRoutineUsesSameBoardCompatibilityAndMetadataLookup() throws {
        let (suiteName, defaults) = makeDefaults()
        defer { defaults.removePersistentDomain(forName: suiteName) }
        let customStore = CustomRoutineStore(defaults: defaults)
        try customStore.save(makeRoutine(id: "custom.generic", mode: .generic))

        let store = AppStore(customRoutineStore: customStore, defaults: defaults)
        let plan = try XCTUnwrap(store.plans.first { $0.id == "custom.generic" })
        let metadata = store.metadata(for: plan)

        XCTAssertNil(plan.boardID)
        XCTAssertEqual(metadata.provenance, .custom)
        XCTAssertEqual(metadata.category, "custom")
        XCTAssertEqual(metadata.tags, ["custom"])
    }

    func testReloadUsesTheInjectedStorePlannerAndSharedCustomMetadata() throws {
        let (suiteName, defaults) = makeDefaults()
        defer { defaults.removePersistentDomain(forName: suiteName) }
        let definition = makeRoutine()
        let injectedStore = InjectedRoutineStore(definition: definition)

        let store = AppStore(customRoutineStore: injectedStore, defaults: defaults)
        let plan = try XCTUnwrap(store.plans.first { $0.id == definition.id })

        XCTAssertEqual(plan.title, "Planned by injected store")
        XCTAssertEqual(store.metadata(for: plan), CustomRoutineStore.metadata(for: definition))
    }

    func testDuplicateCreatesUnsavedLiteralCustomDefinitionWithNewID() throws {
        let (suiteName, defaults) = makeDefaults()
        defer { defaults.removePersistentDomain(forName: suiteName) }
        let store = AppStore(defaults: defaults)
        let source = try XCTUnwrap(store.plans.first)

        let duplicate = try store.duplicateRoutine(source)

        XCTAssertNotEqual(duplicate.id, source.id)
        XCTAssertTrue(duplicate.id.hasPrefix("custom."))
        XCTAssertNotNil(UUID(uuidString: String(duplicate.id.dropFirst("custom.".count))))
        XCTAssertEqual(duplicate.steps.flatMap(\.segments).count, duplicate.steps.count)
        let expectedMode: CustomRoutineTargetMode = if let boardID = source.boardID {
            .boardSpecific(boardID: boardID)
        } else {
            .generic
        }
        XCTAssertEqual(duplicate.targetMode, expectedMode)
        XCTAssertNil(store.customDefinition(for: duplicate.id))
    }

    func testPlanDetailDuplicateUsesCurrentPlanAfterStoredEdit() throws {
        let (suiteName, defaults) = makeDefaults()
        defer { defaults.removePersistentDomain(forName: suiteName) }
        let store = AppStore(defaults: defaults)
        let initialDefinition = makeRoutine()
        try store.saveCustomRoutine(initialDefinition)
        let stalePlan = try XCTUnwrap(store.plans.first { $0.id == initialDefinition.id })
        let updatedDefinition = CustomRoutineDefinition(
            id: initialDefinition.id,
            title: "Updated edge routine",
            subtitle: "Updated local routine",
            difficulty: "Advanced",
            category: "strength",
            tags: ["updated"],
            targetMode: initialDefinition.targetMode,
            steps: initialDefinition.steps + [WorkoutStepDefinition(
                id: "step-2",
                title: "Updated repeat",
                instruction: "Repeat the hang.",
                accessory: "8s",
                duration: 8,
                phase: .hang,
                targets: [.holdIDs(["edge-19-left"])],
                gripType: .halfCrimp,
                activeDuration: 8
            )]
        )
        try store.saveCustomRoutine(updatedDefinition)

        let duplicate = try PlanDetailView.duplicateDefinition(for: stalePlan, in: store)

        XCTAssertEqual(duplicate.title, "Updated edge routine")
        XCTAssertEqual(duplicate.subtitle, "Updated local routine")
        XCTAssertEqual(duplicate.difficulty, "Advanced")
        XCTAssertEqual(duplicate.category, "strength")
        XCTAssertEqual(duplicate.tags, ["updated"])
        XCTAssertEqual(duplicate.steps.map(\.id), ["step-1", "step-2"])
    }

    func testCorruptCustomIDsAreOmittedWithoutShadowingBuiltInsAndWarningIsRetained() throws {
        let (suiteName, defaults) = makeDefaults()
        defer { defaults.removePersistentDomain(forName: suiteName) }
        let builtIn = try XCTUnwrap(PlanCatalog.all.first)
        defaults.set(
            try JSONEncoder().encode(CustomRoutineLibrary(routines: [
                makeRoutine(id: builtIn.id),
                makeRoutine(id: "foreign.invalid")
            ])),
            forKey: CustomRoutineStore.defaultKey
        )
        let corruptStore = CustomRoutineStore(defaults: defaults)

        let store = AppStore(customRoutineStore: corruptStore, defaults: defaults)

        XCTAssertEqual(store.plans.filter { $0.id == builtIn.id }, [builtIn])
        XCTAssertNil(store.customDefinition(for: builtIn.id))
        XCTAssertNil(store.customDefinition(for: "foreign.invalid"))
        XCTAssertNotNil(store.customRoutinePersistenceError)
    }

    func testSaveAndDeleteRefreshCustomPlansAndDefinitionLookup() throws {
        let (suiteName, defaults) = makeDefaults()
        defer { defaults.removePersistentDomain(forName: suiteName) }
        let store = AppStore(defaults: defaults)
        let definition = makeRoutine()

        try store.saveCustomRoutine(definition)

        XCTAssertNil(store.customRoutinePersistenceError)
        let persisted = try XCTUnwrap(store.customDefinition(for: definition.id))
        XCTAssertTrue(store.isCustom(try XCTUnwrap(store.plans.first { $0.id == definition.id })))
        XCTAssertEqual(persisted.steps.map(\.id), ["step-1"])
        XCTAssertEqual(persisted.steps.map { $0.segments.count }, [1])
        XCTAssertEqual(store.customDefinition(for: definition.id), persisted)

        try store.deleteCustomRoutine(id: definition.id)

        XCTAssertFalse(store.plans.contains { $0.id == definition.id })
        XCTAssertNil(store.customDefinition(for: definition.id))
    }

    private final class InjectedRoutineStore: CustomRoutineStoring {
        let routines: [CustomRoutineDefinition]
        let persistenceError: String? = nil
        private let resolvedPlan: TrainingPlan

        init(definition: CustomRoutineDefinition) {
            routines = [definition]
            resolvedPlan = TrainingPlan(
                id: definition.id,
                title: "Planned by injected store",
                subtitle: "Resolved by test double",
                level: "Custom",
                sourceLabel: "Test",
                sourceURL: nil,
                provenance: .custom,
                boardID: BoardCatalog.compactII.id,
                steps: []
            )
        }

        func save(_ routine: CustomRoutineDefinition) throws {}

        func delete(id: String) throws {}

        func plan(for definition: CustomRoutineDefinition) throws -> TrainingPlan {
            resolvedPlan
        }
    }
}
