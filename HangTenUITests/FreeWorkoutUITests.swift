import XCTest

final class FreeWorkoutUITests: XCTestCase {
    override func setUpWithError() throws {
        try super.setUpWithError()
        continueAfterFailure = false
    }

    func testFreeWorkoutEmptySessionShowsLogControls() {
        let app = launchResetFreeWorkout()
        let entry = app.buttons["train.freeWorkout"]
        tapVisibleButton(entry, in: app, timeout: 15)
        XCTAssertTrue(anyElement(app, "freeWorkout.start").waitForExistence(timeout: 10))
        XCTAssertTrue(app.navigationBars["Custom Workout"].waitForExistence(timeout: 10))
        XCTAssertTrue(app.buttons["freeWorkout.empty"].waitForExistence(timeout: 10))
        XCTAssertTrue(app.buttons["freeWorkout.last"].exists)
        // The start sheet replaces the old timeline builder and session.
        XCTAssertFalse(app.otherElements["freeWorkout.builder"].exists)
        XCTAssertFalse(app.otherElements["freeWorkout.session"].exists)
        openEmptyLog(in: app, alreadyOnStartSheet: true)
        XCTAssertTrue(anyElement(app, "freeWorkout.log").waitForExistence(timeout: 10))
        XCTAssertTrue(app.buttons["freeWorkout.finish"].waitForExistence(timeout: 10))
        XCTAssertTrue(app.buttons["freeWorkout.addExercise.button"].waitForExistence(timeout: 10))
        XCTAssertFalse(anyElement(app, "freeWorkout.boardMap").exists,
                       "An empty log should keep Add exercise close to the elapsed time.")
        XCTAssertFalse(app.otherElements["freeWorkout.builder"].exists)
        XCTAssertFalse(app.otherElements["freeWorkout.session"].exists)
    }

    func testPullUpCompletionCanBeUndoneAfterSkippingRest() {
        let app = launchResetFreeWorkout()
        openEmptyLog(in: app)
        app.buttons["freeWorkout.addExercise.button"].tap()
        let pullUps = anyElement(app, "freeWorkout.addExercise.pullUp")
        XCTAssertTrue(pullUps.waitForExistence(timeout: 10))
        pullUps.tap()
        app.buttons["freeWorkout.addExercise.confirm"].tap()

        let completion = app.buttons["freeWorkout.set.complete"]
        XCTAssertTrue(completion.waitForExistence(timeout: 10))
        tapVisibleControl(completion, in: app)
        let skipRest = app.buttons["freeWorkout.rest.skip"]
        XCTAssertTrue(skipRest.waitForExistence(timeout: 10))
        XCTAssertFalse(app.buttons["freeWorkout.rest.dismiss"].exists)
        tapVisibleControl(skipRest, in: app)

        let completed = app.buttons.matching(
            NSPredicate(format: "identifier BEGINSWITH %@", "freeWorkout.set.complete.")
        ).firstMatch
        XCTAssertTrue(completed.waitForExistence(timeout: 10))
        XCTAssertEqual(completed.value as? String, "Completed")
        XCTAssertTrue(completed.label.contains("Pull-ups, set 1"))
        tapVisibleControl(completed, in: app)
        XCTAssertTrue(completion.waitForExistence(timeout: 10))
        XCTAssertEqual(completion.value as? String, "Not completed")
        XCTAssertTrue(app.buttons["freeWorkout.logSet"].exists)
        XCTAssertFalse(anyElement(app, "freeWorkout.restBar").exists)
    }

    /// Empty → add hang → complete set → rest bar → Finish (≥1 set) → template Skip → Last unlocked.
    func testFreeWorkoutHangCompleteRestFinishUnlocksLastWorkout() {
        let app = launchResetFreeWorkout()
        openEmptyLog(in: app)
        addHangExercise(in: app)
        // Complete with the checkbox; starting and logging a timed set are distinct actions.
        completeFocusedSet(in: app)

        XCTAssertTrue(
            anyElement(app, "freeWorkout.restBar").waitForExistence(timeout: 15),
            "Rest bar should appear after completing a set"
        )

        finishWorkoutSkippingTemplate(in: app)

        let startSheet = anyElement(app, "freeWorkout.start")
        let startSheetGone = expectation(for: NSPredicate(format: "exists == false"), evaluatedWith: startSheet)
        XCTAssertEqual(
            XCTWaiter.wait(for: [startSheetGone], timeout: 10),
            .completed,
            "Finishing a workout should dismiss its parent start sheet"
        )

        // Start sheet dismissed after finish; reopen without reset so history remains.
        let entry = app.buttons["train.freeWorkout"]
        tapVisibleButton(entry, in: app, timeout: 15)
        XCTAssertTrue(app.navigationBars["Custom Workout"].waitForExistence(timeout: 15))
        let last = app.buttons["freeWorkout.last"]
        XCTAssertTrue(last.waitForExistence(timeout: 15))
        XCTAssertTrue(last.isEnabled, "Last workout should unlock after finishing ≥1 completed set")
        XCTAssertFalse(
            app.buttons["freeWorkout.resume"].exists,
            "Finished workout should not leave an active Resume row"
        )
    }

