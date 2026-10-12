import XCTest
@testable import HangTen

final class PlanHoldSubstitutionTests: XCTestCase {
    func testNearbyDepthRequiresAnExplicitHoldSelection() throws {
        let board = fixtureBoard(contacts: [
            contact(id: "left-19", name: "19 mm left", depth: 19, side: .left),
            contact(id: "right-19", name: "19 mm right", depth: 19, side: .right)
        ])
        let source = fixturePlan(steps: [fixtureStep(target: .tasks([task(depth: 20)]))])
        let request = try XCTUnwrap(PlanHoldSubstitutions.requests(for: source, on: board).first)
        XCTAssertNil(PlanHoldSubstitutions.applying([:], to: source, on: board))
        let option = try XCTUnwrap(request.options.first)
        XCTAssertEqual(option.label, "19 mm edge")
        let session = try XCTUnwrap(PlanHoldSubstitutions.applying(
            [request.id: option.id], to: source, on: board))
        XCTAssertEqual(Set(WorkoutHighlightResolver.contactIDs(for: session.steps[0], on: board)),
                       ["left-19", "right-19"])
        XCTAssertEqual(session.provenance, .adapted)
        XCTAssertTrue(session.steps[0].instruction.contains(source.steps[0].instruction))
    }

    func testMatchingPairLabelsRemoveInteriorAndHyphenatedSideWordsWithoutLosingHoldFacts() throws {
        let cases: [(HoldKind, Int, String, String, String)] = [
            (.edge, 4, "Outer left middle edge", "Outer RIGHT middle edge", "Outer middle edge"),
            (.pocket, 2, "Face A LEFT dual-finger pocket", "Face A right dual-finger pocket", "Face A dual-finger pocket"),
            (.sloper, 4, "Left-center macro sloper region", "RIGHT-center macro sloper region", "center macro sloper region"),
            (.sloper, 4, "Macro sloper center-left region", "Macro sloper center-RIGHT region", "Macro sloper center region"),
            (.edge, 4, "Upright outer edge LEFT", "Upright outer edge RIGHT", "Upright outer edge")
        ]
        for (kind, capacity, leftName, rightName, expectedLabel) in cases {
            let contacts = [
                PhysicalContact(id: "left", name: leftName, kind: kind, fingerCapacity: capacity,
                    handCapacity: 1, side: .left),
                PhysicalContact(id: "right", name: rightName, kind: kind, fingerCapacity: capacity,
                    handCapacity: 1, side: .right)
            ]
            let board = fixtureBoard(contacts: contacts)
            let predicate = PlanContactPredicate(kind: kind, depth: .measured(.init(minimum: 10, maximum: 10)))
            let source = fixturePlan(steps: [fixtureStep(target: .tasks([[
                .init(target: predicate, side: .left), .init(target: predicate, side: .right)
            ]]), grip: nil)])
            let request = try XCTUnwrap(PlanHoldSubstitutions.requests(for: source, on: board).first)
            XCTAssertEqual(request.options.count, 1)
            let option = try XCTUnwrap(request.options.first)
            XCTAssertEqual(option.label, expectedLabel)
            let session = try XCTUnwrap(PlanHoldSubstitutions.applying([request.id: option.id], to: source, on: board))
            XCTAssertEqual(Set(WorkoutHighlightResolver.contactIDs(for: session.steps[0], on: board)), ["left", "right"])
            let recorded = try XCTUnwrap(try WorkoutActivityRecorder().segments(for: session, on: board)
                .first { $0.kind == .work })
            XCTAssertEqual(recorded.target?.resolvedContactSnapshot?.contactIDs, ["left", "right"])
        }
    }

    func testMixedHandReplacementLabelsKeepAssignmentsAfterRemovingSideWordsFromHoldNames() throws {
        let board = fixtureBoard(contacts: [
            PhysicalContact(id: "left-edge", name: "Outer LEFT middle edge", kind: .edge,
                fingerCapacity: 4, handCapacity: 1, side: .left),
            PhysicalContact(id: "right-pocket", name: "Face A right dual-finger pocket", kind: .pocket,
                fingerCapacity: 2, handCapacity: 1, side: .right)
        ])
        let source = fixturePlan(steps: [fixtureStep(target: .tasks([[
            .init(target: .init(kind: .edge, depth: .measured(.init(minimum: 10, maximum: 10))), side: .left),
            .init(target: .init(kind: .pocket, depth: .measured(.init(minimum: 10, maximum: 10)), fingerCapacity: 2), side: .right)
        ]]), grip: nil)])
        let request = try XCTUnwrap(PlanHoldSubstitutions.requests(for: source, on: board).first)
        XCTAssertEqual(request.options.count, 1)
        let option = try XCTUnwrap(request.options.first)
        XCTAssertEqual(option.label, "Left: Outer middle edge · Right: Face A dual-finger pocket")
        let session = try XCTUnwrap(PlanHoldSubstitutions.applying([request.id: option.id], to: source, on: board))
        let task = try XCTUnwrap(session.steps[0].segments[0].target?.planTasks?.first)
        XCTAssertEqual(task.map(\.side), [.left, .right])
        XCTAssertEqual(try ContactResolver.resolve(task, step: session.steps[0], board: board).map(\.id),
            ["left-edge", "right-pocket"])
    }

