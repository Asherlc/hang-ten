import XCTest
@testable import HangTen

final class ContactResolverTests: XCTestCase {
    func testAllMatchingReturnsCanonicalContactOrder() throws {
        let board = fixtureBoard()
        let step = fixtureStep(target: .edge(selection: .allMatching))

        XCTAssertEqual(
            try ContactResolver.resolve(step.targets[0], step: step, board: board).map(\.id),
            ["edge-right", "edge-left", "edge-deep"]
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

    func testBilateralPairResolvesReciprocalNonGastonLeftRightPair() throws {
        let board = fixtureBoard(documentsPair: true, documentsSides: true)
        let requirement = ContactRequirement.edge(
            depthRangeMillimeters: .init(minimum: 19, maximum: 21),
            selection: .bilateralPair
        )
        let step = fixtureStep(target: requirement)

        XCTAssertEqual(
            try ContactResolver.resolve(requirement, step: step, board: board).map(\.id),
            ["edge-right", "edge-left"]
        )
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

    func testBilateralPairRejectsTwoUnsidedContactsWithoutPairMetadata() {
        let board = fixtureBoard()
        let requirement = ContactRequirement.edge(
            depthRangeMillimeters: .init(minimum: 19, maximum: 21),
            selection: .bilateralPair
        )
        let step = fixtureStep(target: requirement)

        XCTAssertThrowsError(try ContactResolver.resolve(requirement, step: step, board: board)) {
            XCTAssertEqual($0 as? ContactResolutionError, .invalidBilateralPair(candidateCount: 2))
        }
    }

    func testBilateralPairRejectsReciprocalPairWithUnknownSides() {
        let board = fixtureBoard(documentsPair: true)
        let requirement = ContactRequirement.edge(
            depthRangeMillimeters: .init(minimum: 19, maximum: 21),
            selection: .bilateralPair
        )
        let step = fixtureStep(target: requirement)

        XCTAssertThrowsError(try ContactResolver.resolve(requirement, step: step, board: board)) {
            XCTAssertEqual($0 as? ContactResolutionError, .invalidBilateralPair(candidateCount: 2))
        }
    }

    func testBilateralPairRejectsLeftRightContactsWithoutReciprocalPairMetadata() {
        let board = fixtureBoard(documentsSides: true)
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
        let board = fixtureBoard(positionContactIDs: ["edge-deep"], handCapacity: 1)
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

    func testCompactSingleHandBoardAllowsNeutralContactForEitherAthleteSide() throws {
        let board = compactSingleHandBoard(id: "lattice.mxedge-lift-small")
        let requirement = ContactRequirement.edge(
            depthRangeMillimeters: .init(minimum: 29, maximum: 31),
            selection: .single
        )

        for side in [WorkoutSide.left, .right] {
            let step = fixtureStep(target: requirement, handUse: .single, side: side)
            XCTAssertEqual(
                try ContactResolver.resolve(requirement, step: step, board: board).map(\.id),
                ["lower"]
            )
        }
    }

    func testTopologyMatchingBoardWithoutMXEdgeSmallEligibilityRejectsNeutralContact() {
        let board = compactSingleHandBoard(id: "lattice.mxedge-lift-large")
        let requirement = ContactRequirement.edge(
            depthRangeMillimeters: .init(minimum: 29, maximum: 31),
            selection: .single
        )
        let step = fixtureStep(target: requirement, handUse: .single, side: .left)

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
        positionContactIDs: [String]? = nil,
        gripTypes: Set<GripType> = [.openHand],
        documentsPair: Bool = false,
        documentsSides: Bool = false,
        handCapacity: Int? = nil
    ) -> BoardRevision {
        let contacts = [
            PhysicalContact(
                id: "edge-right",
                name: "Right edge",
                kind: .edge,
                handCapacity: handCapacity,
                depthRangeMillimeters: rightDepth,
                gripTypes: gripTypes,
                side: documentsSides ? .right : nil,
                pairedContactID: documentsPair ? "edge-left" : nil
            ),
            PhysicalContact(
                id: "edge-left",
                name: "Left edge",
                kind: .edge,
                handCapacity: handCapacity,
                depthRangeMillimeters: 20...20,
                gripTypes: gripTypes,
                side: documentsSides ? .left : nil,
                pairedContactID: documentsPair ? "edge-right" : nil
            ),
            PhysicalContact(
                id: "edge-deep",
                name: "Deep edge",
                kind: .edge,
                handCapacity: handCapacity,
                depthRangeMillimeters: 30...30,
                gripTypes: gripTypes
            )
        ]
        let geometry = Dictionary(uniqueKeysWithValues: contacts.map {
            ($0.id, [BoardContactPiece(
                id: "\($0.id)-piece",
                contactID: $0.id,
                frame: CGRect(x: 0, y: 0, width: 0.1, height: 0.1),
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
                positionContactIDs.map {
                    BoardPosition(id: "front", presentationID: "front", contactIDs: $0)
                } ?? BoardPosition(id: "front", presentationID: "front")
            ]
        )
    }

    private func compactSingleHandBoard(id: String) -> BoardRevision {
        let contacts = [
            PhysicalContact(
                id: "lower", name: "Lower edge", kind: .edge, handCapacity: 1,
                depthRangeMillimeters: 30...30
            ),
            PhysicalContact(
                id: "inverted", name: "Inverted edge", kind: .edge, handCapacity: 1,
                depthRangeMillimeters: 8...8
            )
        ]
        let descriptor = BoardModelDescriptor(
            schemaVersion: 1,
            coordinateFrame: "board-face-normalized-v1",
            modelSHA256: "compact-fixture",
            modelBounds: BoardModelBounds(minimum: [0, 0, 0], maximum: [1, 1, 0.1]),
            nodes: [],
            contacts: [:]
        )
        let presentation = BoardPresentation(
            id: "model", name: "Model", aspectRatio: 1, isDefault: true,
            media: .model(BoardModelMedia(
                assetPath: "assets/model.usdz",
                descriptorPath: "assets/model.model.json",
                descriptor: descriptor,
                display: BoardModelDisplay(camera: BoardModelCamera(
                    type: "orthographic", viewDirection: [0, 0, -1], up: [0, 1, 0], fitPadding: 0
                ))
            ))
        )
        return BoardRevision(
            id: id, revisionID: "fixture", manufacturer: "Fixture", name: "Compact",
            subtitle: "", dimensions: nil, aspectRatio: 1, contacts: contacts,
            productURL: URL(string: "https://example.com/compact")!, photoAssetName: nil,
            presentations: [presentation],
            positions: [
                BoardPosition(id: "lower", presentationID: "model", contactIDs: ["lower"]),
                BoardPosition(id: "inverted", presentationID: "model", contactIDs: ["inverted"])
            ]
        )
    }
}
