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

/// Batch 05 acceptance uses physical screen coordinates. Accessibility is used
/// only to locate projected frames and observe state, never to invoke a contact.
final class Batch05BoardModelInteractionUITests: XCTestCase {
    override func setUpWithError() throws {
        continueAfterFailure = false
        XCUIDevice.shared.orientation = .portrait
    }

    override func tearDown() {
        XCUIDevice.shared.orientation = .portrait
        super.tearDown()
    }

    func testDoorMount() throws {
        try review(boardID: "frictitious.doormount-pro-7", target: "edge-35-right", surfacePoint: CGVector(dx: 0.83197737, dy: 0.46294296))
    }

    func testMegalith() throws {
        try review(boardID: "frictitious.megalith", target: "center-edge-25", surfacePoint: CGVector(dx: 0.55742604, dy: 0.5415197))
    }

    func testForge() throws {
        try review(boardID: "trango.rock-prodigy-forge", target: "variable-edge-rail-right", surfacePoint: CGVector(dx: 0.6323009872, dy: 0.2882222512))
    }

    func testNatural() throws {
        try review(boardID: "trango.rock-prodigy-natural", target: "upper-pocket-right", surfacePoint: CGVector(dx: 0.63137496, dy: 0.61984193))
    }

    func testEvo() throws {
        try review(boardID: "zlagboard.evo", target: "edge-35-center", surfacePoint: CGVector(dx: 0.44739193, dy: 0.47573414))
    }

    func testPro() throws {
        try review(boardID: "zlagboard.pro", target: "edge-35-center", surfacePoint: CGVector(dx: 0.44776505, dy: 0.3821585))
    }

