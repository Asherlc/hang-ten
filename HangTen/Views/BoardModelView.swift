import RealityKit
import SwiftUI
import UIKit

struct BoardModelSurface: View {
    enum ResultState {
        case loading
        case ready(BoardModelRealityScene)
        case unavailable

        var loadingMessage: String? {
            guard case .loading = self else { return nil }
            return "Downloading 3D model…"
        }
    }

    let board: BoardRevision
    let presentation: BoardPresentation
    let positionID: String?
    let highlightedContactIDs: Set<String>
    let highlightMode: BoardHighlightMode
    let onContactTap: ((PhysicalContact) -> Void)?
    var isDisplayOnly = false
    @State private var result: ResultState = .loading

    init(
        board: BoardRevision,
        presentation: BoardPresentation,
        positionID: String? = nil,
        highlightedContactIDs: Set<String>,
        highlightMode: BoardHighlightMode,
        onContactTap: ((PhysicalContact) -> Void)?,
        isDisplayOnly: Bool = false
    ) {
        self.board = board
        self.presentation = presentation
        self.positionID = positionID
        self.highlightedContactIDs = highlightedContactIDs
        self.highlightMode = highlightMode
        self.onContactTap = onContactTap
        self.isDisplayOnly = isDisplayOnly
    }

    var body: some View {
        // Keep loading and disappearance scoped to this surface. Group forwards
        // lifecycle modifiers to its changing placeholder/model children.
        ZStack {
            if case .ready(let model) = result {
                let realityView = BoardModelRealityView(
                    model: model,
                    boardName: board.name,
                    accessibilityValue: highlightedContactCue,
                    contacts: board.contacts(in: presentation),
                    positionID: positionID,
                    highlightedContactIDs: highlightedContactIDs,
                    highlightMode: highlightMode,
                    onContactTap: onContactTap,
                    onUnavailable: { result = .unavailable },
                    isDisplayOnly: isDisplayOnly
                )
                // Display-only picker cards wrap this in a Button; claiming
                // SwiftUI hits here would intercept the card select tap even
                // when the hosted RealityView has user interaction disabled.
                .allowsHitTesting(!isDisplayOnly)
                if onContactTap == nil {
                    realityView.accessibilityIdentifier("boardModel.3d")
                } else {
                    // A parent accessibility identifier propagates to the
                    // RealityView's projected contact buttons. Keep their
                    // per-contact identifiers available to UI automation and
                    // assistive technology on interactive board maps.
                    realityView
                }
            } else if let loadingMessage = result.loadingMessage {
                HStack(spacing: 12) {
                    ProgressView()
                    Text(loadingMessage)
                        .font(.subheadline)
                }
                .padding(.horizontal, 20)
                .padding(.vertical, 16)
                .background(.regularMaterial, in: RoundedRectangle(cornerRadius: 16))
                .shadow(color: .black.opacity(0.12), radius: 12, y: 4)
                .frame(maxWidth: .infinity, maxHeight: .infinity)
                .accessibilityElement(children: .ignore)
                .accessibilityIdentifier("boardModel.loading")
                .accessibilityLabel(loadingMessage)
                    .allowsHitTesting(false)
            } else {
                BoardModelUnavailableView()
            }
        }
        .task(id: loadIdentity) {
            guard !Task.isCancelled else { return }
            guard case .model = presentation.media else {
                result = .unavailable
                return
            }
            result = .loading
            #if DEBUG
            if ProcessInfo.processInfo.environment["HANGTEN_REVIEW_MODEL_DIAGNOSTICS"] == "1" {
                print("[BoardModelSurface] load begin \(board.id) displayOnly=\(isDisplayOnly)")
            }
            #endif
            do {
                let model = try await BoardModelRealityLoader.load(
                    board: board,
                    presentation: presentation,
                    store: BoardCatalog.packageStore
                )
                guard !Task.isCancelled else { return }
                #if DEBUG
                if ProcessInfo.processInfo.environment["HANGTEN_REVIEW_MODEL_DIAGNOSTICS"] == "1" {
                    print("[BoardModelSurface] load ready \(board.id) scene=\(ObjectIdentifier(model)) displayOnly=\(isDisplayOnly)")
                }
                #endif
                result = .ready(model)
            } catch {
                guard !Task.isCancelled else { return }
                #if DEBUG
                print("[BoardModelSurface] RealityKit model load failed: \(error)")
                #endif
                result = .unavailable
            }
        }
        .onDisappear {
            #if DEBUG
            if ProcessInfo.processInfo.environment["HANGTEN_REVIEW_MODEL_DIAGNOSTICS"] == "1" {
                print("[BoardModelSurface] disappear \(board.id) displayOnly=\(isDisplayOnly)")
            }
            #endif
            result = .loading
        }
    }

