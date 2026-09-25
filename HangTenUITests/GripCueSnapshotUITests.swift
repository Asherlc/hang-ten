import XCTest

final class GripCueDiagnosticScreenshotUITests: XCTestCase {
    private let app = XCUIApplication()
    private let workoutDeepLink = URL(string: "hangten://plan/research.max-hangs/workout")!

    override func setUpWithError() throws {
        continueAfterFailure = false
        app.launchEnvironment = [
            "HANGTEN_REVIEW_FREE_WORKOUTS_USED": "0",
            "HANGTEN_REVIEW_STEP": "1",
            "HANGTEN_REVIEW_LANDSCAPE": "1",
        ]
        app.launch()
    }

    func testMaxHangsDeepLinkDefaultsToUntrackedAndAutoStarts() throws {
        openWorkoutDeepLinkAndChooseLeftHandIfNeeded()
        XCTAssertFalse(app.segmentedControls["workout.initialWeight.sourcePicker"].exists)
        XCTAssertFalse(app.buttons["Start"].exists)
        XCTAssertTrue(app.buttons["Pause"].waitForExistence(timeout: 20))

        let leftHandCue = app.otherElements["workout.gripCue.left"]
        XCTAssertTrue(leftHandCue.waitForExistence(timeout: 10))
        XCTAssertTrue(app.buttons["workout.gripCue.left.model"].exists)
        XCTAssertTrue(leftHandCue.label.contains("Exact fingers: index, middle, ring, and pinky"))
        XCTAssertFalse(app.staticTexts["P+R+M+I"].exists)
        XCTAssertFalse(app.staticTexts["I+M+R+P"].exists)

        let attachment = XCTAttachment(screenshot: XCUIScreen.main.screenshot())
        attachment.name = "Diagnostic screenshot: Max Hangs step 1 landscape grip cues"
        attachment.lifetime = .keepAlways
        add(attachment)
    }

    func testLandscapePreStartHasNoLegacyLoadAdjustment() throws {
        openPlanDetail()
        selectManualWeightSourceIfNeeded()
        XCTAssertTrue(app.textFields["workout.initialWeight.manualField"].waitForExistence(timeout: 10))
        XCTAssertFalse(app.textFields["Workout load adjustment"].exists)
        XCTAssertTrue(app.switches["workout.initialWeight.addBodyweight"].exists)
        let attachment = XCTAttachment(screenshot: XCUIScreen.main.screenshot())
        attachment.name = "Inline manual weight setup in landscape"
        attachment.lifetime = .keepAlways
        add(attachment)
    }

    func testLandscapeManualWorkoutHidesStreamingSensorMeter() throws {
        openPlanDetail(withMotherboardFixture: true)
        selectManualWeightSourceIfNeeded()

        XCTAssertFalse(app.textFields["Workout load adjustment"].exists)
        tapStartRoutine()
        XCTAssertTrue(app.buttons["Pause"].waitForExistence(timeout: 20))
        XCTAssertFalse(app.otherElements["motherboard.forceRocker"].exists)
        XCTAssertFalse(app.buttons["Skip preparation"].exists)
    }

    /// Opens the workout deep link only after Train is the top of the stack, then
    /// retries once if the URL was dropped during a nav/orientation settle.
    private func openWorkoutDeepLinkAndChooseLeftHandIfNeeded(
        perAttemptTimeout: TimeInterval = 20
    ) {
        waitForTrainShellReady(timeout: 20)
        let handChoice = app.buttons["handSide.left"]
        let pause = app.buttons["Pause"]
        app.open(workoutDeepLink)
        if !pause.waitForExistence(timeout: perAttemptTimeout), !handChoice.exists {
            waitForTrainShellReady(timeout: 10)
            app.open(workoutDeepLink)
        }
        if handChoice.exists {
            handChoice.tap()
        }
        XCTAssertTrue(pause.waitForExistence(timeout: perAttemptTimeout))
    }