    private func review(boardID: String, target: String, surfacePoint: CGVector) throws {
        let app = XCUIApplication()
        app.launchEnvironment = [
            "HANGTEN_REVIEW_BOARD_ID": boardID,
            "HANGTEN_REVIEW_PORTRAIT": "1",
        ]
        app.launch()
        let model = app.descendants(matching: .any).matching(NSPredicate(format: "label ENDSWITH %@", "hangboard")).firstMatch
        XCTAssertTrue(model.waitForExistence(timeout: 60))
        if boardID == "zlagboard.evo" || boardID == "zlagboard.pro" {
            try assertModelCornersAreVisible(model)
        }
        capture("\(boardID)-portrait-neutral")
        app.terminate()
        app.launchEnvironment["HANGTEN_REVIEW_BOARD_DETAIL"] = "1"
        app.launch()
        XCTAssertTrue(app.navigationBars["Hold specs"].waitForExistence(timeout: 30))
        let contact = app.buttons["boardModel.contact.\(target)"]
        XCTAssertTrue(contact.waitForExistence(timeout: 60))
        let selected = app.otherElements["boardDetail.selectedHold.\(target)"]
        XCTAssertFalse(selected.exists, "The tap must change the initial default contact")
        capture("\(boardID)-portrait-initial")
        let map = app.descendants(matching: .any).matching(identifier: "boardDetail.map").firstMatch
        XCTAssertTrue(map.exists)
        // These points are exposed triangles verified against native body-inclusive
        // visibility and the production closest screen hit on the final USDZs.
        let initialPoint = map.coordinate(withNormalizedOffset: surfacePoint)
        let contactOffset = CGVector(dx: initialPoint.screenPoint.x - contact.frame.midX,
                                     dy: initialPoint.screenPoint.y - contact.frame.midY)
        initialPoint.tap()
        XCTAssertTrue(selected.waitForExistence(timeout: 10), "Real coordinate tap must select \(target)")
        capture("\(boardID)-portrait-active")

        let initialContactFrame = contact.frame
        let allContacts = app.buttons.matching(NSPredicate(format: "identifier BEGINSWITH %@", "boardModel.contact."))
        let canonicalFrames = Dictionary(uniqueKeysWithValues: allContacts.allElementsBoundByIndex.map { ($0.identifier, $0.frame) })
        map.coordinate(withNormalizedOffset: CGVector(dx: 0.55, dy: 0.5))
            .press(forDuration: 0.1, thenDragTo: map.coordinate(withNormalizedOffset: CGVector(dx: 0.70, dy: 0.65)))
        XCTAssertTrue(selected.exists, "Orbit must preserve contact selection")
        XCTAssertNotEqual(contact.frame, initialContactFrame, "Orbit must change the projected contact")
        capture("\(boardID)-portrait-orbit")
        // A real contact tap runs the production selectContact canonical reset.
        if boardID == "trango.rock-prodigy-forge" {
            // The thin rail's visible triangle changes with orbit; use its
            // reviewed interior point on the active surface in this gesture pose.
            map.coordinate(withNormalizedOffset: CGVector(dx: 0.78, dy: 0.365)).tap()
        } else {
            contact.coordinate(withNormalizedOffset: CGVector(dx: 0.5, dy: 0.5))
                .withOffset(contactOffset).tap()
        }
        XCTAssertTrue(selected.exists)
        let resetFinished = XCTNSPredicateExpectation(predicate: NSPredicate { _, _ in
            let currentFrames = Dictionary(
                uniqueKeysWithValues: allContacts.allElementsBoundByIndex.map { ($0.identifier, $0.frame) }
            )
            guard Set(currentFrames.keys) == Set(canonicalFrames.keys) else { return false }
            return currentFrames.allSatisfy { identifier, frame in
                guard let canonical = canonicalFrames[identifier] else { return false }
                return abs(frame.midX - canonical.midX) <= 0.5
                    && abs(frame.midY - canonical.midY) <= 0.5
            }
        }, object: nil)
        // Reading all 28 Pro frames crosses the UI-test process boundary;
        // allow traversal time without relaxing the canonical-frame tolerance.
        XCTAssertEqual(XCTWaiter.wait(for: [resetFinished], timeout: 15), .completed,
                       "A physical surface tap must finish the canonical camera reset")
        // A top-edge center may move less than two points despite a visible orbit.
        // Require every projected contact to return to its canonical frame.
        let resetFrames = Dictionary(
            uniqueKeysWithValues: allContacts.allElementsBoundByIndex.map { ($0.identifier, $0.frame) }
        )
        XCTAssertEqual(Set(resetFrames.keys), Set(canonicalFrames.keys),
                       "Reset must preserve the complete canonical contact set")
        for (identifier, frame) in resetFrames {
            let canonical = try XCTUnwrap(canonicalFrames[identifier])
            XCTAssertEqual(frame.midX, canonical.midX, accuracy: 0.5, identifier)
            XCTAssertEqual(frame.midY, canonical.midY, accuracy: 0.5, identifier)
        }
        capture("\(boardID)-portrait-reset")

        XCUIDevice.shared.orientation = .landscapeRight
        XCTAssertTrue(selected.waitForExistence(timeout: 10))
        XCTAssertGreaterThan(app.frame.width, app.frame.height)
        XCTAssertGreaterThanOrEqual(map.frame.minX, app.frame.minX)
        XCTAssertGreaterThanOrEqual(map.frame.minY, app.frame.minY)
        XCTAssertLessThanOrEqual(map.frame.maxX, app.frame.maxX)
        XCTAssertLessThanOrEqual(map.frame.maxY, app.frame.maxY)
        capture("\(boardID)-landscape-active")
        app.terminate()
        app.launchEnvironment.removeValue(forKey: "HANGTEN_REVIEW_BOARD_DETAIL")
        app.launchEnvironment.removeValue(forKey: "HANGTEN_REVIEW_PORTRAIT")
        app.launchEnvironment["HANGTEN_REVIEW_LANDSCAPE"] = "1"
        app.launch()
        XCTAssertTrue(model.waitForExistence(timeout: 60))
        capture("\(boardID)-landscape-neutral")
    }

    private func assertModelCornersAreVisible(_ model: XCUIElement) throws {
        let screenshot = XCUIScreen.main.screenshot().image
        let cgImage = try XCTUnwrap(screenshot.cgImage)
        let width = cgImage.width
        let height = cgImage.height
        var pixels = [UInt8](repeating: 0, count: width * height * 4)
        try pixels.withUnsafeMutableBytes { storage in
            let context = try XCTUnwrap(CGContext(data: storage.baseAddress, width: width, height: height,
                bitsPerComponent: 8, bytesPerRow: width * 4,
                space: CGColorSpaceCreateDeviceRGB(),
                bitmapInfo: CGImageAlphaInfo.premultipliedLast.rawValue))
            context.draw(cgImage, in: CGRect(x: 0, y: 0, width: width, height: height))
        }
        let frame = model.frame
        let scale = CGFloat(width) / XCUIApplication().frame.width
        // The approved Zlag bodies have nearly square lower corners. A card's
        // decorative 18pt mask must not erase the real body inside this viewport.
        for x in [frame.minX + 3, frame.maxX - 3] {
            let offset = (Int((frame.maxY - 3) * scale) * width + Int(x * scale)) * 4
            XCTAssertLessThan(pixels[offset + 2], 220,
                              "Native body corner must contain wood, not the cream card background")
        }
    }

    private func capture(_ name: String) {
        let attachment = XCTAttachment(screenshot: XCUIScreen.main.screenshot())
        attachment.name = name
        attachment.lifetime = .keepAlways
        add(attachment)
    }
}
