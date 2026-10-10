import XCTest

final class CustomRoutineSetUITests: XCTestCase {
    /// Stops at the first failure so later interactions cannot hide its cause.
    override func setUpWithError() throws {
        continueAfterFailure = false
    }

    /// Restores the simulator's app and orientation after each scenario.
    override func tearDownWithError() throws {
        XCUIApplication().terminate()
        XCUIDevice.shared.orientation = .portrait
    }

    /// Checks automatic membership, persistence and inline child editing without extra set actions.
    func testSetSavesReopensAndEditsChildInline() {
        let app = launchEditor(name: "Set review")
        addStep(title: "Hang", rest: false, in: app)
        XCTAssertTrue(app.buttons["customRoutine.setHeader.1"].exists)
        XCTAssertTrue(app.staticTexts["Repeat 1 time"].firstMatch.exists)
        capture(app, name: "One step belongs to a set by default")
        addStep(title: "Rest", rest: true, in: app)
        XCTAssertFalse(app.buttons["customRoutine.setHeader.2"].exists)
        changeCount(by: 2, in: app)
        XCTAssertTrue(app.buttons.matching(NSPredicate(format: "label BEGINSWITH %@", "Hang")).firstMatch.exists)
        XCTAssertTrue(app.buttons.matching(NSPredicate(format: "label BEGINSWITH %@", "Rest")).firstMatch.exists)
        capture(app, name: "New steps automatically join the same set")
        tap("customRoutine.save", in: app)
        openSavedRoutine(named: "Set review", in: app)
        reveal(app.staticTexts["Repeat 3 times"].firstMatch, in: app)
        XCTAssertTrue(app.staticTexts["Repeat 3 times"].firstMatch.exists)
        tap("customRoutine.actions", in: app)
        app.buttons["Edit"].tap()
        expandSet(in: app)
        changeCount(by: 1, in: app)
        expandStep(titled: "Rest", in: app)
        XCTAssertFalse(app.switches["customRoutine.stepRepeat"].exists)
        let title = app.textFields["customRoutine.stepTitle"]
        reveal(title, in: app)
        title.tap()
        title.typeText(String(repeating: XCUIKeyboardKey.delete.rawValue, count: 4) + "Recovery\n")
        expandStep(titled: "Recovery", in: app)
        capture(app, name: "Set reopened with shared count and child edits")
        tap("customRoutine.save", in: app)
        reveal(app.staticTexts["Repeat 4 times"].firstMatch, in: app)
        XCTAssertTrue(app.staticTexts["Recovery"].exists)
        tap("customRoutine.actions", in: app)
        app.buttons["Edit"].tap()
        expandSet(in: app)
        XCTAssertFalse(app.buttons["customRoutine.ungroupSet.1"].exists)
        XCTAssertFalse(app.buttons["customRoutine.editSet.1"].exists)
        XCTAssertFalse(app.buttons["customRoutine.editStepSet"].exists)
        capture(app, name: "Set edits stay inline")
    }

    /// Adding to an earlier set retains independent counts and all later steps.
    func testAddingToEarlierSetKeepsIndependentRepeats() {
        let app = launchEditor(name: "Set range review")
        addStep(title: "Single", rest: false, in: app)
        changeCount(by: 1, in: app)
        addSet(title: "Hang", rest: false, in: app)
        addStep(title: "Rest", rest: true, setNumber: 2, in: app)
        addStep(title: "Finish", rest: false, setNumber: 2, in: app)
        changeCount(by: 2, identifier: "customRoutine.setRepeatCount.2", in: app)
        addStep(title: "Extra", rest: false, in: app)
        XCTAssertTrue(app.staticTexts["Repeat 2 times"].firstMatch.exists)
        reveal(app.steppers["customRoutine.setRepeatCount.2"], in: app)
        XCTAssertTrue(app.staticTexts["Repeat 3 times"].firstMatch.exists)
        capture(app, name: "Adding to the earlier set preserves the following set")
        tap("customRoutine.save", in: app)
        openSavedRoutine(named: "Set range review", in: app)
        for title in ["Single", "Extra", "Hang", "Rest", "Finish"] {
            let step = app.staticTexts[title].firstMatch
            reveal(step, in: app)
            XCTAssertTrue(step.exists)
        }
    }

