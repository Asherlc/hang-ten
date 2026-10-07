import XCTest

final class CustomRoutineRepeatUITests: XCTestCase {
    override func setUpWithError() throws {
        continueAfterFailure = false
    }

    func testRepeatRangeSavesPreviewsAndReopensWithEditableCount() {
        let app = launchEditor(name: "Repeat range review")
        addStep(title: "Hang", rest: false, in: app)
        addStep(title: "Rest", rest: true, in: app)
        addStep(title: "Finish", rest: false, in: app)
        tap("customRoutine.addRepeat", in: app)
        XCTAssertTrue(app.navigationBars["Repeat steps"].waitForExistence(timeout: 10))
        selectStepOption("3. Finish", from: "customRoutine.repeatStart", title: "From step", in: app)
        XCTAssertEqual(app.buttons["customRoutine.repeatEnd"].value as? String, "3. Finish")
        selectStepOption("1. Hang", from: "customRoutine.repeatStart", title: "From step", in: app)
        selectStepOption("2. Rest", from: "customRoutine.repeatEnd", title: "Through step", in: app)
        changeCount(by: 4, in: app)
        XCTAssertTrue(app.staticTexts["Run 6 times"].exists)
        capture(app, name: "Repeat range and count")
        tap("customRoutine.repeatSave", in: app)
        XCTAssertTrue(app.buttons["Steps 1–2 · 6 times"].exists)
        capture(app, name: "Custom routine with repeated steps")
        tap("customRoutine.save", in: app)

        openSavedRoutine(named: "Repeat range review", in: app)
        reveal(app.staticTexts["Repeat 6 times"].firstMatch, in: app)
        capture(app, name: "Saved custom repeat preview")
        tap("customRoutine.actions", in: app)
        app.buttons["Edit"].tap()
        XCTAssertTrue(app.navigationBars["Edit routine"].waitForExistence(timeout: 10))
        reveal(app.buttons["Steps 1–2 · 6 times"], in: app)
        app.buttons["Steps 1–2 · 6 times"].tap()
        XCTAssertTrue(app.staticTexts["Run 6 times"].waitForExistence(timeout: 5))
        XCTAssertEqual(app.buttons["customRoutine.repeatEnd"].value as? String, "2. Rest")
        changeCount(by: -3, in: app)
        tap("customRoutine.repeatSave", in: app)
        tap("customRoutine.save", in: app)
        reveal(app.staticTexts["Repeat 3 times"].firstMatch, in: app)
        XCTAssertTrue(app.staticTexts["Repeat 3 times"].exists)
    }

    func testSingleStepRepeatCanBeCancelledAndRemovedWithoutDeletingStep() {
        let app = launchEditor(name: "Single repeat review")
        addStep(title: "Hang", rest: false, in: app)
        tap("customRoutine.addRepeat", in: app)
        changeCount(by: 1, in: app)
        tap("customRoutine.repeatSave", in: app)
        let repeatRow = app.buttons["Step 1 · 3 times"]
        XCTAssertTrue(repeatRow.exists)
        repeatRow.tap()
        changeCount(by: 2, in: app)
        app.navigationBars["Repeat steps"].buttons["Cancel"].tap()
        XCTAssertTrue(repeatRow.waitForExistence(timeout: 5))
        XCTAssertFalse(app.buttons["Step 1 · 5 times"].exists)

        repeatRow.swipeLeft()
        app.buttons["Remove repeat"].tap()
        XCTAssertFalse(repeatRow.exists)
        XCTAssertTrue(app.buttons["Hang"].exists)
        tap("customRoutine.save", in: app)
        openSavedRoutine(named: "Single repeat review", in: app)
        tap("customRoutine.actions", in: app)
        app.buttons["Edit"].tap()
        reveal(app.buttons["customRoutine.addRepeat"], in: app)
        XCTAssertTrue(app.buttons["Hang"].exists)
        XCTAssertEqual(app.buttons.matching(NSPredicate(format: "identifier BEGINSWITH %@", "customRoutine.repeat.")).count, 0)
        capture(app, name: "Repeat removed and original step retained")
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

    private func addStep(title: String, rest: Bool, in app: XCUIApplication) {
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
        let header = app.buttons[title]
        reveal(header, in: app)
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

    private func changeCount(by delta: Int, in app: XCUIApplication) {
        let stepper = app.steppers["customRoutine.repeatCount"]
        XCTAssertTrue(stepper.waitForExistence(timeout: 5))
        let suffix = delta > 0 ? "Increment" : "Decrement"
        let button = stepper.buttons["customRoutine.repeatCount-\(suffix)"]
        for _ in 0..<abs(delta) { button.tap() }
    }

    private func selectStepOption(_ label: String, from identifier: String, title: String, in app: XCUIApplication) {
        let picker = app.buttons[identifier].firstMatch
        XCTAssertTrue(picker.waitForExistence(timeout: 10))
        XCTAssertTrue(picker.isHittable, "Repeat picker is unavailable: \(identifier)")
        picker.tap()
        XCTAssertTrue(app.navigationBars[title].waitForExistence(timeout: 10))
        let option = app.buttons[label].firstMatch
        XCTAssertTrue(option.waitForExistence(timeout: 10), "Step option is unavailable: \(label)")
        capture(app, name: "Repeat step choices: \(title)")
        option.tap()
        let selected = XCTNSPredicateExpectation(
            predicate: NSPredicate { _, _ in picker.exists && picker.isHittable && picker.value as? String == label },
            object: nil
        )
        XCTAssertEqual(XCTWaiter.wait(for: [selected], timeout: 10), .completed)
        capture(app, name: "Selected repeat step: \(title)")
    }

    private func tap(_ identifier: String, in app: XCUIApplication) {
        let target = app.buttons[identifier].firstMatch
        reveal(target, in: app)
        target.tap()
    }

    private func reveal(_ target: XCUIElement, in app: XCUIApplication) {
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
                    app.swipeDown()
                } else {
                    app.swipeUp()
                }
            } else {
                app.swipeUp()
            }
        }
        capture(app, name: "Unavailable control")
        XCTAssertTrue(target.exists && target.isHittable, "Control is unavailable: \(target)")
    }

    private func capture(_ app: XCUIApplication, name: String) {
        let attachment = XCTAttachment(screenshot: app.screenshot())
        attachment.name = name
        attachment.lifetime = .keepAlways
        add(attachment)
    }
}
