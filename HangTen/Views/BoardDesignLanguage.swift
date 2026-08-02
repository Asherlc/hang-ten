import SwiftUI

// MARK: - Reusable board design language

/// Declarative artwork for one physical board. New boards provide normalized
/// geometry and inherit the same rendering, depth, highlighting, and hit logic.
struct BoardDesign {
    let id: String
    let canvasFrame: CGRect
    let silhouette: BoardShape
    let layers: [BoardLayer]
    let holds: [BoardHoldPiece]
    let palette: BoardPalette

    func boardRect(in size: CGSize) -> CGRect {
        CGRect(
            x: size.width * canvasFrame.minX,
            y: size.height * canvasFrame.minY,
            width: size.width * canvasFrame.width,
            height: size.height * canvasFrame.height
        )
    }

    func interactionFrame(for holdID: String) -> CGRect? {
        let frames = holds
            .filter { $0.holdID == holdID }
            .map(\.frame)

        guard let first = frames.first else { return nil }
        let union = frames.dropFirst().reduce(first) { $0.union($1) }
        return union.insetBy(dx: -0.010, dy: -0.035)
    }

    func draw(
        in context: inout GraphicsContext,
        size: CGSize,
        highlightedHoldIDs: Set<String>
    ) {
        let rect = boardRect(in: size)
        let bodyPath = silhouette.path(in: rect)
        let verticalUnit = rect.height

        var shadowContext = context
        shadowContext.addFilter(
            .shadow(
                color: palette.castShadow,
                radius: max(1.0, verticalUnit * 0.022),
                x: 0,
                y: verticalUnit * 0.016
            )
        )
        shadowContext.fill(bodyPath, with: .color(palette.bodyShadow))

        context.fill(
            bodyPath,
            with: .linearGradient(
                Gradient(colors: [palette.bodyTop, palette.body, palette.bodyBottom]),
                startPoint: CGPoint(x: rect.midX, y: rect.minY),
                endPoint: CGPoint(x: rect.midX, y: rect.maxY)
            )
        )

        // Every dimensional plane belongs to the carved body. Clipping here
        // prevents separators and side bays from creating contour spikes.
        context.clip(to: bodyPath)

        for layer in layers {
            let layerRect = scaled(layer.frame, in: rect)
            let path = layer.shape.path(in: layerRect)
            context.fill(path, with: shading(for: layer.role, pathRect: layerRect))
        }

        for hold in holds {
            draw(
                hold,
                highlighted: highlightedHoldIDs.contains(hold.holdID),
                in: &context,
                boardRect: rect
            )
        }
    }

    private func draw(
        _ hold: BoardHoldPiece,
        highlighted: Bool,
        in context: inout GraphicsContext,
        boardRect: CGRect
    ) {
        let rect = scaled(hold.frame, in: boardRect)
        let outerPath = hold.shape.path(in: rect)

        switch hold.treatment {
        case .surface:
            context.fill(
                outerPath,
                with: highlighted
                    ? activeShading(in: rect)
                    : shading(for: .topPlane, pathRect: rect)
            )

        case let .shelf(profile):
            context.fill(
                outerPath,
                with: .linearGradient(
                    Gradient(colors: [palette.bevelTop, palette.bevelBottom]),
                    startPoint: CGPoint(x: rect.midX, y: rect.minY),
                    endPoint: CGPoint(x: rect.midX, y: rect.maxY)
                )
            )

            let inset = min(rect.width, rect.height) * profile.rimInsetFraction
            let contactRect = rect.insetBy(dx: inset, dy: inset)
            let contactPath = hold.shape.path(in: contactRect)
            var shelfContext = context
            shelfContext.addFilter(
                .shadow(
                    color: palette.recessShadow.opacity(0.55),
                    radius: max(0.6, boardRect.height * 0.010),
                    x: 0,
                    y: boardRect.height * 0.007
                )
            )
            shelfContext.fill(
                contactPath,
                with: highlighted
                    ? activeShading(in: contactRect)
                    : shading(for: .shelf, pathRect: contactRect)
            )

        case let .recess(profile):
            context.fill(
                outerPath,
                with: .linearGradient(
                    Gradient(colors: [palette.bevelTop, palette.bevelBottom]),
                    startPoint: CGPoint(x: rect.midX, y: rect.minY),
                    endPoint: CGPoint(x: rect.midX, y: rect.maxY)
                )
            )

            let inset = min(rect.width, rect.height) * profile.rimInsetFraction
            let contactRect = rect.insetBy(dx: inset, dy: inset)
            let contactPath = hold.shape.path(in: contactRect)
            let recessColors: [Color]
            switch profile.depth {
            case .deep:
                recessColors = [palette.recessTop, palette.recessBottom]
            case .shallow:
                recessColors = [palette.shallowRecessTop, palette.shallowRecessBottom]
            }

            var wellContext = context
            wellContext.addFilter(
                .shadow(
                    color: palette.recessShadow,
                    radius: max(0.45, boardRect.height * 0.006),
                    x: 0,
                    y: boardRect.height * 0.003
                )
            )
            wellContext.fill(
                contactPath,
                with: highlighted
                    ? activeShading(in: contactRect)
                    : .linearGradient(
                        Gradient(colors: recessColors),
                        startPoint: CGPoint(x: contactRect.midX, y: contactRect.minY),
                        endPoint: CGPoint(x: contactRect.midX, y: contactRect.maxY)
                    )
            )
        }
    }

