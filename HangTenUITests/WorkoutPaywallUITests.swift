import XCTest

final class CustomRoutineEditorUITests: XCTestCase {
    func testFirstInvalidSaveRevealsValidationFromSteps() {
        continueAfterFailure = false
        let app = XCUIApplication()
        app.launchEnvironment = ["HANGTEN_REVIEW_PLANS": "1", "HANGTEN_REVIEW_PORTRAIT": "1"]
        defer { app.terminate() }
        app.launch()
        let create = app.buttons["customRoutine.create"]
        XCTAssertTrue(create.waitForExistence(timeout: 30))
        create.tap()
        waitForEditor(in: app)
        let board = app.buttons["customRoutine.board"]
        XCTAssertTrue(board.waitForExistence(timeout: 10))
        board.tap()
        app.buttons["No board"].tap()
        let addSet = app.buttons["customRoutine.addSet"]
        reveal(addSet, in: app)
        addSet.tap()
        let title = app.textFields["customRoutine.stepTitle"]
        reveal(title, in: app)
        XCTAssertTrue(title.isHittable, "Adding a set must open its first Hang for inline editing")
        let editor = app.collectionViews.firstMatch
        XCTAssertTrue(editor.waitForExistence(timeout: 5))
        for _ in 0..<3 { editor.swipeUp() }
        XCTAssertFalse(app.textFields["customRoutine.name"].isHittable)
        let beforeSave = XCTAttachment(screenshot: XCUIScreen.main.screenshot())
        beforeSave.name = "Editor scrolled into steps before first Save"
        beforeSave.lifetime = .keepAlways
        add(beforeSave)

        pressSave(in: app)
        let issues = app.staticTexts["customRoutine.validationErrors"]
        let visible = XCTNSPredicateExpectation(
            predicate: NSPredicate(format: "exists == true AND hittable == true"), object: issues
        )
        XCTAssertEqual(XCTWaiter.wait(for: [visible], timeout: 5), .completed,
                       "The first invalid Save must reveal feedback above the scrolled steps")
        XCTAssertTrue(issues.label.contains("A routine name is required."))
        let attachment = XCTAttachment(screenshot: XCUIScreen.main.screenshot())
        attachment.name = "First failed Save reveals validation from scrolled steps"
        attachment.lifetime = .keepAlways
        add(attachment)
    }

    func testValidationRemainsVisibleWhileCorrectingRoutine() {
        continueAfterFailure = false
        let app = XCUIApplication()
        app.launchEnvironment = ["HANGTEN_REVIEW_PLANS": "1", "HANGTEN_REVIEW_PORTRAIT": "1"]
        defer { app.terminate() }
        app.launch()
        let create = app.buttons["customRoutine.create"]
        XCTAssertTrue(create.waitForExistence(timeout: 30))
        create.tap()
        waitForEditor(in: app)
        let save = app.buttons["customRoutine.save"]
        pressSave(in: app)
        if app.alerts.firstMatch.waitForExistence(timeout: 2) {
            app.alerts.firstMatch.buttons["OK"].tap()
        }
        let issues = app.staticTexts["customRoutine.validationErrors"]
        XCTAssertTrue(issues.waitForExistence(timeout: 5), "Invalid fields need feedback after any alert closes")
        XCTAssertTrue(issues.label.contains("A routine name is required."))
        XCTAssertTrue(issues.label.contains("Add at least one step."))
        let attachment = XCTAttachment(screenshot: XCUIScreen.main.screenshot())
        attachment.name = "Routine validation persists in editor"
        attachment.lifetime = .keepAlways
        add(attachment)

        let name = app.textFields["customRoutine.name"]
        XCTAssertTrue(name.isHittable)
        // Tap the text area; the empty center of this SwiftUI field can miss
        // input focus even when XCTest reports the whole row as hittable.
        name.coordinate(withNormalizedOffset: CGVector(dx: 0.05, dy: 0.5)).tap()
        XCTAssertTrue(app.keyboards.firstMatch.waitForExistence(timeout: 5),
                      "Correcting the routine name must first focus its text field")
        name.typeText("My routine")
        XCTAssertEqual(name.value as? String, "My routine")
        let updated = XCTNSPredicateExpectation(
            predicate: NSPredicate(format: "label CONTAINS %@ AND NOT label CONTAINS %@",
                                   "Add at least one step.", "A routine name is required."),
            object: issues
        )
        XCTAssertEqual(XCTWaiter.wait(for: [updated], timeout: 5), .completed)
        XCTAssertTrue(save.exists)
        let corrected = XCTAttachment(screenshot: XCUIScreen.main.screenshot())
        corrected.name = "Routine validation updates after entering a name"
        corrected.lifetime = .keepAlways
        add(corrected)
    }

