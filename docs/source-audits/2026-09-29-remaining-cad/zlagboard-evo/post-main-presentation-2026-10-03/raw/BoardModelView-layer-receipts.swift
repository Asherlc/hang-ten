import RealityKit
import SwiftUI
import CoreImage
import Metal
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
    var usesFrameRenderer = false
    @State private var result: ResultState = .loading

    init(
        board: BoardRevision,
        presentation: BoardPresentation,
        positionID: String? = nil,
        highlightedContactIDs: Set<String>,
        highlightMode: BoardHighlightMode,
        onContactTap: ((PhysicalContact) -> Void)?,
        isDisplayOnly: Bool = false,
        usesFrameRenderer: Bool = false
    ) {
        self.board = board
        self.presentation = presentation
        self.positionID = positionID
        self.highlightedContactIDs = highlightedContactIDs
        self.highlightMode = highlightMode
        self.onContactTap = onContactTap
        self.isDisplayOnly = isDisplayOnly
        self.usesFrameRenderer = usesFrameRenderer
    }

    var body: some View {
        // Keep loading and disappearance scoped to this surface. Group forwards
        // lifecycle modifiers to its changing placeholder/model children.
        ZStack {
            if case .ready(let model) = result {
                if usesFrameRenderer, onContactTap == nil {
                    BoardFrameImageView(model: model, positionID: positionID,
                                        contactIDs: highlightedContactIDs, mode: highlightMode,
                                        isDisplayOnly: isDisplayOnly)
                    .id(ObjectIdentifier(model))
                    .accessibilityElement(children: .ignore)
                    .accessibilityLabel("\(board.name) hangboard")
                    .accessibilityValue(highlightedContactCue ?? "")
                    .accessibilityIdentifier("boardModel.3d")
                } else {
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
            if usesFrameRenderer { BoardFrameEnvironment.prewarm() }
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

    /// Expose all highlighted hold cues, including bilateral and mixed tasks.
    static func highlightedContactCue(
        for contacts: [PhysicalContact],
        highlightedContactIDs: Set<String>
    ) -> String? {
        let cues = Set(contacts.filter { highlightedContactIDs.contains($0.id) }
            .map { GripDiagramView.cueLabel(for: $0) }).sorted()
        return cues.isEmpty ? nil : cues.joined(separator: ", ")
    }

    private var highlightedContactCue: String? {
        Self.highlightedContactCue(
            for: board.contacts(in: presentation),
            highlightedContactIDs: highlightedContactIDs
        )
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

    @Environment(\.scenePhase) private var scenePhase
    @Environment(\.accessibilityReduceMotion) private var reduceMotion
    @State private var cameraRevision = 0
    @State private var lastDragTranslation: CGSize = .zero
    @State private var lastMagnification: CGFloat = 1
    @State private var didReportUnavailable = false
    #if DEBUG
    @State private var synchronizedCameraDiagnostic = "pending"
    @State private var contactTapRevision = 0
    @State private var lastTappedContactID = ""
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
                content.add(model.root)
                content.add(model.camera)
                applySync(size: size)
                if model.hasLiveRopes, positionID != nil {
                    if !model.hasLiveUpdateSubscription {
                        model.installLiveUpdateSubscription(content.subscribe(to: SceneEvents.Update.self) { [weak model] event in
                            let elapsed = event.deltaTime
                            Task { @MainActor [weak model] in model?.advanceLiveRopes(elapsed: elapsed) }
                        })
                    }
                } else {
                    model.installLiveUpdateSubscription(nil)
                }
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
                if model.hasLiveRopes, positionID != nil {
                    if !model.hasLiveUpdateSubscription {
                        model.installLiveUpdateSubscription(content.subscribe(to: SceneEvents.Update.self) { [weak model] event in
                            let elapsed = event.deltaTime
                            Task { @MainActor [weak model] in model?.advanceLiveRopes(elapsed: elapsed) }
                        })
                    }
                } else {
                    model.installLiveUpdateSubscription(nil)
                }
                #if DEBUG
                if ProcessInfo.processInfo.environment["HANGTEN_REVIEW_BOARD_DIAGNOSTICS"] == "1" {
                    let diagnostic = "revision=\(revision);rootActive=\(model.root.isActive);cameraActive=\(model.camera.isActive);sameScene=\(model.root.scene != nil && model.root.scene === model.camera.scene);azimuth=\(model.orbitAzimuth);elevation=\(model.orbitElevation);cameraPitch=\(asin(model.camera.orientation.act(SIMD3<Float>(0, 0, 1)).y));cameraSettled=\(model.isCameraAtTarget);selection=\(highlightedContactIDs.sorted().joined(separator: ","));tapRevision=\(contactTapRevision);pickedContact=\(lastTappedContactID)"
                    Task { @MainActor in
                        if synchronizedCameraDiagnostic != diagnostic {
                            synchronizedCameraDiagnostic = diagnostic
                        }
                    }
                }
                #endif
            }
            .task(id: CameraSelection(positionID: positionID, contactIDs: highlightedContactIDs)) {
                guard !UIAccessibility.isReduceMotionEnabled else { return }
                var wasAnimating = false
                for _ in 0..<10 {
                    try? await Task.sleep(for: .milliseconds(35))
                    guard !Task.isCancelled else { return }
                    let isAnimating = model.isCameraAnimating
                    if isAnimating || wasAnimating { cameraRevision &+= 1 }
                    wasAnimating = isAnimating
                }
            }
            .gesture(orbitGesture(size: size))
            .simultaneousGesture(magnifyGesture)
            .gesture(tapGesture)
            .overlay { accessibilityOverlay(size: size) }
            #if targetEnvironment(simulator)
            .background {
                // Drawable presentation also governs read-only workout and
                // Train previews; contact picking is unrelated to this policy.
                #if DEBUG
                if onContactTap != nil || ProcessInfo.processInfo.environment[
                    "HANGTEN_REVIEW_SKIP_NONINTERACTIVE_PRESENTATION"] != "1" {
                    BoardSimulatorPresentation().allowsHitTesting(false)
                }
                #else
                BoardSimulatorPresentation().allowsHitTesting(false)
                #endif
            }
            #endif
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
        .onAppear { model.setLiveActivity(scenePhase == .active) }
        .onDisappear {
            model.onLiveFrame=nil
            model.onLiveFailure=nil
            model.setLiveActivity(false)
        }
        .onChange(of:scenePhase) { _,phase in model.setLiveActivity(phase == .active) }
        .onChange(of:reduceMotion) { _,value in model.configureLiveMotion(reduceMotion:value,displayOnly:isDisplayOnly) }
        .modifier(BoardModelAccessibilityContainer(
            label: onContactTap == nil ? "\(boardName) hangboard" : nil,
            value: onContactTap == nil ? accessibilityValue : nil))
    }

    private struct CameraSelection: Hashable {
        let positionID: String?
        let contactIDs: Set<String>
    }

    private func applySync(size: CGSize) {
        model.configureLiveMotion(reduceMotion:reduceMotion,displayOnly:isDisplayOnly)
        let unavailableCallback = onUnavailable
        model.onLiveFailure = { unavailableCallback?() }
        let revisionBinding = $cameraRevision
        model.onLiveFrame = { Task { @MainActor in revisionBinding.wrappedValue &+= 1 } }
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
        #if DEBUG
        model.applyReviewCamera()
        #endif
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
                #if DEBUG
                if ProcessInfo.processInfo.environment["HANGTEN_REVIEW_BOARD_DIAGNOSTICS"] == "1" {
                    lastTappedContactID = id
                    contactTapRevision &+= 1
                    cameraRevision &+= 1
                }
                #endif
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

// Temporary candidate: explicit completed frames for the workout's non-pickable
// native board. Geometry, material, suspension and camera authoring remain in
// BoardModelRealityScene. No image is stored in a board package.
struct BoardFrameInput: Equatable {
    let positionID: String?
    let contacts: Set<String>
    let mode: BoardHighlightMode
    let size: CGSize
    let scale: CGFloat
}

/// Two completed native frames for the same presentation and camera.
struct BoardFrameCache<Value> {
    private struct Entry {
        let input: BoardFrameInput
        let orbit: SIMD3<Float>
        let value: Value
    }
    private var entries: [Entry] = []
    var count: Int { entries.count }

    mutating func store(_ value: Value, input: BoardFrameInput, orbit: SIMD3<Float>) {
        entries.removeAll {
            $0.orbit != orbit || $0.input.positionID != input.positionID
                || $0.input.contacts != input.contacts || $0.input.size != input.size
                || $0.input.scale != input.scale || $0.input.mode == input.mode
        }
        entries.append(Entry(input: input, orbit: orbit, value: value))
    }

    func value(for input: BoardFrameInput, orbit: SIMD3<Float>, exactViewport: Bool = false) -> Value? {
        entries.last { entry in
            guard entry.orbit == orbit, entry.input.positionID == input.positionID,
                  entry.input.contacts == input.contacts, entry.input.mode == input.mode else { return false }
            if entry.input.size == input.size && entry.input.scale == input.scale { return true }
            guard !exactViewport, entry.input.size.width > 0, entry.input.size.height > 0,
                  input.size.width > 0, input.size.height > 0 else { return false }
            let prior = entry.input.size.width / entry.input.size.height
            let next = input.size.width / input.size.height
            return prior.isFinite && next.isFinite && abs(prior - next) < 0.000001
        }?.value
    }
}

@MainActor
private enum BoardFrameEnvironment {
    private static var preparation: Task<EnvironmentResource, Error>?
    static func prewarm() {
        guard preparation == nil else { return }
        preparation = Task {
            guard let space = CGColorSpace(name: CGColorSpace.sRGB),
                  let bitmap = CGContext(data: nil, width: 32, height: 16,
                    bitsPerComponent: 8, bytesPerRow: 0, space: space,
                    bitmapInfo: CGImageAlphaInfo.premultipliedLast.rawValue) else {
                throw BoardFrameCoordinator.Failure.environment
            }
            // Analytic uniform white illumination; display adaptation only.
            bitmap.setFillColor(red: 1, green: 1, blue: 1, alpha: 1)
            bitmap.fill(CGRect(x: 0, y: 0, width: 32, height: 16))
            guard let image = bitmap.makeImage() else { throw BoardFrameCoordinator.Failure.environment }
            return try await EnvironmentResource(equirectangular: image,
                withName: "placid-badger-cad-second-half-board-frame-neutral-\(UUID().uuidString)")
        }
    }
    static func resource() async throws -> EnvironmentResource {
        prewarm()
        do { return try await preparation!.value }
        catch { preparation = nil; throw error }
    }
}

@MainActor
private final class BoardFrameCoordinator: ObservableObject {
    @Published private var cache = BoardFrameCache<UIImage>()
    private var presentedOrbit = SIMD3<Float>(0, 0, 1)
    @Published private(set) var unavailable = false
    let model: BoardModelRealityScene
    private var input: BoardFrameInput?
    private var orbit = SIMD3<Float>(0, 0, 1)
    private var renderer: RealityRenderer?
    private var device: (any MTLDevice)?
    private var context: CIContext?
    private var setup: Task<Void, Never>?
    private var active = false
    private var revision = 0
    private var pending: Request?
    private var frame: Frame?
    private struct Request {
        let revision: Int
        let input: BoardFrameInput
        let orbit: SIMD3<Float>
    }
    // Retains the scene (including the ODR lease), renderer and GPU resources
    // until completion and eager image conversion finish, even after disappear.
    private final class Frame {
        let request: Request
        let model: BoardModelRealityScene
        let renderer: RealityRenderer
        let texture: any MTLTexture
        let output: RealityRenderer.CameraOutput
        init(_ request: Request, _ model: BoardModelRealityScene, _ renderer: RealityRenderer,
             _ texture: any MTLTexture, _ output: RealityRenderer.CameraOutput) {
            self.request = request; self.model = model; self.renderer = renderer
            self.texture = texture; self.output = output
        }
    }
    enum Failure: Error { case environment, viewport, renderer, texture, conversion, position }
    init(model: BoardModelRealityScene) { self.model = model }

    func submit(_ next: BoardFrameInput) {
        guard !unavailable else { return }
        let changed = !active || input != next
        active = true; input = next
        if changed { enqueue() }
    }
    func orbitBy(azimuth: Float = 0, elevation: Float = 0, zoomRatio: Float = 1) {
        guard active, !unavailable, azimuth.isFinite, elevation.isFinite,
              zoomRatio.isFinite, zoomRatio > 0 else { return }
        orbit.x = (orbit.x + azimuth).truncatingRemainder(dividingBy: .pi * 2)
        orbit.y = min(max(orbit.y + elevation, -0.55), 0.55)
        orbit.z = min(max(orbit.z / zoomRatio, 0.75), 1.35)
        enqueue()
    }
    func resetCamera() {
        guard active, !unavailable else { return }
        orbit = SIMD3(0, 0, 1); enqueue()
    }
    func disappear() {
        active = false; revision += 1; pending = nil; cache = BoardFrameCache()
    }
    private func enqueue() {
        guard let input else { return }
        revision += 1
        pending = Request(revision: revision, input: input, orbit: orbit)
        drain()
    }
    func image(for input: BoardFrameInput) -> UIImage? {
        // A completed old camera view can remain visible while an orbit gesture
        // renders. A different contact set, position, or mode never substitutes.
        cache.value(for: input, orbit: orbit) ?? cache.value(for: input, orbit: presentedOrbit)
    }
    private func drain() {
        guard active, !unavailable, frame == nil, let input else { return }
        if pending == nil, !input.contacts.isEmpty,
           cache.value(for: input, orbit: orbit, exactViewport: true) != nil {
            let alternate = BoardFrameInput(positionID: input.positionID, contacts: input.contacts,
                mode: input.mode == .active ? .preview : .active, size: input.size, scale: input.scale)
            if cache.value(for: alternate, orbit: orbit, exactViewport: true) == nil {
                pending = Request(revision: revision, input: alternate, orbit: orbit)
            }
        }
        guard let request = pending else { return }
        if cache.value(for: request.input, orbit: request.orbit, exactViewport: true) != nil {
            pending = nil
            model.highlight(input.contacts, mode: input.mode)
            drain()
            return
        }
        if renderer == nil {
            guard setup == nil else { return }
            setup = Task { @MainActor [self] in
                do {
                    let environment = try await BoardFrameEnvironment.resource()
                    guard active else { setup = nil; return }
                    guard let device = MTLCreateSystemDefaultDevice() else { throw Failure.renderer }
                    let renderer = try RealityRenderer()
                    // Runtime studio lighting follows the camera, making cavity
                    // normals and self-shadowing legible under every orbit.
                    let key = Entity(), fill = Entity()
                    key.components.set(DirectionalLightComponent(color: .white, intensity: 3_200))
                    key.components.set(DirectionalLightComponent.Shadow())
                    fill.components.set(DirectionalLightComponent(color: .white, intensity: 600))
                    model.camera.addChild(key); model.camera.addChild(fill)
                    key.look(at: .zero, from: SIMD3(-3, 4, 5), relativeTo: model.camera)
                    fill.look(at: .zero, from: SIMD3(3, 1, 5), relativeTo: model.camera)
                    renderer.entities.append(contentsOf: [model.root, model.camera])
                    renderer.activeCamera = model.camera
                    renderer.lighting.resource = environment
                    renderer.lighting.intensityExponent = 0
                    renderer.extendedDynamicRangeOutput = false
                    renderer.cameraSettings.colorBackground = .color(CGColor(gray: 0, alpha: 0))
                    self.renderer = renderer; self.device = device
                    context = CIContext(mtlDevice: device)
                    setup = nil; drain()
                } catch {
                    setup = nil
                    if active { fail() }
                }
            }
            return
        }
        pending = nil
        do {
            let input = request.input, size = input.size
            guard size.width.isFinite, size.height.isFinite, input.scale.isFinite,
                  size.width >= 0, size.height >= 0, input.scale > 0,
                  size.width * input.scale <= 4096, size.height * input.scale <= 4096 else {
                throw Failure.viewport
            }
            guard size.width > 0, size.height > 0 else { return }
            guard let renderer, let device else { throw Failure.renderer }
            var camera = model.camera.camera
            camera.fieldOfViewInDegrees = 30
            camera.fieldOfViewOrientation = .vertical
            camera.near = 0.001; camera.far = 1000
            model.camera.camera = camera
            model.frame(in: size)
            let selected = model.select(positionID: input.positionID)
            if input.positionID != nil, !selected { throw Failure.position }
            model.orbit(azimuth: request.orbit.x, elevation: request.orbit.y, zoomScale: request.orbit.z)
            model.highlight(input.contacts, mode: input.mode)
            let descriptor = MTLTextureDescriptor.texture2DDescriptor(pixelFormat: .bgra8Unorm_srgb,
                width: Int(ceil(size.width * input.scale)), height: Int(ceil(size.height * input.scale)),
                mipmapped: false)
            descriptor.usage = [.renderTarget, .shaderRead, .shaderWrite]
            descriptor.storageMode = .private
            guard let texture = device.makeTexture(descriptor: descriptor) else { throw Failure.texture }
            let output = try RealityRenderer.CameraOutput(.singleProjection(colorTexture: texture))
            let submitted = Frame(request, model, renderer, texture, output)
            frame = submitted
            do {
                try renderer.updateAndRender(deltaTime: 0, cameraOutput: output, onComplete: { [self, submitted] _ in
                    Task { @MainActor in
                        withExtendedLifetime(submitted) { completed(request.revision) }
                    }
                })
            } catch {
                frame = nil
                throw error
            }
        } catch { fail() }
    }
    private func completed(_ value: Int) {
        guard let frame, frame.request.revision == value else { return }
        defer { self.frame = nil; drain() }
        guard active, !unavailable, value == revision else { return }
        guard let context, let space = CGColorSpace(name: CGColorSpace.sRGB),
              let source = CIImage(mtlTexture: frame.texture, options: [.colorSpace: space]) else {
            fail(); return
        }
        let normalized = source.oriented(.downMirrored)
        guard let rendered = context.createCGImage(normalized, from: normalized.extent,
            format: .RGBA8, colorSpace: space, deferred: false) else { fail(); return }
        let image = UIImage(cgImage: rendered, scale: frame.request.input.scale, orientation: .up)
        presentedOrbit = frame.request.orbit
        cache.store(image, input: frame.request.input, orbit: frame.request.orbit)
        if let input { model.highlight(input.contacts, mode: input.mode) }
    }
    private func fail() { unavailable = true; cache = BoardFrameCache(); pending = nil }
}

private struct BoardFrameImageView: View {
    let positionID: String?
    let contactIDs: Set<String>
    let mode: BoardHighlightMode
    let isDisplayOnly: Bool
    @Environment(\.displayScale) private var displayScale
    @StateObject private var coordinator: BoardFrameCoordinator
    @State private var lastDrag: CGSize = .zero
    @State private var lastMagnification: CGFloat = 1
    init(model: BoardModelRealityScene, positionID: String?, contactIDs: Set<String>,
         mode: BoardHighlightMode, isDisplayOnly: Bool) {
        self.positionID = positionID; self.contactIDs = contactIDs; self.mode = mode
        self.isDisplayOnly = isDisplayOnly
        _coordinator = StateObject(wrappedValue: BoardFrameCoordinator(model: model))
    }
    var body: some View {
        // Semantic values are captured outside GeometryReader's escaping closure.
        let contacts = contactIDs, selection = positionID, highlightMode = mode
        GeometryReader { proxy in
            let input = BoardFrameInput(positionID: selection, contacts: contacts,
                mode: highlightMode, size: proxy.size, scale: displayScale)
            ZStack {
                if coordinator.unavailable { BoardModelUnavailableView() }
                else if let image = coordinator.image(for: input) {
                    Image(uiImage: image).resizable().interpolation(.high).frame(width: proxy.size.width, height: proxy.size.height)
                } else { Color.clear }
            }
            .contentShape(Rectangle())
            .onAppear { coordinator.submit(input) }
            .onChange(of: input) { _, next in coordinator.submit(next) }
            .simultaneousGesture(TapGesture().onEnded {
                coordinator.resetCamera()
            })
            .gesture(DragGesture(minimumDistance: 4).onChanged { value in
                let delta = CGSize(width: value.translation.width - lastDrag.width,
                                   height: value.translation.height - lastDrag.height)
                lastDrag = value.translation
                coordinator.orbitBy(azimuth: -Float(delta.width / max(proxy.size.width, 1)) * 0.9,
                                    elevation: -Float(delta.height / max(proxy.size.height, 1)) * 0.65)
            }.onEnded { _ in lastDrag = .zero })
            .simultaneousGesture(MagnificationGesture().onChanged { value in
                let ratio = value / max(lastMagnification, 0.001)
                lastMagnification = value
                coordinator.orbitBy(zoomRatio: Float(ratio))
            }.onEnded { _ in lastMagnification = 1 })
            .allowsHitTesting(!isDisplayOnly)
        }
        .onDisappear { coordinator.disappear() }
    }
}
#if targetEnvironment(simulator)
import QuartzCore
/// Keep Simulator drawable presentation independent of worker-thread CA transactions.
private struct BoardSimulatorPresentation: UIViewRepresentable {
    func makeUIView(context: Context) -> PresentationView { PresentationView() }
    func updateUIView(_ view: PresentationView, context: Context) { view.scheduleConfiguration() }

    final class PresentationView: UIView {
        private var pending: DispatchWorkItem?
        private var attempts = 0
        private var attemptedViewport: CGRect?
        private weak var configuredLayer: CAMetalLayer?

        override func didMoveToWindow() {
            super.didMoveToWindow()
            pending?.cancel()
            pending = nil
            attempts = 0
            attemptedViewport = nil
            configuredLayer = nil
            if window != nil { scheduleConfiguration() }
        }

        override func layoutSubviews() {
            super.layoutSubviews()
            scheduleConfiguration()
        }

        func scheduleConfiguration() {
            guard let window else { return }
            let viewport = convert(bounds, to: window)
            if attemptedViewport != viewport || configuredLayer?.presentsWithTransaction == true {
                attempts = 0
                configuredLayer = nil
                attemptedViewport = viewport
            }
            if let configuredLayer, configuredLayer.superlayer != nil,
               !configuredLayer.presentsWithTransaction { return }
            guard pending == nil, attempts < 120 else { return }
            let work = DispatchWorkItem { [weak self] in
                guard let self else { return }
                self.pending = nil
                self.configurePresentation()
            }
            pending = work
            DispatchQueue.main.asyncAfter(deadline: .now() + 0.05, execute: work)
        }

        private func configurePresentation() {
            guard let window, bounds.width > 0, bounds.height > 0 else {
                attempts += 1
                scheduleConfiguration()
                return
            }
            let viewport = convert(bounds, to: window)
            var ancestor = superview
            while let container = ancestor {
                var candidates: [CAMetalLayer] = []
                var visited = 0
                func collect(_ layer: CALayer) {
                    visited += 1
                    guard visited < 4096 else { return }
                    if let metal = layer as? CAMetalLayer {
                        let frame = metal.convert(metal.bounds, to: window.layer)
                        if abs(frame.minX - viewport.minX) < 1,
                           abs(frame.minY - viewport.minY) < 1,
                           abs(frame.width - viewport.width) < 1,
                           abs(frame.height - viewport.height) < 1 {
                            candidates.append(metal)
                        }
                    }
                    for child in layer.sublayers ?? [] { collect(child) }
                }
                collect(container.layer)
                if candidates.count == 1, visited < 4096 {
                    let layer = candidates[0]
                    layer.presentsWithTransaction = false
                    configuredLayer = layer
                    #if DEBUG
                    FileHandle.standardError.write(Data("[BoardSimulatorPresentation] configured uptime=\(ProcessInfo.processInfo.systemUptime) layer=\(ObjectIdentifier(layer)) asynchronous=\(!layer.presentsWithTransaction) viewport=\(viewport) attempt=\(attempts)\n".utf8))
                    #endif
                    attempts = 120
                    return
                }
                if container === window { break }
                ancestor = container.superview
            }
            attempts += 1
            #if DEBUG
            if attempts == 120 {
                var metalFrames: [CGRect] = []
                var visited = 0
                func collectFrames(_ layer: CALayer) {
                    visited += 1
                    guard visited < 4096 else { return }
                    if let metal = layer as? CAMetalLayer {
                        metalFrames.append(metal.convert(metal.bounds, to: window.layer))
                    }
                    for child in layer.sublayers ?? [] { collectFrames(child) }
                }
                collectFrames(window.layer)
                FileHandle.standardError.write(Data("[BoardSimulatorPresentation] exhausted uptime=\(ProcessInfo.processInfo.systemUptime) viewport=\(viewport) metalFrames=\(metalFrames) visited=\(visited)\n".utf8))
            }
            #endif
            scheduleConfiguration()
        }
    }
}
#endif
