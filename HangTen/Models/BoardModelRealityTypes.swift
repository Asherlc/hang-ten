import Foundation
import RealityKit
import ModelIO
import SwiftUI
import UIKit
import simd
import CryptoKit

/// RealityKit-native scene that owns the full model lifecycle.
@MainActor
final class BoardModelRealityScene {
    // Core state
    let root = Entity()
    let camera = PerspectiveCamera()

    var modelEntity: ModelEntity?
    var instanceEntities: [Entity] = []
    var contactEntities: [String: [ModelEntity]] = [:]
    private var contactIDByEntity: [Entity: String] = [:]
    private var originalMaterials: [Entity: PhysicallyBasedMaterial] = [:]

    // Suspension/camera state
    private var suspension: BoardModelSuspension?
    private var verifiedPresentations: [String: (BoardModelSolvedSuspension, ModelEntity)] = [:]
    private var canonicalFraming: SuspendedCameraFraming?
    private var currentFraming: SuspendedCameraFraming?
    private var activePositionID: String?

    // Orbit state
    private var orbitAzimuth: Float = 0
    private var orbitElevation: Float = 0
    private var orbitZoom: Float = 1
    private var viewportSize: CGSize = .zero

    // Config
    private let descriptor: BoardModelDescriptor
    private let display: BoardModelDisplay
    private let orientation: BoardModelOrientation?
    private let allowedPositionIDs: Set<String>

    init(descriptor: BoardModelDescriptor, display: BoardModelDisplay, suspension: BoardModelSuspension?, orientation: BoardModelOrientation?, allowedPositionIDs: Set<String>) {
        self.descriptor = descriptor
        self.display = display
        self.suspension = suspension
        self.orientation = orientation
        self.allowedPositionIDs = allowedPositionIDs
    }

    /// Loads the USDZ model from the given URL using ModelIO and binds descriptor nodes.
    func load(usdzURL: URL) async throws {
        // Load via ModelIO (MDLAsset) for validation, then load via RealityKit
        let asset = MDLAsset(url: usdzURL)
        asset.loadTextures()
        
        // Verify asset has meshes
        guard asset.count > 0 else {
            throw NSError(domain: "BoardModelRealityScene", code: -1, userInfo: [NSLocalizedDescriptionKey: "No meshes found in USDZ"])
        }
        
        // Load the USDZ as RealityKit entities (uses ModelIO internally)
        let modelEntity = try await ModelEntity(contentsOf: usdzURL)
        
        // Add to scene root
        root.addChild(modelEntity)
        self.modelEntity = modelEntity
        
        // Build instance entities (for now, treat the loaded hierarchy as a single instance)
        // For boards with multiple instances, this would be expanded per instance descriptor
        instanceEntities = [modelEntity]
        
        // Build contact entity mapping from descriptor
        buildContactEntities()
        
        // Apply neutral PBR materials to all model entities
        applyNeutralMaterials(to: root)
        
        // Set up camera framing based on model bounds
        setupCameraFraming()
    }
    
    private func applyNeutralMaterials(to entity: Entity) {
        if let modelEntity = entity as? ModelEntity {
            let material = Self.neutralMaterial()
            modelEntity.model?.materials = [material]
            originalMaterials[modelEntity] = material
        }
        for child in entity.children {
            applyNeutralMaterials(to: child)
        }
    }
    
