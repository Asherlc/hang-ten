import XCTest

final class FreeWorkoutUITests: XCTestCase {
    func testFreeWorkoutBuilderOpensFromTrain() {
        let app = XCUIApplication()
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
        app.launch()
        app.buttons["train.freeWorkout"].tap()
        XCTAssertTrue(app.navigationBars["Free workout"].waitForExistence(timeout: 10))
        app.buttons["freeWorkout.start"].tap()
        XCTAssertTrue(app.otherElements["freeWorkout.session"].waitForExistence(timeout: 10))
        XCTAssertTrue(app.buttons["freeWorkout.completeSet"].exists)
        XCTAssertTrue(app.buttons["freeWorkout.skip"].exists)
        XCTAssertTrue(app.buttons["freeWorkout.finish"].exists)
    }
}
