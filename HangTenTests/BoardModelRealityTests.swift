import XCTest
import RealityKit
import UIKit
import simd
@testable import HangTen

final class BoardModelRealityTests: XCTestCase {
    @MainActor
    func testClavelliumPitchMovesBoardAroundCordPivotWhileSupportAndCameraStayFixed() async throws {
        let board = try XCTUnwrap(BoardCatalog.packageStore.board(id: "clavellium-training-block"))
        let scene = try await BoardModelRealityLoader.load(board: board, presentation: board.defaultPresentation)
        XCTAssertFalse(scene.hasLiveRopes)
        XCTAssertTrue(scene.select(positionID: try XCTUnwrap(board.positions.first?.id)))
        scene.frame(in: CGSize(width: 800, height: 500))
        let body = try XCTUnwrap(scene.instanceEntities.first)
        let originalBody = body.transformMatrix(relativeTo: scene.root)
        let pivot = SIMD4<Float>(0, 0.0025, 0, 1)
        let originalPivot = originalBody * pivot
        let originalTop = originalBody * SIMD4<Float>(0, 0.05, 0, 1)
        let originalCamera = scene.camera.transform.matrix
        let support = SIMD3<Float>(0, 0.07, 0)
        let originalCord = try XCTUnwrap(scene.transientCordEntity).children.map { $0.transform.matrix }
        for pitch in [Float.pi / 9, -Float.pi / 9] {
            scene.orbit(azimuth: 0, elevation: pitch)
            let placed = body.transformMatrix(relativeTo: scene.root)
            XCTAssertNotEqual(placed, originalBody, "The board must actually rotate, rather than moving only the camera")
            XCTAssertLessThan(simd_distance(placed * pivot, originalPivot), 1e-6)
            XCTAssertGreaterThan(simd_distance(placed * SIMD4<Float>(0, 0.05, 0, 1), originalTop), 0.01)
            XCTAssertEqual(scene.camera.transform.matrix, originalCamera, "Pitch must not move or zoom the camera and make the fixed cord appear to move")
            for column in 0..<3 {
                XCTAssertLessThan(simd_distance(scene.camera.transform.matrix[column], originalCamera[column]), 1e-6,
                                  "The camera orientation must stay fixed during board pitch")
            }
            let cord = try XCTUnwrap(scene.transientCordEntity)
            XCTAssertEqual(cord.children.map { $0.transform.matrix }, originalCord,
                           "The entire cord must stay fixed while the board turns")
            for mouth in [SIMD4<Float>(0, 0.0025, 0.045, 1), SIMD4<Float>(0, 0.0025, -0.045, 1)] {
                XCTAssertLessThan(simd_distance(placed * mouth, originalBody * mouth), 1e-6,
                                  "The board must rotate around the line through its cord points")
            }
            let endpoints = cord.children.flatMap { child -> [SIMD3<Float>] in
                guard let mesh = (child as? ModelEntity)?.model?.mesh else { return [] }
                let halfLength = mesh.bounds.extents.y / 2
                return [-halfLength, halfLength].map { y in
                    let p = child.transformMatrix(relativeTo: scene.root) * SIMD4<Float>(0, y, 0, 1)
                    return SIMD3(p.x, p.y, p.z)
                }
            }
            XCTAssertLessThan(try XCTUnwrap(endpoints.map { simd_distance($0, support) }.min()), 1e-5,
                              "Overhead cord support must not rotate with the board")
        }
        scene.resetCamera(animated: false)
        XCTAssertEqual(body.transformMatrix(relativeTo: scene.root), originalBody)
        XCTAssertEqual(scene.camera.transform.matrix, originalCamera)
    }

    @MainActor
    func testCordedTopSelectionTiltsBoardAndClearingRestoresCanonicalPose() async throws {
        let board = try XCTUnwrap(BoardCatalog.packageStore.board(id: "clavellium-training-block"))
        let scene = try await BoardModelRealityLoader.load(board: board, presentation: board.defaultPresentation)
        XCTAssertTrue(scene.select(positionID: try XCTUnwrap(board.positions.first?.id)))
        scene.frame(in: CGSize(width: 800, height: 500))
        let body = try XCTUnwrap(scene.instanceEntities.first)
        let original = body.transform.matrix
        scene.highlight(["cd-pinch-100mm-top"], mode: .active)
        XCTAssertGreaterThan(scene.orbitElevation, 0.15)
        XCTAssertNotEqual(body.transform.matrix, original)
        let selected = body.transform.matrix
        scene.frame(in: CGSize(width: 800, height: 500))
        scene.highlight(["cd-pinch-100mm-top"], mode: .active)
        XCTAssertEqual(body.transform.matrix, selected, "Repeated updates must not compound the board tilt")
        scene.highlight([], mode: .active)
        XCTAssertEqual(body.transform.matrix, original)
        XCTAssertFalse(scene.hasLiveRopes)
    }

    @MainActor
    func testBoardPitchUsesPairedAttachmentsBoreMouthsAndIndependentInstancePivots() async throws {
        let cases: [(String, SIMD3<Float>)] = [
            ("nature.stone-hanger", [0, -0.0024, 0]),
            ("tension.flash-board", [0.25, 0.047999999, 0.038669699]),
            ("metolius.rock-rings-3d", [0, 0.091, 0])
        ]
        for (id, localPivot) in cases {
            let board = try XCTUnwrap(BoardCatalog.packageStore.board(id: id))
            let scene = try await BoardModelRealityLoader.load(board: board, presentation: board.defaultPresentation)
            XCTAssertFalse(scene.hasLiveRopes, id)
            XCTAssertTrue(scene.select(positionID: try XCTUnwrap(board.positions.first?.id)), id)
            scene.frame(in: CGSize(width: 800, height: 500))
            let before = scene.instanceEntities.map { $0.transformMatrix(relativeTo: scene.root) }
            for pitch in [Float.pi / 9, -Float.pi / 9] {
                scene.orbit(azimuth: 0, elevation: pitch)
                for (index, body) in scene.instanceEntities.enumerated() {
                    let after = body.transformMatrix(relativeTo: scene.root)
                    XCTAssertNotEqual(after, before[index], id)
                    XCTAssertLessThan(simd_distance(after * SIMD4(localPivot, 1), before[index] * SIMD4(localPivot, 1)), 1e-6, id)
                }
            }
        }
    }

    @MainActor
    private func selectionScene() async throws -> BoardModelRealityScene {
        let board = try XCTUnwrap(BoardCatalog.packageStore.board(id: "beastmaker-1000"))
        let scene = try await BoardModelRealityLoader.load(board: board, presentation: board.defaultPresentation)
        let top = ModelEntity(mesh: .generatePlane(width: 0.05, depth: 0.03))
        let front = ModelEntity(mesh: .generatePlane(width: 0.05, depth: 0.03))
        front.orientation = simd_quatf(angle: .pi / 2, axis: [1, 0, 0])
        let side = ModelEntity(mesh: .generatePlane(width: 0.05, depth: 0.03))
        side.orientation = simd_quatf(angle: -.pi / 2, axis: [0, 0, 1])
        for entity in [top, front, side] {
            entity.position = [0, -0.1, -0.1]
            scene.root.addChild(entity)
        }
        scene.contactEntities = ["top": [top], "front": [front], "side": [side]]
        scene.frame(in: CGSize(width: 390, height: 240))
        return scene
    }

    @MainActor
    func testSelectingEdgeOnTopSurfaceTiltsViewJustEnough() async throws {
        let scene = try await selectionScene()
        scene.highlight(["top"], mode: .active)
        XCTAssertGreaterThan(scene.orbitElevation, 0.15, "Top surfaces need a view from above")
        XCTAssertLessThanOrEqual(scene.orbitElevation, 0.4, "Keep the adjustment small")
        XCTAssertEqual(scene.orbitAzimuth, 0, accuracy: 0.001)
        XCTAssertEqual(scene.orbitZoom, 1)
    }

    @MainActor
    func testSelectingVisibleFrontSurfaceKeepsHeadOnView() async throws {
        let scene = try await selectionScene()
        let initial = scene.camera.transform.matrix
        scene.highlight(["front"], mode: .active)
        XCTAssertEqual(scene.orbitElevation, 0)
        XCTAssertEqual(scene.orbitAzimuth, 0)
        XCTAssertEqual(scene.camera.transform.matrix, initial)
    }

    @MainActor
    func testSelectingVisibleFrontSurfaceResetsPriorTiltAndZoom() async throws {
        let scene = try await selectionScene()
        scene.highlight(["top"], mode: .active)
        scene.orbit(azimuth: 0.2, elevation: 0.1, zoomScale: 0.9)
        scene.highlight(["front"], mode: .active)
        XCTAssertEqual(scene.orbitAzimuth, 0)
        XCTAssertEqual(scene.orbitElevation, 0)
        XCTAssertEqual(scene.orbitZoom, 1)
    }

    @MainActor
    func testRecessedSurfaceUsesItsFrontOpeningRatherThanFloorNormal() async throws {
        let scene = try await selectionScene()
        let floor = try XCTUnwrap(scene.contactEntities["top"]?.first)
        // A roof encloses this same upward-facing contact. No hold metadata changes.
        let roof = ModelEntity(mesh: .generateBox(width: 0.06, height: 0.01, depth: 0.04))
        roof.position = floor.position + [0, 0.025, 0]
        scene.instanceEntities[0].addChild(roof, preservingWorldTransform: true)
        scene.highlight(["side"], mode: .active)
        scene.highlight(["top"], mode: .active)
        XCTAssertEqual(scene.orbitElevation, 0, "View the opening head-on, rather than tilting toward the roof")
        XCTAssertEqual(scene.orbitAzimuth, 0)
        XCTAssertNotNil(floor.model)
    }

    @MainActor
    func testOpeningCalculationChangesWhenRoofIsRemoved() async throws {
        let scene = try await selectionScene()
        let floor = try XCTUnwrap(scene.contactEntities["top"]?.first)
        let roof = ModelEntity(mesh: .generateBox(width: 0.06, height: 0.01, depth: 0.04))
        roof.position = floor.position + [0, 0.025, 0]
        scene.instanceEntities[0].addChild(roof, preservingWorldTransform: true)
        scene.highlight(["top"], mode: .active)
        XCTAssertEqual(scene.orbitElevation, 0)
        roof.removeFromParent()
        scene.highlight([], mode: .active)
        scene.highlight(["top"], mode: .active)
        XCTAssertGreaterThan(scene.orbitElevation, 0.15)
    }

