import XCTest
@testable import HangTen

final class CustomRoutineDraftTests: XCTestCase {
    func testMetricMeasurementsUseCanonicalValues() {
        let units = CustomRoutineDisplayUnit.metric
        XCTAssertEqual(units.loadValue(fromKilogramsForce: 11.75), 11.75)
        XCTAssertEqual(units.kilogramsForce(fromDisplayedLoad: -3.25), -3.25)
        XCTAssertEqual(units.depthValue(fromMillimeters: 20.25), 20.25)
        XCTAssertEqual(units.millimeters(fromDisplayedDepth: 20.25), 20.25)
    }

    func testImperialLoadEntryConvertsPoundsToCanonicalKilogramsForce() {
        let units = CustomRoutineDisplayUnit.imperial
        XCTAssertEqual(units.loadValue(fromKilogramsForce: 10), 22.0462262185, accuracy: 0.000_000_001)
        XCTAssertEqual(units.kilogramsForce(fromDisplayedLoad: -10), -4.5359237, accuracy: 0.000_000_001)
    }

    func testImperialDepthEntryConvertsInchesToCanonicalMillimeters() {
        let units = CustomRoutineDisplayUnit.imperial
        XCTAssertEqual(units.depthValue(fromMillimeters: 25.4), 1, accuracy: 0.000_000_001)
        XCTAssertEqual(units.millimeters(fromDisplayedDepth: 0.75), 19.05, accuracy: 0.000_000_001)
    }

    func testNonfiniteLoadInputStillRequiresValidation() {
        for units in CustomRoutineDisplayUnit.allCases {
            for value in [Double.nan, .infinity, -.infinity] {
                var draft = CustomRoutineDraft(createWith: .generic)
                draft.title = "Invalid load"
                var step = makeStep(id: "invalid-load", title: "My step")
                step.externalLoadKGF = units.kilogramsForce(fromDisplayedLoad: value)
                draft.steps = [step]
                XCTAssertFalse(step.externalLoadKGF!.isFinite)
                XCTAssertFalse(units.loadValue(fromKilogramsForce: value).isFinite)
                XCTAssertTrue(CustomRoutineEditorView.localValidationIssues(for: draft.definition())
                    .contains("Step 1 needs a finite external load."))
            }
        }
    }

    func testMeasurementConversionRoundTripsFractionalAuthoredValues() {
        for units in CustomRoutineDisplayUnit.allCases {
            XCTAssertEqual(
                units.kilogramsForce(fromDisplayedLoad: units.loadValue(fromKilogramsForce: -4.25)),
                -4.25,
                accuracy: 0.000_000_001
            )
            XCTAssertEqual(
                units.millimeters(fromDisplayedDepth: units.depthValue(fromMillimeters: 20.35)),
                20.35,
                accuracy: 0.000_000_001
            )
        }
    }

    func testChangingDisplayUnitsPreservesAuthoredCanonicalMeasurements() throws {
        var draft = CustomRoutineDraft(createWith: .generic)
        var step = makeStep(id: "fractional", title: "My step")
        step.externalLoadKGF = -4.25
        step.targets = [ContactRequirement(
            kind: .edge,
            depth: .range(.init(minimum: 17.35, maximum: 22.8)),
            selection: .single
        )]
        draft.steps = [step]
        let original = draft.definition()
        var units = CustomRoutineDisplayUnit.metric

        for _ in 0..<10 {
            units = units == .metric ? .imperial : .metric
            _ = units.loadValue(fromKilogramsForce: draft.steps[0].externalLoadKGF!)
            if case let .range(range)? = draft.steps[0].targets[0].depth {
                _ = units.depthValue(fromMillimeters: range.minimum)
                _ = units.depthValue(fromMillimeters: range.maximum)
            }
        }

        let reopened = try JSONDecoder().decode(
            CustomRoutineDefinition.self,
            from: JSONEncoder().encode(draft.definition())
        )
        XCTAssertEqual(reopened, original)
        XCTAssertEqual(reopened.steps[0].externalLoadKGF, -4.25)
        XCTAssertEqual(reopened.steps[0].workRequirements[0].depth, .range(.init(minimum: 17.35, maximum: 22.8)))
    }

