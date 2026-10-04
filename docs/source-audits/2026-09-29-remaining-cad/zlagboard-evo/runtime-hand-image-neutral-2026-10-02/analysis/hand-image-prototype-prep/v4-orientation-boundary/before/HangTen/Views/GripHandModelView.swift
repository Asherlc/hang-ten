import RealityKit
import Metal
import SwiftUI
#if DEBUG
import CoreImage
import CryptoKit
#endif

/// Rendering parameters, not anatomical measurements or training prescriptions.
/// Finger membership always comes from the routine's explicit configuration.
struct GripHandPose: Equatable {
    let posture: GripType?
    let highlightedFingers: Set<FingerSlot>
    let hasExplicitFingers: Bool

    init(posture: GripType?, fingerConfiguration: FingerConfiguration?) {
        self.posture = posture
        highlightedFingers = fingerConfiguration?.engagedFingers ?? []
        hasExplicitFingers = fingerConfiguration != nil
    }

    func action() -> String {
        switch posture {
        case .halfCrimp: return "HalfCrimp"
        case .fullCrimp: return "FullCrimp"
        case .openHand: return "OpenHand"
        case .sloper: return "Sloper"
        case .fourFingerPocket, .threeFingerPocket, .twoFingerPocket:
            let mask = (highlightedFingers.contains(.index) ? 1 : 0)
                | (highlightedFingers.contains(.middle) ? 2 : 0)
                | (highlightedFingers.contains(.ring) ? 4 : 0)
                | (highlightedFingers.contains(.pinky) ? 8 : 0)
            return "Pocket\(mask)"
        case nil: return "Neutral"
        }
    }
}

/// Displays the evaluated surfaces authored in Art/GripHand/GripHand.blend.
/// Pose changes preserve Blender deformation and smoothing exactly.
@MainActor
private final class GripHandSceneStorage {
    private let makeScene: @MainActor () -> GripHandRealityScene
    lazy var scene = makeScene()

    init(makeScene: @escaping @MainActor () -> GripHandRealityScene = { GripHandRealityScene() }) {
        self.makeScene = makeScene
    }
}

/// Makes the scroll-or-orbit choice once, at the first active drag update.
/// The claiming event seeds the origin so earlier travel cannot jump the camera.
struct GripHandDragState {
    enum Disposition: Equatable { case undecided, orbit, scroll }

    private(set) var disposition: Disposition = .undecided
    private var lastTranslation: CGSize = .zero

    mutating func advance(translation: CGSize, velocity: CGSize) -> CGSize? {
        switch disposition {
        case .undecided:
            let shouldOrbit = OrbitPanArbitration.shouldBegin(
                translation: CGPoint(x: translation.width, y: translation.height),
                velocity: CGPoint(x: velocity.width, y: velocity.height)
            )
            disposition = shouldOrbit ? .orbit : .scroll
            lastTranslation = translation
            return nil
        case .scroll:
            return nil
        case .orbit:
            let delta = CGSize(width: translation.width - lastTranslation.width,
                               height: translation.height - lastTranslation.height)
            lastTranslation = translation
            return delta
        }
    }

    mutating func reset() { self = Self() }
}

#if DEBUG
// Diagnostic launch constant. This affects only descendants of WorkoutView.
@MainActor
enum WorkoutPrestartHandDiagnostic {
    static let isEnabled = BoardHighlightDiagnostic.isEnabled
        && ProcessInfo.processInfo.environment["HANGTEN_REVIEW_SUPPRESS_PRESTART_HAND_HOSTS"] == "1"
}

private struct WorkoutDiagnosticPrestartHandKey: EnvironmentKey {
    static let defaultValue = false
}

extension EnvironmentValues {
    var workoutDiagnosticIsPrestart: Bool {
        get { self[WorkoutDiagnosticPrestartHandKey.self] }
        set { self[WorkoutDiagnosticPrestartHandKey.self] = newValue }
    }
}
#endif

@MainActor
struct GripHandModelView: View {
    let posture: GripType?
    let fingerConfiguration: FingerConfiguration?
    let side: GripCueSide
    let resetToken: Int
    @State private var sceneStorage: GripHandSceneStorage
    @State private var isUnavailable: Bool
    @State private var dragState = GripHandDragState()
    @State private var lastMagnification: CGFloat = 1
    @State private var cameraRevision = 0
    #if DEBUG
    @State private var diagnosticHandViewToken = UUID()
    @Environment(\.workoutDiagnosticIsPrestart) private var diagnosticIsPrestart
    #endif

    private var scene: GripHandRealityScene { sceneStorage.scene }

    init(posture: GripType?, fingerConfiguration: FingerConfiguration?, side: GripCueSide,
         resetToken: Int = 0) {
        self.posture = posture
        self.fingerConfiguration = fingerConfiguration
        self.side = side
        self.resetToken = resetToken
        _sceneStorage = State(initialValue: GripHandSceneStorage())
        _isUnavailable = State(initialValue: false)
    }

    init(posture: GripType?, fingerConfiguration: FingerConfiguration?, side: GripCueSide,
         resetToken: Int, scene: GripHandRealityScene) {
        self.posture = posture
        self.fingerConfiguration = fingerConfiguration
        self.side = side
        self.resetToken = resetToken
        _sceneStorage = State(initialValue: GripHandSceneStorage(makeScene: { scene }))
        _isUnavailable = State(initialValue: scene.isUnavailable)
    }

    var body: some View {
        #if DEBUG
        if BoardHighlightDiagnostic.suppressesAllHandHosts
            || (WorkoutPrestartHandDiagnostic.isEnabled && diagnosticIsPrestart) {
            Color.clear
                .frame(maxWidth: .infinity, maxHeight: .infinity)
                .allowsHitTesting(false)
                .accessibilityHidden(true)
        } else if HandImagePrototype.enabled {
            HandImagePrototypeView(pose: GripHandPose(posture: posture, fingerConfiguration: fingerConfiguration),
                                   side: side, reset: resetToken,
                                   makeScene: { [sceneStorage] in .single(sceneStorage.scene) })
        } else {
            handContent
        }
        #else
        handContent
        #endif
    }

    private var handContent: some View {
        let _ = cameraRevision
        return GeometryReader { proxy in
            let size = proxy.size
            RealityView { content in
                #if DEBUG
                if BoardHighlightDiagnostic.isEnabled {
                    BoardHighlightDiagnostic.shared.handLifecycle(kind: "single",
                        event: "make-entry", root: scene.root, camera: scene.camera,
                        lifetime: scene.diagnosticHandLifetimeToken, view: diagnosticHandViewToken)
                }
                #endif
                content.camera = .virtual
                content.add(scene.root)
                syncScene(in: size)
                updateUnavailableState()
            } update: { _ in
                syncScene(in: size)
                updateUnavailableState()
            }
            .simultaneousGesture(orbitGesture(size: size))
            .simultaneousGesture(magnifyGesture)
            .overlay {
                if isUnavailable {
                    Text("3D hand unavailable")
                        .font(.caption2)
                        .foregroundStyle(.secondary)
                        .multilineTextAlignment(.center)
                        .frame(maxWidth: .infinity, maxHeight: .infinity)
                        .accessibilityHidden(true)
                }
            }
            #if DEBUG
            .onAppear { [viewToken = diagnosticHandViewToken] in
                if BoardHighlightDiagnostic.recordsHandLifetimes {
                    BoardHighlightDiagnostic.shared.handViewLifecycle(view: viewToken, event: "appeared")
                }
            }
            .onDisappear { [viewToken = diagnosticHandViewToken] in
                if BoardHighlightDiagnostic.recordsHandLifetimes {
                    BoardHighlightDiagnostic.shared.handViewLifecycle(view: viewToken, event: "disappeared")
                }
            }
            #endif
            .accessibilityHidden(true)
        }
    }