    private func waitForEditor(in app: XCUIApplication) {
        XCTAssertTrue(app.navigationBars["Create routine"].waitForExistence(timeout: 10))
        let name = app.textFields["customRoutine.name"]
        let save = app.buttons["customRoutine.save"]
        let ready = XCTNSPredicateExpectation(
            predicate: NSPredicate { _, _ in
                name.exists && save.exists && name.isHittable && save.isHittable
            },
            object: nil
        )
        XCTAssertEqual(XCTWaiter.wait(for: [ready], timeout: 5), .completed,
                       "The presented routine editor must be ready for input")
    }

    private func pressSave(in app: XCUIApplication) {
        let save = app.buttons["customRoutine.save"]
        XCTAssertTrue(save.isEnabled)
        XCTAssertTrue(save.isHittable)
        save.coordinate(withNormalizedOffset: CGVector(dx: 0.5, dy: 0.5))
            .press(forDuration: 0.1)
    }

    private func reveal(_ element: XCUIElement, in app: XCUIApplication) {
        let editor = app.collectionViews.firstMatch
        XCTAssertTrue(editor.waitForExistence(timeout: 5))
        for _ in 0..<8 {
            if element.exists && element.isHittable { return }
            editor.swipeUp()
        }
        XCTAssertTrue(element.exists && element.isHittable,
                      "The expanded routine editor must reveal \(element.identifier)")
    }
}

final class WorkoutPaywallUITests: XCTestCase {
    func testThirdWorkoutPaywallCanBeDismissedWithoutStarting() {
        let app = lockedPlanApp()
        app.launch()

        app.buttons["plan.startRoutine"].tap()
        XCTAssertTrue(app.otherElements["paywall.lifetimeUnlock"].waitForExistence(timeout: 2))
        XCTAssertFalse(app.buttons["workout.primaryControl"].exists)
        XCTAssertTrue(app.buttons["paywall.restore"].exists)
        XCTAssertTrue(app.staticTexts["Unlock Hang Ten"].exists)
        XCTAssertTrue(app.staticTexts[
            "You’ve completed your 2 free workouts. Unlock unlimited workouts for a one-time purchase."
        ].exists)

        app.buttons["paywall.close"].tap()

        XCTAssertTrue(app.buttons["plan.startRoutine"].waitForExistence(timeout: 2))
        XCTAssertFalse(app.buttons["workout.primaryControl"].exists)
    }

    func testVerifiedFakePurchaseContinuesIntoSession() {
        let app = lockedPlanApp()
        app.launchEnvironment["HANGTEN_REVIEW_STOREKIT"] = "1"
        app.launchEnvironment["HANGTEN_REVIEW_VERIFIED_PURCHASE"] = "1"
        app.launch()

        app.buttons["plan.startRoutine"].tap()
        XCTAssertTrue(app.otherElements["paywall.lifetimeUnlock"].waitForExistence(timeout: 2))

        let purchase = app.buttons["paywall.purchase"]
        XCTAssertTrue(purchase.waitForExistence(timeout: 2))
        XCTAssertEqual(purchase.label, "Unlock for $2.99")
        purchase.tap()

        assertWorkoutOpened(in: app)
    }

    func testVerifiedFakeRestoreContinuesIntoSession() {
        let app = lockedPlanApp()
        app.launchEnvironment["HANGTEN_REVIEW_STOREKIT"] = "1"
        app.launchEnvironment["HANGTEN_REVIEW_VERIFIED_RESTORE"] = "1"
        app.launch()

        app.buttons["plan.startRoutine"].tap()
        XCTAssertTrue(app.otherElements["paywall.lifetimeUnlock"].waitForExistence(timeout: 2))

        app.buttons["paywall.restore"].tap()

        assertWorkoutOpened(in: app)
    }