    func testImperialAuthoredMeasurementsPersistInCanonicalUnits() throws {
        var draft = CustomRoutineDraft(createWith: .generic)
        var step = makeStep(id: "imperial", title: "My step")
        let units = CustomRoutineDisplayUnit.imperial
        step.externalLoadKGF = units.kilogramsForce(fromDisplayedLoad: 22.0462262185)
        step.targets = [ContactRequirement(
            kind: .edge,
            depth: .range(.init(
                minimum: units.millimeters(fromDisplayedDepth: 0.5),
                maximum: units.millimeters(fromDisplayedDepth: 0.75)
            )),
            selection: .single
        )]
        draft.steps = [step]

        let reopened = try JSONDecoder().decode(
            CustomRoutineDefinition.self,
            from: JSONEncoder().encode(draft.definition())
        )
        XCTAssertEqual(try XCTUnwrap(reopened.steps[0].externalLoadKGF), 10, accuracy: 0.000_000_001)
        guard case let .range(range)? = reopened.steps[0].workRequirements[0].depth else {
            return XCTFail("Expected a canonical millimeter range after reopening")
        }
        XCTAssertEqual(range.minimum, 12.7, accuracy: 0.000_000_001)
        XCTAssertEqual(range.maximum, 19.05, accuracy: 0.000_000_001)
    }

    func testIncompatibleHoldsProduceActionableSaveFeedback() {
        let error = CustomRoutineStoreError.validationFailed([
            .unresolvableSegmentTargets(stepIndex: 1, segmentIndex: 0), .noCompatibleBoard
        ])
        let message = CustomRoutineEditorView.saveErrorMessage(for: error)
        XCTAssertTrue(message.contains("Step 2"))
        XCTAssertTrue(message.contains("Try another hold type, shape, or depth."))
        XCTAssertFalse(message.contains("unresolvableSegmentTargets"))
    }

    func testExerciseNamesFollowChangesAfterSaveAndReopen() {
        var draft = CustomRoutineDraft(createWith: .generic)
        draft.addSet()
        var reopened = CustomRoutineDraft(editing: draft.definition())
        reopened.steps[0].exercise = .loadedLift
        XCTAssertEqual(reopened.steps[0].displayTitle, "Loaded lift")
        XCTAssertEqual(reopened.definition().steps[0].title, "Loaded lift")
        reopened.steps[0].title = "My exercise"
        reopened.steps[0].exercise = .hang
        XCTAssertEqual(reopened.steps[0].displayTitle, "My exercise")
    }

    func testNewStepRequiresAthleteAuthoredDuration() {
        var draft = CustomRoutineDraft(createWith: .generic)
        draft.title = "My routine"
        draft.addSet()
        XCTAssertEqual(draft.steps[0].duration, 0)
        XCTAssertEqual(draft.steps[0].title, "")
        XCTAssertEqual(draft.steps[0].displayTitle, "Hang")
        XCTAssertTrue(CustomRoutineEditorView.localValidationIssues(for: draft.definition())
            .contains("Step 1 needs a positive duration."))
        draft.steps[0].duration = 12
        draft.steps[0].targets = [.kind(.jug)]
        XCTAssertTrue(CustomRoutineEditorView.localValidationIssues(for: draft.definition()).isEmpty)
        XCTAssertEqual(draft.definition().steps[0].title, "Hang")
        draft.steps[0].exercise = .rest
        XCTAssertEqual(draft.definition().steps[0].title, "Rest")
    }

    func testPositiveDurationInputPersistsOneTimedSegment() throws {
        var draft = CustomRoutineDraft(createWith: .generic)
        draft.title = "Timed routine"
        draft.steps = [makeStep(id: "timed", title: "Hang", duration: 0)]

        draft.steps[0].setDuration(12)

        let persisted = try JSONDecoder().decode(
            CustomRoutineDefinition.self,
            from: JSONEncoder().encode(draft.definition())
        )
        let step = try XCTUnwrap(persisted.steps.first)
        XCTAssertEqual(step.duration, 12)
        XCTAssertEqual(step.segments.count, 1)
        XCTAssertEqual(step.segments.first?.kind, .work)
        XCTAssertEqual(step.segments.first?.timing, .fixed)
        XCTAssertEqual(step.segments.first?.duration, 12)
        XCTAssertNil(step.activeDuration)
        XCTAssertTrue(CustomRoutineValidator.issues(for: persisted, availableBoards: BoardCatalog.all).isEmpty)
    }

