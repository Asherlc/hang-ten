import XCTest
import simd
@testable import HangTen

final class SuspendedBoardPresentationTests: XCTestCase {

    private let bounds = BoardModelBounds(
        minimum: [-1, -0.5, -0.2],
        maximum: [1, 0.5, 0.2]
    )

    private func pose(
        rotation: [Double] = [0, 0, 0, 1],
        translation: [Double] = [0, 0, 0],
        viewDirection: [Double] = [0, 0, 1],
        fitPadding: Double = 0.1
    ) -> BoardModelCanonicalPose {
        BoardModelCanonicalPose(
            rotation: rotation,
            translation: translation,
            camera: BoardModelCanonicalCamera(
                viewDirection: viewDirection,
                fitPadding: fitPadding
            )
        )
    }

    private func suspension(
        attachment: [Double] = [0, 0.4, 0],
        anchor: [Double] = [0.4, 2, 0],
        restLength: Double = 2,
        radius: Double = 0.01
    ) -> BoardModelSuspension {
        BoardModelSuspension(
            attachment: BoardModelAttachment(
                nodeID: "attachment",
                pointInModel: attachment,
                provenance: "test"
            ),
            anchor: BoardModelInvisibleAnchor(
                offsetFromBoardBounds: [0, 0, 0],
                visibility: "invisible",
                provenance: "test",
                position: anchor
            ),
            cord: BoardModelCord(
                restLength: restLength,
                radius: radius,
                material: "test-cord",
                provenance: "test"
            ),
            canonicalPoses: [:]
        )
    }

    func testIdentityPoseKeepsAttachmentAtModelPoint() throws {
        let result = try SuspendedBoardPresentation.solve(
            pose: pose(),
            suspension: suspension(),
            bounds: bounds
        )

        XCTAssertEqual(result.transformedAttachment.x, 0, accuracy: 1e-6)
        XCTAssertEqual(result.transformedAttachment.y, 0.4, accuracy: 1e-6)
        XCTAssertEqual(result.transformedAttachment.z, 0, accuracy: 1e-6)
        XCTAssertEqual(result.boardTransform.columns.3.x, 0, accuracy: 1e-6)
        XCTAssertEqual(result.boardTransform.columns.3.y, 0, accuracy: 1e-6)
        XCTAssertEqual(result.boardTransform.columns.3.z, 0, accuracy: 1e-6)
    }

    func testQuarterTurnPoseTransformsAttachment() throws {
        let result = try SuspendedBoardPresentation.solve(
            pose: pose(rotation: [0, sin(Double.pi / 4), 0, cos(Double.pi / 4)]),
            suspension: suspension(attachment: [1, 0, 0]),
            bounds: bounds
        )

        XCTAssertEqual(result.transformedAttachment.x, 0, accuracy: 1e-5)
        XCTAssertEqual(result.transformedAttachment.y, 0, accuracy: 1e-5)
        XCTAssertEqual(result.transformedAttachment.z, -1, accuracy: 1e-5)
    }

    func testExactTautCordIsAThirtyTwoSampleStraightSegment() throws {
        let solution = try SuspendedCordSolver.solve(
            start: SIMD3<Float>(0, 2, 0),
            end: SIMD3<Float>(0, 0, 0),
            restLength: 2
        )

        XCTAssertTrue(solution.isTaut)
        XCTAssertEqual(solution.samples.count, 32)
        XCTAssertEqual(solution.samples.first!, SIMD3<Float>(0, 2, 0))
        XCTAssertEqual(solution.samples.last!, SIMD3<Float>(0, 0, 0))
        XCTAssertTrue(solution.samples.dropFirst().dropLast().allSatisfy { $0.x == 0 && $0.z == 0 })
        XCTAssertEqual(solution.arcLength, 2, accuracy: 1e-6)
    }

    func testSlackCordHasExactEndpointsFiniteSamplesAndContinuousTangents() throws {
        let solution = try SuspendedCordSolver.solve(
            start: SIMD3<Float>(-0.5, 1, 0),
            end: SIMD3<Float>(0.5, 1, 0),
            restLength: 1.6
        )

        XCTAssertFalse(solution.isTaut)
        XCTAssertEqual(solution.samples.count, 32)
        XCTAssertEqual(solution.samples.first!, SIMD3<Float>(-0.5, 1, 0))
        XCTAssertEqual(solution.samples.last!, SIMD3<Float>(0.5, 1, 0))
        XCTAssertTrue(solution.samples.allSatisfy { $0.x.isFinite && $0.y.isFinite && $0.z.isFinite })
        XCTAssertEqual(solution.tangents.count, solution.samples.count)
        XCTAssertTrue(solution.tangents.allSatisfy { $0.x.isFinite && $0.y.isFinite && $0.z.isFinite })
        XCTAssertTrue(zip(solution.tangents, solution.tangents.dropFirst()).allSatisfy {
            simd_length($0.0 - $0.1) < 0.2
        })
        let measuredPolylineLength = zip(solution.samples, solution.samples.dropFirst()).reduce(Float.zero) {
            $0 + simd_length($1.1 - $1.0)
        }
        XCTAssertEqual(solution.polylineArcLength, measuredPolylineLength, accuracy: 1e-6)
        XCTAssertEqual(measuredPolylineLength, 1.6, accuracy: 0.01)
        XCTAssertLessThan(solution.samples.map(\.y).min()!, 1)
    }

