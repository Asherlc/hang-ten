import SwiftUI

enum WorkoutStepFormatting {
    enum ExternalLoadUnit {
        case kilograms

        var label: String {
            switch self {
            case .kilograms: "kg"
            }
        }
    }

    static func externalLoadText(_ loadKGF: Double, unit: ExternalLoadUnit) -> String {
        externalLoadText(displayedLoad: loadKGF, unitLabel: unit.label)
    }

    static func externalLoadText(_ loadKGF: Double, unit: MotherboardForceUnit) -> String {
        externalLoadText(
            displayedLoad: unit.value(fromKilogramsForce: loadKGF),
            unitLabel: unit.label
        )
    }

    private static func externalLoadText(displayedLoad: Double, unitLabel: String) -> String {
        let magnitude = abs(displayedLoad)
        let number = magnitude.rounded() == magnitude
            ? String(format: "%.0f", magnitude)
            : String(format: "%.1f", magnitude)
        if displayedLoad < 0 {
            return "\(number) \(unitLabel) assistance"
        }
        return "+\(number) \(unitLabel)"
    }

    static func labels(
        for step: WorkoutStep,
        taskIndex: Int = 0,
        selectedHandSide: WorkoutSide? = nil
    ) -> [String] {
        WorkoutTimeline.labels(
            for: step, taskIndex: taskIndex, selectedHandSide: selectedHandSide
        ) + (step.externalLoadKGF.map {
            [externalLoadText($0, unit: .kilograms)]
        } ?? [])
    }
}

struct WorkoutStepPickerView: View {
    @Environment(\.dismiss) private var dismiss

    /// Session-expanded steps (already preference-materialized / alternate-expanded).
    let steps: [WorkoutStep]
    let currentStepID: WorkoutStep.ID
    let onSelect: (WorkoutStep) -> Void

    var body: some View {
        NavigationStack {
            ScrollView {
                LazyVStack(spacing: 10) {
                    ForEach(steps) { step in
                        stepRow(step)
                    }
                }
                .padding(20)
            }
            .accessibilityIdentifier("workout.routineSteps")
            .background(Color.hangBackground)
            .navigationTitle("Routine")
            .navigationBarTitleDisplayMode(.inline)
            .toolbar {
                ToolbarItem(placement: .topBarTrailing) {
                    Button("Done") {
                        dismiss()
                    }
                }
            }
        }
    }

    private func stepRow(_ step: WorkoutStep) -> some View {
        let isCurrent = step.id == currentStepID

        return Button {
            guard !isCurrent else { return }
            onSelect(step)
            dismiss()
        } label: {
            HStack(alignment: .top, spacing: 12) {
                Text("\(step.number)")
                    .font(.system(.footnote, design: .rounded, weight: .bold))
                    .foregroundStyle(step.phase.textTint)
                    .fixedSize()
                    .frame(minWidth: 28, minHeight: 28)
                    .padding(2)
                    .background(step.phase.tint.opacity(0.17), in: Circle())

                VStack(alignment: .leading, spacing: 5) {
                    HStack(alignment: .firstTextBaseline, spacing: 8) {
                        Text(step.title)
                            .font(.system(.callout, design: .rounded, weight: .bold))
                            .foregroundStyle(Color.hangInk)
                        Spacer(minLength: 8)
                        Text(step.durationLabel)
                            .font(.system(.caption, design: .rounded, weight: .bold))
                            .foregroundStyle(Color.hangMuted)
                    }

                    Text(step.instruction)
                        .font(.system(.footnote, design: .rounded, weight: .medium))
                        .foregroundStyle(Color.hangMuted)
                        .fixedSize(horizontal: false, vertical: true)

                    Text(step.accessory)
                        .font(.system(.caption2, design: .rounded, weight: .bold))
                        .foregroundStyle(step.phase.textTint)

                    if !step.isRestStep {
                        Text(WorkoutStepFormatting.labels(for: step).joined(separator: " • "))
                            .font(.system(.caption2, design: .rounded, weight: .bold))
                            .foregroundStyle(step.phase.textTint)
                    }
                }

                if isCurrent {
                    Image(systemName: "checkmark.circle.fill")
                        .foregroundStyle(Color.hangGreenDark)
                        .accessibilityHidden(true)
                }
            }
            .frame(maxWidth: .infinity, minHeight: 64, alignment: .leading)
            .padding(14)
            .background(
                isCurrent ? step.phase.tint.opacity(0.16) : Color.white.opacity(0.72),
                in: RoundedRectangle(cornerRadius: 16, style: .continuous)
            )
            .overlay {
                RoundedRectangle(cornerRadius: 16, style: .continuous)
                    .stroke(isCurrent ? step.phase.textTint.opacity(0.5) : Color.clear, lineWidth: 1)
            }
            .contentShape(RoundedRectangle(cornerRadius: 16, style: .continuous))
        }
        .buttonStyle(.plain)
        .accessibilityIdentifier("workout.step.\(step.id)")
        .accessibilityLabel("Step \(step.number), \(step.title), \(step.durationLabel)\(isCurrent ? ", current step" : "")")
    }
}
