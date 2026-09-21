import CryptoKit
import SceneKit
import SwiftUI

/// Identity for a decoded package model. The hash makes replacement assets a
/// distinct cached source even when a board keeps the same presentation ID.
struct BoardModelKey: Hashable {
    let boardID: String
    let presentationID: String
    let modelSHA256: String
}

protocol BoardModelResourceRequesting: AnyObject {
    var progress: Progress { get }
    func beginAccessingResources() async throws
    func endAccessingResources()
}

extension NSBundleResourceRequest: BoardModelResourceRequesting {}

final class BoardModelResourceLease {
    let url: URL
    private var request: BoardModelResourceRequesting?

    init(url: URL, request: BoardModelResourceRequesting? = nil) {
        self.url = url
        self.request = request
    }

    deinit {
        request?.endAccessingResources()
    }
}

private final class BoardModelResourceRequestAccess: @unchecked Sendable {
    private let lock = NSLock()
    private var request: BoardModelResourceRequesting?
    private var isCancelled = false

    init(request: BoardModelResourceRequesting) {
        self.request = request
    }

    func cancel() {
        lock.lock()
        isCancelled = true
        let request = request
        lock.unlock()
        // Cancellation signals the pending request; only a completed successful
        // begin (or its transferred lease) may balance resource access.
        request?.progress.cancel()
    }

    func endAccessingResources() {
        lock.lock()
        let request = request
        self.request = nil
        lock.unlock()
        request?.endAccessingResources()
    }

    func lease(for url: URL) -> BoardModelResourceLease? {
        lock.lock()
        guard !isCancelled else {
            lock.unlock()
            return nil
        }
        let request = request
        self.request = nil
        lock.unlock()
        return request.map { BoardModelResourceLease(url: url, request: $0) }
    }
}

struct BoardModelResourceAccess {
    typealias RequestFactory = (Set<String>, Bundle) -> BoardModelResourceRequesting
    typealias URLResolver = (Bundle, BoardModelResource) -> URL?

    static let live = BoardModelResourceAccess(
        requestFactory: { tags, bundle in
            NSBundleResourceRequest(tags: tags, bundle: bundle)
        },
        urlResolver: { bundle, resource in
            bundle.url(
                forResource: resource.resourceName,
                withExtension: resource.resourceExtension,
                subdirectory: resource.bundleSubdirectory
            )
        }
    )

    let requestFactory: RequestFactory
    let urlResolver: URLResolver

    func acquire(
        _ resource: BoardModelResource,
        bundle: Bundle
    ) async -> BoardModelResourceLease? {
        guard !Task.isCancelled else { return nil }
        let request = requestFactory([resource.tag], bundle)
        let access = BoardModelResourceRequestAccess(request: request)
        return await withTaskCancellationHandler {
            guard !Task.isCancelled else { return nil }
            do {
                try await request.beginAccessingResources()
            } catch {
                return nil
            }
            // Begin has succeeded. Keep ownership through URL resolution;
            // lease transfer and cancellation choose an owner under one lock.
            defer { access.endAccessingResources() }
            guard !Task.isCancelled,
                  let url = urlResolver(bundle, resource),
                  let lease = access.lease(for: url),
                  !Task.isCancelled else {
                return nil
            }
            return lease
        } onCancel: {
            access.cancel()
        }
    }
}

enum BoardModelSolvedSuspension {
    case single(SuspendedSolvedPresentation)
    case pairedLead(SuspendedPairedLeadSolvedPresentation)
    case twoBranch(SuspendedTwoBranchSolvedPresentation)

    var boardTransform: simd_float4x4 {
        switch self {
        case .single(let solved): solved.boardTransform
        case .pairedLead(let solved): solved.boardTransform
        case .twoBranch(let solved): solved.boardTransform
        }
    }

    var cameraFraming: SuspendedCameraFraming {
        switch self {
        case .single(let solved): solved.cameraFraming
        case .pairedLead(let solved): solved.cameraFraming
        case .twoBranch(let solved): solved.cameraFraming
        }
    }
}

enum BoardModelAsset {
    #if DEBUG
    // Task-scoped synchronization for the decode lifetime regression. The
    // production decoder and model source remain unchanged by the test hook.
    @TaskLocal static var willDecodeForTesting: (@Sendable (URL) -> Void)?
    @TaskLocal static var sceneLoaderForTesting: (@Sendable (URL) -> SCNScene?)?
    #endif

    static func load(media: BoardModelMedia, packageURL: URL) -> SCNScene? {
        guard packageURL.isFileURL,
              let values = try? packageURL.resourceValues(forKeys: [.isRegularFileKey]),
              values.isRegularFile == true,
              sha256(of: packageURL) == media.descriptor.modelSHA256 else {
            return nil
        }
        // SceneKit can otherwise return an empty scene for a missing asset.
        #if DEBUG
        if let sceneLoaderForTesting {
            return sceneLoaderForTesting(packageURL)
        }
        #endif
        return try? SCNScene(url: packageURL, options: [.convertToYUp: true])
    }

    private static func sha256(of url: URL) -> String? {
        do {
            let handle = try FileHandle(forReadingFrom: url)
            defer { try? handle.close() }
            var hash = SHA256()
            while let data = try handle.read(upToCount: 1_048_576), !data.isEmpty {
                hash.update(data: data)
            }
            return hash.finalize().map { String(format: "%02x", $0) }.joined()
        } catch {
            return nil
        }
    }