    private var loadIdentity: BoardModelRealityKey? {
        guard case .model(let media) = presentation.media else { return nil }
        return BoardModelRealityKey(
            boardID: board.id,
            presentationID: presentation.id,
            modelSHA256: media.descriptor.modelSHA256
        )
    }

    private var highlightedContactCue: String? {
        let boardContacts = board.contacts(in: presentation)
        let highlighted = boardContacts.filter { highlightedContactIDs.contains($0.id) }
        guard highlighted.count == 1, let contact = highlighted.first else { return nil }
        return GripDiagramView.cueLabel(for: contact)
    }
}

struct BoardModelUnavailableView: View {
    var body: some View {
        ContentUnavailableView(
            "3D model unavailable",
            systemImage: "cube.transparent",
            description: Text("This board model could not be loaded.")
        )
        .accessibilityIdentifier("boardModel.unavailable")
        .accessibilityElement(children: .ignore)
        .allowsHitTesting(false)
    }
}

struct BoardModelRealityView: View {
    let model: BoardModelRealityScene
    let boardName: String
    let accessibilityValue: String?
    let contacts: [PhysicalContact]
    let positionID: String?
    let highlightedContactIDs: Set<String>
    let highlightMode: BoardHighlightMode
    let onContactTap: ((PhysicalContact) -> Void)?
    let onUnavailable: (() -> Void)?
    var isDisplayOnly = false

    @State private var cameraRevision = 0
    @State private var lastDragTranslation: CGSize = .zero
    @State private var lastMagnification: CGFloat = 1
    @State private var didReportUnavailable = false
    #if DEBUG
    @State private var synchronizedCameraDiagnostic = "pending"
    #endif

    private var fieldOfViewDegrees: Double {
        #if DEBUG
        if ProcessInfo.processInfo.environment["HANGTEN_REVIEW_BOARD_TELEPHOTO"] == "1" {
            return 6
        }
        #endif
        return 30
    }

    var body: some View {
        let _ = cameraRevision
        GeometryReader { proxy in
            let size = proxy.size
            Group {
                if !isDisplayOnly, onContactTap != nil {
                    BoardModelARHost(
                        model: model,
                        synchronize: { viewport in
                            applySync(size: viewport)
                            updateRendererDiagnostic(revision: cameraRevision)
                        },
                        onEntityTap: { entity in
                            guard let id = model.contactID(for: entity),
                                  let contact = contacts.first(where: { $0.id == id }) else { return }
                            model.resetCamera(animated: true)
                            cameraRevision &+= 1
                            onContactTap?(contact)
                        },
                        onCameraChange: {
                            cameraRevision &+= 1
                        }
                    )
                } else {
                    RealityView { content in
                        // Board maps use the authored camera, without device tracking
                        // or the AR session's implicit non-AR fallback.
                        content.camera = .virtual
                        content.add(model.root)
                        content.add(model.camera)
                        applySync(size: size)
                        #if DEBUG
                        if ProcessInfo.processInfo.environment["HANGTEN_REVIEW_MODEL_DIAGNOSTICS"] == "1" {
                            print("[BoardModelRealityView] attach scene=\(ObjectIdentifier(model)) camera=\(content.camera) size=\(size) transform=\(model.camera.transform.matrix) rootScene=\(String(describing: model.root.scene))")
                        }
                        #endif
                    } update: { content in
                        // Observe orbit invalidation in the RealityView update itself,
                        // as well as the projected SwiftUI accessibility overlay.
                        let revision = cameraRevision
                        content.camera = .virtual
                        applySync(size: size)
                        updateRendererDiagnostic(revision: revision)
                    }
                    .gesture(orbitGesture(size: size))
                    .simultaneousGesture(magnifyGesture)
                    .gesture(tapGesture)
                }
            }
            .overlay { accessibilityOverlay(size: size) }
            #if DEBUG
            .overlay(alignment: .topLeading) {
                if ProcessInfo.processInfo.environment["HANGTEN_REVIEW_BOARD_DIAGNOSTICS"] == "1" {
                    Color.clear
                        .frame(width: 1, height: 1)
                        .accessibilityElement()
                        .accessibilityIdentifier("boardModel.renderDiagnostic")
                        .accessibilityLabel("Board renderer diagnostic")
                        .accessibilityValue(synchronizedCameraDiagnostic)
                        .allowsHitTesting(false)
                }
            }
            #endif
            .allowsHitTesting(!isDisplayOnly)
            // A different scene gets a fresh renderer host and independent
            // root/camera attachment.
            .id(ObjectIdentifier(model))
        }
        // A display-only card is one element (its host Button owns the tap). An
        // interactive board exposes its contact elements instead, so the
        // container must not collapse them into a single element.
        .modifier(BoardModelAccessibilityContainer(
            label: onContactTap == nil ? "\(boardName) hangboard" : nil,
            value: onContactTap == nil ? accessibilityValue : nil))
    }

