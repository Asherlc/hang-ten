import CryptoKit
import SceneKit
import SwiftUI
import UIKit
import XCTest
@testable import HangTen

@MainActor
final class BoardModelTests: XCTestCase {
    func testOrientationContainerAspectRatioTracksSelectedPositionProjection() throws {
        let board = try XCTUnwrap(BoardCatalog.packageStore.board(id: "yy.baguette-evo"))
        let content = BoardMapPresentationContent(board: board, selectedPresentationID: nil)
        let cases: [(positionID: String, contactID: String, aspectRatio: CGFloat)] = [
            ("paired-25-20-15-10", "edge-20-left", 10.4),
            ("paired-12-8-6", "edge-12-left", 10.4),
            ("central-30-25", "edge-central-30", 10.4),
            ("central-20-6", "edge-central-20", 7.6133276),
            ("rounded-tray", "rounded-tray", 10.4)
        ]
        XCTAssertEqual(board.positions.map(\.id), cases.map(\.positionID))
        for fixture in cases {
            let positionID = BoardMapPresentationSelection.resolvePositionID(
                board: board,
                presentationID: content.presentation.id,
                activeHoldID: fixture.contactID
            )
            XCTAssertEqual(positionID, fixture.positionID)
            XCTAssertEqual(content.presentation.aspectRatio(for: positionID), fixture.aspectRatio, accuracy: 0.000_01, fixture.positionID)
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

    func testModelSceneRejectsUnknownPositionWithoutFallback() throws {
        let descriptor = modelDescriptor(nodes: [
            .init(nodeID: "Board/Body", role: .body, contactID: nil),
            .init(nodeID: "Board/Hold/Left", role: .contact, contactID: "left")
        ])
        let model = try XCTUnwrap(BoardModelScene(
            source: scene(nodes: ["Board/Body", "Board/Hold/Left"]),
            descriptor: descriptor,
            display: display(),
            allowedPositionIDs: ["front"]
        ))

        XCTAssertTrue(model.select(positionID: "front"))
        XCTAssertEqual(model.activePositionID, "front")
        XCTAssertFalse(model.select(positionID: nil))
        XCTAssertTrue(model.isUnavailable)
        XCTAssertNil(model.activePositionID)
        XCTAssertFalse(model.select(positionID: "reverse"))
        XCTAssertTrue(model.isUnavailable)
    }

    func testOrientationRotatesSharedContainerAboutBoundsCenterAndReframesAllCorners() throws {
        let descriptor = modelDescriptor(
            nodes: [
                .init(nodeID: "Board/Body", role: .body, contactID: nil),
                .init(nodeID: "Board/Hold/Left", role: .contact, contactID: "left")
            ],
            minimum: [1, 2, 3],
            maximum: [5, 8, 11]
        )
        let orientation = BoardModelOrientation(
            pivot: "modelBoundsCenter",
            rotations: [
                "front": SIMD4<Double>(0, 0, 0, 1),
                "reverse": SIMD4<Double>(0, 1, 0, 0)
            ]
        )
        let model = try XCTUnwrap(BoardModelScene(
            source: scene(nodes: ["Board/Body", "Board/Hold/Left"]),
            descriptor: descriptor,
            display: display(),
            orientation: orientation,
            allowedPositionIDs: ["front", "reverse"]
        ))
        let contact = try XCTUnwrap(model.contactNodes["left"]?.first)

        XCTAssertTrue(model.select(positionID: "reverse"))
        SCNTransaction.flush()

        XCTAssertEqual(model.contactID(for: contact), "left")
        XCTAssertNil(model.transientCordNode)
        XCTAssertFalse(model.isTransientCordAccessible)
        let pivot = SIMD3<Float>(3, 5, 7)
        let transformedPivot = model.boardContainer.simdTransform * SIMD4<Float>(pivot.x, pivot.y, pivot.z, 1)
        XCTAssertEqual(SIMD3<Float>(transformedPivot.x, transformedPivot.y, transformedPivot.z), pivot)
        let transformedCorner = model.boardContainer.simdTransform * SIMD4<Float>(1, 2, 3, 1)
        XCTAssertEqual(SIMD3<Float>(transformedCorner.x, transformedCorner.y, transformedCorner.z), SIMD3<Float>(5, 2, 11))
        XCTAssertEqual(model.camera.position.x, 3, accuracy: 0.000_01)
        XCTAssertEqual(model.camera.position.y, 5, accuracy: 0.000_01)
        XCTAssertEqual(model.camera.position.z, 16.28, accuracy: 0.000_01)

        let quarterTurn = simd_quatf(angle: .pi / 2, axis: SIMD3<Float>(0, 1, 0))
        let rotated = BoardModelScene.rotatedBounds(descriptor.modelBounds, by: quarterTurn, pivot: pivot)
        let framing = try XCTUnwrap(BoardModelScene.framing(bounds: rotated, display: display()))
        XCTAssertEqual(rotated.minimum[0], -1, accuracy: 0.000_01)
        XCTAssertEqual(rotated.minimum[1], 2, accuracy: 0.000_01)
        XCTAssertEqual(rotated.minimum[2], 5, accuracy: 0.000_01)
        XCTAssertEqual(rotated.maximum[0], 7, accuracy: 0.000_01)
        XCTAssertEqual(rotated.maximum[1], 8, accuracy: 0.000_01)
        XCTAssertEqual(rotated.maximum[2], 9, accuracy: 0.000_01)
        XCTAssertEqual(framing.target, pivot)
        XCTAssertEqual(framing.width, 8, accuracy: 0.000_001)
        XCTAssertEqual(framing.height, 6, accuracy: 0.000_001)
    }

    func testOrientationSelectionResetsOrbitAndAllowsSuspensionAtRuntime() throws {
        let descriptor = modelDescriptor(
            nodes: [
                .init(nodeID: "Board/Body", role: .body, contactID: nil),
                .init(nodeID: "Board/Hold/Left", role: .contact, contactID: "left")
            ],
            minimum: [1, 2, 3],
            maximum: [5, 8, 11]
        )
        let orientation = BoardModelOrientation(
            pivot: "modelBoundsCenter",
            rotations: ["reverse": SIMD4<Double>(0, 1, 0, 0)]
        )
        let model = try XCTUnwrap(BoardModelScene(
            source: scene(nodes: ["Board/Body", "Board/Hold/Left"]),
            descriptor: descriptor,
            display: display(),
            orientation: orientation,
            allowedPositionIDs: ["reverse"]
        ))

        XCTAssertTrue(model.select(positionID: "reverse"))
        let canonicalPosition = model.camera.position
        let canonicalScale = try XCTUnwrap(model.camera.camera?.orthographicScale)
        model.orbit(azimuth: 0.3, elevation: -0.2, zoomScale: 1.2)
        XCTAssertNotEqual(model.camera.position.x, canonicalPosition.x)
        XCTAssertNotEqual(model.camera.camera?.orthographicScale, canonicalScale)
        model.resetCamera(animated: false)
        XCTAssertEqual(model.camera.position.x, canonicalPosition.x, accuracy: 0.000_001)
        XCTAssertEqual(model.camera.position.y, canonicalPosition.y, accuracy: 0.000_001)
        XCTAssertEqual(model.camera.position.z, canonicalPosition.z, accuracy: 0.000_001)
        XCTAssertEqual(model.camera.camera?.orthographicScale, canonicalScale)

        let suspension = BoardModelSuspension(
            attachment: .init(nodeID: "Board/Body", pointInModel: [1, 2, 3], provenance: "test"),
            anchor: .init(offsetFromBoardBounds: [0, 1, 0], visibility: "invisible", provenance: "test", position: [1, 10, 3]),
            cord: .init(restLength: 10, radius: 0.01, material: "test", provenance: "test"),
            canonicalPoses: [
                "reverse": .init(
                    rotation: [0, 0, 0, 1],
                    translation: [0, 0, 0],
                    camera: .init(viewDirection: [0, 0, -1], fitPadding: 0.08)
                )
            ]
        )
        let suspendedModel = try XCTUnwrap(BoardModelScene(
            source: scene(nodes: ["Board/Body", "Board/Hold/Left"]),
            descriptor: descriptor,
            display: display(),
            suspension: suspension,
            orientation: orientation,
            allowedPositionIDs: ["reverse"]
        ))
        XCTAssertTrue(suspendedModel.select(positionID: "reverse"))
        XCTAssertNotNil(suspendedModel.transientCordNode)
        XCTAssertEqual(suspendedModel.transformedAttachment, SIMD3<Float>(1, 2, 3))
    }

    func testOrientationFramingProjectsTrueRotatedCornersInsteadOfAABBPhantoms() throws {
        let bounds = BoardModelBounds(
            minimum: [1, 2, 3],
            maximum: [5, 8, 11]
        )
        let pivot = SIMD3<Float>(3, 5, 7)
        let quaternion = simd_quatf(angle: .pi / 4, axis: SIMD3<Float>(0, 1, 0))
        let display = display(viewDirection: [1, 0, -1], up: [0, 1, 0])

        let transformedCorners = BoardModelScene.rotatedCorners(
            bounds,
            by: quaternion,
            pivot: pivot
        )
        let exact = try XCTUnwrap(BoardModelScene.framing(points: transformedCorners, display: display))
        let aabb = BoardModelScene.rotatedBounds(bounds, by: quaternion, pivot: pivot)
        let aabbFraming = try XCTUnwrap(BoardModelScene.framing(bounds: aabb, display: display))

        XCTAssertEqual(exact.width, 8, accuracy: 0.000_01)
        XCTAssertGreaterThan(aabbFraming.width, exact.width + 1)
    }

    func testFlashBoardNativeSceneUsesApprovedTwoBranchSuspensionAndBindsSmallCrimpContacts() async throws {
        let (board, media, model) = try await loadMigratedModel("tension.flash-board")
        XCTAssertNil(media.orientation)
        XCTAssertEqual(
            media.descriptor.modelSHA256,
            "4098ba4f8d8211683e6ec5c4466cd2725c0a040caae4a75e561d705315757524"
        )
        XCTAssertEqual(media.descriptor.contacts.count, 7)
        guard case .twoBranchCord(let suspension) = media.suspension else {
            return XCTFail("Flash Board must load the approved twoBranchCord suspension")
        }
        XCTAssertEqual(suspension.branches.count, 2)
        XCTAssertEqual(Set(media.descriptor.contacts.keys), Set(board.contacts.map(\.id)))
        XCTAssertTrue(Set(media.descriptor.contacts.keys).isSuperset(of: ["small-crimp-left", "small-crimp-right"]))
        for position in board.positions {
            XCTAssertTrue(model.select(positionID: position.id), position.id)
            XCTAssertFalse(model.isUnavailable, position.id)
            XCTAssertEqual(model.activePositionID, position.id)
            XCTAssertNotNil(model.transientCordNode, position.id)
        }
    }

    func testFlashBoardNativeSceneBuildsVisibleThreeDCordBranchesForSelectedPosition() async throws {
        let (_, media, model) = try await loadMigratedModel("tension.flash-board")

        XCTAssertEqual(media.descriptor.modelSHA256, "4098ba4f8d8211683e6ec5c4466cd2725c0a040caae4a75e561d705315757524")
        XCTAssertEqual(media.descriptor.contacts.count, 7)
        guard case .twoBranchCord(let suspension) = media.suspension else {
            return XCTFail("Flash Board must load the approved twoBranchCord suspension")
        }
        XCTAssertEqual(suspension.branches.count, 2)
        XCTAssertEqual(suspension.passages.left.map(\.id), ["left-outer-passage", "left-inner-passage"])
        XCTAssertEqual(suspension.passages.right.map(\.id), ["right-inner-passage", "right-outer-passage"])
        XCTAssertEqual(Set((suspension.passages.left + suspension.passages.right).map(\.nodeID)), ["flash_board_body_008"])
        XCTAssertEqual(suspension.branches[0].exteriorContactPoints, [[0.014, 0.048526, -0.001], [0.034, 0.048526, -0.001]])
        XCTAssertEqual(suspension.branches[1].exteriorContactPoints, [[0.466, 0.048526, -0.001], [0.486, 0.048526, -0.001]])

        XCTAssertTrue(model.select(positionID: "three-edge-upright"))
        let cord = try XCTUnwrap(model.transientCordNode)
        XCTAssertFalse(cord.isHidden)
        XCTAssertFalse(model.isTransientCordAccessible)
        for branchIndex in 0..<2 {
            let segments = cord.childNodes.filter {
                $0.name?.hasPrefix("suspended.cord.branch.\(branchIndex).") == true
            }
            XCTAssertFalse(segments.isEmpty, "branch \(branchIndex) must contain visible 3D segments")
            XCTAssertTrue(segments.allSatisfy {
                !$0.isHidden && $0.geometry is SCNCylinder && $0.categoryBitMask == BoardModelScene.cordCategory
            })
        }
    }

    func testBaguetteEvoRendersDocumentedSuspendedPresentationForEveryPosition() async throws {
        let (board, media, model) = try await loadMigratedModel("yy.baguette-evo")
        guard case .twoBranchCord(let suspension) = media.suspension else {
            return XCTFail("Baguette Evo must load the documented twoBranchCord suspension")
        }
        XCTAssertEqual(suspension.branches.count, 2)

        for position in board.positions {
            XCTAssertTrue(model.select(positionID: position.id), position.id)
            XCTAssertFalse(model.isUnavailable, position.id)
            XCTAssertEqual(model.activePositionID, position.id)
            XCTAssertFalse(model.isTransientCordAccessible, position.id)
            XCTAssertFalse(try XCTUnwrap(model.transientCordNode, position.id).childNodes.isEmpty, position.id)
        }
    }

    func testPairedLeadModelHangboardsBindTwoDistinctPointsAndRenderNonPickableLeads() async throws {
        for boardID in ["captain-fingerfood.dual", "captain-fingerfood.pocket", "captain-fingerfood.unlevel", "lattice.mxedge-lift-large", "lattice.mxedge-lift-small", "nature.stone-hanger"] {
            let (board, media, model) = try await loadMigratedModel(boardID)
            guard case .pairedLeadCord(let suspension) = media.suspension else {
                return XCTFail("\(boardID) must load the approved pairedLeadCord suspension")
            }

            XCTAssertEqual(suspension.attachments.count, 2, boardID)
            XCTAssertEqual(Set(suspension.attachments.map(\.id)).count, 2, boardID)
            for attachment in suspension.attachments {
                let binding = try XCTUnwrap(media.descriptor.nodes.first { $0.nodeID == attachment.nodeID })
                XCTAssertNotEqual(binding.role, .contact, boardID)
            }
            XCTAssertNotEqual(suspension.attachments[0].pointInModel, suspension.attachments[1].pointInModel, boardID)

            for position in board.positions {
                XCTAssertTrue(model.select(positionID: position.id), "\(boardID)/\(position.id)")
                XCTAssertFalse(model.isUnavailable, "\(boardID)/\(position.id)")
                XCTAssertFalse(model.isTransientCordAccessible, "\(boardID)/\(position.id)")
                let cord = try XCTUnwrap(model.transientCordNode, "\(boardID)/\(position.id)")
                let expectedSegmentCount = suspension.attachments.reduce(0) {
                    $0 + SuspendedCordSolver.sampleCount - 1
                        + (suspension.canonicalPoses[position.id]?.cordContactPoints?[$1.id]?.count ?? $1.contactPointsInModel.count)
                }
                XCTAssertEqual(cord.childNodes.count, expectedSegmentCount, "\(boardID)/\(position.id)")
                XCTAssertEqual(cord.categoryBitMask, BoardModelScene.cordCategory, "\(boardID)/\(position.id)")
                XCTAssertTrue(cord.childNodes.allSatisfy { node in
                    node.categoryBitMask == BoardModelScene.cordCategory && model.contactID(for: node) == nil
                }, "\(boardID)/\(position.id)")
            }
        }
    }

    func testPairedLeadModelHangboardsReserveCordAwareCanonicalCameraMargin() async throws {
        for boardID in ["captain-fingerfood.dual", "captain-fingerfood.pocket", "captain-fingerfood.unlevel", "lattice.mxedge-lift-large", "lattice.mxedge-lift-small", "nature.stone-hanger"] {
            let (board, media, model) = try await loadMigratedModel(boardID)
            guard case .pairedLeadCord(let suspension) = media.suspension else {
                return XCTFail("\(boardID) must load the approved pairedLeadCord suspension")
            }

            // The generic model padding only proves that a centerline reaches
            // the frame edge. A paired hanging lead needs enough surrounding
            // view space to remain visibly distinct from the board in detail.
            for position in board.positions {
                let pose = try XCTUnwrap(suspension.canonicalPoses[position.id])
                let solved = try BoardModelScene.solveSuspension(
                    pose: pose,
                    suspension: .pairedLeadCord(suspension),
                    bounds: media.descriptor.modelBounds
                )
                XCTAssertGreaterThanOrEqual(
                    solved.cameraFraming.fitPadding,
                    1.4,
                    "\(boardID)/\(position.id) needs a cord-aware camera margin"
                )
                model.frame(in: CGSize(width: 390, height: 228))
                XCTAssertTrue(model.select(positionID: position.id))
                XCTAssertFalse(model.isUnavailable)
            }
        }
    }

    func testLatticeStillRejectsFormerSideMidpointRouteThatCrossesBody() async throws {
        let (board, media, _) = try await loadMigratedModel("lattice.mxedge-lift-large")
        guard case .pairedLeadCord(let profile) = media.suspension else { return XCTFail("missing paired leads") }
        let wrongProfile = BoardModelPairedLeadCord(
            attachments: zip(profile.attachments, [-0.083, 0.083]).map { attachment, x in
                BoardModelPairedLeadAttachment(id: attachment.id, nodeID: attachment.nodeID,
                    pointInModel: [x, 0, 0.012], provenance: "deliberately invalid former route")
            }, passages: profile.passages, anchor: profile.anchor, cord: profile.cord, canonicalPoses: profile.canonicalPoses
        )
        let sourceURL = repositoryRootURL().appendingPathComponent("Hangboards/lattice-mxedge-lift-large/assets/primary.usdz")
        let model = try XCTUnwrap(BoardModelScene(source: try SCNScene(url: sourceURL),
            descriptor: media.descriptor, display: media.display, suspension: .pairedLeadCord(wrongProfile),
            allowedPositionIDs: Set(board.positions.map(\.id))))
        XCTAssertFalse(model.select(positionID: "lower-lips-front"))
        XCTAssertTrue(model.isUnavailable)
        XCTAssertNil(model.transientCordNode)
    }

    func testPairedLeadSceneRendersTwoTransientNonPickableCylinderGroupsAndRejectsOneBadLead() throws {
        let selectedPose = BoardModelCanonicalPose(
            rotation: [0, 0, 0, 1],
            translation: [0, 0, 0],
            camera: BoardModelCanonicalCamera(viewDirection: [0, 0, -1], fitPadding: 0.08)
        )
        func suspension(right: [Double]) -> BoardModelPairedLeadCord {
            BoardModelPairedLeadCord(
                attachments: [
                    BoardModelPairedLeadAttachment(id: "left", nodeID: "Lead/Left", pointInModel: [-0.6, 0.4, 0.05], provenance: "test"),
                    BoardModelPairedLeadAttachment(id: "right", nodeID: "Lead/Right", pointInModel: right, provenance: "test"),
                ],
                passages: BoardModelPassagePairs(
                    left: [BoardModelPassage(id: "left-lip", nodeID: "Lead/Left", pointInModel: [-0.6, 0.4, 0.05], provenance: "test")],
                    right: [BoardModelPassage(id: "right-lip", nodeID: "Lead/Right", pointInModel: right, provenance: "test")]
                ),
                anchor: BoardModelInvisibleAnchor(offsetFromBoardBounds: [0, 0, 0], visibility: "invisible", provenance: "test", position: [0, 2, 0]),
                cord: BoardModelCord(restLength: 2, radius: 0.01, material: "test-cord", provenance: "test"),
                canonicalPoses: ["primary": selectedPose]
            )
        }
        let descriptor = modelDescriptor(
            nodes: [
                .init(nodeID: "Body", role: .body, contactID: nil),
                .init(nodeID: "Hold", role: .contact, contactID: "hold"),
                .init(nodeID: "Lead/Left", role: .attachment, contactID: nil),
                .init(nodeID: "Lead/Right", role: .attachment, contactID: nil),
            ],
            minimum: [-1, -0.5, -0.2],
            maximum: [1, 0.5, 0.2]
        )
        func source() -> SCNScene {
            let source = scene(nodes: ["Body", "Hold", "Lead/Left", "Lead/Right"])
            for path in ["Body", "Hold", "Lead/Left", "Lead/Right"] {
                node(at: path, in: source)?.simdPosition = SIMD3<Float>(10, 10, 10)
            }
            return source
        }

        let valid = suspension(right: [0.6, 0.4, -0.05])
        let validModel = try XCTUnwrap(BoardModelScene(
            source: source(), descriptor: descriptor, display: display(), suspension: .pairedLeadCord(valid)
        ))
        XCTAssertTrue(validModel.select(positionID: "primary"))
        let cord = try XCTUnwrap(validModel.transientCordNode)
        XCTAssertFalse(cord.isHidden)
        XCTAssertFalse(validModel.isTransientCordAccessible)
        XCTAssertEqual(cord.categoryBitMask, BoardModelScene.cordCategory)
        XCTAssertEqual(cord.childNodes.count, 2 * (SuspendedCordSolver.sampleCount - 1))
        for branchIndex in 0..<2 {
            let segments = cord.childNodes.filter {
                $0.name?.hasPrefix("suspended.cord.branch.\(branchIndex).") == true
            }
            XCTAssertEqual(segments.count, SuspendedCordSolver.sampleCount - 1)
            XCTAssertTrue(segments.allSatisfy {
                !$0.isHidden && $0.geometry is SCNCylinder && $0.categoryBitMask == BoardModelScene.cordCategory
                    && validModel.contactID(for: $0) == nil
            })
        }

        let invalidModel = try XCTUnwrap(BoardModelScene(
            source: source(), descriptor: descriptor, display: display(),
            suspension: .pairedLeadCord(suspension(right: [1.01, -0.5, 0]))
        ))
        XCTAssertFalse(invalidModel.select(positionID: "primary"))
        XCTAssertTrue(invalidModel.isUnavailable)
        XCTAssertNil(invalidModel.transientCordNode)
    }

    func testFlashBoardCordCenterlinesAreTautAcrossEveryCanonicalPose() async throws {
        let (_, media, model) = try await loadMigratedModel("tension.flash-board")
        guard case .twoBranchCord(let suspension) = media.suspension else {
            return XCTFail("Flash Board must load the approved twoBranchCord suspension")
        }

        for (positionID, pose) in suspension.canonicalPoses.sorted(by: { $0.key < $1.key }) {
            let solved = try BoardModelScene.solveSuspension(
                pose: pose,
                suspension: .twoBranchCord(suspension),
                bounds: media.descriptor.modelBounds
            )
            guard case .twoBranch(let presentation) = solved else {
                return XCTFail("Flash \(positionID) must solve as two branches")
            }
            let passagesByID = Dictionary(uniqueKeysWithValues: (suspension.passages.left + suspension.passages.right).map {
                ($0.id, $0)
            })
            XCTAssertTrue(model.select(positionID: positionID), "Flash \(positionID) must render its solved presentation")
            assertRenderedCordSegments(
                model.transientCordNode,
                paths: presentation.branches.map(\.centerlineSamples),
                label: "Flash \(positionID)"
            )
            for branch in presentation.branches {
                XCTAssertEqual(branch.spans.count, 3, "\(positionID)/\(branch.id)")
                let authoredBranch = try XCTUnwrap(suspension.branches.first { $0.id == branch.id })
                let firstPassage = try XCTUnwrap(passagesByID[authoredBranch.passageIDs[0]])
                let secondPassage = try XCTUnwrap(passagesByID[authoredBranch.passageIDs[1]])
                func transformed(_ point: [Double]) -> SIMD3<Float> {
                    let modelPoint = SIMD3<Float>(
                        Float(point[0]), Float(point[1]), Float(point[2])
                    )
                    let worldPoint = presentation.boardTransform * SIMD4(modelPoint, 1)
                    return SIMD3(worldPoint.x, worldPoint.y, worldPoint.z)
                }
                let expectedRoute = authoredBranch.entryContactPoints.map(transformed)
                    + [transformed(firstPassage.entryPointInModel), transformed(firstPassage.exitPointInModel)]
                    + authoredBranch.exteriorContactPoints.map(transformed)
                    + [transformed(secondPassage.exitPointInModel), transformed(secondPassage.entryPointInModel)]
                    + authoredBranch.exitContactPoints.map(transformed)
                XCTAssertEqual(
                    branch.spans[1],
                    expectedRoute,
                    "Flash \(positionID)/\(branch.id) must preserve authored route points in order"
                )
                assertStraightSamples(
                    branch.spans[0],
                    label: "Flash \(positionID)/\(branch.id) incoming free span"
                )
                assertStraightSamples(
                    branch.spans[2],
                    label: "Flash \(positionID)/\(branch.id) outgoing free span"
                )
                for (index, pair) in zip(branch.spans[1], branch.spans[1].dropFirst()).enumerated() {
                    XCTAssertGreaterThan(
                        simd_length(pair.1 - pair.0),
                        1e-7,
                        "Flash \(positionID)/\(branch.id) authored route segment \(index)"
                    )
                }
                let declaredLength = suspension.branches.first { $0.id == branch.id }!.restLength
                XCTAssertLessThanOrEqual(
                    branch.arcLength,
                    Float(declaredLength) + SuspendedCordSolver.tautTolerance,
                    "Flash \(positionID)/\(branch.id) exceeds declared cord length"
                )
            }
        }
    }

    private func assertRenderedCordSegments(
        _ cord: SCNNode?,
        paths: [[SIMD3<Float>]],
        label: String
    ) {
        guard let cord else {
            return XCTFail("\(label) must have rendered cord geometry")
        }
        for (branchIndex, path) in paths.enumerated() {
            let segments = cord.childNodes
                .filter { $0.name?.hasPrefix("suspended.cord.branch.\(branchIndex).") == true }
                .sorted { segmentIndex($0) < segmentIndex($1) }
            XCTAssertEqual(
                segments.count,
                max(path.count - 1, 0),
                "\(label) branch \(branchIndex) must render one segment per consecutive centerline pair"
            )
            for (index, pair) in zip(path, path.dropFirst()).enumerated() {
                guard index < segments.count,
                      let cylinder = segments[index].geometry as? SCNCylinder else {
                    XCTFail("\(label) branch \(branchIndex) segment \(index) must be a cylinder")
                    continue
                }
                let start = pair.0
                let end = pair.1
                let direction = end - start
                let length = simd_length(direction)
                XCTAssertEqual(
                    Float(cylinder.height),
                    length,
                    accuracy: 1e-5,
                    "\(label) branch \(branchIndex) segment \(index) height must equal its direct span"
                )
                XCTAssertEqual(
                    segments[index].simdPosition,
                    (start + end) / 2,
                    "\(label) branch \(branchIndex) segment \(index) must be centered on its direct span"
                )
                if length > 1e-7 {
                    let axis = segments[index].simdOrientation.act(SIMD3<Float>(0, 1, 0))
                    XCTAssertLessThan(
                        simd_length(axis - direction / length),
                        1e-5,
                        "\(label) branch \(branchIndex) segment \(index) must point along its direct span"
                    )
                }
            }
        }
    }

    private func segmentIndex(_ node: SCNNode) -> Int {
        Int(node.name?.split(separator: ".").last ?? "") ?? -1
    }

    private func assertStraightSamples(_ samples: [SIMD3<Float>], label: String) {
        guard let start = samples.first, let end = samples.last else {
            return XCTFail("\(label) must contain samples")
        }
        let displacement = end - start
        let length = simd_length(displacement)
        XCTAssertGreaterThan(length, 1e-7, "\(label) endpoints must differ")
        guard length > 1e-7 else { return }
        let direction = displacement / length
        for (index, sample) in samples.enumerated() {
            XCTAssertLessThan(
                simd_length(simd_cross(sample - start, direction)),
                1e-5,
                "\(label) sample \(index) must remain on its direct span"
            )
        }
    }

    private func assertCameraBasis(
        _ camera: SCNNode,
        expectedFront: SIMD3<Float>,
        expectedUp: SIMD3<Float>,
        expectedRight: SIMD3<Float>,
        label: String,
        file: StaticString = #filePath,
        line: UInt = #line
    ) {
        let front = camera.simdWorldFront
        let up = camera.simdWorldUp
        let right = camera.simdWorldRight
        let vectors = [front, up, right]
        XCTAssertTrue(vectors.allSatisfy { $0.x.isFinite && $0.y.isFinite && $0.z.isFinite }, "\(label) camera basis must be finite", file: file, line: line)
        XCTAssertEqual(simd_length(front), 1, accuracy: 0.000_1, "\(label) front", file: file, line: line)
        XCTAssertEqual(simd_length(up), 1, accuracy: 0.000_1, "\(label) up", file: file, line: line)
        XCTAssertEqual(simd_length(right), 1, accuracy: 0.000_1, "\(label) right", file: file, line: line)
        XCTAssertEqual(simd_dot(front, up), 0, accuracy: 0.000_1, "\(label) front/up", file: file, line: line)
        XCTAssertEqual(simd_dot(front, right), 0, accuracy: 0.000_1, "\(label) front/right", file: file, line: line)
        XCTAssertEqual(simd_dot(up, right), 0, accuracy: 0.000_1, "\(label) up/right", file: file, line: line)
        assertVectorEqual(simd_cross(front, up), right, "\(label) right-handed", file: file, line: line)
        assertVectorEqual(front, expectedFront, "\(label) expected front", file: file, line: line)
        assertVectorEqual(up, expectedUp, "\(label) expected up", file: file, line: line)
        assertVectorEqual(right, expectedRight, "\(label) expected right", file: file, line: line)
    }

    private func assertVectorEqual(
        _ actual: SIMD3<Float>,
        _ expected: SIMD3<Float>,
        _ message: String,
        file: StaticString = #filePath,
        line: UInt = #line
    ) {
        XCTAssertEqual(actual.x, expected.x, accuracy: 0.000_1, "\(message) x", file: file, line: line)
        XCTAssertEqual(actual.y, expected.y, accuracy: 0.000_1, "\(message) y", file: file, line: line)
        XCTAssertEqual(actual.z, expected.z, accuracy: 0.000_1, "\(message) z", file: file, line: line)
    }

    private func hasNonBackgroundPixels(_ image: CGImage) -> Bool {
        let width = image.width
        let height = image.height
        guard width > 0, height > 0 else { return false }
        var rgba = [UInt8](repeating: 0, count: width * height * 4)
        return rgba.withUnsafeMutableBytes { bytes -> Bool in
            guard let baseAddress = bytes.baseAddress,
                  let context = CGContext(data: baseAddress, width: width, height: height, bitsPerComponent: 8, bytesPerRow: width * 4, space: CGColorSpaceCreateDeviceRGB(), bitmapInfo: CGImageAlphaInfo.premultipliedLast.rawValue) else {
                return false
            }
            context.setFillColor(UIColor.white.cgColor)
            context.fill(CGRect(x: 0, y: 0, width: width, height: height))
            context.draw(image, in: CGRect(x: 0, y: 0, width: width, height: height))
            return (0..<(width * height)).contains { index in
                let offset = index * 4
                return bytes[offset] < 245 || bytes[offset + 1] < 245 || bytes[offset + 2] < 245
            }
        }
    }

    func testFlashBoardCanonicalCameraFacesSelectedSurfaceAcrossEveryPose() throws {
        let board = try XCTUnwrap(BoardCatalog.packageStore.board(id: "tension.flash-board"))
        guard case .model(let media) = board.defaultPresentation.media,
              case .twoBranchCord(let suspension) = media.suspension else {
            return XCTFail("Flash must declare its two-branch canonical poses")
        }
        XCTAssertEqual(suspension.canonicalPoses.count, 4)
        for (positionID, pose) in suspension.canonicalPoses {
            let solved = try BoardModelScene.solveSuspension(
                pose: pose, suspension: .twoBranchCord(suspension), bounds: media.descriptor.modelBounds
            )
            // The verified source faces are +Z (three-edge) and -Z (two-edge).
            // The authored X/Y half-turns bring the two-edge face toward +Z;
            // the three-edge Z half-turn preserves +Z. All four posed faces
            // therefore require a camera looking toward -Z in world space.
            XCTAssertLessThan(
                simd_length(solved.cameraFraming.direction - SIMD3<Float>(0, 0, -1)),
                1e-5,
                "\(positionID) camera must face the selected physical surface"
            )
        }
    }

    func testFlashBoardCameraBasisIsFiniteOrthonormalAndRightHanded() async throws {
        let (_, media, model) = try await loadMigratedModel("tension.flash-board")
        guard case .twoBranchCord(let suspension) = media.suspension else {
            return XCTFail("Flash Board must load the approved twoBranchCord suspension")
        }
        let pose = try XCTUnwrap(suspension.canonicalPoses["two-edge-upright"])
        let solved = try BoardModelScene.solveSuspension(
            pose: pose,
            suspension: .twoBranchCord(suspension),
            bounds: media.descriptor.modelBounds
        )
        let framing = solved.cameraFraming

        XCTAssertTrue(model.select(positionID: "two-edge-upright"))
        SCNTransaction.flush()
        assertCameraBasis(
            model.camera,
            expectedFront: framing.direction,
            expectedUp: framing.up,
            expectedRight: framing.right,
            label: "two-edge canonical"
        )

        let azimuth: Float = 0.3
        let elevation: Float = -0.2
        let zoomScale: Float = 1.2
        model.orbit(azimuth: azimuth, elevation: elevation, zoomScale: zoomScale)
        SCNTransaction.flush()

        let baseOffset = -framing.direction * framing.distance
        let yaw = simd_quatf(angle: azimuth, axis: SIMD3<Float>(0, 1, 0))
        let pitch = simd_quatf(angle: elevation, axis: framing.right)
        let offset = (pitch * yaw).act(baseOffset)
        let expectedPosition = framing.target + simd_normalize(offset) * (framing.distance / zoomScale)
        let expectedFront = simd_normalize(framing.target - expectedPosition)
        let expectedRight = simd_normalize(simd_cross(expectedFront, framing.up))
        let expectedUp = simd_cross(expectedRight, expectedFront)
        assertCameraBasis(
            model.camera,
            expectedFront: expectedFront,
            expectedUp: expectedUp,
            expectedRight: expectedRight,
            label: "two-edge orbit"
        )
    }

    func testCameraOrientationRejectsDegenerateBasisWithoutMovingCamera() async throws {
        let (_, _, model) = try await loadMigratedModel("tension.flash-board")
        XCTAssertTrue(model.select(positionID: "two-edge-upright"))
        SCNTransaction.flush()

        let originalPosition = model.camera.simdPosition
        let originalTransform = model.camera.simdTransform
        let originalScale = try XCTUnwrap(model.camera.camera?.orthographicScale)
        let degenerateTarget = originalPosition + SIMD3<Float>(0, 1, 0)

        XCTAssertFalse(model.orientCamera(at: degenerateTarget, up: SIMD3<Float>(0, 1, 0)))
        XCTAssertEqual(model.camera.simdPosition, originalPosition)
        XCTAssertEqual(model.camera.simdTransform, originalTransform)
        XCTAssertEqual(model.camera.camera?.orthographicScale, originalScale)

        XCTAssertFalse(model.orientCamera(
            at: originalPosition + SIMD3<Float>(0, 0, -1),
            up: SIMD3<Float>(.nan, 1, 0)
        ))
        XCTAssertEqual(model.camera.simdPosition, originalPosition)
        XCTAssertEqual(model.camera.simdTransform, originalTransform)
    }

    func testFrameRejectsInvalidSizesWithoutChangingCameraOrCanonicalSelection() throws {
        let descriptor = modelDescriptor(
            nodes: [
                .init(nodeID: "Board/Body", role: .body, contactID: nil),
                .init(nodeID: "Board/Hold/Left", role: .contact, contactID: "left")
            ],
            minimum: [0, 0, 0],
            maximum: [4, 2, 1]
        )
        let orientation = BoardModelOrientation(
            pivot: "modelBoundsCenter",
            rotations: [
                "front": SIMD4<Double>(0, 0, 0, 1),
                "reverse": SIMD4<Double>(0, 1, 0, 0)
            ]
        )
        let model = try XCTUnwrap(BoardModelScene(
            source: scene(nodes: ["Board/Body", "Board/Hold/Left"]),
            descriptor: descriptor,
            display: display(),
            orientation: orientation,
            allowedPositionIDs: ["front", "reverse"]
        ))

        let validSize = CGSize(width: 386, height: 100)
        model.frame(in: validSize)
        XCTAssertTrue(model.select(positionID: "front"))
        let originalPosition = model.camera.simdPosition
        let originalTransform = model.camera.simdTransform
        let originalScale = try XCTUnwrap(model.camera.camera?.orthographicScale)

        for invalidSize in [
            CGSize(width: CGFloat.nan, height: 100),
            CGSize(width: 100, height: CGFloat.infinity),
            CGSize(width: 0, height: 100),
            CGSize(width: 100, height: 0),
            CGSize(width: -1, height: 100),
            CGSize(width: 100, height: -1)
        ] {
            model.frame(in: invalidSize)
            XCTAssertEqual(model.camera.simdPosition, originalPosition, invalidSize.debugDescription)
            XCTAssertEqual(model.camera.simdTransform, originalTransform, invalidSize.debugDescription)
            XCTAssertEqual(model.camera.camera?.orthographicScale, originalScale, invalidSize.debugDescription)
        }

        XCTAssertTrue(model.select(positionID: "reverse"))
        let expected = try XCTUnwrap(BoardModelScene(
            source: scene(nodes: ["Board/Body", "Board/Hold/Left"]),
            descriptor: descriptor,
            display: display(),
            orientation: orientation,
            allowedPositionIDs: ["front", "reverse"]
        ))
        expected.frame(in: validSize)
        XCTAssertTrue(expected.select(positionID: "front"))
        XCTAssertTrue(expected.select(positionID: "reverse"))

        XCTAssertEqual(model.camera.simdPosition, expected.camera.simdPosition)
        XCTAssertEqual(model.camera.simdTransform, expected.camera.simdTransform)
        XCTAssertEqual(model.camera.camera?.orthographicScale, expected.camera.camera?.orthographicScale)
    }

    func testOrbitRejectsInvalidInputsWithoutChangingCameraOrNextValidOrbit() throws {
        let descriptor = modelDescriptor(
            nodes: [
                .init(nodeID: "Board/Body", role: .body, contactID: nil),
                .init(nodeID: "Board/Hold/Left", role: .contact, contactID: "left")
            ]
        )
        let orientation = BoardModelOrientation(
            pivot: "modelBoundsCenter",
            rotations: ["front": SIMD4<Double>(0, 0, 0, 1)]
        )
        let model = try XCTUnwrap(BoardModelScene(
            source: scene(nodes: ["Board/Body", "Board/Hold/Left"]),
            descriptor: descriptor,
            display: display(),
            orientation: orientation,
            allowedPositionIDs: ["front"]
        ))
        model.frame(in: CGSize(width: 386, height: 100))
        XCTAssertTrue(model.select(positionID: "front"))

        let originalPosition = model.camera.simdPosition
        let originalTransform = model.camera.simdTransform
        let originalScale = try XCTUnwrap(model.camera.camera?.orthographicScale)
        let invalidInputs: [(Float, Float, Float)] = [
            (.nan, 0, 1),
            (0, .infinity, 1),
            (0, 0, 0),
            (0, 0, -1)
        ]
        for (azimuth, elevation, zoomScale) in invalidInputs {
            model.orbit(azimuth: azimuth, elevation: elevation, zoomScale: zoomScale)
            XCTAssertEqual(model.camera.simdPosition, originalPosition)
            XCTAssertEqual(model.camera.simdTransform, originalTransform)
            XCTAssertEqual(model.camera.camera?.orthographicScale, originalScale)
        }

        let validOrbit = (azimuth: Float(0.3), elevation: Float(-0.2), zoomScale: Float(1.2))
        model.orbit(
            azimuth: validOrbit.azimuth,
            elevation: validOrbit.elevation,
            zoomScale: validOrbit.zoomScale
        )

        let expected = try XCTUnwrap(BoardModelScene(
            source: scene(nodes: ["Board/Body", "Board/Hold/Left"]),
            descriptor: descriptor,
            display: display(),
            orientation: orientation,
            allowedPositionIDs: ["front"]
        ))
        expected.frame(in: CGSize(width: 386, height: 100))
        XCTAssertTrue(expected.select(positionID: "front"))
        expected.orbit(
            azimuth: validOrbit.azimuth,
            elevation: validOrbit.elevation,
            zoomScale: validOrbit.zoomScale
        )

        XCTAssertEqual(model.camera.simdPosition, expected.camera.simdPosition)
        XCTAssertEqual(model.camera.simdTransform, expected.camera.simdTransform)
        XCTAssertEqual(model.camera.camera?.orthographicScale, expected.camera.camera?.orthographicScale)
    }

    func testOrbitAllowsACompleteAzimuthRotation() throws {
        let descriptor = modelDescriptor(
            nodes: [
                .init(nodeID: "Board/Body", role: .body, contactID: nil),
                .init(nodeID: "Board/Hold/Left", role: .contact, contactID: "left")
            ]
        )
        let orientation = BoardModelOrientation(
            pivot: "modelBoundsCenter",
            rotations: ["front": SIMD4<Double>(0, 0, 0, 1)]
        )
        let model = try XCTUnwrap(BoardModelScene(
            source: scene(nodes: ["Board/Body", "Board/Hold/Left"]),
            descriptor: descriptor,
            display: display(),
            orientation: orientation,
            allowedPositionIDs: ["front"]
        ))
        model.frame(in: CGSize(width: 386, height: 100))
        XCTAssertTrue(model.select(positionID: "front"))
        let canonicalPosition = model.camera.simdPosition

        let azimuthStep: Float = .pi / 16
        for _ in 0..<32 {
            model.orbit(azimuth: azimuthStep, elevation: 0)
        }

        XCTAssertEqual(model.camera.simdPosition.x, canonicalPosition.x, accuracy: 0.000_01)
        XCTAssertEqual(model.camera.simdPosition.y, canonicalPosition.y, accuracy: 0.000_01)
        XCTAssertEqual(model.camera.simdPosition.z, canonicalPosition.z, accuracy: 0.000_01)

        model.orbit(azimuth: azimuthStep, elevation: 0)

        let expected = try XCTUnwrap(BoardModelScene(
            source: scene(nodes: ["Board/Body", "Board/Hold/Left"]),
            descriptor: descriptor,
            display: display(),
            orientation: orientation,
            allowedPositionIDs: ["front"]
        ))
        expected.frame(in: CGSize(width: 386, height: 100))
        XCTAssertTrue(expected.select(positionID: "front"))
        expected.orbit(azimuth: azimuthStep, elevation: 0)

        XCTAssertEqual(model.camera.simdPosition.x, expected.camera.simdPosition.x, accuracy: 0.000_01)
        XCTAssertEqual(model.camera.simdPosition.y, expected.camera.simdPosition.y, accuracy: 0.000_01)
        XCTAssertEqual(model.camera.simdPosition.z, expected.camera.simdPosition.z, accuracy: 0.000_01)
    }

    func testFlashBoardTwoEdgeSceneProjectsOrbitsAndRendersEachComponentSeparately() async throws {
        let (_, _, model) = try await loadMigratedModel("tension.flash-board")
        let view = BoardModelSCNView(frame: CGRect(x: 0, y: 0, width: 320, height: 320))
        view.backgroundColor = .white
        view.isOpaque = true
        view.rendersContinuously = false
        view.isPlaying = false
        view.display(model)
        view.scene = model.scene
        view.scene?.background.contents = UIColor.white
        view.pointOfView = model.camera

        func projectedCorners(for node: SCNNode) -> [SCNVector3] {
            let bounds = node.boundingBox
            let corners = [bounds.min.x, bounds.max.x].flatMap { x in
                [bounds.min.y, bounds.max.y].flatMap { y in
                    [bounds.min.z, bounds.max.z].map { z in SCNVector3(x, y, z) }
                }
            }
            return corners.map { view.projectPoint(node.convertPosition($0, to: nil)) }
        }

        func assertProjected(_ nodes: [SCNNode], _ label: String) {
            let points = nodes.flatMap(projectedCorners)
            XCTAssertFalse(points.isEmpty, "\(label) must have projected geometry")
            let visible = points.filter { point in
                point.x >= 0 && point.x <= Float(view.bounds.width) &&
                point.y >= 0 && point.y <= Float(view.bounds.height) &&
                point.z >= 0 && point.z <= 1
            }
            let xValues = points.map(\.x)
            let yValues = points.map(\.y)
            let zValues = points.map(\.z)
            XCTAssertFalse(
                visible.isEmpty,
                "\(label) must intersect the viewport with visible depth; " +
                "x=\(xValues.min() ?? .nan)...\(xValues.max() ?? .nan), " +
                "y=\(yValues.min() ?? .nan)...\(yValues.max() ?? .nan), " +
                "z=\(zValues.min() ?? .nan)...\(zValues.max() ?? .nan), " +
                "cameraPosition=\(model.camera.position), cameraFront=\(model.camera.simdWorldFront)"
            )
        }

        func assertProjectedPresentation(_ positionID: String, _ label: String, orbit: Bool = false) throws {
            view.positionID = positionID
            view.selectPositionIfNeeded()
            SCNTransaction.flush()

            if orbit {
                model.orbit(azimuth: 0.3, elevation: -0.2, zoomScale: 1.2)
                SCNTransaction.flush()
            }

            assertProjected(model.geometryNodes, "\(label) board")
            guard let cord = model.transientCordNode else {
                XCTFail("\(label) must create a cord node")
                return
            }
            for branchIndex in 0..<2 {
                let segments = cord.childNodes.filter {
                    $0.name?.hasPrefix("suspended.cord.branch.\(branchIndex).") == true
                }
                XCTAssertFalse(segments.isEmpty, "\(label) branch \(branchIndex) must contain cord geometry")
                assertProjected(segments, "\(label) cord branch \(branchIndex)")
            }

            func capture(_ label: String, only predicate: (SCNNode) -> Bool) throws -> CGImage {
                let nodes = model.geometryNodes + [cord] + cord.childNodes
                let visibility = nodes.map { ($0, $0.isHidden) }
                defer {
                    for (node, isHidden) in visibility {
                        node.isHidden = isHidden
                    }
                }
                for node in nodes {
                    node.isHidden = !predicate(node)
                }
                SCNTransaction.flush()
                view.layoutIfNeeded()
                guard let image = view.snapshot().cgImage else {
                    throw XCTSkip("\(label) snapshot did not produce a CGImage")
                }
                XCTAssertTrue(
                    hasNonBackgroundPixels(image),
                    "\(label) isolated snapshot must contain rendered pixels"
                )
                return image
            }

            _ = try capture("\(label) board", only: { node in
                model.geometryNodes.contains { $0 === node }
            })
            for branchIndex in 0..<2 {
                _ = try capture("\(label) cord branch \(branchIndex)", only: { node in
                    node === cord || node.name?.hasPrefix("suspended.cord.branch.\(branchIndex).") == true
                })
            }
        }

        try assertProjectedPresentation("three-edge-upright", "three-edge control")
        try assertProjectedPresentation("two-edge-upright", "two-edge", orbit: true)
    }

    func testNatureStoneHangerCatalogUsesExactDefaultModelContract() throws {
        let board = try XCTUnwrap(BoardCatalog.packageStore.board(id: "nature.stone-hanger"))
        let presentation = board.defaultPresentation
        guard case .model(let media) = presentation.media else {
            return XCTFail("Nature Stone Hanger must route through model media")
        }
        let expectedHoldIDs = [
            "edge-front-15mm-incut",
            "edge-front-15mm-flat",
            "edge-front-20mm-wood-flat",
            "edge-front-20mm-granite",
            "edge-reverse-10mm-incut",
            "edge-reverse-10mm-flat",
            "edge-reverse-06mm-flat",
            "edge-reverse-06mm-incut",
        ]

        XCTAssertEqual(board.id, "nature.stone-hanger")
        XCTAssertEqual(presentation.id, "primary")
        XCTAssertTrue(presentation.isDefault)
        XCTAssertEqual(board.contacts.map(\.id), expectedHoldIDs)
        XCTAssertEqual(Set(media.descriptor.contacts.keys), Set(expectedHoldIDs))
        XCTAssertEqual(media.assetPath, "assets/primary.usdz")
        XCTAssertEqual(media.descriptorPath, "assets/primary.model.json")
        XCTAssertEqual(media.display.camera.type, "orthographic")
        XCTAssertEqual(media.display.camera.viewDirection, [0, 0, -1])
        XCTAssertEqual(media.display.camera.up, [0, 1, 0])
        XCTAssertEqual(media.display.camera.fitPadding, 0.08)

        let descriptorURL = try XCTUnwrap(
            BoardCatalog.packageStore.presentationDescriptorURL(for: board, presentationID: presentation.id)
        )
        XCTAssertNil(
            BoardCatalog.packageStore.presentationAssetURL(for: board, presentationID: presentation.id)
        )
        XCTAssertEqual(
            BoardCatalog.packageStore.modelResource(for: board, presentationID: presentation.id),
            BoardModelResource(
                packageSlug: "nature-stone-hanger",
                assetPath: "assets/primary.usdz"
            )
        )
        XCTAssertTrue(descriptorURL.path.hasSuffix("/Hangboards/nature-stone-hanger/assets/primary.model.json"))
        XCTAssertNil(BoardCatalog.packageStore.presentationImageURL(for: board, presentationID: presentation.id))
    }

    func testNatureStoneHangerUsesApprovedPairedLeadSuspension() async throws {
        let (loadedBoard, media, model) = try await loadMigratedModel("nature.stone-hanger")
        guard case .model = loadedBoard.defaultPresentation.media else {
            return XCTFail("Nature Stone Hanger must route through model media")
        }

        guard case .pairedLeadCord(let suspension) = media.suspension else {
            return XCTFail("Nature Stone Hanger must load the approved pairedLeadCord suspension")
        }
        XCTAssertEqual(suspension.attachments.count, 2)
        XCTAssertTrue(model.select(positionID: "front"))
        XCTAssertFalse(model.isUnavailable)
        XCTAssertFalse(model.isTransientCordAccessible)
        XCTAssertEqual(model.transientCordNode?.childNodes.count, 2 * (SuspendedCordSolver.sampleCount - 1))
    }

    func testNatureStoneHangerHighlightsNativeContactMaterialsAndClearsThem() async throws {
        let (board, _, model) = try await loadMigratedModel("nature.stone-hanger")
        let highlightedID = "edge-front-20mm-granite"
        let untouchedID = "edge-front-20mm-wood-flat"
        let highlightedNode = try XCTUnwrap(model.contactNodes[highlightedID]?.first)
        let untouchedNode = try XCTUnwrap(model.contactNodes[untouchedID]?.first)
        let highlightedOriginal = try XCTUnwrap(highlightedNode.geometry?.firstMaterial)
        let untouchedOriginal = try XCTUnwrap(untouchedNode.geometry?.firstMaterial)

        XCTAssertEqual(model.contactNodes.count, board.contacts.count)
        model.highlight([highlightedID], mode: .active)
        XCTAssertEqual(
            highlightedNode.geometry?.firstMaterial?.diffuse.contents as? UIColor,
            UIColor(Color.holdActive)
        )
        XCTAssertFalse(highlightedNode.geometry?.firstMaterial === highlightedOriginal)
        XCTAssertTrue(untouchedNode.geometry?.firstMaterial === untouchedOriginal)

        model.highlight([], mode: .active)
        XCTAssertTrue(highlightedNode.geometry?.firstMaterial === highlightedOriginal)
        XCTAssertTrue(untouchedNode.geometry?.firstMaterial === untouchedOriginal)
    }

    // Regression guard for visual validation: the shipped Nature package must
    // build a non-empty scene and resolve a finite camera on both canonical
    // faces. A blank 3D card with no unavailable state means this contract
    // broke between the loader and the renderer.
    func testNatureStoneHangerOrientationSelectsBothFacesWithVisibleFraming() async throws {
        let (board, media, model) = try await loadMigratedModel("nature.stone-hanger")
        guard case .pairedLeadCord(let suspension) = media.suspension else {
            return XCTFail("Nature Stone Hanger must load the approved pairedLeadCord suspension")
        }
        XCTAssertEqual(suspension.canonicalPoses["front"]?.rotation, [0, 0, 0, 1])
        XCTAssertEqual(suspension.canonicalPoses["reverse"]?.rotation, [0, 1, 0, 0])
        XCTAssertFalse(model.geometryNodes.isEmpty, "Nature scene must contain geometry")
        XCTAssertEqual(model.contactNodes.count, board.contacts.count)
        try assertVisibleFraming(model, positionIDs: ["front", "reverse"])
        // NOTE: head-on CPU rays at descriptor face-plane centers intentionally
        // are NOT asserted here. The Stone Hanger's recess interiors belong to
        // the body mesh while only the contact lips are hold meshes, so such
        // rays legitimately strike body first. Tap selection operates on
        // rendered pixels (covered by visual validation), not descriptor
        // rays; the descriptor AABB-to-mouth alignment is tracked separately
        // as a data-fidelity follow-up.
        XCTAssertTrue(model.select(positionID: "front"))
        XCTAssertEqual(model.activePositionID, "front")
    }

    // Same end-to-end guard for every reviewed Baguette position: selection
    // must succeed, keep hold bindings, and leave a finite camera.
    func testBaguetteEvoOrientationSelectsAllReviewedPositionsWithVisibleFraming() async throws {
        let (board, media, model) = try await loadMigratedModel("yy.baguette-evo")
        let orientation = try XCTUnwrap(media.orientation, "Baguette must declare orientation metadata")
        let expectedIDs = [
            "paired-25-20-15-10",
            "paired-12-8-6",
            "central-30-25",
            "central-20-6",
            "rounded-tray",
        ]
        XCTAssertEqual(Set(orientation.rotations.keys), Set(expectedIDs))
        XCTAssertEqual(board.positions.map(\.id), expectedIDs)
        XCTAssertFalse(model.geometryNodes.isEmpty, "Baguette scene must contain geometry")
        XCTAssertEqual(model.contactNodes.count, board.contacts.count)
        try assertVisibleFraming(model, positionIDs: expectedIDs)
    }

    func testPromotedModelMatchesItsV3PhysicalContactInventory() async throws {
        let (board, media, model) = try await loadMigratedModel("yy.baguette-evo")
        let approvedModelSHA256 = "a155242e9f1d230eca31c4b5ce855a1eddc82722ca3da7187ce3c3efc8a4c6bc"
        let approvedDescriptorSHA256 = "1b6f5a4048104a9d0b5b1a1c60002270332ddb54bd0e9a13f057594f34487f47"
        let expectedContactIDs = [
            "edge-20-left", "edge-10-left", "edge-25-left", "edge-15-left",
            "edge-15-right", "edge-25-right", "edge-10-right", "edge-20-right",
            "edge-12-left", "edge-12-right", "edge-8-left", "edge-8-right",
            "edge-6-upper", "edge-6-lower", "edge-central-30", "edge-central-25",
            "edge-central-20", "edge-central-6", "rounded-tray",
        ]

        XCTAssertEqual(board.contacts.map(\.id), expectedContactIDs)
        XCTAssertEqual(Set(media.descriptor.contacts.keys), Set(expectedContactIDs))
        XCTAssertEqual(Set(model.contactNodes.keys), Set(expectedContactIDs))
        XCTAssertEqual(media.descriptor.nodes.filter { $0.role == .body }.count, 1)
        XCTAssertEqual(media.descriptor.nodes.filter { $0.role == .contact }.count, 20)
        XCTAssertEqual(model.geometryNodes.count, 21)
        XCTAssertEqual(model.contactNodes["rounded-tray"]?.count, 2)
        XCTAssertNil(BoardCatalog.packageStore.presentationImageURL(for: board))
        XCTAssertEqual(media.descriptor.modelSHA256, approvedModelSHA256)

        let expectedBindings = [
            "body_mesh_001|body|-",
            "hold_central_06mm_mesh_001|contact|edge-central-6",
            "hold_central_20mm_mesh_001|contact|edge-central-20",
            "hold_central_25mm_mesh_001|contact|edge-central-25",
            "hold_central_30mm_mesh_001|contact|edge-central-30",
            "hold_edge_06mm_left_mesh_001|contact|edge-6-upper",
            "hold_edge_06mm_right_mesh_001|contact|edge-6-lower",
            "hold_edge_08mm_left_mesh_001|contact|edge-8-left",
            "hold_edge_08mm_right_mesh_001|contact|edge-8-right",
            "hold_edge_10mm_left_mesh_001|contact|edge-10-left",
            "hold_edge_10mm_right_mesh_001|contact|edge-10-right",
            "hold_edge_12mm_left_mesh_001|contact|edge-12-left",
            "hold_edge_12mm_right_mesh_001|contact|edge-12-right",
            "hold_edge_15mm_left_mesh_001|contact|edge-15-left",
            "hold_edge_15mm_right_mesh_001|contact|edge-15-right",
            "hold_edge_20mm_left_mesh_001|contact|edge-20-left",
            "hold_edge_20mm_right_mesh_001|contact|edge-20-right",
            "hold_edge_25mm_left_mesh_001|contact|edge-25-left",
            "hold_edge_25mm_right_mesh_001|contact|edge-25-right",
            "hold_rounded_left_mesh_001|contact|rounded-tray",
            "hold_rounded_right_mesh_001|contact|rounded-tray",
        ]
        let actualBindings = media.descriptor.nodes.map {
            "\($0.nodeID)|\($0.role.rawValue)|\($0.contactID ?? "-")"
        }
        XCTAssertEqual(actualBindings, expectedBindings)

        let resource = try XCTUnwrap(BoardCatalog.packageStore.modelResource(for: board))
        let descriptorURL = try XCTUnwrap(BoardCatalog.packageStore.presentationDescriptorURL(for: board))
        let descriptorData = try Data(contentsOf: descriptorURL)
        let descriptorSHA256 = SHA256.hash(data: descriptorData)
            .map { String(format: "%02x", $0) }
            .joined()
        XCTAssertEqual(descriptorSHA256, approvedDescriptorSHA256)
        XCTAssertEqual(
            resource,
            BoardModelResource(
                packageSlug: "yy-baguette-evo",
                assetPath: "assets/primary.usdz"
            )
        )
        XCTAssertNil(BoardCatalog.packageStore.presentationAssetURL(for: board))
        let packageURL = repositoryRootURL()
            .appendingPathComponent("Hangboards", isDirectory: true)
            .appendingPathComponent(resource.packageSlug, isDirectory: true)
        let assetURL = packageURL.appendingPathComponent(resource.assetPath)
        let packageFiles = try FileManager.default.contentsOfDirectory(atPath: packageURL.path)
        let assetFiles = try FileManager.default.contentsOfDirectory(
            atPath: assetURL.deletingLastPathComponent().path
        )
        XCTAssertEqual(Set(packageFiles), ["assets", "board.json"])
        XCTAssertEqual(Set(assetFiles), ["primary.model.json", "primary.usdz"])
    }

    func testBaguetteEvoNativeNearestTrianglePickingCoversEveryContactPiece() async throws {
        try await assertNativeNearestTrianglePicking(boardID: "yy.baguette-evo")
    }

    func testCollectionModelsNativeNearestTrianglePickingCoversEveryContactPiece() async throws {
        for boardID in [
            "metolius.climbers-edge", "metolius.contact", "metolius.simulator-3d",
            "soill.training-tiles", "the-hangboard.the-hangboard",
            "trango.rock-prodigy-training-center",
        ] {
            try await assertNativeNearestTrianglePicking(boardID: boardID)
        }
    }

    private func assertNativeNearestTrianglePicking(boardID: String) async throws {
        let (board, media, model) = try await loadMigratedModel(boardID)
        let view = BoardModelSCNView(frame: CGRect(x: 0, y: 0, width: 800, height: 600))
        view.display(model)
        model.frame(in: view.bounds.size)
        let extent = zip(media.descriptor.modelBounds.minimum, media.descriptor.modelBounds.maximum)
            .map { Float($1 - $0) }
            .max() ?? 1
        let rayExtension = max(extent * 4, 1)

        for position in board.positions {
            XCTAssertTrue(model.select(positionID: position.id), position.id)
            SCNTransaction.flush()
            let reviewAngles: [SIMD2<Float>] = [
                [0, 0], [0.45, 0], [-0.45, 0], [0, 0.4], [0, -0.4],
                [0.35, 0.3], [-0.35, 0.3], [0.35, -0.3], [-0.35, -0.3],
            ]
            for contactID in position.contactIDs {
                let nodes = try XCTUnwrap(model.contactNodes[contactID], "\(position.id): \(contactID)")
                for node in nodes {
                    let raySamples = try nativeTriangleCenters(for: node)
                    let hasNativePick = reviewAngles.contains { angle in
                        model.resetCamera(animated: false)
                        model.orbit(azimuth: angle.x, elevation: angle.y)
                        SCNTransaction.flush()
                        let direction = model.camera.presentation.worldFront
                        return raySamples.contains { localCenter in
                            let center = node.presentation.convertPosition(localCenter, to: model.scene.rootNode)
                            let start = SCNVector3(
                                center.x - direction.x * rayExtension,
                                center.y - direction.y * rayExtension,
                                center.z - direction.z * rayExtension
                            )
                            let end = SCNVector3(
                                center.x + direction.x * rayExtension,
                                center.y + direction.y * rayExtension,
                                center.z + direction.z * rayExtension
                            )
                            let closest = model.scene.rootNode.hitTestWithSegment(
                                from: start,
                                to: end,
                                options: [
                                    SCNHitTestOption.categoryBitMask.rawValue: BoardModelScene.modelPickCategory,
                                    SCNHitTestOption.searchMode.rawValue: SCNHitTestSearchMode.closest.rawValue,
                                ]
                            ).first
                            guard closest?.node === node,
                                  closest.flatMap({ model.contactID(for: $0.node) }) == contactID else {
                                return false
                            }
                            // Exercise the same projected-point nearest hit used by
                            // selectContact, not an accessibility/legend identity lookup.
                            let projected = view.projectPoint(center)
                            let point = CGPoint(x: CGFloat(projected.x), y: CGFloat(projected.y))
                            guard projected.z >= 0, projected.z <= 1, view.bounds.contains(point) else {
                                return false
                            }
                            let screenHit = view.hitTest(point, options: [
                                SCNHitTestOption.categoryBitMask: BoardModelScene.modelPickCategory,
                                SCNHitTestOption.searchMode: SCNHitTestSearchMode.closest.rawValue,
                            ]).first
                            return screenHit?.node === node
                                && screenHit.flatMap { model.contactID(for: $0.node) } == contactID
                        }
                    }
                    XCTAssertTrue(
                        hasNativePick,
                        "\(boardID): \(position.id): \(contactID): \(node.name ?? "unnamed") has no nearest native triangle pick across the reviewed camera angles"
                    )
                }
            }
        }
    }

    func testNatureStoneHangerCordPassageMarkersAreNotSelectableOrAccessible() async throws {
        let (board, media, model) = try await loadMigratedModel("nature.stone-hanger")
        let passageMarkerIDs = ["cord-passage-1", "cord-passage-2"]
        let descriptorNodeIDs = Set(media.descriptor.nodes.map(\.nodeID))

        XCTAssertTrue(passageMarkerIDs.allSatisfy { !descriptorNodeIDs.contains($0) })
        XCTAssertTrue(passageMarkerIDs.allSatisfy { model.contactNodes[$0] == nil })
        XCTAssertEqual(model.geometryNodes.count, board.contacts.count + 1)
        for markerID in passageMarkerIDs {
            let marker = SCNNode()
            marker.name = markerID
            XCTAssertNil(model.contactID(for: marker), markerID)
        }

        let view = BoardModelSCNView(frame: CGRect(x: 0, y: 0, width: 320, height: 320))
        view.display(model)
        view.contacts = board.contacts
        view.onContactTap = { _ in }
        view.updateAccessibility()

        let identifiers = try XCTUnwrap(view.accessibilityElements as? [UIAccessibilityElement])
            .compactMap(\.accessibilityIdentifier)
        XCTAssertEqual(Set(identifiers), Set(board.contacts.map { "boardModel.contact.\($0.id)" }))
        XCTAssertTrue(passageMarkerIDs.allSatisfy { !identifiers.contains("boardModel.contact.\($0)") })
    }

    func testExistingPlanTargetsStillResolveOnMetoliusBaguetteAndTrainingTilesBoards() throws {
        let directPlanBoardIDs: Set<String> = ["metolius.contact", "metolius.simulator-3d"]
        let directPlans = PlanCatalog.all.filter { plan in
            plan.boardID.map(directPlanBoardIDs.contains) == true
        }
        XCTAssertFalse(directPlans.isEmpty)
        for plan in directPlans {
            let board = try XCTUnwrap(plan.boardID.flatMap {
                BoardCatalog.packageStore.board(id: $0)
            })
            for step in plan.steps {
                XCTAssertNoThrow(try ContactResolver.resolve(step.targets, step: step, board: board))
            }
        }

        for boardID in ["yy.baguette-evo", "soill.training-tiles"] {
            let board = try XCTUnwrap(BoardCatalog.packageStore.board(id: boardID))
            let compatibleGenericPlans = PlanCatalog.all.filter { plan in
                plan.boardID == nil && plan.steps.allSatisfy { step in
                    (try? ContactResolver.resolve(step.targets, step: step, board: board)) != nil
                }
            }
            XCTAssertFalse(compatibleGenericPlans.isEmpty, boardID)
            for plan in compatibleGenericPlans {
                for step in plan.steps {
                    let resolvedIDs = try ContactResolver.resolve(step.targets, step: step, board: board).map(\.id)
                    XCTAssertTrue(Set(resolvedIDs).isSubset(of: Set(board.contacts.map(\.id))), "\(plan.id): \(boardID)")
                }
            }
        }

        XCTAssertFalse(PlanCatalog.all.contains { $0.boardID == "nature.stone-hanger" })
    }

    func testExistingRasterAndModelPresentationRoutingDoesNotRegress() throws {
        let modelBoardIDs = [
            "nature.stone-hanger",
            "yy.baguette-evo",
            "metolius.wood-grips-compact-ii",
            "metolius.simulator-3d",
            "soill.training-tiles",
        ]
        let rasterBoardIDs = ["soill.split-palm"]

        for boardID in modelBoardIDs {
            let board = try XCTUnwrap(BoardCatalog.packageStore.board(id: boardID))
            guard case .model(let media) = board.defaultPresentation.media else {
                XCTFail("\(boardID) must remain model-routed")
                continue
            }
            let resource = try XCTUnwrap(BoardCatalog.packageStore.modelResource(for: board))
            XCTAssertNil(BoardCatalog.packageStore.presentationAssetURL(for: board))
            XCTAssertNotNil(BoardCatalog.packageStore.presentationDescriptorURL(for: board))
            XCTAssertEqual(resource.assetPath, media.assetPath)
            XCTAssertEqual(resource.resourceName, "primary")
            XCTAssertEqual(resource.resourceExtension, "usdz")
            XCTAssertNil(BoardCatalog.packageStore.presentationImageURL(for: board))
        }

        for boardID in rasterBoardIDs {
            let board = try XCTUnwrap(BoardCatalog.packageStore.board(id: boardID))
            guard case .raster = board.defaultPresentation.media else {
                XCTFail("\(boardID) must remain raster-routed")
                continue
            }
            XCTAssertNotNil(BoardCatalog.packageStore.presentationAssetURL(for: board))
            XCTAssertNotNil(BoardCatalog.packageStore.presentationImageURL(for: board))
            XCTAssertNil(BoardCatalog.packageStore.presentationDescriptorURL(for: board))
        }
    }

    func testMigratedPackageModelsBindExactInventoriesMaterialsAndNearestHits() async throws {
        for expectation in migratedModelExpectations {
            let (board, media, model) = try await loadMigratedModel(expectation.boardID)

            SCNTransaction.flush()

            XCTAssertEqual(Set(board.contacts.map(\.id)), expectation.contactIDs, expectation.boardID)
            XCTAssertEqual(Set(media.descriptor.contacts.keys), expectation.contactIDs, expectation.boardID)
            XCTAssertEqual(Set(model.contactNodes.keys), expectation.contactIDs, expectation.boardID)
            XCTAssertEqual(
                model.contactNodes.values.reduce(0) { $0 + $1.count },
                expectation.contactIDs.count,
                expectation.boardID
            )
            XCTAssertEqual(model.geometryNodes.count, expectation.contactIDs.count + 1, expectation.boardID)

            for node in model.geometryNodes {
                let materials = try XCTUnwrap(node.geometry?.materials, expectation.boardID)
                XCTAssertFalse(materials.isEmpty, "\(expectation.boardID): \(node.name ?? "unnamed")")
                XCTAssertTrue(
                    materials.allSatisfy { $0.diffuse.contents != nil },
                    "\(expectation.boardID): \(node.name ?? "unnamed")"
                )
            }

            try assertNearestHeadOnHitForEveryContact(model, media: media, boardID: expectation.boardID)
            try assertBodyHitIsNotSelectable(
                model,
                media: media,
                normalizedPoint: expectation.bodyProbe,
                boardID: expectation.boardID
            )
        }
    }

    func testModelSurfaceUnavailableStateNeverPermitsContactSelection() {
        XCTAssertFalse(BoardModelSurface.permitsContactSelection(
            for: .unavailable,
            onContactTap: { _ in }
        ))
        XCTAssertFalse(BoardModelSurface.permitsContactSelection(
            for: .loading,
            onContactTap: { _ in }
        ))
        XCTAssertTrue(BoardModelSurface.permitsContactSelection(
            for: .ready,
            onContactTap: { _ in }
        ))
    }

    func testModelAccessibilityEnumeratesOnlyDescriptorBoundContacts() throws {
        let descriptor = modelDescriptor(nodes: [
            .init(nodeID: "Board/Body", role: .body, contactID: nil),
            .init(nodeID: "Board/Hold/Left", role: .contact, contactID: "left")
        ])
        let model = try XCTUnwrap(BoardModelScene(
            source: scene(nodes: ["Board/Body", "Board/Hold/Left"]),
            descriptor: descriptor,
            display: display()
        ))
        let boundContact = PhysicalContact(id: "left", name: "Bound left", kind: .edge)
        let unboundContact = PhysicalContact(id: "not-in-descriptor", name: "Unbound", kind: .edge)
        let view = BoardModelSCNView(frame: CGRect(x: 0, y: 0, width: 320, height: 160))

        view.display(model)
        view.contacts = [boundContact, unboundContact]
        view.onContactTap = { _ in }
        view.updateAccessibility()

        let elements = try XCTUnwrap(view.accessibilityElements as? [UIAccessibilityElement])
        XCTAssertEqual(elements.compactMap(\.accessibilityIdentifier), ["boardModel.contact.left"])
        XCTAssertEqual(elements.compactMap(\.accessibilityLabel), ["Bound left"])
    }

    // This proves disconnected body components remain visible geometry while
    // only exact physical-contact meshes participate in selection.
    func testTwoBodyModelBindsEachContactAndDoesNotMakeBodyTappable() throws {
        let descriptor = modelDescriptor(nodes: [
            .init(nodeID: "left-body", role: .body, contactID: nil),
            .init(nodeID: "left-edge-node", role: .contact, contactID: "left-edge"),
            .init(nodeID: "mounting-plate", role: .attachment, contactID: nil),
            .init(nodeID: "right-body", role: .body, contactID: nil),
            .init(nodeID: "right-edge-node", role: .contact, contactID: "right-edge")
        ])
        let model = try XCTUnwrap(BoardModelScene(
            source: scene(nodes: ["left-body", "left-edge-node", "mounting-plate", "right-body", "right-edge-node"]),
            descriptor: descriptor,
            display: display()
        ))

        XCTAssertEqual(model.contactNodes.keys.sorted(), ["left-edge", "right-edge"])
        for nonContactName in ["left-body", "mounting-plate", "right-body"] {
            let nonContact = try XCTUnwrap(model.geometryNodes.first { $0.name == nonContactName })
            XCTAssertEqual(nonContact.categoryBitMask, BoardModelScene.modelVisibleCategory)
            XCTAssertNotEqual(nonContact.categoryBitMask, BoardModelScene.modelPickCategory)
            XCTAssertNil(model.contactID(for: nonContact))
        }
        for contactID in ["left-edge", "right-edge"] {
            let contact = try XCTUnwrap(model.contactNodes[contactID]?.first)
            XCTAssertEqual(contact.categoryBitMask, BoardModelScene.modelPickCategory)
            XCTAssertEqual(model.contactID(for: contact), contactID)
        }
    }

    func testModelLightsIlluminateEveryRenderedBoardCategory() throws {
        let descriptor = modelDescriptor(nodes: [
            .init(nodeID: "body", role: .body, contactID: nil),
            .init(nodeID: "hold", role: .contact, contactID: "hold"),
            .init(nodeID: "attachment", role: .attachment, contactID: nil)
        ])
        let suspension = BoardModelPairedLeadCord(
            attachments: [
                .init(id: "left", nodeID: "body", pointInModel: [0.2, 0.4, 0.1], provenance: "test"),
                .init(id: "right", nodeID: "body", pointInModel: [0.8, 0.4, 0.1], provenance: "test")
            ],
            passages: BoardModelPassagePairs(
                left: [BoardModelPassage(id: "left-lip", nodeID: "body", pointInModel: [0.2, 0.4, 0.1], provenance: "test")],
                right: [BoardModelPassage(id: "right-lip", nodeID: "body", pointInModel: [0.8, 0.4, 0.1], provenance: "test")]
            ),
            anchor: .init(offsetFromBoardBounds: [0, 0, 0], visibility: "invisible", provenance: "test", position: [0, 2, 0]),
            cord: .init(restLength: 2, radius: 0.01, material: "test", provenance: "test"),
            canonicalPoses: ["primary": BoardModelCanonicalPose(
                rotation: [0, 0, 0, 1], translation: [0, 0, 0],
                camera: .init(viewDirection: [0, 0, 1], fitPadding: 0.1)
            )]
        )
        let model = try XCTUnwrap(BoardModelScene(
            source: scene(nodes: ["body", "hold", "attachment"]),
            descriptor: descriptor,
            display: display(),
            suspension: .pairedLeadCord(suspension)
        ))
        XCTAssertTrue(model.select(positionID: "primary"))

        var lights: [SCNLight] = []
        model.scene.rootNode.enumerateChildNodes { node, _ in
            if let light = node.light { lights.append(light) }
        }
        XCTAssertFalse(lights.isEmpty)
        let body = try XCTUnwrap(model.geometryNodes.first { $0.name == "body" })
        let contact = try XCTUnwrap(model.geometryNodes.first { $0.name == "hold" })
        let attachment = try XCTUnwrap(model.geometryNodes.first { $0.name == "attachment" })
        let cord = try XCTUnwrap(model.transientCordNode?.childNodes.first)
        XCTAssertEqual(contact.categoryBitMask, 1)
        XCTAssertEqual(cord.categoryBitMask, 2)
        XCTAssertEqual(body.categoryBitMask, 4)
        XCTAssertEqual(attachment.categoryBitMask, 4)
        XCTAssertNotEqual(contact.categoryBitMask, cord.categoryBitMask)
        XCTAssertNotEqual(contact.categoryBitMask, body.categoryBitMask)
        XCTAssertNotEqual(cord.categoryBitMask, body.categoryBitMask)
        let renderedNodes = [contact, cord, body, attachment]
        for light in lights {
            for node in renderedNodes {
                XCTAssertNotEqual(light.categoryBitMask & node.categoryBitMask, 0,
                                  "Every model light must illuminate every rendered board category")
            }
        }
    }

    // This catches a renderer that accepts names by suffix, normalization, or
    // descriptor subsets instead of binding the importer-visible node paths.
    func testGenericModelBindingUsesExactDescriptorNodeIDs() throws {
        let source = scene(nodes: ["Board/Body", "Board/Hold/Left"])
        let descriptor = modelDescriptor(nodes: [
            .init(nodeID: "Board/Body", role: .body, contactID: nil),
            .init(nodeID: "Board/Hold/Left", role: .contact, contactID: "left")
        ])

        let model = try XCTUnwrap(BoardModelScene(
            source: source,
            descriptor: descriptor,
            display: display()
        ))

        XCTAssertEqual(Set(model.contactNodes.keys), ["left"])
        XCTAssertEqual(model.geometryNodes.count, 2)
        XCTAssertEqual(model.contactID(for: try XCTUnwrap(model.contactNodes["left"]?.first)), "left")
        XCTAssertNil(model.contactID(for: try XCTUnwrap(model.geometryNodes.first { $0.name == "Body" })))

        let mismatched = modelDescriptor(nodes: [
            .init(nodeID: "Board/Body", role: .body, contactID: nil),
            .init(nodeID: "left", role: .contact, contactID: "left")
        ])
        XCTAssertNil(BoardModelScene(source: source, descriptor: mismatched, display: display()))
    }

    func testPairedLeadSceneBindingAllowsDistinctPointsOnOneBodyNode() throws {
        let descriptor = modelDescriptor(nodes: [
            .init(nodeID: "Body", role: .body, contactID: nil),
            .init(nodeID: "Hold", role: .contact, contactID: "hold")
        ])
        let suspension = BoardModelPairedLeadCord(
            attachments: [
                .init(id: "left", nodeID: "Body", pointInModel: [0.2, 0.4, 0.1], provenance: "test"),
                .init(id: "right", nodeID: "Body", pointInModel: [0.8, 0.4, 0.1], provenance: "test")
            ],
            passages: BoardModelPassagePairs(
                left: [BoardModelPassage(id: "left-lip", nodeID: "Body", pointInModel: [0.2, 0.4, 0.1], provenance: "test")],
                right: [BoardModelPassage(id: "right-lip", nodeID: "Body", pointInModel: [0.8, 0.4, 0.1], provenance: "test")]
            ),
            anchor: .init(offsetFromBoardBounds: [0, 0, 0], visibility: "invisible", provenance: "test", position: [0, 2, 0]),
            cord: .init(restLength: 2, radius: 0.01, material: "test", provenance: "test"),
            canonicalPoses: ["primary": BoardModelCanonicalPose(rotation: [0, 0, 0, 1], translation: [0, 0, 0], camera: .init(viewDirection: [0, 0, 1], fitPadding: 0.1))]
        )
        let model = try XCTUnwrap(BoardModelScene(
            source: scene(nodes: ["Body", "Hold"]), descriptor: descriptor, display: display(), suspension: .pairedLeadCord(suspension)
        ))

        XCTAssertTrue(model.select(positionID: "primary"))
        XCTAssertFalse(model.isUnavailable)
        XCTAssertEqual(model.transientCordNode?.childNodes.count, 2 * (SuspendedCordSolver.sampleCount - 1))
    }

    // This catches a renderer that silently renders nodes the descriptor did
    // not bind, which would make body geometry or arbitrary importer meshes tappable.
    func testGenericModelBindingRejectsUnlistedGeometryAndInvalidMeshInputs() {
        let descriptor = modelDescriptor(nodes: [
            .init(nodeID: "Board/Body", role: .body, contactID: nil),
            .init(nodeID: "Board/Hold/Left", role: .contact, contactID: "left")
        ])

        XCTAssertNil(BoardModelScene(
            source: scene(nodes: ["Board/Body", "Board/Hold/Left", "Board/Extra"]),
            descriptor: descriptor,
            display: display()
        ))
        XCTAssertNil(BoardModelScene(
            source: scene(nodes: ["Board/Body", "Board/Hold/Left"], materiallessPath: "Board/Hold/Left"),
            descriptor: descriptor,
            display: display()
        ))
    }

    func testGenericModelBindingRejectsGeometryOnImportedRoot() {
        let descriptor = modelDescriptor(nodes: [
            .init(nodeID: "Board/Body", role: .body, contactID: nil),
            .init(nodeID: "Board/Hold/Left", role: .contact, contactID: "left")
        ])
        let source = scene(nodes: ["Board/Body", "Board/Hold/Left"])
        let rootGeometry = SCNBox(width: 0.1, height: 0.1, length: 0.1, chamferRadius: 0)
        rootGeometry.firstMaterial = SCNMaterial()
        source.rootNode.geometry = rootGeometry

        XCTAssertNil(BoardModelScene(source: source, descriptor: descriptor, display: display()))
    }

    func testHighlightsRestoreClonedMaterialsAcrossGenericViews() throws {
        let descriptor = modelDescriptor(nodes: [
            .init(nodeID: "Board/Body", role: .body, contactID: nil),
            .init(nodeID: "Board/Hold/Left", role: .contact, contactID: "left")
        ])
        let source = scene(nodes: ["Board/Body", "Board/Hold/Left"])
        let first = try XCTUnwrap(BoardModelScene(source: source, descriptor: descriptor, display: display()))
        let second = try XCTUnwrap(BoardModelScene(source: source, descriptor: descriptor, display: display()))
        let firstNode = try XCTUnwrap(first.contactNodes["left"]?.first)
        let secondNode = try XCTUnwrap(second.contactNodes["left"]?.first)
        let original = try XCTUnwrap(firstNode.geometry?.firstMaterial)
        let otherOriginal = try XCTUnwrap(secondNode.geometry?.firstMaterial)

        XCTAssertFalse(original === otherOriginal)
        first.highlight(["left"], mode: .active)
        XCTAssertEqual(firstNode.geometry?.firstMaterial?.diffuse.contents as? UIColor, UIColor(Color.holdActive))
        XCTAssertTrue(secondNode.geometry?.firstMaterial === otherOriginal)
        first.highlight([], mode: .active)
        XCTAssertTrue(firstNode.geometry?.firstMaterial === original)
        first.highlight(["left"], mode: .preview)
        XCTAssertEqual(firstNode.geometry?.firstMaterial?.diffuse.contents as? UIColor, UIColor(Color.restBlue))
        first.highlight([], mode: .preview)
        XCTAssertTrue(firstNode.geometry?.firstMaterial === original)
    }

    func testExistingViewRebindsDescriptorFramedReplacementSceneAndCamera() throws {
        let firstDescriptor = modelDescriptor(nodes: [
            .init(nodeID: "Board/Body", role: .body, contactID: nil),
            .init(nodeID: "Board/Hold/Left", role: .contact, contactID: "left")
        ], minimum: [-1, -0.5, -0.1], maximum: [1, 0.5, 0.1])
        let replacementDescriptor = modelDescriptor(nodes: [
            .init(nodeID: "Board/Body", role: .body, contactID: nil),
            .init(nodeID: "Board/Hold/Left", role: .contact, contactID: "left")
        ], minimum: [10, 20, 30], maximum: [14, 26, 32])
        let source = scene(nodes: ["Board/Body", "Board/Hold/Left"])
        let first = try XCTUnwrap(BoardModelScene(
            source: source,
            descriptor: firstDescriptor,
            display: display(viewDirection: [0, 0, -1], up: [0, 1, 0], padding: 0.1)
        ))
        let replacement = try XCTUnwrap(BoardModelScene(
            source: source,
            descriptor: replacementDescriptor,
            display: display(viewDirection: [1, 0, 0], up: [0, 0, 1], padding: 0.3)
        ))
        let view = BoardModelSCNView(frame: CGRect(x: 0, y: 0, width: 350, height: 100))

        view.display(first)
        view.display(replacement)

        XCTAssertTrue(view.scene === replacement.scene)
        XCTAssertTrue(view.pointOfView === replacement.camera)
        XCTAssertTrue(view.model === replacement)
        XCTAssertFalse(view.scene === first.scene)
        XCTAssertNotEqual(first.camera.position.x, replacement.camera.position.x)
        XCTAssertNotEqual(first.camera.position.y, replacement.camera.position.y)
        XCTAssertNotEqual(first.camera.position.z, replacement.camera.position.z)
        XCTAssertNotEqual(first.camera.camera?.orthographicScale, replacement.camera.camera?.orthographicScale)
        view.scene = nil
        view.model = nil
    }

    func testCameraFramingFillsTheDeclaredPresentationAspect() throws {
        let descriptor = modelDescriptor(
            nodes: [
                .init(nodeID: "Board/Body", role: .body, contactID: nil),
                .init(nodeID: "Board/Hold/Left", role: .contact, contactID: "left")
            ],
            minimum: [0, 0, 0],
            maximum: [3.86, 1, 0.1]
        )
        let model = try XCTUnwrap(BoardModelScene(
            source: scene(nodes: ["Board/Body", "Board/Hold/Left"]),
            descriptor: descriptor,
            display: display(padding: 0.08)
        ))

        model.frame(in: CGSize(width: 386, height: 100))

        // SceneKit's orthographic scale is half the visible height.
        XCTAssertEqual(try XCTUnwrap(model.camera.camera?.orthographicScale), 0.5, accuracy: 0.000_001)
    }

    // This catches cancellation of the camera-depth term in the key-light
    // position, which turns the intended front-above key into a top-only key.
    func testDirectionalKeyLightIlluminatesTheCameraFacingSurface() throws {
        let descriptor = modelDescriptor(nodes: [
            .init(nodeID: "Board/Body", role: .body, contactID: nil),
            .init(nodeID: "Board/Hold/Left", role: .contact, contactID: "left")
        ])
        let model = try XCTUnwrap(BoardModelScene(
            source: scene(nodes: ["Board/Body", "Board/Hold/Left"]),
            descriptor: descriptor,
            display: display(viewDirection: [0, 0, -1], up: [0, 1, 0])
        ))
        let key = try XCTUnwrap(model.scene.rootNode.childNodes.first {
            $0.light?.type == .directional
        })
        SCNTransaction.flush()
        let keyDirection = key.presentation.worldFront

        XCTAssertLessThan(
            keyDirection.z,
            -0.5,
            "the key must point substantially along the camera view direction, not only down from above"
        )
    }

    func testClosestNativeHitResolvesOnlyTheFrontDescriptorBoundContact() throws {
        let descriptor = modelDescriptor(nodes: [
            .init(nodeID: "Board/Body", role: .body, contactID: nil),
            .init(nodeID: "Board/Hold/Left", role: .contact, contactID: "left")
        ])
        let source = scene(nodes: ["Board/Body", "Board/Hold/Left"])
        let holdNode = try XCTUnwrap(node(at: "Board/Hold/Left", in: source))
        holdNode.position.z = 0.1
        let model = try XCTUnwrap(BoardModelScene(source: source, descriptor: descriptor, display: display()))

        SCNTransaction.flush()
        let hits = model.scene.rootNode.hitTestWithSegment(
            from: SCNVector3(0, 0, 1),
            to: SCNVector3(0, 0, -1),
            options: [SCNHitTestOption.searchMode.rawValue: SCNHitTestSearchMode.closest.rawValue]
        )
        let closest = try XCTUnwrap(hits.first)

        XCTAssertEqual(model.contactID(for: closest.node), "left")
        XCTAssertNil(model.contactID(for: try XCTUnwrap(model.geometryNodes.first { $0.name == "Body" })))
    }

    private struct MigratedModelExpectation {
        let boardID: String
        let contactIDs: Set<String>
        let bodyProbe: [Double]
    }

    private var migratedModelExpectations: [MigratedModelExpectation] {
        [
            MigratedModelExpectation(
                boardID: "beastmaker-1000",
                contactIDs: [
                    "jug-left", "jug-right", "sloper-35-left", "sloper-35-right", "sloper-center",
                    "pocket-top-outer-left", "pocket-top-outer-right", "pocket-top-left", "pocket-top-right",
                    "pocket-middle-outer-left", "pocket-middle-mid-left", "pocket-middle-inner-left",
                    "pocket-middle-center", "pocket-middle-inner-right", "pocket-middle-mid-right",
                    "pocket-middle-outer-right", "pocket-bottom-outer-left", "pocket-bottom-mid-left",
                    "pocket-bottom-inner-left", "pocket-bottom-inner-right", "pocket-bottom-mid-right",
                    "pocket-bottom-outer-right"
                ],
                bodyProbe: [0.5, 0.02]
            ),
            MigratedModelExpectation(
                boardID: "metolius.wood-grips-compact-ii",
                contactIDs: [
                    "jug-left", "sloper-flat-left", "sloper-round-center", "sloper-flat-right", "jug-right",
                    "edge-29-left", "pocket-29-three-left", "pocket-29-two-left", "pocket-29-four-center",
                    "pocket-29-two-right", "pocket-29-three-right", "edge-29-right", "edge-19-left",
                    "pocket-19-three-left", "pocket-19-three-right", "pocket-19-two-left",
                    "pocket-19-two-right", "pocket-19-four-center", "edge-19-right"
                ],
                bodyProbe: [0.5, 0.02]
            )
        ]
    }

    private func loadMigratedModel(
        _ boardID: String
    ) async throws -> (BoardRevision, BoardModelMedia, BoardModelScene) {
        let board = try XCTUnwrap(BoardCatalog.packageStore.board(id: boardID), boardID)
        let presentation = board.defaultPresentation
        let candidateMedia: BoardModelMedia? = if case .model(let media) = presentation.media {
            media
        } else {
            nil
        }
        let media = try XCTUnwrap(candidateMedia, "\(boardID) is not a package model")
        let resource = try XCTUnwrap(
            BoardCatalog.packageStore.modelResource(
                for: board,
                presentationID: presentation.id
            ),
            boardID
        )
        let packageURL = repositoryRootURL()
            .appendingPathComponent("Hangboards", isDirectory: true)
            .appendingPathComponent(resource.packageSlug, isDirectory: true)
            .appendingPathComponent(resource.assetPath)
        // The hosted app can load the same catalog model concurrently. Give this
        // assertion its own cache identity without changing any model metadata.
        let isolatedBundleURL = FileManager.default.temporaryDirectory
            .appendingPathComponent(
                "BoardModelTests-\(UUID().uuidString).bundle",
                isDirectory: true
            )
        defer { try? FileManager.default.removeItem(at: isolatedBundleURL) }
        let isolatedPackageURL = isolatedBundleURL
            .appendingPathComponent("Hangboards/\(resource.packageSlug)", isDirectory: true)
        let descriptorURL = try XCTUnwrap(
            BoardCatalog.packageStore.presentationDescriptorURL(for: board)
        )
        try FileManager.default.createDirectory(
            at: isolatedPackageURL.appendingPathComponent("assets", isDirectory: true),
            withIntermediateDirectories: true
        )
        let boardURL = try XCTUnwrap(Bundle.main.resourceURL)
            .appendingPathComponent("Hangboards/\(resource.packageSlug)/board.json")
        let boardJSON = try String(contentsOf: boardURL, encoding: .utf8)
        let isolatedBoardID = "fixture.migrated-\(UUID().uuidString.lowercased())"
        // Suspension objects require authored member order. Replace only the
        // unique board ID token instead of reserializing and sorting the package.
        let originalIDToken = "\"\(board.id)\""
        XCTAssertEqual(boardJSON.components(separatedBy: originalIDToken).count, 2, boardID)
        let isolatedBoardJSON = boardJSON.replacingOccurrences(
            of: originalIDToken,
            with: "\"\(isolatedBoardID)\""
        )
        try Data(isolatedBoardJSON.utf8)
            .write(to: isolatedPackageURL.appendingPathComponent("board.json"))
        try Data(contentsOf: descriptorURL)
            .write(to: isolatedPackageURL.appendingPathComponent(media.descriptorPath))
        try PropertyListSerialization.data(
            fromPropertyList: [
                "CFBundleIdentifier": "com.hangten.tests.migrated.\(UUID().uuidString)",
                "CFBundlePackageType": "BNDL",
                "CFBundleVersion": "1"
            ],
            format: .xml,
            options: 0
        ).write(to: isolatedBundleURL.appendingPathComponent("Info.plist"))
        let isolatedStore = try BoardPackageStore(
            bundle: XCTUnwrap(Bundle(url: isolatedBundleURL)),
            modelAssetMode: .onDemand
        )
        let isolatedBoard = try XCTUnwrap(isolatedStore.board(id: isolatedBoardID))
        XCTAssertEqual(isolatedBoard.presentations, board.presentations, boardID)
        XCTAssertEqual(isolatedBoard.contacts, board.contacts, boardID)
        XCTAssertEqual(isolatedBoard.positions, board.positions, boardID)
        XCTAssertEqual(isolatedStore.modelResource(for: isolatedBoard), resource, boardID)
        XCTAssertNil(isolatedStore.presentationAssetURL(for: isolatedBoard), boardID)
        let request = ImmediateBoardModelResourceRequest()
        var requestedTags: [Set<String>] = []
        var resolvedURLs: [URL] = []
        let resourceAccess = BoardModelResourceAccess(
            requestFactory: { tags, _ in
                requestedTags.append(tags)
                return request
            },
            urlResolver: { _, requestedResource in
                XCTAssertTrue(request.didBeginAccess, boardID)
                guard requestedResource == resource else { return nil }
                resolvedURLs.append(packageURL)
                return packageURL
            }
        )

        XCTAssertNil(
            BoardCatalog.packageStore.presentationAssetURL(
                for: board,
                presentationID: presentation.id
            ),
            boardID
        )
        let loaded = await BoardModelLoader.load(
            board: isolatedBoard,
            presentation: isolatedBoard.defaultPresentation,
            store: isolatedStore,
            resourceAccess: resourceAccess
        )
        let model = try XCTUnwrap(loaded, boardID)
        XCTAssertEqual(resolvedURLs, [packageURL], boardID)
        XCTAssertEqual(resolvedURLs.first?.lastPathComponent, "primary.usdz", boardID)
        XCTAssertEqual(requestedTags, [[resource.tag]], boardID)
        XCTAssertTrue(request.didBeginAccess, boardID)
        XCTAssertFalse(request.didEndAccess, boardID)
        return (board, media, model)
    }

    private func repositoryRootURL() -> URL {
        URL(fileURLWithPath: #filePath)
            .deletingLastPathComponent()
            .deletingLastPathComponent()
    }

    private func assertVisibleFraming(
        _ model: BoardModelScene,
        positionIDs: [String],
        file: StaticString = #filePath,
        line: UInt = #line
    ) throws {
        for positionID in positionIDs {
            XCTAssertTrue(
                model.select(positionID: positionID),
                positionID,
                file: file,
                line: line
            )
            XCTAssertEqual(model.activePositionID, positionID, file: file, line: line)
            SCNTransaction.flush()
            let cameraPosition = model.camera.position
            XCTAssertTrue(
                cameraPosition.x.isFinite && cameraPosition.y.isFinite && cameraPosition.z.isFinite,
                "\(positionID) camera must be finite: \(cameraPosition)",
                file: file,
                line: line
            )
            let scale = try XCTUnwrap(
                model.camera.camera?.orthographicScale,
                positionID,
                file: file,
                line: line
            )
            XCTAssertTrue(
                scale.isFinite && scale > 0,
                "\(positionID) scale must be positive finite",
                file: file,
                line: line
            )
        }
    }

    private func nativeTriangleCenters(for node: SCNNode) throws -> [SCNVector3] {
        let geometry = try XCTUnwrap(node.geometry, node.name ?? "unnamed")
        let source = try XCTUnwrap(
            geometry.sources(for: .vertex).first,
            "\(node.name ?? "unnamed") has no vertex source"
        )
        guard source.usesFloatComponents,
              source.bytesPerComponent == MemoryLayout<Float>.size else {
            throw NSError(
                domain: "BoardModelTests.nativeTriangleCenters",
                code: 1,
                userInfo: [NSLocalizedDescriptionKey: "unsupported native vertex component layout"]
            )
        }

        func vertex(_ index: Int) throws -> SCNVector3 {
            guard index >= 0, index < source.vectorCount else {
                throw NSError(
                    domain: "BoardModelTests.nativeTriangleCenters",
                    code: 2,
                    userInfo: [NSLocalizedDescriptionKey: "native triangle index exceeds vertex inventory"]
                )
            }
            func component(_ component: Int) -> Float {
                let byteOffset = source.dataOffset + index * source.dataStride
                    + component * source.bytesPerComponent
                return source.data.withUnsafeBytes {
                    $0.loadUnaligned(fromByteOffset: byteOffset, as: Float.self)
                }
            }
            return SCNVector3(component(0), component(1), component(2))
        }

        func index(in element: SCNGeometryElement, at offset: Int) throws -> Int {
            let byteOffset = offset * element.bytesPerIndex
            guard [1, 2, 4, 8].contains(element.bytesPerIndex),
                  byteOffset >= 0,
                  byteOffset + element.bytesPerIndex <= element.data.count else {
                throw NSError(
                    domain: "BoardModelTests.nativeTriangleCenters",
                    code: 3,
                    userInfo: [NSLocalizedDescriptionKey: "unsupported native triangle index layout"]
                )
            }
            return element.data.withUnsafeBytes { bytes in
                switch element.bytesPerIndex {
                case 1: Int(bytes.loadUnaligned(fromByteOffset: byteOffset, as: UInt8.self))
                case 2: Int(bytes.loadUnaligned(fromByteOffset: byteOffset, as: UInt16.self))
                case 4: Int(bytes.loadUnaligned(fromByteOffset: byteOffset, as: UInt32.self))
                default: Int(bytes.loadUnaligned(fromByteOffset: byteOffset, as: UInt64.self))
                }
            }
        }

        var centers: [SCNVector3] = []
        for element in geometry.elements where element.primitiveType == .triangles {
            let plainSize = element.primitiveCount * 3 * element.bytesPerIndex
            let attributeCount = geometry.sources.count
            let importerMultiIndexSize = plainSize * attributeCount
            let layout: (stride: Int, corners: [Int])
            if element.data.count == plainSize {
                layout = (3, [0, 1, 2])
            } else if element.data.count == importerMultiIndexSize,
                      geometry.sources.first?.semantic == .vertex {
                // USD-imported meshes use one index per attribute per corner:
                // vertex/normal, or vertex/normal/UV for textured sources.
                layout = (3 * attributeCount, [0, attributeCount, 2 * attributeCount])
            } else {
                throw NSError(
                    domain: "BoardModelTests.nativeTriangleCenters",
                    code: 4,
                    userInfo: [NSLocalizedDescriptionKey: "\(node.name ?? "unnamed"): unknown native triangle element layout: bytes=\(element.data.count), triangles=\(element.primitiveCount), bytesPerIndex=\(element.bytesPerIndex), sources=\(geometry.sources.map { $0.semantic.rawValue })"]
                )
            }
            for triangle in 0..<element.primitiveCount {
                let base = triangle * layout.stride
                let first = try vertex(index(in: element, at: base + layout.corners[0]))
                let second = try vertex(index(in: element, at: base + layout.corners[1]))
                let third = try vertex(index(in: element, at: base + layout.corners[2]))
                centers.append(SCNVector3(
                    (first.x + second.x + third.x) / 3,
                    (first.y + second.y + third.y) / 3,
                    (first.z + second.z + third.z) / 3
                ))
            }
        }
        XCTAssertFalse(centers.isEmpty, "\(node.name ?? "unnamed") has no native triangles")
        return centers
    }

    private func assertNearestHeadOnHitForEveryContact(
        _ model: BoardModelScene,
        media: BoardModelMedia,
        boardID: String
    ) throws {
        for contactID in media.descriptor.contacts.keys.sorted() {
            let contact = try XCTUnwrap(media.descriptor.contacts[contactID], "\(boardID): \(contactID)")
            let normalizedCenter = zip(contact.facePlaneAABB.minimum, contact.facePlaneAABB.maximum).map {
                $0 + ($1 - $0) / 2
            }
            let ray = try headOnRay(
                normalizedPoint: normalizedCenter,
                bounds: media.descriptor.modelBounds,
                context: "\(boardID): \(contactID)"
            )
            let closest = try XCTUnwrap(
                model.scene.rootNode.hitTestWithSegment(
                    from: ray.from,
                    to: ray.to,
                    options: [
                        SCNHitTestOption.searchMode.rawValue: SCNHitTestSearchMode.closest.rawValue
                    ]
                ).first,
                "\(boardID): \(contactID)"
            )
            XCTAssertEqual(model.contactID(for: closest.node), contactID, "\(boardID): \(contactID)")
        }
    }

    private func assertBodyHitIsNotSelectable(
        _ model: BoardModelScene,
        media: BoardModelMedia,
        normalizedPoint: [Double],
        boardID: String
    ) throws {
        let ray = try headOnRay(
            normalizedPoint: normalizedPoint,
            bounds: media.descriptor.modelBounds,
            context: "\(boardID): body"
        )
        let hits = model.scene.rootNode.hitTestWithSegment(
            from: ray.from,
            to: ray.to,
            options: [
                SCNHitTestOption.categoryBitMask.rawValue: BoardModelScene.modelPickCategory,
                SCNHitTestOption.searchMode.rawValue: SCNHitTestSearchMode.closest.rawValue
            ]
        )
        XCTAssertTrue(hits.isEmpty, "\(boardID): body geometry must not be selectable")
    }

    private func headOnRay(
        normalizedPoint: [Double],
        bounds: BoardModelBounds,
        context: String
    ) throws -> (from: SCNVector3, to: SCNVector3) {
        XCTAssertEqual(normalizedPoint.count, 2, context)
        XCTAssertEqual(bounds.minimum.count, 3, context)
        XCTAssertEqual(bounds.maximum.count, 3, context)
        let x = bounds.minimum[0] + normalizedPoint[0] * (bounds.maximum[0] - bounds.minimum[0])
        let y = bounds.minimum[1] + normalizedPoint[1] * (bounds.maximum[1] - bounds.minimum[1])
        let spans = zip(bounds.minimum, bounds.maximum).map { $1 - $0 }
        let extensionDistance = try XCTUnwrap(spans.max(), context) * 2
        return (
            SCNVector3(Float(x), Float(y), Float(bounds.maximum[2] + extensionDistance)),
            SCNVector3(Float(x), Float(y), Float(bounds.minimum[2] - extensionDistance))
        )
    }

    private func modelDescriptor(
        nodes: [BoardModelNodeDescriptor],
        minimum: [Double] = [0, 0, 0],
        maximum: [Double] = [1, 1, 1]
    ) -> BoardModelDescriptor {
        let holdIDs = Set(nodes.compactMap { $0.role == .contact ? $0.contactID : nil })
        return BoardModelDescriptor(
            schemaVersion: 1,
            coordinateFrame: "hang-ten-board-v1",
            modelSHA256: String(repeating: "0", count: 64),
            modelBounds: .init(minimum: minimum, maximum: maximum),
            nodes: nodes,
            contacts: Dictionary(uniqueKeysWithValues: holdIDs.map { id in
                (
                    id,
                    .init(
                        nodeIDs: nodes.compactMap { $0.contactID == id ? $0.nodeID : nil },
                        facePlaneAABB: .init(minimum: [0, 0], maximum: [1, 1]),
                        center: [0.5, 0.5]
                    )
                )
            })
        )
    }

    private func display(
        viewDirection: [Double] = [0, 0, -1],
        up: [Double] = [0, 1, 0],
        padding: Double = 0.08
    ) -> BoardModelDisplay {
        .init(camera: .init(
            type: "orthographic",
            viewDirection: viewDirection,
            up: up,
            fitPadding: padding
        ))
    }

    private func scene(nodes: [String], materiallessPath: String? = nil) -> SCNScene {
        let source = SCNScene()
        for path in nodes {
            var parent = source.rootNode
            for component in path.split(separator: "/").map(String.init) {
                if let existing = parent.childNodes.first(where: { $0.name == component }) {
                    parent = existing
                } else {
                    let child = SCNNode()
                    child.name = component
                    parent.addChildNode(child)
                    parent = child
                }
            }
            let geometry = SCNBox(width: 0.1, height: 0.1, length: 0.1, chamferRadius: 0)
            if path != materiallessPath {
                geometry.firstMaterial = SCNMaterial()
                geometry.firstMaterial?.diffuse.contents = UIColor.brown
            } else {
                geometry.materials = []
            }
            parent.geometry = geometry
        }
        return source
    }

    private func node(at path: String, in scene: SCNScene) -> SCNNode? {
        var node: SCNNode? = scene.rootNode
        for component in path.split(separator: "/").map(String.init) {
            node = node?.childNodes.first(where: { $0.name == component })
        }
        return node
    }

}

private final class ImmediateBoardModelResourceRequest: BoardModelResourceRequesting {
    let progress = Progress(totalUnitCount: 1)
    private(set) var didBeginAccess = false
    private(set) var didEndAccess = false

    func beginAccessingResources() async throws {
        didBeginAccess = true
    }

    func endAccessingResources() {
        didEndAccess = true
    }
}
