import Foundation
import simd


// Compatibility names retained for presentation and test callers while the
// model-layer solver owns the single-cord result data.
typealias SuspendedCordSolution = SolvedCordBranch
typealias SuspendedSolvedPresentation = SolvedSuspension
struct SuspendedBranchSolution {
    let id: String
    let passageIDs: [String]
    let spans: [[SIMD3<Float>]]
    let centerlineSamples: [SIMD3<Float>]
    let tangentSamples: [SIMD3<Float>]
    let arcLength: Float
}

struct SuspendedTwoBranchSolvedPresentation {
    let boardTransform: simd_float4x4
    let fixedAnchor: SIMD3<Float>
    let branches: [SuspendedBranchSolution]
    let cameraFraming: SuspendedCameraFraming
    let tubeRadius: Float
    let requiredClearance: Float
}

struct SuspendedPairedLeadSolvedPresentation {
    let boardTransform: simd_float4x4
    let fixedAnchor: SIMD3<Float>
    let leads: [SolvedCordBranch]
    let cameraFraming: SuspendedCameraFraming
    let tubeRadius: Float
    let requiredClearance: Float
}


enum SuspendedBoardPresentation {
    static let additionalClearance: Float = 0.001
    // Two independent hanging leads need more than the generic model edge
    // padding so the free span stays plainly visible in the detail view.
    // This is presentation-only framing; it does not alter any authored cord
    // route, attachment, anchor, or board geometry.
    static let pairedLeadMinimumCameraFitPadding: Float = 1.4

    static func solve(
        pose: BoardModelCanonicalPose,
        suspension: BoardModelSuspension,
        bounds: BoardModelBounds
    ) throws -> SuspendedSolvedPresentation {

        let profile: BoardModelSingleCordSuspension
        switch suspension {
        case .singleCord(let single):
            profile = single
        case .pairedLeadCord:
            throw SuspendedPresentationError.invalidSuspension
        case .twoBranchCord:
            // Preserve the compatibility projection for callers that still
            // route an enum value through the historical single-cord facade.
            profile = BoardModelSingleCordSuspension(
                attachment: suspension.attachment,
                anchor: suspension.anchor,
                cord: suspension.cord,
                canonicalPoses: suspension.canonicalPoses
            )
        }
        return try SuspensionProfileSolver.solveSingle(
            pose: pose,
            profile: profile,
            bounds: bounds
        )
    }

