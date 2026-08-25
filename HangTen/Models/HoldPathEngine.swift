import CoreGraphics
import Foundation

struct HoldPathBounds: Equatable {
    var minX: CGFloat
    var minY: CGFloat
    var maxX: CGFloat
    var maxY: CGFloat

    var width: CGFloat { maxX - minX }
    var height: CGFloat { maxY - minY }
    var center: CGPoint { CGPoint(x: (minX + maxX) / 2, y: (minY + maxY) / 2) }

    init(minX: CGFloat, minY: CGFloat, maxX: CGFloat, maxY: CGFloat) {
        self.minX = minX
        self.minY = minY
        self.maxX = maxX
        self.maxY = maxY
    }
}

enum OutlinePreset: String, CaseIterable, Hashable {
    case oval
    case circle
    case pill
    case roundedRectangle
    case rectangle
}

enum ConstrainedHandle: String, CaseIterable, Hashable {
    case nw
    case n
    case ne
    case e
    case se
    case s
    case sw
    case w

    var includesNorth: Bool { rawValue.contains("n") }
    var includesSouth: Bool { rawValue.contains("s") }
    var includesEast: Bool { rawValue.contains("e") }
    var includesWest: Bool { rawValue.contains("w") }
    var changesX: Bool { includesEast || includesWest }
    var changesY: Bool { includesNorth || includesSouth }
}

enum ShapeConstraintShape: String, CaseIterable, Hashable {
    case oval
    case circle
    case pill
    case roundedRectangle
    case rectangle
}

struct ShapeConstraint: Equatable {
    var shape: ShapeConstraintShape
    var rotationDegrees: Double

    func validated() throws -> ShapeConstraint {
        guard rotationDegrees.isFinite else {
            throw HoldPathEngineError.shapeRotationMustBeFinite
        }
        guard (-180.0..<180.0).contains(rotationDegrees) else {
            throw HoldPathEngineError.shapeRotationMustBeNormalized
        }
        return self
    }
}

struct ConstrainedOutlineModel: Equatable {
    var center: CGPoint
    var rotationDegrees: Double
    var intrinsicBounds: HoldPathBounds
    var handles: [ConstrainedHandle: CGPoint]
}

struct ConstrainedResizeResult: Equatable {
    var commands: [BoardPathCommand]
    var shapeConstraint: ShapeConstraint
}

enum HoldPathEngineError: Error, Equatable, LocalizedError {
    case outlineNeedsNonZeroWidthAndHeight
    case resizePointerMustBeFinite
    case constrainedResizeLocalPointerMustBeFinite
    case minimumSizeMustBePositive
    case constrainedResizeDimensionsMustBeFinite
    case constrainedResizeCoordinatesMustBeFinite
    case shapeRotationMustBeFinite
    case shapeRotationMustBeNormalized

    var errorDescription: String? {
        switch self {
        case .outlineNeedsNonZeroWidthAndHeight:
            "Outline needs non-zero width and height"
        case .resizePointerMustBeFinite:
            "Resize pointer must be finite"
        case .constrainedResizeLocalPointerMustBeFinite:
            "Constrained resize local pointer must be finite"
        case .minimumSizeMustBePositive:
            "Minimum size must be positive"
        case .constrainedResizeDimensionsMustBeFinite:
            "Constrained resize dimensions must be finite"
        case .constrainedResizeCoordinatesMustBeFinite:
            "Constrained resize coordinates must be finite"
        case .shapeRotationMustBeFinite:
            "Shape constraint rotation must be finite"
        case .shapeRotationMustBeNormalized:
            "Shape constraint rotation must be normalized to [-180, 180)"
        }
    }
}

private let holdPathKappa = 0.5522847498307936
private let holdPathEpsilon = CGFloat.ulpOfOne
private let maximumHoldControlCoordinate = 1_000_000.0

extension BoardPathCommand {
    /// The point the curve actually passes through at the end of this command.
    var holdEndPoint: CGPoint? {
        switch self {
        case .move(let destination): destination
        case .line(let destination): destination
        case .quad(let destination, _): destination
        case .curve(let destination, _, _): destination
        case .close: nil
        }
    }

    var isHoldCloseCommand: Bool {
        if case .close = self { return true }
        return false
    }

    var isHoldMoveCommand: Bool {
        if case .move = self { return true }
        return false
    }

    func mapPoints(_ transform: (CGPoint) -> CGPoint) -> BoardPathCommand {
        switch self {
        case .move(let point):
            .move(transform(point))
        case .line(let point):
            .line(transform(point))
        case .quad(let to, let control):
            .quad(to: transform(to), control: transform(control))
        case .curve(let to, let control1, let control2):
            .curve(to: transform(to), control1: transform(control1), control2: transform(control2))
        case .close:
            .close
        }
    }
}

enum HoldPathEngine {

    static func bounds(of commands: [BoardPathCommand]) -> HoldPathBounds {
        var minX = CGFloat.infinity
        var minY = CGFloat.infinity
        var maxX = -CGFloat.infinity
        var maxY = -CGFloat.infinity
        func include(_ point: CGPoint) {
            minX = Swift.min(minX, point.x)
            minY = Swift.min(minY, point.y)
            maxX = Swift.max(maxX, point.x)
            maxY = Swift.max(maxY, point.y)
        }
        var current: CGPoint?
        var start: CGPoint?
        for command in commands {
            switch command {
            case .move(let destination):
                current = destination
                start = destination
                include(destination)
            case .line(let destination):
                current = destination
                include(destination)
            case .quad(let destination, let control):
                if let current {
                    includeQuadraticExtrema(current, control, destination, include)
                }
                current = destination
            case .curve(let destination, let control1, let control2):
                if let current {
                    includeCubicExtrema(current, control1, control2, destination, include)
                }
                current = destination
            case .close:
                if let start {
                    include(start)
                    current = start
                }
            }
        }
        return HoldPathBounds(minX: minX, minY: minY, maxX: maxX, maxY: maxY)
    }

    static func validBounds(of commands: [BoardPathCommand]) throws -> HoldPathBounds {
        let computedBounds = bounds(of: commands)
        let values = [computedBounds.minX, computedBounds.minY, computedBounds.maxX, computedBounds.maxY]
        guard values.allSatisfy({ $0.isFinite }), computedBounds.width.isFinite,
              computedBounds.height.isFinite, computedBounds.width > 0,
              computedBounds.height > 0 else {
            throw HoldPathEngineError.outlineNeedsNonZeroWidthAndHeight
        }
        return computedBounds
    }

    static func createOutlineShapePath(
        of commands: [BoardPathCommand],
        preset: OutlinePreset
    ) throws -> [BoardPathCommand] {
        let pathBounds = try validBounds(of: commands)
        let width = pathBounds.width
        let height = pathBounds.height
        let center = pathBounds.center
        switch preset {
        case .oval:
            return ellipseCommands(center.x, center.y, width / 2, height / 2)
        case .circle:
            let radius = Swift.min(width, height) / 2
            return ellipseCommands(center.x, center.y, radius, radius)
        case .pill:
            return pillCommands(pathBounds)
        case .roundedRectangle:
            return roundedRectangleCommands(pathBounds, Swift.min(width, height) / 5)
        case .rectangle:
            return rectangleCommands(pathBounds)
        }
    }

