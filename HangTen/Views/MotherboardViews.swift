import SwiftUI
import UIKit

struct MotherboardCard: View {
    @ObservedObject var service: MotherboardBluetoothService
    @ObservedObject var settings: MotherboardSettingsStore

    @Environment(\.openURL) private var openURL

    var body: some View {
        VStack(alignment: .leading, spacing: 14) {
            HStack(alignment: .top, spacing: 12) {
                Image(systemName: "sensor.tag.radiowaves.forward.fill")
                    .font(.system(size: 17, weight: .bold))
                    .foregroundStyle(stateTint)
                    .frame(width: 34, height: 34)
                    .background(stateTint.opacity(0.13), in: RoundedRectangle(cornerRadius: 10, style: .continuous))

                VStack(alignment: .leading, spacing: 5) {
                    HStack {
                        Text("Training sensor")
                            .font(.system(size: 15, weight: .bold, design: .rounded))
                            .foregroundStyle(Color.hangInk)
                        Spacer()
                        Pill(title: service.state.label, tint: stateTint, fill: stateTint.opacity(0.12))
                    }

                    Text(service.state.detail)
                        .font(.system(size: 13, weight: .medium, design: .rounded))
                        .foregroundStyle(Color.hangMuted)
                        .fixedSize(horizontal: false, vertical: true)
                }
            }

            MotherboardMeterView(
                measurement: service.latestMeasurement,
                peakLoadKGF: nil,
                actualLoadedTime: 0,
                plannedActiveDuration: 0,
                bodyweightKGF: service.bodyweightKGF,
                unit: settings.forceUnit,
                state: service.state,
                thresholdKGF: settings.thresholdKGF
            )

            HStack {
                sensorValue(title: "Battery", value: batteryText)
                Spacer()
                sensorValue(title: "Last error", value: service.lastError ?? "None", alignment: .trailing)
            }

            if service.state.requiresAppSettings {
                Button(action: openAppSettings) {
                    Label("Open app settings", systemImage: "gear")
                        .frame(maxWidth: .infinity)
                }
                .buttonStyle(.bordered)
                .tint(Color.hangGreenDark)
            } else {
                Button(action: handleConnection) {
                    Label(connectionActionTitle, systemImage: connectionActionIcon)
                        .frame(maxWidth: .infinity)
                }
                .buttonStyle(.borderedProminent)
                .tint(Color.hangGreenDark)
            }
        }
        .hangCard()
    }

    private var batteryText: String {
        guard let batteryValue = service.batteryValue else { return "—" }
        return "\(batteryValue)%"
    }

    private var connectionActionTitle: String {
        service.state.shouldDisconnect ? "Disconnect sensor" : "Connect sensor"
    }

    private var connectionActionIcon: String {
        service.state.shouldDisconnect ? "xmark.circle" : "dot.radiowaves.left.and.right"
    }

    private var stateTint: Color {
        switch service.state {
        case .streaming:
            .hangGreenDark
        case .failed, .unauthorized, .bluetoothUnavailable:
            .holdActiveDeep
        case .idle, .scanning, .connecting, .calibrating, .disconnected:
            .hangMuted
        }
    }

    private func sensorValue(title: String, value: String, alignment: HorizontalAlignment = .leading) -> some View {
        VStack(alignment: alignment, spacing: 3) {
            Text(title.uppercased())
                .font(.system(size: 10, weight: .bold, design: .rounded))
                .foregroundStyle(Color.hangMuted)
            Text(value)
                .font(.system(size: 13, weight: .semibold, design: .rounded))
                .foregroundStyle(Color.hangInk)
                .lineLimit(2)
                .multilineTextAlignment(alignment == .trailing ? .trailing : .leading)
        }
    }

    private func handleConnection() {
        if service.state.shouldDisconnect {
            service.disconnect()
        } else {
            service.connect()
        }
    }

    private func openAppSettings() {
        guard let settingsURL = URL(string: UIApplication.openSettingsURLString) else { return }
        openURL(settingsURL)
    }
}

struct MotherboardSettingsView: View {
    @ObservedObject var service: MotherboardBluetoothService
    @ObservedObject var settings: MotherboardSettingsStore

