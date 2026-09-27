import RealityKit
import SwiftUI
import XCTest
@testable import HangTen

/// Mirrors BoardModelTests's orbit coverage so both rotatable models share
/// the same bounded-turntable guarantees: a full spin returns to the start,
/// zoom stays clamped, and a reset restores the canonical framing.
final class GripHandOrbitTests: XCTestCase {
    func testVerticalFirstDragKeepsScrollingAfterTurningHorizontal() {
        var drag = GripHandDragState()

        XCTAssertNil(drag.advance(translation: CGSize(width: 2, height: 12),
                                  velocity: CGSize(width: 1, height: 15)))
        XCTAssertEqual(drag.disposition, .scroll)
        XCTAssertNil(drag.advance(translation: CGSize(width: 35, height: 14),
                                  velocity: CGSize(width: 30, height: 1)))
        XCTAssertEqual(drag.disposition, .scroll)
    }

    func testHorizontalDragSeedsOrbitDeltaAtClaimAndResetsForNextGesture() {
        var drag = GripHandDragState()

        XCTAssertNil(drag.advance(translation: CGSize(width: 12, height: 2),
                                  velocity: CGSize(width: 15, height: 1)))
        XCTAssertEqual(drag.disposition, .orbit)
        XCTAssertEqual(drag.advance(translation: CGSize(width: 16, height: 5),
                                    velocity: CGSize(width: 5, height: 3)),
                       CGSize(width: 4, height: 3))

        drag.reset()
        XCTAssertEqual(drag.disposition, .undecided)
        XCTAssertNil(drag.advance(translation: CGSize(width: 1, height: 11),
                                  velocity: CGSize(width: 1, height: 12)))
        XCTAssertEqual(drag.disposition, .scroll)
    }

    @MainActor
    func testRealitySceneShowsUnavailableStateForAssetFailure() {
        let scene = GripHandRealityScene(assetResult: .failure(GripHandAsset.AssetError.missingResource))

        XCTAssertTrue(scene.isUnavailable)
        XCTAssertTrue(scene.hand.children.isEmpty)
    }

    @MainActor
    func testHostSyncForwardsPoseFingersSideViewportAndReset() throws {
        let scene = GripHandRealityScene()
        let fingers = FingerConfiguration(engagedFingers: [.index, .ring])
        let view = GripHandModelView(posture: .halfCrimp, fingerConfiguration: fingers,
                                     side: .left, resetToken: 4, scene: scene)
        let _: any View = view

        view.syncScene(in: CGSize(width: 180, height: 260))

        XCTAssertEqual(scene.currentPose?.action(), "HalfCrimp")
        XCTAssertEqual(scene.currentPose?.highlightedFingers, [.index, .ring])
        XCTAssertEqual(scene.hand.scale.x, -1)
        let narrowScale = try XCTUnwrap(scene.camera.components[OrthographicCameraComponent.self]).scale

        scene.orbit(azimuthDelta: 0.3, elevationDelta: 0)
        let orbitPosition = scene.camera.position
        view.syncScene(in: CGSize(width: 300, height: 260))
        XCTAssertNotEqual(scene.camera.position, orbitPosition)
        let wideScale = try XCTUnwrap(scene.camera.components[OrthographicCameraComponent.self]).scale
        XCTAssertLessThan(wideScale, narrowScale)

        scene.orbit(azimuthDelta: 0.3, elevationDelta: 0)
        let secondOrbitPosition = scene.camera.position
        let resetView = GripHandModelView(posture: .halfCrimp, fingerConfiguration: fingers,
                                          side: .left, resetToken: 5, scene: scene)
        resetView.syncScene(in: CGSize(width: 300, height: 260))
        XCTAssertNotEqual(scene.camera.position, secondOrbitPosition)
    }
    @MainActor
    func testRealityMeshUsesBundledPosePositionsNormalsAndIndices() throws {
        let asset = try GripHandAsset.bundled.get()
        let surface = try GripHandRealitySurface(asset: asset)

        try surface.apply(GripHandPose(posture: .halfCrimp, fingerConfiguration: nil))

        XCTAssertNotNil(surface.modelEntity.model)
        XCTAssertEqual(surface.vertexCount, asset.vertexCount)
        XCTAssertEqual(surface.triangleCount, asset.indices.count / 3)
        let vertices = surface.posedVerticesForFraming()
        XCTAssertEqual(vertices.count, asset.vertexCount)
        XCTAssertTrue(vertices.allSatisfy { $0.x.isFinite && $0.y.isFinite && $0.z.isFinite })
        let bounds = vertices.reduce((SIMD3<Float>(repeating: .greatestFiniteMagnitude),
                                      SIMD3<Float>(repeating: -.greatestFiniteMagnitude))) { result, point in
            (simd_min(result.0, point), simd_max(result.1, point))
        }
        XCTAssertTrue((bounds.1 - bounds.0).x > 0)
        XCTAssertTrue((bounds.1 - bounds.0).y > 0)
        XCTAssertTrue((bounds.1 - bounds.0).z > 0)
    }