    func testVerifiedPurchaseCarriesScaleSnapshotIntoSensorPreparation() {
        let app = lockedPlanApp()
        app.launchEnvironment["HANGTEN_REVIEW_STOREKIT"] = "1"
        app.launchEnvironment["HANGTEN_REVIEW_VERIFIED_PURCHASE"] = "1"
        app.launchEnvironment["HANGTEN_REVIEW_MOTHERBOARD"] = "1"
        app.launchEnvironment["HANGTEN_REVIEW_SENSOR_DISCONNECTED"] = "1"
        app.launch()

        if app.navigationBars["Settings"].waitForExistence(timeout: 5) {
            app.navigationBars["Settings"].buttons.firstMatch.tap()
        }
        let source = app.segmentedControls["workout.initialWeight.sourcePicker"]
        XCTAssertTrue(source.waitForExistence(timeout: 10))
        source.buttons["Scale"].tap()
        let connect = app.buttons["plan.initialWeight.connect"]
        XCTAssertTrue(connect.waitForExistence(timeout: 10))
        connect.tap()
        let scaleStatus = app.staticTexts["plan.initialWeight.scaleStatus"]
        let connected = XCTNSPredicateExpectation(
            predicate: NSPredicate(
                format: "label == %@",
                "Your supported scale is connected and ready."
            ),
            object: scaleStatus
        )
        XCTAssertEqual(XCTWaiter.wait(for: [connected], timeout: 10), .completed)
        app.buttons["plan.startRoutine"].tap()
        XCTAssertTrue(app.otherElements["paywall.lifetimeUnlock"].waitForExistence(timeout: 2))

        app.buttons["paywall.purchase"].tap()
        if app.buttons["handSide.left"].waitForExistence(timeout: 5) {
            app.buttons["handSide.left"].tap()
        }

        XCTAssertTrue(app.buttons["Skip preparation"].waitForExistence(timeout: 15))
        XCTAssertFalse(app.segmentedControls["workout.initialWeight.sourcePicker"].exists)
    }