    func testEditingSavedOpenTimingDurationUsesTimedPlaybackWithoutOldActiveDuration() {
        let timings: [WorkoutSegmentTiming] = [.stopwatch, .undefined]
        for timing in timings {
            var original = CustomRoutineDraft(createWith: .generic)
            original.title = "Saved routine"
            var step = makeStep(id: "saved", title: "Hang", duration: 60)
            step.timing = timing
            step.activeDuration = 40
            original.steps = [step]
            let source = original.definition()
            var editing = CustomRoutineDraft(editing: source)
            XCTAssertEqual(editing.definition(), source)

            editing.steps[0].setDuration(12)

            let definition = editing.definition()
            XCTAssertEqual(definition.steps[0].duration, 12)
            XCTAssertEqual(definition.steps[0].segments.first?.timing, .fixed)
            XCTAssertEqual(definition.steps[0].segments.first?.duration, 12)
            XCTAssertNil(definition.steps[0].activeDuration)
            XCTAssertTrue(CustomRoutineValidator.issues(for: definition, availableBoards: BoardCatalog.all).isEmpty)
        }
    }

    func testShorteningTimedDurationBelowOldActiveDurationStillValidates() {
        var original = CustomRoutineDraft(createWith: .generic)
        original.title = "Saved timed routine"
        var step = makeStep(id: "timed", title: "Hang", duration: 12)
        step.activeDuration = 10
        original.steps = [step]
        var editing = CustomRoutineDraft(editing: original.definition())

        editing.steps[0].setDuration(5)

        let definition = editing.definition()
        XCTAssertEqual(definition.steps[0].duration, 5)
        XCTAssertEqual(definition.steps[0].segments.first?.duration, 5)
        XCTAssertNil(definition.steps[0].activeDuration)
        XCTAssertTrue(CustomRoutineValidator.issues(for: definition, availableBoards: BoardCatalog.all).isEmpty)
    }

    func testClearingDurationPreservesStopwatchTimingAndRequiresDuration() {
        var original = CustomRoutineDraft(createWith: .generic)
        original.title = "Saved stopwatch routine"
        var step = makeStep(id: "stopwatch", title: "Hang", duration: 60)
        step.timing = .stopwatch
        original.steps = [step]
        var editing = CustomRoutineDraft(editing: original.definition())

        editing.steps[0].setDuration(nil)

        let definition = editing.definition()
        XCTAssertEqual(editing.steps[0].duration, 0)
        XCTAssertEqual(definition.steps[0].duration, 0)
        XCTAssertEqual(definition.steps[0].segments.first?.timing, .stopwatch)
        XCTAssertNil(definition.steps[0].segments.first?.duration)
        XCTAssertTrue(CustomRoutineEditorView.localValidationIssues(for: definition)
            .contains("Step 1 needs a positive duration."))
    }

    func testExerciseChoiceCanonicalizesRestAndLoadedLift() {
        var step = makeStep(id: "one", title: "My step")
        step.handChoice = .either
        step.exercise = .isometricPull
        XCTAssertEqual(step.phase, .pull)
        XCTAssertEqual(step.action, .isometricPull)
        XCTAssertEqual(step.handUse, .double)
        step.exercise = .loadedLift
        XCTAssertEqual(step.action, .loadedLift)
        XCTAssertEqual(step.repetitions, 1)
        step.externalLoadKGF = 12
        step.exercise = .rest
        XCTAssertEqual(step.phase, .rest)
        XCTAssertTrue(step.targets.isEmpty)
        XCTAssertEqual(step.timing, .fixed)
        XCTAssertNil(step.repetitions)
        XCTAssertNil(step.externalLoadKGF)
        XCTAssertEqual(step.handChoice, .both)
        step.exercise = .hang
        XCTAssertEqual(step.phase, .hang)
        XCTAssertEqual(step.action, .hang)
        XCTAssertEqual(step.title, "My step")
        XCTAssertEqual(step.duration, 10)
    }

    func testExerciseChoicePreservesOptionalWorkoutSections() {
        for phase in [WorkoutPhase.warmUp, .conditioning, .coolDown] {
            var step = makeStep(id: "one", title: "My step")
            step.phase = phase
            step.exercise = .loadedLift
            XCTAssertEqual(step.phase, phase)
            XCTAssertEqual(step.exercise, .loadedLift)
            step.exercise = .hang
            XCTAssertEqual(step.phase, phase)
        }
    }

