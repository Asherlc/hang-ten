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
            timing: .fixed
        )
        let stopwatch = CustomRoutineStepDraft(
            id: "stopwatch",
            title: "Hang",
            instruction: "",
            accessory: "",
            duration: 60,
            phase: .hang,
            targets: [.kind(.jug)],
            timing: .stopwatch
        )

        XCTAssertTrue(rest.isRest)
        XCTAssertFalse(rest.isStopwatch)
        XCTAssertNil(rest.activeDuration)
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
            .init(id: "one", title: "One", instruction: "", accessory: "", duration: 1, phase: .hang, targets: [.kind(.jug)], timing: .fixed),
            .init(id: "two", title: "Two", instruction: "", accessory: "", duration: 2, phase: .rest, targets: [], timing: .fixed),
            .init(id: "three", title: "Three", instruction: "", accessory: "", duration: 3, phase: .hang, targets: [.kind(.edge)], timing: .fixed)
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

    func testNewDraftKeepsItsGeneratedDefinitionIDAcrossRepeatedConversions() {
        let draft = CustomRoutineDraft(createWith: .generic)

        XCTAssertEqual(draft.definition().id, draft.definition().id)
    }

    func testRetargetedNewDraftKeepsItsGeneratedDefinitionID() {
        let draft = CustomRoutineDraft(createWith: .boardSpecific(boardID: BoardCatalog.compactII.id))

        XCTAssertEqual(draft.retargeted(to: .generic).definition().id, draft.definition().id)
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
                timing: .stopwatch
            ),
            .init(
                id: "rest",
                title: "Rest",
                instruction: "Recover.",
                accessory: "5s",
                duration: 5,
                phase: .rest,
                targets: [],
                timing: .fixed
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
                timing: .fixed
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

    func testRestDraftCanonicalizesTargetsGripAndTiming() {
        var draft = CustomRoutineDraft(createWith: .generic)
        draft.steps = [
            .init(
                id: "rest",
                title: "Rest",
                instruction: "Recover.",
                accessory: "15s",
                duration: 15,
                phase: .rest,
                targets: [.kind(.jug)],
                timing: .stopwatch
            )
        ]

        let step = draft.definition().steps[0]

        XCTAssertEqual(step.targets, [])
        XCTAssertNil(step.gripType)
        XCTAssertEqual(step.segments, [
            WorkoutSegmentDefinition(kind: .rest, targets: [], timing: .fixed, duration: 15)
        ])
    }

    func testMetadataOptionsUseAStableSecondaryOrderingForCaseVariants() {
        let metadata = [
            metadata(level: "alpha", category: "beta"),
            metadata(level: "Alpha", category: "Beta")
        ]

        let options = CustomRoutineMetadataOptions(metadata: metadata)

        XCTAssertEqual(options.difficulties, ["Alpha", "alpha", "Custom"])
        XCTAssertEqual(options.categories, ["Beta", "beta", "custom"])
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
                timing: .fixed
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
            .init(id: "kind", title: "Jugs", instruction: "", accessory: "", duration: 10, phase: .hang, targets: [.kind(.jug)], timing: .fixed),
            .init(id: "feature", title: "Edge", instruction: "", accessory: "", duration: 10, phase: .hang, targets: [.feature(.mediumEdge, fallbacks: [])], timing: .fixed)
        ]

        XCTAssertEqual(draft.definition().steps.map(\.targets), [[.kind(.jug)], [.feature(.mediumEdge, fallbacks: [])]])
    }

    func testEditingDraftOmitsLegacyGripAndFingerCueFieldsFromDefinition() {
        let source = CustomRoutineDefinition(
            id: "custom.legacy-cues",
            title: "Legacy cues",
            subtitle: "",
            difficulty: nil,
            category: nil,
            tags: [],
            targetMode: .generic,
            steps: [WorkoutStepDefinition(
                id: "legacy-step",
                title: "Legacy step",
                instruction: "Hang.",
                accessory: "10s",
                duration: 10,
                phase: .hang,
                targets: [.kind(.jug)],
                gripType: .openHand,
                fingerConfiguration: FingerConfiguration(
                    engagedFingers: [.index, .ring]
                ),
                activeDuration: 10
            )]
        )

        let definition = CustomRoutineDraft(editing: source).definition()

        XCTAssertNil(definition.steps[0].gripType)
        XCTAssertNil(definition.steps[0].fingerConfiguration)
    }

    func testEditingDraftRoundTripsNormalizedOneSegmentDefinition() {
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
                gripType: .halfCrimp,
                fingerConfiguration: FingerConfiguration(
                    engagedFingers: [.index, .ring]
                )
            )]
        )

        let definition = CustomRoutineDraft(editing: source).definition()

        XCTAssertEqual(definition.id, source.id)
        XCTAssertEqual(definition.title, source.title)
        XCTAssertEqual(definition.subtitle, source.subtitle)
        XCTAssertEqual(definition.difficulty, source.difficulty)
        XCTAssertEqual(definition.category, source.category)
        XCTAssertEqual(definition.tags, source.tags)
        XCTAssertEqual(definition.targetMode, source.targetMode)
        XCTAssertEqual(definition.steps[0].id, source.steps[0].id)
        XCTAssertEqual(definition.steps[0].title, source.steps[0].title)
        XCTAssertEqual(definition.steps[0].instruction, source.steps[0].instruction)
        XCTAssertEqual(definition.steps[0].accessory, source.steps[0].accessory)
        XCTAssertEqual(definition.steps[0].duration, source.steps[0].duration)
        XCTAssertEqual(definition.steps[0].phase, source.steps[0].phase)
        XCTAssertEqual(definition.steps[0].targets, source.steps[0].targets)
        XCTAssertEqual(definition.steps[0].segments, source.steps[0].segments)
        XCTAssertEqual(definition.steps[0].activeDuration, source.steps[0].activeDuration)
        XCTAssertNil(definition.steps[0].gripType)
        XCTAssertNil(definition.steps[0].fingerConfiguration)
    }

    func testDuplicateDraftCreatesOneStableFreshCustomDefinition() {
        let source = CustomRoutineDefinition(
            id: "custom.source",
            title: "Source",
            subtitle: "Description",
            difficulty: "Hard",
            category: "Strength",
            tags: ["edge", "power"],
            targetMode: .generic,
            steps: [WorkoutStepDefinition(
                id: "source-step",
                title: "Source step",
                instruction: "Hang.",
                accessory: "10s",
                duration: 10,
                phase: .hang,
                targets: [.kind(.jug)],
                gripType: .openHand,
                fingerConfiguration: FingerConfiguration(
                    engagedFingers: [.pinky]
                ),
                activeDuration: 10
            )]
        )

        let duplicate = CustomRoutineDraft(duplicate: source)

        XCTAssertNil(duplicate.id)
        XCTAssertNotEqual(duplicate.definition().id, source.id)
        XCTAssertTrue(duplicate.definition().id.hasPrefix("custom."))
        XCTAssertEqual(duplicate.definition(), duplicate.definition())
        XCTAssertEqual(duplicate.definition().title, source.title)

        let sourceStep = source.steps[0]
        let expectedStep = WorkoutStepDefinition(
            id: sourceStep.id,
            title: sourceStep.title,
            instruction: sourceStep.instruction,
            accessory: sourceStep.accessory,
            duration: sourceStep.duration,
            phase: sourceStep.phase,
            targets: sourceStep.targets,
            segments: [WorkoutSegmentDefinition(
                kind: .work,
                target: .kind(.jug),
                timing: .fixed,
                duration: 10
            )],
            activeDuration: 10
        )
        XCTAssertEqual(duplicate.definition().steps, [expectedStep])
    }

    func testEditingRestStepClearsPostureAndExactFingerConfiguration() {
        let source = CustomRoutineDefinition(
            id: "custom.rest",
            title: "Rest test",
            subtitle: "",
            difficulty: nil,
            category: nil,
            tags: [],
            targetMode: .generic,
            steps: [WorkoutStepDefinition(
                id: "rest-step",
                title: "Rest",
                instruction: "Recover.",
                accessory: "10s",
                duration: 10,
                phase: .rest,
                targets: [.kind(.jug)],
                gripType: .fullCrimp,
                fingerConfiguration: FingerConfiguration(
                    engagedFingers: [.middle, .pinky]
                )
            )]
        )

        let step = CustomRoutineDraft(editing: source).definition().steps[0]

        XCTAssertNil(step.gripType)
        XCTAssertNil(step.fingerConfiguration)
    }

    func testEditingDraftRetainsPersistedIdentityAndCannotBeRetargeted() {
        let source = CustomRoutineDefinition(
            id: "custom.saved",
            title: "Saved",
            subtitle: "Description",
            difficulty: nil,
            category: nil,
            tags: [],
            targetMode: .boardSpecific(boardID: BoardCatalog.compactII.id),
            steps: [WorkoutStepDefinition(
                id: "saved-step",
                title: "Saved step",
                instruction: "Hang.",
                accessory: "10s",
                duration: 10,
                phase: .hang,
                targets: [.holdIDs(["edge-19-left"])],
                gripType: .openHand,
                activeDuration: 10
            )]
        )

        let editing = CustomRoutineDraft(editing: source)

        XCTAssertEqual(editing.id, source.id)
        XCTAssertEqual(editing.definition().id, source.id)
        XCTAssertEqual(editing.retargeted(to: .generic), editing)
    }

    func testEditorLocalValidationRejectsNonFiniteAndNonPositiveStepDurations() {
        var draft = CustomRoutineDraft(createWith: .generic)
        draft.title = "Duration validation"
        draft.steps = [
            makeStep(id: "zero", title: "Zero", duration: 0),
            makeStep(id: "negative", title: "Negative", duration: -1),
            makeStep(id: "infinite", title: "Infinite", duration: .infinity)
        ]

        XCTAssertEqual(
            CustomRoutineEditorView.localValidationIssues(for: draft.definition()),
            [
                "Step 1 needs a positive duration.",
                "Step 2 needs a positive duration.",
                "Step 3 needs a positive duration."
            ]
        )
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

        XCTAssertEqual(CustomRoutineDraft(editing: source).definition(), source)
    }

    private func makeStep(
        id: String,
        title: String,
        duration: TimeInterval = 10
    ) -> CustomRoutineStepDraft {
        CustomRoutineStepDraft(
            id: id,
            title: title,
            instruction: "Instruction",
            accessory: "Accessory",
            duration: duration,
            phase: .hang,
            targets: [.kind(.jug)],
            timing: .fixed
        )
    }

    private func metadata(level: String, category: String) -> PlanMetadata {
        PlanMetadata(
            title: "Test",
            subtitle: "",
            level: level,
            sourceLabel: "Test",
            sourceURL: nil,
            provenance: .custom,
            category: category
        )
    }
}
