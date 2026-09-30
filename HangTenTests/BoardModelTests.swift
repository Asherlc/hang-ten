import XCTest
import simd
@testable import HangTen

final class BoardModelTests: XCTestCase {

    @MainActor
    func testNativeCordMapAspectRatioIncludesCordAndSelectedPosition() throws {
        let board = try XCTUnwrap(BoardCatalog.packageStore.board(id: "yy.baguette-evo"))
        let content = BoardMapPresentationContent(board: board, selectedPresentationID: nil)
        guard case .model(let media) = content.presentation.media,
              case .cadRoutedCord(let suspension) = media.suspension else {
            return XCTFail("Baguette Evo must use its native cord graph")
        }
        let cases: [(positionID: String, contactID: String)] = [
            ("paired-25-20-15-10", "edge-20-left"),
            ("paired-12-8-6", "edge-12-left"),
            ("central-30-25", "edge-central-30"),
            ("central-20-6", "edge-central-20"),
            ("rounded-tray", "rounded-tray")
        ]
        XCTAssertEqual(board.positions.map(\.id), cases.map(\.positionID))
        for fixture in cases {
            let positionID = BoardMapPresentationSelection.resolvePositionID(
                board: board,
                presentationID: content.presentation.id,
                activeHoldID: fixture.contactID
            )
            XCTAssertEqual(positionID, fixture.positionID)
            let pose = try XCTUnwrap(suspension.canonicalPoses[fixture.positionID])
            let framing = try SuspendedBoardPresentation.solve(
                pose: pose, suspension: suspension, bounds: media.descriptor.modelBounds
            ).cameraFraming
            let ratio = content.presentation.aspectRatio(for: positionID)
            XCTAssertEqual(ratio, max(1, CGFloat(framing.width / framing.height)), accuracy: 0.000_01, fixture.positionID)
            XCTAssertGreaterThan(334 / ratio, 100, "A 32-point body-only map hides the suspended board")
        }
    }

    @MainActor
    func testTallNativeCordMapUsesBoundedPortraitHeight() throws {
        let board = try XCTUnwrap(BoardCatalog.packageStore.board(id: "aelith.cyclops-011"))
        let position = try XCTUnwrap(board.positions.first)
        XCTAssertEqual(board.defaultPresentation.aspectRatio(for: position.id), 1)
    }

    @MainActor
    func testMapAspectRatioRetainsOrientationAndMissingPositionFallbacks() throws {
        let board = try XCTUnwrap(BoardCatalog.packageStore.board(id: "yy.baguette-evo"))
        let original = board.defaultPresentation
        guard case .model(let media) = original.media else { return XCTFail("Expected model") }
        let orientationOnly = BoardPresentation(
            id: original.id, name: original.name, aspectRatio: original.aspectRatio,
            isDefault: original.isDefault,
            media: .model(BoardModelMedia(
                assetPath: media.assetPath, descriptorPath: media.descriptorPath,
                descriptor: media.descriptor, display: media.display,
                orientation: media.orientation
            ))
        )
        XCTAssertEqual(orientationOnly.aspectRatio(for: "paired-25-20-15-10"), 10.4, accuracy: 0.000_01)
        XCTAssertEqual(orientationOnly.aspectRatio(for: "central-20-6"), 7.6133276, accuracy: 0.000_01)
        for presentation in [original, orientationOnly] {
            XCTAssertEqual(presentation.aspectRatio(for: nil), presentation.aspectRatio)
            XCTAssertEqual(presentation.aspectRatio(for: "missing-position"), presentation.aspectRatio)
        }
    }

    func testTrainingBoardHoldIDsUseCanonicalHoldOrderForPositionMembership() throws {
        let original = try XCTUnwrap(BoardCatalog.packageStore.board(id: "nature.stone-hanger"))
        let authoredOrder = original.contacts.map(\.id).reversed()
        let shuffledPosition = BoardPosition(
            id: "shuffled",
            presentationID: original.defaultPresentation.id,
            contactIDs: Array(authoredOrder)
        )
        let board = BoardRevision(
            id: original.id,
            revisionID: "test-fixture",
            manufacturer: original.manufacturer,
            name: original.name,
            subtitle: original.subtitle,
            dimensions: original.dimensions,
            aspectRatio: original.aspectRatio,
            equipmentObjects: original.equipmentObjects,
            contacts: original.contacts,
            productURL: original.productURL,
            photoAssetName: original.photoAssetName,
            presentations: original.presentations,
            positions: [shuffledPosition],
            positionTransitions: original.positionTransitions
        )

        XCTAssertEqual(board.position(id: "shuffled")?.id, "shuffled")
        XCTAssertEqual(board.contactIDs(inPosition: "shuffled"), original.contacts.map(\.id))
        XCTAssertNil(board.position(id: "missing"))
    }