    func testCombinedHandChoiceUpdatesSideAndTargetPolicy() {
        var step = makeStep(id: "one", title: "My step")
        step.handChoice = .right
        XCTAssertEqual(step.handUse, .single)
        XCTAssertEqual(step.side, .right)
        XCTAssertEqual(step.targets[0].selection, .single)
        step.handChoice = .left
        XCTAssertEqual(step.handUse, .single)
        XCTAssertEqual(step.side, .left)
        step.handChoice = .both
        XCTAssertEqual(step.handUse, .double)
        XCTAssertEqual(step.side, .both)
        XCTAssertEqual(step.targets[0].selection, .bilateralPair)
        step.handChoice = .either
        XCTAssertEqual(step.handUse, .either)
        XCTAssertEqual(step.side, .both)
        XCTAssertEqual(step.targets[0].selection, .single)
    }

    /// New steps share one set without adding an unintended extra workout repetition.
    func testAddedStepsJoinOneSetByDefault() throws {
        var draft = CustomRoutineDraft(createWith: .generic)
        draft.addStep()
        let firstStepID = try XCTUnwrap(draft.steps.first?.id)
        let firstSet = try XCTUnwrap(draft.sets.first)
        XCTAssertEqual(firstSet.stepIDs, [firstStepID])
        XCTAssertEqual(firstSet.repeatCount, 1)

        draft.addStep()
        let secondStepID = draft.steps[1].id
        XCTAssertEqual(draft.sets.count, 1)
        XCTAssertEqual(draft.sets[0].id, firstSet.id)
        XCTAssertEqual(draft.sets[0].stepIDs, [firstStepID, secondStepID])
        XCTAssertEqual(draft.sets[0].repeatCount, 1)
        XCTAssertTrue(CustomRoutineValidator.setIssues(for: draft.definition()).isEmpty)
    }

    /// A one-step set exposes the same set-level editing and movement as a longer sequence.
    func testSingleStepSetUsesASetEditorRow() {
        var draft = CustomRoutineDraft(createWith: .generic)
        let step = makeStep(id: "one", title: "One")
        draft.steps = [step]
        let set = CustomRoutineSet(id: "single", stepIDs: ["one"], repeatCount: 3)
        draft.updateSet(set)

        XCTAssertEqual(draft.editorItems, [.set(set, steps: [step])])
    }

    /// Adding to an earlier set inserts at its boundary without changing a later set's count or order.
    func testAddingToEarlierSetPreservesFollowingSetAndCounts() {
        var draft = CustomRoutineDraft(createWith: .generic)
        draft.steps = ["one", "two", "three"].map { makeStep(id: $0, title: $0) }
        draft.updateSet(.init(id: "first", stepIDs: ["one"], repeatCount: 5))
        let following = CustomRoutineSet(id: "second", stepIDs: ["two", "three"], repeatCount: 2)
        draft.updateSet(following)

        draft.addStep(to: "first")

        XCTAssertEqual(draft.steps[1].title, "")
        XCTAssertEqual(draft.steps[1].displayTitle, "Hang")
        XCTAssertEqual(draft.steps.map(\.id).suffix(2), ["two", "three"])
        XCTAssertEqual(draft.sets[0].stepIDs, ["one", draft.steps[1].id])
        XCTAssertEqual(draft.sets[0].repeatCount, 5)
        XCTAssertEqual(draft.sets[1], following)
        XCTAssertTrue(CustomRoutineValidator.setIssues(for: draft.definition()).isEmpty)
    }

    /// Explicitly adding a set starts a separate sequence with one run and its own subsequent steps.
    func testAddSetStartsASeparateOnceSet() throws {
        var draft = CustomRoutineDraft(createWith: .generic)
        draft.addStep()
        let first = try XCTUnwrap(draft.sets.first)

        let second = draft.addSet()
        draft.addStep()

        XCTAssertEqual(draft.sets.count, 2)
        XCTAssertEqual(draft.sets[0], first)
        XCTAssertEqual(second.stepIDs, [draft.steps[1].id])
        XCTAssertEqual(second.repeatCount, 1)
        XCTAssertEqual(draft.sets[1].stepIDs, [draft.steps[1].id, draft.steps[2].id])
        XCTAssertEqual(draft.sets[1].repeatCount, 1)
        XCTAssertTrue(CustomRoutineValidator.setIssues(for: draft.definition()).isEmpty)
    }

