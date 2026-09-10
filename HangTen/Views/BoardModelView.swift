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
        return BoardModelScene(
            source: source,
            descriptor: media.descriptor,
            display: media.display,
            suspension: media.suspension
        )
    }
}

/// A model media surface never receives a raster view. Callers must route
/// raster and model presentations exhaustively before constructing this view.
struct BoardModelSurface: View {
    enum ResultState {
        case loading
        case ready(BoardModelScene)
        case unavailable
    }

    let board: TrainingBoard
    let presentation: BoardPresentation
    let positionID: String?
    let highlightedHoldIDs: Set<String>
    let highlightMode: BoardHighlightMode
    let onHoldTap: ((BoardHold) -> Void)?
    @State private var result: ResultState = .loading

    init(
        board: TrainingBoard,
        presentation: BoardPresentation,
        positionID: String? = nil,
        highlightedHoldIDs: Set<String>,
        highlightMode: BoardHighlightMode,
        onHoldTap: ((BoardHold) -> Void)?
    ) {
        self.board = board
        self.presentation = presentation
        self.positionID = positionID
        self.highlightedHoldIDs = highlightedHoldIDs
        self.highlightMode = highlightMode
        self.onHoldTap = onHoldTap
    }

    enum DisplayState: Equatable {
        case loading
        case ready
        case unavailable
    }

    static func permitsHoldSelection(
        for state: DisplayState,
        onHoldTap: ((BoardHold) -> Void)?
    ) -> Bool {
        state == .ready && onHoldTap != nil
    }