    /// Exercises consolidated choices, labeled empty duration, optional instructions and persistence.
    func testSimpleStepControlsSaveAndReopen() {
        let app = launchEditor(name: "Simple builder")
        tap("customRoutine.addSet", in: app)
        let duration = app.textFields["customRoutine.stepDuration"]
        reveal(duration, in: app)
        XCTAssertEqual(duration.value as? String, "")
        XCTAssertTrue(app.staticTexts["Time"].exists)
        XCTAssertFalse(app.buttons["customRoutine.editStepSet"].exists)
        XCTAssertFalse(app.buttons["customRoutine.stepTiming"].exists)
        XCTAssertFalse(app.buttons["customRoutine.stepOptions"].exists)
        XCTAssertFalse(app.buttons["customRoutine.ungroupSet.1"].exists)
        tap("customRoutine.stepExercise", in: app)
        app.buttons["Loaded lift"].tap()
        tap("customRoutine.stepHands", in: app)
        app.buttons["Right hand"].tap()
        tap("customRoutine.stepFingers", in: app)
        app.buttons["3 fingers"].tap()
        tap("customRoutine.stepGrip", in: app)
        app.buttons["Half crimp"].tap()
        reveal(duration, in: app, scrollTowardTop: true)
        duration.tap()
        duration.typeText("12")
        tap("customRoutine.keyboardDone", in: app)
        tap("customRoutine.stepTarget", in: app)
        app.buttons["Edges"].tap()
        enter("20", identifier: "customRoutine.stepDepthValue", in: app)
        XCTAssertFalse(app.buttons["customRoutine.holdDetails"].exists)
        XCTAssertFalse(app.buttons["customRoutine.stepShape"].exists)
        XCTAssertFalse(app.buttons["customRoutine.stepDepth"].exists)
        capture(app, name: "Exercise timing and hands in focused groups")
        XCTAssertTrue(app.staticTexts["Instructions"].exists)
        XCTAssertFalse(app.buttons["customRoutine.stepPhase"].exists)
        XCTAssertFalse(app.buttons["customRoutine.addLeftRightPair"].exists)
        XCTAssertFalse(app.textFields["customRoutine.stepAccessory"].exists)
        let instructionField = app.descendants(matching: .any)
            .matching(identifier: "customRoutine.stepInstruction").firstMatch
        reveal(instructionField, in: app)
        instructionField.tap()
        instructionField.typeText("My own cue")
        tap("customRoutine.keyboardDone", in: app)
        capture(app, name: "Instructions edited directly")
        tap("customRoutine.save", in: app)
        openSavedRoutine(named: "Simple builder", in: app)
        tap("customRoutine.actions", in: app)
        app.buttons["Edit"].tap()
        expandSet(in: app)
        expandStep(titled: "Loaded lift", in: app)
        XCTAssertTrue(app.buttons["customRoutine.stepHands"].label.contains("Right hand"))
        XCTAssertTrue(app.buttons["customRoutine.stepExercise"].label.contains("Loaded lift"))
        XCTAssertTrue(app.buttons["customRoutine.stepFingers"].label.contains("3 fingers"))
        XCTAssertTrue(app.buttons["customRoutine.stepGrip"].label.contains("Half crimp"))
        XCTAssertEqual(app.textFields["customRoutine.stepDuration"].value as? String, "12")
        let depth = app.textFields["customRoutine.stepDepthValue"]
        reveal(depth, in: app)
        XCTAssertEqual(depth.value as? String, "20")
        capture(app, name: "Consolidated selections restored after saving")
        reveal(instructionField, in: app)
        XCTAssertEqual(instructionField.value as? String, "My own cue")
    }

