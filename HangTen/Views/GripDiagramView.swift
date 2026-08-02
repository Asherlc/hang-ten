import SwiftUI

enum GripCueSide {
    case left
    case right
}

struct GripDiagramView: View {
    let hold: BoardHold
    let gripType: GripType

    init(hold: BoardHold, gripType: GripType? = nil) {
        self.hold = hold
        self.gripType = gripType ?? hold.gripType
    }

    private var gripLabel: String {
        switch gripType {
        case .openHand: "Open-hand grip"
        case .halfCrimp: "Half crimp"
        case .fullCrimp: "Full crimp"
        case .fourFingerPocket: "Four-finger pocket"
        case .threeFingerPocket: "Three-finger pocket"
        case .twoFingerPocket: "Two-finger pocket"
        case .sloper: "Open-hand sloper"
        }
    }

    private var fingerCountLabel: String {
        switch gripType.activeFingers.count {
        case 2: "Middle two fingers"
        case 3: "Front three fingers"
        default: "Four fingers"
        }
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
                GripHandCueCard(hold: hold, gripType: gripType, side: .left)
                GripHandCueCard(hold: hold, gripType: gripType, side: .right)
            }
        }
        .padding(.horizontal, 10)
        .padding(.vertical, 10)
        .background(Color.hangCream, in: RoundedRectangle(cornerRadius: 18, style: .continuous))
        .accessibilityElement(children: .combine)
        .accessibilityLabel("\(cueLabel), \(gripLabel), \(fingerCountLabel), both hands")
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
    let hold: BoardHold
    let gripType: GripType
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
            Group {
                if gripType == .twoFingerPocket {
                    Image("PhosphorHandTwo")
                        .resizable()
                        .renderingMode(.template)
                        .scaledToFit()
                } else if gripType.activeFingers.contains(.pinky) {
                    Image(systemName: "hand.raised.fill")
                        .resizable()
                        .scaledToFit()
                } else {
                    Image("PhosphorHandFrontThree")
                        .resizable()
                        .renderingMode(.template)
                        .scaledToFit()
                }
            }
            .scaleEffect(x: mirrorScale, y: 1)
            .foregroundStyle(Color.holdActive)
        }
    }

    private var mirrorScale: CGFloat {
        side == .right ? -1 : 1
    }

    private var gripPoseAsset: String {
        if hold.kind == .jug {
            return "PhosphorHandGrabbing"
        }

        switch gripType {
        case .halfCrimp:
            return "PhosphorHandGrabbing"
        case .fullCrimp:
            return "PhosphorHandFist"
        case .openHand, .fourFingerPocket, .threeFingerPocket, .twoFingerPocket, .sloper:
            return "PhosphorHandPalm"
        }
    }

    private var gripPoseLabel: String {
        if hold.kind == .jug {
            return "Jug grip"
        }

        return switch gripType {
        case .halfCrimp: "Half crimp"
        case .fullCrimp: "Full crimp"
        case .openHand, .fourFingerPocket, .threeFingerPocket, .twoFingerPocket, .sloper: "Open hand"
        }
    }

    private var fingerSetLabel: String {
        switch gripType.activeFingers.count {
        case 2: "Middle 2"
        case 3: "Front 3"
        default: "4 fingers"
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
