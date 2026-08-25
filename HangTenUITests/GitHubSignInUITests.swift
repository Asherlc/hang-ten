import XCTest

final class GitHubSignInUITests: XCTestCase {
    func testGitHubSheetUsesDeviceFlowAndDoesNotExposePATGuidance() throws {
        let app = XCUIApplication()
        app.launchEnvironment = [
            "HANGTEN_REVIEW_BOARD_EDITOR": "1",
            "HANGTEN_REVIEW_GITHUB_SIGN_IN": "1",
        ]
        app.launch()

        XCTAssertTrue(app.buttons["github.connect"].waitForExistence(timeout: 10))
        XCTAssertTrue(app.staticTexts["github.device-flow.description"].exists)
        XCTAssertFalse(app.secureTextFields["github.token"].exists)
        XCTAssertFalse(app.staticTexts.matching(NSPredicate(
            format: "label CONTAINS[c] %@",
            "personal access token"
        )).firstMatch.exists)
    }

    func testGitHubChallengeExposesOpenAndCancelThenReturnsToConnect() throws {
        let app = XCUIApplication()
        app.launchEnvironment = [
            "HANGTEN_REVIEW_BOARD_EDITOR": "1",
            "HANGTEN_REVIEW_GITHUB_SIGN_IN": "1",
            "HANGTEN_REVIEW_GITHUB_DEVICE_CHALLENGE": "1",
        ]
        app.launch()

        let connect = app.buttons["github.connect"]
        XCTAssertTrue(connect.waitForExistence(timeout: 10))
        connect.tap()

        XCTAssertTrue(app.staticTexts["github.device-code"].waitForExistence(timeout: 10))
        XCTAssertEqual(app.staticTexts["github.device-code"].label, "ABCD-EFGH")
        XCTAssertTrue(app.buttons["github.open-verification"].exists)
        let cancel = app.buttons["github.cancel"]
        XCTAssertTrue(cancel.exists)
        cancel.tap()

        XCTAssertTrue(connect.waitForExistence(timeout: 10))
        XCTAssertFalse(app.staticTexts["github.device-code"].exists)
    }
}
