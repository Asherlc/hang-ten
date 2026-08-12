import Foundation
import PostHog

struct PostHogConfiguration {
    let projectToken: String
    let host: String

    init(projectToken: String, host: String) {
        self.projectToken = projectToken.trimmingCharacters(in: .whitespacesAndNewlines)
        self.host = host.trimmingCharacters(in: .whitespacesAndNewlines)
    }

    init(bundle: Bundle) {
        self.init(
            projectToken: bundle.object(forInfoDictionaryKey: "POSTHOG_CLIENT_TOKEN") as? String ?? "",
            host: bundle.object(forInfoDictionaryKey: "POSTHOG_HOST") as? String ?? ""
        )
    }

    var isConfigured: Bool {
        projectToken.hasPrefix("phc_") && traceEndpoint != nil
    }

    var traceEndpoint: URL? {
        guard
            let hostURL = URL(string: host),
            let scheme = hostURL.scheme?.lowercased(),
            ["https", "http"].contains(scheme),
            hostURL.host != nil
        else {
            return nil
        }

        return hostURL
            .appendingPathComponent("i")
            .appendingPathComponent("v1")
            .appendingPathComponent("traces")
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
        make(configuration: PostHogConfiguration(bundle: bundle))
    }

    static func make(configuration: PostHogConfiguration) -> TelemetryDependencies {
        guard configuration.isConfigured else {
            return .noOp()
        }

        let client = PostHogSDKClient(configuration: configuration)
        let postHog = PostHogTelemetry(client: client)
        let diagnostics: any DiagnosticReporting
        if let openTelemetry = OpenTelemetryDiagnostics(configuration: configuration) {
            diagnostics = openTelemetry
        } else {
            diagnostics = NoOpTelemetry()
        }

        return TelemetryDependencies(
            tracking: postHog,
            diagnostics: diagnostics,
            flags: postHog,
            replay: postHog,
            isNoOp: false
        )
    }
}

protocol PostHogCapturing: AnyObject {
    func capture(event: String, properties: [String: String])
    func isFeatureEnabled(_ key: String, default defaultValue: Bool) -> Bool
    func startSessionReplay()
    func stopSessionReplay()
}

final class PostHogTelemetry: TelemetryTracking, FeatureFlagProviding, SessionReplayControlling {
    private let client: any PostHogCapturing

    init(client: any PostHogCapturing) {
        self.client = client
    }

    func track(_ event: HangTenTelemetryEvent) {
        client.capture(event: event.name, properties: event.properties)
    }

    func isEnabled(_ key: String, default defaultValue: Bool) -> Bool {
        client.isFeatureEnabled(key, default: defaultValue)
    }

    func start() {
        client.startSessionReplay()
    }

    func stop() {
        client.stopSessionReplay()
    }
}

private final class PostHogSDKClient: PostHogCapturing {
    private let sdk: PostHogSDK

    init(configuration: PostHogConfiguration, sdk: PostHogSDK = .shared) {
        self.sdk = sdk

        let config = PostHogConfig(
            projectToken: configuration.projectToken,
            host: configuration.host
        )
        config.personProfiles = .identifiedOnly
        config.sessionReplay = true
        config.sessionReplayConfig.maskAllTextInputs = true
        config.sessionReplayConfig.maskAllImages = true
        config.sessionReplayConfig.screenshotMode = false
        config.sessionReplayConfig.captureLogs = false
        config.sessionReplayConfig.captureNetworkTelemetry = false
        config.errorTrackingConfig.autoCapture = true
        sdk.setup(config)
    }

    func capture(event: String, properties: [String: String]) {
        sdk.capture(event, properties: properties.mapValues { $0 as Any })
    }

    func isFeatureEnabled(_ key: String, default defaultValue: Bool) -> Bool {
        guard sdk.getAllFeatureFlags()?.contains(where: { $0.key == key }) == true else {
            return defaultValue
        }

        return sdk.isFeatureEnabled(key, sendFeatureFlagEvent: false)
    }

    func startSessionReplay() {
        sdk.startSessionRecording()
    }

    func stopSessionReplay() {
        sdk.stopSessionRecording()
    }
}
