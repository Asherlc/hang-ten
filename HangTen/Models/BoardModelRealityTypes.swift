import Foundation
import RealityKit
import simd

/// RealityKit-native scene that owns the full model lifecycle.
@MainActor
final class BoardModelRealityScene {
    // Core state
    let root = Entity()
    let camera = PerspectiveCamera()

    private var modelEntity: ModelEntity?
    private var instanceEntities: [Entity] = []
    private var contactEntities: [String: [ModelEntity]] = [:]
    private var contactIDByEntity: [ObjectIdentifier: String] = [:]
    private var originalMaterials: [ObjectIdentifier: PhysicallyBasedMaterial] = [:]

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

    func load(usdzURL: URL) async throws {
        // Load USDZ model using RealityKit/ModelIO
        let modelEntity = try await ModelEntity.loadModel(contentsOf: usdzURL)
        self.modelEntity = modelEntity
        root.addChild(modelEntity)

        // Build contact entity mapping from descriptor
        buildContactEntities(from: modelEntity)
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
        contactIDByEntity[ObjectIdentifier(entity)]
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

    private func buildContactEntities(from modelEntity: ModelEntity) {
        // Traverse model entity hierarchy and build contact entity mapping
        modelEntity.visit { entity in
            if let modelEntity = entity as? ModelEntity,
               let contactID = findContactID(for: entity) {
                contactEntities[contactID, default: []].append(modelEntity)
                contactIDByEntity[ObjectIdentifier(modelEntity)] = contactID
                originalMaterials[ObjectIdentifier(modelEntity)] = modelEntity.model?.materials.first as? PhysicallyBasedMaterial
            }
        }
    }

    private func findContactID(for entity: Entity) -> String? {
        // Find contact ID from entity name or user data
        // This would use the descriptor's node/contact mapping
        return nil
    }

    private func applyHighlight(to entity: ModelEntity, color: Color, mode: BoardHighlightMode) {
        guard var material = entity.model?.materials.first as? PhysicallyBasedMaterial else { return }
        // Apply highlight tint
        var baseColor = material.baseColor
        if case .color(let highlightColor) = baseColor {
            // Blend with highlight
            material.baseColor = .color(highlightColor)
        }
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

/// Loader with SHA-256 verify, cache, resource lease.
@MainActor
final class BoardModelRealityLoader {
    static func load(board: Hangboard, presentation: BoardPresentation) async throws -> BoardModelRealityScene {
        // Implementation will:
        // 1. Verify SHA-256 of USDZ asset
        // 2. Check cache for existing scene
        // 3. Acquire resource lease for on-demand resources
        // 4. Create BoardModelRealityScene with descriptor, display, suspension, orientation
        // 5. Load USDZ into scene
        // 6. Return configured scene

        throw NSError(domain: "BoardModelRealityLoader", code: -1, userInfo: [NSLocalizedDescriptionKey: "Not implemented"])
    }
}