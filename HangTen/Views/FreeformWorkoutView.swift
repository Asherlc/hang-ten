import SwiftUI
import Combine

/// Scale-only Freeform session: enter an edge depth, watch live force, and let
/// the recorder detect efforts. No board, hand, grip or prescription facts are
/// inferred; the summary reuses the ordinary saved-session flow.
struct FreeformWorkoutView: View {
    @EnvironmentObject private var store: AppStore
    @EnvironmentObject private var service: MotherboardBluetoothService
    @EnvironmentObject private var settings: MotherboardSettingsStore
    @Environment(\.scenePhase) private var scenePhase

    @Binding var isPresented: Bool

    @State private var workout = FreeformWorkout()
    @State private var depthText = ""
    @FocusState private var depthIsFocused: Bool
    @State private var accumulatedElapsed: TimeInterval = 0
    @State private var startUptime: TimeInterval = 0
    @State private var summarySession: WorkoutSessionRecord?
    @State private var showsDiscardConfirm = false
    @State private var showsEmptyDiscard = false
    /// Set when the connection is lost while active or paused; used to tell the
    /// model whether Resume follows an actual stream restart.
    @State private var streamRestartedWhilePaused = false
    /// Carries only accepted samples from the model's live measurement to the
    /// meter's stabilized balance display; raw scale packets never pass through.
    @State private var meterMeasurements = PassthroughSubject<MotherboardMeasurement?, Never>()

    private var resolvedDepth: Double? {
        FreeformWorkout.normalizedDepth(from: depthText)
    }

    private var canStart: Bool {
        resolvedDepth != nil && service.state == .streaming && !service.isTaring
    }

    private var canResume: Bool {
        service.state == .streaming && !service.isTaring &&
            workout.canResume(
                deviceID: service.connectedDeviceID?.uuidString,
                profile: service.connectedProfile ?? settings.forceSensorProfile
            )
    }

    var body: some View {
        NavigationStack {
            Group {
                switch workout.state {
                case .idle:
                    setupView
                case .active, .paused:
                    liveView
                case .finished:
                    Color.hangBackground
                }
            }
            .background(Color.hangBackground)
            .navigationTitle("Freeform")
            .navigationBarTitleDisplayMode(.inline)
            .toolbar {
                ToolbarItemGroup(placement: .keyboard) {
                    Spacer()
                    Button("Done") { depthIsFocused = false }
                        .accessibilityIdentifier("freeform.keyboard.done")
                }
                ToolbarItem(placement: .cancellationAction) {
                    Button("Cancel") {
                        if workout.state == .active || workout.state == .paused {
                            showsDiscardConfirm = true
                        } else {
                            close()
                        }
                    }
                    .accessibilityIdentifier("freeform.cancel")
                }
            }
        }
        .interactiveDismissDisabled(
            workout.state == .active || workout.state == .paused
        )
        .confirmationDialog(
            "Discard this Freeform session?",
            isPresented: $showsDiscardConfirm,
            titleVisibility: .visible
        ) {
            Button("Discard session", role: .destructive) {
                workout.discard()
                close()
            }
            .accessibilityIdentifier("freeform.discard.confirm")
            Button("Keep training", role: .cancel) {}
        } message: {
            Text("Recorded efforts will not be saved to history or Apple Health.")
        }
        .alert("No efforts recorded", isPresented: $showsEmptyDiscard) {
            Button("Discard", role: .destructive) {
                workout.discard()
                close()
            }
            .accessibilityIdentifier("freeform.empty.discard")
            Button("Keep training", role: .cancel) {}
                .accessibilityIdentifier("freeform.empty.keepTraining")
        } message: {
            Text("No loaded effort was detected. Discard this session or keep training.")
        }
        .sheet(item: $summarySession) { session in
            WorkoutSummaryView(
                session: session,
                unit: settings.forceUnit,
                loadAdjustmentUnit: settings.loadAdjustmentUnit,
                onSave: {
                    store.saveFreeformSession(session)
                    summarySession = nil
                    close()
                },
                onDiscard: {
                    summarySession = nil
                    close()
                }
            )
            .environmentObject(store)
        }
        .onReceive(service.$latestMeasurement) { measurement in
            guard let measurement,
                  workout.state == .active || (canResume && !streamRestartedWhilePaused) else { return }
            let previousMeasurement = workout.liveMeasurement
            let receivedAt = Date()
            workout.consume(measurement, elapsed: elapsed(), receiptDate: receivedAt)
            // Only a sample the detector accepted changes the live measurement.
            // Rejected or raw packets must not reach the balance display.
            if workout.liveMeasurement != previousMeasurement {
                meterMeasurements.send(workout.liveMeasurement)
            }
        }
        // One timer is the only clock source. Elapsed time is derived from the
        // monotonic system uptime so it cannot jump when the wall clock changes.
        .onReceive(
            Timer.publish(every: 0.25, on: .main, in: .common).autoconnect()
        ) { _ in
            guard workout.state == .active else { return }
            let current = elapsed()
            // One timer also detects a silent stream. Closing at the last
            // accepted sample prevents a late frame from booking the stall.
            if workout.interruptStreamGapIfNeeded(at: current) {
                meterMeasurements.send(nil)
            }
            workout.updateElapsed(current)
        }
        .onChange(of: scenePhase) { _, phase in
            guard phase != .active else { return }
            pauseForInterruption()
        }
        // Observe the publisher directly: a rapid streaming -> disconnected ->
        // streaming transition can coalesce away an `onChange` observation.
        // Track loss while paused too, so only a real stream restart resets the
        // scale's sample identity.
        .onReceive(service.$state) { state in
            guard state != .streaming else { return }
            if workout.state == .active { pauseForInterruption() }
            if workout.state == .active || workout.state == .paused {
                streamRestartedWhilePaused = true
            }
        }
    }

