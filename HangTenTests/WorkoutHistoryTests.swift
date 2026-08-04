import HealthKit
import XCTest
@testable import HangTen

final class WorkoutHistoryTests: XCTestCase {
    private let startDate = Date(timeIntervalSinceReferenceDate: 1_000)
    private let endDate = Date(timeIntervalSinceReferenceDate: 1_600)

    deinit {}

    private var healthRecord: HealthWorkoutRecord {
        HealthWorkoutRecord(
            id: UUID(uuidString: "AAAAAAAA-AAAA-AAAA-AAAA-AAAAAAAAAAAA")!,
            activityTypeRawValue: HKWorkoutActivityType.functionalStrengthTraining.rawValue,
            brandName: HangTenHealthMetadata.brandName,
            planTitle: "Metolius Sequence",
            sessionID: nil,
            startDate: startDate,
            endDate: endDate
        )
    }

    func testOnlyHangTenFunctionalStrengthRecordsAreAccepted() {
        let accepted = healthRecord
        let otherBrand = accepted.with(brandName: "Other App")
        let otherActivity = accepted.with(
            activityTypeRawValue: HKWorkoutActivityType.running.rawValue
        )
        let missingPlan = accepted.with(planTitle: nil)

        XCTAssertTrue(accepted.isHangTen)
        XCTAssertFalse(otherBrand.isHangTen)
        XCTAssertFalse(otherActivity.isHangTen)
        XCTAssertFalse(missingPlan.isHangTen)
    }

    func testWhitespaceOnlyPlanMetadataIsRejected() {
        XCTAssertFalse(healthRecord.with(planTitle: " \n\t ").isHangTen)
    }

    func testEntryPreservesHealthWorkoutIdentityAndDates() {
        let entry = WorkoutHistoryMatcher.entry(from: healthRecord)

        XCTAssertEqual(entry.id, healthRecord.id)
        XCTAssertEqual(entry.planTitle, "Metolius Sequence")
        XCTAssertEqual(entry.startDate, startDate)
        XCTAssertEqual(entry.endDate, endDate)
        XCTAssertFalse(entry.isPendingLocalRecord)
    }

    func testLegacyRecordWithoutSessionIDIsNormalizedWhenPlanTitleExists() {
        let entry = WorkoutHistoryMatcher.entry(from: healthRecord.with(planTitle: "  Legacy Plan  "))

        XCTAssertEqual(entry.planTitle, "Legacy Plan")
    }

    func testMatchingUsesSessionIDStoredUUIDOrLegacyWorkoutDetails() {
        let localID = UUID(uuidString: "BBBBBBBB-BBBB-BBBB-BBBB-BBBBBBBBBBBB")!
        let local = PendingWorkoutRecord(
            id: localID,
            planTitle: "Metolius Sequence",
            startDate: startDate,
            endDate: endDate,
            healthUploadAttempted: true,
            healthWorkoutUUID: nil
        )

        XCTAssertEqual(
            WorkoutHistoryMatcher.matchingHealthWorkout(
                for: local,
                in: [healthRecord.with(sessionID: localID)]
            )?.id,
            healthRecord.id
        )

        let storedUUIDMatch = local.with(healthWorkoutUUID: healthRecord.id)
        XCTAssertEqual(
            WorkoutHistoryMatcher.matchingHealthWorkout(for: storedUUIDMatch, in: [healthRecord])?.id,
            healthRecord.id
        )

        XCTAssertEqual(
            WorkoutHistoryMatcher.matchingHealthWorkout(for: local, in: [healthRecord])?.id,
            healthRecord.id
        )
    }

    func testLegacyMatchingNormalizesLocalAndHealthPlanTitles() {
        let local = PendingWorkoutRecord(
            id: UUID(),
            planTitle: "  Metolius Sequence  ",
            startDate: startDate,
            endDate: endDate,
            healthUploadAttempted: true,
            healthWorkoutUUID: nil
        )

        XCTAssertEqual(
            WorkoutHistoryMatcher.matchingHealthWorkout(
                for: local,
                in: [healthRecord.with(planTitle: " Metolius Sequence ")]
            )?.id,
            healthRecord.id
        )
    }

    func testLegacyPendingWorkoutRecordPayloadDecodesWithoutActivityContext() throws {
        let data = Data("""
        [{
          "id": "00000000-0000-0000-0000-000000000123",
          "planTitle": "Legacy Plan",
          "startDate": 700000000,
          "endDate": 700000600,
          "healthUploadAttempted": false,
          "healthWorkoutUUID": null
        }]
        """.utf8)

        let records = try JSONDecoder().decode([PendingWorkoutRecord].self, from: data)

        XCTAssertEqual(records.count, 1)
        XCTAssertEqual(records[0].planTitle, "Legacy Plan")
        XCTAssertNil(records[0].activityContext)
        XCTAssertTrue(records[0].shouldUploadToHealthKit)
    }

    func testSnapshotSortsDeduplicatesAndAddsUnmatchedLocalRecords() {
        let newerID = UUID(uuidString: "DDDDDDDD-DDDD-DDDD-DDDD-DDDDDDDDDDDD")!
        let newer = healthRecord.with(
            id: newerID,
            startDate: Date(timeIntervalSinceReferenceDate: 2_000),
            endDate: Date(timeIntervalSinceReferenceDate: 2_600)
        )
        let local = PendingWorkoutRecord(
            id: UUID(uuidString: "EEEEEEEE-EEEE-EEEE-EEEE-EEEEEEEEEEEE")!,
            planTitle: "Pending Plan",
            startDate: Date(timeIntervalSinceReferenceDate: 3_000),
            endDate: Date(timeIntervalSinceReferenceDate: 3_600),
            healthUploadAttempted: true,
            healthWorkoutUUID: nil
        )

        let snapshot = WorkoutHistoryMatcher.snapshot(
            healthRecords: [healthRecord, healthRecord, newer],
            localRecords: [local],
            healthQuerySucceeded: true
        )

        XCTAssertEqual(snapshot.source, .healthKit)
        XCTAssertEqual(snapshot.entries.map(\.id), [local.id, newer.id, healthRecord.id])
        XCTAssertEqual(snapshot.entries.map(\.isPendingLocalRecord), [true, false, false])
        XCTAssertEqual(snapshot.sessionCount, 3)
        XCTAssertEqual(snapshot.latestSessionTitle, "Pending Plan")
    }