    @MainActor
    private func makeScene() -> GripHandRealityScene {
        let scene = GripHandRealityScene()
        scene.update(
            pose: GripHandPose(posture: .halfCrimp, fingerConfiguration: nil),
            side: .right,
            viewportSize: CGSize(width: 200, height: 260),
            resetToken: 0
        )
        return scene
    }

    func testVertexColorsUseBaseColorForEmptySelection() throws {
        let asset = try makeColorFixture()
        let action = GripHandPose(posture: .halfCrimp, fingerConfiguration: nil)

        let colors = try GripHandRealityMeshBuilder.vertexColors(
            asset: asset,
            action: action,
            selectedFingers: []
        )

        XCTAssertEqual(colors, Array(repeating: SIMD4<Float>(0.687, 0.392, 0.242, 1), count: 3))
    }

    func testVertexColorsHighlightOnlySelectedAuthoredDigit() throws {
        let asset = try makeColorFixture()
        let action = GripHandPose(posture: .halfCrimp, fingerConfiguration: nil)

        let colors = try GripHandRealityMeshBuilder.vertexColors(
            asset: asset,
            action: action,
            selectedFingers: [.index]
        )

        XCTAssertEqual(colors[0], SIMD4<Float>(0.966, 0.0615, 0.0108, 1))
        XCTAssertEqual(colors[1], SIMD4<Float>(0.687, 0.392, 0.242, 1))
        XCTAssertEqual(colors[2], SIMD4<Float>(0.687, 0.392, 0.242, 1))
    }

    func testVertexColorsUseHalfWeightForSelectedMiddleFinger() throws {
        let asset = try makeColorFixture()
        let action = GripHandPose(posture: .halfCrimp, fingerConfiguration: nil)

        let colors = try GripHandRealityMeshBuilder.vertexColors(
            asset: asset,
            action: action,
            selectedFingers: [.middle]
        )

        XCTAssertEqual(colors[1], SIMD4<Float>(0.8265, 0.22675, 0.1264, 1))
    }

    func testVertexColorsHighlightSelectedIndexAndRingOnly() throws {
        let asset = try makeColorFixture()
        let action = GripHandPose(posture: .halfCrimp, fingerConfiguration: nil)

        let colors = try GripHandRealityMeshBuilder.vertexColors(
            asset: asset,
            action: action,
            selectedFingers: [.index, .ring]
        )

        XCTAssertEqual(colors[0], SIMD4<Float>(0.966, 0.0615, 0.0108, 1))
        XCTAssertEqual(colors[1], SIMD4<Float>(0.687, 0.392, 0.242, 1))
        XCTAssertEqual(colors[2], SIMD4<Float>(0.966, 0.0615, 0.0108, 1))
    }

    func testVertexColorsUseGeometryActionIndependentOfColorMembership() throws {
        let asset = try makeColorFixture()
        let pocketAction = GripHandPose(posture: .twoFingerPocket, fingerConfiguration: nil)
        let explicitPose = GripHandPose(
            posture: .halfCrimp,
            fingerConfiguration: FingerConfiguration(engagedFingers: [.ring])
        )

        let pocketColors = try GripHandRealityMeshBuilder.vertexColors(
            asset: asset,
            action: pocketAction,
            selectedFingers: [.index]
        )
        let explicitPoseColors = try GripHandRealityMeshBuilder.vertexColors(
            asset: asset,
            action: explicitPose,
            selectedFingers: [.index]
        )

        XCTAssertEqual(pocketAction.action(), "Pocket0")
        XCTAssertEqual(explicitPose.action(), "HalfCrimp")
        XCTAssertEqual(pocketColors, explicitPoseColors)
        XCTAssertEqual(pocketColors[0], SIMD4<Float>(0.966, 0.0615, 0.0108, 1))
        XCTAssertEqual(pocketColors[2], SIMD4<Float>(0.687, 0.392, 0.242, 1))
    }