    private func setupCameraFraming() {
        // Compute bounds from all model entities
        var minBounds = SIMD3<Float>(repeating: .greatestFiniteMagnitude)
        var maxBounds = SIMD3<Float>(repeating: -.greatestFiniteMagnitude)
        var foundBounds = false
        var allPoints: [SIMD3<Float>] = []
        
        for entity in instanceEntities {
            let bounds = entity.visualBounds(relativeTo: nil)
            if bounds.min.x.isFinite {
                foundBounds = true
                minBounds = simd_min(minBounds, bounds.min)
                maxBounds = simd_max(maxBounds, bounds.max)
                // Collect corner points for framing
                let corners = [
                    SIMD3<Float>(bounds.min.x, bounds.min.y, bounds.min.z),
                    SIMD3<Float>(bounds.max.x, bounds.min.y, bounds.min.z),
                    SIMD3<Float>(bounds.min.x, bounds.max.y, bounds.min.z),
                    SIMD3<Float>(bounds.max.x, bounds.max.y, bounds.min.z),
                    SIMD3<Float>(bounds.min.x, bounds.min.y, bounds.max.z),
                    SIMD3<Float>(bounds.max.x, bounds.min.y, bounds.max.z),
                    SIMD3<Float>(bounds.min.x, bounds.max.y, bounds.max.z),
                    SIMD3<Float>(bounds.max.x, bounds.max.y, bounds.max.z),
                ]
                allPoints.append(contentsOf: corners)
            }
        }
        
        guard foundBounds else { return }
        
        let center = (minBounds + maxBounds) / 2
        let size = maxBounds - minBounds
        let maxDim = max(size.x, max(size.y, size.z))
        
        // Create a framing similar to SuspendedCameraFraming
        let distance = maxDim * 2.5
        let target = center
        let direction = SIMD3<Float>(0, 0, -1)
        let up = SIMD3<Float>(0, 1, 0)
        let right = SIMD3<Float>(1, 0, 0)
        let viewDirection = SIMD3<Float>(0, 0, 1)
        
        // Calculate width/height/depth for framing
        let width = size.x * 1.2
        let height = size.y * 1.2
        let depth = size.z * 1.2
        let fitPadding: Float = 1.1
        
        currentFraming = SuspendedCameraFraming(
            target: target,
            direction: direction,
            viewDirection: viewDirection,
            right: right,
            up: up,
            distance: distance,
            width: width,
            height: height,
            depth: depth,
            fitPadding: fitPadding,
            includedPoints: allPoints
        )
        canonicalFraming = currentFraming
        
        // Position camera
        updateCameraTransform()
    }
    
    static func neutralMaterial() -> PhysicallyBasedMaterial {
        var material = PhysicallyBasedMaterial()
        material.baseColor = .init(tint: UIColor(red: 0.82, green: 0.80, blue: 0.77, alpha: 1))
        material.roughness = .init(floatLiteral: 0.5)
        material.metallic = .init(floatLiteral: 0)
        return material
    }

    func select(positionID: String?) -> Bool {
        guard let positionID, allowedPositionIDs.contains(positionID) else {
            activePositionID = nil
            return false
        }
        activePositionID = positionID
        return true
    }

    func orbit(azimuth: Float, elevation: Float, zoomScale: Float = 1) {
        orbitAzimuth = azimuth
        orbitElevation = elevation
        orbitZoom = zoomScale
        updateCameraTransform()
    }

    func resetCamera(animated: Bool, completion: (() -> Void)? = nil) {
        orbitAzimuth = 0
        orbitElevation = 0
        orbitZoom = 1
        updateCameraTransform(animated: animated, completion: completion)
    }

    func highlight(_ contactIDs: Set<String>, mode: BoardHighlightMode) {
        // Apply highlight materials to contact entities
        for (contactID, entities) in contactEntities {
            let isHighlighted = contactIDs.contains(contactID)
            let highlightColor: Color = isHighlighted ? (mode == .active ? Color.holdActive : Color.restBlue) : .clear
            for entity in entities {
                applyHighlight(to: entity, color: highlightColor, mode: mode)
            }
        }
    }

    func contactID(for entity: Entity) -> String? {
        contactIDByEntity[entity]
    }

    func frame(in size: CGSize) {
        viewportSize = size
        updateCameraTransform()
    }

    func fittedOrthographicScale(in size: CGSize) -> Double? {
        guard let framing = currentFraming else { return nil }
        // Calculate orthographic scale based on framing
        return Double(max(framing.width, framing.height) * framing.fitPadding)
    }

    private func buildContactEntities() {
        // Build a mapping from nodeID to contactID using the descriptor
        let nodeIDToContactID: [String: String] = Dictionary(uniqueKeysWithValues:
            descriptor.nodes.compactMap { node in
                guard node.role == .contact, let contactID = node.contactID else { return nil }
                return (node.nodeID, contactID)
            }
        )

        // Traverse model entity hierarchy and build contact entity mapping
        traverseEntities(root) { entity in
            if let modelEntity = entity as? ModelEntity,
               let contactID = findContactID(for: entity, nodeIDToContactID: nodeIDToContactID) {
                contactEntities[contactID, default: []].append(modelEntity)
                contactIDByEntity[modelEntity] = contactID
                originalMaterials[modelEntity] = modelEntity.model?.materials.first as? PhysicallyBasedMaterial
            }
        }
    }
    
    private func traverseEntities(_ entity: Entity, _ visit: (Entity) -> Void) {
        visit(entity)
        for child in entity.children {
            traverseEntities(child, visit)
        }
    }

