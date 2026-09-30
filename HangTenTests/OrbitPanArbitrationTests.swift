import XCTest
import UIKit
@testable import HangTen

final class OrbitPanArbitrationTests: XCTestCase {
    func testActivationDistanceRequiresClearFingerTravel() {
        let origin = CGPoint(x: 40, y: 40)
        XCTAssertFalse(
            OrbitPanArbitration.hasClearedActivationDistance(
                from: origin,
                to: CGPoint(x: 44, y: 41)
            )
        )
        XCTAssertTrue(
            OrbitPanArbitration.hasClearedActivationDistance(
                from: origin,
                to: CGPoint(x: 51, y: 40)
            )
        )
    }

    func testShouldBeginPrefersHorizontalVelocityForOrbit() {
        XCTAssertTrue(
            OrbitPanArbitration.shouldBegin(
                translation: .zero,
                velocity: CGPoint(x: 120, y: 40)
            )
        )
        XCTAssertFalse(
            OrbitPanArbitration.shouldBegin(
                translation: .zero,
                velocity: CGPoint(x: 40, y: 120)
            )
        )
    }

    func testShouldBeginFallsBackToTranslationWhenVelocityIsZero() {
        XCTAssertTrue(
            OrbitPanArbitration.shouldBegin(
                translation: CGPoint(x: 12, y: 3),
                velocity: .zero
            )
        )
        XCTAssertFalse(
            OrbitPanArbitration.shouldBegin(
                translation: CGPoint(x: 3, y: 12),
                velocity: .zero
            )
        )
    }

    func testEqualAxesStillClaimHorizontalOrbit() {
        // Matching the prior carousel-style rule: ties go to orbit so a
        // purely diagonal nudge is not left ambiguous for the scroll view.
        XCTAssertTrue(
            OrbitPanArbitration.shouldBegin(
                translation: CGPoint(x: 10, y: 10),
                velocity: .zero
            )
        )
        XCTAssertTrue(
            OrbitPanArbitration.shouldBegin(
                translation: .zero,
                velocity: CGPoint(x: 50, y: 50)
            )
        )
    }
    @MainActor
    func testInteractiveMapAcceptsVerticalAndDiagonalOrbitWithoutChangingPreviewPolicy() {
        let view = UIView(frame: CGRect(x: 0, y: 0, width: 200, height: 200))
        let pan = StubOrbitPanGestureRecognizer()
        view.addGestureRecognizer(pan)
        let map = OrbitPanGestureDelegate(allowsAllDirections: true)
        let preview = OrbitPanGestureDelegate()
        for translation in [CGPoint(x: 0, y: 12), CGPoint(x: 8, y: 12), CGPoint(x: 12, y: 0)] {
            pan.stubTranslation = translation
            XCTAssertTrue(map.gestureRecognizerShouldBegin(pan))
        }
        pan.stubTranslation = CGPoint(x: 0, y: 12)
        XCTAssertFalse(preview.gestureRecognizerShouldBegin(pan))
    }

    @MainActor
    func testSimultaneousRecognitionIsLimitedToConfiguredMapPanAndPinch() {
        let view = UIView()
        let pan = UIPanGestureRecognizer()
        let pinch = UIPinchGestureRecognizer()
        let unrelated = UIPanGestureRecognizer()
        for recognizer in [pan, pinch, unrelated] as [UIGestureRecognizer] {
            view.addGestureRecognizer(recognizer)
        }
        let delegate = OrbitPanGestureDelegate(allowsAllDirections: true)
        delegate.simultaneousPan = pan
        delegate.simultaneousPinch = pinch
        XCTAssertTrue(delegate.gestureRecognizer(pan, shouldRecognizeSimultaneouslyWith: pinch))
        XCTAssertTrue(delegate.gestureRecognizer(pinch, shouldRecognizeSimultaneouslyWith: pan))
        XCTAssertFalse(delegate.gestureRecognizer(pan, shouldRecognizeSimultaneouslyWith: unrelated))
        XCTAssertFalse(delegate.gestureRecognizer(unrelated, shouldRecognizeSimultaneouslyWith: pinch))
        let otherView = UIView()
        otherView.addGestureRecognizer(pinch)
        XCTAssertFalse(delegate.gestureRecognizer(pan, shouldRecognizeSimultaneouslyWith: pinch))
    }

}

/// Supplies stable input without depending on UIKit's idle recognizer bookkeeping.
private final class StubOrbitPanGestureRecognizer: UIPanGestureRecognizer {
    var stubTranslation: CGPoint = .zero
    override func translation(in view: UIView?) -> CGPoint { stubTranslation }
    override func velocity(in view: UIView?) -> CGPoint { .zero }
}
