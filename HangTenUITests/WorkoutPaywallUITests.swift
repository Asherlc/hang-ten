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
        app.launch()

        if app.navigationBars["Settings"].waitForExistence(timeout: 5) {
            app.navigationBars["Settings"].buttons.firstMatch.tap()
        }
        let source = app.segmentedControls["workout.initialWeight.sourcePicker"]
        XCTAssertTrue(source.waitForExistence(timeout: 10))
        source.buttons["Scale"].tap()
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
        XCTAssertTrue(field.waitForExistence(timeout: 2))
        let unit = app.staticTexts["lb"].exists ? "lb" : "kg"
        field.tap()
        field.typeText(
            String(
                repeating: XCUIKeyboardKey.delete.rawValue,
                count: (field.value as? String)?.count ?? 0
            )
        )
        field.typeText("12.5")

        let bodyweight = app.switches["workout.initialWeight.addBodyweight"]
        bodyweight.coordinate(withNormalizedOffset: CGVector(dx: 0.93, dy: 0.5)).tap()
        XCTAssertEqual(bodyweight.value as? String, "1")

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

        app.buttons["plan.startRoutine"].tap()
        XCTAssertTrue(app.buttons["paywall.retryProduct"].waitForExistence(timeout: 2))

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