    func testVeryShortTautCordDoesNotLookSelfIntersecting() throws {
        let length: Float = 8e-6
        let solution = try SuspendedCordSolver.solve(
            start: SIMD3<Float>(0, 0, 0),
            end: SIMD3<Float>(length, 0, 0),
            restLength: length
        )

        XCTAssertTrue(solution.isTaut)
        XCTAssertEqual(solution.samples.count, 32)
        XCTAssertEqual(solution.polylineArcLength, length, accuracy: 1e-9)
    }

    func testRepeatedSolveIsBitwiseDeterministic() throws {
        let first = try SuspendedCordSolver.solve(
            start: SIMD3<Float>(0, 1, 0),
            end: SIMD3<Float>(1, 0.5, 0),
            restLength: 1.7
        )
        let second = try SuspendedCordSolver.solve(
            start: SIMD3<Float>(0, 1, 0),
            end: SIMD3<Float>(1, 0.5, 0),
            restLength: 1.7
        )

        XCTAssertEqual(first.samples, second.samples)
        XCTAssertEqual(first.tangents, second.tangents)
        XCTAssertEqual(first.arcLength, second.arcLength)
    }

    func testShortCordIsRejected() {
        XCTAssertThrowsError(try SuspendedCordSolver.solve(
            start: SIMD3<Float>(0, 1, 0),
            end: SIMD3<Float>(1, 1, 0),
            restLength: 0.99
        )) { error in
            XCTAssertEqual(error as? SuspendedPresentationError, .cordTooShort)
        }
    }

    func testNonUnitPoseIsRejected() {
        XCTAssertThrowsError(try SuspendedBoardPresentation.solve(
            pose: pose(rotation: [0, 0, 0, 2]),
            suspension: suspension(),
            bounds: bounds
        )) { error in
            XCTAssertEqual(error as? SuspendedPresentationError, .nonUnitPose)
        }
    }

    func testZeroHorizontalSlackIsRejected() {
        XCTAssertThrowsError(try SuspendedCordSolver.solve(
            start: SIMD3<Float>(0, 1, 0),
            end: SIMD3<Float>(0, 0, 0),
            restLength: 1.1
        )) { error in
            XCTAssertEqual(error as? SuspendedPresentationError, .zeroHorizontalSlack)
        }
    }

    func testSelfIntersectingCenterlineIsRejectedByValidationHook() {
        let crossing = [
            SIMD3<Float>(0, 0, 0),
            SIMD3<Float>(1, 1, 0),
            SIMD3<Float>(0, 1, 0),
            SIMD3<Float>(1, 0, 0),
        ]
        XCTAssertTrue(SuspendedCordSolver.hasSelfIntersection(crossing))
        XCTAssertThrowsError(try SuspendedCordSolver.validateNoSelfIntersection(crossing)) { error in
            XCTAssertEqual(error as? SuspendedPresentationError, .selfIntersection)
        }
    }

    func testPresentationExposesClearanceAndFramingThatContainCord() throws {
        let result = try SuspendedBoardPresentation.solve(
            pose: pose(),
            suspension: suspension(restLength: 2.1),
            bounds: bounds
        )

        XCTAssertEqual(result.tubeRadius, 0.01, accuracy: 1e-6)
        XCTAssertGreaterThan(result.requiredClearance, result.tubeRadius)
        XCTAssertTrue(result.cameraFraming.contains(result.fixedAnchor))
        XCTAssertTrue(result.cameraFraming.contains(result.transformedAttachment))
        XCTAssertTrue(result.centerlineSamples.allSatisfy { result.cameraFraming.contains($0) })
    }

    func testEachCanonicalPoseFramesItsAttachmentAndCord() throws {
        let poses: [BoardModelCanonicalPose] = [
            pose(),
            pose(rotation: [0, sin(Double.pi / 4), 0, cos(Double.pi / 4)], translation: [0.2, 0, 0]),
            pose(rotation: [sin(Double.pi / 4), 0, 0, cos(Double.pi / 4)], translation: [0, -0.1, 0.1]),
            pose(rotation: [0, 0, sin(Double.pi / 4), cos(Double.pi / 4)], translation: [-0.2, 0, 0]),
        ]

        for canonicalPose in poses {
            let result = try SuspendedBoardPresentation.solve(
                pose: canonicalPose,
                suspension: suspension(restLength: 2.5),
                bounds: bounds
            )
            XCTAssertTrue(result.cameraFraming.contains(result.transformedAttachment))
            XCTAssertTrue(result.cameraFraming.contains(result.fixedAnchor))
            XCTAssertTrue(result.centerlineSamples.allSatisfy { result.cameraFraming.contains($0) })
        }
    }
}