    static func constrainedOutlineModel(
        commands: [BoardPathCommand],
        constraint: ShapeConstraint
    ) throws -> ConstrainedOutlineModel {
        let shapeConstraint = try constraint.validated()
        let worldBounds = try validBounds(of: commands)
        let center = worldBounds.center
        let rotationRadians = CGFloat(shapeConstraint.rotationDegrees * Double.pi / 180)
        var rotated = commands
        rotatePath(&rotated, angleRadians: -rotationRadians, pivot: center)
        let intrinsicBounds = try validBounds(of: rotated)
        let midX = (intrinsicBounds.minX + intrinsicBounds.maxX) / 2
        let midY = (intrinsicBounds.minY + intrinsicBounds.maxY) / 2
        let localHandles: [ConstrainedHandle: CGPoint] = [
            .nw: CGPoint(x: intrinsicBounds.minX, y: intrinsicBounds.minY),
            .n: CGPoint(x: midX, y: intrinsicBounds.minY),
            .ne: CGPoint(x: intrinsicBounds.maxX, y: intrinsicBounds.minY),
            .e: CGPoint(x: intrinsicBounds.maxX, y: midY),
            .se: CGPoint(x: intrinsicBounds.maxX, y: intrinsicBounds.maxY),
            .s: CGPoint(x: midX, y: intrinsicBounds.maxY),
            .sw: CGPoint(x: intrinsicBounds.minX, y: intrinsicBounds.maxY),
            .w: CGPoint(x: intrinsicBounds.minX, y: midY),
        ]
        let handles = localHandles.mapValues { handlePoint in
            rotatePoint(handlePoint, pivot: center, angleRadians: rotationRadians)
        }
        return ConstrainedOutlineModel(
            center: center,
            rotationDegrees: shapeConstraint.rotationDegrees,
            intrinsicBounds: intrinsicBounds,
            handles: handles
        )
    }

    static func resizeConstrainedOutline(
        commands: [BoardPathCommand],
        constraint: ShapeConstraint,
        handle: ConstrainedHandle,
        pointer: CGPoint,
        minimumWidth: CGFloat = 2,
        minimumHeight: CGFloat = 2
    ) throws -> ConstrainedResizeResult {
        let shapeConstraint = try constraint.validated()
        guard pointer.x.isFinite, pointer.y.isFinite else {
            throw HoldPathEngineError.resizePointerMustBeFinite
        }
        guard minimumWidth.isFinite, minimumWidth > 0,
              minimumHeight.isFinite, minimumHeight > 0 else {
            throw HoldPathEngineError.minimumSizeMustBePositive
        }
        let model = try constrainedOutlineModel(commands: commands, constraint: shapeConstraint)
        let rotationRadians = CGFloat(shapeConstraint.rotationDegrees * Double.pi / 180)
        let localPointer = rotatePoint(pointer, pivot: model.center, angleRadians: -rotationRadians)
        guard localPointer.x.isFinite, localPointer.y.isFinite else {
            throw HoldPathEngineError.constrainedResizeLocalPointerMustBeFinite
        }
        var resizeBounds = model.intrinsicBounds
        let originalWidth = resizeBounds.width
        let originalHeight = resizeBounds.height

        if handle.includesWest {
            resizeBounds.minX = Swift.min(localPointer.x, resizeBounds.maxX - minimumWidth)
        }
        if handle.includesEast {
            resizeBounds.maxX = Swift.max(localPointer.x, resizeBounds.minX + minimumWidth)
        }
        if handle.includesNorth {
            resizeBounds.minY = Swift.min(localPointer.y, resizeBounds.maxY - minimumHeight)
        }
        if handle.includesSouth {
            resizeBounds.maxY = Swift.max(localPointer.y, resizeBounds.minY + minimumHeight)
        }

        if shapeConstraint.shape == .circle {
            lockCircleBounds(
                &resizeBounds,
                originalBounds: model.intrinsicBounds,
                handle: handle,
                originalWidth: originalWidth,
                originalHeight: originalHeight,
                minimumSize: Swift.max(minimumWidth, minimumHeight)
            )
        }
        try assertFiniteResizeBounds(resizeBounds)

        let resizedCommands = constrainedPrimitiveCommands(shapeConstraint.shape, resizeBounds)
        try assertFiniteCommands(resizedCommands)
        var rotatedCommands = resizedCommands
        rotatePath(&rotatedCommands, angleRadians: rotationRadians, pivot: model.center)
        try assertFiniteCommands(rotatedCommands)
        return ConstrainedResizeResult(commands: rotatedCommands, shapeConstraint: shapeConstraint)
    }

    static func moveVertex(
        _ commands: inout [BoardPathCommand],
        index: Int,
        deltaX: CGFloat,
        deltaY: CGFloat
    ) {
        guard commands.indices.contains(index), !commands[index].isHoldCloseCommand else { return }
        switch commands[index] {
        case .close:
            break
        case .move(let destination):
            commands[index] = .move(translate(destination, deltaX, deltaY))
        case .line(let destination):
            commands[index] = .line(translate(destination, deltaX, deltaY))
        case .quad(let destination, let control):
            commands[index] = .quad(
                to: translate(destination, deltaX, deltaY),
                control: translate(control, deltaX, deltaY)
            )
        case .curve(let destination, let control1, let control2):
            commands[index] = .curve(
                to: translate(destination, deltaX, deltaY),
                control1: translate(control1, deltaX, deltaY),
                control2: translate(control2, deltaX, deltaY)
            )
        }
    }

    static func addVertex(
        _ commands: inout [BoardPathCommand],
        afterIndex: Int,
        x: CGFloat,
        y: CGFloat
    ) {
        guard commands.indices.contains(afterIndex), !commands[afterIndex].isHoldCloseCommand else {
            return
        }
        let nextIndex = (afterIndex + 1) % commands.count
        guard commands.indices.contains(nextIndex) else { return }
        let next = commands[nextIndex]
        if next.isHoldMoveCommand { return }
        guard let start = commands[afterIndex].holdEndPoint else { return }

        switch next {
        case .quad(let endpoint, let control):
            let midpoint = quadraticPoint(start, control, endpoint, 0.5)
            commands.replaceSubrange(nextIndex...nextIndex, with: [
                .quad(to: midpoint, control: interpolate(start, control, 0.5)),
                .quad(to: endpoint, control: interpolate(control, endpoint, 0.5)),
            ])
        case .curve(let endpoint, let firstControl, let secondControl):
            let split = subdivideCubic(start, firstControl, secondControl, endpoint, 0.5)
            commands.replaceSubrange(nextIndex...nextIndex, with: [split.left, split.right])
        default:
            commands.insert(.line(CGPoint(x: x, y: y)), at: nextIndex)
        }
    }