    private func makeColorFixture() throws -> GripHandAsset {
        let surface = ["positions": [0, 0, 0, 1, 0, 0, 0, 1, 0],
                       "normals": [0, 0, 1, 0, 0, 1, 0, 0, 1]]
        let poseNames = ["Neutral", "OpenHand", "HalfCrimp", "FullCrimp", "Sloper"]
            + (0...15).map { "Pocket\($0)" }
        let fixture: [String: Any] = [
            "schemaVersion": 2,
            "indices": [0, 1, 2],
            "digitIndices": [2, 3, 4],
            "highlightWeights": [1, 0.5, 1],
            "poses": Dictionary(uniqueKeysWithValues: poseNames.map { ($0, surface) })
        ]
        return try GripHandAsset.decode(JSONSerialization.data(withJSONObject: fixture))
    }

    @MainActor
    func testFullAzimuthOrbitReturnsCameraToItsStartingPosition() throws {
        let scene = makeScene()
        let startPosition = scene.camera.position
        let startScale = try XCTUnwrap(scene.camera.components[OrthographicCameraComponent.self]).scale

        let steps = 12
        for _ in 0..<steps {
            scene.orbit(azimuthDelta: .pi * 2 / Float(steps), elevationDelta: 0)
        }

        XCTAssertEqual(scene.camera.position.x, startPosition.x, accuracy: 1e-3)
        XCTAssertEqual(scene.camera.position.y, startPosition.y, accuracy: 1e-3)
        XCTAssertEqual(scene.camera.position.z, startPosition.z, accuracy: 1e-3)
        XCTAssertEqual(scene.camera.components[OrthographicCameraComponent.self]?.scale ?? -1, startScale, accuracy: 1e-6)
    }

    @MainActor
    func testOrbitZoomIsBoundedAndResetRestoresCanonicalFraming() throws {
        let scene = makeScene()
        let canonicalPosition = scene.camera.position
        let canonicalScale = try XCTUnwrap(scene.camera.components[OrthographicCameraComponent.self]).scale

        scene.orbit(azimuthDelta: 0.4, elevationDelta: 0.2, zoomScale: 100)
        XCTAssertEqual(scene.camera.components[OrthographicCameraComponent.self]?.scale ?? -1, canonicalScale / 1.35, accuracy: 1e-6)
        XCTAssertNotEqual(scene.camera.position.x, canonicalPosition.x)

        scene.orbit(azimuthDelta: 0, elevationDelta: 0, zoomScale: 0.0001)
        XCTAssertEqual(scene.camera.components[OrthographicCameraComponent.self]?.scale ?? -1, canonicalScale / 0.75, accuracy: 1e-6)

        scene.orbit(azimuthDelta: 0, elevationDelta: 100)
        let upperPosition = scene.camera.position
        scene.orbit(azimuthDelta: 0, elevationDelta: 100)
        XCTAssertEqual(scene.camera.position, upperPosition)
        scene.orbit(azimuthDelta: 0, elevationDelta: -100)
        let lowerPosition = scene.camera.position
        scene.orbit(azimuthDelta: 0, elevationDelta: -100)
        XCTAssertEqual(scene.camera.position, lowerPosition)

        scene.update(
            pose: GripHandPose(posture: .halfCrimp, fingerConfiguration: nil),
            side: .right,
            viewportSize: CGSize(width: 200, height: 260),
            resetToken: 1
        )
        XCTAssertEqual(scene.camera.position.x, canonicalPosition.x, accuracy: 1e-3)
        XCTAssertEqual(scene.camera.position.y, canonicalPosition.y, accuracy: 1e-3)
        XCTAssertEqual(scene.camera.position.z, canonicalPosition.z, accuracy: 1e-3)
        XCTAssertEqual(scene.camera.components[OrthographicCameraComponent.self]?.scale ?? -1, canonicalScale, accuracy: 1e-6)
    }

