import Foundation
import SwiftUI
import simd

/// Python-compatible `round(value, 9)` for finite JSON numbers. The fused
/// residual preserves which side of an exact scaled midpoint the binary input
/// occupies; values too large to scale are already integral at this precision.
func boardDescriptorRoundedToNinePlaces(_ value: Double) -> Double {
    let scale = 1_000_000_000.0
    guard value.isFinite else {
        return value
    }
    // Once adjacent Doubles are farther apart than the decimal quantum,
    // rounding by at most half that quantum converts back to this same value.
    // Avoid a multiply/divide round trip that can move an already-canonical
    // large value to an adjacent Double.
    if value.ulp > 1 / scale { return value }
    let scaled = value * scale
    let lower = scaled.rounded(.down)
    let upper = scaled.rounded(.up)
    if scaled - lower == 0.5 {
        let residual = (-scaled).addingProduct(value, scale)
        if residual < 0 { return lower / scale }
        if residual > 0 { return upper / scale }
        return (lower.truncatingRemainder(dividingBy: 2) == 0 ? lower : upper) / scale
    }
    return scaled.rounded(.toNearestOrEven) / scale
}

struct HoldFrame: Hashable {
    let x: CGFloat
    let y: CGFloat
    let width: CGFloat
    let height: CGFloat

    var rect: CGRect {
        CGRect(x: x, y: y, width: width, height: height)
    }
}

/// One independently shaped geometry piece belonging to a physical contact.
struct BoardContactPiece: Identifiable, Hashable {
    let id: String
    let contactID: String
    let frame: CGRect
    let shape: BoardShape
    let treatment: BoardContactTreatment

    func rect(in boardRect: CGRect) -> CGRect {
        CGRect(
            x: boardRect.minX + boardRect.width * frame.minX,
            y: boardRect.minY + boardRect.height * frame.minY,
            width: boardRect.width * frame.width,
            height: boardRect.height * frame.height
        )
    }

    func path(in boardRect: CGRect) -> Path {
        shape.path(in: rect(in: boardRect))
    }
}

struct BoardRasterMedia: Hashable {
    let assetPath: String
    let contactGeometry: [String: [BoardContactPiece]]
}

struct BoardModelBounds: Hashable {
    let minimum: [Double]
    let maximum: [Double]
}

struct BoardModelFacePlaneAABB: Hashable {
    let minimum: [Double]
    let maximum: [Double]

    var contactFrame: HoldFrame {
        return HoldFrame(
            x: minimum[0],
            y: minimum[1],
            width: boardDescriptorRoundedToNinePlaces(maximum[0] - minimum[0]),
            height: boardDescriptorRoundedToNinePlaces(maximum[1] - minimum[1])
        )
    }
}

struct BoardModelNodeDescriptor: Hashable, Codable {
    enum Role: String, Hashable, Codable {
        case body
        case contact
        case attachment
    }

    let nodeID: String
    let role: Role
    /// Deterministic picking identity, even when the mesh has other memberships.
    let contactID: String?
    let additionalContactIDs: [String]?

    init(nodeID: String, role: Role, contactID: String?, additionalContactIDs: [String]? = nil) {
        self.nodeID = nodeID
        self.role = role
        self.contactID = contactID
        self.additionalContactIDs = additionalContactIDs
    }

    enum CodingKeys: String, CodingKey {
        case nodeID
        case role
        case contactID = "contactSlotID"
        case additionalContactIDs
    }
}

struct BoardModelAttachment: Hashable {
    let nodeID: String
    let pointInModel: [Double]
    let provenance: String
}

struct BoardModelInvisibleAnchor: Hashable {
    let offsetFromBoardBounds: [Double]
    let visibility: String
    let provenance: String
    let position: [Double]
}

struct BoardModelCord: Hashable {
    let restLength: Double
    let radius: Double
    let material: String
    let provenance: String
}

struct BoardModelCanonicalCamera: Hashable {
    let viewDirection: [Double]
    let fitPadding: Double
}

struct BoardModelCanonicalPose: Hashable {
    let rotation: [Double]
    var translation: [Double]
    let camera: BoardModelCanonicalCamera
    // Visible exterior endpoints in this pose; clipped display endpoints do
    // not establish additional physical mouths or an inferred interior route.
    var attachmentPoints: [String: [Double]]? = nil
    // Ordered exterior contact points keyed by paired-lead attachment ID or
    // two-branch passage ID. Passage overrides never change the actual bore.
    var cordContactPoints: [String: [[Double]]]? = nil
    /// Complete exterior route for each loop in a point-passage two-branch
    /// suspension. These are display estimates in unposed model coordinates.
    var wrappedRoutes: [String: [[Double]]]? = nil
}

struct BoardModelSingleCordSuspension: Hashable {
    let attachment: BoardModelAttachment
    let anchor: BoardModelInvisibleAnchor
    let cord: BoardModelCord
    let canonicalPoses: [String: BoardModelCanonicalPose]
}

struct BoardModelPairedLeadAttachment: Hashable {
    let id: String
    let nodeID: String
    let pointInModel: [Double]
    let provenance: String
    /// Ordered surface contacts from the free hanging span to the terminal
    /// attachment. Empty preserves the direct exterior-lead presentation.
    var contactPointsInModel: [[Double]] = []
}

struct BoardModelPairedLeadCord: Hashable {
    let attachments: [BoardModelPairedLeadAttachment]
    let passages: BoardModelPassagePairs
    let anchor: BoardModelInvisibleAnchor
    let cord: BoardModelCord
    let canonicalPoses: [String: BoardModelCanonicalPose]
}

struct BoardModelPassage: Hashable {
    let id: String
    let nodeID: String
    /// Ordered physical mouths of one actual through-bore. The renderer uses
    /// both points; a single mouth cannot stand in for the bore's route.
    let entryPointInModel: [Double]
    let exitPointInModel: [Double]
    let provenance: String
    let isThroughBore: Bool
    var pointInModel: [Double] { entryPointInModel }

    init(id: String, nodeID: String, entryPointInModel: [Double], exitPointInModel: [Double], provenance: String) {
        self.id = id
        self.nodeID = nodeID
        self.entryPointInModel = entryPointInModel
        self.exitPointInModel = exitPointInModel
        self.provenance = provenance
        self.isThroughBore = true
    }

    init(id: String, nodeID: String, pointInModel: [Double], provenance: String) {
        self.id = id
        self.nodeID = nodeID
        self.entryPointInModel = pointInModel
        self.exitPointInModel = pointInModel
        self.provenance = provenance
        self.isThroughBore = false
    }
}

struct BoardModelPassagePairs: Hashable {
    let left: [BoardModelPassage]
    let right: [BoardModelPassage]
}

struct BoardModelCordBranch: Hashable {
    let id: String
    let passageIDs: [String]
    /// Bounded front-shoulder guide from the incoming free span to the first
    /// bore's entry mouth.
    let entryContactPoints: [[Double]]
    /// Centerline guide points for the bounded exterior bearing route between
    /// the two bore exits. These are not free catenary samples.
    let exteriorContactPoints: [[Double]]
    /// Bounded front-shoulder guide from the second bore's entry mouth back
    /// to the outgoing free span.
    let exitContactPoints: [[Double]]
    let restLength: Double
    let radius: Double
    let material: String
    let provenance: String

    init(id: String, passageIDs: [String], entryContactPoints: [[Double]] = [], exteriorContactPoints: [[Double]] = [], exitContactPoints: [[Double]] = [], restLength: Double, radius: Double, material: String, provenance: String) {
        self.id = id
        self.passageIDs = passageIDs
        self.entryContactPoints = entryContactPoints
        self.exteriorContactPoints = exteriorContactPoints
        self.exitContactPoints = exitContactPoints
        self.restLength = restLength
        self.radius = radius
        self.material = material
        self.provenance = provenance
    }
}

enum BoardModelLoopWinding: String, Hashable {
    /// Hull traversal from the anchor tangent to the channel mouth, viewed
    /// in the model's (y, z) cross-section.
    case clockwise
    case counterclockwise
}

