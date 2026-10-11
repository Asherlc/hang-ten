import XCTest
@testable import HangTen

final class PlanHoldSubstitutionTests: XCTestCase {
    func testMissingHoldRequiresAValidExplicitChoiceAndGroupsRepeatedWork() throws {
        let board = fixtureBoard()
        let source = fixturePlan(steps: [fixtureStep(id: "first"), fixtureStep(id: "repeat")])
        let requests = PlanHoldSubstitutions.requests(for: source, on: board)
        let request = try XCTUnwrap(requests.first)
        XCTAssertEqual(requests.count, 1)
        XCTAssertEqual(request.stepTitles, ["first", "repeat"])
        XCTAssertTrue(request.requiredHoldLabel.contains("10 mm"))
        XCTAssertNil(PlanHoldSubstitutions.applying([:], to: source, on: board))
        XCTAssertNil(PlanHoldSubstitutions.applying([request.id: "unknown"], to: source, on: board))
        let option = try XCTUnwrap(request.options.first)
        let session = try XCTUnwrap(PlanHoldSubstitutions.applying([request.id: option.id], to: source, on: board))
        XCTAssertEqual(session.provenance, .adapted)
        XCTAssertEqual(source.provenance, .official)
        XCTAssertEqual(session.boardID, board.id)
        XCTAssertEqual(session.steps.count, 2)
        for step in session.steps {
            XCTAssertTrue(step.instruction.contains("Source instruction."))
            XCTAssertTrue(step.instruction.contains(option.label))
            XCTAssertEqual(step.accessory, "Source accessory.")
            XCTAssertEqual(step.duration, 12)
            XCTAssertEqual(step.timedWorkDuration, 10)
            XCTAssertEqual(step.repetitions, 3)
            XCTAssertEqual(step.externalLoadKGF, 2)
        }
        XCTAssertEqual(session.stepRepeats, source.stepRepeats)
        XCTAssertEqual(session.id, source.id)
        XCTAssertEqual(session.sourceURL, source.sourceURL)
    }

    func testSelectedHoldsAreIdenticalInPreviewAndRecording() throws {
        let board = fixtureBoard()
        let source = fixturePlan(steps: [fixtureStep()])
        let request = try XCTUnwrap(PlanHoldSubstitutions.requests(for: source, on: board).first)
        let option = try XCTUnwrap(request.options.first { $0.label.contains("20 mm left") && $0.label.contains("20 mm right") })
        let session = try XCTUnwrap(PlanHoldSubstitutions.applying([request.id: option.id], to: source, on: board))
        XCTAssertEqual(Set(WorkoutHighlightResolver.contactIDs(for: session.steps[0], on: board)), ["left-20", "right-20"])
        let recording = try WorkoutActivityRecorder().segments(for: session, on: board)
        let work = try XCTUnwrap(recording.first { $0.kind == .work })
        XCTAssertEqual(Set(try XCTUnwrap(work.target?.resolvedContactSnapshot).contactIDs), ["left-20", "right-20"])
        XCTAssertEqual(work.durationSeconds, 10)
    }

    func testOnlyFailedOrderedTaskChangesAndRestSegmentsRemainUnchanged() throws {
        let board = fixtureBoard()
        let existing = task(depth: 20, sides: [.left, .right])
        let missing = task(depth: 10, sides: [.right, .left])
        let target = WorkoutSegmentTarget.tasks([existing, missing, existing])
        let step = fixtureStep(target: target)
        let source = fixturePlan(steps: [step])
        let request = try XCTUnwrap(PlanHoldSubstitutions.requests(for: source, on: board).first)
        let option = try XCTUnwrap(request.options.first)
        let session = try XCTUnwrap(PlanHoldSubstitutions.applying([request.id: option.id], to: source, on: board))
        let tasks = try XCTUnwrap(session.steps[0].segments[0].target?.planTasks)
        XCTAssertEqual(tasks.count, 3)
        XCTAssertEqual(tasks[0], existing)
        XCTAssertEqual(tasks[2], existing)
        XCTAssertEqual(tasks[1].map(\.side), [.right, .left])
        XCTAssertEqual(session.steps[0].segments[1], step.segments[1])
        XCTAssertEqual(source.steps[0].segments[0].target, target)
    }