    var body: some View {
        Form {
            Section("Force unit") {
                Picker("Unit", selection: $settings.forceUnit) {
                    ForEach(MotherboardForceUnit.allCases) { unit in
                        Text(unit.label).tag(unit)
                    }
                }
                .pickerStyle(.segmented)
            }

            Section("Detection threshold") {
                Slider(value: $settings.thresholdKGF, in: 0.1...50, step: 0.1)

                Stepper(value: $settings.thresholdKGF, in: 0.1...50, step: 0.1) {
                    Text("\(settings.thresholdKGF.forceString(in: settings.forceUnit))")
                }

                LabeledContent("Canonical threshold") {
                    Text(settings.thresholdKGF.forceString(in: .kgf))
                }

                LabeledContent("Displayed threshold") {
                    Text(settings.forceUnit.value(fromKilogramsForce: settings.thresholdKGF).forceString(unit: settings.forceUnit))
                }
            }

            Section {
                Stepper(value: bodyweightCaptureDuration, in: 3...10, step: 1) {
                    Text("Relaxed jug hang: \(bodyweightCaptureDurationText)")
                }
                .accessibilityLabel("Relaxed jug hang capture duration")
                .accessibilityValue(bodyweightCaptureDurationText)
            } header: {
                Text("Bodyweight baseline")
            } footer: {
                Text("Choose how long to measure your relaxed jug hang before a workout. The board averages this load as your bodyweight baseline.")
            }

            Section {
                LabeledContent("Connection", value: service.state.label)

                Button(action: service.tare) {
                    Text(service.isTaring ? "Taring \(service.tareSamplesCollected)/\(service.tareSampleTarget)…" : "Tare")
                }
                .disabled(service.state != .streaming || service.isTaring)
            } header: {
                Text("Sensor")
            } footer: {
                Text("Tare averages the next \(service.tareSampleTarget) unloaded samples and is available while the sensor is streaming.")
            }
        }
        .navigationTitle("Sensor settings")
        .navigationBarTitleDisplayMode(.inline)
    }

    private var bodyweightCaptureDuration: Binding<TimeInterval> {
        Binding(
            get: { min(max(settings.bodyweightCaptureDuration.rounded(), 3), 10) },
            set: { settings.bodyweightCaptureDuration = min(max($0.rounded(), 3), 10) }
        )
    }

    private var bodyweightCaptureDurationText: String {
        "\(Int(bodyweightCaptureDuration.wrappedValue)) seconds"
    }
}

struct MotherboardMeterView: View {
    let measurement: MotherboardMeasurement?
    let peakLoadKGF: Double?
    let actualLoadedTime: TimeInterval
    let plannedActiveDuration: TimeInterval
    let bodyweightKGF: Double?
    let unit: MotherboardForceUnit
    let state: MotherboardConnectionState
    let thresholdKGF: Double

    var body: some View {
        VStack(alignment: .leading, spacing: 10) {
            HStack(alignment: .lastTextBaseline) {
                VStack(alignment: .leading, spacing: 2) {
                    Text("CURRENT FORCE")
                        .font(.system(size: 10, weight: .bold, design: .rounded))
                        .foregroundStyle(Color.hangMuted)
                    Text(currentForceText)
                        .font(.system(size: 28, weight: .heavy, design: .rounded))
                        .foregroundStyle(Color.hangInk)
                }

                Spacer()

                VStack(alignment: .trailing, spacing: 2) {
                    Text("PEAK")
                        .font(.system(size: 10, weight: .bold, design: .rounded))
                        .foregroundStyle(Color.hangMuted)
                    Text(peakForceText)
                        .font(.system(size: 14, weight: .bold, design: .rounded))
                        .foregroundStyle(Color.hangInk)
                }
            }

            if plannedActiveDuration > 0 {
                ProgressView(value: min(max(actualLoadedTime / plannedActiveDuration, 0), 1))
                    .tint(Color.hangGreenDark)
                Text("\(actualLoadedTime.durationText) loaded of \(plannedActiveDuration.durationText) planned")
                    .font(.system(size: 12, weight: .medium, design: .rounded))
                    .foregroundStyle(Color.hangMuted)
            } else {
                Text(state == .streaming ? "Listening for load." : "Connect the sensor to see live force.")
                    .font(.system(size: 12, weight: .medium, design: .rounded))
                    .foregroundStyle(Color.hangMuted)
            }

            HStack {
                Label(loadStatusText, systemImage: loadStatusIcon)
                    .foregroundStyle(loadStatusTint)
                Spacer()
                if let threshold = formattedForce(thresholdKGF) {
                    Text("Threshold \(threshold)")
                        .foregroundStyle(Color.hangMuted)
                }
            }
            .font(.system(size: 11, weight: .bold, design: .rounded))

            balanceContent

            Text(bodyweightFeedbackText)
                .font(.system(size: 12, weight: .medium, design: .rounded))
                .foregroundStyle(Color.hangMuted)
                .accessibilityLabel(bodyweightFeedbackText)

            Label(state.label, systemImage: state == .streaming ? "dot.radiowaves.left.and.right" : "circle.fill")
                .font(.system(size: 11, weight: .bold, design: .rounded))
                .foregroundStyle(Color.hangMuted)
        }
        .padding(14)
        .background(Color.hangCream, in: RoundedRectangle(cornerRadius: 14, style: .continuous))
    }

    private var currentForceText: String {
        guard let measurement,
              let text = formattedForce(measurement.aggregateLoadKGF) else {
            return "Not measured"
        }
        return text
    }

    private var peakForceText: String {
        guard let peakLoadKGF,
              let text = formattedForce(peakLoadKGF) else {
            return "Not measured"
        }
        return text
    }

