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

final class FreeWorkoutDraftTests: XCTestCase {

    func testDraftStoreRoundTrip() {
        let defaults = UserDefaults(suiteName: "FreeWorkoutDraftTests")!
        defaults.removePersistentDomain(forName: "FreeWorkoutDraftTests")
        var draft = FreeWorkoutDraft(title: "Evening session", exercises: [])
        draft.exercises.append(FreeWorkoutExerciseDraft(kind: .hang, workDuration: 7, restDuration: 53))
        FreeWorkoutDraftStore.save(draft, defaults: defaults)
        XCTAssertEqual(FreeWorkoutDraftStore.load(defaults: defaults), draft)
        defaults.removePersistentDomain(forName: "FreeWorkoutDraftTests")
    }
}