    func testOptionsRejectSmallFingerCapacityAndUnsupportedGrip() throws {
        let board = fixtureBoard(extraContacts: [
            contact(id: "small", name: "Too small", depth: 30, capacity: 2, grip: [.halfCrimp]),
            contact(id: "wrong-grip", name: "Wrong grip", depth: 40, capacity: 4, grip: [.openHand])
        ])
        let fingers = try XCTUnwrap(FingerConfiguration(engagedFingers: [.index, .middle, .ring]))
        let source = fixturePlan(steps: [fixtureStep(grip: .halfCrimp, fingers: fingers)])
        let request = try XCTUnwrap(PlanHoldSubstitutions.requests(for: source, on: board).first)
        XCTAssertFalse(request.options.isEmpty)
        XCTAssertFalse(request.options.contains { $0.label.contains("Too small") || $0.label.contains("Wrong grip") })
        let session = try XCTUnwrap(PlanHoldSubstitutions.applying([request.id: request.options[0].id], to: source, on: board))
        XCTAssertEqual(session.steps[0].gripType, .halfCrimp)
        XCTAssertEqual(session.steps[0].fingerConfiguration, fingers)
    }

    func testNoValidPairLeavesNoOptions() throws {
        let board = fixtureBoard(contacts: [contact(id: "only", name: "Only hold", depth: 20)])
        let request = try XCTUnwrap(PlanHoldSubstitutions.requests(for: fixturePlan(steps: [fixtureStep()]), on: board).first)
        XCTAssertTrue(request.options.isEmpty)
    }

    func testTwoHandSubstitutionsRejectSharedContactsFromOneSide() throws {
        let cases: [(ContactSide?, CGFloat)] = [(.left, 0.45), (.right, 0.45), (nil, 0.1), (nil, 0.8)]
        let handSides: [[WorkoutSide?]] = [[nil, nil], [.left, .right], [.right, .left]]
        for (side, x) in cases {
            let board = fixtureBoard(contacts: [
                contact(id: "only", name: "One-sided hold", depth: 20, side: side, handCapacity: 2)
            ], frames: ["only": CGRect(x: x, y: 0.2, width: 0.1, height: 0.1)])
            let source = fixturePlan(steps: [fixtureStep()])
            let request = try XCTUnwrap(PlanHoldSubstitutions.requests(for: source, on: board).first)
            XCTAssertTrue(request.options.isEmpty, "A one-sided contact cannot replace both hands.")
            XCTAssertNil(PlanHoldSubstitutions.applying([:], to: source, on: board))
            for sides in handSides {
                XCTAssertThrowsError(try ContactResolver.resolve(task(depth: 20, sides: sides),
                    step: source.steps[0], board: board))
            }
        }
    }

    func testTwoHandSubstitutionsOfferThePairWithoutAOneSidedSharedContact() throws {
        let board = fixtureBoard(extraContacts: [
            contact(id: "right-30", name: "30 mm right", depth: 30, side: .right, handCapacity: 2)
        ])
        let source = fixturePlan(steps: [fixtureStep()])
        let request = try XCTUnwrap(PlanHoldSubstitutions.requests(for: source, on: board).first)
        XCTAssertEqual(request.options.count, 1)
        let option = try XCTUnwrap(request.options.first)
        let session = try XCTUnwrap(PlanHoldSubstitutions.applying([request.id: option.id], to: source, on: board))
        XCTAssertEqual(Set(WorkoutHighlightResolver.contactIDs(for: session.steps[0], on: board)),
            ["left-20", "right-20"])
    }