    private func openPlanDetail(withMotherboardFixture: Bool = false) {
        app.terminate()
        app.launchEnvironment["HANGTEN_REVIEW_PLAN"] = "1"
        app.launchEnvironment["HANGTEN_REVIEW_PLAN_ID"] = "research.max-hangs"
        if withMotherboardFixture {
            app.launchEnvironment["HANGTEN_REVIEW_MOTHERBOARD"] = "1"
        } else {
            app.launchEnvironment.removeValue(forKey: "HANGTEN_REVIEW_MOTHERBOARD")
        }
        app.launch()
        XCTAssertTrue(
            app.otherElements["plan.initialWeight.setup"].waitForExistence(timeout: 15),
            "The plan review route should take precedence over fixture-only review flags."
        )
    }

    /// Train content (not merely the tab bar) must be visible — the tab bar stays
    /// present while Settings is pushed, which previously let deep links race.
    private func waitForTrainShellReady(timeout: TimeInterval) {
        let settings = app.navigationBars["Settings"]
        let trainBoard = app.otherElements["train.board"]
        let trainSettings = app.buttons["train.settings"]
        let deadline = Date().addingTimeInterval(timeout)

        while Date() < deadline {
            if !settings.exists && (trainBoard.exists || trainSettings.exists) {
                return
            }
            RunLoop.current.run(until: Date().addingTimeInterval(0.25))
        }

        XCTAssertFalse(
            settings.exists,
            "Settings must be dismissed before opening the workout deep link."
        )
        XCTAssertTrue(
            trainBoard.exists || trainSettings.exists,
            "Train shell (train.board / train.settings) should be ready before opening the workout deep link."
        )
    }

    private func selectManualWeightSourceIfNeeded() {
        let source = app.segmentedControls["workout.initialWeight.sourcePicker"]
        let manual = source.buttons["Manual"]
        guard manual.exists, !manual.isSelected else { return }
        manual.tap()
    }

    private func tapStartRoutine() {
        let start = app.buttons["plan.startRoutine"]
        XCTAssertTrue(start.waitForExistence(timeout: 10))
        if !start.isHittable {
            app.swipeUp()
        }
        start.tap()
    }

}

final class InitialWeightSetupUITests: XCTestCase {
    private let app = XCUIApplication()

    override func setUpWithError() throws {
        continueAfterFailure = false
        app.launchEnvironment = [
            "HANGTEN_REVIEW_FREE_WORKOUTS_USED": "0",
            "HANGTEN_REVIEW_PORTRAIT": "1",
            "HANGTEN_REVIEW_MOTHERBOARD": "1",
            "HANGTEN_REVIEW_SENSOR_DISCONNECTED": "1",
            "HANGTEN_REVIEW_PLAN": "1",
            "HANGTEN_REVIEW_PLAN_ID": "research.max-hangs",
        ]
        app.launch()
        XCTAssertTrue(
            app.otherElements["plan.initialWeight.setup"].waitForExistence(timeout: 15),
            "The plan review route should take precedence over fixture-only review flags."
        )
    }

    func testInlineChoicesDefaultToSkipAndKeepManualDraft() {
        let source = app.segmentedControls["workout.initialWeight.sourcePicker"]
        XCTAssertTrue(source.buttons["Skip"].isSelected)
        source.buttons["Manual"].tap()

        let bodyweight = app.switches["workout.initialWeight.addBodyweight"]
        // Tap the switch itself, rather than the center of its full-width Form row.
        bodyweight.coordinate(withNormalizedOffset: CGVector(dx: 0.93, dy: 0.5)).tap()
        XCTAssertEqual(bodyweight.value as? String, "1")
        let field = app.textFields["workout.initialWeight.manualField"]
        field.tap()
        field.typeText(String(repeating: XCUIKeyboardKey.delete.rawValue, count: (field.value as? String)?.count ?? 0))
        field.typeText("12.5")
        let enteredValue = field.value as? String
        XCTAssertEqual(enteredValue, "12.5")
        source.buttons["Scale"].tap()
        XCTAssertTrue(app.buttons["plan.initialWeight.connect"].waitForExistence(timeout: 10))
        XCTAssertTrue(app.buttons["plan.startRoutine"].exists)
        XCTAssertTrue(app.buttons["plan.initialWeight.scaleProfile"].exists)
        XCTAssertFalse(app.navigationBars["Sensor pairing"].exists)
        let attachment = XCTAttachment(screenshot: XCUIScreen.main.screenshot())
        attachment.name = "Inline supported scale setup"
        attachment.lifetime = .keepAlways
        add(attachment)
        source.buttons["Manual"].tap()
        XCTAssertTrue(field.waitForExistence(timeout: 10))
        XCTAssertEqual(field.value as? String, enteredValue)
        XCTAssertEqual(app.switches["workout.initialWeight.addBodyweight"].value as? String, "1")
    }

