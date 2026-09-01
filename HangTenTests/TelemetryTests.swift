import AmplitudeSwift
import XCTest
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

        XCTAssertNil(RootReviewDestination.initial(environment: [:]))
        XCTAssertEqual(
            RootReviewDestination.initial(environment: ["HANGTEN_REVIEW_WORKOUT": "1"]),
            .workout
        )
    }

    func testBoardPresentationReviewRouteResolvesExactCatalogPairThroughNormalMapContent() throws {
        let destination = RootReviewDestination.initial(
            environment: [
                "HANGTEN_REVIEW_BOARD_PRESENTATION": "1",
                "HANGTEN_REVIEW_BOARD_ID": "owl-climb.poker",
                "HANGTEN_REVIEW_PRESENTATION_ID": "face-b"
            ],
            boards: BoardCatalog.all
        )

        guard case let .boardPresentation(board, presentationID) = destination else {
            return XCTFail("Expected the exact board presentation review destination.")
        }
        XCTAssertEqual(board.id, "owl-climb.poker")
        XCTAssertEqual(presentationID, "face-b")

        let map = BoardDetailHoldMap(board: board, presentationID: presentationID)
        XCTAssertEqual(map.presentation.id, "face-b")
        XCTAssertFalse(map.entries.isEmpty)
        XCTAssertTrue(map.entries.allSatisfy { $0.hold.presentationID == "face-b" })
    }

    func testBoardPresentationReviewRouteFailsForUnknownBoard() {
        XCTAssertEqual(
            RootReviewDestination.initial(
                environment: [
                    "HANGTEN_REVIEW_BOARD_PRESENTATION": "1",
                    "HANGTEN_REVIEW_BOARD_ID": "missing.board",
                    "HANGTEN_REVIEW_PRESENTATION_ID": "primary"
                ],
                boards: BoardCatalog.all
            ),
            .boardPresentationError(.boardNotFound("missing.board"))
        )
    }

    func testBoardPresentationReviewRouteFailsForUnknownPresentation() {
        XCTAssertEqual(
            RootReviewDestination.initial(
                environment: [
                    "HANGTEN_REVIEW_BOARD_PRESENTATION": "1",
                    "HANGTEN_REVIEW_BOARD_ID": "owl-climb.poker",
                    "HANGTEN_REVIEW_PRESENTATION_ID": "missing-presentation"
                ],
                boards: BoardCatalog.all
            ),
            .boardPresentationError(
                .presentationNotFound(
                    boardID: "owl-climb.poker",
                    presentationID: "missing-presentation"
                )
            )
        )
    }

    func testBoardPresentationReviewRouteFailsForMissingIdentifiers() {
        XCTAssertEqual(
            RootReviewDestination.initial(
                environment: ["HANGTEN_REVIEW_BOARD_PRESENTATION": "1"],
                boards: BoardCatalog.all
            ),
            .boardPresentationError(.missingBoardID)
        )
        XCTAssertEqual(
            RootReviewDestination.initial(
                environment: [
                    "HANGTEN_REVIEW_BOARD_PRESENTATION": "1",
                    "HANGTEN_REVIEW_BOARD_ID": "owl-climb.poker"
                ],
                boards: BoardCatalog.all
            ),
            .boardPresentationError(.missingPresentationID)
        )
    }

    func testBoardPresentationReviewRouteIsAbsentWithoutOptIn() {
        XCTAssertNil(
            RootReviewDestination.initial(
                environment: [
                    "HANGTEN_REVIEW_BOARD_ID": "owl-climb.poker",
                    "HANGTEN_REVIEW_PRESENTATION_ID": "face-b"
                ],
                boards: BoardCatalog.all
            )
        )
    }

    func testBoardPresentationReviewRouteRejectsEveryPresentNonOptInValue() {
        for value in ["", "true", "yes", "typo"] {
            XCTAssertEqual(
                RootReviewDestination.initial(
                    environment: ["HANGTEN_REVIEW_BOARD_PRESENTATION": value],
                    boards: BoardCatalog.all
                ),
                .boardPresentationError(.invalidEnableValue(value))
            )
        }
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
