import SwiftUI
import UIKit

/// Resolves either the package's unchanged presentation image or a canonical
/// face plus its deterministic, world-up cord rig.
struct BoardPresentationArtwork: View {
    let board: TrainingBoard
    let presentation: BoardPresentation
    let projection: BoardPresentationGeometryProjection
    let canvasSize: CGSize

    private let geometry: BoardCordRigGeometry?
    private let directTwoAnchorRig: BoardDirectTwoAnchorCordRig?
    private let routedGeometry: BoardRoutedCordRigGeometry?
    private let routedRig: BoardRoutedCordRig?
    private let faceImage: UIImage?

    init(
        board: TrainingBoard,
        presentation: BoardPresentation,
        projection: BoardPresentationGeometryProjection,
        canvasSize: CGSize,
        geometry: BoardCordRigGeometry? = nil
    ) {
        self.board = board
        self.presentation = presentation
        self.projection = projection
        self.canvasSize = canvasSize

        if case .directTwoAnchor(let rig) = board.resolvedCordRig(for: presentation) {
            directTwoAnchorRig = rig
            routedRig = nil
            routedGeometry = nil
            self.geometry = geometry ?? BoardCordRigGeometry.make(
                rig: rig,
                projection: projection,
                in: CGRect(origin: .zero, size: canvasSize)
            )
            faceImage = BoardCatalog.packageStore.presentationArtworkImageURL(
                for: board,
                presentationID: presentation.id
            ).flatMap { UIImage(contentsOfFile: $0.path) }
        } else if case .routed(let rig) = board.resolvedCordRig(for: presentation) {
            directTwoAnchorRig = nil
            self.geometry = nil
            routedRig = rig
            routedGeometry = BoardRoutedCordRigGeometry.resolve(
                rig: rig,
                projection: projection,
                in: CGRect(origin: .zero, size: canvasSize)
            )
            faceImage = BoardCatalog.packageStore.presentationArtworkImageURL(
                for: board,
                presentationID: presentation.id
            ).flatMap { UIImage(contentsOfFile: $0.path) }
        } else if presentation.rotationDegrees != nil {
            directTwoAnchorRig = nil
            self.geometry = nil
            routedRig = nil
            routedGeometry = nil
            faceImage = BoardCatalog.packageStore.presentationArtworkImageURL(
                for: board,
                presentationID: presentation.id
            ).flatMap { UIImage(contentsOfFile: $0.path) }
        } else {
            directTwoAnchorRig = nil
            self.geometry = nil
            routedRig = nil
            routedGeometry = nil
            faceImage = nil
        }
    }

    static func geometry(
        for board: TrainingBoard,
        presentation: BoardPresentation,
        projection: BoardPresentationGeometryProjection,
        canvasSize: CGSize
    ) -> BoardCordRigGeometry? {
        guard case .directTwoAnchor(let rig) = board.resolvedCordRig(for: presentation) else {
            return nil
        }
        return BoardCordRigGeometry.make(
            rig: rig,
            projection: projection,
            in: CGRect(origin: .zero, size: canvasSize)
        )
    }

    static func routedGeometry(
        for board: TrainingBoard,
        presentation: BoardPresentation,
        projection: BoardPresentationGeometryProjection,
        canvasSize: CGSize
    ) -> BoardRoutedCordRigGeometry? {
        guard case .routed(let rig) = board.resolvedCordRig(for: presentation) else {
            return nil
        }
        return BoardRoutedCordRigGeometry.resolve(
            rig: rig,
            projection: projection,
            in: CGRect(origin: .zero, size: canvasSize)
        )
    }

