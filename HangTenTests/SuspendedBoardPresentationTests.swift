import XCTest
import SceneKit
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

    private func singleProfile(
        attachment: [Double] = [0, 0.4, 0],
        anchor: [Double] = [0.4, 2, 0],
        restLength: Double = 2,
        radius: Double = 0.01
    ) -> BoardModelSingleCordSuspension {
        BoardModelSingleCordSuspension(
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
        left: [[Double]] = [[-0.6, 0.4, -0.05], [-0.4, 0.4, 0.05]],
        right: [[Double]] = [[0.4, 0.4, -0.05], [0.6, 0.4, 0.05]],
        anchor: [Double] = [0, 2, 0],
        restLength: Double = 4,
        radius: Double = 0.01,
        canonicalPoses: [String: BoardModelCanonicalPose] = [:]
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
            canonicalPoses: canonicalPoses
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

    // This catches the extracted profile solver drifting from the established
    // facade contract: exact endpoints, sample count, tangents, arc lengths,
    // transform, and framing all have to continue describing the same cord.
    func testSingleProfileSolverCharacterizesSlackCordAndFacadeCompatibility() throws {
        let profile = singleProfile()
        let solved = try SuspensionProfileSolver.solveSingle(
            pose: pose(),
            profile: profile,
            bounds: bounds
        )
        let facade = try SuspendedBoardPresentation.solve(
            pose: pose(),
            suspension: .singleCord(profile),
            bounds: bounds
        )

        XCTAssertEqual(solved.cord.samples.count, 32)
        XCTAssertEqual(solved.cord.samples.first, SIMD3<Float>(0.4, 2, 0))
        XCTAssertEqual(solved.cord.samples.last, SIMD3<Float>(0, 0.4, 0))
        XCTAssertFalse(solved.cord.isTaut)
        XCTAssertEqual(solved.cord.arcLength, 2, accuracy: 1e-6)
        XCTAssertEqual(solved.cord.polylineArcLength, 2, accuracy: 0.01)
        XCTAssertEqual(solved.cord.tangents.count, solved.cord.samples.count)
        XCTAssertTrue(solved.cord.tangents.allSatisfy { simd_length($0) > 0.999 && simd_length($0) < 1.001 })
        XCTAssertEqual(solved.boardTransform.columns.3, SIMD4<Float>(0, 0, 0, 1))
        XCTAssertTrue(solved.cameraFraming.contains(solved.fixedAnchor))
        XCTAssertTrue(solved.cameraFraming.contains(solved.transformedAttachment))
        XCTAssertTrue(solved.cord.samples.allSatisfy { solved.cameraFraming.contains($0) })
        XCTAssertEqual(facade.centerlineSamples, solved.cord.samples)
        XCTAssertEqual(facade.tangentSamples, solved.cord.tangents)
        XCTAssertEqual(facade.cordArcLength, solved.cord.arcLength)
    }

    // Literal values captured from the pre-extraction solver at f29f1255.
    // They intentionally do not use the compatibility facade or any solver
    // helper to derive expectations, so changes to catenary arithmetic,
    // sampling, or framing policy remain observable.
    func testSingleProfileSolverMatchesPreExtractionNumericalBaseline() throws {
        let solved = try SuspensionProfileSolver.solveSingle(
            pose: pose(),
            profile: singleProfile(),
            bounds: bounds
        )

        let expectedSamples: [(index: Int, point: SIMD3<Float>)] = [
            (1, SIMD3<Float>(0.3870968, 1.6978989, 0)),
            (8, SIMD3<Float>(0.2967742, 0.6134734, 0)),
            (16, SIMD3<Float>(0.1935484, 0.30244565, 0)),
            (24, SIMD3<Float>(0.090322584, 0.27111173, 0)),
            (30, SIMD3<Float>(0.012903243, 0.3676641, 0))
        ]
        let expectedTangents: [(index: Int, tangent: SIMD3<Float>)] = [
            (1, SIMD3<Float>(-0.046825305, -0.9989031, 0)),
            (8, SIMD3<Float>(-0.16762841, -0.9858503, 0)),
            (16, SIMD3<Float>(-0.6445774, -0.76453906, 0)),
            (24, SIMD3<Float>(-0.9035824, 0.42841431, 0)),
            (30, SIMD3<Float>(-0.40371457, 0.914885, 0))
        ]
        for expected in expectedSamples {
            XCTAssertEqual(solved.cord.samples[expected.index].x, expected.point.x, accuracy: 1e-6)
            XCTAssertEqual(solved.cord.samples[expected.index].y, expected.point.y, accuracy: 1e-6)
            XCTAssertEqual(solved.cord.samples[expected.index].z, expected.point.z, accuracy: 1e-6)
        }
        for expected in expectedTangents {
            XCTAssertEqual(solved.cord.tangents[expected.index].x, expected.tangent.x, accuracy: 1e-6)
            XCTAssertEqual(solved.cord.tangents[expected.index].y, expected.tangent.y, accuracy: 1e-6)
            XCTAssertEqual(solved.cord.tangents[expected.index].z, expected.tangent.z, accuracy: 1e-6)
        }
        XCTAssertEqual(solved.cord.polylineArcLength, 1.9997214, accuracy: 1e-6)
        XCTAssertEqual(solved.cameraFraming.target, SIMD3<Float>(0, 0.75, 0))
        XCTAssertEqual(solved.cameraFraming.right, SIMD3<Float>(-1, 0, 0))
        XCTAssertEqual(solved.cameraFraming.up, SIMD3<Float>(0, 1, 0))
        XCTAssertEqual(solved.cameraFraming.width, 2, accuracy: 1e-6)
        XCTAssertEqual(solved.cameraFraming.height, 2.5, accuracy: 1e-6)
        XCTAssertEqual(solved.cameraFraming.depth, 0.4, accuracy: 1e-6)
        XCTAssertEqual(solved.cameraFraming.distance, 3, accuracy: 1e-6)
        XCTAssertEqual(solved.cameraFraming.includedPoints.count, 42)
    }

    func testSingleProfileSolverCharacterizesTautSlackAndInvalidInputs() throws {
        let taut = try SuspensionProfileSolver.solveSingle(
            pose: pose(),
            profile: singleProfile(attachment: [0, 0, 0], anchor: [0, 2, 0], restLength: 2),
            bounds: bounds
        )
        XCTAssertTrue(taut.cord.isTaut)
        XCTAssertEqual(taut.cord.samples.count, 32)
        XCTAssertEqual(taut.cord.samples.first, SIMD3<Float>(0, 2, 0))
        XCTAssertEqual(taut.cord.samples.last, SIMD3<Float>(0, 0, 0))

        XCTAssertThrowsError(try SuspensionProfileSolver.solveSingle(
            pose: pose(),
            profile: singleProfile(attachment: [.infinity, 0, 0]),
            bounds: bounds
        )) { error in
            XCTAssertEqual(error as? SuspendedPresentationError, .invalidSuspension)
        }
        XCTAssertThrowsError(try SuspensionProfileSolver.solveSingle(
            pose: pose(),
            profile: singleProfile(attachment: [0, 0, 0], anchor: [0, 2, 0], restLength: 2.1),
            bounds: bounds
        )) { error in
            XCTAssertEqual(error as? SuspendedPresentationError, .zeroHorizontalSlack)
        }
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
        XCTAssertEqual(result.branches[0].spans[0].first!, result.fixedAnchor)
        XCTAssertEqual(result.branches[0].spans[0].last!, SIMD3<Float>(-0.6, 0.4, -0.05))
        XCTAssertEqual(result.branches[0].spans[1].first!, SIMD3<Float>(-0.4, 0.4, 0.05))
        XCTAssertEqual(result.branches[0].spans[1].last!, result.fixedAnchor)
        XCTAssertEqual(result.branches[1].spans[0].first!, result.fixedAnchor)
        XCTAssertEqual(result.branches[1].spans[0].last!, SIMD3<Float>(0.4, 0.4, -0.05))
        XCTAssertEqual(result.branches[1].spans[1].first!, SIMD3<Float>(0.6, 0.4, 0.05))
        XCTAssertEqual(result.branches[1].spans[1].last!, result.fixedAnchor)
        XCTAssertEqual(result.branches[0].centerlineSamples.first!, result.fixedAnchor)
        XCTAssertEqual(result.branches[0].centerlineSamples.last!, result.fixedAnchor)
        XCTAssertEqual(result.branches[1].centerlineSamples.first!, result.fixedAnchor)
        XCTAssertEqual(result.branches[1].centerlineSamples.last!, result.fixedAnchor)
    }

    @MainActor
    func testSceneRuntimeDispatchesTwoBranchSuspensionToTwoBranchSolver() throws {
        let suspension = twoBranchSuspension(restLength: 4.2)
        let solved = try BoardModelScene.solveSuspension(
            pose: pose(),
            suspension: .twoBranchCord(suspension),
            bounds: bounds
        )

        guard case .twoBranch(let result) = solved else {
            return XCTFail("scene runtime must preserve the two-branch solved result")
        }
        XCTAssertEqual(result.branches.map(\.id), ["left", "right"])
        XCTAssertEqual(result.cameraFraming.includedPoints.count, 8 + 1 + 4 + 128)
    }

    @MainActor
    func testSceneSelectionRendersBothBranchesAndRejectsUnrelatedInteriorContact() throws {
        let selectedPose = pose()
        let suspension = twoBranchSuspension(
            restLength: 4.2,
            canonicalPoses: ["primary": selectedPose]
        )
        let solved = try SuspendedBoardPresentation.solve(
            pose: selectedPose,
            suspension: suspension,
            bounds: bounds
        )
        let descriptor = sceneDescriptor(for: suspension)

        let clearScene = try XCTUnwrap(BoardModelScene(
            source: modelScene(descriptor: descriptor),
            descriptor: descriptor,
            display: sceneDisplay(),
            suspension: .twoBranchCord(suspension)
        ))
        XCTAssertTrue(clearScene.select(positionID: "primary"))
        let renderedSegments = try XCTUnwrap(clearScene.transientCordNode?.childNodes)
        XCTAssertTrue(renderedSegments.contains { $0.name?.contains("branch.0.segment") == true })
        XCTAssertTrue(renderedSegments.contains { $0.name?.contains("branch.1.segment") == true })

        let interiorPoint = solved.branches[0].centerlineSamples[10]
        let blockedScene = try XCTUnwrap(BoardModelScene(
            source: modelScene(descriptor: descriptor, bodyPosition: interiorPoint),
            descriptor: descriptor,
            display: sceneDisplay(),
            suspension: .twoBranchCord(suspension)
        ))
        XCTAssertFalse(blockedScene.select(positionID: "primary"))
        XCTAssertTrue(blockedScene.isUnavailable)
        XCTAssertNil(blockedScene.transientCordNode)
    }

    func testTwoBranchQuarterTurnTransformsAllFourPassagesButNotAnchor() throws {
        let result = try SuspendedBoardPresentation.solve(
            pose: pose(rotation: [0, sin(Double.pi / 4), 0, cos(Double.pi / 4)]),
            suspension: twoBranchSuspension(),
            bounds: bounds
        )

        XCTAssertEqual(result.fixedAnchor, SIMD3<Float>(0, 2, 0))
        XCTAssertEqual(result.branches[0].spans[0].first!, result.fixedAnchor)
        XCTAssertEqual(result.branches[0].spans[0].last!.x, -0.05, accuracy: 1e-5)
        XCTAssertEqual(result.branches[0].spans[0].last!.z, 0.6, accuracy: 1e-5)
        XCTAssertEqual(result.branches[0].spans[1].first!.x, 0.05, accuracy: 1e-5)
        XCTAssertEqual(result.branches[0].spans[1].first!.z, 0.4, accuracy: 1e-5)
        XCTAssertEqual(result.branches[0].spans[1].last!, result.fixedAnchor)
        XCTAssertEqual(result.branches[1].spans[0].first!, result.fixedAnchor)
        XCTAssertEqual(result.branches[1].spans[0].last!.x, -0.05, accuracy: 1e-5)
        XCTAssertEqual(result.branches[1].spans[0].last!.z, -0.4, accuracy: 1e-5)
        XCTAssertEqual(result.branches[1].spans[1].first!.x, 0.05, accuracy: 1e-5)
        XCTAssertEqual(result.branches[1].spans[1].first!.z, -0.6, accuracy: 1e-5)
        XCTAssertEqual(result.branches[1].spans[1].last!, result.fixedAnchor)
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
            XCTAssertEqual(passageDistance, sqrt(0.05), accuracy: 1e-6)
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
                right: [[0.4, 0.4, 0], [0.6, 0.4, 0]],
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
            suspension: twoBranchSuspension(
                left: [[-0.6, 0.4, 0], [-0.4, 0.4, 0]],
                right: [[0.4, 0.4, 0], [0.6, 0.4, 0]],
                restLength: Double(routeLength)
            ),
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
                    let expected = index == SuspendedCordSolver.sampleCount - 1
                        ? end
                        : start + direction * t
                    XCTAssertEqual(sample, expected)
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

    func testSelfIntersectionRejectsEndpointTouchNearAnotherSegmentEndpoint() {
        let samples = [
            SIMD3<Float>(0, 0, 0),
            SIMD3<Float>(1, 0, 0),
            SIMD3<Float>(1, 1, 0),
            SIMD3<Float>(0.00005, 1, 0),
            SIMD3<Float>(0.00005, 0, 0),
        ]

        XCTAssertTrue(SuspendedCordSolver.hasSelfIntersection(samples))
        XCTAssertThrowsError(try SuspendedCordSolver.validateNoSelfIntersection(samples)) { error in
            XCTAssertEqual(error as? SuspendedPresentationError, .selfIntersection)
        }
    }

    func testClosedBranchPolicyRejectsEndpointTouchNearAnotherSegmentEndpoint() {
        let samples = [
            SIMD3<Float>(0, 0, 0),
            SIMD3<Float>(1, 0, 0),
            SIMD3<Float>(1, 1, 0),
            SIMD3<Float>(0.00005, 1, 0),
            SIMD3<Float>(0.00005, 0, 0),
            SIMD3<Float>(0, 2, 0),
            SIMD3<Float>(0, 0, 0),
        ]

        XCTAssertThrowsError(try SuspendedCordSolver.validateNoSelfIntersectionAllowingClosedEndpoint(samples)) { error in
            XCTAssertEqual(error as? SuspendedPresentationError, .selfIntersection)
        }
    }

    @MainActor
    func testSceneSelectionRejectsEachMissingOrNonAttachmentPassageBinding() throws {
        let suspension = twoBranchSuspension(
            restLength: 4.2,
            canonicalPoses: ["primary": pose()]
        )
        for passage in suspension.passages.left + suspension.passages.right {
            for omit in [true, false] {
                let descriptor = sceneDescriptor(
                    for: suspension,
                    omittedNodeID: omit ? passage.nodeID : nil,
                    bodyNodeID: omit ? nil : passage.nodeID
                )
                let model = try XCTUnwrap(BoardModelScene(
                    source: modelScene(descriptor: descriptor),
                    descriptor: descriptor,
                    display: sceneDisplay(),
                    suspension: .twoBranchCord(suspension)
                ))
                XCTAssertFalse(model.select(positionID: "primary"), "\(passage.nodeID), omitted: \(omit)")
                XCTAssertTrue(model.isUnavailable)
                XCTAssertNil(model.activePositionID)
                XCTAssertNil(model.transientCordNode)
            }
        }
    }

    private func sceneDescriptor(
        for suspension: BoardModelTwoBranchSuspension,
        omittedNodeID: String? = nil,
        bodyNodeID: String? = nil
    ) -> BoardModelDescriptor {
        let passageNodes = (suspension.passages.left + suspension.passages.right)
            .filter { $0.nodeID != omittedNodeID }
            .map {
            BoardModelNodeDescriptor(nodeID: $0.nodeID, role: $0.nodeID == bodyNodeID ? .body : .attachment, holdID: nil)
        }
        return BoardModelDescriptor(
            schemaVersion: 1,
            coordinateFrame: "hang-ten-board-v1",
            modelSHA256: String(repeating: "0", count: 64),
            modelBounds: bounds,
            nodes: [
                BoardModelNodeDescriptor(nodeID: "Body", role: .body, holdID: nil),
                BoardModelNodeDescriptor(nodeID: "Hold", role: .hold, holdID: "hold"),
            ] + passageNodes,
            holds: [
                "hold": BoardModelHoldDescriptor(
                    nodeIDs: ["Hold"],
                    facePlaneAABB: BoardModelFacePlaneAABB(minimum: [0, 0], maximum: [1, 1]),
                    center: [0.5, 0.5]
                )
            ]
        )
    }

    private func sceneDisplay() -> BoardModelDisplay {
        BoardModelDisplay(camera: BoardModelCamera(
            type: "orthographic",
            viewDirection: [0, 0, -1],
            up: [0, 1, 0],
            fitPadding: 0.08
        ))
    }

    private func modelScene(
        descriptor: BoardModelDescriptor,
        bodyPosition: SIMD3<Float>? = nil
    ) -> SCNScene {
        let scene = SCNScene()
        for (index, binding) in descriptor.nodes.enumerated() {
            let geometry = SCNBox(width: 0.02, height: 0.02, length: 0.02, chamferRadius: 0)
            geometry.firstMaterial = SCNMaterial()
            let node = SCNNode(geometry: geometry)
            node.name = binding.nodeID
            node.simdPosition = binding.role == .body && bodyPosition != nil
                ? bodyPosition!
                : SIMD3<Float>(10 + Float(index), 10, 10)
            scene.rootNode.addChildNode(node)
        }
        return scene
    }
}
