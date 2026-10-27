import XCTest

final class WorkoutEndUITests: XCTestCase {
    private var initialSessionCount = 0
    private var activeHistoryTitle = "Max Hangs"

    override func setUpWithError() throws {
        continueAfterFailure = false
    }

    override func tearDownWithError() throws {
        XCUIApplication().terminate()
        XCUIDevice.shared.orientation = .portrait
    }

    func testSelfPacedWarmupWaitsThroughPauseResumeUntilFinish() {
        let app = openWorkout(URL(string: "hangten://plan/warmup.lattice.progressive/workout")!,
            historyTitle: "Lattice · Progressive warm-up")
        XCTAssertEqual(app.staticTexts["workout.timer"].label, "Self-paced")
        Thread.sleep(forTimeInterval: 2)
        XCTAssertFalse(app.navigationBars["Summary"].exists)
        app.buttons["Pause"].tap()
        XCTAssertTrue(app.buttons["Resume"].waitForExistence(timeout: 5))
        app.buttons["Resume"].tap()
        XCTAssertTrue(app.buttons["Pause"].waitForExistence(timeout: 5))
        XCTAssertEqual(app.staticTexts["workout.timer"].label, "Self-paced")
        attachScreenshot(named: "Warm-up waits for explicit Finish")
        app.buttons["workout.skipStep"].tap()
        XCTAssertTrue(app.navigationBars["Summary"].waitForExistence(timeout: 5))
        XCTAssertTrue(app.staticTexts["Progressive sets"].exists)
        attachScreenshot(named: "Explicitly completed self-paced warm-up")
    }

    func testActualRepsPrefillCanBeEditedAndPersistWithoutRecordingTheNextDefault() {
        let title = "Hooper's Beta · Introductory Home Hangboard"
        let app = openWorkout(URL(string: "hangten://plan/hoopers-beta.introductory-home-hangboard/workout")!,
            historyTitle: title, reviewStep: 2, chooseSubstitutes: true)
        let reps = app.textFields["workout.actualReps.pull-ups"]
        XCTAssertTrue(reps.waitForExistence(timeout: 10))
        XCTAssertEqual(reps.value as? String, "10")
        reps.tap()
        reps.doubleTap()
        reps.typeText("8")
        app.buttons["workout.dismissRepKeyboard"].tap()
        XCTAssertEqual(reps.value as? String, "8")
        attachScreenshot(named: "Actual pull-up reps edited below target")
        XCUIDevice.shared.orientation = .landscapeLeft
        defer { XCUIDevice.shared.orientation = .portrait }
        XCTAssertTrue(reps.waitForExistence(timeout: 5))
        XCTAssertEqual(reps.value as? String, "8")
        attachScreenshot(named: "Actual reps retained in landscape")
        XCUIDevice.shared.orientation = .portrait
        app.buttons["workout.skipStep"].tap()
        let next = app.textFields["workout.actualReps.push-ups"]
        XCTAssertTrue(next.waitForExistence(timeout: 5))
        XCTAssertEqual(next.value as? String, "10")
        app.buttons["workout.end"].tap()
        let save = app.alerts.buttons["workout.end.save"].firstMatch
        XCTAssertTrue(save.waitForExistence(timeout: 5))
        save.tap()
        app.tabBars.buttons["History"].tap()
        let session = historySessions(in: app).firstMatch
        XCTAssertTrue(session.waitForExistence(timeout: 10))
        session.tap()
        let actual = app.staticTexts["summary.actualReps.pull-ups"]
        XCTAssertTrue(actual.waitForExistence(timeout: 5))
        XCTAssertTrue(actual.label.contains("8 reps"))
        XCTAssertTrue(actual.label.contains("target 10"))
        XCTAssertFalse(app.staticTexts["summary.actualReps.push-ups"].exists)
        attachScreenshot(named: "Actual reps persisted and unperformed default omitted")
    }