    /// Publishes scene membership and submitted camera revision for opt-in DEBUG review diagnostics.
    private func updateRendererDiagnostic(revision: Int) {
        #if DEBUG
        if ProcessInfo.processInfo.environment["HANGTEN_REVIEW_BOARD_DIAGNOSTICS"] == "1" {
            let diagnostic = "revision=\(revision);rootActive=\(model.root.isActive);cameraActive=\(model.camera.isActive);sameScene=\(model.root.scene != nil && model.root.scene === model.camera.scene)"
            Task { @MainActor in
                if synchronizedCameraDiagnostic != diagnostic {
                    synchronizedCameraDiagnostic = diagnostic
                }
            }
        }
        #endif
    }

    private func applySync(size: CGSize) {
        let priorCameraTransform = model.camera.transform.matrix
        let priorInstanceTransforms = model.instanceEntities.map { $0.transform.matrix }
        var camera = model.camera.camera
        camera.fieldOfViewInDegrees = Float(fieldOfViewDegrees)
        camera.fieldOfViewOrientation = .vertical
        camera.near = 0.001
        camera.far = 1000
        model.camera.camera = camera
        model.frame(in: size)
        let didSelect = model.select(positionID: positionID)
        model.highlight(highlightedContactIDs, mode: highlightMode)
        // RealityView synchronizes after SwiftUI evaluates the accessibility
        // overlay. Reproject once when framing or a board pose actually changes.
        // The unchanged follow-up update must not schedule another invalidation.
        if model.camera.transform.matrix != priorCameraTransform
            || model.instanceEntities.map({ $0.transform.matrix }) != priorInstanceTransforms {
            Task { @MainActor in
                cameraRevision &+= 1
            }
        }
        if let positionID, !didSelect {
            Task { @MainActor in
                guard !didReportUnavailable else { return }
                didReportUnavailable = true
                onUnavailable?()
            }
        } else if didSelect {
            Task { @MainActor in didReportUnavailable = false }
        }
    }

    private var tapGesture: some Gesture {
        SpatialTapGesture()
            .targetedToAnyEntity()
            .onEnded { value in
                guard let id = model.contactID(for: value.entity),
                      let contact = contacts.first(where: { $0.id == id }) else { return }
                model.resetCamera(animated: true)
                cameraRevision &+= 1
                onContactTap?(contact)
            }
    }

    private func orbitGesture(size: CGSize) -> some Gesture {
        DragGesture(minimumDistance: 4)
            .onChanged { value in
                let deltaX = value.translation.width - lastDragTranslation.width
                let deltaY = value.translation.height - lastDragTranslation.height
                lastDragTranslation = value.translation
                model.orbit(azimuth: model.orbitAzimuth - Float(deltaX / max(size.width, 1)) * 0.9,
                            elevation: model.orbitElevation - Float(deltaY / max(size.height, 1)) * 0.65)
                cameraRevision &+= 1
            }
            .onEnded { _ in lastDragTranslation = .zero }
    }

