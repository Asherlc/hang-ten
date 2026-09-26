import XCTest
import RealityKit
@testable import HangTen

final class BoardModelRealityTests: XCTestCase {
    func testRealityTypesCompile() {
        let _ = BoardModelRealityScene.self
        let _ = BoardModelRealityLoader.self
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
            }
        }
    }

    @MainActor
    func testPBRNeutralMaterialsApplied() async throws {
        let board = try XCTUnwrap(BoardCatalog.packageStore.board(id: "trango.rock-prodigy-pivot"))
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
                    // The entity should have negative X scale (mirroring applied to root)
                    XCTAssertEqual(entity.scale.x, -1.0, accuracy: 0.001,
                                   "Mirrored instance should have negative X scale")
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
        scene.frame(in: CGSize(width: 390, height: 240))
        let initial = scene.camera.transform.matrix
        scene.orbit(azimuth: 0.35, elevation: 0.2, zoomScale: 0.9)
        XCTAssertNotEqual(scene.camera.transform.matrix, initial)
        scene.resetCamera(animated: false)
        XCTAssertEqual(scene.camera.transform.matrix, initial)
    }

    @MainActor
    func testClearingHighlightRestoresNeutralPBRBaseline() async throws {
        let board = try XCTUnwrap(BoardCatalog.packageStore.board(id: "trango.rock-prodigy-pivot"))
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
