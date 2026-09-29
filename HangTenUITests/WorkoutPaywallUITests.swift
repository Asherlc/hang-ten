import XCTest

final class WorkoutPaywallUITests: XCTestCase {
    func testThirdWorkoutLaunchShowsPaywallInsteadOfSession() {
        let app = lockedPlanApp()
        app.launch()

        app.buttons["plan.startRoutine"].tap()

        XCTAssertTrue(app.otherElements["paywall.lifetimeUnlock"].waitForExistence(timeout: 2))
        XCTAssertFalse(app.navigationBars["Session"].exists)
        XCTAssertTrue(app.buttons["paywall.restore"].exists)
        XCTAssertTrue(app.staticTexts["Unlock Hang Ten"].exists)
        XCTAssertTrue(app.staticTexts[
            "You’ve completed your 2 free workouts. Unlock unlimited workouts for a one-time purchase."
        ].exists)
    }

    func testDismissingPaywallDoesNotStartWorkout() {
        let app = lockedPlanApp()
        app.launch()

        app.buttons["plan.startRoutine"].tap()
        XCTAssertTrue(app.otherElements["paywall.lifetimeUnlock"].waitForExistence(timeout: 2))

        app.buttons["paywall.close"].tap()

        XCTAssertTrue(app.buttons["plan.startRoutine"].waitForExistence(timeout: 2))
        XCTAssertFalse(app.navigationBars["Session"].exists)
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

        XCTAssertTrue(app.navigationBars["Session"].waitForExistence(timeout: 5))
        XCTAssertFalse(app.otherElements["paywall.lifetimeUnlock"].exists)
    }

    func testVerifiedFakeRestoreContinuesIntoSession() {
        let app = lockedPlanApp()
        app.launchEnvironment["HANGTEN_REVIEW_STOREKIT"] = "1"
        app.launchEnvironment["HANGTEN_REVIEW_VERIFIED_RESTORE"] = "1"
        app.launch()

        app.buttons["plan.startRoutine"].tap()
        XCTAssertTrue(app.otherElements["paywall.lifetimeUnlock"].waitForExistence(timeout: 2))

        app.buttons["paywall.restore"].tap()

        XCTAssertTrue(app.navigationBars["Session"].waitForExistence(timeout: 5))
        XCTAssertFalse(app.otherElements["paywall.lifetimeUnlock"].exists)
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
        let app = lockedPlanApp()
        app.launchEnvironment["HANGTEN_REVIEW_STOREKIT"] = "1"
        app.launchEnvironment["HANGTEN_REVIEW_VERIFIED_PURCHASE"] = "1"
        app.launchEnvironment["HANGTEN_REVIEW_STEP"] = "999"
        app.launch()

        let source = app.segmentedControls["workout.initialWeight.sourcePicker"]
        XCTAssertTrue(source.waitForExistence(timeout: 10))
        source.buttons["Manual"].tap()

        let field = app.textFields["workout.initialWeight.manualField"]
        XCTAssertTrue(field.waitForExistence(timeout: 10))
        let fieldHittable = XCTNSPredicateExpectation(
            predicate: NSPredicate(format: "exists == true AND isHittable == true"),
            object: field
        )
        XCTAssertEqual(XCTWaiter.wait(for: [fieldHittable], timeout: 10), .completed)
        let unit = app.staticTexts["lb"].exists ? "lb" : "kg"
        let keyboard = app.keyboards.firstMatch
        field.tap()
        XCTAssertTrue(keyboard.waitForExistence(timeout: 5), "Tapping the manual weight field must present its keyboard")
        field.typeText(
            String(
                repeating: XCUIKeyboardKey.delete.rawValue,
                count: (field.value as? String)?.count ?? 0
            )
        )
        field.typeText("12.5")

        let bodyweight = app.switches["workout.initialWeight.addBodyweight"]
        let bodyweightReady = XCTNSPredicateExpectation(
            predicate: NSPredicate(format: "exists == true AND hittable == true"),
            object: bodyweight
        )
        XCTAssertEqual(XCTWaiter.wait(for: [bodyweightReady], timeout: 10), .completed)
        // The iOS 26 accessibility frame extends slightly left of the visible switch.
        // Offset 0.45 lands on the center of the off-state thumb.
        bodyweight.coordinate(withNormalizedOffset: CGVector(dx: 0.45, dy: 0.5)).tap()
        let bodyweightEnabled = XCTNSPredicateExpectation(
            predicate: NSPredicate(format: "value == %@", "1"),
            object: bodyweight
        )
        XCTAssertEqual(XCTWaiter.wait(for: [bodyweightEnabled], timeout: 5), .completed,
                       "Add bodyweight must be on before purchasing")

        let start = app.buttons["plan.startRoutine"]
        XCTAssertTrue(start.waitForExistence(timeout: 2))
        var remainingScrollAttempts = 4
        while !start.isHittable, remainingScrollAttempts > 0 {
            app.swipeUp()
            remainingScrollAttempts -= 1
        }
        XCTAssertTrue(start.isHittable)
        start.tap()
        XCTAssertTrue(app.otherElements["paywall.lifetimeUnlock"].waitForExistence(timeout: 2))

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
        XCTAssertFalse(app.navigationBars["Session"].exists)
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
        XCTAssertFalse(app.navigationBars["Session"].exists)
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
        XCTAssertFalse(app.navigationBars["Session"].exists)
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
        XCTAssertFalse(app.navigationBars["Session"].exists)
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
        XCTAssertFalse(app.navigationBars["Session"].exists)
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
        XCTAssertFalse(app.navigationBars["Session"].exists)
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
        XCTAssertFalse(app.navigationBars["Session"].exists)
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
        XCTAssertFalse(app.navigationBars["Session"].exists)
    }

    private func lockedPlanApp() -> XCUIApplication {
        let app = XCUIApplication()
        app.launchEnvironment["HANGTEN_REVIEW_FREE_WORKOUTS_USED"] = "2"
        app.launchEnvironment["HANGTEN_REVIEW_PLAN"] = "1"
        return app
    }

    private func reviewStoreKitApp(purchaseOutcome: String) -> XCUIApplication {
        let app = lockedPlanApp()
        app.launchEnvironment["HANGTEN_REVIEW_STOREKIT"] = "1"
        app.launchEnvironment["HANGTEN_REVIEW_PURCHASE_OUTCOME"] = purchaseOutcome
        return app
    }
}
