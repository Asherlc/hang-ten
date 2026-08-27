import XCTest
@testable import HangTen

final class WorkoutAccessStoreTests: XCTestCase {
    func testFirstAndSecondSavedWorkoutsRemainAvailableButThirdRequiresPurchase() {
        let defaults = UserDefaults(suiteName: "WorkoutAccessStoreTests.boundary")!
        defaults.removePersistentDomain(forName: "WorkoutAccessStoreTests.boundary")
        let store = WorkoutAccessStore(defaults: defaults)

        XCTAssertEqual(store.launchDecision(hasLifetimeEntitlement: false), .allowed)
        store.recordSavedFreeWorkout(hasLifetimeEntitlement: false)
        XCTAssertEqual(store.launchDecision(hasLifetimeEntitlement: false), .allowed)
        store.recordSavedFreeWorkout(hasLifetimeEntitlement: false)
        XCTAssertEqual(store.launchDecision(hasLifetimeEntitlement: false), .requiresPurchase)
    }

    func testLifetimeEntitlementAllowsWorkoutWithoutConsumingFreeCredit() {
        let defaults = UserDefaults(suiteName: "WorkoutAccessStoreTests.entitled")!
        defaults.removePersistentDomain(forName: "WorkoutAccessStoreTests.entitled")
        let store = WorkoutAccessStore(defaults: defaults)

        store.recordSavedFreeWorkout(hasLifetimeEntitlement: true)

        XCTAssertEqual(store.freeWorkoutsUsed, 0)
        XCTAssertEqual(store.launchDecision(hasLifetimeEntitlement: true), .allowed)
    }

    func testSavedFreeWorkoutCountPersistsAcrossStoreInstances() {
        let suiteName = "WorkoutAccessStoreTests.persistence"
        let defaults = UserDefaults(suiteName: suiteName)!
        defaults.removePersistentDomain(forName: suiteName)
        defer { defaults.removePersistentDomain(forName: suiteName) }
        let firstStore = WorkoutAccessStore(defaults: defaults)

        firstStore.recordSavedFreeWorkout(hasLifetimeEntitlement: false)

        let reloadedStore = WorkoutAccessStore(
            defaults: UserDefaults(suiteName: suiteName)!
        )
        XCTAssertEqual(reloadedStore.freeWorkoutsUsed, 1)
        XCTAssertEqual(
            reloadedStore.launchDecision(hasLifetimeEntitlement: false),
            .allowed
        )
    }
}
