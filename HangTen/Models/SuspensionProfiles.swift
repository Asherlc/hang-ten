import Foundation
import simd

/// Failure modes for the pure suspension-profile solver. SceneKit callers
/// route every one of these to their existing unavailable state.
enum SuspendedPresentationError: Error, Equatable, LocalizedError {
    case invalidBounds, invalidPose, nonUnitPose, invalidSuspension, invalidCord
    case cordTooShort, zeroHorizontalSlack, unbracketedCatenary, nonFiniteCurve
    case selfIntersection, invalidCamera

    var errorDescription: String? {
        switch self {
        case .invalidBounds: "Suspended model bounds are invalid"
        case .invalidPose: "Suspended canonical pose is invalid"
        case .nonUnitPose: "Suspended canonical pose rotation is not unit length"
        case .invalidSuspension: "Suspension attachment or anchor is invalid"
        case .invalidCord: "Suspension cord parameters are invalid"
        case .cordTooShort: "Suspension cord is shorter than its endpoints"
        case .zeroHorizontalSlack: "Slack cord has no horizontal gravity-plane direction"
        case .unbracketedCatenary: "Suspension catenary has no finite bounded solution"
        case .nonFiniteCurve: "Suspension catenary contains a non-finite sample"
        case .selfIntersection: "Suspension catenary self-intersects"
        case .invalidCamera: "Suspended canonical camera framing is invalid"
        }
    }
}

struct SolvedCordBranch {
    let samples: [SIMD3<Float>]
    let tangents: [SIMD3<Float>]
    let arcLength: Float
    let polylineArcLength: Float
    let isTaut: Bool

    var centerlineSamples: [SIMD3<Float>] { samples }
}

struct SuspendedCameraFraming {
    let target: SIMD3<Float>
    let direction: SIMD3<Float>
    let viewDirection: SIMD3<Float>
    let right: SIMD3<Float>
    let up: SIMD3<Float>
    let distance: Float
    let width: Float
    let height: Float
    let depth: Float
    let fitPadding: Float
    let includedPoints: [SIMD3<Float>]

    func contains(_ point: SIMD3<Float>, epsilon: Float = 1e-5) -> Bool {
        guard point.allFinite else { return false }
        let relative = point - target
        return abs(simd_dot(relative, right)) <= width * fitPadding / 2 + epsilon
            && abs(simd_dot(relative, up)) <= height * fitPadding / 2 + epsilon
            && abs(simd_dot(relative, direction)) <= depth * fitPadding / 2 + epsilon
    }
}

struct SolvedSuspension {
    let boardTransform: simd_float4x4
    let fixedAnchor: SIMD3<Float>
    let transformedAttachment: SIMD3<Float>
    let cord: SolvedCordBranch
    let cameraFraming: SuspendedCameraFraming
    let tubeRadius: Float
    let requiredClearance: Float

    var transform: simd_float4x4 { boardTransform }
    var attachment: SIMD3<Float> { transformedAttachment }
    var anchor: SIMD3<Float> { fixedAnchor }
    var centerlineSamples: [SIMD3<Float>] { cord.samples }
    var tangentSamples: [SIMD3<Float>] { cord.tangents }
    var cordSamples: [SIMD3<Float>] { cord.samples }
    var cordArcLength: Float { cord.arcLength }
}

/// Pure, deterministic model-space solving for the legacy single-cord profile.
enum SuspensionProfileSolver {
    static let additionalClearance: Float = 0.001

