import XCTest
@testable import HangTen

final class CustomRoutineDraftTests: XCTestCase {
    func testEitherHandBoardPreviewAllowsRemovingItsSelectedAlternative() {
        let board = mirroredBoard()
        var step = CustomRoutineStepDraft(
            id: "either", title: "Either", instruction: "", accessory: "", duration: 10,
            phase: .hang, targets: [.kind(.edge, selection: .single)], timing: .fixed,
            handUse: .either, side: .both
        )

        XCTAssertEqual(
            CustomRoutineBoardPreview.contactIDs(for: step, on: board),
            Set(["left", "right"])
        )

        CustomRoutineBoardPreview.toggle(
            board.contacts[0], in: &step, on: board
        )

        XCTAssertTrue(step.targets.isEmpty)
        XCTAssertEqual(
            CustomRoutineBoardPreview.contactIDs(for: step, on: board),
            []
        )
    }

    func testDoubleHandPreviewOnOneHandedBoardResolvesBothModeSingleHold() {
        let board = oneHandedBoard()
        let step = CustomRoutineStepDraft(
            id: "double", title: "Double", instruction: "", accessory: "", duration: 10,
            phase: .hang,
            targets: [ContactRequirement.kind(.jug, selection: .bilateralPair)],
            timing: .fixed,
            handUse: .double,
            side: .both
        )

        XCTAssertEqual(
            CustomRoutineBoardPreview.contactIDs(for: step, on: board),
            Set(["jug"]),
            "Both-mode single-hold materialization must preview the resolvable contact"
        )
    }

    func testEitherHandBoardPreviewKeepsAndRemovesItsResolvedAlternative() throws {
        let board = mirroredBoard()
        var step = CustomRoutineStepDraft(
            id: "either", title: "Either", instruction: "", accessory: "", duration: 10,
            phase: .hang, targets: [], timing: .fixed,
            handUse: .either, side: .both
        )

        CustomRoutineBoardPreview.toggle(board.contacts[1], in: &step, on: board)

        XCTAssertNil(step.targets.first?.contactID)
        XCTAssertEqual(
            CustomRoutineBoardPreview.contactIDs(for: step, on: board),
            Set(["left", "right"])
        )
        var draft = CustomRoutineDraft(createWith: .boardSpecific(boardID: board.id))
        draft.steps = [step]
        let persisted = try JSONDecoder().decode(
            CustomRoutineDefinition.self,
            from: JSONEncoder().encode(draft.definition())
        )
        XCTAssertNil(persisted.steps[0].workRequirements.first?.contactID)

        CustomRoutineBoardPreview.toggle(board.contacts[0], in: &step, on: board)

        XCTAssertTrue(step.targets.isEmpty)
        XCTAssertEqual(
            CustomRoutineBoardPreview.contactIDs(for: step, on: board),
            []
        )
    }

    func testSingleHandBoardPreviewPersistsItsExactSelectedContactID() {
        let board = mirroredBoard()
        var step = CustomRoutineStepDraft(
            id: "left", title: "Left", instruction: "", accessory: "", duration: 10,
            phase: .hang, targets: [], timing: .fixed, handUse: .single, side: .left
        )

        CustomRoutineBoardPreview.toggle(board.contacts[0], in: &step, on: board)

        XCTAssertEqual(step.targets.first?.contactID, "left")
        XCTAssertEqual(CustomRoutineBoardPreview.contactIDs(for: step, on: board), ["left"])
        var draft = CustomRoutineDraft(createWith: .boardSpecific(boardID: board.id))
        draft.steps = [step]
        XCTAssertEqual(draft.definition().steps.first?.workRequirements.first?.contactID, "left")
    }

