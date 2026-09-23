import Foundation

enum FreeWorkoutExerciseKind: String, Codable, CaseIterable, Hashable {
    case hang
    case pull
    case rest

    var label: String {
        switch self {
        case .hang: "Hang"
        case .pull: "Pull-ups"
        case .rest: "Rest"
        }
    }
}

struct FreeWorkoutExerciseDraft: Codable, Hashable, Identifiable {
    var id: String
    var kind: FreeWorkoutExerciseKind
    var title: String
    var holdKind: HoldKind?
    /// Exact board contact when the athlete picked a specific hold.
    var contactID: String?
    var contactKind: HoldKind?
    var contactShape: HoldShape?
    var contactDepth: HoldDepth?
    var contactFingerCapacity: Int?
    var workDuration: TimeInterval
    var restDuration: TimeInterval
    var externalLoadKGF: Double?
    var repetitions: Int?
    var gripType: GripType?

    init(
        id: String = UUID().uuidString,
        kind: FreeWorkoutExerciseKind,
        title: String? = nil,
        holdKind: HoldKind? = nil,
        contactID: String? = nil,
        contactKind: HoldKind? = nil,
        contactShape: HoldShape? = nil,
        contactDepth: HoldDepth? = nil,
        contactFingerCapacity: Int? = nil,
        workDuration: TimeInterval = 10,
        restDuration: TimeInterval = 60,
        externalLoadKGF: Double? = nil,
        repetitions: Int? = nil,
        gripType: GripType? = nil
    ) {
        self.id = id
        self.kind = kind
        self.title = title ?? kind.label
        self.holdKind = holdKind
        self.contactID = contactID
        self.contactKind = contactKind
        self.contactShape = contactShape
        self.contactDepth = contactDepth
        self.contactFingerCapacity = contactFingerCapacity
        self.workDuration = workDuration
        self.restDuration = restDuration
        self.externalLoadKGF = externalLoadKGF
        self.repetitions = repetitions
        self.gripType = gripType
    }

    static func hang() -> FreeWorkoutExerciseDraft {
        FreeWorkoutExerciseDraft(kind: .hang, holdKind: .jug, workDuration: 10, restDuration: 60)
    }

    static func pull() -> FreeWorkoutExerciseDraft {
        FreeWorkoutExerciseDraft(
            kind: .pull, holdKind: .jug, workDuration: 25, restDuration: 60,
            repetitions: 5
        )
    }

    static func rest() -> FreeWorkoutExerciseDraft {
        FreeWorkoutExerciseDraft(kind: .rest, workDuration: 0, restDuration: 120)
    }
}

struct FreeWorkoutDraft: Codable, Hashable {
    var title: String
    var exercises: [FreeWorkoutExerciseDraft]

    static var starter: FreeWorkoutDraft {
        FreeWorkoutDraft(title: "Free workout", exercises: [.hang(), .pull(), .rest()])
    }

    func trainingPlan() -> TrainingPlan {
        let steps = exercises.enumerated().map { index, exercise in
            step(for: exercise, number: index + 1)
        }
        return TrainingPlan(
            id: "free.workout",
            title: title.trimmingCharacters(in: .whitespacesAndNewlines).isEmpty ? "Free workout" : title,
            subtitle: "Built on the fly",
            level: "Custom",
            sourceLabel: "Created in Hang Ten",
            sourceURL: nil,
            provenance: .custom,
            boardID: nil,
            steps: steps,
            isFreeWorkout: true
        )
    }

