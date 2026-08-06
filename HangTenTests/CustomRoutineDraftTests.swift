import XCTest
@testable import HangTen

final class CustomRoutineDraftTests: XCTestCase {
    func testNewDraftStartsEmptyAndAddStepAddsOneStableEditableRow() {
        var draft = CustomRoutineDraft(createWith: .generic)

        XCTAssertTrue(draft.steps.isEmpty)

        draft.addStep()

        XCTAssertEqual(draft.steps.count, 1)
        XCTAssertFalse(draft.steps[0].id.isEmpty)
        XCTAssertEqual(draft.steps[0], draft.steps[0])
    }

    func testStepDerivedFlagsFollowPhaseAndTiming() {
        let rest = CustomRoutineStepDraft(
            id: "rest",
            title: "Rest",
            instruction: "",
            accessory: "",
            duration: 10,
            phase: .rest,
            targets: [],
            timing: .fixed,
            gripType: nil
        )
        let stopwatch = CustomRoutineStepDraft(
            id: "stopwatch",
            title: "Hang",
            instruction: "",
            accessory: "",
            duration: 60,
            phase: .hang,
            targets: [.kind(.jug)],
            timing: .stopwatch,
            gripType: nil
        )

        XCTAssertTrue(rest.isRest)
        XCTAssertFalse(rest.isStopwatch)
        XCTAssertFalse(stopwatch.isRest)
        XCTAssertTrue(stopwatch.isStopwatch)
    }

    func testUpdateStepReplacesOnlyTheMatchingID() {
        var draft = CustomRoutineDraft(createWith: .generic)
        let original = makeStep(id: "one", title: "One")
        draft.steps = [original, makeStep(id: "two", title: "Two")]

        draft.updateStep(makeStep(id: "one", title: "Updated"))

        XCTAssertEqual(draft.steps.map(\.title), ["Updated", "Two"])
        XCTAssertEqual(draft.steps[0].id, original.id)
    }

    func testRemoveStepsRemovesExactlyTheSelectedRows() {
        var draft = CustomRoutineDraft(createWith: .generic)
        draft.steps = [
            makeStep(id: "one", title: "One"),
            makeStep(id: "two", title: "Two"),
            makeStep(id: "three", title: "Three"),
            makeStep(id: "four", title: "Four")
        ]

        draft.removeSteps(at: IndexSet([1, 3]))

        XCTAssertEqual(draft.steps.map(\.id), ["one", "three"])
    }

    func testMoveStepsChangesOnlyTheirOrder() {
        var draft = CustomRoutineDraft(createWith: .generic)
        draft.steps = [
            .init(id: "one", title: "One", instruction: "", accessory: "", duration: 1, phase: .hang, targets: [.kind(.jug)], timing: .fixed, gripType: nil),
            .init(id: "two", title: "Two", instruction: "", accessory: "", duration: 2, phase: .rest, targets: [], timing: .fixed, gripType: nil),
            .init(id: "three", title: "Three", instruction: "", accessory: "", duration: 3, phase: .hang, targets: [.kind(.edge)], timing: .fixed, gripType: nil)
        ]

        draft.moveSteps(from: IndexSet(integer: 0), to: 3)

        XCTAssertEqual(draft.steps.map(\.id), ["two", "three", "one"])
    }

    func testMoveStepsPreservesSelectedOrderWhenMovingMultipleRows() {
        var draft = CustomRoutineDraft(createWith: .generic)
        draft.steps = [
            makeStep(id: "one", title: "One"),
            makeStep(id: "two", title: "Two"),
            makeStep(id: "three", title: "Three"),
            makeStep(id: "four", title: "Four")
        ]

        draft.moveSteps(from: IndexSet([1, 3]), to: 0)

        XCTAssertEqual(draft.steps.map(\.id), ["two", "four", "one", "three"])
    }

    func testDefinitionNormalizesTagsAndKeepsTargetModeFixed() {
        var draft = CustomRoutineDraft(createWith: .generic)
        draft.title = "  My routine  "
        draft.subtitle = "  Description "
        draft.tagsText = " strength, , strength, POWER, power "

        let definition = draft.definition()

        XCTAssertEqual(definition.title, "My routine")
        XCTAssertEqual(definition.subtitle, "Description")
        XCTAssertEqual(definition.tags, ["strength", "POWER"])
        XCTAssertEqual(definition.targetMode, .generic)
    }

    func testNewDraftDefinitionUsesCustomUUIDNamespace() throws {
        let definition = CustomRoutineDraft(createWith: .generic).definition()
        let uuidText = try XCTUnwrap(definition.id.split(separator: ".").last.map(String.init))

        XCTAssertTrue(definition.id.hasPrefix("custom."))
        XCTAssertNotNil(UUID(uuidString: uuidText))
    }

