import XCTest
@testable import HangTen

final class ContactResolverTests: XCTestCase {
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

    func testSingleRequiresExactlyOneCandidate() throws {
        let board = fixtureBoard()
        let requirement = ContactRequirement.edge(
            depthRangeMillimeters: .init(minimum: 29, maximum: 31),
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
        let board = fixtureBoard(
            rightDepth: 19...19,
            documentsPair: true,
            documentsSides: true
        )
        let requirement = ContactRequirement.edge(
            depthRangeMillimeters: .init(minimum: 19, maximum: 21),
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
            leftFingerCapacity: 4,
            documentsPair: true,
            documentsSides: true
        )
        let requirement = ContactRequirement.edge(
            depthRangeMillimeters: .init(minimum: 19, maximum: 21),
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
            leftHandCapacity: 2,
            documentsPair: true,
            documentsSides: true
        )
        let requirement = ContactRequirement.edge(
            depthRangeMillimeters: .init(minimum: 19, maximum: 21),
            selection: .bilateralPair
        )
        let step = fixtureStep(target: requirement)

        XCTAssertThrowsError(try ContactResolver.resolve(requirement, step: step, board: board)) {
            XCTAssertEqual($0 as? ContactResolutionError, .invalidBilateralPair(candidateCount: 2))
        }
    }

    func testResolutionRequiresDefaultPositionMembership() throws {
        let board = fixtureBoard(positionContactIDs: ["edge-left"])
        let requirement = ContactRequirement.edge(
            depthRangeMillimeters: .init(minimum: 19, maximum: 21),
            selection: .single
        )
        let step = fixtureStep(target: requirement)

        XCTAssertEqual(
            try ContactResolver.resolve(requirement, step: step, board: board).map(\.id),
            ["edge-left"]
        )
    }

    func testResolutionRequiresFactualGripCompatibility() {
        let board = fixtureBoard()
        let requirement = ContactRequirement(
            kind: .edge,
            compatibleGripTypes: [.fullCrimp],
            selection: .allMatching
        )
        let step = fixtureStep(target: requirement)

        XCTAssertThrowsError(try ContactResolver.resolve(requirement, step: step, board: board)) {
            XCTAssertEqual($0 as? ContactResolutionError, .noMatches)
        }
    }

    func testRequirementGripConstraintRejectsUnknownContactGripMetadata() {
        let board = fixtureBoard(gripTypes: [])
        let requirement = ContactRequirement(
            kind: .edge,
            depthRangeMillimeters: .init(minimum: 29, maximum: 31),
            compatibleGripTypes: [.openHand],
            selection: .single
        )
        let step = fixtureStep(target: requirement)

        XCTAssertThrowsError(try ContactResolver.resolve(requirement, step: step, board: board)) {
            XCTAssertEqual($0 as? ContactResolutionError, .ambiguousSingle(candidateCount: 0))
        }
    }

    func testStepGripConstraintRejectsUnknownContactGripMetadata() {
        let board = fixtureBoard(gripTypes: [])
        let requirement = ContactRequirement.edge(
            depthRangeMillimeters: .init(minimum: 29, maximum: 31),
            selection: .single
        )
        let step = fixtureStep(target: requirement, gripType: .openHand)

        XCTAssertThrowsError(try ContactResolver.resolve(requirement, step: step, board: board)) {
            XCTAssertEqual($0 as? ContactResolutionError, .ambiguousSingle(candidateCount: 0))
        }
    }

    func testUnilateralSideRejectsUnknownContactSideMetadata() {
        let board = fixtureBoard()
        let requirement = ContactRequirement.edge(
            depthRangeMillimeters: .init(minimum: 29, maximum: 31),
            selection: .single
        )
        let step = fixtureStep(
            target: requirement,
            handUse: .single,
            side: .left
        )

        XCTAssertThrowsError(try ContactResolver.resolve(requirement, step: step, board: board)) {
            XCTAssertEqual($0 as? ContactResolutionError, .ambiguousSingle(candidateCount: 0))
        }
    }

    func testRequirementGripTypesAreAlternatives() throws {
        let board = fixtureBoard()
        let requirement = ContactRequirement(
            kind: .edge,
            depthRangeMillimeters: .init(minimum: 29, maximum: 31),
            compatibleGripTypes: [.openHand, .halfCrimp],
            selection: .single
        )
        let step = fixtureStep(target: requirement)

        XCTAssertEqual(
            try ContactResolver.resolve(requirement, step: step, board: board).map(\.id),
            ["edge-deep"]
        )
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
            targets: [target],
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
        documentsPair: Bool = false,
        reciprocalPair: Bool = true,
        documentsSides: Bool = false
    ) -> BoardRevision {
        let contacts = [
            PhysicalContact(
                id: "edge-right",
                name: "Right edge",
                kind: .edge,
                fingerCapacity: rightFingerCapacity,
                handCapacity: rightHandCapacity,
                depthRangeMillimeters: rightDepth,
                gripTypes: gripTypes,
                side: documentsSides ? .right : nil,
                pairedContactID: documentsPair ? "edge-left" : nil
            ),
            PhysicalContact(
                id: "edge-left",
                name: "Left edge",
                kind: .edge,
                fingerCapacity: leftFingerCapacity,
                handCapacity: leftHandCapacity,
                depthRangeMillimeters: 20...20,
                gripTypes: gripTypes,
                side: documentsSides ? .left : nil,
                pairedContactID: documentsPair && reciprocalPair ? "edge-right" : nil
            ),
            PhysicalContact(
                id: "edge-deep",
                name: "Deep edge",
                kind: .edge,
                depthRangeMillimeters: 30...30,
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

    private func jugBoard(_ fixtures: [JugFixture]) -> BoardRevision {
        let contacts = fixtures.map {
            PhysicalContact(id: $0.id, name: $0.id, kind: .jug, depthRangeMillimeters: $0.depth)
        }
        let geometry = Dictionary(uniqueKeysWithValues: fixtures.map {
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
