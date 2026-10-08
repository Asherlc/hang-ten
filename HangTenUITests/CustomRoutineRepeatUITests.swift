import XCTest

final class CustomRoutineRepeatUITests: XCTestCase {
    override func setUpWithError() throws {
        continueAfterFailure = false
    }

    func testInlineStepRepeatSavesReopensAndTurnsOffWithoutDeletingStep() {
        let app = launchEditor(name: "Single repeat review")
        addStep(title: "Hang", rest: false, repeatCount: 3, in: app)
        tap("customRoutine.save", in: app)
        openSavedRoutine(named: "Single repeat review", in: app)
        reveal(app.staticTexts["Repeat 3 times"].firstMatch, in: app)
        XCTAssertTrue(app.staticTexts["Repeat 3 times"].exists)
        tap("customRoutine.actions", in: app)
        app.buttons["Edit"].tap()
        expandStep(titled: "Hang", in: app)
        let toggle = app.switches["customRoutine.stepRepeat"]
        reveal(toggle, in: app)
        XCTAssertEqual(toggle.value as? String, "1")
        XCTAssertTrue(app.staticTexts["Run 3 times"].exists)
        changeCount(by: 2, in: app)
        XCTAssertTrue(app.staticTexts["Run 5 times"].exists)
        capture(app, name: "Inline step repeat reopened and edited")

        setRepeatEnabled(false, in: app)
        XCTAssertFalse(app.steppers["customRoutine.stepRepeatCount"].exists)
        capture(app, name: "Inline repeat turned off")
        expandStep(titled: "Hang", in: app)
        XCTAssertTrue(app.buttons["Hang"].exists)
        tap("customRoutine.save", in: app)
        XCTAssertFalse(app.staticTexts["Repeat 3 times"].exists)
        XCTAssertFalse(app.staticTexts["Repeat 5 times"].exists)
        capture(app, name: "Original step retained after repeat removed")
    }

    func testWorkAndRestStepsHaveIndependentInlineRepeatCounts() {
        let app = launchEditor(name: "Independent repeat review")
        addStep(title: "Rest", rest: true, repeatCount: 2, in: app)
        addStep(title: "Hang", rest: false, repeatCount: 4, in: app)
        XCTAssertFalse(app.buttons["customRoutine.addRepeat"].exists)
        XCTAssertFalse(app.staticTexts["Repeat groups"].exists)
        expandStep(titled: "Rest", in: app)
        reveal(app.switches["customRoutine.stepRepeat"], in: app)
        XCTAssertEqual(app.switches["customRoutine.stepRepeat"].value as? String, "1")
        XCTAssertTrue(app.staticTexts["Run 2 times"].exists)
        expandStep(titled: "Rest", in: app)
        tap("customRoutine.save", in: app)
        openSavedRoutine(named: "Independent repeat review", in: app)
        reveal(app.staticTexts["Repeat 2 times"].firstMatch, in: app)
        XCTAssertTrue(app.staticTexts["Repeat 2 times"].exists)
        reveal(app.staticTexts["Repeat 4 times"].firstMatch, in: app)
        XCTAssertTrue(app.staticTexts["Repeat 4 times"].exists)
        capture(app, name: "Independent work and rest repeats")
    }

    private func launchEditor(name: String) -> XCUIApplication {
        let app = XCUIApplication()
        app.launchEnvironment["HANGTEN_REVIEW_PLANS"] = "1"
        app.launchEnvironment["HANGTEN_REVIEW_ISOLATED_CUSTOM_ROUTINES"] = "1"
        app.launch()
        XCTAssertTrue(app.navigationBars["Plans"].waitForExistence(timeout: 20))
        tap("customRoutine.create", in: app)
        XCTAssertTrue(app.navigationBars["Create routine"].waitForExistence(timeout: 10))
        app.buttons["Generic"].tap()
        let nameField = app.textFields["customRoutine.name"]
        nameField.tap()
        nameField.typeText(name + "\n")
        return app
    }

    private func addStep(title: String, rest: Bool, repeatCount: Int? = nil, in app: XCUIApplication) {
        tap("customRoutine.addStep", in: app)
        let row = app.buttons["New step"]
        reveal(row, in: app)
        row.tap()
        if rest {
            tap("customRoutine.stepPhase", in: app)
            app.buttons["Rest"].tap()
        }
        let field = app.textFields["customRoutine.stepTitle"]
        reveal(field, in: app)
        field.tap()
        let oldValue = field.value as? String ?? ""
        field.typeText(String(repeating: XCUIKeyboardKey.delete.rawValue, count: oldValue.count) + title + "\n")
        if !rest {
            tap("customRoutine.stepTarget", in: app)
            app.buttons["Jugs"].tap()
        }
        if let repeatCount {
            let toggle = app.switches["customRoutine.stepRepeat"]
            reveal(toggle, in: app)
            XCTAssertEqual(toggle.value as? String, "0")
            XCTAssertFalse(app.steppers["customRoutine.stepRepeatCount"].exists)
            setRepeatEnabled(true, in: app)
            changeCount(by: repeatCount - 2, in: app)
            XCTAssertTrue(app.staticTexts["Run \(repeatCount) times"].exists)
            capture(app, name: "\(title) repeat configured during step creation")
        }
        expandStep(titled: title, in: app)
    }