    private var magnifyGesture: some Gesture {
        MagnificationGesture()
            .onChanged { value in
                let ratio = value / max(lastMagnification, 0.001)
                lastMagnification = value
                model.orbit(azimuth: model.orbitAzimuth, elevation: model.orbitElevation,
                            zoomScale: model.orbitZoom / Float(ratio))
                cameraRevision &+= 1
            }
            .onEnded { _ in lastMagnification = 1 }
    }

    @ViewBuilder
    private func accessibilityOverlay(size: CGSize) -> some View {
        if let onContactTap {
            ZStack {
                ForEach(contacts) { contact in
                    if let point = model.projectedContactCenter(contact.id, viewport: size,
                                                               fieldOfViewDegrees: fieldOfViewDegrees) {
                        Color.clear
                            .frame(width: 44, height: 44)
                            .contentShape(Rectangle())
                            .position(point)
                            .accessibilityElement()
                            .accessibilityIdentifier("boardModel.contact.\(contact.id)")
                            .accessibilityLabel(contact.name)
                            .accessibilityAddTraits(
                                highlightedContactIDs.contains(contact.id)
                                    ? [.isButton, .isSelected] : [.isButton])
                            .accessibilityAction { onContactTap(contact) }
                    }
                }
            }
            // Accessibility only: real taps must reach the RealityKit picking
            // gesture so the nearest visible contact wins, not the overlay.
            .allowsHitTesting(false)
        }
    }
}

// Controlled host comparison: interactive maps retain the same scene and camera
// but use a stable UIKit non-AR renderer. Display-only previews keep RealityView.
private struct BoardModelARHost: UIViewRepresentable {
    let model: BoardModelRealityScene
    let synchronize: (CGSize) -> Void
    let onEntityTap: (Entity) -> Void
    let onCameraChange: () -> Void

    /// Creates the coordinator that owns this host’s anchor and gesture state.
    func makeCoordinator() -> Coordinator { Coordinator(parent: self) }

    /// Creates the non-AR renderer container and attaches this independently loaded scene.
    func makeUIView(context: Context) -> BoardModelARContainer {
        let view = BoardModelARContainer(frame: .zero)
        context.coordinator.attach(to: view)
        return view
    }

    /// Refreshes callbacks and synchronizes framing against the renderer’s current bounds.
    func updateUIView(_ view: BoardModelARContainer, context: Context) {
        context.coordinator.parent = self
        context.coordinator.synchronize(view)
    }

    /// Detaches this host’s scene and recognizers when SwiftUI removes its container.
    static func dismantleUIView(_ view: BoardModelARContainer, coordinator: Coordinator) {
        coordinator.detach(from: view)
    }

    @MainActor
    final class Coordinator: NSObject {
        var parent: BoardModelARHost
        let anchor = AnchorEntity(world: .zero)
        let panDelegate = OrbitPanGestureDelegate(allowsAllDirections: true)
        private var lastTranslation: CGPoint = .zero
        private var lastScale: CGFloat = 1

        /// Retains the current host configuration for scene attachment and input callbacks.
        init(parent: BoardModelARHost) { self.parent = parent }

