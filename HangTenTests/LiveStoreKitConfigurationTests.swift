import StoreKitTest
import XCTest
@testable import HangTen

@MainActor
final class LiveStoreKitConfigurationTests: XCTestCase {
    func testCheckedInConfigurationLoadsLocalizedProductAndLivePurchaseUnlocksWorkout() async throws {
        let session = try makeSession()
        defer { session.clearTransactions() }
        let (accessStore, manager, defaults) = makeLockedAccessBoundary(suite: #function)
        defer { defaults.removePersistentDomain(forName: #function) }

        XCTAssertEqual(accessStore.launchDecision(hasLifetimeEntitlement: manager.hasLifetimeEntitlement), .requiresPurchase)

        await manager.prepare()

        let product = try XCTUnwrap(manager.product)
        XCTAssertEqual(product.id, PurchaseManager.lifetimeProductID)
        XCTAssertEqual(product.displayPrice, "$2.99")

        await manager.purchase()

        XCTAssertTrue(manager.hasLifetimeEntitlement)
        XCTAssertEqual(manager.state, .idle)
        XCTAssertEqual(accessStore.launchDecision(hasLifetimeEntitlement: manager.hasLifetimeEntitlement), .allowed)
    }

    func testCheckedInConfigurationLiveRestoreRehydratesEntitlementAndUnlocksWorkout() async throws {
        let session = try makeSession()
        defer { session.clearTransactions() }
        _ = try await session.buyProduct(identifier: PurchaseManager.lifetimeProductID)
        let (accessStore, manager, defaults) = makeLockedAccessBoundary(suite: #function)
        defer { defaults.removePersistentDomain(forName: #function) }

        XCTAssertEqual(accessStore.launchDecision(hasLifetimeEntitlement: manager.hasLifetimeEntitlement), .requiresPurchase)

        await manager.restore()

        XCTAssertTrue(manager.hasLifetimeEntitlement)
        XCTAssertEqual(manager.state, .idle)
        XCTAssertEqual(accessStore.launchDecision(hasLifetimeEntitlement: manager.hasLifetimeEntitlement), .allowed)
    }

    private func makeSession() throws -> SKTestSession {
        let configurationURL = try XCTUnwrap(
            Bundle(for: Self.self).url(forResource: "HangTen", withExtension: "storekit")
        )
        let session = try SKTestSession(contentsOf: configurationURL)
        session.resetToDefaultState()
        session.clearTransactions()
        session.disableDialogs = true
        session.locale = Locale(identifier: "en_US")
        return session
    }

    private func makeLockedAccessBoundary(suite: String) -> (WorkoutAccessStore, PurchaseManager, UserDefaults) {
        let defaults = UserDefaults(suiteName: suite)!
        defaults.removePersistentDomain(forName: suite)
        let accessStore = WorkoutAccessStore(defaults: defaults)
        accessStore.recordSavedFreeWorkout(hasLifetimeEntitlement: false)
        accessStore.recordSavedFreeWorkout(hasLifetimeEntitlement: false)
        let manager = PurchaseManager(client: LiveStoreKitClient())
        return (accessStore, manager, defaults)
    }
}
