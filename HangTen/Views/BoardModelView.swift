import SceneKit
import SwiftUI

/// Identity for a decoded package model. The hash makes replacement assets a
/// distinct cached source even when a board keeps the same presentation ID.
struct BoardModelKey: Hashable {
    let boardID: String
    let presentationID: String
    let modelSHA256: String
}

enum BoardModelSolvedSuspension {
    case single(SuspendedSolvedPresentation)
    case twoBranch(SuspendedTwoBranchSolvedPresentation)

    var boardTransform: simd_float4x4 {
        switch self {
        case .single(let solved): solved.boardTransform
        case .twoBranch(let solved): solved.boardTransform
        }
    }

    var cameraFraming: SuspendedCameraFraming {
        switch self {
        case .single(let solved): solved.cameraFraming
        case .twoBranch(let solved): solved.cameraFraming
        }
    }
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
            suspension: media.suspension,
            orientation: media.orientation,
            allowedPositionIDs: Set(board.positions.filter {
                $0.presentationID == presentation.id
            }.map(\.id))
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
    static let canonicalTransitionDuration: CFTimeInterval = 0.18

    let scene = SCNScene()
    let camera = SCNNode()
    let geometryNodes: [SCNNode]
    private(set) var boardTransform: simd_float4x4
    private(set) var boardContainer: SCNNode
    private let descriptor: BoardModelDescriptor
    private let display: BoardModelDisplay
    private let suspension: BoardModelSuspension?
    private let orientation: BoardModelOrientation?
    private let geometryByNodeID: [String: SCNNode]
    private let projectedWidth: Float
    private let projectedHeight: Float
    private(set) var holdNodes: [String: [SCNNode]] = [:]
    private var holdIDsByNode: [ObjectIdentifier: String] = [:]
    private var originalMaterials: [ObjectIdentifier: [SCNMaterial]] = [:]
    private var lastHighlights: Set<String> = []
    private var lastMode: BoardHighlightMode?
    private var canonicalFraming: SuspendedCameraFraming?
    private var currentFraming: SuspendedCameraFraming?
    // Descriptor, geometry and suspension are immutable for this scene instance.
    // Keep successful pose/clearance results and cord nodes across highlight updates.
    private var verifiedPresentations: [String: (BoardModelSolvedSuspension, SCNNode)] = [:]
    private var orbitAzimuth: Float = 0
    private var orbitElevation: Float = 0
    private var orbitZoom: Float = 1
    private var viewportSize: CGSize = .zero
    private(set) var activePositionID: String?
    private(set) var transformedAttachment = SIMD3<Float>.zero
    private(set) var transientCordNode: SCNNode?
    private(set) var isUnavailable = false
    private(set) var isTransientCordAccessible = false
    private let allowedPositionIDs: Set<String>

    init?(
        source: SCNScene,
        descriptor: BoardModelDescriptor,
        display: BoardModelDisplay,
        suspension: BoardModelSuspension? = nil,
        orientation: BoardModelOrientation? = nil,
        allowedPositionIDs: Set<String>? = nil
    ) {
        guard !(suspension != nil && orientation != nil) else { return nil }
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
        self.display = display
        self.suspension = suspension
        self.orientation = orientation
        self.allowedPositionIDs = allowedPositionIDs
            ?? orientation.map { Set($0.rotations.keys) }
            ?? suspension.map { Set($0.canonicalPoses.keys) }
            ?? []
        self.geometryByNodeID = geometryByNodeID
        holdNodes = boundHoldNodes
        holdIDsByNode = boundHoldIDsByNode
        originalMaterials = originals
        guard let framing = Self.framing(descriptor: descriptor, display: display) else {
            return nil
        }
        projectedWidth = framing.width
        projectedHeight = framing.height
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
        guard let positionID, allowedPositionIDs.contains(positionID) else {
            enterUnavailable()
            return false
        }
        if let orientation {
            guard let components = orientation.rotations[positionID],
                  orientation.pivot == "modelBoundsCenter",
                  let quaternion = Self.quaternion(from: components) else {
                enterUnavailable()
                return false
            }
            let pivot = Self.boundsCenter(descriptor.modelBounds)
            let rotatedCorners = Self.rotatedCorners(
                descriptor.modelBounds,
                by: quaternion,
                pivot: pivot
            )
            guard let framing = Self.framing(points: rotatedCorners, display: display) else {
                enterUnavailable()
                return false
            }
            transitionToOrientation(
                transform: Self.transform(rotating: quaternion, about: pivot),
                framing: framing
            )
            canonicalFraming = framing
            activePositionID = positionID
            isUnavailable = false
            return true
        }
        guard let suspension else {
            guard let framing = Self.framing(descriptor: descriptor, display: display) else {
                enterUnavailable()
                return false
            }
            // Preserve the existing fixed-board camera scale exactly while
            // making its canonical pose available to orbit/reset gestures.
            // Fixed models do not receive an orientation transition.
            canonicalFraming = Self.fixedFraming(from: framing)
            currentFraming = canonicalFraming
            activePositionID = positionID
            isUnavailable = false
            return true
        }
        guard let pose = suspension.canonicalPoses[positionID],
              hasDeclaredAttachmentBindings(for: suspension) else {
            enterUnavailable()
            return false
        }

        do {
            let solved: BoardModelSolvedSuspension
            let cord: SCNNode
            if let cached = verifiedPresentations[positionID] {
                (solved, cord) = cached
            } else {
                solved = try Self.solveSuspension(
                    pose: pose, suspension: suspension, bounds: descriptor.modelBounds
                )
                guard hasClearance(for: solved) else {
                    enterUnavailable()
                    return false
                }
                cord = makeCordNode(for: solved)
                verifiedPresentations[positionID] = (solved, cord)
            }
            transitionToCanonicalPresentation(solved, cord: cord)
            canonicalFraming = solved.cameraFraming
            activePositionID = positionID
            isUnavailable = false
            return true
        } catch {
            enterUnavailable()
            return false
        }
    }

