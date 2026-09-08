import SceneKit
import SwiftUI

/// Display-only models are app resources, separate from the canonical board packages.
/// SceneKit supplies exact triangle picking and on-demand rendering on iOS 17.
/// Keep this bridge isolated so its deprecated rendering API can be replaced independently.
enum BoardModelIdentity {
    static let boardID = "metolius.wood-grips-compact-ii"
}

enum BoardModelAsset {
    static let boardID = BoardModelIdentity.boardID
    static var holdIDs: Set<String> {
        Set(BoardCatalog.packageStore.board(id: boardID)?.holds.map(\.id) ?? [])
    }

    static func supports(_ board: TrainingBoard, presentation: BoardPresentation) -> Bool {
        board.id == boardID
            && board == BoardCatalog.packageStore.board(id: boardID)
            && presentation == board.defaultPresentation
            && presentation.id == BoardPresentation.primaryID
            && presentation.sourcePresentationID == nil
            && !presentation.isInverted
            && Set(board.holds.map(\.id)) == holdIDs
    }

    static func url(in bundle: Bundle = .main) -> URL? {
        bundle.url(forResource: "wood-grips-compact-ii", withExtension: "usdz", subdirectory: "BoardModels")
    }

    static func load(url: URL?) -> SCNScene? {
        // Some SceneKit versions return an empty scene for a missing file.
        guard let url, url.isFileURL,
              let values = try? url.resourceValues(forKeys: [.isRegularFileKey]),
              values.isRegularFile == true else { return nil }
        return try? SCNScene(url: url, options: [.convertToYUp: true])
    }

    static func holdID(for node: SCNNode) -> String? {
        var candidate: SCNNode? = node
        while let current = candidate {
            // USD identifiers replace hyphens with underscores. Only the explicitly
            // registered inventory can map back into a logical app hold.
            let id = (current.name ?? "").replacingOccurrences(of: "_", with: "-")
            if holdIDs.contains(id) { return id }
            candidate = current.parent
        }
        return nil
    }
}

@MainActor
private enum BoardModelCache {
    // Share the decode across simultaneous cards, but give every view independent
    // nodes/materials. A failed load is cached too; the package image stays usable.
    static var loading: Task<SCNScene?, Never>?

    static func source() async -> SCNScene? {
        if let loading { return await loading.value }
        let url = BoardModelAsset.url()
        let task = Task.detached(priority: .userInitiated) { () -> SCNScene? in
            BoardModelAsset.load(url: url)
        }
        loading = task
        return await task.value
    }
}

/// The fallback stays visible while the USDZ decodes and if its inventory is invalid.
struct BoardModelSurface<Fallback: View>: View {
    let board: TrainingBoard
    let presentation: BoardPresentation
    let highlightedHoldIDs: Set<String>
    let highlightMode: BoardHighlightMode
    let onHoldTap: ((BoardHold) -> Void)?
    @ViewBuilder let fallback: () -> Fallback
    @State private var model: BoardModelScene?

    static func hitTestingEnabled(onHoldTap: ((BoardHold) -> Void)?) -> Bool {
        onHoldTap != nil
    }

    var body: some View {
        Group {
            if BoardModelAsset.supports(board, presentation: presentation), let model {
                BoardModelView(
                    model: model, holds: board.holds,
                    highlightedHoldIDs: highlightedHoldIDs, highlightMode: highlightMode,
                    onHoldTap: onHoldTap
                )
                .accessibilityIdentifier("boardModel.3d")
                .allowsHitTesting(Self.hitTestingEnabled(onHoldTap: onHoldTap))
            } else {
                fallback()
            }
        }
        .task(id: BoardModelAsset.supports(board, presentation: presentation)) {
            guard model == nil,
                  BoardModelAsset.supports(board, presentation: presentation),
                  let source = await BoardModelCache.source(), !Task.isCancelled else { return }
            model = BoardModelScene(source: source)
        }
    }
}

@MainActor
final class BoardModelScene {
    let scene = SCNScene()
    let camera = SCNNode()
    private(set) var holdNodes: [String: [SCNNode]] = [:]
    private var originalMaterials: [ObjectIdentifier: [SCNMaterial]] = [:]
    private var lastHighlights: Set<String> = []
    private var lastMode: BoardHighlightMode?

