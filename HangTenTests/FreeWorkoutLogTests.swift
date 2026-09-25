import XCTest
@testable import HangTen

final class FreeWorkoutLogTests: XCTestCase {
    func testAddSetPrefillsFromPreviousSet() throws {
        var log = FreeWorkoutLog(boardID: nil)
        let exerciseID = log.addExercise(
            type: .hang,
            title: "Jug hang",
            holdSelection: .generic(.jug)
        )
        log.updateSet(
            exerciseID: exerciseID,
            setID: log.exercises[0].sets[0].id,
            weightKGF: 13.6,
            duration: 10,
            reps: nil,
            tag: .warmUp
        )

        let newSetID = try XCTUnwrap(log.addSet(toExerciseID: exerciseID))
        let newSet = log.exercises[0].sets.first(where: { $0.id == newSetID })

        XCTAssertEqual(log.exercises[0].sets.count, 2)
        XCTAssertEqual(newSet?.weightKGF, 13.6)
        XCTAssertEqual(newSet?.duration, 10)
        XCTAssertNil(newSet?.reps)
        XCTAssertNil(newSet?.tag)
        XCTAssertNil(newSet?.mode)
        XCTAssertNil(newSet?.completedAt)
    }

    func testAddSetPrefillsRepsForPullUp() throws {
        var log = FreeWorkoutLog(boardID: nil)
        let exerciseID = log.addExercise(
            type: .pullUp,
            title: "Pull-ups",
            holdSelection: .generic(.jug)
        )
        log.updateSet(
            exerciseID: exerciseID,
            setID: log.exercises[0].sets[0].id,
            weightKGF: 5,
            duration: nil,
            reps: 8,
            tag: nil
        )

        let newSetID = try XCTUnwrap(log.addSet(toExerciseID: exerciseID))
        let newSet = log.exercises[0].sets.first(where: { $0.id == newSetID })

        XCTAssertEqual(newSet?.weightKGF, 5)
        XCTAssertEqual(newSet?.reps, 8)
        XCTAssertNil(newSet?.duration)
    }

    func testAddSetReturnsNilForMissingExercise() {
        var log = FreeWorkoutLog(boardID: nil)
        XCTAssertNil(log.addSet(toExerciseID: UUID()))
        XCTAssertTrue(log.exercises.isEmpty)
    }

    func testUncheckedCloneClearsCompletionAndUsesNewIDs() {
        var log = FreeWorkoutLog(boardID: "board-1")
        let exerciseID = log.addExercise(
            type: .hang,
            title: "Edge hang",
            holdSelection: .exact(
                FreeWorkoutHoldSelection.ExactContact(
                    contactID: "edge-1",
                    kind: .edge,
                    shape: nil,
                    depth: nil,
                    fingerCapacity: 4
                )
            )
        )
        let setID = log.exercises[0].sets[0].id
        log.updateSet(
            exerciseID: exerciseID,
            setID: setID,
            weightKGF: 10,
            duration: 7,
            reps: nil,
            tag: .failure
        )
        log.completeSet(exerciseID: exerciseID, setID: setID, mode: .guided)

        let originalLogID = log.id
        let originalExerciseID = log.exercises[0].id
        let originalSetID = log.exercises[0].sets[0].id

        let clone = log.uncheckedClone()

        XCTAssertNotEqual(clone.id, originalLogID)
        XCTAssertEqual(clone.boardID, "board-1")
        XCTAssertEqual(clone.exercises.count, 1)
        XCTAssertNotEqual(clone.exercises[0].id, originalExerciseID)
        XCTAssertEqual(clone.exercises[0].title, "Edge hang")
        XCTAssertEqual(clone.exercises[0].sets.count, 1)
        XCTAssertNotEqual(clone.exercises[0].sets[0].id, originalSetID)
        XCTAssertEqual(clone.exercises[0].sets[0].weightKGF, 10)
        XCTAssertEqual(clone.exercises[0].sets[0].duration, 7)
        XCTAssertEqual(clone.exercises[0].sets[0].tag, .failure)
        XCTAssertNil(clone.exercises[0].sets[0].completedAt)
        XCTAssertNil(clone.exercises[0].sets[0].mode)
    }

    func testTemplateCloneMatchesUncheckedCloneSemantics() {
        var log = FreeWorkoutLog(boardID: nil)
        let exerciseID = log.addExercise(
            type: .pullUp,
            title: "Pull-ups",
            holdSelection: .generic(.jug)
        )
        let setID = log.exercises[0].sets[0].id
        log.completeSet(exerciseID: exerciseID, setID: setID, mode: .manual)

        let template = log.templateClone()
        let unchecked = log.uncheckedClone()

        XCTAssertNil(template.exercises[0].sets[0].completedAt)
        XCTAssertNil(template.exercises[0].sets[0].mode)
        XCTAssertNotEqual(template.id, log.id)
        XCTAssertNotEqual(template.id, unchecked.id)
        XCTAssertEqual(template.exercises[0].type, unchecked.exercises[0].type)
        XCTAssertEqual(template.exercises[0].sets[0].reps, unchecked.exercises[0].sets[0].reps)
    }