    @ViewBuilder
    var body: some View {
        if let routedGeometry, let routedRig, let faceImage {
            BoardRoutedPresentationArtwork(
                faceImage: faceImage,
                rig: routedRig,
                geometry: routedGeometry
            )
        } else if let geometry, let rig = directTwoAnchorRig, let faceImage {
            BoardRiggedPresentationArtwork(
                faceImage: faceImage,
                rig: rig,
                geometry: geometry
            )
        } else if presentation.rotationDegrees != nil, let faceImage {
            Canvas { context, size in
                var faceContext = context
                faceContext.transform = projection.affineTransform(
                    in: CGRect(origin: .zero, size: size)
                )
                faceContext.draw(
                    context.resolve(Image(uiImage: faceImage)),
                    in: CGRect(origin: .zero, size: size)
                )
            }
        } else if board.resolvedCordRig(for: presentation) == nil {
            BoardPresentationImage(board: board, presentationID: presentation.id)
        }
    }

    fileprivate static func drawRiggedArtwork(
        image: Image,
        rig: BoardDirectTwoAnchorCordRig,
        geometry: BoardCordRigGeometry,
        in context: inout GraphicsContext
    ) {
        let scale = geometry.sceneRect.width / rig.sceneSize.width
        guard scale.isFinite, scale > 0 else { return }

        let resolvedImage = context.resolve(image)

        var faceContext = context
        faceContext.transform = geometry.faceTransform
        faceContext.draw(resolvedImage, in: geometry.faceRect)

        let cordPaths = [geometry.tensionPath]

        var shadowContext = context
        shadowContext.translateBy(x: 4 * scale, y: 5 * scale)
        shadowContext.addFilter(.blur(radius: 2.3 * scale))
        stroke(
            cordPaths,
            in: &shadowContext,
            color: Color.black.opacity(0.34),
            width: 35 * scale
        )
        stroke(
            cordPaths,
            in: &context,
            color: Color(red: 5 / 255, green: 6 / 255, blue: 7 / 255),
            width: 31 * scale
        )
        stroke(
            cordPaths,
            in: &context,
            color: Color(red: 21 / 255, green: 23 / 255, blue: 24 / 255),
            width: 25 * scale
        )
        drawBraid(over: cordPaths, geometry: geometry, scale: scale, in: &context)

        var ridgeContext = context
        ridgeContext.translateBy(x: -2 * scale, y: -1 * scale)
        stroke(
            cordPaths,
            in: &ridgeContext,
            color: Color(red: 196 / 255, green: 201 / 255, blue: 204 / 255)
                .opacity(0.18),
            width: 2.4 * scale,
            dash: [1.5 * scale, 5.5 * scale]
        )

        for crescent in geometry.eyeletForegroundCrescents {
            var eyeletContext = context
            eyeletContext.clip(to: crescent)
            eyeletContext.transform = geometry.faceTransform
            eyeletContext.draw(resolvedImage, in: geometry.faceRect)
        }
    }

    fileprivate static func drawRoutedArtwork(
        image: Image,
        rig: BoardRoutedCordRig,
        geometry: BoardRoutedCordRigGeometry,
        in context: inout GraphicsContext
    ) {
        let resolvedImage = context.resolve(image)

        drawRoutedCord(layer: .behindFace, rig: rig, geometry: geometry, in: &context)
        drawRoutedFace(resolvedImage, geometry: geometry, in: &context)
        drawRoutedCord(layer: .aboveFace, rig: rig, geometry: geometry, in: &context)

        for lip in geometry.radialLips {
            var occlusionContext = context
            occlusionContext.clip(to: lip.path)
            drawRoutedFace(resolvedImage, geometry: geometry, in: &occlusionContext)
        }
        for patch in geometry.facePatches {
            var occlusionContext = context
            occlusionContext.clip(to: patch.path)
            drawRoutedFace(resolvedImage, geometry: geometry, in: &occlusionContext)
        }

        drawRoutedCord(layer: .overpass, rig: rig, geometry: geometry, in: &context)
    }

    private static func drawRoutedFace(
        _ image: GraphicsContext.ResolvedImage,
        geometry: BoardRoutedCordRigGeometry,
        in context: inout GraphicsContext
    ) {
        var faceContext = context
        faceContext.transform = geometry.faceTransform
        faceContext.draw(image, in: geometry.faceRect)
    }

