import XCTest
@testable import HangTen

final class TelemetryTests: XCTestCase {
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
