import SwiftUI

private struct FreeWorkoutSetTarget: Identifiable, Hashable {
    let exerciseID: UUID
    let setID: UUID

    var id: UUID { setID }
}

/// Live Strong-style free-workout log: exercises, sets, board highlight, rest timer.
struct FreeWorkoutLogSessionView: View {
    @EnvironmentObject private var store: AppStore
    @Environment(\.dismiss) private var dismiss

    /// Called after Finish confirm so the parent start sheet can dismiss entirely.
    var onFinished: (() -> Void)?
    /// Pops back to the start sheet (Resume / Discard) without clearing the active log.
    var onClose: (() -> Void)?

    @State private var log: FreeWorkoutLog
    @State private var restTimer = FreeWorkoutRestTimer()
    @State private var showsFinishConfirm = false
    @State private var showsDiscardAlert = false
    @State private var showsTemplatePrompt = false
    @State private var templateName = ""
    @State private var finishedForTemplate: FreeWorkoutLog?
    @State private var didFinish = false
    @State private var showsAddExercise = false
    @State private var guidedHangTarget: FreeWorkoutSetTarget?
    @State private var logSetTarget: FreeWorkoutSetTarget?

    init(onFinished: (() -> Void)? = nil, onClose: (() -> Void)? = nil) {
        self.onFinished = onFinished
        self.onClose = onClose
        _log = State(initialValue: ActiveFreeWorkoutStore.load() ?? FreeWorkoutLog())
    }

    private var board: BoardRevision {
        if let boardID = log.boardID {
            return BoardCatalog.board(for: boardID)
        }
        return store.selectedBoard
    }

    private var focusedTarget: (exerciseID: UUID, setID: UUID)? {
        for exercise in log.exercises {
            if let set = exercise.sets.first(where: { !$0.isCompleted }) {
                return (exercise.id, set.id)
            }
        }
        return nil
    }

    private var focusedExercise: FreeExercise? {
        guard let focusedTarget else { return nil }
        return log.exercises.first { $0.id == focusedTarget.exerciseID }
    }

    private var highlightedHoldIDs: Set<String> {
        guard let exercise = focusedExercise else { return [] }
        return Self.contactIDs(for: exercise.holdSelection, hand: exercise.hand, on: board)
    }

    private var showsRestBar: Bool {
        restTimer.isActive || restTimer.isCompleted
    }

