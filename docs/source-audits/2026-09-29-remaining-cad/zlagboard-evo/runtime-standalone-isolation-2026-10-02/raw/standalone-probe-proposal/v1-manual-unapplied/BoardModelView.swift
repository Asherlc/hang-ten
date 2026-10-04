import RealityKit
import SwiftUI

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
        Group {
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
                #if DEBUG
                let diagnosticHost = Group {
                    if ProcessInfo.processInfo.environment["HANGTEN_REVIEW_SEMANTIC_BOARD_HOST"] == "1" {
                        realityView.id(BoardDiagnosticHostIdentity(
                            scene: ObjectIdentifier(model), contactIDs: highlightedContactIDs,
                            mode: highlightMode, positionID: positionID))
                    } else {
                        realityView
                    }
                }
                #else
                let diagnosticHost = realityView
                #endif
                if onContactTap == nil {
                    diagnosticHost.accessibilityIdentifier("boardModel.3d")
                } else {
                    // A parent accessibility identifier propagates to the
                    // RealityView's projected contact buttons. Keep their
                    // per-contact identifiers available to UI automation and
                    // assistive technology on interactive board maps.
                    diagnosticHost
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
            do {
                let model = try await BoardModelRealityLoader.load(
                    board: board,
                    presentation: presentation,
                    store: BoardCatalog.packageStore
                )
                guard !Task.isCancelled else { return }
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
    @State private var diagnosticViewToken = UUID()
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
            #if DEBUG
            if onContactTap == nil,
               ProcessInfo.processInfo.environment["HANGTEN_REVIEW_BOARD_ARVIEW_HOST"] == "1" {
                BoardNonARHostProbe(model: model, viewToken: diagnosticViewToken,
                                    selectedIDs: highlightedContactIDs, mode: highlightMode,
                                    synchronize: { applySync(size: size) })
                    .id(ObjectIdentifier(model))
                    .allowsHitTesting(false)
            } else {
                realityHost(size: size)
            }
            #else
            realityHost(size: size)
            #endif
        }
        // A display-only card is one element (its host Button owns the tap). An
        // interactive board exposes its contact elements instead, so the
        // container must not collapse them into a single element.
        .modifier(BoardModelAccessibilityContainer(
            label: onContactTap == nil ? "\(boardName) hangboard" : nil,
            value: onContactTap == nil ? accessibilityValue : nil))
    }

    private func realityHost(size: CGSize) -> some View {
            RealityView { content in
                #if DEBUG
                if ProcessInfo.processInfo.environment["HANGTEN_REVIEW_BOARD_VIRTUAL_CAMERA"] == "1" {
                    content.camera = .virtual
                }
                #endif
                content.add(model.root)
                content.add(model.camera)
                applySync(size: size)
                #if DEBUG
                if BoardHighlightDiagnostic.isEnabled {
                    BoardHighlightDiagnostic.shared.capture("view-make", scene: model,
                        view: diagnosticViewToken, roots: Array(content.entities), viewport: size)
                    BoardHighlightDiagnostic.shared.startSamples(view: diagnosticViewToken, scene: model)
                }
                #endif
            } update: { content in
                #if DEBUG
                if ProcessInfo.processInfo.environment["HANGTEN_REVIEW_BOARD_VIRTUAL_CAMERA"] == "1" {
                    content.camera = .virtual
                }
                #endif
                applySync(size: size)
                #if DEBUG
                if BoardHighlightDiagnostic.isEnabled {
                    BoardHighlightDiagnostic.shared.capture("view-update", scene: model,
                        view: diagnosticViewToken, roots: Array(content.entities), viewport: size)
                }
                #endif
            }
            .gesture(orbitGesture(size: size))
            .simultaneousGesture(magnifyGesture)
            .gesture(tapGesture)
            .overlay { accessibilityOverlay(size: size) }
            .allowsHitTesting(!isDisplayOnly)
            // A different scene needs a fresh RealityView make closure so its
            // root and camera replace the prior scene's entities.
            .id(ObjectIdentifier(model))
            .onDisappear {
                #if DEBUG
                if BoardHighlightDiagnostic.isEnabled {
                    BoardHighlightDiagnostic.shared.disappear(view: diagnosticViewToken, scene: model)
                }
                #endif
            }
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
            Task { @MainActor in cameraRevision &+= 1 }
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

#if DEBUG
/// Temporary host comparison; interactive boards retain the RealityView branch.
@MainActor
private struct BoardNonARHostProbe: UIViewRepresentable {
    let model: BoardModelRealityScene
    let viewToken: UUID
    let selectedIDs: Set<String>
    let mode: BoardHighlightMode
    let synchronize: () -> Void

    func makeCoordinator() -> Coordinator { Coordinator(model: model, viewToken: viewToken) }

    func makeUIView(context: Context) -> ARView {
        let view = ARView(frame: .zero, cameraMode: .nonAR, automaticallyConfigureSession: false)
        view.isOpaque = false
        view.backgroundColor = .clear
        view.environment.background = .color(.clear)
        view.isUserInteractionEnabled = false
        context.coordinator.anchor.addChild(model.root)
        context.coordinator.anchor.addChild(model.camera)
        view.scene.addAnchor(context.coordinator.anchor)
        synchronize()
        context.coordinator.record("view-make", view: view, ids: selectedIDs, mode: mode)
        if BoardHighlightDiagnostic.isEnabled {
            BoardHighlightDiagnostic.shared.startSamples(view: viewToken, scene: model)
        }
        return view
    }

    func updateUIView(_ view: ARView, context: Context) {
        synchronize()
        context.coordinator.record("view-update", view: view, ids: selectedIDs, mode: mode)
    }

    static func dismantleUIView(_ view: ARView, coordinator: Coordinator) {
        coordinator.record("view-disappear", view: view, ids: [], mode: .active)
        if BoardHighlightDiagnostic.isEnabled {
            BoardHighlightDiagnostic.shared.disappear(view: coordinator.viewToken, scene: coordinator.model)
        }
        if coordinator.model.root.parent === coordinator.anchor { coordinator.model.root.removeFromParent() }
        if coordinator.model.camera.parent === coordinator.anchor { coordinator.model.camera.removeFromParent() }
        view.scene.removeAnchor(coordinator.anchor)
    }

    @MainActor
    final class Coordinator {
        let model: BoardModelRealityScene
        let viewToken: UUID
        let hostToken = UUID()
        let anchor = AnchorEntity(world: .zero)
        private var lastSignature: String?
        private var sink: FileHandle?
        private var sequence = 0

        init(model: BoardModelRealityScene, viewToken: UUID) {
            self.model = model
            self.viewToken = viewToken
        }

        func record(_ event: String, view: ARView, ids: Set<String>, mode: BoardHighlightMode) {
            guard BoardHighlightDiagnostic.isEnabled else { return }
            let anchors = Array(view.scene.anchors)
            let present = anchors.contains { $0 === anchor }
            let children = present ? Array(anchor.children) : []
            // Here roots means enumerated attachment-anchor children, not fabricated model references.
            BoardHighlightDiagnostic.shared.capture(event, scene: model, view: viewToken,
                                                      roots: children)
            let identity: (AnyObject) -> String = { String(describing: ObjectIdentifier($0)) }
            let signature = "\(ids.sorted())|\(mode)|\(present)|\(model.root.isActive)|\(model.camera.isActive)|\(view.bounds)"
            if event == "view-update", signature == lastSignature { return }
            lastSignature = signature
            guard sequence < 256 else { return }
            sequence += 1
            let row: [String: Any] = [
                "event": event, "sequence": sequence, "complete": true,
                "epoch": Date().timeIntervalSince1970, "uptime": ProcessInfo.processInfo.systemUptime,
                "hostToken": hostToken.uuidString, "viewToken": viewToken.uuidString,
                "sceneLifecycleToken": model.diagnosticLifecycleToken.uuidString,
                "arViewID": identity(view), "arSceneID": identity(view.scene),
                "anchorID": identity(anchor), "sceneAnchorIDs": anchors.map(identity),
                "anchorPresent": present, "anchorChildIDs": children.map(identity),
                "rootID": identity(model.root), "cameraID": identity(model.camera),
                "rootParentIsOwnedAnchor": model.root.parent === anchor,
                "cameraParentIsOwnedAnchor": model.camera.parent === anchor,
                "rootSceneIsHostScene": model.root.scene === view.scene,
                "cameraSceneIsHostScene": model.camera.scene === view.scene,
                "rootActive": model.root.isActive, "cameraActive": model.camera.isActive,
                "bounds": [view.bounds.width, view.bounds.height],
                "requestedIDs": ids.sorted(), "requestedMode": String(describing: mode),
                "cameraMode": "nonAR", "contentRootIDScope": "actual owned attachmentAnchor.children"
            ]
            do {
                if sink == nil {
                    let raw = ProcessInfo.processInfo.environment["HANGTEN_REVIEW_DIAGNOSTIC_RUN"] ?? "placid-badger-cad-second-half"
                    let run = String(raw.filter { $0.isASCII && ($0.isLetter || $0.isNumber || $0 == "-" || $0 == "_") }.prefix(100))
                    let folder = FileManager.default.urls(for: .documentDirectory, in: .userDomainMask)[0]
                        .appendingPathComponent("HighlightDiagnostic-\(run)", isDirectory: true)
                    try FileManager.default.createDirectory(at: folder, withIntermediateDirectories: true)
                    let url = folder.appendingPathComponent("arview-host-\(hostToken.uuidString).jsonl")
                    guard FileManager.default.createFile(atPath: url.path, contents: nil) else { throw CocoaError(.fileWriteUnknown) }
                    sink = try FileHandle(forWritingTo: url)
                }
                var data = try JSONSerialization.data(withJSONObject: row, options: [.sortedKeys])
                data.append(0x0a)
                try sink?.write(contentsOf: data)
                if event == "view-disappear" { try sink?.synchronize(); try sink?.close(); sink = nil }
            } catch {
                try? FileHandle.standardError.write(contentsOf: Data("ARView host diagnostic error: \(error)\n".utf8))
            }
        }
    }
}
#endif

#if DEBUG
private struct BoardDiagnosticHostIdentity: Hashable {
    let scene: ObjectIdentifier
    let contactIDs: Set<String>
    let mode: BoardHighlightMode
    let positionID: String?
}
#endif
