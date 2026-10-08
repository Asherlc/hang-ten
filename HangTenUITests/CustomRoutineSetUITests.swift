import XCTest

final class CustomRoutineSetUITests: XCTestCase {
    override func setUpWithError() throws {
        continueAfterFailure = false
    }

    override func tearDownWithError() throws {
        XCUIApplication().terminate()
        XCUIDevice.shared.orientation = .portrait
    }

    func testSetSavesReopensEditsChildAndUngroupsWithoutLosingSteps() {
        let app = launchEditor(name: "Set review")
        addStep(title: "Hang", rest: false, in: app)
        addStep(title: "Rest", rest: true, in: app)
        createSet(count: 3, in: app)
        expandSet(in: app)
        XCTAssertTrue(app.buttons["Hang"].exists)
        XCTAssertTrue(app.buttons["Rest"].exists)
        capture(app, name: "Hang and rest grouped as a set")
        tap("customRoutine.save", in: app)
        openSavedRoutine(named: "Set review", in: app)
        reveal(app.staticTexts["Repeat 3 times"].firstMatch, in: app)
        XCTAssertTrue(app.staticTexts["Repeat 3 times"].exists)
        tap("customRoutine.actions", in: app)
        app.buttons["Edit"].tap()
        expandSet(in: app)
        changeCount(by: 1, identifier: "customRoutine.setRepeatCount", in: app)
        expandStep(titled: "Rest", in: app)
        XCTAssertFalse(app.switches["customRoutine.stepRepeat"].exists)
        let title = app.textFields["customRoutine.stepTitle"]
        reveal(title, in: app)
        title.tap()
        title.typeText(String(repeating: XCUIKeyboardKey.delete.rawValue, count: 4) + "Recovery\n")
        expandStep(titled: "Recovery", in: app)
        capture(app, name: "Set reopened with repeat count and child edits")
        tap("customRoutine.save", in: app)
        reveal(app.staticTexts["Repeat 4 times"].firstMatch, in: app)
        XCTAssertTrue(app.staticTexts["Recovery"].exists)

        tap("customRoutine.actions", in: app)
        app.buttons["Edit"].tap()
        expandSet(in: app)
        tap("customRoutine.ungroupSet", in: app)
        XCTAssertFalse(app.steppers["customRoutine.setRepeatCount"].exists)
        XCTAssertTrue(app.buttons["Hang"].exists)
        XCTAssertTrue(app.buttons["Recovery"].exists)
        capture(app, name: "Ungrouping retains both authored steps")
    }

    func testSetRangeSelectionKeepsIndividualRepeatsSeparate() {
        let app = launchEditor(name: "Set range review")
        addStep(title: "Single", rest: false, repeatCount: 2, in: app)
        addStep(title: "Hang", rest: false, in: app)
        addStep(title: "Rest", rest: true, in: app)
        addStep(title: "Finish", rest: false, in: app)
        tap("customRoutine.addSet", in: app)
        XCTAssertTrue(app.navigationBars["Create set"].waitForExistence(timeout: 5))
        tap("customRoutine.setStart", in: app)
        XCTAssertFalse(app.buttons["1. Single"].exists)
        app.buttons["4. Finish"].tap()
        XCTAssertFalse(app.buttons["customRoutine.setSave"].isEnabled)
        tap("customRoutine.setStart", in: app)
        app.buttons["2. Hang"].tap()
        XCTAssertTrue(app.buttons["customRoutine.setSave"].isEnabled)
        capture(app, name: "Set range and one repetition preview")
        tap("customRoutine.setSave", in: app)
        expandSet(in: app)
        for title in ["Hang", "Rest", "Finish"] {
            let step = app.buttons[title]
            reveal(step, in: app)
            XCTAssertTrue(step.exists)
        }
        let single = app.buttons.matching(NSPredicate(format: "label BEGINSWITH %@", "Single")).firstMatch
        reveal(single, in: app, scrollTowardTop: true)
        XCTAssertTrue(single.exists)
        capture(app, name: "Set alongside an independent repeated step")
    }

    func testSetPlaybackExpandsHangRestInOrderAndIncludesFinalRecovery() {
        let app = launchEditor(name: "Set playback review")
        addStep(title: "Hang", rest: false, in: app)
        addStep(title: "Rest", rest: true, in: app)
        createSet(count: 3, in: app)
        tap("customRoutine.save", in: app)
        openSavedRoutine(named: "Set playback review", in: app)
        tap("plan.startRoutine", in: app)
        let primary = app.buttons["workout.primaryControl"]
        XCTAssertTrue(primary.waitForExistence(timeout: 20))
        let running = XCTNSPredicateExpectation(predicate: NSPredicate(format: "label == %@", "Pause"), object: primary)
        XCTAssertEqual(XCTWaiter.wait(for: [running], timeout: 20), .completed)
        primary.tap()
        let picker = app.buttons["workout.routinePicker"]
        XCTAssertEqual(picker.label, "Step 1 of 6")
        tap("workout.routinePicker", in: app)
        XCTAssertTrue(app.navigationBars["Routine"].waitForExistence(timeout: 5))
        let rows = app.buttons.matching(NSPredicate(format: "identifier BEGINSWITH %@", "workout.step.")).allElementsBoundByIndex
        XCTAssertEqual(rows.count, 6)
        for (index, row) in rows.enumerated() {
            XCTAssertTrue(row.label.contains(index.isMultiple(of: 2) ? "Hang" : "Rest"))
        }
        reveal(rows[5], in: app)
        capture(app, name: "Three repetitions expand into six ordered intervals")
        rows[5].tap()
        XCTAssertEqual(picker.label, "Step 6 of 6")
        XCTAssertTrue(app.staticTexts["Rest"].exists)
        capture(app, name: "Final repetition retains its rest interval")
        tap("workout.skipStep", in: app)
        XCTAssertEqual(primary.label, "Review session")
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
        XCTAssertTrue(app.buttons["customRoutine.addSet"].exists)
        XCTAssertFalse(app.buttons["customRoutine.addSet"].isEnabled)
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
        app.launchEnvironment["HANGTEN_REVIEW_PORTRAIT"] = "1"
        app.launchEnvironment["HANGTEN_REVIEW_BOARD_ID"] = "tension.grindstone-original"
        app.launchEnvironment["HANGTEN_REVIEW_FREE_WORKOUTS_USED"] = "0"
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

    private func createSet(count: Int, in app: XCUIApplication) {
        tap("customRoutine.addSet", in: app)
        XCTAssertTrue(app.navigationBars["Create set"].waitForExistence(timeout: 5))
        XCTAssertTrue(app.staticTexts["Hang"].exists)
        XCTAssertTrue(app.staticTexts["Rest"].exists)
        changeCount(by: count - 2, identifier: "customRoutine.setCount", in: app)
        capture(app, name: "Create set with hang and rest preview")
        tap("customRoutine.setSave", in: app)
    }

    private func expandSet(in app: XCUIApplication) {
        let header = app.buttons.matching(NSPredicate(format: "label BEGINSWITH %@", "Set")).firstMatch
        reveal(header, in: app, scrollTowardTop: true)
        header.tap()
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
            // Modal form coordinates can include the underlying navigation
            // stack's offset. Hittability is authoritative inside the set sheet.
            if target.exists && target.isHittable,
               app.navigationBars["Create set"].exists || app.navigationBars["Edit set"].exists {
                return
            }
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