    static func solve(
        pose: BoardModelCanonicalPose,
        suspension: BoardModelPairedLeadCord,
        bounds: BoardModelBounds
    ) throws -> SuspendedPairedLeadSolvedPresentation {
        let transform = try boardTransform(for: pose)
        let (minimum, maximum) = try validatedBounds(bounds)
        if let points = pose.attachmentPoints {
            guard Set(points.keys) == Set(suspension.attachments.map(\.id)),
                  Set(points.values).count == 2,
                  points.values.allSatisfy({ point in
                      point.count == 3 && point.allSatisfy(\.isFinite)
                          && zip(point, bounds.minimum).allSatisfy({ $0 >= $1 })
                          && zip(point, bounds.maximum).allSatisfy({ $0 <= $1 })
                  }) else { throw SuspendedPresentationError.invalidSuspension }
        }
        guard suspension.attachments.count == 2,
              Set(suspension.attachments.map(\.id)).count == suspension.attachments.count,
              suspension.attachments.allSatisfy({
                  $0.pointInModel.count == 3
                      && $0.pointInModel.allSatisfy(\.isFinite)
                      && zip($0.pointInModel, bounds.minimum).allSatisfy({ $0 >= $1 })
                      && zip($0.pointInModel, bounds.maximum).allSatisfy({ $0 <= $1 })
              }),
              suspension.anchor.visibility == "invisible",
              suspension.anchor.position.count == 3,
              suspension.anchor.position.allSatisfy(\.isFinite) else {
            throw SuspendedPresentationError.invalidSuspension
        }
        guard suspension.cord.restLength.isFinite,
              suspension.cord.restLength > 0,
              suspension.cord.radius.isFinite,
              suspension.cord.radius > 0 else {
            throw SuspendedPresentationError.invalidCord
        }

        let fixedAnchor = SIMD3<Float>(
            Float(suspension.anchor.position[0]),
            Float(suspension.anchor.position[1]),
            Float(suspension.anchor.position[2])
        )
        guard fixedAnchor.allFinite else {
            throw SuspendedPresentationError.invalidSuspension
        }
        let transformedAttachments = suspension.attachments.map { attachment in
            let point = pose.attachmentPoints?[attachment.id] ?? attachment.pointInModel
            return transformPoint(
                transform,
                SIMD3<Float>(
                    Float(point[0]),
                    Float(point[1]),
                    Float(point[2])
                )
            )
        }
        guard transformedAttachments.allSatisfy(\.allFinite) else {
            throw SuspendedPresentationError.invalidPose
        }
        let leads = try transformedAttachments.map {
            try SuspendedCordSolver.solve(
                start: fixedAnchor,
                end: $0,
                restLength: Float(suspension.cord.restLength)
            )
        }
        guard leads.count == 2,
              leads.allSatisfy({
                  $0.samples.count == SuspendedCordSolver.sampleCount
                      && $0.samples.first == fixedAnchor
                      && $0.samples.allSatisfy(\.allFinite)
                      && $0.tangents.allSatisfy(\.allFinite)
              }),
              zip(leads, transformedAttachments).allSatisfy({ $0.0.samples.last == $0.1 }) else {
            throw SuspendedPresentationError.nonFiniteCurve
        }
        let tubeRadius = Float(suspension.cord.radius)
        try validatePairedLeadClearance(
            leads,
            requiredClearance: 2 * tubeRadius + additionalClearance
        )

        let framing = try makeCameraFraming(
            pose: pose,
            transform: transform,
            minimumFitPadding: pairedLeadMinimumCameraFitPadding,
            points: transformedBoundsCorners(minimum: minimum, maximum: maximum, transform: transform)
                + [fixedAnchor]
                + transformedAttachments
                + leads.flatMap(\.samples)
        )
        return SuspendedPairedLeadSolvedPresentation(
            boardTransform: transform,
            fixedAnchor: fixedAnchor,
            leads: leads,
            cameraFraming: framing,
            tubeRadius: tubeRadius,
            requiredClearance: tubeRadius + additionalClearance
        )
    }

