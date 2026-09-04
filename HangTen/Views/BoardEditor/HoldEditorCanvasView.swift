import SwiftUI
import UIKit

struct BoardEditorCanvasArtwork {
    let image: UIImage
    let presentationAspectRatio: CGFloat
    let directTwoAnchorRig: BoardDirectTwoAnchorCordRig?
    let routedCordRig: BoardRoutedCordRig?
    let projection: BoardPresentationGeometryProjection
    let sourcePresentationID: String?
    let availableHoldIDs: Set<String>?

    init(
        image: UIImage,
        presentationAspectRatio: CGFloat,
        directTwoAnchorRig: BoardDirectTwoAnchorCordRig?,
        routedCordRig: BoardRoutedCordRig? = nil,
        projection: BoardPresentationGeometryProjection,
        sourcePresentationID: String? = nil,
        availableHoldIDs: [String]? = nil
    ) {
        self.image = image
        self.presentationAspectRatio = presentationAspectRatio
        self.directTwoAnchorRig = directTwoAnchorRig
        self.routedCordRig = routedCordRig
        self.projection = projection
        self.sourcePresentationID = sourcePresentationID
        self.availableHoldIDs = availableHoldIDs.map(Set.init)
    }

    @MainActor
    static func make(
        package: BoardEditedPackage,
        sourceImage: UIImage
    ) -> BoardEditorCanvasArtwork {
        guard let presentation = package.document.presentations.first(where: \.isDefault)
                ?? package.document.presentations.first else {
            return fallback(package: package, sourceImage: sourceImage)
        }
        let projection = BoardPresentationGeometryProjection(
            rotationDegrees: CGFloat(presentation.resolvedRotationDegrees),
            rotationAnchor: presentation.geometryRotationAnchor
        )
        let sourcePresentationID = presentation.sourcePresentationID ?? presentation.id
        let resolvedCordRig = presentation.cordRig
            ?? package.document.presentations.first {
                $0.id == presentation.sourcePresentationID
            }?.cordRig
        guard let resolvedCordRig else {
            if presentation.rotationDegrees != nil {
                return BoardEditorCanvasArtwork(
                    image: sourceImage,
                    presentationAspectRatio: CGFloat(presentation.aspectRatio),
                    directTwoAnchorRig: nil,
                    projection: projection,
                    sourcePresentationID: sourcePresentationID,
                    availableHoldIDs: presentation.availableHoldIDs
                )
            }
            return fallback(package: package, sourceImage: sourceImage)
        }

        let canvasSize = resolvedCordRig.sceneSize.cgSize
        guard canvasSize.width.isFinite,
              canvasSize.height.isFinite,
              canvasSize.width > 0,
              canvasSize.height > 0 else {
            return fallback(package: package, sourceImage: sourceImage)
        }

        let canvas = CGRect(origin: .zero, size: canvasSize)
        switch resolvedCordRig {
        case .directTwoAnchor(let rig):
            let geometry = BoardCordRigGeometry.make(
                rig: rig,
                projection: projection,
                in: canvas
            )
            let renderer = ImageRenderer(
                content: BoardRiggedPresentationArtwork(
                    faceImage: sourceImage,
                    rig: rig,
                    geometry: geometry
                )
                .frame(width: canvasSize.width, height: canvasSize.height)
            )
            renderer.scale = 1
            renderer.isOpaque = false
            guard let renderedImage = renderer.uiImage else {
                return fallback(package: package, sourceImage: sourceImage)
            }

            return BoardEditorCanvasArtwork(
                image: renderedImage,
                presentationAspectRatio: CGFloat(presentation.aspectRatio),
                directTwoAnchorRig: rig,
                projection: projection,
                sourcePresentationID: sourcePresentationID,
                availableHoldIDs: presentation.availableHoldIDs
            )
        case .routed(let rig):
            guard let geometry = BoardRoutedCordRigGeometry.resolve(
                rig: rig,
                projection: projection,
                in: canvas
            ) else {
                return fallback(package: package, sourceImage: sourceImage)
            }
            let renderer = ImageRenderer(
                content: BoardRoutedPresentationArtwork(
                    faceImage: sourceImage,
                    rig: rig,
                    geometry: geometry
                )
                .frame(width: canvasSize.width, height: canvasSize.height)
            )
            renderer.scale = 1
            renderer.isOpaque = false
            guard let renderedImage = renderer.uiImage else {
                return fallback(package: package, sourceImage: sourceImage)
            }

            return BoardEditorCanvasArtwork(
                image: renderedImage,
                presentationAspectRatio: CGFloat(presentation.aspectRatio),
                directTwoAnchorRig: nil,
                routedCordRig: rig,
                projection: projection,
                sourcePresentationID: sourcePresentationID,
                availableHoldIDs: presentation.availableHoldIDs
            )
        }
    }

    private static func fallback(
        package: BoardEditedPackage,
        sourceImage: UIImage
    ) -> BoardEditorCanvasArtwork {
        BoardEditorCanvasArtwork(
            image: sourceImage,
            presentationAspectRatio: CGFloat(package.document.aspectRatio),
            directTwoAnchorRig: nil,
            projection: BoardPresentationGeometryProjection(isInverted: false)
        )
    }
}

struct HoldEditorCanvasView: UIViewRepresentable {
    @ObservedObject var session: BoardEditorSession
    let artwork: BoardEditorCanvasArtwork?
    let editorBackgroundColor: UIColor
    var reference: HoldEditorCanvasReference?

