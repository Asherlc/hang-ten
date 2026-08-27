import AmplitudeSwift
import Foundation

struct AnalyticsConfiguration {
    let apiKey: String

    init(apiKey: String) {
        self.apiKey = apiKey.trimmingCharacters(in: .whitespacesAndNewlines)
    }

    init(bundle: Bundle) {
        self.init(
            apiKey: bundle.object(forInfoDictionaryKey: "ANALYTICS_API_KEY") as? String ?? ""
        )
    }

    var isConfigured: Bool {
        !apiKey.isEmpty
            && !apiKey.hasPrefix("$(")
            && apiKey != "your_amplitude_api_key"
    }
}

struct TelemetryDependencies {
    let tracking: any TelemetryTracking
    let diagnostics: any DiagnosticReporting
    let flags: any FeatureFlagProviding
    let replay: any SessionReplayControlling
    let isNoOp: Bool

    static func noOp() -> TelemetryDependencies {
        let noOp = NoOpTelemetry()
        return TelemetryDependencies(
            tracking: noOp,
            diagnostics: noOp,
            flags: noOp,
            replay: noOp,
            isNoOp: true
        )
    }
}

enum TelemetryComposition {
    static func make(bundle: Bundle) -> TelemetryDependencies {
        make(configuration: AnalyticsConfiguration(bundle: bundle))
    }

    static func make(configuration: AnalyticsConfiguration) -> TelemetryDependencies {
        guard configuration.isConfigured else {
            return .noOp()
        }

        return TelemetryDependencies(
            tracking: AmplitudeAnalyticsTelemetry(
                client: AmplitudeSDKClient(configuration: configuration)
            ),
            diagnostics: SentryDiagnostics(),
            flags: NoOpTelemetry(),
            replay: NoOpTelemetry(),
            isNoOp: false
        )
    }
}

protocol AmplitudeTrackingClient: AnyObject {
    func track(eventType: String, eventProperties: [String: String])
}

final class AmplitudeAnalyticsTelemetry: TelemetryTracking {
    private let client: any AmplitudeTrackingClient

    init(client: any AmplitudeTrackingClient) {
        self.client = client
    }

    func track(_ event: HangTenTelemetryEvent) {
        client.track(eventType: event.name, eventProperties: event.properties)
    }
}

private final class AmplitudeSDKClient: AmplitudeTrackingClient {
    private let sdk: Amplitude

    init(configuration: AnalyticsConfiguration) {
        sdk = Amplitude(
            configuration: AmplitudeSDKConfiguration.make(configuration: configuration)
        )
    }

    func track(eventType: String, eventProperties: [String: String]) {
        sdk.track(eventType: eventType, eventProperties: eventProperties)
    }
}

enum AmplitudeSDKConfiguration {
    static func make(configuration: AnalyticsConfiguration) -> Configuration {
        Configuration(
            apiKey: configuration.apiKey,
            autocapture: [],
            enableAutoCaptureRemoteConfig: false
        )
    }
}