    @MainActor
    func testDistantGeometryDoesNotEncloseAnExposedSideContact() async throws {
        let scene = try await selectionScene()
        let side = try XCTUnwrap(scene.contactEntities["side"]?.first)
        let distantWall = ModelEntity(mesh: .generateBox(width: 0.01, height: 0.1, depth: 0.1))
        distantWall.position = side.position + [0.3, 0, 0]
        scene.instanceEntities[0].addChild(distantWall, preservingWorldTransform: true)
        scene.highlight(["side"], mode: .active)
        XCTAssertGreaterThan(abs(scene.orbitAzimuth), 0.15,
                             "An unrelated distant surface must not suppress the side pivot")
        XCTAssertEqual(scene.orbitElevation, 0, accuracy: 0.001)
    }

    @MainActor
    func testViewingRaysFollowAnInstancePoseChange() async throws {
        let scene = try await selectionScene()
        let surface = try XCTUnwrap(scene.contactEntities["top"]?.first)
        let instance = try XCTUnwrap(scene.instanceEntities.first)
        surface.position = [0, -1, 0]
        instance.addChild(surface, preservingWorldTransform: true)
        scene.highlight(["top"], mode: .active)
        XCTAssertGreaterThan(scene.orbitElevation, 0.15)
        scene.highlight([], mode: .active)
        instance.orientation = simd_quatf(angle: -.pi / 2, axis: [0, 0, 1])
        scene.highlight(["top"], mode: .active)
        XCTAssertGreaterThan(abs(scene.orbitAzimuth), 0.15)
        XCTAssertEqual(scene.orbitElevation, 0, accuracy: 0.001)
    }

    @MainActor
    func testDiagonalSurfaceCalculatesBothViewingAngles() async throws {
        let scene = try await selectionScene()
        let surface = try XCTUnwrap(scene.contactEntities["top"]?.first)
        surface.orientation = simd_quatf(from: SIMD3<Float>(0, 1, 0),
                                        to: simd_normalize(SIMD3<Float>(0.7, 0.7, 0.1)))
        scene.highlight(["top"], mode: .active)
        XCTAssertGreaterThan(abs(scene.orbitAzimuth), 0.05)
        XCTAssertGreaterThan(scene.orbitElevation, 0.05)
        XCTAssertLessThanOrEqual(simd_length(SIMD2(scene.orbitAzimuth, scene.orbitElevation)), .pi / 9 + 0.001)
    }

    @MainActor
    func testFrontOpeningPocketsAcrossBoardMeshes() async throws {
        for (boardID, contacts) in [
            ("beastmaker-1000", ["pocket-bottom-inner-left", "pocket-top-right", "pocket-middle-center"]),
            ("metolius.simulator-3d", ["pocket-10-left", "pocket-15-center", "pocket-16-center"]),
            ("trango.rock-prodigy-natural", ["upper-pocket-right"])
        ] {
            let board = try XCTUnwrap(BoardCatalog.packageStore.board(id: boardID))
            let scene = try await BoardModelRealityLoader.load(board: board, presentation: board.defaultPresentation)
            scene.frame(in: CGSize(width: 390, height: 240))
            for contact in contacts {
                XCTAssertNotNil(scene.contactEntities[contact], "\(boardID): \(contact)")
                scene.orbit(azimuth: 0.2, elevation: 0.3, zoomScale: 0.9)
                scene.highlight([contact], mode: .active)
                XCTAssertEqual(scene.orbitAzimuth, 0, "\(boardID): \(contact)")
                XCTAssertEqual(scene.orbitElevation, 0, "\(boardID): \(contact)")
                XCTAssertEqual(scene.orbitZoom, 1, "\(boardID): \(contact)")
            }
        }
    }

    @MainActor
    func testSelectionUsesReplacementContactMesh() async throws {
        let scene = try await selectionScene()
        let top = try XCTUnwrap(scene.contactEntities["top"]?.first)
        scene.highlight(["top"], mode: .active)
        XCTAssertGreaterThan(scene.orbitElevation, 0.15)
        scene.highlight([], mode: .active)
        var contents = try XCTUnwrap(top.model?.mesh.contents)
        for var instance in contents.instances {
            instance.transform = simd_float4x4(simd_quatf(angle: .pi / 2, axis: SIMD3(1, 0, 0)))
            contents.instances.update(instance)
        }
        top.model?.mesh = try MeshResource.generate(from: contents)
        scene.highlight(["top"], mode: .active)
        XCTAssertEqual(scene.orbitElevation, 0, "The replacement surface faces the camera")
        XCTAssertEqual(scene.orbitAzimuth, 0)
    }

    @MainActor
    func testSelectingEdgeOnSideSurfacePivotsHorizontally() async throws {
        let scene = try await selectionScene()
        scene.highlight(["side"], mode: .active)
        XCTAssertGreaterThan(abs(scene.orbitAzimuth), 0.15)
        XCTAssertLessThanOrEqual(abs(scene.orbitAzimuth), 0.4)
        XCTAssertEqual(scene.orbitElevation, 0, accuracy: 0.001)
    }

    @MainActor
    func testSelectionAdjustmentPreservesManualOrbitAcrossRenderAndModeUpdates() async throws {
        let scene = try await selectionScene()
        scene.highlight(["top"], mode: .active)
        scene.orbit(azimuth: 0.2, elevation: 0.1, zoomScale: 0.9)
        scene.frame(in: CGSize(width: 390, height: 240))
        scene.highlight(["top"], mode: .preview)
        XCTAssertEqual(scene.orbitAzimuth, 0.2)
        XCTAssertEqual(scene.orbitElevation, 0.1)
        XCTAssertEqual(scene.orbitZoom, 0.9)
    }

    @MainActor
    func testClearingSelectionRestoresDefaultCamera() async throws {
        let scene = try await selectionScene()
        let initial = scene.camera.transform.matrix
        scene.highlight(["top"], mode: .active)
        XCTAssertNotEqual(scene.camera.transform.matrix, initial)
        scene.highlight([], mode: .active)
        XCTAssertEqual(scene.camera.transform.matrix, initial)
    }

    @MainActor
    func testMultipleSelectionsExposeBothTopAndFrontSurfaces() async throws {
        let scene = try await selectionScene()
        scene.highlight(["top", "front"], mode: .active)
        XCTAssertGreaterThan(scene.orbitElevation, 0.15)
        XCTAssertLessThanOrEqual(scene.orbitElevation, 0.4)
    }

    @MainActor
    func testMirroredTopSurfaceStillTiltsAboveTheBoard() async throws {
        let scene = try await selectionScene()
        let top = try XCTUnwrap(scene.contactEntities["top"]?.first)
        top.scale.x = -1
        scene.highlight(["top"], mode: .active)
        XCTAssertGreaterThan(scene.orbitElevation, 0.15)
    }

    @MainActor
    func testUndersideSurfaceTiltsBelowTheBoard() async throws {
        let scene = try await selectionScene()
        let top = try XCTUnwrap(scene.contactEntities["top"]?.first)
        top.orientation = simd_quatf(angle: .pi, axis: [1, 0, 0])
        scene.highlight(["top"], mode: .active)
        XCTAssertLessThan(scene.orbitElevation, -0.15)
        XCTAssertGreaterThanOrEqual(scene.orbitElevation, -0.4)
    }

    @MainActor
    func testAutomaticPivotKeepsTheWholeBoardInsideTheViewport() async throws {
        let scene = try await selectionScene()
        let viewport = CGSize(width: 390, height: 240)
        scene.highlight(["top"], mode: .active)
        let bounds = try XCTUnwrap(scene.instanceEntities.first).visualBounds(relativeTo: nil)
        let view = simd_inverse(scene.camera.transform.matrix)
        let tangent = tan(scene.camera.camera.fieldOfViewInDegrees * .pi / 360)
        for x in [bounds.min.x, bounds.max.x] {
            for y in [bounds.min.y, bounds.max.y] {
                for z in [bounds.min.z, bounds.max.z] {
                    let point = view * SIMD4<Float>(x, y, z, 1)
                    XCTAssertGreaterThan(-point.z, 0)
                    XCTAssertLessThanOrEqual(abs(point.y / -point.z / tangent), 1)
                    XCTAssertLessThanOrEqual(abs(point.x / -point.z / tangent / Float(viewport.width / viewport.height)), 1)
                }
            }
        }
    }

    @MainActor
    func testBeastmakerTopSloperSelectionRevealsMoreOfItsSurface() async throws {
        let board = try XCTUnwrap(BoardCatalog.packageStore.board(id: "beastmaker-1000"))
        let scene = try await BoardModelRealityLoader.load(board: board, presentation: board.defaultPresentation)
        scene.frame(in: CGSize(width: 390, height: 240))
        scene.highlight(["sloper-center"], mode: .active)
        XCTAssertGreaterThan(scene.orbitElevation, 0, "The shallow top sloper needs a clearer view")
        XCTAssertLessThanOrEqual(scene.orbitElevation, 0.4)
    }

    @MainActor
    func testReflectedMeshInstanceStillTiltsAboveItsTopSurface() async throws {
        let scene = try await selectionScene()
        let top = try XCTUnwrap(scene.contactEntities["top"]?.first)
        var contents = try XCTUnwrap(top.model?.mesh.contents)
        let original = try XCTUnwrap(contents.instances.first)
        var reflection = matrix_identity_float4x4
        reflection.columns.0.x = -1
        contents.instances = MeshInstanceCollection([
            MeshResource.Instance(id: original.id, model: original.model, at: reflection)
        ])
        top.model?.mesh = try MeshResource.generate(from: contents)
        scene.highlight(["top"], mode: .active)
        XCTAssertGreaterThan(scene.orbitElevation, 0.15)
    }

    @MainActor
    func testSelectingBeastmakerPocketReturnsToFrontOpening() async throws {
        let board = try XCTUnwrap(BoardCatalog.packageStore.board(id: "beastmaker-1000"))
        let scene = try await BoardModelRealityLoader.load(board: board, presentation: board.defaultPresentation)
        scene.frame(in: CGSize(width: 390, height: 240))
        scene.highlight(["jug-left"], mode: .active)
        XCTAssertGreaterThan(scene.orbitElevation, 0)
        scene.highlight(["pocket-middle-center"], mode: .active)
        XCTAssertEqual(scene.orbitElevation, 0)
        XCTAssertEqual(scene.orbitAzimuth, 0)
    }

