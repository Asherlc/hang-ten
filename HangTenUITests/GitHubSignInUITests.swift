import XCTest

final class GitHubSignInUITests: XCTestCase {
    func testGitHubSheetUsesDeviceFlowAndDoesNotExposePATInput() throws {
        let app = XCUIApplication()
        app.launchEnvironment = [
            "HANGTEN_REVIEW_BOARD_EDITOR": "1",
            "HANGTEN_REVIEW_GITHUB_SIGN_IN": "1",
        ]
        app.launch()

        XCTAssertTrue(app.buttons["github.connect"].waitForExistence(timeout: 10))
        XCTAssertTrue(app.staticTexts["github.device-flow.description"].exists)
        XCTAssertFalse(app.secureTextFields["github.token"].exists)
    }
}
