import SwiftUI

struct BoardRoutedCordTensionSpan: Equatable {
    let groupID: String
    let layer: BoardRoutedCordLayer
    let bodyPortID: String
    let worldPortID: String
    let bodyPoint: CGPoint
    let worldPoint: CGPoint

    var path: Path {
        var path = Path()
        path.move(to: worldPoint)
        path.addLine(to: bodyPoint)
        return path
    }
}

struct BoardResolvedRoutedCordPath {
    let id: String
    let space: BoardRoutedCordSpace
    let layer: BoardRoutedCordLayer
    let path: Path
    let definingPoints: [CGPoint]
}

struct BoardResolvedRoutedCordRadialLip {
    let bodyPortID: String
    let center: CGPoint
    let toward: CGPoint
    let radius: CGFloat
    let chordOffset: CGFloat
    let path: Path
}

struct BoardResolvedRoutedCordFacePatch {
    let path: Path
    let definingPoints: [CGPoint]
}

struct BoardRoutedCordRigGeometry {
    let sceneRect: CGRect
    let sourceRect: CGRect
    let faceRect: CGRect
    let faceTransform: CGAffineTransform
    let scale: CGFloat
    let portPoints: [String: CGPoint]
    let spans: [BoardRoutedCordTensionSpan]
    let paths: [BoardResolvedRoutedCordPath]
    let radialLips: [BoardResolvedRoutedCordRadialLip]
    let facePatches: [BoardResolvedRoutedCordFacePatch]

