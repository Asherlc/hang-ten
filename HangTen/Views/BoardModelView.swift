import RealityKit
import SwiftUI
#if DEBUG
import Metal
#endif

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
    @State private var framebufferTrace = BoardFramebufferTrace()
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
            RealityView { content in
                // Board maps use the authored camera, without device tracking
                // or the AR session's implicit non-AR fallback.
                content.camera = .virtual
                #if DEBUG
                if onContactTap != nil, framebufferTraceEnabled, #available(iOS 26.0, *) {
                    content.renderingEffects.customPostProcessing = .effect(
                        BoardFramebufferEffect(trace: framebufferTrace))
                }
                #endif
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
            // A different scene needs a fresh RealityView make closure so its
            // root and camera replace the prior scene entities.
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
        traceFramebufferState(size: size, phase: "sync")
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
                traceFramebufferState(size: .zero, phase: "reset")
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
                traceFramebufferState(size: size, phase: "orbit")
                cameraRevision &+= 1
            }
            .onEnded { _ in
                lastDragTranslation = .zero
                traceFramebufferState(size: size, phase: "orbit-ended")
            }
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

    private var framebufferTraceEnabled: Bool {
        #if DEBUG
        return ProcessInfo.processInfo.environment["HANGTEN_REVIEW_FRAMEBUFFER"] == "1"
        #else
        return false
        #endif
    }

    /// Records submitted state without publishing SwiftUI or accessibility changes.
    private func traceFramebufferState(size: CGSize, phase: String) {
        #if DEBUG
        guard onContactTap != nil, framebufferTraceEnabled else { return }
        let materials = model.contactEntities.keys.sorted().map { id in
            let assigned = model.contactEntities[id, default: []].map {
                String(describing: $0.model?.materials)
            }.joined(separator: ";")
            return "\(id)=\(assigned)"
        }.joined(separator: "|")
        let projections = highlightedContactIDs.sorted().map { id in
            "\(id)=\(String(describing: model.projectedContactCenter(id, viewport: size, fieldOfViewDegrees: fieldOfViewDegrees)))"
        }.joined(separator: "|")
        framebufferTrace.record(
            "board=\(boardName);scene=\(ObjectIdentifier(model));root=\(ObjectIdentifier(model.root));"
            + "camera=\(ObjectIdentifier(model.camera));phase=\(phase);size=\(size);"
            + "requested=\(highlightedContactIDs.sorted());position=\(positionID ?? "nil");"
            + "azimuth=\(model.orbitAzimuth);elevation=\(model.orbitElevation);"
            + "matrix=\(model.camera.transform.matrix);projected=\(projections);materials=\(materials)")
        #endif
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
/// Temporary bounded trace. Locks protect callback/main-thread exchange; no view state is published.
private final class BoardFramebufferTrace: @unchecked Sendable {
    struct Sample: Sendable {
        let sequence: Int
        let state: String
        let elapsed: Double
        let includePixels: Bool
    }
    private let lock = NSLock()
    private var state = "pending"
    private var changedAt = ProcessInfo.processInfo.systemUptime
    private var nextCheckpoint = 0
    private var sequence = 0
    private var inFlight = 0
    private var payloads = 0
    private var stateMessages = 0
    private let checkpoints: [Double] = [0, 0.5, 2, 10, 20]

    func record(_ value: String) {
        lock.lock()
        guard value != state else { lock.unlock(); return }
        state = value
        changedAt = ProcessInfo.processInfo.systemUptime
        nextCheckpoint = 0
        let emit = stateMessages < 64
        stateMessages += 1
        lock.unlock()
        if emit { print("[BoardFramebufferState] \(value)") }
    }

    func sample() -> Sample? {
        lock.lock()
        defer { lock.unlock() }
        let elapsed = ProcessInfo.processInfo.systemUptime - changedAt
        guard sequence < 32, inFlight < 2, nextCheckpoint < checkpoints.count,
              elapsed >= checkpoints[nextCheckpoint] else { return nil }
        nextCheckpoint += 1
        sequence += 1
        inFlight += 1
        // Keep images for settled checkpoints, rather than consuming the payload
        // budget on intermediate drag callbacks. Hashes remain available earlier.
        let includePixels = payloads < 12 && (nextCheckpoint == 3 || nextCheckpoint == 4)
        if includePixels { payloads += 1 }
        return Sample(sequence: sequence, state: state, elapsed: elapsed, includePixels: includePixels)
    }

    func finish(_ sample: Sample, fields: [String: Any]) {
        lock.lock()
        inFlight -= 1
        let completionState = state
        let remaining = 32 - sequence
        lock.unlock()
        var message = fields
        message["sequence"] = sample.sequence
        message["stateAtRequest"] = sample.state
        message["stateAtCompletion"] = completionState
        message["stateChangedDuringGPUWork"] = completionState != sample.state
        message["remainingReadbackBudget"] = remaining
        message["secondsSinceStateChange"] = sample.elapsed
        message["uptime"] = ProcessInfo.processInfo.systemUptime
        if let data = try? JSONSerialization.data(withJSONObject: message, options: [.sortedKeys]),
           let text = String(data: data, encoding: .utf8) {
            print("[BoardFramebuffer] \(text)")
        }
    }
}

/// Copies the normal rendered source to its required output unchanged, and samples that source.
@available(iOS 26.0, *)
private struct BoardFramebufferEffect: PostProcessEffect {
    let trace: BoardFramebufferTrace

    func postProcess(context: borrowing PostProcessEffectContext<any MTLCommandBuffer>) {
        guard let encoder = context.commandBuffer.makeBlitCommandEncoder() else {
            if let sample = trace.sample() {
                trace.finish(sample, fields: ["error": "blit encoder unavailable; diagnostic output invalid"])
            }
            return
        }
        encoder.copy(from: context.sourceColorTexture, to: context.targetColorTexture)
        guard let sample = trace.sample() else { encoder.endEncoding(); return }
        let source = context.sourceColorTexture
        let bytesPerPixel: Int
        switch source.pixelFormat {
        case .bgra8Unorm, .bgra8Unorm_srgb, .rgba8Unorm, .rgba8Unorm_srgb,
             .rgb10a2Unorm, .bgr10a2Unorm: bytesPerPixel = 4
        case .rgba16Float: bytesPerPixel = 8
        case .rgba32Float: bytesPerPixel = 16
        default:
            encoder.endEncoding()
            trace.finish(sample, fields: ["error": "unsupported source format", "format": source.pixelFormat.rawValue])
            return
        }
        let width = source.width
        let height = source.height
        let packedRow = width * bytesPerPixel
        let row = ((packedRow + 255) / 256) * 256
        guard row * height <= 16 * 1024 * 1024,
              let buffer = context.device.makeBuffer(length: row * height, options: .storageModeShared) else {
            encoder.endEncoding()
            trace.finish(sample, fields: ["error": "readback allocation bounded or failed"])
            return
        }
        encoder.copy(from: source, sourceSlice: 0, sourceLevel: 0,
                     sourceOrigin: MTLOrigin(x: 0, y: 0, z: 0),
                     sourceSize: MTLSize(width: width, height: height, depth: 1),
                     to: buffer, destinationOffset: 0, destinationBytesPerRow: row,
                     destinationBytesPerImage: row * height)
        encoder.endEncoding()
        let projection = String(describing: context.projection)
        let format = source.pixelFormat.rawValue
        let time = context.time
        let trace = trace
        context.commandBuffer.addCompletedHandler { command in
            var fields: [String: Any] = ["width": width, "height": height, "format": format,
                                         "projection": projection, "frameTime": time,
                                         "commandStatus": command.status.rawValue]
            guard command.status == .completed else {
                fields["error"] = String(describing: command.error)
                trace.finish(sample, fields: fields)
                return
            }
            var pixels = Data(capacity: packedRow * height)
            for y in 0..<height {
                pixels.append(buffer.contents().advanced(by: y * row).assumingMemoryBound(to: UInt8.self),
                              count: packedRow)
            }
            var hash: UInt64 = 14695981039346656037
            for byte in pixels { hash = (hash ^ UInt64(byte)) &* 1099511628211 }
            fields["pixelHashFNV1a64"] = String(hash, radix: 16)
            if sample.includePixels {
                do {
                    let compressed = try (pixels as NSData).compressed(using: .zlib)
                    fields["zlibBase64Pixels"] = compressed.base64EncodedString()
                    fields["packedBytesPerRow"] = packedRow
                } catch { fields["payloadError"] = String(describing: error) }
            }
            trace.finish(sample, fields: fields)
        }
    }
}
#endif