    /// Empty → Add Hang → Start Set → Cancel guided → set stays unchecked (no rest bar).
    func testFreeWorkoutGuidedHangCancelLeavesSetUnchecked() {
        // Exercise cancellation without requiring the simulator's audio device.
        // Hosted runners can abort inside AudioToolbox during engine prewarm.
        let app = launchResetFreeWorkout()
        openEmptyLog(in: app)
        addHangExercise(in: app)

        // XCTest can wait for the app to idle until a short guided hang has
        // already completed. Give this cancellation test enough time to find
        // and tap Cancel without racing the default ten-second countdown.
        let duration = app.textFields.matching(
            NSPredicate(format: "identifier BEGINSWITH %@", "freeWorkout.set.duration.")
        ).firstMatch
        XCTAssertTrue(duration.waitForExistence(timeout: 10))
        // The screen-coordinate helper validates visible bounds without asking
        // XCTest for the invalid activation points seen on CI text-field snapshots.
        tapVisibleControl(duration, in: app, requireHittable: false)
        let keyboard = app.keyboards.firstMatch
        // Allow one focus re-tap before injecting a single duration value.
        if !keyboard.waitForExistence(timeout: 5) {
            tapVisibleControl(duration, in: app, requireHittable: false)
        }
        XCTAssertTrue(keyboard.waitForExistence(timeout: 5),
                      "The duration field must show its keyboard before text entry")
        duration.typeText("120")
        // CI can retain a keyboard accessibility element after the onscreen
        // keyboard has disappeared. Only tap the toolbar when its button exists.
        let keyboardDone = app.buttons["freeWorkout.keyboard.done"]
        if keyboardDone.exists {
            tapVisibleControl(keyboardDone, in: app, requireHittable: false)
        }
        // Commit the formatted numeric field before querying its accessibility
        // value. CI can display the complete draft while its focused snapshot
        // still reports the previous value.
        let enteredDuration = XCTNSPredicateExpectation(
            predicate: NSPredicate(format: "value == %@", "120"), object: duration
        )
        XCTAssertEqual(XCTWaiter.wait(for: [enteredDuration], timeout: 10), .completed,
                       "The committed cancellation-test duration must be 120 seconds")

        let startSet = firstMatching(
            in: app,
            identifiers: ["freeWorkout.startSet"],
            labels: ["Start Set"]
        )
        XCTAssertTrue(startSet.waitForExistence(timeout: 10), "Added hang should expose Start Set")
        app.scrollViews["freeWorkout.log.scroll"].swipeUp()
        tapVisibleControl(startSet, in: app, requireHittable: false)

        let guided = anyElement(app, "freeWorkout.guidedHang")
        XCTAssertTrue(guided.waitForExistence(timeout: 15), "Start Set should open guided hang")

        let cancel = firstMatching(
            in: app,
            identifiers: ["freeWorkout.guidedHang.cancel"],
            labels: ["Cancel"]
        )
        if cancel.waitForExistence(timeout: 10) {
            tapVisibleControl(cancel, in: app, requireHittable: false)
        } else if app.alerts.buttons["Cancel"].exists {
            tapVisibleButton(app.alerts.buttons["Cancel"], in: app, timeout: 3)
        } else {
            XCTFail("Guided hang should expose Cancel as a control or confirmation alert")
            return
        }

        // Overlay gone; set still unchecked — Start Set / checkbox remain; rest bar must not appear.
        let guidedGone = NSPredicate(format: "exists == false")
        let waitGuidedGone = expectation(for: guidedGone, evaluatedWith: guided)
        XCTAssertEqual(
            XCTWaiter.wait(for: [waitGuidedGone], timeout: 15),
            .completed,
            "Guided hang should dismiss after Cancel"
        )

        XCTAssertTrue(anyElement(app, "freeWorkout.log").waitForExistence(timeout: 10))
        XCTAssertTrue(
            focusedSetActionAvailable(in: app, timeout: 15),
            "After Cancel, unchecked hang should still expose Start Set / Mark set complete"
        )
        XCTAssertFalse(
            anyElement(app, "freeWorkout.restBar").exists,
            "Cancel must not start rest or mark the set complete"
        )
        let cancelledState = XCTAttachment(screenshot: XCUIScreen.main.screenshot())
        cancelledState.name = "Guided hang cancelled with set unchecked"
        cancelledState.lifetime = .keepAlways
        add(cancelledState)
    }

