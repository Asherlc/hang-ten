import XCTest

final class OwlClimbPokerBoardMapInteractionUITests: XCTestCase {
    override func tearDown() {
        XCUIDevice.shared.orientation = .portrait
        super.tearDown()
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
        XCTAssertFalse(app.buttons["boardDetail.reportIssue"].exists)
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

        assertReportControlsRemainAccessible(in: app)
    }

    func testReportActionSupportsTheLargestAccessibilityTextSize() {
        let app = XCUIApplication()
        app.launchEnvironment = ["HANGTEN_REVIEW_BOARD_PICKER": "1"]
        app.launchArguments = [
            "-UIPreferredContentSizeCategoryName",
            "UICTContentSizeCategoryAccessibilityExtraExtraExtraLarge"
        ]
        app.launch()

        let search = app.searchFields["Search boards"]
        XCTAssertTrue(search.waitForExistence(timeout: 30))
        search.tap()
        search.typeText("Poker")

        let holdSpecs = app.buttons["boardPicker.holdSpecs.owl-climb.poker"]
        XCTAssertTrue(holdSpecs.waitForExistence(timeout: 10))
        holdSpecs.tap()

        let selector = app.segmentedControls["boardDetail.presentationSelector"]
        XCTAssertTrue(selector.waitForExistence(timeout: 5))
        XCTAssertTrue(selector.isHittable)

        let reportIssue = app.buttons["boardDetail.reportIssue"]
        scrollToElement(reportIssue, in: app)
        XCTAssertTrue(isFullyVisibleAboveTabBar(reportIssue, in: app))
        addScreenshot(named: "Poker report action accessibility text")
    }

    private func assertReportControlsRemainAccessible(in app: XCUIApplication) {
        let selector = app.segmentedControls["boardDetail.presentationSelector"]
        XCTAssertTrue(selector.exists)
        XCTAssertTrue(selector.isHittable)

        let reportIssue = app.buttons["boardDetail.reportIssue"]
        scrollToElement(reportIssue, in: app)
        XCTAssertTrue(isFullyVisibleAboveTabBar(reportIssue, in: app))
        addScreenshot(named: "Poker Face B report action portrait")

        XCUIDevice.shared.orientation = .landscapeLeft
        XCTAssertTrue(app.wait(for: .runningForeground, timeout: 5))

        scrollToElement(selector, in: app, direction: .down)
        XCTAssertTrue(selector.isHittable)
        XCTAssertTrue(selector.buttons["Face B — deep slopers"].isSelected)

        scrollToElement(reportIssue, in: app)
        XCTAssertTrue(isFullyVisibleAboveTabBar(reportIssue, in: app))
        addScreenshot(named: "Poker Face B report action landscape")
    }

    private enum ScrollDirection {
        case up
        case down
    }

    private func scrollToElement(
        _ element: XCUIElement,
        in app: XCUIApplication,
        direction: ScrollDirection = .up
    ) {
        let scrollView = app.scrollViews["boardDetail.screen"]
        for _ in 0..<8 where !isFullyVisibleAboveTabBar(element, in: app) {
            switch direction {
            case .up:
                scrollView.swipeUp()
            case .down:
                scrollView.swipeDown()
            }
        }
        XCTAssertTrue(element.waitForExistence(timeout: 5))
    }

    private func isFullyVisibleAboveTabBar(_ element: XCUIElement, in app: XCUIApplication) -> Bool {
        guard element.exists, element.isHittable else { return false }

        let tabBar = app.tabBars.firstMatch
        let visibleBottom = tabBar.exists
            ? tabBar.frame.minY - 8
            : app.windows.firstMatch.frame.maxY
        return element.frame.minY >= app.windows.firstMatch.frame.minY
            && element.frame.maxY <= visibleBottom
    }

    private func addScreenshot(named name: String) {
        let attachment = XCTAttachment(screenshot: XCUIScreen.main.screenshot())
        attachment.name = name
        attachment.lifetime = .keepAlways
        add(attachment)
    }
}