    static func resolve(
        rig: BoardRoutedCordRig,
        projection: BoardPresentationGeometryProjection,
        in canvas: CGRect
    ) -> BoardRoutedCordRigGeometry? {
        let canonicalSceneSize = rig.sceneSize.cgSize
        guard canonicalSceneSize.width.isFinite,
              canonicalSceneSize.height.isFinite,
              canonicalSceneSize.width > 0,
              canonicalSceneSize.height > 0,
              canvas.width.isFinite,
              canvas.height.isFinite,
              canvas.width > 0,
              canvas.height > 0 else {
            return nil
        }

        let scale = min(
            canvas.width / canonicalSceneSize.width,
            canvas.height / canonicalSceneSize.height
        )
        guard scale.isFinite, scale > 0 else { return nil }

        let sceneRect = CGRect(
            x: canvas.midX - canonicalSceneSize.width * scale / 2,
            y: canvas.midY - canonicalSceneSize.height * scale / 2,
            width: canonicalSceneSize.width * scale,
            height: canonicalSceneSize.height * scale
        )

        func scenePoint(_ point: CGPoint) -> CGPoint {
            CGPoint(
                x: sceneRect.minX + point.x * scale,
                y: sceneRect.minY + point.y * scale
            )
        }

        func mappedSceneRect(_ rect: CGRect) -> CGRect {
            CGRect(
                x: sceneRect.minX + rect.minX * scale,
                y: sceneRect.minY + rect.minY * scale,
                width: rect.width * scale,
                height: rect.height * scale
            )
        }

        let canonicalSourceFrame = rig.sourceFrame.cgRect
        let sourceRect = mappedSceneRect(canonicalSourceFrame)
        let canonicalInnerFaceFrame = rig.innerFaceFrame.cgRect
        let faceRect = CGRect(
            x: sourceRect.minX + canonicalInnerFaceFrame.minX * scale,
            y: sourceRect.minY + canonicalInnerFaceFrame.minY * scale,
            width: canonicalInnerFaceFrame.width * scale,
            height: canonicalInnerFaceFrame.height * scale
        )
        let bodyTransform = projection.affineTransform(in: sceneRect)

        func resolvedPoint(
            _ point: BoardCordPoint,
            space: BoardRoutedCordSpace
        ) -> CGPoint {
            let untransformed = scenePoint(
                CGPoint(
                    x: canonicalSourceFrame.minX + point.x,
                    y: canonicalSourceFrame.minY + point.y
                )
            )
            switch space {
            case .body:
                return untransformed.applying(bodyTransform)
            case .world:
                return untransformed
            }
        }

        let portPoints = Dictionary(
            uniqueKeysWithValues: rig.ports.map {
                ($0.id, resolvedPoint($0.point, space: $0.space))
            }
        )

        struct OrderedPort {
            let id: String
            let point: CGPoint
            let declarationIndex: Int
        }

        func ports(
            with ids: [String],
            pairing: BoardRoutedCordPairing
        ) -> [OrderedPort]? {
            var resolved: [OrderedPort] = []
            for (index, id) in ids.enumerated() {
                guard let point = portPoints[id] else { return nil }
                resolved.append(
                    OrderedPort(id: id, point: point, declarationIndex: index)
                )
            }
            guard pairing == .screenOrder else { return resolved }
            return resolved.sorted { lhs, rhs in
                if lhs.point.x != rhs.point.x { return lhs.point.x < rhs.point.x }
                if lhs.point.y != rhs.point.y { return lhs.point.y < rhs.point.y }
                return lhs.declarationIndex < rhs.declarationIndex
            }
        }

        var spans: [BoardRoutedCordTensionSpan] = []
        for group in rig.tensionGroups {
            guard let bodyPorts = ports(with: group.bodyPortIDs, pairing: group.pairing),
                  let worldPorts = ports(with: group.worldPortIDs, pairing: group.pairing),
                  bodyPorts.count == worldPorts.count else {
                return nil
            }
            for (bodyPort, worldPort) in zip(bodyPorts, worldPorts) {
                spans.append(
                    BoardRoutedCordTensionSpan(
                        groupID: group.id,
                        layer: group.layer,
                        bodyPortID: bodyPort.id,
                        worldPortID: worldPort.id,
                        bodyPoint: bodyPort.point,
                        worldPoint: worldPort.point
                    )
                )
            }
        }

        func resolvedPath(
            commands: [BoardRoutedCordPathCommand],
            space: BoardRoutedCordSpace
        ) -> (path: Path, definingPoints: [CGPoint]) {
            var path = Path()
            var definingPoints: [CGPoint] = []
            for command in commands {
                switch command {
                case .move(let to):
                    let point = resolvedPoint(to, space: space)
                    definingPoints.append(point)
                    path.move(to: point)
                case .line(let to):
                    let point = resolvedPoint(to, space: space)
                    definingPoints.append(point)
                    path.addLine(to: point)
                case .quad(let control, let to):
                    let resolvedControl = resolvedPoint(control, space: space)
                    let resolvedTo = resolvedPoint(to, space: space)
                    definingPoints.append(contentsOf: [resolvedControl, resolvedTo])
                    path.addQuadCurve(to: resolvedTo, control: resolvedControl)
                case .curve(let control1, let control2, let to):
                    let resolvedControl1 = resolvedPoint(control1, space: space)
                    let resolvedControl2 = resolvedPoint(control2, space: space)
                    let resolvedTo = resolvedPoint(to, space: space)
                    definingPoints.append(
                        contentsOf: [resolvedControl1, resolvedControl2, resolvedTo]
                    )
                    path.addCurve(
                        to: resolvedTo,
                        control1: resolvedControl1,
                        control2: resolvedControl2
                    )
                case .close:
                    path.closeSubpath()
                }
            }
            return (path, definingPoints)
        }

        let paths = rig.paths.map { authoredPath -> BoardResolvedRoutedCordPath in
            let resolved = resolvedPath(
                commands: authoredPath.commands,
                space: authoredPath.space
            )
            return BoardResolvedRoutedCordPath(
                id: authoredPath.id,
                space: authoredPath.space,
                layer: authoredPath.layer,
                path: resolved.path,
                definingPoints: resolved.definingPoints
            )
        }

        var radialLips: [BoardResolvedRoutedCordRadialLip] = []
        var facePatches: [BoardResolvedRoutedCordFacePatch] = []
        for occlusion in rig.occlusions {
            switch occlusion {
            case .radialLip(let lip):
                guard let incidentSpan = spans.first(where: {
                    $0.bodyPortID == lip.bodyPortID
                }) else {
                    return nil
                }
                let radius = lip.radius * scale * projection.geometryScale
                let chordOffset = lip.chordOffset * scale * projection.geometryScale
                radialLips.append(
                    BoardResolvedRoutedCordRadialLip(
                        bodyPortID: lip.bodyPortID,
                        center: incidentSpan.bodyPoint,
                        toward: incidentSpan.worldPoint,
                        radius: radius,
                        chordOffset: chordOffset,
                        path: radialLipPath(
                            center: incidentSpan.bodyPoint,
                            toward: incidentSpan.worldPoint,
                            radius: radius,
                            chordOffset: chordOffset
                        )
                    )
                )
            case .facePatch(let patch):
                let resolved = resolvedPath(commands: patch.commands, space: .body)
                facePatches.append(
                    BoardResolvedRoutedCordFacePatch(
                        path: resolved.path,
                        definingPoints: resolved.definingPoints
                    )
                )
            }
        }

        return BoardRoutedCordRigGeometry(
            sceneRect: sceneRect,
            sourceRect: sourceRect,
            faceRect: faceRect,
            faceTransform: bodyTransform,
            scale: scale,
            portPoints: portPoints,
            spans: spans,
            paths: paths,
            radialLips: radialLips,
            facePatches: facePatches
        )
    }