    static func addInflectionPoint(
        _ commands: inout [BoardPathCommand],
        afterIndex: Int,
        point: CGPoint
    ) -> Bool {
        guard commands.indices.contains(afterIndex),
              let start = commands[afterIndex].holdEndPoint else {
            return false
        }
        let curveIndex = afterIndex + 1
        guard commands.indices.contains(curveIndex) else { return false }
        switch commands[curveIndex] {
        case .quad(let endpoint, let control):
            let amount = nearestCurveAmount(start, curve: .quad(to: endpoint, control: control), point: point)
            guard amount > 0, amount < 1 else { return false }
            let split = subdivideQuadratic(start, control, endpoint, amount)
            commands.replaceSubrange(curveIndex...curveIndex, with: [split.left, split.right])
            return true
        case .curve(let endpoint, let firstControl, let secondControl):
            let amount = nearestCurveAmount(
                start,
                curve: .curve(to: endpoint, control1: firstControl, control2: secondControl),
                point: point
            )
            guard amount > 0, amount < 1 else { return false }
            let split = subdivideCubic(start, firstControl, secondControl, endpoint, amount)
            commands.replaceSubrange(curveIndex...curveIndex, with: [split.left, split.right])
            return true
        default:
            return false
        }
    }

    static func isInflectionVertex(_ commands: [BoardPathCommand], index: Int) -> Bool {
        mergedInflectionCurve(commands, index) != nil
    }

    static func deleteVertex(_ commands: inout [BoardPathCommand], index: Int) {
        guard commands.indices.contains(index), !commands[index].isHoldCloseCommand else { return }
        guard !(commands[index].isHoldMoveCommand && index != 0) else { return }
        let drawableVertexCount = commands.filter { !$0.isHoldCloseCommand }.count
        guard drawableVertexCount > 3 else { return }

        if index == 0 {
            guard commands.count > 1, !commands[1].isHoldCloseCommand,
                  let nextEnd = commands[1].holdEndPoint else { return }
            commands[0] = .move(nextEnd)
            commands.remove(at: 1)
            return
        }

        if let mergedCurve = mergedInflectionCurve(commands, index) {
            commands.replaceSubrange(index...(index + 1), with: [mergedCurve])
            return
        }

        let next = commands[(index + 1) % commands.count]
        commands.remove(at: index)

        switch next {
        case .quad, .curve:
            let nextCommandIndex = index % commands.count
            guard commands.indices.contains(nextCommandIndex),
                  let endpoint = commands[nextCommandIndex].holdEndPoint else { return }
            commands[nextCommandIndex] = .line(endpoint)
        default:
            break
        }
    }

    static func roundVertex(_ commands: inout [BoardPathCommand], index: Int) -> Bool {
        if index == 0 { return roundStartVertex(&commands) }
        if index == commands.count - 2 { return roundLastVertex(&commands) }
        guard index > 0, index < commands.count, index + 1 < commands.count else { return false }
        guard case .line(let corner) = commands[index],
              case .line(let end) = commands[index + 1],
              let start = commands[index - 1].holdEndPoint else {
            return false
        }
        guard !pointsMatch(start, corner), !pointsMatch(corner, end),
              !areCollinear(start, corner, end) else {
            return false
        }

        let trim: CGFloat = 0.2
        let incoming = interpolate(corner, start, trim)
        let outgoing = interpolate(corner, end, trim)
        commands[index] = .line(incoming)
        commands.replaceSubrange((index + 1)...(index + 1), with: [
            .quad(to: outgoing, control: corner),
            .line(end),
        ])
        return true
    }

    /// Replaces a straight segment with a cubic whose controls sit at the
    /// thirds; the session marks the resulting document command bendable so
    /// later drags bend the curve through the pointer.
    static func makeSegmentBendable(_ commands: inout [BoardPathCommand], afterIndex: Int) -> Bool {
        guard commands.indices.contains(afterIndex),
              let start = commands[afterIndex].holdEndPoint else {
            return false
        }
        let nextIndex = afterIndex + 1
        let next: BoardPathCommand? = commands.indices.contains(nextIndex) ? commands[nextIndex] : nil
        let closingEdge = next?.isHoldCloseCommand == true && nextIndex == commands.count - 1
        var end: CGPoint?
        if closingEdge, case .move(let startPoint)? = commands.first {
            end = startPoint
        } else if case .line(let endPoint)? = next {
            end = endPoint
        }
        guard let end, !pointsMatch(start, end) else { return false }
        let curve = BoardPathCommand.curve(
            to: end,
            control1: interpolate(start, end, 1 / 3),
            control2: interpolate(start, end, 2 / 3)
        )
        if closingEdge {
            commands.replaceSubrange(nextIndex...nextIndex, with: [curve, .close])
        } else {
            commands[nextIndex] = curve
        }
        return true
    }

    /// Moves a marked bendable cubic's controls so the curve midpoint passes
    /// through the pointer while both anchors stay fixed.
    static func bendSegmentToPoint(
        _ commands: inout [BoardPathCommand],
        afterIndex: Int,
        point: CGPoint
    ) -> Bool {
        guard commands.indices.contains(afterIndex),
              let start = commands[afterIndex].holdEndPoint else {
            return false
        }
        let nextIndex = afterIndex + 1
        guard commands.indices.contains(nextIndex),
              point.x.isFinite, point.y.isFinite else {
            return false
        }
        guard case .curve(let end, _, _) = commands[nextIndex] else { return false }
        let control = CGPoint(
            x: (8 * point.x - start.x - end.x) / 6,
            y: (8 * point.y - start.y - end.y) / 6
        )
        commands[nextIndex] = .curve(to: end, control1: control, control2: control)
        return true
    }

    static func makeSegmentStraight(_ commands: inout [BoardPathCommand], afterIndex: Int) -> Bool {
        guard commands.indices.contains(afterIndex),
              let start = commands[afterIndex].holdEndPoint else {
            return false
        }
        let nextIndex = afterIndex + 1
        guard commands.indices.contains(nextIndex) else { return false }
        switch commands[nextIndex] {
        case .quad(let end, _), .curve(let end, _, _):
            guard !pointsMatch(start, end) else { return false }
            commands[nextIndex] = .line(end)
            return true
        default:
            return false
        }
    }

    static func snapSegmentHorizontal(_ commands: inout [BoardPathCommand], afterIndex: Int) -> Bool {
        snapSegmentToAxis(&commands, afterIndex: afterIndex, axis: .horizontal)
    }

    static func snapSegmentVertical(_ commands: inout [BoardPathCommand], afterIndex: Int) -> Bool {
        snapSegmentToAxis(&commands, afterIndex: afterIndex, axis: .vertical)
    }