struct BoardModelTwoBranchSuspension: Hashable {
    let passages: BoardModelPassagePairs
    let branches: [BoardModelCordBranch]
    var anchor: BoardModelInvisibleAnchor
    let canonicalPoses: [String: BoardModelCanonicalPose]
    /// Runtime convex-section wrap clearance for exterior point passages.
    /// Nil retains explicitly authored routes or direct point-passage spans.
    var meshWrapClearance: Double? = nil
    /// Two mouths per end connected by a hidden channel in the CAD body.
    /// The loaded mesh and hanging point determine each exterior lead at runtime.
    var internalLoopClearance: Double? = nil
    /// Threading topology is fixed when the cord is installed; contact points
    /// along that route are recomputed from the mesh for every board pose.
    var internalLoopWindingByPassageID: [String: BoardModelLoopWinding]? = nil
    /// Length of the connected CAD channel centerline between each mouth pair.
    var internalLoopChannelLengthByBranchID: [String: Double]? = nil
    var internalLoopChannelPointsByBranchID: [String: [[Double]]]? = nil
}

struct BoardModelCADCordStrand: Hashable {
    let id: String
    let kind: String
    let restLength: Double
    let radius: Double
    let material: String
    let provenance: String
}

struct BoardModelCADRoutedCord: Hashable {
    let bodyNodeID: String
    let strands: [BoardModelCADCordStrand]
    let anchor: BoardModelInvisibleAnchor
    let canonicalPoses: [String: BoardModelCanonicalPose]
}

enum BoardModelSuspension: Hashable {
    case singleCord(BoardModelSingleCordSuspension)
    case pairedLeadCord(BoardModelPairedLeadCord)
    case twoBranchCord(BoardModelTwoBranchSuspension)
    case cadRoutedCord(BoardModelCADRoutedCord)

    // Compatibility projections for the existing single-cord renderer. New
    // two-branch consumers must switch on the discriminator explicitly.
    init(
        attachment: BoardModelAttachment,
        anchor: BoardModelInvisibleAnchor,
        cord: BoardModelCord,
        canonicalPoses: [String: BoardModelCanonicalPose]
    ) {
        self = .singleCord(BoardModelSingleCordSuspension(
            attachment: attachment,
            anchor: anchor,
            cord: cord,
            canonicalPoses: canonicalPoses
        ))
    }

    var attachment: BoardModelAttachment {
        switch self {
        case .cadRoutedCord(let suspension):
            return BoardModelAttachment(nodeID: suspension.bodyNodeID,
                pointInModel: suspension.canonicalPoses.values.first!.wrappedRoutes!.values.first!.first!,
                provenance: "nativeCADSolve")
        case .singleCord(let suspension): return suspension.attachment
        case .pairedLeadCord(let suspension):
            guard let attachment = suspension.attachments.first else {
                preconditionFailure("pairedLeadCord must have at least one attachment")
            }
            return BoardModelAttachment(
                nodeID: attachment.nodeID,
                pointInModel: attachment.pointInModel,
                provenance: attachment.provenance
            )
        case .twoBranchCord(let suspension):
            guard let passage = suspension.passages.left.first else {
                preconditionFailure("twoBranchCord must have at least one left passage")
            }
            return passage.asAttachment
        }
    }

    var anchor: BoardModelInvisibleAnchor {
        switch self {
        case .cadRoutedCord(let suspension): suspension.anchor
        case .singleCord(let suspension): suspension.anchor
        case .pairedLeadCord(let suspension): suspension.anchor
        case .twoBranchCord(let suspension): suspension.anchor
        }
    }

    var cord: BoardModelCord {
        switch self {
        case .cadRoutedCord(let suspension):
            let strand = suspension.strands[0]
            return BoardModelCord(restLength: strand.restLength, radius: strand.radius,
                                  material: strand.material, provenance: strand.provenance)
        case .singleCord(let suspension): return suspension.cord
        case .pairedLeadCord(let suspension): return suspension.cord
        case .twoBranchCord(let suspension):
            guard let branch = suspension.branches.first else {
                preconditionFailure("twoBranchCord must have at least one branch")
            }
            return BoardModelCord(
                restLength: branch.restLength,
                radius: branch.radius,
                material: branch.material,
                provenance: branch.provenance
            )
        }
    }

    var canonicalPoses: [String: BoardModelCanonicalPose] {
        switch self {
        case .cadRoutedCord(let suspension): suspension.canonicalPoses
        case .singleCord(let suspension): suspension.canonicalPoses
        case .pairedLeadCord(let suspension): suspension.canonicalPoses
        case .twoBranchCord(let suspension): suspension.canonicalPoses
        }
    }
}

private extension BoardModelPassage {
    var asAttachment: BoardModelAttachment {
        BoardModelAttachment(nodeID: nodeID, pointInModel: entryPointInModel, provenance: provenance)
    }
}

struct BoardModelContactDescriptor: Hashable {
    let nodeIDs: [String]
    let facePlaneAABB: BoardModelFacePlaneAABB
    let center: [Double]
    /// The CAD-authored front-plane hold polygon (normalized [x, y] points).
    /// Empty when the source declared no outline, in which case the app falls
    /// back to the mesh region and `facePlaneAABB`.
    let outline: [[Double]]

    init(
        nodeIDs: [String],
        facePlaneAABB: BoardModelFacePlaneAABB,
        center: [Double],
        outline: [[Double]] = []
    ) {
        self.nodeIDs = nodeIDs
        self.facePlaneAABB = facePlaneAABB
        self.center = center
        self.outline = outline
    }
}

struct BoardModelDescriptor: Hashable {
    let schemaVersion: Int
    let coordinateFrame: String
    let modelSHA256: String
    let modelBounds: BoardModelBounds
    let nodes: [BoardModelNodeDescriptor]
    let contacts: [String: BoardModelContactDescriptor]
}

struct BoardModelCamera: Hashable {
    let type: String
    let viewDirection: [Double]
    let up: [Double]
    let fitPadding: Double
    let distanceMultiplier: Double?
    let boundsExpansionFactor: Double?
}

enum BoardSurfaceFinish: String, Hashable, Decodable {
    case neutral, wood, plastic, granite
}

struct BoardModelDisplay: Hashable {
    let camera: BoardModelCamera
    let surfaceFinish: BoardSurfaceFinish
    /// Package-authored surface selection; USDZ meshes remain material-free.
    let woodNodeIDs: [String]
    let plasticNodeIDs: [String]
    let graniteNodeIDs: [String]

    init(camera: BoardModelCamera, surfaceFinish: BoardSurfaceFinish = .neutral,
         woodNodeIDs: [String] = [], plasticNodeIDs: [String] = [], graniteNodeIDs: [String] = []) {
        self.camera = camera
        self.surfaceFinish = surfaceFinish
        self.woodNodeIDs = woodNodeIDs
        self.plasticNodeIDs = plasticNodeIDs
        self.graniteNodeIDs = graniteNodeIDs
    }
}

struct BoardModelOrientation: Hashable {
    /// Quaternions use the package's explicit `[x, y, z, w]` component order.
    let pivot: String
    let rotations: [String: SIMD4<Double>]
}

struct BoardModelTransform: Hashable {
    enum Reflection: String, Hashable {
        case x
    }

    let translation: [Double]
    let rotation: SIMD4<Double>
    let reflection: Reflection?
}

struct BoardModelInstance: Hashable {
    let equipmentObjectID: String
    let baseTransform: BoardModelTransform
    let contactIDsBySlotID: [String: String]
    let suspension: BoardModelSuspension?
    let positionTransforms: [String: BoardModelTransform]?
}

struct BoardModelMedia: Hashable {
    let assetPath: String
    let descriptorPath: String
    let descriptor: BoardModelDescriptor
    let display: BoardModelDisplay
    let suspension: BoardModelSuspension?
    let orientation: BoardModelOrientation?
    let instances: [BoardModelInstance]?
    let physicsDescriptorPath: String?

    init(
        assetPath: String,
        descriptorPath: String,
        descriptor: BoardModelDescriptor,
        display: BoardModelDisplay,
        suspension: BoardModelSuspension? = nil,
        orientation: BoardModelOrientation? = nil,
        instances: [BoardModelInstance]? = nil,
        physicsDescriptorPath: String? = nil
    ) {
        self.assetPath = assetPath
        self.descriptorPath = descriptorPath
        self.descriptor = descriptor
        self.display = display
        self.suspension = suspension
        self.orientation = orientation
        self.instances = instances
        self.physicsDescriptorPath = physicsDescriptorPath
    }
}

