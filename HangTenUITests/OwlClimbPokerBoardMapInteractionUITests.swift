import XCTest

final class OwlClimbPokerBoardMapInteractionUITests: XCTestCase {
    override func tearDown() {
        // Landscape review launches leave the shared simulator in landscape;
        // reset so later cases/suites on the same device are not poisoned.
        XCUIDevice.shared.orientation = .portrait
        super.tearDown()
    }

    // Named so it sorts before testLandscape* under alphabetical XCTest order.
    func testModelBoardDetailRendersAndSelectsHold() throws {
        let app = XCUIApplication()
        // Prefer the board-detail review route over the picker: after a landscape
        // 3D board-detail test, picker launch often white-screens under CI load.
        app.launchEnvironment = [
            "HANGTEN_REVIEW_BOARD_ID": "owl-climb.poker",
            "HANGTEN_REVIEW_BOARD_DETAIL": "1",
            "HANGTEN_REVIEW_PORTRAIT": "1",
        ]
        app.launch()

        XCTAssertTrue(
            app.navigationBars["Hold specs"].waitForExistence(timeout: 30),
            "The DEBUG board-detail route must be displayed."
        )

        // The poker board is a model board with a single presentation ("Four faces")
        // and four orientations (face-a, face-b, face-c, face-d). The default
        // orientation is face-a. There is no presentation selector since there
        // is only one presentation. The 3D model loads asynchronously; verify
        // the board detail map is present (which contains the model surface).
        let map = app.otherElements["boardDetail.map"]
        XCTAssertTrue(map.waitForExistence(timeout: 30), "The board detail map must be present.")

        // Select a face-a contact (default orientation). The hold legend buttons
        // use accessibility identifier "boardDetail.holdLegend.<contactID>".
        let faceALeftOuterSlot = app.buttons["boardDetail.holdLegend.face-a-left-outer-slot"]
        XCTAssertTrue(faceALeftOuterSlot.waitForExistence(timeout: 10))
        XCTAssertTrue(faceALeftOuterSlot.isHittable)
        addScreenshot(named: "Poker Face A normal")

        let selected = app.otherElements["boardDetail.selectedHold.face-a-left-outer-slot"]
        // The hold may already be selected by default; if so, tapping again is a no-op.
        if !selected.exists {
            faceALeftOuterSlot.tap()
            XCTAssertTrue(
                selected.waitForExistence(timeout: 10),
                "Tapping the Face A hold legend button must select the matching hold."
            )
        }
        addScreenshot(named: "Poker Face A selected")
    }

    func testLandscapeBoardDetailHidesRootTabBarAndKeepsMapInViewport() throws {
        let (app, map) = try launchLandscapeBoardDetail(
            boardID: "escape.unlimited",
            expectedBoardName: "Unlimited Board"
        )
        assertMap(map, isInside: app)

        XCUIDevice.shared.orientation = .portrait
    }

    func testLandscapeSquareBoardDetailKeepsMapInViewport() throws {
        let (app, map) = try launchLandscapeBoardDetail(
            boardID: "nature.stone-hanger",
            expectedBoardName: "Stone Hanger"
        )
        assertMap(map, isInside: app)
        XCTAssertEqual(map.frame.midX, app.frame.midX, accuracy: 1)
        XCTAssertEqual(map.frame.width, map.frame.height, accuracy: 1)

        XCUIDevice.shared.orientation = .portrait
    }

    func testLandscapeMultiPresentationSquareBoardDetailKeepsMapInViewport() throws {
        let (app, map) = try launchLandscapeBoardDetail(
            boardID: "nature.stone-hanger-mini",
            expectedBoardName: "Stone Hanger Mini"
        )
        assertMap(map, isInside: app)

        let presentationSelector = app.segmentedControls["boardDetail.presentationSelector"]
        XCTAssertTrue(
            presentationSelector.waitForExistence(timeout: 5),
            "Multi-presentation boards must show the boardDetail.presentationSelector."
        )
        XCTAssertGreaterThanOrEqual(presentationSelector.frame.minY, app.frame.minY)
        XCTAssertLessThanOrEqual(presentationSelector.frame.maxY, map.frame.minY + 1)

        XCUIDevice.shared.orientation = .portrait
    }