    func testMatchingEdgeReplacementsPreferValidEdgePairsOverOtherHoldKinds() throws {
        let board = fixtureBoard(contacts: [
            contact(id: "left-edge", name: "Left 20 mm edge", depth: 20, side: .left),
            contact(id: "right-edge", name: "Right 20 mm edge", depth: 20, side: .right),
            PhysicalContact(id: "left-pocket", name: "Left 30 mm pocket", kind: .pocket,
                fingerCapacity: 4, handCapacity: 1, depth: .range(.init(minimum: 30, maximum: 30)), side: .left),
            PhysicalContact(id: "right-pocket", name: "Right 30 mm pocket", kind: .pocket,
                fingerCapacity: 4, handCapacity: 1, depth: .range(.init(minimum: 30, maximum: 30)), side: .right),
            PhysicalContact(id: "left-sloper", name: "Left 40 mm sloper", kind: .sloper,
                fingerCapacity: 4, handCapacity: 1, depth: .range(.init(minimum: 40, maximum: 40)), side: .left),
            PhysicalContact(id: "right-sloper", name: "Right 40 mm sloper", kind: .sloper,
                fingerCapacity: 4, handCapacity: 1, depth: .range(.init(minimum: 40, maximum: 40)), side: .right)
        ], frames: [
            "left-pocket": CGRect(x: 0.1, y: 0.4, width: 0.1, height: 0.1),
            "left-sloper": CGRect(x: 0.1, y: 0.6, width: 0.1, height: 0.1)
        ])
        let targets: [WorkoutSegmentTarget] = [
            .tasks([task(depth: 10, sides: [.left, .right])]),
            .requirements([.edge(depth: .range(.init(minimum: 10, maximum: 10)), selection: .bilateralPair)])
        ]
        for target in targets {
            let source = fixturePlan(steps: [fixtureStep(target: target)])
            let request = try XCTUnwrap(PlanHoldSubstitutions.requests(for: source, on: board).first)
            XCTAssertEqual(request.options.map(\.label), ["20 mm edge"])
            let option = try XCTUnwrap(request.options.first)
            let session = try XCTUnwrap(PlanHoldSubstitutions.applying([request.id: option.id], to: source, on: board))
            XCTAssertEqual(Set(WorkoutHighlightResolver.contactIDs(for: session.steps[0], on: board)),
                ["left-edge", "right-edge"])
        }
    }

    func testSingleHandWrongSideEdgeDoesNotSuppressAValidOtherKindReplacement() throws {
        let board = fixtureBoard(contacts: [
            contact(id: "left-edge", name: "Left 20 mm edge", depth: 20, side: .left),
            PhysicalContact(id: "right-pocket", name: "Right 30 mm pocket", kind: .pocket,
                fingerCapacity: 4, handCapacity: 1, depth: .range(.init(minimum: 30, maximum: 30)), side: .right)
        ])
        let targets: [WorkoutSegmentTarget] = [
            .tasks([task(depth: 10, sides: [.right])]),
            .requirements([.edge(depth: .range(.init(minimum: 10, maximum: 10)))])
        ]
        for target in targets {
            let source = fixturePlan(steps: [fixtureStep(target: target, handUse: .single, side: .right)])
            let request = try XCTUnwrap(PlanHoldSubstitutions.requests(for: source, on: board).first)
            XCTAssertEqual(request.options.map(\.label), ["30 mm four-finger pocket"])
            let option = try XCTUnwrap(request.options.first)
            let session = try XCTUnwrap(PlanHoldSubstitutions.applying([request.id: option.id], to: source, on: board))
            XCTAssertEqual(WorkoutHighlightResolver.contactIDs(for: session.steps[0], on: board), ["right-pocket"])
        }
    }

