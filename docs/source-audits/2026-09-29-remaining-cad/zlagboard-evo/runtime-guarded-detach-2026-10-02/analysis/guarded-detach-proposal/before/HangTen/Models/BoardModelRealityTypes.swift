import Foundation
#if DEBUG
import Combine
#endif
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
    #if DEBUG
    let diagnosticLifecycleToken = UUID()
    var diagnosticSelection: (Set<String>?, BoardHighlightMode?) {
        (lastHighlightedContactIDs, lastHighlightMode)
    }
    #endif
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
        let woodNodes = Set(display.woodNodeIDs)
        let plasticNodes = Set(display.plasticNodeIDs)
        let graniteNodes = Set(display.graniteNodeIDs)
        self.finishByNodeID = Dictionary(uniqueKeysWithValues: descriptor.nodes.map {
            ($0.nodeID, $0.role == .attachment ? .neutral
                : woodNodes.contains($0.nodeID) ? .wood
                : plasticNodes.contains($0.nodeID) ? .plastic
                : graniteNodes.contains($0.nodeID) ? .granite : display.surfaceFinish)
        })
        #if DEBUG
        if BoardHighlightDiagnostic.isEnabled {
            BoardHighlightDiagnostic.shared.boardSceneConstructed(scene: self)
        }
        #endif
    }