    /// Close mid-session → Resume; discarding an unfinished session keeps Last locked.
    func testFreeWorkoutResumeAfterCloseAndDiscardKeepsLastLocked() {
        let app = launchResetFreeWorkout()
        openEmptyLog(in: app)
        addHangExercise(in: app)

        let close = app.buttons["freeWorkout.close"]
        XCTAssertTrue(close.waitForExistence(timeout: 10))
        // Navigation toolbar snapshots can report invalid activation points on CI.
        // Four accessibility queries can exceed ten seconds on hosted runners.
        tapVisibleControl(close, in: app, requireHittable: false, timeout: 30)

        let resume = app.buttons["freeWorkout.resume"]
        XCTAssertTrue(resume.waitForExistence(timeout: 8), "Active log should surface Resume after Close.")
        tapVisibleButton(resume, in: app, timeout: 10)
        XCTAssertTrue(anyElement(app, "freeWorkout.log").waitForExistence(timeout: 10))
        XCTAssertTrue(focusedSetActionAvailable(in: app, timeout: 10))

        finishDiscardKeepsLastLocked(in: app)
    }

    private func finishDiscardKeepsLastLocked(in app: XCUIApplication) {
        // Finish with zero completed sets → discard; history stays empty.
        let finish = app.buttons["freeWorkout.finish"]
        XCTAssertTrue(finish.waitForExistence(timeout: 10))
        tapVisibleControl(finish, in: app, requireHittable: false, timeout: 30)
        confirmEndWorkoutDialog(in: app)
        let discardAlert = app.alerts["No completed sets"]
        XCTAssertTrue(discardAlert.waitForExistence(timeout: 8))
        let discardButtons = discardAlert.buttons.matching(NSPredicate(format: "label == %@", "Discard"))
        XCTAssertTrue(discardButtons.element(boundBy: 0).waitForExistence(timeout: 5))
        discardButtons.element(boundBy: 0).tap()

        let entry = app.buttons["train.freeWorkout"]
        tapVisibleButton(entry, in: app, timeout: 10)
        XCTAssertTrue(app.buttons["freeWorkout.empty"].waitForExistence(timeout: 10))
        XCTAssertFalse(
            app.buttons["freeWorkout.last"].isEnabled,
            "Discard without completed sets must not unlock Last workout"
        )
    }

    func testTrainShowsCustomWorkoutAndFreeformEntries() {
        let app = launchResetFreeWorkout()
        let custom = app.buttons["train.freeWorkout"]
        XCTAssertTrue(custom.waitForExistence(timeout: 10))
        XCTAssertTrue(
            custom.label.localizedCaseInsensitiveContains("custom workout"),
            "The exercise/set log entry should be named Custom Workout: \(custom.label)"
        )
        XCTAssertFalse(custom.label.localizedCaseInsensitiveContains("freeform"))

        let freeform = app.buttons["train.freeform"]
        XCTAssertTrue(freeform.waitForExistence(timeout: 10), "Freeform should be reachable directly from Train")
        XCTAssertEqual(freeform.label, "Freeform")
    }

    func testFreeformEntryOpensSetupWithDepthAndDisabledStart() {
        let app = launchResetFreeWorkout()
        let entry = app.buttons["train.freeform"]
        tapVisibleButton(entry, in: app, timeout: 15)

        XCTAssertTrue(app.navigationBars["Freeform"].waitForExistence(timeout: 10))
        XCTAssertTrue(anyElement(app, "freeform.depth").waitForExistence(timeout: 10))
        XCTAssertTrue(anyElement(app, "freeform.tare").waitForExistence(timeout: 10))

        let start = app.buttons["freeform.start"]
        XCTAssertTrue(start.waitForExistence(timeout: 10))
        XCTAssertFalse(start.isEnabled, "Start requires a valid depth and a streaming sensor")
        captureReviewScreenshot("freeform-setup")
    }

