import SceneKit
import SwiftUI

/// Identity for a decoded package model. The hash makes replacement assets a
/// distinct cached source even when a board keeps the same presentation ID.
struct BoardModelKey: Hashable {
    let boardID: String
    let presentationID: String
    let modelSHA256: String
}

enum BoardModelAsset {
    static func load(media _: BoardModelMedia, packageURL: URL) -> SCNScene? {
        guard packageURL.isFileURL,
              let values = try? packageURL.resourceValues(forKeys: [.isRegularFileKey]),
              values.isRegularFile == true else {
            return nil
        }
        // SceneKit can otherwise return an empty scene for a missing asset.
        return try? SCNScene(url: packageURL, options: [.convertToYUp: true])
    }
}

@MainActor
private enum BoardModelCache {
    static var loading: [BoardModelKey: Task<SCNScene?, Never>] = [:]

    static func source(
        for key: BoardModelKey,
        media: BoardModelMedia,
        packageURL: URL
    ) async -> SCNScene? {
        if let task = loading[key] { return await task.value }
        let task = Task.detached(priority: .userInitiated) { () -> SCNScene? in
            BoardModelAsset.load(media: media, packageURL: packageURL)
        }
        loading[key] = task
        return await task.value
    }
}

@MainActor
enum BoardModelLoader {
    static func load(
        board: TrainingBoard,
        presentation: BoardPresentation,
        store: BoardPackageStore
    ) async -> BoardModelScene? {
        guard case .model(let media) = presentation.media,
              let packageURL = store.presentationAssetURL(for: board, presentationID: presentation.id) else {
            return nil
        }
        let key = BoardModelKey(
            boardID: board.id,
            presentationID: presentation.id,
            modelSHA256: media.descriptor.modelSHA256
        )
        guard let source = await BoardModelCache.source(
            for: key,
            media: media,
            packageURL: packageURL
        ), !Task.isCancelled else {
            return nil
        }
        return BoardModelScene(source: source, descriptor: media.descriptor)
    }
}

/// Task 3 owns the exhaustive raster/model presentation switch. This bridge
/// keeps its current raster caller compiling while a model is decoded, but its
/// model path has no board registry or resource fallback.
struct BoardModelSurface<Fallback: View>: View {
    enum ResultState {
        case loading
        case ready(BoardModelScene)
        case unavailable
    }

    let board: TrainingBoard
    let presentation: BoardPresentation
    let highlightedHoldIDs: Set<String>
    let highlightMode: BoardHighlightMode
    let onHoldTap: ((BoardHold) -> Void)?
    @ViewBuilder let fallback: () -> Fallback
    @State private var result: ResultState = .loading

    static func hitTestingEnabled(onHoldTap: ((BoardHold) -> Void)?) -> Bool {
        onHoldTap != nil
    }

    var body: some View {
        Group {
            if case .ready(let model) = result {
                BoardModelView(
                    model: model,
                    boardName: board.name,
                    holds: board.holds(in: presentation),
                    highlightedHoldIDs: highlightedHoldIDs,
                    highlightMode: highlightMode,
                    onHoldTap: onHoldTap
                )
                .accessibilityIdentifier("boardModel.3d")
                .allowsHitTesting(Self.hitTestingEnabled(onHoldTap: onHoldTap))
            } else {
                fallback()
            }
        }
        .task(id: loadIdentity) {
            guard case .model = presentation.media else {
                result = .unavailable
                return
            }
            result = .loading
            guard let model = await BoardModelLoader.load(
                board: board,
                presentation: presentation,
                store: BoardCatalog.packageStore
            ), !Task.isCancelled else {
                if !Task.isCancelled { result = .unavailable }
                return
            }
            result = .ready(model)
        }
    }

    private var loadIdentity: BoardModelKey? {
        guard case .model(let media) = presentation.media else { return nil }
        return BoardModelKey(
            boardID: board.id,
            presentationID: presentation.id,
            modelSHA256: media.descriptor.modelSHA256
        )
    }
}

@MainActor
final class BoardModelScene {
    let scene = SCNScene()
    let camera = SCNNode()
    let geometryNodes: [SCNNode]
    private(set) var holdNodes: [String: [SCNNode]] = [:]
    private var holdIDsByNode: [ObjectIdentifier: String] = [:]
    private var originalMaterials: [ObjectIdentifier: [SCNMaterial]] = [:]
    private var lastHighlights: Set<String> = []
    private var lastMode: BoardHighlightMode?