    func testCenteredTwoHandContactRemainsAValidSubstitute() throws {
        let board = fixtureBoard(contacts: [
            contact(id: "shared", name: "Centered edge", depth: 20, handCapacity: 2)
        ], frames: ["shared": CGRect(x: 0.45, y: 0.2, width: 0.1, height: 0.1)])
        let source = fixturePlan(steps: [fixtureStep()])
        let request = try XCTUnwrap(PlanHoldSubstitutions.requests(for: source, on: board).first)
        XCTAssertEqual(request.options.count, 1)
        let option = try XCTUnwrap(request.options.first)
        XCTAssertTrue(option.label.contains("both hands"))
        let session = try XCTUnwrap(PlanHoldSubstitutions.applying([request.id: option.id], to: source, on: board))
        let selectedTask = try XCTUnwrap(session.steps[0].segments[0].target?.planTasks?.first)
        XCTAssertEqual(try ContactResolver.resolve(selectedTask, step: session.steps[0], board: board).map(\.id),
            ["shared", "shared"])
        let work = try XCTUnwrap(try WorkoutActivityRecorder().segments(for: session, on: board).first { $0.kind == .work })
        XCTAssertEqual(work.target?.resolvedContactSnapshot?.contactIDs, ["shared", "shared"])
    }

    func testCompatiblePlansAreReturnedUnchangedAndForeignBoardChoicesAreRejected() throws {
        let board = fixtureBoard()
        let source = fixturePlan(steps: [fixtureStep(target: .tasks([task(depth: 20)]))])
        XCTAssertTrue(PlanHoldSubstitutions.requests(for: source, on: board).isEmpty)
        XCTAssertEqual(PlanHoldSubstitutions.applying([:], to: source, on: board), source)
        let missing = fixturePlan(steps: [fixtureStep()])
        let request = try XCTUnwrap(PlanHoldSubstitutions.requests(for: missing, on: board).first)
        let other = fixtureBoard(id: "other")
        XCTAssertNil(PlanHoldSubstitutions.applying([request.id: request.options[0].id], to: missing, on: other))
    }

    func testPreparedRequestsApplySuccessiveExplicitChoicesWithoutChangingTheSource() throws {
        let board = fixtureBoard(extraContacts: [
            contact(id: "left-30", name: "30 mm left", depth: 30, side: .left),
            contact(id: "right-30", name: "30 mm right", depth: 30, side: .right)
        ])
        let source = fixturePlan(steps: [fixtureStep()])
        let prepared = PlanHoldSubstitutions.prepare(for: source, on: board)
        let request = try XCTUnwrap(prepared.requests.first)
        for depth in [20, 30] {
            let option = try XCTUnwrap(request.options.first { $0.label.contains("\(depth) mm left") })
            let session = try XCTUnwrap(PlanHoldSubstitutions.applying(
                [request.id: option.id], to: source, on: board, prepared: prepared
            ))
            XCTAssertEqual(Set(WorkoutHighlightResolver.contactIDs(for: session.steps[0], on: board)),
                ["left-\(depth)", "right-\(depth)"])
            XCTAssertEqual(session.steps[0].duration, 12)
            XCTAssertEqual(session.steps[0].accessory, "Source accessory.")
        }
        XCTAssertEqual(source.steps[0].instruction, "Source instruction.")
        XCTAssertEqual(source.provenance, .official)
        XCTAssertNil(source.boardID)
    }

    func testPreparedRequestsRejectChangedPrescriptionWithTheSamePlanID() throws {
        let board = fixtureBoard()
        let source = fixturePlan(steps: [fixtureStep()])
        let prepared = PlanHoldSubstitutions.prepare(for: source, on: board)
        let request = try XCTUnwrap(prepared.requests.first)
        let selections = [request.id: try XCTUnwrap(request.options.first).id]
        var changed = source
        changed.stepRepeats = [WorkoutStepRepeat(stepRange: 0..<1, repeatCount: 5)]

        XCTAssertNil(PlanHoldSubstitutions.applying(
            selections, to: changed, on: board, prepared: prepared
        ))
        let fresh = PlanHoldSubstitutions.prepare(for: changed, on: board)
        let session = try XCTUnwrap(PlanHoldSubstitutions.applying(
            selections, to: changed, on: board, prepared: fresh
        ))
        XCTAssertEqual(session.stepRepeats, [WorkoutStepRepeat(stepRange: 0..<1, repeatCount: 5)])
        XCTAssertEqual(Set(WorkoutHighlightResolver.contactIDs(for: session.steps[0], on: board)),
            ["left-20", "right-20"])
    }