    func testVerifiedPurchaseCarriesManualWeightSnapshotIntoSummary() {
        continueAfterFailure = false
        let app = lockedPlanApp()
        app.launchEnvironment["HANGTEN_REVIEW_STOREKIT"] = "1"
        app.launchEnvironment["HANGTEN_REVIEW_VERIFIED_PURCHASE"] = "1"
        app.launchEnvironment["HANGTEN_REVIEW_STEP"] = "999"
        // Match the weight-setup fixture; this case exercises the weight snapshot.
        app.launchEnvironment["HANGTEN_REVIEW_BOARD_ID"] = "tension.grindstone-original"
        app.launchEnvironment["HANGTEN_REVIEW_PLAN_ID"] = "research.max-hangs"
        app.launch()

        XCTAssertTrue(app.staticTexts["Max Hangs"].waitForExistence(timeout: 10))
        XCTAssertTrue(app.staticTexts["Grindstone"].exists,
                      "The weight-flow fixture must resolve to the requested board.")
        let source = app.segmentedControls["workout.initialWeight.sourcePicker"]
        XCTAssertTrue(source.waitForExistence(timeout: 10))
        source.buttons["Manual"].tap()

        // Set the switch before focusing the decimal-pad field. A keyboard-active
        // tap can leave the switch off even when XCTest reports it as hittable.
        let bodyweight = app.switches["workout.initialWeight.addBodyweight"]
        XCTAssertNotNil(visibleControlCoordinate(bodyweight, in: app, requireHittable: false, timeout: 30))
        XCTAssertEqual(bodyweight.value as? String, "0")
        bodyweight.tap()
        let bodyweightEnabled = XCTNSPredicateExpectation(
            predicate: NSPredicate(format: "value == %@", "1"),
            object: bodyweight
        )
        XCTAssertEqual(XCTWaiter.wait(for: [bodyweightEnabled], timeout: 5), .completed,
                       "Add bodyweight must be on before purchasing")

        let field = app.textFields["workout.initialWeight.manualField"]
        XCTAssertTrue(field.waitForExistence(timeout: 10))
        let unit = app.staticTexts["lb"].exists ? "lb" : "kg"
        let keyboard = app.keyboards.firstMatch
        let entryScreenshot = XCTAttachment(screenshot: XCUIScreen.main.screenshot())
        entryScreenshot.name = "Manual weight field before verified purchase"
        entryScreenshot.lifetime = .keepAlways
        add(entryScreenshot)
        // Hosted accessibility queries can outlast a predicate's wait budget in CI.
        // Validate the visible coordinate, then require the keyboard and entered value.
        tapVisibleControl(field, in: app, requireHittable: false, timeout: 30)
        XCTAssertTrue(keyboard.waitForExistence(timeout: 5), "Tapping the manual weight field must present its keyboard")
        field.typeText(
            String(
                repeating: XCUIKeyboardKey.delete.rawValue,
                count: (field.value as? String)?.count ?? 0
            )
        )
        field.typeText("12.5")
        XCTAssertEqual(field.value as? String, "12.5")
        XCTAssertEqual(bodyweight.value as? String, "1")

        let start = app.buttons["plan.startRoutine"]
        XCTAssertTrue(start.waitForExistence(timeout: 2))
        // A full-screen swipe with the keyboard open can move Start behind
        // the navigation bar while XCTest still reports it as hittable.
        let screen = XCUIApplication(bundleIdentifier: "com.apple.springboard")
        let navigationBar = app.navigationBars["Plan"]
        func contentBottom() -> CGFloat {
            let viewport = screen.frame
            guard keyboard.exists else { return viewport.maxY }
            let frame = keyboard.frame
            guard frame.minY.isFinite, frame.width.isFinite, frame.height.isFinite,
                  frame.width > 0, frame.height > 0,
                  frame.minY > navigationBar.frame.maxY,
                  frame.intersects(viewport) else { return viewport.maxY }
            return min(frame.minY, viewport.maxY)
        }
        func isStartVisible() -> Bool {
            let frame = start.frame
            return start.isHittable
                && frame.minY >= navigationBar.frame.maxY
                && frame.maxY <= contentBottom()
        }
        var remainingScrollAttempts = 8
        while !isStartVisible(), remainingScrollAttempts > 0 {
            let viewport = screen.frame
            let contentTop = navigationBar.frame.maxY
            let visibleBottom = contentBottom()
            let origin = screen.coordinate(withNormalizedOffset: .zero).withOffset(
                CGVector(dx: viewport.width / 2, dy: (contentTop + visibleBottom) / 2 - viewport.minY)
            )
            let scrollDelta: CGFloat = start.frame.minY < contentTop ? 100 : -100
            origin.press(forDuration: 0.05, thenDragTo: origin.withOffset(CGVector(dx: 0, dy: scrollDelta)))
            remainingScrollAttempts -= 1
        }
        XCTAssertTrue(isStartVisible(), "Start must be below the navigation bar and above the keyboard")
        tapVisibleControl(start, in: app)
        XCTAssertTrue(app.otherElements["paywall.lifetimeUnlock"].waitForExistence(timeout: 10))

        app.buttons["paywall.purchase"].tap()

        let manualWeight = app.staticTexts["Manual weight: +12.5 \(unit) plus bodyweight"]
        let summary = app.collectionViews.firstMatch
        XCTAssertTrue(summary.waitForExistence(timeout: 10))
        var remainingSummaryScrollAttempts = 10
        while !manualWeight.exists, remainingSummaryScrollAttempts > 0 {
            summary.swipeUp()
            remainingSummaryScrollAttempts -= 1
        }
        XCTAssertTrue(
            manualWeight.waitForExistence(timeout: 2)
        )
        XCTAssertFalse(app.segmentedControls["workout.initialWeight.sourcePicker"].exists)
    }

    func testLandscapePaywallKeepsRestorePurchasesInsideViewport() {
        let app = lockedPlanApp()
        app.launchEnvironment["HANGTEN_REVIEW_STOREKIT"] = "1"
        app.launchEnvironment["HANGTEN_REVIEW_LANDSCAPE"] = "1"
        app.launch()

        let start = app.buttons["plan.startRoutine"]
        XCTAssertTrue(start.waitForExistence(timeout: 2))
        start.tap()

        let restore = app.buttons["paywall.restore"]
        XCTAssertTrue(restore.waitForExistence(timeout: 2))
        XCTAssertGreaterThanOrEqual(restore.frame.minY, app.frame.minY)
        XCTAssertLessThanOrEqual(restore.frame.maxY, app.frame.maxY)
    }

    func testPendingPurchaseShowsApprovedStatusCopy() {
        let app = reviewStoreKitApp(purchaseOutcome: "pending")
        app.launch()

        app.buttons["plan.startRoutine"].tap()
        XCTAssertTrue(app.buttons["paywall.purchase"].waitForExistence(timeout: 2))
        app.buttons["paywall.purchase"].tap()

        XCTAssertTrue(app.staticTexts[
            "Purchase pending. Your workout will unlock after the App Store approves it."
        ].waitForExistence(timeout: 2))
        XCTAssertFalse(app.buttons["workout.primaryControl"].exists)
    }

