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

    func testLandscapePaywallKeepsRestorePurchasesInsideViewport() {
        let app = lockedPlanApp()
        app.launchEnvironment["HANGTEN_REVIEW_STOREKIT"] = "1"
        app.launchEnvironment["HANGTEN_REVIEW_LANDSCAPE"] = "1"
        app.launch()

        app.buttons["plan.startRoutine"].tap()

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