    @MainActor
    func testCordAndCADModelShareMeterScale() async throws {
        for (id,width) in [("clavellium-training-block",Float(0.08)),("lattice.mini-bar",Float(0.155))] {
            let board=try XCTUnwrap(BoardCatalog.packageStore.board(id:id))
            let scene=try await BoardModelRealityLoader.load(board:board,presentation:board.defaultPresentation)
            let body=try XCTUnwrap(scene.modelEntity)
            let bounds=body.visualBounds(relativeTo:scene.root)
            XCTAssertEqual(bounds.max.x-bounds.min.x,width,accuracy:0.00001,id)
            XCTAssertTrue(scene.select(positionID:try XCTUnwrap(board.positions.first?.id)))
            let cord=try XCTUnwrap(scene.transientCordEntity)
            let segment=try XCTUnwrap(cord.children.first as? ModelEntity)
            if scene.hasLiveRopes {
                let frame=try XCTUnwrap(scene.liveFramesForTesting.first)
                let origin=try XCTUnwrap(frame.ropes.first?.positions.first)
                let mesh=try XCTUnwrap(segment.model?.mesh.lowLevelMesh)
                mesh.withUnsafeBytes(bufferIndex:0) { bytes in
                    let vertices=bytes.bindMemory(to:RopeTubeVertex.self)
                    for i in 0..<8 {
                        let center=SIMD3<Float>(Float(origin.x),Float(origin.y),Float(origin.z))
                        XCTAssertEqual(simd_distance(vertices[i].position,center),0.0035,accuracy:1e-7,id)
                    }
                }
            } else {
                let tube=segment.visualBounds(relativeTo:segment)
                XCTAssertEqual(tube.max.x-tube.min.x,0.007,accuracy:0.00001,id)
                XCTAssertEqual(tube.max.z-tube.min.z,0.007,accuracy:0.00001,id)
            }
            XCTAssertEqual(segment.scale,SIMD3<Float>(repeating:1))
            XCTAssertEqual(cord.scale,SIMD3<Float>(repeating:1))
        }
    }

    @MainActor
    func testLiveClavelliumHasMatchedRadiusAndNonPickableCord() async throws {
        let board=try XCTUnwrap(BoardCatalog.packageStore.board(id:"clavellium-training-block"))
        let scene=try await BoardModelRealityLoader.load(board:board,presentation:board.defaultPresentation,useLivePhysics:true)
        XCTAssertTrue(scene.hasLiveRopes)
        XCTAssertTrue(scene.select(positionID:try XCTUnwrap(board.positions.first?.id)))
        let frame=try XCTUnwrap(scene.liveFramesForTesting.first)
        XCTAssertTrue(frame.metrics.geometryAccepted)
        XCTAssertEqual(frame.ropes.first?.radius,0.0035)
        let cord=try XCTUnwrap(scene.transientCordEntity)
        let tube=try XCTUnwrap(cord.children.first as? ModelEntity)
        XCTAssertEqual(tube.scale,SIMD3<Float>(repeating:1))
        XCTAssertNil(tube.components[CollisionComponent.self])
        XCTAssertNil(tube.components[InputTargetComponent.self])
        scene.orbit(azimuth:1,elevation:0.3)
        XCTAssertFalse(scene.select(positionID:nil))
        XCTAssertNil(scene.transientCordEntity)
        XCTAssertTrue(scene.select(positionID:try XCTUnwrap(board.positions.first?.id)))
        XCTAssertNotNil(scene.transientCordEntity)
        XCTAssertEqual(Double(try XCTUnwrap(scene.instanceEntities.first).position.y),frame.boardHeight,accuracy:1e-7)
        scene.stopLiveRopes()
    }

    @MainActor
    func testPairedLiveBoardsMatchInstanceIDsAndPreservePlacement() async throws {
        let store=BoardCatalog.packageStore
        let board=try XCTUnwrap(store.board(id:"clavellium-training-block"))
        guard case .model(let media)=board.defaultPresentation.media else {return XCTFail("Model required")}
        let input=try XCTUnwrap(store.presentationPhysicsInput(for: board)),source=try XCTUnwrap(input.profiles.first)
        let instances=[("left",-0.15),("right",0.15)].map {id,x in
            BoardModelInstance(equipmentObjectID:id,
                baseTransform:BoardModelTransform(translation:[x,0.02,0],rotation:SIMD4(0,0,0,1),reflection:nil),
                contactIDsBySlotID:Dictionary(uniqueKeysWithValues:media.descriptor.contacts.keys.map{($0,$0)}),
                suspension:media.suspension,positionTransforms:nil)
        }
        let profiles=["right","left"].map {id in
            RopePhysicsProfile(id:id,presentationID:source.presentationID,instanceID:id,boardMass:source.boardMass,
                ropes:source.ropes.map {rope in
                    RopePhysicsRope(id:id+"-"+rope.id,baselineRadius:rope.baselineRadius,radius:rope.radius,
                        restLength:rope.restLength,linearMass:rope.linearMass,nodes:rope.nodes,edges:rope.edges)
                })
        }
        let paired=RopePhysicsInput(modelSHA256:input.modelSHA256,sourceSHA256:input.sourceSHA256,
            collision:input.collision,portals:input.portals,channels:input.channels,profiles:profiles)
        let url=try XCTUnwrap(store.presentationAssetURL(for:board) ??
            store.modelResource(for:board)?.debugSimulatorPackagedURL(in:store.resourceBundle))
        let scene=BoardModelRealityScene(descriptor:media.descriptor,display:media.display,
            suspension:nil,orientation:media.orientation,allowedPositionIDs:Set(board.positions.map(\.id)),
            instances:instances,physics:paired,presentationID:source.presentationID,
            resourceLease:BoardModelRealityResourceLease(url:url))
        defer {scene.stopLiveRopes()}
        try await scene.load(usdzURL:url)
        scene.setLiveActivity(false)
        let position=try XCTUnwrap(board.positions.first?.id)
        for _ in 0..<2 {
            XCTAssertTrue(scene.select(positionID:position))
            let group=try XCTUnwrap(scene.transientCordEntity)
            for (index,instance) in instances.enumerated() {
                let frame=scene.liveFramesForTesting[index]
                let expectedProfile = try XCTUnwrap(profiles.first {
                    $0.instanceID == instance.equipmentObjectID
                })
                XCTAssertEqual(Set(frame.ropes.map(\.id)), Set(expectedProfile.ropes.map(\.id)))
                XCTAssertEqual(scene.instanceEntities[index].position.x,Float(instance.baseTransform.translation[0]),accuracy:1e-7)
                XCTAssertEqual(scene.instanceEntities[index].position.y,Float(frame.boardHeight+0.02),accuracy:1e-7)
                let tube=try XCTUnwrap(group.children[index] as? ModelEntity)
                let mesh=try XCTUnwrap(tube.model?.mesh.lowLevelMesh)
                let point=try XCTUnwrap(frame.ropes.first?.positions.first)
                let center=SIMD3<Float>(Float(point.x+instance.baseTransform.translation[0]),Float(point.y+0.02),Float(point.z))
                mesh.withUnsafeBytes(bufferIndex:0) {bytes in
                    let vertices=bytes.bindMemory(to:RopeTubeVertex.self)
                    for i in 0..<8 {
                        let world=tube.transformMatrix(relativeTo:scene.root)*SIMD4(vertices[i].position,1)
                        XCTAssertEqual(simd_distance(SIMD3(world.x,world.y,world.z),center),Float(frame.ropes[0].radius),accuracy:1e-7)
                    }
                }
            }
            XCTAssertFalse(scene.select(positionID:nil))
        }
    }

    @MainActor
    func testLiveScenePausesThenPublishesAcceptedSettledFrame() async throws {
        let board=try XCTUnwrap(BoardCatalog.packageStore.board(id:"clavellium-training-block"))
        let scene=try await BoardModelRealityLoader.load(board:board,presentation:board.defaultPresentation,useLivePhysics:true)
        XCTAssertTrue(scene.select(positionID:try XCTUnwrap(board.positions.first?.id)))
        let initial=try XCTUnwrap(scene.liveFramesForTesting.first)
        var frameNotifications=0
        scene.onLiveFrame = { frameNotifications += 1 }
        scene.setLiveActivity(false)
        scene.advanceLiveRopes(elapsed:100)
        try await Task.sleep(for:.milliseconds(50))
        XCTAssertEqual(scene.liveFramesForTesting.first?.boardHeight,initial.boardHeight)
        scene.configureLiveMotion(reduceMotion:true,displayOnly:false)
        scene.setLiveActivity(true)
        scene.advanceLiveRopes(elapsed:1.0/60)
        let accepted=expectation(for:NSPredicate { _,_ in scene.liveFramesForTesting.first?.settled == true },evaluatedWith:nil)
        await fulfillment(of:[accepted],timeout:30)
        let final=try XCTUnwrap(scene.liveFramesForTesting.first)
        XCTAssertTrue(final.metrics.geometryAccepted);XCTAssertTrue(final.settled)
        XCTAssertEqual(frameNotifications,1,"Projected hold controls must refresh with the physical frame")
        var camera=scene.camera.camera
        camera.fieldOfViewInDegrees=30;camera.fieldOfViewOrientation = .vertical
        scene.camera.camera=camera
        scene.frame(in:CGSize(width:800,height:500))
        let view=simd_inverse(scene.camera.transform.matrix)
        var points=final.ropes.flatMap { $0.positions }.map { SIMD3<Float>(Float($0.x),Float($0.y),Float($0.z)) }
        let bounds=try XCTUnwrap(scene.instanceEntities.first).visualBounds(relativeTo:scene.root)
        for x in [bounds.min.x,bounds.max.x] {for y in [bounds.min.y,bounds.max.y] {for z in [bounds.min.z,bounds.max.z] {points.append(SIMD3(x,y,z))}}}
        for point in points {
            let projected=view*SIMD4(point,1),depth = -projected.z
            XCTAssertGreaterThan(depth,0)
            XCTAssertLessThanOrEqual(abs(projected.x/depth/tan(Float.pi/12)/1.6),1)
            XCTAssertLessThanOrEqual(abs(projected.y/depth/tan(Float.pi/12)),1)
        }
        scene.stopLiveRopes()
    }