    init?(source: SCNScene, descriptor: BoardModelDescriptor) {
        let modelRoot = source.rootNode.clone()
        let descriptorIDs = descriptor.nodes.map(\.nodeID)
        guard !descriptorIDs.isEmpty,
              Set(descriptorIDs).count == descriptorIDs.count,
              Set(descriptorIDs).count == descriptor.nodes.count else {
            return nil
        }

        let descriptorsByNodeID = Dictionary(uniqueKeysWithValues: descriptor.nodes.map { ($0.nodeID, $0) })
        guard descriptorsByNodeID.count == descriptor.nodes.count else { return nil }

        var geometryByNodeID: [String: SCNNode] = [:]
        var clonedGeometryNodes: [SCNNode] = []
        var invalidGeometry = false
        modelRoot.enumerateChildNodes { node, _ in
            guard let geometry = node.geometry else { return }
            guard let nodeID = Self.nodeID(for: node, beneath: modelRoot),
                  geometryByNodeID[nodeID] == nil,
                  !geometry.materials.isEmpty,
                  geometry.sources(for: .vertex).contains(where: { $0.vectorCount > 0 }),
                  let copiedGeometry = geometry.copy() as? SCNGeometry else {
                invalidGeometry = true
                return
            }
            let copiedMaterials = geometry.materials.compactMap { $0.copy() as? SCNMaterial }
            guard copiedMaterials.count == geometry.materials.count else {
                invalidGeometry = true
                return
            }
            copiedGeometry.materials = copiedMaterials
            node.geometry = copiedGeometry
            geometryByNodeID[nodeID] = node
            clonedGeometryNodes.append(node)
        }

        guard !invalidGeometry,
              Set(geometryByNodeID.keys) == Set(descriptorIDs) else {
            return nil
        }

        var boundHoldNodes: [String: [SCNNode]] = [:]
        var boundHoldIDsByNode: [ObjectIdentifier: String] = [:]
        var originals: [ObjectIdentifier: [SCNMaterial]] = [:]
        for (nodeID, node) in geometryByNodeID {
            guard let binding = descriptorsByNodeID[nodeID] else { return nil }
            switch binding.role {
            case .body:
                guard binding.holdID == nil else { return nil }
            case .hold:
                guard let holdID = binding.holdID, !holdID.isEmpty else { return nil }
                boundHoldNodes[holdID, default: []].append(node)
                boundHoldIDsByNode[ObjectIdentifier(node)] = holdID
                originals[ObjectIdentifier(node)] = node.geometry?.materials
            }
        }

        guard Set(boundHoldNodes.keys) == Set(descriptor.holds.keys),
              descriptor.holds.allSatisfy({ holdID, hold in
                  Set(hold.nodeIDs) == Set(
                      descriptor.nodes.compactMap { node in
                          node.role == .hold && node.holdID == holdID ? node.nodeID : nil
                      }
                  )
              }) else {
            return nil
        }

        geometryNodes = clonedGeometryNodes
        holdNodes = boundHoldNodes
        holdIDsByNode = boundHoldIDsByNode
        originalMaterials = originals
        scene.rootNode.addChildNode(modelRoot)
        configureCameraAndLighting()
    }

    func holdID(for node: SCNNode) -> String? {
        var candidate: SCNNode? = node
        while let current = candidate {
            if let holdID = holdIDsByNode[ObjectIdentifier(current)] { return holdID }
            candidate = current.parent
        }
        return nil
    }

    func frame(in size: CGSize) {
        guard size.width > 0, size.height > 0 else { return }
        camera.camera?.orthographicScale = max(0.085, 0.335 * size.height / size.width)
    }

    func highlight(_ ids: Set<String>, mode: BoardHighlightMode) {
        let validIDs = ids.intersection(Set(holdNodes.keys))
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

    private static func nodeID(for node: SCNNode, beneath root: SCNNode) -> String? {
        var names: [String] = []
        var candidate: SCNNode? = node
        while let current = candidate, current !== root {
            guard let name = current.name, !name.isEmpty, !name.contains("/") else { return nil }
            names.append(name)
            candidate = current.parent
        }
        guard candidate === root else { return nil }
        return names.reversed().joined(separator: "/")
    }

    private func configureCameraAndLighting() {
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
}

private struct BoardModelView: UIViewRepresentable {
    let model: BoardModelScene
    let boardName: String
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
        view.boardName = boardName
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
    var boardName = "hangboard"
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
        DispatchQueue.main.async { [weak self] in
            guard let self, self.needsAccessibilityProjection else { return }
            self.needsAccessibilityProjection = false
            self.updateAccessibility()
        }
    }

    @objc func selectHold(_ recognizer: UITapGestureRecognizer) {
        // CPU-only nearest-hit regressions require this commit before SceneKit
        // traverses newly cloned geometry.
        SCNTransaction.flush()
        guard let model,
              let hit = hitTest(recognizer.location(in: self), options: [.searchMode: SCNHitTestSearchMode.closest.rawValue]).first,
              let id = model.holdID(for: hit.node),
              let hold = holds.first(where: { $0.id == id }) else { return }
        onHoldTap?(hold)
    }

    func updateAccessibility() {
        guard let onHoldTap, let model else {
            isAccessibilityElement = true
            accessibilityLabel = "\(boardName) hangboard"
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
