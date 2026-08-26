import XCTest

final class GripCueDiagnosticScreenshotUITests: XCTestCase {
    private let app = XCUIApplication()

    override func setUpWithError() throws {
        continueAfterFailure = false
        app.launchEnvironment = [
            "HANGTEN_REVIEW_PLAN_ID": "research.max-hangs",
            "HANGTEN_REVIEW_WORKOUT": "1",
            "HANGTEN_REVIEW_STEP": "1",
            "HANGTEN_REVIEW_LANDSCAPE": "1",
        ]
        app.launch()
    }

    func testMaxHangsStepOneExposesIndividualHandCuesAndCapturesDiagnosticScreenshot() throws {
        let leftHandCue = app.otherElements["workout.gripCue.left"]
        let rightHandCue = app.otherElements["workout.gripCue.right"]
        let leftFingerIndicator = app.staticTexts["P+R+M+I"]
        let rightFingerIndicator = app.staticTexts["I+M+R+P"]

        XCTAssertTrue(leftHandCue.waitForExistence(timeout: 10))
        XCTAssertTrue(rightHandCue.waitForExistence(timeout: 10))
        XCTAssertTrue(leftFingerIndicator.waitForExistence(timeout: 10))
        XCTAssertTrue(rightFingerIndicator.waitForExistence(timeout: 10))

        let attachment = XCTAttachment(screenshot: XCUIScreen.main.screenshot())
        attachment.name = "Diagnostic screenshot: Max Hangs step 1 landscape grip cues"
        attachment.lifetime = .keepAlways
        add(attachment)
    }
}

final class IronPalmBoardMapInteractionUITests: XCTestCase {
    func testTappingRightSloperPathSelectsRightSloper() throws {
        let app = XCUIApplication()
        app.launchEnvironment = [
            "HANGTEN_REVIEW_BOARD_PICKER": "1",
        ]
        app.launch()

        let search = app.searchFields["Search boards"]
        XCTAssertTrue(search.waitForExistence(timeout: 10))
        search.tap()
        search.typeText("Iron Palm")

        let holdSpecs = app.buttons["boardPicker.holdSpecs.soill.iron-palm-2"]
        XCTAssertTrue(holdSpecs.waitForExistence(timeout: 10))
        holdSpecs.tap()

        let rightSloper = app.buttons["Right sloper"]
        XCTAssertTrue(
            rightSloper.waitForExistence(timeout: 10),
            "The right sloper's canonical path must be exposed as the tappable board-map element."
        )
        rightSloper.tap()

        XCTAssertTrue(
            app.otherElements["boardDetail.selectedHold.sloper-right"].waitForExistence(timeout: 10)
        )
    }
}