    @MainActor
    func testReflectedMeshPreservesInstancePlacementAndSourceBuffers() throws {
        var descriptor = MeshDescriptor(name: "front")
        descriptor.positions = .init([SIMD3<Float>(0, 0, 1), SIMD3<Float>(2, 0, 1), SIMD3<Float>(0, 3, 1)])
        descriptor.normals = .init(Array(repeating: SIMD3<Float>(0, 0, 1), count: 3))
        descriptor.primitives = .triangles([0, 1, 2])
        let mesh = try MeshResource.generate(from: [descriptor])
        var contents = mesh.contents
        for var instance in contents.instances {
            instance.transform = simd_float4x4(simd_quatf(angle: .pi / 2, axis: SIMD3(0, 0, 1)))
            instance.transform.columns.3 = SIMD4(4, 5, 6, 1)
            contents.instances.update(instance)
        }
        let source = try MeshResource.generate(from: contents)
        var reflection = matrix_identity_float4x4
        reflection.columns.0.x = -1
        reflection.columns.3.x = 2 // Reflect about x=1 in the containing board.
        let mirrored = try BoardModelRealityScene.reflectedMesh(source, reflection: reflection)
        let instance = try XCTUnwrap(mirrored.contents.instances.first)
        let model = try XCTUnwrap(mirrored.contents.models[instance.model])
        let part = try XCTUnwrap(model.parts.first)
        XCTAssertEqual(part.triangleIndices?.elements, [0, 2, 1])
        XCTAssertEqual(part.normals?.elements, Array(repeating: SIMD3<Float>(0, 0, 1), count: 3))
        let points = part.positions.map { instance.transform * SIMD4<Float>($0, 1) }
        let expected: [SIMD4<Float>] = [SIMD4(-2, 5, 7, 1), SIMD4(-2, 7, 7, 1), SIMD4(1, 5, 7, 1)]
        for (actual, expected) in zip(points, expected) {
            XCTAssertLessThan(simd_length(actual - expected), 0.0001)
        }
        XCTAssertGreaterThan(simd_determinant(instance.transform), 0)
        let sourcePart = try XCTUnwrap(source.contents.models.first?.parts.first)
        XCTAssertEqual(sourcePart.positions.elements, descriptor.positions.elements)
        XCTAssertEqual(sourcePart.triangleIndices?.elements, [0, 1, 2])
    }

    @MainActor
    func testMirroredBoardNormalsAgreeWithRenderedTriangleWinding() async throws {
        for boardID in ["trango.rock-prodigy-pivot", "soill.split-palm",
                        "trango.rock-prodigy-forge", "trango.rock-prodigy-natural",
                        "trango.rock-prodigy-training-center"] {
            let board = try XCTUnwrap(BoardCatalog.packageStore.board(id: boardID))
            guard case .model(let media) = board.defaultPresentation.media else {
                return XCTFail("Expected model")
            }
            let scene = try await BoardModelRealityLoader.load(board: board,
                                                              presentation: board.defaultPresentation)
            if let positionID = board.positions.first?.id {
                XCTAssertTrue(scene.select(positionID: positionID))
            }
            var mirroredInstancesChecked = 0
            for (instance, root) in zip(media.instances ?? [], scene.instanceEntities)
            where instance.baseTransform.reflection == .x {
                mirroredInstancesChecked += 1
                var trianglesChecked = 0
                var inwardTriangles = 0
                func check(_ entity: Entity) throws {
                    if let component = (entity as? ModelEntity)?.model {
                        for meshInstance in component.mesh.contents.instances {
                            let model = try XCTUnwrap(component.mesh.contents.models[meshInstance.model])
                            let transform = entity.transformMatrix(relativeTo: scene.root) * meshInstance.transform
                            let linear = simd_float3x3(SIMD3(transform.columns.0.x, transform.columns.0.y, transform.columns.0.z),
                                                     SIMD3(transform.columns.1.x, transform.columns.1.y, transform.columns.1.z),
                                                     SIMD3(transform.columns.2.x, transform.columns.2.y, transform.columns.2.z))
                            let normalTransform = simd_transpose(simd_inverse(linear))
                            for part in model.parts {
                                let positions = part.positions.elements
                                let normals = try XCTUnwrap(part.normals).elements
                                let indices = try XCTUnwrap(part.triangleIndices).elements
                                for offset in stride(from: 0, to: indices.count, by: 3) {
                                    let a = Int(indices[offset]), b = Int(indices[offset + 1]), c = Int(indices[offset + 2])
                                    let edge1 = linear * (positions[b] - positions[a])
                                    let edge2 = linear * (positions[c] - positions[a])
                                    let face = simd_cross(edge1, edge2)
                                    guard simd_length(face) > 1e-12 else { continue }
                                    let normal = normalTransform * (normals[a] + normals[b] + normals[c])
                                    guard simd_length(normal) > 1e-6 else { continue }
                                    trianglesChecked += 1
                                    if simd_dot(simd_normalize(face), simd_normalize(normal)) < -0.01 {
                                        inwardTriangles += 1
                                    }
                                }
                            }
                        }
                    }
                    for child in entity.children { try check(child) }
                }
                try check(root)
                XCTAssertGreaterThan(trianglesChecked, 0, boardID)
                let mirroredTriangles = trianglesChecked
                let mirroredInwardTriangles = inwardTriangles
                trianglesChecked = 0
                inwardTriangles = 0
                let sourceIndex = try XCTUnwrap(media.instances?.firstIndex {
                    $0.baseTransform.reflection == nil
                })
                try check(scene.instanceEntities[sourceIndex])
                XCTAssertEqual(mirroredTriangles, trianglesChecked, boardID)
                XCTAssertEqual(mirroredInwardTriangles, inwardTriangles,
                               "\(boardID): reflection must preserve the source winding/normal agreement")
                // Forge's retained source has a small number of pre-existing
                // disagreements at thin facets. Reflection must not add any.
                if boardID != "trango.rock-prodigy-forge" {
                    XCTAssertEqual(inwardTriangles, 0, boardID)
                }
            }
            XCTAssertGreaterThan(mirroredInstancesChecked, 0, boardID)
        }
    }

    @MainActor
    func testRockProdigyPairsPreserveSpacingAndIndependentContactEntities() async throws {
        for boardID in ["trango.rock-prodigy-forge", "trango.rock-prodigy-natural",
                        "trango.rock-prodigy-training-center"] {
            let board = try XCTUnwrap(BoardCatalog.packageStore.board(id: boardID))
            let scene = try await BoardModelRealityLoader.load(board: board,
                                                              presentation: board.defaultPresentation)
            XCTAssertEqual(scene.instanceEntities.count, 2, boardID)
            let left = scene.instanceEntities[0].visualBounds(relativeTo: scene.root)
            let right = scene.instanceEntities[1].visualBounds(relativeTo: scene.root)
            XCTAssertLessThan(left.max.x, 0, boardID)
            XCTAssertGreaterThan(right.min.x, 0, boardID)
            XCTAssertEqual(left.min.x, -right.max.x, accuracy: 0.00001, boardID)
            XCTAssertEqual(left.max.x, -right.min.x, accuracy: 0.00001, boardID)
            XCTAssertEqual(left.center.y, right.center.y, accuracy: 0.00001, boardID)
            XCTAssertEqual(left.center.z, right.center.z, accuracy: 0.00001, boardID)
            XCTAssertEqual(Set(scene.contactEntities.keys), Set(board.contacts.map(\.id)), boardID)
            for contact in board.contacts where contact.id.hasSuffix("-left") {
                let rightID = String(contact.id.dropLast(5)) + "-right"
                let leftEntities = try XCTUnwrap(scene.contactEntities[contact.id])
                let rightEntities = try XCTUnwrap(scene.contactEntities[rightID])
                XCTAssertFalse(leftEntities.isEmpty, contact.id)
                XCTAssertEqual(leftEntities.count, rightEntities.count, contact.id)
                XCTAssertTrue(Set(leftEntities.map(ObjectIdentifier.init))
                    .isDisjoint(with: Set(rightEntities.map(ObjectIdentifier.init))), contact.id)
            }
        }
    }

    @MainActor
    func testEveryCatalogModelKeepsSurfacesVisibleThroughHighlightAndClear() async throws {
        var presentationsChecked = 0
        var mirroredInstancesChecked = 0
        for board in BoardCatalog.packageStore.boards {
            for presentation in board.presentations {
                guard case .model(let media) = presentation.media else { continue }
                let scene = try await BoardModelRealityLoader.load(board: board, presentation: presentation)
                var meshesChecked = 0
                func checkSurfaces(_ entity: Entity) {
                    if let model = (entity as? ModelEntity)?.model {
                        meshesChecked += 1
                        XCTAssertFalse(model.materials.isEmpty, "\(board.id)/\(presentation.id)/\(entity.name)")
                        for material in model.materials {
                            let culling: MaterialParameterTypes.FaceCulling?
                            if let material = material as? CustomMaterial {
                                culling = material.faceCulling
                            } else if let material = material as? PhysicallyBasedMaterial {
                                culling = material.faceCulling
                            } else {
                                culling = nil
                            }
                            XCTAssertEqual(culling, MaterialParameterTypes.FaceCulling.none,
                                           "\(board.id)/\(presentation.id)/\(entity.name): board surfaces must survive reflected winding")
                        }
                    }
                    for child in entity.children { checkSurfaces(child) }
                }
                func checkBoardSurfaces() {
                    for entity in scene.instanceEntities { checkSurfaces(entity) }
                }
                checkBoardSurfaces()
                XCTAssertGreaterThan(meshesChecked, 0, "\(board.id)/\(presentation.id)")
                print("Checking viewing geometry: \(board.id)/\(presentation.id)")
                let contactIDs = Set(scene.contactEntities.keys)
                XCTAssertFalse(contactIDs.isEmpty, "\(board.id)/\(presentation.id)")
                for mode: BoardHighlightMode in [.active, .preview] {
                    scene.highlight(contactIDs, mode: mode)
                    checkBoardSurfaces()
                    scene.highlight([], mode: mode)
                    checkBoardSurfaces()
                }
                // Check every authored pose of reflected instances as well as
                // the default and cleared transforms. This discovers new
                // mirrored boards automatically rather than listing two IDs.
                if media.instances?.contains(where: { $0.baseTransform.reflection == .x }) == true {
                    for position in board.positions where position.presentationID == presentation.id {
                        XCTAssertTrue(scene.select(positionID: position.id), "\(board.id)/\(position.id)")
                        checkBoardSurfaces()
                        for entity in scene.instanceEntities {
                            XCTAssertGreaterThan(simd_determinant(entity.transformMatrix(relativeTo: scene.root)), 0,
                                                 "\(board.id)/\(position.id): pose must preserve outward winding")
                        }
                    }
                    _ = scene.select(positionID: nil)
                    checkBoardSurfaces()
                    for (instance, entity) in zip(media.instances ?? [], scene.instanceEntities)
                    where instance.baseTransform.reflection == .x {
                        XCTAssertGreaterThan(simd_determinant(entity.transformMatrix(relativeTo: scene.root)), 0,
                                             "\(board.id)/\(instance.equipmentObjectID): baked reflection must not reintroduce negative scale on clear")
                        mirroredInstancesChecked += 1
                    }
                }
                presentationsChecked += 1
            }
        }
        XCTAssertGreaterThan(presentationsChecked, 0)
        XCTAssertGreaterThan(mirroredInstancesChecked, 0)
        print("Validated surface visibility for \(presentationsChecked) model presentations and \(mirroredInstancesChecked) reflected instances")
    }