    static func solve(
        pose: BoardModelCanonicalPose,
        suspension: BoardModelTwoBranchSuspension,
        bounds: BoardModelBounds
    ) throws -> SuspendedTwoBranchSolvedPresentation {
        let transform = try boardTransform(for: pose)
        let (minimum, maximum) = try validatedBounds(bounds)

        guard suspension.branches.count == 2,
              suspension.anchor.visibility == "invisible",
              suspension.anchor.position.count == 3,
              suspension.anchor.position.allSatisfy(\.isFinite) else {
            throw SuspendedPresentationError.invalidSuspension
        }
        let fixedAnchor = SIMD3<Float>(
            Float(suspension.anchor.position[0]),
            Float(suspension.anchor.position[1]),
            Float(suspension.anchor.position[2])
        )
        guard fixedAnchor.allFinite else {
            throw SuspendedPresentationError.invalidSuspension
        }

        let allPassages = suspension.passages.left + suspension.passages.right
        guard allPassages.count == 4,
              Set(allPassages.map(\.id)).count == allPassages.count,
              allPassages.allSatisfy({
                  $0.entryPointInModel.count == 3 &&
                  $0.exitPointInModel.count == 3 &&
                  $0.entryPointInModel.allSatisfy(\.isFinite) &&
                  $0.exitPointInModel.allSatisfy(\.isFinite) &&
                  zip($0.entryPointInModel, bounds.minimum).allSatisfy({ $0 >= $1 }) &&
                  zip($0.entryPointInModel, bounds.maximum).allSatisfy({ $0 <= $1 }) &&
                  zip($0.exitPointInModel, bounds.minimum).allSatisfy({ $0 >= $1 }) &&
                  zip($0.exitPointInModel, bounds.maximum).allSatisfy({ $0 <= $1 })
              }) else {
            throw SuspendedPresentationError.invalidSuspension
        }
        let passagesByID = Dictionary(uniqueKeysWithValues: allPassages.map { passage in
            (passage.id, (
                SIMD3<Float>(
                    Float(passage.entryPointInModel[0]),
                    Float(passage.entryPointInModel[1]),
                    Float(passage.entryPointInModel[2])
                ),
                SIMD3<Float>(
                    Float(passage.exitPointInModel[0]),
                    Float(passage.exitPointInModel[1]),
                    Float(passage.exitPointInModel[2])
                ),
                passage.isThroughBore
            ))
        })
        guard passagesByID.values.allSatisfy({ $0.0.allFinite && $0.1.allFinite }) else {
            throw SuspendedPresentationError.invalidSuspension
        }

        var branches: [SuspendedBranchSolution] = []
        var radii: [Float] = []
        let declaredPassageIDs = suspension.branches.flatMap(\.passageIDs)
        guard declaredPassageIDs.count == 4,
              Set(declaredPassageIDs).count == declaredPassageIDs.count,
              Set(suspension.branches.map(\.id)).count == suspension.branches.count else {
            throw SuspendedPresentationError.invalidSuspension
        }
        var framingPoints = transformedBoundsCorners(
            minimum: minimum,
            maximum: maximum,
            transform: transform
        ) + [fixedAnchor]
        for branch in suspension.branches {
            guard branch.passageIDs.count == 2,
                  Set(branch.passageIDs).count == branch.passageIDs.count,
                  branch.restLength.isFinite,
                  branch.restLength > 0,
                  branch.radius.isFinite,
                  branch.radius > 0,
                  branch.passageIDs.allSatisfy({ passagesByID[$0] != nil }) else {
                throw SuspendedPresentationError.invalidCord
            }
            guard let firstModelPassage = passagesByID[branch.passageIDs[0]],
                  let secondModelPassage = passagesByID[branch.passageIDs[1]] else {
                throw SuspendedPresentationError.invalidSuspension
            }
            let usesAuthoredRoute = firstModelPassage.2 && secondModelPassage.2
            guard !usesAuthoredRoute || (
                branch.entryContactPoints.count >= 1 &&
                branch.exteriorContactPoints.count >= 2 &&
                branch.exitContactPoints.count >= 1 &&
                branch.entryContactPoints.allSatisfy({ $0.count == 3 && $0.allSatisfy(\.isFinite) }) &&
                branch.exteriorContactPoints.allSatisfy({ $0.count == 3 && $0.allSatisfy(\.isFinite) }) &&
                branch.exitContactPoints.allSatisfy({ $0.count == 3 && $0.allSatisfy(\.isFinite) })
            ) else {
                throw SuspendedPresentationError.invalidCord
            }
            let firstEntry = transformPoint(transform, firstModelPassage.0)
            let firstExit = transformPoint(transform, firstModelPassage.1)
            let secondExit = transformPoint(transform, secondModelPassage.1)
            let secondEntry = transformPoint(transform, secondModelPassage.0)
            let entryContacts: [SIMD3<Float>]
            let contactPoints: [SIMD3<Float>]
            let exitContacts: [SIMD3<Float>]
            if usesAuthoredRoute {
                entryContacts = branch.entryContactPoints.map {
                    transformPoint(transform, SIMD3<Float>(Float($0[0]), Float($0[1]), Float($0[2])))
                }
                contactPoints = branch.exteriorContactPoints.map {
                    transformPoint(transform, SIMD3<Float>(Float($0[0]), Float($0[1]), Float($0[2])))
                }
                exitContacts = branch.exitContactPoints.map {
                    transformPoint(transform, SIMD3<Float>(Float($0[0]), Float($0[1]), Float($0[2])))
                }
            } else {
                entryContacts = [firstEntry]
                contactPoints = []
                exitContacts = [secondEntry]
            }
            guard firstEntry.allFinite, firstExit.allFinite, secondExit.allFinite, secondEntry.allFinite,
                  entryContacts.allSatisfy(\.allFinite), contactPoints.allSatisfy(\.allFinite),
                  exitContacts.allSatisfy(\.allFinite) else {
                throw SuspendedPresentationError.invalidPose
            }
            let rigidRoute = usesAuthoredRoute
                ? entryContacts + [firstEntry, firstExit] + contactPoints + [secondExit, secondEntry] + exitContacts
                : [firstEntry, secondEntry]
            let rigidLength = zip(rigidRoute, rigidRoute.dropFirst()).reduce(Float.zero) {
                $0 + simd_length($1.1 - $1.0)
            }
            guard rigidLength.isFinite, rigidLength > 1e-7 else {
                throw SuspendedPresentationError.invalidSuspension
            }

            let firstDistance = simd_length(entryContacts[0] - fixedAnchor)
            let secondDistance = simd_length(fixedAnchor - exitContacts[exitContacts.count - 1])
            guard firstDistance.isFinite, secondDistance.isFinite,
                  firstDistance > 1e-7, secondDistance > 1e-7 else {
                throw SuspendedPresentationError.invalidCord
            }
            let minimumRouteLength = firstDistance + rigidLength + secondDistance
            let declaredLength = Float(branch.restLength)
            guard declaredLength.isFinite,
                  declaredLength >= minimumRouteLength - SuspendedCordSolver.tautTolerance else {
                throw SuspendedPresentationError.cordTooShort
            }

            // Reserve the exact authored route and allocate the remaining
            // declared capacity between free spans. Each span renders taut;
            // unused capacity never introduces sag or changes the bore route.
            let freeLength = declaredLength - rigidLength
            let endpointDistanceSum = firstDistance + secondDistance
            guard freeLength.isFinite, endpointDistanceSum.isFinite,
                  freeLength >= endpointDistanceSum - SuspendedCordSolver.tautTolerance else {
                throw SuspendedPresentationError.cordTooShort
            }
            let firstFreeLength = freeLength * (firstDistance / endpointDistanceSum)
            let secondFreeLength = freeLength - firstFreeLength
            guard firstFreeLength.isFinite, secondFreeLength.isFinite else {
                throw SuspendedPresentationError.invalidCord
            }

            let firstSpan = try SuspendedCordSolver.solve(
                start: fixedAnchor,
                end: entryContacts[0],
                restLength: firstFreeLength
            )
            let secondSpan = try SuspendedCordSolver.solve(
                start: exitContacts[exitContacts.count - 1],
                end: fixedAnchor,
                restLength: secondFreeLength
            )
            guard firstSpan.samples.last == entryContacts[0],
                  secondSpan.samples.first == exitContacts[exitContacts.count - 1],
                  firstSpan.samples.allSatisfy(\.allFinite),
                  secondSpan.samples.allSatisfy(\.allFinite),
                  firstSpan.tangents.allSatisfy(\.allFinite),
                  secondSpan.tangents.allSatisfy(\.allFinite) else {
                throw SuspendedPresentationError.nonFiniteCurve
            }

            let centerline = firstSpan.samples
                + Array(rigidRoute.dropFirst())
                + Array(secondSpan.samples.dropFirst())
            let tangents = tangentSamples(for: centerline)
            guard centerline.count == tangents.count,
                  centerline.count >= SuspendedCordSolver.sampleCount * 2,
                  centerline.allSatisfy(\.allFinite),
                  tangents.allSatisfy(\.allFinite) else {
                throw SuspendedPresentationError.nonFiniteCurve
            }
            try SuspendedCordSolver.validateNoSelfIntersectionAllowingClosedEndpoint(centerline)
            let measuredLength = zip(centerline, centerline.dropFirst()).reduce(Float.zero) {
                $0 + simd_length($1.1 - $1.0)
            }
            let arcLength = firstSpan.arcLength + rigidLength + secondSpan.arcLength
            guard measuredLength.isFinite, arcLength.isFinite,
                  arcLength <= declaredLength + SuspendedCordSolver.tautTolerance,
                  measuredLength <= declaredLength + 0.02 else {
                throw SuspendedPresentationError.nonFiniteCurve
            }
            branches.append(SuspendedBranchSolution(
                id: branch.id,
                passageIDs: branch.passageIDs,
                spans: usesAuthoredRoute
                    ? [firstSpan.samples, rigidRoute, secondSpan.samples]
                    : [firstSpan.samples, secondSpan.samples],
                centerlineSamples: centerline,
                tangentSamples: tangents,
                arcLength: arcLength
            ))
            radii.append(Float(branch.radius))
            framingPoints.append(contentsOf: rigidRoute)
            framingPoints.append(contentsOf: centerline)
        }
        guard Set(branches.map(\.id)).count == branches.count,
              let tubeRadius = radii.max(),
              tubeRadius.isFinite, tubeRadius > 0 else {
            throw SuspendedPresentationError.invalidCord
        }
        let framing = try makeCameraFraming(pose: pose, transform: transform, points: framingPoints)
        return SuspendedTwoBranchSolvedPresentation(
            boardTransform: transform,
            fixedAnchor: fixedAnchor,
            branches: branches,
            cameraFraming: framing,
            tubeRadius: tubeRadius,
            requiredClearance: tubeRadius + additionalClearance
        )
    }

