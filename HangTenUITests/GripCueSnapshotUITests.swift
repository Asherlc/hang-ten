import XCTest

final class GripCueSnapshotUITests: XCTestCase {
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

    func testMaxHangsStepOneShowsBothHandCuesAndFourFingerIndicator() throws {
        let leftFingerIndicator = app.staticTexts["P+R+M+I"]
        let rightFingerIndicator = app.staticTexts["I+M+R+P"]

        XCTAssertTrue(leftFingerIndicator.waitForExistence(timeout: 10))
        XCTAssertTrue(rightFingerIndicator.waitForExistence(timeout: 10))

        let attachment = XCTAttachment(screenshot: XCUIScreen.main.screenshot())
        attachment.name = "Max Hangs step 1 landscape grip cues"
        attachment.lifetime = .keepAlways
        add(attachment)
    }
}
