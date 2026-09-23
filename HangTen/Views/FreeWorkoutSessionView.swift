import SwiftUI

private struct EditingStep: Identifiable {
    let id: String
}

struct FreeWorkoutSessionView: View {
    @EnvironmentObject private var store: AppStore
    @Environment(\.dismiss) private var dismiss

    let plan: TrainingPlan
    let draft: FreeWorkoutDraft
    let saveAsPlan: Bool
    let onDismiss: (() -> Void)?

    @State private var steps: [WorkoutStep]
    @State private var timeline: WorkoutTimeline
    @State private var clock = WorkoutClock()
    @State private var liftCompletion = WorkoutLiftCompletion()
    @State private var startedAt = Date()
    @State private var isPaused = false
    @State private var editingStep: EditingStep?
    @State private var didFinish = false
    @State private var saveError: String?

    init(plan: TrainingPlan, draft: FreeWorkoutDraft, saveAsPlan: Bool, onDismiss: (() -> Void)? = nil) {
        self.plan = plan
        self.draft = draft
        self.saveAsPlan = saveAsPlan
        self.onDismiss = onDismiss
        _steps = State(initialValue: plan.steps)
        _timeline = State(initialValue: WorkoutTimeline(steps: plan.steps))
    }

    private var board: BoardRevision {
        store.board(for: plan)
    }

    var body: some View {
        TimelineView(.periodic(from: .now, by: 0.25)) { _ in
            sessionContent
        }
        .navigationTitle(plan.title)
        .navigationBarTitleDisplayMode(.inline)
        .onAppear(perform: startIfNeeded)
        .sheet(item: $editingStep) { edit in
            if let step = steps.first(where: { $0.id == edit.id }) {
                FreeWorkoutStepEditSheet(
                    step: step,
                    liftCompletion: liftCompletion
                ) { updates in
                    apply(updates, to: edit.id)
                }
            }
        }
        .alert("Couldn't save routine", isPresented: saveAlertBinding) {
            Button("OK", role: .cancel) { saveError = nil }
        } message: {
            Text(saveError ?? "An unknown error occurred.")
        }
        .accessibilityElement(children: .contain)
        .accessibilityIdentifier("freeWorkout.session")
    }

    private var sessionContent: some View {
        let elapsed = clock.elapsed
        let isComplete = elapsed >= timeline.duration
        let step = timeline.step(at: elapsed)
        let highlightedIDs = Set(step.map { WorkoutHighlightResolver.contactIDs(for: $0, on: board) } ?? [])

        return VStack(alignment: .leading, spacing: 16) {
            if let step {
                currentSetCard(step: step, elapsed: elapsed, isComplete: isComplete)
            }
            BoardMapView(board: board, highlightedHoldIDs: highlightedIDs)
                .clipShape(RoundedRectangle(cornerRadius: 18, style: .continuous))
            quickAdjustBar(step: step)
            controlBar(step: step, elapsed: elapsed, isComplete: isComplete)
            Spacer(minLength: 0)
        }
        .padding(.horizontal, 20)
        .padding(.vertical, 18)
        .background(Color.hangBackground)
    }

    private func currentSetCard(step: WorkoutStep, elapsed: TimeInterval, isComplete: Bool) -> some View {
        let remaining = max(0, step.duration - timeline.elapsedInStep(at: elapsed))
        return Button {
            editingStep = EditingStep(id: step.id)
        } label: {
            VStack(alignment: .leading, spacing: 6) {
                SectionLabel(title: isComplete ? "Finished" : "Current set · tap to edit")
                Text(step.title)
                    .font(.system(size: 21, weight: .bold, design: .rounded))
                    .foregroundStyle(Color.hangInk)
                HStack(spacing: 12) {
                    Text(FreeWorkoutDraft.durationLabel(remaining) + " left")
                    if let load = step.externalLoadKGF {
                        Text("+\(load.formatted()) kg")
                    }
                    if let reps = step.repetitions {
                        let done = liftCompletion.completedRepetitions(for: step)
                        Text("\(done)/\(reps) reps")
                    }
                }
                .font(.system(size: 14, weight: .bold, design: .rounded))
                .foregroundStyle(Color.hangMuted)
            }
            .hangCard()
        }
        .buttonStyle(.plain)
        .accessibilityIdentifier("freeWorkout.currentSet")
    }

