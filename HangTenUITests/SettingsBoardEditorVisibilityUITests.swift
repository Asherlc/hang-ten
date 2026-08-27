import XCTest

final class SettingsBoardEditorVisibilityUITests: XCTestCase {
    func testBoardEditorControlMatchesBuildConfiguration() throws {
        let app = XCUIApplication()
        app.launch()

        let settings = app.buttons["train.settings"]
        XCTAssertTrue(settings.waitForExistence(timeout: 10))
        settings.tap()

        let boardEditor = app.buttons["settings.boardEditor"]

        #if DEBUG
        XCTAssertTrue(boardEditor.waitForExistence(timeout: 5))
        #else
        XCTAssertFalse(boardEditor.waitForExistence(timeout: 2))
        #endif
    }
}
