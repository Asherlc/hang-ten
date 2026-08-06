import XCTest
@testable import HangTen

@MainActor
final class CustomRoutineAppStoreTests: XCTestCase {
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

        XCTAssertTrue(store.isCustom(try XCTUnwrap(store.plans.first { $0.id == definition.id })))
        XCTAssertEqual(store.customDefinition(for: definition.id), definition)

        try store.deleteCustomRoutine(id: definition.id)

        XCTAssertFalse(store.plans.contains { $0.id == definition.id })
        XCTAssertNil(store.customDefinition(for: definition.id))
    }
}