    func testSnapshotDeduplicatesHealthRecordsBySessionIDKeepingNewestRecord() {
        let sessionID = UUID(uuidString: "FFFFFFFF-FFFF-FFFF-FFFF-FFFFFFFFFFFF")!
        let older = healthRecord
            .with(
                id: UUID(uuidString: "11111111-1111-1111-1111-111111111111")!,
                startDate: Date(timeIntervalSinceReferenceDate: 1_000),
                endDate: Date(timeIntervalSinceReferenceDate: 1_600)
            )
            .with(sessionID: sessionID)
        let newer = healthRecord
            .with(
                id: UUID(uuidString: "22222222-2222-2222-2222-222222222222")!,
                startDate: Date(timeIntervalSinceReferenceDate: 2_000),
                endDate: Date(timeIntervalSinceReferenceDate: 2_600)
            )
            .with(sessionID: sessionID)
            .with(planTitle: "Newest Plan")

        let snapshot = WorkoutHistoryMatcher.snapshot(
            healthRecords: [older, newer],
            localRecords: [],
            healthQuerySucceeded: true
        )

        XCTAssertEqual(snapshot.entries.count, 1)
        XCTAssertEqual(snapshot.entries.first?.id, newer.id)
        XCTAssertEqual(snapshot.latestSessionTitle, "Newest Plan")
    }

    func testUnavailableHealthStoreKeepsLocalHistory() {
        let local = PendingWorkoutRecord(
            id: UUID(), planTitle: "Pending Plan", startDate: startDate, endDate: endDate,
            healthUploadAttempted: false, healthWorkoutUUID: nil
        )

        let snapshot = WorkoutHistoryMatcher.snapshot(
            healthRecords: [], localRecords: [local], healthQuerySucceeded: false
        )

        XCTAssertEqual(snapshot.source, .localFallback)
        XCTAssertEqual(snapshot.entries.map(\.id), [local.id])
    }

    func testEmptySuccessfulHealthQueryWithoutLocalHistoryIsEmptyHealthKitSnapshot() {
        let snapshot = WorkoutHistoryMatcher.snapshot(
            healthRecords: [], localRecords: [], healthQuerySucceeded: true
        )

        XCTAssertEqual(snapshot, WorkoutHistorySnapshot(entries: [], source: .healthKit))
    }

    func testSuccessfulFilteredHealthQueryWithLocalHistoryUsesLocalFallback() {
        let local = PendingWorkoutRecord(
            id: UUID(), planTitle: "Pending Plan", startDate: startDate, endDate: endDate,
            healthUploadAttempted: true, healthWorkoutUUID: nil
        )
        let filteredRecord = healthRecord.with(brandName: "Other App")

        let snapshot = WorkoutHistoryMatcher.snapshot(
            healthRecords: [filteredRecord],
            localRecords: [local],
            healthQuerySucceeded: true
        )

        XCTAssertEqual(snapshot.source, .localFallback)
        XCTAssertEqual(snapshot.entries.map(\.id), [local.id])
    }
}

private extension HealthWorkoutRecord {
    func with(brandName: String) -> HealthWorkoutRecord {
        HealthWorkoutRecord(
            id: id, activityTypeRawValue: activityTypeRawValue, brandName: brandName,
            planTitle: planTitle, sessionID: sessionID, startDate: startDate, endDate: endDate
        )
    }

    func with(activityTypeRawValue: UInt) -> HealthWorkoutRecord {
        HealthWorkoutRecord(
            id: id, activityTypeRawValue: activityTypeRawValue, brandName: brandName,
            planTitle: planTitle, sessionID: sessionID, startDate: startDate, endDate: endDate
        )
    }

    func with(planTitle: String?) -> HealthWorkoutRecord {
        HealthWorkoutRecord(
            id: id, activityTypeRawValue: activityTypeRawValue, brandName: brandName,
            planTitle: planTitle, sessionID: sessionID, startDate: startDate, endDate: endDate
        )
    }

    func with(sessionID: UUID?) -> HealthWorkoutRecord {
        HealthWorkoutRecord(
            id: id, activityTypeRawValue: activityTypeRawValue, brandName: brandName,
            planTitle: planTitle, sessionID: sessionID, startDate: startDate, endDate: endDate
        )
    }

    func with(id: UUID, startDate: Date, endDate: Date) -> HealthWorkoutRecord {
        HealthWorkoutRecord(
            id: id, activityTypeRawValue: activityTypeRawValue, brandName: brandName,
            planTitle: planTitle, sessionID: sessionID, startDate: startDate, endDate: endDate
        )
    }
}

private extension PendingWorkoutRecord {
    func with(healthWorkoutUUID: UUID?) -> PendingWorkoutRecord {
        PendingWorkoutRecord(
            id: id,
            planTitle: planTitle,
            startDate: startDate,
            endDate: endDate,
            healthUploadAttempted: healthUploadAttempted,
            healthWorkoutUUID: healthWorkoutUUID
        )
    }
}
