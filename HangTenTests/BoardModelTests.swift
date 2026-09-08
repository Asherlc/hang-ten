import SceneKit
import SwiftUI
import XCTest
@testable import HangTen

@MainActor
final class BoardModelTests: XCTestCase {
    private var board: TrainingBoard {
        BoardCatalog.board(for: BoardModelAsset.boardID)
    }

    func testOnlyUnmodifiedBundledPrimaryBoardUsesModel() {
        XCTAssertTrue(BoardModelAsset.supports(board, presentation: board.defaultPresentation))
        let otherBoard = BoardCatalog.all.first { $0.id != board.id }!
        XCTAssertFalse(BoardModelAsset.supports(otherBoard, presentation: otherBoard.defaultPresentation))
        let edited = TrainingBoard(
            id: board.id, manufacturer: board.manufacturer, name: board.name,
            subtitle: board.subtitle, dimensions: board.dimensions, aspectRatio: board.aspectRatio,
            holds: Array(board.holds.dropLast()), productURL: board.productURL, photoAssetName: nil
        )
        XCTAssertFalse(BoardModelAsset.supports(edited, presentation: edited.defaultPresentation))
        let sameInventoryEdit = TrainingBoard(
            id: board.id, manufacturer: board.manufacturer, name: "Edited board",
            subtitle: board.subtitle, dimensions: board.dimensions, aspectRatio: board.aspectRatio,
            equipmentObjects: board.equipmentObjects, holds: board.holds,
            semanticHolds: board.semanticHolds, productURL: board.productURL,
            photoAssetName: board.photoAssetName, presentations: board.presentations,
            positions: board.positions, positionTransitions: board.positionTransitions
        )
        XCTAssertEqual(Set(sameInventoryEdit.holds.map(\.id)), BoardModelAsset.holdIDs)
        XCTAssertFalse(BoardModelAsset.supports(sameInventoryEdit, presentation: sameInventoryEdit.defaultPresentation))
        let inverted = BoardPresentation(
            id: "inverted", name: "Inverted", aspectRatio: board.aspectRatio,
            isDefault: false, sourcePresentationID: "primary", isInverted: true
        )
        XCTAssertFalse(BoardModelAsset.supports(board, presentation: inverted))
    }

    func testDisplayOnlyModelSurfaceDoesNotParticipateInHitTesting() {
        XCTAssertFalse(BoardModelSurface<EmptyView>.hitTestingEnabled(onHoldTap: nil))
        XCTAssertTrue(BoardModelSurface<EmptyView>.hitTestingEnabled(onHoldTap: { _ in }))
    }

    func testMissingOrInvalidModelFallsBackWithoutCrashing() {
        XCTAssertNil(BoardModelAsset.load(url: nil))
        XCTAssertNil(BoardModelAsset.load(url: URL(fileURLWithPath: "/missing-epic-whale-model.usdz")))
        XCTAssertNil(BoardModelScene(source: SCNScene()))
    }

    func testActualBundledUSDZContainsEverySelectableHold() throws {
        let url = try XCTUnwrap(BoardModelAsset.url())
        let source = try XCTUnwrap(BoardModelAsset.load(url: url))
        var meshCount = 0
        source.rootNode.enumerateChildNodes { node, _ in
            guard let geometry = node.geometry else { return }
            meshCount += 1
            XCTAssertNotNil(geometry.firstMaterial?.diffuse.contents, "Missing wood material on \(node.parent?.name ?? node.name ?? "mesh")")
        }
        XCTAssertEqual(meshCount, 20)
        let model = try XCTUnwrap(BoardModelScene(source: source))
        XCTAssertEqual(Set(model.holdNodes.keys), Set(board.holds.map(\.id)))
        XCTAssertEqual(model.holdNodes.count, 19)
        for nodes in model.holdNodes.values {
            XCTAssertFalse(nodes.isEmpty)
            XCTAssertTrue(nodes.allSatisfy { ($0.geometry?.sources(for: .vertex).first?.vectorCount ?? 0) > 0 })
            XCTAssertTrue(nodes.allSatisfy { $0.geometry?.firstMaterial?.diffuse.contents != nil })
        }
    }

