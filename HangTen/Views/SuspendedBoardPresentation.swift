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


enum SuspendedBoardPresentation {
    static let additionalClearance: Float = 0.001

    static func solve(
        pose: BoardModelCanonicalPose,
        suspension: BoardModelSuspension,
        bounds: BoardModelBounds
    ) throws -> SuspendedSolvedPresentation {

        let profile: BoardModelSingleCordSuspension
        switch suspension {
        case .singleCord(let single):
            profile = single
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
                  $0.pointInModel.count == 3 &&
                  $0.pointInModel.allSatisfy(\.isFinite) &&
                  zip($0.pointInModel, bounds.minimum).allSatisfy({ $0 >= $1 }) &&
                  zip($0.pointInModel, bounds.maximum).allSatisfy({ $0 <= $1 })
              }) else {
            throw SuspendedPresentationError.invalidSuspension
        }
        let passagesByID = Dictionary(uniqueKeysWithValues: allPassages.map { passage in
            (passage.id, SIMD3<Float>(
                Float(passage.pointInModel[0]),
                Float(passage.pointInModel[1]),
                Float(passage.pointInModel[2])
            ))
        })
        guard passagesByID.values.allSatisfy(\.allFinite) else {
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
            guard let firstModelPoint = passagesByID[branch.passageIDs[0]],
                  let secondModelPoint = passagesByID[branch.passageIDs[1]] else {
                throw SuspendedPresentationError.invalidSuspension
            }
            let first = transformPoint(transform, firstModelPoint)
            let second = transformPoint(transform, secondModelPoint)
            guard first.allFinite, second.allFinite else {
                throw SuspendedPresentationError.invalidPose
            }
            let interiorVector = second - first
            let interiorLength = simd_length(interiorVector)
            guard interiorLength.isFinite, interiorLength > 1e-7,
                  let interiorTangent = normalized(interiorVector) else {
                throw SuspendedPresentationError.invalidSuspension
            }

            let firstDistance = simd_length(first - fixedAnchor)
            let secondDistance = simd_length(fixedAnchor - second)
            guard firstDistance.isFinite, secondDistance.isFinite,
                  firstDistance > 1e-7, secondDistance > 1e-7 else {
                throw SuspendedPresentationError.invalidCord
            }
            let minimumRouteLength = firstDistance + interiorLength + secondDistance
            let declaredLength = Float(branch.restLength)
            guard declaredLength.isFinite,
                  declaredLength >= minimumRouteLength - SuspendedCordSolver.tautTolerance else {
                throw SuspendedPresentationError.cordTooShort
            }

            // Reserve the exact modeled passage route, then distribute the
            // remaining free-cord length in proportion to the two endpoint
            // separations. This is deterministic and preserves the declared
            // total branch length without inventing knot geometry.
            let freeLength = declaredLength - interiorLength
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
                end: first,
                restLength: firstFreeLength
            )
            let secondSpan = try SuspendedCordSolver.solve(
                start: second,
                end: fixedAnchor,
                restLength: secondFreeLength
            )
            guard firstSpan.samples.last == first,
                  secondSpan.samples.first == second,
                  firstSpan.samples.allSatisfy(\.allFinite),
                  secondSpan.samples.allSatisfy(\.allFinite),
                  firstSpan.tangents.allSatisfy(\.allFinite),
                  secondSpan.tangents.allSatisfy(\.allFinite) else {
                throw SuspendedPresentationError.nonFiniteCurve
            }

            let centerline = firstSpan.samples + [second] + Array(secondSpan.samples.dropFirst())
            let tangents = firstSpan.tangents + [interiorTangent] + Array(secondSpan.tangents.dropFirst())
            guard centerline.count == tangents.count,
                  centerline.count == SuspendedCordSolver.sampleCount * 2,
                  centerline.allSatisfy(\.allFinite),
                  tangents.allSatisfy(\.allFinite) else {
                throw SuspendedPresentationError.nonFiniteCurve
            }
            try SuspendedCordSolver.validateNoSelfIntersectionAllowingClosedEndpoint(centerline)
            let measuredLength = zip(centerline, centerline.dropFirst()).reduce(Float.zero) {
                $0 + simd_length($1.1 - $1.0)
            }
            let arcLength = firstSpan.arcLength + interiorLength + secondSpan.arcLength
            guard measuredLength.isFinite, arcLength.isFinite,
                  abs(arcLength - declaredLength) <= 1e-4,
                  abs(measuredLength - declaredLength) <= 0.02 else {
                throw SuspendedPresentationError.nonFiniteCurve
            }
            branches.append(SuspendedBranchSolution(
                id: branch.id,
                passageIDs: branch.passageIDs,
                spans: [firstSpan.samples, secondSpan.samples],
                centerlineSamples: centerline,
                tangentSamples: tangents,
                arcLength: arcLength
            ))
            radii.append(Float(branch.radius))
            framingPoints.append(contentsOf: [first, second])
            framingPoints.append(contentsOf: centerline)
        }
        guard Set(branches.map(\.id)).count == branches.count,
              let tubeRadius = radii.max(),
              tubeRadius.isFinite, tubeRadius > 0 else {
            throw SuspendedPresentationError.invalidCord
        }
        let framing = try makeCameraFraming(pose: pose, points: framingPoints)
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
        guard let direction = normalized(requestedDirection) else {
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
        let fitPadding = Float(1 + pose.camera.fitPadding * 2)
        guard width.isFinite, height.isFinite, depthSpan.isFinite,
              width > 0, height > 0, depthSpan > 0, fitPadding.isFinite else {
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
