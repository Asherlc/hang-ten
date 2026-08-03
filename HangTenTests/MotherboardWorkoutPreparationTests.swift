import XCTest
@testable import HangTen

final class MotherboardWorkoutPreparationTests: XCTestCase {
    func testPreparationAdvancesOnlyWhenTareAndBodyweightComplete() {
        var preparation = MotherboardWorkoutPreparation()

        XCTAssertEqual(preparation.step, .tare)

        preparation.completeTare(isStreaming: true)

        XCTAssertEqual(preparation.step, .bodyweight)
        XCTAssertNil(preparation.bodyweightKGF)

        preparation.completeBodyweight(with: 63.5, isStreaming: true)

        XCTAssertEqual(preparation.step, .ready)
        XCTAssertEqual(preparation.bodyweightKGF, 63.5)
        XCTAssertEqual(preparation.result, .completed(bodyweightKGF: 63.5))
        XCTAssertTrue(preparation.canContinue)
    }

    func testInvalidBodyweightCaptureRemainsOnBodyweightStep() {
        var preparation = MotherboardWorkoutPreparation()
        preparation.completeTare(isStreaming: true)

        for value in [nil, .nan, .infinity, -.infinity, 0, -1] as [Double?] {
            preparation.completeBodyweight(with: value, isStreaming: true)

            XCTAssertEqual(preparation.step, .bodyweight)
            XCTAssertNil(preparation.bodyweightKGF)
            XCTAssertEqual(preparation.result, .inProgress)
            XCTAssertEqual(preparation.failure, .invalidBodyweightCapture)
            XCTAssertFalse(preparation.canContinue)

            preparation.retryBodyweight()
        }
    }

    func testTareCancellationDoesNotAdvanceUntilStreamingCompletion() {
        var preparation = MotherboardWorkoutPreparation()

        preparation.completeTare(isStreaming: false)

        XCTAssertEqual(preparation.step, .tare)
        XCTAssertEqual(preparation.result, .inProgress)
        XCTAssertEqual(preparation.failure, .tareInterrupted)

        preparation.retryTare()
        preparation.completeTare(isStreaming: true)

        XCTAssertEqual(preparation.step, .bodyweight)
        XCTAssertNil(preparation.failure)
    }

    func testBodyweightCancellationDoesNotCompletePreparation() {
        var preparation = MotherboardWorkoutPreparation()
        preparation.completeTare(isStreaming: true)

        preparation.completeBodyweight(with: 63.5, isStreaming: false)

        XCTAssertEqual(preparation.step, .bodyweight)
        XCTAssertNil(preparation.bodyweightKGF)
        XCTAssertEqual(preparation.result, .inProgress)
        XCTAssertEqual(preparation.failure, .bodyweightCaptureInterrupted)
        XCTAssertFalse(preparation.canContinue)

        preparation.retryBodyweight()
        preparation.completeBodyweight(with: 63.5, isStreaming: true)

        XCTAssertEqual(preparation.step, .ready)
        XCTAssertEqual(preparation.bodyweightKGF, 63.5)
        XCTAssertTrue(preparation.canContinue)
    }

    func testSkipIsTerminalAtEveryPreparationStage() {
        var tarePreparation = MotherboardWorkoutPreparation()
        tarePreparation.skip()
        tarePreparation.completeTare(isStreaming: true)
        tarePreparation.retryTare()

        XCTAssertEqual(tarePreparation.step, .tare)
        XCTAssertNil(tarePreparation.bodyweightKGF)
        XCTAssertEqual(tarePreparation.result, .skipped)

        var bodyweightPreparation = MotherboardWorkoutPreparation()
        bodyweightPreparation.completeTare(isStreaming: true)
        bodyweightPreparation.skip()
        bodyweightPreparation.completeBodyweight(with: 63.5, isStreaming: true)
        bodyweightPreparation.retryBodyweight()

        XCTAssertEqual(bodyweightPreparation.step, .bodyweight)
        XCTAssertNil(bodyweightPreparation.bodyweightKGF)
        XCTAssertEqual(bodyweightPreparation.result, .skipped)

        var readyPreparation = MotherboardWorkoutPreparation()
        readyPreparation.completeTare(isStreaming: true)
        readyPreparation.completeBodyweight(with: 63.5, isStreaming: true)
        readyPreparation.skip()
        readyPreparation.completeTare(isStreaming: true)
        readyPreparation.completeBodyweight(with: 75, isStreaming: true)
        readyPreparation.retryBodyweight()

        XCTAssertEqual(readyPreparation.step, .ready)
        XCTAssertNil(readyPreparation.bodyweightKGF)
        XCTAssertEqual(readyPreparation.result, .skipped)
    }

    func testOnlyInitialStreamingStartRequiresPreparation() {
        XCTAssertTrue(MotherboardWorkoutPreparation.requiresPreparation(
            isInitialStart: true,
            isStreaming: true
        ))
        XCTAssertFalse(MotherboardWorkoutPreparation.requiresPreparation(
            isInitialStart: false,
            isStreaming: true
        ))
        XCTAssertFalse(MotherboardWorkoutPreparation.requiresPreparation(
            isInitialStart: true,
            isStreaming: false
        ))
    }
}