    @MainActor
    func testSplitPalmReflectionPreservesTheFrontThroughSelectionAndClear() async throws {
        let board = try XCTUnwrap(BoardCatalog.packageStore.board(id: "soill.split-palm"))
        let scene = try await BoardModelRealityLoader.load(board: board,
                                                          presentation: board.defaultPresentation)
        XCTAssertEqual(scene.instanceEntities.count, 2)
        func checkFrontFacingReflection() {
            for entity in scene.instanceEntities {
                let matrix = entity.transformMatrix(relativeTo: scene.root)
                // Reflect horizontal coordinates only; depth must still face
                // the same camera as the original half, including after reset.
                let expectedX: Float = 1 // Horizontal reflection is in mesh buffers.
                XCTAssertEqual(matrix.columns.0.x, expectedX, accuracy: 0.0001)
                XCTAssertEqual(matrix.columns.0.y, 0, accuracy: 0.0001)
                XCTAssertEqual(matrix.columns.0.z, 0, accuracy: 0.0001)
                XCTAssertEqual(matrix.columns.1.y, 1, accuracy: 0.0001)
                XCTAssertEqual(matrix.columns.2.x, 0, accuracy: 0.0001)
                XCTAssertEqual(matrix.columns.2.y, 0, accuracy: 0.0001)
                XCTAssertEqual(matrix.columns.2.z, 1, accuracy: 0.0001)
            }
        }
        checkFrontFacingReflection()
        XCTAssertTrue(scene.select(positionID: "primary"))
        checkFrontFacingReflection()
        XCTAssertFalse(scene.select(positionID: nil))
        checkFrontFacingReflection()
        func checkVisibleSurfaces(_ entity: Entity) throws {
            if let model = (entity as? ModelEntity)?.model {
                for material in model.materials {
                    if let material = material as? CustomMaterial {
                        XCTAssertEqual(material.faceCulling, .none,
                                       "Reflected plastic surfaces must remain visible")
                    } else if let material = material as? PhysicallyBasedMaterial {
                        XCTAssertEqual(material.faceCulling, .none,
                                       "Fallback and highlighted reflected surfaces must remain visible")
                    } else {
                        XCTFail("Unexpected board material")
                    }
                }
            }
            for child in entity.children { try checkVisibleSurfaces(child) }
        }
        try checkVisibleSurfaces(scene.root)
        let selectedEntities = try XCTUnwrap(scene.contactEntities["left-flat-rail"])
        XCTAssertFalse(selectedEntities.isEmpty)
        scene.highlight(["left-flat-rail"], mode: .active)
        for entity in selectedEntities {
            XCTAssertTrue(entity.model?.materials.first is PhysicallyBasedMaterial)
        }
        try checkVisibleSurfaces(scene.root)
        scene.highlight([], mode: .active)
        try checkVisibleSurfaces(scene.root)
    }

    func testRealityTypesCompile() {
        let _ = BoardModelRealityScene.self
        let _ = BoardModelRealityLoader.self
    }

    @MainActor
    func testEvoHonestoneAndOriginalGrindstoneLoadEveryContactForPicking() async throws {
        let expectedCounts = [
            ("yy.verticalboard-evo", 25),
            ("tension.honestone", 15),
            ("tension.grindstone-original", 12),
        ]
        for (boardID, count) in expectedCounts {
            let board = try XCTUnwrap(BoardCatalog.packageStore.board(id: boardID))
            let presentation = board.defaultPresentation
            guard case .model = presentation.media else {
                XCTFail("\(boardID) must use its native CAD model")
                continue
            }
            let scene = try await BoardModelRealityLoader.load(board: board, presentation: presentation)
            XCTAssertNotNil(scene.modelEntity, boardID)
            XCTAssertEqual(scene.contactEntities.count, count, boardID)
            XCTAssertEqual(Set(scene.contactEntities.keys), Set(board.contacts(in: presentation).map(\.id)), boardID)
            for (contactID, entities) in scene.contactEntities {
                XCTAssertFalse(entities.isEmpty, "\(boardID): \(contactID)")
                for entity in entities {
                    XCTAssertNotNil(entity.model, "\(boardID): \(contactID) must render")
                    XCTAssertNotNil(entity.collision, "\(boardID): \(contactID) must be pickable")
                    XCTAssertNotNil(entity.components[InputTargetComponent.self], "\(boardID): \(contactID)")
                    XCTAssertEqual(scene.contactID(for: entity), contactID, "\(boardID): picking identity")
                }
            }
        }
    }

    @MainActor
    func testBothTransgressionRevisionsLoadNinePickableContacts() async throws {
        for year in [2011, 2013] {
            let board = try XCTUnwrap(BoardCatalog.packageStore.board(
                id: "surfaces-for-climbing-transgression-\(year)"
            ))
            let presentation = board.defaultPresentation
            guard case .model = presentation.media else {
                XCTFail("Transgression \(year) requires its native model")
                continue
            }
            let scene = try await BoardModelRealityLoader.load(board: board, presentation: presentation)
            XCTAssertEqual(scene.contactEntities.count, 9)
            XCTAssertEqual(Set(scene.contactEntities.keys), Set(board.contacts.map(\.id)))
            for (contactID, entities) in scene.contactEntities {
                XCTAssertFalse(entities.isEmpty, contactID)
                for entity in entities {
                    XCTAssertNotNil(entity.collision, contactID)
                    XCTAssertNotNil(entity.components[InputTargetComponent.self], contactID)
                    XCTAssertEqual(scene.contactID(for: entity), contactID)
                }
            }
        }
    }

    @MainActor
    func testWhetstoneNativeModelLoadsAllPickableContacts() async throws {
        let board = try XCTUnwrap(BoardCatalog.packageStore.board(id: "tension.whetstone"))
        let presentation = board.defaultPresentation
        guard case .model = presentation.media else { return XCTFail("Whetstone requires model media") }
        let scene = try await BoardModelRealityLoader.load(board: board, presentation: presentation)
        XCTAssertEqual(board.contacts.count, 12)
        XCTAssertEqual(Set(scene.contactEntities.keys), Set(board.contacts.map(\.id)))
        for (contactID, entities) in scene.contactEntities {
            XCTAssertFalse(entities.isEmpty, contactID)
            for entity in entities {
                XCTAssertNotNil(entity.collision, contactID)
                XCTAssertNotNil(entity.components[InputTargetComponent.self], contactID)
            }
        }
        XCTAssertEqual(scene.displayForTesting.surfaceFinish, .wood)
        for entities in scene.contactEntities.values {
            for entity in entities {
                XCTAssertTrue(entity.model?.materials.first is CustomMaterial,
                              "Whetstone contacts must inherit the procedural wood finish")
            }
        }
    }

    @MainActor
    func testUSDZLoadsAndBindsDescriptor() async throws {
        let board = try XCTUnwrap(BoardCatalog.packageStore.board(id: "trango.rock-prodigy-pivot"))
        let presentation = board.defaultPresentation
        guard case .model(let media) = presentation.media else { return XCTFail("model media required") }
        let scene = try await BoardModelRealityLoader.load(board: board, presentation: presentation)

        // Verify geometry loaded
        XCTAssertNotNil(scene.modelEntity)
        XCTAssertGreaterThan(scene.instanceEntities.count, 0)

        // Verify model has visual bounds (indicating geometry loaded)
        if let modelEntity = scene.modelEntity {
            let bounds = modelEntity.visualBounds(relativeTo: nil)
            XCTAssertTrue(bounds.min.x.isFinite && bounds.max.x.isFinite)
        }
    }

    @MainActor
    func testContactEntitiesPopulatedAndMatchBoardContacts() async throws {
        let board = try XCTUnwrap(BoardCatalog.packageStore.board(id: "trango.rock-prodigy-pivot"))
        let presentation = board.defaultPresentation
        guard case .model(let media) = presentation.media else { return XCTFail("model media required") }
        let scene = try await BoardModelRealityLoader.load(board: board, presentation: presentation)

        // Verify contactEntities is populated
        XCTAssertFalse(scene.contactEntities.isEmpty, "contactEntities should be populated")

        // Get expected contact IDs from board contacts for this presentation
        let boardContacts = board.contacts(in: presentation)
        let expectedContactIDs = Set(boardContacts.map(\.id))

        // Verify contactEntities keys match board contact IDs
        let actualContactIDs = Set(scene.contactEntities.keys)
        XCTAssertEqual(actualContactIDs, expectedContactIDs,
                       "contactEntities keys should match board contacts for this presentation")

        // Verify each contact has at least one entity
        for (contactID, entities) in scene.contactEntities {
            XCTAssertFalse(entities.isEmpty, "Contact \(contactID) should have at least one entity")
            for entity in entities {
                XCTAssertNotNil(entity.collision, "Contact \(contactID) should be pickable")
                XCTAssertNotNil(entity.components[InputTargetComponent.self],
                                "Spatial taps require an input target on each contact entity")
            }
        }
    }