    func testCountedMinuteWorkBecomesRemainingTimeRestWithoutRestartingClock() {
        let app = openWorkout(URL(string: "hangten://plan/method.intermediate-hangboarding.emom/workout")!,
            historyTitle: "Method Climbing · Intermediate 10-minute EMOM", reviewStep: 3, chooseSubstitutes: true)
        let reps = app.textFields["workout.actualReps.pull-ups"]
        XCTAssertTrue(reps.waitForExistence(timeout: 10))
        XCTAssertEqual(reps.value as? String, "3")
        let before = app.staticTexts["workout.timer"].label
        app.buttons["workout.skipStep"].tap()
        XCTAssertTrue(app.staticTexts["Rest"].waitForExistence(timeout: 5))
        let after = app.staticTexts["workout.timer"].label
        XCTAssertLessThanOrEqual(after, before)
        XCTAssertNotEqual(after, "01:00")
        XCTAssertFalse(reps.exists)
        attachScreenshot(named: "Rep completion keeps the minute deadline and enters rest")
    }

    func testEndOffersSaveDiscardAndKeepTraining() {
        let app = openWorkout()
        app.buttons["workout.end"].tap()
        XCTAssertTrue(app.buttons["Save session"].waitForExistence(timeout: 5))
        XCTAssertTrue(app.buttons["Discard session"].exists)
        app.buttons["Keep training"].tap()
        XCTAssertTrue(app.buttons["Pause"].waitForExistence(timeout: 5))
    }

    func testEndSavesAnEarlySessionToHistory() {
        let app = openWorkout()
        app.buttons["workout.end"].tap()
        XCTAssertTrue(app.buttons["Save session"].waitForExistence(timeout: 5))
        attachScreenshot(named: "End workout save or discard")
        app.alerts.buttons["Save session"].firstMatch.tap()
        XCTAssertFalse(app.buttons["workout.end"].waitForExistence(timeout: 2))
        app.tabBars.buttons["History"].tap()
        let sessions = historySessions(in: app)
        let session = sessions.firstMatch
        XCTAssertTrue(session.waitForExistence(timeout: 10))
        XCTAssertEqual(sessions.count, initialSessionCount + 1)
        session.tap()
        XCTAssertTrue(app.navigationBars["Session summary"].waitForExistence(timeout: 5))
        XCTAssertTrue(app.staticTexts["Max hang · set 1"].exists)
        XCTAssertFalse(app.staticTexts["Max hang · set 2"].exists)
        attachScreenshot(named: "Saved early workout first step only")
    }

    func testEndAfterReturningToFirstStepSavesOnlyPerformedSets() {
        let app = openWorkout()
        app.buttons["Pause"].tap()
        XCTAssertTrue(app.buttons["Resume"].waitForExistence(timeout: 5))

        selectWorkoutStep(titled: "Max hang · set 3", in: app)
        XCTAssertTrue(app.buttons["Resume"].waitForExistence(timeout: 5))
        app.buttons["Resume"].tap()
        XCTAssertTrue(app.buttons["Pause"].waitForExistence(timeout: 10))
        Thread.sleep(forTimeInterval: 0.25)
        app.buttons["Pause"].tap()
        XCTAssertTrue(app.buttons["Resume"].waitForExistence(timeout: 5))

        selectWorkoutStep(titled: "Max hang · set 1", in: app)
        XCTAssertTrue(app.buttons["Resume"].waitForExistence(timeout: 5))
        XCTAssertEqual(app.staticTexts["workout.timer"].label, "00:10")
        app.buttons["workout.end"].tap()
        let save = app.alerts.buttons["workout.end.save"].firstMatch
        XCTAssertTrue(save.waitForExistence(timeout: 5))
        XCTAssertTrue(save.isEnabled, "Returning to the start must preserve previously performed work.")
        attachScreenshot(named: "End after returning to first step preserves save")
        save.tap()

        XCTAssertFalse(app.buttons["workout.end"].waitForExistence(timeout: 2))
        app.tabBars.buttons["History"].tap()
        let sessions = historySessions(in: app)
        XCTAssertTrue(sessions.firstMatch.waitForExistence(timeout: 10))
        XCTAssertEqual(sessions.count, initialSessionCount + 1)
        sessions.firstMatch.tap()
        XCTAssertTrue(app.navigationBars["Session summary"].waitForExistence(timeout: 5))
        XCTAssertTrue(app.staticTexts["Max hang · set 1"].exists)
        XCTAssertTrue(app.staticTexts["Max hang · set 3"].exists)
        XCTAssertFalse(app.staticTexts["Max hang · set 2"].exists)
        attachScreenshot(named: "Saved navigation workout contains only performed sets one and three")
    }