    func makeUIView(context: Context) -> HoldEditorCanvasUIView {
        let view = HoldEditorCanvasUIView()
        view.session = session
        view.boardArtwork = artwork
        view.editorBackgroundColor = editorBackgroundColor
        reference?.view = view
        return view
    }

    func updateUIView(_ uiView: HoldEditorCanvasUIView, context: Context) {
        uiView.session = session
        uiView.updateMetadataWarningAccessibility()
        uiView.boardArtwork = artwork
        uiView.editorBackgroundColor = editorBackgroundColor
        uiView.setNeedsDisplay()
    }
}

@MainActor
final class HoldEditorCanvasUIView: UIView {
    weak var session: BoardEditorSession? {
        didSet {
            updateMetadataWarningAccessibility()
            setNeedsDisplay()
        }
    }

    var boardArtwork: BoardEditorCanvasArtwork? {
        didSet { setNeedsDisplay() }
    }

    var editorBackgroundColor: UIColor = UIColor(Color.hangBackground) {
        didSet { backgroundColor = editorBackgroundColor }
    }

    private var zoom: CGFloat = 1
    private var viewportCenter = CGPoint.zero

    private enum DragState {
        case idle
        case viewport(startCenter: CGPoint)
        case translatePiece(startPath: [BoardPathCommand], startPoint: CGPoint)
        case bendSegment(index: Int, startPath: [BoardPathCommand])
        case anchor(index: Int, startPath: [BoardPathCommand])
        case control(index: Int, slot: Int, startPath: [BoardPathCommand])
        case resize(handle: ConstrainedHandle, startPath: [BoardPathCommand])
        case rotate(
            startPath: [BoardPathCommand],
            model: ConstrainedOutlineModel,
            startDegrees: Double,
            startPointerAngle: CGFloat
        )
    }

    private var dragState: DragState = .idle
    private var pinchStartZoom: CGFloat = 1

    override init(frame: CGRect) {
        super.init(frame: frame)
        backgroundColor = editorBackgroundColor
        isOpaque = true
        contentMode = .redraw
        setupGestures()
    }

    @available(*, unavailable)
    required init?(coder: NSCoder) {
        fatalError("HoldEditorCanvasUIView is created in code only")
    }

    var boardAspectRatio: CGFloat {
        if boardArtwork?.sourcePresentationID != nil,
           let presentationAspectRatio = boardArtwork?.presentationAspectRatio {
            return presentationAspectRatio
        }
        return session?.document.aspectRatio ?? 2
    }

    private var visibleHolds: [BoardEditableHold] {
        guard let session,
              let sourcePresentationID = boardArtwork?.sourcePresentationID else {
            return session?.document.holds ?? []
        }
        let availableHoldIDs = boardArtwork?.availableHoldIDs
        return session.document.holds.filter { hold in
            guard hold.presentationID == sourcePresentationID else { return false }
            return availableHoldIDs?.contains(hold.id) ?? true
        }
    }

    func updateMetadataWarningAccessibility() {
        let aggregate = UIAccessibilityElement(accessibilityContainer: self)
        aggregate.accessibilityTraits = .image
        aggregate.accessibilityLabel = session?.metadataWarningAccessibilityLabel ?? "Hangboard hold editor"
        aggregate.accessibilityValue = session?.metadataWarningAccessibilityValue
        aggregate.accessibilityFrameInContainerSpace = bounds

        var elements: [UIAccessibilityElement] = [aggregate]
        if let session {
            for hold in visibleHolds where !session.missingRequiredMetadata(for: hold).isEmpty {
                let warning = UIAccessibilityElement(accessibilityContainer: self)
                warning.accessibilityTraits = .image
                warning.accessibilityLabel = "Incomplete hold metadata: \(hold.id)"
                warning.accessibilityValue = "Missing: \(session.missingRequiredMetadata(for: hold).joined(separator: ", "))"
                warning.accessibilityFrameInContainerSpace = accessibilityFrame(for: hold)
                elements.append(warning)
            }
        }

        isAccessibilityElement = false
        accessibilityElements = elements
    }

    override func layoutSubviews() {
        super.layoutSubviews()
        updateMetadataWarningAccessibility()
    }

    private func accessibilityFrame(for hold: BoardEditableHold) -> CGRect {
        let boardFrame = hold.geometry.map(\.frame.cgRect).reduce(CGRect.null) { partial, frame in
            partial.union(frame)
        }
        guard !boardFrame.isNull else { return bounds }
        let first = screenPoint(
            fromBoard: CGPoint(x: boardFrame.minX, y: boardFrame.minY),
            bounds: bounds
        )
        let second = screenPoint(
            fromBoard: CGPoint(x: boardFrame.maxX, y: boardFrame.maxY),
            bounds: bounds
        )
        return CGRect(
            x: min(first.x, second.x),
            y: min(first.y, second.y),
            width: abs(second.x - first.x),
            height: abs(second.y - first.y)
        )
    }

    // MARK: - Transform

    private func fittedBoardRect(for bounds: CGRect) -> CGRect {
        let aspect = boardAspectRatio
        let width = bounds.width * 0.94
        let height = width / aspect
        let fittedHeight = bounds.height * 0.94
        let fittedWidth = fittedHeight * aspect
        let finalSize = fittedHeight < height ? CGSize(width: fittedWidth, height: fittedHeight) : CGSize(width: width, height: height)
        return CGRect(
            x: bounds.midX - finalSize.width / 2,
            y: bounds.midY - finalSize.height / 2,
            width: finalSize.width,
            height: finalSize.height
        )
    }

    private func baseScale(for bounds: CGRect) -> CGFloat {
        fittedBoardRect(for: bounds).width
    }