    func testInlineScaleConnectionStartsWithExistingSensorPreparation() {
        app.segmentedControls["workout.initialWeight.sourcePicker"].buttons["Scale"].tap()
        let connect = app.buttons["plan.initialWeight.connect"]
        XCTAssertTrue(connect.waitForExistence(timeout: 10))
        connect.tap()
        let status = app.staticTexts["plan.initialWeight.scaleStatus"]
        let connected = XCTNSPredicateExpectation(
            predicate: NSPredicate(
                format: "label == %@",
                "Your supported scale is connected and ready."
            ),
            object: status
        )
        XCTAssertEqual(XCTWaiter.wait(for: [connected], timeout: 10), .completed)
        XCTAssertEqual(connect.label, "Disconnect scale")
        XCTAssertTrue(app.buttons["plan.startRoutine"].exists)
        tapStartRoutine()
        let skip = app.buttons["Skip preparation"]
        XCTAssertTrue(skip.waitForExistence(timeout: 15))
        XCTAssertFalse(app.buttons["plan.initialWeight.connect"].exists)
        skip.tap()
        XCTAssertTrue(app.buttons["Pause"].waitForExistence(timeout: 20))
        XCTAssertTrue(app.otherElements["motherboard.forceRocker"].exists)
        app.buttons["Pause"].tap()
        XCTAssertTrue(app.buttons["Resume"].waitForExistence(timeout: 10))
        XCTAssertFalse(app.buttons["Start"].exists)
    }

    func testScaleSelectionDoesNotBlockStartWhenDisconnected() {
        app.segmentedControls["workout.initialWeight.sourcePicker"].buttons["Scale"].tap()
        tapStartRoutine()
        XCTAssertTrue(app.buttons["Pause"].waitForExistence(timeout: 20))
        XCTAssertFalse(app.buttons["Skip preparation"].exists)
        XCTAssertFalse(app.navigationBars["Sensor pairing"].exists)
    }

    private func tapStartRoutine() {
        let start = app.buttons["plan.startRoutine"]
        XCTAssertTrue(start.waitForExistence(timeout: 10))
        if !start.isHittable {
            app.swipeUp()
        }
        start.tap()
    }
}

final class DualMaxHangsHighlightUITests: XCTestCase {
    func testDualBoardExposesTheResolvedMaxHangHold() throws {
        let app = XCUIApplication()
        // HANGTEN_REVIEW_WORKOUT was removed; plan detail is the stable surface that
        // paints Dual's resolved Max Hangs hold on boardModel.3d (no weight sheet).
        app.launchEnvironment = [
            "HANGTEN_REVIEW_BOARD_ID": "captain-fingerfood.dual",
            "HANGTEN_REVIEW_PLAN_ID": "research.max-hangs",
            "HANGTEN_REVIEW_PLAN": "1",
            "HANGTEN_REVIEW_FREE_WORKOUTS_USED": "0",
        ]
        app.launch()

        XCTAssertTrue(
            app.navigationBars["Plan"].waitForExistence(timeout: 20),
            "DEBUG plan-detail review route should open Max Hangs on Dual."
        )

        let board = app.otherElements["boardModel.3d"]
        // 3D / ODR load can be slow under CI shard load.
        XCTAssertTrue(
            board.waitForExistence(timeout: 60),
            "Plan detail must expose the Dual 3D board model."
        )
        XCTAssertEqual(board.value as? String, "20 mm curved edge")
    }
}

final class IronPalmBoardMapInteractionUITests: XCTestCase {
    override func tearDown() {
        // Landscape review launches leave the shared simulator in landscape;
        // reset so later cases/suites on the same device are not poisoned.
        XCUIDevice.shared.orientation = .portrait
        super.tearDown()
    }

