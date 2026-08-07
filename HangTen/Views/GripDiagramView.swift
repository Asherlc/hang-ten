import SwiftUI

enum GripCueSide {
    case left
    case right
}

struct GripDiagramView: View {
    let hold: BoardHold
    let gripType: GripType
    let fingerConfiguration: FingerConfiguration?

    init(
        hold: BoardHold,
        gripType: GripType? = nil,
        fingerConfiguration: FingerConfiguration? = nil
    ) {
        self.hold = hold
        self.gripType = gripType ?? hold.gripType
        self.fingerConfiguration = fingerConfiguration
    }

    private var gripLabel: String {
        gripType.label
    }

    private var fingerCue: FingerCue {
        FingerCue(
            fingerConfiguration: fingerConfiguration,
            capacity: hold.fingerCapacity
        )
    }

    var body: some View {
        VStack(spacing: 8) {
            Text(cueLabel.uppercased())
                .font(.system(size: 10, weight: .semibold, design: .rounded))
                .tracking(1.35)
                .foregroundStyle(Color.hangMuted)

            Text(gripLabel)
                .font(.system(size: 18, weight: .bold, design: .rounded))
                .foregroundStyle(Color.hangInk)

            HStack(spacing: 10) {
                GripHandCueCard(posture: gripType, fingerCue: fingerCue, side: .left)
                GripHandCueCard(posture: gripType, fingerCue: fingerCue, side: .right)
            }
        }
        .padding(.horizontal, 10)
        .padding(.vertical, 10)
        .background(Color.hangCream, in: RoundedRectangle(cornerRadius: 18, style: .continuous))
        .accessibilityElement(children: .combine)
        .accessibilityLabel("\(cueLabel), \(gripLabel), \(fingerCue.accessibilityLabel), both hands")
    }

    private var cueLabel: String {
        guard hold.cueStyle != .rounded else { return hold.name }

        if hold.cueStyle == .outerJug {
            return "Outer jugs"
        }

        let undirected = hold.name
            .replacingOccurrences(of: "Left ", with: "")
            .replacingOccurrences(of: "Right ", with: "")
            .replacingOccurrences(of: ", left", with: "")
            .replacingOccurrences(of: ", right", with: "")

        if undirected.hasSuffix(" edge") || undirected.hasSuffix(" pocket") {
            return undirected + "s"
        }
        return undirected
    }
}

/// A per-hand cue follows the same information hierarchy as the supplied
/// Grippy references: one symbol describes the grip pose and another describes
/// the participating fingers. The ordering mirrors around the physical board.
struct GripHandCueCard: View {
    let posture: GripType
    let fingerCue: FingerCue
    let side: GripCueSide

    var body: some View {
        HStack(spacing: 8) {
            if side == .left {
                gripPoseCue
                fingerSetCue
            } else {
                fingerSetCue
                gripPoseCue
            }
        }
        .frame(maxWidth: .infinity)
        .padding(.horizontal, 8)
        .padding(.vertical, 9)
        .background(
            Color.hangBackground.opacity(0.88),
            in: RoundedRectangle(cornerRadius: 15, style: .continuous)
        )
        .overlay {
            RoundedRectangle(cornerRadius: 15, style: .continuous)
                .stroke(Color.hangLine.opacity(0.85), lineWidth: 1)
        }
        .accessibilityElement(children: .ignore)
        .accessibilityLabel("\(gripPoseLabel), \(fingerCue.accessibilityLabel)")
    }

    private var gripPoseCue: some View {
        CueGlyph(label: gripPoseLabel) {
            Image(gripPoseAsset)
                .resizable()
                .renderingMode(.template)
                .scaledToFit()
                .scaleEffect(x: mirrorScale, y: 1)
                .foregroundStyle(Color.hangInk.opacity(0.82))
        }
    }

    private var fingerSetCue: some View {
        CueGlyph(label: fingerSetLabel) {
            FingerCueGlyph(fingerCue: fingerCue)
            .scaleEffect(x: mirrorScale, y: 1)
        }
    }