    static func rotatePath(
        _ commands: inout [BoardPathCommand],
        angleRadians: CGFloat,
        pivot: CGPoint
    ) {
        for index in commands.indices {
            switch commands[index] {
            case .close:
                continue
            case .move(let destination):
                commands[index] = .move(rotatePoint(destination, pivot: pivot, angleRadians: angleRadians))
            case .line(let destination):
                commands[index] = .line(rotatePoint(destination, pivot: pivot, angleRadians: angleRadians))
            case .quad(let destination, let control):
                commands[index] = .quad(
                    to: rotatePoint(destination, pivot: pivot, angleRadians: angleRadians),
                    control: rotatePoint(control, pivot: pivot, angleRadians: angleRadians)
                )
            case .curve(let destination, let control1, let control2):
                commands[index] = .curve(
                    to: rotatePoint(destination, pivot: pivot, angleRadians: angleRadians),
                    control1: rotatePoint(control1, pivot: pivot, angleRadians: angleRadians),
                    control2: rotatePoint(control2, pivot: pivot, angleRadians: angleRadians)
                )
            }
        }
    }

    /// Rejects edits that the strict package loader would refuse so a saved
    /// override always loads through BoardPackageStore rules.
    static func validateEditableContour(_ commands: [BoardPathCommand]) throws {
        guard let first = commands.first, first.isHoldMoveCommand else {
            throw BoardGeometryAdaptationError.invalid("path must begin with move")
        }
        let moveCount = commands.lazy.filter(\.isHoldMoveCommand).count
        let closeCount = commands.lazy.filter(\.isHoldCloseCommand).count
        guard moveCount == 1, closeCount == 1, commands.last?.isHoldCloseCommand == true else {
            throw BoardGeometryAdaptationError.invalid("path must contain exactly one closed contour")
        }
        for command in commands {
            switch command {
            case .move(let destination):
                try validateFinitePoint(destination, commandName: "move")
            case .line(let destination):
                try validateFinitePoint(destination, commandName: "line")
            case .quad(let destination, let control):
                try validateFinitePoint(destination, commandName: "quad")
                try validateFinitePoint(control, commandName: "quad")
            case .curve(let destination, let control1, let control2):
                try validateFinitePoint(destination, commandName: "curve")
                try validateFinitePoint(control1, commandName: "curve")
                try validateFinitePoint(control2, commandName: "curve")
            case .close:
                break
            }
        }
        try commands.validateContour()
    }

    /// Contour validation is topological and space-independent: the loader
    /// canonicalizes both axes before comparing points, so editor-space
    /// contours validate identically to canonical piece-normalized ones.
    /// Canonical unit-square anchors are enforced separately when document
    /// commands convert through `holdPathCommands()`.
    private static func validateFinitePoint(_ point: CGPoint, commandName: String) throws {
        guard point.x.isFinite, point.y.isFinite else {
            throw BoardGeometryAdaptationError.invalid("invalid \(commandName) path command")
        }
    }

    private enum SnapAxis {
        case horizontal
        case vertical
    }

    private static func snapSegmentToAxis(
        _ commands: inout [BoardPathCommand],
        afterIndex: Int,
        axis: SnapAxis
    ) -> Bool {
        guard commands.indices.contains(afterIndex),
              let start = commands[afterIndex].holdEndPoint else {
            return false
        }
        let nextIndex = afterIndex + 1
        let next: BoardPathCommand? = commands.indices.contains(nextIndex) ? commands[nextIndex] : nil
        let closingEdge = next?.isHoldCloseCommand == true && nextIndex == commands.count - 1
        var end: CGPoint?
        if closingEdge, case .move(let startPoint)? = commands.first {
            end = startPoint
        } else if case .line(let endPoint)? = next {
            end = endPoint
        }
        guard let end else { return false }
        if axis == .horizontal ? start.y == end.y : start.x == end.x { return false }

        let snappedEnd = axis == .horizontal
            ? CGPoint(x: end.x, y: start.y)
            : CGPoint(x: start.x, y: end.y)
        if closingEdge {
            commands.insert(.line(snappedEnd), at: nextIndex)
        } else {
            commands[nextIndex] = .line(snappedEnd)
        }
        return true
    }

    private static func roundStartVertex(_ commands: inout [BoardPathCommand]) -> Bool {
        guard commands.count > 2 else { return false }
        let lastIndex = commands.count - 1
        guard case .move(let corner) = commands[0],
              case .line(let end) = commands[1],
              case .line = commands[lastIndex - 1],
              commands[lastIndex].isHoldCloseCommand else {
            return false
        }
        guard let start = commands[lastIndex - 1].holdEndPoint,
              !pointsMatch(start, corner), !pointsMatch(corner, end),
              !areCollinear(start, corner, end) else {
            return false
        }

        let trim: CGFloat = 0.2
        commands[0] = .move(interpolate(corner, start, trim))
        commands.replaceSubrange(1...1, with: [
            .quad(to: interpolate(corner, end, trim), control: corner),
            .line(end),
        ])
        return true
    }

    private static func roundLastVertex(_ commands: inout [BoardPathCommand]) -> Bool {
        guard commands.count > 3 else { return false }
        let lastIndex = commands.count - 1
        guard case .line = commands[lastIndex - 2],
              case .line(let corner) = commands[lastIndex - 1],
              commands[lastIndex].isHoldCloseCommand,
              case .move(let end) = commands[0] else {
            return false
        }
        guard let start = commands[lastIndex - 2].holdEndPoint,
              !pointsMatch(start, corner), !pointsMatch(corner, end),
              !areCollinear(start, corner, end) else {
            return false
        }

        let trim: CGFloat = 0.2
        commands[lastIndex - 1] = .line(interpolate(corner, start, trim))
        commands.replaceSubrange(lastIndex...lastIndex, with: [
            .quad(to: interpolate(corner, end, trim), control: corner),
            .close,
        ])
        return true
    }

    private static func lockCircleBounds(
        _ bounds: inout HoldPathBounds,
        originalBounds: HoldPathBounds,
        handle: ConstrainedHandle,
        originalWidth: CGFloat,
        originalHeight: CGFloat,
        minimumSize: CGFloat
    ) {
        let width = bounds.width
        let height = bounds.height
        var diameter: CGFloat
        if handle.changesX && handle.changesY {
            diameter = abs(width - originalWidth) >= abs(height - originalHeight) ? width : height
        } else if handle.changesX {
            diameter = width
        } else {
            diameter = height
        }
        diameter = Swift.max(minimumSize, diameter)

        if handle.changesX {
            if handle.includesWest {
                bounds.minX = bounds.maxX - diameter
            } else {
                bounds.maxX = bounds.minX + diameter
            }
        } else {
            let centerX = (originalBounds.minX + originalBounds.maxX) / 2
            bounds.minX = centerX - diameter / 2
            bounds.maxX = centerX + diameter / 2
        }
        if handle.changesY {
            if handle.includesNorth {
                bounds.minY = bounds.maxY - diameter
            } else {
                bounds.maxY = bounds.minY + diameter
            }
        } else {
            let centerY = (originalBounds.minY + originalBounds.maxY) / 2
            bounds.minY = centerY - diameter / 2
            bounds.maxY = centerY + diameter / 2
        }
    }