    /// Added-weight units never change the millimeter depths, including after reopening.
    func testWeightUnitSwitchPreservesMillimeterDepthAndSavedLoad() {
        let app = launchEditor(name: "Weight conversion review")
        XCTAssertFalse(app.segmentedControls["customRoutine.units"].exists)
        XCTAssertFalse(app.buttons["customRoutine.difficulty"].exists)
        XCTAssertFalse(app.buttons["customRoutine.category"].exists)
        XCTAssertFalse(app.textFields["customRoutine.tags"].exists)
        tap("customRoutine.addSet", in: app)
        tap("customRoutine.stepExercise", in: app)
        app.buttons["Loaded lift"].tap()
        enter("12", identifier: "customRoutine.stepDuration", in: app)
        tap("customRoutine.stepTarget", in: app)
        app.buttons["Edges"].tap()
        let depth = app.textFields["customRoutine.stepDepthValue"]
        reveal(depth, in: app)
        XCTAssertEqual(depth.value as? String, "")
        enter("12.7-", identifier: "customRoutine.stepDepthValue", in: app)
        tap("customRoutine.save", in: app)
        let errors = app.staticTexts["customRoutine.validationErrors"]
        XCTAssertTrue(errors.waitForExistence(timeout: 5))
        XCTAssertTrue(errors.label.contains("ordered range in mm"))
        XCTAssertTrue(app.navigationBars["Create routine"].exists)
        replace("12.7-38.1", identifier: "customRoutine.stepDepthValue", in: app)
        chooseWeightUnit("lb", in: app)
        let load = app.textFields["customRoutine.stepExternalLoad"]
        reveal(load, in: app)
        XCTAssertEqual(load.value as? String, "")
        enter("22.046226", identifier: "customRoutine.stepExternalLoad", in: app)
        capture(app, name: "Added weight uses pounds; hold depths use millimeters")

        chooseWeightUnit("kg", in: app)
        reveal(depth, in: app, scrollTowardTop: true)
        XCTAssertEqual(depth.value as? String, "12.7-38.1")
        XCTAssertEqual(depth.label, "Depth in millimeters")
        reveal(load, in: app)
        XCTAssertEqual(load.value as? String, "10")
        chooseWeightUnit("lb", in: app)
        tap("customRoutine.save", in: app)
        openSavedRoutine(named: "Weight conversion review", in: app)
        tap("customRoutine.actions", in: app)
        app.buttons["Edit"].tap()
        expandSet(in: app)
        expandStep(titled: "Loaded lift", in: app)
        reveal(depth, in: app)
        XCTAssertEqual(depth.value as? String, "12.7–38.1")
        reveal(load, in: app)
        XCTAssertEqual(load.value as? String, "22.046")
        capture(app, name: "Weight preference and millimeter depths survive reopening")
        chooseWeightUnit("kg", in: app)
    }

    /// Expands the default hang/rest set in order and retains its final recovery interval.
    func testSetPlaybackExpandsHangRestInOrderAndIncludesFinalRecovery() {
        let app = launchEditor(name: "Set playback review")
        addStep(title: "Hang", rest: false, in: app)
        addStep(title: "Rest", rest: true, in: app)
        changeCount(by: 2, in: app)
        tap("customRoutine.save", in: app)
        openSavedRoutine(named: "Set playback review", in: app)
        // This generic jug routine needs an explicit substitute on the edge-only board.
        let substitute = app.buttons["plan.substitution.picker.0"]
        XCTAssertTrue(substitute.waitForExistence(timeout: 10))
        XCTAssertFalse(app.buttons["plan.startRoutine"].isEnabled)
        tap("plan.substitution.picker.0", in: app)
        let option = app.buttons.matching(NSPredicate(
            format: "identifier BEGINSWITH %@", "plan.substitution.option.0."
        )).firstMatch
        XCTAssertTrue(option.waitForExistence(timeout: 5))
        option.tap()
        XCTAssertTrue(app.buttons["plan.startRoutine"].isEnabled)
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
        capture(app, name: "Three repetitions expand to six ordered intervals")
        rows[5].tap()
        XCTAssertEqual(picker.label, "Step 6 of 6")
        XCTAssertTrue(app.staticTexts["Rest"].exists)
        capture(app, name: "Final repetition retains its recovery interval")
        tap("workout.skipStep", in: app)
        XCTAssertEqual(primary.label, "Review session")
    }