    func syncScene(in size: CGSize) {
        scene.update(pose: GripHandPose(posture: posture, fingerConfiguration: fingerConfiguration),
                     side: side, viewportSize: size, resetToken: resetToken)
    }

    private func updateUnavailableState() {
        let unavailable = scene.isUnavailable
        guard unavailable != isUnavailable else { return }
        Task { @MainActor in isUnavailable = unavailable }
    }

    private func orbitGesture(size: CGSize) -> some Gesture {
        DragGesture(minimumDistance: OrbitPanArbitration.activationDistance)
            .onChanged { value in
                guard let delta = dragState.advance(translation: value.translation,
                                                    velocity: value.velocity) else { return }
                scene.orbit(azimuthDelta: Float(-delta.width / max(size.width, 1)) * 0.9,
                            elevationDelta: Float(-delta.height / max(size.height, 1)) * 0.65)
                cameraRevision &+= 1
            }
            .onEnded { _ in dragState.reset() }
    }

    private var magnifyGesture: some Gesture {
        MagnificationGesture()
            .onChanged { value in
                let ratio = value / max(lastMagnification, 0.001)
                lastMagnification = value
                scene.orbit(azimuthDelta: 0, elevationDelta: 0, zoomScale: Float(ratio))
                cameraRevision &+= 1
            }
            .onEnded { _ in lastMagnification = 1 }
    }

}

/// Portable Blender export. Validate every surface before creating GPU resources.
struct GripHandAsset: Decodable {
    struct Surface: Decodable {
        let positions: [Float]
        let normals: [Float]
    }

    let schemaVersion: Int
    let indices: [UInt32]
    let digitIndices: [Int]
    let highlightWeights: [Float]
    let poses: [String: Surface]

    enum AssetError: Error { case missingResource, invalidMesh }

    static let bundled: Result<GripHandAsset, Error> = Result {
        guard let url = Bundle.main.url(forResource: "hand-mesh", withExtension: "json") else {
            throw AssetError.missingResource
        }
        return try decode(Data(contentsOf: url))
    }

    static func decode(_ data: Data) throws -> GripHandAsset {
        let asset = try JSONDecoder().decode(GripHandAsset.self, from: data)
        try asset.validate()
        return asset
    }

    var vertexCount: Int { digitIndices.count }

    func validate() throws {
        func require(_ condition: Bool) throws {
            if !condition { throw AssetError.invalidMesh }
        }
        try require(schemaVersion == 2 && vertexCount > 0)
        try require(!indices.isEmpty && indices.count.isMultiple(of: 3)
                    && indices.allSatisfy { $0 < vertexCount })
        try require(digitIndices.allSatisfy { (0...5).contains($0) })
        try require(highlightWeights.count == vertexCount
                    && highlightWeights.allSatisfy { $0.isFinite && (0...1).contains($0) })
        let required = ["Neutral", "OpenHand", "HalfCrimp", "FullCrimp", "Sloper"]
            + (0...15).map { "Pocket\($0)" }
        try require(required.allSatisfy { poses[$0] != nil })
        for surface in poses.values {
            try require(surface.positions.count == vertexCount * 3
                        && surface.normals.count == surface.positions.count)
            try require(surface.positions.allSatisfy(\.isFinite)
                        && surface.normals.allSatisfy(\.isFinite))
        }
    }
}

struct GripHandRealityMeshBuilder {
    private static let baseColor = SIMD4<Float>(0.687, 0.392, 0.242, 1)
    private static let highlightColor = SIMD4<Float>(0.966, 0.0615, 0.0108, 1)

    static func vertexColors(
        asset: GripHandAsset,
        action: GripHandPose,
        selectedFingers: Set<FingerSlot>
    ) throws -> [SIMD4<Float>] {
        guard asset.poses[action.action()] != nil else {
            throw GripHandAsset.AssetError.invalidMesh
        }

        return asset.digitIndices.indices.map { vertex in
            let finger: FingerSlot?
            switch asset.digitIndices[vertex] {
            case 2: finger = .index
            case 3: finger = .middle
            case 4: finger = .ring
            case 5: finger = .pinky
            default: finger = nil
            }

            let authoredWeight = asset.highlightWeights[vertex]
            let strength = finger.map { selectedFingers.contains($0) ? authoredWeight : 0 } ?? 0
            let clampedStrength = min(max(strength, 0), 1)
            if clampedStrength == 0 { return baseColor }
            if clampedStrength == 1 { return highlightColor }
            return baseColor + (highlightColor - baseColor) * clampedStrength
        }
    }
}

@MainActor
final class GripHandRealitySurface {
    private struct Vertex {
        var position: SIMD3<Float>
        var normal: SIMD3<Float>
        var color: SIMD4<Float>
    }

    private struct MeshKey: Hashable {
        let action: String
        let fingers: Set<FingerSlot>
    }

    let root = Entity()
    let modelEntity = ModelEntity()
    private(set) var vertexCount = 0
    private(set) var triangleCount = 0
    private(set) var appliedPose: GripHandPose?
    private(set) var appliedVertexColors: [SIMD4<Float>] = []

    private let asset: GripHandAsset
    private let material: CustomMaterial
    private struct BuiltMesh {
        let resource: MeshResource
        let vertexColors: [SIMD4<Float>]
    }

    private var meshes: [MeshKey: BuiltMesh] = [:]
    private var recentKeys: [MeshKey] = []
    private var currentAction = "Neutral"

    init(asset: GripHandAsset) throws {
        self.asset = asset
        var base = PhysicallyBasedMaterial()
        base.baseColor = .init(tint: .white)
        base.roughness = .init(floatLiteral: 0.9)
        base.metallic = .init(floatLiteral: 0)
        base.faceCulling = .none
        guard let device = MTLCreateSystemDefaultDevice(),
              let library = device.makeDefaultLibrary() else {
            throw GripHandAsset.AssetError.invalidMesh
        }
        let shader = CustomMaterial.SurfaceShader(named: "gripHandSurfaceShader", in: library)
        var material = try CustomMaterial(from: base, surfaceShader: shader)
        material.faceCulling = .none
        self.material = material
        root.addChild(modelEntity)
    }

    func apply(_ pose: GripHandPose) throws {
        let key = MeshKey(action: pose.action(), fingers: pose.highlightedFingers)
        guard asset.poses[key.action] != nil else { throw GripHandAsset.AssetError.invalidMesh }
        let builtMesh: BuiltMesh
        if let cached = meshes[key] {
            builtMesh = cached
        } else {
            builtMesh = try makeMesh(for: key, pose: pose)
            meshes[key] = builtMesh
        }
        recentKeys.removeAll { $0 == key }
        recentKeys.append(key)
        while recentKeys.count > 3 {
            meshes.removeValue(forKey: recentKeys.removeFirst())
        }
        modelEntity.model = ModelComponent(mesh: builtMesh.resource, materials: [material])
        currentAction = key.action
        appliedPose = pose
        appliedVertexColors = builtMesh.vertexColors
        vertexCount = asset.vertexCount
        triangleCount = asset.indices.count / 3
    }

    /// Frame the exact displayed surface, including the source's short wrist.
    func posedVerticesForFraming() -> [SIMD3<Float>] {
        guard let positions = asset.poses[currentAction]?.positions else { return [] }
        return stride(from: 0, to: positions.count, by: 3).map {
            SIMD3(positions[$0], positions[$0 + 1], positions[$0 + 2])
        }
    }