    /// Full simulated Freeform lifecycle: enter depth, record a loaded effort
    /// with a release, pause/resume, finish, save, and confirm depth in history.
    func testFreeformLifecycleRecordsPauseResumeFinishAndSavesDepthToHistory() {
        XCUIDevice.shared.orientation = .portrait
        defer { XCUIDevice.shared.orientation = .portrait }
        let app = XCUIApplication()
        app.launchArguments = ["-workoutAudioCuesEnabled", "NO"]
        app.launchEnvironment["HANGTEN_REVIEW_RESET_FREE_WORKOUT"] = "1"
        app.launchEnvironment["HANGTEN_REVIEW_BOARD_ID"] = "tension.honestone"
        app.launchEnvironment["HANGTEN_REVIEW_MOTHERBOARD"] = "1"
        // Deterministic load/release cycles: an effort opens after the loaded
        // samples pass debounce and closes after the unloaded samples.
        app.launchEnvironment["HANGTEN_REVIEW_FREEFORM_SAMPLE_LOADS"] = "0,20,20,20,0,0,0,20,20,20,0,0"
        app.launch()

        // The review fixture flag also routes Train to Settings. The simulated
        // scale needs the flag, so leave Settings explicitly before continuing.
        if app.navigationBars["Settings"].waitForExistence(timeout: 5) {
            app.navigationBars["Settings"].buttons.firstMatch.tap()
        }
        XCTAssertTrue(app.buttons["train.freeform"].waitForExistence(timeout: 10))

        tapVisibleButton(app.buttons["train.freeform"], in: app, timeout: 15)
        XCTAssertTrue(app.navigationBars["Freeform"].waitForExistence(timeout: 10))
        enterDepthAndStartFreeform(app)

        // A confirmed open effort with positive measured duration. A pending
        // one-sample candidate has no row, so this is not a claim about release.
        XCTAssertTrue(
            anyElement(app, "freeform.effort.effort-1").waitForExistence(timeout: 12),
            "A loaded effort with positive duration should be detected"
        )
        let loaded = anyElement(app, "freeform.live.loaded")
        XCTAssertTrue(loaded.waitForExistence(timeout: 5))
        // A pending one-sample candidate has no row; require a positive
        // measured duration before exercising pause/resume.
        let positiveLoaded = expectation(
            for: NSPredicate(format: "label MATCHES '.*[1-9].*'"),
            evaluatedWith: loaded
        )
        XCTAssertEqual(XCTWaiter.wait(for: [positiveLoaded], timeout: 5), .completed)
        XCTAssertTrue(anyElement(app, "freeform.live.depth").waitForExistence(timeout: 5))
        captureReviewScreenshot("freeform-live")

        // Pause -> explicit resume.
        tapVisibleButton(app.buttons["freeform.pause"], in: app, timeout: 5)
        XCTAssertTrue(anyElement(app, "freeform.paused.user").waitForExistence(timeout: 5))
        captureReviewScreenshot("freeform-paused")

        XCUIDevice.shared.orientation = .landscapeRight
        waitForFreeformOrientation(app, landscape: true)
        XCTAssertTrue(anyElement(app, "freeform.paused.user").waitForExistence(timeout: 5))
        XCTAssertTrue(app.buttons["freeform.resume"].isEnabled)
        captureReviewScreenshot("freeform-landscape")
        XCUIDevice.shared.orientation = .portrait
        waitForFreeformOrientation(app, landscape: false)

        let resume = app.buttons["freeform.resume"]
        XCTAssertTrue(resume.waitForExistence(timeout: 5))
        tapVisibleButton(resume, in: app, timeout: 5)
        XCTAssertTrue(app.buttons["freeform.pause"].waitForExistence(timeout: 5))
        XCTAssertFalse(anyElement(app, "freeform.paused.user").exists)

        // Finish -> summary shows the entered depth.
        tapVisibleButton(app.buttons["freeform.finish"], in: app, timeout: 10)
        let summary = app.navigationBars["Summary"]
        XCTAssertTrue(summary.waitForExistence(timeout: 10))
        let summaryDepth = app.staticTexts["summary.edgeDepth"]
        XCTAssertTrue(summaryDepth.waitForExistence(timeout: 10))
        XCTAssertTrue(summaryDepth.label.contains("18.5"))
        captureReviewScreenshot("freeform-summary")

        tapVisibleButton(app.buttons["workout.summary.save"], in: app, timeout: 10)
        let saved = expectation(for: NSPredicate(format: "exists == false"), evaluatedWith: summary)
        XCTAssertEqual(XCTWaiter.wait(for: [saved], timeout: 10), .completed)

        // History -> saved Freeform session still carries its depth.
        tapVisibleControl(app.buttons["History"], in: app, timeout: 15)
        XCTAssertTrue(app.navigationBars["History"].waitForExistence(timeout: 10))
        let savedSession = app.staticTexts.matching(NSPredicate(format: "label == %@", "Freeform")).firstMatch
        XCTAssertTrue(savedSession.waitForExistence(timeout: 10))
        captureReviewScreenshot("freeform-history")
        savedSession.tap()
        XCTAssertTrue(app.navigationBars["Session summary"].waitForExistence(timeout: 10))
        let historyDepth = app.staticTexts["summary.edgeDepth"]
        XCTAssertTrue(historyDepth.waitForExistence(timeout: 10))
        XCTAssertTrue(historyDepth.label.contains("18.5"))
        captureReviewScreenshot("freeform-history-detail")
    }

