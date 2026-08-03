import XCTest
@testable import HangTen

final class AppStoreFavoritesTests: XCTestCase {
    func testTogglePersistsAcrossStoreInstancesAndCanRemoveFavorite() {
        let defaults = UserDefaults(suiteName: "AppStoreFavoritesTests.toggle")!
        defaults.removePersistentDomain(forName: "AppStoreFavoritesTests.toggle")
        defer { defaults.removePersistentDomain(forName: "AppStoreFavoritesTests.toggle") }

        let plan = PlanCatalog.all[0]
        let store = AppStore(userDefaults: defaults)

        XCTAssertFalse(store.isFavorite(plan))
        store.toggleFavorite(plan)
        XCTAssertTrue(store.isFavorite(plan))

        let reloadedStore = AppStore(userDefaults: defaults)
        XCTAssertTrue(reloadedStore.isFavorite(plan))

        reloadedStore.toggleFavorite(plan)
        XCTAssertFalse(reloadedStore.isFavorite(plan))

        let reloadedAfterRemovalStore = AppStore(userDefaults: defaults)
        XCTAssertFalse(reloadedAfterRemovalStore.isFavorite(plan))
    }

    func testFavoritePlansUseCompatiblePlanOrderAndIgnoreUnknownIDs() {
        let defaults = UserDefaults(suiteName: "AppStoreFavoritesTests.order")!
        defaults.removePersistentDomain(forName: "AppStoreFavoritesTests.order")
        defer { defaults.removePersistentDomain(forName: "AppStoreFavoritesTests.order") }

        let expectedPlans = Array(PlanCatalog.all.prefix(3)).reversed()
        defaults.set(expectedPlans.map(\.id) + ["missing.plan"], forKey: "favoritePlanIDs")

        let store = AppStore(userDefaults: defaults)

        XCTAssertEqual(store.favoritePlans.map(\.id), expectedPlans.reversed().map(\.id))
        XCTAssertFalse(store.favoritePlans.contains { $0.id == "missing.plan" })
    }
}