    func testRetargetingNewDraftPreservesRowsAndMetadataWhileClearingOnlyIncompatibleTargets() {
        var draft = CustomRoutineDraft(createWith: .boardSpecific(boardID: BoardCatalog.compactII.id))
        draft.title = "Retarget me"
        draft.subtitle = "Keep this description"
        draft.difficulty = "Advanced"
        draft.category = "manufacturer"
        draft.tagsText = "power, edges"
        draft.steps = [
            .init(
                id: "hang",
                title: "Exact hang",
                instruction: "Keep the row.",
                accessory: "10s",
                duration: 10,
                phase: .hang,
                targets: [.holdIDs(["edge-19-left"])],
                timing: .stopwatch,
                gripType: .halfCrimp
            ),
            .init(
                id: "rest",
                title: "Rest",
                instruction: "Recover.",
                accessory: "5s",
                duration: 5,
                phase: .rest,
                targets: [],
                timing: .fixed,
                gripType: nil
            )
        ]

        let retargeted = draft.retargeted(to: .generic)

        XCTAssertEqual(retargeted.targetMode, .generic)
        XCTAssertEqual(retargeted.title, draft.title)
        XCTAssertEqual(retargeted.subtitle, draft.subtitle)
        XCTAssertEqual(retargeted.difficulty, draft.difficulty)
        XCTAssertEqual(retargeted.category, draft.category)
        XCTAssertEqual(retargeted.tagsText, draft.tagsText)
        XCTAssertEqual(retargeted.steps.map(\.id), ["hang", "rest"])
        XCTAssertEqual(retargeted.steps.map(\.title), ["Exact hang", "Rest"])
        XCTAssertEqual(retargeted.steps.map(\.timing), [.stopwatch, .fixed])
        XCTAssertEqual(retargeted.steps.map(\.targets), [[], []])
        XCTAssertEqual(retargeted.steps[0].gripType, .halfCrimp)
    }

    func testRetargetingBoardKeepsOnlyExactHoldsAvailableOnTheNewBoard() throws {
        let retainedHold = try XCTUnwrap(BoardCatalog.compactII.holds.first)
        let replacementBoard = TrainingBoard(
            id: "replacement-board",
            manufacturer: "Test",
            name: "Replacement",
            subtitle: "Test board",
            dimensions: "1 × 1",
            aspectRatio: 1,
            holds: [retainedHold],
            productURL: try XCTUnwrap(URL(string: "https://example.com/board")),
            photoAssetName: nil
        )
        var draft = CustomRoutineDraft(createWith: .boardSpecific(boardID: BoardCatalog.compactII.id))
        draft.steps = [
            .init(
                id: "hang",
                title: "Hang",
                instruction: "",
                accessory: "",
                duration: 10,
                phase: .hang,
                targets: [.holdIDs([retainedHold.id, "not-on-new-board"])],
                timing: .fixed,
                gripType: nil
            )
        ]

        let retargeted = draft.retargeted(
            to: .boardSpecific(boardID: replacementBoard.id),
            availableBoards: [replacementBoard]
        )

        XCTAssertEqual(retargeted.steps[0].targets, [.holdIDs([retainedHold.id])])
    }

    func testEditorMetadataOptionsUseBuiltInVocabulariesAndCustomDefaults() {
        let builtInMetadata = PlanCatalog.all.compactMap { PlanCatalog.metadata(for: $0.id) }
        let options = CustomRoutineMetadataOptions()

        XCTAssertTrue(Set(builtInMetadata.map(\.level)).isSubset(of: Set(options.difficulties)))
        XCTAssertTrue(Set(builtInMetadata.map(\.category)).isSubset(of: Set(options.categories)))
        XCTAssertTrue(options.difficulties.contains("Custom"))
        XCTAssertTrue(options.categories.contains("custom"))
    }

    func testDefinitionEmitsOneSegmentWithFixedTimingAndCurrentOrder() {
        var draft = CustomRoutineDraft(createWith: .boardSpecific(boardID: "board"))
        draft.steps = [makeStep(id: "one", title: "One")]

        let definition = draft.definition()

        XCTAssertEqual(definition.targetMode, .boardSpecific(boardID: "board"))
        XCTAssertEqual(definition.steps.map(\.id), ["one"])
        XCTAssertEqual(definition.steps[0].segments.count, 1)
        XCTAssertEqual(definition.steps[0].segments[0].kind, .work)
        XCTAssertEqual(definition.steps[0].segments[0].timing, .fixed)
        XCTAssertEqual(definition.steps[0].segments[0].duration, 10)
    }