    static func solveSingle(
        pose: BoardModelCanonicalPose,
        profile: BoardModelSingleCordSuspension,
        bounds: BoardModelBounds
    ) throws -> SolvedSuspension {
        let transform = try boardTransform(for: pose)
        let (minimum, maximum) = try validatedBounds(bounds)
        guard profile.attachment.pointInModel.count == 3,
              profile.anchor.position.count == 3,
              profile.attachment.pointInModel.allSatisfy(\.isFinite),
              profile.anchor.position.allSatisfy(\.isFinite),
              profile.anchor.visibility == "invisible" else {
            throw SuspendedPresentationError.invalidSuspension
        }
        guard profile.cord.restLength.isFinite,
              profile.cord.restLength > 0,
              profile.cord.radius.isFinite,
              profile.cord.radius > 0 else {
            throw SuspendedPresentationError.invalidCord
        }
        let modelAttachment = SIMD3<Float>(
            Float(profile.attachment.pointInModel[0]),
            Float(profile.attachment.pointInModel[1]),
            Float(profile.attachment.pointInModel[2])
        )
        let fixedAnchor = SIMD3<Float>(
            Float(profile.anchor.position[0]),
            Float(profile.anchor.position[1]),
            Float(profile.anchor.position[2])
        )
        guard modelAttachment.allFinite, fixedAnchor.allFinite else {
            throw SuspendedPresentationError.invalidSuspension
        }
        let transformedAttachment = transformPoint(transform, modelAttachment)
        guard transformedAttachment.allFinite else { throw SuspendedPresentationError.invalidPose }
        let cord = try SuspendedCordSolver.solve(
            start: fixedAnchor,
            end: transformedAttachment,
            restLength: Float(profile.cord.restLength)
        )
        let framing = try makeCameraFraming(
            pose: pose,
            points: transformedBoundsCorners(minimum: minimum, maximum: maximum, transform: transform)
                + [fixedAnchor, transformedAttachment] + cord.samples
        )
        let tubeRadius = Float(profile.cord.radius)
        guard tubeRadius.isFinite else { throw SuspendedPresentationError.invalidCord }
        return SolvedSuspension(
            boardTransform: transform,
            fixedAnchor: fixedAnchor,
            transformedAttachment: transformedAttachment,
            cord: cord,
            cameraFraming: framing,
            tubeRadius: tubeRadius,
            requiredClearance: tubeRadius + additionalClearance
        )
    }

    private static func boardTransform(for pose: BoardModelCanonicalPose) throws -> simd_float4x4 {
        guard pose.rotation.count == 4, pose.translation.count == 3,
              pose.rotation.allSatisfy(\.isFinite), pose.translation.allSatisfy(\.isFinite) else {
            throw SuspendedPresentationError.invalidPose
        }
        let x = Float(pose.rotation[0]), y = Float(pose.rotation[1])
        let z = Float(pose.rotation[2]), w = Float(pose.rotation[3])
        let norm = (x * x + y * y + z * z + w * w).squareRoot()
        guard norm.isFinite else { throw SuspendedPresentationError.invalidPose }
        guard abs(norm - 1) <= 1e-6 else { throw SuspendedPresentationError.nonUnitPose }
        let matrix = simd_float4x4(columns: (
            SIMD4(1 - 2 * (y * y + z * z), 2 * (x * y + z * w), 2 * (x * z - y * w), 0),
            SIMD4(2 * (x * y - z * w), 1 - 2 * (x * x + z * z), 2 * (y * z + x * w), 0),
            SIMD4(2 * (x * z + y * w), 2 * (y * z - x * w), 1 - 2 * (x * x + y * y), 0),
            SIMD4(Float(pose.translation[0]), Float(pose.translation[1]), Float(pose.translation[2]), 1)
        ))
        guard matrix.columns.0.allFinite, matrix.columns.1.allFinite,
              matrix.columns.2.allFinite, matrix.columns.3.allFinite else {
            throw SuspendedPresentationError.invalidPose
        }
        return matrix
    }

