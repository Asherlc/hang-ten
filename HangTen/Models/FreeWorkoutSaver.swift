import Foundation

enum FreeWorkoutSaverError: Error, Equatable {
    case noSavableSteps
}

enum FreeWorkoutSaver {
    static func routineDefinition(from draft: FreeWorkoutDraft, title: String) throws -> CustomRoutineDefinition {
        var steps = draft.exercises.flatMap(stepDefinitions(for:))
        // Custom routines cannot end with a rest step, so strip trailing rests.
        while let last = steps.last, last.phase == .rest {
            steps.removeLast()
        }
        guard !steps.isEmpty else {
            throw FreeWorkoutSaverError.noSavableSteps
        }
        let trimmed = title.trimmingCharacters(in: .whitespacesAndNewlines)
        return CustomRoutineDefinition(
            id: "custom.\(UUID().uuidString)",
            title: trimmed.isEmpty ? "Free workout" : trimmed,
            subtitle: "Saved from a free workout",
            difficulty: nil,
            category: "custom",
            tags: ["free-workout"],
            targetMode: .generic,
            steps: steps
        )
    }

    private static func stepDefinitions(for exercise: FreeWorkoutExerciseDraft) -> [WorkoutStepDefinition] {
        switch exercise.kind {
        case .rest:
            let duration = max(1, exercise.restDuration)
            return [WorkoutStepDefinition(
                id: "free.\(exercise.id)",
                title: exercise.title,
                instruction: "Rest.",
                accessory: "\(Int(duration))s rest",
                duration: duration,
                phase: .rest,
                segments: [
                    WorkoutSegmentDefinition(
                        kind: .rest,
                        target: nil,
                        timing: .fixed,
                        duration: duration
                    )
                ],
                handUse: .double,
                side: .both,
                action: .hang
            )]
        case .hang, .pull:
            guard exercise.holdKind != nil || exercise.contactKind != nil else {
                return []
            }
            let work = max(1, exercise.workDuration)
            let rest = max(0, exercise.restDuration)
            let isPull = exercise.kind == .pull
            let reps = isPull ? max(1, exercise.repetitions ?? 5) : nil
            let load = (exercise.externalLoadKGF ?? 0) == 0 ? nil : exercise.externalLoadKGF

            let workStep = WorkoutStepDefinition(
                id: "free.\(exercise.id)",
                title: exercise.title,
                instruction: exercise.kind == .pull ? "Do pull-ups." : "Hang.",
                accessory: isPull ? "\(reps ?? 0) reps" : "\(Int(work))s hang",
                duration: rest > 0 ? work : work + rest,
                phase: isPull ? .pull : .hang,
                segments: [
                    WorkoutSegmentDefinition(
                        kind: .work,
                        target: .fromLegacyTargets(targets(for: exercise)),
                        timing: .fixed,
                        duration: work
                    )
                ],
                gripType: exercise.gripType,
                activeDuration: rest > 0 ? work : nil,
                handUse: .double,
                side: .both,
                action: isPull ? .loadedLift : .hang,
                repetitions: reps,
                externalLoadKGF: load
            )

            if rest > 0 {
                let restStep = WorkoutStepDefinition(
                    id: "free.\(exercise.id).rest",
                    title: "Rest",
                    instruction: "Rest.",
                    accessory: "\(Int(rest))s rest",
                    duration: rest,
                    phase: .rest,
                    segments: [
                        WorkoutSegmentDefinition(
                            kind: .rest,
                            target: nil,
                            timing: .fixed,
                            duration: rest
                        )
                    ],
                    handUse: .double,
                    side: .both,
                    action: .hang
                )
                return [workStep, restStep]
            }
            return [workStep]
        }
    }

    private static func targets(for exercise: FreeWorkoutExerciseDraft) -> [ContactRequirement] {
        let kind = exercise.holdKind ?? exercise.contactKind
        guard let kind else { return [] }
        return [.kind(kind)]
    }
}
