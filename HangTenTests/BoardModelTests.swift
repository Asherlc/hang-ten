import SceneKit
import SwiftUI
import UIKit
import XCTest
@testable import HangTen

@MainActor
final class BoardModelTests: XCTestCase {
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
        XCTAssertEqual(board.holds.map(\.id), expectedHoldIDs)
        XCTAssertEqual(Set(media.descriptor.holds.keys), Set(expectedHoldIDs))
        XCTAssertEqual(media.assetPath, "assets/primary.usdz")
        XCTAssertEqual(media.descriptorPath, "assets/primary.model.json")
        XCTAssertEqual(media.display.camera.type, "orthographic")
        XCTAssertEqual(media.display.camera.viewDirection, [0, 0, -1])
        XCTAssertEqual(media.display.camera.up, [0, 1, 0])
        XCTAssertEqual(media.display.camera.fitPadding, 0.08)

        let assetURL = try XCTUnwrap(
            BoardCatalog.packageStore.presentationAssetURL(for: board, presentationID: presentation.id)
        )
        let descriptorURL = try XCTUnwrap(
            BoardCatalog.packageStore.presentationDescriptorURL(for: board, presentationID: presentation.id)
        )
        XCTAssertTrue(assetURL.path.hasSuffix("/Hangboards/nature-stone-hanger/assets/primary.usdz"))
        XCTAssertTrue(descriptorURL.path.hasSuffix("/Hangboards/nature-stone-hanger/assets/primary.model.json"))
        XCTAssertNil(BoardCatalog.packageStore.presentationImageURL(for: board, presentationID: presentation.id))
    }

    // The package has two observed external cord-port mouths, but its source
    // does not establish the hidden route, cord dimensions, anchor, or poses.
    // Keep that unsupported suspension contract explicitly unavailable instead
    // of inventing enough inputs to invoke Task 1's deterministic solver.
    func testNatureStoneHangerLeavesUnsupportedSuspensionRoutingUnavailable() throws {
        let board = try XCTUnwrap(BoardCatalog.packageStore.board(id: "nature.stone-hanger"))
        guard case .model(let media) = board.defaultPresentation.media else {
            return XCTFail("Nature Stone Hanger must route through model media")
        }

        XCTAssertNil(media.suspension)
        XCTAssertFalse(BoardModelSurface.permitsHoldSelection(
            for: .unavailable,
            onHoldTap: { _ in XCTFail("unavailable routing must not select a hold") }
        ))
    }

    func testNatureStoneHangerHighlightsNativeHoldMaterialsAndClearsThem() async throws {
        let (board, _, model) = try await loadMigratedModel("nature.stone-hanger")
        let highlightedID = "edge-front-20mm-granite"
        let untouchedID = "edge-front-20mm-wood-flat"
        let highlightedNode = try XCTUnwrap(model.holdNodes[highlightedID]?.first)
        let untouchedNode = try XCTUnwrap(model.holdNodes[untouchedID]?.first)
        let highlightedOriginal = try XCTUnwrap(highlightedNode.geometry?.firstMaterial)
        let untouchedOriginal = try XCTUnwrap(untouchedNode.geometry?.firstMaterial)

        XCTAssertEqual(model.holdNodes.count, board.holds.count)
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

    func testNatureStoneHangerCordPassageMarkersAreNotSelectableOrAccessible() async throws {
        let (board, media, model) = try await loadMigratedModel("nature.stone-hanger")
        let passageMarkerIDs = ["cord-passage-1", "cord-passage-2"]
        let descriptorNodeIDs = Set(media.descriptor.nodes.map(\.nodeID))

        XCTAssertTrue(passageMarkerIDs.allSatisfy { !descriptorNodeIDs.contains($0) })
        XCTAssertTrue(passageMarkerIDs.allSatisfy { model.holdNodes[$0] == nil })
        XCTAssertEqual(model.geometryNodes.count, board.holds.count + 1)
        for markerID in passageMarkerIDs {
            let marker = SCNNode()
            marker.name = markerID
            XCTAssertNil(model.holdID(for: marker), markerID)
        }

        let view = BoardModelSCNView(frame: CGRect(x: 0, y: 0, width: 320, height: 320))
        view.display(model)
        view.holds = board.holds
        view.onHoldTap = { _ in }
        view.updateAccessibility()

        let identifiers = try XCTUnwrap(view.accessibilityElements as? [UIAccessibilityElement])
            .compactMap(\.accessibilityIdentifier)
        XCTAssertEqual(Set(identifiers), Set(board.holds.map { "boardModel.hold.\($0.id)" }))
        XCTAssertTrue(passageMarkerIDs.allSatisfy { !identifiers.contains("boardModel.hold.\($0)") })
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
            for target in plan.steps.flatMap(\.targets) {
                XCTAssertFalse(
                    BoardTargetResolver.substituteHoldIDs(for: target, on: board).isEmpty,
                    "Expected \(plan.id) target \(target) to resolve on \(board.id)"
                )
            }
        }

        for boardID in ["yy.baguette-evo", "soill.training-tiles"] {
            let board = try XCTUnwrap(BoardCatalog.packageStore.board(id: boardID))
            let compatibleGenericPlans = PlanCatalog.all.filter { plan in
                plan.boardID == nil && plan.steps.flatMap(\.targets).allSatisfy {
                    !BoardTargetResolver.substituteHoldIDs(for: $0, on: board).isEmpty
                }
            }
            XCTAssertFalse(compatibleGenericPlans.isEmpty, boardID)
            for plan in compatibleGenericPlans {
                for target in plan.steps.flatMap(\.targets) {
                    let resolvedIDs = BoardTargetResolver.substituteHoldIDs(for: target, on: board)
                    XCTAssertTrue(Set(resolvedIDs).isSubset(of: Set(board.holds.map(\.id))), "\(plan.id): \(boardID)")
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
        ]
        let rasterBoardIDs = ["metolius.simulator-3d", "soill.training-tiles"]

        for boardID in modelBoardIDs {
            let board = try XCTUnwrap(BoardCatalog.packageStore.board(id: boardID))
            guard case .model = board.defaultPresentation.media else {
                XCTFail("\(boardID) must remain model-routed")
                continue
            }
            XCTAssertNotNil(BoardCatalog.packageStore.presentationAssetURL(for: board))
            XCTAssertNotNil(BoardCatalog.packageStore.presentationDescriptorURL(for: board))
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

            XCTAssertEqual(Set(board.holds.map(\.id)), expectation.holdIDs, expectation.boardID)
            XCTAssertEqual(Set(media.descriptor.holds.keys), expectation.holdIDs, expectation.boardID)
            XCTAssertEqual(Set(model.holdNodes.keys), expectation.holdIDs, expectation.boardID)
            XCTAssertEqual(
                model.holdNodes.values.reduce(0) { $0 + $1.count },
                expectation.holdIDs.count,
                expectation.boardID
            )
            XCTAssertEqual(model.geometryNodes.count, expectation.holdIDs.count + 1, expectation.boardID)

            for node in model.geometryNodes {
                let materials = try XCTUnwrap(node.geometry?.materials, expectation.boardID)
                XCTAssertFalse(materials.isEmpty, "\(expectation.boardID): \(node.name ?? "unnamed")")
                XCTAssertTrue(
                    materials.allSatisfy { $0.diffuse.contents != nil },
                    "\(expectation.boardID): \(node.name ?? "unnamed")"
                )
            }

            try assertNearestHeadOnHitForEveryHold(model, media: media, boardID: expectation.boardID)
            try assertBodyHitIsNotSelectable(
                model,
                media: media,
                normalizedPoint: expectation.bodyProbe,
                boardID: expectation.boardID
            )
        }
    }

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

    func testModelAccessibilityEnumeratesOnlyDescriptorBoundHolds() throws {
        let descriptor = modelDescriptor(nodes: [
            .init(nodeID: "Board/Body", role: .body, holdID: nil),
            .init(nodeID: "Board/Hold/Left", role: .hold, holdID: "left")
        ])
        let model = try XCTUnwrap(BoardModelScene(
            source: scene(nodes: ["Board/Body", "Board/Hold/Left"]),
            descriptor: descriptor,
            display: display()
        ))
        let boundHold = BoardHold(id: "left", name: "Bound left", kind: .edge)
        let unboundHold = BoardHold(id: "not-in-descriptor", name: "Unbound", kind: .edge)
        let view = BoardModelSCNView(frame: CGRect(x: 0, y: 0, width: 320, height: 160))

        view.display(model)
        view.holds = [boundHold, unboundHold]
        view.onHoldTap = { _ in }
        view.updateAccessibility()

        let elements = try XCTUnwrap(view.accessibilityElements as? [UIAccessibilityElement])
        XCTAssertEqual(elements.compactMap(\.accessibilityIdentifier), ["boardModel.hold.left"])
        XCTAssertEqual(elements.compactMap(\.accessibilityLabel), ["Bound left"])
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
        first.highlight(["left"], mode: .preview)
        XCTAssertEqual(firstNode.geometry?.firstMaterial?.diffuse.contents as? UIColor, UIColor(Color.restBlue))
        first.highlight([], mode: .preview)
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

    // This catches cancellation of the camera-depth term in the key-light
    // position, which turns the intended front-above key into a top-only key.
    func testDirectionalKeyLightIlluminatesTheCameraFacingSurface() throws {
        let descriptor = modelDescriptor(nodes: [
            .init(nodeID: "Board/Body", role: .body, holdID: nil),
            .init(nodeID: "Board/Hold/Left", role: .hold, holdID: "left")
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

    private struct MigratedModelExpectation {
        let boardID: String
        let holdIDs: Set<String>
        let bodyProbe: [Double]
    }

    private var migratedModelExpectations: [MigratedModelExpectation] {
        [
            MigratedModelExpectation(
                boardID: "beastmaker-1000",
                holdIDs: [
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
                holdIDs: [
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
    ) async throws -> (TrainingBoard, BoardModelMedia, BoardModelScene) {
        let board = try XCTUnwrap(BoardCatalog.packageStore.board(id: boardID), boardID)
        let presentation = board.defaultPresentation
        let candidateMedia: BoardModelMedia? = if case .model(let media) = presentation.media {
            media
        } else {
            nil
        }
        let media = try XCTUnwrap(candidateMedia, "\(boardID) is not a package model")
        let packageURL = try XCTUnwrap(
            BoardCatalog.packageStore.presentationAssetURL(
                for: board,
                presentationID: presentation.id
            ),
            boardID
        )
        XCTAssertEqual(packageURL.lastPathComponent, "primary.usdz", boardID)
        let loaded = await BoardModelLoader.load(
            board: board,
            presentation: presentation,
            store: BoardCatalog.packageStore
        )
        let model = try XCTUnwrap(loaded, boardID)
        return (board, media, model)
    }

    private func assertNearestHeadOnHitForEveryHold(
        _ model: BoardModelScene,
        media: BoardModelMedia,
        boardID: String
    ) throws {
        for holdID in media.descriptor.holds.keys.sorted() {
            let hold = try XCTUnwrap(media.descriptor.holds[holdID], "\(boardID): \(holdID)")
            let normalizedCenter = zip(hold.facePlaneAABB.minimum, hold.facePlaneAABB.maximum).map {
                $0 + ($1 - $0) / 2
            }
            let ray = try headOnRay(
                normalizedPoint: normalizedCenter,
                bounds: media.descriptor.modelBounds,
                context: "\(boardID): \(holdID)"
            )
            let closest = try XCTUnwrap(
                model.scene.rootNode.hitTestWithSegment(
                    from: ray.from,
                    to: ray.to,
                    options: [
                        SCNHitTestOption.searchMode.rawValue: SCNHitTestSearchMode.closest.rawValue
                    ]
                ).first,
                "\(boardID): \(holdID)"
            )
            XCTAssertEqual(model.holdID(for: closest.node), holdID, "\(boardID): \(holdID)")
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
        let closest = try XCTUnwrap(
            model.scene.rootNode.hitTestWithSegment(
                from: ray.from,
                to: ray.to,
                options: [
                    SCNHitTestOption.searchMode.rawValue: SCNHitTestSearchMode.closest.rawValue
                ]
            ).first,
            "\(boardID): body"
        )
        XCTAssertNil(model.holdID(for: closest.node), boardID)
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