    // MARK: - Setup

    private var setupView: some View {
        ScrollView {
            VStack(alignment: .leading, spacing: 20) {
                VStack(alignment: .leading, spacing: 8) {
                    SectionLabel(title: "Edge depth")
                    TextField("Depth in millimeters", text: $depthText)
                        .keyboardType(.decimalPad)
                        .textFieldStyle(.roundedBorder)
                        .focused($depthIsFocused)
                        .accessibilityLabel("Edge depth in millimeters")
                        .accessibilityIdentifier("freeform.depth")
                    Text("Enter the edge depth in millimeters. It is fixed once the session starts.")
                        .font(.system(.footnote, design: .rounded, weight: .medium))
                        .foregroundStyle(Color.hangMuted)
                }

                MotherboardCard(service: service, settings: settings)

                Button {
                    service.tare()
                } label: {
                    Text(
                        service.isTaring
                            ? "Taring \(service.tareSamplesCollected)/\(service.tareSampleTarget)…"
                            : "Tare"
                    )
                    .frame(maxWidth: .infinity)
                }
                .buttonStyle(.bordered)
                .tint(.hangGreenDark)
                .disabled(service.state != .streaming || service.isTaring)
                .accessibilityIdentifier("freeform.tare")

                Button {
                    start()
                } label: {
                    Label("Start", systemImage: "play.fill")
                        .frame(maxWidth: .infinity)
                }
                .buttonStyle(.borderedProminent)
                .controlSize(.large)
                .tint(.hangGreenDark)
                .disabled(!canStart)
                .accessibilityIdentifier("freeform.start")
            }
            .padding(20)
        }
        .scrollDismissesKeyboard(.immediately)
    }

    // MARK: - Live session

