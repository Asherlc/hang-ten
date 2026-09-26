import Foundation
import RealityKit
import ModelIO
import SwiftUI
import UIKit
import simd
import CryptoKit

/// Errors specific to board model RealityKit loading and caching.
enum BoardModelRealityError: Error, Equatable {
    case resourceUnavailable
    case sha256Mismatch(expected: String, actual: String)
    case fileReadError(underlying: String)
    case invalidUSDZ(reason: String)
    case loadGateCancelled
    case loadFailed(reason: String)
    case presentationNotModel
    case cacheError(reason: String)
    case missingModelEntity
    case missingContactDescriptor(contactID: String)
    case invalidSuspension
    case clearanceCheckFailed
    case geometryProcessingFailed(reason: String)
}

/// RealityKit-native scene that owns the full model lifecycle.
@MainActor
final class BoardModelRealityScene {
    // Core state
    let root = Entity()
    let camera = PerspectiveCamera()

    var modelEntity: Entity?
    var instanceEntities: [Entity] = []
    var contactEntities: [String: [ModelEntity]] = [:]
    private(set) var transientCordEntity: Entity?
    private var contactIDByEntity: [Entity: String] = [:]
    private var baselineMaterials: [Entity: PhysicallyBasedMaterial] = [:]

    // Suspension/camera state
    private var suspension: BoardModelSuspension?
    private var verifiedPresentations: [String: (BoardModelSolvedSuspension, ModelEntity)] = [:]
    private var canonicalFraming: SuspendedCameraFraming?
    private var currentFraming: SuspendedCameraFraming?
    private var activePositionID: String?

    // Orbit state
    var orbitAzimuth: Float = 0
    var orbitElevation: Float = 0
    var orbitZoom: Float = 1
    private var viewportSize: CGSize = .zero
    private var lastHighlightedContactIDs: Set<String>?
    private var lastHighlightMode: BoardHighlightMode?

    // Config
    private let descriptor: BoardModelDescriptor
    private let display: BoardModelDisplay
    private let orientation: BoardModelOrientation?
    private let allowedPositionIDs: Set<String>
    private let instances: [BoardModelInstance]?

    // Retain the resource lease until the scene is deallocated,
    // because RealityKit may still stream textures from the USDZ asynchronously.
    // The lease is released automatically when BoardModelRealityResourceLease deinitializes.
    private let resourceLease: BoardModelRealityResourceLease

    // Testing accessors
    var descriptorForTesting: BoardModelDescriptor { descriptor }
    var displayForTesting: BoardModelDisplay { display }
    var orientationForTesting: BoardModelOrientation? { orientation }
    var suspensionForTesting: BoardModelSuspension? { suspension }
    var instancesForTesting: [BoardModelInstance]? { instances }

    init(descriptor: BoardModelDescriptor, display: BoardModelDisplay, suspension: BoardModelSuspension?, orientation: BoardModelOrientation?, allowedPositionIDs: Set<String>, instances: [BoardModelInstance]? = nil, resourceLease: BoardModelRealityResourceLease) {
        self.descriptor = descriptor
        self.display = display
        self.suspension = suspension
        self.orientation = orientation
        self.allowedPositionIDs = allowedPositionIDs
        self.instances = instances
        self.resourceLease = resourceLease
    }

    /// Loads the USDZ model from the given URL using ModelIO and binds descriptor nodes.
    func load(usdzURL: URL) async throws {
        // Load via ModelIO (MDLAsset) for validation, then load via RealityKit
        let asset = MDLAsset(url: usdzURL)
        asset.loadTextures()
        
        // Verify asset has meshes
        guard asset.count > 0 else {
            throw BoardModelRealityError.invalidUSDZ(reason: "No meshes found in USDZ")
        }
        
        // Load the USDZ as RealityKit entity hierarchy (preserves node structure)
        let modelEntity = try await Entity(contentsOf: usdzURL)
        
        self.modelEntity = modelEntity
        
        // Build instance entities from media instances
        if let instances = instances, !instances.isEmpty {
            buildInstanceEntities(from: modelEntity, instances: instances)
        } else {
            // Single instance (legacy behavior)
            root.addChild(modelEntity)
            instanceEntities = [modelEntity]
        }
        
        // Apply neutral PBR materials to all model entities FIRST
        // This captures original USDZ materials before they're replaced
        applyNeutralMaterials(to: root)
        
        // Build contact entity mapping from descriptor
        // Neutral highlight baselines were captured by applyNeutralMaterials().
        buildContactEntities()
        
        // Set up camera framing based on model bounds
        setupCameraFraming()
    }
    