    func testFailedPurchaseShowsApprovedStatusCopy() {
        let app = reviewStoreKitApp(purchaseOutcome: "failed")
        app.launch()

        app.buttons["plan.startRoutine"].tap()
        XCTAssertTrue(app.buttons["paywall.purchase"].waitForExistence(timeout: 2))
        app.buttons["paywall.purchase"].tap()

        XCTAssertTrue(app.staticTexts[
            "We couldn’t complete the purchase. Please try again or restore purchases."
        ].waitForExistence(timeout: 2))
        XCTAssertFalse(app.buttons["workout.primaryControl"].exists)
    }

    func testCancelledPurchaseShowsApprovedStatusCopy() {
        let app = reviewStoreKitApp(purchaseOutcome: "cancelled")
        app.launch()

        app.buttons["plan.startRoutine"].tap()
        XCTAssertTrue(app.buttons["paywall.purchase"].waitForExistence(timeout: 2))
        app.buttons["paywall.purchase"].tap()

        XCTAssertTrue(app.staticTexts[
            "Purchase cancelled. You weren’t charged."
        ].waitForExistence(timeout: 2))
        XCTAssertFalse(app.buttons["workout.primaryControl"].exists)
    }

    func testRetryAfterTransientProductLoadFailureMakesBuyAvailable() {
        let app = lockedPlanApp()
        app.launchEnvironment["HANGTEN_REVIEW_STOREKIT"] = "1"
        app.launchEnvironment["HANGTEN_REVIEW_PRODUCT_LOAD_FAILURES"] = "1"
        app.launch()

        app.buttons["plan.startRoutine"].tap()

        let purchase = app.buttons["paywall.purchase"]
        XCTAssertTrue(purchase.waitForExistence(timeout: 2))
        XCTAssertFalse(purchase.isEnabled)
        let retry = app.buttons["paywall.retryProduct"]
        XCTAssertTrue(retry.waitForExistence(timeout: 2))

        retry.tap()

        XCTAssertTrue(app.buttons["Unlock for $2.99"].waitForExistence(timeout: 2))
        XCTAssertTrue(purchase.isEnabled)
        XCTAssertFalse(app.buttons["workout.primaryControl"].exists)
    }

    func testRetryRemainsAvailableAfterProductLoadFailureAndEmptyRestore() {
        let app = lockedPlanApp()
        app.launchEnvironment["HANGTEN_REVIEW_STOREKIT"] = "1"
        app.launchEnvironment["HANGTEN_REVIEW_PRODUCT_LOAD_FAILURES"] = "1"
        app.launch()

        let start = app.buttons["plan.startRoutine"]
        XCTAssertTrue(start.waitForExistence(timeout: 10))
        let startReady = XCTNSPredicateExpectation(
            predicate: NSPredicate(format: "exists == true AND hittable == true"),
            object: start
        )
        XCTAssertEqual(XCTWaiter.wait(for: [startReady], timeout: 10), .completed)
        start.tap()

        XCTAssertTrue(app.otherElements["paywall.lifetimeUnlock"].waitForExistence(timeout: 10))
        XCTAssertTrue(app.buttons["paywall.retryProduct"].waitForExistence(timeout: 10))

        app.buttons["paywall.restore"].tap()

        XCTAssertTrue(app.staticTexts[
            "Nothing to restore. No lifetime unlock purchase was found."
        ].waitForExistence(timeout: 2))
        let retry = app.buttons["paywall.retryProduct"]
        XCTAssertTrue(retry.exists)
        XCTAssertTrue(retry.isEnabled)

        retry.tap()

        let purchase = app.buttons["paywall.purchase"]
        XCTAssertTrue(app.buttons["Unlock for $2.99"].waitForExistence(timeout: 2))
        XCTAssertTrue(purchase.isEnabled)
        XCTAssertFalse(app.buttons["workout.primaryControl"].exists)
    }

