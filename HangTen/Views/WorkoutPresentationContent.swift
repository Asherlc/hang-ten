import SwiftUI

struct InstructionAccessoryCardRow: Equatable {
    enum Kind: Equatable {
        case instruction
        case accessory
    }

    let kind: Kind
    let text: String
}

enum InstructionAccessoryCardContent {
    static func rows(instruction: String, accessory: String) -> [InstructionAccessoryCardRow] {
        [
            row(kind: .instruction, text: instruction),
            row(kind: .accessory, text: accessory)
        ].compactMap { $0 }
    }

    private static func row(
        kind: InstructionAccessoryCardRow.Kind,
        text: String
    ) -> InstructionAccessoryCardRow? {
        let trimmed = text.trimmingCharacters(in: .whitespacesAndNewlines)
        guard !trimmed.isEmpty else {
            return nil
        }
        return InstructionAccessoryCardRow(kind: kind, text: trimmed)
    }
}

enum WorkoutPresentationContent {
    static let portraitTimerLineLimit = 1

    static func title(step: WorkoutStep, isComplete: Bool) -> String {
        isComplete ? "Session complete" : step.title
    }

    static func cueCardRows(
        step: WorkoutStep,
        countdown: Int,
        isComplete: Bool
    ) -> [InstructionAccessoryCardRow]? {
        guard !isComplete else { return nil }
        let rows = countdown > 0
            ? InstructionAccessoryCardContent.rows(instruction: step.instruction, accessory: "")
            : InstructionAccessoryCardContent.rows(instruction: step.instruction, accessory: step.accessory)
        return rows.isEmpty ? nil : rows
    }
}

enum PlanSourcePresentationContent {
    static func label(for plan: TrainingPlan) -> String {
        "Source: \(plan.sourceLabel)"
    }
}

enum WorkoutLabelPresentationContent {
    static func displayLabels(for labels: [String]) -> [String] {
        labels.map { $0.replacingOccurrences(of: "-", with: " ").capitalized }
    }
}

enum WorkoutLandscapeControlLayoutPolicy {
    static func usesCompactControls(
        isFirstStart: Bool,
        countdown: Int,
        isComplete: Bool
    ) -> Bool {
        isFirstStart && countdown == 0 && !isComplete
    }
}

struct WorkoutLandscapePreStartPresentation: Equatable {
    let cueCardRows: [InstructionAccessoryCardRow]?
    let stopwatchKey: WorkoutActivitySegmentKey?

    static func content(
        for step: WorkoutStep,
        countdown: Int,
        isResting: Bool,
        isComplete: Bool,
        currentStopwatchKey: WorkoutActivitySegmentKey?
    ) -> Self {
        Self(
            cueCardRows: WorkoutPresentationContent.cueCardRows(
                step: step,
                countdown: countdown,
                isComplete: isComplete
            ),
            stopwatchKey: countdown == 0 && !isResting && !isComplete
                ? currentStopwatchKey
                : nil
        )
    }
}
