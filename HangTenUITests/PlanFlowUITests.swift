import XCTest

final class PlanFlowUITests: XCTestCase {
    override func setUpWithError() throws {
        continueAfterFailure = false
    }

    override func tearDownWithError() throws {
        XCUIApplication().terminate()
        XCUIDevice.shared.orientation = .portrait
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

    func testRepeatedRoundsUseTheirDeclaredHangRestCycles() {
        let app = launchPlan("method.intermediate-hangboarding.repeaters")
        reveal("Repeat 4 times", in: app)
        XCTAssertGreaterThanOrEqual(app.staticTexts.matching(NSPredicate(format: "label == %@", "Repeat 4 times")).count, 2)
        XCTAssertEqual(app.otherElements.matching(identifier: "plan.sessionFlow").count, 1)
        let repeatCards = app.otherElements.matching(
            NSPredicate(format: "identifier BEGINSWITH %@", "plan.flow.repeat.")
        ).allElementsBoundByIndex
        let identifiers = repeatCards.map(\.identifier)
        XCTAssertGreaterThanOrEqual(identifiers.count, 2)
        XCTAssertEqual(Set(identifiers).count, identifiers.count, "Declared repeat cards must have distinct identifiers")
        XCTAssertTrue(app.staticTexts["Repeaters"].exists)
        XCTAssertTrue(app.staticTexts["105s recovery"].exists)
        attachScreenshot(named: "Declared repeated rounds", app: app)
    }

    func testFirstHoldPreviewShowsItsInstructionsBeforeStarting() {
        let app = launchPlan("metolius.generic-ten-minute.entry")
        reveal("FIRST HOLD CUE", in: app)

        let preview = app.otherElements["plan.firstHoldCue"]
        XCTAssertTrue(preview.exists)
        XCTAssertTrue(preview.staticTexts["Hang from the jugs for 15 seconds."].exists)
        XCTAssertTrue(preview.staticTexts["15s hang"].exists)
        reveal("Hang from the jugs for 15 seconds.", in: app)
        attachScreenshot(named: "First hold instructions before starting", app: app,
                         centering: "Hang from the jugs for 15 seconds.")
    }

    func testRestPreviewShowsNextHoldInstructionsAndKeepsRecoveryTiming() {
        assertRestPreview(landscape: false)
    }

    func testLandscapeRestPreviewShowsNextHoldInstructionsAndKeepsRecoveryTiming() {
        assertRestPreview(landscape: true)
    }

    private func assertRestPreview(landscape: Bool) {
        let app = launchPlan("metolius.generic-ten-minute.entry", landscape: landscape)
        defer { app.terminate() }
        reveal("Minute 1 rest", in: app)

        let rest = app.otherElements.matching(
            NSPredicate(format: "identifier BEGINSWITH %@", "plan.flow.step.")
        ).containing(.staticText, identifier: "Minute 1 rest").firstMatch
        XCTAssertTrue(rest.exists)
        XCTAssertTrue(rest.staticTexts["45s rest"].exists)
        XCTAssertTrue(rest.staticTexts["Rest for the remainder of the minute."].exists)
        XCTAssertTrue(rest.staticTexts["Do 1 pull-up on a round sloper."].exists)
        reveal("Do 1 pull-up on a round sloper.", in: app)
        attachScreenshot(named: "Rest preview with next hold instructions \(landscape ? "landscape" : "portrait")",
                         app: app, centering: "Do 1 pull-up on a round sloper.")
    }

    private func launchPlan(_ id: String, landscape: Bool = false) -> XCUIApplication {
        XCUIDevice.shared.orientation = landscape ? .landscapeLeft : .portrait
        let app = XCUIApplication()
        app.launchEnvironment["HANGTEN_REVIEW_PLAN"] = "1"
        app.launchEnvironment["HANGTEN_REVIEW_PLAN_ID"] = id
        app.launchEnvironment[landscape ? "HANGTEN_REVIEW_LANDSCAPE" : "HANGTEN_REVIEW_PORTRAIT"] = "1"
        app.launch()
        XCTAssertTrue(app.navigationBars["Plan"].waitForExistence(timeout: 20))
        let orientation = XCTNSPredicateExpectation(
            predicate: NSPredicate { _, _ in
                let frame = app.windows.firstMatch.frame
                return landscape ? frame.width > frame.height : frame.height > frame.width
            },
            object: nil
        )
        XCTAssertEqual(XCTWaiter.wait(for: [orientation], timeout: 10), .completed)
        return app
    }

    private func reveal(_ text: String, in app: XCUIApplication) {
        let element = app.staticTexts[text].firstMatch
        for _ in 0..<8 {
            if element.exists, element.isHittable { return }
            scrollUp(in: app)
        }
        XCTAssertTrue(element.isHittable, "Plan flow content must be visible: \(text)")
    }

    private func scrollUp(in app: XCUIApplication, distance: CGFloat = 0.45) {
        // The page margin avoids board orbit gestures and the floating tab bar.
        let scrollView = app.scrollViews.firstMatch
        let flow = app.otherElements["plan.sessionFlow"]
        let marginX = (flow.frame.minX - scrollView.frame.minX - 8) / scrollView.frame.width
        let start = scrollView.coordinate(withNormalizedOffset: CGVector(dx: marginX, dy: 0.7))
        let end = scrollView.coordinate(withNormalizedOffset: CGVector(dx: marginX, dy: 0.7 - distance))
        start.press(forDuration: 0.1, thenDragTo: end, withVelocity: .slow, thenHoldForDuration: 0.2)
    }

    private func attachScreenshot(named name: String, app: XCUIApplication, centering text: String? = nil) {
        if let text, app.staticTexts[text].firstMatch.frame.minY > app.windows.firstMatch.frame.height * 0.55 {
            scrollUp(in: app, distance: 0.25)
        }
        let attachment = XCTAttachment(screenshot: XCUIScreen.main.screenshot())
        attachment.name = name
        attachment.lifetime = .keepAlways
        add(attachment)
    }
}