    func testSkippingUnperformedFinalSetOmitsUnvisitedSetsFromSummary() {
        let app = openWorkout()
        app.buttons["Pause"].tap()
        XCTAssertTrue(app.buttons["Resume"].waitForExistence(timeout: 5))

        selectWorkoutStep(titled: "Max hang · set 5", in: app)
        XCTAssertTrue(app.buttons["Resume"].waitForExistence(timeout: 5))
        attachScreenshot(named: "Unperformed final set selected while paused")
        app.buttons["workout.skipStep"].tap()

        XCTAssertTrue(app.navigationBars["Summary"].waitForExistence(timeout: 5))
        XCTAssertTrue(app.staticTexts["Max hang · set 1"].exists)
        for set in 2...5 {
            XCTAssertFalse(app.staticTexts["Max hang · set \(set)"].exists,
                           "Navigating past set \(set) must not count it as performed.")
        }
        attachScreenshot(named: "Skipping final set summary contains only performed first set")
    }

    func testEndSavesIndependentStopwatchWorkWhileRoutineRemainsPaused() {
        let app = openWorkout(URL(string: "hangten://plan/tension-long-hangs/workout")!,
                              historyTitle: "Tension Long Hangs")
        app.buttons["Pause"].tap()
        XCTAssertTrue(app.buttons["Resume"].waitForExistence(timeout: 5))
        selectWorkoutStep(titled: "Long hang 2 of 3", in: app)
        XCTAssertTrue(app.buttons["Resume"].waitForExistence(timeout: 5))
        let pausedTimer = app.staticTexts["workout.timer"].label
        XCTAssertEqual(pausedTimer, "00:15")

        // SwiftUI propagates the containing stopwatch identifier to its button.
        let stopwatch = app.buttons["workout.stopwatch"]
        XCTAssertTrue(stopwatch.waitForExistence(timeout: 5))
        XCTAssertEqual(stopwatch.label, "Start stopwatch")
        stopwatch.tap()
        let running = XCTNSPredicateExpectation(
            predicate: NSPredicate(format: "label == %@", "Stop stopwatch"), object: stopwatch
        )
        XCTAssertEqual(XCTWaiter.wait(for: [running], timeout: 5), .completed)
        Thread.sleep(forTimeInterval: 0.25)
        stopwatch.tap()
        let stopped = XCTNSPredicateExpectation(
            predicate: NSPredicate(format: "label == %@", "Resume stopwatch"), object: stopwatch
        )
        XCTAssertEqual(XCTWaiter.wait(for: [stopped], timeout: 5), .completed)
        XCTAssertTrue(app.buttons["Resume"].exists)
        XCTAssertEqual(app.staticTexts["workout.timer"].label, pausedTimer)
        attachScreenshot(named: "Second long hang stopwatch recorded while routine timer stays paused")

        app.buttons["workout.end"].tap()
        let save = app.alerts.buttons["workout.end.save"].firstMatch
        XCTAssertTrue(save.waitForExistence(timeout: 5))
        XCTAssertTrue(save.isEnabled)
        save.tap()
        XCTAssertFalse(app.buttons["workout.end"].waitForExistence(timeout: 2))
        app.tabBars.buttons["History"].tap()
        let sessions = historySessions(in: app)
        XCTAssertTrue(sessions.firstMatch.waitForExistence(timeout: 10))
        XCTAssertEqual(sessions.count, initialSessionCount + 1)
        sessions.firstMatch.tap()
        XCTAssertTrue(app.navigationBars["Session summary"].waitForExistence(timeout: 5))
        XCTAssertTrue(app.staticTexts["Long hang 1 of 3"].exists)
        XCTAssertTrue(app.staticTexts["Long hang 2 of 3"].exists)
        XCTAssertFalse(app.staticTexts["Long hang 3 of 3"].exists)
        attachScreenshot(named: "Saved paused stopwatch workout contains first and second long hangs")
    }

    func testKeepTrainingPreservesAnAlreadyPausedSession() {
        let app = openWorkout()
        app.buttons["Pause"].tap()
        XCTAssertTrue(app.buttons["Resume"].waitForExistence(timeout: 5))
        app.buttons["workout.end"].tap()
        app.buttons["Keep training"].tap()
        XCTAssertTrue(app.buttons["Resume"].waitForExistence(timeout: 5))
    }

