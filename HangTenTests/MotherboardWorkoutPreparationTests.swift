import XCTest
@testable import HangTen

final class MotherboardWorkoutPreparationTests: XCTestCase {
    func testPreparationAdvancesOnlyWhenTareAndBodyweightComplete() {
        var preparation = MotherboardWorkoutPreparation()

        XCTAssertEqual(preparation.step, .tare)

        preparation.completeTare()

        XCTAssertEqual(preparation.step, .bodyweight)
        XCTAssertNil(preparation.bodyweightKGF)

        preparation.completeBodyweight(with: 63.5)

        XCTAssertEqual(preparation.step, .ready)
        XCTAssertEqual(preparation.bodyweightKGF, 63.5)
        XCTAssertEqual(preparation.result, .completed(bodyweightKGF: 63.5))
    }

    func testSkipExitsWithoutInventingABodyweightBaseline() {
        var preparation = MotherboardWorkoutPreparation()
        preparation.completeTare()
        preparation.completeBodyweight(with: 63.5)

        preparation.skip()

        XCTAssertNil(preparation.bodyweightKGF)
        XCTAssertEqual(preparation.result, .skipped)
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