    var body: some View {
        Group {
            if case .ready(let model) = result {
                BoardModelView(
                    model: model,
                    boardName: board.name,
                    holds: board.holds(in: presentation),
                    positionID: positionID,
                    highlightedHoldIDs: highlightedHoldIDs,
                    highlightMode: highlightMode,
                    onHoldTap: onHoldTap,
                    onUnavailable: { result = .unavailable }
                )
                .accessibilityIdentifier("boardModel.3d")
                .allowsHitTesting(Self.permitsHoldSelection(for: .ready, onHoldTap: onHoldTap))
            } else if case .loading = result {
                ProgressView()
                    .accessibilityHidden(true)
                    .allowsHitTesting(false)
            } else {
                BoardModelUnavailableView()
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

@MainActor
final class BoardModelScene {
    static let modelPickCategory = 1
    static let cordCategory = 2

    let scene = SCNScene()
    let camera = SCNNode()
    let geometryNodes: [SCNNode]
    private(set) var boardTransform: simd_float4x4
    private let boardContainer: SCNNode
    private let descriptor: BoardModelDescriptor
    private let suspension: BoardModelSuspension?
    private let geometryByNodeID: [String: SCNNode]
    private let attachmentNodeIDs: Set<String>
    private let projectedWidth: Float
    private let projectedHeight: Float
    private let fitPadding: Float
    private(set) var holdNodes: [String: [SCNNode]] = [:]
    private var holdIDsByNode: [ObjectIdentifier: String] = [:]
    private var originalMaterials: [ObjectIdentifier: [SCNMaterial]] = [:]
    private var lastHighlights: Set<String> = []
    private var lastMode: BoardHighlightMode?
    private var canonicalFraming: SuspendedCameraFraming?
    private var currentFraming: SuspendedCameraFraming?
    private var orbitAzimuth: Float = 0
    private var orbitElevation: Float = 0
    private var orbitZoom: Float = 1
    private var viewportSize: CGSize = .zero
    private(set) var activePositionID: String?
    private(set) var transformedAttachment = SIMD3<Float>.zero
    private(set) var transientCordNode: SCNNode?
    private(set) var isUnavailable = false
    private(set) var isTransientCordAccessible = false

    init?(
        source: SCNScene,
        descriptor: BoardModelDescriptor,
        display: BoardModelDisplay,
        suspension: BoardModelSuspension? = nil
    ) {
        let modelRoot = source.rootNode.clone()
        let descriptorIDs = descriptor.nodes.map(\.nodeID)
        guard !descriptorIDs.isEmpty,
              Set(descriptorIDs).count == descriptorIDs.count,
              Set(descriptorIDs).count == descriptor.nodes.count else {
            return nil
        }

        let descriptorsByNodeID = Dictionary(uniqueKeysWithValues: descriptor.nodes.map { ($0.nodeID, $0) })
        guard descriptorsByNodeID.count == descriptor.nodes.count else { return nil }
        // USD import may preserve exporter Xforms above meshes. Descriptors
        // with bare IDs bind exact unique mesh names; path descriptors retain
        // exact hierarchy-path matching.
        let usesBareImporterNodeIDs = descriptorIDs.allSatisfy { !$0.contains("/") }

        // The cloned imported root is rendered with the scene. It therefore
        // cannot carry a mesh that lies outside the descriptor node inventory.
        guard modelRoot.geometry == nil else { return nil }

        var geometryByNodeID: [String: SCNNode] = [:]
        var clonedGeometryNodes: [SCNNode] = []
        var invalidGeometry = false
        modelRoot.enumerateChildNodes { node, _ in
            guard let geometry = node.geometry else { return }
            let nodeID = usesBareImporterNodeIDs
                ? Self.bareImporterNodeID(for: node)
                : Self.nodeID(for: node, beneath: modelRoot)
            guard let nodeID,
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
            case .attachment:
                guard binding.holdID == nil else { return nil }
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
        self.descriptor = descriptor
        self.suspension = suspension
        self.geometryByNodeID = geometryByNodeID
        self.attachmentNodeIDs = Set(descriptor.nodes.compactMap {
            $0.role == .attachment ? $0.nodeID : nil
        })
        holdNodes = boundHoldNodes
        holdIDsByNode = boundHoldIDsByNode
        originalMaterials = originals
        guard let framing = Self.framing(descriptor: descriptor, display: display) else {
            return nil
        }
        projectedWidth = framing.width
        projectedHeight = framing.height
        fitPadding = framing.padding
        boardTransform = matrix_identity_float4x4
        let modelContainer = SCNNode()
        modelContainer.name = "board.model"
        modelContainer.addChildNode(modelRoot)
        scene.rootNode.addChildNode(modelContainer)
        boardContainer = modelContainer
        for node in clonedGeometryNodes {
            node.categoryBitMask = Self.modelPickCategory
        }
        configureCameraAndLighting(framing: framing)
    }

    func holdID(for node: SCNNode) -> String? {
        var candidate: SCNNode? = node
        while let current = candidate {
            if let holdID = holdIDsByNode[ObjectIdentifier(current)] { return holdID }
            candidate = current.parent
        }
        return nil
    }

    @discardableResult
    func select(positionID: String?) -> Bool {
        guard let suspension else {
            activePositionID = positionID
            isUnavailable = false
            return true
        }
        guard let positionID,
              let pose = suspension.canonicalPoses[positionID],
              attachmentNodeIDs.contains(suspension.attachment.nodeID),
              let binding = descriptor.nodes.first(where: { $0.nodeID == suspension.attachment.nodeID }),
              binding.role == .attachment else {
            enterUnavailable()
            return false
        }

        do {
            let solved = try SuspendedBoardPresentation.solve(
                pose: pose,
                suspension: suspension,
                bounds: descriptor.modelBounds
            )
            boardContainer.simdTransform = solved.boardTransform
            boardTransform = solved.boardTransform
            transformedAttachment = solved.transformedAttachment
            guard hasClearance(for: solved) else {
                enterUnavailable()
                return false
            }
            let cord = makeCordNode(for: solved)
            transientCordNode?.removeFromParentNode()
            transientCordNode = cord
            scene.rootNode.addChildNode(cord)
            isTransientCordAccessible = false
            canonicalFraming = solved.cameraFraming
            currentFraming = solved.cameraFraming
            activePositionID = positionID
            isUnavailable = false
            resetCamera(animated: true)
            return true
        } catch {
            enterUnavailable()
            return false
        }
    }

    func orbit(azimuth: Float, elevation: Float, zoomScale: Float = 1) {
        guard let framing = canonicalFraming,
              azimuth.isFinite, elevation.isFinite,
              zoomScale.isFinite, zoomScale > 0 else { return }
        orbitAzimuth = min(max(orbitAzimuth + azimuth, -0.9), 0.9)
        orbitElevation = min(max(orbitElevation + elevation, -0.55), 0.55)
        orbitZoom = min(max(orbitZoom * zoomScale, 0.75), 1.35)
        let baseOffset = -framing.direction * framing.distance
        let yaw = simd_quatf(angle: orbitAzimuth, axis: SIMD3<Float>(0, 1, 0))
        let pitchAxis = framing.right
        let pitch = simd_quatf(angle: orbitElevation, axis: pitchAxis)
        let offset = (pitch * yaw).act(baseOffset)
        let distance = max(0.01, framing.distance / orbitZoom)
        let normalizedOffset = simd_length(offset) > 1e-6
            ? simd_normalize(offset) * distance
            : baseOffset
        let position = framing.target + normalizedOffset
        camera.position = SCNVector3(position)
        camera.camera?.orthographicScale = Double(cameraScale(for: framing) / orbitZoom)
        camera.look(at: SCNVector3(framing.target), up: SCNVector3(framing.up), localFront: SCNVector3(0, 0, -1))
        currentFraming = framing
    }

    func resetCamera(animated: Bool) {
        guard let framing = canonicalFraming ?? currentFraming else { return }
        let apply = {
            self.orbitAzimuth = 0
            self.orbitElevation = 0
            self.orbitZoom = 1
            self.camera.position = SCNVector3(framing.target - framing.direction * framing.distance)
            self.camera.camera?.orthographicScale = Double(self.cameraScale(for: framing))
            self.camera.look(at: SCNVector3(framing.target), up: SCNVector3(framing.up), localFront: SCNVector3(0, 0, -1))
            self.currentFraming = framing
        }
        if animated {
            SCNTransaction.begin()
            SCNTransaction.animationDuration = 0.18
            apply()
            SCNTransaction.commit()
        } else {
            SCNTransaction.begin()
            SCNTransaction.animationDuration = 0
            SCNTransaction.disableActions = true
            apply()
            SCNTransaction.commit()
        }
    }

    private func cameraScale(for framing: SuspendedCameraFraming) -> Float {
        let aspect = viewportSize.width > 0 && viewportSize.height > 0
            ? Float(viewportSize.width / viewportSize.height)
            : 1
        return max(framing.height, framing.width / aspect) * framing.fitPadding
    }

    private func enterUnavailable() {
        transientCordNode?.removeFromParentNode()
        transientCordNode = nil
        isTransientCordAccessible = false
        isUnavailable = true
        activePositionID = nil
    }

    private func makeCordNode(for solved: SuspendedSolvedPresentation) -> SCNNode {
        let root = SCNNode()
        root.name = "suspended.cord"
        root.categoryBitMask = Self.cordCategory
        for (index, points) in zip(solved.centerlineSamples, solved.centerlineSamples.dropFirst()).enumerated() {
            let start = points.0
            let end = points.1
            let direction = end - start
            let length = simd_length(direction)
            guard length.isFinite, length > 1e-7 else { continue }
            let geometry = SCNCylinder(radius: CGFloat(solved.tubeRadius), height: CGFloat(length))
            let material = SCNMaterial()
            material.diffuse.contents = UIColor(white: 0.08, alpha: 1)
            material.roughness.contents = 0.8
            geometry.firstMaterial = material
            let segment = SCNNode(geometry: geometry)
            segment.name = "suspended.cord.segment.\(index)"
            segment.categoryBitMask = Self.cordCategory
            segment.position = SCNVector3((start + end) / 2)
            segment.simdOrientation = simd_quatf(
                from: SIMD3<Float>(0, 1, 0),
                to: simd_normalize(direction)
            )
            root.addChildNode(segment)
        }
        return root
    }

    private func hasClearance(for solved: SuspendedSolvedPresentation) -> Bool {
        guard solved.centerlineSamples.count >= 2 else { return false }
        let options: [String: Any] = [
            SCNHitTestOption.categoryBitMask.rawValue: Self.modelPickCategory,
            SCNHitTestOption.searchMode.rawValue: SCNHitTestSearchMode.closest.rawValue
        ]
        for (index, points) in zip(solved.centerlineSamples, solved.centerlineSamples.dropFirst()).enumerated() {
            let start = points.0
            let end = points.1
            let hits = scene.rootNode.hitTestWithSegment(
                from: SCNVector3(start),
                to: SCNVector3(end),
                options: options
            )
            for hit in hits {
                let nodeID = nodeID(for: hit.node)
                let isAttachmentInterface = index == solved.centerlineSamples.count - 2
                    && nodeID == suspension?.attachment.nodeID
                if !isAttachmentInterface { return false }
            }
        }
        return true
    }

    private func nodeID(for node: SCNNode) -> String? {
        var candidate: SCNNode? = node
        while let current = candidate {
            if let match = geometryByNodeID.first(where: { $0.value === current }) { return match.key }
            candidate = current.parent
        }
        return nil
    }

    func frame(in size: CGSize) {
        guard size.width > 0, size.height > 0 else { return }
        viewportSize = size
        let aspect = Float(size.width / size.height)
        if let framing = currentFraming {
            camera.camera?.orthographicScale = Double(max(framing.height, framing.width / aspect) * framing.fitPadding)
        } else {
            camera.camera?.orthographicScale = Double(max(projectedHeight, projectedWidth / aspect) * fitPadding)
        }
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

    private static func bareImporterNodeID(for node: SCNNode) -> String? {
        guard let name = node.name, !name.isEmpty, !name.contains("/") else { return nil }
        return name
    }

    private struct Framing {
        let target: SCNVector3
        let direction: SCNVector3
        let up: SCNVector3
        let distance: Float
        let width: Float
        let height: Float
        let padding: Float
    }

    private static func framing(
        descriptor: BoardModelDescriptor,
        display: BoardModelDisplay
    ) -> Framing? {
        let minimum = descriptor.modelBounds.minimum
        let maximum = descriptor.modelBounds.maximum
        let camera = display.camera
        guard minimum.count == 3,
              maximum.count == 3,
              camera.type == "orthographic",
              camera.viewDirection.count == 3,
              camera.up.count == 3,
              camera.fitPadding.isFinite,
              camera.fitPadding > 0,
              minimum.allSatisfy(\.isFinite),
              maximum.allSatisfy(\.isFinite),
              camera.viewDirection.allSatisfy(\.isFinite),
              camera.up.allSatisfy(\.isFinite) else {
            return nil
        }
        let minimumVector = SCNVector3(minimum[0], minimum[1], minimum[2])
        let maximumVector = SCNVector3(maximum[0], maximum[1], maximum[2])
        let target = (minimumVector + maximumVector) / 2
        guard let direction = SCNVector3(camera.viewDirection).normalized(),
              let requestedUp = SCNVector3(camera.up).normalized(),
              let right = direction.cross(requestedUp).normalized() else {
            return nil
        }
        let up = right.cross(direction)
        let corners = [minimumVector.x, maximumVector.x].flatMap { x in
            [minimumVector.y, maximumVector.y].flatMap { y in
                [minimumVector.z, maximumVector.z].map { z in SCNVector3(x, y, z) }
            }
        }
        let horizontal = corners.map { ($0 - target).dot(right) }
        let vertical = corners.map { ($0 - target).dot(up) }
        let depth = corners.map { ($0 - target).dot(direction) }
        guard let width = horizontal.max().flatMap({ maximum in horizontal.min().map { maximum - $0 } }),
              let height = vertical.max().flatMap({ maximum in vertical.min().map { maximum - $0 } }),
              let depthSpan = depth.max().flatMap({ maximum in depth.min().map { maximum - $0 } }),
              width.isFinite, height.isFinite, depthSpan.isFinite,
              width > 0, height > 0 else {
            return nil
        }
        let fitPadding = Float(1 + camera.fitPadding * 2)
        let distance = max(width, height, depthSpan) * fitPadding
        return Framing(
            target: target,
            direction: direction,
            up: up,
            distance: distance,
            width: width,
            height: height,
            padding: fitPadding
        )
    }

    private func configureCameraAndLighting(framing: Framing) {
        camera.camera = SCNCamera()
        camera.camera?.usesOrthographicProjection = true
        camera.camera?.zNear = 0.01
        camera.camera?.zFar = 10
        camera.camera?.wantsHDR = false
        camera.camera?.screenSpaceAmbientOcclusionIntensity = 0.7
        camera.camera?.screenSpaceAmbientOcclusionRadius = 0.018
        camera.camera?.screenSpaceAmbientOcclusionBias = 0.001
        camera.camera?.screenSpaceAmbientOcclusionDepthThreshold = 0.03
        camera.position = framing.target - framing.direction * framing.distance
        camera.look(at: framing.target, up: framing.up, localFront: SCNVector3(0, 0, -1))
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
        key.position = camera.position + framing.up * framing.height
        key.look(at: framing.target, up: framing.up, localFront: SCNVector3(0, 0, -1))
        scene.rootNode.addChildNode(key)
    }
}

private extension SCNVector3 {
    init(_ value: SIMD3<Float>) {
        self.init(value.x, value.y, value.z)
    }

    init(_ values: [Double]) {
        self.init(Float(values[0]), Float(values[1]), Float(values[2]))
    }

    static func + (lhs: SCNVector3, rhs: SCNVector3) -> SCNVector3 {
        SCNVector3(lhs.x + rhs.x, lhs.y + rhs.y, lhs.z + rhs.z)
    }

    static func - (lhs: SCNVector3, rhs: SCNVector3) -> SCNVector3 {
        SCNVector3(lhs.x - rhs.x, lhs.y - rhs.y, lhs.z - rhs.z)
    }

    static func * (lhs: SCNVector3, rhs: Float) -> SCNVector3 {
        SCNVector3(lhs.x * rhs, lhs.y * rhs, lhs.z * rhs)
    }

    static func / (lhs: SCNVector3, rhs: Float) -> SCNVector3 {
        SCNVector3(lhs.x / rhs, lhs.y / rhs, lhs.z / rhs)
    }

    func dot(_ other: SCNVector3) -> Float {
        x * other.x + y * other.y + z * other.z
    }

    func cross(_ other: SCNVector3) -> SCNVector3 {
        SCNVector3(
            y * other.z - z * other.y,
            z * other.x - x * other.z,
            x * other.y - y * other.x
        )
    }

    func normalized() -> SCNVector3? {
        let length = sqrt(dot(self))
        guard length.isFinite, length > 0 else { return nil }
        return self / length
    }
}

private struct BoardModelView: UIViewRepresentable {
    let model: BoardModelScene
    let boardName: String
    let holds: [BoardHold]
    let positionID: String?
    let highlightedHoldIDs: Set<String>
    let highlightMode: BoardHighlightMode
    let onHoldTap: ((BoardHold) -> Void)?
    let onUnavailable: (() -> Void)?

    func makeUIView(context: Context) -> BoardModelSCNView {
        let view = BoardModelSCNView()
        view.backgroundColor = .clear
        view.isOpaque = false
        view.antialiasingMode = .multisampling4X
        view.rendersContinuously = false
        view.isPlaying = false
        view.allowsCameraControl = false
        view.display(model)
        view.onUnavailable = onUnavailable
        view.positionID = positionID
        view.delegate = view
        view.addGestureRecognizer(UITapGestureRecognizer(target: view, action: #selector(view.selectHold(_:))))
        view.addGestureRecognizer(UIPanGestureRecognizer(target: view, action: #selector(view.orbitPan(_:))))
        view.addGestureRecognizer(UIPinchGestureRecognizer(target: view, action: #selector(view.orbitPinch(_:))))
        view.selectPositionIfNeeded()
        return view
    }

    func updateUIView(_ view: BoardModelSCNView, context: Context) {
        view.display(model)
        view.boardName = boardName
        view.holds = holds
        view.positionID = positionID
        view.onHoldTap = onHoldTap
        view.onUnavailable = onUnavailable
        view.highlightedHoldIDs = highlightedHoldIDs
        view.isUserInteractionEnabled = onHoldTap != nil
        view.needsAccessibilityProjection = true
        model.highlight(highlightedHoldIDs, mode: highlightMode)
        view.selectPositionIfNeeded()
        view.updateAccessibility()
    }

    static func dismantleUIView(_ view: BoardModelSCNView, coordinator: ()) {
        view.onHoldTap = nil
        view.onUnavailable = nil
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
    var onUnavailable: (() -> Void)?
    var positionID: String?
    var needsAccessibilityProjection = true
    private var didSelectPosition = false
    private var holdAccessibilityElements: [String: BoardModelAccessibilityElement] = [:]
    private var accessibilityHoldIDs: [String] = []

    func display(_ model: BoardModelScene) {
        guard self.model !== model else { return }
        self.model = model
        didSelectPosition = false
        scene = model.scene
        pointOfView = model.camera
        model.frame(in: bounds.size)
        needsAccessibilityProjection = true
    }

    func selectPositionIfNeeded() {
        guard let model else { return }
        guard !didSelectPosition || model.activePositionID != positionID else { return }
        didSelectPosition = true
        guard model.select(positionID: positionID) else {
            onUnavailable?()
            return
        }
        scene = model.scene
        pointOfView = model.camera
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
              let hit = hitTest(recognizer.location(in: self), options: [
                  SCNHitTestOption.categoryBitMask: BoardModelScene.modelPickCategory,
                  SCNHitTestOption.searchMode: SCNHitTestSearchMode.closest.rawValue
              ]).first,
              let id = model.holdID(for: hit.node),
              let hold = holds.first(where: { $0.id == id }) else { return }
        onHoldTap?(hold)
        _ = model.select(positionID: model.activePositionID)
        model.resetCamera(animated: true)
    }

    @objc func orbitPan(_ recognizer: UIPanGestureRecognizer) {
        guard let model, recognizer.state == .changed else { return }
        let translation = recognizer.translation(in: self)
        let width = max(bounds.width, 1)
        let height = max(bounds.height, 1)
        model.orbit(
            azimuth: Float(-translation.x / width) * 0.9,
            elevation: Float(-translation.y / height) * 0.65
        )
        recognizer.setTranslation(.zero, in: self)
    }

    @objc func orbitPinch(_ recognizer: UIPinchGestureRecognizer) {
        guard let model, recognizer.state == .changed else { return }
        model.orbit(azimuth: 0, elevation: 0, zoomScale: Float(recognizer.scale))
        recognizer.scale = 1
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
