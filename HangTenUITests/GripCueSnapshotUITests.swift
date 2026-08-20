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
        let leftCue = app.otherElements["workout.gripCue.left"]
        let rightCue = app.otherElements["workout.gripCue.right"]
        let leftFingerIndicator = app.otherElements["workout.gripCue.left.fingers"]
        let rightFingerIndicator = app.otherElements["workout.gripCue.right.fingers"]

        XCTAssertTrue(leftCue.waitForExistence(timeout: 10))
        XCTAssertTrue(rightCue.waitForExistence(timeout: 10))
        XCTAssertTrue(leftFingerIndicator.waitForExistence(timeout: 10))
        XCTAssertTrue(rightFingerIndicator.waitForExistence(timeout: 10))
        XCTAssertEqual(leftFingerIndicator.label, "P+R+M+I")
        XCTAssertEqual(rightFingerIndicator.label, "I+M+R+P")

        let attachment = XCTAttachment(screenshot: XCUIScreen.main.screenshot())
        attachment.name = "Max Hangs step 1 landscape grip cues"
        attachment.lifetime = .keepAlways
        add(attachment)
    }
}