    private static func boardTransform(for pose: BoardModelCanonicalPose) throws -> simd_float4x4 {
        guard pose.rotation.count == 4,
              pose.translation.count == 3,
              pose.rotation.allSatisfy(\.isFinite),
              pose.translation.allSatisfy(\.isFinite) else {
            throw SuspendedPresentationError.invalidPose
        }
        let x = Float(pose.rotation[0])
        let y = Float(pose.rotation[1])
        let z = Float(pose.rotation[2])
        let w = Float(pose.rotation[3])
        let norm = (x * x + y * y + z * z + w * w).squareRoot()
        guard norm.isFinite else { throw SuspendedPresentationError.invalidPose }
        guard abs(norm - 1) <= 1e-6 else { throw SuspendedPresentationError.nonUnitPose }
        let matrix = simd_float4x4(columns: (
            SIMD4(1 - 2 * (y * y + z * z), 2 * (x * y + z * w), 2 * (x * z - y * w), 0),
            SIMD4(2 * (x * y - z * w), 1 - 2 * (x * x + z * z), 2 * (y * z + x * w), 0),
            SIMD4(2 * (x * z + y * w), 2 * (y * z - x * w), 1 - 2 * (x * x + y * y), 0),
            SIMD4(Float(pose.translation[0]), Float(pose.translation[1]), Float(pose.translation[2]), 1)
        ))
        guard matrix.columns.0.allFinite,
              matrix.columns.1.allFinite,
              matrix.columns.2.allFinite,
              matrix.columns.3.allFinite else {
            throw SuspendedPresentationError.invalidPose
        }
        return matrix
    }