    private func buildInstanceEntities(from sourceEntity: Entity, instances: [BoardModelInstance]) {
        instanceEntities = []
        let center = Self.boundsCenter(descriptor.modelBounds)
        
        for instance in instances {
            // Clone the source entity hierarchy for this instance
            let instanceEntity = sourceEntity.clone(recursive: true)
            
            instanceEntity.transform = Transform(matrix: Self.instanceMatrix(
                instance: instance, positionID: nil, center: center))
            
            root.addChild(instanceEntity)
            instanceEntities.append(instanceEntity)
        }
    }
    
    private func applyNeutralMaterials(to entity: Entity) {
        if let modelEntity = entity as? ModelEntity,
           let model = modelEntity.model {
            let material = Self.neutralMaterial()
            modelEntity.model?.materials = [material]
            baselineMaterials[modelEntity] = material
        }
        for child in entity.children {
            applyNeutralMaterials(to: child)
        }
    }
    
    private func setupCameraFraming() {
        var allPoints: [SIMD3<Float>] = []
        for entity in instanceEntities {
            let bounds = entity.visualBounds(relativeTo: nil)
            guard [bounds.min.x, bounds.min.y, bounds.min.z,
                   bounds.max.x, bounds.max.y, bounds.max.z].allSatisfy(\.isFinite) else { continue }
            allPoints.append(contentsOf: [
                SIMD3<Float>(bounds.min.x, bounds.min.y, bounds.min.z),
                SIMD3<Float>(bounds.max.x, bounds.min.y, bounds.min.z),
                SIMD3<Float>(bounds.min.x, bounds.max.y, bounds.min.z),
                SIMD3<Float>(bounds.max.x, bounds.max.y, bounds.min.z),
                SIMD3<Float>(bounds.min.x, bounds.min.y, bounds.max.z),
                SIMD3<Float>(bounds.max.x, bounds.min.y, bounds.max.z),
                SIMD3<Float>(bounds.min.x, bounds.max.y, bounds.max.z),
                SIMD3<Float>(bounds.max.x, bounds.max.y, bounds.max.z),
            ])
        }
        guard allPoints.count >= 8,
              display.camera.viewDirection.count == 3,
              display.camera.up.count == 3,
              display.camera.viewDirection.allSatisfy(\.isFinite),
              display.camera.up.allSatisfy(\.isFinite),
              display.camera.fitPadding.isFinite, display.camera.fitPadding > 0 else { return }
        let requestedDirection = SIMD3<Float>(display.camera.viewDirection.map(Float.init))
        let requestedUp = SIMD3<Float>(display.camera.up.map(Float.init))
        guard simd_length(requestedDirection) > 1e-6, simd_length(requestedUp) > 1e-6 else { return }
        let direction = simd_normalize(requestedDirection)
        let rawRight = simd_cross(direction, simd_normalize(requestedUp))
        guard simd_length(rawRight) > 1e-6 else { return }
        let right = simd_normalize(rawRight)
        let up = simd_normalize(simd_cross(right, direction))
        let horizontal = allPoints.map { simd_dot($0, right) }
        let vertical = allPoints.map { simd_dot($0, up) }
        let depth = allPoints.map { simd_dot($0, direction) }
        guard let minH = horizontal.min(), let maxH = horizontal.max(),
              let minV = vertical.min(), let maxV = vertical.max(),
              let minD = depth.min(), let maxD = depth.max() else { return }
        let expansion = Float(display.camera.boundsExpansionFactor ?? 1)
        let width = (maxH - minH) * expansion
        let height = (maxV - minV) * expansion
        let depthSpan = (maxD - minD) * expansion
        guard width.isFinite, height.isFinite, depthSpan.isFinite,
              width > 0, height > 0, depthSpan > 0 else { return }
        let fitPadding = Float(1 + display.camera.fitPadding * 2)
        let target = right * ((minH + maxH) / 2)
            + up * ((minV + maxV) / 2)
            + direction * ((minD + maxD) / 2)
        // `fitPadding` retains the board package's existing orthographic fit
        // margin. Convert that fitted span into a perspective camera distance.
        let defaultDistanceMultiplier = 1 + display.camera.fitPadding * 2
        let distance = max(width, max(height, depthSpan))
            * Float(display.camera.distanceMultiplier ?? defaultDistanceMultiplier)
        currentFraming = SuspendedCameraFraming(
            target: target,
            direction: direction,
            viewDirection: direction,
            right: right,
            up: up,
            distance: distance,
            width: width,
            height: height,
            depth: depthSpan,
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

    // Pure camera projection helpers shared by the board map and model tests.
    // Keep these independent of RealityKit entities so camera metadata can be
    // validated before a USDZ is loaded.
    static func rotatedBounds(_ bounds: BoardModelBounds, by quaternion: simd_quatf,
                              pivot: SIMD3<Float>) -> BoardModelBounds {
        let corners = rotatedCorners(bounds, by: quaternion, pivot: pivot)
        let minimum = SIMD3<Float>(corners.map(\.x).min() ?? 0,
                                   corners.map(\.y).min() ?? 0,
                                   corners.map(\.z).min() ?? 0)
        let maximum = SIMD3<Float>(corners.map(\.x).max() ?? 0,
                                   corners.map(\.y).max() ?? 0,
                                   corners.map(\.z).max() ?? 0)
        return BoardModelBounds(minimum: [Double(minimum.x), Double(minimum.y), Double(minimum.z)],
                                maximum: [Double(maximum.x), Double(maximum.y), Double(maximum.z)])
    }

    static func rotatedCorners(_ bounds: BoardModelBounds, by quaternion: simd_quatf,
                               pivot: SIMD3<Float>) -> [SIMD3<Float>] {
        boundsCorners(bounds).map { quaternion.act($0 - pivot) + pivot }
    }

    static func framing(bounds: BoardModelBounds, display: BoardModelDisplay,
                        orientation: BoardModelOrientation, positionID: String) -> SuspendedCameraFraming? {
        guard orientation.pivot == "modelBoundsCenter",
              let components = orientation.rotations[positionID],
              let rotation = cameraQuaternion(from: components),
              bounds.minimum.count == 3, bounds.maximum.count == 3 else { return nil }
        return framing(points: rotatedCorners(bounds, by: rotation, pivot: boundsCenter(bounds)), display: display)
    }

    static func framing(descriptor: BoardModelDescriptor,
                        display: BoardModelDisplay) -> SuspendedCameraFraming? {
        framing(bounds: descriptor.modelBounds, display: display)
    }

    static func framing(bounds: BoardModelBounds,
                        display: BoardModelDisplay) -> SuspendedCameraFraming? {
        framing(points: boundsCorners(bounds), display: display)
    }

    static func framing(points: [SIMD3<Float>], display: BoardModelDisplay) -> SuspendedCameraFraming? {
        let camera = display.camera
        guard points.count == 8, camera.type == "orthographic",
              camera.viewDirection.count == 3, camera.up.count == 3,
              camera.fitPadding.isFinite, camera.fitPadding > 0,
              points.allSatisfy({ $0.x.isFinite && $0.y.isFinite && $0.z.isFinite }),
              camera.viewDirection.allSatisfy(\.isFinite), camera.up.allSatisfy(\.isFinite) else { return nil }
        let target = points.reduce(SIMD3<Float>.zero, +) / Float(points.count)
        let requestedDirection = SIMD3<Float>(camera.viewDirection.map(Float.init))
        let requestedUp = SIMD3<Float>(camera.up.map(Float.init))
        guard simd_length(requestedDirection) > 0, simd_length(requestedUp) > 0 else { return nil }
        let direction = simd_normalize(requestedDirection)
        let cross = simd_cross(direction, simd_normalize(requestedUp))
        guard simd_length(cross) > 0 else { return nil }
        let right = simd_normalize(cross)
        let up = simd_cross(right, direction)
        let horizontal = points.map { simd_dot($0 - target, right) }
        let vertical = points.map { simd_dot($0 - target, up) }
        let depth = points.map { simd_dot($0 - target, direction) }
        guard let width = horizontal.max().flatMap({ hi in horizontal.min().map { hi - $0 } }),
              let height = vertical.max().flatMap({ hi in vertical.min().map { hi - $0 } }),
              let depthSpan = depth.max().flatMap({ hi in depth.min().map { hi - $0 } }),
              width.isFinite, height.isFinite, depthSpan.isFinite, width > 0, height > 0 else { return nil }
        let fitPadding = Float(1 + camera.fitPadding * 2)
        return SuspendedCameraFraming(target: target, direction: direction, viewDirection: direction,
                                      right: right, up: up, distance: max(width, max(height, depthSpan)) * fitPadding,
                                      width: width, height: height, depth: depthSpan,
                                      fitPadding: fitPadding, includedPoints: points)
    }

    private static func boundsCorners(_ bounds: BoardModelBounds) -> [SIMD3<Float>] {
        guard bounds.minimum.count == 3, bounds.maximum.count == 3 else { return [] }
        let lo = SIMD3<Float>(bounds.minimum.map(Float.init))
        let hi = SIMD3<Float>(bounds.maximum.map(Float.init))
        return [lo.x, hi.x].flatMap { x in [lo.y, hi.y].flatMap { y in
            [lo.z, hi.z].map { SIMD3<Float>(x, y, $0) }
        } }
    }

    private static func cameraQuaternion(from value: SIMD4<Double>) -> simd_quatf? {
        guard value.x.isFinite, value.y.isFinite, value.z.isFinite, value.w.isFinite else { return nil }
        let q = simd_quatf(ix: Float(value.x), iy: Float(value.y), iz: Float(value.z), r: Float(value.w))
        guard q.vector.x.isFinite, q.vector.y.isFinite, q.vector.z.isFinite,
              q.vector.w.isFinite, simd_length(q.vector) > 1e-6 else { return nil }
        return simd_normalize(q)
    }

    func select(positionID: String?) -> Bool {
        guard let positionID, allowedPositionIDs.contains(positionID) else {
            activePositionID = nil
            return false
        }
        if activePositionID == positionID { return true }

        if let instances, !instances.isEmpty {
            guard instances.count == instanceEntities.count else { return false }
            var selectedFraming: SuspendedCameraFraming?
            let cordGroup = Entity()
            for (index, instance) in instances.enumerated() {
                let transform: simd_float4x4
                if let suspension = instance.suspension {
                    guard let pose = suspension.canonicalPoses[positionID] else { return false }
                    do {
                        let base = Self.instanceMatrix(instance: instance, positionID: nil,
                                                       center: Self.boundsCenter(descriptor.modelBounds))
                        let solved = try SuspendedBoardPresentation.solveInstance(
                            pose: pose, suspension: suspension, bounds: descriptor.modelBounds,
                            transform: base)
                        transform = solved.boardTransform
                        selectedFraming = solved.cameraFraming
                        cordGroup.addChild(Self.makeCordEntity(for: solved))
                    } catch { return false }
                } else {
                    guard instance.positionTransforms == nil || instance.positionTransforms?[positionID] != nil else {
                        return false
                    }
                    transform = Self.instanceMatrix(instance: instance, positionID: positionID,
                                                    center: Self.boundsCenter(descriptor.modelBounds))
                }
                instanceEntities[index].transform = Transform(matrix: transform)
            }
            if let selectedFraming {
                currentFraming = selectedFraming
            } else {
                setupCameraFraming()
            }
            transientCordEntity?.removeFromParent()
            if !cordGroup.children.isEmpty {
                transientCordEntity = cordGroup
                root.addChild(cordGroup)
            } else {
                transientCordEntity = nil
            }
        } else if let suspension {
            guard let pose = suspension.canonicalPoses[positionID] else { return false }
            do {
                let solved = try Self.solveSuspension(
                    pose: pose, suspension: suspension, bounds: descriptor.modelBounds)
                instanceEntities.first?.transform = Transform(matrix: solved.boardTransform)
                currentFraming = solved.cameraFraming
                transientCordEntity?.removeFromParent()
                let cord = Self.makeCordEntity(for: solved)
                transientCordEntity = cord
                root.addChild(cord)
            } catch { return false }
        } else if let orientation {
            guard let components = orientation.rotations[positionID] else { return false }
            let rotation = simd_quatf(ix: Float(components.x), iy: Float(components.y),
                                      iz: Float(components.z), r: Float(components.w))
            let center = Self.boundsCenter(descriptor.modelBounds)
            instanceEntities.first?.transform = Transform(matrix: Self.transform(rotation: rotation, about: center))
            setupCameraFraming()
        }
        activePositionID = positionID
        updateCameraTransform()
        return true
    }

    func orbit(azimuth: Float, elevation: Float, zoomScale: Float = 1) {
        guard azimuth.isFinite, elevation.isFinite, zoomScale.isFinite, zoomScale > 0 else { return }
        orbitAzimuth = azimuth.truncatingRemainder(dividingBy: .pi * 2)
        orbitElevation = min(max(elevation, -0.55), 0.55)
        orbitZoom = min(max(zoomScale, 0.75), 1.35)
        updateCameraTransform()
    }

    func resetCamera(animated: Bool, completion: (() -> Void)? = nil) {
        orbitAzimuth = 0
        orbitElevation = 0
        orbitZoom = 1
        updateCameraTransform(animated: animated, completion: completion)
    }

    func highlight(_ contactIDs: Set<String>, mode: BoardHighlightMode) {
        guard contactIDs != lastHighlightedContactIDs || mode != lastHighlightMode else { return }
        lastHighlightedContactIDs = contactIDs
        lastHighlightMode = mode
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
        var candidate: Entity? = entity
        while let current = candidate {
            if let contactID = contactIDByEntity[current] { return contactID }
            candidate = current.parent
        }
        return nil
    }

    func projectedContactCenter(_ contactID: String, viewport: CGSize,
                                fieldOfViewDegrees: Double) -> CGPoint? {
        guard viewport.width > 0, viewport.height > 0, fieldOfViewDegrees > 0,
              let entities = contactEntities[contactID], !entities.isEmpty else { return nil }
        var centers: [SIMD3<Float>] = []
        for entity in entities {
            let bounds = entity.visualBounds(relativeTo: nil)
            guard bounds.min.x.isFinite, bounds.max.x.isFinite,
                  bounds.min.y.isFinite, bounds.max.y.isFinite,
                  bounds.min.z.isFinite, bounds.max.z.isFinite else { continue }
            centers.append((bounds.min + bounds.max) * 0.5)
        }
        guard !centers.isEmpty else { return nil }
        let center = centers.reduce(SIMD3<Float>.zero, +) / Float(centers.count)
        let view = simd_inverse(camera.transform.matrix) * SIMD4<Float>(center, 1)
        let depth = -view.z
        guard depth > 0.0001 else { return nil }
        let focal = Float(1 / tan(fieldOfViewDegrees * .pi / 360))
        let aspect = Float(viewport.width / viewport.height)
        let ndcX = focal / aspect * view.x / depth
        let ndcY = focal * view.y / depth
        return CGPoint(x: CGFloat(ndcX * 0.5 + 0.5) * viewport.width,
                       y: CGFloat(0.5 - ndcY * 0.5) * viewport.height)
    }

    func frame(in size: CGSize) {
        viewportSize = size
        updateCameraTransform()
    }

    func fittedOrthographicScale(in size: CGSize) -> Double? {
        guard let framing = currentFraming else { return nil }
        guard size.width > 0, size.height > 0 else { return nil }
        let aspect = Float(size.width / size.height)
        return Double(max(framing.height, framing.width / aspect) * framing.fitPadding / orbitZoom / 2)
    }

    private func buildContactEntities() {
        // For schema v2 (reusable model), descriptor.contacts is keyed by physical contact ID.
        // Each instance has contactIDsBySlotID mapping slotID -> physicalContactID.
        // We need to build nodeID -> slotID mapping per instance.
        
        // Build a mapping from physicalContactID -> contactDescriptor for quick lookup
        let contactDescriptorByPhysicalID = descriptor.contacts

        // Traverse all instance entities and build contact entity mapping
        for (instanceIndex, instanceEntity) in instanceEntities.enumerated() {
            // Build nodeID -> slotID mapping for this instance
            var nodeIDToSlotID: [String: String] = [:]
            
            if let instances = instances, instanceIndex < instances.count {
                let instance = instances[instanceIndex]
                // Invert contactIDsBySlotID to get physicalContactID -> slotID
                var physicalIDToSlotID: [String: String] = [:]
                for (slotID, physicalContactID) in instance.contactIDsBySlotID {
                    physicalIDToSlotID[physicalContactID] = slotID
                }
                
                // For each physicalContactID in this instance, get the contact descriptor and its nodeIDs
                for (physicalContactID, slotID) in physicalIDToSlotID {
                    if let contactDescriptor = contactDescriptorByPhysicalID[physicalContactID] {
                        for nodeID in contactDescriptor.nodeIDs {
                            nodeIDToSlotID[nodeID] = slotID
                        }
                    }
                }
                
                // Now traverse and map using slotID -> physicalContactID
                let slotIDToContactID = instance.contactIDsBySlotID
                
                traverseEntities(instanceEntity) { entity in
                    if let modelEntity = entity as? ModelEntity,
                       let slotID = findSlotID(for: entity, nodeIDToSlotID: nodeIDToSlotID),
                       let contactID = slotIDToContactID[slotID] {
                        contactEntities[contactID, default: []].append(modelEntity)
                        contactIDByEntity[modelEntity] = contactID
                        modelEntity.generateCollisionShapes(recursive: false)
                        // Neutral highlight baseline captured before this method runs.
                    }
                }
            } else {
                // Single instance (schema v1): descriptor.contacts is keyed by physical contact ID == slotID
                for (physicalContactID, contactDescriptor) in contactDescriptorByPhysicalID {
                    for nodeID in contactDescriptor.nodeIDs {
                        nodeIDToSlotID[nodeID] = physicalContactID
                    }
                }
                
                let slotIDToContactID = Dictionary(uniqueKeysWithValues: nodeIDToSlotID.map { ($0.value, $0.value) })
                
                traverseEntities(instanceEntity) { entity in
                    if let modelEntity = entity as? ModelEntity,
                       let slotID = findSlotID(for: entity, nodeIDToSlotID: nodeIDToSlotID),
                       let contactID = slotIDToContactID[slotID] {
                        contactEntities[contactID, default: []].append(modelEntity)
                        contactIDByEntity[modelEntity] = contactID
                        modelEntity.generateCollisionShapes(recursive: false)
                        // Neutral highlight baseline captured before this method runs.
                    }
                }
            }
        }
    }
    
    private func findSlotID(for entity: Entity, nodeIDToSlotID: [String: String]) -> String? {
        // Primary: direct entity name match (USDZ import uses node names)
        if let slotID = nodeIDToSlotID[entity.name] {
            return slotID
        }
        // Fallback: check parent hierarchy for matching names
        var current: Entity? = entity
        while let parent = current?.parent {
            if let slotID = nodeIDToSlotID[parent.name] {
                return slotID
            }
            current = parent
        }
        // Fallback: try matching by sanitized name (USDZ import may add prefixes/suffixes)
        let sanitizedName = entity.name
            .replacingOccurrences(of: "^[^_]+_", with: "", options: .regularExpression) // Remove prefix before first underscore
            .replacingOccurrences(of: "_[^_]+$", with: "", options: .regularExpression) // Remove suffix after last underscore
        if sanitizedName != entity.name,
           let slotID = nodeIDToSlotID[sanitizedName] {
            return slotID
        }
        // Log unmatched entity for debugging
        if !nodeIDToSlotID.isEmpty {
            print("[BoardModelRealityScene] Warning: No slotID match for entity '\(entity.name)' (sanitized: '\(sanitizedName)'). Available nodeIDs: \(Array(nodeIDToSlotID.keys).prefix(10))")
        }
        return nil
    }
    
    private func traverseEntities(_ entity: Entity, _ visit: (Entity) -> Void) {
        visit(entity)
        for child in entity.children {
            traverseEntities(child, visit)
        }
    }

    private func applyHighlight(to entity: ModelEntity, color: Color, mode: BoardHighlightMode) {
        guard var material = entity.model?.materials.first as? PhysicallyBasedMaterial else { return }

        if color == .clear {
            // Restore the neutral PBR baseline.
            if let baselineMaterial = baselineMaterials[entity] {
                entity.model?.materials = [baselineMaterial]
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
        let framing = currentFraming
        let distance = (framing?.distance ?? 1) * orbitZoom
        let target = framing?.target ?? SIMD3<Float>(0, 0, 0)
        let up = framing?.up ?? SIMD3<Float>(0, 1, 0)
        let direction = simd_normalize(-(framing?.direction ?? SIMD3<Float>(0, 0, -1)))
        let right = framing?.right ?? SIMD3<Float>(1, 0, 0)
        let yaw = simd_quatf(angle: orbitAzimuth, axis: up)
        let yawedDirection = yaw.act(direction)
        let yawedRight = simd_normalize(yaw.act(right))
        let pitch = simd_quatf(angle: -orbitElevation, axis: yawedRight)
        camera.position = target + pitch.act(yawedDirection) * distance
        camera.look(at: target, from: camera.position, relativeTo: nil)

        if animated {
            // Animate camera transition
        }
        completion?()
    }

    private static func boundsCenter(_ bounds: BoardModelBounds) -> SIMD3<Float> {
        guard bounds.minimum.count == 3, bounds.maximum.count == 3 else { return .zero }
        return SIMD3<Float>(
            Float((bounds.minimum[0] + bounds.maximum[0]) / 2),
            Float((bounds.minimum[1] + bounds.maximum[1]) / 2),
            Float((bounds.minimum[2] + bounds.maximum[2]) / 2))
    }

    private static func instanceMatrix(instance: BoardModelInstance, positionID: String?,
                                       center: SIMD3<Float>) -> simd_float4x4 {
        func transformMatrix(_ transform: BoardModelTransform?, pivot: SIMD3<Float>) -> simd_float4x4 {
            guard let transform else { return matrix_identity_float4x4 }
            let rotation = simd_quatf(ix: Float(transform.rotation.x), iy: Float(transform.rotation.y),
                                      iz: Float(transform.rotation.z), r: Float(transform.rotation.w))
            let toPivot = translationMatrix(pivot)
            let fromPivot = translationMatrix(-pivot)
            var result = toPivot * simd_float4x4(rotation) * fromPivot
            if transform.translation.count == 3 {
                result.columns.3 += SIMD4<Float>(Float(transform.translation[0]),
                                                  Float(transform.translation[1]),
                                                  Float(transform.translation[2]), 0)
            }
            if transform.reflection == .x {
                var reflection = matrix_identity_float4x4
                reflection.columns.0.x = -1
                reflection.columns.3.x = 2 * center.x
                result = result * reflection
            }
            return result
        }
        let base = transformMatrix(instance.baseTransform, pivot: center)
        let position = positionID.flatMap { instance.positionTransforms?[$0] }
        let baseTranslation = instance.baseTransform.translation.count == 3
            ? SIMD3<Float>(instance.baseTransform.translation.map(Float.init)) : .zero
        return transformMatrix(position, pivot: center + baseTranslation) * base
    }

    private static func translationMatrix(_ value: SIMD3<Float>) -> simd_float4x4 {
        var result = matrix_identity_float4x4
        result.columns.3 = SIMD4<Float>(value, 1)
        return result
    }

    private static func transform(rotation: simd_quatf, about pivot: SIMD3<Float>) -> simd_float4x4 {
        translationMatrix(pivot) * simd_float4x4(rotation) * translationMatrix(-pivot)
    }

    private static func makeCordEntity(for solved: BoardModelSolvedSuspension) -> Entity {
        let root = Entity()
        var paths: [[SIMD3<Float>]] = []
        let radius: Float
        switch solved {
        case .single(let value):
            paths = [value.cord.samples]
            radius = value.tubeRadius
        case .pairedLead(let value):
            paths = value.leads.map(\.samples)
            radius = value.tubeRadius
        case .twoBranch(let value):
            paths = value.branches.flatMap { $0.spans }
            radius = value.tubeRadius
        }
        var material = PhysicallyBasedMaterial()
        material.baseColor = .init(tint: UIColor(white: 0.12, alpha: 1))
        material.roughness = .init(floatLiteral: 0.85)
        material.metallic = .init(floatLiteral: 0)
        for path in paths {
            for (start, end) in zip(path, path.dropFirst()) {
                let delta = end - start
                let length = simd_length(delta)
                guard length.isFinite, length > 1e-6 else { continue }
                let segment = ModelEntity(mesh: .generateCylinder(height: length, radius: radius),
                                          materials: [material])
                segment.position = (start + end) * 0.5
                segment.orientation = simd_quatf(from: SIMD3<Float>(0, 1, 0), to: delta / length)
                root.addChild(segment)
            }
        }
        return root
    }

    static func solveSuspension(pose: BoardModelCanonicalPose,
                                suspension: BoardModelSuspension,
                                bounds: BoardModelBounds) throws -> BoardModelSolvedSuspension {
        switch suspension {
        case .singleCord(let profile):
            return .single(try SuspendedBoardPresentation.solve(
                pose: pose, suspension: .singleCord(profile), bounds: bounds))
        case .pairedLeadCord(let profile):
            return .pairedLead(try SuspendedBoardPresentation.solve(
                pose: pose, suspension: profile, bounds: bounds))
        case .twoBranchCord(let profile):
            return .twoBranch(try SuspendedBoardPresentation.solve(
                pose: pose, suspension: profile, bounds: bounds))
        }
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
/// This class is @unchecked Sendable because all mutations happen on the MainActor
/// via the @MainActor release() method. The deinit fallback is best-effort.
final class BoardModelRealityResourceLease: @unchecked Sendable {
    let url: URL
    nonisolated(unsafe) private var lease: BoardModelResourceLease?
    nonisolated(unsafe) private var isReleased = false

    init(url: URL, lease: BoardModelResourceLease? = nil) {
        self.url = url
        self.lease = lease
    }

    /// Explicitly release the underlying resource lease.
    /// Must be called on the main actor to ensure thread-safe resource cleanup.
    @MainActor
    func release() {
        guard !isReleased else { return }
        isReleased = true
        lease = nil // BoardModelResourceLease's deinit will call endAccessingResources
    }

    deinit {
        // Fallback: if release() wasn't called explicitly, clean up.
        // Note: deinit runs on arbitrary thread; BoardModelResourceLease's deinit
        // calls endAccessingResources() which may not be thread-safe.
        // Prefer calling release() explicitly on MainActor.
        if !isReleased {
            lease = nil // This triggers BoardModelResourceLease.deinit which calls endAccessingResources()
        }
    }
}

/// Cache for loaded RealityKit model sources.
@MainActor
enum BoardModelRealityCache {
    private final class InFlight {
        var task: Task<BoardModelRealityLoadedSource?, Error>?
        var waiters: [UUID: CheckedContinuation<BoardModelRealityLoadedSource?, Error>] = [:]
    }

    private static var loading: [BoardModelRealityKey: InFlight] = [:]

    // Long-term cache for loaded sources with memory pressure eviction.
    // Cost is based on file size to prioritize keeping smaller models.
    private static let sourceCache: NSCache<NSString, BoardModelRealityLoadedSource> = {
        let cache = NSCache<NSString, BoardModelRealityLoadedSource>()
        cache.countLimit = 10 // Maximum number of cached models
        cache.totalCostLimit = 100 * 1024 * 1024 // 100 MB total cost limit
        return cache
    }()

    // Observer token for memory pressure notifications
    private static var memoryPressureObserver: NSObjectProtocol?

    static func source(
        for key: BoardModelRealityKey,
        media: BoardModelMedia,
        board: BoardRevision,
        presentationID: String,
        store: BoardPackageStore,
        resourceAccess: BoardModelResourceAccess
    ) async throws -> BoardModelRealityLoadedSource? {
        let cacheKey = cacheKeyString(for: key)

        // Check long-term cache first
        if let cachedSource = sourceCache.object(forKey: cacheKey as NSString) {
            return cachedSource
        }

        let waiterID = UUID()
        return try await withTaskCancellationHandler {
            try await withCheckedThrowingContinuation { (continuation: CheckedContinuation<BoardModelRealityLoadedSource?, Error>) in
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
                    // Cache the result for future loads (if successful)
                    if let result = result {
                        let cost = fileSizeCost(for: result.resourceLease.url)
                        sourceCache.setObject(result, forKey: cacheKey as NSString, cost: cost)
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

    private static func cacheKeyString(for key: BoardModelRealityKey) -> String {
        "\(key.boardID)/\(key.presentationID)/\(key.modelSHA256)"
    }

    private static func fileSizeCost(for url: URL) -> Int {
        do {
            let attrs = try FileManager.default.attributesOfItem(atPath: url.path)
            if let fileSize = attrs[.size] as? NSNumber {
                return fileSize.intValue
            }
        } catch {
            // Ignore errors, return default cost
        }
        return 10 * 1024 * 1024 // Default 10 MB cost
    }

    /// Clear the cache in response to memory pressure.
    static func clearCache() {
        sourceCache.removeAllObjects()
    }

    /// Configure automatic memory pressure handling.
    /// Call once at app launch (e.g., from AppDelegate or SceneDelegate).
    static func configureMemoryPressureHandling() {
        #if os(iOS) || os(tvOS)
        guard memoryPressureObserver == nil else { return }
        memoryPressureObserver = NotificationCenter.default.addObserver(
            forName: UIApplication.didReceiveMemoryWarningNotification,
            object: nil,
            queue: .main
        ) { _ in
            Task { @MainActor in
                clearCache()
            }
        }
        #elseif os(macOS)
        // macOS doesn't have a direct equivalent, but we can observe
        // NSWorkspace memory pressure notifications if needed
        #endif
    }

    /// Remove the memory pressure observer.
    /// Call when the app is terminating or when memory pressure handling is no longer needed.
    static func deconfigureMemoryPressureHandling() {
        #if os(iOS) || os(tvOS)
        if let observer = memoryPressureObserver {
            NotificationCenter.default.removeObserver(observer)
            memoryPressureObserver = nil
        }
        #endif
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
        let computedSHA256 = try sha256(of: resourceLease.url)
        guard computedSHA256 == media.descriptor.modelSHA256 else {
            throw BoardModelRealityError.sha256Mismatch(expected: media.descriptor.modelSHA256, actual: computedSHA256)
        }

        return BoardModelRealityLoadedSource(resourceLease: resourceLease)
    }

    private static func sha256(of url: URL) throws -> String {
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
        } catch let error as BoardModelRealityError {
            throw error
        } catch {
            throw BoardModelRealityError.fileReadError(underlying: error.localizedDescription)
        }
    }
}

/// Loaded model source with resource lease.
/// This class is @unchecked Sendable because it's only accessed on the MainActor
/// through the BoardModelRealityCache which is @MainActor-isolated.
final class BoardModelRealityLoadedSource: @unchecked Sendable {
    let resourceLease: BoardModelRealityResourceLease
    
    init(resourceLease: BoardModelRealityResourceLease) {
        self.resourceLease = resourceLease
    }
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
        let acquired = await withTaskCancellationHandler {
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
        if acquired, Task.isCancelled {
            release()
            return false
        }
        return acquired
    }

    static func release() {
        precondition(active > 0, "RealityKit load gate released without an active load")
        if waiters.isEmpty {
            active -= 1
        } else {
            // Hand the slot to the earliest waiter; active stays at limit.
            // Do NOT decrement active here - the waiter now holds the slot.
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
            throw BoardModelRealityError.presentationNotModel
        }

        guard await BoardModelRealityLoadGate.acquire() else {
            throw BoardModelRealityError.loadGateCancelled
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
            if Task.isCancelled { throw CancellationError() }
            throw BoardModelRealityError.resourceUnavailable
        }

        let scene = BoardModelRealityScene(
            descriptor: media.descriptor,
            display: media.display,
            suspension: media.suspension,
            orientation: media.orientation,
            allowedPositionIDs: Set(board.positions.filter {
                $0.presentationID == presentation.id
            }.map(\.id)),
            instances: media.instances,
            resourceLease: source.resourceLease
        )

        // Load the USDZ model via ModelIO
        try await scene.load(usdzURL: source.resourceLease.url)

        // The resource lease is now owned by the scene and will be released
        // when the scene is deallocated (after async texture streaming completes).
        // Do NOT release it here.

        return scene
    }
}