    private func hasDeclaredAttachmentBindings(for suspension: BoardModelSuspension) -> Bool {
        let nodeIDs: [String]
        switch suspension {
        case .singleCord(let single):
            nodeIDs = [single.attachment.nodeID]
        case .twoBranchCord(let twoBranch):
            nodeIDs = (twoBranch.passages.left + twoBranch.passages.right).map(\.nodeID)
            guard nodeIDs.count == 4 else { return false }
        }
        return nodeIDs.allSatisfy { nodeID in
            guard let binding = descriptor.nodes.first(where: { $0.nodeID == nodeID }) else {
                return false
            }
            return (binding.role == .body || binding.role == .attachment)
                && geometryByNodeID[nodeID] != nil
        }
    }

    static func solveSuspension(
        pose: BoardModelCanonicalPose,
        suspension: BoardModelSuspension,
        bounds: BoardModelBounds
    ) throws -> BoardModelSolvedSuspension {
        switch suspension {
        case .singleCord(let single):
            return .single(try SuspendedBoardPresentation.solve(
                pose: pose, suspension: .singleCord(single), bounds: bounds
            ))
        case .twoBranchCord(let twoBranch):
            return .twoBranch(try SuspendedBoardPresentation.solve(
                pose: pose, suspension: twoBranch, bounds: bounds
            ))
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
            self.applyCanonicalCamera(framing)
        }
        if animated {
            SCNTransaction.begin()
            SCNTransaction.animationDuration = Self.canonicalTransitionDuration
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
        return max(framing.height, framing.width / aspect) * framing.fitPadding / 2
    }

    private func enterUnavailable() {
        transientCordNode?.removeFromParentNode()
        transientCordNode = nil
        isTransientCordAccessible = false
        isUnavailable = true
        activePositionID = nil
    }

    private func transitionToCanonicalPresentation(
        _ solved: BoardModelSolvedSuspension,
        cord: SCNNode
    ) {
        // Commit the board, destination-solved cord, and camera together.
        // Cached cords are detached before reuse, so no visible frame can
        // combine the destination cord with the previous board transform.
        SCNTransaction.begin()
        SCNTransaction.disableActions = true
        transientCordNode?.removeFromParentNode()
        transientCordNode = cord
        scene.rootNode.addChildNode(cord)
        isTransientCordAccessible = false
        boardContainer.simdTransform = solved.boardTransform
        applyCanonicalCamera(solved.cameraFraming)
        SCNTransaction.commit()

        boardTransform = solved.boardTransform
        if case .single(let single) = solved {
            transformedAttachment = single.transformedAttachment
        }
        currentFraming = solved.cameraFraming
    }

    private func transitionToOrientation(
        transform: simd_float4x4,
        framing: SuspendedCameraFraming
    ) {
        transientCordNode?.removeFromParentNode()
        transientCordNode = nil
        isTransientCordAccessible = false
        transformedAttachment = .zero

        let boardMoves = !Self.transformsMatch(boardTransform, transform)
        if !boardMoves {
            boardContainer.simdTransform = transform
        }
        SCNTransaction.begin()
        SCNTransaction.animationDuration = Self.canonicalTransitionDuration
        if boardMoves {
            boardContainer.simdTransform = transform
        }
        applyCanonicalCamera(framing)
        SCNTransaction.commit()

        boardTransform = transform
        currentFraming = framing
    }

    private static func transformsMatch(
        _ lhs: simd_float4x4,
        _ rhs: simd_float4x4,
        tolerance: Float = 1e-6
    ) -> Bool {
        for column in 0..<4 {
            for row in 0..<4 where abs(lhs[column][row] - rhs[column][row]) > tolerance {
                return false
            }
        }
        return true
    }

    private func applyCanonicalCamera(_ framing: SuspendedCameraFraming) {
        orbitAzimuth = 0
        orbitElevation = 0
        orbitZoom = 1
        camera.position = SCNVector3(framing.target - framing.direction * framing.distance)
        camera.camera?.orthographicScale = Double(cameraScale(for: framing))
        camera.look(at: SCNVector3(framing.target), up: SCNVector3(framing.up), localFront: SCNVector3(0, 0, -1))
        currentFraming = framing
    }

    private func makeCordNode(for solved: BoardModelSolvedSuspension) -> SCNNode {
        let root = SCNNode()
        root.name = "suspended.cord"
        root.categoryBitMask = Self.cordCategory
        let paths: [([SIMD3<Float>], Float)]
        switch solved {
        case .single(let single):
            paths = [(single.centerlineSamples, single.tubeRadius)]
        case .twoBranch(let twoBranch):
            paths = twoBranch.branches.map { ($0.centerlineSamples, twoBranch.tubeRadius) }
        }
        for (branchIndex, path) in paths.enumerated() {
            for (index, points) in zip(path.0, path.0.dropFirst()).enumerated() {
                let start = points.0
                let end = points.1
                let direction = end - start
                let length = simd_length(direction)
                guard length.isFinite, length > 1e-7 else { continue }
                let geometry = SCNCylinder(radius: CGFloat(path.1), height: CGFloat(length))
                let material = SCNMaterial()
                material.diffuse.contents = UIColor(white: 0.08, alpha: 1)
                material.roughness.contents = 0.8
                geometry.firstMaterial = material
                let segment = SCNNode(geometry: geometry)
                segment.name = "suspended.cord.branch.\(branchIndex).segment.\(index)"
                segment.categoryBitMask = Self.cordCategory
                segment.position = SCNVector3((start + end) / 2)
                segment.simdOrientation = simd_quatf(
                    from: SIMD3<Float>(0, 1, 0),
                    to: simd_normalize(direction)
                )
                root.addChildNode(segment)
            }
        }
        return root
    }

    private func hasClearance(for solved: BoardModelSolvedSuspension) -> Bool {
        struct IntentionalContact {
            let pathIndex: Int
            let segmentIndex: Int
            let segmentParameter: Float
            let nodeID: String
            let point: SIMD3<Float>
        }
        let paths: [[SIMD3<Float>]]
        let clearanceRadius: Float
        let intentionalContacts: [IntentionalContact]
        // Only the explicitly authored bearing/bore interval may touch its
        // bound nonselectable body. Free spans and all holds keep full clearance.
        var bearingIntervals: [(path: Int, segments: Range<Int>, nodes: Set<String>, radius: Float)] = []
        switch solved {
        case .single(let single):
            guard case .some(.singleCord(let singleSuspension)) = suspension else { return false }
            paths = [single.centerlineSamples]
            clearanceRadius = single.requiredClearance
            intentionalContacts = [IntentionalContact(
                pathIndex: 0,
                segmentIndex: single.centerlineSamples.count - 2,
                segmentParameter: 1,
                nodeID: singleSuspension.attachment.nodeID,
                point: single.transformedAttachment
            )]
        case .twoBranch(let twoBranch):
            paths = twoBranch.branches.map(\.centerlineSamples)
            clearanceRadius = twoBranch.requiredClearance
            guard case .some(.twoBranchCord(let twoBranchSuspension)) = suspension else { return false }
            let transform = twoBranch.boardTransform
            let passagePairs = [twoBranchSuspension.passages.left, twoBranchSuspension.passages.right]
            for (index, passages) in passagePairs.enumerated() where passages.allSatisfy(\.isThroughBore) {
                let branch = twoBranch.branches[index]
                guard branch.spans.count == 3 else { return false }
                let start = branch.spans[0].count - 1
                bearingIntervals.append((index, start..<(start + branch.spans[1].count - 1), Set(passages.map(\.nodeID)), Float(twoBranchSuspension.branches[index].radius)))
            }
            intentionalContacts = passagePairs.enumerated().flatMap { pathIndex, passages in
                passages.enumerated().flatMap { passageIndex, passage -> [IntentionalContact] in
                    guard !passage.isThroughBore else { return [] }
                    let point = SIMD3<Float>(Float(passage.pointInModel[0]), Float(passage.pointInModel[1]), Float(passage.pointInModel[2]))
                    let transformed = transform * SIMD4<Float>(point.x, point.y, point.z, 1)
                    let worldPoint = SIMD3<Float>(transformed.x, transformed.y, transformed.z)
                    let joinIndex = SuspendedCordSolver.sampleCount - 1 + passageIndex
                    return [
                        IntentionalContact(pathIndex: pathIndex, segmentIndex: joinIndex - 1, segmentParameter: 1, nodeID: passage.nodeID, point: worldPoint),
                        IntentionalContact(pathIndex: pathIndex, segmentIndex: joinIndex, segmentParameter: 0, nodeID: passage.nodeID, point: worldPoint),
                    ]
                }
            }
        }
        guard paths.allSatisfy({ $0.count >= 2 }),
              clearanceRadius.isFinite, clearanceRadius > 0 else {
            return false
        }
        // The solver's required clearance already includes the cord radius
        // plus its additional separation. Measure mesh distance from the
        // centreline through that single contract, never as a ray.
        // Clearance is evaluated against the solved destination transform,
        // without committing that transform before the canonical transition.
        let previousTransform = boardContainer.simdTransform
        SCNTransaction.begin()
        SCNTransaction.disableActions = true
        boardContainer.simdTransform = solved.boardTransform
        defer {
            boardContainer.simdTransform = previousTransform
            SCNTransaction.commit()
        }

        for (nodeID, node) in geometryByNodeID {
            guard let geometry = node.geometry,
                  let triangles = Self.worldTriangles(for: geometry, node: node) else {
                return false
            }
            for (pathIndex, path) in paths.enumerated() {
                for (segmentIndex, points) in zip(path, path.dropFirst()).enumerated() {
                    let bearing = bearingIntervals.first {
                        $0.path == pathIndex && $0.segments.contains(segmentIndex) && $0.nodes.contains(nodeID)
                    }
                    let requiredDistance = bearing?.radius ?? clearanceRadius
                for triangle in triangles {
                    let approach = Self.closestApproach(
                        from: points.0,
                        to: points.1,
                        triangle: triangle
                    )
                    guard approach.distanceSquared.isFinite else { return false }
                    if approach.distanceSquared >= requiredDistance * requiredDistance { continue }
                    if intentionalContacts.contains(where: {
                        $0.pathIndex == pathIndex &&
                        $0.segmentIndex == segmentIndex &&
                        $0.nodeID == nodeID &&
                        abs(approach.segmentParameter - $0.segmentParameter) <= 1e-5 &&
                        simd_length(approach.trianglePoint - $0.point) <= 1e-5
                    }) {
                        continue
                    }
                    return false
                }
                }
            }
        }
        return true
    }

    private struct Triangle {
        let a: SIMD3<Float>
        let b: SIMD3<Float>
        let c: SIMD3<Float>
    }

    private struct TriangleApproach {
        let distanceSquared: Float
        let segmentParameter: Float
        let trianglePoint: SIMD3<Float>
    }

    private static func worldTriangles(for geometry: SCNGeometry, node: SCNNode) -> [Triangle]? {
        guard let sourceIndex = geometry.sources.firstIndex(where: { $0.semantic == .vertex }) else { return nil }
        let source = geometry.sources[sourceIndex]
        let vertexChannel: Int
        if let channels = geometry.geometrySourceChannels {
            guard channels.count == geometry.sources.count else { return nil }
            vertexChannel = channels[sourceIndex].intValue
        } else {
            vertexChannel = 0
        }
        guard vertexChannel >= 0,
              source.usesFloatComponents,
              source.bytesPerComponent == MemoryLayout<Float>.size,
              source.componentsPerVector >= 3,
              source.dataStride >= source.dataOffset + source.componentsPerVector * source.bytesPerComponent,
              source.vectorCount > 0 else {
            return nil
        }

        let vertices = (0..<source.vectorCount).compactMap { index -> SIMD3<Float>? in
            let offset = source.dataOffset + index * source.dataStride
            guard offset >= 0,
                  offset + 3 * MemoryLayout<Float>.size <= source.data.count else {
                return nil
            }
            let local = SIMD3<Float>(
                float32(in: source.data, at: offset),
                float32(in: source.data, at: offset + 4),
                float32(in: source.data, at: offset + 8)
            )
            let world = node.simdWorldTransform * SIMD4<Float>(local.x, local.y, local.z, 1)
            guard world.x.isFinite, world.y.isFinite, world.z.isFinite else { return nil }
            return SIMD3<Float>(world.x, world.y, world.z)
        }
        guard vertices.count == source.vectorCount else { return nil }

        var result: [Triangle] = []
        for element in geometry.elements {
            guard element.primitiveType == .triangles,
                  element.indicesChannelCount > vertexChannel,
                  element.bytesPerIndex == 1 || element.bytesPerIndex == 2 || element.bytesPerIndex == 4,
                  element.primitiveCount >= 0 else {
                return nil
            }
            let indexCount = element.primitiveCount * 3
            guard indexCount >= 0,
                  indexCount * element.indicesChannelCount * element.bytesPerIndex <= element.data.count else {
                return nil
            }
            for offset in stride(from: 0, to: indexCount, by: 3) {
                guard let first = index(in: element, at: offset, channel: vertexChannel),
                      let second = index(in: element, at: offset + 1, channel: vertexChannel),
                      let third = index(in: element, at: offset + 2, channel: vertexChannel),
                      vertices.indices.contains(first),
                      vertices.indices.contains(second),
                      vertices.indices.contains(third) else {
                    return nil
                }
                result.append(Triangle(a: vertices[first], b: vertices[second], c: vertices[third]))
            }
        }
        return result.isEmpty ? nil : result
    }

    private static func float32(in data: Data, at offset: Int) -> Float {
        let bytes = data[offset..<(offset + 4)]
        let bitPattern = bytes.enumerated().reduce(UInt32.zero) { result, byte in
            result | UInt32(byte.element) << UInt32(byte.offset * 8)
        }
        return Float(bitPattern: bitPattern)
    }

    private static func index(in element: SCNGeometryElement, at index: Int, channel: Int) -> Int? {
        // Imported USDZs can index positions, normals and UVs independently.
        // Read the geometry's declared position channel, in either layout.
        let scalarIndex = element.hasInterleavedIndicesChannels
            ? index * element.indicesChannelCount + channel
            : channel * element.primitiveCount * 3 + index
        let offset = scalarIndex * element.bytesPerIndex
        guard offset >= 0, offset + element.bytesPerIndex <= element.data.count else { return nil }
        let value = element.data[offset..<(offset + element.bytesPerIndex)].enumerated().reduce(UInt32.zero) {
            $0 | UInt32($1.element) << UInt32($1.offset * 8)
        }
        return Int(value)
    }

    private static func closestApproach(
        from start: SIMD3<Float>,
        to end: SIMD3<Float>,
        triangle: Triangle
    ) -> TriangleApproach {
        let direction = end - start
        if let parameter = segmentTriangleIntersectionParameter(
            start: start,
            direction: direction,
            triangle: triangle
        ) {
            let point = start + direction * parameter
            return TriangleApproach(distanceSquared: 0, segmentParameter: parameter, trianglePoint: point)
        }

        var best = TriangleApproach(
            distanceSquared: .infinity,
            segmentParameter: 0,
            trianglePoint: triangle.a
        )
        let endpointCandidates: [(point: SIMD3<Float>, parameter: Float)] = [
            (start, 0), (end, 1)
        ]
        for (point, parameter) in endpointCandidates {
            let trianglePoint = closestPoint(on: triangle, to: point)
            let difference: SIMD3<Float> = point - trianglePoint
            let distanceSquared = simd_dot(difference, difference)
            if distanceSquared < best.distanceSquared {
                best = TriangleApproach(
                    distanceSquared: distanceSquared,
                    segmentParameter: parameter,
                    trianglePoint: trianglePoint
                )
            }
        }
        for (edgeStart, edgeEnd) in [
            (triangle.a, triangle.b), (triangle.b, triangle.c), (triangle.c, triangle.a)
        ] {
            let approach = closestSegmentApproach(start, end, edgeStart, edgeEnd)
            if approach.distanceSquared < best.distanceSquared {
                best = TriangleApproach(
                    distanceSquared: approach.distanceSquared,
                    segmentParameter: approach.firstParameter,
                    trianglePoint: approach.secondPoint
                )
            }
        }
        return best
    }

    private static func segmentTriangleIntersectionParameter(
        start: SIMD3<Float>,
        direction: SIMD3<Float>,
        triangle: Triangle
    ) -> Float? {
        let firstEdge = triangle.b - triangle.a
        let secondEdge = triangle.c - triangle.a
        let perpendicular = simd_cross(direction, secondEdge)
        let determinant = simd_dot(firstEdge, perpendicular)
        guard determinant.isFinite, abs(determinant) > 1e-7 else { return nil }
        let inverse = 1 / determinant
        let offset = start - triangle.a
        let u = simd_dot(offset, perpendicular) * inverse
        guard u >= 0, u <= 1 else { return nil }
        let q = simd_cross(offset, firstEdge)
        let v = simd_dot(direction, q) * inverse
        guard v >= 0, u + v <= 1 else { return nil }
        let parameter = simd_dot(secondEdge, q) * inverse
        guard parameter >= 0, parameter <= 1, parameter.isFinite else { return nil }
        return parameter
    }

    private static func closestPoint(on triangle: Triangle, to point: SIMD3<Float>) -> SIMD3<Float> {
        let ab = triangle.b - triangle.a
        let ac = triangle.c - triangle.a
        let ap = point - triangle.a
        let d1 = simd_dot(ab, ap)
        let d2 = simd_dot(ac, ap)
        if d1 <= 0, d2 <= 0 { return triangle.a }

        let bp = point - triangle.b
        let d3 = simd_dot(ab, bp)
        let d4 = simd_dot(ac, bp)
        if d3 >= 0, d4 <= d3 { return triangle.b }

        let vc = d1 * d4 - d3 * d2
        if vc <= 0, d1 >= 0, d3 <= 0 {
            return triangle.a + ab * (d1 / (d1 - d3))
        }

        let cp = point - triangle.c
        let d5 = simd_dot(ab, cp)
        let d6 = simd_dot(ac, cp)
        if d6 >= 0, d5 <= d6 { return triangle.c }

        let vb = d5 * d2 - d1 * d6
        if vb <= 0, d2 >= 0, d6 <= 0 {
            return triangle.a + ac * (d2 / (d2 - d6))
        }

        let va = d3 * d6 - d5 * d4
        if va <= 0, d4 - d3 >= 0, d5 - d6 >= 0 {
            let edge = triangle.c - triangle.b
            return triangle.b + edge * ((d4 - d3) / ((d4 - d3) + (d5 - d6)))
        }

        let denominator = va + vb + vc
        guard denominator.isFinite, abs(denominator) > 1e-7 else { return triangle.a }
        let inverse = 1 / denominator
        return triangle.a + ab * (vb * inverse) + ac * (vc * inverse)
    }

    private static func closestSegmentApproach(
        _ firstStart: SIMD3<Float>,
        _ firstEnd: SIMD3<Float>,
        _ secondStart: SIMD3<Float>,
        _ secondEnd: SIMD3<Float>
    ) -> (distanceSquared: Float, firstParameter: Float, secondPoint: SIMD3<Float>) {
        let firstDirection = firstEnd - firstStart
        let secondDirection = secondEnd - secondStart
        let offset = firstStart - secondStart
        let a = simd_dot(firstDirection, firstDirection)
        let b = simd_dot(firstDirection, secondDirection)
        let c = simd_dot(secondDirection, secondDirection)
        let d = simd_dot(firstDirection, offset)
        let e = simd_dot(secondDirection, offset)
        let epsilon: Float = 1e-7
        var firstParameter: Float = 0
        var secondParameter: Float = 0

        if a <= epsilon, c <= epsilon {
            let difference = firstStart - secondStart
            return (simd_dot(difference, difference), 0, secondStart)
        }
        if a <= epsilon {
            secondParameter = min(max(e / c, 0), 1)
        } else if c <= epsilon {
            firstParameter = min(max(-d / a, 0), 1)
        } else {
            let denominator = a * c - b * b
            if denominator > epsilon {
                firstParameter = min(max((b * e - c * d) / denominator, 0), 1)
            }
            secondParameter = (b * firstParameter + e) / c
            if secondParameter < 0 {
                secondParameter = 0
                firstParameter = min(max(-d / a, 0), 1)
            } else if secondParameter > 1 {
                secondParameter = 1
                firstParameter = min(max((b - d) / a, 0), 1)
            }
        }
        let firstPoint = firstStart + firstDirection * firstParameter
        let secondPoint = secondStart + secondDirection * secondParameter
        let difference = firstPoint - secondPoint
        return (simd_dot(difference, difference), firstParameter, secondPoint)
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
            camera.camera?.orthographicScale = Double(max(framing.height, framing.width / aspect) * framing.fitPadding / orbitZoom / 2)
        } else {
            camera.camera?.orthographicScale = Double(max(projectedHeight, projectedWidth / aspect) / 2)
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

    static func rotatedBounds(
        _ bounds: BoardModelBounds,
        by quaternion: simd_quatf,
        pivot: SIMD3<Float>
    ) -> BoardModelBounds {
        let transformedCorners = rotatedCorners(bounds, by: quaternion, pivot: pivot)
        let transformedMinimum = SIMD3<Float>(
            transformedCorners.map(\.x).min() ?? 0,
            transformedCorners.map(\.y).min() ?? 0,
            transformedCorners.map(\.z).min() ?? 0
        )
        let transformedMaximum = SIMD3<Float>(
            transformedCorners.map(\.x).max() ?? 0,
            transformedCorners.map(\.y).max() ?? 0,
            transformedCorners.map(\.z).max() ?? 0
        )
        return BoardModelBounds(
            minimum: [Double(transformedMinimum.x), Double(transformedMinimum.y), Double(transformedMinimum.z)],
            maximum: [Double(transformedMaximum.x), Double(transformedMaximum.y), Double(transformedMaximum.z)]
        )
    }

    static func rotatedCorners(
        _ bounds: BoardModelBounds,
        by quaternion: simd_quatf,
        pivot: SIMD3<Float>
    ) -> [SIMD3<Float>] {
        boundsCorners(bounds).map { quaternion.act($0 - pivot) + pivot }
    }

    static func framing(
        descriptor: BoardModelDescriptor,
        display: BoardModelDisplay
    ) -> SuspendedCameraFraming? {
        framing(bounds: descriptor.modelBounds, display: display)
    }

    static func framing(
        bounds: BoardModelBounds,
        display: BoardModelDisplay
    ) -> SuspendedCameraFraming? {
        framing(points: boundsCorners(bounds), display: display)
    }

    static func framing(
        points: [SIMD3<Float>],
        display: BoardModelDisplay
    ) -> SuspendedCameraFraming? {
        let camera = display.camera
        guard points.count == 8,
              camera.type == "orthographic",
              camera.viewDirection.count == 3,
              camera.up.count == 3,
              camera.fitPadding.isFinite,
              camera.fitPadding > 0,
              points.allSatisfy({
                  $0.x.isFinite && $0.y.isFinite && $0.z.isFinite
              }),
              camera.viewDirection.allSatisfy(\.isFinite),
              camera.up.allSatisfy(\.isFinite) else {
            return nil
        }
        let target = points.reduce(SIMD3<Float>.zero, +) / Float(points.count)
        let direction = SIMD3<Float>(Float(camera.viewDirection[0]), Float(camera.viewDirection[1]), Float(camera.viewDirection[2]))
        let requestedUp = SIMD3<Float>(Float(camera.up[0]), Float(camera.up[1]), Float(camera.up[2]))
        guard simd_length(direction) > 0,
              simd_length(requestedUp) > 0 else {
            return nil
        }
        let normalizedDirection = simd_normalize(direction)
        let cross = simd_cross(normalizedDirection, simd_normalize(requestedUp))
        guard simd_length(cross) > 0 else { return nil }
        let right = simd_normalize(cross)
        let up = simd_cross(right, normalizedDirection)
        let horizontal = points.map { simd_dot($0 - target, right) }
        let vertical = points.map { simd_dot($0 - target, up) }
        let depth = points.map { simd_dot($0 - target, normalizedDirection) }
        guard let width = horizontal.max().flatMap({ maximum in horizontal.min().map { maximum - $0 } }),
              let height = vertical.max().flatMap({ maximum in vertical.min().map { maximum - $0 } }),
              let depthSpan = depth.max().flatMap({ maximum in depth.min().map { maximum - $0 } }),
              width.isFinite, height.isFinite, depthSpan.isFinite,
              width > 0, height > 0 else {
            return nil
        }
        let fitPadding = Float(1 + camera.fitPadding * 2)
        let distance = max(width, height, depthSpan) * fitPadding
        return SuspendedCameraFraming(
            target: target,
            direction: normalizedDirection,
            viewDirection: normalizedDirection,
            right: right,
            up: up,
            distance: distance,
            width: width,
            height: height,
            depth: depthSpan,
            fitPadding: fitPadding,
            includedPoints: points
        )
    }

    private static func boundsCorners(_ bounds: BoardModelBounds) -> [SIMD3<Float>] {
        guard bounds.minimum.count == 3, bounds.maximum.count == 3 else { return [] }
        let minimum = SIMD3<Float>(
            Float(bounds.minimum[0]), Float(bounds.minimum[1]), Float(bounds.minimum[2])
        )
        let maximum = SIMD3<Float>(
            Float(bounds.maximum[0]), Float(bounds.maximum[1]), Float(bounds.maximum[2])
        )
        return [minimum.x, maximum.x].flatMap { x in
            [minimum.y, maximum.y].flatMap { y in
                [minimum.z, maximum.z].map { z in SIMD3<Float>(x, y, z) }
            }
        }
    }

    private static func boundsCenter(_ bounds: BoardModelBounds) -> SIMD3<Float> {
        SIMD3<Float>(
            Float((bounds.minimum[0] + bounds.maximum[0]) / 2),
            Float((bounds.minimum[1] + bounds.maximum[1]) / 2),
            Float((bounds.minimum[2] + bounds.maximum[2]) / 2)
        )
    }

    private static func fixedFraming(
        from framing: SuspendedCameraFraming
    ) -> SuspendedCameraFraming {
        SuspendedCameraFraming(
            target: framing.target,
            direction: framing.direction,
            viewDirection: framing.viewDirection,
            right: framing.right,
            up: framing.up,
            distance: framing.distance,
            width: framing.width,
            height: framing.height,
            depth: framing.depth,
            fitPadding: 1,
            includedPoints: framing.includedPoints
        )
    }

    private static func quaternion(from components: SIMD4<Double>) -> simd_quatf? {
        guard components.x.isFinite, components.y.isFinite,
              components.z.isFinite, components.w.isFinite else {
            return nil
        }
        let quaternion = simd_quatf(
            ix: Float(components.x), iy: Float(components.y),
            iz: Float(components.z), r: Float(components.w)
        )
        guard quaternion.vector.x.isFinite, quaternion.vector.y.isFinite,
              quaternion.vector.z.isFinite, quaternion.vector.w.isFinite,
              simd_length(quaternion.vector) > 1e-6 else {
            return nil
        }
        return simd_normalize(quaternion)
    }

    private static func transform(
        rotating quaternion: simd_quatf,
        about pivot: SIMD3<Float>
    ) -> simd_float4x4 {
        var translateToPivot = matrix_identity_float4x4
        translateToPivot.columns.3 = SIMD4<Float>(pivot.x, pivot.y, pivot.z, 1)
        var translateFromPivot = matrix_identity_float4x4
        translateFromPivot.columns.3 = SIMD4<Float>(-pivot.x, -pivot.y, -pivot.z, 1)
        return translateToPivot * simd_float4x4(quaternion) * translateFromPivot
    }

    private func configureCameraAndLighting(framing: SuspendedCameraFraming) {
        camera.camera = SCNCamera()
        camera.camera?.usesOrthographicProjection = true
        camera.camera?.zNear = 0.01
        camera.camera?.zFar = 10
        camera.camera?.wantsHDR = false
        camera.camera?.screenSpaceAmbientOcclusionIntensity = 0.7
        camera.camera?.screenSpaceAmbientOcclusionRadius = 0.018
        camera.camera?.screenSpaceAmbientOcclusionBias = 0.001
        camera.camera?.screenSpaceAmbientOcclusionDepthThreshold = 0.03
        camera.position = SCNVector3(framing.target - framing.direction * framing.distance)
        camera.look(at: SCNVector3(framing.target), up: SCNVector3(framing.up), localFront: SCNVector3(0, 0, -1))
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
        key.position = camera.position + SCNVector3(framing.up) * framing.height
        key.look(at: SCNVector3(framing.target), up: SCNVector3(framing.up), localFront: SCNVector3(0, 0, -1))
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

    func selectPositionIfNeeded() {
        guard let model else { return }
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