    private static func validatedBounds(
        _ bounds: BoardModelBounds
    ) throws -> (SIMD3<Float>, SIMD3<Float>) {
        guard bounds.minimum.count == 3,
              bounds.maximum.count == 3,
              bounds.minimum.allSatisfy(\.isFinite),
              bounds.maximum.allSatisfy(\.isFinite) else {
            throw SuspendedPresentationError.invalidBounds
        }
        let minimum = SIMD3<Float>(bounds.minimum.map(Float.init))
        let maximum = SIMD3<Float>(bounds.maximum.map(Float.init))
        guard minimum.allFinite, maximum.allFinite,
              (0..<3).allSatisfy({ minimum[$0] < maximum[$0] }) else {
            throw SuspendedPresentationError.invalidBounds
        }
        return (minimum, maximum)
    }

    private static func transformPoint(
        _ transform: simd_float4x4,
        _ point: SIMD3<Float>
    ) -> SIMD3<Float> {
        let result = transform * SIMD4(point, 1)
        return SIMD3(result.x, result.y, result.z)
    }

    private static func tangentSamples(for points: [SIMD3<Float>]) -> [SIMD3<Float>] {
        points.indices.map { index in
            let previous = points[max(0, index - 1)]
            let next = points[min(points.count - 1, index + 1)]
            return normalized(next - previous) ?? SIMD3<Float>(0, 1, 0)
        }
    }