    /// The default addition target follows visible order after reordering, rather than metadata order.
    func testDefaultStepAdditionFollowsReorderedSets() throws {
        var draft = CustomRoutineDraft(createWith: .generic)
        draft.addStep()
        let first = try XCTUnwrap(draft.sets.first)
        let second = draft.addSet()
        draft.moveEditorItems(from: IndexSet(integer: 0), to: 2)

        draft.addStep()

        XCTAssertEqual(draft.steps[0].id, second.stepIDs[0])
        XCTAssertEqual(draft.sets[0].stepIDs, [first.stepIDs[0], draft.steps[2].id])
        XCTAssertEqual(draft.sets[1], second)
        XCTAssertTrue(CustomRoutineValidator.setIssues(for: draft.definition()).isEmpty)
    }

    /// A stale set control cannot silently add its step to another sequence.
    func testAddingToMissingSetLeavesTheDraftUnchanged() {
        var draft = CustomRoutineDraft(createWith: .generic)
        draft.addStep()
        let before = draft

        draft.addStep(to: "missing")

        XCTAssertEqual(draft, before)
    }

    /// Planner grouping retains authored values and existing repeats, filling only unused consecutive ranges.
    func testDefaultSetPresentationPreservesStepsAndExistingRepeats() {
        var draft = CustomRoutineDraft(createWith: .generic)
        draft.steps = ["one", "two", "three", "four", "five"].map { makeStep(id: $0, title: $0) }
        let existing = CustomRoutineSet(id: "existing", stepIDs: ["two", "three"], repeatCount: 3)
        draft.updateSet(existing)

        let grouped = draft.assigningDefaultSets()

        XCTAssertEqual(grouped.steps, draft.steps)
        XCTAssertEqual(grouped.sets[0], existing)
        XCTAssertEqual(grouped.sets.dropFirst().map(\.stepIDs), [["one"], ["four", "five"]])
        XCTAssertEqual(grouped.sets.dropFirst().map(\.repeatCount), [1, 1])
        XCTAssertEqual(grouped.editorItems.map(\.stepIDs), [["one"], ["two", "three"], ["four", "five"]])
        XCTAssertEqual(grouped.assigningDefaultSets(), grouped)
        XCTAssertEqual(draft.sets, [existing], "Opening a planner copy must not mutate its input")
        XCTAssertTrue(CustomRoutineValidator.setIssues(for: grouped.definition()).isEmpty)
    }

    /// Adding a unilateral pair in an earlier set cannot append it to another set or split its range.
    func testLeftAndRightPairJoinsItsSourceSetBeforeFollowingSets() {
        var draft = CustomRoutineDraft(createWith: .generic)
        draft.steps = ["one", "two", "three", "four"].map { makeStep(id: $0, title: $0) }
        draft.updateSet(.init(id: "first", stepIDs: ["one", "two"], repeatCount: 4))
        let followingSet = CustomRoutineSet(id: "second", stepIDs: ["three", "four"], repeatCount: 2)
        draft.updateSet(followingSet)

        draft.addLeftAndRightPair(from: draft.steps[0])

        XCTAssertEqual(draft.steps.map(\.id).prefix(2), ["one", "two"])
        XCTAssertEqual(draft.steps.map(\.id).suffix(2), ["three", "four"])
        XCTAssertEqual(draft.steps[2].side, .left)
        XCTAssertEqual(draft.steps[3].side, .right)
        XCTAssertEqual(draft.sets[0].stepIDs, ["one", "two", draft.steps[2].id, draft.steps[3].id])
        XCTAssertEqual(draft.sets[0].repeatCount, 4)
        XCTAssertEqual(draft.sets[1], followingSet)
        XCTAssertTrue(CustomRoutineValidator.setIssues(for: draft.definition()).isEmpty)
    }

