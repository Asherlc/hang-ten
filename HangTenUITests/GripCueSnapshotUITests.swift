import XCTest

final class DefaultGripFingersUITests: XCTestCase {
    func testPortraitWorkoutExposesOneCombinedGripCue() throws {
        let app = XCUIApplication()
        app.launchArguments = ["-workoutAudioCuesEnabled", "NO"]
        app.launchEnvironment = [
            "HANGTEN_REVIEW_BOARD_ID": "tension.honestone",
            "HANGTEN_REVIEW_PORTRAIT": "1",
            "HANGTEN_REVIEW_FREE_WORKOUTS_USED": "0",
        ]
        defer { app.terminate() }
        app.terminate()
        app.open(URL(string: "hangten://plan/research.max-hangs/workout")!)
        let pause = app.buttons["Pause"]
        XCTAssertTrue(pause.waitForExistence(timeout: 30))
        pause.tap()
        let cues = app.descendants(matching: .any).matching(identifier: "workout.gripCue.both")
        XCTAssertTrue(cues.firstMatch.waitForExistence(timeout: 10))
        XCTAssertEqual(cues.count, 1, cues.debugDescription)
        XCTAssertTrue(cues.firstMatch.label.contains("both hands"))
        XCTAssertTrue(cues.firstMatch.label.contains("Exact fingers: index, middle, ring, and pinky"))
        let attachment = XCTAttachment(screenshot: XCUIScreen.main.screenshot())
        attachment.name = "Portrait combined grip accessibility cue"
        attachment.lifetime = .keepAlways
        add(attachment)
    }

    func testUnspecifiedFingersRenderAssumedFourFingerHands() throws {
        let app = XCUIApplication()
        app.launchEnvironment = [
            "HANGTEN_REVIEW_GRIP_MODEL": "1",
            "HANGTEN_REVIEW_GRIP_POSE": "fourFingerPocket",
            "HANGTEN_REVIEW_GRIP_FINGERS": "",
        ]
        defer {
            app.terminate()
            XCUIDevice.shared.orientation = .portrait
        }
        app.launch()
        XCTAssertTrue(app.staticTexts["4 fingers (assumed)"].waitForExistence(timeout: 20))
        XCTAssertFalse(app.staticTexts["Fingers not specified"].exists)
        for orientation in [UIDeviceOrientation.portrait, .landscapeLeft] {
            XCUIDevice.shared.orientation = orientation
            let summary = app.staticTexts["gripModel.review.fingerSummary"]
            let expectedLayout = orientation == .portrait ? "portrait" : "landscape"
            let rotated = XCTNSPredicateExpectation(
                predicate: NSPredicate(format: "value == %@ AND hittable == true", expectedLayout),
                object: summary
            )
            XCTAssertEqual(XCTWaiter.wait(for: [rotated], timeout: 10), .completed)
            XCTAssertTrue(app.staticTexts["4 fingers (assumed)"].isHittable)
            let attachment = XCTAttachment(screenshot: XCUIScreen.main.screenshot())
            attachment.name = "Assumed four fingers \(orientation.rawValue)"
            attachment.lifetime = .keepAlways
            add(attachment)
        }
    }
}

final class GripCueDiagnosticScreenshotUITests: XCTestCase {
    private let app = XCUIApplication()
    private let workoutDeepLink = URL(string: "hangten://plan/research.max-hangs/workout")!

    override func setUpWithError() throws {
        continueAfterFailure = false
        // These tests assert visual and timer behavior rather than speech.
        app.launchArguments = ["-workoutAudioCuesEnabled", "NO"]
        app.launchEnvironment = [
            "HANGTEN_REVIEW_FREE_WORKOUTS_USED": "0",
            "HANGTEN_REVIEW_STEP": "1",
            "HANGTEN_REVIEW_LANDSCAPE": "1",
            // Keep this integration test independent from the board persisted
            // by earlier cases; DEBUG simulator builds bundle this native model.
            "HANGTEN_REVIEW_BOARD_ID": "tension.honestone",
        ]
    }

    func testContactOffsetTaskCanAdvanceWithoutSkippingMinute() throws {
        app.launchEnvironment["HANGTEN_REVIEW_STEP"] = "9"
        app.launchEnvironment.removeValue(forKey: "HANGTEN_REVIEW_LANDSCAPE")
        openWorkout(URL(string: "hangten://plan/metolius.contact.entry/workout")!)
        // This route auto-starts after renderer preparation and its countdown.
        // A transient Start button can disappear before XCTest delivers a tap.
        XCTAssertTrue(app.buttons["Pause"].waitForExistence(timeout: 20))
        let next = app.buttons["workout.nextHold"]
        XCTAssertTrue(next.waitForExistence(timeout: 10))
        XCTAssertTrue(app.staticTexts["Hold 1 of 3"].exists)
        next.tap()
        XCTAssertTrue(app.staticTexts["Hold 2 of 3"].waitForExistence(timeout: 5))
        XCTAssertTrue(app.buttons["Pause"].exists)

        let attachment = XCTAttachment(screenshot: XCUIScreen.main.screenshot())
        attachment.name = "Contact offset task two, same running minute"
        attachment.lifetime = .keepAlways
        add(attachment)
    }