    func testChangingSingleHandToEitherClearsExactContactAndResolvesBothHands() {
        let board = mirroredBoard()
        var step = CustomRoutineStepDraft(
            id: "single-to-either", title: "Either", instruction: "", accessory: "", duration: 10,
            phase: .hang,
            targets: [factualRequirement(contactID: "left", selection: .single)],
            timing: .fixed, handUse: .single, side: .left
        )

        step.transitionHandUse(to: .either)

        XCTAssertEqual(step.handUse, .either)
        XCTAssertEqual(step.side, .both)
        XCTAssertEqual(step.targets, [factualRequirement(contactID: nil, selection: .single)])
        XCTAssertEqual(
            CustomRoutineBoardPreview.contactIDs(for: step, on: board),
            Set(["left", "right"])
        )
    }

    func testChangingSingleHandToDoubleUsesBilateralPairAndPreservesRequirementFacts() {
        let board = mirroredBoard()
        var step = CustomRoutineStepDraft(
            id: "single-to-double", title: "Both", instruction: "", accessory: "", duration: 10,
            phase: .hang,
            targets: [factualRequirement(contactID: "left", selection: .single)],
            timing: .fixed, handUse: .single, side: .left
        )

        step.transitionHandUse(to: .double)

        XCTAssertEqual(step.handUse, .double)
        XCTAssertEqual(step.side, .both)
        XCTAssertEqual(step.targets, [factualRequirement(contactID: nil, selection: .bilateralPair)])
        XCTAssertEqual(
            CustomRoutineBoardPreview.contactIDs(for: step, on: board),
            Set(["left", "right"])
        )
    }

    func testChangingEitherHandWithStaleExactTargetToDoubleUsesBilateralPair() {
        let board = mirroredBoard()
        var step = CustomRoutineStepDraft(
            id: "either-to-double", title: "Both", instruction: "", accessory: "", duration: 10,
            phase: .hang,
            targets: [factualRequirement(contactID: "left", selection: .single)],
            timing: .fixed, handUse: .either, side: .both
        )

        // Older drafts can contain an exact ID because the editor previously
        // retained it when changing from single hand to either hand.
        step.transitionHandUse(to: .double)

        XCTAssertEqual(step.handUse, .double)
        XCTAssertEqual(step.side, .both)
        XCTAssertEqual(step.targets, [factualRequirement(contactID: nil, selection: .bilateralPair)])
        XCTAssertEqual(
            CustomRoutineBoardPreview.contactIDs(for: step, on: board),
            Set(["left", "right"])
        )
    }

    func testDoubleHandPreviewOnOneHandedBoardResolvesThroughCandidateTargets() {
        let board = oneHandedBoard()
        let step = CustomRoutineStepDraft(
            id: "double", title: "Both", instruction: "", accessory: "", duration: 10,
            phase: .hang,
            targets: [ContactRequirement(kind: .jug, selection: .bilateralPair)],
            timing: .fixed,
            handUse: .double,
            side: .both
        )

        XCTAssertEqual(
            CustomRoutineBoardPreview.contactIDs(for: step, on: board),
            Set(["jug"])
        )
    }

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
        let draft = CustomRoutineDraft(createWith: .boardSpecific(boardID: BoardCatalog.defaultBoard.id))