extension BoardModelMedia {
    /// Canonical slots remain model-local; map callers need the physical pair's frame.
    func resolvedContactFrame(_ contactID: String, presentationID: String) -> HoldFrame? {
        guard let contact = descriptor.contacts[contactID] else { return nil }
        guard let instances, !instances.isEmpty,
              instances.allSatisfy({ $0.suspension == nil }),
              let owner = instances.first(where: { $0.contactIDsBySlotID.values.contains(contactID) }) else {
            return contact.facePlaneAABB.contactFrame
        }
        let minimum = SIMD3<Double>(descriptor.modelBounds.minimum)
        let maximum = SIMD3<Double>(descriptor.modelBounds.maximum)
        let center = (minimum + maximum) / 2
        func apply(_ transform: BoardModelTransform, to point: SIMD3<Double>, pivot: SIMD3<Double>) -> SIMD3<Double> {
            var offset = point - pivot
            if transform.reflection == .x { offset.x = -offset.x }
            return simd_quatd(vector: transform.rotation).act(offset) + pivot
                + SIMD3<Double>(transform.translation)
        }
        func placed(_ point: SIMD3<Double>, instance: BoardModelInstance) -> SIMD3<Double> {
            let base = apply(instance.baseTransform, to: point, pivot: center)
            // Use this presentation's implicit position, or its first authored
            // canonical position (e.g. Pivot p1), for nominal map/resolver frames.
            let positionID = instance.positionTransforms?[presentationID] != nil
                ? presentationID : instance.positionTransforms?.keys.sorted().first
            guard let positionID, let pose = instance.positionTransforms?[positionID] else { return base }
            return apply(pose, to: base, pivot: center + SIMD3<Double>(instance.baseTransform.translation))
        }
        let boundsCorners = [minimum.x, maximum.x].flatMap { x in
            [minimum.y, maximum.y].flatMap { y in
                [minimum.z, maximum.z].map { SIMD3<Double>(x, y, $0) }
            }
        }
        let pairPoints = instances.flatMap { instance in boundsCorners.map { placed($0, instance: instance) } }
        let pairMinX = pairPoints.map(\.x).min()!, pairMaxX = pairPoints.map(\.x).max()!
        let pairMinY = pairPoints.map(\.y).min()!, pairMaxY = pairPoints.map(\.y).max()!
        let width = pairMaxX - pairMinX, height = pairMaxY - pairMinY
        guard width > 0, height > 0 else { return nil }
        let local = contact.facePlaneAABB
        let points = [local.minimum[0], local.maximum[0]].flatMap { x in
            [local.minimum[1], local.maximum[1]].map { y in
                placed(SIMD3(minimum.x + x * (maximum.x - minimum.x),
                             minimum.y + y * (maximum.y - minimum.y), center.z), instance: owner)
            }
        }
        let minX = points.map(\.x).min()!, maxX = points.map(\.x).max()!
        let minY = points.map(\.y).min()!, maxY = points.map(\.y).max()!
        return HoldFrame(
            x: boardDescriptorRoundedToNinePlaces((minX - pairMinX) / width),
            y: boardDescriptorRoundedToNinePlaces((minY - pairMinY) / height),
            width: boardDescriptorRoundedToNinePlaces((maxX - minX) / width),
            height: boardDescriptorRoundedToNinePlaces((maxY - minY) / height)
        )
    }
}

enum BoardPresentationMedia: Hashable {
    enum Kind: Hashable {
        case raster
        case model
    }

    case raster(BoardRasterMedia)
    case model(BoardModelMedia)

    var kind: Kind {
        switch self {
        case .raster: .raster
        case .model: .model
        }
    }

    var assetPath: String {
        switch self {
        case .raster(let media): media.assetPath
        case .model(let media): media.assetPath
        }
    }
}

/// The one path source used for normal contact, highlighting, and hit testing.
struct BoardContactPathShape: Shape {
    let pieces: [BoardContactPiece]

    func path(in rect: CGRect) -> Path {
        pieces.reduce(into: Path()) { path, piece in
            path.addPath(piece.path(in: rect))
        }
    }
}

enum BoardContactTreatment: Hashable {
    case recess(BoardRecessProfile)
    case shelf(BoardShelfProfile)
    case surface
}

struct BoardRecessProfile: Hashable {
    let rimInsetFraction: CGFloat
    let depth: BoardRecessDepth
}

enum BoardRecessDepth: Hashable {
    case deep
    case shallow
}

struct BoardShelfProfile: Hashable {
    let rimInsetFraction: CGFloat
}

enum BoardShape: Hashable {
    case roundedRect(cornerRadiusFraction: CGFloat)
    case path(BoardNormalizedPath)

    func path(in rect: CGRect) -> Path {
        switch self {
        case .roundedRect(let fraction):
            let radius = min(rect.width, rect.height) * fraction
            return Path(
                roundedRect: rect,
                cornerSize: CGSize(width: radius, height: radius)
            )
        case .path(let normalizedPath):
            return normalizedPath.path(in: rect)
        }
    }
}

struct BoardNormalizedPath: Hashable {
    let commands: [BoardPathCommand]

    func path(in rect: CGRect) -> Path {
        func point(_ normalized: CGPoint) -> CGPoint {
            CGPoint(
                x: rect.minX + rect.width * normalized.x,
                y: rect.minY + rect.height * normalized.y
            )
        }

        var result = Path()
        for command in commands {
            switch command {
            case .move(let destination):
                result.move(to: point(destination))
            case .line(let destination):
                result.addLine(to: point(destination))
            case let .quad(destination, control):
                result.addQuadCurve(to: point(destination), control: point(control))
            case let .curve(destination, control1, control2):
                result.addCurve(
                    to: point(destination),
                    control1: point(control1),
                    control2: point(control2)
                )
            case .close:
                result.closeSubpath()
            }
        }
        return result
    }
}

enum BoardPathCommand: Hashable {
    case move(CGPoint)
    case line(CGPoint)
    case quad(to: CGPoint, control: CGPoint)
    case curve(to: CGPoint, control1: CGPoint, control2: CGPoint)
    case close
}

enum HoldKind: String, CaseIterable, Codable, Hashable, Identifiable {
    case jug
    case edge
    case pocket
    case pinch
    case sloper
    case gaston

    var id: String { rawValue }

    var label: String {
        switch self {
        case .jug: "Jugs"
        case .edge: "Edges"
        case .pocket: "Pockets"
        case .pinch: "Pinches"
        case .sloper: "Sloper"
        case .gaston: "Gastons"
        }
    }

    var detailLabel: String {
        switch self {
        case .jug: "Jug"
        case .edge: "Edge"
        case .pocket: "Pocket"
        case .pinch: "Pinch"
        case .sloper: "Sloper"
        case .gaston: "Gaston"
        }
    }

    var tint: Color {
        switch self {
        case .jug: .holdBlue
        case .edge: .holdOrange
        case .pocket: .holdPurple
        case .pinch: .holdRed
        case .sloper: .holdTeal
        case .gaston: .holdGreen
        }
    }
}

enum HoldShape: String, Codable, Hashable, CaseIterable, Identifiable {
    case flat
    case round
    case incut
    case slot

    var id: String { rawValue }

    var label: String {
        switch self {
        case .flat: "Flat"
        case .round: "Round"
        case .incut: "Incut"
        case .slot: "Slot"
        }
    }
}

enum HoldSize: String, Codable, Hashable, CaseIterable, Identifiable {
    case tiny
    case small
    case medium
    case large

    var id: String { rawValue }

    var label: String {
        switch self {
        case .tiny: "Tiny"
        case .small: "Small"
        case .medium: "Medium"
        case .large: "Large"
        }
    }

    /// Community-convention depth range in millimeters for this size category.
    var depthRange: ClosedRange<Double> {
        switch self {
        case .tiny: 0...8
        case .small: 8...15
        case .medium: 15...25
        case .large: 25...50
        }
    }
}

struct MillimeterRange: Codable, Hashable {
    let minimum: Double
    let maximum: Double

    private enum CodingKeys: String, CodingKey, CaseIterable {
        case minimum, maximum
    }

    init(minimum: Double, maximum: Double) {
        precondition(Self.isValid(minimum: minimum, maximum: maximum))
        self.minimum = minimum
        self.maximum = maximum
    }

    init(from decoder: Decoder) throws {
        let rawContainer = try decoder.container(keyedBy: HoldDepthCodingKey.self)
        let allowedKeys = Set(CodingKeys.allCases.map(\.rawValue))
        let unsupportedKeys = rawContainer.allKeys
            .filter { !allowedKeys.contains($0.stringValue) }
            .sorted { $0.stringValue < $1.stringValue }
        if let unknownKey = unsupportedKeys.first {
            throw DecodingError.dataCorruptedError(
                forKey: unknownKey,
                in: rawContainer,
                debugDescription: "Unsupported millimeter range field \(unknownKey.stringValue)."
            )
        }

        let container = try decoder.container(keyedBy: CodingKeys.self)
        minimum = try container.decode(Double.self, forKey: .minimum)
        maximum = try container.decode(Double.self, forKey: .maximum)
        guard Self.isValid(minimum: minimum, maximum: maximum) else {
            throw DecodingError.dataCorruptedError(
                forKey: .maximum,
                in: container,
                debugDescription: "A millimeter range must be finite, non-negative, and ordered."
            )
        }
    }

