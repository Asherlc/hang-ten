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
    case twoFingerPocket
    case threeFingerPocket
    case fourFingerPocket
    case fourFingerFlatEdge
    case fourFingerIncutEdge
    case largeOpenHandRail
    case deepTwoFingerPocket
    case thinCrimp
    case shallowThreeFingerSlot
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
        case .twoFingerPocket: "Two-finger pocket"
        case .threeFingerPocket: "Three-finger pocket"
        case .fourFingerPocket: "Four-finger pocket"
        case .fourFingerFlatEdge: "Four-finger flat edge"
        case .fourFingerIncutEdge: "Four-finger incut edge"
        case .largeOpenHandRail: "Large open-hand rail"
        case .deepTwoFingerPocket: "Deep two-finger pocket"
        case .thinCrimp: "Thin crimp"
        case .shallowThreeFingerSlot: "Shallow three-finger slot"
        case .widePinch: "Wide pinch"
        case .mediumPinch: "Medium pinch"
        case .smallPinch: "Small pinch"
        }
    }
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
    let frame: HoldFrame
    let sizeMillimeters: Int?
    let depthRangeMillimeters: ClosedRange<Int>?
    let features: Set<HoldFeature>?

    static let validFingerCapacityRange = 1...4

    init(
        id: String,
        name: String,
        kind: HoldKind,
        geometry: [BoardHoldPiece],
        sizeMillimeters: Int? = nil,
        gripType: GripType? = nil,
        fingerCapacity: Int? = nil,
        depthRangeMillimeters: ClosedRange<Int>? = nil,
        features: Set<HoldFeature>? = nil
    ) {
        precondition(!geometry.isEmpty, "BoardHold geometry must include at least one piece.")
        if let fingerCapacity {
            precondition(
                Self.validFingerCapacityRange.contains(fingerCapacity),
                "BoardHold fingerCapacity must be in \(Self.validFingerCapacityRange)."
            )
        }

        self.id = id
        self.name = name
        self.kind = kind
        self.geometry = geometry
        self.gripType = gripType
        self.fingerCapacity = fingerCapacity
        let firstFrame = geometry[0].frame
        let union = geometry.dropFirst().reduce(firstFrame) { $0.union($1.frame) }
        self.frame = HoldFrame(
            x: union.minX,
            y: union.minY,
            width: union.width,
            height: union.height
        )
        self.sizeMillimeters = sizeMillimeters
        self.depthRangeMillimeters = depthRangeMillimeters
        self.features = features
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
        sizeMillimeters: Int? = nil,
        gripType: GripType? = nil,
        fingerCapacity: Int? = nil,
        depthRangeMillimeters: ClosedRange<Int>? = nil,
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
                    shape: .roundedRect(cornerRadiusFraction: 0)
                )
            ],
            sizeMillimeters: sizeMillimeters,
            gripType: gripType,
            fingerCapacity: fingerCapacity,
            depthRangeMillimeters: depthRangeMillimeters,
            features: features
        )
    }
}

struct TrainingBoard: Identifiable, Hashable {
    let id: String
    let manufacturer: String
    let name: String
    let subtitle: String
    let dimensions: String
    let aspectRatio: CGFloat
    let holds: [BoardHold]
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
        photoAssetName: String?
    ) {
        self.id = id
        self.manufacturer = manufacturer
        self.name = name
        self.subtitle = subtitle
        self.dimensions = dimensions
        self.aspectRatio = aspectRatio
        self.holds = holds
        self.semanticHolds = semanticHolds
        self.productURL = productURL
        self.photoAssetName = photoAssetName
    }


}

struct HoldTarget: Hashable {
    let holdIDs: [String]
    let kind: HoldKind?
    let feature: HoldFeature?
    let fallbackFeatures: [HoldFeature]

    static func ids(_ holdIDs: String...) -> HoldTarget {
        HoldTarget(holdIDs: holdIDs, kind: nil, feature: nil, fallbackFeatures: [])
    }

    static func ids(_ holdIDs: [String]) -> HoldTarget {
        HoldTarget(holdIDs: holdIDs, kind: nil, feature: nil, fallbackFeatures: [])
    }

    static func kind(_ kind: HoldKind) -> HoldTarget {
        HoldTarget(holdIDs: [], kind: kind, feature: nil, fallbackFeatures: [])
    }

