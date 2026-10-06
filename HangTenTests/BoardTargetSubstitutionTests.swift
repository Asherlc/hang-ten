import XCTest
@testable import HangTen

final class ContactResolverTests: XCTestCase {
    func testLopezMaxHangsOffersBothBeastmakersAndRecordsChosenEdges() throws {
        for (boardID, depth, ids, expectedCue) in [
            ("beastmaker-1000", 20.0, Set(["pocket-bottom-outer-left", "pocket-bottom-outer-right"]),
             "20 mm 4 Finger Edge Left, 20 mm 4 Finger Edge Right"),
            ("beastmaker-1000", 15.0, Set(["pocket-top-outer-left", "pocket-top-outer-right"]),
             "15 mm 4 Finger Edge Left, 15 mm 4 Finger Edge Right"),
            ("beastmaker-2000", 15.0, Set(["front-lower-1", "front-lower-9"]),
             "15 mm 4 Finger Edge Left, 15 mm 4 Finger Edge Right")
        ] {
            let board = try XCTUnwrap(BoardCatalog.packageStore.board(id: boardID))
            let plan = PlanCatalog.maxHangs
            XCTAssertTrue(MaxHangsEdgeSelection.availableDepths(for: plan, on: board).contains(depth))
            let selected = try XCTUnwrap(MaxHangsEdgeSelection.resolvedPlans(for: plan, on: board)[depth])
            let accessibleCue = try XCTUnwrap(BoardModelSurface.highlightedContactCue(
                for: board.contacts,
                highlightedContactIDs: ids
            ))
            XCTAssertEqual(accessibleCue, expectedCue, "\(boardID) / \(depth) mm")
            for step in selected.steps where !step.isRestStep {
                XCTAssertEqual(Set(WorkoutHighlightResolver.contactIDs(for: step, on: board)), ids)
            }
            let recorded = try WorkoutActivityRecorder().segments(for: selected, on: board)
            let work = recorded.filter { $0.kind == .work }
            XCTAssertEqual(work.count, 5)
            XCTAssertTrue(work.allSatisfy { $0.durationSeconds == 10 })
            for segment in work {
                guard case .resolvedContacts(let snapshot) = segment.target else {
                    return XCTFail("Selected edges must be recorded as resolved contacts")
                }
                XCTAssertEqual(Set(snapshot.contactIDs), ids)
            }
        }
    }

    func testLopezMaxHangsRejectsUnsupportedAndOutOfRangeEdgeSelections() throws {
        let board = try XCTUnwrap(BoardCatalog.packageStore.board(id: "beastmaker-2000"))
        XCTAssertNil(MaxHangsEdgeSelection.selecting(20, in: PlanCatalog.maxHangs, on: board))
        XCTAssertNil(MaxHangsEdgeSelection.selecting(22, in: PlanCatalog.maxHangs, on: board))
        XCTAssertNil(MaxHangsEdgeSelection.selecting(7, in: PlanCatalog.maxHangs, on: board))
        XCTAssertTrue(MaxHangsEdgeSelection.availableDepths(for: PlanCatalog.abrahangs, on: board).isEmpty)
    }

    func testCatalogSevenThreeCueUsesTwoHandsOnCompactBoard() throws {
        let board = try XCTUnwrap(BoardCatalog.packageStore.board(id: "metolius.wood-grips-compact-ii"))
        let plan = try XCTUnwrap(PlanCatalog.plan(id: "research.seven-three-repeaters"))
        let step = try XCTUnwrap(plan.steps.first { $0.phase == .hang && $0.title.contains("29 mm") })
        let tasks = try XCTUnwrap(step.segments.first?.target?.planTasks)
        XCTAssertEqual(tasks.first?.count, 2)
        XCTAssertEqual(
            Set(try ContactResolver.resolve(tasks[0], step: step, board: board).map(\.id)),
            ["edge-29-left", "edge-29-right"]
        )
    }

    func testEveryBoardSpecificCatalogTaskResolves() throws {
        for plan in PlanCatalog.all where plan.boardID != nil {
            let board = try XCTUnwrap(BoardCatalog.packageStore.board(id: plan.boardID!))
            for step in plan.steps {
                for segment in step.segments where segment.kind == .work {
                    guard let tasks = segment.target?.planTasks else { continue }
                    XCTAssertNoThrow(
                        try ContactResolver.resolve(tasks, step: step, board: board),
                        "\(plan.id) / \(step.id)"
                    )
                }
            }
        }
    }

    func testRepeatersFirstCueHighlightsBothCompactTwentyNineMillimeterEdges() throws {
        let board = try XCTUnwrap(
            BoardCatalog.packageStore.board(id: "metolius.wood-grips-compact-ii")
        )
        let step = try XCTUnwrap(CanonicalPlanSourceFixture.plan("research.seven-three-repeaters").steps.first)

        XCTAssertEqual(
            Set(WorkoutHighlightResolver.contactIDs(for: step, on: board)),
            ["edge-29-left", "edge-29-right"]
        )
    }

