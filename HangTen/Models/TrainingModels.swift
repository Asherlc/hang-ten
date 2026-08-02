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

enum HoldKind: String, CaseIterable, Hashable, Identifiable {
    case jug
    case edge
    case pocket
    case sloper

    var id: String { rawValue }

    var label: String {
        switch self {
        case .jug: "Jugs"
        case .edge: "Edges"
        case .pocket: "Pockets"
        case .sloper: "Sloper"
        }
    }

    var tint: Color {
        switch self {
        case .jug: .holdBlue
        case .edge: .holdOrange
        case .pocket: .holdPurple
        case .sloper: .holdTeal
        }
    }
}

enum HoldCueStyle: String, Hashable {
    case outerJug
    case slot
    case rounded
}

enum FingerSlot: String, CaseIterable, Hashable, Identifiable {
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

enum GripType: String, CaseIterable, Hashable, Identifiable {
    case openHand
    case halfCrimp
    case fullCrimp
    case fourFingerPocket
    case threeFingerPocket
    case sloper

    var id: String { rawValue }

    var label: String {
        switch self {
        case .openHand: "Open hand"
        case .halfCrimp: "Half crimp"
        case .fullCrimp: "Full crimp"
        case .fourFingerPocket: "Four-finger pocket"
        case .threeFingerPocket: "Three-finger pocket"
        case .sloper: "Open-hand sloper"
        }
    }

    var activeFingers: Set<FingerSlot> {
        switch self {
        case .openHand, .halfCrimp, .fullCrimp, .fourFingerPocket, .sloper:
            Set(FingerSlot.allCases)
        case .threeFingerPocket:
            [.index, .middle, .ring]
        }
    }

    var thumbEngaged: Bool {
        self == .fullCrimp
    }
}

struct BoardHold: Identifiable, Hashable {
    let id: String
    let name: String
    let shortLabel: String
    let detail: String
    let kind: HoldKind
    let gripType: GripType
    let cueStyle: HoldCueStyle
    let frame: HoldFrame

    init(
        id: String,
        name: String,
        shortLabel: String,
        detail: String,
        kind: HoldKind,
        frame: HoldFrame,
        gripType: GripType = .openHand,
        cueStyle: HoldCueStyle? = nil
    ) {
        self.id = id
        self.name = name
        self.shortLabel = shortLabel
        self.detail = detail
        self.kind = kind
        self.gripType = gripType
        self.cueStyle = cueStyle ?? (kind == .jug ? .outerJug : (kind == .sloper ? .rounded : .slot))
        self.frame = frame
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
    let productURL: URL
    /// Optional board-specific reference art. Boards without a photo use the
    /// vector fallback, so adding another board does not require an image.
    let photoAssetName: String?

    var displayName: String {
        "\(manufacturer) \(name)"
    }
}

struct HoldTarget: Hashable {
    let holdIDs: [String]
    let kind: HoldKind?

    static func ids(_ holdIDs: String...) -> HoldTarget {
        HoldTarget(holdIDs: holdIDs, kind: nil)
    }

    static func kind(_ kind: HoldKind) -> HoldTarget {
        HoldTarget(holdIDs: [], kind: kind)
    }
}

enum WorkoutPhase: String, Hashable {
    case warmUp
    case hang
    case rest
    case pull
    case coolDown

    var label: String {
        switch self {
        case .warmUp: "Warm up"
        case .hang: "Hang"
        case .rest: "Rest"
        case .pull: "Pull"
        case .coolDown: "Cool down"
        }
    }

