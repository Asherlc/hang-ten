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
            purchaseResult: .success(
                .unverified(productID: PurchaseManager.lifetimeProductID, transactionID: 200)
            )
        )
        let manager = PurchaseManager(client: client)

        await manager.purchase()

        XCTAssertFalse(manager.hasLifetimeEntitlement)
        XCTAssertEqual(manager.state, .failed)
        XCTAssertEqual(client.finishedTransactionIDs, [])
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

    func testRevokedCurrentEntitlementDoesNotUnlockLifetimeAccess() async {
        let manager = PurchaseManager(
            client: FakeStoreKitClient(
                currentEntitlement: .revoked(productID: PurchaseManager.lifetimeProductID)
            )
        )

        await manager.prepare()

        XCTAssertFalse(manager.hasLifetimeEntitlement)
        XCTAssertEqual(manager.state, .idle)
    }

    func testVerifiedPurchaseUnlocksLifetimeAccess() async {
        let client = FakeStoreKitClient(
            purchaseResult: .success(
                .verified(productID: PurchaseManager.lifetimeProductID, transactionID: 100)
            )
        )
        let manager = PurchaseManager(client: client)

        await manager.purchase()

        XCTAssertTrue(manager.hasLifetimeEntitlement)
        XCTAssertEqual(manager.state, .idle)
        XCTAssertEqual(client.finishedTransactionIDs, [100])
    }

    func testCurrentEntitlementAbsenceClearsPreviouslyGrantedLifetimeAccess() async {
        let client = FakeStoreKitClient(
            currentEntitlement: .verified(
                productID: PurchaseManager.lifetimeProductID,
                transactionID: 300
            )
        )
        let manager = PurchaseManager(client: client)

        await manager.prepare()
        client.currentEntitlement = nil
        await manager.restore()

        XCTAssertFalse(manager.hasLifetimeEntitlement)
        XCTAssertEqual(manager.state, .idle)
    }

    func testPrepareRefreshesVerifiedEntitlementWhenProductMetadataLoadFails() async {
        let manager = PurchaseManager(
            client: FakeStoreKitClient(
                currentEntitlement: .verified(
                    productID: PurchaseManager.lifetimeProductID,
                    transactionID: 400
                ),
                productLoadError: TestError.failed
            )
        )

        await manager.prepare()

        XCTAssertTrue(manager.hasLifetimeEntitlement)
        XCTAssertEqual(manager.state, .failed)
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

    func testRevokedLifetimeTransactionUpdateClearsAccess() async {
        let client = FakeStoreKitClient(
            currentEntitlement: .verified(
                productID: PurchaseManager.lifetimeProductID,
                transactionID: 500
            )
        )
        let manager = PurchaseManager(client: client)

        await manager.prepare()
        await waitForUpdateSubscription(from: client)
        client.sendUpdate(
            .revoked(productID: PurchaseManager.lifetimeProductID, transactionID: 501)
        )
        await waitForEntitlementChange(in: manager, expected: false)

        XCTAssertFalse(manager.hasLifetimeEntitlement)
        XCTAssertEqual(manager.state, .idle)
        XCTAssertEqual(client.finishedTransactionIDs, [500, 501])
    }

    func testUnrelatedVerifiedTransactionUpdateIsIgnoredAndNotFinished() async {
        let client = FakeStoreKitClient()
        let manager = PurchaseManager(client: client)

        await manager.prepare()
        await waitForUpdateSubscription(from: client)
        client.sendUpdate(.verified(productID: "com.hangten.training.other", transactionID: 600))
        await Task.yield()

        XCTAssertFalse(manager.hasLifetimeEntitlement)
        XCTAssertFalse(client.finishedTransactionIDs.contains(600))
    }

    private func waitForUpdateSubscription(from client: FakeStoreKitClient) async {
        for _ in 0..<10 where !client.isObservingUpdates {
            await Task.yield()
        }
        XCTAssertTrue(client.isObservingUpdates)
    }

    private func waitForEntitlementChange(in manager: PurchaseManager, expected: Bool) async {
        for _ in 0..<10 where manager.hasLifetimeEntitlement != expected {
            await Task.yield()
        }
    }
}

private enum TestError: Error {
    case failed
}

@MainActor
final class FakeStoreKitClient: StoreKitClient {
    let product: PurchaseProduct?
    var currentEntitlement: StoreKitTransaction?
    let purchaseResult: StoreKitPurchaseResult
    let restoreResult: Result<Void, Error>
    let updates: [StoreKitTransaction]
    let productLoadError: Error?
    private(set) var finishedTransactionIDs: [UInt64] = []
    private(set) var isObservingUpdates = false
    private var updateContinuation: AsyncStream<StoreKitTransaction>.Continuation?

    init(
        product: PurchaseProduct? = PurchaseProduct(
            id: "com.hangten.training.lifetime",
            displayPrice: "$2.99"
        ),
        currentEntitlement: StoreKitTransaction? = nil,
        purchaseResult: StoreKitPurchaseResult = .userCancelled,
        restoreResult: Result<Void, Error> = .success(()),
        updates: [StoreKitTransaction] = [],
        productLoadError: Error? = nil
    ) {
        self.product = product
        self.currentEntitlement = currentEntitlement
        self.purchaseResult = purchaseResult
        self.restoreResult = restoreResult
        self.updates = updates
        self.productLoadError = productLoadError
    }

    func loadProduct(id: String) async throws -> PurchaseProduct? {
        if let productLoadError {
            throw productLoadError
        }
        return product
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
            isObservingUpdates = true
            updateContinuation = continuation
            updates.forEach { _ = continuation.yield($0) }
        }
    }

    func sendUpdate(_ transaction: StoreKitTransaction) {
        updateContinuation?.yield(transaction)
    }

    func finish(_ transaction: StoreKitTransaction) async {
        finishedTransactionIDs.append(transaction.transactionID)
    }

    deinit {
        updateContinuation?.finish()
    }
}
