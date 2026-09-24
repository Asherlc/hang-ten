import AmplitudeSwift
import XCTest
@testable import HangTen

final class TelemetryTests: XCTestCase {
    func testTrainReviewRoutingComposesPlanWithMotherboardFixture() {
        XCTAssertNil(TrainReviewDestination.initial(environment: [:]))
        XCTAssertEqual(
            TrainReviewDestination.initial(
                environment: ["HANGTEN_REVIEW_MOTHERBOARD": "1"]
            ),
            .settings
        )
        XCTAssertEqual(
            TrainReviewDestination.initial(
                environment: [
                    "HANGTEN_REVIEW_MOTHERBOARD": "1",
                    "HANGTEN_REVIEW_PLAN": "1",
                ]
            ),
            .plan
        )
    }

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

    func testConfigurationWithAnUnexpandedAPIKeyBuildsNoOpDependencies() {
        let configuration = AnalyticsConfiguration(
            apiKey: "$(ANALYTICS_API_KEY)"
        )

        XCTAssertFalse(configuration.isConfigured)
        XCTAssertTrue(TelemetryComposition.make(configuration: configuration).isNoOp)
    }

    func testConfigurationWithTheDocumentedExampleAPIKeyBuildsNoOpDependencies() {
        let configuration = AnalyticsConfiguration(apiKey: "your_amplitude_api_key")

        XCTAssertFalse(configuration.isConfigured)
        XCTAssertTrue(TelemetryComposition.make(configuration: configuration).isNoOp)
    }

    func testConfiguredAPIKeyBuildsActiveAnalyticsDependencies() {
        let configuration = AnalyticsConfiguration(
            apiKey: "test-api-key"
        )

        XCTAssertTrue(configuration.isConfigured)
        XCTAssertFalse(TelemetryComposition.make(configuration: configuration).isNoOp)
    }

    func testSentryOnlyCompositionInstallsDiagnosticsAndUserReports() {
        let dependencies = TelemetryComposition.make(
            analytics: AnalyticsConfiguration(apiKey: ""),
            sentry: SentryConfiguration(dsn: "https://example@o0.ingest.sentry.io/1")
        )

        XCTAssertFalse(dependencies.isNoOp)
        XCTAssertTrue(dependencies.diagnostics is SentryDiagnostics)
        XCTAssertTrue(dependencies.userReports is SentryUserReports)
        XCTAssertTrue(dependencies.tracking is NoOpTelemetry)
    }

    func testAmplitudeOnlyCompositionLeavesSentryAdaptersNoOp() {
        let dependencies = TelemetryComposition.make(
            analytics: AnalyticsConfiguration(apiKey: "test-api-key"),
            sentry: SentryConfiguration(dsn: "$(SENTRY_DSN)")
        )

        XCTAssertFalse(dependencies.isNoOp)
        XCTAssertTrue(dependencies.tracking is AmplitudeAnalyticsTelemetry)
        XCTAssertTrue(dependencies.diagnostics is NoOpTelemetry)
        XCTAssertTrue(dependencies.userReports is NoOpTelemetry)
    }

    func testNeitherAmplitudeNorSentryBuildsFullyNoOpDependencies() {
        let dependencies = TelemetryComposition.make(
            analytics: AnalyticsConfiguration(apiKey: ""),
            sentry: SentryConfiguration(dsn: "")
        )

        XCTAssertTrue(dependencies.isNoOp)
        XCTAssertTrue(dependencies.tracking is NoOpTelemetry)
        XCTAssertTrue(dependencies.diagnostics is NoOpTelemetry)
        XCTAssertTrue(dependencies.userReports is NoOpTelemetry)
    }

    func testBothAmplitudeAndSentryInstallIndependentAdapters() {
        let dependencies = TelemetryComposition.make(
            analytics: AnalyticsConfiguration(apiKey: "test-api-key"),
            sentry: SentryConfiguration(dsn: "https://example@o0.ingest.sentry.io/1")
        )

        XCTAssertFalse(dependencies.isNoOp)
        XCTAssertTrue(dependencies.tracking is AmplitudeAnalyticsTelemetry)
        XCTAssertTrue(dependencies.diagnostics is SentryDiagnostics)
        XCTAssertTrue(dependencies.userReports is SentryUserReports)
    }

