import SwiftUI

enum WorkoutSummaryMode: Equatable {
    case pending
    case history

    var isReadOnly: Bool {
        self == .history
    }
}

enum WorkoutSummaryFormatting {
    static func initialWeightText(
        for initialWeight: WorkoutInitialWeightConfiguration,
        unit: WorkoutLoadAdjustmentDisplayUnit
    ) -> String? {
        switch initialWeight.source {
        case .untracked:
            return nil
        case .sensor:
            return "Supported scale"
        case .manual:
            let weightKGF = initialWeight.manualWeightKGF ?? 0
            let displayedValue = unit.value(fromKilogramsForce: weightKGF)
            let value = String(format: "%.1f %@", displayedValue, unit.label)
            return initialWeight.manualWeightIncludesBodyweight
                ? "Manual weight: +\(value) plus bodyweight"
                : "Manual weight: \(value) standalone"
        }
    }

    static func stepRowTitle(for session: WorkoutSessionRecord, at index: Int) -> String {
        session.stepTitle(at: index)
    }

    static func granularSampleCountText(
        for measurements: [MotherboardMeasurement],
        profile: ForceSensorProfile = .motherboard,
        wasTruncated: Bool = false
    ) -> String? {
        guard !measurements.isEmpty else { return nil }
        let label = measurements.count == 1 ? "sample" : "samples"
        let cappedMessage = wasTruncated ? " (capture capped; some samples may be missing)" : ""
        return "\(measurements.count) granular \(profile.label) \(label)\(cappedMessage)"
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

    static func loadAdjustmentText(
        for loadAdjustmentKGF: Double,
        unit: WorkoutLoadAdjustmentDisplayUnit
    ) -> String? {
        guard loadAdjustmentKGF.isFinite, loadAdjustmentKGF != 0 else { return nil }
        let displayedValue = unit.value(fromKilogramsForce: abs(loadAdjustmentKGF))
        guard displayedValue.isFinite else { return nil }

        if loadAdjustmentKGF > 0 {
            return "Added weight: +\(String(format: "%.1f %@", displayedValue, unit.label))"
        }
        return "Pulley assistance: -\(String(format: "%.1f %@", displayedValue, unit.label))"
    }

    static func semanticText(
        for step: WorkoutStepMeasurement,
        unit: MotherboardForceUnit
    ) -> String {
        guard !step.isRest else { return "Rest" }
        let side: String
        switch step.side {
        case .left: side = "Left hand"
        case .right: side = "Right hand"
        case .both: side = "Both hands"
        }
        switch step.action {
        case .hang:
            return "Hang • \(side)"
        case .isometricPull:
            return "Isometric pull • \(side)"
        case .loadedLift:
            let completed = step.completedRepetitions ?? 0
            let prescribed = step.repetitions ?? 0
            let load = step.externalLoadKGF.map {
                " • \(WorkoutStepFormatting.externalLoadText($0, unit: unit))"
            } ?? ""
            return "Loaded lift • \(side) • \(completed) of \(prescribed) lifts complete\(load)"
        }
    }
}

struct WorkoutSummaryView: View {
    let session: WorkoutSessionRecord
    let unit: MotherboardForceUnit
    let loadAdjustmentUnit: WorkoutLoadAdjustmentDisplayUnit
    let onSave: () -> Void
    let onDiscard: () -> Void
    let mode: WorkoutSummaryMode
    @State private var showsDiscardConfirmation = false

    init(
        session: WorkoutSessionRecord,
        unit: MotherboardForceUnit,
        loadAdjustmentUnit: WorkoutLoadAdjustmentDisplayUnit,
        onSave: @escaping () -> Void,
        onDiscard: @escaping () -> Void
    ) {
        self.session = session
        self.unit = unit
        self.loadAdjustmentUnit = loadAdjustmentUnit
        self.onSave = onSave
        self.onDiscard = onDiscard
        mode = .pending
    }