    var body: some View {
        TimelineView(.periodic(from: .now, by: 0.25)) { context in
            let now = context.date
            VStack(spacing: 0) {
                header(at: now)
                ScrollView {
                    VStack(alignment: .leading, spacing: 16) {
                        BoardMapView(board: board, highlightedHoldIDs: highlightedHoldIDs)
                            .frame(minHeight: 180)
                            .clipShape(RoundedRectangle(cornerRadius: 18, style: .continuous))
                            .accessibilityIdentifier("freeWorkout.boardMap")

                        if showsRestBar {
                            restBar(at: now)
                        }

                        exercisesSection

                        Button {
                            showsAddExercise = true
                        } label: {
                            Label("Add Exercise", systemImage: "plus.circle.fill")
                                .frame(maxWidth: .infinity)
                        }
                        .buttonStyle(.bordered)
                        .controlSize(.large)
                        .accessibilityIdentifier("freeWorkout.addExercise.button")
                    }
                    .padding(.horizontal, 20)
                    .padding(.vertical, 16)
                }
            }
            .background(Color.hangBackground)
            .onChange(of: now) { _, date in
                var timer = restTimer
                timer.tick(at: date)
                if timer != restTimer {
                    restTimer = timer
                }
            }
        }
        .navigationTitle("Free workout")
        .navigationBarTitleDisplayMode(.inline)
        .navigationBarBackButtonHidden(true)
        .toolbar {
            ToolbarItem(placement: .cancellationAction) {
                Button("Close") {
                    if let onClose {
                        onClose()
                    } else {
                        dismiss()
                    }
                }
                .accessibilityIdentifier("freeWorkout.close")
            }
            ToolbarItem(placement: .confirmationAction) {
                Button("Finish") { showsFinishConfirm = true }
                    .fontWeight(.semibold)
                    .accessibilityIdentifier("freeWorkout.finish")
            }
        }
        .sheet(isPresented: $showsAddExercise) {
            FreeWorkoutAddExerciseSheet(
                board: board,
                onAdd: { type, hold, hand in
                    addExercise(type: type, holdSelection: hold, hand: hand)
                    showsAddExercise = false
                },
                onCancel: { showsAddExercise = false }
            )
        }
        .fullScreenCover(item: $guidedHangTarget) { target in
            guidedHangCover(for: target)
        }
        .sheet(item: $logSetTarget) { target in
            logSetSheet(for: target)
        }
        .confirmationDialog(
            "End this free workout?",
            isPresented: $showsFinishConfirm,
            titleVisibility: .visible
        ) {
            Button("Finish", role: .destructive) {
                confirmFinish()
            }
            .accessibilityIdentifier("freeWorkout.finish.confirm")
            Button("Cancel", role: .cancel) {}
        } message: {
            Text("Save completed sets to history and Apple Health.")
        }
        .alert("No completed sets", isPresented: $showsDiscardAlert) {
            Button("Discard", role: .destructive) {
                discardAndDismiss()
            }
            .accessibilityIdentifier("freeWorkout.finish.discard")
            Button("Cancel", role: .cancel) {}
        } message: {
            Text("Finish needs at least one completed set. Discard this workout without saving history?")
        }
        .alert("Save as Template?", isPresented: $showsTemplatePrompt) {
            TextField("Template name", text: $templateName)
            Button("Save") {
                saveTemplateAndDismiss()
            }
            .disabled(templateName.trimmingCharacters(in: .whitespacesAndNewlines).isEmpty)
            .accessibilityIdentifier("freeWorkout.template.save")
            Button("Skip", role: .cancel) {
                dismissAfterFinish()
            }
            .accessibilityIdentifier("freeWorkout.template.skip")
        } message: {
            Text("Save completed sets as a reusable unchecked template.")
        }
        .accessibilityElement(children: .contain)
        .accessibilityIdentifier("freeWorkout.log")
    }

    @ViewBuilder
    private func guidedHangCover(for target: FreeWorkoutSetTarget) -> some View {
        if let exercise = log.exercises.first(where: { $0.id == target.exerciseID }),
           let set = exercise.sets.first(where: { $0.id == target.setID })
        {
            let duration = FreeWorkoutGuidedHangCountdown.resolvedDuration(set.duration)
            FreeWorkoutGuidedHangView(
                board: board,
                holdName: holdSubtitle(exercise.holdSelection),
                weightKGF: set.weightKGF,
                duration: duration,
                highlightedHoldIDs: Self.contactIDs(for: exercise.holdSelection, hand: exercise.hand, on: board),
                onComplete: { elapsed in
                    completeGuidedHang(
                        exerciseID: target.exerciseID,
                        setID: target.setID,
                        plannedDuration: duration,
                        elapsed: elapsed
                    )
                    guidedHangTarget = nil
                },
                onCancel: {
                    guidedHangTarget = nil
                }
            )
        } else {
            Color.hangBackground
                .onAppear { guidedHangTarget = nil }
        }
    }

    @ViewBuilder
    private func logSetSheet(for target: FreeWorkoutSetTarget) -> some View {
        if let exercise = log.exercises.first(where: { $0.id == target.exerciseID }),
           let set = exercise.sets.first(where: { $0.id == target.setID })
        {
            FreeWorkoutLogSetSheet(
                exerciseType: exercise.type,
                holdName: holdSubtitle(exercise.holdSelection),
                initialWeightKGF: set.weightKGF,
                initialDuration: set.duration,
                initialReps: set.reps,
                onSave: { weight, duration, reps in
                    completeLoggedSet(
                        exerciseID: target.exerciseID,
                        setID: target.setID,
                        weightKGF: weight,
                        duration: duration,
                        reps: reps
                    )
                    logSetTarget = nil
                },
                onCancel: {
                    logSetTarget = nil
                }
            )
        } else {
            Color.clear
                .onAppear { logSetTarget = nil }
        }
    }