    private static func isValid(minimum: Double, maximum: Double) -> Bool {
        minimum.isFinite && maximum.isFinite && minimum >= 0 && minimum <= maximum
    }
}

enum HoldDepth: Codable, Hashable {
    private static let numericMatchToleranceMillimeters = 1.0

    case category(HoldSize)
    case range(MillimeterRange)

    private enum CodingKeys: String, CodingKey, CaseIterable {
        case category, range
    }

    init(from decoder: Decoder) throws {
        let rawContainer = try decoder.container(keyedBy: HoldDepthCodingKey.self)
        let allowedKeys = Set(CodingKeys.allCases.map(\.rawValue))
        let unsupportedKeys = rawContainer.allKeys
            .filter { !allowedKeys.contains($0.stringValue) }
            .sorted { $0.stringValue < $1.stringValue }
        if let unknownKey = unsupportedKeys.first {
            throw DecodingError.dataCorruptedError(
                forKey: unknownKey,
                in: rawContainer,
                debugDescription: "Unsupported hold depth field \(unknownKey.stringValue)."
            )
        }

        let container = try decoder.container(keyedBy: CodingKeys.self)
        let hasCategory = container.contains(.category)
        let hasRange = container.contains(.range)
        guard hasCategory != hasRange else {
            throw DecodingError.dataCorruptedError(
                forKey: hasCategory ? .range : .category,
                in: container,
                debugDescription: "A hold depth must contain exactly one of category or range."
            )
        }
        if hasCategory {
            self = .category(try container.decode(HoldSize.self, forKey: .category))
        } else {
            self = .range(try container.decode(MillimeterRange.self, forKey: .range))
        }
    }

    func encode(to encoder: Encoder) throws {
        var container = encoder.container(keyedBy: CodingKeys.self)
        switch self {
        case let .category(size):
            try container.encode(size, forKey: .category)
        case let .range(range):
            try container.encode(range, forKey: .range)
        }
    }

    /// Whether a requirement represented by this depth has enough evidence to match a contact depth.
    func matches(_ contactDepth: HoldDepth?) -> Bool {
        guard let contactDepth else { return false }
        return switch (self, contactDepth) {
        case let (.category(required), .category(actual)):
            required == actual
        case let (.category(required), .range(actual)):
            required.depthRange.overlaps(actual.minimum...actual.maximum)
        case let (.range(required), .range(actual)):
            required.minimum <= actual.maximum + Self.numericMatchToleranceMillimeters
                && required.maximum + Self.numericMatchToleranceMillimeters >= actual.minimum
        case (.range, .category):
            false
        }
    }
}

private struct HoldDepthCodingKey: CodingKey {
    let stringValue: String
    let intValue: Int?

    init?(stringValue: String) {
        self.stringValue = stringValue
        intValue = nil
    }

    init?(intValue: Int) {
        stringValue = String(intValue)
        self.intValue = intValue
    }
}

enum ContactSide: String, Codable, Hashable {
    case left
    case right
}

enum SloperType: String, Codable, Hashable {
    case flat
    case round
}

struct SloperMetadata: Codable, Hashable {
    var type: SloperType
    var angleDegrees: Double?

    private enum CodingKeys: String, CodingKey {
        case type
        case angleDegrees
    }

    init(type: SloperType, angleDegrees: Double?) {
        self.type = type
        self.angleDegrees = angleDegrees
    }

    init(from decoder: Decoder) throws {
        let unknownKeys = try decoder.container(keyedBy: SloperAnyCodingKey.self).allKeys.filter {
            !["type", "angleDegrees"].contains($0.stringValue)
        }
        if let unknownKey = unknownKeys.first {
            throw DecodingError.dataCorrupted(
                DecodingError.Context(
                    codingPath: decoder.codingPath + [unknownKey],
                    debugDescription: "Unknown key \(unknownKey.stringValue)"
                )
            )
        }

        let container = try decoder.container(keyedBy: CodingKeys.self)
        type = try container.decode(SloperType.self, forKey: .type)
        angleDegrees = try container.decodeIfPresent(Double.self, forKey: .angleDegrees)
        guard isValid else {
            throw DecodingError.dataCorrupted(
                DecodingError.Context(
                    codingPath: decoder.codingPath,
                    debugDescription: "Sloper angle must be absent for round slopers or finite and in 0...90 for flat slopers."
                )
            )
        }
    }

    func encode(to encoder: Encoder) throws {
        guard isValid else {
            throw EncodingError.invalidValue(
                self,
                EncodingError.Context(
                    codingPath: encoder.codingPath,
                    debugDescription: "Sloper angle must be absent for round slopers or finite and in 0...90 for flat slopers."
                )
            )
        }
        var container = encoder.container(keyedBy: CodingKeys.self)
        try container.encode(type, forKey: .type)
        try container.encodeIfPresent(angleDegrees, forKey: .angleDegrees)
    }

    var isValid: Bool {
        switch (type, angleDegrees) {
        case (.round, nil), (.flat, nil):
            true
        case (.flat, let angle?):
            angle.isFinite && (0...90).contains(angle)
        case (.round, .some):
            false
        }
    }
}

private struct SloperAnyCodingKey: CodingKey {
    let stringValue: String
    let intValue: Int?

    init?(stringValue: String) {
        self.stringValue = stringValue
        self.intValue = nil
    }

    init?(intValue: Int) {
        self.stringValue = String(intValue)
        self.intValue = intValue
    }
}

enum HoldCueStyle: String, Codable, Hashable {
    case outerJug
    case slot
    case pinch
    case rounded
}

enum FingerSlot: String, CaseIterable, Codable, Hashable, Identifiable {
    case index
    case middle
    case ring
    case pinky

    var id: String { rawValue }

    var height: CGFloat {
        switch self {
        case .index: 46
        case .middle: 58
        case .ring: 53
        case .pinky: 40
        }
    }
}

struct FingerConfiguration: Codable, Hashable {
    let engagedFingers: Set<FingerSlot>

    init?(engagedFingers: Set<FingerSlot>) {
        guard !engagedFingers.isEmpty else { return nil }
        self.engagedFingers = engagedFingers
    }

    var count: Int { engagedFingers.count }

    var orderedFingers: [FingerSlot] {
        FingerSlot.allCases.filter(engagedFingers.contains)
    }

    private enum CodingKeys: String, CodingKey {
        case engagedFingers
    }

    init(from decoder: Decoder) throws {
        let container = try decoder.container(keyedBy: CodingKeys.self)
        let decodedFingers = try container.decode([FingerSlot].self, forKey: .engagedFingers)
        guard !decodedFingers.isEmpty else {
            throw DecodingError.dataCorruptedError(
                forKey: .engagedFingers,
                in: container,
                debugDescription: "Finger configuration must include at least one finger."
            )
        }
        guard Set(decodedFingers).count == decodedFingers.count else {
            throw DecodingError.dataCorruptedError(
                forKey: .engagedFingers,
                in: container,
                debugDescription: "Finger configuration cannot include duplicate fingers."
            )
        }
        guard let configuration = Self(engagedFingers: Set(decodedFingers)) else {
            throw DecodingError.dataCorruptedError(
                forKey: .engagedFingers,
                in: container,
                debugDescription: "Finger configuration must include at least one finger."
            )
        }
        self = configuration
    }

    func encode(to encoder: Encoder) throws {
        guard !engagedFingers.isEmpty else {
            let container = encoder.container(keyedBy: CodingKeys.self)
            throw EncodingError.invalidValue(
                engagedFingers,
                EncodingError.Context(
                    codingPath: container.codingPath + [CodingKeys.engagedFingers],
                    debugDescription: "Finger configuration must include at least one finger."
                )
            )
        }

        var container = encoder.container(keyedBy: CodingKeys.self)
        try container.encode(orderedFingers, forKey: .engagedFingers)
    }
}

enum GripType: String, CaseIterable, Codable, Hashable, Identifiable {
    case openHand
    case halfCrimp
    case fullCrimp
    case fourFingerPocket
    case threeFingerPocket
    case twoFingerPocket
    case sloper

