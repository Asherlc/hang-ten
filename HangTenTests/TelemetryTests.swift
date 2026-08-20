import XCTest
import PostHog
@testable import HangTen

final class TelemetryTests: XCTestCase {
    func testRootTabsUseTimelessOrderAndReviewRouting() {
        XCTAssertEqual(RootTab.allCases, [.train, .plans, .history])
        XCTAssertEqual(RootTab.initial(environment: [:]), .train)
        XCTAssertEqual(
            RootTab.initial(environment: ["HANGTEN_REVIEW_PLANS": "1"]),
            .plans
        )
        XCTAssertEqual(
            RootTab.initial(environment: ["HANGTEN_REVIEW_HISTORY": "1"]),
            .history
        )
    }

    func testConfigurationWithoutAProjectTokenBuildsNoOpDependencies() {
        let configuration = PostHogConfiguration(
            projectToken: "$(POSTHOG_CLIENT_TOKEN)",
            host: ""
        )

        XCTAssertFalse(configuration.isConfigured)
        XCTAssertTrue(TelemetryComposition.make(configuration: configuration).isNoOp)
    }

    func testConfiguredTraceEndpointUsesOTLPPathComponents() throws {
        let configuration = PostHogConfiguration(
            projectToken: "phc_test_token",
            host: "https://us.i.posthog.com"
        )

        let endpoint = try XCTUnwrap(configuration.traceEndpoint)

        XCTAssertEqual(endpoint.absoluteString, "https://us.i.posthog.com/i/v1/traces")
        XCTAssertFalse(endpoint.absoluteString.contains("phc_test_token"))
    }

    func testConfigurationRejectsInsecureHTTPHost() {
        let configuration = PostHogConfiguration(
            projectToken: "phc_test_token",
            host: "http://us.i.posthog.com"
        )

        XCTAssertNil(configuration.traceEndpoint)
        XCTAssertFalse(configuration.isConfigured)
    }

    func testSDKConfigurationDisablesAutomaticExceptionCapture() {
        let configuration = PostHogConfiguration(
            projectToken: "phc_test_token",
            host: "https://us.i.posthog.com"
        )

        let sdkConfiguration = PostHogSDKConfiguration.make(configuration: configuration)

        XCTAssertFalse(sdkConfiguration.errorTrackingConfig.autoCapture)
    }

    func testPostHogAdapterTranslatesOnlyTypedProperties() {
        let client = RecordingPostHogClient()
        let telemetry = PostHogTelemetry(client: client)

        telemetry.track(.boardSelected(family: .compactII))

        XCTAssertEqual(client.captures, [
            .init(event: "board selected", properties: ["board_family": "compact_ii"])
        ])
    }

    func testWorkoutFinishedUsesOnlyOutcomeAndCoarseDurationBucket() {
        let event = HangTenTelemetryEvent.workoutFinished(
            outcome: .completed,
            elapsed: 731
        )

        XCTAssertEqual(event.name, "workout finished")
        XCTAssertEqual(event.properties, [
            "outcome": "completed",
            "duration_bucket": "10_to_15_minutes"
        ])
        XCTAssertFalse(event.properties.values.contains("731"))
    }

    func testNoOpTelemetryHasNoRecordedSideEffects() {
        let telemetry = NoOpTelemetry()
        telemetry.track(.customRoutineSaved)
        telemetry.record(.init(category: .persistence, operation: .save, error: TestError()))
        XCTAssertFalse(telemetry.isEnabled("future-flag", default: false))
    }

    func testApprovedEventsExposeOnlyTheirContractProperties() {
        let diagnostic = HangTenDiagnostic(
            category: .persistence,
            operation: .save,
            error: TestError()
        )

        XCTAssertEqual(HangTenTelemetryEvent.appTabSelected(tab: .train).name, "app tab selected")
        XCTAssertEqual(
            [
                HangTenTelemetryEvent.AppTab.train.rawValue,
                HangTenTelemetryEvent.AppTab.plans.rawValue,
                HangTenTelemetryEvent.AppTab.history.rawValue
            ],
            ["train", "plans", "history"]
        )
        XCTAssertEqual(
            HangTenTelemetryEvent.appTabSelected(tab: .train).properties,
            ["tab": "train"]
        )
        XCTAssertEqual(HangTenTelemetryEvent.planBrowsed(source: .catalog).properties, ["source": "catalog"])
        XCTAssertEqual(HangTenTelemetryEvent.workoutStarted(source: .favorite).properties, ["source": "favorite"])
        XCTAssertEqual(HangTenTelemetryEvent.boardSelected(family: .compactII).properties, ["board_family": "compact_ii"])
        XCTAssertEqual(HangTenTelemetryEvent.healthAuthorizationFinished(outcome: .granted).properties, ["outcome": "granted"])
        XCTAssertEqual(HangTenTelemetryEvent.motherboardConnectionFinished(outcome: .connected).properties, ["outcome": "connected"])
        XCTAssertEqual(HangTenTelemetryEvent.appDiagnosticRecorded(diagnostic).properties, [
            "category": "persistence",
            "operation": "save",
            "error_kind": "other"
        ])
    }
}

private struct TestError: Error {}

private final class RecordingPostHogClient: PostHogCapturing {
    struct Capture: Equatable {
        let event: String
        let properties: [String: String]
    }

    private(set) var captures: [Capture] = []

    func capture(event: String, properties: [String: String]) {
        captures.append(.init(event: event, properties: properties))
    }

    func isFeatureEnabled(_ key: String, default defaultValue: Bool) -> Bool {
        defaultValue
    }

    func startSessionReplay() {}

    func stopSessionReplay() {}
}
