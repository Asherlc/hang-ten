import SwiftUI

struct WorkoutSummaryView: View {
    let session: WorkoutSessionRecord
    let unit: MotherboardForceUnit
    let onSave: () -> Void
    let onDiscard: () -> Void

    var body: some View {
        NavigationStack {
            List {
                Section {
                    VStack(alignment: .leading, spacing: 6) {
                        Text(session.planTitle)
                            .font(.system(size: 24, weight: .bold, design: .rounded))
                            .foregroundStyle(Color.hangInk)
                        Text(session.recordedAt.formatted(date: .long, time: .shortened))
                            .font(.system(size: 13, weight: .medium, design: .rounded))
                            .foregroundStyle(Color.hangMuted)
                    }
                    .padding(.vertical, 4)
                }

                Section("Measured load") {
                    ForEach(session.steps, id: \.stepID) { step in
                        stepRow(step)
                    }
                }

                Section {
                    Button("Save session", action: onSave)
                        .frame(maxWidth: .infinity)
                        .font(.system(size: 16, weight: .bold, design: .rounded))
                        .foregroundStyle(Color.hangInk)

                    Button("Discard", role: .destructive, action: onDiscard)
                        .frame(maxWidth: .infinity)
                } footer: {
                    Text("Saving logs this completed routine and writes it to Apple Health. Discarding keeps nothing.")
                }
            }
            .navigationTitle("Session summary")
            .navigationBarTitleDisplayMode(.inline)
        }
    }

    @ViewBuilder
    private func stepRow(_ step: WorkoutStepMeasurement) -> some View {
        VStack(alignment: .leading, spacing: 7) {
            HStack(alignment: .firstTextBaseline) {
                Text(step.stepID)
                    .font(.system(size: 15, weight: .bold, design: .rounded))
                    .foregroundStyle(Color.hangInk)
                Spacer()
                Text(statusText(for: step.status))
                    .font(.system(size: 11, weight: .bold, design: .rounded))
                    .foregroundStyle(statusTint(for: step.status))
            }

            HStack {
                summaryValue(title: "Planned", value: step.plannedActiveDuration.durationText)
                Spacer()
                summaryValue(title: "Loaded", value: step.actualLoadedDuration.durationText)
                Spacer()
                summaryValue(title: "Peak", value: peakText(for: step))
            }

            if step.intervals.count > 1 {
                Text("\(step.intervals.count) intervals: \(step.intervals.map { $0.duration.durationText }.joined(separator: ", "))")
                    .font(.system(size: 12, weight: .medium, design: .rounded))
                    .foregroundStyle(Color.hangMuted)
            }
        }
        .padding(.vertical, 4)
    }

    private func summaryValue(title: String, value: String) -> some View {
        VStack(alignment: .leading, spacing: 2) {
            Text(title.uppercased())
                .font(.system(size: 10, weight: .bold, design: .rounded))
                .foregroundStyle(Color.hangMuted)
            Text(value)
                .font(.system(size: 13, weight: .semibold, design: .rounded))
                .foregroundStyle(Color.hangInk)
        }
    }

    private func peakText(for step: WorkoutStepMeasurement) -> String {
        guard let peakLoadKGF = step.peakLoadKGF else { return "Not measured" }
        return String(format: "%.1f %@", unit.value(fromKilogramsForce: peakLoadKGF), unit.label)
    }

    private func statusText(for status: WorkoutStepMeasurement.Status) -> String {
        switch status {
        case .measured: "Measured"
        case .unmeasured: "Not measured"
        case .interrupted: "Interrupted"
        }
    }

    private func statusTint(for status: WorkoutStepMeasurement.Status) -> Color {
        switch status {
        case .measured: .hangGreenDark
        case .unmeasured: .hangMuted
        case .interrupted: .warmUp
        }
    }
}

private extension TimeInterval {
    var durationText: String {
        String(format: "%.1fs", self)
    }
}
