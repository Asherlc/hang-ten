import SwiftUI

struct WorkoutStepPickerView: View {
    @Environment(\.dismiss) private var dismiss

    let plan: TrainingPlan
    let currentStepID: WorkoutStep.ID
    let onSelect: (WorkoutStep) -> Void

    var body: some View {
        NavigationStack {
            ScrollView {
                LazyVStack(spacing: 10) {
                    ForEach(plan.steps) { step in
                        stepRow(step)
                    }
                }
                .padding(20)
            }
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
                    .font(.system(size: 13, weight: .bold, design: .rounded))
                    .foregroundStyle(step.phase.textTint)
                    .frame(width: 28, height: 28)
                    .background(step.phase.tint.opacity(0.17), in: Circle())

                VStack(alignment: .leading, spacing: 5) {
                    HStack(alignment: .firstTextBaseline, spacing: 8) {
                        Text(step.title)
                            .font(.system(size: 16, weight: .bold, design: .rounded))
                            .foregroundStyle(Color.hangInk)
                        Spacer(minLength: 8)
                        Text(step.durationLabel)
                            .font(.system(size: 12, weight: .bold, design: .rounded))
                            .foregroundStyle(Color.hangMuted)
                    }

                    Text(step.instruction)
                        .font(.system(size: 13, weight: .medium, design: .rounded))
                        .foregroundStyle(Color.hangMuted)
                        .fixedSize(horizontal: false, vertical: true)

                    Text(step.accessory)
                        .font(.system(size: 11, weight: .bold, design: .rounded))
                        .foregroundStyle(step.phase.textTint)
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
