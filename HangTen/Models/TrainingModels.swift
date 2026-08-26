import Foundation
import SwiftUI

struct HoldFrame: Hashable {
    let x: CGFloat
    let y: CGFloat
    let width: CGFloat
    let height: CGFloat

    var rect: CGRect {
        CGRect(x: x, y: y, width: width, height: height)
    }
}

/// One independently shaped contact surface belonging to a physical hold.
struct BoardHoldPiece: Identifiable, Hashable {
    let id: String
    let holdID: String
    let frame: CGRect
    let shape: BoardShape
    let treatment: BoardHoldTreatment

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

/// The one path source used for normal contact, highlighting, and hit testing.
struct BoardHoldPathShape: Shape {
    let pieces: [BoardHoldPiece]

    func path(in rect: CGRect) -> Path {
        pieces.reduce(into: Path()) { path, piece in
            path.addPath(piece.path(in: rect))
        }
    }
}

enum BoardHoldTreatment: Hashable {
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

    var id: String { rawValue }

    var label: String {
        switch self {
        case .jug: "Jugs"
        case .edge: "Edges"
        case .pocket: "Pockets"
        case .pinch: "Pinches"
        case .sloper: "Sloper"
        }
    }

    var detailLabel: String {
        switch self {
        case .jug: "Jug"
        case .edge: "Edge"
        case .pocket: "Pocket"
        case .pinch: "Pinch"
        case .sloper: "Sloper"
        }
    }

    var tint: Color {
        switch self {
        case .jug: .holdBlue
        case .edge: .holdOrange
        case .pocket: .holdPurple
        case .pinch: .holdRed
        case .sloper: .holdTeal
        }
    }
}

enum HoldCueStyle: String, Codable, Hashable {
    case outerJug
    case slot
    case pinch
    case rounded
}

/// Manufacturer routines often name a hold by function instead of by board
/// ID. Features let a board declare the closest physical match once, keeping
/// routine content unchanged as more boards are added.
enum HoldFeature: String, CaseIterable, Codable, Hashable, Identifiable {
    case jug
    case roundSloper
    case largeSlope
    case largeEdge
    case mediumEdge
    case smallEdge
    case pocket
    case flatEdge
    case incutEdge
    case largeOpenHandRail
    case thinCrimp
    case slot
    case widePinch
    case mediumPinch
    case smallPinch

    var id: String { rawValue }

    var label: String {
        switch self {
        case .jug: "Jug"
        case .roundSloper: "Round sloper"
        case .largeSlope: "Large sloper"
        case .largeEdge: "Large edge"
        case .mediumEdge: "Medium edge"
        case .smallEdge: "Small edge"
        case .pocket: "Pocket"
        case .flatEdge: "Flat edge"
        case .incutEdge: "Incut edge"
        case .largeOpenHandRail: "Large open-hand rail"
        case .thinCrimp: "Thin crimp"
        case .slot: "Slot"
        case .widePinch: "Wide pinch"
        case .mediumPinch: "Medium pinch"
        case .smallPinch: "Small pinch"
        }
    }

    enum FeatureGroup: Hashable {
        case edge
        case pocket
        case sloper
        case pinch
        case other
    }

    /// One canonical row per case: physical kind and cross-kind substitution
    /// group, kept together so adding a case can't leave the two properties
    /// out of sync with each other. Finger count is real per-hold/per-target
    /// data (`BoardHold.fingerCapacity`, `HoldTarget.fingerCapacity`), not
    /// something derived from a feature's identity.
    private struct Physicality {
        let holdKind: HoldKind
        let featureGroup: FeatureGroup
    }

    private var physicality: Physicality {
        switch self {
        case .jug:
            Physicality(holdKind: .jug, featureGroup: .other)
        case .roundSloper:
            Physicality(holdKind: .sloper, featureGroup: .sloper)
        case .largeSlope:
            Physicality(holdKind: .sloper, featureGroup: .sloper)
        case .largeEdge:
            Physicality(holdKind: .edge, featureGroup: .edge)
        case .mediumEdge:
            Physicality(holdKind: .edge, featureGroup: .edge)
        case .smallEdge:
            Physicality(holdKind: .edge, featureGroup: .edge)
        case .pocket:
            Physicality(holdKind: .pocket, featureGroup: .pocket)
        case .flatEdge:
            Physicality(holdKind: .edge, featureGroup: .edge)
        case .incutEdge:
            Physicality(holdKind: .edge, featureGroup: .edge)
        case .largeOpenHandRail:
            Physicality(holdKind: .edge, featureGroup: .other)
        case .thinCrimp:
            Physicality(holdKind: .edge, featureGroup: .edge)
        case .slot:
            Physicality(holdKind: .edge, featureGroup: .edge)
        case .widePinch:
            Physicality(holdKind: .pinch, featureGroup: .pinch)
        case .mediumPinch:
            Physicality(holdKind: .pinch, featureGroup: .pinch)
        case .smallPinch:
            Physicality(holdKind: .pinch, featureGroup: .pinch)
        }
    }

    var featureGroup: FeatureGroup { physicality.featureGroup }
    var holdKind: HoldKind { physicality.holdKind }
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

struct BoardHold: Identifiable, Hashable {
    let id: String
    let name: String
    let kind: HoldKind
    let geometry: [BoardHoldPiece]
    let gripType: GripType?
    let fingerCapacity: Int?
    let handCapacity: Int?
    let frame: HoldFrame
    let sizeMillimeters: Double?
    let depthRangeMillimeters: ClosedRange<Double>?
    let features: Set<HoldFeature>?
    let presentationID: String

    static let validFingerCapacityRange = 1...4
    static let validHandCapacityRange = 1...2

    enum DepthMeasurement: Equatable {
        case none
        case fixed(Double)
        case continuous(ClosedRange<Double>)

        init?(
            sizeMillimeters: Double?,
            depthRangeMillimeters: ClosedRange<Double>?
        ) {
            switch (sizeMillimeters, depthRangeMillimeters) {
            case (nil, nil):
                self = .none
            case (let size?, nil):
                self = .fixed(size)
            case (nil, let range?):
                self = .continuous(range)
            case (.some, .some):
                return nil
            }
        }
    }

    init(
        id: String,
        name: String,
        kind: HoldKind,
        geometry: [BoardHoldPiece],
        sizeMillimeters: Double? = nil,
        gripType: GripType? = nil,
        fingerCapacity: Int? = nil,
        handCapacity: Int? = nil,
        depthRangeMillimeters: ClosedRange<Double>? = nil,
        features: Set<HoldFeature>? = nil,
        presentationID: String = BoardPresentation.primaryID
    ) {
        precondition(!geometry.isEmpty, "BoardHold geometry must include at least one piece.")
        guard let depthMeasurement = DepthMeasurement(
            sizeMillimeters: sizeMillimeters,
            depthRangeMillimeters: depthRangeMillimeters
        ) else {
            preconditionFailure("BoardHold must not specify both a size and depth range.")
        }
        if let fingerCapacity {
            precondition(
                Self.validFingerCapacityRange.contains(fingerCapacity),
                "BoardHold fingerCapacity must be in \(Self.validFingerCapacityRange)."
            )
        }
        if let handCapacity {
            precondition(
                Self.validHandCapacityRange.contains(handCapacity),
                "BoardHold handCapacity must be in \(Self.validHandCapacityRange)."
            )
        }

        self.id = id
        self.name = name
        self.kind = kind
        self.geometry = geometry
        self.gripType = gripType
        self.fingerCapacity = fingerCapacity
        self.handCapacity = handCapacity
        let firstFrame = geometry[0].frame
        let union = geometry.dropFirst().reduce(firstFrame) { $0.union($1.frame) }
        self.frame = HoldFrame(
            x: union.minX,
            y: union.minY,
            width: union.width,
            height: union.height
        )
        switch depthMeasurement {
        case .none:
            self.sizeMillimeters = nil
            self.depthRangeMillimeters = nil
        case .fixed(let size):
            self.sizeMillimeters = size
            self.depthRangeMillimeters = nil
        case .continuous(let range):
            self.sizeMillimeters = nil
            self.depthRangeMillimeters = range
        }
        self.features = features
        self.presentationID = presentationID
    }

    /// Narrow source compatibility for hand-built workout and test fixtures.
    /// Package decoding uses the geometry initializer above and never reaches
    /// this frame-only path or its retired presentation arguments.
    init(
        id: String,
        name: String,
        shortLabel _: String,
        detail _: String,
        kind: HoldKind,
        frame: HoldFrame,
        sizeMillimeters: Double? = nil,
        gripType: GripType? = nil,
        fingerCapacity: Int? = nil,
        handCapacity: Int? = nil,
        cueStyle _: HoldCueStyle? = nil,
        depthRangeMillimeters: ClosedRange<Double>? = nil,
        features: Set<HoldFeature>? = nil
    ) {
        self.init(
            id: id,
            name: name,
            kind: kind,
            geometry: [
                BoardHoldPiece(
                    id: "\(id)-geometry-0",
                    holdID: id,
                    frame: frame.rect,
                    shape: .roundedRect(cornerRadiusFraction: 0),
                    treatment: .surface
                )
            ],
            sizeMillimeters: sizeMillimeters,
            gripType: gripType,
            fingerCapacity: fingerCapacity,
            handCapacity: handCapacity,
            depthRangeMillimeters: depthRangeMillimeters,
            features: features,
            presentationID: BoardPresentation.primaryID
        )
    }

