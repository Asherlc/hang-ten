import SwiftUI

enum WorkoutSummaryMode: Equatable {
    case pending
    case history

    var isReadOnly: Bool {
        self == .history
    }
}

enum WorkoutSummaryFormatting {
    static func granularSampleCountText(for measurements: [MotherboardMeasurement]) -> String? {
        guard !measurements.isEmpty else { return nil }
        let label = measurements.count == 1 ? "sample" : "samples"
        return "\(measurements.count) granular Motherboard \(label)"
    }

    static func bodyweightBaselineText(
        for bodyweightKGF: Double?,
        unit: MotherboardForceUnit
    ) -> String? {
        guard let bodyweightKGF,
              bodyweightKGF.isFinite,
              bodyweightKGF > 0 else {
            return nil
        }

        let displayedValue = unit.value(fromKilogramsForce: bodyweightKGF)
        guard displayedValue.isFinite, displayedValue >= 0 else { return nil }
        return "Captured baseline: \(String(format: "%.1f %@", displayedValue, unit.label))"
    }
}

struct WorkoutSummaryView: View {
    let session: WorkoutSessionRecord
    let unit: MotherboardForceUnit
    let onSave: () -> Void
    let onDiscard: () -> Void
    let mode: WorkoutSummaryMode

    init(
        session: WorkoutSessionRecord,
        unit: MotherboardForceUnit,
        onSave: @escaping () -> Void,
        onDiscard: @escaping () -> Void
    ) {
        self.session = session
        self.unit = unit
        self.onSave = onSave
        self.onDiscard = onDiscard
        mode = .pending
    }

    var body: some View {
        NavigationStack {
            WorkoutSummaryContent(
                session: session,
                unit: unit,
                mode: mode,
                onSave: mode.isReadOnly ? nil : onSave,
                onDiscard: mode.isReadOnly ? nil : onDiscard
            )
            .navigationTitle("Session summary")
            .navigationBarTitleDisplayMode(.inline)
        }
    }
}

struct WorkoutSessionHistoryView: View {
    let sessions: [WorkoutSessionRecord]
    let unit: MotherboardForceUnit

    var body: some View {
        List {
            if sessions.isEmpty {
                ContentUnavailableView(
                    "No saved sessions",
                    systemImage: "clock.arrow.circlepath",
                    description: Text("Save a measured workout to review it here.")
                )
            } else {
                ForEach(sessions) { session in
                    NavigationLink {
                        WorkoutSummaryContent(
                            session: session,
                            unit: unit,
                            mode: .history
                        )
                        .navigationTitle("Session summary")
                        .navigationBarTitleDisplayMode(.inline)
                    } label: {
                        VStack(alignment: .leading, spacing: 5) {
                            Text(session.planTitle)
                                .font(.system(size: 15, weight: .bold, design: .rounded))
                                .foregroundStyle(Color.hangInk)
                            Text(session.recordedAt.formatted(date: .abbreviated, time: .shortened))
                                .font(.system(size: 12, weight: .medium, design: .rounded))
                                .foregroundStyle(Color.hangMuted)
                        }
                        .padding(.vertical, 3)
                    }
                }
            }
        }
        .navigationTitle("Session history")
        .navigationBarTitleDisplayMode(.inline)
    }
}

private struct WorkoutSummaryContent: View {
    let session: WorkoutSessionRecord
    let unit: MotherboardForceUnit
    let mode: WorkoutSummaryMode
    var onSave: (() -> Void)?
    var onDiscard: (() -> Void)?

    init(
        session: WorkoutSessionRecord,
        unit: MotherboardForceUnit,
        mode: WorkoutSummaryMode = .history,
        onSave: (() -> Void)? = nil,
        onDiscard: (() -> Void)? = nil
    ) {
        self.session = session
        self.unit = unit
        self.mode = mode
        self.onSave = onSave
        self.onDiscard = onDiscard
    }

    var body: some View {
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

            if let bodyweightBaselineText = WorkoutSummaryFormatting.bodyweightBaselineText(
                for: session.bodyweightKGF,
                unit: unit
            ) {
                Section("Bodyweight baseline") {
                    Text(bodyweightBaselineText)
                        .font(.system(size: 15, weight: .semibold, design: .rounded))
                        .foregroundStyle(Color.hangInk)
                }
            }

            if let granularSampleCountText = WorkoutSummaryFormatting.granularSampleCountText(
                for: session.motherboardMeasurements
            ) {
                Section("Granular sensor data") {
                    Text(granularSampleCountText)
                        .font(.system(size: 15, weight: .semibold, design: .rounded))
                        .foregroundStyle(Color.hangInk)
                }
            }

            if !mode.isReadOnly, let onSave, let onDiscard {
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