    func testPreparedRequestsRejectChangedBoardFactsWithTheSameBoardAndRevisionIDs() throws {
        let board = fixtureBoard()
        let source = fixturePlan(steps: [fixtureStep()])
        let prepared = PlanHoldSubstitutions.prepare(for: source, on: board)
        let request = try XCTUnwrap(prepared.requests.first)
        let selections = [request.id: try XCTUnwrap(request.options.first).id]
        let changed = fixtureBoard(contacts: [
            contact(id: "left-20", name: "30 mm left", depth: 30, side: .left),
            contact(id: "right-20", name: "30 mm right", depth: 30, side: .right)
        ])

        XCTAssertNil(PlanHoldSubstitutions.applying(
            selections, to: source, on: changed, prepared: prepared
        ))
        let fresh = PlanHoldSubstitutions.prepare(for: source, on: changed)
        let session = try XCTUnwrap(PlanHoldSubstitutions.applying(
            selections, to: source, on: changed, prepared: fresh
        ))
        let targets = try XCTUnwrap(session.steps[0].segments[0].target?.planTasks?.first)
        XCTAssertEqual(targets.map { $0.target?.depth }, [
            .measured(.init(minimum: 30, maximum: 30)),
            .measured(.init(minimum: 30, maximum: 30))
        ])
        XCTAssertTrue(session.steps[0].instruction.contains("30 mm left"))
    }

    func testPreparedCompatibleRequestsCannotBypassChoicesAfterTheBoardChanges() throws {
        let board = fixtureBoard()
        let source = fixturePlan(steps: [fixtureStep(target: .tasks([task(depth: 20)]))])
        let prepared = PlanHoldSubstitutions.prepare(for: source, on: board)
        XCTAssertTrue(prepared.requests.isEmpty)
        XCTAssertEqual(PlanHoldSubstitutions.applying([:], to: source, on: board, prepared: prepared), source)
        let changed = fixtureBoard(contacts: [
            contact(id: "left-20", name: "30 mm left", depth: 30, side: .left),
            contact(id: "right-20", name: "30 mm right", depth: 30, side: .right)
        ])

        XCTAssertNil(PlanHoldSubstitutions.applying([:], to: source, on: changed, prepared: prepared))
        let fresh = PlanHoldSubstitutions.prepare(for: source, on: changed)
        let request = try XCTUnwrap(fresh.requests.first)
        let session = try XCTUnwrap(PlanHoldSubstitutions.applying(
            [request.id: try XCTUnwrap(request.options.first).id], to: source, on: changed, prepared: fresh
        ))
        XCTAssertEqual(session.provenance, .adapted)
        XCTAssertTrue(session.steps[0].instruction.contains("30 mm left"))
    }

    func testPreparedRequestsStillRequireEveryExplicitValidChoice() throws {
        let board = fixtureBoard()
        let source = fixturePlan(steps: [fixtureStep(), fixtureStep(id: "second", target: .tasks([task(depth: 5)]))])
        let prepared = PlanHoldSubstitutions.prepare(for: source, on: board)
        XCTAssertEqual(prepared.requests.count, 2)
        let first = try XCTUnwrap(prepared.requests.first)
        let second = try XCTUnwrap(prepared.requests.last)
        let firstOption = try XCTUnwrap(first.options.first)
        let secondOption = try XCTUnwrap(second.options.first)
        XCTAssertNil(PlanHoldSubstitutions.applying([:], to: source, on: board, prepared: prepared))
        XCTAssertNil(PlanHoldSubstitutions.applying(
            [first.id: firstOption.id], to: source, on: board, prepared: prepared
        ))
        XCTAssertNil(PlanHoldSubstitutions.applying(
            [first.id: firstOption.id, second.id: "unknown"], to: source, on: board, prepared: prepared
        ))
        let session = try XCTUnwrap(PlanHoldSubstitutions.applying(
            [first.id: firstOption.id, second.id: secondOption.id], to: source, on: board, prepared: prepared
        ))
        XCTAssertEqual(session.steps.count, 2)
        for step in session.steps {
            XCTAssertEqual(Set(WorkoutHighlightResolver.contactIDs(for: step, on: board)), ["left-20", "right-20"])
        }
    }