    private func shading(for role: BoardSurfaceRole, pathRect: CGRect) -> GraphicsContext.Shading {
        let colors: [Color]
        switch role {
        case .topPlane:
            colors = [palette.topPlaneTop, palette.topPlaneBottom]
        case .faceLight:
            colors = [palette.faceLight, palette.body]
        case .separator:
            colors = [palette.separatorTop, palette.separatorBottom]
        case .bottomPlane:
            colors = [palette.body, palette.bodyBottom]
        case .topSeam:
            colors = [palette.topSeam, palette.topSeam.opacity(0.28)]
        case .shelf:
            colors = [palette.shelfTop, palette.shelfBottom]
        }

        return .linearGradient(
            Gradient(colors: colors),
            startPoint: CGPoint(x: pathRect.midX, y: pathRect.minY),
            endPoint: CGPoint(x: pathRect.midX, y: pathRect.maxY)
        )
    }

    private func activeShading(in rect: CGRect) -> GraphicsContext.Shading {
        .linearGradient(
            Gradient(colors: [.holdActive, .holdActiveDeep]),
            startPoint: CGPoint(x: rect.midX, y: rect.minY),
            endPoint: CGPoint(x: rect.midX, y: rect.maxY)
        )
    }

    private func scaled(_ normalized: CGRect, in rect: CGRect) -> CGRect {
        CGRect(
            x: rect.minX + rect.width * normalized.minX,
            y: rect.minY + rect.height * normalized.minY,
            width: rect.width * normalized.width,
            height: rect.height * normalized.height
        )
    }
}

struct BoardLayer {
    let frame: CGRect
    let shape: BoardShape
    let role: BoardSurfaceRole
}

enum BoardSurfaceRole {
    case topPlane
    case faceLight
    case separator
    case bottomPlane
    case topSeam
    case shelf
}

struct BoardHoldPiece: Identifiable {
    let id: String
    let holdID: String
    let frame: CGRect
    let shape: BoardShape
    let treatment: BoardHoldTreatment
}

enum BoardHoldTreatment {
    case recess(BoardRecessProfile)
    case shelf(BoardShelfProfile)
    case surface
}

struct BoardRecessProfile {
    let rimInsetFraction: CGFloat
    let depth: BoardRecessDepth

    static let deepSlot = BoardRecessProfile(rimInsetFraction: 0.090, depth: .deep)
    static let shallowSlot = BoardRecessProfile(rimInsetFraction: 0.090, depth: .shallow)
}

enum BoardRecessDepth {
    case deep
    case shallow
}

struct BoardShelfProfile {
    let rimInsetFraction: CGFloat

    static let broadJug = BoardShelfProfile(rimInsetFraction: 0.060)
}

struct BoardPalette {
    let bodyTop: Color
    let body: Color
    let bodyBottom: Color
    let bodyShadow: Color
    let castShadow: Color
    let topPlaneTop: Color
    let topPlaneBottom: Color
    let faceLight: Color
    let separatorTop: Color
    let separatorBottom: Color
    let topSeam: Color
    let bevelTop: Color
    let bevelBottom: Color
    let shelfTop: Color
    let shelfBottom: Color
    let recessTop: Color
    let recessBottom: Color
    let shallowRecessTop: Color
    let shallowRecessBottom: Color
    let recessShadow: Color