    func testTrainingBoardPositionSelectionDoesNotBorrowMembershipOrPresentation() throws {
        let original = try XCTUnwrap(BoardCatalog.packageStore.board(id: "nature.stone-hanger"))
        let holdIDs = original.contacts.map(\.id)
        let firstPosition = BoardPosition(
            id: "first",
            presentationID: original.defaultPresentation.id,
            contactIDs: Array(holdIDs.prefix(2))
        )
        let secondPosition = BoardPosition(
            id: "second",
            presentationID: original.defaultPresentation.id,
            contactIDs: Array(holdIDs.dropFirst(2))
        )
        let unavailablePresentationPosition = BoardPosition(
            id: "unavailable",
            presentationID: "missing",
            contactIDs: holdIDs
        )
        let board = BoardRevision(
            id: original.id,
            revisionID: "test-fixture",
            manufacturer: original.manufacturer,
            name: original.name,
            subtitle: original.subtitle,
            dimensions: original.dimensions,
            aspectRatio: original.aspectRatio,
            equipmentObjects: original.equipmentObjects,
            contacts: original.contacts,
            productURL: original.productURL,
            photoAssetName: original.photoAssetName,
            presentations: original.presentations,
            positions: [firstPosition, secondPosition, unavailablePresentationPosition],
            positionTransitions: original.positionTransitions
        )

        XCTAssertEqual(board.contactIDs(inPosition: "first"), Array(holdIDs.prefix(2)))
        XCTAssertEqual(board.contactIDs(inPosition: "second"), Array(holdIDs.dropFirst(2)))
        XCTAssertEqual(board.position(id: "first")?.presentationID, original.defaultPresentation.id)
        XCTAssertEqual(board.position(id: "second")?.presentationID, original.defaultPresentation.id)
        XCTAssertEqual(board.position(id: "unavailable")?.presentationID, "missing")
        XCTAssertEqual(board.contactIDs(inPosition: "unavailable"), [])
    }

    func testBoardMapPositionResolverDoesNotFallbackAcrossPresentationOrHold() throws {
        let board = try XCTUnwrap(BoardCatalog.packageStore.board(id: "nature.stone-hanger"))
        let modelPresentation = try XCTUnwrap(board.presentations.first(where: {
            if case .model = $0.media { return true }
            return false
        }))
        XCTAssertNil(BoardMapPresentationSelection.resolvePositionID(
            board: board,
            presentationID: modelPresentation.id,
            activeHoldID: "not-on-model"
        ))
        XCTAssertEqual(
            BoardMapPresentationSelection.resolvePositionID(
                board: board,
                presentationID: modelPresentation.id,
                activeHoldID: nil
            ),
            board.position(id: board.positions.first {
                $0.presentationID == modelPresentation.id
            }?.id)?.id
        )
    }

    func testBoardMapPositionResolverFollowsHighlightedHoldWhenActiveHoldIsNil() throws {
        let board = try XCTUnwrap(BoardCatalog.packageStore.board(id: "captain-fingerfood.dual"))
        let presentationID = board.defaultPresentation.id
        let highlighted = "straight-edge-20"
        let expectedPosition = try XCTUnwrap(
            board.position(presentationID: presentationID, containingContactID: highlighted)?.id
        )

        XCTAssertEqual(
            BoardMapPresentationSelection.resolvePositionID(
                board: board,
                presentationID: presentationID,
                activeHoldID: nil,
                highlightedHoldIDs: [highlighted]
            ),
            expectedPosition
        )
        XCTAssertNotEqual(
            expectedPosition,
            board.position(presentationID: presentationID)?.id,
            "Highlighted hold should select a pose other than the default first position."
        )
    }

    @MainActor
    func testOrientationFramingProjectsTrueRotatedCornersInsteadOfAABBPhantoms() throws {
        let bounds = BoardModelBounds(
            minimum: [1, 2, 3],
            maximum: [5, 8, 11]
        )
        let pivot = SIMD3<Float>(3, 5, 7)
        let quaternion = simd_quatf(angle: .pi / 4, axis: SIMD3<Float>(0, 1, 0))
        let display = display(viewDirection: [1, 0, -1], up: [0, 1, 0])

        let transformedCorners = BoardModelRealityScene.rotatedCorners(
            bounds,
            by: quaternion,
            pivot: pivot
        )
        let exact = try XCTUnwrap(BoardModelRealityScene.framing(points: transformedCorners, display: display))
        let aabb = BoardModelRealityScene.rotatedBounds(bounds, by: quaternion, pivot: pivot)
        let aabbFraming = try XCTUnwrap(BoardModelRealityScene.framing(bounds: aabb, display: display))

        XCTAssertEqual(exact.width, 8, accuracy: 0.000_01)
        XCTAssertGreaterThan(aabbFraming.width, exact.width + 1)
    }
    private func display(
        viewDirection: [Double] = [0, 0, -1],
        up: [Double] = [0, 1, 0],
        padding: Double = 0.08
    ) -> BoardModelDisplay {
        .init(camera: .init(type: "orthographic", viewDirection: viewDirection, up: up,
                            fitPadding: padding, distanceMultiplier: nil, boundsExpansionFactor: nil))
    }
}