    func testFinishedLogDropsUncheckedSetsAndEmptyExercises() {
        var log = FreeWorkoutLog(boardID: nil)
        let hangID = log.addExercise(
            type: .hang,
            title: "Hang",
            holdSelection: .generic(.jug)
        )
        let hangSet1 = log.exercises[0].sets[0].id
        log.updateSet(
            exerciseID: hangID,
            setID: hangSet1,
            weightKGF: 5,
            duration: 10,
            reps: nil,
            tag: nil
        )
        log.completeSet(exerciseID: hangID, setID: hangSet1, mode: .manual)
        _ = log.addSet(toExerciseID: hangID)

        let pullID = log.addExercise(
            type: .pullUp,
            title: "Pull-ups",
            holdSelection: .generic(.jug)
        )
        // pull-up exercise left entirely unchecked

        let emptyID = log.addExercise(
            type: .hang,
            title: "Unused hang",
            holdSelection: .generic(.jug)
        )
        XCTAssertNotNil(emptyID)

        let finished = log.finishedLog()

        XCTAssertEqual(finished.exercises.count, 1)
        XCTAssertEqual(finished.exercises[0].id, hangID)
        XCTAssertEqual(finished.exercises[0].sets.count, 1)
        XCTAssertEqual(finished.exercises[0].sets[0].id, hangSet1)
        XCTAssertNotNil(finished.exercises[0].sets[0].completedAt)
        XCTAssertEqual(finished.id, log.id)
        XCTAssertNil(finished.exercises.first(where: { $0.id == pullID }))
    }

    func testDefaultRestAfterSecondsIs180() {
        var log = FreeWorkoutLog(boardID: nil)
        let exerciseID = log.addExercise(
            type: .hang,
            title: "Hang",
            holdSelection: .generic(.jug)
        )
        XCTAssertEqual(log.exercises.first(where: { $0.id == exerciseID })?.restAfterSeconds, 180)

        let exercise = FreeExercise(
            type: .pullUp,
            title: "Pull-ups",
            holdSelection: .generic(.jug)
        )
        XCTAssertEqual(exercise.restAfterSeconds, 180)
    }

    func testUncompleteClearsCompletedAtAndMode() {
        var log = FreeWorkoutLog(boardID: nil)
        let exerciseID = log.addExercise(
            type: .hang,
            title: "Hang",
            holdSelection: .generic(.jug)
        )
        let setID = log.exercises[0].sets[0].id
        log.completeSet(exerciseID: exerciseID, setID: setID, mode: .guided)
        XCTAssertNotNil(log.exercises[0].sets[0].completedAt)
        XCTAssertEqual(log.exercises[0].sets[0].mode, .guided)

        log.uncompleteSet(exerciseID: exerciseID, setID: setID)
        XCTAssertNil(log.exercises[0].sets[0].completedAt)
        XCTAssertNil(log.exercises[0].sets[0].mode)
    }

    func testRemoveAndReorderExercises() {
        var log = FreeWorkoutLog(boardID: nil)
        let first = log.addExercise(type: .hang, title: "A", holdSelection: .generic(.jug))
        let second = log.addExercise(type: .pullUp, title: "B", holdSelection: .generic(.jug))
        let third = log.addExercise(type: .hang, title: "C", holdSelection: .generic(.jug))

        log.moveExercise(id: third, toOffset: 0)
        XCTAssertEqual(log.exercises.map(\.id), [third, first, second])

        log.removeExercise(id: first)
        XCTAssertEqual(log.exercises.map(\.id), [third, second])
    }
}

// MARK: - Persistence stores

final class FreeWorkoutLogStoreTests: XCTestCase {
    private var suiteName: String!
    private var defaults: UserDefaults!

    override func setUp() {
        super.setUp()
        suiteName = "FreeWorkoutLogStoreTests.\(UUID().uuidString)"
        defaults = UserDefaults(suiteName: suiteName)!
        defaults.removePersistentDomain(forName: suiteName)
    }

    override func tearDown() {
        defaults.removePersistentDomain(forName: suiteName)
        defaults = nil
        suiteName = nil
        super.tearDown()
    }

    func testActiveLogRoundTripAndClear() {
        var log = nontrivialLog()
        ActiveFreeWorkoutStore.save(log, defaults: defaults)

        let loaded = ActiveFreeWorkoutStore.load(defaults: defaults)
        XCTAssertEqual(loaded, log)

        log.boardID = "updated-board"
        ActiveFreeWorkoutStore.save(log, defaults: defaults)
        XCTAssertEqual(ActiveFreeWorkoutStore.load(defaults: defaults)?.boardID, "updated-board")

        ActiveFreeWorkoutStore.clear(defaults: defaults)
        XCTAssertNil(ActiveFreeWorkoutStore.load(defaults: defaults))
    }

    func testHistoryAppendAndLatestOrdering() {
        let older = FreeWorkoutLog(
            id: UUID(),
            startedAt: Date(timeIntervalSince1970: 100),
            boardID: "a",
            exercises: []
        )
        let newer = FreeWorkoutLog(
            id: UUID(),
            startedAt: Date(timeIntervalSince1970: 50),
            boardID: "b",
            exercises: []
        )

        FreeWorkoutHistoryStore.append(older, defaults: defaults)
        FreeWorkoutHistoryStore.append(newer, defaults: defaults)

        let all = FreeWorkoutHistoryStore.load(defaults: defaults)
        XCTAssertEqual(all.map(\.id), [newer.id, older.id])
        XCTAssertEqual(FreeWorkoutHistoryStore.latest(defaults: defaults)?.id, newer.id)
    }

