import XCTest
@testable import HangTen

final class ContactResolverTests: XCTestCase {
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
            LegacyPlanSeedCatalog.maxHangs.steps.first { $0.id == "max-hangs-1" }
        )
        let sessionStep = try XCTUnwrap(
            step.resolvingEitherHand(selectedHandSide: .left, boardIsOneHanded: board.isOneHanded)
        )
        let resolved = try ContactResolver.resolve(
            sessionStep.workRequirements,
            step: sessionStep,
            board: board
        )
        XCTAssertEqual(Set(resolved.map(\.kind)), [.edge])
        XCTAssertTrue(resolved.allSatisfy {
            $0.depth == .range(.init(minimum: 20, maximum: 20))
        })
        XCTAssertEqual(
            WorkoutHighlightResolver.contactIDs(for: sessionStep, on: board),
            resolved.map(\.id)
        )
    }

    func testMetoliusEntryHighlightsJugAndMediumEdgeOnDual() throws {
        let board = try XCTUnwrap(BoardCatalog.packageStore.board(id: "captain-fingerfood.dual"))
        let jugStep = try XCTUnwrap(
            LegacyPlanSeedCatalog.metoliusEntry.steps.first { $0.id == "entry.minute-1.task-1" }
        )
        let mediumStep = try XCTUnwrap(
            LegacyPlanSeedCatalog.metoliusEntry.steps.first { $0.id == "entry.minute-3.task-1" }
        )

        XCTAssertEqual(
            WorkoutHighlightResolver.contactIDs(for: jugStep, on: board),
            ["outer-jug"]
        )
        let mediumIDs = WorkoutHighlightResolver.contactIDs(for: mediumStep, on: board)
        XCTAssertEqual(mediumIDs.count, 1)
        XCTAssertTrue(mediumIDs[0] == "curved-edge-20" || mediumIDs[0] == "straight-edge-20")
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
        gripTypes: Set<GripType> = [.openHand]
    ) -> BoardRevision {
        let contacts = [
            PhysicalContact(
                id: "edge-right",
                name: "Right edge",
                kind: .edge,
                fingerCapacity: rightFingerCapacity,
                handCapacity: rightHandCapacity,
                depth: .range(.init(minimum: rightDepth.lowerBound, maximum: rightDepth.upperBound)),
                gripTypes: gripTypes
            ),
            PhysicalContact(
                id: "edge-left",
                name: "Left edge",
                kind: .edge,
                fingerCapacity: leftFingerCapacity,
                handCapacity: leftHandCapacity,
                depth: .range(.init(minimum: 20, maximum: 20)),
                gripTypes: gripTypes
            ),
            PhysicalContact(
                id: "edge-deep",
                name: "Deep edge",
                kind: .edge,
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
