import Foundation

/// Pure finish pipeline for free-workout logs: history, discard, template, Health inputs.
///
/// Health segments are derived from completed hang/pull sets only (no rest steps).
/// Hang duration uses the set's duration (default 10s). Pull-ups use `set.duration`
/// when present, otherwise a fixed 5s work marker so `markSessionComplete` can
/// record activity without inventing a parallel Health path.
enum FreeWorkoutFinish {
    static let defaultTitle = "Free workout"
    /// Pull-up work marker when the set has no explicit duration (matches Metolius pull-up timing).
    static let defaultPullUpWorkDuration: TimeInterval = 5
    static let planID = "free.workout.log"

    static func completedSetCount(in log: FreeWorkoutLog) -> Int {
        log.exercises.reduce(0) { partial, exercise in
            partial + exercise.sets.filter(\.isCompleted).count
        }
    }

    /// Clears the active log without writing history.
    static func discardActive(defaults: UserDefaults = .standard) {
        ActiveFreeWorkoutStore.clear(defaults: defaults)
    }

    /// Appends `finishedLog()` to history and clears active. Returns `nil` when
    /// there are zero completed sets (active is left unchanged).
    @discardableResult
    static func persistToHistory(
        _ log: FreeWorkoutLog,
        defaults: UserDefaults = .standard
    ) -> FreeWorkoutLog? {
        guard completedSetCount(in: log) > 0 else { return nil }
        let finished = log.finishedLog()
        FreeWorkoutHistoryStore.append(finished, defaults: defaults)
        ActiveFreeWorkoutStore.clear(defaults: defaults)
        return finished
    }

    /// Saves a named template from a finished log via `finished.templateClone()`.
    /// Returns `nil` when the trimmed name is empty.
    @discardableResult
    static func saveTemplate(
        name: String,
        finished: FreeWorkoutLog,
        defaults: UserDefaults = .standard
    ) -> FreeWorkoutTemplate? {
        let trimmed = name.trimmingCharacters(in: .whitespacesAndNewlines)
        guard !trimmed.isEmpty else { return nil }
        let template = FreeWorkoutTemplate(
            name: trimmed,
            log: finished.templateClone()
        )
        FreeWorkoutTemplateStore.save(template, defaults: defaults)
        return template
    }

    /// Inputs for `AppStore.markSessionComplete` — session bounds + work steps
    /// derived from completed sets (simplified: no inter-set rest segments).
    struct HealthRecordingInput: Equatable {
        let plan: TrainingPlan
        let sessionSteps: [WorkoutStep]
        let session: WorkoutSessionRecord
        let startDate: Date
        let endDate: Date
    }

    static func healthRecordingInput(
        from finished: FreeWorkoutLog,
        title: String = defaultTitle,
        endDate: Date = Date()
    ) -> HealthRecordingInput {
        let resolvedTitle = title.trimmingCharacters(in: .whitespacesAndNewlines).isEmpty
            ? defaultTitle
            : title.trimmingCharacters(in: .whitespacesAndNewlines)
        let steps = workoutSteps(from: finished)
        let plan = TrainingPlan(
            id: planID,
            title: resolvedTitle,
            subtitle: "Logged on the fly",
            level: "Custom",
            sourceLabel: "Created in Hang Ten",
            sourceURL: nil,
            provenance: .custom,
            boardID: finished.boardID,
            steps: steps,
            isFreeWorkout: true
        )
        let measurements = steps.map { step in
            WorkoutStepMeasurement(
                stepID: step.id,
                plannedActiveDuration: step.activeDuration,
                intervals: [],
                peakLoadKGF: nil,
                sampleCount: 0,
                status: .unmeasured,
                handUse: step.handUse,
                side: step.side,
                action: step.action,
                repetitions: step.repetitions,
                completedRepetitions: step.repetitions,
                externalLoadKGF: step.externalLoadKGF,
                isRest: step.isRestStep
            )
        }
        let record = WorkoutSessionRecord(
            id: UUID(),
            planID: plan.id,
            planTitle: plan.title,
            recordedAt: endDate,
            startDate: finished.startedAt,
            endDate: endDate,
            motherboardIdentifier: nil,
            batteryValue: nil,
            steps: measurements,
            stepTitles: steps.map(\.title)
        )
        return HealthRecordingInput(
            plan: plan,
            sessionSteps: steps,
            session: record,
            startDate: finished.startedAt,
            endDate: endDate
        )
    }

    // MARK: - Step derivation

    static func workoutSteps(from finished: FreeWorkoutLog) -> [WorkoutStep] {
        var steps: [WorkoutStep] = []
        var number = 1
        for exercise in finished.exercises {
            for set in exercise.sets where set.isCompleted {
                steps.append(step(for: exercise, set: set, number: number))
                number += 1
            }
        }
        return steps
    }

    private static func step(
        for exercise: FreeExercise,
        set: FreeSet,
        number: Int
    ) -> WorkoutStep {
        let workDuration: TimeInterval
        let phase: WorkoutPhase
        let action: WorkoutAction
        let reps: Int?
        let instruction: String
        let accessory: String

        switch exercise.type {
        case .hang:
            workDuration = FreeWorkoutGuidedHangCountdown.resolvedDuration(set.duration)
            phase = .hang
            action = .hang
            reps = nil
            instruction = "Hang for \(Int(workDuration)) seconds."
            accessory = "\(Int(workDuration))s hang"
        case .pullUp:
            workDuration = max(1, set.duration ?? defaultPullUpWorkDuration)
            phase = .pull
            action = .loadedLift
            let resolvedReps = max(1, set.reps ?? 1)
            reps = resolvedReps
            instruction = "Do \(resolvedReps) pull-ups."
            accessory = "\(resolvedReps) reps"
        }

        let load = (set.weightKGF ?? 0) == 0 ? nil : set.weightKGF
        let handUse: WorkoutHandUse = exercise.hand == .both ? .double : .single
        return WorkoutStep(
            id: "free.log.\(set.id.uuidString)",
            number: number,
            title: exercise.title,
            instruction: instruction,
            accessory: accessory,
            duration: workDuration,
            phase: phase,
            segments: [
                WorkoutSegment(
                    kind: .work,
                    target: .fromLegacyTargets(workRequirements(for: exercise.holdSelection)),
                    timing: .fixed,
                    duration: workDuration
                )
            ],
            handUse: handUse,
            side: exercise.hand,
            action: action,
            repetitions: reps,
            externalLoadKGF: load
        )
    }

    private static func workRequirements(
        for selection: FreeWorkoutHoldSelection
    ) -> [ContactRequirement] {
        switch selection {
        case .generic(let kind):
            return [.kind(kind)]
        case .exact(let exact):
            return [
                ContactRequirement(
                    contactID: exact.contactID,
                    kind: exact.kind,
                    shape: exact.shape,
                    depth: exact.depth,
                    fingerCapacity: exact.fingerCapacity,
                    handCapacity: nil,
                    selection: .single
                )
            ]
        }
    }
}
