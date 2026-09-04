import SwiftUI

struct BoardCordStrand: Equatable {
    let start: CGPoint
    let end: CGPoint
}

struct BoardCordRigGeometry {
    let sceneRect: CGRect
    let sourceRect: CGRect
    let faceRect: CGRect
    let faceTransform: CGAffineTransform
    let projectedAttachments: [CGPoint]
    let pairedAttachments: [CGPoint]
    let strands: [BoardCordStrand]
    let tensionPath: Path
    let eyeletForegroundCrescents: [Path]
    let strokeBounds: CGRect

    static func make(
        rig: BoardDirectTwoAnchorCordRig,
        projection: BoardPresentationGeometryProjection,
        in canvas: CGRect
    ) -> BoardCordRigGeometry {
        let canonicalSceneSize = rig.sceneSize.cgSize
        let scale = min(
            canvas.width / canonicalSceneSize.width,
            canvas.height / canonicalSceneSize.height
        )
        let sceneRect = CGRect(
            x: canvas.midX - canonicalSceneSize.width * scale / 2,
            y: canvas.midY - canonicalSceneSize.height * scale / 2,
            width: canonicalSceneSize.width * scale,
            height: canonicalSceneSize.height * scale
        )

        func scenePoint(_ canonicalPoint: CGPoint) -> CGPoint {
            CGPoint(
                x: sceneRect.minX + canonicalPoint.x * scale,
                y: sceneRect.minY + canonicalPoint.y * scale
            )
        }

        func mappedSceneRect(_ canonicalRect: CGRect) -> CGRect {
            CGRect(
                x: sceneRect.minX + canonicalRect.minX * scale,
                y: sceneRect.minY + canonicalRect.minY * scale,
                width: canonicalRect.width * scale,
                height: canonicalRect.height * scale
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
        let faceTransform = projection.affineTransform(in: sceneRect)

        func sourceRelativePoint(_ point: BoardCordPoint) -> CGPoint {
            scenePoint(
                CGPoint(
                    x: canonicalSourceFrame.minX + point.x,
                    y: canonicalSourceFrame.minY + point.y
                )
            )
        }

        let projectedAttachments = rig.attachmentPoints.map {
            sourceRelativePoint($0).applying(faceTransform)
        }
        let pairedAttachments = projectedAttachments.sorted { lhs, rhs in
            lhs.x == rhs.x ? lhs.y < rhs.y : lhs.x < rhs.x
        }

        let pullPoint = sourceRelativePoint(rig.pullPoint)
        let strands = pairedAttachments.map {
            BoardCordStrand(start: pullPoint, end: $0)
        }

        var tensionPath = Path()
        if let leftAttachment = pairedAttachments.first,
           let rightAttachment = pairedAttachments.last {
            tensionPath.move(to: leftAttachment)
            tensionPath.addLine(to: pullPoint)
            tensionPath.addLine(to: rightAttachment)
        }

        let eyeletForegroundCrescents = pairedAttachments.map {
            eyeletCrescent(
                center: $0,
                toward: pullPoint,
                radius: rig.eyeletRadius * scale,
                chordOffset: 7 * scale
            )
        }
        let pathBounds = tensionPath.boundingRect
        let shadowXMargin = (35 / 2 + 4 + 2.3) * scale
        let shadowYMargin = (35 / 2 + 5 + 2.3) * scale
        let strokeBounds = pathBounds.insetBy(
            dx: -shadowXMargin,
            dy: -shadowYMargin
        )

        return BoardCordRigGeometry(
            sceneRect: sceneRect,
            sourceRect: sourceRect,
            faceRect: faceRect,
            faceTransform: faceTransform,
            projectedAttachments: projectedAttachments,
            pairedAttachments: pairedAttachments,
            strands: strands,
            tensionPath: tensionPath,
            eyeletForegroundCrescents: eyeletForegroundCrescents,
            strokeBounds: strokeBounds
        )
    }

    private static func eyeletCrescent(
        center: CGPoint,
        toward: CGPoint,
        radius: CGFloat,
        chordOffset: CGFloat
    ) -> Path {
        let deltaX = toward.x - center.x
        let deltaY = toward.y - center.y
        let length = sqrt(deltaX * deltaX + deltaY * deltaY)
        guard length > 0, radius >= chordOffset else { return Path() }

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