    private func makeMesh(for key: MeshKey, pose: GripHandPose) throws -> BuiltMesh {
        let source = asset.poses[key.action]!
        let colors = try GripHandRealityMeshBuilder.vertexColors(
            asset: asset, action: pose, selectedFingers: key.fingers
        )
        let vertices = (0..<asset.vertexCount).map { i in
            Vertex(position: SIMD3(source.positions[i * 3], source.positions[i * 3 + 1], source.positions[i * 3 + 2]),
                   normal: SIMD3(source.normals[i * 3], source.normals[i * 3 + 1], source.normals[i * 3 + 2]),
                   color: colors[i])
        }
        let bounds = vertices.reduce(BoundingBox.empty) { box, vertex in
            BoundingBox(min: simd_min(box.min, vertex.position), max: simd_max(box.max, vertex.position))
        }
        let descriptor = LowLevelMesh.Descriptor(
            vertexCapacity: vertices.count,
            vertexAttributes: [
                .init(semantic: .position, format: .float3, offset: MemoryLayout<Vertex>.offset(of: \.position)!),
                .init(semantic: .normal, format: .float3, offset: MemoryLayout<Vertex>.offset(of: \.normal)!),
                .init(semantic: .color, format: .float4, offset: MemoryLayout<Vertex>.offset(of: \.color)!)
            ],
            vertexLayouts: [.init(bufferIndex: 0, bufferStride: MemoryLayout<Vertex>.stride)],
            indexCapacity: asset.indices.count
        )
        let lowLevelMesh = try LowLevelMesh(descriptor: descriptor)
        lowLevelMesh.withUnsafeMutableBytes(bufferIndex: 0) { destination in
            vertices.withUnsafeBytes { source in destination.copyBytes(from: source) }
        }
        lowLevelMesh.withUnsafeMutableIndices { destination in
            asset.indices.withUnsafeBytes { source in destination.copyBytes(from: source) }
        }
        lowLevelMesh.parts.append(.init(indexCount: asset.indices.count, bounds: bounds))
        return BuiltMesh(resource: try MeshResource(from: lowLevelMesh), vertexColors: colors)
    }
}

#if DEBUG
/// Diagnostic framing adaptation from the unchanged authored 3D vertices.
/// The result is fixed until the existing pose/viewport/reset path runs again.
@MainActor
private func gripHandDiagnosticFieldOfView(points: [SIMD4<Float>],
                                           cameraTransform: simd_float4x4,
                                           aspect: Float) -> Float? {
    guard !points.isEmpty, aspect.isFinite, aspect > 0 else { return nil }
    let inverse = simd_inverse(cameraTransform)
    var tangent: Float = 0
    for point in points {
        let projected = inverse * point
        let depth = -projected.z
        guard projected.x.isFinite, projected.y.isFinite, depth.isFinite,
              depth > 0.1, depth < 100 else { return nil }
        tangent = max(tangent, abs(projected.y) / depth,
                      abs(projected.x) / (aspect * depth))
    }
    tangent *= 1.08
    let degrees = 2 * atan(tangent) * 180 / Float.pi
    guard tangent.isFinite, tangent > 0, degrees.isFinite,
          degrees > 0, degrees < 180 else { return nil }
    return degrees
}
#endif

@MainActor
final class GripHandRealityScene {
    #if DEBUG
    let diagnosticHandLifetimeToken = UUID()
    #endif
    let root = Entity()
    let hand = Entity()
    let camera = Entity()
    private let keyLight = Entity()
    private let fillLight = Entity()
    private(set) var isUnavailable = false

    private var surface: GripHandRealitySurface?
    private(set) var currentPose: GripHandPose?
    private var currentSide: GripCueSide?
    private var currentViewportSize: CGSize = .zero
    private var currentResetToken: Int?
    private var canonicalCenter = SIMD3<Float>.zero
    private var canonicalOffset = SIMD3<Float>(0, 0, 1)
    private var canonicalOrthographicScale: Float = 1
    private var orbitAzimuth: Float = 0
    private var orbitElevation: Float = 0
    private var orbitZoom: Float = 1
    init(assetResult: Result<GripHandAsset, Error> = GripHandAsset.bundled) {
        #if DEBUG
        if BoardHighlightDiagnostic.isEnabled {
            BoardHighlightDiagnostic.shared.handLifecycle(kind: "single",
                event: "constructor-entry", root: root, camera: camera,
                lifetime: diagnosticHandLifetimeToken)
        }
        #endif
        root.addChild(hand)
        #if DEBUG
        if BoardHighlightDiagnostic.usesPerspectiveHandCameras {
            // Explicit diagnostic placeholder; the first valid reset fits the vertices.
            camera.components.set(PerspectiveCameraComponent(near: 0.1, far: 100,
                fieldOfViewInDegrees: 60, fieldOfViewOrientation: .vertical))
        } else {
            var orthographicCamera = OrthographicCameraComponent()
            orthographicCamera.near = 0.1
            orthographicCamera.far = 100
            orthographicCamera.scale = 3.2
            orthographicCamera.scaleDirection = .vertical
            camera.components.set(orthographicCamera)
        }
        #else
        var orthographicCamera = OrthographicCameraComponent()
        orthographicCamera.near = 0.1
        orthographicCamera.far = 100
        orthographicCamera.scale = 3.2
        orthographicCamera.scaleDirection = .vertical
        camera.components.set(orthographicCamera)
        #endif
        #if DEBUG
        if BoardHighlightDiagnostic.isEnabled {
            BoardHighlightDiagnostic.shared.handCamera(kind: "single",
                event: "configured", camera: camera, lifetime: diagnosticHandLifetimeToken)
        }
        #endif
        root.addChild(camera)

        root.addChild(keyLight)
        root.addChild(fillLight)
        orientLights(for: .right)

        do {
            let asset = try assetResult.get()
            let surface = try GripHandRealitySurface(asset: asset)
            hand.addChild(surface.root)
            self.surface = surface
        } catch {
            isUnavailable = true
        }
    }

    func update(pose: GripHandPose, side: GripCueSide, viewportSize: CGSize, resetToken: Int) {
        let poseChanged = currentPose != pose
        let sideChanged = currentSide != side
        let viewportChanged = currentViewportSize != viewportSize
        if poseChanged {
            do {
                try surface?.apply(pose)
            } catch {
                surface?.root.removeFromParent()
                surface = nil
                isUnavailable = true
            }
        }
        if sideChanged {
            hand.scale.x = side == .left ? -1 : 1
            orientLights(for: side)
        }
        let needsReset = poseChanged || sideChanged || viewportChanged || currentResetToken != resetToken
        currentPose = pose
        currentSide = side
        currentViewportSize = viewportSize
        currentResetToken = resetToken
        if needsReset { resetCamera() }
    }