    // MARK: - Header / rest

    private func header(at date: Date) -> some View {
        HStack(alignment: .firstTextBaseline) {
            VStack(alignment: .leading, spacing: 4) {
                SectionLabel(title: "Session")
                Text("Free workout")
                    .font(.system(size: 22, weight: .bold, design: .rounded))
                    .foregroundStyle(Color.hangInk)
                Text(elapsedLabel(at: date))
                    .font(.system(size: 14, weight: .medium, design: .rounded))
                    .foregroundStyle(Color.hangMuted)
                    .accessibilityIdentifier("freeWorkout.elapsed")
            }
            Spacer(minLength: 12)
            Button("Finish") { showsFinishConfirm = true }
                .buttonStyle(.borderedProminent)
                .tint(.hangGreenDark)
                .accessibilityIdentifier("freeWorkout.finish.header")
        }
        .padding(.horizontal, 20)
        .padding(.top, 12)
        .padding(.bottom, 8)
    }

    private func restBar(at now: Date) -> some View {
        let remaining = restTimer.remaining(at: now)
        return VStack(alignment: .leading, spacing: 10) {
            HStack {
                SectionLabel(title: "Rest", tint: .restBlueDeep)
                Spacer()
                Text(countdownLabel(remaining))
                    .font(.system(size: 28, weight: .bold, design: .rounded))
                    .foregroundStyle(Color.restBlueDeep)
                    .monospacedDigit()
                    .accessibilityIdentifier("freeWorkout.rest.remaining")
            }
            HStack(spacing: 8) {
                Button("−30") { adjustRest(by: -30, at: now) }
                    .accessibilityIdentifier("freeWorkout.rest.minus30")
                Button("+30") { adjustRest(by: 30, at: now) }
                    .accessibilityIdentifier("freeWorkout.rest.plus30")
                Button("+1m") { adjustRest(by: 60, at: now) }
                    .accessibilityIdentifier("freeWorkout.rest.plus60")
                Spacer()
                Button("Skip") { skipRest() }
                    .accessibilityIdentifier("freeWorkout.rest.skip")
                Button("Dismiss") { dismissRest() }
                    .accessibilityIdentifier("freeWorkout.rest.dismiss")
            }
            .buttonStyle(.bordered)
            .controlSize(.small)
            .tint(.restBlueDeep)
        }
        .hangCard(padding: 14)
        .accessibilityElement(children: .contain)
        .accessibilityIdentifier("freeWorkout.restBar")
    }

    // MARK: - Exercises

    private var exercisesSection: some View {
        VStack(alignment: .leading, spacing: 12) {
            SectionLabel(title: "Exercises")
            if log.exercises.isEmpty {
                Text("Add a hang or pull-up to start logging sets.")
                    .font(.system(size: 14, weight: .medium, design: .rounded))
                    .foregroundStyle(Color.hangMuted)
                    .hangCard(padding: 14)
            } else {
                ForEach(Array(log.exercises.enumerated()), id: \.element.id) { index, exercise in
                    exerciseCard(exercise, at: index)
                }
            }
        }
    }

