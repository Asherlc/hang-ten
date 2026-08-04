import XCTest
@testable import HangTen

final class LocalWorkoutHistoryStoreTests: XCTestCase {
    private var suiteNames: [String] = []

    deinit {}

    override func tearDown() {
        for suiteName in suiteNames {
            UserDefaults().removePersistentDomain(forName: suiteName)
        }
        suiteNames.removeAll()
        super.tearDown()
    }

    func testRecordsRoundTripThroughUserDefaults() {
        let defaults = makeDefaults()
        let record = PendingWorkoutRecord(
            id: UUID(),
            planTitle: "Metolius Sequence",
            startDate: startDate,
            endDate: endDate,
            healthUploadAttempted: false,
            healthWorkoutUUID: nil
        )

        let firstStore = LocalWorkoutHistoryStore(defaults: defaults)
        firstStore.replace([record])

        XCTAssertEqual(LocalWorkoutHistoryStore(defaults: defaults).load(), [record])
    }

    func testReplacingWithEmptyArrayClearsPersistedRecords() {
        let defaults = makeDefaults()
        let record = PendingWorkoutRecord(
            id: UUID(),
            planTitle: "Metolius Sequence",
            startDate: startDate,
            endDate: endDate,
            healthUploadAttempted: false,
            healthWorkoutUUID: nil
        )
        let store = LocalWorkoutHistoryStore(defaults: defaults)

        store.replace([record])
        store.replace([])

        XCTAssertEqual(store.load(), [])
    }

    func testMalformedPayloadLoadsAsEmptyRecords() {
        let defaults = makeDefaults()
        defaults.set(Data("not-json".utf8), forKey: LocalWorkoutHistoryStore.defaultKey)

        XCTAssertEqual(LocalWorkoutHistoryStore(defaults: defaults).load(), [])
    }

    private func makeDefaults() -> UserDefaults {
        let suiteName = "HangTenTests.LocalHistory.\(UUID().uuidString)"
        suiteNames.append(suiteName)
        return UserDefaults(suiteName: suiteName)!
    }

    private var startDate: Date {
        Date(timeIntervalSince1970: 1_700_000_000)
    }

    private var endDate: Date {
        Date(timeIntervalSince1970: 1_700_003_600)
    }
}