    private static func drawRoutedCord(
        layer: BoardRoutedCordLayer,
        rig: BoardRoutedCordRig,
        geometry: BoardRoutedCordRigGeometry,
        in context: inout GraphicsContext
    ) {
        let paths = geometry.renderableTensionPaths(in: layer)
            + geometry.authoredPaths(in: layer).map(\.path)
        guard !paths.isEmpty else { return }

        let diameter = rig.style.diameter * geometry.scale
        guard diameter.isFinite, diameter > 0 else { return }
        stroke(
            paths,
            in: &context,
            color: routedColor(rig.style.outlineColor),
            width: diameter * 1.6
        )
        stroke(
            paths,
            in: &context,
            color: routedColor(rig.style.baseColor),
            width: diameter
        )
        drawRoutedBraid(
            over: paths,
            geometry: geometry,
            diameter: diameter,
            colors: rig.style.braidColors.map(routedColor),
            in: &context
        )
    }

    private static func drawRoutedBraid(
        over paths: [Path],
        geometry: BoardRoutedCordRigGeometry,
        diameter: CGFloat,
        colors: [Color],
        in context: inout GraphicsContext
    ) {
        guard colors.count == 2 else { return }
        let clipStyle = StrokeStyle(
            lineWidth: diameter * 0.84,
            lineCap: .round,
            lineJoin: .round
        )
        var braidClip = Path()
        for path in paths {
            braidClip.addPath(path.strokedPath(clipStyle))
        }

        var braidContext = context
        braidContext.clip(to: braidClip)
        let spacing = max(diameter * 0.72, 1)
        let fiberWidth = max(diameter * 0.18, 0.5)
        let diagonalSpan = geometry.sceneRect.width + geometry.sceneRect.height
        var offset = -diagonalSpan
        var index = 0
        while offset <= diagonalSpan * 2 {
            var fiber = Path()
            if index.isMultiple(of: 2) {
                fiber.move(
                    to: CGPoint(
                        x: geometry.sceneRect.minX + offset,
                        y: geometry.sceneRect.maxY
                    )
                )
                fiber.addLine(
                    to: CGPoint(
                        x: geometry.sceneRect.minX + offset + geometry.sceneRect.height,
                        y: geometry.sceneRect.minY
                    )
                )
            } else {
                fiber.move(
                    to: CGPoint(
                        x: geometry.sceneRect.minX + offset,
                        y: geometry.sceneRect.minY
                    )
                )
                fiber.addLine(
                    to: CGPoint(
                        x: geometry.sceneRect.minX + offset + geometry.sceneRect.height,
                        y: geometry.sceneRect.maxY
                    )
                )
            }
            braidContext.stroke(
                fiber,
                with: .color(colors[index % colors.count]),
                style: StrokeStyle(
                    lineWidth: fiberWidth,
                    lineCap: .round,
                    lineJoin: .round
                )
            )
            offset += spacing
            index += 1
        }
    }

    private static func routedColor(_ hex: String) -> Color {
        guard hex.count == 7,
              hex.first == "#",
              let value = UInt64(hex.dropFirst(), radix: 16) else {
            return .clear
        }
        return Color(
            red: Double((value >> 16) & 0xFF) / 255,
            green: Double((value >> 8) & 0xFF) / 255,
            blue: Double(value & 0xFF) / 255
        )
    }

    private static func stroke(
        _ paths: [Path],
        in context: inout GraphicsContext,
        color: Color,
        width: CGFloat,
        dash: [CGFloat] = []
    ) {
        let style = StrokeStyle(
            lineWidth: width,
            lineCap: .round,
            lineJoin: .round,
            dash: dash
        )
        for path in paths {
            context.stroke(path, with: .color(color), style: style)
        }
    }