    func testTemplateCRUD() throws {
        var log = nontrivialLog()
        log.completeSet(
            exerciseID: log.exercises[0].id,
            setID: log.exercises[0].sets[0].id,
            mode: .guided
        )
        let template = FreeWorkoutTemplate(
            name: " Jug session ",
            log: log.finishedLog().templateClone()
        )

        FreeWorkoutTemplateStore.save(template, defaults: defaults)
        XCTAssertEqual(FreeWorkoutTemplateStore.load(defaults: defaults).count, 1)

        var fetched = try XCTUnwrap(FreeWorkoutTemplateStore.template(id: template.id, defaults: defaults))
        XCTAssertEqual(fetched.name, " Jug session ")
        XCTAssertNil(fetched.log.exercises[0].sets[0].completedAt)
        XCTAssertNil(fetched.log.exercises[0].sets[0].mode)

        fetched.name = "Jug session"
        FreeWorkoutTemplateStore.save(fetched, defaults: defaults)
        XCTAssertEqual(
            FreeWorkoutTemplateStore.template(id: template.id, defaults: defaults)?.name,
            "Jug session"
        )
        XCTAssertEqual(FreeWorkoutTemplateStore.load(defaults: defaults).count, 1)

        FreeWorkoutTemplateStore.delete(id: template.id, defaults: defaults)
        XCTAssertTrue(FreeWorkoutTemplateStore.load(defaults: defaults).isEmpty)
        XCTAssertNil(FreeWorkoutTemplateStore.template(id: template.id, defaults: defaults))
    }

    func testTemplateSaveClearsCompletedAtWithoutCallerClone() throws {
        var log = nontrivialLog()
        log.completeSet(
            exerciseID: log.exercises[0].id,
            setID: log.exercises[0].sets[0].id,
            mode: .manual
        )
        let templateID = UUID()
        let exerciseID = log.exercises[0].id
        let setID = log.exercises[0].sets[0].id
        FreeWorkoutTemplateStore.save(
            FreeWorkoutTemplate(id: templateID, name: "Raw", log: log),
            defaults: defaults
        )

        let saved = try XCTUnwrap(FreeWorkoutTemplateStore.template(id: templateID, defaults: defaults))
        XCTAssertEqual(saved.log.exercises[0].id, exerciseID)
        XCTAssertEqual(saved.log.exercises[0].sets[0].id, setID)
        XCTAssertNil(saved.log.exercises[0].sets[0].completedAt)
        XCTAssertNil(saved.log.exercises[0].sets[0].mode)
    }

    func testCorruptPayloadRecovery() {
        defaults.set(Data("not-json{{{".utf8), forKey: ActiveFreeWorkoutStore.key)
        defaults.set(Data("garbage".utf8), forKey: FreeWorkoutHistoryStore.key)
        defaults.set(Data([0xFF, 0x00, 0x01]), forKey: FreeWorkoutTemplateStore.key)

        XCTAssertNil(ActiveFreeWorkoutStore.load(defaults: defaults))
        XCTAssertEqual(FreeWorkoutHistoryStore.load(defaults: defaults), [])
        XCTAssertNil(FreeWorkoutHistoryStore.latest(defaults: defaults))
        XCTAssertEqual(FreeWorkoutTemplateStore.load(defaults: defaults), [])
    }

    func testNontrivialLogCodableRoundTripThroughActiveStore() {
        let log = nontrivialLog()
        ActiveFreeWorkoutStore.save(log, defaults: defaults)

        let reloaded = ActiveFreeWorkoutStore.load(defaults: defaults)
        XCTAssertEqual(reloaded, log)
        XCTAssertEqual(reloaded?.exercises.count, 2)
        XCTAssertEqual(reloaded?.exercises[0].type, .hang)
        XCTAssertEqual(reloaded?.exercises[0].holdSelection, .generic(.edge))
        XCTAssertEqual(reloaded?.exercises[0].sets[0].weightKGF, 12.5)
        XCTAssertEqual(reloaded?.exercises[0].sets[0].duration, 10)
        XCTAssertEqual(reloaded?.exercises[0].sets[0].tag, .warmUp)
        XCTAssertEqual(reloaded?.exercises[0].sets[0].mode, .guided)
        XCTAssertNotNil(reloaded?.exercises[0].sets[0].completedAt)
        XCTAssertEqual(reloaded?.exercises[1].type, .pullUp)
        XCTAssertEqual(reloaded?.exercises[1].sets[0].reps, 5)
        if case let .exact(contact)? = reloaded?.exercises[1].holdSelection {
            XCTAssertEqual(contact.contactID, "jug-L")
            XCTAssertEqual(contact.kind, .jug)
        } else {
            XCTFail("Expected exact hold selection on pull-up")
        }
    }