    func tensionSpans(in layer: BoardRoutedCordLayer) -> [BoardRoutedCordTensionSpan] {
        spans.filter { $0.layer == layer }
    }

    func renderableTensionPaths(in layer: BoardRoutedCordLayer) -> [Path] {
        let tolerance = max(sceneRect.width, sceneRect.height) * 1e-9
        var clusters: [(
            groupID: String,
            worldPoint: CGPoint,
            spans: [BoardRoutedCordTensionSpan]
        )] = []

        for span in tensionSpans(in: layer) {
            if let index = clusters.firstIndex(where: { cluster in
                guard cluster.groupID == span.groupID else { return false }
                return hypot(
                    cluster.worldPoint.x - span.worldPoint.x,
                    cluster.worldPoint.y - span.worldPoint.y
                ) <= tolerance
            }) {
                clusters[index].spans.append(span)
            } else {
                clusters.append((span.groupID, span.worldPoint, [span]))
            }
        }

        return clusters.map { cluster in
            guard cluster.spans.count > 1 else {
                return cluster.spans[0].path
            }
            let count = CGFloat(cluster.spans.count)
            let apex = CGPoint(
                x: cluster.spans.reduce(0) { $0 + $1.worldPoint.x } / count,
                y: cluster.spans.reduce(0) { $0 + $1.worldPoint.y } / count
            )

            var path = Path()
            path.move(to: cluster.spans[0].bodyPoint)
            path.addLine(to: apex)
            for (index, span) in cluster.spans.dropFirst().enumerated() {
                path.addLine(to: span.bodyPoint)
                if index < cluster.spans.count - 2 {
                    path.addLine(to: apex)
                }
            }
            return path
        }
    }

    func authoredPaths(in layer: BoardRoutedCordLayer) -> [BoardResolvedRoutedCordPath] {
        paths.filter { $0.layer == layer }
    }

    private static func radialLipPath(
        center: CGPoint,
        toward: CGPoint,
        radius: CGFloat,
        chordOffset: CGFloat
    ) -> Path {
        let deltaX = toward.x - center.x
        let deltaY = toward.y - center.y
        let length = sqrt(deltaX * deltaX + deltaY * deltaY)
        guard length.isFinite,
              length > 0,
              radius.isFinite,
              chordOffset.isFinite,
              radius > chordOffset,
              chordOffset > 0 else {
            return Path()
        }

        let unitX = deltaX / length
        let unitY = deltaY / length
        let normalX = -unitY
        let normalY = unitX
        let halfChord = sqrt(radius * radius - chordOffset * chordOffset)
        let start = CGPoint(
            x: center.x + chordOffset * unitX + halfChord * normalX,
            y: center.y + chordOffset * unitY + halfChord * normalY
        )
        let end = CGPoint(
            x: center.x + chordOffset * unitX - halfChord * normalX,
            y: center.y + chordOffset * unitY - halfChord * normalY
        )

        var path = Path()
        path.move(to: start)
        path.addArc(
            center: center,
            radius: radius,
            startAngle: .radians(Double(atan2(start.y - center.y, start.x - center.x))),
            endAngle: .radians(Double(atan2(end.y - center.y, end.x - center.x))),
            clockwise: false
        )
        path.closeSubpath()
        return path
    }
}

enum BoardRoutedCordPresentationValidationFailure: Equatable {
    case unresolvedGeometry
    case centerlineOutsideScene
    case facePatchOutsideScene
    case radialLipOutsideScene
    case bodyNotBelowWorld(bodyPortID: String, worldPortID: String)
}

