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
    let supportPaths: [Path]
    let knotOverpass: Path
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
        let exits = [
            CGPoint(x: pullPoint.x - 22 * scale, y: pullPoint.y),
            CGPoint(x: pullPoint.x + 22 * scale, y: pullPoint.y),
        ]
        let strands = zip(exits, pairedAttachments).map {
            BoardCordStrand(start: $0.0, end: $0.1)
        }

        func offsetPoint(_ x: CGFloat, _ y: CGFloat) -> CGPoint {
            CGPoint(x: pullPoint.x + x * scale, y: pullPoint.y + y * scale)
        }

        var bight = Path()
        bight.move(to: offsetPoint(-12, -61))
        bight.addCurve(
            to: offsetPoint(-21, -142),
            control1: offsetPoint(-26, -82),
            control2: offsetPoint(-30, -115)
        )
        bight.addCurve(
            to: offsetPoint(1, -177),
            control1: offsetPoint(-14, -163),
            control2: offsetPoint(-5, -174)
        )
        bight.addCurve(
            to: offsetPoint(24, -136),
            control1: offsetPoint(9, -171),
            control2: offsetPoint(18, -157)
        )
        bight.addCurve(
            to: offsetPoint(12, -61),
            control1: offsetPoint(31, -109),
            control2: offsetPoint(26, -81)
        )

        var leftKnotAndExit = Path()
        leftKnotAndExit.move(to: offsetPoint(-12, -63))
        leftKnotAndExit.addCurve(
            to: offsetPoint(21, -39),
            control1: offsetPoint(1, -52),
            control2: offsetPoint(18, -51)
        )
        leftKnotAndExit.addCurve(
            to: offsetPoint(5, -18),
            control1: offsetPoint(24, -28),
            control2: offsetPoint(16, -19)
        )
        leftKnotAndExit.addCurve(
            to: offsetPoint(-22, 0),
            control1: offsetPoint(-8, -17),
            control2: offsetPoint(-17, -9)
        )

        var rightKnotAndExit = Path()
        rightKnotAndExit.move(to: offsetPoint(12, -63))
        rightKnotAndExit.addCurve(
            to: offsetPoint(-21, -39),
            control1: offsetPoint(-1, -52),
            control2: offsetPoint(-18, -51)
        )
        rightKnotAndExit.addCurve(
            to: offsetPoint(-5, -18),
            control1: offsetPoint(-24, -28),
            control2: offsetPoint(-16, -19)
        )
        rightKnotAndExit.addCurve(
            to: offsetPoint(22, 0),
            control1: offsetPoint(8, -17),
            control2: offsetPoint(17, -9)
        )

        let supportPaths = [bight, leftKnotAndExit, rightKnotAndExit]

        var knotOverpass = Path()
        knotOverpass.move(to: offsetPoint(-18, -35))
        knotOverpass.addCurve(
            to: offsetPoint(18, -35),
            control1: offsetPoint(-10, -24),
            control2: offsetPoint(9, -22)
        )

        let eyeletForegroundCrescents = zip(pairedAttachments, exits).map {
            eyeletCrescent(
                center: $0.0,
                toward: $0.1,
                radius: rig.eyeletRadius * scale,
                chordOffset: 7 * scale
            )
        }

        let strandPaths = strands.map { strand in
            var path = Path()
            path.move(to: strand.start)
            path.addLine(to: strand.end)
            return path
        }
        let cordPaths = supportPaths + strandPaths + [knotOverpass]
        let pathBounds = cordPaths.reduce(CGRect.null) {
            $0.union($1.boundingRect)
        }
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
            supportPaths: supportPaths,
            knotOverpass: knotOverpass,
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