    private func nontrivialLog() -> FreeWorkoutLog {
        var log = FreeWorkoutLog(
            id: UUID(uuidString: "AAAAAAAA-BBBB-CCCC-DDDD-EEEEEEEEEEEE")!,
            startedAt: Date(timeIntervalSince1970: 1_700_000_000),
            boardID: "trango-rock-prodigy-pivot"
        )
        let hangID = log.addExercise(
            type: .hang,
            title: "20mm edge",
            holdSelection: .generic(.edge),
            restAfterSeconds: 210
        )
        log.updateSet(
            exerciseID: hangID,
            setID: log.exercises[0].sets[0].id,
            weightKGF: 12.5,
            duration: 10,
            reps: nil,
            tag: .warmUp
        )
        log.completeSet(
            exerciseID: hangID,
            setID: log.exercises[0].sets[0].id,
            mode: .guided,
            completedAt: Date(timeIntervalSince1970: 1_700_000_030)
        )
        _ = log.addSet(toExerciseID: hangID)

        let pullID = log.addExercise(
            type: .pullUp,
            title: "Jug pull-ups",
            holdSelection: .exact(
                FreeWorkoutHoldSelection.ExactContact(
                    contactID: "jug-L",
                    kind: .jug,
                    shape: nil,
                    depth: nil,
                    fingerCapacity: nil
                )
            ),
            restAfterSeconds: 180
        )
        log.updateSet(
            exerciseID: pullID,
            setID: log.exercises[1].sets[0].id,
            weightKGF: 0,
            duration: nil,
            reps: 5,
            tag: nil
        )
        return log
    }
}

// MARK: - Draft migration

final class FreeWorkoutDraftMigrationTests: XCTestCase {
    private var suiteName: String!
    private var defaults: UserDefaults!

    override func setUp() {
        super.setUp()
        suiteName = "FreeWorkoutDraftMigrationTests.\(UUID().uuidString)"
        defaults = UserDefaults(suiteName: suiteName)!
        defaults.removePersistentDomain(forName: suiteName)
    }

    override func tearDown() {
        defaults.removePersistentDomain(forName: suiteName)
        defaults = nil
        suiteName = nil
        super.tearDown()
    }

    func testMigratingMapsHangAndPullDropsRest() throws {
        let draft = FreeWorkoutDraft(
            title: "Mixed",
            exercises: [
                FreeWorkoutExerciseDraft(
                    kind: .hang,
                    title: "Jug hang",
                    holdKind: .jug,
                    workDuration: 12,
                    restDuration: 90,
                    externalLoadKGF: 7.5
                ),
                FreeWorkoutExerciseDraft(
                    kind: .rest,
                    title: "Long rest",
                    workDuration: 0,
                    restDuration: 180
                ),
                FreeWorkoutExerciseDraft(
                    kind: .pull,
                    title: "Edge pulls",
                    holdKind: .edge,
                    contactID: "edge-R",
                    contactKind: .edge,
                    contactShape: nil,
                    contactDepth: .category(.medium),
                    contactFingerCapacity: 4,
                    workDuration: 25,
                    restDuration: 0,
                    externalLoadKGF: 2,
                    repetitions: 6
                ),
            ]
        )

        let log = try XCTUnwrap(FreeWorkoutLog.migrating(from: draft))

        XCTAssertEqual(log.exercises.count, 2)

        let hang = log.exercises[0]
        XCTAssertEqual(hang.type, .hang)
        XCTAssertEqual(hang.title, "Jug hang")
        XCTAssertEqual(hang.holdSelection, .generic(.jug))
        XCTAssertEqual(hang.restAfterSeconds, 90)
        XCTAssertEqual(hang.sets.count, 1)
        XCTAssertEqual(hang.sets[0].duration, 12)
        XCTAssertEqual(hang.sets[0].weightKGF, 7.5)
        XCTAssertNil(hang.sets[0].reps)
        XCTAssertNil(hang.sets[0].completedAt)
        XCTAssertNil(hang.sets[0].mode)

        let pull = log.exercises[1]
        XCTAssertEqual(pull.type, .pullUp)
        XCTAssertEqual(pull.title, "Edge pulls")
        XCTAssertEqual(pull.restAfterSeconds, FreeExercise.defaultRestAfterSeconds)
        XCTAssertEqual(pull.sets.count, 1)
        XCTAssertEqual(pull.sets[0].reps, 6)
        XCTAssertEqual(pull.sets[0].weightKGF, 2)
        XCTAssertNil(pull.sets[0].duration)
        XCTAssertNil(pull.sets[0].completedAt)
        if case let .exact(contact) = pull.holdSelection {
            XCTAssertEqual(contact.contactID, "edge-R")
            XCTAssertEqual(contact.kind, .edge)
            XCTAssertEqual(contact.depth, .category(.medium))
            XCTAssertEqual(contact.fingerCapacity, 4)
        } else {
            XCTFail("Expected exact hold on pull")
        }
    }

    func testMigratingReturnsNilWhenOnlyRestsOrEmpty() {
        let restsOnly = FreeWorkoutDraft(
            title: "Rests",
            exercises: [
                FreeWorkoutExerciseDraft(kind: .rest, restDuration: 120),
                FreeWorkoutExerciseDraft(kind: .rest, restDuration: 60),
            ]
        )
        XCTAssertNil(FreeWorkoutLog.migrating(from: restsOnly))
        XCTAssertNil(FreeWorkoutLog.migrating(from: FreeWorkoutDraft(title: "Empty", exercises: [])))
    }