    func testThreeFingerEdgeRequirementAcceptsUnspecifiedAndLargerCapacities() throws {
        let requirement = ContactRequirement(
            kind: .edge,
            depth: .range(.init(minimum: 20, maximum: 20)),
            fingerCapacity: 3,
            selection: .bilateralPair
        )
        let step = fixtureStep(target: requirement)

        for capacity in [nil, 3, 4] as [Int?] {
            let board = fixtureBoard(
                rightFingerCapacity: capacity,
                leftFingerCapacity: capacity
            )

            XCTAssertEqual(
                Set(try ContactResolver.resolve(requirement, step: step, board: board).map(\.id)),
                ["edge-left", "edge-right"],
                "An edge with capacity \(String(describing: capacity)) should allow three fingers."
            )
        }
    }

    func testThreeFingerEdgeRequirementRejectsExplicitlySmallerCapacities() {
        let requirement = ContactRequirement(
            kind: .edge,
            depth: .range(.init(minimum: 20, maximum: 20)),
            fingerCapacity: 3,
            selection: .bilateralPair
        )
        let step = fixtureStep(target: requirement)

        for capacity in [1, 2] {
            let board = fixtureBoard(
                rightFingerCapacity: capacity,
                leftFingerCapacity: capacity
            )

            XCTAssertThrowsError(try ContactResolver.resolve(requirement, step: step, board: board)) {
                XCTAssertEqual($0 as? ContactResolutionError, .noMatches)
            }
        }
    }

    func testNamedPocketCapacityStillRequiresItsSpecifiedSize() throws {
        let requirement = ContactRequirement.kind(.pocket, fingerCapacity: 3, selection: .bilateralPair)
        let step = fixtureStep(target: requirement)

        for capacity in [nil, 2, 3, 4] as [Int?] {
            let board = fixtureBoard(
                rightFingerCapacity: capacity,
                leftFingerCapacity: capacity,
                contactKind: .pocket
            )

            if capacity == 3 {
                XCTAssertEqual(
                    Set(try ContactResolver.resolve(requirement, step: step, board: board).map(\.id)),
                    ["edge-left", "edge-right"]
                )
            } else {
                XCTAssertThrowsError(try ContactResolver.resolve(requirement, step: step, board: board)) {
                    XCTAssertEqual($0 as? ContactResolutionError, .noMatches)
                }
            }
        }
    }

    func testRepeatersRestPreviewsThreeFingerEdgesOnGrindstoneMk2() throws {
        let board = try XCTUnwrap(BoardCatalog.packageStore.board(id: "tension.grindstone"))
        let plan = try XCTUnwrap(PlanCatalog.plan(id: "research.seven-three-repeaters"))
        let rest = try XCTUnwrap(plan.steps.first {
            $0.id == "repeaters-grip-set-1-series-4-rep-3.segment-2"
        })
        let cue = WorkoutTimeline(steps: plan.steps).boardCue(
            currentStep: rest,
            stepElapsed: 1,
            countdown: 0,
            isComplete: false
        )
        let preview = try XCTUnwrap(cue.step)
        let contacts = WorkoutHighlightResolver.contacts(for: preview, on: board)

        XCTAssertTrue(cue.isResting)
        XCTAssertEqual(cue.mode, .preview)
        XCTAssertEqual(preview.fingerConfiguration?.engagedFingers, [.index, .middle, .ring])
        XCTAssertEqual(Set(contacts.map(\.id)).count, 2)
        XCTAssertTrue(contacts.allSatisfy { $0.kind == .edge })
    }

    func testResolutionFailuresDescribeSelectionOrGeometricPairingFailures() {
        XCTAssertEqual(
            ContactResolutionError.noMatches.errorDescription,
            "No physical contact satisfies the workout requirement."
        )
        XCTAssertEqual(
            ContactResolutionError.invalidBilateralPair(candidateCount: 2).errorDescription,
            "Hang Ten could not form a geometrically valid bilateral pair for the workout requirement."
        )
    }

    func testSingleSelectsTheCandidateNearestTheDefaultPresentationMidpoint() throws {
        let board = jugBoard([
            .init(id: "jug-left", frame: CGRect(x: 0.1, y: 0.4, width: 0.1, height: 0.1)),
            .init(id: "jug-center", frame: CGRect(x: 0.45, y: 0.4, width: 0.1, height: 0.1)),
            .init(id: "jug-right", frame: CGRect(x: 0.8, y: 0.4, width: 0.1, height: 0.1))
        ])
        let requirement = ContactRequirement.kind(.jug, selection: .single)

        XCTAssertEqual(
            try ContactResolver.resolve(requirement, step: fixtureStep(target: requirement), board: board).map(\.id),
            ["jug-center"]
        )
    }