    private var liveView: some View {
        ScrollView {
            VStack(alignment: .leading, spacing: 16) {
                MotherboardMeterView(
                    // Only the last accepted sample feeds the display, so force
                    // and per-sensor balance never show a stale or rejected frame.
                    measurement: workout.liveMeasurement,
                    measurementUpdates: meterMeasurements.eraseToAnyPublisher(),
                    peakLoadKGF: workout.peakLoadKGF,
                    actualLoadedTime: workout.loadedDuration,
                    plannedActiveDuration: 0,
                    bodyweightKGF: nil,
                    unit: settings.forceUnit,
                    state: service.state,
                    thresholdKGF: settings.thresholdKGF,
                    showsConnectionStatus: true,
                    showsTotalLoadedTime: true,
                    showsBodyweightFeedback: false
                )

                HStack(alignment: .firstTextBaseline) {
                    sessionStat(
                        title: "Depth",
                        value: workout.edgeDepthMM.map { FreeformWorkout.depthText($0) } ?? "—",
                        identifier: "freeform.live.depth"
                    )
                    Spacer()
                    sessionStat(
                        title: "Loaded",
                        value: MotherboardUserVisibleFormatting.duration(workout.loadedDuration) ?? "—",
                        identifier: "freeform.live.loaded"
                    )
                    Spacer()
                    sessionStat(
                        title: "Elapsed",
                        value: elapsedText(),
                        identifier: "freeform.elapsed"
                    )
                }

                if workout.state == .paused {
                    if service.state != .streaming {
                        Text("Paused — the sensor disconnected. Reconnect the original scale, then resume explicitly; gaps do not count as loaded time.")
                            .font(.system(.footnote, design: .rounded, weight: .medium))
                            .foregroundStyle(Color.hangMuted)
                            .accessibilityIdentifier("freeform.paused.disconnected")
                        MotherboardCard(service: service, settings: settings)
                    } else if !canResume {
                        Text("A different scale is connected. This session keeps the original scale's data — finish now to save those efforts, then start a new session.")
                            .font(.system(.footnote, design: .rounded, weight: .medium))
                            .foregroundStyle(Color.hangMuted)
                            .accessibilityIdentifier("freeform.paused.differentScale")
                    } else {
                        Text("Paused — no time is counted while paused. Resume when you are ready.")
                            .font(.system(.footnote, design: .rounded, weight: .medium))
                            .foregroundStyle(Color.hangMuted)
                            .accessibilityIdentifier("freeform.paused.user")
                    }
                }

                VStack(alignment: .leading, spacing: 10) {
                    SectionLabel(title: "Efforts")
                    if workout.efforts.isEmpty {
                        Text("Efforts are detected automatically when you load the sensor.")
                            .font(.system(.subheadline, design: .rounded, weight: .medium))
                            .foregroundStyle(Color.hangMuted)
                    } else {
                        ForEach(workout.efforts) { effort in
                            effortRow(effort)
                        }
                    }
                }
            }
            .padding(20)
        }
        .safeAreaInset(edge: .bottom, spacing: 0) {
            sessionControls
                .padding(.horizontal, 20)
                .padding(.vertical, 12)
                .background(Color.hangBackground)
        }
    }

    private var sessionControls: some View {
        HStack(spacing: 12) {
            if workout.state == .active {
                Button {
                    pause()
                } label: {
                    Label("Pause", systemImage: "pause.fill")
                        .frame(maxWidth: .infinity)
                }
                .buttonStyle(.bordered)
                .controlSize(.large)
                .accessibilityIdentifier("freeform.pause")
            } else {
                Button {
                    resume()
                } label: {
                    Label("Resume", systemImage: "play.fill")
                        .frame(maxWidth: .infinity)
                }
                .buttonStyle(.bordered)
                .controlSize(.large)
                .tint(.hangGreenDark)
                .disabled(!canResume)
                .accessibilityIdentifier("freeform.resume")
            }

            Button {
                finish()
            } label: {
                Label("Finish", systemImage: "checkmark.circle.fill")
                    .frame(maxWidth: .infinity)
            }
            .buttonStyle(.borderedProminent)
            .controlSize(.large)
            .tint(.hangGreenDark)
            .accessibilityIdentifier("freeform.finish")
        }
    }

