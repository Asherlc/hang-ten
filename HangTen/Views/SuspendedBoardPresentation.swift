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
    /// The caller supplies F -> B -> W. Anchors remain authored world points;
    /// solving after placement preserves world gravity even for rotated units.
    static func solveInstance(
        pose: BoardModelCanonicalPose,
        suspension: BoardModelSuspension,
        bounds: BoardModelBounds,
        transform: simd_float4x4
    ) throws -> BoardModelSolvedSuspension {
        guard (0..<4).allSatisfy({ transform[$0].allFinite }) else {
            throw SuspendedPresentationError.invalidPose
        }
        switch suspension {
        case .pairedLeadCord(let profile):
            return .pairedLead(try solve(pose: pose, suspension: profile, bounds: bounds,
                modelTransform: transform, preserveAuthoredAnchor: true))
        case .twoBranchCord(let profile):
            return .twoBranch(try solve(pose: pose, suspension: profile, bounds: bounds, modelTransform: transform))
        case .singleCord(let profile):
            guard profile.attachment.pointInModel.count == 3,
                  profile.attachment.pointInModel.allSatisfy(\.isFinite) else {
                throw SuspendedPresentationError.invalidSuspension
            }
            let (minimum, maximum) = try validatedBounds(bounds)
            let corners = transformedBoundsCorners(minimum: minimum, maximum: maximum, transform: transform)
            let worldBounds = BoardModelBounds(
                minimum: (0..<3).map { axis in Double(corners.map { $0[axis] }.min()!) },
                maximum: (0..<3).map { axis in Double(corners.map { $0[axis] }.max()!) })
            let point = transformPoint(transform, SIMD3(profile.attachment.pointInModel.map(Float.init)))
            let placed = BoardModelSingleCordSuspension(
                attachment: .init(nodeID: profile.attachment.nodeID, pointInModel: [Double(point.x), Double(point.y), Double(point.z)], provenance: profile.attachment.provenance),
                anchor: profile.anchor, cord: profile.cord, canonicalPoses: profile.canonicalPoses)
            let identityPose = BoardModelCanonicalPose(rotation: [0, 0, 0, 1], translation: [0, 0, 0], camera: pose.camera)
            let solved = try SuspensionProfileSolver.solveSingle(pose: identityPose, profile: placed, bounds: worldBounds)
            let framing = try makeCameraFraming(pose: pose, transform: transform,
                points: corners + [solved.fixedAnchor, point] + solved.cord.samples)
            return .single(SolvedSuspension(boardTransform: transform, fixedAnchor: solved.fixedAnchor,
                transformedAttachment: point, cord: solved.cord, cameraFraming: framing,
                tubeRadius: solved.tubeRadius, requiredClearance: solved.requiredClearance))
        }
    }

    private static func validateContactOverrides(_ routes: [String: [[Double]]]?, ids: Set<String>) throws {
        guard let routes else { return }
        guard Set(routes.keys) == ids,
              routes.values.allSatisfy({ route in
                  !route.isEmpty && route.allSatisfy { $0.count == 3 && $0.allSatisfy(\.isFinite) }
                      && zip(route, route.dropFirst()).allSatisfy { $0.0 != $0.1 }
              }) else { throw SuspendedPresentationError.invalidSuspension }
    }

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
        bounds: BoardModelBounds,
        modelTransform: simd_float4x4? = nil,
        preserveAuthoredAnchor: Bool = false
    ) throws -> SuspendedPairedLeadSolvedPresentation {
        let transform = try modelTransform ?? boardTransform(for: pose)
        let (minimum, maximum) = try validatedBounds(bounds)
        try validateContactOverrides(pose.cordContactPoints, ids: Set(suspension.attachments.map(\.id)))
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
                      && $0.contactPointsInModel.allSatisfy({ point in
                          point.count == 3 && point.allSatisfy(\.isFinite)
                      })
              }),
              suspension.passages.left.count == 1,
              suspension.passages.right.count == 1,
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

        var fixedAnchor = SIMD3<Float>(
            Float(suspension.anchor.position[0]),
            Float(suspension.anchor.position[1]),
            Float(suspension.anchor.position[2])
        )
        guard fixedAnchor.allFinite else {
            throw SuspendedPresentationError.invalidSuspension
        }
        func modelPoint(_ values: [Double]) -> SIMD3<Float> {
            SIMD3<Float>(Float(values[0]), Float(values[1]), Float(values[2]))
        }
        // A real cord cannot pass through the board, so the span that is not
        // hanging free is the shortest route around it. Solving that in model
        // space keeps the board an axis-aligned box; the pose transform is rigid,
        // so lengths are the same either way. The box is grown by the cord's own
        // radius because the cord bends around the lip at its own thickness.
        let cordMargin = Float(suspension.cord.radius) * 2 + additionalClearance + 0.002
        let obstacleMinimum = minimum - SIMD3<Float>(repeating: cordMargin)
        let obstacleMaximum = maximum + SIMD3<Float>(repeating: cordMargin)
        // When both bores face the same way the board hangs with its cords in
        // front of that face, so the convergence point belongs in the same plane.
        // Leaving it in the board's mid-plane would force a taut cord to detour
        // around the whole board to reach a hole on the face.
        let boreAxes = suspension.attachments.compactMap { attachment -> SIMD3<Float>? in
            guard let stubValues = attachment.contactPointsInModel.last else { return nil }
            return normalized(
                modelPoint(stubValues)
                    - modelPoint(pose.attachmentPoints?[attachment.id] ?? attachment.pointInModel)
            )
        }
        // Only reusable-instance solving opts out of legacy anchor projection;
        // explicit transforms on legacy callers retain their existing behavior.
        if !preserveAuthoredAnchor,
           boreAxes.count == suspension.attachments.count,
           let leading = boreAxes.first,
           boreAxes.allSatisfy({ simd_dot($0, leading) > 0.9 }),
           let sharedAxis = normalized(boreAxes.reduce(SIMD3<Float>.zero, +)) {
            let anchorBefore = transformPoint(simd_inverse(transform), fixedAnchor)
            let facePlane = simd_dot(sharedAxis, SIMD3<Float>(
                sharedAxis.x >= 0 ? obstacleMaximum.x : obstacleMinimum.x,
                sharedAxis.y >= 0 ? obstacleMaximum.y : obstacleMinimum.y,
                sharedAxis.z >= 0 ? obstacleMaximum.z : obstacleMinimum.z
            )) + 0.005
            let shift = facePlane - simd_dot(sharedAxis, anchorBefore)
            if shift > 0 {
                fixedAnchor = transformPoint(transform, anchorBefore + sharedAxis * shift)
            }
        }
        // A pose can stand the board on end and leave both bores on one line below
        // the convergence point. The board would swing until that point sat above
        // it, so the pull stays centred; instead the farther cord runs a little
        // proud of the nearer one, which is how two cords actually share a line.
        let boreExits: [SIMD3<Float>] = suspension.attachments.compactMap { attachment in
            guard let stubValues = attachment.contactPointsInModel.last else { return nil }
            return transformPoint(transform, modelPoint(stubValues))
        }
        var trailingLead: Int?
        if boreExits.count == 2,
           let spread = normalized(boreExits[1] - boreExits[0]),
           let toFirst = normalized(boreExits[0] - fixedAnchor),
           abs(simd_dot(spread, toFirst)) > 0.985 {
            let firstDistance = simd_length(boreExits[0] - fixedAnchor)
            let secondDistance = simd_length(boreExits[1] - fixedAnchor)
            trailingLead = firstDistance > secondDistance ? 0 : 1
        }
        let anchorInModel = transformPoint(simd_inverse(transform), fixedAnchor)
        let transformedRoutes: [[SIMD3<Float>]] = try suspension.attachments.enumerated().map { index, attachment in
            let terminal = modelPoint(pose.attachmentPoints?[attachment.id] ?? attachment.pointInModel)
            if let contacts = pose.cordContactPoints?[attachment.id] {
                return (contacts.map(modelPoint) + [terminal]).map { transformPoint(transform, $0) }
            }
            guard let stubValues = attachment.contactPointsInModel.last else {
                // Boards that publish a bare mouth with no approach stub keep the
                // plain terminal route.
                return [transformPoint(transform, terminal)]
            }
            let stub = modelPoint(stubValues)
            guard let outward = normalized(stub - terminal) else {
                throw SuspendedPresentationError.invalidSuspension
            }
            // The cord leaves along the bore's own axis, far enough out to clear
            // the board before the free span takes over.
            let boreFace = SIMD3<Float>(
                outward.x >= 0 ? obstacleMaximum.x : obstacleMinimum.x,
                outward.y >= 0 ? obstacleMaximum.y : obstacleMinimum.y,
                outward.z >= 0 ? obstacleMaximum.z : obstacleMinimum.z
            )
            let clearingStandoff = simd_dot(outward, boreFace) - simd_dot(outward, terminal) + 0.005
            let sharedLineOffset: Float = index == trailingLead ? 0.012 : 0
            let standoff = max(simd_length(stub - terminal), clearingStandoff) + sharedLineOffset
            let exit = terminal + outward * standoff
            let wraps = tautPath(
                from: anchorInModel,
                to: exit,
                minimum: obstacleMinimum,
                maximum: obstacleMaximum
            )
            return (wraps + [exit, terminal]).map { transformPoint(transform, $0) }
        }
        guard transformedRoutes.allSatisfy({ route in
                  !route.isEmpty
                        && route.allSatisfy(\.allFinite)
                        && zip(route, route.dropFirst()).allSatisfy({
                            simd_length($0.1 - $0.0) > 1e-7
                        })
              }) else {
            throw SuspendedPresentationError.invalidPose
        }
        let leads = try transformedRoutes.map { route in
            let rigidLength = zip(route, route.dropFirst()).reduce(Float.zero) {
                $0 + simd_length($1.1 - $1.0)
            }
            let freeLength = Float(suspension.cord.restLength) - rigidLength
            guard rigidLength.isFinite, freeLength.isFinite, freeLength > 0 else {
                throw SuspendedPresentationError.cordTooShort
            }
            let freeSpan = try SuspendedCordSolver.solve(
                start: fixedAnchor,
                end: route[0],
                restLength: freeLength
            )
            let samples = freeSpan.samples + Array(route.dropFirst())
            let tangents = tangentSamples(for: samples)
            let polylineLength = zip(samples, samples.dropFirst()).reduce(Float.zero) {
                $0 + simd_length($1.1 - $1.0)
            }
            let arcLength = freeSpan.arcLength + rigidLength
            guard samples.count == tangents.count,
                  samples.allSatisfy(\.allFinite),
                  tangents.allSatisfy(\.allFinite),
                  polylineLength.isFinite,
                  arcLength.isFinite,
                  arcLength <= Float(suspension.cord.restLength) + SuspendedCordSolver.tautTolerance else {
                throw SuspendedPresentationError.nonFiniteCurve
            }
            try SuspendedCordSolver.validateNoSelfIntersection(samples)
            return SolvedCordBranch(
                samples: samples,
                tangents: tangents,
                arcLength: arcLength,
                polylineArcLength: polylineLength,
                isTaut: true
            )
        }
        guard leads.count == 2,
              leads.allSatisfy({
                  $0.samples.count >= SuspendedCordSolver.sampleCount
                      && $0.samples.first == fixedAnchor
                      && $0.samples.allSatisfy(\.allFinite)
                      && $0.tangents.allSatisfy(\.allFinite)
              }),
              zip(leads, transformedRoutes).allSatisfy({ $0.0.samples.last == $0.1.last }) else {
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
                + transformedRoutes.flatMap { $0 }
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
        bounds: BoardModelBounds,
        modelTransform: simd_float4x4? = nil
    ) throws -> SuspendedTwoBranchSolvedPresentation {
        let transform = try modelTransform ?? boardTransform(for: pose)
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
        try validateContactOverrides(pose.cordContactPoints, ids: Set(allPassages.map(\.id)))
        guard pose.cordContactPoints == nil || allPassages.allSatisfy(\.isThroughBore) else {
            throw SuspendedPresentationError.invalidSuspension
        }
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
                entryContacts = (pose.cordContactPoints?[branch.passageIDs[0]] ?? branch.entryContactPoints).map {
                    transformPoint(transform, SIMD3<Float>(Float($0[0]), Float($0[1]), Float($0[2])))
                }
                contactPoints = branch.exteriorContactPoints.map {
                    transformPoint(transform, SIMD3<Float>(Float($0[0]), Float($0[1]), Float($0[2])))
                }
                exitContacts = (pose.cordContactPoints?[branch.passageIDs[1]] ?? branch.exitContactPoints).map {
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
            guard zip(rigidRoute, rigidRoute.dropFirst()).allSatisfy({
                simd_length($0.1 - $0.0) > 1e-7
            }) else { throw SuspendedPresentationError.invalidPose }
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

    /// True when the open segment passes through the box interior, so a cord
    /// laid along it would be inside the board rather than around it.
    private static func segmentEntersBox(
        _ start: SIMD3<Float>,
        _ end: SIMD3<Float>,
        minimum: SIMD3<Float>,
        maximum: SIMD3<Float>
    ) -> Bool {
        let delta = end - start
        var entry: Float = 0
        var exit: Float = 1
        for axis in 0..<3 {
            if abs(delta[axis]) < 1e-9 {
                if start[axis] <= minimum[axis] || start[axis] >= maximum[axis] { return false }
                continue
            }
            var near = (minimum[axis] - start[axis]) / delta[axis]
            var far = (maximum[axis] - start[axis]) / delta[axis]
            if near > far { swap(&near, &far) }
            entry = max(entry, near)
            exit = min(exit, far)
            if entry >= exit { return false }
        }
        return exit - entry > 1e-5
    }

    /// Shortest cord route from `start` to `end` that stays out of the box. A
    /// taut cord takes the shortest path it can reach, so the corners of the
    /// obstacle are the only places it can bend.
    private static func tautPath(
        from start: SIMD3<Float>,
        to end: SIMD3<Float>,
        minimum: SIMD3<Float>,
        maximum: SIMD3<Float>
    ) -> [SIMD3<Float>] {
        guard segmentEntersBox(start, end, minimum: minimum, maximum: maximum) else { return [] }
        var nodes = [start, end]
        for x in [minimum.x, maximum.x] {
            for y in [minimum.y, maximum.y] {
                for z in [minimum.z, maximum.z] {
                    nodes.append(SIMD3<Float>(x, y, z))
                }
            }
        }
        var best = [Float](repeating: .greatestFiniteMagnitude, count: nodes.count)
        var previous = [Int](repeating: -1, count: nodes.count)
        var settled = [Bool](repeating: false, count: nodes.count)
        best[0] = 0
        while true {
            var current = -1
            for index in nodes.indices where !settled[index] {
                if current < 0 || best[index] < best[current] { current = index }
            }
            guard current >= 0, best[current] < .greatestFiniteMagnitude, current != 1 else { break }
            settled[current] = true
            for next in nodes.indices where !settled[next] {
                guard !segmentEntersBox(
                    nodes[current], nodes[next], minimum: minimum, maximum: maximum
                ) else { continue }
                let candidate = best[current] + simd_length(nodes[next] - nodes[current])
                if candidate < best[next] {
                    best[next] = candidate
                    previous[next] = current
                }
            }
        }
        guard best[1] < .greatestFiniteMagnitude else { return [] }
        var route: [SIMD3<Float>] = []
        var cursor = 1
        while previous[cursor] > 0 {
            cursor = previous[cursor]
            route.append(nodes[cursor])
        }
        return route.reversed()
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

    static func validatePairedLeadClearance(
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
        // A paired lead may have an authored common trunk before it forks,
        // and a pair that immediately diverges can still be within tube
        // clearance for one or two discretized samples at the anchor. Both
        // are one initial topology: a contiguous prefix ending at the first
        // aligned pair that has full clearance. A pair that never reaches
        // that state is two overlapping leads, not a valid suspension.
        guard let forkIndex = firstPath.indices.first(where: {
            $0 > 0 && $0 < secondPath.count
                && simd_length_squared(firstPath[$0] - secondPath[$0]) >= clearanceSquared
        }) else {
            throw SuspendedPresentationError.selfIntersection
        }
        let firstInitialRaySegmentCount = initialStraightRaySegmentCount(
            in: firstPath,
            sharedAnchor: sharedAnchor
        )
        let secondInitialRaySegmentCount = initialStraightRaySegmentCount(
            in: secondPath,
            sharedAnchor: sharedAnchor
        )
        let hasDistinctInitialRays: Bool
        if let firstInitialDirection = normalized(firstPath[1] - sharedAnchor),
           let secondInitialDirection = normalized(secondPath[1] - sharedAnchor) {
            hasDistinctInitialRays = simd_length_squared(simd_cross(
                firstInitialDirection,
                secondInitialDirection
            )) > 1e-10
        } else {
            hasDistinctInitialRays = false
        }
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
                // Before the verified fork, both leads are one intentional
                // anchor-to-fork assembly. Once either segment is past that
                // fork, even a return to the anchor area must have the full
                // two-tube clearance.
                let isWithinInitialCommonTrunk = firstIndex < forkIndex
                    && secondIndex < forkIndex
                // The solver emits each free lead as a straight ray from the
                // shared anchor. Unequal lead lengths mean equal sample
                // indices are not equal physical distances, so the initial
                // two-tube knot can include non-adjacent segment indices.
                // Distinct straight rays can only diverge; accepting their
                // near-anchor overlap cannot mask a downstream reapproach.
                let isWithinDistinctInitialRays = hasDistinctInitialRays
                    && firstIndex < firstInitialRaySegmentCount
                    && secondIndex < secondInitialRaySegmentCount
                // Sampled leads that leave the same anchor can yield their
                // closest approach on different early segments. That contact
                // is part of the anchor knot only while both segments are in
                // their contiguous, anchor-contained prefixes. In particular,
                // do not use this exception for a later segment that returns
                // to the anchor after the leads have forked.
                let isCrossSegmentInsideInitialAnchorKnot = firstIndex != secondIndex
                    && simd_length_squared(firstPoint - sharedAnchor) <= clearanceSquared
                    && simd_length_squared(secondPoint - sharedAnchor) <= clearanceSquared
                    && isInitialAnchorKnotSegment(
                        firstIndex,
                        in: firstPath,
                        sharedAnchor: sharedAnchor,
                        clearanceSquared: clearanceSquared
                    )
                    && isInitialAnchorKnotSegment(
                        secondIndex,
                        in: secondPath,
                        sharedAnchor: sharedAnchor,
                        clearanceSquared: clearanceSquared
                    )
                if !isSharedAnchorContact
                    && !isWithinInitialCommonTrunk
                    && !isWithinDistinctInitialRays
                    && !isCrossSegmentInsideInitialAnchorKnot {
                    throw SuspendedPresentationError.selfIntersection
                }
            }
        }
    }

    private static func initialStraightRaySegmentCount(
        in path: [SIMD3<Float>],
        sharedAnchor: SIMD3<Float>
    ) -> Int {
        guard path.count >= 2,
              let direction = normalized(path[1] - sharedAnchor) else {
            return 0
        }
        var segmentCount = 0
        var previousProjection: Float = 0
        for endpoint in path.dropFirst() {
            let displacement = endpoint - sharedAnchor
            let projection = simd_dot(displacement, direction)
            let distanceFromRay = simd_length(displacement - direction * projection)
            let distanceTolerance = max(
                SuspendedCordSolver.tautTolerance,
                abs(projection) * 1e-6
            )
            guard projection.isFinite,
                  distanceFromRay.isFinite,
                  projection > previousProjection,
                  distanceFromRay <= distanceTolerance else {
                break
            }
            segmentCount += 1
            previousProjection = projection
        }
        return segmentCount
    }

    /// Returns whether a segment enters from the leading anchor knot. Every
    /// preceding sample through the segment's start must remain inside the
    /// knot; the caller separately verifies that the closest contact itself
    /// is inside it. This permits the contact portion of the one segment that
    /// exits the knot, without allowing a re-entry after a real fork.
    private static func isInitialAnchorKnotSegment(
        _ segmentIndex: Int,
        in path: [SIMD3<Float>],
        sharedAnchor: SIMD3<Float>,
        clearanceSquared: Float
    ) -> Bool {
        guard segmentIndex >= 0, segmentIndex + 1 < path.count else {
            return false
        }
        return path.prefix(segmentIndex + 1).allSatisfy {
            simd_length_squared($0 - sharedAnchor) <= clearanceSquared
        }
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

    private static func firstSegmentsContactOnlyAtSharedAnchor(
        _ firstSegment: (SIMD3<Float>, SIMD3<Float>),
        _ secondSegment: (SIMD3<Float>, SIMD3<Float>),
        sharedAnchor: SIMD3<Float>
    ) -> Bool {
        let firstDirection = firstSegment.1 - firstSegment.0
        let secondDirection = secondSegment.1 - secondSegment.0
        let firstLengthSquared = simd_length_squared(firstDirection)
        let secondLengthSquared = simd_length_squared(secondDirection)
        guard firstSegment.0 == sharedAnchor,
              secondSegment.0 == sharedAnchor,
              firstLengthSquared.isFinite,
              secondLengthSquared.isFinite,
              firstLengthSquared > 1e-12,
              secondLengthSquared > 1e-12 else {
            return false
        }

        // Non-collinear rays intersect only at their shared origin. Collinear
        // rays are deliberately excluded so a same-ray pair cannot masquerade
        // as a valid fork.
        return simd_length_squared(simd_cross(firstDirection, secondDirection))
            > 1e-12 * firstLengthSquared * secondLengthSquared
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