    var tint: Color {
        switch self {
        case .warmUp: .warmUp
        case .hang: .hangGreen
        case .rest: .restBlue
        case .pull: .pullOrange
        case .coolDown: .coolDownPurple
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
    let gripType: GripType?

    init(
        id: String,
        number: Int,
        title: String,
        instruction: String,
        accessory: String,
        duration: TimeInterval,
        phase: WorkoutPhase,
        targets: [HoldTarget],
        gripType: GripType? = nil
    ) {
        self.id = id
        self.number = number
        self.title = title
        self.instruction = instruction
        self.accessory = accessory
        self.duration = duration
        self.phase = phase
        self.targets = targets
        self.gripType = gripType
    }

    var activeDuration: TimeInterval {
        phase == .hang ? min(10, duration) : duration
    }

    var hasRestInterval: Bool {
        duration > activeDuration
    }

    var restDuration: TimeInterval {
        max(0, duration - activeDuration)
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
}

struct TrainingPlan: Identifiable, Hashable {
    let id: String
    let title: String
    let subtitle: String
    let level: String
    let sourceLabel: String
    let sourceURL: URL
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
    // Board geometry is data, not view code. Add new TrainingBoard values here
    // and plans can resolve their hold IDs without changing the workout UI.
    static let compactII = TrainingBoard(
        id: "metolius.wood-grips-compact-ii",
        manufacturer: "Metolius",
        name: "Wood Grips Compact II",
        subtitle: "A compact FSC-certified wood board for everyday strength work.",
        dimensions: "24\" × 6.2\"",
        aspectRatio: 3.88,
        holds: [
            BoardHold(
                id: "jug-left",
                name: "Left outer jug",
                shortLabel: "J",
                detail: "Open-hand jug",
                kind: .jug,
                frame: HoldFrame(x: 0.03, y: 0.09, width: 0.15, height: 0.82)
            ),
            BoardHold(
                id: "jug-right",
                name: "Right outer jug",
                shortLabel: "J",
                detail: "Open-hand jug",
                kind: .jug,
                frame: HoldFrame(x: 0.82, y: 0.09, width: 0.15, height: 0.82)
            ),
            BoardHold(
                id: "sloper-center",
                name: "Center sloper",
                shortLabel: "S",
                detail: "Rounded open-hand hold",
                kind: .sloper,
                frame: HoldFrame(x: 0.431, y: 0.35, width: 0.136, height: 0.17),
                gripType: .sloper
            ),
            BoardHold(
                id: "edge-29-left",
                name: "Left 29 mm edge",
                shortLabel: "29",
                detail: "Deep edge",
                kind: .edge,
                frame: HoldFrame(x: 0.217, y: 0.35, width: 0.107, height: 0.17)
            ),
            BoardHold(
                id: "edge-29-right",
                name: "Right 29 mm edge",
                shortLabel: "29",
                detail: "Deep edge",
                kind: .edge,
                frame: HoldFrame(x: 0.680, y: 0.35, width: 0.107, height: 0.17)
            ),
            BoardHold(
                id: "edge-19-left",
                name: "Left 19 mm edge",
                shortLabel: "19",
                detail: "Shallow edge",
                kind: .edge,
                frame: HoldFrame(x: 0.228, y: 0.70, width: 0.107, height: 0.17)
            ),
            BoardHold(
                id: "edge-19-right",
                name: "Right 19 mm edge",
                shortLabel: "19",
                detail: "Shallow edge",
                kind: .edge,
                frame: HoldFrame(x: 0.680, y: 0.70, width: 0.107, height: 0.17)
            ),
            BoardHold(
                id: "pocket-4-deep-left",
                name: "Deep four-finger pocket, left",
                shortLabel: "4D",
                detail: "Four-finger pocket",
                kind: .pocket,
                frame: HoldFrame(x: 0.344, y: 0.35, width: 0.067, height: 0.17),
                gripType: .fourFingerPocket
            ),
            BoardHold(
                id: "pocket-4-deep-right",
                name: "Deep four-finger pocket, right",
                shortLabel: "4D",
                detail: "Four-finger pocket",
                kind: .pocket,
                frame: HoldFrame(x: 0.596, y: 0.35, width: 0.068, height: 0.17),
                gripType: .fourFingerPocket
            ),
            BoardHold(
                id: "pocket-3-shallow-left",
                name: "Shallow three-finger pocket, left",
                shortLabel: "3S",
                detail: "Three-finger pocket",
                kind: .pocket,
                frame: HoldFrame(x: 0.348, y: 0.70, width: 0.067, height: 0.17),
                gripType: .threeFingerPocket
            ),
            BoardHold(
                id: "pocket-3-shallow-right",
                name: "Shallow three-finger pocket, right",
                shortLabel: "3S",
                detail: "Three-finger pocket",
                kind: .pocket,
                frame: HoldFrame(x: 0.596, y: 0.70, width: 0.068, height: 0.17),
                gripType: .threeFingerPocket
            ),
            BoardHold(
                id: "sloper-center-lower",
                name: "Lower center sloper",
                shortLabel: "S",
                detail: "Rounded open-hand hold",
                kind: .sloper,
                frame: HoldFrame(x: 0.431, y: 0.70, width: 0.136, height: 0.17),
                gripType: .sloper
            )
        ],
        productURL: URL(string: "https://www.metoliusclimbing.com/collections/training-boards/products/wood-grips-ii-training-boards")!,
        photoAssetName: "CompactBoardIllustration"
    )

    static let all: [TrainingBoard] = [compactII]

    static func board(for id: String?) -> TrainingBoard {
        all.first { $0.id == id } ?? compactII
    }
}

enum PlanCatalog {
    static let metoliusTenMinute = TrainingPlan(
        id: "metolius.compact-ii.ten-minute",
        title: "Metolius 10-minute sequence",
        subtitle: "A guided Compact II translation of Metolius's ten-minute format.",
        level: "Foundation",
        sourceLabel: "Metolius Contact Training Guide",
        sourceURL: URL(string: "https://www.metoliusclimbing.com/pages/contact-training-guide")!,
        boardID: BoardCatalog.compactII.id,
        steps: [
            WorkoutStep(
                id: "warm-up-jugs",
                number: 1,
                title: "Easy warm-up",
                instruction: "Move gently on the outer jugs. Keep your grip open and your elbows soft.",
                accessory: "Ease in — this should feel easy.",
                duration: 60,
                phase: .warmUp,
                targets: [.ids("jug-left", "jug-right")],
                gripType: .openHand
            ),
            WorkoutStep(
                id: "hang-29mm",
                number: 2,
                title: "29 mm edge",
                instruction: "Dead hang with both hands on the deep edges. Use assistance if needed.",
                accessory: "10s hang · 50s rest",
                duration: 60,
                phase: .hang,
                targets: [.ids("edge-29-left", "edge-29-right")],
                gripType: .openHand
            ),
            WorkoutStep(
                id: "hang-deep-pocket",
                number: 3,
                title: "Deep pockets",
                instruction: "Hang on the deep four-finger pockets with an open hand.",
                accessory: "10s hang · 50s rest",
                duration: 60,
                phase: .hang,
                targets: [.ids("pocket-4-deep-left", "pocket-4-deep-right")],
                gripType: .fourFingerPocket
            ),
            WorkoutStep(
                id: "hang-sloper",
                number: 4,
                title: "Center sloper",
                instruction: "Stay relaxed through the shoulders and keep contact even across both hands.",
                accessory: "10s hang · 50s rest",
                duration: 60,
                phase: .hang,
                targets: [.ids("sloper-center")],
                gripType: .sloper
            ),
            WorkoutStep(
                id: "hang-three-finger",
                number: 5,
                title: "Three-finger pockets",
                instruction: "Use the deeper portion of the three-finger pockets first; stop before form breaks.",
                accessory: "10s hang · 50s rest",
                duration: 60,
                phase: .hang,
                targets: [.ids("pocket-3-shallow-left", "pocket-3-shallow-right")],
                gripType: .threeFingerPocket
            ),
            WorkoutStep(
                id: "hang-19mm",
                number: 6,
                title: "19 mm edge",
                instruction: "Use an open-hand edge grip. Take weight off with your feet or a pulley when necessary.",
                accessory: "10s hang · 50s rest",
                duration: 60,
                phase: .hang,
                targets: [.ids("edge-19-left", "edge-19-right")],
                gripType: .openHand
            ),
            WorkoutStep(
                id: "repeat-deep-pocket",
                number: 7,
                title: "Pocket repeat",
                instruction: "Return to the deep pockets at a controlled intensity. Quality beats fatigue.",
                accessory: "10s hang · 50s rest",
                duration: 60,
                phase: .hang,
                targets: [.ids("pocket-4-deep-left", "pocket-4-deep-right")],
                gripType: .fourFingerPocket
            ),
            WorkoutStep(
                id: "repeat-29mm",
                number: 8,
                title: "Edge repeat",
                instruction: "Repeat the 29 mm edge with smooth shoulders and no sudden loading.",
                accessory: "10s hang · 50s rest",
                duration: 60,
                phase: .hang,
                targets: [.ids("edge-29-left", "edge-29-right")],
                gripType: .openHand
            ),
            WorkoutStep(
                id: "pull-ups-jugs",
                number: 9,
                title: "Smooth pull-ups",
                instruction: "Use the outer jugs for a few strict, controlled reps. Keep the lower body quiet.",
                accessory: "Stop well before failure.",
                duration: 60,
                phase: .pull,
                targets: [.ids("jug-left", "jug-right")],
                gripType: .openHand
            ),
            WorkoutStep(
                id: "cool-down-jugs",
                number: 10,
                title: "Cool down",
                instruction: "Stay on the easy jugs and let your breathing settle before you step away.",
                accessory: "Easy movement · gentle release",
                duration: 60,
                phase: .coolDown,
                targets: [.ids("jug-left", "jug-right")],
                gripType: .openHand
            )
        ]
    )

    static let all: [TrainingPlan] = [metoliusTenMinute]
}