    private func findContactID(for entity: Entity, nodeIDToContactID: [String: String]) -> String? {
        // Find contact ID from entity name (USDZ import uses node names)
        if let contactID = nodeIDToContactID[entity.name] {
            return contactID
        }
        // Also check if any parent has a matching name
        var current: Entity? = entity
        while let parent = current?.parent {
            if let contactID = nodeIDToContactID[parent.name] {
                return contactID
            }
            current = parent
        }
        return nil
    }

    private func applyHighlight(to entity: ModelEntity, color: Color, mode: BoardHighlightMode) {
        guard var material = entity.model?.materials.first as? PhysicallyBasedMaterial else { return }

        if color == .clear {
            // Restore original material
            if let originalMaterial = originalMaterials[entity] {
                entity.model?.materials = [originalMaterial]
            }
            return
        }

        // Apply highlight by setting a tint color
        let uiColor = UIColor(color)
        material.baseColor = .init(tint: uiColor.withAlphaComponent(0.6))
        material.roughness = .init(floatLiteral: 0.8)

        entity.model?.materials = [material]
    }

private func updateCameraTransform(animated: Bool = false, completion: (() -> Void)? = nil) {
        // Update camera position based on orbit state and framing
        let distance = (currentFraming?.distance ?? 1) * orbitZoom
        let x = distance * cos(orbitElevation) * sin(orbitAzimuth)
        let y = distance * sin(orbitElevation)
        let z = distance * cos(orbitElevation) * cos(orbitAzimuth)

        let target = currentFraming?.target ?? SIMD3<Float>(0, 0, 0)
        camera.position = target + SIMD3<Float>(x, y, z)
        camera.look(at: target, from: camera.position, relativeTo: nil)

        if animated {
            // Animate camera transition
        }
        completion?()
    }
}

/// Identity for a decoded package model. The hash makes replacement assets a
/// distinct cached source even when a board keeps the same presentation ID.
struct BoardModelRealityKey: Hashable, Sendable {
    let boardID: String
    let presentationID: String
    let modelSHA256: String
}

/// Resource lease for on-demand model assets.
final class BoardModelRealityResourceLease {
    let url: URL
    private var lease: BoardModelResourceLease?

    init(url: URL, lease: BoardModelResourceLease? = nil) {
        self.url = url
        self.lease = lease
    }

    deinit {
        // BoardModelResourceLease's deinit will call endAccessingResources
    }
}

/// Cache for loaded RealityKit model sources.
@MainActor
private enum BoardModelRealityCache {
    private final class InFlight {
        var task: Task<BoardModelRealityLoadedSource?, Error>?
        var waiters: [UUID: CheckedContinuation<BoardModelRealityLoadedSource?, Error>] = [:]
    }

    private static var loading: [BoardModelRealityKey: InFlight] = [:]

