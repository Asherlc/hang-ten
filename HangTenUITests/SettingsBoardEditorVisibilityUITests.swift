import XCTest

final class SettingsBoardEditorVisibilityUITests: XCTestCase {
    func testPlansPageDoesNotShowLearnMoreCard() {
        let app = XCUIApplication()
        app.launchEnvironment["HANGTEN_REVIEW_PLANS"] = "1"
        app.launch()

        XCTAssertTrue(app.staticTexts["Choose your session."].waitForExistence(timeout: 10))
        XCTAssertFalse(app.staticTexts["Learn more"].exists)
        XCTAssertFalse(app.staticTexts["Each routine includes its source link."].exists)
        XCTAssertFalse(app.staticTexts["Read the evidence overview"].exists)
    }

    func testBoardPackagesSectionMatchesBuildConfiguration() throws {
        let app = XCUIApplication()
        app.launch()

        let settings = app.buttons["train.settings"]
        XCTAssertTrue(settings.waitForExistence(timeout: 10))
        settings.tap()

        let boardPackages = app.staticTexts["BOARD PACKAGES"]
        let boardEditor = app.buttons["settings.boardEditor"]

        #if DEBUG
        XCTAssertTrue(boardPackages.waitForExistence(timeout: 5))
        XCTAssertTrue(boardEditor.waitForExistence(timeout: 5))
        #else
        XCTAssertFalse(boardPackages.waitForExistence(timeout: 2))
        XCTAssertFalse(boardEditor.waitForExistence(timeout: 2))
        #endif
    }
}