    func testSingleBreaksEqualMidpointDistancesByContactID() throws {
        let board = jugBoard([
            .init(id: "jug-z", frame: CGRect(x: 0.125, y: 0.4, width: 0.25, height: 0.1)),
            .init(id: "jug-a", frame: CGRect(x: 0.625, y: 0.4, width: 0.25, height: 0.1))
        ])
        let requirement = ContactRequirement.kind(.jug, selection: .single)

        XCTAssertEqual(
            try ContactResolver.resolve(requirement, step: fixtureStep(target: requirement), board: board).map(\.id),
            ["jug-a"]
        )
    }

    func testBilateralPairSelectsTwoStraddlingCandidatesWithoutPairingMetadata() throws {
        let board = jugBoard([
            .init(id: "jug-left", frame: CGRect(x: 0.1, y: 0.4, width: 0.1, height: 0.1)),
            .init(id: "jug-right", frame: CGRect(x: 0.8, y: 0.4, width: 0.1, height: 0.1))
        ])
        let requirement = ContactRequirement.kind(.jug, selection: .bilateralPair)

        XCTAssertEqual(
            try ContactResolver.resolve(requirement, step: fixtureStep(target: requirement), board: board).map(\.id),
            ["jug-left", "jug-right"]
        )
    }

    func testBilateralPairRejectsTwoCandidatesOnTheSameSideOfThePresentationMidpoint() {
        let board = jugBoard([
            .init(id: "jug-near", frame: CGRect(x: 0.55, y: 0.4, width: 0.1, height: 0.1)),
            .init(id: "jug-far", frame: CGRect(x: 0.85, y: 0.4, width: 0.1, height: 0.1))
        ])
        let requirement = ContactRequirement.kind(.jug, selection: .bilateralPair)

        XCTAssertThrowsError(try ContactResolver.resolve(requirement, step: fixtureStep(target: requirement), board: board)) {
            XCTAssertEqual($0 as? ContactResolutionError, .invalidBilateralPair(candidateCount: 2))
        }
    }

    func testBilateralPairDerivesExtremaFromFrameCentersRatherThanEdges() throws {
        let board = jugBoard([
            .init(id: "jug-left", frame: CGRect(x: 0.1, y: 0.4, width: 0.1, height: 0.1)),
            .init(id: "jug-wide-right", frame: CGRect(x: 0.55, y: 0.4, width: 0.4, height: 0.1)),
            .init(id: "jug-narrow-right", frame: CGRect(x: 0.75, y: 0.4, width: 0.05, height: 0.1))
        ])
        let requirement = ContactRequirement.kind(.jug, selection: .bilateralPair)

        XCTAssertEqual(
            try ContactResolver.resolve(requirement, step: fixtureStep(target: requirement), board: board).map(\.id),
            ["jug-left", "jug-narrow-right"]
        )
    }

    func testSingleSelectsTheOnlyCandidateMatchingAnExactDepth() throws {
        let board = fixtureBoard()
        let requirement = ContactRequirement.edge(
            depth: .range(.init(minimum: 29, maximum: 31)),
            selection: .single
        )
        let step = fixtureStep(target: requirement)

        XCTAssertEqual(
            try ContactResolver.resolve(requirement, step: step, board: board).map(\.id),
            ["edge-deep"]
        )
    }

    func testBilateralPairSelectsOuterContactsFromDefaultPresentationWhenThreeJugsMatch() throws {
        let board = threeJugBoard()
        let requirement = ContactRequirement.kind(.jug, selection: .bilateralPair)
        let step = fixtureStep(target: requirement)

        XCTAssertEqual(
            try ContactResolver.resolve(requirement, step: step, board: board).map(\.id),
            ["jug-left", "jug-right"]
        )
    }

    func testBilateralPairRejectsThreeMatchingContactsOnOneSideOfPresentationMidpoint() {
        let board = jugBoard([
            .init(id: "jug-near", frame: CGRect(x: 0.55, y: 0.4, width: 0.1, height: 0.1)),
            .init(id: "jug-middle", frame: CGRect(x: 0.7, y: 0.4, width: 0.1, height: 0.1)),
            .init(id: "jug-far", frame: CGRect(x: 0.85, y: 0.4, width: 0.1, height: 0.1))
        ])
        let requirement = ContactRequirement.kind(.jug, selection: .bilateralPair)

        XCTAssertThrowsError(try ContactResolver.resolve(requirement, step: fixtureStep(target: requirement), board: board)) {
            XCTAssertEqual($0 as? ContactResolutionError, .invalidBilateralPair(candidateCount: 3))
        }
    }