    func testEndDiscardsWithoutAddingHistory() {
        let app = openWorkout()
        app.buttons["workout.end"].tap()
        XCTAssertTrue(app.buttons["Discard session"].waitForExistence(timeout: 5))
        app.alerts.buttons["Discard session"].firstMatch.tap()
        XCTAssertFalse(app.buttons["workout.end"].waitForExistence(timeout: 2))
        app.tabBars.buttons["History"].tap()
        XCTAssertTrue(app.navigationBars["History"].waitForExistence(timeout: 10))
        XCTAssertEqual(historySessions(in: app).count, initialSessionCount)
    }

    private func openWorkout(
        _ url: URL = URL(string: "hangten://plan/research.max-hangs/workout")!,
        historyTitle: String = "Max Hangs",
        reviewStep: Int? = nil,
        chooseSubstitutes: Bool = false
    ) -> XCUIApplication {
        activeHistoryTitle = historyTitle
        let app = XCUIApplication()
        app.launchArguments = ["-workoutAudioCuesEnabled", "NO"]
        app.launchEnvironment = [
            "HANGTEN_REVIEW_BOARD_ID": "tension.honestone",
            "HANGTEN_REVIEW_FREE_WORKOUTS_USED": "0",
            "HANGTEN_REVIEW_PORTRAIT": "1"
        ]
        if let reviewStep { app.launchEnvironment["HANGTEN_REVIEW_STEP"] = String(reviewStep) }
        app.terminate()
        app.launch()
        XCTAssertTrue(app.tabBars.buttons["History"].waitForExistence(timeout: 20))
        app.tabBars.buttons["History"].tap()
        XCTAssertTrue(app.navigationBars["History"].waitForExistence(timeout: 10))
        initialSessionCount = historySessions(in: app).count
        app.tabBars.buttons["Train"].tap()
        app.open(url)
        if chooseSubstitutes, app.buttons["plan.startRoutine"].waitForExistence(timeout: 10) {
            let count = app.buttons.matching(NSPredicate(format: "identifier BEGINSWITH %@", "plan.substitution.picker.")).count
            for index in 0..<count {
                let picker = app.buttons["plan.substitution.picker.\(index)"]
                for _ in 0..<12 where !picker.isHittable { scrollPlanUp(in: app) }
                picker.tap()
                let option = app.buttons["plan.substitution.option.\(index).0"]
                XCTAssertTrue(option.waitForExistence(timeout: 5))
                option.tap()
            }
            let start = app.buttons["plan.startRoutine"]
            for _ in 0..<12 where !start.isHittable { scrollPlanUp(in: app) }
            XCTAssertTrue(start.isEnabled)
            start.tap()
        }
        XCTAssertTrue(app.buttons["Pause"].waitForExistence(timeout: 60))
        return app
    }

    private func scrollPlanUp(in app: XCUIApplication) {
        let scrollView = app.scrollViews.firstMatch
        let start = scrollView.coordinate(withNormalizedOffset: CGVector(dx: 0.02, dy: 0.75))
        let end = scrollView.coordinate(withNormalizedOffset: CGVector(dx: 0.02, dy: 0.25))
        start.press(forDuration: 0.1, thenDragTo: end)
    }

    private func historySessions(in app: XCUIApplication) -> XCUIElementQuery {
        app.buttons.matching(NSPredicate(format: "label CONTAINS %@", activeHistoryTitle))
    }

    private func selectWorkoutStep(titled title: String, in app: XCUIApplication) {
        app.buttons["workout.routinePicker"].tap()
        let navigationBar = app.navigationBars["Routine"]
        XCTAssertTrue(navigationBar.waitForExistence(timeout: 5))
        let scrollView = app.scrollViews["workout.stepList"]
        XCTAssertTrue(scrollView.waitForExistence(timeout: 5))
        let row = app.buttons.matching(NSPredicate(
            format: "identifier BEGINSWITH %@ AND label CONTAINS %@",
            "workout.step.", title
        )).firstMatch
        for _ in 0..<10 {
            let viewport = scrollView.frame.intersection(app.frame)
            let top = max(viewport.minY, navigationBar.frame.maxY) + 8
            let bottom = min(viewport.maxY, app.frame.maxY - 34) - 8
            let frame = row.exists ? row.frame : .null
            let visible = frame.intersection(CGRect(
                x: viewport.minX, y: top, width: viewport.width, height: max(0, bottom - top)
            ))
            if row.exists, row.isHittable, visible.width > 40, visible.height >= 80 {
                row.coordinate(withNormalizedOffset: CGVector(
                    dx: (visible.midX - frame.minX) / frame.width,
                    dy: (visible.midY - frame.minY) / frame.height
                )).tap()
                XCTAssertTrue(navigationBar.waitForNonExistence(timeout: 5))
                return
            }
            if frame.height > 0, frame.height.isFinite, frame.minY < top {
                scrollView.swipeDown()
            } else {
                scrollView.swipeUp()
            }
        }
        attachScreenshot(named: "Workout step unavailable: \(title)")
        XCTFail("Workout step must be selectable: \(title)")
    }