    /// True when this hold declares any of `features`, and (when specified)
    /// also has the exact `fingerCapacity`. Shared by plan and custom-routine
    /// validation so their matching rules can't drift apart.
    func matches(anyOf features: some Collection<HoldFeature>, fingerCapacity: Int?) -> Bool {
        guard self.features?.contains(where: features.contains) == true else { return false }
        guard let fingerCapacity else { return true }
        return self.fingerCapacity == fingerCapacity
    }
}

struct BoardPresentation: Identifiable, Hashable {
    static let primaryID = "primary"

    let id: String
    let name: String
    let aspectRatio: CGFloat
    let isDefault: Bool
}

struct TrainingBoard: Identifiable, Hashable {
    let id: String
    let manufacturer: String
    let name: String
    let subtitle: String
    let dimensions: String
    let aspectRatio: CGFloat
    let holds: [BoardHold]
    let presentations: [BoardPresentation]
    /// Board-owned semantic targets loaded alongside the physical hold data.
    /// The empty default preserves hand-built board fixtures and catalog entries.
    let semanticHolds: [String: SemanticHoldMappingDefinition]
    let productURL: URL
    /// Optional board-specific reference art. Boards without a photo use the
    /// vector fallback, so adding another board does not require an image.
    let photoAssetName: String?

    init(
        id: String,
        manufacturer: String,
        name: String,
        subtitle: String,
        dimensions: String,
        aspectRatio: CGFloat,
        holds: [BoardHold],
        semanticHolds: [String: SemanticHoldMappingDefinition] = [:],
        productURL: URL,
        photoAssetName: String?,
        presentations: [BoardPresentation] = []
    ) {
        self.id = id
        self.manufacturer = manufacturer
        self.name = name
        self.subtitle = subtitle
        self.dimensions = dimensions
        self.aspectRatio = aspectRatio
        self.holds = holds
        self.presentations = presentations.isEmpty
            ? [
                BoardPresentation(
                    id: BoardPresentation.primaryID,
                    name: "Primary",
                    aspectRatio: aspectRatio,
                    isDefault: true
                )
            ]
            : presentations
        self.semanticHolds = semanticHolds
        self.productURL = productURL
        self.photoAssetName = photoAssetName
    }

    var defaultPresentation: BoardPresentation {
        presentations.first(where: \.isDefault) ?? presentations[0]
    }

    func presentation(id: String?) -> BoardPresentation? {
        guard let id else { return nil }
        return presentations.first { $0.id == id }
    }
}

struct HoldTarget: Hashable {
    let holdIDs: [String]
    let kind: HoldKind?
    let feature: HoldFeature?
    let fallbackFeatures: [HoldFeature]
    /// The finger count this target wants, matched against
    /// `BoardHold.fingerCapacity`. Real, author-specified data — not derived
    /// from `feature`'s name (see e.g. `.pocket`, which covers holds of any
    /// finger count on its own).
    let fingerCapacity: Int?

    init(
        holdIDs: [String],
        kind: HoldKind?,
        feature: HoldFeature?,
        fallbackFeatures: [HoldFeature],
        fingerCapacity: Int?
    ) {
        if let fingerCapacity {
            precondition(
                BoardHold.validFingerCapacityRange.contains(fingerCapacity),
                "HoldTarget fingerCapacity must be in \(BoardHold.validFingerCapacityRange)."
            )
        }
        self.holdIDs = holdIDs
        self.kind = kind
        self.feature = feature
        self.fallbackFeatures = fallbackFeatures
        self.fingerCapacity = fingerCapacity
    }

    static func ids(_ holdIDs: String...) -> HoldTarget {
        HoldTarget(holdIDs: holdIDs, kind: nil, feature: nil, fallbackFeatures: [], fingerCapacity: nil)
    }

    static func ids(_ holdIDs: [String]) -> HoldTarget {
        HoldTarget(holdIDs: holdIDs, kind: nil, feature: nil, fallbackFeatures: [], fingerCapacity: nil)
    }

    static func kind(_ kind: HoldKind) -> HoldTarget {
        HoldTarget(holdIDs: [], kind: kind, feature: nil, fallbackFeatures: [], fingerCapacity: nil)
    }