    static func source(
        for key: BoardModelRealityKey,
        media: BoardModelMedia,
        board: BoardRevision,
        presentationID: String,
        store: BoardPackageStore,
        resourceAccess: BoardModelResourceAccess
    ) async throws -> BoardModelRealityLoadedSource? {
        let waiterID = UUID()
        return try await withTaskCancellationHandler {
            try await withCheckedThrowingContinuation { continuation in
                guard !Task.isCancelled else {
                    continuation.resume(throwing: CancellationError())
                    return
                }
                if let entry = loading[key] {
                    entry.waiters[waiterID] = continuation
                    return
                }
                let entry = InFlight()
                entry.waiters[waiterID] = continuation
                loading[key] = entry
entry.task = Task<BoardModelRealityLoadedSource?, Error> {
                        var result: BoardModelRealityLoadedSource?
                        do {
                            result = try await loadSource(
                                media: media,
                                board: board,
                                presentationID: presentationID,
                                store: store,
                                resourceAccess: resourceAccess
                            )
                            // A canceled acquisition may finish after a replacement
                            // load has started for the same model identity.
                            guard loading[key] === entry else { return nil }
                            loading[key] = nil
                            let waiters = entry.waiters
                            entry.waiters.removeAll()
                            for waiter in waiters.values {
                                waiter.resume(returning: result)
                            }
                        } catch {
                            // Propagate error to all waiters
                            guard loading[key] === entry else { return nil }
                            loading[key] = nil
                            let waiters = entry.waiters
                            entry.waiters.removeAll()
                            for waiter in waiters.values {
                                waiter.resume(throwing: error)
                            }
                        }
                        return result
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
                waiter.resume(throwing: CancellationError())
            }
        }
    }

    private static func loadSource(
        media: BoardModelMedia,
        board: BoardRevision,
        presentationID: String,
        store: BoardPackageStore,
        resourceAccess: BoardModelResourceAccess
    ) async throws -> BoardModelRealityLoadedSource? {
        let resourceLease: BoardModelRealityResourceLease?
        if let bundledURL = store.presentationAssetURL(
            for: board,
            presentationID: presentationID
        ) {
            resourceLease = BoardModelRealityResourceLease(url: bundledURL)
        } else if let resource = store.modelResource(
            for: board,
            presentationID: presentationID
        ) {
            if let packagedURL = resource.debugSimulatorPackagedURL(in: store.resourceBundle) {
                resourceLease = BoardModelRealityResourceLease(url: packagedURL)
            } else {
                if let lease = await resourceAccess.acquire(
                    resource,
                    bundle: store.resourceBundle
                ) {
                    resourceLease = BoardModelRealityResourceLease(url: lease.url, lease: lease)
                } else {
                    resourceLease = nil
                }
            }
        } else {
            resourceLease = nil
        }
        guard let resourceLease, !Task.isCancelled else { return nil }

        // Verify SHA-256
        let computedSHA256 = sha256(of: resourceLease.url)
        guard computedSHA256 == media.descriptor.modelSHA256 else {
            return nil
        }

        return BoardModelRealityLoadedSource(resourceLease: resourceLease)
    }

    private static func sha256(of url: URL) -> String? {
        // 1 MB read buffer for streaming hash computation
        let readBufferSize = 1_048_576
        do {
            let handle = try FileHandle(forReadingFrom: url)
            defer { try? handle.close() }
            var hash = SHA256()
            while let data = try handle.read(upToCount: readBufferSize), !data.isEmpty {
                hash.update(data: data)
            }
            return hash.finalize().map { String(format: "%02x", $0) }.joined()
        } catch {
            return nil
        }
    }
}

struct BoardModelRealityLoadedSource {
    let resourceLease: BoardModelRealityResourceLease
}

/// Load gate to serialize 3D model loads.
/// Limit is 1 because RealityKit model loading is memory-intensive and concurrent
/// loads can cause OOM or GPU resource contention on iOS devices.
@MainActor
private enum BoardModelRealityLoadGate {
    private static let limit = 1
    private static var active = 0
    private static var waiters: [(id: UUID, continuation: CheckedContinuation<Bool, Never>)] = []

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
            waiters.removeFirst().continuation.resume(returning: true)
        }
    }
}

/// Loader with SHA-256 verify, cache, resource lease.
@MainActor
final class BoardModelRealityLoader {
    static func load(
        board: BoardRevision,
        presentation: BoardPresentation,
        store: BoardPackageStore = BoardCatalog.packageStore,
        resourceAccess: BoardModelResourceAccess = .live
    ) async throws -> BoardModelRealityScene {
        guard case .model(let media) = presentation.media else {
            throw NSError(domain: "BoardModelRealityLoader", code: -1, userInfo: [NSLocalizedDescriptionKey: "Presentation is not a model"])
        }

        guard await BoardModelRealityLoadGate.acquire() else {
            throw NSError(domain: "BoardModelRealityLoader", code: -2, userInfo: [NSLocalizedDescriptionKey: "Load gate cancelled"])
        }
        defer { BoardModelRealityLoadGate.release() }

        let key = BoardModelRealityKey(
            boardID: board.id,
            presentationID: presentation.id,
            modelSHA256: media.descriptor.modelSHA256
        )

        guard let source = try await BoardModelRealityCache.source(
            for: key,
            media: media,
            board: board,
            presentationID: presentation.id,
            store: store,
            resourceAccess: resourceAccess
        ), !Task.isCancelled else {
            throw NSError(domain: "BoardModelRealityLoader", code: -3, userInfo: [NSLocalizedDescriptionKey: "Failed to load model source"])
        }

        let scene = BoardModelRealityScene(
            descriptor: media.descriptor,
            display: media.display,
            suspension: media.suspension,
            orientation: media.orientation,
            allowedPositionIDs: Set(board.positions.filter {
                $0.presentationID == presentation.id
            }.map(\.id))
        )

        // Load the USDZ model via ModelIO
        try await scene.load(usdzURL: source.resourceLease.url)

        return scene
    }
}