    private func attachScreenshot(named name: String) {
        let attachment = XCTAttachment(screenshot: XCUIScreen.main.screenshot())
        attachment.name = name
        attachment.lifetime = .keepAlways
        add(attachment)
    }
}

final class PlanFlowUITests: XCTestCase {
    override func setUpWithError() throws {
        continueAfterFailure = false
    }

    override func tearDownWithError() throws {
        XCUIApplication().terminate()
        XCUIDevice.shared.orientation = .portrait
    }

    func testHoopersSubstitutionsShareOneSmallEdgeChoiceAndLaunchWorkout() {
        let app = launchPlan("hoopers-beta.introductory-home-hangboard", boardID: "tension.grindstone", reviewStep: 10)
        XCTAssertEqual(app.staticTexts.matching(identifier: "Replacement for small edge").count, 1)
        attachScreenshot(named: "Hooper substitutions share one small edge choice", app: app,
                         centering: "Replacement for small edge")
        let pickers = app.buttons.matching(NSPredicate(format: "identifier BEGINSWITH %@", "plan.substitution.picker."))
        let count = pickers.count
        XCTAssertGreaterThan(count, 0)
        for index in 0..<count {
            let picker = app.buttons["plan.substitution.picker.\(index)"]
            for _ in 0..<12 {
                if picker.isHittable { break }
                scrollUp(in: app)
            }
            XCTAssertTrue(picker.isHittable)
            picker.tap()
            let option = app.buttons["plan.substitution.option.\(index).0"]
            XCTAssertTrue(option.waitForExistence(timeout: 5))
            option.tap()
        }
        XCTAssertTrue(app.staticTexts["Your adapted session"].exists)
        let start = app.buttons["plan.startRoutine"]
        for _ in 0..<8 {
            if start.isHittable { break }
            scrollUp(in: app)
        }
        XCTAssertTrue(start.isEnabled)
        attachScreenshot(named: "Hooper shared substitutions selected", app: app)
        start.tap()
        XCTAssertTrue(app.buttons["workout.end"].waitForExistence(timeout: 15))
        let renderedBoard = app.descendants(matching: .any).matching(identifier: "boardModel.3d").firstMatch
        XCTAssertTrue(renderedBoard.waitForExistence(timeout: 60))
        let highlights = XCTNSPredicateExpectation(
            predicate: NSPredicate(format: "value == %@", "Left 25 mm edge, Right 25 mm edge"),
            object: renderedBoard)
        XCTAssertEqual(XCTWaiter.wait(for: [highlights], timeout: 15), .completed)
        let pause = app.buttons["Pause"]
        XCTAssertTrue(pause.waitForExistence(timeout: 15))
        pause.tap()
        attachScreenshot(named: "Hooper matching depth workout", app: app)
    }

    func testMissingHoldsRequireExplicitSubstitutionsBeforeStarting() {
        let app = launchPlan("research.max-hangs", boardID: "owl-climb.poker")
        let picker = app.buttons["plan.substitution.picker.0"]
        XCTAssertTrue(picker.waitForExistence(timeout: 10))
        XCTAssertTrue(app.staticTexts["Choose substitutes"].exists)
        XCTAssertFalse(app.buttons["plan.startRoutine"].isEnabled)
        attachScreenshot(named: "Missing hold substitution choices", app: app)

        picker.tap()
        let option = app.buttons.matching(NSPredicate(format: "identifier BEGINSWITH %@", "plan.substitution.option.0.")).firstMatch
        XCTAssertTrue(option.waitForExistence(timeout: 5))
        option.tap()
        XCTAssertTrue(app.staticTexts["Your adapted session"].exists)
        XCTAssertTrue(app.buttons["plan.startRoutine"].isEnabled)
        attachScreenshot(named: "Explicitly selected substitute", app: app)

        picker.tap()
        app.buttons["Clear substitution"].tap()
        XCTAssertFalse(app.buttons["plan.startRoutine"].isEnabled)
    }

