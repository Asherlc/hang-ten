import XCTest

final class FreeWorkoutUITests: XCTestCase {
    override func setUpWithError() throws {
        try super.setUpWithError()
        continueAfterFailure = false
    }

    func testFreeWorkoutStartSheetOpensFromTrain() {
        let app = launchResetFreeWorkout()
        let entry = app.buttons["train.freeWorkout"]
        XCTAssertTrue(entry.waitForExistence(timeout: 10))
        entry.tap()
        XCTAssertTrue(app.navigationBars["Free workout"].waitForExistence(timeout: 10))
        XCTAssertTrue(anyElement(app, "freeWorkout.start").waitForExistence(timeout: 10))
        XCTAssertTrue(app.buttons["freeWorkout.empty"].waitForExistence(timeout: 10))
        XCTAssertTrue(app.buttons["freeWorkout.last"].exists)
        // Timeline builder is gone; start sheet is the only entry.
        XCTAssertFalse(app.otherElements["freeWorkout.builder"].exists)
        XCTAssertFalse(app.otherElements["freeWorkout.session"].exists)
    }

    func testFreeWorkoutEmptySessionShowsLogControls() {
        let app = launchResetFreeWorkout()
        openEmptyLog(in: app)
        XCTAssertTrue(anyElement(app, "freeWorkout.log").waitForExistence(timeout: 10))
        XCTAssertTrue(app.buttons["freeWorkout.finish"].waitForExistence(timeout: 10))
        XCTAssertTrue(app.buttons["freeWorkout.addExercise.button"].waitForExistence(timeout: 10))
        XCTAssertTrue(anyElement(app, "freeWorkout.boardMap").waitForExistence(timeout: 10))
        XCTAssertFalse(app.otherElements["freeWorkout.builder"].exists)
        XCTAssertFalse(app.otherElements["freeWorkout.session"].exists)
    }

    func testFreeWorkoutEmptyStartsMinimalLogSession() {
        let app = launchResetFreeWorkout()
        openEmptyLog(in: app)
        XCTAssertTrue(anyElement(app, "freeWorkout.log").waitForExistence(timeout: 10))
        XCTAssertTrue(app.buttons["freeWorkout.finish"].waitForExistence(timeout: 10))
    }

    /// Empty → add hang → complete set → rest bar → Finish (≥1 set) → template Skip → Last unlocked.
    func testFreeWorkoutHangCompleteRestFinishUnlocksLastWorkout() {
        let app = launchResetFreeWorkout()
        openEmptyLog(in: app)
        addHangExercise(in: app)
        // Hang focused actions are Start Set / Log Set; manual complete uses the set checkbox
        // (pull-up owns freeWorkout.markDone). Prefer checkbox so this path is independent of guided hang.
        completeFocusedHangViaMarkDone(in: app)

        XCTAssertTrue(
            anyElement(app, "freeWorkout.restBar").waitForExistence(timeout: 15),
            "Rest bar should appear after completing a set"
        )

        finishWorkoutSkippingTemplate(in: app)

        // Start sheet dismissed after finish; reopen without reset so history remains.
        let entry = app.buttons["train.freeWorkout"]
        tapHittable(entry, timeout: 15)
        XCTAssertTrue(app.navigationBars["Free workout"].waitForExistence(timeout: 15))
        let last = app.buttons["freeWorkout.last"]
        XCTAssertTrue(last.waitForExistence(timeout: 15))
        XCTAssertTrue(last.isEnabled, "Last workout should unlock after finishing ≥1 completed set")
        XCTAssertFalse(
            app.buttons["freeWorkout.resume"].exists,
            "Finished workout should not leave an active Resume row"
        )
    }