    private func exerciseCard(_ exercise: FreeExercise, at index: Int) -> some View {
        let isFocusedExercise = focusedTarget?.exerciseID == exercise.id
        return VStack(alignment: .leading, spacing: 10) {
            HStack(alignment: .firstTextBaseline) {
                VStack(alignment: .leading, spacing: 2) {
                    Text(exercise.title)
                        .font(.system(size: 17, weight: .bold, design: .rounded))
                        .foregroundStyle(Color.hangInk)
                    Text(holdSubtitle(exercise.holdSelection))
                        .font(.system(size: 12, weight: .medium, design: .rounded))
                        .foregroundStyle(Color.hangMuted)
                }
                Spacer()
                Menu {
                    if index > 0 {
                        Button("Move Up") { moveExercise(exercise.id, toOffset: index - 1) }
                    }
                    if index < log.exercises.count - 1 {
                        Button("Move Down") { moveExercise(exercise.id, toOffset: index + 1) }
                    }
                    Button("Delete", role: .destructive) { deleteExercise(exercise.id) }
                } label: {
                    Image(systemName: "ellipsis.circle")
                        .font(.system(size: 20, weight: .medium))
                        .foregroundStyle(Color.hangMuted)
                }
                .accessibilityIdentifier("freeWorkout.exercise.menu.\(exercise.id.uuidString)")
            }

            setHeaderRow(for: exercise)

            ForEach(Array(exercise.sets.enumerated()), id: \.element.id) { setIndex, set in
                setRow(
                    exercise: exercise,
                    set: set,
                    number: setIndex + 1,
                    isFocused: focusedTarget?.exerciseID == exercise.id
                        && focusedTarget?.setID == set.id
                )
            }

            HStack(spacing: 10) {
                Button {
                    addSet(to: exercise.id)
                } label: {
                    Label("Add Set", systemImage: "plus")
                }
                .accessibilityIdentifier("freeWorkout.addSet.\(exercise.id.uuidString)")

                if isFocusedExercise, let focused = focusedTarget, focused.exerciseID == exercise.id {
                    focusedSetActions(exercise: exercise, setID: focused.setID)
                }
            }
            .buttonStyle(.bordered)
            .controlSize(.small)
        }
        .hangCard(padding: 14)
        .overlay {
            if isFocusedExercise {
                RoundedRectangle(cornerRadius: 24, style: .continuous)
                    .stroke(Color.hangGreenDark.opacity(0.55), lineWidth: 2)
            }
        }
        .accessibilityElement(children: .contain)
        .accessibilityIdentifier("freeWorkout.exercise.\(exercise.id.uuidString)")
    }

    private func setHeaderRow(for exercise: FreeExercise) -> some View {
        HStack(spacing: 8) {
            Text("#")
                .frame(width: 28, alignment: .leading)
            Text("kg")
                .frame(maxWidth: .infinity)
            if exercise.type == .hang {
                Text("sec")
                    .frame(maxWidth: .infinity)
            } else {
                Text("reps")
                    .frame(maxWidth: .infinity)
            }
            Text("✓")
                .frame(width: 36, alignment: .center)
        }
        .font(.system(size: 11, weight: .bold, design: .rounded))
        .foregroundStyle(Color.hangMuted)
    }

    private func setRow(
        exercise: FreeExercise,
        set: FreeSet,
        number: Int,
        isFocused: Bool
    ) -> some View {
        HStack(spacing: 8) {
            Text("\(number)")
                .font(.system(size: 15, weight: .bold, design: .rounded))
                .foregroundStyle(isFocused ? Color.hangGreenDark : Color.hangInk)
                .frame(width: 28, alignment: .leading)

            TextField(
                "kg",
                value: weightBinding(exerciseID: exercise.id, setID: set.id),
                format: .number.precision(.fractionLength(0...1))
            )
            .keyboardType(.decimalPad)
            .multilineTextAlignment(.center)
            .font(.system(size: 15, weight: .medium, design: .rounded))
            .padding(.vertical, 6)
            .padding(.horizontal, 4)
            .background(Color.hangBackground, in: RoundedRectangle(cornerRadius: 8, style: .continuous))
            .accessibilityIdentifier("freeWorkout.set.weight.\(set.id.uuidString)")

            if exercise.type == .hang {
                TextField(
                    "sec",
                    value: durationBinding(exerciseID: exercise.id, setID: set.id),
                    format: .number.precision(.fractionLength(0...0))
                )
                .keyboardType(.numberPad)
                .multilineTextAlignment(.center)
                .font(.system(size: 15, weight: .medium, design: .rounded))
                .padding(.vertical, 6)
                .padding(.horizontal, 4)
                .background(Color.hangBackground, in: RoundedRectangle(cornerRadius: 8, style: .continuous))
                .accessibilityIdentifier("freeWorkout.set.duration.\(set.id.uuidString)")
            } else {
                TextField(
                    "reps",
                    value: repsBinding(exerciseID: exercise.id, setID: set.id),
                    format: .number
                )
                .keyboardType(.numberPad)
                .multilineTextAlignment(.center)
                .font(.system(size: 15, weight: .medium, design: .rounded))
                .padding(.vertical, 6)
                .padding(.horizontal, 4)
                .background(Color.hangBackground, in: RoundedRectangle(cornerRadius: 8, style: .continuous))
                .accessibilityIdentifier("freeWorkout.set.reps.\(set.id.uuidString)")
            }

            Button {
                toggleSetCompletion(exerciseID: exercise.id, setID: set.id)
            } label: {
                Image(systemName: set.isCompleted ? "checkmark.circle.fill" : "circle")
                    .font(.system(size: 22, weight: .semibold))
                    .foregroundStyle(set.isCompleted ? Color.hangGreenDark : Color.hangMuted)
            }
            .buttonStyle(.plain)
            .frame(width: 36)
            .accessibilityLabel(set.isCompleted ? "Completed" : "Mark set complete")
            // Focused row keeps a stable id for UITests; others retain per-set ids.
            .accessibilityIdentifier(
                isFocused
                    ? "freeWorkout.set.complete"
                    : "freeWorkout.set.complete.\(set.id.uuidString)"
            )
        }
        .padding(.vertical, 2)
        .background(isFocused ? Color.hangGreen.opacity(0.12) : Color.clear)
        .clipShape(RoundedRectangle(cornerRadius: 10, style: .continuous))
        .accessibilityIdentifier("freeWorkout.set.\(set.id.uuidString)")
    }

