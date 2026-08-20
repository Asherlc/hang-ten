import SwiftUI
import UIKit

struct AppSettingsView: View {
    @EnvironmentObject private var store: AppStore
    @EnvironmentObject private var motherboardBluetoothService: MotherboardBluetoothService
    @EnvironmentObject private var motherboardSettingsStore: MotherboardSettingsStore
    @Environment(\.openURL) private var openURL
    @Environment(\.scenePhase) private var scenePhase

    var body: some View {
        ScrollView(showsIndicators: false) {
            VStack(alignment: .leading, spacing: 21) {
                VStack(alignment: .leading, spacing: 12) {
                    SectionLabel(title: "Training sensor")
                    MotherboardCard(
                        service: motherboardBluetoothService,
                        settings: motherboardSettingsStore
                    )
                    sensorSettingsLink
                }

                VStack(alignment: .leading, spacing: 12) {
                    SectionLabel(title: "Apple Health")
                    healthCard
                }
            }
            .padding(.horizontal, 20)
            .padding(.top, 18)
            .padding(.bottom, 30)
        }
        .background(Color.hangBackground)
        .navigationTitle("Settings")
        .navigationBarTitleDisplayMode(.inline)
        .onAppear {
            store.refreshHealthAuthorization()
        }
        .onChange(of: scenePhase) { _, phase in
            if phase == .active {
                store.refreshHealthAuthorization()
            }
        }
    }

    private var sensorSettingsLink: some View {
        NavigationLink {
            MotherboardSettingsView(
                service: motherboardBluetoothService,
                settings: motherboardSettingsStore
            )
        } label: {
            HStack(spacing: 12) {
                Image(systemName: "slider.horizontal.3")
                    .font(.system(size: 16, weight: .bold))
                    .foregroundStyle(Color.hangGreenDark)
                    .frame(width: 34, height: 34)
                    .background(
                        Color.hangGreen.opacity(0.22),
                        in: RoundedRectangle(cornerRadius: 10, style: .continuous)
                    )
                Text("Sensor settings")
                    .font(.system(size: 15, weight: .bold, design: .rounded))
                    .foregroundStyle(Color.hangInk)
                Spacer()
                Image(systemName: "chevron.right")
                    .font(.system(size: 12, weight: .bold))
                    .foregroundStyle(Color.hangMuted)
            }
        }
        .buttonStyle(.plain)
        .hangCard()
        .accessibilityIdentifier("settings.sensor")
    }

    private var healthCard: some View {
        VStack(alignment: .leading, spacing: 12) {
            HStack(alignment: .top, spacing: 12) {
                Image(systemName: "heart.text.square.fill")
                    .font(.system(size: 18, weight: .bold))
                    .foregroundStyle(Color.holdActiveDeep)
                    .frame(width: 34, height: 34)
                    .background(
                        Color.holdActive.opacity(0.12),
                        in: RoundedRectangle(cornerRadius: 10, style: .continuous)
                    )

                VStack(alignment: .leading, spacing: 5) {
                    HStack {
                        Text("Apple Health")
                            .font(.system(size: 15, weight: .bold, design: .rounded))
                            .foregroundStyle(Color.hangInk)
                        Spacer()
                        Pill(
                            title: store.healthAuthorizationState.statusLabel,
                            tint: healthStatusTint,
                            fill: healthStatusTint.opacity(0.12)
                        )
                    }

                    Text(store.healthAuthorizationState.detail)
                        .font(.system(size: 13, weight: .medium, design: .rounded))
                        .foregroundStyle(Color.hangMuted)
                        .fixedSize(horizontal: false, vertical: true)
                }
            }

            if let healthAuthorizationError = store.healthAuthorizationError {
                Text(healthAuthorizationError)
                    .font(.system(size: 12, weight: .semibold, design: .rounded))
                    .foregroundStyle(Color.holdActiveDeep)
            }

            Text(historySourceMessage)
                .font(.system(size: 13, weight: .medium, design: .rounded))
                .foregroundStyle(Color.hangMuted)
                .fixedSize(horizontal: false, vertical: true)
                .accessibilityIdentifier("health.historySource")

            if let healthAction {
                Button(
                    action: { handleHealthAuthorization(healthAction) },
                    label: {
                        HStack {
                            Image(systemName: healthAction == .settings ? "gear" : "heart.fill")
                            Text(healthAction == .settings ? "Open app settings" : "Connect Apple Health")
                            Spacer()
                            Image(systemName: "arrow.right")
                        }
                        .font(.system(size: 14, weight: .bold, design: .rounded))
                        .foregroundStyle(Color.hangInk)
                        .padding(.horizontal, 14)
                        .padding(.vertical, 12)
                        .background(
                            Color.hangCream,
                            in: RoundedRectangle(cornerRadius: 13, style: .continuous)
                        )
                    }
                )
                .buttonStyle(.plain)
                .accessibilityIdentifier(
                    healthAction == .connect ? "health.connect" : "health.settings"
                )
            }
        }
        .padding(16)
        .background(
            Color.holdActive.opacity(0.08),
            in: RoundedRectangle(cornerRadius: 18, style: .continuous)
        )
    }

    private var healthStatusTint: Color {
        switch store.healthAuthorizationState {
        case .authorized:
            .hangGreenDark
        case .denied:
            .holdActiveDeep
        case .notDetermined, .unavailable:
            .hangMuted
        }
    }

    private func handleHealthAuthorization(_ healthAction: HealthAction) {
        if healthAction == .settings,
           let settingsURL = URL(string: UIApplication.openSettingsURLString) {
            openURL(settingsURL)
        } else {
            store.requestHealthAuthorization()
        }
    }

    private var historySourceMessage: String {
        switch store.workoutHistory.source {
        case .healthKit:
            "History synced from Apple Health."
        case .localFallback:
            "History stored on this device until Apple Health is connected."
        case .syncing:
            "Syncing Hang Ten history with Apple Health…"
        case .unavailable:
            "Apple Health history is unavailable; completed sessions stay on this device."
        }
    }

    private var healthAction: HealthAction? {
        guard store.healthAuthorizationState != .unavailable else { return nil }
        if store.healthAuthorizationState == .denied {
            return .settings
        }
        if store.shouldShowConnectAppleHealth {
            return .connect
        }
        if store.workoutHistory.source == .localFallback {
            return .settings
        }
        return nil
    }

    private enum HealthAction {
        case connect
        case settings
    }
}