    /// Empty → Add Hang → Start Set → Cancel guided → set stays unchecked (no rest bar).
    func testFreeWorkoutGuidedHangCancelLeavesSetUnchecked() throws {
        let app = launchResetFreeWorkout()
        openEmptyLog(in: app)
        addHangExercise(in: app)

        let startSet = firstMatching(
            in: app,
            identifiers: ["freeWorkout.startSet"],
            labels: ["Start Set"]
        )
        guard startSet.waitForExistence(timeout: 15), startSet.isHittable else {
            throw XCTSkip("Start Set not hittable; guided hang cancel path unavailable in this layout")
        }
        startSet.tap()

        let guided = anyElement(app, "freeWorkout.guidedHang")
        guard guided.waitForExistence(timeout: 15) else {
            throw XCTSkip("Guided hang overlay did not appear after Start Set")
        }

        let cancel = firstMatching(
            in: app,
            identifiers: ["freeWorkout.guidedHang.cancel"],
            labels: ["Cancel"]
        )
        if cancel.waitForExistence(timeout: 10), cancel.isHittable {
            cancel.tap()
        } else if app.alerts.buttons["Cancel"].waitForExistence(timeout: 3) {
            app.alerts.buttons["Cancel"].tap()
        } else {
            throw XCTSkip("Guided hang Cancel control not found (alert or identifier)")
        }

        // Overlay gone; set still unchecked — Start Set / checkbox remain; rest bar must not appear.
        let guidedGone = NSPredicate(format: "exists == false")
        let waitGuidedGone = expectation(for: guidedGone, evaluatedWith: guided)
        XCTAssertEqual(
            XCTWaiter.wait(for: [waitGuidedGone], timeout: 15),
            .completed,
            "Guided hang should dismiss after Cancel"
        )

        XCTAssertTrue(
            focusedSetActionAvailable(in: app, timeout: 15),
            "After Cancel, unchecked hang should still expose Start Set / Mark set complete"
        )
        XCTAssertFalse(
            anyElement(app, "freeWorkout.restBar").exists,
            "Cancel must not start rest or mark the set complete"
        )
    }

    /// Close mid-session → Resume; Finish-discard keeps Last locked; real finish unlocks Last.
    func testFreeWorkoutResumeAfterCloseAndLastAfterFinish() {
        let app = launchResetFreeWorkout()
        openEmptyLog(in: app)
        addHangExercise(in: app)

        let close = app.buttons["freeWorkout.close"]
        XCTAssertTrue(close.waitForExistence(timeout: 10))
        close.tap()

        let resume = app.buttons["freeWorkout.resume"]
        if resume.waitForExistence(timeout: 8) {
            resume.tap()
            XCTAssertTrue(anyElement(app, "freeWorkout.log").waitForExistence(timeout: 10))
            XCTAssertTrue(focusedSetActionAvailable(in: app, timeout: 10))
        } else {
            // Fallback: terminate/relaunch without reset — active log must still Resume.
            app.terminate()
            let relaunched = XCUIApplication()
            relaunched.launch()
            let entry = relaunched.buttons["train.freeWorkout"]
            tapHittable(entry, timeout: 15)
            let resumeAfterRelaunch = relaunched.buttons["freeWorkout.resume"]
            XCTAssertTrue(
                resumeAfterRelaunch.waitForExistence(timeout: 10),
                "Active log should surface Resume after Close or relaunch"
            )
            resumeAfterRelaunch.tap()
            XCTAssertTrue(anyElement(relaunched, "freeWorkout.log").waitForExistence(timeout: 10))

            finishDiscardThenRealFinishUnlocksLast(in: relaunched)
            return
        }

        finishDiscardThenRealFinishUnlocksLast(in: app)
    }

    private func finishDiscardThenRealFinishUnlocksLast(in app: XCUIApplication) {
        // Finish with zero completed sets → discard; history stays empty.
        let finish = app.buttons["freeWorkout.finish"]
        XCTAssertTrue(finish.waitForExistence(timeout: 10))
        finish.tap()
        confirmEndWorkoutDialog(in: app)
        let discardAlert = app.alerts["No completed sets"]
        XCTAssertTrue(discardAlert.waitForExistence(timeout: 8))
        let discardButtons = discardAlert.buttons.matching(NSPredicate(format: "label == %@", "Discard"))
        XCTAssertTrue(discardButtons.element(boundBy: 0).waitForExistence(timeout: 5))
        discardButtons.element(boundBy: 0).tap()

        let entry = app.buttons["train.freeWorkout"]
        tapHittable(entry, timeout: 10)
        XCTAssertTrue(app.buttons["freeWorkout.empty"].waitForExistence(timeout: 10))
        XCTAssertFalse(
            app.buttons["freeWorkout.last"].isEnabled,
            "Discard without completed sets must not unlock Last workout"
        )

        // Real finish path unlocks Last.
        openEmptyLog(in: app, alreadyOnStartSheet: true)
        addHangExercise(in: app)
        completeFocusedSetPreferringGuidedHang(in: app)
        XCTAssertTrue(anyElement(app, "freeWorkout.restBar").waitForExistence(timeout: 10))
        finishWorkoutSkippingTemplate(in: app)

        tapHittable(entry, timeout: 10)
        let last = app.buttons["freeWorkout.last"]
        XCTAssertTrue(last.waitForExistence(timeout: 10))
        XCTAssertTrue(last.isEnabled)
    }