    func testDerivedBilateralPairRejectsDifferentFactualDescriptors() {
        let board = jugBoard([
            .init(id: "jug-left", frame: CGRect(x: 0.1, y: 0.4, width: 0.1, height: 0.1), depth: 20...20),
            .init(id: "jug-center", frame: CGRect(x: 0.45, y: 0.4, width: 0.1, height: 0.1), depth: 20...20),
            .init(id: "jug-right", frame: CGRect(x: 0.8, y: 0.4, width: 0.1, height: 0.1), depth: 25...25)
        ])
        let requirement = ContactRequirement.kind(.jug, selection: .bilateralPair)

        XCTAssertThrowsError(try ContactResolver.resolve(requirement, step: fixtureStep(target: requirement), board: board)) {
            XCTAssertEqual($0 as? ContactResolutionError, .invalidBilateralPair(candidateCount: 3))
        }
    }

    func testBilateralPairRejectsContactsWithDifferentFactualDescriptors() {
        let board = fixtureBoard(rightDepth: 19...19)
        let requirement = ContactRequirement.edge(
            depth: .range(.init(minimum: 19, maximum: 21)),
            selection: .bilateralPair
        )
        let step = fixtureStep(target: requirement)

        XCTAssertThrowsError(try ContactResolver.resolve(requirement, step: step, board: board)) {
            XCTAssertEqual($0 as? ContactResolutionError, .invalidBilateralPair(candidateCount: 2))
        }
    }

    func testBilateralPairRejectsDifferentFingerCapacity() {
        let board = fixtureBoard(
            rightFingerCapacity: 3,
            leftFingerCapacity: 4
        )
        let requirement = ContactRequirement.edge(
            depth: .range(.init(minimum: 19, maximum: 21)),
            selection: .bilateralPair
        )
        let step = fixtureStep(target: requirement)

        XCTAssertThrowsError(try ContactResolver.resolve(requirement, step: step, board: board)) {
            XCTAssertEqual($0 as? ContactResolutionError, .invalidBilateralPair(candidateCount: 2))
        }
    }

    func testBilateralPairRejectsDifferentHandCapacity() {
        let board = fixtureBoard(
            rightHandCapacity: 1,
            leftHandCapacity: 2
        )
        let requirement = ContactRequirement.edge(
            depth: .range(.init(minimum: 19, maximum: 21)),
            selection: .bilateralPair
        )
        let step = fixtureStep(target: requirement)

        XCTAssertThrowsError(try ContactResolver.resolve(requirement, step: step, board: board)) {
            XCTAssertEqual($0 as? ContactResolutionError, .invalidBilateralPair(candidateCount: 2))
        }
    }

    func testResolutionUsesAllDefaultPresentationContactsNotOnlyFirstPosition() throws {
        // Authored membership lists only the left edge, matching Dual-style
        // multi-position packages where each pose owns a subset.
        let board = fixtureBoard(positionContactIDs: ["edge-left"])
        let requirement = ContactRequirement.edge(
            depth: .range(.init(minimum: 19, maximum: 21)),
            selection: .single
        )
        let step = fixtureStep(target: requirement)

        XCTAssertEqual(
            try ContactResolver.resolve(requirement, step: step, board: board).map(\.id),
            ["edge-left"]
        )
        // Both 20 mm edges remain candidates via presentation.contactIDs; the
        // single selector still picks a stable contact without requiring the
        // first authored position to list every hold.
        XCTAssertEqual(
            Set(board.defaultPresentation.contactIDs),
            Set(["edge-left", "edge-right", "edge-deep"])
        )
    }

    func testMaxHangsHighlightsDualTwentyMillimeterEdge() throws {
        let board = try XCTUnwrap(BoardCatalog.packageStore.board(id: "captain-fingerfood.dual"))
        let step = try XCTUnwrap(
            CanonicalPlanSourceFixture.plan("research.max-hangs").steps.first { $0.id == "max-hangs-1" }
        )
        let tasks = try XCTUnwrap(step.segments.first?.target?.planTasks)
        XCTAssertEqual(tasks.count, 1)
        let task = try XCTUnwrap(tasks.first)
        let sourceTarget = PlanHandTarget(target: .init(
            kind: .edge, depth: .measured(.init(minimum: 9, maximum: 19))
        ))
        XCTAssertEqual(task, [sourceTarget, sourceTarget])
        XCTAssertEqual(step.handUse, .double)
        XCTAssertTrue(board.isOneHanded)
        let resolved = try ContactResolver.resolve(
            task,
            step: step,
            board: board
        )
        // The source prescribes two hands. This one-hand board requires two
        // copies of the same selected physical edge, preserving both slots.
        XCTAssertEqual(resolved.count, 2)
        XCTAssertEqual(Set(resolved.map(\.id)).count, 1)
        XCTAssertEqual(Set(resolved.map(\.kind)), [.edge])
        XCTAssertTrue(resolved.allSatisfy {
            $0.depth == .range(.init(minimum: 20, maximum: 20))
        })
        XCTAssertEqual(
            WorkoutHighlightResolver.contactIDs(for: step, on: board),
            resolved.map(\.id)
        )
    }