    /// Empty Finish must offer Keep training and return to a live session.
    func testFreeformEmptyFinishKeepTrainingRecoversLiveSession() {
        let app = XCUIApplication()
        app.launchArguments = ["-workoutAudioCuesEnabled", "NO"]
        app.launchEnvironment["HANGTEN_REVIEW_RESET_FREE_WORKOUT"] = "1"
        app.launchEnvironment["HANGTEN_REVIEW_BOARD_ID"] = "tension.honestone"
        app.launchEnvironment["HANGTEN_REVIEW_MOTHERBOARD"] = "1"
        // No load at all, so Finish has nothing savable.
        app.launchEnvironment["HANGTEN_REVIEW_FREEFORM_SAMPLE_LOADS"] = "0,0,0,0,0,0"
        app.launch()

        if app.navigationBars["Settings"].waitForExistence(timeout: 5) {
            app.navigationBars["Settings"].buttons.firstMatch.tap()
        }
        tapVisibleButton(app.buttons["train.freeform"], in: app, timeout: 15)
        XCTAssertTrue(app.navigationBars["Freeform"].waitForExistence(timeout: 10))
        enterDepthAndStartFreeform(app)

        XCTAssertFalse(anyElement(app, "freeform.effort.effort-1").exists)
        tapVisibleButton(app.buttons["freeform.finish"], in: app, timeout: 10)

        let keepTraining = app.alerts["No efforts recorded"].buttons.matching(
            identifier: "freeform.empty.keepTraining"
        ).firstMatch
        XCTAssertTrue(keepTraining.waitForExistence(timeout: 5))
        keepTraining.tap()

        XCTAssertTrue(app.buttons["freeform.pause"].waitForExistence(timeout: 5))
        XCTAssertTrue(anyElement(app, "freeform.live.loaded").waitForExistence(timeout: 5))
        XCTAssertTrue(app.buttons["freeform.finish"].isEnabled)
    }

    // MARK: - Helpers

    private func enterDepthAndStartFreeform(_ app: XCUIApplication) {
        let depth = app.textFields["freeform.depth"]
        XCTAssertTrue(depth.waitForExistence(timeout: 10))
        depth.tap()
        depth.typeText("18.5")

        let done = app.buttons["freeform.keyboard.done"]
        XCTAssertTrue(done.waitForExistence(timeout: 5))
        done.tap()

        let start = app.buttons["freeform.start"]
        XCTAssertTrue(start.waitForExistence(timeout: 10))
        if !start.isHittable {
            app.scrollViews.containing(.textField, identifier: "freeform.depth").firstMatch.swipeUp()
        }
        tapVisibleControl(start, in: app, timeout: 12)
        XCTAssertTrue(app.buttons["freeform.pause"].waitForExistence(timeout: 10))
    }

    private func waitForFreeformOrientation(_ app: XCUIApplication, landscape: Bool) {
        let viewport = expectation(for: NSPredicate { _, _ in
            let frame = app.windows.firstMatch.frame
            return landscape ? frame.width > frame.height : frame.height > frame.width
        }, evaluatedWith: app)
        XCTAssertEqual(XCTWaiter.wait(for: [viewport], timeout: 10), .completed)
    }