    /// Persists nested repeats and adds circuit recovery only between completed rounds.
    func testCircuitSavesRepeaterAndPlaysRecoveryBetweenRounds() {
        let app = launchEditor(name: "Circuit repeater review")
        tap("customRoutine.addCircuit", in: app)
        XCTAssertTrue(app.buttons["customRoutine.circuitHeader.1"].exists)
        XCTAssertTrue(app.buttons["customRoutine.setHeader.1"].exists)
        enter("7", identifier: "customRoutine.stepDuration", in: app)
        tap("customRoutine.stepGrip", in: app)
        app.buttons["Half crimp"].tap()
        tap("customRoutine.stepTarget", in: app)
        app.buttons["Edges"].tap()
        enter("25", identifier: "customRoutine.stepDepthValue", in: app)
        let instruction = app.descendants(matching: .any)
            .matching(identifier: "customRoutine.stepInstruction").firstMatch
        reveal(instruction, in: app)
        instruction.tap()
        instruction.typeText("Pain free")
        tap("customRoutine.keyboardDone", in: app)
        expandStep(titled: "Hang", in: app)
        addStep(title: "Rest", rest: true, duration: 3, in: app)
        changeCount(by: 5, in: app)
        let circuitRest = app.textFields["customRoutine.circuitRest.1"]
        reveal(circuitRest, in: app, scrollTowardTop: true)
        XCTAssertEqual(circuitRest.value as? String, "")
        enter("180", identifier: "customRoutine.circuitRest.1", in: app)
        changeCount(by: 2, identifier: "customRoutine.circuitRepeatCount.1", in: app)
        capture(app, name: "Circuit repeats the six hang and rest pairs three times")

        tap("customRoutine.save", in: app)
        openSavedRoutine(named: "Circuit repeater review", in: app)
        tap("customRoutine.actions", in: app)
        app.buttons["Edit"].tap()
        expandCircuit(in: app)
        reveal(circuitRest, in: app)
        XCTAssertEqual(circuitRest.value as? String, "180")
        XCTAssertTrue(app.staticTexts["Repeat 3 times"].firstMatch.exists)
        expandSet(in: app)
        XCTAssertTrue(app.staticTexts["Repeat 6 times"].firstMatch.exists)
        expandStep(titled: "Hang", in: app)
        XCTAssertEqual(app.textFields["customRoutine.stepDuration"].value as? String, "7")
        XCTAssertTrue(app.buttons["customRoutine.stepGrip"].label.contains("Half crimp"))
        let depth = app.textFields["customRoutine.stepDepthValue"]
        reveal(depth, in: app)
        XCTAssertEqual(depth.value as? String, "25")
        reveal(instruction, in: app)
        XCTAssertEqual(instruction.value as? String, "Pain free")
        capture(app, name: "Circuit and inner repeater settings survive reopening")
        tap("customRoutine.save", in: app)

        tap("plan.startRoutine", in: app)
        let primary = app.buttons["workout.primaryControl"]
        XCTAssertTrue(primary.waitForExistence(timeout: 20))
        let running = XCTNSPredicateExpectation(predicate: NSPredicate(format: "label == %@", "Pause"), object: primary)
        XCTAssertEqual(XCTWaiter.wait(for: [running], timeout: 20), .completed)
        primary.tap()
        let picker = app.buttons["workout.routinePicker"]
        XCTAssertEqual(picker.label, "Step 1 of 38")
        tap("workout.routinePicker", in: app)
        XCTAssertTrue(app.navigationBars["Routine"].waitForExistence(timeout: 5))

        // Three rounds contain 12 authored intervals each, plus two circuit rests.
        // The authored final three-second rest remains in every round.
        let boundaries: [(number: Int, title: String, duration: String)] = [
            (1, "Hang", "7s"),
            (12, "Rest", "3s"),
            (13, "Rest between rounds", "3m"),
            (14, "Hang", "7s"),
            (25, "Rest", "3s"),
            (26, "Rest between rounds", "3m"),
            (27, "Hang", "7s"),
            (38, "Rest", "3s")
        ]
        for boundary in boundaries {
            let row = app.buttons.matching(NSPredicate(
                format: "identifier BEGINSWITH %@ AND label BEGINSWITH %@",
                "workout.step.", "Step \(boundary.number), "
            )).firstMatch
            revealWorkoutStep(row, in: app)
            XCTAssertTrue(row.label.contains(", \(boundary.title), \(boundary.duration)"), row.label)
            if boundary.number == 13 || boundary.number == 26 {
                row.tap()
                XCTAssertEqual(picker.label, "Step \(boundary.number) of 38")
                XCTAssertEqual(app.staticTexts["workout.timer"].label, "03:00")
                capture(app, name: "Circuit recovery at step \(boundary.number)")
                tap("workout.routinePicker", in: app)
                XCTAssertTrue(app.navigationBars["Routine"].waitForExistence(timeout: 5))
            }
        }
        capture(app, name: "Third round ends with the authored short rest")
        let finalRest = app.buttons.matching(NSPredicate(
            format: "identifier BEGINSWITH %@ AND label BEGINSWITH %@",
            "workout.step.", "Step 38, "
        )).firstMatch
        finalRest.tap()
        XCTAssertEqual(picker.label, "Step 38 of 38")
        XCTAssertEqual(app.staticTexts["workout.timer"].label, "00:03")
        tap("workout.skipStep", in: app)
        XCTAssertEqual(primary.label, "Review session")
    }