    private var mirrorScale: CGFloat {
        side == .right ? -1 : 1
    }

    private var gripPoseAsset: String {
        switch posture {
        case .halfCrimp:
            return "PhosphorHandGrabbing"
        case .fullCrimp:
            return "PhosphorHandFist"
        case .openHand:
            return "PhosphorHandPalm"
        }
    }

    private var gripPoseLabel: String {
        switch posture {
        case .halfCrimp: "Half crimp"
        case .fullCrimp: "Full crimp"
        case .openHand: "Open hand"
        }
    }

    private var fingerSetLabel: String {
        fingerCue.shortLabel
    }
}

enum FingerCue {
    case capacity(Int)
    case exact(FingerConfiguration)

    init(fingerConfiguration: FingerConfiguration?, capacity: Int) {
        self = fingerConfiguration.map(Self.exact) ?? .capacity(capacity)
    }

    var shortLabel: String {
        switch self {
        case let .capacity(count): "Up to \(count)"
        case let .exact(configuration): configuration.orderedFingers.map(\.shortLabel).joined(separator: "+")
        }
    }

    var accessibilityLabel: String {
        switch self {
        case let .capacity(count): "Up to \(count) fingers"
        case let .exact(configuration): "Exact fingers: \(configuration.orderedFingers.namedList)"
        }
    }
}

private struct FingerCueGlyph: View {
    let fingerCue: FingerCue

    var body: some View {
        switch fingerCue {
        case let .capacity(count):
            ZStack(alignment: .bottomTrailing) {
                Image(systemName: "hand.raised.fill")
                    .resizable()
                    .scaledToFit()
                    .foregroundStyle(Color.holdActive.opacity(0.68))
                Text("≤\(count)")
                    .font(.system(size: 11, weight: .heavy, design: .rounded))
                    .foregroundStyle(Color.hangInk)
                    .padding(.horizontal, 4)
                    .padding(.vertical, 2)
                    .background(Color.hangCream, in: Capsule())
            }
        case let .exact(configuration):
            HStack(alignment: .bottom, spacing: 3) {
                ForEach(FingerSlot.allCases) { finger in
                    RoundedRectangle(cornerRadius: 4, style: .continuous)
                        .fill(
                            configuration.engagedFingers.contains(finger)
                                ? Color.holdActive
                                : Color.hangLine.opacity(0.45)
                        )
                        .overlay {
                            RoundedRectangle(cornerRadius: 4, style: .continuous)
                                .stroke(Color.hangInk.opacity(0.25), lineWidth: 1)
                        }
                        .frame(width: 7, height: finger.height * 0.62)
                }
            }
            .frame(maxHeight: .infinity, alignment: .bottom)
        }
    }
}

private extension FingerSlot {
    var shortLabel: String {
        switch self {
        case .index: "I"
        case .middle: "M"
        case .ring: "R"
        case .pinky: "P"
        }
    }

    var displayName: String {
        switch self {
        case .index: "index"
        case .middle: "middle"
        case .ring: "ring"
        case .pinky: "pinky"
        }
    }
}

private extension Array where Element == FingerSlot {
    var namedList: String {
        let names = map(\.displayName)
        switch names.count {
        case 0: return "none"
        case 1: return names[0]
        case 2: return "\(names[0]) and \(names[1])"
        default: return "\(names.dropLast().joined(separator: ", ")), and \(names[names.count - 1])"
        }
    }
}

private struct CueGlyph<Glyph: View>: View {
    let label: String
    @ViewBuilder let glyph: () -> Glyph

    var body: some View {
        VStack(spacing: 4) {
            glyph()
                .frame(width: 39, height: 44)

            Text(label)
                .font(.system(size: 10, weight: .bold, design: .rounded))
                .foregroundStyle(Color.hangMuted)
                .lineLimit(1)
                .minimumScaleFactor(0.68)
        }
        .frame(maxWidth: .infinity)
    }
}