    func resetCamera() {
        guard let surface else { return }
        let points = surface.posedVerticesForFraming().map { point in
            SIMD4<Float>(point.x * hand.scale.x, point.y, point.z, 1)
        }
        guard !points.isEmpty else { return }
        var low = SIMD3<Float>(repeating: .greatestFiniteMagnitude)
        var high = SIMD3<Float>(repeating: -.greatestFiniteMagnitude)
        for point in points {
            let xyz = SIMD3<Float>(point.x, point.y, point.z)
            low = simd_min(low, xyz)
            high = simd_max(high, xyz)
        }
        let center = (low + high) / 2
        let offset = SIMD3<Float>(currentSide == .left ? 5.8 : -5.8, 2.75, 9.4)
        guard let transform = Self.cameraTransform(position: center + offset, target: center) else { return }
        let inverseCamera = simd_inverse(transform)
        var halfWidth: Float = 0
        var halfHeight: Float = 0
        for point in points {
            let projected = inverseCamera * point
            halfWidth = max(halfWidth, abs(projected.x))
            halfHeight = max(halfHeight, abs(projected.y))
        }
        let size = currentViewportSize
        let aspect = size.width.isFinite && size.height.isFinite && size.width > 0 && size.height > 0
            ? Float(size.width / size.height) : 0.85
        guard aspect.isFinite, aspect > 0 else { return }
        let orthographicScale = max(halfHeight, halfWidth / aspect) * 1.08
        guard orthographicScale.isFinite, orthographicScale > 0 else { return }
        #if DEBUG
        if BoardHighlightDiagnostic.usesPerspectiveHandCameras {
            guard let degrees = gripHandDiagnosticFieldOfView(points: points,
                    cameraTransform: transform, aspect: aspect),
                  var component = camera.components[PerspectiveCameraComponent.self] else {
                BoardHighlightDiagnostic.shared.handCamera(kind: "single",
                    event: "fit-rejected", camera: camera, lifetime: diagnosticHandLifetimeToken, points: points)
                return
            }
            camera.transform = Transform(matrix: transform)
            component.fieldOfViewInDegrees = degrees
            camera.components.set(component)
        } else {
            camera.transform = Transform(matrix: transform)
            var component = camera.components[OrthographicCameraComponent.self]!
            component.scale = orthographicScale
            camera.components.set(component)
        }
        #else
        camera.transform = Transform(matrix: transform)
        var component = camera.components[OrthographicCameraComponent.self]!
        component.scale = orthographicScale
        camera.components.set(component)
        #endif
        #if DEBUG
        if BoardHighlightDiagnostic.isEnabled {
            BoardHighlightDiagnostic.shared.handCamera(kind: "single",
                event: "reset-fitted", camera: camera, lifetime: diagnosticHandLifetimeToken, points: points)
        }
        #endif

        canonicalCenter = center
        canonicalOffset = offset
        canonicalOrthographicScale = orthographicScale
        orbitAzimuth = 0
        orbitElevation = 0
        orbitZoom = 1
    }

    func orbit(azimuthDelta: Float, elevationDelta: Float, zoomScale: Float = 1) {
        guard azimuthDelta.isFinite, elevationDelta.isFinite,
              zoomScale.isFinite, zoomScale > 0 else { return }
        let fullRotation: Float = .pi * 2
        let nextAzimuth = (orbitAzimuth + azimuthDelta).truncatingRemainder(dividingBy: fullRotation)
        let nextElevation = min(max(orbitElevation + elevationDelta, -0.55), 0.55)
        let nextZoom = min(max(orbitZoom * zoomScale, 0.75), 1.35)
        let baseDistance = simd_length(canonicalOffset)
        guard baseDistance > 1e-6 else { return }
        let baseDirection = canonicalOffset / baseDistance
        let worldUp = SIMD3<Float>(0, 1, 0)
        let rightVector = simd_cross(worldUp, baseDirection)
        guard simd_length(rightVector) > 1e-6 else { return }
        let right = simd_normalize(rightVector)

        let yaw = simd_quatf(angle: nextAzimuth, axis: worldUp)
        let pitch = simd_quatf(angle: nextElevation, axis: right)
        let distance = baseDistance / nextZoom
        guard distance.isFinite, distance > 0 else { return }
        let rotatedOffset = (pitch * yaw).act(baseDirection) * distance
        guard rotatedOffset.x.isFinite, rotatedOffset.y.isFinite, rotatedOffset.z.isFinite,
              let transform = Self.cameraTransform(position: canonicalCenter + rotatedOffset,
                                                   target: canonicalCenter) else { return }
        camera.transform = Transform(matrix: transform)
        #if DEBUG
        if !BoardHighlightDiagnostic.usesPerspectiveHandCameras {
            var component = camera.components[OrthographicCameraComponent.self]!
            component.scale = canonicalOrthographicScale / nextZoom
            camera.components.set(component)
        }
        #else
        var component = camera.components[OrthographicCameraComponent.self]!
        component.scale = canonicalOrthographicScale / nextZoom
        camera.components.set(component)
        #endif
        orbitAzimuth = nextAzimuth
        orbitElevation = nextElevation
        orbitZoom = nextZoom
    }

    private static func cameraTransform(position: SIMD3<Float>, target: SIMD3<Float>) -> simd_float4x4? {
        let direction = target - position
        let length = simd_length(direction)
        guard length.isFinite, length > 1e-6 else { return nil }
        let forward = direction / length
        let worldUp = SIMD3<Float>(0, 1, 0)
        let rightVector = simd_cross(forward, worldUp)
        let rightLength = simd_length(rightVector)
        guard rightLength.isFinite, rightLength > 1e-6 else { return nil }
        let right = rightVector / rightLength
        let up = simd_cross(right, forward)
        var transform = matrix_identity_float4x4
        transform.columns.0 = SIMD4<Float>(right.x, right.y, right.z, 0)
        transform.columns.1 = SIMD4<Float>(up.x, up.y, up.z, 0)
        transform.columns.2 = SIMD4<Float>(-forward.x, -forward.y, -forward.z, 0)
        transform.columns.3 = SIMD4<Float>(position.x, position.y, position.z, 1)
        return transform
    }

    private func orientLights(for side: GripCueSide) {
        // Both cameras look from positive Z. Mirror the lights on X with the
        // hand so each key stays beside its camera and in front of the palm.
        let lateral: Float = side == .left ? 1 : -1
        keyLight.components.set(DirectionalLightComponent(
            color: .white, intensity: side == .left ? 4_500 : 2_800
        ))
        fillLight.components.set(DirectionalLightComponent(
            color: .white, intensity: side == .left ? 4_000 : 250
        ))
        keyLight.look(at: .zero, from: SIMD3(lateral * 5.8, 8, 7), relativeTo: root)
        fillLight.look(at: .zero, from: SIMD3(-lateral * 2, 2, -5), relativeTo: root)
    }
}

/// One renderer and one camera for a pair of mirrored hands. Keeping both
/// meshes in the same RealityView prevents sibling renderers from displaying
/// different frames after a synchronized pose update.
@MainActor
final class GripHandRealityPairScene {
    #if DEBUG
    let diagnosticHandLifetimeToken = UUID()
    #endif
    let root = Entity()
    let camera = Entity()
    let leftHand = Entity()
    let rightHand = Entity()
    private let keyLight = Entity()
    private let fillLight = Entity()
    private(set) var leftSurface: GripHandRealitySurface?
    private(set) var rightSurface: GripHandRealitySurface?
    private(set) var isAvailable = false
    private(set) var currentPose: GripHandPose?
    private(set) var currentViewportSize: CGSize = .zero
    private(set) var currentResetToken: Int?

    private let slotOffset: Float = 0.82
    private var canonicalCenter = SIMD3<Float>.zero
    private var canonicalOffset = SIMD3<Float>(0, 0, 1)
    private var canonicalOrthographicScale: Float = 1
    private var orbitAzimuth: Float = 0
    private var orbitElevation: Float = 0
    private var orbitZoom: Float = 1

