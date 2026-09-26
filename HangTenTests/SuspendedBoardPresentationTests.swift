import XCTest
import SceneKit
import simd
@testable import HangTen

final class SuspendedBoardPresentationTests: XCTestCase {

    func testInstanceRoutedPairedLeadsPreserveAuthoredWorldAnchor() throws {
        var transform = matrix_identity_float4x4
        transform.columns.0.x = -1
        transform.columns.3 = SIMD4(3, 0, 0, 1)
        let paired = pairedLeadSuspension(
            leftContacts: [[-0.6, 0.4, 0.15]], rightContacts: [[0.6, 0.4, 0.05]],
            anchor: [3, 3, 0], restLength: 4)
        guard case .pairedLead(let solved) = try SuspendedBoardPresentation.solveInstance(
            pose: pose(), suspension: .pairedLeadCord(paired), bounds: bounds, transform: transform) else {
            return XCTFail("Expected paired leads")
        }
        XCTAssertEqual(solved.fixedAnchor, SIMD3(3, 3, 0))
        for lead in solved.leads {
            XCTAssertEqual(lead.samples.first, SIMD3(3, 3, 0))
        }
        XCTAssertTrue(solved.cameraFraming.contains(SIMD3(3, 3, 0)))
    }

    func testInstanceRoutedPairedLeadsRejectLengthRequiringAnchorRelocation() throws {
        var transform = matrix_identity_float4x4
        transform.columns.0.x = -1
        transform.columns.3 = SIMD4(3, 0, 0, 1)
        let paired = pairedLeadSuspension(
            leftContacts: [[-0.6, 0.4, 0.15]], rightContacts: [[0.6, 0.4, 0.05]],
            anchor: [3, 3, 0], restLength: 3)
        XCTAssertThrowsError(try SuspendedBoardPresentation.solveInstance(
            pose: pose(), suspension: .pairedLeadCord(paired), bounds: bounds, transform: transform)) {
            XCTAssertEqual($0 as? SuspendedPresentationError, .cordTooShort)
        }
    }

    func testLegacyRoutedPairedLeadsRetainProjectionWithExplicitModelTransform() throws {
        var transform = matrix_identity_float4x4
        transform.columns.0.x = -1
        transform.columns.3 = SIMD4(3, 0, 0, 1)
        let paired = pairedLeadSuspension(
            leftContacts: [[-0.6, 0.4, 0.15]], rightContacts: [[0.6, 0.4, 0.05]],
            anchor: [3, 3, 0], restLength: 3)
        let solved = try SuspendedBoardPresentation.solve(
            pose: pose(), suspension: paired, bounds: bounds, modelTransform: transform)
        XCTAssertEqual(solved.fixedAnchor.x, 3)
        XCTAssertEqual(solved.fixedAnchor.y, 3)
        XCTAssertEqual(solved.fixedAnchor.z, 0.228, accuracy: 0.000001)
    }

    func testInstanceSuspensionSolvesInWorldSpaceWithFixedAnchor() throws {
        var transform = matrix_identity_float4x4
        transform.columns.0.x = -1
        transform.columns.3 = SIMD4(3, 0, 0, 1)
        let paired = pairedLeadSuspension(anchor: [3, 3, 0], restLength: 3)
        guard case .pairedLead(let solved) = try SuspendedBoardPresentation.solveInstance(
            pose: pose(), suspension: .pairedLeadCord(paired), bounds: bounds, transform: transform) else {
            return XCTFail("Expected paired leads")
        }
        XCTAssertEqual(solved.fixedAnchor, SIMD3(3, 3, 0))
        XCTAssertEqual(try XCTUnwrap(solved.leads[0].samples.last), SIMD3(3.6, 0.4, 0.05))
        XCTAssertEqual(try XCTUnwrap(solved.leads[1].samples.last), SIMD3(2.4, 0.4, -0.05))
        XCTAssertTrue(solved.cameraFraming.includedPoints.allSatisfy { solved.cameraFraming.contains($0) })
        guard case .single(let single) = try SuspendedBoardPresentation.solveInstance(
            pose: pose(), suspension: suspension(attachment: [0.6, 0.4, 0], anchor: [3, 3, 0], restLength: 3),
            bounds: bounds, transform: transform) else {
            return XCTFail("Expected single cord")
        }
        XCTAssertEqual(single.transformedAttachment, SIMD3(2.4, 0.4, 0))
        XCTAssertEqual(single.fixedAnchor, SIMD3(3, 3, 0))
        transform.columns.3.x = .infinity
        XCTAssertThrowsError(try SuspendedBoardPresentation.solveInstance(
            pose: pose(), suspension: .pairedLeadCord(paired), bounds: bounds, transform: transform))
    }

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

