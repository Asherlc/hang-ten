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
    let activeDurationOverride: TimeInterval?

    init(
        id: String,
        number: Int,
        title: String,
        instruction: String,
        accessory: String,
        duration: TimeInterval,
        phase: WorkoutPhase,
        targets: [HoldTarget],
        gripType: GripType? = nil,
        activeDuration: TimeInterval? = nil
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
        self.activeDurationOverride = activeDuration
    }

    var activeDuration: TimeInterval {
        guard phase == .hang else { return duration }
        return min(duration, activeDurationOverride ?? 10)
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
            gripType: gripType,
            activeDuration: activeDurationOverride
        )
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

    static let evidenceOverviewURL = URL(string: "https://pmc.ncbi.nlm.nih.gov/articles/PMC9806751/")!

    private static func warmUpStep(id: String, duration: TimeInterval = 180) -> WorkoutStep {
        WorkoutStep(
            id: id,
            number: 0,
            title: "Progressive warm-up",
            instruction: "Move gently on the outer jugs, then add a few easy edge contacts. Keep your grip open and your shoulders engaged.",
            accessory: "Easy movement · do not fatigue",
            duration: duration,
            phase: .warmUp,
            targets: [.ids("jug-left", "jug-right")],
            gripType: .openHand
        )
    }

    private static func hangStep(
        id: String,
        title: String,
        instruction: String,
        accessory: String,
        active: TimeInterval,
        rest: TimeInterval,
        targets: [HoldTarget],
        gripType: GripType
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
            gripType: gripType,
            activeDuration: active
        )
    }

    private static func recoveryStep(id: String, title: String, duration: TimeInterval, accessory: String) -> WorkoutStep {
        WorkoutStep(
            id: id,
            number: 0,
            title: title,
            instruction: "Step off the board, shake out, and breathe before the next effort.",
            accessory: accessory,
            duration: duration,
            phase: .rest,
            targets: []
        )
    }

    private static func coolDownStep(id: String) -> WorkoutStep {
        WorkoutStep(
            id: id,
            number: 0,
            title: "Cool down",
            instruction: "Stay on the easy jugs and let your breathing settle before you step away.",
            accessory: "Easy movement · gentle release",
            duration: 60,
            phase: .coolDown,
            targets: [.ids("jug-left", "jug-right")],
            gripType: .openHand
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
        subtitle: "Heavy 7-second hangs for peak finger strength.",
        level: "Advanced",
        sourceLabel: "Lattice max hang protocol",
        sourceURL: URL(string: "https://latticetraining.com/workout/1c4cc25a-ebe8-4930-8541-5b604a831c5f/half-4-hang-max/")!,
        boardID: BoardCatalog.compactII.id,
        steps: numbered([
            warmUpStep(id: "max-hangs-warm-up"),
            hangStep(
                id: "max-hangs-1",
                title: "Max hang · set 1",
                instruction: "Use added weight or assistance so seven seconds is near-max without losing shoulder position or grip shape.",
                accessory: "7s hang · 3m recovery · half crimp",
                active: 7,
                rest: 180,
                targets: [.ids("edge-19-left", "edge-19-right")],
                gripType: .halfCrimp
            ),
            hangStep(
                id: "max-hangs-2",
                title: "Max hang · set 2",
                instruction: "Repeat the same load or make a small adjustment. Stop before form breaks.",
                accessory: "7s hang · 3m recovery · half crimp",
                active: 7,
                rest: 180,
                targets: [.ids("edge-19-left", "edge-19-right")],
                gripType: .halfCrimp
            ),
            hangStep(
                id: "max-hangs-3",
                title: "Max hang · set 3",
                instruction: "Keep the effort high and the movement quiet. Do not turn this into a full-crimp test.",
                accessory: "7s hang · 3m recovery · half crimp",
                active: 7,
                rest: 180,
                targets: [.ids("edge-19-left", "edge-19-right")],
                gripType: .halfCrimp
            ),
            hangStep(
                id: "max-hangs-4",
                title: "Max hang · set 4",
                instruction: "Take the full recovery and reproduce your best controlled effort.",
                accessory: "7s hang · 3m recovery · half crimp",
                active: 7,
                rest: 180,
                targets: [.ids("edge-19-left", "edge-19-right")],
                gripType: .halfCrimp
            ),
            hangStep(
                id: "max-hangs-5",
                title: "Max hang · set 5",
                instruction: "Finish with one high-quality effort. Log the load or assistance used today.",
                accessory: "7s hang · final effort",
                active: 7,
                rest: 0,
                targets: [.ids("edge-19-left", "edge-19-right")],
                gripType: .halfCrimp
            ),
            coolDownStep(id: "max-hangs-cool-down")
        ])
    )

    static let forceF80 = TrainingPlan(
        id: "research.force-feedback-f80",
        title: "F80 Force Board",
        subtitle: "80% force-feedback repeaters for strength and endurance.",
        level: "Advanced",
        sourceLabel: "Frontiers force-feedback hangboard study",
        sourceURL: URL(string: "https://www.frontiersin.org/journals/sports-and-active-living/articles/10.3389/fspor.2022.862782/full")!,
        boardID: BoardCatalog.compactII.id,
        steps: numbered({
            var steps = [warmUpStep(id: "f80-warm-up")]
            for set in 1...3 {
                for rep in 1...12 {
                    steps.append(
                        hangStep(
                            id: "f80-set-\(set)-rep-\(rep)",
                            title: "F80 · set \(set), rep \(rep)",
                            instruction: "Hang at roughly 80% of your tested maximum finger force. Keep both hands even and reduce load if force or shape drops.",
                            accessory: "10s hang · 6s rest · 80% target",
                            active: 10,
                            rest: 6,
                            targets: [.ids("edge-19-left", "edge-19-right")],
                            gripType: .halfCrimp
                        )
                    )
                }
                if set < 3 {
                    steps.append(
                        recoveryStep(
                            id: "f80-set-\(set)-recovery",
                            title: "Eight-minute set recovery",
                            duration: 480,
                            accessory: "8m recovery · step off the board"
                        )
                    )
                }
            }
            steps.append(coolDownStep(id: "f80-cool-down"))
            return steps
        }())
    )

    static let forceF100 = TrainingPlan(
        id: "research.force-feedback-f100",
        title: "F100 Force Board",
        subtitle: "Maximal force-feedback hangs with full recovery.",
        level: "Expert",
        sourceLabel: "Frontiers force-feedback hangboard study",
        sourceURL: URL(string: "https://www.frontiersin.org/journals/sports-and-active-living/articles/10.3389/fspor.2022.862782/full")!,
        boardID: BoardCatalog.compactII.id,
        steps: numbered({
            var steps = [warmUpStep(id: "f100-warm-up")]
            for set in 1...2 {
                for round in 1...6 {
                    steps.append(
                        hangStep(
                            id: "f100-set-\(set)-round-\(round)-left",
                            title: "F100 · left hand",
                            instruction: "On a force board, take one maximal six-second effort with the left hand. Use assistance if you cannot keep the intended edge position.",
                            accessory: "6s max · alternate hands",
                            active: 6,
                            rest: 0,
                            targets: [.ids("edge-19-left")],
                            gripType: .halfCrimp
                        )
                    )
                    steps.append(
                        hangStep(
                            id: "f100-set-\(set)-round-\(round)-right",
                            title: "F100 · right hand",
                            instruction: "Repeat the maximal six-second effort on the right hand. Keep the shoulder packed and stop if pain appears.",
                            accessory: "6s max · alternate hands",
                            active: 6,
                            rest: round == 6 ? (set == 1 ? 300 : 0) : 168,
                            targets: [.ids("edge-19-right")],
                            gripType: .halfCrimp
                        )
                    )
                }
            }
            steps.append(coolDownStep(id: "f100-cool-down"))
            return steps
        }())
    )

    static let evaIntHangs = TrainingPlan(
        id: "research.eva-int-hangs",
        title: "Eva IntHangs",
        subtitle: "Intermittent 10/5 hangs for finger endurance.",
        level: "Intermediate+",
        sourceLabel: "Eva López hangboard comparison",
        sourceURL: URL(string: "https://pubmed.ncbi.nlm.nih.gov/30988852/")!,
        boardID: BoardCatalog.compactII.id,
        steps: numbered({
            var steps = [warmUpStep(id: "int-hangs-warm-up")]
            for set in 1...3 {
                for rep in 1...5 {
                    steps.append(
                        hangStep(
                            id: "int-hangs-set-\(set)-rep-\(rep)",
                            title: "IntHang · set \(set), rep \(rep)",
                            instruction: "Hang for ten seconds, then relax for five. Choose assistance or an edge where the final rep remains controlled but challenging.",
                            accessory: "10s hang · 5s rest · 5 reps",
                            active: 10,
                            rest: rep < 5 ? 5 : 0,
                            targets: [.ids("edge-19-left", "edge-19-right")],
                            gripType: .halfCrimp
                        )
                    )
                }
                if set < 3 {
                    steps.append(
                        recoveryStep(
                            id: "int-hangs-set-\(set)-recovery",
                            title: "One-minute set recovery",
                            duration: 60,
                            accessory: "1m recovery · shake out"
                        )
                    )
                }
            }
            steps.append(coolDownStep(id: "int-hangs-cool-down"))
            return steps
        }())
    )

    static let repeaters = TrainingPlan(
        id: "research.seven-three-repeaters",
        title: "7/3 Repeaters",
        subtitle: "The classic repeater format across three board positions.",
        level: "Intermediate",
        sourceLabel: "Beastmaker 7/3 study protocol",
        sourceURL: URL(string: "https://www.frontiersin.org/journals/sports-and-active-living/articles/10.3389/fspor.2022.888158/full")!,
        boardID: BoardCatalog.compactII.id,
        steps: numbered({
            var steps = [warmUpStep(id: "repeaters-warm-up")]
            let grips: [(title: String, targets: [HoldTarget], grip: GripType)] = [
                ("29 mm open edge", [.ids("edge-29-left", "edge-29-right")], .openHand),
                ("Deep four-finger pocket", [.ids("pocket-4-deep-left", "pocket-4-deep-right")], .fourFingerPocket),
                ("19 mm half crimp", [.ids("edge-19-left", "edge-19-right")], .halfCrimp)
            ]

            for (index, grip) in grips.enumerated() {
                for rep in 1...6 {
                    steps.append(
                        hangStep(
                            id: "repeaters-grip-\(index + 1)-rep-\(rep)",
                            title: "7/3 · \(grip.title), rep \(rep)",
                            instruction: "Hang for seven seconds and rest for three. Use foot assistance or reduce load so the last repetition stays technically clean.",
                            accessory: "7s hang · 3s rest · 6 reps",
                            active: 7,
                            rest: rep < 6 ? 3 : 0,
                            targets: grip.targets,
                            gripType: grip.grip
                        )
                    )
                }
                if index < grips.count - 1 {
                    steps.append(
                        recoveryStep(
                            id: "repeaters-grip-\(index + 1)-recovery",
                            title: "Two-minute grip recovery",
                            duration: 120,
                            accessory: "2m recovery · switch grip"
                        )
                    )
                }
            }
            steps.append(coolDownStep(id: "repeaters-cool-down"))
            return steps
        }())
    )

    static let abrahangs = TrainingPlan(
        id: "research.abrahangs",
        title: "Abrahangs",
        subtitle: "Low-intensity, feet-supported hangs across varied grips.",
        level: "Supplemental",
        sourceLabel: "Lattice Abrahangs protocol",
        sourceURL: URL(string: "https://latticetraining.com/workout/1832c13b-14c1-444c-82a2-e72b22a6fb13/abrahangs-protocol")!,
        boardID: BoardCatalog.compactII.id,
        steps: numbered({
            var steps = [warmUpStep(id: "abrahangs-warm-up", duration: 120)]
            let grips: [(title: String, targets: [HoldTarget], grip: GripType)] = [
                ("29 mm open edge", [.ids("edge-29-left", "edge-29-right")], .openHand),
                ("Deep four-finger pocket", [.ids("pocket-4-deep-left", "pocket-4-deep-right")], .fourFingerPocket),
                ("Center sloper", [.ids("sloper-center")], .sloper),
                ("Three-finger pocket", [.ids("pocket-3-shallow-left", "pocket-3-shallow-right")], .threeFingerPocket),
                ("19 mm open edge", [.ids("edge-19-left", "edge-19-right")], .openHand),
                ("29 mm half crimp", [.ids("edge-29-left", "edge-29-right")], .halfCrimp)
            ]

            for (index, grip) in grips.enumerated() {
                steps.append(
                    hangStep(
                        id: "abrahangs-grip-\(index + 1)",
                        title: "Abrahang · \(grip.title)",
                        instruction: "Keep both feet supported. Apply only a small strain and stop if your fingers shift, pinch, or become painful.",
                        accessory: "10s hang · 50s rest · feet supported",
                        active: 10,
                        rest: 50,
                        targets: grip.targets,
                        gripType: grip.grip
                    )
                )
            }
            steps.append(coolDownStep(id: "abrahangs-cool-down"))
            return steps
        }())
    )

    static let horst753 = TrainingPlan(
        id: "coach.horst-seven-fifty-three",
        title: "7–53 Max Hangs",
        subtitle: "Short maximal hangs with long, complete recoveries.",
        level: "Advanced",
        sourceLabel: "Eric Hörst fingerboard protocols",
        sourceURL: URL(string: "https://trainingforclimbing.com/4-fingerboard-strength-protocols-that-work/")!,
        boardID: BoardCatalog.compactII.id,
        steps: numbered({
            var steps = [warmUpStep(id: "horst-753-warm-up")]
            let grips: [(title: String, targets: [HoldTarget], grip: GripType)] = [
                ("29 mm half crimp", [.ids("edge-29-left", "edge-29-right")], .halfCrimp),
                ("19 mm half crimp", [.ids("edge-19-left", "edge-19-right")], .halfCrimp),
                ("Deep four-finger pocket", [.ids("pocket-4-deep-left", "pocket-4-deep-right")], .fourFingerPocket)
            ]

            for (index, grip) in grips.enumerated() {
                for rep in 1...3 {
                    steps.append(
                        hangStep(
                            id: "horst-753-grip-\(index + 1)-rep-\(rep)",
                            title: "7–53 · \(grip.title), rep \(rep)",
                            instruction: "Take a near-maximal seven-second effort, then step off completely for fifty-three seconds. Keep the grip controlled.",
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
                            accessory: "3m recovery · switch grip"
                        )
                    )
                }
            }
            steps.append(coolDownStep(id: "horst-753-cool-down"))
            return steps
        }())
    )

    static let ladders = TrainingPlan(
        id: "coach.bechtel-three-six-nine",
        title: "3–6–9 Ladders",
        subtitle: "A progressive volume ladder for controlled finger strength.",
        level: "Intermediate+",
        sourceLabel: "Steve Bechtel 3–6–9 ladder protocol",
        sourceURL: URL(string: "https://strengthclimbing.com/steve-bechtels-3-6-9-ladders/")!,
        boardID: BoardCatalog.compactII.id,
        steps: numbered({
            var steps = [warmUpStep(id: "ladders-warm-up")]
            for round in 1...3 {
                for (index, hangSeconds) in [3, 6, 9].enumerated() {
                    steps.append(
                        hangStep(
                            id: "ladders-round-\(round)-\(hangSeconds)",
                            title: "Ladder \(round) · \(hangSeconds) seconds",
                            instruction: "Use a load that would allow roughly twelve seconds at most. Stay smooth as the hold time increases.",
                            accessory: "\(hangSeconds)s hang · 30s rest",
                            active: TimeInterval(hangSeconds),
                            rest: index < 2 ? 30 : 0,
                            targets: [.ids("edge-29-left", "edge-29-right")],
                            gripType: .halfCrimp
                        )
                    )
                }
                if round < 3 {
                    steps.append(
                        recoveryStep(
                            id: "ladders-round-\(round)-recovery",
                            title: "Three-minute ladder recovery",
                            duration: 180,
                            accessory: "3m recovery · repeat the ladder"
                        )
                    )
                }
            }
            steps.append(coolDownStep(id: "ladders-cool-down"))
            return steps
        }())
    )

    static let densityHangs = TrainingPlan(
        id: "coach.density-hangs",
        title: "Density Hangs",
        subtitle: "Longer submaximal hangs for finger capacity.",
        level: "Intermediate+",
        sourceLabel: "Tyler Nelson density hang protocol",
        sourceURL: URL(string: "https://strengthclimbing.com/dr-tyler-nelsons-density-hangs-finger-training-for-rock-climbing/")!,
        boardID: BoardCatalog.compactII.id,
        steps: numbered({
            var steps = [warmUpStep(id: "density-warm-up")]
            let grips: [(title: String, targets: [HoldTarget], grip: GripType)] = [
                ("29 mm open edge", [.ids("edge-29-left", "edge-29-right")], .openHand),
                ("Deep four-finger pocket", [.ids("pocket-4-deep-left", "pocket-4-deep-right")], .fourFingerPocket)
            ]

            for (holdIndex, grip) in grips.enumerated() {
                for set in 1...2 {
                    for rep in 1...3 {
                        steps.append(
                            hangStep(
                                id: "density-hold-\(holdIndex + 1)-set-\(set)-rep-\(rep)",
                                title: "Density · \(grip.title), set \(set), rep \(rep)",
                                instruction: "Hang for thirty seconds at a load you can control, then rest for fifteen. Use foot assistance before your grip shape changes.",
                                accessory: "30s hang · 15s rest · 2:1 density",
                                active: 30,
                                rest: rep < 3 ? 15 : 0,
                                targets: grip.targets,
                                gripType: grip.grip
                            )
                        )
                    }
                    if set < 2 {
                        steps.append(
                            recoveryStep(
                                id: "density-hold-\(holdIndex + 1)-set-\(set)-recovery",
                                title: "Three-minute set recovery",
                                duration: 180,
                                accessory: "3m recovery · repeat the hold"
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
                            accessory: "3m recovery · change hold"
                        )
                    )
                }
            }
            steps.append(coolDownStep(id: "density-cool-down"))
            return steps
        }())
    )

    static let zlagboardEndurance = TrainingPlan(
        id: "device.zlagboard-sixty-sixty",
        title: "Zlagboard 60/60 Endurance",
        subtitle: "Ten long intervals with foot-supported scaling.",
        level: "Intermediate",
        sourceLabel: "Zlagboard endurance protocol",
        sourceURL: URL(string: "https://strengthclimbing.com/zlagboard-forearm-endurance-workout/")!,
        boardID: BoardCatalog.compactII.id,
        steps: numbered({
            var steps = [warmUpStep(id: "zlagboard-warm-up")]
            for interval in 1...10 {
                steps.append(
                    hangStep(
                        id: "zlagboard-interval-\(interval)",
                        title: "60/60 · interval \(interval)",
                        instruction: "Keep your feet supported and hold for sixty seconds. Adjust assistance before your shoulders or fingers lose position.",
                        accessory: "60s hang · 60s rest · feet supported",
                        active: 60,
                        rest: interval < 10 ? 60 : 0,
                        targets: [.ids("edge-29-left", "edge-29-right")],
                        gripType: .openHand
                    )
                )
            }
            steps.append(coolDownStep(id: "zlagboard-cool-down"))
            return steps
        }())
    )

    static let all: [TrainingPlan] = [
        metoliusTenMinute,
        maxHangs,
        forceF80,
        forceF100,
        evaIntHangs,
        repeaters,
        abrahangs,
        horst753,
        ladders,
        densityHangs,
        zlagboardEndurance
    ]
}
