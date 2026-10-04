import XCTest

final class PlanFlowUITests: XCTestCase {
    override func setUpWithError() throws {
        continueAfterFailure = false
    }

    func testRepeaterPreviewGroupsCyclesAndRetainsExceptionalRecovery() {
        let app = launchPlan("rptc.seven-three-repeaters")
        reveal("Repeat 6 times", in: app)
        XCTAssertTrue(app.staticTexts["15 cues"].exists)
        XCTAssertTrue(app.staticTexts["RPTC repeater set"].exists)
        XCTAssertFalse(app.staticTexts["RPTC repeater set · rep 2 of 7"].exists)
        attachScreenshot(named: "Repeater grouped cycles", app: app, centering: "Repeat 6 times")

        reveal("RPTC repeater set · rep 7 of 7", in: app)
        XCTAssertTrue(app.staticTexts["173s rest"].exists)
        reveal("RPTC repeater set · between-set rest", in: app)
        attachScreenshot(named: "Repeater final recovery", app: app)
    }

    func testRepeatedRoundsAlsoGroupTheirInnerHangRestCycles() {
        let app = launchPlan("method.intermediate-hangboarding.repeaters")
        reveal("Repeat 4 times", in: app)
        XCTAssertGreaterThanOrEqual(app.staticTexts.matching(NSPredicate(format: "label == %@", "Repeat 4 times")).count, 2)
        XCTAssertTrue(app.staticTexts["Repeaters"].exists)
        XCTAssertTrue(app.staticTexts["105s recovery"].exists)
        attachScreenshot(named: "Nested repeated rounds", app: app)
    }

    private func launchPlan(_ id: String) -> XCUIApplication {
        let app = XCUIApplication()
        app.launchEnvironment["HANGTEN_REVIEW_PLAN"] = "1"
        app.launchEnvironment["HANGTEN_REVIEW_PLAN_ID"] = id
        app.launchEnvironment["HANGTEN_REVIEW_PORTRAIT"] = "1"
        app.launch()
        XCTAssertTrue(app.navigationBars["Plan"].waitForExistence(timeout: 20))
        return app
    }

    private func reveal(_ text: String, in app: XCUIApplication) {
        let element = app.staticTexts[text].firstMatch
        for _ in 0..<8 {
            if element.exists, element.isHittable { return }
            app.swipeUp()
        }
        XCTAssertTrue(element.exists, "Missing plan flow content: \(text)")
    }

    private func attachScreenshot(named name: String, app: XCUIApplication, centering text: String? = nil) {
        if let text, app.staticTexts[text].firstMatch.frame.minY > app.frame.height * 0.55 {
            let start = app.coordinate(withNormalizedOffset: CGVector(dx: 0.5, dy: 0.75))
            let end = app.coordinate(withNormalizedOffset: CGVector(dx: 0.5, dy: 0.4))
            start.press(forDuration: 0.1, thenDragTo: end, withVelocity: .slow, thenHoldForDuration: 0.2)
        }
        let attachment = XCTAttachment(screenshot: app.screenshot())
        attachment.name = name
        attachment.lifetime = .keepAlways
        add(attachment)
    }
}