    func testTwoHandTaskOnMiniBarExplainsTwoBoards() throws {
        app.launchEnvironment["HANGTEN_REVIEW_BOARD_ID"] = "lattice.mini-bar"
        app.launchEnvironment["HANGTEN_REVIEW_STEP"] = "2"
        app.launchEnvironment.removeValue(forKey: "HANGTEN_REVIEW_LANDSCAPE")
        openWorkout(workoutDeepLink)
        XCTAssertTrue(
            app.staticTexts["Use two boards, one hand on each."].waitForExistence(timeout: 20)
        )
        let attachment = XCTAttachment(screenshot: XCUIScreen.main.screenshot())
        attachment.name = "Two hands on one-hand Mini Bar require two boards"
        attachment.lifetime = .keepAlways
        add(attachment)
    }

    func testOneArmTaskLetsAthleteChooseSide() throws {
        app.launchEnvironment["HANGTEN_REVIEW_STEP"] = "9"
        app.launchEnvironment["HANGTEN_REVIEW_PLAN_ID"] = "metolius.contact.intermediate"
        app.launchEnvironment.removeValue(forKey: "HANGTEN_REVIEW_LANDSCAPE")
        openWorkout(URL(string: "hangten://plan/metolius.contact.intermediate/workout")!)
        // Cold model preparation can take over a minute on CI. Wait through
        // preparation and the countdown, then freeze the minute for side selection.
        let primaryControl = app.buttons["workout.primaryControl"]
        let running = XCTNSPredicateExpectation(
            predicate: NSPredicate { _, _ in
                primaryControl.exists && primaryControl.label == "Pause"
            },
            object: nil
        )
        XCTAssertEqual(XCTWaiter.wait(for: [running], timeout: 120), .completed)
        primaryControl.tap()
        let paused = XCTNSPredicateExpectation(
            predicate: NSPredicate(format: "label == %@", "Resume"),
            object: primaryControl
        )
        XCTAssertEqual(XCTWaiter.wait(for: [paused], timeout: 10), .completed)
        XCTAssertEqual(app.buttons["workout.routinePicker"].label, "Step 9 of 10")
        let rightHand = app.buttons["workout.taskHand.right"]
        XCTAssertTrue(rightHand.waitForExistence(timeout: 20))
        rightHand.tap()
        XCTAssertTrue(app.staticTexts["Hold 1 of 3"].exists)
        XCTAssertTrue(app.staticTexts["Hang • Right hand"].exists)
        let attachment = XCTAttachment(screenshot: XCUIScreen.main.screenshot())
        attachment.name = "One arm Contact sloper on chosen right side"
        attachment.lifetime = .keepAlways
        add(attachment)
    }

    func testMaxHangsDeepLinkDefaultsToUntrackedAndAutoStarts() throws {
        openWorkoutDeepLinkAndChooseLeftHandIfNeeded()
        XCTAssertFalse(app.segmentedControls["workout.initialWeight.sourcePicker"].exists)
        XCTAssertFalse(app.buttons["Start"].exists)
        XCTAssertTrue(app.buttons["Pause"].waitForExistence(timeout: 20))

        let skip = app.buttons["workout.skipStep"]
        XCTAssertTrue(skip.isHittable)
        XCTAssertLessThanOrEqual(skip.frame.maxY, app.frame.maxY,
                                 "The landscape hand previews must leave Skip fully onscreen")

        let leftHandCue = app.otherElements["workout.gripCue.left"]
        XCTAssertTrue(leftHandCue.waitForExistence(timeout: 10))
        XCTAssertFalse(app.buttons["workout.gripCue.left.model"].exists)
        XCTAssertFalse(app.buttons["workout.gripCue.right.model"].exists)
        XCTAssertTrue(leftHandCue.label.contains("Exact fingers: index, middle, ring, and pinky"))
        XCTAssertFalse(app.staticTexts["P+R+M+I"].exists)
        XCTAssertFalse(app.staticTexts["I+M+R+P"].exists)

        let attachment = XCTAttachment(screenshot: XCUIScreen.main.screenshot())
        attachment.name = "Diagnostic screenshot: Max Hangs step 1 landscape grip cues"
        attachment.lifetime = .keepAlways
        add(attachment)
    }

