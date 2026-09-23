import XCTest

final class FreeWorkoutUITests: XCTestCase {
    func testFreeWorkoutBuilderOpensFromTrain() {
        let app = XCUIApplication()
        app.launchEnvironment["HANGTEN_REVIEW_RESET_FREE_WORKOUT"] = "1"
        app.launch()
        let entry = app.buttons["train.freeWorkout"]
        XCTAssertTrue(entry.waitForExistence(timeout: 10))
        entry.tap()
        XCTAssertTrue(app.navigationBars["Free workout"].waitForExistence(timeout: 10))
        XCTAssertTrue(app.buttons["freeWorkout.addHang"].exists)
        XCTAssertTrue(app.buttons["freeWorkout.start"].exists)
    }

    func testFreeWorkoutSessionStartsAndShowsControls() {
        let app = XCUIApplication()
        app.launchEnvironment["HANGTEN_REVIEW_RESET_FREE_WORKOUT"] = "1"
        app.launch()
        app.buttons["train.freeWorkout"].tap()
        XCTAssertTrue(app.navigationBars["Free workout"].waitForExistence(timeout: 10))
        app.buttons["freeWorkout.addHang"].tap()
        let startButton = app.buttons["freeWorkout.start"]
        XCTAssertTrue(startButton.waitForExistence(timeout: 10))
        startButton.tap()
        XCTAssertTrue(app.buttons["freeWorkout.completeSet"].waitForExistence(timeout: 15))
        XCTAssertTrue(app.buttons["freeWorkout.skip"].exists)
        XCTAssertTrue(app.buttons["freeWorkout.finish"].exists)
    }

    func testFreeWorkoutLiveEditAndFinishReturnsToTrain() {
        let app = XCUIApplication()
        app.launchEnvironment["HANGTEN_REVIEW_RESET_FREE_WORKOUT"] = "1"
        app.launch()
        app.buttons["train.freeWorkout"].tap()
        XCTAssertTrue(app.navigationBars["Free workout"].waitForExistence(timeout: 10))
        let start = app.buttons["freeWorkout.start"]
        XCTAssertTrue(start.waitForExistence(timeout: 10))
        start.tap()
        let adjustUp = app.buttons["freeWorkout.adjustUp.Time"]
        XCTAssertTrue(adjustUp.waitForExistence(timeout: 15))
        adjustUp.tap()
        let finish = app.buttons["freeWorkout.finish"]
        XCTAssertTrue(finish.waitForExistence(timeout: 10))
        finish.tap()
        XCTAssertTrue(app.buttons["train.freeWorkout"].waitForExistence(timeout: 15))
    }
}
