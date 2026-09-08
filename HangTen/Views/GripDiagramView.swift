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
        .accessibilityElement(children: .contain)
        .accessibilityLabel("\(cueLabel), \(accessibilityCueLabel), both hands")
    }

    private var cueLabel: String {
        guard hold.kind != .sloper else { return hold.name }

        if hold.kind == .jug {
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

/// The same 3D rig drives compact workout cues and the rotatable detail view.
struct GripHandCueCard: View {
    let posture: GripType?
    let fingerConfiguration: FingerConfiguration?
    let side: GripCueSide
    @State private var showsModel = false

    var body: some View {
        VStack(spacing: 3) {
            Button {
                showsModel = true
            } label: {
                GripHandModelView(posture: posture, fingerConfiguration: fingerConfiguration, side: side)
                    .frame(height: 88)
                    .overlay(alignment: .topTrailing) {
                        Image(systemName: "arrow.up.left.and.arrow.down.right")
                            .font(.system(size: 9, weight: .semibold))
                            .foregroundStyle(Color.hangMuted)
                    }
                    .contentShape(Rectangle())
            }
            .buttonStyle(.plain)
            .accessibilityLabel("Explore \(side.accessibilityIdentifier) hand in 3D")
            .accessibilityIdentifier("workout.gripCue.\(side.accessibilityIdentifier).model")

            Text(posture?.label ?? "Grip not specified")
                .font(.system(size: 10, weight: .bold, design: .rounded))
                .foregroundStyle(Color.hangMuted)
                .lineLimit(1)
                .minimumScaleFactor(0.68)
            if fingerConfiguration == nil {
                Text("Fingers not specified")
                    .font(.system(size: 10, weight: .semibold, design: .rounded))
                    .foregroundStyle(Color.hangMuted)
                    .lineLimit(1)
                    .minimumScaleFactor(0.68)
                    .accessibilityIdentifier("workout.gripCue.\(side.accessibilityIdentifier).fingers")
            }
        }
        .frame(maxWidth: .infinity)
        .padding(.horizontal, 8)
        .padding(.vertical, 7)
        .background(Color.hangBackground.opacity(0.88), in: RoundedRectangle(cornerRadius: 15))
        .overlay {
            RoundedRectangle(cornerRadius: 15)
                .stroke(Color.hangLine.opacity(0.85), lineWidth: 1)
        }
        .accessibilityElement(children: .contain)
        .accessibilityLabel(accessibilityLabel)
        .accessibilityIdentifier("workout.gripCue.\(side.accessibilityIdentifier)")
        .sheet(isPresented: $showsModel) {
            GripHandModelInspector(posture: posture, fingerConfiguration: fingerConfiguration, side: side)
        }
    }

    private var accessibilityLabel: String {
        [
            posture?.label ?? "Grip not specified",
            fingerConfiguration.map { "Exact fingers: \($0.orderedFingers.namedList)" } ?? "Fingers not specified"
        ].joined(separator: ", ")
    }
}

extension GripCueSide {
    var handArtworkMirrorScale: CGFloat {
        self == .left ? -1 : 1
    }

    var accessibilityIdentifier: String {
        switch self {
        case .left: "left"
        case .right: "right"
        }
    }
}

private extension FingerSlot {
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
