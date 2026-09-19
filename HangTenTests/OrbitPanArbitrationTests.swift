import XCTest
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
}
