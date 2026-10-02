import Foundation
import RealityKit
import Metal
import SwiftUI
import UIKit
import simd
import CryptoKit

protocol BoardModelResourceRequesting: AnyObject {
    var progress: Progress { get }
    func beginAccessingResources() async throws
    func endAccessingResources()
}

extension NSBundleResourceRequest: BoardModelResourceRequesting {}

final class BoardModelResourceLease {
    let url: URL
    nonisolated(unsafe) private var request: BoardModelResourceRequesting?

    init(url: URL, request: BoardModelResourceRequesting? = nil) {
        self.url = url
        self.request = request
    }

    deinit {
        // Note: deinit runs on arbitrary thread; endAccessingResources() may not be thread-safe.
        // The BoardModelResourceRequestAccess.lease() method transfers ownership to the lease
        // and clears the request under a lock, so this deinit is a fallback for cancelled paths.
        request?.endAccessingResources()
    }
}

private final class BoardModelResourceRequestAccess: @unchecked Sendable {
    private let lock = NSLock()
    nonisolated(unsafe) private var request: BoardModelResourceRequesting?
    nonisolated(unsafe) private var isCancelled = false

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
    private var baselineMaterials: [Entity: any RealityKit.Material] = [:]
    private let finishByNodeID: [String: BoardSurfaceFinish]

    // Suspension/camera state
    private var suspension: BoardModelSuspension?
    private var verifiedPresentations: [String: (BoardModelSolvedSuspension, ModelEntity)] = [:]
    private var meshWrapSection: [SIMD2<Float>]?
    private var canonicalFraming: SuspendedCameraFraming?
    private var currentFraming: SuspendedCameraFraming?
    private var activePositionID: String?

    private let liveSceneID = UUID()
    private var liveGeneration: UInt64 = 0
    private var liveControllers: [LiveRopeController] = []
    private var liveMeshes: [[LiveRopeMesh]] = []
    private var liveFrames: [RopeFrameSnapshot] = []
    private var liveBaseTransforms: [simd_float4x4] = []
    private var liveSubscription: EventSubscription?
    private var liveFailure: Error?
    private var liveActivity = true
    #if DEBUG
    private var reviewCameraApplied = false
    private var reviewRotations: [Double] = ProcessInfo.processInfo.environment["HANGTEN_REVIEW_ROPE_ROTATION_SEQUENCE"]?
        .split(separator:",").compactMap { Double($0) }.filter(\.isFinite) ?? []
    #endif
    var onLiveFailure: (() -> Void)?
    var onLiveFrame: (() -> Void)?
    var hasLiveRopes: Bool { !liveControllers.isEmpty }
    var liveFramesForTesting: [RopeFrameSnapshot] { liveFrames }

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
    private let physics: RopePhysicsInput?
    private let presentationID: String?

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

    init(descriptor: BoardModelDescriptor, display: BoardModelDisplay, suspension: BoardModelSuspension?, orientation: BoardModelOrientation?, allowedPositionIDs: Set<String>, instances: [BoardModelInstance]? = nil, physics: RopePhysicsInput? = nil, presentationID: String? = nil, resourceLease: BoardModelRealityResourceLease) {
        self.descriptor = descriptor
        self.display = display
        self.suspension = suspension
        self.orientation = orientation
        self.allowedPositionIDs = allowedPositionIDs
        self.instances = instances
        self.physics = physics
        self.presentationID = presentationID
        self.resourceLease = resourceLease
        let woodNodes = Set(display.woodNodeIDs)
        let plasticNodes = Set(display.plasticNodeIDs)
        let graniteNodes = Set(display.graniteNodeIDs)
        self.finishByNodeID = Dictionary(uniqueKeysWithValues: descriptor.nodes.map {
            ($0.nodeID, $0.role == .attachment ? .neutral
                : woodNodes.contains($0.nodeID) ? .wood
                : plasticNodes.contains($0.nodeID) ? .plastic
                : graniteNodes.contains($0.nodeID) ? .granite : display.surfaceFinish)
        })
    }

/// Loads the USDZ model directly into RealityKit and binds descriptor nodes.
    func load(usdzURL: URL) async throws {
        // RealityKit imports the USDZ asynchronously and reports malformed assets.
        let modelEntity = try await Entity(contentsOf: usdzURL)

        self.modelEntity = modelEntity

        // Build instance entities from media instances
        if let instances = instances, !instances.isEmpty {
            try buildInstanceEntities(from: modelEntity, instances: instances)
        } else {
            // Single instance (legacy behavior)
            root.addChild(modelEntity)
            instanceEntities = [modelEntity]
        }

        // Appearance is runtime-only; the bundled USDZ stays unbound. Capture
        // each finish before highlighting so deselection restores the authored finish.
        applyBoardMaterials(to: root, inheritedFinish: display.surfaceFinish)

        // Build contact entity mapping from descriptor
        // Highlight baselines were captured by applyBoardMaterials().
        try buildContactEntities()

        // Set up camera framing based on model bounds
        setupCameraFraming()
        try await prepareLiveRopes()
    }