    func testPublishedLongHangStopwatchRunsBeyondEstimateWithRoutinePaused() throws {
        app.launchEnvironment = [
            "HANGTEN_REVIEW_FREE_WORKOUTS_USED": "0",
            "HANGTEN_REVIEW_BOARD_ID": "metolius.wood-grips-compact-ii",
            "HANGTEN_REVIEW_LANDSCAPE": "1"
        ]
        openWorkout(URL(string: "hangten://plan/tension-long-hangs/workout")!)
        let pause = app.buttons["Pause"]
        XCTAssertTrue(pause.waitForExistence(timeout: 20))
        pause.tap()
        // SwiftUI propagates the containing stopwatch identifier to the button.
        let stopwatch = app.buttons["workout.stopwatch"]
        XCTAssertTrue(stopwatch.waitForExistence(timeout: 10))
        XCTAssertEqual(stopwatch.label, "Start stopwatch")
        stopwatch.tap()
        let stopwatchRunning = XCTNSPredicateExpectation(
            predicate: NSPredicate(format: "label == %@", "Stop stopwatch"),
            object: stopwatch
        )
        XCTAssertEqual(XCTWaiter.wait(for: [stopwatchRunning], timeout: 10), .completed)
        let stopwatchElapsed = app.staticTexts.matching(identifier: "workout.stopwatch").firstMatch
        let beyondEstimate = XCTNSPredicateExpectation(
            predicate: NSPredicate { object, _ in
                guard let element = object as? XCUIElement, element.exists else { return false }
                let components = element.label.split(separator: ":")
                guard components.count == 2,
                      let minutes = Int(components[0]),
                      let seconds = Int(components[1]) else { return false }
                return minutes * 60 + seconds >= 16
            },
            object: stopwatchElapsed
        )
        XCTAssertEqual(
            XCTWaiter.wait(for: [beyondEstimate], timeout: 30), .completed,
            "The independent stopwatch must visibly exceed the 15-second estimate."
        )
        XCTAssertTrue(app.buttons["Resume"].exists)
        XCTAssertEqual(stopwatch.label, "Stop stopwatch")
        XCTAssertTrue(app.staticTexts["Long hang 1 of 3"].exists)
        let image = XCTAttachment(screenshot: XCUIScreen.main.screenshot())
        image.name = "Published Tension long hang beyond 15-second estimate"
        image.lifetime = .keepAlways
        add(image)
        stopwatch.tap()
        app.buttons["workout.skipStep"].tap()
        XCTAssertTrue(app.staticTexts["Rest"].waitForExistence(timeout: 10))
    }