    private static func validatePairedLeadClearance(
        _ leads: [SolvedCordBranch],
        requiredClearance: Float
    ) throws {
        guard leads.count == 2,
              leads.allSatisfy({ $0.samples.count >= 2 }),
              requiredClearance.isFinite,
              requiredClearance > 0 else {
            throw SuspendedPresentationError.invalidCord
        }
        let firstPath = leads[0].samples
        let secondPath = leads[1].samples
        let sharedAnchor = firstPath[0]
        guard sharedAnchor == secondPath[0] else {
            throw SuspendedPresentationError.invalidSuspension
        }
        let clearanceSquared = requiredClearance * requiredClearance
        for (firstIndex, firstSegment) in zip(firstPath, firstPath.dropFirst()).enumerated() {
            for (secondIndex, secondSegment) in zip(secondPath, secondPath.dropFirst()).enumerated() {
                let approach = segmentClosestApproach(
                    firstSegment.0, firstSegment.1,
                    secondSegment.0, secondSegment.1
                )
                guard approach.distanceSquared.isFinite else {
                    throw SuspendedPresentationError.nonFiniteCurve
                }
                guard approach.distanceSquared < clearanceSquared else { continue }
                let firstPoint = pointOnSegment(
                    firstSegment.0,
                    firstSegment.1,
                    parameter: approach.firstParameter
                )
                let secondPoint = pointOnSegment(
                    secondSegment.0,
                    secondSegment.1,
                    parameter: approach.secondParameter
                )
                let isSharedAnchorContact = firstIndex == 0
                    && secondIndex == 0
                    && simd_length_squared(firstPoint - sharedAnchor) <= 1e-12
                    && simd_length_squared(secondPoint - sharedAnchor) <= 1e-12
                    && firstSegmentsContactOnlyAtSharedAnchor(
                        firstSegment,
                        secondSegment,
                        sharedAnchor: sharedAnchor
                    )
                // Two physical leads converge at this single authored anchor.
                // With discretized taut centerlines, their first spans remain
                // within two tube diameters for a short distance after that
                // knot. Allow only that bounded anchor neighborhood; every
                // later approach must maintain the full two-tube clearance.
                let isWithinSharedAnchorKnot = firstIndex == 0
                    && secondIndex == 0
                    && firstSegmentsContactOnlyAtSharedAnchor(
                        firstSegment,
                        secondSegment,
                        sharedAnchor: sharedAnchor
                    )
                    && simd_length(firstPoint - sharedAnchor) <= requiredClearance
                    && simd_length(secondPoint - sharedAnchor) <= requiredClearance
                if !isSharedAnchorContact && !isWithinSharedAnchorKnot {
                    throw SuspendedPresentationError.selfIntersection
                }
            }
        }
    }