    private static func drawBraid(
        over paths: [Path],
        geometry: BoardCordRigGeometry,
        scale: CGFloat,
        in context: inout GraphicsContext
    ) {
        guard scale.isFinite, scale > 0 else { return }

        let strokeStyle = StrokeStyle(
            lineWidth: 23 * scale,
            lineCap: .round,
            lineJoin: .round
        )
        var braidClip = Path()
        for path in paths {
            braidClip.addPath(path.strokedPath(strokeStyle))
        }

        var braidContext = context
        braidContext.clip(to: braidClip)
        braidContext.fill(
            Path(geometry.sceneRect),
            with: .color(Color(red: 23 / 255, green: 25 / 255, blue: 26 / 255))
        )

        let spacing = 12 * scale
        let diagonalSpan = geometry.sceneRect.width + geometry.sceneRect.height
        var offset = -diagonalSpan
        while offset <= diagonalSpan * 2 {
            var lightFiber = Path()
            lightFiber.move(
                to: CGPoint(
                    x: geometry.sceneRect.minX + offset,
                    y: geometry.sceneRect.maxY
                )
            )
            lightFiber.addLine(
                to: CGPoint(
                    x: geometry.sceneRect.minX + offset + geometry.sceneRect.height,
                    y: geometry.sceneRect.minY
                )
            )
            braidContext.stroke(
                lightFiber,
                with: .color(
                    Color(red: 93 / 255, green: 97 / 255, blue: 99 / 255)
                        .opacity(0.58)
                ),
                lineWidth: 2 * scale
            )

            var darkFiber = Path()
            darkFiber.move(
                to: CGPoint(
                    x: geometry.sceneRect.minX + offset,
                    y: geometry.sceneRect.minY
                )
            )
            darkFiber.addLine(
                to: CGPoint(
                    x: geometry.sceneRect.minX + offset + geometry.sceneRect.height,
                    y: geometry.sceneRect.maxY
                )
            )
            braidContext.stroke(
                darkFiber,
                with: .color(
                    Color(red: 3 / 255, green: 4 / 255, blue: 4 / 255)
                        .opacity(0.94)
                ),
                lineWidth: 2.3 * scale
            )

            var highlightFiber = Path()
            highlightFiber.move(
                to: CGPoint(
                    x: geometry.sceneRect.minX + offset + 3 * scale,
                    y: geometry.sceneRect.maxY
                )
            )
            highlightFiber.addLine(
                to: CGPoint(
                    x: geometry.sceneRect.minX + offset + geometry.sceneRect.height
                        + 3 * scale,
                    y: geometry.sceneRect.minY
                )
            )
            braidContext.stroke(
                highlightFiber,
                with: .color(
                    Color(red: 156 / 255, green: 160 / 255, blue: 162 / 255)
                        .opacity(0.32)
                ),
                lineWidth: 0.7 * scale
            )
            offset += spacing
        }
    }
}

/// The shared primitive used by package presentation views and editor previews.
/// Its caller owns image resolution and the geometry-to-canvas mapping.
struct BoardRiggedPresentationArtwork: View {
    let faceImage: UIImage
    let rig: BoardDirectTwoAnchorCordRig
    let geometry: BoardCordRigGeometry

    var body: some View {
        Canvas(opaque: false, rendersAsynchronously: false) { context, _ in
            BoardPresentationArtwork.drawRiggedArtwork(
                image: Image(uiImage: faceImage),
                rig: rig,
                geometry: geometry,
                in: &context
            )
        }
        .allowsHitTesting(false)
        .accessibilityHidden(true)
    }
}

struct BoardRoutedPresentationArtwork: View {
    let faceImage: UIImage
    let rig: BoardRoutedCordRig
    let geometry: BoardRoutedCordRigGeometry

    var body: some View {
        Canvas(opaque: false, rendersAsynchronously: false) { context, _ in
            BoardPresentationArtwork.drawRoutedArtwork(
                image: Image(uiImage: faceImage),
                rig: rig,
                geometry: geometry,
                in: &context
            )
        }
        .allowsHitTesting(false)
        .accessibilityHidden(true)
    }
}