    static func feature(
        _ feature: HoldFeature,
        fallback fallbackFeatures: HoldFeature...
    ) -> HoldTarget {
        HoldTarget(
            holdIDs: [],
            kind: nil,
            feature: feature,
            fallbackFeatures: fallbackFeatures
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

    var detail: String {
        switch self {
        case .official:
            "Task order, repetitions, and prescribed times match the linked manufacturer routine."
        case .adapted:
            "This app version changes or supplements the source for guided timing, safety, or board fit."
        case .custom:
            "Created in Hang Ten."
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

    static let defaultBoard: TrainingBoard = {
        guard let board = all.first else {
            fatalError("The bundled board library contains no completed boards.")
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
                    accessory: "App timer · \(Int(remaining))s rest",
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
extension BoardMappingDefinition {
    func unknownHoldIDs(on board: TrainingBoard) -> Set<String> {
        let boardHoldIDs = Set(board.holds.map(\.id))
        let mappedHoldIDs = Set(semanticHolds.values.flatMap(\.holdIDs))
        return mappedHoldIDs.subtracting(boardHoldIDs)
    }
}

enum LegacyPlanSeedBoardMappings {
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

    private static let exactTargetMapping = LegacyPlanSeedBoardMappings.required(
        containingSemantic: "edge-19"
    )
    private static let exactTargetBoard = requiredBoard(id: exactTargetMapping.boardID)

    private static func requiredBoard(id boardID: String) -> TrainingBoard {
        let matches = BoardCatalog.all.filter { $0.id == boardID }
        precondition(
            matches.count == 1,
            "Expected exactly one discovered board with ID \(boardID)."
        )
        let board = matches[0]
        let missingHoldIDs = exactTargetMapping.unknownHoldIDs(on: board)
        precondition(
            missingHoldIDs.isEmpty,
            "Plan mapping for board \(boardID) references unknown hold IDs: \(missingHoldIDs.sorted())."
        )
        return board
    }

    private static func exactTarget(
        _ semanticID: String,
        holdIndex: Int? = nil
    ) -> HoldTarget {
        guard let holdIDs = exactTargetMapping.semanticHolds[semanticID]?.holdIDs else {
            preconditionFailure(
                "The plan seed mapping is missing \(semanticID) semantics."
            )
        }
        if let holdIndex {
            precondition(holdIDs.indices.contains(holdIndex))
            return .ids([holdIDs[holdIndex]])
        }
        return .ids(holdIDs)
    }

    private static let sourceURL = URL(
        string: "https://www.metoliusclimbing.com/pages/10-minute-sequences-hangboard-training-guide"
    )!

    private static let sourceLabel = "Metolius 10 Minute Sequences — Hangboard Training Guide"

    private static let adaptationNote =
        "Source sequence with guided task timing; pull-ups default to 5 seconds each and other counted repetitions to 1 second each."

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
                    targets: [.feature(.fourFingerFlatEdge, fallback: .largeEdge)]
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
                    targets: [.feature(.threeFingerPocket)],
                    gripType: nil
                ),
                MetoliusCycleBuilder.fixed(
                    title: "Straight-arm three-finger-pocket hang",
                    instruction: "Stay on for a 25-second straight-arm hang on the same three-finger pocket.",
                    duration: 25,
                    phase: .hang,
                    targets: [.feature(.threeFingerPocket)],
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
                    targets: [.feature(.fourFingerFlatEdge, fallback: .largeEdge)]
                ),
                MetoliusCycleBuilder.fixed(
                    title: "Single-arm flat-edge hang · other hand",
                    instruction: "Switch hands and repeat the 20-second one-armed hang from a four-finger flat edge.",
                    duration: 20,
                    phase: .hang,
                    targets: [.feature(.fourFingerFlatEdge, fallback: .largeEdge)]
                )
            ],
            [
                MetoliusCycleBuilder.pullUps(
                    count: 5,
                    title: "Offset pull-ups",
                    instruction: "Do 5 offset pull-ups with the top hand on a large slope and bottom hand on a three-finger pocket.",
                    phase: .pull,
                    targets: [.feature(.largeSlope), .feature(.threeFingerPocket)]
                ),
                MetoliusCycleBuilder.pullUps(
                    count: 5,
                    title: "Offset pull-ups · other side",
                    instruction: "Change hands and repeat 5 offset pull-ups with the top hand on a large slope and bottom hand on a three-finger pocket.",
                    phase: .pull,
                    targets: [.feature(.largeSlope), .feature(.threeFingerPocket)]
                )
            ],
            [
                MetoliusCycleBuilder.fixed(
                    title: "Incut-edge bent-arm hang",
                    instruction: "Hold a 90° bent-arm hang on a four-finger incut edge for 30 seconds.",
                    duration: 30,
                    phase: .hang,
                    targets: [.feature(.fourFingerIncutEdge, fallback: .largeEdge)]
                ),
                MetoliusCycleBuilder.fixed(
                    title: "Straight-arm three-finger-pocket hang",
                    instruction: "Then hold a straight-arm three-finger-pocket hang for 15 seconds.",
                    duration: 15,
                    phase: .hang,
                    targets: [.feature(.threeFingerPocket)],
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
                    targets: [.feature(.threeFingerPocket)],
                    gripType: nil
                ),
                MetoliusCycleBuilder.pullUps(
                    count: 3,
                    title: "Power pull-ups",
                    instruction: "Then do 3 power pull-ups with weight or helper resistance.",
                    phase: .pull,
                    targets: [.feature(.threeFingerPocket)]
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
        subtitle: "Seven-second half-crimp hangs on a 20 mm edge; Compact II targeting and the five-set timer structure are app-guided.",
        level: "Advanced",
        sourceLabel: "Lattice max hang protocol",
        sourceURL: URL(string: "https://latticetraining.com/workout/1c4cc25a-ebe8-4930-8541-5b604a831c5f/half-4-hang-max/")!,
        provenance: .adapted,
        boardID: exactTargetBoard.id,
        steps: numbered([
            hangStep(
                id: "max-hangs-1",
                title: "Max hang · set 1",
                instruction: "Hang for 7 seconds on a 20 mm edge in a half-crimp, four-finger position at near-maximal intensity.",
                accessory: "7s hang · app recovery 3m · half crimp",
                active: 7,
                rest: 180,
                targets: [exactTarget("edge-19")],
                gripType: .halfCrimp
            ),
            hangStep(
                id: "max-hangs-2",
                title: "Max hang · set 2",
                instruction: "Hang for 7 seconds on a 20 mm edge in a half-crimp, four-finger position at near-maximal intensity.",
                accessory: "7s hang · app recovery 3m · half crimp",
                active: 7,
                rest: 180,
                targets: [exactTarget("edge-19")],
                gripType: .halfCrimp
            ),
            hangStep(
                id: "max-hangs-3",
                title: "Max hang · set 3",
                instruction: "Hang for 7 seconds on a 20 mm edge in a half-crimp, four-finger position at near-maximal intensity.",
                accessory: "7s hang · app recovery 3m · half crimp",
                active: 7,
                rest: 180,
                targets: [exactTarget("edge-19")],
                gripType: .halfCrimp
            ),
            hangStep(
                id: "max-hangs-4",
                title: "Max hang · set 4",
                instruction: "Hang for 7 seconds on a 20 mm edge in a half-crimp, four-finger position at near-maximal intensity.",
                accessory: "7s hang · app recovery 3m · half crimp",
                active: 7,
                rest: 180,
                targets: [exactTarget("edge-19")],
                gripType: .halfCrimp
            ),
            hangStep(
                id: "max-hangs-5",
                title: "Max hang · set 5",
                instruction: "Hang for 7 seconds on a 20 mm edge in a half-crimp, four-finger position at near-maximal intensity.",
                accessory: "7s hang · half crimp",
                active: 7,
                rest: 0,
                targets: [exactTarget("edge-19")],
                gripType: .halfCrimp
            ),
        ])
    )

    static let forceF80 = TrainingPlan(
        id: "research.force-feedback-f80",
        title: "F80 Force Board",
        subtitle: "80% MFSi repeaters on the study hold; Compact II targeting is adapted.",
        level: "Advanced",
        sourceLabel: "Frontiers force-feedback hangboard study",
        sourceURL: URL(string: "https://www.frontiersin.org/journals/sports-and-active-living/articles/10.3389/fspor.2022.862782/full")!,
        provenance: .adapted,
        boardID: exactTargetBoard.id,
        steps: numbered({
            var steps: [WorkoutStep] = []
            for set in 1...3 {
                for rep in 1...12 {
                    steps.append(
                        hangStep(
                            id: "f80-set-\(set)-rep-\(rep)",
                            title: "F80 · set \(set), rep \(rep)",
                            instruction: "Hang with both hands at 80% MFSi on the study hold for 10 seconds, then rest for 6 seconds.",
                            accessory: "10s hang · 6s rest · 80% MFSi",
                            active: 10,
                            rest: 6,
                            targets: [exactTarget("edge-19")],
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
        subtitle: "Six-second maximal alternating-hand hangs; Compact II targeting and timer structure are app adaptations.",
        level: "Expert",
        sourceLabel: "Frontiers force-feedback hangboard study",
        sourceURL: URL(string: "https://www.frontiersin.org/journals/sports-and-active-living/articles/10.3389/fspor.2022.862782/full")!,
        provenance: .adapted,
        boardID: exactTargetBoard.id,
        steps: numbered({
            var steps: [WorkoutStep] = []
            for set in 1...2 {
                for round in 1...6 {
                    steps.append(
                        hangStep(
                            id: "f100-set-\(set)-round-\(round)-right",
                            title: "F100 · right hand",
                            instruction: "Apply maximal force with the right hand for 6 seconds.",
                            accessory: "6s max",
                            active: 6,
                            rest: 0,
                            targets: [exactTarget("edge-19", holdIndex: 1)],
                            gripType: nil
                        )
                    )
                    steps.append(
                        hangStep(
                            id: "f100-set-\(set)-round-\(round)-left",
                            title: "F100 · left hand",
                            instruction: "Apply maximal force with the left hand for 6 seconds.",
                            accessory: "6s max",
                            active: 6,
                            rest: round == 6 ? (set == 1 ? 300 : 0) : 168,
                            targets: [exactTarget("edge-19", holdIndex: 0)],
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
        subtitle: "Intermittent dead-hangs from the Eva López comparison study; exact timer structure and Compact II targeting are app adaptations.",
        level: "Intermediate+",
        sourceLabel: "Eva López hangboard comparison",
        sourceURL: URL(string: "https://pubmed.ncbi.nlm.nih.gov/30988852/")!,
        provenance: .adapted,
        boardID: exactTargetBoard.id,
        steps: numbered({
            var steps: [WorkoutStep] = []
            for set in 1...3 {
                for rep in 1...5 {
                    steps.append(
                        hangStep(
                            id: "int-hangs-set-\(set)-rep-\(rep)",
                            title: "IntHang · set \(set), rep \(rep)",
                            instruction: "Intermittent dead-hang interval from the study comparison, guided here by an app timer adaptation.",
                            accessory: "App timer adaptation",
                            active: 10,
                            rest: rep < 5 ? 5 : 0,
                            targets: [exactTarget("edge-19")],
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
                            accessory: "App recovery"
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
        subtitle: "Two identical 7/3 sets with six progressive series; Compact II hold mapping is adapted.",
        level: "Intermediate",
        sourceLabel: "Beastmaker 7/3 study protocol",
        sourceURL: URL(string: "https://www.frontiersin.org/journals/sports-and-active-living/articles/10.3389/fspor.2022.888158/full")!,
        provenance: .adapted,
        boardID: exactTargetBoard.id,
        steps: numbered({
            var steps: [WorkoutStep] = []
            let grips: [(
                title: String,
                targets: [HoldTarget],
                grip: GripType?,
                fingerConfiguration: FingerConfiguration?
            )] = [
                ("29 mm open edge", [exactTarget("edge-29")], .openHand, nil),
                ("19 mm open edge", [exactTarget("edge-19")], .openHand, nil),
                ("19 mm half crimp", [exactTarget("edge-19")], .halfCrimp, nil),
                ("Front-three open edge", [exactTarget("edge-19")], .openHand, FingerConfiguration(engagedFingers: [.index, .middle, .ring])),
                ("Back-three half crimp", [exactTarget("edge-19")], .halfCrimp, FingerConfiguration(engagedFingers: [.middle, .ring, .pinky])),
                ("Front-two open edge", [exactTarget("edge-19")], .openHand, FingerConfiguration(engagedFingers: [.index, .middle]))
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
        subtitle: "Low-intensity feet-supported hangs; 10/50 timing and Compact II grip mapping are app adaptations.",
        level: "Supplemental",
        sourceLabel: "Lattice Abrahangs protocol",
        sourceURL: URL(string: "https://latticetraining.com/workout/1832c13b-14c1-444c-82a2-e72b22a6fb13/abrahangs-protocol")!,
        provenance: .adapted,
        boardID: exactTargetBoard.id,
        steps: numbered({
            var steps: [WorkoutStep] = []
            let grips: [(title: String, targets: [HoldTarget], grip: GripType, fingerConfiguration: FingerConfiguration?)] = [
                ("Half 4 Hang", [exactTarget("edge-19")], .halfCrimp, nil),
                ("F3 Open Hang", [exactTarget("edge-19")], .openHand, FingerConfiguration(engagedFingers: [.index, .middle, .ring])),
                ("M2 Open Hang", [exactTarget("edge-19")], .openHand, FingerConfiguration(engagedFingers: [.middle, .ring])),
                ("F2 Open Hang", [exactTarget("edge-19")], .openHand, FingerConfiguration(engagedFingers: [.index, .middle])),
                ("B3 Half Hang", [exactTarget("edge-19")], .halfCrimp, FingerConfiguration(engagedFingers: [.middle, .ring, .pinky])),
                ("F3 Half Hang", [exactTarget("edge-19")], .halfCrimp, FingerConfiguration(engagedFingers: [.index, .middle, .ring]))
            ]

            for (index, grip) in grips.enumerated() {
                steps.append(
                    hangStep(
                        id: "abrahangs-grip-\(index + 1)",
                        title: "Abrahang · \(grip.title)",
                        instruction: "Keep both feet supported and the intensity low throughout.",
                        accessory: "Feet supported · app timer",
                        active: 10,
                        rest: 50,
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
        subtitle: "Seven-second maximal hangs with exact 53-second rests; Compact II holds and three-minute set recovery are app choices.",
        level: "Advanced",
        sourceLabel: "Eric Hörst fingerboard protocols",
        sourceURL: URL(string: "https://trainingforclimbing.com/4-fingerboard-strength-protocols-that-work/")!,
        provenance: .adapted,
        boardID: exactTargetBoard.id,
        steps: numbered({
            var steps: [WorkoutStep] = []
            let grips: [(title: String, targets: [HoldTarget], grip: GripType)] = [
                ("29 mm half crimp", [exactTarget("edge-29")], .halfCrimp),
                ("19 mm open edge", [exactTarget("edge-19")], .openHand),
                ("Two-finger pocket", [.feature(.twoFingerPocket)], .openHand)
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
                            accessory: "App recovery · 3m"
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
        subtitle: "The 3–6–9 sequence; three rounds, Compact II targeting, and exact rests are app choices within the source ranges.",
        level: "Intermediate+",
        sourceLabel: "Steve Bechtel 3–6–9 ladder protocol",
        sourceURL: URL(string: "https://strengthclimbing.com/steve-bechtels-3-6-9-ladders/")!,
        provenance: .adapted,
        boardID: exactTargetBoard.id,
        steps: numbered({
            var steps: [WorkoutStep] = []
            for round in 1...3 {
                for (index, hangSeconds) in [3, 6, 9].enumerated() {
                    steps.append(
                        hangStep(
                            id: "ladders-round-\(round)-\(hangSeconds)",
                            title: "Ladder \(round) · \(hangSeconds) seconds",
                            instruction: "Use a load that allows about 12 seconds at maximum.",
                            accessory: "App timer · \(hangSeconds)s hang · 30s rest",
                            active: TimeInterval(hangSeconds),
                            rest: index < 2 ? 30 : 0,
                            targets: [exactTarget("edge-29")],
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
                            accessory: "App recovery · 3m"
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
        subtitle: "Density hangs within the source ranges; exact timers, set count, and Compact II holds are app adaptations.",
        level: "Intermediate+",
        sourceLabel: "Tyler Nelson density hang protocol",
        sourceURL: URL(string: "https://strengthclimbing.com/dr-tyler-nelsons-density-hangs-finger-training-for-rock-climbing/")!,
        provenance: .adapted,
        boardID: exactTargetBoard.id,
        steps: numbered({
            var steps: [WorkoutStep] = []
            let grips: [(title: String, targets: [HoldTarget], grip: GripType)] = [
                ("29 mm open edge", [exactTarget("edge-29")], .openHand),
                ("Four-finger pocket", [.feature(.fourFingerPocket)], .openHand)
            ]

            for (holdIndex, grip) in grips.enumerated() {
                for set in 1...2 {
                    for rep in 1...3 {
                        steps.append(
                        hangStep(
                            id: "density-hold-\(holdIndex + 1)-set-\(set)-rep-\(rep)",
                            title: "Density · \(grip.title), set \(set), rep \(rep)",
                            instruction: "Density hang guided by an app timer inside the source's 20–40 second work and 10–20 second rest ranges.",
                            accessory: "App timer · 30s hang · 15s rest",
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
                            accessory: "App recovery · 3m"
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
                            accessory: "App recovery · 3m"
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
        subtitle: "Ten 60-second hangs with 60-second rests; Compact II targeting is adapted.",
        level: "Intermediate",
        sourceLabel: "Zlagboard endurance protocol",
        sourceURL: URL(string: "https://strengthclimbing.com/zlagboard-forearm-endurance-workout/")!,
        provenance: .adapted,
        boardID: exactTargetBoard.id,
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
                        targets: [exactTarget("edge-29")],
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
        accessory: String = "Coach-guided · source timing not prescribed",
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

    static let latticeLiteHomeAdaptations = TrainingPlan(
        id: "lattice.lite-home-adaptations",
        title: "Lattice Lite Guide · Home Adaptations",
        subtitle: "Faithful weekly template with app-guided rows where the PDF gives no task timer.",
        level: "Intermediate",
        sourceLabel: "Lattice Training · Lite Guide to Home Adaptations",
        sourceURL: URL(string: "https://latticetraining.com/app/uploads/2020/03/Lite-Guide-to-home-adaptations.pdf")!,
        provenance: .adapted,
        boardID: nil,
        steps: numbered([
            guidedTask(id: "lattice-lite-max-hang", title: "Max hang · 2× weekly", instruction: "Schedule the source max-hang session twice this week. The source sample week gives frequency but no task duration; use a coach or stopwatch.", accessory: "Weekly frequency · 2×", phase: .hang, targets: [.feature(.smallEdge)], gripType: .halfCrimp),
            guidedTask(id: "lattice-lite-f80-repeaters", title: "80% repeaters · 1× weekly", instruction: "Schedule the source 80% repeater session once this week. Preserve the 80% effort target; the source sample week gives no timer here.", accessory: "Weekly frequency · 1×", phase: .hang, targets: [.feature(.mediumEdge)], gripType: .halfCrimp),
            guidedTask(id: "lattice-lite-753-forty", title: "7:3s at 40% · 1× weekly", instruction: "Schedule the source 7:3-second repeater session at 40% once this week. The source names the format and frequency, not a full app protocol.", accessory: "Weekly frequency · 1×", phase: .hang, targets: [.feature(.mediumEdge)], gripType: .openHand),
            guidedTask(id: "lattice-lite-on-the-minute-pull-ups", title: "On-the-minute pull-ups · 1.5× weekly", instruction: "Schedule the source on-the-minute pull-up work one and a half times this week. Preserve the unusual 1.5× sample-week frequency; use the source/coach timing rather than an invented count.", accessory: "Weekly frequency · 1.5×", phase: .pull, targets: [.feature(.jug)]),
            guidedTask(id: "lattice-lite-weighted-pull-ups", title: "Weighted pull-ups · 1× weekly", instruction: "Schedule weighted pull-ups once this week. The source sample week does not prescribe repetitions or duration in this template.", accessory: "Weekly frequency · 1×", phase: .pull, targets: [.feature(.jug)]),
            conditioningTask(id: "lattice-lite-floor-core", title: "Floor core · 1× weekly", instruction: "Schedule floor-core work once this week. Use the source's floor-core exercises; this row intentionally does not invent counts or timing.", accessory: "Weekly frequency · 1×"),
            conditioningTask(id: "lattice-lite-stabilizer", title: "Stabilizer conditioning · 2× weekly", instruction: "Schedule stabilizer conditioning twice this week. Follow the source/coach prescription; no count or duration is supplied by the weekly sample.", accessory: "Weekly frequency · 2×"),
            conditioningTask(id: "lattice-lite-hip-flexibility", title: "Hip flexibility · 2× weekly", instruction: "Schedule hip-flexibility work twice this week. Use the source guidance and a coach-led or stopwatch-led mobility block.", accessory: "Weekly frequency · 2×"),
            conditioningTask(id: "lattice-lite-upper-body-flexibility", title: "Upper-body flexibility · 1× weekly", instruction: "Schedule upper-body flexibility once this week. The source names the task and frequency but does not prescribe a duration.", accessory: "Weekly frequency · 1×")
        ])
    )

    static let hoopersBetaIntroductory = TrainingPlan(
        id: "hoopers-beta.introductory-home-hangboard",
        title: "Hooper's Beta · Introductory Home Hangboard",
        subtitle: "45+ minute routine with exact round order, optionality, and coach-guided qualifiers retained.",
        level: "Intermediate",
        sourceLabel: "Hooper's Beta · Jason Hooper PT, DPT, OCS, CAFS",
        sourceURL: URL(string: "https://www.hoopersbeta.com/library/hold-hangboard-introductory-routine")!,
        provenance: .adapted,
        boardID: nil,
        steps: numbered({
            var steps: [WorkoutStep] = [
                conditioningTask(id: "hoopers-intro-foam-roll", title: "Warm-up · foam rolling", instruction: "Foam roll to mobilize tissue and thoracic mobility before overhead work. The source gives no count or duration.") ,
                conditioningTask(id: "hoopers-intro-normal-pull-ups", title: "Warm-up · normal pull-ups", instruction: "Perform 10 normal pull-ups on a jug or pull-up bar, or about 75% of your maximum.", accessory: "10 reps or ~75% max"),
                conditioningTask(id: "hoopers-intro-normal-push-ups", title: "Warm-up · normal push-ups", instruction: "Perform 10–20 normal push-ups, or about 75% of your maximum.", accessory: "10–20 reps or ~75% max"),
                conditioningTask(id: "hoopers-intro-wide-pull-ups", title: "Warm-up · wide pull-ups", instruction: "Perform wide pull-ups on the widest large ledge available; do not use a jug. The source prescribes no count.", accessory: "Large ledge · no source count"),
                conditioningTask(id: "hoopers-intro-wide-push-ups", title: "Warm-up · wide push-ups", instruction: "Perform wide push-ups with hands rotated outward as comfortable. Quality and range matter; the source prescribes no count.", accessory: "Wide push-ups · no source count"),
                conditioningTask(id: "hoopers-intro-narrow-pull-ups", title: "Warm-up · narrow pull-ups", instruction: "Perform narrow pull-ups on a large edge. The source prescribes no count.", accessory: "Large edge · no source count"),
                conditioningTask(id: "hoopers-intro-narrow-push-ups", title: "Warm-up · narrow push-ups", instruction: "Perform narrow push-ups, preferably on fists or as diamond push-ups. The source prescribes no count.", accessory: "Narrow push-ups · no source count"),
                hangStep(id: "hoopers-intro-round-1-set-1-hang", title: "Round 1 · submax no-weight hang", instruction: "Hang submaximally with no weight for 30 seconds on a medium-to-large ledge. Start the 60-second timer immediately after the hang.", accessory: "30s hang · submax · no weight", active: 30, rest: 0, targets: [.feature(.largeEdge)], gripType: .openHand),
                conditioningTask(id: "hoopers-intro-round-1-set-1-taps", title: "Round 1 · plank shoulder taps", instruction: "During the source's 60-second interval after the hang, perform 30–40 plank shoulder taps (or thigh taps). Stop if form breaks.", accessory: "30–40 reps · source 60s interval", duration: 60),
                hangStep(id: "hoopers-intro-round-1-set-2-hang", title: "Round 1 · submax no-weight hang", instruction: "Repeat the 30-second submaximal no-weight hang on a medium-to-large ledge.", accessory: "30s hang · set 2 of 2", active: 30, rest: 0, targets: [.feature(.largeEdge)], gripType: .openHand),
                conditioningTask(id: "hoopers-intro-round-1-set-2-taps", title: "Round 1 · plank shoulder taps", instruction: "Perform 30–40 plank shoulder taps (or thigh taps) after the second hang. The source's 60-second interval includes this work.", accessory: "30–40 reps · set 2 of 2", duration: 60)
            ]

            for set in 1...3 {
                for rep in 1...5 {
                    steps.append(contentsOf: [
                        hangStep(id: "hoopers-intro-round-2-set-\(set)-rep-\(rep)-left", title: "Round 2 · single-arm recruitment pull", instruction: "With the feet on the ground and elbow slightly bent, pull the hangboard down rather than lifting off. Build toward near-max over a 5-second hold on the left hand.", accessory: "5s left · rep \(rep) of 5", active: 5, rest: 0, targets: [.feature(.smallEdge)], gripType: .halfCrimp),
                        hangStep(id: "hoopers-intro-round-2-set-\(set)-rep-\(rep)-right", title: "Round 2 · single-arm recruitment pull", instruction: "Repeat the 5-second single-arm recruitment pull on the right hand. Do not lift off the ground.", accessory: "5s right · rep \(rep) of 5", active: 5, rest: 0, targets: [.feature(.smallEdge)], gripType: .halfCrimp)
                    ])
                }
                steps.append(conditioningTask(id: "hoopers-intro-round-2-set-\(set)-kicks", title: "Round 2 · flutter and scissor kicks", instruction: "Perform 20–30 flutter kicks and 20–30 scissor kicks. Start the source's 90-second timer after the fifth rep on the second hand; protect your lower back and neck.", accessory: "20–30 each · source 90s interval", duration: 90))
            }

            for set in 1...3 {
                steps.append(contentsOf: [
                    hangStep(id: "hoopers-intro-round-3-set-\(set)-hang", title: "Round 3 · submax weighted hang", instruction: "Hang submaximally with weight for 20 seconds in an open-hand position on a medium-to-large ledge. Start the source's 90-second timer after the hang.", accessory: "20s hang · submax · weighted", active: 20, rest: 0, targets: [.feature(.largeEdge)], gripType: .openHand),
                    conditioningTask(id: "hoopers-intro-round-3-set-\(set)-side-plank", title: "Round 3 · side plank with hip abduction", instruction: "Perform about 10 hip-abduction reps on each side during the source's 90-second interval.", accessory: "~10 each side · source 90s interval", duration: 90)
                ])
            }

            for set in 1...4 {
                steps.append(contentsOf: [
                    hangStep(id: "hoopers-intro-round-4-set-\(set)-hang", title: "Round 4 · minimal-edge hang\(set == 4 ? " (optional set 4)" : "")", instruction: "Hang on the minimal edge for 12 seconds at effort level ±3 seconds. Start the full 3-minute rest immediately after the hold.\(set == 4 ? " This fourth set is optional; stop after three if that is your choice." : "")", accessory: "12s hang · full 3m rest · \(set == 4 ? "optional" : "set \(set) of 3–4")", active: 12, rest: 0, targets: [.feature(.smallEdge)], gripType: .halfCrimp),
                    conditioningTask(id: "hoopers-intro-round-4-set-\(set)-recovery", title: "Round 4 · bird dog and stretches\(set == 4 ? " (optional set 4)" : "")", instruction: "Use the full 3-minute recovery: plank bird dog for approximately 45–60 seconds, then the source's stretches.\(set == 4 ? " Skip this recovery with the optional fourth set." : "")", accessory: "45–60s bird dog · 3m total recovery", duration: 180)
                ])
            }

            for set in 1...4 {
                steps.append(contentsOf: [
                    guidedTask(id: "hoopers-intro-round-5-set-\(set)-pull-ups", title: "Round 5 · hangboard pull-ups (optional set \(set))", instruction: "Optional Round 5: this is one paired set within the source's 2–4 total sets. Use open hands on medium-to-large ledges; vary ledges, offsets, or your favorite ledge pull. Stop after your chosen total.", accessory: "Optional · set \(set) of 2–4 total", phase: .pull, targets: [.feature(.largeEdge)]),
                    conditioningTask(id: "hoopers-intro-round-5-set-\(set)-hollow", title: "Round 5 · hollow rock/hold (paired optional set \(set))", instruction: "Within the same optional set, perform 10–20 hollow rocks, then hold. Keep a stable spine; stop or regress if your back feels it. Stop Round 5 after 2–4 total paired sets.", accessory: "Optional · 10–20 reps then hold")
                ])
            }
            return steps
        }())
    )

    static let methodRepeaters = TrainingPlan(
        id: "method.intermediate-hangboarding.repeaters",
        title: "Method Climbing · Intermediate Repeaters",
        subtitle: "Five-round repeater workout; app uses the top of each source range as its guided default.",
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
                            instruction: "Hang for 5–7 seconds, rest for 5–7 seconds, and repeat five times per round. The app defaults to 7s/7s; adjust to the source range with a stopwatch if needed.",
                            accessory: "App default 7s hang · 7s rest · source range 5–7s",
                            active: 7,
                            rest: rep < 5 ? 7 : 0,
                            targets: [.feature(.smallEdge)],
                            gripType: .halfCrimp
                        )
                    )
                }
                if round < 5 {
                    steps.append(recoveryStep(id: "method-repeaters-round-\(round)-recovery", title: "Repeaters · round recovery", duration: 105, accessory: "App default 105s · source range 90–120s"))
                }
            }
            return steps
        }())
    )

    static let methodEMOM = TrainingPlan(
        id: "method.intermediate-hangboarding.emom",
        title: "Method Climbing · Intermediate 10-minute EMOM",
        subtitle: "Exact ten-minute task order with app defaults for un-timed pull-up/knee-raise work.",
        level: "Intermediate",
        sourceLabel: "Method Climbing · Intermediate Hangboarding",
        sourceURL: URL(string: "https://methodclimb.com/intermediate-hangboarding/")!,
        provenance: .adapted,
        boardID: nil,
        steps: numbered([
            emomMinute(id: "method-emom-minute-1", title: "Minute 1 · 20mm hang", instruction: "Hang for 20 seconds on 20mm, then rest for the remainder of the minute.", work: [(.feature(.mediumEdge), 20, .hang, .halfCrimp)], rest: 40),
            emomMinute(id: "method-emom-minute-2", title: "Minute 2 · deep three-finger pocket + jug pull-ups", instruction: "Hang for 15 seconds on deep three-finger pockets, then do 3 pull-ups on jugs. The app defaults to 5 seconds per pull-up before the remainder-minute rest.", work: [(.feature(.threeFingerPocket), 15, .hang, .openHand), (.feature(.jug), 15, .pull, nil)], rest: 30),
            emomMinute(id: "method-emom-minute-3", title: "Minute 3 · 20mm hang + jug knee raises", instruction: "Hang for 10 seconds on 20mm, then do 5 knee raises on jugs. The app uses 1 second per knee raise as a guided default; rest for the remainder.", work: [(.feature(.mediumEdge), 10, .hang, .halfCrimp), (.feature(.jug), 5, .pull, nil)], rest: 45),
            emomMinute(id: "method-emom-minute-4", title: "Minute 4 · bent-arm 15mm hang", instruction: "Hold a bent-arm hang for 15 seconds on 15mm, then rest for the remainder.", work: [(.feature(.smallEdge), 15, .hang, .halfCrimp)], rest: 45),
            emomMinute(id: "method-emom-minute-5", title: "Minute 5 · sloper hang + jug pull-ups", instruction: "Hang for 10 seconds on a sloper, then do 3 pull-ups on jugs. The app defaults to 5 seconds per pull-up before the remainder-minute rest.", work: [(.feature(.largeSlope, fallback: .roundSloper), 10, .hang, .openHand), (.feature(.jug), 15, .pull, nil)], rest: 35),
            emomMinute(id: "method-emom-minute-6", title: "Minute 6 · medium three-finger pocket", instruction: "Hang for 10 seconds on medium three-finger pockets, then rest for the remainder.", work: [(.feature(.threeFingerPocket), 10, .hang, .openHand)], rest: 50),
            emomMinute(id: "method-emom-minute-7", title: "Minute 7 · offset pull-ups", instruction: "Do 3 offset pull-ups with one hand on a jug and the other on a small edge. The app defaults to 5 seconds per pull-up before the remainder-minute rest.", work: [(.feature(.jug), 15, .pull, nil), (.feature(.smallEdge), 15, .pull, nil)], rest: 30),
            emomMinute(id: "method-emom-minute-8", title: "Minute 8 · 15mm hang", instruction: "Hang for 25 seconds on a 15mm edge, then rest for the remainder.", work: [(.feature(.smallEdge), 25, .hang, .halfCrimp)], rest: 35),
            emomMinute(id: "method-emom-minute-9", title: "Minute 9 · 20mm hang + jug knee raises", instruction: "Hang for 20 seconds on 20mm, then do 10 knee raises on jugs. The app uses 1 second per knee raise as a guided default; rest for the remainder.", work: [(.feature(.mediumEdge), 20, .hang, .halfCrimp), (.feature(.jug), 10, .pull, nil)], rest: 30),
            guidedTask(id: "method-emom-minute-10", title: "Minute 10 · max sloper", instruction: "Take a max hang on a sloper. The source does not prescribe a duration; use the stopwatch and finish the minute with any remaining rest.", accessory: "Minute 10 · max effort · stopwatch", phase: .hang, targets: [.feature(.largeSlope, fallback: .roundSloper)], duration: 60, timing: .stopwatch, gripType: .openHand)
        ])
    )

    static let latticeBeginnerGuide = TrainingPlan(
        id: "lattice.beginner-climbers-training-guide",
        title: "Lattice Beginner Climber's Foundational Guide",
        subtitle: "Reference plan, not a fabricated timed protocol; source guidance prioritizes climbing and basic strength first.",
        level: "Beginner",
        sourceLabel: "Lattice Training · The Beginner Climber's Training Guide",
        sourceURL: URL(string: "https://latticetraining.com/blog/the-beginners-guide")!,
        provenance: .adapted,
        boardID: nil,
        steps: numbered([
            conditioningTask(id: "lattice-beginner-climb-first", title: "Climb and build wall finger strength", instruction: "Prioritize climbing and varied grip practice on the wall before adding hangboarding. The source gives priorities, not a session count or timer."),
            conditioningTask(id: "lattice-beginner-assisted-pull-ups", title: "Assisted or banded pull-ups", instruction: "Build upper-body and tendon capacity with good-form pull-ups; use assistance or a band as needed. No source count is prescribed."),
            conditioningTask(id: "lattice-beginner-press-ups", title: "Press-ups", instruction: "Add good-form press-ups for general upper-body capacity. No source count is prescribed."),
            conditioningTask(id: "lattice-beginner-spiderman", title: "Floor core · Spider-Man holds", instruction: "Use Spider-Man holds to brace tension between hands and feet. Coach-guided; the source prescribes no count or duration."),
            conditioningTask(id: "lattice-beginner-dish-tucks", title: "Floor core · dish tucks", instruction: "Use dish tucks for general core conditioning. Coach-guided; do not infer a source rep scheme."),
            conditioningTask(id: "lattice-beginner-moving-plank", title: "Floor core · moving plank variations", instruction: "Use moving plank variations for core conditioning and stability. Coach-guided; no source count or duration is supplied."),
            conditioningTask(id: "lattice-beginner-deadlifts", title: "Deadlifts", instruction: "Use deadlifts for posterior-chain strength and core bracing, learning form from an experienced trainer if needed. No source count is prescribed."),
            guidedTask(id: "lattice-beginner-light-hangboard", title: "Later phase · light hangboarding", instruction: "Only later, when appropriate, use a longer light hang such as the source's example of 20 seconds with one foot on the floor. Do not max out; this is an example, not a universal prescription.", accessory: "Example only · 20s with a foot down", phase: .hang, targets: [.feature(.mediumEdge)], duration: 20, timing: .fixed, gripType: .openHand)
        ])
    )

    static let reiHangboardSample = TrainingPlan(
        id: "rei.hangboard-sample-workout",
        title: "REI · Hangboard Sample Workout",
        subtitle: "Simple five-grip sample with source alternatives, recovery warning, and pain stop retained.",
        level: "Intermediate",
        sourceLabel: "REI Expert Advice · How to Use a Hangboard to Train for Rock Climbing",
        sourceURL: URL(string: "https://www.rei.com/learn/expert-advice/how-to-use-a-hangboard-to-train-for-rock-climbing.html")!,
        provenance: .adapted,
        boardID: nil,
        steps: numbered({
            var steps: [WorkoutStep] = [
                guidedTask(id: "rei-sample-warm-up", title: "Warm-up", instruction: "Warm up with 20–30 minutes of easy climbing or light traversing, OR use 20–30-second dead hangs on the biggest holds plus several pull-up sets. The app shows a 25-minute manual preview default only; choose the source alternative that fits.", accessory: "Source: 20–30m easy climbing OR 20–30s big-hold hangs + pull-up sets", phase: .conditioning, duration: 1500, timing: .stopwatch)
            ]
            let grips: [(title: String, target: HoldTarget, grip: GripType)] = [
                ("Jug", .feature(.jug), .openHand),
                ("Three-finger pocket", .feature(.threeFingerPocket), .openHand),
                ("Medium edge", .feature(.mediumEdge), .openHand),
                ("Medium pinch", .feature(.mediumPinch, fallback: .mediumEdge), .openHand),
                ("Large sloper", .feature(.largeSlope, fallback: .roundSloper), .openHand)
            ]
            for (index, grip) in grips.enumerated() {
                for rep in 1...6 {
                    steps.append(hangStep(id: "rei-sample-\(index + 1)-rep-\(rep)", title: "\(grip.title) · rep \(rep)", instruction: "Hang for 7–10 seconds, rest for 5 seconds, and repeat six times. Stop at pain; use the source's recovery guidance.", accessory: "App default 7s hang · 5s rest · source range 7–10s", active: 7, rest: rep < 6 ? 5 : 0, targets: [grip.target], gripType: grip.grip))
                }
                if index < grips.count - 1 {
                    steps.append(recoveryStep(id: "rei-sample-\(index + 1)-recovery", title: "Three-minute grip recovery", duration: 180, accessory: "3m recovery · rest a full day or two before hard finger training"))
                }
            }
            steps.append(conditioningTask(id: "rei-sample-recovery", title: "Light stretching and recovery", instruction: "Finish with light stretching and recovery. Rest a full day or two before another hard finger-training session, and stop immediately if you feel pain.", accessory: "Recovery guidance · no source duration"))
            return steps
        }())
    )

    /// Kept as the stable featured-plan symbol used by navigation fallbacks.
    static let metoliusTenMinute = metoliusEntry

    static let all: [TrainingPlan] = {
        let metoliusPlans = [metoliusEntry, metoliusIntermediate, metoliusAdvanced]
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
            latticeLiteHomeAdaptations,
            hoopersBetaIntroductory,
            methodRepeaters,
            methodEMOM,
            latticeBeginnerGuide,
            reiHangboardSample
        ]

        #if DEBUG
        assert(metoliusPlans.count == 3, "The Metolius guide has three routines")
        for plan in metoliusPlans {
            assert(plan.provenance == .adapted)
            assert(plan.sourceURL == sourceURL)
            assert(plan.subtitle.contains("guided task timing"))
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
        assert(adaptedPlans.allSatisfy { $0.provenance == .adapted })

        let plans = metoliusPlans + adaptedPlans
        func targetResolves(_ target: HoldTarget, on board: TrainingBoard) -> Bool {
            let boardHoldIDs = Set(board.holds.map(\.id))
            if !target.holdIDs.isEmpty {
                return Set(target.holdIDs).isSubset(of: boardHoldIDs)
            }
            if let feature = target.feature {
                let acceptedFeatures = [feature] + target.fallbackFeatures
                return board.holds.contains { hold in
                    !(hold.features ?? []).isDisjoint(with: acceptedFeatures)
                }
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

        return metoliusPlans + adaptedPlans
    }()
}