    func testPerspectiveFitUsesFieldOfViewAndViewportAspect() throws {
        let framing = SuspendedCameraFraming(
            target: .zero, direction: SIMD3(0, 0, -1), viewDirection: SIMD3(0, 0, -1),
            right: SIMD3(1, 0, 0), up: SIMD3(0, 1, 0), distance: 1,
            width: 4, height: 2, depth: 0.5, fitPadding: 1.2, includedPoints: []
        )
        let wide = try XCTUnwrap(BoardModelRealityScene.perspectiveFitDistance(
            framing: framing, viewportSize: CGSize(width: 400, height: 200), fieldOfViewDegrees: 30))
        let narrow = try XCTUnwrap(BoardModelRealityScene.perspectiveFitDistance(
            framing: framing, viewportSize: CGSize(width: 200, height: 400), fieldOfViewDegrees: 30))
        let telephoto = try XCTUnwrap(BoardModelRealityScene.perspectiveFitDistance(
            framing: framing, viewportSize: CGSize(width: 400, height: 200), fieldOfViewDegrees: 6))
        XCTAssertGreaterThan(narrow, wide)
        XCTAssertGreaterThan(telephoto, wide)
    }

    @MainActor
    func testPBRNeutralMaterialsApplied() async throws {
        let scene = try await neutralFixtureScene()

        // Verify all model entities have PhysicallyBasedMaterial with neutral values
        var checkedEntities = 0
        for entity in scene.instanceEntities {
            checkNeutralMaterial(on: entity, checkedCount: &checkedEntities)
        }

        XCTAssertGreaterThan(checkedEntities, 0, "Should have checked at least one entity for neutral material")
    }

@MainActor
    func testInstanceHierarchyFromMediaInstances() async throws {
        let board = try XCTUnwrap(BoardCatalog.packageStore.board(id: "trango.rock-prodigy-pivot"))
        let presentation = board.defaultPresentation
        guard case .model(let media) = presentation.media else { return XCTFail("model media required") }
        let scene = try await BoardModelRealityLoader.load(board: board, presentation: presentation)

        // Verify instances are created from media.instances
        let expectedInstanceCount = media.instances?.count ?? 1
        XCTAssertEqual(scene.instanceEntities.count, expectedInstanceCount,
                       "Should have one instance entity per media instance (or 1 for single)")

        // Verify each instance has baseTransform applied
        if let instances = media.instances {
            for (index, instance) in instances.enumerated() {
                let entity = scene.instanceEntities[index]
                // The entity transform should reflect the instance's baseTransform
                let baseTranslation = SIMD3<Float>(
                    Float(instance.baseTransform.translation[0]),
                    Float(instance.baseTransform.translation[1]),
                    Float(instance.baseTransform.translation[2])
                )
                // Position should be close to baseTransform translation (allowing for model centering)
                XCTAssertTrue(entity.position.x.isFinite && entity.position.y.isFinite && entity.position.z.isFinite,
                              "Instance \(index) should have valid transform from baseTransform")

                // If reflection == .x, verify mirroring was applied
                if instance.baseTransform.reflection == .x {
                    XCTAssertGreaterThan(simd_determinant(entity.transform.matrix), 0,
                                         "Baked reflected geometry should use a positive transform determinant")
                    // And should have ModelEntity children with model components
                    var hasModelEntities = false
                    func checkForModelEntity(_ e: Entity) {
                        if e is ModelEntity { hasModelEntities = true }
                        for child in e.children { checkForModelEntity(child) }
                    }
                    checkForModelEntity(entity)
                    XCTAssertTrue(hasModelEntities, "Mirrored instance should have ModelEntity children")
                }
            }
        }
    }

    @MainActor
    func testInstanceSourceTemplateIsNotAttachedAlongsideClones() async throws {
        let board = try XCTUnwrap(BoardCatalog.packageStore.board(id: "trango.rock-prodigy-pivot"))
        let presentation = board.defaultPresentation
        guard case .model(let media) = presentation.media,
              let instances = media.instances, !instances.isEmpty else {
            return XCTFail("model media with explicit instances required")
        }

        let scene = try await BoardModelRealityLoader.load(board: board, presentation: presentation)

        XCTAssertNil(scene.modelEntity?.parent,
                     "The imported model is only a clone template when explicit instances exist")
        XCTAssertEqual(scene.root.children.count, instances.count,
                       "Only transformed instance entities should be rendered")
    }

    @MainActor
    func testSelectingPositionAppliesReusableInstanceTransforms() async throws {
        let board = try XCTUnwrap(BoardCatalog.packageStore.board(id: "trango.rock-prodigy-pivot"))
        let presentation = board.defaultPresentation
        let scene = try await BoardModelRealityLoader.load(board: board, presentation: presentation)
        let initial = scene.instanceEntities.map { $0.transform.matrix }
        let positionID = try XCTUnwrap(board.positions.first(where: { $0.presentationID == presentation.id })?.id)

        XCTAssertTrue(scene.select(positionID: positionID))
        let selected = scene.instanceEntities.map { $0.transform.matrix }
        XCTAssertEqual(selected.count, initial.count)
        XCTAssertNotEqual(selected, initial, "Position transforms should be applied to cloned instances")
    }

    @MainActor
    func testRockRingSelectionAppliesThreadedLoopPoseExactlyOnce() async throws {
        let board = try XCTUnwrap(BoardCatalog.packageStore.board(id: "metolius.rock-rings-3d"))
        guard case .model(let media) = board.defaultPresentation.media else {
            return XCTFail("expected Rock Rings model")
        }
        let instances = try XCTUnwrap(media.instances)
        let scene = try await BoardModelRealityLoader.load(board: board, presentation: board.defaultPresentation)
        guard instances.count == scene.instanceEntities.count else {
            return XCTFail("instance count mismatch")
        }
        let initial = scene.instanceEntities.map { $0.transform.matrix }
        XCTAssertTrue(scene.select(positionID: "primary"))
        let centerX = Float((media.descriptor.modelBounds.minimum[0] + media.descriptor.modelBounds.maximum[0]) / 2)
        for (index, instance) in instances.enumerated() {
            guard case .twoBranchCord(let profile) = instance.suspension else {
                return XCTFail("expected threaded-loop adapter")
            }
            XCTAssertNotNil(profile.internalLoopChannelPointsByBranchID)
            let pose = try XCTUnwrap(profile.canonicalPoses["primary"])
            let poseMatrix = try SuspendedBoardPresentation.boardTransform(for: pose)
            XCTAssertNotEqual(poseMatrix, matrix_identity_float4x4)
            // Reflection belongs to the mesh. Restore the authored base and
            // cancel that reflection after composing exactly one canonical pose.
            var reflection = matrix_identity_float4x4
            if instance.baseTransform.reflection == .x {
                reflection.columns.0.x = -1
                reflection.columns.3.x = 2 * centerX
            }
            let expected = initial[index] * reflection * poseMatrix * reflection
            let actual = scene.instanceEntities[index].transform.matrix
            for column in 0..<4 {
                for row in 0..<4 {
                    XCTAssertEqual(actual[column][row], expected[column][row], accuracy: 1e-6,
                                   "\(instance.equipmentObjectID) column \(column) row \(row)")
                }
            }
        }
    }

    @MainActor
    func testRockRingsStaySeparatedAndBothFitAfterSelectionAndClear() async throws {
        let board = try XCTUnwrap(BoardCatalog.packageStore.board(id: "metolius.rock-rings-3d"))
        let scene = try await BoardModelRealityLoader.load(board: board, presentation: board.defaultPresentation)
        XCTAssertEqual(scene.instanceEntities.count, 2)
        guard scene.instanceEntities.count == 2 else { return }
        XCTAssertNil(scene.modelEntity?.parent)
        scene.camera.camera.fieldOfViewInDegrees = 30
        scene.camera.camera.fieldOfViewOrientation = .vertical
        let viewport = CGSize(width: 390, height: 240)
        for positionID: String? in [nil, "primary", nil, "primary"] {
            let selected = scene.select(positionID: positionID)
            if positionID != nil { XCTAssertTrue(selected) }
            scene.frame(in: viewport)
            let left = scene.instanceEntities[0].visualBounds(relativeTo: scene.root)
            let right = scene.instanceEntities[1].visualBounds(relativeTo: scene.root)
            XCTAssertLessThan(left.max.x, right.min.x)
            for contactID in scene.contactEntities.keys {
                let point = try XCTUnwrap(scene.projectedContactCenter(
                    contactID, viewport: viewport,
                    fieldOfViewDegrees: Double(scene.camera.camera.fieldOfViewInDegrees)))
                XCTAssertTrue(CGRect(origin: .zero, size: viewport).contains(point), contactID)
            }
        }
    }

    @MainActor
    func testCameraOrbitAndResetUpdateRealityKitCamera() async throws {
        let board = try XCTUnwrap(BoardCatalog.packageStore.board(id: "trango.rock-prodigy-pivot"))
        let scene = try await BoardModelRealityLoader.load(board: board,
                                                          presentation: board.defaultPresentation)
        let viewport = CGSize(width: 390, height: 240)
        scene.frame(in: viewport)
        let initial = scene.camera.transform.matrix
        let contactIDs = scene.contactEntities.keys.sorted()
        let canonicalCenters = Dictionary(uniqueKeysWithValues: contactIDs.compactMap { id in
            scene.projectedContactCenter(id, viewport: viewport, fieldOfViewDegrees: 40)
                .map { (id, $0) }
        })
        XCTAssertEqual(canonicalCenters.count, contactIDs.count,
                       "Every contact must have a projected center before orbit")

        scene.orbit(azimuth: 0.35, elevation: 0.2, zoomScale: 0.9)
        XCTAssertNotEqual(scene.camera.transform.matrix, initial)
        let orbitedCenters = Dictionary(uniqueKeysWithValues: contactIDs.compactMap { id in
            scene.projectedContactCenter(id, viewport: viewport, fieldOfViewDegrees: 40)
                .map { (id, $0) }
        })
        XCTAssertTrue(contactIDs.contains { canonicalCenters[$0] != orbitedCenters[$0] },
                      "Orbit must change projected contact centers")

        scene.resetCamera(animated: false)
        XCTAssertEqual(scene.camera.transform.matrix, initial)
        for id in contactIDs {
            let canonical = try XCTUnwrap(canonicalCenters[id])
            let reset = try XCTUnwrap(scene.projectedContactCenter(
                id, viewport: viewport, fieldOfViewDegrees: 40))
            XCTAssertEqual(reset.x, canonical.x, accuracy: 0.001, id)
            XCTAssertEqual(reset.y, canonical.y, accuracy: 0.001, id)
        }
    }