    /// Checks that editing, duplication, and retargeting preserve the same authored set membership.
    func testSetSurvivesEditingDuplicatingAndRetargeting() throws {
        var draft = CustomRoutineDraft(createWith: .generic)
        draft.title = "Repeat"
        draft.steps = [makeStep(id: "one", title: "One"), makeStep(id: "two", title: "Two")]
        let set = CustomRoutineSet(id: "repeat", stepIDs: ["one", "two"], repeatCount: 6)
        draft.updateSet(set)
        let definition = draft.definition()

        XCTAssertEqual(CustomRoutineDraft(editing: definition).sets, [set])
        let duplicate = CustomRoutineDraft(duplicate: definition).definition()
        XCTAssertNotEqual(duplicate.id, definition.id)
        XCTAssertEqual(duplicate.sets, [set])
        XCTAssertEqual(draft.retargeted(to: .boardSpecific(boardID: BoardCatalog.defaultBoard.id)).sets, [set])
        XCTAssertNil(draft.newSet(), "Every step already belongs to this repeat")
    }

    /// Checks membership pruning after child deletion, including removal of an empty set.
    func testDeletingSetMembersShrinksRangeAndRemovesEmptySet() {
        var draft = CustomRoutineDraft(createWith: .generic)
        draft.steps = ["one", "two", "three"].map { makeStep(id: $0, title: $0) }
        draft.updateSet(.init(id: "repeat", stepIDs: ["one", "two", "three"], repeatCount: 5))

        draft.removeSteps(at: IndexSet(integer: 1))
        XCTAssertEqual(draft.sets, [.init(id: "repeat", stepIDs: ["one", "three"], repeatCount: 5)])
        XCTAssertTrue(CustomRoutineValidator.setIssues(for: draft.definition()).isEmpty)
        draft.removeSteps(at: IndexSet([0, 1]))
        XCTAssertTrue(draft.sets.isEmpty)
    }

    /// Checks that selecting any child for movement carries the complete set in its original order.
    func testReorderingASetMemberMovesWholeSetAndKeepsOrder() {
        var draft = CustomRoutineDraft(createWith: .generic)
        draft.steps = ["one", "two", "three", "four"].map { makeStep(id: $0, title: $0) }
        let set = CustomRoutineSet(id: "repeat", stepIDs: ["two", "three"], repeatCount: 6)
        draft.updateSet(set)

        draft.moveSteps(from: IndexSet(integer: 2), to: 0)
        XCTAssertEqual(draft.steps.map(\.id), ["two", "three", "one", "four"])
        XCTAssertEqual(draft.sets, [set])
        draft.moveSteps(from: IndexSet(integer: 0), to: 4)
        XCTAssertEqual(draft.steps.map(\.id), ["one", "four", "two", "three"])
        XCTAssertTrue(CustomRoutineValidator.setIssues(for: draft.definition()).isEmpty)
    }

    /// Checks that insertion inside another set snaps to its boundary and preserves both sequences.
    func testMovingIntoAnotherSetKeepsItsMembersTogether() {
        var draft = CustomRoutineDraft(createWith: .generic)
        draft.steps = ["one", "two", "three", "four", "five"].map { makeStep(id: $0, title: $0) }
        draft.updateSet(.init(id: "first", stepIDs: ["one", "two"]))
        draft.updateSet(.init(id: "second", stepIDs: ["three", "four"]))

        draft.moveSteps(from: IndexSet(integer: 0), to: 3)
        XCTAssertEqual(draft.steps.map(\.id), ["three", "four", "one", "two", "five"])
        XCTAssertTrue(CustomRoutineValidator.setIssues(for: draft.definition()).isEmpty)
        draft.moveSteps(from: IndexSet(integer: 4), to: 1)
        XCTAssertEqual(draft.steps.map(\.id), ["five", "three", "four", "one", "two"])
        XCTAssertTrue(CustomRoutineValidator.setIssues(for: draft.definition()).isEmpty)
    }

    /// Checks that overlapping membership is rejected and ungrouping retains the original rows.
    func testOverlappingSetIsRejectedAndRemovingSetRetainsSteps() {
        var draft = CustomRoutineDraft(createWith: .generic)
        draft.steps = ["one", "two", "three"].map { makeStep(id: $0, title: $0) }
        let set = CustomRoutineSet(id: "repeat", stepIDs: ["one", "two"])
        draft.updateSet(set)
        draft.updateSet(.init(stepIDs: ["two", "three"]))
        XCTAssertEqual(draft.sets, [set])
        XCTAssertNil(draft.newSet(), "A set needs at least two consecutive ungrouped steps")

        let steps = draft.steps
        draft.removeSet(id: set.id)
        XCTAssertEqual(draft.steps, steps)
        XCTAssertTrue(draft.definition().sets.isEmpty)
    }