    private static func constrainedPrimitiveCommands(
        _ shape: ShapeConstraintShape,
        _ bounds: HoldPathBounds
    ) -> [BoardPathCommand] {
        let width = bounds.width
        let height = bounds.height
        let center = bounds.center
        switch shape {
        case .oval, .circle:
            return ellipseCommands(center.x, center.y, width / 2, height / 2)
        case .pill:
            return pillCommands(bounds)
        case .roundedRectangle:
            return roundedRectangleCommands(bounds, Swift.min(width, height) / 5)
        case .rectangle:
            return rectangleCommands(bounds)
        }
    }

    private static func assertFiniteResizeBounds(_ bounds: HoldPathBounds) throws {
        let values = [bounds.minX, bounds.minY, bounds.maxX, bounds.maxY]
        guard values.allSatisfy({ $0.isFinite }), bounds.width.isFinite, bounds.height.isFinite else {
            throw HoldPathEngineError.constrainedResizeDimensionsMustBeFinite
        }
    }

    private static func assertFiniteCommands(_ commands: [BoardPathCommand]) throws {
        for command in commands {
            switch command {
            case .close:
                continue
            case .move(let destination):
                try assertFinitePoint(destination)
            case .line(let destination):
                try assertFinitePoint(destination)
            case .quad(let destination, let control):
                try assertFinitePoint(destination)
                try assertFinitePoint(control)
            case .curve(let destination, let control1, let control2):
                try assertFinitePoint(destination)
                try assertFinitePoint(control1)
                try assertFinitePoint(control2)
            }
        }
    }

    private static func assertFinitePoint(_ point: CGPoint) throws {
        guard point.x.isFinite, point.y.isFinite else {
            throw HoldPathEngineError.constrainedResizeCoordinatesMustBeFinite
        }
    }

    static func translate(
        _ point: CGPoint,
        _ deltaX: CGFloat,
        _ deltaY: CGFloat
    ) -> CGPoint {
        CGPoint(x: point.x + deltaX, y: point.y + deltaY)
    }

    /// Translates every anchor and control point by the same board-space delta.
    static func translatePath(
        _ commands: inout [BoardPathCommand],
        deltaX: CGFloat,
        deltaY: CGFloat
    ) {
        commands = commands.map { command in
            command.mapPoints { Self.translate($0, deltaX, deltaY) }
        }
    }

    private static func rotatePoint(
        _ point: CGPoint,
        pivot: CGPoint,
        angleRadians: CGFloat
    ) -> CGPoint {
        let cosine = cos(angleRadians)
        let sine = sin(angleRadians)
        let deltaX = point.x - pivot.x
        let deltaY = point.y - pivot.y
        return CGPoint(
            x: pivot.x + deltaX * cosine - deltaY * sine,
            y: pivot.y + deltaX * sine + deltaY * cosine
        )
    }

    private static func includeQuadraticExtrema(
        _ start: CGPoint,
        _ control: CGPoint,
        _ end: CGPoint,
        _ include: (CGPoint) -> Void
    ) {
        include(start)
        include(end)
        let starts = [start.x, start.y]
        let controls = [control.x, control.y]
        let ends = [end.x, end.y]
        for axis in 0..<2 {
            let denominator = starts[axis] - 2 * controls[axis] + ends[axis]
            if denominator == 0 { continue }
            let amount = (starts[axis] - controls[axis]) / denominator
            if amount > 0, amount < 1 {
                include(quadraticPoint(start, control, end, amount))
            }
        }
    }

    private static func includeCubicExtrema(
        _ start: CGPoint,
        _ firstControl: CGPoint,
        _ secondControl: CGPoint,
        _ end: CGPoint,
        _ include: (CGPoint) -> Void
    ) {
        include(start)
        include(end)
        let starts = [start.x, start.y]
        let firsts = [firstControl.x, firstControl.y]
        let seconds = [secondControl.x, secondControl.y]
        let ends = [end.x, end.y]
        for axis in 0..<2 {
            let a = -starts[axis] + 3 * firsts[axis] - 3 * seconds[axis] + ends[axis]
            let b = 2 * (starts[axis] - 2 * firsts[axis] + seconds[axis])
            let c = firsts[axis] - starts[axis]
            for amount in quadraticRoots(a, b, c) where amount > 0 && amount < 1 {
                include(cubicPoint(start, firstControl, secondControl, end, amount))
            }
        }
    }

    private static func quadraticRoots(_ a: CGFloat, _ b: CGFloat, _ c: CGFloat) -> [CGFloat] {
        if abs(a) < holdPathEpsilon {
            return abs(b) < holdPathEpsilon ? [] : [-c / b]
        }
        let discriminant = b * b - 4 * a * c
        if discriminant < 0 { return [] }
        let root = discriminant.squareRoot()
        return [(-b + root) / (2 * a), (-b - root) / (2 * a)]
    }

    private static func ellipseCommands(
        _ centerX: CGFloat,
        _ centerY: CGFloat,
        _ radiusX: CGFloat,
        _ radiusY: CGFloat
    ) -> [BoardPathCommand] {
        let kappa = CGFloat(holdPathKappa)
        return [
            .move(CGPoint(x: centerX, y: centerY - radiusY)),
            .curve(
                to: CGPoint(x: centerX + radiusX, y: centerY),
                control1: CGPoint(x: centerX + kappa * radiusX, y: centerY - radiusY),
                control2: CGPoint(x: centerX + radiusX, y: centerY - kappa * radiusY)
            ),
            .curve(
                to: CGPoint(x: centerX, y: centerY + radiusY),
                control1: CGPoint(x: centerX + radiusX, y: centerY + kappa * radiusY),
                control2: CGPoint(x: centerX + kappa * radiusX, y: centerY + radiusY)
            ),
            .curve(
                to: CGPoint(x: centerX - radiusX, y: centerY),
                control1: CGPoint(x: centerX - kappa * radiusX, y: centerY + radiusY),
                control2: CGPoint(x: centerX - radiusX, y: centerY + kappa * radiusY)
            ),
            .curve(
                to: CGPoint(x: centerX, y: centerY - radiusY),
                control1: CGPoint(x: centerX - radiusX, y: centerY - kappa * radiusY),
                control2: CGPoint(x: centerX - kappa * radiusX, y: centerY - radiusY)
            ),
            .close,
        ]
    }

    private static func rectangleCommands(_ bounds: HoldPathBounds) -> [BoardPathCommand] {
        [
            .move(CGPoint(x: bounds.minX, y: bounds.minY)),
            .line(CGPoint(x: bounds.maxX, y: bounds.minY)),
            .line(CGPoint(x: bounds.maxX, y: bounds.maxY)),
            .line(CGPoint(x: bounds.minX, y: bounds.maxY)),
            .close,
        ]
    }

