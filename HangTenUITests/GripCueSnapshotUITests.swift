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
        openWorkoutDeepLinkExpectingInitialWeightSetup()
    }

    func testMaxHangsStepOneExposesIndividualHandCuesAndCapturesDiagnosticScreenshot() throws {
        // Auto-start presents initial weight setup; cancel to return to the idle workout screen.
        if app.buttons["Cancel"].waitForExistence(timeout: 10) {
            app.buttons["Cancel"].tap()
        }
        XCTAssertTrue(app.buttons["Start"].waitForExistence(timeout: 10))

        let leftHandCue = app.otherElements["workout.gripCue.left"]
        let rightHandCue = app.otherElements["workout.gripCue.right"]
        XCTAssertTrue(leftHandCue.waitForExistence(timeout: 10))
        XCTAssertTrue(rightHandCue.waitForExistence(timeout: 10))
        XCTAssertTrue(app.buttons["workout.gripCue.left.model"].exists)
        XCTAssertTrue(app.buttons["workout.gripCue.right.model"].exists)
        XCTAssertTrue(leftHandCue.label.contains("Exact fingers: index, middle, ring, and pinky"))
        XCTAssertTrue(rightHandCue.label.contains("Exact fingers: index, middle, ring, and pinky"))
        XCTAssertFalse(app.staticTexts["P+R+M+I"].exists)
        XCTAssertFalse(app.staticTexts["I+M+R+P"].exists)

        let attachment = XCTAttachment(screenshot: XCUIScreen.main.screenshot())
        attachment.name = "Diagnostic screenshot: Max Hangs step 1 landscape grip cues"
        attachment.lifetime = .keepAlways
        add(attachment)
    }

    func testLandscapePreStartHasNoLegacyLoadAdjustment() throws {
        selectManualWeightSourceIfNeeded()
        XCTAssertTrue(app.textFields["workout.initialWeight.manualField"].waitForExistence(timeout: 10))
        XCTAssertFalse(app.textFields["Workout load adjustment"].exists)
        XCTAssertTrue(app.switches["workout.initialWeight.addBodyweight"].exists)
        let attachment = XCTAttachment(screenshot: XCUIScreen.main.screenshot())
        attachment.name = "Manual initial weight setup in landscape"
        attachment.lifetime = .keepAlways
        add(attachment)
    }

    func testLandscapeManualWorkoutHidesStreamingSensorMeter() throws {
        app.terminate()
        app.launchEnvironment["HANGTEN_REVIEW_MOTHERBOARD"] = "1"
        app.launch()
        dismissSettingsReviewIfPresented()
        openWorkoutDeepLinkExpectingInitialWeightSetup()
        selectManualWeightSourceIfNeeded()

        XCTAssertTrue(app.buttons["workout.initialWeight.continue"].waitForExistence(timeout: 15))
        XCTAssertFalse(app.textFields["Workout load adjustment"].exists)
        app.buttons["workout.initialWeight.continue"].tap()
        XCTAssertTrue(app.buttons["handSide.left"].waitForExistence(timeout: 10))
        app.buttons["handSide.left"].tap()
        XCTAssertTrue(app.buttons["Pause"].waitForExistence(timeout: 20))
        XCTAssertFalse(app.otherElements["motherboard.forceRocker"].exists)
        XCTAssertFalse(app.buttons["Skip preparation"].exists)
    }

    /// Opens the workout deep link only after Train is the top of the stack, then
    /// retries once if the URL was dropped during a nav/orientation settle.
    private func openWorkoutDeepLinkExpectingInitialWeightSetup(
        perAttemptTimeout: TimeInterval = 20
    ) {
        waitForTrainShellReady(timeout: 20)
        let sourcePicker = app.segmentedControls["workout.initialWeight.sourcePicker"]
        app.open(workoutDeepLink)
        if sourcePicker.waitForExistence(timeout: perAttemptTimeout) {
            return
        }
        // Landscape + Settings pop can swallow the first openurl; Train is ready now.
        waitForTrainShellReady(timeout: 10)
        app.open(workoutDeepLink)
        XCTAssertTrue(
            sourcePicker.waitForExistence(timeout: perAttemptTimeout),
            "Initial weight setup source picker should appear after the workout deep link."
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
            trainBoard.exists || trainSettings.exists || app.tabBars.firstMatch.exists,
            "Train shell (train.board / train.settings / tab bar) should be ready before opening the workout deep link."
        )
    }

    private func selectManualWeightSourceIfNeeded() {
        let source = app.segmentedControls["workout.initialWeight.sourcePicker"]
        let manual = source.buttons["Manual"]
        guard manual.exists, !manual.isSelected else { return }
        manual.tap()
    }

    private func dismissSettingsReviewIfPresented() {
        // HANGTEN_REVIEW_MOTHERBOARD still opens Settings from Train; dismiss so the
        // workout deep link can present on the Train stack.
        let settings = app.navigationBars["Settings"]
        guard settings.waitForExistence(timeout: 8) else { return }
        settings.buttons.firstMatch.tap()

        let dismissed = XCTNSPredicateExpectation(
            predicate: NSPredicate(format: "exists == false"),
            object: settings
        )
        let result = XCTWaiter.wait(for: [dismissed], timeout: 10)
        XCTAssertEqual(
            result,
            .completed,
            "Settings should finish dismissing before the workout deep link."
        )
    }
}