    private static func firstSegmentsContactOnlyAtSharedAnchor(
        _ firstSegment: (SIMD3<Float>, SIMD3<Float>),
        _ secondSegment: (SIMD3<Float>, SIMD3<Float>),
        sharedAnchor: SIMD3<Float>
    ) -> Bool {
        guard firstSegment.0 == sharedAnchor,
              secondSegment.0 == sharedAnchor else {
            return false
        }
        let firstDirection = firstSegment.1 - firstSegment.0
        let secondDirection = secondSegment.1 - secondSegment.0
        let firstLengthSquared = simd_length_squared(firstDirection)
        let secondLengthSquared = simd_length_squared(secondDirection)
        guard firstLengthSquared > 1e-12, secondLengthSquared > 1e-12 else {
            return false
        }
        let crossLengthSquared = simd_length_squared(simd_cross(firstDirection, secondDirection))
        let collinearTolerance = 1e-10 * firstLengthSquared * secondLengthSquared
        let pointsAlongSameRay = crossLengthSquared <= collinearTolerance
            && simd_dot(firstDirection, secondDirection) > 0
        return !pointsAlongSameRay
    }

    private static func segmentClosestApproach(
        _ firstStart: SIMD3<Float>,
        _ firstEnd: SIMD3<Float>,
        _ secondStart: SIMD3<Float>,
        _ secondEnd: SIMD3<Float>
    ) -> (distanceSquared: Float, firstParameter: Float, secondParameter: Float) {
        let firstDirection = firstEnd - firstStart
        let secondDirection = secondEnd - secondStart
        let startDifference = firstStart - secondStart
        let firstLengthSquared = simd_dot(firstDirection, firstDirection)
        let directionDot = simd_dot(firstDirection, secondDirection)
        let secondLengthSquared = simd_dot(secondDirection, secondDirection)
        let firstOffset = simd_dot(firstDirection, startDifference)
        let secondOffset = simd_dot(secondDirection, startDifference)
        let denominator = firstLengthSquared * secondLengthSquared - directionDot * directionDot
        var firstNumerator: Float
        var firstDenominator = denominator
        var secondNumerator: Float
        var secondDenominator = denominator

        if denominator < 1e-12 {
            firstNumerator = 0
            firstDenominator = 1
            secondNumerator = secondOffset
            secondDenominator = secondLengthSquared
        } else {
            firstNumerator = directionDot * secondOffset - secondLengthSquared * firstOffset
            secondNumerator = firstLengthSquared * secondOffset - directionDot * firstOffset
            if firstNumerator < 0 {
                firstNumerator = 0
                secondNumerator = secondOffset
                secondDenominator = secondLengthSquared
            } else if firstNumerator > firstDenominator {
                firstNumerator = firstDenominator
                secondNumerator = secondOffset + directionDot
                secondDenominator = secondLengthSquared
            }
        }
        if secondNumerator < 0 {
            secondNumerator = 0
            if -firstOffset < 0 {
                firstNumerator = 0
            } else if -firstOffset > firstLengthSquared {
                firstNumerator = firstDenominator
            } else {
                firstNumerator = -firstOffset
                firstDenominator = firstLengthSquared
            }
        } else if secondNumerator > secondDenominator {
            secondNumerator = secondDenominator
            if -firstOffset + directionDot < 0 {
                firstNumerator = 0
            } else if -firstOffset + directionDot > firstLengthSquared {
                firstNumerator = firstDenominator
            } else {
                firstNumerator = -firstOffset + directionDot
                firstDenominator = firstLengthSquared
            }
        }
        let firstParameter = abs(firstNumerator) < 1e-12 ? 0 : firstNumerator / firstDenominator
        let secondParameter = abs(secondNumerator) < 1e-12 ? 0 : secondNumerator / secondDenominator
        let difference = startDifference + firstDirection * firstParameter - secondDirection * secondParameter
        return (simd_dot(difference, difference), firstParameter, secondParameter)
    }

    private static func pointOnSegment(
        _ start: SIMD3<Float>,
        _ end: SIMD3<Float>,
        parameter: Float
    ) -> SIMD3<Float> {
        start + (end - start) * parameter
    }