    var body: some View {
        NavigationStack {
            WorkoutSummaryContent(
                session: session,
                unit: unit,
                loadAdjustmentUnit: loadAdjustmentUnit
            )
            .navigationTitle("Summary")
            .navigationBarTitleDisplayMode(.inline)
            .safeAreaInset(edge: .bottom) {
                Text("Saving adds this session to history and Apple Health, if connected.")
                    .font(.system(.caption, design: .rounded))
                    .foregroundStyle(Color.hangMuted)
                    .frame(maxWidth: .infinity)
                    .padding(.horizontal, 16)
                    .padding(.vertical, 8)
                    .background(Color.hangBackground)
            }
            .toolbar {
                if !mode.isReadOnly {
                    ToolbarItem(placement: .cancellationAction) {
                        Button("Discard", role: .destructive) {
                            showsDiscardConfirmation = true
                        }
                        .accessibilityIdentifier("workout.summary.discard")
                    }
                    ToolbarItem(placement: .confirmationAction) {
                        Button("Save session", action: onSave)
                            .buttonStyle(.borderedProminent)
                            .tint(.hangGreenDark)
                            .accessibilityIdentifier("workout.summary.save")
                    }
                }
            }
            .alert("Discard this session?", isPresented: $showsDiscardConfirmation) {
                Button("Discard session", role: .destructive, action: onDiscard)
                    .accessibilityIdentifier("workout.summary.discardConfirm")
                Button("Keep reviewing", role: .cancel) {}
            } message: {
                Text("This session will not be saved to history or Apple Health.")
            }
        }
        .interactiveDismissDisabled(!mode.isReadOnly)
    }
}

struct HistoryView: View {
    @EnvironmentObject private var store: AppStore
    @EnvironmentObject private var settings: MotherboardSettingsStore
    @Environment(\.scenePhase) private var scenePhase

    var body: some View {
        NavigationStack {
            WorkoutSessionHistoryView(
                sessions: store.sessionHistory,
                unit: settings.forceUnit,
                loadAdjustmentUnit: settings.loadAdjustmentUnit,
                persistenceError: store.sessionPersistenceError
            )
        }
        .onAppear {
            store.refreshHealthAuthorization()
        }
        .onChange(of: scenePhase) { _, phase in
            if phase == .active {
                store.refreshHealthAuthorization()
            }
        }
    }
}

struct WorkoutSessionHistoryView: View {
    let sessions: [WorkoutSessionRecord]
    let unit: MotherboardForceUnit
    let loadAdjustmentUnit: WorkoutLoadAdjustmentDisplayUnit
    var persistenceError: String? = nil

    var body: some View {
        List {
            if let persistenceError {
                Label(persistenceError, systemImage: "exclamationmark.triangle.fill")
                    .font(.system(.footnote, design: .rounded, weight: .semibold))
                    .foregroundStyle(Color.holdActiveDeep)
            }

            if sessions.isEmpty {
                ContentUnavailableView(
                    "No saved sessions",
                    systemImage: "clock.arrow.circlepath",
                    description: Text("Save a completed workout to review it here.")
                )
                .listRowBackground(Color.hangCream)
            } else {
                ForEach(sessions) { session in
                    NavigationLink {
                        WorkoutSummaryContent(
                            session: session,
                            unit: unit,
                            loadAdjustmentUnit: loadAdjustmentUnit
                        )
                        .navigationTitle("Session summary")
                        .navigationBarTitleDisplayMode(.inline)
                    } label: {
                        VStack(alignment: .leading, spacing: 5) {
                            Text(session.planTitle)
                                .font(.system(.subheadline, design: .rounded, weight: .bold))
                                .foregroundStyle(Color.hangInk)
                            Text(session.recordedAt.formatted(date: .abbreviated, time: .shortened))
                                .font(.system(.caption, design: .rounded, weight: .medium))
                                .foregroundStyle(Color.hangMuted)
                            if session.initialWeight.source != .untracked {
                                Text(session.initialWeight.source.label)
                                    .font(.system(.caption, design: .rounded, weight: .medium))
                                    .foregroundStyle(Color.hangMuted)
                            }
                        }
                        .padding(.vertical, 3)
                    }
                    .listRowBackground(Color.hangCream)
                }
            }
        }
        .scrollContentBackground(.hidden)
        .background(Color.hangBackground)
        .navigationTitle("History")
        .navigationBarTitleDisplayMode(.inline)
    }
}

private struct WorkoutSummaryContent: View {
    let session: WorkoutSessionRecord
    let unit: MotherboardForceUnit
    let loadAdjustmentUnit: WorkoutLoadAdjustmentDisplayUnit

    init(
        session: WorkoutSessionRecord,
        unit: MotherboardForceUnit,
        loadAdjustmentUnit: WorkoutLoadAdjustmentDisplayUnit
    ) {
        self.session = session
        self.unit = unit
        self.loadAdjustmentUnit = loadAdjustmentUnit
    }