    private func buildInstanceEntities(from sourceEntity: Entity, instances: [BoardModelInstance]) throws {
        instanceEntities = []
        let center = Self.boundsCenter(descriptor.modelBounds)

        for instance in instances {
            // Clone the source entity hierarchy for this instance
            let instanceEntity = sourceEntity.clone(recursive: true)
            if instance.baseTransform.reflection == .x {
                try Self.reflectMeshes(in: instanceEntity, center: center)
            }
            instanceEntity.transform = renderTransform(Self.instanceMatrix(
                instance: instance, positionID: nil, center: center), instance: instance)

            root.addChild(instanceEntity)
            instanceEntities.append(instanceEntity)
        }
    }

    /// Bake the reflection into independent mesh resources. A negative entity
    /// scale reverses front-face winding, so double-sided shading lights the
    /// reflected front with inward normals. Reflect normals and reverse the
    /// triangles together, keeping imported node names and contact bindings.
    private static func reflectMeshes(in root: Entity, center: SIMD3<Float>) throws {
        let reflection = reflectionMatrix(center: center)
        func visit(_ entity: Entity) throws {
            if let entity = entity as? ModelEntity, var component = entity.model {
                let localToBoard = entity.transformMatrix(relativeTo: root)
                let localReflection = simd_inverse(localToBoard) * reflection * localToBoard
                component.mesh = try reflectedMesh(component.mesh, reflection: localReflection)
                entity.model = component
            }
            for child in entity.children { try visit(child) }
        }
        try visit(root)
    }

    static func reflectedMesh(_ mesh: MeshResource, reflection: simd_float4x4) throws -> MeshResource {
        var contents = mesh.contents
        let originReflection = reflectionMatrix(center: .zero)
        func reflect(_ value: SIMD3<Float>) -> SIMD3<Float> { SIMD3(-value.x, value.y, value.z) }
        for var model in contents.models {
            for var part in model.parts {
                guard var indices = part.triangleIndices?.elements, indices.count.isMultiple(of: 3) else {
                    throw BoardModelRealityError.geometryProcessingFailed(reason: "Reflected board mesh must contain triangles")
                }
                part.positions = .init(part.positions.map(reflect))
                if let normals = part.normals { part.normals = .init(normals.map(reflect)) }
                if let tangents = part.tangents { part.tangents = .init(tangents.map(reflect)) }
                if let bitangents = part.bitangents { part.bitangents = .init(bitangents.map(reflect)) }
                for offset in stride(from: 0, to: indices.count, by: 3) {
                    indices.swapAt(offset + 1, offset + 2)
                }
                part.triangleIndices = .init(indices)
                model.parts.update(part)
            }
            contents.models.update(model)
        }
        for var instance in contents.instances {
            // Conjugate imported mesh-instance transforms so translating or
            // rotating a mesh within its named node preserves board-space reflection.
            instance.transform = reflection * instance.transform * originReflection
            contents.instances.update(instance)
        }
        return try MeshResource.generate(from: contents)
    }

    private func renderTransform(_ matrix: simd_float4x4, instance: BoardModelInstance) -> Transform {
        guard instance.baseTransform.reflection == .x else { return Transform(matrix: matrix) }
        // The mesh already owns this reflection. Cancel it from the authored
        // presentation matrix on load, pose changes, and clearing selection.
        return Transform(matrix: matrix * Self.reflectionMatrix(center: Self.boundsCenter(descriptor.modelBounds)))
    }

    private func applyBoardMaterials(to entity: Entity, inheritedFinish: BoardSurfaceFinish) {
        // CAD descriptor names identify the authored surfaces. Carry the finish
        // through any unnamed mesh children inserted by the USDZ importer.
        let finish = finishByNodeID[entity.name] ?? inheritedFinish
        if let modelEntity = entity as? ModelEntity, modelEntity.model != nil {
            let material: any RealityKit.Material
            switch finish {
            case .wood: material = Self.woodMaterial
            case .plastic: material = Self.plasticMaterial
            case .granite: material = Self.graniteMaterial
            case .neutral: material = Self.neutralMaterial()
            }
            modelEntity.model?.materials = [material]
            baselineMaterials[modelEntity] = material
        }
        for child in entity.children {
            applyBoardMaterials(to: child, inheritedFinish: finish)
        }
    }

    private static let woodMaterial: any RealityKit.Material = {
        var base = PhysicallyBasedMaterial()
        base.baseColor = .init(tint: UIColor(red: 0.78, green: 0.66, blue: 0.49, alpha: 1))
        base.roughness = .init(floatLiteral: 0.82)
        base.metallic = .init(floatLiteral: 0)
        base.faceCulling = .none
        guard let device = MTLCreateSystemDefaultDevice(),
              let library = device.makeDefaultLibrary() else { return base }
        do {
            let shader = CustomMaterial.SurfaceShader(named: "boardWoodSurfaceShader", in: library)
            return try CustomMaterial(from: base, surfaceShader: shader)
        } catch {
            #if DEBUG
            print("[BoardModelRealityScene] Wood shader unavailable: \(error)")
            #endif
            // A warm matte fallback still identifies wood on unsupported devices.
            return base
        }
    }()