    func testSingleHandReplacementsPreferTheMatchingKindOnTheRequestedSide() throws {
        for side in [WorkoutSide.left, .right] {
            let contactSide: ContactSide = side == .left ? .left : .right
            let board = fixtureBoard(contacts: [
                contact(id: "edge", name: "20 mm edge", depth: 20, side: contactSide),
                PhysicalContact(id: "pocket", name: "30 mm pocket", kind: .pocket,
                    fingerCapacity: 4, handCapacity: 1, depth: .range(.init(minimum: 30, maximum: 30)), side: contactSide)
            ])
            let targets: [WorkoutSegmentTarget] = [
                .tasks([task(depth: 10, sides: [side])]),
                .requirements([.edge(depth: .range(.init(minimum: 10, maximum: 10)))])
            ]
            for target in targets {
                let source = fixturePlan(steps: [fixtureStep(target: target, handUse: .single, side: side)])
                let request = try XCTUnwrap(PlanHoldSubstitutions.requests(for: source, on: board).first)
                XCTAssertEqual(request.options.map(\.label), ["20 mm edge"])
                let option = try XCTUnwrap(request.options.first)
                let session = try XCTUnwrap(PlanHoldSubstitutions.applying([request.id: option.id], to: source, on: board))
                XCTAssertEqual(WorkoutHighlightResolver.contactIDs(for: session.steps[0], on: board), ["edge"])
            }
        }
    }

    func testMissingMatchingEdgePairKeepsValidOtherHoldKindsAsFallbacks() throws {
        let board = fixtureBoard(contacts: [
            contact(id: "left-edge", name: "Left 20 mm edge", depth: 20, side: .left),
            PhysicalContact(id: "left-pocket", name: "Left 30 mm pocket", kind: .pocket,
                fingerCapacity: 4, handCapacity: 1, depth: .range(.init(minimum: 30, maximum: 30)), side: .left),
            PhysicalContact(id: "right-pocket", name: "Right 30 mm pocket", kind: .pocket,
                fingerCapacity: 4, handCapacity: 1, depth: .range(.init(minimum: 30, maximum: 30)), side: .right),
            PhysicalContact(id: "left-sloper", name: "Left 40 mm sloper", kind: .sloper,
                fingerCapacity: 4, handCapacity: 1, depth: .range(.init(minimum: 40, maximum: 40)), side: .left),
            PhysicalContact(id: "right-sloper", name: "Right 40 mm sloper", kind: .sloper,
                fingerCapacity: 4, handCapacity: 1, depth: .range(.init(minimum: 40, maximum: 40)), side: .right)
        ], frames: [
            "left-pocket": CGRect(x: 0.1, y: 0.4, width: 0.1, height: 0.1),
            "left-sloper": CGRect(x: 0.1, y: 0.6, width: 0.1, height: 0.1)
        ])
        let targets: [WorkoutSegmentTarget] = [
            .tasks([task(depth: 10, sides: [.left, .right])]),
            .requirements([.edge(depth: .range(.init(minimum: 10, maximum: 10)), selection: .bilateralPair)])
        ]
        for target in targets {
            let source = fixturePlan(steps: [fixtureStep(target: target)])
            let request = try XCTUnwrap(PlanHoldSubstitutions.requests(for: source, on: board).first)
            XCTAssertEqual(Set(request.options.map(\.label)), ["30 mm four-finger pocket", "40 mm sloper"])
            for option in request.options {
                let session = try XCTUnwrap(PlanHoldSubstitutions.applying([request.id: option.id], to: source, on: board))
                let expected: Set<String> = option.label == "40 mm sloper"
                    ? ["left-sloper", "right-sloper"] : ["left-pocket", "right-pocket"]
                XCTAssertEqual(Set(WorkoutHighlightResolver.contactIDs(for: session.steps[0], on: board)), expected)
            }
        }
    }