    var id: String { rawValue }

    var label: String {
        switch self {
        case .openHand: "Open hand"
        case .halfCrimp: "Half crimp"
        case .fullCrimp: "Full crimp"
        case .fourFingerPocket: "Four-finger pocket"
        case .threeFingerPocket: "Three-finger pocket"
        case .twoFingerPocket: "Two-finger pocket"
        case .sloper: "Open-hand sloper"
        }
    }

    init(from decoder: Decoder) throws {
        let container = try decoder.singleValueContainer()
        let rawValue = try container.decode(String.self)
        guard let gripType = Self(rawValue: rawValue) else {
            throw DecodingError.dataCorruptedError(
                in: container,
                debugDescription: "Unknown grip posture: \(rawValue)."
            )
        }
        self = gripType
    }

    func encode(to encoder: Encoder) throws {
        var container = encoder.singleValueContainer()
        try container.encode(rawValue)
    }
}

struct EquipmentObject: Codable, Hashable, Identifiable {
    let id: String

    init(id: String) {
        self.id = id
    }
}

struct PhysicalContact: Identifiable, Hashable {
    let id: String
    let equipmentObjectID: String
    let name: String
    let kind: HoldKind
    let shape: HoldShape?
    let fingerCapacity: Int?
    let handCapacity: Int?
    let depth: HoldDepth?
    let gripTypes: Set<GripType>
    let side: ContactSide?
    let pairedContactID: String?

    static let validFingerCapacityRange = 1...4
    static let validHandCapacityRange = 1...2

    init(
        id: String,
        equipmentObjectID: String = "primary",
        name: String,
        kind: HoldKind,
        shape: HoldShape? = nil,
        fingerCapacity: Int? = nil,
        handCapacity: Int? = nil,
        depth: HoldDepth? = nil,
        gripTypes: Set<GripType> = [],
        side: ContactSide? = nil,
        pairedContactID: String? = nil
    ) {
        if let fingerCapacity {
            precondition(
                Self.validFingerCapacityRange.contains(fingerCapacity),
                "PhysicalContact fingerCapacity must be in \(Self.validFingerCapacityRange)."
            )
        }
        if let handCapacity {
            precondition(
                Self.validHandCapacityRange.contains(handCapacity),
                "PhysicalContact handCapacity must be in \(Self.validHandCapacityRange)."
            )
        }

        self.id = id
        self.equipmentObjectID = equipmentObjectID
        self.name = name
        self.kind = kind
        self.shape = shape
        self.fingerCapacity = fingerCapacity
        self.handCapacity = handCapacity
        self.depth = depth
        self.gripTypes = gripTypes
        self.side = side
        self.pairedContactID = pairedContactID
    }

    func resolvedFrame(in presentation: BoardPresentation) -> HoldFrame? {
        switch presentation.media {
        case .raster(let media):
            guard let pieces = media.contactGeometry[id],
                  let first = pieces.first else { return nil }
            let union = pieces.dropFirst().reduce(first.frame) { $0.union($1.frame) }
            return HoldFrame(
                x: union.minX,
                y: union.minY,
                width: boardDescriptorRoundedToNinePlaces(union.width),
                height: boardDescriptorRoundedToNinePlaces(union.height)
            )
        case .model(let media):
            return media.resolvedContactFrame(id, presentationID: presentation.id)
        }
    }
}

struct BoardPresentation: Identifiable, Hashable {
    static let primaryID = "primary"

    let id: String
    let name: String
    let aspectRatio: CGFloat
    let isDefault: Bool
    /// A presentation may show an existing physical surface in a different
    /// mounting orientation, without duplicating the board's hold inventory.
    let sourcePresentationID: String?
    let isInverted: Bool
    let media: BoardPresentationMedia

    init(
        id: String,
        name: String,
        aspectRatio: CGFloat,
        isDefault: Bool,
        sourcePresentationID: String? = nil,
        isInverted: Bool = false,
        media: BoardPresentationMedia = .raster(
            BoardRasterMedia(assetPath: "", contactGeometry: [:])
        )
    ) {
        self.id = id
        self.name = name
        self.aspectRatio = aspectRatio
        self.isDefault = isDefault
        self.sourcePresentationID = sourcePresentationID
        self.isInverted = isInverted
        self.media = media
    }

    var contactIDs: Set<String> {
        switch media {
        case .raster(let media): Set(media.contactGeometry.keys)
        case .model(let media): Set(media.descriptor.contacts.keys)
        }
    }

    func containsContact(id: String) -> Bool {
        contactIDs.contains(id)
    }
}

enum BoardPositionTransitionKind: String, Codable, Hashable {
    case seamless
    case setupRequired
    case unsupported
}

enum ResolvedBoardPositionTransitionKind: Hashable {
    case same
    case seamless
    case setupRequired
    case unsupported
}

struct BoardPosition: Identifiable, Codable, Hashable {
    let id: String
    let presentationID: String
    let contactIDs: [String]
    /// Retained internally so model packages can distinguish omitted membership
    /// (which materializes) from an authored empty array (invalid).
    let contactIDsWereExplicitlyAuthored: Bool
    let effectiveDepths: [String: HoldDepth]

    init(id: String, presentationID: String, contactIDs: [String], effectiveDepths: [String: HoldDepth] = [:]) {
        self.id = id
        self.presentationID = presentationID
        self.contactIDs = contactIDs
        self.contactIDsWereExplicitlyAuthored = true
        self.effectiveDepths = effectiveDepths
    }

    init(id: String, presentationID: String, effectiveDepths: [String: HoldDepth] = [:]) {
        self.id = id
        self.presentationID = presentationID
        self.contactIDs = []
        self.contactIDsWereExplicitlyAuthored = false
        self.effectiveDepths = effectiveDepths
    }

    private enum CodingKeys: String, CodingKey { case id, presentationID, contactIDs, effectiveDepths }

    init(from decoder: Decoder) throws {
        let container = try decoder.container(keyedBy: CodingKeys.self)
        id = try container.decode(String.self, forKey: .id)
        presentationID = try container.decode(String.self, forKey: .presentationID)
        contactIDsWereExplicitlyAuthored = container.contains(.contactIDs)
        contactIDs = contactIDsWereExplicitlyAuthored
            ? try container.decode([String].self, forKey: .contactIDs)
            : []
        effectiveDepths = try container.decodeIfPresent([String: HoldDepth].self, forKey: .effectiveDepths) ?? [:]
    }

    func encode(to encoder: Encoder) throws {
        var container = encoder.container(keyedBy: CodingKeys.self)
        try container.encode(id, forKey: .id)
        try container.encode(presentationID, forKey: .presentationID)
        if contactIDsWereExplicitlyAuthored {
            try container.encode(contactIDs, forKey: .contactIDs)
        }
        if !effectiveDepths.isEmpty { try container.encode(effectiveDepths, forKey: .effectiveDepths) }
    }
}

struct BoardPositionTransition: Codable, Hashable {
    let fromPositionID: String
    let toPositionID: String
    let kind: BoardPositionTransitionKind
}

/// Package-owned policy for mapping athlete hand choice onto neutral contacts.
/// This controls app resolution only and does not describe a physical board fact.
enum UnilateralHandResolution: String, Codable, Hashable {
    case athleteRelative
}

struct BoardRevision: Identifiable, Hashable {
    let id: String
    let revisionID: String
    let manufacturer: String
    let name: String
    let subtitle: String
    let dimensions: String?
    let aspectRatio: CGFloat
    /// Package-authored simultaneous hand capacity for the board (`1...2`).
    /// Omitted in `board.json` decodes as `2` (conventional two-handed).
    let handCapacity: Int
    let unilateralHandResolution: UnilateralHandResolution?
    let equipmentObjects: [EquipmentObject]
    let contacts: [PhysicalContact]
    let presentations: [BoardPresentation]
    let positions: [BoardPosition]
    let positionTransitions: [BoardPositionTransition]
    let productURL: URL
    /// Optional board-specific reference art. Boards without a photo use the
    /// vector fallback, so adding another board does not require an image.
    let photoAssetName: String?