    func testOneShotSeedAppendsFinishedShapedHistoryAndClearsDraft() throws {
        let draft = FreeWorkoutDraft(
            title: "Last draft",
            exercises: [
                FreeWorkoutExerciseDraft(
                    kind: .hang,
                    title: "Hang",
                    holdKind: .sloper,
                    workDuration: 10,
                    restDuration: 60,
                    externalLoadKGF: 5
                ),
                .rest(),
            ]
        )
        FreeWorkoutDraftStore.save(draft, defaults: defaults)

        let first = FreeWorkoutDraftMigration.runIfNeeded(defaults: defaults)
        guard case let .seeded(logID) = first else {
            return XCTFail("Expected seeded, got \(first)")
        }

        let latest = try XCTUnwrap(FreeWorkoutHistoryStore.latest(defaults: defaults))
        XCTAssertEqual(latest.id, logID)
        XCTAssertEqual(latest.exercises.count, 1)
        XCTAssertEqual(latest.exercises[0].type, .hang)
        XCTAssertEqual(latest.exercises[0].sets[0].duration, 10)
        XCTAssertEqual(latest.exercises[0].sets[0].weightKGF, 5)
        XCTAssertEqual(latest.exercises[0].restAfterSeconds, 60)
        XCTAssertEqual(latest.exercises[0].sets[0].completedAt, latest.startedAt)
        XCTAssertNil(latest.exercises[0].sets[0].mode)

        let unchecked = latest.uncheckedClone()
        XCTAssertNil(unchecked.exercises[0].sets[0].completedAt)
        XCTAssertEqual(unchecked.exercises[0].sets[0].duration, 10)

        XCTAssertNil(FreeWorkoutDraftStore.load(defaults: defaults))
        XCTAssertTrue(defaults.bool(forKey: FreeWorkoutDraftMigration.migratedFlagKey))

        FreeWorkoutDraftStore.save(draft, defaults: defaults)
        let second = FreeWorkoutDraftMigration.runIfNeeded(defaults: defaults)
        XCTAssertEqual(second, .skippedAlreadyMigrated)
        XCTAssertEqual(FreeWorkoutHistoryStore.load(defaults: defaults).count, 1)
    }

    func testOneShotSeedDoesNotOverwriteExistingHistory() {
        let existing = FreeWorkoutLog(
            startedAt: Date(timeIntervalSince1970: 42),
            boardID: "existing",
            exercises: []
        )
        FreeWorkoutHistoryStore.append(existing, defaults: defaults)
        FreeWorkoutDraftStore.save(
            FreeWorkoutDraft(title: "Ignored", exercises: [.hang()]),
            defaults: defaults
        )

        let outcome = FreeWorkoutDraftMigration.runIfNeeded(defaults: defaults)
        XCTAssertEqual(outcome, .skippedHistoryExists)
        XCTAssertEqual(FreeWorkoutHistoryStore.latest(defaults: defaults)?.id, existing.id)
        XCTAssertEqual(FreeWorkoutHistoryStore.load(defaults: defaults).count, 1)
        XCTAssertNotNil(FreeWorkoutDraftStore.load(defaults: defaults))
        XCTAssertTrue(defaults.bool(forKey: FreeWorkoutDraftMigration.migratedFlagKey))
    }

    func testOneShotSeedNoOpsWhenDraftMissing() {
        let outcome = FreeWorkoutDraftMigration.runIfNeeded(defaults: defaults)
        XCTAssertEqual(outcome, .skippedNoDraft)
        XCTAssertNil(FreeWorkoutHistoryStore.latest(defaults: defaults))
        XCTAssertFalse(defaults.bool(forKey: FreeWorkoutDraftMigration.migratedFlagKey))
    }
}

// MARK: - Rest timer

final class FreeWorkoutRestTimerTests: XCTestCase {
    private let t0 = Date(timeIntervalSince1970: 1_000_000)

    func testStartSetsActiveRemaining() {
        var timer = FreeWorkoutRestTimer()
        XCTAssertFalse(timer.isActive)
        XCTAssertEqual(timer.remaining(at: t0), 0)

        timer.start(duration: 180, at: t0)

        XCTAssertTrue(timer.isActive)
        XCTAssertFalse(timer.isCompleted)
        XCTAssertEqual(timer.remaining(at: t0), 180)
        XCTAssertEqual(timer.remaining(at: t0.addingTimeInterval(45)), 135)
    }

    func testSkipDeactivates() {
        var timer = FreeWorkoutRestTimer()
        timer.start(duration: 180, at: t0)
        timer.skip()

        XCTAssertFalse(timer.isActive)
        XCTAssertFalse(timer.isCompleted)
        XCTAssertEqual(timer.phase, .inactive)
        XCTAssertEqual(timer.remaining(at: t0.addingTimeInterval(10)), 0)
    }

    func testDismissDeactivates() {
        var timer = FreeWorkoutRestTimer()
        timer.start(duration: 90, at: t0)
        timer.dismiss()

        XCTAssertFalse(timer.isActive)
        XCTAssertFalse(timer.isCompleted)
        XCTAssertEqual(timer.phase, .inactive)
        XCTAssertEqual(timer.remaining(at: t0), 0)
    }