    #if DEBUG
    @MainActor static var queuedLoadWaiterCount: Int {
        BoardModelLoadGate.debugQueuedWaiters
    }
    #endif
}

private final class BoardModelLoadedAsset {
    let scene: SCNScene
    let resourceLease: BoardModelResourceLease

    init(scene: SCNScene, resourceLease: BoardModelResourceLease) {
        self.scene = scene
        self.resourceLease = resourceLease
    }
}

@MainActor
private enum BoardModelCache {
    private final class InFlight {
        var task: Task<Void, Never>?
        var waiters: [UUID: CheckedContinuation<BoardModelLoadedAsset?, Never>] = [:]
    }

    private static var loading: [BoardModelKey: InFlight] = [:]

    static func source(
        for key: BoardModelKey,
        media: BoardModelMedia,
        board: BoardRevision,
        presentationID: String,
        store: BoardPackageStore,
        resourceAccess: BoardModelResourceAccess
    ) async -> BoardModelLoadedAsset? {
        let waiterID = UUID()
        return await withTaskCancellationHandler {
            await withCheckedContinuation { continuation in
                guard !Task.isCancelled else {
                    continuation.resume(returning: nil)
                    return
                }
                if let entry = loading[key] {
                    entry.waiters[waiterID] = continuation
                    return
                }
                let entry = InFlight()
                entry.waiters[waiterID] = continuation
                loading[key] = entry
                entry.task = Task {
                    let loaded = await loadSource(
                        media: media,
                        board: board,
                        presentationID: presentationID,
                        store: store,
                        resourceAccess: resourceAccess
                    )
                    // A canceled acquisition may finish after a replacement
                    // load has started for the same model identity.
                    guard loading[key] === entry else { return }
                    loading[key] = nil
                    let waiters = entry.waiters
                    entry.waiters.removeAll()
                    for waiter in waiters.values {
                        waiter.resume(returning: loaded)
                    }
                }
            }
        } onCancel: {
            Task { @MainActor in
                guard let entry = loading[key],
                      let waiter = entry.waiters.removeValue(forKey: waiterID) else { return }
                if entry.waiters.isEmpty {
                    loading[key] = nil
                    entry.task?.cancel()
                }
                // Release the view task immediately. The resource request still
                // balances any successful access when its completion arrives.
                waiter.resume(returning: nil)
            }
        }
    }

    private static func loadSource(
        media: BoardModelMedia,
        board: BoardRevision,
        presentationID: String,
        store: BoardPackageStore,
        resourceAccess: BoardModelResourceAccess
    ) async -> BoardModelLoadedAsset? {
        let resourceLease: BoardModelResourceLease?
        if let bundledURL = store.presentationAssetURL(
            for: board,
            presentationID: presentationID
        ) {
            resourceLease = BoardModelResourceLease(url: bundledURL)
        } else if let resource = store.modelResource(
            for: board,
            presentationID: presentationID
        ) {
            if let packagedURL = resource.debugSimulatorPackagedURL(in: store.resourceBundle) {
                resourceLease = BoardModelResourceLease(url: packagedURL)
            } else {
                resourceLease = await resourceAccess.acquire(
                    resource,
                    bundle: store.resourceBundle
                )
            }
        } else {
            resourceLease = nil
        }
        guard let resourceLease, !Task.isCancelled else { return nil }
        #if DEBUG
        let willDecodeForTesting = BoardModelAsset.willDecodeForTesting
        let sceneLoaderForTesting = BoardModelAsset.sceneLoaderForTesting
        #endif
        let scene = await Task.detached(priority: .userInitiated) {
            withExtendedLifetime(resourceLease) {
                #if DEBUG
                willDecodeForTesting?(resourceLease.url)
                return BoardModelAsset.$sceneLoaderForTesting.withValue(sceneLoaderForTesting) {
                    BoardModelAsset.load(media: media, packageURL: resourceLease.url)
                }
                #else
                return BoardModelAsset.load(media: media, packageURL: resourceLease.url)
                #endif
            }
        }.value
        guard let scene, !Task.isCancelled else { return nil }
        return BoardModelLoadedAsset(scene: scene, resourceLease: resourceLease)
    }
}

/// Serializes 3D model loads (decode + MainActor scene build) so only one is
/// in flight globally. SwiftUI `.task` cancels on disappear; a cancelled
/// queued load is removed and resumed with `false` so it never consumes or
/// leaks a slot. Mirrors the waiter pattern used by `BoardModelCache`.
@MainActor
private enum BoardModelLoadGate {
    private static let limit = 1
    private static var active = 0
    private static var waiters: [(id: UUID, continuation: CheckedContinuation<Bool, Never>)] = []

    /// Returns true when the caller holds a slot and must call `release()`.
    /// Returns false when the caller is cancelled before the slot is granted
    /// (the caller must NOT call `release()` in that case).
    static func acquire() async -> Bool {
        guard !Task.isCancelled else { return false }
        if active < limit {
            active += 1
            return true
        }
        let waiterID = UUID()
        return await withTaskCancellationHandler {
            await withCheckedContinuation { continuation in
                guard !Task.isCancelled else {
                    continuation.resume(returning: false)
                    return
                }
                waiters.append((waiterID, continuation))
            }
        } onCancel: {
            Task { @MainActor in
                guard let index = waiters.firstIndex(where: { $0.id == waiterID }) else {
                    return
                }
                let waiter = waiters.remove(at: index)
                waiter.continuation.resume(returning: false)
            }
        }
    }