enum BoardRoutedCordPresentationValidation {
    static func failure(
        for rig: BoardRoutedCordRig,
        rotationDegrees: Double,
        rotationAnchor: BoardGeometryRotationAnchor,
        geometryScale: Double = 1
    ) -> BoardRoutedCordPresentationValidationFailure? {
        let canvas = CGRect(origin: .zero, size: rig.sceneSize.cgSize)
        guard let geometry = BoardRoutedCordRigGeometry.resolve(
            rig: rig,
            projection: BoardPresentationGeometryProjection(
                rotationDegrees: CGFloat(rotationDegrees),
                geometryScale: CGFloat(geometryScale),
                rotationAnchor: rotationAnchor
            ),
            in: canvas
        ) else {
            return .unresolvedGeometry
        }

        let tolerance = max(geometry.sceneRect.width, geometry.sceneRect.height) * 1e-9
        let styleInset = 0.8 * rig.style.diameter * geometry.scale

        func contains(_ point: CGPoint, inset: CGFloat) -> Bool {
            point.x >= geometry.sceneRect.minX + inset - tolerance
                && point.y >= geometry.sceneRect.minY + inset - tolerance
                && point.x <= geometry.sceneRect.maxX - inset + tolerance
                && point.y <= geometry.sceneRect.maxY - inset + tolerance
        }

        for span in geometry.spans {
            guard contains(span.bodyPoint, inset: styleInset),
                  contains(span.worldPoint, inset: styleInset) else {
                return .centerlineOutsideScene
            }
        }
        for path in geometry.paths {
            guard path.definingPoints.allSatisfy({ contains($0, inset: styleInset) }) else {
                return .centerlineOutsideScene
            }
        }
        for patch in geometry.facePatches {
            guard patch.definingPoints.allSatisfy({ contains($0, inset: 0) }) else {
                return .facePatchOutsideScene
            }
        }
        for lip in geometry.radialLips {
            guard lip.center.x - lip.radius >= geometry.sceneRect.minX - tolerance,
                  lip.center.y - lip.radius >= geometry.sceneRect.minY - tolerance,
                  lip.center.x + lip.radius <= geometry.sceneRect.maxX + tolerance,
                  lip.center.y + lip.radius <= geometry.sceneRect.maxY + tolerance else {
                return .radialLipOutsideScene
            }
        }
        for span in geometry.spans {
            guard span.bodyPoint.y > span.worldPoint.y + tolerance else {
                return .bodyNotBelowWorld(
                    bodyPortID: span.bodyPortID,
                    worldPortID: span.worldPortID
                )
            }
        }
        return nil
    }
}

enum BoardExternalSlidingLoopCordPresentationValidationFailure: Equatable {
    case unresolvedGeometry
    case centerlineOutsideScene
    case pullInsideContactShape
    case pullNotAboveContactShape
}

struct BoardExternalSlidingLoopCordRigGeometry {
    let sceneRect: CGRect
    let sourceRect: CGRect
    let faceRect: CGRect
    let faceTransform: CGAffineTransform
    let scale: CGFloat
    let pullPoint: CGPoint
    let contactPoints: [CGPoint]
    let returnPoints: [CGPoint]
    let tensionPath: Path
    let returnPath: Path

    private static let cornerSteps = 24

    private struct Placement {
        let sceneRect: CGRect
        let sourceRect: CGRect
        let faceRect: CGRect
        let faceTransform: CGAffineTransform
        let scale: CGFloat
        let center: CGPoint
        let pullPoint: CGPoint
        let halfWidth: CGFloat
        let halfHeight: CGFloat
        let radius: CGFloat
        let coreHalfWidth: CGFloat
        let coreHalfHeight: CGFloat
        let radians: CGFloat
        let extentX: CGFloat
        let extentY: CGFloat
    }