    func testMetoliusEntryHighlightsJugAndMediumEdgeOnDual() throws {
        let board = try XCTUnwrap(BoardCatalog.packageStore.board(id: "captain-fingerfood.dual"))
        let jugStep = try XCTUnwrap(
            CanonicalPlanSourceFixture.plan("metolius.generic-ten-minute.entry").steps.first { $0.id == "entry.minute-1.task-1" }
        )
        let mediumStep = try XCTUnwrap(
            CanonicalPlanSourceFixture.plan("metolius.generic-ten-minute.entry").steps.first { $0.id == "entry.minute-3.task-1" }
        )

        XCTAssertTrue(board.isOneHanded)
        let jugTasks = try XCTUnwrap(jugStep.segments.first?.target?.planTasks)
        XCTAssertEqual(jugTasks.count, 1)
        let jugTask = try XCTUnwrap(jugTasks.first)
        XCTAssertEqual(jugTask, [
            PlanHandTarget(target: .init(kind: .jug)),
            PlanHandTarget(target: .init(kind: .jug))
        ])
        let jugIDs = try ContactResolver.resolve(jugTask, step: jugStep, board: board).map(\.id)
        XCTAssertEqual(jugIDs, ["outer-jug", "outer-jug"])
        XCTAssertEqual(WorkoutHighlightResolver.contactIDs(for: jugStep, on: board), jugIDs)
        let mediumTasks = try XCTUnwrap(mediumStep.segments.first?.target?.planTasks)
        XCTAssertEqual(mediumTasks.count, 1)
        let mediumTask = try XCTUnwrap(mediumTasks.first)
        XCTAssertEqual(mediumTask, [
            PlanHandTarget(target: .init(kind: .edge, depth: .category(.medium))),
            PlanHandTarget(target: .init(kind: .edge, depth: .category(.medium)))
        ])
        let mediumContacts = try ContactResolver.resolve(mediumTask, step: mediumStep, board: board)
        let mediumIDs = WorkoutHighlightResolver.contactIDs(for: mediumStep, on: board)
        XCTAssertEqual(mediumIDs, mediumContacts.map(\.id))
        XCTAssertEqual(mediumIDs.count, 2)
        XCTAssertEqual(Set(mediumIDs).count, 1)
        XCTAssertTrue(mediumIDs.allSatisfy { $0 == "curved-edge-20" || $0 == "straight-edge-20" })
    }

    func testEmptyContactGripTypesDoNotConstrainStepGrip() throws {
        let board = fixtureBoard(gripTypes: [])
        let requirement = ContactRequirement.edge(
            depth: .range(.init(minimum: 29, maximum: 31)),
            selection: .single
        )
        let step = fixtureStep(target: requirement, gripType: .halfCrimp)

        XCTAssertEqual(
            try ContactResolver.resolve(requirement, step: step, board: board).map(\.id),
            ["edge-deep"]
        )
    }

    func testStepGripConstraintRejectsIncompatibleNonEmptyContactGripMetadata() {
        let board = fixtureBoard(gripTypes: [.openHand])
        let requirement = ContactRequirement.edge(
            depth: .range(.init(minimum: 29, maximum: 31)),
            selection: .single
        )
        let step = fixtureStep(target: requirement, gripType: .halfCrimp)

        XCTAssertThrowsError(try ContactResolver.resolve(requirement, step: step, board: board)) {
            XCTAssertEqual($0 as? ContactResolutionError, .noMatches)
        }
    }

    func testSingleSelectionIgnoresUnilateralWorkoutSide() throws {
        let board = fixtureBoard()
        let requirement = ContactRequirement.edge(
            depth: .range(.init(minimum: 29, maximum: 31)),
            selection: .single
        )
        let step = fixtureStep(
            target: requirement,
            handUse: .single,
            side: .left
        )

        XCTAssertEqual(
            try ContactResolver.resolve(requirement, step: step, board: board).map(\.id),
            ["edge-deep"]
        )
    }

    func testSingleDoesNotGuessAmongMultipleCandidatesWithoutEveryDefaultPresentationFrame() throws {
        let board = jugBoard(
            [
                .init(id: "jug-left", frame: CGRect(x: 0.1, y: 0.4, width: 0.1, height: 0.1)),
                .init(id: "jug-center", frame: CGRect(x: 0.45, y: 0.4, width: 0.1, height: 0.1))
            ],
            missingGeometryContactIDs: ["jug-center"]
        )
        let requirement = ContactRequirement.kind(.jug, selection: .single)

        // Contacts missing default-presentation geometry are not candidates.
        XCTAssertEqual(
            try ContactResolver.resolve(requirement, step: fixtureStep(target: requirement), board: board).map(\.id),
            ["jug-left"]
        )
    }