    init(
        id: String,
        revisionID: String,
        manufacturer: String,
        name: String,
        subtitle: String,
        dimensions: String?,
        aspectRatio: CGFloat,
        handCapacity: Int = 2,
        unilateralHandResolution: UnilateralHandResolution? = nil,
        equipmentObjects: [EquipmentObject] = [.init(id: "primary")],
        contacts: [PhysicalContact],
        productURL: URL,
        photoAssetName: String?,
        presentations: [BoardPresentation] = [],
        positions: [BoardPosition]? = nil,
        positionTransitions: [BoardPositionTransition] = []
    ) {
        precondition(
            PhysicalContact.validHandCapacityRange.contains(handCapacity),
            "BoardRevision handCapacity must be in \(PhysicalContact.validHandCapacityRange)."
        )
        self.id = id
        self.revisionID = revisionID
        self.manufacturer = manufacturer
        self.name = name
        self.subtitle = subtitle
        self.dimensions = dimensions
        self.aspectRatio = aspectRatio
        self.handCapacity = handCapacity
        self.unilateralHandResolution = unilateralHandResolution
        self.equipmentObjects = equipmentObjects
        self.contacts = contacts
        let resolvedPresentations = presentations.isEmpty
            ? [
                BoardPresentation(
                    id: BoardPresentation.primaryID,
                    name: "Primary",
                    aspectRatio: aspectRatio,
                    isDefault: true
                )
            ]
            : presentations
        self.presentations = resolvedPresentations
        self.positions = positions ?? resolvedPresentations.map {
            BoardPosition(id: $0.id, presentationID: $0.id)
        }
        self.positionTransitions = positionTransitions
        self.productURL = productURL
        self.photoAssetName = photoAssetName
    }

    var defaultPresentation: BoardPresentation {
        presentations.first(where: \.isDefault) ?? presentations[0]
    }

    /// True when the package authors this board as one-handed (`handCapacity == 1`).
    /// Not inferred from contact inventory or spatial pairing.
    var isOneHanded: Bool {
        handCapacity == 1
    }

    func presentation(id: String?) -> BoardPresentation? {
        guard let id else { return nil }
        return presentations.first { $0.id == id }
    }

    /// Returns the authored position without silently substituting another
    /// position or presentation. This is the single position lookup used by
    /// model selection and hold-membership resolution.
    func position(id: String?) -> BoardPosition? {
        guard let id else { return nil }
        return positions.first { $0.id == id }
    }

    func position(presentationID: String, containingContactID contactID: String? = nil) -> BoardPosition? {
        positions.first { position in
            guard position.presentationID == presentationID else { return false }
            guard let contactID else { return true }
            return contactIDs(inPosition: position.id).contains(contactID)
        }
    }

    /// Physical contacts that have display-derived matching geometry in this
    /// exact presentation. A missing media mapping is unavailable, rather
    /// than a reason to borrow geometry from another presentation.
    func contacts(in presentation: BoardPresentation) -> [PhysicalContact] {
        contacts.filter { $0.resolvedFrame(in: presentation) != nil }
    }

    func contactIDs(inPosition positionID: String) -> [String] {
        guard let position = position(id: positionID),
              let presentation = presentation(id: position.presentationID) else {
            return []
        }
        let presentedIDs: Set<String>
        switch presentation.media {
        case .model: presentedIDs = Set(position.contactIDs)
        case .raster(let media): presentedIDs = Set(media.contactGeometry.keys)
        }
        return contacts.compactMap { presentedIDs.contains($0.id) ? $0.id : nil }
    }

    func contacts(inPosition positionID: String) -> [PhysicalContact] {
        guard let position = position(id: positionID) else { return [] }
        let identifiers = Set(contactIDs(inPosition: positionID))
        return contacts.filter { identifiers.contains($0.id) }.map { contact in
            guard let depth = position.effectiveDepths[contact.id] else { return contact }
            return PhysicalContact(id: contact.id, equipmentObjectID: contact.equipmentObjectID,
                                   name: contact.name, kind: contact.kind, shape: contact.shape,
                                   fingerCapacity: contact.fingerCapacity, handCapacity: contact.handCapacity,
                                   depth: depth, gripTypes: contact.gripTypes, side: contact.side,
                                   pairedContactID: contact.pairedContactID)
        }
    }

    func transitionKind(
        from fromPositionID: String,
        to toPositionID: String
    ) -> ResolvedBoardPositionTransitionKind {
        guard positions.contains(where: { $0.id == fromPositionID }),
              positions.contains(where: { $0.id == toPositionID }) else {
            return .unsupported
        }
        guard fromPositionID != toPositionID else { return .same }
        guard let transition = positionTransitions.first(where: {
            $0.fromPositionID == fromPositionID && $0.toPositionID == toPositionID
        }) else {
            return .setupRequired
        }
        switch transition.kind {
        case .seamless: return .seamless
        case .setupRequired: return .setupRequired
        case .unsupported: return .unsupported
        }
    }

    func object(id: String) -> EquipmentObject? {
        equipmentObjects.first { $0.id == id }
    }
}

enum WorkoutSegmentKind: String, Codable, Hashable {
    case work
    case rest
}

enum WorkoutSegmentTiming: String, CaseIterable, Codable, Hashable, Identifiable {
    case fixed
    case stopwatch
    case undefined

    var id: String { rawValue }

    var label: String {
        switch self {
        case .fixed: "Timed"
        case .stopwatch: "Stopwatch"
        case .undefined: "Unspecified"
        }
    }
}

/// Prescription for a work segment: athlete-chosen holds, or one or more
/// concrete contact requirements. Rest segments never carry a target.
enum WorkoutSegmentTarget: Codable, Hashable {
    case selfSelected
    case requirements([ContactRequirement])
    case tasks([[PlanHandTarget]])

    /// Maps a legacy empty-array self-selected prescription or a non-empty
    /// requirement list. Empty arrays become `.selfSelected`; callers that
    /// need a hard non-empty requirements value should use `nonEmptyRequirements(_:)`.
    static func fromLegacyTargets(_ targets: [ContactRequirement]) -> WorkoutSegmentTarget {
        targets.isEmpty ? .selfSelected : .requirements(targets)
    }

    /// Non-empty requirements only. Returns nil when `requirements` is empty.
    /// Named distinctly from the `.requirements` enum case to avoid overload ambiguity.
    static func nonEmptyRequirements(_ requirements: [ContactRequirement]) -> WorkoutSegmentTarget? {
        guard !requirements.isEmpty else { return nil }
        return .requirements(requirements)
    }

    var contactRequirements: [ContactRequirement] {
        switch self {
        case .selfSelected:
            []
        case .requirements(let requirements):
            requirements
        case .tasks(let tasks):
            tasks.flatMap { $0.map { $0.target?.legacyRequirement ?? ContactRequirement() } }
        }
    }

    var planTasks: [[PlanHandTarget]]? {
        if case .tasks(let tasks) = self { return tasks }
        return nil
    }

    var isSelfSelected: Bool {
        switch self {
        case .selfSelected: true
        case .requirements: false
        case .tasks(let tasks):
            !tasks.isEmpty && tasks.allSatisfy { task in
                task.allSatisfy { $0.target == nil }
            }
        }
    }

    private enum Kind: String, Codable {
        case selfSelected
        case requirements
    }

    private enum CodingKeys: String, CodingKey, CaseIterable {
        case kind
        case requirements
        case tasks
    }

    private struct DynamicCodingKey: CodingKey {
        var stringValue: String
        init?(stringValue: String) { self.stringValue = stringValue }
        var intValue: Int? { nil }
        init?(intValue: Int) { return nil }
    }

    init(from decoder: Decoder) throws {
        let rawContainer = try decoder.container(keyedBy: DynamicCodingKey.self)
        let allowedKeys = Set(CodingKeys.allCases.map(\.rawValue))
        if let unknownKey = rawContainer.allKeys.first(where: {
            !allowedKeys.contains($0.stringValue)
        }) {
            throw DecodingError.dataCorruptedError(
                forKey: unknownKey,
                in: rawContainer,
                debugDescription: "Unsupported workout segment target field \(unknownKey.stringValue)."
            )
        }

        let container = try decoder.container(keyedBy: CodingKeys.self)
        if container.contains(.tasks) {
            guard !container.contains(.kind), !container.contains(.requirements) else {
                throw DecodingError.dataCorruptedError(
                    forKey: .tasks, in: container,
                    debugDescription: "Task targets cannot contain legacy target fields."
                )
            }
            let tasks = try container.decode([[PlanHandTarget]].self, forKey: .tasks)
            guard !tasks.isEmpty, tasks.allSatisfy({ (1...2).contains($0.count) }) else {
                throw DecodingError.dataCorruptedError(
                    forKey: .tasks, in: container,
                    debugDescription: "Each task must contain one or two hand targets."
                )
            }
            self = .tasks(tasks)
            return
        }
        switch try container.decode(Kind.self, forKey: .kind) {
        case .selfSelected:
            guard !container.contains(.requirements) else {
                throw DecodingError.dataCorruptedError(
                    forKey: .requirements,
                    in: container,
                    debugDescription: "Self-selected segment targets cannot contain requirements."
                )
            }
            self = .selfSelected
        case .requirements:
            let requirements = try container.decode([ContactRequirement].self, forKey: .requirements)
            guard !requirements.isEmpty else {
                throw DecodingError.dataCorruptedError(
                    forKey: .requirements,
                    in: container,
                    debugDescription: "Segment requirement targets must be non-empty."
                )
            }
            self = .requirements(requirements)
        }
    }

