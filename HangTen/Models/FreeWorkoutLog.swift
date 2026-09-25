import Foundation

enum FreeExerciseType: String, Codable, Hashable, CaseIterable {
    case hang
    case pullUp

    var label: String {
        switch self {
        case .hang: "Hang"
        case .pullUp: "Pull-ups"
        }
    }
}

enum FreeSetTag: String, Codable, Hashable, CaseIterable {
    case warmUp
    case drop
    case failure
}

enum FreeSetMode: String, Codable, Hashable, CaseIterable {
    case guided
    case manual
}

/// Hold choice for a free-workout exercise (board-agnostic generic or exact contact).
enum FreeWorkoutHoldSelection: Codable, Hashable {
    case generic(HoldKind)
    case exact(ExactContact)

    struct ExactContact: Codable, Hashable {
        var contactID: String
        var kind: HoldKind?
        var shape: HoldShape?
        var depth: HoldDepth?
        var fingerCapacity: Int?

        init(
            contactID: String,
            kind: HoldKind? = nil,
            shape: HoldShape? = nil,
            depth: HoldDepth? = nil,
            fingerCapacity: Int? = nil
        ) {
            self.contactID = contactID
            self.kind = kind
            self.shape = shape
            self.depth = depth
            self.fingerCapacity = fingerCapacity
        }

        init(_ contact: PhysicalContact) {
            self.init(
                contactID: contact.id,
                kind: contact.kind,
                shape: contact.shape,
                depth: contact.depth,
                fingerCapacity: contact.fingerCapacity
            )
        }
    }
}

struct FreeSet: Codable, Hashable, Identifiable {
    var id: UUID
    var weightKGF: Double?
    var duration: TimeInterval?
    var reps: Int?
    var tag: FreeSetTag?
    var mode: FreeSetMode?
    var completedAt: Date?

    init(
        id: UUID = UUID(),
        weightKGF: Double? = nil,
        duration: TimeInterval? = nil,
        reps: Int? = nil,
        tag: FreeSetTag? = nil,
        mode: FreeSetMode? = nil,
        completedAt: Date? = nil
    ) {
        self.id = id
        self.weightKGF = weightKGF
        self.duration = duration
        self.reps = reps
        self.tag = tag
        self.mode = mode
        self.completedAt = completedAt
    }

    var isCompleted: Bool { completedAt != nil }

    /// Prefills load/work fields from another set; leaves completion state empty.
    static func prefilling(from previous: FreeSet?) -> FreeSet {
        FreeSet(
            weightKGF: previous?.weightKGF,
            duration: previous?.duration,
            reps: previous?.reps
        )
    }
}

struct FreeExercise: Codable, Hashable, Identifiable {
    static let defaultRestAfterSeconds: TimeInterval = 180

    var id: UUID
    var type: FreeExerciseType
    var title: String
    var holdSelection: FreeWorkoutHoldSelection
    var hand: WorkoutSide
    var restAfterSeconds: TimeInterval
    var sets: [FreeSet]

    init(
        id: UUID = UUID(),
        type: FreeExerciseType,
        title: String? = nil,
        holdSelection: FreeWorkoutHoldSelection = .generic(.jug),
        hand: WorkoutSide = .both,
        restAfterSeconds: TimeInterval = FreeExercise.defaultRestAfterSeconds,
        sets: [FreeSet]? = nil
    ) {
        self.id = id
        self.type = type
        self.title = title ?? type.label
        self.holdSelection = holdSelection
        self.hand = hand
        self.restAfterSeconds = restAfterSeconds
        self.sets = sets ?? [FreeSet()]
    }
}

struct FreeWorkoutLog: Codable, Hashable, Identifiable {
    var id: UUID
    var startedAt: Date
    var boardID: String?
    var exercises: [FreeExercise]