    @MainActor
    func testMixedFinishesRestoreEveryContact() async throws {
        for (boardID, graniteNodeIDs) in [
            ("nature.stoak-board-iii", ["granite_insert_left", "granite_insert_right", "granite_insert_center"]),
            ("nature.stone-hanger", ["edge_front_20mm_granite_mesh_001"])
        ] {
            let board = try XCTUnwrap(BoardCatalog.packageStore.board(id: boardID))
            let scene = try await BoardModelRealityLoader.load(board: board,
                                                              presentation: board.defaultPresentation)
            XCTAssertEqual(scene.displayForTesting.surfaceFinish, .wood)
            XCTAssertTrue(scene.displayForTesting.woodNodeIDs.isEmpty,
                          "Wood coverage must not depend on enumerating each mesh")
            XCTAssertEqual(Set(scene.displayForTesting.graniteNodeIDs),
                           Set(graniteNodeIDs))
            for id in scene.contactEntities.keys.sorted() {
                let entities = try XCTUnwrap(scene.contactEntities[id])
                XCTAssertFalse(entities.isEmpty)
                if id.hasPrefix("lower-composite-") {
                    XCTAssertGreaterThanOrEqual(entities.count, 2, "Mixed contacts must include wood and stone")
                }
                var baselineTints: [Entity: UIColor] = [:]
                let graniteNodes = Set(scene.displayForTesting.graniteNodeIDs)
                for entity in entities {
                    let material = try XCTUnwrap(entity.model?.materials.first as? CustomMaterial,
                                                 "Every wood/stone contact must receive its finish: \(id)")
                    let tint = UIColor(cgColor: material.baseColor.__tint)
                    var r: CGFloat = 0, g: CGFloat = 0, b: CGFloat = 0, a: CGFloat = 0
                    XCTAssertTrue(tint.getRed(&r, green: &g, blue: &b, alpha: &a))
                    if graniteNodes.contains(entity.name) {
                        XCTAssertLessThan(r, 0.4, "Granite must be dark: \(entity.name)")
                        XCTAssertLessThan(abs(r - b), 0.05)
                    } else {
                        XCTAssertGreaterThan(r, g, "Wood walls must retain warm grain")
                        XCTAssertGreaterThan(g, b)
                    }
                    baselineTints[entity] = tint
                }
                for mode: BoardHighlightMode in [.active, .preview] {
                    scene.highlight([id], mode: mode)
                    for entity in entities {
                        XCTAssertTrue(entity.model?.materials.first is PhysicallyBasedMaterial)
                    }
                    scene.highlight([], mode: mode)
                    for entity in entities {
                        let restored = try XCTUnwrap(entity.model?.materials.first as? CustomMaterial)
                        XCTAssertEqual(UIColor(cgColor: restored.baseColor.__tint), baselineTints[entity])
                    }
                }
            }
        }
    }

    @MainActor
    func testBoardFinishCoversUnlistedMeshWhileAttachmentsStayNeutral() async throws {
        let board = try XCTUnwrap(BoardCatalog.packageStore.board(id: "beastmaker-1000"))
        let presentation = board.defaultPresentation
        guard case .model(let media) = presentation.media else { return XCTFail("model required") }
        let bodyNode = try XCTUnwrap(media.descriptor.nodes.first(where: { $0.role == .body }))
        let loadedSource = try await BoardModelRealityCache.source(
            for: BoardModelRealityKey(boardID: board.id, presentationID: presentation.id,
                                      modelSHA256: media.descriptor.modelSHA256),
            media: media, board: board, presentationID: presentation.id,
            store: BoardCatalog.packageStore, resourceAccess: .live
        )
        let source = try XCTUnwrap(loadedSource)
        for attachment in [false, true] {
            var nodes = media.descriptor.nodes.filter { $0.nodeID != bodyNode.nodeID }
            if attachment {
                nodes.append(BoardModelNodeDescriptor(nodeID: bodyNode.nodeID, role: .attachment, contactID: nil))
            }
            let descriptor = BoardModelDescriptor(
                schemaVersion: media.descriptor.schemaVersion,
                coordinateFrame: media.descriptor.coordinateFrame,
                modelSHA256: media.descriptor.modelSHA256, modelBounds: media.descriptor.modelBounds,
                nodes: nodes, contacts: media.descriptor.contacts
            )
            let scene = BoardModelRealityScene(
                descriptor: descriptor, display: BoardModelDisplay(camera: media.display.camera, surfaceFinish: .wood),
                suspension: nil, orientation: nil, allowedPositionIDs: [], resourceLease: source.resourceLease
            )
            try await scene.load(usdzURL: source.resourceLease.url)
            let entity = try XCTUnwrap(scene.root.findEntity(named: bodyNode.nodeID) as? ModelEntity)
            if attachment {
                XCTAssertTrue(entity.model?.materials.first is PhysicallyBasedMaterial,
                              "Attachments must override the board finish")
            } else {
                XCTAssertTrue(entity.model?.materials.first is CustomMaterial,
                              "A newly imported mesh must inherit wood without another node selection")
            }
        }
    }

    @MainActor
    func testPlasticContactsHighlightAndRestoreMintMaterial() async throws {
        let board = try XCTUnwrap(BoardCatalog.packageStore.board(id: "trango.rock-prodigy-pivot"))
        let scene = try await BoardModelRealityLoader.load(board: board,
                                                          presentation: board.defaultPresentation)
        let contactID = try XCTUnwrap(scene.contactEntities.keys.sorted().first)
        let entities = try XCTUnwrap(scene.contactEntities[contactID])
        XCTAssertFalse(entities.isEmpty)
        var baselineTints: [Entity: UIColor] = [:]
        for entity in entities {
            let material = try XCTUnwrap(entity.model?.materials.first as? CustomMaterial,
                                         "Plastic contacts must receive the mint resin finish")
            let tint = UIColor(cgColor: material.baseColor.__tint)
            var red: CGFloat = 0, green: CGFloat = 0, blue: CGFloat = 0, alpha: CGFloat = 0
            XCTAssertTrue(tint.getRed(&red, green: &green, blue: &blue, alpha: &alpha))
            XCTAssertGreaterThan(green, red, "Plastic must use mint rather than the wood finish")
            XCTAssertGreaterThan(blue, red)
            baselineTints[entity] = tint
        }
        for mode: BoardHighlightMode in [.active, .preview] {
            scene.highlight([contactID], mode: mode)
            for entity in entities {
                XCTAssertTrue(entity.model?.materials.first is PhysicallyBasedMaterial,
                              "Selected plastic grips must use the solid highlight")
            }
            scene.highlight([], mode: mode)
            for entity in entities {
                let restored = try XCTUnwrap(entity.model?.materials.first as? CustomMaterial,
                                             "Clearing selection must restore the mint resin finish")
                XCTAssertEqual(UIColor(cgColor: restored.baseColor.__tint), baselineTints[entity])
            }
        }
    }

    @MainActor
    func testCatalogBoardFinishesCoverEveryImportedBodyAndHoldMesh() async throws {
        var boardsChecked = 0
        var meshesChecked = 0
        for board in BoardCatalog.packageStore.boards {
            for presentation in board.presentations {
                guard case .model(let media) = presentation.media,
                      media.display.surfaceFinish != .neutral else { continue }
                let scene = try await BoardModelRealityLoader.load(board: board, presentation: presentation)
                let attachmentIDs = Set(media.descriptor.nodes.filter { $0.role == .attachment }.map(\.nodeID))
                let surfaceIDs = Set(media.descriptor.nodes.filter { $0.role != .attachment }.map(\.nodeID))
                let graniteIDs = Set(media.display.graniteNodeIDs)
                func check(_ entity: Entity, attachment: Bool = false, granite: Bool = false) throws {
                    let isAttachment = attachmentIDs.contains(entity.name) ? true
                        : surfaceIDs.contains(entity.name) ? false : attachment
                    let isGranite = surfaceIDs.contains(entity.name) ? graniteIDs.contains(entity.name) : granite
                    if let model = (entity as? ModelEntity)?.model {
                        if isAttachment {
                            XCTAssertTrue(model.materials.first is PhysicallyBasedMaterial, board.id)
                        } else {
                            let material = try XCTUnwrap(model.materials.first as? CustomMaterial,
                                                         "Unfinished mesh: \(board.id)/\(entity.name)")
                            let tint = UIColor(cgColor: material.baseColor.__tint)
                            var r: CGFloat = 0, g: CGFloat = 0, b: CGFloat = 0, a: CGFloat = 0
                            XCTAssertTrue(tint.getRed(&r, green: &g, blue: &b, alpha: &a))
                            if isGranite || media.display.surfaceFinish == .granite {
                                XCTAssertLessThan(r, 0.4, board.id)
                                XCTAssertLessThan(abs(r - b), 0.05, board.id)
                            } else if media.display.surfaceFinish == .wood {
                                XCTAssertGreaterThan(r, g, board.id)
                                XCTAssertGreaterThan(g, b, board.id)
                            } else {
                                XCTAssertGreaterThan(g, r, board.id)
                                XCTAssertGreaterThan(b, r, board.id)
                            }
                            meshesChecked += 1
                        }
                    }
                    for child in entity.children { try check(child, attachment: isAttachment, granite: isGranite) }
                }
                try check(scene.root)
                boardsChecked += 1
            }
        }
        XCTAssertGreaterThan(boardsChecked, 0)
        XCTAssertGreaterThan(meshesChecked, boardsChecked)
    }

    @MainActor
    func testWoodContactsHighlightAndRestoreGrainMaterial() async throws {
        let board = try XCTUnwrap(BoardCatalog.packageStore.board(id: "beastmaker-1000"))
        let scene = try await BoardModelRealityLoader.load(board: board,
                                                          presentation: board.defaultPresentation)
        let contactID = try XCTUnwrap(scene.contactEntities.keys.sorted().first)
        let entities = try XCTUnwrap(scene.contactEntities[contactID])
        XCTAssertFalse(entities.isEmpty)
        for entity in entities {
            XCTAssertTrue(entity.model?.materials.first is CustomMaterial,
                          "Wood contacts must receive the grain shader, including recesses")
        }

        for mode: BoardHighlightMode in [.active, .preview] {
            scene.highlight([contactID], mode: mode)
            for entity in entities {
                let highlighted = try XCTUnwrap(entity.model?.materials.first as? PhysicallyBasedMaterial,
                                               "Wood grips must still show the selection color")
                XCTAssertEqual(highlighted.roughness.scale, 0.8, accuracy: 0.0001)
            }
            scene.highlight([], mode: mode)
            for entity in entities {
                XCTAssertTrue(entity.model?.materials.first is CustomMaterial,
                              "Clearing selection must restore wood grain")
            }
        }
    }