    private func step(for exercise: FreeWorkoutExerciseDraft, number: Int) -> WorkoutStep {
        switch exercise.kind {
        case .rest:
            let duration = max(1, exercise.restDuration)
            return WorkoutStep(
                id: "free.\(exercise.id)",
                number: number,
                title: exercise.title,
                instruction: "Rest.",
                accessory: FreeWorkoutDraft.durationLabel(duration) + " rest",
                duration: duration,
                phase: .rest,
                segments: [
                    WorkoutSegment(kind: .rest, target: nil, timing: .fixed, duration: duration)
                ]
            )
        case .hang:
            return timedStep(
                for: exercise,
                number: number,
                phase: .hang,
                action: .hang,
                instruction: "Hang for \(Int(exercise.workDuration)) seconds."
            )
        case .pull:
            let reps = max(1, exercise.repetitions ?? 5)
            let step = timedStep(
                for: exercise,
                number: number,
                phase: .pull,
                action: .loadedLift,
                instruction: "Do \(reps) pull-ups."
            )
            return WorkoutStep(
                id: step.id, number: step.number, title: step.title,
                instruction: step.instruction, accessory: "\(reps) reps",
                duration: step.duration, phase: step.phase, segments: step.segments,
                gripType: step.gripType, handUse: step.handUse, side: step.side,
                action: step.action, repetitions: reps,
                externalLoadKGF: step.externalLoadKGF,
                timedWorkDuration: step.timedWorkDuration
            )
        }
    }

    private func timedStep(
        for exercise: FreeWorkoutExerciseDraft,
        number: Int,
        phase: WorkoutPhase,
        action: WorkoutAction,
        instruction: String
    ) -> WorkoutStep {
        let work = max(1, exercise.workDuration)
        let rest = max(0, exercise.restDuration)
        var segments = [
            WorkoutSegment(
                kind: .work,
                target: .fromLegacyTargets(workRequirements(for: exercise)),
                timing: .fixed,
                duration: work
            )
        ]
        if rest > 0 {
            segments.append(
                WorkoutSegment(kind: .rest, target: nil, timing: .fixed, duration: rest)
            )
        }
        let load = (exercise.externalLoadKGF ?? 0) == 0 ? nil : exercise.externalLoadKGF
        return WorkoutStep(
            id: "free.\(exercise.id)",
            number: number,
            title: exercise.title,
            instruction: instruction,
            accessory: "\(Int(work))s \(phase.label.lowercased())",
            duration: work + rest,
            phase: phase,
            segments: segments,
            gripType: exercise.gripType,
            handUse: .double,
            side: .both,
            action: action,
            externalLoadKGF: load,
            timedWorkDuration: rest > 0 ? work : nil
        )
    }

    private func workRequirements(for exercise: FreeWorkoutExerciseDraft) -> [ContactRequirement] {
        if let contactID = exercise.contactID {
            return [
                ContactRequirement(
                    contactID: contactID,
                    kind: exercise.contactKind,
                    shape: exercise.contactShape,
                    depth: exercise.contactDepth,
                    fingerCapacity: exercise.contactFingerCapacity,
                    handCapacity: nil,
                    selection: .single
                )
            ]
        }
        guard let holdKind = exercise.holdKind else { return [] }
        return [.kind(holdKind)]
    }

    static func durationLabel(_ duration: TimeInterval) -> String {
        let seconds = Int(duration)
        if seconds >= 60 && seconds % 60 == 0 {
            return "\(seconds / 60)m"
        }
        if seconds >= 60 {
            return "\(seconds / 60)m \(seconds % 60)s"
        }
        return "\(seconds)s"
    }
}

enum FreeWorkoutDraftStore {
    static let lastDraftKey = "HangTen.freeWorkout.lastDraft.v1"

    static func load(defaults: UserDefaults = .standard) -> FreeWorkoutDraft? {
        #if DEBUG
        if ProcessInfo.processInfo.environment["HANGTEN_REVIEW_RESET_FREE_WORKOUT"] == "1" {
            defaults.removeObject(forKey: lastDraftKey)
            return nil
        }
        #endif
        guard let data = defaults.data(forKey: lastDraftKey) else { return nil }
        return try? JSONDecoder().decode(FreeWorkoutDraft.self, from: data)
    }

    static func save(_ draft: FreeWorkoutDraft, defaults: UserDefaults = .standard) {
        guard let data = try? JSONEncoder().encode(draft) else { return }
        defaults.set(data, forKey: lastDraftKey)
    }
}