    func testBilateralPairDoesNotGuessAmongCandidatesWithoutEveryDefaultPresentationFrame() {
        let board = jugBoard(
            [
                .init(id: "jug-left", frame: CGRect(x: 0.1, y: 0.4, width: 0.1, height: 0.1)),
                .init(id: "jug-right", frame: CGRect(x: 0.8, y: 0.4, width: 0.1, height: 0.1))
            ],
            missingGeometryContactIDs: ["jug-right"]
        )
        let requirement = ContactRequirement.kind(.jug, selection: .bilateralPair)

        XCTAssertThrowsError(try ContactResolver.resolve(requirement, step: fixtureStep(target: requirement), board: board)) {
            XCTAssertEqual($0 as? ContactResolutionError, .invalidBilateralPair(candidateCount: 1))
        }
    }

    func testMaxHangsResolvesPentaReusableTwentyMillimeterPairAndPose() throws {
        let board = try XCTUnwrap(BoardCatalog.packageStore.board(id: "yy.penta-evo"))
        // The source plan offers 8–20 mm; the athlete chooses the exact edge
        // through the production plan-page path before a session is resolved.
        let selected = try XCTUnwrap(MaxHangsEdgeSelection.resolvedPlans(
            for: PlanCatalog.maxHangs, on: board)[20])
        let step = try XCTUnwrap(selected.steps.first { !$0.isRestStep })
        let target = try XCTUnwrap(step.segments.first { $0.kind == .work }?.target)
        let resolved = try XCTUnwrap(ContactResolver.resolve(target, step: step, board: board).first)
        let expected: Set<String> = ["edge-20-left", "edge-20-right"]
        XCTAssertEqual(Set(resolved.map(\.id)), expected)
        XCTAssertEqual(Set(WorkoutHighlightResolver.contactIDs(for: step, on: board)), expected)
        for contact in resolved {
            XCTAssertEqual(contact.depth, .range(.init(minimum: 20, maximum: 20)))
            XCTAssertEqual(BoardMapPresentationSelection.resolvePositionID(
                board: board, presentationID: board.defaultPresentation.id, activeHoldID: contact.id
            ), "edge-20")
        }
    }

    func testExactPentaTasksUseAuthoredUnitPlacementInsteadOfInstanceArrayOrder() throws {
        let original = try XCTUnwrap(BoardCatalog.packageStore.board(id: "yy.penta-evo"))
        guard case .model(let media) = original.defaultPresentation.media else { return XCTFail("Native model expected") }
        let instances = try XCTUnwrap(media.instances)
        let target = PlanContactPredicate(kind: .edge, depth: .measured(.init(minimum: 20, maximum: 20)))
        let step = try XCTUnwrap(PlanCatalog.maxHangs.steps.first { !$0.isRestStep })
        for order in [instances, Array(instances.reversed())] {
            let reorderedMedia = BoardModelMedia(assetPath: media.assetPath, descriptorPath: media.descriptorPath,
                descriptor: media.descriptor, display: media.display, suspension: media.suspension,
                orientation: media.orientation, instances: order, physicsDescriptorPath: media.physicsDescriptorPath)
            let presentation = BoardPresentation(id: original.defaultPresentation.id,
                name: original.defaultPresentation.name, aspectRatio: original.defaultPresentation.aspectRatio,
                isDefault: true, media: .model(reorderedMedia))
            let board = BoardRevision(id: original.id, revisionID: original.revisionID,
                manufacturer: original.manufacturer, name: original.name, subtitle: original.subtitle,
                dimensions: original.dimensions, aspectRatio: original.aspectRatio,
                equipmentObjects: original.equipmentObjects, contacts: original.contacts,
                productURL: original.productURL, photoAssetName: nil,
                presentations: [presentation], positions: original.positions)
            for (sides, ids) in [
                ([WorkoutSide.left, .right], ["edge-20-left", "edge-20-right"]),
                ([WorkoutSide.right, .left], ["edge-20-right", "edge-20-left"])
            ] {
                let task = sides.map { PlanHandTarget(target: target, side: $0) }
                let selection = try ContactResolver.resolveSelection(task, step: step, board: board)
                XCTAssertEqual(selection.contacts.map(\.id), ids)
                XCTAssertEqual(selection.positionID, "edge-20")
            }
        }
    }

