import SwiftUI

enum GripCueSide {
    case left
    case right
}

struct GripDiagramView: View {
    let hold: PhysicalContact
    let gripType: GripType?
    let fingerConfiguration: FingerConfiguration?
    let resolvedHandSide: WorkoutSide?

    init(
        hold: PhysicalContact,
        gripType: GripType?,
        fingerConfiguration: FingerConfiguration? = nil,
        resolvedHandSide: WorkoutSide? = nil
    ) {
        self.hold = hold
        self.gripType = gripType
        self.fingerConfiguration = fingerConfiguration
        self.resolvedHandSide = resolvedHandSide
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
                if let singleSide = Self.singleSide(
                    handCapacity: hold.handCapacity,
                    resolvedSide: resolvedHandSide
                ) {
                    GripHandCueCard(
                        posture: gripType,
                        fingerConfiguration: fingerConfiguration,
                        side: singleSide,
                        showsPostureLabel: false,
                        exposesAccessibility: false
                    )
                } else {
                    GripHandPairCueCards(
                        posture: gripType,
                        fingerConfiguration: fingerConfiguration,
                        showsPostureLabel: false,
                        exposesAccessibility: false
                    )
                }
            }
        }
        .padding(.horizontal, 10)
        .padding(.vertical, 10)
        .background(Color.hangCream, in: RoundedRectangle(cornerRadius: 18, style: .continuous))
        .accessibilityElement(children: .ignore)
        .accessibilityLabel(accessibilitySummary)
        .accessibilityIdentifier(accessibilityCueIdentifier)
    }

    private var accessibilityCueIdentifier: String {
        let side = Self.singleSide(
            handCapacity: hold.handCapacity,
            resolvedSide: resolvedHandSide
        )?.accessibilityIdentifier ?? "both"
        return "workout.gripCue.\(side)"
    }

    /// Resolves which hand an illustration should render for a hold that only
    /// physically fits one hand. Returns `nil` for two-handed or unspecified
    /// capacity so the caller renders both hands.
    static func singleSide(handCapacity: Int?, resolvedSide: WorkoutSide?) -> GripCueSide? {
        guard handCapacity == 1 else { return nil }
        switch resolvedSide {
        case .left: return .left
        case .right: return .right
        case .both, .none: return .right
        }
    }

    private var accessibilitySummary: String {
        if let singleSide = Self.singleSide(
            handCapacity: hold.handCapacity,
            resolvedSide: resolvedHandSide
        ) {
            return "\(cueLabel), \(accessibilityCueLabel), \(singleSide.accessibilityIdentifier) hand"
        }
        return "\(cueLabel), \(accessibilityCueLabel), both hands"
    }

    /// Hold label for the grip cue. Bilateral boards keep the historical plural
    /// forms ("Outer jugs", "… edges"); single-hand holds stay singular so the
    /// cue does not read as a two-handed prescription.
    static func cueLabel(for hold: PhysicalContact) -> String {
        guard hold.kind != .sloper else { return hold.name }

        let singular: String
        if hold.kind == .jug {
            singular = "Outer jug"
        } else {
            singular = hold.name
                .replacingOccurrences(of: "Left ", with: "")
                .replacingOccurrences(of: "Right ", with: "")
                .replacingOccurrences(of: ", left", with: "")
                .replacingOccurrences(of: ", right", with: "")
        }

        guard hold.handCapacity != 1 else { return singular }

        if hold.kind == .jug {
            return "Outer jugs"
        }
        if singular.hasSuffix(" edge") || singular.hasSuffix(" pocket") {
            return singular + "s"
        }
        return singular
    }

    private var cueLabel: String {
        Self.cueLabel(for: hold)
    }

    var accessibilityCueLabel: String {
        [
            gripType?.label ?? "Grip not specified",
            fingerConfiguration?.accessibilityCueSummary ?? "4 fingers (assumed)"
        ]
            .compactMap { $0 }
            .joined(separator: ", ")
    }
}

/// Inline grip illustration and its accessible finger description.
struct GripHandCueCard: View {
    let posture: GripType?
    let fingerConfiguration: FingerConfiguration?
    let side: GripCueSide
    var usesSharedPairPreview = false
    var showsPostureLabel = true
    var exposesAccessibility = true

    var body: some View {
        VStack(spacing: 3) {
            if !usesSharedPairPreview {
                GripHandModelView(posture: posture, fingerConfiguration: fingerConfiguration, side: side)
                    .frame(height: 88)
                    .allowsHitTesting(false)
                    .accessibilityHidden(true)
            }

            if showsPostureLabel {
                Text(posture?.label ?? "Grip not specified")
                    .font(.system(.caption, design: .rounded, weight: .bold))
                    .foregroundStyle(Color.hangMuted)
                    .fixedSize(horizontal: false, vertical: true)
            }
            if fingerConfiguration?.hasExactFingers != true {
                Text(fingerSummary)
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
        .background(Color.hangBackground.opacity(usesSharedPairPreview ? 0.48 : 0.88), in: RoundedRectangle(cornerRadius: 15))
        .overlay {
            RoundedRectangle(cornerRadius: 15)
                .stroke(Color.hangLine.opacity(0.85), lineWidth: 1)
        }
        .accessibilityElement(children: .contain)
        .accessibilityLabel(accessibilityLabel)
        .accessibilityIdentifier(exposesAccessibility ? "workout.gripCue.\(side.accessibilityIdentifier)" : "")
        .accessibilityHidden(!exposesAccessibility)
    }

    var fingerSummary: String {
        fingerConfiguration?.cueSummary ?? "4 fingers (assumed)"
    }

    var accessibilityLabel: String {
        [
            side == .left ? "Left hand" : "Right hand",
            posture?.label ?? "Grip not specified",
            fingerConfiguration?.accessibilityCueSummary ?? "4 fingers (assumed)"
        ].joined(separator: ", ")
    }
}

struct GripHandPairCueCards: View {
    let posture: GripType?
    let fingerConfiguration: FingerConfiguration?
    var showsPostureLabel = true
    var exposesAccessibility = true

    var body: some View {
        VStack(spacing: 6) {
            GripHandPairModelView(posture: posture, fingerConfiguration: fingerConfiguration)
                .frame(height: 88)
                .padding(.horizontal, 8)
                .accessibilityHidden(true)

            if showsPostureLabel {
                Text(posture?.label ?? "Grip not specified")
                    .font(.system(.caption, design: .rounded, weight: .bold))
                    .foregroundStyle(Color.hangMuted)
            }
            if fingerConfiguration?.hasExactFingers != true {
                Text(fingerSummary)
                    .font(.system(.caption, design: .rounded, weight: .semibold))
                    .foregroundStyle(Color.hangMuted)
            }
        }
        .accessibilityElement(children: .ignore)
        .accessibilityLabel("Both hands, \(posture?.label ?? "Grip not specified"), \(fingerConfiguration?.accessibilityCueSummary ?? "4 fingers (assumed)")")
        .accessibilityIdentifier(exposesAccessibility ? "workout.gripCue.both" : "")
        .accessibilityHidden(!exposesAccessibility)
    }

    private var fingerSummary: String {
        fingerConfiguration?.cueSummary ?? "4 fingers (assumed)"
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

extension FingerConfiguration {
    var cueSummary: String {
        hasExactFingers
            ? "Exact fingers: \(orderedFingers.namedList)"
            : "\(count) \(count == 1 ? "finger" : "fingers")"
    }

    var accessibilityCueSummary: String {
        hasExactFingers ? cueSummary : "\(cueSummary), Finger identities not specified"
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