    @MainActor
    func testSideChangeMirrorsHandAndRefitsCamera() {
        let scene = makeScene()
        let rightPosition = scene.camera.position
        let rightScale = scene.camera.components[OrthographicCameraComponent.self]!.scale

        scene.update(pose: GripHandPose(posture: .halfCrimp, fingerConfiguration: nil),
                     side: .left, viewportSize: CGSize(width: 200, height: 260), resetToken: 0)

        XCTAssertEqual(scene.hand.scale.x, -1)
        XCTAssertEqual(scene.camera.position.x, -rightPosition.x, accuracy: 1e-3)
        XCTAssertEqual(scene.camera.components[OrthographicCameraComponent.self]!.scale,
                       rightScale, accuracy: 1e-3)
    }

    @MainActor
    func testPoseAndViewportChangesRefitAuthoredBounds() {
        let scene = makeScene()
        let initialScale = scene.camera.components[OrthographicCameraComponent.self]!.scale

        scene.update(pose: GripHandPose(posture: .openHand, fingerConfiguration: nil),
                     side: .right, viewportSize: CGSize(width: 200, height: 260), resetToken: 0)
        let poseScale = scene.camera.components[OrthographicCameraComponent.self]!.scale
        XCTAssertNotEqual(poseScale, initialScale)

        scene.update(pose: GripHandPose(posture: .openHand, fingerConfiguration: nil),
                     side: .right, viewportSize: CGSize(width: 100, height: 260), resetToken: 0)
        let narrowScale = scene.camera.components[OrthographicCameraComponent.self]!.scale
        XCTAssertGreaterThan(narrowScale, poseScale)
    }

    @MainActor
    func testZeroViewportAndInvalidDeltasKeepCameraFiniteAndStable() {
        let scene = makeScene()
        let pose = GripHandPose(posture: .halfCrimp, fingerConfiguration: nil)
        scene.update(pose: pose, side: .right, viewportSize: .zero, resetToken: 0)
        XCTAssertTrue([scene.camera.position.x, scene.camera.position.y, scene.camera.position.z,
                       scene.camera.components[OrthographicCameraComponent.self]!.scale].allSatisfy(\.isFinite))

        let position = scene.camera.position
        let scale = scene.camera.components[OrthographicCameraComponent.self]!.scale
        scene.orbit(azimuthDelta: .nan, elevationDelta: 0)
        scene.orbit(azimuthDelta: 0, elevationDelta: .infinity)
        scene.orbit(azimuthDelta: 0, elevationDelta: 0, zoomScale: 0)
        scene.orbit(azimuthDelta: 0, elevationDelta: 0, zoomScale: .nan)
        XCTAssertEqual(scene.camera.position, position)
        XCTAssertEqual(scene.camera.components[OrthographicCameraComponent.self]!.scale, scale)

        scene.update(pose: pose, side: .right,
                     viewportSize: CGSize(width: 200, height: 260), resetToken: 0)
        scene.orbit(azimuthDelta: 0.2, elevationDelta: 0.1)
        XCTAssertTrue([scene.camera.position.x, scene.camera.position.y, scene.camera.position.z].allSatisfy(\.isFinite))
    }

