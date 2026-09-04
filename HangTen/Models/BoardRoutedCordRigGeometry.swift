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
                let radius = lip.radius * scale
                let chordOffset = lip.chordOffset * scale
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
        rotationAnchor: BoardGeometryRotationAnchor
    ) -> BoardRoutedCordPresentationValidationFailure? {
        let canvas = CGRect(origin: .zero, size: rig.sceneSize.cgSize)
        guard let geometry = BoardRoutedCordRigGeometry.resolve(
            rig: rig,
            projection: BoardPresentationGeometryProjection(
                rotationDegrees: CGFloat(rotationDegrees),
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
