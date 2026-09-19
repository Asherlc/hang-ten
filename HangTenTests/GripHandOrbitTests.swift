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