    init?(source: SCNScene) {
        let model = source.rootNode.clone()
        var hasUnboundGeometry = false
        model.enumerateChildNodes { node, _ in
            guard let geometry = node.geometry else { return }
            if geometry.materials.isEmpty { hasUnboundGeometry = true }
            node.geometry = geometry.copy() as? SCNGeometry
            node.geometry?.materials = geometry.materials.compactMap { $0.copy() as? SCNMaterial }
            guard let id = BoardModelAsset.holdID(for: node) else { return }
            holdNodes[id, default: []].append(node)
            originalMaterials[ObjectIdentifier(node)] = node.geometry?.materials
        }
        guard !hasUnboundGeometry, Set(holdNodes.keys) == BoardModelAsset.holdIDs else { return nil }
        scene.rootNode.addChildNode(model)
        camera.camera = SCNCamera()
        camera.camera?.usesOrthographicProjection = true
        camera.camera?.zNear = 0.01
        camera.camera?.zFar = 10
        camera.camera?.wantsHDR = false
        camera.camera?.screenSpaceAmbientOcclusionIntensity = 0.7
        camera.camera?.screenSpaceAmbientOcclusionRadius = 0.018
        camera.camera?.screenSpaceAmbientOcclusionBias = 0.001
        camera.camera?.screenSpaceAmbientOcclusionDepthThreshold = 0.03
        camera.position = SCNVector3(0, 0.0785, 1)
        camera.look(at: SCNVector3(0, 0.0785, 0.028))
        scene.rootNode.addChildNode(camera)

        let ambient = SCNNode()
        ambient.light = SCNLight()
        ambient.light?.type = .ambient
        ambient.light?.intensity = 250
        scene.rootNode.addChildNode(ambient)
        let key = SCNNode()
        key.light = SCNLight()
        key.light?.type = .directional
        key.light?.intensity = 850
        key.light?.castsShadow = true
        key.light?.shadowColor = UIColor.black.withAlphaComponent(0.45)
        key.light?.shadowRadius = 3
        key.light?.shadowSampleCount = 8
        key.light?.shadowMapSize = CGSize(width: 2048, height: 2048)
        key.light?.zNear = 0.01
        key.light?.zFar = 3
        key.light?.maximumShadowDistance = 3
        key.position = SCNVector3(-0.4, 0.8, 1)
        key.look(at: SCNVector3(0, 0.08, 0))
        scene.rootNode.addChildNode(key)
    }

    func frame(in size: CGSize) {
        guard size.width > 0, size.height > 0 else { return }
        camera.camera?.orthographicScale = max(0.085, 0.335 * size.height / size.width)
    }

    func highlight(_ ids: Set<String>, mode: BoardHighlightMode) {
        let validIDs = ids.intersection(BoardModelAsset.holdIDs)
        guard validIDs != lastHighlights || mode != lastMode else { return }
        let color = UIColor(mode == .active ? Color.holdActive : Color.restBlue)
        for (id, nodes) in holdNodes {
            for node in nodes {
                let originals = originalMaterials[ObjectIdentifier(node)] ?? []
                if validIDs.contains(id) {
                    node.geometry?.materials = originals.compactMap { original in
                        guard let material = original.copy() as? SCNMaterial else { return nil }
                        material.diffuse.contents = color
                        material.emission.contents = color.withAlphaComponent(0.18)
                        material.emission.intensity = 0.18
                        material.roughness.contents = 0.8
                        return material
                    }
                } else {
                    node.geometry?.materials = originals
                }
            }
        }
        lastHighlights = validIDs
        lastMode = mode
    }
}

private struct BoardModelView: UIViewRepresentable {
    let model: BoardModelScene
    let holds: [BoardHold]
    let highlightedHoldIDs: Set<String>
    let highlightMode: BoardHighlightMode
    let onHoldTap: ((BoardHold) -> Void)?