    private static func validatedBounds(_ bounds: BoardModelBounds) throws -> (SIMD3<Float>, SIMD3<Float>) {
        guard bounds.minimum.count == 3, bounds.maximum.count == 3,
              bounds.minimum.allSatisfy(\.isFinite), bounds.maximum.allSatisfy(\.isFinite) else {
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

    private static func transformPoint(_ transform: simd_float4x4, _ point: SIMD3<Float>) -> SIMD3<Float> {
        let result = transform * SIMD4(point, 1)
        return SIMD3(result.x, result.y, result.z)
    }

    private static func transformedBoundsCorners(
        minimum: SIMD3<Float>, maximum: SIMD3<Float>, transform: simd_float4x4
    ) -> [SIMD3<Float>] {
        [minimum.x, maximum.x].flatMap { x in
            [minimum.y, maximum.y].flatMap { y in
                [minimum.z, maximum.z].map { transformPoint(transform, SIMD3(x, y, $0)) }
            }
        }
    }

    private static func makeCameraFraming(
        pose: BoardModelCanonicalPose, points: [SIMD3<Float>]
    ) throws -> SuspendedCameraFraming {
        guard pose.camera.viewDirection.count == 3,
              pose.camera.viewDirection.allSatisfy(\.isFinite),
              pose.camera.fitPadding.isFinite, pose.camera.fitPadding > 0,
              points.allSatisfy(\.allFinite) else { throw SuspendedPresentationError.invalidCamera }
        let requestedDirection = SIMD3<Float>(pose.camera.viewDirection.map(Float.init))
        guard let direction = normalized(requestedDirection) else { throw SuspendedPresentationError.invalidCamera }
        let worldUp = SIMD3<Float>(0, 1, 0)
        let requestedUp = abs(simd_dot(direction, worldUp)) > 0.999 ? SIMD3<Float>(0, 0, 1) : worldUp
        guard let right = normalized(simd_cross(direction, requestedUp)),
              let up = normalized(simd_cross(right, direction)) else {
            throw SuspendedPresentationError.invalidCamera
        }
        let horizontal = points.map { simd_dot($0, right) }
        let vertical = points.map { simd_dot($0, up) }
        let depth = points.map { simd_dot($0, direction) }
        guard let minHorizontal = horizontal.min(), let maxHorizontal = horizontal.max(),
              let minVertical = vertical.min(), let maxVertical = vertical.max(),
              let minDepth = depth.min(), let maxDepth = depth.max() else {
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
        guard target.allFinite, distance.isFinite, distance > 0 else { throw SuspendedPresentationError.invalidCamera }
        return SuspendedCameraFraming(
            target: target, direction: direction, viewDirection: direction, right: right, up: up,
            distance: distance, width: width, height: height, depth: depthSpan,
            fitPadding: fitPadding, includedPoints: points
        )
    }

    private static func normalized(_ vector: SIMD3<Float>) -> SIMD3<Float>? {
        let length = simd_length(vector)
        guard length.isFinite, length > 1e-7 else { return nil }
        return vector / length
    }
}

enum SuspendedCordSolver {
    static let sampleCount = 32
    static let bisectionTolerance: Float = 1e-6
    static let tautTolerance: Float = 1e-5
    static let gravity = SIMD3<Float>(0, -1, 0)

    static func solve(start: SIMD3<Float>, end: SIMD3<Float>, restLength: Float) throws -> SolvedCordBranch {
        guard start.allFinite, end.allFinite, restLength.isFinite, restLength > 0 else {
            throw SuspendedPresentationError.invalidCord
        }
        let delta = end - start
        let endpointDistance = simd_length(delta)
        guard endpointDistance.isFinite else { throw SuspendedPresentationError.invalidCord }
        guard restLength >= endpointDistance - tautTolerance else { throw SuspendedPresentationError.cordTooShort }
        let isTaut = abs(restLength - endpointDistance) <= tautTolerance
        if isTaut {
            let tangent = endpointDistance > 1e-7 ? delta / endpointDistance : SIMD3<Float>(0, 1, 0)
            var samples = (0..<sampleCount).map { start + delta * (Float($0) / Float(sampleCount - 1)) }
            samples[0] = start
            samples[sampleCount - 1] = end
            return try makeSolution(samples: samples, tangents: Array(repeating: tangent, count: sampleCount), arcLength: endpointDistance, isTaut: true)
        }
        let vertical = simd_dot(delta, gravity)
        let horizontalVector = delta - gravity * vertical
        let horizontal = simd_length(horizontalVector)
        guard horizontal.isFinite, horizontal > 1e-7 else { throw SuspendedPresentationError.zeroHorizontalSlack }
        let horizontalAxis = horizontalVector / horizontal
        let horizontalArc = (restLength * restLength - vertical * vertical).squareRoot()
        guard horizontalArc.isFinite, horizontalArc > horizontal else { throw SuspendedPresentationError.unbracketedCatenary }
        let a = try solveCatenaryParameter(horizontal: horizontal, arc: horizontalArc)
        let shift = horizontal / 2 + a * Float(asinh(Double(vertical / horizontalArc)))
        let offset = a * Float(cosh(Double(shift / a)))
        var samples: [SIMD3<Float>] = []
        var tangents: [SIMD3<Float>] = []
        samples.reserveCapacity(sampleCount)
        tangents.reserveCapacity(sampleCount)
        for index in 0..<sampleCount {
            let t = Float(index) / Float(sampleCount - 1)
            let x = horizontal * t
            let argument = (x - shift) / a
            let sag = offset - a * Float(cosh(Double(argument)))
            let tangentVector = horizontalAxis + gravity * -Float(sinh(Double(argument)))
            guard sag.isFinite, tangentVector.allFinite else { throw SuspendedPresentationError.nonFiniteCurve }
            samples.append(start + horizontalAxis * x + gravity * sag)
            guard let tangent = normalized(tangentVector) else { throw SuspendedPresentationError.nonFiniteCurve }
            tangents.append(tangent)
        }
        samples[0] = start
        samples[sampleCount - 1] = end
        return try makeSolution(samples: samples, tangents: tangents, arcLength: restLength, isTaut: false)
    }

    static func solve(from start: SIMD3<Float>, to end: SIMD3<Float>, restLength: Float) throws -> SolvedCordBranch {
        try solve(start: start, end: end, restLength: restLength)
    }

    static func hasSelfIntersection(
        _ samples: [SIMD3<Float>],
        tolerance: Float = 1e-6
    ) -> Bool {
        guard samples.count >= 4 else { return false }
        for first in 0..<(samples.count - 2) {
            for second in (first + 2)..<(samples.count - 1) {
                if samples[first] == samples[second]
                    || samples[first] == samples[second + 1]
                    || samples[first + 1] == samples[second]
                    || samples[first + 1] == samples[second + 1] {
                    return true
                }
                let approach = segmentClosestApproach(
                    samples[first], samples[first + 1],
                    samples[second], samples[second + 1]
                )
                if approach.distanceSquared <= tolerance * tolerance,
                   !closestApproachTouchesOnlySegmentEndpoints(
                    approach,
                    firstStart: samples[first],
                    firstEnd: samples[first + 1],
                    secondStart: samples[second],
                    secondEnd: samples[second + 1],
                    tolerance: tolerance
                   ) {
                    return true
                }
            }
        }
        return false
    }

    static func validateNoSelfIntersection(
        _ samples: [SIMD3<Float>],
        tolerance: Float = 1e-6
    ) throws {
        guard samples.count >= 2, samples.allSatisfy(\.allFinite) else {
            throw SuspendedPresentationError.nonFiniteCurve
        }
        guard !hasSelfIntersection(samples, tolerance: tolerance) else {
            throw SuspendedPresentationError.selfIntersection
        }
    }

    /// Validates a closed branch path while allowing only its intentional
    /// anchor closure. Adjacent segments are allowed to share their passage
    /// endpoint; every other endpoint touch or segment crossing is rejected.
    static func validateNoSelfIntersectionAllowingClosedEndpoint(
        _ samples: [SIMD3<Float>],
        tolerance: Float = 1e-6
    ) throws {
        guard samples.count >= 2, samples.allSatisfy(\.allFinite) else {
            throw SuspendedPresentationError.nonFiniteCurve
        }
        guard samples.first == samples.last else {
            try validateNoSelfIntersection(samples, tolerance: tolerance)
            return
        }
        guard samples.count >= 4 else { return }
        for first in 0..<(samples.count - 2) {
            for second in (first + 2)..<(samples.count - 1) {
                let isAnchorClosure = first == 0 && second == samples.count - 2
                let sharesOnlyAnchor = isAnchorClosure
                    && samples[first] == samples[second + 1]
                    && samples[first] != samples[second]
                    && samples[first + 1] != samples[second]
                    && samples[first + 1] != samples[second + 1]
                if !sharesOnlyAnchor && (
                    samples[first] == samples[second]
                        || samples[first] == samples[second + 1]
                        || samples[first + 1] == samples[second]
                        || samples[first + 1] == samples[second + 1]
                ) {
                    throw SuspendedPresentationError.selfIntersection
                }
                let approach = segmentClosestApproach(
                    samples[first], samples[first + 1],
                    samples[second], samples[second + 1]
                )
                let isEndpointToEndpoint = closestApproachTouchesOnlySegmentEndpoints(
                    approach,
                    firstStart: samples[first],
                    firstEnd: samples[first + 1],
                    secondStart: samples[second],
                    secondEnd: samples[second + 1],
                    tolerance: tolerance
                )
                let firstClosestPoint = pointAtSegmentParameter(
                    approach.s,
                    start: samples[first],
                    end: samples[first + 1]
                )
                let secondClosestPoint = pointAtSegmentParameter(
                    approach.t,
                    start: samples[second],
                    end: samples[second + 1]
                )
                let touchesOnlyAnchor = isAnchorClosure
                    && simd_dot(
                        firstClosestPoint - samples[first],
                        firstClosestPoint - samples[first]
                    ) <= tolerance * tolerance
                    && simd_dot(
                        secondClosestPoint - samples[second + 1],
                        secondClosestPoint - samples[second + 1]
                    ) <= tolerance * tolerance
                if approach.distanceSquared <= tolerance * tolerance,
                   (!isEndpointToEndpoint || (isAnchorClosure && !touchesOnlyAnchor)) {
                    throw SuspendedPresentationError.selfIntersection
                }
                if isAnchorClosure {
                    let toleranceSquared = tolerance * tolerance
                    let finalStartDistance = pointSegmentDistanceSquared(
                        samples[second], samples[first], samples[first + 1]
                    )
                    let firstEndDistance = pointSegmentDistanceSquared(
                        samples[first + 1], samples[second], samples[second + 1]
                    )
                    if (finalStartDistance <= toleranceSquared && samples[second] != samples[first])
                        || (firstEndDistance <= toleranceSquared && samples[first + 1] != samples[first]) {
                        throw SuspendedPresentationError.selfIntersection
                    }
                }
            }
        }
    }

    private static func solveCatenaryParameter(horizontal: Float, arc: Float) throws -> Float {
        func residual(_ parameter: Float) -> Float {
            guard parameter.isFinite, parameter > 0 else { return .infinity }
            let argument = Double(horizontal / (2 * parameter))
            guard argument < 80 else { return .infinity }
            let value = 2 * parameter * Float(sinh(argument)) - arc
            return value.isFinite ? value : .infinity
        }
        var lower = max(Float.ulpOfOne * 1024, min(horizontal, arc) * 1e-6)
        var upper = max(horizontal, arc) / 2
        var lowerValue = residual(lower), upperValue = residual(upper)
        var attempts = 0
        while lowerValue < 0 && attempts < 64 { lower /= 2; lowerValue = residual(lower); attempts += 1 }
        attempts = 0
        while upperValue > 0 && attempts < 64 { upper *= 2; upperValue = residual(upper); attempts += 1 }
        guard lowerValue >= 0, upperValue <= 0, lower.isFinite, upper.isFinite else { throw SuspendedPresentationError.unbracketedCatenary }
        for _ in 0..<128 {
            let midpoint = (lower + upper) / 2
            let value = residual(midpoint)
            if value.isFinite { if value > 0 { lower = midpoint } else { upper = midpoint } } else { lower = midpoint }
            if upper - lower <= bisectionTolerance { break }
        }
        let result = (lower + upper) / 2
        guard result.isFinite, result > 0 else { throw SuspendedPresentationError.unbracketedCatenary }
        return result
    }

    private static func makeSolution(samples: [SIMD3<Float>], tangents: [SIMD3<Float>], arcLength: Float, isTaut: Bool) throws -> SolvedCordBranch {
        guard samples.count == sampleCount, tangents.count == sampleCount, arcLength.isFinite,
              samples.allSatisfy(\.allFinite), tangents.allSatisfy(\.allFinite) else { throw SuspendedPresentationError.nonFiniteCurve }
        try validateNoSelfIntersection(samples)
        let polylineArcLength = zip(samples, samples.dropFirst()).reduce(Float.zero) { $0 + simd_length($1.1 - $1.0) }
        guard polylineArcLength.isFinite else { throw SuspendedPresentationError.nonFiniteCurve }
        return SolvedCordBranch(samples: samples, tangents: tangents, arcLength: arcLength, polylineArcLength: polylineArcLength, isTaut: isTaut)
    }

    private static func normalized(_ vector: SIMD3<Float>) -> SIMD3<Float>? {
        let length = simd_length(vector)
        guard length.isFinite, length > 1e-7 else { return nil }
        return vector / length
    }

    private static func segmentClosestApproach(_ p0: SIMD3<Float>, _ p1: SIMD3<Float>, _ q0: SIMD3<Float>, _ q1: SIMD3<Float>) -> (distanceSquared: Float, s: Float, t: Float) {
        let u = p1 - p0, v = q1 - q0, w = p0 - q0
        let a = simd_dot(u, u), b = simd_dot(u, v), c = simd_dot(v, v)
        let d = simd_dot(u, w), e = simd_dot(v, w), denominator = a * c - b * b
        var sN: Float, sD = denominator, tN: Float, tD = denominator
        if denominator < 1e-12 { sN = 0; sD = 1; tN = e; tD = c }
        else { sN = b * e - c * d; tN = a * e - b * d
            if sN < 0 { sN = 0; tN = e; tD = c } else if sN > sD { sN = sD; tN = e + b; tD = c }
        }
        if tN < 0 { tN = 0; if -d < 0 { sN = 0 } else if -d > a { sN = sD } else { sN = -d; sD = a } }
        else if tN > tD { tN = tD; if -d + b < 0 { sN = 0 } else if -d + b > a { sN = sD } else { sN = -d + b; sD = a } }
        let s = abs(sN) < 1e-12 ? 0 : sN / sD
        let t = abs(tN) < 1e-12 ? 0 : tN / tD
        let difference = w + u * s - v * t
        return (simd_dot(difference, difference), s, t)
    }
    private static func pointSegmentDistanceSquared(
        _ point: SIMD3<Float>,
        _ start: SIMD3<Float>,
        _ end: SIMD3<Float>
    ) -> Float {
        let direction = end - start
        let lengthSquared = simd_dot(direction, direction)
        guard lengthSquared.isFinite, lengthSquared > 1e-12 else {
            let difference = point - start
            return simd_dot(difference, difference)
        }
        let parameter = min(max(simd_dot(point - start, direction) / lengthSquared, 0), 1)
        let difference = point - (start + direction * parameter)
        return simd_dot(difference, difference)
    }

    /// Parameter thresholds are not a safe proxy for an endpoint: a real
    /// endpoint-to-interior touch can occur arbitrarily close to an endpoint.
    /// Classify the closest points geometrically instead, so only two segment
    /// endpoints may receive the very-short-taut non-intersection allowance.
    private static func closestApproachTouchesOnlySegmentEndpoints(
        _ approach: (distanceSquared: Float, s: Float, t: Float),
        firstStart: SIMD3<Float>,
        firstEnd: SIMD3<Float>,
        secondStart: SIMD3<Float>,
        secondEnd: SIMD3<Float>,
        tolerance: Float
    ) -> Bool {
        let firstPoint = pointAtSegmentParameter(approach.s, start: firstStart, end: firstEnd)
        let secondPoint = pointAtSegmentParameter(approach.t, start: secondStart, end: secondEnd)
        return pointIsAtSegmentEndpoint(firstPoint, start: firstStart, end: firstEnd, tolerance: tolerance)
            && pointIsAtSegmentEndpoint(secondPoint, start: secondStart, end: secondEnd, tolerance: tolerance)
    }

    private static func pointAtSegmentParameter(
        _ parameter: Float,
        start: SIMD3<Float>,
        end: SIMD3<Float>
    ) -> SIMD3<Float> {
        start + (end - start) * min(max(parameter, 0), 1)
    }

    private static func pointIsAtSegmentEndpoint(
        _ point: SIMD3<Float>,
        start: SIMD3<Float>,
        end: SIMD3<Float>,
        tolerance: Float
    ) -> Bool {
        let toleranceSquared = tolerance * tolerance
        return simd_dot(point - start, point - start) <= toleranceSquared
            || simd_dot(point - end, point - end) <= toleranceSquared
    }
}

private extension SIMD3 where Scalar == Float {
    var allFinite: Bool { x.isFinite && y.isFinite && z.isFinite }
}

private extension SIMD4 where Scalar == Float {
    var allFinite: Bool { x.isFinite && y.isFinite && z.isFinite && w.isFinite }
}