    init(assetResult: Result<GripHandAsset, Error> = GripHandAsset.bundled) {
        #if DEBUG
        if BoardHighlightDiagnostic.isEnabled {
            BoardHighlightDiagnostic.shared.handLifecycle(kind: "pair",
                event: "constructor-entry", root: root, camera: camera,
                lifetime: diagnosticHandLifetimeToken)
        }
        #endif
        root.addChild(leftHand)
        root.addChild(rightHand)
        leftHand.position.x = -slotOffset
        rightHand.position.x = slotOffset
        leftHand.scale.x = -1
        #if DEBUG
        if BoardHighlightDiagnostic.usesPerspectiveHandCameras {
            // Explicit diagnostic placeholder; the first valid reset fits the vertices.
            camera.components.set(PerspectiveCameraComponent(near: 0.1, far: 100,
                fieldOfViewInDegrees: 60, fieldOfViewOrientation: .vertical))
        } else {
            var orthographicCamera = OrthographicCameraComponent()
            orthographicCamera.near = 0.1
            orthographicCamera.far = 100
            orthographicCamera.scale = 3.2
            orthographicCamera.scaleDirection = .vertical
            camera.components.set(orthographicCamera)
        }
        #else
        var orthographicCamera = OrthographicCameraComponent()
        orthographicCamera.near = 0.1
        orthographicCamera.far = 100
        orthographicCamera.scale = 3.2
        orthographicCamera.scaleDirection = .vertical
        camera.components.set(orthographicCamera)
        #endif
        #if DEBUG
        if BoardHighlightDiagnostic.isEnabled {
            BoardHighlightDiagnostic.shared.handCamera(kind: "pair",
                event: "configured", camera: camera, lifetime: diagnosticHandLifetimeToken)
        }
        #endif
        root.addChild(camera)
        root.addChild(keyLight)
        root.addChild(fillLight)
        keyLight.components.set(DirectionalLightComponent(color: .white, intensity: 3_200))
        fillLight.components.set(DirectionalLightComponent(color: .white, intensity: 600))
        // Directional lights affect every entity, so the pair shares one centered rig.
        keyLight.look(at: .zero, from: SIMD3(0, 8, 7), relativeTo: root)
        fillLight.look(at: .zero, from: SIMD3(0, 2, -5), relativeTo: root)

        do {
            let asset = try assetResult.get()
            let left = try GripHandRealitySurface(asset: asset)
            let right = try GripHandRealitySurface(asset: asset)
            leftHand.addChild(left.root)
            rightHand.addChild(right.root)
            leftSurface = left
            rightSurface = right
            isAvailable = true
        } catch {
            isAvailable = false
        }
    }

    func update(pose: GripHandPose, viewportSize: CGSize, resetToken: Int) {
        let poseChanged = currentPose != pose
        let viewportChanged = currentViewportSize != viewportSize
        if poseChanged {
            do {
                try leftSurface?.apply(pose)
                try rightSurface?.apply(pose)
            } catch {
                if let leftSurface { leftHand.removeChild(leftSurface.root) }
                if let rightSurface { rightHand.removeChild(rightSurface.root) }
                leftSurface = nil
                rightSurface = nil
                isAvailable = false
            }
        }
        let needsReset = poseChanged || viewportChanged || currentResetToken != resetToken
        currentPose = pose
        currentViewportSize = viewportSize
        currentResetToken = resetToken
        if needsReset { resetCamera() }
    }

    func resetCamera() {
        guard let leftSurface, let rightSurface else { return }
        let points = framedPoints(for: leftSurface, under: leftHand)
            + framedPoints(for: rightSurface, under: rightHand)
        guard !points.isEmpty else { return }
        var low = SIMD3<Float>(repeating: .greatestFiniteMagnitude)
        var high = SIMD3<Float>(repeating: -.greatestFiniteMagnitude)
        for point in points {
            let xyz = SIMD3<Float>(point.x, point.y, point.z)
            low = simd_min(low, xyz)
            high = simd_max(high, xyz)
        }
        let center = (low + high) / 2
        // Shared frontal oblique camera frames the union, leaving room for both hands.
        let offset = SIMD3<Float>(0, 2.75, 9.4)
        guard let transform = Self.cameraTransform(position: center + offset, target: center) else { return }
        let inverseCamera = simd_inverse(transform)
        var halfWidth: Float = 0
        var halfHeight: Float = 0
        for point in points {
            let projected = inverseCamera * point
            halfWidth = max(halfWidth, abs(projected.x))
            halfHeight = max(halfHeight, abs(projected.y))
        }
        let size = currentViewportSize
        let aspect = size.width.isFinite && size.height.isFinite && size.width > 0 && size.height > 0
            ? Float(size.width / size.height) : 0.85
        guard aspect.isFinite, aspect > 0 else { return }
        let scale = max(halfHeight, halfWidth / aspect) * 1.08
        guard scale.isFinite, scale > 0 else { return }
        #if DEBUG
        if BoardHighlightDiagnostic.usesPerspectiveHandCameras {
            guard let degrees = gripHandDiagnosticFieldOfView(points: points,
                    cameraTransform: transform, aspect: aspect),
                  var component = camera.components[PerspectiveCameraComponent.self] else {
                BoardHighlightDiagnostic.shared.handCamera(kind: "pair",
                    event: "fit-rejected", camera: camera, lifetime: diagnosticHandLifetimeToken, points: points)
                return
            }
            camera.transform = Transform(matrix: transform)
            component.fieldOfViewInDegrees = degrees
            camera.components.set(component)
        } else {
            camera.transform = Transform(matrix: transform)
            var component = camera.components[OrthographicCameraComponent.self]!
            component.scale = scale
            camera.components.set(component)
        }
        #else
        camera.transform = Transform(matrix: transform)
        var component = camera.components[OrthographicCameraComponent.self]!
        component.scale = scale
        camera.components.set(component)
        #endif
        #if DEBUG
        if BoardHighlightDiagnostic.isEnabled {
            BoardHighlightDiagnostic.shared.handCamera(kind: "pair",
                event: "reset-fitted", camera: camera, lifetime: diagnosticHandLifetimeToken, points: points)
        }
        #endif
        canonicalCenter = center
        canonicalOffset = offset
        canonicalOrthographicScale = scale
        orbitAzimuth = 0
        orbitElevation = 0
        orbitZoom = 1
    }

    func orbit(azimuthDelta: Float, elevationDelta: Float, zoomScale: Float = 1) {
        guard azimuthDelta.isFinite, elevationDelta.isFinite,
              zoomScale.isFinite, zoomScale > 0 else { return }
        let nextAzimuth = (orbitAzimuth + azimuthDelta).truncatingRemainder(dividingBy: .pi * 2)
        let nextElevation = min(max(orbitElevation + elevationDelta, -0.55), 0.55)
        let nextZoom = min(max(orbitZoom * zoomScale, 0.75), 1.35)
        let distance = simd_length(canonicalOffset)
        guard distance.isFinite, distance > 1e-6 else { return }
        let direction = canonicalOffset / distance
        let up = SIMD3<Float>(0, 1, 0)
        let rightVector = simd_cross(up, direction)
        guard simd_length(rightVector) > 1e-6 else { return }
        let yaw = simd_quatf(angle: nextAzimuth, axis: up)
        let pitch = simd_quatf(angle: nextElevation, axis: simd_normalize(rightVector))
        let rotatedOffset = (pitch * yaw).act(direction) * (distance / nextZoom)
        guard let transform = Self.cameraTransform(position: canonicalCenter + rotatedOffset,
                                                   target: canonicalCenter) else { return }
        camera.transform = Transform(matrix: transform)
        #if DEBUG
        if !BoardHighlightDiagnostic.usesPerspectiveHandCameras {
            var component = camera.components[OrthographicCameraComponent.self]!
            component.scale = canonicalOrthographicScale / nextZoom
            camera.components.set(component)
        }
        #else
        var component = camera.components[OrthographicCameraComponent.self]!
        component.scale = canonicalOrthographicScale / nextZoom
        camera.components.set(component)
        #endif
        orbitAzimuth = nextAzimuth
        orbitElevation = nextElevation
        orbitZoom = nextZoom
    }

    private func framedPoints(for surface: GripHandRealitySurface, under hand: Entity) -> [SIMD4<Float>] {
        surface.posedVerticesForFraming().map { hand.transform.matrix * SIMD4<Float>($0, 1) }
    }

    private static func cameraTransform(position: SIMD3<Float>, target: SIMD3<Float>) -> simd_float4x4? {
        let direction = target - position
        let length = simd_length(direction)
        guard length.isFinite, length > 1e-6 else { return nil }
        let forward = direction / length
        let rightVector = simd_cross(forward, SIMD3<Float>(0, 1, 0))
        let rightLength = simd_length(rightVector)
        guard rightLength.isFinite, rightLength > 1e-6 else { return nil }
        let right = rightVector / rightLength
        let up = simd_cross(right, forward)
        var transform = matrix_identity_float4x4
        transform.columns.0 = SIMD4<Float>(right.x, right.y, right.z, 0)
        transform.columns.1 = SIMD4<Float>(up.x, up.y, up.z, 0)
        transform.columns.2 = SIMD4<Float>(-forward.x, -forward.y, -forward.z, 0)
        transform.columns.3 = SIMD4<Float>(position.x, position.y, position.z, 1)
        return transform
    }
}