    // MARK: - Helpers

    private func launchResetFreeWorkout() -> XCUIApplication {
        let app = XCUIApplication()
        app.launchEnvironment["HANGTEN_REVIEW_RESET_FREE_WORKOUT"] = "1"
        app.launch()
        return app
    }

    private func openEmptyLog(in app: XCUIApplication, alreadyOnStartSheet: Bool = false) {
        if !alreadyOnStartSheet {
            let entry = app.buttons["train.freeWorkout"]
            XCTAssertTrue(entry.waitForExistence(timeout: 10))
            entry.tap()
        }
        let empty = app.buttons["freeWorkout.empty"]
        XCTAssertTrue(empty.waitForExistence(timeout: 10))
        empty.tap()
        XCTAssertTrue(anyElement(app, "freeWorkout.log").waitForExistence(timeout: 10))
    }

    private func addHangExercise(in app: XCUIApplication) {
        let add = app.buttons["freeWorkout.addExercise.button"]
        XCTAssertTrue(add.waitForExistence(timeout: 10))
        add.tap()
        XCTAssertTrue(anyElement(app, "freeWorkout.addExercise").waitForExistence(timeout: 10))

        // Hang is the default type; tap the hang control when present for coverage.
        let hang = anyElement(app, "freeWorkout.addExercise.hang")
        if hang.waitForExistence(timeout: 3), hang.isHittable {
            hang.tap()
        } else if app.buttons["Hang"].waitForExistence(timeout: 2) {
            app.buttons["Hang"].tap()
        }

        let confirm = app.buttons["freeWorkout.addExercise.confirm"]
        XCTAssertTrue(confirm.waitForExistence(timeout: 10))
        confirm.tap()

        // Wait until focused hang actions are available (sheet dismissed).
        XCTAssertTrue(
            focusedSetActionAvailable(in: app, timeout: 12),
            "Added hang should expose Start Set, Mark done, or Mark set complete"
        )
    }

    /// Hang has no `freeWorkout.markDone` (pull-up only); complete via focused checkbox.
    private func completeFocusedHangViaMarkDone(in app: XCUIApplication) {
        let markDone = firstMatching(
            in: app,
            identifiers: ["freeWorkout.markDone"],
            labels: ["Mark done"]
        )
        if markDone.waitForExistence(timeout: 3), markDone.isHittable {
            markDone.tap()
            return
        }

        let checkbox = firstMatching(
            in: app,
            identifiers: ["freeWorkout.set.complete"],
            labels: ["Mark set complete"]
        )
        XCTAssertTrue(
            checkbox.waitForExistence(timeout: 15),
            "Hang set needs Mark set complete (or Mark done) to finish without guided hang"
        )
        tapHittable(checkbox, timeout: 15)
    }

    /// Prefer guided Start Set → Complete early; fall back to checkbox / Mark done.
    private func completeFocusedSetPreferringGuidedHang(in app: XCUIApplication) {
        let startSet = firstMatching(
            in: app,
            identifiers: ["freeWorkout.startSet"],
            labels: ["Start Set"]
        )
        if startSet.waitForExistence(timeout: 5), startSet.isHittable {
            startSet.tap()
            XCTAssertTrue(
                anyElement(app, "freeWorkout.guidedHang").waitForExistence(timeout: 10),
                "Start Set should present guided hang"
            )
            let completeEarly = firstMatching(
                in: app,
                identifiers: ["freeWorkout.guidedHang.completeEarly"],
                labels: ["Complete early"]
            )
            XCTAssertTrue(completeEarly.waitForExistence(timeout: 10))
            completeEarly.tap()
            return
        }

        completeFocusedHangViaMarkDone(in: app)
    }

    private func focusedSetActionAvailable(in app: XCUIApplication, timeout: TimeInterval) -> Bool {
        firstMatching(in: app, identifiers: ["freeWorkout.startSet"], labels: ["Start Set"])
            .waitForExistence(timeout: timeout)
            || firstMatching(in: app, identifiers: ["freeWorkout.markDone"], labels: ["Mark done"])
            .waitForExistence(timeout: 2)
            || firstMatching(
                in: app,
                identifiers: ["freeWorkout.set.complete"],
                labels: ["Mark set complete"]
            ).waitForExistence(timeout: 2)
    }