    static func release() {
        if waiters.isEmpty {
            active -= 1
        } else {
            // Hand the slot to the earliest waiter; active stays at limit.
            waiters.removeFirst().continuation.resume(returning: true)
        }
    }

    #if DEBUG
    fileprivate static var debugQueuedWaiters: Int { waiters.count }
    #endif
}

@MainActor
enum BoardModelLoader {
    static func load(
        board: BoardRevision,
        presentation: BoardPresentation,
        store: BoardPackageStore,
        resourceAccess: BoardModelResourceAccess = .live
    ) async -> BoardModelScene? {
        guard case .model(let media) = presentation.media else {
            return nil
        }
        guard await BoardModelLoadGate.acquire() else { return nil }
        defer { BoardModelLoadGate.release() }
        let key = BoardModelKey(
            boardID: board.id,
            presentationID: presentation.id,
            modelSHA256: media.descriptor.modelSHA256
        )
        guard let source = await BoardModelCache.source(
            for: key,
            media: media,
            board: board,
            presentationID: presentation.id,
            store: store,
            resourceAccess: resourceAccess
        ), !Task.isCancelled else {
            return nil
        }
        return BoardModelScene(
            source: source.scene,
            descriptor: media.descriptor,
            display: media.display,
            suspension: media.suspension,
            orientation: media.orientation,
            allowedPositionIDs: Set(board.positions.filter {
                $0.presentationID == presentation.id
            }.map(\.id)),
            resourceLease: source.resourceLease
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
                BoardModelView(
                    model: model,
                    boardName: board.name,
                    contacts: board.contacts(in: presentation),
                    positionID: positionID,
                    highlightedContactIDs: highlightedContactIDs,
                    highlightMode: highlightMode,
                    onContactTap: onContactTap,
                    onUnavailable: { result = .unavailable },
                    isDisplayOnly: isDisplayOnly
                )
                .accessibilityIdentifier("boardModel.3d")
                // Display-only picker cards wrap this in a Button; claiming
                // SwiftUI hits here would intercept the card select tap even
                // when the hosted SCNView has user interaction disabled.
                .allowsHitTesting(!isDisplayOnly)
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
        .onDisappear {
            result = .loading
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
    static let modelVisibleCategory = 4
    static let renderedCategory = modelPickCategory | cordCategory | modelVisibleCategory
    static let canonicalTransitionDuration: CFTimeInterval = 0.18

    private struct PreparedCameraState {
        let transform: simd_float4x4
        let orthographicScale: Double?
    }

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
    private(set) var contactNodes: [String: [SCNNode]] = [:]
    private var contactIDsByNode: [ObjectIdentifier: String] = [:]
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
    private let resourceLease: BoardModelResourceLease?

    init?(
        source: SCNScene,
        descriptor: BoardModelDescriptor,
        display: BoardModelDisplay,
        suspension: BoardModelSuspension? = nil,
        orientation: BoardModelOrientation? = nil,
        allowedPositionIDs: Set<String>? = nil,
        resourceLease: BoardModelResourceLease? = nil
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

        var boundContactNodes: [String: [SCNNode]] = [:]
        var boundContactIDsByNode: [ObjectIdentifier: String] = [:]
        var originals: [ObjectIdentifier: [SCNMaterial]] = [:]
        for (nodeID, node) in geometryByNodeID {
            guard let binding = descriptorsByNodeID[nodeID] else { return nil }
            switch binding.role {
            case .body:
                guard binding.contactID == nil else { return nil }
                node.categoryBitMask = Self.modelVisibleCategory
            case .contact:
                guard let contactID = binding.contactID, !contactID.isEmpty else { return nil }
                boundContactNodes[contactID, default: []].append(node)
                boundContactIDsByNode[ObjectIdentifier(node)] = contactID
                originals[ObjectIdentifier(node)] = node.geometry?.materials
                node.categoryBitMask = Self.modelPickCategory
            case .attachment:
                guard binding.contactID == nil else { return nil }
                node.categoryBitMask = Self.modelVisibleCategory
            }
        }

        guard descriptor.nodes.contains(where: { $0.role == .body }),
              Set(boundContactNodes.keys) == Set(descriptor.contacts.keys),
              descriptor.contacts.allSatisfy({ contactID, contact in
                  contact.nodeIDs == descriptor.nodes.compactMap { node in
                      node.role == .contact && node.contactID == contactID ? node.nodeID : nil
                  }.sorted()
              }) else {
            return nil
        }

        geometryNodes = clonedGeometryNodes
        self.descriptor = descriptor
        self.display = display
        self.suspension = suspension
        self.orientation = orientation
        self.allowedPositionIDs = allowedPositionIDs
            ?? suspension.map { Set($0.canonicalPoses.keys) }
            ?? orientation.map { Set($0.rotations.keys) }
            ?? []
        self.resourceLease = resourceLease

        self.geometryByNodeID = geometryByNodeID
        contactNodes = boundContactNodes
        contactIDsByNode = boundContactIDsByNode
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
        configureCameraAndLighting(framing: framing)
    }

    func contactID(for node: SCNNode) -> String? {
        var candidate: SCNNode? = node
        while let current = candidate {
            if let contactID = contactIDsByNode[ObjectIdentifier(current)] { return contactID }
            candidate = current.parent
        }
        return nil
    }

    @discardableResult
    func select(positionID: String?) -> Bool {
        // Pose changes must invalidate the highlight short-circuit so a later
        // applyHighlights call always repaints materials for the posed nodes.
        lastHighlights = []
        lastMode = nil
        guard let positionID, allowedPositionIDs.contains(positionID) else {
            enterUnavailable()
            return false
        }
        if suspension == nil, let orientation {
            guard let components = orientation.rotations[positionID],
                  orientation.pivot == "modelBoundsCenter",
                  let quaternion = Self.quaternion(from: components) else {
                enterUnavailable()
                return false
            }
            let pivot = Self.boundsCenter(descriptor.modelBounds)
            guard let framing = Self.framing(
                bounds: descriptor.modelBounds,
                display: display,
                orientation: orientation,
                positionID: positionID
            ) else {
                enterUnavailable()
                return false
            }
            guard transitionToOrientation(
                transform: Self.transform(rotating: quaternion, about: pivot),
                framing: framing
            ) else { return false }
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
            guard transitionToCanonicalPresentation(solved, cord: cord) else { return false }
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
        case .pairedLeadCord(let pairedLead):
            nodeIDs = pairedLead.attachments.map(\.nodeID)
            guard nodeIDs.count == 2 else { return false }
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
        case .pairedLeadCord(let pairedLead):
            return .pairedLead(try SuspendedBoardPresentation.solve(
                pose: pose, suspension: pairedLead, bounds: bounds
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
        let fullAzimuthRotation: Float = .pi * 2
        let nextAzimuth = (orbitAzimuth + azimuth)
            .truncatingRemainder(dividingBy: fullAzimuthRotation)
        let nextElevation = min(max(orbitElevation + elevation, -0.55), 0.55)
        let nextZoom = min(max(orbitZoom * zoomScale, 0.75), 1.35)
        let baseOffset = -framing.direction * framing.distance
        let yaw = simd_quatf(angle: nextAzimuth, axis: SIMD3<Float>(0, 1, 0))
        let pitchAxis = framing.right
        let pitch = simd_quatf(angle: nextElevation, axis: pitchAxis)
        let offset = (pitch * yaw).act(baseOffset)
        let distance = max(0.01, framing.distance / nextZoom)
        let normalizedOffset = simd_length(offset) > 1e-6
            ? simd_normalize(offset) * distance
            : baseOffset
        let position = framing.target + normalizedOffset
        let scale = Double(cameraScale(for: framing) / nextZoom)
        guard position.x.isFinite, position.y.isFinite, position.z.isFinite,
              scale.isFinite, scale > 0,
              applyCamera(
                  position: position,
                  target: framing.target,
                  up: framing.up,
                  orthographicScale: scale
              ) else { return }
        orbitAzimuth = nextAzimuth
        orbitElevation = nextElevation
        orbitZoom = nextZoom
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
        let aspect: Float
        if viewportSize.width.isFinite, viewportSize.height.isFinite,
           viewportSize.width > 0, viewportSize.height > 0 {
            aspect = Float(viewportSize.width / viewportSize.height)
        } else {
            aspect = 1
        }
        guard aspect.isFinite, aspect > 0 else { return .nan }
        let scale = max(framing.height, framing.width / aspect) * framing.fitPadding / 2
        return scale.isFinite && scale > 0 ? scale : .nan
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
    ) -> Bool {
        guard let cameraState = preparedCanonicalCameraState(for: solved.cameraFraming) else {
            return false
        }
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
        applyPreparedCameraState(cameraState)
        SCNTransaction.commit()

        boardTransform = solved.boardTransform
        if case .single(let single) = solved {
            transformedAttachment = single.transformedAttachment
        }
        currentFraming = solved.cameraFraming
        return true
    }

    private func transitionToOrientation(
        transform: simd_float4x4,
        framing: SuspendedCameraFraming
    ) -> Bool {
        guard let cameraState = preparedCanonicalCameraState(for: framing) else {
            return false
        }
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
        applyPreparedCameraState(cameraState)
        SCNTransaction.commit()

        boardTransform = transform
        currentFraming = framing
        return true
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

    @discardableResult
    private func applyCanonicalCamera(_ framing: SuspendedCameraFraming) -> Bool {
        let position = framing.target - framing.direction * framing.distance
        let scale = Double(cameraScale(for: framing))
        guard let cameraState = Self.preparedCameraState(
            position: position,
            target: framing.target,
            up: framing.up,
            orthographicScale: scale
        ) else { return false }
        applyPreparedCameraState(cameraState)
        orbitAzimuth = 0
        orbitElevation = 0
        orbitZoom = 1
        currentFraming = framing
        return true
    }

    private func preparedCanonicalCameraState(
        for framing: SuspendedCameraFraming
    ) -> PreparedCameraState? {
        let position = framing.target - framing.direction * framing.distance
        let scale = Double(cameraScale(for: framing))
        return Self.preparedCameraState(
            position: position,
            target: framing.target,
            up: framing.up,
            orthographicScale: scale
        )
    }

    @discardableResult
    func orientCamera(at target: SIMD3<Float>, up requestedUp: SIMD3<Float>) -> Bool {
        applyCamera(position: camera.simdPosition, target: target, up: requestedUp)
    }

    @discardableResult
    private func applyCamera(
        position: SIMD3<Float>,
        target: SIMD3<Float>,
        up requestedUp: SIMD3<Float>,
        orthographicScale: Double? = nil
    ) -> Bool {
        guard let state = Self.preparedCameraState(
            position: position,
            target: target,
            up: requestedUp,
            orthographicScale: orthographicScale
        ) else {
            return false
        }
        applyPreparedCameraState(state)
        return true
    }

    private func applyPreparedCameraState(_ state: PreparedCameraState) {
        camera.simdTransform = state.transform
        if let orthographicScale = state.orthographicScale {
            camera.camera?.orthographicScale = orthographicScale
        }
    }

    private static func preparedCameraState(
        position: SIMD3<Float>,
        target: SIMD3<Float>,
        up: SIMD3<Float>,
        orthographicScale: Double? = nil
    ) -> PreparedCameraState? {
        guard orthographicScale.map({ $0.isFinite && $0 > 0 }) ?? true,
              let transform = cameraTransform(
                  position: position,
                  target: target,
                  up: up
              ) else {
            return nil
        }
        return PreparedCameraState(transform: transform, orthographicScale: orthographicScale)
    }

    private static func cameraTransform(
        position: SIMD3<Float>,
        target: SIMD3<Float>,
        up requestedUp: SIMD3<Float>
    ) -> simd_float4x4? {
        let direction = target - position
        let directionLength = simd_length(direction)
        let requestedUpLength = simd_length(requestedUp)
        guard [position, target, requestedUp, direction].allSatisfy({ vector in
            vector.x.isFinite && vector.y.isFinite && vector.z.isFinite
        }),
              directionLength.isFinite, directionLength > 1e-6,
              requestedUpLength.isFinite, requestedUpLength > 1e-6 else {
            return nil
        }

        let forward = direction / directionLength
        let normalizedRequestedUp = requestedUp / requestedUpLength
        let rightVector = simd_cross(forward, normalizedRequestedUp)
        let rightLength = simd_length(rightVector)
        guard rightLength.isFinite, rightLength > 1e-6 else { return nil }
        let right = rightVector / rightLength
        let up = simd_cross(right, forward)
        guard [forward, right, up].allSatisfy({ vector in
            vector.x.isFinite && vector.y.isFinite && vector.z.isFinite
        }),
              abs(simd_length(up) - 1) <= 1e-4 else {
            return nil
        }
        var transform = matrix_identity_float4x4
        transform.columns.0 = SIMD4<Float>(right.x, right.y, right.z, 0)
        transform.columns.1 = SIMD4<Float>(up.x, up.y, up.z, 0)
        transform.columns.2 = SIMD4<Float>(-forward.x, -forward.y, -forward.z, 0)
        transform.columns.3 = SIMD4<Float>(position.x, position.y, position.z, 1)
        return transform
    }

    private func makeCordNode(for solved: BoardModelSolvedSuspension) -> SCNNode {
        let root = SCNNode()
        root.name = "suspended.cord"
        root.categoryBitMask = Self.cordCategory
        let paths: [([SIMD3<Float>], Float)]
        switch solved {
        case .single(let single):
            paths = [(single.centerlineSamples, single.tubeRadius)]
        case .pairedLead(let pairedLead):
            paths = pairedLead.leads.map { ($0.centerlineSamples, pairedLead.tubeRadius) }
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
            var mouthRadius: Float = 0
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
        case .pairedLead(let pairedLead):
            paths = pairedLead.leads.map(\.centerlineSamples)
            clearanceRadius = pairedLead.requiredClearance
            guard case .some(.pairedLeadCord(let pairedLeadSuspension)) = suspension,
                  pairedLeadSuspension.attachments.count == pairedLead.leads.count else { return false }
            for (index, attachment) in pairedLeadSuspension.attachments.enumerated() {
                let lead = pairedLead.leads[index]
                let firstRoutedSegment = SuspendedCordSolver.sampleCount - 1
                guard lead.centerlineSamples.count >= SuspendedCordSolver.sampleCount else { return false }
                // The solver has already resolved pose.cordContactPoints over
                // the attachment default. Samples after the fixed-size free
                // span are therefore the actual authored surface route for
                // this pose, even when the default route is empty.
                guard lead.centerlineSamples.count > SuspendedCordSolver.sampleCount else { continue }
                bearingIntervals.append((
                    index,
                    firstRoutedSegment..<(lead.centerlineSamples.count - 1),
                    [attachment.nodeID],
                    pairedLead.tubeRadius
                ))
            }
            intentionalContacts = zip(pairedLead.leads, pairedLeadSuspension.attachments).enumerated().map {
                index, pair in
                IntentionalContact(
                    pathIndex: index,
                    segmentIndex: pair.0.centerlineSamples.count - 2,
                    segmentParameter: 1,
                    nodeID: pair.1.nodeID,
                    point: pair.0.centerlineSamples[pair.0.centerlineSamples.count - 1],
                    mouthRadius: pairedLead.tubeRadius + pairedLead.requiredClearance
                )
            }
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
                    let segmentMinimum = simd_min(points.0, points.1) - SIMD3<Float>(repeating: requiredDistance)
                    let segmentMaximum = simd_max(points.0, points.1) + SIMD3<Float>(repeating: requiredDistance)
                for triangle in triangles {
                    // A conservative broad phase avoids expensive triangle
                    // distance work for the rest of the imported mesh. Bounds
                    // include the entire cord clearance tube, so no possible
                    // contact can be skipped.
                    if triangle.maximum.x < segmentMinimum.x || triangle.minimum.x > segmentMaximum.x
                        || triangle.maximum.y < segmentMinimum.y || triangle.minimum.y > segmentMaximum.y
                        || triangle.maximum.z < segmentMinimum.z || triangle.minimum.z > segmentMaximum.z { continue }
                    let approach = Self.closestApproach(
                        from: points.0,
                        to: points.1,
                        triangle: triangle
                    )
                    guard approach.distanceSquared.isFinite else { return false }
                    if approach.distanceSquared >= requiredDistance * requiredDistance { continue }
                    if intentionalContacts.contains(where: { contact in
                        guard contact.pathIndex == pathIndex,
                              contact.segmentIndex == segmentIndex,
                              contact.nodeID == nodeID else { return false }
                        if contact.mouthRadius == 0 {
                            return abs(approach.segmentParameter - contact.segmentParameter) <= 1e-5
                                && simd_length(approach.trianglePoint - contact.point) <= requiredDistance
                        }
                        // The terminal mouth interface is at most one tube
                        // radius plus its required clearance along the lead.
                        // Mesh proximity includes the tube around that short
                        // span. Recheck the entire remaining free span, so a
                        // nearby closest point cannot hide a farther collision
                        // against the same large triangle.
                        let direction = points.1 - points.0
                        let contactPoint = points.0 + direction * approach.segmentParameter
                        guard simd_length(contactPoint - contact.point) <= contact.mouthRadius,
                              simd_length(approach.trianglePoint - contact.point) <= contact.mouthRadius + requiredDistance else { return false }
                        let length = simd_length(direction)
                        if length <= contact.mouthRadius { return true }
                        let freeEnd = points.1 - direction * (contact.mouthRadius / length)
                        let freeApproach = Self.closestApproach(from: points.0, to: freeEnd, triangle: triangle)
                        return freeApproach.distanceSquared.isFinite
                            && freeApproach.distanceSquared >= requiredDistance * requiredDistance
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
        let minimum: SIMD3<Float>
        let maximum: SIMD3<Float>

        init(a: SIMD3<Float>, b: SIMD3<Float>, c: SIMD3<Float>) {
            self.a = a
            self.b = b
            self.c = c
            minimum = simd_min(a, simd_min(b, c))
            maximum = simd_max(a, simd_max(b, c))
        }
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
        guard size.width.isFinite, size.height.isFinite,
              size.width > 0, size.height > 0 else { return }
        let aspect = size.width / size.height
        guard aspect.isFinite, aspect > 0 else { return }
        let aspectFloat = Float(aspect)
        guard aspectFloat.isFinite, aspectFloat > 0 else { return }

        let candidateScale: Double
        if let framing = currentFraming {
            candidateScale = Double(
                max(framing.height, framing.width / aspectFloat)
                    * framing.fitPadding / orbitZoom / 2
            )
        } else {
            candidateScale = Double(max(projectedHeight, projectedWidth / aspectFloat) / 2)
        }
        guard candidateScale.isFinite, candidateScale > 0 else { return }

        viewportSize = size
        camera.camera?.orthographicScale = candidateScale
    }

    func highlight(_ contactIDs: Set<String>, mode: BoardHighlightMode) {
        let validIDs = contactIDs.intersection(Set(contactNodes.keys))
        guard validIDs != lastHighlights || mode != lastMode else { return }
        let color = UIColor(mode == .active ? Color.holdActive : Color.restBlue)
        for (id, nodes) in contactNodes {
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
        bounds: BoardModelBounds,
        display: BoardModelDisplay,
        orientation: BoardModelOrientation,
        positionID: String
    ) -> SuspendedCameraFraming? {
        guard orientation.pivot == "modelBoundsCenter",
              let components = orientation.rotations[positionID],
              let quaternion = quaternion(from: components),
              bounds.minimum.count == 3, bounds.maximum.count == 3 else {
            return nil
        }
        // Project the rotated corners directly into the camera plane. A new
        // axis-aligned box would overestimate oblique views of the rotated model.
        return framing(
            points: rotatedCorners(bounds, by: quaternion, pivot: boundsCenter(bounds)),
            display: display
        )
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
        guard orientCamera(at: framing.target, up: framing.up) else { return }
        scene.rootNode.addChildNode(camera)

        let ambient = SCNNode()
        ambient.light = SCNLight()
        ambient.light?.type = .ambient
        ambient.light?.intensity = 250
        ambient.light?.categoryBitMask = Self.renderedCategory
        scene.rootNode.addChildNode(ambient)
        let key = SCNNode()
        key.light = SCNLight()
        key.light?.type = .directional
        key.light?.intensity = 850
        key.light?.categoryBitMask = Self.renderedCategory
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
    let contacts: [PhysicalContact]
    let positionID: String?
    let highlightedContactIDs: Set<String>
    let highlightMode: BoardHighlightMode
    let onContactTap: ((PhysicalContact) -> Void)?
    let onUnavailable: (() -> Void)?
    var isDisplayOnly = false

    func makeUIView(context: Context) -> BoardModelSCNView {
        let view = BoardModelSCNView()
        view.backgroundColor = .clear
        view.isOpaque = false
        view.antialiasingMode = .multisampling4X
        view.rendersContinuously = false
        view.isPlaying = false
        view.allowsCameraControl = false
        view.boardName = boardName
        view.contacts = contacts
        view.positionID = positionID
        view.highlightedContactIDs = highlightedContactIDs
        view.onContactTap = onContactTap
        view.onUnavailable = onUnavailable
        view.display(model)
        view.delegate = view
        let orbitPan = OrbitPanGestureRecognizer(target: view, action: #selector(view.orbitPan(_:)))
        orbitPan.delegate = view.orbitGestureDelegate
        view.addGestureRecognizer(orbitPan)
        view.orbitPanGesture = orbitPan
        let tapGesture = UITapGestureRecognizer(target: view, action: #selector(view.selectContact(_:)))
        tapGesture.delegate = view
        // Short taps never clear orbit activation distance, so the pan fails
        // and the contact tap can recognize without being stolen by micro-drags.
        tapGesture.require(toFail: orbitPan)
        view.addGestureRecognizer(tapGesture)
        view.contactTapGesture = tapGesture
        view.addGestureRecognizer(UIPinchGestureRecognizer(target: view, action: #selector(view.orbitPinch(_:))))
        // Pose first, then paint. Dual and other multi-pose boards rebuild the
        // visible transform in select(); highlighting beforehand can leave
        // lastHighlights stuck while the posed materials never receive color.
        view.selectPositionIfNeeded()
        view.applyHighlights(highlightedContactIDs, mode: highlightMode)
        view.updateAccessibility()
        view.updateTapGesturePresence()
        return view
    }

    func updateUIView(_ view: BoardModelSCNView, context: Context) {
        view.display(model)
        view.boardName = boardName
        view.contacts = contacts
        view.positionID = positionID
        view.onContactTap = onContactTap
        view.onUnavailable = onUnavailable
        view.highlightedContactIDs = highlightedContactIDs
        view.isUserInteractionEnabled = !isDisplayOnly
        view.needsAccessibilityProjection = true
        view.selectPositionIfNeeded()
        view.applyHighlights(highlightedContactIDs, mode: highlightMode)
        view.updateAccessibility()
        view.updateTapGesturePresence()
    }

    static func dismantleUIView(_ view: BoardModelSCNView, coordinator: ()) {
        view.onContactTap = nil
        view.onUnavailable = nil
        view.accessibilityElements = nil
        view.delegate = nil
        view.scene = nil
        view.model = nil
        view.contactTapGesture = nil
        view.orbitPanGesture = nil
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

class BoardModelSCNView: SCNView, SCNSceneRendererDelegate, UIGestureRecognizerDelegate {
    var model: BoardModelScene?
    var boardName = "hangboard"
    var contacts: [PhysicalContact] = []
    var highlightedContactIDs: Set<String> = []
    var onContactTap: ((PhysicalContact) -> Void)?
    var onUnavailable: (() -> Void)?
    var positionID: String?
    var needsAccessibilityProjection = true
    let orbitGestureDelegate = OrbitPanGestureDelegate()
    var orbitPanGesture: OrbitPanGestureRecognizer?
    var contactTapGesture: UITapGestureRecognizer?
    private var contactAccessibilityElements: [String: BoardModelAccessibilityElement] = [:]
    private var accessibilityContactIDs: [String] = []
    private var accessibilityProjection: AccessibilityProjection?
    private var animatedResetRenderGeneration = 0

    private struct AccessibilityProjection: Equatable {
        let cameraTransform: SCNMatrix4
        let presentationTransform: SCNMatrix4
        let projectionTransform: SCNMatrix4
        let orthographicScale: Double
        let presentationProjection: SCNMatrix4
        let presentationScale: Double
        let viewport: CGRect

        static func == (lhs: Self, rhs: Self) -> Bool {
            SCNMatrix4EqualToMatrix4(lhs.cameraTransform, rhs.cameraTransform)
                && SCNMatrix4EqualToMatrix4(lhs.presentationTransform, rhs.presentationTransform)
                && SCNMatrix4EqualToMatrix4(lhs.projectionTransform, rhs.projectionTransform)
                && lhs.orthographicScale == rhs.orthographicScale
                && SCNMatrix4EqualToMatrix4(lhs.presentationProjection, rhs.presentationProjection)
                && lhs.presentationScale == rhs.presentationScale
                && lhs.viewport == rhs.viewport
        }
    }

    private var currentAccessibilityProjection: AccessibilityProjection? {
        guard let pointOfView, let camera = pointOfView.camera else { return nil }
        return AccessibilityProjection(
            cameraTransform: pointOfView.worldTransform,
            presentationTransform: pointOfView.presentation.worldTransform,
            projectionTransform: camera.projectionTransform,
            orthographicScale: camera.orthographicScale,
            presentationProjection: pointOfView.presentation.camera?.projectionTransform ?? camera.projectionTransform,
            presentationScale: pointOfView.presentation.camera?.orthographicScale ?? camera.orthographicScale,
            viewport: bounds
        )
    }

    override func gestureRecognizerShouldBegin(_ gestureRecognizer: UIGestureRecognizer) -> Bool {
        guard gestureRecognizer is UITapGestureRecognizer else { return true }
        return onContactTap != nil
    }

    func updateTapGesturePresence() {
        let shouldHaveTap = onContactTap != nil
        if let contactTapGesture, !shouldHaveTap {
            removeGestureRecognizer(contactTapGesture)
            self.contactTapGesture = nil
        } else if contactTapGesture == nil, shouldHaveTap {
            let tap = UITapGestureRecognizer(target: self, action: #selector(selectContact(_:)))
            tap.delegate = self
            if let orbitPanGesture {
                tap.require(toFail: orbitPanGesture)
            }
            addGestureRecognizer(tap)
            self.contactTapGesture = tap
        }
    }

    private func requestPausedRedraw() {
        guard !rendersContinuously, !isPlaying else { return }
        setNeedsDisplay()
    }

    private func requestAnimatedResetRedraw() {
        needsAccessibilityProjection = true
        guard !rendersContinuously, !isPlaying else {
            setNeedsDisplay()
            return
        }

        // A paused SCNView renders a single dirty frame, which leaves
        // presentation transforms frozen while an implicit camera
        // transaction is running. Keep the renderer alive through the short
        // canonical transition so accessibility projection follows the
        // presentation camera, then return to the board's paused state.
        animatedResetRenderGeneration &+= 1
        let generation = animatedResetRenderGeneration
        rendersContinuously = true
        setNeedsDisplay()
        let duration = BoardModelScene.canonicalTransitionDuration + 0.1
        DispatchQueue.main.asyncAfter(deadline: .now() + duration) { [weak self] in
            guard let self, self.animatedResetRenderGeneration == generation else { return }
            self.rendersContinuously = false
            self.needsAccessibilityProjection = true
            self.setNeedsDisplay()
        }
    }

    func display(_ model: BoardModelScene) {
        guard self.model !== model else { return }
        self.model = model
        scene = model.scene
        pointOfView = model.camera
        model.frame(in: bounds.size)
        needsAccessibilityProjection = true
        requestPausedRedraw()
    }

    func selectPositionIfNeeded() {
        guard let model else { return }
        let didSelect = model.select(positionID: positionID)
        scene = model.scene
        pointOfView = model.camera
        needsAccessibilityProjection = true
        requestPausedRedraw()
        guard didSelect else {
            onUnavailable?()
            return
        }
    }

    override func layoutSubviews() {
        super.layoutSubviews()
        model?.frame(in: bounds.size)
        needsAccessibilityProjection = true
        requestPausedRedraw()
        updateAccessibility()
    }

    nonisolated func renderer(_ renderer: any SCNSceneRenderer, didRenderScene scene: SCNScene, atTime time: TimeInterval) {
        DispatchQueue.main.async { [weak self] in
            guard let self else { return }
            // Camera gestures and implicit reset animations can change projection
            // without a SwiftUI update. Refresh only when a rendered state changes.
            guard self.needsAccessibilityProjection
                    || self.accessibilityProjection != self.currentAccessibilityProjection else { return }
            self.updateAccessibility()
        }
    }

    @objc func selectContact(_ recognizer: UITapGestureRecognizer) {
        guard let model, onContactTap != nil else { return }
        // CPU-only nearest-hit regressions require this commit before SceneKit
        // traverses newly cloned geometry.
        SCNTransaction.flush()
        guard let hit = hitTest(recognizer.location(in: self), options: [
            SCNHitTestOption.categoryBitMask: BoardModelScene.modelPickCategory,
            SCNHitTestOption.searchMode: SCNHitTestSearchMode.closest.rawValue
        ]).first,
              let id = model.contactID(for: hit.node),
              let contact = contacts.first(where: { $0.id == id }) else { return }
        onContactTap?(contact)
        requestAnimatedResetRedraw()
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
        requestPausedRedraw()
    }

    @objc func orbitPinch(_ recognizer: UIPinchGestureRecognizer) {
        guard let model, recognizer.state == .changed else { return }
        model.orbit(azimuth: 0, elevation: 0, zoomScale: Float(recognizer.scale))
        recognizer.scale = 1
        requestPausedRedraw()
    }

    func applyHighlights(_ ids: Set<String>, mode: BoardHighlightMode) {
        highlightedContactIDs = ids
        model?.highlight(ids, mode: mode)
        requestPausedRedraw()
    }

    func updateAccessibility() {
        needsAccessibilityProjection = false
        accessibilityProjection = currentAccessibilityProjection
        guard let onContactTap, let model else {
            isAccessibilityElement = true
            accessibilityLabel = "\(boardName) hangboard"
            accessibilityValue = contacts.filter { highlightedContactIDs.contains($0.id) }.map(\.name).joined(separator: ", ")
            accessibilityElements = nil
            contactAccessibilityElements.removeAll()
            accessibilityContactIDs = []
            return
        }
        isAccessibilityElement = false
        let elements = contacts.compactMap { contact -> UIAccessibilityElement? in
            guard let node = model.contactNodes[contact.id]?.first else { return nil }
            let box = node.boundingBox
            let center = SCNVector3((box.min.x + box.max.x) / 2, (box.min.y + box.max.y) / 2, (box.min.z + box.max.z) / 2)
            let projected = projectPoint(node.convertPosition(center, to: nil))
            guard projected.x.isFinite, projected.y.isFinite else { return nil }
            let element = contactAccessibilityElements[contact.id]
                ?? BoardModelAccessibilityElement(accessibilityContainer: self)
            contactAccessibilityElements[contact.id] = element
            element.accessibilityLabel = contact.name
            element.accessibilityIdentifier = "boardModel.contact.\(contact.id)"
            element.accessibilityTraits = highlightedContactIDs.contains(contact.id) ? [.button, .selected] : .button
            element.accessibilityFrameInContainerSpace = CGRect(x: CGFloat(projected.x) - 18, y: CGFloat(projected.y) - 18, width: 36, height: 36)
            element.action = { onContactTap(contact) }
            return element
        }
        let ids = elements.compactMap(\.accessibilityIdentifier)
        if accessibilityContactIDs != ids {
            accessibilityElements = elements
            accessibilityContactIDs = ids
        }
    }
}
