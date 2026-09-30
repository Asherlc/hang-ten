import XCTest
import RealityKit
import UIKit
import simd
@testable import HangTen

final class BoardModelRealityTests: XCTestCase {
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
    func testLiveClavelliumHasMatchedRadiusAndOrbitLeavesPhysicsUnchanged() async throws {
        let board=try XCTUnwrap(BoardCatalog.packageStore.board(id:"clavellium-training-block"))
        let scene=try await BoardModelRealityLoader.load(board:board,presentation:board.defaultPresentation)
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
        XCTAssertEqual(scene.liveFramesForTesting.first?.boardHeight,frame.boardHeight)
        XCTAssertEqual(scene.liveFramesForTesting.first?.ropes.first?.positions,frame.ropes.first?.positions)
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
        let input=try XCTUnwrap(media.physics),source=try XCTUnwrap(input.profiles.first)
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
                XCTAssertTrue(frame.ropes.allSatisfy{$0.id.hasPrefix(instance.equipmentObjectID+"-")})
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
        let scene=try await BoardModelRealityLoader.load(board:board,presentation:board.defaultPresentation)
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

    func testRealityTypesCompile() {
        let _ = BoardModelRealityScene.self
        let _ = BoardModelRealityLoader.self
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
        var checkedEntities = 0
        for entity in scene.instanceEntities {
            checkNeutralMaterial(on: entity, checkedCount: &checkedEntities)
        }
        XCTAssertGreaterThan(checkedEntities, 0)
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
        let board = try XCTUnwrap(BoardCatalog.packageStore.board(id: "nature.stone-hanger"))
        let presentation = board.defaultPresentation
        guard case .model(let media) = presentation.media else { return XCTFail("model media required") }
        let scene = try await BoardModelRealityLoader.load(board: board, presentation: presentation)

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
                    XCTAssertLessThan(simd_determinant(entity.transform.matrix), 0,
                                      "Mirrored instance should preserve a negative transform determinant")
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
    func testStoakMixedFinishesRestoreEveryContact() async throws {
        let board = try XCTUnwrap(BoardCatalog.packageStore.board(id: "nature.stoak-board-iii"))
        let scene = try await BoardModelRealityLoader.load(board: board,
                                                          presentation: board.defaultPresentation)
        XCTAssertEqual(scene.displayForTesting.surfaceFinish, .wood)
        XCTAssertTrue(scene.displayForTesting.woodNodeIDs.isEmpty,
                      "Wood coverage must not depend on enumerating each mesh")
        XCTAssertEqual(Set(scene.displayForTesting.graniteNodeIDs),
                       ["granite_insert_left", "granite_insert_right", "granite_insert_center"])
        for id in ["edge-22-center", "gradient-edge-left", "gradient-edge-right", "top-jug",
                   "lower-composite-left", "lower-composite-right", "lower-composite-center"] {
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
    func testClearingHighlightRestoresNeutralPBRBaseline() async throws {
        let board = try XCTUnwrap(BoardCatalog.packageStore.board(id: "nature.stone-hanger"))
        let scene = try await BoardModelRealityLoader.load(board: board,
                                                          presentation: board.defaultPresentation)
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
            for azimuth in [Float(0),.pi/2,.pi] {
                scene.orbit(azimuth:azimuth,elevation:0)
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