    private func pairedLeadSuspension(
        left: [Double] = [-0.6, 0.4, 0.05],
        right: [Double] = [0.6, 0.4, -0.05],
        leftContacts: [[Double]] = [],
        rightContacts: [[Double]] = [],
        anchor: [Double] = [0, 2, 0],
        restLength: Double = 2,
        radius: Double = 0.01,
        canonicalPoses: [String: BoardModelCanonicalPose] = [:]
    ) -> BoardModelPairedLeadCord {
        BoardModelPairedLeadCord(
            attachments: [
                BoardModelPairedLeadAttachment(id: "left", nodeID: "left-attachment", pointInModel: left, provenance: "test", contactPointsInModel: leftContacts),
                BoardModelPairedLeadAttachment(id: "right", nodeID: "right-attachment", pointInModel: right, provenance: "test", contactPointsInModel: rightContacts),
            ],
            passages: BoardModelPassagePairs(
                left: [BoardModelPassage(id: "left-lip", nodeID: "left-attachment", pointInModel: left, provenance: "test")],
                right: [BoardModelPassage(id: "right-lip", nodeID: "right-attachment", pointInModel: right, provenance: "test")]
            ),
            anchor: BoardModelInvisibleAnchor(offsetFromBoardBounds: [0, 0, 0], visibility: "invisible", provenance: "test", position: anchor),
            cord: BoardModelCord(restLength: restLength, radius: radius, material: "test-cord", provenance: "test"),
            canonicalPoses: canonicalPoses
        )
    }