    func testRetryRemainsHittableAfterProductLoadFailureAndRestoreFailure() {
        let app = lockedPlanApp()
        app.launchEnvironment["HANGTEN_REVIEW_STOREKIT"] = "1"
        app.launchEnvironment["HANGTEN_REVIEW_PRODUCT_LOAD_FAILURES"] = "1"
        app.launchEnvironment["HANGTEN_REVIEW_RESTORE_OUTCOME"] = "failed"
        app.launch()

        app.buttons["plan.startRoutine"].tap()
        XCTAssertTrue(app.buttons["paywall.retryProduct"].waitForExistence(timeout: 2))

        app.buttons["paywall.restore"].tap()

        XCTAssertTrue(app.staticTexts[
            "Restore failed. Please try again."
        ].waitForExistence(timeout: 2))
        let retry = app.buttons["paywall.retryProduct"]
        XCTAssertTrue(retry.exists)
        XCTAssertTrue(retry.isEnabled)

        retry.tap()

        XCTAssertTrue(app.buttons["Unlock for $2.99"].waitForExistence(timeout: 2))
        XCTAssertTrue(app.buttons["paywall.purchase"].isEnabled)
        XCTAssertFalse(app.buttons["workout.primaryControl"].exists)
    }

    func testRestoreWithoutEntitlementShowsNothingToRestoreFeedback() {
        let app = lockedPlanApp()
        app.launchEnvironment["HANGTEN_REVIEW_STOREKIT"] = "1"
        app.launch()

        app.buttons["plan.startRoutine"].tap()
        XCTAssertTrue(app.buttons["paywall.restore"].waitForExistence(timeout: 2))
        app.buttons["paywall.restore"].tap()

        XCTAssertTrue(app.staticTexts[
            "Nothing to restore. No lifetime unlock purchase was found."
        ].waitForExistence(timeout: 2))
        XCTAssertFalse(app.buttons["workout.primaryControl"].exists)
    }

    func testRestoreFailureUsesRestoreSpecificFeedback() {
        let app = lockedPlanApp()
        app.launchEnvironment["HANGTEN_REVIEW_STOREKIT"] = "1"
        app.launchEnvironment["HANGTEN_REVIEW_RESTORE_OUTCOME"] = "failed"
        app.launch()

        app.buttons["plan.startRoutine"].tap()
        XCTAssertTrue(app.buttons["paywall.restore"].waitForExistence(timeout: 2))
        app.buttons["paywall.restore"].tap()

        XCTAssertTrue(app.staticTexts[
            "Restore failed. Please try again."
        ].waitForExistence(timeout: 2))
        XCTAssertFalse(app.staticTexts[
            "We couldn’t complete the purchase. Please try again or restore purchases."
        ].exists)
        XCTAssertFalse(app.buttons["workout.primaryControl"].exists)
    }

    private func assertWorkoutOpened(
        in app: XCUIApplication,
        file: StaticString = #filePath,
        line: UInt = #line
    ) {
        // Verified access opens the session before on-demand 3D preparation finishes.
        XCTAssertTrue(app.buttons["workout.end"].waitForExistence(timeout: 10), file: file, line: line)
        XCTAssertTrue(app.staticTexts["workout.timer"].exists, file: file, line: line)
        XCTAssertFalse(app.otherElements["paywall.lifetimeUnlock"].exists, file: file, line: line)
        let attachment = XCTAttachment(screenshot: XCUIScreen.main.screenshot())
        attachment.name = "Workout opened after verified access"
        attachment.lifetime = .keepAlways
        add(attachment)
    }

    private func lockedPlanApp() -> XCUIApplication {
        let app = XCUIApplication()
        app.launchEnvironment["HANGTEN_REVIEW_FREE_WORKOUTS_USED"] = "2"
        app.launchEnvironment["HANGTEN_REVIEW_PLAN"] = "1"
        // Keep access handoffs independent of the board persisted by previous
        // tests and its on-demand model download. This is the bundled weight fixture.
        app.launchEnvironment["HANGTEN_REVIEW_BOARD_ID"] = "tension.grindstone-original"
        app.launchEnvironment["HANGTEN_REVIEW_PLAN_ID"] = "research.max-hangs"
        return app
    }

    private func reviewStoreKitApp(purchaseOutcome: String) -> XCUIApplication {
        let app = lockedPlanApp()
        app.launchEnvironment["HANGTEN_REVIEW_STOREKIT"] = "1"
        app.launchEnvironment["HANGTEN_REVIEW_PURCHASE_OUTCOME"] = purchaseOutcome
        return app
    }
}
