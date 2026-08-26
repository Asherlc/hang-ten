import Foundation

/// The exporter validates feature targets but intentionally does not link the
/// activity-recorder and Bluetooth model graph. It needs only this conservative
/// compatibility check; runtime highlighting remains implemented by the app's
/// resolver in `WorkoutActivityRecording.swift`.
enum BoardTargetResolver {
    static func substituteHoldIDs(
        for target: HoldTarget,
        on board: TrainingBoard,
        gripType: GripType? = nil
    ) -> [String] {
        let compatibleHolds = (gripType == .halfCrimp || gripType == .fullCrimp)
            ? board.holds.filter {
                $0.kind == .edge && $0.gripType != .openHand &&
                    $0.features?.contains(.largeOpenHandRail) != true
            }
            : board.holds

        if !target.holdIDs.isEmpty {
            let knownIDs = Set(compatibleHolds.map(\.id))
            return target.holdIDs.filter(knownIDs.contains)
        }
        if let feature = target.feature {
            let features = [feature] + target.fallbackFeatures
            for candidate in features {
                let matching = compatibleHolds.filter { hold in
                    guard hold.features?.contains(candidate) == true else { return false }
                    return target.fingerCapacity == nil || hold.fingerCapacity == target.fingerCapacity
                }
                if !matching.isEmpty { return matching.map(\.id) }
            }
            let matchingKind = compatibleHolds.filter {
                $0.kind == feature.holdKind &&
                    (target.fingerCapacity == nil || $0.fingerCapacity == target.fingerCapacity)
            }
            return matchingKind.map(\.id)
        }
        guard let kind = target.kind else { return [] }
        return compatibleHolds.filter { $0.kind == kind }.map(\.id)
    }
}

// The exporter decodes board artwork so it uses the same strict package path
// as the app, but it does not render workout highlights.
enum BoardHighlightMode: Hashable {
    case active
    case preview
}

@main
enum ExportPlanLibrary {
    static func main() throws {
        guard CommandLine.arguments.count == 2 else {
            throw ExportError.missingOutputPath
        }

        let store = try PlanLibraryStore(
            definition: BuiltInPlanLibraryDefinition.document
        )
        let output = URL(fileURLWithPath: CommandLine.arguments[1])
        try store.write(to: output, prettyPrinted: true, options: .atomic)
        print("Exported \(store.plans.count) plans to \(output.path)")
    }
}

private enum ExportError: LocalizedError {
    case missingOutputPath

    var errorDescription: String? {
        "Usage: ExportPlanLibrary <output-path>"
    }
}
