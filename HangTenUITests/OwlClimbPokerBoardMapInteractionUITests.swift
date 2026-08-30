import XCTest

final class OwlClimbPokerBoardMapInteractionUITests: XCTestCase {
    func testTappingFaceBSloperMapElementSelectsSloper() throws {
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

        let faceB = app.segmentedControls["boardDetail.presentationSelector"].buttons["Face B — deep slopers"]
        XCTAssertTrue(faceB.waitForExistence(timeout: 5))
        faceB.tap()

        let sloper = app.buttons
            .matching(identifier: "boardDetail.map")
            .matching(NSPredicate(format: "label == %@", "Face B left deep sloper"))
            .element
        XCTAssertTrue(sloper.waitForExistence(timeout: 5))
        XCTAssertTrue(sloper.isHittable)
        addScreenshot(named: "Poker Face B normal")

        let selected = app.otherElements[
            "boardDetail.selectedHold.face-b-left-deep-sloper"
        ]
        XCTAssertFalse(selected.exists)
        sloper.tap()

        XCTAssertTrue(
            selected.waitForExistence(timeout: 5),
            "Tapping the Face B sloper map element must select the matching hold."
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
