import SceneKit
import SwiftUI

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
struct GripHandModelView: UIViewRepresentable {
    let posture: GripType?
    let fingerConfiguration: FingerConfiguration?
    let side: GripCueSide
    var interactive = false
    var resetToken = 0

    func makeCoordinator() -> Coordinator { Coordinator() }

    func makeUIView(context: Context) -> SCNView {
        let view = GripHandSceneView()
        view.backgroundColor = .clear
        view.isOpaque = false
        view.antialiasingMode = .multisampling4X
        view.preferredFramesPerSecond = 30
        view.rendersContinuously = false
        view.isPlaying = false
        view.isAccessibilityElement = false
        view.accessibilityElementsHidden = true
        context.coordinator.install(in: view)
        view.didResize = { [weak coordinator = context.coordinator] in coordinator?.resetCamera() }
        return view
    }

    func updateUIView(_ view: SCNView, context: Context) {
        let pose = GripHandPose(posture: posture, fingerConfiguration: fingerConfiguration)
        context.coordinator.update(pose: pose, side: side, resetToken: resetToken)
        view.isUserInteractionEnabled = interactive
        view.allowsCameraControl = interactive
        view.defaultCameraController.interactionMode = .orbitTurntable
        view.defaultCameraController.inertiaEnabled = false
        view.defaultCameraController.minimumVerticalAngle = -75
        view.defaultCameraController.maximumVerticalAngle = 75
        view.setNeedsDisplay()
    }

    static func dismantleUIView(_ view: SCNView, coordinator: Coordinator) {
        (view as? GripHandSceneView)?.didResize = nil
        view.scene = nil
        view.delegate = nil
    }

    final class Coordinator {
        private let scene = SCNScene()
        private let hand = SCNNode()
        private let camera = SCNNode()
        private var rig: GripHandSurface?
        private weak var view: SCNView?
        private var currentPose: GripHandPose?
        private var currentSide: GripCueSide?
        private var currentResetToken: Int?

        func install(in view: SCNView) {
            self.view = view
            scene.rootNode.addChildNode(hand)
            camera.camera = SCNCamera()
            camera.camera?.usesOrthographicProjection = true
            camera.camera?.orthographicScale = 3.2
            camera.camera?.zNear = 0.1
            camera.camera?.zFar = 100
            scene.rootNode.addChildNode(camera)
            addLight(type: .ambient, intensity: 180, position: SCNVector3Zero)
            // Light the palm-facing default view evenly for both mirrored hands.
            addLight(type: .omni, intensity: 580, position: SCNVector3(0, 8, 7))
            addLight(type: .omni, intensity: 140, position: SCNVector3(0, 2, -5))
            switch GripHandAsset.bundled {
            case .success(let asset):
                let rig = GripHandSurface(asset: asset)
                hand.addChildNode(rig.root)
                self.rig = rig
            case .failure:
                let label = UILabel()
                label.text = "3D hand unavailable"
                label.font = .preferredFont(forTextStyle: .caption2)
                label.textColor = .secondaryLabel
                label.textAlignment = .center
                label.numberOfLines = 0
                label.frame = view.bounds
                label.autoresizingMask = [.flexibleWidth, .flexibleHeight]
                view.addSubview(label)
            }
            view.scene = scene
            view.pointOfView = camera
        }

        func update(pose: GripHandPose, side: GripCueSide, resetToken: Int) {
            let changed = currentPose != pose || currentSide != side
            if changed {
                rig?.apply(pose)
                hand.scale.x = side == .left ? -1 : 1
            }
            let reset = changed || currentResetToken != resetToken
            currentPose = pose
            currentSide = side
            currentResetToken = resetToken
            if reset { resetCamera() }
        }

        func resetCamera() {
            guard let rig else { return }
            let points = rig.posedVerticesForFraming().map { hand.simdTransform * SIMD4<Float>($0, 1) }
            guard !points.isEmpty else { return }
            var low = SIMD3<Float>(repeating: .greatestFiniteMagnitude)
            var high = SIMD3<Float>(repeating: -.greatestFiniteMagnitude)
            for point in points {
                let xyz = SIMD3<Float>(point.x, point.y, point.z)
                low = simd_min(low, xyz)
                high = simd_max(high, xyz)
            }
            let center = (low + high) / 2
            // A palm-oblique view reveals the finger pads and joint bends.
            camera.simdPosition = center + SIMD3<Float>(currentSide == .left ? 5.8 : -5.8, 2.75, 9.4)
            camera.look(at: SCNVector3(center.x, center.y, center.z))
            let inverseCamera = simd_inverse(camera.simdTransform)
            var halfWidth: Float = 0
            var halfHeight: Float = 0
            for point in points {
                let projected = inverseCamera * point
                halfWidth = max(halfWidth, abs(projected.x))
                halfHeight = max(halfHeight, abs(projected.y))
            }
            let size = view?.bounds.size ?? .zero
            let aspect = size.height > 0 && size.width > 0 ? Float(size.width / size.height) : 0.85
            camera.camera?.orthographicScale = Double(max(halfHeight, halfWidth / aspect) * 1.08)
            view?.pointOfView = camera
            view?.defaultCameraController.target = SCNVector3(center.x, center.y, center.z)
            view?.setNeedsDisplay()
        }