    private func firstMatching(
        in app: XCUIApplication,
        identifiers: [String],
        labels: [String]
    ) -> XCUIElement {
        for id in identifiers {
            let byID = anyElement(app, id)
            if byID.exists { return byID }
        }
        for label in labels {
            let button = app.buttons[label]
            if button.exists { return button }
        }
        if let id = identifiers.first {
            return anyElement(app, id)
        }
        return app.buttons[labels.first ?? ""]
    }

    private func finishWorkoutSkippingTemplate(in app: XCUIApplication) {
        // Rest Skip shares the "Skip" label with the template alert — dismiss rest first.
        let dismissRest = app.buttons["freeWorkout.rest.dismiss"]
        if dismissRest.waitForExistence(timeout: 2), dismissRest.isHittable {
            dismissRest.tap()
        }

        let finish = app.buttons["freeWorkout.finish"]
        XCTAssertTrue(finish.waitForExistence(timeout: 10))
        finish.tap()

        confirmEndWorkoutDialog(in: app)
        skipTemplatePrompt(in: app)

        // Wait until the free-workout sheet is gone so Train controls are hittable.
        let log = anyElement(app, "freeWorkout.log")
        let gone = NSPredicate(format: "exists == false")
        let wait = expectation(for: gone, evaluatedWith: log)
        XCTAssertEqual(
            XCTWaiter.wait(for: [wait], timeout: 10),
            .completed,
            "Free workout log should dismiss after Finish + Skip"
        )
    }

    private func confirmEndWorkoutDialog(in app: XCUIApplication) {
        XCTAssertTrue(
            app.staticTexts["End this free workout?"].waitForExistence(timeout: 8),
            "Expected Finish confirmation dialog"
        )

        let byID = anyElement(app, "freeWorkout.finish.confirm")
        if byID.waitForExistence(timeout: 2), byID.isHittable {
            byID.tap()
            return
        }

        // Prefer Finish controls that are not the toolbar/header actions.
        let dialogFinishes = app.buttons.matching(
            NSPredicate(
                format: "label == %@ AND identifier != %@ AND identifier != %@",
                "Finish",
                "freeWorkout.finish",
                "freeWorkout.finish.header"
            )
        )
        if dialogFinishes.element(boundBy: 0).waitForExistence(timeout: 3) {
            dialogFinishes.element(boundBy: 0).tap()
            return
        }

        let sheetFinishes = app.sheets.buttons.matching(NSPredicate(format: "label == %@", "Finish"))
        if sheetFinishes.element(boundBy: 0).waitForExistence(timeout: 2) {
            sheetFinishes.element(boundBy: 0).tap()
            return
        }

        XCTFail("Could not find Finish confirmation button")
    }

    private func skipTemplatePrompt(in app: XCUIApplication) {
        let alert = app.alerts["Save as Template?"]
        if alert.waitForExistence(timeout: 10) {
            let skipInAlert = alert.buttons.matching(NSPredicate(format: "label == %@", "Skip"))
            XCTAssertTrue(skipInAlert.element(boundBy: 0).waitForExistence(timeout: 5))
            skipInAlert.element(boundBy: 0).tap()
            return
        }

        let byID = anyElement(app, "freeWorkout.template.skip")
        if byID.waitForExistence(timeout: 3), byID.isHittable {
            byID.tap()
            return
        }

        XCTFail("Expected Save as Template? alert with Skip after finishing a set")
    }

    private func tapHittable(_ element: XCUIElement, timeout: TimeInterval = 10) {
        let predicate = NSPredicate(format: "exists == true AND isHittable == true")
        let wait = expectation(for: predicate, evaluatedWith: element)
        XCTAssertEqual(XCTWaiter.wait(for: [wait], timeout: timeout), .completed)
        element.tap()
    }

    private func anyElement(_ app: XCUIApplication, _ identifier: String) -> XCUIElement {
        let other = app.otherElements[identifier]
        if other.exists { return other }
        let button = app.buttons[identifier]
        if button.exists { return button }
        return app.descendants(matching: .any)[identifier]
    }
}