    /// Changes a one-step set back to one run while retaining its authored step and set controls.
    func testSingleStepSetSavesReopensAndReturnsToOneRunWithoutDeletingStep() {
        let app = launchEditor(name: "Single repeat review")
        addStep(title: "Hang", rest: false, in: app)
        changeCount(by: 2, in: app)
        tap("customRoutine.save", in: app)
        openSavedRoutine(named: "Single repeat review", in: app)
        reveal(app.staticTexts["Repeat 3 times"].firstMatch, in: app)
        tap("customRoutine.actions", in: app)
        app.buttons["Edit"].tap()
        expandSet(in: app)
        expandStep(titled: "Hang", in: app)
        XCTAssertFalse(app.switches["customRoutine.stepRepeat"].exists)
        expandStep(titled: "Hang", in: app)
        changeCount(by: 2, in: app)
        XCTAssertTrue(app.staticTexts["Repeat 5 times"].firstMatch.exists)
        changeCount(by: -4, in: app)
        XCTAssertTrue(app.staticTexts["Repeat 1 time"].firstMatch.exists)
        XCTAssertTrue(app.buttons["customRoutine.setHeader.1"].exists)
        XCTAssertTrue(app.buttons.matching(NSPredicate(format: "label BEGINSWITH %@", "Hang")).firstMatch.exists)
        capture(app, name: "One run retains the single-step set")
        tap("customRoutine.save", in: app)
        XCTAssertFalse(app.staticTexts["Repeat 3 times"].exists)
        XCTAssertFalse(app.staticTexts["Repeat 5 times"].exists)
        XCTAssertTrue(app.staticTexts["Hang"].exists)
    }

    /// Saves explicitly separate work/rest sets with independent counts.
    func testWorkAndRestSetsKeepIndependentRepeatCounts() {
        let app = launchEditor(name: "Independent repeat review")
        addStep(title: "Rest", rest: true, in: app)
        changeCount(by: 1, in: app)
        addSet(title: "Hang", rest: false, in: app)
        changeCount(by: 3, identifier: "customRoutine.setRepeatCount.2", in: app)
        XCTAssertTrue(app.buttons["customRoutine.addSet"].isEnabled)
        capture(app, name: "Separate rest and work sets retain independent counts")
        tap("customRoutine.save", in: app)
        openSavedRoutine(named: "Independent repeat review", in: app)
        for count in [2, 4] {
            let label = app.staticTexts["Repeat \(count) times"].firstMatch
            reveal(label, in: app)
            XCTAssertTrue(label.exists)
        }
        capture(app, name: "Saved independent set repeats")
    }