    func testAdjustPlusAndMinus() {
        var timer = FreeWorkoutRestTimer()
        timer.start(duration: 180, at: t0)

        timer.subtract30(at: t0)
        XCTAssertEqual(timer.remaining(at: t0), 150)

        timer.add30(at: t0)
        XCTAssertEqual(timer.remaining(at: t0), 180)

        timer.add60(at: t0)
        XCTAssertEqual(timer.remaining(at: t0), 240)
        XCTAssertTrue(timer.isActive)
    }

    func testAdjustClampsRemainingAtZeroAndCompletes() {
        var timer = FreeWorkoutRestTimer()
        timer.start(duration: 20, at: t0)
        timer.adjust(by: -30, at: t0)

        XCTAssertEqual(timer.remaining(at: t0), 0)
        XCTAssertFalse(timer.isActive)
        XCTAssertTrue(timer.isCompleted)
        XCTAssertEqual(timer.phase, .completed)
    }

    func testExpiresNaturallyWithFrozenClock() {
        var timer = FreeWorkoutRestTimer()
        timer.start(duration: 60, at: t0)

        let mid = t0.addingTimeInterval(30)
        XCTAssertEqual(timer.remaining(at: mid), 30)
        timer.tick(at: mid)
        XCTAssertTrue(timer.isActive)
        XCTAssertFalse(timer.isCompleted)

        let end = t0.addingTimeInterval(60)
        XCTAssertEqual(timer.remaining(at: end), 0)
        timer.tick(at: end)
        XCTAssertFalse(timer.isActive)
        XCTAssertTrue(timer.isCompleted)
        XCTAssertEqual(timer.phase, .completed)

        let past = t0.addingTimeInterval(90)
        XCTAssertEqual(timer.remaining(at: past), 0)
    }

    func testZeroDurationStartsCompleted() {
        var timer = FreeWorkoutRestTimer()
        timer.start(duration: 0, at: t0)

        XCTAssertFalse(timer.isActive)
        XCTAssertTrue(timer.isCompleted)
        XCTAssertEqual(timer.remaining(at: t0), 0)
    }

    func testAdjustIgnoredWhenInactive() {
        var timer = FreeWorkoutRestTimer()
        timer.adjust(by: 30, at: t0)
        XCTAssertEqual(timer.phase, .inactive)

        timer.start(duration: 60, at: t0)
        timer.skip()
        timer.add60(at: t0)
        XCTAssertEqual(timer.phase, .inactive)
    }
}

// MARK: - Guided hang countdown

final class FreeWorkoutGuidedHangCountdownTests: XCTestCase {
    private let t0 = Date(timeIntervalSince1970: 2_000_000)

    func testResolvedDurationUsesDefaultWhenNil() {
        XCTAssertEqual(FreeWorkoutGuidedHangCountdown.resolvedDuration(nil), 10)
        XCTAssertEqual(FreeWorkoutGuidedHangCountdown.resolvedDuration(7), 7)
        XCTAssertEqual(FreeWorkoutGuidedHangCountdown.resolvedDuration(0), 1)
    }

    func testStartPauseResumeAndNaturalComplete() {
        var countdown = FreeWorkoutGuidedHangCountdown()
        countdown.start(duration: 10, at: t0)

        XCTAssertTrue(countdown.isRunning)
        XCTAssertEqual(countdown.remaining(at: t0), 10)
        XCTAssertEqual(countdown.elapsed(at: t0.addingTimeInterval(3)), 3)

        countdown.pause(at: t0.addingTimeInterval(4))
        XCTAssertTrue(countdown.isPaused)
        XCTAssertEqual(countdown.remaining(at: t0.addingTimeInterval(100)), 6)

        countdown.resume(at: t0.addingTimeInterval(20))
        XCTAssertTrue(countdown.isRunning)
        XCTAssertEqual(countdown.remaining(at: t0.addingTimeInterval(22)), 4)

        countdown.tick(at: t0.addingTimeInterval(26))
        XCTAssertTrue(countdown.isCompleted)
        XCTAssertEqual(countdown.remaining(at: t0.addingTimeInterval(26)), 0)
    }

    func testCancelLeavesIdleWithoutCompletion() {
        var countdown = FreeWorkoutGuidedHangCountdown()
        countdown.start(duration: 10, at: t0)
        countdown.cancel()

        XCTAssertEqual(countdown.phase, .idle)
        XCTAssertFalse(countdown.isCompleted)
        XCTAssertEqual(countdown.remaining(at: t0.addingTimeInterval(5)), 0)
    }

    func testCompleteEarlyMarksCompleted() {
        var countdown = FreeWorkoutGuidedHangCountdown()
        countdown.start(duration: 10, at: t0)
        let elapsed = countdown.elapsed(at: t0.addingTimeInterval(3.5))
        countdown.complete()

        XCTAssertTrue(countdown.isCompleted)
        XCTAssertEqual(elapsed, 3.5, accuracy: 0.001)
    }