    func testOneHandedBoardUsesExistingLegacyHandMaterialization() throws {
        let board = fixtureBoard(contacts: [contact(id: "one", name: "20 mm single", depth: 20)], handCapacity: 1)
        let valid = ContactRequirement(kind: .edge, depth: .range(.init(minimum: 20, maximum: 20)), selection: .bilateralPair)
        let source = fixturePlan(steps: [fixtureStep(target: .requirements([valid]))])
        XCTAssertTrue(PlanHoldSubstitutions.requests(for: source, on: board).isEmpty)
        XCTAssertEqual(PlanHoldSubstitutions.applying([:], to: source, on: board), source)
        let missing = ContactRequirement(kind: .edge, depth: .range(.init(minimum: 10, maximum: 10)), selection: .bilateralPair)
        let missingPlan = fixturePlan(steps: [fixtureStep(target: .requirements([missing]))])
        let request = try XCTUnwrap(PlanHoldSubstitutions.requests(for: missingPlan, on: board).first)
        XCTAssertEqual(request.options.count, 1)
        let session = try XCTUnwrap(PlanHoldSubstitutions.applying([request.id: request.options[0].id], to: missingPlan, on: board))
        let resolved = WorkoutSessionHandResolver.materialized(session.steps[0], preference: .left, boardIsOneHanded: true)
        XCTAssertEqual(try ContactResolver.resolve(resolved.workRequirements, step: resolved, board: board).map(\.id), ["one"])
    }

    func testCustomSessionAndAdditionalWorkSegmentsKeepTheirAuthoredMetadata() throws {
        let board = fixtureBoard()
        let base = fixtureStep()
        let extra = WorkoutSegment(kind: .work, target: .tasks([task(depth: 20)]), timing: .stopwatch, duration: nil)
        let step = WorkoutStep(id: base.id, number: base.number, title: base.title,
            instruction: base.instruction, accessory: base.accessory, duration: base.duration, phase: base.phase,
            segments: base.segments + [extra], gripType: base.gripType, fingerConfiguration: base.fingerConfiguration,
            handUse: base.handUse, side: base.side, repetitions: base.repetitions,
            externalLoadKGF: base.externalLoadKGF, timedWorkDuration: base.timedWorkDuration)
        var source = TrainingPlan(id: "custom", title: "Custom", subtitle: "", level: "Custom", sourceLabel: "Athlete",
            sourceURL: nil, provenance: .custom, boardID: "previous-board", steps: [step])
        source.isFreeWorkout = true
        let request = try XCTUnwrap(PlanHoldSubstitutions.requests(for: source, on: board).first)
        let session = try XCTUnwrap(PlanHoldSubstitutions.applying([request.id: request.options[0].id], to: source, on: board))
        XCTAssertEqual(session.provenance, .custom)
        XCTAssertTrue(session.isFreeWorkout)
        XCTAssertEqual(session.steps[0].segments[2], extra)
        XCTAssertEqual(source.boardID, "previous-board")
        XCTAssertEqual(session.boardID, "board")
    }

