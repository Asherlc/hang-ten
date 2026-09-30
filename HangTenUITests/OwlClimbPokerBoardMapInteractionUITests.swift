import XCTest
import UIKit

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
        XCTAssertTrue(search.waitForExistence(timeout: 45), "Board picker Search boards must appear.")
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
        try review(boardID: "frictitious.doormount-pro-7", target: "edge-35-right",
                   surfacePoint: CGVector(dx: 0.83197737, dy: 0.46294296),
                   resetContactOffset: CGVector(dx: 0.82, dy: 0.55))
    }

    func testMegalith() throws {
        try review(boardID: "frictitious.megalith", target: "center-edge-25")
    }

    func testForge() throws {
        // The projected bounds center falls in the gap between the two units.
        try review(boardID: "trango.rock-prodigy-forge", target: "variable-edge-rail-right",
                   surfacePoint: CGVector(dx: 0.70, dy: 0.43))
    }

    func testNatural() throws {
        // The projected center of this recessed pocket can fall in empty space
        // after orbiting; aim at its visible right wall for the reset tap.
        try review(boardID: "trango.rock-prodigy-natural", target: "upper-pocket-right",
                   resetContactOffset: CGVector(dx: 0.82, dy: 0.55))
    }

    func testEvo() throws {
        try review(boardID: "zlagboard.evo", target: "edge-35-center")
    }

    func testPro() throws {
        try review(boardID: "zlagboard.pro", target: "edge-35-center",
                   surfacePoint: CGVector(dx: 0.44776505, dy: 0.3821585))
    }

    private func review(boardID: String, target: String, surfacePoint: CGVector? = nil,
                        resetContactOffset: CGVector = CGVector(dx: 0.5, dy: 0.5)) throws {
        let app = XCUIApplication()
        XCUIDevice.shared.orientation = .portrait
        app.launchEnvironment = [
            "HANGTEN_REVIEW_BOARD_ID": boardID,
            "HANGTEN_REVIEW_BOARD_DIAGNOSTICS": "1",
        ]
        app.launch()
        // The Train card's noninteractive preview starts loading this same model
        // before the map test begins. Navigate straight to Hold specs instead
        // of waiting for that preview to finish and importing the USDZ again in
        // the interactive map. The contact query below is the readiness check
        // for the model this test actually exercises.
        app.buttons["View hold specs"].tap()
        XCTAssertTrue(app.navigationBars["Hold specs"].waitForExistence(timeout: 30))
        let contact = app.buttons["boardModel.contact.\(target)"]
        XCTAssertTrue(contact.waitForExistence(timeout: 120))
        let map = app.descendants(matching: .any).matching(identifier: "boardDetail.map").firstMatch
        XCTAssertTrue(map.waitForExistence(timeout: 10))
        if boardID == "zlagboard.evo" || boardID == "zlagboard.pro" {
            try assertModelBodyIsVisible(in: map)
        }
        capture("\(boardID)-portrait-neutral")
        let selected = app.otherElements["boardDetail.selectedHold.\(target)"]
        XCTAssertFalse(selected.exists, "The tap must change the initial default contact")
        capture("\(boardID)-portrait-initial")
        XCTAssertTrue(map.exists)
        // The contact's accessibility frame is projected from its live RealityKit
        // bounds. Tap that screen location through the RealityView so this checks
        // native spatial picking without baking in the previous renderer's camera.
        let initialPoint = surfacePoint.map { map.coordinate(withNormalizedOffset: $0) }
            ?? surfaceCoordinate(for: contact, in: map)
        initialPoint.tap()
        XCTAssertTrue(selected.waitForExistence(timeout: 10), "Real coordinate tap must select \(target)")
        capture("\(boardID)-portrait-active")

        let initialContactFrame = contact.frame
        captureRendererDiagnostic(app: app, name: "\(boardID)-before-orbit")
        let initialMapFrame = map.frame
        // Use the same screen anchor as tapVisibleControl. App accessibility
        // containers can report invalid bounds on iOS 26.
        let screenFrame = XCUIApplication(bundleIdentifier: "com.apple.springboard").frame
        let initialMapImage = try mapSnapshot(in: initialMapFrame, screenFrame: screenFrame)
        // Some models have empty gaps around the projected center. Begin the
        // orbit on the verified surface point when the test needed one to pick.
        let orbitStart = surfacePoint != nil
            ? initialPoint
            : map.coordinate(withNormalizedOffset: CGVector(dx: 0.55, dy: 0.5))
        // DoorMount's shallow viewport makes the old gesture only 44 × 11 points.
        // Give UIKit a sustained drag across the surface rather than a brief
        // touch that can be synthesized as a contact tap/camera reset on CI.
        let orbitEndX = boardID == "frictitious.doormount-pro-7" ? 0.50 : 0.70
        orbitStart.press(forDuration: 0.3,
                         thenDragTo: map.coordinate(withNormalizedOffset: CGVector(dx: orbitEndX, dy: 0.65)),
                         withVelocity: .slow, thenHoldForDuration: 0.2)
        XCTAssertTrue(selected.exists, "Orbit must preserve contact selection")
        let orbitFinished = XCTNSPredicateExpectation(predicate: NSPredicate { _, _ in
            contact.frame != initialContactFrame
        }, object: nil)
        XCTAssertEqual(XCTWaiter.wait(for: [orbitFinished], timeout: 15), .completed,
                       "Orbit must change the projected contact")
        let visibleOrbit = XCTNSPredicateExpectation(predicate: NSPredicate { _, _ in
            guard let image = try? self.mapSnapshot(in: initialMapFrame, screenFrame: screenFrame) else {
                return false
            }
            return image != initialMapImage
        }, object: nil)
        let visibleOrbitResult = XCTWaiter.wait(for: [visibleOrbit], timeout: 60)
        capture("\(boardID)-portrait-orbit")
        captureRendererDiagnostic(app: app, name: "\(boardID)-after-orbit")
        XCTAssertEqual(visibleOrbitResult, .completed,
                       "Orbit must change the rendered board, not only its accessibility projection")
        // Reproject after orbit; the initial contact offset no longer tracks
        // the visible surface once the camera has moved.
        let resetPoint = surfaceCoordinate(for: contact, in: map, offset: resetContactOffset)
        resetPoint.tap()
        XCTAssertTrue(selected.exists)
        let resetFinished = XCTNSPredicateExpectation(predicate: NSPredicate { _, _ in
            let frame = contact.frame
            // XCUI frames are pixel-rounded. Exact camera/framing reset is
            // covered for every contact by BoardModelRealityTests.
            return abs(frame.midX - initialContactFrame.midX) <= 3
                && abs(frame.midY - initialContactFrame.midY) <= 3
        }, object: nil)
        let resetResult = XCTWaiter.wait(for: [resetFinished], timeout: 30)
        if resetResult != .completed {
            print("Camera reset diagnostic: board=\(boardID) contact=\(target) canonical=\(initialContactFrame) actual=\(contact.frame)")
        }
        XCTAssertEqual(resetResult, .completed,
                       "A physical surface tap must finish the canonical camera reset")
        capture("\(boardID)-portrait-reset")

        XCUIDevice.shared.orientation = .landscapeRight
        XCTAssertTrue(selected.waitForExistence(timeout: 10))
        XCTAssertGreaterThan(app.frame.width, app.frame.height)
        XCTAssertGreaterThanOrEqual(map.frame.minX, app.frame.minX)
        XCTAssertGreaterThanOrEqual(map.frame.minY, app.frame.minY)
        XCTAssertLessThanOrEqual(map.frame.maxX, app.frame.maxX)
        XCTAssertLessThanOrEqual(map.frame.maxY, app.frame.maxY)
        capture("\(boardID)-landscape-active")
    }

    private func surfaceCoordinate(for contact: XCUIElement, in map: XCUIElement,
                                   offset: CGVector = CGVector(dx: 0.5, dy: 0.5)) -> XCUICoordinate {
        let frame = contact.frame
        let viewport = map.frame
        return map.coordinate(withNormalizedOffset: CGVector(
            dx: (frame.minX + frame.width * offset.dx - viewport.minX) / viewport.width,
            dy: (frame.minY + frame.height * offset.dy - viewport.minY) / viewport.height
        ))
    }

    private func captureRendererDiagnostic(app: XCUIApplication, name: String) {
        let element = app.descendants(matching: .any)
            .matching(identifier: "boardModel.renderDiagnostic").firstMatch
        let value = element.exists ? String(describing: element.value ?? "pending") : "missing"
        let mapFrame = app.descendants(matching: .any)
            .matching(identifier: "boardDetail.map").firstMatch.frame
        let screenshot = XCUIScreen.main.screenshot().image
        let attachment = XCTAttachment(string:
            "renderer=\(value);map=\(mapFrame);app=\(app.frame);imageSize=\(screenshot.size);scale=\(screenshot.scale);orientation=\(screenshot.imageOrientation.rawValue);rawPixels=\(screenshot.cgImage?.width ?? 0)x\(screenshot.cgImage?.height ?? 0)")
        attachment.name = name
        attachment.lifetime = .keepAlways
        add(attachment)
    }

    private func mapSnapshot(in frame: CGRect, screenFrame: CGRect) throws -> Data {
        // RealityView's accessibility element can remain queryable while XCTest
        // cannot snapshot its hosted view. Crop the screen at the saved viewport
        // instead, so the assertion observes pixels without that snapshot API.
        let screenshot = normalizedScreenImage()
        let image = try XCTUnwrap(screenshot.cgImage)
        let scale = CGFloat(image.width) / screenFrame.width
        let region = CGRect(x: (frame.minX - screenFrame.minX) * scale,
                            y: (frame.minY - screenFrame.minY) * scale,
                            width: frame.width * scale,
                            height: frame.height * scale).integral
        let bounds = CGRect(x: 0, y: 0, width: image.width, height: image.height)
        XCTAssertTrue(region.width > 0 && region.height > 0 && bounds.contains(region),
                      "Map crop \(region) must fit normalized screenshot \(bounds); map=\(frame), screen=\(screenFrame)")
        let cropped = try XCTUnwrap(image.cropping(to: region))
        return try XCTUnwrap(UIImage(cgImage: cropped).pngData())
    }

    private func normalizedScreenImage() -> UIImage {
        let image = XCUIScreen.main.screenshot().image
        // A screenshot can retain a landscape CGImage with a portrait UIImage
        // orientation after another test rotates the device. Draw it once to
        // apply that orientation before converting screen points to pixels.
        let format = UIGraphicsImageRendererFormat()
        format.scale = image.scale
        return UIGraphicsImageRenderer(size: image.size, format: format).image { _ in
            image.draw(in: CGRect(origin: .zero, size: image.size))
        }
    }

    private func assertModelBodyIsVisible(in viewport: XCUIElement) throws {
        let rendered = XCTNSPredicateExpectation(predicate: NSPredicate { _, _ in
            ((try? self.modelBodySampleCount(in: viewport)) ?? 0) > 8
        }, object: nil)
        // On-Demand Resources can still be downloading when the card's accessibility
        // element appears. Wait for the rendered body itself before checking it.
        XCTAssertEqual(XCTWaiter.wait(for: [rendered], timeout: 90), .completed,
                       "Native board body must finish loading inside its map viewport")
    }

    private func modelBodySampleCount(in viewport: XCUIElement) throws -> Int {
        let screenshot = normalizedScreenImage()
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
        let frame = viewport.frame
        // Ignore the rounded card edge. A blank ODR placeholder can otherwise
        // satisfy this check from its border even though RealityKit has no mesh.
        let bodyFrame = frame.insetBy(dx: frame.width * 0.12, dy: frame.height * 0.12)
        let scale = CGFloat(width) / XCUIApplication().frame.width
        // RealityKit preserves the physical mesh aspect ratio within its card.
        // Scan the inner viewport so the card border and letterbox margins do not
        // count as visible board geometry.
        var visibleBodySamples = 0
        let sampleCount = 16
        for row in 0..<sampleCount {
            for column in 0..<sampleCount {
                let x = bodyFrame.minX + (CGFloat(column) + 0.5) * bodyFrame.width / CGFloat(sampleCount)
                let y = bodyFrame.minY + (CGFloat(row) + 0.5) * bodyFrame.height / CGFloat(sampleCount)
                let offset = (Int(y * scale) * width + Int(x * scale)) * 4
                if pixels[offset + 2] < 235 { visibleBodySamples += 1 }
            }
        }
        return visibleBodySamples
    }

    private func capture(_ name: String) {
        let attachment = XCTAttachment(screenshot: XCUIScreen.main.screenshot())
        attachment.name = name
        attachment.lifetime = .keepAlways
        add(attachment)
    }
}