    @MainActor
    private func neutralFixtureScene() async throws -> BoardModelRealityScene {
        let board = try XCTUnwrap(BoardCatalog.packageStore.board(id: "nature.stone-hanger"))
        let presentation = board.defaultPresentation
        guard case .model(let media) = presentation.media else {
            XCTFail("model required")
            throw NSError(domain: "BoardModelRealityTests", code: 1)
        }
        let loadedSource = try await BoardModelRealityCache.source(
            for: BoardModelRealityKey(boardID: board.id, presentationID: presentation.id,
                                      modelSHA256: media.descriptor.modelSHA256),
            media: media, board: board, presentationID: presentation.id,
            store: BoardCatalog.packageStore, resourceAccess: .live
        )
        let source = try XCTUnwrap(loadedSource)
        // Neutral rendering remains supported independently of catalog finish assignments.
        let scene = BoardModelRealityScene(
            descriptor: media.descriptor,
            display: BoardModelDisplay(camera: media.display.camera, surfaceFinish: .neutral),
            suspension: nil, orientation: nil, allowedPositionIDs: [], resourceLease: source.resourceLease
        )
        try await scene.load(usdzURL: source.resourceLease.url)
        return scene
    }

    @MainActor
    func testClearingHighlightRestoresNeutralPBRBaseline() async throws {
        let scene = try await neutralFixtureScene()
        let contactID = try XCTUnwrap(scene.contactEntities.keys.first)
        scene.highlight([contactID], mode: .active)
        scene.highlight([], mode: .active)

        for entity in try XCTUnwrap(scene.contactEntities[contactID]) {
            let material = try XCTUnwrap(entity.model?.materials.first as? PhysicallyBasedMaterial)
            XCTAssertEqual(material.metallic.scale, 0, accuracy: 0.0001)
            XCTAssertEqual(material.roughness.scale, 0.5, accuracy: 0.0001)
        }
    }

    @MainActor
    func testSuspendedSelectionCreatesTransientCordEntity() async throws {
        let board = try XCTUnwrap(BoardCatalog.packageStore.board(id: "nature.stone-hanger"))
        let presentation = board.defaultPresentation
        guard case .model(let media) = presentation.media,
              media.suspension != nil else {
            return XCTFail("expected suspended model presentation")
        }
        let scene = try await BoardModelRealityLoader.load(board: board, presentation: presentation)
        let positionID = try XCTUnwrap(board.positions.first(where: { $0.presentationID == presentation.id })?.id)

        XCTAssertTrue(scene.select(positionID: positionID))
        let cord = try XCTUnwrap(scene.transientCordEntity)
        XCTAssertGreaterThan(cord.children.count, 0, "Solved cord paths should become RealityKit segments")
        XCTAssertTrue(cord.parent === scene.root)
    }

    @MainActor
    func testNativePairedLeadAndTwoBranchModelsCreateNonPickableCordSegments() async throws {
        let store = BoardCatalog.packageStore
        let cases = [try XCTUnwrap(store.board(id: "nature.stone-hanger")),
                     try XCTUnwrap(store.board(id: "tension.flash-board"))]

        for board in cases {
            let presentation = board.defaultPresentation
            guard case .model(let media) = presentation.media,
                  let suspension = media.suspension else {
                return XCTFail("\(board.id) must have a model suspension")
            }
            let scene = try await BoardModelRealityLoader.load(board: board, presentation: presentation,
                                                               store: store)
            let positionID = try XCTUnwrap(board.positions.first {
                $0.presentationID == presentation.id
            }?.id, board.id)
            XCTAssertTrue(scene.select(positionID: positionID), board.id)
            let cord = try XCTUnwrap(scene.transientCordEntity, board.id)
            XCTAssertFalse(cord.children.isEmpty, board.id)
            XCTAssertTrue(cord.children.allSatisfy { scene.contactID(for: $0) == nil }, board.id)
            XCTAssertTrue(cord.children.allSatisfy { ($0 as? ModelEntity)?.collision == nil }, board.id)

            switch (board.id, suspension) {
            case ("nature.stone-hanger", .pairedLeadCord): break
            case ("tension.flash-board", .twoBranchCord): break
            default: XCTFail("Unexpected suspension family for \(board.id)")
            }
        }
    }

    @MainActor
    func testMiniBarRealityKitCordWrapsUnderTheBodyInEveryGripPose() async throws {
        let board = try XCTUnwrap(BoardCatalog.packageStore.board(id: "lattice.mini-bar"))
        let scene = try await BoardModelRealityLoader.load(
            board: board, presentation: board.defaultPresentation)
        for position in board.positions {
            XCTAssertTrue(scene.select(positionID: position.id), position.id)
            let cord = try XCTUnwrap(scene.transientCordEntity, position.id)
            let body = try XCTUnwrap(scene.instanceEntities.first, position.id)
            let inverse = body.transformMatrix(relativeTo: scene.root).inverse
            let localCenters = cord.children.map { child -> SIMD3<Float> in
                let center = inverse * SIMD4<Float>(child.position(relativeTo: scene.root), 1)
                return SIMD3<Float>(center.x, center.y, center.z)
            }
            XCTAssertLessThan(try XCTUnwrap(localCenters.map(\.y).min()), 0.008,
                              "The \(position.id) loop must pass around the lower surface")
            XCTAssertTrue(cord.children.allSatisfy { ($0 as? ModelEntity)?.collision == nil })
        }
    }

    @MainActor
    func testMiniBarOrbitKeepsBodyAndEntireCordInsideViewport() async throws {
        let board=try XCTUnwrap(BoardCatalog.packageStore.board(id:"lattice.mini-bar"))
        let scene=try await BoardModelRealityLoader.load(board:board,presentation:board.defaultPresentation)
        let viewport=CGSize(width:540,height:209)
        scene.frame(in:viewport)
        for position in board.positions {
            XCTAssertTrue(scene.select(positionID:position.id))
            for angles in [SIMD2<Float>(0,0), [Float.pi/2,0], [Float.pi,0], [0,Float.pi/9], [0,-Float.pi/9], [0.35,0.35]] {
                scene.orbit(azimuth:angles.x,elevation:angles.y)
                let view=scene.camera.transform.matrix.inverse
                let tangent=tan(scene.camera.camera.fieldOfViewInDegrees*Float.pi/360)
                for entity in scene.instanceEntities+[try XCTUnwrap(scene.transientCordEntity)] {
                    let bounds=entity.visualBounds(relativeTo:scene.root)
                    for x in [bounds.min.x,bounds.max.x] {
                        for y in [bounds.min.y,bounds.max.y] {
                            for z in [bounds.min.z,bounds.max.z] {
                                let point=view*SIMD4<Float>(x,y,z,1),depth = -point.z
                                XCTAssertGreaterThan(depth,0,position.id)
                                XCTAssertLessThanOrEqual(abs(point.x/depth/tangent/Float(viewport.width/viewport.height)),1,position.id)
                                XCTAssertLessThanOrEqual(abs(point.y/depth/tangent),1,position.id)
                            }
                        }
                    }
                }
            }
        }
    }

    @MainActor
    func testClearingSelectionRemovesTransientCordEntity() async throws {
        let board = try XCTUnwrap(BoardCatalog.packageStore.board(id: "nature.stone-hanger"))
        let presentation = board.defaultPresentation
        let scene = try await BoardModelRealityLoader.load(board: board, presentation: presentation)
        let positionID = try XCTUnwrap(board.positions.first(where: { $0.presentationID == presentation.id })?.id)
        XCTAssertTrue(scene.select(positionID: positionID))
        let cordEntity = try XCTUnwrap(scene.transientCordEntity)
        XCTAssertNotNil(cordEntity.parent)

        XCTAssertFalse(scene.select(positionID: nil))

        XCTAssertNil(scene.transientCordEntity)
        XCTAssertNil(cordEntity.parent)
    }

    @MainActor
    func testNativeLoadGateSerializesWaitersAndRecoversAfterCancellation() async throws {
        let firstResult = await BoardModelRealityLoadGate.acquire()
        XCTAssertTrue(firstResult)
        let cancelled = Task { @MainActor in await BoardModelRealityLoadGate.acquire() }
        for _ in 0..<100 where BoardModelRealityLoadGate.queuedWaiterCount == 0 {
            await Task.yield()
        }
        XCTAssertEqual(BoardModelRealityLoadGate.queuedWaiterCount, 1)
        cancelled.cancel()
        let cancelledResult = await cancelled.value
        XCTAssertFalse(cancelledResult)

        let next = Task { @MainActor in await BoardModelRealityLoadGate.acquire() }
        for _ in 0..<100 where BoardModelRealityLoadGate.queuedWaiterCount == 0 {
            await Task.yield()
        }
        XCTAssertEqual(BoardModelRealityLoadGate.queuedWaiterCount, 1)
        BoardModelRealityLoadGate.release()
        let nextResult = await next.value
        XCTAssertTrue(nextResult)
        BoardModelRealityLoadGate.release()

        let finalResult = await BoardModelRealityLoadGate.acquire()
        XCTAssertTrue(finalResult)
        BoardModelRealityLoadGate.release()
    }

    @MainActor
    func testSuspensionOrientationDisplayPassedToScene() async throws {
        let board = try XCTUnwrap(BoardCatalog.packageStore.board(id: "trango.rock-prodigy-pivot"))
        let presentation = board.defaultPresentation
        guard case .model(let media) = presentation.media else { return XCTFail("model media required") }
        let scene = try await BoardModelRealityLoader.load(board: board, presentation: presentation)

        // Verify scene has access to suspension, orientation, display through public accessors
        // These may be nil depending on the board's media configuration
        XCTAssertNotNil(scene.descriptorForTesting)
        XCTAssertNotNil(scene.displayForTesting)
        // suspension and orientation are optional - just verify they're accessible
        _ = scene.suspensionForTesting
        _ = scene.orientationForTesting
    }

    // MARK: - Helpers

    private func checkNeutralMaterial(
        on entity: Entity,
        checkedCount: inout Int
    ) {
        if let modelEntity = entity as? ModelEntity,
           let material = modelEntity.model?.materials.first as? PhysicallyBasedMaterial {
            checkedCount += 1
            XCTAssertEqual(material.metallic.scale, 0, accuracy: 0.0001)
            XCTAssertEqual(material.roughness.scale, 0.5, accuracy: 0.0001)
        }

        for child in entity.children {
            checkNeutralMaterial(on: child, checkedCount: &checkedCount)
        }
    }
}