    @ViewBuilder
    private func quickAdjustBar(step: WorkoutStep?) -> some View {
        if let step, !step.isRestStep {
            HStack(spacing: 10) {
                if step.externalLoadKGF != nil || step.action == .loadedLift || step.phase == .hang {
                    adjustGroup(title: "Weight", down: {
                        nudge(step, FreeWorkoutStepUpdates(externalLoadKGF: max(0, (step.externalLoadKGF ?? 0) - 1)))
                    }, up: {
                        nudge(step, FreeWorkoutStepUpdates(externalLoadKGF: (step.externalLoadKGF ?? 0) + 1))
                    })
                }
                adjustGroup(title: "Time", down: {
                    adjustWorkTime(step, by: -5)
                }, up: {
                    adjustWorkTime(step, by: 5)
                })
                if step.action == .loadedLift {
                    adjustGroup(title: "Reps", down: {
                        nudge(step, FreeWorkoutStepUpdates(repetitions: max(1, (step.repetitions ?? 1) - 1)))
                    }, up: {
                        nudge(step, FreeWorkoutStepUpdates(repetitions: (step.repetitions ?? 1) + 1))
                    })
                    Button("Log rep") {
                        liftCompletion.completeLift(for: step)
                    }
                    .buttonStyle(.bordered)
                    .tint(.hangGreenDark)
                    .accessibilityIdentifier("freeWorkout.logRep")
                }
            }
            .font(.system(size: 14, weight: .bold, design: .rounded))
        }
    }

    private func adjustGroup(title: String, down: @escaping () -> Void, up: @escaping () -> Void) -> some View {
        HStack(spacing: 6) {
            Button("−", action: down)
                .accessibilityIdentifier("freeWorkout.adjustDown.\(title)")
            Text(title)
            Button("+", action: up)
                .accessibilityIdentifier("freeWorkout.adjustUp.\(title)")
        }
        .buttonStyle(.bordered)
        .tint(.hangGreenDark)
    }

    @ViewBuilder
    private func controlBar(step: WorkoutStep?, elapsed: TimeInterval, isComplete: Bool) -> some View {
        HStack(spacing: 10) {
            Button(isPaused ? "Resume" : "Pause") {
                isPaused ? clock.start(initialCountdown: 0) : clock.pause()
                isPaused.toggle()
            }
            .buttonStyle(.bordered)
            .tint(.hangGreenDark)
            Button("Complete set") {
                clock.seek(to: timeline.skipTarget(from: elapsed) ?? timeline.duration)
            }
            .buttonStyle(.borderedProminent)
            .tint(.hangGreenDark)
            .disabled(step == nil || isComplete)
            .accessibilityIdentifier("freeWorkout.completeSet")
            Button("Skip") {
                clock.seek(to: timeline.skipTarget(from: elapsed) ?? timeline.duration)
            }
            .buttonStyle(.bordered)
            .tint(.hangGreenDark)
            .disabled(step == nil || isComplete)
            .accessibilityIdentifier("freeWorkout.skip")
            Spacer()
            Button("Finish") {
                finish()
            }
            .buttonStyle(.bordered)
            .tint(.red)
            .accessibilityIdentifier("freeWorkout.finish")
        }
    }

    private func nudge(_ step: WorkoutStep, _ updates: FreeWorkoutStepUpdates) {
        apply(updates, to: step.id)
    }

    private func adjustWorkTime(_ step: WorkoutStep, by delta: TimeInterval) {
        let workDuration = max(1, step.activeDuration + delta)
        nudge(
            step,
            FreeWorkoutStepUpdates(
                duration: step.restDuration + workDuration,
                timedWorkDuration: step.timedWorkDuration == nil ? nil : workDuration
            )
        )
    }

    private func apply(_ updates: FreeWorkoutStepUpdates, to stepID: String) {
        guard steps.contains(where: { $0.id == stepID }) else { return }
        if clock.isRunning {
            let currentStepID = timeline.step(at: clock.elapsed)?.id
            guard stepID == currentStepID || currentStepID == nil else { return }
        }
        timeline.updateStep(id: stepID, updates)
        steps = timeline.currentSteps
    }

    private func startIfNeeded() {
        guard !clock.isRunning, !didFinish else { return }
        startedAt = Date()
        clock.start(initialCountdown: 0)
    }