    private var loadStatusText: String {
        guard state == .streaming else { return "Sensor unavailable" }
        guard let measurement,
              measurement.aggregateLoadKGF.isFinite else {
            return "Waiting for load"
        }
        return measurement.aggregateLoadKGF >= max(thresholdKGF, 0) ? "Loaded" : "Unloaded"
    }

    private var loadStatusIcon: String {
        switch loadStatusText {
        case "Loaded": "figure.climbing"
        case "Unloaded": "hand.raised"
        default: "questionmark.circle"
        }
    }

    private var loadStatusTint: Color {
        loadStatusText == "Loaded" ? Color.hangGreenDark : Color.hangMuted
    }

    @ViewBuilder
    private var balanceContent: some View {
        if let balance = balancePercentages {
            HStack {
                balanceValue(title: "LEFT", value: balance.left)
                Spacer()
                balanceValue(title: "RIGHT", value: balance.right)
            }
            .accessibilityElement(children: .ignore)
            .accessibilityLabel("Balance: left \(balance.left), right \(balance.right)")
        } else {
            Text("Balance unavailable — waiting for a measured load.")
                .font(.system(size: 12, weight: .medium, design: .rounded))
                .foregroundStyle(Color.hangMuted)
        }
    }

    private var balancePercentages: (left: String, right: String)? {
        guard let measurement,
              let left = formattedPercentage(measurement.leftShare * 100),
              let right = formattedPercentage(measurement.rightShare * 100),
              measurement.leftShare > 0 || measurement.rightShare > 0 else {
            return nil
        }
        return (left, right)
    }

    private var bodyweightFeedbackText: String {
        guard let bodyweightKGF,
              bodyweightKGF.isFinite,
              bodyweightKGF > 0 else {
            return "Bodyweight baseline unavailable."
        }
        guard let measurement,
              measurement.aggregateLoadKGF.isFinite,
              measurement.aggregateLoadKGF >= 0,
              let percentage = formattedPercentage(measurement.bodyweightPercentage(for: bodyweightKGF)) else {
            return "Bodyweight percentage unavailable — waiting for a measurement."
        }
        return "\(percentage) bodyweight"
    }

    private func balanceValue(title: String, value: String) -> some View {
        VStack(alignment: title == "LEFT" ? .leading : .trailing, spacing: 2) {
            Text(title)
                .font(.system(size: 10, weight: .bold, design: .rounded))
                .foregroundStyle(Color.hangMuted)
            Text(value)
                .font(.system(size: 15, weight: .bold, design: .rounded))
                .foregroundStyle(Color.hangInk)
        }
    }

    private func formattedForce(_ kilogramsForce: Double) -> String? {
        guard kilogramsForce.isFinite, kilogramsForce >= 0 else { return nil }
        let displayedValue = unit.value(fromKilogramsForce: kilogramsForce)
        guard displayedValue.isFinite, displayedValue >= 0 else { return nil }
        return String(format: "%.1f %@", displayedValue, unit.label)
    }

    private func formattedPercentage(_ percentage: Double) -> String? {
        guard percentage.isFinite, percentage >= 0 else { return nil }
        guard percentage <= 9_999 else { return "9,999%+" }
        return String(format: "%.0f%%", percentage)
    }
}

private extension MotherboardConnectionState {
    var label: String {
        switch self {
        case .bluetoothUnavailable: "Bluetooth unavailable"
        case .unauthorized: "Bluetooth access needed"
        case .idle: "Not connected"
        case .scanning: "Looking for sensor"
        case .connecting: "Connecting"
        case .calibrating: "Calibrating"
        case .streaming: "Streaming"
        case .disconnected: "Disconnected"
        case .failed: "Connection failed"
        }
    }

    var detail: String {
        switch self {
        case .bluetoothUnavailable:
            "Turn on Bluetooth, then check Hang Ten’s Bluetooth access in Settings."
        case .unauthorized:
            "Allow Bluetooth access for Hang Ten in Settings to connect your Motherboard."
        case .idle, .disconnected:
            "Connect a Motherboard to see live force while you train."
        case .scanning:
            "Looking nearby for your Motherboard."
        case .connecting:
            "Connecting to your Motherboard."
        case .calibrating:
            "Preparing the sensor for live force readings."
        case .streaming:
            "Live force readings are ready."
        case .failed:
            "Try connecting again. If the Motherboard is connected to another app, release it there first, then retry."
        }
    }

    var shouldDisconnect: Bool {
        switch self {
        case .scanning, .connecting, .calibrating, .streaming:
            true
        case .bluetoothUnavailable, .unauthorized, .idle, .disconnected, .failed:
            false
        }
    }

    var requiresAppSettings: Bool {
        self == .unauthorized || self == .bluetoothUnavailable
    }
}

private extension Double {
    func forceString(in unit: MotherboardForceUnit) -> String {
        unit.value(fromKilogramsForce: self).forceString(unit: unit)
    }

    func forceString(unit: MotherboardForceUnit) -> String {
        String(format: "%.1f %@", self, unit.label)
    }
}

private extension TimeInterval {
    var durationText: String {
        String(format: "%.1fs", self)
    }
}
