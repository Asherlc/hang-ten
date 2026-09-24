import XCTest
@testable import HangTen

final class FreeWorkoutSaverTests: XCTestCase {
    func testSaverMapsHangPullRestToValidDefinition() throws {
        let draft = FreeWorkoutDraft(title: "Evening", exercises: [
            FreeWorkoutExerciseDraft(kind: .hang, holdKind: .jug, workDuration: 10, restDuration: 50),
            FreeWorkoutExerciseDraft(kind: .pull, holdKind: .jug, workDuration: 25, restDuration: 60, repetitions: 5),
            FreeWorkoutExerciseDraft(kind: .rest, workDuration: 0, restDuration: 120),
        ])
        let definition = try FreeWorkoutSaver.routineDefinition(from: draft, title: "Evening")
        XCTAssertEqual(definition.targetMode, .generic)
        XCTAssertEqual(definition.steps.count, 3)
        XCTAssertTrue(definition.id.hasPrefix("custom."))
        let issues = CustomRoutineValidator.issues(for: definition, availableBoards: BoardCatalog.all)
        XCTAssertTrue(issues.isEmpty, "Unexpected validation issues: \(issues)")
    }

    func testSaverThrowsWhenNoHoldTargets() {
        let draft = FreeWorkoutDraft(title: "Empty", exercises: [
            FreeWorkoutExerciseDraft(kind: .hang, holdKind: nil, workDuration: 10, restDuration: 0),
        ])
        XCTAssertThrowsError(try FreeWorkoutSaver.routineDefinition(from: draft, title: "Empty")) { error in
            XCTAssertEqual(error as? FreeWorkoutSaverError, .noSavableSteps)
        }
    }

    func testSavedDefinitionResolvesToPlan() throws {
        let draft = FreeWorkoutDraft(title: "Evening", exercises: [
            FreeWorkoutExerciseDraft(kind: .hang, holdKind: .jug, workDuration: 10, restDuration: 50),
        ])
        let definition = try FreeWorkoutSaver.routineDefinition(from: draft, title: "Evening")
        let store = CustomRoutineStore(
            defaults: UserDefaults(suiteName: "FreeWorkoutSaverTests")!,
            availableBoards: BoardCatalog.all
        )
        let plan = try store.plan(for: definition)
        XCTAssertEqual(plan.steps.count, 1)
    }

    func testExecutedDraftReconstructsEditedSteps() {
        let draft = FreeWorkoutDraft(title: "Evening", exercises: [
            FreeWorkoutExerciseDraft(kind: .hang, title: "Jug hang", holdKind: .jug, workDuration: 10, restDuration: 50),
            FreeWorkoutExerciseDraft(kind: .pull, title: "Pull-ups", holdKind: .jug, workDuration: 25, restDuration: 0, repetitions: 5),
        ])
        let executed = FreeWorkoutSaver.executedDraft(from: draft.trainingPlan().steps, title: "Evening")
        XCTAssertEqual(executed.title, "Evening")
        XCTAssertEqual(executed.exercises.count, 2)
        XCTAssertEqual(executed.exercises[0].kind, .hang)
        XCTAssertEqual(executed.exercises[0].holdKind, .jug)
        XCTAssertEqual(executed.exercises[0].workDuration, 10)
        XCTAssertEqual(executed.exercises[0].restDuration, 50)
        XCTAssertEqual(executed.exercises[1].kind, .pull)
        XCTAssertEqual(executed.exercises[1].repetitions, 5)
    }

    func testTrailingRestIsStrippedOnSave() throws {
        let draft = FreeWorkoutDraft(title: "Evening", exercises: [
            FreeWorkoutExerciseDraft(kind: .hang, holdKind: .jug, workDuration: 10, restDuration: 50),
        ])
        let definition = try FreeWorkoutSaver.routineDefinition(from: draft, title: "Evening")
        XCTAssertEqual(definition.steps.count, 1)
        XCTAssertNotEqual(definition.steps.last?.phase, .rest)
    }

    func testHoldlessExercisesAreOmittedOnSave() throws {
        let draft = FreeWorkoutDraft(title: "Mixed", exercises: [
            FreeWorkoutExerciseDraft(kind: .hang, title: "Jug hang", holdKind: .jug, workDuration: 10, restDuration: 0),
            FreeWorkoutExerciseDraft(kind: .hang, title: "Mystery hang", holdKind: nil, workDuration: 10, restDuration: 0),
        ])
        XCTAssertEqual(FreeWorkoutSaver.omittedHoldlessTitles(in: draft), ["Mystery hang"])
        let definition = try FreeWorkoutSaver.routineDefinition(from: draft, title: "Mixed")
        XCTAssertEqual(definition.steps.count, 1)
        XCTAssertEqual(definition.steps.first?.title, "Jug hang")
    }
}
