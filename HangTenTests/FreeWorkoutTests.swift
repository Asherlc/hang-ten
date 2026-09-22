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
    func testHangExerciseConvertsToWorkPlusRestStep() {
        var draft = FreeWorkoutDraft(title: "Free workout", exercises: [])
        draft.exercises.append(FreeWorkoutExerciseDraft(
            kind: .hang,
            title: "Jug hang",
            holdKind: .jug,
            workDuration: 10,
            restDuration: 50,
            externalLoadKGF: 5,
            repetitions: nil,
            gripType: .openHand
        ))
        let plan = draft.trainingPlan()
        XCTAssertTrue(plan.isFreeWorkout)
        XCTAssertEqual(plan.steps.count, 1)
        let step = plan.steps[0]
        XCTAssertEqual(step.duration, 60)
        XCTAssertEqual(step.timedWorkDuration, 10)
        XCTAssertEqual(step.phase, .hang)
        XCTAssertEqual(step.externalLoadKGF, 5)
        XCTAssertEqual(step.segments.count, 2)
        XCTAssertEqual(step.segments[0].kind, .work)
        XCTAssertEqual(step.segments[1].kind, .rest)
    }

    func testPullExerciseUsesLoadedLiftSemantics() {
        var draft = FreeWorkoutDraft(title: "Free workout", exercises: [])
        draft.exercises.append(FreeWorkoutExerciseDraft(
            kind: .pull,
            title: "Pull-ups",
            holdKind: .jug,
            workDuration: 25,
            restDuration: 0,
            externalLoadKGF: nil,
            repetitions: 5,
            gripType: nil
        ))
        let step = draft.trainingPlan().steps[0]
        XCTAssertEqual(step.phase, .pull)
        XCTAssertEqual(step.action, .loadedLift)
        XCTAssertEqual(step.repetitions, 5)
        XCTAssertNil(step.repetitions.flatMap { $0 > 0 ? nil : $0 })
        XCTAssertTrue(WorkoutStepSemantics.hasValidActionAndRepetitions(step.action, step.repetitions))
        XCTAssertEqual(step.duration, 25)
        XCTAssertNil(step.timedWorkDuration)
    }

    func testRestExerciseConvertsToRestStep() {
        var draft = FreeWorkoutDraft(title: "Free workout", exercises: [])
        draft.exercises.append(FreeWorkoutExerciseDraft(kind: .rest, workDuration: 0, restDuration: 120))
        let step = draft.trainingPlan().steps[0]
        XCTAssertTrue(step.isRestStep)
        XCTAssertEqual(step.duration, 120)
    }

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
