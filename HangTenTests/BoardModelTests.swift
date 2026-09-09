import SceneKit
import SwiftUI
import XCTest
@testable import HangTen

@MainActor
final class BoardModelTests: XCTestCase {
    func testModelSurfaceUnavailableStateNeverPermitsHoldSelection() {
        XCTAssertFalse(BoardModelSurface.permitsHoldSelection(
            for: .unavailable,
            onHoldTap: { _ in }
        ))
        XCTAssertFalse(BoardModelSurface.permitsHoldSelection(
            for: .loading,
            onHoldTap: { _ in }
        ))
        XCTAssertTrue(BoardModelSurface.permitsHoldSelection(
            for: .ready,
            onHoldTap: { _ in }
        ))
    }

    // This catches a renderer that accepts names by suffix, normalization, or
    // descriptor subsets instead of binding the importer-visible node paths.
    func testGenericModelBindingUsesExactDescriptorNodeIDs() throws {
        let source = scene(nodes: ["Board/Body", "Board/Hold/Left"])
        let descriptor = modelDescriptor(nodes: [
            .init(nodeID: "Board/Body", role: .body, holdID: nil),
            .init(nodeID: "Board/Hold/Left", role: .hold, holdID: "left")
        ])

        let model = try XCTUnwrap(BoardModelScene(
            source: source,
            descriptor: descriptor,
            display: display()
        ))

        XCTAssertEqual(Set(model.holdNodes.keys), ["left"])
        XCTAssertEqual(model.geometryNodes.count, 2)
        XCTAssertEqual(model.holdID(for: try XCTUnwrap(model.holdNodes["left"]?.first)), "left")
        XCTAssertNil(model.holdID(for: try XCTUnwrap(model.geometryNodes.first { $0.name == "Body" })))

        let mismatched = modelDescriptor(nodes: [
            .init(nodeID: "Board/Body", role: .body, holdID: nil),
            .init(nodeID: "left", role: .hold, holdID: "left")
        ])
        XCTAssertNil(BoardModelScene(source: source, descriptor: mismatched, display: display()))
    }

    // This catches a renderer that silently renders nodes the descriptor did
    // not bind, which would make body geometry or arbitrary importer meshes tappable.
    func testGenericModelBindingRejectsUnlistedGeometryAndInvalidMeshInputs() {
        let descriptor = modelDescriptor(nodes: [
            .init(nodeID: "Board/Body", role: .body, holdID: nil),
            .init(nodeID: "Board/Hold/Left", role: .hold, holdID: "left")
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
            .init(nodeID: "Board/Body", role: .body, holdID: nil),
            .init(nodeID: "Board/Hold/Left", role: .hold, holdID: "left")
        ])
        let source = scene(nodes: ["Board/Body", "Board/Hold/Left"])
        let rootGeometry = SCNBox(width: 0.1, height: 0.1, length: 0.1, chamferRadius: 0)
        rootGeometry.firstMaterial = SCNMaterial()
        source.rootNode.geometry = rootGeometry

        XCTAssertNil(BoardModelScene(source: source, descriptor: descriptor, display: display()))
    }

    func testHighlightsRestoreClonedMaterialsAcrossGenericViews() throws {
        let descriptor = modelDescriptor(nodes: [
            .init(nodeID: "Board/Body", role: .body, holdID: nil),
            .init(nodeID: "Board/Hold/Left", role: .hold, holdID: "left")
        ])
        let source = scene(nodes: ["Board/Body", "Board/Hold/Left"])
        let first = try XCTUnwrap(BoardModelScene(source: source, descriptor: descriptor, display: display()))
        let second = try XCTUnwrap(BoardModelScene(source: source, descriptor: descriptor, display: display()))
        let firstNode = try XCTUnwrap(first.holdNodes["left"]?.first)
        let secondNode = try XCTUnwrap(second.holdNodes["left"]?.first)
        let original = try XCTUnwrap(firstNode.geometry?.firstMaterial)
        let otherOriginal = try XCTUnwrap(secondNode.geometry?.firstMaterial)

        XCTAssertFalse(original === otherOriginal)
        first.highlight(["left"], mode: .active)
        XCTAssertEqual(firstNode.geometry?.firstMaterial?.diffuse.contents as? UIColor, UIColor(Color.holdActive))
        XCTAssertTrue(secondNode.geometry?.firstMaterial === otherOriginal)
        first.highlight([], mode: .active)
        XCTAssertTrue(firstNode.geometry?.firstMaterial === original)
    }

    func testExistingViewRebindsDescriptorFramedReplacementSceneAndCamera() throws {
        let firstDescriptor = modelDescriptor(nodes: [
            .init(nodeID: "Board/Body", role: .body, holdID: nil),
            .init(nodeID: "Board/Hold/Left", role: .hold, holdID: "left")
        ], minimum: [-1, -0.5, -0.1], maximum: [1, 0.5, 0.1])
        let replacementDescriptor = modelDescriptor(nodes: [
            .init(nodeID: "Board/Body", role: .body, holdID: nil),
            .init(nodeID: "Board/Hold/Left", role: .hold, holdID: "left")
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

    func testClosestNativeHitResolvesOnlyTheFrontDescriptorBoundHold() throws {
        let descriptor = modelDescriptor(nodes: [
            .init(nodeID: "Board/Body", role: .body, holdID: nil),
            .init(nodeID: "Board/Hold/Left", role: .hold, holdID: "left")
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

        XCTAssertEqual(model.holdID(for: closest.node), "left")
        XCTAssertNil(model.holdID(for: try XCTUnwrap(model.geometryNodes.first { $0.name == "Body" })))
    }

    private func modelDescriptor(
        nodes: [BoardModelNodeDescriptor],
        minimum: [Double] = [0, 0, 0],
        maximum: [Double] = [1, 1, 1]
    ) -> BoardModelDescriptor {
        let holdIDs = Set(nodes.compactMap { $0.role == .hold ? $0.holdID : nil })
        return BoardModelDescriptor(
            schemaVersion: 1,
            coordinateFrame: "hang-ten-board-v1",
            modelSHA256: String(repeating: "0", count: 64),
            modelBounds: .init(minimum: minimum, maximum: maximum),
            nodes: nodes,
            holds: Dictionary(uniqueKeysWithValues: holdIDs.map { id in
                (
                    id,
                    .init(
                        nodeIDs: nodes.compactMap { $0.holdID == id ? $0.nodeID : nil },
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