    func testMatchingSourcePairOffersMatchingDepthsWithoutMixedEdgeOptions() throws {
        let board = fixtureBoard(extraContacts: [
            contact(id: "left-30", name: "30 mm left", depth: 30, side: .left),
            contact(id: "right-30", name: "30 mm right", depth: 30, side: .right)
        ])
        let source = fixturePlan(steps: [fixtureStep()])
        let request = try XCTUnwrap(PlanHoldSubstitutions.requests(for: source, on: board).first)
        XCTAssertEqual(request.options.count, 2)
        XCTAssertTrue(request.requiredHoldLabel.contains("Half crimp"))
        for option in request.options {
            let target = try XCTUnwrap(option.target.planTasks?.first)
            XCTAssertEqual(target[0].target, target[1].target)
        }
    }

    func testNumericToleranceDoesNotPresentDifferentFactualDepthsAsAMatchingPair() throws {
        let board = fixtureBoard(contacts: [
            contact(id: "left-20", name: "20 mm left", depth: 20, side: .left),
            contact(id: "right-21", name: "21 mm right", depth: 21, side: .right)
        ])
        let source = fixturePlan(steps: [fixtureStep()])
        let request = try XCTUnwrap(PlanHoldSubstitutions.requests(for: source, on: board).first)
        XCTAssertTrue(request.options.isEmpty,
            "The resolver's depth tolerance must not create a matching pair from physically different depths.")
    }

    func testMixedTaskKeepsTheAlreadySupportedHandTarget() throws {
        let board = fixtureBoard()
        let supported = PlanHandTarget(target: PlanContactPredicate(kind: .edge,
            depth: .measured(.init(minimum: 20, maximum: 20)), fingerCapacity: 3), side: .left)
        let missing = PlanHandTarget(target: PlanContactPredicate(kind: .pocket, fingerCapacity: 3), side: .right)
        let source = fixturePlan(steps: [fixtureStep(target: .tasks([[supported, missing]]))])
        let request = try XCTUnwrap(PlanHoldSubstitutions.requests(for: source, on: board).first)
        XCTAssertFalse(request.options.isEmpty)
        for option in request.options {
            XCTAssertEqual(option.target.planTasks?.first?.first, supported)
        }
    }

    func testUnsidedSingleTaskResolvesBeforeAnAthleteChoosesAHand() throws {
        let board = fixtureBoard(contacts: [contact(id: "left-only", name: "20 mm left only", depth: 20, side: .left)])
        let source = fixturePlan(steps: [fixtureStep(target: .tasks([task(depth: 20, sides: [nil])]))])
        XCTAssertFalse(WorkoutSessionHandResolver.needsHandChoice(plan: source, board: board))
        XCTAssertTrue(PlanHoldSubstitutions.requests(for: source, on: board).isEmpty)
        XCTAssertEqual(PlanHoldSubstitutions.applying([:], to: source, on: board), source)
        let missing = fixturePlan(steps: [fixtureStep(target: .tasks([task(depth: 10, sides: [nil])]))])
        let request = try XCTUnwrap(PlanHoldSubstitutions.requests(for: missing, on: board).first)
        let session = try XCTUnwrap(PlanHoldSubstitutions.applying([request.id: request.options[0].id], to: missing, on: board))
        XCTAssertNil(session.steps[0].segments[0].target?.planTasks?.first?.first?.side)
        XCTAssertFalse(WorkoutSessionHandResolver.needsHandChoice(plan: session, board: board))
    }

    func testTwoHandTaskOnOneHandBoardKeepsOneContactPerBoardCopy() throws {
        let board = fixtureBoard(contacts: [contact(id: "one", name: "20 mm single", depth: 20)], handCapacity: 1)
        let source = fixturePlan(steps: [fixtureStep()])
        let request = try XCTUnwrap(PlanHoldSubstitutions.requests(for: source, on: board).first)
        XCTAssertEqual(request.options.count, 1)
        XCTAssertTrue(request.options[0].label.contains("two boards"))
        let session = try XCTUnwrap(PlanHoldSubstitutions.applying([request.id: request.options[0].id], to: source, on: board))
        let tasks = try XCTUnwrap(session.steps[0].segments[0].target?.planTasks)
        XCTAssertEqual(tasks[0].count, 2)
        XCTAssertEqual(try ContactResolver.resolve(tasks[0], step: session.steps[0], board: board).map(\.id), ["one", "one"])
    }