    private func scale(for bounds: CGRect) -> CGFloat {
        baseScale(for: bounds) * zoom
    }

    private func riggedSceneRect(for bounds: CGRect) -> CGRect {
        let fittedRect = fittedBoardRect(for: bounds)
        let scaledSize = CGSize(
            width: fittedRect.width * zoom,
            height: fittedRect.height * zoom
        )
        let center = CGPoint(
            x: fittedRect.midX + (0.5 - viewportCenter.x) * scaledSize.width,
            y: fittedRect.midY + (0.5 - viewportCenter.y) * scaledSize.height
        )
        return CGRect(
            x: center.x - scaledSize.width / 2,
            y: center.y - scaledSize.height / 2,
            width: scaledSize.width,
            height: scaledSize.height
        )
    }

    private func riggedFrames(
        for bounds: CGRect
    ) -> (sceneRect: CGRect, faceRect: CGRect)? {
        guard let artwork = boardArtwork else { return nil }
        let canvas = riggedSceneRect(for: bounds)
        if let rig = artwork.directTwoAnchorRig {
            let geometry = BoardCordRigGeometry.make(
                rig: rig,
                projection: artwork.projection,
                in: canvas
            )
            return (geometry.sceneRect, geometry.faceRect)
        }
        if let rig = artwork.routedCordRig,
           let geometry = BoardRoutedCordRigGeometry.resolve(
               rig: rig,
               projection: artwork.projection,
               in: canvas
           ) {
            return (geometry.sceneRect, geometry.faceRect)
        }
        return nil
    }

    /// Board-normalized point to screen point. Board space spans 0...1 across
    /// the presentation image on both axes; the fitted board rect encodes the
    /// aspect ratio, so one scale serves both axes.
    private func screenPoint(fromBoard point: CGPoint, bounds: CGRect) -> CGPoint {
        if let artwork = boardArtwork,
           let frames = riggedFrames(for: bounds),
           frames.faceRect.width > 0,
           frames.faceRect.height > 0 {
            let facePoint = CGPoint(
                x: frames.faceRect.minX + point.x * frames.faceRect.width,
                y: frames.faceRect.minY + point.y * frames.faceRect.height
            )
            return artwork.projection.project(facePoint, in: frames.sceneRect)
        }
        if let artwork = boardArtwork,
           artwork.sourcePresentationID != nil {
            let sceneRect = riggedSceneRect(for: bounds)
            let facePoint = CGPoint(
                x: sceneRect.minX + point.x * sceneRect.width,
                y: sceneRect.minY + point.y * sceneRect.height
            )
            return artwork.projection.project(facePoint, in: sceneRect)
        }
        let rect = fittedBoardRect(for: bounds)
        let s = scale(for: bounds)
        return CGPoint(
            x: rect.midX + (point.x - viewportCenter.x) * s,
            y: rect.midY + (point.y - viewportCenter.y) * s
        )
    }

    private func boardPoint(fromScreen point: CGPoint, bounds: CGRect) -> CGPoint {
        if let artwork = boardArtwork,
           let frames = riggedFrames(for: bounds),
           frames.faceRect.width > 0,
           frames.faceRect.height > 0 {
            let facePoint = point.applying(
                artwork.projection.affineTransform(in: frames.sceneRect).inverted()
            )
            return CGPoint(
                x: (facePoint.x - frames.faceRect.minX) / frames.faceRect.width,
                y: (facePoint.y - frames.faceRect.minY) / frames.faceRect.height
            )
        }
        if let artwork = boardArtwork,
           artwork.sourcePresentationID != nil {
            let sceneRect = riggedSceneRect(for: bounds)
            let facePoint = point.applying(
                artwork.projection.affineTransform(in: sceneRect).inverted()
            )
            return CGPoint(
                x: (facePoint.x - sceneRect.minX) / sceneRect.width,
                y: (facePoint.y - sceneRect.minY) / sceneRect.height
            )
        }
        let rect = fittedBoardRect(for: bounds)
        let s = scale(for: bounds)
        return CGPoint(
            x: viewportCenter.x + (point.x - rect.midX) / s,
            y: viewportCenter.y + (point.y - rect.midY) / s
        )
    }

    private func clampViewport() {
        viewportCenter.x = min(max(viewportCenter.x, -1), 2)
        viewportCenter.y = min(max(viewportCenter.y, -1), 2)
    }

    func zoomToFit() {
        zoom = 1
        viewportCenter = CGPoint(x: 0.5, y: 0.5)
        updateMetadataWarningAccessibility()
        setNeedsDisplay()
    }

    // MARK: - Gestures