    func makeUIView(context: Context) -> BoardModelSCNView {
        let view = BoardModelSCNView()
        view.backgroundColor = .clear
        view.isOpaque = false
        view.antialiasingMode = .multisampling4X
        view.rendersContinuously = false
        view.isPlaying = false
        view.allowsCameraControl = false
        view.display(model)
        view.delegate = view
        view.addGestureRecognizer(UITapGestureRecognizer(target: view, action: #selector(view.selectHold(_:))))
        return view
    }

    func updateUIView(_ view: BoardModelSCNView, context: Context) {
        view.display(model)
        view.holds = holds
        view.onHoldTap = onHoldTap
        view.highlightedHoldIDs = highlightedHoldIDs
        view.isUserInteractionEnabled = onHoldTap != nil
        view.needsAccessibilityProjection = true
        model.highlight(highlightedHoldIDs, mode: highlightMode)
        view.updateAccessibility()
    }

    static func dismantleUIView(_ view: BoardModelSCNView, coordinator: ()) {
        view.onHoldTap = nil
        view.accessibilityElements = nil
        view.delegate = nil
        view.scene = nil
        view.model = nil
    }
}

private final class BoardModelAccessibilityElement: UIAccessibilityElement {
    var action: (() -> Void)?
    override func accessibilityActivate() -> Bool {
        guard let action else { return false }
        action()
        return true
    }
}

final class BoardModelSCNView: SCNView, SCNSceneRendererDelegate {
    var model: BoardModelScene?
    var holds: [BoardHold] = []
    var highlightedHoldIDs: Set<String> = []
    var onHoldTap: ((BoardHold) -> Void)?
    var needsAccessibilityProjection = true
    private var holdAccessibilityElements: [String: BoardModelAccessibilityElement] = [:]
    private var accessibilityHoldIDs: [String] = []

    func display(_ model: BoardModelScene) {
        guard self.model !== model else { return }
        self.model = model
        scene = model.scene
        pointOfView = model.camera
        model.frame(in: bounds.size)
        needsAccessibilityProjection = true
    }

    override func layoutSubviews() {
        super.layoutSubviews()
        model?.frame(in: bounds.size)
        needsAccessibilityProjection = true
        updateAccessibility()
    }

    nonisolated func renderer(_ renderer: any SCNSceneRenderer, didRenderScene scene: SCNScene, atTime time: TimeInterval) {
        // projectPoint uses the renderer's committed camera projection, which can
        // still be the previous layout's projection during layoutSubviews.
        DispatchQueue.main.async { [weak self] in
            guard let self, self.needsAccessibilityProjection else { return }
            self.needsAccessibilityProjection = false
            self.updateAccessibility()
        }
    }

    @objc func selectHold(_ recognizer: UITapGestureRecognizer) {
        guard let hit = hitTest(recognizer.location(in: self), options: [.searchMode: SCNHitTestSearchMode.closest.rawValue]).first,
              let id = BoardModelAsset.holdID(for: hit.node),
              let hold = holds.first(where: { $0.id == id }) else { return }
        onHoldTap?(hold)
    }

    func updateAccessibility() {
        guard let onHoldTap, let model else {
            isAccessibilityElement = true
            accessibilityLabel = "Wood Grips Compact II hangboard"
            accessibilityValue = holds.filter { highlightedHoldIDs.contains($0.id) }.map(\.name).joined(separator: ", ")
            accessibilityElements = nil
            holdAccessibilityElements.removeAll()
            accessibilityHoldIDs = []
            return
        }
        isAccessibilityElement = false
        let elements = holds.compactMap { hold -> UIAccessibilityElement? in
            guard let node = model.holdNodes[hold.id]?.first else { return nil }
            let box = node.boundingBox
            let center = SCNVector3((box.min.x + box.max.x) / 2, (box.min.y + box.max.y) / 2, (box.min.z + box.max.z) / 2)
            let projected = projectPoint(node.convertPosition(center, to: nil))
            guard projected.x.isFinite, projected.y.isFinite else { return nil }
            let element = holdAccessibilityElements[hold.id]
                ?? BoardModelAccessibilityElement(accessibilityContainer: self)
            holdAccessibilityElements[hold.id] = element
            element.accessibilityLabel = hold.name
            element.accessibilityIdentifier = "boardModel.hold.\(hold.id)"
            element.accessibilityTraits = highlightedHoldIDs.contains(hold.id) ? [.button, .selected] : .button
            element.accessibilityFrameInContainerSpace = CGRect(x: CGFloat(projected.x) - 18, y: CGFloat(projected.y) - 18, width: 36, height: 36)
            element.action = { onHoldTap(hold) }
            return element
        }
        let ids = elements.compactMap(\.accessibilityIdentifier)
        if accessibilityHoldIDs != ids {
            accessibilityElements = elements
            accessibilityHoldIDs = ids
        }
    }
}
