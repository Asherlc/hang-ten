import Foundation
import SwiftUI

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

struct BoardModelNodeDescriptor: Hashable {
    enum Role: String, Hashable {
        case body
        case contact
        case attachment
    }

    let nodeID: String
    let role: Role
    let contactID: String?
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
    let translation: [Double]
    let camera: BoardModelCanonicalCamera
    // Visible exterior endpoints in this pose; clipped display endpoints do
    // not establish additional physical mouths or an inferred interior route.
    var attachmentPoints: [String: [Double]]? = nil
    // Ordered exterior contact points keyed by paired-lead attachment ID or
    // two-branch passage ID. Passage overrides never change the actual bore.
    var cordContactPoints: [String: [[Double]]]? = nil
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

struct BoardModelTwoBranchSuspension: Hashable {
    let passages: BoardModelPassagePairs
    let branches: [BoardModelCordBranch]
    let anchor: BoardModelInvisibleAnchor
    let canonicalPoses: [String: BoardModelCanonicalPose]
}

enum BoardModelSuspension: Hashable {
    case singleCord(BoardModelSingleCordSuspension)
    case pairedLeadCord(BoardModelPairedLeadCord)
    case twoBranchCord(BoardModelTwoBranchSuspension)

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
        case .singleCord(let suspension): suspension.anchor
        case .pairedLeadCord(let suspension): suspension.anchor
        case .twoBranchCord(let suspension): suspension.anchor
        }
    }

    var cord: BoardModelCord {
        switch self {
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
}

struct BoardModelDisplay: Hashable {
    let camera: BoardModelCamera
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

    init(
        assetPath: String,
        descriptorPath: String,
        descriptor: BoardModelDescriptor,
        display: BoardModelDisplay,
        suspension: BoardModelSuspension? = nil,
        orientation: BoardModelOrientation? = nil,
        instances: [BoardModelInstance]? = nil
    ) {
        self.assetPath = assetPath
        self.descriptorPath = descriptorPath
        self.descriptor = descriptor
        self.display = display
        self.suspension = suspension
        self.orientation = orientation
        self.instances = instances
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
            required.minimum <= actual.maximum && required.maximum >= actual.minimum
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
            return media.descriptor.contacts[id]?.facePlaneAABB.contactFrame
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

    init(id: String, presentationID: String, contactIDs: [String]) {
        self.id = id
        self.presentationID = presentationID
        self.contactIDs = contactIDs
        self.contactIDsWereExplicitlyAuthored = true
    }

    init(id: String, presentationID: String) {
        self.id = id
        self.presentationID = presentationID
        self.contactIDs = []
        self.contactIDsWereExplicitlyAuthored = false
    }

    private enum CodingKeys: String, CodingKey { case id, presentationID, contactIDs }

    init(from decoder: Decoder) throws {
        let container = try decoder.container(keyedBy: CodingKeys.self)
        id = try container.decode(String.self, forKey: .id)
        presentationID = try container.decode(String.self, forKey: .presentationID)
        contactIDsWereExplicitlyAuthored = container.contains(.contactIDs)
        contactIDs = contactIDsWereExplicitlyAuthored
            ? try container.decode([String].self, forKey: .contactIDs)
            : []
    }

    func encode(to encoder: Encoder) throws {
        var container = encoder.container(keyedBy: CodingKeys.self)
        try container.encode(id, forKey: .id)
        try container.encode(presentationID, forKey: .presentationID)
        if contactIDsWereExplicitlyAuthored {
            try container.encode(contactIDs, forKey: .contactIDs)
        }
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
        }
    }

    var isSelfSelected: Bool {
        if case .selfSelected = self { return true }
        return false
    }

    private enum Kind: String, Codable {
        case selfSelected
        case requirements
    }

    private enum CodingKeys: String, CodingKey, CaseIterable {
        case kind
        case requirements
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

struct MetoliusTaskDefinition: Hashable {
    let title: String
    let instruction: String
    let accessory: String
    let duration: TimeInterval
    let phase: WorkoutPhase
    let targets: [ContactRequirement]
    let gripType: GripType?
    let fingerConfiguration: FingerConfiguration?
    let timing: WorkoutSegmentTiming

    init(
        title: String,
        instruction: String,
        accessory: String,
        duration: TimeInterval,
        phase: WorkoutPhase,
        targets: [ContactRequirement],
        gripType: GripType? = nil,
        fingerConfiguration: FingerConfiguration? = nil,
        timing: WorkoutSegmentTiming = .fixed
    ) {
        self.title = title
        self.instruction = instruction
        self.accessory = accessory
        self.duration = duration
        self.phase = phase
        self.targets = targets
        self.gripType = gripType
        self.fingerConfiguration = fingerConfiguration
        self.timing = timing
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

enum MetoliusCycleBuilder {
    static let cycleDuration: TimeInterval = 60
    static let pullUpDuration: TimeInterval = 5
    static let repetitionDuration: TimeInterval = 1

    enum Error: Swift.Error, Equatable, LocalizedError {
        case overfullCycle(total: TimeInterval, cycleDuration: TimeInterval)

        var errorDescription: String? {
            switch self {
            case let .overfullCycle(total, cycleDuration):
                "Metolius minute totals \(Int(total)) seconds, exceeding its \(Int(cycleDuration))-second cycle."
            }
        }
    }

    private static func fixedRest(_ duration: TimeInterval) -> WorkoutSegment {
        WorkoutSegment(kind: .rest, target: nil, timing: .fixed, duration: duration)
    }

    static func pullUps(
        count: Int,
        title: String,
        instruction: String,
        phase: WorkoutPhase,
        targets: [ContactRequirement],
        gripType: GripType? = nil,
        fingerConfiguration: FingerConfiguration? = nil
    ) -> MetoliusTaskDefinition {
        task(
            title: title,
            instruction: instruction,
            accessory: count == 1 ? "1 pull-up" : "\(count) pull-ups",
            duration: TimeInterval(count) * pullUpDuration,
            phase: phase,
            targets: targets,
            gripType: gripType,
            fingerConfiguration: fingerConfiguration
        )
    }

    static func repetitions(
        count: Int,
        title: String,
        instruction: String,
        phase: WorkoutPhase,
        targets: [ContactRequirement],
        gripType: GripType? = nil,
        fingerConfiguration: FingerConfiguration? = nil
    ) -> MetoliusTaskDefinition {
        task(
            title: title,
            instruction: instruction,
            accessory: count == 1 ? "1 rep" : "\(count) reps",
            duration: TimeInterval(count) * repetitionDuration,
            phase: phase,
            targets: targets,
            gripType: gripType,
            fingerConfiguration: fingerConfiguration
        )
    }

    static func fixed(
        title: String,
        instruction: String,
        duration: TimeInterval,
        phase: WorkoutPhase,
        targets: [ContactRequirement],
        gripType: GripType? = nil,
        fingerConfiguration: FingerConfiguration? = nil
    ) -> MetoliusTaskDefinition {
        task(
            title: title,
            instruction: instruction,
            accessory: "\(Int(duration))s \(phase.label.lowercased())",
            duration: duration,
            phase: phase,
            targets: targets,
            gripType: gripType,
            fingerConfiguration: fingerConfiguration
        )
    }

    static func choice(
        title: String,
        instruction: String,
        accessory: String,
        duration: TimeInterval,
        phase: WorkoutPhase,
        targets: [ContactRequirement],
        gripType: GripType? = nil,
        fingerConfiguration: FingerConfiguration? = nil
    ) -> MetoliusTaskDefinition {
        task(
            title: title,
            instruction: instruction,
            accessory: accessory,
            duration: duration,
            phase: phase,
            targets: targets,
            gripType: gripType,
            fingerConfiguration: fingerConfiguration,
            timing: .undefined
        )
    }

    static func maxEffort(
        title: String,
        instruction: String,
        phase: WorkoutPhase,
        targets: [ContactRequirement],
        gripType: GripType? = nil,
        fingerConfiguration: FingerConfiguration? = nil
    ) -> MetoliusTaskDefinition {
        task(
            title: title,
            instruction: instruction,
            accessory: "Maximum effort",
            duration: cycleDuration,
            phase: phase,
            targets: targets,
            gripType: gripType,
            fingerConfiguration: fingerConfiguration,
            timing: .stopwatch
        )
    }

    static func expand(
        planID: String,
        minute: Int,
        tasks: [MetoliusTaskDefinition]
    ) throws -> [WorkoutStep] {
        let total = tasks.reduce(0) { $0 + $1.duration }
        guard total <= cycleDuration else {
            throw Error.overfullCycle(total: total, cycleDuration: cycleDuration)
        }

        var steps = tasks.enumerated().map { index, task in
            WorkoutStep(
                id: "\(planID).minute-\(minute).task-\(index + 1)",
                number: index + 1,
                title: task.title,
                instruction: task.instruction,
                accessory: task.accessory,
                duration: task.duration,
                phase: task.phase,
                segments: [
                    WorkoutSegment(
                        kind: .work,
                        target: .fromLegacyTargets(task.targets),
                        timing: task.timing,
                        duration: task.timing == .fixed ? task.duration : nil
                    )
                ],
                gripType: task.gripType,
                fingerConfiguration: task.fingerConfiguration,
                timedWorkDuration: task.timing == .fixed ? task.duration : nil
            )
        }

        let remaining = cycleDuration - total
        if remaining > 0 {
            steps.append(
                WorkoutStep(
                    id: "\(planID).minute-\(minute).rest",
                    number: tasks.count + 1,
                    title: "Minute \(minute) rest",
                    instruction: "Rest for the remainder of the minute.",
            accessory: "\(Int(remaining))s rest",
                    duration: remaining,
                    phase: .rest,
                    segments: [fixedRest(remaining)]
                )
            )
        }

        return steps
    }

    private static func task(
        title: String,
        instruction: String,
        accessory: String,
        duration: TimeInterval,
        phase: WorkoutPhase,
        targets: [ContactRequirement],
        gripType: GripType?,
        fingerConfiguration: FingerConfiguration?,
        timing: WorkoutSegmentTiming = .fixed
    ) -> MetoliusTaskDefinition {
        MetoliusTaskDefinition(
            title: title,
            instruction: instruction,
            accessory: accessory,
            duration: duration,
            phase: phase,
            targets: targets,
            gripType: gripType,
            fingerConfiguration: fingerConfiguration,
            timing: timing
        )
    }
}

/// Source-audited factual requirements for Metolius's numbered routines.
/// The plan guide and official numbered/depth diagrams establish every field.
enum BundledPlanContactRequirements {
    static let metoliusContactBoardID = "metolius.contact"
    static let metoliusSimulator3DBoardID = "metolius.simulator-3d"

    enum MetoliusContactTarget {
        case anyHold
        case outerJugs
        case pinches
        case flatSloper
        case roundSlopers
        case edge16
        case edge17
        case edge18
        case pocket4
        case pocket6
        case pocket7
        case pocket8
        case pocket9
        case pocket11
        case pocket13

        fileprivate var requirement: ContactRequirement {
            switch self {
            case .anyHold:
                ContactRequirement(selection: .single)
            case .outerJugs:
                .kind(.jug, selection: .bilateralPair)
            case .pinches:
                .kind(.pinch, selection: .single)
            case .flatSloper:
                ContactRequirement(kind: .sloper, shape: .flat, selection: .single)
            case .roundSlopers:
                ContactRequirement(kind: .sloper, shape: .round, selection: .single)
            case .edge16:
                .edge(depth: .range(.init(minimum: 15, maximum: 15)), selection: .single)
            case .edge17:
                .edge(depth: .range(.init(minimum: 35, maximum: 35)), selection: .single)
            case .edge18:
                .edge(depth: .range(.init(minimum: 28, maximum: 28)), selection: .single)
            case .pocket4:
                pocket(fingers: 4, depth: 30)
            case .pocket6:
                pocket(fingers: 3, depth: 20)
            case .pocket7:
                pocket(fingers: 3, depth: 30)
            case .pocket8:
                pocket(fingers: 2, depth: 32)
            case .pocket9:
                pocket(fingers: 4, depth: 20)
            case .pocket11:
                pocket(fingers: 2, depth: 25)
            case .pocket13:
                pocket(fingers: 3, depth: 17)
            }
        }

        private func pocket(fingers: Int, depth: Double) -> ContactRequirement {
            ContactRequirement(
                kind: .pocket,
                depth: .range(.init(minimum: depth, maximum: depth)),
                fingerCapacity: fingers,
                selection: .single
            )
        }
    }

    enum MetoliusSimulator3DTarget {
        case anyHold
        case outerJugs
        case centerJug
        case flatSlopers
        case roundSlopers
        case edge5
        case edge6
        case edge7
        case edge11
        case pocket4
        case pocket8
        case pocket9
        case pocket12
        case pocket15
        case pocket17
        case pocket18

        fileprivate var requirement: ContactRequirement? {
            switch self {
            case .anyHold:
                ContactRequirement(selection: .single)
            case .outerJugs:
                .kind(.jug, selection: .bilateralPair)
            case .centerJug:
                .kind(.jug, selection: .single)
            case .flatSlopers:
                ContactRequirement(kind: .sloper, shape: .flat, selection: .bilateralPair)
            case .roundSlopers:
                ContactRequirement(kind: .sloper, shape: .round, selection: .single)
            case .edge5:
                edge(depth: 25)
            case .edge6:
                edge(depth: 19)
            case .edge7:
                edge(depth: 36)
            case .edge11:
                edge(depth: 14)
            case .pocket4:
                pocket(fingers: 3, depth: 30, selection: .single)
            case .pocket8:
                pocket(fingers: 3, depth: 15, selection: .single)
            case .pocket9:
                pocket(fingers: 3, depth: 35, selection: .single)
            case .pocket12:
                pocket(fingers: 2, depth: 30, selection: .single)
            case .pocket15:
                pocket(fingers: 3, depth: 50, selection: .single)
            case .pocket17:
                pocket(fingers: 2, depth: 28, selection: .single)
            case .pocket18:
                pocket(fingers: 2, depth: 32, selection: .single)
            }
        }

        private func edge(depth: Double) -> ContactRequirement {
            .edge(
                depth: .range(.init(minimum: depth, maximum: depth)),
                selection: .single
            )
        }

        private func pocket(
            fingers: Int,
            depth: Double,
            selection: ContactSelectionPolicy
        ) -> ContactRequirement {
            ContactRequirement(
                kind: .pocket,
                depth: .range(.init(minimum: depth, maximum: depth)),
                fingerCapacity: fingers,
                selection: selection
            )
        }
    }

    static func contactTargets(_ groups: MetoliusContactTarget...) -> [ContactRequirement] {
        groups.map(\.requirement)
    }

    static func simulator3DTargets(_ groups: MetoliusSimulator3DTarget...) -> [ContactRequirement] {
        groups.compactMap(\.requirement)
    }

    static let metoliusRockRingBoardID = "metolius.rock-rings-3d"

    enum MetoliusRockRingTarget {
        case jugs
        case fourFingerEdges
        case threeFingerPockets
        case twoFingerPockets

        fileprivate var requirement: ContactRequirement {
            switch self {
            case .jugs:
                .kind(.jug, selection: .single)
            case .fourFingerEdges:
                ContactRequirement(kind: .pocket, fingerCapacity: 4, selection: .single)
            case .threeFingerPockets:
                ContactRequirement(kind: .pocket, fingerCapacity: 3, selection: .single)
            case .twoFingerPockets:
                ContactRequirement(kind: .pocket, fingerCapacity: 2, selection: .single)
            }
        }
    }

    static func rockRingTargets(_ groups: MetoliusRockRingTarget...) -> [ContactRequirement] {
        groups.map(\.requirement)
    }
}

enum LegacyPlanSeedCatalog {
    static let repeaterStepIDPrefix = "repeaters-grip-"

    private static let sourceURL = URL(
        string: "https://www.metoliusclimbing.com/pages/10-minute-sequences-hangboard-training-guide"
    )!

    private static let sourceLabel = "Metolius 10 Minute Sequences — Hangboard Training Guide"

    private static let adaptationNote = "Ten 60-second hangboard sequences."

    // Semantic terms explicitly named by Metolius's 10 Minute Sequences
    // guide. These requirements intentionally contain no board contact IDs or
    // references: the resolver selects factual contacts from the board.
    private static let roundSloperTarget = ContactRequirement(
        kind: .sloper,
        shape: .round
    )
    private static let mediumEdgeTarget = ContactRequirement.edge(
        depth: .category(.medium)
    )
    private static let largeEdgeTarget = ContactRequirement.edge(
        depth: .category(.large)
    )
    private static let smallEdgeTarget = ContactRequirement.edge(
        depth: .category(.small)
    )
    private static let largeSlopeTarget = ContactRequirement(
        kind: .sloper,
        depth: .category(.large)
    )
    private static let fourFingerFlatEdgeTarget = ContactRequirement(
        kind: .edge,
        shape: .flat,
        fingerCapacity: 4
    )
    private static let fourFingerIncutEdgeTarget = ContactRequirement(
        kind: .edge,
        shape: .incut,
        fingerCapacity: 4
    )

    private static func expanded(
        planID: String,
        _ minutes: [[MetoliusTaskDefinition]]
    ) -> [WorkoutStep] {
        var steps: [WorkoutStep] = []
        for (index, tasks) in minutes.enumerated() {
            do {
                steps += try MetoliusCycleBuilder.expand(
                    planID: planID,
                    minute: index + 1,
                    tasks: tasks
                )
            } catch {
                preconditionFailure("Invalid Metolius plan \(planID) minute \(index + 1): \(error)")
            }
        }
        return steps.enumerated().map { index, step in
            step.withNumber(index + 1)
        }
    }

    private static let contactSourceURL = URL(
        string: "https://www.metoliusclimbing.com/pages/contact-training-guide"
    )!

    private static let simulator3DSourceURL = URL(
        string: "https://www.metoliusclimbing.com/pages/simulator-3d-training-guide"
    )!

    /// Keeps an unchanged manufacturer minute as one source-governed cycle.
    /// The guide supplies the 60-second cycle and remaining-time rest, but no
    /// app-defined per-repetition work durations.
    private static func officialSourceCycles(
        planID: String,
        _ minutes: [(instruction: String, targets: [ContactRequirement], phase: WorkoutPhase)]
    ) -> [WorkoutStep] {
        precondition(minutes.count == 10, "An official Metolius routine has ten source minutes.")
        return minutes.enumerated().map { index, minute in
            WorkoutStep(
                id: "\(planID).minute-\(index + 1)",
                number: index + 1,
                title: "Minute \(index + 1)",
                instruction: "\(minute.instruction) Use the remaining time to rest until the next minute.",
                accessory: "60-second source cycle · remaining time rest",
                duration: MetoliusCycleBuilder.cycleDuration,
                phase: minute.phase,
                segments: [
                    WorkoutSegment(
                        kind: .work,
                        target: .fromLegacyTargets(minute.targets),
                        timing: .undefined,
                        duration: nil
                    )
                ]
            )
        }
    }

    private static func officialMetoliusPlan(
        id: String,
        title: String,
        level: String,
        sourceLabel: String,
        sourceURL: URL,
        boardID: String,
        subtitle: String = "Official ten-minute sequence; remaining time rests.",
        minutes: [(instruction: String, targets: [ContactRequirement], phase: WorkoutPhase)]
    ) -> TrainingPlan {
        TrainingPlan(
            id: id,
            title: title,
            subtitle: subtitle,
            level: level,
            sourceLabel: sourceLabel,
            sourceURL: sourceURL,
            provenance: .official,
            boardID: boardID,
            steps: officialSourceCycles(planID: id, minutes)
        )
    }

    static let metoliusContactEntry = officialMetoliusPlan(
        id: "metolius.contact.entry",
        title: "Metolius Contact · Entry",
        level: "Entry",
        sourceLabel: "Metolius Contact Training Guide",
        sourceURL: contactSourceURL,
        boardID: BundledPlanContactRequirements.metoliusContactBoardID,
        minutes: [
            ("1 pull-up outer jugs (2); 10 second hang center edge (17).", BundledPlanContactRequirements.contactTargets(.outerJugs, .edge17), .pull),
            ("1 pull-up deep four finger edge (4), stay on — 10 s bent arm hang (90°), stay on — 1 more pull-up.", BundledPlanContactRequirements.contactTargets(.pocket4), .pull),
            ("2 offset pull-ups (1 arm each) outer jug (2) & deep three finger pockets (6).", BundledPlanContactRequirements.contactTargets(.outerJugs, .pocket6), .pull),
            ("6 s. L-hang on any holds (bend knees if needed); 5 s. dead hang two finger pockets (11).", BundledPlanContactRequirements.contactTargets(.anyHold, .pocket11), .hang),
            ("10 s. dead hang flat sloper (15); 5 knee raises outer jug (2).", BundledPlanContactRequirements.contactTargets(.flatSloper, .outerJugs), .hang),
            ("16 s. offset hang (8 s. per side) deep edge (17) & med pocket (7).", BundledPlanContactRequirements.contactTargets(.edge17, .pocket7), .hang),
            ("3 pull-ups any hold.", BundledPlanContactRequirements.contactTargets(.anyHold), .pull),
            ("10 s. bent arm hang (elbows 90°) round sloper (3).", BundledPlanContactRequirements.contactTargets(.roundSlopers), .hang),
            ("1 offset pull-up, pinch & pocket (1 & 11), change hands & repeat; 10 s. dead hang round sloper (3).", BundledPlanContactRequirements.contactTargets(.pinches, .pocket11, .roundSlopers), .pull),
            ("2 pull-ups any hold; dead hang center edge (17) till failure. Fight hard & don't let go!!", BundledPlanContactRequirements.contactTargets(.anyHold, .edge17), .hang)
        ]
    )

    static let metoliusContactIntermediate = officialMetoliusPlan(
        id: "metolius.contact.intermediate",
        title: "Metolius Contact · Intermediate",
        level: "Intermediate",
        sourceLabel: "Metolius Contact Training Guide",
        sourceURL: contactSourceURL,
        boardID: BundledPlanContactRequirements.metoliusContactBoardID,
        minutes: [
            ("3 pull-ups outer jugs (2); 20 second dead hang deep three finger pockets (6).", BundledPlanContactRequirements.contactTargets(.outerJugs, .pocket6), .pull),
            ("10 s. bent arm (elbows at 90°) hang outer jug (2) — stay on — 2 pull-ups — stay on 10 s. bent arm hang (elbows at 110°).", BundledPlanContactRequirements.contactTargets(.outerJugs), .hang),
            ("4 offset pull-ups (each arm) outer jugs (2) & deep three finger pockets (6).", BundledPlanContactRequirements.contactTargets(.outerJugs, .pocket6), .pull),
            ("10 s. L-hang on any holds; 10 s. dead hang on two finger pockets (11).", BundledPlanContactRequirements.contactTargets(.anyHold, .pocket11), .hang),
            ("10 s. offset hang, deep center edge (17) & med three finger edge (8), reverse holds — repeat.", BundledPlanContactRequirements.contactTargets(.edge17, .pocket8), .hang),
            ("15 s. offset hang pockets (4) & (13), reverse holds — repeat.", BundledPlanContactRequirements.contactTargets(.pocket4, .pocket13), .hang),
            ("4 pull-ups deep center edge (17); 10 knee raises any holds.", BundledPlanContactRequirements.contactTargets(.edge17, .anyHold), .pull),
            ("15 s. dead hang, two finger pockets (7); rest 10 s.; 10 s. hang three finger pockets (9).", BundledPlanContactRequirements.contactTargets(.pocket7, .pocket9), .hang),
            ("10 s. one arm hang round sloper (3), repeat other arm; 4 pull-ups center edge (17).", BundledPlanContactRequirements.contactTargets(.roundSlopers, .edge17), .hang),
            ("4 pull-ups flat sloper (15); bump out to round sloper (3) & dead hang to failure. Fight hard!!", BundledPlanContactRequirements.contactTargets(.flatSloper, .roundSlopers), .hang)
        ]
    )

    static let metoliusContactAdvanced = officialMetoliusPlan(
        id: "metolius.contact.advanced",
        title: "Metolius Contact · Advanced",
        level: "Advanced",
        sourceLabel: "Metolius Contact Training Guide",
        sourceURL: contactSourceURL,
        boardID: BundledPlanContactRequirements.metoliusContactBoardID,
        minutes: [
            ("6 pull-ups outer jugs (2); 20 s. dead hang deep four finger pockets (4).", BundledPlanContactRequirements.contactTargets(.outerJugs, .pocket4), .pull),
            ("15 s. bent arm hang (elbows at 90°) outer jug (2) — stay on — 4 pull-ups — stay on — 15 s. bent arm hang (elbows at 110°).", BundledPlanContactRequirements.contactTargets(.outerJugs), .hang),
            ("6 offset pull-ups (3 each arm) outer jug (2) & deep four finger pockets (4); 10 s. dead hang medium edge (18).", BundledPlanContactRequirements.contactTargets(.outerJugs, .pocket4, .edge18), .pull),
            ("15 s. L-hang any holds (hold good form); 15 s. dead hang on two finger pockets (11).", BundledPlanContactRequirements.contactTargets(.anyHold, .pocket11), .hang),
            ("10 s. dead hang extra shallow three finger pockets (13), stay on; campus to med four finger pocket (9), campus to round slopers (3), hold 15 s.", BundledPlanContactRequirements.contactTargets(.pocket13, .pocket9, .roundSlopers), .hang),
            ("15 s. one arm hang center edge (17); rest 20 s.; repeat other arm.", BundledPlanContactRequirements.contactTargets(.edge17), .hang),
            ("5 L-sit pull-ups (bend knees if you have to), pinches (1); 20 s. bent arm hang (elbows at 90°), deep four finger pockets (4).", BundledPlanContactRequirements.contactTargets(.pinches, .pocket4), .pull),
            ("10 s. hang center edges (16, 17), reverse holds — repeat; 3 power pull-ups (use weights or helper for resistance, should just be able to complete final rep).", BundledPlanContactRequirements.contactTargets(.edge16, .edge17), .hang),
            ("20 s. slight bent arm hang, two finger pockets (7), stay on; bump to round slopers (3), 20 s. dead hang.", BundledPlanContactRequirements.contactTargets(.pocket7, .roundSlopers), .hang),
            ("8 pull-ups flat sloper (3), bump out to round sloper (3), and dead hang to failure. Fight hard!!", BundledPlanContactRequirements.contactTargets(.flatSloper, .roundSlopers), .hang)
        ]
    )

    static let metoliusSimulator3DEntry = officialMetoliusPlan(
        id: "metolius.simulator-3d.entry",
        title: "Metolius Simulator 3D · Entry",
        level: "Entry",
        sourceLabel: "Metolius Simulator 3D Training Guide",
        sourceURL: simulator3DSourceURL,
        boardID: BundledPlanContactRequirements.metoliusSimulator3DBoardID,
        subtitle: "Official ten-minute sequence; remaining time rests. Feet on a chair may lower resistance; place it 1'–3' behind the board plane.",
        minutes: [
            ("10 second dead hang, deep flat edge (7).", BundledPlanContactRequirements.simulator3DTargets(.edge7), .hang),
            ("15 second dead hang + one pull-up, outer jugs (1).", BundledPlanContactRequirements.simulator3DTargets(.outerJugs), .hang),
            ("2 offset pull-up (1 each arm) center jug (14) & deep three finger pockets (4).", BundledPlanContactRequirements.simulator3DTargets(.centerJug, .pocket4), .pull),
            ("15 second dead hang, extra deep 3 finger pockets (9).", BundledPlanContactRequirements.simulator3DTargets(.pocket9), .hang),
            ("12 second dead hang flat slopers (2) & 5 knee raises outer jugs (1).", BundledPlanContactRequirements.simulator3DTargets(.flatSlopers, .outerJugs), .hang),
            ("16 second offset hang / (8 sec per side), deep pocket (15) & shallow edge (5).", BundledPlanContactRequirements.simulator3DTargets(.pocket15, .edge5), .hang),
            ("3 pull-ups outer jugs (1).", BundledPlanContactRequirements.simulator3DTargets(.outerJugs), .pull),
            ("8 second bent arm hang (elbows @ 90), round slopers (3).", BundledPlanContactRequirements.simulator3DTargets(.roundSlopers), .hang),
            ("1 pull-up & then 10 second hang, ext-deep 3 finger pocket (9).", BundledPlanContactRequirements.simulator3DTargets(.pocket9), .pull),
            ("Dead hang to failure, any holds.", BundledPlanContactRequirements.simulator3DTargets(.anyHold), .hang)
        ]
    )

    static let metoliusSimulator3DIntermediate = officialMetoliusPlan(
        id: "metolius.simulator-3d.intermediate",
        title: "Metolius Simulator 3D · Intermediate",
        level: "Intermediate",
        sourceLabel: "Metolius Simulator 3D Training Guide",
        sourceURL: simulator3DSourceURL,
        boardID: BundledPlanContactRequirements.metoliusSimulator3DBoardID,
        minutes: [
            ("25 second dead hang, medium edge (5).", BundledPlanContactRequirements.simulator3DTargets(.edge5), .hang),
            ("20 second dead hang, flat slopers (2), 3 pull-ups flat slopers.", BundledPlanContactRequirements.simulator3DTargets(.flatSlopers), .hang),
            ("15 second bent arm hang, shallow edge (6) & 10 knee raises, jugs (1).", BundledPlanContactRequirements.simulator3DTargets(.edge6, .outerJugs), .hang),
            ("15 second dead hang flat slope (2), 15 second dead hang round slopers (3).", BundledPlanContactRequirements.simulator3DTargets(.flatSlopers, .roundSlopers), .hang),
            ("20 second offset hang, jug (1) & shallow pocket (17), reverse holds — repeat.", BundledPlanContactRequirements.simulator3DTargets(.outerJugs, .pocket17), .hang),
            ("15 second offset hang, pockets (4 & 9), reverse holds and repeat.", BundledPlanContactRequirements.simulator3DTargets(.pocket4, .pocket9), .hang),
            ("4 pull-ups, medium edges, 10 knee raises any holds.", BundledPlanContactRequirements.simulator3DTargets(.edge5, .anyHold), .pull),
            ("30 second dead hang, deep pockets (7).", BundledPlanContactRequirements.simulator3DTargets(.edge7), .hang),
            ("10 sec one arm hang jugs (1), repeat other arm.", BundledPlanContactRequirements.simulator3DTargets(.outerJugs), .hang),
            ("5 pull-ups deep edges (7), without dropping off, bump up to round slopers (3) & dead hang till failure.", BundledPlanContactRequirements.simulator3DTargets(.edge7, .roundSlopers), .hang)
        ]
    )

    static let metoliusSimulator3DAdvanced = officialMetoliusPlan(
        id: "metolius.simulator-3d.advanced",
        title: "Metolius Simulator 3D · Advanced",
        level: "Advanced",
        sourceLabel: "Metolius Simulator 3D Training Guide",
        sourceURL: simulator3DSourceURL,
        boardID: BundledPlanContactRequirements.metoliusSimulator3DBoardID,
        minutes: [
            ("25 second dead hang shallow edge (6), 5 pull-ups three finger pockets (9).", BundledPlanContactRequirements.simulator3DTargets(.edge6, .pocket9), .hang),
            ("5 offset pull-ups, pockets (15 & 12), reverse holds repeat.", BundledPlanContactRequirements.simulator3DTargets(.pocket15, .pocket12), .pull),
            ("45 second dead hang, extra shallow edges (11).", BundledPlanContactRequirements.simulator3DTargets(.edge11), .hang),
            ("5 offset pull-ups, round sloper (3) & deep pocket (4), reverse holds repeat.", BundledPlanContactRequirements.simulator3DTargets(.roundSlopers, .pocket4), .pull),
            ("10 second dead hang, x-shallow edges (11), staying on, campus to three finger pockets (9), campus to shallow edges (6), campus to flat slopers (2), hold for 15 seconds.", BundledPlanContactRequirements.simulator3DTargets(.edge11, .pocket9, .edge6, .flatSlopers), .hang),
            ("15 second one arm hang, round sloper (3), rest 10 seconds, repeat other arm.", BundledPlanContactRequirements.simulator3DTargets(.roundSlopers), .hang),
            ("5 L-sit pull-ups (bend knees if you have to), jugs (1), 20 second bent arm hang (elbows @ 90), deep two finger pockets (12).", BundledPlanContactRequirements.simulator3DTargets(.outerJugs, .pocket12), .pull),
            ("20 second slightly bent arm hang, shallow 3 finger pocket (8), stay on, bump to x-deep three finger pockets 25 second dead hang.", BundledPlanContactRequirements.simulator3DTargets(.pocket8, .pocket9), .hang),
            ("10 second hang center pockets (18 & 17), reverse holds repeat, three power pull-ups (use weights or helper for resistance, should just be able to complete third pull).", BundledPlanContactRequirements.simulator3DTargets(.pocket18, .pocket17), .hang),
            ("8 fast pull-ups, jugs (1) (keeping form perfect), dead hang round sloper to failure (fighting hard!).", BundledPlanContactRequirements.simulator3DTargets(.outerJugs, .roundSlopers), .hang)
        ]
    )

    private static let rockRingSourceURL = URL(
        string: "https://www.metoliusclimbing.com/pages/rock-ring-training-guide"
    )!

    static let metoliusRockRing = officialMetoliusPlan(
        id: "metolius.rock-rings.ten-minute",
        title: "Metolius Rock Rings · 10-Minute Sequence",
        level: "All levels",
        sourceLabel: "Metolius Rock Ring Training Guide",
        sourceURL: rockRingSourceURL,
        boardID: BundledPlanContactRequirements.metoliusRockRingBoardID,
        subtitle: "Official ten-minute sequence; remaining time rests.",
        minutes: [
            ("3 pull-ups on jugs.", BundledPlanContactRequirements.rockRingTargets(.jugs), .pull),
            ("10 second bent-arm hang on 3 finger pockets; 15 second dead hang on 2 finger pockets.", BundledPlanContactRequirements.rockRingTargets(.threeFingerPockets, .twoFingerPockets), .hang),
            ("2 offset pull-ups on 4 finger edge & 2 finger pocket; 2 offset pull-ups other way.", BundledPlanContactRequirements.rockRingTargets(.fourFingerEdges, .twoFingerPockets), .pull),
            ("20 second L-hang on 4 finger edges; 10 second dead hang on 3 finger pockets.", BundledPlanContactRequirements.rockRingTargets(.fourFingerEdges, .threeFingerPockets), .hang),
            ("5 pull-ups on 4 finger edges.", BundledPlanContactRequirements.rockRingTargets(.fourFingerEdges), .pull),
            ("20 second bent-arm hang on 3 finger pockets; 10 second dead hang on 2 finger pockets.", BundledPlanContactRequirements.rockRingTargets(.threeFingerPockets, .twoFingerPockets), .hang),
            ("15 second L-hang on 4 finger edges; 15 second dead hang on 4 finger edges.", BundledPlanContactRequirements.rockRingTargets(.fourFingerEdges), .hang),
            ("10 second offset hang on 4 finger edge & 2 finger pocket; 10 second offset hang other way.", BundledPlanContactRequirements.rockRingTargets(.fourFingerEdges, .twoFingerPockets), .hang),
            ("20 second L-hang on 4 finger edges.", BundledPlanContactRequirements.rockRingTargets(.fourFingerEdges), .hang),
            ("5 pull-ups on 3 finger pockets; dead hang 3 finger pockets to failure. Fight hard!!", BundledPlanContactRequirements.rockRingTargets(.threeFingerPockets), .hang)
        ]
    )

    static let metoliusEntry = TrainingPlan(
        id: "metolius.generic-ten-minute.entry",
        title: "Metolius 10-minute · Entry",
        subtitle: adaptationNote,
        level: "Entry",
        sourceLabel: sourceLabel,
        sourceURL: sourceURL,
        provenance: .adapted,
        boardID: nil,
        steps: expanded(planID: "entry", [
            [MetoliusCycleBuilder.fixed(title: "Jug hang", instruction: "Hang from the jugs for 15 seconds.", duration: 15, phase: .hang, targets: [.kind(.jug)])],
            [MetoliusCycleBuilder.pullUps(count: 1, title: "Round sloper pull-up", instruction: "Do 1 pull-up on a round sloper.", phase: .pull, targets: [roundSloperTarget])],
            [MetoliusCycleBuilder.fixed(title: "Medium-edge hang", instruction: "Hang from a medium edge for 10 seconds.", duration: 10, phase: .hang, targets: [mediumEdgeTarget])],
            [MetoliusCycleBuilder.fixed(title: "Pocket hang + shrugs", instruction: "Hang from a pocket for 15 seconds and include 3 shrugs.", duration: 15, phase: .hang, targets: [.kind(.pocket)])],
            [MetoliusCycleBuilder.fixed(title: "Large edge + pull-ups", instruction: "Hang from a large edge for 20 seconds and include 2 pull-ups.", duration: 20, phase: .hang, targets: [largeEdgeTarget])],
            [
                MetoliusCycleBuilder.fixed(title: "Round-sloper hang", instruction: "Hang from a round sloper for 10 seconds.", duration: 10, phase: .hang, targets: [roundSloperTarget]),
                MetoliusCycleBuilder.repetitions(count: 5, title: "Pocket knee raises", instruction: "Do 5 knee raises on a pocket.", phase: .pull, targets: [.kind(.pocket)])
            ],
            [MetoliusCycleBuilder.pullUps(count: 4, title: "Large-edge pull-ups", instruction: "Do 4 pull-ups on a large edge.", phase: .pull, targets: [largeEdgeTarget])],
            [MetoliusCycleBuilder.fixed(title: "Medium-edge hang", instruction: "Hang from a medium edge for 10 seconds.", duration: 10, phase: .hang, targets: [mediumEdgeTarget])],
            [MetoliusCycleBuilder.pullUps(count: 3, title: "Jug pull-ups", instruction: "Do 3 pull-ups on the jugs.", phase: .pull, targets: [.kind(.jug)])],
            [MetoliusCycleBuilder.maxEffort(title: "Maximum sloper hang", instruction: "Hang from a round sloper for as long as you can.", phase: .hang, targets: [roundSloperTarget])]
        ])
    )

    static let metoliusIntermediate = TrainingPlan(
        id: "metolius.generic-ten-minute.intermediate",
        title: "Metolius 10-minute · Intermediate",
        subtitle: adaptationNote,
        level: "Intermediate",
        sourceLabel: sourceLabel,
        sourceURL: sourceURL,
        provenance: .adapted,
        boardID: nil,
        steps: expanded(planID: "intermediate", [
            [
                MetoliusCycleBuilder.fixed(title: "Large-edge hang", instruction: "Hang from a large edge for 15 seconds.", duration: 15, phase: .hang, targets: [largeEdgeTarget]),
                MetoliusCycleBuilder.pullUps(count: 3, title: "Large-edge pull-ups", instruction: "Do 3 pull-ups on the large edge.", phase: .pull, targets: [largeEdgeTarget])
            ],
            [
                MetoliusCycleBuilder.pullUps(count: 2, title: "Round sloper pull-ups", instruction: "Do 2 pull-ups on a round sloper.", phase: .pull, targets: [roundSloperTarget]),
                MetoliusCycleBuilder.fixed(title: "Medium-edge hang", instruction: "Hang from a medium edge for 20 seconds.", duration: 20, phase: .hang, targets: [mediumEdgeTarget])
            ],
            [
                MetoliusCycleBuilder.fixed(title: "Small-edge hang", instruction: "Hang from a small edge for 20 seconds.", duration: 20, phase: .hang, targets: [smallEdgeTarget]),
                MetoliusCycleBuilder.fixed(title: "Bent-arm pocket hang", instruction: "Hold a pocket at a 90° bent arm for 15 seconds.", duration: 15, phase: .hang, targets: [.kind(.pocket)])
            ],
            [MetoliusCycleBuilder.fixed(title: "Round-sloper hang", instruction: "Hang from a round sloper for 30 seconds.", duration: 30, phase: .hang, targets: [roundSloperTarget])],
            [
                MetoliusCycleBuilder.fixed(title: "Large-edge hang", instruction: "Hang from a large edge for 20 seconds.", duration: 20, phase: .hang, targets: [largeEdgeTarget]),
                MetoliusCycleBuilder.pullUps(count: 4, title: "Pocket pull-ups", instruction: "Do 4 pull-ups on a pocket.", phase: .pull, targets: [.kind(.pocket)])
            ],
            [
                MetoliusCycleBuilder.pullUps(count: 3, title: "Offset pulls", instruction: "Do 3 offset pulls with the high hand on a jug and low hand on a small edge.", phase: .pull, targets: [.kind(.jug), smallEdgeTarget]),
                MetoliusCycleBuilder.pullUps(count: 3, title: "Offset pulls · other side", instruction: "Change hands and repeat 3 offset pulls with the high hand on a jug and low hand on a small edge.", phase: .pull, targets: [.kind(.jug), smallEdgeTarget])
            ],
            [
                MetoliusCycleBuilder.repetitions(count: 15, title: "Jug knee raises", instruction: "Do 15 knee raises on the jugs.", phase: .pull, targets: [.kind(.jug)]),
                MetoliusCycleBuilder.fixed(title: "Medium-edge hang", instruction: "Hang from a medium edge for 15 seconds.", duration: 15, phase: .hang, targets: [mediumEdgeTarget])
            ],
            [MetoliusCycleBuilder.fixed(title: "Medium-edge hang", instruction: "Hang from a medium edge for 25 seconds.", duration: 25, phase: .hang, targets: [mediumEdgeTarget])],
            [
                MetoliusCycleBuilder.fixed(title: "Slope hang", instruction: "Hang from a slope for 15 seconds.", duration: 15, phase: .hang, targets: [largeSlopeTarget]),
                MetoliusCycleBuilder.pullUps(count: 3, title: "Jug pull-ups", instruction: "Do 3 pull-ups on the jugs.", phase: .pull, targets: [.kind(.jug)])
            ],
            [MetoliusCycleBuilder.maxEffort(title: "Maximum sloper hang", instruction: "Hang from a round sloper for as long as you can.", phase: .hang, targets: [roundSloperTarget])]
        ])
    )

    static let metoliusAdvanced = TrainingPlan(
        id: "metolius.generic-ten-minute.advanced",
        title: "Metolius 10-minute · Advanced",
        subtitle: adaptationNote,
        level: "Advanced",
        sourceLabel: sourceLabel,
        sourceURL: sourceURL,
        provenance: .adapted,
        boardID: nil,
        steps: expanded(planID: "advanced", [
            [
                MetoliusCycleBuilder.fixed(
                    title: "Large-slope hang",
                    instruction: "Hold a straight-arm hang on a large slope for 20 seconds.",
                    duration: 20,
                    phase: .hang,
                    targets: [largeSlopeTarget],
                    gripType: nil
                ),
                MetoliusCycleBuilder.pullUps(
                    count: 3,
                    title: "Four-finger flat-edge pull-ups",
                    instruction: "Do 3 pull-ups on a four-finger flat edge.",
                    phase: .pull,
                    targets: [fourFingerFlatEdgeTarget]
                )
            ],
            [
                MetoliusCycleBuilder.fixed(
                    title: "Bent-arm large-slope hang",
                    instruction: "Hold a slightly bent-arm hang on a large slope for 20 seconds.",
                    duration: 20,
                    phase: .hang,
                    targets: [largeSlopeTarget],
                    gripType: nil
                ),
                MetoliusCycleBuilder.fixed(
                    title: "L-sit or hanging knee curls",
                    instruction: "Stay on for a 20-second L-sit or 20 hanging knee curls.",
                    duration: 20,
                    phase: .hang,
                    targets: [largeSlopeTarget],
                    gripType: nil
                )
            ],
            [
                MetoliusCycleBuilder.pullUps(
                    count: 5,
                    title: "Three-finger-pocket pull-ups",
                    instruction: "Do 5 pull-ups on a three-finger pocket.",
                    phase: .pull,
                    targets: [.kind(.pocket, fingerCapacity: 3)],
                    gripType: nil
                ),
                MetoliusCycleBuilder.fixed(
                    title: "Straight-arm three-finger-pocket hang",
                    instruction: "Stay on for a 25-second straight-arm hang on the same three-finger pocket.",
                    duration: 25,
                    phase: .hang,
                    targets: [.kind(.pocket, fingerCapacity: 3)],
                    gripType: nil
                )
            ],
            [
                MetoliusCycleBuilder.fixed(
                    title: "Hold ladder",
                    instruction: "Start at a three-finger pocket and move through every hold upward, staying on each for 5 seconds; finish with a 20-second large-slope hang.",
                    duration: 40,
                    phase: .hang,
                    targets: [.kind(.pocket), .kind(.edge), .kind(.sloper), .kind(.jug)]
                )
            ],
            [
                MetoliusCycleBuilder.fixed(
                    title: "Single-arm flat-edge hang",
                    instruction: "Hang one-armed from a four-finger flat edge for 20 seconds.",
                    duration: 20,
                    phase: .hang,
                    targets: [fourFingerFlatEdgeTarget]
                ),
                MetoliusCycleBuilder.fixed(
                    title: "Single-arm flat-edge hang · other hand",
                    instruction: "Switch hands and repeat the 20-second one-armed hang from a four-finger flat edge.",
                    duration: 20,
                    phase: .hang,
                    targets: [fourFingerFlatEdgeTarget]
                )
            ],
            [
                MetoliusCycleBuilder.pullUps(
                    count: 5,
                    title: "Offset pull-ups",
                    instruction: "Do 5 offset pull-ups with the top hand on a large slope and bottom hand on a three-finger pocket.",
                    phase: .pull,
                    targets: [largeSlopeTarget, .kind(.pocket, fingerCapacity: 3)]
                ),
                MetoliusCycleBuilder.pullUps(
                    count: 5,
                    title: "Offset pull-ups · other side",
                    instruction: "Change hands and repeat 5 offset pull-ups with the top hand on a large slope and bottom hand on a three-finger pocket.",
                    phase: .pull,
                    targets: [largeSlopeTarget, .kind(.pocket, fingerCapacity: 3)]
                )
            ],
            [
                MetoliusCycleBuilder.fixed(
                    title: "Incut-edge bent-arm hang",
                    instruction: "Hold a 90° bent-arm hang on a four-finger incut edge for 30 seconds.",
                    duration: 30,
                    phase: .hang,
                    targets: [fourFingerIncutEdgeTarget]
                ),
                MetoliusCycleBuilder.fixed(
                    title: "Straight-arm three-finger-pocket hang",
                    instruction: "Then hold a straight-arm three-finger-pocket hang for 15 seconds.",
                    duration: 15,
                    phase: .hang,
                    targets: [.kind(.pocket, fingerCapacity: 3)],
                    gripType: nil
                )
            ],
            [
                MetoliusCycleBuilder.pullUps(
                    count: 3,
                    title: "L-sit pull-ups",
                    instruction: "Do 3 L-sit pull-ups, bending your knees if needed.",
                    phase: .pull,
                    targets: [largeSlopeTarget]
                ),
                MetoliusCycleBuilder.choice(
                    title: "Choose one: front lever or straight-arm hang",
                    instruction: "Choose one: hold a 5-second front lever or 15-second straight-arm hang on a large slope. If choosing the front lever, finish at 5 seconds; do not perform both.",
                    accessory: "Choose one · 5 seconds front lever OR 15 seconds straight-arm large-slope hang",
                    duration: 15,
                    phase: .hang,
                    targets: [largeSlopeTarget],
                    gripType: nil
                )
            ],
            [
                MetoliusCycleBuilder.fixed(
                    title: "Two-finger three-finger-pocket hang",
                    instruction: "Hang straight-armed for 20 seconds using only 2 fingers in three-finger pockets.",
                    duration: 20,
                    phase: .hang,
                    targets: [.kind(.pocket, fingerCapacity: 3)],
                    gripType: nil
                ),
                MetoliusCycleBuilder.pullUps(
                    count: 3,
                    title: "Power pull-ups",
                    instruction: "Then do 3 power pull-ups with weight or helper resistance.",
                    phase: .pull,
                    targets: [.kind(.pocket, fingerCapacity: 3)]
                )
            ],
            [
                MetoliusCycleBuilder.maxEffort(
                    title: "Maximum slope hangs",
                    instruction: "Do a maximum slightly bent-arm hang on a large slope to failure with no rest, then a maximum straight-arm hang on the large slope.",
                    phase: .hang,
                    targets: [largeSlopeTarget],
                    gripType: nil
                )
            ]
        ])
    )

    private static func fixedWork(_ target: ContactRequirement, _ duration: TimeInterval) -> WorkoutSegment {
        WorkoutSegment(kind: .work, target: .fromLegacyTargets([target]), timing: .fixed, duration: duration)
    }

    private static func fixedRest(_ duration: TimeInterval) -> WorkoutSegment {
        WorkoutSegment(kind: .rest, target: nil, timing: .fixed, duration: duration)
    }

    static let sharedWarmUpDuration: TimeInterval = 60
    static let sharedCoolDownDuration: TimeInterval = 60

    private static func hangStep(
        id: String,
        title: String,
        instruction: String,
        accessory: String,
        active: TimeInterval,
        rest: TimeInterval,
        targets: [ContactRequirement],
        gripType: GripType? = nil,
        fingerConfiguration: FingerConfiguration? = nil,
        handUse: WorkoutHandUse = .double
    ) -> WorkoutStep {
        WorkoutStep(
            id: id,
            number: 0,
            title: title,
            instruction: instruction,
            accessory: accessory,
            duration: active + rest,
            phase: .hang,
            segments: [
                WorkoutSegment(
                    kind: .work,
                    target: .fromLegacyTargets(targets),
                    timing: .fixed,
                    duration: active
                )
            ] + (rest > 0 ? [fixedRest(rest)] : []),
            gripType: gripType,
            fingerConfiguration: fingerConfiguration,
            handUse: handUse,
            timedWorkDuration: active
        )
    }

    private static func recoveryStep(id: String, title: String, duration: TimeInterval, accessory: String) -> WorkoutStep {
        WorkoutStep(
            id: id,
            number: 0,
            title: title,
            instruction: "",
            accessory: accessory,
            duration: duration,
            phase: .rest,
            segments: [fixedRest(duration)]
        )
    }

    private static func numbered(_ steps: [WorkoutStep]) -> [WorkoutStep] {
        steps.enumerated().map { index, step in
            step.withNumber(index + 1)
        }
    }

    /// Lattice max-hang and Abrahangs protocols both name a 20 mm edge and are
    /// two-handed hangs. `.bilateralPair` resolves the board's paired left/right
    /// 20 mm holds.
    private static let lattice20mmEdgePairTarget = ContactRequirement.edge(
        depth: .range(.init(minimum: 20, maximum: 20)),
        selection: .bilateralPair
    )

    /// Frontiers force-feedback study instrumented hold.
    private static let forceFeedback12mmEdgeTarget = ContactRequirement.edge(
        depth: .range(.init(minimum: 12, maximum: 12)),
        selection: .single
    )

    /// Reported Megos protocol edge depth range.
    private static let megos20to24mmEdgeTarget = ContactRequirement.edge(
        depth: .range(.init(minimum: 20, maximum: 24)),
        selection: .single
    )

    /// Hörst 7–53 recommends 14–20 mm edges for half/open work.
    private static let horst14to20mmEdgeTarget = ContactRequirement.edge(
        depth: .range(.init(minimum: 14, maximum: 20)),
        selection: .single
    )

    /// Hörst 7–53 recommends 20–30 mm two-finger pockets.
    private static let horst20to30mmTwoFingerPocketTarget = ContactRequirement(
        kind: .pocket,
        depth: .range(.init(minimum: 20, maximum: 30)),
        fingerCapacity: 2,
        selection: .single
    )

    /// Density Hangs tip: relatively large edges (20–35 mm).
    private static let densityLargeEdgeTarget = ContactRequirement.edge(
        depth: .range(.init(minimum: 20, maximum: 35)),
        selection: .single
    )

    /// Zlagboard endurance example hold class (“e.g., 20 mm edges”).
    private static let zlagboard20mmEdgeTarget = ContactRequirement.edge(
        depth: .range(.init(minimum: 20, maximum: 20)),
        selection: .single
    )

    /// Hooper's Beta “medium to large ledge” spans categorical medium+large mm.
    private static let hoopersMediumToLargeLedgeTarget = ContactRequirement.edge(
        depth: .range(.init(minimum: 15, maximum: 50)),
        selection: .single
    )

    /// Hooper's Beta minimal-edge / small half-crimp recruitment hold.
    private static let hoopersSmallEdgeTarget = ContactRequirement.edge(
        depth: .category(.small),
        selection: .single
    )

    /// Method Climbing repeaters: try 15 mm or 20 mm.
    private static let methodRepeaters15to20mmEdgeTarget = ContactRequirement.edge(
        depth: .range(.init(minimum: 15, maximum: 20)),
        selection: .single
    )

    private static let method20mmEdgeTarget = ContactRequirement.edge(
        depth: .range(.init(minimum: 20, maximum: 20)),
        selection: .single
    )

    private static let method15mmEdgeTarget = ContactRequirement.edge(
        depth: .range(.init(minimum: 15, maximum: 15)),
        selection: .single
    )

    private static let methodDeepThreeFingerPocketTarget = ContactRequirement(
        kind: .pocket,
        depth: .category(.large),
        fingerCapacity: 3,
        selection: .single
    )

    private static let methodMediumThreeFingerPocketTarget = ContactRequirement(
        kind: .pocket,
        depth: .category(.medium),
        fingerCapacity: 3,
        selection: .single
    )

    private static let methodJugTarget = ContactRequirement.kind(.jug)
    private static let methodSloperTarget = ContactRequirement.kind(.sloper)
    private static let methodSmallEdgeTarget = ContactRequirement.edge(
        depth: .category(.small),
        selection: .single
    )

    static let maxHangs = TrainingPlan(
        id: "research.max-hangs",
        title: "Max Hangs",
        subtitle: "Five near-maximal 7-second half-crimp hangs on a 20 mm edge.",
        level: "Advanced",
        sourceLabel: "Lattice max hang protocol",
        sourceURL: URL(string: "https://latticetraining.com/workout/1c4cc25a-ebe8-4930-8541-5b604a831c5f/half-4-hang-max/")!,
        provenance: .adapted,
        boardID: nil,
        steps: numbered([
            hangStep(
                id: "max-hangs-1",
                title: "Max hang · set 1",
                instruction: "Hang for 7 seconds on a 20 mm edge in a half-crimp, four-finger position at near-maximal intensity.",
                accessory: "7s hang · 3m recovery · half crimp",
                active: 7,
                rest: 180,
                targets: [lattice20mmEdgePairTarget],
                gripType: .halfCrimp,
                fingerConfiguration: FingerConfiguration(engagedFingers: [.index, .middle, .ring, .pinky]),
                handUse: .double
            ),
            hangStep(
                id: "max-hangs-2",
                title: "Max hang · set 2",
                instruction: "Hang for 7 seconds on a 20 mm edge in a half-crimp, four-finger position at near-maximal intensity.",
                accessory: "7s hang · 3m recovery · half crimp",
                active: 7,
                rest: 180,
                targets: [lattice20mmEdgePairTarget],
                gripType: .halfCrimp,
                fingerConfiguration: FingerConfiguration(engagedFingers: [.index, .middle, .ring, .pinky]),
                handUse: .double
            ),
            hangStep(
                id: "max-hangs-3",
                title: "Max hang · set 3",
                instruction: "Hang for 7 seconds on a 20 mm edge in a half-crimp, four-finger position at near-maximal intensity.",
                accessory: "7s hang · 3m recovery · half crimp",
                active: 7,
                rest: 180,
                targets: [lattice20mmEdgePairTarget],
                gripType: .halfCrimp,
                fingerConfiguration: FingerConfiguration(engagedFingers: [.index, .middle, .ring, .pinky]),
                handUse: .double
            ),
            hangStep(
                id: "max-hangs-4",
                title: "Max hang · set 4",
                instruction: "Hang for 7 seconds on a 20 mm edge in a half-crimp, four-finger position at near-maximal intensity.",
                accessory: "7s hang · 3m recovery · half crimp",
                active: 7,
                rest: 180,
                targets: [lattice20mmEdgePairTarget],
                gripType: .halfCrimp,
                fingerConfiguration: FingerConfiguration(engagedFingers: [.index, .middle, .ring, .pinky]),
                handUse: .double
            ),
            hangStep(
                id: "max-hangs-5",
                title: "Max hang · set 5",
                instruction: "Hang for 7 seconds on a 20 mm edge in a half-crimp, four-finger position at near-maximal intensity.",
                accessory: "7s hang · half crimp",
                active: 7,
                rest: 0,
                targets: [lattice20mmEdgePairTarget],
                gripType: .halfCrimp,
                fingerConfiguration: FingerConfiguration(engagedFingers: [.index, .middle, .ring, .pinky]),
                handUse: .double
            ),
        ])
    )

    static let forceF80 = TrainingPlan(
        id: "research.force-feedback-f80",
        title: "F80 Force Board",
        subtitle: "Three sets of up to 12 10-second hangs at 80% MFSi with real-time force feedback on an instrumented 12 mm edge.",
        level: "Advanced",
        sourceLabel: "Frontiers force-feedback hangboard study",
        sourceURL: URL(string: "https://www.frontiersin.org/journals/sports-and-active-living/articles/10.3389/fspor.2022.862782/full")!,
        provenance: .adapted,
        boardID: nil,
        steps: numbered({
            var steps: [WorkoutStep] = []
            for set in 1...3 {
                for rep in 1...12 {
                    steps.append(
                        hangStep(
                            id: "f80-set-\(set)-rep-\(rep)",
                            title: "F80 · set \(set), rep \(rep)",
                            instruction: "Use real-time force feedback to hang with both hands at 80% MFSi on an instrumented 12 mm edge for 10 seconds; rest 6 seconds between repetitions. Stop the set if force falls below 70% MFSi.",
                            accessory: "10s hang · 6s rest · 80% MFSi",
                            active: 10,
                            rest: set == 3 && rep == 12 ? 0 : 6,
                            targets: [forceFeedback12mmEdgeTarget],
                            gripType: nil
                        )
                    )
                }
                if set < 3 {
                    steps.append(
                        recoveryStep(
                            id: "f80-set-\(set)-recovery",
                            title: "Eight-minute set recovery",
                            duration: 480,
                            accessory: "8m recovery"
                        )
                    )
                }
            }
            return steps
        }())
    )

    static let forceF100 = TrainingPlan(
        id: "research.force-feedback-f100",
        title: "F100 Force Board",
        subtitle: "Two sets of six 6-second hangs per hand with real-time force feedback on an instrumented 12 mm edge.",
        level: "Expert",
        sourceLabel: "Frontiers force-feedback hangboard study",
        sourceURL: URL(string: "https://www.frontiersin.org/journals/sports-and-active-living/articles/10.3389/fspor.2022.862782/full")!,
        provenance: .adapted,
        boardID: nil,
        steps: numbered({
            var steps: [WorkoutStep] = []
            for set in 1...2 {
                for round in 1...6 {
                    steps.append(
                        hangStep(
                            id: "f100-set-\(set)-round-\(round)-right",
                            title: "F100 · right hand",
                            instruction: "Use real-time force feedback to apply maximal force with the right hand on an instrumented 12 mm edge for 6 seconds.",
                            accessory: "6s max",
                            active: 6,
                            rest: 0,
                            targets: [forceFeedback12mmEdgeTarget],
                            gripType: nil
                        )
                    )
                    steps.append(
                        hangStep(
                            id: "f100-set-\(set)-round-\(round)-left",
                            title: "F100 · left hand",
                            instruction: "Use real-time force feedback to apply maximal force with the left hand on an instrumented 12 mm edge for 6 seconds.",
                            accessory: "6s max",
                            active: 6,
                            rest: round == 6 ? (set == 1 ? 300 : 0) : 168,
                            targets: [forceFeedback12mmEdgeTarget],
                            gripType: nil
                        )
                    )
                }
            }
            return steps
        }())
    )

    static let evaIntHangs = TrainingPlan(
        id: "research.eva-int-hangs",
        title: "Eva Intermittent Dead-Hangs",
        subtitle: "Intermittent dead-hangs with 10-second hangs and 5-second rests.",
        level: "Intermediate+",
        sourceLabel: "Eva López hangboard comparison",
        sourceURL: URL(string: "https://pubmed.ncbi.nlm.nih.gov/30988852/")!,
        provenance: .adapted,
        boardID: nil,
        steps: numbered({
            var steps: [WorkoutStep] = []
            for set in 1...3 {
                for rep in 1...5 {
                    steps.append(
                        hangStep(
                            id: "int-hangs-set-\(set)-rep-\(rep)",
                            title: "IntHang · set \(set), rep \(rep)",
                            instruction: "Hang for 10 seconds, then rest for 5 seconds.",
                            accessory: "10s hang · 5s rest",
                            active: 10,
                            rest: rep < 5 ? 5 : 0,
                            targets: [],
                            gripType: nil
                        )
                    )
                }
                if set < 3 {
                    steps.append(
                        recoveryStep(
                            id: "int-hangs-set-\(set)-recovery",
                            title: "One-minute set recovery",
                            duration: 60,
                            accessory: "1m recovery"
                        )
                    )
                }
            }
            return steps
        }())
    )

    static let repeaters = TrainingPlan(
        id: "research.seven-three-repeaters",
        title: "7/3 Repeaters",
        subtitle: "Two 7/3 repeater sets across six progressive series.",
        level: "Intermediate",
        sourceLabel: "Beastmaker 7/3 study protocol",
        sourceURL: URL(string: "https://www.frontiersin.org/journals/sports-and-active-living/articles/10.3389/fspor.2022.888158/full")!,
        provenance: .adapted,
        boardID: nil,
        steps: numbered({
            var steps: [WorkoutStep] = []
            let grips: [(
                title: String,
                targets: [ContactRequirement],
                grip: GripType?,
                fingerConfiguration: FingerConfiguration?
            )] = [
                ("29 mm open edge", [ContactRequirement.edge(depth: .range(.init(minimum: 29, maximum: 29)))], .openHand, nil),
                ("19 mm open edge", [ContactRequirement.edge(depth: .range(.init(minimum: 19, maximum: 19)))], .openHand, nil),
                ("19 mm half crimp", [ContactRequirement.edge(depth: .range(.init(minimum: 19, maximum: 19)))], .halfCrimp, nil),
                ("Front-three open edge", [ContactRequirement(kind: .edge, fingerCapacity: 3)], .openHand, FingerConfiguration(engagedFingers: [.index, .middle, .ring])),
                ("Back-three half crimp", [ContactRequirement(kind: .edge, fingerCapacity: 3)], .halfCrimp, FingerConfiguration(engagedFingers: [.middle, .ring, .pinky])),
                ("Front-two open edge", [ContactRequirement(kind: .edge, fingerCapacity: 2)], .openHand, FingerConfiguration(engagedFingers: [.index, .middle]))
            ]

            for set in 1...2 {
                for (index, grip) in grips.enumerated() {
                    for rep in 1...7 {
                        steps.append(
                            hangStep(
                                id: "\(repeaterStepIDPrefix)set-\(set)-series-\(index + 1)-rep-\(rep)",
                                title: "7/3 · set \(set) · \(grip.title) · rep \(rep)",
                                instruction: "Hang for 7 seconds, then rest for 3 seconds.",
                                accessory: "7s hang · 3s rest · 7 reps",
                                active: 7,
                                rest: rep < 7 ? 3 : 0,
                                targets: grip.targets,
                                gripType: grip.grip,
                                fingerConfiguration: grip.fingerConfiguration
                            )
                        )
                    }
                    if index < grips.count - 1 {
                        steps.append(
                            recoveryStep(
                                id: "\(repeaterStepIDPrefix)set-\(set)-series-\(index + 1)-recovery",
                                title: "Series recovery",
                                duration: 150,
                                accessory: "2m 30s recovery"
                            )
                        )
                    }
                }
                if set < 2 {
                    steps.append(
                        recoveryStep(
                            id: "\(repeaterStepIDPrefix)set-\(set)-recovery",
                            title: "Set recovery",
                            duration: 360,
                            accessory: "6m recovery"
                        )
                    )
                }
            }
            return steps
        }())
    )

    /// Faithful step-level expansion of the reported Megos protocol. The
    /// source states the work/rest cycle and side/set order, while the app
    /// exposes each source repetition as its own unilateral timer step.
    static let megoOneArmSevenThree = TrainingPlan(
        id: "research.megos-one-arm-7-3",
        title: "Megos · One-arm 7/3 Repeaters",
        subtitle: "Six sets of four 7/3 one-arm repeaters per side, with 2m set recovery.",
        level: "Advanced",
        sourceLabel: "Alex Megos finger-training power-endurance protocol (reported by Eric Hörst)",
        sourceURL: URL(string: "https://trainingforclimbing.com/alex-megos-finger-training-power-endurance-protocol/")!,
        provenance: .adapted,
        boardID: nil,
        steps: numbered({
            var steps: [WorkoutStep] = []

            for set in 1...6 {
                for side in [WorkoutSide.left, .right] {
                    for repetition in 1...4 {
                        steps.append(
                            WorkoutStep(
                                id: "megos-7-3-set-\(set)-\(side.rawValue)-rep-\(repetition)",
                                number: 0,
                                title: "Megos 7/3 · set \(set) · \(side.rawValue) · rep \(repetition) of 4",
                                instruction: "Hang one-armed from a comfortable 20–24 mm edge for 7 seconds.",
                                accessory: "7s hang · 3s rest",
                                duration: 10,
                                phase: .hang,
                                segments: [
                                    WorkoutSegment(
                                        kind: .work,
                                        target: .fromLegacyTargets([megos20to24mmEdgeTarget]),
                                        timing: .fixed,
                                        duration: 7
                                    ),
                                    fixedRest(3)
                                ],
                                gripType: .halfCrimp,
                                handUse: .single,
                                side: side,
                                action: .hang,
                                timedWorkDuration: 7
                            )
                        )
                    }
                }
                if set < 6 {
                    steps.append(
                        recoveryStep(
                            id: "megos-7-3-set-\(set)-recovery",
                            title: "Megos 7/3 · set recovery",
                            duration: 120,
                            accessory: "2m recovery"
                        )
                    )
                }
            }
            return steps
        }())
    )

    /// The Rock Prodigy instructions leave grip identity, grip order, and set
    /// count to the athlete. This one-set template deliberately has no board
    /// target: selecting one would turn a manufacturer choice into an app
    /// prescription. Repeat the template manually for the source's 1–3 sets
    /// on each of approximately 5–10 chosen grips.
    static let rptcRepeaters = TrainingPlan(
        id: "rptc.seven-three-repeaters",
        title: "RPTC · 7/3 Repeaters",
        subtitle: "Self-selected 5–10 grip routine; 1–3 sets per grip.",
        level: "Self-selected",
        sourceLabel: "Rock Prodigy Training Center Use Instructions",
        sourceURL: URL(string: "https://cdn.shopify.com/s/files/1/0282/7557/2841/files/RPTC_Use_Instructions.pdf?v=1588608155")!,
        provenance: .official,
        boardID: nil,
        steps: numbered({
            return (1...7).map { rep in
                let finalRep = rep == 7
                return WorkoutStep(
                    id: "rptc-repeaters-set-rep-\(rep)",
                    number: 0,
                    title: "RPTC repeater set · rep \(rep) of 7",
                    instruction: finalRep
                        ? "Complete the seventh 7-second two-handed dead hang on the grip you selected, then use the table's 2:53 recovery to reach 4:00 from the first hang. The source separately prescribes the following 3-minute rest period between sets; do not treat the table recovery as that rest. Do not pull up or lock off. Use a load that reaches near failure on the final set; change 10 lb between sets and 5 lb for the same set from workout to workout."
                        : "Complete a 7-second two-handed dead hang on the grip you selected, then rest 3 seconds.",
                    accessory: finalRep
                        ? "7s two-handed deadhang · 2m 53s rest to 4:00"
                        : "7s two-handed deadhang · 3s rest",
                    duration: finalRep ? 180 : 10,
                    phase: .hang,
                    timedWorkDuration: 7
                )
            } + [
                WorkoutStep(
                    id: "rptc-repeaters-between-sets-rest",
                    number: 0,
                    title: "RPTC repeater set · between-set rest",
                    instruction: "Rest 3 minutes between sets. If you chose another of the source-permitted 1–3 sets on this grip, begin it after this rest; then move to the next of approximately 5–10 grips.",
                    accessory: "3-minute rest period between sets",
                    duration: 180,
                    phase: .rest)
            ]
        }())
    )

    static let abrahangs = TrainingPlan(
        id: "research.abrahangs",
        title: "Abrahangs",
        subtitle: "Low-intensity feet-supported hang variations.",
        level: "Supplemental",
        sourceLabel: "Lattice Abrahangs protocol",
        sourceURL: URL(string: "https://latticetraining.com/workout/1832c13b-14c1-444c-82a2-e72b22a6fb13/abrahangs-protocol")!,
        provenance: .adapted,
        boardID: nil,
        steps: numbered({
            var steps: [WorkoutStep] = []
            let grips: [(title: String, targets: [ContactRequirement], grip: GripType, fingerConfiguration: FingerConfiguration?)] = [
                ("Half 4 Hang", [lattice20mmEdgePairTarget], .halfCrimp, FingerConfiguration(engagedFingers: [.index, .middle, .ring, .pinky])),
                ("F3 Open Hang", [lattice20mmEdgePairTarget], .openHand, FingerConfiguration(engagedFingers: [.index, .middle, .ring])),
                ("M2 Open Hang", [lattice20mmEdgePairTarget], .openHand, FingerConfiguration(engagedFingers: [.middle, .ring])),
                ("F2 Open Hang", [lattice20mmEdgePairTarget], .openHand, FingerConfiguration(engagedFingers: [.index, .middle])),
                ("B3 Half Hang", [lattice20mmEdgePairTarget], .halfCrimp, FingerConfiguration(engagedFingers: [.middle, .ring, .pinky])),
                ("F3 Half Hang", [lattice20mmEdgePairTarget], .halfCrimp, FingerConfiguration(engagedFingers: [.index, .middle, .ring]))
            ]

            for (index, grip) in grips.enumerated() {
                steps.append(
                    hangStep(
                        id: "abrahangs-grip-\(index + 1)",
                        title: "Abrahang · \(grip.title)",
                        instruction: "Keep both feet supported and the intensity low throughout.",
                        accessory: "Feet supported · 10s hang · 50s rest",
                        active: 10,
                        rest: index < grips.count - 1 ? 50 : 0,
                        targets: grip.targets,
                        gripType: grip.grip,
                        fingerConfiguration: grip.fingerConfiguration,
                        handUse: .double
                    )
                )
            }
            return steps
        }())
    )

    static let horst753 = TrainingPlan(
        id: "coach.horst-seven-fifty-three",
        title: "7–53 Max Hangs",
        subtitle: "Three 7/53 maximal hangs with recovery between sets.",
        level: "Advanced",
        sourceLabel: "Eric Hörst fingerboard protocols",
        sourceURL: URL(string: "https://trainingforclimbing.com/4-fingerboard-strength-protocols-that-work/")!,
        provenance: .adapted,
        boardID: nil,
        steps: numbered({
            var steps: [WorkoutStep] = []
            let grips: [(title: String, targets: [ContactRequirement], grip: GripType)] = [
                ("14–20 mm half crimp", [horst14to20mmEdgeTarget], .halfCrimp),
                ("14–20 mm open edge", [horst14to20mmEdgeTarget], .openHand),
                ("20–30 mm two-finger pocket", [horst20to30mmTwoFingerPocketTarget], .openHand)
            ]

            for (index, grip) in grips.enumerated() {
                for rep in 1...3 {
                    steps.append(
                        hangStep(
                            id: "horst-753-grip-\(index + 1)-rep-\(rep)",
                            title: "7–53 · \(grip.title), rep \(rep)",
                            instruction: "Take a near-maximal 7-second hang, then rest for 53 seconds.",
                            accessory: "7s hang · 53s rest · 3 reps",
                            active: 7,
                            rest: rep < 3 ? 53 : 0,
                            targets: grip.targets,
                            gripType: grip.grip
                        )
                    )
                }
                if index < grips.count - 1 {
                    steps.append(
                        recoveryStep(
                            id: "horst-753-grip-\(index + 1)-recovery",
                            title: "Three-minute grip recovery",
                            duration: 180,
                            accessory: "3m recovery"
                        )
                    )
                }
            }
            return steps
        }())
    )

    static let ladders = TrainingPlan(
        id: "coach.bechtel-three-six-nine",
        title: "3–6–9 Ladders",
        subtitle: "3–6–9 ladder sequence.",
        level: "Intermediate+",
        sourceLabel: "Steve Bechtel 3–6–9 ladder protocol",
        sourceURL: URL(string: "https://strengthclimbing.com/steve-bechtels-3-6-9-ladders/")!,
        provenance: .adapted,
        boardID: nil,
        steps: numbered({
            var steps: [WorkoutStep] = []
            for round in 1...3 {
                for (index, hangSeconds) in [3, 6, 9].enumerated() {
                    steps.append(
                        hangStep(
                            id: "ladders-round-\(round)-\(hangSeconds)",
                            title: "Ladder \(round) · \(hangSeconds) seconds",
                            instruction: "Use a load that allows about 12 seconds at maximum.",
                            accessory: "\(hangSeconds)s hang · 30s rest",
                            active: TimeInterval(hangSeconds),
                            rest: index < 2 ? 30 : 0,
                            targets: [],
                            gripType: nil
                        )
                    )
                }
                if round < 3 {
                    steps.append(
                        recoveryStep(
                            id: "ladders-round-\(round)-recovery",
                            title: "Three-minute ladder recovery",
                            duration: 180,
                            accessory: "3m recovery"
                        )
                    )
                }
            }
            return steps
        }())
    )

    static let densityHangs = TrainingPlan(
        id: "coach.density-hangs",
        title: "Density Hangs",
        subtitle: "Density hangs with a 2:1 work-to-rest relationship.",
        level: "Intermediate+",
        sourceLabel: "Tyler Nelson density hang protocol",
        sourceURL: URL(string: "https://strengthclimbing.com/dr-tyler-nelsons-density-hangs-finger-training-for-rock-climbing/")!,
        provenance: .adapted,
        boardID: nil,
        steps: numbered({
            var steps: [WorkoutStep] = []
            let grips: [(title: String, targets: [ContactRequirement], grip: GripType)] = [
                ("20–35 mm large edge", [densityLargeEdgeTarget], .openHand),
                ("20–35 mm large edge · set B", [densityLargeEdgeTarget], .openHand)
            ]

            for (holdIndex, grip) in grips.enumerated() {
                for set in 1...2 {
                    for rep in 1...3 {
                        steps.append(
                        hangStep(
                            id: "density-hold-\(holdIndex + 1)-set-\(set)-rep-\(rep)",
                            title: "Density · \(grip.title), set \(set), rep \(rep)",
                            instruction: "Hang for 30 seconds, then rest for 15 seconds.",
                            accessory: "30s hang · 15s rest",
                            active: 30,
                            rest: rep < 3 ? 15 : 0,
                            targets: grip.targets,
                            gripType: nil
                        )
                        )
                    }
                    if set < 2 {
                        steps.append(
                        recoveryStep(
                            id: "density-hold-\(holdIndex + 1)-set-\(set)-recovery",
                            title: "Three-minute set recovery",
                            duration: 180,
                            accessory: "3m recovery"
                        )
                        )
                    }
                }
                if holdIndex < grips.count - 1 {
                    steps.append(
                        recoveryStep(
                            id: "density-hold-\(holdIndex + 1)-recovery",
                            title: "Three-minute hold recovery",
                            duration: 180,
                            accessory: "3m recovery"
                        )
                    )
                }
            }
            return steps
        }())
    )

    static let zlagboardEndurance = TrainingPlan(
        id: "device.zlagboard-sixty-sixty",
        title: "Zlagboard 60/60 Endurance",
        subtitle: "Ten 60-second hangs with 60-second rests.",
        level: "Intermediate",
        sourceLabel: "Zlagboard endurance protocol",
        sourceURL: URL(string: "https://strengthclimbing.com/zlagboard-forearm-endurance-workout/")!,
        provenance: .adapted,
        boardID: nil,
        steps: numbered({
            var steps: [WorkoutStep] = []
            for interval in 1...10 {
                steps.append(
                    hangStep(
                        id: "zlagboard-interval-\(interval)",
                        title: "60/60 · interval \(interval)",
                        instruction: "Hang for 60 seconds, then rest for 60 seconds.",
                        accessory: "60s hang · 60s rest",
                        active: 60,
                        rest: interval < 10 ? 60 : 0,
                        targets: [zlagboard20mmEdgeTarget],
                        gripType: nil
                    )
                )
            }
            return steps
        }())
    )

    // MARK: - Source-linked plans requested by the training-plan import audit

    /// A source task with no prescribed duration is still useful in the app,
    /// but its timing must remain manual. The 60-second row is an app preview
    /// default only; the instruction and source audit retain the prescription.
    private static func guidedTask(
        id: String,
        title: String,
        instruction: String,
        accessory: String,
        phase: WorkoutPhase,
        targets: [ContactRequirement] = [],
        duration: TimeInterval = 60,
        timing: WorkoutSegmentTiming = .undefined,
        gripType: GripType? = nil
    ) -> WorkoutStep {
        WorkoutStep(
            id: id,
            number: 0,
            title: title,
            instruction: instruction,
            accessory: accessory,
            duration: duration,
            phase: phase,
            segments: phase == .hang || phase == .pull
                ? [WorkoutSegment(
                    kind: .work,
                    target: .fromLegacyTargets(targets),
                    timing: timing,
                    duration: timing == .fixed ? duration : nil
                )]
                : [],
            gripType: gripType
        )
    }

    private static func conditioningTask(
        id: String,
        title: String,
        instruction: String,
        accessory: String = "",
        duration: TimeInterval = 60
    ) -> WorkoutStep {
        guidedTask(
            id: id,
            title: title,
            instruction: instruction,
            accessory: accessory,
            phase: .conditioning,
            duration: duration
        )
    }

    private static func emomMinute(
        id: String,
        title: String,
        instruction: String,
        work: [(duration: TimeInterval, phase: WorkoutPhase, gripType: GripType?, targets: [ContactRequirement])],
        rest: TimeInterval
    ) -> WorkoutStep {
        let workSegments = work.map {
            WorkoutSegment(
                kind: .work,
                target: .fromLegacyTargets($0.targets),
                timing: .fixed,
                duration: $0.duration
            )
        }
        let segments = workSegments + (rest > 0
            ? [WorkoutSegment(kind: .rest, target: nil, timing: .fixed, duration: rest)]
            : [])
        return WorkoutStep(
            id: id,
            number: 0,
            title: title,
            instruction: instruction,
            accessory: "60s EMOM · rest for the remainder of the minute",
            duration: segments.compactMap(\.duration).reduce(0, +),
            phase: work.first?.phase ?? .conditioning,
            segments: segments,
            gripType: work.first?.gripType
        )
    }

    static let hoopersBetaIntroductory = TrainingPlan(
        id: "hoopers-beta.introductory-home-hangboard",
        title: "Hooper's Beta · Introductory Home Hangboard",
        subtitle: "Introductory hangboard routine with five rounds.",
        level: "Intermediate",
        sourceLabel: "Hooper's Beta · Jason Hooper PT, DPT, OCS, CAFS",
        sourceURL: URL(string: "https://www.hoopersbeta.com/library/hold-hangboard-introductory-routine")!,
        provenance: .adapted,
        boardID: nil,
        steps: numbered({
            var steps: [WorkoutStep] = [
                conditioningTask(id: "hoopers-intro-foam-roll", title: "Warm-up · foam rolling", instruction: "Foam roll before overhead work.") ,
                conditioningTask(id: "hoopers-intro-normal-pull-ups", title: "Warm-up · normal pull-ups", instruction: "Perform 10 normal pull-ups on a jug or pull-up bar, or about 75% of your maximum.", accessory: "10 reps or ~75% max"),
                conditioningTask(id: "hoopers-intro-normal-push-ups", title: "Warm-up · normal push-ups", instruction: "Perform 10–20 normal push-ups, or about 75% of your maximum.", accessory: "10–20 reps or ~75% max"),
                conditioningTask(id: "hoopers-intro-wide-pull-ups", title: "Warm-up · wide pull-ups", instruction: "Perform wide pull-ups on the widest large ledge available; do not use a jug."),
                conditioningTask(id: "hoopers-intro-wide-push-ups", title: "Warm-up · wide push-ups", instruction: "Perform wide push-ups with hands rotated outward as comfortable."),
                conditioningTask(id: "hoopers-intro-narrow-pull-ups", title: "Warm-up · narrow pull-ups", instruction: "Perform narrow pull-ups on a large edge."),
                conditioningTask(id: "hoopers-intro-narrow-push-ups", title: "Warm-up · narrow push-ups", instruction: "Perform narrow push-ups, preferably on fists or as diamond push-ups."),
                hangStep(id: "hoopers-intro-round-1-set-1-hang", title: "Round 1 · submax no-weight hang", instruction: "Hang submaximally with no weight for 30 seconds on a medium-to-large ledge.", accessory: "30s hang · submax · no weight", active: 30, rest: 0, targets: [hoopersMediumToLargeLedgeTarget], gripType: .openHand),
                conditioningTask(id: "hoopers-intro-round-1-set-1-taps", title: "Round 1 · plank shoulder taps", instruction: "Perform 30–40 plank shoulder taps (or thigh taps). Stop if form breaks.", accessory: "30–40 reps", duration: 60),
                hangStep(id: "hoopers-intro-round-1-set-2-hang", title: "Round 1 · submax no-weight hang", instruction: "Repeat the 30-second submaximal no-weight hang on a medium-to-large ledge.", accessory: "30s hang · set 2 of 2", active: 30, rest: 0, targets: [hoopersMediumToLargeLedgeTarget], gripType: .openHand),
                conditioningTask(id: "hoopers-intro-round-1-set-2-taps", title: "Round 1 · plank shoulder taps", instruction: "Perform 30–40 plank shoulder taps (or thigh taps) after the second hang.", accessory: "30–40 reps · set 2 of 2", duration: 60)
            ]

            for set in 1...3 {
                for rep in 1...5 {
                    steps.append(contentsOf: [
                        hangStep(id: "hoopers-intro-round-2-set-\(set)-rep-\(rep)-left", title: "Round 2 · single-arm recruitment pull", instruction: "With the feet on the ground and elbow slightly bent, pull the hangboard down rather than lifting off. Build toward near-max over a 5-second hold on the left hand.", accessory: "5s left · rep \(rep) of 5", active: 5, rest: 0, targets: [hoopersSmallEdgeTarget], gripType: .halfCrimp),
                        hangStep(id: "hoopers-intro-round-2-set-\(set)-rep-\(rep)-right", title: "Round 2 · single-arm recruitment pull", instruction: "Repeat the 5-second single-arm recruitment pull on the right hand. Do not lift off the ground.", accessory: "5s right · rep \(rep) of 5", active: 5, rest: 0, targets: [hoopersSmallEdgeTarget], gripType: .halfCrimp)
                    ])
                }
                steps.append(conditioningTask(id: "hoopers-intro-round-2-set-\(set)-kicks", title: "Round 2 · flutter and scissor kicks", instruction: "Perform 20–30 flutter kicks and 20–30 scissor kicks. Protect your lower back and neck.", accessory: "20–30 each", duration: 90))
            }

            for set in 1...3 {
                steps.append(contentsOf: [
                    hangStep(id: "hoopers-intro-round-3-set-\(set)-hang", title: "Round 3 · submax weighted hang", instruction: "Hang submaximally with weight for 20 seconds in an open-hand position on a medium-to-large ledge.", accessory: "20s hang · submax · weighted", active: 20, rest: 0, targets: [hoopersMediumToLargeLedgeTarget], gripType: .openHand),
                    conditioningTask(id: "hoopers-intro-round-3-set-\(set)-side-plank", title: "Round 3 · side plank with hip abduction", instruction: "Perform about 10 hip-abduction reps on each side.", accessory: "~10 each side", duration: 90)
                ])
            }

            for set in 1...4 {
                steps.append(contentsOf: [
                    hangStep(id: "hoopers-intro-round-4-set-\(set)-hang", title: "Round 4 · minimal-edge hang\(set == 4 ? " (optional set 4)" : "")", instruction: "Hang on the minimal edge for 12 seconds at effort level ±3 seconds. Start the full 3-minute rest immediately after the hold.\(set == 4 ? " This fourth set is optional; stop after three if that is your choice." : "")", accessory: "12s hang · full 3m rest · \(set == 4 ? "optional" : "set \(set) of 3–4")", active: 12, rest: 0, targets: [hoopersSmallEdgeTarget], gripType: .halfCrimp),
                    conditioningTask(id: "hoopers-intro-round-4-set-\(set)-recovery", title: "Round 4 · bird dog and stretches\(set == 4 ? " (optional set 4)" : "")", instruction: "Use the full 3-minute recovery: plank bird dog for approximately 45–60 seconds, then stretch.\(set == 4 ? " Skip this recovery with the optional fourth set." : "")", accessory: "45–60s bird dog · 3m total recovery", duration: 180)
                ])
            }

            for set in 1...4 {
                steps.append(contentsOf: [
                    guidedTask(id: "hoopers-intro-round-5-set-\(set)-pull-ups", title: "Round 5 · hangboard pull-ups (optional set \(set))", instruction: "Use open hands on medium-to-large ledges; vary ledges, offsets, or your favorite ledge pull. Stop after 2–4 total paired sets.", accessory: "Optional · set \(set) of 2–4 total", phase: .pull, targets: [hoopersMediumToLargeLedgeTarget]),
                    conditioningTask(id: "hoopers-intro-round-5-set-\(set)-hollow", title: "Round 5 · hollow rock/hold (paired optional set \(set))", instruction: "Within the same optional set, perform 10–20 hollow rocks, then hold. Keep a stable spine; stop or regress if your back feels it. Stop Round 5 after 2–4 total paired sets.", accessory: "Optional · 10–20 reps then hold")
                ])
            }
            return steps
        }())
    )

    static let methodRepeaters = TrainingPlan(
        id: "method.intermediate-hangboarding.repeaters",
        title: "Method Climbing · Intermediate Repeaters",
        subtitle: "Five rounds of 5–7-second repeaters.",
        level: "Intermediate",
        sourceLabel: "Method Climbing · Intermediate Hangboarding",
        sourceURL: URL(string: "https://methodclimb.com/intermediate-hangboarding/")!,
        provenance: .adapted,
        boardID: nil,
        steps: numbered({
            var steps: [WorkoutStep] = []
            for round in 1...5 {
                for rep in 1...5 {
                    steps.append(
                        hangStep(
                            id: "method-repeaters-round-\(round)-rep-\(rep)",
                            title: "Repeaters · round \(round), rep \(rep)",
                            instruction: "Hang for 5–7 seconds, rest for 5–7 seconds, and repeat five times per round.",
                            accessory: "7s hang · 7s rest",
                            active: 7,
                            rest: rep < 5 ? 7 : 0,
                            targets: [methodRepeaters15to20mmEdgeTarget],
                            gripType: .halfCrimp
                        )
                    )
                }
                if round < 5 {
                    steps.append(recoveryStep(id: "method-repeaters-round-\(round)-recovery", title: "Repeaters · round recovery", duration: 105, accessory: "105s recovery"))
                }
            }
            return steps
        }())
    )

    static let methodEMOM = TrainingPlan(
        id: "method.intermediate-hangboarding.emom",
        title: "Method Climbing · Intermediate 10-minute EMOM",
        subtitle: "Ten-minute hangboard session.",
        level: "Intermediate",
        sourceLabel: "Method Climbing · Intermediate Hangboarding",
        sourceURL: URL(string: "https://methodclimb.com/intermediate-hangboarding/")!,
        provenance: .adapted,
        boardID: nil,
        steps: numbered([
            emomMinute(id: "method-emom-minute-1", title: "Minute 1 · 20mm hang", instruction: "Hang for 20 seconds on 20mm, then rest for the remainder of the minute.", work: [(20, .hang, .halfCrimp, [method20mmEdgeTarget])], rest: 40),
            emomMinute(id: "method-emom-minute-2", title: "Minute 2 · deep three-finger pocket + jug pull-ups", instruction: "Hang for 15 seconds on deep three-finger pockets, then do 3 pull-ups on jugs.", work: [(15, .hang, .openHand, [methodDeepThreeFingerPocketTarget]), (15, .pull, nil, [methodJugTarget])], rest: 30),
            emomMinute(id: "method-emom-minute-3", title: "Minute 3 · 20mm hang + jug knee raises", instruction: "Hang for 10 seconds on 20mm, then do 5 knee raises on jugs.", work: [(10, .hang, .halfCrimp, [method20mmEdgeTarget]), (5, .pull, nil, [methodJugTarget])], rest: 45),
            emomMinute(id: "method-emom-minute-4", title: "Minute 4 · bent-arm 15mm hang", instruction: "Hold a bent-arm hang for 15 seconds on 15mm, then rest for the remainder.", work: [(15, .hang, .halfCrimp, [method15mmEdgeTarget])], rest: 45),
            emomMinute(id: "method-emom-minute-5", title: "Minute 5 · sloper hang + jug pull-ups", instruction: "Hang for 10 seconds on a sloper, then do 3 pull-ups on jugs.", work: [(10, .hang, .openHand, [methodSloperTarget]), (15, .pull, nil, [methodJugTarget])], rest: 35),
            emomMinute(id: "method-emom-minute-6", title: "Minute 6 · medium three-finger pocket", instruction: "Hang for 10 seconds on medium three-finger pockets, then rest for the remainder.", work: [(10, .hang, .openHand, [methodMediumThreeFingerPocketTarget])], rest: 50),
            emomMinute(id: "method-emom-minute-7", title: "Minute 7 · offset pull-ups", instruction: "Do 3 offset pull-ups with one hand on a jug and the other on a small edge.", work: [(15, .pull, nil, [methodJugTarget]), (15, .pull, nil, [methodSmallEdgeTarget])], rest: 30),
            emomMinute(id: "method-emom-minute-8", title: "Minute 8 · 15mm hang", instruction: "Hang for 25 seconds on a 15mm edge, then rest for the remainder.", work: [(25, .hang, .halfCrimp, [method15mmEdgeTarget])], rest: 35),
            emomMinute(id: "method-emom-minute-9", title: "Minute 9 · 20mm hang + jug knee raises", instruction: "Hang for 20 seconds on 20mm, then do 10 knee raises on jugs.", work: [(20, .hang, .halfCrimp, [method20mmEdgeTarget]), (10, .pull, nil, [methodJugTarget])], rest: 30),
            guidedTask(id: "method-emom-minute-10", title: "Minute 10 · max sloper", instruction: "Take a max hang on a sloper.", accessory: "Max effort · stopwatch", phase: .hang, targets: [methodSloperTarget], duration: 60, timing: .stopwatch, gripType: .openHand)
        ])
    )

    static let reiHangboardSample = TrainingPlan(
        id: "rei.hangboard-sample-workout",
        title: "REI · Hangboard Sample Workout",
        subtitle: "Five-grip hangboard workout with recovery between grips.",
        level: "Intermediate",
        sourceLabel: "REI Expert Advice · How to Use a Hangboard to Train for Rock Climbing",
        sourceURL: URL(string: "https://www.rei.com/learn/expert-advice/how-to-use-a-hangboard-to-train-for-rock-climbing.html")!,
        provenance: .adapted,
        boardID: nil,
        steps: numbered({
            var steps: [WorkoutStep] = [
                guidedTask(id: "rei-sample-warm-up", title: "Warm-up", instruction: "Warm up with 20–30 minutes of easy climbing or light traversing, OR use 20–30-second dead hangs on the biggest holds plus several pull-up sets.", accessory: "20–30m easy climbing OR 20–30s big-hold hangs + pull-up sets", phase: .conditioning, duration: 1500, timing: .stopwatch)
            ]
            let grips: [(title: String, grip: GripType, targets: [ContactRequirement])] = [
                ("Jug", .openHand, [ContactRequirement.kind(.jug)]),
                ("Three-finger pocket", .openHand, [ContactRequirement(kind: .pocket, fingerCapacity: 3)]),
                ("Medium edge", .openHand, [mediumEdgeTarget]),
                ("Medium pinch", .openHand, [ContactRequirement(kind: .pinch, depth: .category(.medium))]),
                ("Large sloper", .openHand, [ContactRequirement(kind: .sloper, depth: .category(.large))])
            ]
            for (index, grip) in grips.enumerated() {
                for rep in 1...6 {
                    steps.append(hangStep(id: "rei-sample-\(index + 1)-rep-\(rep)", title: "\(grip.title) · rep \(rep)", instruction: "Hang for 7–10 seconds, rest for 5 seconds, and repeat six times. Stop at pain.", accessory: "7s hang · 5s rest", active: 7, rest: rep < 6 ? 5 : 0, targets: grip.targets, gripType: grip.grip))
                }
                if index < grips.count - 1 {
                    steps.append(recoveryStep(id: "rei-sample-\(index + 1)-recovery", title: "Three-minute grip recovery", duration: 180, accessory: "3m recovery · rest a full day or two before hard finger training"))
                }
            }
            steps.append(conditioningTask(id: "rei-sample-recovery", title: "Light stretching and recovery", instruction: "Finish with light stretching and recovery. Rest a full day or two before another hard finger-training session, and stop immediately if you feel pain."))
            return steps
        }())
    )

    /// Kept as the stable featured-plan symbol used by navigation fallbacks.
    static let metoliusTenMinute = metoliusEntry

    static let all: [TrainingPlan] = {
        let metoliusPlans = [metoliusEntry, metoliusIntermediate, metoliusAdvanced]
        let boardSpecificMetoliusPlans = [
            metoliusContactEntry,
            metoliusContactIntermediate,
            metoliusContactAdvanced,
            metoliusSimulator3DEntry,
            metoliusSimulator3DIntermediate,
            metoliusSimulator3DAdvanced,
            metoliusRockRing
        ]
        let officialPlans = boardSpecificMetoliusPlans + [rptcRepeaters]
        let adaptedPlans = [
            maxHangs,
            forceF80,
            forceF100,
            evaIntHangs,
            repeaters,
            megoOneArmSevenThree,
            abrahangs,
            horst753,
            ladders,
            densityHangs,
            zlagboardEndurance,
            hoopersBetaIntroductory,
            methodRepeaters,
            methodEMOM,
            reiHangboardSample
        ]

        #if DEBUG
        assert(metoliusPlans.count == 3, "The Metolius guide has three routines")
        for plan in metoliusPlans {
            assert(plan.provenance == .adapted)
            assert(plan.sourceURL == sourceURL)
            assert(plan.subtitle == adaptationNote)
            assert(plan.duration == 600)
            assert(plan.steps.count > 10)
            assert(plan.steps.map(\.number) == Array(1...plan.steps.count))
            assert(Set(plan.steps.map(\.id)).count == plan.steps.count)
            assert(
                plan.steps.allSatisfy { step in
                    if step.phase == .rest {
                        return step.workRequirements.isEmpty && step.timedWorkDuration == nil
                    }
                    let timing = step.segments.first?.timing ?? .fixed
                    return step.segments.allSatisfy { segment in
                        switch segment.kind {
                        case .rest:
                            return segment.target == nil
                        case .work:
                            // Generic Metolius work keeps authored semantic
                            // requirements (or explicit self-selected when empty).
                            return segment.target != nil
                        }
                    }
                        && (
                        timing == .fixed
                            ? step.timedWorkDuration == step.duration
                            : step.timedWorkDuration == nil
                    )
                }
            )
            for minute in 1...10 {
                let cycleSteps = plan.steps.filter { $0.id.contains(".minute-\(minute).") }
                assert(!cycleSteps.isEmpty)
                assert(cycleSteps.reduce(0) { $0 + $1.duration } <= MetoliusCycleBuilder.cycleDuration)
                assert(cycleSteps.reduce(0) { $0 + $1.duration } == MetoliusCycleBuilder.cycleDuration)
            }
        }
        assert(boardSpecificMetoliusPlans.count == 7, "The Contact, Simulator 3D, and Rock Ring guides have seven routines")
        for plan in boardSpecificMetoliusPlans {
            assert(plan.provenance == .official)
            assert(plan.duration == 600)
            assert(plan.steps.count == 10)
            assert(plan.steps.allSatisfy { $0.duration == MetoliusCycleBuilder.cycleDuration })
            assert(plan.steps.allSatisfy { $0.timedWorkDuration == nil })
            assert(plan.steps.map(\.number) == Array(1...10))
            assert(Set(plan.steps.map(\.id)).count == 10)
            assert(
                plan.boardID == BundledPlanContactRequirements.metoliusContactBoardID ||
                    plan.boardID == BundledPlanContactRequirements.metoliusSimulator3DBoardID ||
                    plan.boardID == BundledPlanContactRequirements.metoliusRockRingBoardID
            )
        }
        assert(officialPlans.allSatisfy { $0.provenance == .official })
        assert(adaptedPlans.allSatisfy { $0.provenance == .adapted })

        let plans = metoliusPlans + officialPlans + adaptedPlans
        assert(Set(plans.map(\.id)).count == plans.count)
        for plan in plans {
            assert(Set(plan.steps.map(\.id)).count == plan.steps.count)

            if let boardID = plan.boardID {
                assert(BoardCatalog.all.contains { $0.id == boardID })
            }
            if let boardID = plan.boardID {
                let board = BoardCatalog.board(for: boardID)
                assert(
                    plan.steps.allSatisfy { step in
                        step.workRequirements.allSatisfy {
                            (try? ContactResolver.resolve($0, step: step, board: board)) != nil
                        }
                    },
                    "The declared board cannot run \(plan.id)"
                )
            }
        }
        #endif

        return metoliusPlans + officialPlans + adaptedPlans
    }()
}