    private func setupGestures() {
        viewportCenter = CGPoint(x: 0.5, y: 0.5)

        let pan = UIPanGestureRecognizer(target: self, action: #selector(handlePan(_:)))
        pan.maximumNumberOfTouches = 2
        pan.delegate = self
        addGestureRecognizer(pan)

        let pinch = UIPinchGestureRecognizer(target: self, action: #selector(handlePinch(_:)))
        pinch.delegate = self
        addGestureRecognizer(pinch)

        let tap = UITapGestureRecognizer(target: self, action: #selector(handleTap(_:)))
        addGestureRecognizer(tap)
    }

    @objc private func handlePinch(_ gesture: UIPinchGestureRecognizer) {
        switch gesture.state {
        case .began:
            beginViewportZoom()
        case .changed:
            updateViewportZoom(scale: gesture.scale)
        default:
            break
        }
    }

    @objc private func handleTap(_ gesture: UITapGestureRecognizer) {
        guard gesture.state == .ended, let session else { return }
        let location = gesture.location(in: self)
        if let piece = hitTestPiece(at: location) {
            session.select(holdID: piece.holdID, pieceIndex: piece.pieceIndex)
            session.select(handle: hitTestHandle(at: location))
        } else {
            session.select(holdID: nil)
        }
        setNeedsDisplay()
    }

    @objc private func handlePan(_ gesture: UIPanGestureRecognizer) {
        guard let session else { return }
        let location = gesture.location(in: self)
        let translation = gesture.translation(in: self)

        switch gesture.state {
        case .began:
            beginDrag(at: location, touches: gesture.numberOfTouches, session: session)
        case .changed:
            continueDrag(to: location, translation: translation, session: session)
        case .ended, .cancelled, .failed:
            endDrag(session: session)
        default:
            break
        }
    }

    func beginViewportPan() {
        dragState = .viewport(startCenter: viewportCenter)
    }

    func updateViewportPan(translation: CGPoint) {
        guard case .viewport(let startCenter) = dragState else { return }
        if boardArtwork?.sourcePresentationID != nil {
            let fittedRect = fittedBoardRect(for: bounds)
            viewportCenter = CGPoint(
                x: startCenter.x - translation.x / (fittedRect.width * zoom),
                y: startCenter.y - translation.y / (fittedRect.height * zoom)
            )
        } else {
            let s = scale(for: bounds)
            viewportCenter = CGPoint(
                x: startCenter.x - translation.x / s,
                y: startCenter.y - translation.y / s
            )
        }
        clampViewport()
        updateMetadataWarningAccessibility()
        setNeedsDisplay()
    }

    func beginViewportZoom() {
        pinchStartZoom = zoom
    }

    func updateViewportZoom(scale: CGFloat) {
        zoom = min(max(pinchStartZoom * scale, 0.6), 24)
        clampViewport()
        updateMetadataWarningAccessibility()
        setNeedsDisplay()
    }

    private func beginDrag(at location: CGPoint, touches: Int, session: BoardEditorSession) {
        if session.tool == .pan || touches >= 2 {
            beginViewportPan()
            return
        }
        if let handle = hitTestHandle(at: location), beginHandleDrag(handle, at: location) {
            return
        }
        if let selection = hitTestPiece(at: location) {
            if selection != session.selectedPiece {
                session.select(holdID: selection.holdID, pieceIndex: selection.pieceIndex)
            }
            if session.isRoundedRectPiece { return }
            guard let piece = session.selectedPieceDocument,
                  let startPath = try? session.boardCommands(for: piece) else { return }
            if let bendableIndex = hitTestBendableSegment(at: location, commands: startPath, session: session) {
                session.select(handle: .anchor(commandIndex: bendableIndex - 1 >= 0 ? bendableIndex - 1 : 0))
                session.beginInteractiveEdit()
                dragState = .bendSegment(index: bendableIndex, startPath: startPath)
                return
            }
            session.beginInteractiveEdit()
            dragState = .translatePiece(startPath: startPath, startPoint: boardPoint(fromScreen: location, bounds: bounds))
            return
        }
        beginViewportPan()
    }

    private func beginHandleDrag(_ handle: BoardEditorSession.HandleTarget, at location: CGPoint) -> Bool {
        guard let session,
              let piece = session.selectedPieceDocument,
              let startPath = try? session.boardCommands(for: piece) else {
            return false
        }
        session.beginInteractiveEdit()
        switch handle {
        case .anchor(let index):
            dragState = .anchor(index: index, startPath: startPath)
            return true
        case .control(let index, let slot):
            dragState = .control(index: index, slot: slot, startPath: startPath)
            return true
        case .constraintHandle(let constrainedHandle):
            guard piece.shapeConstraint != nil else { return false }
            dragState = .resize(handle: constrainedHandle, startPath: startPath)
            return true
        case .rotation:
            guard let constraint = piece.shapeConstraint,
                  let model = try? HoldPathEngine.constrainedOutlineModel(
                      commands: startPath,
                      constraint: constraint
                  ) else {
                return false
            }
            let center = screenPoint(fromBoard: model.center, bounds: bounds)
            let angle = atan2(location.y - center.y, location.x - center.x)
            dragState = .rotate(
                startPath: startPath,
                model: model,
                startDegrees: constraint.rotationDegrees,
                startPointerAngle: angle
            )
            return true
        }
    }

    private func continueDrag(to location: CGPoint, translation: CGPoint, session: BoardEditorSession) {
        switch dragState {
        case .idle:
            break
        case .viewport:
            updateViewportPan(translation: translation)
        case .translatePiece(let startPath, let startPoint):
            let current = boardPoint(fromScreen: location, bounds: bounds)
            let deltaX = current.x - startPoint.x
            let deltaY = current.y - startPoint.y
            var moved = startPath
            HoldPathEngine.translatePath(&moved, deltaX: deltaX, deltaY: deltaY)
            try? session.replaceSelectedBoardPath(moved, constraint: nil, recordsHistory: false)
            setNeedsDisplay()
        case .bendSegment(let index, let startPath):
            var moved = startPath
            let pointer = boardPoint(fromScreen: location, bounds: bounds)
            HoldPathEngine.bendSegmentToPoint(&moved, afterIndex: index, point: pointer)
            try? session.replaceSelectedBoardPath(moved, constraint: nil, recordsHistory: false)
            setNeedsDisplay()
        case .anchor(let index, let startPath):
            let current = boardPoint(fromScreen: location, bounds: bounds)
            var moved = startPath
            if let anchor = moved.indices.contains(index) ? moved[index].boardAnchor : nil {
                let deltaX = current.x - anchor.x
                let deltaY = current.y - anchor.y
                HoldPathEngine.moveVertex(&moved, index: index, deltaX: deltaX, deltaY: deltaY)
                try? session.replaceSelectedBoardPath(moved, constraint: nil, recordsHistory: false)
            }
            setNeedsDisplay()
        case .control(let index, let slot, let startPath):
            var moved = startPath
            if moved.controlPoint(commandIndex: index, slot: slot) != nil {
                let current = boardPoint(fromScreen: location, bounds: bounds)
                moved.setControlPoint(commandIndex: index, slot: slot, point: current)
                try? session.replaceSelectedBoardPath(moved, constraint: nil, recordsHistory: false)
            }
            setNeedsDisplay()
        case .resize(let handle, let startPath):
            let pointer = boardPoint(fromScreen: location, bounds: bounds)
            if let constraint = session.selectedPieceDocument?.shapeConstraint,
               let result = try? HoldPathEngine.resizeConstrainedOutline(
                   commands: startPath,
                   constraint: constraint,
                   handle: handle,
                   pointer: pointer,
                   minimumWidth: session.minimumResizeWidth,
                   minimumHeight: session.minimumResizeHeight
               ) {
                try? session.replaceSelectedBoardPath(
                    result.commands,
                    constraint: result.shapeConstraint,
                    recordsHistory: false
                )
            }
            setNeedsDisplay()
        case .rotate(let startPath, let model, let startDegrees, let startPointerAngle):
            let center = screenPoint(fromBoard: model.center, bounds: bounds)
            let angle = atan2(location.y - center.y, location.x - center.x)
            var deltaDegrees = Double((angle - startPointerAngle) * 180 / .pi)
            deltaDegrees = BoardEditorSession.normalizedConstraintDegrees(deltaDegrees)
            let newDegrees = BoardEditorSession.normalizedConstraintDegrees(startDegrees + deltaDegrees)
            var rotated = startPath
            HoldPathEngine.rotatePath(
                &rotated,
                angleRadians: CGFloat((newDegrees - startDegrees) * Double.pi / 180),
                pivot: model.center
            )
            try? session.replaceSelectedBoardPath(
                rotated,
                constraint: ShapeConstraint(shape: rotationShape ?? .oval, rotationDegrees: newDegrees),
                recordsHistory: false
            )
            setNeedsDisplay()
        }
    }

    private var rotationShape: ShapeConstraintShape? {
        session?.selectedPieceDocument?.shapeConstraint?.shape
    }

    private func endDrag(session: BoardEditorSession) {
        dragState = .idle
        session.commitLiveChange()
        setNeedsDisplay()
    }

    // MARK: - Hit testing

    private var handleHitRadius: CGFloat { 26 }

    private func hitTestHandle(at location: CGPoint) -> BoardEditorSession.HandleTarget? {
        guard let session,
              let piece = session.selectedPieceDocument,
              let startPath = try? session.boardCommands(for: piece) else {
            return nil
        }
        for (index, command) in startPath.enumerated() {
            if case .close = command { continue }
            if let anchor = command.boardAnchor,
               distance(location, screenPoint(fromBoard: anchor, bounds: bounds)) <= handleHitRadius {
                return .anchor(commandIndex: index)
            }
        }
        for (index, command) in startPath.enumerated() {
            switch command {
            case .quad(_, let control):
                if distance(location, screenPoint(fromBoard: control, bounds: bounds)) <= handleHitRadius {
                    return .control(commandIndex: index, slot: 0)
                }
            case .curve(_, let control1, let control2):
                if distance(location, screenPoint(fromBoard: control1, bounds: bounds)) <= handleHitRadius {
                    return .control(commandIndex: index, slot: 0)
                }
                if distance(location, screenPoint(fromBoard: control2, bounds: bounds)) <= handleHitRadius {
                    return .control(commandIndex: index, slot: 1)
                }
            default:
                break
            }
        }
        if let constraint = piece.shapeConstraint,
           let model = try? HoldPathEngine.constrainedOutlineModel(commands: startPath, constraint: constraint) {
            for (handle, boardPointValue) in model.handles.sorted(by: { $0.key.rawValue < $1.key.rawValue }) {
                if distance(location, screenPoint(fromBoard: boardPointValue, bounds: bounds)) <= handleHitRadius {
                    return .constraintHandle(handle)
                }
            }
            if let rotationPosition = rotationHandlePosition(model: model),
               distance(location, rotationPosition) <= handleHitRadius {
                return .rotation
            }
        }
        return nil
    }

    private func rotationHandlePosition(model: ConstrainedOutlineModel) -> CGPoint? {
        guard let topCenter = model.handles[.n] else { return nil }
        let screenTop = screenPoint(fromBoard: topCenter, bounds: bounds)
        let screenCenter = screenPoint(fromBoard: model.center, bounds: bounds)
        let direction = CGPoint(x: screenTop.x - screenCenter.x, y: screenTop.y - screenCenter.y)
        let length = max(hypot(direction.x, direction.y), 1)
        let offset: CGFloat = 44
        return CGPoint(
            x: screenTop.x + direction.x / length * offset,
            y: screenTop.y + direction.y / length * offset
        )
    }

    /// Returns the command index of a marked bendable cubic whose flattened
    /// curve passes near the touch, so body drags bend it through the pointer.
    private func hitTestBendableSegment(
        at location: CGPoint,
        commands: [BoardPathCommand],
        session: BoardEditorSession
    ) -> Int? {
        guard let piece = session.selectedPieceDocument,
              piece.shapeConstraint == nil else {
            return nil
        }
        let documents = piece.shape.commands ?? []
        var current = CGPoint.zero
        var best: (index: Int, distance: CGFloat)?
        for (index, command) in commands.enumerated() {
            guard index < documents.count else { break }
            switch command {
            case .move(let point):
                current = point
                continue
            case .close:
                continue
            case .line(let point):
                current = point
                continue
            case .quad, .curve:
                break
            }
            guard documents[index].bendable == true else {
                if let endpoint = command.boardAnchor { current = endpoint }
                continue
            }
            for sample in flattenedSamples(from: current, command: command) {
                let screenSample = screenPoint(fromBoard: sample, bounds: bounds)
                let distance = hypot(screenSample.x - location.x, screenSample.y - location.y)
                if distance <= handleHitRadius && (best == nil || distance < best!.distance) {
                    best = (index, distance)
                }
            }
            if let endpoint = command.boardAnchor { current = endpoint }
        }
        return best?.index
    }

    private func flattenedSamples(from start: CGPoint, command: BoardPathCommand) -> [CGPoint] {
        var samples: [CGPoint] = []
        for step in 1...16 {
            let t = CGFloat(step) / 16
            let inverse = 1 - t
            switch command {
            case .quad(let to, let control):
                samples.append(CGPoint(
                    x: inverse * inverse * start.x + 2 * inverse * t * control.x + t * t * to.x,
                    y: inverse * inverse * start.y + 2 * inverse * t * control.y + t * t * to.y
                ))
            case .curve(let to, let control1, let control2):
                samples.append(CGPoint(
                    x: inverse * inverse * inverse * start.x
                        + 3 * inverse * inverse * t * control1.x
                        + 3 * inverse * t * t * control2.x
                        + t * t * t * to.x,
                    y: inverse * inverse * inverse * start.y
                        + 3 * inverse * inverse * t * control1.y
                        + 3 * inverse * t * t * control2.y
                        + t * t * t * to.y
                ))
            default:
                break
            }
        }
        return samples
    }

    private func hitTestPiece(at location: CGPoint) -> BoardEditorSession.PieceSelection? {
        guard let session else { return nil }
        let boardLocation = boardPoint(fromScreen: location, bounds: bounds)
        var best: (selection: BoardEditorSession.PieceSelection, area: CGFloat)?
        for hold in visibleHolds {
            for (pieceIndex, piece) in hold.geometry.enumerated() {
                guard let commands = try? session.boardCommands(for: piece),
                  commands.containsBoard(point: boardLocation) else {
                    continue
                }
                let pieceBounds = HoldPathEngine.bounds(of: commands)
                let area = max(pieceBounds.width * pieceBounds.height, 0)
                if best == nil || area < best!.area {
                    best = (
                        BoardEditorSession.PieceSelection(holdID: hold.id, pieceIndex: pieceIndex),
                        area
                    )
                }
            }
        }
        return best?.selection
    }

    private func distance(_ a: CGPoint, _ b: CGPoint) -> CGFloat {
        hypot(a.x - b.x, a.y - b.y)
    }

    // MARK: - Drawing

    override func draw(_ rect: CGRect) {
        guard let context = UIGraphicsGetCurrentContext(), let session else { return }
        context.setLineJoin(.round)
        context.setLineCap(.round)

        if let boardArtwork {
            if boardArtwork.directTwoAnchorRig != nil || boardArtwork.routedCordRig != nil {
                boardArtwork.image.draw(in: riggedSceneRect(for: bounds))
            } else if boardArtwork.sourcePresentationID != nil {
                let sceneRect = riggedSceneRect(for: bounds)
                context.saveGState()
                context.concatenate(
                    boardArtwork.projection.affineTransform(in: sceneRect)
                )
                boardArtwork.image.draw(in: sceneRect)
                context.restoreGState()
            } else {
                let topLeft = screenPoint(fromBoard: .zero, bounds: bounds)
                let bottomRight = screenPoint(
                    fromBoard: CGPoint(x: 1, y: 1),
                    bounds: bounds
                )
                boardArtwork.image.draw(in: CGRect(
                    x: topLeft.x,
                    y: topLeft.y,
                    width: bottomRight.x - topLeft.x,
                    height: bottomRight.y - topLeft.y
                ))
            }
        }

        let selectedHoldID = session.selectedPiece?.holdID
        let selectedPieceIndex = session.selectedPiece?.pieceIndex
        let incompleteHoldIDs = Set(session.incompleteMetadataHoldIDs)

        for hold in visibleHolds {
            for (pieceIndex, piece) in hold.geometry.enumerated() {
                let isSelected = hold.id == selectedHoldID && pieceIndex == selectedPieceIndex
                let isMetadataIncomplete = incompleteHoldIDs.contains(hold.id)
                guard let commands = try? session.boardCommands(for: piece) else { continue }
                let path = bezierPath(commands: commands)
                if isMetadataIncomplete {
                    context.setStrokeColor(UIColor.systemOrange.cgColor)
                    context.setLineWidth(isSelected ? 5 : 3)
                    context.setLineDash(phase: 0, lengths: [6, 4])
                    context.addPath(path.cgPath)
                    context.strokePath()
                    context.setLineDash(phase: 0, lengths: [])
                }
                if isSelected {
                    context.setFillColor(UIColor(Color.holdOrange).withAlphaComponent(0.16).cgColor)
                    context.addPath(path.cgPath)
                    context.fillPath()
                    context.setStrokeColor(UIColor(Color.holdOrange).cgColor)
                    context.setLineWidth(2.5)
                } else {
                    context.setStrokeColor(UIColor(Color.holdBlue).withAlphaComponent(0.85).cgColor)
                    context.setLineWidth(1)
                }
                context.addPath(path.cgPath)
                context.strokePath()
            }
        }

        drawSelectionOverlay(context: context)
    }

    private func drawSelectionOverlay(context: CGContext) {
        guard let session,
              let piece = session.selectedPieceDocument,
              let commands = try? session.boardCommands(for: piece) else { return }

        for (index, command) in commands.enumerated() {
            if case .close = command { continue }
            switch command {
            case .quad(_, let control):
                drawControlLink(from: screenPoint(fromBoard: previousAnchor(commands, index), bounds: bounds), to: screenPoint(fromBoard: control, bounds: bounds))
                drawControlCircle(at: screenPoint(fromBoard: control, bounds: bounds))
            case .curve(_, let control1, let control2):
                drawControlLink(from: screenPoint(fromBoard: previousAnchor(commands, index), bounds: bounds), to: screenPoint(fromBoard: control1, bounds: bounds))
                drawControlLink(from: screenPoint(fromBoard: command.boardAnchor ?? .zero, bounds: bounds), to: screenPoint(fromBoard: control2, bounds: bounds))
                drawControlCircle(at: screenPoint(fromBoard: control1, bounds: bounds))
                drawControlCircle(at: screenPoint(fromBoard: control2, bounds: bounds))
            default:
                break
            }
        }

        for (index, command) in commands.enumerated() {
            guard let anchor = command.boardAnchor else { continue }
            drawAnchorSquare(at: screenPoint(fromBoard: anchor, bounds: bounds), highlighted: isSelectedHandle(.anchor(commandIndex: index)))
        }

        if let constraint = piece.shapeConstraint,
           let model = try? HoldPathEngine.constrainedOutlineModel(commands: commands, constraint: constraint) {
            drawConstraintBox(model: model)
        }
    }

    private func drawConstraintBox(model: ConstrainedOutlineModel) {
        guard let nw = model.handles[.nw],
              let n = model.handles[.n],
              let ne = model.handles[.ne],
              let e = model.handles[.e],
              let se = model.handles[.se],
              let s = model.handles[.s],
              let sw = model.handles[.sw],
              let w = model.handles[.w] else { return }
        let corners = [nw, ne, se, sw].map { screenPoint(fromBoard: $0, bounds: bounds) }
        let box = UIBezierPath()
        box.move(to: corners[0])
        box.addLine(to: corners[1])
        box.addLine(to: corners[2])
        box.addLine(to: corners[3])
        box.close()
        UIColor(Color.restBlue).withAlphaComponent(0.8).setStroke()
        box.lineWidth = 1.5
        box.stroke()

        let edgeHandles: [(CGPoint, ConstrainedHandle)] = [
            (n, .n), (e, .e), (s, .s), (w, .w)
        ]
        for (point, handle) in edgeHandles {
            drawRoundHandle(at: screenPoint(fromBoard: point, bounds: bounds), highlighted: isSelectedHandle(.constraintHandle(handle)))
        }
        for (point, handle) in zip(corners, ConstrainedHandle.allCases.filter(\.isCorner)) {
            drawRoundHandle(at: point, highlighted: isSelectedHandle(.constraintHandle(handle)))
        }

        if let top = model.handles[.n], let rotationPosition = rotationHandlePosition(model: model) {
            let stem = UIBezierPath()
            stem.move(to: screenPoint(fromBoard: top, bounds: bounds))
            stem.addLine(to: rotationPosition)
            UIColor(Color.restBlue).withAlphaComponent(0.8).setStroke()
            stem.lineWidth = 1.5
            stem.stroke()
            drawRotationHandle(at: rotationPosition, highlighted: isSelectedHandle(.rotation))
        }
    }

    private func drawAnchorSquare(at point: CGPoint, highlighted: Bool) {
        let side: CGFloat = highlighted ? 14 : 11
        let rect = CGRect(x: point.x - side / 2, y: point.y - side / 2, width: side, height: side)
        UIColor(Color.hangCream).setFill()
        UIBezierPath(roundedRect: rect, cornerRadius: 3).fill()
        UIColor(highlighted ? Color.holdActiveDeep : Color.hangInk).setStroke()
        let outline = UIBezierPath(roundedRect: rect, cornerRadius: 3)
        outline.lineWidth = 1.5
        outline.stroke()
    }

    private func drawControlCircle(at point: CGPoint) {
        let radius: CGFloat = 7
        UIColor(Color.holdBlue).setFill()
        UIBezierPath(ovalIn: CGRect(x: point.x - radius, y: point.y - radius, width: radius * 2, height: radius * 2)).fill()
        UIColor(Color.hangCream).setStroke()
        let ring = UIBezierPath(ovalIn: CGRect(x: point.x - radius, y: point.y - radius, width: radius * 2, height: radius * 2))
        ring.lineWidth = 1.5
        ring.stroke()
    }

    private func drawControlLink(from from_: CGPoint, to: CGPoint) {
        let link = UIBezierPath()
        link.move(to: from_)
        link.addLine(to: to)
        UIColor(Color.holdBlue).withAlphaComponent(0.55).setStroke()
        link.lineWidth = 1
        link.stroke()
    }

    private func drawRoundHandle(at point: CGPoint, highlighted: Bool) {
        let radius: CGFloat = highlighted ? 10 : 8
        UIColor(highlighted ? Color.restBlueDeep : Color.hangCream).setFill()
        UIBezierPath(ovalIn: CGRect(x: point.x - radius, y: point.y - radius, width: radius * 2, height: radius * 2)).fill()
        UIColor(Color.restBlueDeep).setStroke()
        let ring = UIBezierPath(ovalIn: CGRect(x: point.x - radius, y: point.y - radius, width: radius * 2, height: radius * 2))
        ring.lineWidth = 1.5
        ring.stroke()
    }

    private func drawRotationHandle(at point: CGPoint, highlighted: Bool) {
        let radius: CGFloat = highlighted ? 13 : 11
        UIColor(highlighted ? Color.restBlueDeep : Color.hangGreen).setFill()
        UIBezierPath(ovalIn: CGRect(x: point.x - radius, y: point.y - radius, width: radius * 2, height: radius * 2)).fill()
        UIColor(Color.hangCream).setStroke()
        let arrow = UIBezierPath()
        arrow.move(to: CGPoint(x: point.x - radius / 2, y: point.y))
        arrow.addLine(to: CGPoint(x: point.x + radius / 2, y: point.y))
        arrow.move(to: CGPoint(x: point.x + radius / 4, y: point.y - radius / 4))
        arrow.addLine(to: CGPoint(x: point.x + radius / 2, y: point.y))
        arrow.addLine(to: CGPoint(x: point.x + radius / 4, y: point.y + radius / 4))
        UIColor(Color.hangCream).setStroke()
        arrow.lineWidth = 1.5
        arrow.stroke()
    }

    private func previousAnchor(_ commands: [BoardPathCommand], _ index: Int) -> CGPoint {
        var cursor = index
        while cursor > 0 {
            cursor -= 1
            if let anchor = commands[cursor].boardAnchor { return anchor }
        }
        return commands.compactMap(\.boardAnchor).first ?? .zero
    }

    private func isSelectedHandle(_ target: BoardEditorSession.HandleTarget) -> Bool {
        session?.selectedHandle == target
    }

    private func bezierPath(commands: [BoardPathCommand]) -> UIBezierPath {
        let path = UIBezierPath()
        for command in commands {
            switch command {
            case .move(let point):
                path.move(to: screenPoint(fromBoard: point, bounds: bounds))
            case .line(let point):
                path.addLine(to: screenPoint(fromBoard: point, bounds: bounds))
            case .quad(let to, let control):
                path.addQuadCurve(
                    to: screenPoint(fromBoard: to, bounds: bounds),
                    controlPoint: screenPoint(fromBoard: control, bounds: bounds)
                )
            case .curve(let to, let control1, let control2):
                path.addCurve(
                    to: screenPoint(fromBoard: to, bounds: bounds),
                    controlPoint1: screenPoint(fromBoard: control1, bounds: bounds),
                    controlPoint2: screenPoint(fromBoard: control2, bounds: bounds)
                )
            case .close:
                path.close()
            }
        }
        return path
    }
}

extension HoldEditorCanvasUIView: UIGestureRecognizerDelegate {
    func gestureRecognizer(
        _ gestureRecognizer: UIGestureRecognizer,
        shouldRecognizeSimultaneouslyWith otherGestureRecognizer: UIGestureRecognizer
    ) -> Bool {
        true
    }
}

extension Array where Element == BoardPathCommand {
    func containsBoard(point: CGPoint) -> Bool {
        let flattened = flattenedContourPoints()
        guard flattened.count > 2 else { return false }
        var inside = false
        var previous = flattened.last!
        for current in flattened {
            if (current.y > point.y) != (previous.y > point.y) {
                let denominator = previous.y - current.y
                if abs(denominator) > 1e-12 {
                    let intersectionX = (previous.x - current.x) * (point.y - current.y) / denominator + current.x
                    if point.x < intersectionX {
                        inside.toggle()
                    }
                }
            }
            previous = current
        }
        return inside
    }

    private func flattenedContourPoints() -> [CGPoint] {
        var points: [CGPoint] = []
        var current = CGPoint.zero
        var start = CGPoint.zero
        for command in self {
            switch command {
            case .move(let point):
                current = point
                start = point
                points.append(point)
            case .line(let point):
                current = point
                points.append(point)
            case .quad(let to, let control):
                for step in 1...16 {
                    let t = CGFloat(step) / 16
                    let inverse = 1 - t
                    points.append(CGPoint(
                        x: inverse * inverse * current.x + 2 * inverse * t * control.x + t * t * to.x,
                        y: inverse * inverse * current.y + 2 * inverse * t * control.y + t * t * to.y
                    ))
                }
                current = to
            case .curve(let to, let control1, let control2):
                for step in 1...16 {
                    let t = CGFloat(step) / 16
                    let inverse = 1 - t
                    points.append(CGPoint(
                        x: inverse * inverse * inverse * current.x
                            + 3 * inverse * inverse * t * control1.x
                            + 3 * inverse * t * t * control2.x
                            + t * t * t * to.x,
                        y: inverse * inverse * inverse * current.y
                            + 3 * inverse * inverse * t * control1.y
                            + 3 * inverse * t * t * control2.y
                            + t * t * t * to.y
                    ))
                }
                current = to
            case .close:
                current = start
                points.append(start)
            }
        }
        return points
    }
}

private extension ConstrainedHandle {
    var isCorner: Bool {
        switch self {
        case .nw, .ne, .se, .sw: true
        default: false
        }
    }
}