    private func captureReviewScreenshot(_ name: String) {
        let attachment = XCTAttachment(screenshot: XCUIScreen.main.screenshot())
        attachment.name = name
        attachment.lifetime = .keepAlways
        add(attachment)
    }

    private func launchResetFreeWorkout() -> XCUIApplication {
        let app = XCUIApplication()
        // These cases exercise free-workout controls and history, not speech.
        app.launchArguments = ["-workoutAudioCuesEnabled", "NO"]
        app.launchEnvironment["HANGTEN_REVIEW_RESET_FREE_WORKOUT"] = "1"
        // Free Workout does not depend on a 3D board; avoid model loading while
        // locating the Train entry point on a fresh simulator.
        app.launchEnvironment["HANGTEN_REVIEW_BOARD_ID"] = "tension.honestone"
        app.launch()
        return app
    }

    private func openEmptyLog(in app: XCUIApplication, alreadyOnStartSheet: Bool = false) {
        if !alreadyOnStartSheet {
            let entry = app.buttons["train.freeWorkout"]
            tapVisibleButton(entry, in: app, timeout: 15)
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

        // Focused actions sit below the board preview on an iPhone. Scroll them into view
        // before querying XCTest, which otherwise cannot see the lazy row controls.
        let logScrollView = app.scrollViews["freeWorkout.log.scroll"]
        XCTAssertTrue(logScrollView.waitForExistence(timeout: 10), "Free-workout log should scroll")
        logScrollView.swipeUp()

        // Wait until focused hang actions are available (sheet dismissed and row visible).
        XCTAssertTrue(
            focusedSetActionAvailable(in: app, timeout: 5),
            "Added hang should expose Start set or Mark set complete"
        )
    }

    private func completeFocusedSet(in app: XCUIApplication) {
        let checkbox = firstMatching(
            in: app,
            identifiers: ["freeWorkout.set.complete"],
            labels: ["Mark set complete"]
        )
        XCTAssertTrue(
            checkbox.waitForExistence(timeout: 15),
            "The set checkbox should complete a set without starting a guided hang"
        )
        tapVisibleButton(checkbox, in: app, timeout: 15)
    }

    private func focusedSetActionAvailable(in app: XCUIApplication, timeout: TimeInterval) -> Bool {
        firstMatching(in: app, identifiers: ["freeWorkout.startSet"], labels: ["Start set"])
            .waitForExistence(timeout: timeout)
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
        let dismissRest = firstMatching(
            in: app,
            identifiers: ["freeWorkout.rest.skip", "freeWorkout.rest.dismiss"],
            labels: ["Skip rest", "Dismiss"]
        )
        if dismissRest.waitForExistence(timeout: 2), dismissRest.isHittable {
            dismissRest.tap()
        }

        let finish = app.buttons["freeWorkout.finish"]
        XCTAssertTrue(finish.waitForExistence(timeout: 10))
        tapVisibleControl(finish, in: app, requireHittable: false, timeout: 30)

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
            app.staticTexts["End this custom workout?"].waitForExistence(timeout: 8),
            "Expected Finish confirmation dialog"
        )

        let byID = anyElement(app, "freeWorkout.finish.confirm")
        if byID.waitForExistence(timeout: 2), byID.isHittable {
            byID.tap()
            return
        }

        // Prefer the confirmation action over the persistent toolbar action.
        let dialogFinishes = app.buttons.matching(
            NSPredicate(
                format: "label == %@ AND identifier != %@",
                "Finish",
                "freeWorkout.finish"
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
        let alert = app.alerts["Save as template?"]
        if alert.waitForExistence(timeout: 10) {
            XCTAssertFalse(alert.textFields.firstMatch.exists, "Skipping a template must not open the keyboard")
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

        XCTFail("Expected Save as template? alert with Skip after finishing a set")
    }

    private func tapVisibleButton(_ element: XCUIElement, in app: XCUIApplication, timeout: TimeInterval = 10) {
        tapVisibleControl(element, in: app, requireHittable: false, timeout: timeout)
    }

    private func anyElement(_ app: XCUIApplication, _ identifier: String) -> XCUIElement {
        let other = app.otherElements[identifier]
        if other.exists { return other }
        let button = app.buttons[identifier]
        if button.exists { return button }
        return app.descendants(matching: .any)[identifier]
    }
}