    func testPentaLegacyPairRequiresAnExactAthleteSelectedDepth() throws {
        let board = try XCTUnwrap(BoardCatalog.packageStore.board(id: "yy.penta-evo"))
        let step = try XCTUnwrap(CanonicalPlanSourceFixture.plan("research.max-hangs").steps.first { $0.id == "max-hangs-1" })
        let sourceTasks = try XCTUnwrap(step.segments.first?.target?.planTasks)
        XCTAssertEqual(sourceTasks.count, 1)
        let sourceTask = try XCTUnwrap(sourceTasks.first)
        let sourceTarget = PlanHandTarget(target: .init(
            kind: .edge, depth: .measured(.init(minimum: 9, maximum: 19))
        ))
        XCTAssertEqual(sourceTask, [sourceTarget, sourceTarget])
        // The broad source range matches three physical pairs. Do not invent
        // an automatic size choice in the legacy bilateral-pair API. Flattening
        // canonical hand tasks would discard this explicit selection contract.
        let broadPair = ContactRequirement.edge(depth: .range(.init(minimum: 9, maximum: 19)),
                                                selection: .bilateralPair)
        XCTAssertThrowsError(try ContactResolver.resolve(broadPair, step: step, board: board)) {
            XCTAssertEqual($0 as? ContactResolutionError, .invalidBilateralPair(candidateCount: 6))
        }
        let exact = ContactRequirement.edge(depth: .range(.init(minimum: 20, maximum: 20)),
                                            selection: .bilateralPair)
        XCTAssertEqual(Set(try ContactResolver.resolve(exact, step: step, board: board).map(\.id)),
                       ["edge-20-left", "edge-20-right"])
        let selectedHand = PlanHandTarget(target: .init(
            kind: .edge, depth: .measured(.init(minimum: 20, maximum: 20))
        ))
        let selectedTask = [selectedHand, selectedHand]
        let selection = try ContactResolver.resolveSelection(selectedTask, step: step, board: board)
        XCTAssertEqual(selection.contacts.map(\.id), ["edge-20-left", "edge-20-right"])
        XCTAssertEqual(selection.positionID, "edge-20")
    }

    func testReusablePairRejectsDifferentSlotsEvenWhenUnitFramesStraddleMidpoint() throws {
        let board = try reusablePairFixture(ids: ["edge-25-left", "edge-20-right"])
        try assertReusablePairRejected(board)
    }

    func testReusablePairRejectsSameInstanceEvenWhenUnitFramesStraddleMidpoint() throws {
        let board = try reusablePairFixture(ids: ["edge-25-left", "edge-20-left"])
        try assertReusablePairRejected(board)
    }

    func testReusablePairRejectsUnequalContactFacts() throws {
        for difference in ["kind", "shape", "depth", "fingerCapacity", "handCapacity"] {
            let board = try reusablePairFixture(ids: ["edge-20-left", "edge-20-right"], difference: difference)
            try assertReusablePairRejected(board)
        }
    }

    private func assertReusablePairRejected(_ board: BoardRevision) throws {
        // Both synthetic contacts match this broad requirement; the pairing
        // rules must reject them rather than silently choosing per-unit extrema.
        let requirement = ContactRequirement(selection: .bilateralPair)
        XCTAssertThrowsError(try ContactResolver.resolve(
            requirement, step: fixtureStep(target: requirement), board: board
        )) { XCTAssertEqual($0 as? ContactResolutionError, .invalidBilateralPair(candidateCount: 2)) }
    }

    private func reusablePairFixture(ids: [String], difference: String? = nil) throws -> BoardRevision {
        let original = try XCTUnwrap(BoardCatalog.packageStore.board(id: "yy.penta-evo"))
        let contacts = try ids.enumerated().map { index, id in
            let source = try XCTUnwrap(original.contacts.first { $0.id == id })
            let changed = index == 1 ? difference : nil
            // Synthetic facts isolate each pairing rule; production package
            // facts, mappings and per-unit descriptor frames remain untouched.
            return PhysicalContact(id: source.id, equipmentObjectID: source.equipmentObjectID,
                name: source.name, kind: changed == "kind" ? .jug : .edge,
                shape: changed == "shape" ? .round : .flat,
                fingerCapacity: changed == "fingerCapacity" ? 3 : 4,
                handCapacity: changed == "handCapacity" ? 2 : 1,
                depth: .range(.init(minimum: changed == "depth" ? 21 : 20,
                                   maximum: changed == "depth" ? 21 : 20)))
        }
        return BoardRevision(id: "fixture.reusable-pair", revisionID: "fixture",
            manufacturer: "Fixture", name: "Reusable pair", subtitle: "", dimensions: nil,
            aspectRatio: original.aspectRatio, equipmentObjects: original.equipmentObjects,
            contacts: contacts, productURL: original.productURL, photoAssetName: nil,
            presentations: original.presentations, positions: original.positions)
    }

    private func fixtureStep(
        target: ContactRequirement,
        gripType: GripType? = nil,
        handUse: WorkoutHandUse = .double,
        side: WorkoutSide = .both
    ) -> WorkoutStep {
        WorkoutStep(
            id: "fixture-step",
            number: 1,
            title: "Fixture",
            instruction: "",
            accessory: "",
            duration: 10,
            phase: .hang,
            gripType: gripType,
            handUse: handUse,
            side: side
        )
    }

