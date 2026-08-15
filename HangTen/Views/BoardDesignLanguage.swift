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
        return frames.dropFirst().reduce(first) { $0.union($1) }
    }

    func holdPieces(for holdID: String) -> [BoardHoldPiece] {
        holds.filter { $0.holdID == holdID }
    }

    func renderPath(for hold: BoardHoldPiece, in rect: CGRect) -> Path {
        hold.path(in: rect)
    }

    func draw(
        in context: inout GraphicsContext,
        size: CGSize,
        highlightedHoldIDs: Set<String>,
        highlightMode: BoardHighlightMode
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
                highlightMode: highlightMode,
                in: &context,
                boardRect: rect
            )
        }
    }

    private func draw(
        _ hold: BoardHoldPiece,
        highlighted: Bool,
        highlightMode: BoardHighlightMode,
        in context: inout GraphicsContext,
        boardRect: CGRect
    ) {
        let rect = hold.rect(in: boardRect)
        let outerPath = renderPath(for: hold, in: boardRect)

        switch hold.treatment {
        case .surface:
            context.fill(
                outerPath,
                with: highlighted
                    ? highlightShading(mode: highlightMode, in: rect)
                    : shading(for: .topPlane, pathRect: rect)
            )

        case .shelf:
            context.fill(
                outerPath,
                with: highlighted
                    ? highlightShading(mode: highlightMode, in: rect)
                    : shading(for: .shelf, pathRect: rect)
            )

        case let .recess(profile):
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
                outerPath,
                with: highlighted
                    ? highlightShading(mode: highlightMode, in: rect)
                    : .linearGradient(
                        Gradient(colors: recessColors),
                        startPoint: CGPoint(x: rect.midX, y: rect.minY),
                        endPoint: CGPoint(x: rect.midX, y: rect.maxY)
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

    private func highlightShading(
        mode: BoardHighlightMode,
        in rect: CGRect
    ) -> GraphicsContext.Shading {
        switch mode {
        case .active:
            return activeShading(in: rect)
        case .preview:
            return .linearGradient(
                Gradient(colors: [Color.restBlue, Color.restBlue.opacity(0.72)]),
                startPoint: CGPoint(x: rect.midX, y: rect.minY),
                endPoint: CGPoint(x: rect.midX, y: rect.maxY)
            )
        }
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

struct BoardHoldPiece: Identifiable, Hashable {
    let id: String
    let holdID: String
    let frame: CGRect
    let shape: BoardShape
    let treatment: BoardHoldTreatment

    func rect(in boardRect: CGRect) -> CGRect {
        CGRect(
            x: boardRect.minX + boardRect.width * frame.minX,
            y: boardRect.minY + boardRect.height * frame.minY,
            width: boardRect.width * frame.width,
            height: boardRect.height * frame.height
        )
    }

    func path(in boardRect: CGRect) -> Path {
        shape.path(in: rect(in: boardRect))
    }
}

struct BoardHoldPathShape: Shape {
    let pieces: [BoardHoldPiece]

    func path(in rect: CGRect) -> Path {
        var path = Path()
        for piece in pieces {
            path.addPath(piece.path(in: rect))
        }
        return path
    }
}

enum BoardHoldTreatment: Hashable {
    case recess(BoardRecessProfile)
    case shelf(BoardShelfProfile)
    case surface
}

struct BoardRecessProfile: Hashable {
    let rimInsetFraction: CGFloat
    let depth: BoardRecessDepth

    static let deepSlot = BoardRecessProfile(rimInsetFraction: 0.090, depth: .deep)
    static let shallowSlot = BoardRecessProfile(rimInsetFraction: 0.090, depth: .shallow)
}

enum BoardRecessDepth: Hashable {
    case deep
    case shallow
}

struct BoardShelfProfile: Hashable {
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
        shelfTop: Color(red: 0.795, green: 0.715, blue: 0.535),
        shelfBottom: Color(red: 0.735, green: 0.635, blue: 0.445),
        recessTop: Color(red: 0.647, green: 0.573, blue: 0.412),
        recessBottom: Color(red: 0.682, green: 0.612, blue: 0.439),
        shallowRecessTop: Color(red: 0.704, green: 0.625, blue: 0.465),
        shallowRecessBottom: Color(red: 0.729, green: 0.655, blue: 0.490),
        recessShadow: Color(red: 0.310, green: 0.250, blue: 0.190).opacity(0.28)
    )
}

enum BoardShape: Hashable {
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

struct BoardNormalizedPath: Hashable {
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

enum BoardPathCommand: Hashable {
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

// MARK: - Package artwork adaptation

enum BoardArtworkAdaptationError: Error, CustomStringConvertible {
    case invalid(String)

    var description: String {
        switch self {
        case .invalid(let reason):
            reason
        }
    }
}

extension BoardArtworkDocument {
    func boardDesign(holds physicalHolds: [BoardHold]) throws -> BoardDesign {
        guard canvasFrame.isNormalized else {
            throw BoardArtworkAdaptationError.invalid("canvas frame must stay inside normalized bounds")
        }
        guard palette == "sculptedWood" else {
            throw BoardArtworkAdaptationError.invalid("unsupported palette \(palette)")
        }
        guard Set(layers.map(\.id)).count == layers.count else {
            throw BoardArtworkAdaptationError.invalid("artwork layer IDs must be unique")
        }
        guard Set(holdPieces.map(\.id)).count == holdPieces.count else {
            throw BoardArtworkAdaptationError.invalid("artwork hold-piece IDs must be unique")
        }

        return try BoardDesign(
            id: boardID,
            canvasFrame: canvasFrame.cgRect,
            silhouette: silhouette.boardShape(),
            layers: layers.map { try $0.boardLayer() },
            holds: physicalHolds.flatMap(\.geometry),
            palette: .sculptedWood
        )
    }
}

private extension BoardArtworkLayerDocument {
    func boardLayer() throws -> BoardLayer {
        guard frame.isNormalized else {
            throw BoardArtworkAdaptationError.invalid("layer \(id) has an invalid frame")
        }
        return try BoardLayer(
            frame: frame.cgRect,
            shape: shape.boardShape(),
            role: boardSurfaceRole()
        )
    }

    func boardSurfaceRole() throws -> BoardSurfaceRole {
        switch role {
        case "topPlane": .topPlane
        case "faceLight": .faceLight
        case "separator": .separator
        case "bottomPlane": .bottomPlane
        case "topSeam": .topSeam
        case "shelf": .shelf
        default:
            throw BoardArtworkAdaptationError.invalid("layer \(id) has unsupported role \(role)")
        }
    }
}

private extension BoardArtworkHoldPieceDocument {
    func boardHoldPiece() throws -> BoardHoldPiece {
        guard frame.isNormalized else {
            throw BoardArtworkAdaptationError.invalid("hold piece \(id) has an invalid frame")
        }
        return try BoardHoldPiece(
            id: id,
            holdID: holdID,
            frame: frame.cgRect,
            shape: shape.boardShape(),
            treatment: treatment.boardHoldTreatment(pieceID: id)
        )
    }
}

extension BoardHoldPieceDocument {
    func boardHoldPiece(id: String, holdID: String) throws -> BoardHoldPiece {
        guard frame.isNormalized else {
            throw BoardArtworkAdaptationError.invalid("hold piece \(id) has an invalid frame")
        }
        return try BoardHoldPiece(
            id: id,
            holdID: holdID,
            frame: frame.cgRect,
            shape: shape.boardShape(),
            treatment: treatment.map {
                try $0.boardHoldTreatment(pieceID: id)
            } ?? .surface
        )
    }
}

private extension BoardArtworkShapeDocument {
    func boardShape() throws -> BoardShape {
        switch type {
        case "roundedRect":
            guard commands == nil,
                  let cornerRadiusFraction,
                  cornerRadiusFraction.isFinite,
                  (0...0.5).contains(cornerRadiusFraction) else {
                throw BoardArtworkAdaptationError.invalid("rounded rectangle shape is invalid")
            }
            return .roundedRect(cornerRadiusFraction: CGFloat(cornerRadiusFraction))

        case "path":
            guard cornerRadiusFraction == nil,
                  let commands,
                  !commands.isEmpty,
                  commands.first?.command == "move",
                  commands.last?.command == "close" else {
                throw BoardArtworkAdaptationError.invalid("path must begin with move and end with close")
            }
            return .path(
                BoardNormalizedPath(
                    commands: try commands.map { try $0.boardPathCommand() }
                )
            )

        default:
            throw BoardArtworkAdaptationError.invalid("unsupported shape type \(type)")
        }
    }
}

private extension BoardArtworkPathCommandDocument {
    func boardPathCommand() throws -> BoardPathCommand {
        switch command {
        case "move":
            guard control == nil, control1 == nil, control2 == nil else {
                throw invalidCommand()
            }
            return .move(try point(to))
        case "line":
            guard control == nil, control1 == nil, control2 == nil else {
                throw invalidCommand()
            }
            return .line(try point(to))
        case "quad":
            guard control1 == nil, control2 == nil else { throw invalidCommand() }
            return .quad(to: try point(to), control: try point(control))
        case "curve":
            guard control == nil else { throw invalidCommand() }
            return .curve(
                to: try point(to),
                control1: try point(control1),
                control2: try point(control2)
            )
        case "close":
            guard to == nil, control == nil, control1 == nil, control2 == nil else {
                throw invalidCommand()
            }
            return .close
        default:
            throw invalidCommand()
        }
    }

    func point(_ coordinates: [Double]?) throws -> CGPoint {
        guard let coordinates,
              coordinates.count == 2,
              coordinates.allSatisfy({ $0.isFinite && (0...1).contains($0) }) else {
            throw invalidCommand()
        }
        return CGPoint(x: coordinates[0], y: coordinates[1])
    }

    func invalidCommand() -> BoardArtworkAdaptationError {
        .invalid("invalid \(command) path command")
    }
}

private extension BoardArtworkTreatmentDocument {
    func boardHoldTreatment(pieceID: String) throws -> BoardHoldTreatment {
        switch type {
        case "surface":
            guard rimInsetFraction == nil, depth == nil else {
                throw invalidTreatment(pieceID: pieceID)
            }
            return .surface

        case "shelf":
            guard depth == nil, let inset = try validatedInset(pieceID: pieceID) else {
                throw invalidTreatment(pieceID: pieceID)
            }
            return .shelf(BoardShelfProfile(rimInsetFraction: inset))

        case "recess":
            guard let inset = try validatedInset(pieceID: pieceID) else {
                throw invalidTreatment(pieceID: pieceID)
            }
            let recessDepth: BoardRecessDepth
            switch depth {
            case "deep": recessDepth = .deep
            case "shallow": recessDepth = .shallow
            default: throw invalidTreatment(pieceID: pieceID)
            }
            return .recess(
                BoardRecessProfile(rimInsetFraction: inset, depth: recessDepth)
            )

        default:
            throw invalidTreatment(pieceID: pieceID)
        }
    }

    func validatedInset(pieceID: String) throws -> CGFloat? {
        guard let rimInsetFraction else { return nil }
        guard rimInsetFraction.isFinite, (0...0.5).contains(rimInsetFraction) else {
            throw invalidTreatment(pieceID: pieceID)
        }
        return CGFloat(rimInsetFraction)
    }

    func invalidTreatment(pieceID: String) -> BoardArtworkAdaptationError {
        .invalid("hold piece \(pieceID) has an invalid \(type) treatment")
    }
}
