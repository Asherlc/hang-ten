import XCTest
@testable import HangTen

final class TelemetryTests: XCTestCase {
    func testConfigurationWithoutAProjectTokenBuildsNoOpDependencies() {
        let configuration = PostHogConfiguration(
            projectToken: "$(POSTHOG_CLIENT_TOKEN)",
            host: ""
        )

        XCTAssertFalse(configuration.isConfigured)
        XCTAssertTrue(TelemetryComposition.make(configuration: configuration).isNoOp)
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

        XCTAssertEqual(HangTenTelemetryEvent.appTabSelected(tab: .today).name, "app tab selected")
        XCTAssertEqual(HangTenTelemetryEvent.appTabSelected(tab: .today).properties, ["tab": "today"])
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