        private func addLight(type: SCNLight.LightType, intensity: CGFloat, position: SCNVector3) {
            let node = SCNNode()
            node.light = SCNLight()
            node.light?.type = type
            node.light?.intensity = intensity
            node.light?.color = UIColor(white: 1, alpha: 1)
            node.position = position
            scene.rootNode.addChildNode(node)
        }
    }
}

private final class GripHandSceneView: SCNView {
    var didResize: (() -> Void)?
    private var previousSize: CGSize = .zero

    override func layoutSubviews() {
        super.layoutSubviews()
        if bounds.size != previousSize {
            previousSize = bounds.size
            didResize?()
        }
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

private final class GripHandSurface {
    let root = SCNNode()
    private let mesh = SCNNode()
    private let asset: GripHandAsset
    private let channels: SCNGeometrySource
    private let triangles: SCNGeometryElement
    private let material: SCNMaterial
    // Most cue cards never change pose. Cache only the three most recently viewed
    // surfaces in each instance; never allocate every pocket combination eagerly.
    private var geometries: [String: SCNGeometry] = [:]
    private var recentPoses: [String] = []
    private var currentAction = "Neutral"

    init(asset: GripHandAsset) {
        self.asset = asset
        // Four one-hot vertex channels preserve exact finger identity. The shader
        // selects channels before interpolation, so adjacent fingers stay neutral.
        var values = [Float](repeating: 0, count: asset.vertexCount * 4)
        for vertex in 0..<asset.vertexCount {
            let digit = asset.digitIndices[vertex]
            if digit >= 2 { values[vertex * 4 + digit - 2] = asset.highlightWeights[vertex] }
        }
        channels = Self.source(values, semantic: .color, components: 4)
        triangles = SCNGeometryElement(indices: asset.indices, primitiveType: .triangles)
        material = SCNMaterial()
        material.lightingModel = .physicallyBased
        material.diffuse.contents = UIColor.white
        material.roughness.contents = 0.9
        material.metalness.contents = 0
        material.isDoubleSided = true
        root.addChildNode(mesh)
    }

    func apply(_ pose: GripHandPose) {
        let action = pose.action()
        let geometry = geometry(for: action)
        SCNTransaction.begin()
        SCNTransaction.disableActions = true
        mesh.geometry = geometry
        currentAction = action
        let selected = SCNVector4(
            pose.highlightedFingers.contains(.index) ? 1 : 0,
            pose.highlightedFingers.contains(.middle) ? 1 : 0,
            pose.highlightedFingers.contains(.ring) ? 1 : 0,
            pose.highlightedFingers.contains(.pinky) ? 1 : 0)
        geometry.setValue(NSValue(scnVector4: selected), forKey: "selectedFingers")
        SCNTransaction.commit()
    }

    /// Frame the exact displayed surface, including the source's short wrist.
    func posedVerticesForFraming() -> [SIMD3<Float>] {
        let positions = asset.poses[currentAction]!.positions
        return stride(from: 0, to: positions.count, by: 3).map {
            SIMD3(positions[$0], positions[$0 + 1], positions[$0 + 2])
        }
    }

    private func geometry(for action: String) -> SCNGeometry {
        recentPoses.removeAll { $0 == action }
        recentPoses.append(action)
        if let cached = geometries[action] { return cached }
        // Required surfaces and every buffer are validated at load time.
        let surface = asset.poses[action]!
        let geometry = SCNGeometry(sources: [
            Self.source(surface.positions, semantic: .vertex, components: 3),
            Self.source(surface.normals, semantic: .normal, components: 3),
            channels
        ], elements: [triangles])
        geometry.firstMaterial = material
        geometry.shaderModifiers = [.geometry: """
        #pragma arguments
        float4 selectedFingers;
        #pragma body
        float strength = clamp(dot(_geometry.color, selectedFingers), 0.0, 1.0);
        // Shader colors are linear; keep the sage base muted and orange saturated.
        _geometry.color = mix(float4(0.18, 0.23, 0.20, 1.0),
                              float4(0.966, 0.0615, 0.0108, 1.0), strength);
        """]
        geometries[action] = geometry
        while recentPoses.count > 3 {
            geometries.removeValue(forKey: recentPoses.removeFirst())
        }
        return geometry
    }

    private static func source(_ values: [Float], semantic: SCNGeometrySource.Semantic, components: Int) -> SCNGeometrySource {
        values.withUnsafeBytes { buffer in
            SCNGeometrySource(data: Data(buffer), semantic: semantic, vectorCount: values.count / components,
                              usesFloatComponents: true, componentsPerVector: components, bytesPerComponent: 4,
                              dataOffset: 0, dataStride: components * 4)
        }
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
                          side: side, interactive: true, resetToken: resetToken)
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
                HStack {
                    GripHandModelView(posture: posture, fingerConfiguration: configuration,
                                      side: .left, interactive: true, resetToken: resetToken)
                    GripHandModelView(posture: posture, fingerConfiguration: configuration,
                                      side: .right, interactive: true, resetToken: resetToken)
                }
                Text(fingers.isEmpty ? "Fingers not specified" : "Highlighted: " + FingerSlot.allCases.filter(fingers.contains).map(\.rawValue).joined(separator: ", "))
                    .font(.caption)
                Button("Reset view") { resetToken += 1 }
                Text("Drag to rotate · Pinch to zoom")
                    .font(.caption)
            }
            .padding()
            .background(Color.hangCream)
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