    /// Smooth, textureless wood inspired by Fingy's sculpted-object treatment.
    static let sculptedWood = BoardPalette(
        bodyTop: Color(red: 0.870, green: 0.795, blue: 0.635),
        body: Color(red: 0.847, green: 0.780, blue: 0.615),
        bodyBottom: Color(red: 0.855, green: 0.780, blue: 0.608),
        bodyShadow: Color(red: 0.470, green: 0.370, blue: 0.275),
        castShadow: Color(red: 0.280, green: 0.220, blue: 0.180).opacity(0.14),
        topPlaneTop: Color(red: 0.948, green: 0.917, blue: 0.827),
        topPlaneBottom: Color(red: 0.922, green: 0.882, blue: 0.762),
        faceLight: Color(red: 0.900, green: 0.826, blue: 0.655),
        separatorTop: Color(red: 0.865, green: 0.800, blue: 0.630),
        separatorBottom: Color(red: 0.847, green: 0.780, blue: 0.615),
        topSeam: Color(red: 0.790, green: 0.710, blue: 0.555).opacity(0.35),
        bevelTop: Color(red: 0.885, green: 0.817, blue: 0.650),
        bevelBottom: Color(red: 0.800, green: 0.715, blue: 0.535),
        shelfTop: Color(red: 0.820, green: 0.750, blue: 0.580),
        shelfBottom: Color(red: 0.790, green: 0.710, blue: 0.530),
        recessTop: Color(red: 0.647, green: 0.573, blue: 0.412),
        recessBottom: Color(red: 0.682, green: 0.612, blue: 0.439),
        shallowRecessTop: Color(red: 0.704, green: 0.625, blue: 0.465),
        shallowRecessBottom: Color(red: 0.729, green: 0.655, blue: 0.490),
        recessShadow: Color(red: 0.310, green: 0.250, blue: 0.190).opacity(0.28)
    )
}

enum BoardShape {
    case roundedRect(cornerRadiusFraction: CGFloat)
    case path(BoardNormalizedPath)

    func path(in rect: CGRect) -> Path {
        switch self {
        case let .roundedRect(fraction):
            let radius = min(rect.width, rect.height) * fraction
            return Path(
                roundedRect: rect,
                cornerSize: CGSize(width: radius, height: radius)
            )
        case let .path(normalizedPath):
            return normalizedPath.path(in: rect)
        }
    }

    var mirroredHorizontally: BoardShape {
        switch self {
        case .roundedRect:
            return self
        case let .path(path):
            return .path(path.mirroredHorizontally)
        }
    }
}

struct BoardNormalizedPath {
    let commands: [BoardPathCommand]

    func path(in rect: CGRect) -> Path {
        func point(_ normalized: CGPoint) -> CGPoint {
            CGPoint(
                x: rect.minX + rect.width * normalized.x,
                y: rect.minY + rect.height * normalized.y
            )
        }

        var result = Path()
        for command in commands {
            switch command {
            case let .move(to):
                result.move(to: point(to))
            case let .line(to):
                result.addLine(to: point(to))
            case let .quad(to, control):
                result.addQuadCurve(to: point(to), control: point(control))
            case let .curve(to, control1, control2):
                result.addCurve(
                    to: point(to),
                    control1: point(control1),
                    control2: point(control2)
                )
            case .close:
                result.closeSubpath()
            }
        }
        return result
    }

    var mirroredHorizontally: BoardNormalizedPath {
        BoardNormalizedPath(commands: commands.map(\.mirroredHorizontally))
    }
}

enum BoardPathCommand {
    case move(CGPoint)
    case line(CGPoint)
    case quad(to: CGPoint, control: CGPoint)
    case curve(to: CGPoint, control1: CGPoint, control2: CGPoint)
    case close

    var mirroredHorizontally: BoardPathCommand {
        func mirror(_ point: CGPoint) -> CGPoint {
            CGPoint(x: 1 - point.x, y: point.y)
        }

        switch self {
        case let .move(to):
            return .move(mirror(to))
        case let .line(to):
            return .line(mirror(to))
        case let .quad(to, control):
            return .quad(to: mirror(to), control: mirror(control))
        case let .curve(to, control1, control2):
            return .curve(to: mirror(to), control1: mirror(control1), control2: mirror(control2))
        case .close:
            return .close
        }
    }
}

extension CGRect {
    var mirroredHorizontally: CGRect {
        CGRect(x: 1 - maxX, y: minY, width: width, height: height)
    }
}