    private func sessionStat(title: String, value: String, identifier: String) -> some View {
        VStack(alignment: .leading, spacing: 2) {
            Text(title.uppercased())
                .font(.system(.caption2, design: .rounded, weight: .bold))
                .foregroundStyle(Color.hangMuted)
            Text(value)
                .font(.system(.subheadline, design: .rounded, weight: .bold))
                .foregroundStyle(Color.hangInk)
                .monospacedDigit()
        }
        .accessibilityElement(children: .combine)
        .accessibilityIdentifier(identifier)
    }

    private func effortRow(_ effort: FreeformEffort) -> some View {
        HStack {
            Text(effort.id.replacingOccurrences(of: "effort-", with: "Effort "))
                .font(.system(.subheadline, design: .rounded, weight: .bold))
                .foregroundStyle(Color.hangInk)
            Spacer()
            Text(MotherboardUserVisibleFormatting.duration(effort.duration) ?? "—")
                .font(.system(.subheadline, design: .rounded, weight: .semibold))
                .foregroundStyle(Color.hangInk)
            Text(MotherboardUserVisibleFormatting.force(effort.peakLoadKGF, unit: settings.forceUnit) ?? "—")
                .font(.system(.subheadline, design: .rounded, weight: .semibold))
                .foregroundStyle(Color.hangGreenDark)
        }
        .padding(.vertical, 6)
        .accessibilityElement(children: .combine)
        .accessibilityIdentifier("freeform.effort.\(effort.id)")
    }

    // MARK: - Lifecycle

    private func start() {
        guard let depth = resolvedDepth, canStart else { return }
        let startedAt = Date()
        let connectedProfile = service.connectedProfile ?? settings.forceSensorProfile
        workout = FreeformWorkout(
            configuration: MotherboardDetectionConfiguration(
                thresholdKGF: settings.thresholdKGF
            ),
            // App recording tolerance for the profile actually connected now,
            // not the connection-recovery timeout.
            streamGapTimeout: FreeformWorkout.recordingGapTimeout(for: connectedProfile)
        )
        workout.start(
            depthMM: depth,
            startDate: startedAt,
            sensorIdentifier: service.connectedDeviceID?.uuidString,
            sensorBatteryValue: service.batteryValue,
            forceSensorProfile: connectedProfile,
            latestSampleNumber: service.latestMeasurement?.sampleNumber
        )
        streamRestartedWhilePaused = false
        accumulatedElapsed = 0
        startUptime = WorkoutClock.monotonicTime
    }

    /// Elapsed active time from the single monotonic clock, freezing on pause.
    private func elapsed() -> TimeInterval {
        guard workout.state == .active else { return accumulatedElapsed }
        return accumulatedElapsed + max(0, WorkoutClock.monotonicTime - startUptime)
    }

    private func elapsedText() -> String {
        let totalSeconds = Int(workout.elapsed.rounded(.down))
        return String(
            format: "%d:%02d",
            totalSeconds / 60,
            totalSeconds % 60
        )
    }

    private func pause() {
        guard workout.state == .active else { return }
        let current = elapsed()
        accumulatedElapsed = current
        workout.pause(at: current)
        meterMeasurements.send(nil)
    }

    private func pauseForInterruption() {
        guard workout.state == .active else { return }
        let current = elapsed()
        accumulatedElapsed = current
        workout.pause(at: current)
        meterMeasurements.send(nil)
    }

    private func resume() {
        guard canResume else { return }
        startUptime = WorkoutClock.monotonicTime
        // `canResume` already requires the original UUID and profile, so a
        // restart flag here refers to that same scale's new stream.
        workout.resume(
            latestSampleNumber: service.latestMeasurement?.sampleNumber,
            streamRestarted: streamRestartedWhilePaused
        )
        streamRestartedWhilePaused = false
    }

    private func finish() {
        guard workout.state == .active || workout.state == .paused else { return }
        guard let session = workout.finish(at: elapsed()) else {
            showsEmptyDiscard = true
            return
        }
        summarySession = session
    }

    private func close() {
        summarySession = nil
        isPresented = false
    }
}
