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
        app.buttons["freeWorkout.addHang"].tap()
        let startButton = app.buttons["freeWorkout.start"]
        XCTAssertTrue(startButton.waitForExistence(timeout: 5))
        // Scroll to Start button in case it's off-screen in the List
        var attempts = 0
        while !startButton.isHittable && attempts < 5 {
            app.swipeUp()
            attempts += 1
        }
        startButton.tap()
        XCTAssertTrue(app.buttons["freeWorkout.completeSet"].waitForExistence(timeout: 15))
        XCTAssertTrue(app.buttons["freeWorkout.skip"].exists)
        XCTAssertTrue(app.buttons["freeWorkout.finish"].exists)
    }
}