    /// Opens a named generic draft with isolated storage and deterministic review state.
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
        XCTAssertTrue(app.buttons["customRoutine.board"].label.contains("No board"))
        XCTAssertFalse(app.segmentedControls["customRoutine.targetMode"].exists)
        let field = app.textFields["customRoutine.name"]
        field.tap()
        field.typeText(name + "\n")
        return app
    }

    private func chooseWeightUnit(_ label: String, in app: XCUIApplication) {
        tap("customRoutine.stepLoadUnit", in: app)
        app.buttons[label].tap()
    }

    private func enter(_ value: String, identifier: String, in app: XCUIApplication) {
        let field = app.textFields[identifier]
        reveal(field, in: app)
        field.tap()
        field.typeText(value)
        tap("customRoutine.keyboardDone", in: app)
    }

    private func replace(_ value: String, identifier: String, in app: XCUIApplication) {
        let field = app.textFields[identifier]
        reveal(field, in: app)
        field.tap()
        let oldValue = field.value as? String ?? ""
        field.typeText(String(repeating: XCUIKeyboardKey.delete.rawValue, count: oldValue.count) + value)
        tap("customRoutine.keyboardDone", in: app)
    }

    /// Adds to the selected set, creating the first set when the planner is empty.
    private func addStep(title: String, rest: Bool, duration: Int = 10, setNumber: Int = 1, in app: XCUIApplication) {
        if !app.buttons["customRoutine.setHeader.1"].exists {
            tap("customRoutine.addSet", in: app)
        } else {
            tap("customRoutine.addSetStep.\(setNumber)", in: app)
        }
        configureNewStep(title: title, rest: rest, duration: duration, in: app)
        expandSet(in: app, number: setNumber)
        XCTAssertTrue(app.buttons["customRoutine.setHeader.\(setNumber)"].exists)
    }

    /// Starts a separate set and configures its first editable step.
    private func addSet(title: String, rest: Bool, in app: XCUIApplication) {
        tap("customRoutine.addSet", in: app)
        configureNewStep(title: title, rest: rest, in: app)
    }

    /// Authors the newly added fixture step and closes its form before another step is added.
    private func configureNewStep(title: String, rest: Bool, duration seconds: Int = 10, in app: XCUIApplication) {
        if rest {
            tap("customRoutine.stepExercise", in: app)
            app.buttons["Rest"].tap()
        }
        let duration = app.textFields["customRoutine.stepDuration"]
        reveal(duration, in: app)
        duration.tap()
        duration.typeText(String(seconds))
        tap("customRoutine.keyboardDone", in: app)
        let field = app.textFields["customRoutine.stepTitle"]
        reveal(field, in: app)
        field.tap()
        let oldValue = (field.value as? String).flatMap { $0.hasPrefix("e.g.") ? nil : $0 } ?? ""
        field.typeText(String(repeating: XCUIKeyboardKey.delete.rawValue, count: oldValue.count) + title + "\n")
        if !rest {
            tap("customRoutine.stepTarget", in: app)
            app.buttons["Jugs"].tap()
        }
        expandStep(titled: title, in: app)
    }

    /// Opens a set only when its shared count control is not already exposed.
    private func expandSet(in app: XCUIApplication, number: Int = 1) {
        let header = app.buttons["customRoutine.setHeader.\(number)"]
        reveal(header, in: app, scrollTowardTop: true)
        if !app.steppers["customRoutine.setRepeatCount.\(number)"].exists {
            header.tap()
        }
    }

    /// Reveals the circuit's shared repeat and between-round recovery controls.
    private func expandCircuit(in app: XCUIApplication, number: Int = 1) {
        let header = app.buttons["customRoutine.circuitHeader.\(number)"]
        reveal(header, in: app, scrollTowardTop: true)
        if !app.steppers["customRoutine.circuitRepeatCount.\(number)"].exists {
            header.tap()
        }
    }

    /// Toggles the named child form after bringing its disclosure into view.
    private func expandStep(titled title: String, in app: XCUIApplication) {
        let header = app.buttons.matching(NSPredicate(format: "label BEGINSWITH %@", title)).firstMatch
        reveal(header, in: app, scrollTowardTop: true)
        header.tap()
    }

    /// Opens a saved custom routine from My routines and waits for the plan screen.
    private func openSavedRoutine(named name: String, in app: XCUIApplication) {
        XCTAssertTrue(app.navigationBars["Plans"].waitForExistence(timeout: 10))
        tap("workouts.myRoutines", in: app)
        let row = app.staticTexts[name].firstMatch
        XCTAssertTrue(row.waitForExistence(timeout: 10))
        reveal(row, in: app)
        row.tap()
        XCTAssertTrue(app.navigationBars["Plan"].waitForExistence(timeout: 10))
    }

    /// Changes the chosen set's total count with native stepper controls.
    private func changeCount(by delta: Int, identifier: String = "customRoutine.setRepeatCount.1", in app: XCUIApplication) {
        let stepper = app.steppers[identifier]
        reveal(stepper, in: app)
        let suffix = delta > 0 ? "Increment" : "Decrement"
        let button = stepper.buttons["\(identifier)-\(suffix)"]
        for _ in 0..<abs(delta) { button.tap() }
    }

    /// Reveals an identified button before tapping it.
    private func tap(_ identifier: String, in app: XCUIApplication) {
        let target = app.buttons[identifier].firstMatch
        reveal(target, in: app)
        target.tap()
    }

    /// Advances through increasing step numbers inside the presented routine sheet.
    private func revealWorkoutStep(_ target: XCUIElement, in app: XCUIApplication) {
        let navigationBar = app.navigationBars["Routine"]
        let rowPredicate = NSPredicate(format: "identifier BEGINSWITH %@", "workout.step.")
        for _ in 0..<30 {
            guard navigationBar.exists,
                  let scrollView = app.scrollViews.allElementsBoundByIndex.last(where: {
                      $0.buttons.matching(rowPredicate).firstMatch.exists
                  }) else {
                capture(app, name: "Routine sheet unavailable while revealing playback step")
                XCTFail("Routine sheet must remain presented while scrolling its steps")
                return
            }
            let viewport = scrollView.frame.intersection(app.frame)
            let top = max(viewport.minY, navigationBar.frame.maxY) + 8
            let bottom = min(viewport.maxY, app.frame.maxY - 34) - 8
            if target.exists && target.isHittable,
               target.frame.minY >= top, target.frame.maxY <= bottom {
                return
            }
            // Stay inside the sheet's scroll view, in its 20-point blank gutter.
            // Starting over a row can activate that button and dismiss the picker.
            let origin = scrollView.coordinate(withNormalizedOffset: .zero)
            let start = origin.withOffset(CGVector(
                dx: viewport.minX + 8 - scrollView.frame.minX,
                dy: top + (bottom - top) * 0.8 - scrollView.frame.minY
            ))
            let end = origin.withOffset(CGVector(
                dx: viewport.minX + 8 - scrollView.frame.minX,
                dy: top + (bottom - top) * 0.3 - scrollView.frame.minY
            ))
            start.press(forDuration: 0.05, thenDragTo: end, withVelocity: .slow, thenHoldForDuration: 0.1)
        }
        capture(app, name: "Unavailable playback step")
        let hierarchy = XCTAttachment(string: app.debugDescription)
        hierarchy.name = "Unavailable playback step accessibility hierarchy"
        hierarchy.lifetime = .keepAlways
        add(hierarchy)
        XCTFail("Playback step is unavailable: \(target)")
    }

    /// Scrolls identified controls into the usable viewport of the routine sheet.
    private func reveal(_ target: XCUIElement, in app: XCUIApplication, scrollTowardTop: Bool = false) {
        for _ in 0..<10 {
            if target.exists && target.isHittable && !target.identifier.isEmpty,
               app.navigationBars.buttons.matching(identifier: target.identifier).firstMatch.exists {
                return
            }
            // A presented editor leaves the Plans navigation bar in the
            // hierarchy. Its large title must not obscure the sheet's controls.
            let contentTop = app.navigationBars.allElementsBoundByIndex.last?.frame.maxY ?? app.frame.minY
            let tabBar = app.tabBars.firstMatch
            let contentBottom = tabBar.exists && tabBar.isHittable ? tabBar.frame.minY : app.frame.maxY - 34
            if target.exists {
                let frame = target.frame
                if target.isHittable && frame.minY >= contentTop && frame.maxY <= contentBottom { return }
                scroll(in: app, towardTop: frame.minY < contentTop, top: contentTop, bottom: contentBottom)
            } else {
                scroll(in: app, towardTop: scrollTowardTop, top: contentTop, bottom: contentBottom)
            }
        }
        capture(app, name: "Unavailable control")
        let hierarchy = XCTAttachment(string: app.debugDescription)
        hierarchy.name = "Unavailable control accessibility hierarchy"
        hierarchy.lifetime = .keepAlways
        add(hierarchy)
        XCTAssertTrue(target.exists && target.isHittable, "Control is unavailable: \(target)")
    }

    /// Uses a short drag in the page margin so scrolling cannot fling past a control.
    private func scroll(in app: XCUIApplication, towardTop: Bool, top: CGFloat, bottom: CGFloat) {
        let height = bottom - top
        let startY = top + height * (towardTop ? 0.25 : 0.75)
        let endY = startY + height * (towardTop ? 0.3 : -0.3)
        let origin = app.coordinate(withNormalizedOffset: .zero)
        let start = origin.withOffset(CGVector(dx: 8, dy: startY - app.frame.minY))
        let end = origin.withOffset(CGVector(dx: 8, dy: endY - app.frame.minY))
        start.press(forDuration: 0.1, thenDragTo: end, withVelocity: .slow, thenHoldForDuration: 0.2)
    }

    /// Keeps a named screenshot for review of each exercised planner or playback state.
    private func capture(_ app: XCUIApplication, name: String) {
        let attachment = XCTAttachment(screenshot: app.screenshot())
        attachment.name = name
        attachment.lifetime = .keepAlways
        add(attachment)
    }
}