    private func expandStep(titled title: String, in app: XCUIApplication) {
        let header = app.buttons.matching(NSPredicate(format: "label BEGINSWITH %@", title)).firstMatch
        reveal(header, in: app, scrollTowardTop: true)
        header.tap()
    }

    private func openSavedRoutine(named name: String, in app: XCUIApplication) {
        XCTAssertTrue(app.navigationBars["Plans"].waitForExistence(timeout: 10))
        tap("workouts.myRoutines", in: app)
        let row = app.staticTexts[name].firstMatch
        XCTAssertTrue(row.waitForExistence(timeout: 10))
        reveal(row, in: app)
        row.tap()
        XCTAssertTrue(app.navigationBars["Plan"].waitForExistence(timeout: 10))
    }

    private func changeCount(by delta: Int, identifier: String = "customRoutine.stepRepeatCount", in app: XCUIApplication) {
        let stepper = app.steppers[identifier]
        reveal(stepper, in: app)
        let suffix = delta > 0 ? "Increment" : "Decrement"
        let button = stepper.buttons["\(identifier)-\(suffix)"]
        for _ in 0..<abs(delta) { button.tap() }
    }

    private func setRepeatEnabled(_ enabled: Bool, in app: XCUIApplication) {
        let toggle = app.switches["customRoutine.stepRepeat"]
        // Stepper scrolling can move the repeat row. Reveal it again and use
        // the native switch's physical center; the aggregate row includes its label.
        reveal(toggle, in: app)
        let control = toggle.switches.firstMatch
        XCTAssertTrue(control.isEnabled)
        XCTAssertTrue(control.isHittable)
        let diagnostic = XCTAttachment(string: toggle.debugDescription)
        diagnostic.name = "Repeat switch before interaction"
        diagnostic.lifetime = .keepAlways
        add(diagnostic)
        control.coordinate(withNormalizedOffset: CGVector(dx: 0.5, dy: 0.5))
            .press(forDuration: 0.1)
        let changed = XCTNSPredicateExpectation(
            predicate: NSPredicate { _, _ in (toggle.value as? String) == (enabled ? "1" : "0") },
            object: nil
        )
        XCTAssertEqual(XCTWaiter.wait(for: [changed], timeout: 5), .completed,
                       "Repeat must become \(enabled ? "enabled" : "disabled") after one tap")
    }

    private func tap(_ identifier: String, in app: XCUIApplication) {
        let target = app.buttons[identifier].firstMatch
        reveal(target, in: app)
        target.tap()
    }

    private func reveal(_ target: XCUIElement, in app: XCUIApplication, scrollTowardTop: Bool = false) {
        for _ in 0..<10 {
            if target.exists && target.isHittable && !target.identifier.isEmpty,
               app.navigationBars.buttons.matching(identifier: target.identifier).firstMatch.exists {
                return
            }
            let contentTop = app.navigationBars.allElementsBoundByIndex.map { $0.frame.maxY }.max() ?? app.frame.minY
            let contentBottom = app.tabBars.firstMatch.isHittable ? app.tabBars.firstMatch.frame.minY : app.frame.maxY - 34
            if target.exists {
                let frame = target.frame
                if target.isHittable && frame.minY >= contentTop && frame.maxY <= contentBottom { return }
                if frame.minY < contentTop {
                    scroll(in: app, towardTop: true)
                } else {
                    scroll(in: app, towardTop: false)
                }
            } else if scrollTowardTop {
                scroll(in: app, towardTop: true)
            } else {
                scroll(in: app, towardTop: false)
            }
        }
        capture(app, name: "Unavailable control")
        XCTAssertTrue(target.exists && target.isHittable, "Control is unavailable: \(target)")
    }

    private func scroll(in app: XCUIApplication, towardTop: Bool) {
        let scrollView = app.scrollViews.firstMatch
        let flow = app.otherElements["plan.sessionFlow"]
        if scrollView.exists && flow.exists {
            // The page margin avoids the board's orbit gestures and floating tab bar.
            let marginX = (flow.frame.minX - scrollView.frame.minX - 8) / scrollView.frame.width
            let start = scrollView.coordinate(withNormalizedOffset: CGVector(dx: marginX, dy: towardTop ? 0.25 : 0.7))
            let end = scrollView.coordinate(withNormalizedOffset: CGVector(dx: marginX, dy: towardTop ? 0.7 : 0.25))
            start.press(forDuration: 0.1, thenDragTo: end, withVelocity: .slow, thenHoldForDuration: 0.2)
        } else if towardTop {
            app.swipeDown()
        } else {
            app.swipeUp()
        }
    }

    private func capture(_ app: XCUIApplication, name: String) {
        let attachment = XCTAttachment(screenshot: app.screenshot())
        attachment.name = name
        attachment.lifetime = .keepAlways
        add(attachment)
    }
}
