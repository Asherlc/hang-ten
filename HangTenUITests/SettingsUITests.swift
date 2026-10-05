import XCTest

final class SettingsUITests: XCTestCase {
    func testUnitsAreConfiguredFromMainSettings() throws {
        let app = XCUIApplication()
        app.launch()

        let settings = app.buttons["train.settings"]
        XCTAssertTrue(settings.waitForExistence(timeout: 10))
        settings.tap()

        XCTAssertTrue(app.staticTexts["UNITS"].waitForExistence(timeout: 5))
        XCTAssertTrue(app.segmentedControls["settings.forceUnit"].exists)
        XCTAssertTrue(app.segmentedControls["settings.loadAdjustmentUnit"].exists)

        app.buttons["settings.sensor"].tap()
        XCTAssertTrue(app.navigationBars["Sensor settings"].waitForExistence(timeout: 5))
        XCTAssertFalse(app.segmentedControls["settings.forceUnit"].exists)
        XCTAssertFalse(app.segmentedControls["settings.loadAdjustmentUnit"].exists)
    }

    func testPlansPageDoesNotShowLearnMoreCard() {
        let app = XCUIApplication()
        app.launchEnvironment["HANGTEN_REVIEW_PLANS"] = "1"
        app.launch()

        XCTAssertTrue(app.navigationBars["Plans"].waitForExistence(timeout: 10))
        XCTAssertFalse(app.staticTexts["Learn more"].exists)
        XCTAssertFalse(app.staticTexts["Each routine includes its source link."].exists)
        XCTAssertFalse(app.staticTexts["Read the evidence overview"].exists)
    }
}

final class WorkoutChooserUITests: XCTestCase {
    override func setUpWithError() throws {
        continueAfterFailure = false
    }

    func testBrowseFocusAndReturnFromDetails() {
        let app = launchChooser()
        XCTAssertTrue(element(app, "plans.changeBoard").waitForExistence(timeout: 10))
        XCTAssertTrue(element(app, "customRoutine.create").exists)
        XCTAssertFalse(element(app, "workouts.focus.pullingStrength").exists)
        capture(app, name: "Chooser browse")

        element(app, "workouts.focus.mixed").tap()
        XCTAssertTrue(app.navigationBars["Mixed workouts"].waitForExistence(timeout: 5))
        let row = element(app, "workouts.row.metolius.generic-ten-minute.entry")
        XCTAssertTrue(row.waitForExistence(timeout: 5))
        capture(app, name: "Chooser results")
        row.tap()
        XCTAssertTrue(element(app, "plan.startRoutine").waitForExistence(timeout: 10))
        app.navigationBars.buttons.element(boundBy: 0).tap()
        XCTAssertTrue(app.navigationBars["Mixed workouts"].waitForExistence(timeout: 5))
        XCTAssertTrue(row.exists)
    }

    func testFiltersApplyTogetherCancelAndClearPreserveFocus() {
        let app = launchChooser()
        element(app, "workouts.focus.mixed").tap()
        element(app, "workouts.filter").tap()
        XCTAssertTrue(element(app, "workouts.filter.cancel").waitForExistence(timeout: 5))
        element(app, "workouts.filter.option.Under 10 minutes").tap()
        element(app, "workouts.filter.cancel").tap()
        XCTAssertFalse(element(app, "workouts.removeFilter.Under 10 minutes").exists)

        element(app, "workouts.filter").tap()
        element(app, "workouts.filter.option.10–under 20 minutes").tap()
        element(app, "workouts.filter.option.Pull-ups").tap()
        capture(app, name: "Chooser filters")
        element(app, "workouts.filter.apply").tap()
        XCTAssertTrue(element(app, "workouts.removeFilter.10–under 20 minutes").waitForExistence(timeout: 5))
        XCTAssertTrue(element(app, "workouts.removeFilter.Pull-ups").exists)
        XCTAssertTrue(element(app, "workouts.row.metolius.generic-ten-minute.entry").exists)
        app.buttons["Clear all"].tap()
        XCTAssertFalse(element(app, "workouts.removeFilter.Pull-ups").exists)
        XCTAssertTrue(app.navigationBars["Mixed workouts"].exists)
    }

    func testSearchFindsWorkoutsAndShowsEmptyState() {
        let app = launchChooser()
        element(app, "workouts.all").tap()
        let search = app.searchFields.firstMatch
        XCTAssertTrue(search.waitForExistence(timeout: 5))
        search.tap()
        search.typeText("Metolius")
        XCTAssertTrue(element(app, "workouts.row.metolius.generic-ten-minute.entry").waitForExistence(timeout: 5))
        search.buttons["Clear text"].tap()
        search.typeText("zzzznomatchingworkout")
        XCTAssertTrue(app.staticTexts["No matching workouts"].waitForExistence(timeout: 5))
    }