    private func finish() {
        guard !didFinish else { return }
        didFinish = true
        clock.pause()
        let endDate = Date()
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
                completedRepetitions: step.action == .loadedLift
                    ? liftCompletion.completedRepetitions(for: step)
                    : nil,
                externalLoadKGF: step.action == .loadedLift
                    ? liftCompletion.externalLoadKGF(for: step)
                    : step.externalLoadKGF,
                isRest: step.isRestStep
            )
        }
        let record = WorkoutSessionRecord(
            id: UUID(),
            planID: plan.id,
            planTitle: plan.title,
            recordedAt: endDate,
            startDate: startedAt,
            endDate: endDate,
            motherboardIdentifier: nil,
            batteryValue: nil,
            steps: measurements,
            stepTitles: steps.map(\.title)
        )
        store.markSessionComplete(
            plan,
            startDate: startedAt,
            endDate: endDate,
            sessionSteps: steps,
            session: record
        )
        if saveAsPlan {
            do {
                let executedDraft = buildDraft(from: steps, title: draft.title)
                let definition = try FreeWorkoutSaver.routineDefinition(from: executedDraft, title: plan.title)
                try store.saveCustomRoutine(definition)
            } catch {
                saveError = error.localizedDescription
                return
            }
        }
        if let onDismiss { onDismiss() } else { dismiss() }
    }

    private func buildDraft(from steps: [WorkoutStep], title: String) -> FreeWorkoutDraft {
        let exercises = steps.map { step -> FreeWorkoutExerciseDraft in
            let kind: FreeWorkoutExerciseKind
            if step.isRestStep {
                kind = .rest
            } else if step.action == .loadedLift {
                kind = .pull
            } else {
                kind = .hang
            }
            return FreeWorkoutExerciseDraft(
                id: step.id.replacingOccurrences(of: "free.", with: ""),
                kind: kind,
                title: step.title,
                holdKind: step.workRequirements.first(where: { $0.contactID == nil })?.kind,
                contactKind: step.workRequirements.first(where: { $0.contactID != nil })?.kind,
                workDuration: step.activeDuration,
                restDuration: step.isRestStep
                    ? step.duration
                    : max(0, step.duration - step.activeDuration),
                externalLoadKGF: step.externalLoadKGF,
                repetitions: step.repetitions,
                gripType: step.gripType
            )
        }
        return FreeWorkoutDraft(title: title, exercises: exercises)
    }

    private var saveAlertBinding: Binding<Bool> {
        Binding(
            get: { saveError != nil },
            set: { isPresented in
                if !isPresented {
                    saveError = nil
                    if let onDismiss { onDismiss() } else { dismiss() }
                }
            }
        )
    }
}

private struct FreeWorkoutStepEditSheet: View {
    @Environment(\.dismiss) private var dismiss
    let step: WorkoutStep
    let liftCompletion: WorkoutLiftCompletion
    let onSave: (FreeWorkoutStepUpdates) -> Void

    @State private var duration: Double
    @State private var loadText: String
    @State private var reps: Int

    init(
        step: WorkoutStep,
        liftCompletion: WorkoutLiftCompletion,
        onSave: @escaping (FreeWorkoutStepUpdates) -> Void
    ) {
        self.step = step
        self.liftCompletion = liftCompletion
        self.onSave = onSave
        _duration = State(initialValue: step.duration)
        let load = step.action == .loadedLift
            ? (liftCompletion.externalLoadKGF(for: step) ?? step.externalLoadKGF)
            : step.externalLoadKGF
        _loadText = State(initialValue: load.map { $0.formatted() } ?? "")
        _reps = State(initialValue: step.repetitions ?? 1)
    }

    var body: some View {
        NavigationStack {
            Form {
                Stepper("Duration: \(Int(duration))s", value: $duration, in: 1...3600, step: 5)
                if !step.isRestStep {
                    TextField("Added weight (kg)", text: $loadText)
                        .keyboardType(.numbersAndPunctuation)
                    if step.action == .loadedLift {
                        Stepper("Reps: \(reps)", value: $reps, in: 1...100)
                    }
                }
            }
            .navigationTitle("Edit set")
            .navigationBarTitleDisplayMode(.inline)
            .toolbar {
                ToolbarItem(placement: .confirmationAction) {
                    Button("Done") {
                        let newWork: TimeInterval? = step.timedWorkDuration != nil
                            ? min(step.activeDuration, duration)
                            : nil
                        onSave(FreeWorkoutStepUpdates(
                            duration: duration,
                            timedWorkDuration: newWork,
                            externalLoadKGF: Double(loadText),
                            repetitions: step.action == .loadedLift ? reps : nil
                        ))
                        dismiss()
                    }
                }
            }
        }
        .accessibilityIdentifier("freeWorkout.editSheet")
    }
}