    static func feature(
        _ feature: HoldFeature,
        fingerCapacity: Int? = nil,
        fallback fallbackFeatures: HoldFeature...
    ) -> HoldTarget {
        HoldTarget(
            holdIDs: [],
            kind: nil,
            feature: feature,
            fallbackFeatures: fallbackFeatures,
            fingerCapacity: fingerCapacity
        )
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

struct WorkoutSegment: Hashable {
    let kind: WorkoutSegmentKind
    let targets: [HoldTarget]
    var target: HoldTarget? { targets.first }
    let timing: WorkoutSegmentTiming
    let duration: TimeInterval?

    init(
        kind: WorkoutSegmentKind,
        target: HoldTarget?,
        timing: WorkoutSegmentTiming,
        duration: TimeInterval?
    ) {
        self.init(
            kind: kind,
            targets: target.map { [$0] } ?? [],
            timing: timing,
            duration: duration
        )
    }

    init(
        kind: WorkoutSegmentKind,
        targets: [HoldTarget],
        timing: WorkoutSegmentTiming,
        duration: TimeInterval?
    ) {
        self.kind = kind
        self.targets = targets
        self.timing = timing
        self.duration = duration
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

struct WorkoutStep: Identifiable, Hashable {
    let id: String
    let number: Int
    let title: String
    let instruction: String
    let accessory: String
    let duration: TimeInterval
    let phase: WorkoutPhase
    let targets: [HoldTarget]
    let segments: [WorkoutSegment]
    let gripType: GripType?
    let fingerConfiguration: FingerConfiguration?
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
        targets: [HoldTarget],
        segments: [WorkoutSegment] = [],
        gripType: GripType? = nil,
        fingerConfiguration: FingerConfiguration? = nil,
        timedWorkDuration: TimeInterval? = nil
    ) {
        self.id = id
        self.number = number
        self.title = title
        self.instruction = instruction
        self.accessory = accessory
        self.duration = duration
        self.phase = phase
        self.targets = targets
        self.segments = segments
        self.gripType = gripType
        self.fingerConfiguration = fingerConfiguration
        self.timedWorkDuration = timedWorkDuration
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
            targets: targets,
            segments: segments,
            gripType: gripType,
            fingerConfiguration: fingerConfiguration,
            timedWorkDuration: timedWorkDuration
        )
    }
}

struct MetoliusTaskDefinition: Hashable {
    let title: String
    let instruction: String
    let accessory: String
    let duration: TimeInterval
    let phase: WorkoutPhase
    let targets: [HoldTarget]
    let gripType: GripType?
    let fingerConfiguration: FingerConfiguration?
    let timing: WorkoutSegmentTiming

    init(
        title: String,
        instruction: String,
        accessory: String,
        duration: TimeInterval,
        phase: WorkoutPhase,
        targets: [HoldTarget],
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
            return try BoardPackageStore()
        } catch {
            fatalError("Bundled board packages could not be loaded: \(error.localizedDescription)")
        }
    }()

    static let all = packageStore.boards

    /// Generic plans (`boardID: nil`) are authored against the same board as
    /// the legacy semantic-hold mappings. Crashes rather than falling back to
    /// an unrelated board, since silently resolving generic targets against
    /// the wrong board would misrepresent every hold callout in those plans.
    static let defaultBoard: TrainingBoard = {
        guard let boardID = LegacyPlanSeedBoardMappings.all.first?.boardID else {
            fatalError("LegacyPlanSeedBoardMappings.all is empty.")
        }
        guard let board = packageStore.board(id: boardID) else {
            fatalError("The bundled board catalog is missing the legacy default board '\(boardID)'.")
        }
        return board
    }()

    static func board(for id: String?) -> TrainingBoard {
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
        targets: [HoldTarget],
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
        targets: [HoldTarget],
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
        targets: [HoldTarget],
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
        targets: [HoldTarget],
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
        targets: [HoldTarget],
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
                targets: task.targets,
                segments: task.targets.isEmpty ? [] : [
                    WorkoutSegment(
                        kind: .work,
                        targets: task.targets,
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
                    targets: [],
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
        targets: [HoldTarget],
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

/// Board-specific target vocabulary retained by the plan migration seed.
/// Physical board packages intentionally contain no training-plan semantics.
enum LegacyPlanSeedBoardMappings {
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

        fileprivate var holdIDs: [String] {
            switch self {
            case .anyHold:
                [
                    "pinch-left", "jug-left", "flat-sloper-center", "pocket-4-left", "pocket-5-left",
                    "pocket-6-left", "pocket-7-left", "pocket-8-left", "pocket-9-left", "pocket-10-left",
                    "pocket-11-left", "pocket-12-left", "pocket-13-left", "pocket-14-left", "edge-16-center",
                    "edge-17-center", "edge-18-center", "edge-19-center", "pocket-14-right", "pocket-13-right",
                    "pocket-12-right", "pocket-11-right", "pocket-10-right", "pocket-9-right", "pocket-8-right",
                    "pocket-7-right", "pocket-6-right", "pocket-5-right", "pocket-4-right", "round-sloper-3-left",
                    "round-sloper-3-right", "jug-right", "pinch-right"
                ]
            case .outerJugs: ["jug-left", "jug-right"]
            case .pinches: ["pinch-left", "pinch-right"]
            case .flatSloper: ["flat-sloper-center"]
            case .roundSlopers: ["round-sloper-3-left", "round-sloper-3-right"]
            case .edge16: ["edge-16-center"]
            case .edge17: ["edge-17-center"]
            case .edge18: ["edge-18-center"]
            case .pocket4: ["pocket-4-left", "pocket-4-right"]
            case .pocket6: ["pocket-6-left", "pocket-6-right"]
            case .pocket7: ["pocket-7-left", "pocket-7-right"]
            case .pocket8: ["pocket-8-left", "pocket-8-right"]
            case .pocket9: ["pocket-9-left", "pocket-9-right"]
            case .pocket11: ["pocket-11-left", "pocket-11-right"]
            case .pocket13: ["pocket-13-left", "pocket-13-right"]
            }
        }
    }

    enum MetoliusSimulator3DTarget {
        case anyHold
        case outerJugs
        case centerJug
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

        fileprivate var holdIDs: [String] {
            switch self {
            case .anyHold:
                [
                    "jug-1-left", "round-sloper-3-left", "jug-14-center", "round-sloper-3-right", "jug-1-right",
                    "pocket-4-left", "edge-5-left", "edge-6-left", "edge-7-left", "pocket-8-left", "pocket-9-left",
                    "pocket-10-left", "edge-11-left", "pocket-12-left", "pocket-13-left", "pocket-15-center",
                    "pocket-16-center", "pocket-17-center", "pocket-18-center", "pocket-13-right", "pocket-12-right",
                    "edge-11-right", "pocket-10-right", "pocket-9-right", "pocket-8-right", "edge-7-right", "edge-6-right",
                    "edge-5-right", "pocket-4-right"
                ]
            case .outerJugs: ["jug-1-left", "jug-1-right"]
            case .centerJug: ["jug-14-center"]
            case .roundSlopers: ["round-sloper-3-left", "round-sloper-3-right"]
            case .edge5: ["edge-5-left", "edge-5-right"]
            case .edge6: ["edge-6-left", "edge-6-right"]
            case .edge7: ["edge-7-left", "edge-7-right"]
            case .edge11: ["edge-11-left", "edge-11-right"]
            case .pocket4: ["pocket-4-left", "pocket-4-right"]
            case .pocket8: ["pocket-8-left", "pocket-8-right"]
            case .pocket9: ["pocket-9-left", "pocket-9-right"]
            case .pocket12: ["pocket-12-left", "pocket-12-right"]
            case .pocket15: ["pocket-15-center"]
            case .pocket17: ["pocket-17-center"]
            case .pocket18: ["pocket-18-center"]
            }
        }
    }

    static func contactTargets(_ groups: MetoliusContactTarget...) -> [HoldTarget] {
        groups.map { .ids($0.holdIDs) }
    }

    static func simulator3DTargets(_ groups: MetoliusSimulator3DTarget...) -> [HoldTarget] {
        groups.map { .ids($0.holdIDs) }
    }

    static let all = [
        BoardMappingDefinition(
            boardID: "metolius.wood-grips-compact-ii",
            semanticHolds: [
                "edge-19": SemanticHoldMappingDefinition(
                    holdIDs: ["edge-19-left", "edge-19-right"]
                ),
                "edge-29": SemanticHoldMappingDefinition(
                    holdIDs: ["edge-29-left", "edge-29-right"]
                ),
                "flat-slopers": SemanticHoldMappingDefinition(
                    holdIDs: ["sloper-flat-left", "sloper-flat-right"]
                ),
                "outer-jugs": SemanticHoldMappingDefinition(
                    holdIDs: ["jug-left", "jug-right"]
                ),
                "pocket-19-four": SemanticHoldMappingDefinition(
                    holdIDs: ["pocket-19-four-center"]
                ),
                "pocket-19-three": SemanticHoldMappingDefinition(
                    holdIDs: ["pocket-19-three-left", "pocket-19-three-right"]
                ),
                "pocket-19-two": SemanticHoldMappingDefinition(
                    holdIDs: ["pocket-19-two-left", "pocket-19-two-right"]
                ),
                "pocket-29-four": SemanticHoldMappingDefinition(
                    holdIDs: ["pocket-29-four-center"]
                ),
                "pocket-29-three": SemanticHoldMappingDefinition(
                    holdIDs: ["pocket-29-three-left", "pocket-29-three-right"]
                ),
                "pocket-29-two": SemanticHoldMappingDefinition(
                    holdIDs: ["pocket-29-two-left", "pocket-29-two-right"]
                ),
                "round-sloper": SemanticHoldMappingDefinition(
                    holdIDs: ["sloper-round-center"]
                )
            ]
        )
    ]

    static func required(containingSemantic semanticID: String) -> BoardMappingDefinition {
        let matches = all.filter { $0.semanticHolds[semanticID] != nil }
        precondition(
            matches.count == 1,
            "Expected exactly one plan mapping with \(semanticID) semantics."
        )
        return matches[0]
    }
}

enum LegacyPlanSeedCatalog {
    static let repeaterStepIDPrefix = "repeaters-grip-"

    private static let sourceURL = URL(
        string: "https://www.metoliusclimbing.com/pages/10-minute-sequences-hangboard-training-guide"
    )!

    private static let sourceLabel = "Metolius 10 Minute Sequences — Hangboard Training Guide"

    private static let adaptationNote = "Ten 60-second hangboard sequences."

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
        _ minutes: [(instruction: String, targets: [HoldTarget], phase: WorkoutPhase)]
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
                targets: minute.targets,
                segments: minute.targets.isEmpty ? [] : [
                    WorkoutSegment(
                        kind: .work,
                        targets: minute.targets,
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
        minutes: [(instruction: String, targets: [HoldTarget], phase: WorkoutPhase)]
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
        boardID: LegacyPlanSeedBoardMappings.metoliusContactBoardID,
        minutes: [
            ("1 pull-up outer jugs (2); 10 second hang center edge (17).", LegacyPlanSeedBoardMappings.contactTargets(.outerJugs, .edge17), .pull),
            ("1 pull-up deep four finger edge (4), stay on — 10 s bent arm hang (90°), stay on — 1 more pull-up.", LegacyPlanSeedBoardMappings.contactTargets(.pocket4), .pull),
            ("2 offset pull-ups (1 arm each) outer jug (2) & deep three finger pockets (6).", LegacyPlanSeedBoardMappings.contactTargets(.outerJugs, .pocket6), .pull),
            ("6 s. L-hang on any holds (bend knees if needed); 5 s. dead hang pinches (11).", LegacyPlanSeedBoardMappings.contactTargets(.anyHold, .pocket11), .hang),
            ("10 s. dead hang flat sloper (15); 5 knee raises outer jug (2).", LegacyPlanSeedBoardMappings.contactTargets(.flatSloper, .outerJugs), .hang),
            ("16 s. offset hang (8 s. per side) deep edge (17) & med pocket (7).", LegacyPlanSeedBoardMappings.contactTargets(.edge17, .pocket7), .hang),
            ("3 pull-ups any hold.", LegacyPlanSeedBoardMappings.contactTargets(.anyHold), .pull),
            ("10 s. bent arm hang (elbows 90°) deep four finger (3).", LegacyPlanSeedBoardMappings.contactTargets(.roundSlopers), .hang),
            ("1 offset pull-up, jug & pinch (1 & 11), change hands & repeat; 10 s. dead hang deep four finger pockets (3).", LegacyPlanSeedBoardMappings.contactTargets(.pinches, .pocket11, .roundSlopers), .pull),
            ("2 pull-ups any hold; dead hang center edge (17) till failure. Fight hard & don't let go!!", LegacyPlanSeedBoardMappings.contactTargets(.anyHold, .edge17), .hang)
        ]
    )

    static let metoliusContactIntermediate = officialMetoliusPlan(
        id: "metolius.contact.intermediate",
        title: "Metolius Contact · Intermediate",
        level: "Intermediate",
        sourceLabel: "Metolius Contact Training Guide",
        sourceURL: contactSourceURL,
        boardID: LegacyPlanSeedBoardMappings.metoliusContactBoardID,
        minutes: [
            ("3 pull-ups outer jugs (2); 20 second dead hang deep three finger pockets (6).", LegacyPlanSeedBoardMappings.contactTargets(.outerJugs, .pocket6), .pull),
            ("10 s. bent arm (elbows at 90°) hang round sloper (2) — stay on — 2 pull-ups — stay on 10 s. bent arm hang (elbows at 110°).", LegacyPlanSeedBoardMappings.contactTargets(.outerJugs), .hang),
            ("4 offset pull-ups (each arm) outer jugs (2) & deep three finger pockets (6).", LegacyPlanSeedBoardMappings.contactTargets(.outerJugs, .pocket6), .pull),
            ("10 s. L-hang on any holds; 10 s. dead hang on pinches (11).", LegacyPlanSeedBoardMappings.contactTargets(.anyHold, .pocket11), .hang),
            ("10 s. offset hang, deep center edge (17) & med three finger edge (8), reverse holds — repeat.", LegacyPlanSeedBoardMappings.contactTargets(.edge17, .pocket8), .hang),
            ("15 s. offset hang pockets (4) & (13), reverse holds — repeat.", LegacyPlanSeedBoardMappings.contactTargets(.pocket4, .pocket13), .hang),
            ("4 pull-ups deep center edge (17); 10 knee raises any holds.", LegacyPlanSeedBoardMappings.contactTargets(.edge17, .anyHold), .pull),
            ("15 s. dead hang, two finger pockets (7); rest 10 s.; 10 s. hang three finger pockets (9).", LegacyPlanSeedBoardMappings.contactTargets(.pocket7, .pocket9), .hang),
            ("10 s. one arm hang jugs (3), repeat other arm; 4 pull-ups center edge (17).", LegacyPlanSeedBoardMappings.contactTargets(.roundSlopers, .edge17), .hang),
            ("4 pull-ups flat sloper (15); bump out to round sloper (3) & dead hang to failure. Fight hard!!", LegacyPlanSeedBoardMappings.contactTargets(.flatSloper, .roundSlopers), .hang)
        ]
    )

    static let metoliusContactAdvanced = officialMetoliusPlan(
        id: "metolius.contact.advanced",
        title: "Metolius Contact · Advanced",
        level: "Advanced",
        sourceLabel: "Metolius Contact Training Guide",
        sourceURL: contactSourceURL,
        boardID: LegacyPlanSeedBoardMappings.metoliusContactBoardID,
        minutes: [
            ("6 pull-ups round slopers (2); 20 s. dead hang deep two finger pockets (4).", LegacyPlanSeedBoardMappings.contactTargets(.outerJugs, .pocket4), .pull),
            ("15 s. bent arm hang (elbows at 90°) round sloper (2) — stay on — 4 pull-ups — stay on — 15 s. bent arm hang (elbows at 110°).", LegacyPlanSeedBoardMappings.contactTargets(.outerJugs), .hang),
            ("6 offset pull-ups (3 each arm) round sloper (2) & deep two finger pockets (4); 10 s. dead hang medium edge (18).", LegacyPlanSeedBoardMappings.contactTargets(.outerJugs, .pocket4, .edge18), .pull),
            ("15 s. L-hang any holds (hold good form); 15 s. dead hang on pinches (11).", LegacyPlanSeedBoardMappings.contactTargets(.anyHold, .pocket11), .hang),
            ("10 s. dead hang extra shallow three finger pockets (13), stay on; campus to med three finger pocket (9), campus to round slopers (2), hold 15 s.", LegacyPlanSeedBoardMappings.contactTargets(.pocket13, .pocket9, .outerJugs), .hang),
            ("15 s. one arm hang center edge (17); rest 20 s.; repeat other arm.", LegacyPlanSeedBoardMappings.contactTargets(.edge17), .hang),
            ("5 L-sit pull-ups (bend knees if you have to), jugs (1); 20 s. bent arm hang (elbows at 90°), deep two finger pockets (4).", LegacyPlanSeedBoardMappings.contactTargets(.pinches, .pocket4), .pull),
            ("10 s. hang center edges (16, 17), reverse holds — repeat; 3 power pull-ups (use weights or helper for resistance, should just be able to complete final rep).", LegacyPlanSeedBoardMappings.contactTargets(.edge16, .edge17), .hang),
            ("20 s. slight bent arm hang, two finger pockets (7), stay on; bump to round slopers (3), 20 s. dead hang.", LegacyPlanSeedBoardMappings.contactTargets(.pocket7, .roundSlopers), .hang),
            ("8 pull-ups flat sloper (3), bump out to round sloper (3), and dead hang to failure. Fight hard!!", LegacyPlanSeedBoardMappings.contactTargets(.roundSlopers), .hang)
        ]
    )

    static let metoliusSimulator3DEntry = officialMetoliusPlan(
        id: "metolius.simulator-3d.entry",
        title: "Metolius Simulator 3D · Entry",
        level: "Entry",
        sourceLabel: "Metolius Simulator 3D Training Guide",
        sourceURL: simulator3DSourceURL,
        boardID: LegacyPlanSeedBoardMappings.metoliusSimulator3DBoardID,
        subtitle: "Official ten-minute sequence; remaining time rests. Feet on a chair may lower resistance; place it 1'–3' behind the board plane.",
        minutes: [
            ("10 second dead hang, deep flat edge (7).", LegacyPlanSeedBoardMappings.simulator3DTargets(.edge7), .hang),
            ("15 second dead hang + one pull-up, outer jugs (1).", LegacyPlanSeedBoardMappings.simulator3DTargets(.outerJugs), .hang),
            ("2 offset pull-up (1 each arm) center jug (14) & deep three finger pockets (4).", LegacyPlanSeedBoardMappings.simulator3DTargets(.centerJug, .pocket4), .pull),
            ("15 second dead hang, extra deep 3 finger pockets (9).", LegacyPlanSeedBoardMappings.simulator3DTargets(.pocket9), .hang),
            ("12 second dead hang flat slopers (2) & 5 knee raises outer jugs (1).", LegacyPlanSeedBoardMappings.simulator3DTargets(.roundSlopers, .outerJugs), .hang),
            ("16 second offset hang / (8 sec per side), deep pocket (15) & shallow edge (5).", LegacyPlanSeedBoardMappings.simulator3DTargets(.pocket15, .edge5), .hang),
            ("3 pull-ups outer jugs (1).", LegacyPlanSeedBoardMappings.simulator3DTargets(.outerJugs), .pull),
            ("8 second bent arm hang (elbows @ 90), round slopers (3).", LegacyPlanSeedBoardMappings.simulator3DTargets(.roundSlopers), .hang),
            ("1 pull-up & then 10 second hang, ext-deep 3 finger pocket (9).", LegacyPlanSeedBoardMappings.simulator3DTargets(.pocket9), .pull),
            ("Dead hang to failure, any holds.", LegacyPlanSeedBoardMappings.simulator3DTargets(.anyHold), .hang)
        ]
    )

    static let metoliusSimulator3DIntermediate = officialMetoliusPlan(
        id: "metolius.simulator-3d.intermediate",
        title: "Metolius Simulator 3D · Intermediate",
        level: "Intermediate",
        sourceLabel: "Metolius Simulator 3D Training Guide",
        sourceURL: simulator3DSourceURL,
        boardID: LegacyPlanSeedBoardMappings.metoliusSimulator3DBoardID,
        minutes: [
            ("25 second dead hang, medium edge (5).", LegacyPlanSeedBoardMappings.simulator3DTargets(.edge5), .hang),
            ("20 second dead hang, flat slopers (2), 3 pull-ups flat slopers.", LegacyPlanSeedBoardMappings.simulator3DTargets(.roundSlopers), .hang),
            ("15 second bent arm hang, shallow edge (6) & 10 knee raises, jugs (1).", LegacyPlanSeedBoardMappings.simulator3DTargets(.edge6, .outerJugs), .hang),
            ("15 second dead hang flat slope (2), 15 second dead hang round slopers (3).", LegacyPlanSeedBoardMappings.simulator3DTargets(.roundSlopers), .hang),
            ("20 second offset hang, jug (1) & shallow pocket (17), reverse holds — repeat.", LegacyPlanSeedBoardMappings.simulator3DTargets(.outerJugs, .pocket17), .hang),
            ("15 second offset hang, pockets (4 & 9), reverse holds and repeat.", LegacyPlanSeedBoardMappings.simulator3DTargets(.pocket4, .pocket9), .hang),
            ("4 pull-ups, medium edges, 10 knee raises any holds.", LegacyPlanSeedBoardMappings.simulator3DTargets(.edge5, .anyHold), .pull),
            ("30 second dead hang, deep pockets (7).", LegacyPlanSeedBoardMappings.simulator3DTargets(.edge7), .hang),
            ("10 sec one arm hang jugs (1), repeat other arm.", LegacyPlanSeedBoardMappings.simulator3DTargets(.outerJugs), .hang),
            ("5 pull-ups deep edges (7), without dropping off, bump up to round slopers (3) & dead hang till failure.", LegacyPlanSeedBoardMappings.simulator3DTargets(.edge7, .roundSlopers), .hang)
        ]
    )

    static let metoliusSimulator3DAdvanced = officialMetoliusPlan(
        id: "metolius.simulator-3d.advanced",
        title: "Metolius Simulator 3D · Advanced",
        level: "Advanced",
        sourceLabel: "Metolius Simulator 3D Training Guide",
        sourceURL: simulator3DSourceURL,
        boardID: LegacyPlanSeedBoardMappings.metoliusSimulator3DBoardID,
        minutes: [
            ("25 second dead hang shallow edge (6), 5 pull-ups three finger pockets (9).", LegacyPlanSeedBoardMappings.simulator3DTargets(.edge6, .pocket9), .hang),
            ("5 offset pull-ups, pockets (15 & 12), reverse holds repeat.", LegacyPlanSeedBoardMappings.simulator3DTargets(.pocket15, .pocket12), .pull),
            ("45 second dead hang, extra shallow edges (11).", LegacyPlanSeedBoardMappings.simulator3DTargets(.edge11), .hang),
            ("5 offset pull-ups, round sloper (3) & deep pocket (4), reverse holds repeat.", LegacyPlanSeedBoardMappings.simulator3DTargets(.roundSlopers, .pocket4), .pull),
            ("10 second dead hang, x-shallow edges (11), staying on, campus to three finger pockets (9), campus to shallow edges (6), campus to flat slopers (2), hold for 15 seconds.", LegacyPlanSeedBoardMappings.simulator3DTargets(.edge11, .pocket9, .edge6, .roundSlopers), .hang),
            ("15 second one arm hang, round sloper (3), rest 10 seconds, repeat other arm.", LegacyPlanSeedBoardMappings.simulator3DTargets(.roundSlopers), .hang),
            ("5 L-sit pull-ups (bend knees if you have to), jugs (1), 20 second bent arm hang (elbows @ 90), deep two finger pockets (12).", LegacyPlanSeedBoardMappings.simulator3DTargets(.outerJugs, .pocket12), .pull),
            ("20 second slightly bent arm hang, shallow 3 finger pocket (8), stay on, bump to x-deep three finger pockets 25 second dead hang.", LegacyPlanSeedBoardMappings.simulator3DTargets(.pocket8, .pocket9), .hang),
            ("10 second hang center pockets (18 & 17), reverse holds repeat, three power pull-ups (use weights or helper for resistance, should just be able to complete third pull).", LegacyPlanSeedBoardMappings.simulator3DTargets(.pocket18, .pocket17), .hang),
            ("8 fast pull-ups, jugs (1) (keeping form perfect), dead hang round sloper to failure (fighting hard!).", LegacyPlanSeedBoardMappings.simulator3DTargets(.outerJugs, .roundSlopers), .hang)
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
            [MetoliusCycleBuilder.fixed(title: "Jug hang", instruction: "Hang from the jugs for 15 seconds.", duration: 15, phase: .hang, targets: [.feature(.jug)])],
            [MetoliusCycleBuilder.pullUps(count: 1, title: "Round sloper pull-up", instruction: "Do 1 pull-up on a round sloper.", phase: .pull, targets: [.feature(.roundSloper)])],
            [MetoliusCycleBuilder.fixed(title: "Medium-edge hang", instruction: "Hang from a medium edge for 10 seconds.", duration: 10, phase: .hang, targets: [.feature(.mediumEdge)])],
            [MetoliusCycleBuilder.fixed(title: "Pocket hang + shrugs", instruction: "Hang from a pocket for 15 seconds and include 3 shrugs.", duration: 15, phase: .hang, targets: [.feature(.pocket)])],
            [MetoliusCycleBuilder.fixed(title: "Large edge + pull-ups", instruction: "Hang from a large edge for 20 seconds and include 2 pull-ups.", duration: 20, phase: .hang, targets: [.feature(.largeEdge)])],
            [
                MetoliusCycleBuilder.fixed(title: "Round-sloper hang", instruction: "Hang from a round sloper for 10 seconds.", duration: 10, phase: .hang, targets: [.feature(.roundSloper)]),
                MetoliusCycleBuilder.repetitions(count: 5, title: "Pocket knee raises", instruction: "Do 5 knee raises on a pocket.", phase: .pull, targets: [.feature(.pocket)])
            ],
            [MetoliusCycleBuilder.pullUps(count: 4, title: "Large-edge pull-ups", instruction: "Do 4 pull-ups on a large edge.", phase: .pull, targets: [.feature(.largeEdge)])],
            [MetoliusCycleBuilder.fixed(title: "Medium-edge hang", instruction: "Hang from a medium edge for 10 seconds.", duration: 10, phase: .hang, targets: [.feature(.mediumEdge)])],
            [MetoliusCycleBuilder.pullUps(count: 3, title: "Jug pull-ups", instruction: "Do 3 pull-ups on the jugs.", phase: .pull, targets: [.feature(.jug)])],
            [MetoliusCycleBuilder.maxEffort(title: "Maximum sloper hang", instruction: "Hang from a round sloper for as long as you can.", phase: .hang, targets: [.feature(.roundSloper)])]
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
                MetoliusCycleBuilder.fixed(title: "Large-edge hang", instruction: "Hang from a large edge for 15 seconds.", duration: 15, phase: .hang, targets: [.feature(.largeEdge)]),
                MetoliusCycleBuilder.pullUps(count: 3, title: "Large-edge pull-ups", instruction: "Do 3 pull-ups on the large edge.", phase: .pull, targets: [.feature(.largeEdge)])
            ],
            [
                MetoliusCycleBuilder.pullUps(count: 2, title: "Round sloper pull-ups", instruction: "Do 2 pull-ups on a round sloper.", phase: .pull, targets: [.feature(.roundSloper)]),
                MetoliusCycleBuilder.fixed(title: "Medium-edge hang", instruction: "Hang from a medium edge for 20 seconds.", duration: 20, phase: .hang, targets: [.feature(.mediumEdge)])
            ],
            [
                MetoliusCycleBuilder.fixed(title: "Small-edge hang", instruction: "Hang from a small edge for 20 seconds.", duration: 20, phase: .hang, targets: [.feature(.smallEdge)]),
                MetoliusCycleBuilder.fixed(title: "Bent-arm pocket hang", instruction: "Hold a pocket at a 90° bent arm for 15 seconds.", duration: 15, phase: .hang, targets: [.feature(.pocket)])
            ],
            [MetoliusCycleBuilder.fixed(title: "Round-sloper hang", instruction: "Hang from a round sloper for 30 seconds.", duration: 30, phase: .hang, targets: [.feature(.roundSloper)])],
            [
                MetoliusCycleBuilder.fixed(title: "Large-edge hang", instruction: "Hang from a large edge for 20 seconds.", duration: 20, phase: .hang, targets: [.feature(.largeEdge)]),
                MetoliusCycleBuilder.pullUps(count: 4, title: "Pocket pull-ups", instruction: "Do 4 pull-ups on a pocket.", phase: .pull, targets: [.feature(.pocket)])
            ],
            [
                MetoliusCycleBuilder.pullUps(count: 3, title: "Offset pulls", instruction: "Do 3 offset pulls with the high hand on a jug and low hand on a small edge.", phase: .pull, targets: [.feature(.jug), .feature(.smallEdge)]),
                MetoliusCycleBuilder.pullUps(count: 3, title: "Offset pulls · other side", instruction: "Change hands and repeat 3 offset pulls with the high hand on a jug and low hand on a small edge.", phase: .pull, targets: [.feature(.jug), .feature(.smallEdge)])
            ],
            [
                MetoliusCycleBuilder.repetitions(count: 15, title: "Jug knee raises", instruction: "Do 15 knee raises on the jugs.", phase: .pull, targets: [.feature(.jug)]),
                MetoliusCycleBuilder.fixed(title: "Medium-edge hang", instruction: "Hang from a medium edge for 15 seconds.", duration: 15, phase: .hang, targets: [.feature(.mediumEdge)])
            ],
            [MetoliusCycleBuilder.fixed(title: "Medium-edge hang", instruction: "Hang from a medium edge for 25 seconds.", duration: 25, phase: .hang, targets: [.feature(.mediumEdge)])],
            [
                MetoliusCycleBuilder.fixed(title: "Slope hang", instruction: "Hang from a slope for 15 seconds.", duration: 15, phase: .hang, targets: [.feature(.largeSlope)]),
                MetoliusCycleBuilder.pullUps(count: 3, title: "Jug pull-ups", instruction: "Do 3 pull-ups on the jugs.", phase: .pull, targets: [.feature(.jug)])
            ],
            [MetoliusCycleBuilder.maxEffort(title: "Maximum sloper hang", instruction: "Hang from a round sloper for as long as you can.", phase: .hang, targets: [.feature(.roundSloper)])]
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
                    targets: [.feature(.largeSlope)],
                    gripType: nil
                ),
                MetoliusCycleBuilder.pullUps(
                    count: 3,
                    title: "Four-finger flat-edge pull-ups",
                    instruction: "Do 3 pull-ups on a four-finger flat edge.",
                    phase: .pull,
                    targets: [.feature(.flatEdge, fingerCapacity: 4, fallback: .largeEdge)]
                )
            ],
            [
                MetoliusCycleBuilder.fixed(
                    title: "Bent-arm large-slope hang",
                    instruction: "Hold a slightly bent-arm hang on a large slope for 20 seconds.",
                    duration: 20,
                    phase: .hang,
                    targets: [.feature(.largeSlope)],
                    gripType: nil
                ),
                MetoliusCycleBuilder.fixed(
                    title: "L-sit or hanging knee curls",
                    instruction: "Stay on for a 20-second L-sit or 20 hanging knee curls.",
                    duration: 20,
                    phase: .hang,
                    targets: [.feature(.largeSlope)],
                    gripType: nil
                )
            ],
            [
                MetoliusCycleBuilder.pullUps(
                    count: 5,
                    title: "Three-finger-pocket pull-ups",
                    instruction: "Do 5 pull-ups on a three-finger pocket.",
                    phase: .pull,
                    targets: [.feature(.pocket, fingerCapacity: 3)],
                    gripType: nil
                ),
                MetoliusCycleBuilder.fixed(
                    title: "Straight-arm three-finger-pocket hang",
                    instruction: "Stay on for a 25-second straight-arm hang on the same three-finger pocket.",
                    duration: 25,
                    phase: .hang,
                    targets: [.feature(.pocket, fingerCapacity: 3)],
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
                    targets: [.feature(.flatEdge, fingerCapacity: 4, fallback: .largeEdge)]
                ),
                MetoliusCycleBuilder.fixed(
                    title: "Single-arm flat-edge hang · other hand",
                    instruction: "Switch hands and repeat the 20-second one-armed hang from a four-finger flat edge.",
                    duration: 20,
                    phase: .hang,
                    targets: [.feature(.flatEdge, fingerCapacity: 4, fallback: .largeEdge)]
                )
            ],
            [
                MetoliusCycleBuilder.pullUps(
                    count: 5,
                    title: "Offset pull-ups",
                    instruction: "Do 5 offset pull-ups with the top hand on a large slope and bottom hand on a three-finger pocket.",
                    phase: .pull,
                    targets: [.feature(.largeSlope), .feature(.pocket, fingerCapacity: 3)]
                ),
                MetoliusCycleBuilder.pullUps(
                    count: 5,
                    title: "Offset pull-ups · other side",
                    instruction: "Change hands and repeat 5 offset pull-ups with the top hand on a large slope and bottom hand on a three-finger pocket.",
                    phase: .pull,
                    targets: [.feature(.largeSlope), .feature(.pocket, fingerCapacity: 3)]
                )
            ],
            [
                MetoliusCycleBuilder.fixed(
                    title: "Incut-edge bent-arm hang",
                    instruction: "Hold a 90° bent-arm hang on a four-finger incut edge for 30 seconds.",
                    duration: 30,
                    phase: .hang,
                    targets: [.feature(.incutEdge, fingerCapacity: 4, fallback: .largeEdge)]
                ),
                MetoliusCycleBuilder.fixed(
                    title: "Straight-arm three-finger-pocket hang",
                    instruction: "Then hold a straight-arm three-finger-pocket hang for 15 seconds.",
                    duration: 15,
                    phase: .hang,
                    targets: [.feature(.pocket, fingerCapacity: 3)],
                    gripType: nil
                )
            ],
            [
                MetoliusCycleBuilder.pullUps(
                    count: 3,
                    title: "L-sit pull-ups",
                    instruction: "Do 3 L-sit pull-ups, bending your knees if needed.",
                    phase: .pull,
                    targets: [.feature(.largeSlope)]
                ),
                MetoliusCycleBuilder.choice(
                    title: "Choose one: front lever or straight-arm hang",
                    instruction: "Choose one: hold a 5-second front lever or 15-second straight-arm hang on a large slope. If choosing the front lever, finish at 5 seconds; do not perform both.",
                    accessory: "Choose one · 5 seconds front lever OR 15 seconds straight-arm large-slope hang",
                    duration: 15,
                    phase: .hang,
                    targets: [.feature(.largeSlope)],
                    gripType: nil
                )
            ],
            [
                MetoliusCycleBuilder.fixed(
                    title: "Two-finger three-finger-pocket hang",
                    instruction: "Hang straight-armed for 20 seconds using only 2 fingers in three-finger pockets.",
                    duration: 20,
                    phase: .hang,
                    targets: [.feature(.pocket, fingerCapacity: 3)],
                    gripType: nil
                ),
                MetoliusCycleBuilder.pullUps(
                    count: 3,
                    title: "Power pull-ups",
                    instruction: "Then do 3 power pull-ups with weight or helper resistance.",
                    phase: .pull,
                    targets: [.feature(.pocket, fingerCapacity: 3)]
                )
            ],
            [
                MetoliusCycleBuilder.maxEffort(
                    title: "Maximum slope hangs",
                    instruction: "Do a maximum slightly bent-arm hang on a large slope to failure with no rest, then a maximum straight-arm hang on the large slope.",
                    phase: .hang,
                    targets: [.feature(.largeSlope)],
                    gripType: nil
                )
            ]
        ])
    )

    private static func fixedWork(_ target: HoldTarget, _ duration: TimeInterval) -> WorkoutSegment {
        WorkoutSegment(kind: .work, target: target, timing: .fixed, duration: duration)
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
        targets: [HoldTarget],
        gripType: GripType? = nil,
        fingerConfiguration: FingerConfiguration? = nil
    ) -> WorkoutStep {
        WorkoutStep(
            id: id,
            number: 0,
            title: title,
            instruction: instruction,
            accessory: accessory,
            duration: active + rest,
            phase: .hang,
            targets: targets,
            segments: [fixedWork(targets[0], active)] + (rest > 0 ? [fixedRest(rest)] : []),
            gripType: gripType,
            fingerConfiguration: fingerConfiguration,
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
            targets: [],
            segments: [fixedRest(duration)]
        )
    }

    private static func numbered(_ steps: [WorkoutStep]) -> [WorkoutStep] {
        steps.enumerated().map { index, step in
            step.withNumber(index + 1)
        }
    }

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
                targets: [.feature(.mediumEdge, fallback: .largeEdge)],
                gripType: .halfCrimp,
                fingerConfiguration: FingerConfiguration(engagedFingers: [.index, .middle, .ring, .pinky])
            ),
            hangStep(
                id: "max-hangs-2",
                title: "Max hang · set 2",
                instruction: "Hang for 7 seconds on a 20 mm edge in a half-crimp, four-finger position at near-maximal intensity.",
                accessory: "7s hang · 3m recovery · half crimp",
                active: 7,
                rest: 180,
                targets: [.feature(.mediumEdge, fallback: .largeEdge)],
                gripType: .halfCrimp,
                fingerConfiguration: FingerConfiguration(engagedFingers: [.index, .middle, .ring, .pinky])
            ),
            hangStep(
                id: "max-hangs-3",
                title: "Max hang · set 3",
                instruction: "Hang for 7 seconds on a 20 mm edge in a half-crimp, four-finger position at near-maximal intensity.",
                accessory: "7s hang · 3m recovery · half crimp",
                active: 7,
                rest: 180,
                targets: [.feature(.mediumEdge, fallback: .largeEdge)],
                gripType: .halfCrimp,
                fingerConfiguration: FingerConfiguration(engagedFingers: [.index, .middle, .ring, .pinky])
            ),
            hangStep(
                id: "max-hangs-4",
                title: "Max hang · set 4",
                instruction: "Hang for 7 seconds on a 20 mm edge in a half-crimp, four-finger position at near-maximal intensity.",
                accessory: "7s hang · 3m recovery · half crimp",
                active: 7,
                rest: 180,
                targets: [.feature(.mediumEdge, fallback: .largeEdge)],
                gripType: .halfCrimp,
                fingerConfiguration: FingerConfiguration(engagedFingers: [.index, .middle, .ring, .pinky])
            ),
            hangStep(
                id: "max-hangs-5",
                title: "Max hang · set 5",
                instruction: "Hang for 7 seconds on a 20 mm edge in a half-crimp, four-finger position at near-maximal intensity.",
                accessory: "7s hang · half crimp",
                active: 7,
                rest: 0,
                targets: [.feature(.mediumEdge, fallback: .largeEdge)],
                gripType: .halfCrimp,
                fingerConfiguration: FingerConfiguration(engagedFingers: [.index, .middle, .ring, .pinky])
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
                            targets: [.feature(.smallEdge, fallback: .mediumEdge, .largeEdge, .largeOpenHandRail, .jug)],
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
                            targets: [.feature(.smallEdge, fallback: .mediumEdge, .largeEdge, .largeOpenHandRail, .jug)],
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
                            targets: [.feature(.smallEdge, fallback: .mediumEdge, .largeEdge, .largeOpenHandRail, .jug)],
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
                            targets: [.feature(.mediumEdge, fallback: .largeEdge, .largeOpenHandRail, .jug)],
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
                targets: [HoldTarget],
                grip: GripType?,
                fingerConfiguration: FingerConfiguration?
            )] = [
                ("29 mm open edge", [.feature(.largeEdge, fallback: .mediumEdge, .largeOpenHandRail, .jug)], .openHand, nil),
                ("19 mm open edge", [.feature(.mediumEdge, fallback: .largeEdge, .largeOpenHandRail, .jug)], .openHand, nil),
                ("19 mm half crimp", [.feature(.mediumEdge, fallback: .largeEdge, .largeOpenHandRail, .jug)], .halfCrimp, nil),
                ("Front-three open edge", [.feature(.mediumEdge, fallback: .largeEdge, .largeOpenHandRail, .jug)], .openHand, FingerConfiguration(engagedFingers: [.index, .middle, .ring])),
                ("Back-three half crimp", [.feature(.mediumEdge, fallback: .largeEdge, .largeOpenHandRail, .jug)], .halfCrimp, FingerConfiguration(engagedFingers: [.middle, .ring, .pinky])),
                ("Front-two open edge", [.feature(.mediumEdge, fallback: .largeEdge, .largeOpenHandRail, .jug)], .openHand, FingerConfiguration(engagedFingers: [.index, .middle]))
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
            let grips: [(title: String, targets: [HoldTarget], grip: GripType, fingerConfiguration: FingerConfiguration?)] = [
                ("Half 4 Hang", [.feature(.mediumEdge, fallback: .largeEdge, .largeOpenHandRail, .jug)], .halfCrimp, nil),
                ("F3 Open Hang", [.feature(.mediumEdge, fallback: .largeEdge, .largeOpenHandRail, .jug)], .openHand, FingerConfiguration(engagedFingers: [.index, .middle, .ring])),
                ("M2 Open Hang", [.feature(.mediumEdge, fallback: .largeEdge, .largeOpenHandRail, .jug)], .openHand, FingerConfiguration(engagedFingers: [.middle, .ring])),
                ("F2 Open Hang", [.feature(.mediumEdge, fallback: .largeEdge, .largeOpenHandRail, .jug)], .openHand, FingerConfiguration(engagedFingers: [.index, .middle])),
                ("B3 Half Hang", [.feature(.mediumEdge, fallback: .largeEdge, .largeOpenHandRail, .jug)], .halfCrimp, FingerConfiguration(engagedFingers: [.middle, .ring, .pinky])),
                ("F3 Half Hang", [.feature(.mediumEdge, fallback: .largeEdge, .largeOpenHandRail, .jug)], .halfCrimp, FingerConfiguration(engagedFingers: [.index, .middle, .ring]))
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
                        fingerConfiguration: grip.fingerConfiguration
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
            let grips: [(title: String, targets: [HoldTarget], grip: GripType)] = [
                ("29 mm half crimp", [.feature(.largeEdge, fallback: .mediumEdge, .largeOpenHandRail, .jug)], .halfCrimp),
                ("19 mm open edge", [.feature(.mediumEdge, fallback: .largeEdge, .largeOpenHandRail, .jug)], .openHand),
                ("Two-finger pocket", [.feature(.pocket, fingerCapacity: 2, fallback: .mediumEdge, .largeEdge, .largeOpenHandRail, .jug)], .openHand)
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
                            targets: [.feature(.largeEdge, fallback: .mediumEdge, .largeOpenHandRail, .jug)],
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
            let grips: [(title: String, targets: [HoldTarget], grip: GripType)] = [
                ("29 mm open edge", [.feature(.largeEdge, fallback: .mediumEdge, .largeOpenHandRail, .jug)], .openHand),
                ("Four-finger pocket", [.feature(.pocket, fingerCapacity: 4, fallback: .mediumEdge, .largeEdge, .largeOpenHandRail, .jug)], .openHand)
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
                        targets: [.feature(.largeEdge, fallback: .mediumEdge, .largeOpenHandRail, .jug)],
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
        targets: [HoldTarget] = [],
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
            targets: targets,
            segments: targets.isEmpty
                ? []
                : [WorkoutSegment(
                    kind: .work,
                    targets: targets,
                    timing: timing,
                    duration: timing == .fixed ? duration : nil
                )],
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
        work: [(target: HoldTarget, duration: TimeInterval, phase: WorkoutPhase, gripType: GripType?)],
        rest: TimeInterval
    ) -> WorkoutStep {
        let workSegments = work.map {
            WorkoutSegment(kind: .work, target: $0.target, timing: .fixed, duration: $0.duration)
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
            targets: work.map(\.target),
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
                hangStep(id: "hoopers-intro-round-1-set-1-hang", title: "Round 1 · submax no-weight hang", instruction: "Hang submaximally with no weight for 30 seconds on a medium-to-large ledge.", accessory: "30s hang · submax · no weight", active: 30, rest: 0, targets: [.feature(.largeEdge)], gripType: .openHand),
                conditioningTask(id: "hoopers-intro-round-1-set-1-taps", title: "Round 1 · plank shoulder taps", instruction: "Perform 30–40 plank shoulder taps (or thigh taps). Stop if form breaks.", accessory: "30–40 reps", duration: 60),
                hangStep(id: "hoopers-intro-round-1-set-2-hang", title: "Round 1 · submax no-weight hang", instruction: "Repeat the 30-second submaximal no-weight hang on a medium-to-large ledge.", accessory: "30s hang · set 2 of 2", active: 30, rest: 0, targets: [.feature(.largeEdge)], gripType: .openHand),
                conditioningTask(id: "hoopers-intro-round-1-set-2-taps", title: "Round 1 · plank shoulder taps", instruction: "Perform 30–40 plank shoulder taps (or thigh taps) after the second hang.", accessory: "30–40 reps · set 2 of 2", duration: 60)
            ]

            for set in 1...3 {
                for rep in 1...5 {
                    steps.append(contentsOf: [
                        hangStep(id: "hoopers-intro-round-2-set-\(set)-rep-\(rep)-left", title: "Round 2 · single-arm recruitment pull", instruction: "With the feet on the ground and elbow slightly bent, pull the hangboard down rather than lifting off. Build toward near-max over a 5-second hold on the left hand.", accessory: "5s left · rep \(rep) of 5", active: 5, rest: 0, targets: [.feature(.smallEdge)], gripType: .halfCrimp),
                        hangStep(id: "hoopers-intro-round-2-set-\(set)-rep-\(rep)-right", title: "Round 2 · single-arm recruitment pull", instruction: "Repeat the 5-second single-arm recruitment pull on the right hand. Do not lift off the ground.", accessory: "5s right · rep \(rep) of 5", active: 5, rest: 0, targets: [.feature(.smallEdge)], gripType: .halfCrimp)
                    ])
                }
                steps.append(conditioningTask(id: "hoopers-intro-round-2-set-\(set)-kicks", title: "Round 2 · flutter and scissor kicks", instruction: "Perform 20–30 flutter kicks and 20–30 scissor kicks. Protect your lower back and neck.", accessory: "20–30 each", duration: 90))
            }

            for set in 1...3 {
                steps.append(contentsOf: [
                    hangStep(id: "hoopers-intro-round-3-set-\(set)-hang", title: "Round 3 · submax weighted hang", instruction: "Hang submaximally with weight for 20 seconds in an open-hand position on a medium-to-large ledge.", accessory: "20s hang · submax · weighted", active: 20, rest: 0, targets: [.feature(.largeEdge)], gripType: .openHand),
                    conditioningTask(id: "hoopers-intro-round-3-set-\(set)-side-plank", title: "Round 3 · side plank with hip abduction", instruction: "Perform about 10 hip-abduction reps on each side.", accessory: "~10 each side", duration: 90)
                ])
            }

            for set in 1...4 {
                steps.append(contentsOf: [
                    hangStep(id: "hoopers-intro-round-4-set-\(set)-hang", title: "Round 4 · minimal-edge hang\(set == 4 ? " (optional set 4)" : "")", instruction: "Hang on the minimal edge for 12 seconds at effort level ±3 seconds. Start the full 3-minute rest immediately after the hold.\(set == 4 ? " This fourth set is optional; stop after three if that is your choice." : "")", accessory: "12s hang · full 3m rest · \(set == 4 ? "optional" : "set \(set) of 3–4")", active: 12, rest: 0, targets: [.feature(.smallEdge)], gripType: .halfCrimp),
                    conditioningTask(id: "hoopers-intro-round-4-set-\(set)-recovery", title: "Round 4 · bird dog and stretches\(set == 4 ? " (optional set 4)" : "")", instruction: "Use the full 3-minute recovery: plank bird dog for approximately 45–60 seconds, then stretch.\(set == 4 ? " Skip this recovery with the optional fourth set." : "")", accessory: "45–60s bird dog · 3m total recovery", duration: 180)
                ])
            }

            for set in 1...4 {
                steps.append(contentsOf: [
                    guidedTask(id: "hoopers-intro-round-5-set-\(set)-pull-ups", title: "Round 5 · hangboard pull-ups (optional set \(set))", instruction: "Use open hands on medium-to-large ledges; vary ledges, offsets, or your favorite ledge pull. Stop after 2–4 total paired sets.", accessory: "Optional · set \(set) of 2–4 total", phase: .pull, targets: [.feature(.largeEdge)]),
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
                            targets: [.feature(.smallEdge)],
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
            emomMinute(id: "method-emom-minute-1", title: "Minute 1 · 20mm hang", instruction: "Hang for 20 seconds on 20mm, then rest for the remainder of the minute.", work: [(.feature(.mediumEdge), 20, .hang, .halfCrimp)], rest: 40),
            emomMinute(id: "method-emom-minute-2", title: "Minute 2 · deep three-finger pocket + jug pull-ups", instruction: "Hang for 15 seconds on deep three-finger pockets, then do 3 pull-ups on jugs.", work: [(.feature(.pocket, fingerCapacity: 3), 15, .hang, .openHand), (.feature(.jug), 15, .pull, nil)], rest: 30),
            emomMinute(id: "method-emom-minute-3", title: "Minute 3 · 20mm hang + jug knee raises", instruction: "Hang for 10 seconds on 20mm, then do 5 knee raises on jugs.", work: [(.feature(.mediumEdge), 10, .hang, .halfCrimp), (.feature(.jug), 5, .pull, nil)], rest: 45),
            emomMinute(id: "method-emom-minute-4", title: "Minute 4 · bent-arm 15mm hang", instruction: "Hold a bent-arm hang for 15 seconds on 15mm, then rest for the remainder.", work: [(.feature(.smallEdge), 15, .hang, .halfCrimp)], rest: 45),
            emomMinute(id: "method-emom-minute-5", title: "Minute 5 · sloper hang + jug pull-ups", instruction: "Hang for 10 seconds on a sloper, then do 3 pull-ups on jugs.", work: [(.feature(.largeSlope, fallback: .roundSloper), 10, .hang, .openHand), (.feature(.jug), 15, .pull, nil)], rest: 35),
            emomMinute(id: "method-emom-minute-6", title: "Minute 6 · medium three-finger pocket", instruction: "Hang for 10 seconds on medium three-finger pockets, then rest for the remainder.", work: [(.feature(.pocket, fingerCapacity: 3), 10, .hang, .openHand)], rest: 50),
            emomMinute(id: "method-emom-minute-7", title: "Minute 7 · offset pull-ups", instruction: "Do 3 offset pull-ups with one hand on a jug and the other on a small edge.", work: [(.feature(.jug), 15, .pull, nil), (.feature(.smallEdge), 15, .pull, nil)], rest: 30),
            emomMinute(id: "method-emom-minute-8", title: "Minute 8 · 15mm hang", instruction: "Hang for 25 seconds on a 15mm edge, then rest for the remainder.", work: [(.feature(.smallEdge), 25, .hang, .halfCrimp)], rest: 35),
            emomMinute(id: "method-emom-minute-9", title: "Minute 9 · 20mm hang + jug knee raises", instruction: "Hang for 20 seconds on 20mm, then do 10 knee raises on jugs.", work: [(.feature(.mediumEdge), 20, .hang, .halfCrimp), (.feature(.jug), 10, .pull, nil)], rest: 30),
            guidedTask(id: "method-emom-minute-10", title: "Minute 10 · max sloper", instruction: "Take a max hang on a sloper.", accessory: "Max effort · stopwatch", phase: .hang, targets: [.feature(.largeSlope, fallback: .roundSloper)], duration: 60, timing: .stopwatch, gripType: .openHand)
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
            let grips: [(title: String, target: HoldTarget, grip: GripType)] = [
                ("Jug", .feature(.jug), .openHand),
                ("Three-finger pocket", .feature(.pocket, fingerCapacity: 3), .openHand),
                ("Medium edge", .feature(.mediumEdge), .openHand),
                ("Medium pinch", .feature(.mediumPinch, fallback: .mediumEdge), .openHand),
                ("Large sloper", .feature(.largeSlope, fallback: .roundSloper), .openHand)
            ]
            for (index, grip) in grips.enumerated() {
                for rep in 1...6 {
                    steps.append(hangStep(id: "rei-sample-\(index + 1)-rep-\(rep)", title: "\(grip.title) · rep \(rep)", instruction: "Hang for 7–10 seconds, rest for 5 seconds, and repeat six times. Stop at pain.", accessory: "7s hang · 5s rest", active: 7, rest: rep < 6 ? 5 : 0, targets: [grip.target], gripType: grip.grip))
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
            metoliusSimulator3DAdvanced
        ]
        let adaptedPlans = [
            maxHangs,
            forceF80,
            forceF100,
            evaIntHangs,
            repeaters,
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
                        return step.targets.isEmpty && step.timedWorkDuration == nil
                    }
                    let timing = step.segments.first?.timing ?? .fixed
                    return !step.targets.isEmpty && (
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
        assert(boardSpecificMetoliusPlans.count == 6, "The Contact and Simulator 3D guides have six routines")
        for plan in boardSpecificMetoliusPlans {
            assert(plan.provenance == .official)
            assert(plan.duration == 600)
            assert(plan.steps.count == 10)
            assert(plan.steps.allSatisfy { $0.duration == MetoliusCycleBuilder.cycleDuration })
            assert(plan.steps.allSatisfy { $0.timedWorkDuration == nil })
            assert(plan.steps.map(\.number) == Array(1...10))
            assert(Set(plan.steps.map(\.id)).count == 10)
            assert(
                plan.boardID == LegacyPlanSeedBoardMappings.metoliusContactBoardID ||
                    plan.boardID == LegacyPlanSeedBoardMappings.metoliusSimulator3DBoardID
            )
        }
        assert(adaptedPlans.allSatisfy { $0.provenance == .adapted })

        let plans = metoliusPlans + boardSpecificMetoliusPlans + adaptedPlans
        func targetResolves(_ target: HoldTarget, on board: TrainingBoard) -> Bool {
            let boardHoldIDs = Set(board.holds.map(\.id))
            if !target.holdIDs.isEmpty {
                return Set(target.holdIDs).isSubset(of: boardHoldIDs)
            }
            if target.feature != nil {
                return !BoardTargetResolver.substituteHoldIDs(for: target, on: board).isEmpty
            }
            if let kind = target.kind {
                return board.holds.contains { $0.kind == kind }
            }
            return false
        }

        assert(Set(plans.map(\.id)).count == plans.count)
        for plan in plans {
            assert(Set(plan.steps.map(\.id)).count == plan.steps.count)

            if let boardID = plan.boardID {
                assert(BoardCatalog.all.contains { $0.id == boardID })
            } else {
                assert(
                    plan.steps.flatMap(\.targets).allSatisfy { $0.holdIDs.isEmpty },
                    "Board-flexible plans must use semantic targets"
                )
            }
            let candidateBoards = plan.boardID.map { [BoardCatalog.board(for: $0)] }
                ?? BoardCatalog.all
            let compatibleBoards = candidateBoards.filter { board in
                plan.steps.flatMap(\.targets).allSatisfy {
                    targetResolves($0, on: board)
                }
            }
            assert(!compatibleBoards.isEmpty, "No board can run \(plan.id)")

            for board in compatibleBoards {
                for target in plan.steps.flatMap(\.targets) {
                    assert(targetResolves(target, on: board))
                }
            }
        }
        #endif

        return metoliusPlans + boardSpecificMetoliusPlans + adaptedPlans
    }()
}