    @ViewBuilder
    private func focusedSetActions(exercise: FreeExercise, setID: UUID) -> some View {
        switch exercise.type {
        case .hang:
            Button("Start Set") {
                ensureHangDuration(exerciseID: exercise.id, setID: setID)
                guidedHangTarget = FreeWorkoutSetTarget(exerciseID: exercise.id, setID: setID)
            }
            .buttonStyle(.borderedProminent)
            .tint(.hangGreenDark)
            .accessibilityIdentifier("freeWorkout.startSet")

            Button("Log Set") {
                logSetTarget = FreeWorkoutSetTarget(exerciseID: exercise.id, setID: setID)
            }
            .accessibilityIdentifier("freeWorkout.logSet")

        case .pullUp:
            Button("Mark done") {
                completeSet(exerciseID: exercise.id, setID: setID, mode: .manual)
            }
            .buttonStyle(.borderedProminent)
            .tint(.hangGreenDark)
            .accessibilityIdentifier("freeWorkout.markDone")

            Button("Log Set") {
                logSetTarget = FreeWorkoutSetTarget(exerciseID: exercise.id, setID: setID)
            }
            .accessibilityIdentifier("freeWorkout.logSet")
        }
    }

    // MARK: - Bindings

    private func weightBinding(exerciseID: UUID, setID: UUID) -> Binding<Double?> {
        Binding(
            get: { currentSet(exerciseID: exerciseID, setID: setID)?.weightKGF },
            set: { newValue in
                guard let set = currentSet(exerciseID: exerciseID, setID: setID) else { return }
                mutate { log in
                    log.updateSet(
                        exerciseID: exerciseID,
                        setID: setID,
                        weightKGF: newValue,
                        duration: set.duration,
                        reps: set.reps,
                        tag: set.tag
                    )
                }
            }
        )
    }

    private func durationBinding(exerciseID: UUID, setID: UUID) -> Binding<Double?> {
        Binding(
            get: { currentSet(exerciseID: exerciseID, setID: setID)?.duration },
            set: { newValue in
                guard let set = currentSet(exerciseID: exerciseID, setID: setID) else { return }
                mutate { log in
                    log.updateSet(
                        exerciseID: exerciseID,
                        setID: setID,
                        weightKGF: set.weightKGF,
                        duration: newValue,
                        reps: set.reps,
                        tag: set.tag
                    )
                }
            }
        )
    }