    private func solvedLead(_ samples: [SIMD3<Float>]) -> SolvedCordBranch {
        SolvedCordBranch(
            samples: samples,
            tangents: Array(repeating: SIMD3<Float>(0, -1, 0), count: samples.count),
            arcLength: 0,
            polylineArcLength: 0,
            isTaut: true
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

    func testPairedLeadSolvesExactlyTwoIndependentAnchorToAttachmentCenterlines() throws {
        let selectedPose = pose(
            rotation: [0, sin(Double.pi / 4), 0, cos(Double.pi / 4)],
            translation: [0.2, -0.1, 0.3]
        )
        let suspension = pairedLeadSuspension()

        let result = try SuspendedBoardPresentation.solve(
            pose: selectedPose,
            suspension: suspension,
            bounds: bounds
        )

        XCTAssertEqual(result.leads.count, 2)
        XCTAssertEqual(result.fixedAnchor, SIMD3<Float>(0, 2, 0))
        let expectedAttachments = suspension.attachments.map { attachment -> SIMD3<Float> in
            let point = SIMD3<Float>(Float(attachment.pointInModel[0]), Float(attachment.pointInModel[1]), Float(attachment.pointInModel[2]))
            let transformed = result.boardTransform * SIMD4(point, 1)
            return SIMD3<Float>(transformed.x, transformed.y, transformed.z)
        }
        for (index, pair) in zip(result.leads, expectedAttachments).enumerated() {
            let lead = pair.0
            let expectedAttachment = pair.1
            XCTAssertEqual(lead.centerlineSamples.count, SuspendedCordSolver.sampleCount)
            XCTAssertEqual(lead.centerlineSamples.first, result.fixedAnchor)
            XCTAssertEqual(lead.centerlineSamples.last, expectedAttachment)
            XCTAssertFalse(lead.centerlineSamples.contains(expectedAttachments[(index + 1) % 2]))
            assertStraight(lead.centerlineSamples, label: "paired lead")
        }
        XCTAssertEqual(result.tubeRadius, 0.01, accuracy: 1e-6)
        XCTAssertEqual(result.requiredClearance, 0.011, accuracy: 1e-6)
        XCTAssertTrue(result.leads.flatMap(\.centerlineSamples).allSatisfy { result.cameraFraming.contains($0) })
    }

    func testPairedLeadExitsAlongBoreAxisToTheDeclaredTerminal() throws {
        let leftContacts = [[-0.6, 0.5, 0.1], [-0.6, 0.35, 0.05]]
        let rightContacts = [[0.6, 0.5, 0.1], [0.6, 0.35, 0.05]]
        let profile = pairedLeadSuspension(
            left: [-0.6, 0.2, 0],
            right: [0.6, 0.2, 0],
            leftContacts: leftContacts,
            rightContacts: rightContacts,
            restLength: 2.5
        )

        let result = try SuspendedBoardPresentation.solve(
            pose: pose(),
            suspension: profile,
            bounds: bounds
        )

        for (lead, attachment) in zip(result.leads, profile.attachments) {
            let terminal = SIMD3<Float>(
                Float(attachment.pointInModel[0]),
                Float(attachment.pointInModel[1]),
                Float(attachment.pointInModel[2])
            )
            let stubValues = try XCTUnwrap(attachment.contactPointsInModel.last)
            let stub = SIMD3<Float>(Float(stubValues[0]), Float(stubValues[1]), Float(stubValues[2]))
            XCTAssertEqual(lead.samples.first, result.fixedAnchor)
            XCTAssertEqual(lead.samples.last, terminal)
            let exit = lead.samples[lead.samples.count - 2]
            XCTAssertGreaterThan(
                simd_dot(simd_normalize(exit - terminal), simd_normalize(stub - terminal)),
                0.99
            )
            XCTAssertGreaterThanOrEqual(simd_length(exit - terminal), simd_length(stub - terminal))
            XCTAssertLessThanOrEqual(lead.arcLength, 2.5 + SuspendedCordSolver.tautTolerance)
        }
    }

    func testPairedLeadRejectsWhenEitherIndependentLeadIsTooShort() {
        XCTAssertThrowsError(try SuspendedBoardPresentation.solve(
            pose: pose(),
            suspension: pairedLeadSuspension(right: [1, -0.5, 0]),
            bounds: bounds
        )) { error in
            XCTAssertEqual(error as? SuspendedPresentationError, .cordTooShort)
        }
    }

    func testPairedLeadUsesExplicitPoseMouthsInsteadOfRotatingTheOtherFaceMouths() throws {
        let suspension = pairedLeadSuspension()
        var selectedPose = pose()
        selectedPose.attachmentPoints = Dictionary(uniqueKeysWithValues: zip(
            suspension.attachments.map(\.id), [[-0.6, 0.3, 0.05], [0.6, 0.3, -0.05]]
        ))
        let result = try SuspendedBoardPresentation.solve(pose: selectedPose, suspension: suspension, bounds: bounds)
        XCTAssertEqual(result.leads[0].samples.last, SIMD3<Float>(-0.6, 0.3, 0.05))
        XCTAssertEqual(result.leads[1].samples.last, SIMD3<Float>(0.6, 0.3, -0.05))
        selectedPose.attachmentPoints?.removeValue(forKey: suspension.attachments[0].id)
        XCTAssertThrowsError(try SuspendedBoardPresentation.solve(pose: selectedPose, suspension: suspension, bounds: bounds))
    }

    func testPairedLeadUsesOrderedPoseContactsWithoutMovingItsTerminal() throws {
        let profile = pairedLeadSuspension(restLength: 2.5)
        var selectedPose = pose()
        selectedPose.cordContactPoints = [
            "left": [[-0.6, 0.6, 0.1], [-0.6, 0.5, 0.1]],
            "right": [[0.6, 0.6, 0.1], [0.6, 0.5, 0.1]]
        ]
        let solved = try SuspendedBoardPresentation.solve(pose: selectedPose, suspension: profile, bounds: bounds)
        XCTAssertEqual(Array(solved.leads[0].samples.suffix(3)), [
            SIMD3<Float>(-0.6, 0.6, 0.1), SIMD3<Float>(-0.6, 0.5, 0.1), SIMD3<Float>(-0.6, 0.4, 0.05)
        ])
        selectedPose.cordContactPoints?["left"] = [[-0.6, 3, 0.1]]
        XCTAssertThrowsError(try SuspendedBoardPresentation.solve(pose: selectedPose, suspension: profile, bounds: bounds)) {
            XCTAssertEqual($0 as? SuspendedPresentationError, .cordTooShort)
        }
        selectedPose.cordContactPoints?.removeValue(forKey: "left")
        XCTAssertThrowsError(try SuspendedBoardPresentation.solve(pose: selectedPose, suspension: profile, bounds: bounds)) {
            XCTAssertEqual($0 as? SuspendedPresentationError, .invalidSuspension)
        }
    }

    func testPairedLeadRejectsDistinctLeadsThatAreTooCloseAfterTheirSharedAnchor() {
        XCTAssertThrowsError(try SuspendedBoardPresentation.solve(
            pose: pose(),
            suspension: pairedLeadSuspension(
                left: [0, 0.4, 0],
                right: [0.005, 0.4, 0]
            ),
            bounds: bounds
        )) { error in
            XCTAssertEqual(error as? SuspendedPresentationError, .selfIntersection)
        }
    }

    func testPairedLeadRejectsLeadsCloserThanTheirTwoTubeDiameterClearance() {
        XCTAssertThrowsError(try SuspendedBoardPresentation.solve(
            pose: pose(),
            suspension: pairedLeadSuspension(
                left: [-0.0075, 0.4, 0],
                right: [0.0075, 0.4, 0]
            ),
            bounds: bounds
        )) { error in
            XCTAssertEqual(error as? SuspendedPresentationError, .selfIntersection)
        }
    }

    func testPairedLeadAllowsTwoTubeClearanceOnlyInsideTheSharedAnchorKnot() throws {
        let radius = 0.002
        let result = try SuspendedBoardPresentation.solve(
            pose: pose(),
            suspension: pairedLeadSuspension(
                left: [-0.048, 0.0525, 0],
                right: [0.048, 0.0525, 0],
                anchor: [0, 0.3525, 0],
                restLength: 0.55,
                radius: radius
            ),
            bounds: bounds
        )

        XCTAssertEqual(result.leads.count, 2)
        XCTAssertEqual(
            result.requiredClearance,
            Float(radius) + SuspendedBoardPresentation.additionalClearance,
            accuracy: Float(1e-6)
        )
    }

    func testPairedLeadRejectsFullyOverlappingLeadsThatNeverExitTheSharedAnchorKnot() {
        XCTAssertThrowsError(try SuspendedBoardPresentation.solve(
            pose: pose(),
            suspension: pairedLeadSuspension(
                left: [0, 0.402, 0],
                right: [0, 0.402, 0],
                anchor: [0, 0.4, 0],
                restLength: 0.01,
                radius: 0.01
            ),
            bounds: bounds
        )) { error in
            XCTAssertEqual(error as? SuspendedPresentationError, .selfIntersection)
        }
    }

    func testPairedLeadRejectsDivergingLeadsThatNeverReachFullClearance() {
        XCTAssertThrowsError(try SuspendedBoardPresentation.solve(
            pose: pose(),
            suspension: pairedLeadSuspension(
                left: [-0.001, 0.402, 0],
                right: [0.001, 0.402, 0],
                anchor: [0, 0.4, 0],
                restLength: 0.01,
                radius: 0.01
            ),
            bounds: bounds
        )) { error in
            XCTAssertEqual(error as? SuspendedPresentationError, .selfIntersection)
        }
    }

    func testPairedLeadAllowsACommonInitialTrunkThatGenuinelyForks() throws {
        let first = solvedLead([
            [0, 0, 0], [0, -0.03, 0], [-0.05, -0.08, 0], [-0.1, -0.18, 0]
        ])
        let second = solvedLead([
            [0, 0, 0], [0, -0.03, 0], [0.05, -0.08, 0], [0.1, -0.18, 0]
        ])

        try SuspendedBoardPresentation.validatePairedLeadClearance(
            [first, second],
            requiredClearance: 0.02
        )
    }

    func testPairedLeadRejectsACommonTrunkThatNeverForks() {
        let samples: [SIMD3<Float>] = [
            [0, 0, 0], [0, -0.03, 0], [0, -0.08, 0], [0, -0.18, 0]
        ]

        XCTAssertThrowsError(try SuspendedBoardPresentation.validatePairedLeadClearance(
            [solvedLead(samples), solvedLead(samples)],
            requiredClearance: 0.02
        )) { error in
            XCTAssertEqual(error as? SuspendedPresentationError, .selfIntersection)
        }
    }

    func testPairedLeadRejectsAReapproachAfterItsCommonTrunkForks() {
        let first = solvedLead([
            [0, 0, 0], [0, -0.03, 0], [-0.05, -0.08, 0], [0, -0.13, 0], [-0.05, -0.18, 0]
        ])
        let second = solvedLead([
            [0, 0, 0], [0, -0.03, 0], [0.05, -0.08, 0], [0, -0.13, 0], [0.05, -0.18, 0]
        ])

        XCTAssertThrowsError(try SuspendedBoardPresentation.validatePairedLeadClearance(
            [first, second],
            requiredClearance: 0.02
        )) { error in
            XCTAssertEqual(error as? SuspendedPresentationError, .selfIntersection)
        }
    }

    func testPairedLeadRejectsAReapproachToTheSharedAnchorAfterLeavingItsKnot() {
        let first = solvedLead([
            [0, 0, 0], [0, -0.005, 0], [-0.05, -0.08, 0], [0, 0, 0]
        ])
        let second = solvedLead([
            [0, 0, 0], [0, -0.005, 0], [0.05, -0.08, 0], [0, 0, 0]
        ])

        XCTAssertThrowsError(try SuspendedBoardPresentation.validatePairedLeadClearance(
            [first, second],
            requiredClearance: 0.02
        )) { error in
            XCTAssertEqual(error as? SuspendedPresentationError, .selfIntersection)
        }
    }

    func testPairedLeadAllowsAdjacentInitialSegmentsInsideTheSharedAnchorKnot() throws {
        let result = try SuspendedBoardPresentation.solve(
            pose: pose(),
            suspension: pairedLeadSuspension(
                left: [-0.06, 0.4, 0],
                right: [0.06, 0.4, 0],
                anchor: [0, 0.4, 0],
                restLength: 0.12,
                radius: 0.01
            ),
            bounds: bounds
        )

        XCTAssertEqual(result.leads.count, 2)
    }

    func testPairedLeadAllowsUnequalSamplingAlongDistinctStraightAnchorRays() throws {
        let first = solvedLead([
            [0, 0, 0], [-0.001, -0.01, 0], [-0.002, -0.02, 0], [-0.003, -0.03, 0],
            [-0.004, -0.04, 0]
        ])
        let second = solvedLead([
            [0, 0, 0], [0.0004, -0.004, 0], [0.0008, -0.008, 0],
            [0.0012, -0.012, 0], [0.0016, -0.016, 0], [0.002, -0.02, 0],
            [0.003, -0.03, 0], [0.004, -0.04, 0]
        ])

        try SuspendedBoardPresentation.validatePairedLeadClearance(
            [first, second],
            requiredClearance: 0.005
        )
    }

    func testPairedLeadRejectsReapproachAfterDistinctStraightAnchorRays() {
        let first = solvedLead([
            [0, 0, 0], [-0.01, -0.03, 0], [-0.02, -0.06, 0], [0, -0.1, 0]
        ])
        let second = solvedLead([
            [0, 0, 0], [0.01, -0.03, 0], [0.02, -0.06, 0], [0, -0.1, 0]
        ])

        XCTAssertThrowsError(try SuspendedBoardPresentation.validatePairedLeadClearance(
            [first, second],
            requiredClearance: 0.02
        )) { error in
            XCTAssertEqual(error as? SuspendedPresentationError, .selfIntersection)
        }
    }

    func testPairedLeadRejectsShallowBendsThatCrossAfterInitiallySeparating() {
        let first = solvedLead([
            [0, 0, 0], [-0.0028, -1, 0], [0.0028, -2, 0]
        ])
        let second = solvedLead([
            [0, 0, 0], [0.0028, -1, 0], [-0.0028, -2, 0]
        ])

        XCTAssertThrowsError(try SuspendedBoardPresentation.validatePairedLeadClearance(
            [first, second],
            requiredClearance: 0.005
        )) { error in
            XCTAssertEqual(error as? SuspendedPresentationError, .selfIntersection)
        }
    }

    func testPairedLeadRejectsCoincidentAttachmentsBeyondItsSharedAnchor() {
        XCTAssertThrowsError(try SuspendedBoardPresentation.solve(
            pose: pose(),
            suspension: pairedLeadSuspension(
                left: [0, 0.4, 0],
                right: [0, 0.4, 0]
            ),
            bounds: bounds
        )) { error in
            XCTAssertEqual(error as? SuspendedPresentationError, .selfIntersection)
        }
    }

    func testSingleCordSamplesAreStraightAndTautForSupportedPoses() throws {
        let poses = [
            pose(),
            pose(rotation: [0, sin(Double.pi / 4), 0, cos(Double.pi / 4)], translation: [0.2, 0, 0]),
            pose(rotation: [sin(Double.pi / 4), 0, 0, cos(Double.pi / 4)], translation: [0, -0.1, 0.1])
        ]

        for canonicalPose in poses {
            let result = try SuspensionProfileSolver.solveSingle(
                pose: canonicalPose,
                profile: singleProfile(restLength: 2.5),
                bounds: bounds
            )

            XCTAssertTrue(result.cord.isTaut)
            assertStraight(result.cord.centerlineSamples, label: "single cord")
            XCTAssertLessThanOrEqual(result.cord.arcLength, 2.5 + SuspendedCordSolver.tautTolerance)
        }
    }

    func testTwoBranchSamplesAreStraightPerFreeAndAuthoredRouteSpan() throws {
        let (suspension, expectedRoutes) = authoredTwoBranchSuspension()
        let result = try SuspendedBoardPresentation.solve(
            pose: pose(),
            suspension: suspension,
            bounds: bounds
        )

        for branch in result.branches {
            XCTAssertEqual(branch.spans.count, 3)
            assertStraight(branch.spans[0], label: "\(branch.id) incoming free span")
            assertStraight(branch.spans[2], label: "\(branch.id) outgoing free span")
            assertAuthoredRouteIsPiecewiseStraight(
                branch.spans[1],
                expected: try XCTUnwrap(expectedRoutes[branch.id]),
                label: "\(branch.id) authored route"
            )
            XCTAssertLessThanOrEqual(
                branch.arcLength,
                Float(suspension.branches.first { $0.id == branch.id }!.restLength)
                    + SuspendedCordSolver.tautTolerance
            )
        }
    }

    // This catches the extracted profile solver drifting from the established
    // facade contract: exact endpoints, sample count, tangents, arc lengths,
    // transform, and framing all have to continue describing the same cord.
    func testSingleProfileSolverCharacterizesTautCordAndFacadeCompatibility() throws {
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
        XCTAssertTrue(solved.cord.isTaut)
        let endpointDistance = simd_length(solved.cord.samples.last! - solved.cord.samples.first!)
        XCTAssertEqual(solved.cord.arcLength, endpointDistance, accuracy: 1e-6)
        XCTAssertEqual(solved.cord.polylineArcLength, endpointDistance, accuracy: 1e-5)
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

    func testSingleProfileSolverUsesStraightSamplesAndConstantTangents() throws {
        let solved = try SuspensionProfileSolver.solveSingle(
            pose: pose(),
            profile: singleProfile(),
            bounds: bounds
        )

        XCTAssertTrue(solved.cord.isTaut)
        assertStraight(solved.cord.centerlineSamples, label: "single cord")
        XCTAssertTrue(solved.cord.tangents.dropFirst().allSatisfy { $0 == solved.cord.tangents[0] })
        XCTAssertEqual(solved.cord.polylineArcLength, solved.cord.arcLength, accuracy: 1e-5)
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
        let extraLength = try SuspensionProfileSolver.solveSingle(
            pose: pose(),
            profile: singleProfile(attachment: [0, 0, 0], anchor: [0, 2, 0], restLength: 2.1),
            bounds: bounds
        )
        XCTAssertTrue(extraLength.cord.isTaut)
        XCTAssertEqual(extraLength.cord.arcLength, 2, accuracy: 1e-6)
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

    func testTautCordHasExactEndpointsFiniteSamplesAndContinuousTangents() throws {
        let solution = try SuspendedCordSolver.solve(
            start: SIMD3<Float>(-0.5, 1, 0),
            end: SIMD3<Float>(0.5, 1, 0),
            restLength: 1.6
        )

        XCTAssertTrue(solution.isTaut)
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
        XCTAssertEqual(measuredPolylineLength, 1, accuracy: 0.01)
        XCTAssertEqual(solution.samples.map(\.y).min()!, 1, accuracy: 1e-6)
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

    func testVerticalCordWithExtraDeclaredLengthRemainsStraightAndTaut() throws {
        let solution = try SuspendedCordSolver.solve(
            start: SIMD3<Float>(0, 1, 0),
            end: SIMD3<Float>(0, 0, 0),
            restLength: 1.1
        )
        XCTAssertTrue(solution.isTaut)
        assertStraight(solution.centerlineSamples, label: "vertical cord")
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
        let solved = try BoardModelRealityScene.solveSuspension(
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
            let measuredLength = zip(branch.centerlineSamples, branch.centerlineSamples.dropFirst()).reduce(Float.zero) {
                $0 + simd_length($1.1 - $1.0)
            }
            XCTAssertEqual(branch.arcLength, measuredLength, accuracy: 1e-5)
            XCTAssertLessThanOrEqual(branch.arcLength, 4.2 + SuspendedCordSolver.tautTolerance)
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

    func testTwoBranchAcceptsVerticalFreeSpanAndRejectsNonfiniteInputs() throws {
        let result = try SuspendedBoardPresentation.solve(
            pose: pose(),
            suspension: twoBranchSuspension(
                left: [[0, 0.4, 0], [0.1, 0.4, 0]],
                right: [[0.4, 0.4, 0], [0.6, 0.4, 0]],
                anchor: [0, 2, 0],
                restLength: 4
            ),
            bounds: bounds
        )
        XCTAssertTrue(result.branches[0].spans[0].allSatisfy { $0.x == 0 && $0.z == 0 })

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
                // The second passage lies midway along anchor (0, 2, 0)
                // to first passage (-1, 0, 0), so the interior route doubles
                // back over the incoming straight span.
                left: [[-1, 0, 0], [-0.5, 1, 0]],
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
    func testSceneSelectionAcceptsEachBodyOrAttachmentPassageBinding() throws {
        let suspension = twoBranchSuspension(
            restLength: 4.2,
            canonicalPoses: ["primary": pose()]
        )
        for passage in suspension.passages.left + suspension.passages.right {
            for role in [BoardModelNodeDescriptor.Role.body, .attachment] {
                let descriptor = sceneDescriptor(
                    for: suspension,
                    bodyNodeID: role == .body ? passage.nodeID : nil
                )
                let model = try XCTUnwrap(BoardModelScene(
                    source: modelScene(descriptor: descriptor),
                    descriptor: descriptor,
                    display: sceneDisplay(),
                    suspension: .twoBranchCord(suspension)
                ))
                XCTAssertTrue(model.select(positionID: "primary"), "\(passage.nodeID), role: \(role)")
                XCTAssertFalse(model.isUnavailable)
                XCTAssertNotNil(model.transientCordNode)
            }
        }
    }

    @MainActor
    func testSceneSelectionRejectsEachMissingOrHoldPassageBinding() throws {
        let suspension = twoBranchSuspension(
            restLength: 4.2,
            canonicalPoses: ["primary": pose()]
        )
        for passage in suspension.passages.left + suspension.passages.right {
            for omit in [true, false] {
                let descriptor = sceneDescriptor(
                    for: suspension,
                    omittedNodeID: omit ? passage.nodeID : nil,
                    holdNodeID: omit ? nil : passage.nodeID
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

    private func assertStraight(_ samples: [SIMD3<Float>], label: String) {
        guard let start = samples.first, let end = samples.last else {
            return XCTFail("\(label) must have endpoints")
        }
        let direction = end - start
        let lengthSquared = simd_length_squared(direction)
        XCTAssertGreaterThan(lengthSquared, 1e-12, "\(label) endpoints must differ")
        guard lengthSquared > 1e-12 else { return }
        for sample in samples {
            let parameter = simd_dot(sample - start, direction) / lengthSquared
            let closest = start + direction * parameter
            XCTAssertGreaterThanOrEqual(parameter, -1e-5, "\(label) sample before start")
            XCTAssertLessThanOrEqual(parameter, 1 + 1e-5, "\(label) sample after end")
            XCTAssertLessThanOrEqual(simd_length(sample - closest), 1e-5, "\(label) sample is not collinear")
        }
    }

    private func assertAuthoredRouteIsPiecewiseStraight(
        _ route: [SIMD3<Float>],
        expected: [SIMD3<Float>],
        label: String
    ) {
        XCTAssertEqual(route, expected, "\(label) must preserve authored passage/bearing/shoulder points in order")
        XCTAssertGreaterThanOrEqual(route.count, 2, "\(label) needs at least two route points")
        for (index, pair) in zip(route, route.dropFirst()).enumerated() {
            XCTAssertGreaterThan(
                simd_length(pair.1 - pair.0),
                1e-7,
                "\(label) segment \(index) must join distinct authored points directly"
            )
        }
    }

    private func authoredTwoBranchSuspension() -> (
        suspension: BoardModelTwoBranchSuspension,
        expectedRoutes: [String: [SIMD3<Float>]]
    ) {
        func passage(
            _ id: String,
            _ entry: [Double],
            _ exit: [Double]
        ) -> BoardModelPassage {
            BoardModelPassage(
                id: id,
                nodeID: "body",
                entryPointInModel: entry,
                exitPointInModel: exit,
                provenance: "test-authored-route"
            )
        }
        let left0Entry = [-0.6, 0.4, -0.05]
        let left0Exit = [-0.55, 0.42, 0.05]
        let left1Entry = [-0.42, 0.44, 0.02]
        let left1Exit = [-0.39, 0.42, 0.05]
        let right0Entry = [0.39, 0.42, 0.05]
        let right0Exit = [0.42, 0.44, 0.02]
        let right1Entry = [0.55, 0.42, 0.05]
        let right1Exit = [0.6, 0.4, -0.05]
        let leftEntryShoulder = [-0.66, 0.46, -0.06]
        let leftBearing = [[-0.50, 0.46, 0.08], [-0.44, 0.46, 0.08]]
        let leftExitShoulder = [-0.30, 0.46, -0.06]
        let rightEntryShoulder = [0.30, 0.46, -0.06]
        let rightBearing = [[0.44, 0.46, 0.08], [0.50, 0.46, 0.08]]
        let rightExitShoulder = [0.66, 0.46, -0.06]
        let anchor = SIMD3<Float>(0, 2, 0)
        let branch = { (id: String, passageIDs: [String], entry: [Double], bearing: [[Double]], exit: [Double]) in
            BoardModelCordBranch(
                id: id,
                passageIDs: passageIDs,
                entryContactPoints: [entry],
                exteriorContactPoints: bearing,
                exitContactPoints: [exit],
                restLength: 4.2,
                radius: 0.01,
                material: "test-cord",
                provenance: "test-authored-route"
            )
        }
        let suspension = BoardModelTwoBranchSuspension(
            passages: BoardModelPassagePairs(
                left: [passage("left-0", left0Entry, left0Exit), passage("left-1", left1Entry, left1Exit)],
                right: [passage("right-0", right0Entry, right0Exit), passage("right-1", right1Entry, right1Exit)]
            ),
            branches: [
                branch("left", ["left-0", "left-1"], leftEntryShoulder, leftBearing, leftExitShoulder),
                branch("right", ["right-0", "right-1"], rightEntryShoulder, rightBearing, rightExitShoulder),
            ],
            anchor: BoardModelInvisibleAnchor(
                offsetFromBoardBounds: [0, 0, 0],
                visibility: "invisible",
                provenance: "test-authored-route",
                position: [Double(anchor.x), Double(anchor.y), Double(anchor.z)]
            ),
            canonicalPoses: [:]
        )
        let vector: ([Double]) -> SIMD3<Float> = { values in
            SIMD3<Float>(Float(values[0]), Float(values[1]), Float(values[2]))
        }
        return (
            suspension,
            [
                "left": [vector(leftEntryShoulder), vector(left0Entry), vector(left0Exit)]
                    + leftBearing.map(vector)
                    + [vector(left1Exit), vector(left1Entry), vector(leftExitShoulder)],
                "right": [vector(rightEntryShoulder), vector(right0Entry), vector(right0Exit)]
                    + rightBearing.map(vector)
                    + [vector(right1Exit), vector(right1Entry), vector(rightExitShoulder)]
            ]
        )
    }

    private func sceneDescriptor(
        for suspension: BoardModelTwoBranchSuspension,
        omittedNodeID: String? = nil,
        bodyNodeID: String? = nil,
        holdNodeID: String? = nil
    ) -> BoardModelDescriptor {
        let passageNodes = (suspension.passages.left + suspension.passages.right)
            .filter { $0.nodeID != omittedNodeID }
            .map {
            BoardModelNodeDescriptor(
                nodeID: $0.nodeID,
                role: $0.nodeID == holdNodeID ? .contact : ($0.nodeID == bodyNodeID ? .body : .attachment),
                contactID: $0.nodeID == holdNodeID ? "hold" : nil
            )
        }
        return BoardModelDescriptor(
            schemaVersion: 1,
            coordinateFrame: "hang-ten-board-v1",
            modelSHA256: String(repeating: "0", count: 64),
            modelBounds: bounds,
            nodes: [
                BoardModelNodeDescriptor(nodeID: "Body", role: .body, contactID: nil),
                BoardModelNodeDescriptor(nodeID: "Hold", role: .contact, contactID: "hold"),
            ] + passageNodes,
            contacts: [
                "hold": BoardModelContactDescriptor(
                    nodeIDs: ["Hold"] + (holdNodeID.map { [$0] } ?? []),
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
            fitPadding: 0.08,
            distanceMultiplier: nil,
            boundsExpansionFactor: nil
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
