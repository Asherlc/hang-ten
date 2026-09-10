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

    private func twoBranchSuspension(
        left: [[Double]] = [[-0.6, 0.4, 0], [-0.4, 0.4, 0]],
        right: [[Double]] = [[0.4, 0.4, 0], [0.6, 0.4, 0]],
        anchor: [Double] = [0, 2, 0],
        restLength: Double = 4,
        radius: Double = 0.01
    ) -> BoardModelTwoBranchSuspension {
        func passage(_ id: String, _ point: [Double]) -> BoardModelPassage {
            BoardModelPassage(id: id, nodeID: id, pointInModel: point, provenance: "test")
        }
        return BoardModelTwoBranchSuspension(
            passages: BoardModelPassagePairs(
                left: [passage("left-0", left[0]), passage("left-1", left[1])],
                right: [passage("right-0", right[0]), passage("right-1", right[1])]
            ),
            branches: [
                BoardModelCordBranch(id: "left", passageIDs: ["left-0", "left-1"], restLength: restLength, radius: radius, material: "test-cord", provenance: "test"),
                BoardModelCordBranch(id: "right", passageIDs: ["right-0", "right-1"], restLength: restLength, radius: radius, material: "test-cord", provenance: "test"),
            ],
            anchor: BoardModelInvisibleAnchor(offsetFromBoardBounds: [0, 0, 0], visibility: "invisible", provenance: "test", position: anchor),
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
            suspension: suspension(attachment: [1, 0, 0], restLength: 2.5),
            bounds: bounds
        )

        XCTAssertEqual(result.transformedAttachment.x, 0, accuracy: 1e-5)
        XCTAssertEqual(result.transformedAttachment.y, 0, accuracy: 1e-5)
        XCTAssertEqual(result.transformedAttachment.z, -1, accuracy: 1e-5)
    }

    func testQuarterTurnRejectsItsActuallyShortCord() {
        XCTAssertThrowsError(try SuspendedBoardPresentation.solve(
            pose: pose(rotation: [0, sin(Double.pi / 4), 0, cos(Double.pi / 4)]),
            suspension: suspension(attachment: [1, 0, 0], restLength: 2),
            bounds: bounds
        )) { error in
            XCTAssertEqual(error as? SuspendedPresentationError, .cordTooShort)
        }
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

    func testCrossPairedRepeatedEndpointIsRejectedByValidationHook() {
        let a = SIMD3<Float>(0, 0, 0)
        let repeatedEndpoint = [
            a,
            SIMD3<Float>(1, 0, 0),
            SIMD3<Float>(1, 1, 0),
            a,
        ]

        XCTAssertTrue(SuspendedCordSolver.hasSelfIntersection(repeatedEndpoint))
        XCTAssertThrowsError(try SuspendedCordSolver.validateNoSelfIntersection(repeatedEndpoint)) { error in
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

    func testTwoBranchIdentityTransformsAllPassagesAndSharesFixedAnchor() throws {
        let result = try SuspendedBoardPresentation.solve(
            pose: pose(),
            suspension: twoBranchSuspension(),
            bounds: bounds
        )

        XCTAssertEqual(result.branches.count, 2)
        XCTAssertEqual(result.fixedAnchor, SIMD3<Float>(0, 2, 0))
        XCTAssertEqual(result.branches[0].passageIDs, ["left-0", "left-1"])
        XCTAssertEqual(result.branches[1].passageIDs, ["right-0", "right-1"])
        XCTAssertEqual(result.branches[0].spans.count, 2)
        XCTAssertEqual(result.branches[1].spans.count, 2)
        XCTAssertEqual(result.branches[0].spans[0].first!, SIMD3<Float>(-0.6, 0.4, 0))
        XCTAssertEqual(result.branches[0].spans[1].first!, SIMD3<Float>(-0.4, 0.4, 0))
        XCTAssertEqual(result.branches[1].spans[0].first!, result.fixedAnchor)
        XCTAssertEqual(result.branches[1].spans[0].last!, SIMD3<Float>(0.4, 0.4, 0))
        XCTAssertEqual(result.branches[0].centerlineSamples.first!, result.fixedAnchor)
        XCTAssertEqual(result.branches[0].centerlineSamples.last!, result.fixedAnchor)
        XCTAssertEqual(result.branches[1].centerlineSamples.first!, result.fixedAnchor)
        XCTAssertEqual(result.branches[1].centerlineSamples.last!, result.fixedAnchor)
    }

    func testTwoBranchQuarterTurnTransformsAllFourPassagesButNotAnchor() throws {
        let result = try SuspendedBoardPresentation.solve(
            pose: pose(rotation: [0, sin(Double.pi / 4), 0, cos(Double.pi / 4)]),
            suspension: twoBranchSuspension(),
            bounds: bounds
        )

        XCTAssertEqual(result.fixedAnchor, SIMD3<Float>(0, 2, 0))
        XCTAssertEqual(result.branches[0].spans[0].first!.x, 0, accuracy: 1e-5)
        XCTAssertEqual(result.branches[0].spans[0].first!.z, 0.6, accuracy: 1e-5)
        XCTAssertEqual(result.branches[0].spans[1].first!.x, 0, accuracy: 1e-5)
        XCTAssertEqual(result.branches[0].spans[1].first!.z, 0.4, accuracy: 1e-5)
        XCTAssertEqual(result.branches[1].spans[0].last!.z, -0.4, accuracy: 1e-5)
        XCTAssertEqual(result.branches[1].spans[1].first!.z, -0.6, accuracy: 1e-5)
    }

    func testTwoBranchSolveIsBitwiseDeterministicAndPreservesDeclaredOrder() throws {
        let first = try SuspendedBoardPresentation.solve(
            pose: pose(translation: [0.2, -0.1, 0.3]),
            suspension: twoBranchSuspension(restLength: 4.2),
            bounds: bounds
        )
        let second = try SuspendedBoardPresentation.solve(
            pose: pose(translation: [0.2, -0.1, 0.3]),
            suspension: twoBranchSuspension(restLength: 4.2),
            bounds: bounds
        )

        XCTAssertEqual(first.branches.map(\.id), ["left", "right"])
        XCTAssertEqual(first.branches.map(\.passageIDs), [["left-0", "left-1"], ["right-0", "right-1"]])
        XCTAssertEqual(first.branches.map(\.centerlineSamples), second.branches.map(\.centerlineSamples))
        XCTAssertEqual(first.branches.map(\.tangentSamples), second.branches.map(\.tangentSamples))
        XCTAssertEqual(first.branches.map(\.arcLength), second.branches.map(\.arcLength))
    }

    func testTwoBranchPreservesInteriorPassageSpanAndContinuousJoins() throws {
        let result = try SuspendedBoardPresentation.solve(
            pose: pose(),
            suspension: twoBranchSuspension(restLength: 4.2),
            bounds: bounds
        )

        for branch in result.branches {
            XCTAssertEqual(branch.centerlineSamples.first!, result.fixedAnchor)
            XCTAssertEqual(branch.centerlineSamples.last!, result.fixedAnchor)
            XCTAssertEqual(branch.spans[0].last!, branch.centerlineSamples[31])
            let passageDistance = simd_length(branch.centerlineSamples[32] - branch.centerlineSamples[31])
            XCTAssertEqual(passageDistance, branch.spans[0].last!.x < 0 ? 0.2 : 0.2, accuracy: 1e-6)
            XCTAssertEqual(branch.arcLength, 4.2, accuracy: 1e-3)
        }
    }

    func testTwoBranchRejectsShortRestLength() {
        XCTAssertThrowsError(try SuspendedBoardPresentation.solve(
            pose: pose(),
            suspension: twoBranchSuspension(restLength: 1),
            bounds: bounds
        )) { error in
            XCTAssertEqual(error as? SuspendedPresentationError, .cordTooShort)
        }
    }

    func testTwoBranchRejectsZeroHorizontalSlackAndNonfiniteInputs() {
        XCTAssertThrowsError(try SuspendedBoardPresentation.solve(
            pose: pose(),
            suspension: twoBranchSuspension(
                left: [[0, 0.4, 0], [0.1, 0.4, 0]],
                right: [[0.4, 0.4, 0], [0.6, 0.4, 0]],
                anchor: [0, 2, 0],
                restLength: 4
            ),
            bounds: bounds
        )) { error in
            XCTAssertEqual(error as? SuspendedPresentationError, .zeroHorizontalSlack)
        }

        XCTAssertThrowsError(try SuspendedBoardPresentation.solve(
            pose: pose(),
            suspension: twoBranchSuspension(left: [[.infinity, 0.4, 0], [-0.4, 0.4, 0]]),
            bounds: bounds
        )) { error in
            XCTAssertEqual(error as? SuspendedPresentationError, .invalidSuspension)
        }
    }

    func testTwoBranchCameraIncludesBoardCornersPassagesBranchesAndAnchor() throws {
        let result = try SuspendedBoardPresentation.solve(
            pose: pose(rotation: [0, sin(Double.pi / 4), 0, cos(Double.pi / 4)]),
            suspension: twoBranchSuspension(restLength: 4.2),
            bounds: bounds
        )

        XCTAssertEqual(result.cameraFraming.includedPoints.count, 8 + 1 + 4 + result.branches.reduce(0) { $0 + $1.centerlineSamples.count })
        XCTAssertTrue(result.cameraFraming.contains(result.fixedAnchor))
        for branch in result.branches {
            XCTAssertTrue(branch.centerlineSamples.allSatisfy { result.cameraFraming.contains($0) })
            XCTAssertTrue(branch.spans.flatMap { $0 }.allSatisfy { result.cameraFraming.contains($0) })
        }
        XCTAssertEqual(result.tubeRadius, 0.01, accuracy: 1e-6)
        XCTAssertEqual(result.requiredClearance, 0.011, accuracy: 1e-6)
    }

    func testTwoBranchRejectsSelfIntersectionAcrossInteriorRouteAndFreeSpan() {
        let crossingBounds = BoardModelBounds(
            minimum: [-1.2, 0, -0.2],
            maximum: [1.2, 2.2, 0.2]
        )
        XCTAssertThrowsError(try SuspendedBoardPresentation.solve(
            pose: pose(),
            suspension: twoBranchSuspension(
                left: [[-1, 0, 0], [-0.9, 0.9, 0]],
                restLength: 5.5628735
            ),
            bounds: crossingBounds
        )) { error in
            XCTAssertEqual(error as? SuspendedPresentationError, .selfIntersection)
        }
    }

    func testTwoBranchExactTautRouteReturnsStraightThirtyTwoSampleFreeSpans() throws {
        let anchor = SIMD3<Float>(0, 2, 0)
        let leftFirst = SIMD3<Float>(-0.6, 0.4, 0)
        let leftSecond = SIMD3<Float>(-0.4, 0.4, 0)
        let routeLength = simd_length(anchor - leftFirst)
            + simd_length(leftSecond - leftFirst)
            + simd_length(anchor - leftSecond)
        let result = try SuspendedBoardPresentation.solve(
            pose: pose(),
            suspension: twoBranchSuspension(restLength: Double(routeLength)),
            bounds: bounds
        )

        for branch in result.branches {
            XCTAssertEqual(branch.spans.count, 2)
            XCTAssertTrue(branch.spans.allSatisfy { $0.count == SuspendedCordSolver.sampleCount })
            XCTAssertEqual(branch.arcLength, routeLength, accuracy: 1e-5)
            for span in branch.spans {
                let start = span.first!
                let end = span.last!
                let direction = end - start
                for (index, sample) in span.enumerated() {
                    let t = Float(index) / Float(SuspendedCordSolver.sampleCount - 1)
                    XCTAssertEqual(sample, start + direction * t)
                    XCTAssertLessThan(simd_length(simd_cross(sample - start, direction)), 1e-4)
                }
            }
            let expectedCenterline = branch.spans[0]
                + [branch.spans[1].first!]
                + Array(branch.spans[1].dropFirst())
            XCTAssertEqual(branch.centerlineSamples, expectedCenterline)
            XCTAssertEqual(branch.centerlineSamples.first!, anchor)
            XCTAssertEqual(branch.centerlineSamples[31], branch.spans[0].last!)
            XCTAssertEqual(branch.centerlineSamples[32], branch.spans[1].first!)
            XCTAssertEqual(branch.centerlineSamples.last!, anchor)
            let measuredLength = zip(branch.centerlineSamples, branch.centerlineSamples.dropFirst()).reduce(Float.zero) {
                $0 + simd_length($1.1 - $1.0)
            }
            XCTAssertEqual(measuredLength, routeLength, accuracy: 1e-5)
        }
    }

    func testClosedBranchPolicyRejectsInitialAndFinalSegmentContactAwayFromAnchor() {
        let anchor = SIMD3<Float>(0, 0, 0)
        let samples = [
            anchor,
            SIMD3<Float>(2, 0, 0),
            SIMD3<Float>(2, 1, 0),
            SIMD3<Float>(2, 2, 0),
            SIMD3<Float>(1, 1, 0),
            SIMD3<Float>(1, 0, 0),
            anchor,
        ]

        XCTAssertThrowsError(try SuspendedCordSolver.validateNoSelfIntersectionAllowingClosedEndpoint(samples)) { error in
            XCTAssertEqual(error as? SuspendedPresentationError, .selfIntersection)
        }
    }

    func testClosedBranchPolicyRejectsNonClosureEndpointToInteriorContact() {
        let samples = [
            SIMD3<Float>(0, 0, 0),
            SIMD3<Float>(0, 2, 0),
            SIMD3<Float>(2, 2, 0),
            SIMD3<Float>(3, 3, 0),
            SIMD3<Float>(1, 1, 0),
            SIMD3<Float>(0, 0, 0),
        ]

        XCTAssertThrowsError(try SuspendedCordSolver.validateNoSelfIntersectionAllowingClosedEndpoint(samples)) { error in
            XCTAssertEqual(error as? SuspendedPresentationError, .selfIntersection)
        }
    }
}