    func testEndCountdownAudioMatchesSessionPolicy() {
        XCTAssertNil(
            FreeWorkoutGuidedHangCountdown.endCountdownAudio(plannedDuration: 3, remaining: 3)
        )
        XCTAssertNil(
            FreeWorkoutGuidedHangCountdown.endCountdownAudio(plannedDuration: 10, remaining: 0)
        )

        let mid = FreeWorkoutGuidedHangCountdown.endCountdownAudio(
            plannedDuration: 10,
            remaining: 7
        )
        XCTAssertEqual(mid?.delay, 4)
        XCTAssertEqual(mid?.schedule.cues.map(\.phrase), ["3", "2", "1"])

        let late = FreeWorkoutGuidedHangCountdown.endCountdownAudio(
            plannedDuration: 10,
            remaining: 2.2
        )
        XCTAssertEqual(late?.delay, 0)
        XCTAssertEqual(late?.schedule.cues.map(\.phrase), ["3", "2", "1"])
    }

    func testCancelDoesNotCompleteSetOnLog() {
        var log = FreeWorkoutLog()
        let exerciseID = log.addExercise(type: .hang, holdSelection: .generic(.jug))
        let setID = log.exercises[0].sets[0].id
        log.updateSet(
            exerciseID: exerciseID,
            setID: setID,
            weightKGF: 5,
            duration: 10,
            reps: nil,
            tag: nil
        )

        // Cancel path: leave unchecked (no completeSet call).
        XCTAssertFalse(log.exercises[0].sets[0].isCompleted)
        XCTAssertNil(log.exercises[0].sets[0].mode)

        log.completeSet(exerciseID: exerciseID, setID: setID, mode: .guided)
        XCTAssertTrue(log.exercises[0].sets[0].isCompleted)
        XCTAssertEqual(log.exercises[0].sets[0].mode, .guided)
        XCTAssertNotNil(log.exercises[0].sets[0].completedAt)
    }

    func testManualLogCompletesWithMode() {
        var log = FreeWorkoutLog()
        let exerciseID = log.addExercise(type: .pullUp, holdSelection: .generic(.jug))
        let setID = log.exercises[0].sets[0].id
        log.updateSet(
            exerciseID: exerciseID,
            setID: setID,
            weightKGF: 10,
            duration: nil,
            reps: 5,
            tag: nil
        )
        log.completeSet(exerciseID: exerciseID, setID: setID, mode: .manual)

        XCTAssertEqual(log.exercises[0].sets[0].mode, .manual)
        XCTAssertTrue(log.exercises[0].sets[0].isCompleted)
    }
}

// MARK: - Finish → history + template

final class FreeWorkoutFinishTests: XCTestCase {
    private var suiteName: String!
    private var defaults: UserDefaults!

    override func setUp() {
        super.setUp()
        suiteName = "FreeWorkoutFinishTests.\(UUID().uuidString)"
        defaults = UserDefaults(suiteName: suiteName)!
        defaults.removePersistentDomain(forName: suiteName)
    }

    override func tearDown() {
        defaults.removePersistentDomain(forName: suiteName)
        defaults = nil
        suiteName = nil
        super.tearDown()
    }

    func testPersistToHistoryHappyPathClearsActiveAndAppendsLatest() throws {
        var log = FreeWorkoutLog(boardID: "board-finish")
        let hangID = log.addExercise(type: .hang, title: "Edge", holdSelection: .generic(.edge))
        let hangSetID = log.exercises[0].sets[0].id
        log.updateSet(
            exerciseID: hangID,
            setID: hangSetID,
            weightKGF: 10,
            duration: 7,
            reps: nil,
            tag: nil
        )
        log.completeSet(exerciseID: hangID, setID: hangSetID, mode: .guided)

        let pullID = log.addExercise(type: .pullUp, title: "Pulls", holdSelection: .generic(.jug))
        let pullSetID = log.exercises[1].sets[0].id
        log.updateSet(
            exerciseID: pullID,
            setID: pullSetID,
            weightKGF: 5,
            duration: nil,
            reps: 8,
            tag: nil
        )
        log.completeSet(exerciseID: pullID, setID: pullSetID, mode: .manual)

        // Unchecked leftover should be dropped from finished history.
        _ = log.addSet(toExerciseID: hangID)

        ActiveFreeWorkoutStore.save(log, defaults: defaults)

        let finished = try XCTUnwrap(FreeWorkoutFinish.persistToHistory(log, defaults: defaults))

        XCTAssertNil(ActiveFreeWorkoutStore.load(defaults: defaults))
        XCTAssertEqual(FreeWorkoutHistoryStore.latest(defaults: defaults)?.id, finished.id)
        XCTAssertEqual(finished.exercises.count, 2)
        XCTAssertEqual(finished.exercises[0].sets.count, 1)
        XCTAssertTrue(finished.exercises.flatMap(\.sets).allSatisfy(\.isCompleted))

        let template = try XCTUnwrap(
            FreeWorkoutFinish.saveTemplate(
                name: "  Morning edges  ",
                finished: finished,
                defaults: defaults
            )
        )
        XCTAssertEqual(template.name, "Morning edges")
        XCTAssertEqual(FreeWorkoutTemplateStore.load(defaults: defaults).count, 1)
        let saved = try XCTUnwrap(FreeWorkoutTemplateStore.template(id: template.id, defaults: defaults))
        XCTAssertTrue(saved.log.exercises.flatMap(\.sets).allSatisfy { !$0.isCompleted })
        XCTAssertNotEqual(saved.log.id, finished.id)
    }