    func testAdjustableBoardSubstitutesShowTheirEffectiveDepths() {
        let app = launchPlan("metolius.generic-ten-minute.entry", boardID: "plateau.lifting-edge")
        let picker = app.buttons["plan.substitution.picker.0"]
        XCTAssertTrue(picker.waitForExistence(timeout: 10))
        picker.tap()
        for depth in ["10 mm", "15 mm", "18 mm"] {
            let option = app.buttons.matching(NSPredicate(format: "label CONTAINS %@", depth)).firstMatch
            XCTAssertTrue(option.exists)
            XCTAssertTrue(option.label.contains("two boards"))
        }
        attachScreenshot(named: "Adjustable board substitution depths", app: app)
        app.buttons.matching(NSPredicate(format: "label CONTAINS %@", "10 mm")).firstMatch.tap()
        XCTAssertTrue(picker.label.contains("10 mm"))
        XCTAssertFalse(app.buttons["plan.startRoutine"].isEnabled,
                       "Choosing one hold must not skip the remaining missing requirements.")
    }

    func testHoldSelectionIsRestoredAfterRelaunchAndRemainsEditable() {
        var app = launchPlan("metolius.generic-ten-minute.entry", boardID: "plateau.lifting-edge")
        var picker = app.buttons["plan.substitution.picker.0"]
        XCTAssertTrue(picker.waitForExistence(timeout: 10))
        picker.tap()
        let options = app.buttons.matching(NSPredicate(
            format: "identifier BEGINSWITH %@", "plan.substitution.option.0."))
        XCTAssertGreaterThan(options.count, 1)
        let firstLabel = options.element(boundBy: 0).label
        options.element(boundBy: 0).tap()
        XCTAssertFalse(app.buttons["plan.startRoutine"].isEnabled,
                       "Restoring one selection must still require the remaining missing holds.")
        app.terminate()

        app = launchPlan("metolius.generic-ten-minute.entry", boardID: "plateau.lifting-edge", resetHoldSelections: false)
        picker = app.buttons["plan.substitution.picker.0"]
        XCTAssertTrue(picker.waitForExistence(timeout: 10))
        XCTAssertTrue(picker.label.contains(firstLabel))
        XCTAssertFalse(app.buttons["plan.startRoutine"].isEnabled,
                       "Restoring one selection must still require the remaining missing holds.")
        attachScreenshot(named: "Remembered editable hold selection", app: app)
        picker.tap()
        let otherOption = app.buttons.matching(identifier: "plan.substitution.option.0.1").firstMatch
        XCTAssertTrue(otherOption.waitForExistence(timeout: 5))
        let secondLabel = otherOption.label
        otherOption.tap()
        app.terminate()

        app = launchPlan("metolius.generic-ten-minute.entry", boardID: "plateau.lifting-edge", resetHoldSelections: false)
        picker = app.buttons["plan.substitution.picker.0"]
        XCTAssertTrue(picker.waitForExistence(timeout: 10))
        XCTAssertTrue(picker.label.contains(secondLabel))
        picker.tap()
        app.buttons["Clear substitution"].tap()
        XCTAssertFalse(app.buttons["plan.startRoutine"].isEnabled)
        app.terminate()

        app = launchPlan("metolius.generic-ten-minute.entry", boardID: "plateau.lifting-edge", resetHoldSelections: false)
        XCTAssertTrue(app.buttons["plan.substitution.picker.0"].waitForExistence(timeout: 10))
        XCTAssertTrue(app.staticTexts["Choose substitutes"].exists)
        XCTAssertFalse(app.buttons["plan.startRoutine"].isEnabled)
    }