    init(
        id: UUID = UUID(),
        startedAt: Date = Date(),
        boardID: String? = nil,
        exercises: [FreeExercise] = []
    ) {
        self.id = id
        self.startedAt = startedAt
        self.boardID = boardID
        self.exercises = exercises
    }

    // MARK: - Exercise mutations

    @discardableResult
    mutating func addExercise(
        type: FreeExerciseType,
        title: String? = nil,
        holdSelection: FreeWorkoutHoldSelection = .generic(.jug),
        hand: WorkoutSide = .both,
        restAfterSeconds: TimeInterval = FreeExercise.defaultRestAfterSeconds
    ) -> UUID {
        let exercise = FreeExercise(
            type: type,
            title: title,
            holdSelection: holdSelection,
            hand: hand,
            restAfterSeconds: restAfterSeconds
        )
        exercises.append(exercise)
        return exercise.id
    }

    mutating func removeExercise(id: UUID) {
        exercises.removeAll { $0.id == id }
    }

    /// Moves the exercise with `id` so it lands at `toOffset` in the resulting array.
    mutating func moveExercise(id: UUID, toOffset: Int) {
        guard let fromIndex = exercises.firstIndex(where: { $0.id == id }) else { return }
        let clamped = max(0, min(toOffset, exercises.count - 1))
        let exercise = exercises.remove(at: fromIndex)
        exercises.insert(exercise, at: clamped)
    }

    mutating func reorderExercises(fromOffsets: IndexSet, toOffset: Int) {
        exercises.move(fromOffsets: fromOffsets, toOffset: toOffset)
    }

    // MARK: - Set mutations

    /// Returns the new set’s id, or `nil` when `exerciseID` is missing.
    @discardableResult
    mutating func addSet(toExerciseID exerciseID: UUID) -> UUID? {
        guard let index = exercises.firstIndex(where: { $0.id == exerciseID }) else {
            return nil
        }
        let newSet = FreeSet.prefilling(from: exercises[index].sets.last)
        exercises[index].sets.append(newSet)
        return newSet.id
    }

    mutating func updateSet(
        exerciseID: UUID,
        setID: UUID,
        weightKGF: Double?,
        duration: TimeInterval?,
        reps: Int?,
        tag: FreeSetTag?
    ) {
        guard let exerciseIndex = exercises.firstIndex(where: { $0.id == exerciseID }),
              let setIndex = exercises[exerciseIndex].sets.firstIndex(where: { $0.id == setID })
        else { return }
        exercises[exerciseIndex].sets[setIndex].weightKGF = weightKGF
        exercises[exerciseIndex].sets[setIndex].duration = duration
        exercises[exerciseIndex].sets[setIndex].reps = reps
        exercises[exerciseIndex].sets[setIndex].tag = tag
    }

    mutating func completeSet(
        exerciseID: UUID,
        setID: UUID,
        mode: FreeSetMode,
        completedAt: Date = Date()
    ) {
        guard let exerciseIndex = exercises.firstIndex(where: { $0.id == exerciseID }),
              let setIndex = exercises[exerciseIndex].sets.firstIndex(where: { $0.id == setID })
        else { return }
        exercises[exerciseIndex].sets[setIndex].mode = mode
        exercises[exerciseIndex].sets[setIndex].completedAt = completedAt
    }

    mutating func uncompleteSet(exerciseID: UUID, setID: UUID) {
        guard let exerciseIndex = exercises.firstIndex(where: { $0.id == exerciseID }),
              let setIndex = exercises[exerciseIndex].sets.firstIndex(where: { $0.id == setID })
        else { return }
        exercises[exerciseIndex].sets[setIndex].mode = nil
        exercises[exerciseIndex].sets[setIndex].completedAt = nil
    }

    // MARK: - Clones & finish

