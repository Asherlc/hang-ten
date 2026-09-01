import XCTest

final class OwlClimbPokerBoardMapInteractionUITests: XCTestCase {
    func testReviewRouteWiresRequestedPresentationIntoNormalRenderer() {
        let app = XCUIApplication()
        app.launchEnvironment = [
            "HANGTEN_REVIEW_BOARD_PRESENTATION": "1",
            "HANGTEN_REVIEW_BOARD_ID": "owl-climb.poker",
            "HANGTEN_REVIEW_PRESENTATION_ID": "face-b"
        ]
        app.launch()

        let screen = app.descendants(matching: .any)
            .matching(identifier: "boardDetail.screen")
            .firstMatch
        XCTAssertTrue(screen.waitForExistence(timeout: 30))

        let selector = app.segmentedControls["boardDetail.presentationSelector"]
        XCTAssertTrue(selector.waitForExistence(timeout: 10))
        let faceB = selector.buttons["Face B — deep slopers"]
        XCTAssertTrue(faceB.waitForExistence(timeout: 5))
        XCTAssertTrue(faceB.isSelected, "The DEBUG route must pass Face B into the normal renderer.")

        let map = app.descendants(matching: .any)
            .matching(identifier: "boardDetail.map")
            .firstMatch
        XCTAssertTrue(map.waitForExistence(timeout: 5))
    }

    func testInvalidBoardPresentationEnableValueShowsVisibleError() {
        let app = XCUIApplication()
        app.launchEnvironment = [
            "HANGTEN_REVIEW_BOARD_PRESENTATION": "true",
            "HANGTEN_REVIEW_BOARD_ID": "owl-climb.poker",
            "HANGTEN_REVIEW_PRESENTATION_ID": "face-b"
        ]
        app.launch()

        let error = app.descendants(matching: .any)
            .matching(identifier: "boardPresentationReview.error")
            .firstMatch
        XCTAssertTrue(error.waitForExistence(timeout: 30))
        XCTAssertTrue(app.staticTexts["Board presentation unavailable"].exists)
        XCTAssertTrue(
            app.staticTexts[
                "HANGTEN_REVIEW_BOARD_PRESENTATION must be exactly 1; received true."
            ].exists
        )
    }

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
