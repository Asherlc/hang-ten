import SceneKit
import XCTest
@testable import HangTen

/// Mirrors BoardModelTests's orbit coverage so both rotatable models share
/// the same bounded-turntable guarantees: a full spin returns to the start,
/// zoom stays clamped, and a reset restores the canonical framing.
final class GripHandOrbitTests: XCTestCase {
    private func makeInstalledCoordinator() -> (GripHandModelView.Coordinator, SCNView) {
        let coordinator = GripHandModelView.Coordinator()
        let view = SCNView(frame: CGRect(x: 0, y: 0, width: 200, height: 260))
        coordinator.install(in: view)
        coordinator.update(
            pose: GripHandPose(posture: .halfCrimp, fingerConfiguration: nil),
            side: .right,
            resetToken: 0
        )
        return (coordinator, view)
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

    func testFullAzimuthOrbitReturnsCameraToItsStartingPosition() throws {
        let (coordinator, view) = makeInstalledCoordinator()
        let camera = try XCTUnwrap(view.pointOfView)
        let startPosition = camera.simdPosition
        let startScale = try XCTUnwrap(camera.camera?.orthographicScale)

        let steps = 12
        for _ in 0..<steps {
            coordinator.orbit(azimuthDelta: .pi * 2 / Float(steps), elevationDelta: 0)
        }

        XCTAssertEqual(camera.simdPosition.x, startPosition.x, accuracy: 1e-3)
        XCTAssertEqual(camera.simdPosition.y, startPosition.y, accuracy: 1e-3)
        XCTAssertEqual(camera.simdPosition.z, startPosition.z, accuracy: 1e-3)
        XCTAssertEqual(camera.camera?.orthographicScale ?? -1, startScale, accuracy: 1e-6)
    }

    func testOrbitZoomIsBoundedAndResetRestoresCanonicalFraming() throws {
        let (coordinator, view) = makeInstalledCoordinator()
        let camera = try XCTUnwrap(view.pointOfView)
        let canonicalPosition = camera.simdPosition
        let canonicalScale = try XCTUnwrap(camera.camera?.orthographicScale)

        coordinator.orbit(azimuthDelta: 0.4, elevationDelta: 0.2, zoomScale: 100)
        XCTAssertEqual(camera.camera?.orthographicScale ?? -1, canonicalScale / 1.35, accuracy: 1e-6)
        XCTAssertNotEqual(camera.simdPosition.x, canonicalPosition.x)

        coordinator.orbit(azimuthDelta: 0, elevationDelta: 0, zoomScale: 0.0001)
        XCTAssertEqual(camera.camera?.orthographicScale ?? -1, canonicalScale / 0.75, accuracy: 1e-6)

        coordinator.update(
            pose: GripHandPose(posture: .halfCrimp, fingerConfiguration: nil),
            side: .right,
            resetToken: 1
        )
        XCTAssertEqual(camera.simdPosition.x, canonicalPosition.x, accuracy: 1e-3)
        XCTAssertEqual(camera.simdPosition.y, canonicalPosition.y, accuracy: 1e-3)
        XCTAssertEqual(camera.simdPosition.z, canonicalPosition.z, accuracy: 1e-3)
        XCTAssertEqual(camera.camera?.orthographicScale ?? -1, canonicalScale, accuracy: 1e-6)
    }

}