    func testDeepLinkedPlanWithMissingHoldsOffersSubstitutesBeforeStarting() {
        let app = XCUIApplication()
        app.launchArguments = ["-workoutAudioCuesEnabled", "NO", "-HangTen.planHoldSelections.v1", ""]
        app.launchEnvironment = [
            "HANGTEN_REVIEW_BOARD_ID": "owl-climb.poker",
            "HANGTEN_REVIEW_PORTRAIT": "1",
            "HANGTEN_REVIEW_FREE_WORKOUTS_USED": "0"
        ]
        app.terminate()
        app.open(URL(string: "hangten://plan/research.max-hangs/workout")!)

        XCTAssertTrue(app.buttons["plan.substitution.picker.0"].waitForExistence(timeout: 20))
        XCTAssertFalse(app.buttons["plan.startRoutine"].isEnabled)
        XCTAssertFalse(app.buttons["Pause"].exists)
        attachScreenshot(named: "Deep-linked plan requires substitutions", app: app)
    }

    func testCompleteRememberedSelectionPrepopulatesAnEnabledStart() {
        var app = launchPlan("research.max-hangs", boardID: "owl-climb.poker")
        let picker = app.buttons["plan.substitution.picker.0"]
        XCTAssertTrue(picker.waitForExistence(timeout: 10))
        picker.tap()
        let option = app.buttons["plan.substitution.option.0.0"]
        XCTAssertTrue(option.waitForExistence(timeout: 5))
        let selectedLabel = option.label
        option.tap()
        XCTAssertTrue(app.buttons["plan.startRoutine"].isEnabled)
        app.terminate()

        app = launchPlan("research.max-hangs", boardID: "owl-climb.poker", resetHoldSelections: false)
        XCTAssertTrue(app.buttons["plan.substitution.picker.0"].waitForExistence(timeout: 10))
        XCTAssertTrue(app.buttons["plan.substitution.picker.0"].label.contains(selectedLabel))
        XCTAssertTrue(app.buttons["plan.startRoutine"].isEnabled)
        attachScreenshot(named: "Remembered complete hold selection", app: app)
    }

    func testMaxHangsTrainingEdgeIsRestoredAfterRelaunch() {
        var app = launchPlan("research.max-hangs", boardID: "beastmaker-1000")
        let picker = app.buttons["plan.maxHangs.edgePicker"]
        XCTAssertTrue(picker.waitForExistence(timeout: 10))
        picker.tap()
        let smallerEdge = app.buttons["15 mm"]
        XCTAssertTrue(smallerEdge.waitForExistence(timeout: 5))
        smallerEdge.tap()
        XCTAssertTrue(picker.label.contains("15 mm"))
        app.terminate()

        app = launchPlan("research.max-hangs", boardID: "beastmaker-1000", resetHoldSelections: false)
        let restoredPicker = app.buttons["plan.maxHangs.edgePicker"]
        XCTAssertTrue(restoredPicker.waitForExistence(timeout: 10))
        XCTAssertTrue(restoredPicker.label.contains("15 mm"))
        XCTAssertTrue(app.buttons["plan.startRoutine"].isEnabled)
        attachScreenshot(named: "Remembered training edge", app: app)
        restoredPicker.tap()
        XCTAssertTrue(app.buttons["20 mm"].waitForExistence(timeout: 5))
        app.buttons["20 mm"].tap()
        XCTAssertTrue(restoredPicker.label.contains("20 mm"))
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

    private func launchPlan(_ id: String, landscape: Bool = false, boardID: String? = nil,
                            resetHoldSelections: Bool = true, reviewStep: Int? = nil) -> XCUIApplication {
        XCUIDevice.shared.orientation = landscape ? .landscapeLeft : .portrait
        let app = XCUIApplication()
        if resetHoldSelections {
            app.launchArguments = ["-HangTen.planHoldSelections.v1", "", "-HangTen.maxHangsDepths.v1", ""]
        }
        app.launchEnvironment["HANGTEN_REVIEW_PLAN"] = "1"
        app.launchEnvironment["HANGTEN_REVIEW_PLAN_ID"] = id
        if let boardID { app.launchEnvironment["HANGTEN_REVIEW_BOARD_ID"] = boardID }
        if let reviewStep {
            app.launchEnvironment["HANGTEN_REVIEW_STEP"] = String(reviewStep)
            // This route reviews hold selection, independently of simulator audio services.
            app.launchArguments += ["-workoutAudioCuesEnabled", "NO"]
        }
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