    static func roundedRectangleCommands(
        _ bounds: HoldPathBounds,
        _ radius: CGFloat
    ) -> [BoardPathCommand] {
        let kappa = CGFloat(holdPathKappa)
        var commands: [BoardPathCommand] = [
            .move(CGPoint(x: bounds.minX + radius, y: bounds.minY)),
            .line(CGPoint(x: bounds.maxX - radius, y: bounds.minY)),
            .curve(
                to: CGPoint(x: bounds.maxX, y: bounds.minY + radius),
                control1: CGPoint(x: bounds.maxX - radius + kappa * radius, y: bounds.minY),
                control2: CGPoint(x: bounds.maxX, y: bounds.minY + radius - kappa * radius)
            ),
            .line(CGPoint(x: bounds.maxX, y: bounds.maxY - radius)),
            .curve(
                to: CGPoint(x: bounds.maxX - radius, y: bounds.maxY),
                control1: CGPoint(x: bounds.maxX, y: bounds.maxY - radius + kappa * radius),
                control2: CGPoint(x: bounds.maxX - radius + kappa * radius, y: bounds.maxY)
            ),
            .line(CGPoint(x: bounds.minX + radius, y: bounds.maxY)),
            .curve(
                to: CGPoint(x: bounds.minX, y: bounds.maxY - radius),
                control1: CGPoint(x: bounds.minX + radius - kappa * radius, y: bounds.maxY),
                control2: CGPoint(x: bounds.minX, y: bounds.maxY - radius + kappa * radius)
            ),
            .line(CGPoint(x: bounds.minX, y: bounds.minY + radius)),
            .curve(
                to: CGPoint(x: bounds.minX + radius, y: bounds.minY),
                control1: CGPoint(x: bounds.minX, y: bounds.minY + radius - kappa * radius),
                control2: CGPoint(x: bounds.minX + radius - kappa * radius, y: bounds.minY)
            ),
            .close,
        ]
        // A full-radius corner collapses its straight edge onto the previous
        // anchor; drop those degenerate segments so the contour stays valid.
        let contourEpsilon = CGFloat(1e-9)
        var result: [BoardPathCommand] = []
        var previousAnchor: CGPoint?
        for command in commands {
            switch command {
            case .line(let destination):
                if let previousAnchor,
                   abs(previousAnchor.x - destination.x) <= contourEpsilon,
                   abs(previousAnchor.y - destination.y) <= contourEpsilon {
                    continue
                }
                result.append(command)
                previousAnchor = destination
            default:
                if let anchor = command.boardAnchor {
                    previousAnchor = anchor
                }
                result.append(command)
            }
        }
        return result
    }

    private static func pillCommands(_ bounds: HoldPathBounds) -> [BoardPathCommand] {
        let width = bounds.width
        let height = bounds.height
        let kappa = CGFloat(holdPathKappa)
        if width >= height {
            let radius = height / 2
            let centerY = bounds.minY + radius
            return [
                .move(CGPoint(x: bounds.minX + radius, y: bounds.minY)),
                .line(CGPoint(x: bounds.maxX - radius, y: bounds.minY)),
                .curve(
                    to: CGPoint(x: bounds.maxX, y: centerY),
                    control1: CGPoint(x: bounds.maxX - radius + kappa * radius, y: bounds.minY),
                    control2: CGPoint(x: bounds.maxX, y: centerY - kappa * radius)
                ),
                .curve(
                    to: CGPoint(x: bounds.maxX - radius, y: bounds.maxY),
                    control1: CGPoint(x: bounds.maxX, y: centerY + kappa * radius),
                    control2: CGPoint(x: bounds.maxX - radius + kappa * radius, y: bounds.maxY)
                ),
                .line(CGPoint(x: bounds.minX + radius, y: bounds.maxY)),
                .curve(
                    to: CGPoint(x: bounds.minX, y: centerY),
                    control1: CGPoint(x: bounds.minX + radius - kappa * radius, y: bounds.maxY),
                    control2: CGPoint(x: bounds.minX, y: centerY + kappa * radius)
                ),
                .curve(
                    to: CGPoint(x: bounds.minX + radius, y: bounds.minY),
                    control1: CGPoint(x: bounds.minX, y: centerY - kappa * radius),
                    control2: CGPoint(x: bounds.minX + radius - kappa * radius, y: bounds.minY)
                ),
                .close,
            ]
        }
        let radius = width / 2
        let centerX = bounds.minX + radius
        return [
            .move(CGPoint(x: bounds.minX, y: bounds.minY + radius)),
            .line(CGPoint(x: bounds.minX, y: bounds.maxY - radius)),
            .curve(
                to: CGPoint(x: centerX, y: bounds.maxY),
                control1: CGPoint(x: bounds.minX, y: bounds.maxY - radius + kappa * radius),
                control2: CGPoint(x: centerX - kappa * radius, y: bounds.maxY)
            ),
            .curve(
                to: CGPoint(x: bounds.maxX, y: bounds.maxY - radius),
                control1: CGPoint(x: centerX + kappa * radius, y: bounds.maxY),
                control2: CGPoint(x: bounds.maxX, y: bounds.maxY - radius + kappa * radius)
            ),
            .line(CGPoint(x: bounds.maxX, y: bounds.minY + radius)),
            .curve(
                to: CGPoint(x: centerX, y: bounds.minY),
                control1: CGPoint(x: bounds.maxX, y: bounds.minY + radius - kappa * radius),
                control2: CGPoint(x: centerX + kappa * radius, y: bounds.minY)
            ),
            .curve(
                to: CGPoint(x: bounds.minX, y: bounds.minY + radius),
                control1: CGPoint(x: centerX - kappa * radius, y: bounds.minY),
                control2: CGPoint(x: bounds.minX, y: bounds.minY + radius - kappa * radius)
            ),
            .close,
        ]
    }

    private static func pointsMatch(_ left: CGPoint, _ right: CGPoint) -> Bool {
        left.x == right.x && left.y == right.y
    }

    private static func areCollinear(_ start: CGPoint, _ corner: CGPoint, _ end: CGPoint) -> Bool {
        let incomingX = corner.x - start.x
        let incomingY = corner.y - start.y
        let outgoingX = end.x - corner.x
        let outgoingY = end.y - corner.y
        return abs(incomingX * outgoingY - incomingY * outgoingX) <= 1e-9
    }

    private static func interpolate(_ start: CGPoint, _ end: CGPoint, _ amount: CGFloat) -> CGPoint {
        CGPoint(
            x: start.x + (end.x - start.x) * amount,
            y: start.y + (end.y - start.y) * amount
        )
    }

    private static func quadraticPoint(
        _ start: CGPoint,
        _ control: CGPoint,
        _ end: CGPoint,
        _ amount: CGFloat
    ) -> CGPoint {
        let inverse = 1 - amount
        return CGPoint(
            x: inverse * inverse * start.x + 2 * inverse * amount * control.x + amount * amount * end.x,
            y: inverse * inverse * start.y + 2 * inverse * amount * control.y + amount * amount * end.y
        )
    }

