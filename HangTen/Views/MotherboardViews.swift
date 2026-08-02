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
                unit: settings.forceUnit,
                state: service.state
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
                LabeledContent("Connection", value: service.state.label)

                Button("Tare", action: service.tare)
                    .disabled(service.state != .streaming)
            } header: {
                Text("Sensor")
            } footer: {
                Text("Tare zeroes the current load and is available while the sensor is streaming.")
            }
        }
        .navigationTitle("Sensor settings")
        .navigationBarTitleDisplayMode(.inline)
    }
}

struct MotherboardMeterView: View {
    let measurement: MotherboardMeasurement?
    let peakLoadKGF: Double?
    let actualLoadedTime: TimeInterval
    let plannedActiveDuration: TimeInterval
    let unit: MotherboardForceUnit
    let state: MotherboardConnectionState

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

            Label(state.label, systemImage: state == .streaming ? "dot.radiowaves.left.and.right" : "circle.fill")
                .font(.system(size: 11, weight: .bold, design: .rounded))
                .foregroundStyle(Color.hangMuted)
        }
        .padding(14)
        .background(Color.hangCream, in: RoundedRectangle(cornerRadius: 14, style: .continuous))
    }

    private var currentForceText: String {
        guard let measurement else { return "Not measured" }
        return measurement.aggregateLoadKGF.forceString(in: unit)
    }

    private var peakForceText: String {
        guard let peakLoadKGF else { return "Not measured" }
        return peakLoadKGF.forceString(in: unit)
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
            "Try connecting again, or check that your Motherboard is nearby."
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