        /// Attaches the scene beneath an identity anchor and installs native tap, orbit and pinch input.
        func attach(to view: BoardModelARContainer) {
            anchor.addChild(parent.model.root)
            anchor.addChild(parent.model.camera)
            view.renderer.scene.addAnchor(anchor)
            view.onLayout = { [weak self] view in self?.synchronize(view) }
            let pan = OrbitPanGestureRecognizer(target: self, action: #selector(orbit(_:)))
            pan.activationDistance = 4
            pan.delegate = panDelegate
            view.renderer.addGestureRecognizer(pan)
            let tap = UITapGestureRecognizer(target: self, action: #selector(tap(_:)))
            tap.require(toFail: pan)
            view.renderer.addGestureRecognizer(tap)
            let pinch = UIPinchGestureRecognizer(target: self, action: #selector(magnify(_:)))
            panDelegate.simultaneousPan = pan
            panDelegate.simultaneousPinch = pinch
            pinch.delegate = panDelegate
            view.renderer.addGestureRecognizer(pinch)
        }

        /// Applies framing and selection only when UIKit reports a finite, positive viewport.
        func synchronize(_ view: BoardModelARContainer) {
            let size = view.renderer.bounds.size
            guard size.width.isFinite, size.height.isFinite,
                  size.width > 0, size.height > 0 else { return }
            parent.synchronize(size)
        }

        /// Releases layout callbacks, input recognizers and the entities attached by this host.
        func detach(from view: BoardModelARContainer) {
            view.onLayout = nil
            for gesture in view.renderer.gestureRecognizers ?? [] {
                view.renderer.removeGestureRecognizer(gesture)
            }
            view.renderer.scene.removeAnchor(anchor)
            parent.model.root.removeFromParent()
            parent.model.camera.removeFromParent()
        }

        /// Resolves a completed native collision hit before forwarding physical contact selection.
        @objc private func tap(_ gesture: UITapGestureRecognizer) {
            guard gesture.state == .ended, let view = gesture.view as? ARView else { return }
            let entity = view.entity(at: gesture.location(in: view))
            guard let entity else { return }
            parent.onEntityTap(entity)
        }

        /// Applies incremental pan deltas using the existing viewport-normalized camera orbit math.
        @objc private func orbit(_ gesture: UIPanGestureRecognizer) {
            guard let view = gesture.view else { return }
            switch gesture.state {
            case .began, .changed:
                let translation = gesture.translation(in: view)
                let deltaX = translation.x - lastTranslation.x
                let deltaY = translation.y - lastTranslation.y
                lastTranslation = translation
                parent.model.orbit(
                    azimuth: parent.model.orbitAzimuth - Float(deltaX / max(view.bounds.width, 1)) * 0.9,
                    elevation: parent.model.orbitElevation - Float(deltaY / max(view.bounds.height, 1)) * 0.65)
                parent.onCameraChange()
            case .ended, .cancelled, .failed:
                lastTranslation = .zero
            default: break
            }
        }

        /// Applies incremental pinch ratios to zoom and resets gesture bookkeeping at termination.
        @objc private func magnify(_ gesture: UIPinchGestureRecognizer) {
            switch gesture.state {
            case .began, .changed:
                let ratio = gesture.scale / max(lastScale, 0.001)
                lastScale = gesture.scale
                parent.model.orbit(azimuth: parent.model.orbitAzimuth,
                                   elevation: parent.model.orbitElevation,
                                   zoomScale: parent.model.orbitZoom / Float(ratio))
                parent.onCameraChange()
            case .ended, .cancelled, .failed:
                lastScale = 1
            default: break
            }
        }
    }
}

private final class BoardModelARContainer: UIView {
    let renderer = ARView(frame: .zero, cameraMode: .nonAR, automaticallyConfigureSession: false)
    var onLayout: ((BoardModelARContainer) -> Void)?

    /// Builds an opaque non-AR surface using the surrounding card's background.
    override init(frame: CGRect) {
        super.init(frame: frame)
        let surfaceColor = UIColor(Color.hangCream)
        backgroundColor = surfaceColor
        isOpaque = true
        renderer.environment.background = .color(surfaceColor)
        renderer.backgroundColor = surfaceColor
        renderer.isOpaque = true
        addSubview(renderer)
    }

    /// Rejects storyboard decoding because this container is created programmatically.
    @available(*, unavailable)
    required init?(coder: NSCoder) { fatalError("init(coder:) is unavailable") }

    /// Sizes the renderer to actual container bounds before synchronizing camera framing.
    override func layoutSubviews() {
        super.layoutSubviews()
        renderer.frame = bounds
        onLayout?(self)
    }
}

private struct BoardModelAccessibilityContainer: ViewModifier {
    let label: String?
    let value: String?

    func body(content: Content) -> some View {
        if let label {
            content
                .accessibilityElement(children: .ignore)
                .accessibilityLabel(label)
                .accessibilityValue(value ?? "")
        } else {
            content
        }
    }
}