    var body: some View {
        List {
            Section {
                VStack(alignment: .leading, spacing: 6) {
                    Text(session.planTitle)
                        .font(.system(.title2, design: .rounded, weight: .bold))
                        .foregroundStyle(Color.hangInk)
                    Text(session.recordedAt.formatted(date: .long, time: .shortened))
                        .font(.system(.footnote, design: .rounded, weight: .medium))
                        .foregroundStyle(Color.hangMuted)
                }
                .padding(.vertical, 4)
            }

            Section(session.initialWeight.source == .sensor ? "Measured load" : "Workout steps") {
                ForEach(Array(session.steps.enumerated()), id: \.element.stepID) { index, step in
                    stepRow(
                        step,
                        title: WorkoutSummaryFormatting.stepRowTitle(for: session, at: index),
                        showsMeasuredLoad: session.initialWeight.source == .sensor
                    )
                }
            }

            if session.initialWeight.source == .sensor {
                Section("Scale") {
                    Text(session.forceSensorProfile.label)
                        .font(.system(.subheadline, design: .rounded, weight: .semibold))
                        .foregroundStyle(Color.hangInk)
                }
            }

            if let initialWeightText = WorkoutSummaryFormatting.initialWeightText(
                for: session.initialWeight,
                unit: loadAdjustmentUnit
            ) {
                Section("Initial weight") {
                    Text(initialWeightText)
                        .font(.system(.subheadline, design: .rounded, weight: .semibold))
                        .foregroundStyle(Color.hangInk)
                }
            }

            if let loadAdjustmentText = WorkoutSummaryFormatting.loadAdjustmentText(
                for: session.loadAdjustmentKGF,
                unit: loadAdjustmentUnit
            ) {
                Section("Load adjustment") {
                    Text(loadAdjustmentText)
                        .font(.system(.subheadline, design: .rounded, weight: .semibold))
                        .foregroundStyle(Color.hangInk)
                }
            }

            if session.initialWeight.source == .sensor,
               let bodyweightBaselineText = WorkoutSummaryFormatting.bodyweightBaselineText(
                for: session.bodyweightKGF,
                unit: unit
            ) {
                Section("Bodyweight baseline") {
                    Text(bodyweightBaselineText)
                        .font(.system(.subheadline, design: .rounded, weight: .semibold))
                        .foregroundStyle(Color.hangInk)
                }
            }

            if session.initialWeight.source == .sensor,
               let granularSampleCountText = WorkoutSummaryFormatting.granularSampleCountText(
                for: session.motherboardMeasurements,
                profile: session.forceSensorProfile,
                wasTruncated: session.motherboardMeasurementsTruncated
            ) {
                Section("Granular scale data") {
                    Text(granularSampleCountText)
                        .font(.system(.subheadline, design: .rounded, weight: .semibold))
                        .foregroundStyle(Color.hangInk)
                }
            }

        }
        .scrollContentBackground(.hidden)
        .background(Color.hangBackground)
    }

    @ViewBuilder
    private func stepRow(
        _ step: WorkoutStepMeasurement,
        title: String,
        showsMeasuredLoad: Bool
    ) -> some View {
        VStack(alignment: .leading, spacing: 7) {
            HStack(alignment: .firstTextBaseline) {
                Text(title)
                    .font(.system(.subheadline, design: .rounded, weight: .bold))
                    .foregroundStyle(Color.hangInk)
                Spacer()
                if showsMeasuredLoad {
                    Text(statusText(for: step.status))
                        .font(.system(.caption2, design: .rounded, weight: .bold))
                        .foregroundStyle(statusTint(for: step.status))
                }
            }

            HStack {
                summaryValue(title: "Planned", value: step.plannedActiveDuration.durationText)
                if showsMeasuredLoad {
                    Spacer()
                    summaryValue(title: "Loaded", value: step.actualLoadedDuration.durationText)
                    Spacer()
                    summaryValue(title: "Peak", value: peakText(for: step))
                }
            }

            let semanticText = WorkoutSummaryFormatting.semanticText(for: step, unit: unit)
            if semanticText.caseInsensitiveCompare(title) != .orderedSame {
                Text(semanticText)
                    .font(.system(.caption, design: .rounded, weight: .bold))
                    .foregroundStyle(Color.hangMuted)
            }

            if step.intervals.count > 1 {
                Text("\(step.intervals.count) intervals: \(step.intervals.map { $0.duration.durationText }.joined(separator: ", "))")
                    .font(.system(.caption, design: .rounded, weight: .medium))
                    .foregroundStyle(Color.hangMuted)
            }
        }
        .padding(.vertical, 4)
    }

    private func summaryValue(title: String, value: String) -> some View {
        VStack(alignment: .leading, spacing: 2) {
            Text(title.uppercased())
                .font(.system(.caption2, design: .rounded, weight: .bold))
                .foregroundStyle(Color.hangMuted)
            Text(value)
                .font(.system(.footnote, design: .rounded, weight: .semibold))
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
        "\(formatted(.number.precision(.fractionLength(0...1))))s"
    }
}