    private func launchLandscapeBoardDetail(
        boardID: String,
        expectedBoardName: String
    ) throws -> (app: XCUIApplication, map: XCUIElement) {
        let app = XCUIApplication()
        app.launchEnvironment = [
            "HANGTEN_REVIEW_BOARD_ID": boardID,
            "HANGTEN_REVIEW_BOARD_DETAIL": "1",
            "HANGTEN_REVIEW_LANDSCAPE": "1",
        ]
        app.launch()

        XCTAssertTrue(
            app.navigationBars["Hold specs"].waitForExistence(timeout: 10),
            "The DEBUG board-detail route must be displayed."
        )
        XCTAssertTrue(
            app.staticTexts[expectedBoardName].waitForExistence(timeout: 5),
            "Hold specs must show '\(expectedBoardName)' for boardID '\(boardID)' (wrong ID silently keeps the default board)."
        )

        let tabBar = app.tabBars.firstMatch
        XCTAssertFalse(
            tabBar.exists && tabBar.isHittable,
            "The root TabView tab bar must not be visible in landscape board detail."
        )

        let map = app.otherElements["boardDetail.map"]
        XCTAssertTrue(map.waitForExistence(timeout: 10), "The board detail map must be present.")
        return (app, map)
    }

    private func assertMap(
        _ map: XCUIElement,
        isInside app: XCUIApplication,
        file: StaticString = #filePath,
        line: UInt = #line
    ) {
        let mapFrame = map.frame
        let appFrame = app.frame
        XCTAssertGreaterThanOrEqual(mapFrame.minX, appFrame.minX, file: file, line: line)
        XCTAssertGreaterThanOrEqual(mapFrame.minY, appFrame.minY, file: file, line: line)
        XCTAssertLessThanOrEqual(mapFrame.maxX, appFrame.maxX, file: file, line: line)
        XCTAssertLessThanOrEqual(mapFrame.maxY, appFrame.maxY, file: file, line: line)
        XCTAssertGreaterThan(
            mapFrame.width,
            80,
            "Map must not collapse in compact landscape (frame=\(mapFrame), app=\(appFrame)).",
            file: file,
            line: line
        )
        XCTAssertGreaterThan(
            mapFrame.height,
            80,
            "Map must not collapse in compact landscape (frame=\(mapFrame), app=\(appFrame)).",
            file: file,
            line: line
        )
        let holdMarker = app.descendants(matching: .any)
            .matching(NSPredicate(format: "identifier BEGINSWITH %@", "boardDetail.holdMarker."))
            .firstMatch
        let modelSurface = app.descendants(matching: .any)["boardModel.3d"]
        XCTAssertTrue(
            map.isHittable
                || (holdMarker.exists && holdMarker.isHittable)
                || (modelSurface.exists && modelSurface.isHittable),
            "Map (or a hold marker / 3D surface on it) must remain hittable in compact landscape.",
            file: file,
            line: line
        )
    }

    private func addScreenshot(named name: String) {
        let attachment = XCTAttachment(screenshot: XCUIScreen.main.screenshot())
        attachment.name = name
        attachment.lifetime = .keepAlways
        add(attachment)
    }
}

final class BeastmakerBoardPickerInteractionUITests: XCTestCase {
    override func setUpWithError() throws {
        continueAfterFailure = false
        XCUIDevice.shared.orientation = .portrait
    }

    override func tearDown() {
        XCUIDevice.shared.orientation = .portrait
        super.tearDown()
    }

    func testTappingModelCenterSelectsBoard() throws {
        let app = XCUIApplication()
        app.launchEnvironment = ["HANGTEN_REVIEW_BOARD_PICKER": "1"]
        app.launch()

        let search = app.searchFields["Search boards"]
        if !search.waitForExistence(timeout: 45) {
            // Picker review route can white-screen under CI load after landscape
            // board-detail cases; one terminate+relaunch recovers reliably.
            app.terminate()
            app.launch()
            XCTAssertTrue(
                search.waitForExistence(timeout: 60),
                "Board picker Search boards must appear after relaunch."
            )
        }
        search.tap()
        search.typeText("Beastmaker 1000")

        let picker = app.navigationBars["Choose board"]
        XCTAssertTrue(picker.waitForExistence(timeout: 30))

        let board = app.buttons["boardPicker.board.beastmaker-1000"]
        XCTAssertTrue(board.waitForExistence(timeout: 45))

        // The model is display-only and intentionally collapsed from the
        // accessibility tree. The card button frame still covers its visible
        // model region: y=0.35 is the model center before the title row.
        board.coordinate(withNormalizedOffset: CGVector(dx: 0.5, dy: 0.35)).tap()

        XCTAssertTrue(
            app.buttons["Change board"].waitForExistence(timeout: 10),
            "Tapping the model center must select the board and dismiss the picker."
        )
        XCTAssertFalse(board.exists, "The picker card must disappear after selection.")
    }
}