    /// New session IDs with all sets unchecked (modes and completedAt cleared).
    func uncheckedClone(startedAt: Date = Date()) -> FreeWorkoutLog {
        FreeWorkoutLog(
            id: UUID(),
            startedAt: startedAt,
            boardID: boardID,
            exercises: exercises.map { exercise in
                FreeExercise(
                    id: UUID(),
                    type: exercise.type,
                    title: exercise.title,
                    holdSelection: exercise.holdSelection,
                    hand: exercise.hand,
                    restAfterSeconds: exercise.restAfterSeconds,
                    sets: exercise.sets.map { set in
                        FreeSet(
                            id: UUID(),
                            weightKGF: set.weightKGF,
                            duration: set.duration,
                            reps: set.reps,
                            tag: set.tag,
                            mode: nil,
                            completedAt: nil
                        )
                    }
                )
            }
        )
    }

    /// Alias for template / last-workout reuse: same as `uncheckedClone()`.
    func templateClone(startedAt: Date = Date()) -> FreeWorkoutLog {
        uncheckedClone(startedAt: startedAt)
    }

    /// History shape: only completed sets; exercises with zero completed sets are dropped.
    func finishedLog() -> FreeWorkoutLog {
        FreeWorkoutLog(
            id: id,
            startedAt: startedAt,
            boardID: boardID,
            exercises: exercises.compactMap { exercise in
                let completed = exercise.sets.filter(\.isCompleted)
                guard !completed.isEmpty else { return nil }
                var copy = exercise
                copy.sets = completed
                return copy
            }
        )
    }

    // MARK: - Draft migration

    /// Converts a legacy `FreeWorkoutDraft` into an unchecked log shape.
    ///
    /// Hang and pull drafts become exercises with one unchecked set each.
    /// Rest exercises are dropped. When a hang/pull had `restDuration > 0`, that
    /// value becomes `restAfterSeconds`; otherwise the default (180) is used.
    /// Returns `nil` when nothing migratable remains (empty or rest-only).
    static func migrating(from draft: FreeWorkoutDraft) -> FreeWorkoutLog? {
        let exercises: [FreeExercise] = draft.exercises.compactMap { draftExercise in
            switch draftExercise.kind {
            case .rest:
                return nil
            case .hang:
                return FreeExercise(
                    type: .hang,
                    title: draftExercise.title,
                    holdSelection: Self.holdSelection(from: draftExercise),
                    restAfterSeconds: Self.restAfterSeconds(from: draftExercise.restDuration),
                    sets: [
                        FreeSet(
                            weightKGF: draftExercise.externalLoadKGF,
                            duration: draftExercise.workDuration,
                            reps: nil
                        )
                    ]
                )
            case .pull:
                return FreeExercise(
                    type: .pullUp,
                    title: draftExercise.title,
                    holdSelection: Self.holdSelection(from: draftExercise),
                    restAfterSeconds: Self.restAfterSeconds(from: draftExercise.restDuration),
                    sets: [
                        FreeSet(
                            weightKGF: draftExercise.externalLoadKGF,
                            duration: nil,
                            reps: draftExercise.repetitions
                        )
                    ]
                )
            }
        }
        guard !exercises.isEmpty else { return nil }
        return FreeWorkoutLog(exercises: exercises)
    }

    private static func holdSelection(from draft: FreeWorkoutExerciseDraft) -> FreeWorkoutHoldSelection {
        if let contactID = draft.contactID {
            return .exact(
                FreeWorkoutHoldSelection.ExactContact(
                    contactID: contactID,
                    kind: draft.contactKind ?? draft.holdKind,
                    shape: draft.contactShape,
                    depth: draft.contactDepth,
                    fingerCapacity: draft.contactFingerCapacity
                )
            )
        }
        if let holdKind = draft.holdKind {
            return .generic(holdKind)
        }
        return .generic(.jug)
    }

    private static func restAfterSeconds(from restDuration: TimeInterval) -> TimeInterval {
        restDuration > 0 ? restDuration : FreeExercise.defaultRestAfterSeconds
    }
}