    func testPersistToHistoryWithZeroCompletedDoesNotAppendOrClear() {
        var log = FreeWorkoutLog()
        _ = log.addExercise(type: .hang, holdSelection: .generic(.jug))
        ActiveFreeWorkoutStore.save(log, defaults: defaults)

        XCTAssertNil(FreeWorkoutFinish.persistToHistory(log, defaults: defaults))
        XCTAssertNotNil(ActiveFreeWorkoutStore.load(defaults: defaults))
        XCTAssertTrue(FreeWorkoutHistoryStore.load(defaults: defaults).isEmpty)
    }

    func testDiscardActiveClearsWithoutHistory() {
        var log = FreeWorkoutLog()
        let exerciseID = log.addExercise(type: .hang, holdSelection: .generic(.jug))
        log.completeSet(
            exerciseID: exerciseID,
            setID: log.exercises[0].sets[0].id,
            mode: .manual
        )
        ActiveFreeWorkoutStore.save(log, defaults: defaults)

        FreeWorkoutFinish.discardActive(defaults: defaults)

        XCTAssertNil(ActiveFreeWorkoutStore.load(defaults: defaults))
        XCTAssertTrue(FreeWorkoutHistoryStore.load(defaults: defaults).isEmpty)
    }

    func testHealthRecordingInputDerivesWorkStepsFromCompletedSets() {
        var log = FreeWorkoutLog(
            startedAt: Date(timeIntervalSince1970: 1_000),
            boardID: "metolius.wood-grips-compact-ii"
        )
        let hangID = log.addExercise(type: .hang, title: "Jug hang", holdSelection: .generic(.jug))
        log.updateSet(
            exerciseID: hangID,
            setID: log.exercises[0].sets[0].id,
            weightKGF: 12,
            duration: 9,
            reps: nil,
            tag: nil
        )
        log.completeSet(
            exerciseID: hangID,
            setID: log.exercises[0].sets[0].id,
            mode: .guided
        )
        let pullID = log.addExercise(type: .pullUp, title: "Pull-ups", holdSelection: .generic(.jug))
        log.updateSet(
            exerciseID: pullID,
            setID: log.exercises[1].sets[0].id,
            weightKGF: nil,
            duration: nil,
            reps: 5,
            tag: nil
        )
        log.completeSet(
            exerciseID: pullID,
            setID: log.exercises[1].sets[0].id,
            mode: .manual
        )

        let finished = log.finishedLog()
        let end = Date(timeIntervalSince1970: 1_300)
        let health = FreeWorkoutFinish.healthRecordingInput(
            from: finished,
            title: "Free workout",
            endDate: end
        )

        XCTAssertEqual(health.plan.title, "Free workout")
        XCTAssertTrue(health.plan.isFreeWorkout)
        XCTAssertEqual(health.startDate, finished.startedAt)
        XCTAssertEqual(health.endDate, end)
        XCTAssertEqual(health.sessionSteps.count, 2)
        XCTAssertEqual(health.sessionSteps[0].phase, .hang)
        XCTAssertEqual(health.sessionSteps[0].duration, 9)
        XCTAssertEqual(health.sessionSteps[1].phase, .pull)
        XCTAssertEqual(health.sessionSteps[1].duration, FreeWorkoutFinish.defaultPullUpWorkDuration)
        XCTAssertEqual(health.sessionSteps[1].repetitions, 5)
        XCTAssertEqual(health.session.planTitle, "Free workout")
        XCTAssertEqual(health.session.steps.count, 2)
    }

    func testSaveTemplateRejectsBlankName() {
        let finished = FreeWorkoutLog()
        XCTAssertNil(FreeWorkoutFinish.saveTemplate(name: "   ", finished: finished, defaults: defaults))
        XCTAssertTrue(FreeWorkoutTemplateStore.load(defaults: defaults).isEmpty)
    }

    func testDecimalTextParsesCommaLocale() {
        let de = Locale(identifier: "de_DE")
        XCTAssertEqual(FreeWorkoutDecimalText.parse("12,5", locale: de), 12.5)
        XCTAssertEqual(FreeWorkoutDecimalText.parse(" 12,5 ", locale: de), 12.5)
        XCTAssertNil(FreeWorkoutDecimalText.parse("   ", locale: de))
        XCTAssertNil(FreeWorkoutDecimalText.parse("", locale: de))
    }

    func testDecimalTextParsesDotLocale() {
        let en = Locale(identifier: "en_US")
        XCTAssertEqual(FreeWorkoutDecimalText.parse("12.5", locale: en), 12.5)
        XCTAssertEqual(FreeWorkoutDecimalText.format(12.5, locale: en), "12.5")
        XCTAssertEqual(FreeWorkoutDecimalText.format(12, locale: en), "12")
        XCTAssertEqual(FreeWorkoutDecimalText.format(nil, locale: en), "")
    }

    func testDecimalTextFormatsCommaLocale() {
        let de = Locale(identifier: "de_DE")
        XCTAssertEqual(FreeWorkoutDecimalText.format(12.5, locale: de), "12,5")
        XCTAssertEqual(FreeWorkoutDecimalText.format(12, locale: de), "12")
    }
}