    private func repsBinding(exerciseID: UUID, setID: UUID) -> Binding<Int?> {
        Binding(
            get: { currentSet(exerciseID: exerciseID, setID: setID)?.reps },
            set: { newValue in
                guard let set = currentSet(exerciseID: exerciseID, setID: setID) else { return }
                mutate { log in
                    log.updateSet(
                        exerciseID: exerciseID,
                        setID: setID,
                        weightKGF: set.weightKGF,
                        duration: set.duration,
                        reps: newValue,
                        tag: set.tag
                    )
                }
            }
        )
    }

    private func currentSet(exerciseID: UUID, setID: UUID) -> FreeSet? {
        guard let exercise = log.exercises.first(where: { $0.id == exerciseID }) else { return nil }
        return exercise.sets.first { $0.id == setID }
    }

    // MARK: - Mutations

    private func mutate(_ body: (inout FreeWorkoutLog) -> Void) {
        body(&log)
        ActiveFreeWorkoutStore.save(log)
    }

    private func addExercise(type: FreeExerciseType, holdSelection: FreeWorkoutHoldSelection, hand: WorkoutSide) {
        mutate { log in
            log.addExercise(type: type, holdSelection: holdSelection, hand: hand)
        }
    }

    private func addSet(to exerciseID: UUID) {
        mutate { log in
            _ = log.addSet(toExerciseID: exerciseID)
        }
    }

    private func deleteExercise(_ id: UUID) {
        mutate { log in
            log.removeExercise(id: id)
        }
    }

    private func moveExercise(_ id: UUID, toOffset: Int) {
        mutate { log in
            log.moveExercise(id: id, toOffset: toOffset)
        }
    }

    private func toggleSetCompletion(exerciseID: UUID, setID: UUID) {
        guard let set = currentSet(exerciseID: exerciseID, setID: setID) else { return }
        if set.isCompleted {
            mutate { log in
                log.uncompleteSet(exerciseID: exerciseID, setID: setID)
            }
        } else {
            // Checkbox is a quick manual complete (hang or pull-up).
            completeSet(exerciseID: exerciseID, setID: setID, mode: .manual)
        }
    }

    /// Persists default hang duration when the set has none, before starting guided hang.
    private func ensureHangDuration(exerciseID: UUID, setID: UUID) {
        guard let set = currentSet(exerciseID: exerciseID, setID: setID),
              set.duration == nil
        else { return }
        mutate { log in
            log.updateSet(
                exerciseID: exerciseID,
                setID: setID,
                weightKGF: set.weightKGF,
                duration: FreeWorkoutGuidedHangCountdown.defaultDuration,
                reps: set.reps,
                tag: set.tag
            )
        }
    }

    private func completeGuidedHang(
        exerciseID: UUID,
        setID: UUID,
        plannedDuration: TimeInterval,
        elapsed: TimeInterval
    ) {
        guard let set = currentSet(exerciseID: exerciseID, setID: setID) else { return }
        // Complete-early records actual hang time; natural end keeps planned duration.
        let recordedDuration = elapsed + 0.5 < plannedDuration ? elapsed : plannedDuration
        mutate { log in
            log.updateSet(
                exerciseID: exerciseID,
                setID: setID,
                weightKGF: set.weightKGF,
                duration: recordedDuration,
                reps: set.reps,
                tag: set.tag
            )
        }
        completeSet(exerciseID: exerciseID, setID: setID, mode: .guided)
    }

    private func completeLoggedSet(
        exerciseID: UUID,
        setID: UUID,
        weightKGF: Double?,
        duration: TimeInterval?,
        reps: Int?
    ) {
        guard let set = currentSet(exerciseID: exerciseID, setID: setID) else { return }
        mutate { log in
            log.updateSet(
                exerciseID: exerciseID,
                setID: setID,
                weightKGF: weightKGF,
                duration: duration,
                reps: reps,
                tag: set.tag
            )
        }
        completeSet(exerciseID: exerciseID, setID: setID, mode: .manual)
    }