    func testTappingRightSloperPathSelectsRightSloper() throws {
        let app = XCUIApplication()
        // Prefer the board-detail review route over the picker: after a landscape
        // 3D board-detail test, picker launch often white-screens under CI load.
        app.launchEnvironment = [
            "HANGTEN_REVIEW_BOARD_ID": "soill.iron-palm-2",
            "HANGTEN_REVIEW_BOARD_DETAIL": "1",
            "HANGTEN_REVIEW_PORTRAIT": "1",
        ]
        app.launch()

        XCTAssertTrue(
            app.navigationBars["Hold specs"].waitForExistence(timeout: 30),
            "The DEBUG board-detail route must be displayed."
        )

        let rightSloper = app.buttons["Right sloper"]
        XCTAssertTrue(
            rightSloper.waitForExistence(timeout: 10),
            "The right sloper's canonical path must be exposed as the tappable board-map element."
        )
        rightSloper.tap()

        XCTAssertTrue(
            app.otherElements["boardDetail.selectedHold.sloper-right"].waitForExistence(timeout: 10)
        )
    }
}

final class OneHandedHandChoiceUITests: XCTestCase {
    private let app = XCUIApplication()

    override func setUpWithError() throws {
        continueAfterFailure = false
        app.launchEnvironment = [
            "HANGTEN_REVIEW_BOARD_ID": "captain-fingerfood.dual",
            "HANGTEN_REVIEW_PLAN_ID": "research.max-hangs",
            "HANGTEN_REVIEW_PLAN": "1",
            "HANGTEN_REVIEW_PORTRAIT": "1",
            "HANGTEN_REVIEW_FREE_WORKOUTS_USED": "0",
        ]
        app.launch()
    }

    func testInlineHandChoiceOnOneHandedBoard() throws {
        XCTAssertTrue(
            app.navigationBars["Plan"].waitForExistence(timeout: 20),
            "DEBUG plan-detail review route should open Max Hangs on the one-handed Dual board."
        )

        selectManualWeightSourceIfNeeded()
        tapStartRoutine()

        let handPicker = app.buttons["workout.handPicker"]
        XCTAssertTrue(
            handPicker.waitForExistence(timeout: 20),
            "The pre-start workout page must expose the inline hand picker when a choice is needed."
        )
        XCTAssertTrue(
            handPicker.label.contains("Alternate hands"),
            "A capacity-1 board must default to Alternate hands, got: \(handPicker.label)"
        )

        handPicker.tap()

        let both = app.buttons["handSide.both"]
        XCTAssertTrue(both.waitForExistence(timeout: 10), "The Both menu item must be present.")
        XCTAssertEqual(both.label, "Both hands (two boards)")
        XCTAssertTrue(app.buttons["handSide.alternate"].exists, "The Alternate menu item must be present.")

        app.buttons["handSide.left"].tap()

        let updated = app.buttons["workout.handPicker"]
        let labelUpdated = XCTNSPredicateExpectation(
            predicate: NSPredicate(format: "label CONTAINS %@", "Left hand"),
            object: updated
        )
        XCTAssertEqual(
            XCTWaiter.wait(for: [labelUpdated], timeout: 10),
            .completed,
            "Choosing a hand must update the picker label, got: \(updated.label)"
        )

        let start = app.buttons["Start"]
        XCTAssertTrue(start.waitForExistence(timeout: 10))
        start.tap()

        XCTAssertTrue(app.buttons["Pause"].waitForExistence(timeout: 20))
        XCTAssertFalse(
            app.buttons["workout.handPicker"].isEnabled,
            "The hand picker must be disabled once the routine is running."
        )
    }

    private func selectManualWeightSourceIfNeeded() {
        let source = app.segmentedControls["workout.initialWeight.sourcePicker"]
        let manual = source.buttons["Manual"]
        guard manual.exists, !manual.isSelected else { return }
        manual.tap()
    }

    private func tapStartRoutine() {
        let start = app.buttons["plan.startRoutine"]
        XCTAssertTrue(start.waitForExistence(timeout: 10))
        if !start.isHittable {
            app.swipeUp()
        }
        start.tap()
    }
}
