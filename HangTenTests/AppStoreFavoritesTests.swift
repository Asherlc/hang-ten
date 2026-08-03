import Combine
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

    func testRemovingFavoriteEmitsOneStoreChange() {
        let defaults = UserDefaults(suiteName: "AppStoreFavoritesTests.removalEmission")!
        defaults.removePersistentDomain(forName: "AppStoreFavoritesTests.removalEmission")
        defer { defaults.removePersistentDomain(forName: "AppStoreFavoritesTests.removalEmission") }

        let plan = PlanCatalog.all[0]
        defaults.set([plan.id], forKey: "favoritePlanIDs")
        let store = AppStore(userDefaults: defaults)
        var changeCount = 0
        let cancellable = store.objectWillChange.sink { _ in
            changeCount += 1
        }

        store.toggleFavorite(plan)

        XCTAssertEqual(changeCount, 1)
        XCTAssertFalse(store.isFavorite(plan))
        _ = cancellable
    }

    func testFavoritePlansUseCompatiblePlanOrderAndIgnoreUnknownIDs() {
        let defaults = UserDefaults(suiteName: "AppStoreFavoritesTests.order")!
        defaults.removePersistentDomain(forName: "AppStoreFavoritesTests.order")
        defer { defaults.removePersistentDomain(forName: "AppStoreFavoritesTests.order") }

        let fixtureStore = AppStore(userDefaults: defaults)
        let expectedPlans = Array(fixtureStore.plans.prefix(3))
        let scrambledFavoriteIDs = Array(expectedPlans.map(\.id).reversed()) + ["missing.plan"]
        defaults.set(scrambledFavoriteIDs, forKey: "favoritePlanIDs")

        let store = AppStore(userDefaults: defaults)

        XCTAssertEqual(store.favoritePlans.map(\.id), expectedPlans.map(\.id))
        XCTAssertFalse(store.favoritePlans.contains { $0.id == "missing.plan" })
    }
}