    func testPublishedPresetVisualCheckpoints() throws {
        let cases = [
            ("tension-6-and-10", "metolius.wood-grips-compact-ii", "1", "Tension matched edge and half-crimp cue"),
            ("cameron-horst-one-arm", "metolius.wood-grips-compact-ii", "1", "Cameron Horst single-hand strength cue"),
            ("rock-prodigy.rptc-intermediate", "trango.rock-prodigy-training-center", "1", "RPTC warm-up jug highlight"),
            ("rock-prodigy.pivot-intermediate", "trango.rock-prodigy-pivot", "1", "Pivot manual orientation instruction")
        ]
        for (index, reviewCase) in cases.enumerated() {
            let (plan, board, step, name) = reviewCase
            // One plan still exercises the speaker toggle; the remaining
            // screenshots can skip audio preparation and repeated toggle taps.
            app.launchArguments = index == 0 ? [] : ["-workoutAudioCuesEnabled", "NO"]
            app.launchEnvironment = [
                "HANGTEN_REVIEW_FREE_WORKOUTS_USED": "0", "HANGTEN_REVIEW_BOARD_ID": board,
                "HANGTEN_REVIEW_LANDSCAPE": "1", "HANGTEN_REVIEW_STEP": step
            ]
            openWorkout(URL(string: "hangten://plan/\(plan)/workout")!)
            let pause = app.buttons["Pause"]
            XCTAssertTrue(pause.waitForExistence(timeout: 20), plan)
            pause.tap()
            XCTAssertTrue(app.buttons["Resume"].waitForExistence(timeout: 10), plan)
            if index == 0 {
                let speaker = app.buttons["workout.spokenCues"]
                XCTAssertTrue(speaker.waitForExistence(timeout: 5))
                let initialLabel = speaker.label
                guard initialLabel == "Turn off spoken cues"
                        || initialLabel == "Turn on spoken cues" else {
                    XCTFail("The spoken-cues control must expose its current action.")
                    return
                }
                speaker.tap()
                XCTAssertNotEqual(speaker.label, initialLabel)
                speaker.tap()
                XCTAssertEqual(speaker.label, initialLabel)
            }
            let image = XCTAttachment(screenshot: XCUIScreen.main.screenshot())
            image.name = name
            image.lifetime = .keepAlways
            add(image)
        }
        app.terminate()
        app.launchEnvironment = [
            "HANGTEN_REVIEW_FREE_WORKOUTS_USED": "0", "HANGTEN_REVIEW_BOARD_ID": "trango.rock-prodigy-pivot",
            "HANGTEN_REVIEW_PORTRAIT": "1", "HANGTEN_REVIEW_PLAN": "1",
            "HANGTEN_REVIEW_PLAN_ID": "rock-prodigy.pivot-introductory"
        ]
        app.launch()
        XCTAssertTrue(app.otherElements["plan.initialWeight.setup"].waitForExistence(timeout: 20))
        let detail = XCTAttachment(screenshot: XCUIScreen.main.screenshot())
        detail.name = "Pivot introductory plan detail"
        detail.lifetime = .keepAlways
        add(detail)
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

    func testWorkoutPauseSurvivesRotationAndResumes() {
        defer { XCUIDevice.shared.orientation = .portrait }
        app.launchEnvironment.removeValue(forKey: "HANGTEN_REVIEW_LANDSCAPE")
        // This test covers the clock and navigation, independently of the
        // simulator's audio service and speech playback (disabled in setUp).
        openWorkoutDeepLinkAndChooseLeftHandIfNeeded(orientation: .landscapeLeft)
        let landscapeLayout = XCTNSPredicateExpectation(
            predicate: NSPredicate { _, _ in
                let frame = self.app.windows.firstMatch.frame
                return frame.width > frame.height
            },
            object: nil
        )
        XCTAssertEqual(XCTWaiter.wait(for: [landscapeLayout], timeout: 10), .completed)
        app.buttons["Pause"].tap()
        XCTAssertTrue(app.buttons["Resume"].waitForExistence(timeout: 10))
        let timer = app.staticTexts["workout.timer"]
        XCTAssertTrue(timer.exists)
        let pausedTime = timer.label
        let landscape = XCTAttachment(screenshot: XCUIScreen.main.screenshot())
        landscape.name = "Paused workout landscape"
        landscape.lifetime = .keepAlways
        add(landscape)

        XCUIDevice.shared.orientation = .portrait
        let portrait = XCTNSPredicateExpectation(
            predicate: NSPredicate { _, _ in
                let frame = self.app.windows.firstMatch.frame
                return frame.height > frame.width
            },
            object: nil
        )
        XCTAssertEqual(XCTWaiter.wait(for: [portrait], timeout: 10), .completed)
        XCTAssertTrue(app.buttons["Resume"].waitForExistence(timeout: 10))
        XCTAssertEqual(timer.label, pausedTime, "Rotation must preserve the paused clock")
        let portraitScreenshot = XCTAttachment(screenshot: XCUIScreen.main.screenshot())
        portraitScreenshot.name = "Paused workout portrait"
        portraitScreenshot.lifetime = .keepAlways
        add(portraitScreenshot)

        let skip = app.buttons["workout.skipStep"]
        if skip.label != "Skip step 1: Max hang · set 1" {
            app.buttons["workout.routinePicker"].tap()
            let firstStep = app.buttons.matching(NSPredicate(
                format: "identifier BEGINSWITH %@ AND label BEGINSWITH %@",
                "workout.step.", "Step 1, "
            )).firstMatch
            XCTAssertTrue(firstStep.waitForExistence(timeout: 10))
            firstStep.tap()
        }
        XCTAssertEqual(skip.label, "Skip step 1: Max hang · set 1")
        XCTAssertTrue(skip.isEnabled)
        // Keep the work step paused until the skip. Slow CI queries after
        // resuming can otherwise let its ten-second hang reach rest first.
        skip.tap()
        // Entering a rest step is immediate; the next work step gets a countdown.
        let restStep = XCTNSPredicateExpectation(
            predicate: NSPredicate(format: "label == %@", "Skip step 2: Rest"),
            object: skip
        )
        XCTAssertEqual(XCTWaiter.wait(for: [restStep], timeout: 5), .completed)
        XCTAssertTrue(app.buttons["Resume"].exists, "Skipping to rest preserves the paused clock")
        app.buttons["Resume"].tap()
        XCTAssertTrue(app.buttons["Pause"].waitForExistence(timeout: 10))
        skip.tap()
        XCTAssertTrue(app.buttons["Cancel countdown"].waitForExistence(timeout: 5))
        // The countdown can finish between the existence query and the tap.
        // Its primary control keeps this identifier when its label becomes Pause.
        app.buttons["workout.primaryControl"].tap()
        XCTAssertTrue(app.buttons["Resume"].waitForExistence(timeout: 10))
        XCTAssertEqual(skip.label, "Skip step 3: Max hang · set 2")

        let cancelledCountdown = XCTAttachment(screenshot: XCUIScreen.main.screenshot())
        cancelledCountdown.name = "Next work step paused after skipping rest"
        cancelledCountdown.lifetime = .keepAlways
        add(cancelledCountdown)
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

    /// A cold URL launch starts on Train without a preceding navigation transition.
    private func openWorkout(_ url: URL, orientation: UIDeviceOrientation? = nil) {
        // Fixture launch arguments and environment must apply even if an earlier
        // test left this app running on the shared shard simulator.
        app.terminate()
        if let orientation {
            XCUIDevice.shared.orientation = orientation
        }
        app.open(url)
    }

    private func openWorkoutDeepLinkAndChooseLeftHandIfNeeded(
        timeout: TimeInterval = 20,
        orientation: UIDeviceOrientation? = nil
    ) {
        let handChoice = app.buttons["handSide.left"]
        let pause = app.buttons["Pause"]
        openWorkout(workoutDeepLink, orientation: orientation)
        let destination = app.buttons.matching(
            NSPredicate(format: "identifier == %@ OR label == %@", "handSide.left", "Pause")
        ).firstMatch
        XCTAssertTrue(destination.waitForExistence(timeout: timeout))
        if handChoice.exists {
            handChoice.tap()
        }
        XCTAssertTrue(pause.waitForExistence(timeout: timeout))
    }

    private func openPlanDetail(withMotherboardFixture: Bool = false) {
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

final class PendingWorkoutSummaryUITests: XCTestCase {
    func testPendingSummaryRequiresSaveOrConfirmedDiscard() {
        continueAfterFailure = false
        let app = XCUIApplication()
        app.launchEnvironment = [
            "HANGTEN_REVIEW_FREE_WORKOUTS_USED": "0",
            "HANGTEN_REVIEW_PORTRAIT": "1",
            "HANGTEN_REVIEW_PLAN": "1",
            "HANGTEN_REVIEW_PLAN_ID": "research.max-hangs",
            "HANGTEN_REVIEW_BOARD_ID": "tension.grindstone-original",
            "HANGTEN_REVIEW_STEP": "999",
        ]
        app.launch()
        let start = app.buttons["plan.startRoutine"]
        XCTAssertTrue(start.waitForExistence(timeout: 20))
        start.tap()

        let save = app.buttons["workout.summary.save"]
        let discard = app.buttons["workout.summary.discard"]
        XCTAssertTrue(save.waitForExistence(timeout: 20))
        let summaryCapture = XCTAttachment(screenshot: XCUIScreen.main.screenshot())
        summaryCapture.name = "Pending summary with persistent Save"
        summaryCapture.lifetime = .keepAlways
        add(summaryCapture)
        let summary = app.navigationBars["Summary"]
        summary.coordinate(withNormalizedOffset: CGVector(dx: 0.5, dy: 0.1))
            .press(forDuration: 0.05, thenDragTo:
                app.coordinate(withNormalizedOffset: CGVector(dx: 0.5, dy: 0.85)))
        XCTAssertTrue(save.isHittable, "Dragging must not dismiss an unsaved summary.")

        discard.tap()
        let confirmation = app.alerts["Discard this session?"]
        XCTAssertTrue(confirmation.waitForExistence(timeout: 5))
        let discardCapture = XCTAttachment(screenshot: XCUIScreen.main.screenshot())
        discardCapture.name = "Pending summary discard confirmation"
        discardCapture.lifetime = .keepAlways
        add(discardCapture)
        confirmation.buttons["Keep reviewing"].tap()
        XCTAssertTrue(save.isHittable)

        discard.tap()
        // SwiftUI alerts can expose both a proxy and its native child button.
        confirmation.buttons["Discard session"].firstMatch.tap()
        let dismissed = XCTNSPredicateExpectation(
            predicate: NSPredicate(format: "exists == false"), object: save
        )
        XCTAssertEqual(XCTWaiter.wait(for: [dismissed], timeout: 10), .completed)
    }
}

final class InitialWeightSetupUITests: XCTestCase {
    private let app = XCUIApplication()

    override func setUpWithError() throws {
        continueAfterFailure = false
        // These cases exercise plan setup and sensor routing, not speech.
        app.launchArguments = ["-workoutAudioCuesEnabled", "NO"]
        app.launchEnvironment = [
            "HANGTEN_REVIEW_FREE_WORKOUTS_USED": "0",
            "HANGTEN_REVIEW_PORTRAIT": "1",
            "HANGTEN_REVIEW_MOTHERBOARD": "1",
            "HANGTEN_REVIEW_SENSOR_DISCONNECTED": "1",
            "HANGTEN_REVIEW_PLAN": "1",
            "HANGTEN_REVIEW_PLAN_ID": "research.max-hangs",
            // Pin the board so earlier tests cannot change the weight-flow fixture.
            // Its native model is bundled in DEBUG simulator builds.
            "HANGTEN_REVIEW_BOARD_ID": "tension.grindstone-original",
        ]
        app.launch()
        XCTAssertTrue(
            app.otherElements["plan.initialWeight.setup"].waitForExistence(timeout: 15),
            "The plan review route should take precedence over fixture-only review flags."
        )
        XCTAssertTrue(app.staticTexts["Max Hangs"].waitForExistence(timeout: 10))
        XCTAssertTrue(app.staticTexts["Grindstone"].exists,
                      "The weight-flow fixture must resolve to the requested board.")
    }

    func testInlineChoicesKeepManualDraftAndExposeOneLabeledToggle() {
        let source = app.segmentedControls["workout.initialWeight.sourcePicker"]
        XCTAssertTrue(source.buttons["Skip"].isSelected)
        source.buttons["Manual"].tap()

        let bodyweight = app.switches["workout.initialWeight.addBodyweight"]
        XCTAssertNotNil(visibleControlCoordinate(bodyweight, in: app, requireHittable: false, timeout: 30))
        XCTAssertEqual(bodyweight.value as? String, "0")
        XCTAssertEqual(bodyweight.label, "Add bodyweight")
        XCTAssertEqual(app.switches.matching(identifier: "workout.initialWeight.addBodyweight").count, 1)
        XCTAssertFalse(app.buttons["workout.initialWeight.addBodyweight"].exists,
                       "The tappable row must expose only its switch accessibility representation.")
        XCTAssertFalse(app.buttons["workout.initialWeight.addBodyweight.label"].exists,
                       "Bodyweight should have one labeled toggle, without a duplicate button.")
        bodyweight.tap()
        let bodyweightEnabled = XCTNSPredicateExpectation(
            predicate: NSPredicate(format: "value == %@", "1"),
            object: bodyweight
        )
        XCTAssertEqual(XCTWaiter.wait(for: [bodyweightEnabled], timeout: 5), .completed,
                       "Manual tracking must add bodyweight when its switch is enabled")
        let field = app.textFields["workout.initialWeight.manualField"]
        XCTAssertTrue(field.waitForExistence(timeout: 10))
        // Read the draft before focusing; a hosted accessibility query can be slow.
        let draftCharacterCount = (field.value as? String)?.count ?? 0
        tapVisibleControl(field, in: app, requireHittable: false)
        let keyboard = app.keyboards.firstMatch
        if !keyboard.waitForExistence(timeout: 5) {
            tapVisibleControl(field, in: app, requireHittable: false)
        }
        XCTAssertTrue(keyboard.waitForExistence(timeout: 5),
                      "The manual weight field must show its keyboard before text entry")
        field.typeText(String(repeating: XCUIKeyboardKey.delete.rawValue, count: draftCharacterCount))
        field.typeText("12.5")
        let enteredWeight = XCTNSPredicateExpectation(
            predicate: NSPredicate(format: "value == %@", "12.5"), object: field
        )
        // A hosted accessibility query can consume most of a five-second wait.
        XCTAssertEqual(XCTWaiter.wait(for: [enteredWeight], timeout: 15), .completed)
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
        let manualAttachment = XCTAttachment(screenshot: XCUIScreen.main.screenshot())
        manualAttachment.name = "Final manual bodyweight setup"
        manualAttachment.lifetime = .keepAlways
        add(manualAttachment)
        bodyweight.tap()
        let bodyweightDisabled = XCTNSPredicateExpectation(
            predicate: NSPredicate(format: "value == %@", "0"),
            object: bodyweight
        )
        XCTAssertEqual(XCTWaiter.wait(for: [bodyweightDisabled], timeout: 5), .completed)
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
        // Navigation can retain the plan's accessibility elements behind the
        // preparation sheet. Its connection control must not be interactive.
        XCTAssertFalse(
            connect.isHittable,
            "The plan's connection button must not be interactive during preparation."
        )
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
    func testLopezEdgePickerChangesTheBeastmaker1000Preview() throws {
        let app = XCUIApplication()
        app.launchArguments = ["-workoutAudioCuesEnabled", "NO"]
        app.launchEnvironment = [
            "HANGTEN_REVIEW_BOARD_ID": "beastmaker-1000",
            "HANGTEN_REVIEW_PLAN_ID": "research.max-hangs",
            "HANGTEN_REVIEW_PLAN": "1",
            "HANGTEN_REVIEW_FREE_WORKOUTS_USED": "0"
        ]
        app.launch()
        XCTAssertTrue(app.navigationBars["Plan"].waitForExistence(timeout: 20))
        let picker = app.buttons["plan.maxHangs.edgePicker"]
        XCTAssertTrue(picker.waitForExistence(timeout: 10))
        picker.tap()
        app.buttons["15 mm"].tap()
        app.swipeUp()
        let board = app.otherElements["boardModel.3d"]
        XCTAssertTrue(board.waitForExistence(timeout: 60))
        let selectedHighlight = NSPredicate(format: "value CONTAINS[c] %@", "15 mm")
        expectation(for: selectedHighlight, evaluatedWith: board)
        waitForExpectations(timeout: 10)
        let attachment = XCTAttachment(screenshot: XCUIScreen.main.screenshot())
        attachment.name = "López MaxHangs selected 15 mm Beastmaker 1000 edges"
        attachment.lifetime = .keepAlways
        add(attachment)

        let start = app.buttons["plan.startRoutine"]
        XCTAssertTrue(start.waitForExistence(timeout: 10))
        // Scrolling to the preview can leave Start behind the navigation bar
        // even when XCTest reports it as hittable. Keep the whole button
        // between the navigation and tab bars before synthesizing the tap.
        let navigationBar = app.navigationBars["Plan"]
        let tabBar = app.tabBars.firstMatch
        func contentBottom() -> CGFloat {
            tabBar.exists ? min(tabBar.frame.minY, app.frame.maxY) : app.frame.maxY
        }
        func isStartVisible() -> Bool {
            let frame = start.frame
            return start.isHittable
                && frame.minY >= navigationBar.frame.maxY
                && frame.maxY <= contentBottom()
        }
        var remainingScrollAttempts = 8
        while !isStartVisible(), remainingScrollAttempts > 0 {
            let viewport = app.frame
            let contentTop = navigationBar.frame.maxY
            let origin = app.coordinate(withNormalizedOffset: .zero).withOffset(
                CGVector(dx: viewport.width / 2,
                         dy: (contentTop + contentBottom()) / 2 - viewport.minY)
            )
            let scrollDelta: CGFloat = start.frame.minY < contentTop ? 100 : -100
            origin.press(forDuration: 0.05, thenDragTo: origin.withOffset(CGVector(dx: 0, dy: scrollDelta)))
            remainingScrollAttempts -= 1
        }
        guard isStartVisible() else {
            XCTFail("Start must be visible between the navigation and tab bars; frame=\(start.frame)")
            return
        }
        tapVisibleControl(start, in: app)
        let pause = app.buttons["Pause"]
        XCTAssertTrue(pause.waitForExistence(timeout: 20))
        pause.tap()
        let workoutBoard = app.otherElements["boardModel.3d"]
        XCTAssertTrue(workoutBoard.waitForExistence(timeout: 60))
        expectation(for: selectedHighlight, evaluatedWith: workoutBoard)
        waitForExpectations(timeout: 10)
    }

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
        /// Sets up the test environment for one-handed board hand choice tests.
        continueAfterFailure = false
        app.launchArguments = ["-workoutAudioCuesEnabled", "NO"]
        app.launchEnvironment = [
            // Use a real capacity-1 raster board with a 20 mm edge. This
            // hand-choice test does not need asynchronous 3D preview rendering.
            "HANGTEN_REVIEW_BOARD_ID": "frictitious.nug",
            "HANGTEN_REVIEW_PLAN_ID": "research.max-hangs",
            "HANGTEN_REVIEW_PLAN": "1",
            "HANGTEN_REVIEW_PORTRAIT": "1",
            "HANGTEN_REVIEW_FREE_WORKOUTS_USED": "0",
        ]
        app.launch()
    }

    /// A two-hand source task on a one-hand board requires two boards.
    func testTwoHandTaskOnOneHandedBoardRequiresTwoBoards() throws {
        XCTAssertTrue(
            app.navigationBars["Plan"].waitForExistence(timeout: 20),
            "DEBUG plan-detail review route should open Max Hangs on the one-handed Nug board."
        )
        XCTAssertTrue(app.staticTexts["The NUG"].exists, "The hand-choice fixture must resolve to the Nug board.")

        selectManualWeightSourceIfNeeded()
        tapStartRoutine()

        XCTAssertTrue(
            app.staticTexts["Use two boards, one hand on each."].waitForExistence(timeout: 20)
        )
        XCTAssertFalse(
            app.buttons["workout.handPicker"].exists,
            "Explicit two-hand task targets do not need a separate session hand choice."
        )
        XCTAssertTrue(app.buttons["Pause"].waitForExistence(timeout: 20))
        XCTAssertFalse(app.buttons["workout.handPicker"].exists)
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

extension XCTestCase {
    /// Tap a measured screen position without resolving the control's window again.
    /// SwiftUI menus and switches can expose finite control frames beneath
    /// invalid window containers on iOS 26. Use the owning application as the screen anchor
    /// so events target that application’s process.
    func tapVisibleControl(
        _ element: XCUIElement,
        in application: XCUIApplication,
        normalizedOffset: CGVector = CGVector(dx: 0.5, dy: 0.5),
        requireHittable: Bool = true,
        timeout: TimeInterval = 10,
        file: StaticString = #filePath,
        line: UInt = #line
    ) {
        visibleControlCoordinate(
            element, in: application, normalizedOffset: normalizedOffset, requireHittable: requireHittable,
            timeout: timeout, file: file, line: line
        )?.tap()
    }

    /// Validate a complete accessibility snapshot before applying the retry budget.
    /// A single hosted query can outlast that budget; a valid result is still ready.
    func visibleControlCoordinate(
        _ element: XCUIElement,
        in application: XCUIApplication,
        normalizedOffset: CGVector = CGVector(dx: 0.5, dy: 0.5),
        requireHittable: Bool = true,
        timeout: TimeInterval = 10,
        file: StaticString = #filePath,
        line: UInt = #line
    ) -> XCUICoordinate? {
        let screen = application
        let deadline = ProcessInfo.processInfo.systemUptime + timeout
        var lastFrame: CGRect?
        var lastViewport: CGRect?
        repeat {
            if element.exists, element.isEnabled, !requireHittable || element.isHittable {
                let frame = element.frame
                let viewport = screen.frame
                lastFrame = frame
                lastViewport = viewport
                if frame.minX.isFinite, frame.minY.isFinite,
                   frame.width.isFinite, frame.height.isFinite,
                   frame.width > 0, frame.height > 0,
                   viewport.minX.isFinite, viewport.minY.isFinite,
                   viewport.width.isFinite, viewport.height.isFinite,
                   viewport.width > 0, viewport.height > 0 {
                    let point = CGPoint(
                        x: frame.minX + frame.width * normalizedOffset.dx,
                        y: frame.minY + frame.height * normalizedOffset.dy
                    )
                    if viewport.contains(point) {
                        let offset = CGVector(dx: point.x - viewport.minX, dy: point.y - viewport.minY)
                        return screen.coordinate(withNormalizedOffset: .zero).withOffset(offset)
                    }
                }
            }
            if ProcessInfo.processInfo.systemUptime >= deadline { break }
            Thread.sleep(forTimeInterval: 0.1)
        } while true
        XCTFail("Control must have a finite, visible frame; control=\(String(describing: lastFrame)), screen=\(String(describing: lastViewport))", file: file, line: line)
        return nil
    }
}

final class BoardPickerUITests: XCTestCase {
    func testKnownBoardSearchFavoritesAndSpecsKeepSelectionDistinct() {
        continueAfterFailure = false
        let app = XCUIApplication()
        app.launchArguments = ["-favoriteBoardIDs", "()", "-workoutAudioCuesEnabled", "NO"]
        app.launchEnvironment = [
            "HANGTEN_REVIEW_BOARD_PICKER": "1",
            "HANGTEN_REVIEW_PORTRAIT": "1",
            "HANGTEN_REVIEW_BOARD_ID": "tension.honestone",
            "HANGTEN_REVIEW_FREE_WORKOUTS_USED": "0",
        ]
        app.launch()
        let picker = app.navigationBars["Choose board"]
        XCTAssertTrue(picker.waitForExistence(timeout: 20))
        let favorite = app.buttons["boardPicker.favorite.beastmaker-1000"]
        XCTAssertTrue(favorite.waitForExistence(timeout: 10))
        favorite.tap()
        XCTAssertTrue(picker.isHittable, "Starring a board must not select or dismiss it.")

        let manufacturer = app.buttons["boardPicker.manufacturerFilter"]
        manufacturer.tap()
        let beastmaker = app.buttons["Beastmaker"].firstMatch
        XCTAssertTrue(beastmaker.waitForExistence(timeout: 10))
        beastmaker.tap()
        XCTAssertEqual(app.buttons.matching(NSPredicate(format: "identifier BEGINSWITH %@", "boardPicker.board.")).count, 2)

        let scope = app.segmentedControls["boardPicker.scope"]
        scope.buttons["Favorites"].tap()
        let board = app.buttons["boardPicker.board.beastmaker-1000"]
        XCTAssertTrue(board.waitForExistence(timeout: 10))
        XCTAssertEqual(app.buttons.matching(NSPredicate(format: "identifier BEGINSWITH %@", "boardPicker.board.")).count, 1)

        let specs = app.buttons["boardPicker.holdSpecs.beastmaker-1000"]
        XCTAssertTrue(specs.waitForExistence(timeout: 10))
        specs.tap()
        let details = app.navigationBars["Hold specs"]
        XCTAssertTrue(details.waitForExistence(timeout: 10))
        XCTAssertTrue(app.staticTexts["Beastmaker 1000"].exists)
        details.buttons.firstMatch.tap()
        XCTAssertTrue(picker.waitForExistence(timeout: 10))

        favorite.tap()
        XCTAssertTrue(app.staticTexts["No matching favorites"].waitForExistence(timeout: 10))
        app.buttons["boardPicker.clearFilters"].tap()
        XCTAssertTrue(scope.buttons["All boards"].isSelected)
        XCTAssertEqual(manufacturer.value as? String, "All manufacturers")
        let search = app.searchFields.firstMatch
        search.tap()
        search.typeText("beastmaker 1000")
        XCTAssertTrue(board.waitForExistence(timeout: 10))
        XCTAssertEqual(app.buttons.matching(NSPredicate(format: "identifier BEGINSWITH %@", "boardPicker.board.")).count, 1)
        specs.tap()
        XCTAssertTrue(details.waitForExistence(timeout: 10))
        XCTAssertFalse(app.keyboards.firstMatch.exists, "Inspecting a search result must dismiss its keyboard.")
        details.buttons.firstMatch.tap()
        XCTAssertTrue(picker.waitForExistence(timeout: 10))
        XCTAssertTrue(board.waitForExistence(timeout: 10))
        search.tap()
        XCTAssertTrue(app.keyboards.firstMatch.waitForExistence(timeout: 5))
        board.tap()
        XCTAssertTrue(app.navigationBars["Train"].waitForExistence(timeout: 10))
        XCTAssertTrue(app.staticTexts["Beastmaker 1000"].exists)
        XCTAssertFalse(app.keyboards.firstMatch.exists, "Selecting a search result must dismiss its keyboard.")
    }
}