@MainActor
private final class GripHandPairSceneStorage {
    private let makeScene: @MainActor () -> GripHandRealityPairScene
    lazy var scene = makeScene()

    init(makeScene: @escaping @MainActor () -> GripHandRealityPairScene = { GripHandRealityPairScene() }) {
        self.makeScene = makeScene
    }
}

/// Shared RealityView host for layouts that display both mirrored hands.
@MainActor
struct GripHandPairModelView: View {
    let posture: GripType?
    let fingerConfiguration: FingerConfiguration?
    let resetToken: Int
    @State private var sceneStorage: GripHandPairSceneStorage
    @State private var isUnavailable: Bool
    @State private var dragState = GripHandDragState()
    @State private var lastMagnification: CGFloat = 1
    @State private var cameraRevision = 0
    #if DEBUG
    @State private var diagnosticHandViewToken = UUID()
    @Environment(\.workoutDiagnosticIsPrestart) private var diagnosticIsPrestart
    #endif

    private var scene: GripHandRealityPairScene { sceneStorage.scene }

    init(posture: GripType?, fingerConfiguration: FingerConfiguration?, resetToken: Int = 0) {
        self.posture = posture
        self.fingerConfiguration = fingerConfiguration
        self.resetToken = resetToken
        _sceneStorage = State(initialValue: GripHandPairSceneStorage())
        _isUnavailable = State(initialValue: false)
    }

    init(posture: GripType?, fingerConfiguration: FingerConfiguration?, resetToken: Int = 0,
         scene: GripHandRealityPairScene) {
        self.posture = posture
        self.fingerConfiguration = fingerConfiguration
        self.resetToken = resetToken
        _sceneStorage = State(initialValue: GripHandPairSceneStorage(makeScene: { scene }))
        _isUnavailable = State(initialValue: !scene.isAvailable)
    }

    var body: some View {
        #if DEBUG
        if BoardHighlightDiagnostic.suppressesAllHandHosts
            || (WorkoutPrestartHandDiagnostic.isEnabled && diagnosticIsPrestart) {
            Color.clear
                .frame(maxWidth: .infinity, maxHeight: .infinity)
                .allowsHitTesting(false)
                .accessibilityHidden(true)
        } else if HandImagePrototype.enabled {
            HandImagePrototypeView(pose: GripHandPose(posture: posture, fingerConfiguration: fingerConfiguration),
                                   reset: resetToken,
                                   makeScene: { [sceneStorage] in .pair(sceneStorage.scene) })
        } else {
            handContent
        }
        #else
        handContent
        #endif
    }

    private var handContent: some View {
        let _ = cameraRevision
        return GeometryReader { proxy in
            let size = proxy.size
            RealityView { content in
                #if DEBUG
                if BoardHighlightDiagnostic.isEnabled {
                    BoardHighlightDiagnostic.shared.handLifecycle(kind: "pair",
                        event: "make-entry", root: scene.root, camera: scene.camera,
                        lifetime: scene.diagnosticHandLifetimeToken, view: diagnosticHandViewToken)
                }
                #endif
                content.camera = .virtual
                content.add(scene.root)
                syncScene(in: size)
                updateUnavailableState()
            } update: { _ in
                syncScene(in: size)
                updateUnavailableState()
            }
            .simultaneousGesture(orbitGesture(size: size))
            .simultaneousGesture(magnifyGesture)
            .overlay {
                if isUnavailable {
                    Text("3D hands unavailable")
                        .font(.caption2)
                        .foregroundStyle(.secondary)
                        .multilineTextAlignment(.center)
                        .frame(maxWidth: .infinity, maxHeight: .infinity)
                        .accessibilityHidden(true)
                }
            }
            #if DEBUG
            .onAppear { [viewToken = diagnosticHandViewToken] in
                if BoardHighlightDiagnostic.recordsHandLifetimes {
                    BoardHighlightDiagnostic.shared.handViewLifecycle(view: viewToken, event: "appeared")
                }
            }
            .onDisappear { [viewToken = diagnosticHandViewToken] in
                if BoardHighlightDiagnostic.recordsHandLifetimes {
                    BoardHighlightDiagnostic.shared.handViewLifecycle(view: viewToken, event: "disappeared")
                }
            }
            #endif
            .accessibilityHidden(true)
        }
    }

    func syncScene(in size: CGSize) {
        scene.update(pose: GripHandPose(posture: posture, fingerConfiguration: fingerConfiguration),
                     viewportSize: size, resetToken: resetToken)
    }

    private func updateUnavailableState() {
        let unavailable = !scene.isAvailable
        guard unavailable != isUnavailable else { return }
        Task { @MainActor in isUnavailable = unavailable }
    }

    private func orbitGesture(size: CGSize) -> some Gesture {
        DragGesture(minimumDistance: OrbitPanArbitration.activationDistance)
            .onChanged { value in
                guard let delta = dragState.advance(translation: value.translation,
                                                    velocity: value.velocity) else { return }
                scene.orbit(azimuthDelta: Float(-delta.width / max(size.width, 1)) * 0.9,
                            elevationDelta: Float(-delta.height / max(size.height, 1)) * 0.65)
                cameraRevision &+= 1
            }
            .onEnded { _ in dragState.reset() }
    }

    private var magnifyGesture: some Gesture {
        MagnificationGesture()
            .onChanged { value in
                let ratio = value / max(lastMagnification, 0.001)
                lastMagnification = value
                scene.orbit(azimuthDelta: 0, elevationDelta: 0, zoomScale: Float(ratio))
                cameraRevision &+= 1
            }
            .onEnded { _ in lastMagnification = 1 }
    }
}

struct GripHandModelInspector: View {
    let posture: GripType?
    let fingerConfiguration: FingerConfiguration?
    let side: GripCueSide
    @Environment(\.dismiss) private var dismiss
    @State private var resetToken = 0

    var body: some View {
        NavigationStack {
            GeometryReader { geometry in
                if geometry.size.width > geometry.size.height {
                    HStack(spacing: 24) {
                        model
                        controls.frame(width: min(260, geometry.size.width * 0.34))
                    }
                } else {
                    VStack(spacing: 16) {
                        model
                        controls
                    }
                }
            }
            .padding(20)
            .background(Color.hangCream)
            .navigationTitle(posture?.label ?? "Grip not specified")
            .navigationBarTitleDisplayMode(.inline)
            .toolbar {
                ToolbarItem(placement: .confirmationAction) {
                    Button("Done") { dismiss() }
                }
            }
        }
    }

    private var model: some View {
        GripHandModelView(posture: posture, fingerConfiguration: fingerConfiguration,
                          side: side, resetToken: resetToken)
            .frame(maxWidth: .infinity, maxHeight: .infinity)
            .accessibilityLabel("Rotatable 3D \(side.accessibilityIdentifier) hand")
    }

    private var controls: some View {
        VStack(spacing: 16) {
            Text(fingerConfiguration.map { "Highlighted: " + $0.orderedFingers.map(\.rawValue).joined(separator: ", ") }
                 ?? "Fingers not specified")
                .font(.subheadline.weight(.semibold))
                .foregroundStyle(Color.hangInk)
            Text("Drag to rotate · Pinch to zoom")
                .font(.footnote)
                .foregroundStyle(Color.hangMuted)
            Button("Reset view") { resetToken += 1 }
                .buttonStyle(.bordered)
                .accessibilityIdentifier("gripModel.reset")
            Text("Schematic grip illustration")
                .font(.caption2)
                .foregroundStyle(Color.hangMuted)
        }
        .multilineTextAlignment(.center)
    }
}