    func testMixedTwoHandTaskOnOneHandBoardLabelsDifferentContactsAsTwoBoards() throws {
        let board = fixtureBoard(contacts: [
            contact(id: "edge-20", name: "20 mm edge", depth: 20),
            contact(id: "edge-30", name: "30 mm edge", depth: 30)
        ], handCapacity: 1)
        let missing = task(depth: 10, sides: [.left]) + task(depth: 15, sides: [.right])
        let source = fixturePlan(steps: [fixtureStep(target: .tasks([missing]))])
        let request = try XCTUnwrap(PlanHoldSubstitutions.requests(for: source, on: board).first)
        let option = try XCTUnwrap(request.options.first { $0.label.contains("20 mm edge") && $0.label.contains("30 mm edge") })
        XCTAssertTrue(option.label.contains("two boards"))
        let session = try XCTUnwrap(PlanHoldSubstitutions.applying([request.id: option.id], to: source, on: board))
        let selectedTask = try XCTUnwrap(session.steps[0].segments[0].target?.planTasks?.first)
        XCTAssertEqual(Set(try ContactResolver.resolve(selectedTask, step: session.steps[0], board: board).map(\.id)),
            ["edge-20", "edge-30"])
    }

    func testCatalogMaxHangsOnSupportedBeastmakerKeepsItsSourcePrescription() throws {
        let board = try XCTUnwrap(BoardCatalog.packageStore.board(id: "beastmaker-1000"))
        let source = PlanCatalog.maxHangs
        XCTAssertTrue(PlanHoldSubstitutions.requests(for: source, on: board).isEmpty)
        XCTAssertEqual(PlanHoldSubstitutions.applying([:], to: source, on: board), source)
    }

    func testSourceDepthRangesDoNotExposeInternalMatchingToleranceBands() throws {
        let board = fixtureBoard(contacts: [
            contact(id: "left", name: "30 mm left", depth: 30, side: .left),
            contact(id: "right", name: "30 mm right", depth: 30, side: .right)
        ])
        let source = PlanCatalog.maxHangs
        let request = try XCTUnwrap(PlanHoldSubstitutions.requests(for: source, on: board).first)
        XCTAssertFalse(request.requiredHoldLabel.contains("9–19 mm"),
                       "The serialized matching band is not the source's 8–20 mm prescription.")
        let session = try XCTUnwrap(PlanHoldSubstitutions.applying(
            [request.id: request.options[0].id], to: source, on: board
        ))
        XCTAssertTrue(session.steps[0].instruction.contains(source.steps[0].instruction))
    }

    func testEffectiveDepthChoicesForTheSameContactHaveDistinctFactualLabels() throws {
        let base = fixtureBoard(contacts: [contact(id: "edge", name: "Wood edge", depth: 18)], handCapacity: 1)
        let positions = [10.0, 15.0, 18.0].map { depth in
            BoardPosition(id: "depth-\(Int(depth))", presentationID: "front", contactIDs: ["edge"],
                effectiveDepths: ["edge": .range(.init(minimum: depth, maximum: depth))])
        } + [BoardPosition(id: "depth-range", presentationID: "front", contactIDs: ["edge"],
                effectiveDepths: ["edge": .range(.init(minimum: 20, maximum: 22))])]
        let board = BoardRevision(id: base.id, revisionID: base.revisionID,
            manufacturer: base.manufacturer, name: base.name, subtitle: base.subtitle,
            dimensions: nil, aspectRatio: base.aspectRatio, handCapacity: 1, contacts: base.contacts,
            productURL: base.productURL, photoAssetName: nil, presentations: base.presentations, positions: positions)
        let source = fixturePlan(steps: [fixtureStep(target: .tasks([task(depth: 7)]))])
        let request = try XCTUnwrap(PlanHoldSubstitutions.requests(for: source, on: board).first)
        XCTAssertEqual(request.options.count, 4)
        XCTAssertEqual(Set(request.options.map(\.label)).count, 4)
        for depth in ["10 mm", "15 mm", "18 mm", "20–22 mm"] {
            XCTAssertTrue(request.options.contains { $0.label.contains("Wood edge") && $0.label.contains(depth) })
        }
    }