    static func resolve(
        rig: BoardExternalSlidingLoopCordRig,
        projection: BoardPresentationGeometryProjection,
        in canvas: CGRect
    ) -> BoardExternalSlidingLoopCordRigGeometry? {
        guard let placement = placement(rig: rig, projection: projection, in: canvas),
              pullIsOutsideContactShape(placement),
              placement.pullPoint.y < placement.center.y - placement.extentY else {
            return nil
        }
        let boundary = roundedRectangleBoundary(placement)
        guard boundary.count >= 4 else { return nil }

        let centerDirection = atan2(
            placement.center.y - placement.pullPoint.y,
            placement.center.x - placement.pullPoint.x
        )
        let angularOffsets = boundary.map { point in
            normalizedAngleDifference(
                atan2(point.y - placement.pullPoint.y, point.x - placement.pullPoint.x),
                reference: centerDirection
            )
        }
        guard let firstIndex = angularOffsets.indices.min(by: {
            angularOffsets[$0] < angularOffsets[$1]
        }), let secondIndex = angularOffsets.indices.max(by: {
            angularOffsets[$0] < angularOffsets[$1]
        }), firstIndex != secondIndex,
              angularOffsets[secondIndex] - angularOffsets[firstIndex] < .pi else {
            return nil
        }

        let orderedIndexes = [firstIndex, secondIndex].sorted { lhs, rhs in
            let left = boundary[lhs]
            let right = boundary[rhs]
            return left.x == right.x ? left.y < right.y : left.x < right.x
        }
        let leftIndex = orderedIndexes[0]
        let rightIndex = orderedIndexes[1]
        let forwardArc = cyclicBoundaryArc(
            boundary,
            startIndex: leftIndex,
            endIndex: rightIndex,
            step: 1
        )
        let backwardArc = cyclicBoundaryArc(
            boundary,
            startIndex: leftIndex,
            endIndex: rightIndex,
            step: -1
        )
        guard forwardArc.count >= 2, backwardArc.count >= 2 else { return nil }
        let forwardScore = arcScore(forwardArc)
        let backwardScore = arcScore(backwardArc)
        let returnPoints = forwardScore.maximumY > backwardScore.maximumY
            || (forwardScore.maximumY == backwardScore.maximumY
                && forwardScore.averageY >= backwardScore.averageY)
            ? forwardArc
            : backwardArc
        let contactPoints = [boundary[leftIndex], boundary[rightIndex]]
        let tensionPath = path(through: [
            contactPoints[0], placement.pullPoint, contactPoints[1],
        ])

        return BoardExternalSlidingLoopCordRigGeometry(
            sceneRect: placement.sceneRect,
            sourceRect: placement.sourceRect,
            faceRect: placement.faceRect,
            faceTransform: placement.faceTransform,
            scale: placement.scale,
            pullPoint: placement.pullPoint,
            contactPoints: contactPoints,
            returnPoints: returnPoints,
            tensionPath: tensionPath,
            returnPath: path(through: returnPoints)
        )
    }

    static func validationFailure(
        for rig: BoardExternalSlidingLoopCordRig,
        projection: BoardPresentationGeometryProjection,
        in canvas: CGRect
    ) -> BoardExternalSlidingLoopCordPresentationValidationFailure? {
        guard let placement = placement(rig: rig, projection: projection, in: canvas) else {
            return .unresolvedGeometry
        }
        let tolerance = max(placement.sceneRect.width, placement.sceneRect.height) * 1e-9
        let styleInset = 0.8 * rig.style.diameter * placement.scale
        guard placement.pullPoint.x >= placement.sceneRect.minX + styleInset - tolerance,
              placement.pullPoint.y >= placement.sceneRect.minY + styleInset - tolerance,
              placement.pullPoint.x <= placement.sceneRect.maxX - styleInset + tolerance,
              placement.pullPoint.y <= placement.sceneRect.maxY - styleInset + tolerance,
              placement.center.x - placement.extentX >= placement.sceneRect.minX + styleInset - tolerance,
              placement.center.y - placement.extentY >= placement.sceneRect.minY + styleInset - tolerance,
              placement.center.x + placement.extentX <= placement.sceneRect.maxX - styleInset + tolerance,
              placement.center.y + placement.extentY <= placement.sceneRect.maxY - styleInset + tolerance else {
            return .centerlineOutsideScene
        }
        guard pullIsOutsideContactShape(placement, tolerance: tolerance) else {
            return .pullInsideContactShape
        }
        guard placement.pullPoint.y < placement.center.y - placement.extentY - tolerance else {
            return .pullNotAboveContactShape
        }
        guard resolve(rig: rig, projection: projection, in: canvas) != nil else {
            return .unresolvedGeometry
        }
        return nil
    }