    func testMixedHandReplacementsPreserveEveryRequiredKindAndTaskOrderWhenPossible() throws {
        let board = fixtureBoard(contacts: [
            contact(id: "left-edge", name: "Left 20 mm edge", depth: 20, side: .left),
            contact(id: "right-edge", name: "Right 20 mm edge", depth: 20, side: .right),
            PhysicalContact(id: "left-pocket", name: "Left 30 mm pocket", kind: .pocket,
                fingerCapacity: 4, handCapacity: 1, depth: .range(.init(minimum: 30, maximum: 30)), side: .left),
            PhysicalContact(id: "right-pocket", name: "Right 30 mm pocket", kind: .pocket,
                fingerCapacity: 4, handCapacity: 1, depth: .range(.init(minimum: 30, maximum: 30)), side: .right)
        ], frames: ["left-pocket": CGRect(x: 0.1, y: 0.4, width: 0.1, height: 0.1)])
        let task: [PlanHandTarget] = [
            .init(target: .init(kind: .edge, depth: .measured(.init(minimum: 10, maximum: 10))), side: .left),
            .init(target: .init(kind: .pocket, depth: .measured(.init(minimum: 10, maximum: 10))), side: .right)
        ]
        for hands in [task, Array(task.reversed())] {
            let source = fixturePlan(steps: [fixtureStep(target: .tasks([hands]))])
            let request = try XCTUnwrap(PlanHoldSubstitutions.requests(for: source, on: board).first)
            XCTAssertEqual(request.options.count, 1)
            let option = try XCTUnwrap(request.options.first)
            let expectedLabel = hands[0].side == .left
                ? "Left: 20 mm edge · Right: 30 mm four-finger pocket"
                : "Right: 30 mm four-finger pocket · Left: 20 mm edge"
            XCTAssertEqual(option.label, expectedLabel)
            let session = try XCTUnwrap(PlanHoldSubstitutions.applying([request.id: option.id], to: source, on: board))
            let selected = try XCTUnwrap(session.steps[0].segments[0].target?.planTasks?.first)
            XCTAssertEqual(selected.map { $0.target?.kind }, hands.map { $0.target?.kind })
            XCTAssertEqual(selected.map(\.side), hands.map(\.side))
        }
    }

    func testPreservingAllMixedTaskKindsTakesPriorityOverKeepingOneExactTarget() throws {
        let base = fixtureBoard(contacts: [
            contact(id: "left-edge", name: "Left edge", depth: 20, side: .left),
            contact(id: "right-edge", name: "Right edge", depth: 20, side: .right),
            PhysicalContact(id: "right-pocket", name: "Right pocket", kind: .pocket,
                fingerCapacity: 4, handCapacity: 1, depth: .range(.init(minimum: 40, maximum: 40)), side: .right)
        ])
        let pair = fixtureBoard(contacts: Array(base.contacts.prefix(2)))
        let mixed = fixtureBoard(contacts: [base.contacts[0], base.contacts[2]])
        let board = BoardRevision(id: base.id, revisionID: base.revisionID,
            manufacturer: base.manufacturer, name: base.name, subtitle: base.subtitle,
            dimensions: nil, aspectRatio: base.aspectRatio, contacts: base.contacts,
            productURL: base.productURL, photoAssetName: nil, presentations: [
                .init(id: "edge-pair-front", name: "Edge pair", aspectRatio: 2, isDefault: true,
                    media: pair.defaultPresentation.media),
                .init(id: "edge-pocket-front", name: "Edge and pocket", aspectRatio: 2, isDefault: false,
                    media: mixed.defaultPresentation.media)
            ],
            positions: [
                .init(id: "edge-pair", presentationID: "edge-pair-front", contactIDs: ["left-edge", "right-edge"],
                    effectiveDepths: ["left-edge": .range(.init(minimum: 20, maximum: 20)),
                        "right-edge": .range(.init(minimum: 20, maximum: 20))]),
                .init(id: "edge-pocket", presentationID: "edge-pocket-front", contactIDs: ["left-edge", "right-pocket"],
                    effectiveDepths: ["left-edge": .range(.init(minimum: 30, maximum: 30))])
            ])
        let source = fixturePlan(steps: [fixtureStep(target: .tasks([[
            .init(target: .init(kind: .edge, depth: .measured(.init(minimum: 20, maximum: 20))), side: .left),
            .init(target: .init(kind: .pocket, depth: .measured(.init(minimum: 10, maximum: 10))), side: .right)
        ]]))])
        let request = try XCTUnwrap(PlanHoldSubstitutions.requests(for: source, on: board).first)
        XCTAssertEqual(request.options.map(\.label), ["Left: 30 mm edge · Right: 40 mm four-finger pocket"])
        let option = try XCTUnwrap(request.options.first)
        let session = try XCTUnwrap(PlanHoldSubstitutions.applying([request.id: option.id], to: source, on: board))
        let selected = try XCTUnwrap(session.steps[0].segments[0].target?.planTasks?.first)
        let resolution = try ContactResolver.resolveSelection(selected, step: session.steps[0], board: board)
        XCTAssertEqual(resolution.positionID, "edge-pocket")
        XCTAssertEqual(resolution.contacts.map(\.id), ["left-edge", "right-pocket"])
    }

