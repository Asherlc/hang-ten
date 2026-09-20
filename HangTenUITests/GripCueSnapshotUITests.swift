import XCTest

final class GripCueDiagnosticScreenshotUITests: XCTestCase {
    private let app = XCUIApplication()

    override func setUpWithError() throws {
        continueAfterFailure = false
        app.launchEnvironment = [
            "HANGTEN_REVIEW_PLAN_ID": "research.max-hangs",
            "HANGTEN_REVIEW_WORKOUT": "1",
            "HANGTEN_REVIEW_FREE_WORKOUTS_USED": "0",
            "HANGTEN_REVIEW_STEP": "1",
            "HANGTEN_REVIEW_LANDSCAPE": "1",
        ]
        app.launch()
    }

    func testMaxHangsStepOneExposesIndividualHandCuesAndCapturesDiagnosticScreenshot() throws {
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

    func testLandscapePreStartLoadAdjustmentShowsOnlyFieldAndUnit() throws {
        let loadAdjustment = app.textFields["Workout load adjustment"]

        XCTAssertTrue(loadAdjustment.waitForExistence(timeout: 10))
        XCTAssertTrue(app.staticTexts["lb"].exists || app.staticTexts["kg"].exists)
        XCTAssertFalse(app.staticTexts["Load"].exists)
    }

    func testLandscapePreStartLoadAdjustmentIsDisabledWhileScaleStreams() throws {
        app.terminate()
        app.launchEnvironment["HANGTEN_REVIEW_MOTHERBOARD"] = "1"
        app.launch()

        let loadAdjustment = app.textFields["Workout load adjustment"]
        XCTAssertTrue(loadAdjustment.waitForExistence(timeout: 10))
        XCTAssertFalse(loadAdjustment.isEnabled)
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