    func testBoardSelectionCreationAndFavoritesRemainAvailable() {
        let app = launchChooser()
        element(app, "plans.changeBoard").tap()
        XCTAssertTrue(app.navigationBars["Choose board"].waitForExistence(timeout: 5))
        let board = app.buttons.matching(NSPredicate(format: "identifier BEGINSWITH %@", "boardPicker.board.")).firstMatch
        XCTAssertTrue(board.waitForExistence(timeout: 5))
        board.tap()
        XCTAssertTrue(app.navigationBars["Plans"].waitForExistence(timeout: 5))

        element(app, "customRoutine.create").tap()
        XCTAssertTrue(app.navigationBars["Create routine"].waitForExistence(timeout: 5))
        XCTAssertTrue(element(app, "customRoutine.name").exists)
        app.buttons["Cancel"].tap()
        element(app, "workouts.all").tap()
        let add = app.buttons["Add Metolius 10-minute · Entry to favorites"]
        let remove = app.buttons["Remove Metolius 10-minute · Entry from favorites"]
        if remove.exists { remove.tap() }
        XCTAssertTrue(add.waitForExistence(timeout: 5))
        add.tap()
        XCTAssertTrue(remove.waitForExistence(timeout: 5))
        XCTAssertTrue(element(app, "workouts.row.metolius.generic-ten-minute.entry").exists)
        remove.tap()
    }

    func testEmptyMyRoutinesOffersCreation() {
        let app = launchChooser()
        let myRoutines = element(app, "workouts.myRoutines")
        scrollToReach(myRoutines, in: app)
        myRoutines.tap()
        XCTAssertTrue(app.navigationBars["My routines"].waitForExistence(timeout: 5))
        XCTAssertTrue(app.staticTexts["Create your first routine"].waitForExistence(timeout: 5))
        XCTAssertFalse(app.staticTexts["No matching workouts"].exists)
        let create = element(app, "customRoutine.create")
        scrollToReach(create, in: app)
        create.tap()
        XCTAssertTrue(app.navigationBars["Create routine"].waitForExistence(timeout: 5))
        XCTAssertTrue(element(app, "customRoutine.name").exists)
    }

    func testAccessibilityTextSizeKeepsFavoriteAndFiltersUsable() {
        let app = launchChooser(accessibilityTextSize: true)
        let allWorkouts = element(app, "workouts.all")
        scrollToReach(allWorkouts, in: app)
        allWorkouts.tap()
        XCTAssertTrue(app.navigationBars["All workouts"].waitForExistence(timeout: 5))

        let add = app.buttons["Add Metolius 10-minute · Entry to favorites"]
        let remove = app.buttons["Remove Metolius 10-minute · Entry from favorites"]
        if remove.exists {
            scrollToReach(remove, in: app)
            remove.tap()
        }
        scrollToReach(add, in: app)
        add.tap()
        XCTAssertTrue(remove.waitForExistence(timeout: 5))
        XCTAssertFalse(element(app, "plan.startRoutine").exists)
        capture(app, name: "Chooser accessibility text favorite")
        remove.tap()

        let filter = element(app, "workouts.filter")
        XCTAssertTrue(filter.isHittable)
        filter.tap()
        XCTAssertTrue(element(app, "workouts.filter.cancel").waitForExistence(timeout: 5))
        let duration = element(app, "workouts.filter.option.10–under 20 minutes")
        scrollToReach(duration, in: app)
        duration.tap()
        let apply = element(app, "workouts.filter.apply")
        XCTAssertTrue(apply.isHittable)
        capture(app, name: "Chooser accessibility text filters")
        apply.tap()
        XCTAssertTrue(element(app, "workouts.removeFilter.10–under 20 minutes").waitForExistence(timeout: 5))
    }

    private func scrollToReach(_ target: XCUIElement, in app: XCUIApplication) {
        for _ in 0..<8 {
            if target.exists && target.isHittable { break }
            app.swipeUp()
        }
        XCTAssertTrue(target.exists && target.isHittable)
    }

    private func launchChooser(accessibilityTextSize: Bool = false) -> XCUIApplication {
        let app = XCUIApplication()
        app.launchEnvironment["HANGTEN_REVIEW_PLANS"] = "1"
        app.launchEnvironment["HANGTEN_REVIEW_BOARD_ID"] = "metolius.wood-grips-compact-ii"
        if accessibilityTextSize {
            app.launchArguments += ["-UIPreferredContentSizeCategoryName", "UICTContentSizeCategoryAccessibilityXXXL"]
        }
        app.launch()
        XCTAssertTrue(app.navigationBars["Plans"].waitForExistence(timeout: 15))
        return app
    }

    private func element(_ app: XCUIApplication, _ identifier: String) -> XCUIElement {
        app.descendants(matching: .any).matching(identifier: identifier).firstMatch
    }

    private func capture(_ app: XCUIApplication, name: String) {
        let attachment = XCTAttachment(screenshot: app.screenshot())
        attachment.name = name
        attachment.lifetime = .keepAlways
        add(attachment)
    }
}
