import HealthKit
import XCTest
@testable import HangTen

final class HealthKitServiceTests: XCTestCase {
    private let startDate = Date(timeIntervalSinceReferenceDate: 1_000)
    private let endDate = Date(timeIntervalSinceReferenceDate: 1_600)

    func testHealthKitWorkoutMapsHangTenMetadataAndSessionID() {
        let sessionID = UUID(uuidString: "AAAAAAAA-AAAA-AAAA-AAAA-AAAAAAAAAAAA")!
        let workout = workout(
            metadata: [
                HKMetadataKeyWorkoutBrandName: HangTenHealthMetadata.brandName,
                HangTenHealthMetadata.planNameKey: "Metolius Sequence",
                HangTenHealthMetadata.sessionIDKey: sessionID.uuidString
            ]
        )

        let record = HealthKitService.record(from: workout)

        XCTAssertEqual(record.id, workout.uuid)
        XCTAssertEqual(record.startDate, startDate)
        XCTAssertEqual(record.endDate, endDate)
        XCTAssertEqual(record.brandName, HangTenHealthMetadata.brandName)
        XCTAssertEqual(record.planTitle, "Metolius Sequence")
        XCTAssertEqual(record.sessionID, sessionID)
        XCTAssertTrue(record.isHangTen)
    }

    func testHealthKitWorkoutWithoutSessionIDRemainsLegacyHangTenRecord() {
        let record = HealthKitService.record(from: workout(
            metadata: [
                HKMetadataKeyWorkoutBrandName: HangTenHealthMetadata.brandName,
                HangTenHealthMetadata.planNameKey: "Legacy Sequence"
            ]
        ))

        XCTAssertNil(record.sessionID)
        XCTAssertTrue(record.isHangTen)
    }

    func testHealthKitWorkoutFromAnotherBrandIsNotHangTen() {
        let record = HealthKitService.record(from: workout(
            metadata: [
                HKMetadataKeyWorkoutBrandName: "Other App",
                HangTenHealthMetadata.planNameKey: "Metolius Sequence"
            ]
        ))

        XCTAssertFalse(record.isHangTen)
    }

    func testNonFunctionalStrengthHealthKitWorkoutIsNotHangTen() {
        let record = HealthKitService.record(from: workout(
            activityType: .running,
            metadata: [
                HKMetadataKeyWorkoutBrandName: HangTenHealthMetadata.brandName,
                HangTenHealthMetadata.planNameKey: "Metolius Sequence"
            ]
        ))

        XCTAssertFalse(record.isHangTen)
    }

    private func workout(
        activityType: HKWorkoutActivityType = .functionalStrengthTraining,
        metadata: [String: Any]
    ) -> HKWorkout {
        HKWorkout(
            activityType: activityType,
            start: startDate,
            end: endDate,
            duration: endDate.timeIntervalSince(startDate),
            totalEnergyBurned: nil,
            totalDistance: nil,
            metadata: metadata
        )
    }
}