    func testUnspecifiedRequiredKindDoesNotImposeAnInferredHoldKindPreference() throws {
        let board = fixtureBoard(contacts: [
            contact(id: "edge", name: "20 mm edge", depth: 20, side: .right),
            PhysicalContact(id: "pocket", name: "30 mm pocket", kind: .pocket,
                fingerCapacity: 4, handCapacity: 1, depth: .range(.init(minimum: 30, maximum: 30)), side: .right)
        ])
        let source = fixturePlan(steps: [fixtureStep(target: .tasks([[
            .init(target: .init(depth: .measured(.init(minimum: 10, maximum: 10))), side: .right)
        ]]), handUse: .single, side: .right)])
        let request = try XCTUnwrap(PlanHoldSubstitutions.requests(for: source, on: board).first)
        XCTAssertEqual(request.options.map(\.label), ["20 mm edge", "30 mm four-finger pocket"])
    }

    func testSelfSelectedHandDoesNotPreventPreservingTheOtherHandsRequiredKind() throws {
        let board = fixtureBoard(contacts: [
            contact(id: "left-edge", name: "Left 20 mm edge", depth: 20, side: .left),
            contact(id: "right-edge", name: "Right 20 mm edge", depth: 20, side: .right),
            PhysicalContact(id: "right-pocket", name: "Right 30 mm pocket", kind: .pocket,
                fingerCapacity: 4, handCapacity: 1, depth: .range(.init(minimum: 30, maximum: 30)), side: .right)
        ])
        let source = fixturePlan(steps: [fixtureStep(target: .tasks([[
            .init(side: .left),
            .init(target: .init(kind: .edge, depth: .measured(.init(minimum: 10, maximum: 10))), side: .right)
        ]]))])
        let request = try XCTUnwrap(PlanHoldSubstitutions.requests(for: source, on: board).first)
        XCTAssertEqual(request.options.count, 1)
        let option = try XCTUnwrap(request.options.first)
        let selected = try XCTUnwrap(option.target.planTasks?.first)
        XCTAssertNil(selected[0].target)
        XCTAssertEqual(selected[0].side, .left)
        XCTAssertEqual(selected[1].target?.kind, .edge)
        XCTAssertEqual(selected[1].side, .right)
    }

    func testMatchingPairPickerDescribesTheHoldOnceAndAppliesBothContacts() throws {
        let board = fixtureBoard(extraContacts: [
            contact(id: "left-30", name: "Left 30 mm edge", depth: 30, side: .left),
            contact(id: "right-30", name: "Right 30 mm edge", depth: 30, side: .right),
            contact(id: "left-40", name: "Left 40 mm edge", depth: 40, side: .left)
        ])
        let source = fixturePlan(steps: [fixtureStep()])
        let request = try XCTUnwrap(PlanHoldSubstitutions.requests(for: source, on: board).first)
        XCTAssertEqual(request.requiredHoldLabel, "10 mm edge")
        XCTAssertEqual(request.options.map(\.label), ["20 mm edge", "30 mm edge"])
        let option = try XCTUnwrap(request.options.first { $0.label == "30 mm edge" })
        let session = try XCTUnwrap(PlanHoldSubstitutions.applying([request.id: option.id], to: source, on: board))
        XCTAssertEqual(Set(WorkoutHighlightResolver.contactIDs(for: session.steps[0], on: board)),
            ["left-30", "right-30"])
        let work = try XCTUnwrap(try WorkoutActivityRecorder().segments(for: session, on: board).first { $0.kind == .work })
        XCTAssertEqual(Set(work.target?.resolvedContactSnapshot?.contactIDs ?? []), ["left-30", "right-30"])
        XCTAssertEqual(session.steps[0].gripType, .halfCrimp)
    }