    func testBoardSpecificDraftStoresExactSelectedHoldIDs() {
        var draft = CustomRoutineDraft(createWith: .boardSpecific(boardID: BoardCatalog.compactII.id))
        draft.steps = [
            .init(
                id: "hang",
                title: "Edge hang",
                instruction: "Hang.",
                accessory: "10s",
                duration: 10,
                phase: .hang,
                targets: [.holdIDs(["edge-19-left", "edge-19-right"])],
                timing: .fixed,
                gripType: .halfCrimp
            )
        ]

        let definition = draft.definition()

        XCTAssertEqual(
            definition.targetMode,
            .boardSpecific(boardID: BoardCatalog.compactII.id)
        )
        XCTAssertEqual(definition.steps[0].targets, [.holdIDs(["edge-19-left", "edge-19-right"])])
    }

    func testGenericDraftCanStoreKindAndFeatureTargets() {
        var draft = CustomRoutineDraft(createWith: .generic)
        draft.steps = [
            .init(id: "kind", title: "Jugs", instruction: "", accessory: "", duration: 10, phase: .hang, targets: [.kind(.jug)], timing: .fixed, gripType: .openHand),
            .init(id: "feature", title: "Edge", instruction: "", accessory: "", duration: 10, phase: .hang, targets: [.feature(.mediumEdge, fallbacks: [])], timing: .fixed, gripType: nil)
        ]

        XCTAssertEqual(draft.definition().steps.map(\.targets), [[.kind(.jug)], [.feature(.mediumEdge, fallbacks: [])]])
    }

    func testDuplicateDraftRoundTripsNormalizedOneSegmentDefinition() {
        let source = CustomRoutineDefinition(
            id: "custom.fixed",
            title: "Fixed",
            subtitle: "Description",
            difficulty: "Hard",
            category: "Strength",
            tags: ["edge", "power"],
            targetMode: .boardSpecific(boardID: "board"),
            steps: [WorkoutStepDefinition(
                id: "fixed-step",
                title: "Edge hang",
                instruction: "Hang.",
                accessory: "10s",
                duration: 10,
                phase: .hang,
                targets: [.holdIDs(["edge-left", "edge-right"])],
                segments: [WorkoutSegmentDefinition(
                    kind: .work,
                    target: .holdIDs(["edge-left", "edge-right"]),
                    timing: .fixed,
                    duration: 10
                )],
                gripType: .halfCrimp
            )]
        )

        XCTAssertEqual(CustomRoutineDraft(duplicate: source).definition(), source)
    }

    func testDuplicateDraftPreservesStopwatchAsOneSimpleStep() throws {
        let source = CustomRoutineDefinition(
            id: "custom.max",
            title: "Max",
            subtitle: "",
            difficulty: nil,
            category: nil,
            tags: [],
            targetMode: .generic,
            steps: [WorkoutStepDefinition(
                id: "max-step",
                title: "Max hang",
                instruction: "Hang.",
                accessory: "Up to 60s",
                duration: 60,
                phase: .hang,
                targets: [.feature(.roundSloper, fallbacks: [])],
                segments: [WorkoutSegmentDefinition(
                    kind: .work,
                    target: .feature(.roundSloper, fallbacks: []),
                    timing: .stopwatch,
                    duration: nil
                )]
            )]
        )

        let draft = CustomRoutineDraft(duplicate: source)
        let definition = draft.definition()

        XCTAssertEqual(definition.steps.count, 1)
        XCTAssertEqual(definition.steps[0].segments.count, 1)
        XCTAssertEqual(definition.steps[0].segments[0].timing, .stopwatch)
        XCTAssertNil(definition.steps[0].segments[0].duration)
    }

    func testDuplicateDraftPreservesUndefinedTimingWithoutSegmentDuration() {
        let source = CustomRoutineDefinition(
            id: "custom.undefined",
            title: "Undefined",
            subtitle: "",
            difficulty: nil,
            category: nil,
            tags: [],
            targetMode: .generic,
            steps: [WorkoutStepDefinition(
                id: "undefined-step",
                title: "Repeat",
                instruction: "",
                accessory: "",
                duration: 60,
                phase: .hang,
                targets: [.kind(.jug)],
                segments: [WorkoutSegmentDefinition(
                    kind: .work,
                    target: .kind(.jug),
                    timing: .undefined,
                    duration: nil
                )]
            )]
        )

        XCTAssertEqual(CustomRoutineDraft(duplicate: source).definition(), source)
    }

    private func makeStep(id: String, title: String) -> CustomRoutineStepDraft {
        CustomRoutineStepDraft(
            id: id,
            title: title,
            instruction: "Instruction",
            accessory: "Accessory",
            duration: 10,
            phase: .hang,
            targets: [.kind(.jug)],
            timing: .fixed,
            gripType: .openHand
        )
    }
}
