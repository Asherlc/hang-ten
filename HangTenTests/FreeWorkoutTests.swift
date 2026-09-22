import XCTest
@testable import HangTen

final class FreeWorkoutTests: XCTestCase {
    private func makePlan(isFreeWorkout: Bool = false) -> TrainingPlan {
        TrainingPlan(
            id: "free.test",
            title: "Free workout",
            subtitle: "Built on the fly",
            level: "Custom",
            sourceLabel: "Created in Hang Ten",
            sourceURL: nil,
            provenance: .custom,
            boardID: nil,
            steps: [],
            isFreeWorkout: isFreeWorkout
        )
    }

    func testTrainingPlanDefaultsToNonFreeWorkout() {
        let plan = TrainingPlan(
            id: "free.test",
            title: "Free workout",
            subtitle: "Built on the fly",
            level: "Custom",
            sourceLabel: "Created in Hang Ten",
            sourceURL: nil,
            provenance: .custom,
            boardID: nil,
            steps: []
        )
        XCTAssertFalse(plan.isFreeWorkout)
    }

    func testTrainingPlanCanBeMarkedFreeWorkout() {
        XCTAssertTrue(makePlan(isFreeWorkout: true).isFreeWorkout)
    }
}