    private static let graniteMaterial: any RealityKit.Material = {
        var base = PhysicallyBasedMaterial()
        base.baseColor = .init(tint: UIColor(red: 0.25, green: 0.26, blue: 0.27, alpha: 1))
        base.roughness = .init(floatLiteral: 0.92)
        base.metallic = .init(floatLiteral: 0)
        base.faceCulling = .none
        guard let device = MTLCreateSystemDefaultDevice(),
              let library = device.makeDefaultLibrary() else { return base }
        do {
            let shader = CustomMaterial.SurfaceShader(named: "boardGraniteSurfaceShader", in: library)
            return try CustomMaterial(from: base, surfaceShader: shader)
        } catch {
            #if DEBUG
            print("[BoardModelRealityScene] Granite shader unavailable: \(error)")
            #endif
            return base
        }
    }()

    private static let plasticMaterial: any RealityKit.Material = {
        var base = PhysicallyBasedMaterial()
        // Seafoam mint is the app's display palette, not a product color fact.
        base.baseColor = .init(tint: UIColor(red: 123.0 / 255, green: 203.0 / 255,
                                            blue: 178.0 / 255, alpha: 1))
        base.roughness = .init(floatLiteral: 0.78)
        base.metallic = .init(floatLiteral: 0)
        // Like the neutral finish, retain front surfaces when an instance's
        // reflection reverses winding. CustomMaterial inherits this setting.
        base.faceCulling = .none
        guard let device = MTLCreateSystemDefaultDevice(),
              let library = device.makeDefaultLibrary() else { return base }
        do {
            let shader = CustomMaterial.SurfaceShader(named: "boardPlasticSurfaceShader", in: library)
            return try CustomMaterial(from: base, surfaceShader: shader)
        } catch {
            #if DEBUG
            print("[BoardModelRealityScene] Plastic shader unavailable: \(error)")
            #endif
            return base
        }
    }()

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
        // `perspectiveFitDistance` applies fitPadding after considering the
        // viewport FOV. Keep the fallback distance unpadded to avoid applying
        // the package margin twice when the viewport is already available.
        let defaultDistanceMultiplier = 1.0
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
        if canonicalFraming == nil {
            canonicalFraming = currentFraming
        }