#if DEBUG
/// Isolated visual QA; choices here never modify a workout or its prescriptions.
struct GripHandModelReviewView: View {
    @State private var posture: GripType = .halfCrimp
    @State private var fingers: Set<FingerSlot> = [.index, .middle, .ring, .pinky]
    @State private var resetToken = 0

    var body: some View {
        NavigationStack {
            VStack(spacing: 12) {
                Picker("Grip", selection: $posture) {
                    ForEach(GripType.allCases) { Text($0.label).tag($0) }
                }
                .pickerStyle(.menu)
                HStack {
                    ForEach(FingerSlot.allCases) { finger in
                        Button(finger.rawValue.capitalized) {
                            if fingers.contains(finger) { fingers.remove(finger) }
                            else { fingers.insert(finger) }
                        }
                        .buttonStyle(.bordered)
                        .tint(fingers.contains(finger) ? Color.holdActiveDeep : Color.hangMuted)
                    }
                }
                GripHandPairModelView(posture: posture, fingerConfiguration: configuration,
                                      resetToken: resetToken)
                Text(fingers.isEmpty ? "Fingers not specified" : "Highlighted: " + FingerSlot.allCases.filter(fingers.contains).map(\.rawValue).joined(separator: ", "))
                    .font(.caption)
                Button("Reset view") { resetToken += 1 }
                Text("Drag to rotate · Pinch to zoom")
                    .font(.caption)
            }
            .padding()
            .background(ProcessInfo.processInfo.environment["HANGTEN_REVIEW_HAND_IMAGE_DARK_BACKGROUND"] == "1"
                        ? Color.black : Color.hangCream)
            .navigationTitle("3D hand review")
        }
        .onAppear {
            let environment = ProcessInfo.processInfo.environment
            if let requested = environment["HANGTEN_REVIEW_GRIP_POSE"].flatMap(GripType.init(rawValue:)) { posture = requested }
            if let requested = environment["HANGTEN_REVIEW_GRIP_FINGERS"] {
                fingers = Set(requested.split(separator: ",").compactMap { FingerSlot(rawValue: String($0)) })
            }
        }
    }

    private var configuration: FingerConfiguration? { FingerConfiguration(engagedFingers: fingers) }
}
#endif

#if DEBUG
// Throwaway, launch-gated RealityRenderer feasibility probe. No live UIView host.
@MainActor
private enum HandImagePrototype {
    static let enabled = BoardHighlightDiagnostic.isEnabled
        && ProcessInfo.processInfo.environment["HANGTEN_REVIEW_HAND_IMAGE"] == "1"
}

@MainActor
private enum HandImageScene {
    case single(GripHandRealityScene)
    case pair(GripHandRealityPairScene)
    var root: Entity { switch self { case .single(let s): s.root; case .pair(let s): s.root } }
    var camera: Entity { switch self { case .single(let s): s.camera; case .pair(let s): s.camera } }
    var kind: String { switch self { case .single: "single"; case .pair: "pair" } }
    var available: Bool { switch self { case .single(let s): !s.isUnavailable; case .pair(let s): s.isAvailable } }
    func configure(_ input: HandImageInput, orbit: SIMD3<Float>) {
        switch self {
        case .single(let s):
            s.update(pose: input.pose, side: input.side, viewportSize: input.size, resetToken: input.reset)
            s.resetCamera()
            s.orbit(azimuthDelta: orbit.x, elevationDelta: orbit.y, zoomScale: orbit.z)
        case .pair(let s):
            s.update(pose: input.pose, viewportSize: input.size, resetToken: input.reset)
            s.resetCamera()
            s.orbit(azimuthDelta: orbit.x, elevationDelta: orbit.y, zoomScale: orbit.z)
        }
    }
}

private struct HandImageInput: Equatable {
    let pose: GripHandPose
    let side: GripCueSide
    let size: CGSize
    let displayScale: CGFloat
    let reset: Int
}

@MainActor
private final class HandImageCoordinator: ObservableObject {
    @Published private(set) var image: UIImage?
    @Published private(set) var unavailable = false
    private let makeScene: @MainActor () -> HandImageScene
    private let session = UUID()
    private var scene: HandImageScene?
    private var renderer: RealityRenderer?
    private var device: (any MTLDevice)?
    private var context: CIContext?
    private var input: HandImageInput?
    private var orbit = SIMD3<Float>(0, 0, 1)
    private var revision = 0
    private var active = false
    private var failed = false
    private var pending: Request?
    private var inFlight: Frame?
    private var publishedCount = 0
    private struct Request {
        let revision: Int
        let input: HandImageInput
        let orbit: SIMD3<Float>
    }
    // Strong ownership lasts through the documented GPU-completion callback AND
    // eager Core Image materialization. Only MainActor reads/mutates this frame.
    @MainActor
    private final class Frame {
        let request: Request
        let scene: HandImageScene
        let renderer: RealityRenderer
        let texture: any MTLTexture
        let output: RealityRenderer.CameraOutput
        init(request: Request, scene: HandImageScene, renderer: RealityRenderer,
             texture: any MTLTexture, output: RealityRenderer.CameraOutput) {
            self.request = request; self.scene = scene; self.renderer = renderer
            self.texture = texture; self.output = output
        }
    }
    init(makeScene: @escaping @MainActor () -> HandImageScene) { self.makeScene = makeScene }