    @MainActor
    func testPairSceneOwnsBothSurfacesAndAppliesRepeatedPoseUpdatesTogether() throws {
        let asset = try GripHandAsset.bundled.get()
        let scene = GripHandRealityPairScene(assetResult: .success(asset))
        let hands = try XCTUnwrap(FingerConfiguration(engagedFingers: [.index, .middle, .ring, .pinky]))
        let leftSurface = try XCTUnwrap(scene.leftSurface)
        let rightSurface = try XCTUnwrap(scene.rightSurface)

        scene.update(pose: GripHandPose(posture: .halfCrimp, fingerConfiguration: hands),
                     viewportSize: CGSize(width: 360, height: 260), resetToken: 0)
        XCTAssertTrue(scene.isAvailable)
        XCTAssertFalse(scene.root.children.isEmpty)
        XCTAssertTrue(scene.root.children.contains { $0 === scene.leftHand })
        XCTAssertTrue(scene.root.children.contains { $0 === scene.rightHand })
        XCTAssertFalse(leftSurface.modelEntity === rightSurface.modelEntity)
        XCTAssertEqual(leftSurface.appliedPose?.action(), "HalfCrimp")
        XCTAssertEqual(rightSurface.appliedPose?.action(), "HalfCrimp")
        let halfCrimpColors = try GripHandRealityMeshBuilder.vertexColors(
            asset: asset, action: GripHandPose(posture: .halfCrimp, fingerConfiguration: hands),
            selectedFingers: hands.engagedFingers
        )
        XCTAssertEqual(leftSurface.appliedVertexColors, halfCrimpColors)
        XCTAssertEqual(rightSurface.appliedVertexColors, halfCrimpColors)

        let openHand = GripHandPose(posture: .openHand,
                                    fingerConfiguration: FingerConfiguration(engagedFingers: [.index, .ring]))
        scene.update(pose: openHand,
                     viewportSize: CGSize(width: 360, height: 260), resetToken: 0)

        let openHandColors = try GripHandRealityMeshBuilder.vertexColors(
            asset: asset, action: openHand, selectedFingers: openHand.highlightedFingers
        )
        XCTAssertEqual(leftSurface.appliedPose, openHand)
        XCTAssertEqual(rightSurface.appliedPose, openHand)
        XCTAssertEqual(leftSurface.appliedVertexColors, openHandColors)
        XCTAssertEqual(rightSurface.appliedVertexColors, openHandColors)

        scene.update(pose: GripHandPose(posture: .halfCrimp, fingerConfiguration: hands),
                     viewportSize: CGSize(width: 360, height: 260), resetToken: 0)
        XCTAssertEqual(leftSurface.appliedPose?.action(), "HalfCrimp")
        XCTAssertEqual(rightSurface.appliedPose?.action(), "HalfCrimp")
        XCTAssertEqual(leftSurface.appliedVertexColors, halfCrimpColors)
        XCTAssertEqual(rightSurface.appliedVertexColors, halfCrimpColors)

        scene.update(pose: openHand, viewportSize: CGSize(width: 360, height: 260), resetToken: 0)
        XCTAssertEqual(leftSurface.appliedPose, openHand)
        XCTAssertEqual(rightSurface.appliedPose, openHand)
        XCTAssertEqual(leftSurface.appliedVertexColors, openHandColors)
        XCTAssertEqual(rightSurface.appliedVertexColors, openHandColors)
    }

    @MainActor
    func testPairSceneFramesUnionAndOrbitsOneCamera() throws {
        let scene = GripHandRealityPairScene()
        let directionalLights = scene.root.children.filter {
            $0.components[DirectionalLightComponent.self] != nil
        }
        XCTAssertEqual(directionalLights.count, 2,
                       "Both hands share one key light and one fill light")
        scene.update(pose: GripHandPose(posture: .halfCrimp, fingerConfiguration: nil),
                     viewportSize: CGSize(width: 420, height: 260), resetToken: 0)
        let startingCamera = scene.camera.position
        let startingScale = try XCTUnwrap(scene.camera.components[OrthographicCameraComponent.self]).scale

        scene.orbit(azimuthDelta: 0.35, elevationDelta: 0.1, zoomScale: 1.1)

        XCTAssertNotEqual(scene.camera.position, startingCamera)
        XCTAssertLessThan(scene.camera.components[OrthographicCameraComponent.self]!.scale, startingScale)
        XCTAssertTrue(scene.root.children.contains { $0 === scene.camera })
    }

    @MainActor
    func testPairModelViewForwardsSharedPoseAndViewport() {
        let scene = GripHandRealityPairScene()
        let view = GripHandPairModelView(
            posture: .halfCrimp,
            fingerConfiguration: FingerConfiguration(engagedFingers: [.middle, .ring]),
            resetToken: 3,
            scene: scene
        )
        let _: any View = view

        view.syncScene(in: CGSize(width: 380, height: 240))

        XCTAssertEqual(scene.currentPose?.action(), "HalfCrimp")
        XCTAssertEqual(scene.currentPose?.highlightedFingers, [.middle, .ring])
        XCTAssertEqual(scene.currentResetToken, 3)
        XCTAssertEqual(scene.currentViewportSize, CGSize(width: 380, height: 240))
    }

}
