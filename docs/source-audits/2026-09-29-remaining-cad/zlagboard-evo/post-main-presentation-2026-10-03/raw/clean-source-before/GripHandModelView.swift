import RealityKit
import Metal
import SwiftUI

/// Rendering parameters, not anatomical measurements or training prescriptions.
/// Explicit finger selections take precedence; otherwise the display assumes four fingers.
struct GripHandPose: Equatable {
    let posture: GripType?
    let highlightedFingers: Set<FingerSlot>
    let hasExplicitFingers: Bool

    init(posture: GripType?, fingerConfiguration: FingerConfiguration?) {
        self.posture = posture
        highlightedFingers = fingerConfiguration?.engagedFingers ?? Set(FingerSlot.allCases)
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

private struct GripHandPreparation: Equatable {
    let id: UUID
    let size: CGSize
    let pose: GripHandPose
    let isLeft: Bool?
    let resetToken: Int
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
    @State private var preparationHostID = UUID()
    @State private var synchronizedPreparation: GripHandPreparation?
    @Environment(\.workoutRendererPreparationID) private var preparationID

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
        let _ = cameraRevision
        GeometryReader { proxy in
            let size = proxy.size
            RealityView { content in
                content.camera = .virtual
                content.add(scene.root)
                syncScene(in: size)
                updateUnavailableState()
                reportPreparation(in: size)
            } update: { _ in
                syncScene(in: size)
                updateUnavailableState()
                reportPreparation(in: size)
            }
            .simultaneousGesture(orbitGesture(size: size))
            .simultaneousGesture(magnifyGesture)
            #if targetEnvironment(simulator)
            .background {
                #if DEBUG
                if ProcessInfo.processInfo.environment["HANGTEN_REVIEW_SKIP_HAND_PRESENTATION"] != "1" {
                    SimulatorDrawablePresentation(role: "single-hand").allowsHitTesting(false)
                }
                #else
                SimulatorDrawablePresentation(role: "single-hand").allowsHitTesting(false)
                #endif
            }
            #endif
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
            .accessibilityHidden(true)
            .preference(key: WorkoutRendererReadinessKey.self, value: preparationID == nil
                        ? .init() : .init(renderers: [preparationHostID: .init(
                            kind: .hand, isReady: synchronizedPreparation == currentPreparation(in: size) && !isUnavailable,
                            preparationID: preparationID)]))
        }
    }

    private func currentPreparation(in size: CGSize) -> GripHandPreparation? {
        preparationID.map { GripHandPreparation(id: $0, size: size,
            pose: GripHandPose(posture: posture, fingerConfiguration: fingerConfiguration),
            isLeft: side == .left, resetToken: resetToken) }
    }

    private func reportPreparation(in size: CGSize) {
        guard let preparation = currentPreparation(in: size), synchronizedPreparation != preparation,
              size.width.isFinite, size.height.isFinite, size.width > 0, size.height > 0,
              !scene.isUnavailable else { return }
        Task { @MainActor in synchronizedPreparation = preparation }
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

    struct Geometry {
        let positions: [SIMD3<Float>]
        let normals: [SIMD3<Float>]
        let indices: [UInt32]
    }

    static func geometry(asset: GripHandAsset, action: String, mirrored: Bool) throws -> Geometry {
        guard let source = asset.poses[action] else { throw GripHandAsset.AssetError.invalidMesh }
        let positions = stride(from: 0, to: source.positions.count, by: 3).map { offset in
            SIMD3(mirrored ? -source.positions[offset] : source.positions[offset],
                  source.positions[offset + 1], source.positions[offset + 2])
        }
        let normals = stride(from: 0, to: source.normals.count, by: 3).map { offset in
            SIMD3(mirrored ? -source.normals[offset] : source.normals[offset],
                  source.normals[offset + 1], source.normals[offset + 2])
        }
        var indices: [UInt32] = asset.indices
        if mirrored {
            for offset in stride(from: 0, to: indices.count, by: 3) {
                indices.swapAt(offset + 1, offset + 2)
            }
        }
        return Geometry(positions: positions, normals: normals, indices: indices)
    }

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
        let mirrored: Bool
    }

    let root = Entity()
    let modelEntity = ModelEntity()
    private(set) var vertexCount = 0
    private(set) var triangleCount = 0
    private(set) var appliedPose: GripHandPose?
    private(set) var appliedVertexColors: [SIMD4<Float>] = []
    private(set) var appliedMirrored = false

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

    func apply(_ pose: GripHandPose, mirrored: Bool = false) throws {
        let key = MeshKey(action: pose.action(), fingers: pose.highlightedFingers, mirrored: mirrored)
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
        appliedMirrored = mirrored
        vertexCount = asset.vertexCount
        triangleCount = asset.indices.count / 3
    }

    /// Frame the exact displayed surface, including the source's short wrist.
    func posedVerticesForFraming() -> [SIMD3<Float>] {
        guard let positions = asset.poses[currentAction]?.positions else { return [] }
        return stride(from: 0, to: positions.count, by: 3).map {
            SIMD3(appliedMirrored ? -positions[$0] : positions[$0],
                  positions[$0 + 1], positions[$0 + 2])
        }
    }

    private func makeMesh(for key: MeshKey, pose: GripHandPose) throws -> BuiltMesh {
        let geometry = try GripHandRealityMeshBuilder.geometry(
            asset: asset, action: key.action, mirrored: key.mirrored
        )
        let colors = try GripHandRealityMeshBuilder.vertexColors(
            asset: asset, action: pose, selectedFingers: key.fingers
        )
        let vertices = (0..<asset.vertexCount).map { i in
            Vertex(position: geometry.positions[i],
                   normal: geometry.normals[i],
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
            indexCapacity: geometry.indices.count
        )
        let lowLevelMesh = try LowLevelMesh(descriptor: descriptor)
        lowLevelMesh.withUnsafeMutableBytes(bufferIndex: 0) { destination in
            vertices.withUnsafeBytes { source in destination.copyBytes(from: source) }
        }
        lowLevelMesh.withUnsafeMutableIndices { destination in
            geometry.indices.withUnsafeBytes { source in destination.copyBytes(from: source) }
        }
        lowLevelMesh.parts.append(.init(indexCount: geometry.indices.count, bounds: bounds))
        return BuiltMesh(resource: try MeshResource(from: lowLevelMesh), vertexColors: colors)
    }
}

@MainActor
final class GripHandRealityScene {
    let root = Entity()
    let hand = Entity()
    let camera = Entity()
    private let keyLight = Entity()
    private let fillLight = Entity()
    private(set) var isUnavailable = false

    private var surface: GripHandRealitySurface?
    var isMirrored: Bool { surface?.appliedMirrored ?? false }
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
        root.addChild(hand)
        var orthographicCamera = OrthographicCameraComponent()
        orthographicCamera.near = 0.1
        orthographicCamera.far = 100
        orthographicCamera.scale = 3.2
        orthographicCamera.scaleDirection = .vertical
        camera.components.set(orthographicCamera)
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
        if poseChanged || sideChanged {
            do {
                try surface?.apply(pose, mirrored: side == .left)
            } catch {
                surface?.root.removeFromParent()
                surface = nil
                isUnavailable = true
            }
        }
        if sideChanged {
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
        let points = surface.posedVerticesForFraming().map { SIMD4<Float>($0, 1) }
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
        camera.transform = Transform(matrix: transform)
        var component = camera.components[OrthographicCameraComponent.self]!
        component.scale = orthographicScale
        camera.components.set(component)

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
        var component = camera.components[OrthographicCameraComponent.self]!
        component.scale = canonicalOrthographicScale / nextZoom
        camera.components.set(component)
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
            color: .white, intensity: 2_800
        ))
        fillLight.components.set(DirectionalLightComponent(
            color: .white, intensity: 250
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

    private let handGap: Float = 0.55
    private var canonicalCenter = SIMD3<Float>.zero
    private var canonicalOffset = SIMD3<Float>(0, 0, 1)
    private var canonicalOrthographicScale: Float = 1
    private var orbitAzimuth: Float = 0
    private var orbitElevation: Float = 0
    private var orbitZoom: Float = 1

    init(assetResult: Result<GripHandAsset, Error> = GripHandAsset.bundled) {
        root.addChild(leftHand)
        root.addChild(rightHand)
        // Show the palm and the inward curl of each half-crimp finger.
        leftHand.orientation = simd_quatf(angle: 0.85, axis: SIMD3(0, 1, 0))
        rightHand.orientation = simd_quatf(angle: -0.85, axis: SIMD3(0, 1, 0))
        var orthographicCamera = OrthographicCameraComponent()
        orthographicCamera.near = 0.1
        orthographicCamera.far = 100
        orthographicCamera.scale = 3.2
        orthographicCamera.scaleDirection = .vertical
        camera.components.set(orthographicCamera)
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
                try leftSurface?.apply(pose, mirrored: true)
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
        let leftLocal = leftSurface.posedVerticesForFraming()
        let rightLocal = rightSurface.posedVerticesForFraming()
        guard let leftInnerEdge = leftLocal.map({ leftHand.orientation.act($0).x }).max(),
              let rightInnerEdge = rightLocal.map({ rightHand.orientation.act($0).x }).min() else { return }
        let slotOffset = max(0, (leftInnerEdge - rightInnerEdge + handGap) / 2)
        leftHand.position.x = -slotOffset
        rightHand.position.x = slotOffset
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
        camera.transform = Transform(matrix: transform)
        var component = camera.components[OrthographicCameraComponent.self]!
        component.scale = scale
        camera.components.set(component)
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
        var component = camera.components[OrthographicCameraComponent.self]!
        component.scale = canonicalOrthographicScale / nextZoom
        camera.components.set(component)
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
    @State private var preparationHostID = UUID()
    @State private var synchronizedPreparation: GripHandPreparation?
    @Environment(\.workoutRendererPreparationID) private var preparationID

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
        let _ = cameraRevision
        GeometryReader { proxy in
            let size = proxy.size
            RealityView { content in
                content.camera = .virtual
                content.add(scene.root)
                syncScene(in: size)
                updateUnavailableState()
                reportPreparation(in: size)
            } update: { _ in
                syncScene(in: size)
                updateUnavailableState()
                reportPreparation(in: size)
            }
            .simultaneousGesture(orbitGesture(size: size))
            .simultaneousGesture(magnifyGesture)
            #if targetEnvironment(simulator)
            .background {
                #if DEBUG
                if ProcessInfo.processInfo.environment["HANGTEN_REVIEW_SKIP_HAND_PRESENTATION"] != "1" {
                    SimulatorDrawablePresentation(role: "paired-hands").allowsHitTesting(false)
                }
                #else
                SimulatorDrawablePresentation(role: "paired-hands").allowsHitTesting(false)
                #endif
            }
            #endif
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
            .accessibilityHidden(true)
            .preference(key: WorkoutRendererReadinessKey.self, value: preparationID == nil
                        ? .init() : .init(renderers: [preparationHostID: .init(
                            kind: .hand, isReady: synchronizedPreparation == currentPreparation(in: size) && !isUnavailable,
                            preparationID: preparationID)]))
        }
    }

    private func currentPreparation(in size: CGSize) -> GripHandPreparation? {
        preparationID.map { GripHandPreparation(id: $0, size: size,
            pose: GripHandPose(posture: posture, fingerConfiguration: fingerConfiguration),
            isLeft: nil, resetToken: resetToken) }
    }

    private func reportPreparation(in size: CGSize) {
        guard let preparation = currentPreparation(in: size), synchronizedPreparation != preparation,
              size.width.isFinite, size.height.isFinite, size.width > 0, size.height > 0,
              scene.isAvailable else { return }
        Task { @MainActor in synchronizedPreparation = preparation }
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

#if DEBUG
/// Isolated visual QA; choices here never modify a workout or its prescriptions.
struct GripHandModelReviewView: View {
    @State private var posture: GripType = .halfCrimp
    @State private var fingers: Set<FingerSlot> = [.index, .middle, .ring, .pinky]
    @State private var resetToken = 0
    @State private var layoutOrientation = "unknown"

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
                Text(fingers.isEmpty ? "4 fingers (assumed)" : "Highlighted: " + FingerSlot.allCases.filter(fingers.contains).map(\.rawValue).joined(separator: ", "))
                    .font(.caption)
                    .accessibilityIdentifier("gripModel.review.fingerSummary")
                    .accessibilityValue(layoutOrientation)
                Button("Reset view") { resetToken += 1 }
                Text("Drag to rotate · Pinch to zoom")
                    .font(.caption)
            }
            .padding()
            .background(Color.hangCream)
            .navigationTitle("3D hand review")
        }
        // XCTest's SpringBoard frame does not track the foreground app's rotation.
        // Report the actual review layout so screenshots wait for SwiftUI to resize.
        .onGeometryChange(for: String.self) { geometry in
            let size = geometry.size
            guard size.width.isFinite, size.height.isFinite,
                  size.width > 0, size.height > 0 else { return "unknown" }
            return size.width > size.height ? "landscape" : "portrait"
        } action: { layoutOrientation = $0 }
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