    func encode(to encoder: Encoder) throws {
        var container = encoder.container(keyedBy: CodingKeys.self)
        switch self {
        case .selfSelected:
            try container.encode(Kind.selfSelected, forKey: .kind)
        case .requirements(let requirements):
            guard !requirements.isEmpty else {
                throw EncodingError.invalidValue(
                    requirements,
                    EncodingError.Context(
                        codingPath: container.codingPath + [CodingKeys.requirements],
                        debugDescription: "Segment requirement targets must be non-empty."
                    )
                )
            }
            try container.encode(Kind.requirements, forKey: .kind)
            try container.encode(requirements, forKey: .requirements)
        case .tasks(let tasks):
            guard !tasks.isEmpty, tasks.allSatisfy({ (1...2).contains($0.count) }) else {
                throw EncodingError.invalidValue(
                    tasks,
                    EncodingError.Context(
                        codingPath: container.codingPath + [CodingKeys.tasks],
                        debugDescription: "Each task must contain one or two hand targets."
                    )
                )
            }
            try container.encode(tasks, forKey: .tasks)
        }
    }
}

struct WorkoutSegment: Hashable {
    let kind: WorkoutSegmentKind
    /// Required for work; must be nil for rest.
    let target: WorkoutSegmentTarget?
    let timing: WorkoutSegmentTiming
    let duration: TimeInterval?

    init(
        kind: WorkoutSegmentKind,
        target: WorkoutSegmentTarget?,
        timing: WorkoutSegmentTiming,
        duration: TimeInterval?
    ) {
        self.kind = kind
        self.target = target
        self.timing = timing
        self.duration = duration
    }

    /// Convenience for work segments with an explicit target, or rest with nil.
    init(
        kind: WorkoutSegmentKind,
        timing: WorkoutSegmentTiming,
        duration: TimeInterval?,
        target: WorkoutSegmentTarget? = nil
    ) {
        self.init(kind: kind, target: target, timing: timing, duration: duration)
    }

    var contactRequirements: [ContactRequirement] {
        target?.contactRequirements ?? []
    }

    var isSelfSelected: Bool {
        target?.isSelfSelected == true
    }

    func mappingRequirements(_ transform: (ContactRequirement) -> ContactRequirement) -> WorkoutSegment {
        guard let target else {
            return self
        }
        switch target {
        case .selfSelected:
            return self
        case .requirements(let requirements):
            return WorkoutSegment(
                kind: kind,
                target: .fromLegacyTargets(requirements.map(transform)),
                timing: timing,
                duration: duration
            )
        case .tasks:
            return self
        }
    }
}

enum WorkoutPhase: String, CaseIterable, Codable, Hashable, Identifiable {
    case warmUp
    case hang
    case rest
    case pull
    case conditioning
    case coolDown

    var id: String { rawValue }

    var label: String {
        switch self {
        case .warmUp: "Warm up"
        case .hang: "Hang"
        case .rest: "Rest"
        case .pull: "Pull"
        case .conditioning: "Conditioning"
        case .coolDown: "Cool down"
        }
    }

    var tint: Color {
        switch self {
        case .warmUp: .warmUp
        case .hang: .hangGreen
        case .rest: .restBlue
        case .pull: .pullOrange
        case .conditioning: .pullOrange
        case .coolDown: .coolDownPurple
        }
    }

    /// Dark companion colors keep phase text readable on cream while `tint`
    /// remains available for fills, progress, and other non-text accents.
    var textTint: Color {
        switch self {
        case .warmUp: Color(red: 0.45, green: 0.25, blue: 0.06)
        case .hang: .hangGreenDark
        case .rest: Color(red: 0.18, green: 0.34, blue: 0.52)
        case .pull: Color(red: 0.55, green: 0.20, blue: 0.08)
        case .conditioning: Color(red: 0.44, green: 0.22, blue: 0.10)
        case .coolDown: Color(red: 0.34, green: 0.22, blue: 0.48)
        }
    }
}

enum WorkoutHandUse: String, Codable, CaseIterable, Hashable {
    /// The prescription can be performed with one hand, selected when the
    /// session begins. Definitions retain `.both` until that selection is
    /// resolved for recording.
    case either
    case single
    case double
}

enum WorkoutSide: String, Codable, CaseIterable, Hashable {
    case left
    case right
    case both
}

/// Athlete start-of-session hand preference. Does not add `WorkoutHandUse` cases;
/// it only drives materialization / alternate expansion before the session runs.
enum WorkoutSessionHandPreference: Equatable {
    case left
    case right
    case alternate
    case both

    /// Left/right map to a concrete side for gradual migration; alternate and both
    /// require the dedicated session-step path instead.
    var selectedHandSide: WorkoutSide? {
        switch self {
        case .left: return .left
        case .right: return .right
        case .alternate, .both: return nil
        }
    }
}

extension WorkoutSessionHandPreference {
    /// Start-of-session default derived from the selected board's hand capacity.
    /// A board that fits one hand at a time defaults to alternating sides; a
    /// board that fits both hands defaults to a simultaneous both-hands set.
    static func defaultPreference(boardHandCapacity: Int) -> WorkoutSessionHandPreference {
        boardHandCapacity <= 1 ? .alternate : .both
    }
}

/// User-facing wording for the start-of-session hand choice. Only a one-handed
/// board ever asks the athlete to set up two boards.
enum HandChoiceCopy {
    static func bothHandsTitle(boardIsOneHanded: Bool) -> String {
        boardIsOneHanded ? "Both hands (two boards)" : "Both hands"
    }

    static func bothHandsHint(boardIsOneHanded: Bool) -> String {
        boardIsOneHanded
            ? "Both hands simultaneously on two boards."
            : "Both hands simultaneously on this board."
    }
}

enum WorkoutAction: String, Codable, CaseIterable, Hashable {
    case hang
    case isometricPull
    case loadedLift
}

enum WorkoutStepSemantics {
    static func hasValidHandUseAndSide(_ handUse: WorkoutHandUse, _ side: WorkoutSide) -> Bool {
        switch handUse {
        case .single:
            side == .left || side == .right
        case .double:
            side == .both
        case .either:
            side == .both
        }
    }

    static func hasValidHandUse(
        _ handUse: WorkoutHandUse,
        phase: WorkoutPhase,
        action: WorkoutAction
    ) -> Bool {
        handUse != .either || (
            phase != .rest &&
                phase != .pull &&
                action != .isometricPull
        )
    }

    static func hasValidActionAndRepetitions(_ action: WorkoutAction, _ repetitions: Int?) -> Bool {
        switch action {
        case .loadedLift:
            guard let repetitions else { return false }
            return repetitions > 0
        case .hang, .isometricPull:
            return repetitions == nil
        }
    }

    static func hasValidExternalLoad(_ externalLoadKGF: Double?) -> Bool {
        externalLoadKGF?.isFinite ?? true
    }
}

struct WorkoutStep: Identifiable, Hashable {
    let id: String
    let number: Int
    let title: String
    let instruction: String
    let accessory: String
    let duration: TimeInterval
    let phase: WorkoutPhase
    let segments: [WorkoutSegment]
    let gripType: GripType?
    let fingerConfiguration: FingerConfiguration?
    let handUse: WorkoutHandUse
    let side: WorkoutSide
    let action: WorkoutAction
    let repetitions: Int?
    let externalLoadKGF: Double?
    /// When set, the app splits the minute into timed work and timed rest.
    /// Manufacturer task cycles leave this nil because the athlete completes
    /// the listed reps/hangs, then rests for whatever remains in the minute.
    let timedWorkDuration: TimeInterval?