    private static func placement(
        rig: BoardExternalSlidingLoopCordRig,
        projection: BoardPresentationGeometryProjection,
        in canvas: CGRect
    ) -> Placement? {
        guard BoardExternalSlidingLoopCordRigValidation.failureReason(for: rig) == nil else {
            return nil
        }
        let canonicalSceneSize = rig.sceneSize.cgSize
        guard canonicalSceneSize.width.isFinite,
              canonicalSceneSize.height.isFinite,
              canonicalSceneSize.width > 0,
              canonicalSceneSize.height > 0,
              canvas.width.isFinite,
              canvas.height.isFinite,
              canvas.width > 0,
              canvas.height > 0,
              projection.geometryScale.isFinite,
              projection.geometryScale > 0 else {
            return nil
        }
        let scale = min(
            canvas.width / canonicalSceneSize.width,
            canvas.height / canonicalSceneSize.height
        )
        guard scale.isFinite, scale > 0 else { return nil }
        let sceneRect = CGRect(
            x: canvas.midX - canonicalSceneSize.width * scale / 2,
            y: canvas.midY - canonicalSceneSize.height * scale / 2,
            width: canonicalSceneSize.width * scale,
            height: canonicalSceneSize.height * scale
        )
        func scenePoint(_ point: CGPoint) -> CGPoint {
            CGPoint(
                x: sceneRect.minX + point.x * scale,
                y: sceneRect.minY + point.y * scale
            )
        }
        func mappedSceneRect(_ rect: CGRect) -> CGRect {
            CGRect(
                x: sceneRect.minX + rect.minX * scale,
                y: sceneRect.minY + rect.minY * scale,
                width: rect.width * scale,
                height: rect.height * scale
            )
        }

        let canonicalSourceFrame = rig.sourceFrame.cgRect
        let sourceRect = mappedSceneRect(canonicalSourceFrame)
        let faceFrame = rig.innerFaceFrame.cgRect
        let faceRect = CGRect(
            x: sourceRect.minX + faceFrame.minX * scale,
            y: sourceRect.minY + faceFrame.minY * scale,
            width: faceFrame.width * scale,
            height: faceFrame.height * scale
        )
        let faceTransform = projection.affineTransform(in: sceneRect)
        let bodyFrame = rig.bodyContactFrame.cgRect
        let untransformedCenter = scenePoint(CGPoint(
            x: canonicalSourceFrame.minX + bodyFrame.midX,
            y: canonicalSourceFrame.minY + bodyFrame.midY
        ))
        let center = untransformedCenter.applying(faceTransform)
        let pullPoint = scenePoint(CGPoint(
            x: canonicalSourceFrame.minX + rig.pullPoint.x,
            y: canonicalSourceFrame.minY + rig.pullPoint.y
        ))
        let centerlineOffset = (rig.style.diameter / 2 + rig.clearance) * scale
        let halfWidth = bodyFrame.width * scale * projection.geometryScale / 2
            + centerlineOffset
        let halfHeight = bodyFrame.height * scale * projection.geometryScale / 2
            + centerlineOffset
        let radius = rig.cornerRadius * scale * projection.geometryScale
            + centerlineOffset
        let coreHalfWidth = halfWidth - radius
        let coreHalfHeight = halfHeight - radius
        let radians = atan2(faceTransform.b, faceTransform.a)
        let extentX = abs(cos(radians)) * coreHalfWidth
            + abs(sin(radians)) * coreHalfHeight + radius
        let extentY = abs(sin(radians)) * coreHalfWidth
            + abs(cos(radians)) * coreHalfHeight + radius
        let values = [
            center.x, center.y, pullPoint.x, pullPoint.y, halfWidth, halfHeight,
            radius, coreHalfWidth, coreHalfHeight, radians, extentX, extentY,
        ]
        guard values.allSatisfy(\.isFinite),
              halfWidth > 0,
              halfHeight > 0,
              radius >= 0,
              radius <= min(halfWidth, halfHeight),
              coreHalfWidth >= 0,
              coreHalfHeight >= 0 else {
            return nil
        }
        return Placement(
            sceneRect: sceneRect,
            sourceRect: sourceRect,
            faceRect: faceRect,
            faceTransform: faceTransform,
            scale: scale,
            center: center,
            pullPoint: pullPoint,
            halfWidth: halfWidth,
            halfHeight: halfHeight,
            radius: radius,
            coreHalfWidth: coreHalfWidth,
            coreHalfHeight: coreHalfHeight,
            radians: radians,
            extentX: extentX,
            extentY: extentY
        )
    }