    private func fixturePlan(steps: [WorkoutStep]) -> TrainingPlan {
        var plan = TrainingPlan(id: "source", title: "Source", subtitle: "", level: "Entry", sourceLabel: "Manufacturer",
            sourceURL: URL(string: "https://example.com/source"), provenance: .official, boardID: nil, steps: steps)
        plan.stepRepeats = [WorkoutStepRepeat(stepRange: 0..<steps.count, repeatCount: steps.count)]
        return plan
    }

    private func fixtureStep(id: String = "first", target: WorkoutSegmentTarget? = nil,
                             grip: GripType? = .halfCrimp, fingers: FingerConfiguration? = nil) -> WorkoutStep {
        WorkoutStep(id: id, number: 1, title: id, instruction: "Source instruction.", accessory: "Source accessory.",
            duration: 12, phase: .hang,
            segments: [WorkoutSegment(kind: .work, target: target ?? .tasks([task(depth: 10)]), timing: .fixed, duration: 10),
                       WorkoutSegment(kind: .rest, target: nil, timing: .fixed, duration: 2)],
            gripType: grip, fingerConfiguration: fingers, handUse: .double, side: .both,
            repetitions: 3, externalLoadKGF: 2, timedWorkDuration: 10)
    }

    private func task(depth: Double, sides: [WorkoutSide?] = [nil, nil]) -> [PlanHandTarget] {
        sides.map { PlanHandTarget(target: PlanContactPredicate(kind: .edge,
            depth: .measured(.init(minimum: depth, maximum: depth)), fingerCapacity: 3), side: $0) }
    }

    private func contact(id: String, name: String, depth: Double, capacity: Int = 4,
                         grip: Set<GripType> = [.halfCrimp], side: ContactSide? = nil,
                         handCapacity: Int = 1) -> PhysicalContact {
        PhysicalContact(id: id, name: name, kind: .edge, fingerCapacity: capacity, handCapacity: handCapacity,
            depth: .range(.init(minimum: depth, maximum: depth)), gripTypes: grip, side: side)
    }

    private func fixtureBoard(id: String = "board", contacts: [PhysicalContact]? = nil,
                              extraContacts: [PhysicalContact] = [], handCapacity: Int = 2,
                              frames: [String: CGRect] = [:]) -> BoardRevision {
        let contacts = (contacts ?? [contact(id: "left-20", name: "20 mm left", depth: 20, side: .left),
                                    contact(id: "right-20", name: "20 mm right", depth: 20, side: .right)]) + extraContacts
        let geometry = Dictionary(uniqueKeysWithValues: contacts.enumerated().map { index, contact in
            (contact.id, [BoardContactPiece(id: contact.id + "-piece", contactID: contact.id,
                frame: frames[contact.id] ?? CGRect(x: index == 0 ? 0.1 : 0.8, y: 0.2, width: 0.1, height: 0.1),
                shape: .roundedRect(cornerRadiusFraction: 0), treatment: .surface)])
        })
        let presentation = BoardPresentation(id: "front", name: "Front", aspectRatio: 2, isDefault: true,
            media: .raster(BoardRasterMedia(assetPath: "", contactGeometry: geometry)))
        return BoardRevision(id: id, revisionID: "v1", manufacturer: "Fixture", name: "Fixture", subtitle: "", dimensions: nil,
            aspectRatio: 2, handCapacity: handCapacity, contacts: contacts,
            productURL: URL(string: "https://example.com/board")!, photoAssetName: nil, presentations: [presentation])
    }
}
