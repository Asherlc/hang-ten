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
        XCTAssertThrowsError(try FreeWorkoutSaver.routineDefinition(from: draft, title: "Empty"))
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
}