/// Loads the USDZ model directly into RealityKit and binds descriptor nodes.
    func load(usdzURL: URL) async throws {
        // RealityKit imports the USDZ asynchronously and reports malformed assets.
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

        // Appearance is runtime-only; the bundled USDZ stays unbound. Capture
        // each finish before highlighting so deselection restores the authored finish.
        applyBoardMaterials()

        // Build contact entity mapping from descriptor
        // Highlight baselines were captured by applyBoardMaterials().
        try buildContactEntities()

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

    func applyBoardMaterials() {
        for instance in instanceEntities {
            applyBoardMaterials(to: instance, relativeTo: instance, inheritedFinish: display.surfaceFinish)
        }
    }

    private func applyBoardMaterials(to entity: Entity, relativeTo instanceRoot: Entity,
                                     inheritedFinish: BoardSurfaceFinish) {
        // CAD descriptor names identify the authored surfaces. Carry the finish
        // through any unnamed mesh children inserted by the USDZ importer.
        let nodeID = findNodeID(for: entity, relativeTo: instanceRoot, bindings: finishByNodeID)
        let finish = nodeID.flatMap { finishByNodeID[$0] } ?? inheritedFinish
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
            applyBoardMaterials(to: child, relativeTo: instanceRoot, inheritedFinish: finish)
        }
    }

    private static let woodMaterial: any RealityKit.Material = {
        var base = PhysicallyBasedMaterial()
        base.baseColor = .init(tint: UIColor(red: 0.78, green: 0.66, blue: 0.49, alpha: 1))
        base.roughness = .init(floatLiteral: 0.82)
        base.metallic = .init(floatLiteral: 0)
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
        guard let positionID else {
            clearSelection()
            return false
        }
        guard allowedPositionIDs.contains(positionID) else {
            return false
        }
        if activePositionID == positionID { return true }

        if let instances, !instances.isEmpty {
            guard instances.count == instanceEntities.count else { return false }
            var selectedFraming: SuspendedCameraFraming?
            var selectedTransforms: [simd_float4x4] = []
            let cordGroup = Entity()
            for instance in instances {
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
                selectedTransforms.append(transform)
            }
            for (entity, transform) in zip(instanceEntities, selectedTransforms) {
                entity.transform = Transform(matrix: transform)
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
        activePositionID = nil
        transientCordEntity?.removeFromParent()
        transientCordEntity = nil
        if let instances, !instances.isEmpty, instances.count == instanceEntities.count {
            let center = Self.boundsCenter(descriptor.modelBounds)
            for (entity, instance) in zip(instanceEntities, instances) {
                entity.transform = Transform(matrix: Self.instanceMatrix(
                    instance: instance, positionID: nil, center: center))
            }
        } else {
            for entity in instanceEntities { entity.transform = .identity }
        }
        currentFraming = canonicalFraming
        updateCameraTransform()
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
        #if DEBUG
        if BoardHighlightDiagnostic.isEnabled,
           contactIDs != lastHighlightedContactIDs || mode != lastHighlightMode {
            BoardHighlightDiagnostic.shared.capture("highlight-before", scene: self,
                ids: contactIDs, mode: mode, priorIDs: lastHighlightedContactIDs,
                priorMode: lastHighlightMode)
        }
        #endif
        guard contactIDs != lastHighlightedContactIDs || mode != lastHighlightMode else { return }
        lastHighlightedContactIDs = contactIDs
        lastHighlightMode = mode
        // A shared mesh is selected when any of its logical contacts is selected.
        // Update each entity once so an unselected membership cannot clear it.
        let highlightedEntities = Set(contactIDs.flatMap { contactEntities[$0] ?? [] })
        let allEntities = Set(contactEntities.values.flatMap { $0 })
        for entity in allEntities {
            let highlightColor: Color = highlightedEntities.contains(entity)
                ? (mode == .active ? Color.holdActive : Color.restBlue) : .clear
            applyHighlight(to: entity, color: highlightColor, mode: mode)
        }
        #if DEBUG
        if BoardHighlightDiagnostic.isEnabled {
            BoardHighlightDiagnostic.shared.capture("highlight-after", scene: self)
        }
        #endif
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
                                               bindings: nodeIDToSlotID),
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
                // V1 picking uses the node's primary identity. Memberships come
                // from the full contact inventory and may share the same mesh.
                for node in descriptor.nodes where node.role == .contact {
                    if let primaryID = node.contactID {
                        nodeIDToSlotID[node.nodeID] = primaryID
                    }
                }
                var contactIDsByNodeID: [String: [String]] = [:]
                for contactID in contactDescriptorByPhysicalID.keys.sorted() {
                    for nodeID in contactDescriptorByPhysicalID[contactID]?.nodeIDs ?? [] {
                        contactIDsByNodeID[nodeID, default: []].append(contactID)
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
                                               bindings: nodeIDToSlotID),
                       let slotID = nodeIDToSlotID[nodeID],
                       let contactID = slotIDToContactID[slotID] {
                        matchedNodeIDs.insert(nodeID)
                        for member in contactIDsByNodeID[nodeID] ?? [] {
                            contactEntities[member, default: []].append(modelEntity)
                        }
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

    private func findNodeID<Value>(for entity: Entity, relativeTo instanceRoot: Entity,
                                   bindings: [String: Value]) -> String? {
        if bindings[entity.name] != nil { return entity.name }
        var components: [String] = []
        var current: Entity? = entity
        while let value = current, value !== instanceRoot {
            components.append(value.name)
            current = value.parent
        }
        let path = components.reversed().joined(separator: "/")
        return bindings[path] == nil ? nil : path
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
        let zoomedDistance = distance * orbitZoom
        let target = framing?.target ?? SIMD3<Float>(0, 0, 0)
        let up = framing?.up ?? SIMD3<Float>(0, 1, 0)
        let direction = simd_normalize(-(framing?.direction ?? SIMD3<Float>(0, 0, -1)))
        let right = framing?.right ?? SIMD3<Float>(1, 0, 0)
        let yaw = simd_quatf(angle: orbitAzimuth, axis: up)
        let yawedDirection = yaw.act(direction)
        let yawedRight = simd_normalize(yaw.act(right))
        let pitch = simd_quatf(angle: -orbitElevation, axis: yawedRight)
        camera.position = target + pitch.act(yawedDirection) * zoomedDistance
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
        case .cadRoutedCord(let profile):
            return .twoBranch(try SuspendedBoardPresentation.solve(pose: pose, suspension: profile, bounds: bounds))
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

        #if DEBUG
        if BoardHighlightDiagnostic.isEnabled {
            // Open the existing process stream before the app's only scene constructor.
            _ = BoardHighlightDiagnostic.shared
        }
        #endif
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

#if DEBUG
/// Temporary recorder; an explicit DEBUG gate enables the bounded visibility experiment.
struct BoardDiagnosticSurfaceInputs: Equatable {
    let boardID: String
    let presentationID: String
    let positionID: String?
    let ids: Set<String>
    let mode: BoardHighlightMode
    let isDisplayOnly: Bool
}

@MainActor
final class BoardHighlightDiagnostic {
    static let isEnabled = ProcessInfo.processInfo.environment["HANGTEN_REVIEW_HIGHLIGHT_DIAGNOSTIC"] == "1"
    // Diagnostic launch constant: never toggled within an app process.
    static let suppressesAllHandHosts = isEnabled
        && ProcessInfo.processInfo.environment["HANGTEN_REVIEW_SUPPRESS_ALL_HAND_HOSTS"] == "1"
    static let usesPerspectiveHandCameras = isEnabled
        && ProcessInfo.processInfo.environment["HANGTEN_REVIEW_ALL_HAND_PERSPECTIVE"] == "1"
    static let shared = BoardHighlightDiagnostic()
    private var handLifecycleCounts: [String: Int] = [
        "single.constructor-entry": 0, "single.make-entry": 0,
        "pair.constructor-entry": 0, "pair.make-entry": 0
    ]
    // Launch-gated, weak-only census. Values never own a board scene or entity.
    private static let recordsPredecessorAttachments = isEnabled
        && ProcessInfo.processInfo.environment["HANGTEN_REVIEW_PREDECESSOR_ATTACHMENT_CENSUS"] == "1"
    @MainActor
    private final class WeakBoardLifetime {
        weak var wrapper: BoardModelRealityScene?
        weak var root: Entity?
        weak var camera: Entity?
        var constructedIDs: [String: String] = [:]
    }
    private var boardLifetimes: [UUID: WeakBoardLifetime] = [:]
    private let enabled: Bool
    private var sink: FileHandle?
    private var sequence = 0
    private var failed = false
    private struct ViewSceneKey: Hashable {
        let scene: UUID
        let view: UUID
    }
    private var samplers: [ViewSceneKey: Task<Void, Never>] = [:]
    private var viewSignatures: [ViewSceneKey: String] = [:]
    private var requestedIDs: [UUID: Set<String>] = [:]
    private var requestedModes: [UUID: String] = [:]
    private var resolvedSurfaceInputs: [UUID: [String: Any]] = [:]
    private var visibilityPending: Set<UUID> = []
    private var visibilityStarted: Set<UUID> = []
    private var visibilityTasks: [UUID: Task<Void, Never>] = [:]
    private var visibilityRestores: [UUID: () -> Void] = [:]
    private weak var secondHostRoot: Entity?
    private weak var secondHostCamera: Entity?
    private var secondHostToken: UUID?
    private var viewports: [UUID: CGSize] = [:]
    private weak var standaloneScene: BoardModelRealityScene?
    private var standaloneViewToken: UUID?
    private var standaloneViewport: CGSize = .zero
    private var standaloneViewportChanged: TimeInterval = 0
    private var standaloneCounter: BoardDiagnosticUpdateCounter?
    private var standaloneSubscription: (any Cancellable)?

    private init() {
        let env = ProcessInfo.processInfo.environment
        enabled = Self.isEnabled
        guard enabled else { return }
        do {
            let rawRun = env["HANGTEN_REVIEW_DIAGNOSTIC_RUN"] ?? "placid-badger-cad-second-half"
            let run = String(rawRun.filter { $0.isASCII && ($0.isLetter || $0.isNumber || $0 == "-" || $0 == "_") }.prefix(100))
            guard !run.isEmpty else { throw CocoaError(.fileWriteInvalidFileName) }
            let directory = FileManager.default.urls(for: .documentDirectory, in: .userDomainMask)[0]
                .appendingPathComponent("HighlightDiagnostic-\(run)", isDirectory: true)
            try FileManager.default.createDirectory(at: directory, withIntermediateDirectories: true)
            // Unique per process: never append to or truncate an earlier evidence file.
            let url = directory.appendingPathComponent("events-\(UUID().uuidString).jsonl")
            guard FileManager.default.createFile(atPath: url.path, contents: nil) else {
                throw CocoaError(.fileWriteUnknown)
            }
            sink = try FileHandle(forWritingTo: url)
            emit(["event": "recorder-open", "path": url.path,
                  "processID": ProcessInfo.processInfo.processIdentifier,
                  "handLifecycleInstrumentationVersion": 1,
                  "suppressesAllHandHosts": Self.suppressesAllHandHosts,
                  "usesPerspectiveHandCameras": Self.usesPerspectiveHandCameras])
        } catch { fail(error) }
    }

    /// Sparse lifetime observations only; no SwiftUI state or scene mutation.
    func handLifecycle(kind: String, event: String, root: Entity) {
        guard enabled else { return }
        let key = "\(kind).\(event)"
        guard let previous = handLifecycleCounts[key] else { return }
        handLifecycleCounts[key] = previous + 1
        emit(["event": "hand-lifecycle", "handKind": kind, "lifecycleEvent": event,
              "handRootID": String(describing: ObjectIdentifier(root))])
    }

    /// Sparse configuration/reset evidence; never called from body or per frame.
    func handCamera(kind: String, event: String, camera: Entity,
                    points: [SIMD4<Float>]? = nil) {
        guard enabled else { return }
        let perspective = camera.components[PerspectiveCameraComponent.self]
        let orthographic = camera.components[OrthographicCameraComponent.self]
        var value: [String: Any] = ["event": "hand-camera", "handKind": kind,
            "cameraEvent": event, "handCameraID": String(describing: ObjectIdentifier(camera)),
            "cameraTransform": matrix(camera),
            "perspectivePresent": perspective != nil, "orthographicPresent": orthographic != nil]
        if let perspective {
            value["near"] = perspective.near
            value["far"] = perspective.far
            value["fieldOfViewInDegrees"] = perspective.fieldOfViewInDegrees
            value["fieldOfViewOrientation"] = String(describing: perspective.fieldOfViewOrientation)
        }
        if let orthographic {
            value["near"] = orthographic.near
            value["far"] = orthographic.far
            value["orthographicScale"] = orthographic.scale
        }
        if let points {
            let inverse = simd_inverse(camera.transform.matrix)
            let depths = points.map { -(inverse * $0).z }
            value["framingVertexCount"] = points.count
            value["allDepthsFinite"] = depths.allSatisfy(\.isFinite)
            if !depths.isEmpty, depths.allSatisfy(\.isFinite) {
                value["minimumDepth"] = depths.min()!
                value["maximumDepth"] = depths.max()!
                value["allDepthsInsideUnchangedClips"] = depths.allSatisfy { $0 > 0.1 && $0 < 100 }
            }
        }
        emit(value)
    }

    /// Once per native board scene init, before its asynchronous USDZ load.
    func boardSceneConstructed(scene: BoardModelRealityScene) {
        guard enabled else { return }
        if Self.recordsPredecessorAttachments {
            let lifetime = WeakBoardLifetime()
            lifetime.wrapper = scene
            lifetime.root = scene.root
            lifetime.camera = scene.camera
            lifetime.constructedIDs = ["wrapperID": identity(scene),
                "rootID": identity(scene.root), "cameraID": identity(scene.camera),
                "modelSHA256": scene.descriptorForTesting.modelSHA256]
            boardLifetimes[scene.diagnosticLifecycleToken] = lifetime
        }
        emit(["event": "board-scene-constructed",
              "sceneLifecycleToken": scene.diagnosticLifecycleToken.uuidString,
              "sceneID": identity(scene), "rootID": identity(scene.root),
              "cameraID": identity(scene.camera),
              "modelSHA256": scene.descriptorForTesting.modelSHA256,
              "trainBoardSuppressionRequested": ProcessInfo.processInfo.environment[
                  "HANGTEN_REVIEW_SUPPRESS_TRAIN_BOARD_HOST"] == "1"])
    }

    /// Point observations only: retention and entity attachment do not prove rendering.
    private func boardLifetimeSnapshot() -> [[String: Any]] {
        func entitySnapshot(_ entity: Entity?) -> [String: Any] {
            guard let entity else { return ["alive": false] }
            return ["alive": true, "entityID": identity(entity),
                "parentEntityID": entity.parent.map(identity) ?? "nil",
                "realitySceneID": entity.scene.map(identity) ?? "nil",
                "enabled": entity.isEnabled, "isActive": entity.isActive]
        }
        return boardLifetimes.keys.sorted { $0.uuidString < $1.uuidString }.map { token in
            let lifetime = boardLifetimes[token]!
            return ["sceneLifecycleToken": token.uuidString,
                "constructedIDs": lifetime.constructedIDs,
                "wrapperAlive": lifetime.wrapper != nil,
                "root": entitySnapshot(lifetime.root),
                "camera": entitySnapshot(lifetime.camera)]
        }
    }

    private func fail(_ error: Error) {
        failed = true
        let text = "[BoardHighlightDiagnostic] recorder failure: \(error)\n"
        try? FileHandle.standardError.write(contentsOf: Data(text.utf8))
    }

    private func emit(_ fields: [String: Any]) {
        guard enabled, !failed, let sink else { return }
        // Hard bound: the diagnostic never becomes an indefinite background logger.
        guard sequence < 4096 else { return }
        sequence += 1
        var value = fields
        value["handLifecycleCounts"] = handLifecycleCounts
        value["sequence"] = sequence
        value["epoch"] = Date().timeIntervalSince1970
        value["uptime"] = ProcessInfo.processInfo.systemUptime
        value["complete"] = true
        if sequence == 4096 { value["eventLimitReached"] = true }
        do {
            var data = try JSONSerialization.data(withJSONObject: value, options: [.sortedKeys])
            data.append(0x0a)
            try sink.write(contentsOf: data)
            // Direct FileHandle writes bypass stdio buffering; synchronize at sparse markers.
            if fields["event"] as? String == "sample-end"
                || fields["event"] as? String == "view-disappear" || sequence == 4096 {
                try sink.synchronize()
            }
        } catch { fail(error) }
    }

    func standaloneViewportMatches(_ expected: CGSize) -> Bool {
        standaloneViewport == expected
    }

    var standaloneIsReady: Bool {
        guard let standaloneScene else { return false }
        return standaloneScene.root.scene != nil && standaloneScene.camera.isActive
            && standaloneViewport.width > 0 && standaloneViewport.height > 0
            && ProcessInfo.processInfo.systemUptime - standaloneViewportChanged >= 1
            && UIApplication.shared.applicationState == .active
    }

    func standaloneSchedule(baseUptime: TimeInterval, viewport: CGSize,
                            phaseDurations: [TimeInterval], phaseStartOffsets: [TimeInterval],
                            captureOffsets: [TimeInterval], snapshotOffsets: [[TimeInterval]],
                            completionTailOffset: TimeInterval, timingProfile: String) {
        if ProcessInfo.processInfo.environment["HANGTEN_REVIEW_SCENE_UPDATE_COUNTER"] == "1",
           let actualScene = standaloneScene?.root.scene {
            let counter = BoardDiagnosticUpdateCounter()
            standaloneCounter = counter
            standaloneSubscription = actualScene.subscribe(to: SceneEvents.Update.self) { [weak counter] _ in
                counter?.increment()
            }
        }
        var schedule: [String: Any] = ["event": "standalone-schedule", "baseUptime": baseUptime,
              "driver": ProcessInfo.processInfo.environment["HANGTEN_REVIEW_STANDALONE_DRIVER"] ?? "A",
              "baseEpoch": Date().timeIntervalSince1970 + baseUptime - ProcessInfo.processInfo.systemUptime,
              "phases": ["clear", "active", "preview", "active", "preview"],
              "phaseDurations": phaseDurations, "phaseStartOffsets": phaseStartOffsets,
              "totalDuration": phaseDurations.reduce(0, +), "completionTailOffset": completionTailOffset,
              "captureOffsets": captureOffsets, "snapshotOffsets": snapshotOffsets,
              "timingProfileLabel": timingProfile,
              "configuredViewportPoints": [Double(viewport.width), Double(viewport.height)],
              "actualViewportPoints": [Double(standaloneViewport.width), Double(standaloneViewport.height)],
              "applicationCensus": applicationCensus()]
        if let uniformDuration = phaseDurations.first,
           phaseDurations.allSatisfy({ $0 == uniformDuration }) {
            schedule["phaseSeconds"] = uniformDuration
        }
        emit(schedule)
    }

    func standaloneSnapshot(_ event: String) {
        guard let standaloneScene else { return }
        capture(event, scene: standaloneScene, view: standaloneViewToken)
    }

    func finishStandaloneObservation() {
        standaloneSnapshot("standalone-observation-end")
        standaloneSubscription?.cancel()
        standaloneSubscription = nil
        standaloneCounter = nil
    }

    func harnessObservedSelection(state: String, ids: Set<String>, mode: BoardHighlightMode,
                                  positionID: String?, viewport: CGSize) {
        guard enabled else { return }
        emit(["event": "standalone-observed-selection", "state": state,
              "ids": ids.sorted(), "mode": String(describing: mode),
              "positionID": positionID ?? "nil",
              "viewportPoints": [Double(viewport.width), Double(viewport.height)]])
    }

    func harnessEvent(_ event: String, state: String, viewport: CGSize) {
        guard enabled else { return }
        emit(["event": event, "state": state,
              "viewportPoints": [Double(viewport.width), Double(viewport.height)],
              "applicationCensus": applicationCensus()])
    }

    func surfaceInputs(_ inputs: BoardDiagnosticSurfaceInputs, scene: BoardModelRealityScene) {
        guard enabled else { return }
        let row: [String: Any] = ["boardID": inputs.boardID,
            "presentationID": inputs.presentationID, "positionID": inputs.positionID ?? "nil",
            "ids": inputs.ids.sorted(), "mode": String(describing: inputs.mode),
            "isDisplayOnly": inputs.isDisplayOnly]
        resolvedSurfaceInputs[scene.diagnosticLifecycleToken] = row
        emit(["event": "surface-inputs", "sceneLifecycleToken": scene.diagnosticLifecycleToken.uuidString,
              "resolvedSurfaceInputs": row])
    }

    private func applicationCensus() -> [String: Any] {
        let app = UIApplication.shared
        let scenes: [[String: Any]] = app.connectedScenes.compactMap { scene in
            guard let windowScene = scene as? UIWindowScene else { return nil }
            return ["sceneID": identity(windowScene),
                    "sessionID": windowScene.session.persistentIdentifier,
                    "activationState": windowScene.activationState.rawValue,
                    "interfaceOrientation": windowScene.interfaceOrientation.rawValue,
                    "windows": windowScene.windows.map { window -> [String: Any] in
                        var counts: [String: Int] = [:]
                        var placements: [[String: Any]] = []
                        func visit(_ view: UIView) {
                            let name = String(reflecting: type(of: view))
                            if name.contains("Reality") || name.contains("ARView") {
                                counts[name, default: 0] += 1
                                let rect = view.convert(view.bounds, to: window)
                                var placement: [String: Any] = ["viewID": String(describing: ObjectIdentifier(view)), "class": name,
                                    "frameInWindow": [Double(rect.minX), Double(rect.minY), Double(rect.width), Double(rect.height)],
                                    "hidden": view.isHidden, "alpha": Double(view.alpha)]
                                if let host = view as? ARView { placement["realitySceneID"] = String(describing: ObjectIdentifier(host.scene)) }
                                placements.append(placement)
                            }
                            view.subviews.forEach(visit)
                        }
                        visit(window)
                        return ["windowID": identity(window), "hidden": window.isHidden,
                                "alpha": Double(window.alpha), "key": window.isKeyWindow,
                                "bounds": [Double(window.bounds.width), Double(window.bounds.height)],
                                "rendererNamedViewClasses": counts, "rendererPlacements": placements]
                    }]
        }
        return ["applicationState": app.applicationState.rawValue, "windowScenes": scenes,
                "standaloneGate": ProcessInfo.processInfo.environment["HANGTEN_REVIEW_STANDALONE_BOARD"] == "1"]
    }

    private func identity(_ object: AnyObject) -> String { String(describing: ObjectIdentifier(object)) }
    private func renderMembership(root: Entity, camera: Entity) -> [String: Any] {
        var result: [String: Any] = [
            "rootEntityID": identity(root), "cameraEntityID": identity(camera),
            "rootRealitySceneID": root.scene.map(identity) ?? "nil",
            "cameraRealitySceneID": camera.scene.map(identity) ?? "nil",
            "rootActive": root.isActive, "cameraActive": camera.isActive,
            "orthographic": camera.components[OrthographicCameraComponent.self] != nil,
            "perspective": camera.components[PerspectiveCameraComponent.self] != nil,
            "cameraTransform": matrix(camera)]
        if let c = camera.components[OrthographicCameraComponent.self] {
            result["near"] = c.near; result["far"] = c.far; result["scale"] = c.scale
        }
        if let c = camera.components[PerspectiveCameraComponent.self] {
            result["near"] = c.near; result["far"] = c.far
            result["verticalFOVDegrees"] = c.fieldOfViewInDegrees
        }
        return result
    }

    func captureSecondHost(_ event: String, token: UUID, root: Entity, camera: Entity) {
        guard enabled else { return }
        if event == "second-host-make" {
            secondHostRoot = root; secondHostCamera = camera; secondHostToken = token
        }
        emit(["event": event, "secondHostLifecycleToken": token.uuidString,
              "secondHost": renderMembership(root: root, camera: camera)])
        if event == "second-host-disappear", secondHostToken == token {
            secondHostRoot = nil; secondHostCamera = nil; secondHostToken = nil
        }
    }

    private func matrix(_ entity: Entity) -> [Float] {
        let m = entity.transform.matrix
        return [m.columns.0, m.columns.1, m.columns.2, m.columns.3]
            .flatMap { [$0.x, $0.y, $0.z, $0.w] }
    }

    func capture(_ event: String, scene: BoardModelRealityScene,
                 view: UUID? = nil, roots: [Entity]? = nil,
                 ids: Set<String>? = nil, mode: BoardHighlightMode? = nil,
                 priorIDs: Set<String>? = nil, priorMode: BoardHighlightMode? = nil,
                 viewport: CGSize? = nil) {
        guard enabled else { return }
        let key = scene.diagnosticLifecycleToken
        if let viewport {
            viewports[key] = viewport
            if ProcessInfo.processInfo.environment["HANGTEN_REVIEW_STANDALONE_BOARD"] == "1" {
                if standaloneViewport != viewport || standaloneScene !== scene {
                    standaloneViewport = viewport
                    standaloneViewportChanged = ProcessInfo.processInfo.systemUptime
                }
                standaloneScene = scene
                if let view { standaloneViewToken = view }
            }
        }
        if let ids { requestedIDs[key] = ids }
        if let mode { requestedModes[key] = String(describing: mode) }
        let selected = requestedIDs[key] ?? []
        if let view, let roots, event == "view-make" || event == "view-update" {
            let viewKey = ViewSceneKey(scene: key, view: view)
            let signature = ([key.uuidString] + roots.map(identity) + [
                String(describing: matrix(scene.root)), String(describing: matrix(scene.camera)),
                requestedModes[key] ?? "unset", selected.sorted().joined(separator: ",")
            ]).joined(separator: "|")
            if event == "view-update", viewSignatures[viewKey] == signature { return }
            viewSignatures[viewKey] = signature
        }
        let surfaces: [[String: Any]] = selected.sorted().flatMap { id in
            (scene.contactEntities[id] ?? []).map { entity in
                var chain: [String] = []
                var parent: Entity? = entity
                var underRoot = false
                while let current = parent {
                    chain.append(identity(current))
                    if current === scene.root { underRoot = true }
                    parent = current.parent
                }
                var row: [String: Any] = ["contactID": id, "entityID": identity(entity),
                    "name": entity.name, "ancestors": chain, "underRegisteredRoot": underRoot,
                    "attached": entity.scene != nil, "enabled": entity.isEnabled,
                    "transform": matrix(entity)]
                if let material = entity.model?.materials.first {
                    row["materialType"] = String(describing: type(of: material))
                    if let pbr = material as? PhysicallyBasedMaterial {
                        var r: CGFloat = 0, g: CGFloat = 0, b: CGFloat = 0, a: CGFloat = 0
                        row["resolvedRGBAValid"] = pbr.baseColor.tint.getRed(&r, green: &g, blue: &b, alpha: &a)
                        row["rgba"] = [Double(r), Double(g), Double(b), Double(a)]
                    }
                }
                return row
            }
        }
        var row: [String: Any] = ["event": event, "sceneID": identity(scene),
            "sceneLifecycleToken": scene.diagnosticLifecycleToken.uuidString,
            "rootID": identity(scene.root), "cameraID": identity(scene.camera),
            "modelSHA256": scene.descriptorForTesting.modelSHA256,
            "selectedIDs": selected.sorted(), "requestedMode": requestedModes[key] ?? "unset",
            "cachedIDs": (scene.diagnosticSelection.0 ?? []).sorted(),
            "cachedMode": scene.diagnosticSelection.1.map { String(describing: $0) } ?? "unset",
            "rootAttached": scene.root.scene != nil, "rootEnabled": scene.root.isEnabled,
            "rootTransform": matrix(scene.root), "cameraTransform": matrix(scene.camera),
            "surfaces": surfaces]
        if let inputs = resolvedSurfaceInputs[key] { row["resolvedSurfaceInputs"] = inputs }
        if let standaloneCounter, scene === standaloneScene {
            row["sceneUpdateCount"] = standaloneCounter.value
        }
        if let viewport = viewports[key] {
            row["viewportPoints"] = [Double(viewport.width), Double(viewport.height)]
        }
        let workoutBoundaryCensus = ProcessInfo.processInfo.environment["HANGTEN_REVIEW_WORKOUT_BOUNDARY_CENSUS"] == "1"
            && (event == "highlight-before" || event == "highlight-after")
        if event == "view-make" || event == "sample" || event.hasPrefix("standalone-") || workoutBoundaryCensus {
            row["applicationCensus"] = applicationCensus()
        }
        row["boardRenderMembership"] = renderMembership(root: scene.root, camera: scene.camera)
        // After the existing view-update dedup guard; never part of its signature.
        // No additional event or sample is scheduled for this census.
        if Self.recordsPredecessorAttachments {
            row["boardLifetimeCensus"] = boardLifetimeSnapshot()
        }
        if let secondHostRoot, let secondHostCamera, let secondHostToken {
            row["secondHostLifecycleToken"] = secondHostToken.uuidString
            row["secondHost"] = renderMembership(root: secondHostRoot, camera: secondHostCamera)
        }
        if let view { row["viewToken"] = view.uuidString }
        if let roots {
            row["contentRootIDs"] = roots.map(identity)
            row["contentContainsRegisteredRoot"] = roots.contains { $0 === scene.root }
        }
        if let priorIDs { row["priorCachedIDs"] = priorIDs.sorted() }
        if let priorMode { row["priorCachedMode"] = String(describing: priorMode) }
        emit(row)
        let env = ProcessInfo.processInfo.environment
        if env["HANGTEN_REVIEW_ENTITY_VISIBILITY_PROBE"] == "1",
           env["HANGTEN_REVIEW_BOARD_ARVIEW_HOST"] != "1",
           env["HANGTEN_REVIEW_SUPPRESS_WORKOUT_HAND_HOST"] != "1" {
            if event == "highlight-before", mode == .preview, priorMode == .active, !selected.isEmpty {
                visibilityPending.insert(key)
            }
            if event == "highlight-after", visibilityPending.remove(key) != nil {
                startVisibilityProbe(scene: scene, ids: selected)
            }
        }
    }

    private func startVisibilityProbe(scene: BoardModelRealityScene, ids: Set<String>) {
        let key = scene.diagnosticLifecycleToken
        guard visibilityStarted.insert(key).inserted else { return }
        capture("visibility-scheduled", scene: scene)
        visibilityTasks[key] = Task { @MainActor [weak scene] in
            do { try await Task.sleep(for: .seconds(3)) }
            catch { return }
            guard !Task.isCancelled, let scene else { return }
            let entities = Set(ids.flatMap { scene.contactEntities[$0] ?? [] })
            let saved = entities.map { ($0, $0.isEnabled) }
            self.visibilityRestores[key] = { saved.forEach { $0.0.isEnabled = $0.1 } }
            defer {
                self.visibilityRestores.removeValue(forKey: key)?()
                self.visibilityTasks.removeValue(forKey: key)
                self.capture("visibility-restored", scene: scene)
            }
            self.capture("visibility-before-disable", scene: scene)
            entities.forEach { $0.isEnabled = false }
            self.capture("visibility-disabled", scene: scene)
            do { try await Task.sleep(for: .seconds(3)) }
            catch { return }
        }
    }

    func startSamples(view: UUID, scene: BoardModelRealityScene) {
        guard enabled else { return }
        // Standalone observations follow scripted sparse brackets instead of this sampler.
        guard ProcessInfo.processInfo.environment["HANGTEN_REVIEW_STANDALONE_BOARD"] != "1" else { return }
        let key = ViewSceneKey(scene: scene.diagnosticLifecycleToken, view: view)
        guard samplers[key] == nil else { return }
        samplers[key] = Task { @MainActor [weak scene] in
            for _ in 0..<120 {
                do { try await Task.sleep(for: .seconds(1)) }
                catch { return }
                guard !Task.isCancelled, let scene else { return }
                self.capture("sample", scene: scene, view: view)
            }
            if let scene { self.capture("sample-end", scene: scene, view: view) }
        }
    }

    func disappear(view: UUID, scene: BoardModelRealityScene) {
        guard enabled else { return }
        capture("view-disappear", scene: scene, view: view)
        if scene === standaloneScene, view == standaloneViewToken { finishStandaloneObservation() }
        let key = ViewSceneKey(scene: scene.diagnosticLifecycleToken, view: view)
        samplers.removeValue(forKey: key)?.cancel()
        if let restore = visibilityRestores.removeValue(forKey: scene.diagnosticLifecycleToken) {
            restore()
            capture("visibility-teardown-restored", scene: scene, view: view)
        }
        visibilityTasks.removeValue(forKey: scene.diagnosticLifecycleToken)?.cancel()
        viewSignatures.removeValue(forKey: key)
    }
}
#endif

#if DEBUG
/// No SwiftUI observations, per-frame I/O, scene ownership or rendering mutation.
private final class BoardDiagnosticUpdateCounter: @unchecked Sendable {
    private let lock = NSLock()
    private var count: UInt64 = 0
    func increment() { lock.lock(); count &+= 1; lock.unlock() }
    var value: UInt64 { lock.lock(); defer { lock.unlock() }; return count }
}
#endif