    private func fixtureBoard(
        rightDepth: ClosedRange<Double> = 20...20,
        rightFingerCapacity: Int? = nil,
        leftFingerCapacity: Int? = nil,
        rightHandCapacity: Int? = nil,
        leftHandCapacity: Int? = nil,
        positionContactIDs: [String]? = nil,
        gripTypes: Set<GripType> = [.openHand],
        contactKind: HoldKind = .edge
    ) -> BoardRevision {
        let contacts = [
            PhysicalContact(
                id: "edge-right",
                name: "Right edge",
                kind: contactKind,
                fingerCapacity: rightFingerCapacity,
                handCapacity: rightHandCapacity,
                depth: .range(.init(minimum: rightDepth.lowerBound, maximum: rightDepth.upperBound)),
                gripTypes: gripTypes
            ),
            PhysicalContact(
                id: "edge-left",
                name: "Left edge",
                kind: contactKind,
                fingerCapacity: leftFingerCapacity,
                handCapacity: leftHandCapacity,
                depth: .range(.init(minimum: 20, maximum: 20)),
                gripTypes: gripTypes
            ),
            PhysicalContact(
                id: "edge-deep",
                name: "Deep edge",
                kind: contactKind,
                depth: .range(.init(minimum: 30, maximum: 30)),
                gripTypes: gripTypes
            )
        ]
        let geometry = Dictionary(uniqueKeysWithValues: contacts.map {
            let x: CGFloat
            switch $0.id {
            case "edge-left": x = 0.1
            case "edge-right": x = 0.8
            default: x = 0.45
            }
            return ($0.id, [BoardContactPiece(
                id: "\($0.id)-piece",
                contactID: $0.id,
                frame: CGRect(x: x, y: 0, width: 0.1, height: 0.1),
                shape: .roundedRect(cornerRadiusFraction: 0),
                treatment: .surface
            )])
        })
        let presentation = BoardPresentation(
            id: "front",
            name: "Front",
            aspectRatio: 2,
            isDefault: true,
            media: .raster(BoardRasterMedia(assetPath: "", contactGeometry: geometry))
        )
        return BoardRevision(
            id: "fixture.board",
            revisionID: "fixture-revision",
            manufacturer: "Fixture",
            name: "Board",
            subtitle: "",
            dimensions: nil,
            aspectRatio: 2,
            contacts: contacts,
            productURL: URL(string: "https://example.com/board")!,
            photoAssetName: nil,
            presentations: [presentation],
            positions: [
                BoardPosition(
                    id: "front",
                    presentationID: "front",
                    contactIDs: positionContactIDs ?? contacts.map(\.id)
                )
            ]
        )
    }

    private func threeJugBoard() -> BoardRevision {
        jugBoard([
            .init(id: "jug-left", frame: CGRect(x: 0.1, y: 0.4, width: 0.1, height: 0.1)),
            .init(id: "jug-center", frame: CGRect(x: 0.45, y: 0.4, width: 0.1, height: 0.1)),
            .init(id: "jug-right", frame: CGRect(x: 0.8, y: 0.4, width: 0.1, height: 0.1))
        ])
    }

    private struct JugFixture {
        let id: String
        let frame: CGRect
        let depth: ClosedRange<Double>?

        init(id: String, frame: CGRect, depth: ClosedRange<Double>? = nil) {
            self.id = id
            self.frame = frame
            self.depth = depth
        }
    }

    private func jugBoard(
        _ fixtures: [JugFixture],
        missingGeometryContactIDs: Set<String> = []
    ) -> BoardRevision {
        let contacts = fixtures.map {
            PhysicalContact(
                id: $0.id,
                name: $0.id,
                kind: .jug,
                depth: $0.depth.map { .range(.init(minimum: $0.lowerBound, maximum: $0.upperBound)) }
            )
        }
        let geometry = Dictionary(uniqueKeysWithValues: fixtures.filter {
            !missingGeometryContactIDs.contains($0.id)
        }.map {
            ($0.id, [BoardContactPiece(
                id: "\($0.id)-piece",
                contactID: $0.id,
                frame: $0.frame,
                shape: .roundedRect(cornerRadiusFraction: 0),
                treatment: .surface
            )])
        })
        let presentation = BoardPresentation(
            id: "front",
            name: "Front",
            aspectRatio: 2,
            isDefault: true,
            media: .raster(BoardRasterMedia(assetPath: "", contactGeometry: geometry))
        )
        return BoardRevision(
            id: "fixture.three-jug-board",
            revisionID: "fixture-revision",
            manufacturer: "Fixture",
            name: "Three jugs",
            subtitle: "",
            dimensions: nil,
            aspectRatio: 2,
            contacts: contacts,
            productURL: URL(string: "https://example.com/board")!,
            photoAssetName: nil,
            presentations: [presentation],
            positions: [BoardPosition(id: "front", presentationID: "front", contactIDs: contacts.map(\.id))]
        )
    }

}