    private static func cubicPoint(
        _ start: CGPoint,
        _ firstControl: CGPoint,
        _ secondControl: CGPoint,
        _ end: CGPoint,
        _ amount: CGFloat
    ) -> CGPoint {
        let inverse = 1 - amount
        return CGPoint(
            x: inverse * inverse * inverse * start.x
                + 3 * inverse * inverse * amount * firstControl.x
                + 3 * inverse * amount * amount * secondControl.x
                + amount * amount * amount * end.x,
            y: inverse * inverse * inverse * start.y
                + 3 * inverse * inverse * amount * firstControl.y
                + 3 * inverse * amount * amount * secondControl.y
                + amount * amount * amount * end.y
        )
    }

    private struct CurveSplit {
        var left: BoardPathCommand
        var right: BoardPathCommand
    }

    private static func subdivideQuadratic(
        _ start: CGPoint,
        _ control: CGPoint,
        _ end: CGPoint,
        _ amount: CGFloat
    ) -> CurveSplit {
        let firstControl = interpolate(start, control, amount)
        let secondControl = interpolate(control, end, amount)
        let midpoint = interpolate(firstControl, secondControl, amount)
        return CurveSplit(
            left: .quad(to: midpoint, control: firstControl),
            right: .quad(to: end, control: secondControl)
        )
    }

    private static func subdivideCubic(
        _ start: CGPoint,
        _ firstControl: CGPoint,
        _ secondControl: CGPoint,
        _ end: CGPoint,
        _ amount: CGFloat
    ) -> CurveSplit {
        let firstMidpoint = interpolate(start, firstControl, amount)
        let controlMidpoint = interpolate(firstControl, secondControl, amount)
        let lastMidpoint = interpolate(secondControl, end, amount)
        let leftControl = interpolate(firstMidpoint, controlMidpoint, amount)
        let rightControl = interpolate(controlMidpoint, lastMidpoint, amount)
        let midpoint = interpolate(leftControl, rightControl, amount)
        return CurveSplit(
            left: .curve(to: midpoint, control1: firstMidpoint, control2: leftControl),
            right: .curve(to: end, control1: rightControl, control2: lastMidpoint)
        )
    }

    private static func nearestCurveAmount(
        _ start: CGPoint,
        curve: BoardPathCommand,
        point: CGPoint
    ) -> CGFloat {
        var bestAmount: CGFloat = 0
        var bestDistanceSquared = CGFloat.infinity
        let samples = 128
        for index in 1..<samples {
            let amount = CGFloat(index) / CGFloat(samples)
            let candidate = curvePoint(start, curve, amount)
            let distanceSquared = squaredDistance(candidate, point)
            if distanceSquared < bestDistanceSquared {
                bestAmount = amount
                bestDistanceSquared = distanceSquared
            }
        }
        if bestDistanceSquared < 1e-12 { return bestAmount }

        var lower = Swift.max(CGFloat(0), bestAmount - 1 / CGFloat(samples))
        var upper = Swift.min(CGFloat(1), bestAmount + 1 / CGFloat(samples))
        for _ in 0..<20 {
            let first = lower + (upper - lower) / 3
            let second = upper - (upper - lower) / 3
            if squaredDistance(curvePoint(start, curve, first), point)
                <= squaredDistance(curvePoint(start, curve, second), point) {
                upper = second
            } else {
                lower = first
            }
        }
        return (lower + upper) / 2
    }

    private static func curvePoint(
        _ start: CGPoint,
        _ curve: BoardPathCommand,
        _ amount: CGFloat
    ) -> CGPoint {
        switch curve {
        case .quad(let end, let control):
            return quadraticPoint(start, control, end, amount)
        case .curve(let end, let firstControl, let secondControl):
            return cubicPoint(start, firstControl, secondControl, end, amount)
        default:
            return start
        }
    }

    private static func squaredDistance(_ left: CGPoint, _ right: CGPoint) -> CGFloat {
        let deltaX = left.x - right.x
        let deltaY = left.y - right.y
        return deltaX * deltaX + deltaY * deltaY
    }

    private static func curveLength(_ deltaX: CGFloat, _ deltaY: CGFloat) -> CGFloat {
        (deltaX * deltaX + deltaY * deltaY).squareRoot()
    }

    private static func mergedInflectionCurve(
        _ commands: [BoardPathCommand],
        _ index: Int
    ) -> BoardPathCommand? {
        guard index > 0, index + 1 < commands.count else { return nil }
        guard let start = commands[index - 1].holdEndPoint else { return nil }
        switch (commands[index], commands[index + 1]) {
        case (.quad(let vertex, let incomingControl), .quad(let end, let outgoingControl)):
            let incomingLength = curveLength(vertex.x - incomingControl.x, vertex.y - incomingControl.y)
            let outgoingLength = curveLength(outgoingControl.x - vertex.x, outgoingControl.y - vertex.y)
            let amount = mergeAmount(start, vertex, end, incomingLength, outgoingLength)
            if let amount, hasStableSubdivisionAmount(amount) {
                let tolerance = subdivisionTolerance(amount)
                let fromStart = extrapolate(start, incomingControl, amount)
                let fromEnd = extrapolate(end, outgoingControl, 1 - amount)
                if pointsClose(fromStart, fromEnd, tolerance) {
                    let split = subdivideQuadratic(start, fromStart, end, amount)
                    if commandsMatch(split.left, .quad(to: vertex, control: incomingControl), tolerance),
                       commandsMatch(split.right, .quad(to: end, control: outgoingControl), tolerance) {
                        return .quad(to: end, control: fromStart)
                    }
                }
            }
            return fallbackQuadraticMerge(incomingControl, outgoingControl, end)
        case (
            .curve(let vertex, let leftFirstControl, let leftSecondControl),
            .curve(let end, let rightFirstControl, let rightSecondControl)
        ):
            let incomingLength = curveLength(vertex.x - leftSecondControl.x, vertex.y - leftSecondControl.y)
            let outgoingLength = curveLength(rightFirstControl.x - vertex.x, rightFirstControl.y - vertex.y)
            let amount = mergeAmount(start, vertex, end, incomingLength, outgoingLength)
            if let amount, hasStableSubdivisionAmount(amount) {
                let tolerance = subdivisionTolerance(amount)
                let mergedFirstControl = extrapolate(start, leftFirstControl, amount)
                let mergedSecondControl = extrapolate(end, rightSecondControl, 1 - amount)
                let split = subdivideCubic(start, mergedFirstControl, mergedSecondControl, end, amount)
                let left = BoardPathCommand.curve(
                    to: vertex, control1: leftFirstControl, control2: leftSecondControl
                )
                let right = BoardPathCommand.curve(
                    to: end, control1: rightFirstControl, control2: rightSecondControl
                )
                if commandsMatch(split.left, left, tolerance),
                   commandsMatch(split.right, right, tolerance) {
                    return .curve(to: end, control1: mergedFirstControl, control2: mergedSecondControl)
                }
            }
            return fallbackCubicMerge(leftFirstControl, rightSecondControl, end)
        default:
            return nil
        }
    }

