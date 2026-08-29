import XCTest

final class OwlClimbPokerBoardMapInteractionUITests: XCTestCase {
    func testPokerFaceBSloperHasAlignedNormalActiveAndHitTestStates() throws {
        let app = XCUIApplication()
        app.launchEnvironment = ["HANGTEN_REVIEW_BOARD_PICKER": "1"]
        app.launch()

        let search = app.searchFields["Search boards"]
        XCTAssertTrue(search.waitForExistence(timeout: 30))
        search.tap()
        search.typeText("Poker")

        let holdSpecs = app.buttons["boardPicker.holdSpecs.owl-climb.poker"]
        XCTAssertTrue(holdSpecs.waitForExistence(timeout: 10))
        holdSpecs.tap()

        let map = app.buttons["boardDetail.map"]
        XCTAssertTrue(map.waitForExistence(timeout: 10))
        addScreenshot(named: "Poker normal Face A")

        let faceB = app.segmentedControls["boardDetail.presentationSelector"].buttons["Face B — slopers"]
        XCTAssertTrue(faceB.waitForExistence(timeout: 5))
        faceB.tap()

        let sloper = app.buttons["Face B left central sloper"]
        XCTAssertTrue(sloper.waitForExistence(timeout: 5))
        sloper.tap()

        XCTAssertTrue(
            app.otherElements["boardDetail.selectedHold.face-b-sloper-left"].waitForExistence(timeout: 5),
            "The canonical Face B sloper path must be the tappable element and selected highlight."
        )
        addScreenshot(named: "Poker Face B sloper active")
    }

    private func addScreenshot(named name: String) {
        let attachment = XCTAttachment(screenshot: XCUIScreen.main.screenshot())
        attachment.name = name
        attachment.lifetime = .keepAlways
        add(attachment)
    }
}
