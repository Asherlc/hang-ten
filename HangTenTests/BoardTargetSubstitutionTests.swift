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

    func testBilateralPairRequiresExactlyTwoFactuallyCompatibleContacts() throws {
        let board = fixtureBoard()
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
        let board = fixtureBoard(rightDepth: 19...19)
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

    private func fixtureStep(target: ContactRequirement) -> WorkoutStep {
        WorkoutStep(
            id: "fixture-step",
            number: 1,
            title: "Fixture",
            instruction: "",
            accessory: "",
            duration: 10,
            phase: .hang,
            targets: [target]
        )
    }

    private func fixtureBoard(
        rightDepth: ClosedRange<Double> = 20...20,
        positionContactIDs: [String]? = nil
    ) -> BoardRevision {
        let contacts = [
            PhysicalContact(
                id: "edge-right",
                name: "Right edge",
                kind: .edge,
                depthRangeMillimeters: rightDepth,
                gripTypes: [.openHand]
            ),
            PhysicalContact(
                id: "edge-left",
                name: "Left edge",
                kind: .edge,
                depthRangeMillimeters: 20...20,
                gripTypes: [.openHand]
            ),
            PhysicalContact(
                id: "edge-deep",
                name: "Deep edge",
                kind: .edge,
                depthRangeMillimeters: 30...30,
                gripTypes: [.openHand]
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
                BoardPosition(
                    id: "front",
                    presentationID: "front",
                    contactIDs: positionContactIDs ?? contacts.map(\.id)
                )
            ]
        )
    }
}
