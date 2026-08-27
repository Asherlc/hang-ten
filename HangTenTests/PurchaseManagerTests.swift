import XCTest
@testable import HangTen

@MainActor
final class PurchaseManagerTests: XCTestCase {
    func testVerifiedCurrentEntitlementUnlocksLifetimeAccess() async {
        let client = FakeStoreKitClient(
            currentEntitlement: .verified(productID: PurchaseManager.lifetimeProductID)
        )
        let manager = PurchaseManager(client: client)

        await manager.prepare()

        XCTAssertTrue(manager.hasLifetimeEntitlement)
    }

    func testUnverifiedPurchaseDoesNotUnlockAccess() async {
        let client = FakeStoreKitClient(
            purchaseResult: .success(.unverified(productID: PurchaseManager.lifetimeProductID))
        )
        let manager = PurchaseManager(client: client)

        await manager.purchase()

        XCTAssertFalse(manager.hasLifetimeEntitlement)
        XCTAssertEqual(manager.state, .failed)
    }

    func testUnverifiedCurrentEntitlementDoesNotUnlockAccess() async {
        let client = FakeStoreKitClient(
            currentEntitlement: .unverified(productID: PurchaseManager.lifetimeProductID)
        )
        let manager = PurchaseManager(client: client)

        await manager.prepare()

        XCTAssertFalse(manager.hasLifetimeEntitlement)
        XCTAssertEqual(manager.state, .failed)
    }

    func testVerifiedPurchaseUnlocksLifetimeAccess() async {
        let client = FakeStoreKitClient(
            purchaseResult: .success(.verified(productID: PurchaseManager.lifetimeProductID))
        )
        let manager = PurchaseManager(client: client)

        await manager.purchase()

        XCTAssertTrue(manager.hasLifetimeEntitlement)
        XCTAssertEqual(manager.state, .idle)
    }

    func testRestoreUnlocksLifetimeAccessWhenCurrentEntitlementIsVerified() async {
        let client = FakeStoreKitClient(
            currentEntitlement: .verified(productID: PurchaseManager.lifetimeProductID)
        )
        let manager = PurchaseManager(client: client)

        await manager.restore()

        XCTAssertTrue(manager.hasLifetimeEntitlement)
        XCTAssertEqual(manager.state, .idle)
    }

    func testPendingPurchaseRemainsVisibleToThePaywall() async {
        let manager = PurchaseManager(client: FakeStoreKitClient(purchaseResult: .pending))

        await manager.purchase()

        XCTAssertFalse(manager.hasLifetimeEntitlement)
        XCTAssertEqual(manager.state, .pending)
    }

    func testCancelledPurchaseReturnsToIdle() async {
        let manager = PurchaseManager(client: FakeStoreKitClient(purchaseResult: .userCancelled))

        await manager.purchase()

        XCTAssertFalse(manager.hasLifetimeEntitlement)
        XCTAssertEqual(manager.state, .idle)
    }

    func testFailedPurchaseDoesNotUnlockLifetimeAccess() async {
        let manager = PurchaseManager(
            client: FakeStoreKitClient(purchaseResult: .failed(TestError.failed))
        )

        await manager.purchase()

        XCTAssertFalse(manager.hasLifetimeEntitlement)
        XCTAssertEqual(manager.state, .failed)
    }

    func testPrepareExposesAppOwnedLocalizedDisplayPrice() async {
        let manager = PurchaseManager(
            client: FakeStoreKitClient(
                product: PurchaseProduct(
                    id: PurchaseManager.lifetimeProductID,
                    displayPrice: "€2.99"
                )
            )
        )

        await manager.prepare()

        XCTAssertEqual(manager.product?.displayPrice, "€2.99")
    }

    func testVerifiedTransactionUpdateUnlocksLifetimeAccess() async {
        let manager = PurchaseManager(
            client: FakeStoreKitClient(
                updates: [.verified(productID: PurchaseManager.lifetimeProductID)]
            )
        )

        await manager.prepare()
        for _ in 0..<5 where !manager.hasLifetimeEntitlement {
            await Task.yield()
        }

        XCTAssertTrue(manager.hasLifetimeEntitlement)
    }
}

private enum TestError: Error {
    case failed
}

@MainActor
final class FakeStoreKitClient: StoreKitClient {
    let product: PurchaseProduct?
    let currentEntitlement: StoreKitTransaction?
    let purchaseResult: StoreKitPurchaseResult
    let restoreResult: Result<Void, Error>
    let updates: [StoreKitTransaction]

    init(
        product: PurchaseProduct? = PurchaseProduct(
            id: "com.hangten.training.lifetime",
            displayPrice: "$2.99"
        ),
        currentEntitlement: StoreKitTransaction? = nil,
        purchaseResult: StoreKitPurchaseResult = .userCancelled,
        restoreResult: Result<Void, Error> = .success(()),
        updates: [StoreKitTransaction] = []
    ) {
        self.product = product
        self.currentEntitlement = currentEntitlement
        self.purchaseResult = purchaseResult
        self.restoreResult = restoreResult
        self.updates = updates
    }

    func loadProduct(id: String) async throws -> PurchaseProduct? {
        product
    }

    func currentEntitlement(for productID: String) async throws -> StoreKitTransaction? {
        currentEntitlement
    }

    func purchase(productID: String) async -> StoreKitPurchaseResult {
        purchaseResult
    }

    func restorePurchases() async throws {
        try restoreResult.get()
    }

    func transactionUpdates() -> AsyncStream<StoreKitTransaction> {
        AsyncStream { continuation in
            updates.forEach { _ = continuation.yield($0) }
            continuation.finish()
        }
    }

    func finish(_ transaction: StoreKitTransaction) async {}
}