    private func completeSet(exerciseID: UUID, setID: UUID, mode: FreeSetMode) {
        // Completing / starting the next set dismisses any active rest, then starts a new one.
        dismissRest()
        let restSeconds = log.exercises.first(where: { $0.id == exerciseID })?.restAfterSeconds
            ?? FreeExercise.defaultRestAfterSeconds
        mutate { log in
            log.completeSet(exerciseID: exerciseID, setID: setID, mode: mode)
        }
        restTimer.start(duration: restSeconds)
    }

    private func adjustRest(by delta: TimeInterval, at now: Date) {
        restTimer.adjust(by: delta, at: now)
    }

    private func skipRest() {
        restTimer.skip()
    }

    private func dismissRest() {
        restTimer.dismiss()
    }

    private func confirmFinish() {
        guard !didFinish else { return }
        if FreeWorkoutFinish.completedSetCount(in: log) == 0 {
            showsDiscardAlert = true
            return
        }
        performFinish()
    }

    private func discardAndDismiss() {
        guard !didFinish else { return }
        didFinish = true
        FreeWorkoutFinish.discardActive()
        dismissAfterFinish()
    }

    private func performFinish() {
        guard !didFinish else { return }
        guard let finished = FreeWorkoutFinish.persistToHistory(log) else {
            showsDiscardAlert = true
            return
        }
        didFinish = true
        finishedForTemplate = finished
        log = finished

        let health = FreeWorkoutFinish.healthRecordingInput(from: finished)
        store.markSessionComplete(
            health.plan,
            startDate: health.startDate,
            endDate: health.endDate,
            sessionSteps: health.sessionSteps,
            session: health.session
        )

        templateName = ""
        showsTemplatePrompt = true
    }

    private func saveTemplateAndDismiss() {
        if let finished = finishedForTemplate {
            _ = FreeWorkoutFinish.saveTemplate(name: templateName, finished: finished)
        }
        dismissAfterFinish()
    }

    private func dismissAfterFinish() {
        finishedForTemplate = nil
        if let onFinished {
            onFinished()
        } else {
            dismiss()
        }
    }

    // MARK: - Labels / highlight

    private func elapsedLabel(at date: Date) -> String {
        let elapsed = max(0, date.timeIntervalSince(log.startedAt))
        let totalSeconds = Int(elapsed.rounded(.down))
        let minutes = totalSeconds / 60
        let seconds = totalSeconds % 60
        return String(format: "Elapsed %d:%02d", minutes, seconds)
    }

    private func countdownLabel(_ remaining: TimeInterval) -> String {
        let totalSeconds = Int(remaining.rounded(.up))
        let minutes = totalSeconds / 60
        let seconds = totalSeconds % 60
        return String(format: "%d:%02d", minutes, seconds)
    }

    private func holdSubtitle(_ selection: FreeWorkoutHoldSelection) -> String {
        switch selection {
        case .generic(let kind):
            return kind.label
        case .exact(let exact):
            if let contact = board.contacts.first(where: { $0.id == exact.contactID }) {
                return contact.name
            }
            return exact.kind?.label ?? "Hold"
        }
    }

    /// Resolves hold highlight via the same ContactResolver path as timeline sessions,
    /// driven by the focused exercise’s hold — not WorkoutTimeline.
    static func contactIDs(for selection: FreeWorkoutHoldSelection, hand: WorkoutSide, on board: BoardRevision) -> Set<String> {
        let requirements: [ContactRequirement]
        switch selection {
        case .generic(let kind):
            requirements = [.kind(kind)]
        case .exact(let exact):
            requirements = [
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
        let handUse: WorkoutHandUse = hand == .both ? .double : .single
        let step = WorkoutStep(
            id: "free-log-highlight",
            number: 1,
            title: "",
            instruction: "",
            accessory: "",
            duration: 1,
            phase: .hang,
            segments: [
                WorkoutSegment(
                    kind: .work,
                    target: .fromLegacyTargets(requirements),
                    timing: .fixed,
                    duration: 1
                )
            ],
            handUse: handUse,
            side: hand,
            action: .hang
        )
        return Set(WorkoutHighlightResolver.contactIDs(for: step, on: board))
    }
}