    init(
        id: String,
        number: Int,
        title: String,
        instruction: String,
        accessory: String,
        duration: TimeInterval,
        phase: WorkoutPhase,
        segments: [WorkoutSegment] = [],
        gripType: GripType? = nil,
        fingerConfiguration: FingerConfiguration? = nil,
        handUse: WorkoutHandUse = .double,
        side: WorkoutSide = .both,
        action: WorkoutAction = .hang,
        repetitions: Int? = nil,
        externalLoadKGF: Double? = nil,
        timedWorkDuration: TimeInterval? = nil
    ) {
        self.id = id
        self.number = number
        self.title = title
        self.instruction = instruction
        self.accessory = accessory
        self.duration = duration
        self.phase = phase
        self.segments = segments
        self.gripType = gripType
        self.fingerConfiguration = fingerConfiguration
        self.handUse = handUse
        self.side = side
        self.action = action
        self.repetitions = repetitions
        self.externalLoadKGF = externalLoadKGF
        self.timedWorkDuration = timedWorkDuration
    }

    /// Contact requirements prescribed by work segments. Self-selected work
    /// contributes nothing; rest segments are ignored.
    var workRequirements: [ContactRequirement] {
        segments.flatMap(\.contactRequirements)
    }

    /// True when every work segment is self-selected (or there is no work
    /// segment carrying requirements).
    var isSelfSelectedWork: Bool {
        let workTargets = segments.compactMap { segment -> WorkoutSegmentTarget? in
            guard segment.kind == .work else { return nil }
            return segment.target
        }
        return !workTargets.isEmpty && workTargets.allSatisfy(\.isSelfSelected)
    }

    var activeDuration: TimeInterval {
        return min(timedWorkDuration ?? duration, duration)
    }

    var isRestStep: Bool {
        phase == .rest
    }

    var hasRestInterval: Bool {
        duration > activeDuration
    }

    var durationLabel: String {
        let seconds = Int(duration)
        let minutes = seconds / 60
        let remainder = seconds % 60

        if minutes > 0 && remainder > 0 {
            return "\(minutes)m \(remainder)s"
        }
        if minutes > 0 {
            return "\(minutes)m"
        }
        return "\(remainder)s"
    }

    var restDuration: TimeInterval {
        max(0, duration - activeDuration)
    }

    func withNumber(_ number: Int) -> WorkoutStep {
        WorkoutStep(
            id: id,
            number: number,
            title: title,
            instruction: instruction,
            accessory: accessory,
            duration: duration,
            phase: phase,
            segments: segments,
            gripType: gripType,
            fingerConfiguration: fingerConfiguration,
            handUse: handUse,
            side: side,
            action: action,
            repetitions: repetitions,
            externalLoadKGF: externalLoadKGF,
            timedWorkDuration: timedWorkDuration
        )
    }

    /// Materializes an athlete's start-of-session hand choice for downstream
    /// board resolution, highlighting, and activity recording.
    ///
    /// `boardIsOneHanded` forces this resolution for `.double` steps too:
    /// a board where every contact only fits one hand can never actually
    /// perform a bilateral prescription, regardless of how the step was
    /// authored.
    func resolvingEitherHand(selectedHandSide: WorkoutSide?, boardIsOneHanded: Bool = false) -> WorkoutStep? {
        guard handUse == .either || (handUse == .double && boardIsOneHanded) else { return self }
        guard let side = selectedHandSide, side == .left || side == .right else {
            return nil
        }
        let singleHandedSegments = segments.map { segment in
            segment.mappingRequirements(\.singleHandSelection)
        }
        return WorkoutStep(
            id: id, number: number, title: title, instruction: instruction,
            accessory: accessory, duration: duration, phase: phase,
            segments: singleHandedSegments, gripType: gripType,
            fingerConfiguration: fingerConfiguration, handUse: .single,
            side: side, action: action, repetitions: repetitions,
            externalLoadKGF: externalLoadKGF, timedWorkDuration: timedWorkDuration
        )
    }
}

enum RoutineProvenance: String, Codable, Hashable {
    case official
    case adapted
    case custom

    var label: String {
        switch self {
        case .official: "Official"
        case .adapted: "Adapted"
        case .custom: "Custom"
        }
    }

}

struct TrainingPlan: Identifiable, Hashable {
    let id: String
    let title: String
    let subtitle: String
    let level: String
    let sourceLabel: String
    let sourceURL: URL?
    let provenance: RoutineProvenance
    let boardID: String?
    let steps: [WorkoutStep]
    var isFreeWorkout: Bool = false

    var duration: TimeInterval {
        steps.reduce(0) { $0 + $1.duration }
    }

    var durationLabel: String {
        let minutes = Int(duration) / 60
        let seconds = Int(duration) % 60
        if seconds == 0 {
            return "\(minutes) min"
        }
        return "\(minutes)m \(seconds)s"
    }
}

/// Athlete-selected edge size for the adapted López MAW session. The bundled
/// plan retains a semantic range; the session narrows it without changing the
/// catalog or recording a different hold from the one shown in the preview.
enum MaxHangsEdgeSelection {
    /// Resolve each eligible edge once so plan views can retain these snapshots.
    static func resolvedPlans(for plan: TrainingPlan, on board: BoardRevision) -> [Double: TrainingPlan] {
        guard plan.id == "research.max-hangs" else { return [:] }
        let depths = Set(board.contacts.compactMap { contact -> Double? in
            guard contact.kind == .edge,
                  case .range(let depth) = contact.depth,
                  depth.minimum == depth.maximum,
                  (8...20).contains(depth.minimum) else { return nil }
            return depth.minimum
        })
        return depths.reduce(into: [:]) { resolved, depth in
            resolved[depth] = selecting(depth, in: plan, on: board)
        }
    }

    static func availableDepths(for plan: TrainingPlan, on board: BoardRevision) -> [Double] {
        resolvedPlans(for: plan, on: board).keys.sorted(by: >)
    }

    static func selecting(_ depth: Double, in plan: TrainingPlan, on board: BoardRevision) -> TrainingPlan? {
        guard plan.id == "research.max-hangs", depth.isFinite, (8...20).contains(depth) else { return nil }
        let predicate = PlanContactPredicate(kind: .edge, depth: .measured(.init(minimum: depth, maximum: depth)))
        let target = WorkoutSegmentTarget.tasks([[PlanHandTarget(target: predicate), PlanHandTarget(target: predicate)]])
        let steps = plan.steps.map { step in
            WorkoutStep(
                id: step.id, number: step.number, title: step.title,
                instruction: step.instruction, accessory: step.accessory,
                duration: step.duration, phase: step.phase,
                segments: step.segments.map { segment in
                    guard segment.kind == .work else { return segment }
                    return WorkoutSegment(kind: .work, target: target, timing: segment.timing, duration: segment.duration)
                },
                gripType: step.gripType, fingerConfiguration: step.fingerConfiguration,
                handUse: step.handUse, side: step.side, action: step.action,
                repetitions: step.repetitions, externalLoadKGF: step.externalLoadKGF,
                timedWorkDuration: step.timedWorkDuration
            )
        }
        // Numeric matching has a tolerance. Offer a size only when its resolved
        // physical contacts actually have that exact measured point depth.
        guard steps.filter({ !$0.isRestStep }).allSatisfy({ step in
            guard let contacts = try? ContactResolver.resolve(target, step: step, board: board).first,
                  contacts.count == 2 else { return false }
            return contacts.allSatisfy { $0.depth == .range(.init(minimum: depth, maximum: depth)) }
        }) else { return nil }
        return TrainingPlan(
            id: plan.id, title: plan.title, subtitle: plan.subtitle, level: plan.level,
            sourceLabel: plan.sourceLabel, sourceURL: plan.sourceURL,
            provenance: plan.provenance, boardID: plan.boardID, steps: steps
        )
    }
}

enum BoardCatalog {

    static let packageStore: BoardPackageStore = {
        do {
            return try BoardPackageStore(modelAssetMode: .onDemand)
        } catch {
            fatalError("Bundled board packages could not be loaded: \(error.localizedDescription)")
        }
    }()

    static let all = packageStore.boards

    /// The initial catalog selection remains stable while plan requirements
    /// resolve independently against whichever board the athlete selects.
    static let defaultBoard: BoardRevision = {
        let boardID = "metolius.wood-grips-compact-ii"
        guard let board = packageStore.board(id: boardID) else {
            fatalError("The bundled board catalog is missing the default board '\(boardID)'.")
        }
        return board
    }()

    static func board(for id: String?) -> BoardRevision {
        guard let id else { return defaultBoard }
        return packageStore.board(id: id) ?? defaultBoard
    }

}