    func testPickingNamesRejectBodyAndUnknownMeshes() {
        let parent = SCNNode()
        parent.name = "pocket_19_two_left"
        let child = SCNNode()
        child.name = "Mesh"
        parent.addChildNode(child)
        XCTAssertEqual(BoardModelAsset.holdID(for: child), "pocket-19-two-left")
        parent.name = "wood_body"
        XCTAssertNil(BoardModelAsset.holdID(for: child))
        parent.name = "pocket_100_unknown"
        XCTAssertNil(BoardModelAsset.holdID(for: child))
    }

    func testHighlightsRestoreWoodAndRemainIndependentAcrossViews() throws {
        let source = try XCTUnwrap(BoardModelAsset.load(url: BoardModelAsset.url()))
        let first = try XCTUnwrap(BoardModelScene(source: source))
        let second = try XCTUnwrap(BoardModelScene(source: source))
        let id = "pocket-19-two-left"
        let node = try XCTUnwrap(first.holdNodes[id]?.first)
        let otherNode = try XCTUnwrap(second.holdNodes[id]?.first)
        let original = try XCTUnwrap(node.geometry?.firstMaterial)
        let otherOriginal = try XCTUnwrap(otherNode.geometry?.firstMaterial)
        XCTAssertFalse(original === otherOriginal)
        first.highlight([id, "invalid-hold"], mode: .active)
        XCTAssertEqual(node.geometry?.firstMaterial?.diffuse.contents as? UIColor, UIColor(Color.holdActive))
        XCTAssertTrue(otherNode.geometry?.firstMaterial === otherOriginal)
        first.highlight([id], mode: .preview)
        XCTAssertEqual(node.geometry?.firstMaterial?.diffuse.contents as? UIColor, UIColor(Color.restBlue))
        first.highlight([], mode: .active)
        XCTAssertTrue(node.geometry?.firstMaterial === original)
        let third = try XCTUnwrap(BoardModelScene(source: source))
        XCTAssertFalse(third.holdNodes[id]?.first?.geometry?.firstMaterial?.diffuse.contents is UIColor)
    }

    func testExistingViewRebindsReplacementSceneAndItsCamera() throws {
        let source = try XCTUnwrap(BoardModelAsset.load(url: BoardModelAsset.url()))
        let first = try XCTUnwrap(BoardModelScene(source: source))
        let replacement = try XCTUnwrap(BoardModelScene(source: source))
        let view = BoardModelSCNView(frame: CGRect(x: 0, y: 0, width: 350, height: 100))
        view.display(first)
        view.display(replacement)
        XCTAssertTrue(view.scene === replacement.scene)
        XCTAssertTrue(view.pointOfView === replacement.camera)
        XCTAssertTrue(view.model === replacement)
        XCTAssertFalse(view.scene === first.scene)
        XCTAssertLessThan(try XCTUnwrap(replacement.camera.camera).orthographicScale, 1)
        view.scene = nil
        view.model = nil
    }

    func testPocketFacesRemainPickableThroughBodyOpenings() throws {
        let source = try XCTUnwrap(BoardModelAsset.load(url: BoardModelAsset.url()))
        let model = try XCTUnwrap(BoardModelScene(source: source))
        // There is no render loop in this CPU-only regression. Commit the newly
        // cloned scene graph before asking SceneKit's hit-test engine to traverse it.
        SCNTransaction.flush()
        for id in ["pocket-19-two-left", "pocket-29-four-center", "edge-29-left"] {
            let node = try XCTUnwrap(model.holdNodes[id]?.first)
            let box = node.boundingBox
            let center = node.convertPosition(SCNVector3(
                (box.min.x + box.max.x) / 2,
                (box.min.y + box.max.y) / 2,
                (box.min.z + box.max.z) / 2
            ), to: nil)
            // Match the head-on orthographic view's parallel rays.
            let start = SCNVector3(center.x, center.y, model.camera.position.z)
            let end = SCNVector3(center.x, center.y, -0.1)
            let hits = model.scene.rootNode.hitTestWithSegment(from: start, to: end, options: nil)
            let closest = try XCTUnwrap(hits.min { lhs, rhs in
                func distance(_ hit: SCNHitTestResult) -> Float {
                    let p = hit.worldCoordinates
                    return pow(p.x - start.x, 2) + pow(p.y - start.y, 2) + pow(p.z - start.z, 2)
                }
                return distance(lhs) < distance(rhs)
            })
            XCTAssertEqual(BoardModelAsset.holdID(for: closest.node), id, "Body tessellation must preserve the \(id) opening")
        }
    }
}
