import SwiftUI

enum GripCueSide {
    case left
    case right
}

struct GripDiagramView: View {
    let hold: BoardHold
    let gripType: GripType?
    let fingerConfiguration: FingerConfiguration?

    init(
        hold: BoardHold,
        gripType: GripType?,
        fingerConfiguration: FingerConfiguration? = nil
    ) {
        self.hold = hold
        self.gripType = gripType
        self.fingerConfiguration = fingerConfiguration
    }

    var body: some View {
        VStack(spacing: 8) {
            Text(cueLabel.uppercased())
                .font(.system(size: 10, weight: .semibold, design: .rounded))
                .tracking(1.35)
                .foregroundStyle(Color.hangMuted)

            if let gripType {
                Text(gripType.label)
                    .font(.system(size: 18, weight: .bold, design: .rounded))
                    .foregroundStyle(Color.hangInk)
            } else {
                Text("Grip not specified")
                    .font(.system(size: 16, weight: .semibold, design: .rounded))
                    .foregroundStyle(Color.hangMuted)
            }

            HStack(spacing: 10) {
                GripHandCueCard(
                    posture: gripType,
                    fingerConfiguration: fingerConfiguration,
                    side: .left
                )
                GripHandCueCard(
                    posture: gripType,
                    fingerConfiguration: fingerConfiguration,
                    side: .right
                )
            }
        }
        .padding(.horizontal, 10)
        .padding(.vertical, 10)
        .background(Color.hangCream, in: RoundedRectangle(cornerRadius: 18, style: .continuous))
        .accessibilityElement(children: .combine)
        .accessibilityLabel("\(cueLabel), \(accessibilityCueLabel), both hands")
    }

    private var cueLabel: String {
        guard hold.kind != .sloper else { return hold.name }

        if hold.kind == .jug,
           hold.name.localizedCaseInsensitiveContains("outer") {
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

    private var accessibilityCueLabel: String {
        [
            gripType?.label ?? "Grip not specified",
            fingerConfiguration.map { "Exact fingers: \($0.orderedFingers.namedList)" }
        ]
            .compactMap { $0 }
            .joined(separator: ", ")
    }
}

/// A per-hand cue follows the same information hierarchy as the supplied
/// Grippy references: one symbol describes the grip pose and another describes
/// the participating fingers. The ordering mirrors around the physical board.
struct GripHandCueCard: View {
    let posture: GripType?
    let fingerConfiguration: FingerConfiguration?
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
        .accessibilityLabel(accessibilityLabel)
    }

    @ViewBuilder private var gripPoseCue: some View {
        if let posture {
            CueGlyph(label: gripPoseLabel(for: posture)) {
                Image(gripPoseAsset(for: posture))
                    .resizable()
                    .renderingMode(.template)
                    .scaledToFit()
                    .scaleEffect(x: mirrorScale, y: 1)
                    .foregroundStyle(Color.hangInk.opacity(0.82))
            }
        }
    }

    @ViewBuilder private var fingerSetCue: some View {
        if let fingerConfiguration {
            CueGlyph(label: fingerConfiguration.orderedFingers.map(\.shortLabel).joined(separator: "+")) {
                FingerCueGlyph(fingerConfiguration: fingerConfiguration)
                    .scaleEffect(x: mirrorScale, y: 1)
            }
        }
    }

    private var mirrorScale: CGFloat {
        side == .right ? -1 : 1
    }

    private func gripPoseAsset(for posture: GripType) -> String {
        switch posture {
        case .halfCrimp:
            return "PhosphorHandGrabbing"
        case .fullCrimp:
            return "PhosphorHandFist"
        case .openHand, .fourFingerPocket, .threeFingerPocket, .twoFingerPocket, .sloper:
            return "PhosphorHandPalm"
        }
    }

    private func gripPoseLabel(for posture: GripType) -> String {
        switch posture {
        case .halfCrimp: "Half crimp"
        case .fullCrimp: "Full crimp"
        case .openHand: "Open hand"
        case .fourFingerPocket: "Four-finger pocket"
        case .threeFingerPocket: "Three-finger pocket"
        case .twoFingerPocket: "Two-finger pocket"
        case .sloper: "Open-hand sloper"
        }
    }

    private var accessibilityLabel: String {
        [
            posture.map(gripPoseLabel),
            fingerConfiguration.map { "Exact fingers: \($0.orderedFingers.namedList)" }
        ]
        .compactMap { $0 }
        .joined(separator: ", ")
    }
}

private struct FingerCueGlyph: View {
    let fingerConfiguration: FingerConfiguration

    var body: some View {
        HStack(alignment: .bottom, spacing: 3) {
            ForEach(FingerSlot.allCases) { finger in
                RoundedRectangle(cornerRadius: 4, style: .continuous)
                    .fill(
                        fingerConfiguration.engagedFingers.contains(finger)
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