    private static func pullIsOutsideContactShape(
        _ placement: Placement,
        tolerance: CGFloat = 0
    ) -> Bool {
        let deltaX = placement.pullPoint.x - placement.center.x
        let deltaY = placement.pullPoint.y - placement.center.y
        let cosine = cos(placement.radians)
        let sine = sin(placement.radians)
        let localX = cosine * deltaX + sine * deltaY
        let localY = -sine * deltaX + cosine * deltaY
        let roundedDeltaX = max(0, abs(localX) - placement.coreHalfWidth)
        let roundedDeltaY = max(0, abs(localY) - placement.coreHalfHeight)
        return hypot(roundedDeltaX, roundedDeltaY) > placement.radius + tolerance
    }

    private static func roundedRectangleBoundary(_ placement: Placement) -> [CGPoint] {
        let corners: [(x: CGFloat, y: CGFloat, start: CGFloat)] = [
            (placement.coreHalfWidth, -placement.coreHalfHeight, -.pi / 2),
            (placement.coreHalfWidth, placement.coreHalfHeight, 0),
            (-placement.coreHalfWidth, placement.coreHalfHeight, .pi / 2),
            (-placement.coreHalfWidth, -placement.coreHalfHeight, .pi),
        ]
        let cosine = cos(placement.radians)
        let sine = sin(placement.radians)
        var points: [CGPoint] = []
        for corner in corners {
            for step in 0...cornerSteps {
                let angle = corner.start + CGFloat(step) * .pi / (2 * CGFloat(cornerSteps))
                let localX = corner.x + placement.radius * cos(angle)
                let localY = corner.y + placement.radius * sin(angle)
                let point = CGPoint(
                    x: placement.center.x + cosine * localX - sine * localY,
                    y: placement.center.y + sine * localX + cosine * localY
                )
                if points.last.map({ hypot($0.x - point.x, $0.y - point.y) > 1e-9 }) ?? true {
                    points.append(point)
                }
            }
        }
        if let first = points.first,
           let last = points.last,
           hypot(first.x - last.x, first.y - last.y) <= 1e-9 {
            points.removeLast()
        }
        return points
    }

    private static func normalizedAngleDifference(
        _ angle: CGFloat,
        reference: CGFloat
    ) -> CGFloat {
        let fullTurn = 2 * CGFloat.pi
        var result = (angle - reference + .pi).truncatingRemainder(dividingBy: fullTurn)
        if result < 0 { result += fullTurn }
        return result - .pi
    }

    private static func cyclicBoundaryArc(
        _ boundary: [CGPoint],
        startIndex: Int,
        endIndex: Int,
        step: Int
    ) -> [CGPoint] {
        var points = [boundary[startIndex]]
        var index = startIndex
        for _ in 0..<boundary.count {
            if index == endIndex { return points }
            index = (index + step + boundary.count) % boundary.count
            points.append(boundary[index])
        }
        return []
    }

    private static func arcScore(_ points: [CGPoint]) -> (maximumY: CGFloat, averageY: CGFloat) {
        (
            points.map(\.y).max() ?? -.infinity,
            points.reduce(0) { $0 + $1.y } / CGFloat(points.count)
        )
    }

    private static func path(through points: [CGPoint]) -> Path {
        var path = Path()
        guard let first = points.first else { return path }
        path.move(to: first)
        for point in points.dropFirst() {
            path.addLine(to: point)
        }
        return path
    }
}

enum BoardExternalSlidingLoopCordPresentationValidation {
    static func failure(
        for rig: BoardExternalSlidingLoopCordRig,
        rotationDegrees: Double,
        rotationAnchor: BoardGeometryRotationAnchor,
        geometryScale: Double = 1
    ) -> BoardExternalSlidingLoopCordPresentationValidationFailure? {
        BoardExternalSlidingLoopCordRigGeometry.validationFailure(
            for: rig,
            projection: BoardPresentationGeometryProjection(
                rotationDegrees: CGFloat(rotationDegrees),
                geometryScale: CGFloat(geometryScale),
                rotationAnchor: rotationAnchor
            ),
            in: CGRect(origin: .zero, size: rig.sceneSize.cgSize)
        )
    }
}