final class InitialWeightSetupUITests: XCTestCase {
    private let app = XCUIApplication()
    private let workoutDeepLink = URL(string: "hangten://plan/research.max-hangs/workout")!

    override func setUpWithError() throws {
        continueAfterFailure = false
        app.launchEnvironment = [
            "HANGTEN_REVIEW_FREE_WORKOUTS_USED": "0",
            "HANGTEN_REVIEW_PORTRAIT": "1",
            "HANGTEN_REVIEW_MOTHERBOARD": "1",
            "HANGTEN_REVIEW_SENSOR_DISCONNECTED": "1",
        ]
        app.launch()
        if app.navigationBars["Settings"].waitForExistence(timeout: 5) {
            app.navigationBars["Settings"].buttons.firstMatch.tap()
        }
        app.open(workoutDeepLink)
        XCTAssertTrue(app.segmentedControls["workout.initialWeight.sourcePicker"].waitForExistence(timeout: 15))
        if app.buttons["Turn off spoken cues"].exists { app.buttons["Turn off spoken cues"].tap() }
    }

    func testPairingCancelKeepsManualDraftAndAllowsRetry() {
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
        let source = app.segmentedControls["workout.initialWeight.sourcePicker"]
        source.buttons["Sensor"].tap()
        XCTAssertTrue(app.buttons["workout.sensorPairing.cancel"].waitForExistence(timeout: 10))
        let attachment = XCTAttachment(screenshot: XCUIScreen.main.screenshot())
        attachment.name = "Sensor pairing presented inside initial weight setup"
        attachment.lifetime = .keepAlways
        add(attachment)
        app.buttons["workout.sensorPairing.cancel"].tap()
        XCTAssertTrue(source.waitForExistence(timeout: 10))
        source.buttons["Manual"].tap()
        XCTAssertEqual(field.value as? String, enteredValue)
        XCTAssertEqual(app.switches["workout.initialWeight.addBodyweight"].value as? String, "1")
        source.buttons["Sensor"].tap()
        XCTAssertTrue(app.buttons["workout.sensorPairing.cancel"].waitForExistence(timeout: 10))
        app.buttons["workout.sensorPairing.cancel"].tap()
        app.buttons["workout.initialWeight.continue"].tap()
        XCTAssertTrue(app.buttons["workout.sensorPairing.connect"].waitForExistence(timeout: 10))
    }

    func testPairingStreamingDismissesSetupAndStartsOnceAfterPreparation() {
        app.segmentedControls["workout.initialWeight.sourcePicker"].buttons["Sensor"].tap()
        let connect = app.buttons["workout.sensorPairing.connect"]
        XCTAssertTrue(connect.waitForExistence(timeout: 10))
        connect.tap()
        XCTAssertTrue(app.buttons["handSide.left"].waitForExistence(timeout: 10))
        app.buttons["handSide.left"].tap()
        let skip = app.buttons["Skip preparation"]
        XCTAssertTrue(skip.waitForExistence(timeout: 15))
        XCTAssertFalse(app.buttons["workout.sensorPairing.connect"].exists)
        XCTAssertFalse(app.buttons["workout.initialWeight.continue"].exists)
        skip.tap()
        XCTAssertTrue(app.buttons["Pause"].waitForExistence(timeout: 20))
        XCTAssertTrue(app.otherElements["motherboard.forceRocker"].exists)
        app.buttons["Pause"].tap()
        XCTAssertTrue(app.buttons["Resume"].waitForExistence(timeout: 10))
        XCTAssertFalse(app.buttons["Start"].exists)
    }
}

final class DualMaxHangsHighlightUITests: XCTestCase {
    func testDualBoardExposesTheResolvedMaxHangHold() throws {
        let app = XCUIApplication()
        app.launchEnvironment = [
            "HANGTEN_REVIEW_BOARD_ID": "captain-fingerfood.dual",
            "HANGTEN_REVIEW_PLAN_ID": "research.max-hangs",
            "HANGTEN_REVIEW_WORKOUT": "1",
            "HANGTEN_REVIEW_FREE_WORKOUTS_USED": "0",
            "HANGTEN_REVIEW_STEP": "1",
        ]
        app.launch()

        let board = app.otherElements["boardModel.3d"]
        XCTAssertTrue(board.waitForExistence(timeout: 30))
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