    func testSingleSidePickerNamesTheHoldAndUsesTheRequestedHand() throws {
        let board = fixtureBoard(contacts: [
            contact(id: "left-20", name: "Left 20 mm edge", depth: 20, side: .left),
            contact(id: "right-30", name: "Right 30 mm edge", depth: 30, side: .right),
            contact(id: "center-25", name: "Centered 25 mm edge", depth: 25)
        ], frames: ["center-25": CGRect(x: 0.45, y: 0.2, width: 0.1, height: 0.1)])
        let source = fixturePlan(steps: [fixtureStep(target: .tasks([task(depth: 10, sides: [.right])]),
            handUse: .single, side: .right)])
        let request = try XCTUnwrap(PlanHoldSubstitutions.requests(for: source, on: board).first)
        XCTAssertEqual(request.requiredHoldLabel, "10 mm edge")
        XCTAssertEqual(request.options.map(\.label), ["25 mm edge", "30 mm edge"])
        let option = try XCTUnwrap(request.options.first { $0.label == "30 mm edge" })
        let session = try XCTUnwrap(PlanHoldSubstitutions.applying([request.id: option.id], to: source, on: board))
        XCTAssertEqual(WorkoutHighlightResolver.contactIDs(for: session.steps[0], on: board), ["right-30"])
        XCTAssertEqual(session.steps[0].segments[0].target?.planTasks?.first?.first?.side, .right)
    }

    func testPocketChoicesKeepTheirFactualFingerCapacityWithoutHandLabels() throws {
        let capacities: [Int] = [2, 3]
        let contacts = capacities.flatMap { fingers in
            [ContactSide.left, .right].map { side in
                PhysicalContact(id: "pocket-\(fingers)-\(side.rawValue)",
                    name: "\(side.rawValue.capitalized) 20 mm \(fingers)-finger pocket", kind: .pocket,
                    fingerCapacity: fingers, handCapacity: 1,
                    depth: .range(.init(minimum: 20, maximum: 20)), gripTypes: [.halfCrimp], side: side)
            }
        }
        let board = fixtureBoard(contacts: contacts)
        let predicate = PlanContactPredicate(kind: .pocket, depth: .measured(.init(minimum: 10, maximum: 10)))
        let source = fixturePlan(steps: [fixtureStep(target: .tasks([[.init(target: predicate), .init(target: predicate)]]))])
        let request = try XCTUnwrap(PlanHoldSubstitutions.requests(for: source, on: board).first)
        XCTAssertEqual(Set(request.options.map(\.label)), ["20 mm two-finger pocket", "20 mm three-finger pocket"])
        for option in request.options {
            let session = try XCTUnwrap(PlanHoldSubstitutions.applying([request.id: option.id], to: source, on: board))
            let ids = Set(WorkoutHighlightResolver.contactIDs(for: session.steps[0], on: board))
            let fingers = option.label == "20 mm two-finger pocket" ? 2 : 3
            XCTAssertEqual(ids, ["pocket-\(fingers)-left", "pocket-\(fingers)-right"])
        }
    }

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
        let option = try XCTUnwrap(request.options.first { $0.label == "20 mm edge" })
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
        XCTAssertEqual(option.label, "20 mm edge")
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
            let option = try XCTUnwrap(request.options.first { $0.label == "\(depth) mm edge" })
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
        XCTAssertTrue(session.steps[0].instruction.contains("30 mm edge"))
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
        XCTAssertTrue(session.steps[0].instruction.contains("30 mm edge"))
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
        XCTAssertEqual(request.requiredHoldLabel, "10 mm edge")
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
            XCTAssertTrue(request.options.contains { $0.label.contains("edge") && $0.label.contains(depth) })
        }
    }

    private func fixturePlan(steps: [WorkoutStep]) -> TrainingPlan {
        var plan = TrainingPlan(id: "source", title: "Source", subtitle: "", level: "Entry", sourceLabel: "Manufacturer",
            sourceURL: URL(string: "https://example.com/source"), provenance: .official, boardID: nil, steps: steps)
        plan.stepRepeats = [WorkoutStepRepeat(stepRange: 0..<steps.count, repeatCount: steps.count)]
        return plan
    }

    private func fixtureStep(id: String = "first", target: WorkoutSegmentTarget? = nil,
                             grip: GripType? = .halfCrimp, fingers: FingerConfiguration? = nil,
                             handUse: WorkoutHandUse = .double, side: WorkoutSide = .both) -> WorkoutStep {
        WorkoutStep(id: id, number: 1, title: id, instruction: "Source instruction.", accessory: "Source accessory.",
            duration: 12, phase: .hang,
            segments: [WorkoutSegment(kind: .work, target: target ?? .tasks([task(depth: 10)]), timing: .fixed, duration: 10),
                       WorkoutSegment(kind: .rest, target: nil, timing: .fixed, duration: 2)],
            gripType: grip, fingerConfiguration: fingers, handUse: handUse, side: side,
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