    private static func hasStableSubdivisionAmount(_ amount: CGFloat) -> Bool {
        amount.isFinite && amount >= 1e-4 && amount <= 1 - 1e-4
    }

    private static func mergeAmount(
        _ start: CGPoint,
        _ vertex: CGPoint,
        _ end: CGPoint,
        _ incomingLength: CGFloat,
        _ outgoingLength: CGFloat
    ) -> CGFloat? {
        let handleLength = incomingLength + outgoingLength
        if handleLength > 1e-9 { return incomingLength / handleLength }

        let incomingChord = curveLength(vertex.x - start.x, vertex.y - start.y)
        let outgoingChord = curveLength(end.x - vertex.x, end.y - vertex.y)
        let chordLength = incomingChord + outgoingChord
        return chordLength > 1e-9 ? incomingChord / chordLength : nil
    }

    private static func fallbackQuadraticMerge(
        _ first: CGPoint,
        _ second: CGPoint,
        _ end: CGPoint
    ) -> BoardPathCommand? {
        .quad(to: end, control: stableMidpoint(first, second))
    }

    private static func stableMidpoint(_ first: CGPoint, _ second: CGPoint) -> CGPoint {
        CGPoint(x: first.x / 2 + second.x / 2, y: first.y / 2 + second.y / 2)
    }

    private static func fallbackCubicMerge(
        _ first: CGPoint,
        _ second: CGPoint,
        _ end: CGPoint
    ) -> BoardPathCommand? {
        .curve(to: end, control1: first, control2: second)
    }

    private static func extrapolate(_ start: CGPoint, _ point: CGPoint, _ amount: CGFloat) -> CGPoint {
        CGPoint(
            x: start.x + (point.x - start.x) / amount,
            y: start.y + (point.y - start.y) / amount
        )
    }

    private static func subdivisionTolerance(_ amount: CGFloat) -> CGFloat {
        4e-6 / Swift.min(amount, 1 - amount)
    }

    private static func commandsMatch(
        _ lhs: BoardPathCommand,
        _ rhs: BoardPathCommand,
        _ tolerance: CGFloat
    ) -> Bool {
        switch (lhs, rhs) {
        case (.close, .close):
            return true
        case (.move(let a), .move(let b)), (.line(let a), .line(let b)):
            return pointsClose(a, b, tolerance)
        case (.quad(let toA, let controlA), .quad(let toB, let controlB)):
            return pointsClose(toA, toB, tolerance) && pointsClose(controlA, controlB, tolerance)
        case (
            .curve(let toA, let firstA, let secondA),
            .curve(let toB, let firstB, let secondB)
        ):
            return pointsClose(toA, toB, tolerance)
                && pointsClose(firstA, firstB, tolerance)
                && pointsClose(secondA, secondB, tolerance)
        default:
            return false
        }
    }

    private static func pointsClose(
        _ left: CGPoint,
        _ right: CGPoint,
        _ tolerance: CGFloat = 1e-6
    ) -> Bool {
        abs(left.x - right.x) <= tolerance && abs(left.y - right.y) <= tolerance
    }
}

extension BoardGeometryTreatmentDocument {
    init(
        type: String,
        rimInsetFraction: Double?,
        depth: String?
    ) {
        self.type = type
        self.rimInsetFraction = rimInsetFraction
        self.depth = depth
    }
}

extension BoardGeometryPathCommandDocument {
    init(
        command: String,
        to: [Double]? = nil,
        control: [Double]? = nil,
        control1: [Double]? = nil,
        control2: [Double]? = nil
    ) {
        self.command = command
        self.to = to
        self.control = control
        self.control1 = control1
        self.control2 = control2
    }

    func holdPathCommand() throws -> BoardPathCommand {
        switch command {
        case "move":
            guard control == nil, control1 == nil, control2 == nil else {
                throw invalidHoldCommand()
            }
            return .move(try holdPoint(to))
        case "line":
            guard control == nil, control1 == nil, control2 == nil else {
                throw invalidHoldCommand()
            }
            return .line(try holdPoint(to))
        case "quad":
            guard control1 == nil, control2 == nil else { throw invalidHoldCommand() }
            return .quad(to: try holdPoint(to), control: try holdControlPoint(control))
        case "curve":
            guard control == nil else { throw invalidHoldCommand() }
            return .curve(
                to: try holdPoint(to),
                control1: try holdControlPoint(control1),
                control2: try holdControlPoint(control2)
            )
        case "close":
            guard to == nil, control == nil, control1 == nil, control2 == nil else {
                throw invalidHoldCommand()
            }
            return .close
        default:
            throw invalidHoldCommand()
        }
    }

    private func holdPoint(_ coordinates: [Double]?) throws -> CGPoint {
        guard let coordinates,
              coordinates.count == 2,
              coordinates.allSatisfy({ $0.isFinite && (0.0...1.0).contains($0) }) else {
            throw invalidHoldCommand()
        }
        return CGPoint(x: coordinates[0], y: coordinates[1])
    }

    private func holdControlPoint(_ coordinates: [Double]?) throws -> CGPoint {
        guard let coordinates,
              coordinates.count == 2,
              coordinates.allSatisfy({ $0.isFinite }) else {
            throw invalidHoldCommand()
        }
        guard coordinates.allSatisfy({ abs($0) <= maximumHoldControlCoordinate }) else {
            throw BoardGeometryAdaptationError.invalid("path coordinates are too large to represent")
        }
        return CGPoint(x: coordinates[0], y: coordinates[1])
    }

    private func invalidHoldCommand() -> BoardGeometryAdaptationError {
        .invalid("invalid \(command) path command")
    }
}

extension Array where Element == BoardGeometryPathCommandDocument {
    func holdPathCommands() throws -> [BoardPathCommand] {
        try map { try $0.holdPathCommand() }
    }
}

extension Array where Element == BoardPathCommand {
    func pathCommandDocuments() -> [BoardGeometryPathCommandDocument] {
        map { command in
            switch command {
            case .move(let destination):
                BoardGeometryPathCommandDocument(command: "move", to: [destination.x, destination.y], control: nil, control1: nil, control2: nil)
            case .line(let destination):
                BoardGeometryPathCommandDocument(command: "line", to: [destination.x, destination.y], control: nil, control1: nil, control2: nil)
            case .quad(let destination, let control):
                BoardGeometryPathCommandDocument(command: "quad", to: [destination.x, destination.y], control: [control.x, control.y], control1: nil, control2: nil)
            case .curve(let destination, let control1, let control2):
                BoardGeometryPathCommandDocument(command: "curve", to: [destination.x, destination.y], control: nil, control1: [control1.x, control1.y], control2: [control2.x, control2.y])
            case .close:
                BoardGeometryPathCommandDocument(command: "close", to: nil, control: nil, control1: nil, control2: nil)
            }
        }
    }

    /// Validates against the same rules the strict package decoder applies.
    func validateEditableContour() throws {
        try HoldPathEngine.validateEditableContour(self)
    }
}