    func testUnexpandedSentryDSNIsNotConfigured() {
        XCTAssertFalse(SentryConfiguration(dsn: "$(SENTRY_DSN)").isConfigured)
        XCTAssertFalse(SentryConfiguration(dsn: "  ").isConfigured)
        XCTAssertTrue(SentryConfiguration(dsn: "https://example@o0.ingest.sentry.io/1").isConfigured)
    }

    func testUserReportMapsOnlyTypedIDTags() {
        let report = HangTenUserReport(
            source: .boardDetail,
            message: "  Highlight is wrong  ",
            contactEmail: "  climber@example.com  ",
            boardID: "board-1",
            holdID: "hold-2",
            planID: nil,
            stepID: " "
        )

        XCTAssertEqual(report.message, "Highlight is wrong")
        XCTAssertEqual(report.contactEmail, "climber@example.com")
        XCTAssertNil(report.stepID)
        XCTAssertEqual(report.tags, [
            "report_source": "board_detail",
            "board_id": "board-1",
            "hold_id": "hold-2"
        ])
    }

    func testEmptyContactEmailBecomesNil() {
        let report = HangTenUserReport(
            source: .workout,
            message: "Step timing feels early",
            contactEmail: "   ",
            boardID: "board-1",
            planID: "plan-9",
            stepID: "step-3"
        )

        XCTAssertNil(report.contactEmail)
        XCTAssertEqual(report.tags["plan_id"], "plan-9")
        XCTAssertEqual(report.tags["step_id"], "step-3")
        XCTAssertEqual(report.tags["report_source"], "workout")
        XCTAssertNil(report.tags["hold_id"])
    }

    @MainActor
    func testAppStoreForwardsUserReportsToAdapter() {
        let reports = RecordingUserReports()
        let telemetry = TelemetryDependencies(
            tracking: NoOpTelemetry(),
            diagnostics: NoOpTelemetry(),
            userReports: reports,
            flags: NoOpTelemetry(),
            replay: NoOpTelemetry(),
            isNoOp: false
        )
        let store = AppStore(telemetry: telemetry)
        let report = HangTenUserReport(
            source: .workout,
            message: "Wrong hold highlighted",
            boardID: store.selectedBoard.id,
            planID: "plan-1",
            stepID: "step-1"
        )

        store.submitUserReport(report)

        XCTAssertEqual(reports.submissions, [report])
    }

    @MainActor
    func testAppStoreIgnoresEmptyUserReportMessages() {
        let reports = RecordingUserReports()
        let telemetry = TelemetryDependencies(
            tracking: NoOpTelemetry(),
            diagnostics: NoOpTelemetry(),
            userReports: reports,
            flags: NoOpTelemetry(),
            replay: NoOpTelemetry(),
            isNoOp: false
        )
        let store = AppStore(telemetry: telemetry)

        store.submitUserReport(
            HangTenUserReport(
                source: .boardDetail,
                message: "   ",
                boardID: "board-1"
            )
        )

        XCTAssertTrue(reports.submissions.isEmpty)
    }

    func testAmplitudeAdapterTranslatesOnlyTypedProperties() {
        let client = RecordingAmplitudeClient()
        let telemetry = AmplitudeAnalyticsTelemetry(client: client)

        telemetry.track(.boardSelected(family: .compactII))

        XCTAssertEqual(client.captures, [
            .init(event: "board selected", properties: ["board_family": "compact_ii"])
        ])
    }

    func testAmplitudeSDKConfigurationDisablesAutocaptureAndRemoteConfiguration() {
        let configuration = AmplitudeSDKConfiguration.make(
            configuration: AnalyticsConfiguration(apiKey: "test-api-key")
        )

        XCTAssertEqual(configuration.autocapture, [])
        XCTAssertFalse(configuration.enableAutoCaptureRemoteConfig)
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
        telemetry.submit(
            HangTenUserReport(source: .boardDetail, message: "noop", boardID: "board-1")
        )
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

private final class RecordingUserReports: UserReportSubmitting {
    private(set) var submissions: [HangTenUserReport] = []

    func submit(_ report: HangTenUserReport) {
        submissions.append(report)
    }
}

private final class RecordingAmplitudeClient: AmplitudeTrackingClient {
    struct Capture: Equatable {
        let event: String
        let properties: [String: String]
    }

    private(set) var captures: [Capture] = []

    func track(eventType: String, eventProperties: [String: String]) {
        captures.append(.init(event: eventType, properties: eventProperties))
    }
}