    func submit(_ next: HandImageInput) {
        guard !failed else { return }
        active = true
        if input != next { orbit = SIMD3<Float>(0, 0, 1) }
        input = next
        enqueue()
    }
    func orbitBy(azimuth: Float, elevation: Float, zoom: Float = 1) {
        guard active, !failed, azimuth.isFinite, elevation.isFinite, zoom.isFinite, zoom > 0 else { return }
        // Same per-gesture accumulation and clamps as both existing scene.orbit methods.
        orbit.x = (orbit.x + azimuth).truncatingRemainder(dividingBy: .pi * 2)
        orbit.y = min(max(orbit.y + elevation, -0.55), 0.55)
        orbit.z = min(max(orbit.z * zoom, 0.75), 1.35)
        enqueue()
    }
    func disappear() {
        active = false; revision += 1; pending = nil; image = nil
        log("disappear", revision: revision)
        // No cancellation API. The submitted frame retains all resources until completion.
    }
    private func enqueue() {
        guard let input else { return }
        revision += 1
        pending = Request(revision: revision, input: input, orbit: orbit)
        image = nil // Never display a stale semantic/camera revision while awaiting the current one.
        // Strings preserve even nonfinite inputs without invalid JSON numbers.
        log("requested", revision: revision, extra: [
            "requestedViewport": [String(describing: input.size.width), String(describing: input.size.height)],
            "requestedDisplayScale": String(describing: input.displayScale)])
        drain()
    }
    private func drain() {
        guard active, !failed, inFlight == nil, let request = pending else { return }
        pending = nil
        do {
            let size = request.input.size, scale = request.input.displayScale
            guard size.width.isFinite, size.height.isFinite, scale.isFinite else {
                throw Failure.nonfiniteViewport
            }
            guard scale > 0 else { throw Failure.invalidDisplayScale }
            guard size.width >= 0, size.height >= 0 else { throw Failure.negativeViewport }
            guard size.width * scale <= 4096, size.height * scale <= 4096 else {
                throw Failure.oversizedViewport
            }
            guard size.width > 0, size.height > 0 else {
                log("waiting-for-viewport", revision: request.revision)
                // Consume this zero-geometry request without constructing the scene.
                // Only an ordinary input onChange/onAppear can submit a later request.
                return
            }
            if scene == nil { scene = makeScene() }
            guard let scene, scene.available else { throw Failure.sceneUnavailable }
            if renderer == nil {
                guard let device = MTLCreateSystemDefaultDevice() else { throw Failure.noMetalDevice }
                self.device = device
                context = CIContext(mtlDevice: device)
                let renderer = try RealityRenderer()
                renderer.entities.append(contentsOf: [scene.root])
                renderer.activeCamera = scene.camera
                renderer.cameraSettings.colorBackground = .color(CGColor(gray: 0, alpha: 0))
                renderer.extendedDynamicRangeOutput = false
                self.renderer = renderer
            }
            guard let renderer, let device else { throw Failure.noMetalDevice }
            // Scene mutation happens only while no previous render/conversion is in flight.
            scene.configure(request.input, orbit: request.orbit)
            let descriptor = MTLTextureDescriptor.texture2DDescriptor(
                pixelFormat: .bgra8Unorm_srgb,
                width: Int(ceil(size.width * scale)), height: Int(ceil(size.height * scale)),
                mipmapped: false)
            descriptor.usage = [.renderTarget, .shaderRead, .shaderWrite]
            descriptor.storageMode = .private
            guard let texture = device.makeTexture(descriptor: descriptor) else { throw Failure.noTexture }
            let output = try RealityRenderer.CameraOutput(.singleProjection(colorTexture: texture))
            let frame = Frame(request: request, scene: scene, renderer: renderer, texture: texture, output: output)
            inFlight = frame
            log("submitted", revision: request.revision, extra: [
                "kind": scene.kind, "rootID": String(describing: ObjectIdentifier(scene.root)),
                "cameraID": String(describing: ObjectIdentifier(scene.camera)),
                "orthographic": scene.camera.components[OrthographicCameraComponent.self] != nil,
                "perspective": scene.camera.components[PerspectiveCameraComponent.self] != nil,
                "viewport": [size.width, size.height], "displayScale": scale,
                "textureWidth": texture.width, "textureHeight": texture.height,
                "textureFormat": "bgra8Unorm_srgb", "toneMappingEnabled": renderer.cameraSettings.isToneMappingEnabled,
                "orientationConversion": "none; UIImage.up", "inputColorSpace": "sRGB"])
            let submittedRevision = request.revision
            try renderer.updateAndRender(deltaTime: 0, cameraOutput: output, onComplete: { [self] _ in
                let callbackUptime = ProcessInfo.processInfo.systemUptime
                let callbackEpoch = Date().timeIntervalSince1970
                Task { @MainActor in self.completed(revision: submittedRevision, callbackUptime: callbackUptime, callbackEpoch: callbackEpoch) }
            })
        } catch {
            // A throwing submission has not established a successful completion.
            // Keep a possibly submitted frame alive until coordinator teardown; fail closed.
            fail(error, revision: request.revision)
        }
    }
    private func completed(revision completedRevision: Int, callbackUptime: Double, callbackEpoch: Double) {
        guard let frame = inFlight, frame.request.revision == completedRevision else { return }
        log("gpu-completion-callback", revision: completedRevision, extra: ["metalCommandBufferStatusAvailable": false,
            "callbackUptime": callbackUptime, "callbackEpoch": callbackEpoch])
        defer { inFlight = nil; drain() }
        guard active, !failed, completedRevision == revision else {
            log("stale-completion-discarded", revision: completedRevision); return
        }
        do {
            guard let context, let colorSpace = CGColorSpace(name: CGColorSpace.sRGB),
                  let ciImage = CIImage(mtlTexture: frame.texture, options: [.colorSpace: colorSpace]),
                  let cgImage = context.createCGImage(ciImage, from: ciImage.extent,
                    format: .RGBA8, colorSpace: colorSpace, deferred: false) else { throw Failure.conversion }
            // No flip inferred from appearance. This explicit up/no-transform convention must pass visual review.
            let result = UIImage(cgImage: cgImage, scale: frame.request.input.displayScale, orientation: .up)
            log("conversion-complete", revision: completedRevision, extra: [
                "cgAlphaInfo": cgImage.alphaInfo.rawValue, "cgBitsPerComponent": cgImage.bitsPerComponent,
                "cgColorSpace": cgImage.colorSpace?.name as String? ?? "nil",
                "cgWidth": cgImage.width, "cgHeight": cgImage.height,
                "orientation": "up", "eagerMaterialization": true])
            guard publishedCount < 64, let png = result.pngData() else { throw Failure.png }
            let directory = try BoardHighlightDiagnostic.shared.handImageDirectory(session: session)
            let url = directory.appendingPathComponent("revision-\(completedRevision).png")
            try png.write(to: url, options: .withoutOverwriting)
            // No suspension between current-revision check, conversion, file materialization and publication.
            image = result; unavailable = false; publishedCount += 1
            log("published", revision: completedRevision, extra: [
                "currentRevision": revision, "pngPath": url.path,
                "pngSHA256": SHA256.hash(data: png).map { String(format: "%02x", $0) }.joined(),
                "pngByteCount": png.count])
        } catch { fail(error, revision: completedRevision) }
    }
    private func fail(_ error: Error, revision: Int) {
        failed = true; pending = nil; image = nil; unavailable = true
        log("failed", revision: revision, extra: ["error": String(describing: error)])
    }
    private func log(_ event: String, revision: Int, extra: [String: Any] = [:]) {
        var fields = extra
        fields["sessionID"] = session.uuidString; fields["revision"] = revision
        BoardHighlightDiagnostic.shared.handImage(event, fields: fields)
    }
    private enum Failure: Error { case nonfiniteViewport, invalidDisplayScale, negativeViewport, oversizedViewport, sceneUnavailable, noMetalDevice, noTexture, conversion, png }
}

@MainActor
private struct HandImagePrototypeView: View {
    let pose: GripHandPose
    let side: GripCueSide
    let reset: Int
    @Environment(\.displayScale) private var displayScale
    @StateObject private var coordinator: HandImageCoordinator
    @State private var dragState = GripHandDragState()
    @State private var lastMagnification: CGFloat = 1
    init(pose: GripHandPose, side: GripCueSide = .right, reset: Int,
         makeScene: @escaping @MainActor () -> HandImageScene) {
        self.pose = pose; self.side = side; self.reset = reset
        _coordinator = StateObject(wrappedValue: HandImageCoordinator(makeScene: makeScene))
    }
    var body: some View {
        GeometryReader { proxy in
            let input = HandImageInput(pose: pose, side: side, size: proxy.size, displayScale: displayScale, reset: reset)
            ZStack {
                Color.clear
                if let image = coordinator.image {
                    Image(uiImage: image).resizable().interpolation(.none)
                } else if coordinator.unavailable {
                    Text("3D hand image unavailable").font(.caption2).foregroundStyle(.secondary)
                }
            }
            .contentShape(Rectangle())
            .onAppear { coordinator.submit(input) }
            .onChange(of: input) { _, value in coordinator.submit(value) }
            .onDisappear { coordinator.disappear() }
            .simultaneousGesture(DragGesture(minimumDistance: OrbitPanArbitration.activationDistance)
                .onChanged { value in
                    guard let delta = dragState.advance(translation: value.translation, velocity: value.velocity) else { return }
                    coordinator.orbitBy(azimuth: Float(-delta.width / max(proxy.size.width, 1)) * 0.9,
                                        elevation: Float(-delta.height / max(proxy.size.height, 1)) * 0.65)
                }.onEnded { _ in dragState.reset() })
            .simultaneousGesture(MagnificationGesture().onChanged { value in
                let ratio = value / max(lastMagnification, 0.001); lastMagnification = value
                coordinator.orbitBy(azimuth: 0, elevation: 0, zoom: Float(ratio))
            }.onEnded { _ in lastMagnification = 1 })
            .accessibilityHidden(true)
        }
    }
}
#endif