        XCTAssertEqual(draft.retargeted(to: .generic).definition().id, draft.definition().id)
    }

    func testRetargetingNewDraftPreservesRowsAndMetadataWhileClearingOnlyIncompatibleTargets() {
        var draft = CustomRoutineDraft(createWith: .boardSpecific(boardID: BoardCatalog.defaultBoard.id))
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
                targets: [.kind(.edge)],
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
        XCTAssertEqual(retargeted.steps.map(\.targets), [[.kind(.edge)], []])
    }

    func testRetargetingBoardSpecificRightHoldToGenericStripsExactContactID() throws {
        let board = BoardRevision(
            id: "mirrored", revisionID: "test", manufacturer: "Fixture", name: "Mirrored",
            subtitle: "", dimensions: "", aspectRatio: 1,
            contacts: [
                PhysicalContact(id: "left", name: "Left edge", kind: .edge, side: .left, pairedContactID: "right"),
                PhysicalContact(id: "right", name: "Right edge", kind: .edge, side: .right, pairedContactID: "left")
            ],
            productURL: try XCTUnwrap(URL(string: "https://example.com/mirrored")), photoAssetName: nil
        )
        var step = CustomRoutineStepDraft(
            id: "hang", title: "Right edge", instruction: "", accessory: "", duration: 10,
            phase: .hang, targets: [], timing: .fixed, handUse: .single, side: .right
        )
        CustomRoutineBoardPreview.toggle(board.contacts[1], in: &step, on: board)
        var draft = CustomRoutineDraft(createWith: .boardSpecific(boardID: board.id))
        draft.steps = [step]

        let savedGenericDefinition = try JSONDecoder().decode(
            CustomRoutineDefinition.self,
            from: JSONEncoder().encode(draft.retargeted(to: .generic).definition())
        )

        let target = try XCTUnwrap(savedGenericDefinition.steps.first?.workRequirements.first)
        XCTAssertEqual(savedGenericDefinition.targetMode, .generic)
        XCTAssertNil(target.contactID)
        XCTAssertEqual(target.kind, .edge)
        XCTAssertEqual(target.selection, .single)
    }

    func testRetargetingBoardSpecificDraftToAnotherBoardStripsExactContactID() {
        var draft = CustomRoutineDraft(createWith: .boardSpecific(boardID: "first-board"))
        draft.steps = [
            .init(
                id: "hang", title: "Exact edge", instruction: "", accessory: "", duration: 10,
                phase: .hang,
                targets: [ContactRequirement(contactID: "first-board-edge", kind: .edge, selection: .single)],
                timing: .fixed, handUse: .single, side: .right
            )
        ]
        let replacementBoard = BoardRevision(
            id: "second-board", revisionID: "test", manufacturer: "Fixture", name: "Second",
            subtitle: "", dimensions: "", aspectRatio: 1,
            contacts: [PhysicalContact(id: "second-board-edge", name: "Edge", kind: .edge)],
            productURL: URL(string: "https://example.com/second")!, photoAssetName: nil
        )

        let retargeted = draft.retargeted(
            to: .boardSpecific(boardID: replacementBoard.id),
            availableBoards: [replacementBoard]
        )

        XCTAssertNil(retargeted.steps[0].targets[0].contactID)
        XCTAssertEqual(retargeted.steps[0].targets[0].kind, .edge)
    }

    func testRetargetingBoardKeepsOnlyExactHoldsAvailableOnTheNewBoard() throws {
        let retainedHold = try XCTUnwrap(BoardCatalog.defaultBoard.contacts.first)
        let replacementBoard = BoardRevision(
            id: "replacement-board",
            revisionID: "test-fixture",
            manufacturer: "Test",
            name: "Replacement",
            subtitle: "Test board",
            dimensions: "1 × 1",
            aspectRatio: 1,
            contacts: [retainedHold],
            productURL: try XCTUnwrap(URL(string: "https://example.com/board")),
            photoAssetName: nil
        )
        var draft = CustomRoutineDraft(createWith: .boardSpecific(boardID: BoardCatalog.defaultBoard.id))
        draft.steps = [
            .init(
                id: "hang",
                title: "Hang",
                instruction: "",
                accessory: "",
                duration: 10,
                phase: .hang,
                targets: [.kind(.edge)],
                timing: .fixed
            )
        ]

        let retargeted = draft.retargeted(
            to: .boardSpecific(boardID: replacementBoard.id),
            availableBoards: [replacementBoard]
        )

        XCTAssertEqual(retargeted.steps[0].targets, [.kind(.edge)])
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
                timing: .stopwatch,
                handUse: .single,
                side: .right,
                action: .loadedLift,
                repetitions: 7,
                externalLoadKGF: 12
            )
        ]

        let step = draft.definition().steps[0]

        XCTAssertEqual(step.workRequirements, [])
        XCTAssertNil(step.gripType)
        XCTAssertEqual(step.handUse, .double)
        XCTAssertEqual(step.side, .both)
        XCTAssertEqual(step.action, .hang)
        XCTAssertNil(step.repetitions)
        XCTAssertNil(step.externalLoadKGF)
        XCTAssertEqual(step.segments, [
            WorkoutSegmentDefinition(kind: .rest, target: nil, timing: .fixed, duration: 15)
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
        var draft = CustomRoutineDraft(createWith: .boardSpecific(boardID: BoardCatalog.defaultBoard.id))
        draft.steps = [
            .init(
                id: "hang",
                title: "Edge hang",
                instruction: "Hang.",
                accessory: "10s",
                duration: 10,
                phase: .hang,
                targets: [.kind(.edge)],
                timing: .fixed
            )
        ]

        let definition = draft.definition()

        XCTAssertEqual(
            definition.targetMode,
            .boardSpecific(boardID: BoardCatalog.defaultBoard.id)
        )
        XCTAssertEqual(definition.steps[0].workRequirements, [.kind(.edge)])
    }

    func testGenericDraftCanStoreKindAndFeatureTargets() {
        var draft = CustomRoutineDraft(createWith: .generic)
        draft.steps = [
            .init(id: "kind", title: "Jugs", instruction: "", accessory: "", duration: 10, phase: .hang, targets: [.kind(.jug)], timing: .fixed),
            .init(id: "feature", title: "Edge", instruction: "", accessory: "", duration: 10, phase: .hang, targets: [.edge(depth: .category(.medium))], timing: .fixed)
        ]

        XCTAssertEqual(draft.definition().steps.map(\.workRequirements), [[.kind(.jug)], [.edge(depth: .category(.medium))]])
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
                segments: [WorkoutSegmentDefinition(
                    kind: .work,
                    target: .fromLegacyTargets([.kind(.edge)]),
                    timing: .fixed,
                    duration: 10
                )],
                gripType: .halfCrimp,
                fingerConfiguration: FingerConfiguration(
                    engagedFingers: [.index, .ring]
                ),
                activeDuration: 10
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
        XCTAssertEqual(definition.steps[0].workRequirements, source.steps[0].workRequirements)
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
                segments: [
                    WorkoutSegmentDefinition(
                        kind: .work,
                        target: .fromLegacyTargets([.kind(.jug)]),
                        timing: .fixed,
                        duration: 10
                    )
                ],
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
            segments: [WorkoutSegmentDefinition(
                kind: .work,
                target: .fromLegacyTargets([.kind(.jug)]),
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
            targetMode: .boardSpecific(boardID: BoardCatalog.defaultBoard.id),
            steps: [WorkoutStepDefinition(
                id: "saved-step",
                title: "Saved step",
                instruction: "Hang.",
                accessory: "10s",
                duration: 10,
                phase: .hang,
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
                segments: [WorkoutSegmentDefinition(
                    kind: .work,
                    target: .fromLegacyTargets([ContactRequirement(kind: .sloper, shape: .round)]),
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
                segments: [WorkoutSegmentDefinition(
                    kind: .work,
                    target: .fromLegacyTargets([.kind(.jug)]),
                    timing: .undefined,
                    duration: nil
                )]
            )]
        )

        XCTAssertEqual(CustomRoutineDraft(editing: source).definition(), source)
    }

    func testEditingDraftPreservesUnilateralStepSemantics() {
        let source = CustomRoutineDefinition(
            id: "custom.unilateral",
            title: "Unilateral",
            subtitle: "",
            difficulty: nil,
            category: nil,
            tags: [],
            targetMode: .generic,
            steps: [WorkoutStepDefinition(
                id: "left-pull",
                title: "Left pull",
                instruction: "Pull.",
                accessory: "",
                duration: 10,
                phase: .pull,
                handUse: .single,
                side: .left,
                action: .isometricPull,
                externalLoadKGF: -4
            )]
        )

        let definition = CustomRoutineDraft(editing: source).definition()

        XCTAssertEqual(definition.steps[0].handUse, .single)
        XCTAssertEqual(definition.steps[0].side, .left)
        XCTAssertEqual(definition.steps[0].action, .isometricPull)
        XCTAssertNil(definition.steps[0].repetitions)
        XCTAssertEqual(definition.steps[0].externalLoadKGF, -4)
    }

    func testAddLeftAndRightPairDuplicatesCompatibleStepValues() {
        var draft = CustomRoutineDraft(createWith: .generic)
        let source = CustomRoutineStepDraft(
            id: "lift",
            title: "Loaded lift",
            instruction: "Lift.",
            accessory: "",
            duration: 30,
            phase: .pull,
            targets: [.kind(.jug)],
            timing: .fixed,
            handUse: .single,
            side: .left,
            action: .loadedLift,
            repetitions: 4,
            externalLoadKGF: -5
        )

        draft.addLeftAndRightPair(from: source)

        XCTAssertEqual(draft.steps.map(\.side), [.left, .right])
        XCTAssertEqual(draft.steps.map(\.handUse), [.single, .single])
        XCTAssertEqual(draft.steps.map(\.action), [.loadedLift, .loadedLift])
        XCTAssertEqual(draft.steps.map(\.repetitions), [4, 4])
        XCTAssertEqual(draft.steps.map(\.externalLoadKGF), [-5, -5])
        XCTAssertNotEqual(draft.steps[0].id, draft.steps[1].id)
    }

    func testAddLeftAndRightPairRemapsExactContactToTheOppositeSidePair() throws {
        var draft = CustomRoutineDraft(createWith: .boardSpecific(boardID: "mirrored"))
        let source = CustomRoutineStepDraft(
            id: "hang",
            title: "Edge hang",
            instruction: "Hang.",
            accessory: "",
            duration: 10,
            phase: .hang,
            targets: [factualRequirement(contactID: "left", selection: .single)],
            timing: .fixed,
            handUse: .single,
            side: .left
        )

        draft.addLeftAndRightPair(from: source, board: mirroredBoard())

        XCTAssertEqual(draft.steps.map(\.side), [.left, .right])
        let leftTarget = try XCTUnwrap(draft.steps[0].targets.first)
        let rightTarget = try XCTUnwrap(draft.steps[1].targets.first)
        XCTAssertEqual(leftTarget.contactID, "left")
        XCTAssertEqual(rightTarget.contactID, "right")
        for target in [leftTarget, rightTarget] {
            XCTAssertEqual(target.kind, .edge)
            XCTAssertEqual(target.shape, .flat)
            XCTAssertEqual(target.depth, .range(MillimeterRange(minimum: 18, maximum: 22)))
            XCTAssertEqual(target.fingerCapacity, 2)
            XCTAssertEqual(target.handCapacity, 1)
            XCTAssertEqual(target.selection, .single)
        }
    }

    func testAddLeftAndRightPairRemapsARightHandSourceContactToTheLeftStep() throws {
        var draft = CustomRoutineDraft(createWith: .boardSpecific(boardID: "mirrored"))
        let source = CustomRoutineStepDraft(
            id: "hang",
            title: "Edge hang",
            instruction: "Hang.",
            accessory: "",
            duration: 10,
            phase: .hang,
            targets: [factualRequirement(contactID: "right", selection: .single)],
            timing: .fixed,
            handUse: .single,
            side: .right
        )

        draft.addLeftAndRightPair(from: source, board: mirroredBoard())

        XCTAssertEqual(try XCTUnwrap(draft.steps[0].targets.first).contactID, "left")
        XCTAssertEqual(try XCTUnwrap(draft.steps[1].targets.first).contactID, "right")
    }

    func testAddLeftAndRightPairLeavesGenericAndUnpairableTargetsUnchanged() throws {
        let generic = CustomRoutineStepDraft(
            id: "generic",
            title: "Jug hang",
            instruction: "Hang.",
            accessory: "",
            duration: 10,
            phase: .hang,
            targets: [.kind(.jug)],
            timing: .fixed,
            handUse: .single,
            side: .left
        )
        var genericDraft = CustomRoutineDraft(createWith: .generic)
        genericDraft.addLeftAndRightPair(from: generic, board: nil)
        XCTAssertEqual(genericDraft.steps.map { $0.targets }, [[.kind(.jug)], [.kind(.jug)]])

        let unknown = CustomRoutineStepDraft(
            id: "unknown",
            title: "Edge hang",
            instruction: "Hang.",
            accessory: "",
            duration: 10,
            phase: .hang,
            targets: [factualRequirement(contactID: "not-on-board", selection: .single)],
            timing: .fixed,
            handUse: .single,
            side: .left
        )
        var unknownDraft = CustomRoutineDraft(createWith: .boardSpecific(boardID: "mirrored"))
        unknownDraft.addLeftAndRightPair(from: unknown, board: mirroredBoard())
        XCTAssertEqual(
            unknownDraft.steps.compactMap { $0.targets.first?.contactID },
            ["not-on-board", "not-on-board"]
        )
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

    private func mirroredBoard() -> BoardRevision {
        let contacts = [
            PhysicalContact(
                id: "left", name: "Left edge", kind: .edge,
                shape: .flat, fingerCapacity: 2, handCapacity: 1,
                depth: .range(.init(minimum: 18, maximum: 22)), gripTypes: [.halfCrimp], side: .left,
                pairedContactID: "right"
            ),
            PhysicalContact(
                id: "right", name: "Right edge", kind: .edge,
                shape: .flat, fingerCapacity: 2, handCapacity: 1,
                depth: .range(.init(minimum: 18, maximum: 22)), gripTypes: [.halfCrimp], side: .right,
                pairedContactID: "left"
            )
        ]
        let geometry = Dictionary(uniqueKeysWithValues: contacts.enumerated().map { index, contact in
            (contact.id, [BoardContactPiece(
                id: "\(contact.id)-piece",
                contactID: contact.id,
                frame: CGRect(x: index == 0 ? 0.1 : 0.8, y: 0, width: 0.1, height: 0.1),
                shape: .roundedRect(cornerRadiusFraction: 0),
                treatment: .surface
            )])
        })
        return BoardRevision(
            id: "mirrored", revisionID: "test", manufacturer: "Fixture", name: "Mirrored",
            subtitle: "", dimensions: "", aspectRatio: 1, contacts: contacts,
            productURL: URL(string: "https://example.com/mirrored")!, photoAssetName: nil,
            presentations: [BoardPresentation(
                id: "front", name: "Front", aspectRatio: 1, isDefault: true,
                media: .raster(BoardRasterMedia(assetPath: "", contactGeometry: geometry))
            )]
        )
    }

    private func oneHandedBoard() -> BoardRevision {
        let contacts = [
            PhysicalContact(id: "jug", name: "Jug", kind: .jug, handCapacity: 1)
        ]
        let geometry = ["jug": [BoardContactPiece(
            id: "jug-piece",
            contactID: "jug",
            frame: CGRect(x: 0.5, y: 0, width: 0.1, height: 0.1),
            shape: .roundedRect(cornerRadiusFraction: 0),
            treatment: .surface
        )]]
        return BoardRevision(
            id: "one-handed", revisionID: "test", manufacturer: "Fixture", name: "One-handed",
            subtitle: "", dimensions: "", aspectRatio: 1, handCapacity: 1, contacts: contacts,
            productURL: URL(string: "https://example.com/one-handed")!, photoAssetName: nil,
            presentations: [BoardPresentation(
                id: "front", name: "Front", aspectRatio: 1, isDefault: true,
                media: .raster(BoardRasterMedia(assetPath: "", contactGeometry: geometry))
            )]
        )
    }

    private func factualRequirement(
        contactID: String?,
        selection: ContactSelectionPolicy
    ) -> ContactRequirement {
        ContactRequirement(
            contactID: contactID,
            kind: .edge,
            shape: .flat,
            depth: .range(MillimeterRange(minimum: 18, maximum: 22)),
            fingerCapacity: 2,
            handCapacity: 1,
            selection: selection
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