    /// Checks that creation needs adjacent unused steps and cannot bridge an existing repeat.
    func testNewSetStartsWithConsecutiveUngroupedSteps() throws {
        var draft = CustomRoutineDraft(createWith: .generic)
        XCTAssertNil(draft.newSet())
        draft.addStep()
        XCTAssertNil(draft.newSet())
        draft.steps = ["one", "two", "three", "four", "five"].map { makeStep(id: $0, title: $0) }
        draft.sets = []
        draft.updateSet(.init(stepIDs: ["two"]))

        let set = try XCTUnwrap(draft.newSet())
        XCTAssertEqual(set.stepIDs, ["three", "four"], "Do not set across an existing repeat")
        draft.updateSet(set)
        XCTAssertNil(draft.newSet(), "The remaining steps are not consecutive")
    }

    /// Checks row-to-step offset translation for atomic movement and deletion of grouped sequences.
    func testSetEditorRowsMoveAndDeleteWholeSequences() {
        var draft = CustomRoutineDraft(createWith: .generic)
        draft.steps = ["one", "two", "three", "four", "five"].map { makeStep(id: $0, title: $0) }
        let set = CustomRoutineSet(id: "set", stepIDs: ["two", "three"], repeatCount: 6)
        draft.updateSet(set)
        draft.updateSet(.init(id: "single", stepIDs: ["five"], repeatCount: 3))
        XCTAssertEqual(draft.editorItems.map(\.stepIDs), [["one"], ["two", "three"], ["four"], ["five"]])
        XCTAssertEqual(Set(draft.editorItems.map(\.id)).count, 4)

        draft.moveEditorItems(from: IndexSet(integer: 1), to: 4)
        XCTAssertEqual(draft.steps.map(\.id), ["one", "four", "five", "two", "three"])
        draft.moveEditorItems(from: IndexSet(integer: 2), to: 4)
        XCTAssertEqual(draft.steps.map(\.id), ["one", "four", "two", "three", "five"])
        XCTAssertTrue(CustomRoutineValidator.setIssues(for: draft.definition()).isEmpty)

        draft.removeEditorItems(at: IndexSet([0, 2]))
        XCTAssertEqual(draft.steps.map(\.id), ["four", "five"])
        XCTAssertEqual(draft.sets.map(\.id), ["single"])
    }

    /// Checks that child edits and ordering survive removal of the surrounding set metadata.
    func testUngroupingKeepsChildEditsAndTheirOrder() {
        var draft = CustomRoutineDraft(createWith: .generic)
        draft.steps = ["hang", "rest"].map { makeStep(id: $0, title: $0) }
        let set = CustomRoutineSet(id: "repeat", stepIDs: ["hang", "rest"], repeatCount: 3)
        draft.updateSet(set)
        var rest = draft.steps[1]
        rest.phase = .rest
        rest.duration = 4
        draft.updateStep(rest)
        XCTAssertEqual(draft.editorItems, [.set(set, steps: draft.steps)])

        draft.removeSet(id: set.id)
        XCTAssertEqual(draft.editorItems, draft.steps.map { .step($0) })
        XCTAssertEqual(draft.steps[1], rest)
    }