    private static func transformedBoundsCorners(
        minimum: SIMD3<Float>,
        maximum: SIMD3<Float>,
        transform: simd_float4x4
    ) -> [SIMD3<Float>] {
        [minimum.x, maximum.x].flatMap { x in
            [minimum.y, maximum.y].flatMap { y in
                [minimum.z, maximum.z].map { z in
                    transformPoint(transform, SIMD3(x, y, z))
                }
            }
        }
    }

    private static func makeCameraFraming(
        pose: BoardModelCanonicalPose,
        transform: simd_float4x4,
        minimumFitPadding: Float = 1,
        points: [SIMD3<Float>]
    ) throws -> SuspendedCameraFraming {
        guard pose.camera.viewDirection.count == 3,
              pose.camera.viewDirection.allSatisfy(\.isFinite),
              pose.camera.fitPadding.isFinite,
              pose.camera.fitPadding > 0,
              points.allSatisfy(\.allFinite) else {
            throw SuspendedPresentationError.invalidCamera
        }
        let requestedDirection = SIMD3<Float>(pose.camera.viewDirection.map(Float.init))
        // The declared direction identifies the face in the unposed model.
        // Rotate it with the board before framing the world-space route;
        // otherwise a half-turn can point the camera at the opposite face.
        let posedDirection = transform * SIMD4<Float>(requestedDirection, 0)
        guard let direction = normalized(SIMD3<Float>(posedDirection.x, posedDirection.y, posedDirection.z)) else {
            throw SuspendedPresentationError.invalidCamera
        }
        let worldUp = SIMD3<Float>(0, 1, 0)
        let fallbackUp = SIMD3<Float>(0, 0, 1)
        let requestedUp = abs(simd_dot(direction, worldUp)) > 0.999
            ? fallbackUp
            : worldUp
        guard let right = normalized(simd_cross(direction, requestedUp)),
              let up = normalized(simd_cross(right, direction)) else {
            throw SuspendedPresentationError.invalidCamera
        }
        let horizontal = points.map { simd_dot($0, right) }
        let vertical = points.map { simd_dot($0, up) }
        let depth = points.map { simd_dot($0, direction) }
        guard let minHorizontal = horizontal.min(),
              let maxHorizontal = horizontal.max(),
              let minVertical = vertical.min(),
              let maxVertical = vertical.max(),
              let minDepth = depth.min(),
              let maxDepth = depth.max() else {
            throw SuspendedPresentationError.invalidCamera
        }
        let width = maxHorizontal - minHorizontal
        let height = maxVertical - minVertical
        let depthSpan = maxDepth - minDepth
        let fitPadding = max(Float(1 + pose.camera.fitPadding * 2), minimumFitPadding)
        guard width.isFinite, height.isFinite, depthSpan.isFinite,
              width > 0, height > 0, depthSpan > 0,
              minimumFitPadding.isFinite, minimumFitPadding >= 1,
              fitPadding.isFinite else {
            throw SuspendedPresentationError.invalidCamera
        }
        let target = right * ((minHorizontal + maxHorizontal) / 2)
            + up * ((minVertical + maxVertical) / 2)
            + direction * ((minDepth + maxDepth) / 2)
        let distance = max(width, max(height, depthSpan)) * fitPadding
        guard target.allFinite, distance.isFinite, distance > 0 else {
            throw SuspendedPresentationError.invalidCamera
        }
        return SuspendedCameraFraming(
            target: target,
            direction: direction,
            viewDirection: direction,
            right: right,
            up: up,
            distance: distance,
            width: width,
            height: height,
            depth: depthSpan,
            fitPadding: fitPadding,
            includedPoints: points
        )
    }

    private static func normalized(_ vector: SIMD3<Float>) -> SIMD3<Float>? {
        let length = simd_length(vector)
        guard length.isFinite, length > 1e-7 else { return nil }
        return vector / length
    }
}

private extension SIMD3 where Scalar == Float {
    var allFinite: Bool { x.isFinite && y.isFinite && z.isFinite }
}

private extension SIMD4 where Scalar == Float {
    var allFinite: Bool { x.isFinite && y.isFinite && z.isFinite && w.isFinite }
}