        // Position camera
        updateCameraTransform()
    }

    static func neutralMaterial() -> PhysicallyBasedMaterial {
        var material = PhysicallyBasedMaterial()
        material.baseColor = .init(tint: UIColor(red: 0.82, green: 0.80, blue: 0.77, alpha: 1))
        material.roughness = .init(floatLiteral: 0.5)
        material.metallic = .init(floatLiteral: 0)
        // A reflected instance reverses triangle winding. Some CAD contacts
        // are open front surfaces, so culling would hide the mirrored half.
        material.faceCulling = .none
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
        #if DEBUG
        if activePositionID != positionID {
            LiveRopeReviewTrace.log("scene select position=\(String(describing:positionID)) previous=\(String(describing:activePositionID)) live=\(hasLiveRopes) active=\(liveActivity)")
        }
        #endif
        guard let positionID else {
            clearSelection()
            return false
        }
        guard allowedPositionIDs.contains(positionID) else {
            return false
        }
        if liveFailure != nil { return false }
        if activePositionID == positionID { return true }
        if hasLiveRopes {
            var targets:[simd_quatd]=[]
            for index in liveControllers.indices {
                let setup=instances.flatMap{$0.indices.contains(index) ? $0[index].suspension:nil} ?? suspension
                guard let pose=setup?.canonicalPoses[positionID],pose.rotation.count == 4 else {return false}
                let q=simd_quatd(ix:pose.rotation[0],iy:pose.rotation[1],iz:pose.rotation[2],r:pose.rotation[3])
                guard q.vector.x.isFinite,q.vector.y.isFinite,q.vector.z.isFinite,q.vector.w.isFinite,
                      abs(simd_length(q.vector)-1)<1e-6 else {return false}
                targets.append(simd_normalize(q))
            }
            liveGeneration &+= 1
            for (controller,target) in zip(liveControllers,targets) {
                controller.setTarget(orientation:target,generation:liveGeneration)
                if liveActivity { controller.resume() } else { controller.pause() }
            }
            if transientCordEntity == nil {
                do {
                    for index in liveFrames.indices { try applyLiveFrame(liveFrames[index],instance:index) }
                    attachLiveCordGroup()
                } catch { failLiveRopes(error); return false }
            }
            activePositionID = positionID
            #if DEBUG
            if let degrees = ProcessInfo.processInfo.environment["HANGTEN_REVIEW_ROPE_ROTATION_DEGREES"].flatMap(Double.init), degrees.isFinite {
                setLivePhysicalOrientation(simd_quatd(angle:degrees*Double.pi/180,axis:SIMD3(0,0,1)))
            }
            #endif
            return true
        }

        if let instances, !instances.isEmpty {
            guard instances.count == instanceEntities.count else { return false }
            var selectedFramings: [SuspendedCameraFraming] = []
            var selectedTransforms: [simd_float4x4] = []
            var framingPose: BoardModelCanonicalPose?
            var framingTransform: simd_float4x4?
            let cordGroup = Entity()
            for instance in instances {
                let transform: simd_float4x4
                if let suspension = instance.suspension {
                    guard let pose = suspension.canonicalPoses[positionID] else { return false }
                    do {
                        let base = Self.instanceMatrix(instance: instance, positionID: nil,
                                                       center: Self.boundsCenter(descriptor.modelBounds))
                        let instanceTransform: simd_float4x4
                        if case .twoBranchCord = suspension {
                            // This adapter composes base * pose itself and places
                            // connected-channel anchors using the base alone.
                            instanceTransform = base
                        } else {
                            instanceTransform = try SuspendedBoardPresentation.boardTransform(for: pose) * base
                        }
                        let solved = try SuspendedBoardPresentation.solveInstance(
                            pose: pose, suspension: suspension, bounds: descriptor.modelBounds,
                            transform: instanceTransform)
                        transform = solved.boardTransform
                        if framingPose == nil {
                            framingPose = pose
                            framingTransform = transform
                        }
                        selectedFramings.append(solved.cameraFraming)
                        cordGroup.addChild(Self.makeCordEntity(for: solved))
                    } catch { return false }
                } else {
                    guard instance.positionTransforms == nil || instance.positionTransforms?[positionID] != nil else {
                        return false
                    }
                    transform = Self.instanceMatrix(instance: instance, positionID: positionID,
                                                    center: Self.boundsCenter(descriptor.modelBounds))
                }
                selectedTransforms.append(transform)
            }
            var combinedFraming: SuspendedCameraFraming?
            if !selectedFramings.isEmpty {
                let allBounds = selectedTransforms.flatMap { transform in
                    Self.boundsCorners(descriptor.modelBounds).map { point in
                        let placed = transform * SIMD4<Float>(point, 1)
                        return SIMD3<Float>(placed.x, placed.y, placed.z)
                    }
                }
                guard let pose = framingPose, let transform = framingTransform,
                      let framing = try? SuspendedBoardPresentation.makeCameraFraming(
                        pose: pose, transform: transform,
                        minimumFitPadding: selectedFramings.map(\.fitPadding).max() ?? 1,
                        points: selectedFramings.flatMap(\.includedPoints) + allBounds) else { return false }
                combinedFraming = framing
            }
            for (index, transform) in selectedTransforms.enumerated() {
                instanceEntities[index].transform = renderTransform(transform, instance: instances[index])
            }
            if let combinedFraming { currentFraming = combinedFraming }
            else { setupCameraFraming() }
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
                var resolvedPose = pose
                if case .twoBranchCord(let profile) = suspension,
                   let clearance = profile.meshWrapClearance {
                    guard profile.branches.count == 2,
                          profile.passages.left.count == 2,
                          profile.passages.right.count == 2,
                          let radius = profile.branches.map({ Float($0.radius) }).max() else {
                        return false
                    }
                    let passages = [profile.passages.left, profile.passages.right]
                    let loops = zip(profile.branches, passages).map { branch, side in
                        (id: branch.id,
                         outerX: Float(side[0].pointInModel[0]),
                         innerX: Float(side[1].pointInModel[0]))
                    }
                    resolvedPose.wrappedRoutes = try MeshSectionWrapSolver.routes(
                        section: try wrapSection(),
                        anchor: SIMD3<Float>(profile.anchor.position.map(Float.init)),
                        pose: pose,
                        radius: radius,
                        clearance: Float(clearance),
                        loops: loops)
                }
                if case .twoBranchCord(let profile) = suspension,
                   profile.internalLoopClearance != nil,
                   pose.cordContactPoints == nil {
                    guard profile.branches.count == 2,
                          profile.passages.left.count == 2,
                          profile.passages.right.count == 2 else {
                        return false
                    }
                    let settled = try MeshInternalLoopSolver.settledPose(
                        section: try wrapSection(),
                        anchor: SIMD3<Float>(profile.anchor.position.map(Float.init)),
                        pose: pose, profile: profile)
                    resolvedPose = settled.pose
                    var routes = settled.routes
                    // The second mouth of each hidden U is traversed outward.
                    for passage in [profile.passages.left[1], profile.passages.right[1]] {
                        routes[passage.id]?.reverse()
                    }
                    resolvedPose.cordContactPoints = routes
                }
                let solved = try Self.solveSuspension(
                    pose: resolvedPose, suspension: suspension, bounds: descriptor.modelBounds)
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

    /// Read the rigid body surface from the same imported USDZ that RealityKit
    /// renders. The section is cached before the first canonical pose rotates
    /// the board; only transient cord entities depend on it.
    private func wrapSection() throws -> [SIMD2<Float>] {
        if let meshWrapSection { return meshWrapSection }
        guard let instance = instanceEntities.first else {
            throw BoardModelRealityError.invalidSuspension
        }
        let bodyIDs = Set(descriptor.nodes.filter { $0.role == .body }.map(\.nodeID))
        var section: [SIMD2<Float>] = []
        traverseEntities(instance) { entity in
            guard bodyIDs.contains(entity.name),
                  let model = (entity as? ModelEntity)?.model else { return }
            let transform = entity.transformMatrix(relativeTo: root)
            for meshModel in model.mesh.contents.models {
                for part in meshModel.parts {
                    for vertex in part.positions {
                        let point = transform * SIMD4<Float>(vertex, 1)
                        section.append(SIMD2<Float>(point.y, point.z))
                    }
                }
            }
        }
        guard section.count >= 3,
              section.allSatisfy({ $0.x.isFinite && $0.y.isFinite }) else {
            throw BoardModelRealityError.geometryProcessingFailed(reason: "missing wrap body section")
        }
        meshWrapSection = section
        return section
    }

    private func clearSelection() {
        installLiveUpdateSubscription(nil)
        liveGeneration &+= 1
        liveControllers.forEach { $0.pause() }
        activePositionID = nil
        transientCordEntity?.removeFromParent()
        transientCordEntity = nil
        if let instances, !instances.isEmpty, instances.count == instanceEntities.count {
            let center = Self.boundsCenter(descriptor.modelBounds)
            for (entity, instance) in zip(instanceEntities, instances) {
                entity.transform = renderTransform(Self.instanceMatrix(
                    instance: instance, positionID: nil, center: center), instance: instance)
            }
        } else {
            for entity in instanceEntities { entity.transform = .identity }
        }
        currentFraming = canonicalFraming
        updateCameraTransform()
    }

    private func prepareLiveRopes() async throws {
        guard let physics else { return }
        let candidates=physics.profiles.filter { presentationID == nil || $0.presentationID == presentationID }
        guard candidates.count == instanceEntities.count else { throw BoardModelRealityError.invalidSuspension }
        let profiles:[RopePhysicsProfile]
        if let instances,!instances.isEmpty {
            guard instances.count == instanceEntities.count,
                  Set(instances.map(\.equipmentObjectID)).count == instances.count else {throw BoardModelRealityError.invalidSuspension}
            profiles=try instances.map {instance in
                let matching=candidates.filter{$0.instanceID == instance.equipmentObjectID}
                guard matching.count == 1 else {throw BoardModelRealityError.invalidSuspension}
                return matching[0]
            }
            liveBaseTransforms=instances.map {Self.instanceMatrix(instance:$0,positionID:nil,
                center:Self.boundsCenter(descriptor.modelBounds))}
        } else {
            guard candidates.count == 1,candidates[0].instanceID == nil else {throw BoardModelRealityError.invalidSuspension}
            profiles=candidates;liveBaseTransforms=[matrix_identity_float4x4]
        }
        // Each independent solver uses vertical gravity in its local world.
        // A display placement must preserve that direction; tilted worlds need
        // a physics coordinate adapter before their profiles can be enabled.
        guard liveBaseTransforms.allSatisfy({base in
            let up=base*SIMD4<Float>(0,1,0,0)
            return simd_length(up-SIMD4<Float>(0,1,0,0))<1e-6
        }) else {throw BoardModelRealityError.invalidSuspension}
        for (index,profile) in profiles.enumerated() {
            let prepared = try await Task.detached(priority:.userInitiated) {
                let collider=try RopeTriangleCollider(input:physics)
                let q=simd_quatd(angle:0,axis:SIMD3<Double>(0,0,1))
                let state=try RopeThreadedSeed.make(input:physics,profileID:profile.id,orientation:q,collider:collider)
                return try RopeDynamicsSolver.prepareDisplay(input:physics,state:state,collider:collider)
            }.value
            try Task.checkCancellation()
            let meshes=try prepared.1.ropes.map { try LiveRopeMesh(capacity:$0.positions.count,radialSegments:8,radius:Float($0.radius)) }
            liveMeshes.append(meshes); liveFrames.append(prepared.1)
            let controller=LiveRopeController(solver:prepared.0,sceneID:liveSceneID,delivery:{ [weak self] sceneID,generation,frame in
                guard let self,sceneID == self.liveSceneID,generation == self.liveGeneration,self.activePositionID != nil else { return }
                do { try self.applyLiveFrame(frame,instance:index) }
                catch { self.failLiveRopes(error) }
            },failure:{ [weak self] error in self?.failLiveRopes(error) })
            controller.pause(); liveControllers.append(controller)
            try applyLiveFrame(prepared.1,instance:index)
        }
    }

    private func attachLiveCordGroup() {
        let group=Entity()
        for meshes in liveMeshes { for mesh in meshes { group.addChild(mesh.entity) } }
        transientCordEntity?.removeFromParent()
        transientCordEntity=group; root.addChild(group)
        updateLiveFraming()
    }

    private func applyLiveFrame(_ frame:RopeFrameSnapshot,instance:Int) throws {
        guard liveMeshes.indices.contains(instance),liveBaseTransforms.indices.contains(instance),
              frame.metrics.geometryAccepted,liveMeshes[instance].count == frame.ropes.count else { throw BoardModelRealityError.invalidSuspension }
        let base=liveBaseTransforms[instance]
        for (mesh,rope) in zip(liveMeshes[instance],frame.ropes) {
            guard abs(Double(mesh.radius)-rope.radius)<1e-8 else { throw BoardModelRealityError.invalidSuspension }
            try mesh.update(positions:rope.positions)
            mesh.entity.transform=Transform(matrix:base)
        }
        liveFrames[instance]=frame
        let q=frame.orientation.vector
        let physical=Transform(scale:SIMD3(repeating:1),
            rotation:simd_quatf(ix:Float(q.x),iy:Float(q.y),iz:Float(q.z),r:Float(q.w)),
            translation:SIMD3(0,Float(frame.boardHeight),0))
        instanceEntities[instance].transform=Transform(matrix:base*physical.matrix)
        if frame.settled {
            updateLiveFraming()
            #if DEBUG
            if activePositionID != nil,!reviewRotations.isEmpty {
                let degrees=reviewRotations.removeFirst()
                setLivePhysicalOrientation(simd_quatd(angle:degrees*Double.pi/180,axis:SIMD3(0,0,1)))
            }
            #endif
        }
        onLiveFrame?()
    }

    private func updateLiveFraming() {
        var points:[SIMD3<Float>]=[]
        for entity in instanceEntities {
            let bounds=entity.visualBounds(relativeTo:root)
            points += Self.boundsCorners(BoardModelBounds(minimum:[Double(bounds.min.x),Double(bounds.min.y),Double(bounds.min.z)],
                maximum:[Double(bounds.max.x),Double(bounds.max.y),Double(bounds.max.z)]))
        }
        for (index,frame) in liveFrames.enumerated() { for rope in frame.ropes { for point in rope.positions {
            let world=liveBaseTransforms[index]*SIMD4<Float>(Float(point.x),Float(point.y),Float(point.z),1)
            let p=SIMD3<Float>(world.x,world.y,world.z),r=Float(rope.radius)
            points += [p-SIMD3(repeating:r),p+SIMD3(repeating:r)]
        } } }
        guard !points.isEmpty else { return }
        let minimum=points.reduce(SIMD3<Float>(repeating:.infinity),simd_min)
        let maximum=points.reduce(SIMD3<Float>(repeating:-.infinity),simd_max)
        // A conservative body rotation envelope keeps the camera stationary
        // while the board moves; refitting happens only at accepted rest.
        let radius=Self.boundsCorners(descriptor.modelBounds).map(simd_length).max() ?? 0
        var low=minimum,high=maximum
        for (index,frame) in liveFrames.enumerated() {
            let world=liveBaseTransforms[index]*SIMD4<Float>(0,Float(frame.boardHeight),0,1)
            let center=SIMD3<Float>(world.x,world.y,world.z)
            low=simd_min(low,center-SIMD3(repeating:radius))
            high=simd_max(high,center+SIMD3(repeating:radius))
        }
        if let framing=Self.framing(bounds:BoardModelBounds(minimum:[Double(low.x),Double(low.y),Double(low.z)],
            maximum:[Double(high.x),Double(high.y),Double(high.z)]),display:display) {
            currentFraming=framing
        }
        updateCameraTransform()
    }

    var hasLiveUpdateSubscription: Bool { liveSubscription != nil }

    func installLiveUpdateSubscription(_ subscription:EventSubscription?) {
        liveSubscription?.cancel(); liveSubscription=subscription
    }
    func advanceLiveRopes(elapsed:Double) {
        guard activePositionID != nil,liveFailure == nil else { return }
        liveControllers.forEach { $0.advance(elapsed:elapsed) }
    }
    func setLiveActivity(_ active:Bool) {
        #if DEBUG
        LiveRopeReviewTrace.log("scene activity requested=\(active) current=\(liveActivity) position=\(String(describing:activePositionID))")
        #endif
        guard liveActivity != active else { return }
        liveActivity=active
        for controller in liveControllers {
            if active && activePositionID != nil { controller.resume() } else { controller.pause() }
        }
    }
    func configureLiveMotion(reduceMotion:Bool,displayOnly:Bool) {
        liveControllers.forEach { $0.settleImmediately = reduceMotion || displayOnly }
    }
    func stopLiveRopes() {
        liveSubscription?.cancel(); liveSubscription=nil
        liveControllers.forEach { $0.stop() }
    }
    private func failLiveRopes(_ error:Error) {
        liveFailure=error; stopLiveRopes()
        transientCordEntity?.removeFromParent(); transientCordEntity=nil
        onLiveFailure?()
    }
    #if DEBUG
    func applyReviewCamera() {
        guard !reviewCameraApplied,let view=ProcessInfo.processInfo.environment["HANGTEN_REVIEW_MODEL_VIEW"],
              ["front","side","top"].contains(view),let framing=currentFraming else { return }
        reviewCameraApplied=true
        let front = Float.pi-atan2(framing.direction.x,framing.direction.z)
        orbitAzimuth=front+(view == "side" ? .pi/2:0)
        orbitElevation=view == "top" ? .pi/2-0.001:0
        updateCameraTransform()
    }
    func setLivePhysicalOrientation(_ orientation:simd_quatd) {
        liveGeneration &+= 1
        for controller in liveControllers { controller.setTarget(orientation:orientation,generation:liveGeneration) }
    }
    #endif
    deinit { liveSubscription?.cancel() }

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

    nonisolated static func perspectiveFitDistance(framing: SuspendedCameraFraming,
                                       viewportSize: CGSize,
                                       fieldOfViewDegrees: Float,
                                       distanceMultiplier: Float = 1) -> Float? {
        guard fieldOfViewDegrees.isFinite, fieldOfViewDegrees > 0, fieldOfViewDegrees < 179,
              distanceMultiplier.isFinite, distanceMultiplier > 0,
              framing.width.isFinite, framing.width > 0,
              framing.height.isFinite, framing.height > 0,
              framing.depth.isFinite, framing.depth >= 0,
              framing.fitPadding.isFinite, framing.fitPadding > 0 else { return nil }
        let aspect = viewportSize.width > 0 && viewportSize.height > 0
            ? Float(viewportSize.width / viewportSize.height) : 1
        let tangent = tan(fieldOfViewDegrees * .pi / 360)
        guard aspect.isFinite, aspect > 0, tangent.isFinite, tangent > 0 else { return nil }
        let verticalDistance = framing.height * 0.5 / tangent
        let horizontalDistance = framing.width * 0.5 / (tangent * aspect)
        let distance = (max(verticalDistance, horizontalDistance) + framing.depth * 0.5)
            * framing.fitPadding * distanceMultiplier
        return distance.isFinite && distance > 0 ? distance : nil
    }

    func fittedOrthographicScale(in size: CGSize) -> Double? {
        guard let framing = currentFraming else { return nil }
        guard size.width > 0, size.height > 0 else { return nil }
        let aspect = Float(size.width / size.height)
        return Double(max(framing.height, framing.width / aspect) * framing.fitPadding / orbitZoom / 2)
    }

    private func buildContactEntities() throws {
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

                var matchedNodeIDs: Set<String> = []
                traverseEntities(instanceEntity) { entity in
                    if let modelEntity = entity as? ModelEntity,
                       let nodeID = findNodeID(for: entity, relativeTo: instanceEntity,
                                               nodeIDToSlotID: nodeIDToSlotID),
                       let slotID = nodeIDToSlotID[nodeID],
                       let contactID = slotIDToContactID[slotID] {
                        matchedNodeIDs.insert(nodeID)
                        contactEntities[contactID, default: []].append(modelEntity)
                        contactIDByEntity[modelEntity] = contactID
                        modelEntity.generateCollisionShapes(recursive: false)
                        modelEntity.components.set(InputTargetComponent())
                    }
                }
                try requireDescriptorNodes(nodeIDToSlotID, matched: matchedNodeIDs,
                                           slotIDToContactID: slotIDToContactID)
            } else {
                // Single instance (schema v1): descriptor.contacts is keyed by physical contact ID == slotID
                for (physicalContactID, contactDescriptor) in contactDescriptorByPhysicalID {
                    for nodeID in contactDescriptor.nodeIDs {
                        nodeIDToSlotID[nodeID] = physicalContactID
                    }
                }

                let slotIDToContactID = Dictionary(
                    nodeIDToSlotID.values.map { ($0, $0) },
                    uniquingKeysWith: { first, _ in first }
                )

                var matchedNodeIDs: Set<String> = []
                traverseEntities(instanceEntity) { entity in
                    if let modelEntity = entity as? ModelEntity,
                       let nodeID = findNodeID(for: entity, relativeTo: instanceEntity,
                                               nodeIDToSlotID: nodeIDToSlotID),
                       let slotID = nodeIDToSlotID[nodeID],
                       let contactID = slotIDToContactID[slotID] {
                        matchedNodeIDs.insert(nodeID)
                        contactEntities[contactID, default: []].append(modelEntity)
                        contactIDByEntity[modelEntity] = contactID
                        modelEntity.generateCollisionShapes(recursive: false)
                        modelEntity.components.set(InputTargetComponent())
                    }
                }
                try requireDescriptorNodes(nodeIDToSlotID, matched: matchedNodeIDs,
                                           slotIDToContactID: slotIDToContactID)
            }
        }
    }

    private func findNodeID(for entity: Entity, relativeTo instanceRoot: Entity,
                            nodeIDToSlotID: [String: String]) -> String? {
        if nodeIDToSlotID[entity.name] != nil { return entity.name }
        var components: [String] = []
        var current: Entity? = entity
        while let value = current, value !== instanceRoot {
            components.append(value.name)
            current = value.parent
        }
        let path = components.reversed().joined(separator: "/")
        return nodeIDToSlotID[path] == nil ? nil : path
    }

    private func requireDescriptorNodes(_ nodeIDToSlotID: [String: String],
                                        matched: Set<String>,
                                        slotIDToContactID: [String: String]) throws {
        guard let missingNodeID = nodeIDToSlotID.keys.sorted().first(where: { !matched.contains($0) }),
              let slotID = nodeIDToSlotID[missingNodeID],
              let contactID = slotIDToContactID[slotID] else { return }
        #if DEBUG
        print("[BoardModelRealityScene] Descriptor node \(missingNodeID) did not match an imported RealityKit entity")
        #endif
        throw BoardModelRealityError.missingContactDescriptor(contactID: contactID)
    }

    private func traverseEntities(_ entity: Entity, _ visit: (Entity) -> Void) {
        visit(entity)
        for child in entity.children {
            traverseEntities(child, visit)
        }
    }

    private func applyHighlight(to entity: ModelEntity, color: Color, mode: BoardHighlightMode) {
        guard let baseline = baselineMaterials[entity] else { return }

        if color == .clear {
            // Restore the complete runtime finish, including a wood shader.
            entity.model?.materials = [baseline]
            return
        }

        // Use a solid selection color for legibility over either finish.
        var material = (baseline as? PhysicallyBasedMaterial) ?? Self.neutralMaterial()
        let uiColor = UIColor(color)
        material.baseColor = .init(tint: uiColor.withAlphaComponent(0.6))
        material.roughness = .init(floatLiteral: 0.8)

        entity.model?.materials = [material]
    }

    private func updateCameraTransform(animated: Bool = false, completion: (() -> Void)? = nil) {
        // Update camera position based on orbit state and framing
        let framing = currentFraming
        let fov = camera.camera.fieldOfViewInDegrees
        let distanceMultiplier = Float(display.camera.distanceMultiplier ?? 1)
        let distance = framing.flatMap {
            Self.perspectiveFitDistance(framing: $0, viewportSize: viewportSize,
                                       fieldOfViewDegrees: fov,
                                       distanceMultiplier: distanceMultiplier)
        } ?? (framing?.distance ?? 1)
        let target = framing?.target ?? SIMD3<Float>(0, 0, 0)
        let up = framing?.up ?? SIMD3<Float>(0, 1, 0)
        let direction = simd_normalize(-(framing?.direction ?? SIMD3<Float>(0, 0, -1)))
        let right = framing?.right ?? SIMD3<Float>(1, 0, 0)
        let yaw = simd_quatf(angle: orbitAzimuth, axis: up)
        let yawedDirection = yaw.act(direction)
        let yawedRight = simd_normalize(yaw.act(right))
        let pitch = simd_quatf(angle: -orbitElevation, axis: yawedRight)
        let outward = pitch.act(yawedDirection)
        var fittedDistance = distance
        if let framing, !framing.includedPoints.isEmpty, viewportSize.width > 0, viewportSize.height > 0 {
            // The original projected spans stop describing the bounds after
            // orbit. Fit the same geometry in the camera's actual basis.
            let cross = simd_cross(-outward,SIMD3<Float>(0,1,0))
            let cameraRight = simd_length_squared(cross)>1e-12 ? simd_normalize(cross):yawedRight
            let cameraUp = simd_cross(cameraRight,-outward)
            let tangent = tan(fov * .pi/360)
            let aspect = Float(viewportSize.width/viewportSize.height)
            let low = framing.includedPoints.reduce(SIMD3<Float>(repeating:.infinity),simd_min)
            let high = framing.includedPoints.reduce(SIMD3<Float>(repeating:-.infinity),simd_max)
            for x in [low.x,high.x] { for y in [low.y,high.y] { for z in [low.z,high.z] {
                let offset = SIMD3(x,y,z)-target
                let span = max(abs(simd_dot(offset,cameraRight))/aspect,abs(simd_dot(offset,cameraUp)))
                fittedDistance = max(fittedDistance,simd_dot(offset,outward)+span*framing.fitPadding/tangent)
            } } }
        }
        camera.position = target + outward * (fittedDistance * orbitZoom)
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
                result = result * reflectionMatrix(center: center)
            }
            return result
        }
        let base = transformMatrix(instance.baseTransform, pivot: center)
        let position = positionID.flatMap { instance.positionTransforms?[$0] }
        let baseTranslation = instance.baseTransform.translation.count == 3
            ? SIMD3<Float>(instance.baseTransform.translation.map(Float.init)) : .zero
        return transformMatrix(position, pivot: center + baseTranslation) * base
    }

    private static func reflectionMatrix(center: SIMD3<Float>) -> simd_float4x4 {
        var reflection = matrix_identity_float4x4
        reflection.columns.0.x = -1
        reflection.columns.3.x = 2 * center.x
        return reflection
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
        let url = resourceLease.url
        let computedSHA256 = try await Task.detached(priority: .utility) {
            try Self.sha256(of: url)
        }.value
        guard computedSHA256 == media.descriptor.modelSHA256 else {
            throw BoardModelRealityError.sha256Mismatch(expected: media.descriptor.modelSHA256, actual: computedSHA256)
        }

        return BoardModelRealityLoadedSource(resourceLease: resourceLease)
    }

    nonisolated private static func sha256(of url: URL) throws -> String {
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

/// Loaded source shared only by waiters while the same key is in flight.
final class BoardModelRealityLoadedSource {
    let resourceLease: BoardModelRealityResourceLease

    init(resourceLease: BoardModelRealityResourceLease) {
        self.resourceLease = resourceLease
    }
}

/// Load gate to serialize 3D model loads.
/// Limit is 1 because RealityKit model loading is memory-intensive and concurrent
/// loads can cause OOM or GPU resource contention on iOS devices.
@MainActor
enum BoardModelRealityLoadGate {
    private static let limit = 1
    private static var active = 0
    private static var waiters: [(id: UUID, continuation: CheckedContinuation<Bool, Never>)] = []

    static var queuedWaiterCount: Int { waiters.count }

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
            physics: try store.presentationPhysicsInput(for: board, presentationID: presentation.id),
            presentationID: presentation.id,
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
