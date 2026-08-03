import HealthKit
import XCTest
@testable import HangTen

final class HealthKitServiceTests: XCTestCase {
    private let workoutID = UUID(uuidString: "BBBBBBBB-BBBB-BBBB-BBBB-BBBBBBBBBBBB")!
    private let startDate = Date(timeIntervalSinceReferenceDate: 1_000)
    private let endDate = Date(timeIntervalSinceReferenceDate: 1_600)

    func testMapperPreservesHangTenMetadataAndSessionID() {
        let sessionID = UUID(uuidString: "AAAAAAAA-AAAA-AAAA-AAAA-AAAAAAAAAAAA")!
        let record = record(
            metadata: [
                HKMetadataKeyWorkoutBrandName: HangTenHealthMetadata.brandName,
                HangTenHealthMetadata.planNameKey: "Metolius Sequence",
                HangTenHealthMetadata.sessionIDKey: sessionID.uuidString
            ]
        )

        XCTAssertEqual(record.id, workoutID)
        XCTAssertEqual(record.startDate, startDate)
        XCTAssertEqual(record.endDate, endDate)
        XCTAssertEqual(record.brandName, HangTenHealthMetadata.brandName)
        XCTAssertEqual(record.planTitle, "Metolius Sequence")
        XCTAssertEqual(record.sessionID, sessionID)
        XCTAssertTrue(record.isHangTen)
    }

    func testMapperKeepsLegacyHangTenRecordWithoutSessionID() {
        let record = record(
            metadata: [
                HKMetadataKeyWorkoutBrandName: HangTenHealthMetadata.brandName,
                HangTenHealthMetadata.planNameKey: "Legacy Sequence"
            ]
        )

        XCTAssertNil(record.sessionID)
        XCTAssertTrue(record.isHangTen)
    }

    func testMapperRejectsWorkoutFromAnotherBrand() {
        let record = record(
            metadata: [
                HKMetadataKeyWorkoutBrandName: "Other App",
                HangTenHealthMetadata.planNameKey: "Metolius Sequence"
            ]
        )

        XCTAssertFalse(record.isHangTen)
    }

    func testMapperRejectsNonFunctionalStrengthWorkout() {
        let record = record(
            activityType: .running,
            metadata: [
                HKMetadataKeyWorkoutBrandName: HangTenHealthMetadata.brandName,
                HangTenHealthMetadata.planNameKey: "Metolius Sequence"
            ]
        )

        XCTAssertFalse(record.isHangTen)
    }

    func testHangTenWorkoutPredicateMatchesOnlyFunctionalStrengthTraining() {
        let predicate = HealthKitService.hangTenWorkoutPredicate()

        XCTAssertTrue(predicate.evaluate(with: [
            "workoutActivityType": HKWorkoutActivityType.functionalStrengthTraining.rawValue
        ]))
        XCTAssertFalse(predicate.evaluate(with: [
            "workoutActivityType": HKWorkoutActivityType.running.rawValue
        ]))
    }

    private func record(
        activityType: HKWorkoutActivityType = .functionalStrengthTraining,
        metadata: [String: Any]
    ) -> HealthWorkoutRecord {
        HealthKitService.record(
            id: workoutID,
            activityTypeRawValue: activityType.rawValue,
            metadata: metadata,
            startDate: startDate,
            endDate: endDate
        )
    }
}