    func testConfiguredDepthToggleUsesResolvedPositionWithinSharedPresentation() throws {
        let contact = PhysicalContact(id: "edge", name: "Fixture edge", kind: .edge,
            handCapacity: 1, depth: .range(.init(minimum: 18, maximum: 18)))
        let geometry = [contact.id: [BoardContactPiece(id: "edge-piece", contactID: contact.id,
            frame: CGRect(x: 0.4, y: 0.4, width: 0.2, height: 0.1),
            shape: .roundedRect(cornerRadiusFraction: 0), treatment: .surface)]]
        let board = BoardRevision(id: "fixture.shared-presentation-depths", revisionID: "fixture",
            manufacturer: "Fixture", name: "Fixture", subtitle: "", dimensions: "", aspectRatio: 1,
            contacts: [contact], productURL: URL(string: "https://example.com/fixture")!, photoAssetName: nil,
            presentations: [BoardPresentation(id: "front", name: "Fixture", aspectRatio: 1, isDefault: true,
                media: .raster(BoardRasterMedia(assetPath: "", contactGeometry: geometry)))],
            positions: [18, 10].map { depth in
                BoardPosition(id: "depth-\(depth)", presentationID: "front", contactIDs: [contact.id],
                    effectiveDepths: [contact.id: .range(.init(minimum: Double(depth), maximum: Double(depth)))])
            })
        let original = CustomRoutineStepDraft(id: "configured", title: "", instruction: "", accessory: "",
            duration: 10, phase: .hang, targets: [.edge(depth: .range(.init(minimum: 10, maximum: 10)))],
            timing: .fixed, handUse: .single, side: .left)
        XCTAssertEqual(CustomRoutineBoardPreview.presentationID(for: original, on: board), "front")
        XCTAssertEqual(CustomRoutineBoardPreview.contactIDs(for: original, on: board), ["edge"])

        var removing = original
        let shallow = try XCTUnwrap(board.contacts(inPosition: "depth-10").first)
        CustomRoutineBoardPreview.toggle(shallow, in: &removing, on: board)
        XCTAssertTrue(removing.targets.isEmpty, "Tapping the selected 10 mm configuration must remove it.")

        var changing = original
        let deeper = try XCTUnwrap(board.contacts(inPosition: "depth-18").first)
        CustomRoutineBoardPreview.toggle(deeper, in: &changing, on: board)
        XCTAssertEqual(changing.targets.first?.contactID, "edge")
        XCTAssertEqual(changing.targets.first?.depth, .range(.init(minimum: 18, maximum: 18)),
            "Tapping another depth in the same presentation must change the target.")
        CustomRoutineBoardPreview.toggle(deeper, in: &changing, on: board)
        XCTAssertTrue(changing.targets.isEmpty)
    }

    func testConfiguredTargetReopensItsModelAndChangingDepthKeepsTheContact() throws {
        let board = try XCTUnwrap(BoardCatalog.packageStore.board(id: "plateau.lifting-edge"))
        var step = CustomRoutineStepDraft(id: "configured", title: "", instruction: "", accessory: "", duration: 10,
            phase: .hang, targets: [.edge(depth: .range(.init(minimum: 10, maximum: 10)))],
            timing: .fixed, handUse: .single, side: .left)
        XCTAssertEqual(CustomRoutineBoardPreview.presentationID(for: step, on: board), "depth-10mm")
        XCTAssertEqual(CustomRoutineBoardPreview.contactIDs(for: step, on: board), ["edge-18"])
        let deeper = try XCTUnwrap(board.contacts(inPosition: "depth-18mm").first)
        CustomRoutineBoardPreview.toggle(deeper, in: &step, on: board)
        XCTAssertEqual(step.targets.first?.contactID, "edge-18")
        XCTAssertEqual(step.targets.first?.depth, .range(.init(minimum: 18, maximum: 18)))
        XCTAssertEqual(CustomRoutineBoardPreview.presentationID(for: step, on: board), "depth-18mm")
        CustomRoutineBoardPreview.toggle(deeper, in: &step, on: board)
        XCTAssertTrue(step.targets.isEmpty)
    }

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

    func testEditorLocalValidationShowsTerminalRestMessageAfterNormalization() {
        let steps = [
            WorkoutStepDefinition(
                id: "implicit-rest", title: "Implicit rest", instruction: "", accessory: "",
                duration: 12, phase: .hang, activeDuration: 8
            ),
            WorkoutStepDefinition(
                id: "compound-rest", title: "Compound rest", instruction: "", accessory: "",
                duration: 12, phase: .hang,
                segments: [
                    .init(kind: .work, target: .fromLegacyTargets([.kind(.jug)]), timing: .fixed, duration: 8),
                    .init(kind: .rest, target: nil, timing: .fixed, duration: 4)
                ]
            )
        ]
        for step in steps {
            let definition = CustomRoutineDefinition(
                id: "custom.terminal-rest", title: "Terminal rest", subtitle: "",
                difficulty: nil, category: nil, tags: [], targetMode: .generic, steps: [step]
            )
            XCTAssertTrue(
                CustomRoutineEditorView.localValidationIssues(for: definition)
                    .contains("End the routine with a work step."),
                "The editor must explain the normalized trailing rest in \(step.id)"
            )
        }
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
